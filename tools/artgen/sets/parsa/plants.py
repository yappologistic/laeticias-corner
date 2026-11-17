"""Pārsa's plants (persepolis.md §3.4): the garden trees of a Persian paradise in spring and the
crops and flowers of the plain. Canopies use the home set's leaf clusters (models/nature.py)
so trees of both sets sit together in one world."""

import math

import numpy as np

from arch import ellipsoid, rod
from models.nature import leaf_mass, trunk
from setbuild import Item
from palette import MAT
from voxel import Model, Rng, value_noise


def _tree_model(k, top, r=10):
    return Model.empty(-r, 16 + r, -r, 16 + r, 0, top, k=k)


def t_cypress(v, frame, frames, k):
    """A narrow dark green column, the schematic conifer of the reliefs."""
    rng = Rng(500, v)
    h = 50.0 + 4.0 * v
    m = _tree_model(k, int(h) + 4, 6)
    trunk(m, 8, 8, 1.0, 6.0)
    clumps = []
    for i in range(9):
        t = i / 8
        z = 6.0 + t * (h - 10.0)
        r = 3.6 * (1 - t) ** 0.6 + 1.0
        clumps.append((8 + rng.uniform(-0.4, 0.4), 8 + rng.uniform(-0.4, 0.4), z, r))
    leaf_mass(m, clumps, 501 + v, materials=(("leaf_dark", 1.0),), under="leaf_dark", cluster=(1.8, 2.6),
              squash=1.3, level=-1.2)
    return m


def t_plane(v, frame, frames, k):
    """An oriental plane: a broad rounded crown on a pale mottled trunk."""
    rng = Rng(510, v)
    m = _tree_model(k, 64, 14)
    trunk(m, 8, 8, 1.9, 30.0, material="wood_grey", flare=1.8)
    for a in (0.6, 2.6, 4.4):
        rod(m, (8, 8, 22.0), (8 + 7 * math.cos(a), 8 + 7 * math.sin(a), 36.0), 1.0, "wood_grey")
    clumps = [(8 + 8 * math.cos(a) * rng.uniform(0.6, 1.0), 8 + 8 * math.sin(a) * rng.uniform(0.6, 1.0),
               40 + rng.uniform(-4, 6), rng.uniform(7.0, 9.0)) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    clumps.append((8, 8, 50.0, 9.0))
    leaf_mass(m, clumps, 511 + v, materials=(("leaf", 0.7), ("grass", 0.3)), under="leaf_dark", level=-0.6)
    # The plane's mottled bark: pale patches where the old bark has flaked away.
    X, Y, Z = m.coords()
    bark = (m.mat == MAT["wood_grey"]) & (value_noise(X, Y, Z * 0.6, 1.2, 513 + v) > 0.72)
    m.put(bark, "cream", tone=0.2)
    return m


def t_poplar(v, frame, frames, k):
    """A tall white poplar along a channel, its silvery leaves catching the light."""
    rng = Rng(520, v)
    h = 50.0 + 4 * v
    m = _tree_model(k, int(h) + 4, 7)
    trunk(m, 8, 8, 1.1, h * 0.5, material="wood_grey")
    clumps = [(8 + rng.uniform(-1, 1), 8 + rng.uniform(-1, 1), 14 + t * (h - 20), 4.6 * (1 - abs(t - 0.4)) + 1.6)
              for t in np.linspace(0, 1, 8)]
    leaf_mass(m, clumps, 521 + v, materials=(("leaf", 0.5), ("snow", 0.2), ("grass", 0.3)), under="leaf_dark",
              cluster=(2.0, 3.0), squash=1.2, level=-0.4)
    return m


def t_willow(v, frame, frames, k):
    """A willow by the river: a short trunk, a drooping crown of hanging strands."""
    rng = Rng(530, v)
    m = _tree_model(k, 44, 14)
    trunk(m, 8, 8, 1.6, 18.0, lean=(0.6, -0.4))
    clumps = [(8 + 7 * math.cos(a), 8 + 7 * math.sin(a), 28 + rng.uniform(-2, 3), 6.0)
              for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)] + [(8, 8, 34, 7.0)]
    leaf_mass(m, clumps, 531 + v, materials=(("grass", 0.6), ("leaf", 0.4)), under="leaf", level=-0.4)
    for i in range(26):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(6, 13)
        x, y = 8 + r * math.cos(a), 8 + r * math.sin(a)
        rod(m, (x, y, 30 - r * 0.5), (x * 1.02, y * 1.02, 30 - r * 0.5 - rng.uniform(8, 16)), 0.35, "grass", tone=0.3)
    return m


def _flowering(v, k, seed, flower, h=28.0, spread=7.0, flower_share=0.35, fruit=None):
    rng = Rng(seed, v)
    m = _tree_model(k, int(h) + 4, 10)
    trunk(m, 8, 8, 1.1, h * 0.4, lean=(rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)))
    clumps = [(8 + spread * 0.7 * math.cos(a), 8 + spread * 0.7 * math.sin(a), h * 0.62 + rng.uniform(-2, 2),
               rng.uniform(4.0, 5.2)) for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)]
    clumps.append((8, 8, h * 0.8, 5.5))
    mats = (("leaf", 1 - flower_share), (flower, flower_share)) if flower else (("leaf", 1.0),)
    leaf_mass(m, clumps, seed + 1 + v, materials=mats, under="leaf_dark", level=-0.4)
    if fruit:
        for i in range(10):
            cx, cy, cz, r = clumps[i % len(clumps)]
            a = rng.uniform(0, 2 * math.pi)
            p = (cx + r * 0.95 * math.cos(a), cy + r * 0.95 * math.sin(a), cz + rng.uniform(-r * 0.4, r * 0.5))
            ellipsoid(m, p, (0.7, 0.7, 0.7), fruit, tone=0.4)
    return m


