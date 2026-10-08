# Standalone project: never opens or modifies the operational .xpr.
set package [file normalize [file join [file dirname [info script]] ..]]
set repo [file normalize [file join $package .. ..]]
if {[llength $argv]<1 || [llength $argv]>3} {error "Usage: build.tcl NEW_BUILD_DIRECTORY ?direct|phase60? ?trigger_hz=60?"}
set phase_clock 0
set trigger_hz 60
if {[llength $argv]>=2} {
    if {[lindex $argv 1] ni {direct phase60}} {error "Unknown variant"}
    set phase_clock [expr {[lindex $argv 1] eq "phase60"}]
}
if {[llength $argv]==3} {set trigger_hz [lindex $argv 2]}
if {$trigger_hz ni {30 60}} {error "Supported trigger rates: 30 or 60 Hz"}
set out [file normalize [lindex $argv 0]]
if {[file exists $out]} {error "Refusing existing build directory $out"}
file mkdir $out
set f [open $out/build_options.tcl w]
puts $f "set phase_clock $phase_clock\nset trigger_hz $trigger_hz"
close $f
file copy $package [file join $out source_snapshot]
set package [file join $out source_snapshot]
create_project eo_sync [file join $out project] -part xcku15p-ffve1517-2-i
set_param general.maxThreads 8
set_property target_language Verilog [current_project]
add_files [glob [file join $package rtl *.v]]
add_files -fileset constrs_1 [file join $package constraints eo_sync_board.xdc]
if {$phase_clock} {add_files -fileset constrs_1 [file join $package constraints eo_sync_phase60.xdc]}
set_property top EoSyncTop [current_fileset]
set_property generic [list PHASE_CLOCK=$phase_clock TRIGGER_HZ=$trigger_hz] [current_fileset]
foreach {ip widths depth} {eo_sync_ila {64 256 1 16 32} 16384 eo_sync_snapshot_ila {64 32 2} 32768} {
    create_ip -name ila -vendor xilinx.com -library ip -version 6.2 -module_name $ip
    set cfg [list CONFIG.C_NUM_OF_PROBES [llength $widths] CONFIG.C_DATA_DEPTH $depth CONFIG.C_INPUT_PIPE_STAGES 1 CONFIG.C_ADV_TRIGGER false CONFIG.C_EN_STRG_QUAL false]
    set i 0
    foreach width $widths {lappend cfg CONFIG.C_PROBE${i}_WIDTH $width;incr i}
    if {$ip eq "eo_sync_ila" || $ip eq "eo_sync_snapshot_ila"} {lappend cfg CONFIG.C_EN_STRG_QUAL true CONFIG.C_INPUT_PIPE_STAGES 3}
    set_property -dict $cfg [get_ips $ip]
    generate_target all [get_ips $ip]
}
update_compile_order -fileset sources_1
create_ip -name vio -vendor xilinx.com -library ip -version 3.0 -module_name eo_sync_vio
set_property -dict [list CONFIG.C_NUM_PROBE_IN 1 CONFIG.C_PROBE_IN0_WIDTH 60 CONFIG.C_NUM_PROBE_OUT 3 CONFIG.C_PROBE_OUT0_WIDTH 5 CONFIG.C_PROBE_OUT0_INIT_VAL 0x00 CONFIG.C_PROBE_OUT1_WIDTH 45 CONFIG.C_PROBE_OUT1_INIT_VAL 0x000000000000 CONFIG.C_PROBE_OUT2_WIDTH 1 CONFIG.C_PROBE_OUT2_INIT_VAL 0x0] [get_ips eo_sync_vio]
generate_target all [get_ips eo_sync_vio]
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
report_timing -from [get_ports {CAM*_YOUT[*] CAM*_COUT[*]}] -delay_type max -max_paths 32 -file $out/input_setup_zero_reference.rpt
report_timing -from [get_ports {CAM*_YOUT[*] CAM*_COUT[*]}] -delay_type min -max_paths 32 -file $out/input_hold_zero_reference.rpt
report_cdc -details -file $out/cdc.rpt
report_clock_utilization -file $out/clocks.rpt
report_utilization -file $out/utilization.rpt
report_drc -file $out/drc.rpt
report_io -file $out/io.rpt
write_checkpoint $out/EoSyncTop_routed.dcp
set f [open $out/timing_summary.rpt r];set txt [read $f];close $f
if {![regexp {\n\s*(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\d+\s+\d+} $txt -> wns tns whs ths wpws tpws]} {error "Timing summary not found"}
foreach value [list $wns $tns $whs $ths $wpws $tpws] {
    if {$value<0} {error "Timing violation; bitstream withheld. WNS=$wns WHS=$whs WPWS=$wpws"}
}
set f [open $out/build_validation.json w]
puts $f "{\"wns_ns\":$wns,\"tns_ns\":$tns,\"whs_ns\":$whs,\"ths_ns\":$ths,\"wpws_ns\":$wpws,\"tpws_ns\":$tpws,\"camera_clock_mhz\":148.5,\"input_delays\":\"Zero-reference aperture model, not measured board/camera timing\",\"trigger_hz\":$trigger_hz,\"trigger_high_us\":2000,\"reference_hz\":27000000}"
close $f
puts "EO60_PHASE=GUARDED_BITSTREAM"
write_debug_probes $out/EoSyncTop.ltx
write_bitstream $out/EoSyncTop.bit
puts "EO60_BUILD_DONE=$out"
close_project
