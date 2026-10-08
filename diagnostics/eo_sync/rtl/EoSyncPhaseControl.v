`timescale 1ns/1ps
// MMCM fine-phase command sequencer. One output cycle = 8*56 = 448 taps.
// PSEN and PSDONE are synchronous to the same 27 MHz PSCLK.
module EoSyncPhaseControl(
    input wire clk,reset,locked,done,
    input wire [8:0] target,
    output reg enable=0,
    output reg [8:0] current=0,
    output wire busy,
    output reg fault=0
);
    reg waiting=0;
    reg [15:0] watchdog=0;
    assign busy=waiting || current!=target || !locked;
    always @(posedge clk) begin
        enable<=0;
        if(reset || !locked) begin
            current<=0;waiting<=0;watchdog<=0;
            if(reset)fault<=0;
        end else if(!fault) begin
            if(target>=448)fault<=1;
            else if(waiting) begin
                if(done)begin
                    current<=current==447?0:current+1'b1;
                    waiting<=0;watchdog<=0;
                end else if(watchdog==65535)fault<=1;
                else watchdog<=watchdog+1'b1;
            end else if(current!=target)begin
                enable<=1;waiting<=1;watchdog<=0;
            end
        end
    end
endmodule
