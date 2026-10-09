"""Restore the remembered EO6 route without sending valid camera parameter fields.

The inspected MCU handler applies the route first, then skips out-of-range
ancillary fields. This is specific to the inspected firmware, not a general
ICD no-change sentinel. It writes the same MCU mode back to its mode flash.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'captures/eo_dnr_cam2_20261009'
sys.path.insert(0,str(ROOT/'scripts'))
from eo_cam_power import Master,find_port
from eo_video_mode import read_status

source=Path('C:/SVNProjects/IMU_Stabilize_v40/EO_OSD_Remote_20260812/ST_Link-test/Core/Src/mcu_fsm.c')
code=source.read_text(encoding='utf-8',errors='replace')
for guard in ['if (payload[1] <= 99u)', 'if (payload[2] <= 99u)',
              'if (payload[3] <= 2u)', 'if (payload[4] <= 2u)',
              'if (payload[5] <= 2u)', 'if (blend <= 999u)']:
    assert guard in code,guard
result=dict(at=datetime.now().astimezone().isoformat(),source=str(source),
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            reviewed_functions=['mcu_on_icd_frame/PANORAMA_CONTROL','icd_apply_panorama_camera_params','icd_apply_mode'],
            request_payload_hex='06ffffffffffffff',
            semantics='Select EO physical camera 6; all ancillary fields are outside checked ranges, so the inspected handler skips camera/display parameter writes.',
            standard_eo_video_mode_select_used=False,valid_camera_parameter_fields_sent=False,
            mcu_mode_flash_write=True,fpga_configuration_flash_write=False)
m=Master(find_port())
try:
    before=read_status(m)
    assert before[13]==6 and bytes(before[14:21])==bytes(7),before.hex()
    result['status_before_hex']=before.hex()
    m.send(0x2203,bytes([6])+bytes([255])*7)
    ack,_=m.collect(4,want=0x22A3)
    assert ack is not None,'Mode-only restore ACK missing'
    result['ack_hex']=ack[2].hex()
    assert ack[2][:8]==bytes([6])+bytes(7),ack[2].hex()
    after=read_status(m)
    result['status_after_hex']=after.hex()
    assert after[0]==before[0] and after[13:21]==before[13:21],(before.hex(),after.hex())
    result['reported_mode_and_all_parameters_unchanged']=True
finally:
    m.close()
(OUT/'restore_route_only.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Mode-only route request acknowledged; controller mode and parameter bytes remain unchanged. Verify USB image separately.')
