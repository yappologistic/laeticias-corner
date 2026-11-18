"""Eleusis, summer 432 BC (docs/design/sets/world.md §4.2; athens.md §3.7).

World rect C 556..575, R 222..250; local (c, r) = world (C - 556, R - 222); local level 0 = world
level 1. The acropolis hill in the north-west (+2..3, limestone); the Telesterion (10 x 10, the
Periclean rebuilding under way) on its terrace against it, inside the sanctuary wall; the gate
faces the Sacred Way, which arrives straight from Athens' Sacred Gate across the east edge
(portal `sacred_way_w`); the town below the sanctuary; the shore of the bay in the south; the
Megarid road leaves west (portal `eleusis_w`); stubble fields of the Thriasian plain.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Poly, Rect

GRAVEL, EARTH, STUBBLE = "athens.gravel", "athens.packed_earth", "athens.field_stubble"
HOUSES = {"athens.g_house": 2, "athens.g_house_two": 2, "athens.g_house_small": 3}


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "plain")
    # The bay of Eleusis: shore from row 24, sea one level below the land.
    sea = (L.sea_below() & Rect(0, 24, W - 1, H - 1)) | \
        Poly([(4, 25), (12, 24), (19, 24), (19, 28), (4, 28)])
    land = Rect(0, 0, W - 1, H - 1) - sea
    L.level(land, 0)
    L.paint(land, "athens.dry_grass")
    L.paint(sea, "world.sea")
    L.level(sea, -1)
    L.district("shore", sea | Rect(0, 23, W - 1, 24))
    L.level(Rect(0, 23, W - 1, 24) - sea, 0, face="athens.earth")

    # The acropolis hill, limestone, the sanctuary terrace against its south-east foot.
    hill = Poly([(0, 0), (7, 0), (7, 4), (3, 5), (2, 9), (0, 9)]) - Rect(3, 5, 15, 17)
    WP.raise_levels(L, hill, top=3, base=1, face="world.rock", steps=2)
    L.paint(hill, "athens.rock_limestone")
    L.district("acropolis", hill)
    terrace = Rect(3, 5, 15, 17) - hill
    L.level(terrace, 1, face="athens.limestone")
    L.paint(terrace, GRAVEL)
    L.district("sanctuary", Rect(3, 5, 15, 17))

    # Ways: the Sacred Way from Athens to the gate stair; the town street to the Megarid road.
    sacred = WP.portal_street(L, "sacred_way_w", [(18, 14), (18, 11)], width=1, paving=GRAVEL)
    town = WP.portal_street(L, "eleusis_w", [(17, 18), (17, 14)], width=1, paving=EARTH)
    court = L.street([(15, 11), (14, 11), (14, 16), (5, 16)], width=1, paving=GRAVEL)
    L.level(Line([(15, 11), (14, 11), (14, 16), (5, 16)], 1), 1)
    for r in (10, 11):
        L.stair("athens.stair_marble", rect=(16, r, 17, r), face="east",
                name="gate_stair" if r == 11 else None)
    shore = L.street([(9, 19), (9, 23)], width=1, paving=EARTH)

    # The Telesterion on its terrace, the wall round the sanctuary with the gate on the way.
    L.place("athens.telesterion", rect=(4, 6, 13, 15), name="telesterion")
    ring = [(15, 5), (15, 9)], [(15, 12), (15, 17)], [(3, 17), (15, 17)], [(8, 5), (15, 5)]
    for pts in ring:
        L.wall(Line(list(pts), 1), "athens.g_wall")
    put(L, "athens.g_wall_tower", (14, 3))
    put(L, "athens.g_brazier", (13, 16))
    put(L, "athens.g_stele_inscr", (14, 6))
    put(L, "athens.g_statue_base", (14, 8))

    # The town: houses facing the street, wells and shrines in the yards.
    L.district("town", Rect(0, 17, 16, 22) | Rect(16, 12, 19, 22))
    L.houses(Rect(0, 18, 16, 22) | Rect(18, 15, 19, 22), HOUSES, front=[town, shore],
             gap=0.15, seed="town")
    for at in ((5, 21), (12, 21)):
        put(L, "athens.g_well", at)
    put(L, "athens.g_shrine", (16, 13))
    put(L, "athens.g_herm", (19, 13), face="west")

    # The shore: a jetty into the bay, nets drying, a fishing boat's lane.
    for r in range(25, 28):
        L.place("world.jetty", at=(9, r))
    put(L, "world.drying_rack", (8, 23))
    put(L, "world.fish_hut", (11, 22), face="west")
    L.lane("eleusis_fishing", [(9, 27), (14, 27)], kind="sea",
           ports={"home": 0, "grounds": 1, "start": 0, "end": 1})

    # The Thriasian plain: stubble with balks; olives and cypresses on the slopes.
    L.district("fields", Rect(8, 0, W - 1, 4))
    L.fields(Rect(8, 0, W - 1, 4), STUBBLE, plot=(4, 2), path=EARTH, seed="plain")
    L.scatter(Rect(0, 0, W - 1, 24) - Rect(3, 5, 15, 17) - Rect(0, 17, 19, 23),
              {"athens.t_olive": 3, "athens.t_cypress": 1, "athens.p_thyme": 2}, 0.12,
              seed="slopes", clump=0.6)
    L.row(Line([(18, 0), (18, 9)], 1), "athens.t_cypress", every=3)

    L.node("telesterion", (14, 13))
    L.node("eleusis_town", (9, 19))
    L.node("eleusis_shore", (9, 23))
    WP.finish(L, "athens.limestone", {"athens.g_house_small": 0, "athens.g_house_two": 1})
    L.expect("telesterion", rect=(4, 6, 13, 15), level=1)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
