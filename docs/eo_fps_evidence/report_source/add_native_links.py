"""Supply native local-file hyperlinks unavailable in the authoring API."""
import json
import os
from pathlib import Path
import sys
import zipfile
from xml.etree import ElementTree as ET

book=Path(sys.argv[1])
links=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
MAIN='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
DOCREL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKGREL='http://schemas.openxmlformats.org/package/2006/relationships'
ET.register_namespace('',MAIN)
ET.register_namespace('r',DOCREL)
with zipfile.ZipFile(book) as z:
    data={i.filename:z.read(i.filename) for i in z.infolist()}
workbook=ET.fromstring(data['xl/workbook.xml'])
rel=ET.fromstring(data['xl/_rels/workbook.xml.rels'])
targets={r.attrib['Id']:r.attrib['Target'] for r in rel}
sheets={s.attrib['name']:targets[s.attrib[f'{{{DOCREL}}}id']] for s in workbook.find(f'{{{MAIN}}}sheets')}
for name in dict.fromkeys(l['sheet'] for l in links):
    target=sheets[name]
    sheetfile=target.lstrip('/') if target.startswith('/') else 'xl/'+target
    sheet=ET.fromstring(data[sheetfile])
    linksnode=sheet.find(f'{{{MAIN}}}hyperlinks')
    if linksnode is None:
        linksnode=ET.Element(f'{{{MAIN}}}hyperlinks')
        # Hyperlinks precede print settings and drawing objects in worksheet order.
        after={'sheetPr','dimension','sheetViews','sheetFormatPr','cols','sheetData','sheetCalcPr','sheetProtection','protectedRanges','scenarios','autoFilter','sortState','dataConsolidate','customSheetViews','mergeCells','phoneticPr','conditionalFormatting','dataValidations'}
        idx=0
        for i,c in enumerate(sheet):
            if c.tag.rsplit('}',1)[-1] in after:idx=i+1
        sheet.insert(idx,linksnode)
    sp=Path(sheetfile)
    relfile=str(sp.parent/'_rels'/(sp.name+'.rels')).replace('\\','/')
    relationships=ET.fromstring(data[relfile]) if relfile in data else ET.Element(f'{{{PKGREL}}}Relationships')
    existing={r.attrib['Id'] for r in relationships}
    for i,l in enumerate(x for x in links if x['sheet']==name):
        rid=f'rIdEvidence{i+1}'
        assert rid not in existing
        ET.SubElement(linksnode,f'{{{MAIN}}}hyperlink',{'ref':l['cell'],f'{{{DOCREL}}}id':rid,'display':l['label']})
        ET.SubElement(relationships,f'{{{PKGREL}}}Relationship',{'Id':rid,'Type':DOCREL+'/hyperlink','Target':Path(l['target']).as_uri(),'TargetMode':'External'})
    data[sheetfile]=ET.tostring(sheet,encoding='utf-8',xml_declaration=True)
    data[relfile]=ET.tostring(relationships,encoding='utf-8',xml_declaration=True)
tmp=book.with_suffix('.xlsx.tmp')
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
    for name,content in data.items():z.writestr(name,content)
os.replace(tmp,book)
print(f'Added {len(links)} native evidence hyperlinks.')
