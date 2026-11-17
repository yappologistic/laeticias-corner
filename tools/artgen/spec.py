"""What the atlas must contain (every sprite key the catalog implies, with its frame count) and
where and at which resolution it is built."""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets" / "catalog.json"
ASSETS = ROOT / "assets"
PREVIEWS = ROOT / "out" / "artgen"
# Models are authored in design units: 16 per tile edge, whatever the output resolution.
DESIGN_TILE = 16

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
class Build:
    """One build: the tile size, where the atlas goes and where previews go.

    A tile is `tile_w` x `tile_w / 2` pixels; `k` voxels (and pixels of height) per design
    unit, so `16 k` voxels per tile edge. Everything resolution dependent derives from `k`.
    """
    tile_w: int
    out: Path
    previews: Path

    @property
    def k(self) -> int:
        return self.tile_w // (2 * DESIGN_TILE)

    @property
    def tile_h(self) -> int:
        return self.tile_w // 2

    @property
    def atlas_png(self) -> Path:
        return self.out / "atlas.png"

    @property
    def atlas_json(self) -> Path:
        return self.out / "atlas.json"


def parse_build(argv) -> tuple[Build, argparse.Namespace]:
    ap = argparse.ArgumentParser(description="Build the sprite atlas from the catalog.")
    ap.add_argument("--tile", type=int, help="tile width in px (default: catalog tile.w)")
    ap.add_argument("--out", type=Path, help="directory for atlas.png/atlas.json and previews "
                    "(default: assets/, previews in out/artgen/)")
    ap.add_argument("--preview", action="store_true", help="also write preview scenes")
    args = ap.parse_args(argv)
    tile = load_catalog()["tile"]
    if args.tile is None and tile["h"] * 2 != tile["w"]:
        ap.error(f"catalog tile {tile['w']}x{tile['h']} is not 2:1")
    w = args.tile or tile["w"]
    if w <= 0 or w % (2 * DESIGN_TILE):
        ap.error(f"tile width {w} must be a positive multiple of {2 * DESIGN_TILE}")
    out = (args.out or ASSETS).resolve()
    return Build(w, out, out if args.out else PREVIEWS), args


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
