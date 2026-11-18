"""Pārsa's life and text: who is where at each hour, what they do, the chains, the spring
audience and the other events, the figures and every card (`assets/regions/parsa.json`).

Sources: `docs/design/cities/persepolis.md` as corrected by the fact-check
(`docs/design/cities/fact-check.md` §1): the treasurer of 470 is Mauš; the occasion is "the
spring audience" and only the card `new_year` names the New Year question; Cyrus's tomb was
found robbed; Herodotus's "no altars, no fire" is a Greek claim the reliefs contradict.
Built by `tools/worldgen/build.sh --city parsa`, checked by `worldgen.citylife`.
"""

from __future__ import annotations

from worldgen import citylife as CL
from worldgen import seasonlife as SL
from worldgen.citylife import card, curve, go, grid_rect, pop, role, sched, use, wait, wander

SEASONS = SL.sibling(__file__, "seasons")
SEASON_BEDS = SEASONS.SEASON_BEDS
P = "parsa."

# -- hours -------------------------------------------------------------------------------------

DENSITIES = {
    "always": [1.0] * 24,
    "day": curve({0: 0, 5: 0.25, 6: 0.7, 7: 1, 12: 0.7, 14: 1, 18: 0.6, 19: 0.3, 20: 0.1, 21: 0}),
    "work": curve({0: 0, 5: 0.3, 6: 0.85, 7: 1, 12: 0.6, 14: 1, 18: 0.4, 19: 0}),
    "dawn_work": curve({0: 0, 4: 0.5, 5: 0.9, 6: 1, 12: 0.6, 14: 0.9, 15: 1, 18: 0.5, 19: 0}),
    "court": curve({0: 0.1, 6: 0.4, 7: 1, 12: 0.7, 14: 0.9, 18: 0.7, 19: 0.5, 20: 0.3, 22: 0.1}),
    "watch": curve({0: 0.5, 4: 0.7, 6: 1, 18: 0.8, 20: 0.5}),
    "night_watch": curve({0: 1, 5: 0.4, 6: 0, 18: 0.4, 20: 1}),
    "houses": curve({0: 0, 4: 0.3, 5: 0.7, 6: 1, 12: 0.7, 14: 0.9, 17: 1, 19: 0.6, 20: 0.3,
                     21: 0.1, 22: 0}),
    "kitchen": curve({0: 0, 4: 0.6, 5: 1, 9: 0.8, 11: 1, 13: 0.7, 14: 0.9, 18: 1, 21: 0.4, 22: 0}),
    "evening": curve({0: 0.2, 1: 0, 17: 0.3, 18: 0.8, 19: 1, 22: 0.6, 23: 0.3}),
    "camp": curve({0: 0.15, 5: 0.5, 6: 0.9, 8: 0.8, 12: 0.6, 14: 0.8, 17: 0.9, 19: 1, 21: 0.6,
                   22: 0.3, 23: 0.15}),
    "graze": curve({0: 0.3, 5: 0.8, 6: 1, 18: 0.8, 19: 0.4}),
    "children": curve({0: 0, 6: 0.3, 7: 0.9, 8: 1, 12: 0.6, 14: 1, 18: 0.7, 19: 0.3, 20: 0}),
    "audience": curve({0: 0, 6: 0.5, 7: 1, 12: 0.6, 13: 0.3, 18: 0}),
}

RAIN = {"when": {"weather": "rain"}, "routine": "shelter", "priority": 2}


def home_routine(door_item: str, within: int = 6) -> dict:
    return {"steps": [go(item=door_item, slot="door", within=within),
                      {"enter": {"here": True}, "until": {"hour": "05:00"}}]}


def shelter_door(within: int = 12) -> dict:
    return {"steps": [go(slot_kind="door", within=within),
                      {"enter": {"here": True}, "until": {"weather": "clear"}}]}


def shelter_portico() -> dict:
    return {"steps": [go(item=P + "apadana", slot="stroll"),
                      use(anim="idle", until={"weather": "clear"})]}


