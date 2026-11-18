"""Rome's year and its towns' (docs/design/seasons.md §2.2 `med_green`, §3.7, §3.9, §3.10): the
city of AD 126/127 in every month, laid over its April day (`life.py`), which it keeps in April,
the month of the Parilia; and the year of Ostia and Portus, the Alban Mount and Brundisium.

- The calendar by month (corrected, seasons.md §8): the Parilia on 21 April (spring day 2), the
  Floralia's last days in May, the Vestalia in June, the Ludi Apollinares in July (summer day 2,
  not 3), the Vinalia Rustica on 19 August (the April Vinalia would fall on the Parilia's day), the
  Ludi Romani in September, the October Horse in October, the Ludi Plebeii in November, the
  Saturnalia in December (winter day 1, not 2), the Kalends of January, the Lupercalia in
  February. At Ostia the ship of Isis opens the sea on 5 March; the Alexandrian grain fleet comes
  in from May to August.
- Starlings over the Tiber from October to February, not in spring; swifts from April to August.
- Work (the menologia rustica): pruning in February and March, shearing in May, hay in June, the
  grain harvest in June and July, the vintage in September and October, ploughing and sowing in
  October and November, olives in November and December; the building sites at 0.6 in winter.
- The sea closed from November to February: ships laid up and hulls hauled ashore at Portus and
  Brundisium, shipwrights busy, few sailors and passengers on the quays.
- Sound: the winter day bed (no swallows; hearth crackle, wind and dripping gutters) in
  December, January and February.
"""

from __future__ import annotations

from worldgen import seasonlife as SL
from worldgen.citylife import card, go, pop, sched, use, wander, role

R = "rome."
F = SL.factors
W = SL.in_months
SEA_OPEN = [0.6, 0.8, 1, 1, 1, 1, 1, 0.8, 0.6, 0.45, 0.45, 0.45]   # crews and passengers ashore


def work(id_, actor, name, steps, card_, hours=(("05:30", "11:30"), ("15:00", "19:00"))):
    return role(id_, actor, name, sched(*[(a, b, "work") for a, b in hours]),
                {"work": {"loop": True, "steps": steps}}, card=card_)


def farm_roles() -> list[dict]:
    return [
        work("reaper", R + "farmer", "Reaper", [
            wander(radius=8, dur=(15, 30)), use(anim="work_low", dur=(40, 60)),
            go(item=R + "r_villa_farm", slot="door", within=24), use(anim="idle", dur=(8, 14))], "reaper"),
        work("ploughman", R + "farmer", "Ploughman", [
            wander(radius=8, dur=(20, 40)), use(anim="work_low", dur=(40, 60)),
            wander(radius=4, dur=(10, 20)), use(anim="work_low", dur=(30, 50))], "ploughman"),
        work("grape_picker", R + "enslaved", "Grape picker", [
            go(item=R + "r_vine", spot="beside", within=24), use(anim="work_low", dur=(40, 70)),
            {"take": R + "goods_wine_amphora"}, go(item=R + "r_villa_farm", slot="door", within=40),
            {"put": R + "goods_wine_amphora"}], "grape_picker"),
        work("olive_picker", R + "enslaved", "Olive picker", [
            go(item=R + "t_olive", spot="beside", within=32), use(anim="work_low", dur=(40, 70)),
            go(item=R + "t_olive", spot="beside", within=32), use(anim="work_low", dur=(30, 60))],
             "olive_picker"),
        work("haymaker", R + "farmer", "Haymaker", [
            wander(radius=8, dur=(15, 30)), use(anim="work_high", dur=(40, 60)),
            use(anim="work_low", dur=(20, 30))], "haymaker"),
        work("shearer", R + "shepherd", "Shearer", [
            wander(radius=6, dur=(20, 30)), use(anim="idle", dur=(40, 60))], "shearer",
             hours=(("06:00", "12:00"), ("15:00", "18:30"))),
    ]


