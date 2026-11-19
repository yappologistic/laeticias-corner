"""The world's plants and natural props (docs/design/sets/world.md §2.1), each a small family of
looks so scattered plants never tile: the deciduous oaks of Italy, Thrace and Anatolia and the
Persian oak of the Zagros park woods, beech, fir and the tiered cedar of the Taurus, wild
pistachio, tamarisk, date-palm clumps, tall reed beds that sway, evergreen scrub, thistles,
wildflowers of six stretches, juniper, cork oak and oleaster; boulders, rock tors, summits and
driftwood. Canopies use the home set's leaf clusters (models/nature.py), as the city sets do, so
trees of every set stand together in one world. Only the reed bed moves (two frames)."""

import math

import numpy as np

from arch import ellipsoid, field_fill, fill, rod
from models.nature import leaf_mass
from setbuild import Item
from voxel import Model, Rng, hash01, value_noise


def _tree(k, top, r=10, fw=1, fh=1):
    return Model.empty(-r, fw * 16 + r, -r, fh * 16 + r, 0, top, k=k)


def _trunk(m, base, top, r, mat="bark", seed=0):
    """A trunk with a little taper, its bark in furrows."""
    (x0, y0, z0), (x1, y1, z1) = base, top
    n = 6
    for i in range(n):
        a, b = i / n, (i + 1) / n
        p = (x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, z0 + (z1 - z0) * a)
        q = (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b, z0 + (z1 - z0) * b)
        rod(m, p, q, r * (1.0 - 0.35 * a), mat, tone=lambda X, Y, Z: 0.35 * (np.sin((X + Y) * 2.1 + Z * 0.4) > 0.6) - 0.1)


def _crown(m, x, y, z, n, rad, spread, rng, lift=(0.0, 0.0)):
    """Clumps round a centre: (x, y, z, r) for leaf_mass."""
    out = []
    for i in range(n):
        a = i * 2 * math.pi / n + rng.uniform(-0.4, 0.4)
        r = spread * rng.uniform(0.55, 1.0)
        out.append((x + r * math.cos(a), y + r * math.sin(a), z + rng.uniform(*lift), rad * rng.uniform(0.8, 1.1)))
    return out


# ---------------------------------------------------------------- trees

def t_oak(v, frame, frames, k):
    """A deciduous oak (downy, Turkey or valonia): grey furrowed trunk, a broad crown of lobed
    leaves. r0 full and round, r1 an old pollard with a knobbed head of young shoots, r2 a
    young tree, r3 a lopsided field oak leaning from the wind."""
    rng = Rng(5100, v)
    m = _tree(k, 50, 16)
    if v == 0:
        _trunk(m, (8, 8, 0), (8.5, 8.5, 16.0), 2.0, "wood_grey")
        for a in (0.3, 2.3, 4.2):
            rod(m, (8.5, 8.5, 14.0), (8 + 8 * math.cos(a), 8 + 8 * math.sin(a), 24.0), 1.1, "wood_grey")
        clumps = _crown(m, 8, 8, 28.0, 6, 7.0, 8.0, rng, (-2, 3)) + [(8, 8, 36.0, 8.0)]
    elif v == 1:
        _trunk(m, (8, 8, 0), (8, 8, 12.0), 2.6, "wood_grey")
        ellipsoid(m, (8, 8, 13.0), (3.4, 3.4, 2.4), "wood_grey", tone=0.1)
        clumps = _crown(m, 8, 8, 18.0, 5, 4.6, 4.5, rng, (0, 3)) + [(8, 8, 22.0, 5.0)]
    elif v == 2:
        _trunk(m, (8, 8, 0), (8.2, 8.0, 12.0), 1.0, "wood_grey")
        clumps = _crown(m, 8, 8, 18.0, 4, 4.4, 3.6, rng, (0, 3)) + [(8, 8, 24.0, 4.6)]
    else:
        lean = (4.0, -2.5)
        _trunk(m, (8, 8, 0), (8 + lean[0], 8 + lean[1], 15.0), 1.8, "wood_grey")
        clumps = [(8 + lean[0] * 1.6 + rng.uniform(-3, 3), 8 + lean[1] * 1.6 + rng.uniform(-3, 3), 24.0 + rng.uniform(-2, 4),
                   rng.uniform(5.5, 7.5)) for _ in range(5)] + [(8 + lean[0], 8 + lean[1], 30.0, 6.5)]
    leaf_mass(m, clumps, 5101 + v, materials=(("leaf", 0.6), ("grass", 0.25), ("olive", 0.15)), under="leaf_dark",
              level=-0.6)
    return m


