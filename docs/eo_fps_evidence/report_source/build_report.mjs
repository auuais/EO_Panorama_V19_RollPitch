import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root='E:/Xylinx/EO_Panorama_V19_RollPitch';
const evidence=path.join(root,'captures/takeover_20261007');
const sweepRoot=path.join(root,'captures/exposure_sweep_20261007_1915');
const sweep30Root=path.join(root,'captures/exposure_sweep_30hz_20261007_2020');
const formatRoot=path.join(root,'captures/cam2_1080p60_20261007_2353');
const formatTest=await JSON.parse(await fs.readFile(path.join(formatRoot,'format_test_results.json'),'utf8'));
const diagRoot=path.join(root,'captures/eo60_diagnostic_20261008_0051');
const diag=JSON.parse(await fs.readFile(path.join(diagRoot,'live_results.json'),'utf8'));
const slowRoot=path.join(root,'captures/eo60_exposure_20261008_0344');
const slow=JSON.parse(await fs.readFile(path.join(slowRoot,'sweep_results.json'),'utf8'));
const verifyRoot=path.join(root,'captures/eo60_verify_20261008');
const verification=JSON.parse(await fs.readFile(path.join(verifyRoot,'verification_results.json'),'utf8'));
const outputDir=path.join(root,'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99');
const work=path.join(root,'.tmpCRC/excel_report_20261007');
const read=async p=>JSON.parse(await fs.readFile(p,'utf8'));
const sweepIndex=await read(path.join(sweepRoot,'sweep_index.json'));
const restored=await read(path.join(sweepRoot,'final_state.json'));
const sweepData=await Promise.all(sweepIndex.entries.map(async config=>({config,data:await read(path.join(sweepRoot,config.tag,'summary.json'))})));
const index30=await read(path.join(sweep30Root,'sweep_index.json'));
const restored30=await read(path.join(sweep30Root,'final_state.json'));
const sweep30Data=await Promise.all(index30.entries.map(async config=>({config,data:await read(path.join(sweep30Root,config.tag,'summary.json'))})));
assert.equal(sweep30Data.length,sweepData.length);
assert.ok(sweepData.length>=7);
const wb=Workbook.create();
const hyperlinks=[];
const summary=wb.worksheets.add('Report');
const sweep=wb.worksheets.add('Exposure Sweep');
const ila=wb.worksheets.add('ILA Results');
const usb=wb.worksheets.add('USB Results');
const ink='#203047',navy='#253C59',blue='#336B9E',pale='#F1F5FA',orange='#FFF0D2',gray='#637184';
function base(s,last,widths){
  s.showGridLines=false;
  const r=s.getRange(`A1:${last}`);
  r.format.font={name:'Arial',size:10,color:ink};
  r.format.verticalAlignment='center';r.format.rowHeight=21;
  widths.forEach((w,i)=>s.getRangeByIndexes(0,i,parseInt(last.match(/\d+/)[0]),1).format.columnWidth=w);
}
function cell(s,a,v){s.getRange(a).values=[[v]];}
function formula(s,a,f){s.getRange(a).formulas=[[f]];}
function title(s,text,lastcol){
  cell(s,'A2',text);s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:navy};
  s.getRange(`A2:${lastcol}2`).format.rowHeight=28;
  s.getRange(`A3:${lastcol}3`).format.borders={bottom:{style:'thin',color:'#BDC9D7'}};
}
function header(s,range,values){
  s.getRange(range).values=[values];
  s.getRange(range).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:36};
}
function section(s,row,text,lastcol){
  cell(s,`A${row}`,text);s.getRange(`A${row}:${lastcol}${row}`).format.fill=pale;
  s.getRange(`A${row}`).format.font.bold=true;s.getRange(`A${row}:${lastcol}${row}`).format.rowHeight=25;
}
function link(s,a,p,label){
  cell(s,a,label);
  hyperlinks.push({sheet:s.name,cell:a,target:p.replaceAll('\\','/'),label});
  s.getRange(a).format.font.color=blue;
}
function lines(s,start,texts){texts.forEach((t,i)=>cell(s,`A${start+i}`,t));}
function stripe(s,start,end,lastcol){for(let r=start;r<=end;r++)if((r-start)%2===1)s.getRange(`A${r}:${lastcol}${r}`).format.fill='#F7F9FC';}

