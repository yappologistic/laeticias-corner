"""Ostia and Portus: a working port's day in April AD 126 (`assets/regions/ostia.json`).

Grain ships from Egypt and Africa moor in Trajan's hexagon and Claudius's outer harbour; dockers
carry the sacks into the warehouses; barges are loaded at the canal and the river quay and towed
up the Tiber to Rome. In the town, shipowners and traders keep offices behind the theatre (most of
the emblem mosaics seen there today are later: fact-check.md §3.1), the Capitolium is new, and the
watch has a station. Salt is raked on the pans by the shore; tombs line the road across the Isola
Sacra. The townsfolk and trades are Rome's (`regions/rome/townlife.py`).

Built by `tools/worldgen/build.sh --city ostia`, checked by `worldgen.citylife`.
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
    X = T.borrow("housewife", "townsman", "child", "errand_slave", "freedwoman", "reveller", "vigil",
                 "dog", "cat", "hen", "shopkeeper", "insula_shop", "counter_keeper", "baker", "fuller",
                 "water_carrier", "stoker", "bather", "gull", "swallow", "shepherd", "sheep", "goat",
                 "mourner")

    def add(*a, **kw):
        X.append(role(*a, **kw))

    add("port_docker", R + "docker", "Docker at Portus", sched(("05:00", "12:00", "unload"), ("13:30", "19:00", "unload")),
        {"unload": loop(go(item=R + "quay", slot="mooring", within=10), use(anim="carry_idle", dur=(8, 14)),
                        {"take": R + "goods_grain_sack"}, go(item=R + "r_horrea", slot="door", within=12),
                        {"put": R + "goods_grain_sack"}, go(node="portus"), wait(dur=(8, 14)))}, card="docker")
    add("barge_loader", R + "enslaved", "Barge loader", sched(("05:30", "12:00", "load"), ("13:30", "18:30", "load")),
        {"load": loop(go(item=R + "r_horrea", spot="beside", within=12), {"take": R + "goods_grain_sack"},
                      go(node="river_quay"), {"put": R + "goods_grain_sack"}, use(anim="work_low", dur=(10, 20)))},
        card="porter")
    add("clerk", R + "freedman", "Warehouse clerk", sched(("06:00", "12:00", "tally"), ("14:00", "18:00", "tally")),
        {"tally": loop(go(node="hexagon_quay"), use(anim="serve", dur=(30, 50)), go(node="portus"),
                       use(anim="talk", dur=(15, 25)))}, card="horrea_clerk")
    add("customs", R + "togatus", "Customs officer", sched(("06:30", "12:00", "inspect"), ("14:00", "17:30", "inspect")),
        {"inspect": loop(go(node="portus"), use(anim="gesture", dur=(20, 30)), go(node="hexagon_quay"),
                         use(anim="talk", dur=(20, 30)))}, card="customs_officer")
    add("shipowner", R + "syrian_merchant", "Shipowner", sched(("07:00", "12:00", "office"), ("14:00", "18:00", "office")),
        {"office": loop(go(node="ostia_guilds"), use(anim="talk", dur=(30, 50)), go(node="ostia_forum"),
                        wander(radius=4, dur=(15, 25)), go(node="river_quay"), use(anim="talk", dur=(15, 25)))},
        card="shipowner")
    add("sailor", R + "egyptian_sailor", "Sailor of the grain fleet", sched(("06:00", "19:00", "ashore")),
        {"ashore": loop(go(node="hexagon_quay"), use(anim="haul", dur=(20, 30)), go(node="portus"),
                        wander(radius=5, dur=(20, 30)), go(node="portus_mole"), wait(dur=(15, 25)))}, card="egypt")
    add("hauler", R + "hauler", "Barge hauler", sched(("05:30", "12:00", "tow"), ("13:30", "18:30", "tow")),
        {"tow": loop(go(node="river_quay"), use(anim="haul", dur=(30, 50)), go(node="tiber_bridge"),
                     use(anim="haul", dur=(30, 50)))}, card="hauler")
    add("fisher", "world.fisher", "Fisherman", sched(("04:30", "11:00", "fish"), ("15:00", "18:30", "fish")),
        {"fish": loop(go(item=R + "quay", slot="mooring", within=12), use(anim="haul", dur=(20, 30)),
                      {"take": R + "goods_fish"}, go(item=R + "r_thermopolium", spot="beside", within=20),
                      {"put": R + "goods_fish"}, use(anim="sit", dur=(20, 30)))}, card="fish_market")
    add("salt_worker", R + "farmer", "Salt raker", sched(("05:30", "11:30", "rake"), ("14:30", "18:30", "rake")),
        {"rake": loop(go(node="salt_pans"), wander(radius=5, dur=(20, 30)), use(anim="work_low", dur=(40, 60)))},
        card="salt")
    add("gardener", R + "farmer", "Market gardener", sched(("05:00", "11:30", "beds"), ("14:30", "19:00", "beds")),
        {"beds": loop(wander(radius=6, dur=(20, 40)), use(anim="work_low", dur=(30, 50)), use(anim="work_high", dur=(15, 25)))},
        card="farmer")
    add("worshipper", R + "citizen", "Worshipper at the Capitolium", sched(("06:00", "12:00", "visit"), ("13:30", "18:30", "visit")),
        {"visit": loop(go(node="ostia_capitolium"), use(anim="idle", dur=(20, 30)), go(node="ostia_forum"),
                       use(anim="talk", dur=(15, 25)), go(node="decumanus"), wait(dur=(10, 20))),
         "shelter": T.shelter_door(12)}, interrupts=[T.RAIN], card="plebs")
    add("theatre_visitor", R + "citizen", "At the theatre", sched(("13:30", "18:00", "watch")),
        {"watch": loop(go(home="visit"), use({"home": "visit"}, anim="sit", dur=(50, 80)), use(anim="talk", dur=(10, 20)))},
        home={"item": R + "ostia_theatre", "slot": "visit"}, card="theatre")
    add("theatre_goer", R + "citizen", "Theatre-goer", sched(("13:30", "18:00", "watch")),
        {"watch": loop(go(node="ostia_theatre"), use(anim="sit", dur=(50, 80)), go(node="ostia_guilds"),
                       use(anim="talk", dur=(15, 25)))}, card="theatre")
    add("keeper", R + "enslaved", "Lighthouse keeper", sched(("17:30", "06:00", "fire")),
        {"fire": loop(go(node="portus_mole"), {"take": "world.goods_firewood"}, wander(radius=3, dur=(20, 30)),
                      {"put": "world.goods_firewood"}, use(anim="work_low", dur=(30, 50)))}, card="lighthouse")
    add("traveller", "world.traveller", "Traveller on the Via Ostiensis", sched(("05:30", "18:30", "travel")),
        {"travel": loop(go(node="porta_romana"), use(anim="sit", dur=(15, 25)), go(node="ostiensis_tombs"),
                        wait(dur=(15, 25)), go(node="decumanus"), wait(dur=(15, 25)))}, card="cursus_role")
    add("road_cart", R + "cart", "Cart for Rome", sched(("19:00", "05:00", "haul"), ("06:00", "18:30", "wait")),
        {"haul": loop(go(node="porta_romana"), go(node="ostiensis_tombs"), wait(dur=(30, 50)), go(node="decumanus")),
         "wait": loop(go(node="ostiensis_tombs"), wait(dur=(80, 140)))},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}, card="night_carts")
    return X


def districts() -> list[dict]:
    homes = [pop("housewife", "houses", 10), pop("townsman", "day", 8), pop("child", "children", 5),
             pop("errand_slave", "work", 6), pop("freedwoman", "day", 3), pop("reveller", "evening", 3),
             pop("dog", "always", 1), pop("cat", "always", 1)]
    return [
        {"id": "town", "area": "town", "populations": homes + [
            per("shopkeeper", "r_taberna", 1, "market"), per("counter_keeper", "r_thermopolium", 1, "evening_shop"),
            per("insula_shop", "r_insula", 1, "market"), per("baker", "r_bakery", 1, "dawn_work"),
            per("fuller", "r_fullonica", 2, "work"), per("water_carrier", "r_lacus", 1, "houses"),
            per("stoker", "r_bath_small", 1, "always"), per("vigil", "r_vigiles", 4, "always"),
            per("theatre_visitor", "ostia_theatre", 2, "afternoon"), pop("theatre_goer", "afternoon", 6),
            pop("bather", "baths", 8), pop("worshipper", "day", 4), pop("shipowner", "day", 6),
            pop("sailor", "day", 3), pop("fisher", "harbour", 2), pop("road_cart", "night", 1)]},
        {"id": "forum", "area": "town", "populations": [
            pop("worshipper", "day", 24), pop("townsman", "day", 10), pop("shipowner", "day", 6),
            pop("child", "children", 4), per("water_carrier", "r_lacus", 1, "houses")]},
        {"id": "portus", "area": "centre", "populations": [
            pop("port_docker", "harbour", 30), pop("barge_loader", "harbour", 8), pop("clerk", "work", 4),
            pop("customs", "work", 3), pop("sailor", "day", 8), pop("shipowner", "day", 3), pop("hauler", "harbour", 3),
            pop("gull", "birds", 6), pop("keeper", "night", 2), pop("cat", "always", 1),
            per("insula_shop", "r_insula", 1, "market")]},
        {"id": "harbour", "area": "sea", "populations": [pop("gull", "birds", 12)]},
        {"id": "river", "area": "sea", "populations": [pop("gull", "birds", 6), pop("swallow", "birds", 6)]},
        {"id": "sea", "area": "sea", "populations": [pop("gull", "birds", 12)]},
        {"id": "isola_sacra", "area": "country", "populations": [
            pop("gardener", "fields", 18), pop("shepherd", "graze", 2), pop("sheep", "graze", 6), pop("dog", "always", 1)]},
        {"id": "fields", "area": "country", "populations": [
            pop("gardener", "fields", 16), pop("shepherd", "graze", 2), pop("sheep", "graze", 8),
            pop("goat", "graze", 2), pop("hen", "day", 2)]},
        {"id": "road", "area": "road", "populations": [
            pop("traveller", "road", 14), per("mourner", "r_tomb", 1, "day"), pop("road_cart", "day", 2)]},
        {"id": "saltpans", "area": "country", "populations": [pop("salt_worker", "fields", 26)]},
    ]


def chains() -> list[dict]:
    q = R + "quay.mooring"
    return [
        {"id": "ostia_grain", "name": "Grain from the ships to the barges", "period": 150, "hours": ["05:00", "18:30"],
         "stages": [
             {"slot": q, "makes": R + "goods_grain_sack", "near": "portus", "by": "port_docker",
              "label": "unloaded from a grain ship"},
             {"carry": R + "goods_grain_sack", "from": q, "to": R + "r_horrea.door", "near": "portus",
              "by": "port_docker", "workers": 2},
             {"carry": R + "goods_grain_sack", "from": R + "r_horrea.door", "to": q, "near": "river_quay",
              "by": "barge_loader", "workers": 2},
             {"slot": q, "sink": R + "goods_grain_sack", "near": "river_quay", "by": "barge_loader",
              "label": "loaded aboard a barge for Rome"}]},
        {"id": "ostia_bread", "name": "Ostia's bread", "period": 140, "hours": ["04:00", "17:00"], "stages": [
             {"slot": R + "r_horrea.door", "makes": R + "goods_grain_sack", "near": "decumanus", "by": "errand_slave",
              "label": "a sack bought from a warehouse"},
             {"carry": R + "goods_grain_sack", "from": R + "r_horrea.door", "to": R + "r_bakery.work",
              "near": "decumanus", "by": "errand_slave", "workers": 2},
             {"slot": R + "r_bakery.work", "needs": R + "goods_grain_sack", "makes": R + "goods_bread",
              "near": "decumanus", "by": "baker", "label": "ground and baked"},
             {"carry": R + "goods_bread", "from": R + "r_bakery.work", "to": R + "r_taberna.sell", "near": "decumanus",
              "by": "baker"},
             {"slot": R + "r_taberna.sell", "sink": R + "goods_bread", "near": "decumanus", "by": "shopkeeper",
              "label": "sold"}]},
        {"id": "ostia_salt", "name": "Salt from the pans", "period": 160, "hours": ["06:00", "18:00"], "stages": [
             {"slot": "node:salt_pans", "makes": "world.goods_salt", "by": "salt_worker",
              "label": "raked up where the sea water has dried"},
             {"carry": "world.goods_salt", "from": "node:salt_pans", "to": R + "r_taberna.sell", "near": "decumanus",
              "by": "errand_slave", "workers": 2},
             {"slot": R + "r_taberna.sell", "sink": "world.goods_salt", "near": "decumanus", "by": "shopkeeper",
              "label": "sold by the measure"}]},
    ]


FESTIVALS = [{"id": "grain_fleet", "season": "spring", "day": 1, "hours": ["06:00", "12:00"]}]


def events() -> list[dict]:
    return [
        ev("grain_fleet", "festival", "large", {"on": "calendar", "festival": "grain_fleet", "hours": ["07:00", "07:30"]},
           (180, 240), [], zone="harbour", cast=[{"actor": R + "merchantman", "count": 3}],
           sfx="sfx/world/gull.wav", card="annona_ships", string="grain_fleet"),
        ev("ship_unloads", "common", "medium", {"on": "token_arrived", "actor": R + "merchantman"}, (90, 120),
           [use(item=R + "quay", slot="mooring", anim="carry_idle", dur=(60, 90), effect="unload"),
            {"emit": {"sfx": "sfx/world/rope.wav"}}], zone="portus",
           cast=[{"role": "port_docker", "count": 6, "from": "district"}, {"role": "clerk", "count": 1}],
           ambience={"file": "amb/world/ship.ogg", "gain": 0.6}, card="annona_ships"),
        ev("customs_check", "common", "small", window(("09:00", "09:30"), 0.5), (60, 80),
           [go(node="portus"), use(anim="gesture", dur=(40, 60))], zone="portus",
           cast=[{"role": "customs", "count": 2}, {"role": "shipowner", "count": 1}], card="portoria"),
        ev("guild_business", "daily", "small", window(("08:00", "08:30")), (90, 110),
           [go(node="ostia_guilds"), use(anim="talk", dur=(70, 90))], zone="town",
           cast=[{"role": "shipowner", "count": 6, "from": "district"}], card="collegia"),
        ev("barges_leave", "common", "small", window(("07:00", "16:00"), every=1800), (90, 110),
           [go(node="tiber_bridge"), use(anim="haul", dur=(60, 80))], route=["river_quay", "tiber_bridge"],
           cast=[{"role": "hauler", "count": 4}], sfx="sfx/world/rope.wav", card="hauler"),
        ev("fishing_fleet", "daily", "small", window(("04:30", "05:00")), (60, 90), [], zone="harbour",
           cast=[{"actor": "world.fishing_boat", "count": 2}], sfx="sfx/world/gull.wav"),
        ev("theatre_show", "common", "medium", window(("15:00", "15:30"), 0.5), (110, 120),
           [go(node="ostia_theatre"), use(anim="sit", dur=(90, 110))], zone="town",
           cast=[{"role": "theatre_goer", "count": 12, "from": "district"}, {"actor": R + "musician", "count": 1}],
           sfx="sfx/rome/tibia.wav", card="theatre"),
        ev("lighthouse_lit", "daily", "small", window(("18:30", "19:00")), (60, 80),
           [go(node="portus_mole"), {"emit": {"fx": "beacon"}}], zone="portus",
           cast=[{"role": "keeper", "count": 1}], glow=True, card="lighthouse", string="lighthouse"),
        ev("funeral", "uncommon", "medium", window(("08:30", "09:00"), 0.25), (100, 115),
           [go(node="isola_tombs"), {"emit": {"sfx": "sfx/rome/tibia.wav"}}], route=["portus", "isola_tombs"],
           cast=[{"role": "townsman", "count": 6}, {"actor": R + "musician", "count": 1}], card="tombs"),
        ev("lamps_lit", "daily", "small", window(("18:30", "19:00")), (60, 80),
           [{"each": {"item": R + "r_compitum", "max": 4}, "state": "lit"}], zone="town", sfx="sfx/world/lamp.wav",
           card="compitum"),
        ev("vigiles_round", "daily", "small", window(("21:00", "21:30")), (90, 110),
           [wander(zone="town", dur=(80, 100))], zone="town", cast=[{"role": "vigil", "count": 4}], card="vigiles"),
        ev("dogs_bark", "common", "small", window(("21:00", "03:00"), every=5400), (5, 6), [], zone="town",
           sfx="sfx/world/dog_far.wav"),
    ]


def cards() -> dict:
    L, I, RO = "landmark", "idea", "role"
    c = {
        "portus_hexagon": card(L, "Portus Traiani", "Trajan's harbour",
            "Trajan's hexagonal basin, about 358 metres a side, opened around 112: quays and warehouses all "
            "round, ships moored side by side, and a canal to the Tiber. The grain of Egypt and Africa is "
            "unloaded here for Rome."),
        "portus_lighthouse": card(L, "Pharus", "The lighthouse of Portus",
            "A tower of diminishing storeys with a fire on top, at the mouth of Claudius's outer harbour, built "
            "on the sunken ship that had carried Caligula's obelisk from Egypt."),
        "ostia_guilds": card(L, "Piazzale delle Corporazioni", "The square of the shipping offices",
            "Offices of shipowners and traders from Africa, Gaul and the East line the portico behind the "
            "theatre. Most of the emblem mosaics seen there today were laid later in the century, so its "
            "floors are plain."),
        "ostia_capitolium": card(L, "Capitolium Ostiense", "Ostia's Capitolium",
            "Ostia's tall brick temple to Jupiter, Juno and Minerva, newly built in the 120s at the head of "
            "the forum."),
        "ostia_theatre": card(L, "Theatrum Ostiense", "Ostia's theatre",
            "The theatre Agrippa built under Augustus, on the decumanus near the river. Behind its stage lies "
            "the porticoed square of the shipping offices. It will be enlarged later in the century."),
        "annona_ships": card(I, "Naves frumentariae", "The grain fleet",
            "When the sailing season opens in spring, big round-hulled ships bring grain from Alexandria and "
            "Carthage. At Portus their cargo is measured, stored and moved into barges, which men and oxen tow "
            "up the Tiber to the warehouses of Rome, a few days' haul. Rome could not eat without them."),
        "portoria": card(I, "Portoria", "Customs at the harbour",
            "Goods landed in the empire's ports paid customs duties, usually a few per cent of their value, "
            "collected by contractors and officials who checked cargoes and declarations on the quay. Italy "
            "paid no land tax, but its harbours still took their toll."),
        "collegia": card(I, "Collegia", "Guilds",
            "Shipowners, bakers, builders, ropemakers and dockers formed associations for their trade, with a "
            "patron, a meeting house, shared feasts and burial funds. At Ostia the shippers of each port kept "
            "an office on the square behind the theatre, where merchants came to find a ship."),
        "lighthouse": card(RO, "Pharus", "", "A keeper carries wood to the fire on the lighthouse at dusk, so ships "
                           "can find the harbour mouth at night."),
        "customs_officer": card(RO, "Portitor", "", "A customs officer checks the cargo and the declaration before "
                                "goods leave the quay."),
        "shipowner": card(RO, "Navicularius", "", "A shipowner who carries grain for the state's supply and meets "
                          "merchants at his office on the square."),
        "salt": card(RO, "Salinator", "", "Salt rakers gather the salt left where sea water dries in the shallow pans "
                     "by the shore."),
    }
    c.update(T.role_cards(roles()))
    c["compitum"] = T.ROME.role_cards(RO)["compitum"]
    return c


def build(view) -> dict:
    return {
        "version": 1, "id": "ostia", "name": "Ostia and Portus", "native": "Ostia · Portus",
        "caption": "Ostia and Portus · April AD 126", "era": "The Rome of Hadrian · AD 126", "season": "spring",
        "theme": T.theme([{"file": "amb/rome/river.ogg", "hours": ["05:30", "19:30"]},
                          {"file": "amb/rome/night.ogg", "hours": ["19:30", "05:30"]}],
                         [{"rect": grid_rect(view, "harbour"), "file": "amb/world/sea.ogg", "gain": 0.8},
                          {"rect": grid_rect(view, "sea"), "file": "amb/world/sea.ogg", "gain": 0.9},
                          {"rect": grid_rect(view, "fields"), "file": "amb/world/fields.ogg", "gain": 0.6,
                           "hours": ["05:00", "19:30"]}],
                         [{"item": R + "r_lacus", "file": "amb/rome/fountain.ogg", "when": "always"},
                          {"item": R + "r_bath_small", "file": "amb/rome/baths.ogg", "when": "afternoon"}],
                         "April showers; sea mist some mornings; the west wind off the sea"),
        "densities": T.DENSITIES,
        "districts": districts(),
        "roles": roles(),
        "groups": [],
        "chains": chains(),
        "festivals": FESTIVALS,
        "events": events(),
        "days_shown": [{"day": 3, "label": "A working day at the port"},
                       {"day": 0, "label": "The grain fleet comes in (spring, day 1)"}],
        "figures": [],
        "lanes_tokens": [{"actor": R + "merchantman", "lane": "ostia:portus", "count": 3},
                         {"actor": "world.fishing_boat", "lane": "ostia:portus", "count": 2},
                         {"actor": R + "barge", "lane": "ostia:tiber_ostia", "count": 2},
                         {"actor": R + "barge", "lane": "ostia:portus_canal", "count": 1}],
        "cards": cards(),
        "strings": {"first_visit": "Ostia and Portus, April AD 126: the sailing season is open and the grain "
                                   "fleet is in.",
                    "grain_fleet": "The grain fleet is coming in: a line of big ships rounds the lighthouse.",
                    "lighthouse": "Dusk: the fire is lit on the lighthouse."},
        "journal": ["landmark:*", "chain:*", "idea:*", "event:grain_fleet"],
    }
