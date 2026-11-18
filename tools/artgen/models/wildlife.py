"""The rare visitors, modelled like the other critters: facing +x, anchored at the ground contact
point (flyers at the bottom of the body, the koi at its belly under the water line).

Each builder takes (anim, frame, frames, k); `anim` is the animation without its facing.
"""

import math

import numpy as np

from models.critters import S, _blob, _model, _pitched, _put_points
from rig import BEAST_DUTY, foot_cycle
from voxel import ellipsoid, segment


def _coords(m):
    return tuple(a / S for a in m.coords())


# Four-beat walk order of the legs as `_legs` lists them (fore left, fore right, hind left,
# hind right): left hind, left fore, right hind, right fore.
WALK_ORDER = (0.25, 0.75, 0.0, 0.5)


def _legs(m, X, Y, Z, hips, length, t, swing, r, material, stride=1.0, tone=-0.3, socks=None):
    """Four legs in a four-beat walk, each foot planted while it bears weight: hips are
    (x, y, z) per leg; `t` the walk phase in radians; a foot sweeps `swing * stride` units
    either side of its hip."""
    for n, (x, y, z) in enumerate(hips):
        a, up = foot_cycle(t / (2 * math.pi) - WALK_ORDER[n], BEAST_DUTY) if swing else (0.0, 0.0)
        foot = (x + a * swing * stride, y, up * swing * 0.5)
        knee = ((x + foot[0]) / 2 + 0.25 * (1 if x < 0 else -1), y, z - length * 0.5)
        m.put(segment(X, Y, Z, (x, y, z), knee, r), material, tone=tone)
        m.put(segment(X, Y, Z, knee, foot, r * 0.85), material, tone=tone)
        if socks:
            m.put(segment(X, Y, Z, (knee[0] * 0.6 + foot[0] * 0.4, y, knee[2] * 0.6), foot, r * 0.9),
                  socks, tone=-0.2)


def _hop(u: float, height: float) -> tuple[float, bool]:
    """One hop a cycle: a crouch on the ground, then a parabola through the air (the legs
    stretched while rising)."""
    if u < 0.25:
        return 0.0, False
    v = (u - 0.25) / 0.75
    return height * 4 * v * (1 - v), v < 0.5


HERON_REACH = 1.6
HEDGEHOG_REACH = 0.6
FOX_REACH = 1.2
DEER_REACH = 1.2


# ---- owl ----