FARM_CARDS = {
    "reaper": card("role", "Messor", "The harvest, June and July",
                   "Gangs of reapers cut the wheat of the Campagna with sickles in early summer; "
                   "the straw is left long and the ears go to the threshing floor."),
    "ploughman": card("role", "Arator", "October and November",
                      "After the first autumn rains the ox plough turns the fields and the wheat is "
                      "sown for next summer."),
    "grape_picker": card("role", "Vindemiator", "The vintage",
                         "In September and October the grapes of the Janiculum and the Campagna are "
                         "cut, trodden and pressed, and the must poured into jars."),
    "olive_picker": card("role", "Oleae lector", "Olives in winter",
                         "Olives are gathered from November into December, beaten or picked, and "
                         "pressed for the year's oil."),
    "haymaker": card("role", "Faenisex", "Hay in June",
                     "The country calendars put the hay harvest in June: meadows mown and the hay "
                     "dried for the winter's animals."),
    "shearer": card("role", "Tonsor ovium", "Shearing in May",
                    "Sheep are washed and shorn in May, before the heat, as the farm calendars "
                    "carved in stone advise."),
}

COUNTRY = ("vatican", "campagna", "janiculum")


SWALLOWS = F(0.0, mar_sep=1.0)


def swallows(dist: str, p: dict):
    """Swallows are summer birds (March to September); they leave for the winter."""
    if (p.get("role") or p.get("actor")) == "swallow":
        return SWALLOWS, None
    return None


def rome_rule(dist: str, p: dict):
    key = p.get("role") or p.get("actor")
    if key == "swallow":
        return SWALLOWS, None
    if dist in COUNTRY and key == "farmer":
        return F(1.0, aug=0.8, sep=0.8, dec_feb=0.85), None
    if dist in COUNTRY and key == "vinedresser":
        return F(1.0, feb=1.3, mar=1.3, sep=1.3, oct=1.3, dec=0.8, jan=0.8), None
    if key == "reveller" or key == "night_walker":
        return F(1.0, nov=0.8, dec_feb=0.6), None
    return None


