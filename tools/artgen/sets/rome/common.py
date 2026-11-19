"""Shared pieces of the Rome landmarks: the bible's scales (rome.md §2.1), tile helpers, the
orders of the great buildings in metres, statues on the rig, Roman trees (stone pine, cypress,
plane, laurel), paving, lamps, cranes and building-site gear."""

import math

import numpy as np

import materials as M
from arch import Scale, fill, halo, rod, slab
from models.nature import leaf_mass
from rig import Dress
from roman import ROrder
from sets.athens.common import cypress, olive_tree, scaffold  # noqa: F401  (shared trees and scaffolding)
from voxel import Rng, hash01, value_noise

T = 16                      # design units per tile
LAMP = (255, 201, 92)
FIRE = (255, 154, 58)

# rome.md §2.1: monuments s = 0.65, the imperial fora 0.5, the Colosseum 0.6, the Theatre of
# Marcellus 0.5, the very largest complexes 0.33-0.4, waypoint landmarks about 0.45.
S65, S6, S5, S4, S35, S33, S45 = (Scale(v) for v in (0.65, 0.6, 0.5, 0.4, 0.35, 0.33, 0.45))

# Orders (metres): Pantheon porch (granite shafts 11.9 m, white marble Corinthian capitals and
# bases, 14.15 m with them), Castor (14.8 m fluted white marble), Saturn (Ionic, 11 m, grey and
# pink granite shafts), Mars Ultor (17.7 m), Trajan's Forum colonnades (pavonazzetto shafts).
PANTHEON_GREY = ROrder("corinthian", D=1.48, H=14.15, shaft="granite", trim="marble", fluted=False)
PANTHEON_PINK = ROrder("corinthian", D=1.48, H=14.15, shaft="granite_pink", trim="marble", fluted=False)
CASTOR = ROrder("corinthian", D=1.45, H=14.8)
SATURN = ROrder("ionic", D=1.43, H=11.0, shaft="granite", trim="marble", fluted=False)
MARS = ROrder("corinthian", D=1.76, H=17.7)
CAPITOLINE = ROrder("corinthian", D=1.9, H=16.0, gilt=True)
TEMPLE = ROrder("corinthian", D=1.2, H=11.5)
SMALL = ROrder("corinthian", D=0.9, H=8.5)
PORTICO = ROrder("corinthian", D=0.8, H=7.0, shaft="cipollino")
PAVONAZZETTO = ROrder("corinthian", D=0.95, H=8.9, shaft="marble", trim="marble")
GIALLO = ROrder("corinthian", D=1.0, H=9.0, shaft="giallo", trim="marble", fluted=False)
TUSCAN = ROrder("tuscan", D=0.9, H=6.5, shaft="travertine", trim="travertine", fluted=False)
IONIC = ROrder("ionic", D=0.9, H=7.5)


def tc(d):
    """Centre of tile row/column d (design units)."""
    return d * T + T / 2


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def referrer(module):
    def ref(fn, **kw):
        return (module, fn, tuple(sorted(kw.items())))
    return ref


# ---------------------------------------------------------------- people as statues

TOGATE = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="short", beard="short", garment="toga",
               colour="linen", feet="shoes")
ARMOURED = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="curly", beard="short", garment="tunic",
                 colour="cinnabar", worn=("cuirass",), cape="purple", feet="boots", hand_l="spear")
GODDESS = Dress(body="woman", skin="skin_tan", hair="cedar", hair_style="knot", beard="none", garment="chiton_long",
                colour="linen", mantle="linen", feet="shoes")
VESTAL = Dress(body="woman", skin="skin_tan", hair="cedar", hair_style="braids", beard="none", garment="stola",
               colour="whitewash", under="whitewash", head="suffibulum", head_mat="whitewash", head_trim="cinnabar",
               feet="shoes")
SUN_GOD = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="curly", beard="none", garment="none",
                head="radiate", head_mat="gold", feet="bare", hand_l="staff")


# ---------------------------------------------------------------- trees

def stone_pine(m, x, y, z, h=44.0, seed=0, lean=None):
    """The umbrella pine: a tall bare trunk with a slight lean and a reddish scaly bark, forking
    high into a flat-topped dome of dark green needle clouds."""
    rng = Rng(1300, seed)
    lx, ly = lean if lean is not None else (rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0))
    top = (x + lx, y + ly, z + h * 0.68)
    rod(m, (x, y, z), top, 1.3, "bark", tone=lambda X, Y, Z: 0.3 * (hash01(np.floor(Z * 1.5).astype(np.int64), 3) > 0.6))
    clumps = []
    for i in range(6):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(3.0, 8.0) * h / 44.0
        bx, by = top[0] + r * math.cos(a), top[1] + r * math.sin(a)
        rod(m, top, (bx, by, z + h * 0.82), 0.6, "bark")
        clumps.append((bx, by, z + h * rng.uniform(0.84, 0.92), rng.uniform(5.0, 6.6) * h / 44.0))
    clumps.append((top[0], top[1], z + h * 0.93, 6.0 * h / 44.0))
    leaf_mass(m, clumps, 1301 + seed, materials=(("leaf_dark", 0.75), ("leaf", 0.25)), under="leaf_dark",
              cluster=(2.4, 3.2), squash=0.42, level=-0.7)


def plane_tree(m, x, y, z, h=46.0, seed=0):
    """A plane shading a portico or garden: pale mottled trunk, broad rounded crown."""
    rng = Rng(1310, seed)
    rod(m, (x, y, z), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), z + h * 0.55), 1.8, "wood_grey", tone=0.1)
    clumps = [(x + 7.0 * math.cos(a), y + 7.0 * math.sin(a), z + h * rng.uniform(0.7, 0.82), rng.uniform(5.5, 7.0))
              for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)] + [(x, y, z + h * 0.9, 7.0)]
    leaf_mass(m, clumps, 1311 + seed, materials=(("leaf", 0.7), ("grass", 0.3)), under="leaf_dark", level=-0.6)


