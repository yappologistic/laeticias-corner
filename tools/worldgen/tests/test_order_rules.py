"""Where walkers may be (docs/design/draw-order.md §5.2, `worldgen/walkable.py`): every rule
rejects a fixture shaped like a real offender of out/reports/draw-order-audit.md part 1 and lets
the corrected shape pass."""

import unittest

import numpy as np

from tests.helpers import catalog, check, ground_layout, layout
from worldgen import compiler, compose, walkable
from worldgen.graph import Graph, Lane
from worldgen.layer import grid_to_plan
from worldgen.shapes import Rect
from worldgen.walk import EngineWalk


def meadow():
    L = layout()
    L.fill("grass", district="meadows")
    return L


def found(issues, code, level="error"):
    return [i.message for i in issues if i.code == code and i.level == level]


def world_of(L):
    """The composed fixture world and its graphs, for the scanner and the report."""
    upl, _ = compiler.compile_layer(ground_layout())
    pl, _ = compiler.compile_layer(L)
    g, _ = compiler.derive_graph(L)
    return compose.compose([("base", upl), (L.layer, pl)]), {L.layer: g}, pl


class SealedWalkArea(unittest.TestCase):
    """W-W5 and W-L2: the Baths of Trajan's south run ended at an insula two levels down, so 63
    walk tiles and three slots were an island; relay stations sat in pits beside a ramp's side."""

    def station(self, pit: bool):
        L = meadow()
        L.street([(0, 20), (31, 20)], width=1, paving="path")
        L.node("road", (0, 20))
        if pit:
            L.level(Rect(0, 0, 31, 18), 2)
            L.level(Rect(9, 5, 16, 12), 0)
        L.place("world.royal_station", rect=(10, 6, 13, 9), face="west")
        return L

    def test_a_station_on_the_roads_ground_passes(self):
        issues = check(self.station(pit=False))
        self.assertEqual(found(issues, "W-W5") + found(issues, "W-L2"), [])

    def test_a_station_in_a_pit_is_an_island(self):
        issues = check(self.station(pit=True))
        self.assertTrue(found(issues, "W-W5"), issues)
        self.assertTrue(any("royal_station.door" in m for m in found(issues, "W-L2")))


class SpotUnderAnotherItem(unittest.TestCase):
    """W-L1: the Curia's senator spot under the Lapis Niger; a fold's gate under a peak."""

    def fold(self, blocked: bool):
        L = meadow()
        L.street([(0, 20), (31, 20)], width=1, paving="path")
        L.node("road", (0, 20))
        p = L.place("world.sheepfold", at=(12, 8), face="west")
        if blocked:
            c, r, _f = p.slots["gate"][0]
            L.place("world.boulder", at=(c - L.origin[0], r - L.origin[1]))
        return L

    def test_a_free_gate_passes(self):
        self.assertEqual(found(check(self.fold(False)), "W-L1"), [])

    def test_a_gate_under_a_boulder_is_a_collision(self):
        self.assertTrue(any("world.boulder" in m and "collision" in m
                            for m in found(check(self.fold(True)), "W-L1")))


class SpotInsideItsOwnKit(unittest.TestCase):
    """W-L1 (art): rome.mutatio's change spots inside its footprint; known to the art lane, so a
    named warning (plan/art_pending.py) until its geometry changes."""

    def test_is_reported_as_art_pending(self):
        L = meadow()
        L.street([(0, 20), (31, 20)], width=1, paving="path")
        L.node("road", (0, 20))
        L.place("rome.mutatio", at=(10, 14), face="south")
        issues = check(L)
        self.assertEqual([m for m in found(issues, "W-L1") if "mutatio" in m], [])
        self.assertTrue(any("[art:" in m and "mutatio.change" in m
                            for m in found(issues, "W-L1", "warning")))


class ReedsOnWater(unittest.TestCase):
    """W-D2: world.t_reeds is walkable kit; standing on water it became a deck walkers could
    take into the river (susiana, mesopotamia, euphrates_crossing)."""

    def test_the_layout_never_puts_walkable_reeds_on_water(self):
        L = meadow()
        L.paint(Rect(0, 0, 5, 23), "world.river")
        self.assertIsNone(L.place("world.t_reeds", at=(3, 3)))
        self.assertIsNotNone(L.place("world.t_reeds", at=(7, 3)))
        L.paint(Rect(6, 0, 7, 23), "world.river")       # a river laid over the bank later
        self.assertTrue(all(p.removed for p in L.items if p.id == "world.t_reeds"))

    def test_reeds_on_water_are_refused(self):
        L = meadow()
        L.paint(Rect(0, 0, 5, 23), "world.river")
        L.place("world.t_reeds", at=(7, 3))
        world, graphs, _pl = world_of(L)
        river = world.terrains.index("world.river")
        c, r = next((p.c, p.r) for p in L.items if p.id == "world.t_reeds")
        world.T[r, c] = river                         # the committed file's shape
        msgs = [f.msg for f in walkable.scan(world, catalog(), graphs) if f.code == "W-D2"]
        self.assertTrue(any("t_reeds" in m for m in msgs), msgs)


