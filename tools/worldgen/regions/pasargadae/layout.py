"""Pasargadae, spring c. 470 BC (docs/design/sets/world.md §4.3).

World rect C 1176..1203, R 260..287; local (c, r) = world (C - 1176, R - 260); local level 0 =
world level 5. The tomb of Cyrus on its six steps (c 4..8, r 18..22) with the magi's guardhouse
beside it (Arrian 6.29); Palace P facing its garden of narrow stone channels and square basins
(c 12..23, r 4..13), cypresses and planes along the channels; the road from Pārsa comes in over
the south edge (portal `pasargadae_s`, c 14) and runs north to the garden; paths to the tomb.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import night_posts, put
from worldgen.shapes import Line, Rect

ROYAL, GRAVEL = "world.road_royal", "parsa.gravel"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "plain")
    L.paint(Rect(0, 0, W - 1, H - 1), "parsa.plain_grass")
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    L.district("garden", Rect(10, 2, 25, 15))
    L.district("tomb", Rect(1, 15, 12, 25))
    road = WP.portal_street(L, "pasargadae_s", [(14, 15)], width=2, paving=ROYAL)
    L.street([(14, 15), (24, 15), (24, 3), (11, 3), (11, 15), (14, 15)][0:3], width=1,
             paving=GRAVEL)
    L.street([(24, 15), (24, 3), (11, 3), (11, 14)], width=1, paving=GRAVEL)
    tomb_path = L.street([(14, 23), (10, 23), (10, 22)], width=1, paving=GRAVEL)
    L.place("parsa.pasargadae_garden", rect=(12, 4, 23, 13), name="pasargadae_garden")
    L.place("parsa.cyrus_tomb", rect=(4, 18, 8, 22), name="cyrus_tomb")
    L.place("parsa.p_house_small", rect=(9, 20, 10, 21), face="south", name="magi_house")
    # Channels round the garden, cypresses and planes beside them.
    L.wall(Line([(11, 2), (25, 2)], 1), "parsa.p_channel")
    L.row(Line([(12, 14), (23, 14)], 1), "parsa.t_cypress", every=2)
    L.row(Line([(25, 4), (25, 13)], 1), "parsa.t_plane", every=3)
    L.row(Line([(10, 4), (10, 13)], 1), "parsa.t_cypress", every=2)
    put(L, "parsa.p_fire_altar", (7, 24))
    L.fields(Rect(16, 17, W - 1, 25), "parsa.field_barley", plot=(4, 3), path="parsa.packed_earth",
             seed="fields")
    L.scatter(Rect(0, 0, 9, 14) | Rect(0, 26, W - 1, H - 1),
              {"parsa.t_almond": 1, "world.t_pistachio": 1, "parsa.p_steppe": 3}, 0.1,
              seed="plain")
    L.node("pasargadae_garden", (14, 15))
    L.node("cyrus_tomb", (10, 23))
    # The Magi who kept Cyrus' tomb lived beside it and watched it by night (Arrian 6.29);
    # torches at the garden's gates.
    night_posts(L, "parsa.p_brazier", [(11, 19), (7, 17)], ring=3, gap=4)
    night_posts(L, "parsa.p_torch", [(12, 14), (18, 14), (14, 12)], ring=2, gap=3)
    WP.finish(L, "parsa.earth")
    L.expect("pasargadae_garden", rect=(12, 4, 23, 13), level=0)
    L.expect("cyrus_tomb", rect=(4, 18, 8, 22), level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
