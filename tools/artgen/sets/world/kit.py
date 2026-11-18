"""The connective kit of the world (docs/design/sets/world.md §3): crossings and harbour works
that join from tile to tile (fords, stone and timber bridges, pontoons, jetties, moles, terrace
walls), stairs and ramps, and the things of road, field and shore for every era: milestones,
shrines, the Royal Road's stations, watchtowers and beacons, folds and huts, charcoal kilns,
fishermen's huts and racks, shadufs, reed houses of the marshes, burial mounds, inns, cisterns,
quarries, salt pans and herders' tents.

Toolkits as the city sets use them (`arch`, `materials`, `greek`), so world kit stands beside
city kit without a seam. Rotatable pieces are modelled facing +y (their door or front on the
+y face); kit stairs climb away from their front, toward -y at r0. Connect pieces run along the
axis of their neighbours; a piece with a neighbour on one side only is an end, and bridges ramp
down there to the bank."""

import math

import numpy as np

import materials as M
from arch import carve, ellipsoid, face_box, fill, halo, mudbrick_wall, revolve, rod, slab, tent
from greek import house_wall, tiled_roof
from setbuild import Item
from voxel import Model, Rng, hash01, value_noise

T = 16
FIRE = (255, 154, 58)
LAMP = (255, 201, 92)
N_BIT, E_BIT, S_BIT, W_BIT = 1, 2, 4, 8


def _m(fw, fh, top, k, below=0, pad=3):
    return Model.empty(-pad, fw * T + pad, -pad, fh * T + pad, -below, top, k=k)


def _mask(v):
    return int(v[1:]) if isinstance(v, str) else int(v)


# ---------------------------------------------------------------- joined pieces

def _segments(mask):
    """The runs of a connect piece: for each direction from the tile centre to an edge,
    'arm' (a neighbour there), 'end' (the run stops at the bank on that side) or nothing. A
    run with a neighbour on one side only gets an end on the other; an isolated piece runs
    along y with ends at both sides."""
    dirs = {"n": bool(mask & N_BIT), "s": bool(mask & S_BIT), "e": bool(mask & E_BIT), "w": bool(mask & W_BIT)}
    seg = {d: "arm" for d, on in dirs.items() if on}
    if not seg:
        return {"n": "end", "s": "end"}
    if dirs["n"] != dirs["s"] and not (dirs["e"] or dirs["w"]):
        seg["s" if dirs["n"] else "n"] = "end"
    if dirs["e"] != dirs["w"] and not (dirs["n"] or dirs["s"]):
        seg["w" if dirs["e"] else "e"] = "end"
    return seg


def _seg_frame(d, X, Y):
    """For a direction from the centre: (t along it 0 at the centre .. 1 at the edge, s across
    it, inside the half tile)."""
    u, v = X - 8.0, Y - 8.0
    t, s = {"n": (-v, u), "s": (v, u), "e": (u, v), "w": (-u, v)}[d]
    return t / 8.0, s, t >= -0.01


def _deck_height(seg, X, Y, width, z_deck, z_end):
    """Height of the deck top over the tile (-1 outside the deck)."""
    out = np.full(np.broadcast(X, Y).shape, -1.0)
    for d, kind in seg.items():
        t, s, ok = _seg_frame(d, X, Y)
        inside = ok & (t <= 1.0001) & (np.abs(s) < width)
        z = z_deck if kind == "arm" else z_deck + (z_end - z_deck) * np.clip(t, 0, 1) ** 1.2
        out = np.where(inside, np.maximum(out, z), out)
    return out


def _deck(m, mask, width, z_deck, z_end, material, top_mat, tone, top_tone=0.0, z_bottom=-1.0, thick=None):
    seg = _segments(mask)
    hfun = lambda X, Y: _deck_height(seg, X, Y, width, z_deck, z_end)
    lo = (lambda X, Y: z_bottom) if thick is None else (lambda X, Y: hfun(X, Y) - thick)
    box = (-0.5, 16.5, -0.5, 16.5, z_bottom, max(z_deck, z_end) + 0.5)
    fill(m, box, material, lambda X, Y, Z: (Z < hfun(X, Y) - 0.8) & (Z >= lo(X, Y)) & (hfun(X, Y) > 0), tone=tone)
    fill(m, box, top_mat, lambda X, Y, Z: (Z < hfun(X, Y)) & (Z >= hfun(X, Y) - 0.8) & (hfun(X, Y) > 0), tone=top_tone)
    return seg, hfun


def _rails(m, seg, width, z_deck, z_end, h, material, side=0, inset=1.0, r=None, tone=0.2):
    """Parapets or hand-rails along both edges of every run (side=+1 or -1: one edge only)."""
    for d, kind in seg.items():
        for sgn in ((-1, 1) if side == 0 else (side,)):
            def mask(X, Y, Z, d=d, kind=kind, sgn=sgn):
                t, s, ok = _seg_frame(d, X, Y)
                z = z_deck if kind == "arm" else z_deck + (z_end - z_deck) * np.clip(t, 0, 1) ** 1.2
                edge = (s * sgn > width - inset) & (s * sgn < width)
                return ok & (t <= 1.0001) & edge & (Z >= z - 0.5) & (Z < z + h)
            fill(m, (-0.5, 16.5, -0.5, 16.5, min(z_deck, z_end) - 1, max(z_deck, z_end) + h + 1), material, mask, tone=tone)


def ford(v, frame, frames, k):
    """A ford: r0 flat stepping stones across the stream, r1 gravel shallows marked with poles
    at the edges of the crossing. Walkable; stones laid so it can be crossed either way."""
    m = _m(1, 1, 6, k, below=1)
    rng = Rng(6000, v)
    if v == 0:
        for (x, y) in ((8, 1.8), (8.6, 5.2), (7.6, 8.4), (8.4, 11.6), (8, 14.6), (2.0, 8.2), (4.9, 7.6), (11.2, 8.6), (14.2, 8)):
            rx, ry = rng.uniform(1.4, 1.9), rng.uniform(1.2, 1.7)
            fill(m, (x - 2.2, x + 2.2, y - 2.2, y + 2.2, -1.0, 1.6), "stone",
                 lambda X, Y, Z, x=x, y=y, rx=rx, ry=ry: ((X - x) / rx) ** 2 + ((Y - y) / ry) ** 2 < 1 - (Z / 1.8) ** 2,
                 tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.2, 6001) - 0.5) * 0.8 + 0.2)
    else:
        fill(m, (0.5, 15.5, 0.5, 15.5, -1.0, 0.5), "gravel",
             lambda X, Y, Z: (np.abs(X - 8) < 5.5) | (np.abs(Y - 8) < 5.5),
             tone=lambda X, Y, Z: (hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), 6002) - 0.5) * 1.2)
        for (x, y) in ((2.0, 2.0), (14.0, 2.0), (2.0, 14.0), (14.0, 14.0)):
            rod(m, (x, y, -1.0), (x + 0.3, y, 6.0), 0.4, "wood", tone=0.1)
            fill(m, (x - 0.6, x + 0.9, y - 0.5, y + 0.5, 4.6, 5.6), "cinnabar", tone=0.1)
    return m


def bridge_arch(v, frame, frames, k):
    """A Roman stone arch bridge: one semicircular arch of grey limestone with tufa voussoirs
    to each middle piece, pointed cutwaters at the piers, a paved deck between low parapets;
    the end pieces are solid abutments ramping down to the bank."""
    mask = _mask(v)
    m = _m(1, 1, 18, k, below=2)
    w, zd, ze = 5.0, 9.0, 2.5
    seg, hfun = _deck(m, mask, w, zd, ze, "stone", "basalt", M.ashlar(2.2, 5.0, 6010, spread=0.45),
                      top_tone=lambda X, Y, Z: (hash01(np.floor(X / 2.2).astype(np.int64), np.floor(Y / 2.2).astype(np.int64), 6011) - 0.5) * 0.8,
                      z_bottom=-2.0)
    for axis, a, b in (("y", "n", "s"), ("x", "w", "e")):
        if seg.get(a) == "arm" and seg.get(b) == "arm":
            R, zs = 6.0, 0.5
            along = (lambda X, Y: Y) if axis == "y" else (lambda X, Y: X)
            across = (lambda X, Y: X) if axis == "y" else (lambda X, Y: Y)
            carve(m, (-1, 17, -1, 17, -2.0, zs + R), lambda X, Y, Z: (np.abs(across(X, Y) - 8) < w + 0.1) &
                  (np.hypot(along(X, Y) - 8, np.maximum(Z - zs, 0)) < R))
            fill(m, (-1, 17, -1, 17, zs, zs + R + 1.6), "tufa",
                 lambda X, Y, Z: (np.abs(np.abs(across(X, Y) - 8) - (w - 0.6)) < 0.6) &
                 (np.hypot(along(X, Y) - 8, Z - zs) >= R) & (np.hypot(along(X, Y) - 8, Z - zs) < R + 1.5) & (Z >= zs),
                 tone=lambda X, Y, Z: 0.3 - 0.8 * (((np.arctan2(Z - zs, along(X, Y) - 8) * 7 / np.pi) % 1.0) < 0.14),
                 only_solid=True)
            for edge in (0.0, 16.0):        # cutwaters on both faces at the piers
                fill(m, (-4, 20, -4, 20, -2.0, 6.0), "stone",
                     lambda X, Y, Z, edge=edge: (np.abs(across(X, Y) - 8) >= w) & (np.abs(across(X, Y) - 8) < w + 3.0) &
                     (np.abs(along(X, Y) - edge) < 2.2 * (1 - (np.abs(across(X, Y) - 8) - w) / 3.0)) &
                     (along(X, Y) >= -0.01) & (along(X, Y) <= 16.01) & (Z < 6.0 - (np.abs(across(X, Y) - 8) - w)),
                     tone=M.ashlar(1.8, 4.0, 6012, spread=0.4))
    _rails(m, seg, w, zd, ze, 3.0, "stone", tone=M.plus(M.ashlar(1.5, 5.0, 6013, spread=0.3), 0.15))
    return m


