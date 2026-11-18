"""Sidon, spring c. 470 BC: a harbour stop at the end of the Levant road (world.md §4.3).

World rect C 990..1007, R 300..340; local (c, r) = world (C - 990, R - 300); local level 0 = world
level 1. The road comes down the coast over the north edge (portal `sidon_n`, c 10) along a
strip above the shore: houses, a mole and a jetty with the harbour lane to the Levant lane's
port `sidon`, cedar logs stacked on the strand, cedars on the slope. The temple of Eshmun has
no art: the card says so, and the stop uses common pieces.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
import numpy as np

from worldgen.shapes import Mask, Rect

EARTH = "parsa.packed_earth"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "shore")
    strip = Rect(9, 0, 15, 30)
    dry = Mask(0, 0, np.isin(L.T, [i for i, t in enumerate(L.terrains) if not L.cat.is_water(t)]))
    L.level(dry & strip, 0, face="world.earth")
    L.district("town", strip)
    road = WP.portal_street(L, "sidon_n", [(11, 0), (11, 26)], width=1, paving=EARTH)
    for r in range(18, 22):
        if L.cat.is_water(L.terrain_at(8 + L.origin[0], r + L.origin[1]) or ""):
            L.place("world.mole", at=(8, r))
    if L.cat.is_water(L.terrain_at(8 + L.origin[0], 23 + L.origin[1]) or ""):
        L.place("world.jetty", at=(8, 23))
    put(L, "world.beacon", (9, 17))
    for at in ((9, 25), (9, 27)):
        put(L, "world.log_stack", at, face="west")
    L.houses(Rect(12, 2, 15, 28), {"parsa.p_house": 1, "parsa.p_house_small": 3}, front=[road],
             gap=0.15, seed="town")
    put(L, "parsa.p_well", (10, 12))
    L.scatter(Rect(16, 0, W - 1, H - 1), {"world.t_cedar": 3, "world.p_maquis": 1}, 0.25,
              seed="slope", clump=0.6)
    WP.harbour_lane(L, "sidon", [(7, 22)], port="sidon", home="quay")
    L.node("sidon_quay", (11, 22))
    WP.finish(L, "world.earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
