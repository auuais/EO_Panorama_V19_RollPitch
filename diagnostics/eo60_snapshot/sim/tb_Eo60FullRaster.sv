`timescale 1ns/1ps
module tb_Eo60FullRaster;
    reg clk=0;always #3.367 clk=~clk;
    reg [7:0] y=128,c=64;
    wire toggle;wire [255:0] report;wire [7:0] live;
    Eo60RasterMonitor dut(clk,y,c,toggle,report,live);
    task word_out(input [7:0] yy,input [7:0] cc);
        begin @(negedge clk);y=yy;c=cc;end
    endtask
    task trs(input bit v,input bit h);
        reg [7:0] xy;
        begin xy={1'b1,1'b0,v,h,v^h,h,v,v^h};
            word_out(255,255);word_out(0,0);word_out(0,0);word_out(xy,xy);end
    endtask
    task line_out(input bit v);
        begin trs(v,1);repeat(272)word_out(128,64);trs(v,0);repeat(1920)word_out(128,64);end
    endtask
    integer row;
    initial begin
        for(row=0;row<1125;row=row+1)line_out(row<45);
        for(row=0;row<45;row=row+1)line_out(1);
        trs(0,1);repeat(10)word_out(128,64);
        if(toggle!==1 || report[85:64]!=2073600 || report[97:86]!=1080 ||
           report[125:114]!=1125 || report[133:126]!=3 || report[191:160]!=2475000 ||
           report[223:192]!={16'd2200,16'd2200} || report[157:134]!=0 ||
           report[31:0]!=32'h2e01a886 || report[63:32]!=32'h36ab6c3d)
           $fatal(1,"1080p60 reference mismatch %h",report);
        $display("PASS: complete 1080p60 geometry and independently precomputed full/ROI CRCs");$finish;
    end
    initial begin #20000000;$fatal(1,"timeout");end
endmodule
