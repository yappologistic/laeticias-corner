"""Architectural primitives for big voxel models: columns, stairs, merlons, stone frames with
cavetto cornices, relief friezes, glazed-brick panels, mudbrick walls, flat roofs, tents.

Everything is written in the model's design units in grid axes (+x south, +y west, z up) and
draws through `fill`, which evaluates a shape only over the voxels of its bounding box that
lie inside the model's grid. A landmark builder can therefore call every primitive for the
whole building on any chunk and pay only for what falls inside it (`bigrender`).

Faces are named by their outward normal: '+x' (south, the shaded face seen at the lower
right), '+y' (west, the lit face seen at the lower left), '-x' (north) and '-y' (east). On a
face, `s` runs along the wall from left to right as seen from outside, and `d` is the depth
into the wall from its surface.
"""

import math
from dataclasses import dataclass

import numpy as np

from voxel import Halo, Model, hash01, value_noise

FACES = ("+x", "-x", "+y", "-y")


@dataclass(frozen=True)
class Scale:
    """Landmark scale `s` (world.md §2): 8 voxels per metre x s horizontally and 10 per metre
    x s vertically at 64x32 tiles, i.e. 4 s and 5 s design units per metre."""
    s: float = 1.0

    def h(self, metres: float) -> float:
        return 4.0 * self.s * metres

    def v(self, metres: float) -> float:
        return 5.0 * self.s * metres


def fill(m: Model, box, material: str, mask=None, tone=0.0, normal=None, only_empty=False):
    """Put `material` where `mask(X, Y, Z)` holds inside `box` = (x0, x1, y0, y1, z0, z1).
    `tone` and `normal` may be constants or functions of the same local coordinates."""
    w = m.box_window(*box)
    if w is None:
        return
    sl, X, Y, Z = w
    msk = np.ones((X.size, Y.size, Z.size), bool) if mask is None else mask(X, Y, Z)
    if not np.any(msk):
        return
    tn = tone(X, Y, Z) if callable(tone) else tone
    nr = normal(X, Y, Z) if callable(normal) else normal
    m.put(msk, material, tn, nr, only_empty, sl)


def field_fill(m: Model, box, field, material: str, tone=0.0, eps=0.75):
    """Fill where `field(X, Y, Z) < 0` with normals from the field's gradient, so rough natural
    surfaces (rock, earth) shade smoothly instead of as voxel staircases."""
    def normal(X, Y, Z):
        return tuple((field(X + e[0], Y + e[1], Z + e[2]) - field(X - e[0], Y - e[1], Z - e[2]))
                     for e in ((eps, 0, 0), (0, eps, 0), (0, 0, eps)))
    fill(m, box, material, lambda X, Y, Z: field(X, Y, Z) < 0, tone, normal)


def carve(m: Model, box, mask=None):
    w = m.box_window(*box)
    if w is None:
        return
    sl, X, Y, Z = w
    msk = np.ones((X.size, Y.size, Z.size), bool) if mask is None else \
        np.broadcast_to(mask(X, Y, Z), (X.size, Y.size, Z.size))
    m.mat[sl][msk] = 0
    m.nrm[sl][msk] = 0.0


def halo(m: Model, x, y, z, radius, rgb, strength=1.0):
    """Halos are kept by the chunk that contains them (bigrender), so add them always."""
    m.halos.append(Halo(x, y, z, radius, rgb, strength))


def face_frame(face, X, Y, Z, x0, x1, y0, y1):
    """(s, d) on a box's face: s along the wall left to right seen from outside, d inward."""
    if face == "+x":
        return y1 - Y, x1 - X
    if face == "-x":
        return Y - y0, X - x0
    if face == "+y":
        return X - x0, y1 - Y
    return x1 - X, Y - y0


def face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, d0, d1):
    """The box covering s in [s0, s1), depth d in [d0, d1) of a face of [x0,x1)x[y0,y1)."""
    if face == "+x":
        return (x1 - d1, x1 - d0, y1 - s1, y1 - s0, z0, z1)
    if face == "-x":
        return (x0 + d0, x0 + d1, y0 + s0, y0 + s1, z0, z1)
    if face == "+y":
        return (x0 + s0, x0 + s1, y1 - d1, y1 - d0, z0, z1)
    return (x1 - s1, x1 - s0, y0 + d0, y0 + d1, z0, z1)


def face_normal(face):
    return {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+y": (0.0, 1.0, 0.0),
            "-y": (0.0, -1.0, 0.0)}[face]


def face_length(face, x0, x1, y0, y1):
    return (y1 - y0) if face in ("+x", "-x") else (x1 - x0)


# ---------- textures (tones as functions of local coordinates) ----------

def ashlar_tone(course=3.0, block=6.0, seed=1, joint=0.35, polygonal=0.0):
    """Coursed blocks with fine dark joints and a lit top edge; `polygonal` skews joints so
    big blocks read as the fitted polygonal masonry of a terrace wall."""
    def tone(X, Y, Z):
        along = X + Y
        row = np.floor(Z / course)
        skew = polygonal * (hash01(row.astype(np.int64), seed) - 0.5) * (Z % course) / course * block
        a = along + (row % 2) * block * 0.5 + skew
        col = np.floor(a / block)
        j = joint
        jn = ((Z % course) < j) | ((a % block) < j)
        top = (Z % course) >= course - j
        h = hash01(row.astype(np.int64), col.astype(np.int64), seed)
        return -1.0 * jn + 0.35 * top + (h - 0.5) * 0.6
    return tone


