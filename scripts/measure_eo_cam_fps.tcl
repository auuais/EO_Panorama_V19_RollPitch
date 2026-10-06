# EO camera input frame rate and period spread, from EoCamFrameRateMon.
#
#   vivado -mode batch -source scripts/measure_eo_cam_fps.tcl -tclargs ?sweeps?
#   python scripts/decode_cam_fps.py <the printed CAM_FPS_OUTDIR>
#
# READ ONLY.  Arms the ILA, captures immediately and writes each capture as a
# CSV; the decoding happens in decode_cam_fps.py.  The monitor reports one
# camera per one-second window and advances the camera each window, so one
# capture shows one camera and the default 14 sweeps cover all six about twice.
#
# Read the SPREAD between a camera's shortest and longest frame period, not the
# rate: six free-running cameras also read ~30 fps each.
set root [file normalize [file join [file dirname [info script]] ..]]
set sweeps 14
if {[llength $argv] > 0} { set sweeps [lindex $argv 0] }

set ltxfile [file join $root EO_Panorama_V19_M1.runs impl_1 KintexTop_EO_IR_HD_SDI_panorama_base.ltx]
if {[info exists ::env(V19_LTX)] && $::env(V19_LTX) ne ""} {
    set ltxfile [file normalize $::env(V19_LTX)]
}

open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
open_hw_target
set dev [lindex [get_hw_devices] 0]
current_hw_device $dev
set_property PROBES.FILE $ltxfile $dev
set_property FULL_PROBES.FILE $ltxfile $dev
refresh_hw_device $dev

# the hd_clk ILA is the one carrying the rate word
set ila ""
foreach cand [get_hw_ilas -of_objects $dev] {
    if {[llength [get_hw_probes -of_objects $cand -filter {NAME =~ "*eo_cam_rate_word*"} -quiet]] > 0} {
        set ila $cand ; break
    }
}
if {$ila eq ""} {
    puts "NO RATE PROBE: this bitstream predates EoCamFrameRateMon"
    close_hw_target ; close_hw_manager ; exit 1
}
puts "ILA=$ila"

set outdir [file join $root captures cam_fps [clock format [clock seconds] -format "%Y%m%d_%H%M%S"]]
file mkdir $outdir
for {set i 0} {$i < $sweeps} {incr i} {
    set_property CONTROL.TRIGGER_POSITION 0 $ila
    run_hw_ila -trigger_now $ila
    wait_on_hw_ila $ila
    set d [upload_hw_ila_data $ila]
    write_hw_ila_data -csv_file -force [file join $outdir [format "w%03d.csv" $i]] $d
    after 500
}
puts "CAM_FPS_OUTDIR=$outdir"

close_hw_target
close_hw_manager
