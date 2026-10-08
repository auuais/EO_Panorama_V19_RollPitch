"""Explicit camera OSD keys with durable serial evidence; no image/state inference."""
import argparse
import json
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'scripts'))
from eo_osd_evidence import KEYS, cobs
from eo_cam_power import Master, crc16_ccitt_false, find_port

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cam', type=int, choices=range(2, 7), required=True)
    parser.add_argument('--keys', nargs='+', choices=KEYS, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise RuntimeError('Refusing to overwrite evidence')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    log = dict(cam=args.cam, events=[], note='ACK is not a camera state readback; inspect the captured OSD.')
    master = Master(find_port())
    try:
        for seq, key in enumerate(args.keys, 1):
            raw = bytes([2, 5, 0, 1, seq, 0x33, args.cam, KEYS[key]])
            wire = cobs(raw+struct.pack('<H', crc16_ccitt_false(raw))+b'\x03')
            master.ser.write(wire)
            master.ser.flush()
            rx = bytearray()
            deadline = time.perf_counter()+.65
            while time.perf_counter() < deadline:
                rx.extend(master.ser.read(4096))
            log['events'].append(dict(time=datetime.now().astimezone().isoformat(), key=key, tx=wire.hex(), rx=rx.hex()))
            args.out.write_text(json.dumps(log, indent=2)+'\n')
    finally:
        master.close()
    print(args.out)

if __name__ == '__main__':
    main()
