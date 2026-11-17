"""Greek architecture for big voxel models, reusable by every set with Greek or Roman building
(athens.md §3.1): the Doric and Ionic orders as parameters, crepidomas, marble ashlar with
orthostates, the Doric frieze of triglyphs and metopes, the Ionic frieze, geisa, pediments with
sculpture, akroteria, antefixes, tiled roofs (marble or terracotta, Corinthian or Laconian),
conical and pyramidal roofs, whole temples (peripteral, prostyle, in antis), stoas, statues
on the walker rig, herms, stelai, statue bases, vases, and painted mouldings.

Units and axes follow `arch` (design units in grid axes: +x south, +y west, z up; faces named
by their outward normal; `s` runs along a face left to right seen from outside). An `Order`
is written in metres and drawn at a landmark `Scale`. Everything draws through `arch.fill`, so
a builder can call it for the whole building on any chunk (`bigrender`).

Colour follows the evidence for painted Classical marble: the shafts, walls and architraves
stay marble with a warm wax tone; triglyphs and regulae are blue-black; taeniae, the frieze
crown and mouldings carry red, blue and green (egg-and-dart, leaf, meander); metope and frieze
grounds and the tympanum are blue; sculpture is painted with gilded bronze attachments.
"""

import math
from dataclasses import dataclass, field, replace
from functools import lru_cache

import numpy as np

import materials as M
import relief as R
import relief_greek as G
import rig
from arch import FACES, Scale, carve, ellipsoid, face_box, face_frame, face_length, fill, halo, revolve, rod, slab
from palette import MAT
from voxel import Model, hash01, value_noise

# ---------------------------------------------------------------- orders


@dataclass(frozen=True)
class Order:
    """A column order in metres. `H` is the column with its capital; the entablature is
    architrave + frieze + geison."""
    kind: str = "doric"               # doric | ionic
    D: float = 1.9                    # lower diameter
    H: float = 10.4
    upper: float = 0.79               # upper / lower diameter
    flutes: int = 20
    entasis: float = 0.02             # swelling at about 2/5 height, fraction of D
    arch_h: float = 1.35
    frieze_h: float = 1.35
    geison_h: float = 0.62
    geison_out: float = 0.85
    material: str = "marble"

    def r(self, S: Scale):
        return S.h(self.D) / 2

    def entablature(self, S: Scale):
        return S.v(self.arch_h + self.frieze_h + self.geison_h)


def _shaft_radius(o: Order, S: Scale, z0, z1):
    r0 = o.r(S)

    def radius(t):
        return r0 * (1 - (1 - o.upper) * t) + r0 * 2 * o.entasis * np.clip(np.sin(np.pi * np.clip(t / 0.8, 0, 1)), 0, 1) ** 1.5
    return radius


