"""The Euphrates crossing, spring c. 470 BC (docs/design/sets/world.md §4.3).

World rect C 1008..1023, R 170..185; local (c, r) = world (C - 1008, R - 170); local level 0 =
world level 4. The river (c 6..9) with landing stages on both banks (r 7..9) where round hide
boats (quffa, Herodotus 1.194) ferry goods across on their lane; a bridge of boats beside them
carries the Royal Road, so caravans and couriers cross on foot (the site and the means are
uncertain: Xenophon's army waded at Thapsacus); a relay station on the east bank (c 11..14,
r 3..6); a camp of tents on the west bank (c 0..3, r 10..13); tamarisks, reeds and poplars.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

ROYAL, EARTH = "world.road_royal", "parsa.packed_earth"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "crossing")
    L.paint(Rect(0, 0, W - 1, H - 1), "world.steppe")
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    west = WP.portal_street(L, "euph_w", [(4, 8), (4, 11), (5, 11)], width=1, paving=EARTH)
    east = WP.portal_street(L, "euph_e", [(11, 8), (11, 11), (10, 11)], width=1, paving=EARTH)
    river = [(7, 0), (7, 15)]
    L.river(river, width=4, terrain="world.river", banks=None, seed="euphrates")
    L.level(Line(river, 4), 0)  # flush with its banks, as the kit decks are drawn (the base meets it)
    # The bridge of boats on row 11, the ferry's landing stages on row 8.
    for c in range(6, 10):
        L.place("world.pontoon", at=(c, 11))
    L.place("world.jetty", at=(6, 8))
    L.place("world.jetty", at=(9, 8))
    L.lane("quffa_ferry", [(7, 8), (8, 8)], kind="river",   # between the stages' heads
           ports={"start": 0, "end": 1, "west_landing": 0, "east_landing": 1})
    WP.harbour_lane(L, "euphrates_boats", [(8, 13), (8, 15)], port="crossing", home="landing")
    L.place("world.royal_station", rect=(11, 3, 14, 6), face="south", name="euphrates_station")
    put(L, "parsa.p_trough", (12, 7))
    for at in ((0, 10), (2, 12)):
        put(L, "parsa.p_tent", at)
    put(L, "parsa.p_well", (1, 9))
    L.district("river", Line(river, 6))
    L.scatter(Rect(0, 0, W - 1, H - 1) - Rect(0, 7, W - 1, 12),
              {"world.t_tamarisk": 2, "parsa.t_poplar": 2, "world.t_reeds": 2}, 0.2, seed="banks")
    L.node("west_bridge", (5, 11))
    L.node("east_bridge", (10, 11))
    L.edge("west_bridge", "east_bridge", kind="bridge")
    L.node("west_landing", (4, 8))
    L.node("euph_station", (11, 8))
    WP.finish(L, "world.earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
