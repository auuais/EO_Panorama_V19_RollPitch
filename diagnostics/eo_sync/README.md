# Five-camera EO synchronization diagnostic

Physical EO cameras 2–6 map to FPGA CAM1–CAM5. Camera 1 is untouched.
This standalone volatile diagnostic observes BT.1120 at 1080p30 or 1080p60.
It does not provide USB video, stabilize images, or write configuration flash.

## Measurement

Each input is sampled independently on both PCLK edges. Ten strict raster
monitors report complete-frame CRC, central 96×96 ROI CRC and geometry. Every
monitor's toggle is synchronized to one 27 MHz oscillator. Each channel latches
its own timestamp before round-robin serialization. Simultaneous channel events
therefore do not acquire the serializer's staggered delay. The time quantum is
37.037 ns nominal; clock-domain quantization and board/camera delays remain.

One 60 Hz, 2 ms-high signal drives all five trigger outputs. Both output edges
are recorded by the same timestamp logic. This verifies the FPGA-generated
signal, not electrical arrival or acceptance at each camera. OFF trigger
polarity is recorded in the camera OSD. No physical exposure-start signal is
observed. Raster alignment must not be described as exposure synchronization.

Event metadata: kind [63:56] (1 frame, 2 trigger rise, 3 trigger fall), channel
[55:48], timestamp [47:0]. Frame channel = 2×(physical camera−2)+phase, where
phase 0 is rising and 1 falling. Trigger channel is 10. Probe 4 signature is
`E05C0001`. Probe 3 is a saturating overrun indicator; any nonzero value rejects
the capture. It is not an exact count of lost events.

Payload bit fields: full CRC [31:0], ROI CRC [63:32], active pixels [85:64],
active lines [97:86], sequence [113:98], EAV count [125:114], flags [133:126],
bad Y marker [145:134], bad chroma marker [157:146], frame clocks [191:160],
line maximum [207:192], line minimum [223:208]. The report is published at the
next active-raster boundary and describes the preceding complete raster.

A valid record requires 2,073,600 pixels, 1080 active lines, 1125 EAVs,
2,475,000 pixel clocks, line minimum=maximum=2200, flags=3 and no bad Y/C markers.
CRC changes require an independent Freeze negative control before they can be
used as image-update evidence. A change alone does not prove a new exposure.

Each camera also has a falling-edge luminance crop ILA for direct OSD readback:
original x=512…1535, y=128…1023, taking every second pixel and row, 512×448.
No resizing or filtering occurs in acquisition. Its 32768 packets include one
complete 28672-packet crop and the beginning of the next crop.

## Reproduce

Use Vivado 2025.2, KU15P, one local hardware target and JTAG at 6 MHz. Camera and
serial mutations must remain sequential. Keep original OSD settings, current
operational bitstream/LTX and display/pose readbacks for restoration.

1. `powershell -File diagnostics/eo_sync/scripts/simulate.ps1`
2. `python diagnostics/eo_sync/scripts/test_decoders.py`
3. `vivado -mode batch -source diagnostics/eo_sync/scripts/build.tcl -tclargs NEW_BUILD_DIRECTORY`
4. Inspect timing, CDC and IO reports. The build rejects failing internal setup,
   hold or pulse timing. Zero-reference input constraints are not external
   camera/board timing signoff.
5. `vivado -mode batch -source diagnostics/eo_sync/scripts/program.tcl -tclargs NEW_BUILD_DIRECTORY/EoSyncTop.bit`
6. `vivado -mode batch -source diagnostics/eo_sync/scripts/capture.tcl -tclargs MATCHING.ltx NEW_CAPTURE_DIRECTORY 2`
7. `python diagnostics/eo_sync/scripts/decode_events.py NEW_CAPTURE_DIRECTORY`
8. For OSD evidence, send explicit keys with `osd_keys.py`, then use
   `capture_snapshot.tcl MATCHING.ltx NEW_DIRECTORY CAMERA_2_TO_6` and
   `decode_snapshot.py NEW_DIRECTORY`. ACKs never substitute for OSD readback.

## Comparison protocol

Hold exposure, gain and processing constant within each format. Verify mode,
format and shutter directly on all five OSDs. Allow settling after changes.
Capture ExtTrig, FreeRun, then ExtTrig again at each format. Keep the generated
trigger at 60 Hz throughout. Record Freeze controls separately with menus
closed. Restore every camera setting and the operational FPGA afterward.

Never bridge the dead time between JTAG capture blocks. Decode each block and
sampling phase separately. Match events by common timestamps, not sequence
numbers (camera sequence origins differ). Report signed offsets to camera 2
and the shortest circular arc containing all five phases, in microseconds.
This avoids a frame-period jump when a tightly aligned group straddles an
arbitrary period boundary. In free run, it describes closest raster phases,
not a shared exposure cohort. Preserve each camera's rate, valid geometry,
sequence gaps, and CRC-change counts. Do not turn invalid or missing records
into zero spread. Report image timing separately from raster timing and state
whether the Freeze control qualified it.
