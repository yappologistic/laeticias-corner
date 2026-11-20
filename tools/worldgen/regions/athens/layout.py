"""Athens at the Panathenaia, summer 432 BC (docs/design/cities/athens.md).

World rect C 576..735, R 220..379; local (c, r) = world (C - 576, R - 220); local level 0 =
world level 1 (the Agora). The Acropolis rises in the middle of the walled city as a craggy
limestone rock: a plateau at 10 with sheer faces north and south, a ledge for the Peripatos, the
approach ramp climbing its west end to the unfinished Propylaia. The Agora lies north-west of it
under Kolonos Agoraios, the Kerameikos with the Dipylon and the Sacred Gate in the north-west
corner, the Pnyx and the Hill of the Nymphs on the west hills, the Mouseion to the south-west.
The Long Walls run from the city wall south-west to Piraeus (a satellite in the south-west corner:
Kantharos, Zea and Mounychia on the Saronic Gulf); the Pentelikon quarries are a satellite in the
north-east corner, Lykabettos and the Lyceum lie outside the east wall, the Ilissos with the
Olympieion and the Kallirrhoe outside the south-east wall, farms and olive groves all round.

Order of the build: levels (as one array, stair runs carved into it), ground, water, ways,
landmarks and stairs, walls, districts, quarters and their fillers, country, detail, finishing.
Coordinates are the bible's (§2.2-§2.6) unless a comment says why they differ.
"""

import numpy as np

from worldgen import rng
from worldgen.dsl import Layout
from worldgen.finish import (clear_doors, crossings, fit_faces, fords, glow_cap, night_posts,
                             orth, put, seam, stairstep)
from worldgen.shapes import Ellipse, Line, Mask, Poly, Rect

N = 160
A = "athens."
GRASS, ROCK, MARBLE, GRAVEL = A + "dry_grass", A + "rock_limestone", A + "marble_paving", A + "gravel"
EARTH, STUBBLE, OLIVE_SOIL, BED = A + "packed_earth", A + "field_stubble", A + "olive_soil", A + "riverbed"
SEA, SHALLOWS = "world.sea", "world.shallows"
LIME, ASHLAR, EARTHF = A + "limestone", A + "ashlar", A + "earth"
STAIR, RAMP = A + "stair_marble", "world.ramp"

# --- the Acropolis -----------------------------------------------------------------------------
# The plateau (level 10) holds every D1 landmark with a rim of a tile or two; its outline follows
# the rock (longer west-east, the west end narrowed by the Propylaia), not the district's rect.
PLATEAU = Poly([(63, 85), (64, 81), (68, 78), (76, 77), (84, 76), (96, 75), (108, 76),
                (118, 76), (123, 79), (125, 84), (125, 91), (124, 96), (122, 99), (114, 101),
                (104, 102), (95, 103), (86, 102), (77, 101), (72, 97), (72, 92), (63, 91)])
LANDING = Rect(62, 86, 65, 90)          # the approach's head before the Propylaia (level 10)
BASTION = Rect(62, 91, 65, 95)          # Nike bastion (level 9)
NIKE_TERRACE = Rect(66, 92, 71, 96)     # under the Propylaia's south-west wing (level 9)
APPROACH = Rect(48, 86, 61, 92)
THEATRE = Rect(104, 104, 118, 120)
ODEION = Rect(120, 102, 132, 115)

# --- the lower city ----------------------------------------------------------------------------
AGORA = Rect(20, 26, 52, 62)
KOLONOS = Ellipse(12, 45, 7, 13)
AREOPAGUS = Ellipse(51, 75, 6, 6)
NYMPHS = Ellipse(11, 77, 5, 7)
MOUSEION = Ellipse(42, 121, 8, 9)
LYKABETTOS = Ellipse(154, 33, 7, 8)
PLOT = Rect(34, 66, 44, 76)             # the decorate zone (bible §10)

# The Themistoclean wall, clockwise from the Dipylon (bible §2.5). Streets are laid first, so
# every street the wall meets leaves a gate gap; towers flank the gates.
CITY_WALL = [
    [(15, 6), (42, 6), (43, 7), (72, 7), (73, 6), (100, 6), (108, 7), (116, 9), (126, 12),
     (136, 16), (142, 19), (145, 22), (145, 110), (140, 114), (135, 118), (131, 121),
     (127, 124), (127, 131), (122, 135), (118, 136), (96, 137), (80, 137), (64, 138), (52, 138),
     (46, 134), (41, 129), (36, 123), (33, 117), (31, 112), (29, 108), (28, 106), (4, 106),
     (3, 105), (3, 19)],
    [(4, 13), (6, 13), (7, 12)],          # Sacred Gate to the Dipylon
]
LONG_N = [(5, 107), (4, 118), (2, 130)]  # the North Long Wall (to Piraeus)
LONG_M = [(16, 107), (14, 118), (12, 130)]  # the Middle Long Wall
# Piraeus' landward wall, and round Mounychia to the shore east of its harbour.
PIRAEUS_WALL = [(0, 131), (38, 131), (38, 140), (54, 140), (57, 144), (57, 152)]

# --- Piraeus -----------------------------------------------------------------------------------
HARBOUR = Rect(2, 141, 19, 150)          # Kantharos quay and emporion (quay on its south side)
SHEDS = Rect(23, 141, 38, 146)           # Zea ship sheds (slipways open to the south)
KANTHAROS = Rect(1, 151, 19, 157) | Ellipse(10, 154, 11, 3) | Rect(8, 158, 14, 159)
ZEA = Ellipse(31, 151, 8, 4) | Rect(23, 147, 38, 151) | Rect(28, 154, 33, 159)
MOUNYCHIA_HILL = Ellipse(47, 146, 6, 5)
MOUNYCHIA = Ellipse(51, 156, 4, 3) | Rect(49, 157, 53, 159)

ILISSOS = [(159, 118), (150, 121), (140, 123), (131, 125), (131, 139), (125, 145), (118, 151),
           (112, 159)]
ERIDANOS = [(56, 30), (48, 29), (42, 27), (41, 24), (33, 21), (22, 18), (8, 17)]


def build(L: Layout) -> None:
    cc, rr = np.meshgrid(np.arange(N), np.arange(N))

    def noise(scale, key, octaves=3):
        return rng.fbm(cc + L.origin[0], rr + L.origin[1], scale, rng.hash64("athens", key),
                       octaves=octaves)

    lv, rock, ashlar, runs = _levels(L, cc, rr, noise)
    _ground(L, lv, rock, ashlar, cc, rr, noise)
    _water(L)
    ways = _ways(L, lv)
    _landmarks(L)
    for run in runs:
        _build_run(L, run)
    _walls(L)
    inside = _districts(L)
    _agora(L)
    _acropolis_detail(L)
    _quarters(L, ways, inside, noise)
    _kerameikos(L, noise)
    _piraeus(L, noise)
    _country(L, inside, noise)
    _night(L, inside)
    _nodes(L)
    clear_doors(L, all_slots=True)
    glow_cap(L, {A + "g_house_small": 0, A + "g_house_two": 1, A + "g_house": 2,
                 A + "g_workshop": 3, A + "g_shrine": 4, A + "g_brazier": 5})
    seam(L, GRASS, STUBBLE)
    fit_faces(L, LIME)
    _views(L)


# =============================================================================================
# 1. Levels
# =============================================================================================

def _m(shape) -> np.ndarray:
    return shape.mask(0, 0, N, N)


def _dist(src: np.ndarray, limit: int = 24) -> np.ndarray:
    """Steps from a mask, alternating 4- and 8-neighbour growth (an octagonal distance)."""
    d = np.full(src.shape, limit, dtype=np.int32)
    d[src] = 0
    cur = src.copy()
    for k in range(1, limit):
        g = cur.copy()
        g[1:, :] |= cur[:-1, :]
        g[:-1, :] |= cur[1:, :]
        g[:, 1:] |= cur[:, :-1]
        g[:, :-1] |= cur[:, 1:]
        if k % 2 == 0:
            g[1:, 1:] |= cur[:-1, :-1]
            g[:-1, :-1] |= cur[1:, 1:]
            g[1:, :-1] |= cur[:-1, 1:]
            g[:-1, 1:] |= cur[1:, :-1]
        d[g & ~cur] = k
        cur = g
    return d


# Stair and ramp runs: (item, foot tile, face, rise, level at the foot, width, name). A run climbs
# away from its foot (on the `face` side): each flight stands at its lower level, the tile after
# it is the landing one level up and the next flight's foot.
RUNS = [
    (STAIR, (21, 36), "east", 2, 0, 2, "kolonos_steps"),
    (STAIR, (56, 83), "south", 3, 0, 1, "areopagus_steps"),
    (STAIR, (56, 74), "east", 2, 3, 1, "areopagus_steps_top"),
    (STAIR, (30, 74), "north", 4, 0, 2, "pnyx_path"),
    (STAIR, (30, 96), "north", 2, 4, 1, "meton_steps"),
    (STAIR, (70, 94), "south", 1, 9, 1, "nike_steps"),
    (STAIR, (128, 100), "south", 5, 0, 1, "peripatos_east"),
    # A broad marble flight at the approach's foot (the city's own piece: no plank ramp in the
    # view of the Propylaia, V15).
    (STAIR, (41, 89), "west", 1, 0, 3, "approach_steps"),
    (STAIR, (40, 146), "west", 4, 0, 1, "mounychia_steps"),
    (RAMP, (4, 5), "south", 1, 0, 1, "academy_road_ramp"),
    (RAMP, (153, 45), "north", 1, 0, 1, "lyceum_ramp"),
    # The quarry road climbs Pentelikon's foot in two legs of three ramps (bible: rise 6 over
    # 30 tiles): east along r 3..4 to a bend at 3, then east again along r 8..9 to the quarry's
    # lip (6). The hillside is shaped to the road, so each flight cuts one of its scarps.
    (RAMP, (111, 3), "west", 3, 0, 2, "quarry_road"),
    (RAMP, (124, 8), "west", 3, 3, 2, "quarry_road_upper"),
]
STEP = {"west": (-1, 0), "north": (0, -1), "east": (1, 0), "south": (0, 1)}
SIDE = {"west": (0, 1), "east": (0, 1), "north": (1, 0), "south": (1, 0)}


