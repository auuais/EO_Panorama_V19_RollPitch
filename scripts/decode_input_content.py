"""Decode segmented receiver CRC captures; never compare across missed rasters."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def decode(folder):
    records=[]
    incomplete=0
    for path in sorted(folder.glob('events_*.csv')):
        with path.open(newline='') as f:
            reader=csv.DictReader(f)
            col=next(k for k in reader.fieldnames if 'eo_content_event_word' in k)
            groups=defaultdict(dict)
            for row in reader:
                try: word=int(row[col],16)
                except (ValueError,TypeError): continue
                if not word>>63: continue
                cam=(word>>60)&7; kind=(word>>57)&7
                seq=(word>>41)&65535; flags=(word>>33)&255
                if cam>5 or kind>4: raise ValueError(f'Bad event {word:x}')
                key=(cam,seq)
                packet=(flags,word&0xffffffff)
                if kind in groups[key] and groups[key][kind]!=packet:
                    raise ValueError(f'Conflicting packet {path} {key} {kind}')
                groups[key][kind]=packet
            for (cam,seq),g in groups.items():
                if set(g)!=set(range(5)):
                    incomplete+=1;continue
                if len({p[0] for p in g.values()})!=1:
                    raise ValueError('Flags changed within one mailbox')
                records.append(dict(file=path.name,cam=cam+1,seq=seq,flags=g[0][0],
                                    crc=g[0][1],roi_crc=g[1][1],pixels=g[2][1],
                                    lines=(g[3][1]>>12)&4095,eavs=g[3][1]&4095,
                                    tick=g[4][1]))
    summary={'complete_reports':len(records),'incomplete_mailboxes':incomplete,'cameras':{}}
    for cam in range(1,7):
        rr=[r for r in records if r['cam']==cam]
        pairs=[]; missing=0; ticks=0; seqsum=0
        for a,b in zip(rr,rr[1:]):
            ds=(b['seq']-a['seq'])&65535
            dt=(b['tick']-a['tick'])&0xffffffff
            if not ds: continue
            if not dt or ds>32768: raise ValueError('Ordering or capture interval invalid')
            missing+=ds-1; ticks+=dt;seqsum+=ds
            if ds==1: pairs.append((a,b))
        stats={}
        for key in ['crc','roi_crc']:
            changed=sum(a[key]!=b[key] for a,b in pairs)
            # Count spacing only inside uninterrupted sequences. This avoids
            # endpoint bias from estimating rate with many short ILA blocks.
            spacing=Counter();last_change=None
            for a,b in zip(rr,rr[1:]):
                if ((b['seq']-a['seq'])&65535)!=1:
                    last_change=None
                    continue
                if a[key]!=b[key]:
                    if last_change is not None:
                        spacing[(b['seq']-last_change)&65535]+=1
                    last_change=b['seq']
            stats[key]=dict(consecutive_pairs=len(pairs),changed=changed,
                            duplicate=len(pairs)-changed,
                            change_fraction=changed/len(pairs) if pairs else None,
                            estimated_updates_hz=(changed/len(pairs)*seqsum*74250000/ticks)
                            if pairs and ticks else None,
                            distinct_crc_states=len({r[key] for r in rr}),
                            change_spacing_rasters=dict(spacing))
        summary['cameras'][cam]=dict(reports=len(rr),missed_between_reports=missing,
                                    raster_hz=seqsum*74250000/ticks if ticks else None,
                                    flags=dict(Counter(r['flags'] for r in rr)),
                                    geometry=dict(Counter(f"{r['pixels']} pixels, {r['lines']} active lines, {r['eavs']} EAV" for r in rr)),
                                    content=stats)
    if records:
        with (folder/'decoded_frames.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    (folder/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path)
    decode(ap.parse_args().folder)
