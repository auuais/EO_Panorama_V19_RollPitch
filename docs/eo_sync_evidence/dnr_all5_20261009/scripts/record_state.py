"""Record camera states only following direct visual inspection of ILA OSD crops."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch');OUT=ROOT/'captures/eo_dnr_all5_20261009'
p=argparse.ArgumentParser();p.add_argument('stage',choices=['initial','on_frozen','on_live','off_live','return_live','off_repeat_live','off_frozen','restored']);p.add_argument('--visually-confirmed',action='store_true',required=True);a=p.parse_args()
sections={
 'initial':['initial_format','initial_exposure','initial_image'],
 'on_frozen':['test_format','set_exposure60','test_trigger','freeze_on_on'],
 'on_live':['test_format','set_exposure60','test_trigger','freeze_off_on'],
 'off_live':['test_format','set_exposure60','test_trigger','dnr_off'],
 'return_live':['test_format','set_exposure60','test_trigger','dnr_on_return'],
 'off_repeat_live':['test_format','set_exposure60','test_trigger','dnr_off_repeat'],
 'off_frozen':['test_format','set_exposure60','test_trigger','freeze_on_off'],
 'restored':['restored_format','restored_exposure','restored_image','restored_closed']}
evidence=[]
for section in sections[a.stage]:
 for c in range(2,7):
  folder=OUT/section/f'cam{c}';frame=json.loads((folder/'snapshot_summary.json').read_text())['frames'][0]['file'];image=folder/frame
  evidence.append(dict(camera=c,section=section,image=image.relative_to(OUT).as_posix(),sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
state=dict(verified_at=datetime.now().astimezone().isoformat(),verification='Direct visual review of all five reconstructed ILA OSD crops in every listed contact sheet',
 stage=a.stage,physical_cameras=[2,3,4,5,6],all_camera_readbacks_verified=True,
 format='1080p30' if a.stage in ['initial','restored'] else '1080p60',shutter='1/240 s' if a.stage in ['initial','restored'] else '1/60 s',gain_db=0,
 dnr='OFF' if a.stage in ['off_live','off_repeat_live','off_frozen'] else '2D+3D',freeze='ON' if a.stage in ['on_frozen','off_frozen'] else 'OFF',
 menus_closed_after_snapshot=True,camera1='No camera 1 OSD or parameter commands sent',evidence=evidence)
if a.stage not in ['initial','restored']:state.update(mode='ExtTrig',exttrig_delay_ms=0,strobe_delay_ms=0,strobe_width_ms=1,trigger_polarity='OFF',strobe_polarity='OFF',trigger_hz=30,trigger_high_us=2000,phase_taps=[336,280,308,280,322],phases=['rising']*5)
if a.stage=='initial':
 state['display_selection']=int(re.search(r'current video select (\d+)',(OUT/'initial_display.txt').read_text()).group(1))
 state['initial_usb_capture_note']='The no-key USB command used --cam 6 as a metadata label; it did not select a camera. Actual display selection was EO3, independently read from the controller.'
 files=['builds/eo_sync_20261008_r2/EoSyncTop.bit','builds/eo_sync_20261008_r2/EoSyncTop.ltx','builds/eo_sync_20261008_r4_trig30/EoSyncTop.bit','builds/eo_sync_20261008_r4_trig30/EoSyncTop.ltx','builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit']
 (OUT/'build_sha256.json').write_text(json.dumps(dict(files=[dict(path=f,sha256=hashlib.sha256((ROOT/f).read_bytes()).hexdigest()) for f in files],note='Existing diagnostic builds reused; no RTL changes or rebuild.'),indent=2)+'\n',encoding='utf-8')
if a.stage=='restored':
 for name in ['display','pose']:assert (OUT/f'initial_{name}.txt').read_text().strip()==(OUT/f'final_{name}.txt').read_text().strip(),name
 assert 'PROGRAMMED='+(ROOT/'builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit').as_posix() in (ROOT/'.tmpCRC/eo_dnr_all5_20261009/restore_operational.log').read_text()
 state.update(display_matches_initial=True,pose_matches_initial=True,usb_scene_verified=True,display_selection=3,
  osd_save_or_defaults_used=False,configuration_flash_programmed=False,mode_only_route_reapplied=True,mcu_mode_flash_written=True,
  usb_image='final_usb.png',usb_sha256=hashlib.sha256((OUT/'final_usb.png').read_bytes()).hexdigest())
target=OUT/(a.stage+'_state_verified.json');assert not target.exists();target.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8');print(target)
