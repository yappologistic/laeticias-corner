"""Visitors, modelled around the origin facing +x; the anchor is the ground contact point.

`front` sprites face +x (down-right); `back` sprites face -y (up-right), i.e. the model turned
three quarter-turns clockwise. The engine mirrors these for the other two directions.
"""

import math

import numpy as np

from pack import Sprite
from palette import GLOW, INK, PLASTER, ROOF, STONE, STRAW, WATER, _rgb
from render import render_sprite
from palette import MAT
from rig import BEAST_DUTY, foot_cycle
from voxel import Model, ellipsoid, ellipsoid_normal, segment


S = 1.35  # critters are modelled at life-ish size and enlarged so they read at 1x
# Walks with planted feet (rig.foot_cycle): a foot sweeps `reach` model units either side.
HEN_REACH = 0.9
CAT_REACH = 1.2
DUCK_REACH = 0.9


def _model(k, x0, x1, y0, y1, z0, z1) -> Model:
    return Model.empty(*(int(math.floor(v * S)) if v < 0 else int(math.ceil(v * S))
                         for v in (x0, x1, y0, y1, z0, z1)), k=k)


def _put_points(m, pts, material, **kw):
    m.put_points(np.asarray(pts, np.float32) * S, material, **kw)


def _blob(m, X, Y, Z, c, r, material, tone=0.0):
    m.put(ellipsoid(X, Y, Z, *c, *r), material, tone=tone, normal=ellipsoid_normal(X, Y, Z, *c, *r))


def _pitched(X, Y, Z, angle, cx, cz):
    """Coordinates of a body tipped nose-down by `angle` about the point (cx, ., cz)."""
    if not angle:
        return X, Y, Z
    c, s = math.cos(angle), math.sin(angle)
    dx, dz = X - cx, Z - cz
    return cx + dx * c - dz * s, Y, cz + dx * s + dz * c


def _splash(m, frame, seed, radius=3.5):
    """Droplets thrown up round a critter on the water."""
    rng = np.random.Generator(np.random.PCG64([seed, frame]))
    pts = []
    for _n in range(12):
        a = rng.uniform(0, 2 * math.pi)
        d = radius * rng.uniform(0.8, 1.3)
        pts.append((d * math.cos(a), d * math.sin(a) * 0.8, rng.uniform(0.6, 3.0) * (1 + frame % 2)))
    _put_points(m, pts, "water", tone=1.8)


