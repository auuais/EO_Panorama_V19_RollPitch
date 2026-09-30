//============================================================================
// RpEmitter
//
// Streams finished output rows from the RowWindow as the panorama raster the
// M1 renderers produced: 3840 pixels per row for EO, 3576 for IR (the IR fold
// formatter pads the rest).
//
// Row sy_out may be emitted once ROW_READY[sy_out] <= y0_done (every pixel of
// it has then been written this pass), or once the whole pass is done.
//
// Strips are read in order, one read per pixel.  Seam k joins strip k and
// strip k+1: strip k's pixels from TAIL_START[k] on are held in a seam buffer
// and the first HEAD_LEN[k] pixels j of strip k+1 are blended with buffer
// entry min(j, TAIL_LEN[k]-1) at alpha index ALPHA_POS(k, j):
//
//   EO   every seam 17/17, alpha j, Y and C blended with rounding
//   IR   29/29 with alpha j, except seam 2 (cam2/cam3), which straddles the
//        fold: 48 cam2 pixels (lx 592..639, the last one repeated), 90 cam3
//        pixels, alpha cam23_fold_alpha_pos(j); luma blended with vlerp
//
// Absent cameras: EO blacks a seam whose camera A is absent; IR shows camera
// B instead (M1 IR renderer's promotion).  A row the walker had to drop
// pixels from (RowWindow overflow) is emitted black.
//============================================================================
`timescale 1ns/1ps
module RpEmitter #(
    parameter integer NUM_ROWS = 480,
    parameter [15:0]  BLACK = 16'h1080,
    parameter integer RW_RD_LAT = 2,
    parameter         ALPHA_Y_FILE    = "../../assets/rowruns/eo_v19_alpha_y.mem",
    parameter         ALPHA_C_FILE    = "../../assets/rowruns/eo_v19_alpha_c.mem",
    parameter         IR_ALPHA_Y_FILE = "../../assets/rowruns/ir_v19_alpha_y.mem"
) (
    input  wire         clk,
    input  wire         rst,
    input  wire         sensor_ir,
    input  wire         start,
    input  wire [5:0]   cam_present,
    // IR only: tint every camera pixel magenta (luma kept, chroma replaced),
    // to flag that a roll/pitch offset is in force.  Pixels that are black
    // because no camera supplied them stay black.
    input  wire         mark_ir,

    output reg  [8:0]   rr_raddr,
    input  wire [10:0]  rr_rdata,          // latency 1

    input  wire         y0_done_valid,
    input  wire [10:0]  y0_done,
    input  wire         all_done,

    input  wire         drop_valid,
    input  wire [8:0]   drop_sy,

    output reg  [17:0]  rw_raddr,
    input  wire [71:0]  rw_dout,           // latency RW_RD_LAT

    output wire         px_valid,
    input  wire         px_ready,
    output wire [15:0]  px_data,
    output reg          frame_done,
    output reg          done,

    output reg  [8:0]   sy_out,
    output wire         can_progress
);
    //------------------------------------------------------------------------
    // Sensor geometry
    //------------------------------------------------------------------------
    reg ir;                                  // latched at start
    function [9:0] strip_w;
        input [2:0] k; input i;
        begin
            if (i) case (k) 3'd0: strip_w = 616; 3'd2: strip_w = 640; default: strip_w = 621; endcase
            else   case (k) 3'd0: strip_w = 650; default: strip_w = 655; endcase
        end
    endfunction
    function [11:0] strip_base;
        input [2:0] k; input i;
        begin
            if (i) case (k) 3'd0: strip_base = 0; 3'd1: strip_base = 616; 3'd2: strip_base = 1237;
                            3'd3: strip_base = 1877; 3'd4: strip_base = 2498; default: strip_base = 3119; endcase
            else   case (k) 3'd0: strip_base = 0; 3'd1: strip_base = 650; 3'd2: strip_base = 1305;
                            3'd3: strip_base = 1960; 3'd4: strip_base = 2615; default: strip_base = 3270; endcase
        end
    endfunction
    function [9:0] tail_start;          // seam k, in strip k
        input [2:0] k; input i;
        begin
            if (i) tail_start = (k == 3'd0) ? 10'd587 : 10'd592;
            else   tail_start = (k == 3'd0) ? 10'd633 : 10'd638;
        end
    endfunction
    function [5:0] tail_len;
        input [2:0] k; input i;
        begin
            tail_len = i ? ((k == 3'd2) ? 6'd48 : 6'd29) : 6'd17;
        end
    endfunction
    function [6:0] head_len;
        input [2:0] k; input i;
        begin
            head_len = i ? ((k == 3'd2) ? 7'd90 : 7'd29) : 7'd17;
        end
    endfunction
    function [4:0] cam23_fold_alpha_pos;
        input [6:0] j;
        reg [10:0] scaled;
        begin
            if (j <= 7'd17) cam23_fold_alpha_pos = 5'd0;
            else begin
                scaled = ((j - 7'd17) * 5'd25) + 11'd32;
                cam23_fold_alpha_pos = (scaled[10:6] > 5'd28) ? 5'd28 : scaled[10:6];
            end
        end
    endfunction

    reg [15:0] alpha_y    [0:31];
    reg [15:0] alpha_c    [0:15];
    reg [15:0] alpha_y_ir [0:31];
    initial begin
        $readmemh(ALPHA_Y_FILE, alpha_y);
        $readmemh(ALPHA_C_FILE, alpha_c);
        $readmemh(IR_ALPHA_Y_FILE, alpha_y_ir);
    end

    //------------------------------------------------------------------------
    // Row sequencing
    //------------------------------------------------------------------------
    localparam [2:0] E_IDLE = 3'd0, E_RR = 3'd1, E_RR2 = 3'd2, E_RR3 = 3'd3,
                     E_WAIT = 3'd4, E_ROW = 3'd5, E_FLUSH = 3'd6, E_DONE = 3'd7;
    reg [2:0]  state;
    reg [10:0] rr_val;
    reg [479:0] row_bad;
    reg [5:0]  present;
    reg [2:0]  k;
    reg [9:0]  j;

    wire ready_now = all_done || (y0_done_valid && (rr_val <= y0_done));
    assign can_progress = !((state == E_WAIT) && !ready_now);

    localparam integer PIPE = RW_RD_LAT + 4;
    reg  [PIPE-1:0] pv;
    reg  [4:0]      ocount;
    function [4:0] count_ones;
        input [PIPE-1:0] v;
        integer n;
        begin
            count_ones = 0;
            for (n = 0; n < PIPE; n = n + 1) count_ones = count_ones + v[n];
        end
    endfunction
    wire [4:0] pipe_n = count_ones(pv);
    wire room = (ocount + pipe_n) < 5'd14;
    wire issue = (state == E_ROW) && room;
    wire last_of_row = (k == 3'd5) && (j == strip_w(3'd5, ir) - 10'd1);

    always @(posedge clk) begin
        if (rst) begin
            state <= E_IDLE; sy_out <= 9'd0; done <= 1'b0; ir <= 1'b0;
        end else begin
            case (state)
            E_IDLE: if (start) begin
                sy_out <= 9'd0; done <= 1'b0; row_bad <= 480'd0; present <= cam_present;
                ir <= sensor_ir;
                state <= E_RR;
            end
            // rr_raddr is registered in E_RR, read by the table in E_RR2 and
            // its data is on rr_rdata in E_RR3.
            E_RR:   begin rr_raddr <= sy_out; state <= E_RR2; end
            E_RR2:  state <= E_RR3;
            E_RR3:  begin rr_val <= rr_rdata; state <= E_WAIT; end
            E_WAIT: if (ready_now) begin k <= 3'd0; j <= 10'd0; state <= E_ROW; end
            E_ROW: if (issue) begin
                if (last_of_row) begin
                    if (sy_out == NUM_ROWS - 1) state <= E_FLUSH;
                    else begin sy_out <= sy_out + 9'd1; state <= E_RR; end
                end else if (j == strip_w(k, ir) - 10'd1) begin
                    k <= k + 3'd1; j <= 10'd0;
                end else begin
                    j <= j + 10'd1;
                end
            end
            E_FLUSH: if (frame_done) begin done <= 1'b1; state <= E_DONE; end
            default: ;
            endcase
            if (drop_valid) row_bad[drop_sy] <= 1'b1;
        end
    end

    //------------------------------------------------------------------------
    // Pixel pipeline
    //   p0 issue: rw_raddr, side {k, j, sel, bad, last}
    //   p0+RW_RD_LAT: word arrives -> extract pixel
    //   +1 classify (tail -> seam buffer, head -> pair with buffered pixel)
    //   +2 products  +3 result -> output FIFO
    //------------------------------------------------------------------------
    reg [2:0] sk [0:7];
    reg [9:0] sj [0:7];
    reg [2:0] ssel [0:7];
    reg       sbad [0:7];
    reg       slast [0:7];
    integer   m;
    always @(posedge clk) begin
        if (rst) pv <= 0;
        else     pv <= {pv[PIPE-2:0], issue};
        if (issue) begin : addr
            reg [11:0] sx;
            sx = strip_base(k, ir) + {2'd0, j};
            if (ir) begin rw_raddr <= {sy_out[8:0], sx[11:3]}; ssel[0] <= sx[2:0]; end
            else    begin rw_raddr <= {sy_out[7:0], sx[11:2]}; ssel[0] <= {1'b0, sx[1:0]}; end
        end
        sk[0] <= k; sj[0] <= j; sbad[0] <= row_bad[sy_out];
        slast[0] <= last_of_row && (sy_out == NUM_ROWS - 1);
        for (m = 1; m < 8; m = m + 1) begin
            sk[m] <= sk[m-1]; sj[m] <= sj[m-1]; ssel[m] <= ssel[m-1]; sbad[m] <= sbad[m-1]; slast[m] <= slast[m-1];
        end
    end

    wire        w_v    = pv[RW_RD_LAT];
    wire [2:0]  w_k    = sk[RW_RD_LAT];
    wire [9:0]  w_j    = sj[RW_RD_LAT];
    wire [2:0]  w_sel  = ssel[RW_RD_LAT];
    wire        w_bad  = sbad[RW_RD_LAT];
    wire        w_last = slast[RW_RD_LAT];
    wire [15:0] w_px   = ir ? {rw_dout[w_sel*9 +: 8], 8'h80} : rw_dout[w_sel[1:0]*18 +: 16];

    // seam buffer, random access by position within the tail
    reg [15:0] seam [0:47];

    wire       tail = (w_k != 3'd5) && (w_j >= tail_start(w_k, ir));
    wire       head = (w_k != 3'd0) && (w_j < head_len(w_k - 3'd1, ir));
    wire [9:0] tail_idx = w_j - tail_start(w_k, ir);
    wire [5:0] tl_prev  = tail_len(w_k - 3'd1, ir);
    wire [5:0] head_idx = (w_j >= tl_prev) ? (tl_prev - 6'd1) : w_j[5:0];
    wire [4:0] apos     = (ir && (w_k == 3'd3)) ? cam23_fold_alpha_pos(w_j[6:0]) : w_j[4:0];

    reg        c_v, c_out, c_blend, c_bad, c_last, c_pa, c_pb;
    reg [15:0] c_a, c_b;
    reg [15:0] c_fy, c_fc;
    always @(posedge clk) begin
        if (rst || (state == E_IDLE)) begin
            c_v <= 1'b0;
        end else begin
            c_v <= w_v;
            if (w_v && tail) seam[tail_idx[5:0]] <= w_px;
        end
        c_out   <= !tail;
        c_blend <= head;
        c_bad   <= w_bad;
        c_last  <= w_last;
        c_a     <= head ? seam[head_idx] : w_px;
        c_b     <= w_px;
        c_pa    <= head ? present[w_k - 3'd1] : present[w_k];
        c_pb    <= present[w_k];
        c_fy    <= ir ? alpha_y_ir[apos] : alpha_y[apos];
        c_fc    <= alpha_c[(apos > 5'd15) ? 4'd7 : apos[4:1]];
    end

    function [32:0] wacc;
        input [7:0] a, b;
        input [15:0] f;
        begin
            wacc = ({1'b0, a} * (17'd65536 - {1'b0, f})) + ({1'b0, b} * {1'b0, f}) + 33'd32768;
        end
    endfunction
    function [7:0] vlerp;
        input [7:0] p0, p1;
        input [15:0] f;
        reg signed [8:0]  d;
        reg signed [24:0] mm;
        begin
            d  = $signed({1'b0, p1}) - $signed({1'b0, p0});
            mm = d * $signed({1'b0, f});
            vlerp = p0 + mm[24:16];
        end
    endfunction
    reg        d_v, d_out, d_blend, d_bad, d_last, d_pa, d_pb;
    reg [15:0] d_a, d_b;
    reg [32:0] d_y, d_c;
    reg [7:0]  d_ir;
    always @(posedge clk) begin
        d_v <= rst ? 1'b0 : c_v;
        d_out <= c_out; d_blend <= c_blend; d_bad <= c_bad; d_last <= c_last;
        d_pa <= c_pa; d_pb <= c_pb; d_a <= c_a; d_b <= c_b;
        d_y  <= wacc(c_a[15:8], c_b[15:8], c_fy);
        d_c  <= wacc(c_a[7:0],  c_b[7:0],  c_fc);
        d_ir <= vlerp(c_a[15:8], c_b[15:8], c_fy);
    end

    reg        e_v, e_last;
    reg [15:0] e_px;
    reg [15:0] e_raw;
    reg        e_blk;          // black because no camera supplied this pixel
    always @* begin
        if (d_bad) begin
            e_raw = BLACK;                                    e_blk = 1'b1;
        end else if (!d_blend) begin
            e_raw = d_pa ? d_a : BLACK;                       e_blk = !d_pa;
        end else if (d_pa && d_pb) begin
            e_raw = ir ? {d_ir, 8'h80} : {d_y[23:16], d_c[23:16]};
            e_blk = 1'b0;
        end else if (d_pa) begin
            e_raw = d_a;                                      e_blk = 1'b0;
        end else if (d_pb && ir) begin
            e_raw = d_b;                                      e_blk = 1'b0;
        end else begin
            e_raw = BLACK;                                    e_blk = 1'b1;
        end
    end

    // 4:2:2 chroma alternates Cb, Cr along the row.  Every output row is an
    // even number of pixels (3840 EO, 3576 IR), so one free-running parity
    // reset at pass start stays aligned for the whole frame.
    localparam [7:0] MAGENTA_CB = 8'd212;
    localparam [7:0] MAGENTA_CR = 8'd235;
    wire       e_push = !rst && d_v && d_out;
    reg        e_par;
    always @(posedge clk) begin
        if (rst || start)   e_par <= 1'b0;
        else if (e_push)    e_par <= ~e_par;
    end
    wire [7:0] magenta_c = e_par ? MAGENTA_CR : MAGENTA_CB;

    always @(posedge clk) begin
        e_v    <= e_push;
        e_last <= d_last;
        e_px   <= (ir && mark_ir && !e_blk) ? {e_raw[15:8], magenta_c} : e_raw;
    end

    //------------------------------------------------------------------------
    // Output FIFO (16 entries)
    //------------------------------------------------------------------------
    reg [16:0] ofifo [0:15];
    reg [3:0]  o_wr, o_rd;
    wire       o_pop = (ocount != 0) && px_ready;
    assign px_valid = (ocount != 0);
    assign px_data  = ofifo[o_rd][15:0];
    always @(posedge clk) begin
        if (rst) begin
            o_wr <= 4'd0; o_rd <= 4'd0; ocount <= 5'd0; frame_done <= 1'b0;
        end else begin
            frame_done <= 1'b0;
            if (e_v) begin
                ofifo[o_wr] <= {e_last, e_px};
                o_wr <= o_wr + 4'd1;
            end
            if (o_pop) begin
                o_rd <= o_rd + 4'd1;
                if (ofifo[o_rd][16]) frame_done <= 1'b1;
            end
            ocount <= ocount + (e_v ? 5'd1 : 5'd0) - (o_pop ? 5'd1 : 5'd0);
        end
    end
endmodule
