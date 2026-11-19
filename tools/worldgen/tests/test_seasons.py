"""The seasons (worldgen.seasons, seasonlife, seasoncheck; docs/design/seasons.md): the calendar,
the catalog writer, the region helpers, and every check S1-S19 with a case that passes and a
deliberate fault that is reported by name. Fixtures are small and built here, never committed
data (the climates are the tool's own table)."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tests.helpers import ROOT
from worldgen import citylife as CL
from worldgen import climates as C
from worldgen import seasoncheck as SC
from worldgen import seasonlife as SL
from worldgen import seasons as S
from worldgen.compose import World
from worldgen.coords import COLS, ROWS, to_grid

RAW = {c["id"]: c for c in C.CLIMATES}
CLIMS = {cid: S.resolve(RAW, cid) for cid in RAW}


def codes(rep: SC.Report, level="error") -> list[str]:
    return [c for c, lv, _w, _m in rep.items if lv == level]


class Calendar(unittest.TestCase):
    def test_one_day_is_one_month(self):
        self.assertEqual([S.month_of(d) for d in (0, 1, 3, 9, 11, 12)],
                         ["mar", "apr", "jun", "dec", "feb", "mar"])
        self.assertEqual([S.season_of(d) for d in (0, 2, 3, 8, 9, 11)],
                         ["spring", "spring", "summer", "autumn", "winter", "winter"])
        self.assertEqual(S.day_of("summer", 2), 4)   # the Panathenaia: July
        self.assertEqual(S.day_of("spring", 2), 1)   # the Parilia: April

    def test_months_spans_wrap_the_year(self):
        self.assertEqual(C.months("nov-feb"), ["nov", "dec", "jan", "feb"])
        self.assertEqual(C.by_month({"dec-feb": 0.5}, 1.0)[9:], [0.5, 0.5, 0.5])

    def test_festivals_by_season_day_or_months(self):
        olive = {"id": "olive_harvest", "months": ["nov", "dec", "jan"]}
        dion = {"id": "city_dionysia", "season": "spring", "day": 2}
        self.assertEqual([d for d in range(12) if CL.festival_on(olive, d)], [8, 9, 10])
        self.assertEqual([d for d in range(12) if CL.festival_on(dion, d)], [1])

    def test_chain_pace_by_month(self):
        c = {"months": ["apr", "may"], "by_month": [1, 0.5] + [1] * 10}
        self.assertEqual([CL.chain_factor(c, d) for d in range(3)], [0.0, 0.5, 1.0])


class Climates(unittest.TestCase):
    def test_inheritance_fills_what_a_climate_leaves_out(self):
        lev = CLIMS["levant"]
        self.assertEqual(lev["classes"]["grass"], CLIMS["med_dry"]["classes"]["grass"])
        self.assertEqual(lev["snow"]["line"][9], 10)           # its own
        self.assertIn("sea", CLIMS["sea_aegean"])
        self.assertEqual(CLIMS["plateau"]["fauna"]["storks"][0], "apr")

    def test_the_tools_table_is_complete(self):
        rep = SC.Report()
        SC.check_climates(RAW, {"med_dry": {"grass", "crop"}}, rep)
        self.assertEqual(rep.errors, [])

    def test_a_short_row_a_lost_parent_and_a_stray_sea_are_reported(self):
        raw = copy.deepcopy(RAW)
        raw["med_dry"]["classes"]["grass"] = raw["med_dry"]["classes"]["grass"][:11]
        raw["thracian"]["inherits"] = "nowhere"
        raw["fars"]["sea"] = {"state": [1] * 12, "sailing": [1] * 12}
        raw["anatolian"]["turn_events"] = dict(raw["anatolian"]["turn_events"], winter="dragons")
        rep = SC.Report()
        SC.check_climates(raw, {}, rep)
        text = " ".join(m for *_x, m in rep.errors)
        self.assertIn("twelve states", text)
        self.assertIn("not a climate", text)
        self.assertIn("sea block", text)
        self.assertIn("dragons", text)

    def test_snow_never_on_the_plains(self):
        rep = SC.Report()
        SC.check_snow(RAW, CLIMS, ROOT, rep)
        self.assertNotIn("S8", codes(rep))
        clims = copy.deepcopy(CLIMS)
        clims["mesopotamian"]["snow"]["line"][10] = 3
        clims["anatolian"]["snow"]["lowland"] = {"months": ["jan"], "chance": 0.5}   # its own snow
        rep = SC.Report()
        SC.check_snow(RAW, clims, ROOT, rep)
        self.assertEqual(codes(rep).count("S8"), 2)


class States(unittest.TestCase):
    def test_every_state_an_item_shows_is_listed(self):
        e = {"id": "rome.t_plane", **S.season_fields("rome", "rome.t_plane", C.SEASON_ITEMS["rome"]["rome.t_plane"],
                                                     {"med_green", "highland"}, CLIMS)}
        rep = SC.Report()
        SC.states_problems("rome", e, {"med_green", "highland"}, CLIMS, rep)
        self.assertEqual(rep.errors, [])
        e["season_states"] = [s for s in e["season_states"] if s != "bare"]
        SC.states_problems("rome", e, {"med_green"}, CLIMS, rep)
        self.assertEqual(codes(rep), ["S4"])

    def test_bloom_and_fruit_months_win(self):
        spec = C.SEASON_ITEMS["athens"]["athens.t_oleander"]
        st = S.item_states(CLIMS["med_dry"], spec)
        self.assertEqual(st[3:7], ["bloom"] * 4)              # June to September
        self.assertEqual(st[0], "green")

    def test_the_home_climate_keeps_its_season_names_for_home_pieces(self):
        home = CLIMS["home"]
        self.assertEqual(S.class_row(home, "deciduous", False)[10], "winter")
        self.assertEqual(S.class_row(home, "deciduous", True)[10], "bare")


class CatalogWriter(unittest.TestCase):
    LINE = ('{\n "version": 1,\n "set": "rome",\n "terrain": [\n'
            '  {"id": "rome.grass_spring", "name": "Spring grass", "base": true},\n'
            '  {"id": "rome.mud_bank", "name": "Mud bank"}\n ],\n "items": [\n'
            '  {"id": "rome.t_plane", "name": "Plane", "footprint": [1, 1]},\n'
            '  {"id": "rome.r_brazier", "name": "Brazier"}\n ],\n "art": {"pages": 1}\n}\n')

    def test_one_entry_per_line_stays_one_entry_per_line(self):
        out = S.set_catalog_text(self.LINE, "rome", {"rome.t_plane": {"med_green"}},
                                 {"rome.grass_spring": {"med_green"}}, CLIMS)
        lines = out.split("\n")
        self.assertEqual(len(lines), len(self.LINE.split("\n")))
        self.assertIn('{"id": "rome.mud_bank", "name": "Mud bank"}', out)   # untouched
        plane = json.loads(next(x for x in lines if "t_plane" in x).strip().rstrip(","))
        self.assertEqual(plane["season_class"], "deciduous")
        self.assertEqual(plane["season_states"], ["fresh", "turn", "bare"])
        self.assertIn('"snow_catch": false', out)
        self.assertEqual(S.set_catalog_text(out, "rome", {"rome.t_plane": {"med_green"}},
                                            {"rome.grass_spring": {"med_green"}}, CLIMS), out)

    def test_the_main_catalog_gains_its_calendar_once(self):
        text = (ROOT / "assets/catalog.json").read_text()
        once = S.main_catalog_text(text)
        self.assertEqual(S.main_catalog_text(once), once)
        doc = json.loads(once)
        self.assertEqual(len(doc["climates"]), 15)
        self.assertEqual(doc["calendar"]["months"][1]["name"], "April")
        self.assertEqual(doc["seasons"], json.loads(text)["seasons"])


class Helpers(unittest.TestCase):
    def test_monthly_splits_by_factor_and_curve(self):
        e = {"role": "shopper", "density": "market", "max_per_chunk": 10}
        out = SL.monthly(e, SL.factors(1.0, dec_feb=0.5), {"jul": "market_hot"})
        self.assertEqual(len(out), 3)
        winter = next(x for x in out if x["max_per_chunk"] == 5)
        self.assertEqual(winter["when"]["months"], ["dec", "jan", "feb"])
        self.assertEqual(next(x for x in out if x["density"] == "market_hot")["when"]["months"], ["jul"])
        self.assertEqual(SL.monthly(e), [e])                   # the same all year: no filter

    def test_months_off_drop_out(self):
        out = SL.monthly({"role": "swallow", "max_per_chunk": 4}, SL.factors(0.0, mar_sep=1.0))
        self.assertEqual(out[0]["when"]["months"], C.MONTHS[:7])


# -- region files ------------------------------------------------------------------------------

def region() -> dict:
    """A small town file with everything a year needs."""
    return {
        "id": "eleusis", "name": "Eleusis", "caption": "Eleusis · 432 BC", "climate": "med_dry",
        "era": {"edge": "The Athens of Pericles · 432 BC", "caption": "Eleusis · {year}",
                "year": {s: "432 BC" for s in C.SEASONS}},
        "moment": {"season": "autumn", "day": 1, "festival": "mysteries", "calendar_day": 6},
        "theme": {"weather": {s: {"showers": 1} for s in C.SEASONS},
                  "seasons": {s: {"grade": [1, 1, 1], "ground": {}} for s in C.SEASONS}},
        "festivals": [{"id": "mysteries", "season": "autumn", "day": 1},
                      {"id": "olive_harvest", "months": ["nov", "dec", "jan"]}],
        "districts": [{"id": "town", "populations": [
            {"actor": "athens.farmer", "variants": {"cold": "climate", "hot": "climate"}},
            {"actor": "world.swift", "when": {"months": ["apr", "may"]}},
            {"role": "picker", "when": {"months": ["nov", "dec"]}}]}],
        "roles": [{"id": "picker", "actor": "athens.farmer", "routines": {"work": {"steps": [
            {"go": {"item": "athens.t_olive", "spot": "beside"}}, {"use": {"here": True}, "anim": "work_low"}]}}}],
        "groups": [{"id": "herd", "seasonal": {"summer": "eleusis/town", "winter": "eleusis/town",
                                               "move": ["may", "oct"],
                                               "route": {"start": "base:a", "end": "base:c"}}}],
        "events": [{"id": "olive_harvest_day", "trigger": {"on": "calendar", "festival": "olive_harvest"}},
                   {"id": "swifts", "trigger": {"on": "window", "months": ["apr", "may"]}}],
        "lanes_tokens": [{"actor": "athens.merchant", "lane": "x:y", "by_month": "sailing"},
                         {"actor": "world.traveller", "by_month": [1] * 12}],
        "water": [{"body": "ilissos", "level": ["high"] * 12}],
    }


class Graph:
    class E:
        def __init__(self, a, b):
            self.a, self.b = a, b

    def __init__(self, pairs):
        self.edges = [self.E(a, b) for a, b in pairs]


GRAPHS = {"base": Graph([("a", "b"), ("b", "c")])}
KINDS = {"athens.farmer": {"idle", "move", "work_low"}, "world.swift": {"move"}}


def check(d, needs_audio=frozenset(), files=frozenset()) -> SC.Report:
    rep = SC.Report()
    SC.check_region(d, CLIMS, RAW, set(files), set(needs_audio), {"eleusis/town"}, GRAPHS,
                    {"athens.t_olive": {"eleusis"}}, KINDS, rep)
    return rep


class Regions(unittest.TestCase):
    def test_a_complete_region_passes(self):
        self.assertEqual(check(region()).errors, [])

    def test_s1_s2_climate_named_and_no_pin(self):
        d = region()
        d["climate"] = "tundra"
        self.assertEqual(codes(check(d)), ["S1"])
        d = region()
        d["climate"] = "med_green"
        self.assertIn("S1", codes(check(d)))                   # not the plan's
        d = region()
        d["season"] = "summer"
        d["theme"]["climate"] = "athens"
        self.assertEqual(codes(check(d)), ["S2", "S2"])

    def test_s5_moment_on_its_festival(self):
        d = region()
        d["moment"]["day"] = 2
        self.assertIn("S5", codes(check(d)))

    def test_s6_festivals_and_events_that_can_happen(self):
        d = region()
        d["festivals"].append({"id": "x", "season": "spring", "day": 2, "months": ["may"]})
        d["events"].append({"id": "never", "trigger": {"on": "window", "months": ["jan"],
                                                        "season": ["summer"]}})
        self.assertEqual(codes(check(d)).count("S6"), 2)

    def test_s9_herds_on_a_joined_drove_road(self):
        d = region()
        d["groups"][0]["seasonal"]["route"]["end"] = "base:zz"
        d["groups"][0]["seasonal"]["winter"] = "nowhere/land"
        self.assertEqual(codes(check(d)).count("S9"), 2)

    def test_s10_tokens_name_a_row_the_climate_has(self):
        d = region()
        d["lanes_tokens"][0]["by_month"] = "monsoon"
        d["lanes_tokens"][1]["by_month"] = [1] * 11
        self.assertEqual(codes(check(d)).count("S10"), 2)

    def test_s11_dress_only_on_kinds_that_change_it(self):
        d = region()
        d["districts"][0]["populations"].append({"actor": "world.stork", "variants": {"cold": "climate"}})
        self.assertIn("S11", codes(check(d)))

    def test_s12_beds_recorded_or_on_the_needs_list(self):
        d = region()
        d["theme"]["seasons"]["winter"]["ambience"] = {"beds": [{"file": "amb/athens/night_winter.ogg"}]}
        self.assertIn("S12", codes(check(d)))
        self.assertNotIn("S12", codes(check(d, needs_audio={"amb/athens/night_winter.ogg"})))

    def test_s13_captions_name_no_season(self):
        d = region()
        d["caption"] = "Eleusis · summer, 432 BC"
        d["era"]["caption"] = "Eleusis"
        self.assertEqual(codes(check(d)).count("S13"), 2)

    def test_s15_the_whole_year(self):
        d = region()
        del d["theme"]["weather"]["winter"]
        d["water"][0]["level"] = ["high"] * 11
        self.assertEqual(codes(check(d)).count("S15"), 2)

    def test_s16_seasonal_roles_target_what_is_placed(self):
        d = region()
        d["roles"][0]["routines"]["work"]["steps"][0]["go"]["item"] = "athens.t_vine"
        d["roles"][0]["routines"]["work"]["steps"][1]["anim"] = "dance"
        self.assertEqual(codes(check(d)).count("S16"), 2)

    def test_s17_nothing_out_of_its_season(self):
        d = region()
        d["districts"][0]["populations"][1]["when"]["months"] = ["jan"]      # swifts in January
        d["events"][1]["trigger"]["months"] = ["dec"]                          # swifts in December
        d["events"].append({"id": "winter_flurry", "trigger": {"on": "window", "months": ["jul"]}})
        d["festivals"][1]["months"] = ["jun"]                                  # olives in June
        self.assertEqual(codes(check(d)).count("S17"), 4)


# -- the map and the flood -------------------------------------------------------------------------

def tiny_world(regions: tuple[str, str], terrains=("world.alluvium", "world.river")) -> World:
    """Two regions side by side (west and east), a river along the west one's middle row."""
    w = World(terrains=list(terrains), districts=[f"{regions[0]}/land", f"{regions[1]}/land"])
    w.T = np.zeros((ROWS, COLS), dtype=np.uint16)
    w.L = np.zeros((ROWS, COLS), dtype=np.uint8)
    w.D = np.zeros((ROWS, COLS), dtype=np.uint16)
    w.D[:, 20:] = 1
    w.T[10, 0:20] = 1
    w.occ = np.full((ROWS, COLS), -1, dtype=np.int32)
    return w


