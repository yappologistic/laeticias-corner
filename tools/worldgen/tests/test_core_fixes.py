"""The core rules the Rome builder asked for: moorings on water, decks over water, junctions only
at one level, the README status line, world.json against the layer files, the Rome portals and
placeholders in the plan."""

import json
import tempfile
import unittest
from pathlib import Path

from plan import world_plan as P
from tests.helpers import catalog, check, codes, layout
from worldgen import compiler
from worldgen.finish import clear_doors
from worldgen.shapes import Rect
from worldgen.validate import readme_complete, world_file


def meadow():
    L = layout()
    L.fill("grass", district="village")
    return L


class Moorings(unittest.TestCase):
    """`rome.quay` (r0) moors its boat on the tile west of the post."""

    def quay(self, water_cols=(10, 11)):
        L = meadow()
        L.paint(Rect(water_cols[0], 0, water_cols[1], 23), "water")
        L.street([(13, 0), (13, 23)], width=1, paving="path")
        L.node("n", (13, 0))
        L.node("s", (13, 23))
        return L

    def test_mooring_on_water_beside_the_quay_is_valid(self):
        L = self.quay()
        p = L.place("rome.quay", at=(12, 8), face="west")
        self.assertEqual(p.slots["mooring"][0][:2], (L.origin[0] + 11, L.origin[1] + 8))
        clear_doors(L, all_slots=True)
        self.assertFalse(p.removed, "the clean-up keeps a post whose boat spot is on water")
        v7 = [i for i in check(L) if i.code == "V7" and i.level == "error"]
        self.assertEqual(v7, [], [i.text() for i in v7])

    def test_mooring_with_no_land_beside_it_is_an_error(self):
        L = self.quay(water_cols=(8, 12))
        L.paint(Rect(10, 8, 10, 8), "grass")          # the post on a rock in the river
        L.place("rome.quay", at=(10, 8), face="west")
        self.assertTrue(any("touches no walkable tile" in i.message for i in check(L)
                            if i.code == "V7" and i.level == "error"))

    def test_mooring_out_of_reach_of_the_graph_is_an_error(self):
        L = meadow()
        L.paint(Rect(2, 0, 3, 23), "water")
        L.level(Rect(5, 0, 31, 23), 3)                 # a cliff between the quay and the street
        L.street([(30, 0), (30, 23)], width=1, paving="path")
        L.place("rome.quay", at=(4, 8), face="west")
        self.assertTrue(any("mooring slot" in i.message and "walking tiles" in i.message
                            for i in check(L) if i.code == "V7" and i.level == "error"))


class Decks(unittest.TestCase):
    """The bridge's own `on` is set per test: the set catalog says where it stands."""

    def setUp(self):
        self.d = catalog().items["rome.pons_fabricius"]
        self.on = self.d.on

    def tearDown(self):
        self.d.on = self.on

    def bridge(self):
        """A river one level below its banks, a bridge across it, a way over its deck (which
        keeps the water under it) joining the streets on both banks."""
        L = meadow()
        L.paint(Rect(14, 0, 17, 23), "water")
        L.level(Rect(14, 0, 17, 23), -1)
        west = L.street([(0, 12), (13, 12)], width=1, paving="path")
        L.street([(13, 12), (18, 12)], width=1, paving=None)
        L.street([(18, 12), (31, 12)], width=1, paving="path")
        L.node("west", (0, 12))
        L.node("east", (31, 12))
        p = L.place("rome.pons_fabricius", at=(14, 11))
        return L, p, west

    def test_deck_over_water_joins_the_banks(self):
        self.d.on = "water"
        L, p, _ = self.bridge()
        self.assertEqual(L.walk_tiles(p), {(L.origin[0] + c, L.origin[1] + 12)
                                           for c in range(14, 18)})
        self.assertEqual(L.terrain_at(L.origin[0] + 15, L.origin[1] + 12), "water")
        issues = check(L)
        bad = [i for i in issues if i.code in ("V5", "V6") and i.level == "error"]
        self.assertEqual(bad, [], [i.text() for i in bad])

    def test_landmark_floor_on_land_is_no_deck(self):
        self.d.on = "land"
        L, p, _ = self.bridge()
        L.paint(Rect(14, 11, 17, 13), "grass")       # the bridge on a mud bank at water level
        self.assertTrue(any("without a stair" in i.message for i in check(L)
                            if i.code == "V5" and i.level == "error"))


class Junctions(unittest.TestCase):
    def terrace(self):
        L = meadow()
        L.level(Rect(0, 0, 31, 10), 2)                     # a terrace north of the street
        low = L.street([(0, 12), (31, 12)], width=1, paving="path")
        high = L.street([(10, 2), (10, 10)], width=1, paving="path")   # ends a tile above it
        return L, low, high

    def test_street_end_does_not_join_a_street_on_another_level(self):
        L, _, _ = self.terrace()
        g, _ = compiler.derive_graph(L)
        top = next(n.id for n in g.nodes if n.at == L_grid(L, 10, 10))
        joined = {e.b if e.a == top else e.a for e in g.edges if top in (e.a, e.b)}
        self.assertEqual(len(joined), 1, "only its own street's other end")

    def test_a_stair_joins_the_levels(self):
        L, _, _ = self.terrace()
        L.level(Rect(20, 9, 20, 10), 1)
        L.stair("world.stair_stone", rect=(20, 10, 20, 11), face="south")
        L.level(Rect(20, 10, 20, 11), 1)
        L.level(Rect(20, 9, 20, 9), 2)
        L.street([(20, 2), (20, 9)], width=1, paving="path")
        g, _ = compiler.derive_graph(L)
        self.assertTrue(any(e.kind == "stair" for e in g.edges))
        self.assertNotIn("V5", codes(check(L)))