def plaster_tone(seed=3, amount=0.5):
    """Hand-smoothed mud plaster: broad soft blotches, never noisy."""
    def tone(X, Y, Z):
        n = value_noise(X + Y * 0.7, Y - X * 0.3, Z, 6.0, seed)
        return (n - 0.5) * amount
    return tone


def brick_tone(course=1.0, brick=2.0, seed=5):
    def tone(X, Y, Z):
        row = np.floor(Z / course)
        a = X + Y + (row % 2) * brick / 2
        jn = ((Z % course) < 0.25) | ((a % brick) < 0.25)
        return -0.8 * jn + (hash01(row.astype(np.int64), np.floor(a / brick).astype(np.int64), seed) - 0.5) * 0.5
    return tone


# ---------- solids ----------

def slab(m, x0, x1, y0, y1, z0, z1, material, tone=0.0, normal=None):
    fill(m, (x0, x1, y0, y1, z0, z1), material, tone=tone, normal=normal)


def cylinder(m, cx, cy, r, z0, z1, material, tone=0.0, flutes=0, flute_depth=0.18):
    """Upright cylinder; `flutes` cut shallow vertical channels that catch the light."""
    def mask(X, Y, Z):
        dx, dy = X - cx, Y - cy
        rr = np.hypot(dx, dy)
        if flutes:
            a = np.arctan2(dy, dx)
            rad = r - flute_depth * (np.cos(a * flutes) > 0.3)
            return rr <= rad
        return rr <= r

    def tn(X, Y, Z):
        base = tone(X, Y, Z) if callable(tone) else tone
        if not flutes:
            return base
        a = np.arctan2(Y - cy, X - cx)
        return base + 0.55 * (np.cos(a * flutes) > 0.3) - 0.25

    fill(m, (cx - r, cx + r, cy - r, cy + r, z0, z1), material, mask, tn,
         lambda X, Y, Z: (X - cx, Y - cy, Z * 0.0))


def revolve(m, cx, cy, z0, z1, radius, material, tone=0.0, ribs=0):
    """A turned shape: `radius(t)` gives the radius at height fraction t in [0, 1]."""
    shaped = radius
    radius = lambda t: shaped(t) + np.zeros_like(t)     # constant radii are allowed
    rmax = float(np.max(radius(np.linspace(0, 1, 64))))

    def mask(X, Y, Z):
        t = np.clip((Z - z0) / (z1 - z0), 0, 1)
        return np.hypot(X - cx, Y - cy) <= radius(t)

    def tn(X, Y, Z):
        base = tone(X, Y, Z) if callable(tone) else tone
        if not ribs:
            return base
        a = np.arctan2(Y - cy, X - cx)
        return base + 0.6 * (np.cos(a * ribs) > 0.55) - 0.2

    def nr(X, Y, Z):
        t = np.clip((Z - z0) / (z1 - z0), 0, 1)
        dr = (radius(np.clip(t + 0.02, 0, 1)) - radius(np.clip(t - 0.02, 0, 1))) / (0.04 * (z1 - z0))
        return (X - cx, Y - cy, -dr * np.hypot(X - cx, Y - cy))

    fill(m, (cx - rmax, cx + rmax, cy - rmax, cy + rmax, z0, z1), material, mask, tn, nr)


def ellipsoid(m, c, r, material, tone=0.0):
    cx, cy, cz = c
    rx, ry, rz = r
    fill(m, (cx - rx, cx + rx, cy - ry, cy + ry, cz - rz, cz + rz), material,
         lambda X, Y, Z: ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2 + ((Z - cz) / rz) ** 2 <= 1,
         tone, lambda X, Y, Z: ((X - cx) / rx ** 2, (Y - cy) / ry ** 2, (Z - cz) / rz ** 2))


def rod(m, p, q, r, material, tone=0.0):
    """A capsule from p to q (poles, ropes, beams at an angle)."""
    p, q = np.asarray(p, np.float32), np.asarray(q, np.float32)
    lo, hi = np.minimum(p, q) - r, np.maximum(p, q) + r
    d = q - p
    dd = float(d @ d) or 1e-6

    def axis(X, Y, Z):
        t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1] + (Z - p[2]) * d[2]) / dd, 0, 1)
        return X - p[0] - t * d[0], Y - p[1] - t * d[1], Z - p[2] - t * d[2]

    def mask(X, Y, Z):
        a, b, c = axis(X, Y, Z)
        return a * a + b * b + c * c <= r * r

    fill(m, (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]), material, mask, tone, axis)


# ---------- columns ----------

