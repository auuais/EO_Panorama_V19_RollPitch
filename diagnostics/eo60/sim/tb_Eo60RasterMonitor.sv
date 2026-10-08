`timescale 1ns/1ps
module tb_Eo60RasterMonitor;
    reg clk=0;always #3.367 clk=~clk;
    reg [7:0] y=128,c=64;
    wire toggle;wire [255:0] report;wire [7:0] live;
    Eo60RasterMonitor #(.WIDTH(16),.HEIGHT(4),.LINE_CLOCKS(32),.TOTAL_LINES(6),
        .ROI_X(4),.ROI_Y(1),.ROI_W(4),.ROI_H(2)) dut(clk,y,c,toggle,report,live);
    integer count=0;reg last=0;reg [31:0] crc0,roi0;
    always @(negedge clk) if(toggle!=last) begin
        last=toggle;
        if(count<3) begin
            if(report[133:126]!==8'h03 || report[191:160]!=192 || report[223:192]!={16'd32,16'd32})
                $fatal(1,"Valid geometry failed frame %d: %h",count,report);
            if(count==0) begin crc0=report[31:0];roi0=report[63:32];end
            if(count==1 && (report[31:0]!=crc0 || report[63:32]!=roi0)) $fatal(1,"Repeat not preserved");
            if(count==2 && (report[31:0]==crc0 || report[63:32]==roi0)) $fatal(1,"Content change missed");
        end else if(report[127]) $fatal(1,"Malformed frame accepted %d",count);
        count=count+1;
    end
    task word_out(input [7:0] yy,input [7:0] cc);
        begin @(negedge clk);#0.1;y=yy;c=cc;end
    endtask
    task trs(input bit v,input bit h,input bit broken);
        reg [7:0] xy;
        begin
            xy={1'b1,1'b0,v,h,v^h,h,v,v^h};if(broken)xy=xy^8'h01;
            word_out(255,255);word_out(0,0);word_out(0,0);word_out(xy,xy);
        end
    endtask
    task raster(input integer id,input integer fault);
        integer row,col;
        begin for(row=0;row<6;row=row+1) begin
            trs(row<2,1,fault==1 && row==3);
            repeat(8) word_out(128,64);
            if(fault==2 && row==4) word_out(128,64);
            trs(row<2,0,0);
            for(col=0;col<16;col=col+1)word_out(32+row*16+col+id,128+id);
        end end
    endtask
    initial begin
        raster(0,0);raster(0,0);raster(1,0);raster(1,1);raster(1,2);raster(1,0);
        repeat(20)word_out(128,64);
        if(count!=5)$fatal(1,"Missing reports %d",count);
        $display("PASS: repeats, changed payload, invalid XY, bad line/frame length rejected at 148.5 MHz");$finish;
    end
    initial begin #20000;$fatal(1,"timeout");end
endmodule
