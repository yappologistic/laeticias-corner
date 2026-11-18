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
    """World kit decks ramp down to their own tile: banks flush with the water."""

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
        bad = v16(check(self.bridge(sunk=1)))
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


if __name__ == "__main__":
    unittest.main()
