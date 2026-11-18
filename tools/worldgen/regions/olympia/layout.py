"""Olympia, summer 432 BC: a stop at the end of the road along the gulf (world.md §4.2).

World rect C 470..491, R 320..340; local (c, r) = world (C - 470, R - 320); local level 0 = world
level 1. The road comes in over the north edge (portal `olympia_n`, c 8) to the Altis, Zeus'
precinct, on a level bench (+2): its wall, altars, statue bases, the sacred olives and planes;
priests' houses outside it; the Alpheios below in the south. The temple of Zeus, Pheidias'
workshop and the stadium have no art: the card says so, and the stop uses common Greek pieces.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

EARTH, GRAVEL = "athens.packed_earth", "athens.gravel"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "valley")
    bench = Rect(0, 0, 14, 12)
    L.level(bench, 2, face="athens.earth")
    L.paint(bench, "athens.dry_grass")
    L.district("altis", Rect(1, 2, 12, 10))
    road = WP.portal_street(L, "olympia_n", [(8, 6), (3, 6)], width=1, paving=EARTH)
    path = L.street([(8, 6), (8, 11), (13, 11)], width=1, paving=GRAVEL)
    for c in range(1, 13):
        for r in (2, 10):
            if (c, r) not in ((8, 2), (8, 10)):
                put(L, "athens.g_wall", (c, r))
    for at in ((4, 4), (6, 4), (10, 4), (4, 8), (10, 8)):
        put(L, "athens.g_statue_base", at, face="south")
    put(L, "athens.g_shrine", (6, 8), face="north")
    put(L, "athens.g_shrine", (11, 6), face="west")
    put(L, "athens.g_well", (9, 5))
    L.row(Line([(2, 3), (12, 3)], 1), "athens.t_olive", every=3)
    L.row(Line([(2, 9), (12, 9)], 1), "athens.t_plane", every=4)
    L.houses(Rect(9, 12, 14, 12) | Rect(0, 11, 7, 12), {"athens.g_house_small": 2,
             "athens.g_house_two": 1}, front=[path], gap=0.2, seed="priests")
    L.scatter(Rect(15, 0, W - 1, 13), {"athens.t_olive": 2, "world.p_maquis": 2}, 0.15,
              seed="hills", clump=0.5)
    L.node("altis", (8, 6))
    WP.finish(L, "athens.earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
