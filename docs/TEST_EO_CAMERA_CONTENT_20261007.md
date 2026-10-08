# EO camera content rate tests

**Correction, 8 October 2026:** the later 1080p60 fresh-FPS conclusions below are withdrawn. Direct ILA OSD reconstruction shows that switching from 1080p30 with 1/30 s selected to 1080p60 changes the displayed shutter to 1/60 s. More importantly, the original dedicated diagnostic reports about 60 full-frame and ROI CRC changes/s even with camera Freeze ON. The frozen sampled image is byte-identical before and after that original-bitstream control. Valid raster geometry did not guarantee active-pixel integrity. See the final verification section and `captures/eo60_verify_20261008/verification_results.json`. Earlier 1080p30 measurements remain separately scoped.

Tests on 7 October 2026 reproduce the reported 15 Hz output with the original camera settings, but **15 Hz is not a fixed limit of ExtTrig mode**. On camera 2, selecting FreeRun doubles output novelty, and shortening the shutter to 1/240 second also produces about 30 distinct output images per second while ExtTrig remains selected. Restoring the original settings restores about 15 updates per second.

Fresh raw-input ILA checksums now locate the original repetition **before DDR**: camera 1 changes every raster, while cameras 2–6 alternate changed and repeated full-raster payloads. All six carry 30 complete 1920×1080 active rasters/s. These measurements describe transmitted pixels, not physical sensor exposure counts.

## Configuration and evidence

Repository: `E:/Xylinx/EO_Panorama_V19_RollPitch`, starting commit `e462da6`. The initial FPGA image was the archived `20261006_221847_trsmon_trig60_9a8a81e` build. A fresh ILA run in `captures/cam_fps/20261007_011703` confirms 60 common trigger edges/s, 30 raster starts/s on each input, 1125 EAV markers per raster and zero frame-sampled F changes.

The user confirmed camera 1 FreeRun and cameras 2–6 trigger mode. Camera 2 was then read through its own OSD, with screenshots and exact serial commands archived under `captures/takeover_20261007/osd`:

- Trigger Mode ExtTrig; TrigIn Polarity OFF; StrOut Polarity OFF; ExtTrig Delay 0.0; Strobe Delay 0.0; Strobe Width 1.0.
- Exposure page: LENS MANUAL, MODE disabled, AGC 0 dB, SHUT SPEED 1/30 sec.
- Special Function: NTSC, 1080p/30fps, BT.1120/SDI, EX-SDI OFF.

Camera 1's OSD was also checked: FreeRun, StrOut Polarity ON, Strobe Delay 0.0, Strobe Width 1.0; LENS MANUAL, MODE MANUAL, AGC 0 dB and shutter 1/60 sec. Thus the initial cross-camera comparison also differs in shutter setting. Camera 1's settings were not changed.

DirectShow enumeration identified device 0 as **USB3 Video**, with OBS Virtual Camera at index 1. The USB device has VID 345F / PID 2131. Every acquisition saves full-frame BLAKE2b-128 hashes, timestamps, lossless 96×96 BGR patches, first/last frames, an annotated ROI map and JSON statistics. Patches can be rehashed against their corresponding timeline entries. A hash change denotes changed pixels; it does not itself count physical exposures.

Mode selection uses the existing ICD helper, which reapplies EO brightness and contrast even when their status bytes are unchanged. Initial status parameters were seven zero bytes. Camera mode and shutter tests subsequently used OSD keys directly, avoiding display-mode changes during each comparison. OSD screenshots provide setting readback; command acknowledgement alone is not treated as readback. No camera power cycle or MCU firmware flash was used.

## USB output results with 60 Hz trigger

| Condition | Full image changes per second | Evidence directory under captures/takeover_20261007 |
| --- | ---: | --- |
| Camera 1 initial FreeRun | 29.55 | baseline_cam1 |
| Camera 2 initial ExtTrig | 14.93 | baseline_mode2 |
| Cameras 3–6 initial ExtTrig | 14.83–14.93 | baseline_mode3 through baseline_mode6 |
| Camera 2 changed to FreeRun | 29.65 | cam2_free_prebuild |
| Camera 2 returned to ExtTrig | 14.93 | cam2_ext_return_prebuild |
| Camera 2 ExtTrig with verified 1/60 sec shutter | 14.93 | cam2_ext_shutter60_prebuild |
| Camera 2 ExtTrig with verified 1/240 sec shutter | 29.95 | cam2_ext_shutter240_prebuild |
| Repeat at 1/240 sec, four useful separate patches | 30.06 | cam2_ext_shutter240_repeat |
| Camera 2 restored to verified 1/30 sec shutter | 15.03 | cam2_ext_shutter30_restored |

Every listed full-frame timeline has zero revisits to an earlier non-adjacent hash. At 1/240 second the four useful patches change on the same grabs as the whole image, at roughly 30 Hz, normally with two USB grabs per pixel state. The central patch falls on a nearly black area: it was completely zero in one acquisition and changed irregularly in the repeat. It is excluded from the short-exposure rate conclusion. This is an observed failure of the assumption that sensor noise always guarantees useful novelty in any selected patch.

Early captures wrote first-frame PNGs during acquisition, causing a brief read stall and lowering measured rates slightly. PNG encoding was moved outside acquisition for later runs. Grab rates are retained in every JSON file; the restored-shutter run acquired about 52.6 grabs/s during the FPGA build, while the short-shutter repeat acquired about 60.0/s. Neither is described as an exact exposure count.

## Panorama comparison

With the initial settings, interior panorama patches give approximately 29.57 changes/s for the expected camera 1 tile and 14.83/s for each expected camera 2–6 tile (`baseline_mode14`). Thus the earlier report of 30 Hz for camera 2 and 3 panorama tiles was not reproduced with these ROIs.

Coordinates are inside the tiles and away from the 17-column seams. The 3840×480 logical panorama is folded at physical row 480. Full screenshots document the mapping; camera labels are geometric expectations until an individual-camera intervention verifies them. No lens-cover identification is claimed.

## USB output results with 30 Hz trigger