def duck(anim, frame, frames, k):
    """A white duck on the water; `waddle` and `sleep` happen on land (legs, no waterline)."""
    flap = anim == "flap"
    m = _model(k, -6, 7, -8 if flap else -4, 9 if flap else 5, 0, 13 if flap else 10)
    X, Y, Z = (a / S for a in m.coords())
    t = 2 * math.pi * frame / frames
    moving = anim == "move"
    on_land = anim in ("waddle", "sleep")
    bob = 0.5 * math.sin(t) if moving else 0.0
    dip = anim == "idle" and frame % 2 == 1
    lift = 0.0
    if anim == "waddle":
        lift = 1.3 + 0.15 * (1 - math.cos(2 * t))
        for side, off in ((1.0, 0.0), (-1.0, 0.5)):
            a, up = foot_cycle(frame / frames + off)
            foot = (0.4 + a * DUCK_REACH, side * 1.0, up * 0.5)
            m.put(segment(X, Y, Z, (0.2, side * 0.9, 1.6 + lift), foot, 0.4), "orange", tone=0.2)
            m.put(ellipsoid(X, Y, Z, foot[0] + 0.6, foot[1], foot[2] + 0.2, 0.9, 0.6, 0.25), "orange", tone=0.5)
    elif anim == "flap":
        lift = 0.6 + 0.4 * frame
    pitch = (0.45, 1.05, 0.5)[frame % 3] if anim == "dabble" else 0.0
    roll = 0.3 * math.sin(t) if anim == "waddle" else 0.0
    base = 2.6 + bob + lift
    Xb, Yb, Zb = _pitched(X, Y - roll, Z, pitch, 0.0, base)
    _blob(m, Xb, Yb, Zb, (0, 0, base), (3.6, 2.4, 2.2), "cream")
    m.put(segment(Xb, Yb, Zb, (-2.5, 0, base + 0.9), (-4.3, 0, base + 2.4), 1.0), "cream", tone=-0.4)
    if flap:
        # Wings beating: long pale feathered blades raised and lowered round the shoulders.
        up = (1.0, 0.1, -0.6)[frame % 3]
        for side in (1, -1):
            tip = (-1.6, side * 6.2, base + 1.2 + up * 3.0)
            wing = segment(X, Y, Z, (-0.3, side * 1.6, base + 1.0), tip, 1.1) | \
                segment(X, Y, Z, (-1.5, side * 1.6, base + 0.8), (tip[0] - 1.2, tip[1] * 0.85, tip[2] - 0.5), 0.9)
            feather = ((np.abs(Y) * 1.3) % 1.0) < 0.3
            m.put(wing, "cream", tone=0.2 - feather * 0.7 - (np.abs(Y) > 4.5) * 0.4)
        _splash(m, frame, 31)
    else:
        wing = ellipsoid(Xb, Yb, Zb, -0.6, 0, base + 0.8, 2.6, 2.5, 1.4) & (np.abs(Yb) > 1.6)
        if m.fine:  # overlapping flight feathers: a darker line along each, tips towards the tail
            feather = ((Xb - (Zb - bob - lift) * 0.6) % 0.9) < 0.3
            m.put(wing, "cream", tone=-0.5 - feather * 0.8 - (Xb < -2.2) * 0.5)
            m.put(segment(Xb, Yb, Zb, (-3.6, 0, base + 1.8), (-4.9, 0, base + 3.3), 0.55), "cream", tone=-0.6)
        else:
            m.put(wing, "cream", tone=-0.8)
    if anim == "sleep":
        # Head turned back and tucked under the wing: only the crown and a glimpse of bill.
        _blob(m, X, Y, Z, (-0.8, 0.9, base + 1.9), (1.6, 1.4, 1.3), "cream", tone=0.3)
        m.put(ellipsoid(X, Y, Z, -1.9, 1.6, base + 1.4, 0.8, 0.5, 0.35), "orange", tone=0.3)
        _put_points(m, [(-0.2, 2.2, base + 2.0), (0.2, 2.2, base + 2.0)], "ink", tone=1.0)  # shut eye
    elif anim != "dabble" or pitch < 0.8:
        hz = (4.6 if dip else 6.2) + bob + lift
        hx = 3.4 if dip else 2.6
        if anim == "dabble":
            hx, hz = 3.6, base - 0.4
        if anim == "flap":
            hz += 0.6
        m.put(segment(X, Y, Z, (1.8, 0, base + 0.9), (hx, 0, hz), 1.0), "cream")
        _blob(m, X, Y, Z, (hx, 0, hz), (1.6, 1.4, 1.5), "cream", tone=0.3)
        m.put(ellipsoid(X, Y, Z, hx + 1.9, 0, hz - 0.4, 1.0, 0.7, 0.45), "orange", tone=0.8)
        _put_points(m, [(hx + 0.6, 1.2, hz + 0.3)], "ink")
        if m.fine:  # a nostril, a pale lower mandible and a glint in the eye
            _put_points(m, [(hx + 2.1, 0.45, hz - 0.2)], "ember")
            m.put(ellipsoid(X, Y, Z, hx + 1.7, 0, hz - 0.75, 0.8, 0.55, 0.2), "orange", tone=-0.3)
            _put_points(m, [(hx + 0.75, 1.25, hz + 0.6)], "cream", tone=2)
    if not on_land:
        m.carve(Z < 0.6)  # sits in the water
        if anim == "dabble":
            m.put((np.hypot(X - 2.8, Y * 1.2) < 2.2) & (np.hypot(X - 2.8, Y * 1.2) > 1.4) & (Z < 1.1) & (Z >= 0.6),
                  "water", tone=1.5)   # a ring where the head went under
    return m


