import contextlib
import io
import json
import shutil
import sys
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'diagnostics/eo_sync/scripts'))
from collect_study import collect
prior=root/'captures/eo_sync_20261008'
target=root/'.tmpCRC/eo_sync_trig30_20261008/collector_regression';target.mkdir(exist_ok=True)
config=json.loads((prior/'study_config.json').read_text(encoding='utf-8'))
config['conditions']=[c for c in config['conditions'] if c['id'] in ['60_freeze','60_trigger_a']]
for c in config['conditions']:
    out=target/c['id'];out.mkdir(exist_ok=True)
    for p in (prior/c['id']).glob('events_*.csv'):shutil.copyfile(p,out/p.name)
    shutil.copyfile(prior/c['id']/'phase_checks.txt',out/'phase_checks.txt')
path=target/'config.json'
results=[]
for expected_rate in [60,30]:
    config['protocol']['trigger_hz']=expected_rate
    path.write_text(json.dumps(config))
    with contextlib.redirect_stdout(io.StringIO()):result=collect(path)
    checks=[c['trigger_verified'] for c in result['conditions']]
    assert checks==[expected_rate==60]*2,checks
    results.append(dict(expected_hz=expected_rate,captured_hz=60,verified=checks))
print(json.dumps(results))