def roles() -> list[dict]:
    R = []
    # --- the terrace: court, guards, ushers, magi, servants -----------------------------------
    R.append(role("courtier", P + "noble", "Persian noble", sched(
        ("06:30", "12:00", "attend"), ("12:00", "14:00", "rest"), ("14:00", "19:30", "walk")),
        {"attend": {"loop": True, "steps": [
            go(node="apadana_stair_n.head"), use(anim="talk", dur=(20, 40)),
            go(node="gate_all_lands"), wait(dur=(6, 12)),
            go(node="tripylon_stair.head"), use(anim="talk", dur=(15, 30)),
            wander(radius=4, dur=(15, 25))]},
         "rest": {"steps": [go(node="palace_court"), wander(radius=3, dur=(30, 50)),
                            use(anim="idle", dur=(40, 60))]},
         "walk": {"loop": True, "steps": [
             go(node="palace_court"), use(anim="talk", dur=(15, 25)),
             go(node="hadish_stair_w.head"), use(anim="talk", dur=(20, 30)),
             go(node="north_court"), wait(dur=(8, 14))]},
         "shelter": shelter_portico()}, interrupts=[RAIN], card="courtier"))
    R.append(role("median_official", P + "elamite", "Elamite courtier", sched(
        ("06:30", "12:30", "attend"), ("14:00", "18:30", "attend")),
        {"attend": {"loop": True, "steps": [
            go(node="north_court"), use(anim="talk", dur=(15, 30)),
            go(node="apadana_stair_n.head"), use(anim="talk", dur=(20, 30)),
            go(node="hall_forecourt"), wait(dur=(10, 15))]},
         "shelter": shelter_portico()}, interrupts=[RAIN]))
    R.append(role("usher", P + "usher", "Usher", sched(("06:00", "13:00", "audience"),
                                                       ("14:00", "18:00", "gate")),
        {"audience": {"loop": True, "steps": [
            go(home="usher"), use({"home": "usher"}, anim="gesture", dur=(20, 30)),
            use(anim="bow", dur=(4, 6)), go(node="stair_top"), wait(dur=(10, 20))]},
         "gate": {"loop": True, "steps": [
             go(node="gate_all_lands"), use(anim="idle", dur=(30, 50)),
             go(node="stair_top"), use(anim="gesture", dur=(6, 10))]},
         "shelter": shelter_portico()}, interrupts=[RAIN], card="usher",
        home={"item": P + "apadana", "slot": "usher"}))
    guard_posts = [(P + "great_stair", "guard"), (P + "gate_all_lands", "guard"),
                   (P + "apadana", "guard"), (P + "tacara", "guard"), (P + "tripylon", "guard")]
    for item, slot in guard_posts:
        R.append(role("guard_" + item.split(".")[1], P + "guard_spear", "Spearman of the guard",
            sched(("04:00", "18:00", "post"), ("18:30", "04:00", "post")),
            {"post": {"steps": [go(home=slot), use({"home": slot}, anim="guard",
                                                   until={"hour": "18:00"})]}},
            home={"item": item, "slot": slot}, card="spearman"))
    R.append(role("spearman", P + "guard_spear", "Spearman of the guard", sched(
        ("04:00", "20:00", "patrol"), ("20:00", "04:00", "night_patrol")),
        {"patrol": {"loop": True, "steps": [
            go(node="stair_top"), use(anim="march", dur=(8, 12)), go(node="gate_all_lands"),
            use(anim="guard", dur=(20, 30)), go(node="north_court"), use(anim="march", dur=(8, 12)),
            go(node="apadana_stair_n.foot"), use(anim="guard", dur=(20, 30)),
            go(node="palace_court"), use(anim="guard", dur=(15, 25))]},
         "night_patrol": {"loop": True, "steps": [
             go(node="stair_top"), use(anim="guard", dur=(30, 50)), go(node="north_court"),
             use(anim="march", dur=(10, 15)), go(node="palace_court"), use(anim="guard", dur=(30, 50))]}},
        card="spearman"))
    R.append(role("drill_soldier", P + "guard_spear", "Soldier at drill", sched(
        ("05:00", "12:30", "drill"), ("15:00", "20:00", "drill")),
        {"drill": {"loop": True, "steps": [
            go(home="drill"), use({"home": "drill"}, anim="march", dur=(20, 30)),
            use(anim="guard", dur=(10, 20))]}}, home={"item": P + "garrison", "slot": "drill"}))
    R.append(role("garrison_soldier", P + "guard_spear", "Soldier of the garrison", sched(
        ("05:00", "21:00", "round")),
        {"round": {"loop": True, "steps": [
             go(node="garrison_gate"), use(anim="march", dur=(6, 10)),
             go(node="archive"), use(anim="guard", dur=(15, 25)),
             go(node="hall_forecourt"), wait(dur=(6, 12))]}}))
    R.append(role("wall_watch", P + "guard_mede", "Guard in Median dress", sched(
        ("18:00", "06:00", "torch_round"), ("06:00", "18:00", "day_round")),
        {"torch_round": {"loop": True, "steps": [
            go(node="archive"), use(anim="guard", dur=(20, 40)),
            go(node="quarry_face"), use(anim="guard", dur=(20, 40)),
            go(node="mountain_shrine"), wait(dur=(10, 20))]},
         "day_round": {"loop": True, "steps": [
             go(node="treasury_door"), use(anim="guard", dur=(30, 60)),
             go(item=P + "p_brazier", spot="beside", within=6), use(anim="guard", dur=(30, 50)),
             go(node="haul_ramp"), wait(dur=(10, 20))]}}, card="mede_guard"))
    R.append(role("magus", P + "magus", "Magus", sched(
        ("03:30", "06:30", "dawn_fire"), ("06:30", "17:30", "day"), ("17:30", "20:00", "dusk_fire")),
        {"dawn_fire": {"steps": [go(home="tend"), use({"home": "tend"}, anim="pour", dur=(20, 30)),
                                 use(anim="talk", dur=(30, 50)),
                                 use(anim="idle", until={"hour": "06:30"})]},
         "day": {"loop": True, "steps": [
             go(home="tend"), use({"home": "tend"}, anim="pour", dur=(15, 25)),
             wander(radius=4, dur=(30, 60)), use(anim="talk", dur=(15, 25))]},
         "dusk_fire": {"steps": [go(home="tend"), use({"home": "tend"}, anim="pour", dur=(15, 20)),
                                 use(anim="talk", dur=(40, 60))]}},
        home={"item": P + "p_fire_altar", "slot": "tend"}, card="magus"))
    R.append(role("royal_servant", P + "servant", "Servant of the court", sched(
        ("05:00", "11:00", "kitchen"), ("11:00", "16:00", "fetch"), ("16:00", "21:00", "dinner")),
        {"kitchen": {"loop": True, "steps": [
            go(item=P + "p_oven", spot="beside", within=6), use(anim="serve", dur=(15, 25)),
            {"take": "world.goods_dish"}, go(node="royal_kitchens"), {"put": "world.goods_dish"},
            use(anim="carry_idle", dur=(6, 10))]},
         "fetch": {"loop": True, "steps": [
             go(node="royal_kitchens"), use(anim="carry_idle", dur=(8, 12)),
             go(node="palace_court"), use(anim="serve", dur=(10, 20)),
             go(node="hadish_kitchens"), wait(dur=(10, 20))]},
         "dinner": {"loop": True, "steps": [
             go(item=P + "p_oven", spot="beside", within=6), {"take": "world.goods_dates"},
             go(node="hadish_stair_w.head"), {"put": "world.goods_dates"},
             use(anim="serve", dur=(10, 18)), go(node="hadish_kitchens")]},
         "shelter": shelter_portico()}, interrupts=[RAIN], card="servant"))
    R.append(role("household_woman", P + "woman_worker", "Woman of a royal household", sched(
        ("06:00", "12:00", "household"), ("13:00", "20:00", "household")),
        {"household": {"loop": True, "steps": [
            go(node="palace_court"), use(anim="idle", dur=(10, 20)),
            go(item=P + "p_workshop", slot="work", within=6), use(anim="throw", dur=(20, 30)),
            go(node="royal_kitchens"), {"take": "world.goods_waterskin"}, go(node="palace_court"),
            {"put": "world.goods_waterskin"}]},
         "shelter": shelter_portico()}, interrupts=[RAIN], card="household_woman"))
    R.append(role("musician", P + "musician", "Court musician", sched(
        ("16:00", "18:30", "practice"), ("19:00", "23:30", "play")),
        {"practice": {"steps": [go(node="palace_court"), use(anim="play", dur=(40, 60)),
                                go(node="pavilion")]},
         "play": {"steps": [go(home="music"), use({"home": "music"}, anim="play",
                                                 until={"hour": "23:30"})]}},
        home={"item": P + "pavilion", "slot": "music"}, card="musician"))
    # --- the building site and the quarry -------------------------------------------------------
    R.append(role("quarryman", P + "labourer", "Quarryman", sched(
        ("05:30", "12:00", "cut"), ("12:00", "13:30", "noon"), ("13:30", "17:30", "cut")),
        {"cut": {"loop": True, "steps": [
            go(item=P + "quarry", slot="cut"), use(anim="haul", dur=(20, 35)),
            use(anim="idle", dur=(4, 8))]},
         "noon": {"steps": [go(node="quarry_face"), use(anim="idle", dur=(40, 50))]}},
        home={"item": P + "quarry", "slot": "cut"}, card="quarryman"))
    R.append(role("sledge", P + "p_sledge", "Ox sledge with a block", sched(("06:00", "17:30", "haul")),
        {"haul": {"loop": True, "steps": [
            go(node="quarry_face"), wait(dur=(15, 25)), go(node="haul_ramp"),
            go(node="masons_yard"), wait(dur=(15, 25))]}},
        locomotion={"mode": "walk", "speed": 0.5, "network": "roads", "turn_radius": 2}))
    R.append(role("cart", P + "p_cart", "Ox cart", sched(("06:00", "18:00", "haul")),
        {"haul": {"loop": True, "steps": [
            go(node="caravan_yard"), wait(dur=(20, 30)), go(node="brickfield"), wait(dur=(15, 25)),
            go(node="haul_ramp"), go(node="masons_yard"), wait(dur=(20, 30))]}},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}))
    R.append(role("rope_team", P + "labourer", "Rope team", sched(("06:00", "17:30", "pull")),
        {"pull": {"loop": True, "steps": [
            {"follow": {"actor": P + "p_sledge"}, "dur": [60, 90], "spacing": 0.8},
            use(anim="haul", dur=(10, 20)), use(anim="idle", dur=(6, 10))]}}))
    R.append(role("mason", P + "mason", "Mason", sched(
        ("06:00", "12:00", "dress"), ("12:00", "13:30", "noon"), ("13:30", "17:30", "dress")),
        {"dress": {"loop": True, "steps": [
            go(item=P + "hall_100", slot="mason"), use(anim="work_high", dur=(25, 40)),
            use(anim="idle", dur=(4, 8))]},
         "noon": {"steps": [go(item=P + "p_drum_stack", spot="beside", within=6),
                            use(anim="idle", dur=(40, 50))]}},
        home={"item": P + "hall_100", "slot": "mason"}, card="mason"))
    R.append(role("column_setter", P + "labourer", "Column setter", sched(
        ("06:30", "12:00", "hoist"), ("13:30", "17:00", "hoist")),
        {"hoist": {"loop": True, "steps": [
            go(item=P + "hall_100", slot="hoist"), use(anim="haul", dur=(25, 40)),
            go(item=P + "p_crane", spot="beside", within=8), use(anim="haul", dur=(15, 25))]}}))
    R.append(role("carpenter", P + "craftsman", "Carpenter", sched(
        ("06:30", "12:00", "beams"), ("13:30", "17:30", "beams")),
        {"beams": {"loop": True, "steps": [
            go(item=P + "p_crane", spot="beside", within=8), use(anim="work_high", dur=(25, 40)),
            go(item=P + "p_drum_stack", spot="beside", within=8), use(anim="kneel", dur=(15, 25))]}},
        card="carpenter"))
    R.append(role("sculptor", P + "craftsman", "Relief sculptor", sched(
        ("06:30", "12:00", "carve"), ("13:30", "17:30", "carve")),
        {"carve": {"loop": True, "steps": [
            go(item=P + "p_drum_stack", spot="beside", within=8), use(anim="kneel", dur=(30, 50)),
            use(anim="work_high", dur=(20, 30))]}}, card="sculptor"))
    R.append(role("site_scribe", P + "scribe", "Scribe of the works", sched(
        ("06:30", "12:00", "count"), ("13:30", "17:00", "count")),
        {"count": {"loop": True, "steps": [
            go(item=P + "p_scribe_desk", slot="write", within=6), use(anim="write", dur=(30, 50)),
            go(item=P + "hall_100", slot="mason"), use(anim="idle", dur=(6, 10))]}}))
    # --- the treasury and the archive -----------------------------------------------------------
    R.append(role("treasury_scribe", P + "scribe", "Treasury scribe", sched(
        ("06:30", "12:00", "weigh"), ("13:30", "17:00", "file")),
        {"weigh": {"loop": True, "steps": [
            go(item=P + "p_scales", spot="beside", within=6), use(anim="write", dur=(30, 50)),
            go(node="treasury_door"), use(anim="idle", dur=(6, 12))]},
         "file": {"loop": True, "steps": [
             go(node="treasury_door"), {"take": "world.goods_letter"}, go(node="archive"),
             {"put": "world.goods_letter"}, use(anim="write", dur=(20, 30))]}}, card="scribe"))
    R.append(role("porter", P + "labourer", "Porter", sched(
        ("06:00", "12:00", "carry"), ("13:30", "17:30", "carry")),
        {"carry": {"loop": True, "steps": [
            go(item=P + "p_sacks", spot="beside", within=8), {"take": "world.goods_sacks"},
            go(item=P + "p_granary", slot="door", within=10), {"put": "world.goods_sacks"},
            use(anim="idle", dur=(6, 10))]}}, card="porter"))
    # --- town, crafts and the workers' quarter --------------------------------------------------
    R.append(role("weaver", P + "woman_worker", "Weaver", sched(
        ("06:00", "12:00", "weave"), ("12:00", "13:30", "noon"), ("13:30", "17:30", "weave")),
        {"weave": {"loop": True, "steps": [
            go(item=P + "p_loom", slot="weave", within=4), use(anim="throw", dur=(40, 60)),
            use(anim="idle", dur=(4, 8))]},
         "noon": {"steps": [go(node="weavers"), use(anim="idle", dur=(30, 45))]}},
        home={"item": P + "p_loom", "slot": "weave"}, card="weaver"))
    R.append(role("weaving_overseer", P + "overseer_woman", "Overseer of weavers", sched(
        ("06:00", "17:30", "oversee")),
        {"oversee": {"loop": True, "steps": [
            go(item=P + "p_loom", slot="weave", within=4), use(anim="gesture", dur=(10, 15)),
            go(node="weavers"), use(anim="idle", dur=(15, 25)),
            go(item=P + "p_workshop", slot="work", within=8), use(anim="gesture", dur=(8, 12))]}}))
    R.append(role("brickmaker", P + "labourer", "Brickmaker", sched(
        ("05:30", "11:30", "mould"), ("11:30", "13:30", "noon"), ("13:30", "17:30", "mould")),
        {"mould": {"loop": True, "steps": [
            go(item=P + "p_brickfield", slot="mould"), use(anim="haul", dur=(25, 40)),
            use(anim="idle", dur=(6, 10))]},
         "noon": {"steps": [go(node="brickfield"), use(anim="idle", dur=(40, 50))]}},
        home={"item": P + "p_brickfield", "slot": "mould"}, card="brickmaker"))
    R.append(role("kiln_worker", P + "craftsman", "Kiln worker", sched(
        ("06:00", "12:00", "fire"), ("13:30", "17:30", "fire")),
        {"fire": {"loop": True, "steps": [
            go(item=P + "p_kiln", spot="beside", within=4), use(anim="stir", dur=(30, 45)),
            use(anim="kneel", dur=(10, 15))]}}, home={"item": P + "p_kiln", "slot": "beside"}))
    R.append(role("wall_decorator", P + "craftsman", "Wall decorator", sched(
        ("06:30", "12:00", "panel"), ("13:30", "17:30", "panel")),
        {"panel": {"loop": True, "steps": [
            go(item=P + "paradise_gate", spot="beside"), use(anim="work_high", dur=(30, 45)),
            use(anim="kneel", dur=(15, 25))]}}, card="wall_decorator"))
    R.append(role("goldsmith", P + "craftsman", "Goldsmith", sched(
        ("06:30", "12:00", "work"), ("13:30", "17:30", "work")),
        {"work": {"loop": True, "steps": [
            go(item=P + "p_workshop", slot="work", within=6), use(anim="work_high", dur=(30, 50)),
            use(anim="kneel", dur=(10, 20))]}}, card="goldsmith"))
    R.append(role("dyer", P + "woman_worker", "Dyer", sched(
        ("06:00", "12:00", "dye"), ("13:30", "17:30", "rinse")),
        {"dye": {"loop": True, "steps": [
            go(item=P + "p_jars", spot="beside", within=8), use(anim="stir", dur=(30, 45)),
            go(node="dye_yard"), use(anim="idle", dur=(6, 10))]},
         "rinse": {"loop": True, "steps": [
             go(node="dye_yard"), use(anim="stir", dur=(25, 35)),
             go(item=P + "p_jars", spot="beside", within=8), use(anim="throw", dur=(15, 25))]}},
        card="dyer"))
    R.append(role("grinder", P + "woman_worker", "Grinder", sched(
        ("05:00", "11:00", "grind"), ("14:00", "18:00", "grind")),
        {"grind": {"loop": True, "steps": [
            go(item=P + "p_granary", slot="door", within=8), {"take": "world.goods_sacks"},
            go(slot_kind="door", within=8), use(anim="stir", dur=(30, 50)),
            go(item=P + "p_oven", spot="beside", within=10), {"put": "world.goods_sacks"}]}},
        card="grinder"))
    R.append(role("baker", P + "woman_worker", "Baker", sched(
        ("04:30", "10:30", "bake"), ("15:00", "18:30", "bake")),
        {"bake": {"loop": True, "steps": [
            go(item=P + "p_oven", spot="beside", within=6), use(anim="stir", dur=(20, 30)),
            use(anim="throw", dur=(15, 25)), use(anim="idle", dur=(4, 8))]}}, card="baker"))
    R.append(role("water_carrier", P + "woman_worker", "Water carrier", sched(
        ("05:00", "10:00", "water"), ("16:00", "19:00", "water")),
        {"water": {"loop": True, "steps": [
            go(home="draw"), use({"home": "draw"}, anim="stir", dur=(6, 10)),
            {"take": "world.goods_waterskin"}, go(slot_kind="door", within=10),
            {"put": "world.goods_waterskin"}, use(anim="idle", dur=(4, 8))]},
         "shelter": shelter_door()}, interrupts=[RAIN],
        home={"item": P + "p_well", "slot": "draw"}))
    R.append(role("townswoman", P + "woman_worker", "Woman of the town", sched(
        ("05:00", "12:00", "chores"), ("13:30", "20:00", "chores")),
        {"chores": {"loop": True, "steps": [
            go(slot_kind="door", within=8), use(anim="stir", dur=(20, 35)),
            go(node="town_square"), use(anim="idle", dur=(10, 20)),
            go(item=P + "p_oven", spot="beside", within=12), use(anim="throw", dur=(15, 25))]},
         "shelter": shelter_door()}, interrupts=[RAIN]))
    R.append(role("workman", P + "labourer", "Workman of the town", sched(
        ("05:00", "19:30", "errands")),
        {"errands": {"loop": True, "steps": [
            go(node="workers_quarter"), use(anim="idle", dur=(8, 14)),
            go(item=P + "p_jars", spot="beside", within=12), {"take": "world.goods_amphorae"},
            go(slot_kind="door", within=12), {"put": "world.goods_amphorae"},
            go(node="town_square"), wait(dur=(10, 20))]},
         "shelter": shelter_door()}, interrupts=[RAIN]))
    R.append(role("child", P + "child", "Child", sched(("06:30", "19:30", "play")),
        {"play": {"loop": True, "steps": [{"pick": [
            {"weight": 3, "steps": [wander(radius=6, dur=(20, 40)), use(anim="run", dur=(6, 10))]},
            {"weight": 2, "steps": [go(node="town_square"), use(anim="kneel", dur=(20, 30))]},
            {"weight": 2, "steps": [go(node="stair_plaza"), use(anim="idle", dur=(20, 40))]}]}]},
         "shelter": shelter_door()}, interrupts=[RAIN], card="child"))
    R.append(role("elamite_priest", P + "elamite", "Elamite priest", sched(
        ("05:00", "08:00", "offer"), ("16:00", "19:00", "offer")),
        {"offer": {"loop": True, "steps": [
            go(node="elamite_shrine"), use(anim="talk", dur=(30, 50)),
            wander(radius=3, dur=(15, 25)), use(anim="idle", dur=(15, 25))]}},
        card="elamite_priest"))
    R.append(role("town_scribe", P + "scribe", "Granary scribe", sched(
        ("05:30", "12:00", "record"), ("14:00", "17:00", "record")),
        {"record": {"loop": True, "steps": [
            go(item=P + "p_scribe_desk", slot="write", within=6), use(anim="write", dur=(40, 60)),
            go(item=P + "p_granary", slot="door", within=10), use(anim="idle", dur=(6, 10))]}}))
    # --- the plain: gardens, fields, horses, flocks, the road -----------------------------------
    R.append(role("gardener", P + "gardener", "Gardener of the paradise", sched(
        ("04:00", "07:00", "channels"), ("07:00", "12:00", "tend"), ("14:00", "18:30", "tend")),
        {"channels": {"steps": [
            go(item=P + "p_sluice", spot="beside"), use(anim="work_low", dur=(10, 15)),
            go(item=P + "p_basin", spot="beside", within=6), use(anim="pour", dur=(15, 25))]},
         "tend": {"loop": True, "steps": [{"pick": [
             {"weight": 3, "steps": [wander(zone="paradise", dur=(20, 40)),
                                     use(anim="work_high", dur=(20, 30))]},
             {"weight": 2, "steps": [go(item=P + "p_basin", spot="beside", within=6),
                                     use(anim="pour", dur=(15, 25))]},
             {"weight": 2, "steps": [wander(radius=5, dur=(20, 30)),
                                     use(anim="work_low", dur=(20, 35))]}]}]}}, card="gardener"))
    R.append(role("farmer", P + "farmer", "Farmer", sched(
        ("04:30", "11:30", "field"), ("14:30", "18:30", "field")),
        {"field": {"loop": True, "steps": [{"pick": [
            {"weight": 4, "steps": [wander(radius=6, dur=(20, 40)),
                                    use(anim="work_low", dur=(30, 50))]},
            {"weight": 1, "steps": [go(item=P + "p_threshing", spot="beside", within=40),
                                    use(anim="haul", dur=(20, 30))]}]}]}}, card="farmer"))
    R.append(role("groom", P + "groom", "Groom", sched(
        ("04:30", "08:00", "water"), ("08:00", "16:30", "exercise"), ("16:30", "19:30", "water")),
        {"water": {"loop": True, "steps": [
            go(item=P + "p_trough", spot="beside", within=8), use(anim="stir", dur=(15, 25)),
            go(item=P + "p_horse_line", spot="beside", within=8), use(anim="stir", dur=(20, 30))]},
         "exercise": {"loop": True, "steps": [
             go(item=P + "p_horse_line", spot="beside", within=8), use(anim="stir", dur=(15, 25)),
             wander(radius=8, dur=(30, 50))]}}, card="groom"))
    R.append(role("horse", P + "nisaean_horse", "Nisaean horse", sched(("00:00", "24:00", "graze")),
        {"graze": {"loop": True, "steps": [
            go(item=P + "p_horse_line", spot="beside", within=10), use(anim="graze", dur=(30, 60)),
            wander(radius=3, dur=(10, 20))]}}, card="nisaean_horse"))
    R.append(role("rider", P + "cavalryman", "Horseman", sched(
        ("06:00", "11:00", "ride"), ("15:00", "18:00", "ride")),
        {"ride": {"loop": True, "steps": [
            go(node="cavalry_ground"), wander(zone="cavalry", dur=(40, 70)),
            go(node="archery_ground"), wait(dur=(10, 20))]}}))
    R.append(role("archer", P + "archer", "Archer", sched(("06:00", "11:30", "shoot"),
                                                        ("15:00", "18:00", "shoot")),
        {"shoot": {"loop": True, "steps": [
            go(node="archery_ground"), use(anim="shoot", dur=(20, 30)),
            go(item=P + "p_archery_butt", spot="beside", within=6), use(anim="idle", dur=(6, 10))]}},
        card="archer"))
    R.append(role("shepherd", P + "shepherd", "Shepherd", sched(
        ("05:00", "17:30", "graze"), ("17:30", "19:00", "fold")),
        {"graze": {"loop": True, "steps": [wander(radius=10, dur=(40, 70)),
                                           use(anim="gesture", dur=(6, 10))]},
         "fold": {"steps": [go(node="sheepfold"), use(anim="idle", until={"hour": "19:00"})]}},
        card="shepherd"))
    R.append(role("sheep", "world.sheep", "Sheep", sched(("05:00", "19:00", "graze")),
        {"graze": {"loop": True, "steps": [wander(radius=6, dur=(20, 40)),
                                           use(anim="graze", dur=(10, 25))]}}))
    R.append(role("goat", "world.goat", "Goat", sched(("05:00", "19:00", "graze")),
        {"graze": {"loop": True, "steps": [wander(radius=6, dur=(20, 40)),
                                           use(anim="graze", dur=(10, 25))]}}))
    R.append(role("dog", "world.dog", "Dog", sched(("00:00", "24:00", "roam")),
        {"roam": {"loop": True, "steps": [wander(radius=8, dur=(20, 40)),
                                          use(anim="sleep", dur=(30, 60))]}}))
    R.append(role("stork", "world.stork", "White stork", sched(("06:00", "19:00", "forage")),
        {"forage": {"loop": True, "steps": [wander(radius=10, dur=(15, 30)),
                                            use(anim="peck", dur=(8, 16))]}}))
    R.append(role("hoopoe", P + "hoopoe", "Hoopoe", sched(("05:00", "19:00", "peck")),
        {"peck": {"loop": True, "steps": [wander(radius=5, dur=(10, 20)),
                                          use(anim="peck", dur=(6, 12)),
                                          {"emit": {"sfx": "sfx/parsa/hoopoe.wav"}}]}},
        card="hoopoe"))
    R.append(role("zebu", P + "zebu", "Humped ox", sched(("05:30", "18:00", "work")),
        {"work": {"loop": True, "steps": [
            go(item=P + "p_threshing", spot="beside", within=12), use(anim="graze", dur=(30, 50)),
            wander(radius=4, dur=(20, 30))]}}))
    R.append(role("station_scribe", P + "scribe", "Station scribe", sched(
        ("06:00", "19:00", "check")),
        {"check": {"loop": True, "steps": [
            go(item=P + "road_station", slot="seal_check"), use(anim="write", dur=(30, 50)),
            go(node="caravan_yard"), use(anim="idle", dur=(10, 15))]}}, card="station"))
    R.append(role("camel", P + "dromedary", "Dromedary", sched(("00:00", "24:00", "rest")),
        {"rest": {"loop": True, "steps": [go(node="caravan_yard"), use(anim="graze", dur=(40, 80)),
                                          wander(radius=3, dur=(10, 20))]}}))
    R.append(role("caravan_driver", P + "caravan_driver", "Caravan driver", sched(
        ("06:00", "20:00", "yard")),
        {"yard": {"loop": True, "steps": [
            go(node="caravan_yard"), use(anim="idle", dur=(20, 30)),
            go(item=P + "p_trough", spot="beside", within=8), use(anim="idle", dur=(10, 20)),
            go(item=P + "road_station", slot="door"), wait(dur=(10, 15))]}}))
    # --- the delegations' camp ------------------------------------------------------------------
    R.append(role("camp_servant", P + "servant", "Camp attendant", sched(("05:00", "22:00", "camp")),
        {"camp": {"loop": True, "steps": [
            go(item=P + "p_tent", slot="door", within=4), use(anim="serve", dur=(15, 25)),
            go(item=P + "p_brazier", spot="beside", within=6), use(anim="idle", dur=(10, 20)),
            go(item=P + "p_jars", spot="beside", within=6), {"take": "world.goods_waterskin"},
            go(item=P + "p_tent", slot="door", within=4), {"put": "world.goods_waterskin"}]}}))
    for people in CAMP:
        for part, anims in (("lead", True), ("bearer", False)):
            steps = [go(item=P + "p_brazier", spot="beside", within=6),
                     use(anim="idle", dur=(30, 60)),
                     go(item=P + "p_tent", slot="door", within=6),
                     use(anim="bow" if anims else "idle", dur=(4, 8)), wander(radius=4, dur=(20, 30))]
            R.append(role(f"guest_{people}_{part}", f"{P}del_{people}_{part}",
                          f"Guest of the court ({PEOPLES[people][0]})",
                          sched(("05:30", "22:00", "wait")), {"wait": {"loop": True, "steps": steps}}))
    # --- the delegations' own roles (cast by the audience; their routine is the event's) --------
    for people in PEOPLES:
        for part in ("lead", "bearer"):
            R.append(role(f"del_{people}_{part}", f"{P}del_{people}_{part}",
                          f"{PEOPLES[people][0]} ({'leader' if part == 'lead' else 'gift-bearer'})",
                          [], {}, card=f"delegation_{people}"))
    return R


