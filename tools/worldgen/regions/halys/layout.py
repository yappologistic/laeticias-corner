"""The Halys crossing, spring c. 470 BC (docs/design/sets/world.md §4.3; Herodotus 5.52).

World rect C 950..965, R 120..135; local (c, r) = world (C - 950, R - 120); local level 0 = world
level 5. The river runs north (c 5..7); on its west bank the gates with their towers and guard
post straddle the Royal Road (c 0..3, r 6..13); a timber bridge carries the road over (r 9..10);
on the east bank a relay station (c 10..13, r 4..7) and a watchtower (c 12..13, r 11..12).
"""

from worldgen import waypoint as WP
from worldgen import finish as F
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

ROYAL = "world.road_royal"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "crossing")
    L.paint(Rect(0, 0, W - 1, H - 1), "world.steppe")
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    road = WP.portal_street(L, "halys_w", [(9, 9)], width=2, paving=ROYAL)
    road_e = WP.portal_street(L, "halys_e", [(9, 9)], width=2, paving=ROYAL)
    yard = L.street([(11, 9), (11, 8)], width=1, paving="parsa.packed_earth")
    river = [(6, 15), (6, 0)]   # the Halys flows north
    L.river(river, width=3, terrain="world.river", banks={"world.t_reeds": 0.35}, seed="halys")
    L.level(Line(river, 3), WP.river_level(L, river, -1))
    F.fords(L, [road, road_e], item="world.bridge_timber")
    L.place("parsa.halys_gates", rect=(0, 6, 3, 13), name="halys_gates")
    L.place("world.royal_station", rect=(10, 4, 13, 7), face="south", name="halys_station")
    L.place("world.watchtower", at=(12, 11), face="north")
    put(L, "parsa.p_trough", (13, 8))
    put(L, "parsa.p_well", (14, 11))
    L.district("road", Rect(0, 8, W - 1, 11))
    L.scatter(Rect(0, 0, W - 1, H - 1) - Rect(0, 4, 15, 13), {"parsa.t_poplar": 2,
              "parsa.t_willow": 2, "parsa.p_steppe": 3}, 0.15, seed="banks", clump=0.5)
    L.node("halys_station", (11, 8))
    WP.finish(L, "world.earth")
    L.expect("halys_gates", rect=(0, 6, 3, 13), level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