def laurel(m, x, y, z, h=18.0, seed=0):
    rng = Rng(1320, seed)
    rod(m, (x, y, z), (x, y, z + h * 0.3), 0.6, "bark")
    clumps = [(x + rng.uniform(-2, 2), y + rng.uniform(-2, 2), z + h * rng.uniform(0.45, 0.8), rng.uniform(3.0, 4.2))
              for _ in range(4)]
    leaf_mass(m, clumps, 1321 + seed, materials=(("leaf_dark", 0.6), ("leaf", 0.4)), under="leaf_dark",
              cluster=(1.8, 2.4), level=-0.6)


def box_hedge(m, x0, x1, y0, y1, z, h=2.5):
    fill(m, (x0, x1, y0, y1, z, z + h), "leaf_dark",
         tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z * 2, 1.2, 7) - 0.5) * 1.2 + 0.4 * (Z > z + h - 0.6))


# ---------------------------------------------------------------- ground, lamps, site gear

def lawn(seed):
    """The tone of a landmark's lawn: broad patches of lusher and drier grass, tufts with lit
    tops and dark hollows, and a blade-fine speckle, so a lawn of many tiles is never one flat
    colour (V7-010: a broad noise alone quantised to a single step)."""
    def tone(X, Y, Z):
        broad = (value_noise(X, Y, Z * 0, 9.0, seed) - 0.5) * 0.9
        tuft = value_noise(X, Y, Z * 0, 1.1, seed + 1)
        blade = hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), seed + 2) - 0.5
        return broad + 0.7 * (tuft > 0.68) - 0.6 * (tuft < 0.22) + 0.8 * blade
    return tone


def paving(m, box, z0, z1, material="travertine", slab_x=6.0, slab_y=4.5, seed=11):
    fill(m, (*box, z0, z1), material, tone=M.paving(slab_x, slab_y, seed))


def basalt_road(m, box, z0, z1, seed=13):
    """Polygonal basalt paving: irregular grey-black blocks with pale joints."""
    def tone(X, Y, Z):
        cell = np.floor(X / 2.6 + 0.4 * np.sin(Y * 0.9)).astype(np.int64)
        row = np.floor(Y / 2.6 + 0.4 * np.sin(X * 0.8)).astype(np.int64)
        jn = ((X / 2.6 + 0.4 * np.sin(Y * 0.9)) % 1.0 < 0.12) | ((Y / 2.6 + 0.4 * np.sin(X * 0.8)) % 1.0 < 0.12)
        return (hash01(cell, row, seed) - 0.5) * 0.8 + 1.2 * jn
    fill(m, (*box, z0, z1), "basalt", tone=tone)


def lamp(m, x, y, z, strength=0.7, r=8.0):
    fill(m, (x - 0.6, x + 0.6, y - 0.6, y + 0.6, z, z + 1.0), "lamp")
    halo(m, x, y, z + 0.5, r, LAMP, strength)


def torch(m, x, y, z, h=6.0, strength=0.9):
    rod(m, (x, y, z), (x, y, z + h), 0.35, "wood")
    fill(m, (x - 0.7, x + 0.7, y - 0.7, y + 0.7, z + h, z + h + 1.6), "fire")
    halo(m, x, y, z + h + 1.0, 12.0, FIRE, strength)


def treadwheel_crane(m, x, y, z, h, along="y", load="marble", swing=0.0):
    """A Roman treadwheel crane (polyspastos): two tall jib legs leaning over the work, guyed
    back, a great wheel at the foot walked by men, the rope over a block at the top."""
    fx, fy = (0.0, 1.0) if along == "y" else (1.0, 0.0)
    px, py = fy, fx
    top = (x + fx * h * 0.28 + swing, y + fy * h * 0.28, z + h)
    for s in (-1, 1):
        rod(m, (x + px * s * 3.0, y + py * s * 3.0, z), top, 0.55, "wood", tone=0.1)
    rod(m, top, (x - fx * h * 0.45, y - fy * h * 0.45, z), 0.18, "straw", tone=0.2)
    wr = h * 0.17
    wx, wy = x - fx * 4.0, y - fy * 4.0

    def wheel(X, Y, Z):
        a = (X - wx) * fx + (Y - wy) * fy
        b = (X - wx) * px + (Y - wy) * py
        rr = np.hypot(a, Z - (z + wr + 0.5))
        rim = (np.abs(rr - wr) < 0.55) | ((rr < wr) & (np.abs(np.sin(np.arctan2(Z - z - wr, a) * 4)) < 0.12))
        return rim & (np.abs(b) < 2.4)
    fill(m, (wx - wr - 3, wx + wr + 3, wy - wr - 3, wy + wr + 3, z, z + 2 * wr + 1.5), "wood_light", wheel,
         tone=lambda X, Y, Z: 0.1)
    rod(m, top, (top[0], top[1], z + h * 0.35), 0.15, "straw", tone=0.3)
    if load:
        bz = z + h * 0.35
        slab(m, top[0] - 2.4, top[0] + 2.4, top[1] - 1.6, top[1] + 1.6, bz - 3.2, bz, load, tone=0.2)


def drums(m, x, y, z, r, n, seed=0, material="marble", along="y"):
    """A row of column drums lying on the ground."""
    from sets.athens.common import drum
    for i in range(n):
        o = i * (2 * r + 1.2)
        drum(m, x + (o if along == "x" else 0.0), y + (o if along == "y" else 0.0), z, r, r * 1.6, lying=True,
             material=material, along="x" if along == "y" else "y")
