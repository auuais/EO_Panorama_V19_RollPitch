"""Read-only integrity and actual spread summary of one completed capture stage."""
import json
import sys
from pathlib import Path
ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch');sys.path.insert(0,str(ROOT/'diagnostics/eo_sync/scripts'))
from decode_events import read_events,analyze_block,stats
folder=ROOT/'captures/eo_dnr_all5_20261009'/sys.argv[1]
spreads={k:[] for k in ['raster','full_crc','roi_crc']}
for p in sorted(folder.glob('events_*.csv')):
 a=analyze_block(read_events(p),'rising')
 assert all(c['valid']==c['records'] and c['sequence_gaps']==0 for c in a['cameras'])
 for k,rr in a['cohorts'].items():spreads[k].extend(r['span_us'] for r in rr)
 print(json.dumps(dict(block=p.name,cameras=[{k:c[k] for k in ['camera','records','valid','sequence_gaps','duration_s','raster_hz','full_changes','roi_changes']} for c in a['cameras']],trigger_period_us=a['trigger_fall_period_us'],trigger_high_us=a['trigger_high_us'])))
print(json.dumps(dict(condition=folder.name,spreads_us={k:stats(v) for k,v in spreads.items()})))
