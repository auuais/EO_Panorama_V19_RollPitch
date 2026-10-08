`timescale 1ns/1ps
module trigger_rate_checker #(parameter RATE=30)(output reg done=0);
    reg clk=0; always #5 clk=~clk;
    wire trigger,valid;wire [63:0] metadata;wire [255:0] payload;wire [15:0] overruns;
    EoSyncTelemetry #(.TRIGGER_HZ(RATE)) dut(clk,10'd0,2560'd0,trigger,metadata,payload,valid,overruns);
    integer clocks=0,last_rise=-1,rises=0,falls=0,reported_rises=0;
    reg previous=0;
    reg [47:0] prior_report_rise=0;
    localparam PERIOD=27000000/RATE;
    always @(negedge clk) begin
        clocks=clocks+1;
        if(trigger && !previous) begin
            // Startup pulse is already high at time zero; count full later pulses.
            if(rises>=2 && clocks-last_rise!=PERIOD)$fatal(1,"wrong generated period %0d Hz",RATE);
            last_rise=clocks;rises=rises+1;
        end
        if(!trigger && previous) begin
            if(falls>=1 && clocks-last_rise!=54000)$fatal(1,"wrong generated high time %0d Hz",RATE);
            falls=falls+1;
        end
        previous=trigger;
        if(valid) begin
            if(metadata[55:48]!=10)$fatal(1,"unexpected event channel");
            if(metadata[63:56]==2) begin
                if(reported_rises && metadata[47:0]-prior_report_rise!=PERIOD)$fatal(1,"wrong timestamped period");
                prior_report_rise=metadata[47:0];reported_rises=reported_rises+1;
            end else if(metadata[63:56]==3) begin
                if(metadata[47:0]-prior_report_rise!=54000)$fatal(1,"wrong timestamped high time");
            end else $fatal(1,"unexpected event kind");
        end
        if(overruns)$fatal(1,"trigger telemetry overrun");
        if(clocks>2*PERIOD+55000) begin
            if(rises<3 || falls<3 || reported_rises<3)$fatal(1,"missing pulse evidence");
            done=1;
        end
    end
endmodule
module tb_EoSyncTriggerRates;
    wire done30,done60;
    trigger_rate_checker #(30) check30(done30);
    trigger_rate_checker #(60) check60(done60);
    initial begin
        wait(done30 && done60);
        $display("PASS: real-scale 30/60 Hz trigger periods, 2 ms high time and ILA edge timestamps");
        $finish;
    end
    initial begin #25000000;$fatal(1,"timeout");end
endmodule
