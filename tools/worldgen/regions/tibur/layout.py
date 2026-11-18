"""Tibur, April AD 126: a roadside stop at the end of the Via Tiburtina (world.md §4.1).

World rect C 272..303, R 40..79; local (c, r) = world (C - 272, R - 40); local level 0 = world
level 2. The road comes up from the Appia over the south edge (portal `tiburtina`, c 4) onto
the plain below the hills, where olive groves, a farm and a travertine quarry stand; the hills
keep their relief. Hadrian's villa and the round temple above the falls have no art: the card
says so, and the stop is built from common Roman pieces.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Rect

R = "rome."
EARTH, GRASS = R + "packed_earth", R + "grass_spring"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "hills")
    plain = Rect(0, 24, 15, H - 1)
    L.paint(plain, GRASS)
    L.level(plain, 0, face=R + "tufa")
    L.district("plain", plain)
    road = WP.portal_street(L, "tiburtina", [(4, 28), (13, 28)], width=1, paving=EARTH)
    lane = L.street([(8, 28), (8, 33), (13, 33)], width=1, paving=EARTH)
    put(L, R + "r_villa_farm", (1, 29), face="east")
    put(L, R + "r_domus", (9, 24), face="south")
    put(L, "world.quarry", (11, 34), face="north")
    put(L, R + "r_well", (5, 27))
    put(L, R + "r_milestone", (5, 36), face="west")
    put(L, R + "r_altar", (12, 27), face="south")
    L.scatter(Rect(0, 34, 7, H - 2) | Rect(9, 29, 15, 32), {R + "t_olive": 5, R + "t_cypress": 1},
              0.35, seed="olives", clump=0.3)
    L.node("tibur_farm", (8, 28))
    WP.finish(L, R + "earth")
    L.view("whole", Rect(0, 20, 20, H - 1))
