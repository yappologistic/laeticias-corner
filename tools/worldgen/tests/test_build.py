"""Determinism (V13), round trips of whole layers through the reader, previews on a tiny world."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from tests.helpers import ROOT, atlas, catalog, check, ground_layout, layout
from worldgen import base, compiler, compose, preview
from worldgen.build import Builder
from worldgen.graph import read_graph, write_graph
from worldgen.layer import grid_to_plan, plan_to_grid, read_lcw, write_lcw
from worldgen.shapes import Rect


def fp(iid, v):
    d = catalog().items[iid]
    fx, fy = d.footprint_k(v)
    return (fy, fx)


def village():
    L = layout()
    L.fill("grass", district="village")
    s = L.street([(0, 12), (31, 12)], width=2, paving="cobble")
    L.houses(Rect(0, 0, 31, 23), {"cottage": 2, "barn": 1, "toolshed": 1}, front=[s],
             seed="v")
    L.river([(0, 20), (31, 21)], width=1, banks={"reeds": 0.3}, seed="brook")
    L.scatter(Rect(0, 0, 31, 23), {"oak": 1, "flowers_red": 1}, 0.1, seed="green", clump=0.5)
    L.node("west", (0, 12))
    return L


class Determinism(unittest.TestCase):
    def test_layer_compiles_to_the_same_bytes(self):
        out = []
        for _ in range(2):
            pl, _ = compiler.compile_layer(village())
            g, _ = compiler.derive_graph(village())
            out.append((write_lcw(plan_to_grid(pl, fp)), write_graph(g)))
        self.assertEqual(out[0], out[1])

    def test_base_layer_compiles_to_the_same_bytes(self):
        out = []
        for _ in range(2):
            L, g, _ = base.build_base(catalog())
            pl, _ = compiler.compile_layer(L)
            out.append((write_lcw(plan_to_grid(pl, fp)), write_graph(g)))
        self.assertEqual(out[0], out[1])


class RoundTrip(unittest.TestCase):
    def test_layer_through_the_reader(self):
        pl, _ = compiler.compile_layer(village())
        back = grid_to_plan(read_lcw(write_lcw(plan_to_grid(pl, fp))), fp)
        for a in ("T", "L", "D"):
            self.assertTrue(np.array_equal(getattr(back, a), getattr(pl, a)), a)
        self.assertEqual((back.terrains, back.districts), (pl.terrains, pl.districts))
        self.assertEqual(sorted((i.id, i.c, i.r, i.variant) for i in back.items),
                         sorted((i.id, i.c, i.r, i.variant) for i in pl.items))
        g, _ = compiler.derive_graph(village())
        self.assertEqual(read_graph(write_graph(g)), g)

    def test_village_validates(self):
        errs = [i.text() for i in check(village()) if i.level == "error"]
        self.assertEqual(errs, [])


class Previews(unittest.TestCase):
    def test_tiny_world_previews(self):
        upl, _ = compiler.compile_layer(ground_layout())
        pl, _ = compiler.compile_layer(village())
        w = compose.compose([("base", upl), ("corner", pl)])
        m = preview.map_image(w, catalog(), atlas(), (0, 0, 63, 47), 4)
        self.assertEqual(m.size, (256, 192))
        iso = preview.IsoRenderer(w, catalog(), atlas(), ROOT)
        img = iso.render((8, 8, 43, 35), 1, strip=128)
        a = np.asarray(img)
        self.assertGreater(img.width, 1000)
        self.assertGreater(len(np.unique(a.reshape(-1, 3), axis=0)), 50)  # not blank
        big = iso.render((0, 0, 63, 47), 1, max_px=600)
        self.assertLessEqual(max(big.size), 600)

    def test_missing_art_draws_a_labelled_placeholder(self):
        iso = preview.IsoRenderer(compose.compose([]), catalog(), atlas(), ROOT)
        im, ox, oy = iso.placeholder("world.wayside_shrine", 1, 1)
        self.assertGreater(im.height, 40)


class BuilderOutput(unittest.TestCase):
    def test_world_json_lists_every_layer_and_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Builder(ROOT, Path(tmp), Path(tmp) / "reports")
            import json
            doc = json.loads(b.world_json())
            self.assertEqual(doc["grid"], [448, 1280])
            self.assertEqual(doc["home"]["origin"], [40, 1200])
            self.assertEqual(doc["layers"][0]["id"], "base")
            self.assertIn("parsa", [r["id"] for r in doc["regions"]])


if __name__ == "__main__":
    unittest.main()
