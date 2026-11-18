"""Rome's life and text: who is where at each hour of an April day in AD 126, what they do, the
chains of goods, the Parilia and the other events, the named figures and every card
(`assets/regions/rome.json`).

Sources: `docs/design/cities/rome.md` as corrected by the fact-check
(`docs/design/cities/fact-check.md` §3): the Parilia was "now called" the Romaia by Athenaeus's
time (about AD 200), not renamed by decree; Ovid's shepherds purify the flocks with smoke at
twilight (the ground is sprinkled, not the sheep) and pray facing the east; Marcus is four, five
on 26 April; Hadrian's, Sabina's and Antinous's presence on the day is not recorded, so the game
imagines them here and their cards say so; Apollodorus's fate and Cloelia's statue are doubtful
and their cards say so; Cornelia's surviving base is Augustan by its letters and the seated statue
is placed "in a portico" by Pliny; the Pantheon's bronze tiles are not known to have been gilded;
the vigiles' reward went to informally freed slaves (Junian Latins); the barge takes "a few days"
upriver; Juvenal's toga line is about country Italy.

Conventions shared with Athens and Pārsa (see `out/reports/world-life.md`): populations are
`density[hour] x max_per_chunk` per 1 024 tiles of a district; an hour no schedule block covers is
indoors or away; events start at their game hour but run in real seconds and may overrun it (a
game hour is 30 real seconds), their participants busy until they end; processions are sized to
90-120 real seconds by route length and pace.

Built by `tools/worldgen/build.sh --city rome`, checked by `worldgen.citylife`.
"""

from __future__ import annotations

from worldgen import citylife as CL
from worldgen import seasonlife as SL
from worldgen.citylife import card, curve, go, grid_rect, pop, role, sched, use, wait, wander

SEASONS = SL.sibling(__file__, "seasons")
SEASON_BEDS = SEASONS.ROME_BEDS
R = "rome."
# The four-day week (living-world §4.1): market day (nundinae) and the races on day 0, the Senate
# on day 1, a game day at the amphitheatre on day 2, the grain distribution on day 3.
MARKET = {"every": 4, "offset": 0}
SENATE = {"every": 4, "offset": 1}
RACES = SENATE      # the circus races on Senate days, never on a festival's own games
GAMES = {"every": 4, "offset": 3}
DOLE = {"every": 4, "offset": 2}
FEAST = {"festival": "parilia"}
WORKDAY = {"not_festival": "parilia"}     # courts, Senate and the building site rest on the day

DENSITIES = {
    "always": [1.0] * 24,
    "day": curve({0: 0, 5: 0.2, 6: 0.7, 7: 1, 12: 0.75, 14: 0.9, 16: 1, 18: 0.6, 19: 0.35,
                  20: 0.15, 21: 0.05, 22: 0}),
    # The Forum fills for the morning's business, thins at midday and fills again in the golden
    # late afternoon with people walking home from the baths.
    "forum": curve({0: 0, 5: 0.15, 6: 0.6, 7: 1, 12: 0.75, 14: 0.85, 16: 1, 18: 0.55, 19: 0.3,
                    20: 0.1, 21: 0}),
    "market": curve({0: 0, 5: 0.3, 6: 0.8, 7: 1, 12: 0.7, 14: 0.85, 17: 0.7, 18: 0.4, 19: 0.1,
                     20: 0}),
    "work": curve({0: 0, 5: 0.4, 6: 0.9, 7: 1, 12: 0.6, 14: 1, 17: 0.7, 18: 0.3, 19: 0}),
    "morning": curve({0: 0, 6: 0.6, 7: 1, 12: 0.3, 13: 0}),
    # Bakers knead and fire before dawn (bible §6.9); their day is over by the afternoon.
    "dawn_work": curve({0: 0, 2: 0.7, 3: 1, 8: 1, 11: 0.7, 13: 0.5, 17: 0.4, 19: 0.1, 20: 0}),
    "houses": curve({0: 0, 4: 0.2, 5: 0.6, 6: 1, 12: 0.75, 14: 0.85, 17: 1, 19: 0.6, 20: 0.35,
                     21: 0.15, 22: 0}),
    "salutatio": curve({0: 0, 4: 0.5, 5: 1, 7: 0.5, 8: 0}),
    # The baths fill after the eighth hour (bible §6.9).
    "baths": curve({0: 0, 9: 0.15, 12: 0.4, 13: 0.8, 14: 1, 16: 1, 17: 0.7, 18: 0.3, 19: 0}),
    "evening": curve({0: 0.15, 1: 0, 17: 0.3, 18: 0.8, 19: 1, 22: 0.5, 23: 0.2}),
    "night": curve({0: 1, 4: 0.6, 5: 0.2, 6: 0, 19: 0.4, 20: 0.8, 21: 1}),
    "watch": curve({0: 0.6, 6: 1, 20: 0.8, 22: 0.6}),
    "children": curve({0: 0, 6: 0.4, 7: 0.9, 8: 1, 12: 0.6, 14: 1, 18: 0.6, 19: 0.3, 20: 0}),
    "graze": curve({0: 0.2, 5: 0.7, 6: 1, 19: 0.6, 20: 0.2}),
    "fields": curve({0: 0, 5: 0.5, 6: 1, 11: 0.8, 12: 0.5, 14: 0.8, 15: 1, 18: 0.5, 19: 0.1,
                     20: 0}),
    "harbour": curve({0: 0.05, 4: 0.3, 5: 0.8, 6: 1, 12: 0.7, 14: 1, 18: 0.6, 19: 0.3, 20: 0.1}),
    "afternoon": curve({0: 0, 12: 0.3, 13: 0.8, 14: 1, 17: 0.8, 18: 0.3, 19: 0}),
    "festival": curve({0: 0.05, 4: 0.2, 5: 0.5, 6: 0.8, 8: 1, 12: 0.8, 14: 1, 18: 1, 20: 0.9,
                       21: 0.6, 22: 0.3, 23: 0.05}),
    "birds": curve({0: 0, 4: 0.3, 5: 1, 19: 1, 20: 0.4, 21: 0}),
    # The Parilia's evening: feasting in the streets and the fires (bible §7.2).
    "parilia_night": curve({0: 0.05, 1: 0, 17: 0.4, 18: 0.8, 19: 1, 22: 0.6, 23: 0.1}),
    # Street counters serve from dawn until well after dark (bible §6.3, row 8).
    "evening_shop": curve({0: 0, 5: 0.4, 6: 0.9, 7: 1, 13: 0.8, 16: 1, 21: 0.6, 22: 0.2, 23: 0}),
    "road": curve({0: 0, 5: 0.3, 6: 0.8, 8: 1, 12: 0.7, 14: 0.9, 17: 1, 18: 0.6, 19: 0.2,
                   20: 0}),
}

RAIN = {"when": {"weather": "rain"}, "routine": "shelter", "priority": 2}


def per(role_, item, count=1, density="always", **kw) -> dict:
    return CL.per(role_, R + item, count, density, **kw)


def loop(*steps) -> dict:
    return {"loop": True, "steps": list(steps)}


def once(*steps) -> dict:
    return {"steps": list(steps)}


def shelter_door(within: int = 12) -> dict:
    return once(go(slot_kind="door", within=within),
                {"enter": {"here": True}, "until": {"weather": "clear"}})


def shelter_at(node: str) -> dict:
    """Under a portico or a basilica's arcade until the shower passes."""
    return once(go(node=node), use(anim="idle", until={"weather": "clear"}))


def home_for(until: str, within: int = 14) -> dict:
    """Indoors for the rest of the block: dinner, sleep (not drawn)."""
    return once(go(slot_kind="door", within=within), {"enter": {"here": True}, "until": {"hour": until}})


