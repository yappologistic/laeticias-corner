"""The city round the Acropolis in 432 (athens.md §2.3 D5, D7, D12-D14): the Dipylon and the
Sacred Gate in the Kerameikos, the Pnyx in its first phase with Meton's sundial, the Theatre of
Dionysos with its wooden seating, the old temple of Dionysos, the Odeion of Pericles, the
abandoned Olympieion platform, the Kallirrhoe spring and the Lyceum."""

import math

import numpy as np

import materials as M
from arch import Scale, carve, ellipsoid, fill, halo, rod, slab
from greek import (Order, Stoa, Temple, city_wall, column, doric_entablature, hip_roof, house_wall, poros_wall, stoa,
                   temple, tiled_roof)
from setbuild import Landmark
from sets.athens.common import FIRE, S, T, altar, drum, olive_tree, referrer, rock_field, tiles
from models.nature import leaf_mass
from voxel import Rng, value_noise

ref = referrer("sets.athens.city")
S08 = Scale(0.8)


def _torch(m, x, y, z):
    rod(m, (x, y, z), (x, y, z + 3.0), 0.4, "bronze")
    ellipsoid(m, (x, y, z + 4.0), (0.9, 0.9, 1.4), "fire", tone=0.3)
    halo(m, x, y, z + 4.0, 11.0, FIRE, 0.8)


def _tower(m, x0, x1, y0, y1, h, seed, roof=True):
    """A wall tower: a stone socle, plastered mudbrick, small windows, a tiled pyramid roof."""
    city_wall(m, x0, x1, y0, y1, 0.0, h, seed=seed, merlons=not roof)
    for face_y in (y0, y1):
        for x in ((x0 + x1) / 2 - 3.0, (x0 + x1) / 2 + 3.0):
            fill(m, (x - 0.9, x + 0.9, face_y - 0.4, face_y + 0.4, h - 9.0, h - 5.0), "ink", tone=0.0)
    if roof:
        slab(m, x0 - 1.0, x1 + 1.0, y0 - 1.0, y1 + 1.0, h, h + 1.2, "poros", tone=0.3)
        hip_roof(m, x0 - 2.0, x1 + 2.0, y0 - 2.0, y1 + 2.0, h + 1.2, (x1 - x0) * 0.35, material="terracotta",
                 seed=seed + 1)


# ---------------------------------------------------------------- Kerameikos gates

def dipylon(m):
    """The Dipylon, the city's greatest gate, where the Panathenaic Way begins: a long court
    open to the Kerameikos between two strong towers, closed at its inner end by a double
    gateway (two passages and a pier); mudbrick on a stone base, whitewashed, crenellated
    curtains, tiled tower roofs, torches at the gates."""
    seed = 401
    h = 34.0
    # The court's side walls (the city wall turned inward) and the outer towers.
    for x0, x1 in ((4.0, 30.0), (82.0, 108.0)):
        city_wall(m, x0, x1, 0.0, 78.0, 0.0, h, seed=seed, grave_reuse=True)
        _tower(m, x0, x1, 78.0, 110.0, h + 14.0, seed + 2)
    # The inner double gate: two passages with timber doors standing open, the pier between.
    city_wall(m, 30.0, 82.0, 0.0, 20.0, 0.0, h, seed=seed + 3)
    for x0, x1 in ((32.0, 48.0), (64.0, 80.0)):
        carve(m, (x0, x1, -1.0, 21.0, 0.0, 26.0))
        slab(m, x0 - 1.0, x1 + 1.0, -0.5, 20.5, 26.0, 28.0, "wood", tone=M.timber("x", seed))
        for xx in (x0 - 1.5, x1 + 0.5):    # the leaves standing open against the jambs
            slab(m, xx, xx + 1.0, 20.0, 28.0, 0.0, 24.0, "wood", tone=M.timber("y", seed + 1))
    for y in (22.0,):
        for x in (31.0, 81.0):
            _torch(m, x, y, 18.0)
    for x in (31.0, 81.0):
        _torch(m, x, 112.0, 26.0)


