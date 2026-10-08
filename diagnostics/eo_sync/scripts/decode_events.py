"""Decode synchronization ILA events and compare five cameras on one timebase.

No exposure-synchronization claim is inferred from raster or CRC alignment.
CRC changes are descriptive until separately qualified with a Freeze control.
"""
import argparse
import bisect
import csv
import hashlib
import json
import statistics
from pathlib import Path

REF_HZ = 27_000_000
SIGNATURE = 0xE05C0001
FIELDS = [('full_crc', 0, 32), ('roi_crc', 32, 32), ('pixels', 64, 22),
          ('lines', 86, 12), ('sequence', 98, 16), ('eavs', 114, 12),
          ('flags', 126, 8), ('bad_xy', 134, 12), ('bad_c', 146, 12),
          ('frame_clocks', 160, 32), ('line_max', 192, 16), ('line_min', 208, 16)]
EXPECTED = dict(pixels=2073600, lines=1080, eavs=1125, flags=3, bad_xy=0,
                bad_c=0, frame_clocks=2475000, line_max=2200, line_min=2200)


def stats(values):
    if not values:
        return dict(n=0, min=None, median=None, p95=None, max=None, mean=None)
    v = sorted(values)
    x = .95 * (len(v)-1)
    lo = int(x)
    p95 = v[lo] + (v[min(lo+1, len(v)-1)]-v[lo])*(x-lo)
    return dict(n=len(v), min=v[0], median=statistics.median(v), p95=p95,
                max=v[-1], mean=statistics.mean(v))


def circular_span(offsets, period):
    """Length of shortest arc containing all phases; invariant to wrap origin."""
    phases = sorted(x % period for x in offsets)
    gaps = [b-a for a, b in zip(phases, phases[1:])]
    gaps.append(phases[0]+period-phases[-1])
    return period-max(gaps)