@dataclass(frozen=True)
class Column:
    """An Achaemenid column (persepolis.md §3.1), heights in design units.

    base: 'bell' (bell-shaped with hanging petals on a square plinth), 'square' (square
    two-step plinth with a torus) or 'plain'. capital: 'bull', 'lion', 'griffin' (addorsed
    protomes over a bell and tall double volutes), 'protome' (protomes only, the short
    capitals of lesser halls), 'wood' (painted wooden column with a simple cap) or 'none'
    (a shaft still being built). `beam` is the axis the protomes face along ('x' or 'y')."""
    shaft_r: float
    height: float                 # base to the saddle top
    base: str = "bell"
    capital: str = "bull"
    beam: str = "y"
    flutes: int = 24
    material: str = "limestone"
    paint: bool = True            # gilded horns and painted eyes on the protomes


def column(m: Model, cx: float, cy: float, z0: float, c: Column):
    r = c.shaft_r
    H = c.height
    mat = c.material
    if c.base == "bell":
        plinth = 0.035 * H
        slab(m, cx - r * 2.0, cx + r * 2.0, cy - r * 2.0, cy + r * 2.0, z0, z0 + plinth, mat,
             tone=ashlar_tone(plinth, r * 4, 11))
        bell_h = 0.07 * H
        revolve(m, cx, cy, z0 + plinth, z0 + plinth + bell_h,
                lambda t: r * (1.85 - 0.75 * t ** 0.8), mat, ribs=16)
        torus_z = z0 + plinth + bell_h
    elif c.base == "square":
        s1, s2 = 0.025 * H, 0.025 * H
        slab(m, cx - r * 2.1, cx + r * 2.1, cy - r * 2.1, cy + r * 2.1, z0, z0 + s1, mat, tone=-0.2)
        slab(m, cx - r * 1.7, cx + r * 1.7, cy - r * 1.7, cy + r * 1.7, z0 + s1, z0 + s1 + s2, mat)
        torus_z = z0 + s1 + s2
    else:
        torus_z = z0
    torus_h = 0.02 * H if c.base != "plain" else 0.0
    if torus_h:
        revolve(m, cx, cy, torus_z, torus_z + torus_h,
                lambda t: r * (1.12 + 0.18 * np.sin(np.pi * t)), mat, tone=0.3)
    shaft0 = torus_z + torus_h
    cap = {"bull": 0.30, "lion": 0.30, "griffin": 0.30, "protome": 0.14, "wood": 0.06,
           "none": 0.0}[c.capital]
    shaft1 = z0 + H * (1 - cap)
    if c.capital == "wood":
        cylinder(m, cx, cy, r, shaft0, shaft1, mat, tone=_band_tone(shaft0, shaft1))
    else:
        cylinder(m, cx, cy, r, shaft0, shaft1, mat, flutes=c.flutes if m.fine else 0)
    if c.capital == "none":
        return
    if c.capital == "wood":
        slab(m, cx - r * 1.5, cx + r * 1.5, cy - r * 1.5, cy + r * 1.5, shaft1, z0 + H, "cedar")
        return
    z = shaft1
    if c.capital in ("bull", "lion", "griffin"):
        # The palm element: a drooping leaf crown, then an upright calyx.
        ph = 0.07 * H
        revolve(m, cx, cy, z, z + ph * 0.45, lambda t: r * (1.0 + 0.7 * t ** 1.5), mat, ribs=14, tone=0.1)
        revolve(m, cx, cy, z + ph * 0.45, z + ph, lambda t: r * (1.25 - 0.35 * t + 0.4 * t ** 3), mat,
                ribs=18, tone=0.2)
        z += ph
        # Tall double volutes: a slim block with paired vertical scrolls on two faces.
        vh = 0.11 * H
        _volutes(m, cx, cy, z, z + vh, r, c.beam, mat)
        z += vh
    _protomes(m, cx, cy, z, z0 + H, r, c, mat)


def _band_tone(z0, z1):
    """Painted bands on a plastered wooden column (Treasury)."""
    def tone(X, Y, Z):
        t = (Z - z0) / max(z1 - z0, 1)
        return 0.4 * (np.sin(t * 40) > 0.6) - 0.3 * (np.sin(t * 40 + 1.4) > 0.8)
    return tone


def _volutes(m, cx, cy, z0, z1, r, beam, mat):
    along_x = beam == "x"
    hw_a, hw_b = (r * 1.15, r * 0.95)
    lx, ly = (hw_a, hw_b) if along_x else (hw_b, hw_a)
    slab(m, cx - lx, cx + lx, cy - ly, cy + ly, z0, z1, mat, tone=0.1)

    def scrolls(X, Y, Z):
        s = (Y - cy) if along_x else (X - cx)
        t = (Z - z0) / (z1 - z0)
        u = np.abs(s) / (r * 1.2)
        curl = ((t < 0.22) | (t > 0.78)) & (u > 0.35)
        rib = np.cos(t * 24) > 0.4
        return curl, rib

    def tone(X, Y, Z):
        curl, rib = scrolls(X, Y, Z)
        return 0.6 * curl - 0.4 * rib * ~curl
    ext = 0.35 * r
    ex, ey = (lx, ly + ext) if along_x else (lx + ext, ly)
    fill(m, (cx - ex, cx + ex, cy - ey, cy + ey, z0, z1), mat,
         lambda X, Y, Z: scrolls(X, Y, Z)[0] | ((np.abs(X - cx) <= lx) & (np.abs(Y - cy) <= ly)), tone)


