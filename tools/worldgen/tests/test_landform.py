"""The land's form (worldgen.landform): faces with art (V18), borders that follow the land (V19)
and the pass that waves them, map markers on their places (V20), interior floors and paving
(V21), and the grading that makes hillsides slopes. Each check has a passing case and a
deliberate fault reported by name; fixtures are built here, never committed data."""

import unittest

import numpy as np

from plan import world_plan as P
from tests.helpers import ROOT, catalog, check, codes, layout
from worldgen import compiler, compose, landform
from worldgen.compose import World, WItem
from worldgen.coords import COLS, ROWS
from worldgen.layer import AUX_SHIFT
from worldgen.shapes import Rect


def composed(L):
    pl, _ = compiler.compile_layer(L)
    return compose.compose([(L.layer, pl)]), pl


def mine_of(world, pl):
    sl = (slice(pl.r0, pl.r0 + pl.h), slice(pl.c0, pl.c0 + pl.w))
    return sl, world.owner[sl] == 0


class Faces(unittest.TestCase):
    def test_v18_a_face_index_past_the_terrains_faces(self):
        L = layout()
        L.fill("world.steppe", district="meadows")
        L.level(Rect(4, 4, 9, 9), 2)
        L.paint(Rect(4, 4, 9, 9), "world.field")
        world, pl = composed(L)
        sl, mine = mine_of(world, pl)
        self.assertEqual(landform.face_issues(world, catalog(), ROOT, sl, mine), [])
        r, c = pl.r0 + 9, pl.c0 + 6                      # a field's south rim tile
        world.L[r, c] = (world.L[r, c] & 0x0F) | (2 << AUX_SHIFT)
        found = landform.face_issues(world, catalog(), ROOT, sl, mine)
        self.assertTrue(any("pick face 2" in m for m, _ in found))

    def test_the_compiler_gives_a_repainted_tile_its_terrains_first_face(self):
        L = layout()
        L.fill("world.steppe", district="meadows")
        L.level(Rect(4, 4, 9, 9), 2)
        L.AUX[4:10, 4:10] = 2                             # the steppe's coast face ...
        L.paint(Rect(4, 4, 9, 9), "world.field")          # ... kept under a field (one face)
        self.assertNotIn("V18", codes(check(L)))


class Seams(unittest.TestCase):
    def straight(self):
        L = layout()
        L.fill("grass", district="meadows")
        L.paint(Rect(0, 0, 31, 9), "meadow")              # a 32-tile ruler line at row 9|10
        return L

    def test_v19_a_ruler_straight_border(self):
        self.assertIn("V19", codes(check(self.straight())))

    def test_waving_breaks_it_and_moves_only_free_tiles(self):
        L = self.straight()
        L.place("oak", at=(12, 10))
        n = landform.wave_seams(L)
        self.assertGreater(n, 0)
        self.assertNotIn("V19", codes(check(L)))
        self.assertEqual(L.terrains[L.T[10, 12]], "grass")   # the tree's tile kept its ground

    def test_a_stepped_border_moves_its_level_but_never_beside_what_is_built(self):
        L = self.straight()
        L.level(Rect(0, 0, 31, 9), 1)                     # the meadow a level up: a crease
        L.place("oak", at=(20, 11))
        before = L.LV.copy()
        landform.wave_seams(L)
        moved = L.LV != before
        self.assertTrue(moved.any())
        self.assertFalse(moved[10:13, 19:22].any())       # round the tree nothing changed level

    def test_a_road_verge_may_run_straight(self):
        L = layout()
        L.fill("grass", district="meadows")
        L.paint(Rect(0, 10, 31, 10), "path")
        L.paint(Rect(0, 0, 31, 9), "meadow")
        self.assertNotIn("V19", codes(check(L)))


class Markers(unittest.TestCase):
    def world(self, built: bool) -> World:
        w = World(terrains=["rome.grass_spring"], districts=["tibur/town"])
        w.T = np.zeros((ROWS, COLS), dtype=np.uint16)
        w.L = np.full((ROWS, COLS), 2, dtype=np.uint8)
        w.D = np.zeros((ROWS, COLS), dtype=np.uint16)
        w.occ = np.full((ROWS, COLS), -1, dtype=np.int32)
        w.layers = ["tibur"]
        if built:
            c, r = next(at for rid, at, _i in P.MARKERS if rid == "tibur")
            for k, (dc, dr) in enumerate(((0, 1), (-4, -4), (3, -5), (-5, 3), (4, 3))):
                w.items.append(WItem("rome.r_domus", c + dc, r + dr, 4, 5, 0, "tibur"))
        return w

    def test_v20_a_marker_on_an_empty_hillside_and_on_its_town(self):
        found = landform.marker_issues(self.world(False), catalog(), ["tibur"])
        self.assertTrue(found and "opens on 0% built ground" in found[0][0])
        self.assertEqual(landform.marker_issues(self.world(True), catalog(), ["tibur"]), [])


