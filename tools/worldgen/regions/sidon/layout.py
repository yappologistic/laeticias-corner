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


def _wet(L: Layout, c: int, r: int) -> bool:
    return L.cat.is_water(L.terrain_at(c + L.origin[0], r + L.origin[1]) or "")


def _pier(L: Layout, item: str, r: int, n: int) -> int | None:
    """Up to n pieces west from the first water tile west of the road on row r; returns the
    column of the piece that meets the strand."""
    c = 11
    while c > 0 and not _wet(L, c - 1, r):
        c -= 1
    first = c - 1
    for k in range(n):
        if first - k < 0 or not _wet(L, first - k, r):
            break
        L.place(item, at=(first - k, r))
    return first if first >= 0 and _wet(L, first, r) else None


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "shore")
    strip = Rect(9, 0, 15, 30)
    dry = Mask(0, 0, np.isin(L.T, [i for i, t in enumerate(L.terrains) if not L.cat.is_water(t)]))
    L.level(dry & strip, 0, face="world.earth")
    # The strand west of the road is the shore's, where the ships are built and the purple
    # boiled; the road and the houses are the town; the open water is the sea's (gulls).
    L.district("town", Rect(11, 0, 15, 30))
    L.district("sea", Mask(0, 0, ~dry.array))
    road = WP.portal_street(L, "sidon_n", [(11, 0), (11, 26)], width=1, paving=EARTH)
    # The mole and the jetty run west from the strand into the water (the base's coast decides
    # where the strand ends), one tile wide, met by the road's edge.
    mole = _pier(L, "world.mole", 18, 4)
    _pier(L, "world.jetty", 23, 3)
    if mole is not None:
        next((p for at in ((mole + 1, 17), (mole + 1, 16), (mole, 17), (mole + 1, 15))
              if (p := put(L, "world.beacon", at)) is not None), None)
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