def rome_events(doc: dict) -> None:
    by_id = {e["id"]: e for e in doc["events"]}
    for eid, ms in (("starlings", ["oct", "nov", "dec", "jan", "feb"]),
                    ("swifts", ["apr", "may", "jun", "jul", "aug"])):
        t = by_id[eid]["trigger"]
        t.pop("season", None)
        t["months"] = ms
    # Starlings wheel in thousands at dusk (seasons.md §3.8): a murmuration in the sky, not the
    # swallows that stood in for them (swallows are gone in winter).
    st = by_id["starlings"]
    st.pop("cast", None)
    st["steps"] = [{"emit": {"fx": "fx/world.starlings"}}]
    st["sfx"] = st.get("sfx") or "sfx/world/swifts.wav"
    doc["events"] += [
        {"id": "floralia", "rarity": "festival", "size": "medium", "zone": "circus",
         "trigger": {"on": "calendar", "festival": "floralia", "hours": ["15:00", "15:30"]},
         "duration": [150, 200], "cast": [{"role": "forum_crowd", "count": 14}, {"actor": R + "musician", "count": 2}],
         "steps": [go(node="circus_stands"), use(anim="idle", dur=(130, 180))], "sfx": "sfx/world/cheer.wav",
         "string": "floralia", "card": "floralia"},
        {"id": "october_horse", "rarity": "festival", "size": "medium", "zone": "campus",
         "trigger": {"on": "calendar", "festival": "october_horse", "hours": ["09:00", "09:30"]},
         "duration": [150, 200], "cast": [{"role": "forum_crowd", "count": 16}, {"actor": R + "racehorse", "count": 2}],
         "steps": [go(node="campus_south"), use(anim="idle", dur=(130, 180))], "sfx": "sfx/world/cheer.wav",
         "string": "october_horse", "card": "october_horse"},
        {"id": "ludi_plebeii", "rarity": "festival", "size": "large", "zone": "circus",
         "trigger": {"on": "calendar", "festival": "ludi_plebeii", "hours": ["14:00", "14:30"]},
         "duration": [200, 260], "cast": [{"role": "forum_crowd", "count": 20}],
         "steps": [go(node="circus_stands"), use(anim="idle", dur=(180, 240))], "sfx": "sfx/world/cheer.wav",
         "string": "ludi_plebeii"},
        {"id": "kalends", "rarity": "festival", "size": "medium", "zone": "capitol",
         "trigger": {"on": "calendar", "festival": "kalends", "hours": ["08:00", "08:30"]},
         "duration": [150, 200], "cast": [{"role": "forum_crowd", "count": 12}],
         "steps": [go(node="capitolium"), use(anim="idle", dur=(130, 180))], "sfx": "sfx/rome/cornu.wav",
         "string": "kalends", "card": "kalends"},
        {"id": "braziers_lit", "rarity": "daily", "size": "small", "zone": "subura",
         "trigger": {"on": "window", "hours": ["17:00", "17:30"], "months": ["nov", "dec", "jan", "feb", "mar"],
                     "chance": 1.0},
         "duration": [40, 60], "steps": [{"each": {"item": R + "r_brazier", "within": 4096}, "state": "lit",
                                          "every": 3}],
         "sfx": "sfx/world/lamp.wav", "string": "braziers"},
        {"id": "winter_dusting", "rarity": "rare", "size": "small", "zone": "forum",
         "trigger": {"on": "window", "hours": ["05:00", "07:00"], "months": ["dec", "jan", "feb"], "chance": 0.2},
         "duration": [120, 180], "steps": [{"emit": {"fx": "fx/snowflake"}}],
         "ambience": {"file": "amb/world/snow.ogg", "gain": 0.5}, "string": "dusting"},
        {"id": "vintage_treading", "rarity": "uncommon", "size": "small", "zone": "janiculum",
         "trigger": {"on": "window", "hours": ["09:00", "10:00"], "months": ["sep", "oct"], "chance": 1.0},
         "duration": [150, 200], "cast": [{"role": "vinedresser", "count": 4, "from": "district"}],
         "steps": [wander(zone="janiculum", dur=(130, 180))],
         "ambience": {"file": "amb/world/press.ogg", "gain": 0.6}, "string": "vintage"},
    ]


def rome_cards(doc: dict) -> None:
    doc["cards"]["vinalia"] = card("event", "Vinalia Rustica", "",
                                   "On 19 August Jupiter is asked to protect the vintage to come; "
                                   "Varro says the flamen of Jupiter cut the first grapes.")
    doc["cards"].update(FARM_CARDS)
    doc["cards"].update({
        "floralia": card("event", "Floralia", "Flora's games",
                         "From late April into May the games of Flora are held: plays, races and "
                         "flowers, with goats and hares let loose in the Circus."),
        "october_horse": card("event", "Equus October", "15 October",
                              "A two-horse chariot race on the Campus Martius; the right-hand horse "
                              "of the winning pair is sacrificed to Mars."),
        "kalends": card("event", "Kalends of January", "The new year",
                        "The new consuls take office, vows are made for the emperor on the "
                        "Capitol, and people give small gifts of sweets and lamps for luck."),
    })
    doc["strings"].update({
        "floralia": "The Floralia: flowers, plays and games in the Circus.",
        "october_horse": "The October Horse: a chariot race on the Campus Martius.",
        "ludi_plebeii": "The Plebeian Games: the Circus fills again.",
        "kalends": "The Kalends of January: the new consuls go up to the Capitol.",
        "braziers": "Braziers glow in the shops and at the crossroads shrines.",
        "dusting": "A dusting of snow on the roofs this morning. It will be gone by noon.",
        "vintage": "The grapes are trodden on the Janiculum.",
        "first_visit": "Rome, AD 126: the city of Hadrian, the temple of Venus and Roma rising on the Velia.",
    })


