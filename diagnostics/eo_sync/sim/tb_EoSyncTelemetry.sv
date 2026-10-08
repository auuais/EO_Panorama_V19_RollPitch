`timescale 1ns/1ps
module tb_EoSyncTelemetry;
    reg clk=0;always #5 clk=~clk;
    reg [9:0] toggles=0;
    reg [2559:0] reports=0;
    wire trigger,valid;wire [63:0] metadata;wire [255:0] payload;wire [15:0] overruns;
    EoSyncTelemetry #(.REF_HZ(10000),.TRIGGER_HZ(10),.PULSE_CLOCKS(20)) dut(clk,toggles,reports,trigger,metadata,payload,valid,overruns);
    reg [47:0] first_stamp=0;integer count=0;reg [9:0] received=0;
    integer i;
    always @(negedge clk) if(valid && metadata[63:56]==1) begin
        if(received[metadata[55:48]])$fatal(1,"duplicate channel");
        received[metadata[55:48]]=1;count=count+1;
        if(count==1)first_stamp=metadata[47:0];
        if(metadata[47:0]!=first_stamp)$fatal(1,"serialization changed simultaneous timestamps");
        if(payload!=metadata[55:48]+100)$fatal(1,"payload/channel mismatch");
    end
    initial begin
        repeat(30)@(negedge clk);
        for(i=0;i<10;i=i+1)reports[i*256+:256]=i+100;
        toggles=10'h3ff;
        repeat(40)@(negedge clk);
        if(count!=10 || received!=10'h3ff || overruns!=0)$fatal(1,"missing report/overrun");
        $display("PASS: ten simultaneous camera/phase events retain identical timestamps and independent payloads");
        $finish;
    end
endmodule
