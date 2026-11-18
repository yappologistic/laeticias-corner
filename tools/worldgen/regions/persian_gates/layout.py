"""The Persian Gates, spring c. 470 BC (docs/design/sets/world.md §4.3).

World rect C 1112..1127, R 330..345; local (c, r) = world (C - 1112, R - 330); local level 0 =
world level 6. A narrow defile: the road runs west to east along r 7..8, climbing two levels on
ramps from the west mouth (portal `gates_w`, world 4) to the east mouth (portal `gates_e`); cliffs
of limestone rise on both sides (+6..+9, impassable, snow on the tops, Persian oaks on ledges);
the walled station of the guards stands beside the road at the west mouth where the gorge widens
(north of the road rather than across it, so the road keeps its own line); a watchtower on a
ledge and a beacon above. A guarded pass on the road to Pārsa in 470 (the battle of 330 BC is
later; the site is debated).
"""

from worldgen import waypoint as WP
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

ROYAL = "world.road_royal"


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "pass")
    L.paint(Rect(0, 0, W - 1, H - 1), "world.steppe")
    floor = Rect(0, 6, W - 1, 9)
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    L.level(Rect(0, 1, 8, 9), -2)      # the widening at the west mouth
    L.level(Rect(9, 6, 12, 9), -2)
    L.level(Rect(13, 6, W - 1, 9), 0)
    north = Rect(0, 0, W - 1, 5) - Rect(0, 1, 8, 5)
    south = Rect(0, 10, W - 1, H - 1)
    for cl in (north, south):
        WP.raise_levels(L, cl, top=9, base=6, face="world.rock", steps=1)
        L.paint(cl, "world.rock")
        L.impassable(cl)
    L.paint(Rect(0, 0, W - 1, 0) | Rect(0, H - 1, W - 1, H - 1), "world.snow")
    L.district("cliffs", north | south)
    L.district("road", floor | Rect(0, 1, 8, 5))

    road = WP.portal_street(L, "gates_w", [(8, 7)], width=2, paving=ROYAL, level=-2)
    WP.portal_street(L, "gates_e", [(W - 1, 7), (8, 7)], width=2, paving=ROYAL)
    L.level(Rect(0, 7, 8, 8), -2)
    for r in (7, 8):
        L.stair("world.ramp", rect=(4, r, 7, r), face="west")
        L.stair("world.ramp", rect=(9, r, 12, r), face="west")
    L.level(Rect(0, 6, 3, 9), -2)
    L.level(Rect(4, 6, 8, 9), -2)
    L.level(Rect(8, 6, 8, 9), -1)
    L.level(Rect(9, 6, 12, 9), -1)
    L.level(Rect(13, 6, W - 1, 9), 0)
    L.place("parsa.gates_station", rect=(0, 1, 7, 6), name="gates_station")
    put(L, "world.watchtower", (11, 4), face="south")
    put(L, "world.beacon", (14, 2))
    for at in ((10, 11), (13, 12), (5, 13)):
        put(L, "world.t_oak_zagros", at)
    put(L, "parsa.p_trough", (5, 9))
    L.node("gates_guardpost", (2, 7))
    WP.finish(L, "world.rock")
    L.view("whole", Rect(0, 0, W - 1, H - 1))