def bridge_timber(v, frame, frames, k):
    """A timber bridge: oak trestles at the piece edges, a plank deck laid across the run, one
    hand-rail; the end pieces slope down to the bank. Era-neutral (Croesus crossed the Halys by
    bridges, Herodotus 1.75)."""
    mask = _mask(v)
    m = _m(1, 1, 12, k, below=1)
    w, zd, ze = 4.0, 6.0, 2.0
    seg, hfun = _deck(m, mask, w, zd, ze, "wood", "wood_light", 0.0,
                      top_tone=lambda X, Y, Z: -0.6 * (((X + Y) % 2.0) < 0.35) + (hash01(np.floor(X + Y).astype(np.int64), 6021) - 0.5) * 0.6,
                      thick=1.2)
    for d, kind in seg.items():
        if kind != "arm":
            continue
        for sgn in (-1, 1):            # a trestle at the piece edge: two posts and a brace
            px, py = {"n": (8 + sgn * (w - 0.6), 0.6), "s": (8 + sgn * (w - 0.6), 15.4),
                      "e": (15.4, 8 + sgn * (w - 0.6)), "w": (0.6, 8 + sgn * (w - 0.6))}[d]
            rod(m, (px, py, -1.0), (px, py, zd - 1.0), 0.55, "wood", tone=0.1)
        a = {"n": ((8 - w, 0.6), (8 + w, 0.6)), "s": ((8 - w, 15.4), (8 + w, 15.4)),
             "e": ((15.4, 8 - w), (15.4, 8 + w)), "w": ((0.6, 8 - w), (0.6, 8 + w))}[d]
        rod(m, (a[0][0], a[0][1], 0.5), (a[1][0], a[1][1], zd - 1.4), 0.3, "wood")
        rod(m, (a[0][0], a[0][1], zd - 1.4), (a[1][0], a[1][1], zd - 1.4), 0.4, "wood")
    _rails(m, seg, w, zd, ze, 3.2, "wood", side=1, inset=0.6, tone=0.15)
    return m


def pontoon(v, frame, frames, k):
    """A bridge of boats: boats moored side by side across the stream, planks laid over them,
    rope rails; it bobs a pixel (two frames). Xenophon saw such bridges on the Maeander and the
    Tigris (Anabasis 1.2.5, 2.4.24)."""
    mask = _mask(v)
    bob = 0.5 * (frame % 2)
    m = _m(1, 1, 8, k, below=2)
    w, zd, ze = 4.0, 3.5 + bob, 1.2
    seg = _segments(mask)
    for d, kind in seg.items():
        if kind != "arm":
            continue
        t0 = 4.0
        bx, by = {"n": (8, t0), "s": (8, 16 - t0), "e": (16 - t0, 8), "w": (t0, 8)}[d]
        across_x = d in ("n", "s")
        L = 2 * w + 3.0
        def hull(X, Y, Z, bx=bx, by=by, across_x=across_x):
            a = (X - bx) if across_x else (Y - by)
            b = (Y - by) if across_x else (X - bx)
            half = 1.9 * np.sqrt(np.clip(1 - (a / (L / 2)) ** 2, 0, 1))
            return (np.abs(b) < half) & (Z < 1.6 + bob + 0.6 * (np.abs(a) / (L / 2)) ** 3) & (Z > -1.5 + np.abs(b) * 0.4)
        fill(m, (bx - 9, bx + 9, by - 9, by + 9, -1.5, 3.0 + bob), "pitch", hull, tone=0.1)
        fill(m, (bx - 9, bx + 9, by - 9, by + 9, 1.0 + bob, 1.8 + bob), "wood", lambda X, Y, Z, h=hull: h(X, Y, Z), tone=0.3,
             only_solid=True)
    seg, hfun = _deck(m, mask, w, zd, ze, "wood", "wood_light", 0.0,
                      top_tone=lambda X, Y, Z: -0.6 * (((X + Y) % 2.2) < 0.4), thick=0.9)
    _rails(m, seg, w, zd, ze, 2.6, "straw", inset=0.35, tone=0.0)
    return m


def jetty(v, frame, frames, k):
    """A timber jetty on oak piles: a plank deck, bollards along the edge where boats tie up;
    its head (the end out in the water) carries a pair of bollards and a coil of rope."""
    mask = _mask(v)
    m = _m(1, 1, 8, k, below=2)
    w, zd = 5.0, 3.0
    seg, hfun = _deck(m, mask, w, zd, zd, "wood", "wood_light", 0.0,
                      top_tone=lambda X, Y, Z: -0.6 * (((X + Y) % 2.0) < 0.35) + (hash01(np.floor(X - Y).astype(np.int64), 6041) - 0.5) * 0.5,
                      thick=1.0)
    for d in seg:
        for sgn in (-1, 1):
            for t in (2.0, 7.0):
                px, py = {"n": (8 + sgn * (w - 0.5), t), "s": (8 + sgn * (w - 0.5), 16 - t), "e": (16 - t, 8 + sgn * (w - 0.5)),
                          "w": (t, 8 + sgn * (w - 0.5))}[d]
                rod(m, (px, py, -2.0), (px, py, zd + (0.8 if t == 7.0 else -0.2)), 0.6, "wood", tone=0.1)
        if seg[d] == "end" or len(seg) == 1:
            for sgn in (-1, 1):
                px, py = {"n": (8 + sgn * 3.2, 2.5), "s": (8 + sgn * 3.2, 13.5), "e": (13.5, 8 + sgn * 3.2), "w": (2.5, 8 + sgn * 3.2)}[d]
                revolve(m, px, py, zd, zd + 2.0, lambda t: 0.9 - 0.2 * t, "wood", tone=0.2)
    ellipsoid(m, (6.0, 9.5, zd + 0.4), (1.3, 1.3, 0.5), "straw", tone=-0.1)
    return m


def mole(v, frame, frames, k):
    """A harbour mole: a breakwater of rough boulders sloping into the water under a dressed
    stone top with bollards; gulls perch on it. The head is rounded."""
    mask = _mask(v)
    m = _m(1, 1, 12, k, below=2, pad=5)
    seg = _segments(mask)
    w, zt = 4.5, 6.0

    def dist(X, Y):
        d = np.full(np.broadcast(X, Y).shape, 1e3)
        for dd, kind in seg.items():
            t, s, ok = _seg_frame(dd, X, Y)
            reach = 1.0 if kind == "arm" else 0.55
            d = np.where(ok & (t <= reach), np.minimum(d, np.abs(s)), d)
        return np.minimum(d, np.hypot(X - 8, Y - 8))

    def rubble_top(X, Y):
        dd = dist(X, Y)
        return np.where(dd < w, zt, zt - (dd - w) * 1.6) + (value_noise(X, Y, X * 0, 1.4, 6050) - 0.5) * 1.6

    def rubble_tone(X, Y, Z):
        h = hash01(np.floor(X / 1.6).astype(np.int64), np.floor(Y / 1.6).astype(np.int64), np.floor(Z / 1.4).astype(np.int64), 6051)
        return (h - 0.5) * 1.3 - 0.7 * (Z < 0.8)
    from arch import field_fill
    field_fill(m, (-5, 21, -5, 21, -2.0, zt + 1), lambda X, Y, Z: Z - rubble_top(X, Y), "stone", tone=rubble_tone)
    fill(m, (-1, 17, -1, 17, zt - 0.5, zt + 1.0), "attic_rock", lambda X, Y, Z: dist(X, Y) < w - 0.5,
         tone=M.ashlar(1.5, 4.0, 6052, spread=0.35))
    for (x, y) in ((8 - 3.0, 8 - 3.0), (8 + 3.0, 8 + 3.0)):
        if dist(np.array(x), np.array(y)) < w - 1:
            revolve(m, x, y, zt + 1.0, zt + 3.2, lambda t: 0.9 - 0.2 * t, "attic_rock", tone=0.3)
    return m


def _jetty_slots(v):
    """Mooring on the water beside the deck, facing it; loading on the deck."""
    seg = _segments(_mask(v))
    along_y = "n" in seg or "s" in seg
    moor = {"t": [1, 0], "face": "-x"} if along_y else {"t": [0, 1], "face": "-y"}
    return {"mooring": [moor], "load": [{"t": [0, 0]}]}


def _mole_slots(v):
    seg = _segments(_mask(v))
    along_y = "n" in seg or "s" in seg
    moor = {"t": [1, 0], "face": "-x"} if along_y else {"t": [0, 1], "face": "-y"}
    return {"mooring": [moor], "perch": [{"t": [0, 0], "off": [-6, -3], "z": 18}, {"t": [0, 0], "off": [6, 3], "z": 18}]}


