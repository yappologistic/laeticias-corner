"""Beneventum, April AD 126: a roadside stop on the Via Appia (docs/design/sets/world.md §4.1).

World rect C 344..355, R 208..219; local (c, r) = world (C - 344, R - 208); local level 0 = world
level 2. The Appia runs east-west on r 5..6; where the Via Traiana branches south-east a lane
leaves between shops, an altar at the fork. Trajan's arch (dedicated 114) has no art: the card
says so; the stop is common Roman pieces.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import night_posts, put
from worldgen.shapes import Rect

R = "rome."
BASALT, EARTH, GRASS = R + "basalt_paving", R + "packed_earth", R + "grass_spring"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "town")
    L.paint(Rect(0, 0, W - 1, H - 1), GRASS)
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    L.district("road", Rect(0, 4, W - 1, 7))
    road = WP.portal_street(L, "appia_benev_w", [(6, 5)], width=2, paving=BASALT)
    road_e = WP.portal_street(L, "appia_benev_e", [(6, 5)], width=2, paving=BASALT)
    traiana = L.street([(7, 7), (7, 10), (W - 1, 10)], width=1, paving=EARTH)
    put(L, R + "r_altar", (6, 8), face="east")
    put(L, R + "r_milestone", (8, 7), face="north")
    L.houses(Rect(0, 0, W - 1, 3), {R + "r_insula_low": 2, R + "r_taberna": 3}, front=[road],
             gap=0.15, seed="north")
    L.houses(Rect(0, 8, 5, H - 1), {R + "r_domus": 1, R + "r_taberna": 2}, front=[road],
             gap=0.2, seed="west")
    L.houses(Rect(8, 8, W - 1, 9), {R + "r_insula_low": 1, R + "r_taberna": 2,
             R + "r_thermopolium": 1}, front=[traiana], gap=0.1, seed="fork")
    L.scatter(Rect(8, 11, W - 1, H - 1), {R + "t_olive": 2, R + "r_vine": 2}, 0.25, seed="fields",
              clump=0.5)
    L.node("beneventum_fork", (7, 7))
    night_posts(L, R + "r_lamp", [(9, 7), (3, 7)], ring=2, gap=3)   # the inn and shops at the fork
    WP.finish(L, R + "earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
