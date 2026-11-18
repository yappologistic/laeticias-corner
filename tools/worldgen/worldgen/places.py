"""Names and eras at every level, so the engine can caption a view with the most specific place
it is over: a district's `name`, its region's `name` and `caption`, and the region's `era` (the
edge caption: which time this land is in). City files keep their own names and captions; the
stretches, seas and seams get specific ones here instead of their plan labels (an earlier sweep
saw "Latium Italy" over the Forum and "Anatolia" at Susa); every district gets a name.
"""

from __future__ import annotations

from plan import world_plan as P

ERA = {"rome": "The Rome of Hadrian · AD 126", "athens": "The Athens of Pericles · 432 BC",
       "parsa": "The Persian empire of Xerxes · c. 470 BC"}
# The time a stretch's caption names (its season is the calendar's: seasons.md §6.2).
MOMENT = {"rome": "AD 126", "athens": "432 BC", "parsa": "c. 470 BC"}
# Seas and seams belong to the time on whose side they lie (world.md §8).
SIDE = {"tyrrhenian": "rome", "adriatic": "rome", "ionian_sea": "rome", "aegean": "athens",
        "saronic": "athens", "east_med": "parsa", "persian_gulf": "parsa"}
STRETCH = {
    "latium_italy": "Latium", "apennines": "The Apennines", "adriatic": "The Adriatic Sea",
    "tyrrhenian": "The Tyrrhenian Sea", "ionian_sea": "The Ionian Sea", "greece": "Greece",
    "attica_north": "Northern Attica", "arcadia": "Arcadia", "thrace": "Thrace",
    "aegean": "The Aegean Sea", "saronic": "The Saronic Gulf",
    "east_med": "The coast of Syria", "ionia_lydia": "Ionia", "anatolia": "Anatolia",
    "syrian_steppe": "The Syrian steppe", "mesopotamia": "Mesopotamia", "susiana": "Susiana",
    "taurus": "The Taurus", "zagros": "The Zagros", "iran_plateau": "The Iranian plateau",
    "persian_gulf": "The Persian Gulf",
}
SEAMS = {"seam_dell": ("The misty dell", "Between the corner and Rome"),
         "seam_ionian": ("The Ionian mist", "Between AD 126 and 432 BC"),
         "seam_ionia": ("The haze over the Kaystros hills", "Between 432 and c. 470 BC")}
# District names: per region where they are proper places, then by district id.
DISTRICTS = {
    "rome": {"forum": "Forum Romanum", "fora": "The imperial fora", "markets": "Trajan's Markets",
             "capitol": "The Capitol", "velia": "The Velia", "colosseum": "The Colosseum valley",
             "palatine": "The Palatine", "circus": "Circus Maximus", "velabrum": "Velabrum",
             "boarium": "Forum Boarium", "island": "Tiber Island", "emporium": "The Emporium",
             "river": "The Tiber banks", "campus": "Campus Martius", "subura": "Subura",
             "quirinal": "The Quirinal", "esquiline": "The Esquiline", "oppian": "The Oppian",
             "castra": "Castra Praetoria", "caelian": "The Caelian", "aventine": "The Aventine",
             "transtiberim": "Transtiberim", "janiculum": "The Janiculum",
             "vatican": "The Vatican plain", "campagna": "The Campagna", "appia": "Via Appia",
             "decorate": "Rome"},
    "athens": {"agora": "The Agora", "council": "The Bouleuterion and the Tholos",
               "kerameikos": "Kerameikos", "cemetery": "The Kerameikos cemetery",
               "acropolis": "The Acropolis", "slopes": "The Acropolis slopes",
               "areopagus": "The Areopagus", "pnyx": "The Pnyx", "kolonos": "Kolonos Agoraios",
               "dionysos": "The sanctuary of Dionysos", "melite": "Melite", "koile": "Koile",
               "kollytos": "Kollytos", "kydathenaion": "Kydathenaion",
               "skambonidai": "Skambonidai", "east_quarter": "The eastern quarter",
               "piraeus": "Piraeus", "harbour": "The Kantharos", "long_walls": "The Long Walls",
               "north_fields": "Fields north of the walls",
               "south_fields": "Fields south of the walls", "ilissos": "The Ilissos",
               "countryside": "The Attic countryside", "lyceum": "The Lyceum",
               "pentelikon": "Pentelikon", "lykabettos": "Lykabettos", "hymettos": "Hymettos",
               "mouseion": "The Mouseion hill"},
    "parsa": {"terrace": "The terrace", "audience": "The Apadāna",
              "building_site": "The Hall of a Hundred Columns", "garrison": "The garrison",
              "palaces": "The palaces", "treasury": "The Treasury",
              "slope": "Kuh-e Raḥmat", "quarry": "The quarry", "paradise": "The paradise",
              "garden_strip": "The gardens below the terrace", "forecourt": "The forecourt",
              "town": "The town", "workers": "The workers' quarter",
              "crafts": "The craftsmen's quarter", "village": "The village", "fields": "The fields",
              "stables": "The stables", "river": "The Pulvar banks",
              "station": "The royal road station", "cavalry": "The cavalry camp",
              "camp": "The delegations' camp", "southern_plain": "The southern plain",
              "naqsh": "Naqsh-e Rostam", "plain": "The Marvdasht plain"},
    "ostia": {"town": "Ostia", "forum": "The forum of Ostia", "portus": "Portus",
              "harbour": "Claudius' harbour", "river": "The Tiber mouth", "sea": "The sea",
              "isola_sacra": "Isola Sacra", "fields": "The fields", "road": "Via Ostiensis",
              "saltpans": "The salt pans"},
    "alban_mount": {"summit": "The summit sanctuary", "slopes": "The slopes", "woods": "The woods",
                    "lake": "The crater lake", "road": "Via Appia"},
    "brundisium": {"town": "Brundisium", "harbour": "The harbour", "road": "Via Appia",
                   "sea": "The sea"},
    "delphi": {"cliffs": "The Phaedriades", "sanctuary": "The sanctuary of Apollo",
               "slope": "The olive slope"},
    "delos": {"kynthos": "Mount Kynthos", "sanctuary": "The sanctuary of Apollo"},
    "corinth": {"acrocorinth": "Acrocorinth", "harbours": "Lechaion and Kenchreai"},
    "ephesus": {"artemision": "The Artemision"},
    "olympia": {"altis": "The Altis", "valley": "The Alpheios valley"},
    "sparta": {"valley": "The Eurotas valley", "villages": "The villages"},
    "eleusis": {"sanctuary": "The sanctuary of Demeter", "plain": "The Thriasian plain"},
    "academy": {"grove": "The grove of Akademos"},
    "sardis": {"mounds": "The royal mounds", "valley": "The Hermos valley"},
    "susa": {"citadel": "The citadel mound"},
    "gordion": {"citadel": "The citadel mound"},
    "babylon": {"east_bank": "The east bank", "west_bank": "The west bank",
                "groves": "The palm groves"},
    "pasargadae": {"garden": "The palace garden", "tomb": "The tomb of Cyrus"},
    "tibur": {"plain": "The plain below Tibur"},
    "euphrates_crossing": {"crossing": "The crossing", "river": "The Euphrates"},
    "halys": {"crossing": "The crossing"},
}
ROADS = {"latium_italy": "Via Appia", "apennines": "Via Appia", "anatolia": "The Royal Road",
         "iran_plateau": "The Royal Road", "mesopotamia": "The Royal Road",
         "susiana": "The Royal Road", "zagros": "The Royal Road", "taurus": "The Cilician road",
         "east_med": "The Levant road", "attica_north": "The Acharnai road",
         "arcadia": "The road to Sparta", "greece": "The roads of Greece"}