base(summary,'J202',[32,17,18,18,3,15,15,15,15,15]);summary.tabColor=navy;
title(summary,'EO camera FPS — consolidated findings','J');
cell(summary,'A3','Live FPGA ILA and USB measurements. Rates describe changed pixel payloads, not sensor exposures.');
cell(summary,'A4','New: 1080p/60 slower-shutter results start at row 103. Earlier 1080p/30 sweeps and the dedicated RTL validation are preserved.');
cell(summary,'J3',new Date('2026-10-08T00:00:00Z'));summary.getRange('J3').setNumberFormat('dd mmm yyyy');
section(summary,5,'1080p/30 · camera 2 input content updates/s','D');
header(summary,'A6:D6',['ExtTrig condition','60 Hz trigger','30 Hz trigger','30 Hz spacing\n(rasters/update)']);
for(let i=0;i<sweepData.length;i++){
  const r=7+i,src=7+i,c=sweepData[i].config;
  cell(summary,`A${r}`,`${c.tag.includes('restore')||c.tag.includes('return')?'Return ':''}1/${c.shutter_denominator} s`);
  const end=6+sweepData.length;
  formula(summary,`B${r}`,`=SUMIF('Exposure Sweep'!$A$7:$A$${end},"${c.tag}",'Exposure Sweep'!$F$7:$F$${end})`);
  const c30=sweep30Data[i].config;
  assert.equal(c30.shutter_denominator,c.shutter_denominator);
  formula(summary,`C${r}`,`=SUMIF('Exposure Sweep'!$A$101:$A$110,"${c30.tag}",'Exposure Sweep'!$F$101:$F$110)`);
  formula(summary,`D${r}`,`=SUMIF('Exposure Sweep'!$A$101:$A$110,"${c30.tag}",'Exposure Sweep'!$E$101:$E$110)`);
}
const lastSweep=6+sweepData.length;
assert.ok(lastSweep<=16,'Expand report layout for more than ten conditions');
summary.getRange(`B7:C${lastSweep}`).setNumberFormat('0.00');summary.getRange(`D7:D${lastSweep}`).setNumberFormat('0');
summary.getRange(`B7:C${lastSweep}`).format.font.bold=true;
stripe(summary,7,lastSweep,'D');
lines(summary,17,[
  ...restored30.headline_lines
]);
const chart=summary.charts.add('bar',summary.getRange(`A6:C${lastSweep}`));
chart.title='1080p/30 input updates/s · 60 vs 30 Hz trigger';chart.titleTextStyle.typeface='Arial';chart.titleTextStyle.fontSize=13;
chart.hasLegend=true;chart.series.items[0].fill=blue;chart.series.items[1].fill='#E6A343';
chart.legend={position:'top',textStyle:{typeface:'Arial',fontSize:10}};
chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:9}};
chart.yAxis={numberFormatCode:'0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};
chart.setPosition('F5','J19');
section(summary,21,'Review of the handoff and manufacturer statement','J');
link(summary,'J21',path.join(root,'docs/HANDOFF_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md'),'Handoff');
lines(summary,22,[
  'Revised handoff: 30 rasters/s and ~15 output updates/s at the starting settings are reproduced; repetition is now located before DDR.',
  'Earlier fixed-15-Hz / exposure-independent interpretations are contradicted by the same-camera shutter test and return to baseline.',
  'The latest handoff correctly treated input pixel novelty as unresolved. Raw-input CRCs now resolve that gap for these conditions.',
  'Manufacturer’s quoted ~25 Hz: not reproduced. Both fresh input sweeps give ~15 or ~30 updates/s, depending on shutter.',
  'The manufacturer’s original wording and configuration are unavailable. A different setup could still produce 25 Hz.',
  'Earlier panorama claim of ~30 Hz on cameras 2 and 3: not reproduced with the interior tile patches used here.'
]);
section(summary,29,'Measurement limits','J');
link(summary,'J29',path.join(root,'docs/TEST_EO_CAMERA_CONTENT_20261007.md'),'Method');
lines(summary,30,[
  'Input identity uses whole-active-raster CRC plus a separate 96 × 96 patch CRC. Equality is not collision-free byte proof.',
  'ILA upload leaves gaps. Only consecutive raster sequences are compared. Short-block endpoints bias simple change fractions.',
  'The input update rate is raster rate divided by the observed, uniform spacing between changes. No physical exposure count is claimed.',
  'Each condition records its actual readback image, whether readback was before or after capture, and any intervening FPGA reloads.',
  'New 30/60 Hz diagnostics differ only in timer period at RTL. Trigger-derived DDR epochs change too; input CRC is measured before DDR.',
  'Some short-shutter USB patches were black. Useful patches and full-frame hashes support the reported output rates.',
  'Panorama camera labels are geometric expectations. No lens-cover identification test was performed.'
]);
section(summary,38,'State after the 30 Hz exposure sweep on 7 October','J');
link(summary,'J38',path.join(sweep30Root,'final_state.json'),'State record');
lines(summary,39,[
  restored30.diagnostic_video_summary,
  restored30.diagnostic_video_limit,
  `The original working 60 Hz image was restored at ${restored30.restored_local}. Final display: EO camera 1. All OSD menus closed.`,
  'Latest starting settings restored: all shutters 1/240 s, AGC 0 dB. Camera 1 FreeRun; cameras 2–6 ExtTrig.',
  'Camera 2 readback: trigger/strobe polarities OFF, trigger/strobe delays 0.0, strobe width 1.0.',
  'EO pitch offsets remain alternating −500/+500 centidegrees, all rolls zero. IR offsets remain zero.',
  'No QSPI write, camera power cycle, MCU firmware flash or OSD SAVE occurred. The original top-level RTL was restored.'
]);
header(summary,'A47:D47',['Post-sweep video check','Updates/s','USB grabs','Non-adjacent revisits']);
cell(summary,'A48','Camera 1 FreeRun');cell(summary,'A49','Camera 2 ExtTrig');
section(summary,52,'Validation and interpretation','J');
link(summary,'J52',path.join(sweep30Root,'sweep_validation.json'),'Evidence checks');
lines(summary,53,[
  'Monitor simulation covered independent CRC vectors, repeated/changed content, six mailboxes and full 1080p geometry.',
  'The decoder test covered gaps and incomplete reports. All included USB patch archives matched their saved hash timelines.',
  restored30.timing_summary,
  `${sweepData.reduce((n,x)=>n+x.data.complete_reports,0).toLocaleString()} reports at 60 Hz + ${sweep30Data.reduce((n,x)=>n+x.data.complete_reports,0).toLocaleString()} at 30 Hz + 1,938 earlier. Local evidence links require the original files.`,
  'A further 612-report 60 Hz reference uses today’s controls (Exposure Sweep, row 194). Earlier ILA / USB evidence is preserved.'
]);

const detailStart=34,detailEnd=detailStart+sweepData.length*6-1;
base(sweep,'V234',[19,12,12,14,12,14,12,11,11,12,15,12,3,24,22,10,11,12,12,12,12,35]);
sweep.tabColor=blue;
title(sweep,'Exposure sweeps · 60 Hz above, 30 Hz from row 98','V');
cell(sweep,'A3','7 October 2026, starting 19:15 KST. Camera 2 ExtTrig, AGC 0 dB; all other camera settings held fixed.');
cell(sweep,'A4','Each point: 12 segmented ILA blocks. Whole-active-raster CRC identifies pixel changes before DDR. OSD setting verified separately.');
header(sweep,'A6:L6',['Acquisition','Shutter\n(1/n s)','Exposure\n(ms)','Raster rate\n(rasters/s)','Change spacing\n(rasters)','Input content\n(updates/s)','Complete\nreports','Changed\npairs','Repeated\npairs','Spacing\nobservations','Trigger\n(Hz)','Readback\ntiming']);
header(sweep,'M6:V6',['—','Raw result','OSD readback','Camera mode','AGC (dB)','Blocks','Readback image','ILA image','Geometry','Protocol record']);
let detailRow=detailStart;
for(let i=0;i<sweepData.length;i++){
 const {config:c,data:d}=sweepData[i],r=7+i,m=d.cameras['2'],f=m.content.crc,sp=Object.keys(f.change_spacing_rasters);
 assert.equal(sp.length,1,`${c.tag}: nonuniform cadence needs explicit treatment`);
 assert.deepEqual(Object.keys(c.trigger_hz_observed),['60']);
 sweep.getRange(`A${r}:L${r}`).values=[[c.tag,c.shutter_denominator,null,m.raster_hz,Number(sp[0]),null,m.reports,f.changed,f.duplicate,f.change_spacing_rasters[sp[0]],60,c.osd_readback_timing]];
 formula(sweep,`C${r}`,`=1000/B${r}`);formula(sweep,`F${r}`,`=D${r}/E${r}`);
 link(sweep,`N${r}`,path.join(sweepRoot,c.tag,'summary.json'),'ILA summary');
 link(sweep,`O${r}`,path.join(sweepRoot,c.osd_readback),'Verified camera OSD');
 link(sweep,`V${r}`,path.join(sweepRoot,c.tag,'configuration.json'),'Setting / reload record');
 sweep.getRange(`P${r}:U${r}`).values=[['ExtTrig',0,12,'Working 60 Hz','Content monitor','Valid']];
 for(let cam=1;cam<=6;cam++,detailRow++){
  const x=d.cameras[cam],m=x.content.crc,keys=Object.keys(m.change_spacing_rasters),roi=Object.keys(x.content.roi_crc.change_spacing_rasters);
  assert.equal(keys.length,1);assert.deepEqual(Object.keys(x.flags),['3']);
  assert.deepEqual(Object.keys(x.geometry),['2073600 pixels, 1080 active lines, 1125 EAV']);
  assert.equal(Number(keys[0]),cam===1?1:cam===2?Number(sp[0]):2);
  const q=detailRow;
  sweep.getRange(`A${q}:L${q}`).values=[[c.tag,cam,cam===1?1000/60:cam===2?c.exposure_ms:null,x.raster_hz,Number(keys[0]),null,x.reports,m.changed,m.duplicate,m.change_spacing_rasters[keys[0]],60,roi.length===1?Number(roi[0]):'Mixed']];
  formula(sweep,`F${q}`,`=D${q}/E${q}`);
  link(sweep,`N${q}`,path.join(sweepRoot,c.tag,'summary.json'),'Raw result');
  cell(sweep,`O${q}`,cam===1?'FreeRun':'ExtTrig');
  link(sweep,`V${q}`,path.join(sweepRoot,c.tag,'configuration.json'),'Condition record');
  sweep.getRange(`P${q}:U${q}`).values=[[3,1080,2073600,1125,x.missed_between_reports,d.incomplete_mailboxes]];
 }
}
sweep.getRange(`A7:A${lastSweep}`).format.wrapText=true;sweep.getRange(`A7:L${lastSweep}`).format.rowHeight=32;
sweep.getRange(`C7:D${lastSweep}`).setNumberFormat('0.000');sweep.getRange(`F7:F${lastSweep}`).setNumberFormat('0.00');
sweep.getRange(`K7:L${lastSweep}`).format.horizontalAlignment='center';
sweep.getRange(`Q7:R${lastSweep}`).format.horizontalAlignment='center';
sweep.getRange(`P7:U${lastSweep}`).format.wrapText=true;
sweep.tables.add(`A6:V${lastSweep}`,true,'ExposureSummary');sweep.freezePanes.freezeRows(5);sweep.freezePanes.freezeColumns(2);
section(sweep,18,'How to read this experiment','L');
lines(sweep,19,[
 'Rates count changed transmitted pixel payloads, not physical sensor exposures or accepted electrical triggers.',
 'The raster period remains ~33.333 ms. Shutter values are camera-menu settings; the actual sensor integration time was not measured.',
 'Only camera 2 shutter was changed. The menu was closed before each ILA acquisition; ExtTrig and AGC remained unchanged.',
 'Working video image enables OSD readback. The diagnostic input-monitor image has black output; its screenshots are not readback.',
 'Before/after records identify readback timing. No shutter writes intervene between a captured condition and its matching readback.',
 'Adjacent setting pairs share one diagnostic load; pairs are separated by a working-image readback and diagnostic reload.',
 'CRC spacing uses only consecutive raster sequences. Gaps and incomplete mailbox packets are excluded; each row retains the raw counts.',
 'Whole-raster CRC determines the rate. A dark central ROI can miss changes at short shutter settings; ROI spacing is reported separately.',
 `Fresh sweep: ${sweepData.reduce((n,x)=>n+x.data.complete_reports,0).toLocaleString()} complete raster reports across ${sweepData.length} conditions and all six cameras.`,
 'Camera 3–6 exposure settings were not read back; they act as unchanged controls. See the earlier ILA and USB sheets for prior experiments.',
 'Each setting contains about 3 seconds of adjacent-raster comparisons per camera spread over 12 blocks; this is not a continuous long-duration test.',
 'The shutter boundary is an observed menu-setting boundary. Accepted-trigger count, sensor integration and internal camera scheduling remain unmeasured.'
]);
link(sweep,'N19',path.join(sweepRoot,'sweep_index.json'),'Sweep configuration index');
link(sweep,'N21',path.join(sweepRoot,'final_state.json'),'Final restoration record');
link(sweep,'N23',path.join(sweepRoot,'osd/initial_cam2_trigger.png'),'Initial trigger OSD');
link(sweep,'N25',path.join(sweepRoot,'osd/final_cam2_trigger.png'),'Final trigger OSD');
section(sweep,31,'All six camera inputs · geometry and control checks','L');
header(sweep,'A33:L33',['Acquisition','Camera','Exposure\n(ms)','Raster rate\n(rasters/s)','Change spacing\n(rasters)','Input content\n(updates/s)','Complete\nreports','Changed\npairs','Repeated\npairs','Spacing\nobservations','Trigger\n(Hz)','ROI spacing\n(rasters)']);
header(sweep,'P33:U33',['Flags','Active lines','Y/C samples','EAV markers','Missed rasters','Partial reports*']);
header(sweep,'M33:O33',['—','Raw result','Camera mode']);header(sweep,'V33:V33',['Condition record']);
sweep.getRange(`A${detailStart}:A${detailEnd}`).format.wrapText=true;sweep.getRange(`A${detailStart}:L${detailEnd}`).format.rowHeight=32;
sweep.getRange(`C${detailStart}:D${detailEnd}`).setNumberFormat('0.000');sweep.getRange(`F${detailStart}:F${detailEnd}`).setNumberFormat('0.00');
sweep.getRange(`G${detailStart}:K${detailEnd}`).setNumberFormat('#,##0');sweep.getRange(`P${detailStart}:U${detailEnd}`).setNumberFormat('#,##0');
sweep.tables.add(`A33:V${detailEnd}`,true,'ExposureControls');
cell(sweep,`A${detailEnd+2}`,'*Partial-report count is for the whole acquisition, repeated for each camera. Do not sum it across cameras. Flags 3 = complete and geometry valid.');

section(sweep,98,'30 Hz fixed-timer trigger · fresh camera-2 sweep','V');
cell(sweep,'A99','Same eight shutter choices and two return tests. Camera 1 FreeRun at 1/240 s; cameras 3–6 ExtTrig at 1/240 s, held fixed.');
header(sweep,'A100:V100',sweep.getRange('A6:V6').values[0]);
header(sweep,'A130:V130',sweep.getRange('A33:V33').values[0]);
for(let i=0;i<sweep30Data.length;i++){
 const {config:c,data:d}=sweep30Data[i],r=101+i,x=d.cameras['2'],m=x.content.crc,keys=Object.keys(m.change_spacing_rasters);
 assert.equal(keys.length,1,'Mixed 30 Hz cadence needs explicit treatment');
 assert.deepEqual(Object.keys(c.trigger_hz_observed),['30']);
 sweep.getRange(`A${r}:L${r}`).values=[[c.tag,c.shutter_denominator,null,x.raster_hz,Number(keys[0]),null,x.reports,m.changed,m.duplicate,m.change_spacing_rasters[keys[0]],30,c.osd_readback_timing]];
 formula(sweep,`C${r}`,`=1000/B${r}`);formula(sweep,`F${r}`,`=D${r}/E${r}`);
 link(sweep,`N${r}`,path.join(sweep30Root,c.tag,'summary.json'),'ILA summary');
 link(sweep,`O${r}`,path.join(sweep30Root,c.osd_readback),'Verified camera OSD');
 link(sweep,`V${r}`,path.join(sweep30Root,c.tag,'configuration.json'),'Setting / reload record');
 sweep.getRange(`P${r}:U${r}`).values=[['ExtTrig',0,12,c.readback_image||'Working 60 Hz','30 Hz content monitor','Valid']];
 for(let cam=1;cam<=6;cam++){
   const q=131+i*6+cam-1,y=d.cameras[cam],f=y.content.crc,sp=Object.keys(f.change_spacing_rasters),roi=Object.keys(y.content.roi_crc.change_spacing_rasters);
   assert.equal(sp.length,1);assert.deepEqual(Object.keys(y.flags),['3']);
   assert.deepEqual(Object.keys(y.geometry),['2073600 pixels, 1080 active lines, 1125 EAV']);
   sweep.getRange(`A${q}:L${q}`).values=[[c.tag,cam,cam===2?c.exposure_ms:1000/240,y.raster_hz,Number(sp[0]),null,y.reports,f.changed,f.duplicate,f.change_spacing_rasters[sp[0]],30,roi.length===1?Number(roi[0]):'Mixed']];
   formula(sweep,`F${q}`,`=D${q}/E${q}`);
   link(sweep,`N${q}`,path.join(sweep30Root,c.tag,'summary.json'),'Raw result');
   cell(sweep,`O${q}`,cam===1?'FreeRun':'ExtTrig');
   link(sweep,`V${q}`,path.join(sweep30Root,c.tag,'configuration.json'),'Condition record');
   sweep.getRange(`P${q}:U${q}`).values=[[3,1080,2073600,1125,y.missed_between_reports,d.incomplete_mailboxes]];
 }
}
for(const [a,b] of [[101,110],[131,190]]){
 sweep.getRange(`A${a}:A${b}`).format.wrapText=true;sweep.getRange(`A${a}:L${b}`).format.rowHeight=32;
 sweep.getRange(`C${a}:D${b}`).setNumberFormat('0.000');sweep.getRange(`F${a}:F${b}`).setNumberFormat('0.00');
 sweep.getRange(`G${a}:K${b}`).setNumberFormat('#,##0');
}
sweep.getRange('P101:U110').format.wrapText=true;
sweep.getRange('K101:L110').format.horizontalAlignment='center';
sweep.getRange('Q101:R110').format.horizontalAlignment='center';
sweep.tables.add('A100:V110',true,'ExposureSummary30');
sweep.tables.add('A130:V190',true,'ExposureControls30');
section(sweep,113,'30 Hz protocol, trigger evidence and comparison limits','L');
lines(sweep,114,[
 'Fixed timer period: 2,475,000 cycles of nominal 74.25 MHz = 33.333 ms. Pulse high: 148,500 cycles = 2.000 ms.',
 'Live probe11 counts 30 common trigger edges per nominal one-second window; quantized trigger-period observations are retained per point.',
 'The source differs from the 60 Hz content-monitor archive only in the timer-period literal. Sensor integration and accepted triggers are unmeasured.',
 'This fixed-timer experiment is separate from the earlier strobe-following 30 Hz USB experiment retained on USB Results.',
 'All six starting shutters were freshly read back as 1/240 s. Camera 1 is FreeRun; cameras 2–6 are ExtTrig; all AGC values are 0 dB.',
 'Camera 1 was 1/60 s in the prior sweep; prior camera 3–6 shutter values were not read back. Control differences cannot be assigned to trigger rate alone.',
 'Camera 2 uses the same verified shutter choices, trigger mode, polarities and delays as the 60 Hz sweep. Only its shutter varies within this run.',
 ...restored30.protocol_lines,
 'All settings use 12 capture blocks; gaps and partial reports are excluded. Complete 1080p geometry is checked for all six inputs.',
 'Return-to-1/30 is a test point. Final restoration is to the actual starting 1/240 s and the working 60 Hz FPGA image.'
]);
link(sweep,'N114',path.join(sweep30Root,'sweep_index.json'),'30 Hz sweep index');
link(sweep,'N116',path.join(root,'builds/bit_archive/20261007_contentmon_trig30_e462da6/build_validation.json'),'Build / timing / simulation');
link(sweep,'N118',path.join(sweep30Root,'initial_state.json'),'All six initial readbacks');
link(sweep,'N120',path.join(sweep30Root,'sweep_validation.json'),'Measurement checks');
link(sweep,'N122',path.join(sweep30Root,'final_state.json'),'Restoration record');
section(sweep,128,'30 Hz run · all six inputs and raw control observations','L');
cell(sweep,'A192','*Partial count belongs to the whole acquisition, repeated beside each camera. Rates indicate transmitted payload novelty, not physical exposures.');
section(sweep,194,'Fresh 60 Hz reference with today’s control settings','V');
cell(sweep,'A195','Camera 2: ExtTrig 1/30 s. Cameras 1 and 3–6: 1/240 s. This reference separates changed control settings from a trigger-rate effect.');
header(sweep,'A196:V196',sweep.getRange('A33:V33').values[0]);
const ref60=await read(path.join(sweep30Root,'input_reference60_shutter30/summary.json'));
for(let cam=1;cam<=6;cam++){
 const q=196+cam,y=ref60.cameras[cam],f=y.content.crc,sp=Object.keys(f.change_spacing_rasters);
 assert.equal(sp.length,1);assert.deepEqual(Object.keys(y.flags),['3']);
 sweep.getRange(`A${q}:L${q}`).values=[['Current 60 Hz reference',cam,1000/(cam===2?30:240),y.raster_hz,Number(sp[0]),null,y.reports,f.changed,f.duplicate,f.change_spacing_rasters[sp[0]],60,Number(Object.keys(y.content.roi_crc.change_spacing_rasters)[0])]];
 formula(sweep,`F${q}`,`=D${q}/E${q}`);
 link(sweep,`N${q}`,path.join(sweep30Root,'input_reference60_shutter30/summary.json'),'Raw result');
 cell(sweep,`O${q}`,cam===1?'FreeRun':'ExtTrig');
 link(sweep,`V${q}`,path.join(sweep30Root,'input_reference60_shutter30/configuration.json'),'Condition record');
 sweep.getRange(`P${q}:U${q}`).values=[[3,1080,2073600,1125,y.missed_between_reports,ref60.incomplete_mailboxes]];
}
sweep.getRange('A197:A202').format.wrapText=true;sweep.getRange('A197:L202').format.rowHeight=32;
sweep.getRange('C197:D202').setNumberFormat('0.000');sweep.getRange('F197:F202').setNumberFormat('0.00');
sweep.tables.add('A196:V202',true,'CurrentReference60');

base(ila,'U119',[19,7,12,11,11,11,11,12,13,13,12,12,15,11,10,9,3,26,12,12,12]);
title(ila,'Raw-input ILA measurements','U');
cell(ila,'A3','Full active Y/C payload, before DDR. Cameras 2–6 ExtTrig per user; camera 2 verified by OSD. Camera 1 FreeRun.');
cell(ila,'A4','Cadence = measured raster rate / observed uniform change spacing. Camera 3–6 shutters were not read back.');
header(ila,'A6:P6',['Acquisition','Camera','Shutter\n(ms)','Complete\nreports','Consecutive\npairs','Changed\npairs','Repeated\npairs','Change spacing\n(rasters)','Raster rate\n(rasters/s)','Content rate\n(updates/s)','Spacing\nobservations','Patch spacing\n(rasters)','Active\nY/C samples','Active\nlines','Total EAV\nmarkers','Flags']);
cell(ila,'R6','Source');cell(ila,'S6','Missed rasters');cell(ila,'T6','Blocks');cell(ila,'U6','Partial reports*');
ila.getRange('R6:U6').format.font.bold=true;ila.getRange('R6:U6').format.wrapText=true;
const acquisitions=[['input_original','Original settings',12,1000/30],['input_shutter240','Short shutter',12,1000/240],['input_restored30','Restored settings',12,1000/30],['content_smoke','Initial smoke run',2,1000/30]];
let rr=7;
for(const [folder,label,blocks,shutter] of acquisitions){
 const data=await read(path.join(evidence,folder,'summary.json'));
 for(let cam=1;cam<=6;cam++,rr++){
  const c=data.cameras[cam],m=c.content.crc,sp=Object.keys(m.change_spacing_rasters),roi=Object.keys(c.content.roi_crc.change_spacing_rasters);
  assert.equal(sp.length,1);assert.equal(roi.length,1);assert.deepEqual(Object.keys(c.flags),['3']);
  assert.deepEqual(Object.keys(c.geometry),['2073600 pixels, 1080 active lines, 1125 EAV']);
  ila.getRange(`A${rr}:P${rr}`).values=[[label,cam,cam===1?1000/60:cam===2?shutter:null,c.reports,m.consecutive_pairs,m.changed,m.duplicate,Number(sp[0]),c.raster_hz,null,m.change_spacing_rasters[sp[0]],Number(roi[0]),2073600,1080,1125,3]];
  formula(ila,`J${rr}`,`=I${rr}/H${rr}`);
  link(ila,`R${rr}`,path.join(evidence,folder,'summary.json'),`${label} JSON`);
  ila.getRange(`S${rr}:U${rr}`).values=[[c.missed_between_reports,blocks,data.incomplete_mailboxes]];
 }
}
stripe(ila,7,30,'P');ila.getRange('C7:C30').setNumberFormat('0.000');ila.getRange('D7:H30').setNumberFormat('#,##0');
ila.getRange('I7:I30').setNumberFormat('0.00000');ila.getRange('J7:J30').setNumberFormat('0.00');ila.getRange('K7:P30').setNumberFormat('#,##0');
ila.getRange('S7:U30').setNumberFormat('#,##0');ila.freezePanes.freezeRows(6);ila.freezePanes.freezeColumns(2);
header(ila,'Q6:U6',['—','Source','Missed rasters','Blocks','Partial reports*']);
ila.tables.add('A6:U30',true,'InputMeasurements');
section(ila,33,'Protocol and configuration evidence','P');
lines(ila,34,[
  '*Partial reports are counts for the whole acquisition, repeated beside each camera. Do not sum them across cameras.',
  'Missed rasters occur between capture blocks during upload and are excluded from adjacent-payload comparisons.',
  'Flags 3 means a complete report with valid geometry. Central-patch change spacing agrees with whole-raster spacing in every row.',
  'A checksum change is a pixel-payload change. CRC collision risk and sensor/ISP behavior limit claims about physical exposures.',
  'Timing assumes the nominal 74.25 MHz HD clock. All main acquisitions independently report a 60 Hz trigger on probe11.',
  'Manual trigger polarity OFF corresponds to the falling edge. The manual timing sketch does not define a maximum exposure rate.'
]);
const refs=[
 ['Original shutter before intervention','osd/preinput_shutter30.png','Camera 2: 1/30 s'],
 ['Short shutter setting','osd/preinput_shutter240.png','Camera 2: 1/240 s'],
 ['Trigger mode during short-shutter test','osd/preinput_exttrig240.png','ExtTrig remained selected'],
 ['Final shutter readback','osd/final_shutter30_readback.png','Camera 2 restored to 1/30 s'],
 ['Final trigger-mode readback','osd/final_exttrig_readback.png','ExtTrig and original timing settings'],
 ['Return command log','osd/input_restore30_command_black.json','Restored during diagnostic load; OSD verified afterward'],
 ['Trigger timing manual','manual/ext_trigger_timing.png','DM-G15-42 v1.04, printed page 41'],
 ['Final restoration record','final_state.json','Original working FPGA image, display camera 1'],
 ['DDR calibration result','diag_mig_console.txt','Calibration passed despite diagnostic black output'],
 ['Complete test narrative','../../docs/TEST_EO_CAMERA_CONTENT_20261007.md','Methods, qualifications and final state'],
 ['Reviewed handoff','../../docs/HANDOFF_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md','Manufacturer statement is quoted secondhand here']
];
refs.forEach(([name,p,note],i)=>{const r=42+i;cell(ila,`A${r}`,name);link(ila,`E${r}`,path.resolve(evidence,p),'Open evidence');cell(ila,`G${r}`,note);});
lines(ila,55,[
 'Diagnostic archive: 20261007_contentmon_e462da6. Matching LTX and decoder are required; probe12 is repurposed.',
 'Operational archive restored: 20261006_221847_trsmon_trig60_9a8a81e. Diagnostic video output remains unqualified.',
 'CRC algorithm: CRC-32/MPEG-2 recurrence, initial FFFFFFFF, no reflection/final XOR; Y then C, most significant bit first.',
 'A frame report contains full CRC, patch CRC, pixel/line counts, sequence, flags and timestamp. Sequence is excluded from CRC.'
]);
link(ila,'A61',path.join(root,'builds/bit_archive/20261007_contentmon_e462da6/README.md'),'Diagnostic archive readme');
lines(ila,63,[
 'Withdrawn metric: DDR descriptor epoch labels are trigger-derived identifiers, not a frame publication count. The old ~30-label/s result is excluded.',
 'TRS frame starts and EAV counts alone cannot prove fresh content. Complete payload geometry and raw-input CRCs supply the additional evidence here.'
]);
link(ila,'A66',path.join(root,'docs/REVIEW_EO_CAM_TRIGGER_RATE_FINDINGS_20261006.md'),'Independent handoff review');

base(usb,'O62',[27,19,11,12,10,12,12,13,13,12,13,3,27,3,65]);
title(usb,'USB output measurements','O');
cell(usb,'A3','USB3 Video capture device. 1920 × 1080 BGR from YUY2. BLAKE2b-128 full-frame and lossless patch hashes.');
cell(usb,'A4','Rate = observed changes / first-to-last grab interval. Shutters left blank were not read back. All times and settings are test records.');
header(usb,'A6:K6',['Acquisition','Observed region','Trigger\n(Hz)','Shutter\n(ms)','USB\ngrabs','Interval\n(s)','Pixel\nchanges','Output updates\n(per second)','USB grab rate\n(per second)','Non-adjacent\nrevisits','Use in rate\nconclusion']);
cell(usb,'M6','Source');cell(usb,'O6','Notes');usb.getRange('M6:O6').format.font.bold=true;
const runs=[
 ['baseline_cam1','Camera 1',60,1000/60,'Included','Initial FreeRun control.'],
 ['baseline_mode1','Camera 1',60,1000/60,'Included','Repeat FreeRun baseline.'],
 ['baseline_mode2','Camera 2',60,1000/30,'Included','Initial ExtTrig.'],
 ['baseline_mode3','Camera 3',60,null,'Included','ExtTrig per user. Shutter not read back.'],
 ['baseline_mode4','Camera 4',60,null,'Included','ExtTrig per user. Shutter not read back.'],
 ['baseline_mode5','Camera 5',60,null,'Included','ExtTrig per user. Shutter not read back.'],
 ['baseline_mode6','Camera 6',60,null,'Included','ExtTrig per user. Shutter not read back.'],
 ['cam2_free_prebuild','Camera 2',60,null,'Included','FreeRun intervention. Its shutter was not read back.'],
 ['cam2_ext_return_prebuild','Camera 2',60,1000/30,'Included','Returned to ExtTrig.'],
 ['cam2_ext_shutter60_prebuild','Camera 2',60,1000/60,'Included','ExtTrig with OSD-verified 1/60 s shutter.'],
 ['cam2_ext_shutter240_prebuild','Camera 2',60,1000/240,'Included','Full-frame result. Central patch was black and excluded.'],
 ['cam2_ext_shutter240_repeat','Camera 2',60,1000/240,'Included','Four useful patches agreed with the whole image.'],
 ['cam2_ext_shutter30_restored','Camera 2',60,1000/30,'Included','Restored shutter. Five patches agreed.'],
 ['trig30_cam2_shutter30','Camera 2',30,1000/30,'Included','Nominal 30 Hz trigger. Original shutter.'],
 ['trig30_cam2_shutter240','Camera 2',30,1000/240,'Included','Three useful patches agreed. Central patch excluded.'],
 ['trig30_cam2_restored','Camera 2',30,1000/30,'Included','Same-image return to original shutter.'],
 ['trig30_cam2_shutter100','Camera 2',30,1000/120,'Included','OSD says 1/120 s. The provisional folder name is wrong.'],
 ['baseline_mode14','Panorama full image',60,null,'Context','Whole-image novelty is not a per-camera measurement.'],
 ['diag_cam2_shutter30','Camera 2',60,1000/30,'Excluded','Diagnostic black output. Not a camera-rate measurement.'],
 ['final_cam2','Camera 2',60,1000/30,'Included','Final original image and ExtTrig shutter restored.'],
 ['final_cam1','Camera 1',60,1000/60,'Included','Final displayed FreeRun camera. Live video verified.']
];
const usbRows={};rr=7;
for(const [folder,region,trig,shutter,use,note] of runs){
 const d=await read(path.join(evidence,folder,'metadata.json')),m=d.metrics.full;
 usbRows[folder]=rr;
 usb.getRange(`A${rr}:K${rr}`).values=[[folder,region,trig,shutter,m.grabs,d.interval_s,m.transitions,null,d.grab_hz,m.revisits,use]];
 formula(usb,`H${rr}`,`=G${rr}/F${rr}`);link(usb,`M${rr}`,path.join(evidence,folder,'metadata.json'),'Capture metadata');cell(usb,`O${rr}`,note);rr++;
}
const pano=await read(path.join(evidence,'baseline_mode14/metadata.json'));
for(let cam=1;cam<=6;cam++,rr++){
 const m=pano.metrics[`cam${cam}_expected`];
 usb.getRange(`A${rr}:K${rr}`).values=[['baseline_mode14',`Expected tile ${cam}`,60,cam===1?1000/60:cam===2?1000/30:null,m.grabs,pano.interval_s,m.transitions,null,pano.grab_hz,m.revisits,'Included']];
 formula(usb,`H${rr}`,`=G${rr}/F${rr}`);link(usb,`M${rr}`,path.join(evidence,'baseline_mode14/roi_map.png'),'Panorama ROI map');cell(usb,`O${rr}`,'Interior patch. Geometric camera identity not intervention-verified.');
}
for(const [folder,region,shutter,note] of [
 ['usb_initial_cam2','Camera 2',1000/30,'Fresh exposure-sweep baseline. Working 60 Hz image, ExtTrig.'],
 ['usb_final_cam2','Camera 2',1000/30,'Fresh sweep restoration. ExtTrig, 1/30 s verified.'],
 ['usb_final_cam1','Camera 1',1000/60,'Final displayed camera; FreeRun control.']
]){
 const d=await read(path.join(sweepRoot,folder,'metadata.json')),m=d.metrics.full;
 usbRows[folder]=rr;
 usb.getRange(`A${rr}:K${rr}`).values=[[folder,region,60,shutter,m.grabs,d.interval_s,m.transitions,null,d.grab_hz,m.revisits,'Included']];
 formula(usb,`H${rr}`,`=G${rr}/F${rr}`);link(usb,`M${rr}`,path.join(sweepRoot,folder,'metadata.json'),'Fresh capture metadata');cell(usb,`O${rr}`,note);rr++;
}
for(const [folder,region,note] of [
 ['usb_initial_cam2','Camera 2','Before 30 Hz run: actual starting shutter 1/240 s; working 60 Hz image.'],
 ['usb_final_cam2','Camera 2','After 30 Hz run: actual starting 1/240 s restored; working 60 Hz image.'],
 ['usb_final_cam1','Camera 1','After 30 Hz run: untouched FreeRun 1/240 s; final displayed camera.']
]){
 const d=await read(path.join(sweep30Root,folder,'metadata.json')),m=d.metrics.full,key=`run30_${folder}`;
 usbRows[key]=rr;
 usb.getRange(`A${rr}:K${rr}`).values=[[key,region,60,1000/240,m.grabs,d.interval_s,m.transitions,null,d.grab_hz,m.revisits,'Included']];
 formula(usb,`H${rr}`,`=G${rr}/F${rr}`);link(usb,`M${rr}`,path.join(sweep30Root,folder,'metadata.json'),'Latest capture metadata');cell(usb,`O${rr}`,note);rr++;
}
const last=rr-1;stripe(usb,7,last,'K');usb.getRange(`D7:D${last}`).setNumberFormat('0.000');
usb.getRange(`E7:E${last}`).setNumberFormat('#,##0');usb.getRange(`F7:F${last}`).setNumberFormat('0.000');
usb.getRange(`G7:G${last}`).setNumberFormat('#,##0');usb.getRange(`H7:I${last}`).setNumberFormat('0.000');usb.getRange(`J7:J${last}`).setNumberFormat('0');
usb.getRange(`A7:A${last}`).format.font.size=10;
usb.getRange(`A7:A${last}`).format.wrapText=true;usb.getRange(`A7:K${last}`).format.rowHeight=32;
usb.getRange(`K7:K${last}`).conditionalFormats.add('containsText',{text:'Excluded',format:{fill:orange,font:{bold:true,color:'#8A4A08'}}});
header(usb,'L6:O6',['—','Source','·','Notes']);
usb.getRange(`J7:K${last}`).format.horizontalAlignment='center';
usb.tables.add(`A6:O${last}`,true,'OutputMeasurements');usb.freezePanes.freezeRows(6);usb.freezePanes.freezeColumns(2);
section(usb,42,'Acquisition notes','K');
lines(usb,43,[
 'Early baseline acquisitions encoded PNGs during collection, causing a brief stall. Later captures moved PNG encoding after acquisition.',
 'Grab rates are retained above. Output rates are based on actual elapsed time and are not rounded to expected camera rates.',
 'The earlier USB image measured 29.999370 Hz over 256 trigger intervals, using a slightly modulated strobe source. Fresh ILA tests use a fixed timer.',
 'Switching the trigger image also changes DDR epoch timing. The same-image shutter tests provide the cleaner intervention.',
 'A central patch can be too dark to detect novelty. Short-shutter conclusions use full-frame hashes and other useful patches.',
 'All saved patch archives matched their hash timelines. New fixed-30-Hz raw-input measurements are on Exposure Sweep, starting row 98.'
]);
link(usb,'A49',path.join(evidence,'patch_verification.json'),'Prior patch integrity results');
link(usb,'E49',path.join(evidence,'trig30_edges/trigger_summary.json'),'30 Hz trigger intervals');
link(usb,'I49',path.join(sweep30Root,'final_state.json'),'Latest restored state');
link(usb,'A51',path.join(root,'docs/TEST_EO_CAMERA_CONTENT_20261007.md'),'Earlier written report');
link(usb,'E51',path.join(sweepRoot,'patch_verification.json'),'Fresh patch integrity results');
link(usb,'I51',path.join(sweep30Root,'patch_verification.json'),'Latest patch integrity');
for(const [target,key] of [[48,'run30_usb_final_cam1'],[49,'run30_usb_final_cam2']]){
 for(const [dest,col] of [['B','H'],['C','E'],['D','J']])formula(summary,`${dest}${target}`,`=SUMIF('USB Results'!$A$7:$A$${last},"${key}",'USB Results'!$${col}$7:$${col}$${last})`);
}
summary.getRange('B48:B49').setNumberFormat('0.000');summary.getRange('C48:D49').setNumberFormat('#,##0');

// Format change experiment: invalid geometry prevents an accepted content rate.
section(ila,70,'Camera 2 HD-format test · 8 October 2026','U');
cell(ila,'A71','ExtTrig, 1/240 s, AGC 0 dB. Fixed 60 Hz trigger. Same diagnostic load for the format change and return.');
header(ila,'A73:P73',['Camera output','Cam','Trigger\n(Hz)','30-mode shutter\n(1/n s)','Raster starts\n(per second)','Reports','Valid\ngeometry','Invalid\ngeometry','Input updates\n(per second)','Changed\nCRC pairs','Repeated\nCRC pairs','Blocks','ILA result','Rate accepted','Active lines\nminimum','Active lines\nmaximum']);
header(ila,'Q73:U73',['—','Raw result','Protocol','EAV minimum','EAV maximum']);
for(let i=0;i<formatTest.entries.length;i++){
 const e=formatTest.entries[i],r=74+i;
 ila.getRange(`A${r}:P${r}`).values=[[e.label,2,e.trigger_hz,e.shutter_denominator,e.raster_starts_hz,e.camera_reports,e.valid_reports,e.invalid_reports,null,e.crc_changed_pairs,e.crc_repeated_pairs,e.blocks,e.content_rate_accepted?'Valid':'Invalid geometry',e.content_rate_accepted?'Yes':'No',e.active_line_min,e.active_line_max]];
 if(e.content_rate_accepted)formula(ila,`I${r}`,`=E${r}`);else cell(ila,`I${r}`,'Unverified');
 link(ila,`R${r}`,path.join(formatRoot,e.tag,'summary.json'),'ILA summary');
 link(ila,`S${r}`,path.join(formatRoot,e.tag,'configuration.json'),'Setting record');
 ila.getRange(`T${r}:U${r}`).values=[[e.eav_min,e.eav_max]];
}
ila.getRange('A74:U75').format.rowHeight=38;
ila.getRange('A73:U73').format.rowHeight=50;
ila.getRange('A74:D75').format.wrapText=true;
ila.getRange('M74:N75').format.wrapText=true;
ila.getRange('E74:E75').setNumberFormat('0.000');ila.getRange('I74:I75').setNumberFormat('0.000');
ila.getRange('F74:H75').setNumberFormat('#,##0');
ila.getRange('I74').format.fill=orange;ila.getRange('M74:N74').format.fill=orange;
ila.tables.add('A73:U75',true,'FormatChangeMeasurements');
section(ila,78,'Interpretation and limits','U');
lines(ila,79,[
 '60-mode capture: 179 of 179 camera-2 reports have invalid geometry. CRC changes are excluded from fresh-image FPS conclusions.',
 'Return to 1080p/30: 106 of 106 reports valid, with 94 changed and zero repeated adjacent comparisons. Full and patch CRC agree.',
 'The other five cameras retain valid geometry in both captures. Each condition contains 612 total reports across all six inputs.',
 'The 60-mode OSD image was black. Selection was made from the verified 1080p/30 menu; 60 raster starts/s support the format inference.',
 'Manufacturer lists 1080p30, 1080p60 and 720p60 in NTSC. Direct OSD readback of the selected 60-mode text was unavailable.',
 'At an assumed 148.5 MHz CAM1_PCLK, the archived diagnostic has WNS -0.883 ns, TNS -69.112 ns and 162 failing endpoints.',
 'The passive monitor itself passes internal setup (+3.826 ns) and hold (+0.020 ns). External Y/C input delays are unconstrained.',
 'Actual camera PCLK was not measured independently. Capture-path timing failure alone does not identify the raw-input corruption cause.',
 'Decoder CRC-rate estimates for invalid frames remain in raw JSON for provenance. They are not accepted measurements in this report.',
 'Working 60 Hz FPGA image restored. Camera 2 verified at 1080p/30, ExtTrig, 1/240 s, AGC 0 dB. Display restored to camera 3.'
]);
link(ila,'A90',path.join(formatRoot,'format_test_results.json'),'Consolidated test evidence');
cell(ila,'A89','Normal receiver VSYNC counter: 0/s at the 60-mode setting, returning to 30/s at 1080p/30. Raw-monitor markers do not imply valid frames.');
link(ila,'E90',path.join(formatRoot,'timing_cam2_148p5.rpt'),'Full-design timing');
link(ila,'J90',path.join(formatRoot,'contentmon_cam2_timing.json'),'Monitor timing');
link(ila,'N90',path.join(formatRoot,'final_state.json'),'Restored state');
link(ila,'A92',path.join(formatRoot,'osd/initial_special.png'),'Initial 1080p/30 OSD');
link(ila,'E92',path.join(formatRoot,'osd/final_special.png'),'Restored 1080p/30 OSD');
link(ila,'J92',path.join(formatRoot,'osd/final_shutter.png'),'Restored exposure');
link(ila,'N92',path.join(formatRoot,'osd/final_trigger.png'),'Restored trigger');
cell(ila,'A94','Manufacturer format list:');cell(ila,'A95',formatTest.manufacturer_format_reference);
section(summary,60,'Earlier test: full diagnostic at requested 1080p/60 output','J');
header(summary,'A62:D62',['Output setting','Raster starts/s','Valid reports','Input updates/s']);
for(let i=0;i<2;i++){
 const r=63+i,src=74+i;
 for(const [dest,col] of [['A','A'],['B','E'],['D','I']])formula(summary,`${dest}${r}`,`='ILA Results'!${col}${src}`);
 formula(summary,`C${r}`,`='ILA Results'!G${src}&" / "&'ILA Results'!F${src}`);
}
summary.getRange('A63:D64').format.rowHeight=29;summary.getRange('B63:B64').setNumberFormat('0.000');summary.getRange('D63:D64').setNumberFormat('0.000');
summary.getRange('C63:D63').format.fill=orange;
summary.getRange('C63:C64').format.horizontalAlignment='center';
lines(summary,66,[
 'ExtTrig and 1/240 s exposure held fixed. ILA independently confirms 60 Hz trigger in both captures.',
 'At the requested 60-mode setting, video goes black and every camera-2 report has invalid geometry. Fresh-image FPS is unverified.',
 'Changing CRCs can result from corrupted samples. The apparent 60 changes/s in raw decoder output must not be reported as fresh-image FPS.',
 'Returning to 1080p/30 on the same diagnostic load restores valid geometry and about 30 content updates/s.',
 'At the assumed 148.5 MHz input clock, the full diagnostic fails timing. The passive monitor passes its internal timing checks.',
 'The external input timing is unqualified; the precise cause of lost line markers remains unresolved.',
 'Direct OSD text readback at 60-mode was unavailable. The command sequence and 60-Hz raster starts support the 1080p/60 inference.',
 'Working 60 Hz FPGA image and camera-2 starting settings restored. Final display: EO camera 3. All menus closed.'
]);
link(summary,'A76',path.join(formatRoot,'format_test_results.json'),'New test evidence');
cell(summary,'A74','The normal receiver VSYNC counter reads 0/s in 60-mode and returns to 30/s at 1080p/30; only the raw monitor detects ~60 starts/s.');
link(summary,'F76',path.join(formatRoot,'final_state.json'),'Earlier restored state');
section(summary,80,'Dedicated RTL: camera 2 at 1080p/60, 1/240 s exposure','J');
header(summary,'A82:D82',['Format / sampling edge','Raster frames/s','Valid reports','Input updates/s']);
section(ila,99,'Dedicated input RTL validation · 8 October 2026','P');
header(ila,'A101:P101',['Output format','Edge','Trigger\nHz','30-mode setting\n(ms)','PCLK\nMHz','Raster\nframes/s','Reports','Valid\nreports','Changed\npairs','Repeated\npairs','Rasters /\nupdate','Input\nupdates/s','Clocks /\nraster','Clocks /\nline','Y sync\nerrors max','C sync\nerrors max']);
ila.getRange('A101:P101').format.rowHeight=58;
let diagRow=102,summaryRow=83;
for(const entry of diag.entries){
  const clocks=Object.keys(entry.data.pclk_hz_observations).map(Number);
  const measuredClock=(Math.min(...clocks)+Math.max(...clocks))/2/1e6;
  for(const phase of ['rising','falling']){
    const p=entry.data.phases[phase],g=entry.geometry[phase];
    const spacing=p.content_rate_accepted?Number(Object.keys(p.spacing.crc)[0]):'Unverified';
    ila.getRange(`A${diagRow}:P${diagRow}`).values=[[entry.label,phase==='rising'?'Rise':'Fall',60,1000/240,
      measuredClock,p.raster_starts_hz??'No report',p.reports,p.valid_reports,p.crc_changed_pairs,p.crc_repeated_pairs,
      spacing,p.input_updates_hz??'Unverified',g.frame_clocks?.min??'n.a.',g.line_min?.min??'n.a.',g.bad_xy?.max??'n.a.',g.c_sync_bad?.max??'n.a.']];
    cell(summary,`A${summaryRow}`,`${entry.label} / ${phase==='rising'?'rise':'fall'}`);
    formula(summary,`B${summaryRow}`,`='ILA Results'!F${diagRow}`);
    formula(summary,`C${summaryRow}`,`='ILA Results'!H${diagRow}&" / "&'ILA Results'!G${diagRow}`);
    formula(summary,`D${summaryRow}`,`='ILA Results'!L${diagRow}`);
    link(ila,`R${diagRow}`,path.join(diagRoot,entry.tag,'summary.json'),'Capture summary');
    link(ila,`S${diagRow}`,path.join(diagRoot,entry.tag,'decoded_frames.csv'),'Raw reports');
    if(!p.content_rate_accepted)summary.getRange(`B${summaryRow}:D${summaryRow}`).format.fill=orange;
    diagRow++;summaryRow++;
  }
}
ila.tables.add('A101:P107',true,'DedicatedInputMeasurements');
ila.getRange('D102:F107').setNumberFormat('0.000');ila.getRange('L102:L107').setNumberFormat('0.000');
ila.getRange('M102:N107').setNumberFormat('#,##0');ila.getRange('A102:P107').format.rowHeight=28;
for(const range of ['F104','K104:P104'])ila.getRange(range).format.horizontalAlignment='right';
summary.getRange('B83:B88').setNumberFormat('0.000');summary.getRange('D83:D88').setNumberFormat('0.000');
summary.getRange('A83:D88').format.rowHeight=29;summary.getRange('C83:C88').format.horizontalAlignment='center';
lines(summary,90,[
 '1080p/60: falling-edge sampling gives 256/256 valid reports and 248/248 changed adjacent pairs. Full-frame and region CRCs agree on cadence.',
 'Measured PCLK is about 148.498 MHz and the raster/content rates are about 60/s. The rising-edge monitor produced no complete reports.',
 'The 1080p/30 control and return capture each give 128 valid reports per edge and about 30 input content updates/s.',
 'Dedicated RTL passes routed timing at 148.5 MHz: setup +2.345 ns, hold +0.010 ns, pulse width +2.825 ns. The full video design is unchanged.',
 'External input timing uses a zero-reference model, not measured camera/PCB bounds. Clean live sync and geometry qualify this measurement.',
 'These three initial conditions use 60 Hz trigger and 1/240 s exposure. The subsequent slower-shutter sweep starts at row 103.',
 'The diagnostic has no video output. The format transition is supported by paired OSD commands, measured PCLK and valid 1080p raster geometry.',
 'Working FPGA image and 1080p/30 ExtTrig, 1/240 s, 0 dB settings restored. Final display: camera 3; menus closed.'
]);
link(summary,'A99',path.join(diagRoot,'live_results.json'),'Dedicated test evidence');
link(summary,'F99',path.join(diagRoot,'final_state.json'),'Initial diagnostic restoration');
lines(ila,110,[
 'Input samples are observed before DDR. Phase reports use 27 MHz timestamps and are checked for 1920 × 1080 active samples, 1125 EAVs and 2200 clocks/line.',
 'The 1080p/60 falling phase has zero Y-parity and C-sync errors. No complete rising-phase reports were produced; a missing report is not a measured zero FPS.',
 'PCLK shown is the midpoint of observed counter values, rounded for display. Frequency quantization is ±256 Hz relative to the uncalibrated 27 MHz reference.',
 'Capture blocks contain gaps during JTAG upload. Only consecutive sequence numbers form CRC pairs; gaps and partial mailboxes are excluded from cadence comparisons.',
 'The first IDDRE1 trial failed the HD-bank primitive minimum-period requirement and produced no bitstream. The delivered design uses explicitly timed fabric SDR registers.',
 'CRC changes measure received pixel payload updates, not direct sensor exposure counts. The new 60-mode observation does not replace earlier 30-format exposure results.'
]);
link(ila,'A118',path.join(root,'builds/eo60_input_20261008_r2/timing_summary.rpt'),'Routed timing');
link(ila,'D118',path.join(root,'builds/eo60_input_20261008_r2/manifest.json'),'Build hashes');
link(ila,'G118',path.join(root,'diagnostics/eo60/README.md'),'RTL procedure');
link(ila,'K118',path.join(diagRoot,'initial_format.png'),'Starting format');
link(ila,'N118',path.join(diagRoot,'final_format.png'),'Restored format');

section(summary,103,'1080p/60 slower shutters · camera 2 · 60 Hz trigger','J');
cell(summary,'A104','ExtTrig, manual shutter, AGC 0 dB. Falling-edge input ILA; eight capture blocks per setting.');
header(summary,'A106:D106',['Shutter setting','Exposure setting\n(ms)','Raster frames/s','Input updates/s']);
section(sweep,208,'1080p/60 output · slower shutters · dedicated input RTL','V');
cell(sweep,'A209','8 October 2026. Camera 2 only. Each condition has its own diagnostic load and visible 1080p/30 shutter readback before and after.');
header(sweep,'A210:L210',['Acquisition','30-mode shutter\n(1/n s)','30-mode setting\n(ms)','Raster rate\n(rasters/s)','Change spacing\n(rasters)','Fresh input FPS','Complete\nreports','Changed\npairs','Repeated\npairs','Spacing\nobservations','Trigger\n(Hz)','ROI spacing\n(rasters)']);
header(sweep,'M210:V210',['—','Raw result','Before OSD','After OSD','PCLK\n(MHz)','Rising\nreports','Valid fall\nreports','Y errors\nmaximum','C errors\nmaximum','Condition / readback review']);
sweep.getRange('A210:V210').format.rowHeight=50;
slow.entries.forEach((e,i)=>{
 const r=211+i,q=107+i,p=e.data.phases.falling,g=e.geometry.falling;
 const sp=Object.keys(p.spacing.crc),rp=Object.keys(p.spacing.roi_crc);
 const spacing=p.content_rate_accepted?Number(sp[0]):'Unverified';
 const clocks=Object.keys(e.data.pclk_hz_observations).map(Number);
 sweep.getRange(`A${r}:L${r}`).values=[[e.tag,e.shutter_denominator,null,p.raster_starts_hz,spacing,null,p.reports,p.crc_changed_pairs,p.crc_repeated_pairs,sp.length===1?p.spacing.crc[sp[0]]:'Mixed',60,rp.length===1?Number(rp[0]):'Mixed']];
 formula(sweep,`C${r}`,`=1000/B${r}`);
 if(p.content_rate_accepted)formula(sweep,`F${r}`,`=D${r}/E${r}`);else cell(sweep,`F${r}`,'Unverified');
 sweep.getRange(`Q${r}:U${r}`).values=[[(Math.min(...clocks)+Math.max(...clocks))/2/1e6,e.data.phases.rising.reports,p.valid_reports,g.bad_xy?.max??'n.a.',g.c_sync_bad?.max??'n.a.']];
 link(sweep,`N${r}`,path.join(slowRoot,e.tag,'input/summary.json'),'ILA summary');
 link(sweep,`O${r}`,path.join(slowRoot,e.config.before_readback),'Verified before');
 link(sweep,`P${r}`,path.join(slowRoot,e.tag,'after_exposure.png'),'After OSD');
 link(sweep,`V${r}`,path.join(slowRoot,e.tag,'readback_review.json'),'Setting / evidence review');
 cell(summary,`A${q}`,`${e.tag.startsWith('return')?'Return ':''}1/${e.shutter_denominator} s`);
 for(const [dest,src] of [['B','C'],['C','D'],['D','F']])formula(summary,`${dest}${q}`,`='Exposure Sweep'!${src}${r}`);
});
sweep.tables.add('A210:V215',true,'DedicatedExposure60');
sweep.getRange('A211:V215').format.rowHeight=32;sweep.getRange('A211:A215').format.wrapText=true;
sweep.getRange('C211:D215').setNumberFormat('0.000');sweep.getRange('F211:F215').setNumberFormat('0.000');sweep.getRange('Q211:Q215').setNumberFormat('0.000');
sweep.getRange('R211:U215').format.horizontalAlignment='center';
summary.getRange('A107:D111').format.rowHeight=29;summary.getRange('B107:D111').setNumberFormat('0.000');
summary.getRange('D107:D111').format.font.bold=true;stripe(summary,107,111,'D');
const validTotal=slow.entries.reduce((n,e)=>n+e.data.phases.falling.valid_reports,0);
const reportTotal=slow.entries.reduce((n,e)=>n+e.data.phases.falling.reports,0);
const changedTotal=slow.entries.reduce((n,e)=>n+e.data.phases.falling.crc_changed_pairs,0);
const repeatedTotal=slow.entries.reduce((n,e)=>n+e.data.phases.falling.crc_repeated_pairs,0);
cell(summary,'A113',`${changedTotal} changed adjacent pairs; ${repeatedTotal} repeated pairs across the five captures. Both CRCs agree on one update per raster.`);
lines(summary,114,[
 `${validTotal}/${reportTotal} complete falling-edge reports pass geometry and sync checks. Full-frame and 96 × 96 region CRCs determine content cadence.`,
 'All settings retain about 60 raster frames/s. The content update column counts changes in the transmitted pixel payload.',
 'Each shutter setting was visibly read at 1080p/30 immediately before and after its 1080p/60 capture; no shutter writes occurred between.',
 'PCLK and complete 1920 × 1080 raster geometry verify the format transition. Direct OSD text at 1080p/60 was unavailable.',
 'Menu values were read at 1080p/30. Actual 60-mode integration, format-specific exposure handling and clamping remain unverified.',
 'Only consecutive captured rasters form comparisons. Eight blocks contain upload gaps; this is a short sampled test.',
 'The operational FPGA and camera 2 at 1080p/30, ExtTrig, 1/240 s, 0 dB were restored. Display: camera 3; menus closed.'
]);
cell(summary,'A121',`Rising-edge monitor: ${slow.entries.reduce((n,e)=>n+e.data.phases.rising.reports,0)} reports, ${slow.entries.reduce((n,e)=>n+e.data.phases.rising.valid_reports,0)} valid. These reports are excluded.`);
link(summary,'A122',path.join(slowRoot,'sweep_results.json'),'Slower-shutter evidence');
link(summary,'F122',path.join(slowRoot,'final_state.json'),'Latest restored state');
section(sweep,218,'Readback, integrity and interpretation','V');
lines(sweep,219,[
 'Falling-edge reports qualify these measurements. Rising-phase reports are excluded; invalid or missing rising reports do not establish camera FPS.',
 'Valid raster: 2,073,600 Y/C samples, 1080 active lines, 1125 EAVs, 2200 clocks/line and 2,475,000 clocks/raster, with zero Y-parity and C-sync errors.',
 'The before/after OSD pictures use the working 1080p/30 path. The camera is commanded to 1080p/60 for acquisition and returned to 1080p/30 for readback.',
 'Each condition reloads the exact same dedicated bitstream. No shutter command occurs between its before and after images; both pictures were visually checked.',
 'PCLK is the midpoint of observed counter values. Quantization is ±256 Hz relative to the uncalibrated 27 MHz reference.',
 'The trigger counter observes the generated 60-Hz signal inside the FPGA, not accepted electrical triggers at the camera connector.',
 'CRC changes establish received-payload cadence, not exposure count. Physical integration, format-specific shutter handling and clamping remain unverified.',
 'ILA upload gaps and partial reports are excluded from adjacent comparisons. Rate = raster rate / uniform inter-change spacing; both CRCs must agree.',
 'The 1/240 s return checks reversibility after the slower settings. Earlier 1080p/30 output sweeps remain separate above.',
 'Full row-by-row reports and capture metadata are retained beside each linked summary. The operational DDR/video design is not qualified for 1080p/60.'
]);
link(sweep,'A231',path.join(slowRoot,'sweep_results.json'),'Consolidated sweep evidence');
link(sweep,'F231',path.join(slowRoot,'final_state.json'),'Restored state');
link(sweep,'J231',path.join(slowRoot,'initial_trigger.png'),'Initial ExtTrig');
link(sweep,'N231',path.join(slowRoot,'final_trigger.png'),'Final ExtTrig');
// Supersede the 60-mode interpretation while preserving raw evidence/counts.
cell(summary,'A4','Correction: 60 fresh FPS is unverified. A 1/30 s preselection displays 1/60 s in 1080p60. Verification starts at row 125.');
cell(summary,'A80','Earlier dedicated RTL: 1080p60 with 1/240 s preselected in 30-mode');
cell(summary,'A66','Both captures use a 60 Hz trigger. The 1/240 s shutter was read in 30-mode; the active 60-mode value was not read.');
cell(ila,'A71','ExtTrig, AGC 0 dB, fixed 60 Hz trigger. 1/240 s was read in 30-mode. The active 60-mode shutter was not read.');
cell(ila,'D73','30-mode shutter\n(1/n s)');
cell(ila,'D101','30-mode setting\n(ms)');
cell(ila,'L105','Unverified');
cell(summary,'A90','The earlier 60-mode capture has 256 valid-geometry reports and 248 changed pairs. A later frozen-camera test invalidates its fresh-FPS interpretation.');
cell(summary,'A91','Measured PCLK is about 148.498 MHz and the raster rate is about 60/s. Fresh-image FPS is unverified. The rising monitor produced no complete reports.');
cell(summary,'A94','Geometry and internal timing do not prove active-pixel integrity. The original diagnostic later reports 60 changes/s on a frozen image.');
cell(summary,'A95','The 1/240 s value was read in 1080p30. Active 60-mode shutter and true fresh-image FPS were not established in that test.');
cell(ila,'A116','Correction, 8 October: original diagnostic fails the verified frozen-camera control at 1080p60. Fresh input FPS is unverified; see Report row 125.');
cell(ila,'A115','CRC novelty requires an independent stability control. The original 60-mode diagnostic fails Freeze; its fresh-image cadence is unverified.');
cell(summary,'A103','Earlier 1080p60 sweep: fresh-FPS conclusions withdrawn after Freeze control');
cell(summary,'A104','Shutters below are 1080p30 preselected values. They were not read in 60-mode. Raw counts remain archived.');
header(summary,'A106:D106',['30-mode preselection','30-mode value\n(ms)','Raster frames/s','Fresh input FPS']);
cell(sweep,'A208','Earlier 1080p60 sweep: 30-mode shutter preselection; fresh FPS unverified');
cell(sweep,'B210','30-mode shutter\n(1/n s)');cell(sweep,'C210','30-mode setting\n(ms)');cell(sweep,'F210','Fresh input FPS');
for(let r=211;r<=215;r++)cell(sweep,`F${r}`,'Unverified');
cell(summary,'A113',`${changedTotal} raw changed pairs and ${repeatedTotal} repeated pairs. These CRC counts do not establish fresh-image cadence after the failed Freeze control.`);
cell(summary,'A114',`${validTotal}/${reportTotal} complete reports pass geometry and sync checks. This alone does not establish integrity of every active pixel.`);
cell(summary,'A115','About 60 input rasters/s remains a timing measurement. The previously accepted fresh-image FPS values are now unverified.');
cell(summary,'A118','Direct 60-mode readback now shows 1/30 s preselection becomes 1/60 s. Physical integration time remains unmeasured.');
cell(sweep,'A225','Correction: CRC changes can persist with camera FREEZE ON. Earlier 60-mode fresh-FPS estimates are withdrawn, although raster timing remains valid.');
cell(sweep,'A219','Falling-edge reports pass geometry; they do not qualify pixel integrity or fresh FPS. Invalid or missing rising reports also do not establish camera FPS.');
hyperlinks.find(x=>x.sheet==='Report'&&x.cell==='F122').label='Earlier restored state';cell(summary,'F122','Earlier restored state');
// New verification is linked to the measured raw records and reviewed OSD.
section(summary,125,'Verification with direct 1080p60 OSD and frozen-camera controls','J');
lines(summary,126,verification.headline_lines);
header(summary,'A130:D130',['Verification condition','Raster frames/s','Full CRC changed / pairs','ROI CRC changed / pairs']);
const firstV=236,lastV=firstV+verification.entries.length-1;
const area=sweep.getRange(`A233:V${lastV+18}`);area.format.font={name:'Arial',size:10,color:ink};area.format.verticalAlignment='center';area.format.rowHeight=23;
section(sweep,233,'8 October verification: direct OSD and Freeze negative controls','V');
cell(sweep,'A234','All captures use a generated 60 Hz trigger. Falling-phase geometry is checked; Freeze is a required control for interpreting CRC novelty.');
header(sweep,'A235:L235',['Condition','Format\nrasters/s','OSD shutter','DNR','Freeze','FPGA build','Valid\nreports','Raster\nframes/s','Adjacent\npairs','Full CRC\nchanged','ROI CRC\nchanged','Fresh\ninput FPS']);
header(sweep,'M235:P235',['—','Raw summary','OSD evidence','Review / context']);
header(sweep,'Q235:R235',['Raw ROI cadence\n(changes/s)','Freeze control']);
sweep.getRange('A235:R235').format.rowHeight=58;
verification.entries.forEach((e,i)=>{
 const r=firstV+i,q=131+i;
 sweep.getRange(`A${r}:L${r}`).values=[[e.label,e.format_hz,e.shutter_osd,e.dnr,e.freeze,e.build_label,e.valid_reports,e.raster_hz,e.pairs,e.full_changed,e.roi_changed,e.fresh_input_fps??(e.freeze==='ON'?'Control':'Unverified')]];
 link(sweep,`N${r}`,path.join(verifyRoot,e.tag,'summary.json'),'ILA summary');
 link(sweep,`O${r}`,path.join(verifyRoot,e.osd_evidence),'OSD readback');
 link(sweep,`P${r}`,path.join(verifyRoot,'verification_results.json'),'Verdict');
 if(e.roi_spacing_rasters)formula(sweep,`Q${r}`,`=H${r}/${e.roi_spacing_rasters}`);else cell(sweep,`Q${r}`,e.roi_changed===0?'Constant':'Mixed');
 cell(sweep,`R${r}`,e.freeze_control_pass===null?'n.a.':e.freeze_control_pass?'Pass':'Fail');
 cell(summary,`A${q}`,e.label);formula(summary,`B${q}`,`='Exposure Sweep'!H${r}`);
 formula(summary,`C${q}`,`='Exposure Sweep'!J${r}&" / "&'Exposure Sweep'!I${r}`);
 formula(summary,`D${q}`,`='Exposure Sweep'!K${r}&" / "&'Exposure Sweep'!I${r}`);
});
sweep.tables.add(`A235:R${lastV}`,true,'FreezeVerification');
sweep.getRange(`A236:F${lastV}`).format.wrapText=true;sweep.getRange(`A236:P${lastV}`).format.rowHeight=36;
sweep.getRange(`H236:H${lastV}`).setNumberFormat('0.000');sweep.getRange(`L236:L${lastV}`).setNumberFormat('0.000');
sweep.getRange(`Q236:Q${lastV}`).setNumberFormat('0.000');
summary.getRange(`A131:A${130+verification.entries.length}`).format.wrapText=true;
summary.getRange(`A131:D${130+verification.entries.length}`).format.rowHeight=36;
summary.getRange(`B131:B${130+verification.entries.length}`).setNumberFormat('0.000');
summary.getRange(`C131:D${130+verification.entries.length}`).format.horizontalAlignment='center';
stripe(summary,131,130+verification.entries.length,'D');
const notesRow=133+verification.entries.length;
lines(summary,notesRow,verification.verdict_lines);
lines(sweep,lastV+3,verification.method_lines);
link(summary,`A${notesRow+verification.verdict_lines.length+1}`,path.join(verifyRoot,'verification_results.json'),'Verification evidence');
link(summary,`F${notesRow+verification.verdict_lines.length+1}`,path.join(verifyRoot,'final_state.json'),'Latest restored state');
link(sweep,`A${lastV+15}`,verification.manual_path,'Supplied manufacturer manual');
link(sweep,`F${lastV+15}`,path.join(root,'builds/eo60_snapshot_20261008_r1/manifest.json'),'Snapshot build / timing');
link(sweep,`K${lastV+15}`,path.join(verifyRoot,'test_protocol.json'),'Test protocol');
section(summary,163,'Direct camera OSD evidence captured through the ILA','J');
cell(summary,'A164','1080p30: 1/30 s before switching format');cell(summary,'F164','1080p60: 1/60 s after switching format');
for(const [key,row,col] of [['exposure30',165,0],['exposure60',165,5],['freeze60',184,0]]){
 const bytes=await fs.readFile(path.join(verifyRoot,verification.key_images[key]));
 summary.images.add({dataUrl:`data:image/png;base64,${bytes.toString('base64')}`,anchor:{from:{row,col},extent:{widthPx:600,heightPx:337.5}}});
}
cell(summary,'A180','No shutter command occurred between these two readbacks. Menu text is not a physical integration-time measurement.');
link(summary,'A181',path.join(verifyRoot,verification.key_images.exposure30),'Original 30-mode OSD image');
link(summary,'F181',path.join(verifyRoot,verification.key_images.exposure60),'Original 60-mode OSD image');
section(summary,183,'Negative control: camera Freeze ON at 1080p60','J');
cell(summary,'F186','Original r2: 248 / 248 full CRC pairs changed.');
cell(summary,'F188','Original r2: 248 / 248 ROI CRC pairs changed.');
cell(summary,'F190','The sampled frozen image stayed byte-identical');
cell(summary,'F191','before and after the original-r2 test.');
cell(summary,'F193','The 30-mode frozen control passes.');
cell(summary,'F195','These controls invalidate the old fresh-FPS claim.');
link(summary,'A199',path.join(verifyRoot,verification.key_images.freeze60),'Original Freeze OSD image');
// Recalculate once after all authored content, then verify consequential results.
// Check dependency propagation with a temporary edit, then restore the observation.
const originalSpacing=sweep.getRange('E7').values[0][0];
cell(sweep,'E7',originalSpacing*2);
assert.ok(Math.abs(summary.getRange('B7').values[0][0]-sweepData[0].data.cameras['2'].raster_hz/originalSpacing/2)<0.00001);
cell(sweep,'E7',originalSpacing);
const originalSpacing30=sweep.getRange('E101').values[0][0];
cell(sweep,'E101',originalSpacing30*2);
assert.ok(Math.abs(summary.getRange('C7').values[0][0]-sweep30Data[0].data.cameras['2'].raster_hz/originalSpacing30/2)<0.00001);
cell(sweep,'E101',originalSpacing30);
wb.recalculate();
assert.equal(summary.getRange('D63').values[0][0],'Unverified');
assert.equal(summary.getRange('C63').values[0][0],'0 / 179');
assert.ok(Math.abs(summary.getRange('D64').values[0][0]-29.999610627643293)<0.00001);
assert.equal(summary.getRange('D85').values[0][0],'Unverified');
assert.equal(summary.getRange('C86').values[0][0],'256 / 256');
assert.equal(summary.getRange('D86').values[0][0],'Unverified');
for(let i=0;i<sweepData.length;i++){
 const r=7+i,c=sweepData[i].data.cameras['2'],expected=c.raster_hz/Number(Object.keys(c.content.crc.change_spacing_rasters)[0]);
 const actual=summary.getRange(`B${r}`).values[0][0];assert.ok(Math.abs(actual-expected)<0.0001,`Summary B${r}: ${actual}`);
 const c30=sweep30Data[i].data.cameras['2'],expected30=c30.raster_hz/Number(Object.keys(c30.content.crc.change_spacing_rasters)[0]);
 assert.ok(Math.abs(summary.getRange(`C${r}`).values[0][0]-expected30)<0.0001);
}
assert.equal(ila.getRange('F14').values[0][0],85);assert.equal(ila.getRange('G14').values[0][0],0);
assert.equal(usbRows.final_cam2,26);assert.equal(usbRows.final_cam1,27);
const inspection=await wb.inspect({kind:'table',range:`Report!A6:D${lastSweep}`,include:'values,formulas',tableMaxRows:12,tableMaxCols:4,maxChars:5000});
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Formula errors',maxChars:3000});
console.log(inspection.ndjson);console.log(errors.ndjson);
await fs.mkdir(outputDir,{recursive:true});
await fs.writeFile(path.join(work,'verification_consolidated.json'),JSON.stringify({summary:summary.getRange(`A6:D${lastSweep}`).values,formulas:summary.getRange(`A6:D${lastSweep}`).formulas,errors:errors.ndjson,usbRows,chartSeries:chart.series.items.map(s=>({values:s.formula,categories:s.categoryFormula}))},null,2));
for(const [sheetName,range,file] of [
 ['Report',`A125:J${notesRow+verification.verdict_lines.length+1}`,'verification_report.png'],
 ['Report','A163:J181','verification_osd.png'],['Report','A183:J199','verification_freeze.png'],
 ['Exposure Sweep',`A233:L${lastV}`,'verification_measurements.png'],
 ['Exposure Sweep',`N235:R${lastV}`,'verification_sources.png'],
 ['Exposure Sweep',`A${lastV+3}:V${lastV+15}`,'verification_notes.png'],
 ['Report','A2:J27','consolidated_report_top.png'],['Report','A29:J58','consolidated_report_bottom.png'],
 ['Report','A60:J76','format60_report.png'],['ILA Results','A70:P89','format60_ila.png'],['ILA Results','Q73:U75','format60_sources.png'],
 ['Report','A80:J99','dedicated60_report.png'],['ILA Results','A99:P107','dedicated60_ila.png'],['ILA Results','A110:U118','dedicated60_notes.png'],
 ['Report','A103:J122','slow60_report.png'],['Exposure Sweep','A208:L215','slow60_measurements.png'],['Exposure Sweep','N210:V215','slow60_sources.png'],['Exposure Sweep','A218:V231','slow60_notes.png'],
 ['Exposure Sweep',`A2:L${lastSweep}`,'sweep_summary.png'],['Exposure Sweep','A18:O30','sweep_protocol.png'],
 ['Exposure Sweep','A31:L51','sweep_controls.png'],['Exposure Sweep','N33:U51','sweep_geometry.png'],
 ['Exposure Sweep',`N6:V${lastSweep}`,'sweep_sources.png'],
 ['ILA Results','R6:U30','consolidated_ila_sources.png'],
 ['ILA Results','A55:P66','consolidated_ila_notes.png'],
 ['Exposure Sweep','A98:L110','sweep30_summary.png'],['Exposure Sweep','A113:O125','sweep30_protocol.png'],
 ['Exposure Sweep','A128:L148','sweep30_controls.png'],['Exposure Sweep','N100:V110','sweep30_sources.png'],
 ['Exposure Sweep','A194:L202','current_reference60.png'],
 ['USB Results','A34:K39','fresh_usb.png'],['USB Results','M34:O39','fresh_usb_sources.png'],['USB Results','A42:K51','consolidated_usb_notes.png']
]){
 if(process.argv.includes('--skip-previews'))continue;
 if(process.argv.includes('--verification-only-previews')&&!['consolidated_report_top.png','dedicated60_report.png','slow60_report.png','slow60_measurements.png','verification_report.png','verification_measurements.png','verification_sources.png','verification_notes.png','verification_osd.png','verification_freeze.png'].includes(file))continue;
 if(process.argv.includes('--slow-only-previews')&&!['consolidated_report_top.png','dedicated60_report.png','slow60_report.png','slow60_measurements.png','slow60_sources.png','slow60_notes.png'].includes(file))continue;
 if(process.argv.includes('--diagnostic-only-previews')&&!['consolidated_report_top.png','format60_report.png','dedicated60_report.png','dedicated60_ila.png','dedicated60_notes.png'].includes(file))continue;
 if(process.argv.includes('--format-only-previews')&&!['consolidated_report_top.png','consolidated_report_bottom.png','format60_report.png','format60_ila.png','format60_sources.png'].includes(file))continue;
 const preview=await wb.render({sheetName,range,scale:1.4,format:'png'});
 await fs.writeFile(path.join(work,file),new Uint8Array(await preview.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);
const outputPath=path.join(outputDir,'EO_Camera_FPS_Consolidated_Report_20261007.xlsx');
await xlsx.save(outputPath);
for(const l of hyperlinks)await fs.access(l.target);
await fs.writeFile(path.join(work,'hyperlinks.json'),JSON.stringify(hyperlinks,null,2));
// The authoring engine does not implement HYPERLINK or a native hyperlink API.
// Add only native OpenXML hyperlink relationships after the supported export.
console.log(execFileSync('C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',[path.join(work,'add_native_links.py'),outputPath,path.join(work,'hyperlinks.json')],{encoding:'utf8'}));
console.log('SAVED',outputPath);
