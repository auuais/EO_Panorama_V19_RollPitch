# Independent review of EO camera input FPS and live FPGA ILA

Reviewed 2026-10-06, Asia/Seoul. Live captures: 20:52-20:53 and 20:57 KST.

The requested handoff was found in this RollPitch repository, not in the supplied M1 path. Source handoff: [HANDOFF_EO_CAM_INPUT_FPS_REVIEW_20261006.md](HANDOFF_EO_CAM_INPUT_FPS_REVIEW_20261006.md). The user confirmed camera 1 free-run and cameras 2-6 trigger mode during this review. That is user-confirmed configuration; camera OSD readback was not performed.

## Verdict

**The running FPGA reports 30 BT.1120 vertical-blanking transitions per second on each of six camera channels. The handoff's conclusion that this disproves 25 fresh images/s, or proves the cameras ignore exposure triggers, is not justified.**

Three consequential errors were found:

1. Descriptor epochs are trigger-derived labels that can skip values, not independent frame counters. Their slope cannot establish camera frame rate.
2. The reported 13.8 us/frame trigger mismatch compares a common individual interval with camera timing, rather than comparing average periods. Consecutive live trigger captures show regular shorter intervals that compensate for the longer ones; the mean is about 33.333 ms.
3. The follower-spread analysis includes unfinished measurements and appears to omit upper span bits in the first run. Its zero medians and maximum near 9 ms are not reliable summaries of the archived evidence.

The RTL packing, Python field extraction, and six separate input connections check out. An RTL simulation now demonstrates that 25 Hz is decoded as 25 Hz and that all six mux selections are distinct. A physical one-camera perturbation test is still unperformed.

## Hardware provenance and actions

- Connected through JTAG to `xcku15p_0`, cable `00001bd45a2c01`, with Vivado 2025.2.
- Running device enumerated two ILAs and one MIG. The archived LTX matched the live debug cores without mismatch warnings.
- Rate ILA: `u_top_hd_mux_ila`, UUID `819C12171EDC5568ADB41A73EF8C2D75`, 8192 samples maximum.
- DDR ILA: `u_ddr_black_frame/u_dbg_ila_0`, UUID `7A9C4629CC9A569688AA469E26300B84`.
- Used `builds/bit_archive/20261006_150257_camratemon_bd9af71/KintexTop_EO_IR_HD_SDI_panorama_base.ltx`. Its SHA-256 matches the current implementation LTX: `5243b0c66ec584973a9f7b2ff8a6ce91850eae2be3c9d5726284eff66f9977e9`.
- The relevant monitor, top-level, trigger-source and writer RTL have no diff against `bd9af71`. The decoder was added subsequently.
- The archive's programming log identifies that bitstream; compatible live debug UUIDs support that provenance. This review did not perform bitstream readback or independently authenticate the entire programmed image.
- The archived successful timing run reports WNS +0.111 ns, WHS +0.010 ns, no setup/hold total violations.
- No FPGA programming/reset, camera-setting writes, serial-port access or SDI-grabber access was performed. Only ILA capture settings were changed. The segmented capture script restored its saved ILA settings on successful completion.
- Production RTL and the original handoff were left unchanged. Existing XPR/XDC working-tree modifications were already present.

Raw evidence: [captures/cam_fps_review/20261006_205147](../captures/cam_fps_review/20261006_205147/). Hardware properties, capture timestamps, CSVs, JSON analysis and simulation counterexample output are retained there.

## Fresh measurements

Twenty-four immediate captures used varying delays to avoid sampling only one selector parity. Each capture contained 8192 consecutive hd_clk samples, approximately 110.3 us. Every capture had one stable rate word. These are snapshots of accumulated one-second statistics, not continuous recordings of every intervening second.

| Physical camera | Captures | VSYNC falls/window | Min/max interval, ticks |
|---|---:|---:|---|
| 1 | 4 | 30 | 9668 / 9669 |
| 2 | 4 | 30 | 9668 / 9669 |
| 3 | 4 | 30 | 9668 / 9669 |
| 4 | 4 | 30 | 9668 / 9669 |
| 5 | 5 | 30 | 9668 / 9669 |
| 6 | 3 | 30 | 9668 / 9669 |

