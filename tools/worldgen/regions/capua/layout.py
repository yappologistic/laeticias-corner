"""Capua, April AD 126: a roadside stop on the Via Appia (docs/design/sets/world.md §4.1).

World rect C 318..333, R 198..213; local (c, r) = world (C - 318, R - 198); local level 0 = world
level 1. The Appia crosses east-west on r 12..13 between its two portals; along it a posting
station, shops, a fountain and tombs, houses behind. The city's amphitheatre and its other
monuments have no art: the stop is built from the common Roman pieces, as its card says.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Rect

R = "rome."
BASALT, EARTH, GRASS = R + "basalt_paving", R + "packed_earth", R + "grass_spring"
HOUSES = {R + "r_insula_low": 2, R + "r_domus": 1, R + "r_taberna": 2}


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "town")
    L.paint(Rect(0, 0, W - 1, H - 1), GRASS)
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    L.district("road", Rect(0, 11, W - 1, 14))
    road = WP.portal_street(L, "appia_capua_w", [(8, 12)], width=2, paving=BASALT)
    road_e = WP.portal_street(L, "appia_capua_e", [(8, 12)], width=2, paving=BASALT)
    north = L.street([(7, 11), (7, 3), (13, 3)], width=1, paving=EARTH)
    south = L.street([(10, 14), (10, 15)], width=1, paving=EARTH)
    put(L, R + "mutatio", (1, 5), face="south")
    put(L, R + "r_lacus", (9, 11), face="south")
    put(L, R + "r_milestone", (4, 14), face="north")
    L.houses(Rect(8, 0, W - 1, 10), HOUSES, front=[north, road_e], gap=0.15, seed="north")
    L.houses(Rect(0, 0, 6, 4), {R + "r_taberna": 1, R + "r_insula_low": 1}, front=[north],
             gap=0.2, seed="corner")
    tombs = [R + "r_tomb", R + "tomb_house", R + "tomb_altar", R + "r_tomb"]
    for k, c in enumerate(range(0, W - 1, 4)):
        put(L, tombs[k % 4], (c, 14 if c != 8 else 15), face="north")
    L.scatter(Rect(0, 15, W - 1, H - 1), {R + "t_stone_pine": 2, R + "t_cypress": 2,
              R + "r_vine": 3}, 0.2, seed="south", clump=0.5)
    L.node("capua_station", (7, 11))
    WP.finish(L, R + "earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
