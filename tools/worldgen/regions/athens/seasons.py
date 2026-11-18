"""Athens' year (docs/design/seasons.md §2.2 `med_dry`, §3.7, §3.10): the city's life in every
month of 432/431 BC, laid over its summer day (`life.py`), which it keeps unchanged in July, the
month of the Panathenaia.

- The calendar by month: the City Dionysia in April, the Thargelia in May, the Skira in June,
  the Panathenaia in July, the Mysteries in September, the Oschophoria in October, the
  Thesmophoria in November, the Rural Dionysia in December, the Lenaia in January, the
  Anthesteria in February; the olive harvest from November to January (not all autumn).
- Work by month (Hesiod's year; the Attic farming calendar): barley reaped in May and June,
  threshed in June and July, the vintage in September, ploughing and sowing after the first rains
  in October and November, olives picked from November to January, vines pruned in February,
  sheep shorn in April and May.
- The sea: merchant ships and the grain fleet in the sailing season only; triremes in their
  sheds at Zea from December to February with the shipwrights busy; fewer rowers on the quays.
- The streets: a shorter midday rest from October to April (the summer day keeps its long one);
  fewer people out on winter days and evenings; the marble chain at 0.6 in the winter months.
- Sound: the cool-season day bed (no cicadas) from October to May, the winter night bed (no
  crickets) from November to March.
"""

from __future__ import annotations

from worldgen import seasonlife as SL
from worldgen.citylife import go, pop, use, wander

A = "athens."
F = SL.factors

FESTIVALS = [
    {"id": "city_dionysia", "season": "spring", "day": 2, "hours": ["07:00", "18:00"]},
    {"id": "thargelia", "season": "spring", "day": 3, "hours": ["07:00", "16:00"]},
    {"id": "skira", "season": "summer", "day": 1, "hours": ["07:00", "15:00"]},
    {"id": "panathenaia", "season": "summer", "day": 2, "hours": ["05:30", "18:00"]},
    {"id": "mysteries", "season": "autumn", "day": 1, "hours": ["06:00", "18:00"]},
    {"id": "oschophoria", "season": "autumn", "day": 2, "hours": ["07:00", "15:00"]},
    {"id": "thesmophoria", "season": "autumn", "day": 3, "hours": ["06:00", "18:00"]},
    {"id": "olive_harvest", "months": ["nov", "dec", "jan"], "hours": ["06:00", "17:00"]},
    {"id": "rural_dionysia", "season": "winter", "day": 1, "hours": ["09:00", "17:00"]},
    {"id": "lenaia", "season": "winter", "day": 2, "hours": ["09:00", "17:00"]},
    {"id": "anthesteria", "season": "winter", "day": 3, "hours": ["08:00", "20:00"]},
]

COUNTRY = ("north_fields", "south_fields", "ilissos", "countryside")
TOWN = ("melite", "koile", "kollytos", "kydathenaion", "skambonidai", "east_quarter")
WORK_HOURS = [("05:00", "11:30"), ("15:00", "19:00")]

# The summer day the city was built on already rests at midday; in the cool months (October to
# April) the rest is shorter: the same curves with noon and one o'clock lifted.
COOL = ["oct", "nov", "dec", "jan", "feb", "mar", "apr"]


def _cool(curve: list[float]) -> list[float]:
    return [round(min(1.0, v * 1.2), 3) if h in (12, 13) else v for h, v in enumerate(curve)]


def work_role(id_, actor, name, steps, card=None):
    r = {"id": id_, "actor": actor, "name": name,
         "schedule": [{"hours": list(h), "routine": "work"} for h in WORK_HOURS],
         "routines": {"work": {"loop": True, "steps": steps}}}
    if card:
        r["card"] = card
    return r


