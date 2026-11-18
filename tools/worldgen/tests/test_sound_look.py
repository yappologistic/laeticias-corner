"""L9 sound, L10 look and L11 names: the region file checks added with the atmosphere audio and
the visual direction (docs/design/look.md §3.5). Each rule has a document that passes and one
that fails."""

import copy
import unittest

from tests.helpers import ROOT
from worldgen import look, places, sound

FILES, FAMILIES = sound.manifests(ROOT)


def doc():
    return {"id": "latium_italy", "name": "Latium", "caption": "Latium · April AD 126",
            "era": "The Rome of Hadrian · AD 126",
            "theme": {"sound": {"crowd": "crowd.latin", "wind": "wind.open"},
                      "ambience": {"beds": [{"file": "amb/world/fields.ogg"}]}},
            "districts": [{"id": "road", "name": "Via Appia",
                           "populations": [{"actor": "world.traveller", "density": "d"}],
                           "sound": {"surfaces": {"stone": 0.9}, "wind": "wind.street",
                                     "crowd": {"family": "crowd.latin", "full": 6}}}],
            "events": [{"id": "market_day", "ambience": {"file": "amb/world/crowd_latin_2.ogg"}}],
            "roles": [{"id": "baker", "routines": {"bake": {"steps": [{"use": {"here": True},
                                                                       "anim": "work_low"}]}},
                       "sound": {"loop": "amb/world/bakery.ogg"}}],
            "chains": []}


class Sound(unittest.TestCase):
    def errors(self, d):
        return [m for lv, w, m in sound.check(d, FILES, FAMILIES) if lv == "error"]

    def test_a_wired_region_passes(self):
        self.assertEqual(self.errors(doc()), [])

    def test_a_file_in_no_manifest_fails(self):
        d = doc()
        d["events"][0]["ambience"]["file"] = "amb/world/crowd_klingon_2.ogg"
        self.assertTrue(any("no audio manifest" in m for m in self.errors(d)))

    def test_an_unknown_family_fails(self):
        d = doc()
        d["districts"][0]["sound"]["wind"] = "wind.space"
        self.assertTrue(any("family" in m for m in self.errors(d)))

    def test_a_silent_event_fails(self):
        d = doc()
        d["events"][0].pop("ambience")
        self.assertTrue(any("silent" in m for m in self.errors(d)))

    def test_a_working_role_without_sound_fails(self):
        d = doc()
        d["roles"][0].pop("sound")
        self.assertTrue(any("works without a sound" in m for m in self.errors(d)))

    def test_a_populated_district_without_sound_fails(self):
        d = doc()
        d["districts"][0].pop("sound")
        self.assertTrue(any("populated" in m for m in self.errors(d)))


def with_look():
    d = doc()
    fam = copy.deepcopy(look.FAMILY["rome"])
    d["theme"]["look"] = {"phases": fam["phases"], "sky": fam["sky"], "sun": fam["sun"],
                          "shade": fam["shade"], "haze": fam["haze"] | {"by_zoom": {
                              "half": 0.15, "quarter": 0.22, "overview": 0.3}},
                          "stars": 0.5, "weather": {"spring": {"storm": 0.1, "fog": 0.2, "dust": 0}},
                          "lights": {"rome.r_lamp": {"kind": "lamp", "colour": "#ffc27a",
                                                     "radius": 2.5, "flicker": {"hz": [6, 9],
                                                                                "depth": 0.08}}},
                          "water": fam["water"]}
    return d


class Look(unittest.TestCase):
    def errors(self, d):
        return [m for lv, w, m in look.check(d) if lv == "error"]

    def test_a_complete_look_passes(self):
        self.assertEqual(self.errors(with_look()), [])

    def test_no_look_fails(self):
        self.assertTrue(self.errors(doc()))

    def test_exposure_out_of_range_fails(self):
        d = with_look()
        d["theme"]["look"]["phases"]["dusk"]["exposure"] = 3.0
        self.assertTrue(any("0.2..1.5" in m for m in self.errors(d)))

    def test_a_sky_needs_three_stops(self):
        d = with_look()
        d["theme"]["look"]["sky"]["night"] = ["#0d1330", "#20294d"]
        self.assertTrue(any("three stops" in m for m in self.errors(d)))

    def test_haze_must_rise_with_zoom_out(self):
        d = with_look()
        d["theme"]["look"]["haze"]["by_zoom"]["overview"] = 0.01
        self.assertTrue(any("rise" in m for m in self.errors(d)))

    def test_an_unknown_light_kind_fails(self):
        d = with_look()
        d["theme"]["look"]["lights"]["rome.r_lamp"]["kind"] = "neon"
        self.assertTrue(any("unknown kind" in m for m in self.errors(d)))


class Names(unittest.TestCase):
    def test_named_region_passes(self):
        self.assertEqual(places.check(doc()), [])

    def test_a_region_of_a_time_needs_its_era(self):
        d = doc()
        d.pop("era")
        self.assertTrue(any("era" in m for _, _, m in places.check(d)))

    def test_every_district_needs_a_name(self):
        d = doc()
        d["districts"][0].pop("name")
        self.assertTrue(any("needs a name" in m for _, _, m in places.check(d)))

    def test_apply_gives_stretches_specific_names(self):
        d = places.apply({"id": "anatolia", "name": "Anatolia", "caption": "Anatolia",
                          "districts": [{"id": "road"}]})
        self.assertEqual(d["caption"], "Anatolia · c. 470 BC")
        self.assertEqual(d["era"], "The Persian empire of Xerxes · c. 470 BC")
        self.assertEqual(d["districts"][0]["name"], "The Royal Road")


if __name__ == "__main__":
    unittest.main()