At nominal hd_clk = 74.25 MHz, one tick is 3.447811 us. The measured period fields translate to 33.333441-33.336889 ms. The window is 74,249,984 clock cycles, or 0.9999997845 nominal seconds. Absolute frequencies inherit the board oscillator's unmeasured tolerance; that does not plausibly account for a 25-versus-30 difference.

The trigger count was 30 in all 24 snapshots. `eo_trigger_free_running` was zero throughout those captured samples. The RTL source follows camera 1's STROBE in that state; this says nothing by itself about follower cameras accepting the outgoing pulses.

### Consecutive trigger intervals disprove the fixed-mismatch premise

The existing ILA supports segmented capture. Four acquisitions each recorded 64 consecutive `eo_fpga_trigger_start` events, 128 samples per event. Each segment starts with that one-cycle pulse asserted; the rate word is decoded at sample 32, after its trigger-period pipeline has updated.

| Interval field | Nominal interval | Occurrences among 256 |
|---:|---:|---:|
| 9642 | 33.243798 ms | 2 |
| 9643 | 33.247246 ms | 34 |
| 9671 | 33.343785 ms | 19 |
| 9672 | 33.347232 ms | 201 |

Mean encoded interval: **33.332889 ms**, reciprocal approximately **30.0004 Hz**. Treat the last digits as quantized diagnostic arithmetic, not calibrated frequency accuracy. Each 64-event sequence contains periodic shorter intervals, roughly one in seven. All 256 sampled events show `free_running=0`.

Consequently, using 33.3473 ms as a constant trigger period is incorrect in the current confirmed mixed configuration. The prior sparse samples overrepresented that longer interval. The mean is compatible with 30 Hz camera timing; the claimed fixed 414 ppm mismatch is not established. These captures do not retrospectively prove the exact sequence in the earlier all-trigger run.

Even if a fixed 13.8 us/frame mismatch existed, a full 33.3 ms phase wrap would take about 2415 frames, or **80.5 seconds**, not 2.8 seconds as proposed in the handoff.

## Audit of the four handoff questions

### 1. Does the field layout match the decoder?

Yes. [EoCamFrameRateMon.v](../src/EoCamFrameRateMon.v) packs 2+6+14+3+8+15+15+1 = 64 bits. [decode_cam_fps.py](../scripts/decode_cam_fps.py) extracts exactly those bit ranges, with hexadecimal parsing. The selector is bits 41:39; there is no one-bit shift.

[tb_EoCamFrameRateMon_review.sv](../sim/tb_EoCamFrameRateMon_review.sv) runs the unmodified monitor RTL with the same 256-cycle divider and an accelerated nominal clock parameter. Six inputs are independently driven at 30, 25, 20, 15, 0 and 10 events/s. It checks counts, interval bounds, all selector values and packed output over eight windows. Vivado xsim passes. The production Python decoder also recovers all six IDs and expected rates from the simulation's exported words.

This rules out a basic counter/mux/bit-extraction explanation for 25 Hz becoming 30 Hz under the tested stimuli. It does not replace a hardware channel-isolation test. The historical mixed run samples only cameras 2, 4, 5 and 6, so the handoff's table should not say every camera was measured in that run. The fresh run covers all six.

### 2. Are these six actual camera VSYNC inputs?

They are six distinct **decoded BT.1120 V bits**, not dedicated VSYNC pins or sensor exposure signals. The top level connects `{eo5_vsync,...,eo0_vsync}` to the monitor. Each `Kintex_top_Ncam_1ch` receiver consumes its own `CAMN_PCLK` and `CAMN_YOUT`; it recognizes `FF 00 00` timing prefixes and copies bit 5 of the next word into its VSYNC register. For example, see [Kintex_top_1cam_ch1_1202.v](../src/Kintex_top_1cam_ch1_1202.v). Camera 0 uses [KintexTop_0cam_ch1_0108.v](../src/KintexTop_0cam_ch1_0108.v).

On valid progressive BT.1120 video, a falling V transition identifies leaving vertical blanking. The approval sheet specifies progressive scan. There is no downstream replay, output-rate conversion or synthetic VSYNC generator in this measurement path. However, this monitor does not validate active-pixel geometry, timing-word parity, or uniqueness of the image payload. Therefore “30 decoded raster starts/s” is the strongest direct claim.

### 3. Can 25 fresh images/s coexist with these 30 readings?