def _protomes(m, cx, cy, z0, z1, r, c: Column, mat):
    """Two animal foreparts back to back along the beam axis, the saddle between them."""
    h = z1 - z0
    L = r * 2.6                    # each forepart's reach from the axis
    w = r * 0.95
    sx, sy = (1, 0) if c.beam == "x" else (0, 1)
    paint = c.paint
    for side in (-1, 1):
        ox, oy = sx * side, sy * side
        # Body: a deep chest; the saddle between the two heads is a little lower.
        ellipsoid(m, (cx + ox * L * 0.42, cy + oy * L * 0.42, z0 + h * 0.48),
                  (abs(ox) * L * 0.5 + abs(oy) * w + 0.01, abs(oy) * L * 0.5 + abs(ox) * w + 0.01, h * 0.42),
                  mat, tone=0.15)
        # Folded forelegs under the chest.
        for lat in (-0.45, 0.45):
            px = cx + ox * L * 0.62 + sy * lat * w * 1.2
            py = cy + oy * L * 0.62 + sx * lat * w * 1.2
            slab(m, px - r * 0.28, px + r * 0.28, py - r * 0.28, py + r * 0.28, z0, z0 + h * 0.35, mat,
                 tone=-0.2)
        hx, hy = cx + ox * L * 0.98, cy + oy * L * 0.98
        hz = z0 + h * 0.62
        if c.capital in ("bull", "protome"):
            ellipsoid(m, (hx, hy, hz), (r * 0.55 if ox else r * 0.5, r * 0.55 if oy else r * 0.5, h * 0.24), mat,
                      tone=0.25)
            # Horns curving forward and up, gilded.
            for lat in (-1, 1):
                bx, by = hx + sy * lat * r * 0.45, hy + sx * lat * r * 0.45
                rod(m, (bx - ox * r * 0.2, by - oy * r * 0.2, hz + h * 0.16),
                    (bx + ox * r * 0.25, by + oy * r * 0.25, hz + h * 0.36), max(r * 0.13, 0.35),
                    "gold" if paint else mat, tone=0.2)
                rod(m, (bx - ox * r * 0.35, by - oy * r * 0.35, hz + h * 0.1),
                    (bx + sy * lat * r * 0.3 - ox * r * 0.4, by + sx * lat * r * 0.3 - oy * r * 0.4, hz + h * 0.12),
                    max(r * 0.12, 0.3), mat)
        elif c.capital == "lion":
            ellipsoid(m, (hx, hy, hz), (r * 0.65, r * 0.65, h * 0.26), mat, tone=0.2)
            # Mane collar and open jaw.
            ellipsoid(m, (hx - ox * r * 0.3, hy - oy * r * 0.3, hz - h * 0.02), (r * 0.8, r * 0.8, h * 0.3), mat,
                      tone=-0.3)
            slab(m, hx + ox * r * 0.3 - r * 0.2, hx + ox * r * 0.3 + r * 0.2, hy + oy * r * 0.3 - r * 0.2,
                 hy + oy * r * 0.3 + r * 0.2, hz - h * 0.18, hz - h * 0.1, "cinnabar" if paint else mat)
        else:  # griffin: a beak, a crest and tall ears
            ellipsoid(m, (hx, hy, hz + h * 0.04), (r * 0.5, r * 0.5, h * 0.24), mat, tone=0.2)
            rod(m, (hx, hy, hz + h * 0.02), (hx + ox * r * 0.7, hy + oy * r * 0.7, hz - h * 0.1),
                max(r * 0.2, 0.4), "gold" if paint else mat)
            for lat in (-1, 1):
                bx, by = hx + sy * lat * r * 0.3, hy + sx * lat * r * 0.3
                rod(m, (bx, by, hz + h * 0.2), (bx - ox * r * 0.15, by - oy * r * 0.15, hz + h * 0.45),
                    max(r * 0.12, 0.3), mat)
        if paint:  # a painted eye
            ex, ey = hx + ox * r * 0.25, hy + oy * r * 0.25
            fill(m, (ex - r * 0.8, ex + r * 0.8, ey - r * 0.8, ey + r * 0.8, hz + h * 0.04, hz + h * 0.1),
                 "hair_black", lambda X, Y, Z: (np.hypot(X - ex, Y - ey) > r * 0.45) &
                 (np.hypot(X - ex, Y - ey) < r * 0.62), only_empty=False)
    # The saddle: a hollow between the necks where the beam end rests.
    slab(m, cx - r * 0.9, cx + r * 0.9, cy - r * 0.9, cy + r * 0.9, z0 + h * 0.2, z0 + h * 0.86, mat, tone=-0.1)


def column_grid(m, xs, ys, z0, c: Column):
    for x in xs:
        for y in ys:
            column(m, x, y, z0, c)


# ---------- roofs, beams, parapets ----------

