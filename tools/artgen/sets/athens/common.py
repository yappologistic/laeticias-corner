"""Shared pieces of the Athens landmarks: scale, tile helpers, statues on the rig, olive trees,
stacks of blocks, cranes and scaffolds, altars and fires, lifting bosses, gravel and paving."""

import math
import numpy as np

import materials as M
from arch import Scale, ellipsoid, face_box, face_frame, face_length, fill, halo, rod, slab
from greek import paste, statue_model
from models.nature import leaf_mass
from rig import Dress
from voxel import Rng, hash01, value_noise

S = Scale(1.0)
T = 16                                   # design units per tile
LAMP = (255, 201, 92)
FIRE = (255, 154, 58)


def tc(d):
    """Centre of tile row/column d (design units)."""
    return d * T + T / 2


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def referrer(module):
    def ref(fn, **kw):
        return (module, fn, tuple(sorted(kw.items())))
    return ref


# ---------------------------------------------------------------- statues

ATHENA = Dress(body="woman", skin="skin_tan", hair="cedar", hair_style="long", beard="none", garment="peplos",
               colour="saffron", head="attic_helmet", head_mat="bronze", head_trim="gold", shawl="gold",
               hand_l="aspis", hand_r="dory", pattern_mat="bronze", trim="gold", feet="shoes")


def bronze_statue(m, dress, x, y, z, height, anim="idle", frame=0, keep=("gold", "metal"), turns=0,
                  material="bronze_cast"):
    """A statue `height` design units tall standing on (x, y, z), cast from a rig dress."""
    from rig import BODIES
    scale = height / BODIES[dress.body][0]
    sub = statue_model(dress, round(scale, 3), 2, material, keep, anim, frame, turns)
    paste(m, sub, x, y, z)


# ---------------------------------------------------------------- plants

def olive_tree(m, x, y, z, h=24.0, seed=0, spread=1.0, gnarled=1.0):
    """An olive: a short, twisted, hollowed trunk splitting into crooked limbs, a broad
    rounded crown of silver-green leaf clusters in loose clumps with sky between them."""
    rng = Rng(900, seed)
    lean = (rng.uniform(-1.5, 1.5) * gnarled, rng.uniform(-1.5, 1.5) * gnarled)
    tr = 1.7 * spread
    # The trunk in twisted strands, darker in the furrows.
    for i in range(3):
        a = i * 2.1 + rng.uniform(0, 1)
        ox, oy = math.cos(a) * tr * 0.45, math.sin(a) * tr * 0.45
        rod(m, (x + ox, y + oy, z), (x + ox * 0.4 + lean[0], y + oy * 0.4 + lean[1], z + h * 0.38), tr * 0.55, "bark",
            tone=-0.1 * i)
    limbs = []
    for i in range(4):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(3.0, 6.0) * spread
        top = (x + lean[0] + math.cos(a) * r, y + lean[1] + math.sin(a) * r, z + h * rng.uniform(0.55, 0.72))
        rod(m, (x + lean[0], y + lean[1], z + h * 0.36), top, tr * 0.32, "bark", tone=0.1)
        limbs.append(top)
    clumps = [(lx + rng.uniform(-1, 1), ly + rng.uniform(-1, 1), lz + rng.uniform(1.0, 3.0), rng.uniform(3.4, 4.6) * spread)
              for lx, ly, lz in limbs]
    clumps.append((x + lean[0], y + lean[1], z + h * 0.82, 4.4 * spread))
    leaf_mass(m, clumps, 901 + seed, materials=(("olive", 0.65), ("olive_silver", 0.35)), under="olive",
              cluster=(2.2, 3.0), squash=0.8, level=-0.5)


def cypress(m, x, y, z, h=40.0, seed=0):
    rng = Rng(910, seed)
    rod(m, (x, y, z), (x, y, z + 6.0), 0.9, "bark")
    clumps = []
    for i in range(9):
        t = i / 8
        clumps.append((x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.4, 0.4), z + 5.0 + t * (h - 8.0),
                       3.0 * (1 - t) ** 0.6 + 0.9))
    leaf_mass(m, clumps, 911 + seed, materials=(("leaf_dark", 1.0),), under="leaf_dark", cluster=(1.6, 2.4),
              squash=1.3, level=-1.1)


