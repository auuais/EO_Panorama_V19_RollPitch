module Kintex_top_5cam_1ch(
    // FPGA global reset
    input  wire        FPGA_RESET,

    // EO Camera 5
    input  wire        CAM5_PCLK,
    input  wire [7:0]  CAM5_YOUT,
    input  wire [7:0]  CAM5_COUT,
    input  wire        STROBE_OUT0,
    output wire        TRIG_IN5,

    // DEBUG output port 
    output wire        IEG0_PCLK,
    output wire        IEG0_HSYNC,
    output wire        IEG0_VSYNC,
    output wire [19:0] IEG0_DOUT,

    //IEG0_DOUT 0,1 & 10
    output wire        IEG1_PCLK,
    output wire        IEG1_HSYNC,
    output wire        IEG1_VSYNC,
    output wire [19:0] IEG1_DOUT,

    // SAV/EAV derived frame timing, for the input-rate monitor.  trs_frame_tgl
    // toggles once per frame start (V falling in the XY word); trs_lines is the
    // number of EAV codes in the frame that just ended, and trs_f is its F bit.
    // Both are stable between toggles, so the reader can sample them on the
    // toggle without a handshake.
    output wire        trs_frame_tgl,
    output wire [11:0] trs_lines,
    output wire        trs_f
);
assign TRIG_IN5 = STROBE_OUT0;
/////////////////////////////////////////////
// Reset buffer
/////////////////////////////////////////////
wire nRESET = 1'b1;
//wire nRESET;
//IBUF U_RESET_bufg (
//   .I(FPGA_RESET),
//   .O(nRESET)
//);

/////////////////////////////////////////////
// CAM5 PCLK BUFG 
/////////////////////////////////////////////
wire CAM5_PCLK_bufg;

IBUF U_cam5_pclk_ibuf (
    .I(CAM5_PCLK),
    .O(CAM5_PCLK_bufg)
);
//BUFG U_cam5_pclk_bufg (
//    .I(CAM5_PCLK_ibufg),
//    .O(CAM5_PCLK_bufg)
//);

/////////////////////////////////////////////
// EO CAMERA data latch 
/////////////////////////////////////////////
reg [7:0] CAM5_YOUT_1d, CAM5_COUT_1d;

always @(posedge CAM5_PCLK_bufg or negedge nRESET) begin
    if (!nRESET) begin
        CAM5_YOUT_1d <= 8'h00;
        CAM5_COUT_1d <= 8'h00;
    end else begin
        CAM5_YOUT_1d <= CAM5_YOUT;
        CAM5_COUT_1d <= CAM5_COUT;
    end
end

/////////////////////////////////////////////
// BT.1120 TRS(FF 00 00 XY)
/////////////////////////////////////////////
reg [7:0] cam5_y_d0, cam5_y_d1, cam5_y_d2;

always @(posedge CAM5_PCLK_bufg or negedge nRESET) begin
    if(!nRESET) begin
        cam5_y_d2 <= 8'h00;
        cam5_y_d1 <= 8'h00;
        cam5_y_d0 <= 8'h00;  
    end else begin
        cam5_y_d2 <= cam5_y_d1;
        cam5_y_d1 <= cam5_y_d0;
        cam5_y_d0 <= CAM5_YOUT;  
    end
end