def flat_roof(m, x0, x1, y0, y1, z, beam_dir="y", depth=4.0, beam_r=1.0, spacing=4.0,
              overhang=1.0, edge_mat="mudbrick", top_mat="mudbrick"):
    """A flat roof on cedar beams: beam ends show under a plastered fascia, packed earth on
    top. `z` is the underside of the beams."""
    # Main beams across the span, their round ends standing out of the walls.
    if beam_dir == "y":
        for bx in np.arange(x0 + spacing / 2, x1, spacing):
            slab(m, bx - beam_r, bx + beam_r, y0 - overhang, y1 + overhang, z, z + beam_r * 2, "cedar",
                 tone=lambda X, Y, Z: -0.4 * (np.abs(X % 1.0 - 0.5) < 0.12))
    else:
        for by in np.arange(y0 + spacing / 2, y1, spacing):
            slab(m, x0 - overhang, x1 + overhang, by - beam_r, by + beam_r, z, z + beam_r * 2, "cedar",
                 tone=lambda X, Y, Z: -0.4 * (np.abs(Y % 1.0 - 0.5) < 0.12))
    slab(m, x0, x1, y0, y1, z + beam_r * 2, z + depth - 0.6, edge_mat, tone=plaster_tone(13, 0.35))
    slab(m, x0 + 0.5, x1 - 0.5, y0 + 0.5, y1 - 0.5, z + depth - 0.6, z + depth, top_mat,
         tone=lambda X, Y, Z: (value_noise(X, Y, Z, 14.0, 17) - 0.5) * 0.3 - 0.7)


def merlons(m, x0, x1, y0, y1, z, height, material="limestone", pitch=None, sides=FACES, thick=None):
    """A parapet of Achaemenid stepped merlons (each a three-stepped tooth) on the rim of the
    rectangle at height z. `pitch` is the tooth spacing."""
    pitch = pitch or height * 1.2
    thick = thick or max(1.0, height * 0.32)

    def tooth(s):
        u = np.abs((s % pitch) - pitch / 2) / (pitch / 2)     # 0 at a tooth's centre
        steps = np.floor((1 - u) * 4.0) / 3.0                  # three steps up to the top
        return np.clip(steps, 0, 1) * height

    for face in sides:
        L = face_length(face, x0, x1, y0, y1)
        box = face_box(face, x0, x1, y0, y1, z, z + height, 0, L, 0, thick)

        def mask(X, Y, Z, face=face):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            return (Z - z) < np.maximum(tooth(s), height * 0.18)

        fill(m, box, material, mask, tone=lambda X, Y, Z: 0.2 * ((Z - z) % (height / 3) > height / 3 - 0.5))


def cornice(m, x0, x1, y0, y1, z, height, out, material="limestone", tone=0.0):
    """A cavetto ('gorge') cornice: a concave flare outward to `out` over `height`, a flat
    fillet on top; Egyptian in origin, the crown of every Pārsa door and window frame."""
    def mask(X, Y, Z):
        t = np.clip((Z - z) / height, 0, 1)
        flare = out * (1 - np.sqrt(np.clip(1 - t * t, 0, 1))) if True else 0
        flare = np.where(t > 0.85, out, flare)
        dx = np.maximum(np.maximum(x0 - X, X - x1), 0)
        dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
        return np.maximum(dx, dy) <= flare + 1e-3

    def tn(X, Y, Z):
        t = np.clip((Z - z) / height, 0, 1)
        base = tone(X, Y, Z) if callable(tone) else tone
        return base + 0.5 * (t > 0.85) - 0.3 * (t < 0.15) + 0.25 * (np.sin(t * 9) > 0.7)

    fill(m, (x0 - out, x1 + out, y0 - out, y1 + out, z, z + height), material, mask, tn)


# ---------- stone frames: doors, windows, niches ----------

def stone_frame(m, face, wall, s0, width, z0, height, kind="door", depth=None, leaf="gold",
                relief=None, frame_w=None, cornice_h=None, material="limestone"):
    """A monolithic stone door or window frame set in a wall box `wall` = (x0,x1,y0,y1,z0,z1)
    on `face`: jambs, lintel, a cavetto cornice, the opening recessed (a door leaf sheathed in
    gold or bronze foil, or a dark window). `relief(s, z)` may paint the jambs' inner faces.
    `kind` 'niche' is a blind window."""
    x0, x1, y0, y1, wz0, wz1 = wall
    fw = frame_w or max(1.0, width * 0.16)
    ch = cornice_h or max(1.5, height * 0.14)
    depth = depth if depth is not None else min(3.0, (x1 - x0 if face in ("+y", "-y") else y1 - y0) * 0.5)
    # The frame proud of the wall by a little.
    fb = face_box(face, x0, x1, y0, y1, z0, z0 + height + fw, s0 - fw, s0 + width + fw, -0.6, 1.0)
    fill(m, fb, material, tone=0.15)
    fl = _face_bounds(face, fb)
    cornice(m, *fl, z0 + height + fw, ch, 0.9, material, tone=0.1)
    if kind == "door":   # a gilded fillet along the cornice top of doorways
        fill(m, _grow(fb, 0.9, z0 + height + fw + ch - 0.6, z0 + height + fw + ch), "gold", tone=0.2)
    # The opening.
    ob = face_box(face, x0, x1, y0, y1, z0 + (0 if kind == "door" else 0.0), z0 + height,
                  s0, s0 + width, -0.7, depth)
    carve(m, ob)
    back = face_box(face, x0, x1, y0, y1, z0, z0 + height, s0, s0 + width, depth, depth + 0.6)
    if kind == "door":
        fill(m, back, leaf, tone=lambda X, Y, Z: 0.5 * (((Z - z0) % 3.0) < 0.5) - 0.2)
    elif kind == "window":
        fill(m, back, "polished", tone=-1.5)
    else:
        fill(m, back, material, tone=-0.5)
    if relief is not None:
        relief(m, face, ob, s0, width, z0, height, depth)


