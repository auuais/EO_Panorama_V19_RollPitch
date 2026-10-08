"""Curate measurements with OSD/negative-control context; preserve raw decodes."""
import csv,json,hashlib
from pathlib import Path
root=Path('E:/Xylinx/EO_Panorama_V19_RollPitch')
out=root/'captures/eo60_verify_20261008'
final_state=json.loads((out/'final_state.json').read_text())
assert final_state['restored'] is True
specs=[
 ('crc30_shutter30','30-mode 1/30 s',30,'1/30 s','2D+3D','OFF','Snapshot','osd30_shutter30_reopened'),
 ('crc60_2x','60-mode 2x',60,'2x','2D+3D','OFF','Snapshot','osd60_slower_attempt'),
 ('crc60_freeze_on','Freeze: snapshot RTL',60,'2x','2D+3D','ON','Snapshot','osd60_freeze_on'),
 ('crc60_freeze_original','Freeze: original RTL',60,'2x','2D+3D','ON','Original r2','osd60_freeze_on'),
 ('crc60_frozen_dnr_off','Freeze: DNR OFF',60,'2x','OFF','ON','Snapshot','osd60_frozen_dnr_off'),
 ('crc60_2x_dnr_off','2x, DNR OFF',60,'2x','OFF','OFF','Snapshot','osd60_unfrozen_dnr_off'),
 ('crc60_shutter60_dnr_off','1/60 s, DNR OFF',60,'1/60 s','OFF','OFF','Snapshot','osd60_shutter60_dnr_off'),
 ('crc30_freeze_control','30-mode Freeze control',30,'1/60 s','OFF','ON','Snapshot','osd30_freeze_control'),
]
entries=[]
for tag,label,hz,shutter,dnr,freeze,build,osd in specs:
    folder=out/tag;raw=json.loads((folder/'summary.json').read_text());p=raw['phases']['falling']
    rows=[r for r in csv.DictReader((folder/'decoded_frames.csv').open()) if r['phase']=='1']
    pairs=[(a,b) for a,b in zip(rows,rows[1:]) if (int(b['seq'])-int(a['seq']))%65536==1 and a['valid']==b['valid']=='True']
    full=sum(a['crc']!=b['crc'] for a,b in pairs);roi=sum(a['roi_crc']!=b['roi_crc'] for a,b in pairs)
    assert len(pairs)==p['valid_adjacent_pairs'] and full==p['crc_changed_pairs']
    snap=json.loads((out/osd/'snapshot_summary.json').read_text())
    entry=dict(tag=tag,label=label,format_hz=hz,shutter_osd=shutter,dnr=dnr,freeze=freeze,build_label=build,
        raster_hz=p['raster_starts_hz'],reports=p['reports'],valid_reports=p['valid_reports'],pairs=len(pairs),
        full_changed=full,roi_changed=roi,full_spacing=p['spacing']['crc'],roi_spacing=p['spacing']['roi_crc'],
        fresh_input_fps=p['input_updates_hz'] if hz==30 and freeze=='OFF' else None,
        raw_decoder_accepted=p['content_rate_accepted'],raw_decoder_input_updates_hz=p['input_updates_hz'],
        osd_evidence=f"{osd}/{snap['frames'][0]['file']}",trigger_hz_observations=raw['trigger_hz_observations'],
        pclk_hz_observations=raw['pclk_hz_observations'])
    entry['freeze_control_pass']=(full==roi==0 and len(pairs)>0 and p['valid_reports']==p['reports']) if freeze=='ON' else None
    entry['roi_spacing_rasters']=int(next(iter(p['spacing']['roi_crc']))) if len(p['spacing']['roi_crc'])==1 else None
    if tag=='crc30_freeze_control':
        entry['shutter_readback_evidence']='post30_control_shutter.png'
        entry['shutter_readback_context']='After capture at unchanged 1080p30, before any restoration shutter writes; 1/60 s was visually reviewed.'
    entries.append(entry)
