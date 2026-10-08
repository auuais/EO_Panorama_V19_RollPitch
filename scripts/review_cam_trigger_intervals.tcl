# Capture consecutive trigger events in segmented ILA memory; no design writes.
set root [file normalize [file join [file dirname [info script]] ..]]
set outdir [file join $root captures cam_fps_review 20261006_205147]
set ltxfile [file join $root builds bit_archive 20261006_150257_camratemon_bd9af71 KintexTop_EO_IR_HD_SDI_panorama_base.ltx]
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
open_hw_target
set dev [lindex [get_hw_devices] 0]
current_hw_device $dev
set_property PROBES.FILE $ltxfile $dev
set_property FULL_PROBES.FILE $ltxfile $dev
refresh_hw_device $dev
set ila ""
set probe ""
foreach candidate [get_hw_ilas -of_objects $dev] {
    set found [get_hw_probes -quiet -of_objects $candidate -filter {NAME == "eo_fpga_trigger_start"}]
    if {[llength $found]} {set ila $candidate; set probe $found; break}
}
if {[llength $probe] != 1} {error "Expected one trigger-start probe"}
set saved_depth [get_property CONTROL.DATA_DEPTH $ila]
set saved_count [get_property CONTROL.WINDOW_COUNT $ila]
set saved_position [get_property CONTROL.TRIGGER_POSITION $ila]
set saved_compare [get_property TRIGGER_COMPARE_VALUE $probe]
set_property CONTROL.TRIGGER_POSITION 0 $ila
set_property CONTROL.DATA_DEPTH 128 $ila
set_property CONTROL.WINDOW_COUNT 64 $ila
set_property TRIGGER_COMPARE_VALUE eq1'b1 $probe
puts "SEGMENTED_ILA=$ila DEPTH=[get_property CONTROL.DATA_DEPTH $ila] WINDOWS=[get_property CONTROL.WINDOW_COUNT $ila]"
for {set i 0} {$i < 4} {incr i} {
    run_hw_ila $ila
    wait_on_hw_ila -timeout 15 $ila
    set data [upload_hw_ila_data $ila]
    write_hw_ila_data -csv_file -force [file join $outdir [format "trigger_segments_%02d.csv" $i]] $data
}
set_property CONTROL.WINDOW_COUNT $saved_count $ila
set_property CONTROL.DATA_DEPTH $saved_depth $ila
set_property CONTROL.TRIGGER_POSITION $saved_position $ila
set_property TRIGGER_COMPARE_VALUE $saved_compare $probe
close_hw_target
close_hw_manager
puts "TRIGGER_SEGMENTS_DONE=$outdir"