def roles() -> list[dict]:
    X = []

    def add(*a, **kw):
        X.append(role(*a, **kw))

    # --- the Forum and the fora -------------------------------------------------------------
    add("forum_crowd", R + "citizen", "Citizen in the Forum", sched(
        ("06:00", "12:00", "business"), ("12:00", "14:00", "rest"), ("14:00", "19:30", "stroll")),
        {"business": loop(go(node="forum"), use(anim="talk", dur=(15, 25)), go(node="rostra"),
                          use(anim="idle", dur=(15, 30)), go(node="basilica_julia"),
                          use(anim="sit", dur=(20, 40)), go(node="curia"), wander(radius=4, dur=(15, 25))),
         "rest": loop(go(node="basilica_julia"), use(anim="sit", dur=(60, 90))),
         "stroll": loop(go(node="forum"), use(anim="talk", dur=(15, 25)), go(node="vesta"),
                        wander(radius=4, dur=(20, 30)), go(node="via_sacra_velia"), wait(dur=(8, 14))),
         "shelter": shelter_at("basilica_julia")}, interrupts=[RAIN], card="plebs")
    add("client", R + "togatus", "Client in a toga", sched(
        ("04:30", "07:00", "salutatio"), ("07:00", "12:00", "forum"), ("13:30", "16:30", "baths"),
        ("16:30", "21:00", "dinner")),
        {"salutatio": once(go(item=R + "r_domus", slot="salutatio", within=24),
                           use(anim="idle", dur=(40, 70)), use(anim="talk", dur=(10, 20)),
                           wait(dur=(20, 40))),
         "forum": loop(go(node="forum"), use(anim="gesture", dur=(10, 20)), go(node="basilica_julia"),
                       use(anim="talk", dur=(20, 30)), go(node="rostra"), use(anim="idle", dur=(15, 25))),
         "baths": loop(go(node="agrippa_baths"), wait(dur=(40, 60)), wander(radius=5, dur=(20, 30))),
         "dinner": home_for("21:00", 20), "shelter": shelter_at("basilica_julia")},
        interrupts=[RAIN], card="client")
    add("senator", R + "senator", "Senator", sched(
        ("05:00", "07:00", "receive"), ("07:00", "12:00", "forum"), ("13:30", "16:00", "baths"),
        ("16:00", "21:00", "dinner")),
        {"receive": once(go(item=R + "r_domus", slot="door", within=20), use(anim="talk", dur=(60, 90))),
         "forum": loop(go(node="curia"), use(anim="gesture", dur=(15, 25)), go(node="forum"),
                       use(anim="talk", dur=(20, 30)), go(node="basilica_julia"), wait(dur=(15, 25))),
         "baths": loop(go(node="agrippa_baths"), wait(dur=(40, 70))),
         "dinner": home_for("21:00", 20), "shelter": shelter_at("curia")},
        interrupts=[RAIN], card="senator")
    add("lictor", R + "lictor", "Lictor with the fasces", sched(("06:00", "17:00", "escort")),
        {"escort": loop({"follow": {"actor": R + "senator"}, "dur": [50, 80], "spacing": 1.2},
                        go(node="curia"), use(anim="guard", dur=(20, 30)))}, card="lictor")
    add("advocate", R + "togatus", "Advocate", sched(("07:00", "12:00", "plead")),
        {"plead": loop(go(home="court"), use({"home": "court"}, anim="gesture", dur=(30, 50)),
                       use(anim="talk", dur=(15, 25)), use(anim="idle", dur=(10, 20)))},
        home={"item": R + "julia", "slot": "court"}, card="advocate")
    add("gamester", R + "citizen", "Idler at a gaming board", sched(("08:00", "18:00", "play")),
        {"play": loop(go(home="game"), use({"home": "game"}, anim="sit", dur=(60, 100)),
                      use(anim="talk", dur=(10, 20)))},
        home={"item": R + "julia", "slot": "game"}, card="gaming_board")
    add("orator", R + "togatus", "Speaker on the Rostra", sched(("08:00", "11:30", "speak")),
        {"speak": loop(go(home="orator"), use({"home": "orator"}, anim="gesture", dur=(40, 60)),
                       use(anim="idle", dur=(20, 40)))},
        home={"item": R + "rostra", "slot": "orator"}, card="rostra_speaker")
    add("schoolmaster", R + "teacher", "Schoolmaster", sched(("06:30", "11:30", "teach")),
        {"teach": loop(go(home="school"), use({"home": "school"}, anim="talk", dur=(40, 60)),
                       use(anim="write", dur=(20, 30)))},
        home={"item": R + "forum_square", "slot": "school"}, card="school")
    add("pupil", R + "child", "Pupil", sched(("06:30", "11:30", "school"), ("11:30", "18:00", "play")),
        {"school": loop({"follow": {"actor": R + "teacher"}, "dur": [60, 90], "spacing": 0.9},
                        go(node="basilica_julia"), use(anim="kneel", dur=(40, 60))),
         "play": loop(wander(radius=6, dur=(20, 40)), use(anim="run", dur=(6, 10)))}, card="school")
    add("seller", R + "working_woman", "Seller in the arcades", sched(
        ("06:00", "12:00", "sell"), ("14:00", "18:30", "sell")),
        {"sell": loop(go(home="shop"), use({"home": "shop"}, anim="serve", dur=(30, 50),
                                           effect="open_shutters"), use(anim="idle", dur=(6, 12)))},
        home={"item": R + "aemilia", "slot": "shop"}, card="seller")
    add("porter", R + "enslaved", "Porter", sched(("05:30", "12:00", "carry"), ("14:00", "18:30", "carry")),
        {"carry": loop(go(item=R + "piperataria", spot="beside"), use(anim="carry_idle", dur=(6, 10)),
                       {"take": "world.goods_bale"}, go(node="markets"), {"put": "world.goods_bale"},
                       go(node="forum"), wait(dur=(10, 20)))}, card="porter")
    add("attendant", R + "enslaved", "Household slave", sched(
        ("05:00", "12:00", "attend"), ("13:30", "19:00", "attend")),
        {"attend": loop({"follow": {"actor": R + "matron"}, "dur": [50, 80], "spacing": 1.0},
                        use(anim="carry_idle", dur=(10, 20))), "shelter": shelter_door(16)},
        interrupts=[RAIN], card="enslaved")
    add("matron", R + "matron", "Matron", sched(
        ("06:30", "12:00", "errands"), ("13:30", "16:30", "visits"), ("16:30", "20:00", "home")),
        {"errands": loop(go(node="forum"), use(anim="talk", dur=(15, 25)),
                         go(item=R + "aemilia", spot="beside"), use(anim="serve", dur=(10, 20)),
                         go(node="vesta"), use(anim="idle", dur=(10, 15))),
         "visits": loop(go(slot_kind="door", within=16), wait(dur=(30, 50)), wander(radius=5, dur=(20, 30))),
         "home": home_for("20:00", 20), "shelter": shelter_at("basilica_julia")},
        interrupts=[RAIN], card="matron")
    add("vestal", R + "vestal", "Vestal Virgin", sched(
        ("04:00", "12:00", "fire"), ("14:00", "19:30", "fire")),
        {"fire": loop(go(item=R + "vestals", slot="door"), wait(dur=(20, 30)), go(node="vesta"),
                      use(anim="pray", dur=(30, 50)), go(node="vestals"), use(anim="idle", dur=(20, 40)))},
        card="vestals_order")
    add("flamen", R + "flamen", "Priest", sched(("05:00", "12:00", "rites"), ("15:00", "18:30", "rites")),
        {"rites": loop({"pick": [
            {"weight": 1, "steps": [go(node="vesta"), use(anim="pray", dur=(15, 25))]},
            {"weight": 1, "steps": [go(node="forum"), use(anim="pour", dur=(10, 15))]},
            {"weight": 2, "steps": [go(node="capitolium"), wander(radius=4, dur=(20, 30)),
                                    use(anim="pour", dur=(10, 15))]}]})}, card="flamen")
    add("temple_priest", R + "flamen", "Priest at the altar", sched(("05:30", "11:30", "offer")),
        {"offer": loop(go(home="sacrifice"), use({"home": "sacrifice"}, anim="pour", dur=(20, 30)),
                       use(anim="pray", dur=(20, 30)), use(anim="idle", dur=(10, 20)))},
        home={"item": R + "capitolium", "slot": "sacrifice"}, card="flamen")
    add("hercules_priest", R + "flamen", "Priest of Hercules", sched(("06:00", "11:00", "offer")),
        {"offer": loop(go(home="sacrifice"), use({"home": "sacrifice"}, anim="pour", dur=(20, 30)),
                       use(anim="pray", dur=(15, 25)))},
        home={"item": R + "ara_maxima", "slot": "sacrifice"}, card="ara_maxima_rite")
    add("worshipper", R + "citizen", "Worshipper", sched(("05:30", "12:00", "visit"), ("14:00", "18:30", "visit")),
        {"visit": loop(go(node="capitolium"), use(anim="idle", dur=(20, 30)), go(node="arx"),
                       use(anim="talk", dur=(10, 20)), go(node="clivus_foot"), wait(dur=(10, 15))),
         "shelter": shelter_door(20)}, interrupts=[RAIN], card="plebs")
    add("soldier", R + "praetorian", "Soldier of the urban cohorts", sched(("00:00", "24:00", "watch")),
        {"watch": loop(go(node="forum"), use(anim="guard", dur=(40, 70)), go(node="curia"),
                       use(anim="march", dur=(10, 15)), go(node="rostra"), use(anim="guard", dur=(30, 50)))},
        card="urban_cohort")
    add("pigeon", R + "pigeon", "Pigeon", sched(("05:00", "19:30", "peck")),
        {"peck": loop(wander(radius=5, dur=(10, 20)), use(anim="peck", dur=(10, 20)))})
    add("greek", R + "greek_teacher", "Greek teacher", sched(("07:00", "12:00", "teach"), ("14:00", "18:00", "teach")),
        {"teach": loop(go(node="trajan_forum"), use(anim="talk", dur=(30, 50)), wander(radius=4, dur=(20, 30)),
                       go(node="forum"), use(anim="talk", dur=(20, 30))), "shelter": shelter_at("trajan_forum")},
        interrupts=[RAIN], card="greek_learning")
    add("syrian", R + "syrian_merchant", "Syrian merchant", sched(("06:30", "12:00", "trade"), ("14:00", "18:00", "trade")),
        {"trade": loop(go(item=R + "piperataria", spot="beside"), use(anim="talk", dur=(20, 30)),
                       go(node="markets"), use(anim="talk", dur=(20, 30)), go(node="vicus_tuscus"),
                       wait(dur=(15, 25)))}, card="syrian")
    add("visitor", R + "citizen", "Visitor in the fora", sched(("06:30", "12:00", "look"), ("14:00", "19:00", "look")),
        {"look": loop(go(node="trajan_forum"), use(anim="idle", dur=(20, 40)),
                      go(node="trajan_forum"), use(anim="talk", dur=(10, 20)),
                      go(node="markets"), wander(radius=4, dur=(20, 30))),
         "shelter": shelter_at("trajan_forum")}, interrupts=[RAIN], card="plebs")
    add("market_seller", R + "freedman", "Shopkeeper in Trajan's Markets", sched(
        ("06:00", "12:30", "sell"), ("14:30", "18:30", "sell")),
        {"sell": loop(go(home="shop"), use({"home": "shop"}, anim="serve", dur=(30, 50)),
                      use(anim="talk", dur=(10, 20)))},
        home={"item": R + "trajan_markets", "slot": "shop"}, card="freedman")
    add("clerk", R + "freedman", "Clerk of the record office", sched(("07:00", "12:00", "records"), ("14:00", "16:30", "records")),
        {"records": loop(go(node="arx"), use(anim="talk", dur=(20, 30)), go(node="clivus_foot"),
                         use(anim="serve", dur=(15, 25)), go(node="curia"), wait(dur=(15, 25)))},
        card="tabularium_clerk")
    add("goose", R + "goose", "Sacred goose of Juno", sched(("05:00", "20:00", "peck")),
        {"peck": loop(wander(radius=4, dur=(15, 30)), use(anim="peck", dur=(15, 25)))}, card="geese")

    # --- the Velia and the building site ----------------------------------------------------
    add("mason", R + "builder", "Mason at the temple", sched(("06:00", "12:00", "build"), ("13:30", "18:00", "build")),
        {"build": loop(go(home="work"), use({"home": "work"}, anim="work_high", dur=(40, 60)),
                       use(anim="haul", dur=(10, 20)))},
        home={"item": R + "venus_roma", "slot": "work"}, card="mason")
    add("crane_walker", R + "builder", "Treadwheel walker", sched(("06:00", "12:00", "tread"), ("13:30", "18:00", "tread")),
        {"tread": loop(go(home="work"), use({"home": "work"}, anim="haul", dur=(40, 60)),
                       use(anim="idle", dur=(6, 12)))},
        home={"item": R + "r_crane", "slot": "work"}, card="treadwheel")
    add("bricklayer", R + "builder", "Bricklayer", sched(("06:00", "12:00", "lay"), ("13:30", "18:00", "lay")),
        {"lay": loop(go(node="venus_roma_site"), wander(radius=5, dur=(15, 25)), use(anim="work_high", dur=(30, 50)),
                     go(item=R + "r_scaffold", spot="beside", within=6), use(anim="carry_idle", dur=(10, 20)))},
        card="bricklayer")
    add("labourer", R + "enslaved", "Labourer at the site", sched(("06:00", "12:00", "haul"), ("13:30", "18:00", "haul")),
        {"haul": loop(go(node="venus_roma_site"), use(anim="work_low", dur=(30, 50)),
                      {"take": "rome.goods_bricks"}, go(node="arch_titus"), {"put": "rome.goods_bricks"},
                      go(node="via_sacra_velia"), wait(dur=(8, 14)))}, card="labourer")
    add("site_cart", R + "cart", "Ox cart for the temple", sched(("06:00", "17:00", "haul")),
        {"haul": loop(go(node="emporium"), wait(dur=(20, 30)), go(node="clivus_foot"),
                      go(node="venus_roma_site"), wait(dur=(20, 30)))},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}, card="site_cart")
    add("night_unloader", R + "enslaved", "Night gang at the site", sched(("19:00", "05:00", "unload")),
        {"unload": loop(go(item=R + "venus_roma", slot="work"), use(anim="work_low", dur=(40, 60)),
                        wander(radius=4, dur=(20, 30)))}, card="night_carts")
    add("passer", R + "citizen", "Passer-by on the Via Sacra", sched(("06:00", "12:00", "walk"), ("14:00", "19:30", "walk")),
        {"walk": loop(go(node="via_sacra_velia"), go(node="arch_titus"), use(anim="idle", dur=(10, 20)),
                      go(node="colossus"), use(anim="talk", dur=(10, 20)), go(node="meta_sudans"),
                      wait(dur=(10, 15))), "shelter": shelter_door(16)}, interrupts=[RAIN], card="plebs")
    add("water_carrier", R + "working_woman", "Water carrier", sched(("05:00", "10:00", "water"), ("16:00", "19:30", "water")),
        {"water": loop(go(home="fill"), use({"home": "fill"}, anim="carry_idle", dur=(10, 16)),
                       {"take": "rome.goods_water_jug"}, go(slot_kind="door", within=16),
                       {"put": "rome.goods_water_jug"})},
        home={"item": R + "r_lacus", "slot": "fill"}, card="fountain")
    add("meta_carrier", R + "working_woman", "Woman at the Meta Sudans", sched(("05:00", "10:00", "water"), ("16:00", "19:30", "water")),
        {"water": loop(go(home="fill"), use({"home": "fill"}, anim="carry_idle", dur=(10, 16)),
                       {"take": "rome.goods_water_jug"}, go(node="colossus"), {"put": "rome.goods_water_jug"})},
        home={"item": R + "meta_sudans", "slot": "fill"}, card="fountain")

    # --- the Palatine -----------------------------------------------------------------------
    add("guard", R + "praetorian", "Praetorian on guard", sched(("00:00", "24:00", "guard")),
        {"guard": loop(go(node="palatine_court"), use(anim="guard", dur=(60, 100)), go(node="palatine_west"),
                       use(anim="march", dur=(10, 15)), use(anim="guard", dur=(40, 60)))}, card="praetorian")
    add("horse_guard", R + "german_guard", "Horse guard", sched(("06:00", "20:00", "guard")),
        {"guard": loop(go(node="palatine_court"), use(anim="guard", dur=(60, 90)), wander(radius=5, dur=(20, 30)))},
        card="german_guard")
    add("courtier", R + "togatus", "Courtier", sched(("06:00", "12:00", "court"), ("14:00", "18:00", "court")),
        {"court": loop(go(node="palatine_court"), use(anim="talk", dur=(20, 30)), go(node="palatine_west"),
                       use(anim="gesture", dur=(10, 20)), wander(radius=4, dur=(20, 30)))}, card="courtier")
    add("palace_slave", R + "enslaved", "Palace servant", sched(("05:00", "12:00", "serve"), ("14:00", "20:00", "serve")),
        {"serve": loop(go(node="palatine_court"), use(anim="carry_idle", dur=(10, 20)),
                       {"take": "world.goods_firewood"}, go(node="palatine_west"), {"put": "world.goods_firewood"},
                       use(anim="work_low", dur=(20, 30)))}, card="enslaved")
    add("gardener", R + "farmer", "Gardener", sched(("05:30", "11:30", "garden"), ("15:00", "18:30", "garden")),
        {"garden": loop(wander(radius=5, dur=(20, 30)), use(anim="work_low", dur=(30, 50)),
                        use(anim="work_high", dur=(15, 25)))}, card="gardener")

    # --- the Circus -------------------------------------------------------------------------
    add("stable_hand", R + "enslaved", "Stable hand", sched(("05:00", "12:00", "stables"), ("14:00", "19:00", "stables")),
        {"stables": loop(go(node="circus_carceres"), use(anim="work_low", dur=(30, 50)),
                         {"take": "world.goods_sacks"}, wander(radius=4, dur=(15, 25)), {"put": "world.goods_sacks"})},
        card="stables")
    add("racehorse", R + "racehorse", "Racehorse", sched(("05:30", "18:30", "graze")),
        {"graze": loop(wander(radius=4, dur=(20, 40)), use(anim="idle", dur=(20, 40)))})
    add("chariot", R + "racing_chariot", "Team at exercise", sched(("07:00", "11:00", "exercise")),
        {"exercise": loop(go(node="circus_carceres"), wait(dur=(15, 25)), go(node="circus_stands"),
                          go(node="circus_carceres"))},
        locomotion={"mode": "walk", "speed": 1.4, "network": "circus", "turn_radius": 2}, card="factions")
    add("circus_trader", R + "freedman", "Seller under the Circus arcades", sched(
        ("06:30", "12:00", "sell"), ("13:00", "19:00", "sell")),
        {"sell": loop(go(node="circus_stands"), use(anim="serve", dur=(30, 50)), go(node="circus_carceres"),
                      use(anim="talk", dur=(15, 25)))}, card="freedman")
    add("race_fan", R + "citizen", "Race-goer", sched(("12:30", "18:30", "races")),
        {"races": loop(go(item=R + "circus_maximus", spot="beside"), use(anim="idle", dur=(60, 90)),
                       use(anim="talk", dur=(10, 20)), go(node="circus_stands"), wait(dur=(20, 40)))},
        card="factions")

    # --- the Colosseum valley ---------------------------------------------------------------
    add("valley_walker", R + "citizen", "Citizen in the valley", sched(("06:00", "12:00", "walk"), ("14:00", "19:30", "walk")),
        {"walk": loop(go(node="colosseum"), use(anim="idle", dur=(15, 25)), go(node="meta_sudans"),
                      use(anim="talk", dur=(10, 20)), go(node="ludus"), wander(radius=4, dur=(20, 30))),
         "shelter": shelter_door(16)}, interrupts=[RAIN], card="plebs")
    add("game_crowd", R + "citizen", "Spectator", sched(("12:30", "18:30", "watch")),
        {"watch": loop(go(item=R + "colosseum", spot="beside"), use(anim="idle", dur=(60, 100)),
                       go(node="colosseum"), use(anim="talk", dur=(15, 25)))}, card="amphitheatre_games")

    # --- the river port ---------------------------------------------------------------------
    add("docker", R + "docker", "Docker (saccarius)", sched(("05:00", "12:00", "unload"), ("13:30", "19:00", "unload")),
        {"unload": loop(go(item=R + "quay", slot="mooring", within=8), use(anim="carry_idle", dur=(8, 14)),
                        {"take": "rome.goods_grain_sack"}, go(item=R + "horrea_galbana", slot="door"),
                        {"put": "rome.goods_grain_sack"}, go(node="emporium"), wait(dur=(8, 14)))},
        card="docker")
    add("tally_clerk", R + "freedman", "Tally clerk", sched(("06:00", "12:00", "tally"), ("14:00", "18:00", "tally")),
        {"tally": loop(go(home="door"), use({"home": "door"}, anim="talk", dur=(30, 50)),
                       use(anim="serve", dur=(15, 25)))},
        home={"item": R + "horrea_galbana", "slot": "door"}, card="horrea_clerk")
    add("emporium_crane", R + "builder", "Crane crew at the wharf", sched(("05:30", "12:00", "lift"), ("13:30", "18:30", "lift")),
        {"lift": loop(go(home="work"), use({"home": "work"}, anim="haul", dur=(40, 60)), use(anim="idle", dur=(6, 10)))},
        home={"item": R + "r_crane", "slot": "work"}, card="treadwheel")
    add("dumper", R + "enslaved", "Sherd carrier on the mound", sched(("06:00", "12:00", "dump"), ("14:00", "18:00", "dump")),
        {"dump": loop(go(home="dump"), use({"home": "dump"}, anim="work_low", dur=(30, 50)),
                      use(anim="carry_idle", dur=(6, 12)))},
        home={"item": R + "testaccio", "slot": "dump"}, card="testaccio_work")
    add("warehouse_man", R + "enslaved", "Warehouse porter", sched(("05:30", "12:00", "store"), ("14:00", "18:30", "store")),
        {"store": loop(go(item=R + "r_horrea", slot="door", within=10), use(anim="carry_idle", dur=(10, 16)),
                       {"take": "rome.goods_oil_amphora"}, go(node="testaccio"), {"put": "rome.goods_oil_amphora"},
                       go(node="emporium"), wait(dur=(10, 20)))}, card="warehouse")
    add("hauler", R + "hauler", "Barge hauler", sched(("05:30", "12:00", "tow"), ("13:30", "18:30", "tow")),
        {"tow": loop(go(node="emporium"), use(anim="haul", dur=(30, 50)), go(node="pons_sublicius"),
                     use(anim="haul", dur=(30, 50)), wait(dur=(10, 20)))}, card="hauler")
    add("sailor", R + "egyptian_sailor", "Egyptian sailor", sched(("06:00", "18:00", "ashore")),
        {"ashore": loop(go(node="emporium"), use(anim="haul", dur=(20, 30)), go(node="testaccio"),
                        wander(radius=4, dur=(20, 30)), go(node="horrea_galbana"), wait(dur=(15, 25)))},
        card="egypt")
    add("merchant", R + "syrian_merchant", "Merchant at the wharf", sched(("06:00", "12:00", "trade"), ("14:00", "18:00", "trade")),
        {"trade": loop(go(node="emporium"), use(anim="talk", dur=(30, 50)), go(node="horrea_galbana"),
                       use(anim="talk", dur=(15, 25)))}, card="syrian")
    add("gull", R + "gull", "Gull", sched(("04:30", "20:30", "fly")),
        {"fly": loop(wander(radius=14, dur=(20, 40)), use(anim="idle", dur=(10, 20)))})
    add("swallow", R + "swallow", "Swallow", sched(("05:00", "19:30", "fly")),
        {"fly": loop(wander(radius=16, dur=(20, 40)), use(anim="idle", dur=(4, 8)))}, card="swallows")
    add("ox_team", R + "ox", "Towing ox", sched(("05:30", "18:30", "tow")),
        {"tow": loop(go(node="pons_sublicius"), use(anim="idle", dur=(20, 30)), go(node="emporium"),
                     use(anim="graze", dur=(20, 30)))})

    # --- the Forum Boarium, the Velabrum, the island ---------------------------------------
    add("stall_keeper", R + "working_woman", "Stall keeper", sched(("05:30", "12:30", "sell"), ("14:00", "18:30", "sell")),
        {"sell": loop(go(home="sell"), use({"home": "sell"}, anim="serve", dur=(30, 50), effect="open_shutters"),
                      use(anim="idle", dur=(6, 12)), use(anim="serve", dur=(20, 30)))},
        home={"item": R + "r_stall", "slot": "sell"}, card="seller")
    add("drover", R + "farmer", "Cattle drover", sched(("05:00", "11:30", "drive"), ("14:00", "17:30", "drive")),
        {"drive": loop({"follow": {"actor": R + "ox"}, "dur": [40, 60], "spacing": 1.0},
                       go(node="forum_boarium"), use(anim="work_low", dur=(15, 25)))}, card="cattle_market")
    add("ox", R + "ox", "Ox for sale", sched(("05:00", "17:30", "stand")),
        {"stand": loop(wander(radius=3, dur=(20, 30)), use(anim="graze", dur=(30, 50)))})
    add("shopper", R + "citizen", "Shopper", sched(("05:30", "12:00", "shop"), ("14:00", "19:00", "shop")),
        {"shop": loop(go(node="forum_boarium"), use(anim="talk", dur=(10, 20)),
                      go(item=R + "r_stall", slot="buy", within=10), wait(dur=(8, 14)),
                      go(node="forum_holitorium"), wander(radius=4, dur=(15, 25))),
         "shelter": shelter_door(12)}, interrupts=[RAIN], card="plebs")
    add("sick", R + "citizen", "Sick man in the portico", sched(("00:00", "24:00", "rest")),
        {"rest": loop(go(home="sleep"), use({"home": "sleep"}, anim="sit", dur=(120, 200)))},
        home={"item": R + "tiber_island", "slot": "sleep"}, card="aesculapius")
    add("pilgrim", R + "matron", "Pilgrim to Aesculapius", sched(("06:00", "12:00", "pray"), ("14:00", "18:30", "pray")),
        {"pray": loop(go(node="tiber_island_east"), use(anim="idle", dur=(30, 50)), use(anim="talk", dur=(10, 20)),
                      go(node="pons_aemilius"), wait(dur=(10, 20)))}, card="aesculapius")

    # --- trades in the quarters -------------------------------------------------------------
    add("baker", R + "baker", "Baker", sched(("02:00", "12:00", "bake"), ("14:00", "17:00", "bake")),
        {"bake": loop(go(home="work"), use({"home": "work"}, anim="stir", dur=(40, 60)),
                      use(anim="carry_idle", dur=(8, 14)))},
        home={"item": R + "r_bakery", "slot": "work"}, card="baker")
    add("mill_donkey", R + "donkey", "Mill donkey", sched(("02:00", "11:00", "turn")),
        {"turn": loop(go(item=R + "r_bakery", spot="beside"), use(anim="idle", dur=(40, 60)),
                      use(anim="graze", dur=(10, 15)))}, card="mill_donkey")
    add("fuller", R + "fuller", "Fuller", sched(("06:00", "12:00", "tread"), ("13:30", "18:00", "tread")),
        {"tread": loop(go(home="work"), use({"home": "work"}, anim="work_low", dur=(40, 60)),
                       use(anim="idle", dur=(6, 10)))},
        home={"item": R + "r_fullonica", "slot": "work"}, card="fuller")
    add("dyer", R + "fuller", "Dyer", sched(("06:00", "12:00", "dye"), ("13:30", "18:00", "dye")),
        {"dye": loop(go(home="work"), use({"home": "work"}, anim="work_low", dur=(40, 60)),
                     use(anim="idle", dur=(6, 10)))},
        home={"item": R + "r_dyeworks", "slot": "work"}, card="dyer")
    add("glassblower", R + "glassblower", "Glassblower", sched(("06:00", "12:00", "blow"), ("13:30", "18:00", "blow")),
        {"blow": loop(go(home="work"), use({"home": "work"}, anim="play", dur=(40, 60)),
                      use(anim="idle", dur=(8, 12)))},
        home={"item": R + "r_glass", "slot": "work"}, card="glass")
    add("smith", R + "smith", "Smith", sched(("05:30", "12:00", "forge"), ("13:30", "18:30", "forge")),
        {"forge": loop(go(home="work"), use({"home": "work"}, anim="work_high", dur=(40, 60)),
                       use(anim="idle", dur=(6, 10)))},
        home={"item": R + "r_smithy", "slot": "work"}, card="smith")
    add("shopkeeper", R + "freedman", "Shopkeeper", sched(("06:00", "12:00", "shop"), ("14:00", "19:30", "shop")),
        {"shop": loop(go(home="sell"), use({"home": "sell"}, anim="serve", dur=(30, 50), effect="open_shutters"),
                      use(anim="talk", dur=(15, 25)))},
        home={"item": R + "r_taberna", "slot": "sell"}, card="taberna")
    add("insula_shop", R + "working_woman", "Woman at a shop counter", sched(("06:00", "12:00", "shop"), ("14:00", "19:00", "shop")),
        {"shop": loop(go(home="sell"), use({"home": "sell"}, anim="serve", dur=(30, 50), effect="open_shutters"),
                      use(anim="idle", dur=(6, 12)))},
        home={"item": R + "r_insula", "slot": "sell"}, card="taberna")
    add("counter_keeper", R + "freedman", "Hot-food seller", sched(("06:00", "22:00", "serve")),
        {"serve": loop(go(home="serve"), use({"home": "serve"}, anim="serve", dur=(30, 50)),
                       use(anim="talk", dur=(10, 20)))},
        home={"item": R + "r_thermopolium", "slot": "serve"}, card="thermopolium")
    add("weaver", R + "working_woman", "Weaver", sched(("05:30", "12:00", "weave"), ("14:00", "18:00", "weave")),
        {"weave": loop(go(home="sell"), use({"home": "sell"}, anim="serve", dur=(40, 60)),
                       use(anim="carry_idle", dur=(6, 10)))},
        home={"item": R + "r_insula_low", "slot": "sell"}, card="weaver")
    add("stoker", R + "enslaved", "Bath stoker", sched(("04:00", "12:00", "stoke"), ("12:00", "19:00", "stoke")),
        {"stoke": loop(go(home="door"), use({"home": "door"}, anim="work_low", dur=(30, 50)),
                       {"take": "world.goods_firewood"}, wander(radius=3, dur=(10, 15)),
                       {"put": "world.goods_firewood"})},
        home={"item": R + "r_bath_small", "slot": "door"}, card="stoker")
    add("bather", R + "bather", "Bather", sched(("12:30", "18:30", "bathe")),
        {"bathe": loop(go(item=R + "r_bath_small", spot="beside", within=12), {"enter": {"here": True}, "dur": [40, 70]},
                       wander(radius=6, dur=(20, 40)), use(anim="idle", dur=(15, 25)))}, card="baths")
    add("agrippa_bather", R + "bather", "Bather at Agrippa's baths", sched(("12:30", "18:30", "bathe")),
        {"bathe": loop(go(item=R + "agrippa_baths", spot="beside"), wait(dur=(40, 70)), go(node="stagnum"),
                       use(anim="idle", dur=(20, 30)), wander(radius=5, dur=(20, 30)))}, card="baths")
    add("exerciser", R + "citizen", "Man at exercise", sched(("07:00", "12:30", "exercise"), ("14:00", "17:30", "exercise")),
        {"exercise": loop(go(node="oppian"), wander(radius=6, dur=(20, 40)), use(anim="talk", dur=(10, 20)),
                          use(anim="sit", dur=(20, 30)))}, card="baths")
    add("vigil", R + "vigil", "Vigil of the watch", sched(("19:00", "06:00", "round"), ("06:00", "19:00", "post")),
        {"round": loop(wander(radius=12, dur=(40, 70)), go(slot_kind="door", within=16), use(anim="idle", dur=(10, 20))),
         "post": loop(go(item=R + "r_vigiles", spot="beside"), use(anim="idle", dur=(60, 100)),
                      wander(radius=6, dur=(20, 30)))}, card="vigiles")

    # --- the residential quarters -----------------------------------------------------------
    add("housewife", R + "working_woman", "Woman of the house", sched(
        ("05:00", "10:00", "water"), ("10:00", "17:00", "errands"), ("17:00", "20:30", "water")),
        {"water": loop({"pick": [
            {"weight": 1, "steps": [go(item=R + "r_lacus", slot="fill", within=18), use(anim="carry_idle", dur=(3, 5)),
                                    {"take": "rome.goods_water_jug"}, go(slot_kind="door", within=10),
                                    {"put": "rome.goods_water_jug"}]},
            {"weight": 2, "steps": [go(slot_kind="door", within=10), use(anim="carry_idle", dur=(20, 40)),
                                    wander(radius=5, dur=(20, 30))]}]}),
         "errands": loop({"pick": [
             {"weight": 3, "steps": [go(slot_kind="door", within=12), wait(dur=(30, 50)), wander(radius=6, dur=(20, 30))]},
             {"weight": 1, "steps": [go(item=R + "r_compitum", slot="pray", within=14), use(anim="idle", dur=(4, 6))]}]}),
         "shelter": shelter_door()}, interrupts=[RAIN], card="women")
    add("townsman", R + "citizen", "Neighbour", sched(("05:30", "12:00", "errands"), ("13:30", "20:00", "errands")),
        {"errands": loop(go(slot_kind="door", within=12), wait(dur=(10, 20)), wander(radius=8, dur=(30, 50)),
                         use(anim="talk", dur=(10, 20))), "shelter": shelter_door()}, interrupts=[RAIN], card="plebs")
    add("freedwoman", R + "freedman", "Freed shopkeeper on an errand", sched(("06:00", "12:00", "errands"), ("14:00", "19:00", "errands")),
        {"errands": loop(go(slot_kind="door", within=12), use(anim="talk", dur=(10, 20)), wander(radius=6, dur=(20, 40))),
         "shelter": shelter_door()}, interrupts=[RAIN], card="freedman")
    add("errand_slave", R + "enslaved", "Enslaved worker", sched(("05:00", "12:00", "errands"), ("13:30", "20:00", "errands")),
        {"errands": loop({"pick": [
            {"weight": 2, "steps": [go(slot_kind="door", within=12), {"take": "world.goods_firewood"},
                                    wander(radius=8, dur=(20, 40)), go(slot_kind="door", within=12),
                                    {"put": "world.goods_firewood"}]},
            {"weight": 1, "steps": [go(item=R + "r_lacus", slot="fill", within=18), use(anim="carry_idle", dur=(4, 6)),
                                    {"take": "rome.goods_water_jug"}, go(slot_kind="door", within=10),
                                    {"put": "rome.goods_water_jug"}]}]}),
         "shelter": shelter_door()}, interrupts=[RAIN], card="enslaved")
    add("child", R + "child", "Child", sched(("06:30", "19:30", "play")),
        {"play": loop({"pick": [
            {"weight": 3, "steps": [wander(radius=6, dur=(20, 40)), use(anim="run", dur=(6, 10))]},
            {"weight": 2, "steps": [wander(radius=3, dur=(10, 15)), use(anim="kneel", dur=(20, 30))]}]}),
         "shelter": shelter_door()}, interrupts=[RAIN], card="children")
    add("patron", R + "senator", "Patron at his door", sched(("04:30", "07:30", "receive"), ("16:00", "21:00", "dinner")),
        {"receive": once(go(item=R + "r_domus", slot="door", within=10), use(anim="talk", dur=(80, 120)),
                         use(anim="gesture", dur=(20, 30))),
         "dinner": home_for("21:00", 10)}, card="salutatio")
    add("litter", R + "litter", "Litter with its bearers", sched(("06:00", "11:00", "carry")),
        {"carry": loop(go(item=R + "r_domus", slot="door", within=16), wait(dur=(20, 30)), go(node="forum"),
                       wait(dur=(30, 50)), go(node="caelian"))},
        locomotion={"mode": "walk", "speed": 0.7, "network": "streets", "turn_radius": 1}, card="litter")
    add("reveller", R + "citizen", "Late diner with a lamp", sched(("19:00", "01:00", "home")),
        {"home": loop(go(item=R + "r_thermopolium", spot="beside", within=14), use(anim="talk", dur=(20, 40)),
                      wander(radius=8, dur=(30, 50)), go(slot_kind="door", within=12), wait(dur=(10, 20)))},
        card="popina")
    add("dog", R + "dog", "Dog", sched(("00:00", "24:00", "roam")),
        {"roam": loop(wander(radius=8, dur=(20, 40)), use(anim="sleep", dur=(30, 60)))}, card="dogs")
    add("cat", R + "cat", "Cat", sched(("00:00", "24:00", "prowl")),
        {"prowl": loop(wander(radius=5, dur=(20, 40)), use(anim="sleep", dur=(40, 80)))}, card="cats")
    add("hen", R + "hen", "Hen", sched(("05:00", "19:30", "peck")),
        {"peck": loop(wander(radius=3, dur=(10, 20)), use(anim="peck", dur=(10, 20)))})
    add("goat", R + "goat", "Goat", sched(("05:00", "19:30", "graze")),
        {"graze": loop(wander(radius=6, dur=(20, 40)), use(anim="graze", dur=(10, 25)))})
    add("sheep", R + "sheep", "Sheep", sched(("05:00", "19:30", "graze")),
        {"graze": loop(wander(radius=6, dur=(20, 40)), use(anim="graze", dur=(10, 25)))})
    add("pig", R + "pig", "Pig", sched(("05:00", "19:00", "root")),
        {"root": loop(wander(radius=3, dur=(15, 25)), use(anim="graze", dur=(20, 30)))})
    add("aquarius", R + "enslaved", "Public slave of the water office", sched(("06:00", "12:00", "channel"), ("14:00", "17:00", "channel")),
        {"channel": loop(go(node="aqueduct"), use(anim="work_low", dur=(30, 50)), go(node="caelian"),
                         use(anim="carry_idle", dur=(10, 20)), go(node="player_domus"), wait(dur=(10, 20)))},
        card="aquarius")
    add("jewish_trader", R + "jewish_trader", "Trader of the Transtiberim community", sched(
        ("06:30", "12:00", "trade"), ("14:00", "18:00", "trade")),
        {"trade": loop(go(item=R + "synagogue", spot="beside"), use(anim="talk", dur=(20, 30)), go(node="transtiberim"),
                       use(anim="talk", dur=(20, 30)), go(node="pons_aemilius"), wait(dur=(10, 20)))},
        card="synagogue_community")
    add("gaul", R + "gaul", "Gaulish trader", sched(("07:00", "18:00", "trade")),
        {"trade": loop(go(node="transtiberim"), use(anim="idle", dur=(20, 30)), go(node="forum_boarium"),
                       wait(dur=(20, 30)))}, card="gaul")
    add("rider", R + "moorish_horseman", "Moorish horseman", sched(("07:00", "11:00", "ride"), ("15:00", "18:00", "ride")),
        {"ride": loop(go(node="via_lata"), wander(radius=8, dur=(40, 70)), go(node="campus_south"), wait(dur=(15, 25)))},
        card="moor")
    add("theatre_goer", R + "citizen", "Theatre-goer", sched(("13:30", "18:00", "watch")),
        {"watch": loop(go(node="marcellus"), use(anim="sit", dur=(50, 80)), go(node="octavia"),
                       use(anim="talk", dur=(15, 25)))}, card="theatre")
    add("visitor_campus", R + "citizen", "Visitor in the Campus Martius", sched(("06:30", "12:00", "look"), ("14:00", "19:00", "look")),
        {"look": loop(go(node="pantheon"), use(anim="idle", dur=(20, 40)), go(node="saepta"),
                      use(anim="talk", dur=(10, 20)), go(node="octavia"), wander(radius=5, dur=(20, 30))),
         "shelter": shelter_at("saepta")}, interrupts=[RAIN], card="plebs")

    # --- the countryside, the roads ---------------------------------------------------------
    add("farmer", R + "farmer", "Farmer", sched(("05:00", "11:30", "field"), ("15:00", "19:00", "field")),
        {"field": loop({"pick": [
            {"weight": 4, "steps": [wander(radius=6, dur=(20, 40)), use(anim="work_low", dur=(30, 50))]},
            {"weight": 1, "steps": [go(item=R + "r_villa_farm", slot="door", within=20), use(anim="idle", dur=(10, 15))]}]})},
        card="farmer")
    add("vinedresser", R + "farmer", "Vine-dresser", sched(("05:30", "11:30", "vines"), ("15:00", "18:30", "vines")),
        {"vines": loop(wander(radius=6, dur=(20, 40)), use(anim="work_high", dur=(30, 50)),
                       use(anim="work_low", dur=(15, 25)))}, card="vinedresser")
    add("villa_steward", R + "farmer", "Steward of the villa", sched(("06:00", "12:00", "estate"), ("14:00", "18:00", "estate")),
        {"estate": loop(go(home="work"), use({"home": "work"}, anim="work_low", dur=(30, 50)), wander(radius=6, dur=(20, 30)))},
        home={"item": R + "suburban_villa", "slot": "work"}, card="villa")
    add("shepherd", R + "shepherd", "Shepherd", sched(("05:00", "19:00", "herd")),
        {"herd": loop(wander(radius=10, dur=(40, 70)), use(anim="idle", dur=(10, 20)), use(anim="run", dur=(4, 8)))},
        card="shepherd")
    add("mourner", R + "matron", "Mourner at a tomb", sched(("06:00", "11:00", "tomb"), ("15:00", "18:30", "tomb")),
        {"tomb": loop(go(home="mourn"), use({"home": "mourn"}, anim="idle", dur=(40, 70)), wander(radius=4, dur=(15, 25)))},
        home={"item": R + "r_tomb", "slot": "mourn"}, card="tombs")
    add("traveller", "world.traveller", "Traveller on the Via Appia", sched(("05:30", "18:30", "travel")),
        {"travel": loop(go(node="mutatio"), use(anim="sit", dur=(20, 40)), go(node="appia_tombs"),
                        go(node="porta_capena"), wait(dur=(15, 25)))}, card="cursus_publicus")
    add("carriage", R + "carriage", "Travelling carriage", sched(("06:00", "17:00", "travel")),
        {"travel": loop(go(node="mutatio"), wait(dur=(30, 50)), go(node="appia_tombs"), go(node="porta_capena"),
                        wait(dur=(40, 60)))},
        locomotion={"mode": "walk", "speed": 0.8, "network": "roads", "turn_radius": 2}, card="cursus_publicus")
    add("muleteer", "world.muleteer", "Muleteer", sched(("05:30", "18:00", "lead")),
        {"lead": loop({"follow": {"actor": R + "mule"}, "dur": [60, 90], "spacing": 0.8}, use(anim="gesture", dur=(6, 10)))},
        card="mules")
    add("mule", R + "mule", "Pack mule", sched(("05:30", "18:00", "walk")),
        {"walk": loop(go(node="mutatio"), use(anim="graze", dur=(20, 30)), go(node="porta_capena"),
                      use(anim="idle", dur=(20, 30)))}, card="mules")
    add("grain_mule", R + "mule", "Mule with grain sacks", sched(("04:00", "18:00", "carry")),
        {"carry": loop(go(item=R + "horrea_galbana", slot="door"), use(anim="idle", dur=(10, 20)),
                       go(item=R + "r_bakery", slot="work"), use(anim="idle", dur=(10, 20)))}, card="mules")
    add("waiting_cart", R + "cart", "Cart waiting for dusk", sched(("06:00", "18:30", "wait")),
        {"wait": loop(go(node="porta_capena"), wait(dur=(80, 140)), go(node="appia_tombs"), wait(dur=(60, 100)))},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}, card="night_carts")
    add("night_cart", R + "cart", "Night cart", sched(("18:30", "05:00", "haul")),
        {"haul": loop(go(node="porta_capena"), go(node="colosseum"), go(node="venus_roma_site"), wait(dur=(30, 50)),
                      go(node="porta_capena"), go(node="appia_tombs"), wait(dur=(20, 30)))},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}, card="night_carts")
    add("carter", R + "carter", "Carter", sched(("18:30", "05:00", "drive")),
        {"drive": loop({"follow": {"actor": R + "cart"}, "dur": [60, 90], "spacing": 0.8}, use(anim="idle", dur=(10, 20)))},
        card="night_carts")
    add("fisher", "world.fisher", "Fisherman", sched(("04:30", "11:00", "fish"), ("15:00", "18:30", "fish")),
        {"fish": loop(go(item=R + "quay", slot="mooring", within=12), use(anim="haul", dur=(20, 30)),
                      {"take": "rome.goods_fish"}, go(node="forum_boarium"), {"put": "rome.goods_fish"},
                      use(anim="sit", dur=(20, 30)))}, card="fish_market")

    # --- the camp ----------------------------------------------------------------------------
    add("camp_guard", R + "praetorian", "Praetorian at the gate", sched(("00:00", "24:00", "guard")),
        {"guard": loop(go(home="guard"), use({"home": "guard"}, anim="guard", dur=(60, 120)), use(anim="march", dur=(8, 12)))},
        home={"item": R + "castra_praetoria", "slot": "guard"}, card="praetorian")
    add("recruit", R + "praetorian", "Praetorian at drill", sched(("06:00", "11:00", "drill"), ("15:00", "18:00", "drill")),
        {"drill": loop(go(home="drill"), use({"home": "drill"}, anim="march", dur=(30, 50)), use(anim="guard", dur=(10, 20)))},
        home={"item": R + "castra_praetoria", "slot": "drill"}, card="praetorian")
    add("veteran", R + "legionary", "Legionary on leave", sched(("07:00", "12:00", "walk"), ("14:00", "18:00", "walk")),
        {"walk": loop(go(node="castra"), use(anim="idle", dur=(20, 30)), go(node="esquiline"), wander(radius=6, dur=(20, 40)))},
        card="legions")
    add("auxiliary", R + "auxiliary", "Auxiliary on an errand", sched(("07:00", "17:00", "walk")),
        {"walk": loop(go(node="castra"), use(anim="guard", dur=(20, 30)), go(node="esquiline"), wait(dur=(20, 30)))},
        card="legions")

    # --- the festival ------------------------------------------------------------------------
    add("reveller_day", R + "citizen", "Festival-goer", sched(("05:00", "22:30", "festival")),
        {"festival": loop(go(node="forum"), use(anim="talk", dur=(20, 40)), go(node="via_sacra_velia"),
                          use(anim="idle", dur=(20, 30)), go(node="vesta"), wander(radius=5, dur=(20, 40)))},
        card="parilia")
    add("festival_woman", R + "matron", "Woman at the festival", sched(("05:30", "22:00", "festival")),
        {"festival": loop(go(node="vesta"), use(anim="idle", dur=(20, 30)), go(node="via_sacra_velia"),
                          use(anim="talk", dur=(20, 30)), wander(radius=5, dur=(20, 30)))}, card="parilia")
    add("youth", R + "citizen", "Young man for the fires", sched(("16:00", "23:30", "fires")),
        {"fires": loop(wander(radius=6, dur=(30, 50)), use(anim="talk", dur=(20, 30)), use(anim="sit", dur=(10, 20)))},
        card="parilia")
    add("feaster", R + "citizen", "Neighbour feasting in the street", sched(("17:30", "23:30", "feast")),
        {"feast": loop(go(slot_kind="door", within=10), use(anim="sit", dur=(40, 70)), use(anim="talk", dur=(20, 30)),
                       wander(radius=5, dur=(20, 30)))}, card="parilia")
    add("feast_woman", R + "working_woman", "Woman bringing food to the street", sched(("17:30", "23:00", "feast")),
        {"feast": loop(go(slot_kind="door", within=10), {"take": R + "goods_bread"}, wander(radius=5, dur=(20, 30)),
                       {"put": R + "goods_bread"}, use(anim="serve", dur=(20, 30)))}, card="parilia")
    return X


