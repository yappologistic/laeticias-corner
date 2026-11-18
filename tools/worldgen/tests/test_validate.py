"""Each validator trips on a deliberate error, and a clean fixture passes."""

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import catalog, check, codes, ground_layout, layout
from worldgen.shapes import Rect


def clean():
    """A small valid layer: grass, a street with both ends named, a cottage facing it."""
    L = layout()
    L.fill("grass", district="village")
    s = L.street([(0, 12), (31, 12)], width=1, paving="path")
    L.node("west", (0, 12))
    L.node("east", (31, 12))
    L.place("cottage", at=(10, 10), face="south")  # door at (10..11, 12): on the street
    return L, s


class Clean(unittest.TestCase):
    def test_clean_fixture_has_no_errors(self):
        L, _ = clean()
        issues = check(L)
        self.assertEqual(codes(issues), [], [i.text() for i in issues if i.level == "error"])


class Checks(unittest.TestCase):
    def test_v1_unknown_ids_and_districts(self):
        L, _ = clean()
        L.paint(Rect(0, 0, 2, 2), "no.such_terrain")
        L.place("no.such_item", at=(5, 5))
        L.district("elsewhere/x", Rect(0, 20, 3, 23))
        issues = check(L)
        texts = " ".join(i.message for i in issues if i.code == "V1" and i.level == "error")
        self.assertIn("no.such_terrain", texts)
        self.assertIn("no.such_item", texts)
        self.assertIn("elsewhere/x", texts)

    def test_v1_variant_out_of_range(self):
        L, _ = clean()
        p = L.place("oak", at=(20, 2))
        p.k = catalog().items["oak"].count  # one past the last look, as a stale build left it
        self.assertTrue(any("outside the catalog" in i.message for i in check(L)
                            if i.code == "V1" and i.level == "error"))

    def test_v2_overlap(self):
        L, _ = clean()
        L.place("oak", at=(10, 11))  # inside the cottage
        self.assertIn("V2", codes(check(L)))

    def test_v3_wrong_ground_and_uneven(self):
        L, _ = clean()
        L.paint(Rect(20, 2, 22, 4), "water")
        L.place("oak", at=(21, 3))
        L.level(Rect(25, 2, 25, 2), 1)
        L.place("barn", at=(24, 1))
        issues = [i for i in check(L) if i.code == "V3"]
        self.assertTrue(any("needs land" in i.message for i in issues))
        self.assertTrue(any("not flat" in i.message for i in issues))

    def test_v3_stair_levels(self):
        L, _ = clean()
        L.stair("world.ramp", rect=(20, 20, 23, 20), face="east")  # head must be 1 level up
        self.assertTrue(any("head" in i.message for i in check(L) if i.code == "V3"))

    def test_v4_expected_rect(self):
        L, _ = clean()
        L.place("barn", at=(20, 2), name="big_barn")
        L.expect("big_barn", rect=(21, 2, 22, 4))
        self.assertIn("V4", codes(check(L)))

    def test_v5_street_over_water(self):
        L, s = clean()
        L.paint(Rect(15, 11, 16, 13), "water")
        self.assertIn("V5", codes(check(L)))

    def test_v5_step_without_stair(self):
        L, s = clean()
        L.level(Rect(20, 0, 31, 23), 1)
        self.assertIn("V5", codes(check(L)))

    def test_v6_disconnected(self):
        L, _ = clean()
        L.street([(0, 20), (5, 20)], width=1, paving="path")
        self.assertIn("V6", codes(check(L)))

    def test_v6_undeclared_portal(self):
        L, _ = clean()
        L.street([(31, 12), (31, 23)], width=1, paving="path", portal="nowhere")
        self.assertIn("V6", codes(check(L)))

    def test_v7_door_on_water(self):
        L, _ = clean()
        L.paint(Rect(20, 3, 24, 3), "water")
        L.place("cottage", at=(21, 1), face="south")  # door at y 3: water
        self.assertIn("V7", codes(check(L)))

    def test_v8_bases_touch_and_sea_level(self):
        L, _ = clean()
        L.paint(Rect(25, 15, 31, 23), "rome.grass_spring")  # base next to grass, no overlay
        L.paint(Rect(0, 20, 3, 23), "world.sea")            # sea at land level
        msgs = [i.message for i in check(L) if i.code == "V8"]
        self.assertTrue(any("base terrains touch" in m for m in msgs))
        self.assertTrue(any("sea tiles above level 0" in m for m in msgs))

    def test_v8_river_uphill(self):
        L, _ = clean()
        L.river([(20, 18), (28, 18)], width=1)
        L.level(Rect(25, 18, 28, 18), 1)
        self.assertTrue(any("uphill" in i.message for i in check(L) if i.code == "V8"))

    def test_v9_missing_district(self):
        L = layout()
        L.paint(Rect(0, 0, 31, 23), "grass")  # ground, but no district anywhere
        self.assertIn("V9", codes(check(L)))

    def test_v10_glow_budget(self):
        L, _ = clean()
        for i in range(41):  # world C 32..41 is one grid chunk column
            L.place("lamp", at=(22 + i % 10, 14 + i // 10))
        self.assertIn("V10", codes(check(L)))

    def test_v10_budget_of_a_chunk_elsewhere_is_not_this_layers(self):
        L, _ = clean()
        under = ground_layout(rect=(0, 0, 127, 47))
        for i in range(41):  # world C 100..109: a chunk column the test layer does not touch
            under.place("lamp", at=(100 + i % 10, 14 + i // 10))
        self.assertNotIn("V10", codes(check(L, under)))

    def test_v11_hidden_ground_warns(self):
        L, _ = clean()
        # A ridge 12 levels high in front (south-west) of the street hides it.
        L.level(Rect(0, 13, 31, 23), 12)
        L.level(Rect(0, 0, 31, 11), 0)
        issues = check(L)
        self.assertIn("V11", codes(issues, "warning"))

    def test_v12_card_missing_from_region_file(self):
        L, _ = clean()
        d = catalog().items["cottage"]
        old = d.card
        d.card = "cottage_card"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "assets/regions"
                p.mkdir(parents=True)
                (p / "corner.json").write_text(json.dumps({"version": 1, "cards": {}}))
                self.assertIn("V12", codes(check(L, root=Path(tmp))))
        finally:
            d.card = old


if __name__ == "__main__":
    unittest.main()
