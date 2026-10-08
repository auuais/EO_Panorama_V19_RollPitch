# Read-only audit of the routed checkpoint; external timing remains unmeasured.
if {[llength $argv]!=1} {error "Usage: audit_routed.tcl BUILD_DIRECTORY"}
set out [file normalize [lindex $argv 0]]
open_checkpoint $out/EoSyncTop_routed.dcp
if {[llength [get_cells -hier -quiet -filter {REF_NAME == IDDRE1}]]} {error "Unexpected DDR input primitive"}
set samplers [get_cells -hier -regexp {u_sampler[1-5]/g_bit\[[0-9]+\]\.u_(rise|fall)$}]
if {[llength $samplers]!=160} {error "Expected 160 SDR input registers, found [llength $samplers]"}
set f [open $out/sampler_placement.csv w]
puts $f "cell,primitive,site,bel"
foreach cell $samplers {
    set site [get_property LOC $cell]
    if {![string match SLICE* $site]} {error "Sampler is not in fabric: $cell $site"}
    puts $f "$cell,[get_property REF_NAME $cell],$site,[get_property BEL $cell]"
}
close $f
set mmcms [get_cells -hier -quiet -filter {REF_NAME == MMCME4_ADV}]
if {[llength $mmcms]} {
    if {[llength $mmcms]!=5} {error "Expected five independent phase MMCMs"}
    set f [open $out/phase_clock_placement.txt w]
    foreach n {1 2 3 4 5} {
        set raw [get_nets -of_objects [get_pins u_clock${n}/O]]
        if {[get_property CLOCK_DEDICATED_ROUTE $raw] ne "ANY_CMT_COLUMN"} {error "Unexpected phase-clock route"}
        puts $f "$raw [get_property CLOCK_DEDICATED_ROUTE $raw]"
        foreach cell [list u_clock${n} g_phase${n}.u_phase/u_mmcm g_phase${n}.u_phase/u_sample g_phase${n}.u_phase/u_feedback] {
            puts $f "$cell [get_property LOC [get_cells $cell]]"
        }
    }
    close $f
    if {[llength [get_nets -hier -quiet -filter {CLOCK_DEDICATED_ROUTE == FALSE}]]} {error "Fabric clock routing override found"}
}
report_bus_skew -file $out/bus_skew.rpt
report_timing -from [all_registers] -to [all_registers] -delay_type max -max_paths 20 -file $out/internal_setup.rpt
report_timing -from [all_registers] -to [all_registers] -delay_type min -max_paths 20 -file $out/internal_hold.rpt
puts "SYNC_AUDIT_DONE: 160 fabric SDR input registers; no IDDRE1"
close_design
