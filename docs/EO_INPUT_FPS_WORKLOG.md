# EO input FPS investigation: checkpoints and next work

Updated 8 October 2026 (Asia/Seoul).

Repository: `https://github.com/auuais/EO_Panorama_V19_RollPitch`.
Working branch: `codex/eo-input-fps-verification`, based on `e462da6`.

The user requested continued commits, tracking and GitHub pushes. Make focused
commits at completed, validated checkpoints and push this branch after each
checkpoint. Record measured results and remaining limitations here. This is a
development workflow, not a scheduled background task.

First pushed checkpoint: `e82f566` — EO input FPS diagnostics and reproducible
capture tests. The following report checkpoint adds the corrected verdict,
compact evidence, workbook and this work log; use Git history for its hash.

## Completed

- Added passive input-content RTL, USB/ILA acquisition tools, decoding and
  synthetic regression checks for the original 1080p30 investigation.
- Built separate 1080p60 input diagnostics with both sampling phases and then
  a two-frame, decimated-luminance snapshot ILA for direct OSD review.
- Read the supplied EO manuals and completed eight new verification conditions
  with a generated 60 Hz trigger. Direct OSD shows 1/30 s at 1080p30 becoming
  1/60 s at 1080p60 without an intervening shutter command.
- With camera Freeze ON, the original r2 diagnostic reported 248/248 changed
  full and ROI CRC pairs. Its previous 60 fresh-FPS conclusion is withdrawn.
- Approximately 60 rasters/s is confirmed. The new build observes about 30 ROI
  changes/s at directly read 1/60 s, but its full CRC also fails the 60-mode
  Freeze control. Whole-frame fresh FPS remains unverified.
- Updated the consolidated workbook, preserving historical raw counts and
  marking the previous 60 fresh-FPS estimates unverified. The workbook contains
  three direct OSD images and the new control results.
- Restored and verified the operational FPGA, camera 2 at 1080p30 / ExtTrig /
  1/240 s / 0 dB / DNR 2D+3D / Freeze OFF, display camera 6 and unchanged pose
  parameters. No QSPI write, MCU flash, camera power cycle or OSD SAVE was used.

The full narrative is [TEST_EO_CAMERA_CONTENT_20261007.md](TEST_EO_CAMERA_CONTENT_20261007.md).
The current report and compact measured evidence are in
[eo_fps_evidence](eo_fps_evidence/README.md). Raw captures and complete builds
remain local under the repository's existing capture policy; they are not
included in the GitHub evidence bundle.

## Next: qualify EO single output through USB3 at 1080p60

This work has been assessed but the video-output RTL has **not** been built yet.
The operational EO single path goes through DDR and uses a 74.25 MHz output
clock with 2200 x 1125 timing: 30 rasters/s. The earlier camera-format switch
produced black USB video. The dedicated ILA diagnostics have no video output.
Receiving 60 USB buffers/s from the existing output is not proof of 60 distinct
source frames.

1. Establish a properly timed 1080p60 video output, including downstream SDI and
   USB capture support. Keep camera input integrity and output-rate conversion
   separate in the measurements.
2. Send an independently numbered 60 Hz test pattern to USB3. Record every
   received frame and count missing/repeated sequence numbers before relying
   on the capture chain for camera-FPS conclusions.
3. Feed camera 2 through the qualified single-camera path. Verify format and
   shutter directly, perform Freeze controls, then record unfrozen images and
   compare consecutive frames with a timed optical scene.
4. Update the report with distinct raster, received-buffer, changed-image and
   physical-exposure claims. Actual integration time needs a separate optical
   or validated exposure-timing measurement.

## Scope of this checkpoint

The existing local modifications to `EO_Panorama_V19_M1.xpr` and
`ip/ddr4_sub64/ddr4_sub64_board.xdc` are not part of these commits. The unrelated
bandwidth JSON files and offset-setting helper remain local as well.
Diagnostic source packages are reproducible standalone projects and do not
require committing the generated Vivado project or bitstream.
