# Volatile JTAG configuration only. No configuration-memory or MCU writes.
if {[llength $argv]!=1} {error "Usage: program.tcl diagnostic.bit"}
set bit [file normalize [lindex $argv 0]]
set ltx [file rootname $bit].ltx
if {![file exists $bit] || ![file exists $ltx]} {error "Need bitstream and matching LTX"}
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
set target [get_hw_targets]
if {[llength $target]!=1} {error "Expected exactly one connected target"}
# Debug hub is clocked from 27 MHz; keep TCK comfortably below ref/2.5.
set_property PARAM.FREQUENCY 6000000 $target
open_hw_target $target
set dev [get_hw_devices -quiet xcku15p_0]
if {[llength $dev]!=1} {error "Expected xcku15p_0"}
current_hw_device $dev
set_property PROGRAM.FILE $bit $dev
set_property PROBES.FILE $ltx $dev
set_property FULL_PROBES.FILE $ltx $dev
program_hw_devices $dev
refresh_hw_device $dev
puts "EO60_PROGRAMMED=$bit"
close_hw_target
close_hw_manager
