"""The Acropolis in summer 432 (athens.md §2.3 D1, §3.1, §3.2): the finished Parthenon, the
Propylaia stopped with its lifting bosses on the blocks, the old Nike bastion, the approach
ramp, the Old Temple's foundations with its repaired west chamber, the Pandroseion's olive,
the bronze Athena, the Great Altar, the sculptors' yard, and the smaller sanctuaries.

Footprints: plan c (east) x r (south) -> catalog [r extent, c extent]; inside a footprint dx
runs south (+x), dy west (+y), the origin tile is the north-east corner."""

from dataclasses import replace

import numpy as np

import materials as M
from arch import carve, ellipsoid, fill, halo, rod, slab
from greek import (Order, Temple, column, crepidoma, doric_entablature, geison_ring, herm, hip_roof, house_wall, marble_wall,
                   pediment, poros_wall, stele, statue_base, temple, tiled_roof)
from rig import Dress
from setbuild import Landmark
from sets.athens.common import (ATHENA, S, T, altar, blocks, bosses, bronze_statue, crane, drum, olive_tree, referrer,
                                scaffold, tiles)
from voxel import value_noise

ref = referrer("sets.athens.acropolis")

# The Parthenon's Doric order (Pentelic marble): columns 10.43 m, lower diameter 1.905 m,
# 20 flutes, entablature 3.32 m; the porch columns 10.1 m (athens.md §3.1, §3.2).
PARTHENON = Order("doric", D=1.905, H=10.43, upper=0.78, flutes=20, entasis=0.02, arch_h=1.35, frieze_h=1.35,
                  geison_h=0.62, geison_out=0.85)


def parthenon(m):
    """8 x 17 Doric columns on three steps; a cella with six-column porches at both ends behind
    grilles; the continuous Ionic frieze of the procession round the top of the cella; 92
    painted metopes (west Amazons, south centaurs, east giants, north Troy); the west pediment
    (in view) with Athena and Poseidon contesting Attica, the east with the birth of Athena;
    floral akroteria, a marble-tiled roof with painted antefixes; lamplight at the west door."""
    t = Temple(order=PARTHENON, axis="y", cols=(8, 17), steps=(S.v(0.55),) * 3, tread=2.2, edge=4.6,
               cella=(18.0, 33.0), porch="prostyle", porch_cols=6, porch_order=replace(PARTHENON, H=10.1, D=1.71),
               pediments=("east", "west"), metopes={"+y": "amazon", "-y": "giant", "+x": "centaur", "-x": "troy"},
               frieze=True, roof="marble", akroteria="floral", door_glow=True, grilles=True, seed=101)
    temple(m, t, S, 1.0, 8 * T - 1.0, 1.0, 17 * T - 1.0)


# ---------------------------------------------------------------- the Propylaia

PROP_DORIC = Order("doric", D=1.56, H=8.81, upper=0.8, arch_h=1.15, frieze_h=1.2, geison_h=0.55, geison_out=0.75)
PROP_IONIC = Order("ionic", D=1.035, H=10.25, upper=0.84, flutes=24)
PINAK = Order("doric", D=1.02, H=5.85, upper=0.8, arch_h=0.8, frieze_h=0.85, geison_h=0.45, geison_out=0.6)
P_COLS = (56.0, 72.0, 88.0, 120.0, 136.0, 152.0)    # x of the six columns, the wide bay on tile dx 6
P_RISE = 6.0                                        # the floor rises this much to the east portico


P_EAST = 16.0                                       # the passage ramps down to the summit over this


def _prop_floor(y):
    """Floor of the central passage: level through the forecourt, a ramp up through the west
    hall to the gate wall, level in the east portico, and down again through its wide middle
    bay to the summit, so both ends meet the ground they open onto."""
    return float(min(np.clip((92.0 - y) / (92.0 - 40.0), 0, 1), np.clip(y / P_EAST, 0, 1)) * P_RISE)


