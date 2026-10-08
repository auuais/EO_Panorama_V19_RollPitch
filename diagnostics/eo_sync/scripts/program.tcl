# Volatile FPGA programming only. Never writes configuration flash.
if {[llength $argv]!=1} {error "Usage: program.tcl bitstream.bit"}
set bit [file normalize [lindex $argv 0]]
set ltx [file rootname $bit].ltx
if {![file exists $bit] || ![file exists $ltx]} {error "Bitstream and matching LTX required"}
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
set target [get_hw_targets]
if {[llength $target]!=1} {error "Expected exactly one target"}
set_property PARAM.FREQUENCY 6000000 $target
open_hw_target $target
set dev [get_hw_devices -quiet xcku15p_0]
if {[llength $dev]!=1} {error "Expected KU15P"}
current_hw_device $dev
set_property PROBES.FILE $ltx $dev
set_property FULL_PROBES.FILE $ltx $dev
set_property PROGRAM.FILE $bit $dev
program_hw_devices $dev
refresh_hw_device $dev
puts "PROGRAMMED=$bit"
close_hw_target
close_hw_manager
