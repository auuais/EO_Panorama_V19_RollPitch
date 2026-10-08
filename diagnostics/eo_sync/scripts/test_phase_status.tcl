# Run with Vivado -mode batch -source ...; no hardware connection or mutation.
source [file join [file dirname [info script]] phase_status.tcl]
proc refresh_hw_vio {vio} {}
set probes [dict create current current locked locked busy busy fault fault]
set values [dict create current 142A150A8542 locked 1F busy 00 fault 00]
proc get_property {property probe} {
    global values
    if {$property ne "INPUT_VALUE"} {error "Unexpected read"}
    return [dict get $values $probe]
}
set actual [phase_read_hex mocked_vio $probes]
if {$actual ne "003F42A150A8542"} {error "60-bit VIO status truncated: $actual"}
set word [expr 0x$actual]
for {set i 0} {$i<5} {incr i} {
    if {(($word>>(9*$i))&511)!=322} {error "Camera phase target ordering lost"}
}
dict set values fault 10
set actual [phase_read_hex mocked_vio $probes]
if {(([expr 0x$actual]>>55)&31)!=16} {error "Highest fault bit lost"}
dict set values locked INVALID
if {![catch {phase_read_hex mocked_vio $probes}]} {error "Malformed VIO readback accepted"}
puts "PASS: 60-bit status preserves all camera targets, lock bits and high fault bits"
exit
