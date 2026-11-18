"""Rome's plants in April (rome.md §3.4): umbrella pines (used moderately: the city-wide pine
look is partly modern), cypresses at tombs and gardens, planes shading porticoes, laurel by the
palace doors, myrtle, the fig, the olive, vines in fresh leaf, box topiary, roses, poplars and
holm oaks, acanthus, poppies in the grass, Tiber reeds (swaying) and market-garden beds.
Canopies use the home set's leaf clusters (models/nature.py), so every set's trees sit
together in one world."""

import math

import numpy as np

from arch import ellipsoid, fill, rod
from models.nature import leaf_mass
from setbuild import Item
from sets.rome.common import box_hedge, cypress, laurel, olive_tree, plane_tree, stone_pine
from voxel import Model, Rng, hash01, value_noise


def _tree(k, top, r=10):
    return Model.empty(-r, 16 + r, -r, 16 + r, 0, top, k=k)


def t_stone_pine(v, frame, frames, k):
    m = _tree(k, 64, 16)
    stone_pine(m, 8.0, 8.0, 0.0, h=54.0 + 6 * v, seed=v)
    return m


def t_cypress(v, frame, frames, k):
    m = _tree(k, 60, 6)
    cypress(m, 8.0, 8.0, 0.0, h=48.0 + 6 * v, seed=v + 20)
    return m


def t_plane(v, frame, frames, k):
    m = _tree(k, 60, 15)
    plane_tree(m, 8.0, 8.0, 0.0, h=52.0 + 4 * v, seed=v)
    return m


def t_laurel(v, frame, frames, k):
    m = _tree(k, 30, 6)
    laurel(m, 8.0, 8.0, 0.0, h=24.0, seed=v + 3)
    return m


def t_myrtle(v, frame, frames, k):
    """Myrtle, sacred to Venus: a dense dark bush starred with white flowers."""
    m = _tree(k, 18, 4)
    rng = Rng(1510, v)
    clumps = [(8 + rng.uniform(-2, 2), 8 + rng.uniform(-2, 2), rng.uniform(5.0, 10.0), rng.uniform(3.0, 4.0))
              for _ in range(4)]
    leaf_mass(m, clumps, 1511 + v, materials=(("leaf_dark", 0.8), ("leaf", 0.2)), under="leaf_dark", cluster=(1.6, 2.2))
    X, Y, Z = m.coords()
    from palette import MAT
    m.put((m.mat == MAT["leaf"]) & (hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64),
                                           np.floor(Z * 2).astype(np.int64), 1512) < 0.12), "white_paint", 0.3)
    return m


def t_fig(v, frame, frames, k):
    """A fig: a low spreading grey trunk, big lobed leaves just opening in April."""
    from sets.athens.kit import _fig
    m = _tree(k, 28, 10)
    _fig(m, 8.0, 8.0, 0.0, 18.0 + 3 * v, 1520 + v)
    return m


def t_olive(v, frame, frames, k):
    m = _tree(k, 36, 12)
    olive_tree(m, 8.0, 8.0, 0.0, h=24.0 + 3 * v, seed=v + 40, spread=1.0 + 0.1 * v, gnarled=1.0 + 0.3 * v)
    return m


def t_vine(v, frame, frames, k):
    """A vine trained on a stake and a cross-pole, in fresh April leaf."""
    m = _tree(k, 22, 4)
    rod(m, (8.0, 8.0, 0.0), (8.0, 8.0, 14.0), 0.35, "wood")
    rod(m, (8.0, 2.0, 13.0), (8.0, 14.0, 13.0), 0.3, "wood")
    rod(m, (8.0, 8.0, 0.0), (7.0, 7.0, 10.0), 0.6, "bark")
    leaf_mass(m, [(8.0, 5.0, 13.0, 2.6), (8.0, 11.0, 13.0, 2.6), (7.0, 8.0, 10.0, 2.4)], 1530 + v,
              materials=(("leaf", 0.5), ("grass", 0.5)), under="leaf_dark", squash=0.7)
    return m


