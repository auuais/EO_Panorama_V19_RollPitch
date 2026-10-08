# Read one OSD crop from each requested camera during one JTAG connection.
if {[llength $argv]<2 || [llength $argv]>5} {error "Usage: capture_snapshots.tcl matching.ltx NEW_DIRECTORY ?2:3:4:5:6? ?keys:colon:separated? ?close:keys?"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
set cameras {2 3 4 5 6}
if {[llength $argv]>=3} {set cameras [split [string map {: ,} [lindex $argv 2]] ,]}
set keys {};set close_keys {}
if {[llength $argv]>=4 && [lindex $argv 3] ne "-"} {set keys [split [string map {: ,} [lindex $argv 3]] ,]}
if {[llength $argv]>=5 && [lindex $argv 4] ne "-"} {set close_keys [split [string map {: ,} [lindex $argv 4]] ,]}
set key_script [file join [file dirname [info script]] osd_keys.py]
set key_python [file join $::env(LOCALAPPDATA) Programs Python Python39 python.exe]
if {[info exists ::env(EO_OSD_PYTHON)]} {set key_python $::env(EO_OSD_PYTHON)}
foreach camera $cameras {if {$camera<2 || $camera>6} {error "Camera must be 2..6"}}
if {[file exists $out]} {error "Refusing existing directory"}
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
foreach camera $cameras {
    set index [expr {$camera-1}]
    set dir [file join $out cam$camera]
    file mkdir $dir
    set ila ""
    foreach candidate [get_hw_ilas -of_objects $dev] {
        if {[llength [get_hw_probes -quiet -of_objects $candidate -filter "NAME =~ *sync_snapshot_data${index}*"]]==1} {set ila $candidate;break}
    }
    if {$ila eq ""} {error "Snapshot ILA not found for camera $camera"}
    set probes {}
    foreach {port name width} {0 snapshot_pixels 64 1 snapshot_meta 32 2 snapshot_control 2} {
        set p [create_hw_probe -map [format {probe%d[%d:0]} $port [expr {$width-1}]] [format {%s[%d:0]} $name [expr {$width-1}]] $ila]
        lappend probes $p
        if {$port==2} {set control $p}
    }
    set f [open $dir/provenance.txt w]
    puts $f "LTX: $ltx\nStarted: [clock format [clock seconds]]\nDevice: $dev\nILA: $ila\nPhysical camera: $camera"
    close $f
    set old [dict create]
    foreach property {CONTROL.DATA_DEPTH CONTROL.WINDOW_COUNT CONTROL.TRIGGER_POSITION CONTROL.CAPTURE_MODE CONTROL.CAPTURE_CONDITION} {
        dict set old $property [get_property $property $ila]
    }
    set status [catch {
        set_property CONTROL.WINDOW_COUNT 1 $ila
        set_property CONTROL.DATA_DEPTH 32768 $ila
        set_property CONTROL.TRIGGER_POSITION 0 $ila
        set_property CONTROL.CAPTURE_MODE BASIC $ila
        set_property CONTROL.CAPTURE_CONDITION AND $ila
        set_property TRIGGER_COMPARE_VALUE {eq2'b11} $control
        set_property CAPTURE_COMPARE_VALUE {eq2'bX1} $control
        # Issue keys after JTAG setup so the menu cannot time out during connection.
        if {[llength $keys]} {
            puts [exec $key_python -E $key_script --cam $camera --keys {*}$keys --out $dir/keys.json]
            after 200
        }
        run_hw_ila $ila
        wait_on_hw_ila -timeout 20 $ila
        set data [upload_hw_ila_data $ila]
        write_hw_ila_data -csv_file $dir/snapshot.csv $data
        if {[llength $close_keys]} {puts [exec $key_python -E $key_script --cam $camera --keys {*}$close_keys --out $dir/close_keys.json]}
    } result options]
    dict for {property value} $old {set_property $property $value $ila}
    delete_hw_probe $probes
    if {$status} {close_hw_target;close_hw_manager;return -options $options $result}
    puts "SYNC_SNAPSHOT_CAMERA_DONE=$camera"
}
close_hw_target
close_hw_manager
puts "SYNC_SNAPSHOTS_DONE=$out"
