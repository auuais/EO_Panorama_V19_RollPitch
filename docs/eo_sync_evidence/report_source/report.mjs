import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root=process.cwd();
const source=path.join(root,'captures/eo_sync_20261008/study.json');
const study=JSON.parse(await fs.readFile(source,'utf8'));
const outputDir=path.join(root,'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99');
const scratch=path.join(root,'.tmpCRC/eo_sync_20261008');
const wb=Workbook.create();
const summary=wb.worksheets.add('Comparison');
const cameras=wb.worksheets.add('Camera results');
const matched=wb.worksheets.add('Matched rasters');
const colors={navy:'#253B56',blue:'#3E7195',pale:'#EDF2F6',orange:'#D9973D',text:'#243244'};
function style(sheet,range){const r=sheet.getRange(range);r.format.font={name:'Arial',size:10,color:colors.text};r.format.rowHeight=21;r.format.verticalAlignment='center';sheet.showGridLines=false;}
function header(sheet,range){const r=sheet.getRange(range);r.format.fill=colors.navy;r.format.font.color='#FFFFFF';r.format.font.bold=true;r.format.wrapText=true;r.format.horizontalAlignment='center';r.format.rowHeight=34;}
function title(sheet,text){sheet.getRange('A2').values=[[text]];sheet.getRange('A2').format.font.size=15;sheet.getRange('A2').format.font.bold=true;sheet.getRange('A3:J3').format.borders={bottom:{style:'thin',color:colors.blue}};}
const cohorts=study.raster_cohorts;
const cohortHeaders=['Condition','Format fps','Mode','Block','Cam 2 tick','Cam 3 tick','Cam 4 tick','Cam 5 tick','Cam 6 tick','Period ticks','Circular spread us','Circular spread ms','Cam 3 offset us','Cam 4 offset us','Cam 5 offset us','Cam 6 offset us'];
style(matched,`A1:P${cohorts.length+4}`);
matched.getRange('A1').values=[['Processed matched raster boundaries; one row per camera-2 anchor, nearest valid frame from every camera.']];
matched.getRange('A2').values=[['Ticks use the nominal 27 MHz reference. Shortest circular arc = period minus largest cyclic gap. Capture blocks stay separate.']];
matched.getRange('A3:P3').values=[cohortHeaders];header(matched,'A3:P3');
matched.getRange(`A4:P${cohorts.length+3}`).values=cohorts.map(r=>[r.condition,r.format_fps,r.mode,r.block,...[2,3,4,5,6].map(c=>r[`cam${c}_tick`]),r.period_ticks,r.span_us,null,...[3,4,5,6].map(c=>r[`cam${c}_offset_us`])]);
matched.getRange('L4').formulas=[['=K4/1000']];matched.getRange(`L4:L${cohorts.length+3}`).fillDown();
matched.getRange('A:A').format.columnWidth=21;matched.getRange('B:D').format.columnWidth=15;matched.getRange('E:J').format.columnWidth=19;matched.getRange('K:P').format.columnWidth=19;
matched.getRange(`E4:J${cohorts.length+3}`).setNumberFormat('0');matched.getRange(`K4:P${cohorts.length+3}`).setNumberFormat('0.000');
matched.tables.add(`A3:P${cohorts.length+3}`,true,'MatchedRasters');matched.freezePanes.freezeRows(3);matched.freezePanes.freezeColumns(4);

