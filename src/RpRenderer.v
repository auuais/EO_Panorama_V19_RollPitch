`include "EoV19PanoramaParams.vh"
//============================================================================
// RpRenderer
//
// Source-driven panorama renderer with live per-camera roll/pitch offsets,
// shared by EO and IR panorama (they never run at the same time).  Replaces
// EoV19StreamingRendererII1 and IrV19StreamingRenderer: same output rasters,
// same seam blends, bit-exact with them at zero offset.  See
// docs/ROLLPITCH_SOURCE_DRIVEN_RENDERER.md.
//
// Per pass, for y0 = Ylo .. Yhi:
//   ROWS       rows y0 and y0+1 are complete in the line ring
//   GO/WALK    the walker issues every pixel whose source row is y0
//   DRAIN      the sampler has written them into the RowWindow
//   then y0_done = y0 lets the emitter release rows whose ROW_READY <= y0.
// The replay is asked for row y0+2 while y0 renders, so it fetches the next
// row concurrently into the ring's third slot.
//
// Tables are rebuilt between passes whenever the selected sensor or its
// offsets change (~1 M cycles, ~4 ms).
//============================================================================
`timescale 1ns/1ps
module RpRenderer #(
    parameter integer SETTLE_CYCLES     = 1,
    parameter integer DRAIN_CYCLES      = 16,
    // IR_OFFSET_MARK 1: while any IR camera carries a roll or pitch offset,
    // the IR panorama is tinted magenta (RpEmitter mark_ir).  EO is never
    // marked.  0 = off.
    parameter integer IR_OFFSET_MARK    = 0,
    parameter         RUN_ROM_FILE      = "../../assets/rowruns/eo_v19_render_runs.mem",
    parameter         IR_RUN_ROM_FILE   = "../../assets/rowruns/ir_v19_render_runs.mem",
    parameter         ANGLE_ROM_FILE    = "../../assets/rollpitch/eo_rp_angle.mem",
    parameter         IR_ANGLE_ROM_FILE = "../../assets/rollpitch/ir_rp_angle.mem",
    parameter         ALPHA_Y_FILE      = "../../assets/rowruns/eo_v19_alpha_y.mem",
    parameter         ALPHA_C_FILE      = "../../assets/rowruns/eo_v19_alpha_c.mem",
    parameter         IR_ALPHA_Y_FILE   = "../../assets/rowruns/ir_v19_alpha_y.mem"
) (
    input  wire          rst_n,
    input  wire          clk,
    input  wire          sensor_ir,         // 0 EO panorama, 1 IR panorama
    input  wire          start_copy,
    input  wire [5:0]    cam_present,
    input  wire          source_frame_reset,

    // BEAT_OUT replay of the selected sensor
    input  wire          beat_valid,
    input  wire [10:0]   beat_row,
    input  wire [6:0]    beat_idx,
    input  wire [1535:0] beat_data,
    input  wire          row_done,
    input  wire [10:0]   row_done_row,

    // offsets, already synchronised and stable (ui_clk)
    input  wire [95:0]   eo_roll_cd,
    input  wire [95:0]   eo_pitch_cd,
    input  wire [95:0]   ir_roll_cd,
    input  wire [95:0]   ir_pitch_cd,

    output wire          px_valid,
    input  wire          px_ready,
    output wire [15:0]   px_data,
    output wire          frame_done,
    output wire          frames_valid,

    output wire          source_need_valid,
    output wire [10:0]   source_need_row,
    output wire [10:0]   source_start_row,
    // EO camera writer / replay windows from the last EO table build
    output reg  [6:0]    fetch_beat_lo,
    output reg  [6:0]    fetch_beat_hi,
    output reg  [10:0]   wr_row_lo,
    output reg  [10:0]   wr_row_hi,
    output reg  [6:0]    wr_beat_lo,
    output reg  [6:0]    wr_beat_hi,

    // status
    output wire          tables_valid,
    output wire          tables_busy,
    output wire [31:0]   build_count,
    output wire [15:0]   status_flags,
    output wire [63:0]   dbg_word
);
    wire rst = !rst_n;

    //------------------------------------------------------------------------
    // Tables
    //------------------------------------------------------------------------
    reg         build_req;
    reg  [95:0] built_roll, built_pitch;
    reg         built_once;
    wire        tbl_busy, tbl_valid, tbl_sat, tbl_ir;
    wire [10:0] ylo, yhi, col_lo, col_hi;
    wire [14:0] rom_addr;
    wire [143:0] rom_data, rom_data_unused;
    wire [95:0] rom_data_ir, rom_data_ir_unused;
    wire [14:0] params_raddr;
    wire [143:0] params_rdata;
    reg  [10:0] bend_raddr;
    wire [15:0] bend_rdata;
    wire [8:0]  rr_raddr;
    wire [10:0] rr_rdata;

    wire [95:0] sel_roll  = sensor_ir ? ir_roll_cd  : eo_roll_cd;
    wire [95:0] sel_pitch = sensor_ir ? ir_pitch_cd : eo_pitch_cd;

    // Fixed at pass start, with the tables the pass uses, so the tint appears
    // and clears on the same frame as the offset it reports.
    wire ir_offsets_set = sensor_ir && ((sel_roll != 96'd0) || (sel_pitch != 96'd0));
    reg  ir_mark_q = 1'b0;

    EoV19RunRom #(.DEPTH(`EO_V19_RUN_COUNT), .ADDR_W(15), .ROM_FILE(RUN_ROM_FILE)) u_rom (
        .clk(clk), .addr_a(rom_addr), .addr_b(15'd0), .data_a(rom_data), .data_b(rom_data_unused));
    IrV19RunRom #(.DEPTH(28800), .ADDR_W(15), .ROM_FILE(IR_RUN_ROM_FILE)) u_rom_ir (
        .clk(clk), .en(1'b1), .addr_a(rom_addr), .addr_b(15'd0), .data_a(rom_data_ir), .data_b(rom_data_ir_unused));

    RpTables #(.ANGLE_ROM_FILE(ANGLE_ROM_FILE), .IR_ANGLE_ROM_FILE(IR_ANGLE_ROM_FILE)) u_tables (
        .clk(clk), .rst(rst), .sensor_ir(sensor_ir),
        .build_req(build_req), .roll_cd(sel_roll), .pitch_cd(sel_pitch),
        .busy(tbl_busy), .tables_valid(tbl_valid), .sat_seen(tbl_sat), .build_count(build_count),
        .ylo(ylo), .yhi(yhi), .col_lo(col_lo), .col_hi(col_hi),
        .rom_addr(rom_addr), .rom_data(rom_data), .rom_data_ir(rom_data_ir), .built_ir(tbl_ir),
        .params_raddr(params_raddr), .params_rdata(params_rdata),
        .bend_raddr(bend_raddr), .bend_rdata(bend_rdata),
        .rready_raddr(rr_raddr), .rready_rdata(rr_rdata));
    assign tables_valid = tbl_valid;
    assign tables_busy  = tbl_busy;
    wire   tables_match = tbl_valid && (tbl_ir == sensor_ir) &&
                          (sel_roll == built_roll) && (sel_pitch == built_pitch);
    assign frames_valid = tables_match;

    //------------------------------------------------------------------------
    // Pass control
    //------------------------------------------------------------------------
    localparam [3:0] C_IDLE = 4'd0, C_BUILD = 4'd1, C_SETTLE = 4'd2, C_EDGE = 4'd3,
                     C_ROWS = 4'd4, C_BEND = 4'd5, C_GO = 4'd6, C_WALK = 4'd7,
                     C_DRAIN = 4'd8, C_FLUSH = 4'd9, C_END = 4'd10;
    reg [3:0]  cs;
    reg [26:0] settle;
    reg [10:0] y0;
    reg        y0_last;
    reg [15:0] bend_q;
    reg [1:0]  slot_a, slot_b;
    reg        y0_done_valid;
    reg [10:0] y0_done;
    reg        all_done;
    reg        need_valid;
    reg [10:0] need_row;
    reg [7:0]  drain;
    reg        pass_start;
    reg        pass_rst;
    reg        edge_seen_late;

    wire        walker_idle;
    wire [11:0] rows_done;
    wire        ring_idle;
    wire        emit_done;
    wire        emit_frame_done;
    wire [8:0]  sy_out;
    wire        emit_can_progress;
    wire        sampler_busy;

    wire rebuild_needed = !built_once || !tbl_valid || (tbl_ir != sensor_ir) ||
                          (sel_roll != built_roll) || (sel_pitch != built_pitch);
    wire [11:0] row_cap = tbl_ir ? 12'd511 : 12'd1079;

    assign source_need_valid = need_valid;
    assign source_need_row   = need_row;
    assign source_start_row  = ylo;

    function [10:0] cap_row;
        input [11:0] v;
        input [11:0] cap;
        begin cap_row = (v > cap) ? cap[10:0] : v[10:0]; end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            cs <= C_IDLE; build_req <= 1'b0; built_once <= 1'b0;
            built_roll <= 96'd0; built_pitch <= 96'd0;
            need_valid <= 1'b0; need_row <= 11'd0;
            y0_done_valid <= 1'b0; all_done <= 1'b0;
            pass_start <= 1'b0; pass_rst <= 1'b1; edge_seen_late <= 1'b0;
            settle <= 27'd0;
        end else begin
            build_req  <= 1'b0;
            pass_start <= 1'b0;
            pass_rst   <= 1'b0;

            if (!start_copy && (cs != C_IDLE) && (cs != C_BUILD) && (cs != C_SETTLE)) begin
                // abort / end of pass
                cs <= C_IDLE; need_valid <= 1'b0; pass_rst <= 1'b1;
                y0_done_valid <= 1'b0; all_done <= 1'b0;
            end else begin
                case (cs)
                C_IDLE: begin
                    // Rebuild between passes whenever the tables do not
                    // describe the selected sensor and its current offsets.
                    // A pending copy simply waits the ~4 ms.
                    if (rebuild_needed) begin
                        build_req <= 1'b1;
                        built_roll <= sel_roll; built_pitch <= sel_pitch;
                        cs <= C_BUILD;
                    end else if (start_copy) begin
                        pass_start <= 1'b1;
                        ir_mark_q <= (IR_OFFSET_MARK != 0) && ir_offsets_set;
                        y0 <= ylo; y0_last <= (ylo == yhi);
                        slot_a <= ylo % 3; slot_b <= (ylo + 11'd1) % 3;
                        y0_done_valid <= 1'b0; all_done <= 1'b0;
                        need_valid <= 1'b1;
                        need_row <= cap_row({1'b0, ylo} + 12'd2, row_cap);
                        cs <= C_EDGE;
                    end
                end
                C_BUILD: if (!build_req && !tbl_busy && tbl_valid) begin
                    built_once <= 1'b1; settle <= 27'd0; cs <= C_SETTLE;
                end
                C_SETTLE: begin
                    settle <= settle + 27'd1;
                    if (settle >= SETTLE_CYCLES - 1) cs <= C_IDLE;
                end
                C_EDGE: if (source_frame_reset) cs <= C_ROWS;
                C_ROWS: if (rows_done >= {1'b0, y0} + 12'd2) begin
                    bend_raddr <= y0; cs <= C_BEND;
                end
                C_BEND: cs <= C_GO;                 // bend_rdata valid next cycle
                C_GO: begin bend_q <= bend_rdata; cs <= C_WALK; drain <= 8'd0; end
                C_WALK: begin
                    // walker sees y0_go in the C_GO->C_WALK transition cycle;
                    // idle is only trusted from the second cycle on.
                    drain <= drain + 8'd1;
                    if ((drain != 8'd0) && walker_idle) begin drain <= 8'd0; cs <= C_DRAIN; end
                end
                C_DRAIN: begin
                    drain <= drain + 8'd1;
                    if (drain >= DRAIN_CYCLES && !sampler_busy) begin
                        y0_done <= y0; y0_done_valid <= 1'b1;
                        if (y0 == yhi) begin
                            all_done <= 1'b1; need_valid <= 1'b0; cs <= C_FLUSH;
                        end else begin
                            y0 <= y0 + 11'd1; y0_last <= (y0 + 11'd1 == yhi);
                            slot_a <= slot_b; slot_b <= (slot_b == 2'd2) ? 2'd0 : slot_b + 2'd1;
                            need_row <= cap_row({1'b0, y0} + 12'd3, row_cap);
                            cs <= C_ROWS;
                        end
                    end
                end
                C_FLUSH: if (emit_done) cs <= C_END;
                C_END: ;
                default: cs <= C_IDLE;
                endcase
                if (source_frame_reset && (cs == C_ROWS || cs == C_WALK || cs == C_DRAIN))
                    edge_seen_late <= 1'b1;
            end
        end
    end
    wire y0_go = (cs == C_GO);

    //------------------------------------------------------------------------
    // EO window outputs: follow the tables only while they describe EO, and
    // hold the last EO values while IR panorama runs (EO capture is off then).
    //------------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            fetch_beat_lo <= 7'd0;  fetch_beat_hi <= 7'd112;
            wr_row_lo <= 11'd0;     wr_row_hi <= 11'd1079;
            wr_beat_lo <= 7'd0;     wr_beat_hi <= 7'd119;
        end else if (tbl_valid && !tbl_ir) begin : win
            reg [10:0] cl;
            reg [6:0]  blo, bhi;
            // qx_phase may step one column below col_lo or up to col_hi.
            cl  = (col_lo == 11'd0) ? 11'd0 : col_lo - 11'd1;
            blo = {cl[10:7], 3'b000};               // (cl/16) rounded down to a batch of 8
            bhi = {col_hi[10:7], 3'b000};
            fetch_beat_lo <= blo;
            fetch_beat_hi <= bhi;
            wr_row_lo  <= ylo;
            wr_row_hi  <= (yhi == 11'd1079) ? 11'd1079 : yhi + 11'd1;
            wr_beat_lo <= blo;
            wr_beat_hi <= (bhi > 7'd112) ? 7'd119 : bhi + 7'd7;
        end
    end

    //------------------------------------------------------------------------
    // Datapath
    //------------------------------------------------------------------------
    wire [8:0]  ring_word;
    wire [1:0]  ring_sel;
    wire [2:0]  ring_cam;
    wire [15:0] ring_pa, ring_pb;

    RpLineRing u_ring (
        .clk(clk), .rst(rst), .frame_start(source_frame_reset), .sensor_ir(tbl_ir),
        .beat_valid(beat_valid), .beat_row(beat_row), .beat_idx(beat_idx), .beat_data(beat_data),
        .row_done(row_done), .row_done_row(row_done_row),
        .rows_done(rows_done), .writer_idle(ring_idle),
        .rd_word(ring_word), .rd_sel(ring_sel), .rd_cam(ring_cam),
        .rd_slot_a(slot_a), .rd_slot_b(slot_b),
        .rd_pa(ring_pa), .rd_pb(ring_pb));

    wire        tok_valid, drop_valid;
    wire [2:0]  tok_cam;
    wire [8:0]  tok_sy, drop_sy;
    wire [9:0]  tok_lx;
    wire signed [31:0] tok_ax, tok_ay;
    wire        q_ovf, alias_drop;
    wire [12:0] q_peak;
    wire [31:0] visits;

    RpWalker u_walker (
        .clk(clk), .sensor_ir(tbl_ir), .rst(rst || pass_rst), .pass_start(pass_start),
        .y0_go(y0_go), .y0(y0), .y0_last(y0_last), .bucket_end(bend_q), .idle(walker_idle),
        .params_raddr(params_raddr), .params_rdata(params_rdata),
        .sy_out(sy_out), .emit_can_progress(emit_can_progress),
        .tok_valid(tok_valid), .tok_cam(tok_cam), .tok_sy(tok_sy), .tok_lx(tok_lx),
        .tok_ax(tok_ax), .tok_ay(tok_ay), .drop_valid(drop_valid), .drop_sy(drop_sy),
        .queue_overflow_seen(q_ovf), .alias_drop_seen(alias_drop),
        .queue_peak(q_peak), .visit_count(visits));

    wire [7:0]  rw_we;
    wire [17:0] rw_waddr, rw_raddr;
    wire [71:0] rw_din, rw_dout;
    wire [31:0] row_mismatch;

    RpSampler u_sampler (
        .clk(clk), .rst(rst || pass_rst), .sensor_ir(tbl_ir),
        .tok_valid(tok_valid), .tok_cam(tok_cam), .tok_sy(tok_sy), .tok_lx(tok_lx),
        .tok_ax(tok_ax), .tok_ay(tok_ay), .y0(y0),
        .ring_word(ring_word), .ring_sel(ring_sel), .ring_cam(ring_cam),
        .ring_pa(ring_pa), .ring_pb(ring_pb),
        .rw_we(rw_we), .rw_addr(rw_waddr), .rw_din(rw_din),
        .busy(sampler_busy), .row_mismatch_count(row_mismatch));

    RpRowWindow #(.RD_LAT(5)) u_rw (
        .clk(clk), .we(rw_we), .waddr(rw_waddr), .din(rw_din),
        .raddr(rw_raddr), .dout(rw_dout));

    RpEmitter #(.RW_RD_LAT(5), .ALPHA_Y_FILE(ALPHA_Y_FILE), .ALPHA_C_FILE(ALPHA_C_FILE),
                .IR_ALPHA_Y_FILE(IR_ALPHA_Y_FILE)) u_emit (
        .clk(clk), .rst(rst || pass_rst), .sensor_ir(tbl_ir), .start(pass_start), .cam_present(cam_present),
        .mark_ir(ir_mark_q),
        .rr_raddr(rr_raddr), .rr_rdata(rr_rdata),
        .y0_done_valid(y0_done_valid), .y0_done(y0_done), .all_done(all_done),
        .drop_valid(drop_valid), .drop_sy(drop_sy),
        .rw_raddr(rw_raddr), .rw_dout(rw_dout),
        .px_valid(px_valid), .px_ready(px_ready), .px_data(px_data),
        .frame_done(emit_frame_done), .done(emit_done),
        .sy_out(sy_out), .can_progress(emit_can_progress));
    assign frame_done = emit_frame_done;

    assign status_flags = {7'd0, tbl_ir, edge_seen_late, (row_mismatch != 0), q_ovf, alias_drop,
                           tbl_sat, tbl_busy, tbl_valid, all_done};
    assign dbg_word = {cs, sy_out[8:0], y0, rows_done[10:0], q_peak[11:0], visits[15:0], 1'b0};
endmodule
