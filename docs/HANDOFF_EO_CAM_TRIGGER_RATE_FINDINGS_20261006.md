# Handoff: EO cameras deliver 15 distinct images/s in trigger mode — findings and method

**Date:** 2026-10-06
**Repo:** `E:\Xylinx\EO_Panorama_V19_RollPitch`
**Supersedes:** `HANDOFF_EO_CAM_INPUT_FPS_REVIEW_20261006.md` (earlier, incomplete
— its conclusion that the modes were indistinguishable came from measuring the
wrong thing; see "Mistakes" below)
**Bitstream for the final measurements:** commit `9a8a81e`, archive
`builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/`

## The manufacturer's claim

The EO camera vendor states:

* **free-run: 30 Hz output**
* **trigger mode: output falls to about 25 Hz, even with a 30 Hz trigger**

**The claim is directionally correct and we can now state it precisely.** The
effect is real but larger than described: we measure **exactly 15 Hz**, not 25.

## Headline findings

1. **In trigger mode every camera transmits 30 complete frames per second but
   only 15 distinct pictures.** Each picture is sent twice.
2. **Free-run gives 30 distinct pictures per second** on the same camera, same
   cabling, same FPGA build. Camera 1 is free-running and acts as the control in
   every measurement below.
3. **It is not interlacing or short frames.** Counted from the cameras' own
   SAV/EAV codes: 1125 lines per frame (1080 active + 45 blanking), minimum =
   maximum over a one-second window, and the F bit never changes.
4. **The rate does not follow the trigger frequency.** Driving the trigger at
   60 Hz instead of 30 Hz changed nothing: still 14.98 distinct images/s. So
   "the camera captures on every second trigger" is **wrong** — it looks like a
   fixed internal limit in triggered mode.
5. **Exposure is not the cause.** The user set shutter 12 and re-measured: no
   change (14.98 before and after). A long shutter duplicating frames was the
   obvious suspect and is ruled out.

### The numbers

Single-camera mode, USB3 grabber, 8 s per camera, 60 Hz grab rate:

| camera | mode | distinct images/s | repeats |
|---|---|---|---|
| cam 1 | free-run | 29.83 | each image ×2 |
| cam 2 | trigger | 14.98 | ×4 |
| cam 3 | trigger | 14.98 | ×4 |
| cam 4 | trigger | 14.97 | ×4 |
| cam 5 | trigger | 14.98 | ×4 |
| cam 6 | trigger | 15.00 | ×4 |

With the trigger at 60 Hz (confirmed in the FPGA: 60 edges/s, 16.667 ms):
cam 2 → 14.98, cam 3 → 14.98, cam 1 (free-run control) → 29.83.

From the cameras' SAV/EAV, all six identical:

| frames/s (TRS) | VSYNC/s | lines per frame | F changes/s |
|---|---|---|---|
| 30 | 30 | 1125 (min = max) | 0 |

## Method — four independent measurements

### 1. Frame starts at the camera pins (FPGA)

`src/EoCamFrameRateMon.v`, running in `hd_clk` (74.25 MHz from the board's
27 MHz oscillator, independent of every camera clock).

There is no separate VSYNC wire: the camera sends BT.1120 with embedded sync.
Each receiver (`Kintex_top_Ncam_ch1_*.v`) detects the TRS preamble `FF 00 00`
and latches the V bit from the XY word, so `eoN_vsync` is a level following the
V bit. The monitor counts its **falling edge** — V going 1→0, the first active
line of a frame — over a one-second window, and also keeps the shortest and
longest interval between frames.

**What this can and cannot see.** It counts frames *transmitted on the wire*. It
is blind to whether the picture inside is new, which is exactly the gap that
made the first handoff wrong. It also cannot see fields on its own, which is
why measurement 2 exists.

### 2. SAV/EAV content (FPGA)

Each receiver now also counts the EAV codes between frame starts and brings out
that count, the F bit, and a toggle per frame start (added in commit `9a8a81e`).
`EoCamFrameRateMon` reports per camera per second: last/min/max lines per frame,
how often F changed, and frame starts counted from the TRS decode — a
cross-check on measurement 1 through a different path. **The two counts agree at
30, which validates the counting method.**

