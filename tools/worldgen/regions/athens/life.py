"""Athens' life and text: who is where at each hour of a summer day in 432 BC (and, through
`seasons.py`, in every month of the year), what they do,
the chains, the Panathenaic procession and the other events, the figures and every card
(`assets/regions/athens.json`).

Sources: `docs/design/cities/athens.md` as corrected by the fact-check
(`docs/design/cities/fact-check.md` §2): Pheidias only as a dusk memory, with both ancient
versions; no shields on the Painted Stoa (they came in 425 and 421); the rhapsodes' contest
belongs to the Great Panathenaia (434, 430), so in 432 a recital is informal; the robe for Athena
"perhaps"; Kephalos without a workforce number; the Scythians' red rope and its fine as ancient
commentators told it; the Stoa of Zeus at most a fresh building site.
Built by `tools/worldgen/build.sh --city athens`, checked by `worldgen.citylife`.
"""

from __future__ import annotations

from worldgen import citylife as CL
from worldgen import seasonlife as SL
from worldgen.citylife import card, curve, go, grid_rect, pop, role, sched, use, wait, wander

SEASONS = SL.sibling(__file__, "seasons")
SEASON_BEDS = SEASONS.SEASON_BEDS

A = "athens."
ASSEMBLY = {"days": {"every": 4, "offset": 2}}
FEAST = {"festival": "panathenaia"}
WORKDAY = {"not_festival": "panathenaia"}   # the Panathenaia is a holiday for the workshops

DENSITIES = {
    "always": [1.0] * 24,
    "day": curve({0: 0, 5: 0.25, 6: 0.7, 7: 1, 12: 0.8, 14: 0.95, 15: 1, 19: 0.6, 20: 0.3, 21: 0.1,
                  22: 0}),
    "market": curve({0: 0, 5: 0.3, 6: 0.8, 7: 1, 12: 0.75, 14: 0.9, 18: 0.7, 19: 0.4, 20: 0.1,
                     21: 0}),
    "work": curve({0: 0, 5: 0.3, 6: 0.85, 7: 1, 12: 0.65, 14: 1, 18: 0.4, 19: 0}),
    "dawn_work": curve({0: 0, 4: 0.4, 5: 0.9, 6: 1, 12: 0.6, 15: 1, 18: 0.6, 19: 0.2, 20: 0}),
    "houses": curve({0: 0, 4: 0.3, 5: 0.8, 6: 1, 12: 0.7, 14: 0.9, 17: 1, 19: 0.7, 20: 0.4,
                     21: 0.15, 22: 0}),
    "afternoon": curve({0: 0, 6: 0.3, 9: 0.6, 12: 0.7, 14: 1, 18: 0.8, 19: 0.4, 20: 0}),
    "watch": curve({0: 0.5, 5: 0.8, 6: 1, 19: 0.8, 21: 0.5}),
    "evening": curve({0: 0.2, 1: 0, 17: 0.4, 18: 0.8, 19: 1, 22: 0.6, 23: 0.3}),
    "graze": curve({0: 0.2, 5: 0.8, 6: 1, 19: 0.6, 20: 0.2}),
    "children": curve({0: 0, 6: 0.4, 7: 0.9, 8: 1, 12: 0.6, 14: 1, 18: 0.7, 19: 0.3, 20: 0}),
    "harbour": curve({0: 0.1, 4: 0.4, 5: 0.9, 6: 1, 12: 0.75, 14: 1, 18: 0.7, 20: 0.3, 22: 0.1}),
}

RAIN = {"when": {"weather": "rain"}, "routine": "shelter", "priority": 2}


def per(role_, item, count=1, density="always", **kw) -> dict:
    return CL.per(role_, A + item, count, density, **kw)


def shelter_door(within: int = 12) -> dict:
    return {"steps": [go(slot_kind="door", within=within),
                      {"enter": {"here": True}, "until": {"weather": "clear"}}]}


def shelter_stoa() -> dict:
    return {"steps": [go(node="stoa_poikile"), use(anim="idle", until={"weather": "clear"})]}