def owl(anim, frame, frames, k):
    """A tawny owl: round face disc, low ear tufts, streaked brown, dark eyes."""
    flying = anim == "move"
    m = _model(k, -5, 6, -8 if flying else -4, 9 if flying else 5, 0, 12)
    m.hover = flying
    X, Y, Z = _coords(m)
    hoot = anim == "hoot"
    puff = (0.0, 0.5, 0.2)[frame % 3] if hoot else 0.0
    streak = (((Z * 1.7 + np.sin(Y * 3.0) * 0.3) % 1.0) < 0.3) * -0.7
    body = (0.0, 0, 3.6)
    _blob(m, X, Y, Z, body, (2.4, 2.5, 3.5 + puff * 0.3), "wood_light", tone=streak)
    m.put(ellipsoid(X, Y, Z, 1.3, 0, 3.3, 1.4, 1.9, 2.4 + puff), "straw", tone=-0.3 + streak * 0.6)
    if flying:
        up = 0.25 + 0.75 * math.cos(2 * math.pi * frame / frames)   # one wingbeat a cycle
        for side in (1, -1):
            tip = (-0.8, side * 7.0, 4.8 + up * 3.0)
            wing = segment(X, Y, Z, (0, side * 1.8, 4.6), tip, 1.4) | \
                segment(X, Y, Z, (-1.2, side * 1.8, 4.0), (tip[0] - 1.3, tip[1] * 0.8, tip[2] - 0.8), 1.1)
            bar = ((np.abs(Y) * 1.2) % 1.2) < 0.35
            m.put(wing, "wood", tone=0.5 - bar * 0.8)
    else:
        for side in (1, -1):   # folded wings with pale spots
            wing = ellipsoid(X, Y, Z, -0.9, side * 1.7, 3.6, 1.8, 0.9, 2.5)
            m.put(wing, "wood", tone=0.3 - (((Z * 1.3) % 1.0) < 0.3) * 0.7)
        # Toes gripping the perch.
        for side in (0.8, -0.8):
            _put_points(m, [(1.0, side, 0.2), (1.4, side, 0.2)], "yellow", tone=0.2)
    hx, hz = 0.5 + (0.4 if hoot and frame % 3 else 0.0), 8.0
    _blob(m, X, Y, Z, (hx, 0, hz), (2.4, 2.6, 2.2), "wood_light", tone=0.2)
    # The face turns towards the camera; a pale disc round dark eyes, a little hooked beak.
    c, s_ = math.cos(0.6), math.sin(0.6)
    U = (X - hx) * c + Y * s_
    W = -(X - hx) * s_ + Y * c

    def at(u, w, z):
        return (hx + u * c - w * s_, u * s_ + w * c, z)
    disc = (U > 1.0) & (np.hypot(W / 2.0, (Z - hz + 0.2) / 1.6) < 1.0) & \
        ellipsoid(X, Y, Z, hx, 0, hz, 2.6, 2.8, 2.4)
    m.put(disc, "straw", tone=1.0 - 0.9 * (np.hypot(W, Z - hz + 0.2) > 1.5))
    blink = anim == "idle" and frame % 2 == 1
    for ew in (0.85, -0.85):
        _put_points(m, [at(2.35, ew, hz)], "wood" if blink else "ink", tone=-0.4 if blink else 0.0)
        if not blink:
            _put_points(m, [at(2.45, ew + 0.3, hz + 0.3)], "cream", tone=1.5)
    beak_open = hoot and frame % 3 == 1
    _put_points(m, [at(2.6, 0, hz - 0.6), at(2.5, 0, hz - 0.95 - 0.4 * beak_open)], "yellow", tone=0.5)
    for side in (1, -1):   # ear tufts, set low and wide
        m.put(segment(X, Y, Z, at(0.1, side * 1.4, hz + 1.7), at(-0.2, side * 1.9, hz + 2.6), 0.5), "wood",
              tone=0.2)
    m.put(ellipsoid(X, Y, Z, -2.0, 0, 1.6, 1.0, 1.2, 1.4), "wood", tone=-0.2)   # tail
    return m


# ---- heron ----

