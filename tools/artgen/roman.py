"""Roman architecture for big voxel models (rome.md §3.1), reusable by any set with Roman
building: the Tuscan, Ionic, Corinthian and Composite orders (free-standing, engaged and as
pilasters), Roman entablatures with dentils and modillions, inscriptions as texture, brick-faced
concrete, travertine and tufa ashlar, painted stucco, arched openings and arcades, façades
running round ellipses and circles in arcaded storeys (amphitheatres, theatres, the circus's
curved end, hemicycles), domes with step rings, coffers and an oculus, barrel and groin vault
roofs, temples on high podiums with frontal stairs, round temples, basilicas with clerestories,
porticoes, triumphal arches, honorific columns with a spiral relief band and obelisks.

Units and axes follow `arch` (design units in grid axes: +x south, +y west, z up; faces named
by their outward normal; `s` runs along a face left to right seen from outside); an `ROrder`
is written in metres and drawn at a landmark `Scale`. Everything draws through `arch.fill`, so
a builder can call it for the whole building on any chunk (`bigrender`).
"""

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import greek
import materials as M
import relief as R
from arch import FACES, Scale, carve, ellipsoid, face_box, face_frame, face_length, fill, halo, revolve, rod, slab
from voxel import hash01, value_noise

LAMP = (255, 201, 92)


def _i(a):
    return np.floor(a).astype(np.int64)


# ---------------------------------------------------------------- local frames

def local_box(front, box, u0, u1, v0, v1):
    """A box given in a building's own frame (u from the back toward `front`, v across, both
    from the box's corner) as grid coordinates."""
    x0, x1, y0, y1 = box[:4]
    if front == "+x":
        return (x0 + u0, x0 + u1, y0 + v0, y0 + v1)
    if front == "-x":
        return (x1 - u1, x1 - u0, y0 + v0, y0 + v1)
    if front == "+y":
        return (x0 + v0, x0 + v1, y0 + u0, y0 + u1)
    return (x0 + v0, x0 + v1, y1 - u1, y1 - u0)


def local_pt(front, box, u, v):
    b = local_box(front, box, u, u, v, v)
    return b[0], b[2]


def depth_len(front, box):
    x0, x1, y0, y1 = box[:4]
    return ((x1 - x0), (y1 - y0)) if front in ("+x", "-x") else ((y1 - y0), (x1 - x0))


def side_faces(front):
    """The faces to the left and right of a front (seen from outside it) and the back face."""
    return {"+x": ("+y", "-y", "-x"), "-x": ("-y", "+y", "+x"), "+y": ("-x", "+x", "-y"),
            "-y": ("+x", "-x", "+y")}[front]


# ---------------------------------------------------------------- textures

def brick(seed=5, course=0.85, bond=14.0, spread=0.45):
    """Opus testaceum: thin red-orange bricks in courses with pale mortar, each brick its own
    tone, a bonding course of big pale tiles (bipedales) every `bond` units of height, a
    little soot and rain-darkening low on the wall."""
    def tone(X, Y, Z):
        along = X + Y
        row = _i(Z / course)
        a = along + (row % 2) * 1.3
        mortar = (Z % course) < 0.3
        h = hash01(row, _i(a / 2.6), seed)
        t = (h - 0.5) * spread + 0.75 * mortar - 0.35 * ((a % 2.6) < 0.25)
        band = (Z % bond) < 0.9
        t = t + np.where(band, 0.45 + 0.25 * (hash01(_i(a / 6.0), row, seed, 3) - 0.5), 0.0)
        return t + (value_noise(along * 0.5, Z * 0.3, X * 0, 9.0, seed + 7) - 0.5) * 0.5
    return tone


def travertine(course=3.2, block=8.0, seed=3, holes=0.06):
    """Travertine ashlar: warm cream blocks, joints, and the stone's small dark holes."""
    base = M.ashlar(course, block, seed, joint=0.3, spread=0.5, odd=0.1)

    def tone(X, Y, Z):
        pit = hash01(_i((X + Y) * 2.2), _i(Z * 2.2), _i((X - Y) * 2.2), seed, 13) < holes
        return base(X, Y, Z) - 0.9 * pit
    return tone


def stucco(seed=7, amount=0.35):
    """Lime stucco over brick: smooth, a few patches and a darker splash band near the foot."""
    def tone(X, Y, Z):
        n = value_noise((X + Y) * 0.5, (X - Y) * 0.5, Z * 0.5, 8.0, seed) - 0.5
        return n * amount - 0.35 * (Z < 2.0)
    return tone


def marble_veneer(seed=9, slab_w=6.0, slab_h=5.0):
    """Marble revetment plates in a grid with fine joints and a soft vein noise."""
    def tone(X, Y, Z):
        a = X + Y
        jn = ((a % slab_w) < 0.25) | ((Z % slab_h) < 0.25)
        h = hash01(_i(a / slab_w), _i(Z / slab_h), seed)
        vein = np.abs(value_noise(a * 0.8, Z * 0.8, X * 0, 3.0, seed + 1) - 0.5) < 0.03
        return (h - 0.5) * 0.35 - 0.7 * jn - 0.5 * vein + 0.1
    return tone


