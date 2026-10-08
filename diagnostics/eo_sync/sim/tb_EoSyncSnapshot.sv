`timescale 1ns/1ps
module tb_EoSyncSnapshot;
 reg clk=0;always #3.367 clk=~clk;
 reg [7:0] y=0;wire [63:0] data;wire [31:0] meta;wire [1:0] control;
 EoSyncSnapshot #(.WIDTH(1540)) dut(clk,y,data,meta,control);
 integer f,r,x,b,packets=0,starts=0,fs,rs,g,expected;
 task emit(input [7:0] v);begin @(negedge clk);y=v;end endtask
 task trs(input bit v,input bit h);
  reg [7:0] xy;begin xy={1'b1,1'b0,v,h,v^h,h,v,v^h};emit(255);emit(0);emit(0);emit(xy);end
 endtask
 always @(posedge clk)begin
  #1;
  if(control[0])begin
   fs=meta[31:17];rs=meta[16:7];g=meta[6:0];
   if(fs<1 || fs>2 || rs>=448 || g>=64)$fatal(1,"bad crop coordinates %h",meta);
   for(b=0;b<8;b=b+1)begin
    expected=(fs-1)*17+(128+rs*2)*3+512+g*16+b*2;
    if(data[63-b*8-:8]!==expected[7:0])$fatal(1,"wrong pixel meta=%h byte=%0d",meta,b);
   end
   if(control[1]!==((rs==0)&&(g==0)))$fatal(1,"bad SOF");
   packets=packets+1;if(control[1])starts=starts+1;
  end
 end
 initial begin
  repeat(8)emit(16);
  for(f=0;f<2;f=f+1)begin
   trs(1,1);repeat(16)emit(128);trs(1,0);repeat(1540)emit(16);
   for(r=0;r<1030;r=r+1)begin
    trs(0,1);repeat(16)emit(128);trs(0,0);
    for(x=0;x<1540;x=x+1)emit(f*17+r*3+x);
   end
  end
  trs(1,1);repeat(32)emit(16);
  if(packets!=57344 || starts!=2)$fatal(1,"counts packets=%0d starts=%0d",packets,starts);
  $display("PASS: two 512x448 OSD crops, exact original pixel coordinates, packing, SOF and packet counts");$finish;
 end
endmodule
