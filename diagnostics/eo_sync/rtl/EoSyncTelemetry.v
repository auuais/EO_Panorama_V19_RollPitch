`timescale 1ns/1ps
// Timestamp every channel independently before round-robin serialization.
// Camera channel 2*n is rising, 2*n+1 falling; n=0 means physical camera 2.
// Metadata [63:56]=kind (1=frame,2=trigger rise,3=trigger fall),
// [55:48]=channel, [47:0]=common 27 MHz tick. Payload is the raster report.
module EoSyncTelemetry #(
    parameter REF_HZ=27000000, TRIGGER_HZ=60, PULSE_CLOCKS=54000,
    parameter CHANNELS=10
)(
    input wire clk,
    input wire [CHANNELS-1:0] toggles,
    input wire [CHANNELS*256-1:0] reports,
    output wire trigger,
    output reg [63:0] metadata=0,
    output reg [255:0] payload=0,
    output reg valid=0,
    output reg [15:0] overruns=0
);
    localparam PERIOD=REF_HZ/TRIGGER_HZ;
    reg [31:0] trigger_count=0;
    reg [47:0] tick=0;
    reg previous_trigger=0;
    assign trigger=trigger_count<PULSE_CLOCKS;
    (* ASYNC_REG="TRUE" *) reg [CHANNELS-1:0] t1=0,t2=0,t3=0;
    (* ASYNC_REG="TRUE" *) reg [CHANNELS*256-1:0] r1=0,r2=0;
    reg [CHANNELS-1:0] seen=0;
    reg [CHANNELS:0] pending=0;
    reg [47:0] stamps[0:CHANNELS];
    reg [255:0] held[0:CHANNELS];
    reg [7:0] kinds[0:CHANNELS];
    reg [7:0] select=0;
    integer i;
    initial for(i=0;i<=CHANNELS;i=i+1) begin
        stamps[i]=0;held[i]=0;kinds[i]=0;
    end
    always @(posedge clk) begin
        tick<=tick+1'b1;
        trigger_count<=trigger_count==PERIOD-1?0:trigger_count+1'b1;
        previous_trigger<=trigger;
        t1<=toggles;t2<=t1;t3<=t2;r1<=reports;r2<=r1;
        valid<=0;
        select<=select==CHANNELS?0:select+1'b1;
        if(pending[select]) begin
            metadata<={kinds[select],select,stamps[select]};
            payload<=held[select];valid<=1;pending[select]<=0;
        end
        // Later nonblocking assignments deliberately retain a new event if
        // it arrives on the same clock that the old one is drained.
        for(i=0;i<CHANNELS;i=i+1) begin
            if(t3[i]!=seen[i]) begin
                stamps[i]<=tick;held[i]<=r2[i*256+:256];kinds[i]<=1;
                pending[i]<=1;seen[i]<=t3[i];
                if(pending[i] && select!=i && overruns!=16'hffff)
                    overruns<=overruns+1'b1;
            end
        end
        if(trigger!=previous_trigger) begin
            stamps[CHANNELS]<=tick;held[CHANNELS]<=0;
            kinds[CHANNELS]<=trigger?2:3;pending[CHANNELS]<=1;
            if(pending[CHANNELS] && select!=CHANNELS && overruns!=16'hffff)
                overruns<=overruns+1'b1;
        end
    end
endmodule
