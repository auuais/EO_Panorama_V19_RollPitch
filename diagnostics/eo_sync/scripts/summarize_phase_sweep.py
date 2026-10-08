"""Summarize geometry and CRC stability at each independently captured phase.

Frozen windows must be declared by the operator using verified camera OSDs.
The script never infers Freeze from scene similarity or maximum novelty.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from decode_events import read_events, analyze_block, EXPECTED


def summarize(root, frozen=False):
    rows = []
    for path in sorted(root.glob('phase_*/events_*.csv')):
        events = read_events(path)
        tap = int(path.parent.name.split('_')[1])
        for edge in ['rising', 'falling']:
            result = analyze_block(events, edge)
            for camera in result['cameras']:
                selected = [e for e in events if e['kind']==1 and e['camera']==camera['camera'] and e['phase']==edge]
                good = [e for e in selected if e['geometry_valid']]
                full = Counter(e['full_crc'] for e in good)
                roi = Counter(e['roi_crc'] for e in good)
                row = dict(tap=tap, effective_tap=(tap+(224 if edge=='falling' else 0))%448,
                           **camera, unique_full_crc=len(full), unique_roi_crc=len(roi),
                           modal_full_crc=f'{full.most_common(1)[0][0]:08x}' if full else None,
                           modal_roi_crc=f'{roi.most_common(1)[0][0]:08x}' if roi else None,
                           source_file=str(path.relative_to(root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                row['all_geometry_valid'] = camera['records']>=100 and camera['valid']==camera['records'] and camera['sequence_gaps']==0
                row['frozen_full_stable'] = frozen and row['all_geometry_valid'] and len(full)==1
                row['frozen_roi_stable'] = frozen and row['all_geometry_valid'] and len(roi)==1
                row['geometry_failures'] = {k:sum(e[k]!=v for e in selected) for k,v in EXPECTED.items()}
                rows.append(row)
    if not rows:raise ValueError('No phase sweep captures found')
    result = dict(frozen_declared=frozen, rows=rows)
    (root/'phase_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    fields = ['tap','effective_tap','camera','phase','records','valid','timing_valid','sequence_gaps','raster_hz',
              'unique_full_crc','unique_roi_crc','modal_full_crc','modal_roi_crc','all_geometry_valid',
              'frozen_full_stable','frozen_roi_stable','source_file','sha256']
    with (root/'phase_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    for cam in range(2,7):
        print(json.dumps(dict(camera=cam, candidates=[{k:r[k] for k in ['tap','phase','records','valid','frozen_full_stable','modal_full_crc']}
              for r in rows if r['camera']==cam and r['all_geometry_valid']]),separators=(',',':')))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--frozen',action='store_true')
    a=p.parse_args();summarize(a.folder,a.frozen)
