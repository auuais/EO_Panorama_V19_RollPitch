import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.cwd(), scratch=path.join(root,'.tmpCRC/eo_sync_trig30_exp60_20261009');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(scratch,'report_before.xlsx')));
const summary=wb.worksheets.getItem('Comparison'), cameras=wb.worksheets.getItem('Camera results'), matched=wb.worksheets.getItem('Matched rasters');
async function render(sheetName,range,name){const blob=await wb.render({sheetName,range,scale:1.3});await fs.writeFile(path.join(scratch,name+'.png'),new Uint8Array(await blob.arrayBuffer()));}
if(process.argv.includes('--preview')){
  await render('Comparison','A55:J81','baseline');
  console.log((await wb.inspect({kind:'table',range:'Comparison!A62:J67',include:'values,formulas',tableMaxRows:6,tableMaxCols:10,maxChars:3000})).ndjson);
  process.exit(0);
}
const source='captures/eo_sync_trig30_exp60_20261009';
const study=JSON.parse(await fs.readFile(path.join(root,source,'study.json'),'utf8'));
const metrics=JSON.parse(await fs.readFile(path.join(root,source,'live_metrics.json'),'utf8'));
const repeatMetrics=JSON.parse(await fs.readFile(path.join(root,source,'repeat_metrics.json'),'utf8'));
const c=study.conditions.find(x=>!x.control),control=study.conditions.find(x=>x.id===c.control_id);
const repeat=study.conditions.find(x=>x.id==='60_trig30_exp60_repeat');
if(!c.trigger_verified||!c.content_complete||!c.timing_complete||!c.qualified_image_series)throw Error('Unqualified live capture');
if(!repeat?.trigger_verified||!repeat.content_complete||!repeat.timing_complete||!repeat.qualified_image_series)throw Error('Unqualified repeat');
const cr=study.camera_rows,cohorts=study.raster_cohorts;
const cameraStart=179,cameraEnd=cameraStart+cr.length-1,matchedStart=19497,matchedEnd=matchedStart+cohorts.length-1;
const style=(sheet,range)=>{const r=sheet.getRange(range);r.format.font={name:'Arial',size:10,color:'#243244'};r.format.rowHeight=21;r.format.verticalAlignment='center';};
const header=range=>{const r=summary.getRange(range);r.format.fill='#253B56';r.format.font.color='#FFFFFF';r.format.font.bold=true;r.format.wrapText=true;r.format.horizontalAlignment='center';r.format.rowHeight=34;};
cameras.tables.items.find(t=>t.name==='CameraObservations').rows.add(null,cr.map(r=>[r.condition,r.mode,r.control,r.selected,r.camera,r.phase,r.block,r.build,r.records,r.timing_valid,r.valid,null,r.sequence_gaps,r.duration_s,r.raster_hz,r.full_changes,r.full_change_hz,r.roi_changes,r.roi_change_hz,r.offset_median_us,r.drift_us_per_second,r.since_trigger_fall_us?.median??null,r.since_trigger_fall_us?.min??null,r.since_trigger_fall_us?.max??null,source+'/'+r.source_file,r.source_sha256,r.format_fps,r.phase_tap??null,r.control_id??null]));
style(cameras,`A${cameraStart}:AC${cameraEnd}`);
cameras.getRange(`L${cameraStart}`).formulas=[[`=IF(I${cameraStart}=0,"",K${cameraStart}/I${cameraStart})`]];cameras.getRange(`L${cameraStart}:L${cameraEnd}`).fillDown();
cameras.getRange(`L${cameraStart}:L${cameraEnd}`).setNumberFormat('0.0%');
for(const range of [`N${cameraStart}:O${cameraEnd}`,`Q${cameraStart}:Q${cameraEnd}`])cameras.getRange(range).setNumberFormat('0.00000');
cameras.getRange(`S${cameraStart}:X${cameraEnd}`).setNumberFormat('0.000');
matched.tables.items.find(t=>t.name==='MatchedRasters').rows.add(null,cohorts.map(r=>[r.condition,r.format_fps,r.mode,r.block,...[2,3,4,5,6].map(cam=>r[`cam${cam}_tick`]),r.period_ticks,r.span_us,null,...[3,4,5,6].map(cam=>r[`cam${cam}_offset_us`])]));
style(matched,`A${matchedStart}:P${matchedEnd}`);
matched.getRange(`L${matchedStart}`).formulas=[[`=K${matchedStart}/1000`]];matched.getRange(`L${matchedStart}:L${matchedEnd}`).fillDown();
matched.getRange(`E${matchedStart}:J${matchedEnd}`).setNumberFormat('0');matched.getRange(`K${matchedStart}:P${matchedEnd}`).setNumberFormat('0.000');
style(summary,'A99:J125');
summary.getRange('A99').values=[['1/60 s exposure setting: 1080p60 with 30 Hz trigger']];summary.getRange('A99').format.font={name:'Arial',size:15,bold:true,color:'#243244'};
const notes={
100:'9 October 2026 KST. Cameras 2–6: ExtTrig / 1080p60 / shutter 1/60 s / 0 dB / DNR 2D+3D / ExtTrig Delay 0.0 ms.',
101:'ILA verified trigger: 33,333.333 µs period, 2,000 µs high. Shutter and format read directly from each 1080p60 OSD.',
102:'Result: about 60 rasters/s and a dominant 30 ROI updates/s cadence. Camera 5 has persistent extra CRC transitions.',
103:'Cameras 2–4: clean two-raster change spacing. Camera 6 is clean on repeat. Camera 5 cannot be certified as a clean 30 FPS stream.',
104:'Rates = counted changes / observed frame-span; two live blocks exclude upload gaps. Small endpoint offsets are expected.',
113:`Fresh Freeze control: ${control.observed_s.toFixed(2)} s. Full-raster stable: ${control.qualifies_full?'YES':'NO'}; central 96x96 ROI stable: ${control.qualifies_roi?'YES':'NO'}.`,
114:'Primary capture: camera 5 has 12 one-raster intervals; camera 6 has two. All other inter-change intervals are two rasters.',
115:'Same r4 bitstream; rising-edge phase taps for cameras 2–6: 336, 280, 308, 280, 322. Fresh control uses identical taps.',
116:'Strict geometry 100%; no selected-path sequence gaps or telemetry overruns. Full-frame CRC is not used for image cadence.',
121:'Raster spread is the shortest circular arc of five nearest raster phases. It does not identify simultaneous exposures.',
122:'The 1/60 s value is a verified camera setting; actual sensor integration time and trigger acceptance were not measured.',
123:'CRC changes describe central image-data updates. They do not independently prove distinct sensor exposures.',
125:'Restored operational FPGA; cameras 2–6: 1080p30 / ExtTrig / 1/240 s / Freeze OFF / ExtTrig Delay 0.0 ms.'
};
for(const [row,text] of Object.entries(notes))summary.getRange(`A${row}`).values=[[text]];
summary.getRange('A102').format.font.bold=true;
summary.getRange('A106:J106').values=[['Camera','Trigger Hz','Observed s','Raster count','Rasters/s','ROI changes','Changes/s','CRC scope','Strict valid %','Sequence gaps']];header('A106:J106');
const col=s=>`'Camera results'!$${s}$${cameraStart}:$${s}$${cameraEnd}`,expected=[];
for(let cam=2;cam<=6;cam++){
  const row=cam+105,criteria=`${col('A')},"${c.id}",${col('F')},"${c.phases[cam-2]}",${col('E')},A${row}`,sum=s=>`SUMIFS(${col(s)},${criteria})`;
  summary.getRange(`A${row}:J${row}`).values=[[cam,c.trigger_hz,null,null,null,null,null,'96x96 ROI',null,null]];
  summary.getRange(`C${row}:G${row}`).formulas=[[`=${sum('N')}`,`=${sum('I')}`,`=(D${row}-COUNTIFS(${criteria}))/C${row}`,`=${sum('R')}`,`=F${row}/C${row}`]];
  summary.getRange(`I${row}:J${row}`).formulas=[[`=${sum('K')}/D${row}`,`=${sum('M')}`]];
  const m=metrics.cameras.find(x=>x.camera===cam);expected.push({row,camera:cam,seconds:m.seconds,records:m.rasters,raster_hz:m.raster_hz,changes:m.roi_changes,change_hz:m.roi_changes_hz});
}
for(const range of ['C107:C111'])summary.getRange(range).setNumberFormat('0.00');
for(const range of ['D107:D111','F107:F111'])summary.getRange(range).setNumberFormat('#,##0');
for(const range of ['E107:E111','G107:G111'])summary.getRange(range).setNumberFormat('0.000');
summary.getRange('I107:I111').setNumberFormat('0.0%');summary.getRange('H107:H111').format.horizontalAlignment='center';
summary.getRange('A118:J118').values=[['Format / mode','Trigger Hz','Observed s','Matched sets','Min spread ms','Median ms','P95 ms','Max ms','Changes/s min','Changes/s max']];header('A118:J118');
summary.getRange('H110:H111').values=[['ROI anomaly']];
summary.getRange('A112').values=[['Anomalous transitions are retained in the rates above; they are not evidence of additional sensor exposures.']];
const primaryMatchedEnd=matchedStart+c.spreads_us.raster.n-1;
const ref=`'Matched rasters'!L${matchedStart}:L${primaryMatchedEnd}`;
summary.getRange('A119:C119').values=[['1080p60 ExtTrig',c.trigger_hz,c.observed_s]];
summary.getRange('D119:J119').formulas=[[`=COUNT(${ref})`,`=MIN(${ref})`,`=MEDIAN(${ref})`,`=PERCENTILE(${ref},0.95)`,`=MAX(${ref})`,'=MIN(G107:G111)','=MAX(G107:G111)']];
summary.getRange('C119').setNumberFormat('0.00');summary.getRange('D119').setNumberFormat('#,##0');summary.getRange('E119:J119').setNumberFormat('0.000');
style(summary,'A129:J148');
summary.getRange('A129').values=[['Repeat at unchanged 1/60 s, 30 Hz trigger and sampling phases']];summary.getRange('A129').format.font.bold=true;
summary.getRange('A130').values=[['One additional live block. The same preceding five-camera Freeze control applies; settings and phase taps were unchanged.']];
summary.getRange('A132:J132').values=[['Camera','Trigger Hz','Observed s','Raster count','Rasters/s','ROI changes','Changes/s','CRC scope','Strict valid %','Sequence gaps']];header('A132:J132');
for(let cam=2;cam<=6;cam++){
  const row=cam+131,criteria=`${col('A')},"${repeat.id}",${col('F')},"rising",${col('E')},A${row}`,sum=s=>`SUMIFS(${col(s)},${criteria})`;
  summary.getRange(`A${row}:J${row}`).values=[[cam,30,null,null,null,null,null,cam===5?'ROI anomaly':'96x96 ROI',null,null]];
  summary.getRange(`C${row}:G${row}`).formulas=[[`=${sum('N')}`,`=${sum('I')}`,`=(D${row}-COUNTIFS(${criteria}))/C${row}`,`=${sum('R')}`,`=F${row}/C${row}`]];
  summary.getRange(`I${row}:J${row}`).formulas=[[`=${sum('K')}/D${row}`,`=${sum('M')}`]];
  const m=repeatMetrics.cameras.find(x=>x.camera===cam);expected.push({row,camera:cam,seconds:m.seconds,records:m.rasters,raster_hz:m.raster_hz,changes:m.roi_changes,change_hz:m.roi_changes_hz});
}
summary.getRange('C133:C137').setNumberFormat('0.00');
for(const range of ['D133:D137','F133:F137'])summary.getRange(range).setNumberFormat('#,##0');
for(const range of ['E133:E137','G133:G137'])summary.getRange(range).setNumberFormat('0.000');
summary.getRange('I133:I137').setNumberFormat('0.0%');summary.getRange('H133:H137').format.horizontalAlignment='center';
summary.getRange('A139').values=[['Camera 5 repeat: 851 two-raster intervals and 10 one-raster intervals. Each other camera has 856 intervals, all two rasters.']];
summary.getRange('A140').values=[['Camera 6 repeat supports a clean 30 ROI updates/s cadence. Its two primary-capture one-raster intervals remain documented.']];
summary.getRange('A141').values=[['Camera 5 CRC anomalies persist despite a stable frozen ROI. Sampling errors are possible; the cause is not established.']];
summary.getRange('A143:J143').values=[['Format / mode','Trigger Hz','Observed s','Matched sets','Min spread ms','Median ms','P95 ms','Max ms','Changes/s min','Changes/s max']];header('A143:J143');
const repeatRef=`'Matched rasters'!L${primaryMatchedEnd+1}:L${matchedEnd}`;
summary.getRange('A144:C144').values=[['1080p60 repeat',30,repeat.observed_s]];
summary.getRange('D144:J144').formulas=[[`=COUNT(${repeatRef})`,`=MIN(${repeatRef})`,`=MEDIAN(${repeatRef})`,`=PERCENTILE(${repeatRef},0.95)`,`=MAX(${repeatRef})`,'=MIN(G133:G137)','=MAX(G133:G137)']];
summary.getRange('C144').setNumberFormat('0.00');summary.getRange('D144').setNumberFormat('#,##0');summary.getRange('E144:J144').setNumberFormat('0.000');
summary.getRange('A146').values=[['At the 1/60 s shutter setting, cameras 2–4 and the camera 6 repeat retain a clean 30 ROI updates/s cadence.']];
summary.getRange('A147').values=[['This does not establish a clean whole-frame rate on all five cameras, physical integration time, or synchronized exposures.']];
summary.getRange('A148').values=[['Spread varies between sequential captures; this comparison does not attribute its change to shutter speed or trigger rate.']];
wb.recalculate();
for(const e of expected){const v=summary.getRange(`C${e.row}:G${e.row}`).values[0];[e.seconds,e.records,e.raster_hz,e.changes,e.change_hz].forEach((x,i)=>{if(typeof v[i]!=='number'||Math.abs(v[i]-x)>1e-8)throw Error(`Camera ${e.camera} formula mismatch`);});}
const spread=[c.spreads_us.raster.n,...['min','median','p95','max'].map(k=>c.spreads_us.raster[k]/1000)],got=summary.getRange('D119:H119').values[0];
spread.forEach((x,i)=>{if(Math.abs(got[i]-x)>1e-8)throw Error('Spread formula mismatch');});
const repeatSpread=[repeat.spreads_us.raster.n,...['min','median','p95','max'].map(k=>repeat.spreads_us.raster[k]/1000)],repeatGot=summary.getRange('D144:H144').values[0];
repeatSpread.forEach((x,i)=>{if(Math.abs(repeatGot[i]-x)>1e-8)throw Error('Repeat spread formula mismatch');});
const scan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Exposure follow-up formula error scan'});
await fs.writeFile(path.join(scratch,'report_error_scan.ndjson'),scan.ndjson);if(scan.ndjson.split('\n').filter(Boolean).some(l=>JSON.parse(l).kind==='match'))throw Error('Formula errors');
await render('Comparison','A99:J125','exposure60');await render('Comparison','A129:J148','repeat');await render('Camera results',`A${cameraStart}:M${cameraStart+5}`,'appended_cameras');await render('Matched rasters',`A${matchedStart}:P${matchedStart+5}`,'appended_rasters');
const output=path.join(root,'outputs/01a1110b-4bdf-79b3-af63-c2b05f5fcb99/EO_Camera_Synchronization_Comparison_20261009_Exposure60.xlsx');
console.log('Calculations and previews complete. Export requires the separately reviewed restoration record.');
const deadline=Date.now()+600000;let restored;
while(Date.now()<deadline){
  try{restored=JSON.parse(await fs.readFile(path.join(root,source,'restoration/verified_state.json'),'utf8'));break;}
  catch(e){if(e.code!=='ENOENT')throw e;await new Promise(resolve=>setTimeout(resolve,5000));}
}
if(!restored?.all_camera_readbacks_verified||!restored.display_matches_initial||!restored.pose_matches_initial)throw Error('Restoration is not verified');
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
await fs.writeFile(path.join(scratch,'report_validation.json'),JSON.stringify({output,cameraStart,cameraEnd,matchedStart,matchedEnd,expected,spread,spreadRow:119,repeatSpread,repeatSpreadRow:144},null,2));
console.log(output);
