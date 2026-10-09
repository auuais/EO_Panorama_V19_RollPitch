"""Five-camera actual spread, cadence and Freeze qualification from raw ILA CSVs."""
import bisect
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch')
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'captures/eo_dnr_all5_20261009'
sys.path.insert(0,str(ROOT/'diagnostics/eo_sync/scripts'))
from decode_events import REF_HZ,analyze_block,read_events,stats,unwrap_offsets

def save_csv(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)

def changed(rows,key):
    return [b for a,b in zip(rows,rows[1:]) if a[key]!=b[key]]

camera_rows=[];cohorts=[];pair_rows=[];conditions={};cadence=[];sources=[]
for condition in ['control_on','on_a','control_off','off_b','on_return','off_repeat']:
    camera_totals={c:dict(camera=c,records=0,valid=0,timing_valid=0,sequence_gaps=0,duration_s=0,
        full_changes=0,roi_changes=0) for c in range(2,7)}
    condition_cohorts={k:[] for k in ['raster','full_crc','roi_crc']}
    blocks=[]
    for p in sorted((OUT/condition).glob('events_*.csv')):
        events=read_events(p);a=analyze_block(events,'rising')
        file=p.relative_to(OUT).as_posix();sha=hashlib.sha256(p.read_bytes()).hexdigest()
        sources.append(dict(file=file,sha256=sha))
        assert a['trigger_fall_period_us']['min']==a['trigger_fall_period_us']['max']
        assert abs(a['trigger_fall_period_us']['median']-1e6/30)<1e-7
        assert a['trigger_high_us']['min']==a['trigger_high_us']['max']==2000
        blocks.append(dict(file=file,sha256=sha,trigger_fall_period_us=a['trigger_fall_period_us'],trigger_high_us=a['trigger_high_us'],matching=a['matching']))
        for item in a['cameras']:
            c=item['camera'];assert item['valid']==item['timing_valid']==item['records'],(condition,c,'geometry')
            assert item['sequence_gaps']==0,(condition,c,'sequence gaps')
            total=camera_totals[c]
            for key in ['records','valid','timing_valid','sequence_gaps','duration_s','full_changes','roi_changes']:total[key]+=item[key]
            camera_rows.append(dict(condition='all5_dnr_'+condition,mode='ExtTrig',control=condition.startswith('control'),selected=True,
                **item,block=p.name,build='r4_trig30',offset_median_us=a['matching']['raster']['offsets'][c]['unwrapped_offset_us']['median'],
                drift_us_per_second=a['matching']['raster']['offsets'][c]['drift_us_per_second'],source_file=file,source_sha256=sha,
                format_fps=60,phase_tap=[336,280,308,280,322][c-2],control_id='all5_dnr_control_off' if condition in ['off_b','off_repeat','control_off'] else 'all5_dnr_control_on'))
        for series,rows in a['cohorts'].items():
            for row in rows:
                entry=dict(condition='all5_dnr_'+condition,format_fps=60,mode='ExtTrig',**row)
                condition_cohorts[series].append(entry)
                if not condition.startswith('control'):cohorts.append(entry)
        streams={c:[e for e in events if e.get('camera')==c and e.get('phase')=='rising'] for c in range(2,7)}
        for series in ['full_crc','roi_crc']:
            for c,rr in streams.items():
                changes=changed(rr,series)
                intervals=[((b['sequence']-a['sequence'])&65535) for a,b in zip(changes,changes[1:])]
                cadence.append(dict(condition=condition,block=p.name,camera=c,series=series,changes=len(changes),
                    interval_rasters=dict(Counter(intervals)),sequence_parity=dict(Counter(e['sequence']%2 for e in changes))))
        if not condition.startswith('control'):
            for series in ['raster','full_crc','roi_crc']:
                ss={c:rr if series=='raster' else changed(rr,series) for c,rr in streams.items() if c in [2,3]}
                period=statistics.median(b['tick']-a['tick'] for a,b in zip(ss[2],ss[2][1:]))
                reference=[e['tick'] for e in ss[3]];used=set()
                for event in ss[2]:
                    pos=bisect.bisect_left(reference,event['tick']);candidates=reference[max(0,pos-1):pos+1]
                    if not candidates:continue
                    tick=min(candidates,key=lambda t:abs(t-event['tick']))
                    if abs(tick-event['tick'])>period/2:continue
                    assert tick not in used,('Duplicate pair partner',condition,p.name,series,tick)
                    used.add(tick)
                    delta=(event['tick']-tick)/27
                    pair_rows.append(dict(condition=condition,block=p.name,series=series,cam2_tick=event['tick'],cam3_tick=tick,
                        signed_cam2_minus_cam3_us=delta,absolute_spread_us=abs(delta)))
    assert len(blocks)==(1 if condition.startswith('control') else 2),(condition,blocks)
    for c,total in camera_totals.items():
        total['raster_hz']=(total['records']-len(blocks))/total['duration_s']
        for key in ['full','roi']:total[key+'_change_hz']=total[key+'_changes']/total['duration_s']
    condition_pairs={}
    for series in ['raster','full_crc','roi_crc']:
        rows=[r for r in pair_rows if r['condition']==condition and r['series']==series]
        condition_pairs[series]=dict(pairs=len(rows),absolute_spread_us=stats([r['absolute_spread_us'] for r in rows]),signed_cam2_minus_cam3_us=stats([r['signed_cam2_minus_cam3_us'] for r in rows]))
    conditions[condition]=dict(dnr='OFF' if condition in ['off_b','off_repeat','control_off'] else '2D+3D',
        observed_s=camera_totals[2]['duration_s'],cameras=list(camera_totals.values()),blocks=blocks,
        spreads_us={k:stats([r['span_us'] for r in rows]) for k,rows in condition_cohorts.items()},cam2_cam3=condition_pairs)

