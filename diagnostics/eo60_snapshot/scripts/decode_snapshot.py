"""Reconstruct directly sampled 960x540 luminance frames; no interpolation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

def decode(folder):
    groups={}
    with (folder/'snapshot.csv').open(newline='') as f:
        reader=csv.DictReader(f)
        def field(part):
            matches=[k for k in reader.fieldnames if k.startswith(part+'[')]
            if len(matches)!=1:raise ValueError((part,reader.fieldnames))
            return matches[0]
        p,m,c=map(field,['snapshot_pixels','snapshot_meta','snapshot_control'])
        for row in reader:
            try:control=int(row[c],16);meta=int(row[m],16);pixels=int(row[p],16)
            except ValueError:continue
            if not control&1:raise ValueError('Storage qualifier allowed an invalid sample')
            seq=meta>>17;y=(meta>>7)&1023;xgroup=meta&127
            if y>=540 or xgroup>=120:raise ValueError(('Invalid image coordinate',seq,y,xgroup))
            if bool(control&2)!=(y==0 and xgroup==0):raise ValueError('SOF/coordinate disagreement')
            frame=groups.setdefault(seq,{})
            if (y,xgroup) in frame:raise ValueError('Duplicate pixel packet')
            frame[y,xgroup]=pixels.to_bytes(8,'big')
    frames=[];images=[]
    for seq,packets in groups.items():
        if len(packets)!=64800:continue
        im=np.empty((540,960),dtype=np.uint8)
        for (y,g),pixels in packets.items():im[y,g*8:g*8+8]=list(pixels)
        file=f'frame_{seq:05d}.png';Image.fromarray(im).save(folder/file)
        frames.append(dict(sequence=seq,file=file,packets=len(packets),sha256=hashlib.sha256(im.tobytes()).hexdigest(),mean_y=float(im.mean())))
        images.append(im)
    if len(frames)!=2:raise ValueError(('Expected two complete frames',[(s,len(g)) for s,g in groups.items()]))
    if (frames[1]['sequence']-frames[0]['sequence'])%32768!=1:raise ValueError('Frames not consecutive')
    diff=np.abs(images[0].astype(np.int16)-images[1].astype(np.int16))
    result=dict(width=960,height=540,sampling='Every second original Y pixel and row; no spatial or temporal filtering',
                frames=frames,partial_frames={str(s):len(g) for s,g in groups.items() if len(g)!=64800},
                comparison=dict(changed_pixels=int(np.count_nonzero(diff)),total_pixels=diff.size,
                                mean_absolute_difference=float(diff.mean()),max_absolute_difference=int(diff.max()),
                                difference_histogram=np.bincount(diff.ravel(),minlength=256).tolist()))
    (folder/'snapshot_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='comparison'},indent=2))
    print('Changed pixels:',result['comparison']['changed_pixels'],'MAD:',result['comparison']['mean_absolute_difference'])
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);decode(p.parse_args().folder)
