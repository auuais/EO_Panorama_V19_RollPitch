"""Checks acceptance and rejection using independently assembled CSV packets."""
import csv
import tempfile
import unittest
from pathlib import Path
from decode import decode

class DecodeTest(unittest.TestCase):
    def capture(self, folder, cadence=1, bad=None, drop=None, signature=0xE0600001, hz=60, trigger=60, freeze=None, frames=32):
        fields=['eo60_capture_event_word','eo60_capture_pclk_hz','eo60_capture_trigger_edges','eo60_capture_seconds','eo60_capture_signature']
        with (folder/'events_000.csv').open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(fields)
            for seq in range(frames):
                for phase in range(2):
                    flags=5 if seq==bad else 3
                    content_seq=min(seq,freeze) if freeze is not None else seq
                    values=[content_seq//cadence+100,content_seq//cadence+200,2073600,(1080<<12)|1125,
                            (0xffff0000+seq*(27000000//hz)+phase*500)&0xffffffff,2475000,(2200<<16)|2200,0]
                    for kind,value in enumerate(values):
                        if drop==(seq,phase,kind):continue
                        word=(1<<63)|(phase<<60)|(kind<<57)|(seq<<41)|(flags<<33)|value
                        writer.writerow([f'{x:x}' for x in [word,2475000*hz,trigger,3,signature]])
    def run_case(self, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);self.capture(folder,**kwargs);return decode(folder,kwargs.get('hz',60))
    def test_fresh_60_and_timestamp_wrap(self):
        result=self.run_case()
        for p in result['phases'].values():
            self.assertTrue(p['content_rate_accepted']);self.assertEqual(p['input_updates_hz'],60)
    def test_repeated_cadence(self):
        for cadence,expected in [(2,30),(4,15)]:
            result=self.run_case(cadence=cadence,frames=48)
            self.assertEqual(result['phases']['rising']['input_updates_hz'],expected)
    def test_invalid_frame_blocks_content_claim(self):
        for p in self.run_case(bad=10)['phases'].values():
            self.assertFalse(p['content_rate_accepted']);self.assertIsNone(p['input_updates_hz'])
    def test_partial_mailbox_excluded(self):
        result=self.run_case(drop=(10,0,2))
        self.assertEqual(result['excluded_partial_mailboxes'],1)
        self.assertEqual(result['phases']['rising']['reports'],31)
        self.assertEqual(result['phases']['rising']['missing_between_reports'],1)
        self.assertEqual(result['phases']['rising']['valid_adjacent_pairs'],29)
    def test_wrong_trigger_rejected(self):
        self.assertFalse(self.run_case(trigger=30)['phases']['rising']['content_rate_accepted'])
    def test_30_raster_control(self):
        self.assertEqual(self.run_case(hz=30)['phases']['rising']['input_updates_hz'],30)
    def test_wrong_signature_rejected(self):
        with self.assertRaisesRegex(ValueError,'signature'):self.run_case(signature=0)
    def test_changed_then_frozen_not_claimed_as_constant_rate(self):
        self.assertFalse(self.run_case(freeze=16)['phases']['rising']['content_rate_accepted'])

if __name__=='__main__':unittest.main()
