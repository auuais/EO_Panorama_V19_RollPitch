`timescale 1ns/1ps
module tb_Eo60InputSampler;
  reg pclk=0;always #3.367 pclk=~pclk;
  reg [15:0] data=0;wire [15:0] rising,falling;
  Eo60InputSampler dut(pclk,data,rising,falling);
  reg [15:0] last_rise=0,last_fall=0,expect_rise,expect_fall;
  integer checked=0;
  // Drive well away from both edges, with a distinct word each half-cycle.
  always @(pclk) #1 data=data+16'h0101;
  always @(negedge pclk) last_fall=data;
  always @(posedge pclk) begin
    expect_rise=last_rise;expect_fall=last_fall;last_rise=data;
    #0.5;
    if($time>120) begin
      if(rising!==expect_rise || falling!==expect_fall) $fatal(1,"SDR sample alignment");
      checked=checked+1;
      if(checked==100) begin $display("PASS: vendor FDRE both-edge SDR sampling and pipeline alignment");$finish;end
    end
  end
endmodule
