"""The Rome set: Rome on the Parilia, 21 April AD 126, under Hadrian, with the Tiber, Ostia and
Portus, the Campagna, the aqueducts and the Via Appia (docs/design/cities/rome.md). Landmarks
are modelled in grid axes (+x south, +y west) at the bible's scales with the shared Roman
toolkit (`roman`, `relief_roman`) over the Greek one; people wear Roman dress on the shared rig."""

from sets.rome import animals, ground, kit, landmarks, people, plants

# Looks per face material (setbuild: 4 unless named): the natural faces have eight, since every
# level of a cliff draws one at random and they must not repeat.
EDGE_VARIANTS = {f"rome.{e}": 8 for e in ground.NATURAL}

LANDMARKS = landmarks.LANDMARKS
ITEMS = {**kit.ITEMS, **plants.ITEMS}
STATES = {}
# The Forum is the busiest view: its district packs first, beside the people when it fits.
DISTRICT_ORDER = (2,)
# Frame counts of animated items, terrain and effects (the manifest is authoritative).
FRAMES = {**kit.FRAMES, **plants.FRAMES, **ground.FRAMES}

# What the set catalog lists beyond the landmarks (sets/rome/catalog.py writes it).
CATALOG = {
    "terrain": ground.TERRAIN_CATALOG,
    "items": kit.catalog_items() + plants.catalog_items(),
    "actors": people.actors_catalog() + animals.actors_catalog(),
    "goods": ground.GOODS_CATALOG,
    "art": {"edges": ground.EDGES, "slopes": ground.SLOPES, "fx": sorted(ground.FRAMES.keys() - {"rome.river_tiber"})},
}


def actor_sprite(kind, variant, anim, facing, frame, k):
    if kind in animals.CRITTERS or kind in animals.CARTS or kind in animals.SHIPS:
        return animals.sprite(kind, variant, anim, facing, frame, k)
    return people.sprite(kind, variant, anim, facing, frame, k)


def carry_at(kind, k):
    return people.carry_at(kind, k)


def flat(keys, cat, k):
    return ground.build(keys, cat, k)


def extra_keys(cat):
    """Keys beyond the shared scheme: the interior looks of the natural overlays
    (`ground.INTERIOR`, terrain.SHIFTS), which the engine picks per tile."""
    ids = {t["id"] for t in cat.get("terrain", [])}
    return [f"terrain/{tid}/m15/v{v}/f0" for tid, n in ground.INTERIOR.items() if tid in ids for v in range(1, n)]