def inscription(m, face, wall, s0, s1, z0, z1, material="gold", rows=1, seed=1):
    """Letters as texture on a face (too small to read): rows of capitals in gilded bronze or
    red paint, words with gaps, inset into the surface."""
    x0, x1, y0, y1 = wall[:4]
    rh = (z1 - z0) / rows

    def mask(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        row = _i((Z - z0) / rh)
        v = ((Z - z0) % rh) / rh
        col = _i((s - s0) * 2.0)           # one voxel column per letter stroke at k = 2
        letter = col // 3
        stroke = col % 3
        word = hash01(letter // 5, row, seed) < 0.18
        h = hash01(letter, row, seed, 2)
        shape = np.where(stroke == 1, h < 0.55, h < 0.85)
        return (v > 0.15) & (v < 0.85) & (stroke < 2) & shape & ~word
    fill(m, face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -0.05, 0.45), material, mask, tone=0.3, only_solid=True)


def numerals(m, face, wall, s0, s1, z0, z1, material="cinnabar", seed=2):
    """Painted entrance numerals over an arch (Colosseum): a short group of strokes."""
    x0, x1, y0, y1 = wall[:4]
    mid = (s0 + s1) / 2

    def mask(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        col = _i((s - mid) * 2.0)
        return (np.abs(col) <= 2) & (col % 2 == 0)
    fill(m, face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -0.05, 0.4), material, mask, tone=0.1, only_solid=True)


# ---------------------------------------------------------------- the orders

@dataclass(frozen=True)
class ROrder:
    """A Roman column order in metres. `kind`: tuscan, ionic, corinthian, composite. `shaft`
    and `trim` are the materials of the shaft and of the base and capital (coloured marble
    or granite shafts with white marble capitals were the imperial habit); `gilt` gilds the
    leaf tips and volutes."""
    kind: str = "corinthian"
    D: float = 1.48
    H: float = 14.15
    shaft: str = "marble"
    trim: str = "marble"
    fluted: bool = True
    gilt: bool = False

    def r(self, S: Scale):
        return S.h(self.D) / 2

    def entablature(self, S: Scale):
        return S.v(self.H * (0.22 if self.kind == "tuscan" else 0.24))


def _base(m, cx, cy, z0, r0, h, mat, tuscan=False):
    """An Attic base (plinth, torus, scotia, torus) or the Tuscan plinth and torus."""
    p = r0 * 1.42
    slab(m, cx - p, cx + p, cy - p, cy + p, z0, z0 + h * 0.32, mat, tone=lambda X, Y, Z: 0.2 * (Z > z0 + h * 0.25))
    if tuscan:
        revolve(m, cx, cy, z0 + h * 0.32, z0 + h, lambda t: r0 * (1.3 - 0.25 * t ** 2), mat, tone=0.15)
        return z0 + h
    revolve(m, cx, cy, z0 + h * 0.32, z0 + h * 0.58, lambda t: r0 * (1.25 + 0.1 * np.sin(np.pi * t)), mat, tone=0.15)
    revolve(m, cx, cy, z0 + h * 0.58, z0 + h * 0.76, lambda t: r0 * 1.08, mat, tone=-0.5)
    revolve(m, cx, cy, z0 + h * 0.76, z0 + h, lambda t: r0 * (1.12 + 0.08 * np.sin(np.pi * t)), mat, tone=0.25)
    return z0 + h


def _shaft(m, cx, cy, z0, z1, r0, mat, fluted, seed=0, upper=0.86):
    nfl = 24

    def radius(t):
        return r0 * (1 - (1 - upper) * t) + r0 * 0.03 * np.sin(np.pi * np.clip(t / 0.85, 0, 1))

    def mask(X, Y, Z):
        t = np.clip((Z - z0) / max(z1 - z0, 1e-3), 0, 1)
        rr = np.hypot(X - cx, Y - cy)
        lim = radius(t)
        if fluted and m.fine:
            f = (np.arctan2(Y - cy, X - cx) * nfl / (2 * np.pi)) % 1.0
            lim = lim - 0.24 * (1 - (2 * f - 1) ** 2) * (t > 0.33)     # flutes above a cabled third
        return rr <= lim

    def nrm(X, Y, Z):
        a = np.arctan2(Y - cy, X - cx)
        if not fluted:
            return (np.cos(a), np.sin(a), Z * 0.0)
        f = (a * nfl / (2 * np.pi)) % 1.0
        tilt = (f - 0.5) * 1.2
        return (np.cos(a - tilt), np.sin(a - tilt), Z * 0.0)

    def tone(X, Y, Z):
        n = (value_noise(X * 1.5, Y * 1.5, Z * 0.4, 4.0, seed + 3) - 0.5) * 0.35
        if fluted:
            f = (np.arctan2(Y - cy, X - cx) * nfl / (2 * np.pi)) % 1.0
            n = n + 0.3 * (f < 0.1)
        return n
    fill(m, (cx - r0 * 1.05, cx + r0 * 1.05, cy - r0 * 1.05, cy + r0 * 1.05, z0, z1), mat, mask, tone, nrm)
    return radius(1.0)


def _corinthian(m, cx, cy, z0, h, rt, mat, gilt, composite=False):
    """Two rows of acanthus leaves round a bell, their tips curling out, corner volutes
    (big Ionic ones on the Composite) and a concave abacus with a flower on each side."""
    zb = z0 + h * 0.84

    def leaves(X, Y, Z):
        t = np.clip((Z - z0) / (zb - z0), 0, 1)
        a = np.arctan2(Y - cy, X - cx)
        rr = np.hypot(X - cx, Y - cy)
        bell = rt * (1.0 + 0.32 * t)
        out = np.zeros_like(rr + t)
        for row, (lo, hi, ph, L) in enumerate(((0.0, 0.5, 0.0, 0.55), (0.28, 0.82, np.pi / 8, 0.75))):
            u = np.clip((t - lo) / (hi - lo), 0, 1)
            inrow = (t >= lo) & (t <= hi)
            lobe = np.clip(np.cos((a - ph) * 8), 0, 1) ** 0.6
            curl = np.where(u > 0.7, (u - 0.7) * 2.2, 0.0)      # tips turning outward
            out = np.maximum(out, np.where(inrow, rt * L * lobe * (0.45 + 0.4 * u + curl), 0.0))
        return rr <= bell + out * 0.6

    def ltone(X, Y, Z):
        a = np.arctan2(Y - cy, X - cx)
        rib = np.cos(a * 16) > 0.7
        t = (Z - z0) / (zb - z0)
        return 0.35 - 0.6 * rib + 0.3 * ((t % 0.5) > 0.4)
    R_ = rt * 1.8
    fill(m, (cx - R_, cx + R_, cy - R_, cy + R_, z0, zb), mat, leaves, ltone,
         lambda X, Y, Z: (X - cx, Y - cy, (Z - z0) * 0.25))
    if gilt:
        fill(m, (cx - R_, cx + R_, cy - R_, cy + R_, z0 + h * 0.3, zb), "gold",
             lambda X, Y, Z: np.hypot(X - cx, Y - cy) > rt * 1.25, tone=0.2, only_solid=True)
    # Volutes under the abacus corners.
    vr = rt * (0.42 if composite else 0.3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            vx, vy = cx + sx * rt * 0.98, cy + sy * rt * 0.98
            ellipsoid(m, (vx, vy, zb - vr * 0.6), (vr, vr, vr * 1.1), "gold" if gilt else mat, tone=0.3)
    if composite:     # the egg-and-dart echinus under the volutes
        revolve(m, cx, cy, zb - h * 0.22, zb - h * 0.08, lambda t: rt * (1.22 + 0.06 * np.sin(np.pi * t)), mat,
                tone=lambda X, Y, Z: 0.4 * (np.cos(np.arctan2(Y - cy, X - cx) * 14) > 0.3) - 0.3)
    # The abacus, its sides curving in, a flower on each.
    ab = rt * 1.55

    def abacus(X, Y, Z):
        u, v = np.abs(X - cx), np.abs(Y - cy)
        return (u <= ab - 0.18 * ab * (1 - (v / ab) ** 2)) & (v <= ab - 0.18 * ab * (1 - (u / ab) ** 2))
    fill(m, (cx - ab, cx + ab, cy - ab, cy + ab, zb, z0 + h), mat, abacus,
         tone=lambda X, Y, Z: 0.3 * (Z > z0 + h - 0.5))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ellipsoid(m, (cx + dx * ab * 0.86, cy + dy * ab * 0.86, zb + (z0 + h - zb) * 0.5), (0.45, 0.45, 0.45),
                  "gold" if gilt else mat, tone=0.4)


def column(m, cx, cy, z0, o: ROrder, S: Scale, seed=0, height=None):
    """One column standing at (cx, cy) on z0; returns the top of its capital. `height`
    overrides the order's (stacked storeys, stretched or shortened shafts)."""
    H = height if height is not None else S.v(o.H)
    r0 = o.r(S)
    if o.kind == "ionic":
        go = greek.Order(kind="ionic", D=o.D, H=H / S.v(1.0), upper=0.86, flutes=24, material=o.trim)
        greek.column(m, cx, cy, z0, go, S, paint=False)
        if o.shaft != o.trim:      # a coloured shaft between white base and capital
            bh = S.v(o.D * 0.5)
            _shaft(m, cx, cy, z0 + bh, z0 + H - S.v(o.D * 0.36), r0 * 0.98, o.shaft, False, seed)
        return z0 + H
    tuscan = o.kind == "tuscan"
    bh = S.v(o.D * 0.5)
    cap_h = S.v(o.D * (0.5 if tuscan else 1.15))
    zs = _base(m, cx, cy, z0, r0, bh, o.trim, tuscan)
    rt = _shaft(m, cx, cy, zs, z0 + H - cap_h, r0, o.shaft, o.fluted and not tuscan, seed)
    zc = z0 + H - cap_h
    if tuscan:
        revolve(m, cx, cy, zc, zc + cap_h * 0.55, lambda t: rt * (1.05 + 0.3 * np.sin(t * np.pi / 2)), o.trim, tone=0.1)
        ab = rt * 1.4
        slab(m, cx - ab, cx + ab, cy - ab, cy + ab, zc + cap_h * 0.55, z0 + H, o.trim,
             tone=lambda X, Y, Z: 0.3 * (Z > z0 + H - 0.5))
    else:
        _corinthian(m, cx, cy, zc, cap_h, rt, o.trim, o.gilt, composite=o.kind == "composite")
    return z0 + H


def engaged(m, face, wall, s, z0, o: ROrder, S: Scale, height=None, seed=0):
    """A half column standing against `face` of the wall box at `s` along it (its axis on the
    wall surface, the back half buried in the wall)."""
    x0, x1, y0, y1 = wall[:4]
    cx, cy = {"+x": (x1, y1 - s), "-x": (x0, y0 + s), "+y": (x0 + s, y1), "-y": (x1 - s, y0)}[face]
    return column(m, cx, cy, z0, o, S, seed, height)


def pilaster(m, face, wall, s, z0, z1, w, o: ROrder, out=0.6):
    """A flat pilaster on a face: base, shaft, a capital band (leaf rows on Corinthian)."""
    x0, x1, y0, y1 = wall[:4]
    bh = min(1.6, (z1 - z0) * 0.08)
    ch = min(3.0, (z1 - z0) * 0.12)
    fill(m, face_box(face, x0, x1, y0, y1, z0, z0 + bh, s - w / 2 - 0.4, s + w / 2 + 0.4, -out - 0.3, 0.1), o.trim,
         tone=0.2)
    fill(m, face_box(face, x0, x1, y0, y1, z0 + bh, z1 - ch, s - w / 2, s + w / 2, -out, 0.1), o.shaft,
         tone=lambda X, Y, Z: -0.2 * (np.abs(face_frame(face, X, Y, Z, x0, x1, y0, y1)[0] - s) < w * 0.15))
    fill(m, face_box(face, x0, x1, y0, y1, z1 - ch, z1, s - w / 2 - 0.5, s + w / 2 + 0.5, -out - 0.4, 0.1), o.trim,
         tone=lambda X, Y, Z: 0.35 * (((Z - (z1 - ch)) % 1.2) > 0.7) - 0.15)


# ---------------------------------------------------------------- entablature and cornices

def entablature(m, box, z, h, faces=FACES, material="marble", frieze="plain", frieze_mat=None, seed=0,
                inscribe=(), gilt=False, modillions=True):
    """A Roman entablature round (or along `faces` of) the box from z up `h`: a three-fascia
    architrave, the frieze (plain, `garland` with bucrania, or a material band), and a cornice
    of bed moulding, dentils, modillions, corona and sima projecting about h/3. `inscribe`
    lists faces whose frieze carries a gilded inscription. Returns the top."""
    x0, x1, y0, y1 = box[:4]
    a_h, f_h = h * 0.34, h * 0.3
    c_h = h - a_h - f_h
    out = max(1.0, h * 0.35)

    def grow(b, d, sides=faces):
        bx0, bx1, by0, by1 = b
        return (bx0 - d * ("-x" in sides), bx1 + d * ("+x" in sides), by0 - d * ("-y" in sides),
                by1 + d * ("+y" in sides))
    for i in range(3):            # fascias stepping out
        zz = z + a_h * i / 3
        slab(m, *grow(box, 0.12 * i), zz, zz + a_h / 3, material,
             tone=lambda X, Y, Z, zz=zz: 0.3 * (Z > zz + a_h / 3 - 0.45) - 0.05)
    zf = z + a_h
    slab(m, *box, zf, zf + f_h, frieze_mat or material, tone=0.05)
    for face in faces:
        if frieze == "garland":
            _garlands(m, face, box, zf, zf + f_h, material, seed)
        if face in inscribe:
            L = face_length(face, *box)
            inscription(m, face, box, L * 0.12, L * 0.88, zf + f_h * 0.2, zf + f_h * 0.8, "gold", seed=seed)
    zc = zf + f_h
    parts = ((0.14, 0.2, 0.15), (0.22, 0.45, 0.0), (0.24, 0.7, 0.0), (0.22, 1.0, 0.3), (0.18, 1.08, 0.4))
    for i, (frac, o_, tn) in enumerate(parts):
        zz = zc + c_h * sum(p[0] for p in parts[:i])
        hh = c_h * frac
        b = grow(box, out * o_)
        if i == 1:      # dentils
            fill(m, (*b, zz, zz + hh), material, _teeth(box, faces, 1.0, 0.5, out * o_), tone=0.15)
            slab(m, *grow(box, out * 0.25), zz, zz + hh, material, tone=-0.2)
        elif i == 2 and modillions:    # modillions: brackets under the corona
            fill(m, (*b, zz, zz + hh), material, _teeth(box, faces, 2.8, 1.0, out * o_), tone=0.25)
            slab(m, *grow(box, out * 0.45), zz, zz + hh, material, tone=-0.35)
        else:
            slab(m, *b, zz, zz + hh, material, tone=lambda X, Y, Z, zz=zz, hh=hh, tn=tn: tn + 0.35 * (Z > zz + hh - 0.5))
    if gilt:
        greek.paint_ring(m, grow(box, out * 1.08), zc + c_h * 0.82, zc + c_h, "beads", ["gold", material], out=0.3,
                         deep=0.4, sides=faces)
    return zc + c_h


def _teeth(box, faces, period, width, out):
    """A mask of blocks every `period` along the faces, `width` long, standing out `out`."""
    x0, x1, y0, y1 = box[:4]

    def mask(X, Y, Z):
        ok = np.zeros(np.broadcast(X, Y, Z).shape, bool)
        inside_x = (X >= x0) & (X < x1)
        inside_y = (Y >= y0) & (Y < y1)
        for f in faces:
            if f == "+x":
                sel = (X >= x1) & (X < x1 + out) & inside_y & ((Y % period) < width)
            elif f == "-x":
                sel = (X < x0) & (X >= x0 - out) & inside_y & ((Y % period) < width)
            elif f == "+y":
                sel = (Y >= y1) & (Y < y1 + out) & inside_x & ((X % period) < width)
            else:
                sel = (Y < y0) & (Y >= y0 - out) & inside_x & ((X % period) < width)
            ok = ok | sel
        return ok | (inside_x & inside_y)
    return mask


def _garlands(m, face, box, z0, z1, material, seed):
    """Garlands swinging between ox skulls on a frieze, in relief."""
    x0, x1, y0, y1 = box[:4]
    h = z1 - z0
    period = h * 3.2

    def mask(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = (s % period) / period
        sag = z1 - h * 0.25 - h * 0.45 * np.sin(np.pi * u)
        garland = np.abs(Z - sag) < h * 0.14
        skull = (np.abs(u - 0.0) < 0.06) | (np.abs(u - 1.0) < 0.06)
        skull = skull & (Z > z0 + h * 0.3) & (Z < z1 - h * 0.1)
        return (garland | skull) & (d < 0) & (d > -0.5)
    fill(m, face_box(face, x0, x1, y0, y1, z0, z1, 0, face_length(face, x0, x1, y0, y1), -0.5, 0.0), material, mask,
         tone=0.35)


def cornice(m, box, z, h, out, material="marble", faces=FACES):
    """A simple moulded crown: a cyma over a corona."""
    x0, x1, y0, y1 = box[:4]
    for i, (fr, o_) in enumerate(((0.4, 0.4), (0.6, 1.0))):
        zz = z + h * (0.0 if i == 0 else 0.4)
        d = out * o_
        slab(m, x0 - d * ("-x" in faces), x1 + d * ("+x" in faces), y0 - d * ("-y" in faces), y1 + d * ("+y" in faces),
             zz, zz + h * fr, material, tone=lambda X, Y, Z, zz=zz, fr=fr: 0.35 * (Z > zz + h * fr - 0.5) - 0.1)
    return z + h


# ---------------------------------------------------------------- walls and openings

def wall(m, box, z0, z1, kind="brick", seed=1, material=None):
    """A wall slab faced as `kind`: brick (opus testaceum), travertine, tufa, stucco
    (painted: material gives the colour), veneer (marble plates; material the marble)."""
    x0, x1, y0, y1 = box[:4]
    if kind == "brick":
        slab(m, x0, x1, y0, y1, z0, z1, material or "brick", tone=brick(seed))
    elif kind == "travertine":
        slab(m, x0, x1, y0, y1, z0, z1, material or "travertine", tone=travertine(seed=seed))
    elif kind == "tufa":
        slab(m, x0, x1, y0, y1, z0, z1, material or "tufa", tone=M.ashlar(2.4, 4.5, seed, joint=0.3, spread=0.7))
    elif kind == "stucco":
        slab(m, x0, x1, y0, y1, z0, z1, material or "whitewash", tone=stucco(seed))
    elif kind == "veneer":
        slab(m, x0, x1, y0, y1, z0, z1, material or "marble", tone=marble_veneer(seed))
    elif kind == "marble":
        slab(m, x0, x1, y0, y1, z0, z1, material or "marble",
             tone=M.plus(M.ashlar(2.6, 7.0, seed, joint=0.2, spread=0.25, odd=0.05),
                         lambda X, Y, Z: -0.2 * np.clip(1 - (Z - z0) / 30.0, 0, 1)))
    else:
        raise KeyError(kind)


def arch_mask(s, z, s0, w, z0, spring):
    """Inside an arched opening of width w starting at s0 on the face, from z0, springing at
    `spring` (semicircular head)."""
    c = s0 + w / 2
    r = w / 2
    return (np.abs(s - c) < r) & (z >= z0) & ((z < spring) | ((s - c) ** 2 + (z - spring) ** 2 < r * r))


def opening(m, face, wall_box, s0, w, z0, spring, depth, frame=None, frame_w=None, through=True, back=None,
            keystone=True):
    """An arched opening in a face: carved `depth` deep (or through the wall); `frame` draws a
    ring of voussoirs proud of the face with radial joints and a keystone; `back` fills the
    back of a blind opening (a niche) with that material."""
    x0, x1, y0, y1 = wall_box[:4]
    r = w / 2
    c = s0 + r
    top = spring + r
    box = face_box(face, x0, x1, y0, y1, z0, top + 0.1, s0, s0 + w, -0.1, depth)
    carve(m, box, lambda X, Y, Z: arch_mask(face_frame(face, X, Y, Z, x0, x1, y0, y1)[0], Z, s0, w, z0, spring))
    if back:
        fill(m, face_box(face, x0, x1, y0, y1, z0, top, s0, s0 + w, depth - 0.6, depth), back,
             lambda X, Y, Z: arch_mask(face_frame(face, X, Y, Z, x0, x1, y0, y1)[0], Z, s0, w, z0, spring), tone=-0.3)
    if frame:
        fw = frame_w or max(0.8, w * 0.12)

        def ring(X, Y, Z):
            s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            rr = np.hypot(s - c, Z - spring)
            return (Z >= spring) & (rr >= r) & (rr < r + fw) & (d > -0.35) & (d < 0.3)

        def jt(X, Y, Z):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            a = np.arctan2(Z - spring, s - c)
            k = (a * 9 / np.pi) % 1.0
            return 0.25 - 0.8 * (k < 0.12)
        fill(m, face_box(face, x0, x1, y0, y1, spring, top + fw, s0 - fw, s0 + w + fw, -0.35, 0.3), frame, ring, jt)
        if keystone:
            fill(m, face_box(face, x0, x1, y0, y1, top - 0.3, top + fw + 0.5, c - 0.6, c + 0.6, -0.55, 0.3), frame,
                 tone=0.4)


def window(m, face, wall_box, s0, w, z0, h, arched=False, shutter=None, lit=None, depth=0.9, glass=False):
    """A window: a dark reveal (glazed or open), square or arched, with wooden shutters folded
    back and an optional night glow."""
    x0, x1, y0, y1 = wall_box[:4]
    mat = "glass" if glass else "ink"
    if arched:
        fill(m, face_box(face, x0, x1, y0, y1, z0, z0 + h + w / 2, s0, s0 + w, -0.05, depth), mat,
             lambda X, Y, Z: arch_mask(face_frame(face, X, Y, Z, x0, x1, y0, y1)[0], Z, s0, w, z0, z0 + h), tone=0.0)
    else:
        fill(m, face_box(face, x0, x1, y0, y1, z0, z0 + h, s0, s0 + w, -0.05, depth), mat, tone=0.0)
    if shutter:
        for a, b in ((s0 - w * 0.5, s0), (s0 + w, s0 + w * 1.5)):
            fill(m, face_box(face, x0, x1, y0, y1, z0, z0 + h, a, b, -0.45, 0.0), shutter,
                 tone=lambda X, Y, Z: -0.4 * ((Z % 1.0) < 0.3))
    if lit:
        cx, cy = _face_point(face, wall_box, s0 + w / 2)
        halo(m, cx, cy, z0 + h * 0.5, max(3.0, w * 1.6), LAMP, lit)


def _face_point(face, box, s, d=0.0):
    x0, x1, y0, y1 = box[:4]
    return {"+x": (x1 - d, y1 - s), "-x": (x0 + d, y0 + s), "+y": (x0 + s, y1 - d), "-y": (x1 - s, y0 + d)}[face]


def face_point(face, box, s, d=0.0):
    return _face_point(face, box, s, d)


# ---------------------------------------------------------------- roofs, vaults and domes

def gable(m, box, z, rise, axis, material="terracotta", seed=1, antefixes=False):
    """A tegula-and-imbrex roof: flat pans with half-round cover tiles (greek.tiled_roof)."""
    x0, x1, y0, y1 = box[:4]
    greek.tiled_roof(m, x0, x1, y0, y1, z, rise, axis=axis, material=material, kind="corinthian", seed=seed,
                     antefixes=antefixes, antefix_paint=("terracotta",), pitch=2.4, course=3.0)
    # Gable ends closed with a wall.
    along_y = axis == "y"
    a0, a1 = (x0, x1) if along_y else (y0, y1)
    half = (a1 - a0) / 2
    c = a0 + half
    inner = (x0 + 0.5, x1 - 0.5, y0 + 0.5, y1 - 0.5)
    fill(m, (*inner, z - 0.5, z + rise), "brick",
         lambda X, Y, Z: Z < z + rise * (1 - np.abs((X if along_y else Y) - c) / half) - 1.6, tone=-0.2)


def hip(m, box, z, rise, material="terracotta", seed=1):
    x0, x1, y0, y1 = box[:4]
    greek.hip_roof(m, x0, x1, y0, y1, z, rise, material=material, seed=seed, apex=0.0 if abs((x1 - x0) - (y1 - y0)) < 1
                   else min(0.9, abs((x1 - x0) - (y1 - y0)) / max(x1 - x0, y1 - y0)))


def lean_to(m, box, z_low, z_high, up, material="terracotta", seed=1):
    """A single-pitch tiled roof rising toward the face `up` (aisles, porticoes)."""
    x0, x1, y0, y1 = box[:4]
    along_x = up in ("+x", "-x")
    lo, hi = (x0, x1) if along_x else (y0, y1)
    sgn = 1 if up[0] == "+" else -1

    def frac(X, Y):
        a = X if along_x else Y
        f = (a - lo) / (hi - lo)
        return f if sgn > 0 else 1 - f

    def surf(X, Y):
        return z_low + (z_high - z_low) * np.clip(frac(X, Y), 0, 1)

    def tone(X, Y, Z):
        a = (Y if along_x else X)
        u = (a % 2.4) - 1.2
        f = frac(X, Y) * (hi - lo)
        cover = np.abs(u) < 0.5
        return 0.3 * cover - 0.5 * ((f % 3.0) < 0.4) + (hash01(_i(a / 2.4), _i(f / 3.0), seed) - 0.5) * 0.5

    def mask(X, Y, Z):
        a = (Y if along_x else X)
        u = (a % 2.4) - 1.2
        bump = 0.5 * np.sqrt(np.clip(1 - (u / 0.6) ** 2, 0, 1))
        s = surf(X, Y)
        return (Z < s + bump) & (Z >= s - 1.5)
    slope = (z_high - z_low) / (hi - lo)
    nx = (-sgn * slope, 0.0, 1.0) if along_x else (0.0, -sgn * slope, 1.0)
    fill(m, (x0, x1, y0, y1, z_low - 1.5, z_high + 1.0), material, mask, tone,
         lambda X, Y, Z: (nx[0] + X * 0, nx[1] + Y * 0, nx[2] + Z * 0))


def vault_roof(m, box, z, axis, material="whitewash", thick=1.6, tiles=False, seed=1):
    """The outside of a barrel vault: a half-round roof along `axis` (concrete covered with
    stucco or with tiles in rows along the curve)."""
    x0, x1, y0, y1 = box[:4]
    along_y = axis == "y"
    a0, a1 = (x0, x1) if along_y else (y0, y1)
    r = (a1 - a0) / 2
    c = a0 + r

    def mask(X, Y, Z):
        a = (X if along_y else Y) - c
        rr = np.hypot(a, Z - z)
        return (rr <= r) & (rr > r - thick) & (Z >= z)

    def tone(X, Y, Z):
        if not tiles:
            return (value_noise(X, Y, Z, 6.0, seed) - 0.5) * 0.4
        along = Y if along_y else X
        ang = np.arctan2(Z - z, (X if along_y else Y) - c)
        return 0.3 * ((along % 2.4) < 0.8) - 0.5 * (((ang * r) % 3.0) < 0.4)
    fill(m, (*box[:4], z, z + r + 0.5), material, mask, tone,
         lambda X, Y, Z: (((X - c) if along_y else 0 * X), (0 * Y if along_y else (Y - c)), Z - z))


def groin_roof(m, box, z, material="whitewash", thick=1.6, seed=1):
    """A cross vault seen from outside: two barrels crossing over a square bay."""
    x0, x1, y0, y1 = box[:4]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2

    def mask(X, Y, Z):
        h1 = z + np.sqrt(np.clip(1 - ((X - cx) / rx) ** 2, 0, 1)) * min(rx, ry)
        h2 = z + np.sqrt(np.clip(1 - ((Y - cy) / ry) ** 2, 0, 1)) * min(rx, ry)
        top = np.maximum(h1, h2)
        return (Z < top) & (Z >= top - thick) & (Z >= z)
    fill(m, (*box[:4], z, z + min(rx, ry) + 0.5), material, mask,
         lambda X, Y, Z: (value_noise(X, Y, Z, 6.0, seed) - 0.5) * 0.4)


def dome(m, cx, cy, z0, r, material="gold", rise=None, thick=3.0, steps=0, step_h=None, step_mat="brick",
         oculus=0.0, inner="tufa", coffers=True, tiles=True, seed=1):
    """A dome on a drum top at z0: outer radius r, height `rise` (a hemisphere by default),
    hollow `thick` deep; `steps` concentric step rings round its foot (the Pantheon's seven),
    gilded bronze or lead tiles in courses and ribs, an `oculus` of that radius open to the
    sky with a bronze cornice, and coffers on the inner face (seen through the oculus)."""
    rise = rise or r
    step_h = step_h or rise * 0.045

    def outer(X, Y, Z):
        return ((X - cx) / r) ** 2 + ((Y - cy) / r) ** 2 + ((Z - z0) / rise) ** 2

    def inner_f(X, Y, Z):
        return ((X - cx) / (r - thick)) ** 2 + ((Y - cy) / (r - thick)) ** 2 + ((Z - z0) / (rise - thick)) ** 2

    def tone(X, Y, Z):
        if not tiles:
            return (value_noise(X, Y, Z, 5.0, seed) - 0.5) * 0.3
        a = np.arctan2(Y - cy, X - cx)
        lat = np.arcsin(np.clip((Z - z0) / rise, 0, 1))
        rib = ((a * 28 / (2 * np.pi)) % 1.0) < 0.12
        course = ((lat * rise) % 2.6) < 0.45
        h = hash01(_i(a * 40), _i(lat * rise / 2.6), seed)
        return (h - 0.5) * 0.45 - 0.45 * course + 0.35 * rib

    box = (cx - r, cx + r, cy - r, cy + r, z0, z0 + rise + 0.5)
    fill(m, box, material, lambda X, Y, Z: (outer(X, Y, Z) <= 1) & (inner_f(X, Y, Z) > 1) & (Z >= z0), tone,
         lambda X, Y, Z: ((X - cx) / r ** 2, (Y - cy) / r ** 2, (Z - z0) / rise ** 2))
    if coffers:       # five rows of coffers on the inner face, a smooth band above
        def cof(X, Y, Z):
            a = np.arctan2(Y - cy, X - cx)
            lat = np.arcsin(np.clip((Z - z0) / max(rise - thick, 1), 0, 1))
            row = lat / (np.pi / 2) * 9
            sunk = (((a * 28 / (2 * np.pi)) % 1.0) > 0.2) & ((row % 1.0) > 0.25) & (row < 5)
            return 0.35 - 1.0 * sunk
        fill(m, box, inner, lambda X, Y, Z: (inner_f(X, Y, Z) > 1) & (inner_f(X, Y, Z) < 1.18) & (Z >= z0), cof,
             only_solid=True)
    for i in range(steps):       # step rings: each a short cylinder standing just proud of the dome
        za = z0 + i * step_h
        rr = r * math.sqrt(max(0.0, 1 - ((za + step_h - z0) / rise) ** 2)) + 1.2
        fill(m, (cx - rr, cx + rr, cy - rr, cy + rr, za, za + step_h), step_mat,
             lambda X, Y, Z, rr=rr: (np.hypot(X - cx, Y - cy) <= rr) & (inner_f(X, Y, Z) > 1),
             tone=lambda X, Y, Z, za=za: 0.4 * (Z > za + step_h - 0.6) - 0.1 + brick(seed + i)(X, Y, Z) * 0.4,
             normal=lambda X, Y, Z: (X - cx, Y - cy, 0 * Z))
    if oculus:
        carve(m, (cx - oculus, cx + oculus, cy - oculus, cy + oculus, z0, z0 + rise + 1),
              lambda X, Y, Z: np.hypot(X - cx, Y - cy) < oculus)
        zt = z0 + rise * math.sqrt(max(0.0, 1 - (oculus / r) ** 2))
        fill(m, (cx - oculus - 1.4, cx + oculus + 1.4, cy - oculus - 1.4, cy + oculus + 1.4, zt - 1.4, zt + 0.9), "bronze",
             lambda X, Y, Z: (np.abs(np.hypot(X - cx, Y - cy) - oculus - 0.6) < 0.8), tone=0.3)
    return z0 + rise


# ---------------------------------------------------------------- statues and small monuments

def figure_mask(s, d, z, sc, zb, h, d0=0.0, w=1.0):
    """A small standing statue in local (along, depth, height) coordinates, `h` tall on zb:
    head, shoulders, a draped body widening to the feet. For niches and arches where the
    figure is a few pixels across."""
    t = (z - zb) / h
    body = (np.abs(s - sc) < h * w * (0.13 + 0.05 * (1 - t))) & (t >= 0) & (t < 0.82)
    sh = (np.abs(s - sc) < h * w * 0.17) & (t > 0.68) & (t < 0.8)
    head = ((s - sc) ** 2 + ((z - zb - h * 0.9) * 1.1) ** 2) < (h * 0.085 * w) ** 2 * 1.0
    return (body | sh | head) & (np.abs(d - d0) < h * 0.12 * w)


def statue(m, x, y, z, height, dress, material="bronze_cast", keep=("gold",), anim="idle", turns=0, base=None,
           base_mat="marble"):
    """A statue cast from a rig dress on an optional moulded base (w, h); returns its top."""
    from rig import BODIES
    zz = z
    if base:
        zz = greek.statue_base(m, x, y, z, base[0], base[1], material=base_mat)
    scale = height / BODIES[dress.body][0]
    if dress.mount:
        sub = _rider_model(dress, round(scale, 3), m.k, material, keep, turns)
    else:
        sub = greek.statue_model(dress, round(scale, 3), m.k, material, keep, anim, 0, turns)
    greek.paste(m, sub, x, y, zz)
    return zz + height


class _ShiftedBody(greek.ScaledBody):
    """A scaled rig body lifted by `shift` (the rider over the horse)."""

    def __init__(self, m, scale, shift):
        import rig
        rig.Body.__init__(self, m, rot=np.eye(3) / scale, shift=shift)
        self.s = scale


@lru_cache(maxsize=None)
def _rider_model(dress, scale, k, material, keep, turns):
    """An equestrian statue: the rig's horse and its rider at `scale`, cast in one material."""
    import rig
    from palette import MAT
    from voxel import Model
    fr = rig.Frame(dress)
    p = rig.pose("ride", 0, rig.POSES["ride"], fr, dress)
    reach = int(math.ceil(30 * scale)) + 2
    m = Model.empty(-reach, reach, -reach, reach, 0, int(math.ceil((fr.H + 32) * scale)) + 2, k=k)
    seat = rig.horse(greek.ScaledBody(m, scale), 0.0)
    rig.draw(_ShiftedBody(m, scale, (0.0, 0.0, (seat - (fr.hip - 0.6 * fr.f) - 0.1) * scale)), dress, p, fr)
    sel = (m.mat > 0) & ~np.isin(m.mat, [MAT[n] for n in keep])
    m.mat[sel] = MAT[material]
    return m.rotated(turns, 0, 0) if turns else m


def obelisk(m, x, y, z, h, w, material="granite_pink", base_h=None, base_mat="marble", gilt=True):
    """An Egyptian obelisk: a tapering square shaft with incised signs, a pyramidion (gilded
    caps are attested) on a stepped base."""
    if base_h:
        for i, (bw, bh) in enumerate(((w * 2.4, base_h * 0.25), (w * 2.0, base_h * 0.75))):
            zz = z + (0 if i == 0 else base_h * 0.25)
            slab(m, x - bw / 2, x + bw / 2, y - bw / 2, y + bw / 2, zz, zz + bh, base_mat,
                 tone=lambda X, Y, Z, zz=zz, bh=bh: 0.3 * (Z > zz + bh - 0.6) - 0.05)
        z += base_h
    hs = h * 0.92

    def mask(X, Y, Z):
        t = np.clip((Z - z) / hs, 0, 1)
        half = w / 2 * (1 - 0.35 * t)
        return (np.abs(X - x) <= half) & (np.abs(Y - y) <= half)

    def tone(X, Y, Z):
        col = _i((X + Y) * 2)
        row = _i(Z * 2)
        sign = (hash01(col, row, 17) < 0.3) & (np.abs((X + Y) - (x + y)) < w * 0.35)
        return (value_noise(X, Y, Z, 4.0, 3) - 0.5) * 0.3 - 0.6 * sign
    fill(m, (x - w / 2, x + w / 2, y - w / 2, y + w / 2, z, z + hs), material, mask, tone)
    top = w / 2 * 0.65

    def pyr(X, Y, Z):
        t = np.clip((Z - z - hs) / (h - hs), 0, 1)
        return (np.abs(X - x) <= top * (1 - t)) & (np.abs(Y - y) <= top * (1 - t))
    fill(m, (x - top, x + top, y - top, y + top, z + hs, z + h), "gold" if gilt else material, pyr, tone=0.3)
    return z + h


def spiral_column(m, cx, cy, z0, S: Scale, H_m=29.8, D_m=3.7, turns=23, image=None, material="marble",
                  pedestal_m=5.4, statue_dress=None):
    """An honorific column with a spiral relief band (Trajan's): a pedestal carved with
    weapons, a torus wreathed with laurel, the shaft wound with `turns` turns of a band of
    figures (`image`: (img, cmap) of the unrolled band, one pixel per voxel), a Doric capital,
    a viewing platform with a railing, and a gilded bronze statue on top."""
    pw = S.h(5.5) / 2
    ph = S.v(pedestal_m)
    slab(m, cx - pw - 0.8, cx + pw + 0.8, cy - pw - 0.8, cy + pw + 0.8, z0, z0 + 1.2, material, tone=0.2)
    slab(m, cx - pw, cx + pw, cy - pw, cy + pw, z0 + 1.2, z0 + ph - 1.2, material,
         tone=lambda X, Y, Z: -0.55 * (hash01(_i((X + Y) * 1.3), _i(Z * 1.3), 23) < 0.38) + 0.1)
    for face in FACES:   # the door and the inscription panel over it (on the south)
        if face == "+x":
            inscription(m, face, (cx - pw, cx + pw, cy - pw, cy + pw), pw * 0.4, pw * 1.6, z0 + ph * 0.55,
                        z0 + ph * 0.85, "cinnabar", rows=3)
    slab(m, cx - pw - 0.6, cx + pw + 0.6, cy - pw - 0.6, cy + pw + 0.6, z0 + ph - 1.2, z0 + ph, material, tone=0.35)
    r = S.h(D_m) / 2
    zs = z0 + ph
    revolve(m, cx, cy, zs, zs + 1.6, lambda t: r * (1.18 - 0.12 * t), material,
            tone=lambda X, Y, Z: 0.4 * (np.cos(np.arctan2(Y - cy, X - cx) * 12 + Z * 3) > 0.4) - 0.2)
    zs += 1.6
    Hs = S.v(H_m) - 1.6 - S.v(1.6)
    pitch = Hs / turns
    circ = 2 * np.pi * r
    img, cmap = image if image is not None else (None, None)

    def radius(t):
        return r * (1 - 0.1 * t)

    def mask(X, Y, Z):
        t = np.clip((Z - zs) / Hs, 0, 1)
        return np.hypot(X - cx, Y - cy) <= radius(t)

    def tone(X, Y, Z):
        a = (np.arctan2(Y - cy, X - cx) / (2 * np.pi)) % 1.0
        q = (Z - zs) / pitch - a                   # turns climbed along the helix at this angle
        v = q % 1.0
        border = (v < 0.08)
        return -0.5 * border + (value_noise(X, Y, Z, 3.0, 5) - 0.5) * 0.2
    fill(m, (cx - r, cx + r, cy - r, cy + r, zs, zs + Hs), material, mask, tone,
         lambda X, Y, Z: (X - cx, Y - cy, 0 * Z))
    if img is not None:
        Hh, W = img.shape
        mats = {}
        cols = {**R.DEFAULT, "stone": material, "flesh": material}
        for j, i in zip(*np.nonzero(img != ".")):
            slot = R.CODES[img[j, i]][0]
            pal = {**cols, **cmap.get((j, i), {})}
            mats.setdefault(pal.get(slot, slot), []).append((j, i))
        sel = {name: np.zeros(img.shape, bool) for name in mats}
        for name, pts in mats.items():
            jj, ii = zip(*pts)
            sel[name][list(jj), list(ii)] = True

        def look(X, Y, Z):
            a = (np.arctan2(Y - cy, X - cx) / (2 * np.pi)) % 1.0
            q = (Z - zs) / pitch - a
            turn = np.floor(q)
            v = q - turn
            u = ((turn + a) * circ * 2).astype(np.int64)     # px along the unrolled band
            row = ((1 - v) * Hh).astype(np.int64)
            ok = (turn >= 0) & (u >= 0) & (u < W) & (row >= 0) & (row < Hh)
            return np.clip(row, 0, Hh - 1), np.clip(u, 0, W - 1), ok
        for name, sm in sel.items():
            def fm(X, Y, Z, sm=sm):
                row, u, ok = look(X, Y, Z)
                t = np.clip((Z - zs) / Hs, 0, 1)
                rr = np.hypot(X - cx, Y - cy)
                return ok & sm[row, u] & (rr <= radius(t) + 0.55) & (rr > radius(t) - 0.6)
            fill(m, (cx - r - 0.6, cx + r + 0.6, cy - r - 0.6, cy + r + 0.6, zs, zs + Hs), name, fm, tone=0.25,
                 normal=lambda X, Y, Z: (X - cx, Y - cy, 0 * Z))
    zt = zs + Hs
    revolve(m, cx, cy, zt, zt + S.v(0.8), lambda t: r * 0.9 * (1.0 + 0.3 * t), material, tone=0.2)
    zt += S.v(0.8)
    ab = r * 1.25
    slab(m, cx - ab, cx + ab, cy - ab, cy + ab, zt, zt + S.v(0.8), material, tone=0.3)
    zt += S.v(0.8)
    for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):           # the platform railing
        rod(m, (cx + dx * ab, cy - ab, zt + 1.0), (cx + dx * ab, cy + ab, zt + 1.0), 0.2, "bronze", tone=0.2)
        rod(m, (cx - ab, cy + dy * ab, zt + 1.0), (cx + ab, cy + dy * ab, zt + 1.0), 0.2, "bronze", tone=0.2)
    revolve(m, cx, cy, zt, zt + S.v(2.2), lambda t: r * 0.55 * (1 - 0.2 * t), material, tone=0.1)
    zt += S.v(2.2)
    if statue_dress is not None:
        zt = statue(m, cx, cy, zt, S.v(4.5), statue_dress, material="gold", keep=())
    return zt


# ---------------------------------------------------------------- façades round ellipses and circles

@dataclass(frozen=True)
class Storey:
    """One storey of a curved façade. `kind`: arcade (arches between engaged half columns of
    `order`), attic (a wall with pilasters, small windows in every other bay, corbels and
    sockets for awning masts), shops (rectangular shop doors with a window over each),
    windows (a plain wall with one window a bay), blind (a plain wall with pilasters).
    `arch` = (width, spring) as fractions of the bay and of the storey height."""
    h: float
    kind: str = "arcade"
    order: str = "tuscan"
    arch: tuple = (0.62, 0.62)
    statues: bool = False
    masts: int = 0
    material: str = "travertine"
    numbers: bool = False


class Ellipse:
    """Arc length along an ellipse (semi-axes a along x, b along y) for even bays."""

    def __init__(self, cx, cy, a, b):
        self.cx, self.cy, self.a, self.b = cx, cy, a, b
        th = np.linspace(-np.pi, np.pi, 4097)
        dl = np.hypot(-a * np.sin(th), b * np.cos(th))
        s = np.concatenate([[0], np.cumsum((dl[1:] + dl[:-1]) / 2 * (th[1] - th[0]))])
        self.th, self.s, self.L = th, s, float(s[-1])

    def polar(self, X, Y):
        """(param angle, arc length from -pi, radial depth inside the ellipse, outward normal)."""
        dx, dy = X - self.cx, Y - self.cy
        th = np.arctan2(dy / self.b, dx / self.a)
        rho = np.hypot(dx / self.a, dy / self.b)
        phi = np.arctan2(dy, dx)
        reff = self.a * self.b / np.hypot(self.b * np.cos(phi), self.a * np.sin(phi))
        depth = reff * (1 - rho)
        s = np.interp(th, self.th, self.s)
        return th, s, depth

    def point(self, th, off=0.0):
        """The point at parameter th, moved `off` outward along the radius."""
        x, y = self.a * math.cos(th), self.b * math.sin(th)
        rr = math.hypot(x, y)
        return self.cx + x * (1 + off / rr), self.cy + y * (1 + off / rr)


def ring_facade(m, el: Ellipse, z0, storeys, bays, thick, S: Scale, arc=None, inward=False, seed=0,
                gaps=(), statue_mat="marble", phase=0.0):
    """A façade wall following the ellipse `el` (its outer face on the ellipse, or its inner
    face with `inward`), `thick` deep, in stacked `storeys` of `bays` equal bays round the
    whole ellipse; `arc` = (th0, th1) keeps only that stretch (theatres, hemicycles); `gaps`
    lists bay indices left open as entrances (always arched through); `phase` shifts the bays
    along the ellipse (0.5 centres bay 0 on the -x axis). Returns the top z."""
    bay = el.L / bays
    hw = el.a + thick + 6
    box = (el.cx - hw, el.cx + hw, el.cy - (el.b + thick + 6), el.cy + (el.b + thick + 6))
    sgn = -1.0 if inward else 1.0

    def frame(X, Y):
        th, s, depth = el.polar(X, Y)
        s = s + phase * bay
        d = depth if not inward else -depth       # depth into the wall from its visible face
        inarc = np.ones_like(th, bool) if arc is None else _in_arc(th, arc)
        u = (s % bay) / bay
        return th, s, d, u, inarc

    z = z0
    for si, st in enumerate(storeys):
        za, zb = z, z + st.h

        def solid(X, Y, Z, za=za, zb=zb, st=st):
            th, s, d, u, inarc = frame(X, Y)
            return (d >= 0) & (d < thick) & inarc & (Z >= za) & (Z < zb)

        def tn(X, Y, Z, za=za, st=st):
            th, s, d, u, inarc = frame(X, Y)
            row = _i((Z - za) / 3.0)
            col = _i((s + (row % 2) * 4.0) / 8.0)
            jn = (((Z - za) % 3.0) < 0.3) | (((s + (row % 2) * 4.0) % 8.0) < 0.3)
            return (hash01(row, col, seed + si) - 0.5) * 0.5 - 0.8 * jn
        fill(m, (*box, za, zb), st.material, solid, tn)
        aw, asp = st.arch
        w = bay * aw
        spring = za + st.h * asp
        if st.kind in ("arcade", "shops", "windows", "attic"):
            if st.kind == "arcade":
                def hole(X, Y, Z, za=za, spring=spring, w=w):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u - 0.5) * bay
                    return inarc & (d >= -0.1) & (d < thick + 0.1) & arch_mask(so, Z, -w / 2, w, za, spring)
            elif st.kind == "shops":
                def hole(X, Y, Z, za=za, w=w, st=st):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u - 0.5) * bay
                    door = (np.abs(so) < w / 2) & (Z >= za) & (Z < za + st.h * 0.55)
                    win = (np.abs(so) < w * 0.25) & (Z >= za + st.h * 0.68) & (Z < za + st.h * 0.88)
                    return inarc & (d >= -0.1) & (d < thick * 0.6) & (door | win)
            elif st.kind == "windows":
                def hole(X, Y, Z, za=za, st=st):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u - 0.5) * bay
                    return inarc & (d >= -0.1) & (d < thick * 0.5) & (np.abs(so) < bay * 0.14) & \
                        (Z >= za + st.h * 0.35) & (Z < za + st.h * 0.7)
            else:
                def hole(X, Y, Z, za=za, st=st):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u - 0.5) * bay
                    alt = (_i(s / bay) % 2) == 0
                    return inarc & alt & (d >= -0.1) & (d < thick * 0.5) & (np.abs(so) < bay * 0.13) & \
                        (Z >= za + st.h * 0.42) & (Z < za + st.h * 0.62)
            carve(m, (*box, za, zb), hole)
            if st.kind in ("shops", "windows", "attic"):
                fill(m, (*box, za, zb), "ink",
                     lambda X, Y, Z, hole=hole: hole(X, Y, Z) & (frame(X, Y)[2] > thick * 0.35), tone=0.0)
        if gaps:
            def gap(X, Y, Z, za=za, spring=spring, w=w):
                th, s, d, u, inarc = frame(X, Y)
                b = _i(s / bay)
                so = (u - 0.5) * bay
                return np.isin(b, gaps) & (d >= -0.1) & (d < thick + 0.1) & arch_mask(so, Z, -w / 2, w, za, spring)
            if si == 0:
                carve(m, (*box, za, zb), gap)
        if st.kind == "arcade":
            # Engaged half columns at the bay joints and the cornice of the storey.
            o_r = bay * 0.085
            ord_h = st.h * 0.86

            def colm(X, Y, Z, za=za, st=st):
                th, s, d, u, inarc = frame(X, Y)
                so = np.minimum(u, 1 - u) * bay
                t = (Z - za) / ord_h
                rr = o_r * (1.0 + 0.35 * (t < 0.06) + 0.45 * ((t > 0.9) & (t < 1.0)) - 0.08 * t)
                return inarc & (so ** 2 + d ** 2 < rr ** 2) & (d < 0) & (Z >= za) & (Z < za + ord_h)

            def ctone(X, Y, Z, za=za, st=st):
                t = (Z - za) / ord_h
                cap = (t > 0.9)
                leaf = cap & (st.order in ("corinthian", "composite")) & (((Z - za) * 2.0) % 1.0 < 0.5)
                return 0.2 + 0.3 * cap - 0.5 * leaf
            fill(m, (*box, za, za + ord_h), st.material, colm, ctone, lambda X, Y, Z: _ring_normal(el, X, Y, Z, sgn))
            ent = st.h - ord_h

            def band(X, Y, Z, za=za, ent=ent):
                th, s, d, u, inarc = frame(X, Y)
                zz = Z - (za + st.h - ent)
                proj = np.where(zz > ent * 0.6, 1.0, np.where(zz > ent * 0.3, 0.6, 0.35))
                return inarc & (d >= -proj) & (d < thick) & (zz >= 0) & (zz < ent)
            fill(m, (*box, zb - ent, zb), st.material, band,
                 lambda X, Y, Z, zb=zb: 0.4 * (Z > zb - 0.5) - 0.3 * ((Z % 1.4) < 0.3))
            if st.numbers:
                def num(X, Y, Z, spring=spring, w=w):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u - 0.5) * bay
                    col = _i(so * 2.0)
                    zz = Z - (spring + w / 2 + 1.0)
                    return inarc & (np.abs(col) <= 2) & (col % 2 == 0) & (zz >= 0) & (zz < 1.5) & (d > -0.2) & (d < 0.4)
                fill(m, (*box, spring, zb), "cinnabar", num, tone=-0.1, only_solid=True)
            if st.statues:
                def fig(X, Y, Z, za=za, spring=spring):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u - 0.5) * bay
                    hh = (spring - za) * 0.62
                    return inarc & figure_mask(so, d, Z, 0.0, za + 1.0, hh, d0=thick * 0.45, w=0.8) & \
                        ~np.isin(_i(s / bay), gaps)
                fill(m, (*box, za, spring), statue_mat, fig, tone=0.35)
        elif st.kind in ("attic", "blind"):
            def pil(X, Y, Z, za=za, zb=zb):
                th, s, d, u, inarc = frame(X, Y)
                so = np.minimum(u, 1 - u) * bay
                return inarc & (so < bay * 0.07) & (d < 0) & (d > -0.6) & (Z >= za) & (Z < zb - 1.5)
            fill(m, (*box, za, zb), st.material, pil, tone=0.25)
            if st.masts:
                def corbel(X, Y, Z, zb=zb):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u * st.masts % 1.0 - 0.5) * bay / st.masts
                    return inarc & (np.abs(so) < 0.5) & (d < 0) & (d > -0.9) & (Z >= zb - st.h * 0.38) & \
                        (Z < zb - st.h * 0.3)
                fill(m, (*box, zb - st.h * 0.4, zb), st.material, corbel, tone=0.3)

                def mast(X, Y, Z, zb=zb):
                    th, s, d, u, inarc = frame(X, Y)
                    so = (u * st.masts % 1.0 - 0.5) * bay / st.masts
                    return inarc & (so ** 2 + (d + 0.45) ** 2 < 0.12) & (Z >= zb - st.h * 0.3) & (Z < zb + st.h * 0.2)
                fill(m, (*box, zb - st.h * 0.3, zb + st.h * 0.22), "wood", mast, tone=0.1)
            fill(m, (*box, zb - 1.5, zb), st.material,
                 lambda X, Y, Z: (frame(X, Y)[2] >= -0.8) & (frame(X, Y)[2] < thick) & frame(X, Y)[4],
                 tone=lambda X, Y, Z, zb=zb: 0.45 * (Z > zb - 0.5))
        z = zb
    return z


