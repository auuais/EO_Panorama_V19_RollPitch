# Give dbg_ila_1 a twelfth probe, 64 bits, for EoCamFrameRateMon's word.
#
# Done through the IP customisation rather than by editing the .xci: the file
# carries the same parameter in two sections plus generated output products,
# and editing one by hand leaves the IP inconsistent.
#
#   vivado -mode batch -source scripts/add_cam_rate_probe.tcl
set root [file normalize [file join [file dirname [info script]] ..]]
open_project [file join $root EO_Panorama_V19_M1.xpr]
set ip [get_ips dbg_ila_1]
puts "BEFORE probes=[get_property CONFIG.C_NUM_OF_PROBES $ip]"
set_property -dict [list CONFIG.C_NUM_OF_PROBES {12} CONFIG.C_PROBE11_WIDTH {64}] $ip
puts "AFTER  probes=[get_property CONFIG.C_NUM_OF_PROBES $ip] probe11=[get_property CONFIG.C_PROBE11_WIDTH $ip]"
generate_target all $ip
puts "GENERATED"
close_project