# The 23 peoples of the Apadāna's east stair, in one modern order (fact-check §1.1: order and
# some names uncertain; cards never number them). name, gift animal or cart, card text.
PEOPLES = {
    "medes": ("Medes", None, "Neighbours and partners of the Persians. They bring a pitcher, "
              "bowls, a short sword, rings and a riding costume of coat and trousers, the dress "
              "half the court itself wears."),
    "elamites": ("Elamites", (P + "lioness", 1, P + "lion_cub", 2), "From the old kingdom of "
                 "Susa and Anšan. Wreathed, without hats, they bring two bows, two daggers and a "
                 "lioness with her two cubs."),
    "armenians": ("Armenians", (P + "nisaean_horse", 1), "From the high valleys of the north. "
                  "Hooded riders, they lead a bridled stallion and carry a vessel with "
                  "griffin-headed handles."),
    "parthians": ("Parthians", (P + "bactrian_camel", 1), "From the steppe edge east of the "
                  "Caspian. In face-protecting hoods they bring two bowls and a two-humped "
                  "camel."),
    "babylonians": ("Babylonians", (P + "zebu", 1), "From the great city on the Euphrates. In "
                    "tasselled caps they bring shallow bowls, a fringed garment and a humped "
                    "bull."),
    "lydians": ("Lydians", (P + "chariot", 1), "From Sardis, where the Royal Road begins. In tall "
                "conical hats they bring metal phials, griffin-headed armlets and a small "
                "two-horse chariot."),
    "arians": ("Arians", (P + "bactrian_camel", 1), "Probably from Haraiva, around Herat. "
               "Dust-hooded, in short cloaks and trousers, they bring bowls and a camel."),
    "syrians": ("Syrians", (P + "ram", 2), "Livius calls them Syrians; other works say "
                "Assyrians. They bring bowls, a copper ingot shaped like an ox hide, a tasselled "
                "garment and two rams."),
    "cappadocians": ("Cappadocians", (P + "nisaean_horse", 1), "From the Anatolian uplands. "
                     "Their cloaks are pinned at the shoulder; they lead a stallion and bring a "
                     "coat and trousers."),
    "saka": ("Saka", (P + "nisaean_horse", 1), "Riders of the northern steppes in tall pointed "
             "hoods. They lead a horse with a bell and bring rings, a coat and trousers; their "
             "leader wears sword and bow."),
    "egyptians": ("Egyptians", None, "From the Nile. Their panel on the stair is damaged; traces "
                  "of a hippopotamus remain. The game shows them in white linen."),
    "ionians": ("Yaunā", None, "Ionian Greeks, dressed like the Lydians but bareheaded. They "
                "bring ribbed cups, shallow bowls, folded cloth and round bundles, perhaps balls "
                "of thread."),
    "bactrians": ("Bactrians", (P + "bactrian_camel", 1), "From beyond the Hindu Kush, wreathed "
                  "and earringed. They bring bowls and a two-humped camel."),
    "gandharans": ("Gandharans", (P + "water_buffalo", 1), "From the Kabul and Indus valleys. "
                   "They bring lances, a shield and a water buffalo."),
    "arachosians": ("Arachosians", (P + "bactrian_camel", 1), "Probably from around Kandahar. "
                    "With tasselled wreaths and earrings they bring bowls and a camel."),
    "sagartians": ("Sagartians", (P + "nisaean_horse", 1), "Probably horse-breeding nomads of "
                   "the Iranian plateau. Hooded riders, they lead a stallion and bring "
                   "garments."),
    "sogdians": ("Sogdians", (P + "nisaean_horse", 1), "Probably from around Samarkand; the "
                 "panel is damaged. In tight caps they bring a sword, rings, battle-axes and a "
                 "stallion."),
    "indians": ("Indians", ("world.mule", 1), "From Hinduš on the Indus. Bare-chested, they "
                "carry baskets of gold dust on a shoulder pole and lead a mule."),
    "thracians": ("Thracians", (P + "nisaean_horse", 1), "Skudra, from across the Hellespont, in "
                  "felt caps. They bring spears, round shields and a stallion."),
    "arabs": ("Arabs", (P + "dromedary", 1), "From the desert's edge, in long tasselled robes. "
              "They lead a dromedary, the one-humped camel of Arabia."),
    "carians": ("Carians", (P + "bull", 1), "From the Aegean coast of Anatolia, wreathed like "
                "Lydians. They bring a round shield, a spear and a bull."),
    "libyans": ("Libyans", (P + "oryx", 1), "Probably from Cyrene's hinterland; the panel is "
                "damaged. They bring an oryx and a chariot."),
    "kushites": ("Kushites", (P + "okapi", 1), "From Kush up the Nile. They bring an elephant "
                 "tusk, a small lidded bowl and an animal often read as an okapi, though the "
                 "identification is debated."),
}
CAMP = ["medes", "elamites", "babylonians", "lydians", "saka", "ionians", "indians", "arabs"]


def groups() -> list[dict]:
    out = []
    for people, (_name, animal, _t) in PEOPLES.items():
        members = [{"role": f"del_{people}_lead", "count": 1},
                   {"role": f"del_{people}_bearer", "count": 2, "carry": "world.goods_gift_vessels"}]
        if animal:
            for k in range(0, len(animal), 2):
                members.append({"actor": animal[k], "count": animal[k + 1]})
        out.append({"id": f"delegation_{people}", "leader": {"role": "usher"}, "members": members,
                    "formation": {"kind": "line", "spacing": 0.9}})
    out += [
        {"id": "guard_relief", "leader": {"role": "spearman"},
         "members": [{"role": "spearman", "count": 7}], "formation": {"kind": "pairs", "spacing": 0.8}},
        {"id": "royal_ride", "leader": {"actor": P + "chariot"},
         "members": [{"role": "rider", "count": 4}, {"actor": P + "hound", "count": 2}],
         "formation": {"kind": "cluster", "radius": 3}},
        {"id": "caravan", "leader": {"role": "caravan_driver"},
         "members": [{"actor": P + "dromedary", "count": 3}, {"actor": P + "bactrian_camel", "count": 1},
                     {"actor": "world.donkey", "count": 2, "carry": "world.goods_bale"}],
         "formation": {"kind": "line", "spacing": 1.0}},
        {"id": "gulf_caravan", "leader": {"role": "caravan_driver"},
         "members": [{"actor": P + "dromedary", "count": 4, "carry": "world.goods_dates"}],
         "formation": {"kind": "line", "spacing": 1.0}},
        {"id": "flock", "leader": {"role": "shepherd"},
         "members": [{"actor": "world.sheep", "variant": 1, "count": 8},
                     {"actor": "world.goat", "count": 3}, {"actor": "world.dog", "count": 1}],
         "formation": {"kind": "cluster", "radius": 3}},
    ]
    return out


# -- who is where --------------------------------------------------------------------------------

def per(role_, item, count=1, density="always", **kw) -> dict:
    return CL.per(role_, P + item, count, density, **kw)


RATION_DAY = {"days": {"every": 4, "offset": 3}}
SPRING = {"season": ["spring"]}