def _in_arc(th, arc):
    a0, a1 = arc
    if a0 <= a1:
        return (th >= a0) & (th <= a1)
    return (th >= a0) | (th <= a1)


def _ring_normal(el, X, Y, Z, sgn):
    dx, dy = (X - el.cx) / el.a ** 2, (Y - el.cy) / el.b ** 2
    return (sgn * dx, sgn * dy, 0 * Z)


def cavea(m, el_in: Ellipse, el_out: Ellipse, z_in, z_out, arc=None, material="marble", upper_mat="travertine",
          bands=3, aisles=0, seed=0, step=2.0):
    """Tiered seating rising from the inner ellipse (orchestra or arena edge, at z_in) to the
    outer one (z_out): steps every 1 unit of rise, walkways (praecinctiones) dividing `bands`
    zones, radial stairs and dark vomitoria every `aisles` along the arc; the lower zones in
    marble, the top in travertine."""
    hw = el_out.a + 1
    box = (el_out.cx - hw, el_out.cx + hw, el_out.cy - el_out.b - 1, el_out.cy + el_out.b + 1)

    def frac(X, Y):
        dx, dy = X - el_in.cx, Y - el_in.cy
        r_in = np.hypot(dx / el_in.a, dy / el_in.b)
        r_out = np.hypot(dx / el_out.a, dy / el_out.b)
        # 0 at the inner ellipse, 1 at the outer: where the point lies between the two.
        return np.clip((r_in - 1) / np.maximum((r_in - 1) + (1 - r_out), 1e-3), 0, 1), r_in, r_out

    def surf(X, Y):
        f, r_in, r_out = frac(X, Y)
        z = z_in + (z_out - z_in) * f
        return np.floor(z / step) * step, f, r_in, r_out

    def mask(X, Y, Z):
        top, f, r_in, r_out = surf(X, Y)
        inside = (r_in >= 1) & (r_out <= 1)
        if arc is not None:
            inside &= _in_arc(np.arctan2((Y - el_in.cy) / el_in.b, (X - el_in.cx) / el_in.a), arc)
        return inside & (Z < top + step) & (Z >= z_in - 1.0)

    def tone(X, Y, Z):
        top, f, r_in, r_out = surf(X, Y)
        tread = Z > top + step - 0.6
        walk = ((f * bands) % 1.0) < 0.06
        t = 0.5 * tread - 0.45 + 0.3 * walk - 0.5 * (((f * bands) % 1.0) > 0.97)
        if aisles:
            th = np.arctan2((Y - el_in.cy) / el_in.b, (X - el_in.cx) / el_in.a)
            a = (th / (2 * np.pi) * aisles) % 1.0
            stair = (a < 0.03) | (a > 0.97)
            vom = (np.abs(a - 0.5) < 0.035) & (((f * bands) % 1.0) < 0.22) & (((f * bands) % 1.0) > 0.06)
            t = t + 0.3 * stair - 1.4 * vom
        return t
    fill(m, (*box, z_in - 1.0, z_out + step), material, mask, tone, lambda X, Y, Z: (0 * X, 0 * Y, 1 + 0 * Z))
    fill(m, (*box, z_in - 1.0, z_out + step), upper_mat, lambda X, Y, Z: mask(X, Y, Z) & (surf(X, Y)[1] > 0.62),
         tone, only_solid=True)


