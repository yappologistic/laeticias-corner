"""The Alban Mount, April AD 126 (docs/design/sets/world.md §4.1; rome.md §3.7).

World rect C 278..311, R 130..175; local (c, r) = world (C - 278, R - 130); local level 0 = world
level 2. The mount rises from the Via Appia at its foot (r 42..43) to the summit at +8, where the
sanctuary of Jupiter Latiaris stands in its precinct (`latiaris`, c 18..23, r 4..9): the consuls
held the Latin Festival here each year. The paved Via Sacra climbs the south face straight up to
it, a flight a level. West of the summit the crater lake (Lacus Albanus) lies in its rim at +3;
oak and beech woods cover the upper slopes; villas stand on the lower ones; the Liris crosses the
east side to the sea under an arch of the Appia. The Appia comes in from Rome a level lower
(portal `appia_alban_w`, world 1) and climbs one ramp to leave east (`appia_alban_e`, world 2),
tombs, cypresses and milestones along it.
"""

import importlib.util
from pathlib import Path

import numpy as np

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Ellipse, Line, Mask, Rect

_spec = importlib.util.spec_from_file_location(
    "worldgen_region_rome_common", Path(__file__).resolve().parent.parent / "rome" / "common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

R = "rome."
BASALT, TRAV, EARTH = R + "basalt_paving", R + "travertine_paving", R + "packed_earth"
GRASS, FLOOR = R + "grass_spring", "world.forest_floor"
SUMMIT = Rect(17, 3, 24, 11)            # the precinct's platform, the temple in it
TEMPLE = Rect(18, 4, 23, 9)
LAKE = Ellipse(9.5, 20.5, 6.0, 7.0)     # the crater (c 4..15, r 14..27)
WATER = Ellipse(9.5, 20.5, 4.6, 5.6)
ROAD_ROW = 42                           # the Appia, two tiles wide (r 42..43)
SACRA = 20                              # the Via Sacra's column up the south face
FOOT = 35                               # where it leaves the flat to climb


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "slopes")
    wet = C.water_mask(L)               # the Liris, as the base carves it
    lv = _relief(L, wet)
    L.paint(Mask(0, 0, ~wet), GRASS)
    L.level(Mask(0, 0, ~wet), 0)
    C.write_levels(L, np.where(wet, L.LV, lv),
                   lambda k, m: [("world.rock", m & (lv >= 6)), ("world.earth", m & (lv < 6))])
    L.paint(Mask(0, 0, (lv >= 6) & ~C.mask(L, SUMMIT) & ~wet), "world.rock")
    lake = C.mask(L, WATER)
    L.paint(Mask(0, 0, lake), "water")
    L.level(Mask(0, 0, lake), 3)
    L.district("lake", LAKE)
    L.district("summit", SUMMIT)
    L.district("woods", Mask(0, 0, (lv >= 4) & ~C.mask(L, SUMMIT | LAKE)))
    L.district("road", Rect(0, ROAD_ROW - 3, W - 1, ROAD_ROW + 4))

    # The Via Sacra up the south face to the precinct, a flight a level.
    L.street([(SACRA, ROAD_ROW - 1), (SACRA, FOOT)], width=1, paving=BASALT)
    top = WP.climb(L, [(SACRA, FOOT), (SACRA, SUMMIT.r1)], 0, rise=8, paving=BASALT)
    # A track along the foot of the slopes to the villas.
    L.street([(SACRA - 1, 37), (2, 37)], width=1, paving=EARTH)
    _appia(L, wet)
    L.paint(SUMMIT, TRAV)
    L.level(SUMMIT, top, face="world.rock")
    L.street([(SUMMIT.c0, SUMMIT.r1), (SUMMIT.c1, SUMMIT.r1)], width=1, paving=TRAV)
    L.place(R + "latiaris", rect=TEMPLE, name="latiaris")
    for at in ((17, 4), (24, 4), (17, 9), (24, 9)):
        put(L, R + "r_statue", at, face="south")
    put(L, R + "r_altar", (22, 11 - 1), face="south")

    # Villas on the lower slopes above the track, their vineyards behind them.
    for c in (3, 9, 14):
        L.level(Rect(c, 34, c + 2, 36), 0)            # each villa on its own terrace
        put(L, R + "r_villa_farm", (c, 34), face="south")
    C.grove(L, C.mask(L, Rect(2, 29, 17, 33)) & ~wet, "alban_vines", R + "r_vine",
            step=(1, 2), soil=R + "vineyard_soil")
    L.scatter(Rect(0, 29, 18, 39), {R + "t_stone_pine": 2, R + "t_cypress": 1}, 0.05,
              seed="villas")

    # Oak and beech on the upper slopes, olives and poppies lower down, reeds on the shore.
    woods = Mask(0, 0, (L.LV >= 4) & ~C.mask(L, SUMMIT) & ~lake & ~L.STREET)
    L.paint(woods, FLOOR)
    L.scatter(woods, {"world.t_oak": 3, "world.t_beech": 2, R + "t_oak": 1}, 0.32,
              seed="woods", clump=0.6)
    lower = Mask(0, 0, (L.LV >= 1) & (L.LV < 4) & ~lake & ~wet)
    L.scatter(lower, {R + "t_olive": 2, R + "t_oak": 1, R + "p_poppy": 2}, 0.08, seed="slopes",
              clump=0.5)
    shore = Mask(0, 0, C.mask(L, LAKE) & ~lake)
    L.scatter(shore, {R + "p_reeds": 2, R + "t_poplar": 1}, 0.25, seed="shore")

    L.node("latiaris", (SACRA, SUMMIT.r1))
    L.node("villas", (8, 37))
    L.node("appia_foot", (SACRA, ROAD_ROW))
    WP.finish(L, "world.earth", {R + "r_villa_farm": 0})
    L.expect("latiaris", rect=TEMPLE, level=8)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
    L.view("summit", Rect(8, 0, 30, 18))


