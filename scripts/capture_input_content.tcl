# Capture the passive content-monitor diagnostic image. Never programs FPGA.
# Usage: vivado -mode batch -source scripts/capture_input_content.tcl
#        -tclargs matching.ltx new-output-directory ?blocks=24?
if {[llength $argv]<2} {error "Need matching LTX and new output directory"}
set ltx [file normalize [lindex $argv 0]]
set out [file normalize [lindex $argv 1]]
set blocks 24
if {[llength $argv]>2} {set blocks [lindex $argv 2]}
if {[file exists $out]} {error "Refusing to overwrite capture directory $out"}
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
    set p [get_hw_probes -quiet -of_objects $cand -filter {NAME =~ "*eo_content_event_word*"}]
    if {[llength $p]==1} {set ila $cand;set probe $p;break}
}
if {$ila eq ""} {error "No content event probe in connected FPGA/LTX"}
set meta [open [file join $out provenance.txt] w]
puts $meta "Started: [clock format [clock seconds]]\nLTX: $ltx\nDevice: $dev\nILA: $ila\nProbe: $probe"
puts $meta [report_property -return_string $dev]
close $meta
set saved_depth [get_property CONTROL.DATA_DEPTH $ila]
set saved_count [get_property CONTROL.WINDOW_COUNT $ila]
set saved_pos [get_property CONTROL.TRIGGER_POSITION $ila]
set saved_compare [get_property TRIGGER_COMPARE_VALUE $probe]
set_property CONTROL.TRIGGER_POSITION 0 $ila
set_property CONTROL.DATA_DEPTH 32 $ila
set_property CONTROL.WINDOW_COUNT 256 $ila
set_property TRIGGER_COMPARE_VALUE "eq64'b1[string repeat X 63]" $probe
set status [catch {
    for {set i 0} {$i<$blocks} {incr i} {
        run_hw_ila $ila
        wait_on_hw_ila -timeout 15 $ila
        set data [upload_hw_ila_data $ila]
        write_hw_ila_data -csv_file -force [file join $out [format "events_%03d.csv" $i]] $data
        puts "CONTENT_BLOCK=$i"
    }
} result options]
set_property CONTROL.WINDOW_COUNT $saved_count $ila
set_property CONTROL.DATA_DEPTH $saved_depth $ila
set_property CONTROL.TRIGGER_POSITION $saved_pos $ila
set_property TRIGGER_COMPARE_VALUE $saved_compare $probe
close_hw_target
close_hw_manager
if {$status} {return -options $options $result}
puts "CONTENT_CAPTURE_DONE=$out"