# ---------------------------------------------------------------- temples

@dataclass(frozen=True)
class RTemple:
    """A Roman temple in a box: a high podium with a frontal stair between cheek walls, a deep
    porch of `cols` columns across and `deep` rows, and a cella behind. `plan`: prostyle
    (columns in the porch only), peripteral (all round), sine_postico (front and flanks, the
    back wall plain), pseudo (engaged half columns round the cella). `stairs`: front, or
    rostra (a speakers' platform before the porch with stairs at its sides)."""
    order: ROrder
    front: str = "+x"
    cols: int = 6
    deep: int = 3
    plan: str = "prostyle"
    flank: int = 0
    podium: float = 3.5
    podium_kind: str = "marble"
    cella_kind: str = "marble"
    cella_mat: str | None = None
    roof: str = "terracotta"
    pediment: str | None = "gods"
    stairs: str = "front"
    stair_frac: float = 0.22
    acroteria: str = "statues"
    inscription: bool = True
    seed: int = 0
    door_glow: float = 0.0
    margin: float = 1.0


def temple(m, t: RTemple, S: Scale, box, z0=0.0):
    """Build the temple filling the box; returns a dict of heights and the porch box."""
    o = t.order
    Ld, Lw = depth_len(t.front, box)
    P = S.v(t.podium)
    mg = t.margin
    Ls = Ld * t.stair_frac if t.stairs == "front" else Ld * 0.12
    pod_u1 = Ld - (Ls if t.stairs == "front" else 0.0)
    pb = local_box(t.front, box, mg, pod_u1, mg, Lw - mg)
    # Podium: a moulded foot, the die, a crowning moulding.
    slab(m, *local_box(t.front, box, mg - 0.6, pod_u1 + 0.6 * (t.stairs != "front"), mg - 0.6, Lw - mg + 0.6),
         z0, z0 + P * 0.12, t.order.trim if t.podium_kind == "marble" else "travertine", tone=0.2)
    wall(m, pb, z0 + P * 0.12, z0 + P * 0.86, t.podium_kind, t.seed)
    cornice(m, pb, z0 + P * 0.86, P * 0.14, 0.7, t.order.trim if t.podium_kind == "marble" else "travertine")
    zt = z0 + P
    if t.stairs == "front":
        cheek = Lw * 0.09
        sb = local_box(t.front, box, pod_u1 - 0.5, Ld, mg + cheek, Lw - mg - cheek)
        _steps(m, sb, z0, zt, t.front, o.trim, t.seed)
        for v0, v1 in ((mg, mg + cheek), (Lw - mg - cheek, Lw - mg)):     # cheek walls with statue bases
            cb = local_box(t.front, box, pod_u1 - 0.5, Ld - 0.2, v0, v1)
            fill(m, (*cb, z0, zt), o.trim, _cheek(t.front, cb, z0, zt), tone=M.ashlar(2.4, 6.0, t.seed + 3, spread=0.3))
            px, py = local_pt(t.front, box, Ld - 2.0, (v0 + v1) / 2)
            slab(m, px - 1.2, px + 1.2, py - 1.2, py + 1.2, z0, z0 + P * 0.45, o.trim, tone=0.25)
    elif t.stairs == "rostra":
        rb = local_box(t.front, box, pod_u1 - 0.1, Ld, mg + Lw * 0.12, Lw - mg - Lw * 0.12)
        wall(m, rb, z0, zt * 0.7 + z0 * 0.3, t.podium_kind, t.seed + 5)
        cornice(m, rb, zt * 0.7 + z0 * 0.3, 0.8, 0.5, o.trim)
    # Column positions.
    r = o.r(S)
    inset = r * 1.6 + 0.6
    vs = list(np.linspace(mg + inset, Lw - mg - inset, t.cols))
    step = (vs[1] - vs[0]) if len(vs) > 1 else 4 * r
    u_front = pod_u1 - inset
    porch_us = [u_front - i * step for i in range(t.deep)]
    cols = [(u, v) for u in porch_us for v in vs]
    cella_u1 = porch_us[-1] - step * 0.6 if t.plan in ("prostyle", "pseudo") else porch_us[-1] - step * 0.5
    cella_v = (mg + inset - r * 0.6, Lw - mg - inset + r * 0.6) if t.plan in ("prostyle", "pseudo") else \
        (mg + inset + step * 0.55, Lw - mg - inset - step * 0.55)
    if t.plan in ("peripteral", "sine_postico"):
        nf = t.flank or max(3, int(round((u_front - (mg + inset)) / step)) + 1)
        flank_us = list(np.linspace(u_front, mg + inset, nf))
        cols += [(u, v) for u in flank_us for v in (vs[0], vs[-1])]
        if t.plan == "peripteral":
            cols += [(flank_us[-1], v) for v in vs]
        cella_u0 = mg + inset + (step * 0.55 if t.plan == "peripteral" else -r * 0.6)
    else:
        cella_u0 = mg + 0.4
    H = S.v(o.H)
    seen = set()
    for (u, v) in cols:
        key = (round(u, 2), round(v, 2))
        if key in seen:
            continue
        seen.add(key)
        x, y = local_pt(t.front, box, u, v)
        column(m, x, y, zt, o, S, seed=len(seen))
    cb = local_box(t.front, box, cella_u0, cella_u1, cella_v[0], cella_v[1])
    ent = o.entablature(S)
    wall(m, cb, zt, zt + H, t.cella_kind, t.seed + 1, t.cella_mat)
    # The great door in the cella front, bronze leaves in a marble frame.
    front_face = t.front
    Lc = face_length(front_face, *cb)
    dw, dh = min(Lc * 0.3, S.h(6.0)), H * 0.72
    s0 = Lc / 2 - dw / 2
    fill(m, face_box(front_face, *cb, zt, zt + dh + 1.4, s0 - 1.2, s0 + dw + 1.2, -0.5, 0.2), o.trim, tone=0.3)
    carve(m, face_box(front_face, *cb, zt, zt + dh, s0, s0 + dw, -0.6, 1.2))
    fill(m, face_box(front_face, *cb, zt, zt + dh, s0, s0 + dw, 1.0, 1.6), "bronze",
         tone=lambda X, Y, Z: 0.45 * (((Z - zt) % 4.0) < 0.6) - 0.15)
    if t.door_glow:
        dx, dy = _face_point(front_face, cb, Lc / 2, 1.0)
        halo(m, dx, dy, zt + dh * 0.4, 14.0, LAMP, t.door_glow)
    if t.plan == "pseudo":      # half columns round the cella's flanks and back
        for face in side_faces(t.front):
            L = face_length(face, *cb)
            n = max(2, int(round(L / step)) + 1)
            for s in np.linspace(r * 1.2, L - r * 1.2, n):
                engaged(m, face, cb, s, zt, o, S)
    # Entablature over the columns and cella.
    span = local_box(t.front, box, min(cella_u0, porch_us[-1]) - r * 1.2, u_front + r * 1.2, vs[0] - r * 1.2,
                     vs[-1] + r * 1.2)
    ze = entablature(m, span, zt + H, ent, material=o.trim, seed=t.seed,
                     inscribe=(t.front,) if t.inscription else (), frieze="plain")
    # Roof and pediments.
    out = ent * 0.35
    rb = (span[0] - out, span[1] + out, span[2] - out, span[3] + out)
    across = (rb[3] - rb[2]) if t.front in ("+x", "-x") else (rb[1] - rb[0])
    rise = across / 2 * 0.36
    axis = "x" if t.front in ("+x", "-x") else "y"
    fill(m, (*span, ze - 0.5, ze + rise), o.trim,
         lambda X, Y, Z: Z < ze + rise * (1 - np.abs(((Y - (rb[2] + rb[3]) / 2) if axis == "x" else
                                                      (X - (rb[0] + rb[1]) / 2))) / (across / 2)) - 1.6, tone=-0.3)
    greek.tiled_roof(m, *rb, ze, rise, axis=axis, material=t.roof, kind="corinthian", seed=t.seed + 13,
                     antefixes=t.roof != "gold", antefix_paint=("terracotta",) if t.roof == "terracotta" else (t.roof,))
    back = side_faces(t.front)[2]
    apex = ze
    for face in (t.front, back):
        apex = pediment(m, face, rb, ze, rise, S, o.trim, subject=t.pediment if face == t.front else None, seed=t.seed)
    if t.acroteria == "statues":
        _acroteria(m, t.front, rb, ze, rise, apex, S, o)
    elif t.acroteria == "quadriga":
        _acroteria(m, t.front, rb, ze, rise, apex, S, o, quadriga=True)
    return {"podium": zt, "capital": zt + H, "top": ze, "apex": apex, "cella": cb, "span": span,
            "porch_u": porch_us, "cols": vs}