class Decks(unittest.TestCase):
    """W-D1: the base's mole at grid (289, 302) met a quay 48 px above its planks, on a strand
    no road reaches."""

    def jetty(self, cliff_beside: bool, road: bool = True):
        L = meadow()
        L.paint(Rect(0, 0, 13, 23), "water")
        L.level(Rect(0, 0, 13, 23), -1)
        if road:
            L.street([(20, 0), (20, 23)], width=1, paving="path")
            L.node("quay", (20, 12))
        for c in range(10, 14):
            L.place("world.jetty", at=(c, 12))
        if cliff_beside:
            L.paint(Rect(10, 11, 10, 11), "grass")
            L.level(Rect(10, 11, 10, 11), 2)
        return L

    def test_a_jetty_from_the_strand_passes(self):
        self.assertEqual(found(check(self.jetty(False)), "W-D1"), [])

    def test_land_far_above_the_planks_is_refused(self):
        self.assertTrue(any("refuse" in m for m in found(check(self.jetty(True)), "W-D1")))

    def test_a_jetty_no_graph_reaches(self):
        self.assertTrue(any("no graph reaches" in m
                            for m in found(check(self.jetty(False, road=False)), "W-D1")))


class StairEnds(unittest.TestCase):
    """W-S3: the Hadish's west stair (rise 3) met level 10 at its head where 13 was wanted."""

    def flight(self, terrace: int):
        L = meadow()
        L.level(Rect(0, 0, 31, 9), terrace)
        L.level(Rect(5, 10, 5, 11), terrace)
        L.street([(5, 23), (5, 14)], width=1, paving="path")
        L.street([(5, 11), (5, 2)], width=1, paving="path")
        L.place("world.stair_stone", rect=(5, 12, 5, 13), face="south")
        L.node("low", (5, 23))
        L.node("high", (5, 2))
        return L

    def test_a_terrace_one_level_up_passes(self):
        self.assertEqual(found(check(self.flight(1)), "W-S3"), [])

    def test_a_head_on_the_feet_level_fails(self):
        self.assertTrue(found(check(self.flight(0)), "W-S3"))


class FootprintLevels(unittest.TestCase):
    """W-V3: parsa.harem stood on levels 10 and 11 (its walk tiles a level below its platform),
    which V3 allowed for a landmark's walk tiles."""

    def gate(self, step: bool):
        L = meadow()
        L.street([(0, 20), (31, 20)], width=1, paving="path")
        L.node("road", (0, 20))
        p = L.place("rome.porta_capena", at=(10, 10))
        if step:
            c, r = sorted(L.walk_tiles(p))[0]
            L.level(Rect(c - L.origin[0], r - L.origin[1], c - L.origin[0], r - L.origin[1]), 1)
        return L

    def test_one_level_passes(self):
        self.assertEqual(found(check(self.gate(False)), "W-V3"), [])

    def test_a_walk_tile_a_level_off_fails(self):
        self.assertTrue(found(check(self.gate(True)), "W-V3"))


class Graphs(unittest.TestCase):
    """W-G1 and W-G2: no edge between two walk components, none through a building."""

    def ways(self, through_house: bool, over_cliff: bool):
        L = meadow()
        if over_cliff:
            L.level(Rect(16, 0, 31, 23), 2)
        L.paint(Rect(0, 12, 31, 12), "path")
        L.node("w", (0, 12))
        L.node("e", (31, 12))
        # An explicit edge, as a layout joins named places over ground it leaves to another.
        L.edge("w", "e", kind="track")
        if through_house:
            L.place("barn", at=(13, 3))
            L.node("n", (14, 1))
            L.edge("n", "w", kind="track", via=[(14, 12)])
        return L

    def test_a_walkable_way_passes(self):
        issues = check(self.ways(False, False))
        self.assertEqual(found(issues, "W-G1") + found(issues, "W-G2"), [])

    def test_an_edge_through_a_house_names_it(self):
        self.assertTrue(any("barn" in m
                            for m in found(check(self.ways(True, False)), "W-G2")))

    def test_an_edge_over_a_cliff_joins_two_components(self):
        self.assertTrue(found(check(self.ways(False, True)), "W-G1"))


