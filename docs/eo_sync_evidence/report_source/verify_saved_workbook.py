"""Read-only check of the exported workbook against independently decoded data."""
import hashlib
import json
import math
from pathlib import Path
import openpyxl

root=Path.cwd()
path=root/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261008.xlsx'
study=json.loads((root/'captures/eo_sync_20261008/study.json').read_text())
book=openpyxl.load_workbook(path,data_only=True)
formula=openpyxl.load_workbook(path,data_only=False)
assert book.sheetnames==['Comparison','Camera results','Matched rasters']
conditions=[c for c in study['conditions'] if not c['control']]
assert len(conditions)==6
for i,c in enumerate(conditions):
    sheet=book['Comparison']
    r=8+i
    assert sheet.cell(r,1).value==f"1080p{c['format_fps']} {c['mode']}"
    assert sheet.cell(r,2).value==60
    assert math.isclose(sheet.cell(r,3).value,c['observed_s'],abs_tol=1e-8)
    values=[c['spreads_us']['raster']['n']]+[c['spreads_us']['raster'][k]/1000 for k in ['min','median','p95','max']]
    for col,expected in enumerate(values,4):
        assert math.isclose(sheet.cell(r,col).value,expected,abs_tol=1e-8)
        assert formula['Comparison'].cell(r,col).data_type=='f'
    s=c['image_spread_us']
    for col,expected in enumerate([s['n']]+[s[k]/1000 for k in ['min','median','p95','max']],5):
        assert math.isclose(sheet.cell(20+i,col).value,expected,abs_tol=1e-8)
assert len(book['Camera results'].tables)==1 and len(book['Matched rasters'].tables)==1
assert book['Camera results'].freeze_panes and book['Matched rasters'].freeze_panes
cohorts=study['raster_cohorts']
for i,row in enumerate(cohorts,4):
    assert math.isclose(book['Matched rasters'].cell(i,12).value,row['span_us']/1000,abs_tol=1e-8)
    assert formula['Matched rasters'].cell(i,12).value==f'=K{i}/1000'
for i,row in enumerate(study['camera_rows'],7):
    if row['records']:
        assert math.isclose(book['Camera results'].cell(i,12).value,row['valid']/row['records'],abs_tol=1e-10)
    else:
        assert not row['selected']
        assert book['Camera results'].cell(i,12).value in [None,'']
errors=[]
for sheet in book:
    for row in sheet:
        for cell in row:
            if cell.data_type=='e':errors.append(f'{sheet.title}!{cell.coordinate}: {cell.value}')
assert not errors,errors
result=dict(sheets=book.sheetnames,conditions=6,camera_rows=len(study['camera_rows']),
            matched_rows=len(cohorts),all_matched_formulas_and_caches_verified=True,
            headline_values_verified=True,formula_errors=errors,
            workbook_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            engine='Artifact Tool recalculation and read-only OpenXML validation; native Excel execution not performed')
(root/'.tmpCRC/eo_sync_20261008/saved_workbook_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
