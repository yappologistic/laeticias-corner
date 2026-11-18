"""Stride lengths of every locomotion animation, written into the set catalogs and the home
manifest so the engine can play walks by distance walked (graphics-rnd.md §2.9):

    frame = int(distance_in_tiles / stride * frames) % frames

A set catalog's actor gets `"stride"` (tiles one cycle covers) on each locomotion animation
beside its `fps`, and that `fps` is the rate that keeps the feet planted at the actor's usual
speed, so time-based playback is right too until the engine plays by distance. Fliers have no
stride; their wingbeat keeps a fixed rate. `python strides.py <set>` rewrites one catalog
(Rome's is written by `sets/rome/catalog.py`, which calls `annotate`)."""

import importlib
import json
import sys

import rig
import setbuild
import spec

LOCOMOTION = ("move", "carry", "march", "run", "ride")
# Tiles per second (src/core/tuning.hpp kWalkSpeed, kCartSpeed): the speeds the fps assume
# for actors whose catalog entry states none.
SPEED = {"walk": 0.9, "cart": 0.6}
FLIGHT_FPS = 16.0          # twelve-frame wingbeats, one every 0.75 s
TILE_UNITS = spec.DESIGN_TILE


def _people(set_id):
    return importlib.import_module(f"sets.{set_id}.people")


def _animals(set_id):
    return importlib.import_module(f"sets.{set_id}.animals")


def stride_tiles(set_id: str, actor: dict, anim: str) -> float | None:
    """Tiles one cycle of `anim` covers for this actor (the mean of its variants), or None
    for an animation that is not a walk (flight, swimming, a seated ride)."""
    kind, prefix = actor["id"], actor["sprite"].split("/")[0]
    if prefix in ("walker", "figure"):
        people = _people(set_id)
        dresses = [people._posed(kind, v, anim) for v in range(actor.get("variants", 1))]
        if anim == "ride" and not all(d.mount for d in dresses):
            return None
        return sum(rig.stride_tiles(d, anim) for d in dresses) / len(dresses)
    animals = _animals(set_id)
    if prefix == "cart":
        return animals.cart_stride(kind) / TILE_UNITS
    if prefix != "critter":
        return None
    beasts = getattr(animals, "BEASTS", {})
    if kind in beasts:
        from sets.parsa.animals import stride
        return stride(beasts[kind], anim) / TILE_UNITS
    walking = getattr(animals, "WALKING_BIRDS", {})
    if kind in walking:
        from sets.parsa.animals import BIRD_REACH
        return 4 * BIRD_REACH * walking[kind] / TILE_UNITS
    return None


def annotate(set_id: str, cat: dict) -> dict:
    """The catalog with `stride` and a matching `fps` on every locomotion animation."""
    mod = importlib.import_module(f"sets.{set_id}")
    for actor in cat.get("actors", []):
        if actor["sprite"].startswith("ship/"):
            continue
        speed = actor.get("locomotion", {}).get("speed")
        if speed is None:
            speed = SPEED["cart" if actor["sprite"].startswith("cart/") else "walk"]
        for anim, entry in actor["anims"].items():
            if anim not in LOCOMOTION:
                continue
            s = stride_tiles(set_id, actor, anim)
            n = setbuild.anim_frames(mod, actor, anim)
            if s is None:
                entry.pop("stride", None)
                if anim == "move" and actor["sprite"].startswith("critter/"):
                    entry["fps"] = round(FLIGHT_FPS * n / rig.WALK_FRAMES, 1)
                continue
            entry["stride"] = round(s, 3)
            entry["fps"] = round(n * speed / s, 1)
    return cat


def main(set_id: str) -> int:
    path = spec.ROOT / "assets" / "sets" / set_id / "catalog.json"
    cat = annotate(set_id, json.loads(path.read_text()))
    path.write_text(json.dumps(cat, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
