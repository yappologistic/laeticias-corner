"""The Rome set: Rome on the Parilia, 21 April AD 126, under Hadrian, with the Tiber, Ostia and
Portus, the Campagna, the aqueducts and the Via Appia (docs/design/cities/rome.md). Landmarks
are modelled in grid axes (+x south, +y west) at the bible's scales with the shared Roman
toolkit (`roman`, `relief_roman`) over the Greek one; people wear Roman dress on the shared rig."""

from sets.rome import ground, landmarks

LANDMARKS = landmarks.LANDMARKS
ITEMS = {}
STATES = {}
# Frame counts of animated items, terrain and effects (the manifest is authoritative).
FRAMES = {**ground.FRAMES}

# What the set catalog lists beyond the landmarks (sets/rome/catalog.py writes it).
CATALOG = {
    "terrain": ground.TERRAIN_CATALOG,
    "goods": ground.GOODS_CATALOG,
    "art": {"edges": ground.EDGES, "fx": sorted(ground.FRAMES.keys() - {"rome.river_tiber"})},
}


def actor_sprite(kind, variant, anim, facing, frame, k):
    raise KeyError(kind)


def carry_at(kind, k):
    return {}


def flat(keys, cat, k):
    return ground.build(keys, cat, k)
