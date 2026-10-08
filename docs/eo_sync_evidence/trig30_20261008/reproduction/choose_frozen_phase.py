import json
import sys
from pathlib import Path
folder=Path(sys.argv[1]);data=json.loads((folder/'phase_summary.json').read_text())
assert data['frozen_declared']
all_taps=sorted({r['tap'] for r in data['rows']});n=len(all_taps)
assert n==16 and all_taps==list(range(0,448,28))
selection=[]
for cam in range(2,7):
    candidates=[]
    for scope in ['full','roi']:
        for phase in ['rising','falling']:
            rows={r['tap']:r for r in data['rows'] if r['camera']==cam and r['phase']==phase}
            for i,tap in enumerate(all_taps):
                r=rows[tap]
                if not r[f'frozen_{scope}_stable']:continue
                crc=r[f'modal_{scope}_crc'];run=[]
                for j in range(n):
                    t=all_taps[(i+j)%n];q=rows[t]
                    if not q[f'frozen_{scope}_stable'] or q[f'modal_{scope}_crc']!=crc:break
                    run.append(t)
                if len(run)>=3:
                    candidates.append(dict(camera=cam,phase=phase,tap=run[len(run)//2],scope=scope,
                                           contiguous_taps=run,crc=crc))
    candidates.sort(key=lambda r:(r['scope']=='full',len(r['contiguous_taps']),r['phase']=='rising'),reverse=True)
    if not candidates:raise ValueError(f'Camera {cam}: no 3-tap stable frozen window')
    selection.append(candidates[0])
print(json.dumps(selection,indent=2))
(folder/'proposed_selection.json').write_text(json.dumps(selection,indent=2)+'\n')