def districts() -> list[dict]:
    camp = [pop(f"guest_{p}_lead", "camp", 2, when=SPRING) for p in CAMP] + \
           [pop(f"guest_{p}_bearer", "camp", 3, when=SPRING) for p in CAMP]
    return [
        {"id": "terrace", "area": "centre", "populations": [
            pop("spearman", "watch", 22), pop("courtier", "court", 22),
            per("magus", "p_fire_altar", 1, "day"), pop("median_official", "court", 12),
            pop("royal_servant", "kitchen", 10), pop("wall_watch", "night_watch", 6)]},
        {"id": "audience", "area": "centre", "populations": [
            pop("courtier", "court", 28), pop("spearman", "watch", 12), per("usher", "apadana", 1, "audience"),
            per("guard_gate_all_lands", "gate_all_lands", 4, "watch"), per("guard_apadana", "apadana", 4, "watch"),
            per("guard_tripylon", "tripylon", 2, "watch"),
            pop("median_official", "court", 14), pop("royal_servant", "kitchen", 6)]},
        {"id": "building_site", "area": "town", "populations": [
            per("mason", "hall_100", 6, "work"), per("column_setter", "hall_100", 2, "work"),
            pop("carpenter", "work", 12), pop("sculptor", "work", 10), pop("site_scribe", "work", 2),
            pop("rope_team", "work", 6), pop("sledge", "work", 2), pop("cart", "work", 2),
            pop("spearman", "watch", 4),
            pop("wall_watch", "night_watch", 4)]},
        {"id": "garrison", "area": "town", "populations": [
            per("drill_soldier", "garrison", 6, "work"), pop("garrison_soldier", "watch", 40),
            pop("archer", "work", 14)]},
        {"id": "palaces", "area": "town", "populations": [
            pop("royal_servant", "kitchen", 18), pop("baker", "kitchen", 6), pop("spearman", "watch", 6),
            pop("household_woman", "day", 12),
            per("guard_tacara", "tacara", 2, "watch"), pop("courtier", "court", 8),
            per("water_carrier", "p_well", 1, "houses")]},
        {"id": "treasury", "area": "town", "populations": [
            pop("treasury_scribe", "work", 16), pop("wall_watch", "watch", 10), pop("porter", "work", 17)]},
        {"id": "slope", "area": "wild", "populations": [
            pop("wall_watch", "watch", 6), pop("goat", "graze", 5), pop("stork", "day", 1, when=SPRING)]},
        {"id": "quarry", "area": "town", "populations": [
            per("quarryman", "quarry", 4, "work"), pop("rope_team", "work", 30), pop("sledge", "work", 4),
            pop("wall_watch", "night_watch", 4)]},
        {"id": "paradise", "area": "country", "populations": [
            pop("gardener", "dawn_work", 24), pop("hoopoe", "day", 3), pop("courtier", "court", 2),
            pop("wall_decorator", "work", 3),
            per("musician", "pavilion", 3, "evening")]},
        {"id": "garden_strip", "area": "country", "populations": [
            pop("gardener", "dawn_work", 20), pop("hoopoe", "day", 2)]},
        {"id": "forecourt", "area": "centre", "populations": [
            pop("groom", "dawn_work", 22), pop("horse", "graze", 14), pop("spearman", "watch", 8),
            per("guard_great_stair", "great_stair", 2, "watch"),
            pop("child", "children", 10), pop("courtier", "court", 10), per("water_carrier", "p_well", 1, "houses")]},
        {"id": "town", "area": "town", "populations": [
            per("weaver", "p_loom", 1, "work"), pop("weaving_overseer", "work", 2),
            pop("townswoman", "houses", 26), pop("workman", "day", 10), pop("child", "children", 12),
            pop("goldsmith", "work", 4), pop("dog", "day", 2)]},
        {"id": "workers", "area": "town", "populations": [
            pop("townswoman", "houses", 22), pop("workman", "day", 16), pop("child", "children", 10),
            pop("baker", "kitchen", 4), pop("elamite_priest", "day", 2), pop("dog", "day", 2),
            per("magus", "p_fire_altar", 1, "day"),
            pop("workman", "work", 10, when=RATION_DAY)]},
        {"id": "crafts", "area": "town", "populations": [
            per("brickmaker", "p_brickfield", 2, "work"), per("kiln_worker", "p_kiln", 1, "work"),
            pop("dyer", "work", 10), pop("goldsmith", "work", 4), pop("grinder", "houses", 8),
            pop("town_scribe", "work", 4), pop("porter", "work", 8), pop("child", "children", 6),
            pop("baker", "kitchen", 4), pop("workman", "work", 16, when=RATION_DAY),
            pop("grinder", "work", 8, when=RATION_DAY)]},
        {"id": "village", "area": "country", "populations": [
            pop("farmer", "dawn_work", 16), pop("zebu", "work", 4), pop("townswoman", "houses", 10),
            pop("child", "children", 4), pop("baker", "kitchen", 4), pop("dog", "day", 2)]},
        {"id": "fields", "area": "country", "populations": [
            pop("farmer", "dawn_work", 22), pop("stork", "day", 2, when=SPRING), pop("dog", "day", 1)]},
        {"id": "stables", "area": "country", "populations": [
            pop("groom", "dawn_work", 12), pop("horse", "graze", 14)]},
        {"id": "river", "area": "wild", "populations": [
            pop("stork", "day", 3, when=SPRING), pop("farmer", "dawn_work", 3)]},
        {"id": "station", "area": "road", "populations": [
            pop("station_scribe", "day", 8), pop("caravan_driver", "day", 12), pop("camel", "graze", 10),
            pop("cart", "work", 4),
            pop("groom", "dawn_work", 6)]},
        {"id": "cavalry", "area": "country", "populations": [
            pop("rider", "work", 14), pop("archer", "work", 14), pop("horse", "graze", 4)]},
        {"id": "camp", "area": "town", "populations": camp + [
            pop("camp_servant", "camp", 10), pop("horse", "graze", 4), pop("spearman", "watch", 4)]},
        {"id": "southern_plain", "area": "country", "populations": [
            pop("shepherd", "dawn_work", 4), pop("sheep", "graze", 14), pop("goat", "graze", 6),
            pop("farmer", "dawn_work", 6), pop("dog", "day", 1)]},
        {"id": "naqsh", "area": "country", "populations": [
            per("magus", "p_fire_altar", 1, "day"), pop("shepherd", "dawn_work", 4), pop("goat", "graze", 8),
            pop("sheep", "graze", 8)]},
        {"id": "plain", "area": "country", "populations": [
            pop("farmer", "dawn_work", 14), pop("sheep", "graze", 8), pop("stork", "day", 2, when=SPRING)]},
    ]


# -- chains you can watch ------------------------------------------------------------------------



def chains() -> list[dict]:
    return [
        {"id": "parsa_stone", "name": "Stone for the new hall", "period": 140,
         "hours": ["06:00", "17:30"], "stages": [
             {"slot": P + "quarry.cut", "makes": "world.goods_block", "by": "quarryman"},
             {"carry": "world.goods_block", "from": P + "quarry.cut", "to": P + "hall_100.mason",
              "by": "sledge"},
             {"slot": P + "hall_100.mason", "needs": "world.goods_block", "makes": "world.goods_block",
              "out": P + "hall_100.hoist", "by": "mason", "label": "squared and dressed"},
             {"slot": P + "hall_100.hoist", "sink": "world.goods_block", "by": "column_setter",
              "label": "hoisted and set on its dowel"}]},
        {"id": "parsa_bread", "name": "Bread rations", "period": 110, "hours": ["05:00", "17:00"],
         "stages": [
             {"slot": P + "p_threshing.beside", "makes": "world.goods_sacks", "by": "farmer"},
             {"carry": "world.goods_sacks", "from": P + "p_threshing.beside",
              "to": P + "p_granary.door", "near": "granary_yard", "by": "porter"},
             {"slot": P + "p_granary.door", "needs": "world.goods_sacks", "makes": "world.goods_flour",
              "near": "granary_yard", "by": "grinder"},
             {"carry": "world.goods_flour", "from": P + "p_granary.door", "to": P + "p_oven.beside",
              "near": "granary_yard", "by": "baker"},
             {"slot": P + "p_oven.beside", "needs": "world.goods_flour", "makes": "world.goods_bread",
              "near": "granary_yard", "by": "baker"},
             {"slot": P + "p_oven.beside", "sink": "world.goods_bread", "near": "granary_yard",
              "by": "workman", "label": "rations handed out"}]},
        {"id": "parsa_tablets", "name": "A tablet for the archive", "period": 120,
         "hours": ["06:00", "17:00"], "stages": [
             {"slot": P + "p_scribe_desk.write", "makes": "world.goods_tablet", "near": "granary_yard",
              "by": "town_scribe"},
             {"carry": "world.goods_tablet", "from": P + "p_scribe_desk.write", "to": "node:archive",
              "near": "granary_yard", "by": "treasury_scribe"},
             {"slot": "node:archive", "sink": "world.goods_tablet", "by": "treasury_scribe",
              "label": "filed in a basket in the fortification"}]},
        {"id": "parsa_gifts", "name": "Gifts of the peoples", "period": 80,
         "hours": ["06:30", "16:00"], "season": ["spring"], "event": "spring_audience", "stages": [
             {"slot": "node:delegation_camp", "makes": "world.goods_gift_vessels",
              "by": "camp_servant", "label": "gifts unpacked in the camp"},
             {"carry": "world.goods_gift_vessels", "from": "node:delegation_camp",
              "to": P + "apadana.audience", "by": "del_lydians_bearer", "units": 3, "workers": 2},
             {"carry": "world.goods_gift_vessels", "from": P + "apadana.audience",
              "to": "node:treasury_door", "by": "del_lydians_bearer", "units": 3, "workers": 2},
             {"slot": "node:treasury_door", "sink": "world.goods_gift_vessels", "by": "treasury_scribe",
              "label": "weighed, recorded and stored"}]},
        {"id": "parsa_wool", "name": "Wool to robes", "period": 160, "hours": ["06:00", "17:30"],
         "stages": [
             {"slot": "node:sheepfold", "makes": "world.goods_fleece", "by": "shepherd"},
             {"carry": "world.goods_fleece", "from": "node:sheepfold", "to": P + "p_jars.beside",
              "near": "dye_yard", "by": "porter"},
             {"slot": P + "p_jars.beside", "needs": "world.goods_fleece", "makes": "world.goods_yarn",
              "near": "dye_yard", "by": "dyer"},
             {"carry": "world.goods_yarn", "from": P + "p_jars.beside", "to": P + "p_loom.weave",
              "near": "dye_yard", "by": "dyer"},
             {"slot": P + "p_loom.weave", "needs": "world.goods_yarn", "makes": "world.goods_cloth",
              "near": "weavers", "by": "weaver"},
             {"carry": "world.goods_cloth", "from": P + "p_loom.weave", "to": "node:palace_court",
              "near": "weavers", "by": "royal_servant"},
             {"slot": "node:palace_court", "sink": "world.goods_cloth", "by": "courtier",
              "label": "a new robe for the court"}]},
        {"id": "parsa_bricks", "name": "Glazed bricks", "period": 150, "hours": ["06:00", "17:30"],
         "stages": [
             {"slot": P + "p_brickfield.mould", "makes": "world.goods_brick", "near": "brickfield",
              "by": "brickmaker"},
             {"carry": "world.goods_brick", "from": P + "p_brickfield.mould", "to": P + "p_kiln.beside",
              "near": "brickfield", "by": "porter"},
             {"slot": P + "p_kiln.beside", "needs": "world.goods_brick",
              "makes": "world.goods_glazed_brick", "near": "brickfield", "by": "kiln_worker"},
             {"carry": "world.goods_glazed_brick", "from": P + "p_kiln.beside",
              "to": P + "paradise_gate.beside", "near": "brickfield", "by": "workman", "units": 2},
             {"slot": P + "paradise_gate.beside", "sink": "world.goods_glazed_brick",
              "by": "wall_decorator", "label": "set into the gate's glazed panels"}]},
        {"id": "parsa_cedar", "name": "Cedar from Lebanon", "period": 200, "hours": ["07:00", "17:00"],
         "stages": [
             {"slot": "node:caravan_yard", "makes": "world.goods_logs", "by": "caravan_driver"},
             {"carry": "world.goods_logs", "from": "node:caravan_yard", "to": P + "p_crane.beside",
              "by": "cart", "units": 2, "workers": 2},
             {"slot": P + "p_crane.beside", "sink": "world.goods_logs", "by": "carpenter",
              "label": "a roof beam laid on the capitals"}]},
        {"id": "parsa_table", "name": "The king's table", "period": 90, "hours": ["16:00", "21:00"],
         "stages": [
             {"slot": P + "p_oven.beside", "makes": "world.goods_dish", "near": "royal_kitchens",
              "by": "baker"},
             {"carry": "world.goods_dish", "from": P + "p_oven.beside",
              "to": "node:hadish_stair_w.head", "near": "royal_kitchens", "by": "royal_servant"},
             {"slot": "node:hadish_stair_w.head", "sink": "world.goods_dish", "by": "royal_servant",
              "label": "served at the king's dinner"}]},
    ]


# -- the calendar and events -----------------------------------------------------------------------

FESTIVALS = [
    {"id": "spring_audience", "season": "spring", "hours": ["06:30", "13:00"]},
    {"id": "harvest_offering", "season": "summer", "day": 1, "hours": ["07:00", "12:00"]},
    {"id": "bagayadi", "season": "autumn", "day": 1, "hours": ["05:00", "10:00"]},
    {"id": "fire_evening", "season": "winter", "day": 1, "hours": ["18:00", "21:00"]},
]


