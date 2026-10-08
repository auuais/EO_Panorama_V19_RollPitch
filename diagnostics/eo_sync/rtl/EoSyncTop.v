`timescale 1ns/1ps
module EoSyncTop #(parameter PHASE_CLOCK=0)(
    input wire osc27_p,osc27_n,
    input wire CAM1_PCLK,
    input wire [7:0] CAM1_YOUT,CAM1_COUT,
    output wire TRIG_IN1,
    input wire CAM2_PCLK,
    input wire [7:0] CAM2_YOUT,CAM2_COUT,
    output wire TRIG_IN2,
    input wire CAM3_PCLK,
    input wire [7:0] CAM3_YOUT,CAM3_COUT,
    output wire TRIG_IN3,
    input wire CAM4_PCLK,
    input wire [7:0] CAM4_YOUT,CAM4_COUT,
    output wire TRIG_IN4,
    input wire CAM5_PCLK,
    input wire [7:0] CAM5_YOUT,CAM5_COUT,
    output wire TRIG_IN5
);
    wire ref_in,ref_clk; IBUFDS u_ref(.I(osc27_p),.IB(osc27_n),.O(ref_in)); BUFG u_ref_clock(.I(ref_in),.O(ref_clk));
    wire [9:0] toggles;wire [2559:0] reports;wire trigger;
    // Select only the OSD observer's input edge. Both timing/CRC paths always run.
    // VIO bit 0 selects physical camera 2; 0=rising, 1=falling.
    wire [4:0] snapshot_falling;
    wire [44:0] phase_targets,phase_current;
    wire phase_reset;
    wire [4:0] phase_locked,phase_busy,phase_fault;
    eo_sync_vio u_snapshot_select(.clk(ref_clk),.probe_out0(snapshot_falling),
        .probe_out1(phase_targets),.probe_out2(phase_reset),
        .probe_in0({phase_fault,phase_busy,phase_locked,phase_current}));
    wire pclk_in1,pclk1;wire [15:0] rising1,falling1;
    wire raw_clock1;
    IBUF u_input1(.I(CAM1_PCLK),.O(pclk_in1));BUFG u_clock1(.I(pclk_in1),.O(raw_clock1));
    generate if(PHASE_CLOCK)begin:g_phase1
        EoSyncPhaseClock u_phase(raw_clock1,ref_clk,phase_reset,phase_targets[0+:9],pclk1,phase_current[0+:9],phase_locked[0],phase_busy[0],phase_fault[0]);
    end else begin:g_direct1
        assign pclk1=raw_clock1;assign phase_current[0+:9]=0;assign phase_locked[0]=1;assign phase_busy[0]=0;assign phase_fault[0]=0;
    end endgenerate
    Eo60InputSampler u_sampler1(pclk1,{CAM1_YOUT,CAM1_COUT},rising1,falling1);
    Eo60RasterMonitor u_rise1(.clk(pclk1),.y(rising1[15:8]),.c(rising1[7:0]),.toggle(toggles[0]),.report(reports[0+:256]),.live());
    Eo60RasterMonitor u_fall1(.clk(pclk1),.y(falling1[15:8]),.c(falling1[7:0]),.toggle(toggles[1]),.report(reports[256+:256]),.live());
    (* MARK_DEBUG="TRUE" *) wire [63:0] sync_snapshot_data1;
    (* MARK_DEBUG="TRUE" *) wire [31:0] sync_snapshot_meta1;
    (* MARK_DEBUG="TRUE" *) wire [1:0] sync_snapshot_control1;
    (* ASYNC_REG="TRUE" *) reg [1:0] select1=0;
    always @(posedge pclk1) select1<={select1[0],snapshot_falling[0]};
    EoSyncSnapshot u_snapshot1(pclk1,select1[1]?falling1[15:8]:rising1[15:8],sync_snapshot_data1,sync_snapshot_meta1,sync_snapshot_control1);
    eo_sync_snapshot_ila u_snapshot_ila1(.clk(pclk1),.probe0(sync_snapshot_data1),.probe1(sync_snapshot_meta1),.probe2(sync_snapshot_control1));
    assign TRIG_IN1=trigger;
    wire pclk_in2,pclk2;wire [15:0] rising2,falling2;
    wire raw_clock2;
    IBUF u_input2(.I(CAM2_PCLK),.O(pclk_in2));BUFG u_clock2(.I(pclk_in2),.O(raw_clock2));
    generate if(PHASE_CLOCK)begin:g_phase2
        EoSyncPhaseClock u_phase(raw_clock2,ref_clk,phase_reset,phase_targets[9+:9],pclk2,phase_current[9+:9],phase_locked[1],phase_busy[1],phase_fault[1]);
    end else begin:g_direct2
        assign pclk2=raw_clock2;assign phase_current[9+:9]=0;assign phase_locked[1]=1;assign phase_busy[1]=0;assign phase_fault[1]=0;
    end endgenerate
    Eo60InputSampler u_sampler2(pclk2,{CAM2_YOUT,CAM2_COUT},rising2,falling2);
    Eo60RasterMonitor u_rise2(.clk(pclk2),.y(rising2[15:8]),.c(rising2[7:0]),.toggle(toggles[2]),.report(reports[512+:256]),.live());
    Eo60RasterMonitor u_fall2(.clk(pclk2),.y(falling2[15:8]),.c(falling2[7:0]),.toggle(toggles[3]),.report(reports[768+:256]),.live());
    (* MARK_DEBUG="TRUE" *) wire [63:0] sync_snapshot_data2;
    (* MARK_DEBUG="TRUE" *) wire [31:0] sync_snapshot_meta2;
    (* MARK_DEBUG="TRUE" *) wire [1:0] sync_snapshot_control2;
    (* ASYNC_REG="TRUE" *) reg [1:0] select2=0;
    always @(posedge pclk2) select2<={select2[0],snapshot_falling[1]};
    EoSyncSnapshot u_snapshot2(pclk2,select2[1]?falling2[15:8]:rising2[15:8],sync_snapshot_data2,sync_snapshot_meta2,sync_snapshot_control2);
    eo_sync_snapshot_ila u_snapshot_ila2(.clk(pclk2),.probe0(sync_snapshot_data2),.probe1(sync_snapshot_meta2),.probe2(sync_snapshot_control2));
    assign TRIG_IN2=trigger;
    wire pclk_in3,pclk3;wire [15:0] rising3,falling3;
    wire raw_clock3;
    IBUF u_input3(.I(CAM3_PCLK),.O(pclk_in3));BUFG u_clock3(.I(pclk_in3),.O(raw_clock3));
    generate if(PHASE_CLOCK)begin:g_phase3
        EoSyncPhaseClock u_phase(raw_clock3,ref_clk,phase_reset,phase_targets[18+:9],pclk3,phase_current[18+:9],phase_locked[2],phase_busy[2],phase_fault[2]);
    end else begin:g_direct3
        assign pclk3=raw_clock3;assign phase_current[18+:9]=0;assign phase_locked[2]=1;assign phase_busy[2]=0;assign phase_fault[2]=0;
    end endgenerate
    Eo60InputSampler u_sampler3(pclk3,{CAM3_YOUT,CAM3_COUT},rising3,falling3);
    Eo60RasterMonitor u_rise3(.clk(pclk3),.y(rising3[15:8]),.c(rising3[7:0]),.toggle(toggles[4]),.report(reports[1024+:256]),.live());
    Eo60RasterMonitor u_fall3(.clk(pclk3),.y(falling3[15:8]),.c(falling3[7:0]),.toggle(toggles[5]),.report(reports[1280+:256]),.live());
    (* MARK_DEBUG="TRUE" *) wire [63:0] sync_snapshot_data3;
    (* MARK_DEBUG="TRUE" *) wire [31:0] sync_snapshot_meta3;
    (* MARK_DEBUG="TRUE" *) wire [1:0] sync_snapshot_control3;
    (* ASYNC_REG="TRUE" *) reg [1:0] select3=0;
    always @(posedge pclk3) select3<={select3[0],snapshot_falling[2]};
    EoSyncSnapshot u_snapshot3(pclk3,select3[1]?falling3[15:8]:rising3[15:8],sync_snapshot_data3,sync_snapshot_meta3,sync_snapshot_control3);
    eo_sync_snapshot_ila u_snapshot_ila3(.clk(pclk3),.probe0(sync_snapshot_data3),.probe1(sync_snapshot_meta3),.probe2(sync_snapshot_control3));
    assign TRIG_IN3=trigger;
    wire pclk_in4,pclk4;wire [15:0] rising4,falling4;
    wire raw_clock4;
    IBUF u_input4(.I(CAM4_PCLK),.O(pclk_in4));BUFG u_clock4(.I(pclk_in4),.O(raw_clock4));
    generate if(PHASE_CLOCK)begin:g_phase4
        EoSyncPhaseClock u_phase(raw_clock4,ref_clk,phase_reset,phase_targets[27+:9],pclk4,phase_current[27+:9],phase_locked[3],phase_busy[3],phase_fault[3]);
    end else begin:g_direct4
        assign pclk4=raw_clock4;assign phase_current[27+:9]=0;assign phase_locked[3]=1;assign phase_busy[3]=0;assign phase_fault[3]=0;
    end endgenerate
    Eo60InputSampler u_sampler4(pclk4,{CAM4_YOUT,CAM4_COUT},rising4,falling4);
    Eo60RasterMonitor u_rise4(.clk(pclk4),.y(rising4[15:8]),.c(rising4[7:0]),.toggle(toggles[6]),.report(reports[1536+:256]),.live());
    Eo60RasterMonitor u_fall4(.clk(pclk4),.y(falling4[15:8]),.c(falling4[7:0]),.toggle(toggles[7]),.report(reports[1792+:256]),.live());
    (* MARK_DEBUG="TRUE" *) wire [63:0] sync_snapshot_data4;
    (* MARK_DEBUG="TRUE" *) wire [31:0] sync_snapshot_meta4;
    (* MARK_DEBUG="TRUE" *) wire [1:0] sync_snapshot_control4;
    (* ASYNC_REG="TRUE" *) reg [1:0] select4=0;
    always @(posedge pclk4) select4<={select4[0],snapshot_falling[3]};
    EoSyncSnapshot u_snapshot4(pclk4,select4[1]?falling4[15:8]:rising4[15:8],sync_snapshot_data4,sync_snapshot_meta4,sync_snapshot_control4);
    eo_sync_snapshot_ila u_snapshot_ila4(.clk(pclk4),.probe0(sync_snapshot_data4),.probe1(sync_snapshot_meta4),.probe2(sync_snapshot_control4));
    assign TRIG_IN4=trigger;
    wire pclk_in5,pclk5;wire [15:0] rising5,falling5;
    wire raw_clock5;
    IBUF u_input5(.I(CAM5_PCLK),.O(pclk_in5));BUFG u_clock5(.I(pclk_in5),.O(raw_clock5));
    generate if(PHASE_CLOCK)begin:g_phase5
        EoSyncPhaseClock u_phase(raw_clock5,ref_clk,phase_reset,phase_targets[36+:9],pclk5,phase_current[36+:9],phase_locked[4],phase_busy[4],phase_fault[4]);
    end else begin:g_direct5
        assign pclk5=raw_clock5;assign phase_current[36+:9]=0;assign phase_locked[4]=1;assign phase_busy[4]=0;assign phase_fault[4]=0;
    end endgenerate
    Eo60InputSampler u_sampler5(pclk5,{CAM5_YOUT,CAM5_COUT},rising5,falling5);
    Eo60RasterMonitor u_rise5(.clk(pclk5),.y(rising5[15:8]),.c(rising5[7:0]),.toggle(toggles[8]),.report(reports[2048+:256]),.live());
    Eo60RasterMonitor u_fall5(.clk(pclk5),.y(falling5[15:8]),.c(falling5[7:0]),.toggle(toggles[9]),.report(reports[2304+:256]),.live());
    (* MARK_DEBUG="TRUE" *) wire [63:0] sync_snapshot_data5;
    (* MARK_DEBUG="TRUE" *) wire [31:0] sync_snapshot_meta5;
    (* MARK_DEBUG="TRUE" *) wire [1:0] sync_snapshot_control5;
    (* ASYNC_REG="TRUE" *) reg [1:0] select5=0;
    always @(posedge pclk5) select5<={select5[0],snapshot_falling[4]};
    EoSyncSnapshot u_snapshot5(pclk5,select5[1]?falling5[15:8]:rising5[15:8],sync_snapshot_data5,sync_snapshot_meta5,sync_snapshot_control5);
    eo_sync_snapshot_ila u_snapshot_ila5(.clk(pclk5),.probe0(sync_snapshot_data5),.probe1(sync_snapshot_meta5),.probe2(sync_snapshot_control5));
    assign TRIG_IN5=trigger;
    (* MARK_DEBUG="TRUE" *) wire [63:0] sync_metadata;
    (* MARK_DEBUG="TRUE" *) wire [255:0] sync_payload;
    (* MARK_DEBUG="TRUE" *) wire sync_valid;
    (* MARK_DEBUG="TRUE" *) wire [15:0] sync_overruns;
    EoSyncTelemetry u_telemetry(ref_clk,toggles,reports,trigger,sync_metadata,sync_payload,sync_valid,sync_overruns);
    eo_sync_ila u_ila(.clk(ref_clk),.probe0(sync_metadata),.probe1(sync_payload),.probe2(sync_valid),.probe3(sync_overruns),.probe4(32'hE05C0001));
endmodule