class WaterRoutes(unittest.TestCase):
    """No walker route across water without a crossing (V5 and V17)."""

    def ford(self, deck: bool):
        L = meadow()
        L.paint(Rect(14, 0, 16, 23), "world.river")
        L.street([(0, 12), (31, 12)], width=1, paving=None)
        L.paint(Rect(0, 12, 13, 12) | Rect(17, 12, 31, 12), "path")
        if deck:
            for c in range(14, 17):
                L.place("world.bridge_timber", at=(c, 12))
        L.node("w", (0, 12))
        L.node("e", (31, 12))
        return L

    def test_over_a_bridge_passes(self):
        self.assertEqual(found(check(self.ford(True)), "V17"), [])

    def test_through_the_river_fails(self):
        self.assertTrue(found(check(self.ford(False)), "V17"))


class Lanes(unittest.TestCase):
    """W-O2: aegean_delos crossed Delos' land; kenchreai ran over its jetty's planks; the Tiber's
    barges went under the Pons Fabricius, whose geometry declares no clearance."""

    def harbour(self, points, deck: str | None = None):
        L = meadow()
        L.paint(Rect(0, 0, 13, 23), "water")
        L.level(Rect(0, 0, 13, 23), -1)
        L.street([(20, 0), (20, 23)], width=1, paving="path")
        L.node("quay", (20, 12))
        if deck == "jetty":
            for c in range(10, 14):
                L.place("world.jetty", at=(c, 12))
        elif deck == "bridge":
            for r in range(0, 24):
                L.place("bridge", at=(6, r)) if r != 12 else None
        L.lane("boats", points, kind="sea", ports={"start": 0, "end": len(points) - 1})
        return L

    def test_open_water_passes(self):
        self.assertEqual(found(check(self.harbour([(9, 13), (2, 20)])), "W-O2"), [])

    def test_over_land_fails(self):
        self.assertTrue(any("not water" in m
                            for m in found(check(self.harbour([(9, 13), (18, 13)])), "W-O2")))

    def test_over_a_jetty_fails(self):
        self.assertTrue(any("world.jetty" in m for m in found(
            check(self.harbour([(12, 12), (2, 12)], deck="jetty")), "W-O2")))

    def test_beside_the_jetty_head_passes(self):
        self.assertEqual(found(check(self.harbour([(9, 13), (2, 13)], deck="jetty")), "W-O2"),
                         [])

    def test_under_a_bridge_without_clearance_fails(self):
        self.assertTrue(any("clearance" in m for m in found(
            check(self.harbour([(9, 5), (2, 5)], deck="bridge")), "W-O2")))

    def test_a_grazed_corner_is_not_a_crossing(self):
        self.assertEqual(walkable.lane_tiles([(0, 0), (3, 3)]),
                         [(0, 0), (1, 1), (2, 2), (3, 3)])


class EngineModel(unittest.TestCase):
    """The components use exactly the engine's steps (walk.EngineWalk.step)."""

    def test_vectorised_steps_match_the_engine(self):
        L = meadow()
        L.level(Rect(0, 0, 31, 9), 1)
        L.level(Rect(5, 10, 5, 11), 1)
        L.street([(5, 23), (5, 14)], width=1, paving="path")
        L.stair("world.stair_stone", rect=(5, 12, 5, 13), face="south")
        L.paint(Rect(20, 0, 22, 23), "world.river")
        for c in range(20, 23):
            L.place("world.bridge_timber", at=(c, 16))
        L.place("rome.porta_capena", at=(10, 14))
        world, graphs, pl = world_of(L)
        wk = walkable.Walkable(world, catalog(), graphs)
        ew = EngineWalk(world, catalog())
        for r in range(pl.r0, pl.r0 + pl.h):
            for c in range(pl.c0, pl.c0 + pl.w - 1):
                for b in ((c + 1, r), (c, r + 1)):
                    if b[1] >= pl.r0 + pl.h:
                        continue
                    self.assertEqual(wk.can_step((c, r), b), ew.step((c, r), b) is None,
                                     ((c, r), b))


class ArtList(unittest.TestCase):
    def test_an_entry_no_fault_matches_is_stale(self):
        f = walkable.Finding("W-L1", "base", "m", (0, 0), item="rome.mutatio", slot="change")
        stale = walkable.stale_art([f])
        self.assertNotIn(("W-L1", "rome.mutatio", "change"), stale)
        self.assertIn(("W-O2", "rome.pons_fabricius", ""), stale)


class Report(unittest.TestCase):
    def test_a_connected_fixture_has_no_unreached_walk_tiles(self):
        L = SealedWalkArea().station(pit=False)
        world, graphs, _pl = world_of(L)
        st = walkable.stats(world, catalog(), graphs)
        s = st["regions"]["corner"]
        self.assertGreater(s.item_walk, 0)
        self.assertEqual(s.item_unreached, 0)
        self.assertIn("| corner |", walkable.report_md(st))


if __name__ == "__main__":
    unittest.main()
