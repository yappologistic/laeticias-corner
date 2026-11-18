"""The waypoint towns' own life: who works where (the trades each town was known for), what it
makes or ships (a chain), its market rhythm, its evenings and its night watch, and the events of
its year (living-world §2-§5, in the region-file contract `citylife` checks).

Each town in `TOWNS` names its districts' area kinds, its trades (role, kind, workplace, hours,
how many), a chain, its market day (the game's four-day week), the nodes its night watch walks,
and its own events and cards. Every town also gets the same household roles by its set: the
townsfolk on their errands and in the evening, a water carrier at the well, children, the night
watch, a dog, and the lamps lit at dusk. The townsfolk are calibrated so each district meets its
area's movers per screenful (`citylife.AREA`) in every month the town's seasons allow.

`life.town_file` builds the document; `citylife.check` holds it to L1-L8 like a city's.
"""

from __future__ import annotations

from .citylife import AREA, CHUNK_TILES, MOVING, SCREEN_TILES

ALL = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "jan", "feb"]
DAYWORK = [("06:00", "12:00"), ("14:00", "18:30")]
EARLY = [("04:30", "11:00"), ("15:00", "19:00")]      # fishermen, bakers: out before dawn
LONG = [("05:30", "21:00")]                             # stations and inns

# Household kinds by set.
HOUSEHOLD = {
    "rome": {"folk": "rome.citizen", "woman": "rome.working_woman", "child": "rome.child",
             "watch": "rome.vigil", "keeper": "rome.freedman",
             "lamps": ["rome.r_lamp", "rome.r_brazier"], "well": "rome.r_well",
             "wedding": ["jun"], "sfx_music": "sfx/rome/tibia.wav"},
    "athens": {"folk": "athens.citizen", "woman": "athens.woman", "child": "athens.child",
               "watch": "athens.citizen", "keeper": "athens.metic",
               "lamps": ["athens.g_lamp", "athens.g_brazier"], "well": "athens.g_well",
               "wedding": ["jan", "feb"], "sfx_music": "sfx/athens/aulos.wav"},
    "parsa": {"folk": "parsa.labourer", "woman": "parsa.woman_worker", "child": "parsa.child",
              "watch": "parsa.guard_spear", "keeper": "parsa.servant",
              "lamps": ["parsa.p_torch", "parsa.p_brazier"], "well": "parsa.p_well",
              "wedding": ["apr", "may"], "sfx_music": "sfx/parsa/horn.wav"},
}


def T(id_, actor, name, district, target, anim, count, hours=DAYWORK, months=None, card=None):
    """A trade: role id, actor kind, name, district, workplace ({"item": id} | {"node": id} |
    None to work where they stand), working animation, how many, hours, months."""
    return {"id": id_, "actor": actor, "name": name, "district": district, "target": target,
            "anim": anim, "count": count, "hours": hours, "months": months, "card": card}


def C(id_, name, source, goods, carry_to, sink_by, by=("maker", "carrier"), period=200,
      hours=("06:00", "18:00"), labels=("", "", "")):
    return {"id": id_, "name": name, "source": source, "goods": goods, "to": carry_to,
            "by": by, "sink_by": sink_by, "period": period, "hours": list(hours),
            "labels": labels}


def card(kind, title, epithet, text):
    return {"kind": kind, "title": title, "epithet": epithet, "text": text}