def heron(anim, frame, frames, k):
    """A grey heron: long legs, folded S of a neck, black crest stripe, dagger bill."""
    m = _model(k, -7, 12, -4, 5, 0, 22)
    X, Y, Z = _coords(m)
    t = 2 * math.pi * frame / frames
    walking = anim == "move"
    for side, off in ((0.7, 0.0), (-0.7, 0.5)):
        a, up = foot_cycle(frame / frames + off) if walking else (0.0, 0.0)
        sw, lift = a * HERON_REACH, up * 1.2
        knee = (0.2 + sw * 0.6, side, 4.2 + lift)
        foot = (0.6 + sw, side, lift * 0.6)
        m.put(segment(X, Y, Z, (0.0, side * 0.8, 8.4), knee, 0.26), "yellow", tone=-1.3)
        m.put(segment(X, Y, Z, knee, foot, 0.24), "yellow", tone=-1.3)
        _put_points(m, [(foot[0] + 0.8, side, 0.1), (foot[0] - 0.5, side, 0.1)], "yellow", tone=-1.4)
    bob = 0.15 * (1 - math.cos(2 * t)) if walking else 0.0
    body = (-0.6, 0, 10.2 + bob)
    _blob(m, X, Y, Z, body, (3.2, 1.7, 1.8), "stone", tone=0.8)
    for side in (1, -1):   # folded wings: blue-grey with darker flight feathers behind
        wing = ellipsoid(X, Y, Z, -1.2, side * 1.3, 10.6 + bob, 3.0, 0.7, 1.5)
        m.put(wing, "stone", tone=0.2 - (X < -3.0) * 1.2)
    m.put(segment(X, Y, Z, (-3.6, 0, 10.0 + bob), (-5.6, 0, 9.0 + bob), 0.9), "stone", tone=-0.6)
    # Neck: folded back on itself, or struck forward and down when fishing.
    strike = (0.0, 0.6, 1.0, 0.4)[frame % 4] if anim == "fish" else 0.0
    base = (1.8, 0, 11.4 + bob)
    mid = (3.4 + strike * 1.6, 0, 13.4 - strike * 3.5 + bob)
    head = (2.4 + strike * 5.2, 0, 16.6 - strike * 11.8 + bob)
    m.put(segment(X, Y, Z, base, mid, 0.62), "cream", tone=0.6)
    m.put(segment(X, Y, Z, mid, head, 0.55), "cream", tone=0.6)
    if m.fine:   # the dark streaks down the front of the neck
        streaks = segment(X, Y, Z, base, mid, 0.9) & (X > np.asarray(base[0]) + 0.6) & (((Z * 2.0) % 1.0) < 0.35)
        m.put(streaks, "ink", tone=1.0)
    _blob(m, X, Y, Z, head, (1.2, 0.9, 1.0), "cream", tone=0.8)
    dz = -0.6 * strike
    m.put(segment(X, Y, Z, (head[0] + 0.8, 0, head[2] + dz * 0.2), (head[0] + 3.6, 0, head[2] - 0.4 + dz * 2), 0.3),
          "yellow", tone=0.3)
    # Black stripe over the eye running back into a trailing crest.
    m.put(segment(X, Y, Z, (head[0] + 0.6, 0, head[2] + 0.55), (head[0] - 2.2, 0, head[2] + 0.2), 0.32), "ink",
          tone=0.4)
    _put_points(m, [(head[0] + 0.7, 0.75, head[2] + 0.15)], "yellow", tone=1.0)
    if anim == "fish" and frame % 4 == 2:   # the splash where the bill goes in
        _put_points(m, [(head[0] + 3.0, d, 0.6 + abs(d)) for d in (-1.2, -0.6, 0.6, 1.2)], "water", tone=1.8)
    return m


# ---- hedgehog ----

def hedgehog(anim, frame, frames, k):
    """Brown-grey spines with pale tips, a pointed snout, tiny feet; curls into a ball."""
    m = _model(k, -5, 6, -4, 4, 0, 6)
    X, Y, Z = _coords(m)
    t = 2 * math.pi * frame / frames
    curl = anim == "curl"
    tips = ((np.floor(X * 2.6) + np.floor(Y * 2.6) * 3 + np.floor(Z * 2.6) * 7) % 4 == 0)
    if curl:
        squeeze = 0.15 * (frame % 2)
        shell = ellipsoid(X, Y, Z, 0, 0, 2.1, 2.6 - squeeze, 2.4, 2.2 + squeeze)
        m.put(shell, "wood", tone=-0.4 + tips * 1.4, normal=(X, Y, Z - 2.1))
        _put_points(m, [(2.4, 0.4, 1.0)], "ink")     # the nose peeping out
        return m
    scurry = anim == "move"
    bob = 0.1 * (1 - math.cos(2 * t)) if scurry else 0.0
    for n, (x0, side) in enumerate(((1.2, 1), (1.2, -1), (-1.2, 1), (-1.2, -1))):
        a, up = foot_cycle(frame / frames - WALK_ORDER[n], BEAST_DUTY) if scurry else (0.0, 0.0)
        m.put(segment(X, Y, Z, (x0, side * 1.0, 1.0), (x0 + a * HEDGEHOG_REACH, side * 1.1, 0.2 + up * 0.4), 0.35),
              "wood", tone=-0.8)
    shell = ellipsoid(X, Y, Z, -0.4, 0, 1.8 + bob, 2.9, 2.3, 1.9) & (Z > 0.7)
    m.put(shell, "wood", tone=-0.3 + tips * 1.5 - (X > 1.6) * 0.2,
          normal=((X + 0.4) / 2.9 ** 2, Y / 2.3 ** 2, (Z - 1.8) / 1.9 ** 2))
    sniff = 0.2 * (frame % 2) if anim == "idle" else 0.0
    _blob(m, X, Y, Z, (2.1, 0, 1.4 + bob), (1.3, 1.1, 0.9), "wood_light", tone=0.2)
    m.put(segment(X, Y, Z, (2.8, 0, 1.3 + bob), (3.9 + sniff, 0, 1.0 + bob), 0.45), "wood_light", tone=0.5)
    _put_points(m, [(4.1 + sniff, 0, 1.0 + bob)], "ink")
    _put_points(m, [(2.7, 0.75, 1.75 + bob)], "ink")
    return m


