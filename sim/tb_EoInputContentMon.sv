`timescale 1ns/1ps
module tb_EoInputContentMon;
    reg clk=0, hd=0;
    always #5 clk=~clk;
    always #7 hd=~hd;
    reg [7:0] y=128,c=128;
    wire toggle;
    wire [159:0] report;
    wire [63:0] event_word;
    EoInputContentMon #(.WIDTH(16),.HEIGHT(4),.TOTAL_LINES(6),
        .ROI_X(4),.ROI_Y(1),.ROI_W(4),.ROI_H(2)) dut(clk,y,c,toggle,report);
    EoInputContentMux mux(hd,{6{toggle}},{6{report}},event_word);
    integer seen_reports=0, packets=0;
    integer seen[0:5][0:4];
    reg last_toggle=0;
    reg [31:0] expected_crc,expected_roi;
    integer kind,cam,seq,i,j;
    always @(negedge clk) if(toggle!=last_toggle) begin
        last_toggle=toggle;
        expected_crc=(seen_reports==2 || seen_reports==3) ? 32'h54286f40 : 32'h351fa030;
        expected_roi=(seen_reports==2 || seen_reports==3) ? 32'heb279ca8 : 32'hb838e951;
        if(report[31:0]!==expected_crc || report[63:32]!==expected_roi)
            $fatal(1,"CRC mismatch seq=%d actual=%h %h expected=%h %h",seen_reports,report[31:0],report[63:32],expected_crc,expected_roi);
        if(report[85:64]!=64 || report[97:86]!=4 || report[125:114]!=6 ||
           report[113:98]!=seen_reports || report[133:126]!=3)
            $fatal(1,"Geometry/sequence/flags mismatch %h",report);
        seen_reports=seen_reports+1;
    end
    always @(negedge hd) if(event_word[63]) begin
        cam=event_word[62:60]; kind=event_word[59:57]; seq=event_word[56:41];
        if(kind==0) $display("packet time=%t cam=%d seq=%d",$time,cam,seq);
        if(cam>5 || kind>4 || event_word[40:33]!=3) $fatal(1,"bad packet %h",event_word);
        if(seq!=seen[cam][kind]) $fatal(1,"lost packet cam=%d kind=%d seq=%d expected=%d",cam,kind,seq,seen[cam][kind]);
        expected_crc=(seq==2 || seq==3) ? 32'h54286f40 : 32'h351fa030;
        expected_roi=(seq==2 || seq==3) ? 32'heb279ca8 : 32'hb838e951;
        if(kind==0 && event_word[31:0]!=expected_crc) $fatal(1,"CDC full CRC");
        if(kind==1 && event_word[31:0]!=expected_roi) $fatal(1,"CDC ROI CRC");
        if(kind==2 && event_word[31:0]!=64) $fatal(1,"CDC pixel count");
        if(kind==3 && event_word[31:0]!=32'h00004006) $fatal(1,"CDC line count");
        seen[cam][kind]=seen[cam][kind]+1; packets=packets+1;
    end
    task word_out(input [7:0] yy,input [7:0] cc);
        begin @(negedge clk); y=yy;c=cc; end
    endtask
    task trs(input v,input h);
        begin
            word_out(255,255);word_out(0,0);word_out(0,0);
            word_out({1'b1,1'b0,v,h,v^h,h,v,v^h},128);
        end
    endtask
    task raster(input integer image_id);
        integer row,col;
        begin
            for(row=0;row<6;row=row+1) begin
                trs(row<2,1);
                repeat(8) word_out(128,128);
                // Long vertical blank allows all six mailboxes to drain.
                if(row==0) repeat(3200) word_out(128,128);
                trs(row<2,0);
                for(col=0;col<16;col=col+1)
                    word_out(row<2 ? 128 : 32+(row-2)*16+col+image_id,128+image_id);
            end
        end
    endtask
    initial begin
        for(i=0;i<6;i=i+1) for(j=0;j<5;j=j+1) seen[i][j]=0;
        raster(0);raster(0);raster(1);raster(1);raster(0);
        // Publish final active frame at the next active EAV.
        trs(1,1); repeat(3208) word_out(128,128); trs(1,0);
        repeat(16) word_out(128,128);
        trs(1,1); repeat(8) word_out(128,128); trs(1,0);
        repeat(16) word_out(128,128); trs(0,1);
        repeat(4000) word_out(128,128);
        for(i=0;i<6;i=i+1) $display("cam %0d packet counts %0d %0d %0d %0d %0d",i,seen[i][0],seen[i][1],seen[i][2],seen[i][3],seen[i][4]);
        if(seen_reports!=5 || packets!=150) $fatal(1,"incomplete reports=%d packets=%d",seen_reports,packets);
        $display("PASS: independent CRC vectors, repeated/changed/revisited pictures, geometry, sequences, six concurrent CDC mailboxes and all 150 packets");
        $finish;
    end
    initial begin #2000000; $fatal(1,"timeout"); end
endmodule
