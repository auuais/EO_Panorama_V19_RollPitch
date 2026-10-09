# Camera 2 DNR OFF comparison — 9 October 2026

The simultaneous camera-2/camera-3 comparison found several milliseconds of actual input separation in every DNR state. Turning camera 2 DNR OFF did not align their raster starts or demonstrate a substantial reversible change in raster alignment. A camera-3 image-change phase shift occurred while camera 2 DNR was still ON, so the later image-change gap cannot be assigned to DNR. Testing was not expanded to disabling DNR on all five cameras and the Excel workbook was left unchanged.

## Settings and scope

Camera 2: 1080p60, 1/60 s shutter, 0 dB gain, external trigger, ExtTrig Delay 0.0 ms. The r4 diagnostic generated 30 Hz triggers with a 2 ms high time. DNR was changed from 2D+3D to OFF and back to 2D+3D, with Freeze OFF for the three live captures. Camera 3 was an unchanged raster-timing reference. Cameras 3–6 were temporarily changed to 1080p60 for diagnostic clock locks; their exposure and DNR settings were not changed.

All measurements use rising-edge samples at taps 336:280:308:280:322, common nominal 27 MHz timestamps, and the same bitstream. Exact build hashes are in build_sha256.json. Camera settings were read directly from ILA OSD crops. No standard eo_video_mode.py --select command, OSD SAVE/DFLT, or FPGA configuration-flash programming was used. The restoration-only route request is described below.

## Results

### Actual camera-2 versus camera-3 spread

These values are direct separations of nearest camera-2 and camera-3 events in simultaneous ILA captures on the same 27 MHz timebase. All values in the following tables are **milliseconds**. For raster starts, camera 2 arrived later than camera 3 in every matched pair. Captures contain about 58 seconds of live data per condition; capture gaps are excluded.

| Camera 2 DNR state | Matched raster pairs | Minimum spread (ms) | Median spread (ms) | P95 (ms) | Maximum spread (ms) |
|---|---:|---:|---:|---:|---:|
| 2D+3D ON, initial | 3,485 | 7.791222 | **7.965296** | 8.087985 | 8.101630 |
| OFF | 3,452 | 6.992519 | **7.167000** | 7.290219 | 7.303852 |
| 2D+3D ON, restored | 3,494 | 6.178407 | **6.316333** | 6.477335 | 6.491148 |

The gap continued to decrease after DNR was turned back ON. The fitted relative raster drift was about -4.75 microseconds per second. The previously quoted 3-4 microseconds was a residual after removing a clock-drift model; **it was not the measured synchronization spread**. The input raster starts remain separated by approximately 6-8 ms in these captures. The changing separation does not demonstrate a stable output raster phase lock between these two cameras.

The nearest full-image and central-region CRC-change events also have millisecond separations:

| Camera 2 DNR state | Matched CRC-change pairs | Minimum absolute gap (ms) | Median absolute gap (ms) | P95 (ms) | Maximum absolute gap (ms) |
|---|---:|---:|---:|---:|---:|
| 2D+3D ON, initial | 1,740 | 7.864704 | **8.038389** | 8.861896 | 8.875556 |
| OFF | 1,726 | 9.363185 | **9.500000** | 9.660676 | 9.674444 |
| 2D+3D ON, restored | 1,746 | 10.175963 | **10.350648** | 10.474694 | 10.488444 |

Both CRC series produce the same pair results. Camera 3 changed which alternate raster contained its CRC update during the initial ON capture: in on_a/events_001.csv, update intervals of 1, 3 and 1 rasters occurred at 12.575622, 12.625623 and 13.442303 seconds from that block's first event. The last change shifted update parity, which then persisted in the OFF and returning-ON captures. Thus the baseline contains two image-update phases, and a single signed mean or linear fit would obscure the actual behavior. This shift preceded DNR OFF and did not reverse on returning to ON.

Camera 2 passed frozen CRC controls in both DNR states; camera 3 remained live and has no independent frozen control in this experiment. These CRC gaps are therefore descriptive, not a qualified measurement of same-exposure image synchronization. Matching nearest periodic events does not identify the same physical exposure across cameras. Camera 3 shutter was not freshly reread or changed; this was not a matched-exposure pair test. See cam2_cam3_spread.json and cam2_cam3_spread_pairs.csv for reproducible pair results and reference-camera cadence checks.

### Camera 2 cadence and controls

