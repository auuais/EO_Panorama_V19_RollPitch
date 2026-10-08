# Standalone project: never opens or modifies the operational .xpr.
set package [file normalize [file join [file dirname [info script]] ..]]
set repo [file normalize [file join $package .. ..]]
if {[llength $argv]!=1} {error "Usage: build.tcl NEW_BUILD_DIRECTORY"}
set out [file normalize [lindex $argv 0]]
if {[file exists $out]} {error "Refusing existing build directory $out"}
file mkdir $out
file copy $package [file join $out source_snapshot]
set package [file join $out source_snapshot]
create_project eo60_input [file join $out project] -part xcku15p-ffve1517-2-i
set_param general.maxThreads 8
set_property target_language Verilog [current_project]
add_files [glob [file join $package rtl *.v]]
add_files -fileset constrs_1 [file join $package constraints eo60_board.xdc]
set_property top Eo60InputTestTop [current_fileset]
foreach {ip widths depth} {eo60_ila_ref {64 32 8 32 32} 8192 eo60_ila_raw {16 16 16} 4096} {
    create_ip -name ila -vendor xilinx.com -library ip -version 6.2 -module_name $ip
    set cfg [list CONFIG.C_NUM_OF_PROBES [llength $widths] CONFIG.C_DATA_DEPTH $depth CONFIG.C_INPUT_PIPE_STAGES 1 CONFIG.C_ADV_TRIGGER false CONFIG.C_EN_STRG_QUAL false]
    set i 0
    foreach width $widths {lappend cfg CONFIG.C_PROBE${i}_WIDTH $width;incr i}
    set_property -dict $cfg [get_ips $ip]
    generate_target all [get_ips $ip]
}
update_compile_order -fileset sources_1
puts "EO60_PHASE=SYNTHESIS"
launch_runs synth_1 -jobs 8
wait_on_run synth_1
if {![string match {*Complete*} [get_property STATUS [get_runs synth_1]]]} {error "Synthesis failed"}
puts "EO60_PHASE=IMPLEMENTATION"
launch_runs impl_1 -to_step route_design -jobs 8
wait_on_run impl_1
if {![string match {*Complete*} [get_property STATUS [get_runs impl_1]]]} {error "Implementation failed"}
open_run impl_1
report_timing_summary -delay_type min_max -max_paths 20 -report_unconstrained -file $out/timing_summary.rpt
report_timing -from [get_ports {CAM1_YOUT[*] CAM1_COUT[*]}] -delay_type max -max_paths 32 -file $out/input_setup_zero_reference.rpt
report_timing -from [get_ports {CAM1_YOUT[*] CAM1_COUT[*]}] -delay_type min -max_paths 32 -file $out/input_hold_zero_reference.rpt
report_cdc -details -file $out/cdc.rpt
report_clock_utilization -file $out/clocks.rpt
report_utilization -file $out/utilization.rpt
report_drc -file $out/drc.rpt
report_io -file $out/io.rpt
write_checkpoint $out/Eo60InputTestTop_routed.dcp
set f [open $out/timing_summary.rpt r];set txt [read $f];close $f
if {![regexp {\n\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+} $txt -> wns tns whs ths wpws tpws]} {error "Timing summary not found"}
foreach value [list $wns $tns $whs $ths $wpws $tpws] {
    if {$value<0} {error "Timing violation; bitstream withheld. WNS=$wns WHS=$whs WPWS=$wpws"}
}
set f [open $out/build_validation.json w]
puts $f "{\"wns_ns\":$wns,\"tns_ns\":$tns,\"whs_ns\":$whs,\"ths_ns\":$ths,\"wpws_ns\":$wpws,\"tpws_ns\":$tpws,\"camera_clock_mhz\":148.5,\"input_delays\":\"Zero-reference aperture model, not measured board/camera timing\",\"trigger_hz\":60,\"reference_hz\":27000000}"
close $f
puts "EO60_PHASE=GUARDED_BITSTREAM"
write_debug_probes $out/Eo60InputTestTop.ltx
write_bitstream $out/Eo60InputTestTop.bit
puts "EO60_BUILD_DONE=$out"
close_project
