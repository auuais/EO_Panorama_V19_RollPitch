"""Archive the 1080p60 / 30 Hz follow-up without changing prior bench evidence."""
import gzip
import hashlib
import json
from pathlib import Path


def main():
    root=Path.cwd(); source=root/'captures/eo_sync_trig30_20261008'
    parent=root/'docs/eo_sync_evidence'; target=parent/'trig30_20261008'
    scratch=root/'.tmpCRC/eo_sync_trig30_20261008'
    study=json.loads((source/'study.json').read_text())
    recheck=json.loads((source/'cam6_recheck.json').read_text())
    if len(recheck['camera_rows'])!=2 or next(r for r in recheck['camera_rows'] if r['control'])['roi_changes']!=0:
        raise ValueError('Camera 6 repeat has not passed its control')
    restored=json.loads((source/'restoration/verified_state.json').read_text())
    if not restored['all_camera_readbacks_verified']:
        raise ValueError('Restoration must be verified before archiving')
    live=[c for c in study['conditions'] if not c['control']]
    if len(live)!=1 or not all(c['trigger_verified'] and c['content_complete'] and c['qualified_image_series'] for c in live):
        raise ValueError('Follow-up result is not qualified')
    records=[]
    def save(p,relative,compress=False):
        data=p.read_bytes();dest=target/relative
        if compress:dest=dest.with_name(dest.name+'.gz')
        dest.parent.mkdir(parents=True,exist_ok=True)
        archive=gzip.compress(data,compresslevel=9,mtime=0) if compress else data
        dest.write_bytes(archive)
        records.append(dict(file=dest.relative_to(target).as_posix(),source=str(p),
                            source_sha256=hashlib.sha256(data).hexdigest(),source_bytes=len(data),
                            archive_sha256=hashlib.sha256(archive).hexdigest(),archive_bytes=len(archive),
                            encoding='gzip' if compress else 'original'))
    for p in sorted(source.rglob('*')):
        if not p.is_file() or p.name=='snapshot.csv':continue
        if p.suffix not in ['.json','.png','.txt','.csv','.gz']:continue
        save(p,p.relative_to(source),compress=p.suffix=='.csv' or p.name=='study.json')
    build=root/'builds/eo_sync_20261008_r4_trig30'
    for name in ['build_options.tcl','build_validation.json','sampler_placement.csv','phase_clock_placement.txt',
                 'timing_summary.rpt','drc.rpt','bus_skew.rpt','cdc.rpt']:
        p=build/name
        if p.exists():save(p,Path('build_checks')/name,compress=p.suffix=='.rpt')
    for name in ['report_addendum.mjs','report_validation.json','report_error_scan.ndjson',
                 'verify_followup_workbook.py','saved_workbook_validation.json','restore_operational.log',
                 'simulation_checked.log','collector_regression_checked.log','check_collector_rate.py',
                 'choose_frozen_phase.py','live_metrics.py','inspect_cam6_anomalies.py','analyze_cam6_recheck.py',
                 'record_build.py','record_restored.py','program_r4.log','audit_routed.log']:
        p=scratch/name
        if p.exists():save(p,Path('reproduction')/name)
    save(scratch/'sim_trigger_checked/tb_EoSyncTriggerRates.log',Path('reproduction/tb_EoSyncTriggerRates.log'))
    manifest=dict(description='1080p60 with generated 30 Hz trigger and zero programmed trigger delay',files=records)
    (target/'archive_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for item in records:
        data=(target/item['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==item['archive_sha256']
        if item['encoding']=='gzip':data=gzip.decompress(data)
        assert hashlib.sha256(data).hexdigest()==item['source_sha256']
    # The updated copy contains both studies. The original workbook was open and
    # locked, so preserve it and its manifest entry alongside the new report.
    workbook=root/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009.xlsx'
    data=workbook.read_bytes();(parent/workbook.name).write_bytes(data)
    old=json.loads((parent/'archive_manifest.json').read_text())
    entry=next((r for r in old['files'] if r['file']==workbook.name),None)
    if entry is None:
        entry=dict(file=workbook.name,encoding='original');old['files'].append(entry)
    entry.update(source=str(workbook),source_bytes=len(data),archive_bytes=len(data),
                 source_sha256=hashlib.sha256(data).hexdigest(),archive_sha256=hashlib.sha256(data).hexdigest())
    old['followup_manifest']='trig30_20261008/archive_manifest.json'
    (parent/'archive_manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    print(json.dumps(dict(files=len(records),bytes=sum(r['archive_bytes'] for r in records),workbook_sha256=entry['archive_sha256'])))


if __name__=='__main__':main()