def groups() -> list[dict]:
    return [
        {"id": "parilia_procession", "leader": {"actor": R + "lictor"}, "members": [
            {"actor": R + "lictor", "count": 5}, {"actor": R + "hadrian", "count": 1},
            {"actor": R + "sabina", "count": 1}, {"actor": R + "flamen", "count": 3},
            {"actor": R + "vestalis_maxima", "count": 1}, {"actor": R + "vestal", "count": 2},
            {"actor": R + "musician", "count": 3}, {"actor": R + "senator", "count": 6},
            {"actor": R + "togatus", "count": 6}, {"actor": R + "praetorian", "count": 4},
            {"actor": R + "ox", "count": 1}], "formation": {"kind": "pairs", "spacing": 0.9}},
        {"id": "pompa_circensis", "leader": {"actor": R + "togatus"}, "members": [
            {"actor": R + "musician", "count": 3}, {"actor": R + "racing_chariot", "count": 4},
            {"actor": R + "diocles", "count": 1}, {"actor": R + "flamen", "count": 2},
            {"actor": R + "togatus", "count": 4}, {"role": "child", "count": 4}],
         "formation": {"kind": "pairs", "spacing": 1.0}},
        {"id": "senate_arrival", "leader": {"actor": R + "senator"}, "members": [
            {"role": "lictor", "count": 2}, {"role": "senator", "count": 5}, {"role": "client", "count": 6}],
         "formation": {"kind": "cluster", "radius": 2}},
        {"id": "salutatio_queue", "leader": {"role": "patron"}, "members": [{"role": "client", "count": 6}],
         "formation": {"kind": "line", "spacing": 0.9}},
        {"id": "shepherds_flock", "leader": {"role": "shepherd"}, "members": [
            {"actor": R + "sheep", "count": 8}, {"actor": R + "goat", "count": 2},
            {"actor": R + "dog_molossian", "count": 1}], "formation": {"kind": "cluster", "radius": 3}},
        {"id": "funeral", "leader": {"actor": R + "musician"}, "members": [
            {"actor": R + "musician", "count": 2}, {"role": "mourner", "count": 4},
            {"actor": R + "togatus", "count": 4}, {"role": "townsman", "count": 3}],
         "formation": {"kind": "pairs", "spacing": 0.9}},
        {"id": "wedding", "leader": {"actor": R + "musician"}, "members": [
            {"actor": R + "matron", "count": 3}, {"role": "townsman", "count": 4}, {"role": "child", "count": 3},
            {"actor": R + "togatus", "count": 2}], "formation": {"kind": "cluster", "radius": 2}},
        {"id": "vigiles_round", "leader": {"actor": R + "flavius_valens"}, "members": [
            {"role": "vigil", "count": 4}], "formation": {"kind": "line", "spacing": 1.2}},
        {"id": "guard_relief", "leader": {"actor": R + "praetorian"}, "members": [
            {"role": "guard", "count": 6}, {"actor": R + "musician", "count": 1}],
         "formation": {"kind": "pairs", "spacing": 0.8}},
        {"id": "vestals_walk", "leader": {"role": "lictor"}, "members": [
            {"actor": R + "vestalis_maxima", "count": 1}, {"role": "vestal", "count": 2}],
         "formation": {"kind": "line", "spacing": 1.0}},
        {"id": "imperial_party", "leader": {"actor": R + "hadrian"}, "members": [
            {"actor": R + "antinous", "count": 1}, {"role": "lictor", "count": 2},
            {"actor": R + "german_guard", "count": 3}, {"actor": R + "togatus", "count": 2}],
         "formation": {"kind": "cluster", "radius": 2}},
    ]


def quarter(w, c, ch, s, f=4, night=4, dog=1, cat=1, hen=0) -> list[dict]:
    """A residential quarter's everyday people (per chunk-sized share at density 1)."""
    out = [pop("housewife", "houses", w), pop("townsman", "day", c), pop("child", "children", ch),
           pop("errand_slave", "work", s), pop("freedwoman", "day", f), pop("reveller", "evening", night),
           pop("vigil", "night", 3), pop("dog", "always", dog), pop("cat", "always", cat)]
    if hen:
        out.append(pop("hen", "day", hen))
    return out


def shops(market="market") -> list[dict]:
    return [per("shopkeeper", "r_taberna", 1, market), per("counter_keeper", "r_thermopolium", 1, "evening_shop")]


