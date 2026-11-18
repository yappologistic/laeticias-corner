"""Piraeus and the Pentelikon quarries (athens.md §2.3 S1-S2, §3.2), and the Greek-time
waypoints of Attica (§3.7): the Zea ship sheds with triremes hauled up, the Kantharos quay
with its emporion stoa and harbour tower, the marble quarry on Pentelikon, the Telesterion at
Eleusis under construction, and the Academy's grove."""


import numpy as np

import materials as M
from arch import Scale, carve, ellipsoid, field_fill, fill, halo, rod, slab
from greek import Order, Stoa, column, house_wall, poros_wall, stoa, tiled_roof, vase
from setbuild import Landmark
from sets.athens.common import FIRE, S, T, altar, crane, lamp_niche, olive_tree, referrer, scaffold, tiles
from voxel import Rng, hash01, value_noise

ref = referrer("sets.athens.piraeus")
S05 = Scale(0.5)


def hull(m, x0, x1, yc, z0, beam=5.0, depth=4.5, kind="trireme", seed=0):
    """A trireme's hull lying along x, bow toward +x: black with pitch, a bronze ram at the
    waterline, the painted eye on the bow, an outrigger (parexeiresia) with three banks of oar
    ports, a curved stern ornament (aphlaston)."""
    L = x1 - x0

    def half(X):
        t = np.clip((X - x0) / L, 0, 1)
        return beam * np.clip(np.sin(np.pi * np.clip(t * 1.08, 0, 1)) ** 0.5, 0.15, 1.0)

    def keel(X, Y):
        return z0 + depth * 0.15 * ((np.abs(Y - yc) / beam) ** 2)

    fill(m, (x0, x1, yc - beam - 1.5, yc + beam + 1.5, z0, z0 + depth + 1.0), "pitch",
         lambda X, Y, Z: (np.abs(Y - yc) < half(X)) & (Z >= keel(X, Y)) & (Z < z0 + depth),
         tone=lambda X, Y, Z: 0.3 * (Z > z0 + depth - 0.6) - 0.2)
    # The outrigger box with three rows of oar ports.
    fill(m, (x0 + L * 0.18, x0 + L * 0.82, yc - beam - 1.4, yc + beam + 1.4, z0 + depth - 1.6, z0 + depth + 0.4),
         "wood", lambda X, Y, Z: np.abs(Y - yc) > beam - 0.4, tone=lambda X, Y, Z: -0.6 * ((X % 1.6) < 0.5) *
         (np.abs(Z - (z0 + depth - 0.8)) < 0.4))
    fill(m, (x0 + L * 0.15, x0 + L * 0.85, yc - beam - 0.2, yc + beam + 0.2, z0 + 1.0, z0 + depth - 1.6), "ink",
         lambda X, Y, Z: (np.abs(np.abs(Y - yc) - half(X)) < 0.6) & (((X % 1.6) < 0.5)) &
         ((np.abs(Z - (z0 + 1.6)) < 0.35) | (np.abs(Z - (z0 + 2.6)) < 0.35)), tone=0.0, only_solid=True)
    # Bronze ram, painted eyes, deck rails, the stern's curved aphlaston.
    rod(m, (x1 - 2.0, yc, z0 + 0.8), (x1 + 2.5, yc, z0 + 0.8), 0.9, "bronze", tone=0.3)
    for s in (-1, 1):
        ellipsoid(m, (x1 - 3.5, yc + s * (beam * 0.45), z0 + depth - 1.2), (0.8, 0.5, 0.6), "whitewash", tone=0.3)
        fill(m, (x1 - 4.0, x1 - 3.0, yc + s * beam * 0.45 - 0.4, yc + s * beam * 0.45 + 0.4, z0 + depth - 1.5,
                 z0 + depth - 0.9), "gloss", tone=0.0)
        fill(m, (x0 + L * 0.1, x1 - 4.0, yc + s * (beam - 0.5) - 0.3, yc + s * (beam - 0.5) + 0.3, z0 + depth,
                 z0 + depth + 0.7), "cinnabar", tone=0.1)
    rod(m, (x0 + 1.0, yc, z0 + depth), (x0 - 1.5, yc, z0 + depth + 4.0), 0.6, "pitch", tone=0.2)
    rod(m, (x0 - 1.5, yc, z0 + depth + 4.0), (x0 + 0.5, yc, z0 + depth + 6.0), 0.5, "pitch", tone=0.2)


