`timescale 1ns/1ps
module tb_EoSyncPhaseControl;
    reg clk=0;always #5 clk=~clk;
    reg reset=1,locked=0,done=0;reg [8:0] target=0;
    wire enable,busy,fault;wire [8:0] current;
    EoSyncPhaseControl dut(clk,reset,locked,done,target,enable,current,busy,fault);
    integer delay_left=0,commands=0;reg previous_enable=0;
    always @(negedge clk)begin
        done=0;
        if(enable)begin
            if(previous_enable || delay_left!=0)$fatal(1,"overlapping MMCM command");
            delay_left=12;commands=commands+1;
        end else if(delay_left>0)begin
            delay_left=delay_left-1;
            if(delay_left==0)done=1;
        end
        previous_enable=enable;
    end
    task settle;
        integer guard;
        begin
            guard=0;
            repeat(2)@(posedge clk);
            while(busy && guard<10000)begin @(posedge clk);guard=guard+1;end
            if(busy || fault || current!=target)$fatal(1,"phase did not settle");
        end
    endtask
    initial begin
        repeat(4)@(negedge clk);reset=0;locked=1;
        target=28;settle();
        if(commands!=28)$fatal(1,"wrong number of phase commands");
        @(negedge clk);target=447;settle();
        if(commands!=447)$fatal(1,"wrong absolute phase");
        @(negedge clk);target=3;settle();
        if(commands!=451)$fatal(1,"wrong wrap-around");
        @(negedge clk);target=500;
        repeat(3)@(negedge clk);
        if(!fault)$fatal(1,"invalid target was not rejected");
        reset=1;target=0;repeat(3)@(negedge clk);
        if(fault || current!=0 || enable)$fatal(1,"reset did not recover");
        $display("PASS: phase targets, 12-cycle handshakes, one-cycle PSEN, wrap and invalid-target rejection");
        $finish;
    end
endmodule
