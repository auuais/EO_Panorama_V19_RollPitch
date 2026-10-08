# Camera 2 direct ILA image and OSD diagnostic

This standalone KU15P design extends `diagnostics/eo60` with an ILA holding two consecutive 960x540 luminance sample arrays. It observes every second pixel and row without filtering. There is no DDR/video renderer. Camera 2 uses board signals `CAM1_*`. All follower trigger pins remain 60 Hz with 2 ms high pulses.

## Qualification limit discovered on 8 October 2026

**Use reconstructed images for directly reviewed OSD evidence. This build is not a qualified whole-frame fresh-FPS meter at 1080p60.** With camera Freeze ON, its full Y/C CRC changes while its central ROI CRC and sampled Y image stay constant. Disabling DNR does not remove the full-CRC changes. The original r2 diagnostic fails more severely: both CRCs change on all 248 adjacent frozen comparisons. The sampled frozen image is byte-identical before and after that original-r2 control. At 1080p30, the snapshot build's frozen full and ROI CRCs stay constant on both edges.

The exact source of the 60-mode variation has not been isolated. Geometry and internal timing do not establish external active-pixel integrity. The negative control takes precedence over the decoder's `content_rate_accepted` flag. Prior 60 fresh-FPS conclusions are withdrawn.

Direct OSD images show 1080p60 and show a 30-mode 1/30 s preselection becoming **1/60 s** after switching format, without a shutter write. One slower step at 60-mode displays `2x`. With DNR OFF, both `2x` and 1/60 s show about 30 ROI changes/s at 60 rasters/s. This is a local image measurement, not proof of whole-frame FPS or physical integration time.

Results: `captures/eo60_verify_20261008/verification_results.json`, `final_state.json`, and the final section of `docs/TEST_EO_CAMERA_CONTENT_20261007.md`. The consolidated workbook preserves raw counts and marks earlier 60 fresh-FPS interpretations unverified.

## Build and validation

Vivado 2025.2, `xcku15p-ffve1517-2-i`:

```text
vivado -mode batch -source diagnostics/eo60_snapshot/scripts/build.tcl -tclargs NEW_BUILD_DIRECTORY
vivado -mode batch -source diagnostics/eo60_snapshot/scripts/audit_routed.tcl -tclargs BUILD_DIRECTORY
```

Tested build: `builds/eo60_snapshot_20261008_r1`. It contains frozen RTL/constraints, bit/LTX, routed checkpoint, reports and `manifest.json`.

- Bit SHA-256: `5f8e2eb39d7676f7b250dfdcdba9c5b2d584144ed55d89a121cb1c57a7083a62`.
- LTX SHA-256: `904156adff3c76a82256dfde12de41cc08696743b4b7cf4bd9c8aa39f4c001cc`.
- WNS +1.160 ns, WHS +0.001 ns, WPWS +2.825 ns; negative totals zero; bus skew passes.
- Audit: 32 fabric SDR input registers, zero IDDRE1.
- External input delays are a zero-reference aperture model, not measured camera/PCB bounds.
- `sim/tb_Eo60Snapshot.sv` passed pixel packing, decimation, coordinates, sequence/SOF and packet-count checks in Vivado simulation.
- `sim/test_decode_snapshot.py` passed independent full-image coordinate/byte order, sequence wrap, single-pixel difference, probe alias disambiguation and missing-packet rejection checks.

## Acquisition

Use matching LTX, one JTAG connection at a time, and 6 MHz JTAG. `program.tcl` writes volatile FPGA configuration only. Record and restore camera/display settings separately.

```text
vivado -mode batch -source diagnostics/eo60_snapshot/scripts/program.tcl -tclargs PATH.bit
vivado -mode batch -source diagnostics/eo60_snapshot/scripts/capture_snapshot.tcl -tclargs PATH.ltx NEW_CAPTURE_DIRECTORY
python diagnostics/eo60_snapshot/scripts/decode_snapshot.py NEW_CAPTURE_DIRECTORY
```

Port 0 contains eight Y bytes, earliest byte most significant. Port 1 is `{frame_sequence[14:0], row/2[9:0], pixel_group[6:0]}`. Port 2 bit 0 is valid; bit 1 marks row 0/group 0. Each frame is 120 groups x 540 rows = 64,800 packets. The 131,072 valid samples contain two complete frames and 1,472 packets of the next. Decoder guards include valid coordinates, duplicate/missing packets, consecutive sequences and SOF agreement. PNG values are unfiltered measured samples.

The copied CRC capture/decoder scripts preserve the original telemetry protocol. Their cadence gate does **not** apply the independent Freeze control. Use the curated verification results for interpretation. Original protocol details remain in `diagnostics/eo60/README.md`.

Live helper scripts/logs: `.tmpCRC/eo60_verify_20261008`. Raw evidence: `captures/eo60_verify_20261008`. Capture/decoder/program helpers were completed after the build's initial source snapshot; they do not change the bitstream.

## Required test before claiming 60 fresh input FPS

First obtain stable full Y/C capture with verified Freeze ON at 1080p60, across multiple static scenes. Investigate input sampling phase, placement and external clock-to-data margin. Then repeat unfrozen captures with direct 60-mode shutter readback and a calibrated optical time pattern. Measure integration independently if that is the desired claim; the camera's configurable strobe width is not exposure-time readback.
