"""The land and the sea between the cities (81 % of the map): who works and lives on it, by the
month and the hour, anchored on what the base layer places there.

Every population is either spread over a district (`max_per_chunk`) or bound to placed items
(`per_item`), so people stand where their work is: grooms and guests at the relay stations,
station keepers at the mutationes, watchmen on the towers and beacons, shepherds at their folds
with the flock out day and night, farm families at the farmsteads, woodcutters in the woods,
olive pickers in the groves in the olive months, resin tappers in the pines, beekeepers in the
thyme, reed cutters in the marshes, palm climbers in the date groves, goatherds on the maquis,
Thracian riders with their horses, gazelles on the steppe, owls over Greek fields at night,
cranes by the reeds. Months come from the region's climate (`worldgen/climates.py`); the base's
`pasture` districts, which the region files left out, get their herds.

The seams of time get a sparse life of their own (sheep in the dell, ravens in the mist).
"""

from __future__ import annotations

from plan import world_plan as P

# The kinds each era's countryside uses (set catalogs; a region carries home, world and its own
# set's ids only).
KINDS = {
    "rome": {"farmer": "rome.farmer", "shepherd": "rome.shepherd", "keeper": "rome.freedman",
             "guard": "rome.vigil", "hen": "rome.hen", "donkey": "rome.donkey",
             "mule": "rome.mule", "horse": "rome.horse", "woman": "rome.working_woman",
             "herder": "rome.shepherd", "owl": "world.owl"},
    "athens": {"farmer": "athens.farmer", "shepherd": "athens.herder", "keeper": "athens.metic",
               "guard": "athens.citizen", "hen": "athens.hen", "donkey": "athens.donkey",
               "mule": "athens.mule", "horse": "athens.horse", "woman": "athens.woman",
               "herder": "athens.herder", "owl": "athens.owl"},
    "parsa": {"farmer": "parsa.farmer", "shepherd": "parsa.shepherd", "keeper": "parsa.groom",
              "guard": "parsa.guard_spear", "hen": None, "donkey": "world.donkey",
              "mule": "world.mule", "horse": "parsa.nisaean_horse", "woman": "parsa.woman_worker",
              "herder": "parsa.shepherd", "owl": "world.owl"},
}

HERONS = {"latium_italy", "ionia_lydia", "thrace", "anatolia", "mesopotamia", "susiana"}
WOODS = {"thrace", "latium_italy", "apennines", "greece", "arcadia"}
FOREST = {"world.t_oak", "world.t_beech", "world.t_fir", "world.t_cedar", "rome.t_oak",
          "athens.t_pine", "world.t_oak_zagros"}
STATIONS = {"world.royal_station": "parsa", "rome.mutatio": "rome"}
FARMSTEAD = {"rome": "rome.r_villa_farm", "athens": "athens.g_farmstead", "parsa": "parsa.p_house_small"}
WOOD_MONTHS = ["oct", "nov", "dec", "jan", "feb", "mar"]   # timber is felled in the cold months
# Area kinds of the base's districts (citylife.AREA): what a screenful of each should hold.
AREAS = {"road": "road", "farm": "country", "pasture": "country", "land": "wild", "sea": "sea",
         "dell": "wild", "mist": "wild"}
