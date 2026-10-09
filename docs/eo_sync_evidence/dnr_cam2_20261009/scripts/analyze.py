"""DNR ON/OFF/ON comparison of physical camera 2; camera 3 is unchanged."""
import bisect
import collections
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p/'diagnostics/eo_sync/scripts/decode_events.py').exists())
OUT = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'captures/eo_dnr_cam2_20261009'
sys.path.insert(0, str(ROOT / 'diagnostics/eo_sync/scripts'))
from decode_events import REF_HZ, read_events, analyze_block, stats

def regression(points):
    xm = statistics.mean(x for x,y in points)
    ym = statistics.mean(y for x,y in points)
    slope = sum((x-xm)*(y-ym) for x,y in points)/sum((x-xm)**2 for x,y in points)
    intercept = ym-slope*xm
    residuals = [y-(intercept+slope*x) for x,y in points]
    return dict(intercept_us=intercept, slope_us_per_s=slope,
                residual_us=stats(residuals))

def changes(rows, key):
    return [b for a,b in zip(rows, rows[1:]) if a['geometry_valid'] and b['geometry_valid']
            and ((b['sequence']-a['sequence'])&65535)==1 and a[key]!=b[key]]

conditions = {}
phase_points = []
change_points = {'full_crc': [], 'roi_crc': []}
fall_origins = set()
for condition in ['control_on', 'on_a', 'off_b', 'on_return', 'control_off']:
    folder = OUT/condition
    blocks = []
    pair_rows = []
    for path in sorted(folder.glob('events_*.csv')):
        events = read_events(path)
        a = analyze_block(events, 'rising')
        a.pop('cohorts')
        c2 = [e for e in events if e.get('camera')==2 and e.get('phase')=='rising']
        c3 = [e for e in events if e.get('camera')==3 and e.get('phase')=='rising' and e['timing_valid']]
        first_fall = next(t['tick'] for t in events if t['kind']==3)
        fall_origins.add(first_fall % 900000)
        ref = [e['tick'] for e in c3]
        for event in c2:
            if not event['timing_valid']:
                continue
            pos = bisect.bisect_left(ref, event['tick'])
            candidates = ref[max(0,pos-1):pos+1]
            if not candidates:
                continue
            closest = min(candidates, key=lambda t: abs(t-event['tick']))
            if abs(closest-event['tick']) > REF_HZ/120:
                continue
            pair_rows.append(dict(condition=condition, block=path.name, tick=event['tick'],
                                  cam2_minus_cam3_us=(event['tick']-closest)/27))
        for key in ['full_crc', 'roi_crc']:
            series = changes(c2, key)
            intervals = [b['tick']-x['tick'] for x,b in zip(series,series[1:])]
            a['cameras'][0][key+'_interval_ticks_sum'] = sum(intervals)
            a['cameras'][0][key+'_interval_count'] = len(intervals)
            a['cameras'][0][key+'_change_intervals_rasters'] = dict(collections.Counter(
                str((b['sequence']-x['sequence'])&65535) for x,b in zip(series,series[1:])))
            a['cameras'][0][key+'_since_fall_us'] = stats([
                ((e['tick']-first_fall) % 900000)/27
                for e in series]) if series else stats([])
            if not condition.startswith('control'):
                change_points[key].extend(dict(condition=condition, tick=e['tick'],
                    phase_us=((e['tick']-first_fall)%900000)/27) for e in series)
        blocks.append(dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           first_tick=events[0]['tick'], last_tick=events[-1]['tick'], analysis=a))
    if not blocks:
        raise ValueError('Missing '+condition)
    duration = sum(b['analysis']['cameras'][0]['duration_s'] for b in blocks)
    camera = dict(duration_s=duration, records=sum(b['analysis']['cameras'][0]['records'] for b in blocks),
                  valid=sum(b['analysis']['cameras'][0]['valid'] for b in blocks),
                  sequence_gaps=sum(b['analysis']['cameras'][0]['sequence_gaps'] for b in blocks))
    camera['raster_hz'] = sum(b['analysis']['cameras'][0]['records']-1 for b in blocks)/duration
    for key,label in [('full_crc','full'),('roi_crc','roi')]:
        n = sum(b['analysis']['cameras'][0][label+'_changes'] for b in blocks)
        camera[label+'_changes'] = n
        camera[label+'_change_hz'] = n/duration
        counts = collections.Counter()
        for b in blocks:
            counts.update(b['analysis']['cameras'][0][key+'_change_intervals_rasters'])
        camera[label+'_change_intervals_rasters'] = dict(counts)
        n_intervals=sum(b['analysis']['cameras'][0][key+'_interval_count'] for b in blocks)
        ticks=sum(b['analysis']['cameras'][0][key+'_interval_ticks_sum'] for b in blocks)
        camera[label+'_change_interval_hz'] = REF_HZ*n_intervals/ticks if ticks else None
    conditions[condition] = dict(camera2=camera, blocks=blocks, pair_rows=pair_rows)
    if not condition.startswith('control'):
        phase_points.extend(pair_rows)

