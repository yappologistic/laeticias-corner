"""The Rome set: Rome on the Parilia, 21 April AD 126, under Hadrian, with the Tiber, Ostia and
Portus, the Campagna, the aqueducts and the Via Appia (docs/design/cities/rome.md). Landmarks
are modelled in grid axes (+x south, +y west) at the bible's scales with the shared Roman
toolkit (`roman`, `relief_roman`) over the Greek one; people wear Roman dress on the shared rig."""

from sets.rome import animals, ground, kit, landmarks, people, plants

LANDMARKS = landmarks.LANDMARKS
ITEMS = {**kit.ITEMS, **plants.ITEMS}
STATES = {}
# Frame counts of animated items, terrain and effects (the manifest is authoritative).
FRAMES = {**kit.FRAMES, **plants.FRAMES, **ground.FRAMES}

# What the set catalog lists beyond the landmarks (sets/rome/catalog.py writes it).
CATALOG = {
    "terrain": ground.TERRAIN_CATALOG,
    "items": kit.catalog_items() + plants.catalog_items(),
    "actors": people.actors_catalog() + animals.actors_catalog(),
    "goods": ground.GOODS_CATALOG,
    "art": {"edges": ground.EDGES, "fx": sorted(ground.FRAMES.keys() - {"rome.river_tiber"})},
}


def actor_sprite(kind, variant, anim, facing, frame, k):
    if kind in animals.CRITTERS or kind in animals.CARTS or kind in animals.SHIPS:
        return animals.sprite(kind, variant, anim, facing, frame, k)
    return people.sprite(kind, variant, anim, facing, frame, k)


def carry_at(kind, k):
    return people.carry_at(kind, k)


def flat(keys, cat, k):
    return ground.build(keys, cat, k)
