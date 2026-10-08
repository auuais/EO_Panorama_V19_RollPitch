# EO cameras 2–6: synchronization comparison

Bench measurements, 8 October 2026, Asia/Seoul. This report is separate from
the earlier input-FPS investigation.

**At the tested 60 Hz trigger rate, the five BT.1120 raster arrivals were not
aligned in either ExtTrig or FreeRun, at either 1080p30 or 1080p60.** Relative
phase continued drifting, including after switching back to ExtTrig. These
measurements do not determine physical sensor-exposure synchronization.

## Results

All conditions used physical cameras 2–6, shutter 1/240 s, gain 0 dB and DNR
2D+3D. The FPGA generated the same 60 Hz, 2 ms-high trigger throughout. FreeRun
ignores that input. A and B are the first and return ExtTrig observations.

| Format / mode | Observed s | Raster spread median ms | Raster P95 ms | Raster max ms | Qualified payload changes/s | Payload spread median ms |
|---|---:|---:|---:|---:|---:|---:|
| 1080p30 ExtTrig A | 82.125 | 15.415 | 15.490 | 15.499 | ~30, full raster | 15.415 |
| 1080p30 FreeRun | 78.235 | 16.311 | 16.399 | 16.407 | ~30, full raster | 16.311 |
| 1080p30 ExtTrig B | 83.194 | 17.269 | 17.361 | 17.369 | ~30, full raster | 17.269 |
| 1080p60 ExtTrig A | 49.624 | 9.617 | 9.672 | 9.677 | ~30, central ROI | 13.183 |
| 1080p60 FreeRun | 49.638 | 8.852 | 8.909 | 8.915 | ~60, central ROI | 8.852 |
| 1080p60 ExtTrig B | 49.620 | 8.114 | 8.171 | 8.177 | ~30, central ROI | 20.848 |

The numerical difference between sequential capture medians is **not** a
measured improvement caused by either mode. Relative phases evolve with wall
time. For example, camera 3 drift relative to camera 2 was approximately
4.28–4.30 microseconds/second at 1080p30 and 4.55–4.63 microseconds/second at
1080p60, in both modes. Raster cadence stayed approximately 30 or 60 Hz,
respectively. The ROI-change rate reversal at 1080p60 repeated on returning
to ExtTrig. CRC changes remain observations of transmitted bytes, not proof
of distinct sensor exposures.

## Qualification and interpretation

Full-raster CRC in this report covers the 1920×1080 active Y/C payload,
excluding blanking bytes.

- Revision 1, all rising edges, qualified the 1080p30 inputs: a 41.188 s Freeze
  control had 100% strict geometry, zero sequence gaps and zero full/ROI CRC
  changes on all five cameras.
- Initial 1080p60 r1/r2 captures failed input integrity and were excluded.
  Revision 3 uses five independently controlled MMCMs and both sampling edges.
  Full-cycle coarse and frozen fine sweeps preceded selection of rising tap
  322 on every camera. Clocks were locked, settled and fault-free before and
  after every qualified capture block.
- The 24.819 s 1080p60 Freeze control had 1,489–1,490 complete records per
  camera, 100% strict geometry, zero gaps and zero central 96×96 ROI changes.
  Cameras 2–5 had stable full CRCs. Camera 6 had 1,486 full CRC changes while
  frozen; phase-dependent errors persisted in the additional fine sweep.
  Consequently, **1080p60 full-frame image-change measurements are unqualified**.
  Its reported content comparison is limited to the stable central Y/C ROI.
- Every selected path in the six comparison conditions had 100% strict
  geometry, zero sequence gaps and zero telemetry overruns. Each recorded
  trigger interval was 450,000 reference ticks, with 54,000 ticks high.
  All 16,218 raster-cohort spreads were independently checked by rotation.
- Spread is the shortest circular arc containing five nearest event phases,
  using camera 2 as reference. It is not an exposure-cohort measurement.
  The circular period follows the event cadence: about 16.67 ms for 60 rasters/s,
  but about 33.33 ms for 30 payload changes/s. Hence a 20.848 ms payload-change
  spread can coexist with an 8.114 ms raster spread.