def propylaia(m):
    """Mnesikles's gateway, left unfinished in 432: the central building with Doric hexastyle
    fronts west and east (the middle bay wide for the ramp and the animals), the west hall with
    two rows of three Ionic columns, the gate wall with five doorways, the higher east portico;
    the Pinakotheke (picture gallery) on the north-west with three columns in antis facing
    south, the truncated south-west wing facing north; the dark Eleusinian course; lifting
    bosses left on the wall blocks and plain uncut surfaces."""
    seed = 131
    zs = 3.9
    # West crepidoma: three steps, the central passage cut through as a ramp.
    for i in range(3):
        slab(m, 49.0, 159.0, 82.0, 95.0 - i * 1.3, i * 1.3, (i + 1) * 1.3, "marble",
             tone=M.plus(M.ashlar(1.3, 7.0, seed + i, spread=0.3), lambda X, Y, Z, i=i: 0.35 * (Z > (i + 1) * 1.3 - 0.5)))
    fill(m, (49.0, 159.0, 89.0, 91.2, zs - 1.3, zs), "eleusinian", tone=0.1, only_solid=True)   # the dark course
    carve(m, (96.0, 112.0, 80.0, 96.0, 0.0, zs + 0.1))
    # The passage floor (marble paving rising eastward) and the side floors.
    fill(m, (96.0, 112.0, 0.0, 96.0, 0.0, P_RISE + 0.5), "marble",
         lambda X, Y, Z: Z < np.minimum(np.clip((92.0 - Y) / 52.0, 0, 1), np.clip(Y / P_EAST, 0, 1)) * P_RISE + 0.01,
         tone=M.paving(8.0, 5.0, seed))
    slab(m, 49.0, 96.0, 40.0, 82.0, 0, zs, "marble", tone=M.paving(8.0, 6.0, seed + 1))
    slab(m, 112.0, 159.0, 40.0, 82.0, 0, zs, "marble", tone=M.paving(8.0, 6.0, seed + 2))
    slab(m, 49.0, 96.0, 0.0, 40.0, 0, P_RISE + zs, "marble", tone=M.ashlar(2.6, 8.0, seed + 3, spread=0.3))
    slab(m, 112.0, 159.0, 0.0, 40.0, 0, P_RISE + zs, "marble", tone=M.ashlar(2.6, 8.0, seed + 4, spread=0.3))
    zw, ze = zs, P_RISE + zs
    H = S.v(PROP_DORIC.H)
    # Side walls of the west hall and east portico.
    for w in ((49.0, 54.0, 40.0, 84.0), (154.0, 159.0, 40.0, 84.0)):
        marble_wall(m, *w, zw, zw + H + 6.0, seed=seed + 5, orthostate=4.0)
    for w in ((49.0, 54.0, 10.0, 40.0), (154.0, 159.0, 10.0, 40.0)):
        marble_wall(m, *w, ze, ze + H + 6.0, seed=seed + 6, orthostate=4.0)
    for face, w in (("+x", (154.0, 159.0, 10.0, 84.0)), ("-x", (49.0, 54.0, 10.0, 84.0))):
        bosses(m, face, (*w, 0, 0), zw + 4.0, zw + H, seed + 7)
    # The gate wall with five doorways (the central one for the ramp), steps through the others.
    gw = (49.0, 159.0, 36.0, 42.0)
    marble_wall(m, *gw, 0.0, ze + H + 6.0, seed=seed + 8, orthostate=5.0)
    bosses(m, "+y", (*gw, 0, 0), zw + 6.0, zw + H, seed + 9, share=0.3)
    doors = ((96.0, 112.0, 37.0), (61.0, 71.0, 30.0), (137.0, 147.0, 30.0), (76.0, 84.0, 22.0), (124.0, 132.0, 22.0))
    for x0, x1, h in doors:
        central = x0 == 96.0
        z0 = 0.0 if central else zw
        top = z0 + h + (P_RISE if central else 0.0)
        fill(m, (x0 - 1.4, x1 + 1.4, 42.0, 42.8, z0, top + 1.4), "marble", tone=0.25)     # the moulded frame
        carve(m, (x0, x1, 35.0, 43.0, z0, top))
        if not central:
            for i in range(5):     # five steps up through each side door
                slab(m, x0, x1, 36.0 + i * 1.2, 42.0, zw, zw + (i + 1) * (P_RISE / 5), "marble", tone=0.2 + 0.1 * (i % 2))
    fill(m, (96.0, 112.0, 35.0, 43.0, 0.0, P_RISE + 0.5), "marble",
         lambda X, Y, Z: Z < np.clip((92.0 - Y) / 52.0, 0, 1) * P_RISE + 0.01, tone=0.2)
    # West and east porticoes.
    for x in P_COLS:
        column(m, x, 86.0, zw, PROP_DORIC, S, seed=int(x) % 5)
        column(m, x, 8.0, ze, PROP_DORIC, S, seed=int(x + 3) % 5)
    # Two rows of three Ionic columns flanking the ramp in the west hall.
    hi = (zw + H + S.v(PROP_DORIC.arch_h + PROP_DORIC.frieze_h)) - zw - 1.0
    io = replace(PROP_IONIC, H=hi / 5.0)
    for x in (90.0, 118.0):
        for y in (50.0, 62.0, 74.0):
            column(m, x, y, zw, io, S, face="x")
    ent = PROP_DORIC
    rt = PROP_DORIC.r(S) * PROP_DORIC.upper + 0.3
    zg_w = doric_entablature(m, (48.0, 160.0, 86.0 - rt, 86.0 + rt), zw + H, ent, S, list(P_COLS), [86.0],
                             faces=("+y",), seed=seed + 10, geison=False)
    zg_e = doric_entablature(m, (48.0, 160.0, 8.0 - rt, 8.0 + rt), ze + H, ent, S, list(P_COLS), [8.0],
                             faces=("-y",), seed=seed + 11, geison=False)
    # Roofs: the west hall's lower gable, the east portico's higher one rising behind it.
    out = S.h(ent.geison_out)
    slab(m, 48.0, 160.0, 40.0, 86.0, zg_w - 6.0, zg_w, "marble", tone=-0.3)
    slab(m, 48.0, 160.0, 8.0, 42.0, zg_e - 6.0, zg_e, "marble", tone=-0.3)
    gw_top = geison_ring(m, (48.0, 160.0, 38.0, 86.0 + rt), zg_w, S.v(ent.geison_h), out, faces=("+x", "-x", "+y"))
    ge_top = geison_ring(m, (48.0, 160.0, 8.0 - rt, 42.0), zg_e, S.v(ent.geison_h), out, faces=("+x", "-x", "-y"))
    rise = S.v(2.6)
    tiled_roof(m, 48.0 - out, 160.0 + out, 38.0, 86.0 + rt + out, gw_top, rise, axis="y", seed=seed + 12)
    tiled_roof(m, 48.0 - out, 160.0 + out, 8.0 - rt - out, 42.0 + out, ge_top, rise, axis="y", seed=seed + 13)
    pediment(m, "+y", 48.0 - out, 160.0 + out, 38.0, 86.0 + rt + out, gw_top, rise, ent, S, subject=None)
    pediment(m, "-y", 48.0 - out, 160.0 + out, 8.0 - rt - out, 42.0 + out, ge_top, rise, ent, S, subject=None)
    # The east roof's west gable, seen above the west roof.
    pediment(m, "+y", 48.0 - out, 160.0 + out, 8.0 - rt - out, 42.0 + out, ge_top, rise, ent, S, subject=None,
             akroteria=None, sima=False)
    # The Pinakotheke: a room behind a porch of three columns in antis facing south.
    pz = 2.6
    crepidoma(m, 2.0, 79.0, 98.0, 158.0, 0.0, (1.3, 1.3), 0.0, "marble", seed + 14)
    fill(m, (2.0, 79.0, 98.0, 158.0, 1.3, 2.6), "eleusinian", tone=0.1, only_solid=True)
    hp = S.v(PINAK.H)
    for w in ((4.0, 60.0, 100.0, 104.0), (4.0, 60.0, 152.0, 156.0), (4.0, 8.0, 100.0, 156.0), (56.0, 60.0, 100.0, 156.0)):
        marble_wall(m, *w, pz, pz + hp + 4.0, seed=seed + 15, orthostate=3.0)
    for w in ((60.0, 76.0, 100.0, 104.0), (60.0, 76.0, 152.0, 156.0)):     # antae
        marble_wall(m, *w, pz, pz + hp + 4.0, seed=seed + 16, orthostate=3.0)
    carve(m, (55.0, 61.0, 116.0, 124.0, pz, pz + 18.0))                    # the door, and windows either side
    for y in (106.0, 140.0):
        carve(m, (55.0, 61.0, y, y + 6.0, pz + 7.0, pz + 15.0))
    for face, w in (("-y", (4.0, 76.0, 100.0, 104.0)), ("+y", (4.0, 76.0, 152.0, 156.0)), ("-x", (4.0, 8.0, 100.0, 156.0))):
        bosses(m, face, (*w, 0, 0), pz + 3.0, pz + hp + 2.0, seed + 17, share=0.45)
    rtp = PINAK.r(S) * PINAK.upper + 0.3
    for y in (113.0, 128.0, 143.0):
        column(m, 70.0, y, pz, PINAK, S, seed=int(y) % 5)
    zgp = doric_entablature(m, (4.0, 70.0 + rtp, 100.0, 156.0), pz + hp, PINAK, S, [70.0], [113.0, 128.0, 143.0],
                            faces=("+x",), seed=seed + 18)
    hip_roof(m, 4.0 - 2.0, 70.0 + rtp + 2.0, 98.0, 158.0, zgp, S.v(2.4), material="marble", seed=seed + 19)
    # The truncated south-west wing: a shallow porch facing north onto the forecourt.
    crepidoma(m, 129.0, 174.0, 98.0, 150.0, 0.0, (1.3, 1.3), 0.0, "marble", seed + 20)
    for w in ((158.0, 162.0, 100.0, 148.0), (134.0, 162.0, 144.0, 148.0), (134.0, 162.0, 100.0, 104.0)):
        marble_wall(m, *w, pz, pz + hp + 4.0, seed=seed + 21, orthostate=3.0)
    bosses(m, "+x", (158.0, 162.0, 100.0, 148.0, 0, 0), pz + 3.0, pz + hp + 2.0, seed + 22, share=0.45)
    for y in (113.0, 128.0):
        column(m, 136.0, y, pz, PINAK, S, seed=int(y) % 5)
    zgs = doric_entablature(m, (136.0 - rtp, 162.0, 100.0, 148.0), pz + hp, PINAK, S, [136.0], [113.0, 128.0],
                            faces=("-x",), seed=seed + 23)
    hip_roof(m, 136.0 - rtp - 2.0, 164.0, 98.0, 150.0, zgs, S.v(2.0), material="marble", seed=seed + 24)


