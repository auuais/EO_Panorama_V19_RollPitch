#!/usr/bin/env python3
"""Decode probe12: lines per frame and the F bit, from the cameras' SAV/EAV.

    python scripts/decode_cam_trs.py <capture dir>

probe11 counts frame starts (how many frames the camera transmitted); probe12
says what was inside them.  A full 1080p frame carries ~1125 EAV codes between
frame starts (1080 active + blanking).  Half that, or an F bit that keeps
changing, means fields rather than frames.
"""
import csv
import sys
from pathlib import Path

f = lambda v, hi, lo: (v >> lo) & ((1 << (hi - lo + 1)) - 1)


def val(rows, col):
    for r in rows:
        try:
            return int(r[col].strip(), 16)
        except ValueError:
            continue
    return None


def main():
    d = Path(sys.argv[1])
    cams = {}
    for p in sorted(d.glob("w*.csv")):
        rows = list(csv.DictReader(p.open()))
        c11 = next((k for k in rows[0] if "eo_cam_rate_word" in k), None)
        c12 = next((k for k in rows[0] if "eo_cam_trs_word" in k), None)
        if c12 is None:
            sys.exit("no eo_cam_trs_word probe: this bitstream predates the SAV/EAV counters")
        v12 = val(rows, c12)
        v11 = val(rows, c11) if c11 else None
        if v12 is None:
            continue
        sel = f(v12, 63, 61)
        cams[sel] = dict(lines=f(v12, 60, 49), lmin=f(v12, 48, 37), lmax=f(v12, 36, 25),
                         ftog=f(v12, 24, 17), frames=f(v12, 16, 9),
                         vsync_fps=(f(v11, 38, 31) if v11 and f(v11, 63, 62) == 2 else None))
    if not cams:
        sys.exit("no samples")
    print(f"{'camera':8s} {'frames/s':>9s} {'VSYNC/s':>8s} {'lines last':>11s} "
          f"{'lines min':>10s} {'lines max':>10s} {'F changes/s':>12s}")
    for k in sorted(cams):
        c = cams[k]
        vs = c["vsync_fps"] if c["vsync_fps"] is not None else -1
        print(f"cam {k+1:<4d} {c['frames']:9d} {vs:8d} {c['lines']:11d} "
              f"{c['lmin']:10d} {c['lmax']:10d} {c['ftog']:12d}")
    missing = [k + 1 for k in range(6) if k not in cams]
    if missing:
        print(f"no sample for camera(s) {missing} - run more sweeps")


if __name__ == "__main__":
    main()
