# Supplemental read-only audit of the routed diagnostic checkpoint.
if {[llength $argv]!=1} {error "Usage: audit_routed.tcl BUILD_DIRECTORY"}
set out [file normalize [lindex $argv 0]]
open_checkpoint $out/Eo60InputTestTop_routed.dcp
set ddr [get_cells -hier -quiet -filter {REF_NAME == IDDRE1}]
if {[llength $ddr]} {error "Unexpected DDR input primitive in SDR diagnostic"}
set samplers [get_cells -hier -regexp {u_sampler/g_bit\[[0-9]+\]\.u_(rise|fall)$}]
if {[llength $samplers]!=32} {error "Expected 32 SDR input registers, found [llength $samplers]"}
set f [open $out/sampler_placement.csv w]
puts $f "cell,primitive,site,bel"
foreach cell $samplers {
    set site [get_property LOC $cell]
    if {![string match SLICE* $site]} {error "Sampler is not in fabric: $cell $site"}
    puts $f "$cell,[get_property REF_NAME $cell],$site,[get_property BEL $cell]"
}
close $f
report_bus_skew -file $out/bus_skew.rpt
report_timing -from [all_registers] -to [all_registers] -delay_type max -max_paths 20 -file $out/internal_setup.rpt
report_timing -from [all_registers] -to [all_registers] -delay_type min -max_paths 20 -file $out/internal_hold.rpt
puts "EO60_AUDIT_DONE: 32 fabric SDR input registers; no IDDRE1"
close_design
