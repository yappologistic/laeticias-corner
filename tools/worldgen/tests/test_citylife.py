"""City life checks (worldgen.citylife, worldgen.lifesim): a clean region document passes, and each
check trips on a deliberate error. The region is a tiny synthetic view, never committed data."""

import copy
import unittest

from worldgen import citylife as CL
from worldgen import lifesim
from worldgen.citylife import Instance, RegionView, card, curve, go, pop, role, sched, use, wander

WORK = curve({0: 0, 6: 1, 18: 0})


def view() -> RegionView:
    """A square of one chunk with a shop and two benches on a three-node street."""
    shop = Instance("t.shop", "square", 4, 4, 2, 2, {"sell": [(6, 5)], "beside": [(6, 5)]},
                    {"sell": "a", "beside": "a"})
    benches = [Instance("t.bench", "square", 20, 4, 1, 1, {"seat": [(20, 5)], "beside": [(21, 4)]},
                        {"seat": "c", "beside": "c"}),
               Instance("t.bench", "square", 22, 4, 1, 1, {"seat": [(22, 5)], "beside": [(23, 4)]},
                        {"seat": None, "beside": None})]
    return RegionView(
        region="parsa", kinds={"t.walker": {"idle", "move", "carry", "work_high"},
                               "t.cart": {"idle", "move"}},
        goods={"t.goods_a"}, audio={"sfx/t.wav"},
        slots={"t.shop": {"sell": {"kind": "work", "cap": 1}},
               "t.bench": {"seat": {"kind": "sit", "cap": 1}}},
        instances=[shop] + benches,
        nodes={"a": (6, 6, "dest"), "b": (13, 6, None), "c": (20, 6, "dest")},
        adj={"a": [("b", 7)], "b": [("a", 7), ("c", 7)], "c": [("b", 7)]},
        ports=set(),
        districts={"square": {"tiles": 1024, "walk": 900, "chunks": {(0, 0): 1024},
                              "bbox": (0, 0, 31, 31)}},
        landmarks=["t.shop"])


def doc() -> dict:
    """A region where people stroll, a seller keeps the shop and goods go from it to a bench."""
    return {
        "id": "parsa", "season": "spring", "densities": {"work": WORK},
        "districts": [{"id": "square", "area": "town", "populations": [
            pop("stroller", "work", 48), CL.per("seller", "t.shop", 1, "work")]}],
        "roles": [
            role("stroller", "t.walker", "Stroller", sched(("06:00", "18:00", "walk")),
                 {"walk": {"loop": True, "steps": [go(node="a"), wander(radius=4, dur=(20, 30)),
                                                   go(node="c"), use(anim="idle", dur=(10, 20))]}}),
            role("seller", "t.walker", "Seller", sched(("06:00", "18:00", "sell")),
                 {"sell": {"loop": True, "steps": [go(home="sell"),
                                                   use({"home": "sell"}, anim="work_high", dur=(30, 40))]}},
                 home={"item": "t.shop", "slot": "sell"}),
            role("carter", "t.cart", "Cart", sched(("06:00", "18:00", "haul")),
                 {"haul": {"loop": True, "steps": [go(node="a"), go(node="c")]}})],
        "chains": [{"id": "goods", "period": 60, "hours": ["06:00", "18:00"], "stages": [
            {"slot": "t.shop.sell", "makes": "t.goods_a", "by": "seller"},
            {"carry": "t.goods_a", "from": "t.shop.sell", "to": "t.bench.seat", "by": "carter"},
            {"slot": "t.bench.seat", "sink": "t.goods_a", "by": "stroller"}]}],
        "events": [{"id": "parade", "trigger": {"on": "window", "hours": ["08:00", "09:00"]},
                    "duration": [30, 30], "route": ["a", "b", "c"], "sfx": "sfx/t.wav"}],
        "cards": {"shop": card("landmark", "The shop", "A shop on the square",
                               "A small shop on the square where the seller keeps her goods and the "
                               "strollers stop to talk on their way to the benches.")},
    }


def errors(d, v=None, code=None):
    out = [p for p in CL.check(d, v or view()) if p.level == "error"]
    return [p for p in out if code is None or p.code == code]


class Clean(unittest.TestCase):
    def test_clean_document_passes(self):
        self.assertEqual([p.text() for p in errors(doc())], [])