def terrace_wall(v, frame, frames, k):
    """A dry-stone retaining wall standing a course above the ground: rough stones fitted
    without mortar, a few tufts in the joints (olive and vine terraces)."""
    mask = _mask(v)
    m = _m(1, 1, 9, k)
    seg = _segments(mask)
    w = 1.6
    for d, kind in seg.items():
        reach = 1.0 if kind == "arm" else 0.6

        def mk(X, Y, Z, d=d, reach=reach):
            t, s, ok = _seg_frame(d, X, Y)
            top = 6.5 + (value_noise(X, Y, X * 0, 1.5, 6060) - 0.5) * 1.2
            return ok & (t <= reach) & (np.abs(s) < w) & (Z < top)
        fill(m, (-0.5, 16.5, -0.5, 16.5, 0.0, 8.0), "stone", mk, tone=M.ashlar(1.6, 2.8, 6061, polygonal=0.9, spread=0.9))
    fill(m, (6.5, 9.5, 6.5, 9.5, 0.0, 6.8), "stone", tone=M.ashlar(1.6, 2.8, 6062, polygonal=0.9, spread=0.9))
    fill(m, (-0.5, 16.5, -0.5, 16.5, 5.5, 8.0), "olive",
         lambda X, Y, Z: (hash01(np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64), 6063) < 0.04), tone=0.1, only_solid=True)
    return m


# ---------------------------------------------------------------- stairs and ramps

def stair_stone(v, frame, frames, k):
    """Rock-cut steps of one level rising toward -y across two tiles, treads worn hollow in the
    middle, the rock standing rough at both sides."""
    m = _m(1, 2, 14, k)
    n = 6
    for i in range(n):
        z = 8.0 * (i + 1) / n
        y0 = 32.0 - (i + 1) * 32.0 / n
        fill(m, (1.0, 15.0, y0, y0 + 32.0 / n, 0.0, z), "attic_rock",
             tone=lambda X, Y, Z, z=z, y0=y0: 0.7 * (Z > z - 0.6) - 0.8 * (Z <= z - 0.6) * (Y < y0 + 1.0)
             - 0.25 * (np.abs(X - 8) < 3.5) * (Z > z - 0.3) + (value_noise(X, Y, Z, 1.6, 6070 + i) - 0.5) * 0.5)
    for x0, x1 in ((-1.0, 1.6), (14.4, 17.0)):
        fill(m, (x0, x1, 0.0, 32.0, 0.0, 12.0), "attic_rock",
             lambda X, Y, Z: Z < 9.0 + 2.5 * value_noise(X, Y, X * 0, 2.0, 6076) - (Y / 32.0) * 6.0,
             tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.5, 6077) - 0.5) * 1.1)
    return m


def stair_earth(v, frame, frames, k):
    """Earth steps of one level held by logs, rising toward -y across two tiles."""
    m = _m(1, 2, 12, k)
    n = 5
    for i in range(n):
        z = 8.0 * (i + 1) / n
        y0 = 32.0 - (i + 1) * 32.0 / n
        slab(m, 1.0, 15.0, y0, y0 + 32.0 / n, 0.0, z, "sand", tone=lambda X, Y, Z, z=z: (value_noise(X, Y, Z, 1.2, 6080) - 0.5) * 0.7
             + 0.4 * (Z > z - 0.6) - 0.6)
        rod(m, (1.0, y0 + 0.8, z - 0.6), (15.0, y0 + 0.8, z - 0.6), 0.75, "wood", tone=0.2)
        for x in (2.0, 14.0):
            rod(m, (x, y0 + 1.6, z - 2.0), (x, y0 + 1.6, z + 0.4), 0.35, "wood")
    return m


def ramp(v, frame, frames, k):
    """A graded earth ramp of one level over four tiles, rising toward -y, its edges held by a
    kerb of stones (roads climbing between levels)."""
    m = _m(1, 4, 12, k)
    L = 64.0
    fill(m, (1.0, 15.0, 0.0, L, 0.0, 9.0), "sand", lambda X, Y, Z: Z < 8.0 * (L - Y) / L + 0.4,
         tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.5, 6090) - 0.5) * 0.6 - 0.9 * (np.abs(np.abs(X - 8) - 3.0) < 0.6)
         - 0.4 * (np.abs(X - 8) < 0.9) - 0.3)
    # Cross drains of laid stones every few metres, as on graded mountain roads.
    for y in (14.0, 30.0, 46.0):
        fill(m, (1.5, 14.5, y - 0.6, y + 0.6, 0.0, 9.0), "stone", lambda X, Y, Z: Z < 8.0 * (L - Y) / L + 0.7, tone=0.1)
    for x0 in (0.0, 14.5):
        fill(m, (x0, x0 + 1.5, 0.0, L, 0.0, 10.0), "stone", lambda X, Y, Z: Z < 8.0 * (L - Y) / L + 1.4,
             tone=M.ashlar(1.4, 2.6, 6091, polygonal=0.8, spread=0.8))
    return m


def ramp_basalt(v, frame, frames, k):
    """A Roman road climbing one level over four tiles: polygonal basalt paving with raised
    kerbstones (crepidines) and a gutter, as on the Appia (worldgen's request: per-road ramps)."""
    m = _m(1, 4, 12, k)
    L = 64.0

    def top(Y):
        return 8.0 * (L - Y) / L

    def poly(X, Y, Z):
        d1 = np.hypot((X * 0.9) % 2.6 - 1.3, (Y * 1.1) % 2.4 - 1.2)
        return (value_noise(X, Y, Z * 0, 1.3, 6092) - 0.5) * 0.9 - 1.0 * (d1 > 1.15) - 0.25
    fill(m, (2.0, 14.0, 0.0, L, 0.0, 9.0), "basalt", lambda X, Y, Z: Z < top(Y) + 0.4, tone=poly)
    for x0 in (0.4, 14.0):
        fill(m, (x0, x0 + 1.6, 0.0, L, 0.0, 10.0), "travertine", lambda X, Y, Z: Z < top(Y) + 1.4,
             tone=M.ashlar(1.4, 3.2, 6093, spread=0.4))
    return m


def ramp_royal(v, frame, frames, k):
    """The Royal Road climbing one level over four tiles: a broad graded bed of pale packed
    gravel, cambered, edged with set stones, a cross drain of laid slabs (as the flat road)."""
    m = _m(1, 4, 12, k)
    L = 64.0

    def top(X, Y):
        return 8.0 * (L - Y) / L + 0.5 * (1 - ((X - 8.0) / 6.5) ** 2)
    fill(m, (1.0, 15.0, 0.0, L, 0.0, 9.5), "sand", lambda X, Y, Z: Z < top(X, Y),
         tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z, 1.0, 6094) - 0.5) * 0.7 + 0.2)
    for y in (20.0, 44.0):
        fill(m, (1.5, 14.5, y - 0.8, y + 0.8, 0.0, 9.5), "limestone", lambda X, Y, Z: Z < top(X, Y) + 0.2, tone=0.1)
    for x0 in (0.2, 14.8):
        fill(m, (x0, x0 + 1.0, 0.0, L, 0.0, 10.0), "limestone", lambda X, Y, Z: Z < 8.0 * (L - Y) / L + 0.9,
             tone=M.ashlar(0.9, 2.2, 6095, polygonal=0.6, spread=0.7))
    return m


def stile(v, frame, frames, k):
    """A dry-stone wall (along y) stepped as a stile: flat stones jut out on both faces so a
    walker climbs over (the corner's dell); walkable."""
    m = _m(1, 1, 10, k)
    fill(m, (6.2, 9.8, -0.5, 16.5, 0.0, 9.0), "stone",
         lambda X, Y, Z: Z < 8.0 - 3.0 * np.clip(1 - np.abs(Y - 8) / 4.0, 0, 1) + (value_noise(X, Y, X * 0, 1.5, 6100) - 0.5),
         tone=M.ashlar(1.5, 2.6, 6101, polygonal=0.9, spread=0.9))
    for z, x0, x1 in ((2.4, 2.5, 6.2), (2.4, 9.8, 13.5), (4.4, 4.5, 6.2), (4.4, 9.8, 11.5)):
        slab(m, x0, x1, 6.0, 10.0, z - 1.0, z, "stone", tone=0.35)
    return m


def milestone(v, frame, frames, k):
    """A plain uninscribed milestone on the corner's old road: a rough pillar with a rounded
    top, lichen on its north side, a tuft at its foot."""
    m = _m(1, 1, 14, k)
    revolve(m, 8, 5.0, 0.0, 11.0, lambda t: 1.9 - 0.25 * t, "stone",
            tone=lambda X, Y, Z: (value_noise(X, Y, Z, 0.9, 6110) - 0.5) * 0.7)
    ellipsoid(m, (8, 5.0, 11.0), (1.7, 1.7, 1.2), "stone", tone=0.3)
    fill(m, (5, 11, 2, 8, 3.0, 11.0), "olive", lambda X, Y, Z: (Y < 4.0) & (value_noise(X, Y, Z, 1.2, 6111) > 0.62),
         tone=0.0, only_solid=True)
    for a in np.linspace(0, 2 * math.pi, 6, endpoint=False):
        rod(m, (8.8, 6.6, 0), (8.8 + 1.4 * math.cos(a), 6.6 + 1.4 * math.sin(a), 1.6), 0.2, "summer")
    return m


