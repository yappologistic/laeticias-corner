"""Rules for landmarks and stairs that the city layers rely on: furniture on walk tiles, paths into
landmarks whose geometry is not emitted yet, chained stairs, planned base routes, set footprints
that include attached parts."""

from __future__ import annotations

import copy
import unittest

from worldgen import compiler, compose
from worldgen.dsl import Layout
from worldgen.graph import Graph
from worldgen.validate import Target, validate

from tests.helpers import ROOT, catalog, ground_layout


def _cat(extra_items=(), geom=None):
    cat = copy.deepcopy(catalog())
    for spec in extra_items:
        cat.items[spec["id"]] = cat._item(spec, "catalog", "test")
    for iid, g in (geom or {}).items():
        cat.geom[iid] = g
    return cat


def _layout(cat, layer="corner", region="corner", origin=(10, 10), size=(32, 24), base=2):
    L = Layout(layer=layer, region=region, set="home", origin=origin, size=size, base_level=base,
               catalog=cat, regions=[region], source="test")
    return L


def _check(L, cat, graphs=None, under_rect=(0, 0, 63, 47)):
    under = ground_layout(rect=under_rect)
    upl, _ = compiler.compile_layer(under)
    pl, issues = compiler.compile_layer(L)
    g, gissues = compiler.derive_graph(L)
    world = compose.compose([("base", upl), (L.layer, pl)])
    tg = Target(L.layer, L.regions, pl, g, L, L.issues + issues + gissues)
    gs = dict(graphs or {})
    gs[L.layer] = g
    return validate(world, cat, ROOT, tg, gs, set(gs)), g


HALL = {"id": "test.hall", "footprint": [3, 3], "layout": "rotate", "count": 4,
        "rotations": [0], "landmark": True, "on": "land", "height": 60}
SEAT = {"id": "test.seat", "footprint": [1, 1], "layout": "rotate", "count": 4, "on": "land"}


class TestLandmarkRules(unittest.TestCase):
    def test_furniture_stands_on_walk_tiles_only(self):
        # Walk tile (dx 1, dy 1) is the footprint's centre: plan (c0 + 1, r0 + 1).
        cat = _cat([HALL, SEAT], {"test.hall": {"r0": {"walk": [[1, 1]]}}})
        L = _layout(cat)
        L.fill("grass", district="meadows")
        hall = L.place("test.hall", rect=(4, 4, 6, 6))
        self.assertIn((L.origin[0] + 5, L.origin[1] + 5), L.walk_tiles(hall))
        self.assertIsNotNone(L.place("test.seat", at=(5, 5)))
        self.assertIsNone(L.place("test.seat", at=(4, 4)))  # a wall tile of the hall
        issues, _ = _check(L, cat)
        v2 = [i for i in issues if i.code == "V2" and i.level == "error"]
        self.assertEqual(len(v2), 1, [i.message for i in v2])

    def test_path_into_landmark_without_geometry_is_a_warning(self):
        cat = _cat([HALL])
        L = _layout(cat)
        L.fill("grass", district="meadows")
        L.place("test.hall", rect=(4, 4, 6, 6))
        L.street([(1, 5), (10, 5)], width=1, paving="path")
        issues, _ = _check(L, cat)
        self.assertFalse([i for i in issues if i.code == "V5" and i.level == "error"])
        self.assertTrue([i for i in issues if i.code == "V5" and "without geometry" in i.message])
        # With geometry that leaves the row closed, the same path is an error.
        cat2 = _cat([HALL], {"test.hall": {"r0": {"walk": [[0, 0]]}}})
        L2 = _layout(cat2)
        L2.fill("grass", district="meadows")
        L2.place("test.hall", rect=(4, 4, 6, 6))
        L2.street([(1, 5), (10, 5)], width=1, paving="path")
        issues2, _ = _check(L2, cat2)
        self.assertTrue([i for i in issues2 if i.code == "V5" and i.level == "error"])

    def test_chained_stair_landings_join_only_their_flights(self):
        cat = _cat()
        L = _layout(cat)
        L.fill("grass", district="meadows")
        L.street([(1, 20), (30, 20)], width=1, paving="path")
        # Two flights climbing north along c 10: landing at r 16 is level 1, the top r 13 level 2.
        L.level((10, 14, 10, 16), 1)
        L.level((8, 4, 12, 13), 2)
        L.stair("world.stair_earth", rect=(10, 17, 10, 18), face="south")
        L.stair("world.stair_earth", rect=(10, 14, 10, 15), face="south")
        L.street([(10, 13), (10, 5)], width=1, paving="path")
        issues, g = _check(L, cat)
        self.assertFalse([i for i in issues if i.code in ("V3", "V5", "V6") and
                          i.level == "error"], [i.text() for i in issues if i.level == "error"])
        landing = [n.id for n in g.nodes if n.at == (16 + 10, 1279 - 20)]
        self.assertEqual(len(landing), 1)
        touching = [e for e in g.edges if landing[0] in (e.a, e.b)]
        self.assertEqual(sorted(e.kind for e in touching), ["stair", "stair"])

    def test_portal_on_a_planned_base_route_warns(self):
        cat = _cat()
        L = _layout(cat, layer="parsa", region="parsa", origin=(1136, 350), size=(8, 8), base=4)
        L.fill("parsa.plain_grass", district="plain")
        L.street([(0, 4), (7, 4)], width=1, paving="parsa.plain_grass", kind="road",
                 portal="royal_road_w")
        issues, _ = _check(L, cat, graphs={"base": Graph("base")},
                           under_rect=(1130, 344, 1150, 364))
        v6 = [i for i in issues if i.code == "V6"]
        self.assertTrue(v6)
        self.assertFalse([i for i in v6 if i.level == "error"], [i.message for i in v6])

    def test_set_footprint_holding_the_bible_rect_warns(self):
        # persepolis.md: kaba at c 10..12, r 13..15 (3 x 3); a set modelling it 3 x 4 is placed
        # over that rect plus one row: a warning. Shifted off the bible's rect: an error.
        kaba = {"id": "parsa.kaba", "footprint": [4, 3], "layout": "rotate", "count": 4,
                "rotations": [0], "landmark": True, "on": "land", "height": 120}
        for rect, want in (((10, 13, 12, 16), "warning"), ((11, 13, 13, 16), "error")):
            cat = _cat([kaba])
            L = _layout(cat, layer="parsa", region="parsa", origin=(1136, 304), size=(24, 24),
                        base=4)
            L.fill("parsa.plain_grass", district="plain")
            L.place("parsa.kaba", rect=rect, name="kaba")
            issues, _ = _check(L, cat, under_rect=(1130, 300, 1165, 330))
            v4 = [i for i in issues if i.code == "V4" and "kaba" in i.message
                  and "not placed" not in i.message]
            self.assertEqual([i.level for i in v4], [want], [i.message for i in v4])


if __name__ == "__main__":
    unittest.main()
