# Camera 2 / 1080p60 input diagnostic

**8 October 2026 correction: do not use this build's 60-mode CRC novelty as verified fresh-image FPS.** The original r2 bitstream failed a frozen-camera negative control: all 248 adjacent full and ROI CRC pairs changed despite an unchanged frozen sampled image bracketing the test. Direct OSD readback also shows that 1/30 s selected in 1080p30 becomes 1/60 s in 1080p60. The earlier 60-mode rate interpretations below are superseded by `captures/eo60_verify_20261008/verification_results.json` and the final section of `docs/TEST_EO_CAMERA_CONTENT_20261007.md`. Raster timing remains a separate measurement. The decoder's `content_rate_accepted` flag is insufficient without an independent negative control.

This is a separate, JTAG-only design for the KU15P board. It measures camera 2
(board signals `CAM1_*`) at its input pins. It contains no DDR capture, image
renderer, MCU register interface, or video output. The display will be blank
while this image is loaded. The operational project is not changed by the build.

The default trigger is **60 Hz, active high for 2 ms**, sent to all five follower
trigger outputs. The reference is the board's nominal 27 MHz oscillator. The
camera PCLK is independently constrained to **148.5 MHz**. Rates inherit the
27 MHz oscillator's actual accuracy; its frequency has not been calibrated.

## Validated build — 8 October 2026

Build: `builds/eo60_input_20261008_r2/Eo60InputTestTop.bit` with the matching LTX.
SHA-256: `83295cfeff46c0595e1e1d126d3f4763fbbe85696a77dd1ab147083fff273ef0`.
Routed setup/hold/pulse-width slack: **+2.345 / +0.010 / +2.825 ns**.
All failing-endpoint totals are zero under the documented input model. The
routed audit confirms 32 fabric SDR sampling registers, zero IDDRE1 primitives,
and passing debug-core bus-skew checks. Four RTL simulations and eight decoder
tests passed.

Live camera-2 checks used ExtTrig, 60 Hz trigger, manual 1/240 s, and 0 dB AGC:

| Camera format | Sampling edge | Valid / complete reports | Raster rate | Content updates/s |
|---|---|---:|---:|---:|
| 1080p30 control | Rising / falling | 128/128 each | 29.9996 | 29.9996 |
| 1080p60 target | Rising | No complete reports | Unavailable | Unverified |
| 1080p60 target | Falling | 256/256 | 59.9992 | 59.9992 |
| Return to 1080p30 | Rising / falling | 128/128 each | 29.9996 | 29.9996 |

At 1080p60, PCLK was 148,497,920–148,498,176 Hz and the trigger counter read
60 Hz. All 248 captured adjacent valid falling-edge pairs changed in both CRCs.
All complete reports had zero Y-parity and C-sync errors. Use the **falling
phase** for this 1080p60 test. This initial run used only 1/240 s; the subsequent
slower-shutter results are appended below. A missing
rising-phase report is not a measured zero-FPS camera.

Evidence: `captures/eo60_diagnostic_20261008_0051`. The 60-format selection was
made with paired OSD commands; there was no visible 60-format text readback
through this video-less diagnostic. PCLK and valid raster geometry independently
confirm the transition. This result does not qualify the full DDR/video design
for 1080p60.

## What is measured

| Measurement | Method |
|---|---|
| PCLK frequency | Divide PCLK by 256, synchronize, count rising edges over 27,000,000 reference clocks; quantization approximately ±256 Hz |
| Trigger rate | Count internally generated rising edges in each reference window; does not measure the camera connector electrically |
| Raster rate | Timestamp qualified Y-channel vertical-blanking-to-active transitions; also count PCLKs per raster |
| Input content updates | Compare CRC-32/MPEG-2 of every active Y/C sample and a central 96×96 region across adjacent valid rasters |
| Input integrity | Verify Y TRS parity, matching C TRS, 1920×1080 active geometry, 1125 EAVs, 2200 clocks/line, and 2,475,000 clocks/raster |
| Sampling phase | Independent monitors on rising and falling PCLK samples from two explicitly timed fabric SDR register paths |

Both CRCs start at `FFFFFFFF`, process Y then C, and have no final XOR or
reflection. Sequence numbers are not part of either CRC. A changing CRC is
evidence of changed received samples, not a direct measurement of sensor
exposures. A static/noiseless image cannot establish content cadence from CRCs.

The decoder reports content FPS only when all complete reports in that phase
have valid geometry and sync, the raster/PCLK rates match the selected mode,
the trigger counter reads 60, and the full-frame and region CRCs show the same
uniform update spacing. Partial mailboxes and gaps cannot form comparison
pairs. Invalid reports yield `input_updates_hz: null`.

## Timing qualification

The input XDC uses **zero-reference input delays** to expose the implemented
setup/hold aperture. Camera clock-to-data limits and PCB skew are not available.
Passing this model is **not external-interface timing signoff**. Inspect both
input timing reports and require clean live geometry before trusting content
rates. Do not treat either sampling phase as valid because its CRC changes.

