# Dedicated inter-region routes from HD input banks to MMCMs, phase60 only.
set_property CLOCK_DEDICATED_ROUTE BACKBONE [get_nets -of_objects [get_pins u_clock1/O]]
set_property CLOCK_DEDICATED_ROUTE BACKBONE [get_nets -of_objects [get_pins u_clock2/O]]
set_property CLOCK_DEDICATED_ROUTE BACKBONE [get_nets -of_objects [get_pins u_clock3/O]]
set_property CLOCK_DEDICATED_ROUTE BACKBONE [get_nets -of_objects [get_pins u_clock4/O]]
set_property CLOCK_DEDICATED_ROUTE BACKBONE [get_nets -of_objects [get_pins u_clock5/O]]
