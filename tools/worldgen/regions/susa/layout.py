"""Susa, spring c. 470 BC (docs/design/sets/world.md §4.3).

World rect C 1080..1103, R 315..340; local (c, r) = world (C - 1080, R - 315); local level 0 =
world level 1. The citadel mound (+4, earth faces, packed earth on top) carries Darius' palace
(c 0..13, r 2..13: the apadana of bull-capital columns beside courts faced with glazed-brick
archers, lions and winged bulls); a stepped way climbs its south flank; the Shaur (the base's
Karun) runs diagonally through c 14..18; the town of mudbrick houses south of the mound and on
the east bank; the Royal Road enters from the west (portal `susa_w`), crosses the Shaur on a
timber bridge and leaves east for the Persian Gates (portal `susa_e`); river boats from the
Gulf land at a quay (lane `susa`).
"""

from worldgen import waypoint as WP
from worldgen import finish as F
from worldgen.dsl import Layout
from worldgen.finish import put
from worldgen.shapes import Line, Rect

ROYAL, EARTH = "world.road_royal", "parsa.packed_earth"
HOUSES = {"parsa.p_house": 2, "parsa.p_house_small": 3}
SHAUR = [(18, 0), (16, 8), (15, 16), (14, 25)]


def build(L: Layout) -> None:
    W, H = L.size
    WP.ground(L, "plain")
    L.paint(Rect(0, 0, W - 1, H - 1), "world.alluvium")
    L.level(Rect(0, 0, W - 1, H - 1), 0)
    mound = Rect(0, 0, 13, 14)
    L.level(mound, 4, face="world.earth")
    L.paint(mound, "parsa.packed_earth")
    L.district("citadel", mound)
    L.district("town", Rect(0, 15, 13, H - 1) | Rect(17, 0, W - 1, H - 1))

    road = WP.portal_street(L, "susa_w", [(20, 16), (20, 10)], width=1, paving=ROYAL)
    WP.portal_street(L, "susa_e", [(20, 10)], width=1, paving=ROYAL)
    town_w = [L.street([(6, 16), (6, 24), (12, 24)], width=1, paving=EARTH),
              L.street([(1, 20), (11, 20)], width=1, paving=EARTH)]
    town_e = [L.street([(21, 12), (21, 22)], width=1, paving=EARTH),
              L.street([(20, 4), (23, 4)], width=1, paving=EARTH)]
    L.street([(20, 10), (20, 4)], width=1, paving=EARTH)
    up = WP.climb(L, [(13, 15), (13, 14), (1, 14)], 0, rise=4, paving=EARTH)
    L.river(SHAUR, width=2, terrain="world.river", banks={"world.t_reeds": 0.3}, seed="shaur")
    L.level(Line(SHAUR, 2), 0)  # flush with its banks, as the kit decks are drawn (the base meets it)
    F.fords(L, [road], item="world.bridge_timber")
    F.fords(L, town_w + town_e)
    L.place("parsa.susa_palace", rect=(0, 2, 13, 13), name="susa_palace")
    L.houses(Rect(0, 17, 13, H - 1), HOUSES, front=town_w, gap=0.15, seed="town_w")
    L.houses(Rect(17, 0, W - 1, H - 1) - Rect(17, 9, W - 1, 11) - Rect(17, 15, W - 1, 17),
             HOUSES, front=town_e,
             gap=0.15, seed="town_e")
    put(L, "parsa.p_well", (8, 19))
    put(L, "parsa.p_well", (22, 18))
    L.scatter(Line(SHAUR, 6) - Line(SHAUR, 2), {"parsa.t_date": 3, "world.t_palm": 2}, 0.35,
              seed="palms")
    WP.harbour_lane(L, "susa", [(15, 20), (14, 24)], port="susa", home="quay")
    L.node("palace_steps", (1, 14))
    L.node("susa_town", (6, 20))
    L.node("susa_quay", (13, 20))
    WP.finish(L, "world.earth", {"parsa.p_house_small": 0, "parsa.p_house": 1})
    L.expect("susa_palace", rect=(0, 2, 13, 13), level=4)
    L.view("whole", Rect(0, 0, W - 1, H - 1))