qualification={}
for control in ['control_on','control_off']:
    qualification[control]={series:dict(all_five_pass=all(c[series.split('_')[0]+'_changes']==0 for c in conditions[control]['cameras']),
        cameras={str(c['camera']):c[series.split('_')[0]+'_changes']==0 for c in conditions[control]['cameras']}) for series in ['full_crc','roi_crc']}

# Fit the bracketing ON raster offsets and assess OFF residuals. Raw spread remains the primary result.
fit_rows=[r for r in cohorts if r['series']=='raster']
period=statistics.median(r['period_ticks'] for r in fit_rows)/27
t0=fit_rows[0]['anchor_tick'];drift={}
for camera in range(3,7):
    offsets=unwrap_offsets([r[f'cam{camera}_offset_us'] for r in fit_rows],period)
    points=[dict(condition=r['condition'],t=(r['anchor_tick']-t0)/REF_HZ,y=y) for r,y in zip(fit_rows,offsets)]
    on=[p for p in points if p['condition'] in ['all5_dnr_on_a','all5_dnr_on_return']]
    xm=statistics.mean(p['t'] for p in on);ym=statistics.mean(p['y'] for p in on)
    slope=sum((p['t']-xm)*(p['y']-ym) for p in on)/sum((p['t']-xm)**2 for p in on)
    residual={condition:stats([p['y']-ym-slope*(p['t']-xm) for p in points if p['condition']=='all5_dnr_'+condition]) for condition in ['on_a','off_b','on_return','off_repeat']}
    drift[str(camera)]=dict(reference_camera=2,slope_us_per_s=slope,residual_us=residual)

study=dict(format='1080p60',physical_cameras=[2,3,4,5,6],shutter='1/60 s',gain_db=0,mode='ExtTrig',trigger_hz=30,
    trigger_high_us=2000,exttrig_delay_ms=0,reference_clock_hz=REF_HZ,phases=['rising']*5,phase_taps=[336,280,308,280,322],
    dnr_sequence='All five cameras: 2D+3D ON, OFF, ON, OFF repeat; no Freeze intervention between live captures',
    drift_fit_limits='The primary OFF capture is bracketed by ON captures; the later OFF repeat residual extrapolates that fit.',
    spread_definition='Shortest circular arc containing all five nearest input event phases on one common timebase; milliseconds in report. Pair spread is absolute nearest cam2/cam3 event separation.',
    limits='Periodic event matching does not identify same physical exposures. Raster spread and CRC-update phase do not measure sensor exposure timing. CRC interpretation requires the corresponding frozen control; extra live transitions are retained.',
    crc_freeze_qualification=qualification,conditions=conditions,camera_rows=camera_rows,crc_cadence=cadence,
    bracketed_on_raster_drift=drift,sources=sources,raster_cohorts=[r for r in cohorts if r['series']=='raster'])
(OUT/'study.json').write_text(json.dumps(study,indent=2)+'\n',encoding='utf-8')
save_csv('raster_cohorts.csv',[r for r in cohorts if r['series']=='raster'])
save_csv('crc_cohorts.csv',[r for r in cohorts if r['series']!='raster'])
save_csv('cam2_cam3_pairs.csv',pair_rows)
save_csv('camera_observations.csv',camera_rows)
print(json.dumps(dict(qualification=qualification,conditions={k:dict(seconds=v['observed_s'],spreads_us=v['spreads_us'],pair=v['cam2_cam3']['raster']) for k,v in conditions.items()},drift=drift),indent=2))
