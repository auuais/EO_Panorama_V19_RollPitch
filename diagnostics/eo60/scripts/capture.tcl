# Does not program hardware. Requires the exact matching LTX.
if {[llength $argv]<2} {error "Usage: capture.tcl matching.ltx NEW_DIRECTORY ?blocks=12?"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
set blocks 12
if {[llength $argv]>2} {set blocks [lindex $argv 2]}
if {[file exists $out]} {error "Refusing existing evidence directory"}
file mkdir $out
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
set target [get_hw_targets]
if {[llength $target]!=1} {error "Expected exactly one connected target"}
set_property PARAM.FREQUENCY 6000000 $target
open_hw_target $target
set dev [lindex [get_hw_devices] 0]
set_property PROBES.FILE $ltx $dev
set_property FULL_PROBES.FILE $ltx $dev
refresh_hw_device $dev
set ila ""
foreach candidate [get_hw_ilas -of_objects $dev] {
    set p [get_hw_probes -quiet -of_objects $candidate -filter {NAME =~ "*eo60_event_word*"}]
    if {[llength $p]==1} {set ila $candidate;set probe $p;break}
}
if {$ila eq ""} {error "EO60 diagnostic probe not found"}
# Name complete physical ports consistently: synthesis can split off constant
# low bits (notably the eight zero frequency bits). Map sampled bits, not literals.
# AMD UG835 create_hw_probe: https://docs.amd.com/r/2023.2-English/ug835-vivado-tcl-commands/create_hw_probe
set user_probes {}
foreach {port name width} {0 eo60_capture_event_word 64 1 eo60_capture_pclk_hz 32 2 eo60_capture_trigger_edges 8 3 eo60_capture_seconds 32 4 eo60_capture_signature 32} {
    set map [format {probe%d[%d:0]} $port [expr {$width-1}]]
    set p [create_hw_probe -map $map [format {%s[%d:0]} $name [expr {$width-1}]] $ila]
    lappend user_probes $p
    if {$port==0} {set probe $p}
}
set f [open $out/provenance.txt w]
puts $f "LTX: $ltx\nStarted: [clock format [clock seconds]]\nDevice: $dev\nILA: $ila"
puts $f [report_property -return_string $dev]
foreach p [get_hw_probes -of_objects $ila] {puts $f [report_property -return_string $p]}
close $f
set depth [get_property CONTROL.DATA_DEPTH $ila]
set count [get_property CONTROL.WINDOW_COUNT $ila]
set pos [get_property CONTROL.TRIGGER_POSITION $ila]
set compare [get_property TRIGGER_COMPARE_VALUE $probe]
set_property CONTROL.TRIGGER_POSITION 0 $ila
set_property CONTROL.DATA_DEPTH 32 $ila
set_property CONTROL.WINDOW_COUNT 256 $ila
set_property TRIGGER_COMPARE_VALUE "eq64'b1[string repeat X 63]" $probe
set status [catch {
    for {set i 0} {$i<$blocks} {incr i} {
        run_hw_ila $ila
        wait_on_hw_ila -timeout 20 $ila
        set data [upload_hw_ila_data $ila]
        write_hw_ila_data -csv_file [file join $out [format "events_%03d.csv" $i]] $data
        puts "EO60_BLOCK=$i"
    }
} result options]
set_property CONTROL.WINDOW_COUNT $count $ila
set_property CONTROL.DATA_DEPTH $depth $ila
set_property CONTROL.TRIGGER_POSITION $pos $ila
set_property TRIGGER_COMPARE_VALUE $compare $probe
delete_hw_probe $user_probes
close_hw_target
close_hw_manager
if {$status} {return -options $options $result}
puts "EO60_CAPTURE_DONE=$out"
