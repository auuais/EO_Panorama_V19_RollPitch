"""Archive the completed DNR experiment and its exact provenance for Git tracking."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'captures/eo_dnr_cam2_20261009'
SCRATCH=Path(__file__).resolve().parent
DEST=ROOT/'docs/eo_sync_evidence/dnr_cam2_20261009'
if DEST.exists():
    raise FileExistsError(DEST)
restoration=json.loads((SOURCE/'restoration_verified.json').read_text(encoding='utf-8'))
assert restoration['all_readbacks_verified'] and restoration['display_matches_initial'] and restoration['pose_matches_initial']
DEST.mkdir(parents=True)
for path in SOURCE.rglob('*'):
    if path.is_file():
        target=DEST/path.relative_to(SOURCE)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
for path in SCRATCH.iterdir():
    if path.is_file() and path.suffix in ['.py','.log']:
        target=DEST/('scripts' if path.suffix=='.py' else 'logs')/path.name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
data=json.loads((SOURCE/'comparison.json').read_text(encoding='utf-8'))
c=data['conditions']
rows=[]
for label in ['on_a','off_b','on_return']:
    r=c[label]['camera2']
    rows.append(f"| {label} | {r['duration_s']:.3f} | {r['records']} | {r['raster_hz']:.6f} | {r['full_changes']} | {r['full_change_interval_hz']:.6f} |")
text='''# Camera 2 DNR OFF comparison — 9 October 2026

No substantial change in measured input raster timing or image-update cadence was found when DNR was disabled on physical camera 2. Per the request, testing was not expanded to disabling DNR on all five cameras and the Excel workbook was left unchanged.

## Settings and scope

Camera 2: 1080p60, 1/60 s shutter, 0 dB gain, external trigger, ExtTrig Delay 0.0 ms. The r4 diagnostic generated 30 Hz triggers with a 2 ms high time. DNR was changed from 2D+3D to OFF and back to 2D+3D, with Freeze OFF for the three live captures. Camera 3 was an unchanged raster-timing reference. Cameras 3–6 were temporarily changed to 1080p60 for diagnostic clock locks; their exposure and DNR settings were not changed.

All measurements use rising-edge samples at taps 336:280:308:280:322, common nominal 27 MHz timestamps, and the same bitstream. Exact build hashes are in build_sha256.json. Camera settings were read directly from ILA OSD crops. No standard eo_video_mode.py --select command, OSD SAVE/DFLT, or FPGA configuration-flash programming was used. The restoration-only route request is described below.

## Results

| Condition | Measured live time (s) | Valid cam2 rasters | Raster/s | Full-image CRC changes | Image-change cadence/s |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(rows)+'''

All observed successive full-image and central-region image changes were separated by exactly two rasters. The cadence column is computed from adjacent change-event intervals; comparison.json also retains changes/count-window rates, whose small deviations around 30 reflect finite-window endpoints. Capture gaps are excluded, and no transitions are inferred across them.

Camera 2 had 100% valid 1920×1080 geometry and no sequence gaps in all live and frozen captures. Freeze controls passed independently in both DNR states: ON had 1,746 valid rasters over 29.084 s and OFF had 1,749 over 29.134 s, with zero full-image and zero central-region CRC changes in either control. Telemetry signature, valid-bit and overrun checks passed for all stored events. Phase locks/taps/busy/faults were checked before and after captures.

The fitted relative raster drift (camera 2 minus camera 3) was −4.74956 µs/s. Against the bracketing ON linear drift fit, the OFF raster residual had median +3.098 µs and range +2.247 to +3.477 µs. The OFF full-image/ROI change phase relative to the trigger had median +3.943 µs and range +2.996 to +4.274 µs against its bracketing ON fit. These microsecond residuals are not evidence of a large DNR effect. Clock drift was slightly nonlinear: extrapolating only the initial ON image-change fit to the returning ON capture gives −17.47 µs median residual. Consequently, the small residual cannot be assigned causally to DNR, and “no difference” here means no substantial change detectable in this experiment.

These are received-raster and qualified digital image-change measurements. They do not directly measure physical exposure synchronization or end-to-end latency; a whole frame of internal buffering can preserve output cadence and modulo-trigger phase. This single-camera result is not a measurement of all five cameras with DNR OFF.

## Restoration and unchanged report

Direct ILA OSD readbacks confirmed cameras 2–6 back at 1080p30 and camera 2 back at 1/240 s, 0 dB, DNR 2D+3D, Freeze OFF, external trigger and 0.0 ms trigger delay. The original operational FPGA image was reloaded. Read-only USB display/parameter and pose reads exactly matched their starting values. See restoration_verified.json and restored_* folders.

FPGA reconfiguration resets its local mode register while the MCU still remembers EO camera 6. This caused the incomplete boot/default view recorded in final_closed.png. A custom mode-only 0x2203 request (06 FF FF FF FF FF FF FF) restored EO6 routing. The ancillary fields exceed the inspected firmware's checked ranges, so its handler skips their camera/display parameter writes. This is specific to the inspected firmware, not a general protocol no-change sentinel. Source path/hash, payload, ACK and unchanged before/after controller parameters are recorded in restore_route_only.json. The same MCU mode was persisted once to MCU mode flash; FPGA configuration flash was not programmed. The restored full camera-6 scene was directly verified in final_route_restored.png. Fresh post-route display/pose readbacks still match the initial values.

The latest workbook EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx was not edited; SHA-256 remains cd7dc5ae1e5fc248c90c3675ba9eb918822012ee6fe68619acfecc752879a036.

## Reproduce analysis

From this repository, run the bundled Python interpreter with `-X utf8` and `scripts/analyze.py <this evidence directory>`. The analyzer imports diagnostics/eo_sync/scripts/decode_events.py from the repository and regenerates comparison.json and camera2_relative_phase.csv from the raw event CSVs. bench.py and its durable logs document the original hardware sequence; do not run hardware stages without checking the actual starting camera state.

Raw OSD snapshot CSVs, reconstructed PNGs, serial key logs, event CSVs, phase checks, build hashes, comparison data, and restoration evidence are included. No confidential manufacturer manual/PDF is included. manifest.json records SHA-256 and size for every other archived file.
'''
(DEST/'README.md').write_text(text,encoding='utf-8')
entries=[]
for path in sorted(DEST.rglob('*')):
    if path.is_file():
        entries.append(dict(path=path.relative_to(DEST).as_posix(),size=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(DEST/'manifest.json').write_text(json.dumps(dict(created_at=datetime.now().astimezone().isoformat(),
    files=entries,total_bytes=sum(e['size'] for e in entries)),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(archive=str(DEST),files=len(entries),bytes=sum(e['size'] for e in entries))))
