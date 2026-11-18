"""All Rome landmarks (rome.md §2.3, §3.2, §3.7), gathered from the district modules, with
their catalog facts (name, scale, the bible's height, layers, card)."""

from sets.rome import campus, fora, forum, martius, oppian, ostia, outer, palatine, river, velia

DISTRICTS = (campus, fora, forum, martius, oppian, ostia, outer, palatine, river, velia)
LANDMARKS = {k: v for d in DISTRICTS for k, v in d.LANDMARKS.items()}
INFO = {k: v for d in DISTRICTS for k, v in d.INFO.items()}
# Landmarks drawn standing in water (the island, the bridges); every other one stands on land.
ON = {k: v for d in DISTRICTS for k, v in getattr(d, "ON", {}).items()}


def emitter_fx(name):
    """The effect an emitter plays: named by its prefix (`steam_w` -> rome.steam)."""
    return "rome." + name.split("_")[0]