def roles() -> list[dict]:
    return [
        work_role("ploughman", A + "farmer", "Ploughman", [
            wander(radius=8, dur=(20, 40)), use(anim="work_low", dur=(40, 60)),
            wander(radius=4, dur=(10, 20)), use(anim="work_low", dur=(30, 50))], card="ploughman"),
        work_role("reaper", A + "farmer", "Reaper", [
            wander(radius=6, dur=(15, 30)), use(anim="work_low", dur=(40, 60)),
            {"take": "world.goods_sacks"}, go(item=A + "g_farmstead", slot="door", within=16),
            {"put": "world.goods_sacks"}], card="reaper"),
        work_role("olive_picker", A + "enslaved_man", "Olive picker", [
            go(item=A + "t_olive", spot="beside", within=24), use(anim="work_low", dur=(40, 70)),
            go(item=A + "t_olive", spot="beside", within=24), use(anim="work_low", dur=(30, 60)),
            {"take": "world.goods_sacks"}, go(item=A + "g_press", spot="beside", within=24),
            {"put": "world.goods_sacks"}], card="olive_picker"),
        work_role("vintager", A + "farmer", "Grape picker", [
            go(item=A + "t_vine", spot="beside", within=24), use(anim="work_low", dur=(40, 70)),
            {"take": "world.goods_sacks"}, go(item=A + "g_farmstead", slot="door", within=24),
            {"put": "world.goods_sacks"}], card="vintager"),
        work_role("pruner", A + "farmer", "Pruning the vines", [
            go(item=A + "t_vine", spot="beside", within=24), use(anim="work_low", dur=(40, 60)),
            wander(radius=3, dur=(10, 20))], card="pruner"),
        work_role("shearer", A + "herder", "Shearer", [
            wander(radius=6, dur=(20, 30)), use(anim="idle", dur=(40, 60))], card="shearer"),
    ]


def vary_rule(dist: str, p: dict):
    key = p.get("role") or p.get("actor")
    if key == "thresher":
        return F(0.0, jun=1.0, jul=1.0), None
    if dist in COUNTRY and key == "farmer":
        return F(1.0, aug=0.75, sep=0.75, dec=0.85, jan=0.85, feb=0.85), None
    if dist in COUNTRY and key == "ox":
        return F(1.0, oct=1.5, nov=1.5), None
    if dist in ("piraeus",):
        if key == "rower":
            return F(1.0, mar=0.6, nov=0.6, dec_feb=0.35), None
        if key in ("merchant", "ionian", "thracian"):
            return F(1.0, mar=0.6, oct=0.7, nov=0.5, dec_feb=0.3), None
        if key == "docker":
            return F(1.0, mar=0.7, nov=0.6, dec_feb=0.45), None
        if key == "shipwright":
            return F(1.0, nov=1.5, dec_feb=2.0), None
    # The building site and the quarry keep their gangs through the winter (the districts are
    # at their minimum crowd already); their work slows instead: the marble chain runs at 0.6.
    if key in ("night_walker",):
        return F(1.0, nov=0.8, dec_feb=0.6), None
    cool = {m: {"market": "market_cool", "day": "day_cool"}.get(p.get("density")) for m in COOL}
    cool = {m: d for m, d in cool.items() if d} or None
    if dist in TOWN + ("agora", "council", "kerameikos") and \
            key in ("shopper", "townsman", "child", "elder"):
        return F(1.0, dec_feb=0.92 if dist in TOWN else 0.97), cool
    if dist in ("agora", "acropolis", "council", "dionysos") and \
            key in ("visitor", "visitor_woman", "theatre_visitor"):
        return None, cool
    return None


def populations(doc: dict) -> None:
    SL.vary(doc, vary_rule)
    W = SL.in_months
    extra = {
        "north_fields": [pop("ploughman", "dawn_work", 6, when=W(["oct", "nov"])),
                         pop("reaper", "dawn_work", 8, when=W(["may", "jun"])),
                         pop("olive_picker", "dawn_work", 6, when=W(["nov", "dec", "jan"])),
                         pop("shearer", "day", 2, when=W(["apr", "may"]))],
        "south_fields": [pop("ploughman", "dawn_work", 5, when=W(["oct", "nov"])),
                         pop("reaper", "dawn_work", 6, when=W(["may", "jun"])),
                         pop("olive_picker", "dawn_work", 8, when=W(["nov", "dec", "jan"])),
                         pop("vintager", "dawn_work", 4, when=W(["sep"])),
                         pop("pruner", "dawn_work", 3, when=W(["feb"]))],
        "ilissos": [pop("olive_picker", "dawn_work", 8, when=W(["nov", "dec", "jan"])),
                    pop("vintager", "dawn_work", 4, when=W(["sep"])),
                    pop("pruner", "dawn_work", 3, when=W(["feb"])),
                    pop("ploughman", "dawn_work", 4, when=W(["oct", "nov"]))],
        "countryside": [pop("ploughman", "dawn_work", 5, when=W(["oct", "nov"])),
                        pop("reaper", "dawn_work", 6, when=W(["may", "jun"])),
                        pop("olive_picker", "dawn_work", 6, when=W(["nov", "dec", "jan"])),
                        pop("shearer", "day", 2, when=W(["apr", "may"]))],
    }
    for d in doc["districts"]:
        d["populations"] += extra.get(d["id"], [])


