"""Pārsa's year (docs/design/seasons.md §2.2 `fars`, §3.7, §3.10, §8): the terrace and its plain
in every month of c. 470/469 BC, laid over the spring day (`life.py`), which it keeps in spring,
the season of the audience.

- The court: the king, the queen and the crown prince are here from March to July; the court
  rides out in July (summer day 2) and is away from August to February (Ecbatana in late summer,
  Babylon in winter, as Greek writers say: Xenophon, Cyropaedia 8.6.22). While it is away the
  terrace and the audience hall are quieter (fewer courtiers, half the guards, no delegations);
  the treasury, the archive, the workshops and the building site go on.
- The calendar: the spring audience every day of spring; the harvest offering in June; the court
  leaving in July; Bāgayādi in September; Mithrakāna in November (attested only in Greek
  writers); the fire evening in December; snow on the plain on some January days.
- Work (the Fortification tablets' year and the farming calendar of Fārs): barley reaped in June,
  threshed in June and July, the vintage in September, channels cleared in August and
  September, ploughing in October and sowing in November, pruning in February and March,
  shearing in April, wool work in the winter months; the building site at 0.6 in winter.
- Travel: fewer caravans in winter (the climate's row); storks from March to August.
- Sound: the summer plain bed (hot wind, grasshoppers, far threshing) from June to September,
  the winter plain beds (cold wind, crows; frost-still nights) from November.
"""

from __future__ import annotations

from worldgen import seasonlife as SL
from worldgen.citylife import card, go, pop, role, sched, use, wander

P = "parsa."
F = SL.factors
W = SL.in_months
COURT = ["mar", "apr", "may", "jun", "jul"]
AWAY = ["aug", "sep", "oct", "nov", "dec", "jan", "feb"]
STORKS = ["mar", "apr", "may", "jun", "jul", "aug"]

FESTIVALS = [
    {"id": "spring_audience", "season": "spring", "hours": ["06:30", "13:00"]},
    {"id": "harvest_offering", "season": "summer", "day": 1, "hours": ["07:00", "12:00"]},
    {"id": "court_leaves", "season": "summer", "day": 2, "hours": ["06:00", "12:00"]},
    {"id": "bagayadi", "season": "autumn", "day": 1, "hours": ["05:00", "10:00"]},
    {"id": "mithrakana", "season": "autumn", "day": 3, "hours": ["08:00", "16:00"]},
    {"id": "fire_evening", "season": "winter", "day": 1, "hours": ["18:00", "21:00"]},
]


def work(id_, actor, name, steps, card_, hours=(("05:30", "11:30"), ("15:00", "18:30"))):
    return role(id_, actor, name, sched(*[(a, b, "work") for a, b in hours]),
                {"work": {"loop": True, "steps": steps}}, card=card_)


def roles() -> list[dict]:
    return [
        work("ploughman", P + "farmer", "Ploughman", [
            wander(radius=8, dur=(20, 40)), use(anim="work_low", dur=(40, 60)),
            wander(radius=4, dur=(10, 20)), use(anim="work_low", dur=(30, 50))], "ploughman"),
        work("reaper", P + "farmer", "Reaper", [
            wander(radius=8, dur=(15, 30)), use(anim="work_low", dur=(40, 60)),
            go(item=P + "p_threshing", spot="beside", within=40), use(anim="haul", dur=(10, 16))], "reaper"),
        work("vintager", P + "gardener", "Grape picker", [
            go(item=P + "t_vine", spot="beside", within=40), use(anim="work_low", dur=(40, 70)),
            wander(radius=4, dur=(10, 20))], "vintager"),
        work("pruner", P + "gardener", "Pruning", [
            go(item=P + "t_vine", spot="beside", within=40), use(anim="work_high", dur=(40, 60)),
            go(item=P + "t_almond", spot="beside", within=40), use(anim="work_high", dur=(30, 50))], "pruner"),
        work("channel_clearer", P + "labourer", "Clearing the channels", [
            go(item=P + "p_sluice", spot="beside", within=40), use(anim="haul", dur=(40, 70)),
            wander(radius=5, dur=(15, 25)), use(anim="haul", dur=(30, 50))], "channel_clearer"),
        work("shearer", P + "shepherd", "Shearer", [
            wander(radius=6, dur=(20, 30)), use(anim="gesture", dur=(30, 50))], "shearer",
             hours=(("06:00", "12:00"), ("15:00", "18:30"))),
    ]


