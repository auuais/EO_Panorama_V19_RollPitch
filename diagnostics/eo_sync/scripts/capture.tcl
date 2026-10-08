# Timestamped frame reports; never programs the FPGA or changes camera settings.
if {[llength $argv]<2} {error "Usage: capture.tcl matching.ltx NEW_DIRECTORY ?blocks=2?"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
set blocks 2
if {[llength $argv]>2} {set blocks [lindex $argv 2]}
if {[file exists $out]} {error "Refusing existing capture directory"}
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
    if {[llength [get_hw_probes -quiet -of_objects $candidate -filter {NAME =~ "*sync_metadata*"}]]==1} {set ila $candidate;break}
}
if {$ila eq ""} {error "Synchronization ILA not found"}
set probes {}
foreach {port name width} {0 event_metadata 64 1 event_payload 256 2 event_valid 1 3 event_overruns 16 4 event_signature 32} {
    set p [create_hw_probe -map [format {probe%d[%d:0]} $port [expr {$width-1}]] [format {%s[%d:0]} $name [expr {$width-1}]] $ila]
    lappend probes $p
    if {$port==2} {set valid $p}
}
set f [open $out/provenance.txt w]
puts $f "LTX: $ltx\nStarted: [clock format [clock seconds]]\nDevice: $dev\nILA: $ila"
puts $f [report_property -return_string $ila]
foreach vio [get_hw_vios -quiet -of_objects $dev] {
    refresh_hw_vio $vio
    foreach p [get_hw_probes -of_objects $vio] {puts $f [report_property -return_string $p]}
}
close $f
foreach property {CONTROL.DATA_DEPTH CONTROL.WINDOW_COUNT CONTROL.TRIGGER_POSITION CONTROL.CAPTURE_MODE CONTROL.CAPTURE_CONDITION} {
    dict set old $property [get_property $property $ila]
}
set status [catch {
    set_property CONTROL.WINDOW_COUNT 1 $ila
    set_property CONTROL.DATA_DEPTH 16384 $ila
    set_property CONTROL.TRIGGER_POSITION 0 $ila
    set_property CONTROL.CAPTURE_MODE BASIC $ila
    set_property CONTROL.CAPTURE_CONDITION AND $ila
    set_property TRIGGER_COMPARE_VALUE {eq1'b1} $valid
    set_property CAPTURE_COMPARE_VALUE {eq1'b1} $valid
    for {set i 0} {$i<$blocks} {incr i} {
        puts "SYNC_BLOCK_ARMED=$i"
        run_hw_ila $ila
        wait_on_hw_ila -timeout 180 $ila
        set data [upload_hw_ila_data $ila]
        write_hw_ila_data -csv_file [file join $out [format "events_%03d.csv" $i]] $data
        puts "SYNC_BLOCK_SAVED=$i"
    }
} result options]
dict for {property value} $old {set_property $property $value $ila}
delete_hw_probe $probes
close_hw_target
close_hw_manager
if {$status} {return -options $options $result}
puts "SYNC_CAPTURE_DONE=$out"