def districts() -> list[dict]:
    W = WORKDAY
    return [
        {"id": "forum", "area": "centre", "populations": [
            pop("forum_crowd", "forum", 34), pop("client", "forum", 10), pop("senator", "day", 4),
            pop("lictor", "day", 4), pop("matron", "day", 8), pop("attendant", "day", 6),
            per("advocate", "julia", 2, "morning", when=W), per("gamester", "julia", 1, "day"),
            per("orator", "rostra", 1, "morning", when=W), per("schoolmaster", "forum_square", 1, "morning"),
            pop("pupil", "children", 6), per("seller", "aemilia", 3, "market"), pop("porter", "work", 8),
            pop("vestal", "always", 3), pop("flamen", "day", 3), pop("soldier", "watch", 4),
            pop("pigeon", "birds", 6), pop("greek", "day", 2), pop("syrian", "day", 2), pop("night_cart", "night", 1),
            pop("reveller_day", "festival", 24, when=FEAST), pop("festival_woman", "festival", 10, when=FEAST)]},
        {"id": "fora", "area": "centre", "populations": [
            pop("visitor", "forum", 34), pop("client", "forum", 6), pop("matron", "day", 6),
            pop("attendant", "day", 4), pop("greek", "day", 6), pop("syrian", "day", 3), pop("porter", "work", 6),
            pop("child", "children", 4), pop("soldier", "watch", 2), pop("pigeon", "birds", 6),
            pop("reveller_day", "festival", 10, when=FEAST)]},
        {"id": "markets", "area": "wild", "populations": [per("market_seller", "trajan_markets", 3, "market")]},
        {"id": "capitol", "area": "town", "populations": [
            per("temple_priest", "capitolium", 1, "morning"), pop("flamen", "day", 6),
            pop("worshipper", "day", 26), pop("clerk", "day", 6), pop("matron", "day", 4),
            pop("soldier", "watch", 3), pop("goose", "day", 4), pop("pigeon", "birds", 4),
            pop("reveller_day", "festival", 8, when=FEAST)]},
        {"id": "velia", "area": "town", "populations": [
            per("mason", "venus_roma", 2, "work", when=W), per("crane_walker", "r_crane", 1, "work", when=W),
            pop("bricklayer", "work", 10, when=W), pop("labourer", "work", 12, when=W),
            pop("site_cart", "work", 2, when=W), pop("night_unloader", "night", 6), pop("night_cart", "night", 2),
            pop("carter", "night", 2),
            pop("passer", "day", 18), pop("soldier", "watch", 2), pop("pigeon", "birds", 3),
            pop("reveller_day", "festival", 24, when=FEAST), pop("festival_woman", "festival", 8, when=FEAST)]},
        {"id": "colosseum", "area": "town", "populations": [
            pop("valley_walker", "day", 32), per("meta_carrier", "meta_sudans", 1, "always"),
            pop("matron", "day", 4), pop("child", "children", 4), pop("pigeon", "birds", 4),
            pop("game_crowd", "afternoon", 20, when={"days": GAMES}), pop("night_cart", "night", 2),
            pop("reveller_day", "festival", 8, when=FEAST)]},
        {"id": "palatine", "area": "town", "populations": [
            pop("guard", "always", 6), pop("horse_guard", "day", 4), pop("courtier", "day", 12),
            pop("palace_slave", "work", 14), pop("gardener", "fields", 6), pop("attendant", "day", 3),
            pop("cat", "always", 1), pop("pigeon", "birds", 3)]},
        {"id": "circus", "area": "town", "populations": [
            pop("stable_hand", "work", 12), pop("racehorse", "day", 6), pop("chariot", "morning", 4),
            pop("circus_trader", "market", 10), pop("valley_walker", "day", 14),
            pop("race_fan", "afternoon", 24, when={"days": RACES, "not_festival": "parilia"}),
            pop("race_fan", "afternoon", 24, when=FEAST), pop("dog", "always", 1)]},
        {"id": "velabrum", "area": "town", "populations": quarter(10, 8, 5, 6) + shops() + [
            per("baker", "r_bakery", 1, "dawn_work"), per("mill_donkey", "r_bakery", 1, "dawn_work"),
            per("fuller", "r_fullonica", 2, "work"), per("insula_shop", "r_insula", 1, "market"),
            pop("syrian", "day", 2), pop("shopper", "market", 6), pop("night_cart", "night", 2),
            pop("carter", "night", 2),
            pop("feaster", "parilia_night", 10, when=FEAST), pop("feast_woman", "parilia_night", 4, when=FEAST)]},
        {"id": "boarium", "area": "centre", "populations": [
            per("stall_keeper", "r_stall", 1, "market"), pop("shopper", "market", 34),
            per("hercules_priest", "ara_maxima", 1, "morning"), pop("drover", "work", 6), pop("ox", "work", 8),
            pop("porter", "work", 6), pop("fisher", "harbour", 6), pop("gaul", "day", 2),
            pop("jewish_trader", "day", 2), pop("child", "children", 4), pop("cat", "always", 2)] + shops() + [
            per("insula_shop", "r_insula", 1, "market"), pop("reveller_day", "festival", 10, when=FEAST),
            pop("night_cart", "night", 2), pop("carter", "night", 2),
            pop("youth", "parilia_night", 10, when=FEAST), pop("feaster", "parilia_night", 8, when=FEAST)]},
        {"id": "island", "area": "town", "populations": [
            per("sick", "tiber_island", 2, "always"), pop("pilgrim", "day", 24), pop("townsman", "day", 6),
            per("counter_keeper", "r_thermopolium", 1, "evening_shop"), pop("cat", "always", 2)]},
        {"id": "emporium", "area": "centre", "populations": [
            pop("docker", "harbour", 26), per("tally_clerk", "horrea_galbana", 1, "work"),
            per("emporium_crane", "r_crane", 1, "work"), per("dumper", "testaccio", 1, "work"),
            pop("warehouse_man", "work", 12), pop("hauler", "harbour", 10), pop("sailor", "day", 6),
            pop("merchant", "day", 5), pop("ox_team", "harbour", 4), pop("gull", "birds", 6), pop("cat", "always", 1),
            pop("night_cart", "night", 2), pop("carter", "night", 2)]},
        {"id": "river", "area": "sea", "populations": [
            pop("gull", "birds", 14), pop("swallow", "birds", 14)]},
        {"id": "campus", "area": "town", "populations": quarter(9, 6, 4, 4, 2, 3) + shops() + [
            per("insula_shop", "r_insula", 1, "market"), per("stall_keeper", "r_stall", 1, "market"),
            per("water_carrier", "r_lacus", 1, "houses"), per("baker", "r_bakery", 1, "dawn_work"),
            per("smith", "r_smithy", 1, "work"), per("fuller", "r_fullonica", 1, "work"),
            per("vigil", "r_vigiles", 6, "always"),
            pop("visitor_campus", "day", 10), pop("agrippa_bather", "baths", 6), pop("theatre_goer", "afternoon", 4),
            pop("rider", "day", 1), pop("pigeon", "birds", 3), pop("patron", "salutatio", 1),
            pop("client", "salutatio", 3), pop("litter", "morning", 1),
            pop("feaster", "parilia_night", 6, when=FEAST), pop("feast_woman", "parilia_night", 2, when=FEAST)]},
        {"id": "subura", "area": "centre", "populations": quarter(14, 12, 8, 8, 4, 8, 2, 2) + shops() + [
            per("insula_shop", "r_insula", 1, "market"), pop("porter", "work", 6), pop("shopper", "market", 8),
            pop("night_cart", "night", 3), pop("carter", "night", 3),
            pop("reveller_day", "festival", 12, when=FEAST),
            pop("feaster", "parilia_night", 14, when=FEAST), pop("feast_woman", "parilia_night", 6, when=FEAST)]},
        {"id": "quirinal", "area": "town", "populations": quarter(12, 10, 7, 9, 3, 2, 1, 1) + [
            per("water_carrier", "r_lacus", 1, "houses"), pop("patron", "salutatio", 4), pop("client", "salutatio", 10),
            pop("gardener", "fields", 4), pop("litter", "morning", 2),
            pop("feaster", "parilia_night", 6, when=FEAST)]},
        {"id": "esquiline", "area": "town", "populations": quarter(12, 10, 6, 8, 3, 3, 1, 1) + [
            per("insula_shop", "r_insula", 1, "market"), per("glassblower", "r_glass", 1, "work"),
            per("water_carrier", "r_lacus", 1, "houses"), pop("veteran", "day", 3), pop("auxiliary", "day", 2),
            pop("feaster", "parilia_night", 8, when=FEAST), pop("feast_woman", "parilia_night", 3, when=FEAST)]},
        {"id": "oppian", "area": "town", "populations": [
            per("stoker", "r_bath_small", 1, "always"), pop("bather", "baths", 36), pop("exerciser", "day", 22),
            pop("gardener", "fields", 8), pop("greek", "day", 6), pop("matron", "day", 6), pop("attendant", "day", 6),
            per("water_carrier", "r_lacus", 1, "houses"), pop("cat", "always", 1)]},
        {"id": "castra", "area": "country", "populations": [
            per("camp_guard", "castra_praetoria", 2, "always"), per("recruit", "castra_praetoria", 3, "work"),
            pop("veteran", "day", 10), pop("auxiliary", "day", 6)]},
        {"id": "caelian", "area": "town", "populations": quarter(11, 8, 6, 8, 3, 2, 1, 1) + shops() + [
            pop("patron", "salutatio", 4), pop("client", "salutatio", 12), pop("litter", "morning", 2),
            pop("aquarius", "work", 4), pop("gardener", "fields", 4),
            pop("feaster", "parilia_night", 6, when=FEAST), pop("feast_woman", "parilia_night", 3, when=FEAST)]},
        {"id": "aventine", "area": "town", "populations": quarter(12, 9, 6, 9, 3, 2, 1, 1) + [
            per("counter_keeper", "r_thermopolium", 1, "evening_shop"), per("smith", "r_smithy", 1, "work"),
            pop("patron", "salutatio", 4), pop("client", "salutatio", 12), pop("litter", "morning", 2),
            pop("gardener", "fields", 3),
            pop("feaster", "parilia_night", 8, when=FEAST), pop("feast_woman", "parilia_night", 3, when=FEAST)]},
        {"id": "transtiberim", "area": "town", "populations": quarter(10, 6, 5, 4, 2, 3, 1, 1, 2) + shops() + [
            per("insula_shop", "r_insula", 1, "market"), per("glassblower", "r_glass", 1, "work"),
            per("smith", "r_smithy", 1, "work"), per("fuller", "r_fullonica", 2, "work"),
            per("dyer", "r_dyeworks", 1, "work"), per("water_carrier", "r_lacus", 1, "houses"),
            per("weaver", "r_insula_low", 0.4, "work"), pop("warehouse_man", "work", 4),
            pop("jewish_trader", "day", 3), pop("gaul", "day", 1), pop("goat", "graze", 3),
            pop("sailor", "day", 2), pop("night_cart", "night", 1), pop("carter", "night", 1),
            pop("reveller_day", "festival", 6, when=FEAST),
            pop("feaster", "parilia_night", 10, when=FEAST), pop("feast_woman", "parilia_night", 4, when=FEAST), pop("youth", "parilia_night", 6, when=FEAST)]},
        {"id": "janiculum", "area": "country", "populations": [
            pop("vinedresser", "fields", 10), pop("shepherd", "graze", 3), pop("sheep", "graze", 12),
            pop("goat", "graze", 6), pop("dog", "always", 1), pop("townsman", "day", 3),
            pop("youth", "parilia_night", 30, when=FEAST), pop("shepherd", "parilia_night", 4, when=FEAST)]},
        {"id": "vatican", "area": "country", "populations": [
            pop("farmer", "fields", 16), pop("shepherd", "graze", 2), pop("goat", "graze", 4), pop("dog", "always", 1)]},
        {"id": "campagna", "area": "country", "populations": [
            pop("farmer", "fields", 9), per("farmer", "r_villa_farm", 2, "fields"), pop("shepherd", "graze", 2),
            pop("sheep", "graze", 6), pop("pig", "day", 2), pop("hen", "day", 2), pop("fisher", "harbour", 2),
            pop("ox_team", "harbour", 2), pop("dog", "always", 1), pop("youth", "parilia_night", 8, when=FEAST),
            pop("shepherd", "parilia_night", 3, when=FEAST)]},
        {"id": "appia", "area": "road", "populations": [
            pop("traveller", "road", 7), pop("carriage", "road", 1), per("mourner", "r_tomb", 1, "day"),
            per("villa_steward", "suburban_villa", 1, "work"), pop("vinedresser", "fields", 4),
            pop("muleteer", "road", 1), pop("mule", "road", 2), pop("waiting_cart", "day", 2),
            pop("night_cart", "night", 4), pop("carter", "night", 4), pop("dog", "always", 1)]},
        {"id": "decorate", "area": "wild", "populations": [pop("cat", "always", 2)]},
    ]




def chains() -> list[dict]:
    q = R + "quay.mooring"
    return [
        {"id": "rome_bread", "name": "Grain to bread", "period": 120, "hours": ["04:00", "18:00"], "stages": [
            {"slot": q, "makes": R + "goods_grain_sack", "near": "emporium", "by": "docker",
             "label": "unloaded from a barge towed up from Portus"},
            {"carry": R + "goods_grain_sack", "from": q, "to": R + "horrea_galbana.door", "near": "emporium",
             "by": "docker", "workers": 2},
            {"carry": R + "goods_grain_sack", "from": R + "horrea_galbana.door", "to": R + "r_bakery.work",
             "near": "velabrum", "by": "grain_mule", "units": 2, "workers": 3, "label": "by pack mule: no carts by day"},
            {"slot": R + "r_bakery.work", "needs": R + "goods_grain_sack", "makes": R + "goods_bread",
             "near": "velabrum", "by": "baker", "label": "ground by the donkeys, kneaded, stamped, baked"},
            {"carry": R + "goods_bread", "from": R + "r_bakery.work", "to": R + "r_taberna.sell", "near": "velabrum",
             "by": "baker"},
            {"slot": R + "r_taberna.sell", "sink": R + "goods_bread", "near": "velabrum", "by": "shopkeeper",
             "label": "sold to a customer, who walks off eating"}]},
        {"id": "rome_oil", "name": "Oil for the counters", "period": 160, "hours": ["05:00", "18:00"], "stages": [
            {"slot": q, "makes": R + "goods_oil_amphora", "near": "emporium", "by": "docker",
             "label": "a Baetican amphora landed at the wharf"},
            {"carry": R + "goods_oil_amphora", "from": q, "to": R + "r_horrea.door", "near": "emporium",
             "by": "docker", "workers": 2},
            {"carry": R + "goods_oil_amphora", "from": R + "r_horrea.door", "to": R + "r_thermopolium.serve",
             "near": "velabrum", "by": "porter", "workers": 3},
            {"slot": R + "r_thermopolium.serve", "sink": R + "goods_oil_amphora", "near": "velabrum",
             "by": "counter_keeper", "label": "poured into the counter's jars"}]},
        {"id": "rome_testaccio", "name": "The mound of sherds", "period": 140, "hours": ["06:00", "18:00"], "stages": [
            {"slot": R + "r_horrea.door", "makes": R + "goods_oil_amphora", "near": "testaccio", "by": "warehouse_man",
             "label": "an oil amphora emptied into smaller jars"},
            {"carry": R + "goods_oil_amphora", "from": R + "r_horrea.door", "to": R + "testaccio.dump",
             "near": "testaccio", "by": "warehouse_man", "units": 2, "workers": 2},
            {"slot": R + "testaccio.dump", "sink": R + "goods_oil_amphora", "by": "dumper",
             "label": "broken and laid in lime on the mound"}]},
        {"id": "rome_marble", "name": "Marble for Venus and Roma", "period": 300, "hours": ["06:00", "17:30"],
         "stages": [
             {"slot": q, "makes": R + "goods_marble", "near": "emporium", "by": "docker",
              "label": "a block landed at the marble wharf"},
             {"carry": R + "goods_marble", "from": q, "to": R + "r_crane.work", "near": "venus_roma_site",
              "by": "site_cart", "units": 1, "workers": 3, "label": "carts for public works may run by day"},
             {"slot": R + "r_crane.work", "needs": R + "goods_marble", "makes": R + "goods_marble",
              "out": R + "venus_roma.work", "near": "venus_roma_site", "by": "crane_walker",
              "label": "lifted by the treadwheel"},
             {"slot": R + "venus_roma.work", "sink": R + "goods_marble", "by": "mason",
              "label": "set in the peristyle"}]},
        {"id": "rome_bricks", "name": "Bricks for the temple platform", "period": 200, "hours": ["06:00", "17:30"],
         "stages": [
             {"slot": q, "makes": R + "goods_bricks", "near": "forum_boarium", "by": "docker",
              "label": "stamped bricks off a barge from the yards up the Tiber"},
             {"carry": R + "goods_bricks", "from": q, "to": R + "venus_roma.work", "near": "forum_boarium",
              "by": "site_cart", "units": 3, "workers": 2},
             {"slot": R + "venus_roma.work", "sink": R + "goods_bricks", "by": "bricklayer",
              "label": "laid in the facing of the platform"}]},
        {"id": "rome_travertine", "name": "Travertine by night", "period": 240, "hours": ["19:00", "05:00"],
         "stages": [
             {"slot": "node:porta_capena", "makes": "world.goods_block", "by": "night_cart",
              "label": "a block from Tibur, waiting at the gate for dark"},
             {"carry": "world.goods_block", "from": "node:porta_capena", "to": R + "venus_roma.work",
              "by": "night_cart", "units": 1, "workers": 3},
             {"slot": R + "venus_roma.work", "sink": "world.goods_block", "by": "night_unloader",
              "label": "unloaded by torchlight for the morning's masons"}]},
        {"id": "rome_water", "name": "Water from the fountain", "period": 90, "hours": ["05:00", "19:30"],
         "stages": [
             {"slot": R + "r_lacus.fill", "makes": R + "goods_water_jug", "near": "transtiberim",
              "by": "water_carrier", "label": "filled at the street fountain, fed by an aqueduct"},
             {"carry": R + "goods_water_jug", "from": R + "r_lacus.fill", "to": R + "r_insula.door",
              "near": "transtiberim", "by": "water_carrier", "workers": 2},
             {"slot": R + "r_insula.door", "sink": R + "goods_water_jug", "near": "transtiberim", "by": "housewife",
              "label": "carried up the stairs: the upper floors have no pipes"}]},
        {"id": "rome_cloth", "name": "Cloth: weaver, fuller, dyer, shop", "period": 200, "hours": ["06:00", "18:00"],
         "stages": [
             {"slot": R + "r_insula_low.sell", "makes": R + "goods_cloth", "near": "transtiberim", "by": "weaver",
              "label": "a length of woollen cloth off the loom"},
             {"carry": R + "goods_cloth", "from": R + "r_insula_low.sell", "to": R + "r_fullonica.work",
              "near": "transtiberim", "by": "errand_slave"},
             {"slot": R + "r_fullonica.work", "needs": R + "goods_cloth", "makes": R + "goods_cloth",
              "near": "transtiberim", "by": "fuller", "label": "trodden, rinsed, brushed and dried"},
             {"carry": R + "goods_cloth", "from": R + "r_fullonica.work", "to": R + "r_dyeworks.work",
              "near": "transtiberim", "by": "errand_slave"},
             {"slot": R + "r_dyeworks.work", "needs": R + "goods_cloth", "makes": R + "goods_cloth",
              "near": "transtiberim", "by": "dyer", "label": "dyed with madder"},
             {"carry": R + "goods_cloth", "from": R + "r_dyeworks.work", "to": R + "r_taberna.sell",
              "near": "transtiberim", "by": "housewife"},
             {"slot": R + "r_taberna.sell", "sink": R + "goods_cloth", "near": "transtiberim", "by": "shopkeeper",
              "label": "sold for a tunic"}]},
        {"id": "rome_fish", "name": "Fish", "period": 150, "hours": ["05:00", "12:00"], "stages": [
            {"slot": q, "makes": R + "goods_fish", "near": "forum_boarium", "by": "fisher",
             "label": "landed from a river boat"},
            {"carry": R + "goods_fish", "from": q, "to": R + "r_stall.sell", "near": "forum_boarium",
             "by": "housewife", "units": 2},
            {"slot": R + "r_stall.sell", "sink": R + "goods_fish", "near": "forum_boarium", "by": "stall_keeper",
             "label": "sold"}]},
    ]


FESTIVALS = [
    {"id": "parilia", "season": "spring", "day": 2, "hours": ["04:30", "23:00"]},
    {"id": "vinalia", "season": "spring", "day": 3, "hours": ["07:00", "12:00"]},
    {"id": "vestalia", "season": "summer", "day": 1, "hours": ["05:00", "18:00"]},
    {"id": "ludi_apollinares", "season": "summer", "day": 3, "hours": ["12:00", "18:00"]},
    {"id": "ludi_romani", "season": "autumn", "day": 1, "hours": ["12:00", "18:00"]},
    {"id": "saturnalia", "season": "winter", "day": 2, "hours": ["06:00", "23:00"]},
    {"id": "lupercalia", "season": "winter", "day": 3, "hours": ["08:00", "12:00"]},
]


def ev(id_, rarity, size, trigger, duration, steps=(), **kw) -> dict:
    e = {"id": id_, "rarity": rarity, "size": size, "trigger": trigger, "duration": list(duration),
         "steps": list(steps)}
    e.update(kw)
    return e


def window(hours, chance=1.0, **kw) -> dict:
    return {"on": "window", "hours": list(hours), "chance": chance, **kw}