def roles() -> list[dict]:
    R = []
    # --- the Agora ------------------------------------------------------------------------------
    R.append(role("stall_keeper", A + "working_woman", "Market seller", sched(
        ("05:30", "12:00", "sell"), ("14:00", "19:00", "sell")),
        {"sell": {"loop": True, "steps": [
            go(home="sell"), use({"home": "sell"}, anim="serve", dur=(30, 50), effect="open_shutters"),
            use(anim="idle", dur=(6, 12)), use(anim="serve", dur=(20, 30))]},
         "shelter": shelter_stoa()}, interrupts=[RAIN], home={"item": A + "g_stall", "slot": "sell"},
        card="seller"))
    R.append(role("banker", A + "metic", "Money-changer", sched(("06:30", "12:00", "change"),
                                                               ("14:00", "18:00", "change")),
        {"change": {"loop": True, "steps": [
            go(home="work"), use({"home": "work"}, anim="serve", dur=(30, 50)),
            use(anim="talk", dur=(15, 25))]}}, home={"item": A + "g_table_banker", "slot": "work"},
        card="banker"))
    R.append(role("shopper", A + "citizen", "Citizen", sched(
        ("06:00", "12:00", "market"), ("12:00", "14:30", "shade"), ("14:30", "19:30", "stroll")),
        {"market": {"loop": True, "steps": [
            go(node="market"), wander(radius=5, dur=(20, 40)), use(anim="talk", dur=(10, 20)),
            go(item=A + "g_table_banker", spot="beside", within=6), wait(dur=(6, 12)),
            go(node="stoa_poikile"), use(anim="talk", dur=(15, 25))]},
         "shade": {"steps": [go(node="stoa_poikile"), use(anim="sit", dur=(60, 90))]},
         "stroll": {"loop": True, "steps": [
             go(node="agora"), use(anim="talk", dur=(15, 25)), go(node="royal_stoa"),
             wander(radius=4, dur=(20, 30)), go(node="se_fountain"), wait(dur=(8, 14))]},
         "shelter": shelter_stoa()}, interrupts=[RAIN], card="citizen"))
    R.append(role("elder", A + "elder", "Old man", sched(("07:00", "12:00", "sit"),
                                                       ("15:00", "19:00", "sit")),
        {"sit": {"loop": True, "steps": [
            go(node="stoa_poikile"), use(anim="sit", dur=(60, 100)),
            wander(radius=3, dur=(20, 30))]}, "shelter": shelter_stoa()},
        interrupts=[RAIN], card="elder"))
    R.append(role("porter", A + "enslaved_man", "Porter", sched(
        ("05:30", "12:00", "carry"), ("14:00", "19:00", "carry")),
        {"carry": {"loop": True, "steps": [
            go(node="market"), {"take": "world.goods_sacks"}, go(item=A + "g_stall", slot="buy"),
            {"put": "world.goods_sacks"}, go(node="piraeus_gate"), wait(dur=(10, 20))]}},
        card="porter"))
    R.append(role("archer", A + "scythian", "Scythian archer", sched(
        ("06:00", "20:00", "patrol")),
        {"patrol": {"loop": True, "steps": [
            go(node="agora"), use(anim="guard", dur=(30, 50)), go(node="lawcourt"),
            use(anim="gesture", dur=(6, 10)), go(node="bouleuterion"), use(anim="guard", dur=(20, 40)),
            go(item=A + "horos", spot="beside"), use(anim="guard", dur=(15, 25))]}}, card="scythian"))
    R.append(role("fountain_woman", A + "enslaved_woman", "Water carrier", sched(
        ("04:30", "09:00", "water"), ("16:30", "20:00", "water")),
        {"water": {"loop": True, "steps": [
            go(home="fill"), use({"home": "fill"}, anim="carry_idle", dur=(10, 16)),
            {"take": "athens.goods_hydria"}, go(slot_kind="door", within=14),
            {"put": "athens.goods_hydria"}]}},
        home={"item": A + "se_fountain", "slot": "fill"}, card="water_carrier"))
    R.append(role("philosopher", A + "philosopher", "A talker", sched(
        ("07:00", "12:00", "stoa"), ("14:00", "19:00", "walk")),
        {"stoa": {"loop": True, "steps": [
            go(node="stoa_poikile"), use(anim="talk", dur=(30, 50)), use(anim="gesture", dur=(10, 15)),
            wander(radius=4, dur=(20, 30))]},
         "walk": {"loop": True, "steps": [
             go(node="agora"), use(anim="talk", dur=(20, 30)), go(node="simon_shop"),
             use(anim="gesture", dur=(10, 20)), go(node="stoa_poikile"), wait(dur=(10, 20))]},
         "shelter": shelter_stoa()}, interrupts=[RAIN], card="philosopher"))
    R.append(role("pupil", A + "youth", "Young man", sched(("07:00", "12:00", "listen"),
                                                         ("15:00", "19:00", "listen")),
        {"listen": {"loop": True, "steps": [
            {"follow": {"actor": A + "philosopher"}, "dur": [40, 70], "spacing": 1.0},
            go(node="stoa_poikile"), use(anim="idle", dur=(20, 30))]}}, card="youth"))
    # --- the Council and the courts ------------------------------------------------------------
    R.append(role("councillor", A + "citizen", "Councillor", sched(
        ("06:30", "12:00", "council"), ("14:00", "18:00", "council"), ("18:00", "21:00", "dine")),
        {"council": {"loop": True, "steps": [
            go(item=A + "old_bouleuterion", slot="door"), wait(dur=(20, 30)),
            go(node="royal_stoa"), use(anim="talk", dur=(15, 25)), go(node="tholos"),
            wait(dur=(10, 20))]},
         "dine": {"steps": [go(item=A + "tholos", slot="door"),
                            {"enter": {"here": True}, "until": {"hour": "06:00"}}]}},
        card="councillor"))
    R.append(role("herald", A + "citizen", "Herald", sched(("07:00", "12:00", "proclaim")),
        {"proclaim": {"loop": True, "steps": [
            go(home="herald"), use({"home": "herald"}, anim="talk", dur=(20, 30)),
            use(anim="idle", dur=(30, 60))]}}, home={"item": A + "royal_stoa", "slot": "herald"},
        card="herald"))
    R.append(role("juror", A + "elder", "Juror", sched(("06:30", "12:00", "court")),
        {"court": {"loop": True, "steps": [
            go(item=A + "lawcourt", spot="beside"), use(anim="idle", dur=(40, 70)),
            use(anim="sit", dur=(40, 60))]}}, card="juror"))
    # --- the Kerameikos and the cemetery --------------------------------------------------------
    R.append(role("potter", A + "potter", "Potter", sched(
        ("05:30", "12:00", "throw"), ("14:00", "18:00", "throw")),
        {"throw": {"loop": True, "steps": [
            go(home="throw"), use({"home": "throw"}, anim="throw", dur=(30, 50)),
            use(anim="idle", dur=(4, 8))]}}, home={"item": A + "g_wheel", "slot": "throw"},
        card="potter"))
    R.append(role("vase_painter", A + "painter", "Vase painter", sched(
        ("06:00", "12:00", "paint"), ("14:00", "18:00", "paint")),
        {"paint": {"loop": True, "steps": [
            go(home="throw"), use({"home": "throw"}, anim="write", dur=(40, 60)),
            use(anim="idle", dur=(6, 10))]}}, home={"item": A + "g_workshop", "slot": "throw"},
        card="painter"))
    R.append(role("kiln_man", A + "enslaved_man", "Kiln-man", sched(
        ("05:30", "12:00", "stoke"), ("14:00", "18:30", "stoke")),
        {"stoke": {"loop": True, "steps": [
            go(home="stoke"), use({"home": "stoke"}, anim="work_low", dur=(30, 50)),
            use(anim="carry_idle", dur=(6, 10))]}}, home={"item": A + "g_kiln", "slot": "stoke"},
        card="kiln_man"))
    R.append(role("clay_digger", A + "enslaved_man", "Clay digger", sched(
        ("05:00", "11:30", "dig"), ("14:00", "18:00", "dig")),
        {"dig": {"loop": True, "steps": [
            go(node="cemetery"), wander(radius=4, dur=(10, 20)), use(anim="work_low", dur=(30, 40)),
            {"take": "world.goods_sacks"}, go(node="kerameikos_kilns"), {"put": "world.goods_sacks"},
            use(anim="haul", dur=(10, 15))]}}, card="clay_digger"))
    R.append(role("mourner", A + "woman", "Mourner", sched(("06:00", "11:00", "graves"),
                                                         ("16:00", "19:00", "graves")),
        {"graves": {"loop": True, "steps": [
            go(item=A + "g_grave_stele", slot="mourn"), use(anim="idle", dur=(40, 70)),
            wander(radius=4, dur=(15, 25))]}}, card="mourner"))
    # --- the Acropolis ----------------------------------------------------------------------------
    R.append(role("priestess", A + "priest", "Priest or priestess", sched(
        ("04:30", "12:00", "rites"), ("16:00", "19:30", "rites")),
        {"rites": {"loop": True, "steps": [{"pick": [
            {"weight": 1, "steps": [go(item=A + "pandroseion", slot="tend"), use(anim="pour", dur=(10, 15))]},
            {"weight": 1, "steps": [go(item=A + "great_altar", slot="sacrifice"), use(anim="pray", dur=(10, 15))]},
            {"weight": 1, "steps": [go(item=A + "nike_bastion", slot="pray"), use(anim="pray", dur=(10, 15))]},
            {"weight": 4, "steps": [go(node="great_altar"), wander(radius=6, dur=(20, 40)),
                                    use(anim="pour", dur=(10, 15))]}]}]}}, card="priest"))
    R.append(role("visitor", A + "citizen", "Visitor on the rock", sched(
        ("06:00", "12:30", "visit"), ("13:30", "19:30", "visit")),
        {"visit": {"loop": True, "steps": [
            go(node="propylaia"), wait(dur=(6, 12)), go(item=A + "g_stele_inscr", slot="read", within=6),
            use(anim="idle", dur=(15, 25)), go(node="great_altar"), use(anim="talk", dur=(10, 20)),
            go(node="pandroseion"), wait(dur=(10, 15))]}, "shelter": shelter_door(20)},
        card="citizen"))
    R.append(role("visitor_woman", A + "woman", "Woman on the rock", sched(
        ("06:00", "12:30", "visit"), ("13:30", "19:00", "visit")),
        {"visit": {"loop": True, "steps": [
            go(node="propylaia"), wait(dur=(6, 12)), go(node="pandroseion"), use(anim="idle", dur=(15, 25)),
            go(item=A + "brauronion", spot="beside"), wait(dur=(15, 25))]}}, card="woman"))
    R.append(role("yard_mason", A + "mason", "Mason", sched(
        ("06:00", "12:00", "work"), ("14:00", "18:00", "work")),
        {"work": {"loop": True, "steps": [
            go(item=A + "sculpt_yard", slot="hoist"), use(anim="haul", dur=(25, 40)),
            go(item=A + "g_scaffold", spot="beside", within=6), use(anim="work_high", dur=(25, 40))]}},
        card="mason"))
    R.append(role("sculptor", A + "sculptor", "Sculptor", sched(
        ("06:00", "12:00", "carve"), ("14:00", "18:00", "carve")),
        {"carve": {"loop": True, "steps": [
            go(home="carve"), use({"home": "carve"}, anim="work_high", dur=(40, 60)),
            use(anim="idle", dur=(6, 10))]}}, home={"item": A + "sculpt_yard", "slot": "carve"},
        card="sculptor"))
    R.append(role("owl", A + "owl", "Little owl", sched(("00:00", "24:00", "perch")),
        {"perch": {"loop": True, "steps": [wander(radius=6, dur=(20, 40)), use(anim="idle", dur=(60, 120))]}},
        card="owl"))
    # --- the residential quarters ---------------------------------------------------------------
    R.append(role("housewife", A + "woman", "Citizen woman", sched(
        ("05:00", "10:00", "water"), ("10:00", "17:00", "visits"), ("17:00", "20:30", "water")),
        {"water": {"loop": True, "steps": [{"pick": [
            {"weight": 1, "steps": [go(item=A + "g_well", slot="draw", within=16),
                                    use(anim="carry_idle", dur=(3, 5)), {"take": "athens.goods_hydria"},
                                    go(slot_kind="door", within=10), {"put": "athens.goods_hydria"}]},
            {"weight": 2, "steps": [go(slot_kind="door", within=10), use(anim="carry_idle", dur=(20, 40)),
                                    wander(radius=5, dur=(20, 30))]}]}]},
         "visits": {"loop": True, "steps": [{"pick": [
             {"weight": 3, "steps": [go(slot_kind="door", within=10), wait(dur=(30, 50)),
                                     wander(radius=6, dur=(20, 30))]},
             {"weight": 1, "steps": [go(item=A + "g_shrine", slot="pray", within=12),
                                     use(anim="idle", dur=(4, 6))]}]}]},
         "shelter": shelter_door()}, interrupts=[RAIN], card="woman"))
    R.append(role("maid", A + "enslaved_woman", "Enslaved woman", sched(
        ("05:00", "12:00", "errands"), ("14:00", "20:00", "errands")),
        {"errands": {"loop": True, "steps": [{"pick": [
            {"weight": 1, "steps": [go(item=A + "g_well", slot="draw", within=16),
                                    use(anim="carry_idle", dur=(3, 5)), {"take": "athens.goods_hydria"},
                                    go(slot_kind="door", within=10), {"put": "athens.goods_hydria"}]},
            {"weight": 3, "steps": [go(slot_kind="door", within=10), {"take": "world.goods_firewood"},
                                    wander(radius=6, dur=(20, 40)), {"put": "world.goods_firewood"}]}]}]},
         "shelter": shelter_door()}, interrupts=[RAIN], card="enslaved_woman"))
    R.append(role("townsman", A + "citizen", "Citizen", sched(
        ("05:30", "12:00", "errands"), ("14:00", "20:00", "errands")),
        {"errands": {"loop": True, "steps": [
            go(slot_kind="door", within=12), wait(dur=(10, 20)), wander(radius=8, dur=(30, 50)),
            use(anim="talk", dur=(10, 20))]},
         "shelter": shelter_door()}, interrupts=[RAIN], card="citizen"))
    R.append(role("shopkeeper", A + "working_woman", "Shopkeeper", sched(
        ("06:00", "12:00", "shop"), ("15:00", "19:30", "shop")),
        {"shop": {"loop": True, "steps": [
            go(home="sell"), use({"home": "sell"}, anim="serve", dur=(30, 50)),
            use(anim="throw", dur=(20, 30))]}}, home={"item": A + "g_house_small", "slot": "sell"},
        card="shopkeeper"))
    R.append(role("weaver", A + "working_woman", "Wool-worker", sched(
        ("05:00", "12:00", "weave"), ("14:00", "18:00", "weave")),
        {"weave": {"loop": True, "steps": [
            go(home="weave"), use({"home": "weave"}, anim="throw", dur=(50, 70)),
            use(anim="idle", dur=(4, 8))]}}, home={"item": A + "g_loom", "slot": "weave"},
        card="weaver"))
    R.append(role("workman", A + "enslaved_man", "Enslaved worker", sched(
        ("05:30", "12:00", "work"), ("14:00", "19:00", "work")),
        {"work": {"loop": True, "steps": [
            go(slot_kind="door", within=12), {"take": "world.goods_firewood"},
            wander(radius=8, dur=(20, 40)), go(slot_kind="door", within=12),
            {"put": "world.goods_firewood"}, use(anim="work_low", dur=(20, 30))]},
         "shelter": shelter_door()}, interrupts=[RAIN], card="enslaved_man"))
    R.append(role("child", A + "child", "Child", sched(("06:30", "19:30", "play")),
        {"play": {"loop": True, "steps": [{"pick": [
            {"weight": 3, "steps": [wander(radius=6, dur=(20, 40)), use(anim="run", dur=(6, 10))]},
            {"weight": 2, "steps": [wander(radius=3, dur=(10, 15)), use(anim="kneel", dur=(20, 30))]}]}]},
         "shelter": shelter_door()}, interrupts=[RAIN], card="child"))
    R.append(role("schoolboy", A + "youth", "Schoolboy", sched(("07:00", "11:30", "school")),
        {"school": {"steps": [go(node="melite_school"), use(anim="idle", until={"hour": "11:30"})]}},
        card="school"))
    R.append(role("paidagogos", A + "enslaved_man", "Paidagogos", sched(("06:30", "12:00", "escort")),
        {"escort": {"loop": True, "steps": [
            {"follow": {"actor": A + "youth"}, "dur": [40, 60], "spacing": 1.2},
            go(node="melite_school"), wait(dur=(30, 60))]}}, card="paidagogos"))
    R.append(role("spectator", A + "citizen", "Festival-goer", sched(("05:00", "20:00", "watch")),
        {"watch": {"loop": True, "steps": [
            go(node="eleusinion"), use(anim="talk", dur=(30, 50)), go(node="agora"),
            use(anim="idle", dur=(30, 50)), go(node="kerameikos_kilns"), wait(dur=(20, 30))]}},
        card="spectator"))
    R.append(role("night_walker", A + "citizen", "Citizen with a lamp", sched(
        ("19:30", "01:00", "home")),
        {"home": {"loop": True, "steps": [
            wander(radius=10, dur=(30, 50)), go(slot_kind="door", within=12), wait(dur=(10, 20))]}},
        card="citizen"))
    R.append(role("wall_watch", A + "hoplite", "Watch on the walls", sched(("19:00", "06:00", "watch")),
        {"watch": {"loop": True, "steps": [
            wander(radius=12, dur=(40, 70)), use(anim="guard", dur=(30, 60))]}}, card="hoplite"))
    R.append(role("dog", A + "dog_laconian", "Laconian hound", sched(("00:00", "24:00", "roam")),
        {"roam": {"loop": True, "steps": [wander(radius=8, dur=(20, 40)), use(anim="idle", dur=(30, 60))]}}))
    R.append(role("hen", A + "hen", "Hen", sched(("05:00", "19:30", "peck")),
        {"peck": {"loop": True, "steps": [wander(radius=3, dur=(10, 20)), use(anim="peck", dur=(10, 20))]}}))
    R.append(role("cobbler", A + "simon", "Simon at his bench", sched(("06:30", "18:30", "work")),
        {"work": {"loop": True, "steps": [
            go(item=A + "simon_shop", slot="work"), use(anim="stir", dur=(40, 60)),
            use(anim="talk", dur=(15, 25))]}}))
    # --- crafts on Kolonos and in Piraeus -------------------------------------------------------
    R.append(role("smith", A + "smith", "Smith", sched(("05:30", "12:00", "forge"),
                                                     ("14:00", "18:30", "forge")),
        {"forge": {"loop": True, "steps": [
            go(home="work"), use({"home": "work"}, anim="work_high", dur=(40, 60)),
            use(anim="idle", dur=(6, 10))]}}, home={"item": A + "g_forge", "slot": "work"},
        card="smith"))
    R.append(role("caster", A + "metic", "Bronze caster", sched(("06:00", "12:00", "cast"),
                                                               ("14:00", "18:00", "cast")),
        {"cast": {"loop": True, "steps": [
            go(node="hephaisteion"), use(anim="serve", dur=(20, 30)), wander(radius=4, dur=(20, 30)),
            use(anim="talk", dur=(10, 20))]}}, card="caster"))
    # --- the theatre ------------------------------------------------------------------------------
    R.append(role("chorus", A + "chorus", "Chorus member", sched(("14:00", "18:30", "rehearse")),
        {"rehearse": {"loop": True, "steps": [
            go(home="chorus"), use({"home": "chorus"}, anim="dance", dur=(40, 60)),
            use(anim="idle", dur=(10, 15))]}}, home={"item": A + "theatre", "slot": "chorus"},
        card="chorus"))
    R.append(role("aulos_player", A + "musician", "Aulos player", sched(("14:00", "18:30", "play"),
                                                                      ("19:30", "23:00", "symposium")),
        {"play": {"loop": True, "steps": [go(home="aulos"), use({"home": "aulos"}, anim="play", dur=(50, 70))]},
         "symposium": {"steps": [go(slot_kind="door", within=40),
                                 {"enter": {"here": True}, "until": {"hour": "23:00"}}]}},
        home={"item": A + "theatre", "slot": "aulos"}, card="aulos"))
    R.append(role("theatre_visitor", A + "citizen", "Onlooker", sched(("06:30", "12:00", "look"),
                                                                    ("14:00", "18:30", "look")),
        {"look": {"loop": True, "steps": [
            go(node="theatre"), use(anim="sit", dur=(40, 70)), go(node="odeion"),
            wander(radius=4, dur=(20, 30)), use(anim="talk", dur=(10, 20))]}}, card="citizen"))
    # --- Piraeus ------------------------------------------------------------------------------------
    R.append(role("rower", A + "rower", "Rower", sched(("05:00", "12:00", "quay"), ("14:00", "19:00", "quay")),
        {"quay": {"loop": True, "steps": [
            go(node="kantharos_quay"), use(anim="haul", dur=(20, 30)), go(node="zea_sheds"),
            use(anim="haul", dur=(20, 30)), wander(radius=4, dur=(15, 25))]}}, card="rower"))
    R.append(role("docker", A + "enslaved_man", "Dock worker", sched(
        ("05:00", "12:00", "load"), ("14:00", "19:00", "load")),
        {"load": {"loop": True, "steps": [
            go(item=A + "harbour", slot="load"), use(anim="haul", dur=(6, 10)),
            {"take": "world.goods_amphorae"}, go(node="piraeus_agora"), {"put": "world.goods_amphorae"},
            go(node="kantharos_quay"), wait(dur=(8, 14))]}}, card="docker"))
    R.append(role("merchant", A + "metic", "Merchant", sched(("06:00", "12:00", "trade"),
                                                           ("14:00", "19:00", "trade")),
        {"trade": {"loop": True, "steps": [
            go(item=A + "harbour", slot="trade"), use(anim="talk", dur=(30, 50)),
            go(node="piraeus_agora"), use(anim="serve", dur=(20, 30))]}}, card="metic"))
    R.append(role("shipwright", A + "enslaved_man", "Shipwright", sched(
        ("06:00", "12:00", "build"), ("14:00", "18:30", "build")),
        {"build": {"loop": True, "steps": [
            go(item=A + "shipsheds", spot="beside"), use(anim="work_low", dur=(30, 50)),
            use(anim="haul", dur=(15, 25))]}}, card="shipwright"))
    R.append(role("ionian", A + "ionian", "Ionian visitor", sched(("07:00", "18:00", "visit")),
        {"visit": {"loop": True, "steps": [
            go(node="piraeus_agora"), use(anim="talk", dur=(20, 30)), go(node="kantharos_quay"),
            wait(dur=(15, 25))]}}, card="ionian"))
    R.append(role("thracian", A + "thracian", "Thracian", sched(("07:00", "18:00", "visit")),
        {"visit": {"loop": True, "steps": [
            go(node="kantharos_quay"), use(anim="idle", dur=(20, 30)), go(node="piraeus_agora"),
            wait(dur=(15, 25))]}}, card="thracian"))
    R.append(role("gull", "world.gull", "Gull", sched(("04:30", "21:00", "fly")),
        {"fly": {"loop": True, "steps": [wander(radius=14, dur=(20, 40)), use(anim="idle", dur=(10, 20))]}}))
    # --- the roads and the country --------------------------------------------------------------
    R.append(role("cart", A + "cart", "Ox cart", sched(("05:00", "19:00", "haul")),
        {"haul": {"loop": True, "steps": [
            go(node="kantharos_quay"), wait(dur=(20, 30)), go(node="long_walls_road"),
            go(node="long_walls_gate"), go(node="market"), wait(dur=(20, 30))]}},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}))
    R.append(role("drover", A + "drover", "Drover", sched(("05:00", "19:00", "drive")),
        {"drive": {"loop": True, "steps": [
            {"follow": {"actor": A + "cart"}, "dur": [60, 90], "spacing": 0.8},
            use(anim="idle", dur=(10, 20))]}}))
    R.append(role("donkey", A + "donkey", "Donkey", sched(("05:00", "19:00", "walk")),
        {"walk": {"loop": True, "steps": [wander(radius=6, dur=(20, 40)), use(anim="graze", dur=(20, 40))]}}))
    R.append(role("farmer", A + "farmer", "Farmer", sched(
        ("04:30", "11:30", "field"), ("15:00", "19:00", "field")),
        {"field": {"loop": True, "steps": [{"pick": [
            {"weight": 4, "steps": [wander(radius=6, dur=(20, 40)), use(anim="work_low", dur=(30, 50))]},
            {"weight": 1, "steps": [go(item=A + "g_farmstead", slot="door", within=12),
                                    use(anim="carry_idle", dur=(10, 15))]}]}]}}, card="farmer"))
    R.append(role("thresher", A + "farmer", "Thresher", sched(
        ("05:00", "11:00", "thresh"), ("15:00", "18:30", "thresh")),
        {"thresh": {"loop": True, "steps": [
            go(home="work"), use({"home": "work"}, anim="work_low", dur=(30, 50)),
            use(anim="carry_idle", dur=(6, 10))]}}, home={"item": A + "g_threshing", "slot": "work"},
        card="thresher"))
    R.append(role("presser", A + "farmer", "Olive presser", sched(
        ("05:30", "11:00", "press"), ("15:00", "18:30", "press")),
        {"press": {"loop": True, "steps": [
            go(home="work"), use({"home": "work"}, anim="work_low", dur=(30, 50)),
            {"take": "world.goods_amphorae"}, go(item=A + "g_farmstead", slot="door", within=10),
            {"put": "world.goods_amphorae"}]}}, home={"item": A + "g_press", "slot": "work"},
        card="presser"))
    R.append(role("herder", A + "herder", "Goatherd", sched(("05:00", "19:00", "herd")),
        {"herd": {"loop": True, "steps": [wander(radius=10, dur=(40, 70)), use(anim="idle", dur=(10, 20))]}},
        card="herder"))
    R.append(role("goat", A + "goat", "Goat", sched(("05:00", "19:30", "graze")),
        {"graze": {"loop": True, "steps": [wander(radius=6, dur=(20, 40)), use(anim="graze", dur=(10, 25))]}}))
    R.append(role("sheep", A + "sheep", "Sheep", sched(("05:00", "19:30", "graze")),
        {"graze": {"loop": True, "steps": [wander(radius=6, dur=(20, 40)), use(anim="graze", dur=(10, 25))]}}))
    R.append(role("ox", A + "ox", "Ox", sched(("05:00", "18:30", "graze")),
        {"graze": {"loop": True, "steps": [wander(radius=4, dur=(20, 40)), use(anim="graze", dur=(30, 50))]}}))
    # --- the Lyceum and Pentelikon --------------------------------------------------------------
    R.append(role("athlete", A + "athlete", "Athlete", sched(("06:00", "12:00", "train"),
                                                           ("14:00", "19:00", "train")),
        {"train": {"loop": True, "steps": [{"pick": [
            {"weight": 1, "steps": [go(item=A + "lyceum", slot="run"), use(anim="run", dur=(8, 12))]},
            {"weight": 2, "steps": [wander(radius=8, dur=(20, 30)), use(anim="run", dur=(15, 25))]},
            {"weight": 2, "steps": [wander(radius=4, dur=(10, 15)), use(anim="wrestle", dur=(20, 30))]},
            {"weight": 1, "steps": [wander(radius=3, dur=(10, 15)), use(anim="scrape", dur=(15, 20))]}]}]}},
        card="athlete"))
    R.append(role("hoplite", A + "hoplite", "Hoplite", sched(("06:00", "11:00", "drill"),
                                                           ("16:00", "19:00", "drill")),
        {"drill": {"loop": True, "steps": [
            go(home="drill"), use({"home": "drill"}, anim="march", dur=(25, 40)),
            use(anim="guard", dur=(10, 20))]}}, home={"item": A + "lyceum", "slot": "drill"},
        card="hoplite"))
    R.append(role("gate_guard", A + "hoplite", "Watch at the gate", sched(("00:00", "24:00", "watch")),
        {"watch": {"loop": True, "steps": [
            go(item=A + "dipylon", slot="guard"), use(anim="guard", dur=(60, 120)),
            go(node="sacred_gate"), use(anim="march", dur=(10, 15))]}}, card="hoplite"))
    R.append(role("trainer", A + "philosopher", "Trainer", sched(("06:00", "12:00", "watch"),
                                                               ("14:00", "19:00", "watch")),
        {"watch": {"loop": True, "steps": [
            go(item=A + "lyceum", slot="talk"), use(anim="gesture", dur=(20, 30)),
            wander(radius=4, dur=(15, 25))]}}, card="trainer"))
    R.append(role("rider", A + "cavalryman", "Horseman", sched(("06:00", "12:00", "ride"),
                                                             ("14:00", "19:00", "ride")),
        {"ride": {"loop": True, "steps": [go(node="lyceum"), wander(radius=8, dur=(40, 70))]}}))
    R.append(role("quarryman", A + "mason", "Quarryman", sched(
        ("05:00", "12:00", "cut"), ("14:00", "18:30", "cut")),
        {"cut": {"loop": True, "steps": [
            go(home="cut"), use({"home": "cut"}, anim="work_high", dur=(30, 50)),
            use(anim="haul", dur=(10, 20))]}}, home={"item": A + "pentelikon_quarry", "slot": "cut"},
        card="quarryman"))
    R.append(role("quarry_hauler", A + "enslaved_man", "Quarry hauler", sched(
        ("05:00", "12:30", "haul"), ("13:30", "18:30", "haul")),
        {"haul": {"loop": True, "steps": [
            go(node="pentelikon_quarry"), use(anim="haul", dur=(30, 50)), wander(radius=5, dur=(15, 25)),
            use(anim="work_low", dur=(20, 30))]}}, card="quarry_hauler"))
    R.append(role("sledge", A + "sledge", "Marble sledge", sched(("05:30", "18:30", "haul")),
        {"haul": {"loop": True, "steps": [
            go(item=A + "pentelikon_quarry", slot="sledge"), wait(dur=(20, 30)),
            go(node="quarry_road"), go(node="acharnian_gate"), go(node="approach_foot"),
            go(node="sculptors_yard"), wait(dur=(20, 30))]}},
        locomotion={"mode": "walk", "speed": 0.5, "network": "roads", "turn_radius": 2}))
    return R


