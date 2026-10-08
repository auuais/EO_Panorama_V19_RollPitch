import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'diagnostics/eo_sync/scripts'))
from decode_events import read_events
root=Path.cwd()/'captures/eo_sync_trig30_20261008'
events=read_events(root/'60_trig30_live/events_001.csv')
frames=[e for e in events if e['kind']==1 and e['camera']==6 and e['phase']=='falling']
changes=[i for i in range(1,len(frames)) if frames[i]['roi_crc']!=frames[i-1]['roi_crc']]
indices=sorted({i for a,i in zip(changes,changes[1:]) if i-a==1})
groups=[]
for index in indices:
    rows=[dict(sequence=f['sequence'],tick=f['tick'],roi_crc=f"{f['roi_crc']:08x}",full_crc=f"{f['full_crc']:08x}") for f in frames[max(0,index-3):index+4]]
    groups.append(dict(event_index=index,neighborhood=rows))
out=dict(camera=6,block='events_001',single_raster_change_intervals=len(indices),groups=groups,
         limitation='CRC neighborhoods alone cannot distinguish sampling errors from camera payload changes or tearing.')
(root/'cam6_anomalies.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
