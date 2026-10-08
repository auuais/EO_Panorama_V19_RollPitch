"""Reconstruct directly sampled 512x448 luminance OSD crops; no interpolation."""
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
            if y>=448 or xgroup>=64:raise ValueError(('Invalid image coordinate',seq,y,xgroup))
            if bool(control&2)!=(y==0 and xgroup==0):raise ValueError('SOF/coordinate disagreement')
            frame=groups.setdefault(seq,{})
            if (y,xgroup) in frame:raise ValueError('Duplicate pixel packet')
            frame[y,xgroup]=pixels.to_bytes(8,'big')
    frames=[];images=[]
    for seq,packets in groups.items():
        if len(packets)!=28672:continue
        im=np.empty((448,512),dtype=np.uint8)
        for (y,g),pixels in packets.items():im[y,g*8:g*8+8]=list(pixels)
        file=f'frame_{seq:05d}.png';Image.fromarray(im).save(folder/file)
        frames.append(dict(sequence=seq,file=file,packets=len(packets),sha256=hashlib.sha256(im.tobytes()).hexdigest(),mean_y=float(im.mean())))
        images.append(im)
    if len(frames)!=1:raise ValueError(('Expected one complete OSD crop',[(s,len(g)) for s,g in groups.items()]))
    result=dict(width=512,height=448,original_xywh=[512,128,1024,896],
                sampling='Every second Y pixel and row of the OSD crop; no filtering',frames=frames,
                partial_frames={str(s):len(g) for s,g in groups.items() if len(g)!=28672})
    (folder/'snapshot_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='comparison'},indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);decode(p.parse_args().folder)