# ---- fox ----

def fox(anim, frame, frames, k):
    """A russet fox: white chest and tail tip, dark socks, a big brush."""
    m = _model(k, -9, 8, -5, 5, 0, 11)
    X, Y, Z = _coords(m)
    t = 2 * math.pi * frame / frames
    if anim == "sleep":
        breath = 0.2 * (frame % 2)
        _blob(m, X, Y, Z, (-0.3, 0, 1.8), (3.8, 3.0, 1.8 + breath), "ginger", tone=0.0)
        tail = [(-3.6, -1.2, 1.2), (-3.4, 2.4, 1.3), (0.2, 3.6, 1.3), (2.9, 2.6, 1.4)]
        for a, b in zip(tail, tail[1:]):
            m.put(segment(X, Y, Z, a, b, 1.15), "ginger", tone=0.3)
        _blob(m, X, Y, Z, (3.2, 2.5, 1.5), (1.0, 0.9, 0.9), "cream", tone=0.6)
        hx, hy, hz = 2.0, 1.0, 2.4
        _blob(m, X, Y, Z, (hx, hy, hz), (1.6, 1.4, 1.2), "ginger", tone=0.4)
        for side in (1, -1):
            m.put(segment(X, Y, Z, (hx - 0.6, hy + side * 0.8, hz + 0.8), (hx - 1.2, hy + side * 1.0, hz + 1.9), 0.45),
                  "ginger", tone=0.1)
        _put_points(m, [(hx + 1.1, hy + 0.7, hz + 0.2), (hx + 1.1, hy + 0.3, hz + 0.2)], "ink", tone=1.0)
        _put_points(m, [(hx + 2.0, hy, hz - 0.3)], "ink")
        return m
    walking = anim == "move"
    hips = [(2.4, 1.0, 4.0), (2.4, -1.0, 4.0), (-2.4, 1.0, 4.0), (-2.4, -1.0, 4.0)]
    _legs(m, X, Y, Z, hips, 4.0, t, FOX_REACH if walking else 0.0, 0.5, "ginger", socks="ink")
    bob = 0.15 * (1 - math.cos(2 * t)) if walking else 0.0
    _blob(m, X, Y, Z, (0, 0, 4.6 + bob), (3.8, 1.6, 1.7), "ginger", tone=0.0)
    m.put(ellipsoid(X, Y, Z, 2.4, 0, 4.4 + bob, 1.4, 1.3, 1.5) & (Z < 4.6 + bob), "cream", tone=0.6)
    sway = 0.5 * math.sin(t) if walking else 0.4 * (frame % 2)
    tail = [(-3.4, 0, 5.0 + bob), (-5.8, sway, 4.4), (-7.6, sway * 1.5, 3.4)]
    for a, b in zip(tail, tail[1:]):
        m.put(segment(X, Y, Z, a, b, 1.25), "ginger", tone=0.3)
    _blob(m, X, Y, Z, tail[-1], (1.0, 0.9, 0.9), "cream", tone=0.6)
    hx, hz = 4.0, 6.6 + bob
    _blob(m, X, Y, Z, (hx, 0, hz), (1.6, 1.4, 1.3), "ginger", tone=0.4)
    m.put(segment(X, Y, Z, (hx + 0.8, 0, hz - 0.3), (hx + 2.6, 0, hz - 0.6), 0.55), "ginger", tone=0.3)
    m.put(ellipsoid(X, Y, Z, hx + 1.4, 0, hz - 0.7, 1.3, 0.8, 0.45), "cream", tone=0.6)
    _put_points(m, [(hx + 2.8, 0, hz - 0.6)], "ink")
    for side in (1, -1):
        m.put(segment(X, Y, Z, (hx - 0.4, side * 0.8, hz + 0.9), (hx - 0.6, side * 1.0, hz + 2.5), 0.5), "ginger",
              tone=0.0)
        _put_points(m, [(hx - 0.55, side * 1.0, hz + 2.4)], "ink")
    _put_points(m, [(hx + 1.2, 0.75, hz + 0.3)], "ink")
    return m