def wayside_shrine(v, frame, frames, k):
    """A rustic wayside shrine for no named god: a stone pillar with a gabled niche facing the
    road (+y), a lamp and offerings in it, flowers and a small cup on the step."""
    m = _m(1, 1, 24, k)
    slab(m, 4.5, 11.5, 4.0, 11.0, 0.0, 2.0, "stone", tone=M.ashlar(1.0, 3.0, 6120, polygonal=0.7))
    slab(m, 5.5, 10.5, 5.0, 9.5, 2.0, 15.0, "stone", tone=M.ashlar(1.6, 3.0, 6121, polygonal=0.7))
    carve(m, (6.6, 9.4, 7.5, 9.6, 8.0, 12.5))
    tiled_roof(m, 4.8, 11.2, 4.2, 10.4, 15.0, 3.2, axis="y", material="terracotta", seed=6122, antefixes=False)
    ellipsoid(m, (8.0, 8.6, 8.6), (0.6, 0.6, 0.5), "lamp", tone=0.2)
    halo(m, 8.0, 9.0, 9.0, 6.0, LAMP, 0.5)
    for x, mat in ((6.0, "poppy"), (7.2, "white_paint"), (9.6, "yellow")):
        rod(m, (x, 10.6, 2.0), (x, 10.8, 3.6), 0.2, "leaf")
        ellipsoid(m, (x, 10.8, 3.9), (0.5, 0.5, 0.4), mat, tone=0.3)
    revolve(m, 8.5, 10.4, 2.0, 2.9, lambda t: 0.6 + 0.3 * t, "clay", tone=0.1)
    return m


# ---------------------------------------------------------------- the Royal Road and the heights

def royal_station(v, frame, frames, k):
    """A Royal Road station (Herodotus 5.52; rations at stations a day apart in the Persepolis
    Fortification texts): a walled compound of plastered mudbrick on a stone footing, a
    flat-roofed range with beam ends at the back, a reed-and-pole stable lean-to, a timber-
    lintel gate on the front (+y) with a lamp, a trough and hitching posts in the open front
    strip where couriers change horses."""
    m = _m(4, 4, 30, k)
    z = 16.0
    walls = ((2.0, 4.0, 2.0, 46.0), (60.0, 62.0, 2.0, 46.0), (2.0, 62.0, 2.0, 4.0), (2.0, 24.0, 44.0, 46.0),
             (40.0, 62.0, 44.0, 46.0))
    for i, (x0, x1, y0, y1) in enumerate(walls):
        mudbrick_wall(m, x0, x1, y0, y1, 0.0, z, plinth=2.5, seed=6130 + i)
        M.parapet(m, x0, x1, y0, y1, z, 2.0, material="mudbrick", pitch=3.0, sides=("+x", "+y"))
    # The range at the back (-y): rooms under a flat roof on beams.
    mudbrick_wall(m, 4.0, 60.0, 4.0, 18.0, 0.0, 20.0, plinth=2.5, seed=6136)
    M.beam_ends(m, "+y", (4.0, 60.0, 4.0, 18.0), 18.8, spacing=3.4, r=0.6, out=0.8)
    M.roof(m, 4.0, 60.0, 4.0, 18.0, 20.6, seed=6137, kind="domestic", hatches=1, rollers=1, clutter=2)
    for s0 in (10.0, 26.0, 42.0):
        fill(m, face_box("+y", 4.0, 60.0, 4.0, 18.0, 0.0, 10.0, s0, s0 + 4.5, -0.2, 0.4), "ink", tone=0.0)
    # The stable lean-to along the east (+x) wall: poles and a reed roof, mangers, a horse's straw.
    for y in (22.0, 30.0, 38.0):
        rod(m, (52.0, y, 0.0), (52.0, y, 12.0), 0.5, "wood")
    fill(m, (51.0, 61.0, 19.0, 43.0, 12.0, 15.0), "straw", lambda X, Y, Z: Z < 15.0 - (61.0 - X) * 0.25,
         tone=lambda X, Y, Z: -0.4 * ((Y * 2.0) % 1.0 < 0.3))
    slab(m, 55.0, 59.0, 21.0, 41.0, 0.0, 3.0, "wood", tone=M.timber("y", 6138))
    ellipsoid(m, (28.0, 30.0, 0.6), (6.0, 4.0, 0.6), "straw", tone=0.2)
    # The gate: a timber lintel between the wall ends, leaves standing open.
    slab(m, 22.0, 42.0, 43.4, 46.6, z - 1.0, z + 1.6, "cedar", tone=M.timber("x", 6139))
    for x in (24.0, 40.0):
        slab(m, x - 0.4, x + 0.4, 39.0, 44.0, 0.0, 13.0, "cedar", tone=M.timber("y", 6140))
    rod(m, (43.5, 47.0, 10.0), (43.5, 47.6, 12.0), 0.3, "metal")
    ellipsoid(m, (43.5, 47.8, 12.4), (0.7, 0.7, 0.9), "lamp", tone=0.2)
    halo(m, 43.5, 47.8, 12.4, 9.0, LAMP, 0.8)
    # The open front strip: a stone trough, hitching posts, a bench against the south wall.
    slab(m, 50.0, 62.0, 52.0, 58.0, 0.0, 3.4, "ashlar", tone=M.ashlar(1.7, 6.0, 6141))
    fill(m, (51.0, 61.0, 53.0, 57.0, 2.0, 3.0), "water", tone=0.2)
    for x in (4.0, 20.0):
        rod(m, (x, 60.0, 0.0), (x, 60.0, 7.0), 0.45, "wood", tone=0.1)
    slab(m, 62.0, 64.0, 18.0, 40.0, 0.0, 2.6, "wood", tone=M.timber("y", 6142))
    return m


STATION_SLOTS = {
    "door": [{"t": [1, 3], "face": "-y"}],
    "change": [{"t": [0, 3], "face": "+y"}, {"t": [2, 3], "face": "+y"}],
    "horse": [{"t": [0, 4], "face": "+x"}, {"t": [1, 4], "face": "+x"}],
    "trough": [{"t": [3, 4], "face": "-y"}, {"t": [4, 3], "face": "-x"}],
    "rest": [{"t": [4, 1], "face": "+x"}, {"t": [4, 2], "face": "+x"}],
}


def watchtower(v, frame, frames, k):
    """A watchtower at a pass or river gate: a square rubble tower of two storeys with a door,
    slit windows, a timber gallery and parapet on top where the fire basket burns, a ladder."""
    m = _m(2, 2, 50, k)
    x0, x1, y0, y1 = 6.0, 26.0, 6.0, 26.0
    slab(m, x0 - 1, x1 + 1, y0 - 1, y1 + 1, 0.0, 3.0, "stone", tone=M.ashlar(1.5, 4.0, 6150, polygonal=0.8, spread=0.8))
    slab(m, x0, x1, y0, y1, 3.0, 36.0, "stone", tone=M.ashlar(1.8, 4.0, 6151, polygonal=0.7, spread=0.8))
    rod(m, (x0, y0, 18.5), (x1, y0, 18.5), 0.4, "wood")
    for face in ("+x", "+y"):
        for zz in (13.0, 26.0):
            fill(m, face_box(face, x0, x1, y0, y1, zz, zz + 4.0, 9.0, 11.0, -0.2, 1.0), "ink", tone=0.0)
    fill(m, face_box("+y", x0, x1, y0, y1, 3.0, 11.0, 7.0, 13.0, -0.2, 1.2), "cedar", tone=M.timber("y", 6152))
    slab(m, x0 - 2.5, x1 + 2.5, y0 - 2.5, y1 + 2.5, 36.0, 37.4, "wood", tone=M.timber("x", 6153))
    for (a, b) in ((x0 - 2, y0 - 2), (x1 + 2, y0 - 2), (x0 - 2, y1 + 2), (x1 + 2, y1 + 2)):
        rod(m, (a, b, 37.0), (a, b, 41.0), 0.4, "wood")
        rod(m, (a, b, 30.0), ((a + 16) / 2, (b + 16) / 2, 36.0), 0.35, "wood")
    for side in ((x0 - 2, x1 + 2, y1 + 1.6, y1 + 2.2), (x1 + 1.6, x1 + 2.2, y0 - 2, y1 + 2)):
        slab(m, side[0], side[1], side[2], side[3], 39.0, 40.4, "wood", tone=0.2)
    revolve(m, 16.0, 16.0, 37.4, 40.0, lambda t: 1.6 + 0.6 * t, "metal", tone=0.1)
    ellipsoid(m, (16.0, 16.0, 40.6), (1.4, 1.4, 1.0), "ember", tone=0.1)
    halo(m, 16.0, 16.0, 41.0, 16.0, FIRE, 0.9)
    for x in (29.0, 31.0):         # the ladder up the +x side
        rod(m, (x, 18.0, 0.0), (x - 0.4, 18.0, 36.0), 0.3, "wood")
    for zz in np.arange(2.0, 36.0, 3.0):
        rod(m, (29.0, 18.0, zz), (31.0, 18.0, zz), 0.22, "wood")
    return m