def events(doc: dict) -> None:
    by_id = {e["id"]: e for e in doc["events"]}
    by_id["swifts"]["trigger"].pop("season", None)
    by_id["swifts"]["trigger"]["months"] = ["apr", "may", "jun", "jul", "aug"]
    by_id["meltemi"]["trigger"].pop("season", None)
    by_id["meltemi"]["trigger"]["months"] = ["jul", "aug"]
    by_id["summer_storm"]["trigger"].pop("season", None)
    by_id["summer_storm"]["trigger"]["months"] = ["jun", "jul", "aug"]
    doc["events"] += [
        {"id": "thargelia", "rarity": "festival", "size": "medium", "zone": "agora",
         "trigger": {"on": "calendar", "festival": "thargelia", "hours": ["08:00", "09:00"]},
         "duration": [150, 200], "cast": [{"role": "townsman", "count": 10}, {"role": "child", "count": 6},
                                          {"role": "priestess", "count": 1}],
         "steps": [go(node="agora"), use(anim="idle", dur=(120, 160))], "sfx": "sfx/world/chorus_far.wav",
         "string": "thargelia"},
        {"id": "skira", "rarity": "festival", "size": "small", "zone": "acropolis",
         "trigger": {"on": "calendar", "festival": "skira", "hours": ["08:00", "09:00"]},
         "duration": [120, 160], "cast": [{"role": "priestess", "count": 3}, {"role": "housewife", "count": 8}],
         "steps": [go(node="propylaia"), use(anim="idle", dur=(100, 130))], "sfx": "sfx/athens/ololyge.wav",
         "string": "skira"},
        {"id": "oschophoria", "rarity": "festival", "size": "medium", "zone": "ilissos",
         "trigger": {"on": "calendar", "festival": "oschophoria", "hours": ["08:00", "09:00"]},
         "duration": [150, 200], "cast": [{"role": "pupil", "count": 8}, {"role": "townsman", "count": 6}],
         "steps": [wander(zone="ilissos", dur=(120, 160))], "sfx": "sfx/athens/aulos.wav",
         "string": "oschophoria"},
        {"id": "thesmophoria", "rarity": "festival", "size": "medium", "zone": "pnyx",
         "trigger": {"on": "calendar", "festival": "thesmophoria", "hours": ["07:00", "08:00"]},
         "duration": [240, 300], "cast": [{"role": "housewife", "count": 18}, {"role": "priestess", "count": 2}],
         "steps": [go(node="pnyx"), use(anim="idle", dur=(220, 280))], "sfx": "sfx/athens/ololyge.wav",
         "string": "thesmophoria", "card": "thesmophoria"},
        {"id": "rural_dionysia", "rarity": "festival", "size": "small", "zone": "countryside",
         "trigger": {"on": "calendar", "festival": "rural_dionysia", "hours": ["10:00", "11:00"]},
         "duration": [150, 200], "cast": [{"role": "farmer", "count": 8, "from": "district"},
                                          {"actor": A + "musician", "count": 2}],
         "steps": [wander(zone="countryside", dur=(130, 180))], "sfx": "sfx/athens/aulos.wav",
         "string": "rural_dionysia"},
        {"id": "lenaia", "rarity": "festival", "size": "large", "zone": "dionysos",
         "trigger": {"on": "calendar", "festival": "lenaia", "hours": ["09:00", "10:00"]},
         "duration": [300, 360], "cast": [{"role": "theatre_visitor", "count": 24}, {"role": "chorus", "count": 6}],
         "steps": [go(node="theatre"), use(item=A + "theatre", slot="watch", anim="sit", dur=(280, 340))],
         "sfx": "sfx/world/applause.wav", "string": "lenaia", "card": "lenaia"},
        {"id": "anthesteria", "rarity": "festival", "size": "medium", "zone": "kydathenaion",
         "trigger": {"on": "calendar", "festival": "anthesteria", "hours": ["10:00", "11:00"]},
         "duration": [200, 260], "cast": [{"role": "child", "count": 10}, {"role": "housewife", "count": 6},
                                          {"role": "townsman", "count": 8}],
         "steps": [wander(zone="kydathenaion", dur=(180, 240))], "sfx": "sfx/world/cheer.wav",
         "string": "anthesteria", "card": "anthesteria"},
        {"id": "vintage_treading", "rarity": "uncommon", "size": "small", "zone": "south_fields",
         "trigger": {"on": "window", "hours": ["09:00", "10:00"], "months": ["sep"], "chance": 1.0},
         "duration": [150, 200], "cast": [{"role": "vintager", "count": 4, "from": "district"}],
         "steps": [go(item=A + "g_farmstead", slot="door", within=24), use(anim="work_low", dur=(120, 160))],
         "ambience": {"file": "amb/world/press.ogg", "gain": 0.6}, "string": "vintage"},
        {"id": "ships_in_sheds", "rarity": "daily", "size": "small", "zone": "piraeus",
         "trigger": {"on": "window", "hours": ["08:00", "09:00"], "months": ["dec", "jan", "feb"],
                     "chance": 1.0},
         "duration": [240, 300], "cast": [{"role": "shipwright", "count": 6, "from": "district"}],
         "steps": [go(node="zea_sheds"), use(anim="haul", dur=(200, 260))],
         "ambience": {"file": "amb/world/saw.ogg", "gain": 0.6}, "string": "ship_sheds", "card": "ship_sheds"},
        {"id": "braziers_lit", "rarity": "daily", "size": "small", "zone": "agora",
         "trigger": {"on": "window", "hours": ["17:00", "17:30"], "months": ["nov", "dec", "jan", "feb", "mar"],
                     "chance": 1.0},
         "duration": [40, 60], "steps": [{"each": {"item": A + "g_brazier", "within": 4096},
                                          "state": "lit", "every": 3}],
         "sfx": "sfx/world/lamp.wav", "string": "braziers"},
        {"id": "winter_flurry", "rarity": "rare", "size": "small", "zone": "agora",
         "trigger": {"on": "window", "hours": ["07:00", "11:00"], "months": ["dec", "jan", "feb"],
                     "chance": 0.15},
         "duration": [90, 150], "steps": [{"emit": {"fx": "fx/snowflake"}}],
         "ambience": {"file": "amb/world/snow.ogg", "gain": 0.5}, "string": "flurry"},
    ]


