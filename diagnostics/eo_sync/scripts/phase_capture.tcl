# phase60 variant only. Changes sampler clocks, never camera settings or triggers.
if {[llength $argv]<3 || [llength $argv]>4} {error "Usage: phase_capture.tcl matching.ltx NEW_DIRECTORY sweep|set ?comma-separated-taps?"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
set mode [lindex $argv 2]
if {$mode ni {sweep set}} {error "Unknown phase action"}
set taps {0 28 56 84 112 140 168 196 224 252 280 308 336 364 392 420}
if {[llength $argv]==4} {set taps [split [string map {: ,} [lindex $argv 3]] ,]}
foreach tap $taps {if {![string is integer -strict $tap] || $tap<0 || $tap>447} {error "Tap must be 0..447"}}
if {$mode eq "set" && [llength $taps]!=5} {error "Set needs five camera targets"}
if {[file exists $out]} {error "Refusing existing output directory"}
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
set vio [get_hw_vios -of_objects $dev -filter {CELL_NAME =~ "*u_snapshot_select*"}]
if {[llength $vio]!=1} {error "Phase controller VIO not found"}
set phase_target [get_hw_probes -of_objects $vio -filter {NAME =~ "*phase_targets*"}]
if {[llength $phase_target]!=1} {error "Phase target probe not found"}
source [file join [file dirname [info script]] phase_status.tcl]
set phase_status [phase_native_probes $vio]
proc set_phase {values dir} {
    global phase_target phase_status vio
    set packed 0;set i 0
    foreach value $values {set packed [expr {$packed | ($value << (9*$i))}];incr i}
    set_property OUTPUT_VALUE [format %012llX $packed] $phase_target
    commit_hw_vio $vio
    set deadline [expr {[clock milliseconds]+5000}]
    set settled 0
    while {[clock milliseconds]<$deadline} {
        set raw [phase_read_hex $vio $phase_status]
        if {![regexp {^[0-9a-fA-F]+$} $raw]} {error "Invalid phase status $raw"}
        set word [expr 0x$raw]
        set current [expr {$word & ((1<<45)-1)}]
        set locked [expr {($word>>45)&31}]
        set busy [expr {($word>>50)&31}]
        set fault [expr {($word>>55)&31}]
        if {$fault} {error "Phase controller fault mask $fault"}
        if {$locked==31 && $busy==0 && $current==$packed} {set settled 1;break}
        after 25
    }
    if {!$settled} {error "Phase clocks failed to settle: $raw"}
    file mkdir $dir
    set f [open $dir/phase.txt w]
    puts $f "Targets, physical cameras 2..6: $values\nSettled status: $raw\nTime: [clock format [clock seconds]]"
    dict for {name probe} $phase_status {puts $f [report_property -return_string $probe]}
    close $f
    # Discard many complete rasters after any clock adjustment.
    after 500
    return $packed
}
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
set status [catch {
    if {$mode eq "set"} {set_phase $taps $out} else {
        set_property CONTROL.WINDOW_COUNT 1 $ila
        set_property CONTROL.DATA_DEPTH 4096 $ila
        set_property CONTROL.TRIGGER_POSITION 0 $ila
        set_property CONTROL.CAPTURE_MODE BASIC $ila
        set_property CONTROL.CAPTURE_CONDITION AND $ila
        set_property TRIGGER_COMPARE_VALUE {eq1'b1} $valid
        set_property CAPTURE_COMPARE_VALUE {eq1'b1} $valid
        foreach tap $taps {
            set dir [file join $out [format "phase_%03d" $tap]]
            set expected [set_phase [lrepeat 5 $tap] $dir]
            puts "PHASE_SWEEP_ARMED=$tap"
            run_hw_ila $ila
            wait_on_hw_ila -timeout 180 $ila
            set data [upload_hw_ila_data $ila]
            write_hw_ila_data -csv_file $dir/events_000.csv $data
            set raw [phase_read_hex $vio $phase_status]
            if {![regexp {^[0-9a-fA-F]+$} $raw]} {error "Invalid post-capture phase status"}
            set word [expr 0x$raw]
            if {($word & ((1<<45)-1))!=$expected || (($word>>45)&31)!=31 || ($word>>50)!=0} {
                error "Phase clocks lost qualification during capture: $raw"
            }
            set f [open $dir/phase.txt a];puts $f "After capture: $raw";close $f
            puts "PHASE_SWEEP_SAVED=$tap"
        }
    }
} result options]
delete_hw_probe $probes
close_hw_target
close_hw_manager
if {$status} {return -options $options $result}
puts "PHASE_ACTION_DONE=$out"