Yes, as a possible camera-side behavior: 25 new exposures/images could be carried in a continuously timed 30 Hz video stream through repeated or held image content. That would produce 30 V transitions and could also write 30 rasters into DDR. This review does **not** establish that these cameras actually do that.

The supposedly independent epoch check is additionally invalid even as a DDR frame-count measurement:

- [PanoramaBase_DdrBlackFrame.v](../src/PanoramaBase_DdrBlackFrame.v), lines 479-490: `v19_global_epoch` advances on `eo_strobe_edge_ui`.
- [EoV19DdrDesync.v](../src/EoV19DdrDesync.v), lines 226-259: a camera's `frame_epoch_next` is derived from that global trigger count and pending-trigger occupancy.
- Lines 392-413: when behind, the writer consumes two pending trigger labels per raster to catch up.
- Lines 464-473 and 681: the chosen label crosses the FIFO and is copied to `desc_epoch_ui`. There is no `desc_epoch_ui += 1 per published frame` rule.

Eight fresh DDR snapshots reproduce label slopes of 29.64-30.26 labels/s on cameras 1 and 5. They do not validate an independent frame rate. A reproducible counterexample, using the repository's existing model of these same equations, supplies 30 triggers/s and 25 rasters/s: **25.0 actual frames/s yields about 30.025 labels/s** over the selected finite interval. Labels skip, e.g. `1,2,3,5,6,...`.

Use a dedicated counter incremented on each `desc_valid_ui` pulse for DDR frame rate. Even that counts captured rasters, not fresh camera exposures.

### 4. Does the period difference prove the cameras are not locked?

No. The current consecutive captures invalidate the fixed-period comparison, as detailed above. More generally, output-raster phase/frequency and sensor exposure timing are different observables. Prior project documentation records a manufacturer statement that BT.1120 outputs are not synchronized; see [HANDOFF_PANORAMA_MOTION_ARTIFACT_REANALYSIS_20260805.md](HANDOFF_PANORAMA_MOTION_ARTIFACT_REANALYSIS_20260805.md), section 5.4. That is a historical project record, not newly authenticated vendor correspondence.

Stable per-camera period minima/maxima also cannot distinguish stable independent oscillators from trigger locking. A phase measurement would characterize raster timing relative to triggers, but would not, by itself, establish whether exposures are triggered.

## Other corrections

### Follower spread requires completion qualification and all 22 bits

The top level clears `eo_follow_span_cycles` at every trigger, sets it to zero for the first follower event, and updates it as later followers arrive. It is a final five-follower spread only when `eo_follow_seen=31` and `eo_follow_wait=0` (or at the completion pulse). Zero during an unfinished measurement does not mean aligned cameras.

Re-decoding the first valid sample in every historical CSV, combining bits 21:20 with bits 19:0, gives:

| Run | Complete snapshots / total | Median completed spread | Completed range |
|---|---:|---:|---:|
| 20:01, free-run label | 3 / 14 | 33.012 ms | 33.010-33.016 ms |
| 20:21, all-trigger label | 7 / 20 | 5.986 ms | 5.942-6.015 ms |
| 20:40, mixed label | 11 / 20 | 8.977 ms | 8.910-9.008 ms |
| Fresh 20:52 mixed run | 9 / 24 | 10.726 ms | 10.698-10.779 ms |

The first run's full-width completed spread reaches 33 ms. Taking only the low 20 bits wraps every 14.1229 ms and can turn that into a much smaller number. Circular phase ordering can also make a cluster straddling a trigger look nearly one frame wide. These summaries should not be treated as direct exposure-skew measurements.

### The fallback flag was already available

`eo_trigger_free_running` is bit 0 of `eo_follow_probe7`, and is named explicitly in all these CSVs. The archived all-trigger run has it set in all 20 snapshots; the mixed run has it clear in all 20; the original free-run run has 13 clear and one set. Thus the all-trigger run was sampling fallback operation at those times. The flag does not say that the follower cameras themselves are free-running.

The sticky `strobe_seen` flag is not exposed by name, but adding it is not necessary to observe the already-probed fallback flag. The suspected pair/long-gap behavior in the first run is not proven by sparse last-interval snapshots. Those snapshots contain 4813, 4841, 4842 and 14502 ticks, not thirteen identical 16.69 ms observations.

### Small real monitor limitations