class Floors(unittest.TestCase):
    def test_v21_plaster_outside_a_hall_and_grass_showing_through_paving(self):
        L = layout()
        L.fill("grass", district="meadows")
        L.paint(Rect(4, 4, 4, 4), "parsa.paving_red")     # no hall here
        L.paint(Rect(10, 10, 14, 12), "cobble")
        L.paint(Rect(12, 11, 12, 11), "grass")            # a hole in the paving
        world, pl = composed(L)
        sl, mine = mine_of(world, pl)
        text = " ".join(m for m, _ in landform.floor_issues(world, catalog(), sl, mine))
        self.assertIn("interior floor", text)
        self.assertIn("base ground showing through paving", text)
        self.assertEqual(landform.close_paving_holes(L), 1)
        self.assertEqual(L.terrains[L.T[11, 12]], "cobble")


class Water(unittest.TestCase):
    def test_v22_a_side_step_a_step_into_the_sea_and_a_jutting_stream(self):
        L = layout()
        L.fill("world.steppe", level=1, district="meadows")
        L.paint(Rect(0, 10, 25, 11), "world.river")
        L.AUX[10:12, 0:26] = 0                              # flowing east
        L.level(Rect(0, 0, 12, 23), 2)                      # the west half a level up: the
        #                                                     stream falls square across it
        world, pl = composed(L)
        sl, mine = mine_of(world, pl)
        self.assertEqual(landform.water_issues(world, catalog(), sl, mine), [])
        L.level(Rect(5, 11, 12, 11), 1)                     # the south half drops early: aside
        L.paint(Rect(26, 10, 31, 11), "world.sea")
        L.level(Rect(26, 10, 31, 11), 0)                    # and it steps a level into the sea
        L.level(Rect(0, 12, 4, 23), 0)                      # its bank sinks below it
        world, pl = composed(L)
        sl, mine = mine_of(world, pl)
        text = " ".join(m for m, _ in landform.water_issues(world, catalog(), sl, mine))
        self.assertIn("beside it", text)
        self.assertIn("into the sea", text)
        self.assertIn("juts out", text)


class SlopeArt(unittest.TestCase):
    def test_v23_slope_ground_without_its_shapes(self):
        import json
        import tempfile
        from pathlib import Path
        L = layout()
        L.fill("world.steppe", level=1, district="meadows")
        L.level(Rect(0, 0, 31, 9), 2)
        world, pl = composed(L)
        sl, mine = mine_of(world, pl)
        self.assertEqual(landform.slope_issues(world, catalog(), ROOT, sl, mine), [])
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "assets/sets/world").mkdir(parents=True)
            (Path(tmp) / "assets/sets/world/catalog.json").write_text(
                json.dumps({"art": {"slopes": ["world.steppe"]}}))
            found = landform.slope_issues(world, catalog(), Path(tmp), sl, mine)
        self.assertTrue(found and "has no art" in found[0][0])


class Grading(unittest.TestCase):
    def test_slope_ground_steps_a_level_per_neighbour_rock_and_water_hold(self):
        lv = np.zeros((12, 12), dtype=np.int16)
        lv[:, 6:] = 4                                     # a four-level scarp
        water = np.zeros_like(lv, dtype=bool)
        water[0, :6] = True                               # a stream at its foot, level 0
        eligible = ~water
        eligible[8:, 6:] = False                          # rock keeps its cliff there
        landform.grade(lv, eligible, water)
        ok = eligible[2:8]                                # off the stream's banks
        steps = np.abs(np.diff(lv[2:8], axis=1))[ok[:, 1:] & ok[:, :-1]]
        self.assertLessEqual(int(steps.max()), 1)
        self.assertEqual(lv[11, 5], 0)                    # beside the rock: nothing pulls
        self.assertLessEqual(int(lv[1, :6].max()), 1)     # a level at most over the water
        self.assertTrue((lv >= 0).all() and lv[:, 6:].min() == 4)   # nothing lowered

    def test_lone_spikes_and_pits_go(self):
        lv = np.full((7, 7), 3, dtype=np.int16)
        lv[2, 2], lv[4, 4] = 6, 0
        landform.lone_steps(lv, np.ones_like(lv, dtype=bool))
        self.assertTrue((lv == 3).all())


if __name__ == "__main__":
    unittest.main()
