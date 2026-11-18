"""The connective world's core: route profiles and paths, waypoint helpers, and the validator
rules for portals, lanes, sets and rivers between layers."""

import unittest

import numpy as np

from plan import world_plan as P
from tests.helpers import catalog, check, codes, ground_layout, layout
from worldgen import compiler, compose, routes
from worldgen import waypoint as WP
from worldgen.graph import Graph, Lane, Port
from worldgen.validate import Target, validate
from worldgen.shapes import Rect


class Profile(unittest.TestCase):
    def test_levels_change_only_on_ramps_and_meet_fixed_ends(self):
        path = [(c, 0) for c in range(30)]
        lv = np.zeros((1, 40), dtype=np.int16)
        lv[0, 12:] = 3                       # a 3-level step in the ground
        water = np.zeros((1, 40), dtype=bool)
        z, ramps, fails = routes.profile(path, lv, water, 0, 2, set())
        self.assertEqual((z[0], z[-1], fails), (0, 2, 0))
        on_ramp = {i for i0, _ in ramps for i in range(i0 - 1, i0 + routes.RAMP_RUN + 1)}
        for i in range(1, len(z)):
            if z[i] != z[i - 1]:
                self.assertIn(i, on_ramp)    # every change happens at a ramp's head or foot
                self.assertEqual(abs(z[i] - z[i - 1]), 1)

    def test_no_ramp_on_water_or_without_a_straight_run(self):
        path = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (4, 3)]  # all corners
        lv = np.full((8, 8), 2, dtype=np.int16)
        water = np.zeros((8, 8), dtype=bool)
        z, ramps, fails = routes.profile(path, lv, water, 0, 1, set())
        self.assertEqual(ramps, [])
        self.assertEqual(fails, 1)           # reported, not hidden

    def test_astar4_is_axis_parallel_and_avoids_closed_tiles(self):
        cost = np.ones((20, 30))
        cost[:, 10] = np.inf
        cost[15, 10] = 1.0                   # one gap in the wall
        path = routes.astar4(cost, (2, 2), (25, 3), margin=30)
        self.assertEqual(path[0], (2, 2))
        self.assertEqual(path[-1], (25, 3))
        self.assertIn((10, 15), path)
        for a, b in zip(path, path[1:]):
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)


class Waypoint(unittest.TestCase):
    def _town(self):
        under = ground_layout()
        under.level(Rect(0, 0, 63, 47), 1)
        upl, _ = compiler.compile_layer(under)
        L = layout()
        L.below = compose.compose([("base", upl)])
        return L

    def test_ground_copies_the_base(self):
        L = self._town()
        WP.ground(L)
        self.assertTrue((L.LV == 1).all())
        self.assertEqual({L.terrains[t] for t in np.unique(L.T)}, {"grass"})

    def test_climb_puts_a_flight_per_level(self):
        L = self._town()
        WP.ground(L)
        top = WP.climb(L, [(2, 5), (14, 5)], 1, rise=3, paving="path")
        self.assertEqual(top, 4)
        flights = [p for p in L.items if p.id == "world.stair_stone"]
        self.assertEqual(len(flights), 3)
        self.assertNotIn("V3", codes(check(L)))


class WorldRules(unittest.TestCase):
    def test_portal_level_must_match_the_plan(self):
        P.PORTALS["test_gate"] = (("corner", "base"), (10, 20), 9)
        try:
            L = layout()
            L.fill("grass", district="village")
            L.street([(0, 10), (10, 10)], width=1, paving="path", portal="test_gate")
            msgs = [i.message for i in check(L) if i.code == "V6" and i.level == "error"]
            self.assertTrue(any("level" in m and "test_gate" in m for m in msgs), msgs)
        finally:
            del P.PORTALS["test_gate"]

    def test_lane_ports_of_one_place_meet(self):
        L = layout()
        L.fill("grass", district="village")
        L.street([(0, 5), (8, 5)], width=1, paving="path")
        L.lane("harbour", [(2, 2), (30, 2)], kind="sea", ports={"piraeus": 1})
        upl, _ = compiler.compile_layer(ground_layout())
        pl, issues = compiler.compile_layer(L)
        g, gi = compiler.derive_graph(L)
        other = Graph("athens", lanes=[Lane("kantharos", "sea", [(300, 600), (310, 600)],
                                            [Port("piraeus", 1)])])
        world = compose.compose([("base", upl), (L.layer, pl)])
        tg = Target(L.layer, L.regions, pl, g, L, L.issues + issues + gi)
        out = validate(world, catalog(), catalog().root, tg, {L.layer: g, "athens": other},
                       {L.layer})
        self.assertTrue(any("does not meet" in i.message for i in out if i.code == "V6"))

    def test_region_set_rule(self):
        L = layout()
        L.fill("grass", district="village")
        L.place("parsa.p_well", at=(5, 5))       # a Persian well in the corner's region
        self.assertTrue(any("region-set" in i.message for i in check(L) if i.code == "V1"))


if __name__ == "__main__":
    unittest.main()
