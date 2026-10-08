"""Read all camera menus through the restored operational USB path.

Run only after cameras are known to have closed menus and the operational
1080p30 FPGA has been restored. Does not change camera settings.
"""
import json
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
out = root/'captures/eo_sync_20261008/restoration'
out.mkdir(exist_ok=False)
python = sys.executable
def run(script, args, log=None):
    p = subprocess.run([python, str(root/script), *args], text=True, capture_output=True)
    if log: log.write_text(p.stdout+p.stderr, encoding='utf-8')
    if p.returncode: raise RuntimeError(p.stdout+p.stderr)
    print(p.stdout, flush=True)
def shot(cam, label, keys):
    run(Path('scripts/eo_osd_evidence.py'), ['--cam',str(cam),'--keys',*keys,'--out',str(out/f'cam{cam}_{label}.png')])
for cam in range(2,7):
    run(Path('scripts/eo_video_mode.py'), ['--select',str(cam)],out/f'cam{cam}_select.txt')
    shot(cam,'trigger',['enter','enter'])
    shot(cam,'exposure',['up','enter','down','enter'])
    shot(cam,'image',['up','enter','down','down','enter','down','down','down','down','down','down'])
    shot(cam,'format',['up']*7+['enter','down','down','enter','down','down','down'])
    shot(cam,'closed',['up']*4+['enter']+['up']*6+['enter'])
run(Path('scripts/eo_video_mode.py'), ['--show'], out/'display.txt')
run(Path('scripts/icd_set_offsets.py'), ['--show'], out/'pose.txt')
print('RESTORATION_READBACK_CAPTURE_COMPLETE',flush=True)