- A camera or trigger edge coincident with `win_end` is dropped from the window counts: later nonblocking assignments overwrite its increment and latch the old count. The RTL test explicitly reproduces this. It biases a count downward; it cannot explain a stable 25-to-30 overcount.
- The period reset takes priority over a simultaneous tick. Integer-tick measurements can consequently undercount an interval by a tick; this matters for precise ppm comparisons, not 25-versus-30 Hz.
- The trigger's internal 15-bit saturating interval is exported as only 14 bits. Values at or above 16384 ticks (about 56.49 ms) wrap in the exported field. The six-bit trigger count also truncates above 63. The current approximately 33 ms observations are within range.
- Period extrema are reset each window and the first crossing interval is deliberately omitted. Long missing-frame intervals, startup and saturation need explicit validity handling before broader use.
- RTL comments claiming 3.4512 us/tick and 9651 ticks at 33.3 ms are numerically wrong; the decoder's conversion is correct. Comments saying period spread separates free-run from genlock are also too strong.

## Manufacturer evidence and remaining decisive test

The local approval sheet was inspected, including the rendered trigger timing diagram: `C:/SVNProjects/IMU_Stabilize_v40/Manual/EO/원우Approval sheet _DM-G15-42_v1.04_240104.pdf`.

- PDF page 40 (printed 39): trigger configuration requires exposure MODE=MANUAL.
- PDF page 42 (printed 41): the external-trigger diagram relates the active trigger edge to an exposure start, image data and configurable strobe timing. It supplies no measured 30-trigger-to-25-fresh-image throughput result.
- PDF page 51 (printed 50): 30/60 and 25/50 are selectable NTSC/PAL format families.
- The [manufacturer's public product page](https://www.wonwoo.com/kr/product/product_view.php?idx=188&part1_idx=&part2_idx=15&part3_idx=) lists output formats and external trigger/strobe support. It does not state the quoted 25 Hz trigger-mode limit.

The exact vendor communication behind the handoff's 25 Hz claim was not supplied. Its meaning could be raster rate, new-image rate, accepted-exposure rate, or a particular configuration limit. The current evidence cannot choose among these.

The useful next experiment is to verify one follower's actual MANUAL/ExtTrig/polarity/delay settings, then measure **new exposure or image identity** against trigger events: preferably a camera-provided exposure strobe or frame ID, or a controlled changing optical time code observed at the camera input. Record raster starts and a true completed-frame counter separately. Per-input frame checksums can help detect exact duplicates, but noise/ISP processing and a static scene can make simple pixel-difference tests ambiguous. The rendered panorama/SDI output alone introduces downstream frame repetition/drop as another confounder.

A temporary one-camera rate change or power-off can additionally validate physical channel isolation. That requires user action and was not done here. A phase-only firmware rebuild should not be the first step toward resolving the 25-fresh-images question.

## Reproduction and added artifacts

- [review_cam_fps_live.tcl](../scripts/review_cam_fps_live.tcl): captures rate words, existing fallback flag, DDR labels and hardware/timestamp metadata without programming.
- [review_cam_trigger_intervals.tcl](../scripts/review_cam_trigger_intervals.tcl): four segmented acquisitions of 64 consecutive trigger events; currently saves into this review's evidence directory.
- [review_cam_fps_analysis.py](../scripts/review_cam_fps_analysis.py): preserves per-capture values, checks complete follower spreads and summarizes segmented trigger intervals.
- [tb_EoCamFrameRateMon_review.sv](../sim/tb_EoCamFrameRateMon_review.sv): real-RTL simulation for distinct rates, absent channel, packing and boundary collision.
- [review_cam_fps_counterexamples.py](../scripts/review_cam_fps_counterexamples.py): verifies the production decoder against simulation words and demonstrates the epoch-label counterexample. The epoch portion is a logic model, not a full DDR simulation.
- [review_analysis.json](../captures/cam_fps_review/20261006_205147/review_analysis.json): historical and fresh capture summaries plus the 256 trigger intervals.
- Simulation results: `sim_out/cam_fps_review_20261006/review_sim.log`, `sim_words.csv`; counterexample results: `captures/cam_fps_review/20261006_205147/counterexamples.txt`.

Simulation was compiled with Vivado `xvlog -sv` and `xelab`, then run with `xsim -runall`. No firmware rebuild or deployment is part of this review.