def t_oak_zagros(v, frame, frames, k):
    """Brant's oak of the Zagros park woodland: low and broad, several stems from the base, an
    open crown with sky through it."""
    rng = Rng(5110, v)
    m = _tree(k, 34, 16)
    stems = 2 + v
    clumps = []
    for i in range(stems):
        a = i * 2 * math.pi / stems + rng.uniform(-0.3, 0.3)
        tx, ty = 8 + 5.5 * math.cos(a), 8 + 5.5 * math.sin(a)
        _trunk(m, (8 + math.cos(a), 8 + math.sin(a), 0), (tx, ty, 14.0 + rng.uniform(-2, 2)), 1.0, "wood_grey")
        clumps += [(tx + rng.uniform(-2.5, 2.5), ty + rng.uniform(-2.5, 2.5), 17.0 + rng.uniform(-2, 3), rng.uniform(3.8, 5.0))
                   for _ in range(2)]
    leaf_mass(m, clumps, 5111 + v, materials=(("olive", 0.55), ("leaf", 0.3), ("leaf_dark", 0.15)), under="leaf_dark",
              cluster=(2.2, 3.0), squash=0.7, level=-0.5)
    return m


def t_beech(v, frame, frames, k):
    """Beech of the Apennines and Thrace: a smooth silver trunk, a dense rounded crown in the
    fresh green of April."""
    rng = Rng(5120, v)
    m = _tree(k, 54, 14)
    h = (22.0, 18.0, 25.0)[v]
    rod(m, (8, 8, 0), (8, 8, h), 1.7, "wood_grey", tone=lambda X, Y, Z: 0.4 * (value_noise(X, Y, Z * 0.4, 1.4, 5121) > 0.68))
    for a in (0.8, 2.9, 4.8):
        rod(m, (8, 8, h * 0.7), (8 + 5 * math.cos(a), 8 + 5 * math.sin(a), h + 6.0), 0.8, "wood_grey")
    clumps = _crown(m, 8, 8, h + 10.0, 6, 6.2, 6.5, rng, (-3, 4)) + [(8, 8, h + 18.0, 6.8), (8, 8, h + 8.0, 6.5)]
    leaf_mass(m, clumps, 5122 + v, materials=(("grass", 0.55), ("leaf", 0.45)), under="leaf", level=-0.35)
    return m


def t_fir(v, frame, frames, k):
    """Silver (Greek) fir: a dark narrow cone of level branch tiers, three heights. Snow on it
    is the season's (the shader path's snow bit on its up-facing needles), never a look."""
    rng = Rng(5130, v)
    h = (50.0, 44.0, 48.0)[v]
    m = _tree(k, int(h) + 4, 9)
    rod(m, (8, 8, 0), (8, 8, h), 1.0, "bark")
    tiers = 9
    for i in range(tiers):
        t = i / (tiers - 1)
        z = 6.0 + t * (h - 8.0)
        r = 7.5 * (1 - t) ** 0.9 + 1.2
        clumps = [(8 + r * 0.6 * math.cos(a), 8 + r * 0.6 * math.sin(a), z, r * 0.55)
                  for a in np.linspace(0, 2 * math.pi, 5, endpoint=False) + rng.uniform(0, 1)]
        leaf_mass(m, clumps, 5131 + v * 17 + i, materials=(("leaf_dark", 1.0),), under="leaf_dark",
                  cluster=(1.8, 2.4), squash=0.45, level=-1.0)
    return m