# -- the towns -------------------------------------------------------------------------------
TOWNS = {
    "tibur": {
        "areas": {"hills": "country", "plain": "country"},
        "trades": [
            T("quarryman", "rome.builder", "Quarryman at the travertine", "hills",
              {"item": "world.quarry"}, "work_high", 4, card="quarryman"),
            T("olive_grower", "rome.farmer", "Olive grower", "plain", {"item": "rome.r_villa_farm"},
              "work_low", 3, months=None),
            T("carter", "rome.carter", "Carter on the Tiburtina", "hills", {"node": "tiburtina"},
              "idle", 1)],
        "chain": C("tibur_travertine", "Travertine for Rome", "world.quarry.beside",
                   "rome.goods_marble", "node:tiburtina", "carter", by=("quarryman", "stone_hauler"),
                   labels=("a block of travertine cut from the quarry", "hauled to the road",
                           "loaded on a cart for Rome")),
        "market": 1, "round": ["tibur_farm", "tiburtina"],
        "cards": {"quarryman": card("role", "Lapicida", "", "Quarrymen cut the white travertine "
                                    "below Tibur: the stone of the Colosseum and of Rome's "
                                    "new temples, carted down the Via Tiburtina.")},
    },
    "capua": {
        "areas": {"road": "road", "town": "town"},
        "trades": [
            T("station_hand", "rome.freedman", "Hand at the mutatio", "town",
              {"item": "rome.mutatio"}, "serve", 2, LONG),
            T("shopkeeper", "rome.freedman", "Shopkeeper", "town", {"item": "rome.r_insula_low"},
              "serve", 3),
            T("perfumer", "rome.working_woman", "Perfume seller of the Seplasia", "town",
              {"item": "rome.r_insula_low"}, "serve", 1, card="perfumer"),
            T("mourner", "rome.matron", "Visitor at the tombs", "road", {"item": "rome.r_tomb"},
              "pray", 1)],
        "chain": C("capua_wine", "Campanian wine for travellers", "rome.r_insula_low.beside",
                   "rome.goods_wine_amphora", "rome.mutatio.beside", "station_hand",
                   by=("shopkeeper", "wine_porter"),
                   labels=("an amphora of Campanian wine from the shop", "carried to the posting "
                           "station", "poured for travellers")),
        "market": 2, "round": ["appia_capua_w", "capua_station", "appia_capua_e"],
        "cards": {"perfumer": card("role", "Unguentaria", "", "Capua's Seplasia was a whole "
                                   "street of perfume sellers, famous across Italy for their "
                                   "scented oils.")},
    },
    "beneventum": {
        "areas": {"road": "road", "town": "country"},
        "trades": [
            T("vinedresser", "rome.farmer", "Vinedresser", "town", {"item": "rome.r_vine"},
              "work_low", 2),
            T("altar_keeper", "rome.flamen", "Priest at the altar", "town",
              {"item": "rome.r_altar"}, "pray", 1, [("06:30", "11:00"), ("16:00", "18:30")])],
        "chain": None,
        "market": 3, "round": ["appia_benev_w", "beneventum_fork", "appia_benev_e"],
        "cards": {},
    },
    "eleusis": {
        "areas": {"acropolis": "wild", "fields": "country", "plain": "country",
                  "sanctuary": "country", "shore": "country", "town": "town"},
        "trades": [
            T("priestess_servant", "athens.priest", "Servant of the goddesses", "sanctuary",
              {"node": "telesterion"}, "pray", 2, [("06:00", "11:00"), ("15:00", "18:30")]),
            T("builder", "athens.mason", "Builder on the Telesterion", "sanctuary",
              {"node": "telesterion"}, "work_high", 3, card="telesterion_builder"),
            T("barley_farmer", "athens.farmer", "Farmer of the Rarian plain", "fields", None,
              "work_low", 3, card="rarian"),
            T("fisher", "world.fisher", "Fisherman of the bay", "shore", {"node": "eleusis_shore"},
              "work_low", 2, EARLY)],
        "chain": C("eleusis_first_fruits", "First fruits for the goddesses",
                   "athens.g_house_small.beside", "world.goods_sacks", "node:telesterion",
                   "priestess_servant", by=("barley_farmer", "grain_porter"), period=240,
                   labels=("a share of the barley harvest", "carried up to the sanctuary",
                           "stored as the goddesses' first fruits")),
        "market": 0, "round": ["eleusis_town", "telesterion", "eleusis_shore"],
        "cards": {"rarian": card("role", "Farmer", "", "Eleusis' Rarian plain was where, the "
                                 "story said, Demeter first taught men to sow barley."),
                  "telesterion_builder": card("role", "Builder", "", "Masons at work on the "
                                              "Periclean Telesterion, the hall of the "
                                              "Mysteries, still without its roof."),
                  "eleusis_first_fruits": card("idea", "Aparchai", "First fruits",
                                               "An Athenian decree of about these years asked "
                                               "the farmers of Attica, and invited all Greeks, to "
                                               "bring a share of their barley and wheat to the two "
                                               "goddesses at Eleusis. The grain was stored in "
                                               "pits in the sanctuary and sold to pay for "
                                               "offerings and dedications.")},
    },
    "academy": {
        "areas": {"grove": "country"},
        "trades": [
            T("gymnast", "athens.athlete", "Young man at exercise", "grove", None, "run", 3,
              [("06:00", "11:00"), ("15:00", "18:30")]),
            T("trainer", "athens.elder", "Trainer", "grove", None, "idle", 1,
              [("06:00", "11:00"), ("15:00", "18:30")]),
            T("olive_keeper", "athens.farmer", "Keeper of the sacred olives", "grove",
              {"item": "athens.academy_grove"}, "work_low", 1)],
        "chain": C("academy_oil", "Oil of the sacred olives", "athens.academy_grove.beside",
                   "world.goods_oil_jar", "node:academy_e", "oil_porter",
                   by=("olive_keeper", "oil_porter"), period=300,
                   labels=("oil pressed from the sacred olives", "carried to the road",
                           "taken to the city for the prizes")),
        "market": None, "round": ["academy", "academy_e"],
        "cards": {"academy_oil": card("idea", "Moriai", "The sacred olives",
                                      "The olives of the Academy were sacred to Athena, said "
                                      "to be grown from the tree on the Acropolis. Their oil "
                                      "filled the painted amphorae given as prizes at the "
                                      "Great Panathenaia, and to cut one down was a crime "
                                      "tried before the Areopagus.")},
    },
    "corcyra": {
        "areas": {"harbour": "country", "island": "country"},
        "trades": [
            T("fisher", "world.fisher", "Fisherman", "harbour", {"node": "corcyra_quay"},
              "haul", 3, EARLY),
            T("rower", "athens.rower", "Rower of the fleet", "harbour", {"node": "corcyra_quay"},
              "haul", 3, card="corcyra_fleet"),
            T("shopkeeper", "athens.metic", "Shopkeeper", "island",
              {"item": "athens.g_house_small"}, "serve", 2)],
        "chain": C("corcyra_fish", "Fish for the town", "node:corcyra_quay", "world.goods_fish",
                   "athens.g_house_small.beside", "cook", by=("fisher", "fish_porter"),
                   period=180, hours=("05:00", "13:00"),
                   labels=("the night's catch landed on the quay", "carried up into the town",
                           "cooked in the houses")),
        "market": 1, "round": ["corcyra_quay"],
        "cards": {"corcyra_fleet": card("role", "Rower", "", "Kerkyra's 120 triremes made the "
                                        "second fleet of Greece; the quarrel over it led Athens "
                                        "to an alliance in 433.")},
    },
    "delphi": {
        "areas": {"cliffs": "wild", "sanctuary": "country", "slope": "country"},
        "trades": [
            T("temple_servant", "athens.priest", "Temple servant", "sanctuary", {"node": "temple"},
              "pour", 2, [("06:00", "11:30"), ("15:00", "18:30")]),
            T("guide", "athens.citizen", "Guide on the Sacred Way", "sanctuary",
              {"node": "treasury"}, "gesture", 2, card="exegetes"),
            T("goatherd", "athens.herder", "Goatherd on the slopes", "slope", None, "idle", 1,
              [("05:30", "19:00")])],
        "chain": C("delphi_offerings", "Cakes for the god", "node:delphi_s", "world.goods_bread",
                   "node:temple", "temple_servant", by=("cake_seller", "offering_bearer"),
                   period=240, hours=("07:00", "16:00"),
                   labels=("an offering cake bought below the sanctuary",
                           "carried up the Sacred Way", "laid on the altar")),
        "market": None, "round": ["delphi_s", "treasury", "temple"],
        "cards": {"exegetes": card("role", "Exegetes", "", "Local guides walked visitors up "
                                   "the Sacred Way, telling the story of every treasury and "
                                   "statue they passed.")},
    },
    "olympia": {
        "areas": {"altis": "country", "valley": "country"},
        "trades": [
            T("priest", "athens.priest", "Priest of Zeus", "altis", {"node": "altis"}, "pour", 1,
              [("06:00", "11:00"), ("15:00", "18:00")]),
            T("athlete", "athens.athlete", "Athlete in training", "valley", None, "run", 3,
              [("06:00", "11:00"), ("16:00", "19:00")], months=["may", "jun", "jul"]),
            T("woodman", "world.logger", "The woodman of the altar", "valley", None, "work_high",
              1, card="xyleus"),
            T("farmer", "athens.farmer", "Farmer of Elis", "valley", None, "work_low", 2)],
        "chain": C("olympia_poplar", "White poplar for the ash altar", "node:olympia_n",
                   "world.goods_firewood", "node:altis", "priest", by=("woodman", "wood_carrier"),
                   period=300, hours=("06:00", "17:00"),
                   labels=("white poplar cut in the valley", "carried into the Altis",
                           "burnt on the altar of ash")),
        "market": None, "round": ["olympia_n", "altis"],
        "cards": {"xyleus": card("role", "Xyleus", "", "Pausanias says a woodman supplied the "
                                 "white poplar used for every sacrifice to Zeus at Olympia, and "
                                 "no other wood.")},
    },
    "sparta": {
        "areas": {"valley": "country", "villages": "country"},
        "trades": [
            T("helot", "athens.farmer", "Helot at the plough", "valley", None, "work_low", 4,
              card="helot"),
            T("spartiate", "athens.spartan", "Spartiate at exercise", "villages", None, "idle", 2,
              [("06:00", "11:00"), ("15:00", "18:00")]),
            T("boy", "athens.child", "Boy of the agoge", "villages", None, "run", 2,
              [("06:00", "11:00"), ("15:00", "18:00")], card="agoge")],
        "chain": C("sparta_mess", "Barley for the common mess", "athens.g_house_small.beside",
                   "world.goods_sacks", "node:sparta_shrine", "spartiate",
                   by=("helot", "mess_porter"), period=300,
                   labels=("barley grown by helots", "carried to the mess",
                           "shared at the common meal")),
        "market": None, "round": ["sparta_e", "sparta_shrine"],
        "cards": {"helot": card("role", "Helot", "", "The land of Sparta was worked by helots, "
                                "an unfree people bound to it, who gave half its yield to their "
                                "Spartan masters."),
                  "agoge": card("role", "Agoge", "", "Spartan boys left home at seven for the "
                                "agoge, a hard common training in packs under older youths."),
                  "sparta_mess": card("idea", "Syssitia", "The common meals",
                                      "Every Spartiate ate in a mess of about fifteen men and "
                                      "paid his share each month in barley, wine, cheese and "
                                      "figs, Plutarch says. A man who could not pay lost his "
                                      "full rights. The famous black broth was eaten there.")},
    },
    "corinth": {
        "areas": {"acrocorinth": "wild", "harbours": "country", "land": "country",
                  "town": "town"},
        "trades": [
            T("hauler", "athens.enslaved_man", "Hauler on the diolkos", "harbours",
              {"node": "kenchreai"}, "haul", 4, card="diolkos_hauler"),
            T("potter", "athens.potter", "Potter", "town", {"item": "athens.g_house_small"},
              "throw", 2),
            T("sailor", "world.sailor", "Sailor", "harbours", {"node": "lechaion"}, "haul", 3),
            T("farmer", "athens.farmer", "Farmer", "land", None, "work_low", 3)],
        "chain": C("corinth_diolkos", "Cargo across the isthmus", "node:lechaion",
                   "world.goods_amphorae", "node:kenchreai", "sailor", by=("sailor", "hauler"),
                   period=240, labels=("a cargo unloaded at Lechaion", "hauled over the "
                                       "diolkos", "loaded again at Kenchreai")),
        "market": 2, "round": ["corinth_temple", "lechaion", "kenchreai"],
        "cards": {"diolkos_hauler": card("role", "Hauler", "", "Gangs dragged cradles with "
                                         "cargoes, and sometimes whole ships, over the paved "
                                         "diolkos.")},
    },
    "delos": {
        "areas": {"island": "wild", "kynthos": "wild", "sanctuary": "country", "sea": "wild"},
        "trades": [
            T("priest", "athens.priest", "Priest of Apollo", "sanctuary", {"node": "lions"},
              "pray", 2, [("06:00", "11:00"), ("15:00", "18:30")]),
            T("boatman", "world.sailor", "Boatman", "island", {"node": "delos_harbour"}, "haul",
              2, EARLY)],
        "chain": C("delos_gifts", "Gifts for Apollo", "node:delos_harbour",
                   "world.goods_gift_vessels", "node:lions", "priest", by=("boatman", "gift_bearer"),
                   period=300, labels=("a gift landed from a pilgrim ship", "carried up to the "
                                       "sanctuary", "dedicated to the god")),
        "market": None, "round": ["delos_harbour", "lions"],
        "seasonal_area": {"sanctuary": {"area": "wild", "months": ["nov", "dec", "jan", "feb",
                                                                   "mar"]}},
        "cards": {},
    },
    "ephesus": {
        "areas": {"artemision": "country", "harbour": "country", "town": "town"},
        "trades": [
            T("temple_servant", "athens.priest", "Servant of Artemis", "artemision",
              {"node": "artemision"}, "pray", 2, [("06:00", "11:00"), ("15:00", "18:30")]),
            T("mason", "athens.mason", "Mason on the temple", "artemision",
              {"node": "artemision"}, "work_high", 2),
            T("docker", "athens.rower", "Docker", "harbour", {"node": "ephesus_harbour"}, "haul",
              3),
            T("shopkeeper", "athens.ionian", "Ionian shopkeeper", "town",
              {"item": "athens.g_house_small"}, "talk", 2)],
        "chain": C("ephesus_offerings", "Cargo for the temple", "node:ephesus_harbour",
                   "world.goods_amphorae", "node:artemision", "temple_servant",
                   by=("docker", "temple_porter"), period=240,
                   labels=("oil and wine landed at the harbour", "carried across the plain",
                           "stored for Artemis")),
        "market": 3, "round": ["ephesus_town", "ephesus_harbour", "artemision"],
        "cards": {},
    },
    "sardis": {
        "areas": {"acropolis": "wild", "mounds": "wild", "town": "town", "valley": "country"},
        "trades": [
            T("gold_washer", "parsa.labourer", "Gold washer on the Paktolos", "valley",
              {"node": "paktolos"}, "haul", 3, card="paktolos"),
            T("scribe", "parsa.scribe", "Scribe of the satrap", "town",
              {"node": "sardis_station"}, "write", 1),
            T("groom", "parsa.groom", "Groom at the station", "town", {"node": "sardis_station"},
              "stir", 2, LONG),
            T("weaver", "parsa.woman_worker", "Weaver", "town", {"item": "parsa.p_house_small"},
              "stir", 2)],
        "chain": C("sardis_gold", "Gold dust of the Paktolos", "node:paktolos", "world.goods_silver",
                   "node:sardis_station", "scribe", by=("gold_washer", "gold_carrier"),
                   period=300, labels=("gold dust washed from the river sand",
                                       "carried up to the town", "weighed and recorded")),
        "market": 0, "round": ["sardis_w", "sardis_station", "sardis_e"],
        "cards": {"paktolos": card("role", "Gold washer", "", "The Paktolos brought gold dust "
                                   "down from Mount Tmolos, Herodotus says; it made Lydia's "
                                   "kings rich.")},
    },
    "halys": {
        "areas": {"crossing": "country", "road": "road"},
        "trades": [
            T("gate_guard", "parsa.guard_spear", "Guard at the gates", "crossing",
              {"node": "halys_station"}, "guard", 2, LONG, card="halys_guard"),
            T("groom", "parsa.groom", "Groom at the station", "crossing",
              {"item": "world.royal_station"}, "stir", 2, LONG)],
        "chain": None,
        "market": None, "round": ["halys_w", "halys_station", "halys_e"],
        "cards": {"halys_guard": card("role", "Guard", "", "Travellers on the Royal Road were "
                                      "stopped at the gates of the Halys and their documents "
                                      "checked.")},
    },
    "gordion": {
        "areas": {"citadel": "town", "plain": "country"},
        "trades": [
            T("weaver", "parsa.woman_worker", "Weaver", "citadel", {"item": "parsa.p_house_small"},
              "stir", 3, card="gordion_weaver"),
            T("shepherd", "parsa.shepherd", "Shepherd", "plain", None, "gesture", 2,
              [("05:30", "19:00")]),
            T("farmer", "parsa.farmer", "Farmer by the Sangarios", "plain", None, "work_low", 2),
            T("worshipper", "parsa.woman_worker", "Worshipper of Matar", "citadel",
              {"item": "world.matar_shrine"}, "idle", 1, [("07:00", "10:00"), ("16:00", "18:00")])],
        "chain": C("gordion_wool", "Wool for the looms", "node:gordion_s", "world.goods_fleece",
                   "node:gordion_citadel", "weaver", by=("shepherd", "wool_carrier"), period=300,
                   labels=("fleece from the flocks on the plain", "carried up to the citadel",
                           "spun and woven")),
        "market": 2, "round": ["gordion_s", "gordion_citadel"],
        "cards": {"gordion_weaver": card("role", "Weaver", "", "Thousands of clay loom weights "
                                         "found at Gordion show how much cloth its houses "
                                         "wove.")},
    },
    "euphrates_crossing": {
        "areas": {"crossing": "country", "river": "wild"},
        "trades": [
            T("ferryman", "parsa.labourer", "Ferryman", "crossing", {"node": "west_landing"},
              "haul", 3, card="quffa"),
            T("groom", "parsa.groom", "Groom at the station", "crossing",
              {"node": "euph_station"}, "stir", 2, LONG)],
        "chain": C("euphrates_loads", "Loads over the river", "node:west_landing",
                   "world.goods_sacks", "node:euph_station", "groom", by=("ferryman", "porter"),
                   period=240, labels=("a load ferried across", "carried up to the station",
                                       "packed on the beasts")),
        "market": None, "round": ["west_bridge", "euph_station", "east_bridge"],
        "cards": {"quffa": card("role", "Ferryman", "", "Round boats of skins on a frame of "
                                "willow, Herodotus says, carried loads down and across the "
                                "Euphrates.")},
    },
    "sidon": {
        "areas": {"shore": "country", "town": "town"},
        "trades": [
            T("shipwright", "parsa.craftsman", "Shipwright", "shore", {"node": "sidon_quay"},
              "work_high", 3, card="sidon_ships"),
            T("dyer", "parsa.woman_worker", "Purple dyer", "shore", None, "stir", 2,
              card="purple"),
            T("fisher", "world.fisher", "Fisherman", "shore", {"node": "sidon_quay"}, "haul", 2,
              EARLY),
            T("merchant", "world.merchant", "Phoenician merchant", "town",
              {"item": "parsa.p_house_small"}, "talk", 2)],
        "chain": C("sidon_cedar", "Cedar for the ships", "node:sidon_n", "world.goods_logs",
                   "node:sidon_quay", "shipwright", by=("logger", "log_hauler"), period=300,
                   labels=("cedar brought down from the mountains", "hauled to the strand",
                           "worked into hulls")),
        "market": 1, "round": ["sidon_n", "sidon_quay"],
        "cards": {"sidon_ships": card("role", "Shipwright", "", "Sidon's ships were the best "
                                      "in Xerxes' fleet, Herodotus says, and its king sat next "
                                      "to the Great King."),
                  "purple": card("role", "Dyer", "", "Phoenician dyers boiled sea snails for "
                                 "the purple that made their cloth famous, and their beaches "
                                 "stank of it.")},
    },
    "babylon": {
        "areas": {"east_bank": "town", "groves": "country", "west_bank": "country"},
        "trades": [
            T("scribe", "parsa.scribe", "Scribe of a temple household", "east_bank",
              {"node": "etemenanki_court"}, "write", 2, card="babylon_scribe"),
            T("brickmaker", "parsa.labourer", "Brickmaker", "west_bank", None, "work_low", 3),
            T("boatman", "parsa.labourer", "Boatman", "east_bank", {"node": "babylon_quay"},
              "haul", 2),
            T("gardener", "parsa.gardener", "Gardener in the palm groves", "groves",
              {"item": "parsa.t_date"}, "work_low", 2),
            T("craftsman", "parsa.craftsman", "Craftsman", "east_bank",
              {"item": "parsa.p_house_small"}, "stir", 3)],
        "chain": C("babylon_dates", "Dates for the river boats", "parsa.t_date.beside",
                   "world.goods_dates", "node:babylon_quay", "boatman",
                   by=("gardener", "date_porter"), period=240,
                   labels=("dates picked in the groves", "carried to the quay",
                           "loaded on the boats")),
        "market": 3, "round": ["ishtar_gate", "etemenanki_court", "babylon_quay"],
        "cards": {"babylon_scribe": card("role", "Scribe", "", "Babylon's temples and "
                                         "business houses kept their accounts in cuneiform on "
                                         "clay, and thousands of tablets survive.")},
    },
    "susa": {
        "areas": {"citadel": "country", "plain": "country", "town": "town"},
        "trades": [
            T("scribe", "parsa.scribe", "Scribe", "citadel", {"node": "palace_steps"}, "write", 2),
            T("guard", "parsa.guard_spear", "Palace guard", "citadel", {"node": "palace_steps"},
              "guard", 2, LONG),
            T("craftsman", "parsa.elamite", "Elamite craftsman", "town",
              {"item": "parsa.p_house_small"}, "talk", 3),
            T("boatman", "parsa.labourer", "Boatman", "plain", {"node": "susa_quay"}, "haul", 2)],
        "chain": C("susa_rations", "Barley rations", "node:susa_quay", "world.goods_sacks",
                   "node:palace_steps", "scribe", by=("boatman", "ration_porter"), period=240,
                   labels=("barley landed at the river quay", "carried up the mound",
                           "issued as rations and recorded")),
        "market": 0, "round": ["susa_town", "palace_steps", "susa_quay"],
        "cards": {},
    },
    "persian_gates": {
        "areas": {"cliffs": "wild", "road": "road"},
        "trades": [
            T("guard", "parsa.guard_spear", "Guard of the pass", "road",
              {"node": "gates_guardpost"}, "guard", 2, LONG),
            T("archer", "parsa.archer", "Archer on watch", "road", {"node": "gates_guardpost"},
              "idle", 1, LONG)],
        "chain": None,
        "market": None, "round": ["gates_w", "gates_guardpost", "gates_e"],
        "cards": {},
    },
    "pasargadae": {
        "areas": {"garden": "country", "plain": "country", "tomb": "country"},
        "trades": [
            T("gardener", "parsa.gardener", "Gardener of the paradise", "garden",
              {"node": "pasargadae_garden"}, "work_low", 3),
            T("magus", "parsa.magus", "Magus keeping the tomb", "tomb", {"node": "cyrus_tomb"},
              "pray", 1, LONG),
            T("shepherd", "parsa.shepherd", "Shepherd", "plain", None, "gesture", 2,
              [("05:30", "19:00")])],
        "chain": C("pasargadae_rations", "The magi's rations", "node:pasargadae_s",
                   "world.goods_flour", "node:cyrus_tomb", "magus", by=("miller", "flour_carrier"),
                   period=300, labels=("flour from the plain", "carried to the tomb",
                                       "the magi's daily ration (Arrian 6.29)")),
        "market": None, "round": ["pasargadae_s", "pasargadae_garden", "cyrus_tomb"],
        "cards": {},
    },
}