def L_grid(L, c, r):
    from worldgen.coords import to_grid
    return to_grid(L.origin[0] + c, L.origin[1] + r)


class Files(unittest.TestCase):
    def test_readme_status_is_a_line_not_a_phrase(self):
        self.assertTrue(readme_complete("# Rome\n\nStatus: complete\n"))
        self.assertFalse(readme_complete("Status: built. Mark it complete here (Status: complete) "
                                         "once the art lands."))

    def test_world_json_lists_exactly_the_layer_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "layers").mkdir()
            for n in ("base", "rome"):
                (out / "layers" / f"{n}.lcw").write_bytes(b"")
            doc = {"layers": [{"id": "base"}]}
            (out / "world.json").write_text(json.dumps(doc))
            self.assertTrue(world_file(out, [n for n, _, _ in P.LAYERS]))
            doc["layers"].append({"id": "rome"})
            (out / "world.json").write_text(json.dumps(doc))
            self.assertEqual(world_file(out, [n for n, _, _ in P.LAYERS]), [])

    def test_rome_portals_and_placeholders(self):
        layers, tile, level = P.PORTALS["portuensis"]
        self.assertEqual((layers, tile, level), (("ostia", "rome"), (140, 184), 1))
        cat = catalog()
        for lid, (w, h) in {"saepta": (9, 23), "iseum": (7, 9), "stadium_domitian": (10, 25),
                            "pompey_theatre": (12, 12), "trajan_baths": (30, 30)}.items():
            d = cat.items[f"rome.{lid}"]
            self.assertEqual((d.footprint[1], d.footprint[0]), (w, h), lid)
            self.assertTrue(d.landmark)


if __name__ == "__main__":
    unittest.main()


class Network(unittest.TestCase):
    """The journey's chain across layers: portals, lanes and seam crossings join it."""

    def graphs(self):
        from worldgen.coords import to_grid
        from worldgen.graph import Edge, Graph, Lane, Node, Port

        def g(name, nodes, edges=(), lanes=()):
            gr = Graph(name)
            gr.nodes = [Node(i, to_grid(*at), k) for i, at, k in nodes]
            gr.edges = [Edge(a, b, "road") for a, b in edges]
            gr.lanes = [Lane(i, "sea", [to_grid(*p) for p in pts], [Port(pid, k) for pid, k in pp])
                        for i, pts, pp in lanes]
            return gr
        return {
            "a": g("a", [("gate", (0, 0), None), ("quay", (10, 0), None)], [("gate", "quay")],
                   [("out", [(11, 1), (30, 1)], [("quay", 0), ("mist_w", 1)])]),
            "b": g("b", [("pier", (61, 2), None), ("town", (70, 2), "dest")],
                   [("pier", "town")], [("in", [(60, 1), (50, 1)], [("pier", 0), ("mist_e", 1)])]),
        }

    def test_lanes_and_the_mist_join_the_chain(self):
        from worldgen.validate import network
        self.assertEqual(network(self.graphs(), ["a:gate", "b:town"]), [])

    def test_a_break_is_named(self):
        from worldgen.validate import network
        gs = self.graphs()
        gs["b"].edges = []
        issues = network(gs, ["a:gate", "b:pier", "b:town"])
        self.assertTrue(issues and "breaks after b:pier" in issues[0].message, issues)
        self.assertTrue(network(gs, ["a:gate", "c:nowhere"]))


class SunkenFloor(unittest.TestCase):
    """V3 lets a landmark's walk tiles lie a level off its flat footprint (the Pārsa Treasury's
    corridor stepping down to its door), and V5 lets walkers take that step."""

    def setUp(self):
        self.d = catalog().items["rome.pons_fabricius"]
        self.on = self.d.on
        self.d.on = "land"

    def tearDown(self):
        self.d.on = self.on

    def layout(self, drop):
        L = meadow()
        L.street([(0, 12), (13, 12)], width=1, paving="path")
        L.street([(13, 12), (18, 12)], width=1, paving=None)
        L.street([(18, 12), (31, 12)], width=1, paving="path")
        L.level(Rect(14, 12, 17, 12), -drop)          # the deck row: the bridge's walk tiles
        L.place("rome.pons_fabricius", at=(14, 11))
        return L

    def test_walk_tiles_one_level_down_pass(self):
        issues = check(self.layout(1))
        bad = [i for i in issues if i.code in ("V3", "V5") and i.level == "error"]
        self.assertEqual(bad, [], [i.text() for i in bad])

    def test_two_levels_down_is_refused(self):
        self.assertTrue(any("more than a level off" in i.message for i in check(self.layout(2))
                            if i.code == "V3"))

    def test_solid_part_must_stay_flat(self):
        L = self.layout(1)
        L.level(Rect(14, 11, 14, 11), 1)              # a solid tile of the footprint raised
        self.assertTrue(any("not flat" in i.message for i in check(L) if i.code == "V3"))
