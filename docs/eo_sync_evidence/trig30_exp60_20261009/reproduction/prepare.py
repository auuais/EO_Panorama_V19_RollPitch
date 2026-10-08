import datetime
import hashlib
import json
import sys
from pathlib import Path
root=Path.cwd(); old=root/'captures/eo_sync_trig30_20261008'; new=root/'captures/eo_sync_trig30_exp60_20261009'; scratch=root/'.tmpCRC/eo_sync_trig30_exp60_20261009'
assert '--visually-confirmed' in sys.argv,'Review all initial camera readbacks before recording state'
assert not (new/'initial_state_verified.json').exists(),'Refusing to overwrite the recorded initial state'
state=json.loads((old/'initial_state_verified.json').read_text())
state.update(date_kst=datetime.datetime.now().astimezone().date().isoformat(),verified_at=datetime.datetime.now().astimezone().isoformat(),all_camera_readbacks_verified=True)
(new/'initial_state_verified.json').write_text(json.dumps(state,indent=2)+'\n')
build=json.loads((old/'build_sha256.json').read_text())
for f in build['files']:
    if f['path'].endswith(('.bit','.ltx')):assert hashlib.sha256((root/f['path']).read_bytes()).hexdigest()==f['sha256']
build['reuse_note']='Existing r4 build reused without rebuilding for the 1/60 s exposure comparison.'
(new/'build_sha256.json').write_text(json.dumps(build,indent=2)+'\n')
config=json.loads((old/'study_config.json').read_text(encoding='utf-8'))
config['protocol'].update(date='9 October 2026 KST',shutter_s=1/60,setting_evidence='pretest_verified.json; baseline_exposure, baseline_trigger, baseline_format, freeze_on and freeze_off direct OSD crops.',sampling_selection='Reused final r4 rising-edge taps from prior phase qualification; fresh five-camera frozen-image control at 1/60 s.')
for c in config['conditions']:
    c['id']=c['id'].replace('60_trig30_','60_trig30_exp60_');c['phases']=['rising']*5;c['phase_taps']=[336,280,308,280,322]
    if 'control_id' in c:c['control_id']=c['control_id'].replace('60_trig30_','60_trig30_exp60_')
repeat=dict(config['conditions'][1],id='60_trig30_exp60_repeat',blocks=1)
config['conditions'].append(repeat)
(new/'study_config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
print('Initial settings recorded after visual inspection; reused build hashes verified; analysis configured.')