GENERIC = {"road": "The road", "farm": "Farms", "land": "Countryside", "sea": "The open sea",
           "pasture": "Pastures", "reserved": "The outskirts", "town": "The town",
           "harbour": "The harbour", "island": "The island", "plain": "The plain",
           "valley": "The valley", "river": "The river", "hills": "The hills",
           "fields": "The fields", "shore": "The shore", "acropolis": "The acropolis",
           "crossing": "The crossing", "slope": "The slope", "cliffs": "The cliffs",
           "groves": "The groves", "grove": "The grove", "citadel": "The citadel",
           "sanctuary": "The sanctuary", "tomb": "The tomb", "garden": "The garden",
           "lake": "The lake", "woods": "The woods", "summit": "The summit", "slopes": "The slopes"}


def side(rid: str) -> str | None:
    s = P.REGIONS[rid][1]
    return s if s in ERA else SIDE.get(rid)


def apply(doc: dict) -> dict:
    rid = doc["id"]
    if rid not in P.REGIONS:
        return doc
    kind = P.REGIONS[rid][0]
    s = side(rid)
    if kind == "seam" and rid in SEAMS:
        doc["name"], doc["caption"] = SEAMS[rid]
    elif kind == "stretch" and rid in STRETCH:
        doc["name"] = STRETCH[rid]
        doc["caption"] = f"{STRETCH[rid]} · {MOMENT[s]}" if s else STRETCH[rid]
    if s and not doc.get("era"):
        doc["era"] = ERA[s]
    names = DISTRICTS.get(rid, {})
    for d in doc.get("districts", []):
        if d.get("name"):
            continue
        if d["id"] in names:
            d["name"] = names[d["id"]]
        elif d["id"] == "road" and rid in ROADS:
            d["name"] = ROADS[rid]
        else:
            d["name"] = GENERIC.get(d["id"], d["id"].replace("_", " ").capitalize())
    return doc


def check(doc: dict) -> list[tuple[str, str, str]]:
    """Every region has a name and caption; every region of a time has its era; every district
    a name."""
    out = []
    rid = doc.get("id")
    if not doc.get("name") or not doc.get("caption"):
        out.append(("error", "region", "needs a name and a caption"))
    if rid in P.REGIONS and side(rid) and not doc.get("era"):
        out.append(("error", "region", "needs its era (the edge caption)"))
    for d in doc.get("districts", []):
        if not d.get("name"):
            out.append(("error", f"district {d['id']}", "needs a name"))
    return out
