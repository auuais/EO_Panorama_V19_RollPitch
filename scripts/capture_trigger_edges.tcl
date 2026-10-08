# Consecutive one-cycle strobe/fallback events on the archived 30 Hz image.
if {[llength $argv]!=2} {error "Need LTX path and new output directory"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
if {[file exists $out]} {error "Output already exists"}
file mkdir $out
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
open_hw_target
set dev [lindex [get_hw_devices] 0]
current_hw_device $dev
set_property PROBES.FILE $ltx $dev
set_property FULL_PROBES.FILE $ltx $dev
refresh_hw_device $dev
set ila ""
foreach candidate [get_hw_ilas -of_objects $dev] {
    set p [get_hw_probes -quiet -of_objects $candidate -filter {NAME == "eo_fpga_trigger_start"}]
    if {[llength $p]==1} {set ila $candidate;set probe $p;break}
}
if {$ila eq ""} {error "No strobe/fallback pulse probe"}
set_property CONTROL.TRIGGER_POSITION 0 $ila
set_property CONTROL.DATA_DEPTH 128 $ila
set_property CONTROL.WINDOW_COUNT 64 $ila
set_property TRIGGER_COMPARE_VALUE eq1'b1 $probe
for {set i 0} {$i<4} {incr i} {
    run_hw_ila $ila
    wait_on_hw_ila -timeout 15 $ila
    set d [upload_hw_ila_data $ila]
    write_hw_ila_data -csv_file -force [file join $out [format "trigger_segments_%02d.csv" $i]] $d
}
set_property TRIGGER_COMPARE_VALUE eq1'bX $probe
set_property CONTROL.WINDOW_COUNT 1 $ila
set_property CONTROL.DATA_DEPTH 8192 $ila
close_hw_target
close_hw_manager
puts "TRIGGER_CAPTURE_DONE=$out"