def _run_tiles(run):
    """[(flight rects, landing tiles, level)] of a run, in climbing order."""
    item, (fc, fr), face, rise, lvl0, width, _name = run
    dc, dr = STEP[face]
    ac, ar = -dc, -dr                      # climbing direction
    pc, pr = SIDE[face]
    length = 2 if item == STAIR else 4
    out = []
    foot = (fc, fr)
    for k in range(rise):
        tiles = [(foot[0] + ac * s + pc * w, foot[1] + ar * s + pr * w)
                 for s in range(1, length + 1) for w in range(width)]
        landing = (foot[0] + ac * (length + 1), foot[1] + ar * (length + 1))
        out.append((tiles, [(landing[0] + pc * w, landing[1] + pr * w) for w in range(width)],
                    lvl0 + k))
        foot = landing
    return out


def _carve(lv: np.ndarray, run) -> None:
    item, (fc, fr), face, rise, lvl0, width, _name = run
    pc, pr = SIDE[face]
    for w in range(width):
        lv[fr + pr * w, fc + pc * w] = lvl0
    for tiles, landing, k in _run_tiles(run):
        for c, r in tiles:
            lv[r, c] = k
        for c, r in landing:
            lv[r, c] = k + 1


def _levels(L: Layout, cc, rr, noise):
    """Local levels for the whole region as one array, then written to the layer with faces:
    limestone on rock, ashlar where the Acropolis walls face the cliff, earth banks elsewhere."""
    lv = np.zeros((N, N), dtype=np.int32)
    rock = np.zeros((N, N), dtype=bool)

    # --- the Acropolis: plateau, sheer rim, ledge, slopes -----------------------------------
    plat = _m(PLATEAU) | _m(LANDING)
    high = plat | _m(BASTION) | _m(NIKE_TERRACE)
    d = _dist(high, 12)
    # A distance wobbled by slow noise bends the outline into long crags and bays; the profiles
    # give a few tall faces with ledges between them, so the rock reads as one rock: on the north
    # the rim drops 10 -> 5 onto the Peripatos' ledge, then 5 -> 2 and 2 -> 0; on the south the
    # Kimonian wall stands 10 -> 6 over a ledge the theatre's cavea meets, then the slope falls
    # 6 -> 3 onto a second ledge for the sanctuaries and 3 -> 0 to the city.
    de = d + np.where(d >= 2, np.round((noise(9.0, "crag") - 0.5) * 2.2).astype(int), 0)
    de = np.clip(de, 0, 12)
    north_p = np.array([10, 5, 5, 5, 2, 2, 0, 0, 0, 0, 0, 0, 0])
    south_p = np.array([10, 6, 6, 6, 3, 3, 0, 0, 0, 0, 0, 0, 0])
    zone = (cc >= 54) & (cc <= 131) & (rr >= 63) & (rr <= 110)
    slope = np.where(rr < 86, north_p[de], south_p[de])
    lv = np.where(zone, np.maximum(lv, slope), lv)
    lv[plat] = 10
    lv[_m(BASTION) | _m(NIKE_TERRACE)] = 9
    rock |= zone & (d <= 7)
    # The approach climbs between retaining walls: its south flank rises with it; the theatre
    # and the Odeion are cut into the south slope (the cavea's top meets the rock at 6).
    for c in range(48, 62):
        lv[93:96, c] = np.minimum(lv[93:96, c], 1 + (c - 48) * 9 // 13)
    lv[_m(APPROACH)] = 1
    lv[103, 103:120] = 6
    lv[_m(THEATRE) | _m(Rect(106, 121, 112, 124)) | _m(ODEION)] = 0
    lv[_m(Rect(100, 116, 103, 125)) | _m(Rect(119, 116, 133, 126))] = 0
    # The Panathenaic Way's corridor round the west end of the rock, and the approach's foot.
    lv[_m(Rect(58, 62, 62, 85) | Rect(40, 82, 62, 85) | Rect(40, 86, 47, 92))] = 0
    lv[_m(Rect(44, 86, 47, 92))] = 1
    lv[_m(Rect(60, 70, 64, 76))] = 0      # the Klepsydra under the north-west cliff

    # --- Areopagus: a bare rock highest in the west, falling to the Way ---------------------
    ar = _m(AREOPAGUS) & ~(lv > 0)
    ad = _dist(~_m(AREOPAGUS), 8)
    a_lv = np.clip(np.round(5.4 - np.maximum(cc - 50, 0) * 0.35 - np.maximum(rr - 75, 0) * 0.7),
                   0, 5)
    lv = np.where(ar, np.minimum(a_lv, ad + 1), lv)
    lv[_m(Rect(47, 71, 51, 76))] = 5                        # the council's flat rock top
    rock |= ar

    # --- Kolonos Agoraios (2), the Pnyx and the Hill of the Nymphs (4-6), the Mouseion (8) ---
    kol = _m(KOLONOS)
    kd = _dist(~kol, 4)
    lv = np.where(kol, np.minimum(2, kd), lv)
    lv[_m(Rect(9, 39, 19, 48))] = 2                         # the Hephaisteion's terrace
    nym = _m(NYMPHS)
    nd = _dist(~nym, 8)
    lv = np.where(nym, np.minimum(6, nd + 2), lv)
    rock |= nym & (noise(3.0, "nymph_rock") > 0.45)
    # North slope of the Pnyx hill, rising south to the apron (4); the apron round the assembly
    # place; the hilltop behind it (6) with Meton's sundial.
    grade = np.clip((rr - 73) // 3 + 1, 0, 4)
    pz = (cc >= 9) & (cc <= 31) & (rr >= 74) & (rr <= 85)
    lv = np.where(pz, np.maximum(lv, grade), lv)
    lv[_m(Rect(9, 83, 25, 85) | Rect(9, 86, 31, 100))] = 4
    # Behind the assembly the hilltop (6) with Meton's sundial; its south flank falls to the
    # wall, its west flank to the road inside the wall.
    lv[_m(Rect(12, 101, 31, 102) | Rect(24, 103, 31, 103))] = 6
    lv[_m(Rect(9, 103, 23, 103))] = 4
    lv[_m(Rect(9, 104, 31, 104))] = 3
    lv[_m(Rect(9, 105, 31, 105))] = 1
    lv[_m(Rect(9, 101, 11, 102))] = 4
    for c in (7, 8):
        lv[67:106, c] = np.minimum(np.maximum(lv[67:106, c], c - 6), lv[67:106, c] + 99)
    lv[_m(Rect(4, 66, 6, 105) | Rect(4, 103, 11, 105))] = 0
    ez = (cc >= 32) & (cc <= 35) & (rr >= 83) & (rr <= 103)
    lv = np.where(ez, np.maximum(lv, 35 - cc), lv)   # the apron's east bank
    rock |= (cc >= 4) & (cc <= 31) & (rr >= 74) & (rr <= 103) & (noise(3.5, "pnyx_rock") > 0.5)
    mus = _m(MOUSEION)
    md = _dist(~mus, 10)
    lv = np.where(mus, np.minimum(8, np.round(md * 1.1 + (noise(5.0, "mouseion") - 0.5) * 2)
                                  .astype(int) + 1), lv)
    lv = np.where(mus, np.clip(lv, 1, 8), lv)
    rock |= mus & (noise(3.0, "mouseion_rock") > 0.4)

    # --- outside the walls: Lykabettos, Pentelikon, Hymettos' foothills, the north bank -----
    lyk = _m(LYKABETTOS)
    yd = _dist(~lyk, 10)
    lv = np.where(lyk, np.clip(np.round(yd * 0.9 + (noise(4.0, "lyk") - 0.5) * 1.6), 1, 6), lv)
    rock |= lyk & (noise(3.0, "lyk_rock") > 0.5)
    pent = (cc >= 128) & (rr <= 26)
    p_lv = np.clip(np.round(1 + (cc - 128) * 0.22 + (26 - rr) * 0.16
                            + (noise(6.0, "pentelikon") - 0.5) * 2.0), 1, 9)
    lv = np.where(pent, np.maximum(lv, p_lv), lv)
    rock |= pent & (p_lv >= 3)
    hym = ((cc >= 148) & (rr >= 70) & (rr <= 112)) | ((cc >= 140) & (rr >= 146))
    h_lv = np.clip(np.round((cc - 146) * 0.3 + (noise(7.0, "hymettos") - 0.5) * 1.5), 0, 3)
    lv = np.where(hym, np.maximum(lv, h_lv), lv)
    rock |= hym & (h_lv >= 2) & (noise(3.0, "hym_rock") > 0.55)

    _meet_edges(L, lv)

    # --- landmark platforms and the quarry --------------------------------------------------
    lv[_m(Rect(140, 0, 159, 18))] = 6                       # quarry working level
    lv[_m(Rect(139, 3, 139, 16))] = 6                       # its west lip, where the road leaves
    lv[_m(Rect(54, 66, 58, 70))] = 2                        # Eleusinion terrace
    lv[_m(Rect(148, 50, 159, 66))] = 1                      # Lyceum
    lv[_m(Rect(146, 43, 159, 49))] = 0                      # the Mesogeia road below Lykabettos
    lv[_m(Rect(146, 50, 147, 66))] = 0

    # --- Piraeus: Mounychia hill (4), the harbours at sea level -----------------------------
    mh = _m(MOUNYCHIA_HILL)
    mhd = _dist(~mh, 6)
    lv = np.where(mh, np.minimum(4, mhd + 1), lv)
    lv[_m(Rect(49, 144, 53, 148))] = 4                     # the summit, Artemis Mounychia
    rock |= mh & (noise(3.0, "mounychia_rock") > 0.5)
    lv[_m(Rect(126, 99, 134, 101))] = 0                     # below the Peripatos' east stair

    # Pentelikon's foot north of the wall, shaped to the quarry road: the lower leg's terrace
    # (rows 0..7 west of the bend), the bend at 3, the upper leg's terrace with the mountain
    # above it and the slope below it falling toward the wall.
    lower = np.clip((cc - 111) // 5, 0, 3)
    upper = 3 + np.clip((cc - 124) // 5, 0, 3)
    foot = (cc >= 104) & (cc <= 138)
    lv = np.where(foot & (rr <= 7) & (cc < 124), np.maximum(lv, lower), lv)
    lv = np.where(foot & (rr >= 3) & (rr <= 4) & (cc < 127), lower, lv)
    lv = np.where(foot & (rr >= 5) & (rr <= 7) & (cc >= 124) & (cc <= 126), 3, lv)
    lv = np.where(foot & (rr <= 7) & (cc >= 127), np.maximum(lv, upper + 1), lv)
    lv = np.where(foot & (rr >= 8) & (rr <= 9) & (cc >= 124), upper, lv)
    lv = np.where(foot & (rr >= 10) & (rr <= 11) & (cc >= 124), np.minimum(lv, upper - 1), lv)
    rock |= foot & (rr <= 11) & (cc >= 116) & (noise(4.0, "pent_foot") > 0.45)
    for run in RUNS:
        _carve(lv, run)

    sea = _sea()
    lv[sea] = -1
    ashlar = np.zeros((N, N), dtype=bool)
    # The Periclean and Kimonian walls face the plateau's rim on the north and south.
    rim = plat & (_dist(~plat, 2) == 1)
    ashlar |= rim & ((rr >= 99) | (rr <= 78))
    return lv, rock, ashlar, RUNS


def _sea() -> np.ndarray:
    return _m(KANTHAROS | ZEA | MOUNYCHIA)


def _meet_edges(L: Layout, lv: np.ndarray) -> None:
    """Near the layer's edges, levels bend toward the world outside (at most one level per tile
    from the edge) where a seam of cliffs would show from the camera in the south-west: ground
    outside the north and east edges that is higher than ours (its faces look onto us), and our
    ground on the west and south edges that is higher than the world outside (our faces show).
    Water outside is left to the coast; the Academy road keeps its ramp."""
    keep = np.zeros((N, N), dtype=bool)
    keep[0:6, 3:6] = True
    for i in range(N):
        for (c, r), (oc, orr), (dc, dr), raise_ in (((i, 0), (i, -1), (0, 1), True),
                                                    ((N - 1, i), (N, i), (-1, 0), True),
                                                    ((i, N - 1), (i, N), (0, -1), False),
                                                    ((0, i), (-1, i), (1, 0), False)):
            t = L.below_terrain(oc, orr)
            if t is None or L.cat.is_water(t):
                continue
            out = L.below_level(oc, orr)
            for k in range(6):
                x, y = c + dc * k, r + dr * k
                if keep[y, x]:
                    continue
                if raise_:
                    lv[y, x] = max(lv[y, x], out - k)
                else:
                    lv[y, x] = min(lv[y, x], out + k)


# =============================================================================================
# 2. Ground
# =============================================================================================

def _ground(L: Layout, lv, rock, ashlar, cc, rr, noise) -> None:
    L.fill(GRASS, level=0, district="countryside")
    lo, hi = int(lv.min()), int(lv.max())
    for k in range(lo, hi + 1):
        if k == 0:
            continue
        m = lv == k
        for face, sel in ((ASHLAR, ashlar), (LIME, rock & ~ashlar), (EARTHF, ~rock & ~ashlar)):
            if (m & sel).any():
                L.level(Mask(0, 0, m & sel), k, face=face if k > 0 else None)
    L.paint(Mask(0, 0, rock & ~ashlar), ROCK)
    L.paint(Mask(0, 0, ashlar), MARBLE)       # the wall walk along the rim
    sea = _sea()
    L.paint(Mask(0, 0, sea), SEA)
    shallow = sea & (_dist(~sea, 2) == 1)
    L.paint(Mask(0, 0, shallow), SHALLOWS)


# =============================================================================================
# 3. Water: the Ilissos and the Eridanos (summer-dry stony beds with a thin stream)
# =============================================================================================

def _water(L: Layout) -> None:
    L.paint(Line(ILISSOS, 3), BED)
    L.paint(Line(ERIDANOS, 1) | Line([(1, 17), (0, 17)], 1), BED)
    L.paint(Line(ERIDANOS[:3], 2), BED)       # channelled where it skirts the Agora


# =============================================================================================
# 4. Ways
# =============================================================================================

def _ways(L: Layout, lv) -> dict:
    W = {}

    def st(key, points, width=1, paving=EARTH, kind="street", portal=None, fine=False):
        pts = stairstep(points, run=1) if fine else orth(points)
        s = L.street(pts, width=width, paving=paving, kind=kind, portal=portal)
        W.setdefault(key, []).append(s)
        return s

    # The Panathenaic Way: from the Dipylon's court through the Kerameikos, across the Agora on
    # the diagonal, past the Eleusinion, round the Areopagus' east side and west below the rock
    # to the foot of the approach (bible §2.5).
    st("way", [(8, 10), (18, 10), (18, 22), (22, 22)], 3, GRAVEL)
    st("way", [(22, 22), (44, 50)], 3, GRAVEL, fine=True)   # straight on screen
    st("way", [(44, 50), (51, 55), (52, 62), (60, 64), (60, 84), (40, 84), (40, 90), (41, 90)],
       3, GRAVEL)
    st("way", [(44, 89), (47, 89)], 1, GRAVEL)                      # steps' head to the approach
    # On the rock: the landing, through the Propylaia's passage, along the processional way
    # between the Old Temple and the Parthenon to the Great Altar and the sculptors' yard.
    st("rock", [(62, 89), (64, 89), (64, 87), (116, 87)], 2, MARBLE)
    st("rock", [(85, 87), (85, 83)], 1, MARBLE)                      # Pandroseion, Old Temple
    st("rock", [(70, 91), (76, 91), (76, 88)], 1, MARBLE)              # Nike steps' head
    st("rock", [(70, 94), (66, 94)], 1, ROCK)                        # Nike terrace
    # Gates and country roads.
    st("academy", [(4, 0), (4, 10), (7, 10)], 1, EARTH, "road", portal="academy_road_n")
    st("sacred", [(0, 16), (18, 16)], 1, GRAVEL, "road", portal="sacred_way_w")
    st("acharnai", [(41, 0), (41, 14), (46, 20), (46, 29)], 2, EARTH, "road", portal="acharnai_n")
    st("diochares", [(40, 44), (53, 44), (62, 43), (70, 41), (80, 42), (92, 44), (104, 46),
                     (118, 48), (128, 54), (136, 58), (147, 60)], 2, EARTH, "road")
    st("diochares", [(147, 60), (147, 45), (159, 45)], 1, EARTH, "road", portal="mesogeia_e")
    st("ne_gate", [(104, 46), (106, 26), (110, 16), (110, 3)], 2, EARTH, "road")
    st("quarry", [(4, 5), (6, 5), (6, 3), (111, 3)], 1, EARTH, "road")   # from the ramp's foot
    st("quarry", [(126, 3), (126, 6), (124, 6), (124, 8)], 1, EARTH, "road")   # the bend
    st("quarry", [(139, 8), (142, 8), (142, 15)], 1, EARTH, "road")
    st("tripods", [(118, 48), (126, 56), (134, 64), (134, 117), (119, 117)], 2, EARTH)
    st("peripatos", [(128, 100), (134, 100)], 1, EARTH)
    st("kollytos", [(103, 117), (96, 116), (88, 118), (80, 121), (80, 137)], 2, EARTH)
    st("phaleron", [(80, 137), (79, 145), (68, 148), (55, 148), (55, 152), (50, 152)], 1, EARTH,
       "road")
    st("koile", [(96, 116), (90, 112), (76, 110), (62, 108), (48, 106), (36, 104), (33, 104)],
       2, EARTH)
    st("melitides", [(34, 105), (34, 106), (30, 110), (24, 113)], 1, EARTH, "road")
    st("koile", [(40, 105), (40, 85)], 2, EARTH)     # along the approach steps' foot, not over them
    st("itonian", [(96, 116), (98, 128), (133, 128), (133, 140), (135, 140)], 1, EARTH, "road")
    st("long_walls", [(5, 66), (5, 104), (10, 104), (10, 108), (9, 118), (7, 128), (7, 136)], 2,
       EARTH, "road")
    st("hamaxitos", [(27, 61), (29, 61), (29, 65), (14, 65), (14, 66), (1, 66), (1, 136)], 1,
       EARTH, "road")
    st("melite", [(29, 65), (30, 70), (30, 73)], 1, EARTH)
    st("pnyx", [(30, 86), (30, 96)], 1, ROCK)                        # the apron east of the Pnyx
    st("pnyx", [(28, 102), (31, 102)], 1, ROCK)                      # by Meton's sundial, at the steps' head
    st("areopagus", [(50, 74), (48, 74)], 1, ROCK)
    # The Agora: walks along its west buildings, under the Stoa Poikile, along its south side.
    st("agora", [(26, 23), (26, 61)], 2, GRAVEL)
    st("agora", [(22, 29), (53, 29)], 1, GRAVEL)
    st("agora", [(26, 56), (51, 56)], 1, GRAVEL)
    st("kolonos", [(21, 36), (24, 36)], 2, GRAVEL)
    st("kolonos", [(15, 36), (15, 40), (9, 40), (9, 47), (19, 47)], 1, EARTH)  # round the temple
    # The Peripatos along the north ledge, from the cave shrines to the east stair.
    st("peripatos", _ledge_path(L, lv), 1, ROCK)
    # Piraeus: Hippodamos' grid north of the harbours, the isthmus street between Kantharos
    # and Zea, the street up Mounychia.
    st("piraeus", [(0, 133), (37, 133)], 2, EARTH)
    st("piraeus", [(0, 138), (37, 138)], 1, EARTH)
    for c in (14, 29, 36):
        st("piraeus", [(c, 133), (c, 140)], 1, EARTH)
    st("piraeus", [(20, 133), (20, 150)], 2, EARTH)                  # down to the Kantharos quay
    st("piraeus", [(36, 140), (40, 140), (40, 152), (50, 152)], 1, EARTH)
    st("piraeus", [(51, 146), (53, 146)], 1, ROCK)                   # Mounychia's summit
    # Sea lanes: from the Kantharos quay, the Zea sheds and the Mounychia landing out through
    # each mouth; Kantharos' lane ends where the plan's Saronic and Aegean lanes begin.
    L.lane("kantharos", [(11, 152), (11, 156), (12, 159)], kind="sea",
           ports={"quay": 0, "piraeus": 2})
    L.lane("zea", [(31, 148), (31, 152), (30, 159)], kind="sea", ports={"sheds": 0, "zea_mouth": 2})
    L.lane("mounychia", [(51, 154), (51, 159)], kind="sea", ports={"landing": 0, "mouth": 1})
    return W


def _ledge_path(L: Layout, lv) -> list:
    """The Peripatos: along the level-5 ledge under the north rim from its west end (the cave
    shrines) to the head of its east stair (bible: a path round the rock at mid-height), as the
    shortest 4-step path over ledge tiles, keeping to the ledge's middle where it can."""
    from collections import deque
    ok = (lv == 5)
    ok[:, :64] = False
    start = min(((c, r) for r in range(66, 90) for c in range(64, 80) if ok[r, c]),
                key=lambda t: (t[0], -t[1]))
    goal = (128, 85)
    prev = {start: None}
    q = deque([start])
    while q:
        t = q.popleft()
        if t == goal:
            break
        for dc, dr in ((1, 0), (0, -1), (0, 1), (-1, 0)):
            n = (t[0] + dc, t[1] + dr)
            if 0 <= n[0] < N and 0 <= n[1] < N and ok[n[1], n[0]] and n not in prev:
                prev[n] = t
                q.append(n)
    path = [goal]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    path.reverse()
    keep = [path[0]]
    for a, b in zip(path[1:], path[2:] + [None]):
        if b is not None and (keep[-1][0] == a[0] == b[0] or keep[-1][1] == a[1] == b[1]):
            continue
        keep.append(a)
    return keep


def _build_run(L: Layout, run) -> None:
    item, (fc, fr), face, rise, lvl0, width, name = run
    for k, (tiles, _landing, _lvl) in enumerate(_run_tiles(run)):
        for w in range(width):
            mine = tiles[w::width] if False else [t for i, t in enumerate(tiles) if i % width == w]
            cs = [t[0] for t in mine]
            rs = [t[1] for t in mine]
            nm = name if (k, w) == (0, 0) else f"{name}_{k}_{w}"
            L.stair(item, rect=(min(cs), min(rs), max(cs), max(rs)), face=face, name=nm)
        paint = [t for t in tiles]
        for c, r in paint:
            if L.terrain_at(c + L.origin[0], r + L.origin[1]) in (GRASS, ROCK):
                L.paint(Rect(c, r, c, r), ROCK if item == STAIR else EARTH)


# =============================================================================================
# 5. Landmarks (bible §2.3; V4 checks every rect and level)
# =============================================================================================

def _landmarks(L: Layout) -> None:
    P = {}

    def lm(id_, rect):
        P[id_] = L.place(A + id_, rect=rect, name=id_)
        return P[id_]

    # The Acropolis.
    L.stair(A + "approach", rect=APPROACH, face="west", name="approach")
    lm("propylaia", (66, 81, 75, 91))
    lm("nike_bastion", BASTION)
    lm("parthenon", (96, 90, 112, 97))
    lm("old_temple", (88, 79, 98, 84))
    lm("pandroseion", (84, 79, 87, 82))
    lm("promachos", (80, 84, 81, 85))
    lm("brauronion", (78, 95, 86, 100))
    lm("chalkotheke", (88, 98, 94, 101))
    lm("great_altar", (114, 84, 116, 86))
    lm("zeus_polieus", (116, 79, 120, 83))
    lm("sculpt_yard", (113, 88, 121, 98))
    # The Agora and Kolonos.
    lm("hephaisteion", (11, 42, 18, 45))
    lm("royal_stoa", (20, 31, 21, 35))
    lm("stoa_zeus", (20, 38, 23, 48))
    lm("old_bouleuterion", (20, 50, 25, 55))
    lm("tholos", (21, 57, 25, 61))
    lm("stoa_poikile", (30, 26, 39, 28))
    lm("twelve_gods", (34, 31, 35, 32))
    lm("tyrannicides", (40, 40, 41, 41))
    lm("se_fountain", (46, 58, 49, 61))
    lm("lawcourt", (30, 57, 36, 62))
    lm("horos", (26, 62, 26, 62))
    lm("simon_shop", (26, 63, 28, 64))
    lm("eleusinion", (54, 66, 58, 70))
    # Gates, hills, the south slope, outside the walls.
    lm("dipylon", (8, 6, 14, 12))
    lm("sacred_gate", (2, 14, 6, 18))
    lm("pnyx", (12, 86, 28, 100))
    lm("meton_dial", (26, 101, 27, 102))
    lm("theatre", THEATRE)
    lm("dionysos_temple", (106, 121, 112, 124))
    lm("odeion", ODEION)
    lm("olympieion", (134, 128, 152, 138))
    lm("kallirrhoe", (136, 140, 138, 142))
    lm("lyceum", (148, 50, 159, 66))
    lm("pentelikon_quarry", (140, 0, 159, 18))
    # Piraeus.
    lm("harbour", HARBOUR)
    lm("shipsheds", SHEDS)
    return P


# =============================================================================================
# 6. Walls
# =============================================================================================

def _wall_line(L: Layout, pts, kit, every) -> None:
    """Towers where 2 x 2 fits about every `every` tiles and on both sides of every gate (a gap
    a street leaves in the wall's line), then the wall pieces between them."""
    path = Line(pts, 1).path()

    def street(i):
        if not 0 <= i < len(path):
            return False
        return bool(L.STREET[path[i][1], path[i][0]])

    since = every // 2
    for i, (c, r) in enumerate(path):
        since += 1
        if street(i):
            continue
        gate = (i > 0 and street(i - 1)) or (i + 1 < len(path) and street(i + 1))
        if since >= every or gate:
            for oc, orr in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
                if put(L, A + "g_wall_tower", (c + oc, r + orr)):
                    since = 0
                    break
    L.wall(Line(pts, 1), kit)


def _walls(L: Layout) -> None:
    for pts in CITY_WALL:
        _wall_line(L, pts, A + "g_wall", 8)
    for pts in (LONG_N, LONG_M):
        _wall_line(L, pts, A + "g_long_wall", 12)
    _wall_line(L, PIRAEUS_WALL, A + "g_wall", 8)



# =============================================================================================
# 7. Districts
# =============================================================================================

def _districts(L: Layout) -> np.ndarray:
    """Every tile gets a district (the actor system's populations follow them); later calls win.
    Returns the mask of tiles inside the city wall."""
    inside = _m(Poly(CITY_WALL[0][:-1] + [(3, 13), (7, 12)]))
    L.district("north_fields", Rect(15, 0, 135, 5))
    L.district("cemetery", Rect(0, 0, 14, 13) | Rect(0, 14, 1, 20) | Rect(15, 0, 34, 5))
    L.district("long_walls", Poly([(0, 107), (17, 107), (13, 130), (0, 130)]))
    L.district("south_fields", Rect(39, 139, 110, 159) | Rect(14, 107, 40, 130))
    L.district("ilissos", Rect(111, 116, 159, 159) - Rect(111, 116, 126, 136))
    L.district("lykabettos", Rect(146, 22, 159, 44))
    L.district("lyceum", Rect(146, 45, 159, 69))
    L.district("hymettos", Rect(146, 70, 159, 115))
    L.district("pentelikon", Rect(128, 0, 159, 21))
    L.district("melite", Mask(0, 0, inside) & Rect(4, 59, 47, 106))
    L.district("koile", Mask(0, 0, inside) & Rect(30, 102, 62, 137))
    L.district("kerameikos", Mask(0, 0, inside) & Rect(4, 7, 31, 27))
    L.district("skambonidai", Mask(0, 0, inside) & Rect(32, 7, 145, 25))
    L.district("kydathenaion", Mask(0, 0, inside) & Rect(47, 22, 145, 66))
    L.district("east_quarter", Mask(0, 0, inside) & Rect(133, 22, 145, 116))
    L.district("kollytos", Mask(0, 0, inside) & Rect(56, 104, 135, 137))
    L.district("kolonos", Mask(0, 0, KOLONOS.mask(0, 0, N, N)))
    L.district("agora", AGORA - Rect(20, 26, 25, 61))
    L.district("council", Rect(20, 29, 25, 61))
    L.district("areopagus", AREOPAGUS)
    L.district("pnyx", Rect(4, 70, 31, 103))
    L.district("mouseion", MOUSEION)
    L.district("dionysos", Rect(100, 102, 133, 126))
    L.district("slopes", Mask(0, 0, _dist(_m(PLATEAU) | _m(LANDING) | _m(BASTION), 8) <= 6)
               - Rect(100, 102, 133, 126))
    L.district("acropolis", PLATEAU | LANDING | BASTION | NIKE_TERRACE)
    L.district("piraeus", Rect(0, 131, 38, 159) | Rect(39, 140, 57, 159))
    L.district("harbour", KANTHAROS | ZEA | MOUNYCHIA)
    return inside


# =============================================================================================
# 8. Lanes and houses
# =============================================================================================

def _corners(tiles) -> list:
    """The vertices of a 4-connected tile path (its first, last and turning tiles)."""
    keep = [tiles[0]]
    for a, b in zip(tiles[1:], tiles[2:] + [None]):
        if b is not None and (keep[-1][0] == a[0] == b[0] or keep[-1][1] == a[1] == b[1]):
            continue
        keep.append(a)
    return keep


def _lanes(L: Layout, area: np.ndarray, starts, seed: str, run=(4, 9), max_len=34,
           paving=EARTH, dead: set | None = None) -> list:
    """Unpaved lanes that wander off the main streets (Athens was not gridded): each starts on
    a street, runs a few tiles, jogs a tile or two aside, and goes on until it meets another way,
    leaves its quarter, meets a building or a change of level. Dead ends are kept (the courtyard
    alleys of a Greek town), but a lane that stops a step short of another way is either joined
    to it or cut back, so no path is drawn across a house."""
    st = rng.stream("athens", "lanes", seed)
    out = []
    dead = set() if dead is None else dead     # dead ends of earlier lanes: keep clear of them

    def ok(c, r, lvl):
        return (0 <= c < N and 0 <= r < N and area[r, c] and L.OCC[r, c] < 0
                and not L.IMP[r, c] and L.LV[r, c] == lvl and L.T[r, c] >= 0
                and not L.cat.is_water(L.terrains[L.T[r, c]])
                and not any(abs(c - a) + abs(r - b) <= 2 for a, b in dead))

    def street(c, r, lvl):
        return 0 <= c < N and 0 <= r < N and L.STREET[r, c] and L.LV[r, c] == lvl

    for (c, r, dc, dr) in starts:
        if not (0 <= c < N and 0 <= r < N) or L.STREET[r, c]:
            continue
        lvl = L.LV[r - dr, c - dc]
        if not ok(c, r, lvl):
            continue
        tiles = [(c - dc, r - dr), (c, r)]
        head, joined = (dc, dr), False
        while not joined and len(tiles) < max_len:
            stop = False
            for _ in range(st.randint(*run)):
                nxt = (tiles[-1][0] + head[0], tiles[-1][1] + head[1])
                if street(*nxt, lvl):
                    tiles.append(nxt)
                    joined = True
                    break
                if not ok(*nxt, lvl):
                    stop = True
                    break
                tiles.append(nxt)
            if joined or stop:
                break
            side = (head[1], head[0]) if st.chance(0.5) else (-head[1], -head[0])
            for _ in range(st.randint(1, 2)):
                nxt = (tiles[-1][0] + side[0], tiles[-1][1] + side[1])
                if not ok(*nxt, lvl) or L.STREET[nxt[1], nxt[0]]:
                    break
                tiles.append(nxt)
        while not joined and len(tiles) >= 5:
            own = set(tiles)
            ec, er = tiles[-1]
            near = [(ec + a, er + b) for a in range(-2, 3) for b in range(-2, 3)
                    if a * a + b * b <= 6 and 0 <= ec + a < N and 0 <= er + b < N
                    and L.STREET[er + b, ec + a] and (ec + a, er + b) not in own]
            if not near:
                break
            t = min(near, key=lambda q: (abs(q[0] - ec) + abs(q[1] - er), q))
            if L.LV[t[1], t[0]] != lvl:
                tiles.pop()
                continue
            step = [(ec + (t[0] - ec) * k // max(abs(t[0] - ec), 1), er) for k in
                    range(1, abs(t[0] - ec) + 1)] + \
                   [(t[0], er + (t[1] - er) * k // max(abs(t[1] - er), 1)) for k in
                    range(1, abs(t[1] - er) + 1)]
            if all(ok(*q, lvl) or q == t for q in step):
                tiles += step
                joined = True
            else:
                tiles.pop()
        if len(tiles) >= 5:
            if not joined:
                dead.add(tiles[-1])
            out.append(L.street(_corners(tiles), width=1, paving=paving))
    return out


def _starts(L: Layout, streets, every=(5, 9), seed="s") -> list:
    """Lane starts along streets: the first tile off the paving, alternating sides."""
    st = rng.stream("athens", "starts", seed)
    out = []
    for s in streets:
        path = s.path()
        i = st.randint(1, every[1])
        while i < len(path) - 1:
            c, r = path[i][0] - L.origin[0], path[i][1] - L.origin[1]
            a, b = path[i - 1], path[i + 1]
            dc, dr = (0, 1) if a[1] == b[1] else (1, 0)
            sign = 1 if st.chance(0.5) else -1
            dc, dr = dc * sign, dr * sign
            k = 1
            while 0 <= c + dc * k < N and 0 <= r + dr * k < N and L.STREET[r + dr * k, c + dc * k]:
                k += 1
            out.append((c + dc * k, r + dr * k, dc, dr))
            i += st.randint(*every)
    return out


def _quarters(L: Layout, W, inside, noise) -> None:
    """The residential demes: lanes off the main streets, then courtyard houses taking the
    frontage, small houses and workshops filling in; density falls from the Agora and the rock
    toward the walls, where gardens, vines and olive yards open up."""
    _plot(L)
    _fountain(L)
    dead: set = set()
    flat = inside & (L.LV == 0) & (L.OCC < 0)
    main = [s for k in ("way", "acharnai", "diochares", "ne_gate", "tripods", "kollytos", "koile",
                        "hamaxitos", "melite", "itonian", "long_walls", "agora") for s in W.get(k, [])]
    quarters = [
        # name, area, kit for the frontage, kit for the fill, gap, lane spacing
        ("melite", Rect(4, 59, 47, 106) - PLOT - Rect(4, 70, 31, 104),
         {A + "g_house": 3, A + "g_house_two": 1.5}, {A + "g_house_small": 3},
         0.1, (5, 8)),
        ("koile", Rect(30, 100, 62, 137), {A + "g_house": 2, A + "g_house_two": 1},
         {A + "g_house_small": 3}, 0.2, (6, 9)),
        ("kydathenaion_w", Rect(47, 22, 95, 66), {A + "g_house": 3, A + "g_house_two": 2},
         {A + "g_house_small": 3}, 0.1, (5, 8)),
        ("kydathenaion_e", Rect(96, 22, 134, 66), {A + "g_house": 3, A + "g_house_two": 1},
         {A + "g_house_small": 3}, 0.15, (6, 9)),
        ("skambonidai", Rect(32, 8, 144, 21), {A + "g_house": 2, A + "g_house_two": 0.5},
         {A + "g_house_small": 2}, 0.3, (7, 11)),
        ("east", Rect(135, 22, 144, 110), {A + "g_house": 2}, {A + "g_house_small": 2}, 0.35, (7, 11)),
        ("kollytos", Rect(56, 108, 126, 136) - Rect(100, 102, 133, 126),
         {A + "g_house": 3, A + "g_house_two": 1.5}, {A + "g_house_small": 3},
         0.12, (5, 8)),
    ]
    for name, area, front_kit, fill_kit, gap, every in quarters:
        am = _m(area) & flat
        mine = [s for s in main if any(am[r - L.origin[1], c - L.origin[0]]
                                       for c, r in Line(s.points, s.width + 2).tiles()
                                       if 0 <= c - L.origin[0] < N and 0 <= r - L.origin[1] < N)]
        lanes = _lanes(L, am, _starts(L, mine, every, name), name, dead=dead)
        lanes += _lanes(L, am, _starts(L, lanes, (6, 10), name + "_2"), name + "_2", run=(3, 7),
                        max_len=18, dead=dead)
        lanes += _lanes(L, am, _starts(L, lanes, (7, 11), name + "_3"), name + "_3", run=(3, 6),
                        max_len=12, dead=dead)
        front = mine + lanes
        built = L.houses(Mask(0, 0, am), front_kit, front=front, gap=gap, seed=name)
        built += L.houses(Mask(0, 0, am), fill_kit, front=front, gap=gap + 0.05,
                          seed=name + "_fill")
        # Density falls from the Agora and the rock toward the walls: far houses give way to
        # gardens (kept as open ground for vines, figs and olives below).
        for p in built:
            far = np.hypot(p.c - L.origin[0] - 70, (p.r - L.origin[1] - 72) * 1.15)
            if rng.hash01(np.array([p.c]), np.array([p.r]), rng.hash64("athens", "thin"))[0] \
                    < np.clip((far - 48) / 45, 0, 0.65):
                L.remove(p)
        # Yards and gardens: wells, jars, household shrines; figs, vines and olives in gardens;
        # more garden toward the walls.
        green = 0.05 + gap * 0.25
        L.scatter(Mask(0, 0, am), {A + "g_well": 1, A + "g_pots": 2, A + "g_shrine": 0.6,
                                   A + "g_loom": 0.3}, 0.02, min_gap=2, seed=name + "_yards")
        L.scatter(Mask(0, 0, am), {A + "t_fig": 3, A + "t_vine": 3, A + "t_olive": 2,
                                   A + "t_myrtle": 1, A + "t_laurel": 0.5}, green, seed=name + "_green",
                  clump=0.7)
    # Herms at doorways and crossings: one at the door of about every fourth house.
    for p in [p for p in L.items if not p.removed and p.id in (A + "g_house", A + "g_house_two")]:
        if p.door and rng.hash64("athens", "herm", p.c, p.r) % 4 == 0:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                at = (p.door[0] + dc - L.origin[0], p.door[1] + dr - L.origin[1])
                if (at[0] + L.origin[0], at[1] + L.origin[1]) in set(p.tiles()):
                    continue
                if put(L, A + "g_herm", at, face=_facing(dc, dr)):
                    break


def _fountain(L: Layout) -> None:
    """The fountain house of Kydathenaion (bible §2.5, c 88, r 50) on a small gravel square off
    the Diochares street, with a shrine and a plane tree."""
    L.paint(Rect(85, 46, 93, 54), GRAVEL)
    L.street([(89, 44), (89, 49)], width=1, paving=GRAVEL)
    L.place(A + "g_fountain", at=(88, 50), face="north", name="kydathenaion_fountain")
    put(L, A + "g_shrine", (86, 48), face="east")
    put(L, A + "t_plane", (92, 48))
    put(L, A + "t_plane", (86, 52))


def _beside_street(L: Layout, area: np.ndarray, items: dict, density: float, seed: str) -> None:
    """Workshop kit that opens on a way (potters' yards, kilns, wheels, forges): tried on free
    tiles in hash order, each turned to face the street it stands by, and kept only where every
    work spot off its own footprint is a street tile, so nothing ends up boxed in a backyard."""
    names = list(items)
    total = sum(items.values())
    js, is_ = np.nonzero(area & (L.OCC < 0) & ~L.STREET)
    cand = sorted(zip(is_.tolist(), js.tolist()), key=lambda t: rng.hash64("athens", seed, *t))
    for c, r in cand:
        h = rng.hash64("athens", seed, "pick", c, r)
        if (h % 1000) / 1000 >= density:
            continue
        u = ((h >> 12) % 1000) / 1000 * total
        item = names[-1]
        for n in names:
            u -= items[n]
            if u < 0:
                item = n
                break
        for dc, dr in ((-1, 0), (0, -1), (1, 0), (0, 1)):
            if not (0 <= c + dc < N and 0 <= r + dr < N and L.STREET[r + dr, c + dc]):
                continue
            p = put(L, item, (c, r), face=_facing(-dc, -dr))
            if p is None:
                continue
            own = set(p.tiles())
            spots = [(sc, sr) for lst in p.slots.values() for sc, sr, _f in lst
                     if (sc, sr) not in own]
            if all(L._local(sc, sr) is not None and L.STREET[L._local(sc, sr)] for sc, sr in spots):
                break
            L.remove(p)


def _facing(dc, dr) -> str:
    return {(1, 0): "west", (-1, 0): "east", (0, 1): "north", (0, -1): "south"}[(dc, dr)]


def _plot(L: Layout) -> None:
    """The decorate zone in Melite (bible §10): a courtyard house in its corner and an empty walled
    garden to furnish, its gate on the lane to the north."""
    c0, r0, c1, r1 = PLOT.c0, PLOT.r0, PLOT.c1, PLOT.r1
    L.paint(Rect(c0 + 1, r0 + 1, c1 - 1, r1 - 1), EARTH)
    L.wall(Line([(c0, r0), (c0 + 4, r0)], 1), A + "g_wall")
    L.wall(Line([(c0 + 7, r0), (c1, r0)], 1), A + "g_wall")
    L.wall(Line([(c0, r0 + 1), (c0, r1)], 1), A + "g_wall")
    L.wall(Line([(c1, r0 + 1), (c1, r1)], 1), A + "g_wall")
    L.wall(Line([(c0 + 1, r1), (c1 - 1, r1)], 1), A + "g_wall")
    L.place(A + "g_house", at=(c0 + 1, r0 + 1), face="east", name="player_house")
    L.street([(c0 + 5, 56), (c0 + 5, r0 + 2)], width=1, paving=EARTH)


# =============================================================================================
# 9. The Agora, the rock, the Kerameikos
# =============================================================================================

def _agora(L: Layout) -> None:
    """The square: trampled earth with gravel walks, Kimon's plane trees along its edges, the
    market's stalls by trade on its east side, money-changers' tables by the Way, the Herms at
    its north-west entrance, dedications and inscribed decrees before the council buildings."""
    sq = Rect(27, 29, 52, 56)
    L.paint(sq & _free_m(L, sq), EARTH)
    for c in range(28, 52, 4):
        put(L, A + "t_plane", (c, 31), variant=c % 2)
    for r in range(34, 56, 4):
        put(L, A + "t_plane", (52, r), variant=r % 2)
        put(L, A + "t_plane", (28, r), variant=(r + 1) % 2)
    # Stalls: six trades in loose rows (pottery, fish, garlands, figs and cheese, perfume,
    # sandals), each row a trade, with gaps for buyers.
    for i, r in enumerate((33, 36, 39, 45, 48, 51)):
        for c in range(42, 51, 3):
            if rng.hash64("athens", "stall", c, r) % 5:
                p = put(L, A + "g_stall", (c, r), variant=i)
                if p is not None and any(L.OCC[L._local(sc, sr)] >= 0
                                         for lst in p.slots.values() for sc, sr, _f in lst
                                         if L._local(sc, sr) is not None):
                    L.remove(p)
    for at in ((35, 46), (37, 41), (31, 40), (44, 54)):
        put(L, A + "g_table_banker", at)
    for c in range(23, 30, 2):
        put(L, A + "g_herm", (c, 25), face="south")
    for at in ((23, 29), (24, 49), (28, 44), (33, 35), (39, 37), (45, 42)):
        put(L, A + "g_statue_base", at, face="east")
    for at in ((28, 50), (28, 52), (28, 54), (23, 37), (28, 33), (32, 56)):
        put(L, A + "g_stele_inscr", at, face="east")
    put(L, A + "g_shrine", (28, 57), face="east")
    put(L, A + "g_well", (45, 57))


def _free_m(L: Layout, rect: Rect) -> Mask:
    occ = L.OCC[rect.r0:rect.r1 + 1, rect.c0:rect.c1 + 1] < 0
    st = ~L.STREET[rect.r0:rect.r1 + 1, rect.c0:rect.c1 + 1]
    return Mask(rect.c0, rect.r0, occ & st)


def _acropolis_detail(L: Layout) -> None:
    """Decrees and tribute lists on stelai and dedications along the processional way, the
    building site at the unfinished Propylaia, the Klepsydra, the cave shrines at the
    Peripatos' west end, scrub on the rock, the south slope's sanctuary."""
    for c in range(78, 112, 3):
        put(L, A + "g_stele_inscr", (c, 86), face="south")
        put(L, A + "g_statue_base", (c + 1, 89), face="north")
    L.paint(Rect(94, 88, 95, 98) & _free_m(L, Rect(94, 88, 95, 98)), MARBLE)  # before the west front
    # The Propylaia stops: blocks still bossed, a crane and scaffolds left standing.
    for at, item in (((76, 79), A + "g_crane"), ((77, 82), A + "g_scaffold"),
                     ((63, 82), A + "g_scaffold"), ((76, 84), A + "g_scaffold"),
                     ((65, 84), A + "g_scaffold")):
        put(L, item, at, face="north")
    put(L, A + "g_brazier", (113, 83))
    put(L, A + "g_fountain", (62, 72), face="west")                      # the Klepsydra
    # Cave shrines of Apollo and Pan under the north-west cliff, where the Peripatos begins.
    start = min((p for p in L.streets if p.paving == ROCK and len(p.points) > 6),
                key=lambda s: -len(s.points)).points[0]
    sc, sr = start[0] - L.origin[0], start[1] - L.origin[1]
    for dc, dr in ((0, -1), (1, -1), (-1, 0), (0, 1)):
        put(L, A + "g_shrine", (sc + dc, sr + dr), face="north")
    rock = Mask(0, 0, (L.LV > 0) & (L.LV < 10) & (L.T == L.terrains.index(ROCK))) \
        - Rect(9, 101, 31, 103)
    L.scatter(rock, {A + "p_thyme": 4, A + "p_asphodel": 2, A + "p_acanthus": 0.5}, 0.22,
              seed="rock_scrub", clump=0.6)
    L.scatter(rock, {A + "t_pine": 1, A + "t_fig": 0.3}, 0.02, min_gap=2, seed="rock_trees")
    L.scatter(PLATEAU, {A + "p_thyme": 1, A + "p_asphodel": 1}, 0.03, seed="plateau_scrub")
    # The south slope's sanctuary of Dionysos: choregic monuments, an altar, cypresses.
    for at in ((100, 120), (102, 124), (114, 125), (119, 124), (121, 121)):
        put(L, A + "g_statue_base", at, face="south")
    put(L, A + "g_shrine", (113, 125), face="south")
    L.scatter(Rect(100, 116, 133, 127), {A + "t_cypress": 2, A + "t_plane": 1, A + "t_laurel": 1},
              0.06, min_gap=2, seed="dionysos_trees")


def _kerameikos(L: Layout, noise) -> None:
    """Inside the walls the potters' quarter: workshop yards with kilns, wheels and pots drying;
    outside the Dipylon and the Sacred Gate the cemetery along the roads, grave stelae and
    mounds among cypresses and asphodel; clay pits north of the wall."""
    inner = Rect(4, 7, 31, 27) - AGORA
    am = _m(inner) & (L.LV == 0) & (L.OCC < 0)
    main = [s for s in L.streets if s.paving in (GRAVEL,)]
    lanes = _lanes(L, am, _starts(L, main, (4, 7), "kerameikos"), "kerameikos", run=(3, 6))
    _beside_street(L, am, {A + "g_workshop": 3, A + "g_kiln": 4, A + "g_wheel": 1.5,
                           A + "g_pots": 1.5}, 0.5, "potters")
    L.houses(Mask(0, 0, am), {A + "g_house_small": 2, A + "g_house": 1, A + "g_house_two": 1},
             front=main + lanes, gap=0.15, seed="kerameikos")
    L.scatter(Mask(0, 0, am), {A + "g_pots": 3}, 0.04, seed="kilns")
    # The cemetery: graves face the roads.
    cem = Rect(0, 0, 14, 13) | Rect(15, 0, 34, 5)
    cemm = _m(cem)
    for s in L.streets:
        if s.kind != "road":
            continue
        for c, r in s.path():
            lc, lr = c - L.origin[0], r - L.origin[1]
            if not (0 <= lc < N and 0 <= lr < N and cemm[lr, lc]):
                continue
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if rng.hash64("athens", "grave", lc, lr, dc) % 3 == 0:
                    put(L, A + "g_grave_stele", (lc + dc, lr + dr), face=_facing(-dc, -dr))
    L.scatter(cem, {A + "g_grave_stele": 3, A + "g_grave_mound": 1, A + "t_cypress": 1.5,
                    A + "p_asphodel": 3}, 0.2, seed="cemetery", clump=0.5)
    L.paint(Rect(17, 0, 25, 3) & Mask(0, 0, noise(3.0, "clay") > 0.45) & _free_m(L, Rect(17, 0, 25, 3)),
            EARTH)


# =============================================================================================
# 10. Piraeus
# =============================================================================================

def _piraeus(L: Layout, noise) -> None:
    """Hippodamos' grid of straight streets north of the harbours, courtyard houses in its
    blocks, the agora of Piraeus with stalls, Kephalos' shield workshop, moles with towers at
    the harbour mouths, Artemis Mounychia on her hill, fishermen at Mounychia's landing."""
    grid = _m(Rect(0, 131, 38, 141)) & (L.LV == 0) & (L.OCC < 0)
    streets = [s for s in L.streets
               if any(Rect(0, 131, 40, 152).contains(c - L.origin[0], r - L.origin[1])
                      for c, r in s.points)]
    # The agora of Piraeus and Kephalos' workshop (forges, a potter's yard for the leather and
    # wood) take their blocks first.
    for c in range(24, 29, 2):
        for r in (135, 136):
            put(L, A + "g_stall", (c, r), variant=(c + r) % 6)
    _beside_street(L, _m(Rect(30, 134, 35, 137)), {A + "g_forge": 2, A + "g_workshop": 1}, 0.9,
                   "kephalos")
    L.houses(Mask(0, 0, grid), {A + "g_house": 2, A + "g_house_two": 2}, front=streets, gap=0.08,
             seed="piraeus")
    L.houses(Mask(0, 0, grid), {A + "g_house_small": 3}, front=streets, gap=0.1,
             seed="piraeus_fill")
    L.scatter(Mask(0, 0, grid), {A + "g_pots": 2, A + "g_well": 1, A + "t_fig": 1}, 0.03,
              min_gap=2, seed="piraeus_yards")
    # Moles and their towers narrowing the harbour mouths.
    for at in ((6, 158), (15, 158), (26, 155), (34, 155), (47, 157), (54, 157)):
        put(L, A + "g_wall_tower", at)
    for at in ((21, 151), (22, 152), (39, 149), (24, 140)):
        put(L, A + "g_pots", at)
    # Mounychia: the sanctuary of Artemis on the summit, cypresses, scrub on the hill.
    put(L, A + "g_shrine", (51, 145), face="south")
    put(L, A + "g_statue_base", (50, 147), face="south")
    hill = Mask(0, 0, MOUNYCHIA_HILL.mask(0, 0, N, N) & (L.LV > 0))
    L.scatter(hill, {A + "t_cypress": 1, A + "t_pine": 2, A + "p_thyme": 4}, 0.18,
              seed="mounychia_green")
    L.scatter(Rect(0, 150, 57, 159) - KANTHAROS - ZEA - MOUNYCHIA,
              {A + "p_thyme": 2, A + "g_pots": 0.3, A + "t_pine": 0.3}, 0.12, seed="akte")


# =============================================================================================
# 11. The country: fields, olive groves, vineyards, farms, the Ilissos, the hills
# =============================================================================================

def _grove(L: Layout, shape, seed: str, item: str = A + "t_olive", step=(3, 2)) -> None:
    """Trees planted in loose rows on worked soil: rows every `step[1]`, trees every `step[0]`
    staggered row by row, each nudged a tile by its hash, one in seven missing."""
    m = shape.mask(0, 0, N, N) & (L.OCC < 0) & ~L.STREET & (L.LV >= 0)
    soil = OLIVE_SOIL if item == A + "t_olive" else EARTH
    cc, rr = np.meshgrid(np.arange(N), np.arange(N))
    worked = rng.fbm(cc + L.origin[0], rr + L.origin[1], 4.0, rng.hash64("athens", seed, "soil"),
                     octaves=2) > 0.47
    L.paint(Mask(0, 0, m & worked), soil)
    js, is_ = np.nonzero(m)
    if js.size == 0:
        return
    for r in range(int(js.min()), int(js.max()) + 1, step[1]):
        off = (r // step[1]) % 2 * (step[0] // 2)
        for c in range(int(is_.min()) + off, int(is_.max()) + 1, step[0]):
            h = rng.hash64("athens", seed, c, r)
            if h % 7 == 0:
                continue
            at = (c + int(h >> 8) % 3 - 1, r)
            if 0 <= at[0] < N and m[r, at[0]]:
                put(L, item, at, variant=int(h >> 16) % 3)


def _track(L: Layout, starts, reach: int = 30):
    """A farm track: the shortest way over free ground of one level from `starts` to the
    nearest street, laid as an earth track (nothing when no street is within reach)."""
    from collections import deque
    starts = [t for t in starts if 0 <= t[0] < N and 0 <= t[1] < N and L.OCC[t[1], t[0]] < 0
              and L.T[t[1], t[0]] >= 0 and not L.cat.is_water(L.terrains[L.T[t[1], t[0]]])]
    if not starts:
        return None
    lvl = L.LV[starts[0][1], starts[0][0]]
    prev = {t: None for t in starts}
    q = deque((t, 0) for t in starts)
    while q:
        t, d = q.popleft()
        if L.STREET[t[1], t[0]]:
            path = [t]
            while prev[path[-1]] is not None:
                path.append(prev[path[-1]])
            if len(path) < 2:
                return None
            return L.street(_corners(path[::-1]), width=1, paving=EARTH, kind="track")
        if d >= reach:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (t[0] + dc, t[1] + dr)
            if not (0 <= n[0] < N and 0 <= n[1] < N) or n in prev:
                continue
            if L.LV[n[1], n[0]] != lvl or L.OCC[n[1], n[0]] >= 0 or L.IMP[n[1], n[0]]:
                continue
            if L.T[n[1], n[0]] < 0 or L.cat.is_water(L.terrains[L.T[n[1], n[0]]]):
                continue
            prev[n] = t
            q.append((n, d + 1))
    return None


def _farm(L: Layout, at, face: str, seed: str) -> None:
    """An Attic farm: the farmstead with its tower, a track to the nearest road, a threshing
    floor on the open ground beside it, an olive press under its wall, jars."""
    c, r = at
    p = put(L, A + "g_farmstead", at, face=face)
    if p is None:
        return
    door = (p.door[0] - L.origin[0], p.door[1] - L.origin[1])
    own = {(x - L.origin[0], y - L.origin[1]) for x, y in p.tiles()}
    if _track(L, [(door[0] + a, door[1] + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if (door[0] + a, door[1] + b) not in own]) is None:
        L.remove(p)
        return
    st = rng.stream("athens", "farm", seed)
    # The threshing floor is flat ground that people and animals work on; it goes in once the
    # set catalog marks it walkable (until then its work spots would be unreachable).
    if L.cat.items[A + "g_threshing"].walkable:
        for dc, dr in ((4, 0), (-4, 0), (0, 4), (0, -4), (4, 3), (-4, -3)):
            if put(L, A + "g_threshing", (c + dc, r + dr)):
                break
    # The press under the farm's wall, or on the nearest free ground of the yard (the oil chain
    # starts here, so every farm needs one).
    near = [(3, 1), (-1, 3), (1, -1), (3, 2), (4, 0), (0, 4), (-3, 0), (0, -3), (4, 3), (-3, 3),
            (3, -3), (-3, -2), (5, 1), (1, 5), (-4, 1), (1, -4)]
    for dc, dr in near:
        if _press(L, (c + dc, r + dr)):
            break
    for _ in range(3):
        put(L, A + "g_pots", (c + st.randint(-2, 4), r + st.randint(-2, 4)))


def _press(L: Layout, at) -> bool:
    """An olive press whose work spot is free ground (else it would be cleared off again)."""
    for face in ("west", "north"):
        p = put(L, A + "g_press", at, face=face)
        if p is None:
            continue
        loc = [L._local(c, r) for c, r, _f in p.slots.get("work", [])]
        if loc and all(x is not None and L.OCC[x] < 0 and not L.STREET[x] for x in loc):
            return True
        L.remove(p)
    return False


def _country(L: Layout, inside, noise) -> None:
    out = ~inside
    # --- north of the wall: fields and olive rows, a few farms -------------------------------
    L.fields(Rect(36, 0, 135, 4) - Rect(38, 0, 44, 4), STUBBLE, plot=(6, 2), path=EARTH,
             seed="north_fields")
    _grove(L, Rect(52, 0, 70, 4) | Rect(96, 0, 108, 4), "north_olives", step=(3, 2))
    # --- between the Long Walls and the Mouseion's wall: fields, an olive yard, a farm -------
    lw_out = Mask(0, 0, out & _m(Poly([(15, 108), (29, 108), (34, 119), (40, 129), (37, 130),
                                        (13, 130)])))
    _farm(L, (22, 112), "west", "lw_farm")
    L.fields(lw_out & Rect(14, 108, 30, 120), STUBBLE, plot=(4, 3), path=EARTH, seed="lw_fields")
    _grove(L, lw_out & Rect(14, 121, 40, 130), "lw_olives")
    corridor = Mask(0, 0, _m(Poly([(6, 108), (15, 108), (12, 129), (3, 129)])))
    L.scatter(corridor, {A + "t_olive": 1, A + "p_thyme": 3, A + "p_asphodel": 2}, 0.12,
              seed="corridor")
    for r in range(112, 129, 8):
        put(L, A + "g_herm", (11 - (r - 108) // 8, r), face="west")
    L.scatter(Rect(0, 67, 2, 130), {A + "p_thyme": 3, A + "p_asphodel": 1}, 0.25, seed="shore")
    # --- south of the wall: farms, fields, olive groves down the Ilissos, vineyards ----------
    south = Mask(0, 0, out & _m(Rect(39, 139, 159, 159)) & ~_m(Line(ILISSOS, 7))
                 & ~_m(MOUNYCHIA_HILL) & (L.LV == 0))
    for i, at in enumerate(((66, 141), (92, 143), (104, 150), (72, 154), (88, 153), (140, 152),
                            (152, 145), (122, 153))):
        _farm(L, at, "north" if i % 2 else "west", f"south{i}")
    L.fields(south & Rect(58, 139, 100, 148), STUBBLE, plot=(5, 3), path=EARTH, seed="south_f")
    _grove(L, south & Rect(60, 149, 110, 159), "south_olives")
    _grove(L, south & Rect(100, 139, 112, 148), "south_vines", item=A + "t_vine", step=(1, 2))
    _grove(L, Mask(0, 0, out & (L.LV == 0)) & (Rect(112, 140, 159, 159) - Line(ILISSOS, 5)
                                             - Rect(134, 128, 152, 143)),
           "ilissos_olives")
    # The Ilissos: planes and chaste trees on its banks (Plato's Phaedrus), oleander, reeds.
    L.scatter(Line(ILISSOS, 7) - Line(ILISSOS, 3), {A + "t_plane": 2, A + "t_agnus": 2,
                                                   A + "t_oleander": 2, A + "p_reeds": 3,
                                                   A + "t_poplar": 0.5},
              0.32, seed="ilissos_banks", clump=0.5)
    L.scatter(Line(ERIDANOS, 3) - Line(ERIDANOS, 1), {A + "p_reeds": 2, A + "t_oleander": 1},
              0.25, seed="eridanos_banks")
    # --- the hills outside the wall ------------------------------------------------------
    L.scatter(LYKABETTOS, {A + "t_pine": 3, A + "p_thyme": 3, A + "p_asphodel": 1}, 0.3,
              seed="lykabettos", clump=0.5)
    L.scatter(Rect(146, 70, 159, 115) | Rect(140, 143, 159, 159),
              {A + "p_thyme": 5, A + "t_pine": 0.6, A + "p_asphodel": 1}, 0.22, seed="hymettos",
              clump=0.6)
    L.scatter(Rect(146, 50, 147, 69) | Rect(146, 45, 159, 49) - Rect(152, 45, 154, 49),
              {A + "t_plane": 2, A + "t_poplar": 1}, 0.25, min_gap=1, seed="lyceum_planes")
    pent = Mask(0, 0, _m(Rect(120, 0, 159, 26)) & (L.LV > 0))
    L.scatter(pent, {A + "t_pine": 2, A + "p_thyme": 4, A + "p_asphodel": 1}, 0.2,
              seed="pentelikon", clump=0.6)
    for at in ((114, 6), (118, 6), (122, 7)):
        put(L, A + "g_house_small", at, face="north")                  # quarrymen's huts
    L.scatter(MOUSEION, {A + "p_thyme": 4, A + "t_pine": 0.6, A + "p_asphodel": 2}, 0.25,
              seed="mouseion", clump=0.5)
    L.scatter(Rect(4, 70, 31, 100) - Rect(12, 86, 28, 100) - Rect(29, 74, 32, 100), {A + "p_thyme": 4, A + "t_pine": 0.4,
                                                            A + "p_asphodel": 1}, 0.18,
              seed="pnyx_scrub", clump=0.5)
    L.scatter(KOLONOS, {A + "t_olive": 2, A + "t_cypress": 1, A + "t_myrtle": 1,
                        A + "t_laurel": 1, A + "p_thyme": 2, A + "p_acanthus": 1}, 0.2,
              seed="kolonos_green", clump=0.5)
    _beside_street(L, _m(KOLONOS) & (L.LV == 2), {A + "g_forge": 2, A + "g_pots": 1}, 0.25,
                   "bronze")                                              # casters by the temple
    # Dry grass with asphodel everywhere else that is still bare outside the walls.
    L.scatter(Mask(0, 0, out), {A + "p_asphodel": 2, A + "p_thyme": 1, A + "t_olive": 0.3},
              0.05, seed="dry_country")


# =============================================================================================
# 12. Named places for the life data (dest nodes, at most 64)
# =============================================================================================

NODES = {
    "dipylon": (11, 10), "sacred_gate": (4, 16), "kerameikos_kilns": (22, 13),
    "cemetery": (4, 4), "agora": (37, 44), "stoa_poikile": (35, 29), "royal_stoa": (26, 33),
    "bouleuterion": (26, 53), "tholos": (26, 59), "se_fountain": (47, 56), "lawcourt": (33, 56),
    "simon_shop": (27, 65), "market": (46, 44), "hephaisteion": (21, 36),
    "eleusinion": (60, 68), "klepsydra": (60, 73), "areopagus": (48, 74),
    "approach_foot": (41, 89), "propylaia": (64, 88), "great_altar": (112, 87),
    "sculptors_yard": (116, 87), "pandroseion": (85, 84), "nike_bastion": (67, 94),
    "peripatos_caves": (66, 78), "pnyx": (30, 90), "meton_dial": (29, 102),
    "theatre": (119, 117), "odeion": (134, 108), "acharnian_gate": (41, 8),
    "diochares_gate": (145, 60), "ne_gate": (110, 12), "halade_gate": (80, 135),
    "itonian_gate": (126, 128), "melitides_gate": (31, 110), "piraeus_gate": (3, 66),
    "long_walls_gate": (10, 106), "long_walls_road": (9, 118), "piraeus_agora": (26, 133),
    "kantharos_quay": (20, 148), "zea_sheds": (31, 140), "kephalos_workshop": (33, 138),
    "mounychia": (52, 146), "mounychia_landing": (50, 152), "kydathenaion_fountain": (89, 48),
    "pentelikon_quarry": (142, 10), "quarry_road": (126, 5), "lyceum": (153, 45),
    "olympieion": (133, 134), "kallirrhoe": (134, 140), "phaleron_road": (79, 145),
    "north_farms": (60, 3), "south_farms": (80, 142), "melite_school": (36, 80),
    "player_house": (39, 66), "kollytos_tavern": (88, 118),
}


# Lit nights (W1): Athens had no public lighting. Light came from doorways and shop counters,
# lamps in wall niches at corners and herms, the gates' torches and braziers, the Tholos where a
# third of the prytaneis kept watch all night, the quays of Piraeus, and altar embers.
NIGHT_LAMPS = ("tholos", "royal_stoa", "stoa_poikile", "bouleuterion", "se_fountain", "simon_shop",
               "eleusinion", "approach_foot", "theatre", "kollytos_tavern", "piraeus_agora",
               "zea_sheds", "kephalos_workshop", "kydathenaion_fountain", "melite_school",
               "hephaisteion", "market", "agora", "lawcourt")
NIGHT_BRAZIERS = ("dipylon", "sacred_gate", "propylaia", "nike_bastion", "kantharos_quay",
                  "mounychia_landing", "long_walls_gate", "piraeus_gate")


def _night(L: Layout, inside: np.ndarray) -> None:
    gates = [(p.c - L.origin[0] + p.pw // 2, p.r - L.origin[1] + p.ph // 2) for p in L.items
             if p.id == A + "g_wall_gate" and not p.removed]
    night_posts(L, A + "g_brazier", [NODES[n] for n in NIGHT_BRAZIERS] + gates, ring=3, gap=6)
    # the Altar of the Twelve Gods, the city's milestone zero and an asylum: a lamp all night
    night_posts(L, A + "g_shrine", [(33, 31), (36, 33), (31, 37)], ring=3, gap=12)
    # the Scythian archers, the city's public slaves who kept order, camped in the Agora
    night_posts(L, A + "g_brazier", [(31, 47), (34, 50)], ring=3, gap=30)
    # The Acropolis after dark (QA7 V7-018): a watch on Athena's treasure in the Parthenon's
    # west room, lamps at the Pandroseion's olive and before the old temple of Athena Polias.
    night_posts(L, A + "g_brazier", [(94, 93)], ring=3, gap=6)
    night_posts(L, A + "g_lamp", [NODES["pandroseion"], (93, 85)], ring=3, gap=4)
    night_posts(L, A + "g_lamp", [NODES[n] for n in NIGHT_LAMPS], ring=3, gap=4)
    piraeus = np.zeros_like(inside)
    piraeus[128:, :60] = True
    night_posts(L, A + "g_lamp", [(c, 150) for c in range(3, 20, 6)], ring=2, gap=5)
    night_posts(L, A + "g_lamp", crossings(L, inside | piraeus, gap=9), ring=2, gap=7)


def _nodes(L: Layout) -> None:
    """Each name goes on the street tile nearest its spot (a node off the streets would be
    joined by a straight edge that may cross houses)."""
    js, is_ = np.nonzero(L.STREET)
    for nid, (c, r) in NODES.items():
        k = int(np.argmin((is_ - c) ** 2 + (js - r) ** 2))
        L.node(nid, (int(is_[k]), int(js[k])))

def _views(L: Layout) -> None:
    # The way up to the Propylaia, from the Panathenaic Way's bend to the landing (V15).
    L.sightline("propylaia_approach", Rect(36, 82, 65, 95))
    L.view("whole_region", Rect(0, 0, 159, 159))
    L.view("acropolis", Rect(40, 60, 136, 126))
    L.view("acropolis_west_1x", Rect(40, 76, 80, 100))
    L.view("acropolis_south_1x", Rect(84, 88, 122, 114))
    L.view("agora", Rect(0, 14, 62, 70))
    L.view("quarter", Rect(60, 24, 110, 66))
    L.view("way", Rect(0, 0, 66, 96))
    L.view("long_walls", Rect(0, 100, 44, 140))
    L.view("piraeus", Rect(0, 128, 60, 159))
    L.view("farms", Rect(56, 136, 120, 159))
    L.view("pentelikon", Rect(100, 0, 159, 30))
    L.view("ilissos", Rect(104, 110, 159, 159))
