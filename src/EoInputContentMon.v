`timescale 1ns/1ps
// Passive BT.1120 input observer. No signal from this module controls capture.
// CRC-32/MPEG-2 recurrence, initial FFFFFFFF, no reflection/final XOR;
// every active sample contributes Y then C (16 bits, MSB first).
// The sequence number is deliberately NOT included in either checksum.
module EoInputContentMon #(
    parameter WIDTH=1920, HEIGHT=1080, TOTAL_LINES=1125,
    parameter ROI_X=912, ROI_Y=480, ROI_W=96, ROI_H=96
)(
    input wire clk, input wire [7:0] y, c,
    output reg toggle=0, output reg [159:0] report=0
);
    reg [7:0] yi=0, ci=0, d0=0, d1=0, d2=0;
    wire marker=(d2==8'hff && d1==0 && d0==0);
    wire sav=marker && !yi[4], eav=marker && yi[4];
    reg prev_v=0, started=0, first_f=0, field_change=0;
    wire start=marker && prev_v && !yi[5];
    reg [15:0] seq=0;
    reg [31:0] crc=32'hffffffff, roi_crc=32'hffffffff;
    reg [21:0] pixels=0;
    reg [11:0] lines=0, eavs=0, remaining=0, age=0;
    reg active_line=0, roi_line=0, bad_line=0;
    wire geometry_ok=(pixels==WIDTH*HEIGHT && lines==HEIGHT &&
                       eavs==TOTAL_LINES && !bad_line && !field_change);
    wire [7:0] flags={4'd0,field_change,bad_line,geometry_ok,1'b1};
    function [31:0] crc16;
        input [31:0] old;
        input [15:0] data;
        reg [31:0] v;
        integer b;
        begin
            v=old;
            for(b=15;b>=0;b=b-1)
                v={v[30:0],1'b0} ^ ((v[31]^data[b]) ? 32'h04c11db7 : 32'd0);
            crc16=v;
        end
    endfunction
    always @(posedge clk) begin
        yi<=y; ci<=c;
        d2<=d1; d1<=d0; d0<=yi;
        if(age!=12'hfff) age<=age+1'b1;
        if(marker) begin
            prev_v<=yi[5];
            if(started && yi[6]!=first_f) field_change<=1;
        end
        if(start) begin
            if(started) begin
                report<={26'd0,flags,eavs,seq,lines,pixels,roi_crc,crc};
                toggle<=~toggle;
                seq<=seq+1'b1;
            end
            started<=1; first_f<=yi[6]; field_change<=0;
            crc<=32'hffffffff; roi_crc<=32'hffffffff;
            pixels<=0; lines<=0; eavs<=eav ? 1 : 0;
            remaining<=0; active_line<=0; bad_line<=0;
        end else begin
            if(eav && started) begin
                eavs<=eavs+1'b1;
                if(active_line && (age!=WIDTH+3 || remaining!=0)) bad_line<=1;
                active_line<=0;
            end
            if(remaining!=0) begin
                remaining<=remaining-1'b1;
                crc<=crc16(crc,{yi,ci});
                pixels<=pixels+1'b1;
                if(roi_line && remaining<=WIDTH-ROI_X && remaining>WIDTH-ROI_X-ROI_W)
                    roi_crc<=crc16(roi_crc,{yi,ci});
            end
        end
        // Also handles V falling at SAV instead of the preceding EAV.
        if(sav && !yi[5] && (started || start)) begin
            remaining<=WIDTH; age<=0; active_line<=1;
            lines<=start ? 1 : lines+1'b1;
            roi_line<=start ? (ROI_Y==0) : (lines>=ROI_Y && lines<ROI_Y+ROI_H);
        end
    end
endmodule

// Mailboxes remain stable for one raster (~33 ms). Toggle and payload cross
// through synchronizers; payload is sampled after three toggle stages.
// Five packets, 64 clocks apart, allow 32-sample segmented ILA captures.
// 63 valid, 62:60 camera (0..5), 59:57 kind, 56:41 raster sequence,
// 40:33 flags, 32 reserved, 31:0 value. kind 0 full CRC, 1 ROI CRC,
// 2 active sample count, 3 {8'b0,active lines[11:0],EAVs[11:0]},
// 4 hd_clk timestamp (wraps at 2^32). flags bit0 complete, bit1 geometry OK,
// bit2 malformed active line, bit3 field changed within frame.
module EoInputContentMux(
    input wire clk,
    input wire [5:0] toggles,
    input wire [959:0] reports,
    output reg [63:0] event_word=0
);
    (* ASYNC_REG="TRUE" *) reg [5:0] t1=0,t2=0,t3=0;
    (* ASYNC_REG="TRUE" *) reg [959:0] r1=0,r2=0;
    reg [5:0] seen=0;
    reg [2:0] cam=0,kind=0;
    reg [5:0] cooldown=0;
    reg busy=0;
    reg [159:0] held=0;
    reg held_toggle=0;
    reg [31:0] tick=0, held_tick=0;
    reg [31:0] value;
    always @* begin
        case(kind)
            0: value=held[31:0];
            1: value=held[63:32];
            2: value={10'd0,held[85:64]};
            3: value={8'd0,held[97:86],held[125:114]};
            default: value=held_tick;
        endcase
    end
    always @(posedge clk) begin
        t1<=toggles; t2<=t1; t3<=t2;
        r1<=reports; r2<=r1;
        tick<=tick+1'b1;
        event_word[63]<=0;
        if(cooldown!=0) cooldown<=cooldown-1'b1;
        else if(busy) begin
            event_word<={1'b1,cam,kind,held[113:98],held[133:126],1'b0,value};
            cooldown<=63;
            if(kind==4) begin
                seen[cam]<=held_toggle;
                busy<=0; kind<=0;
                cam<=cam==5 ? 0 : cam+1'b1;
            end else kind<=kind+1'b1;
        end else if(t3[cam]!=seen[cam]) begin
            held<=r2[cam*160+:160]; held_toggle<=t3[cam]; held_tick<=tick;
            busy<=1; kind<=0;
        end else cam<=cam==5 ? 0 : cam+1'b1;
    end
endmodule