The archived `20261006_150257_camratemon_bd9af71` image was programmed over JTAG while the new diagnostic build ran. The fresh rate capture in `captures/cam_fps/20261007_014301` reports 30 raster starts/s per camera and 30 common trigger edges/s. Four segmented captures in `captures/takeover_20261007/trig30_edges` contain 256 consecutive trigger intervals: 203 at 9672 ticks, 20 at 9671, 30 at 9643 and 3 at 9642. With 256 HD clocks per tick, their mean is 33.334034 ms, or 29.999370 Hz. The trigger is slightly modulated by its strobe-following source; it is not the constant 60 Hz override.

On this image, camera 2 with ExtTrig and the original 1/30-second shutter gives 14.95 output changes/s (`trig30_cam2_shutter30`). Selecting 1/240 second gives 30.05/s (`trig30_cam2_shutter240`), with three separate useful patches changing on the same grabs as the full image and zero revisits. The centre patch is black and excluded. This also contradicts a universal 25 Hz cap under a nominal 30 Hz trigger, while leaving the manufacturer's unprovided configuration and physical exposure-count definition unresolved.

Restoring 1/30 second returns all five patches and the full image to 14.93 changes/s (`trig30_cam2_restored`). This is a shutter A/B/A comparison on the same camera with the same FPGA image.

An intermediate **OSD-verified 1/120 second** setting gives 15.03 changes/s in the full image and four useful patches. Its provisional acquisition directory is `trig30_cam2_shutter100`; that name is inaccurate, and `configuration.json` records the correction to 1/120 from the saved OSD screenshot. The camera's menu steps were verified visually rather than inferred from key counts.

The two FPGA images change the DDR epoch source along with the physical trigger, so their comparison is not an isolated trigger-frequency experiment. Each shutter comparison, however, keeps its FPGA image and trigger source fixed.

## Receiver measurement

`src/EoInputContentMon.v` is a passive observer of each camera's raw Y/C input in its own pixel clock domain, before DDR admission. It computes separate whole-active-raster and central-patch CRCs, counts active samples, active lines and EAVs, and increments a raster sequence independently of content. The sequence number is excluded from the checksums.

The monitor checks 1920 samples per active line, 1080 active lines and 1125 total EAVs. A full report crosses into the independent HD clock domain using a stable mailbox and synchronized toggle. The existing 64-bit probe12 is repurposed for five packets per raster: full CRC, patch CRC, active sample count, line counts and HD clock timestamp. Probe11 retains the existing rate monitor. This diagnostic image requires its own matching LTX and decoder; the old TRS decoder must not interpret its probe12.

Validation already passed:

- `sim/tb_EoInputContentMon.sv`: independently computed CRC vectors, repeated/changed/revisited content, geometry, raster sequences and six simultaneous mailboxes with all 150 packets received.
- `sim/tb_EoInputContent1080.sv`: full default 1920×1080 raster, 1125 lines, 2,073,600 active samples and independently computed full/patch reference CRCs.
- `scripts/test_decode_input_content.py`: known 30 Hz timing, 2:1 repeats, missing rasters and incomplete packet groups. Missing sequences are not compared as adjacent frames.

The diagnostic build completed at 02:00 KST and is archived in `builds/bit_archive/20261007_contentmon_e462da6`, including its matching LTX, source snapshot and binary SHA-256 hashes. The existing timing guard passed with WNS 0.087 ns, WHS 0.006 ns, WPWS 0.099 ns and zero corresponding total negative slack; the bus-skew report is clean. This is a pass under the repository's existing constraints, not an independent external-interface timing audit. Original trigger and capture logic are unchanged in this diagnostic source.

### Original settings: measured input repetition

`content_smoke` contains 102 complete reports from two capture blocks. The longer `input_original` acquisition contains 612 complete reports from 12 blocks: 101, 99, 105, 103, 102 and 102 for cameras 1–6 respectively. Every complete report has flags 3 (complete and geometry valid), 2,073,600 active Y/C samples, 1080 active lines and 1125 total EAV markers. Measured raster rates are 29.99948–29.99966 Hz using the nominal 74.25 MHz HD clock.

For camera 1, all 89 consecutive comparisons changed. Cameras 2–6 respectively have 44/43, 46/47, 44/47, 44/46 and 48/42 changed/repeated consecutive comparisons. Within each uninterrupted captured sequence, their full-raster CRCs alternate changed/repeated without exception. All measured intervals between content changes are exactly two rasters (32, 34, 32, 32 and 36 intervals respectively); camera 1's 77 measured intervals are all one raster. This establishes approximately 15 versus 30 input payload updates/s under the tested initial configuration.

ILA upload creates gaps between blocks. The decoder excludes incomplete reports and never compares content across missing raster sequences. Unequal counts of changed/repeated comparisons arise from short-block endpoints; the `estimated_updates_hz` fraction in JSON can consequently range from 14.5 to 16 despite an exact two-raster pattern. Use `change_spacing_rasters` and the actual sequence data for the cadence conclusion. CRC equality is strong evidence of repeated payload, not a mathematically collision-free byte comparison.

### Short shutter: measured input recovery

The known working 60 Hz image was temporarily loaded to read camera 2's OSD. `osd/preinput_shutter30.png` confirms the starting 1/30-second shutter; `preinput_shutter240.png` confirms 1/240 second after the intervention; `preinput_exttrig240.png` confirms ExtTrig remained selected, with both polarities OFF and trigger delay 0.0. The menu was visibly closed (`preinput_closed240.png`) before reloading the same diagnostic binary.

`input_shutter240` contains 612 complete reports from 12 blocks, all with valid 1920×1080/1125 geometry. Camera 2 has 97 reports and **85 changed, zero repeated consecutive comparisons**. Its 73 measurable change intervals are all one raster, with raster rate 29.999610 Hz. Its central-patch CRC agrees. Camera 1 continues changing every raster; cameras 3–6 continue their strict alternating changed/repeated pattern. Thus only the intentionally changed camera doubles its input content-update cadence.

