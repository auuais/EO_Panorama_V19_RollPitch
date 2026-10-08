`timescale 1ns/1ps
// Two SDR sampling paths. HD-bank IDDRE1 has an 8 ns minimum period on this
// part and cannot be used at 148.5 MHz. Keep these registers in the fabric;
// time both external apertures and the falling-to-rising half-cycle paths.
// Both SDR sampling choices are retained. Never select a phase from CRC
// novelty alone: geometry, sync quality and repeatability must qualify it.
module Eo60InputSampler(
    input wire pclk,
    input wire [15:0] data,
    output wire [15:0] rising,
    output wire [15:0] falling
);
    genvar b;
    generate for (b=0;b<16;b=b+1) begin : g_bit
        wire rise_q,fall_q;
        (* IOB="FALSE", DONT_TOUCH="TRUE" *)
        FDRE #(.INIT(1'b0)) u_rise(.C(pclk),.CE(1'b1),.R(1'b0),.D(data[b]),.Q(rise_q));
        (* IOB="FALSE", DONT_TOUCH="TRUE" *)
        FDRE #(.INIT(1'b0),.IS_C_INVERTED(1'b1)) u_fall(.C(pclk),.CE(1'b1),.R(1'b0),.D(data[b]),.Q(fall_q));
        FDRE #(.INIT(1'b0)) u_rise_align(.C(pclk),.CE(1'b1),.R(1'b0),.D(rise_q),.Q(rising[b]));
        FDRE #(.INIT(1'b0)) u_fall_align(.C(pclk),.CE(1'b1),.R(1'b0),.D(fall_q),.Q(falling[b]));
    end endgenerate
endmodule