def events() -> list[dict]:
    F = "parilia"
    E = []
    a = E.append
    # --- the Parilia, Rome's birthday (bible §7.2 as corrected) ------------------------------
    a(ev("parilia_dawn_prayer", "festival", "small", {"on": "calendar", "festival": F, "hours": ["05:00", "05:30"]},
         (70, 90), [use(anim="idle", dur=(50, 70))], zone="janiculum",
         cast=[{"role": "shepherd", "count": 3, "from": "district"}, {"group": "shepherds_flock"}],
         sfx="sfx/world/sheep_bells.wav", card="parilia_rite", string="parilia_dawn"))
    a(ev("parilia_fumigants", "festival", "medium", {"on": "calendar", "festival": F, "hours": ["07:00", "07:30"]},
         (90, 120), [go(node="vesta"), use(anim="idle", dur=(60, 90))], zone="forum",
         cast=[{"role": "reveller_day", "count": 10, "from": "district"}, {"role": "vestal", "count": 2},
               {"actor": R + "vestalis_maxima", "count": 1}], card="parilia_rite", string="parilia_fumigants"))
    a(ev("parilia_procession", "festival", "large", {"on": "calendar", "festival": F, "hours": ["09:00", "09:30"]},
         (100, 120), [go(node="vesta"), go(node="via_sacra_velia"), go(node="arch_titus"), go(node="venus_roma_site"),
                      use(item=R + "venus_roma", slot="work", anim="idle", dur=(30, 40)),
                      {"emit": {"sfx": "sfx/rome/tibia.wav"}}],
         route=["forum", "vesta", "via_sacra_velia", "arch_titus", "venus_roma_site"],
         cast=[{"group": "parilia_procession"}, {"role": "reveller_day", "count": 16, "from": "district"}],
         ambience={"file": "amb/rome/procession.ogg", "gain": 0.8}, card="romaia", string="parilia_procession"))
    a(ev("parilia_pompa", "festival", "large", {"on": "calendar", "festival": F, "hours": ["13:30", "14:00"]},
         (100, 115), [go(node="velabrum"), go(node="vicus_tuscus"), go(node="circus_carceres")],
         route=["clivus_foot", "velabrum", "vicus_tuscus", "circus_carceres"],
         cast=[{"group": "pompa_circensis"}], sfx="sfx/rome/tibia.wav", card="factions", string="pompa"))
    a(ev("parilia_races", "festival", "large", {"on": "after", "event": "parilia_pompa"}, (90, 100),
         [use(item=R + "circus_maximus", slot="spectator", anim="idle", dur=(80, 95))], zone="circus",
         cast=[{"actor": R + "racing_chariot", "count": 4}, {"actor": R + "diocles", "count": 1},
               {"actor": R + "hadrian", "count": 1}, {"actor": R + "sabina", "count": 1}],
         ambience={"file": "amb/rome/circus.ogg", "gain": 0.9}, card="circus_maximus", string="races"))
    a(ev("parilia_purification", "festival", "medium", {"on": "calendar", "festival": F, "hours": ["18:30", "19:00"]},
         (100, 120), [use(anim="idle", dur=(30, 40)), {"emit": {"fx": "smoke"}}, wander(zone="janiculum", dur=(50, 70))],
         zone="janiculum", cast=[{"role": "shepherd", "count": 4, "from": "district"}, {"group": "shepherds_flock"},
                                 {"role": "youth", "count": 4, "from": "district"}],
         sfx="sfx/world/sheep_bells.wav", card="parilia_rite", string="parilia_purification"))
    a(ev("parilia_bonfires", "festival", "large", {"on": "calendar", "festival": F, "hours": ["21:30", "22:00"]},
         (110, 120), [{"emit": {"fx": "bonfire"}}, use(anim="idle", dur=(20, 30)), wander(radius=3, dur=(60, 80))],
         zones=["janiculum", "transtiberim", "boarium", "campagna"],
         cast=[{"role": "youth", "count": 10, "from": "district"}, {"role": "shepherd", "count": 4},
               {"role": "child", "count": 6}, {"actor": R + "musician", "count": 2}],
         sfx="sfx/rome/tibia.wav", glow=True, card="parilia", string="bonfires"))
    a(ev("parilia_feast", "festival", "medium", {"on": "calendar", "festival": F, "hours": ["19:00", "19:30"]},
         (110, 120), [go(slot_kind="door", within=10), use(anim="sit", dur=(90, 110))], zone="subura",
         cast=[{"role": "townsman", "count": 10}, {"role": "housewife", "count": 6}, {"role": "child", "count": 4}],
         card="parilia"))
    a(ev("hut_of_romulus", "festival", "small", {"on": "calendar", "festival": F, "hours": ["10:30", "11:00"]},
         (60, 80), [go(node="palatine_west"), use(anim="idle", dur=(50, 70))], zone="palatine",
         cast=[{"role": "courtier", "count": 4}, {"role": "reveller_day", "count": 6}], card="romulus"))
    # --- the everyday --------------------------------------------------------------------
    a(ev("salutatio", "daily", "medium", window(("05:00", "05:30")), (90, 120),
         [go(item=R + "r_domus", slot="salutatio", within=10), use(anim="idle", dur=(70, 100))],
         zones=["caelian", "aventine", "quirinal"], cast=[{"group": "salutatio_queue"}], card="salutatio",
         string="salutatio"))
    a(ev("scipio_dawn", "daily", "small", window(("04:00", "04:30")), (60, 80),
         [use(item=R + "capitolium", slot="sacrifice", anim="idle", dur=(50, 70))], zone="capitol",
         cast=[{"actor": R + "scipio", "count": 1}], card="scipio"))
    a(ev("dioscuri", "rare", "small", window(("04:30", "05:30"), 0.08), (20, 30),
         [go(node="vesta"), use(anim="idle", dur=(15, 20))], zone="forum",
         cast=[{"actor": R + "castor", "count": 2}, {"actor": R + "horse", "count": 2}], card="dioscuri"))
    a(ev("capitol_sacrifice", "common", "medium", window(("08:00", "08:30"), 0.7), (80, 100),
         [use(item=R + "capitolium", slot="sacrifice", anim="pour", dur=(60, 80)), {"emit": {"sfx": "sfx/rome/tibia.wav"}}],
         zone="capitol", cast=[{"role": "temple_priest", "count": 1}, {"role": "flamen", "count": 2},
                               {"actor": R + "musician", "count": 1}, {"actor": R + "ox", "count": 1},
                               {"role": "worshipper", "count": 6}], card="sacrifice"))
    a(ev("trial", "common", "medium", window(("08:00", "08:30"), 0.8, not_festival=F), (120, 150),
         [go(item=R + "julia", spot="beside"), use(anim="idle", dur=(100, 130))], zone="forum",
         cast=[{"role": "advocate", "count": 2}, {"role": "forum_crowd", "count": 12, "from": "district"},
               {"role": "client", "count": 4}], card="law", string="trial"))
    a(ev("senate", "uncommon", "medium", window(("07:00", "07:30"), 0.6, days=SENATE, not_festival=F), (100, 120),
         [go(node="vesta"), go(node="forum"), go(item=R + "curia", slot="door"), {"enter": {"here": True}, "dur": [60, 80]}],
         route=["via_sacra_velia", "vesta", "forum", "curia"], cast=[{"group": "senate_arrival"}],
         card="senate", string="senate"))
    a(ev("recitation", "daily", "small", window(("09:00", "09:30"), not_festival=F), (60, 80),
         [use(item=R + "forum_square", slot="school", anim="talk", dur=(50, 70))], zone="forum",
         cast=[{"role": "schoolmaster", "count": 1}, {"role": "pupil", "count": 6}], card="school"))
    a(ev("market_day", "uncommon", "medium", window(("06:30", "07:00"), days=MARKET), (150, 180),
         [go(item=R + "r_stall", slot="buy", within=8), use(anim="idle", dur=(120, 150)), {"emit": {"sfx": "sfx/world/vendor.wav"}}],
         zones=["boarium", "campus"], cast=[{"role": "shopper", "count": 16, "from": "district"},
                                            {"actor": R + "farmer", "count": 4}], card="nundinae", string="market_day"))
    a(ev("pompa", "uncommon", "large", window(("13:30", "14:00"), days=RACES, not_festival=F), (100, 115),
         [go(node="velabrum"), go(node="vicus_tuscus"), go(node="circus_carceres")],
         route=["clivus_foot", "velabrum", "vicus_tuscus", "circus_carceres"], cast=[{"group": "pompa_circensis"}],
         sfx="sfx/rome/tibia.wav", card="factions", string="pompa"))
    a(ev("races", "uncommon", "large", {"on": "after", "event": "pompa"}, (150, 180),
         [use(item=R + "circus_maximus", slot="spectator", anim="idle", dur=(140, 170))], zone="circus",
         cast=[{"actor": R + "racing_chariot", "count": 4}, {"actor": R + "diocles", "count": 1}],
         ambience={"file": "amb/rome/circus.ogg", "gain": 0.9}, card="circus_maximus", string="races"))
    a(ev("chariot_practice", "common", "small", window(("08:00", "08:30"), 0.7), (80, 100),
         [go(node="circus_stands"), go(node="circus_carceres")], zone="circus",
         cast=[{"actor": R + "racing_chariot", "count": 2}, {"role": "stable_hand", "count": 3}],
         sfx="sfx/world/gallop.wav", card="factions"))
    a(ev("arena_games", "uncommon", "large", window(("14:00", "14:30"), 0.7, days=GAMES, not_festival=F), (150, 180),
         [go(item=R + "colosseum", slot="entrance"), {"enter": {"here": True}, "dur": [120, 150]},
          {"emit": {"sfx": "sfx/rome/hydraulis.wav"}}, {"emit": {"sfx": "sfx/rome/cornu.wav"}}],
         zone="colosseum", cast=[{"role": "game_crowd", "count": 20, "from": "district"}], card="amphitheatre_games",
         string="arena"))
    a(ev("grain_dole", "uncommon", "medium", window(("08:00", "08:30"), days=DOLE, not_festival=F), (120, 150),
         [go(item=R + "r_horrea", slot="door", within=6), use(anim="idle", dur=(100, 130))], zone="campus",
         cast=[{"role": "townsman", "count": 12, "from": "district"}, {"actor": R + "aelius_eutyches", "count": 1}],
         card="annona", string="dole"))
    a(ev("barges_arrive", "common", "medium", {"on": "token_arrived", "actor": R + "barge"}, (90, 120),
         [use(item=R + "quay", slot="mooring", anim="carry_idle", dur=(60, 90), effect="unload"),
          {"emit": {"sfx": "sfx/world/rope.wav"}}], zone="emporium",
         cast=[{"role": "docker", "count": 6, "from": "district"}, {"actor": R + "apion", "count": 1},
               {"actor": R + "mulvius", "count": 1}], ambience={"file": "amb/rome/river.ogg", "gain": 0.7},
         card="annona", string="grain_fleet"))
    a(ev("towing", "common", "small", window(("07:00", "16:00"), every=1800), (90, 110),
         [go(node="emporium"), use(anim="haul", dur=(60, 80))], route=["pons_sublicius", "emporium"],
         cast=[{"role": "hauler", "count": 4}, {"role": "ox_team", "count": 2}], sfx="sfx/world/rope.wav", card="hauler"))
    a(ev("crane_lifts", "uncommon", "small", {"on": "chain", "chain": "rome_marble", "stage": 2}, (60, 80),
         [use(item=R + "r_crane", slot="work", anim="haul", dur=(50, 70))], zone="velia",
         cast=[{"role": "crane_walker", "count": 1}, {"role": "mason", "count": 2}],
         ambience={"file": "amb/rome/treadwheel.ogg", "gain": 0.8}, card="treadwheel"))
    a(ev("vestals_walk", "daily", "small", window(("12:30", "13:00")), (100, 115),
         [go(node="vicus_tuscus"), go(node="circus_stands")], route=["vestals", "vicus_tuscus", "circus_stands"],
         cast=[{"group": "vestals_walk"}], card="vestals_order", string="vestals"))
    a(ev("guard_change_dawn", "daily", "small", window(("06:00", "06:30")), (70, 90),
         [go(node="palatine_west"), go(node="palatine_court"), use(anim="march", dur=(30, 40))], zone="palatine",
         cast=[{"group": "guard_relief"}], sfx="sfx/rome/cornu.wav", card="praetorian", string="guard"))
    a(ev("guard_change_dusk", "daily", "small", window(("18:00", "18:30")), (70, 90),
         [go(node="palatine_west"), go(node="palatine_court"), use(anim="march", dur=(30, 40))], zone="palatine",
         cast=[{"group": "guard_relief"}], sfx="sfx/rome/cornu.wav", card="praetorian"))
    a(ev("lamps_lit", "daily", "small", window(("18:30", "19:00")), (70, 90),
         [{"each": {"item": R + "r_compitum", "max": 4}, "state": "lit"}], zones=["subura", "campus", "transtiberim"],
         sfx="sfx/world/lamp.wav", card="compitum"))
    a(ev("night_carts", "daily", "medium", window(("19:00", "19:30")), (110, 120),
         [go(node="porta_capena"), go(node="colosseum"), go(node="venus_roma_site")],
         route=["appia_tombs", "porta_capena", "colosseum", "venus_roma_site"],
         cast=[{"role": "night_cart", "count": 4}, {"role": "carter", "count": 4}],
         ambience={"file": "amb/world/cart.ogg", "gain": 0.8}, card="night_carts", string="night_carts"))
    a(ev("vigiles_round", "daily", "small", window(("21:00", "21:30")), (100, 120),
         [go(node="subura_baker"), go(node="carinae")], route=["esquiline", "subura_baker", "carinae"],
         cast=[{"group": "vigiles_round"}], card="vigiles"))
    a(ev("fire_alarm", "rare", "medium", window(("20:00", "02:00"), every=9000), (90, 120),
         [go(item=R + "r_insula", slot="door", within=6), use(anim="idle", dur=(70, 90)), {"emit": {"fx": "smoke"}}],
         zone="subura", cast=[{"role": "vigil", "count": 6}, {"actor": R + "flavius_valens", "count": 1},
                              {"role": "townsman", "count": 6}], card="vigiles", string="fire"))
    a(ev("funeral", "uncommon", "medium", window(("08:30", "09:00"), 0.3, not_festival=F), (100, 115),
         [go(node="appia_tombs"), use(item=R + "r_tomb", slot="mourn", anim="idle", dur=(30, 40)),
          {"emit": {"sfx": "sfx/rome/tibia.wav"}}],
         route=["porta_capena", "appia_tombs"], cast=[{"group": "funeral"}], card="tombs", string="funeral"))
    a(ev("wedding", "rare", "medium", window(("18:30", "19:00"), 0.15), (100, 115),
         [go(node="carinae"), go(slot_kind="door", within=6), {"emit": {"sfx": "sfx/rome/tibia.wav"}}],
         route=["subura", "carinae"], cast=[{"group": "wedding"}], card="wedding", string="wedding"))
    # --- small things ---------------------------------------------------------------------
    a(ev("dog_sausage", "uncommon", "small",
         {"on": "reactive", "when": {"near": {"actor": R + "dog", "item": R + "r_thermopolium", "within": 2}}},
         (6, 8), [go(item=R + "r_thermopolium", spot="beside"), wander(radius=8, dur=(4, 6))],
         cast=[{"role": "dog", "count": 1}], sfx="sfx/world/vendor.wav", card="dogs"))
    a(ev("cat_fish", "uncommon", "small",
         {"on": "reactive", "when": {"near": {"actor": R + "cat", "item": R + "r_stall", "within": 2,
                                              "goods": R + "goods_fish"}}},
         (6, 8), [go(item=R + "r_stall", spot="beside"), {"take": R + "goods_fish"}, wander(radius=8, dur=(4, 6))],
         cast=[{"role": "cat", "count": 1}], sfx="sfx/world/vendor.wav", card="cats"))
    a(ev("fountain_quarrel", "common", "small", window(("06:00", "09:00"), 0.4), (30, 45),
         [go(item=R + "r_lacus", slot="fill", within=8), use(anim="serve", dur=(20, 30))], zone="transtiberim",
         cast=[{"role": "water_carrier", "count": 2}, {"role": "housewife", "count": 2}], card="fountain"))
    a(ev("graffiti", "common", "small", window(("10:00", "17:00"), 0.5), (20, 30),
         [go(slot_kind="door", within=8), use(anim="idle", dur=(15, 20))], zone="subura",
         cast=[{"role": "townsman", "count": 1}], card="graffiti"))
    a(ev("pigeons_up", "common", "small",
         {"on": "reactive", "when": {"near": {"actor": R + "child", "item": R + "forum_square", "within": 3}}},
         (5, 6), [], zone="forum", cast=[{"role": "pigeon", "count": 6}], sfx="sfx/world/pigeons_up.wav"))
    a(ev("fountain_play", "common", "small", window(("13:00", "16:00"), 0.4), (60, 90),
         [go(item=R + "r_lacus", slot="fill", within=10), use(anim="run", dur=(40, 60))], zone="campus",
         cast=[{"role": "child", "count": 4}], card="children"))
    a(ev("street_performer", "common", "small", window(("14:30", "17:00"), 0.5), (90, 110),
         [go(node="saepta"), use(anim="idle", dur=(70, 90))], zone="campus",
         cast=[{"actor": R + "musician", "count": 1}, {"role": "visitor_campus", "count": 8}], card="performer"))
    a(ev("starlings", "daily", "small", window(("18:30", "19:00"), season=["autumn", "winter", "spring"]), (60, 80),
         [], zone="river", cast=[{"actor": R + "swallow", "count": 12}], card="starlings"))
    a(ev("swifts", "daily", "small", window(("18:00", "18:30"), season=["spring", "summer"]), (60, 80),
         [wander(radius=12, dur=(50, 70))], zone="forum", cast=[{"actor": "world.swift", "count": 8}],
         sfx="sfx/world/swifts.wav"))
    a(ev("tiber_mist", "common", "small", {"on": "window", "hours": ["04:00", "06:00"], "chance": 0.5,
                                            "season": ["spring", "autumn"]},
         (120, 150), [{"emit": {"fx": "mist"}}], zone="river"))
    a(ev("spring_shower", "common", "medium", {"on": "weather", "kind": "rain", "season": ["spring"]}, (90, 150),
         [{"emit": {"fx": "gutter_spout"}}], zone="subura", card="weather_april"))
    a(ev("rainbow", "rare", "small", {"on": "weather", "kind": "rain_stop", "season": ["spring"], "hours": ["07:00", "18:00"]},
         (40, 60), [], zone="palatine"))
    a(ev("dogs_bark", "common", "small", window(("21:00", "03:00"), every=5400), (5, 6), [], zone="subura",
         sfx="sfx/world/dog_far.wav"))
    a(ev("flock_out", "daily", "small", window(("05:30", "06:00")), (80, 100),
         [wander(zone="janiculum", dur=(70, 90))], route=["transtiberim", "janiculum"],
         cast=[{"group": "shepherds_flock"}], sfx="sfx/world/sheep_bells.wav", card="shepherd"))
    a(ev("hadrian_site", "common", "small", window(("10:30", "11:00"), 0.5, not_festival=F), (90, 110),
         [use(item=R + "venus_roma", slot="work", anim="gesture", dur=(70, 90))], zone="velia",
         cast=[{"group": "imperial_party"}, {"role": "mason", "count": 2}], card="hadrian"))
    # --- dusk memories ------------------------------------------------------------------
    a(ev("caesar_memory", "daily", "small", window(("18:30", "19:00")), (80, 100),
         [go(node="forum"), use(anim="idle", dur=(70, 90))], zone="forum",
         cast=[{"actor": R + "caesar", "count": 1}], card="caesar"))
    a(ev("cicero_memory", "daily", "small", window(("19:00", "19:30")), (80, 100),
         [use(item=R + "rostra", slot="orator", anim="gesture", dur=(70, 90))], zone="forum",
         cast=[{"actor": R + "cicero", "count": 1}], card="cicero"))
    a(ev("numa_memory", "daily", "small", window(("19:30", "20:00")), (70, 90),
         [go(node="vesta"), use(anim="idle", dur=(60, 80))], zone="forum",
         cast=[{"actor": R + "numa", "count": 1}], card="numa"))
    a(ev("trajan_memory", "daily", "small", window(("18:30", "19:00")), (80, 100),
         [go(node="trajan_forum"), use(anim="idle", dur=(70, 90))], zone="fora",
         cast=[{"actor": R + "trajan", "count": 1}, {"actor": R + "plotina", "count": 1}], card="trajan"))
    a(ev("mesomedes_evening", "common", "small", window(("19:00", "19:30"), 0.6), (90, 110),
         [go(node="palatine_court"), use(anim="play", dur=(80, 100))], zone="palatine",
         cast=[{"actor": R + "mesomedes", "count": 1}, {"role": "courtier", "count": 4}], card="mesomedes"))
    # --- the other seasons --------------------------------------------------------------
    a(ev("vinalia", "festival", "small", {"on": "calendar", "festival": "vinalia", "hours": ["08:00", "08:30"]},
         (80, 100), [use(item=R + "capitolium", slot="sacrifice", anim="pour", dur=(60, 80))], zone="capitol",
         cast=[{"role": "temple_priest", "count": 1}, {"role": "worshipper", "count": 8}], card="vinalia"))
    a(ev("vestalia", "festival", "medium", {"on": "calendar", "festival": "vestalia", "hours": ["07:00", "07:30"]},
         (120, 150), [go(node="vesta"), use(anim="idle", dur=(100, 130))], zone="forum",
         cast=[{"role": "matron", "count": 10}, {"role": "vestal", "count": 2}], card="vestalia"))
    a(ev("ludi_romani", "festival", "large", {"on": "calendar", "festival": "ludi_romani", "hours": ["14:00", "14:30"]},
         (150, 180), [use(item=R + "circus_maximus", slot="spectator", anim="idle", dur=(140, 170))], zone="circus",
         cast=[{"actor": R + "racing_chariot", "count": 4}, {"role": "race_fan", "count": 20}],
         ambience={"file": "amb/rome/circus.ogg", "gain": 0.9}, card="factions"))
    a(ev("ludi_apollinares", "festival", "large",
         {"on": "calendar", "festival": "ludi_apollinares", "hours": ["14:00", "14:30"]},
         (150, 180), [go(node="marcellus"), use(anim="idle", dur=(130, 160))], zone="campus",
         cast=[{"role": "theatre_goer", "count": 16}], card="theatre"))
    a(ev("saturnalia", "festival", "medium", {"on": "calendar", "festival": "saturnalia", "hours": ["18:00", "18:30"]},
         (110, 120), [go(slot_kind="door", within=10), use(anim="sit", dur=(90, 110))], zone="subura",
         cast=[{"role": "townsman", "count": 10}, {"role": "errand_slave", "count": 6}], card="saturnalia"))
    a(ev("lupercalia", "festival", "medium", {"on": "calendar", "festival": "lupercalia", "hours": ["09:00", "09:30"]},
         (100, 115), [go(node="palatine_west"), go(node="circus_carceres")], zone="palatine",
         cast=[{"role": "youth", "count": 8}], card="lupercal"))
    return E