The input comparison uses identical diagnostic bit/LTX files and the same 60 Hz trigger, independently confirmed in probe11 for all three acquisitions (`rate_probe_summary.json` in each directory). An intervening reload was needed for visible OSD verification; it is not a continuous same-load A/B experiment. The return-to-baseline capture kept the short-shutter diagnostic load running while restoring the shutter through the recorded menu sequence. Final OSD readback after restoring the operational FPGA image confirmed 1/30 second and ExtTrig, with no intervening setting writes.

`input_restored30` contains another 612 complete geometry-valid reports. Camera 2 returns to strict alternating changes/repeats: 43 changed and 41 repeated comparisons, with all 31 measurable change intervals equal to two rasters. Camera 1 remains one-raster cadence and cameras 3–6 remain two-raster cadence. The command log for this return is `osd/input_restore30_command_black.json`; its associated black PNG is not setting readback. Together, the three input runs reproduce 15 → 30 → 15 payload updates/s for camera 2 while the other five cameras act as controls.

### Diagnostic output limitation

The diagnostic image produced an entirely black USB image on its initial load and on a second load. Camera input checksums remained valid. `diag_mig_console.txt` reports calibration passed with no calibration error; `diag_ddr/status.csv` shows active DDR reads/writes, nonzero pixel data, `scan_active=1` and `frame_valid=1`. This excludes a simple failure to calibrate as the explanation, but does not isolate the video-output failure. Changing display selection did not restore the picture. The diagnostic is therefore not accepted as a replacement operational image. Its black USB captures are excluded from camera-rate conclusions.

The operational image restored visible video before the short-shutter setup. The temporary content-monitor connections were also removed from the working top-level RTL after testing. The passive module, simulations and analysis tools remain available, and the exact diagnostic top-level source plus an isolated `content_monitor_top.patch` are preserved in the archive. The archive's diagnostic bitstream remains suitable for the recorded input-only measurement, subject to its unresolved video-output limitation; do not treat it as an approved operating image.

## Implications for the handoff and manufacturer statement

The observed 15 Hz output is reproducible with the initial settings. The hypothesis of a universal fixed 15 Hz camera limit is contradicted by the same-camera shutter test. A general claim that exposure settings cannot affect the rate is also contradicted; one unsuccessful shutter intervention was insufficient.

The supplied camera manual (DM-G15-42 v1.04, printed page 41, archived as `captures/takeover_20261007/manual/ext_trigger_timing.png`) depicts a falling active edge for TrigIn Polarity OFF, whereas the FPGA produces a high pulse lasting 2 ms. With the verified OFF setting, the relevant edge is therefore the pulse's falling edge. The edge repetition rate remains 60 Hz, but calling the camera setting rising-active is inaccurate. The manual's drawing does not establish the exact minimum repetition interval or accepted exposure rate.

The manufacturer's approximately 25 Hz statement is available here only as quoted in the handoff, without its original wording, exposure configuration or definition of output rate. At nominal 30 Hz triggering, the tested output gives about 15 or 30 pixel-state changes/s depending on the shutter setting. That does not reproduce a universal 25 Hz limit, nor does it rule out their measured 25 Hz in a different configuration. It also does not establish the physical sensor exposure count. No message has been sent to the manufacturer.

The revised handoff correctly cautioned that output hashes alone could not locate the repetition. The new raw-input measurements now resolve that uncertainty for the tested original configuration. They also verify the active-payload geometry that the old EAV count alone did not establish. Claims of an immutable 15 Hz trigger-mode ceiling or exposure-independent behavior should be withdrawn. The earlier panorama claim of 30 Hz on cameras 2 and 3 remains unreplicated and should not be used as evidence of mode-dependent recovery.

## Final restoration and retained evidence

The original operational 60 Hz FPGA image, `builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit`, was restored at 02:23:56 KST. SHA-256: `d905e96d96990528a5c2098e0e018fa9d88814a18703fb0ce4f09a348b5f2cfd`. The board is left displaying EO camera 1, with all OSD menus closed.

Camera 2 was read back as ExtTrig, 1/30 second, AGC 0 dB, input/output polarity OFF, trigger/strobe delay 0.0 and strobe width 1.0 (`osd/final_shutter30_readback.png`, `osd/final_exttrig_readback.png`). Camera 1 remains FreeRun at 1/60 second; cameras 3–6 were not changed. Final pose readback matches the initial alternating EO pitch offsets of −500/+500 centidegrees, all EO rolls zero and all IR offsets zero.

Final ten-second USB acquisitions verify live video: camera 2 gives **15.026 updates/s** (`final_cam2`), and the final displayed camera 1 gives **29.954 updates/s** (`final_cam1`). Their interior patches agree and neither has non-adjacent hash revisits. All 21 saved USB patch archives were rehashed against their timelines successfully (`patch_verification.json`); the black diagnostic run is included for evidence integrity, not as a camera-rate measurement.

No QSPI write, camera power cycle, MCU firmware flash or OSD SAVE occurred. Display-mode selection used the existing firmware helper, which persists selection; it was restored to 1. `captures/takeover_20261007/final_state.json` records the final state. Existing unrelated worktree changes were preserved; no commit was made.

Input reproduction uses the archived diagnostic bit/LTX, `scripts/capture_input_content.tcl <matching.ltx> <new-directory> 12`, then `python scripts/decode_input_content.py <directory>`. Programming is a separate explicit step. The decoder saves complete reports, excluded-mailbox counts, sequence gaps and per-camera change intervals. The exact activated diagnostic RTL and tools are retained in the build archive, while the working top-level RTL again uses its original probe12 TRS monitor.

## Evening exposure sweep, 7 October 2026

At the user's request, a fresh raw-input ILA sweep started at 19:15 KST. Camera 2 stayed in ExtTrig with AGC 0 dB. Camera 1 remained FreeRun at 1/60 s; cameras 3–6 were untouched controls. The initial settings were freshly read through OSD. All runs used the archived input-content diagnostic, its matching LTX and the same nominal 60 Hz trigger, independently confirmed in probe11. No new FPGA build was required.

