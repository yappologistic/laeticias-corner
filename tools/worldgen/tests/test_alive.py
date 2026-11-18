"""The world's liveliness checks (worldgen.alive A1-A6) and traffic (worldgen.traffic): clean
inputs pass, and each check trips on a deliberate fault. Inputs are tiny synthetic documents
and graphs, never committed data."""

import unittest

import numpy as np

from worldgen import alive, traffic
from worldgen.graph import Edge, Graph, Lane, Node, Port

MONTHS = alive.MONTHS


def graphs() -> dict[str, Graph]:
    """Two layers joined at a portal: a road a - s (a station) - p, and p - t in a town; a lane."""
    base = Graph("base", nodes=[Node("a", (10, 10)), Node("s", (10, 20), "station"),
                                Node("p", (10, 30), "portal")],
                 edges=[Edge("a", "s", "road"), Edge("s", "p", "road")],
                 lanes=[Lane("sea_lane", "sea", [(40, 10), (40, 30)],
                             [Port("start", 0), Port("harbour", 1), Port("end", 1)])])
    town = Graph("town", nodes=[Node("p", (10, 30), "portal"), Node("market", (10, 34), "dest")],
                 edges=[Edge("p", "market", "street")])
    return {"base": base, "town": town}


def token(**kw) -> dict:
    tk = {"id": "r.0", "actor": "world.traveller", "route": {"start": "base:a",
                                                            "end": "town:market"},
          "count": 2, "hours": ["05:00", "19:30"], "rest": ["base:s"], "offsets": [0.1, 0.6]}
    tk.update(kw)
    return tk


def doc(**kw) -> dict:
    d = {"id": "r", "districts": [], "lanes_tokens": [token()], "festivals": [], "chains": [],
         "events": [{"id": f"e_{s}", "trigger": {"on": "window", "hours": ["08:00", "08:30"],
                                                 "season": s}, "size": "small"}
                    for s in ("spring", "summer", "autumn", "winter")]}
    d.update(kw)
    return d


class TrafficTest(unittest.TestCase):
    def test_path_crosses_layers_at_portals(self):
        j = traffic.Joined(graphs())
        path, length = j.path("base:a", "town:market")
        self.assertEqual(path, ["base:a", "base:s", "base:p", "town:p", "town:market"])
        self.assertEqual(length, 24)
        self.assertEqual(len(j.course(path)), 10 + 1 + 10 + 1 + 4 + 1)

    def test_rest_stops_are_stations_and_towns_never_junctions(self):
        j = traffic.Joined(graphs())
        path, _ = j.path("base:a", "town:market")
        self.assertEqual(traffic.rest_stops(path, j.kind), ["base:s", "town:market"])

    def test_offsets_are_irregular_and_stable(self):
        a = traffic.offsets("x.3", 5)
        self.assertEqual(a, traffic.offsets("x.3", 5))
        gaps = sorted(a)
        steps = {round(b - a_, 3) for a_, b in zip(gaps, gaps[1:])}
        self.assertGreater(len(steps), 1)      # not a clockwork beat
        self.assertTrue(all(0 <= x < 1 for x in a))

    def test_finish_fills_every_token(self):
        d = {"id": "r", "lanes_tokens": [
            {"actor": "world.fishing_boat", "lane": "base:sea_lane", "count": 1},
            {"actor": "parsa.courier", "route": {"start": "base:a", "end": "town:market"},
             "count": 3}]}
        traffic.finish(d, graphs())
        boat, courier = d["lanes_tokens"]
        self.assertEqual(boat["hours"], traffic.FISHING)
        self.assertEqual(boat["rest"], ["harbour"])
        self.assertEqual(courier["hours"], traffic.ALL_DAY)
        self.assertEqual(courier["rest"], ["base:s", "town:market"])
        self.assertEqual(len(courier["offsets"]), 3)