def column(m, cx, cy, z0, o: Order, S: Scale, finish="full", face="y", drums=0, seed=0, paint=True):
    """One column standing at (cx, cy) on z0. `finish`: 'full'; 'unfluted' (flutes begun only
    at the foot and under the capital, as unfinished columns were fluted after erection);
    'bosses' (unfluted with lifting bosses left on the drums: the Propylaia, 432);
    'drums' (`drums` drums only, no capital: a building site). Ionic volutes face along
    `face` ('x' or 'y')."""
    H = S.v(o.H)
    r0 = o.r(S)
    mat = o.material
    if o.kind == "ionic":
        return _ionic(m, cx, cy, z0, o, S, H, r0, mat, face, paint)
    cap_h = S.v(o.D * 0.45)
    zs1 = z0 + H - cap_h
    if finish == "drums":
        zs1 = z0 + drums * S.v(1.2)
    radius = _shaft_radius(o, S, z0, zs1)
    nfl = o.flutes

    def flute_phase(X, Y):
        a = np.arctan2(Y - cy, X - cx)
        return a, (a * nfl / (2 * np.pi)) % 1.0

    fluted = finish == "full"

    def mask(X, Y, Z):
        t = np.clip((Z - z0) / (H - cap_h), 0, 1)
        rr = np.hypot(X - cx, Y - cy)
        lim = radius(t)
        if fluted and m.fine:
            _a, f = flute_phase(X, Y)
            lim = lim - 0.28 * (1 - (2 * f - 1) ** 2)
        return rr <= lim

    def nrm(X, Y, Z):
        a, f = flute_phase(X, Y)
        if not fluted:
            return (np.cos(a), np.sin(a), Z * 0.0)
        tilt = (f - 0.5) * 1.3              # the concave flute turns its sides to and from the sun
        return (np.cos(a - tilt), np.sin(a - tilt), Z * 0.0)

    def tone(X, Y, Z):
        a, f = flute_phase(X, Y)
        t = 0.0
        if fluted:
            t = 0.35 * (f < 0.1) + 0.15 * (f > 0.9)
        else:
            t = (value_noise(X * 2, Y * 2, Z, 3.0, seed + 5) - 0.5) * 0.3
        # Drum joints, faint on finished work, plain on unfinished.
        dz = (Z - z0) % S.v(1.2)
        t = t - (0.55 if not fluted else 0.18) * (dz < 0.35)
        return t
    rmax = r0 * (1 + 2 * o.entasis) + 0.2
    fill(m, (cx - rmax, cx + rmax, cy - rmax, cy + rmax, z0, zs1), mat, mask, tone, nrm)
    if finish == "unfluted":    # flutes started at the foot and the top
        for za, zb in ((z0, z0 + S.v(0.4)), (zs1 - S.v(0.5), zs1)):
            fill(m, (cx - rmax, cx + rmax, cy - rmax, cy + rmax, za, zb), mat,
                 lambda X, Y, Z: np.hypot(X - cx, Y - cy) <= radius(np.clip((Z - z0) / (H - cap_h), 0, 1)),
                 lambda X, Y, Z: 0.35 * (flute_phase(X, Y)[1] < 0.15) - 0.2)
    if finish in ("bosses", "drums"):
        # Lifting bosses: small square lugs left on two sides of each drum.
        nd = int((zs1 - z0) // S.v(1.2))
        for i in range(nd):
            zb = z0 + (i + 0.5) * S.v(1.2)
            for ang in (0.3 + seed * 0.7, 0.3 + seed * 0.7 + np.pi):
                bx, by = cx + math.cos(ang) * (r0 + 0.3), cy + math.sin(ang) * (r0 + 0.3)
                fill(m, (bx - 0.8, bx + 0.8, by - 0.8, by + 0.8, zb - 0.9, zb + 0.9), mat, tone=-0.1)
    if finish == "drums":
        return zs1
    # Necking groove, annulets, echinus, abacus.
    rt = radius(1.0)
    fill(m, (cx - rt - 0.1, cx + rt + 0.1, cy - rt - 0.1, cy + rt + 0.1, zs1 - S.v(0.5), zs1 - S.v(0.5) + 0.5), mat,
         lambda X, Y, Z: np.hypot(X - cx, Y - cy) <= rt + 0.05, -0.9, lambda X, Y, Z: (X - cx, Y - cy, Z * 0))
    ann = cap_h * 0.18
    revolve(m, cx, cy, zs1, zs1 + ann, lambda t: rt * (1.02 + 0.03 * t), mat,
            tone=lambda X, Y, Z: 0.3 * (((Z - zs1) * 2 / max(ann, 0.5)) % 1.0 < 0.5) - 0.2)
    if paint:   # one thin painted ring under the echinus
        fill(m, (cx - rt * 1.2, cx + rt * 1.2, cy - rt * 1.2, cy + rt * 1.2, zs1 + ann - 0.5, zs1 + ann), "cinnabar",
             tone=-0.2, only_solid=True)
    ze = zs1 + ann
    ech = cap_h * 0.42
    revolve(m, cx, cy, ze, ze + ech, lambda t: rt * (1.03 + 0.52 * np.sin(t * np.pi / 2) ** 0.8), mat, tone=0.1)
    ab = (o.D * 1.07) * S.h(1) / 2
    za = ze + ech
    slab(m, cx - ab, cx + ab, cy - ab, cy + ab, za, z0 + H, mat, tone=lambda X, Y, Z: 0.25 * (Z > z0 + H - 0.6) - 0.05)
    return z0 + H


def _ionic(m, cx, cy, z0, o, S, H, r0, mat, face, paint):
    """An Ionic column: Attic base (torus, scotia, torus), 24 flutes with flat fillets, a
    capital of volutes over an egg-and-dart echinus, a thin abacus."""
    bh = S.v(o.D * 0.5)
    revolve(m, cx, cy, z0, z0 + bh * 0.4, lambda t: r0 * (1.45 - 0.05 * t), mat, tone=0.15)
    revolve(m, cx, cy, z0 + bh * 0.4, z0 + bh * 0.62, lambda t: r0 * (1.15 + 0.15 * (2 * t - 1) ** 2), mat, tone=-0.5)
    revolve(m, cx, cy, z0 + bh * 0.62, z0 + bh, lambda t: r0 * (1.28 - 0.18 * t), mat, tone=0.2)
    cap_h = S.v(o.D * 0.55)
    zs0, zs1 = z0 + bh, z0 + H - cap_h
    nfl = o.flutes

    def tone(X, Y, Z):
        f = (np.arctan2(Y - cy, X - cx) * nfl / (2 * np.pi)) % 1.0
        return 0.3 * (f < 0.2) - 0.15 * ((f > 0.4) & (f < 0.8))

    def nrm(X, Y, Z):
        a = np.arctan2(Y - cy, X - cx)
        f = (a * nfl / (2 * np.pi)) % 1.0
        tilt = np.where(f < 0.2, 0.0, (f - 0.6) * 1.4)
        return (np.cos(a - tilt), np.sin(a - tilt), Z * 0)
    rt = r0 * o.upper
    fill(m, (cx - r0, cx + r0, cy - r0, cy + r0, zs0, zs1), mat,
         lambda X, Y, Z: np.hypot(X - cx, Y - cy) <= r0 - (r0 - rt) * np.clip((Z - zs0) / (zs1 - zs0), 0, 1), tone, nrm)
    # Echinus with egg-and-dart, painted.
    revolve(m, cx, cy, zs1, zs1 + cap_h * 0.35, lambda t: rt * (1.0 + 0.25 * t), mat, tone=0.1)
    if paint:
        fill(m, (cx - rt * 1.4, cx + rt * 1.4, cy - rt * 1.4, cy + rt * 1.4, zs1, zs1 + cap_h * 0.35), "eblue",
             lambda X, Y, Z: (np.arctan2(Y - cy, X - cx) * 8 / np.pi) % 1.0 < 0.35, tone=0.1, only_solid=True)
    # The volute member: a cushion across, a spiral on each end face.
    zv0, zv1 = zs1 + cap_h * 0.25, z0 + H - cap_h * 0.12
    along_x = face == "y"            # the volutes are seen on the faces normal to `face`
    lx, ly = (r0 * 1.75, r0 * 0.9) if along_x else (r0 * 0.9, r0 * 1.75)
    fill(m, (cx - lx, cx + lx, cy - ly, cy + ly, zv0, zv1), mat,
         lambda X, Y, Z: True, tone=0.1)
    vr = (zv1 - zv0) * 0.62

    def spiral(X, Y, Z):
        s = (X - cx) if along_x else (Y - cy)
        side = np.sign(s)
        u = np.abs(s) - (lx - vr)
        v = Z - (zv1 - vr)
        rr = np.hypot(u, v)
        a = np.arctan2(v, u)
        coil = ((rr / vr * 2.2 + a / (2 * np.pi)) % 1.0) < 0.45
        return (rr < vr) & coil & (side != 0)
    for d in (-1, 1):
        if along_x:
            box = (cx - lx - 0.2, cx + lx + 0.2, cy + d * ly - 0.6, cy + d * ly + 0.6, zv0 - vr * 0.6, zv1)
        else:
            box = (cx + d * lx - 0.6, cx + d * lx + 0.6, cy - ly - 0.2, cy + ly + 0.2, zv0 - vr * 0.6, zv1)
        fill(m, box, mat, lambda X, Y, Z: (np.hypot(np.abs((X - cx) if along_x else (Y - cy)) - (lx - vr),
                                                     Z - (zv1 - vr)) < vr), tone=0.2)
        fill(m, box, mat, spiral, tone=-0.7, only_solid=True)
    slab(m, cx - lx * 0.95, cx + lx * 0.95, cy - ly * 1.05, cy + ly * 1.05, zv1, z0 + H, mat, tone=0.3)
    return z0 + H


# ---------------------------------------------------------------- painted mouldings

# Motifs: f(u, v) on a band, u along it and v down from its top, both in voxels; returns an
# integer colour index (0, 1, 2 ...) or -1 for the ground left as it is.
MEANDER = ("XXXXX..", "....X..", "XXX.X..", "X...X..", "XXXXXXX")


def _motif(kind, u, v, h):
    u = np.floor(u).astype(np.int64)
    v = np.floor(v).astype(np.int64)
    if kind == "meander":
        rows = np.array([[c == "X" for c in r] for r in MEANDER])
        H, W = rows.shape
        vv = np.clip(((v - (h - H) // 2)), 0, H - 1)
        inside = (v - (h - H) // 2 >= 0) & (v - (h - H) // 2 < H)
        return np.where(inside & rows[vv, u % W], 0, -1)
    if kind == "egg_dart":      # eggs (colour 0) with darts between (colour 1)
        p = u % 4
        return np.where((p < 3) & (v > 0) & (v < h - 1) | (p < 3) & (h <= 2), 0, np.where(p == 3, 1, -1))
    if kind == "leaf":           # Lesbian leaf / hawksbeak: alternating coloured tongues
        p = u % 6
        tongue = np.abs(p - 2.5) <= 2.5 - (v / max(h, 1)) * 2.0
        return np.where(tongue, (u // 3) % 2, -1)
    if kind == "beads":
        p = u % 3
        return np.where(p < 2, 0, 1)
    if kind == "palmette":       # palmettes (0) alternating with lotus (1) over a line (2)
        p = u % 8
        fan = (np.abs(p - 3.5) <= (h - v) * 0.6) & (v < h - 1)
        rib = fan & (((p - 3.5) * 2 + v) % 2 < 1)
        return np.where(v == h - 1, 2, np.where(fan, np.where((u // 8) % 2 == 0, np.where(rib, 1, 0), 1), -1))
    if kind == "stripes":
        return (v * 0 + (u // 4) % 2)
    if kind == "dots":
        return np.where((u % 3 == 1) & (v % 3 == 1), 0, -1)
    return np.zeros_like(u)


def paint_band(m, face, wall, z0, z1, motif, colours, out=0.6, deep=0.6, s0=0.0, s1=None, k=2):
    """Paint a motif on the existing surface of `face` of the box `wall` between z0 and z1."""
    x0, x1, y0, y1 = wall[:4]
    L = face_length(face, x0, x1, y0, y1)
    s1 = L if s1 is None else s1
    h = int(round((z1 - z0) * k))
    box = face_box(face, x0, x1, y0, y1, z0, z1, s0, s1, -out, deep)
    for i, col in enumerate(colours):
        def mask(X, Y, Z, i=i):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            return _motif(motif, (s - s0) * k, (z1 - Z) * k, h) == i
        fill(m, box, col, mask, tone=0.1, only_solid=True)


def paint_ring(m, box, z0, z1, motif, colours, out=0.6, deep=0.6, sides=FACES):
    for face in sides:
        paint_band(m, face, box, z0, z1, motif, colours, out, deep)


# ---------------------------------------------------------------- platforms and walls

def crepidoma(m, x0, x1, y0, y1, z0, steps, tread, material="marble", seed=1, sides=FACES):
    """A stepped platform: `steps` = [rise, ...] from the bottom, each step set in by `tread`
    on `sides`. Returns (stylobate box, top z). The treads are lit, the risers carry fine joints."""
    z = z0
    bx = [x0, x1, y0, y1]
    for i, rise in enumerate(steps):
        slab(m, bx[0], bx[1], bx[2], bx[3], z, z + rise, material,
             tone=M.plus(M.ashlar(rise, 7.0, seed + i, joint=0.25, spread=0.3), lambda X, Y, Z: 0.35 * (Z > z + rise - 0.6)))
        if "-x" in sides:
            bx[0] += tread
        if "+x" in sides:
            bx[1] -= tread
        if "-y" in sides:
            bx[2] += tread
        if "+y" in sides:
            bx[3] -= tread
        z += rise
    return tuple(bx), z


def marble_wall(m, x0, x1, y0, y1, z0, z1, material="marble", course=2.6, seed=3, orthostate=5.0, toichobate=1.2):
    """Isodomic marble masonry: a projecting foot course (toichobate), a course of tall
    orthostates, then equal courses with near-invisible joints and a warm patina darker low."""
    if toichobate:
        slab(m, x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, z0, z0 + toichobate, material,
             tone=lambda X, Y, Z: 0.3 * (Z > z0 + toichobate - 0.5) - 0.1)
    za = z0 + toichobate
    if orthostate:
        slab(m, x0, x1, y0, y1, za, za + orthostate, material,
             tone=M.ashlar(orthostate, 9.0, seed, joint=0.22, spread=0.25, odd=0.05))
        za += orthostate
    slab(m, x0, x1, y0, y1, za, z1, material,
         tone=M.plus(M.ashlar(course, 6.5, seed + 1, joint=0.2, spread=0.22, odd=0.06),
                     lambda X, Y, Z: -0.25 * np.clip(1 - (Z - z0) / 30.0, 0, 1)))


def poros_wall(m, x0, x1, y0, y1, z0, z1, seed=5, course=2.4, material="poros"):
    slab(m, x0, x1, y0, y1, z0, z1, material, tone=M.ashlar(course, 5.5, seed, joint=0.35, spread=0.8, odd=0.2))


def house_wall(m, x0, x1, y0, y1, z0, z1, seed=7, socle=3.0, plaster="whitewash", socle_mat="poros"):
    """A house wall: a rubble socle of stone, plastered mudbrick above (whitewashed or left
    earth-coloured), patched, with a damp foot."""
    if socle:
        slab(m, x0 - 0.25, x1 + 0.25, y0 - 0.25, y1 + 0.25, z0, z0 + socle, socle_mat,
             tone=M.ashlar(1.4, 2.6, seed, joint=0.4, spread=1.1, polygonal=0.8, odd=0.3))
    slab(m, x0, x1, y0, y1, z0 + socle, z1, plaster, tone=M.mud_plaster(seed, 0.5, z0 + socle, 2.0))


# ---------------------------------------------------------------- the Doric entablature

def triglyph_axes(axes, lo, hi, tw):
    """Triglyph centres along one face: over every column axis and every midpoint, the two
    end ones pushed out to the corners (the Doric corner)."""
    out = []
    for i, a in enumerate(axes):
        out.append(a)
        if i + 1 < len(axes):
            out.append((a + axes[i + 1]) / 2)
    if out:
        out[0] = lo + tw / 2
        out[-1] = hi - tw / 2
    return out


def doric_entablature(m, box, z, o: Order, S: Scale, axes_x, axes_y, metopes=None, faces=FACES, paint=True,
                      geison=True, seed=11, metope_ground="eblue", depth=None):
    """The entablature over a rectangle of columns: `box` = (x0, x1, y0, y1) is the architrave's
    outer face; axes_x / axes_y the column axes along x (faces ±y) and along y (faces ±x).
    `metopes(face, i, w, h)` returns an (image, cmap) for metope i of a face or None. Returns
    the top of the geison."""
    x0, x1, y0, y1 = box
    mat = o.material
    A, F, Gh = S.v(o.arch_h), S.v(o.frieze_h), S.v(o.geison_h)
    th = depth or S.h(o.D) * 1.1
    # Architrave (a ring of beams), its face in three fasciae for Ionic, plain for Doric.
    for face in FACES:
        fill(m, face_box(face, x0, x1, y0, y1, z, z + A, 0, face_length(face, x0, x1, y0, y1), 0, th), mat,
             tone=M.plus(M.ashlar(A, 11.0, seed, joint=0.2, spread=0.15, odd=0.0),
                         lambda X, Y, Z: -0.15 * (Z < z + 1.0)))
    tw = S.h(0.84)
    zt = z + A
    # Taenia: the fillet along the architrave top, projecting, painted red.
    slab(m, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, zt - 0.6, zt, mat, tone=0.3)
    if paint:
        paint_ring(m, (x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3), zt - 0.6, zt, "stripes", ["cinnabar", "cinnabar"],
                   sides=faces)
    # Frieze backer, metope plane set back a little.
    inset = 0.5
    fb = (x0 + inset, x1 - inset, y0 + inset, y1 - inset)
    for face in FACES:
        fill(m, face_box(face, *fb, zt, zt + F, 0, face_length(face, *fb), 0, th - inset), mat, tone=0.0)
    for face in faces:
        axes = axes_y if face in ("+x", "-x") else axes_x
        lo_hi = (y0, y1) if face in ("+x", "-x") else (x0, x1)
        L = face_length(face, x0, x1, y0, y1)
        cents = triglyph_axes(sorted(axes), lo_hi[0], lo_hi[1], tw)
        # Convert axis coordinates to s along the face (s grows right seen from outside).
        def to_s(c):
            if face == "+x":
                return y1 - c
            if face == "-x":
                return c - y0
            if face == "+y":
                return c - x0
            return x1 - c
        ss = sorted(to_s(c) for c in cents)
        # Metopes between triglyphs: painted ground, figures in relief.
        if paint:
            fill(m, face_box(face, *fb, zt, zt + F - 0.8, 0, face_length(face, *fb), -0.05, 0.4), metope_ground,
                 tone=-0.1, only_solid=True)
        for i in range(len(ss) - 1):
            a, b = ss[i] + tw / 2, ss[i + 1] - tw / 2
            if metopes is not None and b - a > 1.5:
                pic = metopes(face, i, int(round((b - a) * 2)), int(round((F - 1.0) * 2)))
                if pic is not None:
                    img, cmap = pic
                    R.emboss(m, face, (*fb, 0, 0), a - inset + (0 if face in ("+y", "-x") else 0),
                             zt + F - 0.8, img, cmap=cmap, depth=1)
        # Triglyphs: blocks to the architrave face, blue-black, two glyphs and two half glyphs.
        for sc in ss:
            def glyph(X, Y, Z, sc=sc):
                s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
                u = (s - (sc - tw / 2)) / tw * 6.0       # six strips across
                ch = ((u > 0.5) & (u < 1.5)) | ((u > 2.5) & (u < 3.5)) | ((u > 4.5) & (u < 5.5))
                return -0.9 * (ch & (Z < zt + F - 1.2)) + 0.25 * (Z > zt + F - 1.0)
            fill(m, face_box(face, x0, x1, y0, y1, zt, zt + F, sc - tw / 2, sc + tw / 2, 0, inset + 0.1),
                 "triglyph" if paint else mat, tone=glyph)
            # Regula with its guttae on the architrave under each triglyph.
            fill(m, face_box(face, x0, x1, y0, y1, zt - 1.1, zt - 0.6, sc - tw / 2, sc + tw / 2, -0.35, 0.1),
                 "triglyph" if paint else mat, tone=0.0)
            fill(m, face_box(face, x0, x1, y0, y1, zt - 1.6, zt - 1.1, sc - tw / 2, sc + tw / 2, -0.35, 0.1),
                 "triglyph" if paint else mat,
                 lambda X, Y, Z, sc=sc: ((face_frame(face, X, Y, Z, x0, x1, y0, y1)[0] - sc) * 2 % 1.2 < 0.6), tone=0.2)
    zf = zt + F
    # Frieze crown, painted.
    slab(m, x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2, zf - 0.8, zf, mat, tone=0.25)
    if paint:
        paint_ring(m, (x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2), zf - 0.8, zf, "egg_dart", ["cinnabar", "eblue"],
                   sides=faces)
    if not geison:
        return zf
    return geison_ring(m, box, zf, Gh, S.h(o.geison_out), mat, faces, paint)


def geison_ring(m, box, z, h, out, mat="marble", faces=FACES, paint=True, soffit_paint=True):
    """The horizontal cornice: a slab projecting `out` beyond the box with a sloping soffit (its
    mutules painted blue, seen as a dark drip line), a vertical face with a painted
    hawksbeak along its top."""
    x0, x1, y0, y1 = box
    slab(m, x0 - out, x1 + out, y0 - out, y1 + out, z + h * 0.35, z + h, mat, tone=0.15)
    slab(m, x0 - out * 0.5, x1 + out * 0.5, y0 - out * 0.5, y1 + out * 0.5, z, z + h * 0.35, mat, tone=-0.3)
    if soffit_paint and paint:
        fill(m, (x0 - out * 0.55, x1 + out * 0.55, y0 - out * 0.55, y1 + out * 0.55, z, z + h * 0.35), "triglyph",
             lambda X, Y, Z: np.maximum(np.maximum(x0 - X, X - x1), np.maximum(y0 - Y, Y - y1)) > out * 0.2,
             tone=0.0, only_solid=True)
    if paint:
        paint_ring(m, (x0 - out, x1 + out, y0 - out, y1 + out), z + h - 1.0, z + h, "leaf", ["cinnabar", "eblue"],
                   sides=faces)
    return z + h


def ionic_frieze(m, face, wall, s0, s1, z_top, h, subject="procession", seed=0, ground="eblue", depth=1):
    """A continuous figured frieze along a face (painted relief on a blue ground)."""
    x0, x1, y0, y1 = wall[:4]
    fill(m, face_box(face, x0, x1, y0, y1, z_top - h, z_top, s0, s1, -0.05, 0.45), ground, tone=-0.15,
         only_solid=True)
    W, Hh = int(round((s1 - s0) * 2)), int(round(h * 2))
    if W < 4 or Hh < 4:
        return
    img, cmap = G.frieze_image(W, Hh, subject, seed)
    R.emboss(m, face, wall, s0, z_top, img, cmap=cmap, depth=depth)


# ---------------------------------------------------------------- pediments, akroteria, roofs

def pediment(m, face, x0, x1, y0, y1, z, rise, o: Order, S: Scale, subject=None, ground="lapis", paint=True,
             recess=None, akroteria="floral", sima=True):
    """A pediment on `face` ('+y' or '-y' with the ridge along y; '+x'/'-x' with it along x) of
    the box `x0..x1, y0..y1` (the geison's outer line), from z (the horizontal geison top) up
    by `rise` at the centre: the tympanum recessed by `recess`, its ground painted, sculpture
    in high relief standing on the floor, the raking geison and a painted raking sima, and
    akroteria at the apex and the corners."""
    mat = o.material
    along_y = face in ("+y", "-y")
    lo, hi = (x0, x1) if along_y else (y0, y1)
    half = (hi - lo) / 2
    c = lo + half
    recess = recess if recess is not None else S.h(0.8)
    gh = S.v(o.geison_h)
    # The pediment block: a triangular prism a few units deep behind the face.
    D = S.h(2.2)
    if along_y:
        yf = y1 if face == "+y" else y0
        sgn = 1 if face == "+y" else -1
        box = (x0, x1, min(yf, yf - sgn * D), max(yf, yf - sgn * D), z, z + rise + gh + 3.0)
    else:
        xf = x1 if face == "+x" else x0
        sgn = 1 if face == "+x" else -1
        box = (min(xf, xf - sgn * D), max(xf, xf - sgn * D), y0, y1, z, z + rise + gh + 3.0)

    def across(X, Y):
        return np.abs((X if along_y else Y) - c)

    def depth_in(X, Y):
        return sgn * ((yf - Y) if along_y else (xf - X))

    def top(X, Y):
        return z + rise * (1 - across(X, Y) / half)

    # Tympanum wall (recessed) and the raking geison along the slopes.
    fill(m, box, mat, lambda X, Y, Z: (Z < top(X, Y)) & (depth_in(X, Y) >= recess), tone=0.05)
    fill(m, box, mat, lambda X, Y, Z: (Z >= top(X, Y) - gh * 0.9) & (Z < top(X, Y) + gh * 0.25) & (depth_in(X, Y) >= -0.3),
         tone=lambda X, Y, Z: 0.3 * (Z > top(X, Y)) - 0.1)
    if paint:
        fill(m, box, ground, lambda X, Y, Z: (Z < top(X, Y) - gh * 0.9) & (depth_in(X, Y) < recess + 0.6), tone=-0.1,
             only_solid=True)
        fill(m, box, "triglyph", lambda X, Y, Z: (Z >= top(X, Y) - gh * 0.9) & (Z < top(X, Y) - gh * 0.55) &
             (depth_in(X, Y) < 0.8), tone=0.0, only_solid=True)
    # Sculpture in the recess, embossed on the tympanum wall and standing on the floor.
    if subject:
        L = hi - lo
        W = int(round((L - 2 * gh) * 2))
        Hh = int(round((rise - gh * 0.9) * 2))
        img, cmap = G.pediment_image(W, Hh, subject)
        wall_face = face
        if along_y:
            wbox = (x0, x1, yf - D, yf - recess) if sgn > 0 else (x0, x1, yf + recess, yf + D)
        else:
            wbox = (xf - D, xf - recess, y0, y1) if sgn > 0 else (xf + recess, xf + D, y0, y1)
        s0 = gh
        # Two passes: the whole group a little proud, then the bodies' cores further out, so the
        # figures stand nearly in the round in the recess.
        R.emboss(m, wall_face, wbox, s0, z + Hh / 2.0, img, cmap=cmap, depth=2)
        core = _erode(img)
        R.emboss(m, wall_face, wbox, s0, z + Hh / 2.0, core, cmap=cmap, depth=int(max(3, round(recess * 2 - 1))))
    # The raking sima: a gutter along the slopes, painted with a meander and palmettes.
    if sima:
        sh = S.v(0.55)
        fill(m, box, mat, lambda X, Y, Z: (Z >= top(X, Y) + gh * 0.25) & (Z < top(X, Y) + gh * 0.25 + sh) &
             (depth_in(X, Y) >= -0.5) & (depth_in(X, Y) < 1.6), tone=0.2)
        if paint:
            def sima_paint(i):
                def f(X, Y, Z):
                    dz = (Z - (top(X, Y) + gh * 0.25))
                    u = across(X, Y) * 2
                    on = (dz >= 0) & (dz < sh) & (depth_in(X, Y) < 0.2)
                    return on & (_motif("meander", u, (sh - dz) * 2, int(sh * 2)) == i)
                return f
            fill(m, box, "cinnabar", lambda X, Y, Z: (Z >= top(X, Y) + gh * 0.25) & (Z < top(X, Y) + gh * 0.25 + sh) &
                 (depth_in(X, Y) < 0.2), tone=-0.1, only_solid=True)
            fill(m, box, "ochre", sima_paint(0), tone=0.2, only_solid=True)
    zap = z + rise + gh * 0.25 + S.v(0.55)
    if akroteria:
        ad = 0.8 if along_y else 0.8
        if along_y:
            apex = (c, yf - sgn * ad)
            corners = ((lo + 1.5, yf - sgn * ad), (hi - 1.5, yf - sgn * ad))
        else:
            apex = (xf - sgn * ad, c)
            corners = ((xf - sgn * ad, lo + 1.5), (xf - sgn * ad, hi - 1.5))
        ah = min(S.v(2.6), rise * 0.75)
        akroterion(m, apex[0], apex[1], zap - 0.5, ah, face, akroteria)
        for cx_, cy_ in corners:
            akroterion(m, cx_, cy_, z + gh * 0.25, ah * 0.6, face, akroteria, small=True)
    return zap


def _erode(img):
    """Pixels whose four neighbours are all painted: the core of each figure."""
    on = img != "."
    core = on.copy()
    core[1:, :] &= on[:-1, :]
    core[:-1, :] &= on[1:, :]
    core[:, 1:] &= on[:, :-1]
    core[:, :-1] &= on[:, 1:]
    out = img.copy()
    out[~core] = "."
    return out


def akroterion(m, x, y, z, h, face, kind="floral", small=False):
    """A painted floral akroterion: a palmette fan on volute scrolls standing flat in the
    pediment's plane."""
    along_y = face in ("+y", "-y")
    w = h * (0.75 if not small else 0.6)
    t = 0.7

    def flat(X, Y):
        return (np.abs(Y - y) < t) if along_y else (np.abs(X - x) < t)

    def lateral(X, Y):
        return (X - x) if along_y else (Y - y)
    box = (x - w, x + w, y - w, y + w, z, z + h)
    # A stem and two volute scrolls, then a fan of leaves.
    fill(m, box, "marble", lambda X, Y, Z: flat(X, Y) & (np.abs(lateral(X, Y)) < 0.6) & (Z < z + h * 0.45), tone=0.1)
    fill(m, box, "marble", lambda X, Y, Z: flat(X, Y) & (np.hypot(np.abs(lateral(X, Y)) - w * 0.45,
                                                                    Z - (z + h * 0.25)) < h * 0.2), tone=0.1)
    fill(m, box, "eblue", lambda X, Y, Z: flat(X, Y) & (np.hypot(np.abs(lateral(X, Y)) - w * 0.45,
                                                                   Z - (z + h * 0.25)) < h * 0.09), tone=0.1, only_solid=True)

    def fan(X, Y, Z):
        u, v = lateral(X, Y), Z - (z + h * 0.4)
        rr, a = np.hypot(u, v * 1.1), np.arctan2(u, v)
        return flat(X, Y) & (rr < h * 0.62) & (np.abs(a) < 1.25) & (v > -0.5)

    def rib(X, Y, Z):
        u, v = lateral(X, Y), Z - (z + h * 0.4)
        return ((np.arctan2(u, v + 1e-3) * 9 / np.pi) % 1.0) < 0.5
    fill(m, box, "marble", fan, tone=0.2)
    fill(m, box, "cinnabar", lambda X, Y, Z: fan(X, Y, Z) & rib(X, Y, Z), tone=0.0, only_solid=True)
    fill(m, box, "malachite", lambda X, Y, Z: fan(X, Y, Z) & ~rib(X, Y, Z) & (Z > z + h * 0.75), tone=0.1,
         only_solid=True)
    fill(m, box, "gold", lambda X, Y, Z: flat(X, Y) & (np.hypot(lateral(X, Y), Z - (z + h * 0.42)) < h * 0.12),
         tone=0.3, only_solid=True)


def tiled_roof(m, x0, x1, y0, y1, z0, rise, axis="y", material="marble", kind="corinthian", seed=21,
               antefixes=True, antefix_paint=("cinnabar", "eblue"), ridge=True, thick=2.0, pitch=None, course=None,
               ends=("-", "+")):
    """A gable roof over [x0,x1)x[y0,y1) from the eaves at z0 up `rise` to a ridge along `axis`:
    pan tiles in courses with the cover tiles standing proud in lines down the slope (flat
    Corinthian pans with ridged covers in marble or terracotta, or curved Laconian ones), a
    ridge of cap tiles, and a row of painted antefixes along both eaves."""
    along_y = axis == "y"
    a0, a1 = (x0, x1) if along_y else (y0, y1)       # across the ridge
    half = (a1 - a0) / 2
    c = a0 + half
    pitch = pitch or (2.8 if kind == "corinthian" else 2.2)
    course = course or (3.6 if kind == "corinthian" else 2.6)
    slope = rise / half

    def across(X, Y):
        return np.abs((X if along_y else Y) - c)

    def along(X, Y):
        return (Y if along_y else X)

    def surf(X, Y):
        return z0 + rise * (1 - across(X, Y) / half)

    def relief(X, Y):
        u = (along(X, Y) % pitch) - pitch / 2
        cover = np.abs(u) < (0.55 if kind == "corinthian" else 0.7)
        bump = np.where(cover, (0.65 if kind == "corinthian" else 0.75) * np.sqrt(np.clip(1 - (u / 0.8) ** 2, 0, 1)),
                        -0.15 * (kind == "laconian"))
        d = (half - across(X, Y)) % course               # distance up from each course's lower edge
        lip = 0.25 * (d < 0.6)
        return bump + lip

    def mask(X, Y, Z):
        s = surf(X, Y)
        return (Z < s + relief(X, Y)) & (Z >= s - thick) & (across(X, Y) <= half)

    def tone(X, Y, Z):
        u = (along(X, Y) % pitch) - pitch / 2
        cover = np.abs(u) < 0.6
        d = (half - across(X, Y)) % course
        row = np.floor((half - across(X, Y)) / course).astype(np.int64)
        col = np.floor(along(X, Y) / pitch).astype(np.int64)
        h = hash01(row, col, seed)
        t = (h - 0.5) * (0.6 if material == "marble" else 0.8) + 0.3 * cover - 0.55 * (d < 0.45) \
            - 0.35 * ((np.abs(u) > 0.55) & (np.abs(u) < 0.85))
        # Weathering: broad soft patches, rain-darkened toward the eaves, a few odd tiles.
        weather = (value_noise(X * 0.4, Y * 0.4, Z * 0, 12.0, seed + 3) - 0.5) * 0.7
        eave = -0.45 * np.clip(1 - (half - across(X, Y)) / (course * 1.5), 0, 1)
        odd = np.where(hash01(row, col, seed, 5) < 0.04, -0.6, 0.0) + np.where(hash01(row, col, seed, 6) > 0.97, 0.4, 0.0)
        return t + weather + eave + odd

    def nrm(X, Y, Z):
        sgn = np.sign((X if along_y else Y) - c)
        u = (along(X, Y) % pitch) - pitch / 2
        cover = np.abs(u) < 0.6
        roll = np.where(cover, u / 0.6 * 0.8, 0.0)
        if along_y:
            return (sgn * slope + 0 * X, roll + 0 * Y, 1.0 + 0 * Z)
        return (roll + 0 * X, sgn * slope + 0 * Y, 1.0 + 0 * Z)
    box = (x0, x1, y0, y1, z0 - thick, z0 + rise + 1.2)
    fill(m, box, material, mask, tone, nrm)
    if ridge:
        r = 0.9
        if along_y:
            rod(m, (c, y0 + 0.3, z0 + rise + 0.2), (c, y1 - 0.3, z0 + rise + 0.2), r, material, tone=0.35)
        else:
            rod(m, (x0 + 0.3, c, z0 + rise + 0.2), (x1 - 0.3, c, z0 + rise + 0.2), r, material, tone=0.35)
        if antefixes:   # small painted palmettes standing along the ridge on every other cover line
            def rp(X, Y, Z):
                u = (along(X, Y) % (pitch * 2)) - pitch
                return (np.abs(u) < 0.7 * (1 - np.clip(Z - (z0 + rise + 0.8), 0, 1.6) / 1.8)) & \
                    (np.abs((X if along_y else Y) - c) < 0.45)
            rb = (c - 0.6, c + 0.6, y0 + 2, y1 - 2, z0 + rise + 0.6, z0 + rise + 2.6) if along_y else \
                (x0 + 2, x1 - 2, c - 0.6, c + 0.6, z0 + rise + 0.6, z0 + rise + 2.6)
            fill(m, rb, material, rp, tone=0.3)
            fill(m, rb, antefix_paint[0], lambda X, Y, Z: rp(X, Y, Z) & (Z > z0 + rise + 1.4), tone=0.1, only_solid=True)
    if antefixes:
        # One antefix at the foot of every cover-tile line, alternately painted.
        for side in (-1, 1):
            a = c + side * half
            for i, colr in enumerate(antefix_paint):
                def af(X, Y, Z, i=i, a=a):
                    u = (along(X, Y) % pitch) - pitch / 2
                    k = np.floor(along(X, Y) / pitch).astype(np.int64)
                    w = np.abs((X if along_y else Y) - a) < 0.45
                    h_ = Z - z0
                    shape = np.abs(u) < 0.75 * (1 - np.clip(h_ - 0.4, 0, 2) / 2.2)
                    return w & shape & (h_ > -0.4) & (h_ < 2.2) & (k % len(antefix_paint) == i)
                if along_y:
                    ab = (a - 0.5, a + 0.5, y0, y1, z0 - 0.5, z0 + 2.3)
                else:
                    ab = (x0, x1, a - 0.5, a + 0.5, z0 - 0.5, z0 + 2.3)
                fill(m, ab, material, af, tone=0.2)
                fill(m, ab, colr, lambda X, Y, Z, af=af: af(X, Y, Z) & (Z > z0 + 0.4), tone=0.1, only_solid=True)


def hip_roof(m, x0, x1, y0, y1, z0, rise, material="terracotta", seed=23, apex=None, kind="corinthian", thick=1.6):
    """A pyramidal or hipped roof (the Odeion's tent roof): four tiled slopes rising to an apex
    (or a short ridge), courses parallel to each eave, cover tiles down each slope."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    ridge = 0.0 if apex is None else apex

    def d_edge(X, Y):
        return np.minimum(np.clip(hx - np.abs(X - cx), 0, None) / hx, np.clip(hy - np.abs(Y - cy), 0, None) / hy)

    def surf(X, Y):
        return z0 + rise * np.clip(d_edge(X, Y) * (1 + ridge), 0, 1)

    def facing_x(X, Y):
        return (hx - np.abs(X - cx)) / hx < (hy - np.abs(Y - cy)) / hy

    pitch, course = (2.8, 3.4) if kind == "corinthian" else (2.2, 2.6)

    def tone(X, Y, Z):
        fx = facing_x(X, Y)
        along = np.where(fx, Y, X)
        up = np.where(fx, hx - np.abs(X - cx), hy - np.abs(Y - cy))
        u = (along % pitch) - pitch / 2
        d = up % course
        h = hash01(np.floor(up / course).astype(np.int64), np.floor(along / pitch).astype(np.int64), seed)
        return (h - 0.5) * 0.6 + 0.35 * (np.abs(u) < 0.55) - 0.55 * (d < 0.45)

    def nrm(X, Y, Z):
        fx = facing_x(X, Y)
        sx = np.sign(X - cx) * rise / hx
        sy = np.sign(Y - cy) * rise / hy
        return (np.where(fx, sx, 0.0), np.where(fx, 0.0, sy), 1.0 + 0 * Z)
    fill(m, (x0, x1, y0, y1, z0 - thick, z0 + rise + 1), material,
         lambda X, Y, Z: (Z < surf(X, Y) + 0.5) & (Z >= surf(X, Y) - thick), tone, nrm)
    # Hip ridges with cap tiles.
    for sx in (-1, 1):
        for sy in (-1, 1):
            def hipm(X, Y, Z, sx=sx, sy=sy):
                u = (X - cx) * sx / hx
                v = (Y - cy) * sy / hy
                return (np.abs(u - v) < 0.9 / min(hx, hy)) & (u > 0) & (v > 0) & (np.abs(Z - surf(X, Y) - 0.4) < 0.7)
            fill(m, (x0, x1, y0, y1, z0, z0 + rise + 1.5), material, hipm, tone=0.4)


def conical_roof(m, cx, cy, r, z0, rise, material="terracotta", seed=25, rows=None):
    """A conical roof of lozenge-shaped tiles (the Tholos), courses around and cover lines down,
    the rows offset so the tiles read as diamonds."""
    rows = rows or 2.6

    def surf(X, Y):
        return z0 + rise * (1 - np.hypot(X - cx, Y - cy) / r)

    def tone(X, Y, Z):
        rr = np.hypot(X - cx, Y - cy)
        a = np.arctan2(Y - cy, X - cx)
        ring = np.floor((r - rr) / rows)
        n = np.maximum(np.floor(2 * np.pi * rr / 2.4), 6)
        u = (a / (2 * np.pi) * n + 0.5 * (ring % 2)) % 1.0
        v = ((r - rr) / rows) % 1.0
        lozenge = np.abs(u - 0.5) + np.abs(v - 0.5) * 0.9 < 0.45
        h = hash01(ring.astype(np.int64), np.floor(a * 10).astype(np.int64), seed)
        return (h - 0.5) * 0.5 + 0.3 * lozenge - 0.4 * ~lozenge

    def nrm(X, Y, Z):
        return ((X - cx) * rise / r, (Y - cy) * rise / r, np.hypot(X - cx, Y - cy) + 1e-3)
    fill(m, (cx - r, cx + r, cy - r, cy + r, z0 - 1.5, z0 + rise + 1), material,
         lambda X, Y, Z: (Z < surf(X, Y) + 0.4) & (Z >= surf(X, Y) - 1.6) & (np.hypot(X - cx, Y - cy) <= r), tone, nrm)


# ---------------------------------------------------------------- temples

@dataclass(frozen=True)
class Temple:
    """A Greek temple in a footprint box (design units), long axis along `axis`.

    `cols` = (front, flank) for a peripteral temple; `cella` = (inset across, inset at the
    ends) of the cella walls from the stylobate; porches: 'prostyle' (a row of `porch_cols`
    columns before each cella end, the Parthenon's six), 'antis' (two columns between the
    projecting wall ends, the Hephaisteion) or none. `pediments` = (subject at -end, subject at
    +end) for `relief_greek.pediment_image`; `metopes` = {face: theme} for the outer frieze;
    `frieze` = True for an Ionic frieze round the top of the cella (the Parthenon), "porches" for
    friezes over the porches only (the Hephaisteion)."""
    order: Order
    axis: str = "y"
    cols: tuple = (6, 13)
    steps: tuple = (2.0, 2.0, 2.0)
    tread: float = 2.0
    edge: float = 4.0                         # stylobate edge to the corner column axis
    peripteral: bool = True
    cella: tuple = (14.0, 30.0)
    porch: str = "prostyle"                   # prostyle | antis | none
    porch_cols: int = 6
    porch_order: Order | None = None
    pediments: tuple = ("small", "small")
    metopes: dict = field(default_factory=dict)
    frieze: object = False                     # False, True or 'porches'
    roof: str = "marble"                      # tile material: marble or terracotta
    rise: float | None = None                 # pediment rise (default from a 13.5 degree slope)
    akroteria: str = "floral"
    paint: bool = True
    seed: int = 31
    finish: str = "full"
    door_glow: bool = False
    grilles: bool = False


def temple(m, t: Temple, S: Scale, x0, x1, y0, y1, z0=0.0):
    """Build a temple filling [x0,x1)x[y0,y1). Returns a dict of useful heights."""
    o = t.order
    along_y = t.axis == "y"
    (sx0, sx1, sy0, sy1), zs = crepidoma(m, x0, x1, y0, y1, z0, t.steps, t.tread, o.material, t.seed)
    e = t.edge
    # Column axes on the stylobate.
    fa, fl = t.cols
    if along_y:
        ax_x = list(np.linspace(sx0 + e, sx1 - e, fa))
        ax_y = list(np.linspace(sy0 + e, sy1 - e, fl))
    else:
        ax_x = list(np.linspace(sx0 + e, sx1 - e, fl))
        ax_y = list(np.linspace(sy0 + e, sy1 - e, fa))
    H = S.v(o.H)
    if t.peripteral:
        for x in ax_x:
            for y in ax_y:
                if x in (ax_x[0], ax_x[-1]) or y in (ax_y[0], ax_y[-1]):
                    column(m, x, y, zs, o, S, finish=t.finish, seed=int(x * 7 + y * 3) % 5, paint=t.paint)
    zc = zs + H
    rt = o.r(S) * o.upper
    arch = (ax_x[0] - rt - 0.3, ax_x[-1] + rt + 0.3, ax_y[0] - rt - 0.3, ax_y[-1] + rt + 0.3)
    # The cella.
    ci, ce = t.cella
    if along_y:
        cx0, cx1, cy0, cy1 = sx0 + ci, sx1 - ci, sy0 + ce, sy1 - ce
    else:
        cx0, cx1, cy0, cy1 = sx0 + ce, sx1 - ce, sy0 + ci, sy1 - ci
    wt = S.h(1.2)
    po = t.porch_order or replace(o, H=o.H * 0.96, D=o.D * 0.9)
    zp = zs + (S.v(0.35) * 2 if t.porch == "prostyle" else 0.0)
    if t.porch == "prostyle":     # the porches stand on two more steps
        if along_y:
            crepidoma(m, cx0 - 2.0, cx1 + 2.0, cy0 - S.h(5.0), cy1 + S.h(5.0), zs, (S.v(0.35),) * 2, 0.8, o.material, t.seed + 3)
        else:
            crepidoma(m, cx0 - S.h(5.0), cx1 + S.h(5.0), cy0 - 2.0, cy1 + 2.0, zs, (S.v(0.35),) * 2, 0.8, o.material, t.seed + 3)
    ztop_wall = zc + S.v(o.arch_h) + S.v(o.frieze_h)
    walls = [(cx0, cx0 + wt, cy0, cy1), (cx1 - wt, cx1, cy0, cy1)] if along_y else \
        [(cx0, cx1, cy0, cy0 + wt), (cx0, cx1, cy1 - wt, cy1)]
    ends = [(cx0, cx1, cy0, cy0 + wt), (cx0, cx1, cy1 - wt, cy1)] if along_y else \
        [(cx0, cx0 + wt, cy0, cy1), (cx1 - wt, cx1, cy0, cy1)]
    for w in walls + ends:
        marble_wall(m, *w, zp, ztop_wall, o.material, seed=t.seed + 7)
    # Doors in both end walls (bronze leaves in a moulded frame), the +end one visible.
    dw, dh = S.h(4.2) * (1 if S.s >= 1 else 1), min(S.v(9.8) * (H / S.v(10.4)), H * 0.85)
    for face, w in zip((("-y", "+y") if along_y else ("-x", "+x")), ends):
        L = face_length(face, *w)
        s0 = L / 2 - dw / 2
        fill(m, face_box(face, *w, zp, zp + dh + 1.5, s0 - 1.2, s0 + dw + 1.2, -0.5, 0.2), o.material, tone=0.25)
        carve(m, face_box(face, *w, zp, zp + dh, s0, s0 + dw, -0.6, wt - 0.6))
        fill(m, face_box(face, *w, zp, zp + dh, s0, s0 + dw, wt - 0.6, wt), "bronze",
             tone=lambda X, Y, Z: 0.45 * (((Z - zp) % 4.0) < 0.6) - 0.15)
        if t.door_glow:
            dx, dy = ((w[0] + w[1]) / 2, (w[2] + w[3]) / 2)
            halo(m, dx, dy, zp + dh * 0.4, 14.0, (255, 201, 92), 0.6)
    # Porches: a prostyle row before each end wall, or two columns between projecting antae.
    porch_rows = []
    hp = S.v(po.H)
    if t.porch in ("prostyle", "antis"):
        n = t.porch_cols if t.porch == "prostyle" else 2
        off = min(S.h(3.4), ce - 1.0)              # small temples keep their porch on the stylobate
        if t.porch == "antis":
            antae = [(cx0, cx0 + wt, cy0 - off, cy0), (cx1 - wt, cx1, cy0 - off, cy0),
                     (cx0, cx0 + wt, cy1, cy1 + off), (cx1 - wt, cx1, cy1, cy1 + off)] if along_y else \
                [(cx0 - off, cx0, cy0, cy0 + wt), (cx0 - off, cx0, cy1 - wt, cy1),
                 (cx1, cx1 + off, cy0, cy0 + wt), (cx1, cx1 + off, cy1 - wt, cy1)]
            for w in antae:
                marble_wall(m, *w, zp, ztop_wall, o.material, seed=t.seed + 9)
            off -= S.h(0.7)
        lo_, hi_ = ((cx0, cx1) if along_y else (cy0, cy1))
        if t.porch == "prostyle":
            line = list(np.linspace(lo_ + S.h(0.9), hi_ - S.h(0.9), n))
        else:
            line = [lo_ + wt + (hi_ - lo_ - 2 * wt) * f_ for f_ in (1 / 3, 2 / 3)]
        if along_y:
            porch_rows = [("-y", [(v, cy0 - off) for v in line]), ("+y", [(v, cy1 + off) for v in line])]
        else:
            porch_rows = [("-x", [(cx0 - off, v) for v in line]), ("+x", [(cx1 + off, v) for v in line])]
        for face, pts in porch_rows:
            for x, y in pts:
                column(m, x, y, zp, po, S, finish=t.finish, paint=t.paint)
            # Grilles between the porch columns (cuttings for them survive on the Parthenon).
            if t.grilles:
                for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                    for f_ in np.linspace(0.12, 0.88, 9):
                        gx, gy = xa + (xb - xa) * f_, ya + (yb - ya) * f_
                        rod(m, (gx, gy, zp), (gx, gy, zp + hp * 0.42), 0.22, "metal", tone=0.2)
                    rod(m, (xa, ya, zp + hp * 0.42), (xb, yb, zp + hp * 0.42), 0.3, "metal", tone=0.3)
            # The porch entablature over the columns, back to the cella wall.
            rtp = po.r(S) * po.upper + 0.3
            vs = [q[0] if along_y else q[1] for q in pts]
            ws = [q[1] if along_y else q[0] for q in pts]
            a0, a1 = min(lo_, min(vs) - rtp), max(hi_, max(vs) + rtp)
            if along_y:
                bx = (a0, a1, min(ws) - rtp, cy0 + wt) if face == "-y" else (a0, a1, cy1 - wt, max(ws) + rtp)
            else:
                bx = (min(ws) - rtp, cx0 + wt, a0, a1) if face == "-x" else (cx1 - wt, max(ws) + rtp, a0, a1)
            slab(m, *bx, zp + hp, ztop_wall - S.v(1.0), o.material,
                 tone=M.ashlar(S.v(o.arch_h), 11.0, t.seed, joint=0.2, spread=0.15))
            slab(m, *bx, ztop_wall - S.v(1.0), ztop_wall, o.material, tone=0.0)
            if t.frieze == "porches":
                L = face_length(face, *bx[:4])
                ionic_frieze(m, face, (*bx, 0, 0), 0.5, L - 0.5, ztop_wall, S.v(1.0), seed=t.seed + len(face))
    # The Ionic frieze round the top of the cella and over the porches.
    if t.frieze is True:
        fh = S.v(1.0)
        ext = S.h(4.4) if t.porch == "prostyle" else 0.0
        fbox = (cx0, cx1, cy0 - ext, cy1 + ext) if along_y else (cx0 - ext, cx1 + ext, cy0, cy1)
        for i, face in enumerate(FACES):
            L = face_length(face, *fbox)
            ionic_frieze(m, face, (*fbox, 0, 0), 0.5, L - 0.5, ztop_wall, fh, seed=t.seed + i * 5)
        paint_ring(m, fbox, ztop_wall - fh - 0.6, ztop_wall - fh, "beads", ["gold", "cinnabar"])
    # Outer entablature, the ceiling and the roof.
    def met(face, i, w, h):
        theme = t.metopes.get(face)
        if isinstance(theme, tuple):      # (theme, indices): only those metopes are sculpted
            theme = theme[0] if i in theme[1] else None
        if not theme or w < 6 or h < 6:
            return None
        return G.metope_image(w, h, theme, i)
    zg = doric_entablature(m, arch, zc, o, S, ax_x, ax_y, metopes=met if t.metopes else None, paint=t.paint,
                           seed=t.seed + 11)
    # The ceiling over the pteron: coffered marble beams from the frieze back to the cella.
    slab(m, arch[0] + 1.0, arch[1] - 1.0, arch[2] + 1.0, arch[3] - 1.0, ztop_wall - 0.2, zg - S.v(o.geison_h) * 0.3,
         o.material, tone=-0.4)
    out = S.h(o.geison_out)
    gx0, gx1, gy0, gy1 = arch[0] - out, arch[1] + out, arch[2] - out, arch[3] + out
    half = ((gx1 - gx0) if along_y else (gy1 - gy0)) / 2
    rise = t.rise if t.rise is not None else half * 0.24 * (5.0 / 4.0)
    # Fill under the roof so the pediment block and tiles sit on solid stone.
    zr = zg
    if along_y:
        fill(m, (arch[0], arch[1], arch[2] + S.h(2.2), arch[3] - S.h(2.2), zr - 0.5, zr + rise), o.material,
             lambda X, Y, Z: Z < zr + rise * (1 - np.abs(X - (gx0 + gx1) / 2) / half) - 1.5, tone=-0.3)
    else:
        fill(m, (arch[0] + S.h(2.2), arch[1] - S.h(2.2), arch[2], arch[3], zr - 0.5, zr + rise), o.material,
             lambda X, Y, Z: Z < zr + rise * (1 - np.abs(Y - (gy0 + gy1) / 2) / half) - 1.5, tone=-0.3)
    tiled_roof(m, gx0, gx1, gy0, gy1, zr, rise, axis=t.axis, material=t.roof, seed=t.seed + 13)
    faces = ("-y", "+y") if along_y else ("-x", "+x")
    zap = zr
    for face, subject in zip(faces, t.pediments):
        zap = pediment(m, face, gx0, gx1, gy0, gy1, zr, rise, o, S, subject=subject, paint=t.paint,
                       akroteria=t.akroteria)
    return {"stylobate": zs, "capital": zc, "geison": zg, "apex": zap, "cella": (cx0, cx1, cy0, cy1),
            "axes": (ax_x, ax_y), "porch_z": zp}


# ---------------------------------------------------------------- stoas

@dataclass(frozen=True)
class Stoa:
    """A stoa: a long hall open on its `front` face behind a Doric colonnade, an inner row of
    Ionic columns carrying the ridge, a back wall (with painted panels and hanging shields for
    the Poikile) and a tiled roof with its ridge along the length."""
    order: Order
    front: str = "+x"
    n_cols: int = 10
    inner: Order | None = None
    n_inner: int = 0
    panels: tuple = ()
    shields: int = 0
    roof: str = "terracotta"
    steps: tuple = (1.6,)
    seed: int = 41
    paint: bool = True
    open_ends: bool = False
    inner_at: float = 0.5              # the inner row's place from the back wall (0) to the front (1)


def stoa(m, st: Stoa, S: Scale, x0, x1, y0, y1, z0=0.0, col_tiles=None):
    """Build a stoa in the box. With `col_tiles` (a list of tile indices along the front) the
    front columns stand on those tiles' centres, so the tiles between can be walk tiles."""
    o = st.order
    front = st.front
    along_y = front in ("+x", "-x")          # the colonnade runs along y
    (sx0, sx1, sy0, sy1), zs = crepidoma(m, x0, x1, y0, y1, z0, st.steps, 1.4, o.material, st.seed,
                                          sides=(front,))
    H = S.v(o.H)
    r = o.r(S)
    L0, L1 = (sy0, sy1) if along_y else (sx0, sx1)
    # Front line and back line coordinates.
    if front == "+x":
        fpos, bpos = sx1 - r - 0.8, sx0
    elif front == "-x":
        fpos, bpos = sx0 + r + 0.8, sx1
    elif front == "+y":
        fpos, bpos = sy1 - r - 0.8, sy0
    else:
        fpos, bpos = sy0 + r + 0.8, sy1
    if col_tiles is not None:
        cols = [c * 16 + 8 for c in col_tiles]
    else:
        cols = list(np.linspace(L0 + r + 1.0, L1 - r - 1.0, st.n_cols))
    for c in cols:
        x, y = (fpos, c) if along_y else (c, fpos)
        column(m, x, y, zs, o, S, seed=int(c) % 5, paint=st.paint)
    zc = zs + H
    wt = S.h(0.9)
    # Back wall and end walls; the end walls stop short of the colonnade (antae).
    sgn = 1 if front[0] == "+" else -1
    near = fpos - sgn * (r + 1.5)                 # where the end walls stop
    lo, hi = min(bpos, near), max(bpos, near)
    if along_y:
        back = (bpos, bpos + wt, sy0, sy1) if sgn > 0 else (bpos - wt, bpos, sy0, sy1)
        ends = [(lo, hi, sy0, sy0 + wt), (lo, hi, sy1 - wt, sy1)]
    else:
        back = (sx0, sx1, bpos, bpos + wt) if sgn > 0 else (sx0, sx1, bpos - wt, bpos)
        ends = [(sx0, sx0 + wt, lo, hi), (sx1 - wt, sx1, lo, hi)]
    ztop = zc + S.v(o.arch_h + o.frieze_h)
    house_wall(m, *back, zs, ztop, seed=st.seed, socle=S.v(1.0), plaster="whitewash", socle_mat="poros")
    if not st.open_ends:
        for e in ends:
            house_wall(m, *e, zs, ztop, seed=st.seed + 1, socle=S.v(1.0), plaster="whitewash")
    # Painted panels on the inner face of the back wall, hanging shields above them.
    inner_face = front
    if st.panels:
        Lw = face_length(inner_face, *back)
        n = len(st.panels)
        pw = (Lw - 4.0) / n
        # Hung low enough to be seen under the eaves through the colonnade.
        ph = min(H * 0.4, S.v(2.3))
        zpb = zs + S.v(0.3)
        for i, subj in enumerate(st.panels):
            a = 2.0 + i * pw + 0.8
            b = a + pw - 1.6
            fill(m, face_box(inner_face, *back, zpb - 0.6, zpb + ph + 0.6, a - 0.6, b + 0.6, -0.4, 0.1), "cedar",
                 tone=0.1)
            fill(m, face_box(inner_face, *back, zpb, zpb + ph, a, b, -0.45, -0.3), "cream", tone=0.1)
            img, cmap = G.panel_image(int((b - a) * 2), int(ph * 2), subj)
            R.emboss(m, inner_face, _shift(back, inner_face, -0.45), a, zpb + ph, img, cmap=cmap, depth=0)
    if st.shields:
        Lw = face_length(inner_face, *back)
        for i in range(st.shields):
            s = 3.0 + (Lw - 6.0) * (i + 0.5) / st.shields
            zz = zs + H * 0.82
            fb = face_box(inner_face, *back, zz - 2.2, zz + 2.2, s - 2.2, s + 2.2, -1.0, 0.0)
            fill(m, fb, "bronze", lambda X, Y, Z, s=s, zz=zz: np.hypot(face_frame(inner_face, X, Y, Z, *back[:4])[0] - s,
                                                                    Z - zz) < 2.0, tone=0.25)
    # Inner Ionic row carrying the ridge.
    if st.inner and st.n_inner:
        mid = bpos + (fpos - bpos) * st.inner_at
        icols = list(np.linspace(L0 + 6.0, L1 - 6.0, st.n_inner))
        hi = ztop - zs - S.v(0.6)
        io = replace(st.inner, H=hi / S.v(1))
        for c in icols:
            x, y = (mid, c) if along_y else (c, mid)
            column(m, x, y, zs, io, S, face="x" if along_y else "y", paint=st.paint)
    # Front entablature.
    rt = r * o.upper + 0.3
    if along_y:
        arch = (fpos - rt, fpos + rt, L0, L1)
        axes_x, axes_y = [fpos], cols
    else:
        arch = (L0, L1, fpos - rt, fpos + rt)
        axes_x, axes_y = cols, [fpos]
    zg = doric_entablature(m, arch, zc, o, S, axes_x, axes_y, faces=(front,), paint=st.paint, geison=False,
                           seed=st.seed + 3)
    out = S.h(o.geison_out)
    # The whole hall under one roof: geison round it, ridge along the length.
    if along_y:
        hb = (min(back[0], arch[0]), max(back[1], arch[1]), sy0, sy1)
    else:
        hb = (sx0, sx1, min(back[2], arch[2]), max(back[3], arch[3]))
    slab(m, hb[0] + 0.5, hb[1] - 0.5, hb[2] + 0.5, hb[3] - 0.5, ztop - 0.5, zg, o.material, tone=-0.3)
    zg2 = geison_ring(m, hb, zg, S.v(o.geison_h), out, o.material, faces=FACES, paint=st.paint)
    gb = (hb[0] - out, hb[1] + out, hb[2] - out, hb[3] + out)
    half = ((gb[1] - gb[0]) if along_y else (gb[3] - gb[2])) / 2
    rise = half * 0.3
    tiled_roof(m, *gb, zg2, rise, axis="y" if along_y else "x", material=st.roof, kind="corinthian", seed=st.seed + 5)
    for face in (("-y", "+y") if along_y else ("-x", "+x")):
        pediment(m, face, *gb, zg2, rise, o, S, subject=None, paint=st.paint, akroteria="floral")
    return {"stylobate": zs, "top": zg2 + rise, "cols": cols}


def _shift(box, face, d):
    x0, x1, y0, y1 = box[:4]
    if face == "+x":
        return (x0, x1 + d, y0, y1)
    if face == "-x":
        return (x0 - d, x1, y0, y1)
    if face == "+y":
        return (x0, x1, y0, y1 + d)
    return (x0, x1, y0 - d, y1)


# ---------------------------------------------------------------- statues on the rig

@lru_cache(maxsize=64)
def statue_model(dress, scale, k, material="bronze", keep=(), anim="idle", frame=0, facing_turns=0):
    """A statue: a walker-rig person drawn `scale` times life size into its own small model,
    every material turned to `material` (bronze, marble) except those in `keep` (painted
    details, gilding, a shield blazon). Cached; paste it with `paste`."""
    frames = rig.POSES[anim]
    fr = rig.Frame(dress)
    p = rig.pose(anim, frame, frames, fr, dress)
    reach = int(math.ceil(12 * scale)) + 2
    tall = int(math.ceil((fr.H * 2.3 if dress.hand_l in ("spear", "lance") or dress.hand_r in ("spear", "lance")
                          else fr.H + 6) * scale)) + 2
    m = Model.empty(-reach, reach, -reach, reach, 0, tall, k=k)
    b = ScaledBody(m, scale)
    rig.draw(b, dress, p, fr)
    keep_ids = {MAT[n] for n in keep}
    sel = (m.mat > 0) & ~np.isin(m.mat, list(keep_ids))
    m.mat[sel] = MAT[material]
    if facing_turns:
        m = m.rotated(facing_turns, 0, 0)
    return m


class ScaledBody(rig.Body):
    """A rig body `scale` times life size: body space = world / scale."""

    def __init__(self, m, scale):
        super().__init__(m, rot=np.eye(3) / scale)
        self.s = scale

    def wn(self, n):
        return None if n is None else tuple(np.broadcast_arrays(*n))

    def points(self, pts, material, tone=0.0):
        self.m.put_points(np.asarray(pts, np.float32).reshape(-1, 3) * self.s + self.t, material, tone=tone)


def paste(m, sub: Model, x, y, z):
    """Copy a small model into `m` with its origin at (x, y, z) design units, wherever the two
    grids overlap (so it is safe on every chunk)."""
    k = m.k
    ox, oy, oz = int(round(x * k)) + sub.x0 - m.x0, int(round(y * k)) + sub.y0 - m.y0, int(round(z * k)) + sub.z0 - m.z0
    nx, ny, nz = sub.mat.shape
    a0, b0, c0 = max(ox, 0), max(oy, 0), max(oz, 0)
    a1, b1, c1 = min(ox + nx, m.mat.shape[0]), min(oy + ny, m.mat.shape[1]), min(oz + nz, m.mat.shape[2])
    if a1 <= a0 or b1 <= b0 or c1 <= c0:
        return
    src = (slice(a0 - ox, a1 - ox), slice(b0 - oy, b1 - oy), slice(c0 - oz, c1 - oz))
    dst = (slice(a0, a1), slice(b0, b1), slice(c0, c1))
    sel = sub.mat[src] > 0
    m.mat[dst][sel] = sub.mat[src][sel]
    m.tone[dst][sel] = sub.tone[src][sel]
    m.nrm[dst][sel] = sub.nrm[src][sel]


def statue_base(m, x, y, z, w, h, material="marble", inscription=True, steps=1):
    """A stepped base with a moulded top and an inscription band (letters too small to read)."""
    for i in range(steps):
        slab(m, x - w / 2 - (steps - i) * 0.8, x + w / 2 + (steps - i) * 0.8, y - w / 2 - (steps - i) * 0.8,
             y + w / 2 + (steps - i) * 0.8, z + i * 1.0, z + (i + 1) * 1.0, material, tone=0.2)
    zb = z + steps * 1.0
    slab(m, x - w / 2, x + w / 2, y - w / 2, y + w / 2, zb, zb + h, material,
         tone=M.ashlar(h, w * 2, int(x + y) % 9, joint=0.2, spread=0.2))
    slab(m, x - w / 2 - 0.6, x + w / 2 + 0.6, y - w / 2 - 0.6, y + w / 2 + 0.6, zb + h, zb + h + 1.0, material, tone=0.35)
    if inscription:
        for face in FACES:
            fill(m, face_box(face, x - w / 2, x + w / 2, y - w / 2, y + w / 2, zb + h * 0.55, zb + h * 0.8, 0.8, w - 0.8,
                             -0.05, 0.3), "gloss",
                 lambda X, Y, Z: (hash01(np.floor(X * 2.5).astype(np.int64) + np.floor(Y * 2.5).astype(np.int64),
                                         np.floor(Z * 2.5).astype(np.int64), 7) < 0.4), tone=0.2, only_solid=True)
    return zb + h + 1.0


def herm(m, x, y, z, h=18.0, material="marble", face="+y", paint=True):
    """A herm: a square pillar with a bearded head of Hermes and a phallus, stubs for arms;
    garlanded, the head painted (hair and beard dark, eyes)."""
    w = h * 0.13
    slab(m, x - w, x + w, y - w, y + w, z, z + h * 0.78, material, tone=M.ashlar(h, w * 4, 3, joint=0.1, spread=0.2))
    nx, ny = {"+y": (0, 1), "-y": (0, -1), "+x": (1, 0), "-x": (-1, 0)}[face]
    hz = z + h * 0.78
    ellipsoid(m, (x, y, hz + h * 0.1), (w * 1.05, w * 1.05, h * 0.12), material, tone=0.2)
    ellipsoid(m, (x + nx * w * 0.6, y + ny * w * 0.6, hz + h * 0.01), (w * 0.8, w * 0.8, h * 0.09), "hair_black" if paint else material,
              tone=0.0)
    ellipsoid(m, (x - nx * w * 0.2, y - ny * w * 0.2, hz + h * 0.16), (w * 1.1, w * 1.1, h * 0.07),
              "hair_black" if paint else material, tone=0.1)
    for s in (-1, 1):    # arm stubs at the shoulders
        sx, sy = (x + (ny * s) * w * 1.3, y + (nx * s) * w * 1.3)
        slab(m, min(x, sx) - 0.5, max(x, sx) + 0.5, min(y, sy) - 0.5, max(y, sy) + 0.5, hz - h * 0.12, hz - h * 0.05,
             material, tone=0.1)
    px, py = x + nx * w, y + ny * w
    rod(m, (px, py, z + h * 0.36), (px + nx * 1.4, py + ny * 1.4, z + h * 0.42), 0.6, material, tone=0.2)
    if paint:   # a woollen fillet tied round the neck
        fill(m, (x - w - 0.5, x + w + 0.5, y - w - 0.5, y + w + 0.5, hz - 0.6, hz + 0.2), "cinnabar", tone=0.1)


def stele(m, x, y, z, w, h, face="+y", subject="farewell", material="marble", t=1.4, crown="palmette"):
    """A stele: a tall slab with a relief panel (or inscribed lines) and a palmette crown."""
    along = face in ("+y", "-y")
    bx = (x - w / 2, x + w / 2, y - t / 2, y + t / 2) if along else (x - t / 2, x + t / 2, y - w / 2, y + w / 2)
    slab(m, *bx, z, z + h, material, tone=M.ashlar(h, 40.0, int(x * 3 + y) % 7, joint=0.1, spread=0.3))
    if crown == "palmette":
        cx, cy = x, y
        akroterion(m, cx, cy, z + h - 0.3, h * 0.28, "+y" if along else "+x", "floral", small=True)
    if subject in ("farewell", "youth"):
        img, cmap = G.stele_image(int(w * 2) - 2, int(h * 0.55 * 2), subject)
        R.emboss(m, face, bx, 0.5, z + h * 0.8, img, cmap=cmap, depth=1)
    else:   # inscribed lines, painted red in the letters (illegible at this size)
        for face_ in (face,):
            fill(m, face_box(face_, *bx, z + h * 0.15, z + h * 0.9, 0.5, w - 0.5, -0.05, 0.3), "cinnabar",
                 lambda X, Y, Z: ((Z * 2) % 1.6 < 0.5) & (hash01(np.floor((X + Y) * 3).astype(np.int64),
                                                                    np.floor(Z * 2).astype(np.int64), 3) < 0.55),
                 tone=-0.2, only_solid=True)


# ---------------------------------------------------------------- vases

VASES = {
    # name: (height share list of (t, radius as a fraction of h)) -- profiles from the foot up.
    "amphora": [(0.0, 0.12), (0.05, 0.1), (0.12, 0.16), (0.35, 0.3), (0.55, 0.3), (0.72, 0.2), (0.8, 0.11),
                (0.94, 0.1), (1.0, 0.14)],
    "transport": [(0.0, 0.03), (0.08, 0.08), (0.3, 0.2), (0.55, 0.24), (0.75, 0.2), (0.86, 0.09), (1.0, 0.08)],
    "krater": [(0.0, 0.18), (0.08, 0.14), (0.2, 0.22), (0.55, 0.36), (0.8, 0.4), (1.0, 0.45)],
    "hydria": [(0.0, 0.14), (0.06, 0.12), (0.3, 0.3), (0.55, 0.32), (0.72, 0.18), (0.88, 0.1), (1.0, 0.16)],
    "lekythos": [(0.0, 0.1), (0.08, 0.1), (0.15, 0.16), (0.7, 0.17), (0.75, 0.08), (0.92, 0.06), (1.0, 0.09)],
    "pithos": [(0.0, 0.2), (0.15, 0.32), (0.5, 0.42), (0.85, 0.32), (1.0, 0.24)],
}


def vase(m, x, y, z, h, kind="amphora", body="clay", figure="redfigure", seed=0):
    """A vase turned from its profile. `figure`: 'redfigure' (black gloss with a reserved band
    of red figures), 'blackfigure' (orange with a black figure band: the Panathenaic prize
    amphora), 'whiteground' (lekythos), 'plain'."""
    prof = VASES[kind]
    ts = np.array([p[0] for p in prof], np.float32)
    rs = np.array([p[1] for p in prof], np.float32) * h

    def radius(t):
        return np.interp(t, ts, rs)
    mat = {"redfigure": "gloss", "blackfigure": "clay", "whiteground": "whitewash", "plain": body}[figure]
    revolve(m, x, y, z, z + h, radius, mat, tone=lambda X, Y, Z: 0.2 * ((Z - z) / h > 0.95))
    if figure in ("redfigure", "blackfigure", "whiteground") and h >= 4:
        band = "clay" if figure == "redfigure" else "gloss"
        za, zb = z + h * 0.3, z + h * 0.62

        def fig(X, Y, Z):
            a = np.arctan2(Y - y, X - x)
            u = (a * 6 / np.pi) % 2.0
            v = (Z - za) / (zb - za)
            body_ = (np.abs(u - 1.0) < 0.22) & (v > 0.05) & (v < 0.85)
            head = (np.hypot((u - 1.0) * 2.0, (v - 0.85) * 3.0) < 0.5)
            return body_ | head
        if figure == "redfigure":
            fill(m, (x - h, x + h, y - h, y + h, za, zb), "clay", fig, tone=0.1, only_solid=True)
            fill(m, (x - h, x + h, y - h, y + h, za - 0.4, za), "clay", tone=0.0, only_solid=True)
        else:
            fill(m, (x - h, x + h, y - h, y + h, za, zb), band, fig, tone=0.1, only_solid=True)
    if kind in ("amphora", "hydria", "krater", "transport"):
        for sgn in (-1, 1):
            r1 = radius(0.85 if kind != "krater" else 0.8)
            rod(m, (x, y + sgn * r1, z + h * 0.9), (x, y + sgn * (r1 + h * 0.08), z + h * 0.62), max(0.3, h * 0.04),
                mat, tone=0.2)


# ---------------------------------------------------------------- walls and towers

def city_wall(m, x0, x1, y0, y1, z0, h, socle=None, seed=51, merlons=True, grave_reuse=False, plaster="whitewash"):
    """A Greek city wall: a stone socle of squared blocks (with reused grave stelae near the
    Kerameikos, Thucydides 1.93), a mudbrick curtain plastered, a crenellated parapet."""
    socle = socle if socle is not None else h * 0.35
    slab(m, x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, z0, z0 + socle, "poros",
         tone=M.ashlar(2.6, 6.0, seed, joint=0.35, spread=0.8, polygonal=0.6, odd=0.2))
    if grave_reuse:
        # A few carved slabs in the base course: palmette crowns and relief panels.
        fill(m, (x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, z0 + socle * 0.3, z0 + socle * 0.8), "marble",
             lambda X, Y, Z: (hash01(np.floor((X + Y) / 7.0).astype(np.int64), seed, 3) < 0.18) &
             (((X + Y) % 7.0) > 1.2) & (((X + Y) % 7.0) < 5.2), tone=0.2, only_solid=True)
    slab(m, x0, x1, y0, y1, z0 + socle, z0 + h, plaster, tone=M.mud_plaster(seed, 0.45, z0 + socle, 2.5))
    if merlons:
        pitch = 4.0
        fill(m, (x0, x1, y0, y1, z0 + h, z0 + h + 3.2), plaster,
             lambda X, Y, Z: ((X + Y) % pitch < pitch * 0.55), tone=0.2)
        slab(m, x0, x1, y0, y1, z0 + h, z0 + h + 0.4, "poros", tone=0.3)