| Capture | OSD shutter | Setting (ms) | Input rasters/s | Payload updates/s | Changed / repeated pairs | Change spacing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| input_00_shutter30 | 1/30 s | 33.333 | 29.999607 | 14.999804 | 44 / 43 | 2 raster(s) |
| input_01 | 1/60 s | 16.667 | 29.999607 | 14.999804 | 45 / 43 | 2 raster(s) |
| input_02 | 1/120 s | 8.333 | 29.999606 | 14.999803 | 44 / 40 | 2 raster(s) |
| input_03 | 1/180 s | 5.556 | 29.999607 | 14.999803 | 44 / 46 | 2 raster(s) |
| input_04 | 1/240 s | 4.167 | 29.999607 | 29.999607 | 88 / 0 | 1 raster(s) |
| input_05_return180 | 1/180 s | 5.556 | 29.999607 | 14.999803 | 45 / 41 | 2 raster(s) |
| input_06 | 1/300 s | 3.333 | 29.999607 | 29.999607 | 88 / 0 | 1 raster(s) |
| input_07 | 1/500 s | 2.000 | 29.999607 | 29.999607 | 87 / 0 | 1 raster(s) |
| input_08 | 1/1000 s | 1.000 | 29.999606 | 29.999606 | 87 / 0 | 1 raster(s) |
| input_09_restore30 | 1/30 s | 33.333 | 29.999606 | 14.999803 | 44 / 46 | 2 raster(s) |

The 10 conditions contain 6,120 complete reports from all six cameras (612 per condition, 12 capture blocks). Every complete report has valid 1920×1080 active geometry, 2,073,600 Y/C samples and 1125 EAV markers. Camera 1 changes every raster; cameras 3–6 change every two rasters throughout. Only camera 2's cadence responds to its shutter setting.

The first tested setting with every-raster novelty is 1/240 s (4.167 ms); 1/180 s (5.556 ms) still produces a two-raster pattern. Returning from 1/240 to 1/180 on the same diagnostic load restores 15 updates/s. This is an observed boundary between camera-menu settings, not a direct measurement of integration time or an exact sensor timing threshold. Accepted triggers and physical exposures remain uncounted.

The diagnostic output remains black. OSD readbacks therefore use the working video image. Each configuration record identifies whether readback preceded or followed its capture; no shutter-setting writes intervene between a capture and its matching readback. Adjacent pairs share a diagnostic load, with working-image readback and diagnostic reload between pairs. The 1/240→1/180 reversal and the final 1/1000→1/30 restoration each keep the same running diagnostic image during the comparison. Menus are closed before capture. Display selection 2 is reapplied after working-image reload because the FPGA display configuration resets independently of the MCU status.

ILA upload gaps and incomplete mailboxes are excluded. Each condition contains about three seconds of consecutive-raster comparisons per camera distributed across twelve blocks, so this is not a continuous long-duration test. Rates use uniform observed change spacing rather than the endpoint-biased changed-pair fraction. Whole-raster and central-patch CRCs agree for this sweep. CRC equality remains strong evidence, not collision-free byte proof.

Final restoration: the original working 60 Hz image was restored at 19:57:36 KST. Camera 2 was visually verified as ExtTrig, 1/30 s, AGC 0 dB, both polarities OFF, both delays 0.0 and strobe width 1.0. All menus are closed; display selection is 1; pose readback is unchanged. Final USB results are 15.027 updates/s for camera 2 and 29.981 updates/s for camera 1. All three fresh USB patch archives match their hash timelines. No QSPI write, MCU firmware flash, camera power cycle or OSD SAVE was performed.

Raw evidence: `captures/exposure_sweep_20261007_1915/`. Start with `sweep_index.json`, `sweep_validation.json` and `final_state.json`; each condition links to actual OSD readback and decoded/raw ILA files. The consolidated workbook retains the earlier 30/60 Hz USB experiments, panorama comparison, prior input A/B/A, reviewed claims and limitations alongside this fresh sweep.

## Fixed 30 Hz input ILA exposure sweep, 7 October 2026

At the user's request, the same camera-2 exposure sweep was repeated with a fixed 30 Hz FPGA trigger. A fresh diagnostic was built from the archived 60 Hz content-monitor source, changing only the timer period from 1,237,500 to 2,475,000 HD-clock cycles. The pulse remains high for 148,500 cycles (2 ms at nominal 74.25 MHz). The timer simulation passed; routed setup, hold, pulse-width and bus-skew guards passed before bitstream generation. The bitstream, matching LTX, source manifest and routed reports are archived in `builds/bit_archive/20261007_contentmon_trig30_e462da6/`.

Fresh OSD readbacks found all six cameras at manual 1/240 s, AGC 0 dB. Camera 1 remained FreeRun and cameras 2-6 ExtTrig. These differ from the previous sweep's camera-1 1/60 s and camera-2 1/30 s starting settings; prior cameras 3-6 shutters were not read back. Camera 1 and cameras 3-6 were left untouched in this run. Camera 2 was set to 1/30 s for the sweep and restored to its actual starting 1/240 s afterward.

A fresh 60 Hz reference with these controls and camera 2 at 1/30 s contains 612 complete reports: camera 2 changes every second raster (about 15 updates/s), while cameras 1 and 3-6 change every raster (about 30 updates/s). Whole-active-raster and central-patch CRC spacing agree; all geometry is valid.

| Capture | OSD shutter | Setting (ms) | Input rasters/s | Payload updates/s | Changed / repeated pairs | Change spacing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| input_00_shutter30 | 1/30 s | 33.333 | 29.999607 | 14.999803 | 44 / 46 | 2 raster(s) |
| input_01 | 1/60 s | 16.667 | 29.999606 | 14.999803 | 45 / 44 | 2 raster(s) |
| input_02 | 1/120 s | 8.333 | 29.999606 | 14.999803 | 46 / 43 | 2 raster(s) |
| input_03 | 1/180 s | 5.556 | 29.999606 | 14.999803 | 44 / 44 | 2 raster(s) |
| input_04 | 1/240 s | 4.167 | 29.999607 | 29.999607 | 86 / 0 | 1 raster(s) |
| input_05_return180 | 1/180 s | 5.556 | 29.999606 | 14.999803 | 46 / 41 | 2 raster(s) |
| input_06 | 1/300 s | 3.333 | 29.999607 | 29.999607 | 88 / 0 | 1 raster(s) |
| input_07 | 1/500 s | 2.000 | 29.999607 | 29.999607 | 89 / 0 | 1 raster(s) |
| input_08 | 1/1000 s | 1.000 | 29.999606 | 29.999606 | 87 / 0 | 1 raster(s) |
| input_09_restore30 | 1/30 s | 33.333 | 29.999607 | 14.999803 | 45 / 44 | 2 raster(s) |

