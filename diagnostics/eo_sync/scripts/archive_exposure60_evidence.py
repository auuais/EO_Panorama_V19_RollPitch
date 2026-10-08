"""Archive the 1/60 s, 1080p60, 30 Hz trigger follow-up and consolidated report."""
import gzip
import hashlib
import json
from pathlib import Path


def main():
    root=Path.cwd();source=root/'captures/eo_sync_trig30_exp60_20261009'
    parent=root/'docs/eo_sync_evidence';target=parent/'trig30_exp60_20261009'
    scratch=root/'.tmpCRC/eo_sync_trig30_exp60_20261009'
    study=json.loads((source/'study.json').read_text())
    restored=json.loads((source/'restoration/verified_state.json').read_text())
    assert restored['all_camera_readbacks_verified']
    live=[c for c in study['conditions'] if not c['control']]
    assert len(live)==2 and all(c['trigger_verified'] and c['content_complete'] and c['qualified_image_series'] for c in live)
    records=[]
    def save(p,relative,compress=False):
        data=p.read_bytes();dest=target/relative
        if compress:dest=dest.with_name(dest.name+'.gz')
        dest.parent.mkdir(parents=True,exist_ok=True)
        archive=gzip.compress(data,compresslevel=9,mtime=0) if compress else data
        dest.write_bytes(archive)
        records.append(dict(file=dest.relative_to(target).as_posix(),source=str(p),source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),archive_sha256=hashlib.sha256(archive).hexdigest(),archive_bytes=len(archive),encoding='gzip' if compress else 'original'))
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.name=='snapshot.csv':continue
        if p.suffix in ['.json','.png','.txt','.csv','.gz']:
            save(p,p.relative_to(source),p.suffix=='.csv' or p.name=='study.json')
    for name in ['bench.py','prepare.py','report_addendum.mjs','report_validation.json','report_error_scan.ndjson','verify_followup_workbook.py','saved_workbook_validation.json','live_metrics.py','inspect_anomalies.py','record_restored.py','record_test_state.py','program_r4.log','selected_phase.log','snapshot_rising.log','restore_operational.log','60_trig30_exp60_freeze.log','60_trig30_exp60_live.log','60_trig30_exp60_repeat.log']:
        p=scratch/name
        if p.exists():save(p,Path('reproduction')/name)
    manifest=dict(description='1080p60 / generated 30 Hz trigger / verified 1/60 s shutter / zero programmed trigger delay',reused_build_evidence='../trig30_20261008/build_checks',files=records)
    (target/'archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for item in records:
        data=(target/item['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['archive_sha256']
        if item['encoding']=='gzip':data=gzip.decompress(data)
        assert hashlib.sha256(data).hexdigest()==item['source_sha256']
    workbook=root/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx'
    data=workbook.read_bytes();(parent/workbook.name).write_bytes(data)
    old=json.loads((parent/'archive_manifest.json').read_text())
    entry=next((r for r in old['files'] if r['file']==workbook.name),None)
    if entry is None:entry=dict(file=workbook.name,encoding='original');old['files'].append(entry)
    entry.update(source=str(workbook),source_bytes=len(data),archive_bytes=len(data),source_sha256=hashlib.sha256(data).hexdigest(),archive_sha256=hashlib.sha256(data).hexdigest())
    old['exposure60_followup_manifest']='trig30_exp60_20261009/archive_manifest.json'
    (parent/'archive_manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    print(json.dumps(dict(files=len(records),bytes=sum(r['archive_bytes'] for r in records),workbook_sha256=entry['archive_sha256'])))


if __name__=='__main__':main()
