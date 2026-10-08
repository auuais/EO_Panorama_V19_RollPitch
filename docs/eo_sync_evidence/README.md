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

## 1080p60 / 30 Hz follow-up, 9 October 2026

Setup began on 8 October. `trig30_20261008/` preserves the additional test
with 30 Hz common trigger, 2 ms high time, 1/240 s shutter, 0 dB gain,
DNR 2D+3D and ExtTrig Delay 0.0 ms on physical cameras 2–6. The input-trigger
delay was already zero and was verified again after selecting 1080p60.
The supplied manual's printed page 41 shows ExtTrig Delay between trigger
input and exposure start. Strobe Delay is the separate camera-output setting.

The r4 diagnostic passed internal timing (WNS 0.723 ns, WHS 0.010 ns,
WPWS 1.347 ns) and a full-cycle sampling sweep with frozen camera images.
The selected five-camera control contained 1,628 rasters per camera with
zero central-ROI changes. Cameras 5 and 6 still had changing full-frame CRCs
while frozen, so only the central 96×96 ROI qualifies image-change counts.

Across the two live blocks (54.64 s total), all cameras produced approximately
60 rasters/s. Cameras 2–5 changed their central ROI exactly every two rasters.
Camera 6 initially had three extra ROI transitions in three short bursts
(six one-raster change intervals). Two repeated CRC-difference patterns
suggest sampling error but do not establish its cause. Those observations
are retained in `cam6_anomalies.json` and the original event files.

An independent camera-6 repeat used the rising edge at phase tap 322.
The fresh frozen ROI was identical at taps 308, 322 and 336 and showed zero
changes across 1,676 further rasters. The following 1,676-raster live capture
had 837 ROI changes, with all 836 measured inter-change spacings equal to two
rasters. Thus the supported rate verdict is approximately 60 raster starts/s
and 30 central-image updates/s with a 30 Hz trigger. It is not proof of 30
distinct sensor exposures. Finite capture endpoints slightly shift the
count-per-observed-span rates away from exactly 30.000.

The five-camera raster spread in the primary follow-up was 3.644–3.869 ms,
median 3.764 ms. This is a sequential observation after a format change,
not evidence that 30 Hz triggering improves synchronization over 60 Hz.
Electrical trigger arrival and physical exposure start remain unmeasured.

`EO_Camera_Synchronization_Comparison_20261009.xlsx` retains the original comparison and adds this test at
Comparison row 55, with the camera-6 repeat at row 85. Original validation
files in `report_source/` refer to the pre-addendum workbook retained in Git
commit `c3943b7`. The follow-up manifest and reproduction scripts are under
`trig30_20261008/`. The original workbook content, formulas and styles are
checked for preservation during the edit.
The original workbook was open and locked, so the updated report is saved as
a dated copy. The original workbook remains unchanged.

The operational FPGA and original camera settings were restored again after
the follow-up. All 25 USB readbacks (five menus/views per camera) were directly
inspected. Display selection/parameters and IR/EO pose readbacks match the
initial state. See `trig30_20261008/restoration/verified_state.json`.

## 1/60 s exposure follow-up, 9 October 2026

`trig30_exp60_20261009/` retains the new 1080p60 / ExtTrig / 30 Hz test.
The shutter was directly read as **1/60 s on every camera in 1080p60**.
Gain remained 0 dB, DNR 2D+3D, ExtTrig Delay 0.0 ms, trigger pulse width
2 ms and both polarities OFF. The existing r4 bitstream was reused. All five
observers used rising edges at taps 336, 280, 308, 280 and 322 respectively.

The fresh 28.517 s Freeze control contained 1,711–1,712 rasters per camera,
100% strict geometry, no sequence gaps, and zero central ROI changes on every
camera. Full-frame CRC still changed on camera 5 (1,020 times) and camera 6
(950 times). Image-update conclusions therefore remain limited to the central
96×96 ROI. A stable frozen pattern does not guarantee every live data pattern.

The primary two live blocks cover 57.307 s, and a repeat at unchanged settings
covers 28.571 s. Every selected path has 100% strict geometry, no sequence gaps
and no telemetry overruns. The captured trigger period is exactly 900,000
nominal 27 MHz ticks, with 54,000 ticks high. All cameras deliver approximately
59.999 raster starts/s.

| Camera | Primary ROI changes/s | Repeat ROI changes/s | Inter-change spacing |
|---|---:|---:|---|
| 2 | 30.008 | 30.017 | All two rasters in both observations |
| 3 | 29.991 | 29.999 | All two rasters in both observations |
| 4 | 29.991 | 30.000 | All two rasters in both observations |
| 5 | 30.113 | 30.192 | Primary: 12 one-raster intervals; repeat: 10; otherwise two rasters |
| 6 | 30.026 | 30.017 | Primary: two one-raster intervals; repeat: all two rasters |

**At the verified 1/60 s setting and 30 Hz trigger, cameras 2–4 and the camera 6
repeat support 60 rasters/s with 30 central-image updates/s.** Their clean ROI
cadence did not fall to 15/s. Camera 5's dominant cadence is also two rasters,
but persistent extra CRC transitions prevent certifying a clean 30 FPS stream
for that camera. All anomalies remain in the raw data and
`roi_anomalies.json`; the repeat did not discard or replace the primary data.
Sampling errors are possible, but the cause is not established. None of the
extra transitions is treated as proof of an additional exposure.

Primary raster spread: median 11.251 ms, P95 11.297 ms, maximum 11.305 ms.
Repeat: median 10.741 ms, P95 10.778 ms, maximum 10.782 ms. These are sequential
nearest-raster phase observations, not evidence that shutter speed caused a
synchronization change. Physical exposure starts, trigger acceptance and actual
integration duration were not observed. An OSD shutter value is a verified
setting, not an independent integration-time measurement.

`EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx` preserves the
previous workbook and adds this test at Comparison row 99, with the unchanged
settings repeat at row 129. Forty camera observations and 5,147 matched-raster
sets are appended to the existing detail tables. Reproduction scripts and
formula/export checks are in `trig30_exp60_20261009/reproduction/`; the original
bench paths are retained in those scripts. Copy the reproduction scripts back
to `.tmpCRC/eo_sync_trig30_exp60_20261009/` when reproducing their local workflow.

Restoration evidence belongs to `trig30_exp60_20261009/restoration/` and its
`verified_state.json`: operational FPGA, 1080p30, ExtTrig, 1/240 s, Freeze OFF,
unchanged gain/DNR/delays, and matching display and pose readbacks.
