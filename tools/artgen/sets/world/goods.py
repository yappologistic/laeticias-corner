"""The goods of road and sea (docs/design/sets/world.md §5.4): the carried unit
(`goods/<id>`, 10-16 px) and stacks of one to three at a slot (`goods/<id>/s<n>`, at most 24 x 20),
small voxel models rendered like the city sets' goods."""

import re

import numpy as np

from arch import ellipsoid, fill, revolve, rod, slab
from pack import Sprite
from render import render_base
from voxel import Model

OFFSETS = ((0.0, 0.0, 0.0), (0.0, 4.6, 0.0), (2.2, 2.3, 3.0))


def _one(m, name, x, y, z, i):
    if name == "goods_sacks":
        ellipsoid(m, (x, y, z + 2.0), (2.2, 1.8, 2.0), "straw", tone=-0.1 + 0.1 * i)
        ellipsoid(m, (x, y, z + 4.0), (0.8, 0.8, 0.6), "straw", tone=0.2)
    elif name == "goods_amphorae":
        revolve(m, x, y, z, z + 5.5, lambda t: 0.4 + 1.6 * np.sin(np.pi * np.clip(t * 1.15 - 0.05, 0, 1)) ** 0.8,
                "clay", tone=0.05 * i)
        rod(m, (x - 0.9, y, z + 4.8), (x - 0.9, y, z + 5.8), 0.25, "clay")
        rod(m, (x + 0.9, y, z + 4.8), (x + 0.9, y, z + 5.8), 0.25, "clay")
    elif name == "goods_bale":
        slab(m, x - 2.2, x + 2.2, y - 1.6, y + 1.6, z, z + 2.8, "linen", tone=0.1)
        for xx in (x - 1.0, x + 1.0):
            fill(m, (xx - 0.25, xx + 0.25, y - 1.8, y + 1.8, z - 0.1, z + 3.0), "straw", tone=-0.1)
    elif name == "goods_fish":
        revolve(m, x, y, z, z + 1.4, lambda t: 2.4 + 0.3 * t, "straw", tone=-0.1)
        for j in range(3):
            ellipsoid(m, (x - 1.0 + j, y + (j - 1) * 0.6, z + 1.6), (1.2, 0.4, 0.3), "stone", tone=0.4)
    elif name == "goods_dates":
        revolve(m, x, y, z, z + 2.2, lambda t: 1.6 + 0.6 * t, "straw", tone=0.0)
        ellipsoid(m, (x, y, z + 2.4), (1.8, 1.8, 0.8), "orange", tone=-0.2)
    elif name == "goods_fleece":
        rod(m, (x - 2.0, y, z + 1.3), (x + 2.0, y, z + 1.3), 1.3, "wool", tone=0.1)
        ellipsoid(m, (x - 2.0, y, z + 1.3), (0.4, 1.0, 1.0), "cream", tone=0.2)
    elif name == "goods_letter":
        slab(m, x - 1.2, x + 1.2, y - 0.6, y + 0.6, z, z + 1.8, "leather", tone=0.1)
        ellipsoid(m, (x, y + 0.7, z + 1.0), (0.4, 0.2, 0.4), "cinnabar", tone=0.3)
    elif name == "goods_waterskin":
        ellipsoid(m, (x, y, z + 1.6), (2.0, 1.2, 1.5), "hide", tone=0.1)
        rod(m, (x + 1.8, y, z + 2.0), (x + 2.6, y, z + 3.0), 0.35, "hide", tone=0.2)
    elif name == "goods_firewood":
        for j, (a, b) in enumerate(((-0.6, 0.0), (0.6, 0.0), (0.0, 0.9), (0.0, -0.6))):
            rod(m, (x - 2.4, y + a, z + 0.8 + b), (x + 2.4, y + a, z + 0.8 + b), 0.45, ("wood", "wood_light")[j % 2], tone=0.1)
        rod(m, (x, y - 1.2, z + 1.0), (x, y + 1.2, z + 1.0), 0.15, "straw")
    elif name == "goods_charcoal":
        ellipsoid(m, (x, y, z + 2.0), (2.2, 1.8, 2.0), "straw", tone=-0.3)
        ellipsoid(m, (x, y, z + 3.8), (1.4, 1.2, 0.7), "ink", tone=0.3)
    elif name == "goods_reeds":
        for j in range(5):
            rod(m, (x - 3.0, y + (j - 2) * 0.4, z + 0.6 + (j % 2) * 0.4), (x + 3.0, y + (j - 2) * 0.4, z + 0.6 + (j % 2) * 0.4),
                0.3, ("straw", "summer")[j % 2], tone=0.1)
        rod(m, (x, y - 1.2, z + 0.8), (x, y + 1.2, z + 0.8), 0.15, "wood")
    elif name == "goods_salt":
        revolve(m, x, y, z, z + 1.8, lambda t: 1.8 + 0.3 * t, "straw", tone=-0.1)
        ellipsoid(m, (x, y, z + 2.0), (1.8, 1.8, 0.9), "white_paint", tone=0.3)
    elif name == "goods_logs":
        for j, (a, b) in enumerate(((-0.8, 0.0), (0.8, 0.0), (0.0, 1.3))):
            rod(m, (x - 3.0, y + a, z + 0.8 + b), (x + 3.0, y + a, z + 0.8 + b), 0.75, "cedar", tone=0.1)
            fill(m, (x + 2.8, x + 3.2, y + a - 0.8, y + a + 0.8, z + b, z + 1.6 + b), "wood_light", tone=0.3, only_solid=True)
    else:
        raise KeyError(name)


def sprite(key, k):
    m_ = re.fullmatch(r"goods/world\.(\w+?)(?:/s(\d))?", key)
    name, n = m_[1], int(m_[2] or 1)
    m = Model.empty(-12, 12, -12, 12, 0, 16, k=k)
    for i, (dx, dy, dz) in enumerate(OFFSETS[:n]):
        _one(m, name, dx, dy, dz, i)
    rgba, _g, ox, oy = render_base(m)
    return Sprite(rgba, ox, oy)