class Checks(unittest.TestCase):
    def test_l1_unknown_kind_animation_goods_audio(self):
        d = doc()
        d["roles"][0]["actor"] = "t.ghost"
        d["roles"][1]["routines"]["sell"]["steps"][1]["anim"] = "dance"
        d["chains"][0]["stages"][0]["makes"] = "t.goods_missing"
        d["events"][0]["sfx"] = "sfx/none.wav"
        text = " ".join(p.message for p in errors(d, code="L1"))
        for word in ("t.ghost", "dance", "t.goods_missing", "sfx/none.wav"):
            self.assertIn(word, text)

    def test_l1_pending_goods_need_a_real_stand_in(self):
        d = doc()
        d["chains"][0]["stages"][0]["makes"] = "t.goods_new"
        d["pending"] = {"goods": {"t.goods_new": "t.goods_also_missing"}}
        self.assertTrue(any("stand-in" in p.message for p in errors(d, code="L1")))
        d["pending"]["goods"]["t.goods_new"] = "t.goods_a"
        self.assertFalse(any("t.goods_new" in p.message for p in errors(d, code="L1")))

    def test_l2_slot_out_of_reach(self):
        d = doc()
        d["roles"][0]["routines"]["walk"]["steps"].append(go(item="t.bench", slot="seat"))
        v = view()
        for b in v.instances[1:]:
            b.nodes["seat"] = None
        self.assertTrue(errors(d, v, "L2"))

    def test_l3_more_people_than_places(self):
        d = doc()
        d["districts"][0]["populations"][1]["count"] = 3
        self.assertTrue(any("t.shop.sell" in p.message for p in errors(d, code="L3")))

    def test_l4_broken_and_starved_chains(self):
        d = doc()
        d["chains"][0]["stages"][1]["from"] = "t.bench.seat"
        self.assertTrue(any("broken" in p.message for p in errors(d, code="L4")))
        d = doc()
        d["chains"][0]["stages"].pop()
        self.assertTrue(any("sink" in p.message for p in errors(d, code="L4")))
        d = doc()
        d["chains"][0]["period"] = 5000
        self.assertTrue(any("nothing reached" in p.message for p in errors(d, code="L4")))

    def test_l5_crowded_and_empty(self):
        d = doc()
        d["districts"][0]["populations"][0]["max_per_chunk"] = 400
        self.assertTrue(any("per chunk" in p.message for p in errors(d, code="L5")))
        d["districts"][0]["populations"][0]["max_per_chunk"] = 4
        self.assertTrue(any("minimum" in p.message for p in errors(d, code="L5")))

    def test_l6_cards(self):
        d = doc()
        d["cards"]["shop"]["text"] = "Too short."
        self.assertTrue(errors(d, code="L6"))
        d = doc()
        del d["cards"]["shop"]
        self.assertTrue(any("t.shop" in p.where for p in errors(d, code="L6")))

    def test_l7_retired_names_spelling_british(self):
        d = doc()
        d["cards"]["shop"]["text"] += " Baradkama paid for the color of the Apadana."
        msgs = " ".join(p.message for p in errors(d, code="L7"))
        for word in ("Baradkama", "Apadāna", "colour"):
            self.assertIn(word, msgs)

    def test_l7_rome_fact_check_wording(self):
        d = doc()
        d["id"] = "rome"
        d["cards"]["shop"]["text"] += " Hadrian renamed by Hadrian the Romaea; Marcus, aged five."
        msgs = " ".join(p.message for p in errors(d, code="L7"))
        for word in ("renamed by Hadrian", "aged five", "Romaia"):
            self.assertIn(word, msgs)

    def test_l2_mooring_spot_is_worked_from_beside_its_post(self):
        # The boat's spot is water; only the tile beside the post is on the graph's labels.
        post = Instance("t.quay", "square", 10, 10, 1, 1,
                        {"mooring": [(9, 10)], "beside": [(11, 10), (10, 11)]})
        lab = {(11, 10): "b"}
        self.assertIsNone(CL._node_for(post.spots["mooring"], lab, None, post))
        self.assertEqual(CL._node_for(post.spots["mooring"], lab, None, post, post=True), "b")

    def test_l8_events_share_a_route(self):
        d = doc()
        e = copy.deepcopy(d["events"][0])
        e["id"] = "second_parade"
        e["trigger"]["hours"] = ["08:30", "09:00"]
        d["events"].append(e)
        self.assertTrue(errors(d, code="L8"))
        e["trigger"]["hours"] = ["14:00", "15:00"]
        self.assertFalse(errors(d, code="L8"))


class Simulator(unittest.TestCase):
    def test_counters_stay_in_range_and_units_are_kept(self):
        d = doc()
        res = lifesim.simulate(d["chains"][0], view(), CL.roles_by_id(d))
        self.assertEqual(res["errors"], [])
        self.assertTrue(all(n >= 1 for n in res["per_day"][1:]))

    def test_more_carriers_move_more(self):
        d = doc()
        c = d["chains"][0]
        c["period"] = 10
        one = sum(lifesim.simulate(c, view(), CL.roles_by_id(d))["per_day"])
        c["stages"][1]["workers"] = 3
        three = sum(lifesim.simulate(c, view(), CL.roles_by_id(d))["per_day"])
        self.assertGreater(three, one)

    def test_deterministic(self):
        d = doc()
        a = lifesim.simulate(d["chains"][0], view(), CL.roles_by_id(d))
        b = lifesim.simulate(d["chains"][0], view(), CL.roles_by_id(d))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
