"""Read-only evidence, report-copy and optional Git-index byte checks."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('E:/Xylinx/EO_Panorama_V19_RollPitch')
parser = argparse.ArgumentParser()
parser.add_argument('--staged', action='store_true')
args = parser.parse_args()
archives = [ROOT / 'docs/eo_sync_evidence' / name for name in ['dnr_cam2_20261009', 'dnr_all5_20261009']]
checked = 0
total = 0
for directory in archives:
    manifest = json.loads((directory / 'manifest.json').read_text())
    expected = {item['path'] for item in manifest['files']}
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()} - {'manifest.json'}
    assert expected == actual, (directory, expected ^ actual)
    assert manifest['total_bytes'] == sum(item['size'] for item in manifest['files'])
    for item in manifest['files']:
        data = (directory / item['path']).read_bytes()
        assert len(data) == item['size']
        assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
        checked += 1
        total += len(data)

directory = archives[1]
study = json.loads((directory / 'study.json').read_text())
for observation in study['camera_rows']:
    data = (directory / observation['source_file']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == observation['source_sha256']
for p in directory.glob('*_state_verified.json'):
    for item in json.loads(p.read_text())['evidence']:
        assert hashlib.sha256((directory / item['image']).read_bytes()).hexdigest() == item['sha256']

name = 'EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx'
report = ROOT / 'docs/eo_sync_evidence' / name
validation = json.loads((directory / 'report_provenance/saved_workbook_validation.json').read_text())
data = report.read_bytes()
assert hashlib.sha256(data).hexdigest() == validation['workbook_sha256']
assert data == (ROOT / 'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99' / name).read_bytes()

staged = 0
if args.staged:
    paths = [p.relative_to(ROOT).as_posix() for p in archives] + [report.relative_to(ROOT).as_posix()]
    listing = subprocess.check_output(['git', 'ls-files', '-s', '-z', '--', *paths], cwd=ROOT).decode('utf-8')
    for line in listing.split('\0'):
        if not line:
            continue
        entry, name = line.split('\t', 1)
        mode, oid, stage = entry.split()
        assert stage == '0' and mode == '100644'
        content = (ROOT / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == oid, name
        staged += 1
    assert staged == checked + 3, (staged, checked)

print(json.dumps(dict(manifest_files_checked=checked, evidence_bytes_checked=total, camera_source_hashes_checked=len(study['camera_rows']), workbook_copies_identical=True, staged_files_byte_identical=staged)))
