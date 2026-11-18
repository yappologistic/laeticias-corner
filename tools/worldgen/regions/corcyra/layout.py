"""Kerkyra (Corcyra), summer 432 BC: a harbour stop on the Ionian route (world.md §4.2).

World rect C 440..455, R 200..225; local (c, r) = world (C - 440, R - 200); local level 0 = world
level 1. A small town on the island's east shore: a quay along the water, a mole and a jetty,
the harbour lane out to the Ionian lane's port `corcyra`; houses and a shrine inland. The
archaic temple of Artemis has no art: the card says so, and the stop uses common Greek pieces.
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
import numpy as np

from worldgen.shapes import Mask, Rect

EARTH, GRAVEL = "athens.packed_earth", "athens.gravel"
HOUSES = {"athens.g_house": 2, "athens.g_house_small": 3, "athens.g_house_two": 1}


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "island")
    dry = Mask(0, 0, np.isin(L.T, [i for i, t in enumerate(L.terrains) if not L.cat.is_water(t)]))
    L.level(dry & Rect(2, 4, 12, 20), 0)
    L.district("harbour", Rect(11, 6, W - 1, 18))
    quay = L.street([(11, 8), (11, 16)], width=1, paving=GRAVEL)
    main = L.street([(11, 12), (4, 12), (4, 18), (9, 18)], width=1, paving=EARTH)
    lane = L.street([(8, 12), (8, 6), (10, 6)], width=1, paving=EARTH)
    for r in (10, 11, 12):
        if L.cat.is_water(L.terrain_at(12 + L.origin[0], r + L.origin[1]) or ""):
            L.place("world.mole", at=(12, r))
    if L.cat.is_water(L.terrain_at(12 + L.origin[0], 15 + L.origin[1]) or ""):
        L.place("world.jetty", at=(12, 15))
    put(L, "world.beacon", (11, 7))
    put(L, "athens.g_shrine", (5, 19), face="north")
    put(L, "athens.g_statue_base", (6, 19), face="north")
    put(L, "athens.g_well", (5, 11))
    L.houses(Rect(2, 4, 10, 11) | Rect(5, 13, 10, 17), HOUSES, front=[main, lane], gap=0.15,
             seed="town")
    L.scatter(Rect(0, 0, 13, 3) | Rect(0, 21, 13, H - 1), {"athens.t_olive": 3,
              "athens.t_cypress": 1, "world.p_maquis": 2}, 0.2, seed="island", clump=0.5)
    WP.harbour_lane(L, "corcyra", [(13, 13), (13, 16)], port="corcyra", home="harbour")
    L.node("corcyra_quay", (11, 12))
    WP.finish(L, "athens.earth")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
