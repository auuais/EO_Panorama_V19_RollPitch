import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'diagnostics/eo_sync/scripts'))
from decode_events import read_events
root=Path.cwd()/'captures/eo_sync_trig30_20261008'
study=json.loads((root/'study.json').read_text())
live=next(c for c in study['conditions'] if not c['control'])
assert live['trigger_verified'] and live['qualified_image_series']=='roi_crc'
assert live['content_complete'] and live['timing_complete']
rows=[]
for cam in range(2,7):
    obs=[r for r in live['camera_rows'] if r['camera']==cam]
    seconds=sum(r['duration_s'] for r in obs);records=sum(r['records'] for r in obs);changes=sum(r['roi_changes'] for r in obs)
    rows.append(dict(camera=cam,seconds=seconds,rasters=records,raster_hz=(records-len(obs))/seconds,
                     roi_changes=changes,roi_changes_hz=changes/seconds,sequence_gaps=sum(r['sequence_gaps'] for r in obs)))
patterns=[]
for p in sorted((root/live['id']).glob('events_*.csv')):
    events=read_events(p)
    for cam in range(2,7):
        frames=[e for e in events if e['kind']==1 and e['camera']==cam and e['phase']==live['phases'][cam-2]]
        assert all(e['geometry_valid'] for e in frames)
        changed=[b for a,b in zip(frames,frames[1:]) if a['roi_crc']!=b['roi_crc']]
        gaps=Counter((b['sequence']-a['sequence'])&65535 for a,b in zip(changed,changed[1:]))
        patterns.append(dict(camera=cam,block=p.stem,rasters_between_roi_changes=dict(gaps)))
out=dict(cameras=rows,patterns=patterns,observed_s=live['observed_s'],raster_spread_us=live['spreads_us']['raster'],
         roi_change_spread_us=live['image_spread_us'],trigger=[b['trigger_period_us'] for b in live['blocks_detail']])
(root/'live_metrics.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