def hen(anim, frame, frames, k):
    flap = anim == "flap"
    m = _model(k, -5, 6, -7 if flap else -4, 8 if flap else 5, 0, 14 if flap else 11)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    t = frame / frames
    hop = (0.0, 1.6, 0.4)[frame % 3] if flap else 0.0
    bob = (0.25 * (1 - math.cos(4 * math.pi * t)) if moving else 0.0) + hop
    for side, off in ((-0.9, 0.5), (0.9, 0.0)):
        a, up = foot_cycle(t + off) if moving else (0.0, 0.0)
        m.put(segment(X, Y, Z, (0.2, side, 3 + hop + bob - hop), (0.2 + a * HEN_REACH, side, up * 1.2 + hop), 0.5),
              "orange")
    # A brown hen with a pale breast and a dark tail, so she never reads as a small ginger cat.
    _blob(m, X, Y, Z, (0, 0, 4.4 + bob), (3.0, 2.2, 2.4), "wood_light", tone=-0.2)
    m.put(ellipsoid(X, Y, Z, 1.6, 0, 4.2 + bob, 1.5, 1.8, 1.6), "straw", tone=0.6)
    tail = ellipsoid(X, Y, Z, -2.6, 0, 6.2 + bob, 1.4, 1.2, 1.9)
    if flap:
        # Wings out and up, primaries spread.
        up = (0.8, 1.2, -0.2)[frame % 3]
        for side in (1, -1):
            tip = (-1.4, side * 5.4, 6.0 + bob + up * 2.0)
            wing = segment(X, Y, Z, (0.0, side * 1.8, 5.0 + bob), tip, 1.2)
            m.put(wing, "wood", tone=0.4 - (((np.abs(Y) * 1.4) % 1.0) < 0.3) * 0.8)
    if m.fine:
        # Tail feathers fanned in strips, scalloped feathers over the wing.
        m.put(tail, "wood", tone=0.2 - (((Z - bob) % 0.8) < 0.3) * 0.9 + (X < -3.3) * 0.5)
        if not flap:
            wing = ellipsoid(X, Y, Z, -0.4, 0, 4.8 + bob, 2.0, 2.4, 1.3) & (np.abs(Y) > 1.5)
            scallop = (((X * 1.4 + np.sin(Z * 4.0) * 0.3) % 1.0) < 0.3)
            m.put(wing, "wood", tone=0.6 - scallop * 0.9)
        body = (m.mat == MAT["wood_light"]) & (np.abs(Y) > 1.2)
        m.tone[body] -= np.broadcast_to(((X * 1.6 + Z * 0.8) % 1.0) < 0.25, body.shape)[body] * 0.7
    else:
        m.put(tail, "wood", tone=0.2)
        if not flap:
            m.put(ellipsoid(X, Y, Z, -0.4, 0, 4.8 + bob, 2.0, 2.4, 1.3) & (np.abs(Y) > 1.5), "wood", tone=0.6)
    if anim == "peck":
        hx, hz = ((2.6, 6.6), (3.5, 4.4), (3.9, 1.7))[frame % 3]
    elif anim == "idle" and frame % 2 == 1:
        hx, hz = 3.6, 3.6
    else:
        hx, hz = 2.4, 7.0 + (0.4 if flap else 0.0)
    hz += bob
    if anim == "peck" and frame % 3 == 2:
        hz -= bob
    m.put(segment(X, Y, Z, (1.7, 0, 5.2 + bob), (hx, 0, hz), 1.0), "wood_light", tone=0.1)
    _blob(m, X, Y, Z, (hx, 0, hz), (1.4, 1.2, 1.4), "wood_light", tone=0.2)
    m.put(ellipsoid(X, Y, Z, hx - 0.1, 0, hz + 1.5, 1.2, 0.55, 0.9), "poppy", tone=1.0)
    m.put(ellipsoid(X, Y, Z, hx + 1.2, 0, hz - 0.9, 0.5, 0.5, 0.7), "poppy", tone=0.8)
    m.put(ellipsoid(X, Y, Z, hx + 1.6, 0, hz, 0.8, 0.5, 0.4), "yellow", tone=0.6)
    _put_points(m, [(hx + 0.4, 1.1, hz + 0.3)], "ink")
    if anim == "peck" and frame % 3 == 2:   # a few scratched-up specks of earth
        _put_points(m, [(5.0, 0.8, 0.2), (5.4, -0.6, 0.2), (4.6, 1.5, 0.2)], "soil", tone=1.0)
    return m