a=json.loads((out/'image60_frozen/snapshot_summary.json').read_text())
b=json.loads((out/'image60_frozen_after_original/snapshot_summary.json').read_text())
hashes=[x['sha256'] for s in [a,b] for x in s['frames']]
assert len(set(hashes))==1,'Frozen image not retained across original-build control'
manual=next(Path('C:/SVNProjects/IMU_Stabilize_v40/Manual/EO').glob('*Approval*'))
result=dict(entries=entries,manual_path=manual.as_posix(),manual_sha256=hashlib.sha256(manual.read_bytes()).hexdigest(),
    key_images={k:f"{tag}/{json.loads((out/tag/'snapshot_summary.json').read_text())['frames'][0]['file']}" for k,tag in [('exposure30','osd30_shutter30_reopened'),('exposure60','osd60_exposure_after_switch'),('freeze60','osd60_freeze_on')]},
    frozen_image_sha256=hashes[0],frozen_image_retained_across_original_build=True,
    frozen_image_sampling='960x540 Y, every second pixel and row. Equality is not a full-resolution Y/C byte comparison.',
    primary_verdict='Withdraw 60 fresh input FPS at 1/30 s. Direct 60-mode OSD shows 1/60 s after a 30-mode 1/30 s preselection; original CRC diagnostic fails a frozen-camera control.',
    headline_lines=[
      'Confirmed: 1080p30 at 1/30 s changes to an OSD value of 1/60 s when switched to 1080p60, without a shutter command.',
      'Original diagnostic: FREEZE ON still produces 248/248 changed full and ROI CRC pairs. Its 60 fresh-FPS conclusion is withdrawn.',
      'At directly read 1/60 s: about 60 rasters/s and 30 ROI changes/s. Whole-frame fresh FPS and physical integration remain unverified.'
    ],
    verdict_lines=[
      'The supplied manual lists shutter values for 30/25 fps mode. It does not specify the 60-mode exposure mapping used by the earlier sweep.',
      'The same frozen sampled image is byte-identical before and after the original-bitstream test. Camera settings were not changed during that bracket.',
      'The snapshot build keeps the frozen ROI CRC constant but its full CRC changes. Turning DNR OFF does not remove those full-CRC changes.',
      'At 1080p30, the same snapshot build passes the frozen control: 0/119 changed falling-phase pairs and 0/120 rising-phase pairs in both CRCs.',
      'At 1080p60 with DNR OFF, both 2x and directly read 1/60 s show a two-raster ROI change cadence (about 30/s). This is a local image measurement.',
      'Passing geometry and internal timing is insufficient to qualify active-pixel integrity at 148.5 MHz. The cause is not yet isolated.',
      'Old 60-mode shutter labels were 30-mode preselected values. Raw counts are retained; the former fresh-FPS conclusions are marked unverified.',
      'Earlier 1080p30 exposure sweeps remain separate: roughly 15 or 30 payload updates/s, depending on the shutter setting and recorded controls.',
      'The manufacturer’s quoted 25 Hz claim is not a documented universal limit in these manuals. Its original wording and test conditions remain unavailable.',
      'Operational FPGA and starting camera/display settings were restored. See the linked restoration record.'
    ],
    method_lines=[
      'Manual: DM-G15-42 approval sheet v1.04, 4 January 2024. Printed pages 15 (1080p60 geometry), 39/41 (trigger), 43 (30/25-mode shutter table), 47/48 (DNR/Freeze).',
      'The snapshot ILA stores two complete 960x540 Y sample arrays without filtering, plus 1472 packets of the next raster. Coordinates, byte order and packet completeness are checked.',
      'Two RTL/snapshot decoder checks passed. Snapshot build timing: setup +1.160 ns, hold +0.001 ns, pulse width +2.825 ns; bus skew passes.',
      'External input timing is only a zero-reference aperture model. No camera/PCB clock-to-data limits or electrical timing margin were measured.',
      'All tests use generated 60 Hz / 2 ms-high trigger pulses. The internal counter does not measure camera-accepted triggers or sensor exposure starts.',
      'CRC comparisons use only adjacent valid sequence numbers. Full Y/C CRC and central 96x96 Y/C ROI CRC are compared independently.',
      'Original r2 frozen capture is bracketed by the identical sampled Y image on the snapshot build, with no camera commands between the closed-image snapshots.',
      'The raw decoder can label a frozen original-r2 capture as accepted 60 FPS. That automatic result is rejected by this report’s independent Freeze control.',
      'No 60-mode full-frame fresh-image FPS is accepted here. ROI cadence, when available, is a local observation and does not independently count physical exposures.',
      'Freeze controls do not fully isolate camera post-processing from FPGA input sampling. Disabling DNR excludes that setting as the sole explanation.',
      'To qualify 60 fresh FPS: first obtain stable full Y/C data on a frozen input, then repeat an unfrozen capture with direct 60-mode shutter readback and a timed optical stimulus.',
      'To verify actual integration time: use a calibrated pulsed-light or moving target and exposure timing. A configurable strobe width alone is not sensor integration time.'
    ])
(out/'verification_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps([{k:e[k] for k in ['tag','raster_hz','pairs','full_changed','roi_changed','freeze_control_pass']} for e in entries],indent=2))
