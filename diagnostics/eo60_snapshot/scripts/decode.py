"""EO60 protocol v1. Invalid input must never become an accepted FPS result."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REF_HZ=27_000_000

def decode(folder, expected_hz=60):
    records=[];partial=0;clocks=Counter();triggers=Counter();seconds=set()
    for source in sorted(folder.glob('events_*.csv')):
        with source.open(newline='') as f:
            rows=csv.DictReader(f)
            fields=rows.fieldnames
            def field(fragment):
                matches=[k for k in fields if fragment in k]
                if len(matches)!=1:raise ValueError(f'Expected one {fragment} column: {fields}')
                return matches[0]
            event_col=field('eo60_capture_event_word');clock_col=field('eo60_capture_pclk_hz')
            trigger_col=field('eo60_capture_trigger_edges');seconds_col=field('eo60_capture_seconds')
            signature_col=field('eo60_capture_signature')
            groups=defaultdict(dict);telemetry=set()
            for row in rows:
                try:
                    word=int(row[event_col],16)
                    telemetry.add((int(row[seconds_col],16),int(row[clock_col],16),int(row[trigger_col],16)))
                except (ValueError,TypeError):continue
                if int(row[signature_col],16)!=0xE0600001:raise ValueError('Wrong EO60 protocol signature')
                if not word>>63:continue
                phase=(word>>60)&7;kind=(word>>57)&7;seq=(word>>41)&65535;flags=(word>>33)&255
                if phase>1:raise ValueError('Not an EO60 phase ID')
                packet=(flags,word&0xffffffff)
                key=(phase,seq)
                if kind in groups[key] and groups[key][kind]!=packet:raise ValueError('Conflicting mailbox packet')
                groups[key][kind]=packet
            for second,clock,trigger in telemetry:
                if second>1:clocks[clock]+=1;triggers[trigger]+=1;seconds.add(second)
            for (phase,seq),g in groups.items():
                if set(g)!=set(range(8)):partial+=1;continue
                if len({p[0] for p in g.values()})!=1:raise ValueError('Mailbox flags changed mid-packet')
                r=dict(file=source.name,phase=phase,seq=seq,flags=g[0][0],crc=g[0][1],roi_crc=g[1][1],
                       pixels=g[2][1],lines=(g[3][1]>>12)&4095,eavs=g[3][1]&4095,tick=g[4][1],
                       frame_clocks=g[5][1],line_min=g[6][1]>>16,line_max=g[6][1]&65535,
                       bad_xy=g[7][1]&4095,c_sync_bad=(g[7][1]>>12)&4095)
                r['valid']=r['flags']==3 and r['pixels']==2073600 and r['lines']==1080 and r['eavs']==1125 and r['frame_clocks']==2475000 and r['line_min']==2200 and r['line_max']==2200 and r['bad_xy']==0 and r['c_sync_bad']==0
                records.append(r)
    result=dict(protocol='EO60-v1',reference_hz=REF_HZ,expected_raster_hz=expected_hz,complete_reports=len(records),
                excluded_partial_mailboxes=partial,pclk_hz_observations=dict(clocks),trigger_hz_observations=dict(triggers),phases={})
    for phase,name in [(0,'rising'),(1,'falling')]:
        rr=[r for r in records if r['phase']==phase]
        ticks=0;seqsum=0;pairs=[];missing=0
        spacing={k:Counter() for k in ['crc','roi_crc']};last_change={k:None for k in spacing}
        runs={k:1 for k in spacing};maximum_run={k:1 for k in spacing}
        for a,b in zip(rr,rr[1:]):
            ds=(b['seq']-a['seq'])&65535;dt=(b['tick']-a['tick'])&0xffffffff
            if not ds or not dt or ds>32768:raise ValueError('Bad sequence/timestamp order')
            ticks+=dt;seqsum+=ds;missing+=ds-1
            adjacent=ds==1 and a['valid'] and b['valid']
            if adjacent:pairs.append((a,b))
            for key in spacing:
                runs[key]=runs[key]+1 if adjacent and a[key]==b[key] else 1
                maximum_run[key]=max(maximum_run[key],runs[key])
                if not adjacent:last_change[key]=None
                elif a[key]!=b[key]:
                    if last_change[key] is not None:spacing[key][(b['seq']-last_change[key])&65535]+=1
                    last_change[key]=b['seq']
        hz=seqsum*REF_HZ/ticks if ticks else None
        valid=sum(r['valid'] for r in rr)
        cadence=list(spacing['crc'])
        accepted=bool(len(rr)>=16 and valid==len(rr) and hz and abs(hz-expected_hz)<0.1 and
                      len(cadence)==1 and spacing['crc']==spacing['roi_crc'] and clocks and
                      sum(spacing['crc'].values())>=8 and all(v<=cadence[0] for v in maximum_run.values()) and
                      all(abs(c-2475000*expected_hz)<2475000*expected_hz*0.001 for c in clocks) and set(triggers)=={60})
        result['phases'][name]=dict(reports=len(rr),valid_reports=valid,invalid_reports=len(rr)-valid,
            flags=dict(Counter(r['flags'] for r in rr)),raster_starts_hz=hz,missing_between_reports=missing,
            valid_adjacent_pairs=len(pairs),crc_changed_pairs=sum(a['crc']!=b['crc'] for a,b in pairs),
            crc_repeated_pairs=sum(a['crc']==b['crc'] for a,b in pairs),spacing={k:dict(v) for k,v in spacing.items()},
            maximum_identical_run=maximum_run,
            content_rate_accepted=accepted,input_updates_hz=hz/cadence[0] if accepted else None)
    if records:
        with (folder/'decoded_frames.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--expected-raster-hz',type=int,choices=[30,60],default=60)
    a=p.parse_args();print(json.dumps(decode(a.folder,a.expected_raster_hz),indent=2))
