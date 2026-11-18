"""Landforms after the first visual sweep: the base's relief steps (benches, cleaned outlines,
rivers in reaches) and the rules that keep them (V14 relief, V15 sightlines)."""

import unittest

import numpy as np

from tests.helpers import ROOT, catalog, check, codes, ground_layout, layout
from worldgen import compiler, compose
from worldgen.validate import Target, validate
from worldgen import base
from worldgen.dsl import Layout
from worldgen.shapes import Rect


def base_layout() -> Layout:
    """A procedural-base stand-in: V14 judges only the layer named 'base'."""
    L = Layout(layer="base", region="corner", set="home", origin=(10, 10), size=(32, 24),
               base_level=2, catalog=catalog(), regions=["corner"], source="test")
    L.fill("grass", district="meadows")
    return L


def v14(L) -> list[str]:
    under = ground_layout()
    upl, _ = compiler.compile_layer(under)
    pl, issues = compiler.compile_layer(L)
    g, gissues = compiler.derive_graph(L)
    world = compose.compose([("under", upl), ("base", pl)])
    tg = Target("base", L.regions, pl, g, L, issues + gissues)
    out = validate(world, catalog(), ROOT, tg, {"base": g}, {"base"})
    return [i.message for i in out if i.code == "V14" and i.level == "error"]


class Relief(unittest.TestCase):
    def test_broad_benches_pass(self):
        L = base_layout()
        L.level(Rect(0, 0, 31, 9), 2)
        L.level(Rect(0, 10, 31, 23), 0)
        self.assertEqual(v14(L), [])

    def test_isolated_single_tile_step_is_an_error(self):
        L = base_layout()
        L.level(Rect(15, 12, 15, 12), 1)
        self.assertTrue(any("isolated" in m for m in v14(L)))

    def test_staircase_slope_is_an_error(self):
        L = base_layout()
        for k in range(12):                      # a step every tile: rice terraces
            L.level(Rect(0, 2 + k, 31, 2 + k), min(k, 9))
        L.level(Rect(0, 14, 31, 23), 9)
        self.assertTrue(any("one-tile benches" in m for m in v14(L)))

    def test_staircase_river_is_an_error_and_a_waterfall_is_not(self):
        L = base_layout()
        L.level(Rect(0, 0, 31, 23), 6)
        river = Rect(2, 11, 29, 12)
        L.paint(river, "world.river")
        for k, c in enumerate(range(2, 30, 2)):  # a one-level fall every two tiles
            L.level(Rect(c, 11, 31, 12), 6 - min(k, 5))
        self.assertTrue(any("staircase river" in m for m in v14(L)))
        L2 = base_layout()
        L2.level(Rect(0, 0, 31, 23), 6)
        L2.paint(river, "world.river")
        L2.level(Rect(16, 0, 31, 23), 2)         # one fall of four levels
        self.assertEqual([m for m in v14(L2) if "river" in m], [])


class Sightline(unittest.TestCase):
    def _town(self):
        L = layout()
        L.fill("grass", district="village")
        L.street([(0, 12), (31, 12)], width=1, paving="path")
        L.node("west", (0, 12))
        L.node("east", (31, 12))
        L.sightline("approach", Rect(0, 0, 15, 10))
        return L

    def test_world_kit_in_a_sightline_is_an_error(self):
        L = self._town()
        L.place("world.boulder", at=(5, 5))
        self.assertIn("V15", codes(check(L)))

    def test_own_set_pieces_pass_and_outside_is_free(self):
        L = self._town()
        L.place("oak", at=(5, 5))
        L.place("world.boulder", at=(25, 5))     # outside the marked approach
        self.assertNotIn("V15", codes(check(L)))


class Generator(unittest.TestCase):
    def test_clean_removes_islands_and_keeps_fixed_tiles(self):
        land = np.ones((30, 30), dtype=bool)
        lv = np.full((30, 30), 2, dtype=np.int16)
        lv[10, 10] = 5                           # a one-tile spur
        lv[20:26, 4:26] = 4                      # a broad bench
        lv[3, 25] = 7
        fixed = np.zeros_like(land)
        fixed[3, 25] = True
        base.clean(lv, land, fixed)
        self.assertEqual(lv[10, 10], 2)
        self.assertEqual(lv[22, 15], 4)
        self.assertEqual(lv[3, 25], 7)

    def test_unpimple(self):
        lv = np.full((5, 5), 3, dtype=np.int16)
        lv[2, 2] = 1
        base.unpimple(lv, np.ones((5, 5), dtype=bool))
        self.assertEqual(lv[2, 2], 3)

    def test_benches_gather_steps(self):
        # A slope of one level every four tiles: plain rounding steps every four tiles; benches
        # gather the steps in pairs with broad treads between them.
        h = 1 + np.clip(base.CC - 100, 0, 32) / 4.0
        land = np.ones(h.shape, dtype=bool)
        row = base.terraced(h, land, np.ones(h.shape))[100, 100:133]
        runs = np.diff(np.flatnonzero(np.diff(np.r_[-1, row, -1])))
        self.assertEqual(int(row[-1] - row[0]), 8)
        self.assertGreaterEqual(int(runs.max()), 6)

if __name__ == "__main__":
    unittest.main()
