"""Record restoration after the operator has viewed every new OSD readback."""
import datetime
import hashlib
import json
import sys
from pathlib import Path
if '--visually-confirmed' not in sys.argv:raise ValueError('View all five cameras and every menu before recording verification')
root=Path.cwd();source=root/'captures/eo_sync_trig30_20261008';folder=source/'restoration'
state=json.loads((source/'initial_state_verified.json').read_text())
for initial,final in [('initial_display.txt','display.txt'),('initial_pose.txt','pose.txt')]:
    assert (source/initial).read_text().strip()==(folder/final).read_text().strip(),f'Restored {final} differs'
bit=root/'builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit'
digest=hashlib.sha256(bit.read_bytes()).hexdigest();assert digest==state['operational_bitstream_sha256']
log=root/'.tmpCRC/eo_sync_trig30_20261008/restore_operational.log'
assert 'PROGRAMMED='+bit.as_posix() in log.read_text()
readbacks=[]
for cam in range(2,7):
    for section in ['trigger','exposure','image','format','closed']:
        p=folder/f'cam{cam}_{section}.png'
        readbacks.append(dict(camera=cam,section=section,image=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
state.update(date_kst=datetime.datetime.now().astimezone().date().isoformat(),
             verified_at=datetime.datetime.now().astimezone().isoformat(),all_camera_readbacks_verified=True,
             verification='Direct visual inspection of all five cameras in trigger, exposure, image, format and closed-menu USB contact sheets',
             evidence_folder='restoration',program_log=str(log),readbacks=readbacks,display_matches_initial=True,pose_matches_initial=True,
             menus_closed=True,configuration_flash_written=False,osd_save_or_defaults_used=False)
(folder/'verified_state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Restoration verified; display and pose match initial readbacks.')
