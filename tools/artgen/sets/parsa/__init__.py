"""The Pārsa set: Achaemenid Pārsa (Persepolis) in spring c. 470 BC and the Persian-time places
of its set (docs/design/cities/persepolis.md). Models are in grid axes (+x south, +y west) at
landmark scale s = 0.85 for the terrace (arch.Scale)."""

from sets.parsa import animals, babylon, ground, kit, landmarks, people, plants, waypoints

LANDMARKS = {**landmarks.LANDMARKS, **babylon.LANDMARKS, **waypoints.LANDMARKS}
ITEMS = {**kit.ITEMS, **plants.ITEMS, **babylon.ITEMS}
STATES = kit.STATES
# With the Royal Road's waypoints the set fills its two pages to 88 %: one packing group with
# the longest sides first keeps it on two.
ONE_GROUP = True
PACK_ORDER = "maxside"
# Frame counts of animated items, terrain and effects (the manifest is authoritative).
FRAMES = {**kit.FRAMES, **ground.FRAMES}


def actor_sprite(kind, variant, anim, facing, frame, k):
    if kind in animals.CRITTERS or kind in animals.CARTS:
        return animals.sprite(kind, variant, anim, facing, frame, k)
    return people.sprite(kind, variant, anim, facing, frame, k)


def carry_at(kind, k):
    return people.carry_at(kind, k)


def flat(keys, cat, k):
    return ground.build(keys, cat, k)
