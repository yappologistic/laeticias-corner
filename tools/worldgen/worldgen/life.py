"""Region files for the connective world (world-tech §2.6; living-world §2-§6; docs/design/sets/
world.md §10): the stretches, seas and seams the base layer holds, and the waypoint towns.

Each file gives the theme (grading by moment, haze, climate, ambience beds by stretch), the
populations of the districts the layers write (`road`, `farm`, `pasture`, `land`, `sea` in the
base; the towns' own), flocks with their pastures, fishing grounds, the tokens on lanes and long
routes (fishing boats, merchant ships, river boats, couriers, caravans, mule trains), the road's
events (the courier relay, caravans at dusk, beacons lit), and the towns' cards and strings.
Everything is derived from the plan and the built layers and graphs, so it stays in step with
them; `build.sh --life` rewrites the files this lane owns (never a city's).

Rects in these files are grid [x0, y0, x1, y1] inclusive, as world-tech §2.6 says.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from plan import world_plan as P

from .compose import NONE16, World
from .coords import COLS, ROWS, to_grid, to_plan
from .graph import Graph

TOWNS = ["alban_mount", "brundisium", "tibur", "capua", "beneventum", "eleusis", "academy", "corcyra",
         "delphi", "olympia", "sparta", "corinth", "delos", "ephesus", "sardis", "halys", "gordion",
         "euphrates_crossing", "sidon", "babylon", "susa", "persian_gates", "pasargadae"]

GRADING = {
    "rome": {"dawn": [0.96, 0.86, 0.80], "day": [1.0, 0.98, 0.94], "dusk": [0.98, 0.80, 0.66],
             "night": [0.44, 0.50, 0.68]},
    "athens": {"dawn": [0.98, 0.86, 0.80], "day": [1.0, 0.99, 0.95], "dusk": [0.98, 0.80, 0.68],
               "night": [0.44, 0.50, 0.70]},
    "parsa": {"dawn": [0.92, 0.84, 0.80], "day": [1.0, 0.98, 0.94], "dusk": [0.95, 0.78, 0.66],
              "night": [0.42, 0.48, 0.66]},
    "none": {"dawn": [0.96, 0.92, 0.86], "day": [1.0, 1.0, 0.98], "dusk": [0.96, 0.86, 0.76],
             "night": [0.46, 0.50, 0.66]},
}
HAZE = {"rome": [0.90, 0.88, 0.80], "athens": [0.93, 0.89, 0.80], "parsa": [0.86, 0.82, 0.74],
        "none": [0.92, 0.90, 0.84]}

# Ambience beds by stretch (docs/design/sets/world.md §10.3).
BEDS = {
    "sea": ("amb/world/sea.ogg", "amb/world/sea.ogg"),
    "fields": ("amb/world/fields.ogg", "amb/world/desert_night.ogg"),
    "mountain": ("amb/world/mountain.ogg", "amb/world/mountain.ogg"),
    "road": ("amb/world/road.ogg", "amb/world/desert_night.ogg"),
    "river": ("amb/world/river.ogg", "amb/world/river.ogg"),
    "seam": ("amb/world/seam.ogg", "amb/world/seam.ogg"),
}
STRETCH_BED = {
    "latium_italy": "fields", "greece": "fields", "attica_north": "fields", "thrace": "fields",
    "iran_plateau": "fields", "apennines": "mountain", "arcadia": "mountain", "taurus": "mountain",
    "zagros": "mountain", "anatolia": "road", "syrian_steppe": "road", "east_med": "fields",
    "ionia_lydia": "river", "mesopotamia": "river", "susiana": "river", "corner": "fields",
}

# Who walks where, by the set of the region (kinds from the set catalogs and the world set).
SHEPHERD = {"rome": "rome.shepherd", "athens": "athens.herder", "parsa": "parsa.shepherd"}
FARMER = {"rome": "rome.farmer", "athens": "athens.farmer", "parsa": "parsa.farmer"}
SHIP = {"rome": "rome.merchantman", "athens": "athens.merchant", "parsa": "world.fishing_boat",
        "world": "world.fishing_boat"}

DENSITIES = {
    "road_day": [0, 0, 0, 0, 0, 0.1, 0.4, 0.8, 1, 1, 1, 0.8, 0.5, 0.4, 0.6, 1, 1, 0.9, 0.5, 0.2,
                 0, 0, 0, 0],
    "daytime": [0, 0, 0, 0, 0, 0.15, 0.5, 0.85, 1, 1, 1, 1, 0.85, 0.6, 0.7, 0.9, 1, 0.95, 0.7,
                0.4, 0.15, 0.05, 0, 0],
    "fields": [0, 0, 0, 0, 0, 0.2, 0.7, 1, 1, 1, 0.8, 0.5, 0.3, 0.5, 0.9, 1, 1, 0.8, 0.4, 0.1,
               0, 0, 0, 0],
    "always": [1] * 24,
    "watch": [0.5] * 6 + [0.7] * 13 + [0.5] * 5,
    # out day and night: a flock rests by its fold after dark
    "herd": [0.8] * 5 + [0.9] + [1.0] * 13 + [0.9] + [0.8] * 4,
    # townsfolk out and about: from first light to the end of the evening
    "town_day": [0, 0, 0, 0, 0, 0, 0.6, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.9, 0.8, 0.6, 0, 0],
    # night birds and the night watch: dusk to dawn
    "night": [1, 1, 1, 1, 1, 0.6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.4, 1, 1, 1, 1],
}

# The towns: who lives there, their landmarks' cards, the line on arrival.
TOWN = {
    "alban_mount": {"name": "Mons Albanus", "native": "Mons Albanus",
                    "caption": "The Alban Mount · AD 126",
                    "people": ["rome.farmer", "rome.citizen", "rome.shepherd", "rome.carter"],
                    "cards": {"latiaris": ("Iuppiter Latiaris", "On the Alban Mount",
                                           "Jupiter's sanctuary on the summit, where the consuls "
                                           "held the Latin Festival each year. Below it lies the "
                                           "round crater lake; the Via Appia passes at the "
                                           "mount's foot.")},
                    "first": "The Alban Mount. The paved way climbs to Jupiter's sanctuary above "
                             "the crater lake."},
    "brundisium": {"name": "Brundisium", "native": "Brundisium",
                   "caption": "Brundisium · AD 126",
                   "people": ["rome.docker", "rome.citizen", "rome.egyptian_sailor",
                              "rome.syrian_merchant", "rome.working_woman"],
                   "cards": {"brundisium_harbour": ("Portus Brundisinus", "The harbour for Greece",
                                                    "A branching natural harbour with quays and "
                                                    "warehouses. Here the Via Appia ends, and "
                                                    "ships sail for Greece across the Ionian "
                                                    "Sea.")},
                   "first": "Brundisium: the Via Appia ends at the harbour, and ships leave for "
                            "Greece."},
    "tibur": {"name": "Tibur", "native": "Tibur", "caption": "Tibur · AD 126",
              "people": ["rome.farmer", "rome.citizen", "rome.carter", "rome.working_woman"],
              "cards": {"tibur": ("Tibur", "Olives above the Anio",
                                  "A hill town famous for its olives, its travertine and the "
                                  "falls of the Anio. On the plain below, Hadrian's great villa "
                                  "has been building since about 118. Neither the villa nor the "
                                  "town's round temple is drawn here: the stop shows a farm, "
                                  "olive groves and a quarry made of common pieces.")},
              "place": ("tibur_farm", "tibur"),
              "first": "Tibur: olive groves on the plain below the hills, and a quarry of "
                       "travertine."},
    "capua": {"name": "Capua", "native": "Capua", "caption": "Capua · AD 126",
              "people": ["rome.citizen", "rome.carter", "rome.freedman", "rome.working_woman"],
              "cards": {"capua": ("Capua", "The city of Campania",
                                  "The great city of the Campanian plain, on the Via Appia. Its "
                                  "amphitheatre was one of the largest in Italy; an inscription "
                                  "records that Hadrian restored it. The city's monuments are not "
                                  "drawn here: the stop shows the road between houses, a posting "
                                  "station and tombs made of common Roman pieces.")},
              "place": ("capua_station", "capua"),
              "first": "Capua: the Via Appia runs between shops and tombs past a posting "
                       "station."},
    "beneventum": {"name": "Beneventum", "native": "Beneventum",
                   "caption": "Beneventum · AD 126",
                   "people": ["rome.citizen", "rome.carter", "rome.farmer"],
                   "cards": {"beneventum": ("Beneventum", "Where the Via Traiana begins",
                                            "Here Trajan's new road to Brundisium leaves the "
                                            "Via Appia; an arch in his honour, dedicated in 114, "
                                            "stands at its start. The arch is not drawn here: "
                                            "the stop shows the fork with an altar, shops and "
                                            "houses made of common Roman pieces.")},
                   "place": ("beneventum_fork", "beneventum"),
              "first": "Beneventum: the Via Traiana leaves the Appia here."},
    "corcyra": {"name": "Kerkyra", "native": "Κέρκυρα", "caption": "Kerkyra · 432 BC",
                "people": ["athens.citizen", "athens.woman", "athens.rower", "athens.metic"],
                "cards": {"corcyra": ("Kerkyra", "Island of the strong fleet",
                                      "A rich island city with the second fleet of Greece, "
                                      "allied to Athens since 433. Its old temple of Artemis, "
                                      "with a Gorgon in the pediment, is not drawn here: the "
                                      "stop shows a harbour, houses and a shrine made of common "
                                      "Greek pieces.")},
                "place": ("corcyra_quay", "corcyra"),
              "first": "Kerkyra: a harbour on the island's east shore."},
    "olympia": {"name": "Olympia", "native": "Ὀλυμπία", "caption": "Olympia · 432 BC",
                "people": ["athens.priest", "athens.citizen", "athens.athlete", "athens.ionian"],
                "cards": {"altis": ("Altis", "Zeus' precinct at Olympia",
                                    "The walled grove of Zeus, crowded with altars and statues, "
                                    "where the games are held every four years. The temple of "
                                    "Zeus, finished about 456, Pheidias' workshop and the stadium "
                                    "are not drawn here: the stop shows the wall, altars, statue "
                                    "bases and olives made of common Greek pieces.")},
                "place": ("altis", "altis"),
              "first": "Olympia: the Altis among its olives and planes."},
    "sparta": {"name": "Sparta", "native": "Σπάρτη", "caption": "Sparta · 432 BC",
               "people": ["athens.farmer", "athens.citizen", "athens.woman", "athens.herder"],
               "cards": {"sparta": ("Sparta", "Villages without a wall",
                                    "Sparta is a cluster of villages in the Eurotas valley, "
                                    "not a walled city: Thucydides remarks that it was never "
                                    "built up as one. The sanctuary of Athena of the Bronze House on the "
                                    "low acropolis is not drawn here: the stop shows farmhouses "
                                    "and a shrine made of common Greek pieces.")},
               "place": ("sparta_shrine", "sparta"),
              "first": "Sparta: farmhouses in the Eurotas valley, and no wall."},
    "gordion": {"name": "Gordion", "native": "Gordion", "caption": "Gordion · c. 470 BC",
                "people": ["parsa.labourer", "parsa.woman_worker", "parsa.guard_spear",
                           "parsa.caravan_driver"],
                "cards": {"gordion": ("Gordion", "The old Phrygian capital",
                                      "The city of the Phrygian kings, under Persia since about "
                                      "540, on its walled mound by the Sangarios. North of it lie "
                                      "the royal burial mounds; the greatest, about 53 metres "
                                      "high, has no art of its own here: the cemetery is shown "
                                      "with common mounds, the town with common pieces.")},
                "place": ("gordion_citadel", "gordion"),
              "first": "Gordion: a walled mound by the Sangarios, burial mounds beyond."},
    "sidon": {"name": "Sidon", "native": "Ṣīdōn", "caption": "Sidon · c. 470 BC",
              "people": ["parsa.labourer", "parsa.woman_worker", "parsa.craftsman",
                         "parsa.scribe"],
              "cards": {"sidon": ("Sidon", "A Phoenician harbour",
                                  "A Phoenician city of ships and timber under the Persian king, "
                                  "whose fleet it served; cedar from the mountains behind it "
                                  "was famous. The temple of Eshmun outside the city is not drawn here: "
                                  "the stop shows a harbour, logs on the strand and houses made "
                                  "of common pieces.")},
              "place": ("sidon_quay", "sidon"),
              "first": "Sidon: ships, cedar logs and a harbour on the Levant coast."},
    "eleusis": {"name": "Eleusis", "native": "Ἐλευσίς", "caption": "Eleusis · 432 BC",
                "people": ["athens.citizen", "athens.woman", "athens.priest", "athens.farmer"],
                "cards": {"telesterion": ("Telesterion", "Hall of the Mysteries",
                                          "The square hall where the initiates of Demeter and "
                                          "Kore gathered. Its Periclean rebuilding is under way: "
                                          "Koroibos began it, Metagenes and Xenokles will finish "
                                          "it, Plutarch says; the roof is not finished.")},
                "first": "Eleusis, on its bay. The Sacred Way from Athens ends at the gate of "
                         "Demeter's sanctuary."},
    "academy": {"name": "Akademeia", "native": "Ἀκαδήμεια", "caption": "The Academy · 432 BC",
                "people": ["athens.youth", "athens.athlete", "athens.citizen", "athens.elder"],
                "cards": {"academy_grove": ("Akademeia", "Gymnasium in the sacred grove",
                                            "A gymnasium among the sacred olives and planes "
                                            "outside the Dipylon; the torch races start at the "
                                            "altar of Prometheus.")},
                "first": "The Academy: the grove of the hero Akademos, olives and running "
                         "boys."},
    "delphi": {"name": "Delphi", "native": "Δελφοί", "caption": "Delphi · 432 BC",
               "people": ["athens.priest", "athens.citizen", "athens.ionian", "athens.woman"],
               "cards": {"athenian_treasury": ("Treasury of the Athenians", "On the Sacred Way",
                                               "A small Doric treasury of Parian marble, its "
                                               "metopes carved with Herakles and Theseus; whether "
                                               "it was built about 510 or after Marathon in 490 "
                                               "is debated."),
                         "delphi_apollo": ("Temple of Apollo", "The Alkmaeonid temple",
                                           "Apollo's temple, rebuilt after a fire in the late "
                                           "sixth century; the Alkmaeonids, an Athenian family in "
                                           "exile, gave it a front of marble. Here the Pythia "
                                           "spoke the god's answers to those who came to ask.")},
               "first": "Delphi under the shining cliffs. The Sacred Way climbs to "
                        "Apollo's temple."},
    "corinth": {"name": "Korinthos", "native": "Κόρινθος", "caption": "Corinth · 432 BC",
                "people": ["athens.citizen", "athens.woman", "athens.metic", "athens.rower"],
                "cards": {"corinth_apollo": ("Temple of Apollo", "On its low hill",
                                   "Built about 540 BC and one of the oldest Doric temples in "
                                   "Greece: six by fifteen stocky columns, each shaft cut from "
                                   "a single block of limestone."),
                "diolkos": ("Diolkos", "The ship road",
                            "A paved trackway across the isthmus, several kilometres long, on "
                            "which ships or their cargoes were hauled on wheeled cradles from the "
                            "gulf to the Saronic sea, sparing the voyage round the Peloponnese."),
                "acrocorinth_summit": ("Acrocorinth", "The citadel rock",
                                       "The steep rock above the city, walled on its summit, "
                                       "with a small temple of Aphrodite at the top.")}, "first": "Corinth, between two seas. Ships cross the isthmus on "
                                      "the diolkos."},
    "delos": {"name": "Delos", "native": "Δῆλος", "caption": "Delos · 432 BC",
              "people": ["athens.priest", "athens.ionian", "athens.citizen"],
              "cards": {"delos_sanctuary": ("Sanctuary of Apollo", "Where the god was born",
                                  "The old temple of poros stone, a marble temple begun after "
                                  "478 and still unfinished, and the temple of Artemis. The "
                                  "League's treasury was moved from here to Athens in 454."),
              "naxian_lions": ("Terrace of the Lions", "Gift of the Naxians",
                               "Marble lions set up by the Naxians about 600 BC, sitting in a row "
                               "and looking out over the sacred lake.")}, "first": "Delos, Apollo's island. The lions keep watch over the "
                                    "sacred lake."},
    "ephesus": {"name": "Ephesos", "native": "Ἔφεσος", "caption": "Ephesus · 432 BC",
                "people": ["athens.ionian", "athens.citizen", "athens.woman", "athens.rower"],
                "cards": {"artemision": ("Artemision", "Temple of Artemis",
                             "Artemis' great temple in the wet plain of the Kaystros, begun about "
                             "560 BC with column drums given by Croesus of Lydia. Pliny gives 120 "
                             "years of building, so work may still be going on.")}, "first": "Ephesus at the mouth of the Kaystros. Artemis' great "
                                      "temple stands in the wet plain."},
    "sardis": {"name": "Sardis", "native": "Sfarda", "caption": "Sardis · c. 470 BC",
               "people": ["parsa.labourer", "parsa.woman_worker", "parsa.guard_spear",
                          "parsa.scribe"],
               "cards": {"royal_road_head": ("Head of the Royal Road", "The first station",
                                 "Here the king's road to Susa begins: Herodotus counts 111 "
                                 "stations and about ninety days on foot, and royal riders carry "
                                 "messages from station to station.")}, "first": "Sardis, under its acropolis. Here the Royal Road "
                                     "begins."},
    "halys": {"name": "Halys", "native": "Halys", "caption": "The Halys crossing · c. 470 BC",
              "people": ["parsa.guard_spear", "parsa.groom", "parsa.caravan_driver"],
              "cards": {"halys_gates": ("Gates on the Halys", "A guarded crossing",
                            "Herodotus says that at the river Halys there are gates to pass "
                            "and a great fort guarding the crossing. Travellers on the royal "
                            "road are stopped and checked here.")}, "first": "The gates on the Halys: the road is guarded here."},
    "euphrates_crossing": {"name": "The Euphrates", "native": "Ufrātu",
                           "caption": "The Euphrates crossing · c. 470 BC",
                           "people": ["parsa.caravan_driver", "parsa.groom", "parsa.labourer"],
                           "cards": {}, "first": "The Euphrates. Round boats ferry the loads "
                                                 "across."},
    "babylon": {"name": "Babylon", "native": "Bābili", "caption": "Babylon · c. 470 BC",
                "people": ["parsa.scribe", "parsa.labourer", "parsa.woman_worker",
                           "parsa.guard_spear", "parsa.craftsman"],
                "cards": {"ishtar_gate": ("Ishtar Gate", "The blue gate",
                              "Nebuchadnezzar's gate of about 575 BC, faced with blue glazed "
                              "bricks bearing aurochs and the dragon mušḫuššu in relief; the "
                              "procession of the spring festival passed through it."),
                "processional_way": ("Processional Way", "The street of lions",
                                     "The paved way from the Ishtar Gate south through the "
                                     "city, its walls faced with glazed bricks showing striding "
                                     "lions."),
                "etemenanki": ("Etemenanki", "The great ziggurat",
                               "Marduk's stepped temple tower beside his temple Esagila. How "
                               "much of it stood under Xerxes is debated; it is shown standing.")}, "first": "Babylon. The road enters by the blue gate of Ishtar."},
    "susa": {"name": "Susa", "native": "Šušan", "caption": "Susa · c. 470 BC",
             "people": ["parsa.scribe", "parsa.guard_spear", "parsa.woman_worker",
                        "parsa.labourer", "parsa.elamite"],
             "cards": {"susa_palace": ("Palace of Darius", "Susa",
                                       "An audience hall of 36 columns like Pārsa's, beside courts "
                                       "faced with glazed bricks: archers, lions and winged bulls. "
                                       "Darius's building inscription here names the peoples who "
                                       "made it, from Ionian stonecutters to Babylonian "
                                       "brickmakers.")},
             "first": "Susa: the palace of Darius on its mound above the Shaur."},
    "persian_gates": {"name": "The Persian Gates", "native": "The Persian Gates",
                      "caption": "The Persian Gates · c. 470 BC",
                      "people": ["parsa.guard_spear", "parsa.archer"],
                      "cards": {"gates_station": ("Station at the Gates", "The road to Pārsa",
                                    "A walled station with guards where the road enters the "
                                    "defile toward Pārsa. In 470 BC this is a guarded pass on the "
                                    "king's road; its famous battle came 140 years later.")}, "first": "The Persian Gates. Guards watch the defile on the "
                                            "road to Pārsa."},
    "pasargadae": {"name": "Pasargadae", "native": "Pāθragadā",
                   "caption": "Pasargadae · c. 470 BC",
                   "people": ["parsa.magus", "parsa.gardener", "parsa.guard_spear"],
                   "cards": {"pasargadae_garden": ("Palace P and its garden", "Cyrus' garden",
                                                   "Cyrus' palace faces a garden watered by "
                                                   "narrow stone channels and square basins, "
                                                   "cut in limestone; cypresses and planes grow "
                                                   "along them."),
                             "cyrus_tomb": ("Tomb of Cyrus", "On six steps",
                                            "The tomb of Cyrus the Great, a gabled stone chamber "
                                            "on six steps in a watered grove. The magi who keep "
                                            "it, father to son since Cambyses, receive a sheep a "
                                            "day and a horse a month. Two centuries later "
                                            "Alexander found it robbed and had it restored "
                                            "(Arrian 6.29)."),
                             "cyrus": ("Kūruš", "Cyrus, founder (a memory)",
                                       "Cyrus joined Persians, Medes and Elamites into one empire "
                                       "and took Lydia and Babylon. He rests here in a small stone "
                                       "house on six steps, where magi kept watch, father to son. "
                                       "Two centuries later Alexander found it robbed and had it "
                                       "restored."),
                             "cyrus_cylinder": ("The Cyrus Cylinder", "A careful reading",
                                                "A clay cylinder written in Babylonian cuneiform "
                                                "after Cyrus, 'king of Anšan', took Babylon in 539 "
                                                "BC, and buried in the city's wall. In the manner "
                                                "of Mesopotamian kings, it says Marduk chose Cyrus, "
                                                "blames the previous king, and says Cyrus entered "
                                                "Babylon without battle, returned the images of "
                                                "gods to their shrines in a list of cities from "
                                                "Aššur and Susa to the Zagros, and gathered their "
                                                "people and gave them back their homes. It does not "
                                                "name the Jews; their return is told in the Hebrew "
                                                "Bible. Often called the first charter of human "
                                                "rights, and treasured in Iran today, it is to "
                                                "historians a royal proclamation of a policy of "
                                                "restoring local cults and peoples.")},
                   "figures": [{"actor": "parsa.cyrus", "presence": "memory", "card": "cyrus",
                                "translucent": True,
                                "schedule": [{"hours": ["18:30", "03:00"], "routine": "memory"}],
                                "routines": {"memory": {"steps": [
                                    {"go": {"item": "parsa.cyrus_tomb", "spot": "beside"}},
                                    {"wander": {"radius": 3}, "dur": [40, 60]},
                                    {"use": {"here": True}, "anim": "idle",
                                     "until": {"hour": "03:00"}}]}},
                                "ideas": ["cyrus_cylinder"]}],
                   "first": "Pasargadae: Cyrus' gardens and his tomb on the plain."},
}


def grid_rect(c0, r0, c1, r1):
    """Plan rect -> grid [x0, y0, x1, y1]."""
    xs = [to_grid(c, r) for c in (c0, c1) for r in (r0, r1)]
    return [int(min(x for x, _ in xs)), int(min(y for _, y in xs)), int(max(x for x, _ in xs)),
            int(max(y for _, y in xs))]


def _bbox(mask: np.ndarray):
    js, is_ = np.nonzero(mask)
    return int(is_.min()), int(js.min()), int(is_.max()), int(js.max())


def theme(rid: str) -> dict:
    kind, set_, time, _rect, _b = P.REGIONS[rid]
    t = time if time in GRADING else "none"
    if kind == "seam":
        bed = "seam"
    elif rid in P.BIOMES or rid in STRETCH_BED:
        bed = STRETCH_BED.get(rid, "fields")
    else:
        bed = "sea"
    day, night = BEDS[bed]
    out = {"grading": GRADING[t], "haze": {"colour": HAZE[t], "strength": 0.12},
           "ambience": {"beds": [{"file": day, "hours": ["06:00", "19:00"]},
                                 {"file": night, "hours": ["19:00", "06:00"]}]}}
    if kind == "seam":
        out["seam"] = True
    return out


def pastures(world: World, rid: str) -> list:
    """Grid rects of each fold's pasture in the region (base districts `<rid>/pasture`)."""
    name = f"{rid}/pasture"
    if name not in world.districts:
        return []
    d = world.districts.index(name)
    mask = world.D == d
    out = []
    seen = np.zeros_like(mask)
    for j, i in zip(*np.nonzero(mask)):
        if seen[j, i]:
            continue
        # One rect per 17 x 17 block of pasture (one fold each).
        c0, r0 = (i // 17) * 17, (j // 17) * 17
        sub = mask[r0:r0 + 17, c0:c0 + 17]
        if sub.any():
            a, b, c, e = _bbox(sub)
            out.append(grid_rect(c0 + a, r0 + b, c0 + c, r0 + e))
        seen[r0:r0 + 17, c0:c0 + 17] = True
    return out


def region_of(world: World, c: int, r: int) -> str | None:
    d = int(world.D[r, c])
    return None if d == NONE16 else world.districts[d].split("/", 1)[0]


def stretch_file(rid: str, world: World, graphs: dict[str, Graph]) -> dict:
    kind, set_, time, _rect, _b = P.REGIONS[rid]
    sname = P.LABELS.get(rid, rid.replace("_", " ").title())
    districts = []
    have = {d.split("/", 1)[1] for d in world.districts if d.startswith(rid + "/")}
    era = set_ if set_ in ("rome", "athens", "parsa") else None
    if "road" in have:
        pops = [{"actor": "world.traveller", "density": "road_day", "max_per_chunk": 4},
                {"actor": "world.merchant", "density": "road_day", "max_per_chunk": 1},
                {"actor": "world.donkey", "density": "road_day", "max_per_chunk": 2}]
        if era == "parsa":
            pops.append({"actor": "parsa.groom", "density": "watch", "max_per_chunk": 1})
        districts.append({"id": "road", "populations": pops})
    if "farm" in have and era:
        districts.append({"id": "farm", "populations": [
            {"actor": FARMER[era], "density": "fields", "max_per_chunk": 3},
            {"actor": "world.ox", "density": "fields", "max_per_chunk": 1},
            {"actor": "world.dog", "density": "daytime", "max_per_chunk": 1}]})
    if "land" in have:
        birds = []
        if rid in ("apennines", "arcadia", "taurus", "zagros"):
            birds.append({"actor": "world.eagle", "density": "daytime", "max_per_chunk": 1})
        if era in ("athens", "parsa") and rid not in ("taurus", "zagros"):
            birds.append({"actor": "world.stork", "density": "daytime", "max_per_chunk": 1,
                          "seasons": ["spring", "summer"]})
        districts.append({"id": "land", "populations": birds})
    if "sea" in have:
        districts.append({"id": "sea", "populations": [
            {"actor": "world.gull", "density": "daytime", "max_per_chunk": 1.5}]})
    groups, zones = [], []
    if "pasture" in have and era:
        sheep = {"actor": "world.sheep", "variant": 1 if era == "parsa" else 0, "count": 6}
        groups.append({"id": "flock", "formation": "cluster", "radius": 3,
                       "leader": {"actor": SHEPHERD[era]},
                       "members": [sheep, {"actor": "world.goat", "count": 3},
                                   {"actor": "world.dog", "count": 1}]})
        zones += [{"kind": "pasture", "rect": r, "group": "flock"} for r in pastures(world, rid)]
    tokens = []
    base = graphs.get("base")
    if base:
        for ln in base.lanes:
            c, r = to_plan(*ln.points[0])
            if region_of(world, c, r) != rid:
                continue
            ids = {p.id for p in ln.ports}
            if "grounds" in ids:
                tokens.append({"actor": "world.fishing_boat", "lane": f"base:{ln.id}", "count": 2})
                tokens.append({"actor": "world.fishing_boat", "lane": f"base:{ln.id}", "count": 1,
                               "hours": ["20:30", "03:30"],
                               "when": {"months": ["may", "jun", "jul", "aug", "sep"]},
                               "note": "fishing by torchlight on calm summer nights"})
                gc, gr = to_plan(*ln.points[-1])
                zones.append({"kind": "fishing", "rect": grid_rect(gc - 2, gr - 2, gc + 2, gr + 2),
                              "lane": f"base:{ln.id}"})
            elif ln.kind == "river":
                tokens.append({"actor": "world.reed_boat", "lane": f"base:{ln.id}", "count": 2})
            else:
                tokens.append({"actor": SHIP.get(set_, "world.fishing_boat"),
                               "lane": f"base:{ln.id}", "count": 2})
    events = []
    doc = {"version": 1, "id": rid, "name": sname, "caption": sname, "theme": theme(rid),
           "districts": districts, "densities": DENSITIES, "figures": [], "groups": groups,
           "chains": [], "events": events, "lanes_tokens": tokens, "zones": zones, "cards": {},
           "strings": {}, "journal": []}
    return doc


def road_life(docs: dict, graphs: dict[str, Graph]) -> None:
    """The Royal Road's events, filed with Anatolia (its traffic is `traffic.TRAFFIC`)."""
    base = graphs.get("base")
    if base is None or "anatolia" not in docs:
        return
    royal = [n.id for n in base.nodes if n.kind == "station" and n.id.startswith("royal_road_station")]
    a = docs["anatolia"]
    # L6, the relay of riders (Herodotus 8.98): station to station, a fresh horse waiting.
    a["events"].append({"id": "courier_relay", "trigger": {"on": "window",
                        "hours": ["07:00", "18:00"], "every": 7200},
                        "size": "small", "duration": [30, 60],
                        "cast": [{"actor": "parsa.courier"}, {"actor": "parsa.groom"}],
                        "route": [f"base:{s}" for s in royal],
                        "steps": [{"go": {"node": "next"}},
                                  {"use": {"item": "world.royal_station", "slot": "change"},
                                   "anim": "idle", "dur": [4, 6]}],
                        "sfx": "sfx/world/gallop.wav"})
    # L7, caravans arrive at dusk; beacons lit on the heights in sequence.
    a["events"].append({"id": "caravan_dusk", "trigger": {"on": "window",
                        "hours": ["17:30", "19:00"], "chance": 1.0}, "size": "medium",
                        "duration": [180, 240], "cast": [{"group": "caravan"}],
                        "steps": [{"go": {"item": "world.royal_station", "slot": "horse",
                                          "within": 64}},
                                  {"use": {"here": True}, "anim": "idle", "dur": [60, 90]}]})
    a["events"].append({"id": "beacons_lit", "trigger": {"on": "window",
                        "hours": ["19:00", "19:30"], "chance": 1.0}, "size": "small",
                        "duration": [60, 60],
                        "steps": [{"each": {"item": "world.beacon", "within": 4096},
                                   "state": "lit", "every": 4}]})


def droves(docs: dict, world: World, graphs: dict[str, Graph]) -> None:
    """Flocks on the move (seasonal movement between pastures; the Parilia's flocks brought to
    Rome): a herder leading a `drove` (sheep, goats and a dog in a cluster) along the roads
    between the two farthest farms or stations of each stretch of an era."""
    base = graphs.get("base")
    if base is None:
        return
    for rid, doc in docs.items():
        set_ = P.REGIONS[rid][1]
        if set_ not in SHEPHERD or P.REGIONS[rid][0] != "stretch":
            continue
        stops = sorted((n.id, to_plan(*n.at)) for n in base.nodes
                       if ("_farm_" in n.id or n.kind == "station" or n.id.startswith("fold_"))
                       and region_of(world, *to_plan(*n.at)) == rid)
        if len(stops) < 2:
            continue
        # A flock leaves from its fold (up its drove track) where the stretch has folds.
        folds = [x for x in stops if x[0].startswith("fold_")]
        pairs = [(x, y) for x in folds for y in stops if y[0] != x[0]] if folds else \
            [(x, y) for x in stops for y in stops if x[0] < y[0]]
        a, b = max(pairs, key=lambda xy: (abs(xy[0][1][0] - xy[1][1][0]) +
                                          abs(xy[0][1][1] - xy[1][1][1]), xy[0][0], xy[1][0]))
        sheep = {"actor": "world.sheep", "variant": 1 if set_ == "parsa" else 0, "count": 8}
        doc["groups"].append({"id": "drove", "formation": "cluster", "radius": 3,
                              "leader": {"actor": SHEPHERD[set_]},
                              "members": [sheep, {"actor": "world.goat", "count": 3},
                                          {"actor": "world.dog", "count": 1}]})
        doc["lanes_tokens"].append({"actor": SHEPHERD[set_], "group": "drove", "count": 1,
                                    "route": {"start": f"base:{a[0]}", "end": f"base:{b[0]}"},
                                    "when": {"seasons": ["spring", "autumn"]},
                                    "note": "flocks moving between summer and winter pastures"})
    if "latium_italy" in docs and "rome" in graphs:
        doc = docs["latium_italy"]
        farms = sorted(n.id for n in base.nodes if n.id.startswith("via_appia_farm_"))
        if farms and any(g["id"] == "drove" for g in doc["groups"]):
            doc["lanes_tokens"].append({"actor": "rome.shepherd", "group": "drove", "count": 2,
                                        "route": {"start": f"base:{farms[0]}",
                                                  "end": "rome:appia_se"},
                                        "when": {"season": "spring", "day": 2},
                                        "note": "shepherds bring their flocks to Rome for the "
                                                "Parilia, the shepherds' feast of Pales"})


def town_file(rid: str, layout_world: World, graphs: dict[str, Graph], facts: dict) -> dict:
    from . import seasonlife, townlife
    kind, set_, time, rect, _b = P.REGIONS[rid]
    t = TOWN[rid]
    g = graphs.get(rid)
    tiles, placed, bare = facts.get(rid, ({}, set(), set()))
    nodes = {n.id for n in g.nodes} if g else set()
    rule = seasonlife.TOWN_SEASONS.get(rid, {}).get("factors", {})
    factors = rule.get(("*", "*"), [1.0] * 12)
    from . import climates as C
    from . import seasons as S
    root = Path(__file__).resolve().parents[3]
    work = S.resolve(S.raw_climates(root), C.REGION_CLIMATE[rid]).get("work", {})
    life = townlife.build(rid, set_, tiles, placed, nodes, factors, seasonlife.KIND_ANIMS,
                          t["people"][-1], work, bare)
    tokens = []
    if g:
        for ln in g.lanes:
            ids = {p.id for p in ln.ports}
            if ln.id == "quffa_ferry":
                tokens.append({"actor": "world.quffa", "lane": f"{rid}:{ln.id}", "count": 2,
                               "hours": ["05:00", "20:00"]})
            elif "grounds" in ids:
                tokens.append({"actor": "world.fishing_boat", "lane": f"{rid}:{ln.id}", "count": 1})
                tokens.append({"actor": "world.fishing_boat", "lane": f"{rid}:{ln.id}", "count": 1,
                               "hours": ["20:30", "03:30"],
                               "when": {"months": ["may", "jun", "jul", "aug", "sep"]},
                               "note": "fishing by torchlight on calm summer nights"})
            elif ln.kind == "river" or rid in ("babylon", "susa", "euphrates_crossing"):
                tokens.append({"actor": "world.reed_boat", "lane": f"{rid}:{ln.id}", "count": 2})
            else:
                tokens.append({"actor": SHIP.get(set_, "world.fishing_boat"),
                               "lane": f"{rid}:{ln.id}", "count": 2})
                tokens.append({"actor": "world.fishing_boat", "lane": f"{rid}:{ln.id}", "count": 1})
                # Fishing by torchlight on calm summer nights (Plato, Sophist 220d).
                tokens.append({"actor": "world.fishing_boat", "lane": f"{rid}:{ln.id}", "count": 1,
                               "hours": ["20:30", "03:30"],
                               "when": {"months": ["may", "jun", "jul", "aug", "sep"]},
                               "note": "fishing by torchlight on calm summer nights"})
    kinds_of = {"cyrus": "figure", "cyrus_cylinder": "idea"}
    cards = {k: {"kind": kinds_of.get(k, "landmark"), "title": a, "epithet": b, "text": c}
             for k, (a, b, c) in t["cards"].items()}
    cards.update(life["cards"])
    return {"version": 1, "id": rid, "name": t["name"], "native": t["native"],
            "caption": t["caption"], "theme": theme(rid),
            "districts": life["districts"], "densities": DENSITIES,
            "roles": life["roles"], "figures": t.get("figures", []),
            "groups": [], "chains": life["chains"],
            "events": life["events"], "lanes_tokens": tokens, "zones": [], "cards": cards,
            "strings": {"first_visit": t["first"], **life["strings"]},
            "journal": ["landmark:*", "chain:*"]} | (
        {"place": {"node": f"{rid}:{t['place'][0]}", "card": t["place"][1]}} if "place" in t else {})


def town_facts(world: World) -> dict[str, tuple[dict[str, int], set[str], set[str]]]:
    """Per town: its districts' tiles, the item ids its own layer places and the districts with
    no tile anyone can stand on (all of it impassable)."""
    from .compose import live_items
    from .layer import IMPASSABLE
    out: dict[str, tuple[dict[str, int], set[str], set[str]]] = \
        {rid: ({}, set(), set()) for rid in TOWNS}
    u, c = np.unique(world.D, return_counts=True)
    standing = set(np.unique(world.D[(world.L & IMPASSABLE) == 0]).tolist())
    for d, n in zip(u.tolist(), c.tolist()):
        if d == NONE16:
            continue
        rid, did = world.districts[d].split("/", 1)
        if rid in out:
            out[rid][0][did] = int(n)
            if d not in standing:
                out[rid][2].add(did)
    for _, it in live_items(world):
        if it.layer in out:
            out[it.layer][1].add(it.id)
    return out


def base_items(world: World, reach: set | None = None) -> dict[str, dict[str, dict[str, int]]]:
    """region -> district -> item id -> placements, for the items of the base and corner layers
    (the layers the stretches and seams draw their life from), by the district under each
    item's origin tile; with `reach`, only items with a tile of it beside them (work there is
    work a walker can get to)."""
    from .citylife import _ring
    from .compose import live_items
    out: dict[str, dict[str, dict[str, int]]] = {}
    for _, it in live_items(world):
        if it.layer not in ("base", "corner"):
            continue
        if reach is not None and not any(t in reach for t in _ring(it)):
            continue
        d = int(world.D[it.r, it.c])
        if d == NONE16:
            continue
        rid, did = world.districts[d].split("/", 1)
        row = out.setdefault(rid, {}).setdefault(did, {})
        row[it.id] = row.get(it.id, 0) + 1
    return out


def country_reach(world: World, graphs: dict[str, Graph], cat, root: Path) -> set:
    """Walkable tiles within the life's reach of the base's and the corner's graphs (the reach
    the life checks give a worker, slopes walked as the art's contract has them)."""
    from . import landform
    from .citylife import _graph_labels
    from .validate import walk_map
    walk, stair = walk_map(world, cat)
    slope = landform.slope_tiles(world, cat, root)
    lv = world.L & 0x0F
    out: set = set()
    for name in ("base", "corner"):
        if name in graphs:
            out |= set(_graph_labels(graphs[name], walk, lv, stair, (0, 0, COLS - 1, ROWS - 1),
                                     slope))
    return out


def check_refs(docs: dict, graphs: dict[str, Graph], joined=None) -> list[str]:
    """Every lane and route node a token names exists in the graphs, and every route has a
    path on the joined graph."""
    out = []
    for rid, doc in docs.items():
        for tk in doc["lanes_tokens"]:
            if "lane" in tk:
                layer, lid = tk["lane"].split(":", 1)
                g = graphs.get(layer)
                if g is None or not any(ln.id == lid for ln in g.lanes):
                    out.append(f"{rid}: lane {tk['lane']} not found")
            for end in tk.get("route", {}).values():
                layer, nid = end.split(":", 1)
                g = graphs.get(layer)
                if g is None or g.node(nid) is None:
                    out.append(f"{rid}: route node {end} not found")
            if "route" in tk and joined is not None and \
                    joined.path(tk["route"]["start"], tk["route"]["end"]) is None:
                out.append(f"{rid}: no path from {tk['route']['start']} to {tk['route']['end']}")
        for ev in doc["events"]:
            for end in ev.get("route", []):
                layer, nid = end.split(":", 1)
                if graphs.get(layer) is None or graphs[layer].node(nid) is None:
                    out.append(f"{rid}: event {ev['id']} node {end} not found")
    return out


def write(world: World, graphs: dict[str, Graph], out_dir: Path, cat=None) -> list[Path]:
    """Region files of the stretches, seas, seams and waypoint towns this lane builds."""
    docs = {}
    for rid, v in P.REGIONS.items():
        if v[0] in ("stretch", "seam"):
            docs[rid] = stretch_file(rid, world, graphs)
    road_life(docs, graphs)
    droves(docs, world, graphs)
    from . import countrylife
    from . import seasonlife as SL0
    SL0.load_kinds(Path(__file__).resolve().parents[3])
    corner = countrylife.corner_file(base_items(world).get("corner", {}), SL0.KIND_ANIMS)
    corner["theme"] = theme("corner")
    corner["densities"] = DENSITIES
    docs["corner"] = corner
    regions = Path(__file__).resolve().parent.parent / "regions"
    facts = town_facts(world)
    for rid in TOWNS:
        # A town with its own life module is a city file (`build.sh --city`), never written here.
        if rid in graphs and not (regions / rid / "life.py").exists():
            docs[rid] = town_file(rid, world, graphs, facts)
    from . import climates as C
    from . import look, places, seasonlife, sound, traffic
    traffic.apply(docs, graphs)
    root = Path(__file__).resolve().parents[3]
    ctx = seasonlife.context(world, graphs, cat, root)
    placed = base_items(world, country_reach(world, graphs, cat, root))
    for rid in list(docs):
        docs[rid] = seasonlife.apply(places.apply(docs[rid]), world, graphs, cat, root)
        if P.REGIONS[rid][0] in ("stretch", "seam"):
            countrylife.apply(docs[rid], ctx.clims[C.REGION_CLIMATE[rid]], placed.get(rid, {}),
                              seasonlife.KIND_ANIMS)
            countrylife.events(docs[rid], seasonlife.KIND_ANIMS)
            countrylife.merge_months(docs[rid])
            places.apply(docs[rid])
            seasonlife.dress(docs[rid])
    seasonlife.transhumance(docs, world, graphs, ctx.clims)
    for rid, doc in docs.items():
        countrylife.ambient(doc, ctx.clims[C.REGION_CLIMATE[rid]])
    joined = traffic.Joined(graphs)
    for rid, doc in docs.items():
        sound.apply(doc, world, cat, root)
        look.apply(doc, world, cat, root)
        seasonlife.finish(doc, root)
        traffic.finish(doc, graphs, joined)
    problems = check_refs(docs, graphs, joined)
    if problems:
        raise SystemExit("region files name missing graph parts:\n  " + "\n  ".join(problems))
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for rid, doc in docs.items():
        f = out_dir / f"{rid}.json"
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        paths.append(f)
    return paths
