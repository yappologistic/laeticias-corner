"""Corinth, summer 432 BC (docs/design/sets/world.md §4.2).

World rect C 553..575, R 280..305; local (c, r) = world (C - 553, R - 280); local level 0 = world
level 1. Lechaion on the gulf in the north-west (moles, a beacon, the lane `lechaion` meets the
Ionian route's base lane); the town with the archaic temple of Apollo (c 4..15, r 10..15); the
diolkos (c 16..17, r 0..19), the paved ship trackway across the isthmus; Kenchreai on the
Saronic side (c 17..22, r 14..19; lane `kenchreai`); Acrocorinth as ground (c 0..10, r 16..25,
rising to +7) with the summit sanctuary on top and a stepped path up. The Megarid road arrives
over the north edge (portal `corinth_n`).
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Ellipse, Line, Poly, Rect

EARTH, GRAVEL = "athens.packed_earth", "athens.gravel"
HOUSES = {"athens.g_house": 2, "athens.g_house_two": 2, "athens.g_house_small": 3}


def sea_at(L: Layout, c: int, r: int) -> bool:
    return L.terrain_at(c + L.origin[0], r + L.origin[1]) == "world.sea"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "land")
    gulf = Poly([(0, 0), (12, 0), (11, 3), (8, 7), (0, 8)])
    saronic = Poly([(18, 12), (22, 10), (22, 25), (13, 25), (14, 24), (18, 23), (18, 17)])
    sea = gulf | saronic
    land = Rect(0, 0, W - 1, H - 1) - sea
    L.paint(land, "athens.dry_grass")
    L.level(land, 0)
    L.paint(sea, "world.sea")
    L.level(sea, -1)
    L.district("harbours", sea | Rect(0, 7, 8, 9) | Rect(16, 13, 22, 20))
    # Acrocorinth: steep limestone, the summit at +7 with its little sanctuary.
    acro = Ellipse(5, 21, 6, 5) & Rect(0, 18, 11, H - 1)
    WP.raise_levels(L, acro, top=6, base=1, face="world.rock", steps=1)
    L.paint(acro, "athens.rock_limestone")
    L.district("acrocorinth", acro)

    # Ways: the road from the Megarid down to the town, streets, the diolkos' haul road.
    main = WP.portal_street(L, "corinth_n", [(13, 7), (3, 7), (3, 9)], width=1, paving=EARTH)
    # Round the temple (its footprint c 4..15, r 10..15 is solid), not through it.
    st1 = L.street([(13, 7), (13, 9)], width=1, paving=EARTH)
    st2 = L.street([(3, 9), (3, 17), (14, 17)], width=1, paving=EARTH)
    kench = L.street([(14, 17), (14, 22), (17, 22)], width=1, paving=EARTH)
    # The south gate: the road down the Argolid shore to Sparta and along the gulf to Olympia.
    WP.portal_street(L, "corinth_s", [(12, 22), (14, 22)], width=1, paving=EARTH)
    top = WP.climb(L, [(10, 17), (10, 25), (1, 25), (1, 21), (3, 21)], 0, rise=6,
                   paving=EARTH)
    L.level(Rect(4, 19, 6, 21), top)  # the summit bench, where the path arrives

    L.place("athens.corinth_apollo", rect=(4, 10, 15, 15), name="corinth_apollo")
    # Two tiles north of the town plan's r 2..21: the temple's east steps (c 16, r 12) then meet
    # the trackway's paved walk, not the hauling cradle's closed middle (W-L1).
    L.place("athens.diolkos", rect=(16, 0, 17, 19), name="diolkos")
    L.place("athens.acrocorinth_summit", rect=(4, 19, 6, 21), name="acrocorinth_summit")

    # Lechaion: a mole closing the basin, a beacon at its root, fishermen.
    for r in range(2, 7):
        if sea_at(L, 9, r):
            L.place("world.mole", at=(9, r))
    put(L, "world.beacon", (10, 8))
    for c in range(4, 8):
        put(L, "world.drying_rack", (c, 9)) if c % 2 == 0 else None
    WP.harbour_lane(L, "lechaion", [(5, 6), (2, 4)], port="lechaion", home="quay")
    # Kenchreai: a jetty and a mole on the Saronic shore.
    for c in range(18, 21):
        if sea_at(L, c, 22):
            L.place("world.jetty", at=(c, 22))
    for r in range(14, 18):
        if sea_at(L, 18, r):
            L.place("world.mole", at=(18, r))
    put(L, "world.beacon", (17, 13))
    WP.harbour_lane(L, "kenchreai", [(21, 22), (20, 24)], port="kenchreai", home="quay")

    L.district("town", Rect(1, 8, 14, 17))
    L.houses(Rect(0, 8, 14, 17) - Rect(4, 10, 15, 15), HOUSES, front=[main, st1, st2, kench],
             gap=0.12, seed="town")
    put(L, "athens.g_well", (2, 12))
    put(L, "athens.g_shrine", (12, 9))
    L.scatter(Rect(0, 0, W - 1, H - 1) - Rect(0, 8, 14, 17),
              {"athens.t_olive": 3, "athens.t_cypress": 1, "athens.t_pine": 1, "athens.p_thyme": 2},
              0.12, seed="country", clump=0.6)
    L.node("corinth_temple", (13, 9))
    L.node("lechaion", (5, 7))
    L.node("kenchreai", (17, 22))
    L.node("acrocorinth", (3, 21))
    WP.finish(L, "athens.limestone", {"athens.g_house_small": 0})
    L.expect("corinth_apollo", rect=(4, 10, 15, 15), level=0)
    L.expect("diolkos", rect=(16, 0, 17, 19), level=0)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
