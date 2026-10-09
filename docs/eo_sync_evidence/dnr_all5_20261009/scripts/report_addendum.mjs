import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.cwd(),scratch=path.join(root,'.tmpCRC/eo_dnr_all5_20261009');
const input=path.join(root,'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(process.argv.includes('--preview')?input:path.join(scratch,'report_before.xlsx')));
console.log('Pre-edit workbook imported');
const summary=wb.worksheets.getItem('Comparison');
const fileHash=async p=>createHash('sha256').update(await fs.readFile(p)).digest('hex');
async function render(range,name){const blob=await wb.render({sheetName:'Comparison',range,scale:1.3});await fs.writeFile(path.join(scratch,name+'.png'),new Uint8Array(await blob.arrayBuffer()));}
if(process.argv.includes('--preview')){
  await render('A129:J148','baseline');
  console.log((await wb.inspect({kind:'workbook,sheet,table',maxChars:3500,tableMaxRows:2,tableMaxCols:3})).ndjson);
  console.log((await wb.inspect({kind:'table',range:'Comparison!A143:J148',include:'values,formulas',tableMaxRows:6,tableMaxCols:10,maxChars:3500})).ndjson);
  process.exit(0);
}
const beforeHash=await fileHash(path.join(scratch,'report_before.xlsx'));
if(await fileHash(input)!==beforeHash)throw Error('The report changed after the baseline copy; review before updating.');
const source='captures/eo_dnr_all5_20261009';
const study=JSON.parse(await fs.readFile(path.join(root,source,'study.json'),'utf8'));
const pair=JSON.parse(await fs.readFile(path.join(root,'docs/eo_sync_evidence/dnr_cam2_20261009/cam2_cam3_spread.json'),'utf8'));
const oldComparison=JSON.parse(await fs.readFile(path.join(root,'docs/eo_sync_evidence/dnr_cam2_20261009/comparison.json'),'utf8'));
const restoration=JSON.parse(await fs.readFile(path.join(root,source,'restored_state_verified.json'),'utf8'));
if(!restoration.all_camera_readbacks_verified||!restoration.display_matches_initial||!restoration.pose_matches_initial||!restoration.usb_scene_verified)throw Error('Restoration not verified');
for(const stage of ['on_frozen','on_live','off_live','return_live','off_repeat_live','off_frozen']){
  const state=JSON.parse(await fs.readFile(path.join(root,source,stage+'_state_verified.json'),'utf8'));
  if(!state.all_camera_readbacks_verified||state.format!=='1080p60'||state.shutter!=='1/60 s')throw Error('Test settings not verified: '+stage);
}
const cameras=wb.worksheets.getItem('Camera results'),matched=wb.worksheets.getItem('Matched rasters');
const cameraStart=219,cameraEnd=cameraStart+study.camera_rows.length-1,matchedStart=24644,matchedEnd=matchedStart+study.raster_cohorts.length-1;
const style=(sheet,range)=>{const r=sheet.getRange(range);r.format.font={name:'Arial',size:10,color:'#243244'};r.format.rowHeight=21;r.format.verticalAlignment='center';};
const header=range=>{const r=summary.getRange(range);r.format.fill='#253B56';r.format.font.color='#FFFFFF';r.format.font.bold=true;r.format.wrapText=true;r.format.horizontalAlignment='center';r.format.rowHeight=34;};
cameras.tables.items.find(t=>t.name==='CameraObservations').rows.add(null,study.camera_rows.map(r=>[r.condition,r.mode,r.control,r.selected,r.camera,r.phase,r.block,r.build,r.records,r.timing_valid,r.valid,null,r.sequence_gaps,r.duration_s,r.raster_hz,r.full_changes,r.full_change_hz,r.roi_changes,r.roi_change_hz,r.offset_median_us,r.drift_us_per_second,r.since_trigger_fall_us.median,r.since_trigger_fall_us.min,r.since_trigger_fall_us.max,source+'/'+r.source_file,r.source_sha256,r.format_fps,r.phase_tap,r.control_id]));
console.log('Appended 50 camera observations');
style(cameras,`A${cameraStart}:AC${cameraEnd}`);
cameras.getRange(`L${cameraStart}`).formulas=[[`=K${cameraStart}/I${cameraStart}`]];cameras.getRange(`L${cameraStart}:L${cameraEnd}`).fillDown();
cameras.getRange(`L${cameraStart}:L${cameraEnd}`).setNumberFormat('0.0%');
cameras.getRange(`N${cameraStart}:O${cameraEnd}`).setNumberFormat('0.00000');cameras.getRange(`Q${cameraStart}:Q${cameraEnd}`).setNumberFormat('0.000');cameras.getRange(`S${cameraStart}:X${cameraEnd}`).setNumberFormat('0.000');
for(const col of ['I','J','K','M','P','R'])cameras.getRange(`${col}${cameraStart}:${col}${cameraEnd}`).setNumberFormat('#,##0');
matched.tables.items.find(t=>t.name==='MatchedRasters').rows.add(null,study.raster_cohorts.map(r=>[r.condition,r.format_fps,r.mode,r.block,...[2,3,4,5,6].map(c=>r[`cam${c}_tick`]),r.period_ticks,r.span_us,null,...[3,4,5,6].map(c=>r[`cam${c}_offset_us`])]));
style(matched,`A${matchedStart}:P${matchedEnd}`);
matched.getRange(`L${matchedStart}`).formulas=[[`=K${matchedStart}/1000`]];matched.getRange(`L${matchedStart}:L${matchedEnd}`).fillDown();
matched.getRange(`E${matchedStart}:J${matchedEnd}`).setNumberFormat('0');matched.getRange(`K${matchedStart}:P${matchedEnd}`).setNumberFormat('0.000');
console.log('Appended 14,051 matched raster sets');
style(summary,'A152:J251');
const labels={on_a:'ON (initial)',off_b:'OFF',on_return:'ON (restored)',off_repeat:'OFF (repeat)'};
const liveConditions=['on_a','off_b','on_return','off_repeat'];
const expected=[];const inputRows=[];
function note(row,text){summary.getRange(`A${row}`).values=[[text]];}
function section(row,text){note(row,text);summary.getRange(`A${row}`).format.font={name:'Arial',size:14,bold:true,color:'#243244'};}
function inputStats(condition,measurement,cameraGroup,s,scope){const row=220+inputRows.length;inputRows.push([condition,measurement,cameraGroup,s.n,s.min,s.median,s.p95,s.max,scope]);return row;}
function spreadRow(row,label,seconds,s,inputRow,scope){
 summary.getRange(`A${row}:I${row}`).values=[[label,30,seconds,null,null,null,null,null,scope]];
 summary.getRange(`D${row}:H${row}`).formulas=[[`=D${inputRow}`,...['E','F','G','H'].map(c=>`=IF(D${inputRow}=0,"n.a.",${c}${inputRow}/1000)`)]];
 expected.push({row,expected:[s.n,...['min','median','p95','max'].map(k=>s[k]==null?'n.a.':s[k]/1000)]});
}
const h=['DNR state','Trigger Hz','Observed s','Matched sets','Min spread ms','Median ms','P95 ms','Max ms','Scope'];
section(152,'Camera 2 DNR OFF: actual camera-2/camera-3 spread');
note(153,'9 October 2026. Earlier test: only camera 2 DNR changed; camera 3 remained the timing reference.');
note(154,'1080p60 / 30 Hz trigger / camera 2 shutter 1/60 s. Camera 3 shutter was not freshly reread.');
summary.getRange('A156:I156').values=[h];header('A156:I156');
const oldSeconds=Object.fromEntries(['on_a','off_b','on_return'].map(k=>[k,oldComparison.conditions[k].camera2.duration_s]));
for(const [i,k] of ['on_a','off_b','on_return'].entries()){
 const s=pair.conditions[k].raster.absolute_spread_us;spreadRow(157+i,labels[k],oldSeconds[k],s,inputStats('Cam2 '+labels[k],'Raster pair','2–3',s,'Timing'),'Cam2–cam3 raster');
}
note(161,'Camera 2 arrived later than camera 3. The gap continued to decrease after DNR was restored.');
note(162,'Previously quoted 3–4 microseconds was a clock-drift residual; the actual spread above is milliseconds.');
summary.getRange('A164:I164').values=[h];header('A164:I164');
for(const [i,k] of ['on_a','off_b','on_return'].entries()){
 const s=pair.conditions[k].full_crc.absolute_spread_us;spreadRow(165+i,labels[k],oldSeconds[k],s,inputStats('Cam2 '+labels[k],'CRC-change pair','2–3',s,'Descriptive'),'Full + ROI CRC');
}
note(169,'Camera 3 changed update parity during the initial ON capture, before OFF; it lacked a fresh frozen control.');
note(170,'These image-update gaps cannot be attributed to DNR or treated as same-exposure image synchronization.');
section(173,'All five cameras: DNR OFF synchronization comparison');
note(174,'Cameras 2–6: 1080p60 / 1/60 s / 0 dB / ExtTrig / 0.0 ms trigger delay; same build and sampling phases.');
note(175,'ILA verified 30 Hz trigger with 2 ms high time. All five DNR settings were read directly from their OSDs.');
note(176,'Raster spread: shortest circular arc containing five nearest input phases on the common 27 MHz clock.');
note(177,'DNR OFF did not align the five input raster starts; both OFF captures retain about 10 ms of spread.');
summary.getRange('A178:I178').values=[h];header('A178:I178');
let cursor=matchedStart;
for(const [i,k] of liveConditions.entries()){
 const row=179+i,c=study.conditions[k],s=c.spreads_us.raster;const end=cursor+s.n-1,ref=`'Matched rasters'!L${cursor}:L${end}`;
 const cohortSlice=study.raster_cohorts.slice(cursor-matchedStart,end-matchedStart+1);
 if(cohortSlice.some(r=>r.condition!=='all5_dnr_'+k))throw Error('Raster cohort bounds');
 summary.getRange(`A${row}:I${row}`).values=[[labels[k],30,c.observed_s,null,null,null,null,null,'Five-camera raster']];
 summary.getRange(`D${row}:H${row}`).formulas=[[`=COUNT(${ref})`,`=MIN(${ref})`,`=MEDIAN(${ref})`,`=PERCENTILE(${ref},0.95)`,`=MAX(${ref})`]];
 expected.push({row,expected:[s.n,...['min','median','p95','max'].map(x=>s[x]/1000)]});cursor=end+1;
}
if(cursor!==matchedEnd+1)throw Error('Unused raster cohorts');
note(183,'Sequential median differences include clock drift; the returning ON capture is retained for comparison.');
const roiQualified=Object.values(study.crc_freeze_qualification).every(q=>q.roi_crc.all_five_pass);
note(184,roiQualified?'ROI CRC passed both frozen controls on all five cameras. Full-frame CRC is unreliable on cameras 5 and 6.':'ROI CRC failed one or more frozen controls; the following CRC spread is descriptive only.');
summary.getRange('A186:I186').values=[h];header('A186:I186');
for(const [i,k] of liveConditions.entries()){
 const c=study.conditions[k],s=c.spreads_us.roi_crc;spreadRow(187+i,labels[k],c.observed_s,s,inputStats('All5 '+labels[k],'Five-camera ROI','2–6',s,roiQualified?'Frozen controls pass':'Unqualified'),'Five-camera ROI CRC');
}
note(191,'Cam2–cam3 raster separation within the new all-five DNR test; both shutters set to 1/60 s:');
summary.getRange('A192:I192').values=[h];header('A192:I192');
for(const [i,k] of liveConditions.entries()){
 const c=study.conditions[k],s=c.cam2_cam3.raster.absolute_spread_us;spreadRow(193+i,labels[k],c.observed_s,s,inputStats('All5 '+labels[k],'Raster pair','2–3',s,'Timing'),'Cam2–cam3 raster');
}
section(239,'Cam2–cam3 image-update spread with all five DNR settings changed');
summary.getRange('A240:I240').values=[h];header('A240:I240');
const pairRoiQualified=Object.values(study.crc_freeze_qualification).every(q=>q.roi_crc.cameras['2']&&q.roi_crc.cameras['3']);
for(const [i,k] of liveConditions.entries()){
 const c=study.conditions[k],s=c.cam2_cam3.roi_crc.absolute_spread_us;
 spreadRow(241+i,labels[k],c.observed_s,s,inputStats('All5 '+labels[k],'ROI-change pair','2–3',s,pairRoiQualified?'Frozen controls pass':'Unqualified'),'Cam2–cam3 ROI CRC');
}
note(245,'Nearest ROI-change events; both shutters are verified at 1/60 s. This does not identify shared exposures.');
note(246,pairRoiQualified?'Both cameras passed ROI Freeze controls in ON and OFF states; all live change intervals were two rasters.':'One or both cameras failed an ROI Freeze control; image-change spread is descriptive.');
note(247,'Cam3 update parity shifted between initial ON and OFF, then persisted in ON return and OFF repeat.');
note(248,'The shift occurred in an uncaptured interval; its cause cannot be separated from setting changes and clock phase.');
note(197,'The first OFF ROI gap did not reproduce in OFF repeat. Raster/CRC alignment does not identify shared exposures.');
const maxResidual=Math.max(...Object.values(study.bracketed_on_raster_drift).map(d=>Math.abs(d.residual_us.off_b.median)));
note(198,`Largest median first-OFF raster residual against the ON drift model: ${maxResidual.toFixed(3)} microseconds.`);
note(199,'This drift-model residual is separate from the actual millisecond spread. Whole-frame latency is not measured.');
summary.getRange('A201:F201').values=[['DNR control','Camera','Valid rasters','Observed s','Full CRC changes','ROI CRC changes']];header('A201:F201');
const freezeRows=[];
for(const k of ['control_on','control_off'])for(const c of study.conditions[k].cameras)freezeRows.push([k==='control_on'?'ON frozen':'OFF frozen',c.camera,c.valid,c.duration_s,c.full_changes,c.roi_changes]);
summary.getRange('A202:F211').values=freezeRows;summary.getRange('C202:C211').setNumberFormat('#,##0');summary.getRange('D202:D211').setNumberFormat('0.00');
note(213,'Restored cameras 2–6 to 1080p30 / 1/240 s / DNR 2D+3D / Freeze OFF and the operational FPGA image.');
note(214,'Fresh OSD readbacks and USB view verified restoration; display selection and pose match the starting state.');
const anomalies=study.crc_cadence.filter(c=>liveConditions.includes(c.condition)&&c.series==='roi_crc'&&Object.keys(c.interval_rasters).some(k=>k!=='2'));
note(215,anomalies.length?'Extra ROI transitions are retained. They do not establish additional sensor exposures; see per-camera observations.':'All observed adjacent ROI-change intervals were two rasters in the four live conditions.');
section(218,'Measured spread statistics used above');
summary.getRange('A219:I219').values=[['Condition','Measurement','Cameras','Pairs','Min us','Median us','P95 us','Max us','Qualification']];header('A219:I219');
summary.getRange(`A220:I${219+inputRows.length}`).values=inputRows;
summary.getRange(`D220:D${219+inputRows.length}`).setNumberFormat('#,##0');summary.getRange(`E220:H${219+inputRows.length}`).setNumberFormat('0.000');
note(250,'Source: cam2_cam3_spread.json, simultaneous single-camera DNR test; raw pairs reproduced and checked.');
note(251,'Source: all-five DNR study.json; camera-source CSV filenames and SHA256 are retained in Camera results.');
for(const range of ['C157:C159','C165:C167','C179:C182','C187:C190','C193:C196','C241:C244'])summary.getRange(range).setNumberFormat('0.00');
for(const range of ['D157:D159','D165:D167','D179:D182','D187:D190','D193:D196','D241:D244'])summary.getRange(range).setNumberFormat('#,##0');
for(const range of ['E157:H159','E165:H167','E179:H182','E187:H190','E193:H196','E241:H244'])summary.getRange(range).setNumberFormat('0.000');
wb.recalculate();
console.log('Recalculated workbook');
for(const e of expected){const got=summary.getRange(`D${e.row}:H${e.row}`).values[0];e.expected.forEach((x,i)=>{if(typeof x==='number'?typeof got[i]!=='number'||Math.abs(got[i]-x)>1e-8:got[i]!==x)throw Error('Spread formula mismatch row '+e.row);});}
const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'DNR report formula error scan'});
await fs.writeFile(path.join(scratch,'report_error_scan.ndjson'),scan.ndjson);if(scan.ndjson.split('\n').filter(Boolean).some(l=>JSON.parse(l).kind==='match'))throw Error('Formula errors');
await render('A152:J170','cam2_spread');await render('A173:J199','all5_spread');await render('A201:J237','controls_inputs');await render('A239:J251','all5_pair_roi');
console.log('Rendered all four comparison previews; spread formulas agree with raw analysis');
if(await fileHash(input)!==beforeHash)throw Error('The report changed during authoring; preserve user edits.');
console.log('Exporting workbook');
await (await SpreadsheetFile.exportXlsx(wb)).save(input);
await fs.writeFile(path.join(scratch,'report_validation.json'),JSON.stringify({output:input,cameraStart,cameraEnd,matchedStart,matchedEnd,expected,roiQualified,anomalies,maxResidual},null,2));
console.log(input);
