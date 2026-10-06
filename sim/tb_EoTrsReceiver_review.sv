`timescale 1ns/1ps
// Exercise the actual receiver with synthetic valid TRS words.
// IBUF is an identity model; no board or FPGA programming is involved.
module IBUF(input wire I, output wire O);
    assign O=I;
endmodule
module tb_EoTrsReceiver_review;
    reg clk=0;
    always #5 clk=~clk;
    reg [7:0] y=8'h80;
    wire tgl, fbit;
    wire [11:0] lines;
    Kintex_top_1cam_1ch dut(.FPGA_RESET(1'b1),.CAM1_PCLK(clk),
        .CAM1_YOUT(y),.CAM1_COUT(8'h80),.STROBE_OUT0(1'b0),
        .trs_frame_tgl(tgl),.trs_lines(lines),.trs_f(fbit));
    task byte_out(input [7:0] b);
        begin @(negedge clk); y=b; end
    endtask
    task trs(input f,input v,input h);
        begin
            byte_out(8'hff); byte_out(0); byte_out(0);
            byte_out({1'b1,f,v,h,v^h,f^h,f^v,f^v^h});
        end
    endtask
    task raster(input integer blank_lines,input f);
        integer k;
        begin
            for(k=0;k<1125;k=k+1) begin
                trs(f,k<blank_lines,1'b1);
                repeat(8) byte_out(8'h80);
                trs(f,k<blank_lines,1'b0);
                repeat(24) byte_out(8'h80);
            end
        end
    endtask
    task check(input f);
        begin
            if(lines!==1125 || fbit!==f)
                $fatal(1,"Unexpected lines/F: %0d %b",lines,fbit);
        end
    endtask
    initial begin
        repeat(5) byte_out(8'h80);
        repeat(3) raster(45,0);
        check(0);
        $display("PASS: 1125 total, 1080 active -> reports 1125 lines, F=0");
        repeat(3) raster(125,0);
        check(0);
        $display("PASS: 1125 total, 1000 active -> also reports 1125 lines, F=0");
        raster(125,1); check(1);
        raster(125,0); check(0);
        $display("PASS: receiver exposes alternating frame-sampled F");
        $finish;
    end
    initial begin #5000000; $fatal(1,"timeout"); end
endmodule