Read out on `dbg_ila_1` probe11 (rate/period) and probe12 (lines/F):

```
vivado -mode batch -source scripts/measure_eo_cam_fps.tcl -tclargs 20
python scripts/decode_cam_fps.py <printed CAM_FPS_OUTDIR>     # rate, period
python scripts/decode_cam_trs.py <printed CAM_FPS_OUTDIR>     # lines, F bit
```

### 3. DDR descriptor epochs — WITHDRAWN, this measurement is invalid

`scripts/measure_cam_epoch_rate.tcl` was used as an "independent cross-check"
and it is not one. The independent review
(`REVIEW_EO_CAM_INPUT_FPS_20261006.md`) showed that `desc_epoch_ui` carries a
trigger-derived *label*, not a count of published frames: the label comes from
the global trigger count and pending-trigger occupancy, and a writer that is
behind consumes two labels for one raster, so labels skip. Their counterexample,
built from this repository's own model of those equations, produces **about
30.025 labels/s from 25 actual frames/s**.

So the 29.6–30.3 figure says nothing about camera frame rate and must not be
quoted. For a real DDR frame count, add a counter on `desc_valid_ui` — and even
that counts captured rasters, not fresh exposures.

### 4. Distinct images at the USB3 output

`scripts/measure_output_rate.py` grabs at ~60 fps and counts **distinct-frame
transitions**: a repeated frame is bit-identical, so a change means new content.
This is the only measurement that sees *pictures* rather than *frames*.

Two traps were checked explicitly:

* **Alternation.** A tile flipping between two images (A B A B) gives 30
  transitions/s from 2 pictures. We counted distinct hashes as well as
  transitions: zero revisits, so the transitions are genuinely new images.
* **Static scene.** Sensor noise makes every real frame differ; the free-running
  camera reads 29.83, which confirms the method detects novelty at 30 Hz.

## Corrections from the independent review

`REVIEW_EO_CAM_INPUT_FPS_20261006.md` (2026-10-06 21:00) audited the earlier
handoff against the live board. It confirmed the probe-word packing matches the
decoder, that the six inputs are six distinct decoded BT.1120 V bits, and added
`sim/tb_EoCamFrameRateMon_review.sv`, which drives the unmodified monitor at 30,
25, 20, 15, 0 and 10 events/s and shows 25 Hz decodes as 25 Hz with all six
selector values distinct. That removes the "the mux might be broken" worry in
simulation, though a hardware channel-isolation test is still outstanding.

It also found three errors in the earlier evidence, all accepted here:

1. **The descriptor-epoch cross-check is invalid** (see measurement 3 above).
2. **The "13.8 µs/frame mismatch, so the cameras are not locked" claim does not
   hold.** Consecutive-trigger captures show the interval is not constant: 9672
   ticks in 201 of 256 events, 9643 in 34, mean 33.3329 ms ≈ 30.0004 Hz, which is
   compatible with the cameras' own timing. The earlier sparse sampling
   overrepresented the longer interval. The phase-wrap time quoted with that
   claim was also wrong: a 13.8 µs/frame difference wraps in about 80 s, not the
   2.8 s stated.
3. **The follower-spread summary was wrong twice over** — it used only the low 20
   bits of a 22-bit counter, and it included measurements that had not completed
   (`eo_follow_seen != 31`), where zero means "not finished", not "aligned".
   Re-decoded with all bits and completion filtering: 33.0 ms median in the
   free-run run, 6.0 ms all-trigger, 9.0 ms mixed.

The review's own open question — whether the cameras really carry repeated
content in a 30 Hz stream — is answered by the novelty and SAV/EAV measurements
in this document, which post-date it.

## Open discrepancy — not yet explained

Per-tile novelty in **EO panorama** mode disagrees with single-camera mode:

