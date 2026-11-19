"""V16, crossings: a bridge's, ford's or stair's two landings are walkable ground at the height
of its deck ends and joined to the path graph (added after the owner found bridges at the Tiber
island that met neither bank)."""

import unittest

from tests.helpers import catalog, check, layout
from worldgen.shapes import Rect


def meadow():
    L = layout()
    L.fill("grass", district="meadows")
    return L


def v16(issues, level="error"):
    return [i.message for i in issues if i.code == "V16" and i.level == level]


class LandmarkBridge(unittest.TestCase):
    """The Pons Fabricius' art stands its deck 20-24 px above the water it is set on."""

    def setUp(self):
        self.d = catalog().items["rome.pons_fabricius"]
        self.on = self.d.on
        self.d.on = "water"

    def tearDown(self):
        self.d.on = self.on

    def bridge(self, sunk: int):
        L = meadow()
        L.paint(Rect(14, 0, 17, 23), "water")
        L.level(Rect(14, 0, 17, 23), -sunk)
        L.street([(0, 12), (13, 12)], width=1, paving="path")
        L.street([(13, 12), (18, 12)], width=1, paving=None)
        L.street([(18, 12), (31, 12)], width=1, paving="path")
        L.node("west", (0, 12))
        L.node("east", (31, 12))
        L.place("rome.pons_fabricius", at=(14, 11))
        return L

    def test_banks_a_level_above_the_water_meet_the_deck(self):
        self.assertEqual(v16(check(self.bridge(sunk=1))), [])

    def test_banks_at_the_waters_level_leave_the_deck_hanging(self):
        bad = v16(check(self.bridge(sunk=0)))
        self.assertEqual(len([m for m in bad if "not joined" in m]), 2, bad)


class KitBridge(unittest.TestCase):
    """World kit decks stand at their walk height over the water and ramp to the bank."""

    def bridge(self, sunk: int, wide: bool = False, east: bool = True):
        L = meadow()
        L.paint(Rect(14, 0, 16, 23), "world.river")
        L.level(Rect(14, 0, 16, 23), -sunk)
        L.street([(0, 12), (13, 12)], width=1, paving="path")
        if east:
            L.street([(13, 12), (17, 12)], width=1, paving=None)
            L.street([(17, 12), (31, 12)], width=1, paving="path")
        else:
            L.street([(13, 12), (16, 12)], width=1, paving=None)   # ends on the planks
        for c in range(14, 17):
            for r in ((12, 13) if wide else (12,)):
                L.place("world.bridge_timber", at=(c, r))
        L.node("west", (0, 12))
        return L

    def test_flush_banks_pass(self):
        self.assertEqual(v16(check(self.bridge(sunk=0))), [])

    def test_a_sunk_river_leaves_both_ends_unjoined(self):
        # The timber deck stands 12 px over its water (art §10.1): a level down it still meets
        # the bank within a level, two levels down it hangs 20 px below it.
        self.assertEqual([m for m in v16(check(self.bridge(sunk=1))) if "not joined" in m], [])
        bad = v16(check(self.bridge(sunk=2)))
        self.assertEqual(len([m for m in bad if "not joined" in m]), 2, bad)

    def test_two_wide_draws_a_frame(self):
        self.assertTrue(any("frame" in m for m in v16(check(self.bridge(sunk=0, wide=True)))))

    def test_joined_at_one_end_only(self):
        bad = v16(check(self.bridge(sunk=0, east=False)))
        self.assertTrue(any("one end only" in m or "no graph edge" in m for m in bad), bad)


class Stairs(unittest.TestCase):
    def terrace(self, head_path: bool):
        L = meadow()
        L.level(Rect(0, 0, 31, 9), 1)
        L.street([(5, 23), (5, 14)], width=1, paving="path")
        # Placed as a piece, without the stair's own edge: the paths must reach both ends.
        L.place("world.stair_stone", rect=(5, 12, 5, 13), face="south")
        if head_path:
            L.street([(5, 11), (5, 2)], width=1, paving="path")
        L.level(Rect(5, 10, 5, 11), 1)
        return L

    def test_a_flight_joined_at_foot_and_head_passes(self):
        self.assertEqual(v16(check(self.terrace(head_path=True))), [])

    def test_a_flight_whose_head_no_path_meets_fails(self):
        self.assertTrue(any("no path meets its head" in m
                            for m in v16(check(self.terrace(head_path=False)))))


class EngineWalkRules(unittest.TestCase):
    """V17: the engine enters a stair only at its foot and head, never over its sides."""

    def flight(self, across: bool):
        L = meadow()
        L.level(Rect(0, 0, 31, 9), 1)
        L.street([(5, 23), (5, 14)], width=1, paving="path")
        L.level(Rect(5, 10, 5, 11), 1)
        L.street([(5, 11), (5, 2)], width=1, paving="path")
        L.stair("world.stair_stone", rect=(5, 12, 5, 13), face="south")
        if across:
            L.street([(0, 13), (12, 13)], width=1, paving="path")   # across the flight's side
        return L

    def test_a_path_up_the_flight_passes(self):
        self.assertEqual([i.message for i in check(self.flight(False))
                          if i.code == "V17" and i.level == "error"], [])

    def test_a_street_over_the_flights_side_fails(self):
        self.assertTrue(any("side" in i.message for i in check(self.flight(True))
                            if i.code == "V17" and i.level == "error"))


if __name__ == "__main__":
    unittest.main()


class SideEntry(unittest.TestCase):
    """The Royal Road north of Sidon turned onto its bridge's planks from the side (QA5)."""

    def bridge(self, side: bool):
        L = meadow()
        L.paint(Rect(0, 10, 31, 14), "world.river")
        for r in range(10, 15):
            L.place("world.bridge_timber", at=(16, r))
        if side:
            L.street([(15, 0), (15, 10), (16, 10), (16, 15), (16, 23)], width=1, paving=None)
        else:
            L.street([(16, 0), (16, 23)], width=1, paving=None)
        L.paint(Rect(15, 0, 16, 9) | Rect(16, 15, 16, 23) | Rect(15, 10, 15, 10), "path")
        L.node("north", (16 - side, 0))
        L.node("south", (16, 23))
        return L

    def test_a_span_met_over_its_ends_passes(self):
        self.assertEqual([m for m in v16(check(self.bridge(side=False))) if "side" in m], [])

    def test_a_road_turning_onto_the_planks_fails(self):
        self.assertTrue(any("entered from its side" in m
                            for m in v16(check(self.bridge(side=True)))))


class Piers(unittest.TestCase):
    """Sidon's mole and jetty stood in open water a tile off the strand (QA5)."""

    def pier(self, gap: int, cliff: int = 0):
        L = meadow()
        L.paint(Rect(0, 0, 13, 23), "water")
        L.level(Rect(0, 0, 13, 23), -1)
        L.level(Rect(14, 0, 31, 23), cliff)
        L.street([(20, 0), (20, 23)], width=1, paving="path")
        for c in range(13 - gap - 3, 14 - gap):
            L.place("world.jetty", at=(c, 12))
        L.node("quay", (20, 12))
        return L

    def test_a_jetty_from_the_strand_passes(self):
        self.assertEqual([m for m in v16(check(self.pier(gap=0))) if "land" in m], [])

    def test_a_jetty_in_open_water_fails(self):
        self.assertTrue(any("touches no land" in m for m in v16(check(self.pier(gap=1)))))

    def test_a_jetty_against_a_cliff_fails(self):
        self.assertTrue(any("touches no land" in m
                            for m in v16(check(self.pier(gap=0, cliff=2)))))
