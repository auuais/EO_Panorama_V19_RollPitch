# Handoff: triggered EO cameras — 30 rasters/s at the input, ~15 distinct images/s at the output

**Date:** 2026-10-06 (revised 2026-10-07 after a second independent review)
**Repo:** `E:\Xylinx\EO_Panorama_V19_RollPitch`
**Reviewed by:** `REVIEW_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md` — its corrections are
folded in below. **Read that file before quoting anything here to the vendor.**
**Supersedes:** `HANDOFF_EO_CAM_INPUT_FPS_REVIEW_20261006.md` (earlier, incomplete
— its conclusion that the modes were indistinguishable came from measuring the
wrong thing; see "Mistakes" below)
**Bitstream for the final measurements:** commit `9a8a81e`, archive
`builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/`

## The manufacturer's claim

The EO camera vendor states:

* **free-run: 30 Hz output**
* **trigger mode: output falls to about 25 Hz, even with a 30 Hz trigger**

**A rate loss is real, but we have not yet established where it happens.** At the
*output* we measure ~15 distinct images/s for triggered cameras against ~30 for
the free-running control. At the *camera input* both modes show 30 complete
rasters/s. The missing updates are therefore lost somewhere between the camera
pin and the capture card, and the camera is only one of the candidates — the DDR
writers, frame-set admission, single-camera reader, output copy and scan-out all
sit in between. Until that is isolated, "the camera exposes only 15 times a
second" is a **hypothesis**, not a measurement.

## Headline findings

1. **Triggered cameras transmit 30 complete rasters per second** (measured at
   the camera pins) **while the output shows ~15 distinct pictures per second.**
   One of the two numbers is not a camera property — see "Where the duplication
   might be" below. The output path is not a bypass.
2. **The free-running camera gives ~30 distinct pictures per second** end to
   end, same cabling, same FPGA build. Camera 1 is free-running and is the
   control in every measurement below. Caveat: it is a *different camera* at a
   different pipeline phase, not an A/B/A on one follower, so mode and camera
   identity are not separated yet.
3. **The rasters are not interlaced or short.** From the cameras' own TRS codes:
   1125 EAV codes per frame, min = max over a one-second window, F never
   changes — consistent with progressive 1080p. The counter counts EAV codes; it
   does not separately verify 1080 *active* lines or a complete pixel payload,
   so a malformed-but-correctly-timed raster is not excluded.
4. **The output rate did not follow the trigger frequency.** At a 60 Hz trigger
   the output stayed at 14.98 distinct images/s. This weakens
   "one exposure per two triggers", but it is **not** a clean single-variable
   test: the same 60 Hz timer also drives `eo_strobe_ref` and the global frame
   epoch, so the capture side changed too.
5. **One shutter setting did not change the rate.** Shutter 12 gave 14.98,
   unchanged. That rules out *that* intervention, not exposure in general — a
   downstream rate cap would mask an input-rate change, and we have no decoded
   shutter time or camera read-back.

### The numbers

Single-camera mode, USB3 grabber, 8 s per camera, 60 Hz grab rate. These are
**output** figures, measured after the whole FPGA path:

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

From the cameras' TRS codes, all six identical (confirmed independently in the
second review, both from our archive and from 14 fresh captures):

| frames/s (TRS) | VSYNC/s | lines per frame | F changes/s |
|---|---|---|---|
| 30 | 30 | 1125 (min = max) | 0 |

## Where the duplication might be — the open question

The 15 Hz number is measured at the USB3 output, which is downstream of:

* `u_v19_capN` DDR writers — admission depends on pending trigger labels and a
  free bank token from `u_v19_frameset`; single mode does **not** bypass this;
* the published-bank tracking in `PanoramaBase_DdrBlackFrame.v` (~line 2530) and
  the copy arming at lines 1552-1555 (`copy_armed || frame_edge`, no active
  copy, an output bank free, no backend transition);
* `EoV19SingleCamReader`, the output copy, scan-out, and the capture card.

Any of these can repeat, delay or drop a frame. Nothing here says they do — only
that the measurement cannot distinguish them from the camera. The decisive
instrumentation is a **per-camera payload checksum plus a monotonic raster
sequence number at the receiver output, before DDR admission**, carried through
descriptor publication and output bank commit. If duplicate content is already
present before DDR, it is the camera; if the input is novel at 30 Hz and the
output is 15 Hz, it is ours.

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