def shipsheds(m):
    """The ship sheds of Zea (s = 0.5): a row of long, narrow roofed slipways sloping down
    southward into the water, divided by rows of poros columns that carry the gabled roofs;
    triremes hauled up in most of them, stern first, their masts and oars stored apart."""
    seed = 501
    W, Lh = 6 * T, 16 * T
    rise = 5.0

    def floor(X):
        return np.clip((W - X) / W, 0, 1) * rise
    fill(m, (0.0, W, 0.0, Lh, 0.0, rise + 1.0), "poros", lambda X, Y, Z: Z < floor(X),
         tone=M.ashlar(2.0, 6.0, seed, spread=0.5))
    poros_wall(m, 0.0, 3.0, 0.0, Lh, 0.0, 24.0, seed + 1)
    o = Order("doric", D=0.8, H=6.0, upper=0.85, material="poros")
    for k in range(17):
        y = k * T
        for x in np.arange(10.0, W, 14.0):
            fill(m, (x - 1.4, x + 1.4, y - 1.4, y + 1.4, 0.0, 22.0), "poros",
                 lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 1.3, tone=M.ashlar(3.0, 8.0, seed + k, spread=0.4))
        slab(m, 0.0, W, y - 1.2, y + 1.2, 20.0, 22.0, "wood", tone=M.timber("x", seed))
    for k in range(16):
        y0 = k * T
        tiled_roof(m, 0.0, W + 2.0, y0, y0 + T, 22.0, 4.0, axis="x", material="terracotta", kind="laconian",
                   seed=seed + 10 + k, antefixes=k % 2 == 0)
        if hash01(k, seed) < 0.75:
            hull(m, 8.0, W - 6.0, y0 + T / 2, float(floor(np.float32(40.0))) + 0.5, beam=4.2, depth=4.0, seed=k)
        else:   # an empty shed: the slipway's timber skids and a stack of oars
            for yy in (y0 + 5.0, y0 + 11.0):
                slab(m, 6.0, W - 4.0, yy - 0.6, yy + 0.6, 0.0, rise + 0.5, "wood",
                     tone=M.timber("x", seed + k))
            for i in range(5):
                rod(m, (10.0, y0 + 7.0 + i * 0.5, 0.5 + i * 0.6), (60.0, y0 + 7.0 + i * 0.5, 4.0 + i * 0.6), 0.3,
                    "wood_light")


