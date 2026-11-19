"""Tibur, April AD 126: the town where the Via Tiburtina ends below the hills (world.md §4.1).

World rect C 272..303, R 40..79; local (c, r) = world (C - 272, R - 40); local level 0 = world
level 2. The road comes up from the Appia over the south edge (portal `tiburtina`, c 4) and is
the town's main street on the plain below the hills: houses, shops and a bakery along it and
along a cross street, a fountain and a crossroads shrine where they meet, an altar; south of the
houses the olive farm and its groves, east of them the travertine quarry. The hills keep their
relief. Hadrian's villa and the round temple above the falls have no art: the card says so, and
the town is built from common Roman pieces.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import night_posts, put
from worldgen.shapes import Rect

R = "rome."
EARTH, GRASS = R + "packed_earth", R + "grass_spring"


HOUSES = {R + "r_insula_low": 3, R + "r_taberna": 2, R + "r_thermopolium": 1}


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "hills")
    plain = Rect(0, 24, 15, H - 1)
    town = Rect(0, 24, 15, 33)
    L.paint(plain, GRASS)
    L.level(plain, 0, face=R + "tufa")
    L.district("plain", plain)
    L.district("town", town)
    road = WP.portal_street(L, "tiburtina", [(4, 28), (13, 28)], width=1, paving=EARTH)
    lane = L.street([(8, 28), (8, 33), (13, 33)], width=1, paving=EARTH)
    north = L.street([(4, 28), (4, 25), (12, 25)], width=1, paving=EARTH)
    put(L, R + "r_domus", (9, 26), face="north")
    put(L, R + "r_bakery", (5, 29), face="west")
    put(L, R + "r_lacus", (5, 27))
    put(L, R + "r_compitum", (3, 27))
    put(L, R + "r_altar", (13, 26), face="south")
    L.houses(Rect(0, 24, 3, 33), HOUSES, front=[road, north], gap=0.15, seed="west")
    L.houses(Rect(5, 29, 7, 33), HOUSES, front=[road, lane], gap=0.15, seed="mid")
    L.houses(Rect(9, 29, 15, 32), HOUSES, front=[road, lane], gap=0.15, seed="east")
    L.houses(town, {R + "r_taberna": 3, R + "r_thermopolium": 1, R + "r_smithy": 1},
             front=[road, north, lane], gap=0.05, seed="fill")
    put(L, R + "r_villa_farm", (1, 35), face="east")
    put(L, "world.quarry", (11, 34), face="north")
    put(L, R + "r_well", (5, 35))
    put(L, R + "r_milestone", (5, 37), face="west")
    L.scatter(Rect(0, 38, 9, H - 1) | Rect(5, 34, 9, 36), {R + "t_olive": 5, R + "t_cypress": 1},
              0.35, seed="olives", clump=0.3)
    L.node("tibur_farm", (8, 28))
    night_posts(L, R + "r_lamp", [(6, 31), (2, 30), (12, 31)], ring=2, gap=3)   # shops kept open
    night_posts(L, R + "r_brazier", [(10, 36), (3, 37)], ring=2, gap=4)   # quarry and farm yards
    WP.finish(L, R + "earth")
    L.view("whole", Rect(0, 20, 20, H - 1))