def _dipylon_landmark():
    walk = tiles(2, 4, 2, 6) + [(2, 0), (2, 1), (4, 0), (4, 1)]
    return Landmark((7, 7), (0, 76), ref("dipylon"), walk=walk,
                    slots={"guard": [{"t": [3, 5], "face": "+y"}, {"t": [3, 2], "face": "-y"}]},
                    emitters={"torch_a": (31.0, 22.0, 22.0), "torch_b": (81.0, 22.0, 22.0)}, district=3)


def sacred_gate(m):
    """The Sacred Gate, where the Sacred Way leaves for Eleusis: the road passing west through
    the wall between two towers and, beside it, the Eridanos running through the wall in a
    stone channel under a lintel."""
    seed = 411
    h = 30.0
    _tower(m, 2.0, 15.0, 22.0, 58.0, h + 8.0, seed)
    _tower(m, 64.0, 78.0, 22.0, 58.0, h + 8.0, seed + 2)
    city_wall(m, 48.6, 50.5, 34.0, 46.0, 0.0, h, seed=seed + 1, merlons=False)      # the pier between road and stream
    slab(m, 50.0, 64.0, 34.0, 46.0, 14.0, h, "poros", tone=M.ashlar(2.6, 6.0, seed, spread=0.5))
    for x0 in (49.0, 61.5):
        slab(m, x0, x0 + 2.0, 0.0, 80.0, 0.0, 2.6, "poros", tone=M.ashlar(2.6, 6.0, seed + 3, spread=0.5))
    fill(m, (51.0, 61.5, 0.0, 80.0, 0.0, 1.2), "water", tone=lambda X, Y, Z: 0.5 * ((Y * 0.7 + X * 0.2) % 3.0 < 0.6))


# ---------------------------------------------------------------- the Pnyx

PNYX_RISE = 16.0                   # two levels: the bema at 4, the top at 6
BEMA = 7.5


def _pnyx_ground(x):
    return np.clip((x - 16.0) / (15 * T - 16.0), 0, 1) * PNYX_RISE


def pnyx(m):
    """The assembly place in its first phase (as reconstructed): the natural rocky slope of the
    hill falling north to a low retaining wall and the speakers' platform (bema), cut in the
    rock with steps up to it; bare rock showing through thin dry earth, worn paths, thyme."""
    seed = 421
    W, Lh = 15 * T, 17 * T

    def top(X, Y):
        n = (value_noise(X, Y, X * 0, 9.0, seed) - 0.5) * 1.0
        return np.maximum(_pnyx_ground(X) + n, 0.3)
    rock_field(m, (0.0, W, 0.0, Lh, 0.0, PNYX_RISE + 2.0), top, seed=seed, stains=False)
    # Thin dry earth over most of the slope in broad soft patches (QA4 V-A-006: no mottle):
    # bare grey bedrock shows in long ledges along the contours, thyme in the earth.
    def earth(X, Y, Z):
        n = value_noise(X * 0.35, Y * 0.35, Z * 0, 12.0, seed + 2) + 0.18 * np.sin(X * 0.09 + Y * 0.01)
        return (Z > top(X, Y) - 0.8) & (n > 0.36)
    fill(m, (0.0, W, 0.0, Lh, 0.0, PNYX_RISE + 2.0), "summer", earth,
         tone=lambda X, Y, Z: (value_noise(X, Y, Z * 0, 6.0, seed + 3) - 0.5) * 0.5 - 0.25, only_solid=True)
    fill(m, (0.0, W, 0.0, Lh, 0.0, PNYX_RISE + 2.0), "olive",
         lambda X, Y, Z: earth(X, Y, Z) & (value_noise(X * 2.0, Y * 2.0, Z * 0, 1.0, seed + 4) > 0.8),
         tone=-0.2, only_solid=True)
    # The retaining wall along the north edge and the rock-cut bema with its steps.
    poros_wall(m, 0.0, 6.0, 0.0, Lh, 0.0, 4.0, seed + 4, course=2.0)
    fill(m, (6.0, 30.0, 7 * T, 10 * T, 0.0, BEMA), "attic_rock", tone=M.ashlar(2.5, 8.0, seed + 5, spread=0.5))
    for i in range(3):
        slab(m, 0.0, 6.0 + i * 2.0, 7 * T + 8.0, 7 * T + 16.0, 0.0, BEMA * (i + 1) / 3, "attic_rock", tone=0.2)


