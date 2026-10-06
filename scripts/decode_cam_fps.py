#!/usr/bin/env python3
"""Decode EoCamFrameRateMon's probe word from measure_eo_cam_fps.tcl captures.

    python scripts/decode_cam_fps.py <capture dir>

Each capture reports one camera (the monitor advances the camera every second),
so several captures are needed to cover all six.  Read the SPREAD, not the
rate: six free-running cameras also read ~30 fps each.
"""
import csv
import sys
from pathlib import Path

US_PER_TICK = 256 * 1_000_000 / 74_250_000      # hd_clk 74.25 MHz, 256-cycle ticks


def field(v, hi, lo):
    return (v >> lo) & ((1 << (hi - lo + 1)) - 1)


def main():
    d = Path(sys.argv[1])
    cams, trig = {}, None
    for f in sorted(d.glob("w*.csv")):
        rows = list(csv.DictReader(f.open()))
        col = next((k for k in rows[0] if "eo_cam_rate_word" in k), None)
        if col is None:
            sys.exit(f"no eo_cam_rate_word probe in {f.name}: this bitstream predates the monitor")
        # the first row of these CSVs is a radix marker ("HEX"), not a sample
        v = None
        for r in rows:
            raw = r[col].strip()
            try:
                v = int(raw, 16)
            except ValueError:
                continue
            break
        if v is None or field(v, 63, 62) != 0b10:
            continue
        sel = field(v, 41, 39)
        cams[sel] = (field(v, 38, 31),                       # fps
                     field(v, 30, 16) * US_PER_TICK,          # min period us
                     field(v, 15, 1) * US_PER_TICK)           # max period us
        trig = (field(v, 61, 56), field(v, 55, 42) * US_PER_TICK)

    if not cams:
        sys.exit("no valid samples: is the design running and the probe present?")
    print("EO camera input rate, measured at the camera pins")
    print(f"{'camera':8s} {'fps':>5s} {'period min':>12s} {'period max':>12s} {'spread':>10s}")
    for k in sorted(cams):
        fps, lo, hi = cams[k]
        print(f"cam {k + 1:<4d} {fps:5d} {lo/1000:9.3f} ms {hi/1000:9.3f} ms {hi-lo:8.1f} us")
    if trig:
        print(f"\ntrigger  {trig[0]:5d} Hz   period {trig[1]/1000:.3f} ms")
    missing = [k + 1 for k in range(6) if k not in cams]
    if missing:
        print(f"no sample this run for camera(s): {missing} - run more sweeps")


if __name__ == "__main__":
    main()