| Condition | Measured live time (s) | Valid cam2 rasters | Raster/s | Full-image CRC changes | Image-change cadence/s |
|---|---:|---:|---:|---:|---:|
| on_a | 58.067 | 3486 | 59.999250 | 1742 | 29.999625 |
| off_b | 57.517 | 3453 | 59.999255 | 1726 | 29.999627 |
| on_return | 58.217 | 3495 | 59.999253 | 1746 | 29.999627 |

All observed successive full-image and central-region image changes were separated by exactly two rasters. The cadence column is computed from adjacent change-event intervals; comparison.json also retains changes/count-window rates, whose small deviations around 30 reflect finite-window endpoints. Capture gaps are excluded, and no transitions are inferred across them.

Camera 2 had 100% valid 1920×1080 geometry and no sequence gaps in all live and frozen captures. Freeze controls passed independently in both DNR states: ON had 1,746 valid rasters over 29.084 s and OFF had 1,749 over 29.134 s, with zero full-image and zero central-region CRC changes in either control. Telemetry signature, valid-bit and overrun checks passed for all stored events. Phase locks/taps/busy/faults were checked before and after captures.

The fitted relative raster drift (camera 2 minus camera 3) was −4.74956 µs/s. Against the bracketing ON linear drift fit, the OFF raster residual had median +3.098 µs and range +2.247 to +3.477 µs. The OFF full-image/ROI change phase relative to the trigger had median +3.943 µs and range +2.996 to +4.274 µs against its bracketing ON fit. These microsecond residuals are not evidence of a large DNR effect. Clock drift was slightly nonlinear: extrapolating only the initial ON image-change fit to the returning ON capture gives −17.47 µs median residual. Consequently, the small residual cannot be assigned causally to DNR, and “no difference” here means no substantial change detectable in this experiment.

Camera-2 CRC measurements passed the frozen controls above. Camera-3 CRC timing has the separate qualification limit described above. Neither received-raster timing nor CRC-change timing directly measures physical exposure synchronization or end-to-end latency; a whole frame of internal buffering can preserve output cadence and modulo-trigger phase. This single-camera DNR intervention is not a measurement of all five cameras with DNR OFF.

## Restoration and report provenance

Direct ILA OSD readbacks confirmed cameras 2–6 back at 1080p30 and camera 2 back at 1/240 s, 0 dB, DNR 2D+3D, Freeze OFF, external trigger and 0.0 ms trigger delay. The original operational FPGA image was reloaded. Read-only USB display/parameter and pose reads exactly matched their starting values. See restoration_verified.json and restored_* folders.

FPGA reconfiguration resets its local mode register while the MCU still remembers EO camera 6. This caused the incomplete boot/default view recorded in final_closed.png. A custom mode-only 0x2203 request (06 FF FF FF FF FF FF FF) restored EO6 routing. The ancillary fields exceed the inspected firmware's checked ranges, so its handler skips their camera/display parameter writes. This is specific to the inspected firmware, not a general protocol no-change sentinel. Source path/hash, payload, ACK and unchanged before/after controller parameters are recorded in restore_route_only.json. The same MCU mode was persisted once to MCU mode flash; FPGA configuration flash was not programmed. The restored full camera-6 scene was directly verified in final_route_restored.png. Fresh post-route display/pose readbacks still match the initial values.

The workbook was left unchanged when this single-camera experiment completed (SHA-256 cd7dc5ae1e5fc248c90c3675ba9eb918822012ee6fe68619acfecc752879a036). The later all-five DNR study in [dnr_all5_20261009](../dnr_all5_20261009/README.md) adds both experiments to the consolidated workbook EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx. The pre-edit workbook is retained in that study's report_provenance directory.

## Reproduce analysis

From this repository, run the bundled Python interpreter with `-X utf8` and `scripts/analyze.py <this evidence directory>`. The analyzer imports diagnostics/eo_sync/scripts/decode_events.py from the repository and regenerates comparison.json and camera2_relative_phase.csv from the raw event CSVs. Run `scripts/pair_spread.py` for the direct camera-2/camera-3 spread JSON and pair CSV; its default output is this evidence directory. It independently decodes the six raw event CSVs and verifies that all 10,431 raster pairs match camera2_relative_phase.csv exactly. bench.py and its durable logs document the original hardware sequence; do not run hardware stages without checking the actual starting camera state.

Raw OSD snapshot CSVs, reconstructed PNGs, serial key logs, event CSVs, phase checks, build hashes, comparison data, and restoration evidence are included. No confidential manufacturer manual/PDF is included. manifest.json records SHA-256 and size for every other archived file.