def rule(dist: str, p: dict):
    key = p.get("role") or p.get("actor")
    if key == "stork":
        return None
    if dist in ("terrace", "audience"):
        if key == "courtier":
            return F(1.0, aug_feb=0.6), None
        if key == "median_official":
            return F(1.0, aug_feb=0.75), None
        if key == "royal_servant":
            return F(1.0, aug_feb=0.6), None
        if key == "spearman" or key.startswith("guard_"):
            return F(1.0, aug_feb=0.7), None
    if dist in ("palaces", "forecourt") and key in ("courtier", "royal_servant"):
        return F(1.0, aug_feb=0.9), None
    if dist == "forecourt" and key in ("groom", "horse"):
        return F(1.0, aug_feb=0.6), None
    if dist == "paradise" and key in ("courtier", "musician"):
        return F(1.0, aug_feb=0.0), None
    if dist in ("fields", "plain", "village", "river", "southern_plain") and key == "farmer":
        return F(1.0, aug=0.85, sep=0.85, dec_feb=0.85), None
    if dist == "station" and key in ("caravan_driver", "camel", "cart"):
        return [1, 1, 1, 1, 1, 1, 1, 0.9, 0.8, 0.7, 0.6, 0.7], None
    if key in ("weaver", "dyer", "grinder") and dist in ("town", "crafts"):
        return F(1.0, nov_feb=1.25), None
    return None


def populations(doc: dict) -> None:
    for d in doc["districts"]:
        for p in d["populations"]:
            if p.get("role") == "stork":
                p["when"] = W(STORKS)
    SL.vary(doc, rule)
    extra = {
        "fields": [pop("reaper", "dawn_work", 10, when=W(["jun"])),
                   pop("ploughman", "dawn_work", 8, when=W(["oct", "nov"]))],
        "plain": [pop("reaper", "dawn_work", 6, when=W(["jun"])),
                  pop("ploughman", "dawn_work", 6, when=W(["oct", "nov"])),
                  pop("channel_clearer", "dawn_work", 6, when=W(["aug", "sep"]))],
        "village": [pop("ploughman", "dawn_work", 4, when=W(["oct", "nov"]))],
        "garden_strip": [pop("vintager", "dawn_work", 6, when=W(["sep"])),
                         pop("pruner", "dawn_work", 4, when=W(["feb", "mar"])),
                         pop("channel_clearer", "dawn_work", 4, when=W(["aug", "sep"]))],
        "southern_plain": [pop("shearer", "dawn_work", 3, when=W(["apr"]))],
    }
    for d in doc["districts"]:
        d["populations"] += extra.get(d["id"], [])
        if d["id"] in ("terrace", "audience", "forecourt"):
            # With the court away the terrace is a working place, not a crowd (the life checks
            # hold it to a town's numbers in those months).
            d["seasonal_area"] = {"area": "town", "months": AWAY}
        if d["id"] == "camp":
            # The delegations' camp stands only for the spring audience.
            d["seasonal_area"] = {"area": "wild", "months": AWAY + ["jun", "jul"]}


