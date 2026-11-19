"""Slopes' light, occlusion tops and page grouping (art-round-3): small fixtures with known answers.

    tools/artgen/.venv/bin/python -m unittest discover -s tools/artgen/tests
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import occlusion  # noqa: E402
import slopes  # noqa: E402


class SlopeLight(unittest.TestCase):
    def test_flat_ground_is_unchanged(self):
        self.assertAlmostEqual(float(slopes.ground_light(np.array([0.0, 0.0, 1.0]))), 1.0)

    def test_soft_response_bounds(self):
        """A slope facing away is at most a little darker, one facing the sun a little lighter."""
        away = slopes.ground_light(np.array([0.707, 0.0, 0.707]))
        sunward = slopes.ground_light(np.array([-0.447, 0.0, 0.894]))
        self.assertGreaterEqual(float(away), slopes.GROUND_RANGE[0])
        self.assertLess(float(away), 1.0)
        self.assertGreater(float(sunward), 1.0)

    def test_planes_have_one_normal(self):
        """A straight slope (two neighbouring corners low) is one plane: every pixel the same
        normal, so a hillside of them is one even field with no fan creases."""
        inside, _u, _v, _h, n, _d, _box, _z = slopes.raster("c3", 2, 16)
        ns = n[inside]
        self.assertLess(float(np.abs(ns - ns[0]).max()), 1e-6)

    def test_folds_are_smoothed(self):
        """A corner shape's light varies smoothly: no jump between neighbouring pixels larger
        than a small fraction of the whole range."""
        inside, _u, _v, _h, n, _d, _box, _z = slopes.raster("c1", 2, 16)
        light = slopes.ground_light(n.reshape(-1, 3)).reshape(inside.shape)
        dx = np.abs(np.diff(light, axis=1))[inside[:, 1:] & inside[:, :-1]]
        self.assertLess(float(dx.max()), 0.02)

    def test_materials(self):
        self.assertEqual(slopes.material_of("world.forest_floor"), "forest")
        self.assertEqual(slopes.material_of("athens.rock_limestone"), "rock")
        self.assertEqual(slopes.material_of("parsa.plain_grass"), "grass")
        self.assertEqual(slopes.material_of("rome.packed_earth"), "soil")


class OcclusionColumns(unittest.TestCase):
    def test_arcade_wall_canopy(self):
        solid = np.zeros((3, 1, 60), bool)
        solid[0, 0, 0:2] = True          # an arcade: a floor slab ...
        solid[0, 0, 30:34] = True        # ... and its ceiling 28 px above
        solid[1, 0, 0:40] = True         # a wall, solid from the floor up
        solid[2, 0, 40:50] = True        # a canopy over open ground
        has, top, under = occlusion.columns(solid)
        self.assertEqual(list(has[:, 0]), [True, True, True])
        self.assertEqual(list(top[:, 0]), [34, 40, 50])
        self.assertEqual(list(under[:, 0]), [30, 0, 40])

    def test_small_gap_is_not_room(self):
        solid = np.zeros((1, 1, 30), bool)
        solid[0, 0, 0:10] = True
        solid[0, 0, 14:20] = True        # 4 px of gap: a seam, not a passage
        self.assertEqual(int(occlusion.columns(solid)[2][0, 0]), 0)

    def test_tops_sprite(self):
        solid = np.zeros((8, 8, 20), bool)
        solid[:, :, 0:12] = True
        codes = np.ones((8, 8), np.uint8)
        sp = occlusion.tops(solid, codes, 0, 0)
        self.assertEqual(sp.rgba.shape, (2, 2, 4))
        self.assertEqual((sp.ox, sp.oy), (0, 0))
        self.assertTrue((sp.rgba[..., 0] == 6).all() and (sp.rgba[..., 1] == 0).all() and (sp.rgba[..., 3] == 255).all())


class Pages(unittest.TestCase):
    def test_ground_with_people_no_shadows(self):
        import setbuild

        class Mod:
            LANDMARKS = {}
        keys = ["terrain/athens.dry_grass/v0", "edge/athens.earth_se/v0", "terrain/world.sea/m0/f0",
                "item/athens.p_thyme/base/r0/f0", "item/athens.p_thyme/shadow/r0/f0", "item/athens.g_lamp/glow/r0/f0",
                "fx/athens.fire/f0"]
        groups = setbuild.page_groups(keys, {"items": []}, Mod, "athens")
        first = groups[0][0]
        self.assertIn("terrain/athens.dry_grass/v0", first)
        self.assertIn("edge/athens.earth_se/v0", first)
        self.assertIn("item/athens.p_thyme/base/r0/f0", first)
        self.assertNotIn("item/athens.p_thyme/shadow/r0/f0", [k for g, _a in groups for k in g])
        self.assertEqual(groups[-2], (["item/athens.g_lamp/glow/r0/f0"], True))


if __name__ == "__main__":
    unittest.main()