def _pnyx_landmark():
    walk = [t for t in tiles(1, 14, 0, 16)]
    floor = {(x, y): (BEMA if x == 1 and 7 <= y <= 9 else float(_pnyx_ground((x + 1) * T) + 0.6)) for x, y in walk}
    spots = [{"t": [x, y], "face": "-x"} for x in (4, 6, 8, 10) for y in (3, 6, 9, 12)]
    return Landmark((15, 17), (0, 24), ref("pnyx"), walk=walk, floor=floor,
                    slots={"bema": [{"t": [1, 8], "face": "+x", "z": int(BEMA * 2)}], "assembly": spots,
                           "archer": [{"t": [2, 2], "face": "+x"}, {"t": [2, 14], "face": "+x"}]}, district=4)


def meton_dial(m):
    """Meton's heliotropion: a levelled stone platform with a marked meridian line and a
    gnomon, where he watched the summer solstice of 432."""
    slab(m, 3.0, 29.0, 3.0, 29.0, 0.0, 1.4, "poros", tone=M.ashlar(1.4, 8.0, 3, spread=0.4))
    fill(m, (15.4, 16.6, 4.0, 28.0, 1.3, 1.5), "gloss", tone=0.0)
    for y in (8.0, 14.0, 20.0, 26.0):
        fill(m, (13.0, 19.0, y - 0.3, y + 0.3, 1.3, 1.5), "gloss", tone=0.0)
    slab(m, 14.5, 17.5, 4.0, 7.0, 1.4, 9.0, "marble", tone=0.2)
    rod(m, (16.0, 5.5, 9.0), (16.0, 5.5, 12.0), 0.3, "bronze")


# ---------------------------------------------------------------- the theatre, Dionysos, the Odeion

TH_X, TH_Y = 14 * T, 7.5 * T             # orchestra centre
TH_R0, TH_TOP = 40.0, 48.0               # orchestra radius, cavea top (six levels)
FAN_X = 204.0                            # the seating stops at the orchestra's diameter (the parodoi)


def _cavea(X, Y):
    d = np.hypot(X - TH_X, Y - TH_Y)
    return np.clip((d - TH_R0) / (TH_X - TH_R0), 0, 1)