def _steps(m, sb, z0, z1, front, material, seed):
    x0, x1, y0, y1 = sb
    n = max(2, int(round((z1 - z0) / 1.0)))
    along_x = front in ("+x", "-x")
    lo, hi = (x0, x1) if along_x else (y0, y1)
    sgn = 1 if front[0] == "+" else -1

    def frac(X, Y):
        a = X if along_x else Y
        f = (a - lo) / (hi - lo)
        return np.clip(f if sgn < 0 else 1 - f, 0, 1)      # 1 at the podium, 0 at the foot

    def mask(X, Y, Z):
        top = z0 + np.ceil(frac(X, Y) * n) / n * (z1 - z0)
        return Z < top

    def tone(X, Y, Z):
        top = z0 + np.ceil(frac(X, Y) * n) / n * (z1 - z0)
        return 0.45 * (top - Z < 0.5) - 0.35 * (top - Z > 0.6)
    fill(m, (x0, x1, y0, y1, z0, z1), material, mask, tone)


def _cheek(front, cb, z0, z1):
    x0, x1, y0, y1 = cb
    along_x = front in ("+x", "-x")
    lo, hi = (x0, x1) if along_x else (y0, y1)
    sgn = 1 if front[0] == "+" else -1

    def mask(X, Y, Z):
        a = X if along_x else Y
        f = (a - lo) / (hi - lo)
        f = np.clip(f if sgn < 0 else 1 - f, 0, 1)
        return Z < z0 + (z1 - z0) * np.clip(0.25 + f * 1.2, 0, 1)
    return mask