def _face_bounds(face, box):
    x0, x1, y0, y1, _z0, _z1 = box
    return x0, x1, y0, y1


def _grow(box, by, z0, z1):
    x0, x1, y0, y1, _a, _b = box
    return (x0 - by, x1 + by, y0 - by, y1 + by, z0, z1)


# ---------- reliefs ----------

ROBES = ("cinnabar", "lapis", "saffron", "purple", "malachite", "eblue")


def procession(m, face, wall, s0, s1, z0, z1, depth=0.6, ground="limestone", seed=0, spears=False,
               facing=1, period=None, colours=ROBES, kinds=("persian", "mede")):
    """A register of figures walking in profile along a face, in low relief and painted:
    robes in patterned reds, blues and yellows, beards and hair blue-black, gold details;
    the background stays polished stone. Figure height = z1 - z0."""
    x0, x1, y0, y1, _a, _b = wall
    H = z1 - z0
    period = period or H * 0.62
    fb = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, 0.0)

    def figure(s, z):
        i = np.floor((s - s0) / period).astype(np.int64)
        u = ((s - s0) % period) / period - 0.5            # -0.5..0.5 across the figure's cell
        if facing < 0:
            u = -u
        t = (z - z0) / H                                     # 0 feet .. 1 top
        kind = np.where(hash01(i, seed, 1) < 0.5, 0, 1) if len(kinds) > 1 else np.zeros_like(i)
        body = (t < 0.8) & (np.abs(u + 0.02) < 0.09 + 0.06 * (t < 0.45) * (kind == 0))
        head = ((u - 0.03) ** 2 / 0.005 + (t - 0.85) ** 2 / 0.005) < 1
        cap = (t > 0.88) & (t < 1.0) & (np.abs(u) < 0.07 + 0.02 * (kind == 1))
        beard = (t > 0.74) & (t < 0.84) & (u > 0.0) & (u < 0.1)
        arm = (t > 0.5) & (t < 0.56) & (u > 0.0) & (u < 0.22)
        spear = spears & (np.abs(u - 0.3) < 0.03) & (t < 1.05)
        legs = (kind == 1) & (t < 0.25) & (np.abs(u) < 0.09) & (np.abs(u) > 0.02)
        body = body & ~((kind == 1) & (t < 0.25) & (np.abs(u) < 0.02))
        return i, body | legs, head, cap, beard, arm, spear

    def mask(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        _i, body, head, cap, beard, arm, spear = figure(s, Z)
        return (body | head | cap | beard | arm | spear) & (d > -depth)

    def paint_into(material, sel):
        def mk(X, Y, Z):
            s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            return sel(figure(s, Z), s) & (d > -depth)
        fill(m, fb, material, mk, tone=0.2)

    fill(m, fb, ground, mask, tone=0.3)
    for ci, col in enumerate(colours):
        paint_into(col, lambda f, s, ci=ci: f[1] & (hash01(f[0], seed, 2) * len(colours) // 1 == ci))
    paint_into("hair_black", lambda f, s: f[4])
    paint_into("gold", lambda f, s: f[6])
    paint_into("felt", lambda f, s: f[3])


def rosette_band(m, face, wall, s0, s1, z0, z1, depth=0.4, material="limestone", petals="gold", step=None):
    """A border of 12-petalled rosettes in low relief."""
    x0, x1, y0, y1, _a, _b = wall
    H = z1 - z0
    step = step or H * 1.1
    fb = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, 0.0)

    def mask(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = ((s - s0) % step) - step / 2
        v = Z - (z0 + H / 2)
        return np.hypot(u, v * 1.0) < H * 0.42

    fill(m, fb, material, mask, tone=0.3)

    def centre(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = ((s - s0) % step) - step / 2
        v = Z - (z0 + H / 2)
        a = np.arctan2(v, u)
        r = np.hypot(u, v)
        return (r < H * 0.14) | ((r < H * 0.42) & (np.cos(a * 12) > 0.6) & (r > H * 0.25))

    fill(m, fb, petals, centre, tone=0.2)


def inscription(m, face, wall, s0, s1, z0, z1, depth=0.3, material="limestone"):
    """A cuneiform panel: dense rows of tiny wedges in a frame, never legible letters."""
    x0, x1, y0, y1, _a, _b = wall
    fb = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, 0.0)
    fill(m, fb, material, tone=0.35)

    def wedges(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        row = np.floor((Z - z0) / 0.75)
        col = np.floor((s - s0) / 0.6)
        h = hash01(row.astype(np.int64), col.astype(np.int64), 91)
        edge = (s - s0 < 0.6) | (s1 - s < 0.6) | (Z - z0 < 0.5) | (z1 - Z < 0.5)
        return (((Z - z0) % 0.75 < 0.35) & (h < 0.55) | edge) & (d < 0.05)

    fill(m, face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, -depth + 0.4), material, wedges,
         tone=-1.0)


def glazed_panel(m, face, wall, s0, s1, z0, z1, motif="rosettes", depth=0.3):
    """Glazed bricks proud of the wall: a blue ground with borders and a motif in yellow and
    white ('rosettes', 'triangles' or 'beasts': striding bulls and dragons in relief)."""
    x0, x1, y0, y1, _a, _b = wall
    fb = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, 0.2)
    H = z1 - z0
    fill(m, fb, "glaze_blue", tone=brick_tone(0.8, 1.6, 21))

    def border(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        return (Z - z0 < H * 0.12) | (z1 - Z < H * 0.12)

    fill(m, fb, "glaze_yellow", border, tone=lambda X, Y, Z: 0.4 * (((X + Y) % 2.0) < 1.0))

    if motif == "rosettes":
        def rose(X, Y, Z):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            step = H * 0.55
            u = ((s - s0) % step) - step / 2
            v = Z - (z0 + H / 2)
            r = np.hypot(u, v)
            return (r < H * 0.22) & ((np.cos(np.arctan2(v, u) * 8) > 0.2) | (r < H * 0.07))
        fill(m, fb, "white_paint", rose, tone=0.3)
    elif motif == "beasts":
        def beast(X, Y, Z):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            step = H * 1.1
            i = np.floor((s - s0) / step)
            u = ((s - s0) % step) / step
            t = (Z - z0) / H
            body = (np.abs(t - 0.52) < 0.13) & (u > 0.2) & (u < 0.75)
            legs = (t > 0.18) & (t < 0.42) & ((np.abs(u - 0.26) < 0.035) | (np.abs(u - 0.68) < 0.035))
            neck = (u > 0.7) & (u < 0.82) & (t > 0.5) & (t < 0.78)
            head = ((u - 0.84) ** 2 / 0.004 + (t - 0.76) ** 2 / 0.006) < 1
            horn = (i % 2 == 0) & (u > 0.8) & (u < 0.86) & (t > 0.78) & (t < 0.86)
            tail = (i % 2 == 1) & (u > 0.12) & (u < 0.22) & (np.abs(t - 0.62 - (0.22 - u) * 1.5) < 0.04)
            return body | legs | neck | head | horn | tail
        fill(m, fb, "glaze_yellow", beast, tone=0.5)
    else:
        def tri(X, Y, Z):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            u = ((s - s0) % (H * 0.5)) / (H * 0.5)
            t = (Z - z0) / H
            return (t > 0.2) & (t < 0.8) & (np.abs(u - 0.5) < (0.8 - t) * 0.6)
        fill(m, fb, "white_paint", tri, tone=0.3)


def cypress_band(m, face, wall, s0, s1, z0, z1, depth=0.5, material="limestone"):
    """A row of stylised cypress trees, the relief border between registers."""
    x0, x1, y0, y1, _a, _b = wall
    H = z1 - z0
    step = H * 0.5
    fb = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, 0.0)

    def tree(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = np.abs(((s - s0) % step) - step / 2)
        t = (Z - z0) / H
        return u < 0.22 * step * (1 - t) ** 0.7

    fill(m, fb, "malachite", tree, tone=0.0)
    fill(m, fb, material, lambda X, Y, Z: (Z - z0) < H * 0.08, tone=0.2)


def lion_bull(m, face, wall, s0, s1, z0, z1, depth=0.7, flip=False):
    """The stair-triangle emblem: a lion leaping onto a bull's back from behind."""
    x0, x1, y0, y1, _a, _b = wall
    fb = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -depth, 0.0)
    W, H = s1 - s0, z1 - z0

    def parts(X, Y, Z):
        s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = (s - s0) / W
        if flip:
            u = 1 - u
        t = (Z - z0) / H
        bull = ((u - 0.6) ** 2 / 0.06 + (t - 0.42) ** 2 / 0.04 < 1) | \
            ((t < 0.3) & ((np.abs(u - 0.45) < 0.03) | (np.abs(u - 0.78) < 0.03))) | \
            (((u - 0.86) ** 2 / 0.01 + (t - 0.62) ** 2 / 0.02) < 1)
        lion = ((u - 0.36) ** 2 / 0.04 + (t - 0.66) ** 2 / 0.02 < 1) | \
            (((u - 0.5) ** 2 / 0.008 + (t - 0.78) ** 2 / 0.015) < 1) | \
            ((np.abs(u - 0.22) < 0.03) & (t > 0.3) & (t < 0.62))
        return bull, lion

    fill(m, fb, "limestone", lambda X, Y, Z: parts(X, Y, Z)[0], tone=0.35)
    fill(m, fb, "saffron", lambda X, Y, Z: parts(X, Y, Z)[1], tone=0.1)


# ---------- walls ----------

def mudbrick_wall(m, x0, x1, y0, y1, z0, z1, plinth=None, material="mudbrick", plinth_mat="ashlar",
                  seed=7, dado=None):
    """A thick plastered mudbrick wall on a dressed stone plinth; `dado` paints a band of
    `(height, material)` at the foot of the plaster."""
    plinth = plinth if plinth is not None else min(2.0, (z1 - z0) * 0.12)
    if plinth > 0:
        slab(m, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, z0, z0 + plinth, plinth_mat,
             tone=ashlar_tone(plinth, 5.0, seed))
    slab(m, x0, x1, y0, y1, z0 + plinth, z1, material, tone=plaster_tone(seed))
    if dado:
        h, mat = dado
        slab(m, x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, z0 + plinth, z0 + plinth + h, mat,
             tone=plaster_tone(seed + 1, 0.3))


def stair(m, x0, x1, y0, y1, z0, z1, up, step=None, material="limestone", parapet=0.0, par_h=2.0,
          par_mat=None):
    """A straight flight rising `up` ('+x', '-x', '+y', '-y') from z0 to z1 over the box, with
    a step line every `step` design units of rise and optional side parapets."""
    step = step or 0.75
    along_x = up in ("+x", "-x")
    lo, hi = (x0, x1) if along_x else (y0, y1)
    sign = 1 if up[0] == "+" else -1
    par_mat = par_mat or material

    def frac(X, Y):
        a = X if along_x else Y
        f = (a - lo) / (hi - lo)
        return f if sign > 0 else 1 - f

    def mask(X, Y, Z):
        f = np.clip(frac(X, Y), 0, 1)
        top = z0 + (z1 - z0) * f
        return Z < np.ceil((top - z0) / step) * step + z0

    def tone(X, Y, Z):
        f = np.clip(frac(X, Y), 0, 1)
        top = np.ceil(((z0 + (z1 - z0) * f) - z0) / step) * step + z0
        return 0.45 * (top - Z < 0.5) - 0.4 * (top - Z > step * 0.6) * (top - Z < step)

    fill(m, (x0, x1, y0, y1, z0, z1 + step), material, mask, tone)
    if parapet > 0:
        for side in (0, 1):
            if along_x:
                b = (x0, x1, y0, y0 + parapet) if side == 0 else (x0, x1, y1 - parapet, y1)
            else:
                b = (x0, x0 + parapet, y0, y1) if side == 0 else (x1 - parapet, x1, y0, y1)

            def pm(X, Y, Z):
                f = np.clip(frac(X, Y), 0, 1)
                return Z < z0 + (z1 - z0) * f + par_h + step
            fill(m, (*b, z0, z1 + par_h + step), par_mat, pm, tone=0.25)


def tent(m, x0, x1, y0, y1, z0, h, cloth="wool", stripe=None, ridge="x", door_face=None):
    """A wool tent: a ridge on poles, sloping sides, a dark doorway."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def mask(X, Y, Z):
        if ridge == "x":
            u = np.abs(Y - cy) / ((y1 - y0) / 2)
        else:
            u = np.abs(X - cx) / ((x1 - x0) / 2)
        top = z0 + h * (1 - u) ** 0.9
        return (Z < top) & (Z > top - 0.9)

    def tone(X, Y, Z):
        base = 0.0
        if stripe:
            a = X if ridge == "y" else Y
            base += 0.0 * a
        return base + plaster_tone(31, 0.4)(X, Y, Z)

    fill(m, (x0, x1, y0, y1, z0, z0 + h), cloth, mask, tone)
    if stripe:
        def st(X, Y, Z):
            return mask(X, Y, Z) & ((Z - z0) % (h / 3.0) < 0.8)
        fill(m, (x0, x1, y0, y1, z0, z0 + h), stripe, st, tone=0.1)
    if ridge == "x":
        rod(m, (x0 - 0.5, cy, z0 + h), (x1 + 0.5, cy, z0 + h), 0.35, "wood")
    else:
        rod(m, (cx, y0 - 0.5, z0 + h), (cx, y1 + 0.5, z0 + h), 0.35, "wood")
    if door_face:
        b = face_box(door_face, x0, x1, y0, y1, z0, z0 + h * 0.6, face_length(door_face, x0, x1, y0, y1) * 0.38,
                     face_length(door_face, x0, x1, y0, y1) * 0.62, -0.2, 3.0)
        fill(m, b, "ink", lambda X, Y, Z: mask(X, Y, Z) | True, only_empty=False, tone=0.0)


def awning(m, x0, x1, y0, y1, z, cloth="linen", poles=True, sag=0.6):
    """A flat cloth or reed-mat awning on four poles."""
    if poles:
        for px, py in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
            rod(m, (px, py, 0), (px, py, z), 0.35, "wood")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    fill(m, (x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, z - sag - 0.8, z + 0.6), cloth,
         lambda X, Y, Z: np.abs(Z - (z - sag * (1 - ((X - cx) / ((x1 - x0) / 2)) ** 2) *
                                     (1 - ((Y - cy) / ((y1 - y0) / 2)) ** 2))) < 0.45,
         tone=lambda X, Y, Z: 0.3 * ((X + Y) % 2.0 < 0.6) - 0.1)


def pixels(m: Model, x, y, z):
    """Screen offset (px) of a model point from the anchor: emitters and spots."""
    k = m.k
    return [int(round((x - y) * k)), int(round(((x + y) / 2 - z) * k))]


def circle_pts(cx, cy, r, n):
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
