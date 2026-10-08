`timescale 1ns/1ps
// Grayscale snapshot of the falling-edge stream. Every second row/pixel is
// retained without filtering; eight Y bytes form one packet. Never affects CRC.
module Eo60Snapshot #(parameter WIDTH=1920)(
    input wire clk, input wire [7:0] y,
    output reg [63:0] data=0, output reg [31:0] meta=0,
    output reg [1:0] control=0
);
    reg [7:0] yi=0,d0=0,d1=0,d2=0;
    wire prefix=d2==255 && d1==0 && d0==0;
    wire xy_ok=yi[7] && yi[3:0]=={yi[5]^yi[4],yi[6]^yi[4],yi[6]^yi[5],yi[6]^yi[5]^yi[4]};
    wire marker=prefix && xy_ok;
    wire sav=marker && !yi[4];
    reg prev_v=0,started=0;
    wire start=marker && prev_v && !yi[5];
    reg [14:0] frame_seq=0;
    reg [10:0] next_row=0,row=0,x=0;
    reg [11:0] remaining=0;
    reg [55:0] packed_y=0;
    always @(posedge clk) begin
        yi<=y;d2<=d1;d1<=d0;d0<=yi;
        control<=0;
        if(marker)prev_v<=yi[5];
        if(start)begin
            started<=1;frame_seq<=frame_seq+1'b1;next_row<=0;remaining<=0;
        end
        if(sav && !yi[5] && (started || start))begin
            row<=start?0:next_row;next_row<=start?1:next_row+1'b1;
            x<=0;remaining<=WIDTH;
        end else if(remaining!=0)begin
            remaining<=remaining-1'b1;x<=x+1'b1;
            if(!row[0] && !x[0])begin
                packed_y<={packed_y[47:0],yi};
                if(x[3:0]==14)begin
                    data<={packed_y,yi};
                    meta<={frame_seq,row[10:1],x[10:4]};
                    control<={(row==0 && x==14),1'b1};
                end
            end
        end
    end
endmodule
