"""Synthetic capture: verify rates, duplicates, gaps and partial mailboxes."""
import contextlib
import csv
import io
import tempfile
from pathlib import Path
from decode_input_content import decode

with tempfile.TemporaryDirectory() as name:
    folder=Path(name)
    with (folder/'events_000.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Sample in Buffer','eo_content_event_word[63:0]'])
        w.writerow(['Radix - UNSIGNED','HEX'])
        n=0
        for seq in range(20):
            if seq==10: continue  # Real missing raster, never compare its neighbors.
            for cam in range(6):
                state=seq if cam==0 else seq//2
                values=[state,state+100,2073600,(1080<<12)|1125,seq*2475000+cam*1000]
                for kind,value in enumerate(values):
                    word=(1<<63)|(cam<<60)|(kind<<57)|(seq<<41)|(3<<33)|value
                    w.writerow([n,f'{word:016x}']);n+=1
        # A partially uploaded report must not masquerade as a complete frame.
        w.writerow([n,f'{((1<<63)|(20<<41)|(3<<33)|123):016x}'])
    with contextlib.redirect_stdout(io.StringIO()): result=decode(folder)
    assert result['complete_reports']==114 and result['incomplete_mailboxes']==1
    for cam,s in result['cameras'].items():
        assert abs(s['raster_hz']-30)<1e-9
        assert s['missed_between_reports']==1
        m=s['content']['crc']
        assert m['consecutive_pairs']==17
        assert m['changed']==(17 if cam==1 else 8)
        assert m['duplicate']==(0 if cam==1 else 9)
        assert set(m['change_spacing_rasters'])==({1} if cam==1 else {2})
print('PASS: 30 Hz, 2:1 repeats, skipped sequences, incomplete mailboxes')