Same 15 / 30 update pattern at both trigger rates.
First every-raster setting: 1/240 s; return 1/180 s gives 15.
30 Hz controls: cameras 1 and 3–6 ≈30 updates/s (1/240 s).

The new diagnostic has visible video. All ten ILA conditions use one uninterrupted 30 Hz load, with menus closed during capture.
Baseline 1/30 s was read before loading and again after capture on the diagnostic. All other settings were read directly before capture.
The 1/240 to 1/180 reversal and 1/1000 to 1/30 return retain the same running FPGA image and trigger configuration.

The prior 60 Hz diagnostic had black output. The fresh 30 Hz diagnostic provides visible camera video and OSD.
The prior black-output fault remains unexplained. The new image has been used for this measurement experiment; full operational validation is outside this test.

Every 30 Hz condition contains 612 complete reports in 12 blocks, for 6,120 reports across all six inputs. Probe11 independently confirms 30 common trigger edges per nominal one-second window, with quantized period observations recorded per condition. All complete reports have flags 3, 2,073,600 active Y/C samples, 1080 active lines and 1125 EAV markers. Gaps and incomplete mailbox packets are excluded. Full and ROI histograms, control rates, raw CSVs and OSD readbacks are retained. This measures transmitted payload novelty before DDR, not accepted electrical triggers or physical sensor exposures.

This fixed-timer 30 Hz test is distinct from the earlier strobe-following 30 Hz USB experiment. The new 30/60 Hz diagnostic RTL differs only in timer period; trigger-derived DDR epoch timing still changes. The raw-input CRC location avoids attributing DDR output behavior to the cameras. Short segmented captures do not establish long-duration performance.

30 Hz timing passed existing constraints: WNS 0.098 ns, WHS 0.010 ns, WPWS 0.048 ns; negative totals zero.

Final restoration: working fixed-60-Hz FPGA image restored at 21:25:49 KST; camera 2 ExtTrig 1/240 s verified; camera 1 FreeRun 1/240 s verified and untouched; cameras 3-6 untouched at their initial 1/240 s. Display selection 1, all menus closed, poses unchanged. Final USB rates: camera 1 30.054, camera 2 29.954 updates/s. Patch archives match all saved hash timelines. Original top-level RTL and project file restored; no QSPI write, MCU flash, OSD SAVE or camera power cycle.

Evidence root: `captures/exposure_sweep_30hz_20261007_2020/`. See `initial_state.json`, `sweep_index.json`, `sweep_validation.json` and `final_state.json`. The consolidated Excel report preserves the earlier measurements and adds this sweep, its same-settings 60 Hz reference and the latest restoration state.


## Camera 2 requested 1080p/60 output test, 7–8 October 2026

At 23:53 KST, the actual starting display selection was 3. Camera 2 was visually verified as ExtTrig, manual 1/240 s, AGC 0 dB, NTSC 1080p/30 fps, BT.1120/SDI and EX-SDI OFF. Both trigger/strobe polarities were OFF, both delays 0.0 and width 1.0. Only its HD FORMAT setting was changed for this experiment; other cameras and exposure/trigger settings were held fixed.

One right step from the verified 1080p/30 HD FORMAT row made displayed video black. One left step restored visible 1080p/30. The preceding option was visibly 720p/60; stepping right twice from it again produced the black-output setting. The manufacturer's [format list](https://www.wonwoo.com/kr/product/product_view.php?idx=188&part1_idx=&part2_idx=15&part3_idx=) lists 1080p30, 1080p60 and 720p60 for NTSC. The command sequence and measured 60-Hz raster starts are consistent with the requested 1080p/60 selection, but **direct readback of its OSD text was unavailable**. The black screenshots are command evidence, not setting readback. The menu was closed before acquisition.

The archived fixed-60-Hz content-monitor diagnostic was loaded, and probe11 independently confirms 60 trigger edges per nominal second in both acquisitions. Each acquisition has 12 blocks, 612 complete five-packet reports and 12 excluded partial mailboxes. Both format conditions use the same uninterrupted diagnostic load.

| Camera 2 condition | Raster starts/s | Reports | Valid geometry | Accepted content updates/s |
| --- | ---: | ---: | ---: | --- |
| Requested 1080p/60 setting | 59.999241 | 179 | 0 | Unverified |
| Return to verified 1080p/30 | 29.999611 | 106 | 106 | 29.999611 |

At the 60-mode setting, all 179 camera-2 reports fail expected 1920×1080/1125 geometry. Flags are 5 in 157 reports and 1 in 22; none has geometry-valid bit 1 set. Active-line counts range 642–1080, and EAV counts 907–1074. Although full and patch CRCs change on all 167 adjacent comparisons, **these changes cannot establish fresh-image FPS** because invalid sampling can change checksums. The raw decoder's approximately 60 `estimated_updates_hz` is excluded from accepted results. Probe11 counts the normal receiver VSYNC and records 0/s for camera 2 in this condition (three observations). It returns to 30/s at 1080p/30 (four observations). The passive monitor detecting about 60 raw marker starts/s must not be interpreted as 60 valid frames received.

Returning one HD FORMAT step to 1080p/30 on the same diagnostic load restores correct geometry in all 106 camera-2 reports: 2,073,600 active Y/C samples, 1080 active lines and 1125 EAV. All 94 adjacent comparisons change, and all 82 observed change intervals are one raster; full and patch CRC agree. The other five inputs retain valid geometry in both conditions.