def figures() -> list[dict]:
    def fig(actor, presence, card_, sch=None, routines=None, **kw):
        f = {"actor": R + actor if actor else None, "presence": presence, "card": card_}
        if sch:
            f["schedule"] = sched(*sch)
            f["routines"] = routines
        f.update(kw)
        return {k: v for k, v in f.items() if v is not None}
    return [
        fig("hadrian", "present", "hadrian", [("06:00", "09:00", "palace"), ("11:30", "13:00", "pantheon"),
                                              ("15:00", "18:00", "palace")],
            {"palace": loop(go(node="palatine_court"), use(anim="talk", dur=(30, 50)), go(node="palatine_west"),
                            use(anim="gesture", dur=(15, 25))),
             "pantheon": once(go(node="pantheon"), use(anim="idle", until={"hour": "13:00"}))},
            imagined=True, note="his whereabouts on 21 April 126 are not recorded; the game imagines him here. "
                                "Events take him to the Parilia procession, the races and the Venus and Roma site"),
        fig("sabina", "present", "sabina", [("08:00", "11:00", "gardens"), ("15:00", "17:00", "vestals")],
            {"gardens": loop(go(node="palatine_court"), use(anim="talk", dur=(30, 50)), wander(radius=4, dur=(20, 30))),
             "vestals": once(go(item=R + "vestals", slot="door"), use(anim="talk", until={"hour": "17:00"}))},
            imagined=True, note="presence on the day not recorded; imagined, like Hadrian's"),
        fig("antinous", "present", "antinous", [("07:00", "10:00", "ride"), ("16:00", "18:00", "ride")],
            {"ride": loop(go(node="palatine_west"), wander(radius=8, dur=(40, 70)), use(anim="idle", dur=(20, 30)))},
            imagined=True, note="with Hadrian from about 124; his presence in Rome on the day is not recorded"),
        fig("marcus", "present", "marcus", [("07:00", "11:00", "lessons"), ("15:00", "18:00", "home")],
            {"lessons": loop(go(node="caelian"), use(anim="idle", dur=(40, 60)), go(node="player_domus"),
                             wait(dur=(20, 30))),
             "home": once(go(item=R + "r_domus", slot="door", within=10), use(anim="idle", until={"hour": "18:00"}))},
            note="four years old, five on 26 April; his family's house is on the Caelian; watches the procession"),
        fig("apollodorus", "present", "apollodorus", [("07:30", "12:00", "forum"), ("14:30", "17:30", "forum")],
            {"forum": loop(use(item=R + "trajan_forum", slot="apollodorus", anim="gesture", dur=(40, 60)),
                           use(anim="idle", dur=(30, 50)))},
            note="presence in Rome in 126 uncertain; the card tells Dio's story with its doubts"),
        fig("juvenal", "present", "juvenal", [("04:30", "07:00", "queue"), ("08:00", "12:00", "subura"),
                                              ("15:00", "19:00", "subura")],
            {"queue": once(go(item=R + "r_domus", slot="salutatio", within=30), use(anim="idle", until={"hour": "07:00"})),
             "subura": loop(go(node="subura"), use(anim="talk", dur=(20, 40)), go(node="carinae"), wait(dur=(20, 30)))}),
        fig("suetonius", "present", "suetonius", [("08:00", "12:00", "library"), ("14:00", "17:00", "library")],
            {"library": loop(go(node="trajan_forum"), use(anim="write", dur=(60, 90)), wander(radius=3, dur=(15, 25)))}),
        fig("mesomedes", "present", "mesomedes", [("17:00", "21:00", "evening")],
            {"evening": loop(go(node="palatine_court"), use(anim="play", dur=(60, 90)), use(anim="idle", dur=(20, 30)))}),
        fig("soranus", "present", "soranus", [("07:00", "11:00", "island"), ("14:00", "18:00", "calls")],
            {"island": loop(go(node="tiber_island_east"), use(anim="talk", dur=(40, 60)), wait(dur=(20, 30))),
             "calls": loop(go(slot_kind="door", within=40), use(anim="talk", dur=(40, 60)), wander(radius=6, dur=(20, 30)))}),
        fig("diocles", "present", "diocles", [("06:30", "12:00", "stables"), ("14:00", "17:00", "stables")],
            {"stables": loop(go(node="circus_carceres"), use(anim="idle", dur=(40, 60)), go(node="circus_stands"),
                             wait(dur=(20, 30)))}, note="drives in the races on race days and on the Parilia"),
        fig("vestalis_maxima", "present", "vestalis_maxima", [("04:00", "12:00", "fire"), ("14:00", "19:00", "fire")],
            {"fire": loop(go(node="vesta"), use(anim="pray", dur=(40, 60)), go(item=R + "vestals", slot="door"),
                          wait(dur=(30, 50)))}, note="walks to the Circus with a lictor (vestals_walk)"),
        fig("plotina", "memory", "plotina", note="at dusk in Trajan's Forum (trajan_memory)", translucent=True),
        fig("trajan", "memory", "trajan", note="at dusk by his Column (trajan_memory); his bronze stands on top",
            translucent=True),
        fig("numa", "memory", "numa", note="at dusk by the Regia and Vesta (numa_memory)", translucent=True),
        fig("scipio", "memory", "scipio", note="before dawn at the Capitolium (scipio_dawn)", translucent=True),
        fig("caesar", "memory", "caesar", note="at dusk by his temple (caesar_memory)", translucent=True),
        fig("cicero", "memory", "cicero", note="at dusk on the Rostra (cicero_memory)", translucent=True),
        fig("castor", "apparition", "dioscuri", note="two riders at Juturna's spring at dawn, rarely (dioscuri)"),
        fig(None, "statue", "aeneas", at="augustus_forum"),
        fig(None, "statue", "romulus", at="augustus_forum"),
        fig(None, "shrine", "romulus", at="lupercal"),
        fig(None, "statue", "cloelia", at="via_sacra_velia"),
        fig(None, "statue", "cornelia", at="octavia"),
        fig("claudia_helpis", "present", "claudia_helpis", [("05:30", "22:00", "counter")],
            {"counter": loop(use(item=R + "r_thermopolium", slot="serve", within=4, anim="serve", dur=(40, 60)),
                             use(anim="idle", dur=(10, 20)))}, district="subura"),
        fig("vibius_primus", "present", "vibius_primus", [("02:00", "12:00", "bake")],
            {"bake": loop(use(item=R + "r_bakery", slot="work", anim="stir", dur=(50, 70)), use(anim="idle", dur=(10, 15)))},
            district="velabrum"),
        fig("aelius_eutyches", "present", "aelius_eutyches", [("07:00", "10:00", "forum"), ("10:00", "17:00", "horrea")],
            {"forum": loop(go(node="forum"), use(anim="write", dur=(30, 50)), go(node="curia"), wait(dur=(20, 30))),
             "horrea": loop(go(node="horrea_galbana"), use(anim="write", dur=(40, 60)), go(node="emporium"),
                            wait(dur=(20, 30)))}),
        fig("apion", "present", "apion", [("06:00", "18:00", "barge")],
            {"barge": loop(go(node="emporium"), use(anim="haul", dur=(30, 50)), go(node="horrea_galbana"), wait(dur=(20, 30)))}),
        fig("mulvius", "present", "mulvius", [("05:30", "18:30", "barge")],
            {"barge": loop(go(node="emporium"), use(anim="idle", dur=(40, 60)), go(node="pons_sublicius"), wait(dur=(30, 50)))}),
        fig("flavius_valens", "present", "flavius_valens", [("19:00", "05:00", "watch")],
            {"watch": loop(go(item=R + "r_vigiles", spot="beside"), use(anim="idle", dur=(20, 40)),
                           wander(radius=14, dur=(60, 90)))}),
        fig("felicula", "present", "felicula", [("06:00", "08:00", "water"), ("08:00", "16:00", "play"),
                                                ("16:00", "18:00", "water")],
            {"water": loop(go(item=R + "r_lacus", slot="fill", within=12), use(anim="idle", dur=(20, 30))),
             "play": loop(wander(radius=6, dur=(20, 40)), use(anim="kneel", dur=(30, 50)), use(anim="run", dur=(6, 10)))},
            district="transtiberim"),
        fig("rufina", "present", "rufina", [("06:00", "12:00", "loom"), ("14:00", "18:00", "market")],
            {"loom": loop(go(item=R + "synagogue", slot="door"), wait(dur=(10, 20)), go(node="transtiberim"),
                          use(anim="throw", dur=(60, 90))),
             "market": loop(go(node="pons_aemilius"), wait(dur=(20, 30)), go(node="forum_boarium"), wait(dur=(30, 40)))}),
        fig("sextus", "present", "sextus", [("05:00", "11:00", "litter"), ("11:00", "17:00", "errands")],
            {"litter": loop(go(item=R + "r_domus", slot="door", within=10), use(anim="carry_idle", dur=(30, 50)),
                            go(node="forum"), use(anim="carry_idle", dur=(30, 50))),
             "errands": loop(go(node="caelian"), {"take": "world.goods_firewood"}, wander(radius=6, dur=(20, 30)),
                             {"put": "world.goods_firewood"})}, district="caelian"),
        fig("iulia_ianuaria", "present", "iulia_ianuaria", [("06:00", "12:00", "calls"), ("15:00", "19:00", "calls")],
            {"calls": loop(go(slot_kind="door", within=24), use(anim="talk", dur=(40, 70)), wander(radius=8, dur=(20, 40)))},
            district="aventine"),
    ]


def cards() -> dict:
    F, L, I, RO, EV = "figure", "landmark", "idea", "role", "event"
    c = {
        # --- the Capitol and the Forum ------------------------------------------------------
        "capitolium": card(L, "Capitolium", "Temple of Jupiter Best and Greatest",
            "Rome's greatest temple: three cellae for Jupiter, Juno and Minerva behind Corinthian columns "
            "of Pentelic marble, rebuilt by Domitian with gilded bronze roof tiles and a bronze chariot on "
            "the pediment. Generals ended their triumphs here, and the year's first vows are made here."),
        "arx": card(L, "Arx", "Citadel and Juno Moneta",
            "The Capitol's northern summit, where augurs watched the birds and Juno's geese once warned of "
            "the Gauls. The mint stood near the temple of Juno Moneta, and 'money' still carries her name."),
        "tabularium": card(L, "Tabularium", "The record office",
            "A massive tufa base with an arcaded gallery of Doric half-columns, looking down the length of "
            "the Forum. The state's records and the bronze tablets of its laws were kept on the Capitol."),
        "concord": card(L, "Aedes Concordiae", "Temple of Concord",
            "A temple whose cella runs across its width behind a six-column porch. Inside is a gallery of "
            "famous statues and paintings; the Senate sometimes met here."),
        "vespasian": card(L, "Templum Vespasiani", "Temple of Vespasian and Titus",
            "A Corinthian temple on a high podium below the Tabularium, raised by Domitian to his deified "
            "father and brother."),
        "saturn": card(L, "Aedes Saturni", "Temple of Saturn",
            "One of Rome's oldest temples, Ionic columns on a high podium. The state treasury, the aerarium, "
            "is kept in its podium. In December Saturn's feast turns masters into servants for a few days."),
        "rostra": card(L, "Rostra", "The speakers' platform",
            "A curved platform faced with the bronze rams of captured warships and crowded with honorary "
            "statues. Beside it stands the Golden Milestone, from which the roads of the empire were measured."),
        "curia": card(L, "Curia Iulia", "The Senate house",
            "A tall brick hall with a plain gabled front and bronze doors. About six hundred senators meet "
            "here to pass decrees and judge their peers; their prestige is great, their power the emperor's "
            "to share."),
        "lapis_niger": card(L, "Lapis Niger", "The black stone",
            "A square of black paving behind a low fence marks an ancient, half-forgotten shrine. Some "
            "Romans said Romulus was buried here; others named a shepherd or a hero."),
        "aemilia": card(L, "Basilica Aemilia", "Hall of the Aemilii",
            "A two-storey arcade of white marble with shops along its front: a covered hall for business, "
            "money and law on the north side of the Forum."),
        "forum_square": card(L, "Forum Romanum", "The Forum square",
            "Travertine paving set with honorary columns and statues, the well-head of the Lacus Curtius "
            "and, as Pliny says, a fig, an olive and a vine growing in the square. A schoolmaster teaches "
            "his pupils under an awning here in the mornings."),
        "julia": card(L, "Basilica Iulia", "The law courts",
            "A great two-storey arcaded hall where the centumviral court hears cases about inheritance. "
            "Idlers scratched gaming boards into its steps while they waited, and you can still find them."),
        "castor": card(L, "Aedes Castoris", "Temple of Castor and Pollux",
            "A temple of eight Corinthian columns on a very high podium, vowed after the battle of Lake "
            "Regillus. Its podium held offices and strongrooms; three of its columns still stand."),
        "lacus_iuturnae": card(L, "Lacus Iuturnae", "Spring of Juturna",
            "A basin fed by the nymph's spring, with statues of the Dioscuri and their horses, where the "
            "twins were said to have watered their mounts. Its water was used in sacred rites."),
        "divus_julius": card(L, "Aedes Divi Iulii", "Temple of the Deified Julius",
            "Built where the people burned Caesar's body in 44 BC. Its speakers' platform carries the rams "
            "of ships from Actium; a round altar sits in a niche at its front."),
        "regia": card(L, "Regia", "The king's house",
            "A small, very old building, said to be King Numa's house and later the seat of the chief "
            "priest. The calendar's records and the sacred shields of Mars were kept here."),
        "vesta": card(L, "Aedes Vestae", "Temple of Vesta",
            "A round temple of twenty Corinthian columns under a conical roof with an opening for the "
            "smoke. Inside burns the fire of Rome, tended day and night by the Vestal Virgins; men may not "
            "enter. On the Parilia people fetch the ashes for their fumigations here."),
        "vestals": card(L, "Atrium Vestae", "House of the Vestals",
            "A two-storey courtyard house with long pools, home of the six Vestal Virgins who serve for "
            "thirty years. Statues of the senior Vestals line the court."),
        "piperataria": card(L, "Horrea Piperataria", "The spice warehouses",
            "Domitian's brick warehouses with small barred windows, for pepper and spices brought from "
            "India across the Red Sea and through Egypt."),
        "arch_titus": card(L, "Arcus Titi", "Arch of Titus",
            "A single marble arch on the Via Sacra. Inside, reliefs show Titus's triumph and the spoils of "
            "the Temple of Jerusalem, destroyed in AD 70, with the menorah carried shoulder high. For Rome's "
            "Jewish community it is a monument to loss, not glory."),
        "venus_roma": card(L, "Templum Veneris et Romae", "Temple of Venus and Roma, a building site",
            "Hadrian designed this vast double temple on the Velia himself, begun about 121 on the city's "
            "birthday: Venus faces east, Roma west, back to back. Treadwheel cranes lift column drums from "
            "rows on the ground; it will be dedicated in 135 and finished by 141."),
        "colossus": card(L, "Colossus", "The bronze Sun",
            "A colossal bronze statue made for Nero and turned into the Sun god with a radiate crown, "
            "perhaps 30 to 35 metres tall. To make room for the new temple, Hadrian had it moved upright "
            "with the help of elephants. The amphitheatre will one day take its name from it."),
        "meta_sudans": card(L, "Meta Sudans", "The sweating cone",
            "A tall conical fountain of brick faced with marble; water runs down its sides into a round "
            "basin where the processional routes meet."),
        "colosseum": card(L, "Amphitheatrum Flavium", "The amphitheatre",
            "Three storeys of eighty arches and an attic, 48 metres high, with statues in the upper arches "
            "and masts for the great awning. Some fifty thousand people come here for gladiators and animal "
            "hunts. The name Colosseum is medieval, from the statue beside it."),
        # --- the imperial fora --------------------------------------------------------------
        "trajan_forum": card(L, "Forum Traiani", "Forum of Trajan",
            "The newest and grandest forum: a vast paved square with a gilded bronze Trajan on horseback, "
            "colonnades with statues of captive Dacians and hemicycles on both sides, paid for with Dacian "
            "gold."),
        "basilica_ulpia": card(L, "Basilica Ulpia", "Trajan's basilica",
            "A huge hall with columns of coloured marble and gilded bronze roof tiles, closing the north "
            "side of Trajan's Forum. Courts sit inside, and slaves were freed here before a magistrate."),
        "trajan_column": card(L, "Columna Traiani", "Trajan's Column",
            "A hundred Roman feet of Luna marble wound with a spiral relief of the Dacian wars, some 2,500 "
            "figures in 23 turns, and a bronze Trajan on top. His ashes rest in its base, between a Greek "
            "and a Latin library."),
        "trajan_temple": card(L, "Templum Divi Traiani", "Temple of the Deified Trajan",
            "Hadrian's temple to Trajan, shown north of the Column where the traditional reconstruction "
            "places it; recent excavations have questioned where it stood."),
        "trajan_markets": card(L, "Mercatus Traiani", "Trajan's Markets",
            "A semicircle of brick shops in tiers climbing the Quirinal, with a vaulted hall above and the "
            "street people now call the Via Biberatica running through it: oil, wine, spices, cloth and "
            "offices."),
        "augustus_forum": card(L, "Forum Augusti", "Forum of Augustus and Mars Ultor",
            "The temple of Mars the Avenger stands against a huge grey tufa firewall that keeps the "
            "Subura's fires away. In the porticoes stand Aeneas, Romulus and the great men of Rome, each "
            "with his deeds inscribed beneath."),
        "caesar_forum": card(L, "Forum Iulium", "Forum of Caesar",
            "Caesar's narrow colonnaded square with the temple of Venus Genetrix, mother of his family, "
            "restored by Trajan in 113, and the bankers' hall beside it."),
        "nerva_forum": card(L, "Forum Transitorium", "Forum of Nerva",
            "A narrow forum where the old street into the Subura ran; columns stand close to the wall "
            "under a frieze of women's crafts and the myth of Arachne. The temple is Minerva's."),
        "pacis": card(L, "Templum Pacis", "Temple of Peace",
            "Vespasian's garden square with long water channels and flower beds, porticoes full of famous "
            "art, a library, and the spoils of Jerusalem, among them the menorah."),
        # --- the Palatine and the Circus ----------------------------------------------------
        "palatine_tiberiana": card(L, "Domus Tiberiana", "Palace of Tiberius",
            "The older palace on the Palatine's north edge, begun under Tiberius, its brick substructures "
            "rising high over the Forum."),
        "domus_flavia": card(L, "Domus Flavia", "The state palace",
            "Domitian's palace of state: a vast throne hall, a basilica, a dining hall between fountains "
            "and a peristyle round an octagonal fountain maze. The emperor receives the Senate here."),
        "domus_augustana": card(L, "Domus Augustana", "The emperor's residence",
            "The private palace, whose curved façade and high brick substructures look down over the "
            "Circus Maximus. Our word 'palace' comes from this hill, the Palatium."),
        "palatine_stadium": card(L, "Hippodromus Palatii", "The palace garden stadium",
            "A sunken garden shaped like a stadium, with porticoes, plane trees and fountains, for walks in "
            "the shade."),
        "apollo_palatinus": card(L, "Aedes Apollinis Palatini", "Temple of Apollo",
            "Augustus's temple of Luna marble beside his house, sacred to his patron god, with a famous "
            "Greek and Latin library."),
        "house_augustus": card(L, "Domus Augusti", "House of Augustus",
            "A modest house with painted rooms where the first emperor lived for forty years, preferring "
            "simplicity to palaces."),
        "casa_romuli": card(L, "Casa Romuli", "Hut of Romulus",
            "A small thatched hut of wattle and daub, piously rebuilt whenever it is damaged, where Romulus "
            "was said to have lived. Today is the city's birthday, and people bring garlands."),
        "lupercal": card(L, "Lupercal", "The wolf's cave",
            "A cave shrine at the foot of the Palatine where the she-wolf nursed Romulus and Remus. In "
            "February the Luperci run round the hill from here at the Lupercalia."),
        "circus_maximus": card(L, "Circus Maximus", "The great racecourse",
            "A long arena with tiered seats for some 150,000, shops in its outer arcades, twelve starting "
            "gates and a central barrier with Augustus's obelisk, seven bronze dolphins and seven eggs to "
            "count the laps. Four factions race: Red, White, Green and Blue."),
        "porta_capena": card(L, "Porta Capena", "The wet gate",
            "An old tufa gate of the Servian wall under an aqueduct branch, always dripping. The Via Appia "
            "begins here. Rome itself has no circuit wall in 126; carts wait here for dusk."),
        # --- the river ----------------------------------------------------------------------
        "portunus": card(L, "Aedes Portuni", "Temple of Portunus",
            "A small Ionic temple on a podium by the old river port, sacred to the god of harbours. It still "
            "stands."),
        "hercules_victor": card(L, "Aedes Herculis Victoris", "Round temple of Hercules",
            "A round temple of twenty white marble columns in the cattle market by the river, the oldest "
            "marble building in Rome to survive."),
        "ara_maxima": card(L, "Ara Maxima", "Great Altar of Hercules",
            "Where Hercules, the story goes, rested his cattle by the Tiber. Merchants vowed a tenth of "
            "their profits here."),
        "tiber_island": card(L, "Insula Tiberina", "Tiber Island",
            "The island is faced with travertine like a ship's prow and stern, with an obelisk for a mast. "
            "The healing god Aesculapius has his temple here; the sick sleep in its porticoes, hoping for "
            "a cure in a dream."),
        "pons_fabricius": card(L, "Pons Fabricius", "Bridge of Fabricius",
            "A stone bridge of 62 BC joining the island to the left bank. It is still in use."),
        "pons_cestius": card(L, "Pons Cestius", "Bridge of Cestius",
            "The stone bridge of the first century BC from the island to Transtiberim, the quarter across the Tiber, rebuilt many "
            "times since."),
        "pons_aemilius": card(L, "Pons Aemilius", "The first stone bridge",
            "Rome's first stone bridge, carrying the road from the cattle market across to Transtiberim and "
            "the Via Aurelia."),
        "pons_sublicius": card(L, "Pons Sublicius", "The wooden bridge",
            "The oldest bridge, always rebuilt in wood: no iron may be used in it. Here, the story goes, "
            "Horatius held off the Etruscan army."),
        "horrea_galbana": card(L, "Horrea Galbana", "The grain warehouses",
            "Long warehouses round courtyards where grain brought up the Tiber from Portus is measured, "
            "recorded and stored for the monthly distribution and the bakers."),
        "testaccio": card(L, "Mons Testaceus", "The mound of sherds",
            "A hill made of broken oil amphorae from southern Spain, emptied at the wharf, smashed and "
            "laid in lime. It is about half its later height and will keep growing until the third "
            "century."),
        "emporium": card(L, "Emporium", "The river port",
            "A travertine wharf with mooring posts, treadwheel cranes and stacked amphorae, the warehouse "
            "rows of the Porticus Aemilia behind it. Barges towed up from Portus unload grain, oil, wine "
            "and marble here. The great vaulted Porticus is shown as rows of warehouses."),
        "marcellus": card(L, "Theatrum Marcelli", "Theatre of Marcellus",
            "Augustus's theatre for his nephew, its curved travertine façade of arcades in Doric and Ionic "
            "storeys. Some 15,000 people watch comedies and mimes here."),
        "octavia": card(L, "Porticus Octaviae", "Portico of Octavia",
            "A colonnaded precinct round temples of Jupiter and Juno, full of Greek art. Pliny saw a seated "
            "statue of Cornelia, mother of the Gracchi, in a portico of this area."),
        # --- the Campus Martius -------------------------------------------------------------
        "pantheon": card(L, "Pantheum", "The Pantheon",
            "Hadrian has just rebuilt it: sixteen granite columns, Agrippa's name kept in the inscription, "
            "and a brick rotunda under a dome 43 metres across, covered in bronze tiles and open to the sky "
            "through its oculus. It is still the largest unreinforced concrete dome."),
        "pantheon_court": card(L, "Area Panthei", "The Pantheon's forecourt",
            "A colonnaded court before the portico, where the Pantheon is entered. Seen from here the rotunda "
            "hides behind the tall temple front."),
        "matidia": card(L, "Templum Matidiae", "Temple of Matidia",
            "Hadrian's temple to his deified mother-in-law, Matidia, built after 119 beside the Pantheon: the "
            "first temple in Rome to a deified woman of the imperial family, some think."),
        "agrippa_baths": card(L, "Thermae Agrippae", "Baths of Agrippa",
            "Rome's first great public baths, with a domed hall, vaulted rooms and an exercise yard, beside "
            "the Stagnum, an artificial lake fed by the Aqua Virgo."),
        "saepta": card(L, "Saepta Iulia", "Shops where Romans once voted",
            "Built for the people's voting assemblies, the long colonnaded hall now holds luxury shops. "
            "Its building is not drawn yet: you see its paved court lined with stalls and columns."),
        "iseum": card(L, "Iseum Campense", "Sanctuary of Isis and Serapis",
            "An Egyptian-style sanctuary with obelisks and sphinxes, where shaven priests in linen shake "
            "the sistrum. Its buildings are not drawn yet: a paved court with columns and an altar stands "
            "in for it."),
        "stadium_domitian": card(L, "Stadium Domitiani", "Domitian's stadium",
            "A stadium for Greek-style athletic contests; its shape survives as the Piazza Navona. Here "
            "you see its long arena of trampled earth with statues along the middle."),
        "pompey_theatre": card(L, "Theatrum Pompei", "Theatre of Pompey",
            "Rome's first stone theatre, with a temple of Venus Victrix on top of the seating and a great "
            "portico garden behind its stage, where Caesar was killed. Shown as its paved half-round and "
            "the garden's plane trees."),
        "trajan_baths": card(L, "Thermae Traiani", "Baths of Trajan",
            "Apollodorus built these vast baths on the Oppian in 109: great halls round a central block, "
            "exedrae, exercise yards and gardens in a walled precinct. Its hall is not drawn yet: you see "
            "a paved block of vaulted bath halls with yards and gardens."),
        "tarpeian": card(L, "Saxum Tarpeium", "The Tarpeian rock",
            "The sheer tufa cliff of the Capitol over the Velabrum, from which traitors were thrown in the "
            "old Republic."),
        "aqua_claudia": card(L, "Aqua Claudia", "The aqueduct",
            "Tall arches of rusticated tufa and brick carry Nero's branch of the Claudia across the Caelian "
            "to the Palatine. Rome has ten aqueducts in 126; the curator of the waters and his public slaves "
            "keep them running."),
        "castra_praetoria": card(L, "Castra Praetoria", "Camp of the Praetorians",
            "The walled brick camp of the emperor's guard, some ten thousand men, on the edge of the city. "
            "Guards drill outside its gates."),
        "suburban_villa": card(L, "Villa suburbana", "A villa on the Via Appia",
            "A rich family's country house with its vineyard and kitchen gardens just outside the city, run "
            "by a steward."),
        "synagogue": card(L, "Synagoga", "A synagogue of Transtiberim",
            "Rome's Jews had their own synagogues and burial places, and one community lived across the "
            "Tiber. Its form is not known from excavation, so it is shown as a modest house."),
    }
    c.update(figure_cards(F))
    c.update(idea_cards(I))
    c.update(role_cards(RO))
    c.update(event_cards(EV))
    return c