def _relief(L: Layout, wet: np.ndarray) -> np.ndarray:
    """The mount as a level array: +8 on the summit platform falling a level every three tiles
    (the Via Sacra's climb), the crater rim at +4..5 round the lake at +3, the flat at the
    Appia's level; steeper toward the north and east edges so they meet the plain outside, and
    the Liris' valley left as the base carved it."""
    H, W = L.T.shape
    cc, rr = np.meshgrid(np.arange(W), np.arange(H))
    dc = np.maximum(np.maximum(SUMMIT.c0 - cc, cc - SUMMIT.c1), 0)
    dr = np.maximum(SUMMIT.r0 - rr, 0) * 1.4 + np.maximum(rr - SUMMIT.r1, 0)
    d = np.hypot(dc * 0.8, dr)
    lv = np.clip(8 - np.floor(d / 3), 0, 8).astype(np.int32)
    crater = C.mask(L, LAKE)
    ring = C.mask(L, Ellipse(9.5, 20.5, 8.0, 9.0)) & ~crater
    lv[ring] = np.maximum(lv[ring], 4)
    lv[C.mask(L, Ellipse(9.5, 20.5, 7.0, 8.0)) & ~crater] = np.maximum(
        lv[C.mask(L, Ellipse(9.5, 20.5, 7.0, 8.0)) & ~crater], 5)
    lv[crater] = 3
    lv = np.minimum(lv, 2 * rr)                               # down to the plain in the north
    lv = np.minimum(lv, 2 * (W - 1 - cc))                     # and in the east
    lv = np.minimum(lv, cc + 1)                               # and in the west
    near = np.zeros_like(wet)
    for k in range(-3, 4):
        near |= np.roll(wet, k, axis=1) | np.roll(wet, k, axis=0)
    lv[near] = 0
    lv[rr >= ROAD_ROW - 2] = 0
    return lv


def _appia(L: Layout, wet: np.ndarray) -> None:
    """The Via Appia: a level lower from Rome (west portal) to a ramp at c 6..9, then on at the
    mount's foot over the Liris' arch to the east portal; tombs, trees and milestones."""
    W, H = L.size
    WP.portal_street(L, "appia_alban_w", [(5, ROAD_ROW)], width=2, paving=BASALT)
    for r in (ROAD_ROW, ROAD_ROW + 1):
        L.level(Rect(6, r, 9, r), -1)
        L.stair("world.ramp", rect=(6, r, 9, r), face="west")
    east = WP.portal_street(L, "appia_alban_e", [(10, ROAD_ROW)], width=2, paving=BASALT)
    for c, r in Line(east.points, east.width).tiles():
        lc, lr = c - L.origin[0], r - L.origin[1]
        if 0 <= lc < W and 0 <= lr < H and wet[lr, lc]:
            L.paint(Rect(lc, lr, lc, lr), L.below_terrain(lc, lr))
            L.level(Rect(lc, lr, lc, lr), L.below_level(lc, lr))
            L.place("world.bridge_arch", at=(lc, lr), face="north")
    tombs = [R + "r_tomb", R + "tomb_house", R + "tomb_altar", R + "tomb_drum"]
    for k, c in enumerate(range(3, W - 2, 4)):
        side = ROAD_ROW - 2 if k % 2 == 0 else ROAD_ROW + 2
        face = "south" if side < ROAD_ROW else "north"
        if put(L, tombs[k % 4], (c, side - (1 if side < ROAD_ROW and k % 4 in (0, 1, 3) else 0)),
               face=face):
            put(L, R + "t_cypress", (c + 2, side), face=face)
    put(L, R + "r_milestone", (14, ROAD_ROW + 2), face="north")
    put(L, R + "r_milestone", (30, ROAD_ROW - 1), face="south")
    L.scatter(Rect(0, ROAD_ROW + 3, W - 1, H - 1), {R + "t_stone_pine": 1, R + "p_poppy": 2,
                                                    R + "t_olive": 1}, 0.06, seed="campagna")