# What each town's year holds besides its market days: (season months, hour, name, cast,
# animation, sfx, string). Cast entries are (role or actor, count).
SEASON_EVENTS = {
    "rome": [("spring", ["apr", "may"], "07:00", "ploughing_out", [("folk", 3), ("rome.ox", 1)],
              "work_low", "sfx/world/step_earth_1.wav", "The plough teams go out at first light."),
             ("summer", ["jul", "aug"], "18:30", "evening_cool", [("folk", 6)], "talk",
              "sfx/world/vendor.wav", "Neighbours sit out in the evening cool."),
             ("autumn", ["sep", "oct"], "08:00", "vintage", [("folk", 5), ("woman", 2)],
              "work_low", "sfx/world/pour.wav", "The vintage: baskets of grapes go to the vats."),
             ("winter", ["dec"], "17:00", "saturnalia", [("folk", 6), ("woman", 3)], "talk",
              "sfx/rome/tibia.wav", "The Saturnalia: gifts, games and shouts of 'Io Saturnalia!'")],
    "athens": [("spring", ["mar", "apr"], "08:00", "shearing", [("folk", 3), ("world.sheep", 4)],
                "work_low", "sfx/world/sheep_bells.wav", "Shearing time: the flocks come in."),
               ("summer", ["jun", "jul"], "07:00", "threshing", [("folk", 4)], "work_low",
                "sfx/world/sickle.wav", "The threshing floors are busy from dawn."),
               ("autumn", ["sep"], "08:00", "vintage", [("folk", 5), ("woman", 2)], "work_low",
                "sfx/world/pour.wav", "The vintage: the grapes are trodden in the vats."),
               ("winter", ["dec", "jan"], "16:30", "rural_dionysia", [("folk", 8), ("woman", 3)],
                "idle", "sfx/athens/aulos.wav",
                "The country Dionysia: a procession with songs, a goat and the aulos.")],
    "parsa": [("spring", ["mar", "apr"], "08:00", "shearing", [("folk", 3), ("world.sheep", 4)],
               "work_low", "sfx/world/sheep_bells.wav", "Shearing time: wool for the looms."),
              ("summer", ["jun", "jul", "aug"], "05:30", "early_market", [("folk", 6), ("woman", 3)],
               "talk", "sfx/world/vendor.wav", "The market opens at dawn, before the heat."),
              ("autumn", ["sep", "oct"], "08:00", "harvest_in", [("folk", 4)], "carry",
               "sfx/world/step_earth_2.wav", "The harvest is carried in to the stores."),
              ("winter", ["dec", "jan", "feb"], "17:00", "winter_fires", [("folk", 5)], "idle",
               "amb/world/hearth.ogg", "Fires in the doorways against the cold evening.")],
}


