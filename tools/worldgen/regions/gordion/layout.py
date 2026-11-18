"""Gordion, spring c. 470 BC: a stop off the Royal Road (world.md §4.3).

World rect C 905..925, R 130..150; local (c, r) = world (C - 905, R - 130); local level 0 = world
level 5. A track from the Royal Road over the south edge (portal `gordion_s`, c 10) into the
walled citadel mound (c 8..18, r 10..18), houses and a shrine of Matar inside; the burial
mounds of the old kings north of it, the Sangarios to the east. The great mound has no art of
its own: the card says so; the cemetery is shown with the common tumulus.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Rect

EARTH = "parsa.packed_earth"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "plain")
    L.level(Rect(0, 9, 19, H - 1), 0)
    L.district("citadel", Rect(8, 10, 18, 18))
    road = WP.portal_street(L, "gordion_s", [(10, 15), (16, 15)], width=1, paving=EARTH)
    lane = L.street([(13, 15), (13, 11)], width=1, paving=EARTH)
    for c in range(8, 19):
        for r in range(10, 19):
            edge = c in (8, 18) or r in (10, 18)
            if edge and (c, r) != (10, 18):
                put(L, "parsa.fort_wall", (c, r))
    put(L, "world.matar_shrine", (15, 11), face="south")
    L.houses(Rect(9, 11, 17, 17) - Rect(13, 11, 16, 12), {"parsa.p_house_small": 3,
             "parsa.p_house": 1}, front=[road, lane], gap=0.2, seed="citadel")
    for at in ((2, 2), (7, 1), (12, 3), (3, 7)):
        put(L, "world.tumulus", at, variant=(at[0] // 5) % 2)
    L.scatter(Rect(0, 11, 6, H - 1), {"parsa.t_poplar": 1, "parsa.p_steppe": 3}, 0.15,
              seed="plain", clump=0.5)
    L.node("gordion_citadel", (13, 15))
    WP.finish(L, "world.earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