def figure_cards(F) -> dict:
    return {
        "hadrian": card(F, "Hadrianus", "Emperor and traveller",
            "He has walked the empire from Britain, where his wall is being built, to Syria. Back in Rome "
            "he is rebuilding the Pantheon and designing a temple to Venus and Roma himself; his portraits "
            "always show a full beard. Where he spent 21 April 126 is not recorded: the game imagines him "
            "here for the festival."),
        "sabina": card(F, "Vibia Sabina", "Augusta",
            "Trajan's grand-niece and Hadrian's wife, she travelled with him across the provinces and "
            "received the title Augusta. Coins carry her portrait and her high coiled hairstyle, copied by "
            "fashionable women. Whether she was in Rome today is not recorded; the game imagines her here."),
        "antinous": card(F, "Antinous", "Of Bithynia",
            "A youth from Bithynia, beloved of Hadrian and with him from about 124. After his death in the "
            "Nile in 130, Hadrian made him a god and founded a city in his name. His presence in Rome in "
            "126 is likely but not recorded: today the game has him riding out."),
        "marcus": card(F, "Marcus Annius Verus", "Nearly five",
            "Born on the Caelian, this serious little boy turns five on 26 April. Hadrian will call him "
            "'Verissimus', most truthful. In 161 he becomes emperor as Marcus Aurelius and writes, in Greek, "
            "a private book of reflections that people still read. Today he watches the procession."),
        "apollodorus": card(F, "Apollodorus of Damascus", "Architect",
            "He built Trajan's Forum, Column and Baths and a bridge over the Danube. Cassius Dio, writing a "
            "century later, says he mocked Hadrian's design for Venus and Roma and paid with exile and "
            "death; many historians think the story gossip. Whether he was in Rome in 126 is unknown."),
        "juvenal": card(F, "Iuvenalis", "Satirist",
            "He hates the noise: carts at night, crowds by day, tiles falling from tall blocks, rich patrons "
            "who keep clients waiting at dawn. He said the people want only two things, bread and circuses. "
            "You will find him grumbling in the Subura or in a morning queue."),
        "suetonius": card(F, "Suetonius Tranquillus", "Biographer",
            "Once Hadrian's secretary for letters, now writing lives of the Caesars full of habits, sayings "
            "and scandal. He was dismissed about 122, the story goes, for a lapse of manners toward the "
            "empress. He works among the books of Trajan's libraries."),
        "mesomedes": card(F, "Mesomedes", "Court musician",
            "A freed lyre-singer from Crete who composes hymns for Hadrian. Some of his songs survive with "
            "their melodies written above the words, among the very few ancient tunes we can still read "
            "and sing. In the evenings he plays in the palace gardens."),
        "soranus": card(F, "Soranus of Ephesus", "Physician",
            "Trained in Alexandria, he practises in Rome and writes about childbirth, the care of mothers "
            "and newborns, and what makes a good midwife. His book was copied and used for more than a "
            "thousand years. You may find him among the sick on the island."),
        "diocles": card(F, "Gaius Appuleius Diocles", "Charioteer",
            "A driver of twenty-two from Lusitania who began racing in 122. By the end of his career his "
            "monument will list 1,462 victories and a fortune greater than many senators'. This year he "
            "drives four horses for the Whites."),
        "vestalis_maxima": card(F, "Virgo Vestalis Maxima", "Keeper of the fire",
            "The senior of the six women who guard Vesta's fire and Rome's sacred objects for thirty years "
            "each. They have seats of honour at the games, may free a condemned man they meet by chance, "
            "and keep the wills of emperors. Her name in 126 is not known."),
        "plotina": card(F, "Pompeia Plotina", "Trajan's widow (a memory)",
            "Praised for her modesty and her learning, she backed Hadrian's succession when Trajan died and "
            "supported the Epicurean school in Athens. She died about 122, and Hadrian honoured her with a "
            "temple. At dusk she seems to walk again in her husband's forum."),
        "trajan": card(F, "Traianus", "The best emperor (a memory)",
            "The Senate called him optimus princeps, the best of rulers. Conqueror of Dacia, builder of "
            "this forum, its markets and the harbour at Portus, he died in 117. His Column tells his wars "
            "in 2,500 figures and his ashes rest in its base; at dusk his memory stands beside it."),
        "numa": card(F, "Numa Pompilius", "The peaceful king (a memory)",
            "Rome's second king, by legend, gave the city its priests, its calendar and the cult of Vesta, "
            "advised, they said, by the nymph Egeria in a sacred grove. The Regia was called his house. At "
            "dusk a bearded king seems to pass between the Regia and the fire."),
        "scipio": card(F, "Scipio Africanus", "Victor over Hannibal (a memory)",
            "Before any public business, Livy says, he climbed to Jupiter's temple and sat there alone with "
            "the god, and some Romans whispered he was Jupiter's son. He defeated Hannibal at Zama in 202 "
            "BC. Before dawn his memory still sits at the Capitolium."),
        "caesar": card(F, "Divus Iulius", "Dictator (a memory)",
            "Gaius Julius Caesar, conqueror of Gaul and dictator, was killed by senators in 44 BC. The "
            "people burned his body here in the Forum, and on that spot rose his temple, the first to a "
            "Roman made a god. At dusk his memory stands by it, wreathed in laurel."),
        "cicero": card(F, "Marcus Tullius Cicero", "Orator (a memory)",
            "The greatest speaker of the Republic spoke from these Rostra against Catiline and Mark Antony. "
            "After his murder in 43 BC, Antony had his head and hands fixed here. At dusk he still seems to "
            "speak, silently, to the emptying Forum."),
        "dioscuri": card(F, "Castor et Pollux", "The divine twins",
            "After the battle of Lake Regillus, the story goes, two young riders were seen watering their "
            "horses at Juturna's spring, announcing the victory, then vanishing. Rome built them a temple "
            "beside the spring. Very rarely, at dawn, two riders seem to stand there."),
        "aeneas": card(F, "Aeneas", "Ancestor of Rome (a statue)",
            "Son of Venus, he carried his father Anchises out of burning Troy and led his son Ascanius to "
            "Italy, the poet Virgil tells. Augustus placed this statue group in his forum, facing Romulus, "
            "at the beginning of Rome's story and his own family's."),
        "romulus": card(F, "Romulus et Remus", "Sons of Mars (a statue and a shrine)",
            "Set adrift on the flooded Tiber, the twins were nursed by a she-wolf in the Lupercal cave below "
            "the Palatine. Romulus founded the city on 21 April, traditionally in 753 BC: today is its "
            "birthday. His statue stands in the Forum of Augustus, carrying a defeated king's armour."),
        "cloelia": card(F, "Cloelia", "The girl who swam the Tiber (a statue)",
            "A hostage of the Etruscan king, she escaped across the river with other girls, and Rome honoured "
            "her with a statue on horseback on the Via Sacra. Whether one stood here in 126 is uncertain: "
            "Dionysius found the old one gone, and some said it showed Valeria."),
        "cornelia": card(F, "Cornelia", "Mother of the Gracchi (a statue)",
            "Daughter of Scipio Africanus, she refused a king, educated her children herself and called her "
            "sons, the reformers Tiberius and Gaius Gracchus, her jewels. Pliny saw her seated statue in a "
            "portico here; an inscribed base survives, though where it stood is debated."),
        "claudia_helpis": card(F, "Claudia Helpis", "Innkeeper",
            "Born a slave, freed by her mistress, Claudia Helpis now runs her own counter of hot chickpeas, "
            "lentils, wine and bread in the Subura. Freed men and women ran a large share of Rome's shops, "
            "and many proudly carved their trade on their tombs."),
        "vibius_primus": card(F, "Lucius Vibius Primus", "Baker",
            "Primus's donkeys turn the lava mills before dawn; by sunrise the loaves are stamped with his "
            "mark. Each month the state hands out free grain to some two hundred thousand citizens, and "
            "many of them bring it to bakers like him."),
        "aelius_eutyches": card(F, "Publius Aelius Eutyches", "Clerk of the grain office",
            "An imperial freedman, he counts the grain ships' cargoes for the prefect of the grain supply "
            "and checks the warehouses' tallies at the Horrea Galbana. Under Hadrian more senior posts went to equestrians, but "
            "freedmen still ran the daily paperwork of the empire."),
        "apion": card(F, "Apion", "Sailor from Egypt",
            "Apion came from a village in Egypt and joined the fleet. In a real letter, a recruit of that "
            "name told his father he had arrived safely at Misenum and been given a Roman name. Today he "
            "has come up the river on a grain barge."),
        "mulvius": card(F, "Quintus Mulvius", "Barge master",
            "Mulvius steers a barge up the Tiber from Portus, towed by men and oxen on the bank path: a few "
            "days against the current for some thirty-five kilometres, much quicker back down with the "
            "stream. He knows every sandbank between Portus and the Emporium."),
        "flavius_valens": card(F, "Titus Flavius Valens", "Fireman of the watch",
            "Valens walks the streets at night with buckets, axes and blankets. Fire is the great terror of "
            "a city of wooden floors and oil lamps. A law let informally freed slaves who served six years "
            "in the watch, later three, earn full citizenship."),
        "felicula": card(F, "Felicula", "A fuller's daughter",
            "Felicula fetches water from the fountain twice a day and plays with walnuts on the pavement "
            "with her brother. Her mother dyes cloth; her father treads it clean in the vats. More than "
            "anything she wants to see the races."),
        "rufina": card(F, "Rufina", "Weaver",
            "Rufina's family has lived across the Tiber for generations among dockers, potters and traders "
            "from the East. Rome's Jews had their own synagogues and burial places; the Arch of Titus, with "
            "its spoils of Jerusalem, is not a monument they love."),
        "sextus": card(F, "Sextus", "Litter-bearer",
            "Sextus, from Thrace, carries his master's litter across the city every morning with seven "
            "others. Rome had no uniform for slaves: the Senate once rejected one, Seneca says, in case the "
            "slaves saw how many they were. In the afternoons he runs errands for the household."),
        "iulia_ianuaria": card(F, "Iulia Ianuaria", "Midwife",
            "Ianuaria has delivered half the children of her street. Soranus wrote that a good midwife must "
            "be literate, calm, and have soft hands and short nails. Inscriptions remember several Roman "
            "midwives by name. She walks her rounds on the Aventine."),
    }


def idea_cards(I) -> dict:
    return {
        "law": card(I, "Ius", "Roman law",
            "In the Basilica Iulia advocates plead before the centumviral court, and jurists give written "
            "opinions on hard cases. Roman law grew from statutes, the praetors' yearly edicts and those "
            "opinions into a body of rules and reasoning that later Europe studied again. Hadrian will "
            "soon have the jurist Salvius Iulianus fix the praetor's edict in a permanent form, about 130."),
        "concrete": card(I, "Opus caementicium", "Roman concrete",
            "Lime mortar mixed with volcanic ash, dug round Rome and named for Puteoli near Naples, sets "
            "hard, even under water. Poured "
            "with rubble behind neat brick faces, it let Romans vault halls and baths of a size no one had "
            "built before. The Pantheon's dome uses lighter stone toward the top; it is still the largest "
            "unreinforced concrete dome in the world."),
        "aqueducts": card(I, "Aquae", "Water for a million",
            "Ten aqueducts bring water to Rome in 126, the newest Trajan's of 109, some in channels more "
            "than eighty kilometres long. The water runs down gentle slopes in covered channels, crosses "
            "valleys on arcades, and ends in settling tanks and distribution towers that feed fountains, "
            "baths and the few houses granted a private pipe. Most Romans carry theirs from a street "
            "fountain."),
        "cursus_publicus": card(I, "Cursus publicus", "Roads and the state post",
            "Paved roads run from Rome to every province, measured by milestones from the Golden Milestone "
            "in the Forum. Along them the state post keeps relay stations where official couriers change "
            "mules and horses, with inns nearby. The Via Appia, begun in 312 BC, runs from the Porta Capena "
            "all the way to Brundisium."),
        "calendar": card(I, "Fasti", "The Julian calendar",
            "Caesar reformed Rome's muddled calendar in 46 BC with the help of Greek astronomers: 365 days "
            "and a leap day every fourth year. Days are counted back from the Kalends, Nones and Ides, and "
            "each is marked for business or for the gods. Today, the eleventh day before the Kalends of "
            "May, is the Parilia."),
        "maps": card(I, "Orbis pictus", "Agrippa's map of the world",
            "Augustus's friend Agrippa had the known world drawn and set up in a portico on the Campus "
            "Martius, so that Romans could see their empire from Britain to the Euphrates. It has not "
            "survived; ancient writers who used it describe its distances and provinces."),
        "greek_learning": card(I, "Paideia", "Greek learning in Rome",
            "Educated Romans speak Greek as well as Latin. Greek teachers, doctors, architects and musicians "
            "fill the city, and Hadrian himself loves Greek culture and wears a Greek-style beard. Children "
            "of good families learn Homer with a Greek tutor and rhetoric from a master."),
        "literature": card(I, "Litterae", "Books and libraries",
            "Books are papyrus rolls copied by hand, sold in shops near the Forum and read aloud. Trajan's "
            "Forum has a Greek and a Latin library facing the Column. Juvenal writes his satires and "
            "Suetonius his lives of the Caesars in these years."),
        "annona": card(I, "Annona", "The grain supply",
            "Rome eats far more grain than Italy grows. The prefect of the grain supply brings it by sea "
            "from Egypt, Africa and Sicily to Portus, then by barge up the Tiber to the warehouses. Each "
            "month some two hundred thousand citizens holding a token collect five measures of free grain."),
        "night_carts": card(I, "Plaustra nocturna", "Carts only by night",
            "A law of Caesar's time banned heavy carts from the city's streets for most of the day, probably "
            "until the tenth hour, except for public building work and a few sacred processions. So the "
            "carts wait at the gates and come rumbling in at dusk, and Juvenal complains that no one can "
            "sleep."),
        "baths": card(I, "Thermae", "The baths",
            "For a small coin anyone may bathe: undress, exercise in the yard, sweat in the hot rooms, soak "
            "in the warm, plunge in the cold, and be oiled and scraped with a strigil. The baths fill after "
            "the eighth hour. Hadrian, says the Historia Augusta, separated men's and women's bathing."),
        "factions": card(I, "Factiones", "Red, White, Green and Blue",
            "Chariot teams race for four companies known by their colours, and all Rome takes sides. Four "
            "horses run seven laps round the barrier; a dolphin tips at each lap. Star drivers, most of "
            "them slaves or freedmen, grow rich and famous."),
        "amphitheatre_games": card(I, "Munera", "Games in the amphitheatre",
            "On game days crowds file in through numbered arches, the awning is drawn, and the water organ "
            "and horns play. Gladiators fight in pairs of different arms, and wild animals from Africa are "
            "hunted. The game shows only the outside and the sounds."),
        "religion": card(I, "Religio", "Gods and rites",
            "Romans keep peace with the gods by doing things right: a prayer said exactly, an animal "
            "offered with music, the entrails read. Every house has its Lares, every crossroads a shrine, "
            "and the city honours its own gods beside Isis, Cybele, Mithras and the emperors made divine."),
        "sacrifice": card(I, "Sacrificium", "A sacrifice",
            "The priest covers his head, a piper plays the tibia so no ill-omened sound is heard, wine and "
            "incense go on the fire, and the victim is struck. Its entrails are inspected for signs; the "
            "meat is cooked and shared. Sacrifice is how Rome talks to its gods."),
        "parilia": card(I, "Parilia", "Rome's birthday",
            "The Parilia was the shepherds' feast of Pales, kept on 21 April, the day Romulus founded the "
            "city. The flocks are smoked clean at twilight and young people leap the burning straw. Hadrian's "
            "coins of 121 celebrate the city's 874th birthday with games, and by about AD 200, Athenaeus "
            "says, the day was 'now called' the Romaia."),
        "freedmen": card(I, "Liberti", "Freed men and women",
            "Slaves in Rome were often freed, by will or by purchase. Freed men and women took their former "
            "owner's family name, became citizens, ran shops and workshops, and some grew rich; their "
            "children were born free. Many proudly recorded their trades on their tombs."),
        "housing": card(I, "Insulae", "Apartment blocks",
            "Most Romans rent rooms in brick apartment blocks of four or five storeys, shops on the ground "
            "floor and the cheapest rooms at the top, without water or kitchens. Trajan limited their height "
            "to sixty feet; fires and collapses were feared, as Juvenal complains."),
    }