def groups() -> list[dict]:
    return [
        {"id": "panathenaic_procession", "leader": {"actor": A + "marshal"}, "members": [
            {"actor": A + "peplos_bearer", "count": 2, "carry": A + "goods_peplos"},
            {"actor": A + "kanephoros", "count": 4, "carry": A + "goods_kanoun"},
            {"actor": A + "hydriaphoros", "count": 3, "carry": A + "goods_hydria"},
            {"actor": A + "skaphephoros", "count": 3}, {"actor": A + "metic_daughter", "count": 2},
            {"actor": A + "thallophoros", "count": 4}, {"actor": A + "musician", "count": 2},
            {"actor": A + "drover", "count": 2}, {"actor": A + "heifer", "count": 4},
            {"actor": A + "sheep", "count": 4}, {"actor": A + "hoplite", "count": 6},
            {"actor": A + "cavalryman", "count": 4}, {"actor": A + "alcibiades", "count": 1},
            {"actor": A + "theseus", "count": 1}, {"actor": A + "chariot", "count": 1}],
         "formation": {"kind": "pairs", "spacing": 0.9}},
        {"id": "hoplites_for_potidaea", "leader": {"role": "hoplite"},
         "members": [{"role": "hoplite", "count": 11}], "formation": {"kind": "pairs", "spacing": 0.8}},
        {"id": "assembly_sweep", "leader": {"actor": A + "toxamis"},
         "members": [{"role": "archer", "count": 3}], "formation": {"kind": "line", "spacing": 1.2}},
        {"id": "wedding", "leader": {"actor": A + "cart"},
         "members": [{"actor": A + "musician", "count": 2}, {"role": "housewife", "count": 4},
                     {"role": "townsman", "count": 4}, {"role": "child", "count": 2}],
         "formation": {"kind": "cluster", "radius": 2}},
        {"id": "funeral", "leader": {"role": "townsman"},
         "members": [{"role": "mourner", "count": 4}, {"actor": A + "musician", "count": 1},
                     {"role": "townsman", "count": 3}], "formation": {"kind": "pairs", "spacing": 0.9}},
        {"id": "socratic_ring", "leader": {"actor": A + "socrates"},
         "members": [{"role": "pupil", "count": 4}, {"actor": A + "alcibiades", "count": 1}],
         "formation": {"kind": "cluster", "radius": 2}},
        {"id": "protagoras_pupils", "leader": {"actor": A + "protagoras"},
         "members": [{"role": "pupil", "count": 6}], "formation": {"kind": "line", "spacing": 0.9}},
        {"id": "flock", "leader": {"role": "herder"},
         "members": [{"actor": A + "goat", "count": 5}, {"actor": A + "sheep", "count": 3},
                     {"actor": A + "dog_molossian", "count": 1}], "formation": {"kind": "cluster", "radius": 3}},
    ]


