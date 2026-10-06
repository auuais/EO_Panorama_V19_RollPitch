`timescale 1ns/1ps
// Accelerated wall-time model: same RTL, divider=256, independent input rates.
module tb_EoCamFrameRateMon_review;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0;
    reg [5:0] vs=0;
    reg trig=0;
    wire [63:0] word;
    EoCamFrameRateMon #(.CLK_HZ(768000),.TICK_CYCLES(256)) dut
        (.clk(clk),.rst_n(rst_n),.cam_vsync(vs),.trigger(trig),.dbg_word(word));
    integer cycle=0;
    integer windows=0;
    integer c;
    integer expected[0:5];
    integer periods[0:5];
    reg [5:0] selectors=0;
    integer fd;
    initial begin
        expected[0]=30; expected[1]=25; expected[2]=20;
        expected[3]=15; expected[4]=0; expected[5]=10;
        periods[0]=25600; periods[1]=30720; periods[2]=38400;
        periods[3]=51200; periods[4]=1; periods[5]=76800;
        fd=$fopen("sim_words.csv","w");
        $fdisplay(fd,"window,word,camera,expected_fps");
        repeat(5) @(negedge clk);
        rst_n=1;
    end
    always @(negedge clk) begin
        if (rst_n) begin
            cycle=cycle+1;
            for(c=0;c<6;c=c+1) begin
                if(c==4) vs[c]=0;
                else vs[c]=((cycle+103+c*317)%periods[c])<32;
            end
            trig=((cycle+271)%25600)<16;
        end
    end
    always @(posedge clk) begin
        if(rst_n && dut.win_end) begin
            windows=windows+1;
            #1;
            if(windows>=2) begin
                for(integer k=0;k<6;k=k+1) begin
                    if(dut.fps_q[k] !== expected[k])
                        $fatal(1,"fps mismatch cam=%0d got=%0d expected=%0d",k,dut.fps_q[k],expected[k]);
                    if(k!=4 && (dut.pmin_q[k]<periods[k]/256-1 || dut.pmax_q[k]>periods[k]/256))
                        $fatal(1,"period mismatch cam=%0d",k);
                end
                @(negedge clk); @(negedge clk);
                selectors[word[41:39]]=1;
                if(word[63:62]!==2'b10 || word[38:31]!==expected[word[41:39]])
                    $fatal(1,"packed mux mismatch %h",word);
                $fdisplay(fd,"%0d,%016h,%0d,%0d",windows,word,word[41:39],expected[word[41:39]]);
            end
            if(windows==8) begin
                if(selectors!==6'b111111) $fatal(1,"selector coverage incomplete");
                $display("PASS: six independent rates 30,25,20,15,0,10; all selectors; period bounds; packed word");
                $fclose(fd);
                // Boundary-priority defect: an edge coincident with win_end is discarded.
                @(negedge clk);
                force dut.win_end=1'b1;
                force dut.g_cam[1].frame_start=1'b1;
                #1;
                begin: boundary_check
                    reg [7:0] before_count;
                    before_count=dut.cnt_acc[1];
                    @(posedge clk); #1;
                    if(dut.fps_q[1]!==before_count || dut.cnt_acc[1]!==0)
                        $fatal(1,"unexpected boundary behavior");
                    $display("CONFIRMED: edge at win_end is omitted from both windows");
                end
                $finish;
            end
        end
    end
    initial begin #70000000; $fatal(1,"timeout"); end
endmodule
