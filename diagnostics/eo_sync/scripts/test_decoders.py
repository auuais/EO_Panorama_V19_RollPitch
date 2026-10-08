import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from decode_events import EXPECTED, FIELDS, SIGNATURE, analyze_block, circular_span, read_events, unwrap_offsets
from decode_snapshot import decode


class EventTests(unittest.TestCase):
    def test_wrap_span(self):
        self.assertEqual(circular_span([0, -2, -1, 1, 2], 1000), 4)
        self.assertEqual(circular_span([0, 200, 400, 600, 800], 1000), 800)
        self.assertEqual(unwrap_offsets([490, -490, -470], 1000), [490, 510, 530])

    def test_alignment_and_different_sequence_origins(self):
        events = []
        for frame in range(20):
            for camera in range(2, 7):
                events.append(dict(block='test', kind=1, camera=camera, phase='falling',
                                   tick=frame*900000+(camera-2)*27, sequence=(frame+camera*91)&65535,
                                   geometry_valid=True, timing_valid=True, full_crc=frame//2, roi_crc=frame//2))
        analysis = analyze_block(sorted(events, key=lambda e:e['tick']))
        self.assertEqual(analysis['spans']['raster']['median'], 4)
        self.assertEqual(analysis['spans']['roi_crc']['median'], 4)
        self.assertEqual(analysis['cameras'][0]['raster_hz'], 30)
        self.assertEqual(analysis['cameras'][0]['sequence_gaps'], 0)
        self.assertEqual(analysis['cameras'][0]['roi_changes'], 9)
        self.assertEqual(analysis['matching']['raster']['offsets'][6]['drift_us_per_second'], 0)

    def test_csv_integrity_and_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'events_000.csv'
            names = ['event_metadata[63:0]', 'event_payload[255:0]', 'event_valid[0:0]',
                     'event_overruns[15:0]', 'event_signature[31:0]']
            values = dict(EXPECTED, sequence=65535, full_crc=123, roi_crc=456)
            payload = sum(values.get(k, 0)<<shift for k, shift, _ in FIELDS)
            def save(overruns=0, signature=SIGNATURE):
                with path.open('w', newline='') as f:
                    w=csv.writer(f);w.writerow(names);w.writerow(['HEX']*5)
                    w.writerow([f'{(1<<56)|(9<<48)|12345:x}', f'{payload:x}', '1', f'{overruns:x}', f'{signature:x}'])
            save()
            event=read_events(path)[0]
            self.assertEqual(event['camera'], 6)
            self.assertEqual(event['phase'], 'falling')
            self.assertTrue(event['geometry_valid'])
            self.assertEqual(event['sequence'], 65535)
            save(overruns=1)
            with self.assertRaises(ValueError):read_events(path)
            save(signature=0)
            with self.assertRaises(ValueError):read_events(path)


class SnapshotTests(unittest.TestCase):
    def test_known_pixels_and_missing_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            path=folder/'snapshot.csv'
            def save(skip=False):
                with path.open('w', newline='') as f:
                    w=csv.writer(f)
                    w.writerow(['snapshot_pixels[63:0]', 'snapshot_meta[31:0]', 'snapshot_control[1:0]'])
                    w.writerow(['HEX']*3)
                    for y in range(448):
                        for group in range(64):
                            if skip and (y, group)==(200, 30):continue
                            pixels=bytes(((group*8+x)*2+512+y*2+128)&255 for x in range(8))
                            w.writerow([pixels.hex(), f'{(37<<17)|(y<<7)|group:x}', '3' if (y,group)==(0,0) else '1'])
            save()
            with patch('builtins.print'):result=decode(folder)
            im=np.array(Image.open(folder/result['frames'][0]['file']))
            self.assertEqual(im.shape, (448,512))
            for y,x in [(0,0),(200,255),(447,511)]:self.assertEqual(int(im[y,x]), (x*2+512+y*2+128)&255)
            save(skip=True)
            with self.assertRaises(ValueError):decode(folder)


if __name__=='__main__':unittest.main()