def chains(doc: dict) -> None:
    by_id = {c["id"]: c for c in doc["chains"]}
    by_id["athens_marble"]["by_month"] = F(1.0, dec_feb=0.6)
    # Merchantmen load oil only while the sea is open; the grain ships come from the Black Sea
    # in the sailing season (seasons.md §3.9).
    by_id["athens_oil_export"]["months"] = ["apr", "may", "jun", "jul", "aug", "sep", "oct"]
    by_id["athens_grain"]["months"] = ["apr", "may", "jun", "jul", "aug", "sep", "oct"]
    by_id["athens_fish"]["by_month"] = F(1.0, dec_feb=0.7)


def cards(doc: dict) -> None:
    from worldgen.citylife import card
    doc["cards"].update({
        "ploughman": card("role", "Ploughman", "After the first rains",
                          "When the cranes call overhead, says Hesiod, it is time to plough: the "
                          "farmer yokes his oxen and sows barley and wheat in the soft ground."),
        "reaper": card("role", "Reaper", "Barley in May",
                       "Attic barley ripens early: reapers cut it with sickles in May and wheat in "
                       "June, and carry the sheaves to the threshing floor."),
        "olive_picker": card("role", "Olive picker", "November to January",
                             "Olives are beaten from the branches with sticks or picked by hand "
                             "onto cloths, then carried to the press for the winter's oil."),
        "vintager": card("role", "Grape picker", "The vintage",
                         "In September the grapes are cut and trodden in the vat; the new wine "
                         "rests in jars until the Anthesteria opens it."),
        "pruner": card("role", "Pruner", "Before the swallow",
                       "Hesiod's farmer prunes his vines before the swallow comes back, in the "
                       "last cold weeks of winter."),
        "shearer": card("role", "Shearer", "Spring shearing",
                        "Sheep are shorn in spring before the heat; the wool goes to the women's "
                        "looms for the year's cloth."),
        "thesmophoria": card("event", "Thesmophoria", "For women only",
                             "Citizen women keep Demeter's festival for three days on the hill of "
                             "the Thesmophorion. Men may not attend, and what is done there is "
                             "theirs to know."),
        "lenaia": card("event", "Lenaia", "Comedies in winter",
                       "A winter festival of Dionysus with contests in comedy and tragedy, held "
                       "when no foreigners are in the city, as Aristophanes later jokes."),
        "anthesteria": card("event", "Anthesteria", "The new wine opened",
                            "In early spring the jars of last autumn's wine are opened. Children "
                            "of three get their first little jug, and the dead are thought to "
                            "walk the streets for a day."),
        "ship_sheds": card("landmark", "Ship sheds", "Triremes in winter",
                           "Through the closed season the triremes rest in their long sheds at "
                           "Zea and Mounychia, and shipwrights repair hulls, oars and tackle for "
                           "the spring."),
    })
    doc["strings"].update({
        "thargelia": "Thargelia: the first fruits are carried to Apollo.",
        "skira": "Skira: the priestess walks out under a white parasol.",
        "oschophoria": "Youths carry vine branches heavy with grapes down to Phaleron.",
        "thesmophoria": "The women go up to the Thesmophorion: no men today.",
        "rural_dionysia": "In the demes the Rural Dionysia: a procession, songs and jokes.",
        "lenaia": "The Lenaia: comedies in the theatre, for Athenians only.",
        "anthesteria": "The Anthesteria: the new wine is opened; children carry little jugs.",
        "vintage": "Grapes are trodden in the vats.",
        "ship_sheds": "The triremes are in their sheds; the shipwrights are at work.",
        "braziers": "Braziers are lit in the shops against the cold.",
        "flurry": "A few snowflakes over the Agora. They do not settle.",
    })


