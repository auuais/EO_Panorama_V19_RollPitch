# All-five camera DNR OFF synchronization comparison — 9 October 2026

Physical cameras 2–6 were tested in 1080p60 at 1/60 s, 0 dB, external-trigger mode and 0.0 ms external-trigger delay. The same r4 diagnostic and rising sampling taps 336:280:308:280:322 were used throughout. The common nominal timestamp clock is 27 MHz. Every block verified 30 Hz triggers and 2 ms high time. All camera settings were directly read from reconstructed ILA OSD crops. Camera 1 received no setting commands.

Protocol: all-five ON frozen control; unfreeze; ON live; all-five DNR OFF live; all-five DNR ON return live; repeat all-five OFF live; all-five OFF frozen control; restoration. There was no Freeze intervention between the four live conditions. Each live condition contains two blocks totaling approximately 58 seconds; upload gaps are excluded. Only DNR was changed between the live conditions. The OFF repeat was added because the ROI spread did not return to its initial ON value.

## Actual five-camera input raster spread

Spread is the shortest circular arc containing the five nearest raster phases. It describes received input alignment, not identification of the same physical exposure. Values below are milliseconds, not clock-drift residuals.

| All-five DNR | Observed s | Matched sets | Minimum ms | Median ms | P95 ms | Maximum ms |
|---|---:|---:|---:|---:|---:|---:|
| ON initial | 58.617 | 3515 | 10.825963 | 10.854519 | 10.873863 | 10.876037 |
| OFF | 58.751 | 3523 | 10.642963 | 10.669593 | 10.689630 | 10.692037 |
| ON restored | 58.001 | 3478 | 10.454407 | 10.477704 | 10.504561 | 10.506630 |
| OFF repeat | 58.951 | 3535 | 10.221593 | 10.252000 | 10.271678 | 10.273778 |

## Camera-2/camera-3 comparison within this test

Both cameras now have verified 1/60 s shutters. Pair spread is the absolute separation of nearest raster starts on the same timestamp clock.

| All-five DNR | Pairs | Minimum ms | Median ms | P95 ms | Maximum ms |
|---|---:|---:|---:|---:|---:|
| ON initial | 3518 | 7.290259 | 7.464426 | 7.587715 | 7.601407 |
| OFF | 3527 | 6.176926 | 6.351889 | 6.475830 | 6.489630 |
| ON restored | 3481 | 4.962444 | 5.097889 | 5.257444 | 5.271037 |
| OFF repeat | 3538 | 3.545037 | 3.718944 | 3.843678 | 3.857519 |

## Digital image-change timing and controls

Full-raster and central 96x96 ROI CRCs were checked independently with Freeze ON in both DNR states. Per-camera qualification, cadence histograms and all-five CRC phase spans are retained in study.json. Extra live CRC transitions are retained and are not evidence of additional sensor exposures. Periodic event matching does not establish common exposure identity or physical integration timing.

Camera 2 and camera 3 passed both full-frame and ROI frozen controls. Their live change intervals were all two rasters. Camera 3 update sequence parity changed from odd in the initial ON capture to even in the first OFF capture and remained even in ON return and OFF repeat; camera 2 stayed odd throughout. The phase change occurred in the uncaptured interval between states, so its cause cannot be separated from setting changes and clock phase. The five-camera ROI spread of the first OFF capture did not reproduce on OFF repeat.

| Frozen DNR | Camera | Valid rasters | Observed s | Full CRC changes | ROI CRC changes |
|---|---:|---:|---:|---:|---:|
| 2D+3D | 2 | 1751 | 29.167 | 0 | 0 |
| 2D+3D | 3 | 1750 | 29.151 | 0 | 0 |
| 2D+3D | 4 | 1750 | 29.150 | 0 | 0 |
| 2D+3D | 5 | 1750 | 29.150 | 981 | 0 |
| 2D+3D | 6 | 1750 | 29.150 | 1268 | 0 |
| OFF | 2 | 1848 | 30.784 | 0 | 0 |
| OFF | 3 | 1847 | 30.767 | 0 | 0 |
| OFF | 4 | 1847 | 30.767 | 0 | 0 |
| OFF | 5 | 1847 | 30.767 | 625 | 0 |
| OFF | 6 | 1848 | 30.784 | 1847 | 0 |

| All-five DNR | Matched ROI-change sets | Minimum ms | Median ms | P95 ms | Maximum ms |
|---|---:|---:|---:|---:|---:|
| ON initial | 1755 | 11.152148 | 11.262519 | 11.339652 | 19.119815 |
| OFF | 1759 | 13.459889 | 15.502926 | 15.607344 | 15.616185 |
| ON restored | 1736 | 10.454407 | 13.241463 | 13.270417 | 13.273111 |
| OFF repeat | 1764 | 10.221593 | 10.252093 | 10.271809 | 13.000407 |

## Clock drift and limits

Actual spread and drift-model residual are separate results. The bracketing ON fit estimates each camera raster phase relative to camera 2; OFF residuals and the returning ON capture are retained. Sequential changes in spread alone cannot establish a DNR effect. Nearest raster matching cannot expose a whole-frame internal latency change. Sensor exposure synchronization would require corresponding exposures or independent sensor timing measurements.

| Camera relative to cam2 | ON fitted drift us/s | OFF residual median us | OFF residual minimum us | OFF residual maximum us |
|---|---:|---:|---:|---:|
| 3 | 4.678535 | -0.262613 | -0.525230 | 0.028712 |
| 4 | 2.923170 | 2.428786 | 2.010880 | 2.675826 |
| 5 | 1.652589 | 3.781750 | 3.394895 | 4.337813 |
| 6 | 0.744582 | 7.369813 | 6.521835 | 7.856249 |

## Restoration and consolidated workbook

Fresh ILA OSD readbacks verified all cameras 2–6 restored to 1080p30, 1/240 s, 0 dB, DNR 2D+3D and Freeze OFF, with menus closed. The operational FPGA image was reloaded. The starting EO camera-3 route was reapplied using a mode-only request whose ancillary out-of-range fields are skipped by the inspected firmware. This same-mode request writes MCU mode flash once; FPGA configuration flash was not programmed. Controller display/parameter and pose reads exactly matched their initial values, and the restored full USB camera-3 scene was directly viewed. No OSD SAVE or DFLT was used.

The consolidated workbook retains the prior synchronization study and adds the earlier cam2-only DNR comparison plus this all-five DNR OFF comparison. Existing worksheets, formulas, styles, tables and panes were preserved. New spread formulas and their saved caches were checked against the independent raw-capture analysis; no formula errors were found. Native Excel execution was not performed.

Workbook at completion: EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx
SHA-256: 0deead01a8332fce0377078939ff2c0d6fb5240265acf7974c9556d4a31f6ea5

## Reproduction

analyze.py imports diagnostics/eo_sync/scripts/decode_events.py and recomputes study.json plus raster/CRC cohort and cam2/cam3 pair CSVs from the raw event CSVs. bench.py and logs document hardware stages; do not rerun setting changes without reading the actual starting camera state. Report authoring uses the archived pre-edit workbook and measured statistics. manifest.json hashes every other archive file. No manufacturer manual or PDF is included.