def _propylaia_landmark():
    walk = [(6, dy) for dy in range(10)] + tiles(5, 7, 6, 9) + tiles(0, 2, 0, 5) + [(10, dy) for dy in range(6)]
    walk = sorted(set(walk))
    # A passage tile's floor where it is highest; the east tile's at its middle (the ramp down).
    floor = {t: (_prop_floor(t[1] * T + (T / 2 if t[1] == 0 else 0.0)) if t[0] == 6 and t[1] <= 5 else 0.0)
             for t in walk}
    return Landmark((11, 10), (0, 96), ref("propylaia"), walk=walk, floor=floor,
                    slots={"mnesikles": [{"t": [7, 7], "face": "-y"}], "guard": [{"t": [6, 9], "face": "+y"}]},
                    district=1)


# ---------------------------------------------------------------- the Nike bastion

def nike_bastion(m):
    """The bastion (pyrgos) before the Ionic temple was built: a poros parapet round the top,
    the small old poros naiskos of Athena Nike in antis with its tiled roof, and its altar."""
    seed = 141
    for w in ((0.0, 80.0, 0.0, 2.5), (77.5, 80.0, 0.0, 64.0), (0.0, 80.0, 61.5, 64.0)):
        poros_wall(m, *w, 0.0, 5.0, seed)
        slab(m, w[0] - 0.3, w[1] + 0.3, w[2] - 0.3, w[3] + 0.3, 5.0, 5.8, "poros", tone=0.3)
    # The naiskos: a little cella with two columns in antis facing east.
    small = Order("doric", D=0.5, H=2.8, upper=0.8, arch_h=0.4, frieze_h=0.45, geison_h=0.25, geison_out=0.4,
                  material="poros")
    crepidoma(m, 26.0, 50.0, 26.0, 56.0, 0.0, (1.0, 1.0), 0.8, "poros", seed)
    for w in ((28.0, 30.0, 30.0, 54.0), (46.0, 48.0, 30.0, 54.0), (28.0, 48.0, 52.0, 54.0), (28.0, 48.0, 36.0, 38.0)):
        house_wall(m, *w, 2.0, 2.0 + S.v(2.8), seed=seed + 1, socle=1.4, plaster="whitewash", socle_mat="poros")
    carve(m, (34.0, 42.0, 35.0, 39.0, 2.0, 14.0))
    fill(m, (34.0, 42.0, 37.5, 38.2, 2.0, 14.0), "cedar", tone=-0.2)
    for x in (34.0, 42.0):
        column(m, x, 31.0, 2.0, small, S)
    zg = doric_entablature(m, (27.5, 48.5, 29.0, 54.5), 2.0 + S.v(small.H), small, S, [34.0, 42.0], [31.0],
                           faces=("-y", "+y", "+x", "-x"), seed=seed + 2, paint=True)
    tiled_roof(m, 26.5, 49.5, 28.0, 56.0, zg, 4.0, axis="y", material="terracotta", kind="laconian", seed=seed + 3)
    pediment(m, "-y", 26.5, 49.5, 28.0, 56.0, zg, 4.0, small, S, subject=None)
    pediment(m, "+y", 26.5, 49.5, 28.0, 56.0, zg, 4.0, small, S, subject=None, akroteria=None)
    altar(m, 38.0, 16.0, 0.0, 8.0, 5.0, 3.0, fire=False, material="poros")
    statue_base(m, 60.0, 50.0, 0.0, 5.0, 4.0, material="marble")


