"""Visitors, modelled around the origin facing +x; the anchor is the ground contact point.

`front` sprites face +x (down-right); `back` sprites face -y (up-right), i.e. the model turned
three quarter-turns clockwise. The engine mirrors these for the other two directions.
"""

import math

import numpy as np

from pack import Sprite
from render import render_base
from voxel import Model, cylinder, ellipsoid, ellipsoid_normal, segment


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


def butterfly(anim, frame, frames):
    m = _model(-5, 5, -7, 7, 0, 11)
    X, Y, Z = (a / S for a in m.coords())
    m.hover = True
    flap = (0.15, 0.9, 1.35, 0.9)[frame % 4] if anim == "move" else (0.25, 0.6)[frame % 2]
    m.put(segment(X, Y, Z, (-1.5, 0, 3), (1.5, 0, 3.2), 0.55), "ink")
    for side in (-1, 1):
        # Wing plane hinged at the body, raised by `flap` radians.
        ny, nz = -math.sin(flap) * side, math.cos(flap)
        across = (Y * math.cos(flap) * side + (Z - 3) * math.sin(flap))
        plane = np.abs(Y * ny + (Z - 3) * nz) < 0.6
        ell = lambda cx, cy, rx, ry: ((X - cx) / rx) ** 2 + ((across - cy) / ry) ** 2
        upper = (ell(0.9, 2.9, 2.6, 2.9) <= 1) & (across > 0.3)
        lower = (ell(-1.4, 1.9, 1.7, 1.9) <= 1) & (across > 0.3)
        wing = plane & (upper | lower)
        edge = wing & (ell(0.9, 2.9, 2.6, 2.9) > 0.6) & (ell(-1.4, 1.9, 1.7, 1.9) > 0.5)
        lit = (X * 0 - 0.4, X * 0 + 0.3, X * 0 + 1.0)   # thin membranes: shade as if facing the sky
        m.put(wing & upper, "orange", tone=0.8, normal=lit)
        m.put(wing & lower & ~upper, "yellow", tone=0.4, normal=lit)
        m.put(edge, "ink", tone=0.5, normal=lit)
    return m


def bee(anim, frame, frames):
    m = _model(-4, 4, -4, 4, 0, 8)
    X, Y, Z = (a / S for a in m.coords())
    m.hover = True
    bob = (0, 0.5, 0, -0.5)[frame % 4] if anim == "move" else 0.0
    body = ellipsoid(X, Y, Z, 0, 0, 3 + bob, 2.2, 1.5, 1.5)
    stripe = (np.floor(X + 10) % 2) == 1
    m.put(body & ~stripe, "yellow", normal=ellipsoid_normal(X, Y, Z, 0, 0, 3 + bob, 2.2, 1.5, 1.5))
    m.put(body & stripe, "ink", normal=ellipsoid_normal(X, Y, Z, 0, 0, 3 + bob, 2.2, 1.5, 1.5))
    m.put(ellipsoid(X, Y, Z, 2.2, 0, 3.2 + bob, 0.9, 1.0, 1.0), "ink")
    up = frame % 2 == 0
    for side in (-1, 1):
        m.put(ellipsoid(X, Y, Z, -0.3, side * 1.6, 5.0 + bob if up else 4.2 + bob, 1.2, 1.0,
                        0.5 if up else 0.4), "cream", tone=1.0)
    return m


def firefly(anim, frame, frames):
    m = _model(-3, 3, -3, 3, 0, 6)
    X, Y, Z = (a / S for a in m.coords())
    m.hover = True
    bright = (1.5, 0.8, 0.0, 0.8)[frame % 4] if anim == "move" else (1.5, 0.5)[frame % 2]
    m.put(ellipsoid(X, Y, Z, 0.6, 0, 2.6, 1.1, 0.8, 0.8), "ink")
    m.put(ellipsoid(X, Y, Z, -0.9, 0, 2.3, 1.2, 1.0, 1.0), "lamp", tone=bright - 1.0)
    m.put(ellipsoid(X, Y, Z, 0.2, 0, 3.6, 1.0, 1.4, 0.4), "cream", tone=0.5)
    return m


MODELS = {"duck": duck, "hen": hen, "cat": cat, "butterfly": butterfly, "bee": bee, "firefly": firefly}


def sprite(cid: str, anim: str, frame: int, frames: int) -> Sprite:
    kind, facing = anim.split("_")
    model = MODELS[cid](kind, frame, frames)
    if facing == "back":
        model = model.rotated(3, 0, 0)
    rgba, _glow, ox, oy = render_base(model)
    return Sprite(rgba, ox, oy)
