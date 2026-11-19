"""Ostia and Portus, AD 126 (rome.md §3.7, §6.3): Rome's harbour towns at the Tiber mouth.

World rect C 100..170, R 184..239; local (c, r) = world (C - 100, R - 184); local level 0 = world
level 1. Sea, river and canals lie one level below the land (world level 0), so quays and moles
read as embankments. The Tiber comes in from Rome's south edge (local c 49..56) and reaches the sea
at about (25, 48).

North-west of the mouth, Portus: Claudius's outer harbour cut into the shore, its moles and the
lighthouse on an island in its mouth; Trajan's hexagonal basin behind it (`portus_hexagon`, which
carries its own quays and warehouses), joined to the outer harbour by a channel and to the Tiber
by the Fossa Traiana; warehouses and the customs yard on a service street. Between the canal and
the river, the Isola Sacra with the tombs along the road from Portus to Ostia. South-east of the
mouth, Ostia: the decumanus from the Porta Romana to the sea gate, the forum with the Capitolium
(`ostia_capitolium`), the square of the shipping offices behind the theatre (`ostia_guilds`),
the river harbour with quays, insulae, warehouses, bakeries and fulleries in lanes, salt pans
toward the shore; the Via Ostiensis leaves north to Rome (portal `ostiensis`) between tombs and
market gardens.
"""

import importlib.util
from pathlib import Path

import numpy as np

from worldgen import rng
from worldgen.dsl import Layout
from worldgen.finish import (clear_doors, crossings, fit_faces, free, glow_cap, landings,
                             night_posts, put, seam)
from worldgen.shapes import Line, Mask, Poly, Rect