# ---------------------------------------------------------------- the approach ramp

RAMP_RISE = 9 * 8.0               # nine levels of 16 px


def approach(m):
    """The broad gravel ramp climbing east to the Propylaia between poros retaining walls with
    parapets; worn wheel and hoof lanes, stone kerbs, the sacrificial animals' dung swept to
    the sides."""
    seed = 151
    L = 14 * T

    def top(Y):
        return np.clip((L - Y) / L, 0, 1) * RAMP_RISE

    # The ramp body (rubble fill faced with poros) and its surface of trodden gravel, a paler
    # lane worn up the middle by the processions, wheel ruts, scattered stones.
    fill(m, (8.0, 104.0, 0.0, L, 0.0, RAMP_RISE + 1.0), "poros", lambda X, Y, Z: Z < top(Y) - 1.0,
         tone=M.ashlar(2.6, 6.0, seed, joint=0.35, spread=0.7, polygonal=0.5))

    def gravel(X, Y, Z):
        n = (value_noise(X * 0.5, Y * 0.5, Z, 6.0, seed) - 0.5) * 0.8
        grain = (value_noise(X * 4, Y * 4, Z * 4, 1.0, seed + 1) - 0.5) * 0.9
        lane = 0.45 * np.clip(1 - np.abs(X - 56.0) / 18.0, 0, 1)
        ruts = -0.6 * ((np.abs(X - 44.0) < 0.8) | (np.abs(X - 68.0) < 0.8))
        return n + grain + lane + ruts
    fill(m, (16.0, 96.0, 0.0, L, 0.0, RAMP_RISE + 1.0), "gravel",
         lambda X, Y, Z: (Z >= top(Y) - 1.0) & (Z < top(Y)), tone=gravel)
    # QA4 V-A-007: the ramp read as one plank. Cross ribs of poros set into the gravel every
    # few metres give footing to the sacrificial animals and carry the climb's rhythm; kerb
    # stones line the lanes; the trodden lane is paler between darker margins.
    for y in np.arange(6.0, L - 2.0, 7.0):
        fill(m, (18.0, 94.0, y - 0.7, y + 0.7, 0.0, RAMP_RISE + 1.6), "poros",
             lambda X, Y, Z: (Z >= top(Y) - 1.0) & (Z < top(Y) + 0.4),
             tone=lambda X, Y, Z: 0.3 * ((X % 5.0) > 0.4) - 0.2)
    for x in (18.0, 94.0):
        fill(m, (x - 1.2, x + 1.2, 0.0, L, 0.0, RAMP_RISE + 2.0), "poros",
             lambda X, Y, Z: (Z >= top(Y) - 1.0) & (Z < top(Y) + 0.9),
             tone=M.ashlar(0.9, 3.2, seed + 3, joint=0.4, spread=0.8))
    fill(m, (16.0, 96.0, 0.0, L, 0.0, RAMP_RISE + 1.0), "gravel",
         lambda X, Y, Z: (Z >= top(Y) - 0.5) & (Z < top(Y)) & (np.abs(X - 56.0) > 26.0),
         tone=lambda X, Y, Z: gravel(X, Y, Z) - 0.45, only_solid=True)
    # Retaining walls with parapets along both sides.
    for x0, x1 in ((0.0, 16.0), (96.0, 112.0)):
        fill(m, (x0 + 4.0, x1 - 4.0, 0.0, L, 0.0, RAMP_RISE + 6.0), "poros",
             lambda X, Y, Z: Z < top(Y) + 4.0, tone=M.ashlar(2.6, 7.0, seed + 1, joint=0.35, spread=0.6, polygonal=0.4))
        fill(m, (x0 + 3.6, x1 - 3.6, 0.0, L, 0.0, RAMP_RISE + 7.0), "poros",
             lambda X, Y, Z: (Z >= top(Y) + 4.0) & (Z < top(Y) + 4.8), tone=0.3)
    # Statue bases on the parapets (dedications line the way), a base at the foot.
    statue_base(m, 56.0, L - 6.0, 0.0, 6.0, 3.0)
    for i, y in enumerate((30.0, 90.0, 150.0, 200.0)):
        for x in (8.0, 104.0):
            zt = float(top(np.float32(y))) + 4.8
            slab(m, x - 2.6, x + 2.6, y - 2.6, y + 2.6, zt, zt + 3.0, "marble", tone=M.ashlar(1.5, 2.6, seed + 9 + i))
            herm(m, x, y, zt + 3.0, h=8.0, face="+y" if x > 56 else "-y")


