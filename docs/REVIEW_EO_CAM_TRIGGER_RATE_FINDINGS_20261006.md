# Review of the revised EO camera trigger-rate handoff

Date: 2026-10-06, Asia/Seoul. Reviewed repository HEAD `3600f9d` and [HANDOFF_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md](HANDOFF_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md), last modified 22:38 KST. This follows [the earlier independent review](REVIEW_EO_CAM_INPUT_FPS_20261006.md).

## Verdict

**The revised handoff improves the evidence, but its headline and proposed vendor statement still claim more than the measurements establish.** The defensible observation is approximately 15 distinct output states/s in the reported single-camera USB measurements, with 30 raster starts/s at the camera interface. It remains unresolved whether the duplication originates inside the cameras, DDR capture, frame selection, output scheduling, or another downstream stage.

The handoff itself reports cameras 2 and 3 at approximately 30 panorama-tile updates/s but 15 single-camera updates/s. Until that discrepancy is resolved, “every triggered camera supplies only 15 distinct exposures/s” is a hypothesis, not a verified input measurement. The instruction in its discrepancy section to resolve this before quoting numbers to the vendor is sound; the title, headline and vendor paragraph should obey that same qualification.

## What I independently checked now

- Re-decoded the 20 archived ILA captures in `captures/cam_fps/20261006_222052`.
- Connected to the running `xcku15p_0` with the LTX from `builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e`. Vivado matched the live debug probes without mismatch warnings and enumerated two ILAs and one MIG. This is compatible-image evidence, not full bitstream readback authentication.
- Took 14 fresh ILA captures at 23:21:43-23:22:15 KST: [captures/cam_fps/20261006_232142](../captures/cam_fps/20261006_232142/). Every camera was sampled at least once.
- Checked the new receiver counters, both monitor-word layouts, the Python decoders, the trigger selection, and the single-camera DDR/output path.
- Simulated the actual camera-2 receiver RTL against generated TRS sequences, using an identity model of IBUF. Results are below.
- No FPGA programming/reset, camera-setting writes, serial access, or USB-grabber acquisition was performed during this review. The USB novelty measurements in the handoff were not independently rerun.

Both the archived and fresh captures agree:

| Observable | All six cameras / common trigger |
|---|---|
| Decoded V falling edges per window | 30 on each camera |
| Receiver frame-toggle events per window | 30 on each camera |
| EAV codes between frame boundaries | Last/min/max all 1125 |
| Changes in frame-sampled F bit | 0 |
| Common trigger edges per window | 60 |
| Last common-trigger period | 4834 ticks, nominal 16.666721 ms |

These are sampled one-second accumulator results. Frequencies use the nominal 74.25 MHz reference. The archived build reports WNS +0.029 ns and WHS +0.010 ns.

The old epoch-label, sparse-trigger-period and incomplete follower-span corrections are correctly accepted in the new handoff. They should remain withdrawn as evidence for camera novelty or exposure synchronization.

## Findings requiring correction

### 1. The 15 Hz result is measured after the FPGA, not at the camera input

The new SAV/EAV probes inspect timing words. They do not inspect image identity, compare adjacent frame payloads, or count exposure events. Combining 30 timing boundaries at the input with 15 output hashes/s does not locate where the other content updates were lost or repeated.

Single-camera mode is not a raw camera bypass:

- [PanoramaBase_DdrBlackFrame.v](../src/PanoramaBase_DdrBlackFrame.v), lines 2530 onward: it tracks each camera's latest published DDR bank.
- Lines 2584-2591: a descriptor sets `eo_start_pending`; a copy snapshots `cam_last_bank`.
- Lines 1552-1555: copying still depends on `copy_armed || frame_edge`, no active copy, an available output bank, and no backend transition.
- The selected image then passes through `EoV19SingleCamReader`, output copying, scan-out and the capture card.

That path can select, delay or omit input frames. This review does not prove it is causing the observed halving, but it prevents treating the USB measurement as a direct sensor acquisition rate.

Camera 1 is a useful end-to-end 30 Hz control. It is a different camera, with a different phase relative to the rest of the pipeline, from the followers. The table is not a documented free-run/trigger/free-run A/B/A experiment on the same follower camera. Such an experiment would strengthen mode correlation but would still need input-side content measurement to locate the cause.

### 2. “Single-camera modes are unaffected” by the 60 Hz build is unproven

The 60 Hz timer changes `eo_fpga_trigger_common`, which drives both the outgoing trigger and `eo_strobe_ref` into the DDR subsystem. The global epoch therefore changes for the capture writers in single mode too.

Each `u_v19_capN` still consumes `global_epoch_gray_ui` and free-bank tokens from `u_v19_frameset`; the writer's frame admission depends on pending trigger labels and bank availability. The frame-set manager remains enabled by `running` and controls bank return. Single mode bypasses waiting for a six-camera lease at its reader, but it does not bypass these shared capture mechanisms.

Therefore a 30-versus-60 Hz comparison is not a test that changes only the physical camera trigger. A constant approximately 15 Hz USB rate at those two settings neither proves a fixed internal camera limit nor establishes trigger-frequency independence. It would contradict a simple one-new-image-per-two-triggers model only if the measured output were already shown to represent all accepted camera images.

### 3. The panorama/single discrepancy remains material

The nominal start columns `[0,633,1271,1909,2547,3185]` are consistent with this repository's EO layout. Their existence alone does not prove the measured ROIs contained only one camera. The actual ROI script, fold row ranges, seam exclusion, current offsets and captured imagery still matter. The first 17 columns around a join can include a blend of two cameras; physical panorama folding is at row 480, not the midpoint of the 1080-line grabber image.

