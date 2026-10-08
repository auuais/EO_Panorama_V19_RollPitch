`timescale 1ns/1ps
module Eo60Telemetry #(
    parameter REF_HZ=27000000, TRIGGER_HZ=60, PULSE_CLOCKS=54000
)(
    input wire ref_clk,pclk,
    input wire [1:0] toggles,
    input wire [511:0] reports,
    output wire trigger,
    output reg [63:0] event_word=0,
    output reg [31:0] pclk_hz=0,
    output reg [7:0] trigger_edges=0,
    output reg [31:0] seconds=0
);
    localparam PERIOD=REF_HZ/TRIGGER_HZ;
    reg [31:0] trigger_count=0;
    always @(posedge ref_clk) trigger_count<=trigger_count==PERIOD-1?0:trigger_count+1'b1;
    assign trigger=trigger_count<PULSE_CLOCKS;
    // Divide before crossing domains. Rising edges of bit 7 are 256 PCLKs
    // apart; no asynchronous multi-bit frequency counter is sampled.
    reg [7:0] pclk_div=0;
    always @(posedge pclk) pclk_div<=pclk_div+1'b1;
    (* ASYNC_REG="TRUE" *) reg [2:0] pclk_sync=0;
    reg [31:0] window_count=0,clock_edges=0;
    reg [7:0] trig_acc=0;reg prev_trigger=0;
    wire clock_edge=pclk_sync[1]&&!pclk_sync[2];
    wire trigger_edge=trigger&&!prev_trigger;
    always @(posedge ref_clk) begin
        pclk_sync<={pclk_sync[1:0],pclk_div[7]};prev_trigger<=trigger;
        if(window_count==REF_HZ-1) begin
            window_count<=0;seconds<=seconds+1'b1;
            pclk_hz<=(clock_edges+clock_edge)<<8;clock_edges<=0;
            trigger_edges<=trig_acc+trigger_edge;trig_acc<=0;
        end else begin
            window_count<=window_count+1'b1;
            clock_edges<=clock_edges+clock_edge;trig_acc<=trig_acc+trigger_edge;
        end
    end
    (* ASYNC_REG="TRUE" *) reg [1:0] t1=0,t2=0,t3=0;
    (* ASYNC_REG="TRUE" *) reg [511:0] r1=0,r2=0;
    reg [1:0] seen=0;
    reg phase=0,busy=0,held_toggle=0;
    reg [2:0] kind=0;
    reg [5:0] cooldown=0;
    reg [255:0] held=0;
    reg [31:0] tick=0,held_tick=0;
    reg [31:0] value;
    always @* case(kind)
        0:value=held[31:0];1:value=held[63:32];2:value={10'd0,held[85:64]};
        3:value={8'd0,held[97:86],held[125:114]};4:value=held_tick;
        5:value=held[191:160];6:value=held[223:192];
        default:value={8'd0,held[157:134]};
    endcase
    always @(posedge ref_clk) begin
        t1<=toggles;t2<=t1;t3<=t2;r1<=reports;r2<=r1;tick<=tick+1'b1;
        event_word[63]<=0;
        if(cooldown!=0) cooldown<=cooldown-1'b1;
        else if(busy) begin
            event_word<={1'b1,2'd0,phase,kind,held[113:98],held[133:126],1'b0,value};
            cooldown<=63;
            if(kind==7) begin seen[phase]<=held_toggle;busy<=0;kind<=0;phase<=~phase;end
            else kind<=kind+1'b1;
        end else if(t3[phase]!=seen[phase]) begin
            held<=phase?r2[511:256]:r2[255:0];held_toggle<=t3[phase];held_tick<=tick;busy<=1;kind<=0;
        end else phase<=~phase;
    end
endmodule
