# Resume an explicitly named failed phase60 build after fixing only constraints.
# Preserve the original source and failed implementation log for provenance.
if {[llength $argv]!=1} {error "Usage: resume_phase_build.tcl FAILED_BUILD_DIRECTORY"}
set out [file normalize [lindex $argv 0]]
set package [file normalize [file join [file dirname [info script]] ..]]
set saved $out/source_snapshot/constraints/eo_sync_board.xdc
if {[file exists $out/EoSyncTop.bit] || [file exists ${saved}.before_backbone]} {error "Build already completed or resume already attempted"}
file copy $saved ${saved}.before_backbone
file copy -force $package/constraints/eo_sync_board.xdc $saved
file copy -force $package/constraints/eo_sync_phase60.xdc $out/source_snapshot/constraints/eo_sync_phase60.xdc
file copy $out/project/eo_sync.runs/impl_1/runme.log $out/placement_before_backbone.log
open_project $out/project/eo_sync.xpr
set_param general.maxThreads 8
add_files -fileset constrs_1 $out/source_snapshot/constraints/eo_sync_phase60.xdc
if {[get_property GENERIC [current_fileset]] ne "PHASE_CLOCK=1"} {error "Expected phase60 variant"}
reset_run impl_1
launch_runs impl_1 -to_step route_design -jobs 8
wait_on_run impl_1
if {![string match {*Complete*} [get_property STATUS [get_runs impl_1]]]} {error "Implementation failed"}
# Reuse the identical timing checks and guarded export from the main builder.
set f [open $package/scripts/build.tcl r];set builder [read $f];close $f
set start [string first "open_run impl_1\n" $builder]
if {$start<0} {error "Guarded export section missing"}
eval [string range $builder $start end]
