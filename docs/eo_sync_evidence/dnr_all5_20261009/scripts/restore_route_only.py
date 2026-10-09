"""Reapply the starting EO route using reviewed out-of-range ancillary fields."""
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
ROOT=Path('E:/Xylinx/EO_Panorama_V19_RollPitch');OUT=ROOT/'captures/eo_dnr_all5_20261009'
sys.path.insert(0,str(ROOT/'scripts'))
from eo_cam_power import Master,find_port
from eo_video_mode import read_status
selected=int(re.search(r'current video select (\d+)',(OUT/'initial_display.txt').read_text()).group(1))
assert 1<=selected<=6
source=Path('C:/SVNProjects/IMU_Stabilize_v40/EO_OSD_Remote_20260812/ST_Link-test/Core/Src/mcu_fsm.c')
code=source.read_text(encoding='utf-8',errors='replace')
for guard in ['if (payload[1] <= 99u)','if (payload[2] <= 99u)','if (payload[3] <= 2u)',
              'if (payload[4] <= 2u)','if (payload[5] <= 2u)','if (blend <= 999u)']:assert guard in code
m=Master(find_port());payload=bytes([selected])+bytes([255])*7
result=dict(at=datetime.now().astimezone().isoformat(),source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    selected_eo_camera=selected,payload_hex=payload.hex(),semantics='Route first; inspected firmware skips ancillary camera/display writes because their fields exceed its checked ranges.',
    standard_eo_video_mode_select_used=False,mcu_mode_flash_written=True,fpga_configuration_flash_programmed=False)
try:
    before=read_status(m);assert before[13]==selected and before[14:21]==bytes(7),before.hex()
    result['status_before_hex']=before.hex();m.send(0x2203,payload);ack,_=m.collect(4,want=0x22A3)
    assert ack is not None;assert ack[2][:8]==bytes([selected])+bytes(7)
    result['ack_hex']=ack[2].hex();after=read_status(m);result['status_after_hex']=after.hex()
    assert after[0]==before[0] and after[13:21]==before[13:21]
    result['controller_mode_and_parameters_unchanged']=True
finally:m.close()
(OUT/'restore_route_only.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Starting EO route restored; controller parameters unchanged. Verify USB scene separately.')