def events() -> list[dict]:
    ev = [
        {"id": "spring_audience", "rarity": "festival", "size": "large", "card": "new_year",
         "trigger": {"on": "calendar", "festival": "spring_audience", "hours": ["06:30", "07:00"]},
         "duration": [240, 290],
         "cast": [{"rotate": [f"delegation_{p}" for p in PEOPLES], "count": 3, "spacing_s": 40},
                  {"role": "spearman", "count": 4, "from": "district"},
                  {"actor": P + "xerxes", "count": 1}, {"actor": P + "parasol_bearer", "count": 1},
                  {"actor": P + "maus", "count": 1}],
         "route": ["delegation_camp", "royal_road_end", "great_stair_foot", "stair_top",
                   "gate_all_lands", "apadana_stair_n.foot", "north_court", "treasury_door"],
         "steps": [go(node="great_stair_foot"), go(node="stair_top"), go(node="gate_all_lands"),
                   go(item=P + "apadana", slot="audience"), use(anim="bow", dur=(10, 14)),
                   {"emit": {"sfx": "sfx/parsa/audience.wav"}}, go(node="treasury_door"),
                   wait(dur=(10, 16)), go(node="delegation_camp")],
         "ambience": {"file": "amb/parsa/procession.ogg", "gain": 0.8}, "string": "audience"},
        {"id": "guard_change_dawn", "rarity": "daily", "size": "medium",
         "trigger": {"on": "window", "hours": ["03:30", "04:00"], "chance": 1.0},
         "duration": [60, 75], "cast": [{"group": "guard_relief"}],
         "route": ["garrison_gate", "hall_forecourt", "gate_all_lands", "stair_top"],
         "steps": [go(node="hall_forecourt"), go(node="gate_all_lands"), go(node="stair_top"),
                   {"emit": {"sfx": "sfx/parsa/horn.wav"}}, go(node="garrison_gate")],
         "string": "guard_change"},
        {"id": "guard_change_dusk", "rarity": "daily", "size": "medium",
         "trigger": {"on": "window", "hours": ["18:00", "18:30"], "chance": 1.0},
         "duration": [60, 75], "cast": [{"group": "guard_relief"}],
         "route": ["garrison_gate", "hall_forecourt", "gate_all_lands", "stair_top"],
         "steps": [go(node="hall_forecourt"), go(node="gate_all_lands"), go(node="stair_top"),
                   {"emit": {"sfx": "sfx/parsa/horn.wav"}}, go(node="garrison_gate")]},
        {"id": "fire_offering", "rarity": "daily", "size": "small", "zone": "terrace",
         "trigger": {"on": "window", "hours": ["04:00", "04:30"], "chance": 1.0},
         "duration": [60, 90], "cast": [{"role": "magus", "count": 2, "from": "district"}],
         "steps": [go(item=P + "p_fire_altar", slot="tend", within=8), use(anim="pour", dur=(20, 30)),
                   {"emit": {"sfx": "sfx/parsa/chant.wav"}}, use(anim="talk", dur=(30, 40))],
         "card": "auramazda"},
        {"id": "water_turn", "rarity": "daily", "size": "small", "zone": "paradise",
         "trigger": {"on": "window", "hours": ["04:30", "05:30"], "chance": 1.0},
         "duration": [60, 90], "cast": [{"role": "gardener", "count": 3, "from": "district"},
                                        {"actor": P + "irdumartiya", "count": 1}],
         "steps": [{"each": {"item": P + "p_sluice", "max": 3, "order": "nearest"},
                    "do": [go(each=True), use({"each": True}, anim="work_low", dur=(6, 10),
                                              state="open")]}],
         "card": "paradise"},
        {"id": "ration_day", "rarity": "uncommon", "size": "medium", "zone": "crafts",
         "trigger": {"on": "window", "hours": ["07:00", "07:30"], "days": {"every": 4, "offset": 3},
                     "chance": 1.0},
         "duration": [300, 360],
         "cast": [{"role": "workman", "count": 10, "from": "district"},
                  {"role": "town_scribe", "count": 3, "from": "district"},
                  {"role": "grinder", "count": 4, "from": "district"},
                  {"actor": P + "mithradata", "count": 1}],
         "steps": [go(node="granary_yard"), use(item=P + "p_scribe_desk", slot="write", anim="write",
                                                dur=(10, 14)),
                   {"take": "world.goods_sacks"}, go(node="workers_quarter")],
         "string": "ration_day", "card": "rations"},
        {"id": "tishtrya", "rarity": "rare", "size": "small", "zone": "slope",
         "trigger": {"on": "weather", "kind": "rain", "season": ["spring"], "chance": 0.3},
         "duration": [60, 180], "cast": [{"actor": P + "tishtrya", "count": 1}],
         "steps": [go(node="mountain_shrine"), use(anim="idle", until={"weather": "clear"})],
         "card": "tishtrya", "string": "tishtrya"},
        {"id": "storyteller", "rarity": "daily", "size": "medium", "zone": "forecourt",
         "trigger": {"on": "window", "hours": ["18:30", "19:00"], "chance": 1.0},
         "duration": [120, 150],
         "cast": [{"actor": P + "storyteller", "count": 1}, {"role": "child", "count": 6},
                  {"role": "workman", "count": 3}, {"actor": P + "dadush", "count": 1},
                  {"actor": P + "udusana", "count": 1}],
         "steps": [go(item=P + "great_stair", slot="storyteller"), use(anim="sit", dur=(10, 15)),
                   use(anim="talk", dur=(90, 110))],
         "tales": ["yima", "erexsa", "thraetaona"], "string": "storyteller"},
        {"id": "royal_ride", "rarity": "uncommon", "size": "medium",
         "trigger": {"on": "window", "hours": ["14:00", "15:00"], "chance": 0.4},
         "duration": [90, 120], "cast": [{"group": "royal_ride"}],
         "route": ["palace_court", "south_stair.head", "south_stair.foot", "cavalry_ground",
                   "archery_ground"],
         "steps": [go(node="south_stair.foot"), go(node="cavalry_ground"), go(node="archery_ground"),
                   go(node="south_stair.foot")],
         "sfx": "sfx/parsa/horse_bells.wav"},
        {"id": "tablets_drying", "rarity": "daily", "size": "small", "zone": "crafts",
         "trigger": {"on": "window", "hours": ["11:30", "12:00"], "chance": 1.0},
         "duration": [120, 150], "cast": [{"role": "town_scribe", "count": 2, "from": "district"}],
         "steps": [go(node="granary_yard"), use(item=P + "p_scribe_desk", slot="write", anim="write",
                                                dur=(60, 90))], "card": "archives"},
        {"id": "court_dines", "rarity": "daily", "size": "small", "zone": "palaces",
         "trigger": {"on": "window", "hours": ["18:30", "19:00"], "chance": 1.0},
         "duration": [90, 120], "cast": [{"role": "royal_servant", "count": 6, "from": "district"},
                                         {"role": "musician", "count": 2}],
         "route": ["royal_kitchens", "hadish_kitchens", "palace_court"],
         "steps": [go(node="royal_kitchens"), {"take": "world.goods_dish"}, go(node="hadish_kitchens"),
                   go(item=P + "hadish", slot="stroll"), {"put": "world.goods_dish"}]},
        {"id": "torches_lit", "rarity": "daily", "size": "small", "zone": "terrace",
         "trigger": {"on": "window", "hours": ["18:30", "19:00"], "chance": 1.0},
         "duration": [60, 90], "cast": [{"role": "royal_servant", "count": 2}],
         "steps": [{"each": {"item": P + "p_torch", "max": 7, "order": "route"},
                    "do": [go(each=True), use({"each": True}, anim="serve", dur=(2, 3),
                                              state="lit")]}]},
        {"id": "pavilion_music", "rarity": "common", "size": "small", "zone": "paradise",
         "trigger": {"on": "window", "hours": ["20:00", "21:00"], "chance": 0.7},
         "duration": [150, 200], "cast": [{"role": "musician", "count": 3},
                                          {"actor": P + "amestris", "count": 1}],
         "steps": [go(item=P + "pavilion", slot="music"), use(anim="play", dur=(140, 180))]},
        {"id": "caravan_dusk", "rarity": "daily", "size": "medium",
         "trigger": {"on": "window", "hours": ["17:00", "17:30"], "chance": 1.0},
         "duration": [90, 110], "cast": [{"group": "caravan"}],
         "route": ["royal_road_w", "royal_road_end", "caravan_yard"],
         "steps": [go(node="royal_road_end"), go(node="caravan_yard"),
                   {"emit": {"sfx": "sfx/parsa/camel.wav"}}, wait(dur=(60, 90))],
         "string": "caravan"},
        {"id": "gulf_caravan", "rarity": "rare", "size": "medium",
         "trigger": {"on": "window", "hours": ["08:00", "10:00"], "chance": 0.15},
         "duration": [150, 200], "cast": [{"group": "gulf_caravan"}],
         "route": ["pasargadae_n", "paradise_gate_w", "caravan_yard"],
         "steps": [go(node="paradise_gate_w"), go(node="caravan_yard"),
                   {"emit": {"sfx": "sfx/parsa/camel.wav"}}]},
        {"id": "courier_relay", "rarity": "common", "size": "small",
         "trigger": {"on": "window", "hours": ["07:00", "17:00"], "every": 7200},
         "duration": [30, 45], "cast": [{"actor": P + "courier", "count": 1},
                                        {"role": "groom", "count": 1}],
         "route": ["royal_road_w", "royal_road_station"],
         "steps": [go(node="royal_road_station"), use(item=P + "road_station", slot="seal_check",
                                                      anim="idle", dur=(4, 6))],
         "sfx": "sfx/world/gallop.wav", "card": "royal_road"},
        {"id": "flock_out", "rarity": "daily", "size": "small", "zone": "southern_plain",
         "trigger": {"on": "window", "hours": ["05:00", "05:30"], "chance": 1.0},
         "duration": [90, 120], "cast": [{"group": "flock"}],
         "steps": [go(node="sheepfold"), wander(zone="southern_plain", dur=(80, 100))],
         "sfx": "sfx/world/sheep_bells.wav"},
        {"id": "flock_home", "rarity": "daily", "size": "small", "zone": "southern_plain",
         "trigger": {"on": "window", "hours": ["17:30", "18:00"], "chance": 1.0},
         "duration": [90, 120], "cast": [{"group": "flock"}],
         "steps": [go(node="sheepfold")], "sfx": "sfx/world/sheep_bells.wav"},
        {"id": "storks", "rarity": "common", "size": "small", "zone": "plain",
         "trigger": {"on": "window", "hours": ["07:00", "17:00"], "season": ["spring"], "every": 3600},
         "duration": [10, 12], "cast": [{"role": "stork", "count": 1}],
         "steps": [use(anim="idle", dur=(8, 10))], "sfx": "sfx/parsa/stork.wav"},
        {"id": "kiln_opening", "rarity": "common", "size": "small", "zone": "crafts",
         "trigger": {"on": "chain", "chain": "parsa_bricks", "stage": 2},
         "duration": [40, 60], "cast": [{"actor": P + "bel_iddin", "count": 1},
                                        {"role": "child", "count": 2}],
         "steps": [go(item=P + "p_kiln", spot="beside", within=4), use(anim="stir", dur=(20, 30))]},
        {"id": "hound_steals_bread", "rarity": "uncommon", "size": "small", "zone": "workers",
         "trigger": {"on": "reactive", "when": {"near": {"actor": P + "hound", "item": P + "p_oven",
                                                         "within": 2, "goods": "world.goods_bread"}}},
         "duration": [6, 8], "cast": [{"actor": P + "hound", "count": 1}],
         "steps": [go(item=P + "p_oven", spot="beside"), {"take": "world.goods_bread"}, wander(radius=8, dur=(4, 6))]},
        {"id": "judge", "rarity": "uncommon", "size": "small", "zone": "audience",
         "trigger": {"on": "window", "hours": ["09:00", "11:00"], "chance": 0.3},
         "duration": [90, 120], "cast": [{"role": "median_official", "count": 1},
                                         {"role": "workman", "count": 2}],
         "steps": [go(item=P + "tripylon", slot="guard"), use(anim="talk", dur=(80, 100))],
         "card": "law"},
        {"id": "saena", "rarity": "uncommon", "size": "small", "zone": "slope",
         "trigger": {"on": "window", "hours": ["04:30", "05:30"], "chance": 0.4},
         "duration": [20, 30], "cast": [{"actor": "world.eagle", "count": 1, "stand_in": "parsa.saena"}],
         "steps": [go(node="mountain_shrine")], "card": "saena"},
        {"id": "planting", "rarity": "daily", "size": "small", "zone": "paradise",
         "trigger": {"on": "window", "hours": ["07:30", "09:00"], "chance": 1.0},
         "duration": [90, 120], "cast": [{"role": "gardener", "count": 3, "from": "district"}],
         "steps": [wander(zone="paradise", dur=(20, 30)), use(anim="work_low", dur=(50, 70)),
                   use(anim="pour", dur=(10, 15))]},
        {"id": "harvest_offering", "rarity": "festival", "size": "medium", "zone": "village",
         "trigger": {"on": "calendar", "festival": "harvest_offering", "hours": ["07:00", "08:00"]},
         "duration": [180, 240], "cast": [{"role": "farmer", "count": 8, "from": "district"},
                                          {"role": "magus", "count": 1},
                                          {"actor": P + "irdumartiya", "count": 1}],
         "steps": [go(node="threshing_floor"), {"emit": {"sfx": "sfx/parsa/chant.wav"}},
                   use(anim="idle", dur=(120, 160))], "string": "harvest"},
        {"id": "reapers", "rarity": "daily", "size": "medium", "zone": "fields",
         "trigger": {"on": "window", "hours": ["06:00", "07:00"], "season": ["summer"], "chance": 1.0},
         "duration": [180, 220], "cast": [{"role": "farmer", "count": 6, "from": "district"}],
         "steps": [wander(zone="fields", dur=(160, 200))]},
        {"id": "threshing", "rarity": "daily", "size": "medium", "zone": "village",
         "trigger": {"on": "window", "hours": ["09:00", "10:00"], "season": ["summer"], "chance": 1.0},
         "duration": [180, 220], "cast": [{"role": "zebu", "count": 2}, {"role": "farmer", "count": 3}],
         "steps": [go(item=P + "p_threshing", spot="beside"), use(anim="graze", dur=(160, 200))]},
        {"id": "bagayadi_offering", "rarity": "festival", "size": "medium", "zone": "naqsh",
         "trigger": {"on": "calendar", "festival": "bagayadi", "hours": ["05:00", "05:30"]},
         "duration": [150, 200], "cast": [{"role": "magus", "count": 3}, {"role": "townswoman", "count": 6}],
         "steps": [go(item=P + "p_fire_altar", slot="tend", within=8), {"emit": {"sfx": "sfx/parsa/chant.wav"}},
                   use(anim="idle", dur=(120, 160))], "card": "auramazda"},
        {"id": "fire_evening", "rarity": "festival", "size": "large", "zone": "terrace",
         "trigger": {"on": "calendar", "festival": "fire_evening", "hours": ["18:00", "18:30"]},
         "duration": [180, 240], "cast": [{"role": "magus", "count": 3},
                                          {"role": "courtier", "count": 10, "from": "district"},
                                          {"role": "townswoman", "count": 10}],
         "steps": [go(node="north_court"), use(item=P + "p_fire_altar", slot="tend", anim="idle",
                                              dur=(150, 200))], "string": "fire_evening"},
        {"id": "swifts", "rarity": "daily", "size": "small", "zone": "audience",
         "trigger": {"on": "window", "hours": ["18:00", "19:00"], "season": ["spring", "summer"],
                     "chance": 1.0},
         "duration": [60, 90], "cast": [{"actor": "world.swift", "count": 8}],
         "steps": [wander(radius=12, dur=(50, 80))], "sfx": "sfx/world/swifts.wav"},
        {"id": "dogs_bark", "rarity": "common", "size": "small", "zone": "workers",
         "trigger": {"on": "window", "hours": ["21:00", "03:00"], "every": 5400},
         "duration": [5, 6], "steps": [], "sfx": "sfx/world/dog_far.wav"},
        {"id": "dust_breeze", "rarity": "common", "size": "small", "zone": "plain",
         "trigger": {"on": "weather", "kind": "dust", "season": ["summer"], "hours": ["13:00", "17:00"]},
         "duration": [60, 90], "steps": [{"emit": {"fx": P + "dust"}}]},
        {"id": "valley_fog", "rarity": "common", "size": "small", "zone": "fields",
         "trigger": {"on": "weather", "kind": "fog", "season": ["spring", "autumn"],
                     "hours": ["03:00", "06:00"]}, "duration": [90, 120], "steps": []},
        {"id": "carian_visit", "rarity": "festival", "size": "small", "zone": "camp",
         "trigger": {"on": "calendar", "festival": "spring_audience", "hours": ["15:00", "16:00"],
                     "with_group": "delegation_carians"},
         "duration": [90, 120], "cast": [{"actor": P + "artemisia", "count": 1},
                                         {"role": "camp_servant", "count": 2}],
         "steps": [go(item=P + "p_tent", slot="door", within=6), use(anim="bow", dur=(4, 6))],
         "card": "artemisia"},
    ]
    return ev