def events(doc: dict) -> None:
    by_id = {e["id"]: e for e in doc["events"]}
    retime = {"reapers": ["jun"], "threshing": ["jun", "jul"], "dust_breeze": ["jun", "jul", "aug", "sep"],
              "swifts": ["mar", "apr", "may", "jun", "jul", "aug", "sep"]}
    for eid, ms in retime.items():
        t = by_id[eid]["trigger"]
        t.pop("season", None)
        t["months"] = ms
    doc["events"] += [
        {"id": "court_leaves", "rarity": "festival", "size": "large", "zone": "forecourt",
         "trigger": {"on": "calendar", "festival": "court_leaves", "hours": ["07:00", "07:30"]},
         "duration": [200, 260], "cast": [{"role": "courtier", "count": 10, "from": "district"},
                                          {"role": "spearman", "count": 8}, {"role": "rider", "count": 6},
                                          {"actor": P + "xerxes", "count": 1}],
         "steps": [go(node="great_stair_foot"), go(node="royal_road_station"), use(anim="idle", dur=(60, 90))],
         "route": ["great_stair_foot", "royal_road_station"], "sfx": "sfx/parsa/horn.wav",
         "string": "court_leaves", "card": "court_moves"},
        {"id": "mithrakana", "rarity": "festival", "size": "medium", "zone": "naqsh",
         "trigger": {"on": "calendar", "festival": "mithrakana", "hours": ["09:00", "10:00"]},
         "duration": [150, 200], "cast": [{"role": "magus", "count": 2}, {"role": "townswoman", "count": 8},
                                          {"role": "workman", "count": 6}],
         "steps": [go(item=P + "p_fire_altar", slot="tend", within=8), use(anim="idle", dur=(120, 160))],
         "sfx": "sfx/parsa/chant.wav", "string": "mithrakana", "card": "mithrakana"},
        {"id": "ploughing", "rarity": "daily", "size": "medium", "zone": "fields",
         "trigger": {"on": "window", "hours": ["06:00", "07:00"], "months": ["oct", "nov"], "chance": 1.0},
         "duration": [180, 220], "cast": [{"role": "zebu", "count": 2}, {"role": "ploughman", "count": 3}],
         "steps": [wander(zone="fields", dur=(160, 200))], "sfx": "sfx/world/hoof_earth_1.wav",
         "string": "ploughing"},
        {"id": "plain_snow", "rarity": "uncommon", "size": "small", "zone": "plain",
         "trigger": {"on": "window", "hours": ["04:00", "07:00"], "months": ["jan"], "chance": 0.4},
         "duration": [180, 240], "steps": [{"emit": {"fx": "fx/snowflake"}}],
         "ambience": {"file": "amb/world/snow.ogg", "gain": 0.5}, "string": "plain_snow"},
        {"id": "wool_work", "rarity": "daily", "size": "small", "zone": "town",
         "trigger": {"on": "window", "hours": ["09:00", "10:00"], "months": ["nov", "dec", "jan", "feb"],
                     "chance": 1.0},
         "duration": [200, 260], "cast": [{"role": "weaver", "count": 3, "from": "district"},
                                          {"role": "weaving_overseer", "count": 1}],
         "steps": [go(item=P + "p_loom", spot="beside", within=8), use(anim="throw", dur=(180, 240))],
         "ambience": {"file": "amb/world/loom.ogg", "gain": 0.6}, "string": "wool_work"},
    ]


def figures(doc: dict) -> None:
    for f in doc["figures"]:
        if f.get("actor") in (P + "xerxes", P + "amestris", P + "artaxerxes"):
            for b in f.get("schedule", []):
                b["months"] = COURT
            f["note"] = (f.get("note", "") + "; " if f.get("note") else "") + \
                "here from March to July; the court is away from August (Greek writers say)"


def chains(doc: dict) -> None:
    by_id = {c["id"]: c for c in doc["chains"]}
    by_id["parsa_table"]["months"] = COURT
    by_id["parsa_stone"]["by_month"] = F(1.0, dec_feb=0.6)
    by_id["parsa_bricks"]["by_month"] = F(1.0, dec_feb=0.6)
    by_id["parsa_cedar"]["months"] = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov"]