class Map(unittest.TestCase):
    def test_s14_neighbours_that_may_meet(self):
        rep = SC.Report()
        SC.check_map(tiny_world(("rome", "latium_italy")), rep)
        self.assertNotIn("S14", codes(rep))
        rep = SC.Report()
        SC.check_map(tiny_world(("rome", "babylon")), rep)      # green Latium beside Babylon
        self.assertIn("S14", codes(rep))

    def test_s7_flood_ranks_and_rank_one_tiles(self):
        w = tiny_world(("babylon", "susa"))
        bodies = S.water_bodies(w)
        self.assertEqual([(b["region"], b["kind"]) for b in bodies], [("babylon", "river")])
        flood = S.flood_ranks(w, bodies, CLIMS)
        self.assertTrue(any(t[2] == 1 for t in flood[0]["tiles"]))
        name = bodies[0]["name"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "assets/world").mkdir(parents=True)
            (root / "assets/world/seasons.json").write_text(json.dumps({"flood": flood}))
            regions = {"babylon": {"water": [{"body": name, "level": ["flood"] * 12}]}}
            rep = SC.Report()
            SC.check_flood(root, w, bodies, CLIMS, regions, rep)
            self.assertEqual(rep.errors, [])
            bad = copy.deepcopy(flood)
            x, y = to_grid(30, 5)                          # far from the river, in Susa
            bad[0]["tiles"].append([x, y, 2])
            bad[0]["tiles"] = [t for t in bad[0]["tiles"] if t[2] != 1] + [bad[0]["tiles"][-1]]
            (root / "assets/world/seasons.json").write_text(json.dumps({"flood": bad}))
            rep = SC.Report()
            SC.check_flood(root, w, bodies, CLIMS, regions, rep)
            self.assertEqual(codes(rep).count("S7"), 2)


