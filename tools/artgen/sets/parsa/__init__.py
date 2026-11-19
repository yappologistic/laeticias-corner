"""The Pārsa set: Achaemenid Pārsa (Persepolis) in spring c. 470 BC and the Persian-time places
of its set (docs/design/cities/persepolis.md). Models are in grid axes (+x south, +y west) at
landmark scale s = 0.85 for the terrace (arch.Scale)."""

from sets.parsa import animals, babylon, ground, kit, landmarks, people, plants, waypoints

# Looks per face material (setbuild: 4 unless named): the natural faces have eight, since every
# level of a cliff draws one at random and they must not repeat.
EDGE_VARIANTS = {f"parsa.{e}": 8 for e in ground.NATURAL}

LANDMARKS = {**landmarks.LANDMARKS, **babylon.LANDMARKS, **waypoints.LANDMARKS}
ITEMS = {**kit.ITEMS, **plants.ITEMS, **babylon.ITEMS}
STATES = kit.STATES
# Frame counts of animated items, terrain and effects (the manifest is authoritative).
FRAMES = {**kit.FRAMES, **ground.FRAMES}


# Two pages hold the set with its twelve-frame walks only if the least-seen walk on fewer
# frames (out/reports/art-motion.md): the most-seen people keep twelve; the delegations, the
# other walkers, the guards' parade march and the animals walk on eight, carts move on six.
MOST_SEEN = frozenset({"parsa.noble", "parsa.guard_spear", "parsa.guard_mede", "parsa.usher", "parsa.labourer",
                       "parsa.woman_worker", "parsa.farmer", "parsa.scribe"})


def anim_frames(kind, anim):
    """Frames of a locomotion cycle where the page budget sets them (None: the scheme's)."""
    if kind in animals.CARTS:
        return 6 if anim == "move" else None
    if kind in animals.CRITTERS:
        return 8 if anim in ("move", "run") else None
    if kind.split(".", 1)[1] in people.FIGURES:
        return None
    if anim == "march" or (anim in ("move", "run") and kind not in MOST_SEEN):
        return 8
    return None


def actor_sprite(kind, variant, anim, facing, frame, k):
    n = anim_frames(kind, anim)
    if kind in animals.CRITTERS or kind in animals.CARTS:
        return animals.sprite(kind, variant, anim, facing, frame, k, n)
    return people.sprite(kind, variant, anim, facing, frame, k, n)


def carry_at(kind, k):
    return people.carry_at(kind, k)


def flat(keys, cat, k):
    return ground.build(keys, cat, k)


def extra_keys(cat):
    """Keys beyond the shared scheme: the interior looks of the natural overlays
    (`ground.INTERIOR`, terrain.SHIFTS), which the engine picks per tile."""
    ids = {t["id"] for t in cat.get("terrain", [])}
    return [f"terrain/{tid}/m15/v{v}/f0" for tid, n in ground.INTERIOR.items() if tid in ids for v in range(1, n)]
