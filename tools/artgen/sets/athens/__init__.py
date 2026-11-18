"""The Athens set: Athens at the Panathenaia of summer 432 BC, with Attica, Piraeus and the
Greek-time places of its set (docs/design/cities/athens.md). Landmarks are modelled in grid
axes (+x south, +y west) at the bible's scales (monuments s = 1, the Odeion 0.8, Piraeus's
sheds and the waypoints 0.5) with the shared Greek toolkit (`greek`, `relief_greek`)."""

from sets.athens import animals, ground, kit, landmarks, people, plants

LANDMARKS = landmarks.LANDMARKS
ITEMS = {**kit.ITEMS, **plants.ITEMS}
STATES = kit.STATES
# Frame counts of animated items, terrain and effects (the manifest is authoritative).
FRAMES = {**kit.FRAMES, **plants.FRAMES, **ground.FRAMES}


def actor_sprite(kind, variant, anim, facing, frame, k):
    if kind in animals.CRITTERS or kind in animals.CARTS or kind in animals.SHIPS:
        return animals.sprite(kind, variant, anim, facing, frame, k)
    return people.sprite(kind, variant, anim, facing, frame, k)


def carry_at(kind, k):
    return people.carry_at(kind, k)


def flat(keys, cat, k):
    return ground.build(keys, cat, k)