def t_box(v, frame, frames, k):
    """Box topiary of the peristyles: a clipped hedge block, a ball or a cone."""
    m = _tree(k, 20, 2)
    if v == 0:
        box_hedge(m, 1.0, 15.0, 4.0, 12.0, 0.0, 5.0)
    elif v == 1:
        fill(m, (2, 14, 2, 14, 0, 12), "leaf_dark", lambda X, Y, Z: (X - 8) ** 2 + (Y - 8) ** 2 + (Z - 5.5) ** 2 < 30,
             tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z * 2, 1.2, 1540) - 0.5) * 1.2 + 0.3 * (Z > 7),
             normal=lambda X, Y, Z: (X - 8, Y - 8, Z - 5.5))
    else:
        fill(m, (2, 14, 2, 14, 0, 16), "leaf_dark", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 5.0 * (1 - Z / 16.0),
             tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z * 2, 1.2, 1541) - 0.5) * 1.2,
             normal=lambda X, Y, Z: (X - 8, Y - 8, 2.0 + Z * 0))
    return m


def t_rose(v, frame, frames, k):
    """Roses for gardens and festival garlands (red, pink, white)."""
    m = _tree(k, 14, 3)
    rng = Rng(1550, v)
    clumps = [(8 + rng.uniform(-3, 3), 8 + rng.uniform(-3, 3), rng.uniform(3.0, 6.0), rng.uniform(2.2, 3.0))
              for _ in range(4)]
    leaf_mass(m, clumps, 1551 + v, materials=(("leaf", 0.7), ("leaf_dark", 0.3)), under="leaf_dark", cluster=(1.6, 2.2))
    X, Y, Z = m.coords()
    from palette import MAT
    flower = (m.mat == MAT["leaf"]) & (hash01(np.floor(X * 1.5).astype(np.int64), np.floor(Y * 1.5).astype(np.int64),
                                              np.floor(Z * 1.5).astype(np.int64), 1552 + v) < 0.25)
    m.put(flower, ("poppy", "blossom", "white_paint")[v % 3], 0.3)
    return m


def t_poplar(v, frame, frames, k):
    """A poplar by the river: tall and narrow, leaves shimmering silver-green."""
    m = _tree(k, 60, 7)
    rng = Rng(1560, v)
    rod(m, (8, 8, 0.0), (8, 8, 20.0), 1.0, "wood_grey")
    clumps = [(8 + rng.uniform(-1.5, 1.5), 8 + rng.uniform(-1.5, 1.5), 14.0 + i * 5.0, 4.2 - abs(i - 4) * 0.35)
              for i in range(8)]
    leaf_mass(m, clumps, 1561 + v, materials=(("leaf", 0.5), ("olive_silver", 0.5)), under="leaf_dark",
              cluster=(1.8, 2.6), squash=1.2)
    return m


def t_oak(v, frame, frames, k):
    """A holm oak: a dense, rounded crown of dark evergreen leaves on a short grey trunk."""
    m = _tree(k, 48, 14)
    rng = Rng(1570, v)
    rod(m, (8, 8, 0.0), (8 + rng.uniform(-1, 1), 8 + rng.uniform(-1, 1), 16.0), 1.6, "wood_grey")
    clumps = [(8 + 6.0 * math.cos(a), 8 + 6.0 * math.sin(a), 26.0 + rng.uniform(-2, 3), rng.uniform(6.0, 7.5))
              for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)] + [(8, 8, 34.0, 7.0)]
    leaf_mass(m, clumps, 1571 + v, materials=(("leaf_dark", 0.8), ("olive", 0.2)), under="leaf_dark", level=-0.8)
    return m


def _ground_cover(m, seed, n, draw):
    rng = Rng(seed)
    for i in range(n):
        draw(m, rng.uniform(2.0, 14.0), rng.uniform(2.0, 14.0), rng, i)


def p_acanthus(v, frame, frames, k):
    m = _tree(k, 12, 2)

    def d(m, x, y, rng, i):
        for a in np.linspace(0, 2 * math.pi, 6, endpoint=False):
            rod(m, (x, y, 0.5), (x + 3.0 * math.cos(a), y + 3.0 * math.sin(a), 2.0 + rng.uniform(0, 1.5)), 0.7,
                "leaf_dark", 0.2)
        rod(m, (x, y, 0.0), (x, y, 8.0), 0.35, "white_paint" if i % 2 else "violet", 0.2)
    _ground_cover(m, 1580 + v, 2, d)
    return m