# -- figures ---------------------------------------------------------------------------------------

def figures() -> list[dict]:
    def fig(actor, presence, card, sch=None, routines=None, **kw):
        f = {"actor": P + actor if actor else None, "presence": presence, "card": card}
        if sch:
            f["schedule"] = sched(*sch)
            f["routines"] = routines
        f.update(kw)
        return {k: v for k, v in f.items() if v is not None}
    return [
        fig("xerxes", "present", "xerxes",
            [("07:00", "11:30", "audience"), ("14:00", "17:30", "terrace")],
            {"audience": {"steps": [go(item=P + "p_throne", slot="seat"),
                                    use(anim="sit", until={"hour": "11:30"})]},
             "terrace": {"loop": True, "steps": [go(item=P + "hadish", slot="stroll"),
                                                 use(anim="gesture", dur=(10, 20)),
                                                 go(node="palace_court"), wait(dur=(20, 40))]}},
            attendants=[{"actor": P + "parasol_bearer", "follow": True, "spacing": 0.7}],
            note="his parasol-bearer walks with him; enthroned under a canopy in the audience"),
        fig("amestris", "present", "amestris", [("09:00", "12:00", "courts"), ("15:00", "19:00", "garden")],
            {"courts": {"loop": True, "steps": [go(node="palace_court"), wait(dur=(30, 50)),
                                                go(node="weavers"), wait(dur=(20, 30))]},
             "garden": {"steps": [go(item=P + "pavilion", slot="music"), use(anim="sit", until={"hour": "19:00"})]}}),
        fig("artaxerxes", "present", "artaxerxes", [("07:00", "11:00", "learn")],
            {"learn": {"loop": True, "steps": [go(node="archery_ground"), use(anim="shoot", dur=(20, 30)),
                                               go(node="cavalry_ground"), wait(dur=(20, 30))]}}),
        fig("maus", "present", "maus", [("07:00", "12:30", "weigh"), ("14:00", "17:00", "seal")],
            {"weigh": {"loop": True, "steps": [go(item=P + "p_scales", spot="beside", within=6),
                                               use(anim="serve", dur=(20, 30)), use(anim="write", dur=(20, 30))]},
             "seal": {"loop": True, "steps": [go(node="treasury_door"), use(anim="write", dur=(30, 50))]}}),
        fig("artemisia", "visitor", "artemisia", note="cast with the Carian delegation (carian_visit)"),
        fig("darius", "memory", "darius", [("18:30", "22:00", "memory")],
            {"memory": {"steps": [go(node="tacara_stair_s.foot"), use(anim="gesture", dur=(20, 30)),
                                  use(anim="idle", until={"hour": "22:00"})]}}, translucent=True),
        fig("atossa", "memory", "atossa", [("18:30", "22:00", "memory")],
            {"memory": {"steps": [go(node="palace_court"), use(anim="idle", until={"hour": "22:00"})]}},
            translucent=True),
        fig("irtashduna", "memory", "irtashduna", [("18:30", "21:30", "memory")],
            {"memory": {"steps": [use({"item": P + "pavilion", "slot": "music"}, anim="sit",
                                      until={"hour": "21:30"})]}}, translucent=True,
            note="appears seated at the pavilion; her kind has no walk"),
        fig("parnakka", "memory", "parnakka", [("18:30", "21:30", "memory")],
            {"memory": {"steps": [go(node="granary_yard"),
                                  use(item=P + "p_scribe_desk", slot="write", anim="write",
                                      until={"hour": "21:30"})]}}, translucent=True),
        fig(None, "relief", "gobryas_aspathines", at="naqsh_tomb"),
        fig(None, "shrine", "auramazda", at="north_court"),
        fig("tishtrya", "apparition", "tishtrya", event="tishtrya"),
        fig(None, "tale", "yima", event="storyteller"),
        fig(None, "tale", "erexsa", event="storyteller"),
        fig(None, "tale", "thraetaona", event="storyteller"),
        fig(None, "apparition", "saena", event="saena"),
        fig("mithradata", "present", "mithradata", [("06:30", "12:00", "granary"), ("13:30", "17:00", "treasury")],
            {"granary": {"loop": True, "steps": [go(item=P + "p_scribe_desk", slot="write", within=6),
                                                 use(anim="write", dur=(40, 60))]},
             "treasury": {"loop": True, "steps": [go(node="treasury_door"), use(anim="write", dur=(30, 40))]}}),
        fig("rtakama", "present", "rtakama", [("06:00", "17:30", "lead")],
            {"lead": {"loop": True, "steps": [go(node="weavers"), use(anim="gesture", dur=(10, 15)),
                                              go(item=P + "p_loom", slot="weave", within=4),
                                              use(anim="idle", dur=(15, 20))]}}),
        fig("hermon", "present", "hermon", [("06:00", "11:00", "quarry"), ("13:30", "17:30", "hall")],
            {"quarry": {"loop": True, "steps": [go(item=P + "quarry", slot="cut"), use(anim="work_high", dur=(30, 50))]},
             "hall": {"loop": True, "steps": [go(item=P + "hall_100", slot="mason"),
                                              use(anim="work_high", dur=(30, 50))]}}),
        fig("bel_iddin", "present", "bel_iddin", [("05:30", "17:30", "bricks")],
            {"bricks": {"loop": True, "steps": [go(item=P + "p_brickfield", slot="mould"), use(anim="stir", dur=(30, 40)),
                                                go(item=P + "p_kiln", spot="beside", within=4),
                                                use(anim="stir", dur=(20, 30))]}}),
        fig("pediese", "present", "pediese", [("06:30", "17:30", "gold")],
            {"gold": {"loop": True, "steps": [go(node="goldsmith"),
                                              use(item=P + "p_workshop", slot="work", anim="work_high",
                                                  dur=(40, 60))]}}),
        fig("manes", "present", "manes", [("06:30", "17:30", "roof")],
            {"roof": {"loop": True, "steps": [go(item=P + "p_crane", spot="beside", within=8),
                                              use(anim="work_high", dur=(40, 60))]}}),
        fig("farnadata", "present", "farnadata", [("06:00", "20:00", "station")],
            {"station": {"loop": True, "steps": [go(item=P + "road_station", slot="seal_check"),
                                                 use(anim="write", dur=(30, 50)), go(node="caravan_yard"),
                                                 wait(dur=(10, 15))]}}),
        fig("irdumartiya", "present", "irdumartiya", [("04:30", "11:00", "field"), ("15:00", "18:30", "field")],
            {"field": {"loop": True, "steps": [go(node="village"), wander(zone="fields", dur=(30, 50)),
                                               use(anim="work_low", dur=(30, 50))]}}),
        fig("dadush", "present", "dadush", [("07:00", "18:30", "play")],
            {"play": {"loop": True, "steps": [go(node="brickfield"), use(anim="run", dur=(6, 10)),
                                              go(node="stair_plaza"), wait(dur=(20, 40))]}}),
        fig("udusana", "present", "dadush", [("07:00", "18:30", "play")],
            {"play": {"loop": True, "steps": [go(node="town_square"), use(anim="run", dur=(6, 10)),
                                              go(node="stair_plaza"), wait(dur=(20, 40))]}}),
    ]


# -- cards -----------------------------------------------------------------------------------------