def theatre(m):
    """The Theatre of Dionysos before its stone rebuilding: rows of wooden bleachers (ikria) on
    timber trestles laid over the earth slope of the Acropolis, divided by earth stairways into
    wedges; a round orchestra of beaten earth with the altar (thymele) in the middle; a simple
    wooden stage building (skene) with painted panels on its audience side; scrub and rock on
    the hillside round the seating."""
    seed = 431
    W, Lh = 17 * T, 15 * T

    def hill(X, Y):          # the slope rising north over the footprint behind the parodoi
        f = np.clip((FAN_X - 4.0 - X) / (FAN_X - 4.0), 0, 1) ** 0.9
        return f * TH_TOP + (value_noise(X, Y, X * 0, 10.0, seed) - 0.5) * 2.0 * f

    in_fan = lambda X, Y: (X < FAN_X) & (np.hypot(X - TH_X, Y - TH_Y) > TH_R0)
    rock_field(m, (0.0, TH_X, 0.0, Lh, 0.0, TH_TOP + 3.0), lambda X, Y: np.where(in_fan(X, Y), _cavea(X, Y) * TH_TOP - 1.0,
                                                                                  hill(X, Y)), seed=seed, stains=False)
    fill(m, (0.0, TH_X, 0.0, Lh, 0.0, TH_TOP + 3.0), "summer",
         lambda X, Y, Z: ~in_fan(X, Y) & (Z > hill(X, Y) - 1.0) & (value_noise(X, Y, Z, 4.0, seed + 1) > 0.45),
         tone=lambda X, Y, Z: (value_noise(X * 3, Y * 3, Z, 1.0, seed + 2) - 0.5), only_solid=True)
    # The wooden bleachers: a plank seat and a darker riser per row, six wedges between stairways.
    row = 3.2

    def seat_top(X, Y):
        d = np.hypot(X - TH_X, Y - TH_Y) - TH_R0
        return np.floor(d / row) * row / (TH_X - TH_R0) * TH_TOP + 1.2

    def aisle(X, Y):
        a = np.arctan2(Y - TH_Y, TH_X - X)
        return (np.abs(((a + np.pi / 2) / np.pi * 6) % 1.0 - 0.5) > 0.45)

    def bench(X, Y, Z):
        return in_fan(X, Y) & ~aisle(X, Y) & (Z < seat_top(X, Y)) & (Z > seat_top(X, Y) - 2.4)

    def bench_tone(X, Y, Z):
        d = np.hypot(X - TH_X, Y - TH_Y) - TH_R0
        u = (d % row) / row
        return np.where(u > 0.6, 0.4, -0.5) + (value_noise(X * 2, Y * 2, Z, 1.0, seed + 3) - 0.5) * 0.4
    fill(m, (0.0, TH_X, 0.0, Lh, 0.0, TH_TOP + 3.0), "wood_light", bench, bench_tone)
    # Trestle legs glimpsed under the front rows.
    for a in np.linspace(-1.4, 1.4, 15):
        for d in (TH_R0 + 4.0, TH_R0 + 12.0):
            x, y = TH_X - d * math.cos(a), TH_Y + d * math.sin(a)
            if x >= FAN_X - 2.0:
                continue
            rod(m, (x, y, 0.0), (x, y, float(seat_top(np.float32(x), np.float32(y)))), 0.35, "wood")
    # The orchestra and its altar.
    fill(m, (TH_X - TH_R0, TH_X + TH_R0, TH_Y - TH_R0, TH_Y + TH_R0, 0.0, 0.6), "gravel",
         lambda X, Y, Z: np.hypot(X - TH_X, Y - TH_Y) < TH_R0 - 1.0, tone=lambda X, Y, Z: -0.2 +
         0.3 * (np.abs(np.hypot(X - TH_X, Y - TH_Y) - TH_R0 + 2.0) < 0.6))
    altar(m, TH_X, TH_Y, 0.0, 4.0, 4.0, 3.0, fire=False, steps=False)
    # The skene: a long timber hall with painted panels toward the audience, a tiled roof.
    x0, x1, y0, y1 = 15 * T + 2.0, 17 * T - 2.0, 2 * T, 13 * T
    for xx in (x0, x1):
        for yy in np.arange(y0, y1 + 0.1, 11.0):
            rod(m, (xx, yy, 0.0), (xx, yy, 20.0), 0.7, "wood")
    slab(m, x0, x1, y0, y1, 0.0, 19.0, "wood_light", tone=M.timber("y", seed))
    for i, yy in enumerate(np.arange(y0 + 4.0, y1 - 8.0, 14.0)):
        fill(m, (x0 - 0.5, x0 + 0.2, yy, yy + 10.0, 4.0, 16.0), ("eblue", "cinnabar", "ochre")[i % 3], tone=0.0)
        fill(m, (x0 - 0.6, x0 + 0.1, yy + 3.0, yy + 7.0, 6.0, 14.0), "whitewash", tone=0.2)
    carve(m, (x0 - 1.0, x0 + 3.0, TH_Y - 5.0, TH_Y + 5.0, 0.0, 14.0))
    tiled_roof(m, x0, x1 + 2.0, y0 - 2.0, y1 + 2.0, 19.0, 4.0, axis="y", material="terracotta", kind="laconian",
               seed=seed + 4)


def _theatre_landmark():
    walk = [(x, y) for x in (13, 14) for y in range(15) if y not in (7, 8)]
    return Landmark((17, 15), (0, 56), ref("theatre"), walk=walk,
                    slots={"chorus": [{"t": [13 + i % 2, (4, 5, 6, 9, 10, 11)[i]]} for i in range(6)],
                           "watch": [{"t": [13, 2], "face": "+y"}], "aulos": [{"t": [14, 6], "face": "-x"}]},
                    district=5)