def beacon(v, frame, frames, k):
    """A beacon: a stack of brushwood and logs on a round stone platform, ready to be lit (its
    glow and the fire effect show only when the `lit` state is on; Aeschylus, Agamemnon 281-316)."""
    m = _m(1, 1, 22, k)
    revolve(m, 8, 8, 0.0, 4.0, lambda t: 6.8 - 0.6 * t, "stone", tone=M.ashlar(1.4, 3.0, 6160, polygonal=0.8))
    for i in range(14):
        a = i * 2 * math.pi / 14
        rod(m, (8 + 4.2 * math.cos(a), 8 + 4.2 * math.sin(a), 4.0), (8 + 0.6 * math.cos(a), 8 + 0.6 * math.sin(a), 15.0),
            0.55, ("wood", "wood_grey")[i % 2], tone=0.1)
    ellipsoid(m, (8, 8, 7.5), (3.4, 3.4, 3.4), "straw", tone=-0.3)
    ellipsoid(m, (8, 8, 6.0), (0.8, 0.8, 0.8), "ember", tone=0.0)
    halo(m, 8, 8, 12.0, 18.0, FIRE, 1.0)
    return m


# ---------------------------------------------------------------- herders and fields

def sheepfold(v, frame, frames, k):
    """A dry-stone sheepfold topped with thorn brush, a gap with a hurdle gate on the front (+y),
    a lean-to hut of stone and branches in the back corner; the pen inside is walkable."""
    m = _m(3, 3, 22, k)
    ring = lambda X, Y: (np.maximum(np.abs(X - 24), np.abs(Y - 24)) > 19.5) & (np.maximum(np.abs(X - 24), np.abs(Y - 24)) < 22.5)
    gap = lambda X, Y: (np.abs(X - 24) < 5.0) & (Y > 40)
    fill(m, (0, 48, 0, 48, 0.0, 7.5), "stone",
         lambda X, Y, Z: ring(X, Y) & ~gap(X, Y) & (Z < 6.0 + (value_noise(X, Y, X * 0, 1.5, 6170) - 0.5) * 1.6),
         tone=M.ashlar(1.5, 2.6, 6171, polygonal=0.9, spread=0.9))
    fill(m, (0, 48, 0, 48, 5.0, 10.0), "wood_grey",
         lambda X, Y, Z: ring(X, Y) & ~gap(X, Y) & (Z < 6.0 + 3.0 * value_noise(X, Y, Z, 0.8, 6172)) &
         (hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), np.floor(Z * 2).astype(np.int64), 6173) < 0.45),
         tone=0.1, only_empty=True)
    for x in (19.0, 29.0):
        rod(m, (x, 44.0, 0.0), (x, 44.0, 7.0), 0.45, "wood")
    for zz in (2.0, 4.5):          # the hurdle standing open
        rod(m, (29.0, 44.0, zz), (29.0, 36.0, zz), 0.3, "wood_light")
    # The lean-to hut in the back corner (tile 0, 0).
    slab(m, 3.0, 14.0, 3.0, 14.0, 0.0, 8.0, "stone", tone=M.ashlar(1.5, 2.6, 6174, polygonal=0.9))
    fill(m, (1.5, 15.5, 1.5, 15.5, 8.0, 13.0), "straw", lambda X, Y, Z: Z < 13.0 - (X - 1.5) * 0.35,
         tone=lambda X, Y, Z: -0.4 * ((X * 2.0) % 1.0 < 0.3))
    fill(m, face_box("+y", 3.0, 14.0, 3.0, 14.0, 0.0, 6.0, 3.5, 7.5, -0.2, 0.3), "ink", tone=0.0)
    ellipsoid(m, (24, 24, 0.4), (8.0, 6.0, 0.5), "straw", tone=0.0)
    return m


FOLD_SLOTS = {"pen": [{"t": [1, 1], "off": [-6, -2]}, {"t": [1, 1], "off": [6, 2]}, {"t": [1, 1], "off": [0, 5]}],
              "gate": [{"t": [1, 3], "face": "-y"}]}


def field_hut(v, frame, frames, k):
    """A field shelter: r0 a corbelled dry-stone hut with a low door (the Mediterranean),
    r1 a shelter of reeds and brush on poles (the East)."""
    m = _m(1, 1, 18, k)
    if v == 0:
        def dome(X, Y, Z):
            r = np.hypot(X - 8, Y - 7)
            return (r < 6.0 * np.clip(1 - (Z / 15.0) ** 1.6, 0, 1))
        fill(m, (1, 15, 0, 14, 0.0, 15.0), "stone", dome, tone=M.ashlar(1.2, 2.4, 6180, polygonal=0.9, spread=0.9))
        carve(m, (6.6, 9.4, 10.0, 14.0, 0.0, 5.0))
        fill(m, (6.6, 9.4, 9.0, 10.0, 0.0, 5.0), "ink", tone=0.0)
        slab(m, 6.0, 10.0, 12.0, 13.4, 5.0, 6.0, "stone", tone=0.3)
    else:
        for (x, y) in ((3, 3), (13, 3), (3, 12), (13, 12)):
            rod(m, (x, y, 0.0), (x, y, 10.0 if y < 8 else 8.0), 0.45, "wood")
        fill(m, (1.5, 14.5, 1.5, 13.5, 7.0, 11.5), "straw", lambda X, Y, Z: Z < 11.0 - (Y - 1.5) * 0.25,
             tone=lambda X, Y, Z: -0.4 * ((X * 2.0) % 1.0 < 0.3))
        fill(m, (2.0, 3.0, 3.0, 12.0, 0.0, 9.0), "straw", tone=lambda X, Y, Z: -0.5 * ((Y * 1.6) % 1.0 < 0.25))
        ellipsoid(m, (8, 7, 0.5), (4.0, 3.0, 0.6), "straw", tone=0.2)
    return m


def charcoal_kiln(v, frame, frames, k):
    """A charcoal burners' stack (Acharnai, the Apennines): r0 the earth-covered mound smoking
    from vents round its foot, embers glowing in them at night; r1 the wood stacked upright
    ready for covering, a heap of turf and a rake."""
    m = _m(2, 2, 20, k)
    c = 16.0
    if v == 0:
        from arch import field_fill
        field_fill(m, (2, 30, 2, 30, 0.0, 16.0), lambda X, Y, Z: Z - 14.0 * np.clip(1 - (np.hypot(X - c, Y - c) / 12.5) ** 2, 0, 1),
                   "soil", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.4, 6190) - 0.5) * 0.9)
        for a in np.linspace(0, 2 * math.pi, 7, endpoint=False):
            x, y = c + 11.0 * math.cos(a), c + 11.0 * math.sin(a)
            carve(m, (x - 1, x + 1, y - 1, y + 1, 1.0, 3.5))
            ellipsoid(m, (c + 10.0 * math.cos(a), c + 10.0 * math.sin(a), 2.0), (0.6, 0.6, 0.6), "ember", tone=0.0)
        halo(m, c, c, 3.0, 14.0, FIRE, 0.45)
        fill(m, (2, 30, 2, 30, 8.0, 16.0), "wood_grey", lambda X, Y, Z: (np.hypot(X - c, Y - c) < 2.2) & (Z < 15.0), tone=0.0)
    else:
        for r, n, h in ((2.0, 6, 13.0), (5.0, 12, 12.0), (8.0, 18, 10.5), (11.0, 24, 8.5)):
            for i in range(n):
                a = i * 2 * math.pi / n
                x, y = c + r * math.cos(a), c + r * math.sin(a)
                rod(m, (x, y, 0.0), (x - 0.4 * math.cos(a), y - 0.4 * math.sin(a), h), 0.55, ("wood", "wood_light")[i % 2], tone=0.1)
        fill(m, (22, 31, 0, 9, 0.0, 4.0), "soil", lambda X, Y, Z: Z < 3.5 - np.hypot(X - 26.5, Y - 4.5) * 0.6, tone=0.2)
        rod(m, (4.0, 26.0, 0.2), (10.0, 30.0, 4.0), 0.25, "wood")
    return m


def fish_hut(v, frame, frames, k):
    """A fisherman's hut of stone and reed under a thatch, its door on the front (+y), nets
    hung on a pole and oars leaning by the door, a lamp in the window at night."""
    m = _m(1, 2, 24, k)
    house_wall(m, 2.0, 14.0, 3.0, 26.0, 0.0, 10.0, seed=6200, socle=4.0, plaster="cream")
    fill(m, (0.5, 15.5, 1.5, 27.5, 10.0, 17.0), "straw",
         lambda X, Y, Z: Z < 17.0 - np.abs(X - 8.0) * 1.0, tone=lambda X, Y, Z: -0.45 * ((Y * 1.8) % 1.0 < 0.3) + 0.1)
    fill(m, face_box("+y", 2.0, 14.0, 3.0, 26.0, 0.0, 7.5, 4.5, 7.5, -0.2, 0.3), "cedar", tone=M.timber("x", 6201))
    fill(m, face_box("+x", 2.0, 14.0, 3.0, 26.0, 5.0, 7.5, 9.0, 11.0, -0.2, 0.3), "lamp", tone=0.0)
    halo(m, 14.4, 16.0, 6.2, 7.0, LAMP, 0.5)
    rod(m, (14.5, 28.0, 0.0), (14.5, 28.0, 10.0), 0.35, "wood")
    rod(m, (14.5, 28.0, 9.5), (14.5, 18.0, 10.5), 0.3, "wood")
    fill(m, (13.8, 15.2, 18.0, 28.0, 3.0, 10.0), "wood_grey",
         lambda X, Y, Z: (((Y + Z) % 1.6) < 0.3) | (((Y - Z) % 1.6) < 0.3), tone=0.1)
    for y in (27.5, 29.0):
        rod(m, (2.0, y, 0.0), (0.5, y + 0.6, 11.0), 0.3, "wood_light", tone=0.1)
    return m