class SnowGround(unittest.TestCase):
    """S18, S19 and the base rule they hold: snow as terrain only where the climate keeps it all
    year, and snow rows that agree with the climates' own months."""

    YEAR_ROUND = {"snow": {"line": [12, 13, 14, 14, 14, 14, 14, 14, 13, 12, 11, 11]}}

    def test_lasting_snow_is_the_highest_line_of_a_year_without_a_gap(self):
        self.assertEqual(S.lasting_snow(self.YEAR_ROUND), 14)
        self.assertIsNone(S.lasting_snow(CLIMS["high_mountain"]))   # bare in high summer
        self.assertIsNone(S.lasting_snow(CLIMS["mesopotamian"]))

    def test_s18_snow_below_the_lasting_line_or_in_a_summer_climate(self):
        clims = dict(CLIMS, high_mountain=self.YEAR_ROUND)
        w = tiny_world(("zagros", "apennines"), terrains=("world.steppe", "world.snow"))
        w.T[10, 0:20] = 0
        w.T[3, 2:6] = 1
        w.L[3, 2:6] = 14                                  # a lasting cap at 14
        rep = SC.Report()
        SC.check_snow_ground(w, clims, rep)
        self.assertEqual(rep.errors, [])
        w.L[3, 5] = 12                                    # a snowfield in July at 12
        w.T[4, 30:33] = 1
        w.L[4, 30:33] = 15                                # the Apennines lose all snow by June
        rep = SC.Report()
        SC.check_snow_ground(w, clims, rep)
        self.assertEqual(codes(rep).count("S18"), 2)
        self.assertIn("first at grid (3, 1274) level 12", " ".join(m for *_x, m in rep.errors))

    def test_s19_the_tools_rows_make_sense(self):
        w = tiny_world(("parsa", "susa"), terrains=("parsa.plain_grass", "world.river"))
        w.L[:, :] = 4
        rep = SC.Report()
        SC.check_snow_sense(w, CLIMS, rep)
        self.assertEqual(rep.errors, [])

    def test_s19_lowland_snow_in_a_mild_month_and_summer_snow(self):
        clims = copy.deepcopy(CLIMS)
        clims["fars"]["snow"]["line"][0] = 4        # Pārsa's plain white in March (10 C)
        clims["fars"]["snow"]["line"][4] = 9        # and in July at level 9
        w = tiny_world(("parsa", "susa"), terrains=("parsa.plain_grass", "world.river"))
        rep = SC.Report()
        SC.check_snow_sense(w, clims, rep)
        text = " ".join(m for *_x, m in rep.errors)
        self.assertIn("snow lies on its lowland (level 4) in mar", text)
        self.assertIn("snow down to level 9 in jul", text)

    def test_s19_a_palm_under_snow(self):
        from worldgen.compose import WItem
        w = tiny_world(("parsa", "susa"), terrains=("parsa.plain_grass", "world.river"))
        w.L[5, 3] = 12                                  # Kuh-e Rahmat's flank, white in January
        w.items.append(WItem("parsa.t_date", 3, 5, 1, 1, 0, "parsa"))
        w.occ[5, 3] = 0
        rep = SC.Report()
        SC.check_snow_sense(w, CLIMS, rep)
        self.assertIn("parsa.t_date", " ".join(m for *_x, m in rep.errors))


