"""Layer and graph formats: the world-tech §2.4 hex example, engine-style rejection, round trips."""

import unittest

import numpy as np

from worldgen.graph import Edge, Graph, Lane, Node, Port, read_graph, write_graph
from worldgen.layer import (LayerFormatError, LayerGrid, LayerItem, PlanItem, PlanLayer,
                            grid_to_plan, plan_to_grid, read_lcw, write_lcw)

HEX = """
4C 43 57 4C  01 00  00 00  0A 00 14 00  02 00 01 00
01 00 01 00 01 00 00 00
05 67 72 61 73 73
0D 63 6F 72 6E 65 72 2F 6D 65 61 64 6F 77
03 6F 61 6B
00 00  FE 00
01 01
00 01
01 00 00 00  00 00 00 00 00 00 02 00
"""


def example() -> bytes:
    return bytes.fromhex(HEX.replace("\n", " "))


class LayerFile(unittest.TestCase):
    def test_hex_example_parses(self):
        lg = read_lcw(example())
        self.assertEqual((lg.x0, lg.y0, lg.w, lg.h), (10, 20, 2, 1))
        self.assertEqual((lg.terrains, lg.districts, lg.item_ids),
                         (["grass"], ["corner/meadow"], ["oak"]))
        self.assertEqual(lg.T.tolist(), [[0, 0xFE]])
        self.assertEqual(lg.L.tolist(), [[1, 1]])
        self.assertEqual(lg.D.tolist(), [[0, 0]])
        self.assertEqual(lg.items, [LayerItem(0, 0, 0, 2, 0)])

    def test_hex_example_round_trips_byte_for_byte(self):
        self.assertEqual(write_lcw(read_lcw(example())), example())

    def test_written_example_matches_hex(self):
        lg = LayerGrid(10, 20, 2, 1, ["grass"], ["corner/meadow"], ["oak"],
                       np.array([[0, 0xFE]], np.uint8), np.array([[1, 1]], np.uint8),
                       np.array([[0, 0]], np.uint8), [LayerItem(0, 0, 0, 2)])
        self.assertEqual(write_lcw(lg), example())

    def test_rejects_bad_files(self):
        data = example()
        for bad in (data[:-1], data + b"\x00", b"XXXX" + data[4:], data[:30]):
            with self.assertRaises(LayerFormatError):
                read_lcw(bad)
        big = bytearray(data)
        big[12] = 0xFF  # w = 255: the planes no longer fill the rect
        with self.assertRaises(LayerFormatError):
            read_lcw(bytes(big))
        with self.assertRaises(LayerFormatError):
            read_lcw(data, grid=(11, 1280))  # x 10..11 leaves an 11-wide grid

    def test_long_runs_split(self):
        lg = LayerGrid(0, 0, 300, 2, ["grass"], ["d/x"], [], np.zeros((2, 300), np.uint8),
                       np.zeros((2, 300), np.uint8), np.zeros((2, 300), np.uint8))
        back = read_lcw(write_lcw(lg))
        self.assertTrue((back.T == 0).all())

    def test_plan_grid_round_trip(self):
        rng = np.random.default_rng(1)
        T = rng.integers(0, 3, (5, 7)).astype(np.uint8)
        L = rng.integers(0, 16, (5, 7)).astype(np.uint8)
        D = np.zeros((5, 7), np.uint8)
        items = [PlanItem("cottage", 100, 50, 2, 2, 1), PlanItem("barn", 102, 51, 2, 3, 1)]
        pl = PlanLayer(100, 50, 7, 5, ["a", "b", "c"], ["r/d"], T, L, D, items)
        fp = {"cottage": (2, 2), "barn": (2, 3)}
        lg = plan_to_grid(pl, lambda i, v: fp[i])
        self.assertEqual((lg.x0, lg.y0, lg.w, lg.h), (50, 1279 - 106, 5, 7))
        # Plan (C, R) = (106, 50), the north-east corner, is grid (50, 1173) = cell (0, 0).
        self.assertEqual(lg.T[0, 0], T[0, 6])
        back = grid_to_plan(read_lcw(write_lcw(lg)), lambda i, v: fp[i])
        self.assertTrue((back.T == T).all() and (back.L == L).all())
        self.assertEqual(sorted((i.id, i.c, i.r) for i in back.items),
                         sorted((i.id, i.c, i.r) for i in items))


class GraphFile(unittest.TestCase):
    def test_round_trip_is_identical(self):
        g = Graph("rome", [Node("forum", (88, 1093), "dest"), Node("n12", (92, 1090)),
                           Node("appia_se", (168, 1008), "portal")],
                  [Edge("forum", "n12", "street"),
                   Edge("n12", "appia_se", "road", [(120, 1060), (150, 1030)])],
                  [Lane("tiber", "river", [(183, 1119), (200, 1140)],
                        [Port("emporium", 0, "rome.quay:mooring"), Port("portus", 1)])])
        text = write_graph(g)
        self.assertEqual(write_graph(read_graph(text)), text)
        self.assertEqual(read_graph(text), g)


if __name__ == "__main__":
    unittest.main()