_spec = importlib.util.spec_from_file_location(
    "worldgen_region_rome_common", Path(__file__).resolve().parent.parent / "rome" / "common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

R = "rome."
GRASS, BASALT, TRAV, EARTH = R + "grass_spring", R + "basalt_paving", R + "travertine_paving", R + "packed_earth"
BRICK, FIELD, MUD, TIBER = R + "brick_ground", R + "field_spring", R + "mud_bank", R + "river_tiber"
SEA, SHALLOWS = "world.sea", "world.shallows"
W, H = 71, 56

RIVER = [(52, 0), (51, 6), (48, 13), (44, 20), (40, 27), (35, 34), (30, 41), (26, 47), (23, 55)]
BASIN = Poly([(0, 12), (10, 12), (14, 16), (14, 27), (10, 30), (0, 30)])   # Claudius's harbour
HEXAGON = Rect(17, 2, 36, 19)                                                # Trajan's basin
LIGHTHOUSE = Rect(1, 19, 3, 21)
FOSSA = [(12, 28), (22, 28), (30, 27), (38, 26)]       # Claudius's harbour to the Tiber
CANAL = [(37, 16), (44, 16)]                              # the hexagon's own mouth to the Tiber
TOWN = Poly([(44, 12), (70, 12), (70, 40), (62, 46), (53, 50), (45, 49), (38, 42), (38, 30)])
GATE_ROW = 12                            # the Porta Romana, where the road enters the town
FORUM = Rect(44, 40, 53, 45)
CAPITOLIUM = Rect(46, 32, 49, 37)         # at the forum's head across the decumanus
GUILDS = Rect(50, 24, 61, 29)
THEATRE = Rect(53, 32, 62, 37)          # on the decumanus, the guilds' square behind it
PANS = Rect(57, 42, 69, 50)
URBAN: list = []                         # (mask, ground) of the quarters, painted at the end
PORT = ({R + "r_horrea": 2, R + "r_insula": 1}, {R + "r_insula_low": 1})
TOWN_KIT = ({R + "r_insula": 3, R + "r_insula_corner": 1, R + "r_horrea": 1,
             R + "r_insula_low": 1.2, R + "r_bath_small": 0.15}, {R + "r_insula_low": 2})


def build(L: Layout) -> None:
    URBAN.clear()
    lv = np.zeros((H, W), dtype=np.int32)
    sea = C.mask(L, L.sea_below()) | C.mask(L, BASIN)
    river = C.mask(L, Line(RIVER, 8)) | C.mask(L, Line(FOSSA, 2)) | C.mask(L, Line(CANAL, 2))
    pans = C.mask(L, PANS) & ~sea
    moles = C.mask(L, Line([(0, 11), (10, 11), (15, 16)], 1) | Line([(15, 27), (11, 31), (6, 31)], 1))
    island = C.mask(L, LIGHTHOUSE)
    water = (sea | river) & ~moles & ~island
    lv[water] = -1
    pan_beds = pans & ~C.mask(L, _dykes())
    lv[pan_beds] = -1
    C.meet_edges(L, lv, sides="esw")
    lv[water | pan_beds] = -1

    L.fill(GRASS, level=0, district="fields")
    C.write_levels(L, lv, lambda k, m: [(R + "earth", m)])
    _flow(L)
    open_sea = sea & ~moles & ~island
    L.paint(Mask(0, 0, open_sea), SEA)
    L.paint(Mask(0, 0, _grow(~open_sea) & open_sea), SHALLOWS)
    L.paint(Mask(0, 0, moles | island), TRAV)
    L.level(Mask(0, 0, moles | island), 0, face=R + "travertine")
    L.paint(Mask(0, 0, pan_beds), SHALLOWS)
    L.paint(Mask(0, 0, pans & ~pan_beds), MUD)

    L.district("sea", Mask(0, 0, sea))
    L.district("portus", Rect(0, 0, 38, 24) - Mask(0, 0, sea))
    L.district("harbour", BASIN | HEXAGON)
    L.district("isola_sacra", Poly([(0, 31), (14, 29), (38, 27), (34, 34), (26, 46), (0, 46)])
               - Mask(0, 0, sea | river))
    L.district("river", Mask(0, 0, river))
    L.district("town", TOWN - Mask(0, 0, river))
    L.district("forum", FORUM | CAPITOLIUM | GUILDS)
    L.district("saltpans", PANS)
    L.district("road", Rect(60, 0, 70, GATE_ROW - 1))

    ways = _ways(L)
    _portus(L)
    _ostia(L, ways)
    _country(L)
    _nodes(L)
    C.drop_bad_spots(L)
    clear_doors(L, all_slots=True)
    C.drop_unreached(L)
    for area, ground in URBAN:
        L.paint(Mask(0, 0, area & (L.OCC < 0) & ~L.STREET & (L.T == L.terrains.index(GRASS))),
                ground)
    URBAN.clear()
    _night(L)
    glow_cap(L, {R + "r_insula_low": 0, R + "r_insula": 1, R + "r_taberna": 2,
                 R + "r_thermopolium": 3, R + "r_compitum": 4, R + "r_bakery": 5})
    seam(L, GRASS, R + "packed_earth")
    fit_faces(L, R + "earth")
    L.view("whole", Rect(0, 0, 70, 55))
    L.view("portus", Rect(0, 0, 40, 34))
    L.view("town", Rect(34, 18, 70, 52))
    L.view("isola_sacra", Rect(8, 24, 44, 50))


def _grow(m: np.ndarray) -> np.ndarray:
    g = m.copy()
    g[1:, :] |= m[:-1, :]
    g[:-1, :] |= m[1:, :]
    g[:, 1:] |= m[:, :-1]
    g[:, :-1] |= m[:, 1:]
    return g


def _dykes():
    """The earth banks of the salt pans: a grid of 1-tile walks round 3 x 3 beds."""
    shape = Line([(PANS.c0, PANS.r0), (PANS.c1, PANS.r0)], 1)
    for r in range(PANS.r0, PANS.r1 + 1, 4):
        shape = shape | Line([(PANS.c0, r), (PANS.c1, r)], 1)
    for c in range(PANS.c0, PANS.c1 + 1, 4):
        shape = shape | Line([(c, PANS.r0), (c, PANS.r1)], 1)
    return shape


def _flow(L: Layout) -> None:
    """Flow directions for the Tiber and the canals (painted above as plain water)."""
    L.river(RIVER, width=8, terrain=TIBER)
    L.channel(FOSSA, terrain=TIBER, width=2)
    L.channel(CANAL, terrain=TIBER, width=2)


# =============================================================================================

def _ways(L: Layout) -> dict:
    W_ = {}
    wet = {(c, r): L.terrain_at(c, r) for r in range(L.origin[1], L.origin[1] + H)
           for c in range(L.origin[0], L.origin[0] + W)
           if L.terrain_at(c, r) and L.cat.is_water(L.terrain_at(c, r))}
    # The Via Ostiensis: from the Porta Romana north between tombs to Rome (portal at (63, 0)).
    W_["ostiensis"] = L.street([(63, 0), (63, 38)], width=2, paving=BASALT, kind="road",
                               portal="ostiensis")
    # The decumanus from the Porta Romana west past the forum to the sea gate.
    W_["decumanus"] = L.street([(63, 38), (41, 38)], width=2, paving=BASALT)
    # The cardo from the river quays through the forum to the shore.
    W_["cardo"] = L.street([(45, 30), (45, 49)], width=1, paving=BASALT)
    # The road from Portus over the canal, across the Isola Sacra and the Tiber into Ostia.
    # It comes off the Tiber bridge down quay steps to the decumanus' end (the steps clear of
    # the decumanus, which may not meet them from the side).
    # Off the Tiber's span onto the bank before it turns: a span is entered over its ends.
    W_["portus_road"] = L.street([(26, 20), (26, 36), (40, 36), (40, 39), (41, 39)], width=1,
                                 paving=BASALT, kind="road")
    # Portus's service street round the north and east of the basin; the Via Portuensis from
    # Rome comes in over the north edge (portal `portuensis`).
    W_["portus"] = L.street([(15, 1), (38, 1), (38, 21), (26, 21)], width=1, paving=EARTH)
    W_["portuensis"] = L.street([(40, 0), (40, 1), (38, 1)], width=2, paving=BASALT, kind="road",
                                portal="portuensis")
    # Along the north mole, behind its mooring posts.
    W_["mole"] = L.street([(15, 2), (15, 10), (4, 10)], width=1, paving=TRAV)
    # The quay street along Ostia's river bank.
    bank = []
    for r in range(GATE_ROW, 35):
        wet_c = [c - L.origin[0] for c in range(L.origin[0] + 30, L.origin[0] + 56)
                 if (c, r + L.origin[1]) in wet]
        if wet_c:
            bank.append((max(wet_c) + 2, r))
    W_["quay"] = L.street(C.corners(_orth_tiles(bank)), width=1, paving=TRAV)
    W_["quay_n"] = L.street([bank[0], (62, bank[0][1])], width=1, paving=EARTH)
    W_["bank"] = bank
    # Decks where ways cross water: the canal and the Tiber (stone spans), the basin channel.
    for s in (W_["portus_road"], W_["mole"], W_["portus"], W_["portuensis"]):
        for c, r in Line(s.points, s.width).tiles():
            if (c, r) in wet:
                lc, lr = c - L.origin[0], r - L.origin[1]
                L.paint(Rect(lc, lr, lc, lr), wet[(c, r)])
                L.place("world.bridge_arch", at=(lc, lr), face="north")
    # The river and canals lie at the sea's level, a step below the town: the ways step down
    # to the decks.
    landings(L)
    return W_


def _orth_tiles(pts) -> list:
    """A chain of tiles made 4-connected (a step in both axes becomes two steps)."""
    out = [pts[0]]
    for c, r in pts[1:]:
        pc, pr = out[-1]
        while (pc, pr) != (c, r):
            if pc != c:
                pc += 1 if c > pc else -1
            else:
                pr += 1 if r > pr else -1
            out.append((pc, pr))
    return out


def _portus(L: Layout) -> None:
    L.place(R + "portus_hexagon", rect=HEXAGON, name="portus_hexagon")
    L.place(R + "portus_lighthouse", rect=LIGHTHOUSE, name="portus_lighthouse")
    # Mooring posts along both moles, their ships in Claudius's basin.
    for c in range(4, 11, 2):
        put(L, R + "quay", (c, 11), face="south")
    for c in range(6, 12, 2):
        put(L, R + "quay", (c, 31), face="north")
    # Warehouses, the customs yard and a few lodgings along the service street.
    C.quarter(L, "portus", Rect(0, 0, 16, 9) | Rect(38, 2, 40, 23), PORT, 0.06, 5, 0.04, 0.0,
              ground=EARTH, urban=URBAN)
    for c, r in ((5, 10), (8, 10), (12, 13), (13, 22), (14, 24)):
        put(L, R + "r_amphorae", (c, r), variant=(c + r) % 4)
    put(L, R + "r_crane", (11, 13))
    put(L, R + "r_statue", (16, 9), face="west")
    put(L, R + "r_altar", (2, 22), face="south")
    L.lane("portus", [(6, 38), (4, 32), (4, 26), (12, 27)], kind="sea",
           ports={"sea_s": 0, "sea_w": 1, "claudius": 3})
    # Up the canal from the Tiber to the foot of the Portus street's bridge (an arch that passes
    # no barge: art-smooth-land.md §8), where the basin's goods are handed on.
    L.lane("portus_canal", [(42, 16), (39, 16)], kind="river", ports={"tiber": 0, "hexagon": 1})


def _ostia(L: Layout, W_: dict) -> None:
    # The forum and the Capitolium; the theatre on the decumanus with the square of the shipping
    # offices behind it.
    L.paint(FORUM, TRAV)
    L.place(R + "ostia_capitolium", rect=CAPITOLIUM, name="ostia_capitolium")
    L.place(R + "ostia_guilds", rect=GUILDS, name="ostia_guilds")
    if R + "ostia_theatre" in L.cat.items:
        L.place(R + "ostia_theatre", rect=THEATRE, name="ostia_theatre")
    # Mooring posts on the river bank in front of the quay street.
    wet = C.water_mask(L)
    for c, r in W_["bank"][::3]:
        if wet[r, c - 2] and not wet[r, c - 1]:
            put(L, R + "quay", (c - 1, r), face="west")
    for at in ((44, 40), (53, 40), (49, 45)):
        put(L, R + "r_statue", at, face="north")
    put(L, R + "r_lacus", (50, 41), face="north")
    put(L, R + "r_altar", (51, 39), face="north")
    L.paint(Rect(50, 30, 61, 31) & free(L, Rect(50, 30, 61, 31)), TRAV)
    put(L, R + "r_bath_small", (56, 40), face="north")
    put(L, R + "r_vigiles", (40, 40), face="north")
    # Warehouses and insulae between the river quays and the cardo; the town's insulae, shops,
    # bakeries and fulleries in lanes off the decumanus.
    civic = FORUM | CAPITOLIUM | GUILDS | THEATRE
    river_side = TOWN & Rect(38, GATE_ROW, 62, 23)
    C.quarter(L, "ostia_river", river_side - civic, PORT, 0.05, 6, 0.06, 0.01,
              ground=EARTH, urban=URBAN, fill_front=0.3)
    C.quarter(L, "ostia", (TOWN - civic) - river_side, TOWN_KIT, 0.04, 6, 0.1, 0.02,
              ground=EARTH, urban=URBAN, fill_front=0.5,
              shop_kit={R + "r_bakery": 1, R + "r_fullonica": 1, R + "r_thermopolium": 2,
                        R + "r_taberna": 3, R + "r_compitum": 1, R + "r_lacus": 1})


def _country(L: Layout) -> None:
    # Tombs both sides of the Via Ostiensis outside the Porta Romana, pines behind them.
    road = [s for s in L.streets if s.portal == "ostiensis"][0]
    for c, r in Line(road.points, 1).path():
        lc, lr = c - L.origin[0], r - L.origin[1]
        if lr > GATE_ROW - 3 or lr % 3:
            continue
        put(L, [R + "r_tomb", R + "tomb_house", R + "tomb_altar"][lr // 4 % 3], (lc - 2, lr),
            face="east")
        put(L, R + "tomb_altar", (lc + 2, lr), face="west")
    L.row(Line([(67, 1), (67, GATE_ROW - 2)], 1), R + "t_stone_pine", every=3)
    L.row(Line([(60, 1), (60, GATE_ROW - 2)], 1), R + "t_cypress", every=4)
    # The Isola Sacra: the cemetery along the road from Portus, market gardens, pines.
    for r in range(29, 35):
        for c in (24, 28):
            if rng.hash64("ostia", "isola", c, r) % 2 == 0:
                put(L, R + "tomb_house", (c, r), face="east" if c < 26 else "west")
    for c in range(28, 38, 3):
        put(L, R + "r_tomb", (c, 37), face="north")
    isola = Poly([(0, 32), (14, 30), (36, 28), (31, 35), (25, 45), (0, 45)])
    L.fields(isola & Rect(6, 37, 24, 44), FIELD, plot=(4, 3), path=EARTH, seed="isola_fields")
    L.scatter(isola, {R + "t_stone_pine": 3, R + "t_cypress": 1, R + "p_poppy": 2}, 0.06,
              seed="isola_green", clump=0.6)
    # Market gardens outside the gate, between the river and the road.
    L.fields(Rect(54, 1, 59, GATE_ROW - 2), FIELD, plot=(3, 3), path=EARTH, seed="north_gardens")
    L.scatter(Rect(40, 0, 70, GATE_ROW - 1), {R + "p_cabbage": 2, R + "t_olive": 1,
                                             R + "r_well": 0.3}, 0.05, seed="gardens")
    L.scatter(Rect(0, 0, 70, 55), {R + "t_stone_pine": 2, R + "t_oak": 1, R + "p_poppy": 3,
                                   R + "p_reeds": 0.5}, 0.03, seed="country", clump=0.7)
    banks = Line(RIVER, 10) - Line(RIVER, 8) - L.sea_below()
    L.scatter(banks, {R + "p_reeds": 3, R + "t_poplar": 1}, 0.2, seed="tiber_banks")


NODES = {
    "portus": (26, 21), "portus_mole": (8, 11), "hexagon_quay": (37, 10), "isola_tombs": (26, 32),
    "tiber_bridge": (40, 36), "ostia_forum": (45, 42), "ostia_guilds": (56, 30),
    "ostia_capitolium": (48, 38), "ostia_theatre": (58, 38), "river_quay": (45, 26), "porta_romana": (63, GATE_ROW),
    "decumanus": (60, 38),
    "salt_pans": (56, 46), "ostiensis_tombs": (63, 5),
}


def _night(L: Layout) -> None:
    """Lit nights (W1): the lighthouse, braziers where the customs men and the granaries' guards
    kept watch, lamps along the moles and round Trajan's basin where ships lay overnight, the
    Porta Romana's torches, and in the town the counters, shrines and crossings."""
    night_posts(L, R + "r_brazier", [NODES[n] for n in ("portus", "hexagon_quay", "portus_mole",
                                                        "porta_romana", "river_quay")], ring=3, gap=6)
    quays = [(c, 10) for c in range(3, 12, 4)] + [(c, 20) for c in range(18, 37, 6)] + \
        [(37, r) for r in range(3, 20, 6)] + [(c, 1) for c in range(19, 37, 6)]
    night_posts(L, R + "r_lamp", quays, ring=1, gap=4)
    night_posts(L, R + "r_lamp", [NODES[n] for n in ("ostia_forum", "ostia_theatre", "ostia_guilds",
                                                     "tiber_bridge", "decumanus", "ostia_capitolium")],
                ring=3, gap=5, kin=(R + "r_compitum",))
    town = np.isin(L.DIST, [i for i, d in enumerate(L.districts) if d.endswith(("town", "forum"))])
    night_posts(L, R + "r_lamp", crossings(L, town, gap=8), ring=2, gap=7, kin=(R + "r_compitum",))


def _nodes(L: Layout) -> None:
    C.snap_nodes(L, NODES)
    L.lane("tiber_ostia", RIVER[:6], kind="river", ports={"rome": 0, "ostia_quay": 4, "mouth": 5})
