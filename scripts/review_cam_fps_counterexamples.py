"""Reproduce decoder verification and why descriptor labels are not FPS."""
import csv
from pathlib import Path
from decode_cam_fps import field
from v19_verify_epoch_rejoin import Camera

root = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader((root/'sim_out/cam_fps_review_20261006/sim_words.csv').open()))
for row in rows:
    word = int(row['word'], 16)
    assert field(word, 41, 39) == int(row['camera'])
    assert field(word, 38, 31) == int(row['expected_fps'])
assert {int(row['camera']) for row in rows} == set(range(6))
print('PASS: production decoder recovers all six RTL-simulated camera IDs and rates')

# Existing repository model of the exact trigger_pending / frame_epoch_next
# equations in EoV19DdrDesync.v. This is a logic counterexample, not a DDR test.
cam = Camera()
epoch = 0
records = []
for step in range(30000):
    if step % 100 == 0:
        epoch += 1                         # 30 triggers per modeled second
    frame = step % 120 == 61                # 25 rasters; avoid coincident events
    cam.tick(epoch, frame, step)
    if frame:
        records.append((step/3000, cam.assigned[step]))
steady = [row for row in records if 1 <= row[0] < 9]
actual = len(steady)/8
slope = (steady[-1][1]-steady[0][1])/(steady[-1][0]-steady[0][0])
assert actual == 25 and 29.8 < slope < 30.2
print(f'COUNTEREXAMPLE: {actual:.1f} actual frames/s, {slope:.6f} epoch labels/s')
print('First fifteen (time_s, epoch_label):', records[:15])
print('This does not establish the actual camera exposure rate.')
