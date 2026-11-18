"""Babylon, spring c. 470 BC (docs/design/sets/world.md §4.3).

World rect C 1036..1071, R 285..316; local (c, r) = world (C - 1036, R - 285); local level 0 =
world level 1. The Euphrates runs through from c 12, r 1 to c 20, r 27 (the base's river). On the
east bank the Royal Road comes in over the north edge (portal `babylon_n`) through the Ishtar Gate
(c 30..35, r 1..4) and down the processional way (c 32..33, r 5..18) toward Etemenanki (c 20..31,
r 17..28; shown standing, its state under Xerxes is debated); the inner wall runs west of the gate
(c 18..29, r 2..3) with towers every three tiles; houses of the east bank between them; the road
leaves east for Susa (portal `babylon_e`). On the west bank houses among date palms, groves north
of the wall, shadufs on the canal banks; river boats land at a quay (lane `babylon`); a
timber bridge stands in for the stone-piered bridge Herodotus describes (1.186).
"""

from worldgen import waypoint as WP
from worldgen import finish as F
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

ROYAL, EARTH, BRICK = "world.road_royal", "parsa.packed_earth", "parsa.paving_stone"
HOUSES = {"parsa.p_house": 3, "parsa.p_house_small": 2}
RIVER = [(12, 0), (12, 1), (14, 12), (16, 27), (17, 31)]


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "city")
    land = L.land_below()
    L.paint(Rect(0, 0, W - 1, H - 1), "world.alluvium")
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    L.district("east_bank", Rect(17, 4, W - 1, H - 1))
    L.district("west_bank", Rect(0, 4, 16, H - 1))
    L.district("groves", Rect(0, 0, W - 1, 3))

    # Ways: the processional way from the gate south, the road east, the canal roads.
    proc = WP.portal_street(L, "babylon_n", [(32, 20)], width=2, paving=BRICK)
    east = WP.portal_street(L, "babylon_e", [(34, 20), (33, 20)], width=1, paving=ROYAL)
    town = [L.street([(31, 9), (22, 9), (22, 15)], width=1, paving=EARTH),
            L.street([(31, 14), (25, 14)], width=1, paving=EARTH),
            L.street([(34, 6), (34, 16)], width=1, paving=EARTH)]
    quay = L.street([(14, 22), (4, 22), (4, 8), (11, 8)], width=1, paving=EARTH)
    west = [L.street([(4, 14), (22, 14)], width=1, paving=EARTH)]   # over the river
    L.channel([(3, 22), (3, 3), (11, 3)], terrain="world.river")
    L.level(Line([(3, 22), (3, 3), (11, 3)], 1), -1)

    # Landmarks, the river, the wall and towers, the houses.
    L.place("parsa.ishtar_gate", rect=(30, 1, 35, 4), name="ishtar_gate")
    L.place("parsa.processional_way", rect=(32, 5, 33, 18), name="processional_way")
    L.place("parsa.etemenanki", rect=(20, 17, 31, 28), name="etemenanki")
    L.river(RIVER, width=4, terrain="world.river", banks={"world.t_reeds": 0.3}, seed="euphrates")
    L.level(Line(RIVER, 4), WP.river_level(L, RIVER, -1))
    F.fords(L, west, item="world.bridge_timber")
    F.fords(L, [quay])
    for c in range(18, 30):
        for r in (2, 3):
            if (c - 18) % 3 == 0 and r == 2:
                put(L, "parsa.babylon_tower", (c, 2))
            elif L.fits("parsa.babylon_wall", (c, r)):
                L.place("parsa.babylon_wall", at=(c, r))
    L.houses(Rect(17, 5, 31, 16), HOUSES, front=town, gap=0.12, seed="east")
    L.houses(Rect(5, 9, 11, 21) | Rect(0, 23, 15, H - 1), HOUSES, front=[quay, *west], gap=0.15,
             seed="west")
    # Palms along the water, shadufs on the canal, groves north of the wall.
    for r in range(6, 22, 7):
        put(L, "world.shaduf", (2, r), face="east")
    L.scatter(Rect(0, 4, 3, H - 1) | Rect(0, 0, 17, 1), {"parsa.t_date": 3, "world.t_palm": 2},
              0.4, seed="palms", clump=0.4)
    L.scatter(Rect(18, 0, 29, 1), {"parsa.t_date": 2, "parsa.t_pomegranate": 1}, 0.5, seed="grove")
    WP.harbour_lane(L, "babylon", [(13, 22), (13, 10)], port="babylon", home="quay")
    L.node("ishtar_gate", (32, 5))
    L.node("etemenanki_court", (32, 20))
    L.node("babylon_quay", (13, 22))
    L.node("west_bank", (4, 14))
    WP.finish(L, "world.earth", {"parsa.p_house_small": 0, "parsa.p_house": 1})
    for name, rect in (("ishtar_gate", (30, 1, 35, 4)), ("etemenanki", (20, 17, 31, 28))):
        L.expect(name, rect=rect, level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
    L.view("gate", Rect(16, 0, W - 1, 20))
