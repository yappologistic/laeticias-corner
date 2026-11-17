"""Athens's plants (athens.md §3.4) in high summer: olives silvering, planes and poplars by the
water, cypresses at sanctuaries and graves, Aleppo pines on the hills, figs and vines in courts,
oleander and agnus castus along the streams, myrtle and laurel, thyme scrub, barley stubble,
acanthus, reeds and dry asphodel. Canopies use the home set's leaf clusters (models/nature.py),
so trees of every set sit together in one world."""

import math

import numpy as np

from arch import ellipsoid, rod
from models.nature import leaf_mass
from setbuild import Item
from sets.athens.common import cypress, olive_tree
from voxel import Model, Rng, value_noise


def _tree(k, top, r=10):
    return Model.empty(-r, 16 + r, -r, 16 + r, 0, top, k=k)


def t_olive(v, frame, frames, k):
    """Athena's tree: a short twisted trunk, a broad silver-green crown (three looks)."""
    m = _tree(k, 36, 12)
    olive_tree(m, 8.0, 8.0, 0.0, h=24.0 + 3 * v, seed=v, spread=1.0 + 0.15 * v, gnarled=1.0 + 0.3 * v)
    return m


def t_plane(v, frame, frames, k):
    """An oriental plane (Kimon planted them in the Agora): a pale mottled trunk and a broad crown."""
    rng = Rng(1010, v)
    m = _tree(k, 60, 15)
    rod(m, (8, 8, 0.0), (8 + rng.uniform(-1, 1), 8 + rng.uniform(-1, 1), 26.0), 2.0, "wood_grey", tone=0.1)
    for a in (0.6, 2.6, 4.4):
        rod(m, (8, 8, 20.0), (8 + 7 * math.cos(a), 8 + 7 * math.sin(a), 32.0), 1.0, "wood_grey")
    clumps = [(8 + 8.5 * math.cos(a) * rng.uniform(0.6, 1.0), 8 + 8.5 * math.sin(a) * rng.uniform(0.6, 1.0),
               38 + rng.uniform(-3, 4), rng.uniform(6.5, 8.5)) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    clumps.append((8, 8, 46.0, 8.5))
    leaf_mass(m, clumps, 1011 + v, materials=(("leaf", 0.7), ("grass", 0.3)), under="leaf_dark", level=-0.6)
    X, Y, Z = m.coords()
    from palette import MAT
    bark = (m.mat == MAT["wood_grey"]) & (value_noise(X, Y, Z * 0.6, 1.2, 1013 + v) > 0.7)
    m.put(bark, "cream", tone=0.2)
    return m


def t_cypress(v, frame, frames, k):
    m = _tree(k, 56, 6)
    cypress(m, 8.0, 8.0, 0.0, h=44.0 + 4 * v, seed=v)
    return m


def t_pine(v, frame, frames, k):
    """An Aleppo pine on the hills: a leaning grey trunk and flat, airy dark-green clouds of needles."""
    rng = Rng(1030, v)
    m = _tree(k, 52, 14)
    lean = (rng.uniform(-3, 3), rng.uniform(-3, 3))
    rod(m, (8, 8, 0.0), (8 + lean[0], 8 + lean[1], 30.0), 1.3, "bark", tone=0.0)
    clumps = []
    for i in range(5):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(2.0, 7.0)
        z = rng.uniform(26.0, 40.0)
        x, y = 8 + lean[0] + r * math.cos(a), 8 + lean[1] + r * math.sin(a)
        rod(m, (8 + lean[0] * 0.8, 8 + lean[1] * 0.8, 24.0), (x, y, z - 1.0), 0.6, "bark")
        clumps.append((x, y, z, rng.uniform(4.5, 6.0)))
    leaf_mass(m, clumps, 1031 + v, materials=(("leaf_dark", 0.7), ("olive", 0.3)), under="leaf_dark",
              cluster=(2.4, 3.2), squash=0.55, level=-0.8)
    return m


def t_fig(v, frame, frames, k):
    """A fig in a courtyard: a low spreading grey trunk, big dark lobed leaves."""
    from sets.athens.kit import _fig
    m = _tree(k, 26, 10)
    _fig(m, 8.0, 8.0, 0.0, 18.0, v)
    return m


def t_vine(v, frame, frames, k):
    """A vine: v0 a low bush in a vineyard row, v1 a pergola over a court with grapes ripening."""
    m = _tree(k, 26, 2)
    rng = Rng(1050, v)
    if v == 0:
        rod(m, (8, 8, 0), (8, 8, 6.0), 0.8, "bark")
        leaf_mass(m, [(8 + rng.uniform(-2, 2), 8 + rng.uniform(-2, 2), 8.0, 4.0) for _ in range(3)], 1051,
                  materials=(("leaf", 0.6), ("grass", 0.4)), under="leaf_dark", cluster=(1.8, 2.4), level=-0.4)
    else:
        for x, y in ((1.0, 1.0), (1.0, 15.0), (15.0, 1.0), (15.0, 15.0)):
            rod(m, (x, y, 0.0), (x, y, 20.0), 0.5, "wood")
        for t in (1.0, 8.0, 15.0):
            rod(m, (t, 1.0, 20.0), (t, 15.0, 20.0), 0.4, "wood")
        rod(m, (1.0, 1.0, 0.0), (1.0, 1.0, 20.0), 0.9, "bark")
        leaf_mass(m, [(4.0 + 4 * i, 4.0 + 4 * j, 20.5, 3.2) for i in range(3) for j in range(3)], 1052,
                  materials=(("leaf", 0.7), ("grass", 0.3)), under="leaf_dark", cluster=(1.8, 2.4), squash=0.5,
                  level=-0.3)
    for i in range(5):
        ellipsoid(m, (rng.uniform(4, 12), rng.uniform(4, 12), (6.0 if v == 0 else 18.0) - rng.uniform(0, 1.5)),
                  (0.8, 0.8, 1.1), "purple", tone=0.2)
    return m


def _bush(m, x, y, h, r, seed, materials, flowers=None, n=4):
    rng = Rng(1060, seed)
    clumps = [(x + rng.uniform(-r * 0.5, r * 0.5), y + rng.uniform(-r * 0.5, r * 0.5), h * rng.uniform(0.45, 0.7),
               r * rng.uniform(0.5, 0.7)) for _ in range(n)]
    for cx, cy, cz, _r in clumps:
        rod(m, (x, y, 0.0), (cx, cy, cz), 0.4, "bark")
    leaf_mass(m, clumps, 1061 + seed, materials=materials, under="leaf_dark", cluster=(1.6, 2.2), level=-0.5)
    if flowers:
        for i in range(10):
            ellipsoid(m, (x + rng.uniform(-r, r) * 0.8, y + rng.uniform(-r, r) * 0.8, h * rng.uniform(0.55, 0.9)),
                      (0.7, 0.7, 0.6), flowers, tone=0.3)


def t_poplar(v, frame, frames, k):
    rng = Rng(1070, v)
    m = _tree(k, 56, 7)
    rod(m, (8, 8, 0), (8, 8, 26.0), 1.1, "wood_grey")
    clumps = [(8 + rng.uniform(-1, 1), 8 + rng.uniform(-1, 1), 14 + t * 34, 4.6 * (1 - abs(t - 0.4)) + 1.6)
              for t in np.linspace(0, 1, 8)]
    leaf_mass(m, clumps, 1071 + v, materials=(("leaf", 0.5), ("olive_silver", 0.3), ("grass", 0.2)), under="leaf_dark",
              cluster=(2.0, 3.0), squash=1.2, level=-0.4)
    return m


def t_agnus(v, frame, frames, k):
    m = _tree(k, 22, 6)
    _bush(m, 8.0, 8.0, 17.0, 6.0, 2 + v, (("olive", 0.6), ("leaf", 0.4)), flowers="violet", n=5)
    return m


def t_oleander(v, frame, frames, k):
    m = _tree(k, 20, 6)
    _bush(m, 8.0, 8.0, 15.0, 6.0, 4 + v, (("leaf_dark", 0.6), ("leaf", 0.4)), flowers="blossom" if v == 0 else "cream")
    return m


def t_myrtle(v, frame, frames, k):
    m = _tree(k, 16, 5)
    _bush(m, 8.0, 8.0, 12.0, 5.0, 6 + v, (("leaf_dark", 0.5), ("leaf", 0.5)), flowers="cream", n=3)
    return m


def t_laurel(v, frame, frames, k):
    """A laurel (bay), dense and dark, Apollo's tree."""
    m = _tree(k, 28, 7)
    _bush(m, 8.0, 8.0, 24.0, 6.5, 8 + v, (("leaf_dark", 0.7), ("leaf", 0.3)), n=5)
    return m


def _ground_cover(m, seed, n, draw):
    rng = Rng(1080, seed)
    for i in range(n):
        draw(rng, rng.uniform(1.5, 14.5), rng.uniform(1.5, 14.5), i)


def p_thyme(v, frame, frames, k):
    """Thyme and phrygana scrub: low grey-green cushions, some in purple flower, stones."""
    m = Model.empty(0, 16, 0, 16, 0, 6, k=k)

    def d(rng, x, y, i):
        ellipsoid(m, (x, y, 0.8), (1.6, 1.6, 1.2), ("olive", "olive_silver", "leaf_dark")[i % 3], tone=rng.uniform(-0.3, 0.3))
        if i % 3 == 0:
            ellipsoid(m, (x + 0.4, y, 1.8), (0.7, 0.7, 0.5), "violet", tone=0.3)
    _ground_cover(m, v, 9, d)
    return m


def p_barley(v, frame, frames, k):
    """Barley stubble after the harvest (July): short gold stalks in rows, a few gleaned ears."""
    m = Model.empty(0, 16, 0, 16, 0, 4, k=k)
    for x in np.arange(1.0, 16.0, 2.0):
        for y in np.arange(0.5, 16.0, 1.0):
            rod(m, (x, y, 0.0), (x + 0.2, y, 1.6 + (int(x * 7 + y * 3) % 3) * 0.4), 0.22, "straw", tone=0.2)
    return m


def p_acanthus(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, 0, 10, k=k)
    for a in np.linspace(0, 2 * math.pi, 7, endpoint=False):
        ellipsoid(m, (8 + 3.4 * math.cos(a), 8 + 3.4 * math.sin(a), 2.4), (2.4, 1.4, 1.2), "leaf_dark", tone=0.2)
    rod(m, (8, 8, 0.0), (8, 8, 9.0), 0.4, "leaf")
    for z in (5.0, 6.5, 8.0):
        ellipsoid(m, (8, 8, z), (0.8, 0.8, 0.6), "violet", tone=0.2)
    return m


def p_reeds(v, frame, frames, k):
    """Reeds by the Ilissos and the Eridanos, swaying (two frames)."""
    m = Model.empty(-2, 18, -2, 18, 0, 22, k=k)
    rng = Rng(1090, v)
    for i in range(16):
        x, y = rng.uniform(2, 14), rng.uniform(2, 14)
        h = rng.uniform(12, 20)
        sway = (1.2 if frame else 0.0) + rng.uniform(-0.5, 0.5)
        rod(m, (x, y, 0.0), (x + sway, y + sway * 0.4, h), 0.25, "grass", tone=rng.uniform(-0.2, 0.3))
        if i % 3 == 0:
            ellipsoid(m, (x + sway, y + sway * 0.4, h + 0.8), (0.5, 0.5, 1.4), "wood_light", tone=0.1)
    return m


def p_asphodel(v, frame, frames, k):
    """Summer-dry grass and the dead stalks of asphodel with their seed heads."""
    m = Model.empty(0, 16, 0, 16, 0, 8, k=k)
    rng = Rng(1100, v)
    for i in range(22):
        x, y = rng.uniform(1, 15), rng.uniform(1, 15)
        rod(m, (x, y, 0.0), (x + rng.uniform(-0.6, 0.6), y + rng.uniform(-0.6, 0.6), rng.uniform(1.5, 3.0)), 0.25,
            "straw", tone=rng.uniform(-0.3, 0.3))
    for i in range(3):
        x, y = rng.uniform(3, 13), rng.uniform(3, 13)
        rod(m, (x, y, 0.0), (x, y, 7.0), 0.3, "wood_light", tone=0.1)
        for j in range(4):
            ellipsoid(m, (x + 0.4 * (j % 2), y, 4.5 + j * 0.6), (0.5, 0.5, 0.4), "wood", tone=0.2)
    return m


ITEMS = {f"athens.{n}": Item(fn) for n, fn in (
    ("t_olive", t_olive), ("t_plane", t_plane), ("t_cypress", t_cypress), ("t_pine", t_pine), ("t_fig", t_fig),
    ("t_vine", t_vine), ("t_poplar", t_poplar), ("t_agnus", t_agnus), ("t_oleander", t_oleander),
    ("t_myrtle", t_myrtle), ("t_laurel", t_laurel), ("p_thyme", p_thyme), ("p_barley", p_barley),
    ("p_acanthus", p_acanthus), ("p_reeds", p_reeds), ("p_asphodel", p_asphodel))}

FRAMES = {"athens.p_reeds": 2}
