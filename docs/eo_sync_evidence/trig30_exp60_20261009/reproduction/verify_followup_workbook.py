"""Read-only OpenXML checks of new results and preservation of the prior study."""
import copy
import hashlib
import json
import math
from pathlib import Path
import openpyxl

root=Path.cwd();scratch=root/'.tmpCRC/eo_sync_trig30_exp60_20261009'
out=root/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx'
before=openpyxl.load_workbook(scratch/'report_before.xlsx',data_only=False)
after=openpyxl.load_workbook(out,data_only=False)
values=openpyxl.load_workbook(out,data_only=True)
validation=json.loads((scratch/'report_validation.json').read_text())
study=json.loads((root/'captures/eo_sync_trig30_exp60_20261009/study.json').read_text())

assert after.sheetnames==before.sheetnames==['Comparison','Camera results','Matched rasters']
allowed={s:set() for s in before.sheetnames}
style_differences=[];checked=0;style_pairs=set()
for old in before:
    new=after[old.title]
    assert old.freeze_panes==new.freeze_panes
    assert old.sheet_view.showGridLines==new.sheet_view.showGridLines
    assert list(old.tables)==list(new.tables)
    assert len(old.conditional_formatting)==len(new.conditional_formatting)
    for row in old:
        for cell in row:
            if old.title=='Comparison' and cell.row>=99:continue
            if old.title=='Camera results' and cell.row>=validation['cameraStart']:continue
            if old.title=='Matched rasters' and cell.row>=validation['matchedStart']:continue
            n=new[cell.coordinate]
            if cell.coordinate not in allowed[old.title]:
                assert cell.value==n.value,(old.title,cell.coordinate,cell.value,n.value)
            assert cell.number_format==n.number_format,(old.title,cell.coordinate,'number format')
            pair=(cell.style_id,n.style_id)
            if pair not in style_pairs:
                for prop in ['font','fill','border','alignment','protection']:
                    if copy.copy(getattr(cell,prop))!=copy.copy(getattr(n,prop)):
                        style_differences.append((old.title,cell.coordinate,prop))
                style_pairs.add(pair)
            checked+=1
    for name,table in old.tables.items():
        old_table=old.tables[name];new_table=new.tables[name]
        assert old_table.tableStyleInfo==new_table.tableStyleInfo
        assert old_table.headerRowCount==new_table.headerRowCount
assert not style_differences,style_differences[:20]
for e in validation['expected']:
    r=e['row'];got=[values['Comparison'].cell(r,col).value for col in range(3,8)]
    for a,b in zip(got,[e['seconds'],e['records'],e['raster_hz'],e['changes'],e['change_hz']]):
        assert math.isclose(a,b,abs_tol=1e-8)
    assert values['Comparison'].cell(r,9).value==1
    assert values['Comparison'].cell(r,10).value==0
for col,expected in enumerate(validation['spread'],4):
    assert math.isclose(values['Comparison'].cell(119,col).value,expected,abs_tol=1e-8)
for col,expected in enumerate(validation['repeatSpread'],4):
    assert math.isclose(values['Comparison'].cell(144,col).value,expected,abs_tol=1e-8)
for i,row in enumerate(study['camera_rows'],validation['cameraStart']):
    got=values['Camera results'].cell(i,12).value
    assert got in [None,''] if not row['records'] else math.isclose(got,row['valid']/row['records'],abs_tol=1e-10)
    assert after['Camera results'].cell(i,12).data_type=='f'
for i,row in enumerate(study['raster_cohorts'],validation['matchedStart']):
    assert math.isclose(values['Matched rasters'].cell(i,12).value,row['span_us']/1000,abs_tol=1e-8)
    assert after['Matched rasters'].cell(i,12).value==f'=K{i}/1000'
assert after['Camera results'].tables['CameraObservations'].ref==f"A6:AC{validation['cameraEnd']}"
assert after['Matched rasters'].tables['MatchedRasters'].ref==f"A3:P{validation['matchedEnd']}"
errors=[f'{s.title}!{c.coordinate}' for s in values for row in s for c in row if c.data_type=='e']
assert not errors,errors
result=dict(preserved_cells_checked=checked,unintended_style_changes=style_differences,
            all_new_formulas_and_caches_verified=True,tables_and_panes_preserved=True,
            formula_errors=errors,workbook_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
            engine='Artifact Tool calculation plus read-only OpenXML checks; native Excel execution not performed')
(scratch/'saved_workbook_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
