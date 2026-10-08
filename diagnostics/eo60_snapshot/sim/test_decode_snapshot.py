"""Independent full-image fixture, sequence wrap and missing-packet checks."""
import csv
import hashlib
import importlib.util
import tempfile
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('decoder',Path(__file__).resolve().parents[1]/'scripts/decode_snapshot.py')
decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
with tempfile.TemporaryDirectory() as temp:
    folder=Path(temp)
    yy,xx=np.indices((540,960))
    expected=((xx*3+yy*7)%256).astype(np.uint8)
    frames=[expected,expected.copy()]
    frames[1][100,200]^=127
    with (folder/'snapshot.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['snapshot_pixels[63:0]','snapshot_meta[31:0]','snapshot_control[1:0]','eo60_snapshot_meta[31:0]','eo60_snapshot_control[1:0]'])
        for seq,frame in zip([32767,0],frames):
            for y in range(540):
                for g in range(120):
                    meta=f'{(seq<<17)|(y<<7)|g:x}';control=3 if y==g==0 else 1
                    w.writerow([frame[y,g*8:g*8+8].tobytes().hex(),meta,control,meta,control])
    result=decoder.decode(folder)
    assert [r['sha256'] for r in result['frames']]==[hashlib.sha256(f.tobytes()).hexdigest() for f in frames]
    assert result['comparison']['changed_pixels']==1
    lines=(folder/'snapshot.csv').read_text().splitlines()
    (folder/'snapshot.csv').write_text('\n'.join(lines[:-1])+'\n')
    try:decoder.decode(folder)
    except ValueError as exc:assert 'Expected two complete frames' in str(exc)
    else:raise AssertionError('Missing packet was accepted')
    print('PASS: pixel coordinates/byte order, sequence wrap, one-pixel change, missing-packet rejection')
