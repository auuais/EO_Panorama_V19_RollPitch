import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'diagnostics/eo_sync/scripts'))
from decode_events import read_events,analyze_block
root=Path.cwd()/'captures/eo_sync_trig30_20261008'
fine=[]
for tap in [308,322,336]:
    p=root/f'cam6_frozen_fine/phase_{tap:03d}/events_000.csv'
    frames=[e for e in read_events(p) if e['kind']==1 and e['camera']==6 and e['phase']=='rising']
    assert len(frames)>=100 and all(e['geometry_valid'] for e in frames)
    crc={e['roi_crc'] for e in frames};assert len(crc)==1
    fine.append(dict(tap=tap,records=len(frames),roi_crc=f'{next(iter(crc)):08x}',source=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len({r['roi_crc'] for r in fine})==1
rows=[];patterns=[]
for folder,control in [('cam6_recheck_control',True),('cam6_recheck_live',False)]:
    p=root/folder/'events_000.csv'
    if not p.exists():
        if '--partial' in sys.argv:continue
        raise ValueError('Missing recheck live capture')
    expected=sum(t<<(9*i) for i,t in enumerate([336,280,308,280,322]))
    lines=(root/folder/'phase_checks.txt').read_text().splitlines()
    assert len(lines)==2
    for label,line in zip(['before_capture','after_block_0'],lines):
        word=int(line.split()[-2],16)
        assert line.split()[0]==label and word&((1<<45)-1)==expected and (word>>45)&31==31 and word>>50==0
    events=read_events(p);a=analyze_block(events,'rising');cam=next(c for c in a['cameras'] if c['camera']==6)
    assert cam['records']>=100 and cam['valid']==cam['records'] and cam['sequence_gaps']==0
    for key,target in [('trigger_fall_period_us',1e6/30),('trigger_high_us',2000)]:
        assert a[key]['n']>=100 and abs(a[key]['min']-target)<1e-6 and abs(a[key]['max']-target)<1e-6
    if control:assert cam['roi_changes']==0
    frames=[e for e in events if e['kind']==1 and e['camera']==6 and e['phase']=='rising']
    if control:assert f"{frames[0]['roi_crc']:08x}"==fine[0]['roi_crc']
    changed=[b for a,b in zip(frames,frames[1:]) if a['roi_crc']!=b['roi_crc']]
    patterns.append(dict(condition=folder,rasters_between_roi_changes=dict(Counter((b['sequence']-a['sequence'])&65535 for a,b in zip(changed,changed[1:])))))
    offset=a['matching']['raster'].get('offsets',{}).get(6,{})
    rows.append(dict(condition=folder,mode='ExtTrig 30 Hz recheck',control=control,selected=True,build='r4_trig30',block='events_000',format_fps=60,
                     phase_tap=322,control_id='cam6_recheck_control',source_file=str(p.relative_to(root)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                     offset_median_us=offset.get('unwrapped_offset_us',{}).get('median'),drift_us_per_second=offset.get('drift_us_per_second'),**cam))
out=dict(scope='Camera 6 only: cameras 2–5 remained live during the negative control',fine_phase_qualification=fine,camera_rows=rows,patterns=patterns)
(root/'cam6_recheck.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(fine=fine,results=[{k:r[k] for k in ['condition','records','valid','raster_hz','roi_changes','roi_change_hz','full_changes']} for r in rows],patterns=patterns),indent=2))
