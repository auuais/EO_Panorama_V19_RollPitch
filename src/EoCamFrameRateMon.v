//============================================================================
// EoCamFrameRateMon
//
// Input frame rate of the six EO cameras, measured at the pins.
//
// Each camera's VSYNC is synchronised into clk and its frame starts counted
// over a one-second window, so `fps` is the rate the camera actually delivers
// -- upstream of the DDR writers, the frame-set manager and everything on the
// output side, any of which can hide or invent frames.
//
// The count alone cannot tell free-run from genlock: six free-running cameras
// also read 30 fps each.  What separates them is the spread of the frame
// PERIOD, so the window also keeps the shortest and longest interval seen for
// every camera.  Genlocked cameras follow one trigger, so min and max sit
// close together; free-running ones drift against each other, and a camera
// that misses a genlock edge shows one interval of about twice the nominal.
//
// The trigger's own rate and period are reported alongside, so the cameras can
// be compared against what they are supposed to be following.
//
// Periods are counted in ticks of TICK_CYCLES clk cycles, so a whole frame
// fits in the probe word:
//   74.25 MHz / 256 = 3.4512 us per tick; a 33.3 ms frame is 9651 ticks and
//   the 15-bit field reaches 113 ms.
//   microseconds = ticks * TICK_CYCLES * 1e6 / CLK_HZ
//
// dbg_word carries one camera at a time and `sel` advances every window, so
// consecutive ILA captures sweep all six:
//   [63:62] 2'b10 signature      [61:56] trigger edges in the window
//   [55:42] trigger period       [41:39] camera this word describes
//   [38:31] that camera's frames in the window
//   [30:16] its shortest frame period   [15:1] its longest    [0] spare
// All periods are in ticks.  Nothing here sits in the video path.
//============================================================================
`timescale 1ns/1ps
module EoCamFrameRateMon #(
    parameter integer CLK_HZ      = 74_250_000,
    parameter integer TICK_CYCLES = 256,
    parameter integer WINDOW_MS   = 1000
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [5:0]  cam_vsync,     // asynchronous, one per EO camera
    input  wire        trigger,       // common exposure trigger, clk domain

    // From each receiver's TRS decode, in that camera's pixel clock domain.
    // frame_tgl toggles once per frame start; lines and f are the frame that
    // just ended and hold until the next toggle, so they are sampled on the
    // synchronised toggle without a handshake.
    input  wire [5:0]  trs_frame_tgl,
    input  wire [71:0] trs_lines,     // 6 x 12 bits
    input  wire [5:0]  trs_f,

    output reg  [63:0] dbg_word,
    output reg  [63:0] dbg_word2
);
    localparam integer TICK_HZ      = CLK_HZ / TICK_CYCLES;
    localparam integer WINDOW_TICKS = (TICK_HZ * WINDOW_MS) / 1000;
    localparam [15:0]  PERIOD_MAX   = 16'h7FFF;   // saturate, 15-bit fields

    //------------------------------------------------------------------------
    // Tick and window
    //------------------------------------------------------------------------
    reg [15:0] tick_div = 16'd0;
    reg [23:0] win_cnt  = 24'd0;
    reg        tick     = 1'b0;
    reg        win_end  = 1'b0;
    always @(posedge clk) begin
        tick    <= 1'b0;
        win_end <= 1'b0;
        if (!rst_n) begin
            tick_div <= 16'd0;
            win_cnt  <= 24'd0;
        end else if (tick_div == TICK_CYCLES - 1) begin
            tick_div <= 16'd0;
            tick     <= 1'b1;
            if (win_cnt == WINDOW_TICKS - 1) begin
                win_cnt <= 24'd0;
                win_end <= 1'b1;
            end else begin
                win_cnt <= win_cnt + 24'd1;
            end
        end else begin
            tick_div <= tick_div + 16'd1;
        end
    end

    //------------------------------------------------------------------------
    // Per camera: frame starts, period, and the window's min/max period
    //------------------------------------------------------------------------
    reg [7:0]  fps_q    [0:5];
    reg [15:0] pmin_q   [0:5];
    reg [15:0] pmax_q   [0:5];
    reg [7:0]  cnt_acc  [0:5];
    reg [15:0] pmin_acc [0:5];
    reg [15:0] pmax_acc [0:5];
    reg [15:0] period   [0:5];
    reg [2:0]  vs_sync  [0:5];
    reg        have_prev[0:5];

    genvar g;
    generate
        for (g = 0; g < 6; g = g + 1) begin : g_cam
            // Same edge convention as the follower diagnostic one level up:
            // the frame starts as VSYNC falls.
            wire frame_start = vs_sync[g][2] && !vs_sync[g][1];
            always @(posedge clk) begin
                if (!rst_n) begin
                    vs_sync[g]   <= 3'd0;
                    period[g]    <= 16'd0;
                    cnt_acc[g]   <= 8'd0;
                    pmin_acc[g]  <= PERIOD_MAX;
                    pmax_acc[g]  <= 16'd0;
                    fps_q[g]     <= 8'd0;
                    pmin_q[g]    <= 16'd0;
                    pmax_q[g]    <= 16'd0;
                    have_prev[g] <= 1'b0;
                end else begin
                    vs_sync[g] <= {vs_sync[g][1:0], cam_vsync[g]};

                    if (frame_start) begin
                        period[g] <= 16'd0;
                        if (cnt_acc[g] != 8'hFF) cnt_acc[g] <= cnt_acc[g] + 8'd1;
                        // The first edge of a window has no complete interval
                        // behind it, so it only starts the clock.
                        if (have_prev[g]) begin
                            if (period[g] < pmin_acc[g]) pmin_acc[g] <= period[g];
                            if (period[g] > pmax_acc[g]) pmax_acc[g] <= period[g];
                        end
                        have_prev[g] <= 1'b1;
                    end else if (tick && (period[g] != PERIOD_MAX)) begin
                        period[g] <= period[g] + 16'd1;
                    end

                    if (win_end) begin
                        fps_q[g]     <= cnt_acc[g];
                        pmin_q[g]    <= (pmin_acc[g] == PERIOD_MAX) ? 16'd0 : pmin_acc[g];
                        pmax_q[g]    <= pmax_acc[g];
                        cnt_acc[g]   <= 8'd0;
                        pmin_acc[g]  <= PERIOD_MAX;
                        pmax_acc[g]  <= 16'd0;
                        have_prev[g] <= 1'b0;
                    end
                end
            end
        end
    endgenerate

    //------------------------------------------------------------------------
    // SAV/EAV: lines per frame, and the field bit
    //
    // A camera that answered every other trigger would still show 30 frame
    // starts a second; if instead it switched to fields, these counts halve
    // and the F bit alternates.  That is the difference this measures.
    //------------------------------------------------------------------------
    reg [11:0] lines_last_q [0:5];
    reg [11:0] lines_min_q  [0:5];
    reg [11:0] lines_max_q  [0:5];
    reg [11:0] lines_min_acc[0:5];
    reg [11:0] lines_max_acc[0:5];
    reg [7:0]  ftog_q       [0:5];
    reg [7:0]  ftog_acc     [0:5];
    reg [7:0]  tframes_q    [0:5];
    reg [7:0]  tframes_acc  [0:5];

    genvar t;
    generate
        for (t = 0; t < 6; t = t + 1) begin : g_trs
            (* ASYNC_REG = "TRUE" *) reg [2:0] tgl_sync;
            reg f_prev;
            wire tgl_edge = tgl_sync[2] ^ tgl_sync[1];
            wire [11:0] lines_now = trs_lines[t*12 +: 12];
            always @(posedge clk) begin
                if (!rst_n) begin
                    tgl_sync <= 3'd0; f_prev <= 1'b0;
                    lines_last_q[t] <= 12'd0;
                    lines_min_q[t] <= 12'd0; lines_max_q[t] <= 12'd0;
                    lines_min_acc[t] <= 12'hFFF; lines_max_acc[t] <= 12'd0;
                    ftog_q[t] <= 8'd0; ftog_acc[t] <= 8'd0;
                    tframes_q[t] <= 8'd0; tframes_acc[t] <= 8'd0;
                end else begin
                    tgl_sync <= {tgl_sync[1:0], trs_frame_tgl[t]};
                    if (tgl_edge) begin
                        lines_last_q[t] <= lines_now;
                        if (lines_now < lines_min_acc[t]) lines_min_acc[t] <= lines_now;
                        if (lines_now > lines_max_acc[t]) lines_max_acc[t] <= lines_now;
                        if (tframes_acc[t] != 8'hFF) tframes_acc[t] <= tframes_acc[t] + 8'd1;
                        f_prev <= trs_f[t];
                        if (f_prev != trs_f[t] && (ftog_acc[t] != 8'hFF))
                            ftog_acc[t] <= ftog_acc[t] + 8'd1;
                    end
                    if (win_end) begin
                        lines_min_q[t] <= (lines_min_acc[t] == 12'hFFF) ? 12'd0 : lines_min_acc[t];
                        lines_max_q[t] <= lines_max_acc[t];
                        ftog_q[t]      <= ftog_acc[t];
                        tframes_q[t]   <= tframes_acc[t];
                        lines_min_acc[t] <= 12'hFFF;
                        lines_max_acc[t] <= 12'd0;
                        ftog_acc[t]      <= 8'd0;
                        tframes_acc[t]   <= 8'd0;
                    end
                end
            end
        end
    endgenerate

    //------------------------------------------------------------------------
    // The trigger they are meant to follow
    //------------------------------------------------------------------------
    reg  [2:0]  trig_sync     = 3'd0;
    reg  [15:0] trig_period   = 16'd0;
    reg  [15:0] trig_period_q = 16'd0;
    reg  [7:0]  trig_cnt      = 8'd0;
    reg  [7:0]  trig_fps_q    = 8'd0;
    wire        trig_edge     = trig_sync[1] && !trig_sync[2];
    always @(posedge clk) begin
        if (!rst_n) begin
            trig_sync <= 3'd0; trig_period <= 16'd0; trig_period_q <= 16'd0;
            trig_cnt <= 8'd0; trig_fps_q <= 8'd0;
        end else begin
            trig_sync <= {trig_sync[1:0], trigger};
            if (trig_edge) begin
                trig_period   <= 16'd0;
                trig_period_q <= trig_period;
                if (trig_cnt != 8'hFF) trig_cnt <= trig_cnt + 8'd1;
            end else if (tick && (trig_period != PERIOD_MAX)) begin
                trig_period <= trig_period + 16'd1;
            end
            if (win_end) begin
                trig_fps_q <= trig_cnt;
                trig_cnt   <= 8'd0;
            end
        end
    end

    //------------------------------------------------------------------------
    // One camera per word; sel advances every window
    //------------------------------------------------------------------------
    reg [2:0] sel = 3'd0;
    always @(posedge clk) begin
        if (!rst_n) begin
            sel      <= 3'd0;
            dbg_word <= 64'd0;
        end else begin
            if (win_end) sel <= (sel == 3'd5) ? 3'd0 : (sel + 3'd1);
            // second word: same camera, from the SAV/EAV decode
            //   [63:61] sel  [60:49] lines last  [48:37] min  [36:25] max
            //   [24:17] F-bit changes  [16:9] frame starts  [8:0] spare
            dbg_word2 <= {sel, lines_last_q[sel], lines_min_q[sel], lines_max_q[sel],
                          ftog_q[sel], tframes_q[sel], 9'd0};
            dbg_word <= {2'b10,                       // [63:62] signature
                         trig_fps_q[5:0],             // [61:56]
                         trig_period_q[13:0],         // [55:42]
                         sel,                         // [41:39]
                         fps_q[sel],                  // [38:31]
                         pmin_q[sel][14:0],           // [30:16]
                         pmax_q[sel][14:0],           // [15:1]
                         1'b0};
        end
    end
endmodule
