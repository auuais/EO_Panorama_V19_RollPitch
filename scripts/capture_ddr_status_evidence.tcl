# Read-only ILA acquisition of the current DDR backend with matching probes.
if {[llength $argv] != 2} {error "Need matching LTX and NEW output directory"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
if {[file exists $out]} {error "Refusing to overwrite $out"}
file mkdir $out
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
open_hw_target
set dev [lindex [get_hw_devices] 0]
current_hw_device $dev
set_property PROBES.FILE $ltx $dev
set_property FULL_PROBES.FILE $ltx $dev
refresh_hw_device $dev
set ila ""
foreach cand [get_hw_ilas -of_objects $dev] {
    set p [get_hw_probes -of_objects $cand -filter {NAME =~ "*copy_active"} -quiet]
    if {[llength $p] == 1} {set ila $cand;set probe $p;break}
}
if {$ila eq ""} {error "DDR ILA not found"}
set meta [open [file join $out provenance.txt] w]
puts $meta "Started: [clock format [clock seconds]]\nLTX: $ltx\nDevice: $dev\nILA: $ila"
puts $meta [report_property -return_string $ila]
foreach p [get_hw_probes -of_objects $ila] {puts $meta [report_property -return_string $p]}
close $meta
set pos [get_property CONTROL.TRIGGER_POSITION $ila]
set cmp [get_property TRIGGER_COMPARE_VALUE $probe]
set_property CONTROL.TRIGGER_POSITION 32 $ila
set_property TRIGGER_COMPARE_VALUE eq1'b0 $probe
set status [catch {
    run_hw_ila $ila
    wait_on_hw_ila -timeout 5 $ila
    set data [upload_hw_ila_data $ila]
    write_hw_ila_data -csv_file [file join $out status.csv] $data
} result options]
set_property CONTROL.TRIGGER_POSITION $pos $ila
set_property TRIGGER_COMPARE_VALUE $cmp $probe
close_hw_target
close_hw_manager
if {$status} {return -options $options $result}
puts "DDR_STATUS_DONE=$out"