def drying_rack(v, frame, frames, k):
    """A pole frame by the shore with a net hung to dry and split fish on the bar."""
    m = _m(1, 1, 16, k)
    for y in (2.0, 14.0):
        rod(m, (7.0, y, 0.0), (8.0, y, 12.0), 0.4, "wood")
        rod(m, (9.0, y, 0.0), (8.0, y, 12.0), 0.4, "wood")
    rod(m, (8.0, 1.0, 12.0), (8.0, 15.0, 12.0), 0.35, "wood")
    fill(m, (7.6, 8.4, 2.5, 8.5, 4.0, 11.6), "wood_grey",
         lambda X, Y, Z: (((Y + Z) % 1.4) < 0.25) | (((Y - Z) % 1.4) < 0.25), tone=0.15)
    for y in np.arange(9.5, 14.0, 1.4):
        fill(m, (7.4, 8.6, y - 0.4, y + 0.4, 8.5, 11.8), "white_paint", lambda X, Y, Z: True, tone=0.1)
        fill(m, (7.3, 8.7, y - 0.2, y + 0.2, 8.5, 9.4), "stone", tone=0.0)
    return m


def shaduf(v, frame, frames, k):
    """A shaduf on a canal bank: an upright of mud and timber, a long sweep pivoting on it with
    a clay counterweight, the bucket on its rope dipping toward the water (+y) and lifting (two
    frames)."""
    m = _m(1, 1, 30, k, pad=12)
    slab(m, 6.0, 10.0, 4.0, 8.0, 0.0, 6.0, "mudbrick", tone=M.mud_plaster(6210, 0.4, 0.0, 2.0))
    rod(m, (7.0, 6.0, 6.0), (7.0, 6.0, 15.0), 0.45, "wood")
    rod(m, (9.0, 6.0, 6.0), (9.0, 6.0, 15.0), 0.45, "wood")
    rod(m, (6.6, 6.0, 15.0), (9.4, 6.0, 15.0), 0.3, "wood")
    tilt = (0.45, -0.25)[frame % 2]
    L1, L2 = 9.0, 15.0
    p0 = (8.0, 6.0 - L1 * math.cos(tilt), 15.0 - L1 * math.sin(tilt))
    p1 = (8.0, 6.0 + L2 * math.cos(tilt), 15.0 + L2 * math.sin(tilt))
    rod(m, p0, p1, 0.4, "wood_light", tone=0.1)
    ellipsoid(m, (p0[0], p0[1], p0[2] - 1.0), (1.6, 1.6, 1.6), "clay", tone=0.0)
    drop = 8.0
    rod(m, p1, (p1[0], p1[1], p1[2] - drop), 0.12, "wood")
    revolve(m, p1[0], p1[1], p1[2] - drop - 2.4, p1[2] - drop, lambda t: 1.0 + 0.3 * t, "hide", tone=0.1)
    return m


def reed_hut(v, frame, frames, k):
    """A marsh house of bundled reeds: arches of reed bundles bent over and tied, mat walls
    between them, a decorated end with tall bundle-posts on the front (+y), as on Uruk-period
    seals and the marsh reliefs of Assyria; a fire glows in the doorway at night."""
    m = _m(2, 2, 26, k)
    x0, x1, y0, y1 = 5.0, 27.0, 3.0, 29.0
    cx, R = 16.0, 11.0

    def vault(X, Y, Z):
        return (Y > y0) & (Y < y1) & (np.hypot(X - cx, Z * 0.95) < R) & (np.hypot(X - cx, Z * 0.95) > R - 1.2)
    fill(m, (x0, x1, y0, y1, 0.0, 13.0), "straw", vault,
         tone=lambda X, Y, Z: -0.5 * ((Y % 3.0) < 0.7) + 0.25 * ((np.arctan2(Z, X - cx) * 9) % 1.0 < 0.3))
    fill(m, (x0, x1, y0 - 0.6, y0 + 0.6, 0.0, 13.0), "straw", lambda X, Y, Z: np.hypot(X - cx, Z * 0.95) < R,
         tone=lambda X, Y, Z: -0.4 * ((X % 1.5) < 0.3))
    fill(m, (x0, x1, y1 - 0.6, y1 + 0.6, 0.0, 13.0), "straw",
         lambda X, Y, Z: (np.hypot(X - cx, Z * 0.95) < R) & ~((np.abs(X - cx) < 2.6) & (Z < 8.0)),
         tone=lambda X, Y, Z: -0.4 * (((X + Z) % 1.6) < 0.35))
    fill(m, (cx - 2.6, cx + 2.6, y1 - 1.5, y1 - 0.5, 0.0, 8.0), "ink", tone=0.0)
    for x in (cx - 6.0, cx + 6.0):
        revolve(m, x, y1 + 0.4, 0.0, 16.0, lambda t: 1.3 - 0.4 * t, "straw", tone=-0.1)
        for zz in (5.0, 9.0, 13.0):
            revolve(m, x, y1 + 0.4, zz, zz + 0.8, lambda t: 1.4, "wood_light", tone=0.2)
        ellipsoid(m, (x, y1 + 0.4, 16.8), (1.4, 1.4, 1.2), "straw", tone=0.2)
    ellipsoid(m, (cx, y1 - 3.0, 0.6), (0.9, 0.9, 0.6), "ember", tone=0.0)
    halo(m, cx, y1 - 1.0, 2.5, 8.0, FIRE, 0.55)
    return m


def tumulus(v, frame, frames, k):
    """A burial mound of earth grown over with grass: r0 with a stone ring wall (krepis) at its
    foot and a marker on top, as at the Lydian royal mounds of Bin Tepe; r1 plain."""
    m = _m(3, 3, 24, k)
    c = 24.0
    from arch import field_fill
    R = 21.0 if v == 0 else 22.5
    field_fill(m, (0, 48, 0, 48, 0.0, 22.0), lambda X, Y, Z: Z - (19.0 if v == 0 else 16.0) * np.clip(1 - (np.hypot(X - c, Y - c) / R) ** 2, 0, 1) ** 0.8,
               "steppe", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.6, 6230 + v) - 0.5) * 0.7)
    fill(m, (0, 48, 0, 48, 0.0, 22.0), "olive", lambda X, Y, Z: value_noise(X, Y, Z * 0, 2.5, 6231) > 0.62, tone=-0.2,
         only_solid=True)
    if v == 0:
        fill(m, (0, 48, 0, 48, 0.0, 3.5), "attic_rock",
             lambda X, Y, Z: (np.hypot(X - c, Y - c) > R - 1.6) & (np.hypot(X - c, Y - c) < R + 0.4),
             tone=M.ashlar(1.7, 4.0, 6232, spread=0.5))
        revolve(m, c, c, 18.0, 24.0, lambda t: 1.4 * (1 - t) + 0.4, "attic_rock", tone=0.3)
    return m


# ---------------------------------------------------------------- nice to have

def inn(v, frame, frames, k):
    """A courtyard inn (Greek pandokeion, Roman caupona): rubble walls plastered, rooms under a
    tiled roof round a yard, a gate on the front (+y) with a painted sign, a trough by it, a
    bench and a lamp."""
    m = _m(4, 4, 34, k)
    for i, (x0, x1, y0, y1) in enumerate(((2, 18, 2, 62), (46, 62, 2, 62), (18, 46, 2, 16))):
        house_wall(m, x0, x1, y0, y1, 0.0, 16.0, seed=6240 + i, socle=4.0, plaster="whitewash")
    house_wall(m, 18.0, 25.0, 59.0, 62.0, 0.0, 10.0, seed=6243, socle=3.0, plaster="whitewash")
    house_wall(m, 39.0, 46.0, 59.0, 62.0, 0.0, 10.0, seed=6244, socle=3.0, plaster="whitewash")
    tiled_roof(m, 1.0, 19.0, 1.0, 63.0, 16.0, 6.0, axis="y", material="terracotta", seed=6245, antefixes=False)
    tiled_roof(m, 45.0, 63.0, 1.0, 63.0, 16.0, 6.0, axis="y", material="terracotta", seed=6246, antefixes=False)
    tiled_roof(m, 18.0, 46.0, 1.0, 17.0, 16.0, 6.0, axis="x", material="terracotta", seed=6247, antefixes=False)
    for face, box, s0 in (("+x", (46, 62, 2, 62), 10.0), ("+x", (46, 62, 2, 62), 36.0), ("+y", (46, 62, 2, 62), 5.0)):
        fill(m, face_box(face, *box, 0.0, 9.0, s0, s0 + 4.0, -0.2, 0.4), "cedar", tone=M.timber("y", 6248))
    fill(m, face_box("+y", 2, 18, 2, 62, 9.0, 11.0, 4.0, 11.0, -0.1, 0.3), "cinnabar", tone=0.2)
    slab(m, 25.0, 39.0, 60.0, 61.0, 10.0, 11.4, "wood", tone=M.timber("x", 6249))
    slab(m, 26.0, 38.0, 64.0, 67.0, 0.0, 3.2, "ashlar", tone=M.ashlar(1.6, 5.0, 6250))
    fill(m, (27.0, 37.0, 64.6, 66.4, 2.0, 3.0), "water", tone=0.2)
    ellipsoid(m, (32.0, 30.0, 0.6), (8.0, 6.0, 0.6), "straw", tone=0.1)
    revolve(m, 40.0, 40.0, 0.0, 4.0, lambda t: 1.6 * np.sin(np.pi * (0.2 + 0.6 * t)), "clay", tone=0.1)
    rod(m, (47.0, 63.0, 9.0), (47.0, 64.0, 11.0), 0.3, "metal")
    ellipsoid(m, (47.0, 64.2, 11.4), (0.7, 0.7, 0.9), "lamp", tone=0.2)
    halo(m, 47.0, 64.2, 11.4, 9.0, LAMP, 0.7, kind="door")
    return m


