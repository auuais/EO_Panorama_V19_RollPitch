"""Record explicitly reviewed ILA OSD evidence, never infer settings from ACKs."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('stage',choices=['freeze','live']);p.add_argument('--visually-confirmed',action='store_true');a=p.parse_args()
assert a.visually_confirmed,'Inspect all five camera images first'
root=Path.cwd()/'captures/eo_sync_trig30_exp60_20261009'
folders=['baseline_exposure','baseline_trigger','baseline_format','freeze_on' if a.stage=='freeze' else 'freeze_off']
evidence=[]
for folder in folders:
    image=root/folder/'contact.png';assert image.exists()
    evidence.append(dict(file=str(image.relative_to(root)),sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
state=dict(verified_at=datetime.datetime.now().astimezone().isoformat(),all_camera_readbacks_verified=True,physical_cameras=[2,3,4,5,6],
           verification='Direct visual review of all five camera OSD crops in each contact sheet',format='1080p60',shutter='1/60 s',gain_db=0,dnr='2D+3D',mode='ExtTrig',exttrig_delay_ms=0,strobe_delay_ms=0,strobe_width_ms=1,trigger_polarity='OFF',strobe_polarity='OFF',freeze='ON' if a.stage=='freeze' else 'OFF',menus_closed_after_readback=True,
           diagnostic_bitstream_sha256='4bc5272d453f505f14399f305149ac6a317848bb6761116a3e374ee0e5f54006',phase_taps=[336,280,308,280,322],phases=['rising']*5,trigger_hz=30,evidence=evidence)
(root/('pretest_verified.json' if a.stage=='freeze' else 'live_state_verified.json')).write_text(json.dumps(state,indent=2)+'\n')
print('Recorded reviewed '+a.stage+' settings')
