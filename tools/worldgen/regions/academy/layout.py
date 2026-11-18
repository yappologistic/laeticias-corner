"""The Academy (Akademeia), summer 432 BC (docs/design/sets/world.md §4.2; athens.md §3.7).

World rect C 560..575, R 205..219; local (c, r) = world (C - 560, R - 205); local level 0 = world
level 1, the grove's ground at local 1. The gymnasium in its grove of sacred olives and planes
(`academy_grove`, 12 x 10) with the altar of Prometheus where the torch races start; the road
from the Dipylon comes in over the east edge (portal `academy_e`, from Athens' `academy_road_n`
by the base) between grave stelai, as the public cemetery lined it.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

EARTH = "athens.packed_earth"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "grove")
    L.level(Rect(0, 0, W - 1, H - 1), 1)
    L.paint(Rect(0, 0, W - 1, H - 1), "athens.dry_grass")
    L.paint(Rect(2, 1, 15, 12), "athens.olive_soil")
    WP.portal_street(L, "academy_e", [(15, 12), (2, 12)], width=1, paving=EARTH)
    L.place("athens.academy_grove", rect=(3, 2, 14, 11), name="academy_grove")
    # Grave stelai and a mound facing the road outside the grove (the public cemetery).
    for c in (9, 11, 13):
        put(L, "athens.g_grave_stele", (c, 13), face="north")
    put(L, "athens.g_grave_mound", (14, 13))
    put(L, "athens.g_herm", (15, 11), face="west")
    # The sacred olives and planes round the gymnasium, a plane avenue on the walk.
    L.row(Line([(2, 14), (14, 14)], 1), "athens.t_plane", every=3)
    L.scatter(Rect(0, 0, W - 1, H - 1) - Rect(3, 2, 14, 11),
              {"athens.t_olive": 4, "athens.t_plane": 1, "athens.t_cypress": 0.5}, 0.35,
              seed="moriai", clump=0.4)
    L.node("academy", (8, 12))
    WP.finish(L, "athens.earth")
    L.expect("academy_grove", rect=(3, 2, 14, 11), level=1)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
