"""Sequential, explicit single-camera DNR bench stages; no USB selection writes."""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'captures/eo_dnr_cam2_20261009'
SCRATCH = Path(__file__).resolve().parent
PY = Path('C:/Users/USER/AppData/Local/Programs/Python/Python39/python.exe')
VIVADO = Path('C:/AMDDesignTools/2025.2/Vivado/bin/vivado.bat')
SCRIPTS = ROOT / 'diagnostics/eo_sync/scripts'
R2 = ROOT / 'builds/eo_sync_20261008_r2/EoSyncTop.ltx'
R4 = ROOT / 'builds/eo_sync_20261008_r4_trig30/EoSyncTop.ltx'
TAPS = '336:280:308:280:322'
FORMAT = ('enter:down:down:down:down:down:enter:down:down:down',
          'up:up:up:up:enter:up:up:up:up:up:up:enter')
EXPOSURE = ('enter:down:enter', 'up:enter:up:up:enter')
TRIGGER = ('enter:enter', 'up:enter:up:enter')
IMAGE = ('enter:down:down:down:enter', 'up:enter:up:up:up:up:enter')
DNR = ('enter:down:down:down:enter:down', 'up:up:enter:up:up:up:up:enter')
FREEZE = ('enter:down:down:down:enter:down:down:down:down:down:down',
          'up:up:up:up:up:up:up:enter:up:up:up:up:enter')

def run(command, name):
    log = SCRATCH / (name + '.log')
    if log.exists():
        raise FileExistsError(log)
    with log.open('w', encoding='utf-8') as f:
        p = subprocess.run([str(s) for s in command], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f'{name}: exit {p.returncode}; inspect {log}')
    print(name + ' complete', flush=True)

def tcl(script, args, label):
    run([VIVADO, '-mode', 'batch', '-nolog', '-nojournal', '-source',
         SCRIPTS / (script + '.tcl'), '-tclargs', *args], label)

def snapshots(ltx, label, menu, cameras='2', extra=''):
    keys, close = menu
    if extra:
        keys += ':' + extra
    tcl('capture_snapshots', [ltx, OUT / label, cameras, keys, close], label)
    for camera in cameras.split(':'):
        run([PY, SCRIPTS / 'decode_snapshot.py', OUT / label / ('cam' + camera)],
            label + '_decode_cam' + camera)

def formats(label, direction):
    keys = (FORMAT[0] + ':' + direction + ':' + FORMAT[1]).split(':')
    for cam in range(2, 7):
        run([PY, SCRIPTS / 'osd_keys.py', '--cam', cam, '--keys', *keys,
             '--out', OUT / f'{label}_cam{cam}.json'], f'{label}_cam{cam}')

parser = argparse.ArgumentParser()
parser.add_argument('stage')
a = parser.parse_args()
if a.stage == 'reader_initial':
    tcl('program', [R2.with_suffix('.bit')], 'program_r2_initial')
    tcl('select_snapshot_phase', [R2, 0], 'r2_initial_snapshot_rising')
elif a.stage == 'initial_readback':
    snapshots(R2, 'initial_format', FORMAT, '2:3:4:5:6')
    snapshots(R2, 'initial_exposure', EXPOSURE)
    snapshots(R2, 'initial_trigger', TRIGGER)
    snapshots(R2, 'initial_image', IMAGE)
elif a.stage == 'set60':
    formats('set60', 'right')
elif a.stage == 'program_measure':
    tcl('program', [R4.with_suffix('.bit')], 'program_r4')
    tcl('phase_capture', [R4, OUT / 'selected_phase', 'set', TAPS], 'selected_phase')
    tcl('select_snapshot_phase', [R4, 0], 'r4_snapshot_rising')
elif a.stage == 'set_exposure60':
    snapshots(R4, 'test_exposure',
              (EXPOSURE[0] + ':down:down:down', 'up:up:up:up:enter:up:up:enter'),
              extra='left:left:left')
elif a.stage == 'test_readback':
    snapshots(R4, 'test_format', FORMAT)
    snapshots(R4, 'test_trigger', TRIGGER)
    snapshots(R4, 'test_image_on', IMAGE)
elif a.stage in ['freeze_on_on', 'freeze_off_on', 'freeze_on_off', 'freeze_off_off']:
    snapshots(R4, a.stage, FREEZE, extra='right')
elif a.stage in ['dnr_off', 'dnr_on_return', 'dnr_off_control', 'dnr_on_restore']:
    extra = 'left:left:left' if 'off' in a.stage else 'right:right:right'
    snapshots(R4, a.stage, DNR, extra=extra)
elif a.stage == 'off_frozen_setup':
    snapshots(R4, a.stage,
              (DNR[0], FREEZE[1]),
              extra='left:left:left:down:down:down:down:down:right')
elif a.stage == 'restore_camera2':
    # Closed-menu state is verified again after returning to the original format.
    keys = (DNR[0] + ':right:right:right:down:down:down:down:down:right:' + FREEZE[1]).split(':')
    run([PY, SCRIPTS/'osd_keys.py', '--cam', 2, '--keys', *keys,
         '--out', OUT/'restore_cam2_image_keys.json'], 'restore_cam2_image_keys')
    keys = (EXPOSURE[0] + ':down:down:down:right:right:right:up:up:up:up:enter:up:up:enter').split(':')
    run([PY, SCRIPTS/'osd_keys.py', '--cam', 2, '--keys', *keys,
         '--out', OUT/'restore_cam2_exposure_keys.json'], 'restore_cam2_exposure_keys')
elif a.stage in ['control_on', 'on_a', 'off_b', 'on_return', 'control_off']:
    blocks = 1 if a.stage.startswith('control') else 2
    tcl('capture', [R4, OUT / a.stage, blocks, TAPS], a.stage)
elif a.stage == 'restore_exposure':
    snapshots(R4, 'restore_exposure',
              (EXPOSURE[0] + ':down:down:down', 'up:up:up:up:enter:up:up:enter'),
              extra='right:right:right')
elif a.stage == 'restore30':
    formats('restore30', 'left')
    tcl('program', [R2.with_suffix('.bit')], 'program_r2_restore')
    tcl('select_snapshot_phase', [R2, 0], 'r2_restore_snapshot_rising')
elif a.stage == 'restore_readback':
    snapshots(R2, 'restored_format', FORMAT, '2:3:4:5:6')
    snapshots(R2, 'restored_exposure', EXPOSURE)
    snapshots(R2, 'restored_trigger', TRIGGER)
    snapshots(R2, 'restored_image', IMAGE)
elif a.stage == 'restore_closed':
    snapshots(R2, 'restored_closed', ('-', '-'), '2:3:4:5:6')
elif a.stage == 'restore_operational':
    tcl('program', [ROOT / 'builds/bit_archive/20261006_221847_trsmon_trig60_9a8a81e/KintexTop_EO_IR_HD_SDI_panorama_base.bit'], 'restore_operational')
else:
    raise ValueError(a.stage)
