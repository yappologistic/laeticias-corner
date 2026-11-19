"""Rome on the Parilia, 21 April AD 126, under Hadrian (docs/design/cities/rome.md).

World rect C 96..271, R 24..183; local (c, r) = world (C - 96, R - 24); local level 0 = world
level 1 (the Forum valley). Coordinates are the bible's (§2.2-§2.6) unless a comment says why
they differ.

Order of the build: levels (one array, stair runs carved into it), ground, the Tiber, ways,
landmarks and stairs, districts, quarters and their fillers, the monumental centres' detail, the
river port, the Campagna, finishing. The Tiber runs at bank level from the north edge to below
the Pons Sublicius and drops a level there, so the Emporium's quay and the way to Ostia stand on
embankments (the island and the bridges stand on the river in the art; see `_river`).
"""

import importlib.util
from pathlib import Path

import numpy as np

from worldgen import rng
from worldgen.dsl import Layout
from worldgen.finish import (clear_doors, clear_front, crossings, fit_faces, free, glow_cap, night_posts, orth,
                             put, seam, stairstep)
from worldgen.shapes import Ellipse, Line, Mask, Rect

_spec = importlib.util.spec_from_file_location("worldgen_region_rome_common",
                                               Path(__file__).resolve().parent / "common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

W, H = 176, 160
R = "rome."
GRASS, BASALT, TRAV, BRICK = R + "grass_spring", R + "basalt_paving", R + "travertine_paving", R + "brick_ground"
EARTH, TUFA, FIELD, VINES = R + "packed_earth", R + "tufa_rock", R + "field_spring", R + "vineyard_soil"
TIBER, MUD = R + "river_tiber", R + "mud_bank"
F_TUFA, F_BRICK, F_TRAV, F_EARTH = R + "tufa", R + "brick", R + "travertine", R + "earth"

# --- landmarks (bible §2.3; set footprints where the art differs, see the region README) ------
LM = {
    "capitolium": (70, 51, 78, 60), "arx": (70, 44, 78, 49), "tabularium": (81, 53, 85, 64),
    "concord": (86, 54, 89, 60), "vespasian": (86, 61, 89, 64), "saturn": (86, 65, 92, 68),
    "rostra": (91, 59, 94, 61), "curia": (93, 53, 96, 56), "lapis_niger": (95, 57, 95, 57),
    "aemilia": (97, 53, 112, 58), "forum_square": (95, 59, 107, 68), "julia": (94, 69, 109, 76),
    "castor": (110, 69, 114, 76), "lacus_iuturnae": (115, 72, 115, 73),
    "divus_julius": (108, 61, 111, 65), "regia": (112, 62, 114, 63), "vesta": (112, 66, 114, 68),
    "vestals": (115, 65, 121, 71), "piperataria": (116, 56, 124, 61),
    "arch_titus": (123, 68, 123, 70),          # set: 1 x 3, the passage on r 69
    "venus_roma": (125, 62, 142, 73), "colossus": (144, 64, 146, 66),
    "meta_sudans": (144, 76, 145, 77), "colosseum": (148, 64, 175, 87),
    "trajan_forum": (72, 29, 96, 41), "basilica_ulpia": (74, 24, 94, 28),
    "trajan_column": (80, 20, 88, 23), "trajan_temple": (80, 13, 88, 18),
    "trajan_markets": (97, 16, 109, 33), "augustus_forum": (98, 34, 110, 46),
    "caesar_forum": (85, 43, 96, 52), "nerva_forum": (111, 41, 114, 52), "pacis": (116, 40, 129, 54),
    "palatine_tiberiana": (100, 78, 112, 84), "domus_flavia": (110, 85, 123, 95),
    "domus_augustana": (113, 96, 126, 104), "palatine_stadium": (127, 86, 132, 104),
    "apollo_palatinus": (101, 91, 106, 96), "house_augustus": (101, 97, 105, 101),
    "casa_romuli": (99, 102, 99, 102), "lupercal": (97, 104, 98, 105),
    "circus_maximus": (82, 108, 132, 117), "porta_capena": (133, 118, 136, 121),
    "portunus": (70, 96, 71, 98), "hercules_victor": (73, 99, 75, 101), "ara_maxima": (77, 97, 78, 98),
    "tiber_island": (50, 86, 60, 92),
    "pons_fabricius": (61, 87, 64, 89), "pons_cestius": (46, 89, 49, 91),      # set: 3 rows deep
    "pons_aemilius": (52, 96, 61, 98), "pons_sublicius": (52, 106, 61, 108),
    "marcellus": (56, 72, 71, 83), "octavia": (50, 62, 60, 70),
    "pantheon": (36, 8, 44, 21), "pantheon_court": (34, 0, 46, 7), "matidia": (48, 0, 53, 5),
    "agrippa_baths": (34, 23, 46, 31), "castra_praetoria": (158, 0, 175, 14),
    "horrea_galbana": (67, 151, 84, 156), "suburban_villa": (150, 140, 166, 154),
    "synagogue": (24, 104, 28, 107),
}
# Landmarks a tile off the bible's rect, so that two ways its touching footprints closed open
# (V4 reports each move with its reason; the region README lists them).
MOVED = {
    "saturn": ((86, 65, 92, 68), "one tile west: the Vicus Iugarius enters the Forum between the "
               "Temple of Saturn and the Basilica Iulia, whose footprints touched at a corner"),
    "pacis": ((116, 40, 129, 54), "one tile east: the Argiletum runs from the Forum past the "
              "Forum of Nerva's east side into the Subura (the bible's c 96..97 line crosses "
              "Caesar's and Trajan's fora and the Markets; Nerva's forum has no walk tiles yet)"),
}
LEVEL = {"capitolium": 6, "arx": 7, "tabularium": 1, "arch_titus": 1, "venus_roma": 1,
         "trajan_markets": 1, "castra_praetoria": 2, "suburban_villa": 1, "lupercal": 1,
         **{k: 6 for k in ("palatine_tiberiana", "domus_flavia", "domus_augustana",
                           "palatine_stadium", "apollo_palatinus", "house_augustus",
                           "casa_romuli")}}
# Landmarks the art set has not drawn (or drew with a footprint that cannot stand at the bible's
# rect): their footprints are kept and dressed with stand-ins until the art can be placed.
RESERVED = {"saepta": (48, 8, 56, 30), "iseum": (58, 14, 64, 22),
            "stadium_domitian": (12, 2, 21, 26), "pompey_theatre": (26, 36, 37, 47),
            "trajan_baths": (144, 20, 173, 49), "testaccio": (86, 148, 96, 159),
            "emporium": (61, 140, 85, 159)}
GALBANA = Rect(*LM["horrea_galbana"])
STAGNUM = Rect(22, 30, 32, 35)
DECORATE = Rect(156, 108, 166, 118)

TIBER_UP = [(5, 0), (5, 12), (6, 26), (9, 38), (14, 48), (20, 58), (30, 65), (40, 70), (45, 76),
            (48, 83)]
TIBER_DOWN = [(56, 95), (56, 159)]
BRIDGEHEAD = Rect(41, 89, 45, 93)     # the Pons Cestius' landing in Transtiberim
AQUEDUCT = [(175, 127), (152, 127), (152, 100), (135, 100)]
APPIA = [(135, 122), (150, 132), (169, 138)]                # past the villa
APPIA_END = [(169, 138), (175, 150)]

# Stair runs: (path, level at the foot, rise, name). See common.run_plan.
RUNS = [
    ([(67, 43), (67, 61)], 0, 6, "centum_gradus"),           # Campus Martius -> the Capitol
    ([(87, 70), (78, 70), (78, 61)], 0, 6, "clivus_capitolinus"),
    ([(79, 52), (79, 49)], 6, 1, "arx_steps"),
    ([(119, 64), (122, 64)], 0, 1, "via_sacra_velia"),
    ([(119, 77), (122, 77)], 0, 1, "nova_via_velia"),
    ([(145, 74), (142, 74)], 0, 1, "via_sacra_valley"),
    ([(145, 75), (142, 75)], 0, 1, "via_sacra_valley_2"),
    ([(124, 77), (124, 83), (115, 83)], 1, 5, "clivus_palatinus"),
    ([(118, 25), (118, 13)], 0, 4, "quirinal_steps"),
    ([(105, 120), (90, 120)], 0, 5, "clivus_publicius"),
    ([(136, 95), (145, 95)], 0, 3, "clivus_scauri"),
    ([(150, 88), (150, 97)], 0, 3, "caelian_steps"),
    ([(132, 30), (138, 30)], 0, 2, "clivus_suburanus"),
    ([(150, 58), (150, 52)], 0, 2, "oppian_steps"),
    ([(140, 51), (146, 51)], 0, 2, "carinae_steps"),
    ([(99, 106), (108, 106), (108, 97)], 0, 6, "scalae_caci"),   # the Circus -> the Palatine
]
# The Via Aurelia is a cart road: it crosses the Janiculum in a cutting at street level, three
# tiles wide between tufa faces, so no ramp (a world piece without art) stands on its sightline.
AURELIA_CUT = Rect(0, 95, 25, 97)
# The Baths of Trajan's south entrance run leaves the precinct at its west edge (local c 143,
# r 40): two tiles of the Oppian's level carry it north to the Esquiline's ground, free of the
# Carinae's houses below (W-W5: the run was sealed by an insula two levels down).
BATHS_LANDING = Rect(143, 39, 143, 40)


def build(L: Layout) -> None:
    URBAN.clear()
    for lid, (rect, why) in MOVED.items():
        L.moved(lid, rect=rect, why=why)

    lv, rock, brick = _levels(L)
    _ground(L, lv, rock, brick)
    _river(L)
    ways = _ways(L)
    placed = _landmarks(L)
    _island_way(L)
    for path, lvl0, rise, name in RUNS:
        C.build_run(L, path, lvl0, rise, name, TRAV)
    _districts(L)
    _reserved(L)
    _aqueduct(L)
    _capitol(L)
    _forum(L)
    _fora(L)
    _velia(L)
    _palatine(L)
    _quarters(L, ways)
    # A gate's passage and a bridge's south end are not hidden behind a roof (QA5 L-04).
    for lid in ("porta_capena", "pons_cestius"):
        clear_front(L, Rect(*LM[lid]))
    # Nor a travertine flight behind an insula's roof at 2x (QA5 Q5-L-04): the houses standing
    # just in front of each stair go.
    for p in [p for p in L.items if not p.removed and p.id == R + "stair_travertine"]:
        c0, r0 = p.c - L.origin[0], p.r - L.origin[1]
        clear_front(L, Rect(c0, r0, c0 + p.pw - 1, r0 + p.ph - 1), depth=2)
    _campus(L)
    _transtiberim(L)
    _port(L)
    _campagna(L)
    # The whole Tiber lies a level below its banks (once the streets that pave over its old
    # channels are laid): the island's quay and the bridges' decks are drawn 16-24 px above the
    # water, so their landings meet the banks only so.
    L.level(Mask(0, 0, _water_mask(L)), -1)
    _nodes(L)
    C.drop_bad_spots(L)
    clear_doors(L, all_slots=True)
    C.drop_unreached(L)
    for area, ground in URBAN:
        L.paint(Mask(0, 0, area & (L.OCC < 0) & ~L.STREET & (L.T == L.terrains.index(GRASS))),
                ground)
    URBAN.clear()
    _night(L)
    glow_cap(L, {R + "r_insula_low": 0, R + "r_insula": 1, R + "r_insula_corner": 2,
                 R + "r_domus": 3, R + "r_taberna": 4, R + "r_thermopolium": 5,
                 R + "r_bath_small": 6, R + "r_lamp": 7, R + "r_compitum": 8, R + "r_brazier": 9})
    seam(L, GRASS, EARTH)
    fit_faces(L, F_EARTH)
    for lid, rect in LM.items():
        if lid in placed:
            L.expect(lid, rect=rect, level=LEVEL.get(lid, 0))
    _views(L)


def m(shape) -> np.ndarray:
    return shape.mask(0, 0, W, H)


# =============================================================================================
# 1. Levels
# =============================================================================================

def _levels(L: Layout):
    lv = np.zeros((H, W), dtype=np.int32)
    cc, rr = np.meshgrid(np.arange(W), np.arange(H))
    rock = np.zeros((H, W), dtype=bool)
    brick = np.zeros((H, W), dtype=bool)

    # --- the Capitol: the temple's plateau (6), the Arx (7), the Tarpeian rock (6) ----------
    lv[m(Rect(68, 50, 80, 61))] = 6
    lv[m(Rect(69, 44, 79, 49))] = 7
    lv[m(Rect(68, 44, 68, 49))] = 4
    lv[m(Rect(66, 60, 69, 66))] = 6                       # the Tarpeian rock over the Velabrum
    lv[m(Rect(80, 44, 84, 51))] = np.clip(6 - (cc[m(Rect(80, 44, 84, 51))] - 80), 2, 6)
    lv[m(Rect(81, 52, 85, 65))] = 1                       # the Tabularium's terrace
    for r, k in zip(range(62, 70), (5, 5, 4, 4, 3, 2, 1, 1)):
        lv[r, 68:81] = k                                  # the south face, stepped tufa
    rock |= m(Rect(66, 44, 85, 69)) & (lv > 0) & ~m(Rect(69, 50, 79, 61) | Rect(70, 44, 78, 49))
    rock |= m(Rect(66, 60, 69, 66))

    # --- the Quirinal behind Trajan's Markets (4), the Markets' terrace (1) ----------------
    lv[m(Rect(98, 0, 133, 12))] = 4
    lv[m(Rect(134, 0, 137, 12))] = 3
    lv[m(Rect(98, 13, 133, 13))] = 3
    lv[m(Rect(98, 14, 133, 14))] = 2
    lv[m(Rect(98, 15, 109, 15))] = 2
    lv[m(Rect(110, 15, 133, 15))] = 1
    lv[m(Rect(96, 0, 97, 15))] = 2
    lv[m(Rect(97, 16, 109, 33))] = 1
    brick |= m(Rect(97, 13, 109, 33))

    # --- the Velia (1), the Oppian and Esquiline (2), the Castra (2) -----------------------
    lv[m(Rect(122, 64, 143, 78) | Rect(125, 56, 143, 63))] = 1
    lv[m(Rect(138, 0, 175, 38) | Rect(144, 39, 175, 52) | BATHS_LANDING)] = 2
    brick |= m(Rect(138, 50, 175, 52))

    # --- the Palatine (6): brick substructures over the Circus and the Forum ---------------
    lv[m(Rect(98, 78, 134, 104))] = 6
    lv[m(Rect(97, 78, 97, 102))] = 3
    lv[m(Rect(99, 105, 134, 105))] = 4
    lv[m(Rect(99, 106, 134, 106))] = 2
    lv[m(Rect(97, 103, 98, 106))] = 1                     # the Lupercal's ledge
    brick |= m(Rect(97, 78, 134, 106))

    # --- the Aventine (5), the Servian wall on its south-west, the Caelian (3) -------------
    lv[m(Rect(66, 121, 90, 133) | Rect(91, 121, 132, 136))] = 5
    lv[m(Rect(66, 120, 132, 120))] = 2
    lv[m(Rect(66, 134, 90, 134))] = 3
    lv[m(Rect(66, 135, 90, 135))] = 1
    lv[m(Rect(91, 137, 132, 137))] = 2
    rock |= m(Rect(66, 133, 90, 135))
    lv[m(Rect(137, 90, 175, 130)) & (rr <= 118 + (cc - 137) * 0.75)] = 3   # above the Appia

    # --- the Janiculum ridge (3) west of Transtiberim; the Via Aurelia's crest ---------------
    lv[m(Rect(3, 60, 10, 159))] = 3
    lv[m(Rect(11, 60, 12, 159))] = 2
    lv[m(Rect(13, 60, 14, 159))] = 1
    lv[m(AURELIA_CUT)] = 0                                # the Aurelia's cutting
    rock |= m(Rect(0, 94, 25, 98))

    keep = np.zeros((H, W), dtype=bool)
    for lid, rect in list(LM.items()) + list(RESERVED.items()):
        keep |= m(Rect(*rect))
    keep |= m(AURELIA_CUT)
    keep |= m(Rect(166, 134, 175, 152))                   # the Via Appia leaving east
    keep |= m(Rect(10, 0, 70, 6))                         # the Campus's roads leaving north
    C.meet_edges(L, lv, keep=keep)

    for path, lvl0, rise, _name in RUNS:
        lv[path[0][1], path[0][0]] = lvl0                 # each run's foot on its street
        C.carve_run(lv, path, lvl0, rise)
    for lid, rect in LM.items():
        lv[m(Rect(*rect))] = LEVEL.get(lid, 0)
    if not _testaccio_fits(L):
        mound = m(Ellipse(91, 154, 5.5, 6.5)) & m(Rect(*RESERVED["testaccio"]))
        d = _dist(~mound, 6)
        lv[mound] = np.clip(d[mound], 1, 4)
        brick |= mound
    else:
        lv[m(Rect(*RESERVED["testaccio"]))] = 1           # the mound's sprite rises from 1
        brick |= m(Rect(*RESERVED["testaccio"]))
    return lv, rock, brick


def _dist(src: np.ndarray, limit: int) -> np.ndarray:
    d = np.full(src.shape, limit, dtype=np.int32)
    d[src] = 0
    cur = src.copy()
    for k in range(1, limit):
        g = cur.copy()
        g[1:, :] |= cur[:-1, :]
        g[:-1, :] |= cur[1:, :]
        g[:, 1:] |= cur[:, :-1]
        g[:, :-1] |= cur[:, 1:]
        d[g & ~cur] = k
        cur = g
    return d


def _fp(L: Layout, lid: str):
    """Plan (w, h) of a landmark at r0 (set catalog, or a provisional placeholder with the
    bible's footprint), or None when there is no such item."""
    d = L.cat.items.get(R + lid)
    if d is None:
        return None
    fx, fy = d.footprint
    return fy, fx


def _fits_bible(L: Layout, lid: str) -> bool:
    c0, r0, c1, r1 = RESERVED[lid]
    return _fp(L, lid) == (c1 - c0 + 1, r1 - r0 + 1)


def _testaccio_fits(L: Layout) -> bool:
    return _fits_bible(L, "testaccio")


def _emporium_fits(L: Layout) -> bool:
    """The Emporium item (quay and Porticus Aemilia) can stand only where it leaves the Horrea
    Galbana's rect free (the set's first footprint, 25 x 20, covered it: a kit quay stood in)."""
    fp = _fp(L, "emporium")
    if fp is None:
        return False
    rect = Rect(61, 140, 61 + fp[0] - 1, 140 + fp[1] - 1)
    return not (m(rect) & m(GALBANA)).any() and rect.c1 < W and rect.r1 < H


WHARF = [(63, r) for r in range(140, 151)]


def _emporium_open(L: Layout) -> bool:
    """Placed only when it fits and its wharf is walkable along c 63: the Porticus reaches the
    foot of Testaccio, so the Via Ostiensis runs along the wharf to the portal."""
    if not _emporium_fits(L):
        return False
    fp = _fp(L, "emporium")
    ne_c = 61 + L.origin[0] + fp[0] - 1
    walk = {(ne_c - dy - L.origin[0], 140 + dx) for dx, dy in L.cat.walk_tiles(R + "emporium", 0)}
    return all(t in walk for t in WHARF)


# =============================================================================================
# 2. Ground
# =============================================================================================

def _ground(L: Layout, lv, rock, brick) -> None:
    L.fill(GRASS, level=0, district="campagna")

    def faces(k, mk):
        return [(F_TUFA, mk & rock), (F_BRICK, mk & brick & ~rock), (F_EARTH, mk & ~rock & ~brick)]

    C.write_levels(L, lv, faces)
    L.paint(Mask(0, 0, rock), TUFA)
    if not _testaccio_fits(L):
        L.paint(Mask(0, 0, m(Ellipse(91, 154, 5.5, 6.5)) & m(Rect(*RESERVED["testaccio"]))), BRICK)


# =============================================================================================
# 3. The Tiber
# =============================================================================================

def _quays(L: Layout, rows) -> None:
    """Mooring posts on the east bank's edge, their boats' spots on the water beside them."""
    wet = _water_mask(L)
    for r in rows:
        cols = np.nonzero(wet[r, 40:70])[0]
        if cols.size:
            c = 40 + int(cols.max()) + 1
            put(L, R + "quay", (c, r), face="west")


def _island_way(L: Layout) -> None:
    """Across the Pons Fabricius, the island and the Pons Cestius, from the street on the east
    bank to Transtiberim's, over the decks' walk tiles (no paint: the river stays under them),
    once the art's walk tiles join the two bridges through the island."""
    walk = set()
    for p in L.items:
        if p.name in ("tiber_island", "pons_fabricius", "pons_cestius") and not p.removed:
            walk |= {(c - L.origin[0], r - L.origin[1]) for c, r in L.walk_tiles(p)}
    a, b = (65, 88), (45, 90)
    prev, todo = {a: None}, [a]
    for t in todo:
        if t == b:
            break
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (t[0] + dc, t[1] + dr)
            if n not in prev and (n in walk or n == b):
                prev[n] = t
                todo.append(n)
    if b not in prev:
        return
    path = [b]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    L.street(C.corners(path[::-1]), width=1, paving=None)


def _river(L: Layout) -> None:
    """The Tiber, six tiles wide down the Campus Martius, dividing round the island, then in its
    eight-tile channel to Ostia (bible §2.5); the Stagnum of Agrippa. The island and the bridges
    stand on the water in the art, but the set catalog marks them `on: land`, so they stand on a
    mud bank (the layout puts water under them by itself once the catalog says `water`)."""
    L.river(TIBER_UP, width=6, terrain=TIBER)
    L.channel([(47, 84), (47, 95)], terrain=TIBER, width=4)
    L.channel([(62, 86), (62, 95)], terrain=TIBER, width=4)
    L.channel([(49, 84), (60, 84)], terrain=TIBER, width=2)
    L.channel([(48, 94), (61, 94)], terrain=TIBER, width=2)
    L.paint(Rect(46, 84, 64, 85) | Rect(46, 93, 64, 95), TIBER)
    L.river(TIBER_DOWN, width=8, terrain=TIBER)
    L.paint(STAGNUM, TIBER)
    L.level(STAGNUM, -1)
    for lid in ("tiber_island", "pons_fabricius", "pons_cestius", "pons_aemilius", "pons_sublicius"):
        L.paint(Rect(*LM[lid]), TIBER if L.cat.items[R + lid].on == "water" else MUD)
    banks = m(Line(TIBER_UP, 8)) & ~m(Line(TIBER_UP, 6))
    banks |= m(Line(TIBER_DOWN, 10)) & ~m(Line(TIBER_DOWN, 8))
    L.paint(Mask(0, 0, banks & (L.T == L.terrains.index(GRASS))), MUD)


def _water_mask(L: Layout) -> np.ndarray:
    return C.water_mask(L)


# =============================================================================================
# 4. Ways
# =============================================================================================

def _ways(L: Layout) -> dict:
    Wd: dict = {}

    def st(key, points, width=1, paving=BASALT, kind="street", portal=None, fine=False):
        pts = stairstep(points, run=3) if fine else C.corners(C.expand(orth(points)))
        s = L.street(pts, width=width, paving=paving, kind=kind, portal=portal)
        Wd.setdefault(key, []).append(s)
        return s

    # The Forum: the Via Sacra across the square, past the Regia, up to the Velia, under the
    # Arch of Titus and down to the Colosseum valley (bible §2.5).
    st("sacra", [(95, 59), (115, 59)], 2)
    st("sacra", [(115, 60), (115, 64), (119, 64)])
    st("sacra", [(122, 64), (122, 69), (124, 69), (124, 74)])
    st("sacra", [(124, 74), (142, 74)], 2)
    st("sacra", [(124, 75), (124, 77)])
    st("valley", [(147, 53), (147, 88)])
    st("valley", [(145, 74), (146, 74)], 2)
    # South of the Oppian steps' flights, not across them (walkers cannot cross a stair's side).
    st("valley", [(147, 59), (169, 59), (169, 53)], 2)
    st("valley", [(147, 88), (169, 88)])
    st("valley", [(147, 58), (150, 58)])
    # Across the square, to the Curia, the Vicus Iugarius and the Clivus Capitolinus.
    st("forum", [(95, 60), (95, 66)])
    st("forum", [(93, 70), (87, 70)])
    st("forum", [(90, 64), (90, 58), (96, 58), (96, 60)])
    st("forum", [(95, 66), (93, 66), (93, 70)])        # between Saturn and the Iulia (MOVED)
    st("iugarius", [(89, 70), (89, 85), (66, 85), (66, 97), (62, 97)], 2)
    st("nova", [(93, 77), (119, 77)])
    st("nova", [(122, 77), (122, 74), (124, 74)])
    st("tuscus", [(95, 77), (95, 107)], 2)
    st("tuscus", [(93, 70), (93, 77)])
    # The Carinae and the Subura behind the imperial fora (the Argiletum's line between the
    # Curia and the Basilica Aemilia is closed by their footprints; see the README).
    st("carinae", [(115, 59), (115, 55), (130, 55), (130, 37)], 1)
    st("argiletum", [(115, 55), (115, 37)], 1)         # past the Forum of Nerva (MOVED)
    st("subura", [(130, 37), (111, 37), (111, 16)], 2)
    st("subura", [(111, 25), (136, 25)])
    st("subura", [(130, 25), (130, 30), (132, 30)])
    st("subura", [(118, 25), (118, 37)])
    # The Esquiline and the Oppian.
    st("esquiline", [(138, 30), (141, 30), (141, 17), (173, 17)])   # short of the edge (Tibur's ground)
    st("esquiline", [(146, 51), (175, 51)])
    st("esquiline", [(150, 52), (150, 51)])
    # Down to the Oppian, or only to the Baths of Trajan's precinct once the set draws them.
    st("esquiline", [(157, 0), (157, 19 if L.cat.items[R + "trajan_baths"].source != "provisional"
                                 else 30)])
    st("esquiline", [(140, 51), (140, 39), (130, 39)])
    st("quirinal", [(118, 13), (118, 6), (100, 6)])
    st("quirinal", [(118, 6), (133, 6)])
    # The Via Lata north up the Campus Martius; the Clivus Argentarius under the Arx.
    st("lata", [(65, 0), (65, 43)], 2, kind="road")
    st("lata", [(65, 42), (84, 42)], 2)
    st("lata", [(65, 44), (65, 71), (73, 71), (73, 85)])
    # The Campus Martius between its monuments.
    st("campus", [(24, 0), (24, 29), (12, 29)])
    st("campus", [(47, 0), (47, 33)])
    st("campus", [(57, 0), (57, 33)])
    st("campus", [(33, 33), (65, 33)], 2)
    st("campus", [(24, 29), (33, 29), (33, 33)])
    st("campus", [(38, 33), (38, 61)])
    st("campus", [(20, 49), (65, 49)], 2)
    st("campus", [(29, 60), (65, 60)])
    st("campus", [(49, 60), (49, 71), (55, 71)])
    # The Circus valley and the Aventine.
    st("circus", [(80, 107), (135, 107)])
    st("circus", [(80, 118), (131, 118)], 2)
    st("circus", [(80, 107), (80, 118)], 2)
    st("circus", [(134, 107), (134, 118)])
    st("circus", [(135, 85), (135, 107)], 2)                # the triumphal way by the Palatine
    st("circus", [(99, 107), (99, 106)])
    st("circus", [(105, 119), (105, 120)])
    st("aventine", [(90, 121), (90, 131), (70, 131)])
    st("aventine", [(90, 126), (130, 126)])
    st("aventine", [(110, 121), (110, 135)])
    # Porta Capena and the Via Appia (portal at (175, 150)).
    st("appia", [(134, 118), (134, 121)], 2)
    st("appia", APPIA, 2, kind="road", fine=True)
    st("appia", APPIA_END, 2, kind="road", fine=True)
    st("appia", [(175, 150), (175, 150)], 1, kind="road", portal="appia_se")
    st("appia", [(134, 122), (134, 139)], 2)
    st("appia", [(134, 139), (61, 139)])
    # The Caelian.
    # Below the head of the Caelian steps, not across their top flight.
    st("caelian", [(145, 95), (145, 98), (170, 98), (170, 95)], 2)
    st("caelian", [(150, 97), (150, 125)])
    st("caelian", [(150, 120), (175, 120)])
    st("caelian", [(158, 98), (158, 106), (155, 106)])
    st("caelian", [(140, 104), (150, 104)])
    st("caelian", [(150, DECORATE.r0 + 8), (DECORATE.c0, DECORATE.r0 + 8)], 1, EARTH)  # plot gate
    st("caelian", [(140, 104), (140, 119)])
    # Forum Boarium, the river road, the Via Ostiensis (portal across at (67, 159)).
    st("boarium", [(76, 85), (76, 95), (82, 95), (82, 106)], 2)
    st("boarium", [(66, 97), (66, 106), (79, 106)], 2)
    st("boarium", [(62, 107), (66, 107)], 2)
    st("river_road", [(63, 108), (63, 139)], 2, kind="road")
    st("ostiensis", [(67, 159), (67, 157), (85, 157)], 2, kind="road")
    if _emporium_open(L):
        # The Porticus Aemilia reaches Testaccio: the road runs along the Emporium's wharf.
        st("ostiensis", [(63, 139), (63, 157), (67, 157)], 1, TRAV, kind="road")
    else:
        st("ostiensis", [(85, 157), (85, 139)], 1, kind="road")
    st("ostiensis", [(67, 159), (67, 159)], 1, kind="road", portal="ostiensis")
    # Transtiberim: the Via Aurelia from the Pons Aemilius over the Janiculum (portal at (0, 96)),
    # the Via Portuensis from the Pons Sublicius along the river, the Cestius road, lanes.
    st("aurelia", [(50, 97), (26, 97), (26, 96), (25, 96)], 2, kind="road")
    st("aurelia", [(1, 96), (25, 96)], 1, kind="road")
    st("aurelia", [(0, 96), (0, 96)], 1, kind="road", portal="aurelia_w")
    st("portuensis", [(50, 107), (44, 107), (44, 159)], 2, kind="road")
    st("portuensis", [(44, 159), (44, 159)], 1, kind="road", portal="portuensis")
    # Over the decks of the Pons Aemilius and the Pons Sublicius (their middle rows). On the
    # river (as the art draws them) the way keeps the water under the deck.
    deck = None if L.cat.items[R + "pons_aemilius"].on == "water" else BASALT
    st("bridges", [(51, 97), (62, 97)], 1, paving=deck, kind="road")
    st("bridges", [(51, 107), (62, 107)], 1, paving=deck, kind="road")
    st("transtiberim", [(45, 90), (36, 90), (36, 97)])
    st("transtiberim", [(36, 90), (36, 76), (30, 76), (30, 140)])
    st("transtiberim", [(18, 120), (44, 120)])
    st("transtiberim", [(15, 108), (44, 108)])
    st("transtiberim", [(18, 132), (44, 132)])
    st("transtiberim", [(18, 84), (30, 84)])
    st("quirinal_foot", [(66, 11), (95, 11), (95, 28)])
    return Wd


# =============================================================================================
# 5. Landmarks
# =============================================================================================

def _landmarks(L: Layout) -> set:
    placed = set()
    for lid, rect in LM.items():
        if L.place(R + lid, rect=rect, name=lid) is not None:
            placed.add(lid)
    return placed


def _reserved(L: Layout) -> None:
    """Footprints of the landmarks without usable art: placed when the art can stand at the
    bible's rect, otherwise dressed so the ground reads as what stood there."""
    for lid, rect in RESERVED.items():
        if lid == "emporium":
            continue
        # A provisional entry draws nothing in the engine yet (QA4 V-B-001: the Baths of
        # Trajan read as an empty lawn), so only real art is placed; the rest is dressed.
        if _fits_bible(L, lid) and L.cat.items[R + lid].source != "provisional":
            L.place(R + lid, rect=rect, name=lid)
            continue
        r = Rect(*rect)
        if lid == "saepta":
            # The Saepta's long colonnaded hall of luxury shops: a paved court lined with stalls.
            L.paint(r & free(L, r), TRAV)
            for rr in range(r.r0 + 1, r.r1, 3):
                put(L, R + "r_stall", (r.c0 + 1, rr), variant=rr % 6)
                put(L, R + "r_stall", (r.c1 - 2, rr), variant=(rr + 3) % 6)
            for rr in range(r.r0, r.r1 + 1, 4):
                put(L, R + "r_column_honor", (r.c0 + 4, rr))
        elif lid == "iseum":
            # The Iseum's court: obelisks and sphinxes stand in for the sanctuary.
            L.paint(r & free(L, r), TRAV)
            for at in ((r.c0 + 1, r.r0 + 1), (r.c1 - 1, r.r0 + 1), (r.c0 + 3, r.r0 + 4)):
                put(L, R + "r_column_honor", at)
            put(L, R + "r_altar", (r.c0 + 3, r.r1 - 1), face="south")
            L.scatter(r, {R + "t_fig": 1, R + "t_rose": 1}, 0.1, seed="iseum_garden")
        elif lid == "stadium_domitian":
            # The stadium's long arena of trampled earth, statues along its spine.
            L.paint(r & free(L, r), EARTH)
            for rr in range(r.r0 + 2, r.r1 - 1, 4):
                put(L, R + "r_statue", ((r.c0 + r.c1) // 2, rr), face="west")
        elif lid == "pompey_theatre":
            # The theatre's cavea and its portico garden: a paved half-round with plane trees.
            L.paint(Mask(0, 0, m(Ellipse(31, 41, 6, 6)) & m(r)) & free(L, r), TRAV)
            L.scatter(r, {R + "t_plane": 2, R + "r_statue": 1}, 0.08, seed="pompey_portico")
        elif lid == "trajan_baths":
            # The Baths of Trajan's precinct until the art returns (bible §3.2: a huge symmetrical
            # complex of great halls round a central block, exercise yards, gardens in an
            # enclosure): a paved platform packed with vaulted bath halls either side of the
            # axis, a palaestra of trampled earth on each flank, gardens to the south, a ring of
            # plane trees, and through streets on the axis and along the gardens.
            core = Rect(r.c0 + 4, r.r0 + 3, r.c1 - 4, r.r0 + 20)
            L.paint(core & free(L, r), TRAV)
            L.street([(r.c0 + 15, 17), (r.c0 + 15, 51)], width=1, paving=TRAV)
            L.street([(r.c0 + 1, r.r0 + 22), (r.c1 - 1, r.r0 + 22)], width=1, paving=TRAV)
            for rr in (r.r0 + 4, r.r0 + 8, r.r0 + 12):
                for c in (r.c0 + 6, r.c0 + 10, r.c0 + 17, r.c0 + 21):
                    put(L, R + "r_bath_small", (c, rr), face="south" if rr < r.r0 + 12 else "north")
            L.paint(Rect(r.c0 + 5, r.r0 + 16, r.c0 + 13, r.r0 + 19) & free(L, r), EARTH)
            L.paint(Rect(r.c1 - 13, r.r0 + 16, r.c1 - 5, r.r0 + 19) & free(L, r), EARTH)
            for c in (r.c0 + 4, r.c1 - 4):
                put(L, R + "r_lacus", (c, r.r0 + 16), face="south")
            for c in range(r.c0, r.c1 + 1, 2):
                put(L, R + "t_plane", (c, r.r0))
                put(L, R + "t_plane", (c, r.r1))
            for rr in range(r.r0 + 2, r.r1, 2):
                put(L, R + "t_plane", (r.c0, rr))
                put(L, R + "t_plane", (r.c1, rr))
            L.scatter(Rect(r.c0 + 1, r.r0 + 24, r.c1 - 1, r.r1 - 1),
                      {R + "t_box": 3, R + "t_rose": 2, R + "t_cypress": 1, R + "r_statue": 0.5,
                       R + "r_lacus": 0.3}, 0.22, seed="baths_gardens")
        elif lid == "testaccio":
            # The mound of broken oil amphorae, built as terraced ground (see _levels).
            L.scatter(Mask(0, 0, m(Ellipse(91, 154, 5.5, 6.5)) & m(r)), {R + "r_amphorae": 1},
                      0.25, seed="testaccio")


# =============================================================================================
# 6. Districts (bible §2.2; later calls win)
# =============================================================================================

def _districts(L: Layout) -> None:
    D = L.district
    D("campagna", Rect(0, 0, W - 1, H - 1))
    D("transtiberim", Rect(0, 40, 52, 159))
    D("janiculum", Rect(0, 60, 14, 159))
    D("vatican", Rect(0, 0, 19, 59))
    D("campus", Rect(10, 0, 70, 72))
    D("fora", Rect(72, 13, 128, 54))
    D("quirinal", Rect(96, 0, 137, 15))
    D("markets", Rect(97, 16, 110, 33))
    D("subura", Rect(110, 16, 137, 38) | Rect(129, 39, 143, 55))
    D("esquiline", Rect(138, 0, 175, 19) | Rect(138, 20, 143, 38))
    D("oppian", Rect(144, 20, 175, 52))
    D("castra", Rect(*LM["castra_praetoria"]) | Rect(158, 15, 175, 16))
    D("capitol", Rect(66, 42, 85, 69))
    D("forum", Rect(86, 52, 121, 77))
    D("velia", Rect(122, 55, 143, 78))
    D("colosseum", Rect(143, 53, 175, 89))
    D("palatine", Rect(97, 78, 136, 106))
    D("circus", Rect(80, 107, 136, 119))
    D("velabrum", Rect(84, 70, 96, 106))
    D("boarium", Rect(62, 84, 83, 106))
    D("island", Rect(45, 83, 65, 95))
    D("aventine", Rect(66, 120, 132, 138))
    D("caelian", Rect(137, 90, 175, 130))
    D("decorate", DECORATE)
    D("emporium", Rect(58, 139, 96, 159))
    D("appia", Rect(133, 118, 175, 159) - Rect(137, 90, 175, 130))
    D("river", Mask(0, 0, _water_mask(L)) - Rect(45, 83, 65, 95))


# =============================================================================================
# 7. The monumental centres
# =============================================================================================

def _paint_free(L: Layout, rect: Rect, terrain: str, level: int | None = None) -> None:
    f = free(L, rect)
    if level is not None:
        f = f & Mask(0, 0, L.LV == level)
    L.paint(f, terrain)


def _capitol(L: Layout) -> None:
    """The Area Capitolina paved in travertine round Jupiter's temple, statues and dedications
    crowding it, the augurs' Arx above, laurels and cypresses on the rock."""
    L.street([(67, 61), (79, 61), (79, 52)], width=1, paving=TRAV)
    L.street([(79, 49), (79, 45)], width=1, paving=TRAV)
    _paint_free(L, Rect(68, 50, 80, 61), TRAV, 6)
    _paint_free(L, Rect(69, 44, 79, 49), TRAV, 7)
    for at in ((69, 51), (69, 54), (69, 57), (80, 54), (80, 57), (70, 61), (76, 61)):
        put(L, R + "r_statue", at, face="south")
    put(L, R + "r_altar", (73, 61), face="south")
    put(L, R + "r_column_honor", (80, 60))
    L.scatter(Mask(0, 0, (L.LV > 0) & (L.LV < 6) & (L.T == L.terrains.index(TUFA))),
              {R + "t_laurel": 1, R + "t_cypress": 1, R + "p_acanthus": 2}, 0.1,
              seed="capitol_scrub")


def _forum(L: Layout) -> None:
    """Travertine paving between the Forum's buildings, honorary columns and statues, the
    Cloelia statue on the Via Sacra, fountains, lamps at the shrines."""
    _paint_free(L, Rect(86, 52, 121, 77), TRAV, 0)
    URBAN.append((m(Rect(86, 52, 121, 77)) & (L.LV == 0), TRAV))
    URBAN.append((m(Rect(66, 11, 96, 43) | Rect(97, 34, 128, 54)) & (L.LV == 0), TRAV))
    for at in ((91, 62), (91, 64), (108, 59), (110, 60), (114, 57), (113, 61), (120, 63),
               (116, 63), (94, 66), (110, 66)):
        put(L, R + "r_statue", at, face="south")
    for at in ((92, 57), (113, 59), (108, 67)):
        put(L, R + "r_column_honor", at)
    put(L, R + "r_statue", (118, 64), face="west")             # Cloelia (presence uncertain)
    put(L, R + "r_lacus", (116, 72), face="south")
    for at in ((96, 70), (110, 77), (118, 76)):
        put(L, R + "r_lamp", at)
    put(L, R + "r_altar", (111, 68), face="south")


def _fora(L: Layout) -> None:
    """The bankers' and booksellers' shops of the Clivus Argentarius under the Arx, statues of
    the great men round the imperial fora."""
    for c in range(69, 84, 2):
        put(L, R + "r_taberna", (c, 41), variant=(c // 2) % 8)
    for at in ((71, 30), (97, 35), (97, 40), (97, 47), (113, 39), (129, 41), (129, 47)):
        put(L, R + "r_statue", at, face="east")
    for at in ((70, 24), (70, 19), (90, 13), (90, 20)):
        put(L, R + "t_plane", at)


def _velia(L: Layout) -> None:
    """The building site of Venus and Roma (cranes, scaffolds, stone and brick waiting), the
    Colossus's travertine plaza, the Meta Sudans, the Colosseum's ring of paving, statues."""
    for at in ((126, 60), (133, 60), (140, 58), (143, 66), (140, 76), (128, 76)):
        put(L, R + "r_crane", at)
    for c in (128, 131, 136, 139):
        put(L, R + "r_scaffold", (c, 61))
    URBAN.append((m(Rect(122, 55, 143, 78)) & (L.LV == 1), EARTH))
    L.scatter(Rect(125, 56, 143, 60), {R + "r_amphorae": 1, R + "r_stall": 0.3}, 0.06,
              seed="velia_site")
    _paint_free(L, Rect(143, 53, 175, 90), TRAV, 0)
    for at in ((146, 60), (146, 70), (146, 82), (160, 89), (170, 89), (155, 55), (165, 55)):
        put(L, R + "r_statue", at, face="east")
    for at in ((146, 63), (146, 79)):
        put(L, R + "r_lamp", at)


def _palatine(L: Layout) -> None:
    """The palace terraces: walks to the clivus heads, gardens of box, roses, laurel and planes in
    the open courts, guards' braziers at the stairs."""
    # Round the south end of the Clivus Palatinus' trench, never across its flights.
    L.street([(114, 83), (114, 79), (122, 79)], width=1, paving=TRAV)
    L.street([(115, 83), (115, 84), (126, 84), (126, 95)], width=1, paving=TRAV)
    L.street([(126, 79), (126, 84)], width=1, paving=TRAV)
    L.street([(126, 79), (132, 79)], width=1, paving=TRAV)
    L.street([(108, 96), (108, 86), (100, 86), (100, 104)], width=1, paving=TRAV)
    top = Mask(0, 0, L.LV == 6) & Rect(98, 78, 134, 104)
    L.scatter(top, {R + "t_box": 3, R + "t_rose": 2, R + "t_laurel": 2, R + "t_plane": 1,
                    R + "t_stone_pine": 1, R + "t_myrtle": 1, R + "r_statue": 0.5}, 0.35,
              seed="palatine_gardens", clump=0.4)
    for at in ((113, 82), (109, 97), (127, 80)):
        put(L, R + "r_brazier", at)
    L.scatter(Mask(0, 0, (L.LV > 0) & (L.LV < 6)) & Rect(97, 78, 134, 106),
              {R + "t_cypress": 1, R + "p_acanthus": 2, R + "t_fig": 0.5}, 0.15,
              seed="palatine_slopes")
    put(L, R + "t_fig", (96, 103))                              # the Ficus Ruminalis


# =============================================================================================
# 8. Quarters: lanes, insulae and domus, shops on the streets, yards and gardens
# =============================================================================================

URBAN: list = []      # (mask, ground) of the crowded quarters, painted once the clean-up is done
DENSE, MIXED, RICH = C.DENSE, C.MIXED, C.RICH


def quarter(L: Layout, *args, **kw) -> None:
    C.quarter(L, *args, urban=URBAN, **kw)


def _quarters(L: Layout, Wd: dict) -> None:
    _decorate(L)
    quarter(L, "subura", Rect(110, 16, 137, 38), DENSE, 0.03, 6, 0.12, 0.01, ground=EARTH,
            fill_front=0.6)
    L.scatter(Mask(0, 0, m(Rect(98, 13, 137, 15)) & (L.LV > 0)),
              {R + "t_cypress": 1, R + "t_fig": 1, R + "p_acanthus": 2}, 0.3, seed="quirinal_slope")
    quarter(L, "carinae", Rect(129, 39, 143, 55) - BATHS_LANDING | Rect(113, 53, 115, 54), MIXED,
            0.06, 6, 0.08, 0.03, ground=BRICK, fill_front=0.4)
    quarter(L, "velabrum", Rect(84, 70, 94, 106) | Rect(68, 70, 92, 84), DENSE, 0.04, 6, 0.1, 0.02,
            ground=EARTH, fill_front=0.5)
    quarter(L, "boarium", Rect(62, 86, 83, 106) - Rect(68, 94, 80, 103), MIXED, 0.08, 6, 0.06,
            0.03, ground=EARTH, fill_front=0.4)
    quarter(L, "esquiline", Rect(138, 0, 157, 38) | Rect(158, 15, 175, 19), MIXED, 0.08, 6, 0.06,
            0.05, level=2, ground=BRICK, fill_front=0.3)
    quarter(L, "oppian", Rect(144, 50, 175, 52) | Rect(174, 18, 175, 49), RICH, 0.2, 7, 0.02, 0.1,
            level=2)
    quarter(L, "quirinal", Rect(98, 0, 133, 12), RICH, 0.2, 7, 0.03, 0.12, level=4)
    quarter(L, "aventine", Rect(66, 121, 132, 136), RICH, 0.15, 7, 0.04, 0.1, level=5)
    quarter(L, "caelian", Rect(137, 90, 175, 130) - Rect(155, 107, 167, 119), RICH, 0.18, 7,
            0.03, 0.1, level=3)
    quarter(L, "quirinal_foot", Rect(86, 0, 97, 12) | Rect(72, 0, 79, 22) | Rect(89, 13, 96, 28),
            DENSE, 0.05, 6, 0.08, 0.02, ground=EARTH, fill_front=0.5)


def _decorate(L: Layout) -> None:
    """The player's peristyle garden on the Caelian (bible §10): a domus in its corner, a low
    precinct of box round an empty garden to furnish, its gate on the street to the west."""
    r = DECORATE
    L.paint(Rect(r.c0 + 1, r.r0 + 1, r.c1 - 1, r.r1 - 1), EARTH)
    L.place(R + "r_domus", at=(r.c0 + 1, r.r0 + 1), face="south", name="player_domus")
    for c in range(r.c0, r.c1 + 1):
        put(L, R + "t_box", (c, r.r0))
        put(L, R + "t_box", (c, r.r1))
    for rr in range(r.r0 + 1, r.r1):
        put(L, R + "t_box", (r.c1, rr))
        if rr not in (r.r0 + 7, r.r0 + 8):
            put(L, R + "t_box", (r.c0, rr))


# =============================================================================================
# 9. The Campus Martius
# =============================================================================================

def _campus(L: Layout) -> None:
    """Between the monuments of the Campus: insulae and domus in the blocks, plane trees round
    the Stagnum, the river bank with its gardens, statues before the Pantheon."""
    quarter(L, "campus_n", Rect(25, 0, 33, 28) | Rect(58, 0, 64, 13) | Rect(58, 23, 64, 32),
            MIXED, 0.06, 6, 0.06, 0.03, ground=EARTH, fill_front=0.4)
    quarter(L, "campus_s", Rect(10, 30, 64, 72) - Rect(*RESERVED["pompey_theatre"]) - STAGNUM,
            MIXED, 0.06, 6, 0.06, 0.04, ground=EARTH, fill_front=0.4)
    quarter(L, "campus_river", Rect(9, 0, 23, 29) - Rect(*RESERVED["stadium_domitian"]), MIXED,
            0.15, 6, 0.04, 0.08)
    for c in range(STAGNUM.c0 - 1, STAGNUM.c1 + 2, 2):
        put(L, R + "t_plane", (c, STAGNUM.r0 - 1))
        put(L, R + "t_plane", (c, STAGNUM.r1 + 1))
    for at in ((35, 8), (45, 8), (40, 22), (47, 6)):
        put(L, R + "r_statue", at, face="north")
    put(L, R + "r_lacus", (46, 22), face="south")


# =============================================================================================
# 10. Transtiberim, the Janiculum, the Vatican plain
# =============================================================================================

def _transtiberim(L: Layout) -> None:
    """Across the river: workshops (glass, dye, smiths, fullers), warehouses on the bank, low
    shop-houses and insulae, the synagogue of a Jewish community; gardens, vines and pines
    on the Janiculum; the Vatican plain's gardens and tombs."""
    wet = _water_mask(L)
    west = np.zeros((H, W), dtype=bool)
    for r in range(64, H):
        cols = np.nonzero(wet[r, 12:])[0]
        west[r, 15:12 + (int(cols[0]) if cols.size else W - 12)] = True
    # The Pons Cestius lands on a small square, not against an insula's wall.
    head = m(BRIDGEHEAD) & ~L.STREET & (L.OCC < 0) & ~wet
    L.paint(Mask(0, 0, head), BASALT)
    west &= ~m(BRIDGEHEAD)
    area = Mask(0, 0, west)
    am = west & (L.LV == 0) & (L.OCC < 0)
    C.beside_street(L, am & ~L.STREET, {R + "r_glass": 2, R + "r_dyeworks": 2, R + "r_smithy": 1.5,
                                        R + "r_fullonica": 1.5, R + "r_horrea": 1}, 0.05,
                    "trans_work")
    quarter(L, "transtiberim", area, ({R + "r_insula_low": 3, R + "r_insula": 1.5,
                                       R + "r_horrea": 1}, {R + "r_insula_low": 2}),
            0.1, 6, 0.06, 0.06, ground=EARTH, fill_front=0.3)
    ridge = Mask(0, 0, (L.LV > 0) & (L.OCC < 0)) & Rect(0, 60, 15, 159)
    C.grove(L, (m(Rect(0, 60, 15, 159)) & (L.LV > 0) & (L.OCC < 0)
                & (rng.fbm(*np.meshgrid(np.arange(W) + L.origin[0], np.arange(H) + L.origin[1]),
                           6.0, rng.hash64("rome", "vines"), octaves=2) > 0.5)),
            "janiculum_vines", R + "r_vine", step=(1, 2), soil=VINES)
    L.scatter(ridge, {R + "t_stone_pine": 3, R + "t_cypress": 1, R + "t_oak": 1, R + "p_poppy": 3},
              0.18, seed="janiculum", clump=0.6)
    vat = Mask(0, 0, m(Rect(0, 0, 19, 63)) & ~_water_mask(L) & (L.OCC < 0))
    L.fields(vat & Rect(0, 30, 12, 58), R + "p_cabbage", plot=(3, 2), path=EARTH, seed="vatican_beds")
    L.scatter(vat, {R + "t_stone_pine": 2, R + "t_cypress": 2, R + "r_tomb": 1, R + "tomb_altar": 1,
                    R + "p_poppy": 3}, 0.1, seed="vatican", clump=0.5)


# =============================================================================================
# 11. The river port: Emporium, Porticus Aemilia, Horrea Galbana, Monte Testaccio, quays
# =============================================================================================

def _port(L: Layout) -> None:
    if _emporium_open(L):
        fp = _fp(L, "emporium")
        L.place(R + "emporium", rect=(61, 140, 61 + fp[0] - 1, 140 + fp[1] - 1), name="emporium")
        quay = Rect(61, 151, 66, 159)              # the wharf below the Porticus
    else:
        quay = Rect(61, 140, 66, 159)
    # The wharf: a travertine quay on its embankment with mooring posts along the water,
    # cranes and stacks of amphorae and sacks; the Porticus Aemilia's vaulted bays as rows of
    # warehouses while its art cannot stand.
    _paint_free(L, quay, TRAV, 0)
    _quays(L, range(quay.r0, quay.r1 + 1, 3))
    _quays(L, range(110, 139, 4))                   # the embankment along the river road
    for r in range(quay.r0 + 2, quay.r1 - 1, 9):
        put(L, R + "r_crane", (65, r))
    L.scatter(quay, {R + "r_amphorae": 1}, 0.25, seed="quay_goods")
    if not _emporium_open(L):
        for c in range(67, 84, 4):
            put(L, R + "r_horrea", (c, 142), face="north")
            put(L, R + "r_horrea", (c, 146), face="south")
        L.street([(67, 141), (84, 141)], width=1, paving=TRAV)
        L.street([(67, 150), (84, 150)], width=1, paving=TRAV)
    # Goods stacked along the river road from the Forum Boarium down to the Emporium.
    for rr in range(110, 138, 4):
        put(L, R + "r_amphorae", (62, rr + 1), variant=rr % 4)
    # Stalls of the cattle and oil markets in the Forum Boarium, the Cloaca's mouth.
    _paint_free(L, Rect(68, 94, 80, 103), TRAV, 0)
    for at in ((69, 100), (72, 103), (77, 101), (79, 95)):
        put(L, R + "r_stall", at, variant=at[0] % 6)
    put(L, R + "r_lacus", (72, 94), face="south")
    put(L, R + "r_compitum", (80, 99), face="west")


# =============================================================================================
# 12. The Campagna: the Via Appia, the aqueduct, the villa, vineyards, fields and flocks
# =============================================================================================

def _aqueduct(L: Layout) -> None:
    """The Aqua Claudia striding in on its arcade over the Caelian to the Palatine (the ways
    pass under it through gaps); placed before the quarters fill in round it."""
    for c, r in Line(AQUEDUCT, 1).path():
        if 0 <= c < W and 0 <= r < H and not L.STREET[r, c]:
            put(L, R + "aqua_claudia", (c, r))


def _campagna(L: Layout) -> None:
    # Market gardens and orchards outside the Porta Ostiensis between Testaccio and the Appia,
    # and on the Caelian's south foot.
    south = m(Rect(97, 141, 136, 159)) & (L.OCC < 0) & ~L.STREET
    for at in ((100, 141), (116, 141), (128, 141)):
        put(L, R + "r_villa_farm", at, face="north")
    L.fields(Mask(0, 0, south) & Rect(97, 145, 125, 159), FIELD, plot=(4, 3), path=EARTH,
             seed="ostiensis_gardens")
    L.scatter(Mask(0, 0, south) & Rect(97, 145, 125, 159), {R + "p_cabbage": 3, R + "r_well": 0.2},
              0.25, seed="ostiensis_beds")
    C.grove(L, south & m(Rect(126, 145, 136, 159)), "ostiensis_figs", R + "t_fig", step=(3, 2),
            variants=2)
    foot = m(Rect(136, 118, 152, 139)) & (L.LV == 0) & (L.OCC < 0) & ~L.STREET
    C.grove(L, foot, "caelian_vines", R + "r_vine", step=(1, 2), soil=VINES)
    # Tombs along the Via Appia facing the road, pines and cypresses behind; milestones.
    road = [s for s in L.streets if s.points[0] == (135 + L.origin[0], 122 + L.origin[1])][0]
    tombs = [R + "r_tomb", R + "tomb_drum", R + "tomb_house", R + "tomb_altar"]
    for i, (c, r) in enumerate(Line(road.points, 1).path()):
        lc, lr = c - L.origin[0], r - L.origin[1]
        h = rng.hash64("rome", "appia", lc, lr)
        if i % 3 == 0:
            for side in (-1, 1):
                for k in (2, 3):
                    if put(L, tombs[(h >> (k + side + 4)) % 4], (lc, lr + side * k),
                           face="north" if side > 0 else "south"):
                        break
        if i % 9 == 4:
            put(L, R + "t_stone_pine", (lc, lr + 5))
            put(L, R + "t_cypress", (lc + 1, lr - 4))
        if i % 16 == 8:
            put(L, R + "r_milestone", (lc, lr - 2), face="south")
    put(L, R + "mutatio", (166, 155), face="north")
    # The villa's vineyard and kitchen gardens, farmsteads and their fields, olive yards.
    camp = m(Rect(137, 131, 175, 159)) & (L.OCC < 0) & ~L.STREET
    C.grove(L, camp & m(Rect(137, 140, 149, 159)), "villa_vines", R + "r_vine", step=(1, 2),
            soil=VINES)
    C.grove(L, camp & m(Rect(167, 131, 175, 146)), "appia_olives", R + "t_olive", step=(3, 2),
            variants=3)
    for at, face in (((140, 132), "south"), ((158, 132), "south"), ((170, 156), "north")):
        put(L, R + "r_villa_farm", at, face=face)
        put(L, R + "r_shed", (at[0] + 4, at[1]), face=face)
    L.fields(Mask(0, 0, camp) & Rect(150, 131, 166, 138), FIELD, plot=(5, 3), path=EARTH,
             seed="appia_fields")
    L.fields(Mask(0, 0, camp) & (Rect(137, 147, 149, 159) | Rect(167, 147, 175, 159)), FIELD,
             plot=(4, 3), path=EARTH, seed="appia_fields_s")
    C.grove(L, camp & m(Rect(137, 131, 149, 139)), "appia_olives_w", R + "t_olive", step=(3, 2),
            variants=3)
    L.scatter(Mask(0, 0, camp), {R + "t_stone_pine": 2, R + "t_cypress": 1, R + "p_poppy": 4,
                                 R + "r_well": 0.3}, 0.06, seed="campagna", clump=0.6)
    L.scatter(Rect(0, 0, W - 1, H - 1), {R + "p_poppy": 3, R + "p_acanthus": 1}, 0.02,
              seed="poppies")
    L.scatter(Mask(0, 0, m(Line(TIBER_UP, 9)) & ~m(Line(TIBER_UP, 6)))
              | Mask(0, 0, m(Line(TIBER_DOWN, 11)) & ~m(Line(TIBER_DOWN, 8))),
              {R + "p_reeds": 3, R + "t_poplar": 1}, 0.15, seed="tiber_banks")


# =============================================================================================
# 13. Named places for the life data (dest nodes, at most 64)
# =============================================================================================

NODES = {
    "forum": (100, 63), "curia": (94, 58), "rostra": (95, 62), "basilica_julia": (101, 68),
    "vesta": (113, 64), "vestals": (118, 64), "clivus_foot": (87, 70), "capitolium": (74, 61),
    "arx": (79, 46), "via_sacra_velia": (122, 66), "arch_titus": (124, 69),
    "venus_roma_site": (132, 74), "colosseum": (161, 88), "colossus": (147, 66),
    "meta_sudans": (147, 77), "ludus": (170, 88), "palatine_court": (126, 85),
    "palatine_west": (100, 95), "circus_carceres": (80, 112), "circus_stands": (110, 118),
    "porta_capena": (134, 121), "appia_tombs": (150, 131), "mutatio": (165, 152),
    "suburban_villa": (167, 148), "caelian": (158, 100), "player_domus": (152, 116),
    "aqueduct": (152, 120), "trajan_forum": (84, 42), "markets": (111, 25),
    "subura": (121, 30), "subura_baker": (125, 37), "carinae": (130, 46), "esquiline": (141, 20),
    "castra": (166, 17), "oppian": (160, 51), "quirinal": (110, 6), "via_lata": (65, 20),
    "pantheon": (40, 0), "agrippa_baths": (40, 33), "stagnum": (27, 29), "saepta": (47, 18),
    "campus_south": (38, 49), "octavia": (49, 64), "marcellus": (65, 71),
    "forum_holitorium": (73, 80), "forum_boarium": (75, 96), "ara_maxima": (77, 99),
    "pons_aemilius": (62, 97), "pons_sublicius": (62, 107), "tiber_island_east": (65, 88),
    "transtiberim": (36, 95), "synagogue": (27, 108), "janiculum": (12, 96),
    "aventine": (100, 126), "emporium": (66, 139), "horrea_galbana": (75, 157),
    "testaccio": (85, 150), "vicus_tuscus": (95, 92), "velabrum": (89, 80),
}


# Lit nights (W1): Rome had no street lighting. Light came from the lamps at the crossroads
# shrines of the Lares, the counters of popinae and thermopolia open late, insula windows, the
# Vestals' fire, torches at the Palatine's and the camp's gates, the bridges' ends, and the
# wharves where the night gangs unloaded what the carts could bring in only after dark.
NIGHT_BRAZIERS = ("porta_capena", "castra", "palatine_court", "palatine_west", "emporium",
                  "horrea_galbana", "ludus", "capitolium", "arx", "venus_roma_site")
NIGHT_LAMPS = ("subura", "subura_baker", "carinae", "velabrum", "vicus_tuscus", "forum_holitorium",
               "octavia", "marcellus", "via_sacra_velia", "arch_titus", "meta_sudans",
               "trajan_forum", "markets", "basilica_julia", "esquiline", "oppian", "caelian",
               "aventine", "quirinal", "transtiberim", "synagogue", "campus_south", "saepta",
               "agrippa_baths", "forum_boarium", "ara_maxima", "tiber_island_east", "player_domus", "testaccio",
               "clivus_foot", "colossus")
OPEN_COUNTRY = {"campagna", "janiculum", "vatican", "castra", "appia", "river", "decorate", "markets"}
BRIDGES = ("pons_fabricius", "pons_cestius", "pons_aemilius", "pons_sublicius")


def _night(L: Layout) -> None:
    ends = []
    for lid in BRIDGES:
        c0, r0, c1, r1 = LM[lid]
        if c1 - c0 >= r1 - r0:
            ends += [(c0 - 1, (r0 + r1) // 2), (c1 + 1, (r0 + r1) // 2)]
        else:
            ends += [((c0 + c1) // 2, r0 - 1), ((c0 + c1) // 2, r1 + 1)]
    night_posts(L, R + "r_brazier", [NODES[n] for n in NIGHT_BRAZIERS], ring=3, gap=6)
    night_posts(L, R + "r_lamp", ends, ring=2, gap=3)
    night_posts(L, R + "r_lamp", [(62, r) for r in range(112, 160, 6)], ring=2, gap=4)  # wharf
    night_posts(L, R + "r_lamp", [NODES[n] for n in NIGHT_LAMPS], ring=3, gap=5,
                kin=(R + "r_compitum",))
    town = np.isin(L.DIST, [i for i, d in enumerate(L.districts)
                            if d.split("/")[-1] not in OPEN_COUNTRY])
    night_posts(L, R + "r_lamp", crossings(L, town, gap=8), ring=2, gap=7,
                kin=(R + "r_compitum",))


def _nodes(L: Layout) -> None:
    C.snap_nodes(L, NODES)
    # The Tiber's boats by the bridges' clearances (art-smooth-land.md §8, geometry `pass`): the
    # barges from Ostia come up with the mast lowered through the one span column both the
    # Sublicius (34 px) and the Aemilius (30 px) clear, c 54, and turn at the island's foot;
    # the island's bridges (Fabricius 21, Cestius 26) pass no barge, so the river above the
    # island has its own boats, upriver barges and fishermen, from the island's head north.
    L.lane("tiber", [(56, 159), (56, 112), (54, 112), (54, 94), (56, 93)], kind="river",
           ports={"ostia": 0, "emporium": 1, "forum_boarium": 3, "island": 4})
    L.lane("tiber_upper", [(48, 84), (45, 76), (30, 65), (20, 58), (9, 38), (5, 0)],
           kind="river", ports={"island_head": 0, "north": 5})


def _views(L: Layout) -> None:
    L.view("whole_region", Rect(0, 0, W - 1, H - 1))
    L.view("forum_1x", Rect(80, 40, 126, 80))
    L.view("fora", Rect(64, 8, 132, 56))
    L.view("colosseum_valley", Rect(118, 50, 175, 92))
    L.view("campus", Rect(6, 0, 70, 72))
    L.view("palatine_circus", Rect(78, 74, 140, 124))
    L.view("subura_street", Rect(108, 14, 140, 40))
    L.view("tiber_island", Rect(36, 76, 90, 112))
    L.view("emporium", Rect(50, 128, 100, 159))
    L.view("aqueduct", Rect(130, 92, 175, 135))
    L.view("appia", Rect(128, 115, 175, 159))
    L.view("transtiberim", Rect(0, 60, 54, 159))
    L.view("capitol", Rect(56, 36, 96, 74))
    L.view("oppian", Rect(136, 8, 175, 58))
    L.view("aurelia_cutting", Rect(0, 82, 36, 110))