# -- the document --------------------------------------------------------------------------------

def _steps_at(target, anim, work=(30, 60)) -> list[dict]:
    if target is None:
        return [{"wander": {"radius": 5}, "dur": [15, 30]},
                {"use": {"here": True}, "anim": anim, "dur": list(work)}]
    if "item" in target:
        go = {"go": {"item": target["item"], "spot": "beside", "within": 40}}
    else:
        go = {"go": {"node": target["node"]}}
    return [go, {"use": {"here": True}, "anim": anim, "dur": list(work)},
            {"wander": {"radius": 3}, "dur": [10, 20]},
            {"use": {"here": True}, "anim": anim, "dur": [work[0] // 2, work[1] // 2]}]


def _sched(hours, routine="work", months=None) -> list[dict]:
    out = []
    for a, b in hours:
        blk = {"hours": [a, b], "routine": routine}
        if months:
            blk["months"] = list(months)
        out.append(blk)
    return out


def _anim(kinds, actor, want):
    have = kinds.get(actor)
    return want if have is None or want in have else "idle"


def _pop(role, count, tiles, density="always", **kw) -> dict:
    return {"role": role, "density": density,
            "max_per_chunk": round(count * CHUNK_TILES / max(1, tiles), 2), **kw}


def _need(area: str, tiles: int) -> float:
    """Visible people a district needs for its area's movers per screenful."""
    return AREA[area]["min"] * tiles / (MOVING * SCREEN_TILES)


# Seasonal events that are the land's work: their months follow the town's climate.
WORK_OF = {"shearing": "shearing", "threshing": "threshing", "ploughing_out": "ploughing",
           "vintage": "vintage", "harvest_in": "harvest"}


def build(rid: str, set_: str, tiles: dict[str, int], placed: set[str], nodes: set[str],
          factors: list[float], kinds: dict, visitor: str, work: dict | None = None) -> dict:
    """Roles, districts, chains, events, cards and strings of one town. `tiles` is its districts'
    sizes, `placed` the item ids its layer holds, `nodes` its graph's named nodes, `factors` its
    twelve month factors (seasonlife.TOWN_SEASONS), `kinds` the actor kinds' animations,
    `visitor` the walker kind that strolls its streets, `work` its climate's work months."""
    spec = TOWNS[rid]
    H = HOUSEHOLD[set_]
    roles, pops = [], {d: [] for d in tiles}
    areas = spec["areas"]
    work_d = {}
    def area_in(d, m):
        sa = spec.get("seasonal_area", {}).get(d)
        return sa["area"] if sa and m in sa["months"] else areas[d]

    # The most people a district may hold (all present, out or indoors) in every month, its
    # counts scaled by the month's factor: under its area's cap per chunk, with a margin.
    room = {d: min(AREA[area_in(d, m)]["cap"] * n / SCREEN_TILES * 0.85 / f
                   for m, f in zip(ALL, factors) if f > 0) for d, n in tiles.items()}
    asked = {}
    for t in spec["trades"]:
        asked[t["district"]] = asked.get(t["district"], 0) + t["count"]
    # Townsfolk enough for every district's area in its leanest month (the town's seasons
    # scale every population by month), with a margin.
    need = {d: max((_need(area_in(d, m), n) * 1.1 / f for m, f in zip(ALL, factors) if f > 0),
                   default=0.0) for d, n in tiles.items()}

    def night_room(d):
        return AREA[areas[d]]["night"] * tiles[d] / (MOVING * SCREEN_TILES)
    # The watch walks in the largest district its night allows one in (a few people per
    # screenful at night at most).
    homes = [d for d in tiles if areas[d] not in ("wild", "sea") and night_room(d) >= 1.1]
    watch_d = {max(homes, key=lambda d: (tiles[d], d))} if homes else set()
    watch_d |= {d for d in homes if areas[d] == "town" and night_room(d) >= 2.2}
    watch_n = {d: (1 if night_room(d) < 2.2 else 2) if d in watch_d else 0 for d in tiles}
    for t in spec["trades"]:
        anim = _anim(kinds, t["actor"], t["anim"])
        tgt = t["target"]
        if tgt and "item" in tgt and tgt["item"] not in placed:
            tgt = None
        if tgt and "node" in tgt and tgt["node"] not in nodes:
            tgt = None
        r = {"id": t["id"], "actor": t["actor"], "name": t["name"],
             "schedule": _sched(t["hours"], months=t["months"]),
             "routines": {"work": {"loop": True, "steps": _steps_at(tgt, anim)}}}
        if t.get("card"):
            r["card"] = t["card"]
        roles.append(r)
        if t["district"] in pops:
            d = t["district"]
            # Trades share what the townsfolk and the watch leave of the district's room, at
            # most half of it: a small district gets fewer hands.
            free = max(0.25 * asked[d], min(0.5 * room[d], room[d] - need[d] - watch_n[d]))
            cnt = round(t["count"] * min(1.0, free / asked[d]), 2)
            when = {"months": t["months"]} if t["months"] else {}
            pops[d].append(_pop(t["id"], cnt, tiles[d], **({"when": when} if when else {})))
            work_d[d] = work_d.get(d, 0) + cnt
    named = [n for n in spec["round"] if n in nodes]
    folk, woman, child, watch = H["folk"], H["woman"], H["child"], H["watch"]
    errands = [{"go": {"node": n}} if n else {"wander": {"radius": 6}, "dur": [20, 30]}
               for n in (named[:3] or [None])]
    steps = []
    for g in errands:
        steps += [g, {"use": {"here": True}, "anim": _anim(kinds, folk, "talk"), "dur": [20, 40]},
                  {"wander": {"radius": 4}, "dur": [15, 30]}]
    roles.append({"id": "townsfolk", "actor": folk, "name": "Townsfolk on their errands",
                  "schedule": [{"hours": ["06:00", "18:30"], "routine": "errands"},
                               {"hours": ["18:30", "21:30"], "routine": "evening"}],
                  "routines": {"errands": {"loop": True, "steps": steps},
                               "evening": {"loop": True, "steps": [
                                   {"wander": {"radius": 3}, "dur": [10, 20]},
                                   {"use": {"here": True}, "anim": _anim(kinds, folk, "sit"),
                                    "dur": [40, 80]}]}}})
    well = H["well"] if H["well"] in placed else None
    roles.append({"id": "water_carrier", "actor": woman, "name": "Fetching water",
                  "schedule": [{"hours": ["06:00", "09:30"], "routine": "water"},
                               {"hours": ["16:30", "19:00"], "routine": "water"}],
                  "routines": {"water": {"loop": True, "steps": _steps_at(
                      {"item": well} if well else None, _anim(kinds, woman, "carry_idle"),
                      (20, 40))}}})
    roles.append({"id": "child", "actor": child, "name": "Children at play",
                  "schedule": [{"hours": ["08:00", "12:00"], "routine": "play"},
                               {"hours": ["15:00", "18:30"], "routine": "play"}],
                  "routines": {"play": {"loop": True, "steps": [
                      {"wander": {"radius": 5}, "dur": [15, 30]},
                      {"use": {"here": True}, "anim": _anim(kinds, child, "run"), "dur": [10, 20]}]}}})
    watch_steps = []
    for n in named or [None]:
        watch_steps += [{"go": {"node": n}} if n else {"wander": {"radius": 6}, "dur": [30, 60]},
                        {"use": {"here": True}, "anim": _anim(kinds, watch, "guard"),
                         "dur": [40, 80]}]
    roles.append({"id": "night_watch", "actor": watch, "name": "The night watch",
                  "schedule": [{"hours": ["19:30", "06:00"], "routine": "round"}],
                  "routines": {"round": {"loop": True, "steps": watch_steps}}})
    # Then the household roles, while the district stays under its room.
    for d, n in tiles.items():
        a = areas[d]
        if a in ("sea", "wild"):
            # Cliffs, mounds, slivers of island and water: birds only.
            bird = "world.gull" if a == "sea" or d in ("sea", "harbour", "shore", "river") \
                else "world.raven"
            pops[d].append({"actor": bird, "density": "daytime",
                            "max_per_chunk": round(min(0.6, room[d] * 0.5) * CHUNK_TILES / n, 2)})
            continue
        cap_total = room[d]
        used = work_d.get(d, 0) + watch_n[d]
        if need[d] > 0:
            folk_n = round(max(0.5, need[d]), 2)
            pops[d].append(_pop("townsfolk", folk_n, n, "town_day"))
            used += folk_n
        extras = [("night_watch", watch_n[d], "night", True)] if watch_n[d] else []
        if a in ("town", "country"):
            extras += [("water_carrier", 1 if n < 300 else 2, "always", False),
                       ("child", 1 if n < 300 else 2, "always", False)]
        if a in ("town", "country", "road"):
            extras.append((visitor, 0.6 if n < 300 else 1.2, "daytime", False))
        extras.append(("world.dog", 0.5 if n < 300 else 1, "always", False))
        for key, cnt, dens, always in extras:
            if not always:
                if used + cnt > cap_total:
                    continue
                used += cnt
            if "." in key:
                pops[d].append({"actor": key, "density": dens,
                                "max_per_chunk": round(cnt * CHUNK_TILES / n, 2)})
            else:
                pops[d].append(_pop(key, cnt, n, dens))
    districts = []
    for d in tiles:
        e = {"id": d, "area": areas[d], "populations": pops[d]}
        if d in spec.get("seasonal_area", {}):
            e["seasonal_area"] = spec["seasonal_area"][d]
        districts.append(e)
    doc = {"districts": districts, "roles": roles, "chains": [], "events": [],
           "cards": dict(spec["cards"]), "strings": {}}
    _chain(doc, spec, set_, kinds, placed, nodes)
    _events(doc, rid, spec, set_, H, tiles, placed, named, kinds, work or {})
    return doc


def _chain(doc, spec, set_, kinds, placed, nodes):
    c = spec.get("chain")
    if not c:
        return
    src_item = c["source"].rpartition(".")[0]
    if not c["source"].startswith("node:") and src_item not in placed:
        return
    maker, carrier = c["by"]
    have = {r["id"] for r in doc["roles"]}
    H = HOUSEHOLD[set_]
    hours = [tuple(c["hours"])]
    for rid, actor, anim in ((maker, H["folk"], "work_low"), (carrier, H["folk"], "carry"),
                             (c["sink_by"], H["keeper"], "serve")):
        if rid in have:
            continue
        doc["roles"].append({"id": rid, "actor": actor, "name": rid.replace("_", " ").capitalize(),
                             "schedule": _sched(hours),
                             "routines": {"work": {"loop": True, "steps": [
                                 {"wander": {"radius": 3}, "dur": [10, 20]},
                                 {"use": {"here": True}, "anim": _anim(kinds, actor, anim),
                                  "dur": [20, 40]}]}}})
        have.add(rid)
    a, b, s = c["labels"]
    doc["chains"].append({"id": c["id"], "name": c["name"], "period": c["period"],
                          "hours": c["hours"], "stages": [
                              {"slot": c["source"], "makes": c["goods"], "by": maker, "label": a},
                              {"carry": c["goods"], "from": c["source"], "to": c["to"],
                               "by": carrier, "label": b},
                              {"slot": c["to"], "sink": c["goods"], "by": c["sink_by"],
                               "label": s}]})
    # Its workers must be out whenever it runs: chain hours inside every worker's schedule.
    for r in doc["roles"]:
        if r["id"] in (maker, carrier, c["sink_by"]):
            for blk in r["schedule"]:
                blk.pop("months", None)
            if not any(blk["hours"][0] <= c["hours"][0] and blk["hours"][1] >= c["hours"][1]
                       for blk in r["schedule"]):
                r["schedule"].insert(0, {"hours": list(c["hours"]), "routine": "work"})


def _ev(id_, size, trigger, duration, cast, steps, sfx, string=None, **kw):
    e = {"id": id_, "rarity": kw.pop("rarity", "common"), "size": size, "trigger": trigger,
         "duration": list(duration), "cast": cast, "steps": steps}
    if sfx.endswith(".ogg"):
        e["ambience"] = {"file": sfx, "gain": 0.6}
    else:
        e["sfx"] = sfx
    if string:
        e["string"] = string
    e.update(kw)
    return e


def _events(doc, rid, spec, set_, H, tiles, placed, named, kinds, work):
    evs, strings = doc["events"], doc["strings"]
    main = next((d for d, a in spec["areas"].items() if a == "town"), None) or \
        next((d for d, a in spec["areas"].items() if a == "country"), None) or next(iter(tiles))
    folk, woman = H["folk"], H["woman"]
    kinds_of = {"folk": folk, "woman": woman}
    if spec.get("market") is not None:
        evs.append(_ev("market_day", "medium",
                       {"on": "window", "hours": ["07:30", "08:00"], "chance": 1.0,
                        "days": {"every": 4, "offset": spec["market"]}},
                       (200, 260), [{"actor": folk, "count": 6}, {"actor": woman, "count": 4},
                                    {"actor": "world.merchant", "count": 2}],
                       [{"go": {"node": named[0]}} if named else {"wander": {"radius": 6},
                                                                   "dur": [20, 30]},
                        {"use": {"here": True}, "anim": "idle", "dur": [60, 90]},
                        {"wander": {"radius": 5}, "dur": [40, 60]}],
                       "sfx/world/vendor.wav", "market_day", zone=main,
                       ambience={"file": {"rome": "amb/world/crowd_latin_1.ogg",
                                          "athens": "amb/world/crowd_greek_1.ogg",
                                          "parsa": "amb/world/crowd_persian_1.ogg"}[set_],
                                 "gain": 0.5}))
        strings["market_day"] = "Market day: stalls, voices and goods from the country around."
        evs.append(_ev("market_rain", "small",
                       {"on": "weather", "kind": "rain", "days": {"every": 4,
                                                                  "offset": spec["market"]}},
                       (60, 90), [{"actor": folk, "count": 4}],
                       [{"go": {"node": named[0]}} if named else {"wander": {"radius": 4},
                                                                   "dur": [10, 20]},
                        {"use": {"here": True}, "anim": "idle", "dur": [30, 50]}],
                       "amb/world/rain_roof_1.ogg", "market_rain", zone=main))
        strings["market_rain"] = "Rain: the stallholders cover their goods and wait under the eaves."
    lamps = [x for x in H["lamps"] if x in placed]
    if lamps:
        evs.append(_ev("lamps_lit", "small", {"on": "window", "hours": ["19:00", "19:30"],
                                              "chance": 1.0}, (60, 60),
                       [{"role": "night_watch", "count": 1}],
                       [{"each": {"item": it, "within": 64}, "state": "lit", "every": 4}
                        for it in lamps], "sfx/world/lamp.wav", "lamps_lit", zone=main,
                       rarity="daily"))
        strings["lamps_lit"] = "Dusk: the lamps are lit along the street."
    weds = H["wedding"]
    evs.append(_ev("wedding", "medium", {"on": "window", "hours": ["17:00", "17:30"],
                                         "chance": 0.25, "months": weds},
                   (150, 200), [{"actor": folk, "count": 6}, {"actor": woman, "count": 4}],
                   [{"wander": {"radius": 6}, "dur": [40, 60]},
                    {"use": {"here": True}, "anim": "idle", "dur": [60, 90]}],
                   "sfx/world/wedding_song.wav", "wedding", zone=main, rarity="uncommon"))
    strings["wedding"] = "A wedding: the bride is led to her new home with torches and songs."
    for season, months, hour, eid, cast, anim, sfx, line in SEASON_EVENTS[set_]:
        if eid in WORK_OF:
            have = work.get(WORK_OF[eid])
            if not have:
                continue    # no such work in this climate
            months = [m for m in months if m in have] or list(have)
        h0, m0 = (int(x) for x in hour.split(":"))
        end = f"{h0:02d}:{m0 + 30:02d}" if m0 < 30 else f"{h0 + 1:02d}:{m0 - 30:02d}"
        actors = [kinds_of.get(k, k) for k, _ in cast]
        if not all(anim in kinds.get(x, ()) for x in actors):
            anim = "idle"
        evs.append(_ev(eid, "small", {"on": "window", "hours": [hour, end], "chance": 0.6,
                                      "months": months},
                       (120, 180), [{"actor": x, "count": n} for x, (_, n) in zip(actors, cast)],
                       [{"wander": {"radius": 6}, "dur": [30, 50]},
                        {"use": {"here": True}, "anim": anim, "dur": [60, 90]}], sfx, eid,
                       zone=main))
        strings[eid] = line
    for e in spec.get("events", []):
        evs.append(e)