| tile | mode | panorama | single mode |
|---|---|---|---|
| cam 1 | free-run | 29.91 | 29.83 |
| cam 2 | trigger | **29.91** | **14.98** |
| cam 3 | trigger | **29.91** | **14.98** |
| cam 4 | trigger | 15.00 | 14.97 |
| cam 5 | trigger | 15.00 | — |
| cam 6 | trigger | 15.00 | — |

Cameras 2 and 3 measure 15 distinct images/s on their own but their panorama
tiles update 30 times a second. Both cannot be true of the camera. Either

* the panorama column-to-camera mapping used for the tile bands is wrong (bands
  were taken from `cam_start = [0, 633, 1271, 1909, 2547, 3185]` in the 3840-wide
  logical raster, folded as top = x 0..1919, bottom = x 1920..3839), or
* EO single mode halves the rate for every camera except the strobe master,
  which would make measurement 4's single-mode numbers an output-path artifact.

**This needs resolving before the single-mode numbers are quoted to the vendor.**
The cheap test: put one bottom camera into free-run and see whether its tile
alone goes to 30.

## Mistakes made along the way — recorded so they are not repeated

1. **The first run was free-run and was reported as "what locked cameras look
   like".** The mode was assumed from a label rather than verified, and a
   conclusion was written to fit it. Corrected by the user.
2. **The first measurement counted only frame starts** and was presented as "the
   input frame rate". It cannot see duplicate content — which was the whole
   phenomenon. The user's question "how are you measuring, check SAV/EAV" is
   what exposed this.
3. **Trigger figures were shown against each camera row** in the first Excel
   export; the trigger is one global signal. Fixed in
   `captures/cam_fps/EO_cam_input_fps_corrected.xlsx`.
4. **A trigger-period field read half its true value in free-run.** Explanation:
   the trigger emits pairs of edges ~16.7 ms apart then waits ~50 ms (two edges
   per 66.7 ms = 30/s), and the field reports only the last interval. Inferred,
   not proven. In trigger mode the same field is a clean 33.35 ms. Worth
   understanding: the global frame epoch counts those edges.
5. **The ILA probe was added without regenerating the IP's HDL**, so synthesis
   elaborated against an 11-probe stub and all five placement strategies failed
   for the same reason. `scripts/add_cam_rate_probe.tcl` now resets and
   regenerates the output products and runs `synth_ip`.

## Still unverified

* **The per-camera mux has not been differentiated on hardware.** Simulation now
  covers it (`sim/tb_EoCamFrameRateMon_review.sv`, from the review), but on the
  board all six cameras still report identical values. Power one camera off:
  only that row should go to zero.
* **No testbench for the receiver TRS counters** (lines per frame, F bit) added
  in `9a8a81e`.
* The 60 Hz trigger build advances the global content-frame epoch twice per
  camera frame, so panorama frame-set matching may misbehave in it. Single-camera
  modes are unaffected. `EO_TRIGGER_60HZ = 0` in
  `KintexTop_EO_IR_HD_SDI_panorama_base.v` restores strobe-following.

## What to ask the manufacturer

In trigger mode the camera emits **30 complete 1080p frames per second
(1125 lines, progressive, F steady) but only 15 distinct exposures**, and that
rate is **independent of trigger frequency** — identical at 30 Hz and 60 Hz
trigger, and unchanged by shutter length. Their stated figure is ~25 Hz; we see
a hard 15. What determines the capture rate in triggered mode, and what does the
camera require of the trigger (pulse width, polarity, minimum interval) to
expose once per trigger? Ours is a 2 ms rising-active pulse.

## Suggested next tests

1. **Trigger at 15 Hz.** If the output stays 15, the capture rate is fixed; if it
   halves to 7.5, it does follow the trigger at a 2:1 ratio after all.
2. **Short trigger pulse** (e.g. 100 µs instead of 2 ms) — tests whether the
   camera wants an edge rather than a level. One constant,
   `EO_TRIGGER_PULSE_CYCLES`.
3. **Resolve the panorama/single discrepancy** above before quoting numbers.