INN_SLOTS = {"door": [{"t": [2, 4], "face": "-y"}],
             "rest": [{"t": [0, 4], "face": "+y"}, {"t": [1, 4], "face": "+y"}, {"t": [3, 4], "face": "+y"}],
             "trough": [{"t": [1, 5], "face": "-y"}, {"t": [2, 5], "face": "-y"}]}


def cairn(v, frame, frames, k):
    """A roadside heap of stones (the Greek hermaion; pass cairns): r1 with a standing stone."""
    m = _m(1, 1, 12, k)
    rng = Rng(6260, v)
    for i in range(22):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 4.5)
        z = (4.5 - r) * 1.2 + rng.uniform(0, 1.5)
        ellipsoid(m, (8 + r * math.cos(a), 8 + r * math.sin(a), z), (rng.uniform(1.0, 1.6),) * 2 + (rng.uniform(0.7, 1.1),),
                  ("stone", "attic_rock")[i % 2], tone=rng.uniform(-0.3, 0.4))
    if v == 1:
        slab(m, 7.2, 8.8, 7.0, 9.0, 3.0, 11.0, "attic_rock", tone=0.2)
    return m


def matar_shrine(v, frame, frames, k):
    """A Phrygian rock-cut cult façade for the Mother (Matar): a smooth rock face carved as a
    house front with a gable and an acroterion, filled with interlocking geometric patterns,
    and a deep niche at its foot where her image stands (6th century, the Phrygian highlands)."""
    m = _m(2, 2, 40, k)
    from arch import field_fill
    field_fill(m, (0, 32, 0, 22, 0.0, 36.0), lambda X, Y, Z: (Y - 4.0 - 14.0 * np.clip(1 - Z / 36.0, 0, 1) ** 0.4
                                                             - (value_noise(X, Y, Z, 4.0, 6270) - 0.5) * 5.0),
               "attic_rock", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 6271) - 0.5) * 0.9)
    fy = 18.5
    fill(m, (6.0, 26.0, fy - 0.8, fy + 0.6, 2.0, 30.0), "poros",
         lambda X, Y, Z: (Z < 24.0) | (Z < 30.0 - np.abs(X - 16.0) * 0.6),
         tone=lambda X, Y, Z: 0.35 * ((((X - 6) // 2.5 + (Z - 2) // 2.5) % 2) == 0) * (Z > 12) * (Z < 23) - 0.1)
    fill(m, (15.0, 17.0, fy - 0.8, fy + 0.6, 29.0, 34.0), "poros", tone=0.3)
    carve(m, (12.5, 19.5, fy - 4.0, fy + 1.0, 2.0, 11.0))
    fill(m, (13.0, 19.0, fy - 4.6, fy - 3.4, 2.0, 11.0), "ink", tone=0.0)
    slab(m, 14.5, 17.5, fy - 3.2, fy - 1.0, 2.0, 3.0, "poros", tone=0.2)
    ellipsoid(m, (16.0, fy - 2.0, 6.5), (1.2, 1.0, 3.2), "poros", tone=0.3)
    ellipsoid(m, (16.0, fy - 2.0, 10.2), (0.8, 0.8, 0.9), "poros", tone=0.4)
    slab(m, 9.0, 23.0, fy + 0.6, fy + 5.0, 0.0, 2.0, "attic_rock", tone=0.2)
    return m


def cistern(v, frame, frames, k):
    """A rock-cut cistern: a round mouth with a stone lid half drawn back, a trough beside it,
    the rock dressed flat around."""
    m = _m(2, 2, 10, k)
    slab(m, 3.0, 29.0, 3.0, 29.0, 0.0, 1.6, "attic_rock", tone=M.ashlar(2.0, 6.0, 6280, polygonal=0.6))
    revolve(m, 13.0, 13.0, 1.6, 4.0, lambda t: 4.6, "attic_rock", tone=0.2)
    carve(m, (9.0, 17.0, 9.0, 17.0, 1.0, 4.1), lambda X, Y, Z: np.hypot(X - 13, Y - 13) < 3.2)
    fill(m, (9.0, 17.0, 9.0, 17.0, 0.0, 1.0), "water", lambda X, Y, Z: np.hypot(X - 13, Y - 13) < 3.2, tone=-0.3)
    fill(m, (11.0, 20.0, 11.0, 20.0, 4.0, 5.2), "stone", lambda X, Y, Z: np.hypot(X - 15.5, Y - 15.0) < 3.8, tone=0.3)
    slab(m, 19.0, 28.0, 21.0, 26.0, 1.6, 4.4, "attic_rock", tone=0.1)
    fill(m, (20.0, 27.0, 22.0, 25.0, 3.0, 4.0), "water", tone=0.2)
    return m


def haystack(v, frame, frames, k):
    """A straw stack round a pole; r1 half used, cut down one side."""
    m = _m(1, 1, 16, k)
    rod(m, (8, 8, 0), (8, 8, 15.0), 0.3, "wood")
    fill(m, (1, 15, 1, 15, 0.0, 13.0), "straw",
         lambda X, Y, Z: (np.hypot(X - 8, Y - 8) < 6.0 * np.clip(1 - (Z / 13.0) ** 2, 0, 1)) & ((v == 0) | (X < 9.5 - Z * 0.1)),
         tone=lambda X, Y, Z: -0.4 * ((Z * 1.5) % 1.0 < 0.25) + (value_noise(X, Y, Z, 0.8, 6290) - 0.5) * 0.5)
    return m


def treading_vat(v, frame, frames, k):
    """A plastered treading floor with a low rim, sloping to a spout over a sunken vat; baskets
    of grapes beside it."""
    m = _m(2, 2, 10, k)
    slab(m, 3.0, 27.0, 3.0, 20.0, 0.0, 3.0, "whitewash", tone=M.mud_plaster(6300, 0.3, 0.0, 1.0))
    carve(m, (4.5, 25.5, 4.5, 18.5, 2.2, 3.1))
    fill(m, (4.5, 25.5, 4.5, 18.5, 2.0, 2.3), "purple", lambda X, Y, Z: value_noise(X, Y, Z, 1.5, 6301) > 0.72, tone=-0.2)
    slab(m, 13.0, 17.0, 20.0, 22.0, 1.4, 2.0, "whitewash", tone=0.2)
    revolve(m, 15.0, 25.5, 0.0, 2.0, lambda t: 3.2, "whitewash", tone=0.1)
    carve(m, (11.0, 19.0, 22.0, 29.0, 0.4, 2.1), lambda X, Y, Z: np.hypot(X - 15, Y - 25.5) < 2.4)
    fill(m, (11.0, 19.0, 22.0, 29.0, 0.0, 0.6), "purple", lambda X, Y, Z: np.hypot(X - 15, Y - 25.5) < 2.4, tone=-0.2)
    for x in (24.0, 28.0):
        revolve(m, x, 26.0, 0.0, 3.0, lambda t: 1.6 + 0.3 * t, "straw", tone=0.0)
        ellipsoid(m, (x, 26.0, 3.0), (1.4, 1.4, 0.8), "purple", tone=0.2)
    return m


def boundary_stone(v, frame, frames, k):
    """A rough field marker: r0 a slab set on edge, r1 a squat pillar with a cut line on top."""
    m = _m(1, 1, 10, k)
    if v == 0:
        slab(m, 7.0, 9.0, 5.5, 10.5, 0.0, 7.5, "attic_rock", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.0, 6310) - 0.5) * 0.8)
    else:
        revolve(m, 8, 8, 0.0, 6.0, lambda t: 1.8 - 0.3 * t, "stone", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.0, 6311) - 0.5) * 0.7)
        fill(m, (7.9, 8.1, 6, 10, 5.6, 6.2), "ink", tone=0.0)
    return m


