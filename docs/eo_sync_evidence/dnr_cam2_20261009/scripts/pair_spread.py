"""Report actual cam2/cam3 separation, independently from raw simultaneous ILA events."""
import bisect
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'diagnostics/eo_sync/scripts/decode_events.py').exists())
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostics/eo_sync/scripts'))
from decode_events import REF_HZ, read_events, stats

def changed(rows,key):
    return [b for a,b in zip(rows,rows[1:]) if ((b['sequence']-a['sequence'])&65535)==1 and a[key]!=b[key]]

def fit(rows):
    t0=rows[0]['cam2_tick']
    points=[((r['cam2_tick']-t0)/REF_HZ,r['signed_offset_us']) for r in rows]
    xm=statistics.mean(x for x,y in points);ym=statistics.mean(y for x,y in points)
    slope=sum((x-xm)*(y-ym) for x,y in points)/sum((x-xm)**2 for x,y in points)
    residuals=[y-ym-slope*(x-xm) for x,y in points]
    return dict(drift_us_per_s=slope,residual_us=stats(residuals),
                detrended_stdev_us=statistics.pstdev(residuals))

pairs=[];conditions={};sources=[];cadence_checks=[]
for condition in ['on_a','off_b','on_return']:
    for path in sorted((OUT/condition).glob('events_*.csv')):
        events=read_events(path)
        rows={c:[e for e in events if e.get('camera')==c and e.get('phase')=='rising'] for c in [2,3]}
        assert all(r['geometry_valid'] for stream in rows.values() for r in stream)
        assert all(((b['sequence']-a['sequence'])&65535)==1 for stream in rows.values() for a,b in zip(stream,stream[1:]))
        sources.append(dict(file=path.relative_to(OUT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        for series in ['raster','full_crc','roi_crc']:
            streams={c:(stream if series=='raster' else changed(stream,series)) for c,stream in rows.items()}
            if series!='raster':
                for camera,stream in streams.items():
                    intervals=[((b['sequence']-a['sequence'])&65535) for a,b in zip(stream,stream[1:])]
                    exceptional=[dict(tick=b['tick'],time_from_block_start_s=(b['tick']-events[0]['tick'])/REF_HZ,
                        sequence=b['sequence'],preceding_sequence=a['sequence'],interval_rasters=interval)
                        for a,b,interval in zip(stream,stream[1:],intervals) if interval!=2]
                    cadence_checks.append(dict(condition=condition,block=path.name,camera=camera,series=series,
                        changes=len(stream),sequence_parity_counts=dict(Counter(e['sequence']%2 for e in stream)),
                        interval_raster_counts=dict(Counter(intervals)),exceptional_intervals=exceptional))
            period=statistics.median(b['tick']-a['tick'] for a,b in zip(streams[2],streams[2][1:]))
            ref=[e['tick'] for e in streams[3]];used=set()
            for event in streams[2]:
                pos=bisect.bisect_left(ref,event['tick'])
                candidates=ref[max(0,pos-1):pos+1]
                if not candidates:continue
                tick=min(candidates,key=lambda t:abs(t-event['tick']))
                # Exclude capture endpoints lacking a partner within half a cadence.
                limit=REF_HZ/120 if series=='raster' else period/2
                if abs(event['tick']-tick)>limit:continue
                assert tick not in used,('Duplicate nearest partner',condition,path.name,series,tick)
                used.add(tick)
                delta=(event['tick']-tick)/27
                pairs.append(dict(condition=condition,block=path.name,series=series,
                    cam2_tick=event['tick'],cam3_tick=tick,signed_offset_us=delta,spread_us=abs(delta)))
    conditions[condition]={}
    for series in ['raster','full_crc','roi_crc']:
        selected=[r for r in pairs if r['condition']==condition and r['series']==series]
        conditions[condition][series]=dict(pairs=len(selected),
            signed_cam2_minus_cam3_us=stats([r['signed_offset_us'] for r in selected]),
            absolute_spread_us=stats([r['spread_us'] for r in selected]),
            raw_stdev_us=statistics.pstdev(r['signed_offset_us'] for r in selected),
            within_condition_fit=fit(selected) if series=='raster' else None)

previous=list(csv.DictReader((OUT/'camera2_relative_phase.csv').open(newline='')))
actual=[r for r in pairs if r['series']=='raster']
assert len(actual)==len(previous)
for a,b in zip(actual,previous):
    assert a['condition']==b['condition'] and a['block']==b['block'] and a['cam2_tick']==int(b['tick'])
    assert a['signed_offset_us']==float(b['cam2_minus_cam3_us'])
result=dict(definition='Absolute time separation of nearest cam2 and cam3 events within the same simultaneous capture; positive signed offset means cam2 arrives later.',
    reference_hz=REF_HZ,format='1080p60',trigger_hz=30,
    dnr_sequence='Only camera 2: 2D+3D ON, OFF, ON; camera 3 unchanged',
    exposure_scope='Camera 2 shutter was verified at 1/60 s; camera 3 shutter was not changed or freshly reread in this experiment. Do not describe this as a matched-exposure test.',
    frame_pairing='Nearest periodic events, not identification of the same physical exposure or image across cameras.',
    crc_limits='Cam2 full/ROI CRC passed frozen controls in both DNR states. Cam3 was live throughout this experiment, so its CRC-change timing is descriptive and lacks an independent frozen control in this run.',
    correction='The previously quoted 3–4 us was the OFF residual relative to an ON clock-drift model, not the actual inter-camera spread, which is several milliseconds.',
    crc_phase_observation='Camera 3 changed CRC-update raster parity during on_a/events_001.csv while camera 2 DNR was still ON. Both full and ROI CRCs have exceptional 1, 3 and 1 raster intervals at 12.575622, 12.625623 and 13.442303 s from block start. The final parity persists in OFF and returning ON captures. Signed CRC offsets are not fitted as clock drift because this phase change produces multiple modes.',
    conclusion='Actual cam2/cam3 raster gaps are milliseconds in all states. No substantial reversible DNR OFF effect on raster alignment was demonstrated. The reference-camera CRC parity shift before OFF prevents attributing the later nearest image-change gap to DNR.',
    sources=sources,conditions=conditions,crc_cadence_checks=cadence_checks,raster_pairs_match_previous_raw_data=True)
(OUT/'cam2_cam3_spread.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
with (OUT/'cam2_cam3_spread_pairs.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,list(pairs[0]));w.writeheader();w.writerows(pairs)
print(json.dumps(conditions,indent=2))
