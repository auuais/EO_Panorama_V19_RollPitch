import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'diagnostics/eo_sync/scripts'))
from decode_events import read_events
root=Path.cwd()/'captures/eo_sync_trig30_exp60_20261009'
out=[]
for folder in ['60_trig30_exp60_live','60_trig30_exp60_repeat']:
    for p in sorted((root/folder).glob('events_*.csv')):
        events=read_events(p)
        for cam in range(2,7):
            frames=[e for e in events if e['kind']==1 and e['camera']==cam and e['phase']=='rising']
            changes=[i for i in range(1,len(frames)) if frames[i]['roi_crc']!=frames[i-1]['roi_crc']]
            indices=[i for a,i in zip(changes,changes[1:]) if i-a==1]
            xor=Counter(f"{frames[i]['roi_crc']^frames[i-1]['roi_crc']:08x}" for i in indices)
            groups=[dict(index=i,neighborhood=[{k:f[k] for k in ['sequence','tick','roi_crc','full_crc','geometry_valid']} for f in frames[max(0,i-3):i+4]]) for i in indices]
            out.append(dict(condition=folder,block=p.stem,camera=cam,single_raster_intervals=len(indices),xor_counts=dict(xor),neighborhoods=groups))
payload=dict(observations=out,limitation='CRC neighborhoods alone cannot distinguish receiver sampling errors, camera payload changes or tearing. Repeated CRC XOR values are suggestive, not a diagnosis.')
(root/'roi_anomalies.json').write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['condition','block','camera','single_raster_intervals','xor_counts']} for r in out if r['single_raster_intervals']],indent=2))