# ---- frog ----

def frog(anim, frame, frames, k):
    """A small green frog with a gold eye; it moves by hopping and croaks with a pale throat."""
    m = _model(k, -3, 4, -3, 3, 0, 6)
    X, Y, Z = _coords(m)
    hop, stretch = _hop(frame / frames, 2.2) if anim == "move" else (0.0, False)
    m.hover = hop > 0
    sac = 0.5 * (frame % 2) if anim == "croak" else 0.0
    pitch = -0.4 if stretch else 0.0
    Xb, Yb, Zb = _pitched(X, Y, Z, pitch, 0.0, 1.0 + hop)
    _blob(m, Xb, Yb, Zb, (0, 0, 1.0 + hop), (1.9, 1.4, 0.95), "grass", tone=0.0)
    m.put(ellipsoid(Xb, Yb, Zb, 0.2, 0, 1.4 + hop, 1.6, 0.6, 0.5), "grass", tone=0.9)
    for side in (1, -1):
        leg = (-2.6, side * 1.0, hop) if stretch else (-0.6, side * 1.6, 0.3)
        m.put(segment(X, Y, Z, (-0.8, side * 1.0, 0.8 + hop), leg, 0.45), "grass", tone=-0.5)
        m.put(segment(X, Y, Z, (0.9, side * 0.8, 0.6 + hop), (1.3, side * 1.2, hop * 0.6), 0.3), "grass", tone=-0.4)
        _put_points(m, [(0.9, side * 0.75, 1.75 + hop)], "yellow", tone=0.8)
        _put_points(m, [(1.05, side * 0.75, 1.75 + hop)], "ink")
    if sac:
        _blob(m, X, Y, Z, (1.4, 0, 0.5 + sac * 0.4), (0.6 + sac, 0.8 + sac, 0.5 + sac * 0.6), "cream", tone=0.6)
    return m


# ---- koi ----

def koi(anim, frame, frames, k):
    """An orange and white carp seen from above at a slant; drawn under the water."""
    m = _model(k, -6, 6, -3, 3, 0, 3)
    m.hover = True
    X, Y, Z = _coords(m)
    t = 2 * math.pi * frame / frames
    amp = 0.6 if anim == "move" else 0.25
    bend = lambda x: amp * math.sin(t) * np.clip(-x / 4.0, 0, 1.5) ** 1.5
    Yb = Y - bend(X)
    body = ellipsoid(X, Yb, Z, 0.6, 0, 1.0, 4.0, 1.4, 0.9)
    patch = ((np.sin(X * 1.3 + 1.0) + np.cos(Yb * 2.0 + X * 0.6)) > 0.6)
    m.put(body & patch, "cream", tone=0.6, normal=(X * 0.1, Yb, Z - 0.6))
    m.put(body & ~patch, "orange", tone=0.4, normal=(X * 0.1, Yb, Z - 0.6))
    tail = (np.abs(Yb) < 0.3 + (-X - 3.2) * 0.9) & (X < -3.2) & (X > -5.4) & (np.abs(Z - 1.0) < 0.4)
    m.put(tail, "orange", tone=0.8)
    for side in (1, -1):
        fin = ellipsoid(X, Yb, Z, 1.6, side * 1.5, 0.8, 0.7, 0.6, 0.25)
        m.put(fin, "orange", tone=1.0)
        _put_points(m, [(3.6, side * 0.55, 1.4)], "ink")
    return m


# ---- robin ----