The sampler uses fabric SDR registers intentionally. The trial HD-bank IDDRE1
implementation required an 8.000 ns minimum period in this part's Vivado timing
model, which failed the 6.734 ns camera clock. That trial was rejected without
generating a bitstream. The replacement keeps all sampler paths timed, including
the falling-to-rising transfer; it does not waive the failed primitive limit.

The two payload synchronizer stages precede a three-stage report toggle.
Payloads remain stable for one raster, while both mailboxes drain in less than
40 microseconds at 27 MHz. The PCLK counter crosses only a divided single bit.
The asynchronous clock groups apply to these intentional crossings. The camera
input itself remains timed; trigger outputs are asynchronous exposure events.

## Build and simulations

From the repository root in PowerShell, using Vivado 2025.2:

```powershell
$vivado = 'C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat'
& diagnostics/eo60/scripts/simulate.ps1 -OutputDirectory sim_out/eo60_new
python diagnostics/eo60/scripts/test_decode.py
& $vivado -mode batch -source diagnostics/eo60/scripts/build.tcl -tclargs builds/eo60_new
```

Both scripts require a new output directory. The build creates its own XPR and
ILA IP. It produces routed timing, input aperture, CDC, clock, utilization, DRC,
and IO reports. Bitstream generation is withheld if setup, hold, or pulse-width
summary slack is negative. Review diagnostics in addition to that numeric guard.

The simulations cover repeated and changed content, corrupt sync/geometry,
a complete 1080p60 frame against independent CRC vectors, trigger pulse width
and period, frequency counting, both report mailboxes, and vendor-model FDRE
sampling alignment. Decoder tests cover acceptance, repeated frames, invalid
frames, incomplete reports, incorrect trigger/signature, and timestamp wrap.

## Live procedure

1. On the working image, record the camera's OSD settings and displayed camera.
   Begin with camera 2 at 1080p30, external trigger, and 1/240 s as a control.
2. Program `Eo60InputTestTop.bit` with its matching LTX using
   `diagnostics/eo60/scripts/program.tcl`. It uses 6 MHz JTAG for the 27 MHz
   debug hub and changes volatile FPGA configuration only.
3. Wait at least two seconds for frequency windows to settle. Capture and decode:

```powershell
& $vivado -mode batch -source diagnostics/eo60/scripts/capture.tcl -tclargs builds/eo60_new/Eo60InputTestTop.ltx captures/eo60_new_control 12
python diagnostics/eo60/scripts/decode.py captures/eo60_new_control --expected-raster-hz 30
```

4. Use the working image to set camera 2 to 1080p60, then reload this diagnostic.
   Capture into a different new directory and decode with `--expected-raster-hz 60`.
   An acknowledged OSD key is not a visible format readback. Record that limitation
   if the operational receiver loses its picture at 1080p60.
5. Require stable PCLK, valid frame geometry, clean sync, and repeatable results
   before any content-FPS claim. Compare rising/falling phases. Only then expand
   to exposure sweeps.
6. Restore the camera's initial format/exposure, the working bit/LTX, and the
   original display selection. Verify the OSD and picture again.

Capture never programs the FPGA. It configures 256 windows × 32 samples on the
reference ILA, triggering on event bit 63, and restores the ILA acquisition
settings afterwards. Raw PCLK-domain ILA samples are available separately for
TRS or edge inspection. Never use an old content-monitor decoder for this design.

## Reference ILA / protocol v1

| Probe | Width | Meaning |
|---|---:|---|
| 0 | 64 | `eo60_event_word` |
| 1 | 32 | `eo60_pclk_hz` |
| 2 | 8 | `eo60_trigger_edges` |
| 3 | 32 | `eo60_seconds` |
| 4 | 32 | Constant protocol signature `E0600001` |

Event word: valid `[63]`, phase `[62:60]` (0 rising, 1 falling), kind `[59:57]`,
sequence `[56:41]`, flags `[40:33]`, reserved `[32]`, value `[31:0]`.
Eight packets form a report, 64 reference cycles apart:

| Kind | Value |
|---:|---|
| 0 | Full-frame CRC |
| 1 | Region CRC |
| 2 | Active sample count |
| 3 | Active lines `[23:12]`, EAV count `[11:0]` |
| 4 | 27 MHz timestamp (wraps after about 159 s) |
| 5 | PCLKs per raster |
| 6 | Minimum line clocks `[31:16]`, maximum `[15:0]` |
| 7 | C-sync mismatches `[23:12]`, bad Y XY parity count `[11:0]` |

Flags: bit 0 complete, bit 1 geometry valid, bit 2 bad active line, bit 3 bad Y
parity, bit 4 field changed, bit 5 bad line period, bit 6 bad frame period.
The decoder additionally requires zero C-sync errors. Good flags are `03`.

Raw ILA probes are rising Y/C (16), falling Y/C (16), and falling/rising monitor
live flags (8 each). Each live byte is `{start,prefix,xy_ok,eav,sav,bad_line,
bad_xy,bad_period}`.

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


Shutters were visibly read at 1080p30 before and after each 1080p60 capture.
Actual integration time and any internal clamping were not measured. See
`docs/TEST_EO_CAMERA_CONTENT_20261007.md` for limitations and restoration, and
`captures/eo60_exposure_20261008_0344/sweep_results.json` for the raw evidence index.
