"""Archive this completed bench study and exact source hashes for Git review.

Raw event CSVs are gzip-compressed without changing their decompressed bytes.
Camera manuals and FPGA build binaries remain local and are referenced by hash.
"""
import gzip
import hashlib
import json
from pathlib import Path


def main():
    root=Path.cwd()
    source=root/'captures/eo_sync_20261008'
    target=root/'docs/eo_sync_evidence'
    study=json.loads((source/'study.json').read_text())
    restored=json.loads((source/'restoration/verified_state.json').read_text())
    if not restored['all_camera_readbacks_verified']:
        raise ValueError('Restoration is not verified')
    if len(study['conditions'])!=8 or len(study['raster_cohorts'])<10000:
        raise ValueError('Both-format comparison is incomplete')
    target.mkdir(exist_ok=True)
    records=[]
    def save(path, relative=None, compress=False):
        data=path.read_bytes()
        relative=Path(relative) if relative else path.relative_to(source)
        dest=target/relative
        if compress: dest=dest.with_name(dest.name+'.gz')
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(gzip.compress(data,compresslevel=9,mtime=0) if compress else data)
        archived=dest.read_bytes()
        records.append(dict(file=dest.relative_to(target).as_posix(),source=str(path),
                            source_bytes=len(data),source_sha256=hashlib.sha256(data).hexdigest(),
                            archive_bytes=len(archived),archive_sha256=hashlib.sha256(archived).hexdigest(),
                            encoding='gzip' if compress else 'original'))
    for name in ['study_config.json','protocol.json','build_sha256.json','build_r2_sha256.json',
                 'build_r3_sha256.json','60_state_verification.json','final_state_verification.json',
                 'initial_display.txt','initial_pose.txt','selected_events.csv.gz','raster_cohorts.csv.gz']:
        save(source/name)
    save(source/'study.json',compress=True)
    for c in study['conditions']:
        folder=source/c['id']
        for p in sorted(folder.glob('events_*.csv')):save(p,compress=True)
        for name in ['provenance.txt','phase_checks.txt','summary.json']:
            if (folder/name).exists():save(folder/name)
    for folder in sorted(source.glob('60_phase_*')):
        for name in ['phase_summary.json','phase_summary.csv']:
            if (folder/name).exists():save(folder/name)
        for p in sorted(folder.glob('phase_*/phase.txt')):save(p)
        # Frozen sweeps underpin selection/qualification and remain reproducible.
        if folder.name.startswith('60_phase_frozen'):
            for p in sorted(folder.glob('phase_*/events_*.csv')):save(p,compress=True)
    for p in sorted(source.glob('*contact.png')):save(p)
    for p in sorted(source.glob('cam*.json')):save(p)
    for name in ['60_baseline_format','60_baseline_exposure','60_baseline_trigger','60_freeze_on',
                 '60_freeze_off','60_free_mode','60_free_exposure','60_trigger_b_mode',
                 '60_trigger_b_exposure','60_final_phase','restoration']:
        folder=source/name
        for p in sorted(folder.rglob('*')):
            if p.is_file() and p.suffix in ['.png','.json','.txt']:save(p)
    for name in ['60_r1_smoke','60_r2_osd_smoke']:
        save(source/name/'summary.json')
    workbook=root/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261008.xlsx'
    save(workbook,workbook.name)
    scratch=root/'.tmpCRC/eo_sync_20261008'
    for name in ['report.mjs','report_validation.json','report_error_scan.ndjson','verify_restoration.py',
                 'saved_workbook_validation.json']:
        save(scratch/name,Path('report_source')/name)
    manifest=dict(description='Five-camera synchronization comparison, 8 October 2026 KST',files=records)
    (target/'archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Verify every archived byte and every decompressed event source hash.
    for r in records:
        data=(target/r['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==r['archive_sha256']
        if r['encoding']=='gzip':data=gzip.decompress(data)
        assert hashlib.sha256(data).hexdigest()==r['source_sha256']
    print(json.dumps(dict(files=len(records),bytes=sum(r['archive_bytes'] for r in records))))


if __name__=='__main__':main()
