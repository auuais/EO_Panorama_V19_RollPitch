import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'diagnostics/eo_sync/scripts'))
from decode_events import read_events, analyze_block, stats
paths=sorted((root/'captures/eo_dnr_cam2_20261009'/sys.argv[1]).glob('events_*.csv'))
if len(sys.argv)>2:
    paths=paths[:int(sys.argv[2])]
for path in paths:
    events=read_events(path)
    a=analyze_block(events,'rising')
    rows=[e for e in events if e.get('camera')==2 and e.get('phase')=='rising']
    changes=[b for x,b in zip(rows,rows[1:]) if x['geometry_valid'] and b['geometry_valid']
             and ((b['sequence']-x['sequence'])&65535)==1 and x['full_crc']!=b['full_crc']]
    fall=next(e['tick'] for e in events if e['kind']==3)
    print(json.dumps(dict(file=path.name,cameras=a['cameras'][:2],
                         cam2_full_change_phase_us=stats([((e['tick']-fall)%900000)/27 for e in changes]),
                         trigger_period_us=a['trigger_fall_period_us'],high_us=a['trigger_high_us'])))