def dionysos_temple(m):
    """The old temple of Dionysos Eleuthereus in the sanctuary below the theatre: a small poros
    temple in antis with a terracotta roof."""
    o = Order("doric", D=0.6, H=3.6, upper=0.8, arch_h=0.5, frieze_h=0.55, geison_h=0.3, geison_out=0.45,
              material="poros")
    t = Temple(order=o, axis="y", cols=(2, 2), steps=(1.2, 1.2), tread=1.0, edge=3.0, peripteral=False,
               cella=(6.0, 12.0), porch="antis", pediments=("small", "small"), roof="terracotta", seed=441)
    temple(m, t, S, 8.0, 56.0, 10.0, 102.0)
    altar(m, 62.0, 20.0, 0.0, 6.0, 4.0, 3.0, fire=False)


def odeion(m):
    """Pericles's Odeion (s = 0.8): a great square hall whose forest of interior columns carries a
    steep pyramidal roof, said to imitate the Persian king's tent and built with timber from the
    captured ships; stone walls with high windows, a Doric porch along the south front."""
    seed = 451
    W, Lh = 14 * T, 13 * T
    hb = S08.v(10.0)
    x0, x1, y0, y1 = 8.0, W - 28.0, 8.0, Lh - 8.0
    for w in ((x0, x0 + 4, y0, y1), (x1 - 4, x1, y0, y1), (x0, x1, y0, y0 + 4), (x0, x1, y1 - 4, y1)):
        poros_wall(m, *w, 0.0, hb, seed, course=2.0)
        house_wall(m, *w, hb * 0.35, hb, seed=seed + 1, socle=0.0, plaster="whitewash")
    for y in np.arange(y0 + 16, y1 - 8, 16.0):        # high windows on the south and west walls
        fill(m, (x1 - 0.8, x1 + 0.4, y - 2.0, y + 2.0, hb - 9.0, hb - 3.0), "ink", tone=0.0)
    for x in np.arange(x0 + 16, x1 - 8, 16.0):
        fill(m, (x - 2.0, x + 2.0, y1 - 0.8, y1 + 0.4, hb - 9.0, hb - 3.0), "ink", tone=0.0)
    # The south porch of Doric columns.
    po = Order("doric", D=1.0, H=7.0, upper=0.8, arch_h=0.8, frieze_h=0.85, geison_h=0.45, geison_out=0.6,
               material="poros")
    cols = list(np.arange(y0 + 6.0, y1 - 4.0, 12.0))
    for y in cols:
        column(m, x1 + 14.0, y, 0.0, po, S08)
    slab(m, x1, x1 + 18.0, y0, y1, 0.0, 1.0, "poros", tone=0.2)
    zg = doric_entablature(m, (x1, x1 + 16.0, y0, y1), S08.v(po.H), po, S08, [x1 + 14.0], cols, faces=("+x",),
                           seed=seed + 2)
    tiled_roof(m, x1 - 2.0, x1 + 19.0, y0 - 2.0, y1 + 2.0, zg, 3.0, axis="y", material="terracotta", seed=seed + 3,
               ridge=False)
    # The tent roof: a steep pyramid of tiles to a small lantern.
    slab(m, x0 - 1.0, x1 + 1.0, y0 - 1.0, y1 + 1.0, hb, hb + 1.5, "poros", tone=0.3)
    hip_roof(m, x0 - 3.0, x1 + 3.0, y0 - 3.0, y1 + 3.0, hb + 1.5, 40.0, material="terracotta", seed=seed + 4)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    slab(m, cx - 4.0, cx + 4.0, cy - 4.0, cy + 4.0, hb + 36.0, hb + 44.0, "wood", tone=M.timber("x", seed))
    hip_roof(m, cx - 5.5, cx + 5.5, cy - 5.5, cy + 5.5, hb + 44.0, 5.0, material="terracotta", seed=seed + 5)


# ---------------------------------------------------------------- the Ilissos and the Lyceum