- CRCs describe the previous complete raster and are reported at the next
  active-raster boundary. Each timestamp is latched on the common 27 MHz
  clock before round-robin serialization. The nominal time quantum is
  37.037 ns; oscillator scale, camera/board delay and receiver latency are not
  independently calibrated. Capture blocks and reprogramming gaps stay separate.
- The ILA verifies the generated trigger, not its electrical arrival or
  acceptance at each camera. This synchronization study did not sweep lower
  trigger rates. It does not establish synchronization at a claimed rated
  trigger rate, nor does it disprove sensor-exposure synchronization.

## Manufacturer reference and next discriminating measurement

The locally supplied Wonwoo DM-G15-42 approval sheet v1.04, printed page 39,
describes ExtTrig as “External trigger synchronous image output mode.” No
numerical skew tolerance was found in the reviewed trigger section, printed
pages 39–42. The exact earlier 25 Hz manufacturer statement was not supplied.

Manual: `C:/SVNProjects/IMU_Stabilize_v40/Manual/EO/원우Approval sheet _DM-G15-42_v1.04_240104.pdf`.
SHA256: `e1f5c8ce23da0bca8b7f631279c96de8f947967754329e5fa9586fe79a0b1634`.
The PDF is not redistributed here.

A sensor-exposure verdict requires a common-timebase capture of the trigger
at the camera inputs and all five exposure/strobe outputs, or a shared
time-coded optical target visible to all five cameras with image correspondence.
The trigger rate should also cover the manufacturer's specified supported range.

## Files and reproduction

- [Separate Excel report](EO_Camera_Synchronization_Comparison_20261008.xlsx):
  Comparison, Camera results and Matched rasters. The summary distinguishes
  raster timing, qualified payload timing and relative drift.
- `study_config.json` declares the conditions, exact phase selections, controls
  and report interpretation. `study.json.gz` contains the complete processed
  study. `selected_events.csv.gz` and `raster_cohorts.csv.gz` preserve processed
  observations. Per-condition `events_*.csv.gz` preserve exact original ILA
  CSV bytes after decompression.
- `60_state_verification.json` and `final_state_verification.json` record
  manually reviewed OSD readbacks and image hashes. Contact sheets and key
  logs document mode, format, exposure and Freeze controls. The original
  full snapshot CSVs and additional rejected captures remain local.
- `build_*sha256.json` and `build_checks/` identify the bitstreams and routed
  timing/audit evidence. Binaries/checkpoints stay local. Revision-3 timing
  was WNS 1.257 ns, WHS 0.010 ns, WPWS 1.347 ns with zero negative totals.
  Its external input model is an aperture experiment, not board timing signoff.
- `archive_manifest.json` records source and archive hashes. Compressed source
  CSVs can be decompressed under `captures/eo_sync_20261008` with their original
  folder names, then reprocessed with
  `python diagnostics/eo_sync/scripts/collect_study.py captures/eo_sync_20261008/study_config.json`.
- Diagnostic RTL, capture tools, simulations and decoder tests are in
  [`diagnostics/eo_sync`](../../diagnostics/eo_sync/README.md). The report builder
  and read-only export checks are archived in `report_source/`; the builder
  uses the Codex bundled `@oai/artifact-tool` runtime and local bench paths.
  Spreadsheet formulas were recalculated with Artifact Tool and exported
  caches cross-checked against the decoded study. Native Excel execution was
  not performed.

Restoration details and direct readbacks are recorded in
`restoration/verified_state.json` and the associated images.
The original operational FPGA was reloaded. All five cameras were directly
verified over USB at 1080p30, ExtTrig, 1/240 s, 0 dB, DNR 2D+3D, Freeze OFF,
both polarities OFF, both delays 0.0 and strobe width 1.0. All menus were closed.
Display selection 6, its seven parameter bytes and all IR/EO pose offsets
match the initial readbacks. Camera 1, camera SAVE/DFLT and configuration flash
were not changed. Operational bitstream SHA256:
`d905e96d96990528a5c2098e0e018fa9d88814a18703fb0ce4f09a348b5f2cfd`.
