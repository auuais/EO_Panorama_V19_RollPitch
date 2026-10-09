"""Read-only workbook checks: preserve prior report and verify new actual spread."""
import copy
import hashlib
import json
import math
from pathlib import Path
import openpyxl
ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch');SCRATCH=ROOT/'.tmpCRC/eo_dnr_all5_20261009'
OUT=ROOT/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx'
before=openpyxl.load_workbook(SCRATCH/'report_before.xlsx',data_only=False)
after=openpyxl.load_workbook(OUT,data_only=False);values=openpyxl.load_workbook(OUT,data_only=True)
v=json.loads((SCRATCH/'report_validation.json').read_text());s=json.loads((ROOT/'captures/eo_dnr_all5_20261009/study.json').read_text())
assert before.sheetnames==after.sheetnames==['Comparison','Camera results','Matched rasters']
checked=0;style_pairs=set();differences=[]
for old in before:
 new=after[old.title]
 assert old.freeze_panes==new.freeze_panes;assert old.sheet_view.showGridLines==new.sheet_view.showGridLines
 assert list(old.tables)==list(new.tables);assert len(old.conditional_formatting)==len(new.conditional_formatting)
 assert list(old.merged_cells)==list(new.merged_cells)
 for row in old:
  for cell in row:
   n=new[cell.coordinate];assert cell.value==n.value,(old.title,cell.coordinate,cell.value,n.value)
   assert cell.number_format==n.number_format,(old.title,cell.coordinate,'number_format')
   pair=(old.title,cell.style_id,n.style_id)
   if pair not in style_pairs:
    for prop in ['font','fill','border','alignment','protection']:
     if copy.copy(getattr(cell,prop))!=copy.copy(getattr(n,prop)):differences.append((old.title,cell.coordinate,prop))
    style_pairs.add(pair)
   checked+=1
 for name in old.tables:
  assert old.tables[name].tableStyleInfo==new.tables[name].tableStyleInfo
  assert old.tables[name].headerRowCount==new.tables[name].headerRowCount
assert not differences,differences
for e in v['expected']:
 for col,x in enumerate(e['expected'],4):
  got=values['Comparison'].cell(e['row'],col).value
  assert math.isclose(got,x,abs_tol=1e-8) if isinstance(x,(float,int)) else got==x,(e,col,got)
  assert after['Comparison'].cell(e['row'],col).data_type=='f'
for row,item in enumerate(s['raster_cohorts'],v['matchedStart']):
 assert after['Matched rasters'].cell(row,12).value==f'=K{row}/1000'
 assert math.isclose(values['Matched rasters'].cell(row,12).value,item['span_us']/1000,abs_tol=1e-8)
for row,item in enumerate(s['camera_rows'],v['cameraStart']):
 assert values['Camera results'].cell(row,12).value==1
 assert after['Camera results'].cell(row,12).data_type=='f'
assert after['Camera results'].tables['CameraObservations'].ref==f"A6:AC{v['cameraEnd']}"
assert after['Matched rasters'].tables['MatchedRasters'].ref==f"A3:P{v['matchedEnd']}"
errors=[f'{ws.title}!{c.coordinate}' for ws in values for row in ws for c in row if c.data_type=='e'];assert not errors,errors
result=dict(preserved_cells_checked=checked,unintended_style_changes=differences,all_new_formulas_and_caches_verified=True,
 tables_and_panes_preserved=True,formula_errors=errors,workbook_sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
 engine='Artifact Tool calculation and read-only OpenXML checks; native Excel execution not performed')
(SCRATCH/'saved_workbook_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
