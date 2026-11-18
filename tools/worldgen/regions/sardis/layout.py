"""Sardis, spring c. 470 BC (docs/design/sets/world.md §4.3).

World rect C 860..879, R 200..219; local (c, r) = world (C - 860, R - 200); local level 0 = world
level 2. The Hermos crosses the north (r 6..10) with the Lydian royal mounds beyond it (Bin
Tepe); the lower town of reed-roofed mudbrick houses (Herodotus 5.101) on the road; the Paktolos
(c 4) comes down from the acropolis to the Hermos, gold washers on its banks; the acropolis rises
in the south (+2..+7) with the fortification on its crest, its flanks too steep above +5; the
first station of the Royal Road (`royal_road_head`) where the road leaves east (portal
`sardis_e`). The road from Ephesus comes in from the west (portal `sardis_w`). The acropolis and
the road head stand two rows south and east of the design's plan so they do not overlap.
"""

from worldgen import waypoint as WP
from worldgen import finish as F
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Ellipse, Line, Poly, Rect

ROYAL, EARTH = "world.road_royal", "parsa.packed_earth"
PAKTOLOS = [(4, 19), (4, 15), (4, 11), (5, 8)]


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "valley")
    land = L.land_below()
    L.level(land & Rect(0, 11, W - 1, H - 1), 0)
    L.paint(Rect(0, 11, W - 1, H - 1) & land, "world.steppe")
    L.level(Rect(0, 0, W - 1, 10) & land, 0)
    # The acropolis: eroded slopes of earth, the crest walled.
    acro = Ellipse(10, 17, 5, 3) & Rect(5, 14, 15, H - 1)
    WP.raise_levels(L, acro, top=5, base=1, face="world.earth", steps=1)
    L.impassable(Ellipse(10, 18, 3, 2) & Rect(7, 16, 13, H - 1))
    L.paint(acro, "world.scree")
    L.district("acropolis", acro)
    L.district("town", Rect(0, 10, W - 1, 13))
    L.district("mounds", Rect(0, 0, W - 1, 5))

    # The roads: from Ephesus in the west along the town to the road head and on east.
    west = WP.portal_street(L, "sardis_w", [(2, 14), (2, 12)], width=1, paving=EARTH)
    main = WP.portal_street(L, "sardis_e", [(2, 12)], width=2, paving=ROYAL)
    L.level(Line([(2, 14), (2, 12)], 1), 0)
    L.river(PAKTOLOS, width=1, terrain="world.river", banks={"world.t_reeds": 0.3},
            seed="paktolos")
    hermos = [(19, 8), (10, 8), (0, 8)]
    L.river(hermos, width=3, terrain="world.river", banks={"world.t_reeds": 0.3}, seed="hermos")
    L.level(Line(hermos, 3), WP.river_level(L, hermos, -1))
    F.fords(L, [west, main])
    L.place("parsa.royal_road_head", rect=(16, 14, 19, 17), name="royal_road_head")
    for c in (7, 12):
        put(L, "parsa.p_well", (c, 11))
    L.houses(Rect(0, 10, 14, 11) | Rect(5, 14, 16, 14) - acro, {"parsa.p_house_small": 3,
             "parsa.p_house": 1}, front=[main], gap=0.15, seed="town")
    # The crest's walls and towers.
    L.wall(Line([(7, 15), (13, 15)], 1), "parsa.fort_wall", tower="parsa.fort_tower", every=6)
    # Bin Tepe: three royal mounds north of the Hermos.
    for at in ((3, 1), (9, 0), (15, 2)):
        put(L, "world.tumulus", at, variant=0 if at[0] != 9 else 1)
    L.scatter(Rect(0, 0, W - 1, 5) | Rect(16, 12, W - 1, H - 1),
              {"parsa.t_poplar": 2, "parsa.p_steppe": 3, "parsa.t_willow": 1}, 0.12, seed="valley")
    L.node("sardis_station", (17, 13))
    L.node("paktolos", (5, 12))
    WP.finish(L, "world.earth")
    L.expect("royal_road_head", rect=(16, 14, 19, 17), level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