def _approach_landmark():
    walk = tiles(1, 5, 0, 13)
    L = 14 * T
    # Each tile's floor at its middle, so the foot tile is half a tread above the street (≤ 8 px).
    floor = {(x, y): float(np.clip((L - (y + 0.5) * T) / L, 0, 1) * RAMP_RISE) for x, y in walk}
    return Landmark((7, 14), (0, int(RAMP_RISE) + 10), ref("approach"), walk=walk, floor=floor,
                    slots={"stand": [{"t": [3, 12]}, {"t": [2, 6]}, {"t": [4, 2]}]}, district=1, climb="-y")


# ---------------------------------------------------------------- the Old Temple

def old_temple(m):
    """The Old Temple of Athena after the Persian sack (its state is debated; the bible chooses
    this): the poros foundations of the whole temple low on the rock, cross walls of the cella
    showing, column drums lying where they fell, and the western chamber rebuilt in poros and
    roofed with terracotta tiles, its door to the west."""
    seed = 161
    W, Lh = 6 * T, 11 * T
    crepidoma(m, 4.0, W - 4.0, 4.0, Lh - 4.0, 0.0, (2.0, 2.0), 2.0, "poros", seed)
    for x0, x1 in ((22.0, 26.0), (70.0, 74.0)):
        poros_wall(m, x0, x1, 18.0, Lh - 18.0, 4.0, 7.0, seed + 1)
    for y in (40.0, 92.0, 116.0):
        poros_wall(m, 22.0, 74.0, y, y + 4.0, 4.0, 7.0, seed + 2)
    for i, (x, y) in enumerate(((10.0, 30.0), (12.0, 70.0), (86.0, 50.0), (84.0, 96.0), (40.0, 14.0), (60.0, 12.0))):
        drum(m, x, y, 4.0, 3.4, 5.0, lying=i % 2 == 0, material="poros", along="y" if i % 3 else "x")
    # The repaired west chamber.
    ch = S.v(3.2)
    for w in ((22.0, 26.0, 118.0, 160.0), (70.0, 74.0, 118.0, 160.0), (22.0, 74.0, 156.0, 160.0), (22.0, 74.0, 118.0, 122.0)):
        poros_wall(m, *w, 4.0, 4.0 + ch, seed + 3)
    carve(m, (42.0, 54.0, 155.0, 161.0, 4.0, 18.0))
    fill(m, (42.0, 54.0, 157.0, 158.0, 4.0, 18.0), "cedar", tone=lambda X, Y, Z: -0.4 * ((X % 2.0) < 0.3))
    for x in (34.0, 62.0):
        carve(m, (x - 2, x + 2, 155.0, 161.0, 18.0, 22.0))
    slab(m, 20.0, 76.0, 116.0, 162.0, 4.0 + ch, 4.0 + ch + 1.5, "poros", tone=0.2)
    tiled_roof(m, 18.0, 78.0, 114.0, 164.0, 4.0 + ch + 1.5, 7.0, axis="y", material="terracotta", kind="laconian",
               seed=seed + 4)
    for face in ("-y", "+y"):
        pediment(m, face, 18.0, 78.0, 114.0, 164.0, 4.0 + ch + 1.5, 7.0, Order(material="poros"), S, subject=None,
                 akroteria=None)


# ---------------------------------------------------------------- the Pandroseion, the bronze Athena

