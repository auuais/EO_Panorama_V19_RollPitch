`timescale 1ns/1ps
// Dedicated JTAG-only camera-2 input experiment. No DDR or video renderer.
// Camera 2 is board signal CAM1. All follower trigger outputs keep 60 Hz.
module Eo60InputTestTop # (parameter TRIGGER_HZ=60)(
    input wire osc27_p,osc27_n,CAM1_PCLK,
    input wire [7:0] CAM1_YOUT,CAM1_COUT,
    output wire TRIG_IN1,TRIG_IN2,TRIG_IN3,TRIG_IN4,TRIG_IN5
);
    wire ref_in,ref_clk,pclk_in,pclk;
    IBUFDS u_ref_input(.I(osc27_p),.IB(osc27_n),.O(ref_in));
    BUFG u_ref_clock(.I(ref_in),.O(ref_clk));
    IBUF u_cam_clock_input(.I(CAM1_PCLK),.O(pclk_in));
    BUFG u_cam_clock(.I(pclk_in),.O(pclk));
    wire [15:0] rising,falling;
    Eo60InputSampler u_sampler(pclk,{CAM1_YOUT,CAM1_COUT},rising,falling);
    wire [255:0] report_rising,report_falling;
    wire toggle_rising,toggle_falling;
    wire [7:0] live_rising,live_falling;
    Eo60RasterMonitor u_rising(pclk,rising[15:8],rising[7:0],toggle_rising,report_rising,live_rising);
    Eo60RasterMonitor u_falling(pclk,falling[15:8],falling[7:0],toggle_falling,report_falling,live_falling);
    wire trigger;
    (* MARK_DEBUG="TRUE" *) wire [63:0] eo60_event_word;
    (* MARK_DEBUG="TRUE" *) wire [31:0] eo60_pclk_hz,eo60_seconds;
    (* MARK_DEBUG="TRUE" *) wire [7:0] eo60_trigger_edges;
    Eo60Telemetry #(.TRIGGER_HZ(TRIGGER_HZ)) u_telemetry(
        ref_clk,pclk,{toggle_falling,toggle_rising},{report_falling,report_rising},
        trigger,eo60_event_word,eo60_pclk_hz,eo60_trigger_edges,eo60_seconds);
    assign {TRIG_IN5,TRIG_IN4,TRIG_IN3,TRIG_IN2,TRIG_IN1}={5{trigger}};
    // Probe4 is a protocol/version signature. Decoder refuses other images.
    eo60_ila_ref u_ila_ref(.clk(ref_clk),.probe0(eo60_event_word),
        .probe1(eo60_pclk_hz),.probe2(eo60_trigger_edges),.probe3(eo60_seconds),.probe4(32'hE0600001));
    eo60_ila_raw u_ila_raw(.clk(pclk),.probe0(rising),.probe1(falling),
        .probe2({live_falling,live_rising}));
endmodule