def _cat_head(m, X, Y, Z, head, stripes, eyes_shut=False, tilt=0.0):
    hx, hy, hz = head
    _blob(m, X, Y, Z, head, (1.9, 1.8, 1.6), "ginger", tone=0.3)
    for side in (-1, 1):
        lean = tilt * side
        m.put(segment(X, Y, Z, (hx - 0.3, hy + side * 1.0, hz + 1.0 + lean * 0.3),
                      (hx - 0.4, hy + side * 1.1, hz + 2.4 + lean * 0.5), 0.55), "ginger", tone=0.2)
        if m.fine:  # pink inside the ear
            _put_points(m, [(hx + 0.05, hy + side * 1.0, hz + 1.6), (hx + 0.05, hy + side * 1.0, hz + 1.9)],
                        "blossom", tone=0.6)
    if m.fine:
        # A cream muzzle and bib, green eyes with dark pupils (or shut: a dark line).
        m.put(ellipsoid(X, Y, Z, hx + 1.3, hy, hz - 0.6, 0.8, 1.0, 0.7), "cream", tone=0.3)
        for ey in (1.2, 0.4):
            if eyes_shut:
                _put_points(m, [(hx + 1.0, hy + ey - 0.2, hz + 0.15), (hx + 1.0, hy + ey + 0.2, hz + 0.15)], "ink",
                            tone=1.0)
            else:
                _put_points(m, [(hx + 1.0, hy + ey, hz + 0.3)], "leaf", tone=2.0)
                _put_points(m, [(hx + 1.0, hy + ey, hz + 0.1)], "ink")
    else:
        _put_points(m, [(hx + 1.0, hy + 1.2, hz + 0.3), (hx + 1.6, hy + 0.4, hz + 0.3)], "ink")
    _put_points(m, [(hx + 1.9, hy, hz - 0.5)], "blossom", tone=1)


def _cat_tail(m, X, Y, Z, tail, tip_dark=True):
    for a, b in zip(tail, tail[1:]):
        m.put(segment(X, Y, Z, a, b, 0.65), "ginger", tone=-0.2)
    if m.fine and tip_dark:
        m.put(segment(X, Y, Z, tail[-2], tail[-1], 0.7) & (np.hypot(*(np.broadcast_arrays(
            X - tail[-1][0], Z - tail[-1][2]))) < 1.0), "ginger", tone=-1.2)


