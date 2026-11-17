"""Visitors, modelled around the origin facing +x; the anchor is the ground contact point.

`front` sprites face +x (down-right); `back` sprites face -y (up-right), i.e. the model turned
three quarter-turns clockwise. The engine mirrors these for the other two directions.
"""

import math

import numpy as np

from pack import Sprite
from palette import GLOW, INK, PLASTER, ROOF, STONE, STRAW, WATER, _rgb
from render import render_base
from voxel import Model, ellipsoid, ellipsoid_normal, segment


S = 1.35  # critters are modelled at life-ish size and enlarged so they read at 1x


def _model(x0, x1, y0, y1, z0, z1) -> Model:
    return Model.empty(*(int(math.floor(v * S)) if v < 0 else int(math.ceil(v * S))
                         for v in (x0, x1, y0, y1, z0, z1)))


def _put_points(m, pts, material, **kw):
    m.put_points(np.asarray(pts, np.float32) * S, material, **kw)


def _blob(m, X, Y, Z, c, r, material, tone=0.0):
    m.put(ellipsoid(X, Y, Z, *c, *r), material, tone=tone, normal=ellipsoid_normal(X, Y, Z, *c, *r))


def duck(anim, frame, frames):
    m = _model(-6, 7, -4, 5, 0, 10)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    bob = 0.5 * math.sin(2 * math.pi * frame / frames) if moving else 0.0
    dip = (not moving) and frame % 2 == 1
    _blob(m, X, Y, Z, (0, 0, 2.6 + bob), (3.6, 2.4, 2.2), "cream")
    m.put(segment(X, Y, Z, (-2.5, 0, 3.5 + bob), (-4.3, 0, 5.0 + bob), 1.0), "cream", tone=-0.4)
    wing = ellipsoid(X, Y, Z, -0.6, 0, 3.4 + bob, 2.6, 2.5, 1.4) & (np.abs(Y) > 1.6)
    m.put(wing, "cream", tone=-0.8)
    hz = (4.6 if dip else 6.2) + bob
    hx = 3.4 if dip else 2.6
    m.put(segment(X, Y, Z, (1.8, 0, 3.5 + bob), (hx, 0, hz), 1.0), "cream")
    _blob(m, X, Y, Z, (hx, 0, hz), (1.6, 1.4, 1.5), "cream", tone=0.3)
    m.put(ellipsoid(X, Y, Z, hx + 1.9, 0, hz - 0.4, 1.0, 0.7, 0.45), "orange", tone=0.8)
    _put_points(m, [(hx + 0.6, 1.2, hz + 0.3)], "ink")
    m.carve(Z < 0.6)  # sits in the water
    return m


def hen(anim, frame, frames):
    m = _model(-5, 6, -4, 5, 0, 11)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    step = math.sin(2 * math.pi * frame / frames) if moving else 0.0
    peck = (not moving) and frame % 2 == 1
    bob = abs(step) * 0.5
    for side, phase in ((-0.9, 1), (0.9, -1)):
        lift = max(0.0, step * phase) * 1.2
        m.put(segment(X, Y, Z, (0.2, side, 3), (0.2 + step * phase * 0.8, side, lift), 0.5), "orange")
    _blob(m, X, Y, Z, (0, 0, 4.4 + bob), (3.0, 2.2, 2.4), "ginger")
    m.put(ellipsoid(X, Y, Z, -2.6, 0, 6.2 + bob, 1.4, 1.2, 1.9), "ginger", tone=-0.5)
    m.put(ellipsoid(X, Y, Z, -0.4, 0, 4.8 + bob, 2.0, 2.4, 1.3) & (np.abs(Y) > 1.5), "ginger", tone=-0.8)
    hx, hz = (3.6, 3.6 + bob) if peck else (2.4, 7.0 + bob)
    _blob(m, X, Y, Z, (hx, 0, hz), (1.4, 1.2, 1.4), "ginger", tone=0.4)
    m.put(ellipsoid(X, Y, Z, hx - 0.2, 0, hz + 1.5, 0.9, 0.4, 0.7), "poppy", tone=0.5)
    m.put(ellipsoid(X, Y, Z, hx + 1.3, 0, hz - 0.8, 0.4, 0.4, 0.6), "poppy", tone=0.2)
    m.put(ellipsoid(X, Y, Z, hx + 1.6, 0, hz, 0.8, 0.5, 0.4), "yellow", tone=0.6)
    _put_points(m, [(hx + 0.4, 1.1, hz + 0.3)], "ink")
    return m


