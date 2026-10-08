"""Send explicit EO OSD remote keys and archive the resulting video screen.

Camera identifiers are 1..6. No automatic menu navigation or setting inference.
Wire format matches the firmware's sole permitted legacy command, 0x33.
"""
import argparse
import json
import struct
import time
from datetime import datetime
from pathlib import Path

import cv2
from eo_cam_power import Master, crc16_ccitt_false, find_port


KEYS={'up':1,'down':2,'left':4,'right':8,'enter':16,'back':32}


def cobs(data):
    out=bytearray([0]);idx=0;code=1
    for b in data:
        if b==0:
            out[idx]=code;idx=len(out);out.append(0);code=1
        else:
            out.append(b);code+=1
            if code==255:
                out[idx]=code;idx=len(out);out.append(0);code=1
    out[idx]=code
    return out+b'\x00'


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cam',type=int,choices=range(1,7),required=True)
    ap.add_argument('--keys',nargs='*',choices=KEYS,default=[])
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--port')
    ap.add_argument('--device',type=int,default=0)
    a=ap.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists(): raise RuntimeError('Refusing to overwrite evidence')
    events=[]
    if a.keys:
        m=Master(a.port or find_port())
        try:
            for seq,key in enumerate(a.keys,1):
                raw=bytes([2,5,0,1,seq,0x33,a.cam,KEYS[key]])
                wire=cobs(raw+struct.pack('<H',crc16_ccitt_false(raw))+b'\x03')
                m.ser.write(wire);m.ser.flush()
                rx=bytearray();deadline=time.perf_counter()+.65
                while time.perf_counter()<deadline: rx.extend(m.ser.read(4096))
                events.append(dict(time=datetime.now().astimezone().isoformat(),key=key,tx=wire.hex(),rx=rx.hex()))
        finally: m.close()
    cap=cv2.VideoCapture(a.device,cv2.CAP_DSHOW)
    try:
        cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'YUY2'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,1920);cap.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        until=time.perf_counter()+2
        ok=False
        while time.perf_counter()<until: ok,frame=cap.read()
        if not ok: raise RuntimeError('No video')
        if not cv2.imwrite(str(a.out),frame): raise RuntimeError('Saving frame failed')
    finally: cap.release()
    a.out.with_suffix('.json').write_text(json.dumps(dict(cam=a.cam,device=a.device,events=events),indent=2))
    print(str(a.out))


if __name__=='__main__': main()