def pandroseion(m):
    """The walled court round Athena's sacred olive: low walls, a small stoa on the west side,
    the gnarled olive in the middle, the tomb of Kekrops as a low enclosure at the corner."""
    seed = 171
    for w in ((0.0, 64.0, 0.0, 2.0), (62.0, 64.0, 0.0, 64.0), (0.0, 2.0, 0.0, 64.0)):
        house_wall(m, *w, 0.0, 9.0, seed=seed, socle=3.0, plaster="whitewash")
    small = Order("doric", D=0.5, H=3.2, upper=0.82, arch_h=0.45, frieze_h=0.5, geison_h=0.3, geison_out=0.4,
                  material="poros")
    house_wall(m, 2.0, 62.0, 60.0, 64.0, 0.0, S.v(4.2), seed=seed + 1, socle=2.0, plaster="whitewash")
    for x in (10.0, 22.0, 34.0, 46.0, 56.0):
        column(m, x, 52.0, 0.0, small, S)
    zg = doric_entablature(m, (4.0, 60.0, 50.5, 64.0), S.v(small.H), small, S, [10.0, 22.0, 34.0, 46.0, 56.0],
                           [52.0], faces=("-y",), seed=seed + 2)
    tiled_roof(m, 2.0, 62.0, 48.0, 64.0, zg, 3.0, axis="x", material="terracotta", kind="laconian", seed=seed + 3)
    olive_tree(m, 30.0, 26.0, 0.0, h=34.0, seed=seed, spread=1.6, gnarled=1.6)
    fill(m, (14.0, 46.0, 10.0, 42.0, 0.0, 1.2), "poros", lambda X, Y, Z: np.abs(np.hypot(X - 30, Y - 26) - 13.0) < 1.2,
         tone=0.2)
    # Kekrops's tomb: a low precinct of slabs in the north-east corner.
    for w in ((3.0, 16.0, 3.0, 4.5), (3.0, 4.5, 3.0, 16.0), (14.5, 16.0, 3.0, 16.0), (3.0, 16.0, 14.5, 16.0)):
        slab(m, *w, 0.0, 3.0, "marble", tone=0.2)


def promachos(m):
    """Pheidias's colossal bronze Athena (c. 460-450, about 9 m: estimates vary) on its tall
    moulded base: helmet with a gilded crest, aegis, the spear upright in her right hand with
    its tip catching the sun, the shield resting against her left side."""
    zb = statue_base(m, 16.0, 16.0, 0.0, 20.0, 9.0, steps=2)
    bronze_statue(m, ATHENA, 16.0, 16.0, zb, S.v(8.6), keep=("gold", "metal"))
    halo(m, 17.0, 16.0, zb + S.v(8.6) * 1.55, 6.0, (255, 235, 164), 0.5)


def great_altar(m):
    """The Great Altar of Athena: a long stone altar on a stepped base with its fire, where the
    hecatomb of the Panathenaia is offered."""
    altar(m, 24.0, 24.0, 0.0, 26.0, 16.0, 6.0, fire=True)
    for x in (6.0, 42.0):
        rod(m, (x, 6.0, 0.0), (x, 6.0, 9.0), 0.5, "wood")          # tethering posts for the victims
        rod(m, (x, 42.0, 0.0), (x, 42.0, 9.0), 0.5, "wood")


# ---------------------------------------------------------------- the sculptors' yard