def cat(anim, frame, frames, k):
    m = _model(k, -7, 9, -4, 6, 0, 12)
    X, Y, Z = (a / S for a in m.coords())
    t = 2 * math.pi * frame / frames
    # Tabby stripes; on fine grids narrower, bent with the body and a pixel or two wide.
    if m.fine:
        stripes = (((X * 1.5 + np.abs(Y) * 0.6 + Z * 0.3) % 1.6) < 0.45) * -0.9
    else:
        stripes = ((np.floor(X * 0.9) % 2) == 0) * -0.6
    shut = False
    tilt = 0.0
    if anim == "sleep":
        # Curled in a ring, nose on the paws, the tail wrapped round over the nose.
        breath = 0.2 * (frame % 2)
        _blob(m, X, Y, Z, (-0.4, 0, 2.0), (3.6, 3.0, 2.0 + breath), "ginger", tone=stripes)
        head = (2.0, 1.4, 2.3)
        shut = True
        tail = [(-3.4, -1.0, 1.0), (-2.8, 2.4, 1.0), (0.4, 3.4, 1.0), (2.8, 2.8, 1.2)]
    elif anim == "stretch" and frame % 4 < 2:
        # Front legs out along the ground, chest down, rump and tail up; deeper on frame 1.
        deep = 0.6 * (frame % 4)
        for side in (1, -1):
            m.put(segment(X, Y, Z, (2.4, side * 0.9, 2.2 - deep * 0.5), (5.2 + deep, side * 0.9, 0.4), 0.6),
                  "ginger", tone=-0.3)
            m.put(segment(X, Y, Z, (-2.4, side * 0.9, 4.0), (-2.6, side * 0.9, 0.3), 0.6), "ginger", tone=-0.3)
        m.put(segment(X, Y, Z, (-2.0, 0, 4.4), (2.0, 0, 2.6 - deep), 1.7), "ginger", tone=stripes)
        head = (4.0 + deep * 0.5, 0, 3.2 - deep)
        tail = [(-3.2, 0, 5.0), (-4.4, 0, 7.6), (-4.2, 0.3, 10.0)]
        shut = frame % 4 == 1
    elif anim in ("move", "stretch"):
        u = frame / frames if anim == "move" else None
        for x0, side, off in ((2.6, 1, 0.25), (2.6, -1, 0.75), (-2.4, 1, 0.0), (-2.4, -1, 0.5)):
            a, up = foot_cycle(u - off, BEAST_DUTY) if u is not None else (0.0, 0.0)
            m.put(segment(X, Y, Z, (x0, side * 0.9, 3.5), (x0 + a * CAT_REACH, side * 0.9, 0.3 + up * 0.9), 0.6),
                  "ginger", tone=-0.3)
        _blob(m, X, Y, Z, (0, 0, 4.0), (4.0, 1.7, 1.7), "ginger", tone=stripes)
        head = (4.3, 0, 5.6)
        tail = [(-3.6, 0, 4.4), (-5.6, 0, 6.5 + 0.6 * math.sin(t) * (anim == "move")), (-6.0, 0, 8.6)]
        if anim == "stretch":   # then a good shake: head tilted, tail fluffed
            tilt = 0.8 if frame % 4 == 3 else 0.0
            head = (4.3, 0.3 * (frame % 4 == 3), 5.9)
            shut = frame % 4 == 3
    else:
        # Sitting (idle, sit, groom): haunches down, chest up, tail curled around and flicking.
        paw_up = None
        if anim == "groom":
            paw_up = ((2.7, 0.9, 6.4), (2.6, 0.9, 6.0), (1.9, 1.5, 8.6), (2.2, 1.3, 8.2))[frame % 4]
        legs = [(0.8, (1.9, 0.8, 0.3)), (-0.8, (1.9, -0.8, 0.3))]
        for side, foot in legs:
            if paw_up is not None and side > 0:
                foot = paw_up
            m.put(segment(X, Y, Z, (1.6, side, 3.5), foot, 0.6), "ginger", tone=-0.2)
        _blob(m, X, Y, Z, (-0.8, 0, 2.6), (2.6, 2.0, 2.2), "ginger", tone=stripes)
        _blob(m, X, Y, Z, (0.6, 0, 4.8), (1.7, 1.6, 2.4), "ginger", tone=stripes)
        head = (1.3, 0, 7.6)
        if anim == "groom":
            head = ((1.7, 0.5, 7.0), (1.8, 0.5, 6.7), (1.2, 0.6, 7.6), (1.3, 0.7, 7.4))[frame % 4]
            tilt = (0.0, 0.0, 0.6, 0.8)[frame % 4]
            shut = True
        flick = 1.0 if frame % 2 else 0.0
        if anim == "sit":
            flick = (0.0, 1.4)[frame % 2]
        tail = [(-3.0, 0, 1.0), (-1.5, 2.2, 0.6), (1.0 + flick, 2.4, 0.8 + flick)]
    _cat_tail(m, X, Y, Z, tail)
    _cat_head(m, X, Y, Z, head, stripes, shut, tilt)
    return m


# ---- tiny flyers: hand-drawn at pixel scale, where voxels would only make blobs ----
# Rows top to bottom; the anchor is the bottom-middle of the drawing (the engine adds altitude).
# Each set of drawings is made for one pixel density (pixels per design unit); a build uses the
# densest set that divides its own and enlarges it by the remaining whole factor. On the
# coarse set `back` reuses the `front` drawings; the fine set shows the upper side of the wings
# from behind and the paler underside, head first, from the front.

FLYER_INKS = {"K": (INK, 255), "O": (GLOW[0], 255), "o": (ROOF[3], 255), "R": (ROOF[2], 255),
              "Y": (STRAW[2], 255), "y": (STRAW[3], 255), "W": (PLASTER[4], 255),
              "w": (WATER[5], 200), "g": (STONE[2], 255), "1": (GLOW[2], 255), "2": (GLOW[1], 150),
              "3": (GLOW[0], 60)}

