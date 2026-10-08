`timescale 1ns/1ps
module tb_Eo60Telemetry;
  reg ref_clk=0,pclk=0;
  always #18.5185 ref_clk=~ref_clk;
  always #3.367 pclk=~pclk;
  reg [1:0] toggles=0;
  reg [511:0] reports=0;
  wire trigger;wire [63:0] event_word;wire [31:0] pclk_hz,seconds;wire [7:0] trigger_edges;
  // One accelerated measurement window is 27000 reference cycles.
  Eo60Telemetry #(.REF_HZ(27000),.PULSE_CLOCKS(54)) dut
    (ref_clk,pclk,toggles,reports,trigger,event_word,pclk_hz,trigger_edges,seconds);
  integer cycles=0,last_rise=-1,rise=-1,pulses=0,packets=0,phase,kind;
  integer expected_kind[0:1];integer expected_seq[0:1];integer last_packet=-100;
  reg prev=0;reg [31:0] expected_value;
  function [255:0] payload(input integer seq,input integer phase);
    reg [255:0] r;
    begin
      r=0;r[31:0]='habc00000+seq+phase*256;r[63:32]='hdef00000+seq+phase*256;
      r[85:64]=2073600;r[97:86]=1080;r[113:98]=seq;r[125:114]=1125;
      r[133:126]=3;r[191:160]=2475000;r[207:192]=2200;r[223:208]=2200;
      payload=r;
    end
  endfunction
  always @(negedge ref_clk) begin
    cycles=cycles+1;
    if(trigger && !prev) begin
      if(last_rise>1 && cycles-last_rise!=450) $fatal(1,"trigger period");
      last_rise=cycles;rise=cycles;
    end
    if(!trigger && prev && rise>1) begin
      if(cycles-rise!=54) $fatal(1,"trigger high duration");
      pulses=pulses+1;
    end
    prev=trigger;
    if(event_word[63]) begin
      phase=event_word[62:60];kind=event_word[59:57];
      if(phase>1 || kind!=expected_kind[phase] || event_word[56:41]!=expected_seq[phase] || event_word[40:33]!=3)
        $fatal(1,"incoherent packet %h",event_word);
      if(cycles-last_packet<64) $fatal(1,"packet spacing");
      last_packet=cycles;
      case(kind)
        0:expected_value='habc00000+expected_seq[phase]+phase*256;
        1:expected_value='hdef00000+expected_seq[phase]+phase*256;
        2:expected_value=2073600;
        3:expected_value=(1080<<12)|1125;
        4:expected_value=event_word[31:0];
        5:expected_value=2475000;
        6:expected_value=(2200<<16)|2200;
        7:expected_value=0;
      endcase
      if(event_word[31:0]!==expected_value) $fatal(1,"payload mapping kind %d",kind);
      packets=packets+1;
      expected_kind[phase]=(kind+1)%8;
      if(kind==7)expected_seq[phase]=expected_seq[phase]+1;
    end
  end
  integer seq;
  initial begin
    expected_kind[0]=0;expected_kind[1]=0;expected_seq[0]=10;expected_seq[1]=10;
    for(seq=10;seq<13;seq=seq+1) begin
      repeat(2000) @(negedge pclk);
      reports={payload(seq,1),payload(seq,0)};toggles=~toggles;
      repeat(2000) @(negedge ref_clk);
    end
    wait(seconds==3);@(negedge ref_clk);
    if(pclk_hz<148244 || pclk_hz>148756 || trigger_edges!=60 || packets!=48 || pulses<170)
      $fatal(1,"telemetry final: pclk=%d trigger=%d packets=%d pulses=%d",pclk_hz,trigger_edges,packets,pulses);
    $display("PASS: asynchronous dual mailboxes, packet coherence, trigger period/width, PCLK frequency");$finish;
  end
  initial begin #4000000;$fatal(1,"timeout");end
endmodule