def t_pomegranate(v, frame, frames, k):
    """A small pomegranate tree in spring, red-orange flowers among glossy leaves."""
    return _flowering(v, k, 540, None, h=27.0, spread=6.0, fruit="poppy")


def t_almond(v, frame, frames, k):
    """An almond in full white-pink blossom, the signal of spring."""
    return _flowering(v, k, 550, "blossom", h=30.0, spread=7.5, flower_share=0.85)


def t_fig(v, frame, frames, k):
    return _flowering(v, k, 560, None, h=30.0, spread=8.0)


def t_vine(v, frame, frames, k):
    """A grapevine trained on a trellis of poles (wine was a great ration item)."""
    m = Model.empty(-2, 18, -2, 18, 0, 26, k=k)
    for x, y in ((2, 2), (2, 14), (14, 2), (14, 14)):
        rod(m, (x, y, 0), (x, y, 20.0), 0.45, "wood")
    for y in (2.0, 14.0):
        rod(m, (2, y, 20.0), (14, y, 20.0), 0.35, "wood_light")
    rod(m, (8, 8, 0), (8, 8, 18.0), 0.7, "bark")
    leaf_mass(m, [(4, 8, 20, 4.0), (12, 8, 20, 4.0), (8, 4, 21, 4.0), (8, 12, 20, 4.0)], 571 + v,
              materials=(("grass", 0.6), ("leaf", 0.4)), under="leaf", squash=0.55, level=-0.3)
    return m


def t_date(v, frame, frames, k):
    """A date palm (few, in the garden: they grow in the warm south of Fārs)."""
    rng = Rng(580, v)
    h = 46.0 + 3 * v
    m = _tree_model(k, int(h) + 10, 14)
    pts = [(8 + 1.6 * t * t, 8 + 0.8 * t * t, t * h) for t in np.linspace(0, 1, 12)]
    for (a, b) in zip(pts, pts[1:]):
        rod(m, a, b, 1.3, "bark", tone=0.2 * ((a[2] % 3.0) < 1.5))
    top = pts[-1]
    for i in range(12):
        az = i * 2 * math.pi / 12 + rng.uniform(-0.2, 0.2)
        L = rng.uniform(9, 12)
        mid = (top[0] + L * 0.5 * math.cos(az), top[1] + L * 0.5 * math.sin(az), top[2] + 2.5)
        end = (top[0] + L * math.cos(az), top[1] + L * math.sin(az), top[2] - 3.5)
        rod(m, top, mid, 0.7, "leaf", tone=0.3)
        rod(m, mid, end, 0.55, "leaf", tone=0.0)
    for i in range(3):
        ellipsoid(m, (top[0] + math.cos(i * 2.1) * 1.4, top[1] + math.sin(i * 2.1) * 1.4, top[2] - 2.0),
                  (0.9, 0.9, 1.4), "orange", tone=0.1)
    return m


def _patch(v, k, seed, n, h, stem, head, spread=6.5, head_r=0.5):
    rng = Rng(seed, v)
    m = Model.empty(0, 16, 0, 16, 0, int(h) + 4, k=k)
    for i in range(n):
        x, y = 8 + rng.uniform(-spread, spread), 8 + rng.uniform(-spread, spread)
        hh = h * rng.uniform(0.7, 1.0)
        lean = (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6))
        rod(m, (x, y, 0), (x + lean[0], y + lean[1], hh), 0.18, stem, tone=rng.uniform(-0.2, 0.3))
        if head:
            mat = head(rng) if callable(head) else head
            ellipsoid(m, (x + lean[0], y + lean[1], hh + 0.4), (head_r, head_r, head_r * 1.4), mat, tone=0.3)
    return m


def p_barley(v, frame, frames, k):
    """Young spring barley, bright green, the staple of the ration system."""
    return _patch(v, k, 600, 70, 4.0, "grass", None, spread=7.5)


def p_wheat(v, frame, frames, k):
    return _patch(v, k, 610, 60, 5.0, "grass", "green_paint", spread=7.5, head_r=0.35)


def p_lilies(v, frame, frames, k):
    """Lilies and wild tulips of the Zagros spring."""
    return _patch(v, k, 620, 12, 5.0, "leaf", lambda r: r.choice(("poppy", "white_paint", "yellow", "poppy")),
                  spread=6.0, head_r=0.7)


def p_rose(v, frame, frames, k):
    m = Model.empty(-2, 18, -2, 18, 0, 10, k=k)
    leaf_mass(m, [(8, 8, 4.0, 4.0), (6, 10, 3.5, 3.0)], 631, materials=(("leaf_dark", 0.7), ("blossom", 0.3)),
              under="leaf_dark", level=-0.6)
    return m


def p_steppe(v, frame, frames, k):
    """Grey-green tufts of wormwood and steppe grass on rough ground."""
    return _patch(v, k, 640 + v, 30, 3.0, "wood_grey", None, spread=6.5)


ITEMS = {f"parsa.{n}": Item(fn) for n, fn in (
    ("t_cypress", t_cypress), ("t_plane", t_plane), ("t_poplar", t_poplar), ("t_willow", t_willow),
    ("t_pomegranate", t_pomegranate), ("t_almond", t_almond), ("t_vine", t_vine), ("t_date", t_date),
    ("t_fig", t_fig), ("p_barley", p_barley), ("p_wheat", p_wheat), ("p_lilies", p_lilies),
    ("p_rose", p_rose), ("p_steppe", p_steppe))}