def t_cedar(v, frame, frames, k):
    """Cedar of Lebanon and the Taurus: a massive trunk and flat tiered plates of blue-green
    needles held out level, the timber of empires."""
    rng = Rng(5140, v)
    m = _tree(k, 60, 18)
    _trunk(m, (8, 8, 0), (8, 8, 40.0), 2.4, "bark")
    plates = ((14.0, 11.0), (24.0, 9.5), (33.0, 7.5), (41.0, 5.5), (48.0, 3.5)) if v == 0 else \
        ((12.0, 10.0), (21.0, 11.5), (31.0, 8.0), (40.0, 4.5))
    for i, (z, r) in enumerate(plates):
        a0 = rng.uniform(0, 2 * math.pi)
        for j in range(3):
            a = a0 + j * 2.1
            ox, oy = r * 0.45 * math.cos(a), r * 0.45 * math.sin(a)
            rod(m, (8, 8, z - 1.5), (8 + ox * 1.6, 8 + oy * 1.6, z - 0.5), 0.6, "bark")
        clumps = [(8 + r * 0.5 * math.cos(a0 + j * 2.1), 8 + r * 0.5 * math.sin(a0 + j * 2.1), z, r * 0.62) for j in range(3)]
        clumps.append((8, 8, z, r * 0.55))
        leaf_mass(m, clumps, 5141 + v * 13 + i, materials=(("leaf_dark", 0.7), ("olive", 0.3)), under="leaf_dark",
                  cluster=(2.0, 2.8), squash=0.32, level=-0.7)
    return m


def t_pistachio(v, frame, frames, k):
    """Wild pistachio (Pistacia atlantica): a short trunk and a rounded grey-green crown with
    clusters of reddish fruit."""
    rng = Rng(5150, v)
    m = _tree(k, 32, 13)
    _trunk(m, (8, 8, 0), (8 + rng.uniform(-1, 1), 8, 9.0), 1.6, "wood_grey")
    clumps = _crown(m, 8, 8, 17.0, 5, 5.0, 5.0, rng, (-1, 3)) + [(8, 8, 22.0, 5.4)]
    leaf_mass(m, clumps, 5151 + v, materials=(("olive", 0.75), ("olive_silver", 0.25)), under="olive", level=-0.9)
    for i in range(7 + 3 * v):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(3, 7)
        ellipsoid(m, (8 + r * math.cos(a), 8 + r * math.sin(a), rng.uniform(14, 22)), (0.8, 0.8, 0.7),
                  ("rust", "cinnabar")[i % 2], tone=0.3)
    return m


def t_tamarisk(v, frame, frames, k):
    """Tamarisk of desert rivers and the Gulf shore: a feathery grey-green shrub-tree of many
    thin stems; r1 in pink flower plumes."""
    rng = Rng(5160, v)
    m = _tree(k, 28, 10)
    clumps = []
    for i in range(5 + v):
        a = rng.uniform(0, 2 * math.pi)
        top = (8 + 5 * math.cos(a), 8 + 5 * math.sin(a), rng.uniform(13, 19))
        rod(m, (8 + math.cos(a), 8 + math.sin(a), 0), top, 0.45, "bark")
        clumps.append((*top, rng.uniform(3.0, 4.2)))
    mats = (("olive_silver", 0.55), ("olive", 0.45)) if v != 1 else (("olive_silver", 0.4), ("blossom", 0.45), ("olive", 0.15))
    leaf_mass(m, clumps, 5161 + v, materials=mats, under="olive", cluster=(1.4, 2.0), squash=1.1, level=-0.8)
    return m