def cards() -> dict:
    F, L, I = "figure", "landmark", "idea"
    c = {
        "xerxes": card(F, "Xšayāršā", "Xerxes, Great King, King of Kings",
            "Xerxes finished what his father began here and built the Gate of All Lands. His "
            "inscriptions say Auramazdā made him king. On the Apadāna stairs, the peoples of an "
            "empire from the Aegean to the Indus bring him gifts; here he receives them enthroned "
            "under a canopy among slender columns."),
        "amestris": card(F, "Amestris", "Queen",
            "Wife of Xerxes and mother of the next king. Greek historians told dark stories about "
            "her; Persian records tell us more about how royal women lived: they owned estates, "
            "travelled with their own staff and sealed their own orders. Here she visits the "
            "weavers of her household and sits in the garden pavilion."),
        "artaxerxes": card(F, "Artaxšaça", "Artaxerxes, a young prince",
            "One day he will finish the Hall of a Hundred Columns. Today he is learning to ride "
            "and draw a bow on the plain below the terrace. Greek writers said Persian boys were "
            "taught three things: to ride, to shoot and to tell the truth. His exact age in 470 is "
            "not known."),
        "maus": card(F, "Mauš", "Treasurer (also written Mawuš)",
            "His name survives on the Treasury tablets of these very years, the receipts of a "
            "working empire. Orders reach him to pay craftsmen partly in weighed silver instead "
            "of barley; he seals each payment and files the record. The gifts the delegations "
            "bring this morning will pass through his doors."),
        "artemisia": card(F, "Artemisia of Caria", "Queen of Halicarnassus (a visit imagined)",
            "A Carian queen who commanded ships for Xerxes at Salamis, as Herodotus tells. Here we "
            "imagine her climbing the stairway with the Carians, who bring a bull, a shield and a "
            "spear on the Apadāna reliefs. Whether she was still alive, or still ruling, in 470 "
            "is not known."),
        "darius": card(F, "Dārayavauš", "Darius, builder of Pārsa (a memory)",
            "Darius chose this mountain foot for a new royal city, raised the terrace and began "
            "the Apadāna. He reorganised the empire's satrapies, fixed weights and coinage, "
            "completed the canal from the Nile to the Red Sea begun by an Egyptian king, and cut "
            "his story into the cliff at Bisitun in three languages."),
        "atossa": card(F, "Atossa", "Daughter of Cyrus (a memory)",
            "Daughter of one king, wife of another, mother of a third. Greek writers made her "
            "powerful and proud. Some scholars think the tablets mention her under the Elamite "
            "name Udusana; others are less sure. At dusk she is remembered in the courts of the "
            "residential wing her son built."),
        "irtashduna": card(F, "Irtašduna", "Artystone, queen of estates (a memory)",
            "The Fortification tablets show this wife of Darius, a daughter of Cyrus, managing "
            "estates, workers and stores in her own name and under her own seal. One order from "
            "the king sends her two hundred jars of wine, each a marriš of about ten litres, and a "
            "hundred sheep."),
        "parnakka": card(F, "Parnakka", "Head of the stores (a memory)",
            "A great Persian noble whose seal, between 506 and 497, moved barley, wine, sheep and "
            "travellers across Fārs. The tens of thousands of clay tablets found in the "
            "fortification wall are largely the paperwork of his office: the most detailed record "
            "of daily life in the empire."),
        "gobryas_aspathines": card(F, "Gaubaruva and Aspačanā", "Spear-bearer and bow-bearer",
            "Carved beside Darius's tomb, each labelled by name and office in three languages: "
            "Gobryas, the king's spear-bearer, and Aspathines, who holds the king's battle-axe. "
            "His title is usually translated bow-bearer, but its meaning is debated. They were "
            "the closest companions of the throne."),
        "auramazda": card(F, "Auramazdā", "The great god of the inscriptions",
            "Every royal inscription begins with him: creator of earth, sky, people and happiness. "
            "The tablets also show offerings to other gods, Iranian and Elamite. The winged "
            "figure in a disc above the reliefs may be him, or the king's fortune; scholars still "
            "debate it. Known in Iran today as the Faravahar, it is a cherished symbol."),
        "tishtrya": card(F, "Tištrya", "The rain star",
            "In the Avesta, the star Sirius takes the shape of a white horse with golden ears, "
            "fights the drought demon on the shore of the cosmic sea and wins rain for the lands. "
            "The hymn was written down many centuries later. Watch the ridge when spring clouds "
            "gather."),
        "yima": card(F, "Yima", "King of the golden age (a tale)",
            "The Avesta's Yima ruled when there was neither heat nor cold, sickness nor death. "
            "Medieval Persians, seeing these ruins, believed only he could have built them, and "
            "called them the Throne of Jamshid. The storyteller tells old Iranian tales; whether "
            "they were told this way in 470 is not known."),
        "erexsa": card(F, "Ərəxša", "The swift archer (a tale)",
            "One line of the Avesta remembers him as the swiftest archer of the Aryans, his arrow "
            "flying like the rain star. The story of the arrow that set a frontier was told by "
            "much later writers. At dusk an arrow's streak crosses the sky over the archery "
            "ground."),
        "thraetaona": card(F, "Θraētaona", "Dragon-slayer (a tale)",
            "In the Avesta, Θraētaona defeats Aži Dahāka, the three-headed dragon. Much later "
            "Ferdowsi retold the tale with new characters; the old hymn is short and fierce, and "
            "was itself written down long after Pārsa. Children at the stairway plaza ask for "
            "it again and again."),
        "saena": card(F, "Saēna", "The great bird",
            "The Avesta names the saēna bird. Later Persian books made it the Simurgh, wise and "
            "healing, nesting in the tree of all seeds. The hymns that name it were written down "
            "much later. At dawn, sometimes, a great shadow crosses the mountain behind the "
            "terrace."),
        "mithradata": card(F, "Miθradāta", "Scribe",
            "Miθradāta writes in two worlds: Aramaic in ink on soft leather, and checks the "
            "Elamite scribes pressing wedges into clay. Every jar of wine, every sack of barley "
            "and every traveller's meal on the royal road ends up on one of his tablets, sealed "
            "and filed."),
        "rtakama": card(F, "Ṛtakāmā", "Overseer of weavers",
            "Ṛtakāmā leads forty weavers. The tablets show women like her drawing the highest "
            "rations in their group, and mothers receiving extra grain after a birth. Her "
            "workshop's patterned cloth will become robes for the court and gifts for honoured "
            "guests."),
        "hermon": card(F, "Hermon", "Stonecutter from Ionia",
            "Hermon came from Ionia to cut stone for the king; at Susa, Darius's building charter "
            "names Ionians and Lydians as the stonecutters. He reads a block by the sound it "
            "makes under his hammer. Today he shapes a column drum for the new hall, paid partly "
            "in barley and partly in weighed silver."),
        "bel_iddin": card(F, "Bēl-iddin", "Brickmaker from Babylon",
            "Bēl-iddin's family has made bricks for generations, in Babylon and now in Pārsa; at "
            "Susa, Darius's charter says Babylonians made the baked bricks. Mudbricks dry in the "
            "sun for walls; the best are fired and glazed in blue and yellow. He stamps each "
            "mould with a careful thumb."),
        "pediese": card(F, "Pediese", "Goldsmith from Egypt",
            "Pediese beats gold into leaf thin enough to float, for door fittings and the edges "
            "of painted reliefs; at Susa, Darius's charter names Medes and Egyptians as "
            "goldsmiths. He also makes armlets with griffin heads like the ones the Lydians bring "
            "as gifts."),
        "manes": card(F, "Manes", "Carpenter from Sardis",
            "Manes fits cedar beams that travelled from Lebanon, across rivers and over "
            "mountains, to rest on the bull capitals; at Susa, Darius's charter names Sardians "
            "and Egyptians as woodworkers. Up on the scaffold the whole plain lies below him, "
            "green with young barley."),
        "farnadata": card(F, "Farnadāta", "Station master",
            "Farnadāta checks every traveller's sealed travel document, the halmi of the tablets, "
            "then hands out flour, beer and fodder by the day. Express riders change horses here "
            "without stopping to talk. His scribes log every ration, so we know what a journey "
            "cost."),
        "irdumartiya": card(F, "Irdumartiya", "Farmer",
            "Irdumartiya, the Elamite rendering of the Persian name Ṛtavardiya, grows barley "
            "along the canal. A share of every harvest goes to the royal stores, and from there "
            "back out as rations for the workers on the terrace. When the water is his turn, he "
            "opens the channel at dawn."),
        "dadush": card(F, "Daduš and Udusana", "Two children",
            "Daduš and his sister count the delegations climbing the stairs: today the Lydians "
            "brought a chariot and the Elamites a lioness with two cubs. They are not allowed on "
            "the terrace. They watch from the plaza anyway, and stay for the storyteller at "
            "dusk."),
        # landmarks
        "apadana": card(L, "Apadāna", "Hall of audience",
            "Darius began it and Xerxes finished it: a hall of 36 columns, 19.5 m tall, with "
            "porticoes of twelve on three sides. In the hall and the north portico the capitals "
            "carry paired bulls on tall volutes; in the west portico, which you see, bulls sit "
            "straight on the fluted shaft, and lions in the east. The north stair's central panel "
            "shows the king enthroned."),
        "great_stair": card(L, "The great stairway", "Double stair to the terrace",
            "Each side climbs 63 shallow steps to a landing and 48 more to the top: 111 steps of "
            "10 cm, 38 cm deep and 6.70 m wide, easy enough to climb in a long robe or leading a "
            "horse. Delegations come up here behind their ushers on audience mornings."),
        "apadana_stair_n": card(L, "The north stair of the Apadāna", "Its face hidden from here",
            "Its reliefs climb in three registers: guards, staff-bearers and nobles on one wing, the "
            "gift-bearing peoples on the other, lions attacking bulls in the corners. In 470 its "
            "central panel shows the king enthroned, the crown prince behind him; later it was "
            "replaced by guards under a winged disc."),
        "apadana_stair_e": card(L, "The east stair of the Apadāna", "The peoples of the empire",
            "Twenty-three delegations climb its reliefs in three registers, each led by the hand by "
            "a Persian or Median usher, each with its gifts: a lioness and cubs, a chariot, gold dust, "
            "a dromedary. Their names and order are partly guessed; the cards say probably where "
            "scholars disagree."),
        "tacara_stair_s": card(L, "The Tačara's south stair", "A relief stair",
            "The stair to Darius's palace is carved with guards and gift-bearers in procession and "
            "an inscription naming the builder. The decorated west stair is later: in 470 that side "
            "is plain."),
        "hadish_stair_w": card(L, "The Hadiš stair", "Servants climbing",
            "Its reliefs show servants carrying food up to the king: lambs, wineskins, covered "
            "dishes. At dusk, real servants climb it with the king's dinner."),
        "tripylon_stair": card(L, "The Tripylon stair", "Nobles in conversation",
            "Persian and Median nobles climb its reliefs side by side, holding flowers, turning to "
            "talk, a hand on a friend's shoulder: the most human scene on the terrace."),
        "gate_all_lands": card(L, "Duvarθi visadahyu", "Gate of All Lands",
            "Xerxes's own name for it: the gate of all lands. Four columns over 16.5 m tall "
            "carry kneeling bulls; plain bulls stride out of the west door, and human-headed "
            "winged bulls, an old Mesopotamian guardian, crown the east. Every visitor to the "
            "terrace passes through."),
        "tacara": card(L, "Tačara", "Palace of Darius",
            "Darius's own word for his building, in the inscription on its walls: \"I built this "
            "tačara\". A small palace of polished dark stone with twelve columns, its portico and "
            "relief stair facing south. Door reliefs show the king walking under a parasol."),
        "hadish": card(L, "Hadiš", "Palace of Xerxes",
            "Xerxes's palace on the highest platform: 36 columns and a portico of twelve. Its "
            "stair reliefs show servants carrying food, wineskins and young goats up to the "
            "king's table, as the servants here still do at dusk."),
        "tripylon": card(L, "Tripylon", "The central hall",
            "A small hall with three doors linking the palaces and the audience halls. On its "
            "stair, Persian and Median nobles climb holding flowers, chatting, a hand on a "
            "friend's shoulder. It may not yet be finished in 470; Shahbazi gives it to Xerxes "
            "and Artaxerxes I."),
        "hall_100": card(L, "Hall of a Hundred Columns", "A building site",
            "Begun by Xerxes and finished by his son, a grid of ten by ten columns nearly 14 m "
            "tall. Today some stand finished, others rise drum by drum under timber cranes. The "
            "portico's capitals are human-headed bulls, and two colossal bulls are still being "
            "roughed out at its door."),
        "treasury": card(L, "The Treasury", "Enlarged by Xerxes",
            "Low mudbrick halls with wooden columns plastered and painted in patterns. Gifts, "
            "silver and tribute were weighed and stored here; its tablets of 492-458 record "
            "wages paid partly in silver. Later the audience relief from the Apadāna stair was "
            "moved here, where archaeologists found it."),
        "harem": card(L, "The residential wing", "Called the harem by its excavators",
            "Rows of apartments around courts, with small columned halls and stone door frames "
            "showing the king. The name harem is modern; who lived here, royal women, officials "
            "or stores, is debated."),
        "garrison": card(L, "Garrison quarters", "Barracks of the guard",
            "Rooms for the royal guard, an armoury and a courtyard for drill behind the terrace. "
            "The Greeks called the king's guard the Immortals; their Persian name is unknown. "
            "Spearmen march out from here at every change of the watch."),
        "south_stores": card(L, "Southern storerooms", "Stores of the terrace",
            "Long rooms for jars of wine, oil and grain, sealed and recorded like everything "
            "else in Pārsa. The court fed thousands: a Greek list of the king's dinner counts "
            "sheep, geese and sacks of flour by the hundred."),
        "cistern": card(L, "The cistern", "Water cut into the rock",
            "A basin cut into the mountain feeds channels that run under the terrace. Drains in "
            "the stone carried rain off the platform; after a spring shower they spout into the "
            "plain."),
        "quarry": card(L, "The quarry", "Where every stone starts",
            "Grey limestone is cut from the mountain behind the terrace: a line marked, a slot "
            "cut, wedges driven, a block levered free. Wedge holes and half-cut blocks are still "
            "there today. Follow a block from here to the new hall."),
        "paradise_gate": card(L, "The glazed gate", "After Tol-e Ajori",
            "A gate faced with glazed bricks, bulls and dragons in yellow and white on blue, "
            "like Babylon's Ishtar Gate. The real one stood 3.5 km to the west, built under "
            "Cyrus or Cambyses; the game sets it in the garden wall."),
        "pavilion": card(L, "The garden pavilion", "Over the channels",
            "An open columned pavilion where the garden's stone channels cross. Carpets inside, "
            "cypress rows on every side, almond and pomegranate in flower. At night musicians "
            "play here."),
        "road_station": card(L, "Royal-road station", "Rations for travellers",
            "A walled yard with stables, a storeroom and a room for the official. Travellers "
            "show a sealed document and receive the day's flour, beer and fodder; riders find "
            "fresh horses waiting."),
        "naqsh_cliff": card(L, "Naqsh-e Rostam", "Tomb of Darius (the name is medieval)",
            "Darius's tomb is a cross cut into the cliff: a palace front with four columns, and "
            "above it the king before a fire altar, standing on a throne carried by thirty "
            "figures of his peoples. Inscriptions in three languages tell what kind of king he "
            "wished to be."),
        "kaba": card(L, "The square tower", "Ka'ba-ye Zartosht (a later name)",
            "A tall square stone tower with blind windows and a single high door, facing "
            "Darius's tomb. Its date and purpose are debated: a tomb, a fire house, a store for "
            "royal records? No one knows."),
        "terrace": card(L, "The terrace", "Platform of the palaces",
            "A platform of fitted grey limestone against the mountain, raised by Darius and "
            "about twelve metres high on its long west face, topped by stepped merlons. "
            "Everything on it was painted: red floors, patterned robes on the reliefs, gold on "
            "the crowns."),
        "fort_wall": card(L, "The fortification", "Wall on the mountain",
            "Mudbrick walls with square towers climb the slope behind the terrace. Inside them "
            "excavators found the Fortification tablets: tens of thousands of receipts for "
            "rations, travel and work from the years 509 to 493."),
        # ideas
        "new_year": card(I, "A New Year at Pārsa?", None,
            "The Persian year began with the month Ādukanaiša, near the spring equinox. Many "
            "scholars, among them the Iranian historian Shapur Shahbazi, think this terrace was "
            "built for the New Year, the festival later called Nowruz; others answer that no "
            "ancient text says so and that the reliefs show an ideal, timeless empire. The name "
            "Nowruz first appears centuries later, in Middle Persian. Whether today's Nowruz, "
            "loved by many millions, reaches back to these stairs, no one can yet prove."),
        "susa_charter": card(I, "An empire of many peoples", "Darius's charter at Susa",
            "Darius's building inscription at Susa names who made his palace there: stonecutters "
            "from Ionia and Sardis, goldsmiths from Media and Egypt, Babylonians for the baked "
            "bricks, cedar from Lebanon carried by Carians and Ionians. Pārsa was built the same "
            "way, by workers of many lands, some of whom had come far from home not by choice."),
        "archives": card(I, "The paperwork of an empire", None,
            "Tens of thousands of clay tablets, most in Elamite, some in Aramaic, recorded every "
            "ration, journey and payment in Fārs. Each was sealed, dried in the sun and filed in "
            "baskets. Together they are the most detailed record of daily life in the ancient "
            "Near East."),
        "royal_road": card(I, "The royal road", None,
            "Stations at fixed stages from Sardis to Susa, with rations for anyone carrying a "
            "sealed document and fresh horses for the king's riders. Herodotus, a Greek outsider, "
            "wrote admiringly that nothing mortal travels faster than these messengers, passing "
            "the message from rider to rider."),
        "paradise": card(I, "Paradise", "A walled garden",
            "The Elamite tablets call such estates partetaš; the Old Persian word is reconstructed "
            "as paridaida. The Greeks borrowed it as paradeisos, and English made it paradise: a "
            "walled garden of channels, orchards and shade, its water opened turn by turn at "
            "dawn."),
        "guardians": card(I, "Borrowed guardians", "Art from every land",
            "Human-headed winged bulls came from Assyria, the cavetto cornices over the doors "
            "from Egypt, the stone-cutting skills from Ionia and Lydia. The Persian kings took "
            "the art of every people they ruled and made it their own, a new style meant to show "
            "an empire at peace."),
        "religion": card(I, "Fire and the gods", "And the limits of tolerance",
            "Fire altars stand before the king on the reliefs, and magi tend them at dawn. "
            "Herodotus wrote that Persians used no altars and no fire in sacrifice, a Greek "
            "outsider's claim the reliefs contradict. Kings honoured many gods, yet Xerxes's own "
            "inscription boasts of destroying a sanctuary of false gods: tolerance had limits."),
        "standards": card(I, "Weights and canals", None,
            "Ten shekels made a karša of about 83 grams, and silver was weighed, not counted; "
            "Darius's gold darics were rare in Fārs. His inscriptions by the Red Sea boast of a "
            "canal from the Nile, begun by an Egyptian king, that carried ships to Persia."),
        "takht_e_jamshid": card(I, "Takht-e Jamshid", "The Throne of Jamshid",
            "Medieval Persians, finding the ruins, named them for the legendary king Jamshid, the "
            "Yima of the Avesta. The name is about 1,500 years later than the moment shown here; "
            "the city's own name was Pārsa, like the land and its people."),
        "qanat": card(I, "Water under the plain", "A qanat (careful)",
            "A line of shaft mounds marks a tunnel leading groundwater to the fields. Such qanats "
            "were known in the empire, one dated in Achaemenid Egypt, but none at Pārsa is dated "
            "to 470: the game shows one as a reasonable guess."),
        "rations": card(I, "Rations and wages", None,
            "Workers drew monthly rations of barley, with wine, beer or sheep for higher grades; "
            "by now part was paid in weighed silver. The tablets show mothers given extra grain "
            "after a birth, twice as much for a boy, and women overseers drawing the highest "
            "rations."),
        "law": card(I, "The king's law", None,
            "Darius's inscriptions speak of his dāta, his law, and of rewarding the loyal and "
            "punishing the liar. Greek writers mention royal judges. In a portico a dispute is "
            "heard: two workmen and an official in Median dress, talking it through until "
            "they agree."),
        "kurtash": card(I, "The kurtaš", "Working people of many lands",
            "The tablets call the workers kurtaš: men, women and children of many origins, with "
            "families, names and regular rations. Some were hired, some deported, some attached "
            "to estates; their status varied and is debated. The game shows them as they were "
            "in the tablets: working people. They built Pārsa."),
        # roles
        "courtier": card("role", "Persian noble", None, "In a long pleated robe and a fluted "
                         "cap, he attends the audience and walks the terrace with a friend, as "
                         "the nobles do on the Tripylon stair."),
        "usher": card("role", "Usher", None, "In Median dress, staff in hand, the usher leads "
                      "each delegation by the hand up to the king and presents it."),
        "spearman": card("role", "Spearman of the guard", None, "Robed, with a tall spear whose "
                         "butt is a silver pomegranate and a bow on his back. Greeks called the "
                         "king's guard the Immortals."),
        "mede_guard": card("role", "Guard in Median dress", None, "Tunic, trousers and a bow "
                           "case on the hip; at night he walks the wall with a torch."),
        "magus": card("role", "Magus", None, "The tablets call them makuš. Hood drawn over the "
                      "mouth, a bundle of twigs in hand, he feeds the fire at dawn and dusk."),
        "servant": card("role", "Servant of the court", None, "Carries water to the kitchens by "
                        "day and dishes up the Hadiš stair at dusk, as on its reliefs."),
        "household_woman": card("role", "Woman of a royal household", None, "The tablets show "
                                "royal women with households of their own: weavers, cooks and "
                                "stewards who come and go between the courts."),
        "musician": card("role", "Court musician", None, "An angular harp, pipes or a frame "
                         "drum; Greek writers say many women sang and played at the Persian "
                         "court."),
        "quarryman": card("role", "Quarryman", None, "Marks a line, cuts a slot, drives the "
                          "wedges and levers a block free of the mountain."),
        "mason": card("role", "Mason", None, "Squares and dresses each drum in the yard, then "
                      "sees it slung, hoisted and set on its dowel."),
        "carpenter": card("role", "Carpenter", None, "Saws and fits cedar beams for the roof of "
                          "the new hall, high on the scaffold."),
        "sculptor": card("role", "Relief sculptor", None, "Sketches in red, roughs out, models "
                         "and smooths: a procession of figures in calm profile."),
        "scribe": card("role", "Scribe", None, "Presses wedges into damp clay, rolls a seal "
                       "across it and leaves it in the sun to dry."),
        "porter": card("role", "Porter", None, "Carries sacks from the threshing floors and the "
                       "stores to the granary yard."),
        "weaver": card("role", "Weaver", None, "Works an upright loom in a workshop of women; "
                       "her cloth becomes robes for the court."),
        "brickmaker": card("role", "Brickmaker", None, "Mixes clay with straw and water, fills "
                           "a wooden mould and lays the bricks in rows to dry."),
        "wall_decorator": card("role", "Wall decorator", None, "At Susa, Darius's charter says "
                               "Medes and Egyptians decorated the walls. Here they set glazed "
                               "bricks into the gate's bulls and dragons."),
        "goldsmith": card("role", "Goldsmith", None, "Melts, hammers, punches and polishes gold "
                          "for door fittings, armlets and vessels."),
        "dyer": card("role", "Dyer", None, "Soaks wool in vats of madder, woad and weld by the "
                     "canal, then rinses and hangs it."),
        "grinder": card("role", "Grinder", None, "Grinds barley on a saddle quern, sifts it and "
                        "bags the flour for the ovens."),
        "baker": card("role", "Baker", None, "Slaps rounds of dough on the inside wall of a "
                      "tanūr oven and peels them off, crisp."),
        "child": card("role", "Child", None, "The tablets list rations for boys and girls. "
                      "They run by the canal, play knucklebones and watch the delegations."),
        "elamite_priest": card("role", "Elamite priest", None, "Pours offerings for Humban and "
                               "other Elamite gods, whom the tablets show the state supplied."),
        "gardener": card("role", "Gardener of the paradise", None, "Opens the channels at "
                         "dawn, waters, plants and prunes the royal orchards."),
        "farmer": card("role", "Farmer", None, "Hoes young barley along the canals; a share of "
                       "his harvest goes to the royal stores."),
        "groom": card("role", "Groom", None, "Waters, brushes and exercises the horses, which "
                      "draw rations of their own in the tablets."),
        "nisaean_horse": card("role", "Nisaean horse", None, "The famous horses of Media, "
                              "tails tied, forelocks bunched in a topknot."),
        "archer": card("role", "Archer", None, "Strings his bow, draws, looses and walks to "
                       "the butts to collect his arrows."),
        "shepherd": card("role", "Shepherd", None, "Leads the flock out at dawn with a dog and "
                         "brings it home to the fold at dusk."),
        "hoopoe": card("role", "Hoopoe", None, "A crested, barred bird probing the garden "
                       "beds for grubs, calling hoo-poo-poo."),
        "station": card("role", "Station scribe", None, "Reads each traveller's sealed "
                        "document and logs the flour, beer and fodder issued."),
    }
    for people, (name, _a, text) in PEOPLES.items():
        c[f"delegation_{people}"] = card("delegation", name, "A delegation", text)
    return c


