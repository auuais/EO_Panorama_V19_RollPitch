# Handoff: EO camera input frame rate — please review for errors

> **SUPERSEDED** by `HANDOFF_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md`.
> This document's central conclusion — that the two modes measure the same —
> came from counting frame starts, which cannot see duplicated content.  The
> cameras do differ: 30 distinct images/s free-running, 15 in trigger mode.
> Kept for the method and the mistakes it records.

**Date:** 2026-10-06
**Repo:** `E:\Xylinx\EO_Panorama_V19_RollPitch`
**Bitstream under test:** commit `bd9af71`, archive
`builds/bit_archive/20261006_150257_camratemon_bd9af71/` (loaded over JTAG;
QSPI still holds an older image)

## Why you are reading this

The EO camera manufacturer states:

* **free-run mode: 30 Hz output**
* **trigger mode: output drops to about 25 Hz, even when the trigger is
  supplied at 30 Hz**

We built a measurement in the FPGA and **measured 30 fps in both modes**, on
every camera. That contradicts the manufacturer. Either the manufacturer's
claim does not apply to this configuration, or our measurement is wrong.
**Please look for the mistake in our work before we take this back to them.**

We would rather find an error here than tell a vendor their datasheet is wrong.

## What we built

`src/EoCamFrameRateMon.v` (new). Runs in `hd_clk` = 74.25 MHz, derived from the
board's 27 MHz oscillator through an MMCM (×44/16), so it is independent of
every camera clock.

Per camera, over a one-second window:

* **frame count** — frames per second as delivered at the camera pins
* **shortest and longest interval** between that camera's frame starts

Plus the FPGA trigger's own edge count and last interval.

A frame start is taken as **VSYNC falling**, copying the convention of the
existing follower diagnostic in
`src/KintexTop_EO_IR_HD_SDI_panorama_base.v` (`eoN_frame_start_cam0 =
eoN_vsync_cam0[2] && !eoN_vsync_cam0[1]`).

Periods are counted in **ticks of 256 `hd_clk` cycles = 3.44781 µs**. A 33.3 ms
frame is 9668 ticks; the 15-bit field saturates at 113 ms.

### Probe word (dbg_ila_1 probe11, 64 bits)

RTL packing, MSB first:

| bits | field |
|---|---|
| 63:62 | signature `2'b10` |
| 61:56 | trigger edges in the window |
| 55:42 | trigger last interval, ticks |
| 41:39 | which camera this word describes (`sel`, 0..5) |
| 38:31 | that camera's frames in the window |
| 30:16 | its shortest interval, ticks |
| 15:1 | its longest interval, ticks |
| 0 | spare |

`sel` advances once per window, so consecutive captures sweep the cameras.
`scripts/decode_cam_fps.py` extracts the same ranges — **please check the two
against each other**, a one-bit misalignment would explain a lot (see risk 2).

### Reproducing

```
vivado -mode batch -source scripts/measure_eo_cam_fps.tcl -tclargs 20
python scripts/decode_cam_fps.py <the printed CAM_FPS_OUTDIR>
```

The ILA probe was added through the IP customisation
(`scripts/add_cam_rate_probe.tcl`), not by editing the `.xci`.

## What we measured

Three runs, all with the same bitstream.

| run | camera state | result, every camera |
|---|---|---|
| `captures/cam_fps/20261006_200153` | all free-run | 30 fps, 33.3334–33.3369 ms, spread 3.4 µs |
| `captures/cam_fps/20261006_202138` | all trigger mode | 30 fps, 33.3334–33.3369 ms, spread 3.4 µs |
| `captures/cam_fps/20261006_204056` | cam 1 free-run, cams 2–6 trigger | 30 fps, 33.3334–33.3369 ms, spread 3.4 µs |

3.4 µs is **one tick** — the resolution floor. The two modes are
indistinguishable in this metric.

### Independent cross-check

`scripts/measure_cam_epoch_rate.tcl` reads the per-camera DDR descriptor epoch
counters, a completely separate path (frames actually written to memory, probed
for cameras 1 and 5 only). Per 2.4 s step it gave **29.6–30.3 fps for both**,
including camera 5, which was in trigger mode. So two unrelated paths agree on
30 fps.

### Evidence the cameras are not following the trigger

1. **Period mismatch.** Cameras 33.3335 ms, FPGA trigger 33.3473 ms — the
   cameras run 13.8 µs/frame faster, about 414 ppm. A camera slaved to a
   trigger should have exactly the trigger's period.
2. **Follower spread.** The existing diagnostic (`eo_follow_span_cycles`,
   spread between cameras 2–6 after a trigger) read medians of 3.0 ms, 0.0 ms
   and 8.9 ms across the three runs, maxima to 9 ms. Locked followers should
   sit within tens of µs, consistently.

