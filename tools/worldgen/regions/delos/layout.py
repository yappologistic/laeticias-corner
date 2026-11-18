"""Delos, summer 432 BC (docs/design/sets/world.md §4.2).

World rect C 775..790, R 330..345; local (c, r) = world (C - 775, R - 330); local level 0 = world
level 1. The island (enlarged in the plan for its sanctuary) with the sacred harbour on its west
shore (moles; the lane `delos` meets the Aegean base lane), the sanctuary of Apollo (the old
poros temple, the unfinished marble temple, the Artemision: c 4..13, r 2..9), the terrace of the
Naxian lions facing the sacred lake, Kynthos rising in the east (+3). Graves are still on the
island in 432 (the purification of 426/5 moved them to Rheneia). Rows are two higher than the
design's plan so the lake stays inside the island.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Ellipse, Line, Poly, Rect

EARTH, GRAVEL = "athens.packed_earth", "athens.gravel"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "island")
    island = Poly([(2, 1), (14, 1), (15, 5), (15, 9), (14, 14), (9, 15), (2, 15), (2, 5)])
    sea = Rect(0, 0, W - 1, H - 1) - island
    L.paint(sea, "world.sea")
    L.level(sea, -1)
    L.paint(island, "athens.dry_grass")
    L.level(island, 0)
    L.district("sea", sea)
    L.district("sanctuary", Rect(3, 1, 13, 13))
    # Kynthos: rock rising east of the sanctuary.
    kynthos = Ellipse(15, 8, 1.5, 4) & island
    WP.raise_levels(L, kynthos, top=3, base=1, face="world.rock", steps=1)
    L.paint(kynthos, "world.rock")
    L.district("kynthos", kynthos)
    L.paint(Rect(4, 2, 13, 9), GRAVEL)
    lake = Rect(6, 13, 10, 13)    # a walk between the lions and the lake, where people look
    L.paint(lake, "world.shallows")
    L.level(lake, -1)

    # Ways: from the harbour along the sanctuary's west side, round the lake to the lions.
    L.street([(2, 8), (3, 8), (3, 14), (12, 14), (12, 10)], width=1, paving=GRAVEL)
    L.street([(3, 8), (3, 3)], width=1, paving=GRAVEL)
    L.street([(3, 12), (12, 12)], width=1, paving=GRAVEL)
    L.place("athens.delos_sanctuary", rect=(4, 2, 13, 9), name="delos_sanctuary")
    # The lions on their terrace north of the lake (8 x 2), facing it.
    L.place("athens.naxian_lions", rect=(4, 10, 11, 11), name="naxian_lions")
    for r in range(7, 11):
        if L.terrain_at(1 + L.origin[0], r + L.origin[1]) == "world.sea":
            L.place("world.mole", at=(1, r))
    put(L, "world.beacon", (2, 6))
    WP.harbour_lane(L, "delos", [(1, 11), (0, 12)], port="delos", home="sacred_harbour")
    put(L, "athens.g_house", (4, 12), face="east")
    for at in ((13, 12), (13, 13)):
        put(L, "athens.g_grave_stele", at, face="west")
    L.scatter(island - Rect(3, 1, 13, 14), {"athens.p_thyme": 2, "world.p_maquis": 1}, 0.3,
              seed="scrub")
    L.node("delos_harbour", (3, 9))
    L.node("lions", (8, 14))
    L.expect("delos_sanctuary", rect=(4, 2, 13, 9), level=0)
    L.expect("naxian_lions", rect=(4, 10, 11, 11), level=0)
    WP.finish(L, "athens.limestone")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
