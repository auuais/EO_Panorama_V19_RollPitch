import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[2]/'captures/eo_dnr_cam2_20261009'
items = []
for label in sys.argv[1:]:
    for folder in sorted((root/label).glob('cam*')):
        summary = folder/'snapshot_summary.json'
        if summary.exists():
            frame = json.loads(summary.read_text())['frames'][0]['file']
            items.append((label+'/'+folder.name, folder/frame))
if not items:
    raise ValueError('No decoded images')
cols = min(3,len(items)); rows = (len(items)+cols-1)//cols
canvas = Image.new('RGB',(cols*512,rows*476),'white')
draw = ImageDraw.Draw(canvas)
for i,(label,path) in enumerate(items):
    x=(i%cols)*512;y=(i//cols)*476
    draw.text((x+8,y+7),label,fill='black')
    canvas.paste(Image.open(path).convert('RGB'),(x,y+28))
output = root/('contact_'+'_'.join(sys.argv[1:])+'.png')
canvas.save(output)
print(output)