class AliveChecksTest(unittest.TestCase):
    def setUp(self):
        self.g = graphs()
        self.j = traffic.Joined(self.g)

    # A3
    def test_a3_clean(self):
        self.assertEqual(alive.check_tokens({"r": doc()}, self.g, self.j), [])

    def test_a3_missing_end(self):
        bad = doc(lanes_tokens=[token(route={"start": "base:a", "end": "town:nowhere"})])
        self.assertIn("does not exist", alive.check_tokens({"r": bad}, self.g, self.j)[0][2])

    def test_a3_no_rest_stop(self):
        bad = doc(lanes_tokens=[token(rest=[])])
        self.assertIn("no rest stop", alive.check_tokens({"r": bad}, self.g, self.j)[0][2])

    def test_a3_rest_off_the_way(self):
        bad = doc(lanes_tokens=[token(rest=["base:elsewhere"])])
        self.assertIn("not on its way", alive.check_tokens({"r": bad}, self.g, self.j)[0][2])

    def test_a3_lane_rest_must_be_a_port(self):
        bad = doc(lanes_tokens=[token(route=None, lane="base:sea_lane", rest=["piraeus"])])
        del bad["lanes_tokens"][0]["route"]
        self.assertIn("not a port", alive.check_tokens({"r": bad}, self.g, self.j)[0][2])

    def test_a3_offsets_per_instance(self):
        bad = doc(lanes_tokens=[token(offsets=[0.2])])
        self.assertIn("offset", alive.check_tokens({"r": bad}, self.g, self.j)[0][2])

    # A4
    def test_a4_clean_split_family(self):
        d = doc(districts=[{"id": "x", "populations": [
            {"actor": "world.sheep", "density": "herd", "max_per_chunk": 2,
             "when": {"months": MONTHS[:6]}},
            {"actor": "world.sheep", "density": "herd", "max_per_chunk": 1,
             "when": {"months": MONTHS[6:]}}]}])
        self.assertEqual(alive.check_months({"r": d}), [])

    def test_a4_double(self):
        d = doc(districts=[{"id": "x", "populations": [
            {"actor": "world.sheep", "density": "herd", "max_per_chunk": 2,
             "when": {"months": ["mar", "apr", "may"]}},
            {"actor": "world.sheep", "density": "herd", "max_per_chunk": 1,
             "when": {"months": ["may", "jun"]}}]}])
        out = alive.check_months({"r": d})
        self.assertTrue(any("both hold ['may']" in m for _l, _w, m in out))

    def test_a4_hole(self):
        d = doc(districts=[{"id": "x", "populations": [
            {"actor": "world.sheep", "max_per_chunk": 2, "when": {"months": ["mar", "apr"]}},
            {"actor": "world.sheep", "max_per_chunk": 1, "when": {"months": ["jul", "aug"]}}]}])
        out = alive.check_months({"r": d})
        self.assertTrue(any("hole" in m for _l, _w, m in out))

    def test_a4_one_season_run_is_no_hole(self):
        d = doc(districts=[{"id": "x", "populations": [
            {"actor": "world.stork", "max_per_chunk": 1, "when": {"months": ["dec", "jan"]}},
            {"actor": "world.stork", "max_per_chunk": 2, "when": {"months": ["feb", "mar"]}}]}])
        self.assertEqual(alive.check_months({"r": d}), [])

    def test_a4_bad_name(self):
        d = doc(lanes_tokens=[token(when={"months": ["march"]})])
        self.assertIn("not month names", alive.check_months({"r": d})[0][2])

    # A5, A6
    def test_a5_clean(self):
        self.assertEqual(alive.check_events({"r": doc()}), [])

    def test_a5_season_without_event(self):
        d = doc()
        d["events"] = [e for e in d["events"] if e["trigger"]["season"] != "winter"]
        d["events"].append({"id": "turn", "trigger": {"on": "season_turn", "season": "winter"}})
        out = alive.check_events({"r": d})
        self.assertEqual([w for _l, w, _m in out], ["r winter"])

    def test_a6_large_events_overlap(self):
        big = [{"id": f"big{i}", "size": "large", "duration": [60, 60],
                "trigger": {"on": "window", "hours": ["09:00", "09:30"]}} for i in (1, 2)]
        out = alive.check_events({"r": doc(events=doc()["events"] + big)})
        self.assertTrue(any("two large events" in m for _l, _w, m in out))

    # A1, A2
    def test_a1_daytime_block_without_life(self):
        cell = {"people": 1.0, "animals": 0.0, "birds": 0.0, "n": 1}
        empty = {"people": 0.0, "animals": 0.0, "birds": 0.0, "n": 1}
        regions = {"r": {"morning": {"jun": cell, "jan": cell}, "midday": {"jun": cell,
                                                                            "jan": empty}}}
        out = alive.check_daytime(regions)
        self.assertEqual([w for _l, w, _m in out], ["r midday jan"])
        regions["r"]["midday"]["jan"] = cell
        self.assertEqual(alive.check_daytime(regions), [])

    def test_a2_window_over_the_cap(self):
        chunks = np.zeros((10, 10), np.float32)
        chunks[2:4, 2:4] = 300.0
        v, at = alive.window_max(chunks, 3)
        self.assertEqual((v, at), (1200.0, (1, 1)))
        ok = {"1x": {"all": (1200.0, at, "jun 10:00 (reaches a city)"), "lanes": (500.0, at, "x"),
                     "chunks": 3}}
        self.assertEqual([lv for lv, _w, _m in alive.check_windows(ok)], ["warning"])
        ok["1x"]["lanes"] = (1200.0, at, "jun 10:00")
        self.assertIn("error", [lv for lv, _w, _m in alive.check_windows(ok)])
        far = {"quarter": dict(ok["1x"], chunks=13)}
        self.assertNotIn("error", [lv for lv, _w, _m in alive.check_windows(far)])


if __name__ == "__main__":
    unittest.main()