def olympieion(m):
    """The Peisistratids' abandoned temple of Olympian Zeus: a vast stepped poros platform, a
    few unfinished columns standing to a drum or two, drums lying in the dry grass where the
    work stopped generations ago, a wild olive taking root."""
    seed = 461
    W, Lh = 11 * T, 19 * T
    slab(m, 6.0, W - 6.0, 6.0, Lh - 6.0, 0.0, 2.4, "poros", tone=M.ashlar(2.4, 9.0, seed, spread=0.8, odd=0.3))
    slab(m, 10.0, W - 10.0, 10.0, Lh - 10.0, 2.4, 4.8, "poros", tone=M.ashlar(2.4, 9.0, seed + 1, spread=0.8, odd=0.3))
    fill(m, (10.0, W - 10.0, 10.0, Lh - 10.0, 4.7, 5.2), "summer",
         lambda X, Y, Z: value_noise(X, Y, Z, 5.0, seed + 2) > 0.55, tone=0.0)
    rng = Rng(seed)
    for i, x in enumerate(np.linspace(20.0, W - 20.0, 6)):
        for y in np.linspace(22.0, Lh - 22.0, 12):
            r = rng.uniform(0, 1)
            if r < 0.25:
                drum(m, x, y, 4.8, 7.0, 6.0 * (1 + int(r * 8) % 2))
            elif r < 0.35:
                drum(m, x + rng.uniform(-4, 4), y + rng.uniform(-4, 4), 4.8, 6.5, 6.0, lying=True,
                     along="x" if r < 0.3 else "y")
    olive_tree(m, 40.0, 150.0, 4.8, h=18.0, seed=4)


def kallirrhoe(m):
    """The Kallirrhoe spring by the Ilissos: water welling from a rock-cut basin under a ledge,
    a stone kerb and steps down to it, maidenhair and reeds."""
    seed = 471
    rock_field(m, (0.0, 48.0, 0.0, 22.0, 0.0, 14.0), lambda X, Y: 12.0 * np.clip((22.0 - Y) / 20.0, 0, 1) ** 0.6 +
               (value_noise(X, Y, X * 0, 4.0, seed) - 0.5) * 2, seed=seed, stains=False)
    # Damp dark rock and moss round the basin, maidenhair on the ledge (QA4 V-A-009).
    fill(m, (0.0, 48.0, 12.0, 22.0, 0.0, 14.0), "leaf_dark",
         lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, seed + 1) > 0.55) & (Y > 15.0), tone=-0.1, only_solid=True)
    fill(m, (0.0, 48.0, 0.0, 22.0, 0.0, 14.0), "slate",
         lambda X, Y, Z: (Y > 17.0) & (Z < 3.0) & (value_noise(X, Y, Z, 2.0, seed + 2) > 0.4), tone=-0.2,
         only_solid=True)
    fill(m, (8.0, 40.0, 20.0, 40.0, 0.0, 1.0), "water", lambda X, Y, Z: np.hypot((X - 24) / 15.0, (Y - 30) / 9.0) < 1,
         tone=lambda X, Y, Z: 0.5 * ((X + Y * 0.5) % 4.0 < 0.6))
    fill(m, (6.0, 42.0, 18.0, 42.0, 0.0, 2.0), "poros",
         lambda X, Y, Z: np.abs(np.hypot((X - 24) / 16.5, (Y - 30) / 10.5) - 1.0) < 0.08, tone=0.2)
    for i in range(6):
        rod(m, (6.0 + i * 1.3, 40.0, 0.0), (5.0 + i * 1.5, 41.0, 7.0 + (i % 3)), 0.3, "grass", tone=0.3)