def read_events(path):
    events = []
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        columns = {}
        for name in ['metadata', 'payload', 'valid', 'overruns', 'signature']:
            matches = [k for k in reader.fieldnames if k.startswith('event_'+name+'[')]
            if len(matches) != 1:
                raise ValueError(('Missing/ambiguous alias', name, reader.fieldnames))
            columns[name] = matches[0]
        for index, row in enumerate(reader):
            # Vivado places exactly one radix declaration after the header.
            if index == 0 and row[columns['metadata']].strip().upper() == 'HEX':
                continue
            try:
                v = {k: int(row[col], 16) for k, col in columns.items()}
            except (ValueError, TypeError) as e:
                raise ValueError(('Malformed event', index, row)) from e
            if v['valid'] != 1 or v['signature'] != SIGNATURE or v['overruns']:
                raise ValueError(('Capture integrity failure', index, v))
            meta = v['metadata']
            kind, channel, tick = meta >> 56, (meta >> 48) & 255, meta & ((1 << 48)-1)
            if (kind == 1 and channel not in range(10)) or (kind in [2, 3] and channel != 10) or kind not in [1, 2, 3]:
                raise ValueError(('Unknown event', kind, channel))
            item = dict(block=path.stem, sample=index, kind=kind, channel=channel, tick=tick)
            if kind == 1:
                payload = v['payload']
                item.update({name: (payload >> shift) & ((1 << width)-1) for name, shift, width in FIELDS})
                item.update(camera=channel//2+2, phase=['rising', 'falling'][channel % 2])
                item['geometry_valid'] = all(item[k] == value for k, value in EXPECTED.items())
            events.append(item)
    if not events:
        raise ValueError('Empty capture')
    # Serializer order is not temporal order when several channels arrive together.
    return sorted(events, key=lambda x: (x['tick'], x['channel'], x['sample']))


def analyze_block(events, phase='falling'):
    camera_stats, streams = [], {}
    for camera in range(2, 7):
        rows = [e for e in events if e.get('camera') == camera and e.get('phase') == phase]
        valid = [e for e in rows if e['geometry_valid']]
        gaps = sum(((b['sequence']-a['sequence']) & 65535) != 1 for a, b in zip(rows, rows[1:]))
        periods = [b['tick']-a['tick'] for a, b in zip(valid, valid[1:])
                   if ((b['sequence']-a['sequence']) & 65535) == 1]
        changes = {k: [] for k in ['full_crc', 'roi_crc']}
        adjacent = 0
        for a, b in zip(rows, rows[1:]):
            if a['geometry_valid'] and b['geometry_valid'] and ((b['sequence']-a['sequence']) & 65535) == 1:
                adjacent += 1
                for key in changes:
                    if a[key] != b[key]:
                        changes[key].append(b)
        duration = (valid[-1]['tick']-valid[0]['tick'])/REF_HZ if len(valid)>1 else 0
        camera_stats.append(dict(camera=camera, phase=phase, records=len(rows), valid=len(valid),
                                 sequence_gaps=gaps, adjacent_pairs=adjacent, duration_s=duration,
                                 raster_hz=REF_HZ/statistics.mean(periods) if periods else None,
                                 period_us=stats([p/27 for p in periods]),
                                 full_changes=len(changes['full_crc']), roi_changes=len(changes['roi_crc']),
                                 full_change_hz=len(changes['full_crc'])/duration if duration else None,
                                 roi_change_hz=len(changes['roi_crc'])/duration if duration else None))
        streams[camera] = dict(raster=valid, **changes)
    output = dict(cameras=camera_stats, cohorts={}, spans={})
    for series in ['raster', 'full_crc', 'roi_crc']:
        anchors = streams[2][series]
        if len(anchors) < 3:
            output['cohorts'][series] = []
            output['spans'][series] = stats([])
            continue
        periods = [b['tick']-a['tick'] for a, b in zip(anchors, anchors[1:])]
        period = statistics.median(periods)
        ticks = {c: [e['tick'] for e in streams[c][series]] for c in range(2, 7)}
        cohorts = []
        for anchor in anchors[1:-1]:
            matched = {2: anchor['tick']}
            for c in range(3, 7):
                times = ticks[c]
                pos = bisect.bisect_left(times, anchor['tick'])
                candidates = times[max(0, pos-1):pos+1]
                if not candidates:
                    break
                candidate = min(candidates, key=lambda t: abs(t-anchor['tick']))
                if abs(candidate-anchor['tick']) > .55*period:
                    break
                matched[c] = candidate
            if len(matched) != 5:
                continue
            offsets = {c: matched[c]-anchor['tick'] for c in range(2, 7)}
            cohort = dict(block=events[0]['block'], phase=phase, series=series,
                          anchor_tick=anchor['tick'], period_ticks=period,
                          span_us=circular_span(list(offsets.values()), period)/27,
                          nearest_span_us=(max(offsets.values())-min(offsets.values()))/27)
            for c in range(2, 7):
                cohort[f'cam{c}_tick'] = matched[c]
                cohort[f'cam{c}_offset_us'] = offsets[c]/27
            cohorts.append(cohort)
        output['cohorts'][series] = cohorts
        output['spans'][series] = stats([c['span_us'] for c in cohorts])
    for kind, name in [(2, 'trigger_rise'), (3, 'trigger_fall')]:
        t = [e['tick'] for e in events if e['kind'] == kind]
        output[name+'_period_us'] = stats([(b-a)/27 for a, b in zip(t, t[1:])])
    edge_events = [e for e in events if e['kind'] in [2, 3]]
    output['trigger_high_us'] = stats([(b['tick']-a['tick'])/27 for a, b in zip(edge_events, edge_events[1:])
                                        if a['kind'] == 2 and b['kind'] == 3])
    return output


def write_csv(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(rows)


def decode(folder):
    blocks, decoded, cohorts = [], [], []
    for path in sorted(folder.glob('events_*.csv')):
        events = read_events(path)
        decoded.extend(events)
        block = dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                     duration_s=(events[-1]['tick']-events[0]['tick'])/REF_HZ, events=len(events), phases={})
        for phase in ['rising', 'falling']:
            analysis = analyze_block(events, phase)
            for rows in analysis.pop('cohorts').values():
                cohorts.extend(rows)
            block['phases'][phase] = analysis
        blocks.append(block)
    if not blocks:
        raise ValueError('No event CSV files found')
    result = dict(reference_hz=REF_HZ, timestamp_quantum_ns=1e9/REF_HZ, blocks=blocks,
                  definition='Shortest circular arc containing five nearest camera event phases; camera 2 reference.',
                  limits='Raster timing and CRC-change timing do not measure physical exposure timing. CRC requires Freeze qualification.')
    (folder/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    write_csv(folder/'decoded_events.csv', decoded)
    write_csv(folder/'cohorts.csv', cohorts)
    for block in blocks:
        a = block['phases']['falling']
        print(json.dumps(dict(file=block['file'], duration_s=block['duration_s'], cameras=a['cameras'], spans=a['spans'])))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    decode(parser.parse_args().folder)