The handoff's two proposed explanations are not exhaustive. A ROI crossing a seam can change when its neighbor changes; torn or partially updated output, processing changes, or incorrect cropping can produce new hashes without new whole-camera exposures. Conversely, the single-camera path can omit content updates. Hashing an interior patch and validating its physical-camera mapping is necessary before comparing modes.

### 4. “1125 lines = 1080 active + 45 blanking” was not separately measured

The receiver increments its line counter for every decoded EAV. It does not count active and blanking lines separately, count pixels per active line, or validate a complete image payload. F is sampled at the frame event; the monitor counts changes in that sample, not every possible F transition within a raster.

The new test [tb_EoTrsReceiver_review.sv](../sim/tb_EoTrsReceiver_review.sv) uses the actual `Kintex_top_1cam_1ch` RTL and demonstrates:

| Synthetic input | Counter output |
|---|---|
| 1125 total, 1080 active, 45 blanking | 1125, F=0 |
| 1125 total, 1000 active, 125 blanking | Also 1125, F=0 |
| Alternating F across frame boundaries | Receiver exposes the alternating F value |

Thus the captures are good evidence for a stable 1125-line raster with non-alternating frame-sampled F, consistent with progressive 1080p timing. They do not independently prove 1080 active lines or exclude partial/invalid payloads. The two frame counts also share the same camera receiver's TRS/V decode; they check transfer/counting consistency rather than being independent detectors of valid image content.

Simulation passed with Vivado `xvlog -sv`, `xelab --timescale 1ns/1ps` and `xsim -runall`. Log: `sim_out/trs_review_20261006/review_sim.log`. The IBUF identity model and shortened synthetic line length make this a functional counter test, not a physical-interface timing test or a complete six-channel monitor regression.

### 5. The claimed novelty safeguards lack a reproducible evidence trail here

The referenced [measure_output_rate.py](../scripts/measure_output_rate.py) counts adjacent hash transitions and run lengths. It does not itself calculate non-consecutive revisits or the number of distinct hashes. An additional analysis could have done so, but its script/output is not identified in the handoff.

I found the new ILA CSVs, but did not find the corresponding USB per-frame timelines or tile-analysis script in the project's capture directory. Their locations were requested during this review. The approximately 15 Hz output figures are therefore reported observations from the handoff, not independently recomputed results in this review.

Even a valid zero-revisit result proves distinct output pixel states, not one new exposure per state. For example, publishing a partially updated image and then its completed version produces two different hashes from one new source image, with no return to an old hash. Sensor noise on a static scene is helpful for distinguishing repeated digital frames, but cannot by itself eliminate every processing or capture-path confounder.

### 6. “Exposure is ruled out” and the proposed vendor wording are too strong

An unchanged output rate after one reported shutter setting shows only that this intervention did not change the observed output rate. The handoff does not give the decoded shutter time, camera readback, exposure MODE, DSS state, or a complete configuration record. A downstream rate limit could also conceal an input-rate change. This does not rule out all exposure-related behavior.

The quoted approximately 25 Hz vendor claim remains neither confirmed nor disproved by these results. The handoff's proposed statement “only 15 distinct exposures” and “independent of trigger frequency” should be qualified before sending it externally.

Suggested wording:

> With the tested configuration, our FPGA measures 30 raster starts/s and 1125 EAV markers per raster on each input. At the SDI/USB output, single-camera mode reportedly shows approximately 15 distinct pixel states/s for cameras configured for trigger mode, versus approximately 30 for the free-running control. We also observe a mode-dependent discrepancy for cameras 2 and 3 and have not yet isolated whether repetition originates in the camera or FPGA/output path. Which observable and camera configuration does your approximately 25 Hz figure describe?

No message was sent to the manufacturer.

### 7. Existing follower probes reference the unused trigger source in this build

The pulse stretcher now uses `eo_trigger_start_eff`, which selects the local 60 Hz timer. However, the follower-span reset and `eo_follow_probe7` still use `eo_fpga_trigger_start` from the older strobe/fallback source. `eo_trigger_free_running` likewise describes that older source, not the selected 60 Hz generator.

Probe11 remains valid for the common trigger because its monitor input is `eo_fpga_trigger_common`. But do not reuse the previous segmented-capture script that triggers on `eo_fpga_trigger_start` as if it now captured every outgoing 60 Hz event. Do not interpret the existing follower span as phase relative to the selected 60 Hz trigger. This is a new diagnostic mismatch introduced by the trigger override.

## Recommended next step

Resolve the origin of duplication before varying trigger frequency or pulse width again:

1. Recover the hash timelines and ROI script; verify exact physical-camera ROIs away from seams and check the 15-versus-30 discrepancy from the same captured video.
2. Instrument a per-camera payload checksum and monotonically increasing raster sequence at the receiver output, before DDR writer admission. Include active-pixel/line counts so malformed or partial frames are distinguishable. Retain input frame identities through descriptor publication and output bank commit; add true event counters for these stages.
3. Compare input and output identities while one follower is tested in free-run and trigger modes with read-back configuration and a controlled changing optical target. If duplicate content is already present before DDR, investigate camera timing; if the input is novel at 30 Hz and output at 15 Hz, investigate the FPGA path.

No production RTL changes or new firmware deployment were made in this review. The original revised handoff was preserved, and this companion report records the remaining qualifications.