Our working conclusion: the cameras are **configured** for trigger mode but are
not acting on the trigger, so they deliver their own free-run 30 Hz — which
would explain why the manufacturer's 25 Hz never appears.

## Known weaknesses in our own work — start here

1. **No simulation.** `EoCamFrameRateMon` has no testbench. It went straight to
   hardware. Nothing has verified the counter, the window, or the min/max logic
   against a known stimulus.

2. **The per-camera mux is unproven.** All six cameras report *identical*
   min/max in every run. That is plausible (six cameras near 30.000 Hz, 3.45 µs
   resolution), but it is also exactly what a broken mux or mis-wired
   `cam_vsync` bus would produce. **No test has yet forced one camera to differ.**
   Suggested: power one camera off (fps should go to 0 for that index only), or
   set one camera to a different frame rate, and confirm only that row changes.
   If this is wrong, every per-camera number above is one camera repeated.

3. **Edge polarity assumption.** Frame start = VSYNC falling, inherited from the
   follower diagnostic, never confirmed against the camera's actual timing. If
   VSYNC had more than one pulse per frame, the count would be wrong — though
   the measured 30/s and 33.3 ms agree with each other, which argues against it.

4. **Resolution.** 3.45 µs per tick cannot resolve ppm-level differences
   between free-running cameras, so "identical" here means "within one tick".
   The metric cannot separate the modes on its own; phase is the discriminator
   and we do not measure it.

5. **Trigger field, free-run run.** It reported 16.69 ms between edges while
   counting 30 edges/s. Our explanation: the trigger emits pairs ~16.7 ms apart
   then waits ~50 ms (two edges per 66.7 ms = 30/s), and the field reports only
   the last interval. The 1 s window lands on the same phase each time, hence 13
   samples at 16.69 ms and one at 50 ms. **This is inferred, not proven**, and if
   true it means `EoV19TriggerSource` is both following camera 1's strobe and
   free-running, with the 4 ms handover guard too short to suppress an edge
   16.7 ms away. In trigger mode the field was a clean 33.35 ms throughout.

6. **Capture cadence vs `sel`.** Captures land about every 2 s while `sel`
   advances every 1 s, so runs often miss cameras (one run sampled only 4 of 6).
   Harmless, but it means a run can silently report a subset.

7. **Process error, recorded for honesty.** The first run was free-run and was
   initially reported as "what locked cameras look like" — the mode was assumed
   from a label rather than verified, and the conclusion was written to fit it.
   The user corrected it. Do not trust mode labels in the capture directories;
   they are our notes, not instrumented facts.

8. **Trigger figures were presented per camera** in the first Excel export.
   They are one global signal. Corrected in
   `captures/cam_fps/EO_cam_input_fps_corrected.xlsx`.

## Specific questions

1. Does the probe-word layout in `EoCamFrameRateMon.v` match the field
   extraction in `decode_cam_fps.py`? A one-bit shift would make `sel` appear
   to take only even values — we *did* observe only even `sel` in some runs and
   attributed it to capture cadence (risk 6). Please rule the other explanation
   out properly.
2. Is `cam_vsync` wired to six distinct camera VSYNCs at the instantiation in
   `KintexTop_EO_IR_HD_SDI_panorama_base.v`, and does `eoN_vsync` mean what we
   assume (camera N's frame valid, one pulse per frame)?
3. Is there any path by which a camera genuinely outputting 25 Hz would be
   measured as 30 — repeated frames, a VSYNC that keeps running when no frame is
   delivered, or similar? This is the scenario that would reconcile our data
   with the manufacturer, so it deserves the most attention.
4. Is the 13.8 µs period difference between cameras and trigger a sound basis
   for "not locked", given both are measured by the same tick counter?

## Proposed next step

One RTL change and one rebuild, adding:

* **phase from each trigger edge to that camera's frame start** — constant means
  locked, sliding means free-running; with a 13.8 µs/frame difference the phase
  wraps about every 2.8 s, so it is unmistakable;
* **`EoV19TriggerSource`'s `strobe_seen` and `free_running` flags**, which exist
  in the RTL but are not probed — these also test the risk-5 hypothesis.

Before that, the cheap test in risk 2 (power one camera off and confirm only
that row changes) should be done, because it validates or destroys every
per-camera number in this document.

## Hardware state at the time of writing

* Cameras: camera 1 free-run, cameras 2–6 in trigger mode.
* FPGA: `bd9af71` loaded over JTAG. A power cycle reverts to the older QSPI
  image, which has no rate monitor.
* Serial and the SDI grabber are shared with the user's UI; both must be free
  for the measurement scripts to run.
