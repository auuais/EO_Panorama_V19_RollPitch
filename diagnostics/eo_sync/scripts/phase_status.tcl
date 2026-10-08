# VIO uses native LTX probes: create_hw_probe aliases apply only to ILAs.
proc phase_native_probes {vio} {
    set result [dict create]
    foreach name {current locked busy fault} {
        set probe [get_hw_probes -of_objects $vio -filter "NAME =~ *phase_${name}*"]
        if {[llength $probe]!=1} {error "Missing/ambiguous phase_$name VIO probe"}
        dict set result $name $probe
    }
    return $result
}
proc phase_read_hex {vio probes} {
    refresh_hw_vio $vio
    set word 0
    foreach {name shift width} {current 0 45 locked 45 5 busy 50 5 fault 55 5} {
        set raw [get_property INPUT_VALUE [dict get $probes $name]]
        if {![regexp {^[0-9a-fA-F]+$} $raw]} {error "Invalid $name phase readback $raw"}
        set value [expr 0x$raw]
        if {$value >= (1<<$width)} {error "Oversized $name phase readback"}
        set word [expr {$word | ($value<<$shift)}]
    }
    return [format %015llX $word]
}
