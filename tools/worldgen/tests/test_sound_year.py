"""The year in sound (`worldgen/soundplan.py`): every region has a bed in every month by day and
by night, no sea where the sea cannot be heard, festival and work loops tied to what exists,
every placed workplace that sounds names its loop. Each rule has a document that passes and one
that fails."""

import copy
import unittest

import numpy as np

from tests.helpers import ROOT
from worldgen import sound, soundplan as SP

FILES, FAMILIES = sound.manifests(ROOT)
W = "amb/world/"


def doc():
    return {"id": "olympia", "theme": {
        "ambience": {"beds": [{"file": "amb/athens/day.ogg", "hours": ["05:30", "19:30"]},
                              {"file": "amb/athens/night.ogg", "hours": ["19:30", "05:30"]}],
                     "zones": [{"rect": [10, 10, 20, 20], "file": "amb/athens/sea.ogg",
                                "gain": 0.8}],
                     "loops": [{"item": "athens.g_press", "file": W + "press.ogg",
                                "when": "worked", "hours": ["07:00", "17:00"],
                                "months": ["nov", "dec", "jan"]},
                               {"item": "athens.g_press", "file": W + "vintage.ogg",
                                "when": "worked", "hours": ["07:00", "17:00"],
                                "months": ["sep", "oct"]}]},
        "seasons": {"winter": {"ambience": {"beds": [
            {"file": "amb/athens/day_cool.ogg", "hours": ["05:30", "19:30"]}]}}}},
        "festivals": [{"id": "olympia"}],
        "districts": [{"id": "valley", "populations": [{"role": "reaper"}],
                       "sound": {"surfaces": {}, "water": {"family": "sea.coast"}}}],
        "roles": [{"id": "reaper", "sound": {"loop": W + "reaping.ogg"}}],
        "events": [{"id": "rural_dionysia", "trigger": {"on": "window", "months": ["dec"]},
                    "ambience": {"file": "amb/athens/komos.ogg"}},
                   {"id": "olympic_crowd", "trigger": {"on": "calendar", "festival": "olympia"},
                    "sfx": "sfx/athens/tympanon.wav"}]}


def facts(hears=True, items=("athens.g_press",)):
    near = np.zeros((448, 1280), dtype=bool)
    if hears:
        near[:, :] = True
    return {"hears_sea": hears, "districts": {"valley": hears}, "items": set(items),
            "near": near, "marsh": 0}


def errors(d, f=None):
    out = [m for lv, _w, m in SP.check(d) if lv == "error"]
    if f is not None:
        out += [m for lv, _w, m in SP.check_world(d, f) if lv == "error"]
    return out


class Beds(unittest.TestCase):
    def test_a_region_with_a_bed_every_hour_passes(self):
        self.assertEqual(errors(doc(), facts()), [])

    def test_a_night_without_a_bed_fails(self):
        d = doc()
        d["theme"]["ambience"]["beds"].pop(1)
        self.assertTrue(any("no bed plays" in m for m in errors(d)))

    def test_a_season_bed_replaces_the_plain_one_for_its_hours(self):
        d = doc()
        self.assertEqual(SP.beds_at(d, "winter", "jan", 12.0), ["amb/athens/day_cool.ogg"])
        self.assertEqual(SP.beds_at(d, "winter", "jan", 0.0), ["amb/athens/night.ogg"])
        self.assertEqual(SP.beds_at(d, "summer", "jul", 12.0), ["amb/athens/day.ogg"])

    def test_a_nature_bed_among_the_places_beds_fails(self):
        d = doc()
        d["theme"]["ambience"]["beds"][1]["file"] = W + "night_scrub.ogg"
        self.assertTrue(any("nature bed" in m for m in errors(d)))

    def test_every_bed_kind_covers_every_month_and_hour(self):
        for kind in sorted(set(SP.BED_KIND.values())):
            plain, seasons = SP.beds_for(kind, ["apr", "may"], True)
            d = {"theme": {"ambience": {"beds": plain},
                           "seasons": {s: {"ambience": {"beds": b}} for s, b in seasons.items()}}}
            self.assertEqual([m for m in errors(d) if "no bed" in m], [], kind)

    def test_every_named_file_is_in_a_manifest(self):
        named = set()
        for kind in set(SP.BED_KIND.values()):
            plain, seasons = SP.beds_for(kind, ["apr"], True)
            named |= {b["file"] for b in plain} | {b["file"] for v in seasons.values() for b in v}
        for c in ("mediterranean", "river_plain", "mountain", "east", "steppe"):
            named |= {f for ph in SP.nature_seasons(c).values() for f in ph.values() if f}
        for _p, f, *_ in SP.ITEM_LOOPS:
            named.add(f)
        for t in SP.TURN_SOUNDS.values():
            named |= {t.get("sfx") or t["ambience"]["file"]}
        named |= {c["file"] for c in SP.calls("latium_italy", "mediterranean", True, True, True)}
        self.assertEqual(sorted(named - FILES), [])

    def test_the_nature_beds_are_the_engines_expectations(self):
        n = SP.nature_seasons("mediterranean")
        self.assertEqual(n["spring"]["dawn"], W + "dawn_scrub.ogg")
        self.assertEqual(n["autumn"]["dawn"], W + "dawn_autumn.ogg")
        self.assertEqual(n["winter"]["night"], W + "night_cold.ogg")
        self.assertEqual(n["spring"]["day"], "")