# Seasonal beds (seasons.md §3.12): they replace the year-round day and night beds in their
# months. The files are on the audio lane's list (assets/world/season-needs.json).
DAY_COOL = "amb/athens/day_cool.ogg"
NIGHT_WINTER = "amb/athens/night_winter.ogg"
SEASON_BEDS = {
    "spring": {"beds": [{"file": DAY_COOL, "hours": ["05:00", "19:30"]},
                        {"file": NIGHT_WINTER, "hours": ["19:30", "05:00"], "months": ["mar"]}]},
    "autumn": {"beds": [{"file": DAY_COOL, "hours": ["05:00", "19:30"], "months": ["oct", "nov"]},
                        {"file": NIGHT_WINTER, "hours": ["19:30", "05:00"], "months": ["nov"]}]},
    "winter": {"beds": [{"file": DAY_COOL, "hours": ["05:00", "19:30"]},
                        {"file": NIGHT_WINTER, "hours": ["19:30", "05:00"]}]},
}


def apply(doc: dict) -> dict:
    doc.pop("season", None)
    doc["caption"] = "Athens · 432 BC"
    doc["festivals"] = FESTIVALS
    doc["densities"]["market_cool"] = _cool(doc["densities"]["market"])
    doc["densities"]["day_cool"] = _cool(doc["densities"]["day"])
    doc["roles"] += roles()
    populations(doc)
    events(doc)
    chains(doc)
    cards(doc)
    doc["harbours"] = [{"zone": "piraeus", "laid_up": "sailing", "below": 0.3,
                        "props": ["world.hull_ashore"],
                        "note": "the triremes rest in their sheds at Zea and Mounychia"}]
    amb = doc["theme"]["ambience"]
    amb["cicadas"].pop("season", None)
    amb["cicadas"]["months"] = ["jun", "jul", "aug", "sep"]
    doc["days_shown"] = [
        {"day": 4, "label": "The Panathenaia (summer day 2, July)"},
        {"day": 5, "label": "An ordinary summer day (August)"},
        {"day": 1, "label": "The City Dionysia (spring day 2, April)"},
        {"day": 6, "label": "The Mysteries and an assembly (autumn day 1, September)"},
        {"day": 8, "label": "A November day: ploughing and the olive harvest"},
        {"day": 10, "label": "Assembly day in January: the Lenaia, olives and the ship sheds"},
    ]
    return doc
