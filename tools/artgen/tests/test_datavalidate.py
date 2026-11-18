"""The draw-order rules of the art data (draw-order.md §5.1), each held to a failing fixture from
the audit (out/reports/draw-order-audit.md) and to a passing case.

    tools/artgen/.venv/bin/python tools/artgen/tests/test_datavalidate.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datavalidate import order_rules  # noqa: E402

LEVEL = 16
FLAT3 = [[0, 0, 0]] * 3


def rules(iid, item, entry, keys=()):
    return order_rules(iid, item, entry, set(keys), LEVEL)


def codes(errors):
    return {e.split(": ")[1].split()[0] for e in errors}


class OrderRules(unittest.TestCase):
    def test_p1_walk_tiles_without_pieces(self):
        station = {"footprint": [3, 4], "layout": "rotate"}       # world.royal_station before A1
        self.assertIn("P1", codes(rules("world.royal_station", station,
                                        {"r0": {"h": 60, "walk": [[0, 3], [1, 3], [2, 3]],
                                                "tops": [[0, 0, 0]] * 4}})))
        fold = {"footprint": [3, 3], "layout": "rotate"}          # world.sheepfold
        self.assertIn("P1", codes(rules("world.sheepfold", fold, {"r0": {"h": 50, "walk": [[1, 1], [1, 2]],
                                                                          "tops": FLAT3}})))
        arcade = {"footprint": [1, 1], "layout": "connect"}       # rome.aqua_claudia m0
        self.assertIn("P1", codes(rules("rome.aqua_claudia", arcade, {"m0": {"h": 160, "walk": [[0, 0]],
                                                                             "tops": [[0]]}})))

    def test_p1_run_and_p2_art(self):
        fold = {"footprint": [3, 3], "layout": "rotate"}
        good = {"r0": {"h": 50, "walk": [[1, 1], [1, 2]], "pieces": [[1, 1, 1, 2], [0, 0, 3, 1], [0, 1, 1, 2],
                                                                     [2, 1, 1, 2]],
                       "tops": FLAT3, "under": [0, 0, 0, 0]}}
        keys = [f"item/world.sheepfold/base/r0/p{i}/f0" for i in range(4)]
        self.assertEqual(rules("world.sheepfold", fold, good, keys), [])
        self.assertIn("P2", codes(rules("world.sheepfold", fold, good, keys[:3])))
        mixed = {"r0": dict(good["r0"], pieces=[[0, 0, 3, 3]], under=[0])}
        self.assertIn("P1", codes(rules("world.sheepfold", fold, mixed, keys[:1])))

    def test_p3_tops(self):
        item = {"footprint": [2, 1], "layout": "rotate"}
        self.assertIn("P3", codes(rules("x.box", item, {"r0": {"h": 20}})))
        self.assertIn("P3", codes(rules("x.box", item, {"r1": {"h": 20, "tops": [[4, 4]]}})))   # turned: 1 x 2
        self.assertEqual(rules("x.box", item, {"r1": {"h": 20, "tops": [[4], [4]]}}), [])

    def test_w2_closed_courtyard(self):
        item = {"footprint": [3, 3], "layout": "rotate"}
        court = {"r0": {"h": 40, "walk": [[1, 1]], "pieces": [[1, 1, 1, 1], [0, 0, 3, 1], [0, 1, 1, 2],
                                                              [2, 1, 1, 2], [1, 2, 1, 1]],
                        "tops": FLAT3, "under": [0] * 5}}
        keys = [f"item/x.court/base/r0/p{i}/f0" for i in range(5)]
        self.assertIn("W2", codes(rules("x.court", item, court, keys)))

    def test_w3_step_between_walk_floors(self):
        item = {"footprint": [1, 2], "layout": "rotate"}         # the Pnyx's bema before the fix
        bema = {"r0": {"h": 30, "walk": [[0, 0], [0, 1]], "walk_z": {"0,0": 3, "0,1": 15},
                       "pieces": [[0, 0, 1, 1], [0, 1, 1, 1]], "tops": [[3], [15]], "under": [0, 0]}}
        keys = [f"item/athens.pnyx/base/r0/p{i}/f0" for i in range(2)]
        self.assertIn("W3", codes(rules("athens.pnyx", item, bema, keys)))
        bema["r0"]["walk_z"]["0,1"] = 11
        self.assertNotIn("W3", codes(rules("athens.pnyx", item, bema, keys)))

    def test_s1_climb_across_axis(self):
        relief = {"footprint": [1, 2], "layout": "rotate", "rise": 1, "axis": "x"}   # parsa.stair_relief
        self.assertIn("S1", codes(rules("parsa.stair_relief", relief, {"r0": {"h": 34, "climb": "-y",
                                                                               "tops": [[16], [8]]}})))
        relief["axis"] = "y"
        self.assertEqual(rules("parsa.stair_relief", relief, {"r0": {"h": 34, "climb": "-y", "tops": [[16], [8]]}}),
                         [])

    def test_o1_clearance_per_piece(self):
        bridge = {"footprint": [1, 2], "layout": "rotate"}       # a deck split without clearances
        deck = {"r0": {"h": 40, "walk": [[0, 0], [0, 1]], "pieces": [[0, 0, 1, 2]], "tops": [[20], [20]]}}
        self.assertIn("O1", codes(rules("rome.pons_fabricius", bridge, deck, ["item/rome.pons_fabricius/base/r0/p0/f0"])))


if __name__ == "__main__":
    unittest.main()