def pediment(m, face, rb, z, rise, S: Scale, material, subject=None, seed=0):
    """A Roman pediment on `face` of the roof box: the tympanum set back, the raking cornice
    with modillions, and figures in high relief (`relief_roman.pediment_image`)."""
    go = greek.Order(material=material, geison_h=max(0.5, rise / S.v(1.0) * 0.12))
    zap = greek.pediment(m, face, *rb, z, rise, go, S, subject=None, paint=False, akroteria=None, sima=True)
    if subject:
        import relief_roman as RR
        along_y = face in ("+y", "-y")
        x0, x1, y0, y1 = rb
        lo, hi = (x0, x1) if along_y else (y0, y1)
        gh = S.v(go.geison_h)
        recess, D = S.h(0.8), S.h(2.2)
        W = int(round((hi - lo - 2 * gh) * 2))
        Hh = int(round((rise - gh * 0.9) * 2))
        if W > 8 and Hh > 6:
            img, cmap = RR.pediment_image(W, Hh, subject)
            if along_y:
                yf = y1 if face == "+y" else y0
                wbox = (x0, x1, yf - D, yf - recess) if face == "+y" else (x0, x1, yf + recess, yf + D)
            else:
                xf = x1 if face == "+x" else x0
                wbox = (xf - D, xf - recess, y0, y1) if face == "+x" else (xf + recess, xf + D, y0, y1)
            R.emboss(m, face, wbox, gh, z + Hh / 2.0, img, cmap=cmap, depth=2)
            R.emboss(m, face, wbox, gh, z + Hh / 2.0, greek._erode(img), cmap=cmap, depth=3)
    return zap