const cr=study.camera_rows;
const cameraHeaders=['Condition','Mode','Control','Selected','Camera','Edge','Block','Build','Records','Timing valid','Strict valid','Strict valid %','Sequence gaps','Observed s','Raster Hz','Full CRC changes','Full change Hz','ROI changes','ROI change Hz','Offset median us','Drift us/s','Trigger phase median us','Trigger phase min us','Trigger phase max us','Source file','Source SHA256','Format fps','Phase tap','Freeze control'];
style(cameras,`A1:AC${cr.length+7}`);
cameras.getRange('A1').values=[['Per-camera observations, including rejected sampling edges and Freeze controls. Only Selected = TRUE contributes to the comparison.']];
cameras.getRange('A2').values=[['Source: local ILA CSV captures, captures/eo_sync_20261008; file and SHA256 in columns Y–Z. Analysis: diagnostics/eo_sync/scripts/collect_study.py.']];
cameras.getRange('A3').values=[[`Manual: DM-G15-42 v1.04, printed pp. 39–42; SHA256 ${study.protocol.manual_sha256}. No numerical skew tolerance found in that section.`]];
cameras.getRange('A4').values=[['At 1080p60, full-frame CRC is unqualified even on Selected edges; only the ROI passed. CRC changes do not prove new exposures. Blank validity % means no captured records.']];
cameras.getRange('A6:AC6').values=[cameraHeaders];header(cameras,'A6:AC6');
cameras.getRange(`A7:AC${cr.length+6}`).values=cr.map(r=>[r.condition,r.mode,r.control,r.selected,r.camera,r.phase,r.block,r.build,r.records,r.timing_valid,r.valid,null,r.sequence_gaps,r.duration_s,r.raster_hz,r.full_changes,r.full_change_hz,r.roi_changes,r.roi_change_hz,r.offset_median_us,r.drift_us_per_second,r.since_trigger_fall_us?.median??null,r.since_trigger_fall_us?.min??null,r.since_trigger_fall_us?.max??null,r.source_file,r.source_sha256,r.format_fps,r.phase_tap??null,r.control_id??null]);
cameras.getRange('L7').formulas=[['=IF(I7=0,"",K7/I7)']];cameras.getRange(`L7:L${cr.length+6}`).fillDown();
cameras.getRange('A:B').format.columnWidth=20;cameras.getRange('C:H').format.columnWidth=13;cameras.getRange('I:X').format.columnWidth=18;cameras.getRange('Y:Y').format.columnWidth=42;cameras.getRange('Z:Z').format.columnWidth=73;
cameras.getRange(`L7:L${cr.length+6}`).setNumberFormat('0.0%');cameras.getRange(`N7:O${cr.length+6}`).setNumberFormat('0.00000');cameras.getRange(`Q7:Q${cr.length+6}`).setNumberFormat('0.00000');cameras.getRange(`S7:X${cr.length+6}`).setNumberFormat('0.000');
cameras.getRange('AA:AB').format.columnWidth=15;cameras.getRange('AC:AC').format.columnWidth=21;
cameras.tables.add(`A6:AC${cr.length+6}`,true,'CameraObservations');cameras.freezePanes.freezeRows(6);cameras.freezePanes.freezeColumns(5);