def role_cards(RO) -> dict:
    def rc(title, text):
        return card(RO, title, "", text)
    return {
        "plebs": rc("Plebs", "Ordinary citizens in coloured or undyed tunics: shopkeepers, craftsmen, labourers and "
                    "clients. The toga is for formal business and the games."),
        "client": rc("Cliens", "A citizen who owes his patron loyalty and his vote, and gets help, food or a little "
                     "money in return. He calls at dawn in his toga and follows the patron to the Forum."),
        "senator": rc("Senator", "Broad purple stripes on his tunic, a white toga, black senatorial shoes and often "
                      "a short beard in Hadrian's fashion. Clients and slaves follow him."),
        "lictor": rc("Lictor", "An attendant carrying the fasces, a bundle of rods, ahead of a magistrate. Inside "
                     "the city the axe is taken out of the bundle."),
        "advocate": rc("Advocatus", "A speaker in a toga pleading a case about an inheritance before the "
                       "centumviral court in the Basilica Iulia."),
        "gaming_board": rc("Tabula lusoria", "Idlers scratched gaming boards into the basilica's steps and played "
                           "with counters while the courts sat inside."),
        "rostra_speaker": rc("From the Rostra", "Magistrates and orators address the crowd from the speakers' "
                             "platform, as the great men of the Republic did."),
        "school": rc("Ludus", "A schoolmaster teaches reading, writing and sums to a few pupils with wax tablets "
                     "under an awning in the Forum, from dawn until midday."),
        "seller": rc("Venditrix", "A woman selling from a shop or stall, one of the many women who kept Rome's "
                     "small trade going."),
        "porter": rc("Baiulus", "A porter carrying loads through streets where carts may not go by day."),
        "enslaved": rc("Servus", "Perhaps a fifth to a third of Rome's people are enslaved. They wear no special "
                       "dress; you know them only by the work they are made to do."),
        "matron": rc("Matrona", "A married woman in a long stola with her mantle drawn over her head outside, her "
                     "hair dressed high in the empress's fashion."),
        "vestals_order": rc("Virgines Vestales", "Six priestesses in white with woollen bands who tend Vesta's "
                            "fire, fetch water from a spring and prepare the sacred salt meal."),
        "flamen": rc("Flamen", "A priest of one god, in a heavy cloak and the apex, a cap topped with a spike of "
                     "olive wood."),
        "ara_maxima_rite": rc("At the Great Altar", "Rites for Hercules at his altar by the cattle market; merchants "
                              "vow him a tenth of their profits."),
        "urban_cohort": rc("Cohortes urbanae", "Soldiers of the urban cohorts keep order in the streets under the "
                           "Prefect of the City. In the city they usually go without armour."),
        "syrian": rc("Syrus", "A merchant from Syria in a long tunic and mantle, trading in glass, purple cloth, "
                     "dates and balsam."),
        "freedman": rc("Libertus", "A freed man or woman running a shop: Rome's small trade was largely in their "
                       "hands."),
        "tabularium_clerk": rc("Scriba", "Clerks of the record office climb to the Capitol to copy and file the "
                               "state's documents."),
        "geese": rc("Anseres Iunonis", "Juno's sacred geese, kept on the Capitol since they cackled a warning when "
                    "the Gauls climbed the hill by night."),
        "mason": rc("Faber", "Masons set marble drums and capitals in the peristyle of the new temple."),
        "treadwheel": rc("Magna rota", "Men walk inside a great wooden wheel to wind the rope of a crane and lift "
                         "blocks that weigh several tonnes."),
        "bricklayer": rc("Structor", "Gangs lay the brick facing and pour mortar and rubble behind it: Roman concrete "
                         "walls rising course by course."),
        "labourer": rc("Operarius", "Free and enslaved labourers fetch bricks, mortar and rubble for the building "
                       "site."),
        "site_cart": rc("Plaustrum", "Ox carts for public building may run by day; most other heavy carts must wait "
                        "for dusk."),
        "fountain": rc("Lacus", "Street fountains stand every few blocks, running day and night; women and children "
                       "fetch water and news there."),
        "praetorian": rc("Praetoriani", "The emperor's guard, some ten thousand men camped at the Castra Praetoria, "
                         "posted at the palace in shifts."),
        "german_guard": rc("Equites singulares", "Horsemen of the emperor's own mounted guard, many recruited from "
                           "Germanic peoples of the Rhine frontier."),
        "courtier": rc("Amicus principis", "Friends and officials of the emperor waiting on business at the palace."),
        "gardener": rc("Topiarius", "A gardener clipping box and bay into shapes and keeping the roses of a great "
                       "house."),
        "stables": rc("Stabula", "Stable hands groom, feed and harness the racehorses of the four factions near the "
                      "starting gates."),
        "docker": rc("Saccarius", "Dockers carry sacks and amphorae from the barges to the warehouses; they had "
                     "their own guilds."),
        "horrea_clerk": rc("Horrearius", "A clerk who measures, records and seals each load of grain that enters the "
                           "warehouse."),
        "testaccio_work": rc("On the mound", "Workers break emptied oil amphorae and lay the sherds in neat terraces, "
                             "sprinkled with lime against the smell."),
        "warehouse": rc("Horrea", "Warehouse porters move amphorae of oil and wine between the wharf, the stores and "
                        "the decanting floor."),
        "hauler": rc("Helciarius", "Men and oxen on the bank path haul barges upstream from Portus on long tow "
                     "ropes."),
        "egypt": rc("Aegyptius", "Egyptian sailors crew the grain ships that bring perhaps a third of Rome's bread "
                    "across the sea."),
        "swallows": rc("Hirundines", "The swallows are back with the spring, swooping over the river and the "
                       "rooftops."),
        "cattle_market": rc("Forum Boarium", "Cattle are driven in to the market by the river, as they have been "
                            "since the city was young."),
        "aesculapius": rc("Incubatio", "The sick sleep in the porticoes of Aesculapius on the island, hoping the god "
                          "will send a cure in a dream."),
        "baker": rc("Pistor", "The baker kneads, shapes, stamps and bakes before dawn; donkeys turn his lava mills."),
        "mill_donkey": rc("Asinus", "Blindfolded donkeys walk round and round, turning the hourglass-shaped lava mills "
                          "that grind the grain."),
        "fuller": rc("Fullo", "Fullers tread cloth in vats of water, fuller's earth and stale urine, then rinse, "
                     "brush and dry it."),
        "dyer": rc("Infector", "Dyers soak cloth in vats of madder red, woad blue or saffron yellow; true purple "
                   "comes only from Tyre."),
        "glass": rc("Vitrearius", "A glassblower gathers molten glass on a pipe and blows cups and flasks, a craft "
                    "come from Syria."),
        "smith": rc("Faber ferrarius", "A smith at his forge making nails, tools, hinges and fittings for the quarter."),
        "taberna": rc("Taberna", "A shop open to the street with a masonry counter, closed at night with wooden "
                      "shutters, selling bread, oil, cloth or lamps."),
        "thermopolium": rc("Thermopolium", "A street counter with sunk jars of hot food and wine; most flats have no "
                           "kitchen, so people eat here."),
        "weaver": rc("Textrix", "A woman weaving wool at home, one of the many who made Rome's cloth."),
        "stoker": rc("Fornacator", "Slaves feed the bath furnaces with wood from before dawn to keep the hot rooms hot."),
        "vigiles": rc("Vigiles", "Seven cohorts of firemen and night watchmen, with buckets, axes, hooks and blankets "
                      "soaked in vinegar."),
        "women": rc("Mulieres", "Women fetch water, shop, work at looms and counters, visit neighbours and keep the "
                    "household going."),
        "children": rc("Pueri et puellae", "Children play with walnuts, knucklebones and hoops in the street; boys "
                       "wear a bulla, girls a lunula."),
        "salutatio": rc("Salutatio", "At dawn clients in togas queue at their patrons' doors for the morning greeting, "
                        "a little gift and the day's business."),
        "litter": rc("Lectica", "A curtained litter carried by eight slaves, the way the rich cross the crowded city "
                     "by day."),
        "popina": rc("Popina", "Late diners and drinkers leave the street counters with lamps; the night watch keeps "
                     "an eye on them."),
        "dogs": rc("Canes", "Dogs guard doors (cave canem, says the mosaic) and roam the streets for scraps."),
        "cats": rc("Feles", "Cats have become common in Roman houses and shops, good at keeping mice from the grain."),
        "aquarius": rc("Aquarius", "Public slaves of the water office clear channels, patch pipes and open the "
                       "valves."),
        "synagogue_community": rc("Iudaei", "Jews of the Transtiberim community trade, weave and worship in their "
                                  "own synagogues across the river."),
        "gaul": rc("Gallus", "A trader from Gaul in trousers and a hooded cloak, selling wine and woollen cloaks."),
        "moor": rc("Maurus", "A Moorish horseman from Africa; Moorish cavalry under Lusius Quietus served in Trajan's wars."),
        "theatre": rc("Theatrum", "Comedies, mimes and pantomime dancers draw crowds to the theatres of the Campus "
                      "Martius."),
        "farmer": rc("Agricola", "Farmers and tenants work the market gardens, fields and olive yards round the city."),
        "vinedresser": rc("Vinitor", "Vine-dressers prune, tie and hoe the vines on the hills outside the city."),
        "villa": rc("Vilicus", "The steward of a villa, often himself a slave, runs the estate for its owner."),
        "shepherd": rc("Pastor", "Shepherds bring their flocks to graze on the hills and the Campagna; the Parilia is "
                       "their festival."),
        "tombs": rc("Sepulcra", "Burial is forbidden inside the city, so tombs line the roads leading out of it; "
                    "families visit with offerings."),
        "mules": rc("Muli", "Pack mules carry loads by day, when carts are banned from the streets."),
        "fish_market": rc("Piscator", "River fishermen land their catch for the stalls of the cattle market."),
        "legions": rc("Milites", "The legions are on the frontiers; in Rome you see veterans, recruits and soldiers "
                      "on errands."),
        "compitum": rc("Compitum", "A shrine of the Lares at a crossroads, tended by the neighbourhood's magistrates; "
                       "its lamp is lit at dusk."),
        "graffiti": rc("Inscriptiones", "Walls carry painted notices and scratched graffiti: election appeals, jokes, "
                       "love notes and insults."),
        "performer": rc("Circulator", "A juggler or piper draws a small ring of watchers in a portico."),
        "starlings": rc("Sturni", "At dusk flocks of birds wheel over the Tiber before settling for the night."),
        "weather_april": rc("April showers", "A spring shower: gutters spout, warm paving steams, and sometimes a "
                            "rainbow stands over the Palatine."),
        "nundinae": rc("Nundinae", "Market day, every eighth day in Rome: farmers come in, stalls fill the squares, "
                       "and in the game the races follow in the afternoon."),
        "senate": rc("Senatus", "Senators with lictors and clients arrive at the Curia for a session."),
        "wedding": rc("Nuptiae", "At dusk the bride is led to her new home by torchlight, pipers playing, nuts thrown "
                      "to the children."),
        "night_cart_role": rc("Plaustrarius", "A carter bringing building stone and goods into the city by night."),
        "cursus_role": rc("Viator", "A traveller on the Via Appia, resting at the relay stations between Rome and the south."),
    }


def event_cards(EV) -> dict:
    return {
        "parilia_rite": card(EV, "The shepherds' rite", "",
            "Ovid tells it: at twilight the fold is swept and the ground sprinkled with water, green boughs "
            "hung up, and the sheep purified with smoke of sulphur, olive wood, pine and juniper. The "
            "shepherd prays to Pales four times, facing the east, and washes his hands in dew."),
        "romaia": card(EV, "The birthday procession", "",
            "In the morning the priests, the Vestals and the Senate walk from the Forum to the new temple of "
            "Venus and Roma, begun on this day in 121, for a sacrifice. Hadrian and Sabina lead it, as the "
            "game imagines them here."),
        "vinalia": card(EV, "Vinalia", "", "On 23 April the first wine of last year's vintage is offered to "
                        "Jupiter on the Capitol before anyone may drink it."),
        "vestalia": card(EV, "Vestalia", "", "In June Vesta's temple is opened to women, who walk barefoot to it; "
                         "bakers rest and their donkeys wear garlands."),
        "saturnalia": card(EV, "Saturnalia", "", "In December masters serve their slaves at table, everyone wears "
                           "the freedman's felt cap, and friends give candles and clay figurines."),
    }


STRINGS = {
    "first_visit": "21 April, AD 126: Rome's birthday. The Pantheon is new, the Temple of Venus and Roma is "
                   "rising on the Velia, and at dusk the shepherds' fires of the Parilia are lit.",
    "parilia_dawn": "Dawn on the Parilia: on the Janiculum the shepherds pray to Pales, facing the east.",
    "parilia_fumigants": "People fetch the ashes for their fumigations from Vesta's temple.",
    "parilia_procession": "The birthday procession leaves the Forum for the Temple of Venus and Roma.",
    "pompa": "The procession of the games leaves the Capitol for the Circus.",
    "races": "The races begin: four teams, seven laps.",
    "parilia_purification": "Twilight: the folds are swept and the flocks purified with smoke.",
    "bonfires": "The young leap three times over the burning straw.",
    "salutatio": "Dawn: clients queue at their patrons' doors for the morning greeting.",
    "trial": "A case is being heard in the Basilica Iulia.",
    "senate": "Senators are arriving at the Curia.",
    "market_day": "Market day: farmers have come in and the stalls are full.",
    "arena": "Horns and the water organ: a game day at the amphitheatre.",
    "dole": "Citizens with tokens queue for their monthly grain.",
    "grain_fleet": "A grain barge has come up the Tiber from Portus.",
    "vestals": "The senior Vestal walks to the Circus with her lictor.",
    "guard": "The guard is changed at the palace.",
    "night_carts": "Dusk: the carts kept out by day rumble in through the gate.",
    "fire": "Fire in an apartment block: the watch runs with buckets.",
    "funeral": "A funeral leaves the gate for the tombs of the Via Appia.",
    "wedding": "Torches and pipes: a bride is led to her new home.",
    "decorate_zone": "A peristyle garden of a house on the Caelian, waiting for box hedges, roses and a fountain.",
}

# The activity maps the report renders (`build.sh --city rome --preview`): dawn, mid-morning,
# afternoon, twilight and deep night.
PANELS = [("dawn", 5.5), ("mid-morning", 10.0), ("afternoon", 15.5), ("twilight", 19.5), ("deep night", 1.5)]


# Multipliers on the engine's phase grade ([1, 1, 1] = the corner), chosen as Athens' and Pārsa's
# were: the earlier absolute-looking values (dusk blue 0.60) gave an all-orange dusk in the engine
# (out/qa4/shots/V-D-005_rome_grading.png). Pink-gold dawn on travertine, a warm neutral day for
# brick and green, Rome's honey-gold dusk without the orange cast, a mild blue night whose warm
# points come from the glow layers. The Roman towns share it.
GRADING = {"dawn": [1.03, 0.97, 0.93], "day": [1.02, 1.0, 0.96], "dusk": [1.03, 0.95, 0.87],
           "night": [0.96, 0.97, 1.04]}


def theme(view) -> dict:
    return {
        "grading": GRADING,
        "haze": {"colour": [0.95, 0.89, 0.79], "strength": 0.13, "toward": "west",
                 "note": "bakery and bath-furnace smoke, stronger in the afternoon"},
        "weather": {
            "spring": {"showers": 2, "clouds": 2, "wind": 0.35, "wind_from": "west", "fog": 0.3,
                       "note": "April: mild days, spring showers, the Favonius in the afternoons, mist on the Tiber at dawn"},
            "summer": {"showers": 0, "clouds": 1, "wind": 0.3, "wind_from": "west",
                       "note": "hot and clear; thunderstorms over the hills inland"},
            "autumn": {"showers": 3, "clouds": 3, "wind": 0.4, "note": "rain returns"},
            "winter": {"showers": 3, "clouds": 4, "wind": 0.45, "snow": 0,
                       "note": "rain and cold clear days; no snow in the city"}},
        "ambience": {
            "beds": [{"file": "amb/rome/day.ogg", "hours": ["05:30", "19:30"]},
                     {"file": "amb/rome/night.ogg", "hours": ["19:30", "05:30"]}],
            "zones": [{"rect": grid_rect(view, "forum"), "file": "amb/rome/forum.ogg", "gain": 0.8,
                       "hours": ["06:00", "19:00"], "count_driven": {"roles": ["forum_crowd", "client"], "full": 14}},
                      {"rect": grid_rect(view, "fora"), "file": "amb/rome/forum.ogg", "gain": 0.6,
                       "hours": ["06:30", "19:00"]},
                      {"rect": grid_rect(view, "emporium"), "file": "amb/rome/river.ogg", "gain": 0.8},
                      {"rect": grid_rect(view, "river"), "file": "amb/rome/river.ogg", "gain": 0.6},
                      {"rect": grid_rect(view, "janiculum"), "file": "amb/world/fields.ogg", "gain": 0.6,
                       "hours": ["05:00", "19:30"]},
                      {"rect": grid_rect(view, "campagna"), "file": "amb/world/fields.ogg", "gain": 0.6,
                       "hours": ["05:00", "19:30"]},
                      {"rect": grid_rect(view, "appia"), "file": "amb/world/road.ogg", "gain": 0.5,
                       "hours": ["05:30", "19:00"]}],
            "loops": [{"item": R + "r_lacus", "file": "amb/rome/fountain.ogg", "when": "always"},
                      {"item": R + "meta_sudans", "file": "amb/rome/fountain.ogg", "when": "always"},
                      {"item": R + "lacus_iuturnae", "file": "amb/rome/fountain.ogg", "when": "always"},
                      {"item": R + "r_bath_small", "file": "amb/rome/baths.ogg", "when": "afternoon"},
                      {"item": R + "agrippa_baths", "file": "amb/rome/baths.ogg", "when": "afternoon"},
                      {"slot": R + "r_crane.work", "file": "amb/rome/treadwheel.ogg", "when": "worked"},
                      {"slot": R + "r_smithy.work", "file": "amb/world/smith.ogg", "when": "worked"},
                      {"item": R + "r_brazier", "file": "amb/world/brazier.ogg", "when": "lit"}],
            "one_shots": {"venus_roma.work": "sfx/world/chisel.wav", "r_scaffold.beside": "sfx/world/hammer.wav",
                          "quay.mooring": "sfx/world/rope.wav", "iseum": "sfx/rome/sistrum.wav"}},
        "glow": [R + k for k in ("capitolium", "curia", "vesta", "vestals", "colosseum", "trajan_markets",
                                 "domus_flavia", "domus_augustana", "pantheon", "circus_maximus", "r_insula",
                                 "r_insula_low", "r_taberna", "r_thermopolium", "r_compitum", "r_bath_small",
                                 "r_lamp", "r_brazier", "castra_praetoria")],
        "music": {"day": "music/rome/day.ogg", "night": "music/rome/night.ogg"},
        "arrive": "sfx/rome/arrive.wav",
    }


def _baths(doc: dict, view) -> dict:
    """Once the set draws the Baths of Trajan, the Oppian holds the landmark instead of its
    dressing of small bath halls: bathers go to its doors and the hall stokers (whose
    furnace doors were the small halls') are not cast."""
    if view.of_item(R + "r_bath_small") or not view.of_item(R + "trajan_baths"):
        return doc
    doc["roles"] = [r for r in doc["roles"] if r["id"] != "stoker"]
    for d in doc["districts"]:
        d["populations"] = [p for p in d["populations"] if p.get("role") != "stoker"]
    for r in doc["roles"]:
        if r["id"] == "bather":
            r["routines"]["bathe"]["steps"][0] = {"go": {"item": R + "trajan_baths",
                                                         "spot": "beside", "within": 12}}
    return doc


def build(view) -> dict:
    return SEASONS.rome(_baths(_build(view), view))


def _build(view) -> dict:
    return {
        "version": 1, "id": "rome", "name": "Rome", "native": "Roma",
        "caption": "Rome · AD 126",
        "era": "The Rome of Hadrian · AD 126",
        "theme": theme(view),
        "densities": DENSITIES,
        "districts": districts(),
        "roles": roles(),
        "groups": groups(),
        "chains": chains(),
        "festivals": FESTIVALS,
        "events": events(),
        "days_shown": [{"day": 9, "label": "An April day (week day 1: the Senate meets, races in the Circus)"},
                       {"day": 0, "label": "Market day (week day 0)"},
                       {"day": 1, "label": "The Parilia, 21 April (spring, day 2)"}],
        "figures": figures(),
        "lanes_tokens": [{"actor": R + "barge", "lane": "rome:tiber", "count": 3},
                         {"actor": "world.fishing_boat", "lane": "rome:tiber", "count": 1}],
        "cards": cards(),
        "strings": STRINGS,
        "decorate": {"rect": grid_rect(view, "decorate")},
        "journal": ["landmark:*", "figure:*", "chain:*", "idea:*", "event:parilia_procession",
                    "event:parilia_bonfires"],
    }
