"""Archive completed all-five DNR test, report provenance and exact evidence bytes."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch');SOURCE=ROOT/'captures/eo_dnr_all5_20261009';SCRATCH=ROOT/'.tmpCRC/eo_dnr_all5_20261009';DEST=ROOT/'docs/eo_sync_evidence/dnr_all5_20261009'
restored=json.loads((SOURCE/'restored_state_verified.json').read_text());assert restored['all_camera_readbacks_verified'] and restored['display_matches_initial'] and restored['pose_matches_initial'] and restored['usb_scene_verified']
validation=json.loads((SCRATCH/'saved_workbook_validation.json').read_text());assert validation['all_new_formulas_and_caches_verified'] and not validation['formula_errors'] and not validation['unintended_style_changes']
assert not DEST.exists();DEST.mkdir(parents=True)
for f in SOURCE.rglob('*'):
 if f.is_file():
  d=DEST/f.relative_to(SOURCE);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
for f in SCRATCH.iterdir():
 if f.is_file() and (f.suffix in ['.py','.mjs','.log'] or f.name in ['report_validation.json','saved_workbook_validation.json','report_error_scan.ndjson','report_before.xlsx']):
  d=DEST/('scripts' if f.suffix in ['.py','.mjs'] else 'logs' if f.suffix=='.log' else 'report_provenance')/f.name
  d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
study=json.loads((SOURCE/'study.json').read_text());labels={'on_a':'ON initial','off_b':'OFF','on_return':'ON restored','off_repeat':'OFF repeat'}
text=['# All-five camera DNR OFF synchronization comparison — 9 October 2026','',
'Physical cameras 2–6 were tested in 1080p60 at 1/60 s, 0 dB, external-trigger mode and 0.0 ms external-trigger delay. The same r4 diagnostic and rising sampling taps 336:280:308:280:322 were used throughout. The common nominal timestamp clock is 27 MHz. Every block verified 30 Hz triggers and 2 ms high time. All camera settings were directly read from reconstructed ILA OSD crops. Camera 1 received no setting commands.','',
'Protocol: all-five ON frozen control; unfreeze; ON live; all-five DNR OFF live; all-five DNR ON return live; repeat all-five OFF live; all-five OFF frozen control; restoration. There was no Freeze intervention between the four live conditions. Each live condition contains two blocks totaling approximately 58 seconds; upload gaps are excluded. Only DNR was changed between the live conditions. The OFF repeat was added because the ROI spread did not return to its initial ON value.','',
'## Actual five-camera input raster spread','',
'Spread is the shortest circular arc containing the five nearest raster phases. It describes received input alignment, not identification of the same physical exposure. Values below are milliseconds, not clock-drift residuals.','',
'| All-five DNR | Observed s | Matched sets | Minimum ms | Median ms | P95 ms | Maximum ms |','|---|---:|---:|---:|---:|---:|---:|']
for k,label in labels.items():
 c=study['conditions'][k];s=c['spreads_us']['raster'];text.append(f"| {label} | {c['observed_s']:.3f} | {s['n']} | {s['min']/1000:.6f} | {s['median']/1000:.6f} | {s['p95']/1000:.6f} | {s['max']/1000:.6f} |")
text+=['','## Camera-2/camera-3 comparison within this test','',
'Both cameras now have verified 1/60 s shutters. Pair spread is the absolute separation of nearest raster starts on the same timestamp clock.','',
'| All-five DNR | Pairs | Minimum ms | Median ms | P95 ms | Maximum ms |','|---|---:|---:|---:|---:|---:|']
for k,label in labels.items():
 s=study['conditions'][k]['cam2_cam3']['raster']['absolute_spread_us'];text.append(f"| {label} | {s['n']} | {s['min']/1000:.6f} | {s['median']/1000:.6f} | {s['p95']/1000:.6f} | {s['max']/1000:.6f} |")
text+=['','## Digital image-change timing and controls','',
'Full-raster and central 96x96 ROI CRCs were checked independently with Freeze ON in both DNR states. Per-camera qualification, cadence histograms and all-five CRC phase spans are retained in study.json. Extra live CRC transitions are retained and are not evidence of additional sensor exposures. Periodic event matching does not establish common exposure identity or physical integration timing.','',
 'Camera 2 and camera 3 passed both full-frame and ROI frozen controls. Their live change intervals were all two rasters. Camera 3 update sequence parity changed from odd in the initial ON capture to even in the first OFF capture and remained even in ON return and OFF repeat; camera 2 stayed odd throughout. The phase change occurred in the uncaptured interval between states, so its cause cannot be separated from setting changes and clock phase. The five-camera ROI spread of the first OFF capture did not reproduce on OFF repeat.','',
'| Frozen DNR | Camera | Valid rasters | Observed s | Full CRC changes | ROI CRC changes |','|---|---:|---:|---:|---:|---:|']
for k in ['control_on','control_off']:
 for c in study['conditions'][k]['cameras']:text.append(f"| {study['conditions'][k]['dnr']} | {c['camera']} | {c['valid']} | {c['duration_s']:.3f} | {c['full_changes']} | {c['roi_changes']} |")
text+=['','| All-five DNR | Matched ROI-change sets | Minimum ms | Median ms | P95 ms | Maximum ms |','|---|---:|---:|---:|---:|---:|']
for k,label in labels.items():
 s=study['conditions'][k]['spreads_us']['roi_crc'];text.append('| '+label+' | '+str(s['n'])+' | '+' | '.join('unavailable' if s[x] is None else f"{s[x]/1000:.6f}" for x in ['min','median','p95','max'])+' |')
text+=['','## Clock drift and limits','',
'Actual spread and drift-model residual are separate results. The bracketing ON fit estimates each camera raster phase relative to camera 2; OFF residuals and the returning ON capture are retained. Sequential changes in spread alone cannot establish a DNR effect. Nearest raster matching cannot expose a whole-frame internal latency change. Sensor exposure synchronization would require corresponding exposures or independent sensor timing measurements.','',
'| Camera relative to cam2 | ON fitted drift us/s | OFF residual median us | OFF residual minimum us | OFF residual maximum us |','|---|---:|---:|---:|---:|']
for cam,d in study['bracketed_on_raster_drift'].items():
 s=d['residual_us']['off_b'];text.append(f"| {cam} | {d['slope_us_per_s']:.6f} | {s['median']:.6f} | {s['min']:.6f} | {s['max']:.6f} |")
text+=['','## Restoration and consolidated workbook','',
'Fresh ILA OSD readbacks verified all cameras 2–6 restored to 1080p30, 1/240 s, 0 dB, DNR 2D+3D and Freeze OFF, with menus closed. The operational FPGA image was reloaded. The starting EO camera-3 route was reapplied using a mode-only request whose ancillary out-of-range fields are skipped by the inspected firmware. This same-mode request writes MCU mode flash once; FPGA configuration flash was not programmed. Controller display/parameter and pose reads exactly matched their initial values, and the restored full USB camera-3 scene was directly viewed. No OSD SAVE or DFLT was used.','',
'The consolidated workbook retains the prior synchronization study and adds the earlier cam2-only DNR comparison plus this all-five DNR OFF comparison. Existing worksheets, formulas, styles, tables and panes were preserved. New spread formulas and their saved caches were checked against the independent raw-capture analysis; no formula errors were found. Native Excel execution was not performed.','',
'Workbook at completion: EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx',
'SHA-256: '+validation['workbook_sha256'],'',
'## Reproduction','',
'analyze.py imports diagnostics/eo_sync/scripts/decode_events.py and recomputes study.json plus raster/CRC cohort and cam2/cam3 pair CSVs from the raw event CSVs. bench.py and logs document hardware stages; do not rerun setting changes without reading the actual starting camera state. Report authoring uses the archived pre-edit workbook and measured statistics. manifest.json hashes every other archive file. No manufacturer manual or PDF is included.']
(DEST/'README.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
files=[]
for f in sorted(DEST.rglob('*')):
 if f.is_file():files.append(dict(path=f.relative_to(DEST).as_posix(),size=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(DEST/'manifest.json').write_text(json.dumps(dict(created_at=datetime.now().astimezone().isoformat(),files=files,total_bytes=sum(f['size'] for f in files)),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(archive=str(DEST),files=len(files),bytes=sum(f['size'] for f in files))))
