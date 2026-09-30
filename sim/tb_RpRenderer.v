`timescale 1ns/1ps
// Full source-driven renderer against model/golden.py.
//
// The replay is behavioural but speaks EoV19DdrReplay's BEAT_OUT protocol:
// frame_edge when source_need_valid rises, beats of the fetch window row by
// row (one cycle valid, BEAT_SPACING apart, a random fetch delay per batch of
// 8), row_done after each row, and a hold at row end while row >= need_row.
// Frames use golden.synthetic_frames()'s texture, computed here.
//
// Each case writes its output raster to sim_out/rp_<case>.hex; compare with
//   python model/compare_rp_tb.py
module tb_RpRenderer;
    parameter ROOT = "E:/Xylinx/EO_Panorama_V19_RollPitch";
    parameter OUTDIR = "E:/Xylinx/EO_Panorama_V19_RollPitch/sim_out";
    parameter integer BEAT_SPACING = 4;
    parameter integer MARK_IR = 1;           // compare_rp_tb.py --no-ir-mark when 0

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg          start_copy = 1'b0;
    reg  [5:0]   cam_present = 6'h3F;
    reg  [95:0]  roll_cd = 96'd0, pitch_cd = 96'd0;
    reg          sensor_ir = 1'b0;
    wire         px_valid, frame_done, frames_valid;
    reg          px_ready = 1'b1;
    wire [15:0]  px_data;
    wire         need_valid;
    wire [10:0]  need_row, start_row;
    wire [6:0]   fetch_lo, fetch_hi, wr_beat_lo, wr_beat_hi;
    wire [10:0]  wr_row_lo, wr_row_hi;
    wire         tables_valid, tables_busy;
    wire [31:0]  build_count;
    wire [15:0]  status_flags;
    wire [63:0]  dbg_word;

    reg          frame_edge = 1'b0;
    reg          beat_valid = 1'b0;
    reg  [10:0]  beat_row = 11'd0;
    reg  [6:0]   beat_idx = 7'd0;
    reg  [1535:0] beat_data = 0;
    reg          row_done = 1'b0;
    reg  [10:0]  row_done_row = 11'd0;

    RpRenderer #(
        .SETTLE_CYCLES(1),
        .IR_OFFSET_MARK(MARK_IR),
        .RUN_ROM_FILE({ROOT, "/assets/rowruns/eo_v19_render_runs.mem"}),
        .IR_RUN_ROM_FILE({ROOT, "/assets/rowruns/ir_v19_render_runs.mem"}),
        .ANGLE_ROM_FILE({ROOT, "/assets/rollpitch/eo_rp_angle.mem"}),
        .IR_ANGLE_ROM_FILE({ROOT, "/assets/rollpitch/ir_rp_angle.mem"}),
        .ALPHA_Y_FILE({ROOT, "/assets/rowruns/eo_v19_alpha_y.mem"}),
        .ALPHA_C_FILE({ROOT, "/assets/rowruns/eo_v19_alpha_c.mem"}),
        .IR_ALPHA_Y_FILE({ROOT, "/assets/rowruns/ir_v19_alpha_y.mem"})
    ) dut (
        .rst_n(rst_n), .clk(clk), .sensor_ir(sensor_ir), .start_copy(start_copy), .cam_present(cam_present),
        .source_frame_reset(frame_edge),
        .beat_valid(beat_valid), .beat_row(beat_row), .beat_idx(beat_idx), .beat_data(beat_data),
        .row_done(row_done), .row_done_row(row_done_row),
        .eo_roll_cd(roll_cd), .eo_pitch_cd(pitch_cd), .ir_roll_cd(roll_cd), .ir_pitch_cd(pitch_cd),
        .px_valid(px_valid), .px_ready(px_ready), .px_data(px_data),
        .frame_done(frame_done), .frames_valid(frames_valid),
        .source_need_valid(need_valid), .source_need_row(need_row), .source_start_row(start_row),
        .fetch_beat_lo(fetch_lo), .fetch_beat_hi(fetch_hi),
        .wr_row_lo(wr_row_lo), .wr_row_hi(wr_row_hi), .wr_beat_lo(wr_beat_lo), .wr_beat_hi(wr_beat_hi),
        .tables_valid(tables_valid), .tables_busy(tables_busy), .build_count(build_count),
        .status_flags(status_flags), .dbg_word(dbg_word));

    //------------------------------------------------------------------------
    // Synthetic source frames (golden.synthetic_frames, seed 1)
    //------------------------------------------------------------------------
    function [15:0] src_px;
        input integer cam, x, y;
        integer luma, chroma;
        begin
            luma   = (x*7 + y*13 + cam*41 + ((x*y) >> 6) + (x >> 3)*(y >> 4)*(1 + cam)) & 255;
            chroma = (x*3 + y*5 + cam*17 + ((x ^ (y << 1)) >> 2)) & 255;
            src_px = {luma[7:0], chroma[7:0]};
        end
    endfunction

    //------------------------------------------------------------------------
    // Behavioural BEAT_OUT replay
    //------------------------------------------------------------------------
    integer rp_row, rp_beat, rp_cam, rp_p, rp_wait;
    reg     rp_running = 1'b0;
    integer seed = 7;
    initial begin : replay
        forever begin
            @(negedge clk);
            if (need_valid && !rp_running && start_copy) begin
                rp_running = 1'b1;
                frame_edge = 1'b1;
                @(negedge clk) frame_edge = 1'b0;
                rp_row = start_row;
                while (rp_running) begin
                    rp_beat = 0;
                    while (rp_beat < (sensor_ir ? 20 : 120)) begin
                        if (sensor_ir || (rp_beat >= fetch_lo && rp_beat <= fetch_hi + 7)) begin
                            if ((rp_beat % (sensor_ir ? 4 : 8)) == 0) begin
                                rp_wait = ($random(seed) & 15);
                                repeat (rp_wait) @(negedge clk);
                            end
                            beat_row = rp_row; beat_idx = rp_beat;
                            for (rp_cam = 0; rp_cam < 6; rp_cam = rp_cam + 1)
                                if (sensor_ir)
                                    for (rp_p = 0; rp_p < 32; rp_p = rp_p + 1)
                                        beat_data[rp_cam*256 + rp_p*8 +: 8] = src_px(rp_cam, rp_beat*32 + rp_p, rp_row) >> 8;
                                else
                                    for (rp_p = 0; rp_p < 16; rp_p = rp_p + 1)
                                        beat_data[rp_cam*256 + rp_p*16 +: 16] = src_px(rp_cam, rp_beat*16 + rp_p, rp_row);
                            beat_valid = 1'b1;
                            @(negedge clk) beat_valid = 1'b0;
                            repeat ((sensor_ir ? 8 : BEAT_SPACING) - 1) @(negedge clk);
                        end
                        rp_beat = rp_beat + 1;
                    end
                    row_done = 1'b1; row_done_row = rp_row;
                    @(negedge clk) row_done = 1'b0;
                    // LINE_END: hold while the renderer has not asked for more
                    while (rp_running && (!need_valid || rp_row >= need_row)) begin
                        @(negedge clk);
                        if (!start_copy) rp_running = 1'b0;
                    end
                    if (rp_row == (sensor_ir ? 511 : 1079)) begin
                        while (start_copy) @(negedge clk);
                        rp_running = 1'b0;
                    end
                    rp_row = rp_row + 1;
                    if (!start_copy) rp_running = 1'b0;
                end
            end
        end
    end

    //------------------------------------------------------------------------
    // Output capture with random back-pressure
    //------------------------------------------------------------------------
    integer fout = 0;
    integer npx = 0;
    always @(negedge clk) px_ready <= (($random(seed) & 7) != 0);
    always @(posedge clk) begin
        if (px_valid && px_ready) begin
            if (fout != 0) $fwrite(fout, "%04x\n", px_data);
            npx = npx + 1;
        end
    end

    task run_pass;
        input [8*16-1:0] name;
        input            ir;
        input [95:0] roll, pitch;
        input [5:0]  present;
        integer t0, t;
        begin
            @(negedge clk);
            sensor_ir = ir; roll_cd = roll; pitch_cd = pitch; cam_present = present;
            fout = $fopen({OUTDIR, "/rp_", name, ".hex"}, "w");
            npx = 0;
            repeat (20) @(negedge clk);
            start_copy = 1'b1;
            t0 = $time;
            t = 0;
            while (!frame_done) begin
                @(posedge clk); t = t + 1;
                if (t > 20000000) begin
                    $display("FAIL %0s: no frame_done, npx=%0d dbg=%h flags=%h", name, npx, dbg_word, status_flags);
                    $finish;
                end
            end
            @(negedge clk) start_copy = 1'b0;
            $fclose(fout); fout = 0;
            $display("%0s: %0d cycles, %0d px, flags=%h builds=%0d Y=%0d..%0d fetch=%0d..%0d wr_rows=%0d..%0d wr_beats=%0d..%0d",
                     name, t, npx, status_flags, build_count, dut.ylo, dut.yhi, fetch_lo, fetch_hi,
                     wr_row_lo, wr_row_hi, wr_beat_lo, wr_beat_hi);
            if (npx != (ir ? 3576 : 3840)*480) $display("FAIL %0s: pixel count %0d", name, npx);
        end
    endtask

    function [95:0] v6;
        input signed [15:0] a, b, c, d, e, f;
        begin v6 = {f, e, d, c, b, a}; end
    endfunction

    initial begin
        repeat (10) @(negedge clk);
        rst_n = 1'b1;
        run_pass("eo_zero",    0, v6(0,0,0,0,0,0), v6(0,0,0,0,0,0), 6'h3F);
        run_pass("ir_zero",    1, v6(0,0,0,0,0,0), v6(0,0,0,0,0,0), 6'h3F);
        run_pass("eo_mixed",   0, v6(150,-300,1000,-1000,0,777), v6(-1000,250,0,1000,-60,5), 6'h3F);
        run_pass("ir_mixed",   1, v6(150,-300,1000,-1000,0,777), v6(-1000,250,0,1000,-60,5), 6'h3F);
        run_pass("ir_alt10",   1, v6(1000,-1000,1000,-1000,1000,-1000), v6(1000,-1000,1000,-1000,1000,-1000), 6'h3F);
        run_pass("ir_absent2", 1, v6(0,0,0,0,0,0), v6(0,0,0,0,0,0), 6'b111011);
        run_pass("ir_absent3", 1, v6(150,-300,1000,-1000,0,777), v6(-1000,250,0,1000,-60,5), 6'b110111);
        run_pass("eo_absent",  0, v6(150,-300,1000,-1000,0,777), v6(-1000,250,0,1000,-60,5), 6'b110111);
        $display("DONE tb_RpRenderer");
        $finish;
    end
endmodule