STRINGS = {
    "first_visit": "Pārsa, around the spring equinox of 470 BC. The barley is green, snow lies on "
                   "the mountain, and the first delegation is forming up at the foot of the stair.",
    "audience": "The spring audience begins: three delegations climb the great stair.",
    "guard_change": "A horn: the guard changes at the stairway and the Gate.",
    "ration_day": "Ration day: barley and bread are handed out at the granary yard.",
    "storyteller": "At the stairway plaza an old storyteller begins a tale.",
    "tishtrya": "Spring rain. On the ridge, for a moment, a white horse.",
    "caravan": "A caravan comes down the Royal Road at dusk.",
    "harvest": "The harvest offering at the threshing floor.",
    "fire_evening": "The fire evening: people gather at the altars on the terrace.",
    "decorate_zone": "A walled plot in the paradise, with channels to lay and trees to plant.",
}


def theme(view) -> dict:
    zones = [{"rect": grid_rect(view, d), "file": "amb/parsa/channels.ogg", "gain": 0.7}
             for d in ("paradise", "garden_strip", "river")]
    zones += [{"rect": grid_rect(view, d), "file": "amb/parsa/site.ogg", "gain": 0.8,
               "hours": ["06:00", "18:00"]} for d in ("building_site", "quarry")]
    return {
        # Multipliers on the engine's own phase grade (world-tech §2.6: [1, 1, 1] is the
        # corner's look). The corner's night is the reference for a readable night, so these stay
        # near 1 and only lean: honey-gold dawn, clear slightly cool day, rose-copper dusk, a
        # cool high-desert night a touch darker than the corner's (bright stars, no city glow).
        "grading": {"dawn": [1.03, 0.98, 0.92], "day": [0.98, 0.99, 1.0],
                    "dusk": [1.02, 0.93, 0.90], "night": [0.92, 0.95, 1.04]},
        "haze": {"colour": [0.84, 0.86, 0.90], "strength": 0.12, "toward": "west"},
        "weather": {
            "spring": {"showers": 1, "clouds": 3, "wind": 0.35, "wind_from": "north-west",
                       "note": "rare, memorable showers build over the mountain in the afternoon"},
            "summer": {"showers": 0, "clouds": 1, "wind": 0.45, "dust": 2,
                       "note": "dust breezes after dry days; the court is away"},
            "autumn": {"showers": 0, "clouds": 1, "wind": 0.3, "fog": 1},
            "winter": {"showers": 2, "clouds": 4, "wind": 0.4, "snow": True,
                       "note": "snow on the ridge, few travellers"}},
        "ambience": {
            "beds": [{"file": "amb/parsa/plain_day.ogg", "hours": ["05:00", "19:00"]},
                     {"file": "amb/parsa/plain_night.ogg", "hours": ["19:00", "05:00"]},
                     {"file": "amb/parsa/rain.ogg", "weather": "rain"}],
            "zones": zones,
            "loops": [{"slot": P + "p_loom.weave", "file": "amb/world/loom.ogg", "when": "worked"},
                      {"slot": P + "p_workshop.work", "file": "amb/world/smith.ogg", "when": "worked"},
                      {"slot": P + "p_fire_altar.tend", "file": "amb/world/brazier.ogg", "when": "lit"},
                      {"item": P + "p_brazier", "file": "amb/world/brazier.ogg", "when": "lit"}],
            "one_shots": {"hall_100.mason": "sfx/world/chisel.wav", "quarry.cut": "sfx/world/hammer.wav"}},
        "music": {"day": "music/parsa/day.ogg", "night": "music/parsa/night.ogg"},
        "arrive": "sfx/parsa/arrive.wav",
        "glow": [P + n for n in ("gate_all_lands", "apadana", "tacara", "hadish", "harem", "garrison",
                                 "p_fire_altar", "p_brazier", "p_torch", "p_house", "pavilion")],
    }


def build(view) -> dict:
    return SEASONS.apply({
        "version": 1, "id": "parsa", "name": "Pārsa", "native": "تخت جمشید",
        "caption": "Pārsa · c. 470 BC",
        "era": "The Persian empire of Xerxes · c. 470 BC",
        "theme": theme(view),
        "densities": DENSITIES,
        "districts": districts(),
        "roles": roles(),
        "groups": groups(),
        "chains": chains(),
        "festivals": FESTIVALS,
        "events": events(),
        "days_shown": [{"day": 1, "label": "A spring day: the audience in the morning"},
                       {"day": 3, "label": "Ration day (week day 3)"}],
        "figures": figures(),
        "delegations": [f"delegation_{p}" for p in PEOPLES],
        "lanes_tokens": [],
        "cards": cards(),
        "strings": STRINGS,
        "decorate": {"rect": _decorate(view)},
        "journal": ["landmark:*", "figure:*", "delegation:*", "chain:*", "idea:*"],
    })


def _decorate(view) -> list[int]:
    from worldgen.coords import COLS
    c0, r0 = 1136, 304
    a, b, c, d = c0 + 44, r0 + 9, c0 + 54, r0 + 19
    return [b, COLS - 1 - c, d, COLS - 1 - a]