A read-only timing analysis of the archived routed diagnostic changed CAM1_PCLK (camera 2) from its original 100 MHz constraint to the assumed 148.5 MHz for 1080p/60. Full-design WNS is −0.883 ns, TNS −69.112 ns, with 162 failing endpoints; the worst paths reach the DDR capture FIFO. The passive content monitor's 328 registers meet internal setup (+3.826 ns) and hold (+0.020 ns) under that assumption. External Y/C input delays are unconstrained, and actual camera PCLK was not independently measured. Thus full-design timing failure is a separate confirmed limitation; it does not by itself identify the cause of the raw monitor's lost markers. Valid raster payload reception at 1080p/60 must be established before claiming the camera's fresh-image rate.

The working fixed-60-Hz FPGA image was restored at 00:05:19 KST on 8 October. Camera 2 was visually read back as the starting 1080p/30, ExtTrig, 1/240 s and AGC 0 dB, with unchanged trigger parameters. Display selection returned to its actual starting value 3, all menus closed, poses and seven display parameters unchanged. Camera 2 and final displayed camera 3 had visible video. No QSPI write, MCU flash, camera power cycle, OSD SAVE or tracked source/project edit occurred.

Evidence: `captures/cam2_1080p60_20261007_2353/format_test_results.json`, both acquisition folders, OSD PNG/command logs, timing reports and `final_state.json`. The consolidated workbook includes the new format test and explicitly leaves 60-mode content-update FPS unverified.

## Dedicated 1080p60 RTL build and live validation, 8 October 2026

The requested standalone input diagnostic is in `diagnostics/eo60`. It uses the
27 MHz board reference, a fixed 60 Hz / 2 ms trigger, both PCLK sampling edges,
strict Y/C sync and raster geometry checks, and full-frame/96×96-region CRCs.
It has no DDR capture or video output. The operational top and project were not
modified for this build.

Delivered build: `builds/eo60_input_20261008_r2/Eo60InputTestTop.bit` and matching
LTX. SHA-256: `83295cfeff46c0595e1e1d126d3f4763fbbe85696a77dd1ab147083fff273ef0`.
Routed setup/hold/pulse-width margins at 148.5 MHz are +2.345 / +0.010 / +2.825 ns,
with zero failing endpoints. External input delays remain a zero-reference
aperture model because camera/PCB clock-to-data bounds are unavailable.
The initial HD-bank IDDRE1 trial failed its 8 ns minimum-period requirement and
was rejected without a bitstream. The delivered sampler uses explicitly timed
fabric SDR registers; the routed audit confirms 32 input sampling registers,
zero IDDRE1 primitives, and passing bus-skew checks. Four RTL simulations and
eight decoder tests passed.

Camera 2 stayed in ExtTrig, manual 1/240 s and AGC 0 dB throughout the same
uninterrupted diagnostic load. Eight capture blocks were taken per format.

| Format | Sampling edge | Valid / complete reports | Raster frames/s | Input content updates/s |
| --- | --- | ---: | ---: | ---: |
| 1080p30 control | Rising | 128/128 | 29.999577 | 29.999577 |
| 1080p30 control | Falling | 128/128 | 29.999635 | 29.999635 |
| 1080p60 target | Rising | No complete reports | Unavailable | Unverified |
| 1080p60 target | Falling | 256/256 | 59.999228 | 59.999228 |
| Return 1080p30 | Rising | 128/128 | 29.999637 | 29.999637 |
| Return 1080p30 | Falling | 128/128 | 29.999580 | 29.999580 |

At 1080p60, the independently counted PCLK is 148,497,920–148,498,176 Hz relative
to the uncalibrated 27 MHz reference. Every observed trigger window reads 60.
All 256 falling-edge reports contain 2,073,600 active samples, 1080 active lines,
1125 EAV markers, 2200 clocks/line and 2,475,000 clocks/raster, with zero Y-parity
or C-sync errors. All 248 adjacent comparisons change in both CRCs, and all 240
measured change intervals are one raster. Use falling-edge sampling for this
test. A missing rising-phase report does not mean the camera produces zero FPS.

The verified input result is approximately **60 raster frames/s and 60 changing
pixel payloads/s at 1/240 s exposure and 60 Hz trigger**. Other exposures were
not tested at 1080p60. This does not qualify the operational DDR/video pipeline
for 1080p60 or directly count sensor exposures. The 60-format OSD text remained
unavailable during the video-less diagnostic; paired format commands, measured
PCLK and valid raster geometry independently support the format transition.

The original working fixed-60-Hz image was restored at 01:15:44 KST. Visible OSD
readbacks confirm camera 2 returned to 1080p30, ExtTrig, 1/240 s, 0 dB and its
original trigger parameters. Final display is camera 3 with visible video,
menus closed, and pose/display parameters matching the initial records.

Evidence: `captures/eo60_diagnostic_20261008_0051/live_results.json`, its three
successful capture folders and `final_state.json`. The consolidated Excel
report adds these results at Report row 80 and ILA Results row 99, preserving
the earlier exposure sweeps and the earlier full-design failure record.

## 1080p60 slower-shutter sweep — 8 October 2026

Requested follow-up: check lower shutter speeds with the dedicated input RTL.
Camera 2 remained in ExtTrig with manual shutter and AGC 0 dB. All five captures
used the **60 Hz** diagnostic trigger, active high for 2 ms. This is the generated
signal observed inside the FPGA; accepted camera triggers were not measured.

| Shutter menu setting | Setting (ms) | Raster frames/s | Input content updates/s | Valid / complete falling reports | Changed adjacent pairs | Repeated adjacent pairs | Inter-change spacing: count |
|---|---:|---:|---:|---:|---:|---:|---|
| 1/180 s | 5.556 | 59.999226 | 59.999226 | 245/245 | 237 | 0 | 1: 229 |
| 1/120 s | 8.333 | 59.999228 | 59.999228 | 245/245 | 237 | 0 | 1: 229 |
| 1/60 s | 16.667 | 59.999231 | 59.999231 | 256/256 | 248 | 0 | 1: 240 |
| 1/30 s | 33.333 | 59.999229 | 59.999229 | 256/256 | 248 | 0 | 1: 240 |
| Return 1/240 s | 4.167 | 59.999225 | 59.999225 | 256/256 | 248 | 0 | 1: 240 |