def p_poppy(v, frame, frames, k):
    """Poppies in the April grass."""
    m = _tree(k, 8, 1)

    def d(m, x, y, rng, i):
        rod(m, (x, y, 0.0), (x, y, 3.5 + rng.uniform(0, 2)), 0.2, "leaf")
        ellipsoid(m, (x, y, 4.5 + rng.uniform(0, 1.5)), (0.8, 0.8, 0.5), "poppy", 0.3)
    _ground_cover(m, 1590 + v, 12, d)
    return m


def p_reeds(v, frame, frames, k):
    """Reeds on the Tiber banks, swaying in the wind (two frames)."""
    m = _tree(k, 22, 3)
    sway = 1.2 * (frame % 2) - 0.6

    def d(m, x, y, rng, i):
        h = rng.uniform(10.0, 16.0)
        rod(m, (x, y, 0.0), (x + sway, y + sway * 0.5, h), 0.25, "olive", 0.2)
        ellipsoid(m, (x + sway, y + sway * 0.5, h + 1.0), (0.4, 0.4, 1.4), "straw", 0.2)
    _ground_cover(m, 1600 + v, 14, d)
    return m


def p_cabbage(v, frame, frames, k):
    """Market-garden beds: rows of cabbages, leeks and lettuces in dark worked soil."""
    m = _tree(k, 6, 0)
    fill(m, (0.5, 15.5, 0.5, 15.5, 0.0, 0.6), "soil", tone=0.0)
    for row in range(4):
        for i in range(5):
            x, y = 2.0 + row * 4.0, 2.0 + i * 3.0
            if v == 0:
                ellipsoid(m, (x, y, 1.4), (1.3, 1.3, 1.0), ("leaf", "grass", "olive")[(row + i) % 3], 0.2)
            else:
                rod(m, (x, y, 0.6), (x, y, 3.6), 0.4, "grass", 0.3)
    return m


ITEMS = {f"rome.{n}": Item(fn) for n, fn in (
    ("t_stone_pine", t_stone_pine), ("t_cypress", t_cypress), ("t_plane", t_plane), ("t_laurel", t_laurel),
    ("t_myrtle", t_myrtle), ("t_fig", t_fig), ("t_olive", t_olive), ("t_vine", t_vine), ("t_box", t_box),
    ("t_rose", t_rose), ("t_poplar", t_poplar), ("t_oak", t_oak), ("p_acanthus", p_acanthus), ("p_poppy", p_poppy),
    ("p_reeds", p_reeds), ("p_cabbage", p_cabbage))}

FRAMES = {"rome.p_reeds": 2}

# name, variants, layers, height px, fps
PLANT_INFO = {
    "t_stone_pine": ("Stone (umbrella) pine", 3, "BS", 120, 0), "t_cypress": ("Cypress", 2, "BS", 110, 0),
    "t_plane": ("Plane", 2, "BS", 110, 0), "t_laurel": ("Laurel (bay)", 1, "BS", 50, 0),
    "t_myrtle": ("Myrtle", 1, "BS", 30, 0), "t_fig": ("Fig", 2, "BS", 55, 0), "t_olive": ("Olive", 3, "BS", 55, 0),
    "t_vine": ("Vine", 2, "BS", 30, 0), "t_box": ("Box topiary", 3, "BS", 16, 0), "t_rose": ("Roses", 3, "BS", 14, 0),
    "t_poplar": ("Poplar", 2, "BS", 100, 0), "t_oak": ("Holm oak", 2, "BS", 80, 0),
    "p_acanthus": ("Acanthus", 1, "B", 14, 0), "p_poppy": ("Poppies in grass", 2, "B", 8, 0),
    "p_reeds": ("Reeds", 2, "B", 30, 2), "p_cabbage": ("Market-garden beds", 2, "B", 8, 0),
}
