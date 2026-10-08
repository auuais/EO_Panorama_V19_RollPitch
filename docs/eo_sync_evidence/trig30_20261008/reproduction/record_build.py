import hashlib
import json
from pathlib import Path
root=Path.cwd();build=root/'builds/eo_sync_20261008_r4_trig30'
files=[build/n for n in ['EoSyncTop.bit','EoSyncTop.ltx','EoSyncTop_routed.dcp','build_validation.json','build_options.tcl']]
files+=list((build/'source_snapshot/rtl').glob('*.v'))+list((build/'source_snapshot/constraints').glob('*.xdc'))
result=dict(build=str(build.relative_to(root)),revision='r4',source_commit='a9020ee',
            validation=json.loads((build/'build_validation.json').read_text()),
            files=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
(root/'captures/eo_sync_trig30_20261008/build_sha256.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['validation']))