def robin(anim, frame, frames, k):
    """A round little robin with an orange-red breast; it moves in hops."""
    m = _model(k, -3, 4, -2, 3, 0, 6)
    X, Y, Z = _coords(m)
    hop = _hop(frame / frames, 1.4)[0] if anim == "move" else 0.0
    m.hover = hop > 0
    tilt = 0.25 * (frame % 2) if anim == "idle" else 0.0
    for side in (0.5, -0.5):
        m.put(segment(X, Y, Z, (0.1, side, 1.2 + hop), (0.2, side, hop), 0.2), "wood", tone=-0.4)
    _blob(m, X, Y, Z, (0, 0, 2.2 + hop), (1.8, 1.4, 1.5), "wood_light", tone=-0.3)
    m.put(ellipsoid(X, Y, Z, 0.9, 0, 2.3 + hop, 1.1, 1.2, 1.2), "orange", tone=0.6)
    m.put(segment(X, Y, Z, (-1.4, 0, 2.6 + hop), (-2.6, 0, 3.4 + hop), 0.45), "wood", tone=0.0)
    hx, hz = 1.0 + tilt, 3.7 + hop
    _blob(m, X, Y, Z, (hx, 0, hz), (1.0, 0.95, 0.95), "wood_light", tone=-0.1)
    m.put(ellipsoid(X, Y, Z, hx + 0.5, 0, hz - 0.3, 0.6, 0.85, 0.6), "orange", tone=0.6)
    _put_points(m, [(hx + 1.1, 0, hz)], "ink", tone=0.6)
    _put_points(m, [(hx + 0.6, 0.6, hz + 0.2)], "ink")
    return m


# ---- deer ----

def deer(anim, frame, frames, k):
    """A slender roe deer, warm brown with a white rump; walks slowly and grazes."""
    m = _model(k, -8, 9, -4, 4, 0, 19)
    X, Y, Z = _coords(m)
    t = 2 * math.pi * frame / frames
    walking = anim == "move"
    hips = [(2.6, 0.8, 7.6), (2.6, -0.8, 7.6), (-2.6, 0.8, 7.6), (-2.6, -0.8, 7.6)]
    _legs(m, X, Y, Z, hips, 7.6, t, DEER_REACH / 1.2 if walking else 0.0, 0.42, "wood_light", stride=1.2)
    bob = 0.125 * (1 - math.cos(2 * t)) if walking else 0.0
    _blob(m, X, Y, Z, (0, 0, 8.6 + bob), (4.0, 1.7, 1.9), "wood_light", tone=0.2)
    m.put(ellipsoid(X, Y, Z, -3.4, 0, 8.8 + bob, 1.0, 1.5, 1.4) & (X < -2.9), "cream", tone=0.8)  # rump
    m.put(ellipsoid(X, Y, Z, 0.2, 0, 7.4 + bob, 3.0, 1.4, 0.8) & (Z < 7.4 + bob), "cream", tone=-0.2)
    graze = (0.3, 1.0, 0.9)[frame % 3] if anim == "graze" else 0.0
    neck0 = (3.0, 0, 9.4 + bob)
    head = (5.0 + graze * 0.6, 0, 13.6 - graze * 11.6 + bob)
    m.put(segment(X, Y, Z, neck0, head, 0.85), "wood_light", tone=0.3)
    _blob(m, X, Y, Z, head, (1.2, 0.9, 0.95), "wood_light", tone=0.4)
    snout = (head[0] + 1.5, 0, head[2] - 0.5 - graze * 0.5)
    m.put(segment(X, Y, Z, head, snout, 0.55), "wood_light", tone=0.5)
    _put_points(m, [(snout[0] + 0.3, 0, snout[2])], "ink")
    _put_points(m, [(head[0] + 0.5, 0.75, head[2] + 0.3)], "ink")
    flick = 0.5 * (frame % 2) if anim == "idle" else 0.0
    for side in (1, -1):
        m.put(segment(X, Y, Z, (head[0] - 0.4, side * 0.6, head[2] + 0.7),
                      (head[0] - 1.0 - flick * (side > 0), side * 1.5, head[2] + 1.7), 0.45), "wood_light", tone=0.0)
    if anim == "graze" and frame % 3:   # a nibble of grass at the muzzle
        _put_points(m, [(snout[0] + 0.4, 0.3, 0.6), (snout[0] + 0.2, -0.3, 0.9)], "grass", tone=0.6)
    return m


MODELS = {"owl": owl, "heron": heron, "hedgehog": hedgehog, "fox": fox, "frog": frog, "koi": koi,
          "robin": robin, "deer": deer}
