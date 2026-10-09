"""Explicit sequential five-camera DNR test stages with durable evidence."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch')
OUT=ROOT/'captures/eo_dnr_all5_20261009'
SCRATCH=Path(__file__).resolve().parent
PY=Path('C:/Users/USER/AppData/Local/Programs/Python/Python39/python.exe')
VIVADO=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
SCRIPTS=ROOT/'diagnostics/eo_sync/scripts'
R2=ROOT/'builds/eo_sync_20261008_r2/EoSyncTop.ltx'
R4=ROOT/'builds/eo_sync_20261008_r4_trig30/EoSyncTop.ltx'
OP=ROOT/'builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit'
TAPS='336:280:308:280:322';CAMS='2:3:4:5:6'
FORMAT=('enter:down:down:down:down:down:enter:down:down:down','up:up:up:up:enter:up:up:up:up:up:up:enter')
EXPOSURE=('enter:down:enter','up:enter:up:up:enter')
SHUTTER=(EXPOSURE[0]+':down:down:down','up:up:up:up:enter:up:up:enter')
TRIGGER=('enter:enter','up:enter:up:enter')
IMAGE=('enter:down:down:down:enter','up:enter:up:up:up:up:enter')
DNR=(IMAGE[0]+':down','up:up:enter:up:up:up:up:enter')
FREEZE=(IMAGE[0]+':down:down:down:down:down:down','up:up:up:up:up:up:up:enter:up:up:up:up:enter')

def run(command,label,save_stdout=None):
    log=SCRATCH/(label+'.log')
    if log.exists():raise FileExistsError(log)
    with log.open('w',encoding='utf-8') as f:
        p=subprocess.run([str(x) for x in command],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'{label}: exit {p.returncode}; inspect {log}')
    if save_stdout:(OUT/save_stdout).write_bytes(log.read_bytes())
    print(label+' complete',flush=True)

def tcl(script,args,label):
    run([VIVADO,'-mode','batch','-nolog','-nojournal','-source',SCRIPTS/(script+'.tcl'),'-tclargs',*args],label)

def snapshots(ltx,label,menu,extra='',cameras=CAMS):
    keys,close=menu
    if extra:keys+=':'+extra
    tcl('capture_snapshots',[ltx,OUT/label,cameras,keys,close],label)
    items=[]
    for camera in cameras.split(':'):
        folder=OUT/label/('cam'+camera)
        run([PY,SCRIPTS/'decode_snapshot.py',folder],label+'_decode_cam'+camera)
        frame=json.loads((folder/'snapshot_summary.json').read_text())['frames'][0]['file']
        items.append((label+'/cam'+camera,folder/frame))
    cols=min(3,len(items));rows=(len(items)+cols-1)//cols
    canvas=Image.new('RGB',(cols*512,rows*476),'white');draw=ImageDraw.Draw(canvas)
    for i,(name,p) in enumerate(items):
        x=(i%cols)*512;y=(i//cols)*476
        draw.text((x+8,y+7),name,fill='black');canvas.paste(Image.open(p).convert('RGB'),(x,y+28))
    canvas.save(OUT/('contact_'+label+'.png'))

def formats(label,direction):
    keys=(FORMAT[0]+':'+direction+':'+FORMAT[1]).split(':')
    for camera in range(2,7):
        run([PY,SCRIPTS/'osd_keys.py','--cam',camera,'--keys',*keys,'--out',OUT/f'{label}_cam{camera}.json'],f'{label}_cam{camera}')

p=argparse.ArgumentParser();p.add_argument('stage');a=p.parse_args()
OUT.mkdir(parents=True,exist_ok=True)
if a.stage in ['initial_state','final_state']:
    name='initial' if a.stage=='initial_state' else 'final'
    run([PY,ROOT/'scripts/eo_video_mode.py','--show'],name+'_display',name+'_display.txt')
    run([PY,ROOT/'scripts/icd_set_offsets.py','--show'],name+'_pose',name+'_pose.txt')
    selected=int(re.search(r'current video select (\d+)',(OUT/(name+'_display.txt')).read_text()).group(1))
    assert 1<=selected<=6,selected
    run([PY,ROOT/'scripts/eo_osd_evidence.py','--cam',selected,'--keys','--out',OUT/(name+'_usb.png')],name+'_usb')
elif a.stage in ['reader_initial','reader_restore']:
    tcl('program',[R2.with_suffix('.bit')],a.stage+'_program')
    tcl('select_snapshot_phase',[R2,0],a.stage+'_snapshot_rising')
elif a.stage.startswith('initial_') or a.stage.startswith('restored_'):
    label=a.stage;section=label.split('_',1)[1]
    snapshots(R2,label,{'format':FORMAT,'exposure':EXPOSURE,'trigger':TRIGGER,'image':IMAGE,'closed':('-','-')}[section])
elif a.stage=='set60':formats('set60','right')
elif a.stage=='restore30':formats('restore30','left')
elif a.stage=='program_measure':
    tcl('program',[R4.with_suffix('.bit')],'program_r4')
    tcl('phase_capture',[R4,OUT/'selected_phase','set',TAPS],'selected_phase')
    tcl('select_snapshot_phase',[R4,0],'r4_snapshot_rising')
elif a.stage in ['set_exposure60','restore_exposure240']:
    snapshots(R4,a.stage,SHUTTER,extra='left:left:left' if a.stage=='set_exposure60' else 'right:right:right')
elif a.stage in ['test_format','test_exposure','test_trigger','test_image']:
    snapshots(R4,a.stage,{'format':FORMAT,'exposure':EXPOSURE,'trigger':TRIGGER,'image':IMAGE}[a.stage.split('_')[1]])
elif a.stage in ['dnr_off','dnr_off_repeat','dnr_on_return']:
    snapshots(R4,a.stage,DNR,extra='left:left:left' if 'off' in a.stage else 'right:right:right')
elif a.stage in ['off_frozen_setup','restore_image_on']:
    direction='left:left:left' if a.stage=='off_frozen_setup' else 'right:right:right'
    snapshots(R4,a.stage,(DNR[0],FREEZE[1]),extra=direction+':down:down:down:down:down:right')
elif a.stage in ['freeze_on_on','freeze_off_on','freeze_on_off','freeze_off_off']:
    snapshots(R4,a.stage,FREEZE,extra='right')
elif a.stage in ['control_on','on_a','control_off','off_b','on_return','off_repeat']:
    tcl('capture',[R4,OUT/a.stage,1 if a.stage.startswith('control') else 2,TAPS],a.stage)
elif a.stage=='restore_operational':
    assert hashlib.sha256(OP.read_bytes()).hexdigest()=='d905e96d96990528a5c2098e0e018fa9d88814a18703fb0ce4f09a348b5f2cfd'
    tcl('program',[OP],'restore_operational')
else:raise ValueError(a.stage)
