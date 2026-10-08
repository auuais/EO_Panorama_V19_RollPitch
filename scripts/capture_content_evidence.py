"""Archive USB content timelines and lossless interior patches, without controls.

DirectShow device identity is supplied by the operator/enumerator. Panorama
coordinates follow the 3840x480 raster folded at physical row 480. Camera
labels are geometric expectations, not a lens-cover identity verification.
"""
import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


def stats(values, elapsed):
    starts = [0] + [i for i in range(1, len(values)) if values[i] != values[i-1]]
    runs = np.diff(starts + [len(values)]).tolist()
    unique = len(set(values))
    return dict(grabs=len(values), transitions=len(starts)-1,
                transitions_per_second=(len(starts)-1)/elapsed,
                unique_states=unique, revisits=len(starts)-unique,
                run_lengths=dict(Counter(runs)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--device', type=int, default=0)
    ap.add_argument('--identity', default='USB3 Video (DirectShow index 0)')
    ap.add_argument('--label', required=True)
    ap.add_argument('--panorama', action='store_true')
    ap.add_argument('--seconds', type=float, default=10)
    ap.add_argument('--settle', type=float, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    # Entirely inside each tile, >200 columns from seams, away from fold.
    rois = ({f'cam{i+1}_expected': (x, y, 96, 96) for i, (x,y) in enumerate(
            [(260,180),(895,180),(1535,180),(255,660),(895,660),(1530,660)])}
            if a.panorama else {'interior': (912,480,96,96),
                'upper_left': (400,160,96,96), 'upper_right': (1400,160,96,96),
                'lower_left': (300,720,96,96), 'lower_right': (1400,800,96,96)})
    cap = cv2.VideoCapture(a.device, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError('Cannot open capture device')
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUY2'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
    meta = dict(arguments=vars(a), started=datetime.now().astimezone().isoformat(),
                roi_xywh=rois, format='BGR uint8, OpenCV conversion from YUY2',
                reported_fps=cap.get(cv2.CAP_PROP_FPS),
                hash='BLAKE2b-128', clock='time.perf_counter_ns after read')
    rows, patches = [], {name: [] for name in rois}
    failures = 0
    try:
        end = time.perf_counter()+a.settle
        while time.perf_counter()<end:
            cap.read()
        t0=time.perf_counter_ns()
        while (time.perf_counter_ns()-t0)/1e9<a.seconds:
            ok, frame=cap.read()
            stamp=time.perf_counter_ns()
            if not ok or frame is None:
                failures+=1
                if failures>100: raise RuntimeError('Repeated capture failure')
                continue
            if frame.shape!=(1080,1920,3):
                raise RuntimeError(f'Unexpected raster {frame.shape}')
            row={'grab':len(rows),'elapsed_s':(stamp-t0)/1e9,
                 'full':hashlib.blake2b(frame.tobytes(),digest_size=16).hexdigest()}
            for name,(x,y,w,h) in rois.items():
                crop=frame[y:y+h,x:x+w].copy()
                patches[name].append(crop)
                row[name]=hashlib.blake2b(crop.tobytes(),digest_size=16).hexdigest()
            if not rows:
                first_frame=frame.copy()
            rows.append(row)
    finally:
        cap.release()
    if len(rows)<2: raise RuntimeError('Insufficient grabs')
    # Encoding PNGs during acquisition stalls reads and biases the measured rate.
    cv2.imwrite(str(out/'first_frame.png'),first_frame)
    cv2.imwrite(str(out/'last_frame.png'),frame)
    marked=first_frame.copy()
    for name,(x,y,w,h) in rois.items():
        cv2.rectangle(marked,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.putText(marked,name,(x,y-8),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,0),1)
    cv2.imwrite(str(out/'roi_map.png'),marked)
    elapsed=rows[-1]['elapsed_s']-rows[0]['elapsed_s']
    with (out/'timeline.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    np.savez_compressed(out/'patches.npz',**{k:np.asarray(v) for k,v in patches.items()})
    meta.update(interval_s=elapsed,failed_reads=failures,grab_hz=(len(rows)-1)/elapsed,
                metrics={name:stats([r[name] for r in rows],elapsed) for name in ['full']+list(rois)},
                mean_patch={name:float(np.asarray(v).mean()) for name,v in patches.items()})
    (out/'metadata.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2),flush=True)


if __name__=='__main__': main()