phase_points.sort(key=lambda r:r['tick'])
t0 = phase_points[0]['tick']
previous = None
for row in phase_points:
    row['time_s'] = (row['tick']-t0)/REF_HZ
    offset = row['cam2_minus_cam3_us']
    if previous is not None:
        offset += round((previous-offset)/(1e6/60))*(1e6/60)
    row['unwrapped_offset_us'] = offset
    previous = offset
on = [(r['time_s'],r['unwrapped_offset_us']) for r in phase_points if r['condition']!='off_b']
fit = regression(on)
if len(fall_origins)!=1:
    raise ValueError(('Trigger origin changed',fall_origins))
for row in phase_points:
    row['residual_to_on_drift_us'] = row['unwrapped_offset_us']-(fit['intercept_us']+fit['slope_us_per_s']*row['time_s'])
for condition in ['on_a','off_b','on_return']:
    rows = [r for r in phase_points if r['condition']==condition]
    conditions[condition]['relative_phase_us'] = stats([r['unwrapped_offset_us'] for r in rows])
    conditions[condition]['residual_to_on_drift_us'] = stats([r['residual_to_on_drift_us'] for r in rows])
    conditions[condition]['within_capture_fit'] = regression([(r['time_s'],r['unwrapped_offset_us']) for r in rows])
for condition in conditions.values():
    condition.pop('pair_rows')
qualification = dict(full=all(conditions[c]['camera2']['full_changes']==0 for c in ['control_on','control_off']),
                     roi=all(conditions[c]['camera2']['roi_changes']==0 for c in ['control_on','control_off']))
change_phase = {}
for key,rows in change_points.items():
    baseline = [r for r in rows if r['condition']=='on_a']
    origin = baseline[0]['phase_us']
    for r in rows:
        r['time_s']=(r['tick']-t0)/REF_HZ
        r['unwrapped_phase_us']=r['phase_us']+round((origin-r['phase_us'])/(1e6/30))*(1e6/30)
    baseline_fit=regression([(r['time_s'],r['unwrapped_phase_us']) for r in baseline])
    bracket_fit=regression([(r['time_s'],r['unwrapped_phase_us']) for r in rows if r['condition']!='off_b'])
    summaries={}
    for condition in ['on_a','off_b','on_return']:
        sample=[r for r in rows if r['condition']==condition]
        residuals=[]
        bracket_residuals=[]
        for r in sample:
            predicted=baseline_fit['intercept_us']+baseline_fit['slope_us_per_s']*r['time_s']
            delta=r['unwrapped_phase_us']-predicted
            residuals.append(delta-round(delta/(1e6/30))*(1e6/30))
            predicted=bracket_fit['intercept_us']+bracket_fit['slope_us_per_s']*r['time_s']
            delta=r['unwrapped_phase_us']-predicted
            bracket_residuals.append(delta-round(delta/(1e6/30))*(1e6/30))
        summaries[condition]=dict(phase_us=stats([r['unwrapped_phase_us'] for r in sample]),
                                 residual_to_initial_on_drift_us=stats(residuals),
                                 residual_to_bracketed_on_drift_us=stats(bracket_residuals))
    change_phase[key]=dict(initial_on_fit=baseline_fit,bracketed_on_fit=bracket_fit,conditions=summaries,
        interpretation='CRC transition phase modulo trigger period; an integer raster parity change alone does not identify exposure pairing or pipeline latency.')
result = dict(camera_under_test=2, timing_reference_camera=3, format='1080p60', shutter='1/60 s',
              trigger_hz=30, trigger_high_us=2000, exttrig_delay_ms=0,
              phase='rising', phase_taps=[336,280,308,280,322],
              protocol='ON frozen control; ON live; OFF live; ON live; OFF frozen control',
              reference_clock_hz=REF_HZ, crc_freeze_qualification=qualification,
              on_drift_fit=fit, image_change_phase_vs_trigger=change_phase, conditions=conditions,
              limits='Measures received raster phase and qualified digital image changes; no direct sensor exposure timing or end-to-end latency measurement.')
(OUT/'comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
with (OUT/'camera2_relative_phase.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,list(phase_points[0])); writer.writeheader(); writer.writerows(phase_points)
print(json.dumps(dict(qualification=qualification, drift_fit=fit,
                     image_change_phase_vs_trigger=change_phase,
                     conditions={k:{x:v for x,v in c.items() if x!='blocks'} for k,c in conditions.items()}),indent=2))