def sculpt_yard(m):
    """The masons' and sculptors' yard east of the Parthenon as the last pediment figures are
    finished: big Pentelic blocks with their bosses stacked in rows, column drums, a two-legged
    crane lifting a block onto a waiting cart bed, scaffold poles stacked from the dismantled
    pediment scaffolds, a reed-roofed shed with workbenches, a roughed-out horse's head from a
    pediment team, a seated figure being finished, and drifts of marble chips by each work place."""
    seed = 181

    def chips(cx, cy, r):
        fill(m, (cx - r, cx + r, cy - r, cy + r, 0.0, 0.7), "marble_rough",
             lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < r * (0.6 + 0.4 * value_noise(X, Y, Z, 3.0, seed))) &
             (value_noise(X * 2, Y * 2, Z, 1.0, seed + 1) > 0.42), tone=0.35)
    for cx, cy, r in ((24.0, 40.0, 12.0), (118.0, 28.0, 10.0), (150.0, 22.0, 9.0), (40.0, 108.0, 10.0)):
        chips(cx, cy, r)
    big = (10.0, 7.0, 6.0)
    rows = ((4.0, 4.0, 2), (4.0, 20.0, 3), (36.0, 4.0, 2), (52.0, 6.0, 1), (100.0, 4.0, 3), (124.0, 6.0, 1),
            (150.0, 36.0, 2), (148.0, 118.0, 3), (148.0, 100.0, 2), (4.0, 118.0, 2), (128.0, 132.0, 1))
    for i, (x, y, n) in enumerate(rows):
        blocks(m, x, y, 0.0, n, seed + i, size=big)
    for i, (x, y) in enumerate(((72.0, 122.0), (88.0, 128.0), (104.0, 124.0), (116.0, 136.0))):
        drum(m, x, y, 0.0, 7.0, 5.0, lying=i == 2)
    crane(m, 88.0, 70.0, 0.0, 60.0, along="x")
    slab(m, 92.0, 108.0, 58.0, 66.0, 0.0, 3.0, "wood", tone=M.timber("x", seed))          # the cart bed under it
    scaffold(m, 40.0, 60.0, 92.0, 102.0, 0.0, 30.0, decks=2)
    for i in range(8):     # stacked poles
        rod(m, (114.0, 74.0 + i * 1.6, 1.0 + (i % 3) * 1.4), (164.0, 76.0 + i * 1.6, 1.0 + (i % 3) * 1.4), 0.8, "wood")
    # The shed: posts and a reed roof over benches, tools and a figure being finished.
    for x, y in ((6.0, 58.0), (6.0, 94.0), (34.0, 58.0), (34.0, 94.0)):
        rod(m, (x, y, 0.0), (x, y, 22.0), 0.8, "wood")
    fill(m, (4.0, 36.0, 56.0, 96.0, 21.5, 23.0), "straw", tone=lambda X, Y, Z: -0.35 * ((Y * 2.0) % 1.0 < 0.3))
    slab(m, 10.0, 28.0, 62.0, 66.0, 0.0, 6.0, "wood", tone=M.timber("y", seed))
    blocks(m, 12.0, 72.0, 0.0, 1, seed + 20, size=(10.0, 8.0, 5.0))
    # A horse's head from a pediment team, roughed out on its block.
    ellipsoid(m, (18.0, 77.0, 10.0), (3.2, 5.0, 3.6), "marble", tone=0.3)
    ellipsoid(m, (18.0, 82.5, 8.5), (2.2, 3.0, 2.4), "marble", tone=0.25)
    rod(m, (18.0, 74.0, 12.0), (18.0, 73.0, 16.0), 1.2, "marble", tone=0.2)
    # A draped seated figure being finished, still on its working block.
    bronze_statue(m, Dress(body="woman", garment="chiton_long", mantle="marble", colour="marble", skin="marble",
                           hair="marble", beard="none", hair_style="knot", feet="bare"), 132.0, 60.0, 5.0, 16.0,
                  anim="sit", keep=(), material="marble")
    blocks(m, 126.0, 54.0, 0.0, 1, seed + 21, size=(12.0, 12.0, 5.0), bosses=False)
def _sculpt_landmark():
    blocked = {(0, 0), (0, 1), (2, 0), (3, 0), (6, 0), (7, 0), (8, 0), (9, 2), (9, 6), (9, 7), (0, 7), (8, 8),
               (4, 7), (4, 8), (5, 7), (5, 8), (6, 7), (6, 8), (7, 8), (5, 3), (5, 4), (6, 3), (6, 4),
               (2, 5), (3, 5), (2, 6), (3, 6), (7, 3), (8, 3), (7, 4), (8, 4), (10, 2)} | \
        set(tiles(7, 10, 4, 5)) | set(tiles(0, 2, 3, 5))
    walk = [t for t in tiles(0, 10, 0, 8) if t not in blocked]
    return Landmark((11, 9), (0, 72), ref("sculpt_yard"), walk=walk,
                    slots={"carve": [{"t": [1, 2], "face": "-x"}, {"t": [7, 1], "face": "-y"}, {"t": [9, 1], "face": "-x"}],
                           "hoist": [{"t": [4, 3], "face": "+x"}, {"t": [4, 4], "face": "+x"}],
                           "pheidias": [{"t": [1, 6], "face": "-x"}]},
                    emitters={"dust": (24.0, 40.0, 3.0)}, district=1)


# ---------------------------------------------------------------- smaller sanctuaries (N)

def brauronion(m):
    """The sanctuary of Artemis Brauronia: a stoa with two projecting wings facing north onto
    its court, plastered walls on poros footings, terracotta roofs; votive clothes inside."""
    seed = 191
    W, Lh = 6 * T, 9 * T
    small = Order("doric", D=0.62, H=4.2, upper=0.8, arch_h=0.55, frieze_h=0.6, geison_h=0.35, geison_out=0.5,
                  material="poros")
    hb = S.v(small.H) + 6.0
    house_wall(m, 70.0, 80.0, 6.0, Lh - 6.0, 0.0, hb, seed, socle=3.0)                # back (south) wall
    for y0, y1 in ((6.0, 30.0), (Lh - 30.0, Lh - 6.0)):                             # the wings
        house_wall(m, 30.0, 80.0, y0, y0 + 3.0, 0.0, hb, seed + 1, socle=3.0)
        house_wall(m, 30.0, 80.0, y1 - 3.0, y1, 0.0, hb, seed + 1, socle=3.0)
        house_wall(m, 30.0, 33.0, y0, y1, 0.0, hb, seed + 2, socle=3.0)
        carve(m, (29.0, 34.0, (y0 + y1) / 2 - 3, (y0 + y1) / 2 + 3, 0.0, 12.0))
        tiled_roof(m, 28.0, 82.0, y0 - 2, y1 + 2, hb, 6.0, axis="x", material="terracotta", kind="laconian",
                   seed=seed + int(y0))
    cols = [44.0 + i * 11.0 for i in range(6)]
    for y in cols:
        column(m, 50.0, y, 0.0, small, S)
    zg = doric_entablature(m, (48.0, 80.0, 30.0, Lh - 30.0), S.v(small.H), small, S, [50.0], cols, faces=("-x",),
                           seed=seed + 3)
    tiled_roof(m, 46.0, 82.0, 28.0, Lh - 28.0, zg, 5.0, axis="y", material="terracotta", kind="laconian",
               seed=seed + 4)
    statue_base(m, 16.0, Lh / 2, 0.0, 6.0, 4.0)


