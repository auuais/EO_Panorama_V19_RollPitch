`timescale 1ns/1ps
// Strict, passive BT.1120 observer. Input is already captured by the sampler.
// CRC-32/MPEG-2, initial FFFFFFFF, Y then C, no final xor/reflection.
// report layout is documented in README.md and the decoder.
module Eo60RasterMonitor #(
    parameter WIDTH=1920, HEIGHT=1080, LINE_CLOCKS=2200, TOTAL_LINES=1125,
    parameter ROI_X=912, ROI_Y=480, ROI_W=96, ROI_H=96
)(
    input wire clk, input wire [7:0] y,c,
    output reg toggle=0, output reg [255:0] report=0,
    output wire [7:0] live
);
    reg [7:0] yi=0,ci=0,yd0=0,yd1=0,yd2=0,cd0=0,cd1=0,cd2=0;
    wire prefix=yd2==255 && yd1==0 && yd0==0;
    wire xy_ok=yi[7] && yi[3:0]=={yi[5]^yi[4],yi[6]^yi[4],yi[6]^yi[5],yi[6]^yi[5]^yi[4]};
    wire marker=prefix && xy_ok;
    wire chroma_match=cd2==255 && cd1==0 && cd0==0 && ci==yi;
    wire sav=marker && !yi[4],eav=marker && yi[4];
    reg prev_v=0,started=0,first_f=0,bad_field=0,bad_line=0,bad_xy=0,bad_period=0;
    wire start=marker && prev_v && !yi[5];
    reg [15:0] seq=0;
    reg [31:0] crc=32'hffffffff,roi_crc=32'hffffffff,frame_age=0;
    reg [21:0] pixels=0;
    reg [11:0] lines=0,eavs=0,remaining=0,active_age=0,bad_xy_count=0,c_bad_count=0;
    reg [15:0] line_age=0,line_min=16'hffff,line_max=0;
    reg have_eav=0,active_line=0,roi_line=0;
    wire [15:0] line_interval=line_age+16'd1;
    wire geometry_ok=pixels==WIDTH*HEIGHT && lines==HEIGHT && eavs==TOTAL_LINES &&
                     !bad_line && !bad_xy && !bad_field && !bad_period &&
                     frame_age==LINE_CLOCKS*TOTAL_LINES-1;
    wire [7:0] flags={1'b0,(frame_age!=LINE_CLOCKS*TOTAL_LINES-1),bad_period,bad_field,bad_xy,bad_line,geometry_ok,1'b1};
    assign live={start,prefix,xy_ok,eav,sav,bad_line,bad_xy,bad_period};
    function [31:0] crc16;
        input [31:0] old;input [15:0] data;
        reg [31:0] v;integer b;
        begin v=old;for(b=15;b>=0;b=b-1)
            v={v[30:0],1'b0} ^ ((v[31]^data[b]) ? 32'h04c11db7 : 32'd0);
            crc16=v;end
    endfunction
    always @(posedge clk) begin
        yi<=y;ci<=c;yd2<=yd1;yd1<=yd0;yd0<=yi;cd2<=cd1;cd1<=cd0;cd0<=ci;
        if(active_age!=12'hfff) active_age<=active_age+1'b1;
        if(line_age!=16'hffff) line_age<=line_age+1'b1;
        if(frame_age!=32'hffffffff) frame_age<=frame_age+1'b1;
        if(prefix && !xy_ok && started) begin
            bad_xy<=1;
            if(bad_xy_count!=12'hfff) bad_xy_count<=bad_xy_count+1'b1;
        end
        if(marker) begin
            prev_v<=yi[5];
            if(started && yi[6]!=first_f) bad_field<=1;
            if(started && !chroma_match && c_bad_count!=12'hfff) c_bad_count<=c_bad_count+1'b1;
        end
        if(eav) begin
            have_eav<=1;line_age<=0;
            if(started && have_eav) begin
                if(line_interval!=LINE_CLOCKS) bad_period<=1;
                if(line_interval<line_min) line_min<=line_interval;
                if(line_interval>line_max) line_max<=line_interval;
            end
        end
        if(start) begin
            if(started) begin
                report<={32'd0,line_min,line_max,(frame_age+32'd1),2'd0,c_bad_count,bad_xy_count,
                         flags,eavs,seq,lines,pixels,roi_crc,crc};
                toggle<=~toggle;seq<=seq+1'b1;
            end
            started<=1;first_f<=yi[6];bad_field<=0;bad_line<=0;bad_xy<=0;bad_period<=0;
            bad_xy_count<=0;c_bad_count<=0;frame_age<=0;line_min<=16'hffff;line_max<=0;
            crc<=32'hffffffff;roi_crc<=32'hffffffff;pixels<=0;lines<=0;eavs<=eav?1:0;
            remaining<=0;active_line<=0;
        end else begin
            if(eav && started) begin
                eavs<=eavs+1'b1;
                if(active_line && (active_age!=WIDTH+3 || remaining!=0)) bad_line<=1;
                active_line<=0;
            end
            if(remaining!=0) begin
                remaining<=remaining-1'b1;pixels<=pixels+1'b1;crc<=crc16(crc,{yi,ci});
                if(roi_line && remaining<=WIDTH-ROI_X && remaining>WIDTH-ROI_X-ROI_W)
                    roi_crc<=crc16(roi_crc,{yi,ci});
            end
        end
        if(sav && !yi[5] && (started || start)) begin
            remaining<=WIDTH;active_age<=0;active_line<=1;lines<=start?1:lines+1'b1;
            roi_line<=start?(ROI_Y==0):(lines>=ROI_Y && lines<ROI_Y+ROI_H);
        end
    end
endmodule
