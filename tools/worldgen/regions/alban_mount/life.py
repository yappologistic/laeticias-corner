"""The Alban Mount in April AD 126: Jupiter Latiaris's sanctuary on the summit, the crater lake,
flocks and vines on the slopes, woodcutters in the oak woods, and travellers on the Via Appia at
the mount's foot (`assets/regions/alban_mount.json`). The Latin Festival is shown on a spring day;
its date was set by the consuls each year, so the card says so. Shared Roman roles come from
`regions/rome/townlife.py`.

Built by `tools/worldgen/build.sh --city alban_mount`, checked by `worldgen.citylife`.
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
    X = T.borrow("shepherd", "sheep", "goat", "dog", "farmer", "vinedresser", "mourner", "swallow")

    def add(*a, **kw):
        X.append(role(*a, **kw))

    add("priest", R + "flamen", "Priest of Jupiter Latiaris", sched(("05:30", "11:30", "offer"), ("15:00", "18:00", "offer")),
        {"offer": loop(go(home="sacrifice"), use({"home": "sacrifice"}, anim="pour", dur=(30, 50)),
                       use(anim="pray", dur=(20, 30)))},
        home={"item": R + "latiaris", "slot": "sacrifice"}, card="flamen")
    add("attendant", R + "enslaved", "Temple servant", sched(("05:00", "12:00", "tend"), ("14:00", "18:30", "tend")),
        {"tend": loop(go(node="latiaris"), use(anim="work_low", dur=(30, 50)), {"take": "world.goods_firewood"},
                      wander(radius=4, dur=(15, 25)), {"put": "world.goods_firewood"})}, card="enslaved")
    add("pilgrim", R + "citizen", "Pilgrim on the summit", sched(("06:30", "12:00", "climb"), ("14:00", "18:00", "climb")),
        {"climb": loop(go(node="latiaris"), use(anim="idle", dur=(30, 50)), use(anim="talk", dur=(15, 25)),
                       wander(radius=5, dur=(20, 30)), go(node="villas"), wait(dur=(15, 25))),
         "shelter": T.shelter_door(30)}, interrupts=[T.RAIN], card="pilgrim")
    add("logger", "world.logger", "Woodcutter", sched(("06:00", "11:30", "cut"), ("14:00", "18:00", "cut")),
        {"cut": loop(wander(radius=6, dur=(20, 40)), use(anim="work_high", dur=(40, 60)), use(anim="haul", dur=(20, 30)))},
        card="woodcutter")
    add("lake_fisher", "world.fisher", "Fisherman on the lake", sched(("05:00", "11:00", "fish"), ("15:00", "19:00", "fish")),
        {"fish": loop(wander(radius=4, dur=(20, 30)), use(anim="work_low", dur=(40, 60)), use(anim="sit", dur=(30, 50)))},
        card="lake")
    add("traveller", "world.traveller", "Traveller on the Via Appia", sched(("05:30", "18:30", "travel")),
        {"travel": loop(go(node="appia_foot"), use(anim="sit", dur=(15, 25)), wander(radius=8, dur=(30, 50)))},
        card="cursus_role")
    add("wine_mule", R + "mule", "Mule with wine", sched(("06:00", "17:30", "carry")),
        {"carry": loop(go(item=R + "r_villa_farm", slot="door"), use(anim="idle", dur=(15, 25)), go(node="appia_foot"),
                       use(anim="graze", dur=(15, 25)))}, card="mules")
    add("wine_cart", R + "cart", "Cart for Rome", sched(("06:00", "18:00", "haul")),
        {"haul": loop(go(node="appia_foot"), wait(dur=(60, 100)), wander(radius=10, dur=(40, 60)))},
        locomotion={"mode": "walk", "speed": 0.6, "network": "roads", "turn_radius": 2}, card="site_cart")
    add("magistrate", R + "togatus", "Magistrate of a Latin town", sched(("07:00", "14:00", "festival")),
        {"festival": loop(go(node="latiaris"), use(anim="gesture", dur=(30, 50)), use(anim="talk", dur=(20, 30)))},
        card="feriae_latinae")
    return X


def districts() -> list[dict]:
    fest = {"festival": "feriae_latinae"}
    return [
        {"id": "summit", "area": "country", "populations": [
            per("priest", "latiaris", 1, "morning"), pop("attendant", "work", 4), pop("pilgrim", "day", 18),
            pop("magistrate", "day", 8, when=fest), pop("pilgrim", "festival", 12, when=fest)]},
        {"id": "slopes", "area": "country", "populations": [
            pop("shepherd", "graze", 3), pop("sheep", "graze", 10), pop("goat", "graze", 4), pop("dog", "always", 1),
            per("farmer", "r_villa_farm", 3, "fields"), pop("vinedresser", "fields", 6), pop("pilgrim", "day", 4),
            pop("wine_mule", "work", 2), pop("swallow", "birds", 2)]},
        {"id": "woods", "area": "wild", "populations": [
            pop("logger", "work", 4), pop("goat", "graze", 3), pop("swallow", "birds", 2)]},
        {"id": "lake", "area": "wild", "populations": [pop("lake_fisher", "harbour", 6), pop("swallow", "birds", 4)]},
        {"id": "road", "area": "road", "populations": [
            pop("traveller", "road", 12), pop("wine_cart", "day", 2), per("mourner", "r_tomb", 1, "day"),
            pop("dog", "always", 1)]},
    ]


def chains() -> list[dict]:
    return [
        {"id": "alban_wine", "name": "Alban wine for the road", "period": 200, "hours": ["06:00", "17:30"], "stages": [
            {"slot": R + "r_villa_farm.door", "makes": R + "goods_wine_amphora", "by": "farmer",
             "label": "an amphora of the hill's wine from the villa's cellar"},
            {"carry": R + "goods_wine_amphora", "from": R + "r_villa_farm.door", "to": "node:appia_foot",
             "by": "wine_mule", "units": 2},
            {"slot": "node:appia_foot", "sink": R + "goods_wine_amphora", "by": "wine_cart",
             "label": "loaded on a cart for Rome"}]},
    ]


FESTIVALS = [{"id": "feriae_latinae", "season": "spring", "day": 3, "hours": ["07:00", "14:00"]}]


def events() -> list[dict]:
    return [
        ev("feriae_latinae", "festival", "large", {"on": "calendar", "festival": "feriae_latinae", "hours": ["08:00", "08:30"]},
           (100, 120), [go(node="latiaris"), use(item=R + "latiaris", slot="sacrifice", anim="idle", dur=(40, 60)),
                        {"emit": {"sfx": "sfx/rome/tibia.wav"}}],
           route=["appia_foot", "villas", "latiaris"],
           cast=[{"role": "magistrate", "count": 6}, {"role": "priest", "count": 1}, {"actor": R + "lictor", "count": 4},
                 {"actor": R + "musician", "count": 2}, {"actor": R + "ox", "count": 1},
                 {"role": "pilgrim", "count": 12, "from": "district"}],
           ambience={"file": "amb/rome/procession.ogg", "gain": 0.7}, card="feriae_latinae", string="feriae"),
        ev("summit_sacrifice", "common", "small", window(("07:30", "08:00"), 0.6, not_festival="feriae_latinae"), (70, 90),
           [use(item=R + "latiaris", slot="sacrifice", anim="pour", dur=(50, 70)), {"emit": {"sfx": "sfx/rome/tibia.wav"}}],
           zone="summit", cast=[{"role": "priest", "count": 1}, {"role": "pilgrim", "count": 4}], card="latiaris"),
        ev("flock_out", "daily", "small", window(("05:30", "06:00")), (80, 100), [wander(zone="slopes", dur=(70, 90))],
           zone="slopes", cast=[{"role": "shepherd", "count": 1}, {"actor": R + "sheep", "count": 8},
                                {"actor": R + "dog_molossian", "count": 1}], sfx="sfx/world/sheep_bells.wav",
           card="shepherd"),
        ev("lake_mist", "common", "small", {"on": "window", "hours": ["04:00", "06:30"], "chance": 0.5,
                                             "season": ["spring", "autumn"]}, (120, 150), [{"emit": {"fx": "mist"}}],
           zone="lake", card="lake"),
        ev("woodcutting", "common", "small", window(("09:00", "16:00"), every=2400), (40, 60),
           [use(anim="work_high", dur=(30, 50)), {"emit": {"sfx": "sfx/world/hammer.wav"}}], zone="woods",
           cast=[{"role": "logger", "count": 2}], card="woodcutter"),
        ev("swifts", "daily", "small", window(("18:00", "18:30"), season=["spring", "summer"]), (60, 80),
           [wander(radius=12, dur=(50, 70))], zone="summit", cast=[{"actor": "world.swift", "count": 6}],
           sfx="sfx/world/swifts.wav"),
    ]


def cards() -> dict:
    L, I, RO = "landmark", "idea", "role"
    c = {
        "latiaris": card(L, "Iuppiter Latiaris", "On the Alban Mount",
            "Jupiter's sanctuary on the summit of the Alban Mount, the old meeting place of the Latin peoples, "
            "where the consuls lead the Latin Festival each year. Below it lies the round crater lake; the Via "
            "Appia passes at the mount's foot."),
        "feriae_latinae": card(I, "Feriae Latinae", "The Latin Festival",
            "Each year, on a day the new consuls set, usually in spring, Rome's magistrates climb the Alban Mount "
            "with delegates of the old Latin towns. A white bull is sacrificed to Jupiter Latiaris and its meat "
            "shared among the towns, a memory of the league that Rome once led and then swallowed. The game "
            "shows it on the third day of spring."),
        "lake": card(I, "Lacus Albanus", "The crater lake",
            "The lake fills the crater of an old volcano. In the war against Veii, Livy says, the Romans cut a "
            "tunnel to drain its rising water, and the outlet is still there. Fishermen work its shores, and "
            "mist lies on it on spring mornings."),
        "alban_wine": card(I, "Vinum Albanum", "Alban wine",
            "The volcanic slopes of the Alban hills made a wine Romans praised; Horace and Pliny both name it. "
            "Villas on the slopes send it down by mule to the Via Appia, where carts take it on to Rome's "
            "tables and taverns."),
        "pilgrim": card(RO, "Peregrinator", "", "Pilgrims climb the paved way to Jupiter's sanctuary to pray and make "
                        "an offering."),
        "woodcutter": card(RO, "Lignator", "", "Woodcutters fell oak and chestnut in the woods of the mount for "
                           "firewood and charcoal."),
    }
    c.update(T.role_cards(roles()))
    return c


def build(view) -> dict:
    return {
        "version": 1, "id": "alban_mount", "name": "Mons Albanus", "native": "Mons Albanus",
        "caption": "The Alban Mount · April AD 126", "era": "The Rome of Hadrian · AD 126", "season": "spring",
        "theme": T.theme([{"file": "amb/world/fields.ogg", "hours": ["05:00", "19:30"]},
                          {"file": "amb/world/desert_night.ogg", "hours": ["19:30", "05:00"]}],
                         [{"rect": grid_rect(view, "woods"), "file": "amb/world/mountain.ogg", "gain": 0.5},
                          {"rect": grid_rect(view, "road"), "file": "amb/world/road.ogg", "gain": 0.5,
                           "hours": ["05:30", "19:00"]}],
                         [], "April showers; mist on the crater lake at dawn"),
        "densities": T.DENSITIES,
        "districts": districts(),
        "roles": roles(),
        "groups": [],
        "chains": chains(),
        "festivals": FESTIVALS,
        "events": events(),
        "days_shown": [{"day": 0, "label": "An April day on the mount"},
                       {"day": 2, "label": "The Latin Festival (spring, day 3)"}],
        "figures": [],
        "lanes_tokens": [],
        "cards": cards(),
        "strings": {"first_visit": "The Alban Mount. The paved way climbs to Jupiter's sanctuary above the crater lake.",
                    "feriae": "The Latin Festival: the magistrates climb to Jupiter's altar with a white bull."},
        "journal": ["landmark:*", "chain:*", "idea:*", "event:feriae_latinae"],
    }
