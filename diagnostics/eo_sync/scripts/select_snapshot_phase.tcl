# Only changes OSD snapshot sampling edges. Timing and CRC observers stay active.
if {[llength $argv]!=2} {error "Usage: select_snapshot_phase.tcl matching.ltx DECIMAL_MASK_0_TO_31"}
set ltx [file normalize [lindex $argv 0]]
set mask [lindex $argv 1]
if {![string is integer -strict $mask] || $mask<0 || $mask>31} {error "Invalid phase mask"}
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
set vio [get_hw_vios -of_objects $dev -filter {CELL_NAME =~ "*u_snapshot_select*"}]
if {[llength $vio]!=1} {error "Expected one snapshot-edge selector"}
set probe [get_hw_probes -of_objects $vio]
if {[llength $probe]!=1} {error "Expected one VIO output"}
puts "BEFORE: [report_property -return_string $probe]"
set_property OUTPUT_VALUE [format %02X $mask] $probe
commit_hw_vio $vio
refresh_hw_vio $vio
puts "AFTER: [report_property -return_string $probe]"
puts "SNAPSHOT_FALLING_MASK=$mask"
close_hw_target
close_hw_manager