def cat(anim, frame, frames):
    m = _model(-7, 8, -4, 5, 0, 12)
    X, Y, Z = (a / S for a in m.coords())
    moving = anim == "move"
    t = 2 * math.pi * frame / frames
    stripes = ((np.floor(X * 0.9) % 2) == 0) * -0.6
    if moving:
        for x0, side, ph in ((2.6, 1, 0), (2.6, -1, math.pi), (-2.4, 1, math.pi), (-2.4, -1, 0)):
            sw = math.sin(t + ph)
            m.put(segment(X, Y, Z, (x0, side * 0.9, 3.5), (x0 + sw * 1.2, side * 0.9, 0.3), 0.6),
                  "ginger", tone=-0.3)
        _blob(m, X, Y, Z, (0, 0, 4.0), (4.0, 1.7, 1.7), "ginger", tone=stripes)
        head = (4.3, 0, 5.6)
        tail = [(-3.6, 0, 4.4), (-5.6, 0, 6.5 + 0.6 * math.sin(t)), (-6.0, 0, 8.6)]
    else:
        # Sitting: haunches down, chest up, tail curled around and flicking.
        m.put(segment(X, Y, Z, (1.6, 0.8, 3.5), (1.9, 0.8, 0.3), 0.6), "ginger", tone=-0.2)
        m.put(segment(X, Y, Z, (1.6, -0.8, 3.5), (1.9, -0.8, 0.3), 0.6), "ginger", tone=-0.2)
        _blob(m, X, Y, Z, (-0.8, 0, 2.6), (2.6, 2.0, 2.2), "ginger", tone=stripes)
        _blob(m, X, Y, Z, (0.6, 0, 4.8), (1.7, 1.6, 2.4), "ginger", tone=stripes)
        head = (1.3, 0, 7.6)
        flick = 1.0 if frame % 2 else 0.0
        tail = [(-3.0, 0, 1.0), (-1.5, 2.2, 0.6), (1.0 + flick, 2.4, 0.8 + flick)]
    for a, b in zip(tail, tail[1:]):
        m.put(segment(X, Y, Z, a, b, 0.65), "ginger", tone=-0.2)
    hx, hy, hz = head
    _blob(m, X, Y, Z, head, (1.9, 1.8, 1.6), "ginger", tone=0.3)
    for side in (-1, 1):
        m.put(segment(X, Y, Z, (hx - 0.3, side * 1.0, hz + 1.0), (hx - 0.4, side * 1.1, hz + 2.4), 0.55),
              "ginger", tone=0.2)
    _put_points(m, [(hx + 1.0, 1.2, hz + 0.3), (hx + 1.6, 0.4, hz + 0.3)], "ink")
    _put_points(m, [(hx + 1.9, 0, hz - 0.5)], "blossom", tone=1)
    return m


# ---- tiny flyers: hand-drawn at pixel scale, where voxels would only make blobs ----
# Rows top to bottom; the anchor is the bottom-middle of the body (the engine adds altitude).
# Fluttering flyers read best facing the viewer, so `back` frames reuse the same drawings.

FLYER_INKS = {"K": (INK, 255), "O": (GLOW[0], 255), "R": (ROOF[2], 255), "Y": (STRAW[2], 255),
              "y": (STRAW[3], 255), "W": (PLASTER[4], 255), "w": (WATER[5], 200),
              "g": (STONE[2], 255), "1": (GLOW[2], 255), "2": (GLOW[1], 150), "3": (GLOW[0], 60)}

BUTTERFLY = {
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
BUTTERFLY_FRAMES = {"move": ("open", "half", "shut", "half"), "idle": ("open", "half")}

BEE = {
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

FIREFLY = {
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


def _stencil(rows) -> Sprite:
    h, w = len(rows), len(rows[0])
    rgba = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                color, alpha = FLYER_INKS[ch]
                rgba[y, x, :3] = _rgb(color)
                rgba[y, x, 3] = alpha
    return Sprite(rgba, w // 2, h - 1)


def butterfly(anim, frame, frames):
    return _stencil(BUTTERFLY[BUTTERFLY_FRAMES[anim][frame % len(BUTTERFLY_FRAMES[anim])]])


def bee(anim, frame, frames):
    return _stencil(BEE["up" if frame % 2 == 0 else "down"])


def firefly(anim, frame, frames):
    """Emissive at night, so the glow is part of the sprite: a white-hot core in a warm halo
    that pulses with the frames."""
    pulse = (2, 1, 0, 1) if anim == "move" else (2, 1)
    return _stencil(FIREFLY[pulse[frame % len(pulse)]])


MODELS = {"duck": duck, "hen": hen, "cat": cat}
FLYERS = {"butterfly": butterfly, "bee": bee, "firefly": firefly}


def sprite(cid: str, anim: str, frame: int, frames: int) -> Sprite:
    kind, facing = anim.split("_")
    if cid in FLYERS:
        return FLYERS[cid](kind, frame, frames)
    model = MODELS[cid](kind, frame, frames)
    if facing == "back":
        model = model.rotated(3, 0, 0)
    rgba, _glow, ox, oy = render_base(model)
    return Sprite(rgba, ox, oy)
