"""Ephesus (Ephesos), summer 432 BC (docs/design/sets/world.md §4.2).

World rect C 832..851, R 235..255; local (c, r) = world (C - 832, R - 235); local level 0 = world
level 1. The harbour at the Kaystros mouth in the west (the lane `ephesus` meets the Aegean base
lane); the town on its slope in the north-east (+1..2) with the road east over the hills to
Sardis (portal `ephesus_e`); across the Kaystros on a timber bridge the archaic Artemision (c 2..17,
r 13..20, entrance west) in the wet plain, marsh and reeds round it.
"""

from worldgen import waypoint as WP
from worldgen import finish as F
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Poly, Rect

EARTH, GRAVEL = "athens.packed_earth", "athens.gravel"
HOUSES = {"athens.g_house": 2, "athens.g_house_two": 2, "athens.g_house_small": 3}
KAYSTROS = [(19, 9), (14, 9), (10, 10), (7, 10), (3, 10), (0, 10)]


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "plain")
    sea = Poly([(0, 2), (5, 2), (5, 7), (0, 8)])
    land = Rect(0, 0, W - 1, H - 1) - sea
    L.paint(land, "athens.dry_grass")
    L.level(land, 0)
    L.paint(sea, "world.sea")
    L.level(sea, -1)
    L.district("harbour", sea | Rect(0, 0, 8, 8))
    L.level(Rect(9, 1, W - 1, 8), 1, face="athens.earth")      # the town's slope
    L.district("town", Rect(9, 0, W - 1, 8))
    # The Kaystros to its mouth, marsh round the temple.
    marsh = Rect(0, 13, W - 1, H - 1)
    L.paint(marsh, "world.marsh")
    L.district("artemision", Rect(0, 9, W - 1, H - 1))

    # Ways: the Sardis road down steps through the town, steps to the harbour quay, over the
    # Kaystros on a timber bridge and round to the temple's west front.
    road = WP.portal_street(L, "ephesus_e", [(18, 6)], width=1, paving=EARTH)
    L.stair("world.stair_stone", rect=(16, 6, 17, 6), face="west", name="town_steps")
    upper = L.street([(15, 6), (9, 6)], width=1, paving=EARTH)
    L.level(Rect(9, 6, 15, 6), 1)
    L.stair("world.stair_stone", rect=(7, 6, 8, 6), face="west", name="harbour_steps")
    quay = L.street([(6, 6), (6, 8), (8, 8), (8, 12), (1, 12), (1, 13)], width=1, paving=GRAVEL)
    lanes = [L.street([(14, 6), (14, 2), (18, 2)], width=1, paving=EARTH),
             L.street([(11, 6), (11, 2)], width=1, paving=EARTH)]
    L.level(Line([(14, 6), (14, 2), (18, 2)], 1), 1)
    L.level(Line([(11, 6), (11, 2)], 1), 1)
    L.river(KAYSTROS, width=2, terrain="world.river", banks={"world.t_reeds": 0.4},
            seed="kaystros")
    L.level(Line(KAYSTROS, 2), 0)  # flush with the quay, as the kit bridge is drawn
    F.fords(L, [quay], item="world.bridge_timber")
    L.place("athens.artemision", rect=(2, 13, 17, 20), name="artemision")

    # The harbour: a mole, a jetty, merchants' quay.
    for r in range(3, 8):
        if L.terrain_at(5 + L.origin[0], r + L.origin[1]) == "world.sea":
            L.place("world.mole", at=(5, r))
    put(L, "world.beacon", (6, 2))
    WP.harbour_lane(L, "ephesus", [(4, 7), (2, 6)], port="ephesus", home="quay")
    L.houses(Rect(9, 0, W - 1, 8), HOUSES, front=[road, upper, *lanes], gap=0.12, seed="town")
    put(L, "athens.g_well", (16, 7))
    put(L, "athens.g_shrine", (12, 7))
    L.scatter(Rect(9, 0, W - 1, 9), {"athens.t_olive": 2, "athens.t_fig": 1}, 0.08, seed="yards")
    L.scatter(marsh - Rect(2, 13, 17, 20), {"world.t_reeds": 3, "athens.t_poplar": 1}, 0.35,
              seed="marsh")
    L.node("artemision", (1, 13))
    L.node("ephesus_harbour", (6, 8))
    L.node("ephesus_town", (10, 4))
    WP.finish(L, "athens.earth", {"athens.g_house_small": 0})
    L.expect("artemision", rect=(2, 13, 17, 20), level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
