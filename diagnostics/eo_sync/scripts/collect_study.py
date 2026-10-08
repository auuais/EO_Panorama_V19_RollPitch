"""Consolidate declared experimental conditions without joining capture gaps."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from decode_events import analyze_block, read_events, stats, REF_HZ


def collect(config_path, partial=False):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    root = config_path.parent
    conditions, camera_rows, raster_rows, selected_events, control_rows = [], [], [], [], []
    by_id = {}
    for condition in config['conditions']:
        folder = root/condition['id']
        files = sorted(folder.glob('events_*.csv'))
        if not files:
            if partial:continue
            raise ValueError(('Missing condition', condition['id']))
        if len(files) != condition['blocks']:
            raise ValueError(('Incorrect block count', condition['id'], len(files)))
        if 'phase_taps' in condition:
            taps=condition['phase_taps']
            if len(taps)!=5 or any(not isinstance(t,int) or not 0<=t<448 for t in taps):
                raise ValueError('Invalid phase targets in study configuration')
            expected=sum(t<<(9*i) for i,t in enumerate(taps))
            lines=(folder/'phase_checks.txt').read_text().splitlines()
            labels=['before_capture']+[f'after_block_{i}' for i in range(condition['blocks'])]
            if len(lines)!=len(labels):raise ValueError('Missing phase-clock checks')
            for label,line in zip(labels,lines):
                fields=line.split();word=int(fields[-2],16)
                if fields[0]!=label or (word&((1<<45)-1))!=expected or ((word>>45)&31)!=31 or word>>50:
                    raise ValueError(('Phase-clock qualification failed',condition['id'],line))
        item = dict(condition, blocks_detail=[], camera_rows=[], series={s:[] for s in ['raster','full_crc','roi_crc']})
        for path in files:
            events = read_events(path)
            analysis = analyze_block(events, condition['phases'])
            block = dict(id=path.stem, file=str(path.relative_to(root)),
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         duration_s=(events[-1]['tick']-events[0]['tick'])/REF_HZ,
                         trigger_period_us=analysis['trigger_fall_period_us'],
                         trigger_high_us=analysis['trigger_high_us'])
            item['blocks_detail'].append(block)
            for phase in ['rising','falling']:
                a = analyze_block(events, phase)
                for cam in a['cameras']:
                    row = dict(condition=condition['id'], format_fps=condition['format_fps'], mode=condition['mode'],
                               control=condition['control'], block=path.stem, build=condition['build'],
                               selected=phase==condition['phases'][cam['camera']-2], **cam)
                    row['source_file'] = str(path.relative_to(root))
                    row['source_sha256'] = block['sha256']
                    row['phase_tap'] = condition.get('phase_taps',[None]*5)[cam['camera']-2]
                    row['control_id'] = condition.get('control_id',condition['id'])
                    offset_analysis = analysis if row['selected'] else a
                    offset = offset_analysis['matching']['raster'].get('offsets',{}).get(cam['camera'],{})
                    row['offset_median_us'] = offset.get('unwrapped_offset_us',{}).get('median')
                    row['drift_us_per_second'] = offset.get('drift_us_per_second')
                    camera_rows.append(row)
                    if condition['control']:
                        control_rows.append(row)
            for cam in analysis['cameras']:
                offset = analysis['matching']['raster'].get('offsets',{}).get(cam['camera'],{})
                cam['offset_median_us'] = offset.get('unwrapped_offset_us',{}).get('median')
                cam['drift_us_per_second'] = offset.get('drift_us_per_second')
                item['camera_rows'].append(dict(block=path.stem,**cam))
            for series, rows in analysis['cohorts'].items():
                item['series'][series].extend(rows)
                if series=='raster' and not condition['control']:
                    for row in rows:
                        # Independent rotation-based check of the shortest arc.
                        ticks=[row[f'cam{c}_tick'] for c in range(2,7)]
                        period=row['period_ticks']
                        independent=min(max((t-origin)%period for t in ticks) for origin in ticks)/27
                        if abs(independent-row['span_us'])>1e-7:
                            raise ValueError(('Circular span verification failed', row, independent))
                        raster_rows.append(dict(condition=condition['id'], format_fps=condition['format_fps'], mode=condition['mode'], **row))
            for event in events:
                if event['kind']==1 and event['phase']==condition['phases'][event['camera']-2]:
                    selected_events.append(dict(condition=condition['id'], **event))
        item['observed_s'] = sum(b['duration_s'] for b in item['blocks_detail'])
        item['trigger_verified'] = all(
            b['trigger_period_us']['n']>=100 and b['trigger_high_us']['n']>=100 and
            abs(b['trigger_period_us']['min']-1e6/60)<1e-6 and
            abs(b['trigger_period_us']['max']-1e6/60)<1e-6 and
            abs(b['trigger_high_us']['min']-2000)<1e-6 and
            abs(b['trigger_high_us']['max']-2000)<1e-6
            for b in item['blocks_detail'])
        item['spreads_us'] = {s:stats([r['span_us'] for r in rows]) for s,rows in item['series'].items()}
        item['timing_complete'] = all(c['records']>=100 and c['timing_valid']==c['records'] and c['sequence_gaps']==0 for c in item['camera_rows'])
        item['content_complete'] = all(c['records']>=100 and c['valid']==c['records'] and c['sequence_gaps']==0 for c in item['camera_rows'])
        if condition['control']:
            item['qualifies_full'] = item['content_complete'] and all(c['full_changes']==0 for c in item['camera_rows'])
            item['qualifies_roi'] = item['content_complete'] and all(c['roi_changes']==0 for c in item['camera_rows'])
        by_id[condition['id']] = item
        conditions.append(item)
    for item in conditions:
        if item['control']:continue
        control = by_id.get(item['control_id'])
        if not control:raise ValueError(('Missing control', item['control_id']))
        if item['build']!=control['build'] or item['phases']!=control['phases']:
            raise ValueError('Freeze control must match the measurement build and selected phases')
        if item.get('phase_taps')!=control.get('phase_taps'):
            raise ValueError('Freeze control must match the measurement clock phase targets')
        item['qualified_image_series'] = ('full_crc' if control['qualifies_full'] else 'roi_crc' if control['qualifies_roi'] else None) if item['content_complete'] else None
        item['image_spread_us'] = item['spreads_us'].get(item['qualified_image_series'])
        item['image_scope'] = {'full_crc':'Whole transmitted raster payload changes', 'roi_crc':'Central 96x96 payload changes only', None:'Image-change timing unqualified'}[item['qualified_image_series']]
    for item in conditions:
        del item['series']
    result = dict(protocol=config.get('protocol',{}), conditions=conditions, camera_rows=camera_rows,
                  controls=control_rows, raster_cohorts=raster_rows,
                  verification=dict(circular_spans_independently_verified=len(raster_rows),
                                    selected_raw_event_count=len(selected_events)))
    if 'report_notes' in config:
        result['report_notes'] = config['report_notes']
    (root/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    for name, rows in [('selected_events.csv.gz',selected_events),('raster_cohorts.csv.gz',raster_rows)]:
        with gzip.open(root/name,'wt',newline='') as f:
            fields=list(dict.fromkeys(k for row in rows for k in row))
            writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(conditions=[dict(id=c['id'], observed_s=c['observed_s'],timing_complete=c['timing_complete'],
                                         raster=c['spreads_us']['raster'],image_scope=c.get('image_scope')) for c in conditions],
                          verification=result['verification']),indent=2))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('config',type=Path)
    parser.add_argument('--partial',action='store_true')
    args=parser.parse_args();collect(args.config,args.partial)