All 1258 complete falling-edge reports have strict 1920 × 1080 active geometry,
1125 EAVs, 2200 clocks/line and 2,475,000 clocks/raster, with zero Y-parity or C-sync
errors. Whole-raster and central 96 × 96 ROI CRCs agree on the reported cadence.
The rising-edge monitor produced 22 reports, of which 0 were valid;
its data are excluded from content-rate conclusions. Invalid or missing reports
are not a measured zero camera FPS.

The diagnostic bitstream was unchanged:
`builds/eo60_input_20261008_r2/Eo60InputTestTop.bit`, SHA-256
`83295cfeff46c0595e1e1d126d3f4763fbbe85696a77dd1ab147083fff273ef0`. Each condition reloaded this exact bitstream and
collected eight segmented ILA blocks. Only consecutive valid raster sequence
numbers form CRC comparisons; JTAG upload gaps and partial packets are excluded.
PCLK observations and full row-level reports remain in the raw capture summaries.

### Readback and scope

The operational design cannot display this camera's 1080p60 input reliably, and
the standalone diagnostic has no video output. Therefore each shutter was
visibly read at 1080p30 immediately before and after its 1080p60 acquisition.
No shutter commands occurred inside that bracket. Both OSD images show the same
selected shutter, manual lens and 0 dB AGC. The 60-format transition is supported
by the recorded menu navigation, measured ~148.498 MHz PCLK, ~60 rasters/s and
valid complete 1080p geometry; there is no direct 60-format OSD text readback.

The shutter values are **menu settings**, not independent measurements of sensor
integration time. In particular, a 1/30 s menu selection does not prove that the
camera integrates for 33.333 ms in 60-format operation. Internal clamping,
format-specific shutter handling, integration scheduling and accepted-trigger
behavior remain unresolved. The readbacks do not independently verify the active
shutter used inside 60-mode. CRCs
measure received pixel-payload changes, not physical exposure count; equality
is not collision-free byte proof. Clock rates inherit the uncalibrated 27 MHz
reference and PCLK has ±256 Hz quantization. External input timing retains the
documented zero-reference aperture model rather than measured camera/PCB bounds.

These measurements are a separate 1080p60 sweep. Earlier ~15/~30 content-rate
results used 1080p30 output and remain valid for their recorded conditions.
This diagnostic result does not qualify the full DDR/video design for 1080p60.

### Evidence and restoration

Evidence: `captures/eo60_exposure_20261008_0344/sweep_results.json`, with one
condition folder per table row. Each contains raw ILA CSVs, decoded reports,
summary, exact OSD key transactions, before/after readback review and FPGA
program/restore logs. The consolidated Excel report includes the new summary
at Report row 103 and detailed results at Exposure Sweep row 208.

The operational FPGA image was restored. Camera 2 was visibly verified at
1080p30, ExtTrig, manual 1/240 s and AGC 0 dB; trigger/strobe polarities OFF,
delays 0.0 and strobe width 1.0. Final display is camera 3, menus closed. Display
parameters and pose offsets match the initial records. No QSPI write, MCU
firmware flash, camera power cycle or OSD SAVE was used. See `final_state.json`.

## 8 October verification: direct 60-mode OSD and Freeze controls

**Final verdict: the earlier claim of 60 fresh input FPS at a 1/30 s shutter is withdrawn.** Two independent checks invalidate that interpretation: the shutter was not actually displayed as 1/30 s in 60-mode, and the original CRC diagnostic reports changes on a frozen camera image. Approximately 60 input rasters/s is confirmed; whole-frame fresh-image FPS at 1080p60 is not established by these captures.

### Manufacturer manual and direct shutter readback

The supplied DM-G15-42 approval sheet v1.04, dated 4 January 2024, is at `C:/SVNProjects/IMU_Stabilize_v40/Manual/EO/원우Approval sheet _DM-G15-42_v1.04_240104.pdf`. SHA-256: `e1f5c8ce23da0bca8b7f631279c96de8f947967754329e5fa9586fe79a0b1634`. Its printed page 15 (PDF page 16) specifies 2200 pixel clocks per line and 1125 total lines for 1080p60. Printed pages 39/41 describe ExtTrig and polarity, while page 43 explicitly labels its shutter table as **30/25 fps mode**. It does not supply the 60-mode shutter mapping assumed by the earlier sweep. Printed pages 47/48 describe DNR and Freeze. The supplied catalogue advertises 1080p60 but does not establish 60 independent exposures/s at every shutter setting, or a universal 25 Hz limit.

A new ILA image buffer made the actual OSD visible without the operational DDR/video pipeline. Camera 2 read **1/30 s at 1080p30**. Changing only HD FORMAT to **1080p60** changed the Exposure OSD to **1/60 s**, with no intervening shutter command. ExtTrig and 0 dB remained selected. One slower step then displayed **2x**. These are directly read menu values, not measured physical integration times. No mapping for other old shutter selections is inferred.

Evidence below is relative to `captures/eo60_verify_20261008/`:

- `osd30_shutter30_reopened/frame_04757.png`: 30-mode 1/30 s.
- `osd60_format/frame_10194.png`: 1080p/60 fps format.
- `osd60_exposure_after_switch/frame_15230.png`: 60-mode 1/60 s.
- `osd60_slower_attempt/frame_20084.png`: 60-mode 2x.
- `osd60_trigger/frame_24045.png`: ExtTrig.

### Executed tests

All eight conditions used the internally generated **60 Hz trigger, 2 ms high**. The counter verifies generated trigger cadence, not camera-accepted triggers or exposure starts. Full Y/C CRC and central 96x96 Y/C ROI CRC were compared only between adjacent valid raster sequence numbers. Upload gaps and partial/invalid reports were excluded. Rates use the uncalibrated 27 MHz reference.