class Sea(unittest.TestCase):
    def test_a_sea_bed_out_of_hearing_of_the_sea_fails(self):
        d = doc()
        d["theme"]["ambience"]["beds"][0]["file"] = W + "sea.ogg"
        self.assertTrue(any("sea bed" in m for m in errors(d, facts(hears=False))))

    def test_a_harbour_zone_out_of_hearing_fails(self):
        self.assertTrue(any("no sea within" in m for m in errors(doc(), facts(hears=False))))

    def test_a_shore_family_out_of_hearing_fails(self):
        d = doc()
        d["theme"]["ambience"]["zones"] = []
        self.assertTrue(any("sea.coast" in m for m in errors(d, facts(hears=False))))


class Festivals(unittest.TestCase):
    def test_festival_music_on_a_festival_the_region_does_not_hold_fails(self):
        d = doc()
        d["festivals"] = []
        self.assertTrue(any("does not hold" in m for m in errors(d)))

    def test_festival_music_on_an_event_that_never_runs_fails(self):
        d = doc()
        d["events"][0].pop("trigger")
        self.assertTrue(any("never play" in m for m in errors(d)))

    def test_a_festival_in_an_unknown_month_fails(self):
        d = doc()
        d["events"][0]["trigger"]["months"] = ["thermidor"]
        self.assertTrue(any("unknown month" in m for m in errors(d)))

    def test_the_festivals_get_their_instruments(self):
        e = {"id": "lupercalia", "sfx": "sfx/rome/tibia.wav"}
        for pat, fields in SP.FESTIVAL_SOUNDS:
            if __import__("re").search(pat, e["id"]):
                SP._force(e, fields)
                break
        self.assertEqual(e["sfx"], "sfx/rome/lituus.wav")
        self.assertEqual(e["sounds"], [{"file": "sfx/rome/tibia.wav", "at": "end"}])


class Work(unittest.TestCase):
    def test_a_worked_loop_without_hours_fails(self):
        d = doc()
        d["theme"]["ambience"]["loops"][0].pop("hours")
        self.assertTrue(any("working hours" in m for m in errors(d)))

    def test_a_placed_workplace_without_its_loop_fails(self):
        d = doc()
        d["theme"]["ambience"]["loops"].pop(1)
        self.assertTrue(any("vintage.ogg" in m and "no loop" in m for m in errors(d, facts())))

    def test_a_workplace_worked_by_a_role_with_the_loop_passes(self):
        d = doc()
        d["theme"]["ambience"]["loops"].pop(0)
        d["roles"].append({"id": "presser", "home": {"item": "athens.g_press"},
                           "sound": {"loop": W + "press.ogg"}})
        self.assertEqual(errors(d, facts()), [])

    def test_a_loop_on_an_item_the_region_does_not_hold_fails(self):
        self.assertTrue(any("does not hold" in m for m in errors(doc(), facts(items=()))))

    def test_a_seasonal_work_loop_on_a_role_no_district_holds_fails(self):
        d = copy.deepcopy(doc())
        d["districts"][0]["populations"] = []
        self.assertTrue(any("no district holds" in m for m in errors(d)))

    def test_a_threshing_floor_threshes_then_winnows(self):
        files = [f for f, *_ in SP.item_loops("parsa.p_threshing")]
        self.assertEqual(files, [W + "threshing.ogg", W + "winnowing.ogg"])
        self.assertEqual([f for f, *_ in SP.item_loops("rome.r_brazier")], [W + "brazier.ogg"])


if __name__ == "__main__":
    unittest.main()