def t_palm(v, frame, frames, k):
    """r0 a clump of three date palms of different heights with offshoots at their feet, r1 a
    young palm whose fronds reach the ground. Ringed trunks, arching fronds, date clusters."""
    rng = Rng(5170, v)
    m = _tree(k, 54, 16)

    def palm(x, y, h, lean, n=12, frond=11.0, dates=True):
        pts = [(x + lean[0] * t * t, y + lean[1] * t * t, t * h) for t in np.linspace(0, 1, 12)]
        for a, b in zip(pts, pts[1:]):
            rod(m, a, b, 1.2, "bark", tone=0.25 * ((a[2] % 2.4) < 1.0) - 0.05)
        top = pts[-1]
        for i in range(n):
            az = i * 2 * math.pi / n + rng.uniform(-0.25, 0.25)
            L = frond * rng.uniform(0.85, 1.1)
            # Fronds arch up and out, then droop: three segments, leaflets thickening the middle.
            up = 2.6 if i % 2 else 1.2
            p1 = (top[0] + L * 0.35 * math.cos(az), top[1] + L * 0.35 * math.sin(az), top[2] + up)
            p2 = (top[0] + L * 0.7 * math.cos(az), top[1] + L * 0.7 * math.sin(az), top[2] + up * 0.3 - 1.5)
            end = (top[0] + L * math.cos(az), top[1] + L * math.sin(az), top[2] - 5.5)
            rod(m, top, p1, 0.75, "leaf", tone=0.3)
            rod(m, p1, p2, 0.95, ("leaf", "olive")[i % 2], tone=0.15)
            rod(m, p2, end, 0.6, ("leaf", "olive")[i % 2], tone=-0.1)
        if dates:
            for i in range(3):
                ellipsoid(m, (top[0] + math.cos(i * 2.1) * 1.3, top[1] + math.sin(i * 2.1) * 1.3, top[2] - 2.0),
                          (0.9, 0.9, 1.4), "orange", tone=0.1)
    if v == 0:
        palm(7.0, 7.0, 46.0, (2.0, 1.0), n=14, frond=13.0)
        palm(10.0, 10.0, 34.0, (-2.5, 2.0), n=13, frond=12.0)
        palm(6.0, 11.0, 24.0, (1.0, -2.0), n=11, frond=10.0)
        for (x, y) in ((11.5, 6.0), (4.5, 8.5)):          # offshoots
            for a in np.linspace(0, 2 * math.pi, 6, endpoint=False):
                rod(m, (x, y, 0.5), (x + 3.5 * math.cos(a), y + 3.5 * math.sin(a), 4.5), 0.4, "leaf", tone=0.2)
    else:
        palm(8.0, 8.0, 10.0, (0.5, 0.5), n=14, frond=13.0, dates=False)
    return m


