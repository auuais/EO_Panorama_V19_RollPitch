"""Archive all five EO OSD menus through the operational 1080p30 USB path.

Start with closed menus. Uses only navigation keys, never setting keys or
SAVE/DFLT. Ends with menus closed and display selector 6. Inspect screenshots
to establish state; serial ACKs alone do not verify camera settings.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parents[3]
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    def run(script,args,log=None):
        result=subprocess.run([sys.executable,str(root/script),*args],text=True,capture_output=True)
        if log:log.write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        print(result.stdout,flush=True)
    def shot(cam,label,keys):
        run(Path('scripts/eo_osd_evidence.py'),['--cam',str(cam),'--keys',*keys,'--out',str(out/f'cam{cam}_{label}.png')])
    for cam in range(2,7):
        run(Path('scripts/eo_video_mode.py'),['--select',str(cam)],out/f'cam{cam}_select.txt')
        shot(cam,'trigger',['enter','enter'])
        shot(cam,'exposure',['up','enter','down','enter'])
        shot(cam,'image',['up','enter','down','down','enter']+['down']*6)
        shot(cam,'format',['up']*7+['enter','down','down','enter']+['down']*3)
        shot(cam,'closed',['up']*4+['enter']+['up']*6+['enter'])
    run(Path('scripts/eo_video_mode.py'),['--show'],out/'display.txt')
    run(Path('scripts/icd_set_offsets.py'),['--show'],out/'pose.txt')
    print('OSD_USB_READBACK_CAPTURE_COMPLETE',flush=True)


if __name__=='__main__':main()