def cards(doc: dict) -> None:
    doc["cards"].update({
        "court_moves": card("idea", "The court on the move",
                            "Greek writers say",
                            "Xenophon writes that the king spent seven winter months in Babylon, "
                            "three spring months at Susa and two summer months at Ecbatana. The "
                            "Persian records do not describe the court's year, and the game's "
                            "spring audience at Pārsa is a modern reading: perhaps. Here the court "
                            "rides out in July and the terrace stays quieter until spring, while "
                            "the treasury, the workshops and the building site go on."),
        "mithrakana": card("event", "Mithrakāna", "Known from Greek writers",
                           "An autumn festival of Mithra that Greek writers describe; the "
                           "Persian records name months and offerings, not this feast. Shown "
                           "small, with offerings at the fire altar."),
        "ploughman": card("role", "Ploughman", "October and November",
                          "When the autumn comes the zebu oxen draw the plough across the barley "
                          "fields of the plain, and the seed goes in for next June."),
        "reaper": card("role", "Reaper", "The June harvest",
                       "Barley ripens on the plain in June; reapers cut it with sickles and carry "
                       "the sheaves to the threshing floors."),
        "vintager": card("role", "Grape picker", "September",
                         "The tablets record wine issued as rations; the vines of the gardens are "
                         "picked in September."),
        "pruner": card("role", "Pruner", "Late winter",
                       "Gardeners prune the vines and the fruit trees in the last weeks of winter, "
                       "before the almonds flower."),
        "channel_clearer": card("role", "Channel clearer", "At low water",
                                "When the channels run thin in late summer, work gangs dig out the "
                                "silt so the snowmelt can run freely in spring."),
        "shearer": card("role", "Shearer", "April",
                        "The flocks are shorn in April; the wool goes to the weavers, whose "
                        "rations the tablets list by the hundred."),
    })
    doc["strings"].update({
        "court_leaves": "The court rides out for the cool of the north. The terrace will be quieter now.",
        "mithrakana": "Offerings at the fire altar for Mithra's autumn feast.",
        "ploughing": "Zebu oxen draw the ploughs across the plain.",
        "plain_snow": "Snow on the plain this morning. It will melt by tomorrow.",
        "wool_work": "Winter work: the looms clatter in the weavers' courtyard.",
        "first_visit": "Pārsa, c. 470 BC: the terrace of the kings above the Marvdasht plain.",
    })


SEASON_BEDS = {
    "summer": {"beds": [{"file": "amb/parsa/plain_day_summer.ogg", "hours": ["05:30", "19:00"]},
                        {"file": "amb/parsa/plain_night.ogg", "hours": ["19:00", "05:30"]}]},
    "autumn": {"beds": [{"file": "amb/parsa/plain_day_summer.ogg", "hours": ["05:30", "19:00"],
                         "months": ["sep"]},
                        {"file": "amb/parsa/plain_day_winter.ogg", "hours": ["05:30", "19:00"],
                         "months": ["nov"]},
                        {"file": "amb/parsa/plain_night_winter.ogg", "hours": ["19:00", "05:30"],
                         "months": ["nov"]}]},
    "winter": {"beds": [{"file": "amb/parsa/plain_day_winter.ogg", "hours": ["05:30", "19:00"]},
                        {"file": "amb/parsa/plain_night_winter.ogg", "hours": ["19:00", "05:30"]}]},
    "spring": {"beds": [{"file": "amb/parsa/plain_night_winter.ogg", "hours": ["19:00", "05:30"],
                         "months": ["mar"]}]},
}


def apply(doc: dict) -> dict:
    doc.pop("season", None)
    doc["caption"] = "Pārsa · c. 470 BC"
    doc["theme"].pop("climate", None)
    doc["festivals"] = FESTIVALS
    doc["roles"] += roles()
    populations(doc)
    events(doc)
    figures(doc)
    chains(doc)
    cards(doc)
    doc["days_shown"] = [
        {"day": 1, "label": "April: the spring audience in the morning"},
        {"day": 3, "label": "June: the harvest offering, a ration day"},
        {"day": 4, "label": "July: the court rides out"},
        {"day": 5, "label": "August: the court away, the terrace quiet"},
        {"day": 7, "label": "October: ploughing, a ration day"},
        {"day": 9, "label": "December: the fire evening"},
        {"day": 10, "label": "January: snow on the plain"},
    ]
    return doc