def harbour(m):
    """The Kantharos harbour front: a stone quay with bollards and stacked amphorae, the long
    emporion stoa where merchants show their samples, warehouses behind, and the tower at the
    end of the mole that narrows the harbour mouth, a fire on top at night."""
    seed = 511
    W, Lh = 10 * T, 18 * T
    # The quay: squared blocks to the water's edge on the south.
    slab(m, 104.0, W, 0.0, Lh - 48.0, 0.0, 1.6, "poros", tone=M.ashlar(1.6, 8.0, seed, spread=0.5))
    slab(m, W - 3.0, W, 0.0, Lh - 48.0, 1.6, 2.4, "poros", tone=0.3)
    for y in np.arange(24.0, Lh - 48.0, 48.0):
        fill(m, (W - 8.0, W - 4.0, y - 2.0, y + 2.0, 1.6, 6.0), "poros",
             lambda X, Y, Z, y=y: np.hypot(X - (W - 6.0), Y - y) < 1.8, tone=0.2)
    # Warehouses and the emporion stoa facing the quay.
    for x0, x1, y0, y1 in ((2.0, 28.0, 2.0, 140.0), (2.0, 28.0, 148.0, 286.0)):
        for w in ((x0, x0 + 3, y0, y1), (x1 - 3, x1, y0, y1), (x0, x1, y0, y0 + 3), (x0, x1, y1 - 3, y1)):
            house_wall(m, *w, 0.0, 20.0, seed + 1, socle=4.0, plaster="mudbrick")
        tiled_roof(m, x0 - 2, x1 + 2, y0 - 2, y1 + 2, 20.0, 5.0, axis="y", material="terracotta", kind="laconian",
                   seed=seed + int(y0))
    so = Order("doric", D=0.9, H=5.2, upper=0.8, arch_h=0.7, frieze_h=0.75, geison_h=0.4, geison_out=0.55,
               material="poros")
    st = Stoa(order=so, front="+x", n_cols=17, roof="terracotta", seed=seed + 2)
    stoa(m, st, S, 30.0, 78.0, 4.0, 236.0)
    for y in (40.0, 120.0, 200.0):
        lamp_niche(m, 34.0, y, 12.0, 0.4)
    # Goods on the quay: amphora stacks, sacks, a crane for unloading.
    for i, y in enumerate((16.0, 70.0, 130.0, 190.0)):
        for j in range(4):
            vase(m, 116.0 + (j % 2) * 4.0, y + (j // 2) * 4.0 + i, 1.6, 7.0, "transport", figure="plain")
    crane(m, 140.0, 100.0, 1.6, 36.0, along="x")
    # The mole tower at the west end, a beacon fire on top.
    house_wall(m, 104.0, 156.0, 244.0, 286.0, 0.0, 32.0, seed + 3, socle=10.0, plaster="whitewash", socle_mat="poros")
    fill(m, (104.0, 156.0, 244.0, 286.0, 32.0, 35.0), "whitewash", lambda X, Y, Z: ((X + Y) % 5.0) < 2.6, tone=0.2)
    ellipsoid(m, (130.0, 265.0, 34.0), (3.0, 3.0, 2.0), "fire", tone=0.3)
    halo(m, 130.0, 265.0, 36.0, 20.0, FIRE, 1.0)
    fill(m, (128.0, 132.0, 285.0, 287.0, 0.0, 18.0), "ink", tone=0.0)


def _harbour_landmark():
    blocked = {(9, 1), (9, 4), (9, 7), (9, 10), (9, 13), (7, 0), (7, 1), (7, 4), (7, 8), (7, 11), (7, 12), (8, 5),
               (8, 6), (9, 6)}
    walk = [t for t in tiles(5, 9, 0, 14) if t not in blocked]
    floor = {t: (0.0 if t[0] == 5 else 2.4 if t[0] == 9 else 1.6) for t in walk}
    return Landmark((10, 18), (0, 56), ref("harbour"), walk=walk, floor=floor,
                    slots={"moor": [{"t": [10, y], "face": "-x"} for y in (2, 8, 11, 14)],
                           "trade": [{"t": [5, y], "face": "-x"} for y in (2, 6, 10)],
                           "load": [{"t": [8, 2], "face": "+x"}, {"t": [8, 9], "face": "+x"}]},
                    emitters={"beacon": (130.0, 265.0, 37.0)}, district=7)


def pentelikon_quarry(m):
    """The marble quarry high on Pentelikon: bright white-gold faces cut back in steps where
    the blocks come out, rows of wedge slots, blocks half detached on their beds, the rough
    weathered hillside with pines above, rubble tips, and the sledge ramp down to the road."""
    seed = 521
    W, Lh = 19 * T, 20 * T

    def slope(X, Y):            # the mountain rising east (toward -y)
        n = value_noise(X, Y, X * 0, 24.0, seed) - 0.5
        return np.clip((Lh - Y) / Lh, 0, 1) ** 0.85 * 58.0 + n * 9.0

    def cut(X, Y):
        return np.where(Y >= 200, 0.0, np.where(Y >= 130, 18.0, np.where(Y >= 70, 34.0, 48.0)))

    inside = lambda X, Y: (X > 48) & (X < 256) & (Y > 20)
    top = lambda X, Y: np.where(inside(X, Y), np.minimum(np.maximum(slope(X, Y), 0.0), cut(X, Y)), slope(X, Y))

    def tone(X, Y, Z):
        cutf = inside(X, Y) & (Z > top(X, Y) - 1.0)
        marks = 0.3 * ((X * 1.3 + Z * 0.4) % 1.6 < 0.4)
        rough = (value_noise(X, Y, Z, 4.0, seed + 1) - 0.5) * 1.2
        return np.where(cutf, 0.6 + marks, rough - 0.3)
    field_fill(m, (0, W, 0, Lh, 0, 62), lambda X, Y, Z: Z - top(X, Y), "marble_rough", tone=tone)
    fill(m, (0, W, 0, Lh, 0, 62), "marble",
         lambda X, Y, Z: inside(X, Y) & (Z > top(X, Y) - 1.2) & (np.abs(Z - cut(X, Y)) < 1.0), tone=0.4, only_solid=True)
    fill(m, (0, W, 0, Lh, 0, 62), "summer",
         lambda X, Y, Z: ~inside(X, Y) & (Z > top(X, Y) - 1.0) & (value_noise(X, Y, Z, 5.0, seed + 2) > 0.5),
         tone=0.0, only_solid=True)
    for yb, z in ((200.0, 18.0), (130.0, 34.0), (70.0, 48.0)):
        carve(m, (52, 252, yb - 0.6, yb + 0.8, z - 2.5, z - 1.0), lambda X, Y, Z: (X % 4.0) < 1.2)
    for (x, y, z, w) in ((80, 140, 18, 16), (180, 146, 18, 12), (120, 80, 34, 14), (210, 86, 34, 10), (150, 30, 48, 12)):
        carve(m, (x - 1.2, x + w + 1.2, y - 1.2, y + w * 0.7 + 1.2, z, z + 12.0))
        slab(m, x, x + w, y, y + w * 0.7, z, z + 9.0, "marble", tone=M.plus(M.ashlar(9.0, 40.0, x), 0.3))
    # Rubble tips at both sides.
    for x0, x1 in ((0, 48), (256, 304)):
        fill(m, (x0, x1, 60, 320, 0, 40), "marble_rough",
             lambda X, Y, Z: Z < np.clip((320 - Y) / 260 * 34, 0, None) + (value_noise(X * 2, Y * 2, Z, 1.0, seed + 3) - 0.5) * 3,
             tone=lambda X, Y, Z: (value_noise(X * 3, Y * 3, Z, 1.0, seed + 4) - 0.5) * 1.6)
    # The sledge ramp down the west side and a loaded sledge with its ropes and posts.
    fill(m, (256.0, 290.0, 200.0, 320.0, 0.0, 20.0), "poros",
         lambda X, Y, Z: Z < np.clip((320.0 - Y) / 120.0, 0, 1) * 18.0, tone=M.ashlar(2.0, 6.0, seed, spread=0.6))
    slab(m, 266.0, 280.0, 250.0, 262.0, 9.0, 11.0, "wood", tone=M.timber("y", seed))
    slab(m, 267.0, 279.0, 251.0, 261.0, 11.0, 17.0, "marble", tone=0.3)
    for y in (232.0, 290.0):
        rod(m, (260.0, y, 0.0), (260.0, y, 14.0), 0.9, "wood")
    for x, y in ((24.0, 16.0), (290.0, 30.0), (20.0, 60.0)):
        olive_tree(m, x, y, float(slope(np.float32(x), np.float32(y))), h=18.0, seed=int(x))


def _quarry_landmark():
    walk = tiles(4, 15, 13, 19)
    return Landmark((19, 20), (0, 72), ref("pentelikon_quarry"), walk=walk,
                    slots={"cut": [{"t": [5, 13], "face": "-y"}, {"t": [9, 13], "face": "-y"},
                                   {"t": [13, 13], "face": "-y"}, {"t": [7, 15], "face": "-y"}],
                           "sledge": [{"t": [15, 16], "face": "+y"}]},
                    emitters={"dust": (120.0, 210.0, 3.0)}, district=8)


# ---------------------------------------------------------------- waypoints (s = 0.5)

def telesterion(m):
    """The Telesterion at Eleusis under Iktinos's Periclean rebuilding (its progress in 432 is
    uncertain; shown with the walls up and the roof unfinished): a square hall with rows of
    interior columns, tiers of rock-cut steps for the initiates along the walls, roof beams laid
    over one part and open sky over the rest, scaffolding; the sanctuary wall and the
    Kallichoron well."""
    seed = 531
    W = 10 * T
    hb = S05.v(12.0)
    for w in ((6.0, 10.0, 6.0, 154.0), (150.0, 154.0, 6.0, 154.0), (6.0, 154.0, 6.0, 10.0), (6.0, 154.0, 150.0, 154.0)):
        poros_wall(m, *w, 0.0, hb, seed, course=1.6)
    for d in range(4):         # the tiers of steps inside every wall
        e = 10.0 + d * 4.0
        for w in ((e, e + 4.0, e, 150.0 - d * 4.0), (e, 150.0 - d * 4.0, e, e + 4.0)):
            slab(m, *w, 0.0, 6.0 - d * 1.4, "attic_rock", tone=0.25)
    for face, a in (("+x", (148.0, 156.0, 70.0, 90.0)), ("+y", (70.0, 90.0, 148.0, 156.0))):
        carve(m, (*a, 0.0, 18.0))
    o = Order("doric", D=0.9, H=11.0, upper=0.85, material="marble")
    for x in np.linspace(36.0, 124.0, 6):
        for y in np.linspace(36.0, 124.0, 6):
            fin = "full" if (x + y) < 150 else "drums"
            column(m, x, y, 0.0, o, S05, finish=fin, drums=2 + int(x + y) % 3, seed=int(x))
    for x in np.linspace(36.0, 124.0, 6):          # beams laid over the northern rows only
        rod(m, (x, 30.0, S05.v(11.0) + 1.0), (x, 90.0, S05.v(11.0) + 1.0), 1.1, "wood")
    for y in np.linspace(36.0, 90.0, 4):
        rod(m, (30.0, y, S05.v(11.0) + 2.5), (130.0, y, S05.v(11.0) + 2.5), 0.9, "wood")
    scaffold(m, 100.0, 116.0, 100.0, 116.0, 0.0, 30.0, decks=2)
    fill(m, (124.0, 134.0, 124.0, 134.0, 0.0, 3.0), "poros",
         lambda X, Y, Z: np.abs(np.hypot(X - 129, Y - 129) - 3.6) < 1.2, tone=0.2)


def academy_grove(m):
    """The Academy outside the city: a gymnasium in a grove of Athena's sacred olives (moriai)
    and planes, a running track, and the altar of Prometheus where the torch races start."""
    seed = 541
    W, Lh = 10 * T, 12 * T
    fill(m, (60.0, 80.0, 8.0, Lh - 8.0, 0.0, 0.5), "gravel", tone=-0.1)
    rng = Rng(seed)
    for i in range(14):
        x = 10.0 + (i % 4) * 14.0 + rng.uniform(-3, 3) if i % 2 else 100.0 + (i % 3) * 22.0 + rng.uniform(-3, 3)
        y = 14.0 + (i // 2) * 24.0 + rng.uniform(-4, 4)
        olive_tree(m, x, y, 0.0, h=18.0 + rng.uniform(-2, 3), seed=i, spread=0.9)
    altar(m, 70.0, Lh - 18.0, 0.0, 8.0, 6.0, 3.0, fire=True)


LANDMARKS = {
    "athens.shipsheds": Landmark((6, 16), (0, 40), ref("shipsheds"), district=7),
    "athens.harbour": _harbour_landmark(),
    "athens.pentelikon_quarry": _quarry_landmark(),
    "athens.telesterion": Landmark((10, 10), (0, 56), ref("telesterion"), district=9),
    "athens.academy_grove": Landmark((10, 12), (0, 32), ref("academy_grove"),
                                     emitters={"altar": (70.0, 174.0, 7.0)}, district=9),
}