def quarry(v, frame, frames, k):
    """A small roadside quarry: a face cut back in steps at the back (-y), wedge slots in a line
    where the next block will split off, a block on rollers, chippings."""
    m = _m(3, 3, 28, k)
    from arch import field_fill
    def cut(X, Y):
        return np.where(Y < 14, 24.0, np.where(Y < 24, 15.0, np.where(Y < 32, 7.0, 0.0)))
    field_fill(m, (0, 48, 0, 34, 0.0, 26.0),
               lambda X, Y, Z: Z - cut(X, Y) - (value_noise(X, Y, X * 0, 3.0, 6320) - 0.5) * 1.2 * (Y < 6),
               "travertine", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.6, 6321) - 0.5) * 0.7
               - 0.6 * ((np.abs(Y - 14) < 0.5) | (np.abs(Y - 24) < 0.5) | (np.abs(Y - 32) < 0.5)))
    for x in np.arange(8.0, 40.0, 3.0):
        fill(m, (x - 0.4, x + 0.4, 22.5, 24.5, 13.5, 15.1), "ink", tone=0.0)
    slab(m, 18.0, 30.0, 36.0, 43.0, 1.4, 7.4, "travertine", tone=0.25)
    for x in (19.0, 24.0, 29.0):
        rod(m, (x, 35.0, 0.7), (x, 44.0, 0.7), 0.7, "wood_light")
    fill(m, (2, 46, 34, 47, 0.0, 0.6), "travertine",
         lambda X, Y, Z: hash01(np.floor(X * 1.5).astype(np.int64), np.floor(Y * 1.5).astype(np.int64), 6322) < 0.15, tone=0.4)
    return m


def log_stack(v, frame, frames, k):
    """Cedar logs stacked for hauling down to the shore, ends pale and ringed."""
    m = _m(1, 2, 12, k)
    for row, (n, z) in enumerate(((4, 1.6), (3, 4.4), (2, 7.2))):
        for i in range(n):
            x = 8.0 + (i - (n - 1) / 2) * 3.2
            rod(m, (x, 2.0, z), (x, 30.0, z), 1.55, "cedar", tone=lambda X, Y, Z: 0.2 * ((Y % 3.0) < 0.6) - 0.1)
            for y in (1.6, 30.4):
                fill(m, (x - 1.5, x + 1.5, y - 0.4, y + 0.4, z - 1.5, z + 1.5), "wood_light",
                     lambda X, Y, Z, x=x, z=z: np.hypot(X - x, Z - z) < 1.5,
                     tone=lambda X, Y, Z, x=x, z=z: -0.6 * ((np.hypot(X - x, Z - z) % 0.6) < 0.15))
    return m


def salt_pans(v, frame, frames, k):
    """Shallow salt pans in clay banks, the water evaporating to a white crust; r1 with a heap of
    raked salt and a rake."""
    m = _m(2, 2, 8, k)
    for (x0, y0) in ((2, 2), (17, 2), (2, 17), (17, 17)):
        slab(m, x0, x0 + 13, y0, y0 + 13, 0.0, 1.4, "clay", tone=0.0)
        carve(m, (x0 + 1.2, x0 + 11.8, y0 + 1.2, y0 + 11.8, 0.8, 1.5))
        fill(m, (x0 + 1.2, x0 + 11.8, y0 + 1.2, y0 + 11.8, 0.6, 0.9), "white_paint" if (x0 + y0) % 3 else "water",
             lambda X, Y, Z: value_noise(X, Y, Z, 1.6, 6330) > 0.25, tone=0.2)
    if v == 1:
        fill(m, (12, 20, 12, 20, 0.0, 6.0), "white_paint", lambda X, Y, Z: Z < 5.5 - np.hypot(X - 16, Y - 16) * 1.3, tone=0.3)
        rod(m, (20.0, 10.0, 0.4), (26.0, 14.0, 5.0), 0.25, "wood")
    return m


def tent_black(v, frame, frames, k):
    """A black goat-hair tent of the steppe herders ('the tents of Kedar'): a long low cloth on
    rows of poles, guy ropes, the front (+y) open with a hanging, a fire glowing in it at night."""
    m = _m(2, 2, 18, k)
    for x in (6.0, 16.0, 26.0):
        for y, h in ((8.0, 9.0), (16.0, 12.0), (24.0, 9.0)):
            rod(m, (x, y, 0.0), (x, y, h), 0.35, "wood")

    def cloth(X, Y, Z):
        top = 12.0 - np.abs(Y - 16.0) * 0.38
        sag = 0.7 * (1 - np.cos((X - 6.0) / 10.0 * 2 * math.pi)) * 0.5
        return (Z < top - sag + 0.5) & (Z > top - sag - 0.6) & (Y > 4.0) & (Y < 26.0)
    fill(m, (3.0, 29.0, 4.0, 26.0, 0.0, 13.0), "gloss", cloth, tone=lambda X, Y, Z: -0.3 * ((X % 2.0) < 0.3) + 0.2)
    fill(m, (3.0, 4.0, 4.0, 26.0, 0.0, 9.0), "gloss", lambda X, Y, Z: Z < 9.0 - np.abs(Y - 16) * 0.38, tone=0.0)
    fill(m, (4.0, 28.0, 7.0, 8.0, 0.0, 9.0), "gloss", lambda X, Y, Z: True, tone=0.1)
    for (x, y) in ((3.0, 2.0), (29.0, 2.0), (3.0, 30.0), (29.0, 30.0)):
        rod(m, (x, y, 0.0), (6.0 if x < 16 else 26.0, 8.0 if y < 16 else 24.0, 8.6), 0.12, "wood_light")
    ellipsoid(m, (16.0, 21.0, 0.5), (1.2, 1.2, 0.5), "ember", tone=0.0)
    halo(m, 16.0, 21.0, 2.0, 9.0, FIRE, 0.5)
    for x in (9.0, 23.0):
        ellipsoid(m, (x, 20.0, 0.8), (2.4, 1.6, 0.8), "cinnabar", tone=0.1)
    return m


def _i(fn, slots=None, emitters=None, walk=None):
    return Item(fn, slots=slots or {}, emitters=emitters or {}, walk=walk or [])


ITEMS = {
    "world.ford": _i(ford),
    "world.bridge_arch": _i(bridge_arch),
    "world.bridge_timber": _i(bridge_timber),
    "world.pontoon": _i(pontoon),
    "world.jetty": _i(jetty, slots=_jetty_slots),
    "world.mole": _i(mole, slots=_mole_slots),
    "world.stair_stone": _i(stair_stone),
    "world.stair_earth": _i(stair_earth),
    "world.ramp": _i(ramp),
    "world.ramp_basalt": _i(ramp_basalt),
    "world.ramp_royal": _i(ramp_royal),
    "world.stile": _i(stile),
    "world.milestone": _i(milestone, slots={"rest": [{"t": [0, 1], "face": "+y"}]}),
    "world.wayside_shrine": _i(wayside_shrine, slots={"pray": [{"t": [0, 1], "face": "-y"}]}),
    "world.royal_station": _i(royal_station, slots=STATION_SLOTS, walk=[(0, 3), (1, 3), (2, 3)]),
    "world.watchtower": _i(watchtower, slots={"guard": [{"t": [1, 2], "face": "+y"}]}, emitters={"fire": (16.0, 16.0, 41.0)}),
    "world.beacon": _i(beacon, slots={"tend": [{"t": [0, 1], "face": "-y"}]}, emitters={"fire": (8.0, 8.0, 14.0)}),
    "world.sheepfold": _i(sheepfold, slots=FOLD_SLOTS, walk=[(1, 1), (1, 2)]),
    "world.field_hut": _i(field_hut, slots={"shelter": [{"t": [0, 1], "face": "-y", "off": [-4, 0]},
                                                        {"t": [0, 1], "face": "-y", "off": [4, 0]}]}),
    "world.terrace_wall": _i(terrace_wall),
    "world.charcoal_kiln": _i(charcoal_kiln, slots={"tend": [{"t": [2, 1], "face": "-x"}]},
                              emitters={"smoke": (16.0, 16.0, 15.0)}),
    "world.fish_hut": _i(fish_hut, slots={"door": [{"t": [0, 2], "face": "-y"}]}),
    "world.drying_rack": _i(drying_rack, slots={"mend": [{"t": [1, 0], "face": "-x"}]}),
    "world.shaduf": _i(shaduf, slots={"lift": [{"t": [-1, 0], "face": "+x"}]}),
    "world.reed_hut": _i(reed_hut, slots={"door": [{"t": [1, 2], "face": "-y"}]}),
    "world.tumulus": _i(tumulus),
    "world.inn": _i(inn, slots=INN_SLOTS),
    "world.cairn": _i(cairn),
    "world.matar_shrine": _i(matar_shrine, slots={"pray": [{"t": [1, 2], "face": "-y"}]}),
    "world.cistern": _i(cistern, slots={"draw": [{"t": [0, 2], "face": "-y"}]}),
    "world.haystack": _i(haystack),
    "world.treading_vat": _i(treading_vat, slots={"work": [{"t": [2, 0], "face": "-x"}, {"t": [2, 1], "face": "-x"}]}),
    "world.boundary_stone": _i(boundary_stone),
    "world.quarry": _i(quarry, slots={"cut": [{"t": [1, 3], "face": "-y"}, {"t": [2, 3], "face": "-y"}]}),
    "world.log_stack": _i(log_stack, slots={"stack": [{"t": [1, 0], "face": "-x"}]}),
    "world.salt_pans": _i(salt_pans, slots={"rake": [{"t": [2, 1], "face": "-x"}]}),
    "world.tent_black": _i(tent_black, slots={"door": [{"t": [1, 2], "face": "-y"}]}),
}

FRAMES = {"world.pontoon": 2, "world.shaduf": 2}
