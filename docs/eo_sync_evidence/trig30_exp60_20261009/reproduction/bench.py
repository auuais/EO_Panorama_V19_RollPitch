"""Explicit bench stages. Hardware mutations are sequential; inspect each readback."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'captures/eo_sync_trig30_exp60_20261009'
SCRATCH=Path(__file__).resolve().parent
PY=Path('C:/Users/USER/AppData/Local/Programs/Python/Python39/python.exe')
VIVADO=Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
LTX=ROOT/'builds/eo_sync_20261008_r4_trig30/EoSyncTop.ltx'
SCRIPTS=ROOT/'diagnostics/eo_sync/scripts'
TAPS='336:280:308:280:322'
CAMERAS='2:3:4:5:6'
def run(command, name):
    log=SCRATCH/(name+'.log')
    if log.exists():raise FileExistsError(log)
    with log.open('w',encoding='utf-8') as f:
        p=subprocess.run([str(s) for s in command],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'{name}: exit {p.returncode}; inspect {log}')
    print(name+' complete',flush=True)
def tcl(script,args,label):run([VIVADO,'-mode','batch','-nolog','-nojournal','-source',SCRIPTS/(script+'.tcl'),'-tclargs',*args],label)
def snapshots(label,keys,close,cameras=CAMERAS):
    tcl('capture_snapshots',[LTX,OUT/label,cameras,keys,close],label)
def format_change(label,direction):
    keys=['enter']+['down']*5+['enter']+['down']*3+[direction]+['up']*4+['enter']+['up']*6+['enter']
    for cam in range(2,7):
        run([PY,SCRIPTS/'osd_keys.py','--cam',cam,'--keys',*keys,'--out',OUT/f'{label}_cam{cam}.json'],f'{label}_cam{cam}')

p=argparse.ArgumentParser();p.add_argument('stage');a=p.parse_args()
if a.stage=='set60':format_change('set60','right')
elif a.stage=='program':
    tcl('program',[LTX.with_suffix('.bit')],'program_r4')
    tcl('phase_capture',[LTX,OUT/'selected_phase','set',TAPS],'selected_phase')
    tcl('select_snapshot_phase',[LTX,0],'snapshot_rising')
elif a.stage=='exposure_probe':snapshots('exposure_probe','enter:down:enter:down:down:down:left:left:left','up:up:up:up:enter:up:up:enter','2')
elif a.stage=='set_exposure_others':snapshots('exposure_others','enter:down:enter:down:down:down:left:left:left','up:up:up:up:enter:up:up:enter','3:4:5:6')
elif a.stage=='verify_settings':
    snapshots('baseline_exposure','enter:down:enter','up:enter:up:up:enter')
    snapshots('baseline_trigger','enter:enter','up:enter:up:enter')
    snapshots('baseline_format','enter:down:down:down:down:down:enter:down:down:down','up:up:up:up:enter:up:up:up:up:up:up:enter')
elif a.stage in ['freeze_on','freeze_off']:
    snapshots(a.stage,'enter:down:down:down:enter:down:down:down:down:down:down:right','up:up:up:up:up:up:up:enter:up:up:up:up:enter')
elif a.stage in ['control','live']:
    label='60_trig30_exp60_'+('freeze' if a.stage=='control' else 'live')
    tcl('capture',[LTX,OUT/label,1 if a.stage=='control' else 2,TAPS],label)
elif a.stage=='repeat':tcl('capture',[LTX,OUT/'60_trig30_exp60_repeat',1,TAPS],'60_trig30_exp60_repeat')
elif a.stage=='restore_exposure':
    snapshots('restore_exposure','enter:down:enter:down:down:down:right:right:right','up:up:up:up:enter:up:up:enter')
elif a.stage=='restore30':
    format_change('restore30','left')
    tcl('program',[ROOT/'builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit'],'restore_operational')
elif a.stage=='restore_readback':run([PY,SCRIPTS/'read_osd_usb.py',OUT/'restoration'],'restore_readback')
else:raise ValueError(a.stage)
