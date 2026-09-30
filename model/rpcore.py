#!/usr/bin/env python3
"""Sensor-generic golden model for the shared roll/pitch renderer (EO + IR).

The EO and IR panoramas never run at the same time, so the RTL shares one
source-driven core (tables, queue, RowWindow) and selects the sensor at run
time.  This model describes both through a Sensor config:

  * geometry: source size, segment ROM layout, per-camera strip widths,
    panorama starts, output width
  * sampling: EO interpolates luma and the per-pixel chroma byte with
    rounding (interp8) and phase-locks x to pano_x parity; IR interpolates
    luma only with the M1 IR renderer's truncating vlerp, chroma is 0x80
  * seams: tail of strip k (tail_start..W_k-1) blended into the head of
    strip k+1 (j < head_len), sample index min(j, tail_len-1), alpha index
    alpha_pos(j).  IR's cam2/cam3 seam straddles the fold: 48 tail pixels,
    90 head pixels, cam2 clamped at lx 639, alpha through cam23_fold_alpha_pos
  * absent cameras: EO blacks a seam whose camera A is absent; IR promotes B

Independent transcriptions of both M1 renderers (render_m1_eo / render_m1_ir)
check the offset renderer at zero offset.

  python model/rpcore.py --selftest
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RR = ROOT / "assets" / "rowruns"
BLACK = 0x1080
SEG = 64
ROWS = 480
NCAM = 6
ANGLE_MAX_CD = 1000


def cam23_fold_alpha_pos(j: int) -> int:
    if j <= 17:
        return 0
    scaled = (j - 17) * 25 + 32
    return min(28, (scaled >> 6) & 0x1F)


@dataclass
class Sensor:
    name: str
    src_w: int
    src_h: int
    rom_file: str
    rom_bits: int                  # 144 (EO) or 96 (IR)
    segs: int
    drun_to_q16: int
    cam_w: list
    cam_start: list
    out_w: int
    pitch_tr: float
    tail_start: list               # per seam k = 0..4, in strip k
    tail_len: list
    head_len: list
    alpha_pos: list                # per seam: function j -> alpha index
    alpha_y_file: str
    alpha_c_file: str | None
    is_ir: bool

    @property
    def strip_base(self):
        b, out = 0, []
        for w in self.cam_w:
            out.append(b)
            b += w
        return out


EO = Sensor(
    name="eo", src_w=1920, src_h=1080, rom_file="eo_v19_render_runs.mem", rom_bits=144,
    segs=11, drun_to_q16=11,
    cam_w=[650, 655, 655, 655, 655, 655],
    cam_start=[0, 633, 1271, 1909, 2547, 3185], out_w=3840, pitch_tr=-9.80,
    tail_start=[633, 638, 638, 638, 638], tail_len=[17] * 5, head_len=[17] * 5,
    alpha_pos=[lambda j: j] * 5,
    alpha_y_file="eo_v19_alpha_y.mem", alpha_c_file="eo_v19_alpha_c.mem", is_ir=False)

IR = Sensor(
    name="ir", src_w=640, src_h=512, rom_file="ir_v19_render_runs.mem", rom_bits=96,
    segs=10, drun_to_q16=12,
    cam_w=[616, 621, 640, 621, 621, 621],
    cam_start=[0, 587, 1179, 1771, 2363, 2955], out_w=3576, pitch_tr=-8.72,
    tail_start=[587, 592, 592, 592, 592], tail_len=[29, 29, 48, 29, 29],
    head_len=[29, 29, 90, 29, 29],
    alpha_pos=[lambda j: j, lambda j: j, cam23_fold_alpha_pos, lambda j: j, lambda j: j],
    alpha_y_file="ir_v19_alpha_y.mem", alpha_c_file=None, is_ir=True)


# ---------------------------------------------------------------------------
def load_rom(s: Sensor):
    def s32(v): return v - (1 << 32) if v & (1 << 31) else v
    def s16(v): return v - (1 << 16) if v & (1 << 15) else v
    recs = [int(l, 16) for l in (RR / s.rom_file).read_text().split()]
    assert len(recs) == ROWS * NCAM * s.segs, len(recs)
    if s.rom_bits == 144:
        pos = dict(ax0=48, ay0=80, dax=112, day=128)
    else:
        pos = dict(ax0=0, ay0=32, dax=64, day=80)
    out = {}
    for k, p in pos.items():
        w = 32 if k in ("ax0", "ay0") else 16
        fn = s32 if w == 32 else s16
        out[k] = np.array([fn((r >> p) & ((1 << w) - 1)) for r in recs], np.int64).reshape(ROWS, NCAM, s.segs)
    return out


def load_alpha(s: Sensor):
    ay = [int(l, 16) for l in (RR / s.alpha_y_file).read_text().split()]
    ac = [int(l, 16) for l in (RR / s.alpha_c_file).read_text().split()] if s.alpha_c_file else None
    return ay, ac


def synthetic_frames(s: Sensor, seed: int = 1) -> np.ndarray:
    y, x = np.mgrid[0:s.src_h, 0:s.src_w].astype(np.int64)
    out = np.empty((NCAM, s.src_h, s.src_w), np.int64)
    for cam in range(NCAM):
        luma = (x * 7 + y * 13 + cam * 41 + ((x * y) >> 6) + (x >> 3) * (y >> 4) * (seed + cam)) & 0xFF
        chroma = (x * 3 + y * 5 + cam * 17 + ((x ^ (y << 1)) >> 2)) & 0xFF
        out[cam] = (luma << 8) | (0x80 if s.is_ir else chroma)
    return out


# ---------------------------------------------------------------------------
def round_half_away(num, den):
    return (num + den // 2) // den if num >= 0 else -((-num + den // 2) // den)


def angle_lut(mag_cd):
    r = math.radians(mag_cd / 100.0)
    return int(math.floor(math.cos(r) * 32768 + 0.5)), int(math.floor(math.sin(r) * 32768 + 0.5))


def y_shift_rows(pitch_cd, tr):
    tr_q16 = int(math.floor(tr * 65536 + 0.5)) if tr >= 0 else -int(math.floor(-tr * 65536 + 0.5))
    return round_half_away(tr_q16 * pitch_cd, 100 * 65536)


def cam_transform(s: Sensor, roll_cd, pitch_cd):
    roll_cd = max(-ANGLE_MAX_CD, min(ANGLE_MAX_CD, roll_cd))
    pitch_cd = max(-ANGLE_MAX_CD, min(ANGLE_MAX_CD, pitch_cd))
    c, smag = angle_lut(abs(roll_cd))
    sn = -smag if roll_cd > 0 else smag if roll_cd < 0 else 0
    return c, sn, y_shift_rows(pitch_cd, s.pitch_tr)


def seg_transform(s: Sensor, rom, cam, c, sn, ysh):
    cx, cy = s.src_w << 15, s.src_h << 15
    dx = rom["ax0"][:, cam, :] - cx
    dy = rom["ay0"][:, cam, :] + (ysh << 16) - cy
    Ax = ((c * dx + sn * dy) >> 15) + cx
    Ay = ((-sn * dx + c * dy) >> 15) + cy
    dax = rom["dax"][:, cam, :] << s.drun_to_q16
    day = rom["day"][:, cam, :] << s.drun_to_q16
    return Ax, Ay, (c * dax + sn * day) >> 15, (-sn * dax + c * day) >> 15


def interp8(a, b, f):
    return ((a * (65536 - f) + b * f + 32768) >> 16) & 0xFF


def vlerp(p0, p1, f):
    return (p0 + (((p1 - p0) * f) >> 16)) & 0xFF


def qx_phase(ax, parity):
    q = np.where(ax < 0, 0, np.where(ax > (1918 << 16), 1918, (ax >> 16) & 0x7FF))
    return np.where(q == 0, parity, np.where(q >= 1918, np.where(parity == 1, 1919, 1918), (q & ~1) | parity))


# ---------------------------------------------------------------------------
# Offset renderer (functional)
# ---------------------------------------------------------------------------
def strips(s: Sensor, rom, frames, roll, pitch):
    out = []
    xmax, ymax = (s.src_w - 2) << 16, (s.src_h - 2) << 16
    for cam in range(NCAM):
        c, sn, ysh = cam_transform(s, roll[cam], pitch[cam])
        Ax, Ay, Dx, Dy = seg_transform(s, rom, cam, c, sn, ysh)
        lx = np.arange(s.cam_w[cam])
        sg, i = lx // SEG, lx % SEG
        ax = Ax[:, sg] + i * Dx[:, sg]
        ay = Ay[:, sg] + i * Dy[:, sg]
        valid = (ax >= 0) & (ax <= xmax) & (ay >= 0) & (ay <= ymax)
        y0 = np.clip(ay >> 16, 0, s.src_h - 2)
        fr = ay & 0xFFFF
        f = frames[cam]
        if s.is_ir:
            x = np.clip(ax >> 16, 0, s.src_w - 2)
            px = (vlerp(f[y0, x] >> 8, f[y0 + 1, x] >> 8, fr) << 8) | 0x80
        else:
            x = qx_phase(ax, (s.cam_start[cam] + lx) & 1)
            p0, p1 = f[y0, x], f[y0 + 1, x]
            px = (interp8(p0 >> 8, p1 >> 8, fr) << 8) | interp8(p0 & 0xFF, p1 & 0xFF, fr)
        out.append(np.where(valid, px, BLACK))
    return out


def compose(s: Sensor, st, present=(1,) * 6):
    ay_tab, ac_tab = load_alpha(s)
    out = np.full((ROWS, s.out_w), BLACK, np.int64)
    for k in range(NCAM):
        lo = 0 if k == 0 else s.cam_start[k] + s.head_len[k - 1]
        hi = s.out_w - 1 if k == NCAM - 1 else s.cam_start[k] + s.tail_start[k] - 1
        if hi >= lo:
            out[:, lo:hi + 1] = st[k][:, lo - s.cam_start[k]:hi - s.cam_start[k] + 1] if present[k] else BLACK
        if k == NCAM - 1:
            break
        for j in range(s.head_len[k]):
            px = s.cam_start[k + 1] + j
            a = st[k][:, s.tail_start[k] + min(j, s.tail_len[k] - 1)]
            b = st[k + 1][:, j]
            ap = s.alpha_pos[k](j)
            if s.is_ir:
                bl = (vlerp(a >> 8, b >> 8, ay_tab[ap]) << 8) | 0x80
            else:
                bl = (interp8(a >> 8, b >> 8, ay_tab[ap]) << 8) | interp8(a & 0xFF, b & 0xFF, ac_tab[7 if ap > 15 else ap >> 1])
            pa, pb = present[k], present[k + 1]
            if pa and pb:
                v = bl
            elif pa:
                v = a
            elif pb and s.is_ir:
                v = b
            else:
                v = np.full(ROWS, BLACK)
            out[:, px] = v
    return out


# Flat magenta as the emitter writes it: one luma, Cb on even output columns
# and Cr on odd ones (4:2:2).
MAGENTA_Y, MAGENTA_CB, MAGENTA_CR = 105, 212, 235


def render_offsets(s, rom, frames, roll, pitch, present=(1,) * 6, mark_ir=False):
    # RpRenderer IR_OFFSET_MARK: while any IR camera carries a roll or pitch
    # offset the whole IR panorama is replaced by a flat magenta error screen.
    # EO is never marked.
    if mark_ir and s.is_ir and (any(roll) or any(pitch)):
        chroma = np.where(np.arange(s.out_w) & 1, MAGENTA_CR, MAGENTA_CB)
        return np.broadcast_to((MAGENTA_Y << 8) | chroma, (ROWS, s.out_w)).copy()
    return compose(s, strips(s, rom, frames, roll, pitch), present)


# ---------------------------------------------------------------------------
# M1 transcriptions
# ---------------------------------------------------------------------------
def render_m1_ir(rom, frames, present=(1,) * 6):
    s = IR
    ay_tab, _ = load_alpha(s)
    C = s.cam_start
    out = np.empty((ROWS, s.out_w), np.int64)

    def sample(sy, cam, lx):
        seg, i = lx >> 6, lx & 63
        cx = rom["ax0"][sy, cam, seg] + ((i * rom["dax"][sy, cam, seg]) << 12)
        cy = rom["ay0"][sy, cam, seg] + ((i * rom["day"][sy, cam, seg]) << 12)
        qx = min(639, max(0, cx >> 16))
        qy = min(510, max(0, cy >> 16))
        f = frames[cam]
        return vlerp(int(f[qy, qx] >> 8), int(f[qy + 1, qx] >> 8), cy & 0xFFFF)

    for sy in range(ROWS):
        for px in range(s.out_w):
            blend = False; apos = 0; cb = lb = 0
            if px < C[1]:
                ca, la = 0, px
            elif px <= 615:
                blend, ca, cb, la, lb, apos = True, 0, 1, px, px - C[1], px - C[1]
            elif px < C[2]:
                ca, la = 1, px - C[1]
            elif px <= 1207:
                blend, ca, cb, la, lb, apos = True, 1, 2, px - C[1], px - C[2], px - C[2]
            elif px < C[3]:
                ca, la = 2, px - C[2]
            elif px <= C[3] + 89:
                blend, ca, cb = True, 2, 3
                la = min(639, px - C[2]); lb = px - C[3]; apos = cam23_fold_alpha_pos(px - C[3])
            elif px < C[4]:
                ca, la = 3, px - C[3]
            elif px <= 2391:
                blend, ca, cb, la, lb, apos = True, 3, 4, px - C[3], px - C[4], px - C[4]
            elif px < C[5]:
                ca, la = 4, px - C[4]
            elif px <= 2983:
                blend, ca, cb, la, lb, apos = True, 4, 5, px - C[4], px - C[5], px - C[5]
            else:
                ca, la = 5, px - C[5]
            pa, pb = present[ca], present[cb]
            black = (not pa) and ((not blend) or (not pb))
            if blend and not pa and pb:
                ca, la = cb, lb
            if black:
                out[sy, px] = BLACK
                continue
            va = sample(sy, ca, la)
            if blend and pa and pb:
                va = vlerp(va, sample(sy, cb, lb), ay_tab[apos])
            out[sy, px] = (va << 8) | 0x80
    return out


# ---------------------------------------------------------------------------
# Tables and walk
# ---------------------------------------------------------------------------
def build_tables(s: Sensor, rom, roll, pitch):
    ents = [seg_transform(s, rom, cam, *cam_transform(s, roll[cam], pitch[cam])) for cam in range(NCAM)]
    ymax, xmax = s.src_h - 2, s.src_w - 2
    params = []
    ylo, yhi, xlo, xhi = 1 << 30, -1, 1 << 30, -1
    for sy in range(ROWS):
        for cam in range(NCAM):
            Ax, Ay, Dx, Dy = ents[cam]
            for sg in range(s.segs):
                ln = min(SEG, s.cam_w[cam] - sg * SEG)
                if ln <= 0:
                    continue
                ax0, ay0, dx, dy = int(Ax[sy, sg]), int(Ay[sy, sg]), int(Dx[sy, sg]), int(Dy[sy, sg])
                last = ln - 1
                d = dy >= 0
                i0 = 0 if d else last
                ax_s, ay_s = ax0 + i0 * dx, ay0 + i0 * dy
                ay_e = ay0 + last * dy if d else ay0
                st = min(ymax, max(0, ay_s >> 16))
                en = min(ymax, max(0, ay_e >> 16))
                for axv in (ax0, ax0 + last * dx):
                    xc = min(xmax, max(0, axv >> 16))
                    xlo, xhi = min(xlo, xc), max(xhi, xc + 1)
                ylo, yhi = min(ylo, st), max(yhi, en)
                params.append(dict(sy=sy, cam=cam, seg=sg, i=i0, dir=int(d), last=last, ax=ax_s, ay=ay_s,
                                   stx=dx if d else -dx, sty=dy if d else -dy, st=st, en=en))
    row_ready = [ylo] * ROWS
    for p in params:
        row_ready[p["sy"]] = max(row_ready[p["sy"]], p["en"])
    order = sorted(range(len(params)), key=lambda k: (params[k]["st"], k))
    counts = np.bincount([p["st"] for p in params], minlength=ymax + 1)
    return dict(params=[params[k] for k in order], bucket_end=np.cumsum(counts), row_ready=row_ready,
                ylo=ylo, yhi=yhi, col_lo=xlo, col_hi=xhi)


def simulate_walk(s: Sensor, tbl, slots=256):
    ylo, yhi = tbl["ylo"], tbl["yhi"]
    ymax, xmax = (s.src_h - 2) << 16, (s.src_w - 2) << 16
    total = sum(s.cam_w)
    taken = np.zeros((ROWS, total), np.int32)
    queue, p_next, sy_out, max_window, visits, errors = [], 0, 0, 0, 0, []
    for y0 in range(ylo, yhi + 1):
        last = y0 == yhi
        work, queue = queue, []
        while p_next < tbl["bucket_end"][y0]:
            work.append(dict(tbl["params"][p_next])); p_next += 1
        for e in work:
            visits += 1
            while True:
                ay = e["ay"]
                if not (last or ay < 0 or (ay >> 16) <= y0):
                    queue.append(e); break
                sx = s.strip_base[e["cam"]] + e["seg"] * SEG + e["i"]
                taken[e["sy"], sx] += 1
                if 0 <= e["ax"] <= xmax and 0 <= ay <= ymax and (ay >> 16) != y0:
                    errors.append(("wrong_row", e["sy"], e["cam"], y0))
                max_window = max(max_window, e["sy"] - sy_out + 1)
                if (e["i"] == e["last"]) if e["dir"] else (e["i"] == 0):
                    break
                e["i"] += 1 if e["dir"] else -1
                e["ax"] += e["stx"]; e["ay"] += e["sty"]
        while sy_out < ROWS and tbl["row_ready"][sy_out] <= y0:
            if (taken[sy_out] != 1).any():
                errors.append(("incomplete", sy_out, y0))
            sy_out += 1
    if sy_out != ROWS or (taken != 1).any():
        errors.append(("not_exactly_once", sy_out, int((taken != 1).sum())))
    return not errors, dict(visits=visits, max_window=max_window, errors=errors[:5])


# ---------------------------------------------------------------------------
def selftest():
    ok = True
    # 1. EO through the generic model == model/golden.py (already bit-exact with M1 and RTL)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import golden as g
    rom_eo = load_rom(EO)
    fr_eo = synthetic_frames(EO)
    for r, p, pres in [([0] * 6, [0] * 6, (1,) * 6),
                       ([150, -300, 1000, -1000, 0, 777], [-1000, 250, 0, 1000, -60, 5], (1, 1, 1, 0, 1, 1))]:
        a = render_offsets(EO, rom_eo, fr_eo, r, p, pres)
        b = g.render_offsets(g.load_rom(), g.synthetic_frames(), r, p, pres)
        n = int((a != b).sum()); ok &= n == 0
        print(f"EO generic vs golden.py {r[:2]}.. present={pres}: {n} mismatches")
    # 2. IR offset renderer at zero == M1 IR transcription
    rom_ir = load_rom(IR)
    fr_ir = synthetic_frames(IR)
    for pres in [(1,) * 6, (1, 1, 0, 1, 1, 1), (1, 1, 1, 0, 1, 1)]:
        a = render_offsets(IR, rom_ir, fr_ir, [0] * 6, [0] * 6, pres)
        b = render_m1_ir(rom_ir, fr_ir, pres)
        n = int((a != b).sum()); ok &= n == 0
        print(f"IR zero offset vs M1 IR transcription, present={pres}: {n} mismatches")
    # 3. walks
    for sname, s, rom in [("eo", EO, rom_eo), ("ir", IR, rom_ir)]:
        for label, r, p in [("zero", [0] * 6, [0] * 6), ("roll10", [1000] * 6, [0] * 6),
                            ("alt10", [1000, -1000] * 3, [1000, -1000] * 3),
                            ("mixed", [150, -300, 1000, -1000, 0, 777], [-1000, 250, 0, 1000, -60, 5])]:
            t = build_tables(s, rom, r, p)
            good, st = simulate_walk(s, t)
            ok &= good
            print(f"walk {sname} {label:7s} ok={good} Y={t['ylo']}..{t['yhi']} cols={t['col_lo']}..{t['col_hi']} {st}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    if ap.parse_args().selftest:
        sys.exit(0 if selftest() else 1)
