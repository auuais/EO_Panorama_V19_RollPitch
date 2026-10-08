"""Audit rate-monitor ILA CSVs, preserving every capture and validity state."""
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from decode_cam_fps import field

TICK_US = 256e6 / 74250000


def samples(path):
    with path.open(newline='') as f:
        for row in csv.DictReader(f):
            if row['Sample in Buffer'].isdigit():
                yield row


def rate_review(folder):
    out = []
    for path in sorted(folder.glob('w*.csv')):
        rows = list(samples(path))
        if not rows:
            continue
        col = next(k for k in rows[0] if 'eo_cam_rate_word' in k)
        r = rows[0]
        v = int(r[col], 16)
        assert field(v, 63, 62) == 2 and field(v, 41, 39) < 6, (path, hex(v))
        seen = int(r['eo_follow_seen[4:0]'], 16)
        span = (int(r['eo_follow_span_cycles[21:20]'], 16) << 20) | int(r['eo_follow_span_cycles_1[19:0]'], 16)
        out.append(dict(file=path.name, word=f'{v:016x}', camera=field(v, 41, 39)+1,
                        frames=field(v, 38, 31), min_ticks=field(v, 30, 16), max_ticks=field(v, 15, 1),
                        trigger_count=field(v, 61, 56), trigger_ticks=field(v, 55, 42),
                        free_running=int(r['eo_trigger_free_running'],16),
                        all_free_running_values=sorted({int(x['eo_trigger_free_running'],16) for x in rows}),
                        seen=seen, wait=int(r['eo_follow_wait'],16), span_ms=span/74250,
                        complete=(seen==31 and int(r['eo_follow_wait'],16)==0),
                        distinct_rate_words=len({x[col] for x in rows}), sample_count=len(rows)))
    cams=defaultdict(list)
    for r in out:
        cams[r['camera']].append(r)
    summary = dict(folder=str(folder), captures=len(out), cameras={
        k:dict(captures=len(v), frames=sorted({r['frames'] for r in v}),
               min_ticks=sorted({r['min_ticks'] for r in v}), max_ticks=sorted({r['max_ticks'] for r in v})) for k,v in cams.items()},
        trigger_counts=dict(Counter(r['trigger_count'] for r in out)),
        trigger_ticks=dict(Counter(r['trigger_ticks'] for r in out)),
        free_running=dict(Counter(r['free_running'] for r in out)),
        complete_captures=sum(r['complete'] for r in out))
    complete=[r['span_ms'] for r in out if r['complete']]
    if complete:
        summary['complete_span_ms']=dict(min=min(complete),median=statistics.median(complete),max=max(complete))
    allspan=[r['span_ms'] for r in out]
    if allspan:
        summary['unqualified_span_ms']=dict(min=min(allspan),median=statistics.median(allspan),max=max(allspan))
    return dict(summary=summary,captures=out)


def epochs(folder):
    if not (folder/'times.csv').exists():
        return []
    times={r['file']:r for r in csv.DictReader((folder/'times.csv').open())}
    out=[]
    for path in sorted(folder.glob('e*.csv')):
        r=next(samples(path))
        t=times[path.name]
        vals={cam:int(r[next(k for k in r if f'v19_cap{cam}_desc_epoch' in k)],16) for cam in [0,4]}
        out.append(dict(file=path.name, before_ms=int(t['before_ms']), after_ms=int(t['after_ms']), epochs=vals))
    for prev,cur in zip(out,out[1:]):
        dt=((cur['before_ms']+cur['after_ms'])-(prev['before_ms']+prev['after_ms']))/2000
        cur['epoch_label_slope_per_s']={cam:((cur['epochs'][cam]-prev['epochs'][cam])%256)/dt for cam in [0,4]}
    return out


def trigger_segments(folder):
    captures=[]
    combined=[]
    for path in sorted(folder.glob('trigger_segments_*.csv')):
        rows=list(samples(path))
        col=next(k for k in rows[0] if 'eo_cam_rate_word' in k)
        starts=[r for r in rows if r['Sample in Window']=='0']
        assert len(starts)==64 and all(r['eo_fpga_trigger_start']=='1' for r in starts)
        # Sample after the trigger stretcher, synchronizer and word register update.
        selected=[r for r in rows if r['Sample in Window']=='32']
        assert len(selected)==64
        ticks=[field(int(r[col],16),55,42) for r in selected]
        combined.extend(ticks)
        captures.append(dict(file=path.name, ticks=ticks,
                             free_running=sorted({int(r['eo_trigger_free_running'],16) for r in selected})))
    if not combined:
        return {}
    mean_us=statistics.mean(combined)*TICK_US
    return dict(captures=captures,intervals=len(combined),histogram=dict(Counter(combined)),
                mean_us=mean_us,reciprocal_mean_hz=1e6/mean_us)


if __name__=='__main__':
    results=[]
    for arg in sys.argv[1:]:
        folder=Path(arg)
        result=rate_review(folder)
        result['epoch_labels']=epochs(folder)
        result['trigger_segments']=trigger_segments(folder)
        results.append(result)
        print(json.dumps(result['summary'],indent=2))
        if result['epoch_labels']:
            print('EPOCH_LABELS',json.dumps(result['epoch_labels']))
    Path(sys.argv[-1], 'review_analysis.json').write_text(json.dumps(results,indent=2)+'\n')
