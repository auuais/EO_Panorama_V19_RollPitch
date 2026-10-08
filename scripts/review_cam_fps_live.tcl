# Diagnostic capture only: does not program/reset the FPGA or write camera settings.
set root [file normalize [file join [file dirname [info script]] ..]]
set outdir [file join $root captures cam_fps_review [clock format [clock seconds] -format "%Y%m%d_%H%M%S"]]
file mkdir $outdir
set ltxfile [file join $root builds bit_archive 20261006_150257_camratemon_bd9af71 KintexTop_EO_IR_HD_SDI_panorama_base.ltx]
puts "REVIEW_OUTDIR=$outdir"
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
open_hw_target
set dev [lindex [get_hw_devices] 0]
current_hw_device $dev
set_property PROBES.FILE $ltxfile $dev
set_property FULL_PROBES.FILE $ltxfile $dev
refresh_hw_device $dev
set infofile [open [file join $outdir hardware.txt] w]
puts $infofile "LTX=$ltxfile"
puts $infofile [report_property -return_string $dev]
set rate_ila ""
set epoch_ila ""
foreach ila [get_hw_ilas -of_objects $dev] {
    puts $infofile [report_property -return_string $ila]
    foreach p [get_hw_probes -of_objects $ila] {
        puts $infofile "PROBE $p"
    }
    if {[llength [get_hw_probes -quiet -of_objects $ila -filter {NAME =~ "*eo_cam_rate_word*"}]]} {set rate_ila $ila}
    if {[llength [get_hw_probes -quiet -of_objects $ila -filter {NAME =~ "*/write_retiring"}]]} {set epoch_ila $ila}
}
close $infofile
if {$rate_ila eq ""} {error "Running design has no matching rate ILA; no reprogramming attempted"}
set manifest [open [file join $outdir times.csv] w]
puts $manifest "kind,index,before_ms,after_ms,file"
proc capture_review {ila prefix idx outdir manifest} {
    set_property CONTROL.TRIGGER_POSITION 0 $ila
    set t0 [clock milliseconds]
    run_hw_ila -trigger_now $ila
    wait_on_hw_ila -timeout 10 $ila
    set t1 [clock milliseconds]
    set data [upload_hw_ila_data $ila]
    set fname [format "%s%03d.csv" $prefix $idx]
    write_hw_ila_data -csv_file -force [file join $outdir $fname] $data
    puts $manifest "$prefix,$idx,$t0,$t1,$fname"
    flush $manifest
    puts "REVIEW_CAPTURE $prefix $idx $t0 $t1"
}
for {set i 0} {$i < 24} {incr i} {
    capture_review $rate_ila w $i $outdir $manifest
    # Vary the delay to avoid always sampling the same selector parity.
    after [expr {100 + ($i % 4) * 173}]
}
if {$epoch_ila ne ""} {
    for {set i 0} {$i < 8} {incr i} {
        capture_review $epoch_ila e $i $outdir $manifest
        after 300
    }
}
close $manifest
close_hw_target
close_hw_manager
puts "REVIEW_DONE=$outdir"