def _acroteria(m, front, rb, z, rise, apex, S, o, quadriga=False):
    """Statues on the apex and the corners of the front pediment (gilded bronze); a chariot
    group on the apex of the greatest temples."""
    from rig import Dress
    x0, x1, y0, y1 = rb
    along_x = front in ("+x", "-x")
    if along_x:
        xf = x1 - 1.5 if front == "+x" else x0 + 1.5
        apex_pt, corners = (xf, (y0 + y1) / 2), ((xf, y0 + 1.5), (xf, y1 - 1.5))
    else:
        yf = y1 - 1.5 if front == "+y" else y0 + 1.5
        apex_pt, corners = ((x0 + x1) / 2, yf), ((x0 + 1.5, yf), (x1 - 1.5, yf))
    hgt = S.v(3.2)
    god = Dress(body="man", garment="long_tunic", colour="gold", beard="full", hair_style="curly", hand_l="staff")
    victory = Dress(body="woman", garment="chiton_long", colour="gold", hair_style="knot", beard="none",
                    hand_l="branch")
    if quadriga:
        quadriga_group(m, apex_pt[0], apex_pt[1], apex - 0.8, hgt, front, material="gold")
    else:
        statue(m, apex_pt[0], apex_pt[1], apex - 0.8, hgt, god, material="gold", keep=())
    for cx, cy in corners:
        statue(m, cx, cy, z + 0.4, hgt * 0.85, victory, material="gold", keep=())


def quadriga_group(m, x, y, z, h, front, material="gold"):
    """A four-horse chariot group on a roof or an arch: horses abreast, the car and its
    driver, facing `front`."""
    fx, fy = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[front]
    px, py = -fy, fx                     # across the team
    hh = h * 0.55                        # horse height at the withers
    for i in range(4):
        o_ = (i - 1.5) * hh * 0.42
        bx, by = x + px * o_ + fx * hh * 0.3, y + py * o_ + fy * hh * 0.3
        ellipsoid(m, (bx, by, z + hh * 0.75), (abs(fx) * hh * 0.55 + abs(px) * hh * 0.16 + 0.3,
                                               abs(fy) * hh * 0.55 + abs(py) * hh * 0.16 + 0.3, hh * 0.22), material, 0.2)
        rod(m, (bx + fx * hh * 0.4, by + fy * hh * 0.4, z + hh * 0.85), (bx + fx * hh * 0.75, by + fy * hh * 0.75,
                                                                          z + hh * 1.3), hh * 0.12, material, 0.3)
        for lx in (-0.35, 0.35):
            rod(m, (bx + fx * hh * lx, by + fy * hh * lx, z + hh * 0.6), (bx + fx * hh * lx * 1.2, by + fy * hh * lx * 1.2, z),
                hh * 0.06 + 0.15, material, 0.0)
    cx, cy = x - fx * hh * 0.45, y - fy * hh * 0.45
    ellipsoid(m, (cx, cy, z + hh * 0.45), (hh * 0.35, hh * 0.35, hh * 0.3), material, 0.3)
    rod(m, (cx, cy, z + hh * 0.5), (cx, cy, z + h * 1.05), hh * 0.16, material, 0.2)
    ellipsoid(m, (cx, cy, z + h * 1.1), (hh * 0.13, hh * 0.13, hh * 0.15), material, 0.4)


def round_temple(m, cx, cy, z0, r, n, o: ROrder, S: Scale, steps=3, roof="terracotta", cella_kind="marble",
                 smoke_hole=False, door_face="+x", glow=0.0, seed=0):
    """A round temple (Vesta, Hercules Victor): a stepped round platform, a ring of `n`
    columns, a round cella, a conical tiled roof (a smoke opening at the top for Vesta)."""
    for i in range(steps):
        rr = r - i * 0.9
        revolve(m, cx, cy, z0 + i * 1.0, z0 + (i + 1) * 1.0, lambda t, rr=rr: rr, o.trim,
                tone=lambda X, Y, Z, i=i: 0.35 * (Z > z0 + (i + 1) * 1.0 - 0.5) - 0.05)
    zt = z0 + steps * 1.0
    rc = r - steps * 0.9 - o.r(S) * 1.3
    for i in range(n):
        a = 2 * np.pi * (i + 0.5) / n
        column(m, cx + math.cos(a) * rc, cy + math.sin(a) * rc, zt, o, S, seed=i)
    H = S.v(o.H)
    rw = rc - o.r(S) * 2.0 - S.h(1.6)
    revolve(m, cx, cy, zt, zt + H, lambda t: rw, o.trim if cella_kind == "marble" else "travertine",
            tone=M.ashlar(2.6, 5.0, seed, joint=0.2, spread=0.25))
    fx, fy = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[door_face]
    dx, dy = cx + fx * rw, cy + fy * rw
    dw = S.h(2.6)
    fill(m, (dx - dw, dx + dw, dy - dw, dy + dw, zt, zt + H * 0.6), "bronze",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) > rw - 0.6) & (np.abs((X - dx) * fy - (Y - dy) * fx) < dw * 0.5),
         tone=lambda X, Y, Z: 0.4 * (((Z - zt) % 3.0) < 0.5) - 0.1)
    if glow:
        halo(m, dx, dy, zt + H * 0.3, 12.0, (255, 154, 58), glow)
    ze = zt + H
    ent = o.entablature(S) * 0.8
    revolve(m, cx, cy, ze, ze + ent * 0.6, lambda t: rc + o.r(S) * 1.2, o.trim,
            tone=lambda X, Y, Z: 0.3 * ((Z - ze) % 1.4 > 1.0) - 0.05)
    revolve(m, cx, cy, ze + ent * 0.6, ze + ent, lambda t: rc + o.r(S) * 1.2 + 1.0 * t, o.trim, tone=0.3)
    zr = ze + ent
    rr = rc + o.r(S) * 1.2 + 1.2
    greek.conical_roof(m, cx, cy, rr, zr, rr * 0.5, material=roof, seed=seed + 5)
    if smoke_hole:
        carve(m, (cx - 1.4, cx + 1.4, cy - 1.4, cy + 1.4, zr + rr * 0.42, zr + rr * 0.55),
              lambda X, Y, Z: np.hypot(X - cx, Y - cy) < 1.2)
        fill(m, (cx - 2, cx + 2, cy - 2, cy + 2, zr + rr * 0.4, zr + rr * 0.5), "bronze",
             lambda X, Y, Z: np.abs(np.hypot(X - cx, Y - cy) - 1.5) < 0.5, tone=0.3)
    return zr + rr * 0.5


# ---------------------------------------------------------------- arcaded fronts, porticoes, arches

def arcade_front(m, face, wall_box, z0, storeys, bays, seed=0, s0=0.0, s1=None, statue_mat=None, depth=3.0):
    """A straight arcaded façade on a face, storeys = [(height, order kind, material)], `bays`
    arches a storey between engaged half columns; returns the top."""
    x0, x1, y0, y1 = wall_box[:4]
    L = face_length(face, x0, x1, y0, y1) if s1 is None else s1
    bay = (L - s0) / bays
    z = z0
    for i, (h, kind, mat) in enumerate(storeys):
        aw = bay * 0.6
        for b in range(bays):
            sa = s0 + b * bay + (bay - aw) / 2
            opening(m, face, wall_box, sa, aw, z, z + h * 0.6, depth, frame=mat)
            if statue_mat and i > 0:
                hh = h * 0.5

                def fig(X, Y, Z, sa=sa, z=z, hh=hh):
                    s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
                    return figure_mask(s, d, Z, sa + aw / 2, z + 0.4, hh, d0=1.5)
                fill(m, face_box(face, x0, x1, y0, y1, z, z + hh + 1, sa, sa + aw, 0.5, 2.5), statue_mat, fig, 0.3)
        S1 = Scale(1.0)
        o = ROrder(kind=kind, D=bay * 0.16 / 4.0, H=h * 0.86 / 5.0, shaft=mat, trim=mat, fluted=False)
        for b in range(bays + 1):
            engaged(m, face, wall_box, s0 + b * bay, z, o, S1)
        ent = h * 0.14
        fill(m, face_box(face, x0, x1, y0, y1, z + h - ent, z + h, s0 - 0.6, L + 0.6, -0.9, 1.0), mat,
             tone=lambda X, Y, Z, zz=z + h: 0.4 * (Z > zz - 0.5) - 0.25 * ((Z % 1.2) < 0.3))
        z += h
    return z


