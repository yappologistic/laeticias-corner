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
    # The life data's chains (out/reports/world-life.md): building, bread, writing, gifts, cloth,
    # bricks and glazed bricks, pottery, oil and silver.
    elif name == "goods_block":
        slab(m, x - 2.2, x + 2.2, y - 1.5, y + 1.5, z, z + 2.4, "limestone", tone=0.1 - 0.1 * i)
        fill(m, (x - 2.2, x + 2.2, y - 1.5, y + 1.5, z + 2.0, z + 2.4), "limestone", tone=0.4, only_solid=True)
    elif name == "goods_flour":
        ellipsoid(m, (x, y, z + 2.0), (2.0, 1.7, 2.0), "linen", tone=0.2 - 0.1 * i)
        ellipsoid(m, (x, y, z + 3.9), (0.7, 0.7, 0.5), "linen", tone=0.35)
    elif name == "goods_bread":
        revolve(m, x, y, z, z + 0.8, lambda t: 2.4, "straw", tone=-0.2)
        for j, (a, b) in enumerate(((-0.9, -0.6), (0.9, -0.4), (0.0, 0.9))):
            ellipsoid(m, (x + a, y + b, z + 1.3), (1.0, 1.0, 0.6), "ochre", tone=0.2 - 0.15 * j)
    elif name == "goods_tablet":
        slab(m, x - 1.4, x + 1.4, y - 1.0, y + 1.0, z, z + 0.9, "clay", tone=0.15)
        fill(m, (x - 1.0, x + 1.0, y - 0.7, y + 0.7, z + 0.85, z + 0.9), "clay", tone=-0.6,
             mask=lambda X, Y, Z: ((X * 4).astype(int) % 2 == 0) & ((Y * 3).astype(int) % 3 != 2))
    elif name == "goods_gift_vessels":
        revolve(m, x - 1.0, y, z, z + 3.0, lambda t: 0.6 + 0.9 * np.sin(np.pi * np.clip(t, 0, 1)), "gold", tone=0.2)
        revolve(m, x + 1.2, y + 0.5, z, z + 1.2, lambda t: 1.2 - 0.4 * (1 - t), "gold", tone=0.0)
        rod(m, (x - 1.0, y, z + 3.0), (x - 1.0, y, z + 3.6), 0.3, "gold", tone=0.4)
    elif name == "goods_yarn":
        for j, (a, b) in enumerate(((-1.0, 0.0), (1.0, 0.0), (0.0, 1.4))):
            ellipsoid(m, (x + a, y + b * 0.3, z + 1.0 + b * 0.8), (1.0, 1.0, 1.0), ("wool", "cinnabar", "lapis")[(j + i) % 3],
                      tone=lambda X, Y, Z: 0.3 * ((X + Y + Z) % 0.8 < 0.3))
    elif name == "goods_cloth":
        for j in range(3):
            slab(m, x - 2.0, x + 2.0, y - 1.4, y + 1.4, z + j * 0.7, z + j * 0.7 + 0.7,
                 ("linen", "purple", "saffron")[(j + i) % 3], tone=0.1 + 0.3 * ((j % 2) == 0))
    elif name == "goods_brick":
        for j in range(3):
            slab(m, x - 1.8, x + 1.8, y - 1.0 + (j % 2) * 0.2, y + 1.0 + (j % 2) * 0.2, z + j * 0.9, z + j * 0.9 + 0.85,
                 "mudbrick", tone=0.2 - 0.1 * j)
    elif name == "goods_glazed_brick":
        for j in range(3):
            slab(m, x - 1.8, x + 1.8, y - 1.0, y + 1.0, z + j * 0.9, z + j * 0.9 + 0.85, "mudbrick", tone=0.0)
            fill(m, (x + 1.5, x + 1.8, y - 1.0, y + 1.0, z + j * 0.9, z + j * 0.9 + 0.85),
                 ("glaze_blue", "glaze_yellow", "glaze_blue")[j], tone=0.3)
    elif name == "goods_dish":
        for j in range(3):
            revolve(m, x, y, z + j * 0.5, z + j * 0.5 + 0.5, lambda t: 2.0 + 0.5 * t, "clay", tone=0.1 + 0.1 * j)
    elif name == "goods_pot_raw":
        revolve(m, x, y, z, z + 3.2, lambda t: 0.8 + 1.1 * np.sin(np.pi * np.clip(t * 0.9 + 0.1, 0, 1)), "plaster",
                tone=-0.2)
    elif name == "goods_pot_painted":
        revolve(m, x, y, z, z + 3.2, lambda t: 0.8 + 1.1 * np.sin(np.pi * np.clip(t * 0.9 + 0.1, 0, 1)), "clay",
                tone=lambda X, Y, Z: -0.9 * ((Z % 1.0) < 0.3))
    elif name == "goods_oil_jar":
        revolve(m, x, y, z, z + 4.0, lambda t: 0.5 + 1.4 * np.clip(np.sin(np.pi * np.clip(t * 1.05, 0, 1)), 0, 1) ** 0.7, "clay",
                tone=0.05 * i)
        rod(m, (x, y, z + 4.0), (x, y, z + 4.6), 0.45, "clay", tone=0.2)
        ellipsoid(m, (x, y, z + 4.7), (0.5, 0.5, 0.25), "wood", tone=0.1)
    elif name == "goods_silver":
        for j, (a, b) in enumerate(((-0.8, -0.4), (0.8, 0.0), (0.0, 0.8))):
            slab(m, x + a - 1.1, x + a + 1.1, y + b - 0.5, y + b + 0.5, z + j * 0.4, z + j * 0.4 + 0.5, "metal", tone=0.4)
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