ROME_FESTIVALS = [
    {"id": "parilia", "season": "spring", "day": 2, "hours": ["04:30", "23:00"]},
    {"id": "floralia", "season": "spring", "day": 3, "hours": ["12:00", "18:00"]},
    {"id": "vestalia", "season": "summer", "day": 1, "hours": ["05:00", "18:00"]},
    {"id": "ludi_apollinares", "season": "summer", "day": 2, "hours": ["12:00", "18:00"]},
    {"id": "vinalia", "season": "summer", "day": 3, "hours": ["07:00", "12:00"]},
    {"id": "ludi_romani", "season": "autumn", "day": 1, "hours": ["12:00", "18:00"]},
    {"id": "october_horse", "season": "autumn", "day": 2, "hours": ["08:00", "13:00"]},
    {"id": "ludi_plebeii", "season": "autumn", "day": 3, "hours": ["12:00", "18:00"]},
    {"id": "saturnalia", "season": "winter", "day": 1, "hours": ["06:00", "23:00"]},
    {"id": "kalends", "season": "winter", "day": 2, "hours": ["07:00", "13:00"]},
    {"id": "lupercalia", "season": "winter", "day": 3, "hours": ["08:00", "12:00"]},
]
ROME_BEDS = {"winter": {"beds": [{"file": "amb/rome/day_winter.ogg", "hours": ["05:30", "19:30"]},
                                 {"file": "amb/rome/night.ogg", "hours": ["19:30", "05:30"]}]}}


def rome(doc: dict) -> dict:
    doc.pop("season", None)
    doc["caption"] = "Rome · AD 126"
    doc["theme"].pop("climate", None)
    doc["festivals"] = ROME_FESTIVALS
    doc["roles"] += farm_roles()
    SL.vary(doc, rome_rule)
    extra = {
        "vatican": [pop("reaper", "fields", 6, when=W(["jun", "jul"])),
                    pop("ploughman", "fields", 5, when=W(["oct", "nov"])),
                    pop("haymaker", "fields", 4, when=W(["jun"]))],
        "campagna": [pop("reaper", "fields", 6, when=W(["jun", "jul"])),
                     pop("ploughman", "fields", 5, when=W(["oct", "nov"])),
                     pop("olive_picker", "fields", 6, when=W(["nov", "dec"])),
                     pop("grape_picker", "fields", 4, when=W(["sep", "oct"])),
                     pop("shearer", "graze", 2, when=W(["may"]))],
        "janiculum": [pop("grape_picker", "fields", 6, when=W(["sep", "oct"])),
                      pop("shearer", "graze", 2, when=W(["may"]))],
    }
    for d in doc["districts"]:
        d["populations"] += extra.get(d["id"], [])
    rome_events(doc)
    by_id = {c["id"]: c for c in doc["chains"]}
    # The building site works at 0.6 in winter (seasons.md §3.7): the bricks slow down; the
    # marble and the night travertine already deliver one block a day, the least a chain may.
    by_id["rome_bricks"]["by_month"] = F(1.0, dec_feb=0.6)
    by_id["rome_fish"]["by_month"] = F(1.0, dec_feb=0.7)
    rome_cards(doc)
    doc["days_shown"] = [
        {"day": 1, "label": "The Parilia, 21 April (spring day 2): a Senate day"},
        {"day": 0, "label": "March: market day"},
        {"day": 4, "label": "July: the Ludi Apollinares"},
        {"day": 7, "label": "October: the October Horse, the vintage and games in the arena"},
        {"day": 9, "label": "December: the Saturnalia (a Senate day)"},
        {"day": 10, "label": "January: the Kalends; the grain dole"},
    ]
    return doc


# -- Ostia and Portus ----------------------------------------------------------------------------

