"""Publish the verified report and clarify the previous experiment's provenance."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path('E:/Xylinx/EO_Panorama_V19_RollPitch')
SCRATCH = ROOT / '.tmpCRC/eo_dnr_all5_20261009'
REPORT = 'EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx'
SOURCE = ROOT / 'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99' / REPORT
DEST = ROOT / 'docs/eo_sync_evidence' / REPORT
OLD = ROOT / 'docs/eo_sync_evidence/dnr_cam2_20261009'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

validation = json.loads((SCRATCH / 'saved_workbook_validation.json').read_text())
assert validation['all_new_formulas_and_caches_verified']
assert not validation['formula_errors'] and not validation['unintended_style_changes']
assert digest(SOURCE) == validation['workbook_sha256']
assert digest(DEST) == digest(SCRATCH / 'report_before.xlsx'), 'Tracked report changed'

manifest = json.loads((OLD / 'manifest.json').read_text())
for item in manifest['files']:
    p = OLD / item['path']
    assert p.stat().st_size == item['size'] and digest(p) == item['sha256'], item['path']

readme = OLD / 'README.md'
text = readme.read_text(encoding='utf-8')
old = 'The latest workbook EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx was not edited; SHA-256 remains cd7dc5ae1e5fc248c90c3675ba9eb918822012ee6fe68619acfecc752879a036.'
new = ('The workbook was left unchanged when this single-camera experiment completed '
       '(SHA-256 cd7dc5ae1e5fc248c90c3675ba9eb918822012ee6fe68619acfecc752879a036). '
       'The later all-five DNR study in [dnr_all5_20261009](../dnr_all5_20261009/README.md) '
       'adds both experiments to the consolidated workbook '
       'EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx. '
       'The pre-edit workbook is retained in that study\'s report_provenance directory.')
assert text.count(old) == 1
text = text.replace('## Restoration and unchanged report', '## Restoration and report provenance')
readme.write_text(text.replace(old, new), encoding='utf-8')
for item in manifest['files']:
    if item['path'] == 'README.md':
        item.update(size=readme.stat().st_size, sha256=digest(readme))
manifest['total_bytes'] = sum(item['size'] for item in manifest['files'])
manifest['updated_at'] = datetime.now().astimezone().isoformat()
(OLD / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
shutil.copy2(SOURCE, DEST)
assert digest(DEST) == validation['workbook_sha256']
print(json.dumps(dict(report=str(DEST), sha256=digest(DEST), historical_manifest_files=len(manifest['files']))))