style(summary,'A1:J55');summary.tabColor=colors.navy;
summary.getRange('A:A').format.columnWidth=25;summary.getRange('B:B').format.columnWidth=14;summary.getRange('C:I').format.columnWidth=15;summary.getRange('J:J').format.columnWidth=24;
title(summary,'EO camera synchronization — trigger versus free run');
summary.getRange('A4').values=[['Physical cameras 2–6 | 8 October 2026 | BT.1120 data arrival at the FPGA']];
summary.getRange('A5').values=[['All tests: generated trigger 60 Hz, 2 ms high; shutter 1/240 s; gain 0 dB; DNR 2D+3D. FreeRun ignores the trigger.']];
summary.getRange('A6').values=[['Incoming raster boundaries']];summary.getRange('A6').format.font.bold=true;
summary.getRange('A7:J7').values=[['Format / mode','Trigger Hz','Observed s','Matched sets','Min spread ms','Median ms','P95 ms','Max ms','Raster Hz min','Raster Hz max']];header(summary,'A7:J7');
const conditions=study.conditions.filter(c=>!c.control);
const validations=[];
conditions.forEach((c,i)=>{
  const r=8+i, indices=cohorts.map((x,j)=>x.condition===c.id?j+4:null).filter(x=>x!==null);
  if(!c.timing_complete || !c.content_complete || !c.trigger_verified || !indices.length)throw Error(`Unqualified comparison: ${c.id}`);
  const first=indices[0],last=indices.at(-1);if(last-first+1!==indices.length)throw Error('Noncontiguous cohort range');
  const ref=`'Matched rasters'!L${first}:L${last}`;
  const rates=c.camera_rows.map(x=>x.raster_hz);
  summary.getRange(`A${r}:J${r}`).values=[[`1080p${c.format_fps} ${c.mode}`,60,c.observed_s,null,null,null,null,null,Math.min(...rates),Math.max(...rates)]];
  summary.getRange(`D${r}:H${r}`).formulas=[[`=COUNT(${ref})`,`=MIN(${ref})`,`=MEDIAN(${ref})`,`=PERCENTILE(${ref},0.95)`,`=MAX(${ref})`]];
  validations.push({row:r,id:c.id,expected:[c.spreads_us.raster.n,...['min','median','p95','max'].map(k=>c.spreads_us.raster[k]/1000)]});
});
summary.getRange('C8:C13').setNumberFormat('0.00');summary.getRange('D8:D13').setNumberFormat('#,##0');summary.getRange('E8:J13').setNumberFormat('0.000');
const controls=study.conditions.filter(c=>c.control);
controls.forEach((c,i)=>summary.getRange(`A${15+i}`).values=[[`1080p${c.format_fps} Freeze control: ${c.observed_s.toFixed(2)} s; strict geometry ${c.content_complete?'100%':'FAILED'}; whole-raster stable ${c.qualifies_full?'YES':'NO'}; ROI stable ${c.qualifies_roi?'YES':'NO'}.`]]);
summary.getRange('A18').values=[['Qualified payload changes — rates and five-camera timing spread']];summary.getRange('A18').format.font.bold=true;
summary.getRange('A19:I19').values=[['Format / mode','CRC scope','Changes/s min','Changes/s max','Matched sets','Min ms','Median ms','P95 ms','Max ms']];header(summary,'A19:I19');
conditions.forEach((c,i)=>{
 const r=20+i,key=c.qualified_image_series==='full_crc'?'full_change_hz':c.qualified_image_series==='roi_crc'?'roi_change_hz':null;
 const rates=key?c.camera_rows.map(x=>x[key]):[];
 const s=c.image_spread_us;
 summary.getRange(`A${r}:I${r}`).values=[[`1080p${c.format_fps} ${c.mode}`,key==='full_change_hz'?'Full raster':key?'96x96 ROI':'Unqualified',key?Math.min(...rates):null,key?Math.max(...rates):null,s?.n??null,...['min','median','p95','max'].map(k=>s?.[k]==null?null:s[k]/1000)]];
});
summary.getRange('C20:D25').setNumberFormat('0.000');summary.getRange('E20:E25').setNumberFormat('#,##0');summary.getRange('F20:I25').setNumberFormat('0.000');
summary.getRange('A27').values=[['Payload changes are reported at the next active-raster boundary. They do not identify a shared exposure across cameras.']];
summary.getRange('A28').values=[['Rate ranges cover all five cameras and both capture blocks. DNR remains enabled. A CRC change is not proof of a fresh sensor exposure.']];
summary.getRange('A29').values=[['Circular periods follow event cadence: about 16.67 ms for 60 rasters/s and 33.33 ms for 30 payload changes/s.']];
summary.getRange('A30').values=[['1080p60 camera 6: full-raster CRC changed while frozen. Only raster timing and the stable central 96x96 ROI are qualified.']];
summary.getRange('A31').values=[['Both formats: selected-path strict geometry 100%, no sequence gaps, no telemetry overruns; generated trigger verified in every block.']];
const notes=study.report_notes??[
 '1080p30: data arrivals were not aligned in ExtTrig or FreeRun; switching back to ExtTrig did not reset their relative drift.',
 'Differences between capture medians are not a measured trigger-mode improvement: relative camera phase changes continuously with elapsed time.',
 'These measurements describe incoming raster boundaries and qualified payload changes. Physical exposure synchronization remains unproven.',
 'The spread is the shortest circular arc containing all five nearest raster phases. It does not establish a common exposure or frame identity.',
 'Nominal timestamp resolution: 37.037 ns. Reference frequency, electrical trigger arrival and camera/board delays are not independently calibrated.',
 'Complete capture blocks are analyzed separately; upload gaps and reprogramming intervals are excluded. No missing/invalid frame is replaced with zero spread.',
 'Manufacturer wording describes synchronous image output but provides no numerical skew tolerance in the reviewed trigger section.',
 'A sensor-exposure verdict needs synchronized strobe measurements or a shared, time-coded optical target with image correspondence.'
];notes.forEach((t,i)=>summary.getRange(`A${35+i}`).values=[[t]]);
summary.getRange('A44').values=[['Median within-block drift relative to camera 2 (microseconds per second)']];summary.getRange('A44').format.font.bold=true;
summary.getRange('A45:F45').values=[['Format / mode','Camera 2','Camera 3','Camera 4','Camera 5','Camera 6']];header(summary,'A45:F45');
function median(v){const a=v.filter(x=>x!=null).sort((a,b)=>a-b);return a.length?(a[Math.floor((a.length-1)/2)]+a[Math.floor(a.length/2)])/2:null;}
conditions.forEach((c,i)=>summary.getRange(`A${46+i}:F${46+i}`).values=[[`1080p${c.format_fps} ${c.mode}`,...[2,3,4,5,6].map(cam=>median(c.camera_rows.filter(r=>r.camera===cam).map(r=>r.drift_us_per_second)))]]);
summary.getRange('B46:F51').setNumberFormat('0.000');
wb.recalculate();
for(const v of validations){const got=summary.getRange(`D${v.row}:H${v.row}`).values[0];got.forEach((x,i)=>{if(typeof x!=='number'||Math.abs(x-v.expected[i])>1e-8)throw Error(`${v.id} summary mismatch: ${JSON.stringify(got)}`);});}
const checks=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Final formula error scan'});
await fs.writeFile(path.join(scratch,'report_error_scan.ndjson'),checks.ndjson);
if(checks.ndjson.split('\n').filter(Boolean).some(line=>JSON.parse(line).kind==='match'))throw Error('Formula error scan found a match');
console.log((await wb.inspect({kind:'table',range:'Comparison!A7:J13',include:'values,formulas',tableMaxRows:8,tableMaxCols:10,maxChars:7000})).ndjson);
const previews=[['Comparison','A1:J43','comparison'],['Comparison','A44:J52','drift'],['Camera results','A1:M14','camera_results'],['Matched rasters','A1:P12','matched_rasters']];
const selectedPreviews=process.env.EO_REPORT_PREVIEW==='camera'?[['Camera results','A1:M14','camera_results'],['Camera results','A82:M90','empty_edge']]:process.env.EO_REPORT_SUMMARY_ONLY==='1'?previews.slice(0,1):previews;
for(const [sheetName,range,file] of selectedPreviews){
 const img=await wb.render({sheetName,range,scale:1.3});await fs.writeFile(path.join(scratch,`${file}.png`),new Uint8Array(await img.arrayBuffer()));
}
await fs.mkdir(outputDir,{recursive:true});
const output=await SpreadsheetFile.exportXlsx(wb);
const filename=path.join(outputDir,'EO_Camera_Synchronization_Comparison_20261008.xlsx');await output.save(filename);
await fs.writeFile(path.join(scratch,'report_validation.json'),JSON.stringify({validated_conditions:validations,rows:{camera:cr.length,matched:cohorts.length},output:filename},null,2));
console.log(filename);
