"""Delphi, summer 432 BC (docs/design/sets/world.md §4.2).

World rect C 500..519, R 250..265; local (c, r) = world (C - 500, R - 250); local level 0 = world
level 3. The Phaedriades stand as cliffs along the north (r 0..3, +6..8, impassable); the temple
terrace (+2) holds the Alkmaeonid temple of Apollo (c 6..17, r 4..9, front east) behind its
polygonal wall; the Athenian treasury below it (+1); the Sacred Way comes up from the olive slope
(portal `delphi_s`, c 18, r 15), zigzags west, climbs to the treasury's level, runs back east
past statue bases and inscribed stelai and climbs to the temple's east front. No theatre: the
stone theatre is 4th century; its site is open slope.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Poly, Rect

EARTH, GRAVEL = "world.road_earth", "athens.gravel"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "slope")
    L.paint(Rect(0, 0, W - 1, H - 1), "athens.dry_grass")
    L.level(Rect(0, 13, W - 1, H - 1), 0)                     # the olive slope
    L.level(Rect(0, 10, W - 1, 12), 1, face="athens.limestone")   # the treasury's bench
    terrace = Rect(4, 4, W - 1, 9)
    L.level(Rect(0, 4, 3, 9), 3, face="world.rock")
    L.level(terrace, 2, face="athens.ashlar")                 # the polygonal wall
    L.paint(terrace, GRAVEL)
    cliffs = Rect(0, 0, W - 1, 3)
    WP.raise_levels(L, cliffs, top=8, base=6, face="world.rock", steps=1)
    L.paint(cliffs, "world.rock")
    L.impassable(cliffs)
    L.district("sanctuary", Rect(0, 4, W - 1, 12))
    L.district("cliffs", cliffs)

    # The Sacred Way: up from the slope, west, a flight to the bench, east, a flight up.
    WP.portal_street(L, "delphi_s", [(5, 15)], width=1, paving=EARTH)
    L.stair("world.stair_stone", rect=(5, 13, 5, 14), face="south", name="way_stair_low")
    L.street([(5, 12), (18, 12)], width=1, paving=EARTH)
    L.stair("world.stair_stone", rect=(18, 10, 18, 11), face="south", name="way_stair_high")
    L.level(Rect(18, 10, 18, 11), 1)
    L.street([(18, 9), (18, 4)], width=1, paving=GRAVEL)

    L.place("athens.delphi_apollo", rect=(6, 4, 17, 9), name="delphi_apollo")
    L.place("athens.athenian_treasury", rect=(3, 10, 5, 11), name="athenian_treasury")
    # Dedications along the way; the great altar's brazier before the east front.
    for c in range(7, 17, 2):
        put(L, "athens.g_statue_base", (c, 10), face="south")
        put(L, "athens.g_stele_inscr", (c + 1, 14), face="south")
    put(L, "athens.g_brazier", (19, 6))
    put(L, "athens.g_brazier", (19, 8))
    put(L, "athens.g_shrine", (4, 9))
    # Olives in the Pleistos valley below, laurel and cypress by the sanctuary.
    L.scatter(Rect(0, 13, W - 1, H - 1), {"athens.t_olive": 4, "athens.p_thyme": 1}, 0.3,
              seed="olives", clump=0.5)
    L.scatter(Rect(0, 4, 3, 9) | Rect(19, 10, 19, 12),
              {"athens.t_laurel": 2, "athens.t_cypress": 1}, 0.4, seed="laurel")
    L.node("temple", (18, 6))
    L.node("treasury", (6, 12))
    WP.finish(L, "athens.limestone")
    L.expect("delphi_apollo", rect=(6, 4, 17, 9), level=2)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