_BUTTERFLY_1 = {
    "open": ("K.K...K.K",
             ".K.....K.",
             "KOOK.KOOK",
             "KWROKORWK",
             ".KOOKOOK.",
             ".KYYKYYK.",
             "..KYKYK..",
             "...K.K..."),
    "half": ("..K...K..",
             "...K.K...",
             "..KOKOK..",
             ".KWOKOWK.",
             ".KROKORK.",
             "..KYKYK..",
             "..KYKYK..",
             "...K.K..."),
    "shut": ("...K.K...",
             "....K....",
             "...KOK...",
             "...KOK...",
             "...KRK...",
             "...KYK...",
             "...KYK...",
             "....K...."),
}
_BEE_1 = {
    "up":   ("...wW...",
             "..wWw...",
             ".KYYKYKK",
             "KYyKYyKK",
             ".KKKKKK."),
    "down": ("........",
             "........",
             ".KYYKYKK",
             "KYyKYyKK",
             "wwKKKKw."),
}
_FIREFLY_1 = {
    2: (".33333.",
        "3322233",
        "3221223",
        "3212123",
        "3221223",
        "3322233",
        ".3KgK3."),
    1: (".......",
        "..333..",
        ".32223.",
        ".32123.",
        ".32223.",
        "..333..",
        "..KgK.."),
    0: (".......",
        ".......",
        ".......",
        "...3...",
        "..323..",
        "...3...",
        "..KgK.."),
}

_BUTTERFLY_2_BACK = {
    "open": (".....K...K.....",
             "......K.K......",
             ".KKK...K...KKK.",
             "KWKOK.KKK.KOKWK",
             "KKOOOKKKKKOOOKK",
             "KOOoOOKKKOOoOOK",
             ".KOOOOKKKOOOOK.",
             "..KKRRKKKRRKK..",
             ".KRRoOKKKOoRRK.",
             ".KRoOK.K.KOoRK.",
             "..KKK..K..KKK..",
             "..............."),
    "half": (".....K...K.....",
             "......K.K......",
             "....K..K..K....",
             "...KWK.K.KWK...",
             "...KOOKKKOOK...",
             "...KOoKKKoOK...",
             "....KOKKKOK....",
             "....KRKKKRK....",
             "....KRKKKRK....",
             ".....KK.KK.....",
             ".......K.......",
             "..............."),
    "shut": (".....K...K.....",
             "......K.K......",
             ".......K.......",
             "......KWK......",
             "......KOK......",
             "......KoK......",
             "......KOK......",
             "......KRK......",
             "......KRK......",
             ".......K.......",
             "...............",
             "..............."),
}
_BUTTERFLY_2_FRONT = {
    "open": ("...............",
             ".KKK.......KKK.",
             "KyyyK.....KyyyK",
             "KyKyyK...KyyKyK",
             "KyyyOOK.KOOyyyK",
             ".KyyOOKKKOOyyK.",
             "..KKKKKKKKKKK..",
             ".KYYOKKKKKOYYK.",
             ".KYOOK.K.KOOYK.",
             "..KKK.KKK.KKK..",
             "......K.K......",
             ".....K...K....."),
    "half": ("...............",
             "....K.....K....",
             "...KyK...KyK...",
             "...KyyK.KyyK...",
             "...KyOKKKOyK...",
             "....KOKKKOK....",
             "....KYKKKYK....",
             "....KYKKKYK....",
             ".....KKKKK.....",
             "......KKK......",
             "......K.K......",
             ".....K...K....."),
    "shut": ("...............",
             "...............",
             "...............",
             "......KyK......",
             "......KyK......",
             "......KOK......",
             "......KOK......",
             "......KYK......",
             "......KKK......",
             ".......K.......",
             "......K.K......",
             ".....K...K....."),
}
_BEE_2_FRONT = {
    "up":   ("....ww.ww....",
             "...wWw.wWw...",
             "....ww.ww....",
             "..KKYYKKYK...",
             ".KYyKYyKYyKK.",
             "KYyyKYyKYyKgK",
             ".KYYKYYKYKKK.",
             "..KKKKKKKK...",
             "...K..K..K..."),
    "down": (".............",
             ".............",
             ".............",
             "..KKYYKKYK...",
             ".KYyKYyKYyKK.",
             "KYyyKYyKYyKgK",
             ".KYYKYYKYKKK.",
             "wwKKKKKKKKww.",
             ".wwK..K..Kw.."),
}
_BEE_2_BACK = {
    "up":   (".ww.......ww.",
             "wWww.....wwWw",
             ".www.KKK.www.",
             "....KYYYK....",
             "...KKKKKKK...",
             "...KYyYyYK...",
             "...KKKKKKK...",
             "....KYyYK....",
             ".....KKK....."),
    "down": (".............",
             ".............",
             ".....KKK.....",
             "....KYYYK....",
             "...KKKKKKK...",
             "wwwKYyYyYKwww",
             ".wwKKKKKKKww.",
             "....KYyYK....",
             ".....KKK....."),
}
_GLOW_2 = {
    2: ("...33333...",
        "..3333333..",
        ".333222333.",
        ".332212233.",
        ".332111233.",
        ".332212233.",
        ".333222333.",
        "..3333333..",
        "...33333..."),
    1: ("...........",
        "....333....",
        "...33333...",
        "..3322233..",
        "..3321233..",
        "..3322233..",
        "...33333...",
        "....333....",
        "..........."),
    0: ("...........",
        "...........",
        "...........",
        "....333....",
        "....323....",
        "....333....",
        "...........",
        "...........",
        "..........."),
}
# The fine firefly: its glowing tail over a small dark body, head first or wings first.
_FIREFLY_2 = {face: {n: rows + body for n, rows in _GLOW_2.items()}
              for face, body in (("front", ("....KKgK...", ".....K.K...")),
                                 ("back", ("...gKKKg...", "....K.K....")))}