def ostia(doc: dict) -> dict:
    doc.pop("season", None)
    doc["caption"] = "Ostia and Portus · AD 126"
    doc["theme"].pop("climate", None)
    doc["festivals"] = [
        {"id": "navigium_isidis", "season": "spring", "day": 1, "hours": ["07:00", "14:00"]},
        {"id": "grain_fleet", "months": ["may"], "hours": ["06:00", "12:00"]}]
    sea = {"sailor", "customs", "passenger"}
    dock = {"port_docker", "barge_loader", "hauler"}

    def rule(dist, p):
        key = p.get("role") or p.get("actor")
        if key in sea:
            return SEA_OPEN, None
        if key in dock and dist == "portus":
            return F(1.0, nov=0.85, dec_feb=0.75), None
        if key == "salt_worker":
            return F(1.0, nov_mar=0.85), None
        if key == "gull" and dist == "river":
            return F(1.0, oct_feb=2.0), None      # gulls winter on the river when the swallows go
        return swallows(dist, p)
    SL.vary(doc, rule)
    doc["roles"].append(work("shipwright", R + "builder", "Shipwright", [
        go(node="portus"), use(anim="work_high", dur=(40, 70)), wander(radius=5, dur=(15, 25)),
        use(anim="haul", dur=(30, 50))], "shipwright", hours=(("06:00", "12:00"), ("14:00", "18:30"))))
    for d in doc["districts"]:
        if d["id"] == "portus":
            d["populations"] += [pop("shipwright", "harbour", 16, when=W(["dec", "jan", "feb"])),
                                 pop("shipwright", "harbour", 8, when=W(["mar", "nov"]))]
    doc["events"] += [
        {"id": "navigium_isidis", "rarity": "festival", "size": "large", "zone": "portus",
         "trigger": {"on": "calendar", "festival": "navigium_isidis", "hours": ["09:00", "09:30"]},
         "duration": [200, 260], "cast": [{"role": "worshipper", "count": 14}, {"actor": R + "musician", "count": 2}],
         "steps": [go(node="portus_mole"), use(anim="idle", dur=(180, 240))], "sfx": "sfx/rome/sistrum.wav",
         "string": "navigium", "card": "navigium_isidis"},
        {"id": "hulls_ashore", "rarity": "daily", "size": "small", "zone": "portus",
         "trigger": {"on": "window", "hours": ["08:00", "09:00"], "months": ["dec", "jan", "feb"], "chance": 1.0},
         "duration": [240, 300], "cast": [{"role": "shipwright", "count": 6, "from": "district"}],
         "steps": [go(node="portus"), use(anim="work_high", dur=(200, 260))],
         "ambience": {"file": "amb/world/saw.ogg", "gain": 0.6}, "string": "hulls_ashore"},
    ]
    by_id = {e["id"]: e for e in doc["events"]}
    for eid in ("swifts",):
        if eid in by_id:
            by_id[eid]["trigger"].pop("season", None)
            by_id[eid]["trigger"]["months"] = ["apr", "may", "jun", "jul", "aug"]
    chains = {c["id"]: c for c in doc["chains"]}
    # Ships land grain while the sea is open; the warehouses send it up the Tiber all year (the
    # bread chain in Rome starts at the barges).
    chains["ostia_grain"]["months"] = ["apr", "may", "jun", "jul", "aug", "sep", "oct"]
    chains["ostia_salt"]["by_month"] = F(1.0, nov_mar=0.75)
    doc["cards"].update({
        "navigium_isidis": card("event", "Navigium Isidis", "5 March",
                                "Apuleius describes it: the priests of Isis carry a new ship to "
                                "the shore, load it with offerings and let it go, and with it the "
                                "sailing season opens."),
        "shipwright": card("role", "Faber navalis", "The closed season",
                           "While the sea is closed, hulls are hauled ashore and the shipwrights "
                           "caulk, patch and refit them for the spring."),
    })
    doc["strings"].update({
        "navigium": "The ship of Isis is launched: the sea is open again.",
        "hulls_ashore": "The sea is closed. Hulls lie hauled up on the shore; the shipwrights are at work.",
        "grain_fleet": "The grain fleet is coming in from Alexandria: a line of big ships rounds the lighthouse.",
        "first_visit": "Ostia and Portus, AD 126: Rome's harbour, where the grain ships come in from Alexandria.",
    })
    doc["days_shown"] = [{"day": 0, "label": "The ship of Isis, 5 March (spring day 1)"},
                         {"day": 2, "label": "May: the grain fleet comes in"},
                         {"day": 3, "label": "June: a working day at the port"},
                         {"day": 10, "label": "January: the sea closed, hulls ashore"}]
    return doc