// TRS prefix (FF 00 00) 검출
wire cam5_ff   = (cam5_y_d2 == 8'hFF);
wire cam5_00_1 = (cam5_y_d1 == 8'h00);
wire cam5_00_2 = (cam5_y_d0 == 8'h00);

wire cam5_mkr_fnd = cam5_ff && cam5_00_1 && cam5_00_2;

wire cam5_f_now = CAM5_YOUT[6];
wire cam5_v_now = CAM5_YOUT[5];
wire cam5_h_now = CAM5_YOUT[4];

reg cam5_f_bit, cam5_v_bit, cam5_h_bit;
reg cam5_hsync, cam5_vsync;
//reg cam5_de;
reg cam5_act_video;

wire cam5_sav = cam5_mkr_fnd && (cam5_h_now == 1'b0);
wire cam5_eav = cam5_mkr_fnd && (cam5_h_now == 1'b1);

// HCNT 
reg [11:0] HCNT;

always @(posedge CAM5_PCLK_bufg or negedge nRESET) begin
    if(!nRESET) begin
        cam5_f_bit     <= 1'b0;
        cam5_v_bit     <= 1'b0;
        cam5_h_bit     <= 1'b0;
        cam5_act_video <= 1'b0;
        //cam5_de        <= 1'b0;
        cam5_hsync     <= 1'b0;
        cam5_vsync     <= 1'b0;
        HCNT           <= 12'b0;
    end else begin
        if (cam5_mkr_fnd) begin
            cam5_f_bit <= cam5_f_now;
            cam5_v_bit <= cam5_v_now;
            cam5_h_bit <= cam5_h_now;
        end

        if (cam5_sav)
            cam5_act_video <= 1'b1;
        else if (cam5_eav)
            cam5_act_video <= 1'b0;

        if (cam5_eav)
            HCNT <= 12'b0;
        else if (cam5_act_video || cam5_sav)
            HCNT <= HCNT + 12'b1; 

        if (cam5_mkr_fnd) begin
            cam5_hsync <= cam5_h_now;  
            cam5_vsync <= cam5_v_now;
        end
    end
end

// Lines per frame and field, counted from the TRS codes themselves.
// Frame start is V falling, the same edge the rest of the design uses.
reg        cam5_v_bit_d = 1'b0;
reg [11:0] cam5_line_cnt = 12'd0;
reg [11:0] cam5_lines_q  = 12'd0;
reg        cam5_f_q      = 1'b0;
reg        cam5_frame_tgl = 1'b0;
always @(posedge CAM5_PCLK_bufg or negedge nRESET) begin
    if (!nRESET) begin
        cam5_v_bit_d <= 1'b0; cam5_line_cnt <= 12'd0;
        cam5_lines_q <= 12'd0; cam5_f_q <= 1'b0; cam5_frame_tgl <= 1'b0;
    end else begin
        cam5_v_bit_d <= cam5_v_bit;
        if (cam5_v_bit_d && !cam5_v_bit) begin          // V falling: frame start
            cam5_lines_q   <= cam5_line_cnt;
            cam5_f_q       <= cam5_f_bit;
            cam5_line_cnt  <= 12'd0;
            cam5_frame_tgl <= ~cam5_frame_tgl;
        end else if (cam5_eav && (cam5_line_cnt != 12'hFFF)) begin
            cam5_line_cnt <= cam5_line_cnt + 12'd1;
        end
    end
end
assign trs_frame_tgl = cam5_frame_tgl;
assign trs_lines     = cam5_lines_q;
assign trs_f         = cam5_f_q;

wire cam5_hsync1920 = (HCNT > 0 && HCNT < 1921);

/////////////////////////////////////////////
// DEBUG 포트 
/////////////////////////////////////////////
assign IEG0_PCLK  = CAM5_PCLK_bufg;
//assign IEG0_HSYNC = cam5_hsync;
assign IEG0_HSYNC = cam5_hsync1920 & !cam5_vsync;
assign IEG0_VSYNC = cam5_vsync;

// IEG0_DOUT[10]   FPGA_reset으로 jumper
// IEG0_DOUT[0]    SDA, IEG0_DOUT[1]    SCL
//assign IEG0_DOUT  = {
//                   //CAM5_YOUT_1d,        // [19:12] Y data
//                    HCNT[11:0],        // [19:12] Y data
//                    cam5_hsync,          // [7]
//                    cam5_vsync,          // [6]
//                    cam5_sav,            // [5]
//                    cam5_eav,            // [4]
//                    cam5_ff,             // [3]
//                    cam5_00_1,           // [2]
//                    cam5_00_2,           // [1]
//                    cam5_mkr_fnd         // [0]
//                    };
assign IEG0_DOUT  = {CAM5_YOUT_1d,2'b0,CAM5_COUT_1d,2'b0}; 
//assign IEG0_DOUT  = {CAM5_YOUT_1d,2'b0,CAM5_COUT_1d}; 

/////////////////////////////////////////////
/////////////////////////////////////////////
assign IEG1_PCLK  = CAM5_PCLK_bufg;
assign IEG1_HSYNC = cam5_hsync1920 & !cam5_vsync;
assign IEG1_VSYNC = cam5_vsync;
//assign IEG1_DOUT  = IEG0_DOUT;
assign IEG1_DOUT  = {CAM5_YOUT_1d,2'b0,CAM5_COUT_1d,2'b0}; 

/////////////////////////////////////////////
// EO camera trigger (cam5 only)
/////////////////////////////////////////////

endmodule
