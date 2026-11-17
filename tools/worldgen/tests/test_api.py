"""Shapes, rasterisation, streams, the layout API, the bible parser."""

import unittest

import numpy as np

from tests.helpers import ROOT, layout
from worldgen import bible, raster, rng
from worldgen.coords import to_grid, to_plan
from worldgen.shapes import Ellipse, Line, Poly, Rect


class Raster(unittest.TestCase):
    def test_rect_inclusive(self):
        m = Rect(1, 2, 3, 2).mask(0, 0, 5, 4)
        self.assertEqual(int(m.sum()), 3)
        self.assertTrue(m[2, 1] and m[2, 3] and not m[2, 4])

    def test_poly_through_centres_includes_its_edges(self):
        m = Poly([(0, 0), (4, 0), (4, 2), (0, 2)]).mask(0, 0, 6, 4)
        self.assertEqual(int(m.sum()), 15)

    def test_line_widths_are_exact_on_straight_runs(self):
        for width, rows in ((1, [5]), (2, [5, 6]), (3, [4, 5, 6]), (4, [4, 5, 6, 7])):
            m = Line([(2, 5), (12, 5)], width).mask(0, 0, 16, 12)
            self.assertEqual(sorted(set(np.nonzero(m)[0].tolist())), rows, width)

    def test_diagonal_line_is_4_connected(self):
        path = raster.path_tiles([(0, 0), (7, 5)])
        for a, b in zip(path, path[1:]):
            self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
        m = Line([(0, 0), (7, 5)], 1).mask(0, 0, 8, 6)
        self.assertTrue(all(m[r, c] for c, r in path))

    def test_shape_algebra(self):
        s = (Rect(0, 0, 9, 9) - Ellipse(5, 5, 2, 2)) & Rect(0, 0, 4, 9)
        self.assertEqual(s.bounds(), (0, 0, 9, 9))
        m = s.mask(0, 0, 10, 10)
        self.assertFalse(m[5, 5] or m[0, 6])
        self.assertTrue(m[0, 0])


class Streams(unittest.TestCase):
    def test_streams_depend_only_on_their_key(self):
        s1, s2 = rng.stream("x", 1), rng.stream("x", 1)
        self.assertEqual([s1.next64() for _ in range(5)], [s2.next64() for _ in range(5)])
        self.assertNotEqual(rng.stream("x", 1).next64(), rng.stream("x", 2).next64())

    def test_splitmix_reference_value(self):
        # SplitMix64 seeded with 0 starts with this value in every implementation.
        self.assertEqual(f"{rng.Stream(0).next64():016x}", "e220a8397b1dcdaf")

    def test_noise_is_a_function_of_position(self):
        c, r = rng.grid_coords(100, 50, 20, 10)
        a = rng.fbm(c, r, 12.0, 7)
        b = rng.fbm(c[3:, 5:], r[3:, 5:], 12.0, 7)
        self.assertTrue(np.allclose(a[3:, 5:], b))
        self.assertTrue((a >= 0).all() and (a <= 1).all())


class Coordinates(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(to_grid(1196, 358), (358, 83))
        self.assertEqual(to_plan(358, 83), (1196, 358))
        # world-tech §1.13: the Apadāna's origin tile (NE corner) is grid (358, 60).
        self.assertEqual(to_grid(1219, 358), (358, 60))


class LayoutAPI(unittest.TestCase):
    def test_place_converts_and_checks_the_footprint(self):
        L = layout()
        L.fill("grass", district="m")
        p = L.place("barn", at=(2, 2), face="west")  # barn [3, 2]: plan 2 wide, 3 tall
        self.assertEqual((p.c, p.r, p.pw, p.ph), (12, 12, 2, 3))
        q = L.place("barn", at=(6, 2), face="north")  # turned: plan 3 wide, 2 tall
        self.assertEqual((q.pw, q.ph), (3, 2))
        self.assertIsNone(L.place("barn", rect=(10, 2, 11, 3)))  # 2 x 2 != 2 x 3
        self.assertIn("V4", {i.code for i in L.issues})

    def test_overlap_is_reported_with_both_sources(self):
        L = layout()
        L.fill("grass", district="m")
        L.place("cottage", at=(4, 4))
        self.assertIsNone(L.place("oak", at=(5, 5)))
        msg = [i for i in L.issues if i.code == "V2"][0]
        self.assertIn("cottage", msg.message)
        self.assertIn("test_api.py", msg.src)

    def test_scatter_is_local_and_deterministic(self):
        def run(extra):
            L = layout()
            L.fill("grass", district="m")
            if extra:
                L.scatter(Rect(0, 0, 10, 23), {"rock": 1}, 0.3, seed="other")
            got = L.scatter(Rect(12, 0, 31, 23), {"oak": 1, "pine": 1}, 0.3, seed="wood")
            return [(p.id, p.c, p.r, p.k) for p in got]

        self.assertEqual(run(False), run(True))
        self.assertGreater(len(run(False)), 50)

    def test_houses_face_their_street(self):
        L = layout()
        L.fill("grass", district="m")
        s = L.street([(0, 10), (31, 10)], width=2, paving="cobble")
        hs = L.houses(Rect(0, 0, 31, 23), {"cottage": 1, "toolshed": 1}, front=[s], gap=0.1,
                      seed="t")
        self.assertGreater(len(hs), 6)
        street = Line(s.points, 2).mask(0, 0, 64, 48)
        reached = {p.door for p in hs}
        self.assertTrue(all(d is not None for d in reached))
        front = sum(1 for p in hs if street[p.door[1], p.door[0]])
        self.assertGreater(front, len(hs) // 2)


class Bible(unittest.TestCase):
    def test_persepolis_table(self):
        marks = bible.parse(ROOT / "docs/design/cities/persepolis.md")
        self.assertEqual(marks["apadana"].rect, (60, 54, 83, 77))
        self.assertEqual(marks["apadana"].level, (7, 7))
        self.assertEqual(marks["great_stair"].level, (0, 6))
        self.assertNotIn("terrace", marks)  # an outline, not a rect


if __name__ == "__main__":
    unittest.main()
