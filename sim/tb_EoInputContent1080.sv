`timescale 1ns/1ps
module tb_EoInputContent1080;
    reg clk=0;
    always #5 clk=~clk;
    reg [7:0] y=128,c=64;
    wire toggle;
    wire [159:0] report;
    EoInputContentMon dut(clk,y,c,toggle,report);
    task word_out(input [7:0] yy);
        begin @(negedge clk);y=yy;end
    endtask
    task trs(input v,input h);
        begin word_out(255);word_out(0);word_out(0);
            word_out({1'b1,1'b0,v,h,v^h,h,v,v^h});end
    endtask
    task line_out(input v);
        begin trs(v,1);repeat(272) word_out(128);trs(v,0);repeat(1920) word_out(128);end
    endtask
    integer i;
    initial begin
        for(i=0;i<1125;i=i+1) line_out(i<45);
        for(i=0;i<45;i=i+1) line_out(1);
        trs(0,1);repeat(10) word_out(128);
        if(toggle!==1 || report[85:64]!=2073600 || report[97:86]!=1080 ||
           report[125:114]!=1125 || report[133:126]!=3 ||
           report[31:0]!=32'h2e01a886 || report[63:32]!=32'h36ab6c3d)
            $fatal(1,"Full raster mismatch %h",report);
        $display("PASS: default 1920x1080 active samples, 1125 lines, full/ROI reference CRCs");
        $finish;
    end
    initial begin #50000000; $fatal(1,"timeout");end
endmodule