# ---------------------------------------------------------------- building site gear

def blocks(m, x, y, z, n, seed, material="marble", size=(6.0, 4.0, 3.0), bosses=True):
    """A stack or row of squared blocks with lifting bosses and quarry-rough faces."""
    rng = Rng(920, seed)
    zz = z
    for i in range(n):
        w, d, h = (s * rng.uniform(0.8, 1.2) for s in size)
        ox, oy = rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)
        slab(m, x + ox, x + ox + w, y + oy, y + oy + d, zz, zz + h, material,
             tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z * 2, 1.5, seed + i) - 0.5) * 0.7 + 0.3 * (Z > zz + h - 0.5))
        if bosses:
            bx, by = x + ox + w / 2, y + oy + d
            slab(m, bx - 0.7, bx + 0.7, by - 0.1, by + 0.7, zz + h * 0.35, zz + h * 0.75, material, tone=0.1)
        zz += h


def drum(m, x, y, z, r, h, lying=False, material="marble", along="y"):
    if lying:
        a = (x, y - h / 2, z + r) if along == "y" else (x - h / 2, y, z + r)
        b = (x, y + h / 2, z + r) if along == "y" else (x + h / 2, y, z + r)
        rod(m, a, b, r, material, tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 7) - 0.5) * 0.4)
    else:
        fill(m, (x - r, x + r, y - r, y + r, z, z + h), material, lambda X, Y, Z: np.hypot(X - x, Y - y) <= r,
             tone=lambda X, Y, Z: 0.3 * (Z > z + h - 0.5) + (value_noise(X, Y, Z, 2.0, 9) - 0.5) * 0.3)


def crane(m, x, y, z, h, along="y", load=True, swing=0.0):
    """A two-legged crane (shear legs) leaning over the work, guyed back, with a winch at the
    foot of the legs and a block slung from the pulley."""
    sx, sy = (0.0, 3.5) if along == "y" else (3.5, 0.0)
    lean = (5.0, 0.0) if along == "y" else (0.0, 5.0)
    top = (x + lean[0] + swing, y + lean[1], z + h)
    for s in (-1, 1):
        rod(m, (x + s * sx, y + s * sy, z), top, 0.55, "wood", tone=0.1)
    rod(m, top, (x - lean[0] * 1.6, y - lean[1] * 1.6, z), 0.18, "straw", tone=0.2)       # the guy rope
    rod(m, (x - sx * 0.8 - 1.0, y - sy * 0.8 - 1.0, z + 2.6), (x + sx * 0.8 + 1.0, y + sy * 0.8 + 1.0, z + 2.6), 0.7,
        "wood", tone=0.2)                                                                  # the winch drum
    rod(m, top, (top[0], top[1], z + h * 0.35), 0.16, "straw", tone=0.3)
    if load:
        bz = z + h * 0.35
        slab(m, top[0] - 2.4, top[0] + 2.4, top[1] - 1.6, top[1] + 1.6, bz - 3.2, bz, "marble", tone=0.2)


POLE = 0.55        # scaffold poles: thick enough to draw at 64x32 (thinner ones vanish and the decks float)


def scaffold(m, x0, x1, y0, y1, z0, z1, decks=2):
    """Scaffolding of lashed poles standing on the ground, ledgers round each deck, a plank
    walkway along the long side and a diagonal brace."""
    for x in (x0, x1):
        for y in (y0, y1):
            rod(m, (x, y, z0), (x, y, z1), POLE, "wood_light", tone=0.1)
    along_x = x1 - x0 >= y1 - y0
    for i in range(1, decks + 1):
        zz = z0 + (z1 - z0) * i / (decks + 0.3)
        for a, b in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
            rod(m, (*a, zz), (*b, zz), 0.35, "wood", tone=0.2)
        if along_x:
            slab(m, x0, x1, y1 - (y1 - y0) * 0.45, y1, zz, zz + 0.6, "wood_light", tone=M.timber("x", 3))
        else:
            slab(m, x1 - (x1 - x0) * 0.45, x1, y0, y1, zz, zz + 0.6, "wood_light", tone=M.timber("y", 3))
        rod(m, (x0, y0, zz - 3), (x1, y1, zz), 0.35, "wood", tone=0.0)