def colonnade(m, a, b, z0, n, o: ROrder, S: Scale, depth, front, roof="terracotta", back_kind="marble",
              back_mat=None, back=True, seed=0, ends=True):
    """A portico along the line from a to b (points (x, y)): `n` columns facing `front`, a back
    wall `depth` behind them (optional), the entablature and a lean-to tiled roof rising to
    the back. Returns the roof top."""
    (ax, ay), (bx, by) = a, b
    H = S.v(o.H)
    pts = [(ax + (bx - ax) * i / max(n - 1, 1), ay + (by - ay) * i / max(n - 1, 1)) for i in range(n)]
    for i, (x, y) in enumerate(pts):
        column(m, x, y, z0, o, S, seed=seed + i)
    r = o.r(S) * 1.3
    fx, fy = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[front]
    xs = [ax, bx]
    ys = [ay, by]
    line = (min(xs) - r * abs(fy), max(xs) + r * abs(fy), min(ys) - r * abs(fx), max(ys) + r * abs(fx))
    # The back wall.
    bx0, bx1, by0, by1 = line
    if fx:
        wb = (bx0 - fx * depth, bx0 - fx * depth + 1.6, by0, by1) if fx > 0 else (bx1 + depth - 1.6, bx1 + depth, by0, by1)
    else:
        wb = (bx0, bx1, by0 - fy * depth, by0 - fy * depth + 1.6) if fy > 0 else (bx0, bx1, by1 + depth - 1.6, by1 + depth)
    wb = (min(wb[0], wb[1]), max(wb[0], wb[1]), min(wb[2], wb[3]), max(wb[2], wb[3]))
    if back:
        wall(m, wb, z0, z0 + H + o.entablature(S) * 0.7, back_kind, seed, back_mat)
    ent = o.entablature(S) * 0.75
    beam = (line[0] - r * 0.3 * abs(fx), line[1] + r * 0.3 * abs(fx), line[2] - r * 0.3 * abs(fy), line[3] + r * 0.3 * abs(fy))
    ze = entablature(m, beam, z0 + H, ent, faces=(front,), material=o.trim, seed=seed, modillions=False)
    full = (min(beam[0], wb[0]), max(beam[1], wb[1]), min(beam[2], wb[2]), max(beam[3], wb[3]))
    up = {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y"}[front]
    lean_to(m, full, ze, ze + depth * 0.3, up, roof, seed)
    return ze + depth * 0.3


def triumphal_arch(m, box, front, S: Scale, z0=0.0, bays=1, order=None, material="marble", attic_h=None,
                   relief=None, quadriga=True, seed=0, pier=None):
    """A triumphal arch across the box, its passage(s) running along `front` (front and back
    faces are the arch's two faces): piers with engaged Composite columns, Victories in the
    spandrels, a keystone figure, the passage vault with coffers and relief panels on its
    walls (`relief` (img, cmap) or None), an attic with a gilded inscription, a chariot group
    on top; `pier` fixes the width of the outer piers (a passage that must be a whole walk
    tile). The passages are cut down to the ground. Returns the top."""
    o = order or ROrder(kind="composite", D=0.9, H=8.0)
    x0, x1, y0, y1 = box
    Ld, Lw = depth_len(front, box)          # u: through the arch, v: across
    if pier is None:
        pier = Lw / (bays * 2 + 0.6 * (bays - 1) + 2) if bays > 1 else Lw * 0.28
    H = S.v(o.H)
    zb = z0 + S.v(1.2)
    slab(m, *box, z0, zb, material, tone=0.2)
    ent = o.entablature(S)
    zm = zb + H
    wall(m, box, zb, zm, "marble", seed, material)
    if bays == 1:
        passages = [(pier, Lw - pier)]
    else:
        side_w = (Lw - 2 * pier - 2 * pier * 0.7) * 0.23
        mid_w = Lw - 2 * pier - 2 * side_w - 2 * pier * 0.7
        v = pier
        passages = []
        for w in (side_w, mid_w, side_w):
            passages.append((v, v + w))
            v += w + pier * 0.7
    face, back = front, side_faces(front)[2]
    for (v0, v1) in passages:
        w = v1 - v0
        main = w == max(p[1] - p[0] for p in passages)
        spring = zb + (H * 0.62 if main else H * 0.45)
        for f in (face, back):
            s0 = _s_on(front, f, v0, v1, Lw)
            opening(m, f, box, s0, w, z0, spring, Ld / 2 + 0.2, frame=material, frame_w=1.0)
        # Coffered vault and panels inside the passage.
        pb = local_box(front, box, -0.1, Ld + 0.1, v0, v1)
        fill(m, (*pb, spring, spring + w / 2 + 0.3), material,
             lambda X, Y, Z, pb=pb, spring=spring, w=w: _vault_shell(front, pb, X, Y, Z, spring, w),
             tone=lambda X, Y, Z: -0.6 * ((((X + Y) * 0.7) % 1.0) < 0.35) + 0.1)
        if relief is not None and main:
            img, cmap = relief
            for f2, vv in (("l", v0), ("r", v1)):
                wf = _inner_face(front, f2)
                wb = local_box(front, box, Ld * 0.15, Ld * 0.85, vv - (1.0 if f2 == "l" else 0.0),
                               vv + (1.0 if f2 == "r" else 0.0))
                Lp = face_length(wf, *wb)
                R.emboss(m, wf, wb, 0.0, zb + H * 0.5, img[:, :int(Lp * 2)], cmap=cmap, depth=1, sunk=True)
    # Engaged columns on both faces flanking the passages.
    for f in (face, back):
        for (v0, v1) in passages:
            for vv in (v0 - o.r(S) * 1.6, v1 + o.r(S) * 1.6):
                engaged(m, f, box, _s_on(front, f, vv, vv, Lw), zb, o, S)
    ze = entablature(m, box, zm, ent, material=material, seed=seed)
    ah = attic_h or S.v(4.5)
    wall(m, box, ze, ze + ah, "marble", seed + 2, material)
    for f in (face, back):
        L = face_length(f, *box)
        inscription(m, f, box, L * 0.18, L * 0.82, ze + ah * 0.2, ze + ah * 0.8, "gold", rows=3, seed=seed)
    zt = cornice(m, box, ze + ah, 1.0, 0.6, material)
    if quadriga:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        quadriga_group(m, cx, cy, zt, S.v(4.0), front, "bronze_cast")
        zt += S.v(4.0)
    return zt


def _s_on(front, f, v0, v1, Lw):
    """Position along face f of a span v0..v1 measured across a building facing `front`."""
    if f == front:
        return v0 if front in ("+x", "-y") else Lw - v1
    return Lw - v1 if front in ("+x", "-y") else v0


def _inner_face(front, side):
    return {"+x": {"l": "+y", "r": "-y"}, "-x": {"l": "-y", "r": "+y"}, "+y": {"l": "-x", "r": "+x"},
            "-y": {"l": "+x", "r": "-x"}}[front][side]


def _vault_shell(front, pb, X, Y, Z, spring, w):
    x0, x1, y0, y1 = pb
    c = ((y0 + y1) / 2) if front in ("+x", "-x") else ((x0 + x1) / 2)
    a = (Y if front in ("+x", "-x") else X) - c
    rr = np.hypot(a, Z - spring)
    return (rr >= w / 2 - 0.6) & (rr < w / 2) & (Z >= spring)


def basilica(m, box, front, S: Scale, bays, storeys, porch, h_aisle, h_nave, roof="terracotta", hall="brick",
             seed=0, statue_mat=None, clerestory="arched", gilt_roof=False):
    """A basilica: a two-storey arcaded porch `porch` deep along the front (storeys as in
    `arcade_front`), behind it the hall: aisles under lean-to roofs and a higher nave lit by a
    clerestory of windows under its gable; `gilt_roof` covers the nave in gilded bronze tiles
    (the Basilica Ulpia). Returns the ridge top."""
    Ld, Lw = depth_len(front, box)
    pb = local_box(front, box, Ld - porch, Ld, 0.0, Lw)
    zt = z0 = 0.0
    ztop = sum(h for h, _k, _m in storeys)
    mat = storeys[0][2]
    wall(m, pb, z0, ztop, "marble" if mat == "marble" else "travertine", seed, mat)
    arcade_front(m, front, pb, z0, storeys, bays, seed=seed, statue_mat=statue_mat, depth=porch - 1.5)
    for zz in np.cumsum([0.0] + [h for h, _k, _m in storeys[:-1]])[1:]:      # floor of the upper gallery
        slab(m, *local_box(front, box, Ld - porch + 1.0, Ld - 1.0, 1.0, Lw - 1.0), zz - 1.0, zz, mat, tone=-0.3)
    hb = local_box(front, box, 0.0, Ld - porch, 0.0, Lw)
    wall(m, hb, 0.0, h_aisle, hall, seed + 1)
    aisle = (Ld - porch) * 0.28
    nb = local_box(front, box, aisle, Ld - porch - aisle * 0.6, 0.0, Lw)
    wall(m, nb, h_aisle - 1.0, h_nave, hall, seed + 2)
    for f in (front, side_faces(front)[2]):
        L = face_length(f, *nb)
        n = max(3, int(L / 9.0))
        for i in range(n):
            s = (i + 0.5) * L / n - 2.0
            window(m, f, nb, s, 4.0, h_aisle + (h_nave - h_aisle) * 0.25, (h_nave - h_aisle) * 0.45,
                   arched=clerestory == "arched", glass=True)
    back = side_faces(front)[2]
    up_front = {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y"}
    lean_to(m, local_box(front, box, Ld - porch - aisle * 0.6 - 0.5, Ld - porch + 1.0, -0.5, Lw + 0.5), h_aisle,
            h_aisle + 5.0, up_front[front], roof, seed + 3)
    lean_to(m, local_box(front, box, -0.5, aisle + 0.5, -0.5, Lw + 0.5), h_aisle, h_aisle + 5.0, front, roof, seed + 4)
    lean_to(m, local_box(front, box, Ld - porch - 0.5, Ld + 0.5, -0.5, Lw + 0.5), ztop, ztop + 3.0, up_front[front],
            roof, seed + 6)
    across = Ld - porch - aisle * 1.6
    rise = across / 2 * 0.36
    gable(m, local_box(front, box, aisle - 1.0, Ld - porch - aisle * 0.6 + 1.0, -1.0, Lw + 1.0), h_nave, rise,
          "y" if front in ("+x", "-x") else "x", material="gilt" if gilt_roof else roof, seed=seed + 5)
    return h_nave + rise


def aqueduct(m, x0, x1, y0, y1, axis, z0, h, arches=(), pier_w=4.0, channel=3.0, material="tufa", brick_top=True,
             seed=0, ends=(False, False)):
    """A run of aqueduct arcade along `axis` in the box: piers of rusticated tufa ashlar
    carrying round arches, an attic of brick and the covered channel (specus) on top with its
    lid of slabs; `ends` close the run with a solid pier."""
    along_x = axis == "x"
    lo, hi = (x0, x1) if along_x else (y0, y1)
    c0, c1 = (y0, y1) if along_x else (x0, x1)
    w = c1 - c0
    zc = z0 + h - channel - 2.0

    def rustic(X, Y, Z):
        a = (X if along_x else Y)
        row = _i(Z / 3.2)
        col = _i((a + (row % 2) * 3.0) / 6.0)
        jn = ((Z % 3.2) < 0.45) | (((a + (row % 2) * 3.0) % 6.0) < 0.45)
        boss = (hash01(row, col, seed) - 0.5) * 0.7
        return boss - 0.95 * jn
    fill(m, (x0, x1, y0, y1, z0, zc), material, None, rustic)
    for (a0, a1, spring) in arches:
        def hole(X, Y, Z, a0=a0, a1=a1, spring=spring):
            a = X if along_x else Y
            return arch_mask(a, Z, a0, a1 - a0, z0 - 1, spring)
        carve(m, (x0 - 1, x1 + 1, y0 - 1, y1 + 1, z0 - 1, zc), hole)

        def ring(X, Y, Z, a0=a0, a1=a1, spring=spring):
            a = X if along_x else Y
            c = (a0 + a1) / 2
            rr = np.hypot(a - c, Z - spring)
            return (Z >= spring) & (rr >= (a1 - a0) / 2) & (rr < (a1 - a0) / 2 + 1.6)
        fill(m, (x0, x1, y0, y1, z0, zc), material, ring,
             lambda X, Y, Z, a0=a0, a1=a1, spring=spring: 0.3 - 0.9 * (((np.arctan2(Z - spring, (X if along_x else Y)
                                                                                       - (a0 + a1) / 2) * 7 / np.pi) %
                                                                         1.0) < 0.15), only_solid=True)
    # Impost string course and the attic carrying the channel.
    top_mat = "brick" if brick_top else material
    fill(m, (x0 - 0.4 * (not along_x), x1 + 0.4 * (not along_x), y0 - 0.4 * along_x, y1 + 0.4 * along_x, zc, zc + 1.0),
         material, tone=0.3)
    ch_box = (x0, x1, c0 + w * 0.12, c1 - w * 0.12) if along_x else (c0 + w * 0.12, c1 - w * 0.12, y0, y1)
    slab(m, *ch_box, zc + 1.0, zc + 1.0 + channel, top_mat, tone=brick(seed) if brick_top else 0.0)
    lid = (ch_box[0] - 0.3 * (not along_x), ch_box[1] + 0.3 * (not along_x), ch_box[2] - 0.3 * along_x,
           ch_box[3] + 0.3 * along_x)
    slab(m, *lid, zc + 1.0 + channel, zc + 2.0 + channel, material,
         tone=lambda X, Y, Z: -0.6 * ((((X if along_x else Y)) % 5.0) < 0.35) + 0.2)
    return zc + 2.0 + channel
