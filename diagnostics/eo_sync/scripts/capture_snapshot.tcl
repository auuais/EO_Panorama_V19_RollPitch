# One 512x448 OSD crop, stored only on valid packed pixels.
if {[llength $argv]!=3} {error "Usage: capture_snapshot.tcl matching.ltx NEW_DIRECTORY CAMERA_2_TO_6"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
set camera [lindex $argv 2]
if {$camera<2 || $camera>6} {error "Camera must be 2..6"}
set index [expr {$camera-1}]
if {[file exists $out]} {error "Refusing existing directory"}
file mkdir $out
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
set target [get_hw_targets]
if {[llength $target]!=1} {error "Expected exactly one target"}
set_property PARAM.FREQUENCY 6000000 $target
open_hw_target $target
set dev [get_hw_devices -quiet xcku15p_0]
if {[llength $dev]!=1} {error "Expected KU15P"}
set_property PROBES.FILE $ltx $dev
set_property FULL_PROBES.FILE $ltx $dev
refresh_hw_device $dev
set ila ""
foreach candidate [get_hw_ilas -of_objects $dev] {
    if {[llength [get_hw_probes -quiet -of_objects $candidate -filter "NAME =~ *sync_snapshot_data${index}*"]]==1} {set ila $candidate;break}
}
if {$ila eq ""} {error "Snapshot ILA not found"}
set probes {}
foreach {port name width} {0 snapshot_pixels 64 1 snapshot_meta 32 2 snapshot_control 2} {
    set p [create_hw_probe -map [format {probe%d[%d:0]} $port [expr {$width-1}]] [format {%s[%d:0]} $name [expr {$width-1}]] $ila]
    lappend probes $p
    if {$port==2} {set control $p}
}
set f [open $out/provenance.txt w]
puts $f "LTX: $ltx\nStarted: [clock format [clock seconds]]\nDevice: $dev\nILA: $ila"
puts $f [report_property -return_string $ila]
close $f
foreach property {CONTROL.DATA_DEPTH CONTROL.WINDOW_COUNT CONTROL.TRIGGER_POSITION CONTROL.CAPTURE_MODE CONTROL.CAPTURE_CONDITION} {
    dict set old $property [get_property $property $ila]
}
set status [catch {
    set_property CONTROL.WINDOW_COUNT 1 $ila
    set_property CONTROL.DATA_DEPTH 32768 $ila
    set_property CONTROL.TRIGGER_POSITION 0 $ila
    set_property CONTROL.CAPTURE_MODE BASIC $ila
    set_property CONTROL.CAPTURE_CONDITION AND $ila
    set_property TRIGGER_COMPARE_VALUE {eq2'b11} $control
    set_property CAPTURE_COMPARE_VALUE {eq2'bX1} $control
    run_hw_ila $ila
    wait_on_hw_ila -timeout 20 $ila
    set data [upload_hw_ila_data $ila]
    write_hw_ila_data -csv_file $out/snapshot.csv $data
} result options]
dict for {property value} $old {set_property $property $value $ila}
delete_hw_probe $probes
close_hw_target
close_hw_manager
if {$status} {return -options $options $result}
puts "SYNC_SNAPSHOT_DONE=$out"