Two limits of this measurement, raised by the second review and accepted:
`scripts/measure_output_rate.py` itself counts adjacent transitions and run
lengths — the distinct-hash/revisit analysis was done separately and its script
and per-frame timelines are **not archived**, so the 15/30 figures are reported
observations here, not reproducible artefacts. And even zero revisits proves
distinct pixel states, not one new exposure each: publishing a partially updated
frame and then its completed version yields two hashes from one exposure.

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
tiles update 30 times a second. Both cannot be true of the camera. Candidates,
not exhaustive:

* the panorama column-to-camera mapping used for the tile bands is wrong (bands
  were taken from `cam_start = [0, 633, 1271, 1909, 2547, 3185]` in the 3840-wide
  logical raster, folded as top = x 0..1919, bottom = x 1920..3839). The layout
  constants are right for this repo, but that does not prove the sampled ROIs
  held one camera each: the physical fold is at **row 480**, not the midpoint of
  the 1080-line grabber image, and the 17-column seams blend two cameras, so an
  ROI near a join changes when its *neighbour* changes;
* EO single mode halves the rate for every camera except the strobe master,
  which would make measurement 4's single-mode numbers an output-path artifact;
* torn or partially updated output, or cropping that lands across a seam,
  producing new hashes without new whole-camera exposures.

The fix for the mapping doubt is cheap: hash an **interior** patch well away
from every seam and fold row, and validate its camera identity (e.g. by covering
one lens) before comparing modes.

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
  camera frame, so panorama frame-set matching may misbehave in it. **Single
  modes are not exempt**, contrary to what this document first said: the same
  timer feeds `eo_strobe_ref` and the global epoch, which gate the per-camera
  DDR writers in every mode. So the 30-vs-60 Hz comparison changed the capture
  side as well as the camera trigger. `EO_TRIGGER_60HZ = 0` in
  `KintexTop_EO_IR_HD_SDI_panorama_base.v` restores strobe-following.
* **Diagnostic mismatch introduced by the 60 Hz override.** The pulse stretcher
  now uses `eo_trigger_start_eff`, but the follower-span reset, `eo_follow_probe7`
  and `eo_trigger_free_running` still reference `eo_fpga_trigger_start` — the
  *unused* strobe/fallback source. Do not read the follower span as phase
  against the 60 Hz trigger, and do not reuse the old segmented-capture script
  as if it triggered on every outgoing edge. Probe11 is unaffected: its monitor
  input is `eo_fpga_trigger_common`.
* **No receiver-side content measurement at all.** Checksums and raster sequence
  numbers before DDR admission are the missing instrument (see "Where the
  duplication might be").

## What to ask the manufacturer

**Do not send the earlier draft** ("only 15 distinct exposures", "independent of
trigger frequency"). Both overstate what is measured. Wording that holds:

> With the tested configuration, our FPGA measures 30 raster starts/s and 1125
> EAV markers per raster on each input. At the SDI/USB output, single-camera
> mode shows approximately 15 distinct pixel states/s for cameras configured for
> trigger mode, versus approximately 30 for the free-running control. We also
> observe a mode-dependent discrepancy for cameras 2 and 3, and we have not yet
> isolated whether the repetition originates in the camera or in our FPGA/output
> path. Which observable and camera configuration does your approximately 25 Hz
> figure describe?

Also worth asking regardless of the outcome: what the camera requires of the
trigger (pulse width, polarity, minimum interval) to expose once per trigger.
Ours is a 2 ms rising-active pulse. Nothing has been sent to the vendor yet.

## Suggested next tests — in this order

Locate the duplication **before** varying the trigger again; with the origin
unknown, every trigger experiment measures the whole chain.

1. **Recover and archive the hash timelines and ROI script**, re-hash interior
   patches with verified camera identity, and settle the 15-vs-30 discrepancy
   from one captured video.
2. **Instrument the receiver output**: per-camera payload checksum, monotonic
   raster sequence, active-pixel/line counts, carried through descriptor
   publication and output bank commit, with real event counters at each stage.
   This is the one test that separates camera from FPGA.
3. **A/B/A on one follower** — free-run, trigger, free-run — with configuration
   read-back and a controlled moving target, comparing input *and* output
   identity.
4. Then, if still needed: **trigger at 15 Hz** (fixed rate vs 2:1 ratio) and a
   **short trigger pulse** (100 µs vs 2 ms, via `EO_TRIGGER_PULSE_CYCLES`) —
   with `EO_TRIGGER_60HZ = 0` restored so the epoch is not a second variable.
5. **Power one camera off** and confirm only that row of the monitor goes to
   zero — still the outstanding proof that the per-camera mux works on hardware.
