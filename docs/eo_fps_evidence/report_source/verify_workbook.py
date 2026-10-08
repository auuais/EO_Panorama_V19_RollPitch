"""Read-only package/evidence checks after artifact-tool authoring and export."""
from pathlib import Path
import json, math, hashlib, zipfile
from copy import copy
import openpyxl
from openpyxl.utils import range_boundaries

root=Path('E:/Xylinx/EO_Panorama_V19_RollPitch')
evidence=root/'captures/eo60_verify_20261008'
work=root/'.tmpCRC/eo60_verify_20261008'
out=root/'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_FPS_Consolidated_Report_20261007.xlsx'
w=openpyxl.load_workbook(out,data_only=False)
v=openpyxl.load_workbook(out,data_only=True)
b=openpyxl.load_workbook(work/'report_before_verification.xlsx',data_only=False)
bv=openpyxl.load_workbook(work/'report_before_verification.xlsx',data_only=True)
data=json.loads((evidence/'verification_results.json').read_text(encoding='utf-8'))
links=json.loads((root/'.tmpCRC/excel_report_20261007/hyperlinks.json').read_text(encoding='utf-8'))
assert w.sheetnames==b.sheetnames==['Report','Exposure Sweep','ILA Results','USB Results']
allowed={
 'Report':set('A4 A66 A80 A90 A91 A94 A95 A103 A104 A106 B106 D106 A113 A114 A115 A118 F122'.split()),
 'Exposure Sweep':set('A208 B210 C210 F210 F211 F212 F213 F214 F215 A219 A225'.split()),
 'ILA Results':set('A71 D73 D101 L105 A115'.split()), 'USB Results':set(),
}
changes={}
for s in w:
    prev=b[s.title]
    assert s.freeze_panes==prev.freeze_panes
    assert len(s._charts)==len(prev._charts)
    changes[s.title]=[]
    for row in prev:
        for c in row:
            now=s[c.coordinate]
            if c.value is not None and now.value!=c.value:
                assert c.coordinate in allowed[s.title],(s.title,c.coordinate,c.value,now.value)
                changes[s.title].append(c.coordinate)
            if c.value is not None:
                for attr in ['font','fill','border','alignment','number_format','protection']:
                    assert copy(getattr(c,attr))==copy(getattr(now,attr)),(s.title,c.coordinate,attr)
    for t in prev.tables.values():
        actual=s.tables[t.name]
        assert actual.ref==t.ref
        assert actual.tableStyleInfo==t.tableStyleInfo
    for t in s.tables.values():
        x,y,_,_=range_boundaries(t.ref)
        headers=[s.cell(y,x+i).value for i in range(len(t.tableColumns))]
        names=[c.name for c in t.tableColumns]
        assert headers==names,(s.title,t.name,headers,names)
        assert len(names)==len(set(n.casefold() for n in names))
    for row in v[s.title]:
        for c in row:
            assert c.data_type!='e',(s.title,c.coordinate,c.value)

assert {s.title:len(s.tables) for s in w}=={'Report':0,'Exposure Sweep':7,'ILA Results':3,'USB Results':1}
assert w['Exposure Sweep'].tables['FreezeVerification'].ref=='A235:R243'
assert len(w['Report']._charts)==1 and len(w['Report']._charts[0].series)==2
assert len(w['Report']._images)==3
for r in range(7,17):
    for col in ['B','C','D']:
        assert v['Report'][f'{col}{r}'].value==bv['Report'][f'{col}{r}'].value
for a in ['D86']+[f'D{r}' for r in range(107,112)]:
    assert v['Report'][a].value=='Unverified'
assert v['ILA Results']['L105'].value=='Unverified'
for i,e in enumerate(data['entries']):
    r=236+i; q=131+i;s=v['Exposure Sweep'];summary=v['Report']
    expected={'A':e['label'],'B':e['format_hz'],'C':e['shutter_osd'],'D':e['dnr'],
      'E':e['freeze'],'F':e['build_label'],'G':e['valid_reports'],'H':e['raster_hz'],
      'I':e['pairs'],'J':e['full_changed'],'K':e['roi_changed']}
    for col,x in expected.items():
        actual=s[f'{col}{r}'].value
        assert math.isclose(actual,x,rel_tol=1e-12) if isinstance(x,float) else actual==x,(r,col,actual,x)
    assert math.isclose(summary[f'B{q}'].value,e['raster_hz'],rel_tol=1e-12)
    assert summary[f'C{q}'].value==f"{e['full_changed']} / {e['pairs']}"
    assert summary[f'D{q}'].value==f"{e['roi_changed']} / {e['pairs']}"
    if e['fresh_input_fps'] is not None:
        assert math.isclose(s[f'L{r}'].value,e['fresh_input_fps'],rel_tol=1e-12)
    else:
        assert s[f'L{r}'].value==('Control' if e['freeze']=='ON' else 'Unverified')
    if e['roi_spacing_rasters']:
        assert math.isclose(s[f'Q{r}'].value,e['raster_hz']/e['roi_spacing_rasters'],rel_tol=1e-12)
    else:
        assert s[f'Q{r}'].value=='Constant'
    assert s[f'R{r}'].value==('Pass' if e['freeze_control_pass'] else 'Fail' if e['freeze_control_pass'] is False else 'n.a.')
    raw=json.loads((evidence/e['tag']/'summary.json').read_text())
    p=raw['phases']['falling']
    assert e['full_changed']==p['crc_changed_pairs'] and e['pairs']==p['valid_adjacent_pairs']
    assert set(raw['trigger_hz_observations'])=={'60'}
    assert (evidence/e['osd_evidence']).exists()

assert len(links)==492
for item in links:
    c=w[item['sheet']][item['cell']]
    assert c.value==item['label'] and c.hyperlink
    assert c.hyperlink.target==Path(item['target']).as_uri(),(item,c.hyperlink.target)
    assert Path(item['target']).exists()
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    embedded={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('xl/media/')}
    wanted={hashlib.sha256((evidence/p).read_bytes()).hexdigest() for p in data['key_images'].values()}
    assert embedded==wanted,(embedded,wanted)
manual=Path(data['manual_path'])
assert hashlib.sha256(manual.read_bytes()).hexdigest()==data['manual_sha256']
final=json.loads((evidence/'final_state.json').read_text())
assert final['restored'] and final['camera2']['shutter_osd']=='1/240 sec' and final['display_camera']==6
for name,digest in final['reviewed_images'].items():
    assert hashlib.sha256((evidence/name).read_bytes()).hexdigest()==digest
result={'passed':True,'output':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
 'worksheets':w.sheetnames,'verified_conditions':len(data['entries']),'native_hyperlinks':len(links),
 'embedded_osd_images':3,'preserved_chart_series':2,'formula_errors':0,'intentional_historical_changes':changes,
 'preserved':'All other historical nonempty cells, their formatting, original table ranges/styles and freeze panes.',
 'hardware_restored':True}
(work/'workbook_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
