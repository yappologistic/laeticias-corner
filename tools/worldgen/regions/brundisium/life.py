"""Brundisium in April AD 126: the harbour at the end of the Via Appia, where travellers and goods
take ship for Greece across the Ionian Sea (`assets/regions/brundisium.json`). Dockers load wine
and oil, passengers wait on the quay with their baggage, fishermen land their catch, and
travellers arrive at the column that marks the road's end (the surviving column's date is
debated). Shared Roman roles come from `regions/rome/townlife.py`.

Built by `tools/worldgen/build.sh --city brundisium`, checked by `worldgen.citylife`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from worldgen.citylife import card, go, grid_rect, pop, role, sched, use, wait, wander

_spec = importlib.util.spec_from_file_location(
    "worldgen_life_rome_town", Path(__file__).resolve().parent.parent / "rome" / "townlife.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

R, loop, once, per, ev, window = T.R, T.loop, T.once, T.per, T.ev, T.window


def roles() -> list[dict]:
    X = T.borrow("housewife", "townsman", "child", "errand_slave", "freedwoman", "reveller", "dog", "cat",
                 "shopkeeper", "insula_shop", "counter_keeper", "baker", "smith", "water_carrier", "mourner", "gull")

    def add(*a, **kw):
        X.append(role(*a, **kw))

    add("harbour_docker", R + "docker", "Docker", sched(("05:00", "12:00", "load"), ("13:30", "19:00", "load")),
        {"load": loop(go(item=R + "r_horrea", slot="door", within=12), use(anim="carry_idle", dur=(8, 14)),
                      {"take": R + "goods_wine_amphora"}, go(node="brundisium_quay"), {"put": R + "goods_wine_amphora"},
                      wait(dur=(8, 14)))}, card="docker")
    add("sailor", "world.sailor", "Sailor of a Greek ship", sched(("05:30", "19:00", "ship")),
        {"ship": loop(go(item=R + "brundisium_harbour", spot="beside"), use(anim="haul", dur=(20, 40)),
                      go(node="brundisium_quay"), wander(radius=4, dur=(20, 30)))}, card="crossing_sailor")
    add("passenger", "world.traveller", "Passenger waiting for a ship", sched(("05:30", "18:30", "wait")),
        {"wait": loop(go(node="brundisium_quay"), use(anim="sit", dur=(60, 100)), wander(radius=4, dur=(20, 30)),
                      go(node="brundisium_town"), wait(dur=(20, 30)))}, card="passenger")
    add("merchant", "world.merchant", "Merchant", sched(("06:30", "12:00", "trade"), ("14:00", "18:00", "trade")),
        {"trade": loop(go(node="brundisium_quay"), use(anim="talk", dur=(30, 50)), go(node="brundisium_town"),
                       use(anim="serve", dur=(15, 25)))}, card="merchant")
    add("fisher", "world.fisher", "Fisherman", sched(("04:30", "11:00", "fish"), ("15:00", "18:30", "fish")),
        {"fish": loop(go(item=R + "brundisium_harbour", spot="beside"), use(anim="haul", dur=(20, 30)),
                      {"take": R + "goods_fish"}, go(item=R + "r_taberna", slot="sell", within=12),
                      {"put": R + "goods_fish"}, use(anim="sit", dur=(20, 30)))}, card="fish_market")
    add("customs", R + "togatus", "Customs officer", sched(("06:30", "12:00", "inspect"), ("14:00", "17:30", "inspect")),
        {"inspect": loop(go(node="brundisium_quay"), use(anim="gesture", dur=(20, 30)), wander(radius=4, dur=(15, 25)))},
        card="customs_officer")
    add("road_traveller", "world.traveller", "Traveller at the road's end", sched(("05:30", "18:30", "arrive")),
        {"arrive": loop(go(node="column"), use(anim="idle", dur=(20, 30)), go(node="brundisium_town"),
                        use(anim="sit", dur=(20, 30)))}, card="cursus_role")
    add("carriage", R + "carriage", "Travelling carriage", sched(("06:00", "17:30", "travel")),
        {"travel": loop(go(node="column"), wait(dur=(40, 60)), go(node="brundisium_town"), wait(dur=(30, 50)))},
        locomotion={"mode": "walk", "speed": 0.8, "network": "roads", "turn_radius": 2}, card="cursus_role")
    return X


def districts() -> list[dict]:
    return [
        {"id": "town", "area": "town", "populations": [
            pop("housewife", "houses", 10), pop("townsman", "day", 8), pop("child", "children", 5),
            pop("errand_slave", "work", 6), pop("freedwoman", "day", 3), pop("reveller", "evening", 3),
            pop("dog", "always", 1), pop("cat", "always", 1),
            per("shopkeeper", "r_taberna", 1, "market"), per("counter_keeper", "r_thermopolium", 1, "evening_shop"),
            per("insula_shop", "r_insula", 1, "market"), per("baker", "r_bakery", 1, "dawn_work"),
            per("smith", "r_smithy", 1, "work"), per("water_carrier", "r_lacus", 1, "houses"),
            per("mourner", "r_tomb", 1, "day"), pop("passenger", "day", 4), pop("merchant", "day", 3)]},
        {"id": "harbour", "area": "centre", "populations": [
            pop("harbour_docker", "harbour", 24), pop("sailor", "harbour", 10), pop("passenger", "day", 10),
            pop("merchant", "day", 6), pop("fisher", "harbour", 6), pop("customs", "work", 3),
            pop("gull", "birds", 6), pop("cat", "always", 1)]},
        {"id": "road", "area": "road", "populations": [
            pop("road_traveller", "road", 12), pop("carriage", "road", 2), pop("dog", "always", 1)]},
        {"id": "sea", "area": "sea", "populations": [pop("gull", "birds", 12)]},
    ]


def chains() -> list[dict]:
    m = R + "brundisium_harbour.mooring"
    return [
        {"id": "brundisium_wine", "name": "Wine and oil for Greece", "period": 160, "hours": ["05:00", "18:30"],
         "stages": [
             {"slot": R + "r_horrea.door", "makes": R + "goods_wine_amphora", "by": "harbour_docker",
              "label": "an amphora of Apulian wine from the warehouse"},
             {"carry": R + "goods_wine_amphora", "from": R + "r_horrea.door", "to": m, "by": "harbour_docker",
              "workers": 2},
             {"slot": m, "sink": R + "goods_wine_amphora", "by": "sailor", "label": "stowed aboard a ship for Greece"}]},
        {"id": "brundisium_fish", "name": "Fish", "period": 150, "hours": ["05:00", "12:00"], "stages": [
             {"slot": m, "makes": R + "goods_fish", "by": "fisher", "label": "landed from a fishing boat"},
             {"carry": R + "goods_fish", "from": m, "to": R + "r_taberna.sell", "near": "brundisium_town",
              "by": "fisher"},
             {"slot": R + "r_taberna.sell", "sink": R + "goods_fish", "near": "brundisium_town", "by": "shopkeeper",
              "label": "sold"}]},
    ]


def events() -> list[dict]:
    return [
        ev("ship_departs", "daily", "medium", window(("07:00", "07:30"), 0.7), (100, 120),
           [go(item=R + "brundisium_harbour", spot="beside"), use(anim="idle", dur=(60, 80)),
            {"emit": {"sfx": "sfx/world/rope.wav"}}], zone="harbour",
           cast=[{"role": "passenger", "count": 6, "from": "district"}, {"role": "sailor", "count": 4},
                 {"role": "harbour_docker", "count": 4}], card="crossing", string="ship_departs"),
        ev("ship_arrives", "common", "medium", {"on": "token_arrived", "actor": R + "merchantman"}, (90, 120),
           [go(item=R + "brundisium_harbour", spot="beside"), use(anim="carry_idle", dur=(60, 90), effect="unload")],
           zone="harbour", cast=[{"role": "harbour_docker", "count": 6, "from": "district"}],
           ambience={"file": "amb/world/ship.ogg", "gain": 0.6}, sfx="sfx/world/gull.wav", card="crossing"),
        ev("road_end", "common", "small", window(("08:00", "17:00"), every=1800), (60, 80),
           [go(node="column"), use(anim="idle", dur=(40, 60))], route=["brundisium_town", "column"],
           cast=[{"role": "road_traveller", "count": 3}, {"role": "carriage", "count": 1}], card="appia_end"),
        ev("fishing_fleet", "daily", "small", window(("04:30", "05:00")), (60, 90), [], zone="sea",
           cast=[{"actor": "world.fishing_boat", "count": 2}], sfx="sfx/world/gull.wav"),
        ev("lamps_lit", "daily", "small", window(("18:30", "19:00")), (60, 80),
           [{"each": {"item": R + "r_compitum", "max": 2}, "state": "lit"}], zone="town", sfx="sfx/world/lamp.wav",
           card="compitum"),
        ev("dogs_bark", "common", "small", window(("21:00", "03:00"), every=5400), (5, 6), [], zone="town",
           sfx="sfx/world/dog_far.wav"),
    ]


def cards() -> dict:
    L, I, RO = "landmark", "idea", "role"
    c = {
        "brundisium_harbour": card(L, "Portus Brundisinus", "The harbour for Greece",
            "A branching natural harbour with quays and warehouses, sheltered from the open sea. Here the Via "
            "Appia ends, and ships sail across the Ionian Sea for Greece and the East."),
        "appia_end": card(I, "Finis Viae Appiae", "The road's end",
            "The Via Appia, the 'queen of roads', runs some 540 kilometres from the Porta Capena in Rome to "
            "this harbour. A column marks its end; two stand on the waterfront today, and the date of the "
            "surviving one is debated, so the game shows a simple marker column."),
        "crossing": card(I, "Traiectus", "The crossing to Greece",
            "From Brundisium ships cross the Ionian Sea to Dyrrachium or Apollonia in a day or two with a fair "
            "wind, and travellers go on by the Via Egnatia to the East; others sail round to Corinth. In "
            "winter few ships risk the open sea."),
        "virgil": card(I, "Vergilius", "Virgil's last journey",
            "The poet of the Aeneid fell ill in Greece and died here, at Brundisium, in 19 BC, on his way home "
            "with Augustus. He had asked for the unfinished poem to be burned; Augustus had it published "
            "instead, and it became Rome's own epic."),
        "passenger": card(RO, "Vector", "", "A passenger waits on the quay with his baggage for a ship and a fair "
                          "wind to Greece."),
        "crossing_sailor": card(RO, "Nauta", "", "A sailor of a Greek merchant ship hauls ropes and stows the "
                                "cargo for the crossing."),
        "merchant": card(RO, "Mercator", "", "A merchant bargains on the quay over wine, oil and wool bound for "
                         "the Greek ports."),
        "customs_officer": card(RO, "Portitor", "", "A customs officer checks the cargo and the declaration before "
                                "goods leave the quay."),
        "compitum": T.ROME.role_cards(RO)["compitum"],
    }
    c.update(T.role_cards(roles()))
    return c


def build(view) -> dict:
    return {
        "version": 1, "id": "brundisium", "name": "Brundisium", "native": "Brundisium",
        "caption": "Brundisium · April AD 126", "era": "The Rome of Hadrian · AD 126", "season": "spring",
        "theme": T.theme([{"file": "amb/rome/day.ogg", "hours": ["05:30", "19:30"]},
                          {"file": "amb/rome/night.ogg", "hours": ["19:30", "05:30"]}],
                         [{"rect": grid_rect(view, "harbour"), "file": "amb/world/sea.ogg", "gain": 0.7},
                          {"rect": grid_rect(view, "sea"), "file": "amb/world/sea.ogg", "gain": 0.9}],
                         [{"item": R + "r_lacus", "file": "amb/rome/fountain.ogg", "when": "always"},
                          {"slot": R + "r_smithy.work", "file": "amb/world/smith.ogg", "when": "worked"}],
                         "April showers; the sailing season is open"),
        "densities": T.DENSITIES,
        "districts": districts(),
        "roles": roles(),
        "groups": [],
        "chains": chains(),
        "festivals": [],
        "events": events(),
        "days_shown": [{"day": 0, "label": "A sailing day in April"}],
        "figures": [],
        "lanes_tokens": [{"actor": R + "merchantman", "lane": "brundisium:brundisium", "count": 2},
                         {"actor": "world.fishing_boat", "lane": "brundisium:brundisium", "count": 1}],
        "cards": cards(),
        "strings": {"first_visit": "Brundisium: the Via Appia ends at the harbour, and ships leave for Greece.",
                    "ship_departs": "A ship for Greece is casting off."},
        "journal": ["landmark:*", "chain:*", "idea:*"],
    }
