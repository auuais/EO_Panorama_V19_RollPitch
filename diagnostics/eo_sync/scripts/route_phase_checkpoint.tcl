# Resume from an optimized checkpoint, applying the dedicated clock constraints.
if {[llength $argv]!=1} {error "Usage: route_phase_checkpoint.tcl BUILD_DIRECTORY"}
set out [file normalize [lindex $argv 0]]
set package [file normalize [file join [file dirname [info script]] ..]]
if {[file exists $out/EoSyncTop.bit]} {error "Refusing to overwrite existing bitstream"}
file copy -force $package/constraints/eo_sync_phase60.xdc $out/source_snapshot/constraints/eo_sync_phase60.xdc
file copy -force $package/constraints/eo_sync_board.xdc $out/source_snapshot/constraints/eo_sync_board.xdc
set_param general.maxThreads 8
open_checkpoint $out/project/eo_sync.runs/impl_1/EoSyncTop_opt.dcp
read_xdc $out/source_snapshot/constraints/eo_sync_phase60.xdc
set f [open $out/dedicated_clock_routes.txt w]
foreach n {1 2 3 4 5} {
    set net [get_nets -of_objects [get_pins u_clock${n}/O]]
    if {[get_property CLOCK_DEDICATED_ROUTE $net] ne "BACKBONE"} {error "Clock routing constraint not applied"}
    puts $f "$net [get_property CLOCK_DEDICATED_ROUTE $net]"
}
close $f
place_design
phys_opt_design
route_design
# Same guarded exports as the standard project build, without open_run.
set f [open $package/scripts/build.tcl r];set builder [read $f];close $f
set start [string first "report_timing_summary -delay_type" $builder]
if {$start<0} {error "Guarded export section missing"}
eval [string range $builder $start end]
