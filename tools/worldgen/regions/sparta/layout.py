"""Sparta, summer 432 BC: a stop at the end of the road from Corinth (world.md §4.2).

World rect C 515..535, R 360..385; local (c, r) = world (C - 515, R - 360); local level 0 = world
level 2. The road comes in over the east edge (portal `sparta_e`, r 12) and fords the Eurotas;
loose villages of farmhouses on the valley floor west of the river, no city wall (Sparta had
none), a shrine on open ground. The sanctuary of Athena of the Bronze House has no art: the
card says so, and the stop uses common Greek pieces.
"""

from worldgen import finish as F
from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Rect

EARTH = "athens.packed_earth"
FARMS = {"athens.g_farmstead": 2, "athens.g_house": 1, "athens.g_house_small": 2}


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "valley")
    floor = Rect(6, 3, 18, 22)
    L.level(floor, 0, face="athens.earth")
    L.paint(floor, "athens.dry_grass")
    L.district("villages", floor)
    road = WP.portal_street(L, "sparta_e", [(18, 12), (18, 8), (8, 8), (8, 20)], width=1,
                            paving=EARTH)
    F.fords(L, [road])      # over the Eurotas, flush with the valley floor
    lane = L.street([(8, 14), (16, 14), (16, 20)], width=1, paving=EARTH)
    L.houses(Rect(9, 3, 17, 7), FARMS, front=[road], gap=0.25, seed="north")
    L.houses(Rect(9, 15, 15, 21), FARMS, front=[lane], gap=0.25, seed="south")
    L.houses(Rect(6, 9, 7, 21), {"athens.g_house_small": 1}, front=[road], gap=0.3, seed="west")
    put(L, "athens.g_shrine", (12, 11), face="south")
    put(L, "athens.g_statue_base", (11, 11), face="south")
    put(L, "athens.g_well", (14, 9))
    L.scatter(Rect(9, 9, 17, 13) - Rect(11, 11, 14, 11), {"athens.t_olive": 2, "athens.t_plane": 1},
              0.2, seed="groves", clump=0.4)
    L.node("sparta_shrine", (12, 8))
    WP.finish(L, "athens.earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
