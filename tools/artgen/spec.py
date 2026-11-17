"""What the atlas must contain: every sprite key the catalog implies, with its frame count."""

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets" / "catalog.json"
ATLAS_PNG = ROOT / "assets" / "atlas.png"
ATLAS_JSON = ROOT / "assets" / "atlas.json"
OUT = ROOT / "out" / "artgen"

# Frame counts are ours to choose (the manifest is authoritative); fps comes from the catalog.
WATER_FRAMES = 4
ITEM_FRAMES = {"campfire": 6, "windmill": 6}
DEFAULT_ANIMATED_FRAMES = 4
CRITTER_ANIMS = {"move_front": 4, "move_back": 4, "idle_front": 2, "idle_back": 2}
FX_FRAMES = {"smoke": 6, "ripple": 4, "sparkle": 4, "raindrop": 4, "leaf": 4}
# Flat things lying on the ground or water cast no shadow.
NO_SHADOW = {"lily_pads"}


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text())


@dataclass(frozen=True)
class ItemSpec:
    id: str
    footprint: tuple[int, int]
    layout: str
    variants: tuple[str, ...]
    frames: int
    layers: tuple[str, ...]
    on: str


def item_specs(cat: dict) -> list[ItemSpec]:
    specs = []
    for it in cat["items"]:
        if it["layout"] == "connect":
            variants = tuple(f"m{m}" for m in range(16))
        else:
            variants = tuple(f"r{k}" for k in range(it["count"]))
        frames = ITEM_FRAMES.get(it["id"], DEFAULT_ANIMATED_FRAMES) if "fps" in it else 1
        layers = ["base"]
        if it["id"] not in NO_SHADOW:
            layers.append("shadow")
        if it.get("glow"):
            layers.append("glow")
        specs.append(ItemSpec(it["id"], tuple(it["footprint"]), it["layout"], variants, frames,
                              tuple(layers), it["on"]))
    return specs


def terrain_keys(cat: dict) -> list[str]:
    keys = []
    for t in cat["terrain"]:
        if t.get("base"):
            keys += [f"terrain/{t['id']}/v{n}" for n in range(t["variants"])]
        else:
            frames = WATER_FRAMES if "fps" in t else 1
            keys += [f"terrain/{t['id']}/m{m}/f{f}" for m in range(t["edges"]) for f in range(frames)]
    return keys


def required_keys(cat: dict) -> list[str]:
    keys = terrain_keys(cat)
    for s in item_specs(cat):
        keys += [f"item/{s.id}/{layer}/{v}/f{f}"
                 for layer in s.layers for v in s.variants for f in range(s.frames)]
    for v in cat["visitors"]:
        keys += [f"critter/{v['id']}/{a}/f{f}" for a, n in CRITTER_ANIMS.items() for f in range(n)]
    keys += [f"fx/{name}/f{f}" for name, n in FX_FRAMES.items() for f in range(n)]
    keys += ["edge/cliff_se", "edge/cliff_sw", "ui/tile_ok", "ui/tile_bad"]
    return keys
