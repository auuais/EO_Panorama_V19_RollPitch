`timescale 1ns/1ps
// 1080p60-only clock: 148.5 MHz * 8 = 1188 MHz VCO, /8 = 148.5 MHz.
// Fine phase is 1/(56*1188 MHz), about 15.03 ps per tap, 448 taps/cycle.
// Qualified empirically using frozen pixels; not external interface signoff.
module EoSyncPhaseClock(
    input wire raw_clock,reference,reset,
    input wire [8:0] target,
    output wire sample_clock,
    output wire [8:0] current,
    output wire locked,busy,fault
);
    wire fb_raw,feedback,out_raw,lock_raw,done,enable,control_fault;
    reg [7:0] startup=0;
    always @(posedge reference)if(!(&startup))startup<=startup+1'b1;
    wire reset_mmcm=reset || !(&startup);
    (* ASYNC_REG="TRUE" *) reg [1:0] lock_sync=0;
    reg was_locked=0,lost_lock=0;
    always @(posedge reference)begin
        lock_sync<={lock_sync[0],lock_raw};
        if(reset_mmcm)begin was_locked<=0;lost_lock<=0;end
        else begin
            if(lock_sync[1])was_locked<=1;
            if(was_locked && !lock_sync[1])lost_lock<=1;
        end
    end
    assign locked=lock_sync[1];
    assign fault=control_fault|lost_lock;
    EoSyncPhaseControl u_control(reference,reset_mmcm,locked,done,target,enable,current,busy,control_fault);
    MMCME4_ADV #(.CLKIN1_PERIOD(6.734007),.DIVCLK_DIVIDE(1),
        .CLKFBOUT_MULT_F(8.0),.CLKOUT0_DIVIDE_F(8.0),
        .CLKOUT0_USE_FINE_PS("TRUE"),.CLKFBOUT_USE_FINE_PS("FALSE"),
        .COMPENSATION("AUTO"),.STARTUP_WAIT("FALSE")) u_mmcm(
        .CLKIN1(raw_clock),.CLKIN2(1'b0),.CLKINSEL(1'b1),
        .CLKFBOUT(fb_raw),.CLKFBIN(feedback),.CLKOUT0(out_raw),.LOCKED(lock_raw),
        .PSCLK(reference),.PSEN(enable),.PSINCDEC(1'b1),.PSDONE(done),
        .RST(reset_mmcm),.PWRDWN(1'b0),.DADDR(7'b0),.DCLK(1'b0),
        .DEN(1'b0),.DI(16'b0),.DWE(1'b0),.CDDCREQ(1'b0));
    BUFG u_feedback(.I(fb_raw),.O(feedback));
    BUFG u_sample(.I(out_raw),.O(sample_clock));
endmodule