ALL = ["mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "jan", "feb"]


def _anim(kinds: dict, actor: str, want: str) -> str:
    """`want` if the kind has it, else its idle, else its walk (a bird drawn only in flight)."""
    have = kinds.get(actor, {want, "idle"})
    return want if want in have else "idle" if "idle" in have else "move"


def _role(id_, actor, name, schedule, routines, **kw) -> dict:
    return {"id": id_, "actor": actor, "name": name, "schedule": schedule, "routines": routines,
            **kw}


def _at(item: str, anim: str, work=(30, 60), radius: int = 3) -> dict:
    """Work beside the nearest placed item, step about, work again."""
    return {"loop": True, "steps": [
        {"go": {"item": item, "spot": "beside", "within": 12}},
        {"use": {"here": True}, "anim": anim, "dur": list(work)},
        {"wander": {"radius": radius}, "dur": [10, 20]},
        {"use": {"here": True}, "anim": anim, "dur": [work[0] // 2, work[1] // 2]}]}


def _rest(item: str, anim: str, until: str) -> dict:
    return {"steps": [{"go": {"item": item, "spot": "beside", "within": 12}},
                      {"use": {"here": True}, "anim": anim, "until": {"hour": until}}]}


def _wander(anim: str, radius: int = 8) -> dict:
    return {"loop": True, "steps": [{"wander": {"radius": radius}, "dur": [20, 40]},
                                    {"use": {"here": True}, "anim": anim, "dur": [20, 40]}]}


def _months(*spans: list[str] | None) -> list[str]:
    seen = set()
    for s in spans:
        seen |= set(s or [])
    return [m for m in ALL if m in seen]


def _district(doc: dict, did: str) -> dict:
    d = next((x for x in doc["districts"] if x["id"] == did), None)
    if d is None:
        d = {"id": did, "populations": []}
        doc["districts"].append(d)
    return d


def apply(doc: dict, clim: dict, items: dict[str, dict[str, int]], kinds: dict) -> None:
    """Add the countryside's roles and populations to a stretch or seam file. `items` maps the
    region's district ids to the placed items (counts) the base layer holds there; `kinds` maps
    actor kinds to their animations."""
    rid = doc["id"]
    kind_, set_, *_ = P.REGIONS[rid]
    if kind_ == "seam":
        _seam(doc)
        return
    K = KINDS.get(set_)
    if K is None:   # the open seas of the world set: gulls and traffic only
        for d in doc["districts"]:
            d.setdefault("area", AREAS.get(d["id"], "wild"))
        return
    roles: list[dict] = []
    work = clim.get("work", {})
    have = {d["id"] for d in doc["districts"]} | set(items)

    def role(r):
        if r["id"] not in {x["id"] for x in roles}:
            roles.append(r)

    def per(did, rid_or_actor, item, count, density="always", months=None, actor=False):
        if not items.get(did, {}).get(item):
            return
        p = {("actor" if actor else "role"): rid_or_actor, "per_item": item, "count": count,
             "density": density}
        if months and len(months) < 12:
            p["when"] = {"months": months}
        _district(doc, did)["populations"].append(p)

    # -- relay stations and mutationes: keepers day and night, guests by night, relay animals
    for item, era in STATIONS.items():
        if era != set_:
            continue
        keeper = K["keeper"]
        role(_role("station_keeper", keeper, "Station keeper" if era == "parsa" else "Innkeeper of the mutatio",
                   [{"hours": ["05:00", "21:00"], "routine": "tend"},
                    {"hours": ["21:00", "05:00"], "routine": "watch"}],
                   {"tend": _at(item, _anim(kinds, keeper, "stir" if era == "parsa" else "serve")),
                    "watch": _rest(item, "idle", "05:00")}))
        role(_role("station_guest", "world.traveller", "Traveller resting at the station",
                   [{"hours": ["19:30", "05:30"], "routine": "rest"}],
                   {"rest": _rest(item, "sit", "05:30")}))
        animal = K["horse"] if era == "parsa" else K["mule"]
        role(_role("relay_animal", animal, "Relay horse" if era == "parsa" else "Change of mules",
                   [{"hours": ["00:00", "24:00"], "routine": "graze"}],
                   {"graze": _at(item, _anim(kinds, animal, "graze"), (40, 80), 2)}))
        for did in sorted(items):
            per(did, "station_keeper", item, 1)
            per(did, "station_guest", item, 0.7)
            per(did, "relay_animal", item, 0.7)
    # -- watchtowers and beacons: a watchman, awake all night
    if set_ == "parsa":
        guard = K["guard"]
        role(_role("watchman", guard, "Watchman on the tower",
                   [{"hours": ["18:00", "07:00"], "routine": "watch"},
                    {"hours": ["07:00", "18:00"], "routine": "day"}],
                   {"watch": {"loop": True, "steps": [
                       {"go": {"item": "world.watchtower", "spot": "beside", "within": 12}},
                       {"use": {"here": True}, "anim": _anim(kinds, guard, "guard"), "dur": [60, 120]},
                       {"wander": {"radius": 2}, "dur": [10, 20]}]},
                    "day": _at("world.watchtower", _anim(kinds, guard, "guard"), (60, 120), 2)}))
        for did in sorted(items):
            per(did, "watchman", "world.watchtower", 1)
    # -- a harbour's or a pass's beacon has its keeper wherever it stands
    if any(v.get("world.beacon") for v in items.values()):
        guard = K["guard"]
        role(_role("beacon_keeper", guard, "Beacon keeper",
                   [{"hours": ["17:00", "06:00"], "routine": "watch"}],
                   {"watch": _at("world.beacon", _anim(kinds, guard, "guard"), (60, 120), 2)}))
        for did in sorted(items):
            per(did, "beacon_keeper", "world.beacon", 1)
    # -- shepherds at their folds; the flock out day and night
    shep = K["shepherd"]
    role(_role("shepherd", shep, "Shepherd",
               [{"hours": ["05:00", "19:30"], "routine": "graze"},
                {"hours": ["19:30", "05:00"], "routine": "fold"}],
               {"graze": _wander(_anim(kinds, shep, "gesture"), 8),
                "fold": {"steps": [{"wander": {"radius": 2}, "dur": [10, 20]},
                                   {"use": {"here": True}, "anim": "idle",
                                    "until": {"hour": "05:00"}}]}}))
    for did in sorted(items):
        if items[did].get("world.sheepfold"):
            per(did, "shepherd", "world.sheepfold", 1)
            per(did, "world.sheep", "world.sheepfold", 3, "herd", actor=True)
            per(did, "world.dog", "world.sheepfold", 0.5, actor=True)
    if "pasture" in have:
        d = _district(doc, "pasture")
        sheep_v = 1 if set_ == "parsa" else 0
        d["populations"] += [
            {"role": "shepherd", "density": "herd", "max_per_chunk": 1},
            {"actor": "world.sheep", "variant": sheep_v, "density": "herd", "max_per_chunk": 4},
            {"actor": "world.goat", "density": "herd", "max_per_chunk": 2},
            {"actor": "world.dog", "density": "always", "max_per_chunk": 1}]
        if set_ == "parsa":
            horse = K["horse"]
            role(_role("horse_herd", horse, "Horses at pasture",
                       [{"hours": ["00:00", "24:00"], "routine": "graze"}],
                       {"graze": _wander(_anim(kinds, horse, "graze"), 6)}))
            d["populations"].append({"role": "horse_herd", "density": "herd",
                                     "max_per_chunk": 1.5})
    # -- farms: the family at work and at the door in the evening; dogs all night
    if "farm" in have:
        farmer = K["farmer"]
        role(_role("farmer", farmer, "Farmer",
                   [{"hours": ["05:30", "12:00"], "routine": "work"},
                    {"hours": ["14:30", "18:30"], "routine": "work"},
                    {"hours": ["18:30", "21:00"], "routine": "evening"}],
                   {"work": _wander(_anim(kinds, farmer, "work_low"), 6),
                    "evening": {"loop": True, "steps": [{"wander": {"radius": 3}, "dur": [10, 20]},
                                                        {"use": {"here": True}, "anim": "idle",
                                                         "dur": [40, 80]}]}}))
        d = _district(doc, "farm")
        d["populations"] = [p for p in d["populations"]
                            if p.get("actor") not in (farmer, "world.dog")]
        d["populations"] += [{"role": "farmer", "density": "always", "max_per_chunk": 3},
                             {"actor": "world.dog", "density": "always", "max_per_chunk": 1}]
        home = FARMSTEAD[set_]
        if items.get("farm", {}).get(home):
            if K["hen"]:
                role(_role("hens", K["hen"], "Hens in the yard",
                           [{"hours": ["06:00", "19:30"], "routine": "peck"}],
                           {"peck": _at(home, "peck", (30, 60), 2)}))
                per("farm", "hens", home, 2)
            donkey = K["donkey"]
            role(_role("yard_donkey", donkey, "Donkey in the yard",
                       [{"hours": ["00:00", "24:00"], "routine": "stand"}],
                       {"stand": _at(home, _anim(kinds, donkey, "graze"), (60, 120), 2)}))
            per("farm", "yard_donkey", home, 0.5)
        if items.get("farm", {}).get("world.charcoal_kiln"):
            role(_role("charcoal_burner", farmer, "Charcoal burner",
                       [{"hours": ["00:00", "24:00"], "routine": "burn"}],
                       {"burn": _at("world.charcoal_kiln", _anim(kinds, farmer, "work_low"), (60, 120), 2)}))
            # A stack smoulders for days and is watched day and night.
            per("farm", "charcoal_burner", "world.charcoal_kiln", 1,
                months=_months(work.get("charcoal"), ["nov", "dec", "jan", "feb", "mar"]))
    # -- the land: work bound to what grows there, by the month
    land = items.get("land", {})
    if "land" in have:
        logger = "world.logger"
        trees = sorted(t for t in FOREST if land.get(t))
        if trees:
            role(_role("woodcutter", logger, "Woodcutter",
                       [{"hours": ["06:30", "12:00"], "routine": "cut"},
                        {"hours": ["14:00", "17:30"], "routine": "cut"}],
                       {"cut": {"loop": True, "steps": [
                           {"wander": {"radius": 4}, "dur": [10, 20]},
                           {"use": {"here": True}, "anim": "work_high", "dur": [40, 70]},
                           {"use": {"here": True}, "anim": "haul", "dur": [15, 25]}]}}))
            for t in trees:
                per("land", "woodcutter", t, 0.012, months=WOOD_MONTHS)
                per("land", "woodcutter", t, 0.004,
                    months=[m for m in ALL if m not in WOOD_MONTHS])
        farmer = K["farmer"]
        olive = {"rome": "rome.t_olive", "athens": "athens.t_olive"}.get(set_)
        if olive and land.get(olive) and work.get("olive"):
            role(_role("olive_picker", farmer, "Olive picker",
                       [{"hours": ["07:00", "12:00"], "routine": "pick"},
                        {"hours": ["13:30", "17:00"], "routine": "pick"}],
                       {"pick": _at(olive, _anim(kinds, farmer, "work_high" if set_ == "rome" else "work_low"))}))
            per("land", "olive_picker", olive, 0.02, months=work["olive"])
        if set_ == "athens" and land.get("athens.t_pine"):
            role(_role("resin_tapper", farmer, "Resin tapper",
                       [{"hours": ["06:00", "11:00"], "routine": "tap"},
                        {"hours": ["16:00", "19:00"], "routine": "tap"}],
                       {"tap": _at("athens.t_pine", _anim(kinds, farmer, "work_low"))}))
            per("land", "resin_tapper", "athens.t_pine", 0.01,
                months=["jun", "jul", "aug", "sep"])
        if set_ == "athens" and land.get("athens.p_thyme") and clim.get("fauna", {}).get("bees"):
            role(_role("beekeeper", farmer, "Beekeeper",
                       [{"hours": ["07:00", "11:00"], "routine": "hives"},
                        {"hours": ["16:00", "18:30"], "routine": "hives"}],
                       {"hives": _at("athens.p_thyme", _anim(kinds, farmer, "work_low"), (30, 50), 4)}))
            per("land", "beekeeper", "athens.p_thyme", 0.012,
                months=clim["fauna"]["bees"])
        if set_ == "parsa" and land.get("world.t_reeds") and work.get("dates_harvest"):
            role(_role("reed_cutter", farmer, "Reed cutter",
                       [{"hours": ["06:00", "11:00"], "routine": "cut"},
                        {"hours": ["15:30", "18:30"], "routine": "cut"}],
                       {"cut": _at("world.t_reeds", _anim(kinds, farmer, "work_low"))}))
            per("land", "reed_cutter", "world.t_reeds", 0.02,
                months=["oct", "nov", "dec", "jan", "feb", "mar"])
        if set_ == "parsa" and land.get("parsa.t_date"):
            months = _months(work.get("dates_harvest"), work.get("dates_pollinate"))
            if months:
                role(_role("palm_climber", "parsa.gardener", "Climber in the palms",
                           [{"hours": ["06:00", "11:00"], "routine": "climb"},
                            {"hours": ["15:30", "18:00"], "routine": "climb"}],
                           {"climb": _at("parsa.t_date", "work_high")}))
                per("land", "palm_climber", "parsa.t_date", 0.015, months=months)
        if set_ == "athens" and rid != "thrace":
            herder = K["herder"]
            role(_role("goatherd", herder, "Goatherd on the hills",
                       [{"hours": ["05:30", "19:00"], "routine": "herd"}],
                       {"herd": _wander("idle", 10)}))
            pops = _district(doc, "land")["populations"]
            pops += [{"role": "goatherd", "density": "daytime", "max_per_chunk": 0.25},
                     {"actor": "world.goat", "density": "daytime", "max_per_chunk": 1.2}]
        if rid == "thrace":
            role(_role("thracian_rider", "athens.thracian", "Thracian with his horses",
                       [{"hours": ["06:00", "19:00"], "routine": "ride"}],
                       {"ride": _wander("idle", 12)}))
            role(_role("horse_herd", "athens.horse", "Thracian horses",
                       [{"hours": ["00:00", "24:00"], "routine": "graze"}],
                       {"graze": _wander("graze", 6)}))
            _district(doc, "land")["populations"] += [
                {"role": "thracian_rider", "density": "daytime", "max_per_chunk": 0.3},
                {"role": "horse_herd", "density": "herd", "max_per_chunk": 0.8},
                {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.5}]
            per("land", "thracian_rider", "world.tumulus", 0.3, "daytime")
        if set_ == "parsa" and rid in ("iran_plateau", "anatolia", "zagros"):
            role(_role("gazelle", "world.gazelle", "Gazelles",
                       [{"hours": ["04:30", "20:30"], "routine": "graze"}],
                       {"graze": _wander("graze", 10)}))
            _district(doc, "land")["populations"].append(
                {"role": "gazelle", "density": "daytime", "max_per_chunk": 0.3})
        if K["owl"]:
            role(_role("owl", K["owl"], "Little owl" if K["owl"] == "athens.owl" else "Owl",
                       [{"hours": ["19:30", "05:30"], "routine": "hunt"}],
                       {"hunt": {"loop": True, "steps": [{"wander": {"radius": 5}, "dur": [30, 60]},
                                                         {"use": {"here": True},
                                                          "anim": _anim(kinds, K["owl"], "idle"),
                                                          "dur": [40, 90]}]}}))
            _district(doc, "land")["populations"].append(
                {"role": "owl", "density": "night", "max_per_chunk": 0.5})
        if set_ in ("rome", "parsa"):
            _district(doc, "land")["populations"].append(
                {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.25})
        # Herons in the reed beds and by the rivers; red deer and wild boar in the woods.
        if rid in HERONS:
            _district(doc, "land")["populations"].append(
                {"actor": "world.heron", "density": "daytime", "max_per_chunk": 0.2})
        if rid in WOODS:
            _district(doc, "land")["populations"] += [
                {"actor": "world.deer", "density": "fields", "max_per_chunk": 0.15},
                {"actor": "world.boar", "density": "night", "max_per_chunk": 0.1}]
        if set_ == "athens" and items.get("land", {}).get("athens.g_shrine"):
            role(_role("shrine_keeper", "athens.priest", "Keeper of a country shrine",
                       [{"hours": ["06:30", "11:00"], "routine": "offer"},
                        {"hours": ["16:00", "18:30"], "routine": "offer"}],
                       {"offer": _at("athens.g_shrine", _anim(kinds, "athens.priest", "pour"), (40, 70), 2)}))
            per("land", "shrine_keeper", "athens.g_shrine", 1)
    # Only the roles some population uses (a region without folds has no fold shepherd).
    used = {p.get("role") for d in doc["districts"] for p in d.get("populations", [])}
    roles = [r for r in roles if r["id"] in used]
    doc["roles"] = [r for r in doc.get("roles", []) if r["id"] not in {x["id"] for x in roles}] + roles
    for d in doc["districts"]:
        d.setdefault("area", AREAS.get(d["id"], "wild"))


def _seam(doc: dict) -> None:
    """A seam of time is quiet, never empty: sheep in the corner's dell, ravens and goats in the
    mists, gulls over the Ionian mist band."""
    rid = doc["id"]
    if rid == "seam_dell":
        doc["districts"] += [
            {"id": "dell", "populations": [
                {"actor": "world.sheep", "density": "herd", "max_per_chunk": 3},
                {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.6}]},
            {"id": "mist", "populations": [
                {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.6}]}]
    elif rid == "seam_ionian":
        doc["districts"].append({"id": "mist", "populations": [
            {"actor": "world.gull", "density": "daytime", "max_per_chunk": 1}]})
    elif rid == "seam_ionia":
        doc["districts"].append({"id": "mist", "populations": [
            {"actor": "world.goat", "density": "herd", "max_per_chunk": 1.5},
            {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.6},
            {"actor": "world.traveller", "density": "daytime", "max_per_chunk": 0.4}]})
    for d in doc["districts"]:
        d.setdefault("area", AREAS.get(d["id"], "wild"))


# -- the year's events between the cities ----------------------------------------------------
# (id, months, start hour, cast [(actor, n)], animation, sound, line, district, fx, trigger)
# Casts walk in the named district; sea events are seen and heard, not cast. Hours are game
# hours; an event lasts two to three game hours.

def E(id_, months, hour, cast, anim, sfx, line, zone, fx=None, on="window"):
    return (id_, months, hour, cast, anim, sfx, line, zone, fx, on)


SPRING, SUMMER, AUTUMN, WINTER = (["mar", "apr", "may"], ["jun", "jul", "aug"],
                                  ["sep", "oct", "nov"], ["dec", "jan", "feb"])
EVENTS = {
    "latium_italy": [
        E("robigalia", ["apr"], "07:00", [("rome.flamen", 1), ("rome.citizen", 6), ("rome.farmer", 4)],
          "idle", "sfx/rome/tibia.wav", "The Robigalia: a procession goes out to Robigus' grove to "
          "keep the rust from the young wheat.", "land"),
        E("ambarvalia", ["may"], "07:30", [("rome.farmer", 4), ("rome.pig", 1), ("rome.sheep", 1),
                                           ("rome.ox", 1)], "idle", "sfx/rome/tibia.wav",
          "Farmers lead a pig, a sheep and a bull round their fields to purify them.", "farm"),
        E("vinalia_rustica", ["aug"], "08:00", [("rome.farmer", 5), ("rome.working_woman", 3)],
          "work_low", "sfx/world/pour.wav", "The country Vinalia: the first grapes are cut for "
          "Jupiter.", "farm"),
        E("country_saturnalia", ["dec"], "17:00", [("rome.farmer", 6), ("rome.working_woman", 3)],
          "idle", "sfx/rome/tibia.wav", "The Saturnalia on the farms: masters wait on their "
          "slaves for a day.", "farm"),
        E("rain_at_the_mutatio", None, "08:00", [("world.traveller", 4)], "idle",
          "amb/world/rain_roof_1.ogg", "Rain: travellers crowd under the eaves of the mutatio.",
          "road", on="rain")],
    "apennines": [
        E("lambing", ["feb", "mar", "apr"], "06:30", [("rome.shepherd", 2), ("rome.sheep", 6)],
          "idle", "sfx/world/sheep_1.wav", "Lambing time at the mountain folds.", "land"),
        E("high_pastures", SUMMER, "07:00", [("rome.shepherd", 2), ("rome.sheep", 8),
                                             ("rome.dog", 1)], "idle", "sfx/world/sheep_bells.wav",
          "The flocks of the plain are up on the high pastures for the summer.", "land"),
        E("charcoal_kilns", ["oct", "nov"], "08:00", [("world.logger", 3)], "work_high",
          "sfx/world/chop.wav", "Charcoal kilns smoke in the beech woods.", "land",
          fx="fx/rome.smoke"),
        E("snow_on_the_pass", WINTER, "09:00", [("world.traveller", 3), ("rome.mule", 2)], "idle",
          "amb/world/snow.ogg", "Snow on the pass: travellers wait at the mutatio for it to "
          "clear.", "road")],
    "greece": [
        E("shearing", ["apr", "may"], "07:30", [("athens.herder", 2), ("athens.sheep", 6)], "idle",
          "sfx/world/sheep_bells.wav", "Shearing time: the flocks are brought down to the "
          "farms.", "farm"),
        E("threshing", ["jun", "jul"], "07:00", [("athens.farmer", 4), ("athens.mule", 2)],
          "work_low", "amb/world/threshing.ogg", "Mules tread the sheaves on the threshing floors.",
          "farm"),
        E("vintage", ["sep"], "08:00", [("athens.farmer", 4), ("athens.woman", 2)], "work_low",
          "sfx/world/pour.wav", "The vintage: grapes are trodden in the vats.", "farm"),
        E("olive_harvest", ["nov", "dec", "jan"], "08:00", [("athens.farmer", 5), ("athens.woman", 3)],
          "work_low", "sfx/world/sickle.wav", "Olive harvest: the trees are beaten and the fruit "
          "gathered on cloths.", "land"),
        E("rural_dionysia", ["dec", "jan"], "16:00", [("athens.citizen", 8), ("athens.woman", 3),
                                                     ("athens.musician", 1), ("athens.goat", 1)],
          "idle", "sfx/athens/aulos.wav", "The country Dionysia: a village procession with songs, "
          "the aulos and a goat.", "farm"),
        E("goatherds_shelter", None, "10:00", [("athens.herder", 2), ("world.goat", 6)], "idle",
          "amb/world/rain_leaves_1.ogg", "Rain: goatherds shelter their flocks under the pines.",
          "land", on="rain")],
    "attica_north": [
        E("bees_swarm", ["apr", "may"], "09:00", [("athens.farmer", 2)], "work_low",
          "sfx/world/lark.wav", "Beekeepers smoke the hives on the thyme slopes.", "land"),
        E("harvest_home", ["jun"], "17:00", [("athens.farmer", 4), ("athens.woman", 2)], "idle",
          "sfx/athens/aulos.wav", "The last sheaf is in: a harvest meal on the threshing floor.",
          "farm"),
        E("pressing", ["sep", "oct"], "08:00", [("athens.farmer", 3)], "work_low",
          "amb/world/press.ogg", "The presses are working: new wine and oil.", "farm"),
        E("charcoal_on_parnes", WINTER, "08:00", [("athens.farmer", 2)], "work_low",
          "sfx/world/chop.wav", "Charcoal burners tend their stacks on Parnes.", "farm",
          fx="fx/smoke")],
    "arcadia": [
        E("lambing", ["feb", "mar", "apr"], "06:30", [("athens.herder", 2), ("athens.sheep", 6)],
          "idle", "sfx/world/sheep_1.wav", "Lambing time in the high valleys of Pan.", "land"),
        E("lykaia", ["jul"], "09:00", [("athens.athlete", 4), ("athens.citizen", 6),
                                       ("athens.herder", 2)], "idle", "sfx/world/cheer.wav",
          "The Lykaia: Arcadians gather for games on the mountain of Zeus Lykaios.", "land"),
        E("flocks_down", ["sep", "oct"], "07:00", [("athens.herder", 2), ("athens.sheep", 8)],
          "idle", "sfx/world/sheep_bells.wav", "The flocks go down to the coast for the winter.",
          "land"),
        E("snow_on_the_peaks", WINTER, "17:00", [("athens.herder", 2)], "idle",
          "amb/world/hearth.ogg", "Snow on the peaks: herders sit by the fire in the fold.",
          "land")],
    "thrace": [
        E("horses_to_pasture", ["mar", "apr"], "07:00", [("athens.thracian", 2), ("athens.horse", 4)],
          "idle", "sfx/world/horse_whinny.wav", "Thracians drive their horses out to the spring "
          "grass.", "land"),
        E("thracian_harvest", ["jul"], "07:00", [("athens.thracian", 4)], "idle",
          "sfx/world/sickle.wav", "Harvest in the Thracian plain.", "land"),
        E("hunting_party", ["oct", "nov"], "07:30", [("athens.thracian", 3), ("athens.horse", 2),
                                                    ("athens.dog_molossian", 2)], "idle",
          "sfx/world/dog_far.wav", "A Thracian hunting party rides out with its hounds.", "land"),
        E("wood_smoke", WINTER, "17:00", [("athens.thracian", 2)], "idle", "amb/world/hearth.ogg",
          "Wood smoke over the villages on a cold evening.", "land", fx="fx/smoke")],
    "ionia_lydia": [
        E("asian_meadow", ["mar"], "07:00", [("world.crane", 8)], "move", "sfx/world/cranes.wav",
          "Cranes settle on the Asian meadow by the Kaystros, as in Homer.", "land"),
        E("ionian_harvest", ["jun", "jul"], "07:00", [("athens.farmer", 4)], "work_low",
          "sfx/world/sickle.wav", "Harvest in the Kaystros valley.", "land"),
        E("ionian_vintage", ["sep", "oct"], "08:00", [("athens.farmer", 3), ("athens.woman", 2)],
          "work_low", "sfx/world/pour.wav", "The vintage in the Ionian hills.", "land"),
        E("ionian_olives", ["nov", "dec"], "08:00", [("athens.farmer", 4)], "work_low",
          "sfx/world/sickle.wav", "Olive picking on the terraces.", "land")],
    "anatolia": [
        E("shearing", ["may"], "07:30", [("parsa.shepherd", 2), ("world.sheep", 6)], "idle",
          "sfx/world/sheep_bells.wav", "Shearing at the folds on the plateau.", "pasture"),
        E("threshing", ["aug"], "07:00", [("parsa.farmer", 3), ("world.ox", 2)], "work_low",
          "amb/world/threshing.ogg", "Oxen draw the threshing sledges round the floors.", "farm"),
        E("flocks_down", ["oct"], "07:00", [("parsa.shepherd", 2), ("world.sheep", 8),
                                            ("world.dog", 1)], "idle", "sfx/world/sheep_bells.wav",
          "The flocks come down from the high pastures.", "pasture"),
        E("snowbound_station", WINTER, "16:00", [("world.traveller", 4), ("parsa.groom", 1)], "idle",
          "amb/world/hearth.ogg", "Snow on the road: travellers wait at the station.", "land")],
    "taurus": [
        E("flocks_up", ["may"], "07:00", [("parsa.shepherd", 2), ("world.sheep", 8)], "idle",
          "sfx/world/sheep_bells.wav", "The flocks climb to the summer pastures.", "pasture"),
        E("high_summer", SUMMER, "07:30", [("parsa.shepherd", 1), ("world.goat", 6)], "idle",
          "sfx/world/goat_1.wav", "Goats on the high slopes under the snow.", "land"),
        E("flocks_down", ["sep", "oct"], "07:00", [("parsa.shepherd", 2), ("world.sheep", 8)],
          "idle", "sfx/world/sheep_bells.wav", "The flocks go down to the Cilician plain.",
          "pasture"),
        E("pass_closed", WINTER, "09:00", [("world.muleteer", 2), ("world.mule", 3)], "idle",
          "amb/world/snow.ogg", "Snow in the Cilician Gates: the mule trains wait.", "road")],
    "east_med": [
        E("cedar_hauling", None, "08:00", [("world.logger", 3)], "haul", "sfx/world/chop.wav",
          "Loggers drag cedar trunks down towards the coast.", "land"),
        E("levant_harvest", ["may", "jun"], "07:00", [("parsa.farmer", 3)], "work_low",
          "sfx/world/sickle.wav", "Harvest on the coastal plain.", "land"),
        E("levant_vintage", ["sep"], "08:00", [("parsa.farmer", 3)], "work_low",
          "sfx/world/pour.wav", "The vintage below the mountains.", "land"),
        E("winter_storm", WINTER, "14:00", [], "idle", "sfx/world/thunder_far.wav",
          "A winter storm over the sea: the ships stay in harbour.", "sea",
          fx="fx/world.whitecap")],
    "mesopotamia": [
        E("palm_pollination", ["mar", "apr"], "08:00", [("parsa.gardener", 4)], "work_high",
          "sfx/world/rope.wav", "Climbers in the palms dust the female flowers.", "land"),
        E("barley_harvest", ["apr", "may"], "07:00", [("parsa.farmer", 5)], "work_low",
          "sfx/world/sickle.wav", "The barley harvest on the alluvium.", "land"),
        E("canal_clearing", ["jul", "aug", "sep"], "05:30", [("parsa.labourer", 5)], "haul",
          "sfx/world/chop.wav", "Crews clear the silt from the canals before the flood.", "land"),
        E("seed_ploughs", ["nov", "dec"], "07:00", [("parsa.farmer", 2), ("world.ox", 2)],
          "work_low", "sfx/world/step_earth_1.wav", "Oxen draw the seeder ploughs over the "
          "fields.", "land")],
    "susiana": [
        E("susiana_harvest", ["apr"], "07:00", [("parsa.farmer", 4)], "work_low",
          "sfx/world/sickle.wav", "Harvest in the irrigated plain of Susa.", "land"),
        E("canal_clearing", ["jul", "aug"], "05:30", [("parsa.labourer", 4)], "haul",
          "sfx/world/chop.wav", "Crews clear the canals in the heat, at first light.", "land"),
        E("susiana_dates", ["sep", "oct"], "07:00", [("parsa.gardener", 4)], "work_high",
          "sfx/world/chop.wav", "Climbers cut the heavy clusters of dates.", "land"),
        E("winter_ploughing", ["oct", "nov", "dec"], "07:00", [("parsa.farmer", 2), ("world.ox", 2)],
          "work_low", "sfx/world/step_earth_1.wav", "Ploughing after the first rains.", "land")],
    "syrian_steppe": [
        E("green_steppe", ["mar", "apr"], "07:00", [("parsa.shepherd", 2), ("world.sheep", 8)],
          "idle", "sfx/world/sheep_bells.wav", "The steppe is green: herders bring their flocks.",
          "land"),
        E("night_caravan", SUMMER, "21:00", [("parsa.caravan_driver", 2), ("parsa.dromedary", 5)],
          "idle", "sfx/parsa/camel.wav", "In the summer heat the caravans travel by night.",
          "land"),
        E("gazelles", ["oct", "nov"], "06:30", [("world.gazelle", 6)], "graze",
          "sfx/world/hoof_earth_1.wav", "A herd of gazelles crosses the steppe.", "land"),
        E("rain_pools", WINTER, "09:00", [("parsa.shepherd", 2), ("world.goat", 6)], "idle",
          "sfx/world/goat_1.wav", "Winter rain fills the pools; the herds drink.", "land")],
    "zagros": [
        E("flocks_climb", ["apr", "may"], "06:30", [("parsa.shepherd", 2), ("world.sheep", 8),
                                                   ("world.goat", 4)], "idle",
          "sfx/world/sheep_bells.wav", "The herders climb with their flocks to the summer "
          "pastures.", "land"),
        E("oak_woods", ["jul", "aug"], "08:00", [("world.logger", 2)], "work_high",
          "sfx/world/chop.wav", "Woodcutters in the oak woods of the mountains.", "land"),
        E("flocks_descend", ["sep", "oct"], "06:30", [("parsa.shepherd", 2), ("world.sheep", 8)],
          "idle", "sfx/world/sheep_bells.wav", "The flocks come down towards Susiana.", "land"),
        E("passes_snowbound", WINTER, "10:00", [("world.traveller", 3)], "idle",
          "amb/world/snow.ogg", "Snow closes the high passes.", "road")],
    "iran_plateau": [
        E("almond_blossom", ["mar"], "08:00", [("parsa.gardener", 2)], "work_low",
          "sfx/world/cuckoo.wav", "The almond trees are in blossom.", "land"),
        E("plateau_harvest", ["jul"], "07:00", [("parsa.farmer", 4)], "work_low",
          "sfx/world/sickle.wav", "Harvest on the high plain.", "land"),
        E("pistachio_harvest", ["sep", "oct"], "08:00", [("parsa.farmer", 3)], "work_low",
          "sfx/world/sickle.wav", "Pistachios are knocked from the trees.", "land"),
        E("winter_horses", WINTER, "10:00", [("parsa.nisaean_horse", 6)], "graze",
          "sfx/world/horse_blow.wav", "Horse herds graze the valley floors under the snow "
          "line.", "pasture")],
    "tyrrhenian": [
        E("grain_fleet_sighted", ["may", "jun"], "09:00", [], "idle", "sfx/world/gull_call.wav",
          "Sails on the horizon: the grain fleet from Alexandria.", "sea", fx="fx/world.wake"),
        E("dolphins", SUMMER, "10:00", [("world.dolphin", 3)], "move",
          "sfx/world/gull.wav", "Dolphins play in a ship's wake.", "sea"),
        E("autumn_storm", ["oct", "nov"], "14:00", [], "idle", "sfx/world/thunder_far.wav",
          "An autumn storm rolls in from the sea.", "sea", fx="fx/world.whitecap"),
        E("winter_gale", WINTER, "11:00", [], "idle", "sfx/world/gust_front.wav",
          "A winter gale: the sea is closed.", "sea", fx="fx/world.whitecap")],
    "adriatic": [
        E("fishing_fleet", ["apr", "may"], "05:00", [], "idle", "sfx/world/gull_call.wav",
          "The fishing boats are out at first light.", "sea", fx="fx/world.wake"),
        E("dolphins", SUMMER, "10:00", [("world.dolphin", 3)], "move",
          "sfx/world/gull.wav", "Dolphins in the calm summer sea.", "sea"),
        E("bora_squall", ["oct", "nov"], "13:00", [], "idle", "sfx/world/gust_front.wav",
          "A squall of the north wind tears across the sea.", "sea", fx="fx/world.whitecap"),
        E("winter_bora", WINTER, "10:00", [], "idle", "sfx/world/gust_front.wav",
          "The cold north wind blows for days.", "sea", fx="fx/world.whitecap")],
    "ionian_sea": [
        E("dolphins", ["apr", "may"], "10:00", [("world.dolphin", 3)], "move",
          "sfx/world/gull.wav", "Dolphins run beside the sea lane.", "sea"),
        E("summer_glitter", SUMMER, "12:00", [], "idle", "sfx/world/gull_call.wav",
          "The summer sea glitters under the noon sun.", "sea", fx="fx/athens.sea_glint"),
        E("autumn_storm", ["oct", "nov"], "14:00", [], "idle", "sfx/world/thunder_far.wav",
          "Storm clouds over the Ionian sea.", "sea", fx="fx/world.whitecap"),
        E("winter_gale", WINTER, "11:00", [], "idle", "sfx/world/gust_front.wav",
          "A winter gale: no ship crosses now.", "sea", fx="fx/world.whitecap")],
    "saronic": [
        E("triremes_put_out", ["mar", "apr"], "08:00", [], "idle", "sfx/athens/oars.wav",
          "The first triremes of the year put out from Piraeus.", "sea", fx="fx/world.wake"),
        E("trireme_drill", SUMMER, "09:00", [], "idle", "sfx/athens/trireme.wav",
          "Triremes drill in the gulf, oars flashing in time.", "sea", fx="fx/world.wake"),
        E("autumn_storm", ["oct", "nov"], "14:00", [], "idle", "sfx/world/thunder_far.wav",
          "Autumn storms over Aegina.", "sea", fx="fx/world.whitecap"),
        E("empty_gulf", WINTER, "11:00", [], "idle", "sfx/world/gust_front.wav",
          "The ships are in their sheds; only fishing boats go out.", "sea",
          fx="fx/world.whitecap")],
    "aegean": [
        E("dolphins", ["apr", "may"], "10:00", [("world.dolphin", 3)], "move",
          "sfx/world/gull.wav", "Dolphins among the Cyclades.", "sea"),
        E("meltemi_afternoon", ["jul", "aug"], "14:00", [], "idle", "sfx/world/gust_front.wav",
          "The north wind whitens the crests in the afternoon.", "sea", fx="fx/world.whitecap"),
        E("tunny_run", ["sep", "oct"], "07:00", [], "idle", "sfx/world/fish.wav",
          "The tunny shoals run through the straits; the fishermen watch for them.", "sea",
          fx="fx/world.fish_shoal"),
        E("winter_storm", WINTER, "12:00", [], "idle", "sfx/world/thunder_far.wav",
          "A winter storm over the islands.", "sea", fx="fx/world.whitecap")],
    "persian_gulf": [
        E("date_boats", ["sep", "oct"], "07:00", [], "idle", "sfx/world/rope.wav",
          "Boats loaded with the new dates.", "sea", fx="fx/world.wake"),
        E("shimmer", SUMMER, "12:00", [], "idle", "amb/world/heat.ogg",
          "The shallow sea shimmers in the heat.", "sea", fx="fx/world.shimmer"),
        E("fish_shoals", SPRING, "06:30", [], "idle", "sfx/world/fish.wav",
          "Shoals break the surface at dawn.", "sea", fx="fx/world.fish_shoal"),
        E("shamal", WINTER, "13:00", [], "idle", "sfx/world/gust_front.wav",
          "The north-west wind blows dust over the water.", "sea", fx="fx/world.whitecap")],
    "seam_dell": [
        E("dell_mist", SPRING + AUTUMN, "05:00", [], "idle", "sfx/world/seam.wav",
          "Mist lies in the dell at dawn.", "dell", fx="weather/seam_mist"),
        E("swifts_over_the_dell", SUMMER, "19:00", [("world.swift", 6)], "move",
          "sfx/world/swifts.wav", "Swifts scream over the dell at dusk.", "dell"),
        E("frost_mist", WINTER, "07:00", [], "idle", "sfx/world/seam.wav",
          "A frosty mist hangs over the stile.", "dell", fx="weather/seam_mist")],
    "seam_ionian": [
        E("golden_mist", SPRING + SUMMER, "17:00", [], "idle", "sfx/world/seam.wav",
          "The golden mist bank glows in the evening light.", "mist", fx="weather/seam_mist"),
        E("mist_bell", AUTUMN + WINTER, "06:00", [], "idle", "sfx/world/seam.wav",
          "A bell sounds somewhere inside the mist.", "mist", fx="weather/seam_mist")],
    "seam_ionia": [
        E("hill_haze", SPRING + SUMMER, "15:00", [], "idle", "sfx/world/seam.wav",
          "A faint haze over the Kaystros hills: the years change here.", "mist",
          fx="weather/seam_haze"),
        E("haze_at_dawn", AUTUMN + WINTER, "06:00", [("world.goat", 4)], "idle",
          "sfx/world/goat_2.wav", "Goats graze in the dawn haze between two ages.", "mist")],
}


def events(doc: dict, kinds: dict, table: list | None = None) -> None:
    """The region's events (EVENTS, or `table`): casts in their district, sea events seen and
    heard."""
    table = EVENTS.get(doc["id"], []) if table is None else table
    out = [e for e in doc.get("events", []) if e["id"] not in {x[0] for x in table}]
    strings = doc.setdefault("strings", {})
    dists = {d["id"] for d in doc.get("districts", [])}
    for id_, months, hour, cast, anim, sfx, line, zone, fx, on in table:
        if zone not in dists:
            continue
        if not all(anim in kinds.get(a, {anim}) for a, _ in cast):
            anim = "idle" if all("idle" in kinds.get(a, {"idle"}) for a, _ in cast) else "move"
        h, m = (int(x) for x in hour.split(":"))
        trig = {"on": "window", "hours": [hour, f"{h:02d}:{m + 30:02d}" if m < 30 else
                                          f"{h + 1:02d}:{m - 30:02d}"], "chance": 0.7}
        if on == "rain":
            trig = {"on": "weather", "kind": "rain"}
        if months:
            trig["months"] = list(months)
        steps = []
        if fx:
            steps.append({"emit": {"fx": fx}})
        if cast:
            steps += [{"wander": {"radius": 8}, "dur": [30, 50]},
                      {"use": {"here": True}, "anim": anim, "dur": [60, 90]}]
        e = {"id": id_, "rarity": "seasonal" if months else "common", "size": "small",
             "trigger": trig, "duration": [90, 150], "cast": [{"actor": a, "count": n} for a, n in cast],
             "steps": steps, "zone": zone, "string": id_}
        if sfx.endswith(".ogg"):
            # Never a bed the land itself plays: one file is one loop in the engine.
            assert sfx not in COUNTRY_BEDS, f"{id_}: {sfx} is the land's own bed"
            e["ambience"] = {"file": sfx, "gain": 0.6}
        else:
            e["sfx"] = sfx
        out.append(e)
        strings[id_] = line
    doc["events"] = out


# -- the corner's surroundings ------------------------------------------------------------------
# The home plot is the player's; around it the corner layer holds a borderland (cities/world.md
# §7): meadows with sheep, a beech and oak wood, a strip of coast with the jetty, two farmsteads
# and the old road. Its people are of no time (world kinds only: the country farmer works the
# farms, keeps the bees and herds the sheep).

# The country's own beds (`theme.ambience.beds`): an event that named one as its ambience made the
# same loop answer to two systems.
COUNTRY_BEDS = {"amb/world/fields.ogg", "amb/world/road.ogg", "amb/world/mountain.ogg",
                "amb/world/desert_night.ogg", "amb/world/sea.ogg", "amb/world/river.ogg"}

CORNER_EVENTS = [
    E("lambing", ["mar", "apr"], "06:30", [("world.sheep", 6), ("world.farmer", 1)], "idle",
      "sfx/world/sheep_1.wav", "Lambs in the meadows.", "meadows"),
    E("haymaking", ["jun", "jul"], "08:00", [("world.farmer", 4)], "carry",
      "sfx/world/sickle.wav", "Haymaking: the grass is cut and raked into rows.", "farms"),
    E("berry_picking", ["sep", "oct"], "09:00", [("world.farmer", 3)], "carry",
      "sfx/world/starlings.wav", "Blackberries and apples are picked along the hedges.", "meadows"),
    E("woodcutting", ["dec", "jan", "feb"], "09:00", [("world.logger", 2)], "work_high",
      "sfx/world/chop.wav", "Woodcutters in the winter wood.", "wood"),
    E("nets_hauled", None, "06:00", [("world.fisher", 2)], "haul", "sfx/world/rope.wav",
      "Fishers haul their nets on the shore at first light.", "coast"),
    E("flock_home", None, "18:30", [("world.sheep", 6), ("world.dog", 1)], "idle",
      "sfx/world/sheep_bells.wav", "The flock is brought in at dusk.", "meadows"),
]


def corner_file(placed: dict[str, dict[str, int]], kinds: dict) -> dict:
    """The corner region's life file (the borderland around the home plot)."""
    farm_items = placed.get("farms", {})
    roles = [
        _role("farmhand", "world.farmer", "Farm folk",
              [{"hours": ["05:30", "12:00"], "routine": "work"},
               {"hours": ["14:00", "18:30"], "routine": "work"},
               {"hours": ["18:30", "21:00"], "routine": "evening"}],
              {"work": _at("barn" if farm_items.get("barn") else "cottage", "carry"),
               "evening": _rest("cottage", _anim(kinds, "world.farmer", "sit"), "21:00")}),
        _role("shepherd", "world.farmer", "Shepherd on the hills",
              [{"hours": ["05:30", "19:30"], "routine": "graze"}],
              {"graze": _wander(_anim(kinds, "world.farmer", "sit"), 8)}),
        _role("fisher", "world.fisher", "Fisher on the shore",
              [{"hours": ["04:30", "11:00"], "routine": "fish"},
               {"hours": ["16:00", "20:00"], "routine": "fish"}],
              {"fish": _wander(_anim(kinds, "world.fisher", "work_low"), 6)}),
        _role("woodcutter", "world.logger", "Woodcutter",
              [{"hours": ["07:00", "12:00"], "routine": "cut"},
               {"hours": ["13:30", "17:00"], "routine": "cut"}],
              {"cut": _at("oak", "work_high", (40, 70))}),
        _role("beekeeper", "world.farmer", "Beekeeper",
              [{"hours": ["08:00", "11:00"], "routine": "hives"}],
              {"hives": _at("beehive", "idle", (40, 60), 2)}),
    ]
    districts = [
        {"id": "road", "area": "road", "populations": [
            {"actor": "world.traveller", "density": "road_day", "max_per_chunk": 6},
            {"actor": "world.donkey", "density": "road_day", "max_per_chunk": 2}]},
        {"id": "farms", "area": "country", "populations": [
            {"role": "farmhand", "density": "always", "max_per_chunk": 6},
            {"actor": "world.ox", "density": "fields", "max_per_chunk": 2},
            {"actor": "world.donkey", "density": "always", "max_per_chunk": 1},
            {"actor": "world.dog", "density": "always", "max_per_chunk": 1.5},
            {"role": "beekeeper", "per_item": "beehive", "count": 0.5, "density": "always",
             "when": {"months": ["apr", "may", "jun", "jul", "aug", "sep"]}}]},
        {"id": "meadows", "area": "country", "populations": [
            {"role": "shepherd", "density": "daytime", "max_per_chunk": 0.6},
            {"actor": "world.sheep", "density": "herd", "max_per_chunk": 5},
            {"actor": "world.goat", "density": "herd", "max_per_chunk": 1},
            {"actor": "world.dog", "density": "always", "max_per_chunk": 0.3},
            {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.4}]},
        {"id": "wood", "area": "wild", "populations": [
            {"role": "woodcutter", "per_item": "oak", "count": 0.01, "density": "always"},
            {"actor": "world.raven", "density": "daytime", "max_per_chunk": 0.8}]},
        {"id": "coast", "area": "country", "populations": [
            {"role": "fisher", "density": "always", "max_per_chunk": 3},
            {"actor": "world.gull", "density": "daytime", "max_per_chunk": 2}]},
        {"id": "reserved", "area": "wild", "populations": [
            {"actor": "world.gull", "density": "daytime", "max_per_chunk": 1}]},
    ]
    doc = {"version": 1, "id": "corner", "name": "The corner", "caption": "The corner",
           "theme": {}, "districts": districts, "densities": {}, "figures": [],
           "groups": [], "chains": [], "events": [], "lanes_tokens": [], "zones": [],
           "roles": roles, "cards": {}, "strings": {}, "journal": []}
    events(doc, kinds, CORNER_EVENTS)
    return doc


def merge_months(doc: dict) -> None:
    """Entries of one family (same role or kind, density, place and filters but months) that
    overlap in some months become one entry per run of months with their numbers summed: the
    ploughing months' extra oxen join the year's oxen instead of doubling the entry."""
    import copy
    import json
    for d in doc.get("districts", []):
        fams: dict[str, list[dict]] = {}
        order: list[str] = []
        for p in d.get("populations", []):
            w = {k: v for k, v in p.get("when", {}).items() if k != "months"}
            key = json.dumps([p.get("role") or p.get("actor"), p.get("per_item"),
                              p.get("density"), p.get("variant"), w], sort_keys=True)
            if key not in fams:
                order.append(key)
            fams.setdefault(key, []).append(p)
        out = []
        for key in order:
            ps = fams[key]
            sets = [set(p.get("when", {}).get("months") or ALL) for p in ps]
            if len(ps) == 1 or not any(a & b for i, a in enumerate(sets) for b in sets[i + 1:]):
                out += ps
                continue
            num = "count" if "per_item" in ps[0] else "max_per_chunk"
            groups: dict[float, list[str]] = {}
            for m in ALL:
                n = round(sum(p.get(num, 0) for p, s in zip(ps, sets) if m in s), 3)
                if n > 0:
                    groups.setdefault(n, []).append(m)
            for n, ms in groups.items():
                e = copy.deepcopy(ps[0])
                e[num] = n
                w = e.setdefault("when", {})
                w.pop("months", None)
                if len(ms) < 12:
                    w["months"] = ms
                if not w:
                    e.pop("when")
                out.append(e)
        d["populations"] = out


# -- ambient life for the engine's sky and sea layer (audit-alive §7 item 6) ----------------------
# Not actors: creatures drawn as functions of time and place over what is in view, never counted
# against the live cap. Each entry: what, where (land, sea, coast, river, wood, town), hours,
# months, how many in a screenful, the sprite (an fx or an actor kind drawn small; null where
# the art does not exist yet) and its sound.

def ambient(doc: dict, clim: dict) -> None:
    rid = doc["id"]
    kind_, set_, *_ = P.REGIONS[rid]
    fa = clim.get("fauna", {})
    dists = {d["id"] for d in doc.get("districts", [])}
    sea = bool(dists & {"sea", "harbour", "shore", "harbours", "mist"}) or kind_ == "stretch" and \
        "sea" in dists
    land = bool(dists - {"sea"})
    out = []

    def add(what, where, hours, months, per_screen, sprite, sound=None):
        e = {"kind": what, "where": where, "hours": hours, "per_screen": per_screen,
             "sprite": sprite}
        if months and len(months) < 12:
            e["months"] = months
        if sound:
            e["sound"] = sound
        out.append(e)

    if land:
        add("bats", "land", ["19:30", "05:00"], ["apr", "may", "jun", "jul", "aug", "sep", "oct"],
            2, "world.bat")
        add("moths", "town" if kind_ == "town" else "land", ["20:00", "04:00"],
            ["may", "jun", "jul", "aug", "sep"], 3, "fx/moth")
        owl = KINDS.get(set_, {}).get("owl") or "world.owl"
        add("owl", "land", ["20:00", "05:00"], None, 0.3, owl,
            "sfx/athens/owl.wav" if owl == "athens.owl" else "sfx/world/owl_tawny.wav")
        if fa.get("fireflies"):
            add("fireflies", "land", ["21:00", "01:00"], fa["fireflies"], 6, "fx/sparkle")
        if fa.get("nightingales"):
            add("nightingale", "wood", ["22:00", "04:00"], fa["nightingales"], 0, None,
                "sfx/world/nightingale.wav")
        if fa.get("swifts"):
            add("swifts", "town" if kind_ == "town" else "land", ["18:30", "20:30"], fa["swifts"],
                8, "world.swift", "sfx/world/swifts.wav")
        if fa.get("starlings"):
            add("starlings", "land", ["17:00", "18:30"], fa["starlings"], 40, None,
                "sfx/world/starlings.wav")
        if fa.get("cranes_pass"):
            add("cranes_overhead", "land", ["07:00", "17:00"], fa["cranes_pass"], 12, "world.crane",
                "sfx/world/cranes.wav")
    if sea:
        add("gulls", "coast", ["05:00", "20:00"], None, 4, "world.gull", "sfx/world/gull_call.wav")
        add("dolphins", "sea", ["06:00", "19:00"], ["apr", "may", "jun", "jul", "aug", "sep"], 0.4,
            "world.dolphin")
        add("fish_shoal", "sea", ["05:00", "09:00"], None, 0.5, "fx/world.fish_shoal",
            "sfx/world/fish.wav")
        add("shearwaters", "sea", ["21:00", "04:00"], ["mar", "apr", "may", "jun", "jul", "aug",
                                                      "sep", "oct"], 3, None)
    if out:
        doc["ambient"] = out