# density -> flyer -> facing -> pose -> rows
FLYER_ART = {
    1: {"butterfly": {"front": _BUTTERFLY_1, "back": _BUTTERFLY_1},
        "bee": {"front": _BEE_1, "back": _BEE_1},
        "firefly": {"front": _FIREFLY_1, "back": _FIREFLY_1}},
    2: {"butterfly": {"front": _BUTTERFLY_2_FRONT, "back": _BUTTERFLY_2_BACK},
        "bee": {"front": _BEE_2_FRONT, "back": _BEE_2_BACK},
        "firefly": _FIREFLY_2},
}
BUTTERFLY_FRAMES = {"move": ("open", "half", "shut", "half"), "idle": ("open", "half"),
                    "rest": ("open", "half", "shut")}


def _stencil(rows, scale) -> Sprite:
    h, w = len(rows), len(rows[0])
    rgba = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                color, alpha = FLYER_INKS[ch]
                rgba[y, x, :3] = _rgb(color)
                rgba[y, x, 3] = alpha
    rgba = rgba.repeat(scale, 0).repeat(scale, 1)
    return Sprite(rgba, w // 2 * scale, h * scale - 1)


def _flyer_pose(cid, kind, frame):
    if cid == "butterfly":
        poses = BUTTERFLY_FRAMES[kind]
        return poses[frame % len(poses)]
    if cid == "bee":
        return "up" if frame % 2 == 0 else "down"
    # Fireflies are emissive at night, so the glow is part of the sprite: a white-hot core in
    # a warm halo that pulses with the frames.
    pulse = (2, 1, 0, 1) if kind == "move" else (2, 1)
    return pulse[frame % len(pulse)]


def flyer(cid, kind, facing, frame, k) -> Sprite:
    density = max(d for d in FLYER_ART if k % d == 0)
    rows = FLYER_ART[density][cid][facing][_flyer_pose(cid, kind, frame)]
    return _stencil(rows, k // density)


MODELS = {"duck": duck, "hen": hen, "cat": cat}


def render_model(model, facing: str) -> Sprite:
    if facing == "back":
        model = model.rotated(3, 0, 0)
    return render_sprite(model)


def split_anim(anim: str) -> tuple[str, str]:
    """`move_front` -> (move, front); plain animations are drawn facing front."""
    kind, _, facing = anim.rpartition("_")
    if facing not in ("front", "back"):
        return anim, "front"
    return kind, facing