def bosses(m, face, wall, z0, z1, seed, material="marble", share=0.35, course=2.8, block=7.0):
    """Lifting bosses left on wall blocks (the unfinished Propylaia): small square lugs proud of
    the face at the middle of the lower edge of some blocks."""
    x0, x1, y0, y1 = wall[:4]
    L = face_length(face, x0, x1, y0, y1)

    def mask(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        row = np.floor((Z - z0) / course).astype(np.int64)
        col = np.floor((s + (row % 2) * block * 0.5) / block).astype(np.int64)
        u = (s + (row % 2) * block * 0.5) % block - block / 2
        v = (Z - z0) % course
        return (np.abs(u) < 0.75) & (v > 0.5) & (v < 1.6) & (hash01(row, col, seed) < share) & (d > -0.9)
    fill(m, face_box(face, x0, x1, y0, y1, z0, z1, 0, L, -0.9, 0.05), material, mask, tone=0.15)


# ---------------------------------------------------------------- altars, fires, ground

def altar(m, x, y, z, w, d, h, fire=True, material="marble", steps=True):
    """A stone altar on a stepped base, its top fire-blackened, a fire burning on it."""
    if steps:
        slab(m, x - w / 2 - 2.0, x + w / 2 + 2.0, y - d / 2 - 2.0, y + d / 2 + 2.0, z, z + 1.4, material,
             tone=M.ashlar(1.4, 5.0, 3, spread=0.3))
        z += 1.4
    slab(m, x - w / 2, x + w / 2, y - d / 2, y + d / 2, z, z + h, material, tone=M.ashlar(2.4, 6.0, 5, spread=0.3))
    slab(m, x - w / 2 - 0.6, x + w / 2 + 0.6, y - d / 2 - 0.6, y + d / 2 + 0.6, z + h, z + h + 0.9, material, tone=0.3)
    fill(m, (x - w / 2, x + w / 2, y - d / 2, y + d / 2, z + h + 0.9, z + h + 1.4), "ink",
         lambda X, Y, Z: np.hypot((X - x) / (w / 2), (Y - y) / (d / 2)) < 0.85, tone=0.0)
    if fire:
        for i in range(5):
            a = i * 1.26
            fx, fy = x + math.cos(a) * w * 0.15, y + math.sin(a) * d * 0.15
            ellipsoid(m, (fx, fy, z + h + 2.0), (1.0, 1.0, 1.8), "fire", tone=0.2 * (i % 2))
        ellipsoid(m, (x, y, z + h + 1.8), (w * 0.25, d * 0.25, 0.8), "ember", tone=0.0)
        halo(m, x, y, z + h + 3.0, 16.0, FIRE, 0.9)
    return z + h + 1.4


def paving(m, x0, x1, y0, y1, z0, z1, material="marble", seed=11, slab_x=7.0, slab_y=5.0):
    fill(m, (x0, x1, y0, y1, z0, z1), material, tone=M.paving(slab_x, slab_y, seed))


def rock_field(m, box, top, material="attic_rock", seed=3, stains=True):
    """Natural rock below the height field `top(X, Y)`: weathered, bedded, with rusty stains."""
    from arch import field_fill

    def tone(X, Y, Z):
        n = (value_noise(X, Y, Z, 4.0, seed) - 0.5) * 1.1
        strata = 0.3 * (np.sin(Z * 0.8 + value_noise(X, Y, Z, 18.0, seed + 1) * 5) > 0.6)
        return n + strata - 0.1
    field_fill(m, box, lambda X, Y, Z: Z - top(X, Y), material, tone=tone)
    if stains:
        fill(m, box, "rust", lambda X, Y, Z: (value_noise(X * 0.7, Y * 0.7, Z * 1.5, 6.0, seed + 5) > 0.74),
             tone=0.0, only_solid=True)


def lamp_niche(m, x, y, z, strength=0.6):
    fill(m, (x - 0.7, x + 0.7, y - 0.7, y + 0.7, z, z + 1.2), "lamp")
    halo(m, x, y, z + 0.6, 7.0, LAMP, strength)