class CityLifeByMonth(unittest.TestCase):
    """The cities' life checks run every month: a chain whose worker is away in a month it runs,
    and a district with a quieter character in some months."""

    def test_a_chain_without_its_worker_in_a_month_is_reported(self):
        from tests.test_citylife import doc, view
        d = doc()
        for p in d["districts"][0]["populations"]:
            if p.get("role") == "seller":
                p["when"] = {"months": ["mar", "apr", "may"]}
        self.assertTrue(any(p.code == "L4" and "jun" in p.message for p in CL.check(d, view())))
        d["chains"][0]["months"] = ["mar", "apr", "may"]
        self.assertFalse(any(p.code == "L4" and "is not out" in p.message for p in CL.check(d, view())))

    def test_a_quiet_season_holds_a_district_to_a_lesser_area(self):
        from tests.test_citylife import doc, view
        d = doc()
        d["districts"][0]["area"] = "centre"
        d["districts"][0]["populations"][0]["max_per_chunk"] = 4
        busy = [p for p in CL.check(d, view()) if p.code == "L5" and "busy hour" in p.message]
        d["districts"][0]["seasonal_area"] = {"area": "wild", "months": C.MONTHS}
        quiet = [p for p in CL.check(d, view()) if p.code == "L5" and "busy hour" in p.message]
        self.assertTrue(busy)
        self.assertFalse(quiet)


if __name__ == "__main__":
    unittest.main()
