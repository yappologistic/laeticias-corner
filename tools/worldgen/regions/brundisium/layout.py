"""Brundisium, April AD 126 (docs/design/sets/world.md §4.1; rome.md §3.7).

World rect C 380..407, R 248..279; local (c, r) = world (C - 380, R - 248); local level 0 = world
level 1, the sea at -1 (world 0). The Via Appia comes in from the west (portal `appia_brund_w`,
c 0, r 18) and ends at the marker column (c 12, r 18) before the harbour: the branching natural
harbour with its quays and warehouses (`brundisium_harbour`, c 8..23, r 6..17: a warehouse quay
along its north side, the basin drawn south of it, open to the east), the open sea beyond, a mole off each end (the west one from the fishermen's
shore, the east one closing the eastern arm, its beacon at the root), ships for Greece on the
lane that meets the Ionian crossing at the harbour mouth. The town lies south of the road:
insulae, warehouses, shops and a few domus in lanes off a cardo and a decumanus.
"""

import importlib.util
from pathlib import Path

import numpy as np

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put, seam
from worldgen.shapes import Mask, Poly, Rect

_spec = importlib.util.spec_from_file_location(
    "worldgen_region_rome_common", Path(__file__).resolve().parent.parent / "rome" / "common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

R = "rome."
BASALT, TRAV, EARTH, GRASS = (R + "basalt_paving", R + "travertine_paving", R + "packed_earth",
                              R + "grass_spring")
HARBOUR = Rect(8, 6, 23, 17)
COLUMN = (12, 18)
ROAD = 18                                  # the Appia's row (two tiles wide: r 18..19)
TOWN = Rect(1, 21, 26, 31)
SEA = Poly([(3, 0), (27, 0), (27, 15), (24, 15), (24, 5), (3, 5)])
URBAN: list = []
KIT = ({R + "r_insula": 2, R + "r_horrea": 1.5, R + "r_insula_low": 1.5, R + "r_domus": 1},
       {R + "r_insula_low": 2})


def build(L: Layout) -> None:
    URBAN.clear()
    W, H = L.size
    WP.ground(L, "town")
    sea = C.mask(L, SEA) | C.mask(L, L.sea_below())
    sea &= ~C.mask(L, HARBOUR)
    land = ~sea
    L.paint(Mask(0, 0, land), GRASS)
    L.level(Mask(0, 0, land), 0)
    L.paint(Mask(0, 0, sea), "world.sea")
    L.level(Mask(0, 0, sea), -1)
    L.paint(Mask(0, 0, sea & _near(land, 1)), "world.shallows")
    L.district("sea", Mask(0, 0, sea))
    L.district("harbour", HARBOUR | Rect(0, 6, 7, 11))
    L.district("town", TOWN)
    L.district("road", Rect(0, ROAD - 1, W - 1, ROAD + 2))

    # The Appia to its end at the column; a way round the harbour's west side onto its quays.
    WP.portal_street(L, "appia_brund_w", [(COLUMN[0] - 1, ROAD)], width=2, paving=BASALT)
    L.street([(7, ROAD), (7, 10)], width=1, paving=TRAV)
    L.street([(COLUMN[0] - 1, ROAD + 2), (13, ROAD + 2), (13, H - 1)], width=1, paving=BASALT)
    L.street([(1, 25), (26, 25)], width=1, paving=BASALT)
    L.street([(13, ROAD + 2), (25, ROAD + 2), (25, 16)], width=1, paving=EARTH)
    L.paint(HARBOUR, TRAV)
    harbour = L.place(R + "brundisium_harbour", rect=HARBOUR, name="brundisium_harbour")
    _quay_way(L, harbour)
    put(L, R + "r_column_honor", COLUMN)

    # Moles: the west one off the fishermen's shore, the east one closing the eastern arm.
    for r in range(1, 6):
        if sea[r, 6]:
            L.place("world.mole", at=(6, r))
    for c in range(24, 28):
        if sea[15, c]:
            L.place("world.mole", at=(c, 15))
    put(L, "world.beacon", (24, 16))
    for at in ((1, 6), (3, 6)):
        put(L, "world.fish_hut", at, face="south")
    for at in ((2, 9), (4, 9), (1, 11)):
        put(L, "world.drying_rack", at)

    # The town: warehouses toward the harbour, insulae and domus, shops on the streets.
    C.quarter(L, "brundisium", TOWN, KIT, 0.06, 6, 0.1, 0.03, ground=EARTH, urban=URBAN,
              fill_front=0.4)
    L.scatter(Rect(0, ROAD + 2, W - 1, ROAD + 2) | Rect(0, 12, 6, ROAD - 1),
              {R + "t_stone_pine": 1, R + "t_cypress": 1, R + "p_poppy": 2}, 0.12, seed="green")
    for at in ((3, ROAD - 2), (9, ROAD + 3)):
        put(L, R + "r_tomb", at, face="south" if at[1] < ROAD else "north")

    # From the basin (drawn inside the harbour, south of its warehouse quay) out through its
    # eastern mouth to the harbour mouth, where the base's lanes meet it.
    WP.harbour_lane(L, "brundisium", [(16, 13), (25, 12)], port="brundisium", home="quay")
    L.node("column", (COLUMN[0] - 1, ROAD))
    L.node("brundisium_quay", (8, 10))
    L.node("brundisium_town", (13, 25))
    C.drop_bad_spots(L)
    WP.finish(L, "world.earth", {R + "r_insula_low": 0})
    for area, ground in URBAN:
        L.paint(Mask(0, 0, area & (L.OCC < 0) & ~L.STREET & (L.T == L.terrains.index(GRASS))),
                ground)
    URBAN.clear()
    seam(L, GRASS, EARTH)
    L.expect("brundisium_harbour", rect=HARBOUR, level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))


def _near(m: np.ndarray, d: int) -> np.ndarray:
    out = m.copy()
    for _ in range(d):
        g = out.copy()
        g[1:, :] |= out[:-1, :]
        g[:-1, :] |= out[1:, :]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        out = g
    return out


def _quay_way(L: Layout, harbour) -> None:
    """A way along the harbour's quays over its walk tiles, from the west side (c 7, r 10)
    to the eastern arm (no paint: the floor under them is the quay's paving)."""
    if harbour is None:
        return
    walk = {(c - L.origin[0], r - L.origin[1]) for c, r in L.walk_tiles(harbour)}
    a = (7, 10)
    goal = max(walk, key=lambda t: (t[0], -t[1])) if walk else None
    prev, todo = {a: None}, [a]
    for t in todo:
        for dc, dr in ((1, 0), (0, -1), (0, 1), (-1, 0)):
            n = (t[0] + dc, t[1] + dr)
            if n not in prev and n in walk:
                prev[n] = t
                todo.append(n)
    if goal not in prev:
        return
    path = [goal]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    L.street(C.corners(path[::-1]), width=1, paving=None)