def t_reeds(v, frame, frames, k):
    """A tall reed bed (Phragmites and giant reed) at a river margin or in a marsh, plumes on
    top, swaying in two frames; walkable, and it stands on land or water."""
    m = Model.empty(-3, 19, -3, 19, 0, 26, k=k)
    rng = Rng(5180, v)
    n = (20, 26, 16, 22)[v]
    for i in range(n):
        x, y = rng.uniform(1, 15), rng.uniform(1, 15)
        h = rng.uniform(13, 22)
        sway = (1.6 if frame else 0.0) + rng.uniform(-0.6, 0.6)
        rod(m, (x, y, 0.0), (x + sway, y + sway * 0.4, h), 0.25, ("olive", "grass", "summer")[i % 3],
            tone=rng.uniform(-0.2, 0.3))
        rod(m, (x + sway * 0.3, y, h * 0.4), (x + sway * 0.3 + rng.uniform(-2, 2), y + rng.uniform(-2, 2), h * 0.55), 0.2,
            "olive", tone=0.1)
        if i % 2 == 0:
            ellipsoid(m, (x + sway * 1.1, y + sway * 0.45, h + 1.0), (0.6, 0.6, 1.6), ("wood_light", "straw")[i % 4 // 2],
                      tone=0.15)
    return m


def p_maquis(v, frame, frames, k):
    """Evergreen scrub cushions: r0 kermes oak, r1 lentisk, r2 strawberry tree with red fruit,
    r3 broom in yellow flower."""
    rng = Rng(5190, v)
    m = _tree(k, 16, 4)
    mats = ((("leaf_dark", 0.7), ("olive", 0.3)), (("olive", 0.6), ("leaf_dark", 0.4)),
            (("leaf_dark", 0.6), ("leaf", 0.4)), (("grass", 0.5), ("olive", 0.5)))[v]
    clumps = [(8 + rng.uniform(-4, 4), 8 + rng.uniform(-4, 4), rng.uniform(4, 7), rng.uniform(3.0, 4.2)) for _ in range(4)]
    leaf_mass(m, clumps, 5191 + v, materials=mats, under="leaf_dark", cluster=(1.6, 2.2), squash=0.8, level=-0.4)
    if v in (2, 3):
        for i in range(14):
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(1, 6)
            ellipsoid(m, (8 + r * math.cos(a), 8 + r * math.sin(a), rng.uniform(5, 10)), (0.6, 0.6, 0.5),
                      "poppy" if v == 2 else "yellow", tone=0.3)
    return m


def p_thistle(v, frame, frames, k):
    """Spiny thistles with purple heads and grey camelthorn tufts of the steppe and fallow."""
    rng = Rng(5200, v)
    m = Model.empty(0, 16, 0, 16, 0, 10, k=k)
    for i in range(6 + 2 * v):
        x, y = rng.uniform(2, 14), rng.uniform(2, 14)
        if (i + v) % 3 == 2:        # camelthorn: a low grey-green spiky tuft
            for a in np.linspace(0, 2 * math.pi, 7, endpoint=False):
                rod(m, (x, y, 0), (x + 1.8 * math.cos(a), y + 1.8 * math.sin(a), 1.8), 0.22, "olive_silver", tone=0.1)
            continue
        h = rng.uniform(4.0, 7.0)
        rod(m, (x, y, 0), (x, y, h), 0.25, "olive_silver", tone=0.1)
        for a in np.linspace(0, 2 * math.pi, 4, endpoint=False):
            rod(m, (x, y, h * 0.4), (x + 1.4 * math.cos(a), y + 1.4 * math.sin(a), h * 0.3), 0.3, "olive_silver")
        ellipsoid(m, (x, y, h + 0.5), (0.8, 0.8, 0.8), "violet", tone=0.3)
    return m


FLOWERS = (
    (("poppy", 0.6), ("white_paint", 0.4)),         # r0 poppies and chamomile, Italy in April
    (("lapis", 0.5), ("yellow", 0.5)),              # r1 chicory and yellow composites, Greek summer
    (("poppy", 0.6), ("violet", 0.4)),              # r2 red tulips and irises, Zagros spring
    (("yellow", 0.6), ("white_paint", 0.4)),        # r3 small desert daisies, steppe spring
    (("white_paint", 0.5), ("violet", 0.5)),        # r4 sea squill and sea lavender, coasts
    (("cinnabar", 0.55), ("purple", 0.45)),         # r5 red anemones and grape hyacinths, Anatolia
)


def p_wildflowers(v, frame, frames, k):
    """Wildflowers scattered in the grass; worldgen picks the look by stretch (FLOWERS)."""
    rng = Rng(5210, v)
    m = Model.empty(0, 16, 0, 16, 0, 6, k=k)
    cols = FLOWERS[v]
    for i in range(16):
        x, y = rng.uniform(1.5, 14.5), rng.uniform(1.5, 14.5)
        u = rng.uniform()
        mat = cols[0][0] if u < cols[0][1] else cols[1][0]
        if v == 4 and mat == "white_paint":          # squill: a tall white spike
            rod(m, (x, y, 0), (x, y, 5.0), 0.25, "leaf")
            for z in (3.5, 4.2, 4.9):
                ellipsoid(m, (x, y, z), (0.45, 0.45, 0.4), mat, tone=0.3)
            continue
        h = rng.uniform(1.8, 3.6)
        rod(m, (x, y, 0), (x, y, h), 0.2, "leaf", tone=0.1)
        ellipsoid(m, (x, y, h + 0.3), (0.7, 0.7, 0.45), mat, tone=0.35)
    return m


def t_juniper(v, frame, frames, k):
    """A twisted juniper of the uplands: flaking red-brown bark, dense blue-green tufts."""
    rng = Rng(5220, v)
    m = _tree(k, 30, 10)
    pts = [(8 + math.sin(t * 3 + v) * 2.0, 8 + math.cos(t * 2.4 + v) * 1.6, t * 16.0) for t in np.linspace(0, 1, 7)]
    for a, b in zip(pts, pts[1:]):
        rod(m, a, b, 1.3, "rust", tone=lambda X, Y, Z: 0.4 * (np.sin(Z * 3.0 + X) > 0.5) - 0.2)
    clumps = [(p[0] + rng.uniform(-3, 3), p[1] + rng.uniform(-3, 3), p[2] + rng.uniform(2, 6), rng.uniform(2.6, 3.8))
              for p in pts[2:]]
    leaf_mass(m, clumps, 5221 + v, materials=(("leaf_dark", 0.6), ("olive", 0.4)), under="leaf_dark",
              cluster=(1.6, 2.2), squash=0.8, level=-0.7)
    return m


def t_cork_oak(v, frame, frames, k):
    """Cork oak of Latium and the islands: a thick corky trunk (r1 stripped, its lower part
    orange-red), a rounded dark evergreen crown."""
    rng = Rng(5230, v)
    m = _tree(k, 42, 14)
    rod(m, (8, 8, 0), (8, 8, 15.0), 2.4, "wood_grey", tone=lambda X, Y, Z: 0.5 * (value_noise(X, Y, Z, 0.9, 5231) > 0.6) - 0.2)
    if v == 1:
        fill(m, (4, 12, 4, 12, 0.0, 8.0), "orange", lambda X, Y, Z: np.hypot(X - 8, Y - 8) > 1.9, tone=-0.1, only_solid=True)
    for a in (0.6, 2.6, 4.5):
        rod(m, (8, 8, 13.0), (8 + 6 * math.cos(a), 8 + 6 * math.sin(a), 22.0), 1.1, "wood_grey")
    clumps = _crown(m, 8, 8, 25.0, 5, 6.0, 6.5, rng, (-2, 3)) + [(8, 8, 31.0, 6.5)]
    leaf_mass(m, clumps, 5232 + v, materials=(("leaf_dark", 0.75), ("olive", 0.25)), under="leaf_dark", level=-0.7)
    return m


def t_oleaster(v, frame, frames, k):
    """Wild olive: scrubby and many-stemmed, small silvery leaves."""
    rng = Rng(5240, v)
    m = _tree(k, 30, 11)
    clumps = []
    for i in range(4 + v):
        a = rng.uniform(0, 2 * math.pi)
        top = (8 + 4.5 * math.cos(a), 8 + 4.5 * math.sin(a), rng.uniform(10, 15))
        rod(m, (8 + math.cos(a), 8 + math.sin(a), 0), top, 0.7, "bark")
        clumps.append((*top, rng.uniform(3.4, 4.4)))
    leaf_mass(m, clumps, 5241 + v, materials=(("olive", 0.6), ("olive_silver", 0.4)), under="olive",
              cluster=(1.8, 2.4), level=-0.85)
    return m


# ---------------------------------------------------------------- rock

ROCKS = ("attic_rock", "stone", "rust", "basalt")


def _rock(m, box, top, material, seed, stains=None, beds=True):
    """Natural rock under the height field `top(X, Y)`, shaded from the field's normals, with
    faint bedding and darker cracks."""
    def tone(X, Y, Z):
        n = (value_noise(X, Y, Z, 3.0, seed) - 0.5) * 1.0
        strata = 0.35 * (np.sin(Z * 0.9 + value_noise(X, Y, Z, 12.0, seed + 1) * 5) > 0.6) if beds else 0.0
        crack = -0.8 * (np.abs(value_noise(X, Y, Z, 5.0, seed + 2) - 0.5) < 0.03)
        return n + strata + crack
    field_fill(m, box, lambda X, Y, Z: Z - top(X, Y), material, tone=tone)
    if stains:
        fill(m, box, stains, lambda X, Y, Z: value_noise(X * 0.7, Y * 0.7, Z * 1.5, 5.0, seed + 5) > 0.76,
             tone=0.0, only_solid=True)


def boulder(v, frame, frames, k):
    """A boulder: r0 and r1 grey limestone, r2 red sandstone, r3 dark basalt; lichen on top."""
    rng = Rng(5300, v)
    m = Model.empty(-1, 17, -1, 17, 0, 12, k=k)
    cx, cy = 8 + rng.uniform(-1, 1), 8 + rng.uniform(-1, 1)
    ax, ay, h = rng.uniform(4.5, 6.5), rng.uniform(3.5, 5.5), (8.5, 6.0, 7.0, 8.0)[v]

    def top(X, Y):
        r = np.hypot((X - cx) / ax, (Y - cy) / ay)
        return h * np.clip(1 - r ** 2.2, 0, 1) ** 0.6 + (value_noise(X, Y, X * 0, 2.0, 5301 + v) - 0.5) * 2.0
    _rock(m, (0, 16, 0, 16, 0, 12), top, ("attic_rock", "attic_rock", "rust", "basalt")[v], 5302 + v,
          stains="olive" if v != 2 else None, beds=v != 3)
    return m


def crag(v, frame, frames, k):
    """A 2 x 2 rock tor: piled weathered blocks, a shrub in a cleft. Breaks up mountain flats and
    frames passes."""
    rng = Rng(5310, v)
    m = Model.empty(-2, 34, -2, 34, 0, 30, k=k)
    blobs = [(16 + rng.uniform(-6, 6), 16 + rng.uniform(-6, 6), rng.uniform(5, 9), rng.uniform(14, 24)) for _ in range(4)]

    def top(X, Y):
        out = np.zeros_like(X)
        for bx, by, r, h in blobs:
            d = np.hypot(X - bx, Y - by) / (r * 1.4)
            out = np.maximum(out, h * np.clip(1 - d ** 2.4, 0, 1) ** 0.5)
        return out + (value_noise(X, Y, X * 0, 2.5, 5311 + v) - 0.5) * 3.0
    _rock(m, (0, 32, 0, 32, 0, 30), top, ("attic_rock", "stone", "attic_rock")[v], 5312 + v, stains="olive")
    bx, by, r, h = blobs[0]
    leaf_mass(m, [(bx + r, by, float(top(np.array(bx + r), np.array(by))) + 2.0, 3.0)], 5313 + v,
              materials=(("leaf_dark", 0.6), ("olive", 0.4)), under="leaf_dark", cluster=(1.6, 2.2), level=-0.6)
    return m


def peak(v, frame, frames, k):
    """A 3 x 3 summit standing on the highest level: r0 a limestone horn with snow streaks in
    its gullies, r1 a broad snow dome with rock ribs, r2 a volcanic cone with a crater lip and
    dark ash slopes (Vesuvius after AD 79, Etna, Argaios)."""
    m = Model.empty(-2, 50, -2, 50, 0, 70, k=k)
    c = 24.0
    if v == 0:
        def top(X, Y):
            # A horn of ribs and gullies: height falls off from an off-centre summit, cut by
            # radial gullies and roughened at every scale, so it never reads as a cone.
            r = np.hypot(X - c - 3.0 - (Y - c) * 0.15, Y - c + 2.0) / 23.0
            a = np.arctan2(Y - c, X - c)
            gully = 0.5 + 0.5 * np.sin(a * 6.0 + value_noise(X, Y, X * 0, 5.0, 5324) * 5.0)
            rough = (value_noise(X, Y, X * 0, 6.0, 5321) - 0.5) * 12.0 + (value_noise(X, Y, X * 0, 2.0, 5325) - 0.5) * 4.0
            base = 66.0 * np.clip(1 - r, 0, 1) ** 1.6
            return base * (0.78 + 0.22 * gully) + rough * np.clip(1 - r, 0, 1) ** 0.6
        _rock(m, (0, 48, 0, 48, 0, 70), top, "attic_rock", 5322)
        X, Y, Z = m.coords()
        from palette import MAT
        rock = m.mat == MAT["attic_rock"]
        gully = value_noise(X, Y, Z * 0.3, 4.0, 5323) > 0.6
        m.put(rock & (gully | (m.nrm[..., 2] > 0.75)) & (Z > 22) & (m.nrm[..., 2] > 0.25), "snow", tone=0.2)
    elif v == 1:
        def top(X, Y):
            r = np.hypot(X - c, Y - c) / 23.5
            return 52.0 * np.clip(1 - r * r, 0, 1) ** 0.9 + (value_noise(X, Y, X * 0, 5.0, 5331) - 0.5) * 5.0
        _rock(m, (0, 48, 0, 48, 0, 70), top, "stone", 5332, beds=False)
        X, Y, Z = m.coords()
        from palette import MAT
        rib = np.abs(value_noise(X, Y, Z * 0, 7.0, 5333) - 0.5) < 0.06
        m.put((m.mat == MAT["stone"]) & ~rib & (Z > 12 + 6 * value_noise(X, Y, Z * 0, 5.0, 5334)), "snow", tone=0.3)
    else:
        def top(X, Y):
            r = np.hypot(X - c, Y - c) / 23.5
            cone = 60.0 * np.clip(1 - r, 0, 1) ** 1.1
            crater = np.clip(1 - r / 0.22, 0, 1) * 16.0
            return cone - crater + (value_noise(X, Y, X * 0, 4.0, 5341) - 0.5) * 3.0
        _rock(m, (0, 48, 0, 48, 0, 70), top, "basalt", 5342, beds=False)
        X, Y, Z = m.coords()
        from palette import MAT
        ash = (m.mat == MAT["basalt"]) & (Z < 30) & (value_noise(X, Y, Z, 3.0, 5343) > 0.45)
        m.put(ash, "stone", tone=-0.3)
        m.put((m.mat == MAT["basalt"]) & (Z > 40) & (np.hypot(X - c, Y - c) < 7.5) & (np.hypot(X - c, Y - c) > 4.5),
              "rust", tone=0.1)
    return m


def driftwood(v, frame, frames, k):
    """Bleached logs washed up on the sand."""
    rng = Rng(5350, v)
    m = Model.empty(-1, 17, -1, 17, 0, 5, k=k)
    for i in range(2 + v):
        a = rng.uniform(0, math.pi)
        x, y, L = rng.uniform(5, 11), rng.uniform(5, 11), rng.uniform(5, 9)
        rod(m, (x - L / 2 * math.cos(a), y - L / 2 * math.sin(a), 0.8), (x + L / 2 * math.cos(a), y + L / 2 * math.sin(a), 0.8),
            rng.uniform(0.6, 0.9), "wood_grey", tone=0.3)
        rod(m, (x, y, 0.8), (x + 2.5 * math.cos(a + 1.2), y + 2.5 * math.sin(a + 1.2), 1.6), 0.35, "wood_grey", tone=0.2)
    return m


ITEMS = {f"world.{n}": Item(fn) for n, fn in (
    ("t_oak", t_oak), ("t_oak_zagros", t_oak_zagros), ("t_beech", t_beech), ("t_fir", t_fir), ("t_cedar", t_cedar),
    ("t_pistachio", t_pistachio), ("t_tamarisk", t_tamarisk), ("t_palm", t_palm), ("t_reeds", t_reeds),
    ("p_maquis", p_maquis), ("p_thistle", p_thistle), ("p_wildflowers", p_wildflowers), ("t_juniper", t_juniper),
    ("t_cork_oak", t_cork_oak), ("t_oleaster", t_oleaster), ("boulder", boulder), ("crag", crag), ("peak", peak),
    ("driftwood", driftwood))}

FRAMES = {"world.t_reeds": 2}