| Condition | OSD shutter | DNR | Freeze | Valid falling reports | Adjacent pairs | Full CRC changed | ROI CRC changed | Raster rate |
|---|---|---|---|---:|---:|---:|---:|---:|
| 1080p30 baseline, snapshot build | 1/30 s | 2D+3D | OFF | 128 | 120 | 63 | 63 | 29.999636/s |
| 1080p60, snapshot build | 2x | 2D+3D | OFF | 128 | 120 | 105 | 60 | 59.999317/s |
| 1080p60, snapshot build | 2x | 2D+3D | ON | 128 | 120 | 117 | 0 | 59.999249/s |
| 1080p60, original r2 build | 2x | 2D+3D | ON | 256 | 248 | 248 | 248 | 59.999246/s |
| 1080p60, snapshot build | 2x | OFF | ON | 128 | 120 | 118 | 0 | 59.999308/s |
| 1080p60, snapshot build | 2x | OFF | OFF | 128 | 120 | 119 | 60 | 59.999253/s |
| 1080p60, snapshot build | 1/60 s | OFF | OFF | 128 | 120 | 117 | 60 | 59.999255/s |
| 1080p30 control, snapshot build | 1/60 s | OFF | ON | 127 | 119 | 0 | 0 | 29.999607/s |

The last control's shutter was read immediately afterward at unchanged 1080p30, before restoration shutter writes (`post30_control_shutter.png`). The rising-phase 30-mode frozen control also passed: 128 valid reports, 120 adjacent pairs, zero changes in either CRC. The new 60-mode rising-phase reports were invalid and were excluded.

The **original r2 negative control is decisive**. Freeze ON was directly visible in the OSD. Its frozen closed-menu sampled image was identical before and after temporarily programming the original r2 bitstream, with no camera commands between the bracket snapshots. All four reconstructed 960x540 Y arrays share SHA-256 `9be07f6b8ad95324d3a02039f93f00b44a5dad8a0eb4fb226f5080917bb11a7a`; pixel differences are zero. Yet original r2 reports full and ROI CRC changes on **248/248** valid adjacent pairs, and its raw decoder accepts approximately 60 updates/s. That automatic acceptance is rejected by this independent control. Raw files are retained unchanged.

The snapshot build's frozen ROI remains constant at 60-mode, but its full CRC does not. Disabling DNR does not fix that failure. On an unfrozen input with DNR OFF, both directly read 1/60 s and 2x produce a two-raster ROI change cadence, approximately **30 local patch changes/s**. This does not certify the whole frame's fresh-image FPS or count physical exposures. The sampled Y image also does not prove equality of every full-resolution Y/C byte. A passing full-frame frozen control is required before using whole-frame CRC changes as a freshness measure.

At 1080p30, the same snapshot build passes the frozen control on both phases and the 1/30 s baseline reproduces approximately 15 payload updates/s. Earlier 1080p30 sweeps at 30 and 60 Hz triggers remain separately scoped; this correction concerns the later 1080p60 conclusions.

### RTL validation, remaining uncertainty and concrete next test

The new standalone source is `diagnostics/eo60_snapshot`. It stores two consecutive 960x540 Y arrays by selecting every second pixel/row, without filtering, plus 1472 packets of the next raster. An RTL simulation and an independent synthetic-image decoder test passed packing, coordinates, sequence wrap, packet completeness and a single-pixel difference check. The existing sampler/CRC logic was retained.

Build `builds/eo60_snapshot_20261008_r1` has bit SHA-256 `5f8e2eb39d7676f7b250dfdcdba9c5b2d584144ed55d89a121cb1c57a7083a62` and LTX SHA-256 `904156adff3c76a82256dfde12de41cc08696743b4b7cf4bd9c8aa39f4c001cc`. Routed WNS is +1.160 ns, WHS +0.001 ns and WPWS +2.825 ns; negative totals are zero and bus skew passes. The audit finds 32 fabric SDR input registers and no IDDRE1. The two critical CDC entries are internal to encrypted ILA IP; no blanket clean-CDC claim is made. The input constraints use a zero-reference arrival model rather than measured camera/PCB clock-to-data bounds.

The build-dependent frozen behavior raises a receiver/sampling-integrity concern, but the exact source of variation is **not isolated**. Internal timing and valid geometry do not prove integrity of every active pixel at 148.5 MHz. DNR OFF excludes that setting as the sole explanation; it does not isolate every camera processing stage.

The remaining qualification test has explicit acceptance criteria:

1. At directly verified 1080p60, establish stable full Y/C capture with Freeze ON across several static images and multiple blocks. Require zero unexplained byte/CRC changes across valid adjacent rasters; investigate sampling phase and external timing margin if it fails.
2. Only after that control passes, disable Freeze and capture a timed optical pattern with direct 60-mode shutter readback, logged trigger timing and frame-by-frame content comparison. Count newly represented scene times, separately from raster timing and CRC novelty.
3. To verify 1/30 s or 1/60 s **physical integration**, use a calibrated pulsed-light or moving target together with independently validated exposure timing. A user-programmable strobe width alone is not exposure-time readback.

The supplied manuals do not substantiate a universal 25 Hz limit. The manufacturer's original quoted wording/configuration remains unavailable, so that broader claim cannot be adjudicated from this setup alone.

### Consolidated report and restoration

`verification_results.json` contains the curated results, raw summary links, manual hash and reviewed OSD evidence. Each condition retains raw ILA CSVs, decoded rows and acquisition provenance. The Excel workbook preserves the original measurements, marks prior 60 fresh-FPS values **Unverified**, adds this verification at Report row 125 and Exposure Sweep row 233, and embeds direct OSD images at Report rows 163–199.

Restoration completed and was verified at **2026-10-08 15:42:36 +09:00**. The operational bit SHA-256 is `d905e96d96990528a5c2098e0e018fa9d88814a18703fb0ce4f09a348b5f2cfd`. Camera 2 is 1080p30, ExtTrig, manual 1/240 s, AGC 0 dB, DNR 2D+3D and Freeze OFF. Trigger/strobe polarities are OFF, delays 0.0 and strobe width 1.0. Starting display **camera 6** and all display/pose parameters were restored; menus are closed. Other cameras' OSD settings were untouched. No QSPI write, MCU flash, camera power cycle or OSD SAVE was used. `final_state.json` records reviewed image hashes; `final_exposure240.png` is the final shutter proof. The older `final_exposure.png` is only an intermediate 1/300 s restoration image.
