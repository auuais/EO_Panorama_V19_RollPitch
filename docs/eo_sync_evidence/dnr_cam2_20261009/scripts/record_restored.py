"""Record restoration only after directly viewing all listed OSD readbacks."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--visually-confirmed',action='store_true',required=True)
p.parse_args()
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'captures/eo_dnr_cam2_20261009'

def read_text(path):
    b=path.read_bytes()
    return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').strip()

for initial,final in [('initial_display.txt','final_display_verified.txt'),('initial_pose.txt','final_pose_verified.txt')]:
    assert read_text(OUT/initial)==read_text(OUT/final),(initial,final)
bit=ROOT/'builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit'
sha=hashlib.sha256(bit.read_bytes()).hexdigest()
assert sha=='d905e96d96990528a5c2098e0e018fa9d88814a18703fb0ce4f09a348b5f2cfd'
log=ROOT/'.tmpCRC/eo_dnr_cam2_20261009/restore_operational.log'
assert 'PROGRAMMED='+bit.as_posix() in read_text(log)
readbacks=[]
for section,cameras in [('format',range(2,7)),('closed',range(2,7)),
                         ('exposure',[2]),('trigger',[2]),('image',[2])]:
    for camera in cameras:
        folder=OUT/('restored_'+section)/f'cam{camera}'
        summary=json.loads((folder/'snapshot_summary.json').read_text())
        png=folder/summary['frames'][0]['file']
        readbacks.append(dict(camera=camera,section=section,
            image=png.relative_to(OUT).as_posix(),sha256=hashlib.sha256(png.read_bytes()).hexdigest()))
workbook=ROOT/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx'
workbook_sha=hashlib.sha256(workbook.read_bytes()).hexdigest()
assert workbook_sha=='cd7dc5ae1e5fc248c90c3675ba9eb918822012ee6fe68619acfecc752879a036'
data=json.loads((OUT/'comparison.json').read_text())
assert data['crc_freeze_qualification']==dict(full=True,roi=True)
for condition in data['conditions'].values():
    cam=condition['camera2']
    assert cam['records']==cam['valid'] and cam['sequence_gaps']==0
    for block in condition['blocks']:
        a=block['analysis']
        assert abs(a['trigger_fall_period_us']['min']-1e6/30)<1e-7
        assert abs(a['trigger_fall_period_us']['max']-1e6/30)<1e-7
        assert a['trigger_high_us']['min']==a['trigger_high_us']['max']==2000
state=dict(verified_at=datetime.now().astimezone().isoformat(),
    verification='Directly viewed reconstructed ILA OSD crops, then reloaded operational FPGA; viewed closed USB camera 6',
    readback_scope='All five formats and closed menus; camera 2 exposure, trigger and image settings',
    all_readbacks_verified=True,all_cameras_2_to_6_format='1080p30',
    camera2=dict(shutter='1/240 s',gain_db=0,mode='ExtTrig',exttrig_delay_ms=0,
                 strobe_delay_ms=0,strobe_width_ms=1,trigger_polarity='OFF',strobe_polarity='OFF',
                 dnr='2D+3D',freeze='OFF',sharpness=5,gamma=.45,electronic_zoom='OFF'),
    cameras_3_to_6_exposure_and_dnr='Not changed during this experiment',
    camera1='No camera 1 OSD or parameter commands sent',display_matches_initial=True,pose_matches_initial=True,
    display_selection=6,menus_closed=True,operational_bitstream_sha256=sha,
    operational_program_log=log.relative_to(ROOT).as_posix(),
    osd_save_or_defaults_used=False,configuration_flash_programmed=False,
    standard_usb_display_selection_command_used=False,mode_only_route_reapplied=True,
    mcu_mode_flash_written=True,usb_view_matches_initial=True,
    usb_final_image='final_route_restored.png',
    usb_final_image_sha256=hashlib.sha256((OUT/'final_route_restored.png').read_bytes()).hexdigest(),
    workbook_edited=False,
    workbook=workbook.relative_to(ROOT).as_posix(),workbook_sha256=workbook_sha,readbacks=readbacks)
(OUT/'restoration_verified.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
print('Restoration verified. Initial display/parameters and pose match exactly; workbook unchanged.')
