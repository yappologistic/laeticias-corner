"""L12 lit nights (graphics plan W1): the light points and profiles of a region file. Each rule has
a document that passes and one that fails, over a tiny world built in the test."""

import copy
import unittest

from tests.helpers import catalog, ground_layout, layout
from worldgen import compiler, compose, lights


def world():
    L = layout()
    L.district("meadows", (0, 0, 31, 23))
    L.place("cottage", at=(4, 4))
    L.place("lamp", at=(10, 4))
    L.place("bench", at=(14, 4))
    upl, _ = compiler.compile_layer(ground_layout())
    pl, _ = compiler.compile_layer(L)
    return compose.compose([("base", upl), (L.layer, pl)])


W = world()


def origin(iid):
    it = next(it for _, it in compose.live_items(W) if it.id == iid)
    return list(lights.grid_origin(it))


def doc():
    return {"id": "corner",
            "districts": [{"id": "meadows", "area": "town",
                           "populations": [{"actor": "cat", "density": "d"}]}],
            "festivals": [{"id": "fair"}], "events": [{"id": "dance"}],
            "roles": [{"id": "night_walker", "carries": {"light": "carried_lamp", "prop": "lamp"}}],
            "lights": {"version": 1, "profiles": {
                k: copy.deepcopy(lights.PROFILES[k])
                for k in ("window_evening", "niche_lamp", "carried_lamp", "door_lamp")}},
            "light_points": [origin("cottage") + ["cottage", "window_evening"],
                             origin("cottage") + ["cottage", "door_lamp"],
                             origin("lamp") + ["lamp", "niche_lamp"]]}


class Lights(unittest.TestCase):
    def errors(self, d):
        return [w + ": " + m for lv, w, m in lights.check(d, W, catalog()) if lv == "error"]

    def test_a_lit_region_passes(self):
        self.assertEqual(self.errors(doc()), [])

    def test_a_point_at_no_item_fails(self):
        d = doc()
        d["light_points"][0][0] += 1
        self.assertTrue(any("has its origin" in m for m in self.errors(d)))

    def test_a_point_at_an_item_without_glow_fails(self):
        d = doc()
        d["light_points"].append(origin("bench") + ["bench", "niche_lamp"])
        self.assertTrue(any("gives no light" in m for m in self.errors(d)))

    def test_an_unknown_emitter_fails(self):
        d = doc()
        d["light_points"][2].append("chimney")
        self.assertTrue(any("no emitter" in m for m in self.errors(d)))

    def test_two_lights_of_a_kind_on_a_tile_fail(self):
        d = doc()
        d["lights"]["profiles"]["window_late"] = copy.deepcopy(lights.PROFILES["window_late"])
        d["light_points"].append(origin("cottage") + ["cottage", "window_late"])
        self.assertTrue(any("a second window" in m for m in self.errors(d)))

    def test_bad_hours_fail(self):
        for hours in ([["dusk", "25:00"]], [["dusk"]], [["20:00", "20:00"]], []):
            d = doc()
            d["lights"]["profiles"]["niche_lamp"]["hours"] = hours
            self.assertTrue(any("hours" in m for m in self.errors(d)), hours)

    def test_bad_conditions_fail(self):
        for k, v, word in (("rain", "sometimes", "rain"), ("only", "midsummer", "festival"),
                           ("only", "event:parade", "event"), ("festivals", {"fair": 9}, "factor"),
                           ("kelvin", 4000, "kelvin"), ("kind", "neon", "kind")):
            d = doc()
            d["lights"]["profiles"]["niche_lamp"][k] = v
            self.assertTrue(any(word in m for m in self.errors(d)), (k, v))

    def test_a_flicker_past_a_ramp_step_fails(self):
        d = doc()
        d["lights"]["profiles"]["niche_lamp"]["flicker"]["depth"] = 0.2
        self.assertTrue(any("depth" in m for m in self.errors(d)))

    def test_a_carrier_without_its_profile_fails(self):
        d = doc()
        del d["lights"]["profiles"]["carried_lamp"]
        self.assertTrue(any("carries" in m for m in self.errors(d)))

    def test_a_populated_district_dark_at_dusk_fails(self):
        d = doc()
        d["light_points"] = []
        self.assertTrue(any("no light at dusk" in m for m in self.errors(d)))

    def test_points_are_capped_per_chunk(self):
        pts = [[i % 30, i // 30, "x", "window_evening"] for i in range(200)]
        self.assertEqual(len(lights._cap(pts)), lights.CHUNK_CAP)

    def test_lit_at_runs_past_midnight(self):
        p = lights.PROFILES["window_late"]
        self.assertTrue(lights.lit_at(p, 23.5))
        self.assertTrue(lights.lit_at(p, 1.0))
        self.assertFalse(lights.lit_at(p, 3.0))
        self.assertFalse(lights.lit_at(p, 12.0))


class NightPosts(unittest.TestCase):
    """Layouts add lamps beside streets: never on a door step or in a one-tile passage, never
    two of a kind within the gap."""

    def test_lamps_keep_their_gap_and_leave_passages_free(self):
        from worldgen.finish import night_posts
        L = layout()
        L.fill("grass", district="meadows")
        L.street([(0, 12), (31, 12)], width=1, paving="path")
        L.place("stone_wall", at=(10, 9))
        L.place("stone_wall", at=(12, 9))     # (11, 9): a one-tile passage between two walls
        placed = night_posts(L, "lamp", [(11, 10), (13, 10), (20, 10)], ring=1, gap=4)
        tiles = [(p.c - L.origin[0], p.r - L.origin[1]) for p in placed]
        self.assertNotIn((11, 9), tiles)
        for i, a in enumerate(tiles):
            for b in tiles[i + 1:]:
                self.assertGreaterEqual(max(abs(a[0] - b[0]), abs(a[1] - b[1])), 4)
        self.assertTrue(all(not L.STREET[r, c] for c, r in tiles))