# -- the Alban Mount -----------------------------------------------------------------------------

def alban(doc: dict) -> dict:
    doc.pop("season", None)
    doc["caption"] = "The Alban Mount · AD 126"
    doc["theme"].pop("climate", None)

    def rule(dist, p):
        key = p.get("role") or p.get("actor")
        if key == "vinedresser":
            return F(1.0, feb=1.3, mar=1.3, sep=1.4, oct=1.4, dec=0.7, jan=0.7), None
        if key == "logger":
            return F(1.0, nov=1.2, dec_feb=1.4, jun_aug=0.8), None
        if key == "pilgrim":
            return F(1.0, dec_feb=0.95), None
        return swallows(dist, p)
    SL.vary(doc, rule)
    by_id = {e["id"]: e for e in doc["events"]}
    if "swifts" in by_id:
        by_id["swifts"]["trigger"].pop("season", None)
        by_id["swifts"]["trigger"]["months"] = ["apr", "may", "jun", "jul", "aug"]
    doc["strings"]["first_visit"] = ("The Alban Mount. The paved way climbs to Jupiter's sanctuary above "
                                     "the crater lake; in winter its summit is white.")
    doc["days_shown"] = [{"day": 2, "label": "The Latin Festival (spring day 3, May)"},
                         {"day": 0, "label": "A March day on the mount"},
                         {"day": 7, "label": "October: the vintage on the slopes"},
                         {"day": 10, "label": "January: snow on the summit"}]
    return doc


# -- Brundisium ------------------------------------------------------------------------------------

def brundisium(doc: dict) -> dict:
    doc.pop("season", None)
    doc["caption"] = "Brundisium · AD 126"
    doc["theme"].pop("climate", None)

    def rule(dist, p):
        key = p.get("role") or p.get("actor")
        if key in ("passenger", "merchant") and dist == "harbour":
            return [0.8, 0.9, 1, 1, 1, 1, 1, 0.9, 0.8, 0.7, 0.7, 0.7], None
        if key == "sailor":
            return SEA_OPEN, None
        return None
    SL.vary(doc, rule)
    doc["roles"].append(work("shipwright", R + "builder", "Shipwright", [
        go(node="brundisium_quay"), use(anim="work_high", dur=(40, 70)), wander(radius=5, dur=(15, 25)),
        use(anim="haul", dur=(30, 50))], "shipwright", hours=(("06:00", "12:00"), ("14:00", "18:30"))))
    for d in doc["districts"]:
        if d["id"] == "harbour":
            d["populations"] += [pop("shipwright", "harbour", 18, when=W(["dec", "jan", "feb"])),
                                 pop("shipwright", "harbour", 10, when=W(["mar", "nov"])),
                                 pop("shipwright", "harbour", 4, when=W(["apr", "oct"]))]
    doc["cards"]["shipwright"] = card("role", "Faber navalis", "The closed season",
                                      "While the sea is closed, hulls are hauled ashore and the "
                                      "shipwrights caulk, patch and refit them for the spring.")
    doc["strings"]["hulls_ashore"] = "The sea is closed. Hulls lie hauled up on the shore."
    chains = {c["id"]: c for c in doc["chains"]}
    chains["brundisium_wine"]["months"] = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct"]
    chains["brundisium_fish"]["by_month"] = F(1.0, dec_feb=0.7)
    by_id = {e["id"]: e for e in doc["events"]}
    if "ship_departs" in by_id:
        by_id["ship_departs"]["trigger"]["months"] = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct"]
    doc["days_shown"] = [{"day": 1, "label": "April: ships leave for Greece"},
                         {"day": 10, "label": "January: the sea closed"}]
    return doc