def lyceum(m):
    """The Lyceum gymnasium outside the walls: a straight running track marked with stone
    posts, a grove of plane trees where cavalry and hoplites drill and talkers walk, the little
    shrine of Apollo Lykeios with its altar, and a palaestra court with a colonnade."""
    seed = 481
    W, Lh = 17 * T, 12 * T
    # The track: a long strip of raked sand with start and turning posts.
    fill(m, (4.0, W - 4.0, 18.0, 46.0, 0.0, 0.5), "gravel", tone=lambda X, Y, Z: -0.1 + 0.3 * ((X % 8.0) < 0.4))
    for x in (8.0, W - 8.0):
        for y in (20.0, 32.0, 44.0):
            slab(m, x - 0.8, x + 0.8, y - 0.8, y + 0.8, 0.0, 4.0, "marble", tone=0.2)
    # The shrine of Apollo Lykeios.
    o = Order("doric", D=0.5, H=3.4, upper=0.8, arch_h=0.45, frieze_h=0.5, geison_h=0.3, geison_out=0.4,
              material="poros")
    t = Temple(order=o, axis="x", cols=(2, 2), steps=(1.0,), tread=0.8, edge=2.0, peripteral=False, cella=(3.0, 5.0),
               porch="antis", pediments=("small", "small"), roof="terracotta", seed=seed)
    temple(m, t, S, 36.0, 72.0, 132.0, 160.0)
    altar(m, 82.0, 146.0, 0.0, 5.0, 4.0, 2.6, fire=False)
    # The palaestra: a court ringed by a colonnade and rooms.
    st = Stoa(order=Order("doric", D=0.55, H=3.6, upper=0.8, arch_h=0.45, frieze_h=0.5, geison_h=0.3,
                          geison_out=0.4, material="poros"), front="-x", n_cols=6, roof="terracotta", seed=seed + 1)
    stoa(m, st, S, 196.0, 236.0, 100.0, 180.0)
    # The grove of planes.
    for i, (x, y) in enumerate(((40.0, 80.0), (88.0, 70.0), (130.0, 90.0), (170.0, 74.0), (120.0, 150.0), (20.0, 168.0))):
        _plane(m, x, y, seed + i)


def _plane(m, x, y, seed):
    rng = Rng(seed)
    rod(m, (x, y, 0.0), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), 22.0), 2.0, "wood_grey", tone=0.1)
    for a in (0.6, 2.6, 4.4):
        rod(m, (x, y, 16.0), (x + 7 * math.cos(a), y + 7 * math.sin(a), 28.0), 1.0, "wood_grey")
    clumps = [(x + 8 * math.cos(a) * rng.uniform(0.6, 1.0), y + 8 * math.sin(a) * rng.uniform(0.6, 1.0),
               32 + rng.uniform(-3, 4), rng.uniform(6.5, 8.0)) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    clumps.append((x, y, 40.0, 8.0))
    leaf_mass(m, clumps, seed + 7, materials=(("leaf", 0.7), ("grass", 0.3)), under="leaf_dark", level=-0.6)


def _lyceum_landmark():
    blocked = set(tiles(2, 4, 8, 9)) | set(tiles(12, 14, 6, 11)) | {(5, 8), (5, 9), (0, 1), (0, 2), (16, 1), (16, 2)}
    for x, y in ((40.0, 80.0), (88.0, 70.0), (130.0, 90.0), (170.0, 74.0), (120.0, 150.0), (20.0, 168.0)):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                blocked.add((int(x // T) + dx, int(y // T) + dy))
    walk = [t for t in tiles(0, 16, 0, 11) if t not in blocked]
    return Landmark((17, 12), (0, 56), ref("lyceum"), walk=walk,
                    slots={"drill": [{"t": [x, 2], "face": "+x"} for x in (3, 6, 9, 12)],
                           "run": [{"t": [1, 1]}, {"t": [15, 2]}], "talk": [{"t": [5, 7]}, {"t": [6, 7]}]},
                    district=6)


LANDMARKS = {
    "athens.dipylon": _dipylon_landmark(),
    "athens.sacred_gate": Landmark((5, 5), (0, 48), ref("sacred_gate"), walk=[(x, y) for x in (1, 2) for y in range(5)],
                                   emitters={"stream": (56.0, 70.0, 1.0)},
                                   district=3),
    "athens.pnyx": _pnyx_landmark(),
    "athens.meton_dial": Landmark((2, 2), (0, 14), ref("meton_dial"),
                                  slots={"observe": [{"t": [2, 1], "face": "-x"}]}, district=4),
    "athens.theatre": _theatre_landmark(),
    "athens.dionysos_temple": Landmark((4, 7), (0, 48), ref("dionysos_temple"), district=5),
    "athens.odeion": Landmark((14, 13), (0, 112), ref("odeion"), district=5),
    "athens.olympieion": Landmark((11, 19), (0, 24), ref("olympieion"), district=6),
    "athens.kallirrhoe": Landmark((3, 3), (0, 16), ref("kallirrhoe"),
                                  slots={"fill": [{"t": [1, 3], "face": "-y"}]}, district=6),
    "athens.lyceum": _lyceum_landmark(),
}