def districts() -> list[dict]:
    homes = lambda w, c, ch, m, s: [   # noqa: E731 - a quarter's everyday people
        pop("housewife", "houses", w), pop("townsman", "day", c), pop("child", "children", ch),
        pop("maid", "houses", m), pop("workman", "work", s), pop("dog", "day", 1), pop("hen", "day", 2),
        pop("night_walker", "evening", 4), pop("wall_watch", "always", 2)]
    return [
        {"id": "agora", "area": "centre", "populations": [
            per("stall_keeper", "g_stall", 1, "market"), per("banker", "g_table_banker", 1, "market"),
            pop("shopper", "market", 30), pop("elder", "day", 7), pop("porter", "market", 10),
            pop("spectator", "day", 12, when=FEAST),
            pop("archer", "watch", 6), per("fountain_woman", "se_fountain", 2, "always"),
            pop("philosopher", "afternoon", 3), pop("pupil", "afternoon", 6), pop("child", "children", 4),
            pop("donkey", "market", 2), per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "council", "area": "town", "populations": [
            pop("councillor", "day", 36), per("herald", "royal_stoa", 1, "day"), pop("archer", "watch", 6),
            pop("juror", "day", 6), pop("shopper", "market", 10)]},
        {"id": "kerameikos", "area": "town", "populations": [
            per("potter", "g_wheel", 1, "work", when=WORKDAY),
            per("vase_painter", "g_workshop", 1, "work", when=WORKDAY),
            per("kiln_man", "g_kiln", 1, "work", when=WORKDAY), pop("clay_digger", "work", 9, when=WORKDAY),
            per("shopkeeper", "g_house_small", 1, "market"), pop("child", "children", 6),
            pop("donkey", "work", 2), pop("housewife", "houses", 6),
            pop("spectator", "day", 36, when=FEAST)]},
        {"id": "cemetery", "area": "country", "populations": [
            pop("mourner", "day", 10), per("potter", "g_wheel", 1, "work"),
            per("vase_painter", "g_workshop", 1, "work"), pop("clay_digger", "work", 6),
            per("gate_guard", "dipylon", 2, "watch")]},
        {"id": "acropolis", "area": "centre", "populations": [
            pop("priestess", "day", 8), pop("visitor", "day", 38), pop("visitor_woman", "day", 16),
            pop("yard_mason", "work", 4, when=WORKDAY), per("sculptor", "sculpt_yard", 3, "work", when=WORKDAY),
            pop("spectator", "day", 14, when=FEAST),
            pop("owl", "always", 1)]},
        {"id": "slopes", "area": "wild", "populations": [
            pop("goat", "graze", 4), pop("owl", "always", 2), pop("townsman", "day", 4)]},
        {"id": "areopagus", "area": "wild", "populations": [pop("elder", "day", 6)]},
        {"id": "pnyx", "area": "wild", "populations": [
            pop("herder", "day", 2), pop("goat", "graze", 6), pop("townsman", "day", 4)]},
        {"id": "kolonos", "area": "town", "populations": [
            per("smith", "g_forge", 1, "work"), pop("caster", "work", 24), pop("townsman", "day", 12),
            pop("visitor", "day", 6)]},
        {"id": "dionysos", "area": "town", "populations": [
            per("chorus", "theatre", 6, "afternoon"), per("aulos_player", "theatre", 1, "afternoon"),
            pop("theatre_visitor", "day", 28), pop("priestess", "day", 3), pop("townsman", "day", 12)]},
        {"id": "melite", "area": "town", "populations": homes(16, 10, 8, 8, 6) + [
            per("weaver", "g_loom", 1, "work"), per("shopkeeper", "g_house_small", 1, "market"),
            pop("schoolboy", "children", 4), pop("paidagogos", "children", 3),
            per("cobbler", "simon_shop", 1, "work")]},
        {"id": "koile", "area": "town", "populations": homes(18, 12, 8, 8, 6) + [
            per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "kollytos", "area": "town", "populations": homes(16, 12, 8, 8, 6) + [
            per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "kydathenaion", "area": "town", "populations": homes(18, 14, 9, 8, 7) + [
            per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "skambonidai", "area": "town", "populations": homes(16, 12, 8, 8, 6) + [
            per("weaver", "g_loom", 1, "work"), per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "east_quarter", "area": "town", "populations": homes(14, 12, 8, 8, 6) + [
            per("weaver", "g_loom", 1, "work"), per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "piraeus", "area": "centre", "populations": [
            pop("rower", "harbour", 18), pop("docker", "harbour", 12), pop("merchant", "harbour", 6),
            pop("shipwright", "work", 10), per("smith", "g_forge", 1, "work"),
            per("stall_keeper", "g_stall", 1, "market"), per("vase_painter", "g_workshop", 1, "work"),
            pop("ionian", "day", 6), pop("thracian", "day", 3), pop("housewife", "houses", 8),
            pop("child", "children", 4), pop("gull", "day", 4), pop("archer", "watch", 2),
            per("shopkeeper", "g_house_small", 1, "market")]},
        {"id": "harbour", "area": "sea", "populations": [pop("gull", "harbour", 14)]},
        {"id": "long_walls", "area": "road", "populations": [
            pop("cart", "day", 8), pop("drover", "day", 6), pop("townsman", "day", 6),
            pop("donkey", "day", 2)]},
        {"id": "north_fields", "area": "country", "populations": [
            pop("farmer", "dawn_work", 14), pop("herder", "day", 2), pop("goat", "graze", 6),
            pop("donkey", "work", 2)]},
        {"id": "south_fields", "area": "country", "populations": [
            pop("farmer", "dawn_work", 10), per("thresher", "g_threshing", 2, "dawn_work"),
            per("presser", "g_press", 1, "dawn_work"), pop("herder", "day", 2), pop("goat", "graze", 4),
            pop("sheep", "graze", 4), pop("ox", "work", 2)]},
        {"id": "ilissos", "area": "country", "populations": [
            pop("farmer", "dawn_work", 14), per("presser", "g_press", 1, "dawn_work"),
            pop("herder", "day", 2), pop("goat", "graze", 6), pop("sheep", "graze", 4),
            pop("housewife", "houses", 3), pop("donkey", "work", 2)]},
        {"id": "countryside", "area": "country", "populations": [
            pop("farmer", "dawn_work", 12), pop("herder", "day", 2), pop("goat", "graze", 6),
            pop("donkey", "work", 2), pop("townsman", "day", 4)]},
        {"id": "lyceum", "area": "town", "populations": [
            pop("athlete", "day", 28), per("hoplite", "lyceum", 4, "work"),
            per("trainer", "lyceum", 2, "day"), pop("rider", "day", 8), pop("pupil", "afternoon", 6)]},
        {"id": "pentelikon", "area": "town", "populations": [
            per("quarryman", "pentelikon_quarry", 4, "work"), pop("sledge", "work", 4),
            pop("drover", "work", 8), pop("ox", "work", 8), pop("quarry_hauler", "work", 14)]},
        # (the quarry works on: it is outside the city and its gangs are not festival-goers)
        {"id": "lykabettos", "area": "wild", "populations": [pop("herder", "day", 2), pop("goat", "graze", 6)]},
        {"id": "hymettos", "area": "wild", "populations": [pop("herder", "day", 2), pop("goat", "graze", 6)]},
        {"id": "mouseion", "area": "wild", "populations": [pop("herder", "day", 2), pop("goat", "graze", 6)]},
    ]




def chains() -> list[dict]:
    return [
        {"id": "athens_marble", "name": "Marble for the Acropolis", "period": 210,
         "hours": ["05:30", "18:30"], "stages": [
             {"slot": A + "pentelikon_quarry.cut", "makes": "world.goods_block", "by": "quarryman"},
             {"carry": "world.goods_block", "from": A + "pentelikon_quarry.cut",
              "to": A + "sculpt_yard.carve", "by": "sledge", "units": 1, "workers": 3},
             {"slot": A + "sculpt_yard.carve", "needs": "world.goods_block", "makes": "world.goods_block",
              "out": A + "sculpt_yard.hoist", "by": "sculptor", "label": "carved"},
             {"slot": A + "sculpt_yard.hoist", "sink": "world.goods_block", "by": "yard_mason",
              "label": "hoisted into place"}]},
        {"id": "athens_pottery", "name": "Pottery", "period": 120, "hours": ["05:30", "18:00"], "stages": [
             {"slot": A + "g_wheel.throw", "makes": "world.goods_pot_raw", "near": "kerameikos_kilns",
              "by": "potter"},
             {"carry": "world.goods_pot_raw", "from": A + "g_wheel.throw", "to": A + "g_workshop.throw",
              "near": "kerameikos_kilns", "by": "potter"},
             {"slot": A + "g_workshop.throw", "needs": "world.goods_pot_raw",
              "makes": "world.goods_pot_painted", "near": "kerameikos_kilns", "by": "vase_painter"},
             {"carry": "world.goods_pot_painted", "from": A + "g_workshop.throw", "to": A + "g_kiln.stoke",
              "near": "kerameikos_kilns", "by": "kiln_man"},
             {"slot": A + "g_kiln.stoke", "needs": "world.goods_pot_painted", "makes": A + "goods_redfigure",
              "near": "kerameikos_kilns", "by": "kiln_man", "label": "fired: oxidise, reduce, reoxidise"},
             {"carry": A + "goods_redfigure", "from": A + "g_kiln.stoke", "to": A + "g_stall.sell",
              "near": "kerameikos_kilns", "by": "porter", "units": 2},
             {"slot": A + "g_stall.sell", "sink": A + "goods_redfigure", "near": "market",
              "by": "stall_keeper", "label": "sold"}]},
        {"id": "athens_oil", "name": "Olive oil to the market", "period": 160, "hours": ["05:30", "18:30"],
         "stages": [
             {"slot": A + "g_press.work", "makes": "world.goods_oil_jar", "near": "south_farms",
              "by": "presser", "label": "pressed from the store of olives"},
             {"carry": "world.goods_oil_jar", "from": A + "g_press.work", "to": A + "g_stall.sell",
              "near": "south_farms", "by": "cart", "units": 3, "workers": 2},
             {"slot": A + "g_stall.sell", "sink": "world.goods_oil_jar", "near": "se_fountain",
              "by": "stall_keeper", "label": "sold by the ladle"}]},
        {"id": "athens_oil_export", "name": "Oil for the ships", "period": 200, "hours": ["05:30", "18:30"],
         "stages": [
             {"slot": A + "g_press.work", "makes": "world.goods_amphorae", "near": "kallirrhoe",
              "by": "presser"},
             {"carry": "world.goods_amphorae", "from": A + "g_press.work", "to": A + "harbour.load",
              "near": "kallirrhoe", "by": "cart", "units": 3, "workers": 2},
             {"slot": A + "harbour.load", "sink": "world.goods_amphorae", "by": "docker",
              "label": "loaded aboard a merchantman"}]},
        {"id": "athens_grain", "name": "Black Sea grain", "period": 150, "hours": ["05:00", "18:00"],
         "stages": [
             {"slot": "node:kantharos_quay", "makes": "world.goods_sacks", "by": "docker",
              "label": "unloaded from a grain ship"},
             {"carry": "world.goods_sacks", "from": "node:kantharos_quay", "to": A + "g_stall.sell",
              "by": "cart", "units": 3, "workers": 2, "near": "lawcourt"},
             {"slot": A + "g_stall.sell", "sink": "world.goods_sacks", "near": "lawcourt",
              "by": "stall_keeper", "label": "carried home to be ground"}]},
        {"id": "athens_fish", "name": "Fish", "period": 100, "hours": ["05:00", "12:00"], "stages": [
             {"slot": "node:mounychia_landing", "makes": "world.goods_fish", "by": "rower",
              "label": "landed from the boats"},
             {"carry": "world.goods_fish", "from": "node:mounychia_landing", "to": A + "g_stall.sell",
              "near": "piraeus_agora", "by": "porter", "units": 2},
             {"slot": A + "g_stall.sell", "sink": "world.goods_fish", "near": "piraeus_agora",
              "by": "stall_keeper", "label": "sold"}]},
        {"id": "athens_water", "name": "Water", "period": 70, "hours": ["04:30", "20:00"], "stages": [
             {"slot": A + "se_fountain.fill", "makes": A + "goods_hydria", "by": "fountain_woman"},
             {"carry": A + "goods_hydria", "from": A + "se_fountain.fill", "to": A + "g_house_two.door",
              "near": "se_fountain", "by": "fountain_woman", "workers": 2},
             {"slot": A + "g_house_two.door", "sink": A + "goods_hydria", "near": "se_fountain",
              "by": "housewife", "label": "carried in"}]},
        {"id": "athens_charcoal", "name": "Charcoal from Acharnai", "period": 160,
         "hours": ["06:00", "17:00"], "stages": [
             {"slot": "node:acharnian_gate", "makes": A + "goods_charcoal", "by": "farmer",
              "label": "brought in by donkey from the burners on Parnes"},
             {"carry": A + "goods_charcoal", "from": "node:acharnian_gate", "to": A + "g_kiln.stoke",
              "near": "kerameikos_kilns", "by": "porter", "units": 2, "workers": 2},
             {"slot": A + "g_kiln.stoke", "sink": A + "goods_charcoal", "near": "kerameikos_kilns",
              "by": "kiln_man", "label": "burnt in the firing"}]},
        {"id": "athens_shields", "name": "Shields from Piraeus", "period": 200, "hours": ["06:00", "18:00"],
         "stages": [
             {"slot": A + "g_forge.work", "makes": A + "goods_shield", "near": "kephalos_workshop",
              "by": "smith"},
             {"carry": A + "goods_shield", "from": A + "g_forge.work", "to": A + "harbour.load",
              "near": "kephalos_workshop", "by": "docker"},
             {"slot": A + "harbour.load", "sink": A + "goods_shield", "by": "docker",
              "label": "stowed for the force at Potidaea"}]},
        {"id": "athens_tribute", "name": "Tribute to the Acropolis", "period": 150,
         "hours": ["08:00", "18:00"], "event": "tribute_ship", "stages": [
             {"slot": A + "harbour.trade", "makes": "world.goods_silver", "by": "merchant",
              "label": "sealed jars of silver landed"},
             {"carry": "world.goods_silver", "from": A + "harbour.trade", "to": "node:propylaia",
              "by": "cart", "units": 3, "workers": 2},
             {"slot": "node:propylaia", "sink": "world.goods_silver", "by": "priestess",
              "label": "counted into Athena's treasury"}]},
    ]


FESTIVALS = [
    {"id": "panathenaia", "season": "summer", "day": 2, "hours": ["05:30", "18:00"]},
    {"id": "mysteries", "season": "autumn", "day": 1, "hours": ["06:00", "18:00"]},
    {"id": "thesmophoria", "season": "autumn", "day": 3, "hours": ["06:00", "18:00"]},
    {"id": "olive_harvest", "season": "autumn", "hours": ["06:00", "17:00"]},
    {"id": "lenaia", "season": "winter", "day": 2, "hours": ["09:00", "17:00"]},
    {"id": "anthesteria", "season": "winter", "day": 3, "hours": ["08:00", "20:00"]},
    {"id": "city_dionysia", "season": "spring", "day": 2, "hours": ["07:00", "18:00"]},
]


def events() -> list[dict]:
    return [
        {"id": "panathenaic_procession", "rarity": "festival", "size": "large", "card": "athena",
         "trigger": {"on": "calendar", "festival": "panathenaia", "hours": ["05:30", "06:00"]},
         "duration": [270, 330], "cast": [{"group": "panathenaic_procession"},
                                          {"role": "shopper", "count": 20, "from": "district"}],
         "route": ["dipylon", "kerameikos_kilns", "agora", "eleusinion", "klepsydra", "approach_foot",
                   "propylaia", "pandroseion", "great_altar"],
         "steps": [go(node="agora"), go(node="eleusinion"), go(node="approach_foot"), go(node="propylaia"),
                   go(node="great_altar"), use(item=A + "great_altar", slot="sacrifice", anim="idle",
                                               dur=(40, 60)), {"emit": {"sfx": "sfx/athens/aulos.wav"}}],
         "ambience": {"file": "amb/athens/procession.ogg", "gain": 0.8}, "string": "procession"},
        {"id": "athena_apparition", "rarity": "festival", "size": "small", "zone": "acropolis",
         "trigger": {"on": "after", "event": "panathenaic_procession"}, "duration": [8, 12],
         "steps": [{"emit": {"fx": A + "altar_smoke"}}], "card": "athena"},
        {"id": "sacrificial_feast", "rarity": "festival", "size": "medium", "zone": "kerameikos",
         "trigger": {"on": "calendar", "festival": "panathenaia", "hours": ["18:30", "19:00"]},
         "duration": [120, 160], "cast": [{"role": "townsman", "count": 12}, {"role": "housewife", "count": 6},
                                          {"role": "child", "count": 4}],
         "steps": [go(node="kerameikos_kilns"), use(anim="sit", dur=(100, 140))]},
        {"id": "assembly", "rarity": "uncommon", "size": "large",
         "trigger": {"on": "window", "hours": ["06:30", "07:00"], "days": ASSEMBLY["days"],
                     "not_festival": "panathenaia", "chance": 1.0},
         "duration": [240, 300],
         "cast": [{"group": "assembly_sweep"}, {"role": "shopper", "count": 24, "from": "district"},
                  {"actor": A + "pericles", "count": 1}],
         "route": ["agora", "simon_shop", "melite_school", "pnyx"],
         "steps": [go(node="pnyx"), use(item=A + "pnyx", slot="assembly", anim="idle", dur=(150, 200))],
         "ambience": {"file": "amb/athens/agora.ogg", "gain": 0.6}, "string": "assembly", "card": "democracy"},
        {"id": "law_court", "rarity": "common", "size": "medium", "zone": "agora",
         "trigger": {"on": "window", "hours": ["07:00", "08:00"], "chance": 0.6},
         "duration": [150, 200], "cast": [{"role": "juror", "count": 10}, {"role": "archer", "count": 1}],
         "steps": [go(item=A + "lawcourt", spot="beside"), use(anim="sit", dur=(120, 160))]},
        {"id": "prytaneis_dine", "rarity": "daily", "size": "small", "zone": "council",
         "trigger": {"on": "window", "hours": ["18:00", "18:30"], "chance": 1.0},
         "duration": [60, 90], "cast": [{"role": "councillor", "count": 6, "from": "district"}],
         "steps": [go(item=A + "tholos", slot="door"), {"enter": {"here": True}, "dur": [50, 80]}]},
        {"id": "philosopher_crowd", "rarity": "daily", "size": "medium", "zone": "agora",
         "trigger": {"on": "window", "hours": ["08:00", "09:30"], "chance": 1.0},
         "duration": [120, 150], "cast": [{"group": "socratic_ring"}, {"role": "shopper", "count": 5}],
         "steps": [go(item=A + "stoa_poikile", slot="philosopher"), use(anim="talk", dur=(100, 130))],
         "card": "philosophy"},
        {"id": "protagoras_walk", "rarity": "uncommon", "size": "small", "zone": "kollytos",
         "trigger": {"on": "window", "hours": ["15:00", "16:00"], "chance": 0.4},
         "duration": [90, 120], "cast": [{"group": "protagoras_pupils"}],
         "steps": [go(node="kollytos_tavern"), wander(radius=4, dur=(80, 100))]},
        {"id": "rehearsal", "rarity": "common", "size": "medium", "zone": "dionysos",
         "trigger": {"on": "window", "hours": ["14:00", "15:00"], "chance": 0.8},
         "duration": [150, 180], "cast": [{"role": "chorus", "count": 6}, {"role": "aulos_player", "count": 1},
                                          {"actor": A + "euripides", "count": 1}],
         "steps": [use(item=A + "theatre", slot="chorus", anim="dance", dur=(130, 160))],
         "card": "drama"},
        {"id": "athletes", "rarity": "common", "size": "medium", "zone": "lyceum",
         "trigger": {"on": "window", "hours": ["07:00", "08:00"], "chance": 0.8},
         "duration": [120, 150], "cast": [{"role": "athlete", "count": 6}, {"role": "trainer", "count": 1}],
         "steps": [use(item=A + "lyceum", slot="run", anim="run", dur=(100, 130))]},
        {"id": "kiln_firing", "rarity": "common", "size": "small", "zone": "kerameikos",
         "trigger": {"on": "chain", "chain": "athens_pottery", "stage": 4}, "duration": [60, 80],
         "cast": [{"actor": A + "manes", "count": 1}],
         "steps": [use(item=A + "g_kiln", slot="stoke", anim="work_low", dur=(50, 70), state="firing")],
         "ambience": {"file": "amb/athens/kiln.ogg", "gain": 0.8}},
        {"id": "fountain_dawn", "rarity": "daily", "size": "small", "zone": "agora",
         "trigger": {"on": "window", "hours": ["04:30", "05:00"], "chance": 1.0},
         "duration": [90, 110], "cast": [{"role": "fountain_woman", "count": 4},
                                         {"actor": A + "philinna", "count": 1}, {"actor": A + "mania", "count": 1}],
         "steps": [use(item=A + "se_fountain", slot="fill", anim="carry_idle", dur=(70, 90)),
                   {"emit": {"sfx": "sfx/world/pour.wav"}}]},
        {"id": "symposium", "rarity": "common", "size": "small", "zone": "kydathenaion",
         "trigger": {"on": "window", "hours": ["20:30", "21:30"], "chance": 0.7},
         "duration": [150, 200], "cast": [{"role": "townsman", "count": 5}, {"role": "aulos_player", "count": 1}],
         "steps": [go(item=A + "g_house", slot="door", within=10), {"enter": {"here": True}, "dur": [140, 180]},
                   {"emit": {"sfx": "sfx/athens/lyre.wav"}}], "card": "symposium"},
        {"id": "owl_call", "rarity": "common", "size": "small", "zone": "acropolis",
         "trigger": {"on": "window", "hours": ["21:00", "04:00"], "every": 3600}, "duration": [2, 3],
         "cast": [{"role": "owl", "count": 1}], "steps": [{"emit": {"sfx": "sfx/athens/owl.wav"}}]},
        {"id": "torch_race", "rarity": "festival", "size": "medium",
         "trigger": {"on": "calendar", "festival": "panathenaia", "hours": ["20:30", "21:00"]},
         "duration": [100, 120], "cast": [{"role": "pupil", "count": 6}],
         "route": ["cemetery", "dipylon", "agora", "approach_foot", "propylaia", "great_altar"],
         "steps": [go(node="dipylon"), go(node="agora"), go(node="approach_foot"), go(node="great_altar")],
         "string": "torch_race"},
        {"id": "hoplites_embark", "rarity": "uncommon", "size": "medium",
         "trigger": {"on": "window", "hours": ["08:30", "09:00"], "chance": 0.5,
                     "not_festival": "panathenaia"},
         "duration": [200, 240], "cast": [{"group": "hoplites_for_potidaea"},
                                          {"role": "housewife", "count": 4}],
         "route": ["lyceum", "diochares_gate", "piraeus_gate", "long_walls_gate", "long_walls_road",
                   "piraeus_agora", "kantharos_quay"],
         "steps": [go(node="long_walls_gate"), go(node="long_walls_road"), go(node="kantharos_quay")],
         "string": "embark", "card": "potidaea"},
        {"id": "tribute_ship", "rarity": "rare", "size": "medium", "zone": "piraeus",
         "trigger": {"on": "token_arrived", "actor": A + "merchant", "chance": 0.2},
         "duration": [120, 160], "cast": [{"role": "docker", "count": 4, "from": "district"},
                                          {"role": "hoplite", "count": 2}],
         "steps": [use(item=A + "harbour", slot="load", anim="haul", dur=(40, 60))], "card": "league"},
        {"id": "ship_unloads", "rarity": "common", "size": "medium", "zone": "piraeus",
         "trigger": {"on": "token_arrived", "actor": A + "merchant"}, "duration": [90, 120],
         "cast": [{"role": "docker", "count": 6, "from": "district"}],
         "steps": [use(item=A + "harbour", slot="load", anim="haul", dur=(60, 90), effect="unload")],
         "sfx": "sfx/athens/trireme.wav", "ambience": {"file": "amb/athens/sea.ogg", "gain": 0.6}},
        {"id": "trireme_drill", "rarity": "uncommon", "size": "small", "zone": "harbour",
         "trigger": {"on": "window", "hours": ["07:00", "09:00"], "chance": 0.4}, "duration": [45, 60],
         "cast": [{"actor": A + "trireme", "count": 1}], "steps": [], "sfx": "sfx/athens/oars.wav"},
        {"id": "fishing_fleet", "rarity": "daily", "size": "small", "zone": "harbour",
         "trigger": {"on": "window", "hours": ["04:30", "05:00"], "chance": 1.0}, "duration": [60, 90],
         "cast": [{"actor": A + "fishing", "count": 3}], "steps": [], "sfx": "sfx/world/gull.wav"},
        {"id": "wedding", "rarity": "rare", "size": "medium",
         "trigger": {"on": "window", "hours": ["19:00", "19:30"], "chance": 0.15},
         "duration": [90, 120], "cast": [{"group": "wedding"}],
         "route": ["melite_school", "kydathenaion_fountain"],
         "steps": [go(node="kydathenaion_fountain"), {"emit": {"sfx": "sfx/athens/aulos.wav"}}],
         "string": "wedding"},
        {"id": "funeral", "rarity": "uncommon", "size": "medium",
         "trigger": {"on": "window", "hours": ["03:30", "04:00"], "chance": 0.3,
                     "not_festival": "panathenaia"},
         "duration": [60, 75], "cast": [{"group": "funeral"}],
         "route": ["kerameikos_kilns", "dipylon", "cemetery"],
         "steps": [go(node="dipylon"), go(node="cemetery"), use(item=A + "g_grave_stele", slot="mourn",
                                                                 anim="idle", dur=(30, 40))],
         "card": "burial"},
        {"id": "dog_steals_fish", "rarity": "uncommon", "size": "small", "zone": "piraeus",
         "trigger": {"on": "reactive", "when": {"near": {"actor": A + "dog_laconian", "item": A + "g_stall",
                                                         "within": 2, "goods": "world.goods_fish"}}},
         "duration": [6, 8], "cast": [{"role": "dog", "count": 1}],
         "steps": [go(item=A + "g_stall", spot="beside"), {"take": "world.goods_fish"},
                   wander(radius=8, dur=(4, 6))], "sfx": "sfx/world/vendor.wav"},
        {"id": "megarian_turned_back", "rarity": "uncommon", "size": "small", "zone": "agora",
         "trigger": {"on": "window", "hours": ["07:00", "11:00"], "chance": 0.25}, "duration": [30, 40],
         "cast": [{"actor": A + "metic", "count": 1}, {"role": "archer", "count": 1}],
         "steps": [go(item=A + "horos", spot="beside"), wait(dur=(10, 15)), go(node="dipylon")],
         "card": "megara"},
        {"id": "rhapsode_recital", "rarity": "common", "size": "small", "zone": "agora",
         "trigger": {"on": "window", "hours": ["18:30", "19:00"], "chance": 0.6}, "duration": [90, 120],
         "cast": [{"actor": A + "rhapsode", "count": 1}, {"role": "shopper", "count": 6}],
         "steps": [go(item=A + "twelve_gods", spot="beside"), use(anim="talk", dur=(80, 110))],
         "card": "rhapsode"},
        {"id": "meton_dawn", "rarity": "daily", "size": "small", "zone": "pnyx",
         "trigger": {"on": "window", "hours": ["04:00", "05:00"], "chance": 1.0}, "duration": [60, 90],
         "cast": [{"actor": A + "meton", "count": 1}],
         "steps": [go(item=A + "meton_dial", slot="observe"), use(anim="gesture", dur=(50, 80))]},
        {"id": "lamps_lit", "rarity": "daily", "size": "small", "zone": "agora",
         "trigger": {"on": "window", "hours": ["19:30", "20:00"], "chance": 1.0}, "duration": [60, 90],
         "steps": [{"each": {"item": A + "g_brazier", "max": 4}, "state": "lit"}],
         "sfx": "sfx/world/lamp.wav"},
        {"id": "dogs_bark", "rarity": "common", "size": "small", "zone": "kollytos",
         "trigger": {"on": "window", "hours": ["21:00", "03:00"], "every": 5400}, "duration": [5, 6],
         "steps": [], "sfx": "sfx/world/dog_far.wav"},
        {"id": "swifts", "rarity": "daily", "size": "small", "zone": "acropolis",
         "trigger": {"on": "window", "hours": ["18:00", "19:00"], "season": ["spring", "summer"],
                     "chance": 1.0}, "duration": [60, 90], "cast": [{"actor": "world.swift", "count": 8}],
         "steps": [wander(radius=12, dur=(50, 80))], "sfx": "sfx/world/swifts.wav"},
        {"id": "meltemi", "rarity": "common", "size": "small", "zone": "piraeus",
         "trigger": {"on": "weather", "kind": "wind", "season": ["summer"], "hours": ["13:00", "18:00"]},
         "duration": [300, 400], "steps": [{"emit": {"fx": A + "sea_glint"}}]},
        {"id": "summer_storm", "rarity": "rare", "size": "medium", "zone": "hymettos",
         "trigger": {"on": "weather", "kind": "storm", "season": ["summer"]}, "duration": [90, 150],
         "steps": [], "sfx": "sfx/world/thunder_far.wav"},
        {"id": "flock_out", "rarity": "daily", "size": "small", "zone": "pnyx",
         "trigger": {"on": "window", "hours": ["05:00", "05:30"], "chance": 1.0}, "duration": [80, 100],
         "cast": [{"group": "flock"}], "steps": [wander(zone="pnyx", dur=(70, 90))],
         "sfx": "sfx/world/sheep_bells.wav"},
        {"id": "solon_memory", "rarity": "daily", "size": "small", "zone": "council",
         "trigger": {"on": "window", "hours": ["18:30", "19:00"], "chance": 1.0}, "duration": [80, 100],
         "cast": [{"actor": A + "solon", "count": 1}],
         "steps": [use(item=A + "royal_stoa", slot="herald", anim="talk", dur=(70, 90))], "card": "solon"},
        {"id": "olive_harvest", "rarity": "festival", "size": "medium", "zone": "ilissos",
         "trigger": {"on": "calendar", "festival": "olive_harvest", "hours": ["07:00", "08:00"]},
         "duration": [180, 220], "cast": [{"role": "farmer", "count": 8, "from": "district"}],
         "steps": [wander(zone="ilissos", dur=(30, 40)), use(anim="work_high", dur=(140, 170))]},
        {"id": "mysteries_procession", "rarity": "festival", "size": "large",
         "trigger": {"on": "calendar", "festival": "mysteries", "hours": ["06:00", "06:30"]},
         "duration": [240, 300], "cast": [{"role": "townsman", "count": 20}, {"role": "housewife", "count": 12},
                                          {"role": "priestess", "count": 2}],
         "route": ["eleusinion", "agora", "dipylon", "sacred_gate", "sacred_way_w"],
         "steps": [go(node="agora"), go(node="dipylon"), go(node="sacred_gate"), go(node="sacred_way_w")]},
        {"id": "city_dionysia", "rarity": "festival", "size": "large", "zone": "dionysos",
         "trigger": {"on": "calendar", "festival": "city_dionysia", "hours": ["07:00", "08:00"]},
         "duration": [300, 360], "cast": [{"role": "theatre_visitor", "count": 30}, {"role": "chorus", "count": 6}],
         "steps": [go(node="theatre"), use(item=A + "theatre", slot="watch", anim="sit", dur=(280, 340))]},
    ]


def figures() -> list[dict]:
    def fig(actor, presence, card_, sch=None, routines=None, **kw):
        f = {"actor": A + actor if actor else None, "presence": presence, "card": card_}
        if sch:
            f["schedule"] = sched(*sch)
            f["routines"] = routines
        f.update(kw)
        return {k: v for k, v in f.items() if v is not None}
    return [
        fig("pericles", "present", "pericles", [("07:00", "11:00", "agora"), ("14:00", "17:30", "rock"),
                                                ("18:00", "21:00", "home")],
            {"agora": {"loop": True, "steps": [go(node="bouleuterion"), use(anim="talk", dur=(30, 50)),
                                               go(node="stoa_poikile"), use(anim="gesture", dur=(15, 25))]},
             "rock": {"loop": True, "steps": [go(item=A + "sculpt_yard", slot="pheidias"),
                                              use(anim="talk", dur=(30, 50)), go(node="propylaia"),
                                              wait(dur=(15, 25))]},
             "home": {"steps": [go(node="kydathenaion_fountain"), use(anim="talk", until={"hour": "21:00"})]}},
            note="on assembly days the assembly event takes him to the Pnyx"),
        fig("aspasia", "present", "aspasia", [("09:00", "12:00", "court"), ("17:00", "21:00", "guests")],
            {"court": {"steps": [go(node="kydathenaion_fountain"), use(anim="sit", until={"hour": "12:00"})]},
             "guests": {"steps": [go(node="kydathenaion_fountain"), use(anim="talk", until={"hour": "21:00"})]}}),
        fig("socrates", "present", "socrates", [("07:00", "12:00", "agora"), ("14:30", "17:00", "ilissos"),
                                                ("17:00", "19:30", "simon")],
            {"agora": {"loop": True, "steps": [go(node="stoa_poikile"), use(anim="talk", dur=(30, 50)),
                                               go(node="agora"), use(anim="talk", dur=(20, 30))]},
             "ilissos": {"steps": [go(node="kallirrhoe"), use(anim="sit", until={"hour": "17:00"})]},
             "simon": {"steps": [go(item=A + "simon_shop", slot="sit"), use(anim="talk", until={"hour": "19:30"})]}}),
        fig("sophocles", "present", "sophocles", [("08:00", "12:00", "agora"), ("14:00", "17:00", "theatre")],
            {"agora": {"loop": True, "steps": [go(node="agora"), use(anim="talk", dur=(30, 50)),
                                               go(node="royal_stoa"), wait(dur=(15, 25))]},
             "theatre": {"steps": [go(node="theatre"), use(anim="gesture", until={"hour": "17:00"})]}}),
        fig("euripides", "present", "euripides", [("08:00", "12:00", "read"), ("14:00", "18:00", "theatre")],
            {"read": {"steps": [go(item=A + "stoa_poikile", slot="sit"), use(anim="write", until={"hour": "12:00"})]},
             "theatre": {"steps": [use(item=A + "theatre", slot="watch", anim="sit", until={"hour": "18:00"})]}}),
        fig("pheidias", "memory", "pheidias", [("18:30", "21:30", "memory")],
            {"memory": {"steps": [go(item=A + "sculpt_yard", slot="pheidias"),
                                  use(anim="work_high", dur=(20, 30)), use(anim="idle", until={"hour": "21:30"})]}},
            translucent=True),
        fig("mnesikles", "present", "mnesikles", [("07:00", "12:00", "gate"), ("15:00", "18:00", "gate")],
            {"gate": {"steps": [go(item=A + "propylaia", slot="mnesikles"),
                                use(anim="gesture", dur=(30, 50)), use(anim="idle", until={"hour": "12:00"})]}}),
        fig("protagoras", "present", "protagoras", note="walks with his pupils (protagoras_walk)"),
        fig("meton", "present", "meton", note="at his sundial at dawn (meton_dawn)"),
        fig("alcibiades", "present", "alcibiades", [("16:00", "19:00", "ride")],
            {"ride": {"steps": [go(node="lyceum"), wander(radius=8, dur=(60, 90))]}},
            note="rides with the cavalry in the procession"),
        fig("solon", "memory", "solon", note="dusk at the Royal Stoa (solon_memory)", translucent=True),
        fig("themistocles", "memory", "themistocles", [("18:30", "21:30", "memory")],
            {"memory": {"steps": [go(node="kantharos_quay"), use(anim="idle", until={"hour": "21:30"})]}},
            translucent=True),
        fig("theseus", "reenactor", "theseus", note="in the Panathenaic procession"),
        fig("rhapsode", "reenactor", "rhapsode", note="an informal recital at dusk (rhapsode_recital)"),
        fig(None, "shrine", "athena", at="great_altar"),
        fig(None, "shrine", "poseidon", at="pandroseion"),
        fig(None, "statue", "herakles", at="hephaisteion"),
        fig("philinna", "present", "philinna", [("05:00", "07:00", "water"), ("07:00", "12:00", "loom")],
            {"water": {"steps": [go(item=A + "se_fountain", slot="fill"), use(anim="carry_idle", dur=(20, 30))]},
             "loom": {"steps": [go(item=A + "g_loom", slot="weave"), use(anim="throw", until={"hour": "12:00"})]}}),
        fig("mania", "present", "mania", [("05:00", "12:00", "errands"), ("15:00", "19:00", "errands")],
            {"errands": {"loop": True, "steps": [go(node="kydathenaion_fountain"), wait(dur=(30, 50)),
                                                 go(node="se_fountain"), wait(dur=(20, 30))]}}),
        fig("manes", "present", "manes", [("05:30", "18:30", "kiln")],
            {"kiln": {"steps": [go(item=A + "g_kiln", slot="stoke"), use(anim="work_low", until={"hour": "18:30"})]}}),
        fig("kephalos", "present", "kephalos", [("07:00", "17:00", "workshop")],
            {"workshop": {"loop": True, "steps": [go(node="kephalos_workshop"), use(anim="talk", dur=(30, 50)),
                                                  go(node="piraeus_agora"), wait(dur=(20, 30))]}}),
        fig("sosias", "present", "sosias", [("06:00", "12:00", "charcoal")],
            {"charcoal": {"steps": [go(node="acharnian_gate"), go(node="market"),
                                    use(anim="idle", until={"hour": "12:00"})]}}),
        fig("nikarete", "present", "nikarete", [("05:30", "13:00", "bread")],
            {"bread": {"steps": [go(item=A + "g_stall", slot="buy"), use(anim="serve", until={"hour": "13:00"})]}}),
        fig("toxamis", "present", "toxamis", [("06:00", "19:00", "watch")],
            {"watch": {"loop": True, "steps": [go(item=A + "horos", spot="beside"), use(anim="guard", dur=(40, 60)),
                                               go(node="agora"), use(anim="gesture", dur=(10, 15))]}}),
        fig("euphiletos", "present", "euphiletos", [("05:00", "11:00", "grove"), ("15:00", "18:30", "grove")],
            {"grove": {"loop": True, "steps": [go(node="south_farms"), use(anim="work_low", dur=(40, 60))]}}),
        fig("hegeso", "present", "hegeso", [("08:00", "12:00", "home"), ("16:00", "19:00", "home")],
            {"home": {"loop": True, "steps": [go(node="kydathenaion_fountain"), wait(dur=(30, 50))]}}),
        fig("simon", "present", "simon", note="at his bench (the role cobbler draws him)"),
    ]


def cards() -> dict:
    F, L, I = "figure", "landmark", "idea"
    c = {
        "parthenon": card(L, "Παρθενών", "Parthenon",
            "Begun in 447 and finished this year with its pediments, the Doric temple of 8 by 17 "
            "columns houses Pheidias's gold and ivory Athena. Its west pediment shows Athena and "
            "Poseidon contesting Attica; the frieze inside the colonnade shows a procession like the "
            "one you can follow today. Temples were painted, never plain white."),
        "propylaia": card(L, "Προπύλαια", "The gateway, unfinished",
            "Mnesikles's gateway turns the steep west end of the rock into a stately climb: a central "
            "hall with Doric fronts, a ramp for the animals, a picture gallery in the north-west wing. "
            "This year the work stops; the lifting bosses stay on the blocks, and they are still there "
            "today."),
        "nike_bastion": card(L, "Πύργος", "Nike bastion",
            "A poros bastion beside the gateway with a small old shrine and altar of Athena Nike. The "
            "Ionic temple that stands here today is not built until the 420s."),
        "approach": card(L, "The approach", "Ramp to the rock",
            "A broad gravel ramp between retaining walls climbs from the Panathenaic Way to the gateway. "
            "Sacrificial cattle, riders and the whole procession come up this way."),
        "old_temple": card(L, "Ἀρχαῖος νεώς", "Old Temple of Athena",
            "The temple burned by the Persians in 480. Whether its western rooms were repaired and used "
            "is debated; here its foundations lie open with a repaired, roofed west chamber where the "
            "old olive-wood Athena Polias may be kept."),
        "pandroseion": card(L, "Πανδρόσειον", "The sacred olive",
            "A walled court round Athena's olive tree, her gift to the city in the contest with Poseidon. "
            "Burned in 480, it sprouted again the next day, people said. The tomb of the hero Kekrops "
            "lies beside it."),
        "promachos": card(L, "Ἀθηνᾶ Πρόμαχος", "The bronze Athena",
            "Pheidias's colossal bronze Athena, made around 460-450, stands between the gateway and the "
            "Old Temple. Sailors rounding Cape Sounion are said to have seen the glint of her spear tip. "
            "Her height is uncertain, perhaps 7 to 9 metres."),
        "brauronion": card(L, "Βραυρώνιον", "Artemis Brauronia",
            "A sanctuary of Artemis of Brauron with a stoa of two wings, where women dedicated clothing "
            "to the goddess after childbirth, and girls served her as little bears."),
        "chalkotheke": card(L, "Χαλκοθήκη", "The bronze store",
            "A plain hall where bronze dedications, weapons and votive offerings of Athena were stored, "
            "counted and listed on stone by her treasurers each year."),
        "great_altar": card(L, "Βωμός", "Great Altar of Athena",
            "The altar where the procession ends. Cattle are sacrificed here, a hundred at the Great "
            "Panathenaia, and the meat is shared out to the people in the Kerameikos and the Agora."),
        "zeus_polieus": card(L, "Διὸς Πολιέως", "Zeus of the city",
            "The sanctuary of Zeus Polieus, where the old ox-sacrifice of the Dipolieia is held at "
            "midsummer: the axe is tried for the killing and thrown into the sea."),
        "sculpt_yard": card(L, "The sculptors' yard", "Behind the Parthenon",
            "Blocks with their bosses, roughed-out figures and a two-legged crane: the last of the "
            "pediment work is coming down. Citizens, metics and enslaved men cut stone here side by "
            "side. At dusk, some say, Pheidias still walks among the blocks."),
        "hephaisteion": card(L, "Ἡφαιστεῖον", "Temple of Hephaistos",
            "A Doric temple of 6 by 13 columns on Kolonos Agoraios, almost finished. Its metopes show "
            "Herakles and Theseus; its cult statues are not made until 421-415. Bronze casters work in "
            "pits on the hill around it."),
        "royal_stoa": card(L, "Στοὰ Βασίλειος", "Royal Stoa",
            "A small Doric stoa facing the square where the king archon sits; the laws of Solon are "
            "displayed here on revolving wooden boards and on stone, for anyone to read."),
        "stoa_zeus": card(L, "Στοὰ τοῦ Διός", "Stoa of Zeus, a building site",
            "The Stoa of Zeus Eleutherios is dated around 430-420. In 432 it is at most a fresh "
            "building site, foundations pegged out, and possibly not begun at all; the game shows its "
            "footing."),
        "old_bouleuterion": card(L, "Βουλευτήριον", "Council house",
            "The council of 500, fifty men from each tribe chosen by lot for a year, meets here to "
            "prepare the assembly's business."),
        "tholos": card(L, "Θόλος", "Round dining hall",
            "The fifty councillors on duty, the prytaneis, eat here at public expense, and a third of "
            "them sleep here, so the city is never without a government."),
        "stoa_poikile": card(L, "Στοὰ Ποικίλη", "The Painted Stoa",
            "A long colonnade facing the Agora, hung with great painted panels of Marathon, the "
            "Amazons, the fall of Troy and Oinoe. Anyone may walk and talk here. The captured Spartan "
            "shields Pausanias saw came later, from 425 and 421."),
        "twelve_gods": card(L, "Βωμὸς τῶν δώδεκα θεῶν", "Altar of the Twelve Gods",
            "A fenced altar and a place of refuge for suppliants; distances from Athens were measured "
            "from here, the city's milestone point."),
        "tyrannicides": card(L, "Harmodios and Aristogeiton", "The Tyrannicides",
            "The bronze group by Kritios and Nesiotes (477/6) honours the two men who killed the tyrant's "
            "brother in 514. When the Persians carried off the first statue, the city simply made a new "
            "one."),
        "se_fountain": card(L, "Κρήνη", "South-east fountain house",
            "Water runs from lion-head spouts into the basin; women and enslaved girls fill their "
            "hydriai here at dawn and in the evening."),
        "lawcourt": card(L, "Δικαστήριον", "Law court enclosure",
            "A walled enclosure probably used by the courts (the identification is debated). Juries of "
            "hundreds of citizens over thirty are paid two obols a day."),
        "horos": card(L, "Ὅρος", "Boundary stone",
            "\"I am the boundary of the Agora\", says the inscribed marble post. Beyond it, people under "
            "a curse may not pass."),
        "simon_shop": card(L, "Σίμων", "Simon's shop",
            "A shoemaker's house and shop at the Agora's edge, where hobnails and a cup inscribed SIMONOS "
            "were found. Socrates is said to have sat at his bench."),
        "eleusinion": card(L, "Ἐλευσίνιον", "City Eleusinion",
            "The city sanctuary of Demeter and Kore on the Panathenaic Way, linked by the Sacred Way to "
            "Eleusis and its Mysteries."),
        "dipylon": card(L, "Δίπυλον", "The double gate",
            "The largest gate of Athens: two gate towers and a deep court. The Panathenaic Way begins "
            "here, and the procession sets out at dawn."),
        "sacred_gate": card(L, "Ἱερὰ Πύλη", "The Sacred Gate",
            "The Sacred Way to Eleusis leaves through this gate, with the Eridanos flowing in its "
            "channel beside the road."),
        "pnyx": card(L, "Πνύξ", "The assembly",
            "Every adult male citizen may come here to speak and vote by a show of hands. The audience "
            "sits on the natural slope facing the speakers' platform; perhaps forty meetings a year."),
        "meton_dial": card(L, "Ἡλιοτρόπιον", "Meton's sundial",
            "Here the astronomer Meton observed the summer solstice of 432 BC and proposed a cycle of "
            "19 years that brings the moon's months back into step with the sun's year."),
        "theatre": card(L, "Θέατρον Διονύσου", "Theatre of Dionysos",
            "Wooden bleachers on the south slope face a round earth orchestra with an altar and a simple "
            "wooden stage. The stone theatre comes a century later. Next spring Euripides will stage the "
            "Medea here."),
        "dionysos_temple": card(L, "Ναὸς Διονύσου", "Old temple of Dionysos",
            "A small poros temple of Dionysos Eleuthereus beside the theatre, home of the old wooden "
            "image of the god that is carried in at the City Dionysia."),
        "odeion": card(L, "Ὠιδεῖον", "Odeion of Pericles",
            "A square hall with a forest of columns under a pyramidal roof; Plutarch says it imitated "
            "the Persian king's tent. The music contests of the Great Panathenaia are held here."),
        "olympieion": card(L, "Ὀλυμπιεῖον", "Olympieion foundations",
            "A huge platform begun by the tyrants in the 6th century and abandoned; column drums lie in "
            "the grass. It will not be finished for six hundred years."),
        "kallirrhoe": card(L, "Καλλιρρόη", "The fair-flowing spring",
            "A spring in the bed of the Ilissos whose water was used for bridal baths. Plane trees and "
            "a grassy bank make it a place to sit and talk in the heat."),
        "lyceum": card(L, "Λύκειον", "The Lyceum",
            "A gymnasium in a grove outside the walls with a running track and a shrine of Apollo "
            "Lykeios. Hoplites and cavalry drill here; athletes run and wrestle in the afternoon."),
        "shipsheds": card(L, "Νεώσοικοι", "Ship sheds of Zea",
            "Long rows of roofed slipways where the triremes are hauled out of the water to dry. Athens "
            "has some 300 warships in 431."),
        "harbour": card(L, "Κάνθαρος", "Kantharos and the emporion",
            "The great harbour of Piraeus: quays, the long stoas of the emporion where merchants deal in "
            "grain from the Black Sea and Egypt, moles with towers narrowing the mouth."),
        "pentelikon_quarry": card(L, "Πεντελικόν", "The marble quarry",
            "Bright white-gold faces cut in steps, wedge slots, a sledge ramp: the Parthenon's marble "
            "starts here and goes down to the city on sledges and ox carts."),
        # figures
        "pericles": card(F, "Περικλῆς", "Pericles, first citizen",
            "Elected general year after year, Pericles persuaded the Athenians to rebuild the Acropolis "
            "with the allies' tribute. Thucydides wrote that Athens was in name a democracy but in fact "
            "ruled by its first man. This summer, Sparta's patience is running out."),
        "aspasia": card(F, "Ἀσπασία", "Aspasia of Miletus",
            "A foreign woman of learning and wit, Pericles's partner. Socrates is said to have learned "
            "rhetoric from her. Comic poets mocked her; later writers admired her. As a metic, her son "
            "by Pericles needed a special vote to become a citizen."),
        "socrates": card(F, "Σωκράτης", "Socrates, the questioner",
            "A stonemason's son, aged about 37, who walks barefoot in all weather and asks people what "
            "courage, justice or beauty really are, until they admit they do not know. He wrote "
            "nothing. Soon he will march to Potidaea as a hoplite."),
        "sophocles": card(F, "Σοφοκλῆς", "Sophocles, tragic poet",
            "Winner of more drama contests than anyone, and general with Pericles in the war against "
            "Samos. He also serves as priest of a healing hero. His Antigone asks what a citizen owes "
            "to the city and what to the gods."),
        "euripides": card(F, "Εὐριπίδης", "Euripides, tragic poet",
            "Restless, questioning, fond of books; tradition says he liked solitude. Next spring he will "
            "stage the Medea, a woman's fury against the man who betrayed her. It will come third. This "
            "afternoon he watches its chorus rehearse, a scroll in his lap."),
        "pheidias": card(F, "Φειδίας", "Pheidias, sculptor (a memory)",
            "He made the gold and ivory Athena inside the Parthenon and directed its sculpture. Enemies "
            "of Pericles accused him of stealing the statue's gold. One ancient writer says he died in "
            "an Athenian prison; another that he left for Olympia, where his Zeus became a wonder of the "
            "world. This summer, his yard works on without him."),
        "mnesikles": card(F, "Μνησικλῆς", "Mnesikles, architect",
            "His gateway to the Acropolis turns a steep rock into a stately climb. This year the work "
            "stops, with the stone bosses for lifting still on the blocks; the money and the men are "
            "wanted elsewhere. The bosses are still there today."),
        "protagoras": card(F, "Πρωταγόρας", "Protagoras, sophist",
            "'Man is the measure of all things.' The famous teacher from Abdera charges fees to train "
            "young men in argument, and walks with a crowd of pupils who turn about as he turns. Plato "
            "imagined Socrates debating him at the house of Kallias."),
        "meton": card(F, "Μέτων", "Meton, astronomer",
            "On the Pnyx this summer he marked the solstice, and he proposes a cycle of 19 years that "
            "brings the moon's months back into step with the sun's year. Comic poets laughed at him; "
            "astronomers used his cycle for centuries."),
        "alcibiades": card(F, "Ἀλκιβιάδης", "Alcibiades, Pericles's ward",
            "Eighteen, rich, beautiful and reckless, and adored by the city; today he rides with the "
            "cavalry in the procession, long-haired, in a purple cloak. At Potidaea, Socrates will save "
            "his life. Later he will betray Athens and return to it, twice."),
        "solon": card(F, "Σόλων", "Solon, lawgiver (a memory)",
            "Long ago he freed Athenians enslaved for debt and wrote the laws still kept on revolving "
            "wooden boards in the Royal Stoa. He wrote poems, too: 'I grow old, always learning many "
            "things.' At dusk he is remembered before the stoa."),
        "themistocles": card(F, "Θεμιστοκλῆς", "Themistocles, founder of the fleet (a memory)",
            "He persuaded Athens to spend its silver on ships, won at Salamis and walled Piraeus. "
            "Ostracised, he ended his life as a Persian governor. At dusk he is remembered on the quay, "
            "looking toward Salamis. His harbour still hums below him."),
        "theseus": card(F, "Θησεύς", "Theseus, founder-hero",
            "Slayer of the Minotaur, he joined the villages of Attica into a single city, the Athenians "
            "said. Kimon found his bones on Skyros and brought them home in triumph. In the procession "
            "a young man walks in his likeness, club in hand."),
        "rhapsode": card(F, "The rhapsode", "Singer of Homer",
            "Every fourth summer, at the Great Panathenaia, singers recite the Iliad and Odyssey in "
            "turn, by law. This year is not a great year, but he sings anyway. Listen, and Achilles' "
            "anger and Odysseus' long road home rise in the dusk."),
        "athena": card(F, "Ἀθηνᾶ", "Athena Polias, Parthenos, Promachos",
            "She won Attica from Poseidon by giving the olive. The Athenians bring her old olive-wood "
            "statue a new woven robe, perhaps every summer, certainly every fourth. The gold and ivory "
            "Athena in the Parthenon was a treasure as much as an image."),
        "poseidon": card(F, "Ποσειδῶν", "Poseidon, earth-shaker",
            "He struck the rock with his trident and a salt spring rose, but the gods gave the land to "
            "Athena. Athenians still showed the marks in the rock, and honoured him beside the hero "
            "Erechtheus. Sailors and rowers still pray to him before they put out."),
        "herakles": card(F, "Ἡρακλῆς", "Herakles, hero of the labours",
            "Strongest of heroes, son of Zeus and a mortal woman. His labours fill the metopes of the "
            "Hephaisteion and the Athenian treasury at Delphi; the Athenians claimed they were the first "
            "to honour him as a god. Look for his lion skin and club."),
        "philinna": card(F, "Philinna", "Wool-worker and mother",
            "Philinna spins wool before sunrise and weaves until noon. Her husband sits on the Council "
            "this year. She goes out for water, for festivals and to visit her sister. Her daughter will "
            "carry a basket in next year's procession, if "
            "the priestesses choose her."),
        "mania": card(F, "Mania", "Nurse",
            "Mania was born in Phrygia and sold at Ephesus as a girl. She has raised two of Philinna's "
            "children. Athenian grave stones sometimes honour nurses like her by name, kindly. She hums "
            "Phrygian songs to the baby, in a language no one else "
            "in the house knows."),
        "manes": card(F, "Manes", "Kiln-man",
            "Manes knows the kiln's moods: three firings, air in, air out, then in again, and red clay "
            "turns black where the painter's slip lies. He has saved some coins; some enslaved craftsmen "
            "in Athens worked on their own and paid their master a share."),
        "kephalos": card(F, "Kephalos", "Shield-maker",
            "Kephalos came from Syracuse at Pericles's invitation and makes shields in Piraeus in a large "
            "workshop. Metics like him pay a special tax, serve in the army and cannot own land, but "
            "Athens could not run without them. His sons will keep "
            "the workshop going."),
        "sosias": card(F, "Sosias", "Charcoal seller",
            "Sosias walks from Acharnai with two donkeys of oak charcoal. He votes in the assembly when "
            "the harvest allows, and grumbles that the city folk talk too much. His charcoal feeds the "
            "potters' kilns and the smithies, and warms the "
            "city's winters."),
        "nikarete": card(F, "Nikarete", "Bread-seller",
            "Nikarete sells barley cakes and wheat loaves from a basket in the Agora. Bread-women had a "
            "reputation for sharp tongues. She has seen every general of the last thirty years buy her "
            "bread, and tells you so, twice, before you have paid."),
        "toxamis": card(F, "Toxamis", "Scythian archer",
            "Toxamis is one of the city's Scythian archers: public slaves who keep order in the assembly "
            "and the courts. On assembly mornings they sweep the Agora with a rope dyed red, and, "
            "ancient commentators said, anyone marked with the red loses their pay."),
        "euphiletos": card(F, "Euphiletos", "Farmer",
            "Euphiletos tends olives and vines outside the walls and brings his oil to the city. In a "
            "war he would serve as a hoplite. Tonight he will sleep in the city, at his cousin's in "
            "Kollytos, to see the procession at dawn."),
        "hegeso": card(F, "Hegeso", "Girl",
            "Hegeso is eleven. Girls her age weave the new robe for Athena with the priestesses, and a "
            "few of good family carry baskets in the procession. She practises walking with a basket on "
            "her head, very straight, and does not drop it once."),
        "simon": card(F, "Simon", "Shoemaker",
            "Simon makes sandals at the corner of the Agora. Ancient writers said Socrates often sat at "
            "his bench to talk with young men too young to enter the Agora. The hobnails and his cup were "
            "found by archaeologists, just outside the boundary "
            "stone."),
        # ideas
        "democracy": card(I, "Democracy", "Rule by the people",
            "In 432, a few tens of thousands of men governed themselves directly: they spoke and voted "
            "in the assembly, sat on the Council by lot and judged in huge juries. Women, slaves and "
            "foreigners could not vote; Athens's freedom rested partly on the tribute of others."),
        "philosophy": card(I, "Philosophy", "From nature to how to live",
            "Earlier thinkers asked what the world is made of. In Athens, sophists like Protagoras "
            "taught argument for fees, and Socrates asked everyone what justice, courage and the good "
            "life really are. The questions moved from the stars to the street."),
        "drama": card(I, "Tragedy and comedy", None,
            "Plays are staged for Dionysos at the City Dionysia in spring and the Lenaia in winter, with "
            "choruses of citizens, three actors in masks and a prize for the best poet. A rich citizen "
            "pays for each chorus. The seats are still wooden."),
        "history": card(I, "History", "Herodotus and Thucydides",
            "Herodotus, tradition says, read from his Histories of the Persian Wars in Athens. A young "
            "Athenian named Thucydides is about to begin a history of the war that is coming, written to "
            "be a possession for all time, and to tell what really "
            "happened."),
        "curves": card(I, "The Parthenon's curves", None,
            "Nothing in the Parthenon is quite straight. The base rises about 6 cm in the middle of the "
            "short ends and about 10-11 cm along the long sides; the columns lean slightly inward and "
            "swell a little. Why the builders did it, to correct the eye or for life and tension, is "
            "still argued."),
        "planning": card(I, "A city on a grid", "Piraeus and Hippodamos",
            "Hippodamos of Miletus laid out Piraeus in a regular grid of streets, with zones for the "
            "harbour, the market and the houses, and argued about the best way to order a city. Athens "
            "itself, older, grew in winding lanes around its rock."),
        "medicine": card(I, "Hippocratic medicine", None,
            "Physicians of the Hippocratic school watched symptoms, took notes and looked for natural "
            "causes rather than divine ones. Athens hired public physicians. The cult of the healing god "
            "Asklepios arrives only in 420, and the great plague, "
            "which no physician can stop, in 430."),
        "laurion": card(I, "The silver of Laurion", None,
            "The owls in every purse come from the state mines at Laurion in south Attica, worked mostly "
            "by enslaved men in narrow, airless galleries. The mines are off this map; their silver is "
            "everywhere on it, in every purse and on every stall."),
        "league": card(I, "The League and its tribute", None,
            "Founded against Persia in 478, the Delian League is now an Athenian empire of some 150 "
            "cities. Their tribute arrives by sea; a sixtieth goes to Athena and is listed on stone on "
            "the Acropolis. Chios and Lesbos still send ships instead."),
        "megara": card(I, "The Megarian decree", None,
            "This year Athens has shut the traders of Megara out of the Agora and the League's harbours. "
            "A Megarian at the boundary stone is turned back. Sparta will call it one cause of the war "
            "that begins next spring, together with Potidaea."),
        "potidaea": card(I, "Potidaea", "The cloud on the horizon",
            "Potidaea, a city of the League in the north, has revolted with Corinth's help. Hoplites "
            "march down between the Long Walls to the ships; Socrates and Alcibiades will be among them. "
            "The great war with Sparta is only months "
            "away."),
        "metics": card(I, "Metics", "Resident foreigners",
            "Perhaps ten to twenty-five thousand free foreigners live in Attica with their families: "
            "traders, bankers, potters, shield-makers. They pay a special tax, serve in the army and the "
            "fleet and carry trays in the procession, but cannot vote or own land."),
        "slavery": card(I, "Enslaved Athenians", None,
            "A very large number of the people you see are enslaved: nurses, porters, kiln-men, miners, "
            "even the city's own archers. Many work beside free men at the same tasks; some live on their "
            "own and pay their owner a share. Their freedom was not theirs to choose."),
        "women": card(I, "Women's lives", None,
            "Citizen women run the household, spin and weave, fetch water, visit, mourn and serve as "
            "priestesses; wealthy women go out less. Poorer women sell in the market and nurse. Women "
            "could not vote, but the city's greatest festivals needed them."),
        "symposium": card(I, "The symposium", "The drinking party",
            "After dinner, men recline on couches in the andron, mix wine with water in a krater, sing, "
            "play kottabos and talk. Hired musicians, often enslaved, play the aulos. From the street you "
            "hear only laughter and a lyre, late into the "
            "night."),
        "burial": card(I, "Funerals", None,
            "The dead are carried out before dawn, as an old law requires, with women singing laments "
            "and an aulos player, to graves along the roads outside the walls. Painted stelai and "
            "white-ground oil flasks honour them, and families come back to the graves with ribbons "
            "and oil."),
        # roles
        "seller": card("role", "Market seller", None, "Sells from a trestle stall: bread, oil, pots, fish, "
                       "garlic; bargains loudly and packs up at midday."),
        "banker": card("role", "Money-changer", None, "At his table he tests coins, weighs them and changes "
                       "foreign silver for Athenian owls."),
        "citizen": card("role", "Citizen", None, "In a himation, he shops in the morning, talks in the "
                        "stoas and walks the city in the cool of the evening."),
        "elder": card("role", "Old man", None, "Sits in the shade of the stoa with his staff and watches "
                      "the city go by, ready to argue."),
        "porter": card("role", "Porter", None, "Enslaved or free, he carries sacks and jars between "
                       "the quays, the gates and the stalls."),
        "scythian": card("role", "Scythian archer", None, "A public slave of the city in a pointed cap "
                         "and trousers, keeping order in the Agora and the courts."),
        "water_carrier": card("role", "Water carrier", None, "Fills her hydria at the fountain house, lifts "
                              "it onto her head and walks home."),
        "philosopher": card("role", "A talker", None, "Walks in the stoa with whoever will listen and asks "
                            "what they mean by what they say."),
        "youth": card("role", "Young man", None, "In a short cloak and broad hat, he follows a teacher "
                      "about the Agora and argues back."),
        "councillor": card("role", "Councillor", None, "Chosen by lot for a year, he prepares the "
                           "assembly's business and dines in the Tholos when his tribe is on duty."),
        "herald": card("role", "Herald", None, "Calls the citizens to order, proclaims decrees and calls "
                       "for silence before a speech."),
        "juror": card("role", "Juror", None, "A citizen over thirty with a bronze ticket, paid two obols a "
                      "day to judge a case before sunset."),
        "potter": card("role", "Potter", None, "Wedges the clay, throws a pot on the kick wheel, trims it "
                       "and fixes the handles."),
        "painter": card("role", "Vase painter", None, "Draws the figures in fine slip, fills the ground "
                        "black around them and adds the details before the firing."),
        "kiln_man": card("role", "Kiln-man", None, "Stacks the kiln, stokes it and controls the air "
                         "through three firings."),
        "clay_digger": card("role", "Clay digger", None, "Digs clay in the pits outside the Dipylon and "
                            "carries it to the workshops to soak."),
        "mourner": card("role", "Mourner", None, "Brings oil flasks and ribbons to a family grave and sits "
                        "awhile beside the painted stone."),
        "priest": card("role", "Priest or priestess", None, "Opens the shrine, pours a libation, prays "
                       "and tends the sacred olive."),
        "woman": card("role", "Citizen woman", None, "A himation drawn over her hair, she fetches water, "
                      "visits a neighbour and stops at the household shrine."),
        "mason": card("role", "Mason", None, "Hoists and sets blocks, clamps them with iron and lead and "
                      "dresses the faces."),
        "sculptor": card("role", "Sculptor", None, "Roughs out with the point, works with the claw chisel, "
                         "smooths with a rasp and emery."),
        "owl": card("role", "Little owl", None, "Athena's bird, common on the rock and the walls; it "
                    "calls at night."),
        "enslaved_woman": card("role", "Enslaved woman", None, "A nurse or a maid, carrying water, a baby "
                               "or the shopping through the lanes."),
        "shopkeeper": card("role", "Shopkeeper", None, "Sells from the front room of her house: wool, "
                           "garlands, perfume, lamps."),
        "weaver": card("role", "Wool-worker", None, "Cards, spins and weaves on the warp-weighted loom, "
                       "as women of every class did."),
        "enslaved_man": card("role", "Enslaved worker", None, "Carries firewood and water, works in a "
                             "shop or a field, often beside his owner."),
        "child": card("role", "Child", None, "Plays knucklebones, spins a top or chases a hoop in the "
                      "lanes."),
        "school": card("role", "Schoolboy", None, "Learns his letters, Homer and the lyre at a small "
                       "school in Melite."),
        "paidagogos": card("role", "Paidagogos", None, "The enslaved man who walks a boy to school and "
                           "keeps an eye on him."),
        "smith": card("role", "Smith", None, "Works the bellows and hammers bronze and iron into tools, "
                      "armour and shield facings."),
        "caster": card("role", "Bronze caster", None, "Packs moulds, melts bronze and pours it in pits on "
                       "the hill of the Hephaisteion."),
        "chorus": card("role", "Chorus member", None, "A citizen who rehearses the songs and steps of a "
                       "tragic chorus for months."),
        "aulos": card("role", "Aulos player", None, "Plays the double pipes for the chorus by day and at "
                      "a symposium by night."),
        "rower": card("role", "Rower", None, "A poorer citizen, metic or enslaved man who pulls an oar in "
                      "a trireme, in time to the piper."),
        "docker": card("role", "Dock worker", None, "Hauls ropes and carries amphorae and sacks "
                       "between the ships and the emporion."),
        "metic": card("role", "Merchant", None, "A resident foreigner trading grain, wine and timber "
                      "in the emporion of Piraeus."),
        "shipwright": card("role", "Shipwright", None, "Shapes pine and fir from Macedon with the adze and "
                           "pitches the hulls of triremes."),
        "ionian": card("role", "Ionian visitor", None, "A trader or envoy from the League's Greek "
                       "cities across the Aegean."),
        "thracian": card("role", "Thracian", None, "From the north, where Athens gets timber and silver, "
                         "and many of its slaves."),
        "spectator": card("role", "Festival-goer", None, "Out for the Panathenaia in a clean "
                          "himation, to watch the procession pass and claim a share of the "
                          "meat."),
        "farmer": card("role", "Farmer", None, "Hoes the vines and olives, brings the threshed barley "
                       "home and goes to the city on market days."),
        "thresher": card("role", "Thresher", None, "Spreads the barley on the floor, drives the animals "
                         "round and winnows the grain in the wind."),
        "presser": card("role", "Olive presser", None, "Crushes olives from the store, packs the baskets "
                        "under the beam and decants the oil into jars."),
        "herder": card("role", "Goatherd", None, "Takes the goats and sheep up the hills at dawn and "
                       "brings them down at dusk."),
        "athlete": card("role", "Athlete", None, "Runs, wrestles and scrapes the oil and dust off with a "
                        "strigil, naked as Greeks trained."),
        "hoplite": card("role", "Hoplite", None, "A citizen who can afford a bronze shield, helmet and "
                        "spear, drilling at the Lyceum."),
        "trainer": card("role", "Trainer", None, "Watches the athletes with his rod, corrects a hold and "
                        "calls the pace."),
        "quarry_hauler": card("role", "Quarry hauler", None, "Free and enslaved men rope the blocks "
                              "down the sledge ramp and clear the spoil."),
        "quarryman": card("role", "Quarryman", None, "Cuts a channel round a block, drives the wedges and "
                          "levers the marble free."),
    }
    return c


STRINGS = {
    "first_visit": "Hekatombaion, 432 BC. The Parthenon is finished, the Propylaia has just stopped, and "
                   "at dawn the procession leaves the Dipylon for the rock.",
    "procession": "The Panathenaic procession has left the Dipylon.",
    "assembly": "The archers sweep the Agora with the red rope: the assembly meets on the Pnyx.",
    "embark": "Hoplites march down between the Long Walls to the ships for Potidaea.",
    "torch_race": "Torches in the dark: the runners race from the Academy to the rock.",
    "wedding": "Torches and an aulos: a bride is led to her new home.",
    "decorate_zone": "A courtyard house in Melite, with a garden to furnish.",
}


def theme(view) -> dict:
    return {
        # Multipliers on the engine's own phase grade ([1, 1, 1] = the corner's look; see the
        # Pārsa note): pink-gold dawn, a bright warm summer day, honey-rose dusk without the
        # all-orange cast a strong multiplier gives, a mild night as readable as the corner's.
        "grading": {"dawn": [1.03, 0.97, 0.93], "day": [1.02, 1.01, 0.97], "dusk": [1.02, 0.95, 0.89],
                    "night": [0.96, 0.97, 1.03]},
        "haze": {"colour": [0.93, 0.89, 0.80], "strength": 0.12, "toward": "south-west"},
        "weather": {
            "summer": {"showers": 0, "clouds": 1, "wind": 0.5, "wind_from": "north-east",
                       "note": "calm mornings; the meltemi rises in the afternoon; one rare storm"},
            "autumn": {"showers": 2, "clouds": 3, "wind": 0.4, "note": "the first rains"},
            "winter": {"showers": 3, "clouds": 4, "wind": 0.4, "note": "mild rain; snow on the far mountains"},
            "spring": {"showers": 1, "clouds": 2, "wind": 0.35, "note": "clear and breezy"}},
        "ambience": {
            "beds": [{"file": "amb/athens/day.ogg", "hours": ["05:00", "19:30"]},
                     {"file": "amb/athens/night.ogg", "hours": ["19:30", "05:00"]}],
            "zones": [{"rect": grid_rect(view, "agora"), "file": "amb/athens/agora.ogg", "gain": 0.8,
                       "hours": ["06:00", "19:00"], "count_driven": {"roles": ["stall_keeper", "shopper"],
                                                                      "full": 12}},
                      {"rect": grid_rect(view, "acropolis"), "file": "amb/athens/rock.ogg", "gain": 0.7,
                       "hours": ["05:00", "19:30"]},
                      {"rect": grid_rect(view, "kerameikos"), "file": "amb/athens/potters.ogg", "gain": 0.7,
                       "hours": ["05:30", "18:30"]},
                      {"rect": grid_rect(view, "piraeus"), "file": "amb/athens/sea.ogg", "gain": 0.8},
                      {"rect": grid_rect(view, "harbour"), "file": "amb/athens/sea.ogg", "gain": 0.8}],
            "loops": [{"slot": A + "g_wheel.throw", "file": "amb/athens/wheel.ogg", "when": "worked"},
                      {"slot": A + "g_kiln.stoke", "file": "amb/athens/kiln.ogg", "when": "firing"},
                      {"slot": A + "g_forge.work", "file": "amb/world/smith.ogg", "when": "worked"},
                      {"slot": A + "g_loom.weave", "file": "amb/world/loom.ogg", "when": "worked"},
                      {"item": A + "g_brazier", "file": "amb/world/brazier.ogg", "when": "lit"}],
            "one_shots": {"sculpt_yard.carve": "sfx/world/chisel.wav", "pentelikon_quarry.cut": "sfx/world/hammer.wav"},
            "cicadas": {"hours": ["09:00", "18:00"], "season": ["summer"], "weather": "clear", "fade_s": 20}},
        "music": {"day": "music/athens/day.ogg", "night": "music/athens/night.ogg"},
        "arrive": "sfx/athens/arrive.wav",
    }


def build(view) -> dict:
    return SEASONS.apply({
        "version": 1, "id": "athens", "name": "Athens", "native": "Ἀθῆναι",
        "caption": "Athens · 432 BC",
        "era": "The Athens of Pericles · 432 BC",
        "theme": theme(view),
        "densities": DENSITIES,
        "districts": districts(),
        "roles": roles(),
        "groups": groups(),
        "chains": chains(),
        "festivals": FESTIVALS,
        "events": events(),
        "days_shown": [{"day": 5, "label": "An ordinary summer day (week day 1)"},
                       {"day": 2, "label": "Assembly day (week day 2)"},
                       {"day": 1, "label": "The Panathenaia (summer, day 2)"}],
        "figures": figures(),
        "lanes_tokens": [{"actor": A + "merchant", "lane": "athens:kantharos", "count": 2},
                         {"actor": A + "trireme", "lane": "athens:zea", "count": 2},
                         {"actor": A + "fishing", "lane": "athens:mounychia", "count": 2}],
        "cards": cards(),
        "strings": STRINGS,
        "decorate": {"rect": [286, 659, 296, 669]},
        "journal": ["landmark:*", "figure:*", "chain:*", "idea:*", "event:panathenaic_procession"],
    })