def chalkotheke(m):
    """The Chalkotheke, the store for bronze dedications: a long plain hall of poros and
    plaster under a tiled roof, a door and small high windows."""
    seed = 201
    W, Lh = 4 * T, 7 * T
    hb = 28.0
    for w in ((8.0, 12.0, 4.0, Lh - 4.0), (52.0, 56.0, 4.0, Lh - 4.0), (8.0, 56.0, 4.0, 8.0), (8.0, 56.0, Lh - 8.0, Lh - 4.0)):
        house_wall(m, *w, 0.0, hb, seed=seed, socle=4.0, plaster="whitewash")
    carve(m, (51.0, 57.0, 50.0, 60.0, 0.0, 16.0))
    fill(m, (55.0, 56.0, 50.0, 60.0, 0.0, 16.0), "cedar", tone=-0.2)
    for y in (20.0, 36.0, 76.0, 92.0):
        carve(m, (51.0, 57.0, y, y + 3.0, 21.0, 25.0))
    tiled_roof(m, 5.0, 59.0, 1.0, Lh - 1.0, hb, 8.0, axis="y", material="terracotta", seed=seed + 1)
    for face in ("-y", "+y"):
        pediment(m, face, 5.0, 59.0, 1.0, Lh - 1.0, hb, 8.0, Order(material="poros"), S, subject=None, akroteria=None)
    for i in range(3):     # bronze votives waiting outside: a tripod, a shield, a statue
        x, y = 62.0, 30.0 + i * 24.0
        if i == 0:
            for a in (0.0, 2.1, 4.2):
                rod(m, (x + 2.0 * np.cos(a), y + 2.0 * np.sin(a), 0.0), (x, y, 7.0), 0.3, "bronze")
            ellipsoid(m, (x, y, 8.0), (2.6, 2.6, 1.6), "bronze", tone=0.3)
        elif i == 1:
            stele(m, x, y, 0.0, 5.0, 10.0, face="+x", subject="decree")


def zeus_polieus(m):
    """The sanctuary of Zeus Polieus: a walled precinct with the altar of the Dipolieia (the ox
    sacrifice) and a small building for the sacred oxen and the priest's gear."""
    seed = 211
    for w in ((0.0, 80.0, 0.0, 2.0), (78.0, 80.0, 0.0, 80.0), (0.0, 2.0, 0.0, 80.0), (0.0, 80.0, 78.0, 80.0)):
        house_wall(m, *w, 0.0, 8.0, seed, socle=3.0, plaster="whitewash")
    carve(m, (74.0, 81.0, 34.0, 44.0, 0.0, 8.0))
    altar(m, 44.0, 40.0, 0.0, 12.0, 8.0, 4.0, fire=False)
    for w in ((6.0, 30.0, 6.0, 9.0), (6.0, 30.0, 33.0, 36.0), (6.0, 9.0, 6.0, 36.0), (27.0, 30.0, 6.0, 36.0)):
        house_wall(m, *w, 0.0, 18.0, seed + 1, socle=3.0)
    tiled_roof(m, 4.0, 32.0, 4.0, 38.0, 18.0, 5.0, axis="y", material="terracotta", kind="laconian", seed=seed + 2)
    olive_tree(m, 60.0, 64.0, 0.0, h=20.0, seed=3)


LANDMARKS = {
    "athens.parthenon": Landmark((8, 17), (0, 118), ref("parthenon"), district=1),
    "athens.propylaia": _propylaia_landmark(),
    "athens.nike_bastion": Landmark((5, 4), (0, 40), ref("nike_bastion"),
                                    slots={"pray": [{"t": [2, -1], "face": "+y"}]}, district=1),
    "athens.approach": _approach_landmark(),
    "athens.old_temple": Landmark((6, 11), (0, 48), ref("old_temple"),
                                  slots={"priestess": [{"t": [-1, 9], "face": "+x"}]}, district=1),
    "athens.pandroseion": Landmark((4, 4), (0, 48), ref("pandroseion"),
                                   slots={"tend": [{"t": [4, 2], "face": "-x"}]}, district=1),
    "athens.promachos": Landmark((2, 2), (0, 100), ref("promachos"), district=1),
    "athens.great_altar": Landmark((3, 3), (0, 20), ref("great_altar"),
                                   slots={"sacrifice": [{"t": [1, 3], "face": "-y"}, {"t": [3, 1], "face": "-x"}]},
                                   emitters={"fire": (24.0, 24.0, 12.0)}, district=1),
    "athens.sculpt_yard": _sculpt_landmark(),
    "athens.brauronion": Landmark((6, 9), (0, 40), ref("brauronion"), district=1),
    "athens.chalkotheke": Landmark((4, 7), (0, 40), ref("chalkotheke"), district=1),
    "athens.zeus_polieus": Landmark((5, 5), (0, 32), ref("zeus_polieus"), district=1),
}
