"""What the atlas must contain (every sprite key the catalog implies plus the art-list keys in
`art_list.json`, with their frame counts) and where and at which resolution it is built."""

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "assets" / "catalog.json"
ART_LIST = Path(__file__).with_name("art_list.json")
ASSETS = ROOT / "assets"
PREVIEWS = ROOT / "out" / "artgen"
# Render workers: at most three beside the other agents' work (ARTGEN_JOBS overrides); the
# output never depends on it.
WORKERS = max(1, int(os.environ.get("ARTGEN_JOBS", min(3, max(1, (os.cpu_count() or 2) // 2)))))
# Models are authored in design units: 16 per tile edge, whatever the output resolution.
DESIGN_TILE = 16

# Frame counts are ours to choose (the manifest is authoritative); fps comes from the catalog.
WATER_FRAMES = 4
ITEM_FRAMES = {"campfire": 6, "windmill": 6}
DEFAULT_ANIMATED_FRAMES = 4
# Every visitor has these four; anything more comes from the art list. Walks, swims and wingbeats
# are eight frames with planted feet; the tiny flyers are hand-drawn stencils of four poses.
CRITTER_ANIMS = {"move_front": 8, "move_back": 8, "idle_front": 2, "idle_back": 2}
STENCIL_FLYERS = {"butterfly", "bee", "firefly"}


def critter_anims(cid: str) -> dict[str, int]:
    if cid in STENCIL_FLYERS:
        return {**CRITTER_ANIMS, "move_front": 4, "move_back": 4}
    return CRITTER_ANIMS
# Flat things lying on the ground or water cast no shadow.
NO_SHADOW = {"lily_pads", "stepping_stones"}
SEASONS = ("spring", "summer", "autumn", "winter")
# Animation names the catalog uses that are not sprites of their own.
ENGINE_ANIMS = {"idle", "move", "enter"}


def load_catalog(path: Path = CATALOG) -> dict:
    return json.loads(Path(path).read_text())


@dataclass(frozen=True)
class Build:
    """One build: the catalog, the tile size, where the atlas goes and where previews go.

    A tile is `tile_w` x `tile_w / 2` pixels; `k` voxels (and pixels of height) per design
    unit, so `16 k` voxels per tile edge. Everything resolution dependent derives from `k`.
    """
    tile_w: int
    out: Path
    previews: Path
    catalog: Path = CATALOG

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

    def load_catalog(self) -> dict:
        return load_catalog(self.catalog)


def parse_build(argv, validate_only=False) -> tuple[Build, argparse.Namespace]:
    ap = argparse.ArgumentParser(description="Build the sprite atlas from the catalog.")
    ap.add_argument("--catalog", type=Path, default=CATALOG,
                    help="catalog to derive the required sprites from (default: assets/catalog.json)")
    ap.add_argument("--tile", type=int, help="tile width in px (default: catalog tile.w)")
    ap.add_argument("--out", type=Path, help="directory for atlas.png/atlas.json and previews "
                    "(default: assets/, previews in out/artgen/)")
    if validate_only:
        ap.add_argument("--allow-extra", action="store_true",
                        help="only check that the atlas covers the catalog (extra keys allowed)")
    else:
        ap.add_argument("--preview", action="store_true", help="also write preview scenes")
        ap.add_argument("--set", help="build one art set's pages (assets/sets/<set>/catalog.json) "
                        "instead of the home atlas")
        ap.add_argument("--only", nargs="+", help="with --set: render only keys containing one of "
                        "these strings (a quick look; no geometry, no validation)")
    args = ap.parse_args(argv)
    catalog = args.catalog.resolve()
    tile = load_catalog(catalog)["tile"]
    if args.tile is None and tile["h"] * 2 != tile["w"]:
        ap.error(f"catalog tile {tile['w']}x{tile['h']} is not 2:1")
    w = args.tile or tile["w"]
    if w <= 0 or w % (2 * DESIGN_TILE):
        ap.error(f"tile width {w} must be a positive multiple of {2 * DESIGN_TILE}")
    if getattr(args, "set", None):
        out = (args.out or ASSETS / "atlas").resolve()
        return Build(w, out, out if args.out else PREVIEWS / args.set, catalog), args
    out = (args.out or ASSETS).resolve()
    return Build(w, out, out if args.out else PREVIEWS, catalog), args


@dataclass(frozen=True)
class ItemSpec:
    id: str
    footprint: tuple[int, int]
    layout: str
    variants: tuple[str, ...]
    frames: int
    layers: tuple[str, ...]
    on: str


def item_frames(it: dict) -> int:
    return ITEM_FRAMES.get(it["id"], DEFAULT_ANIMATED_FRAMES) if "fps" in it else 1


def item_specs(cat: dict) -> list[ItemSpec]:
    specs = []
    for it in cat["items"]:
        if it["layout"] == "connect":
            variants = tuple(f"m{m}" for m in range(16))
        else:
            variants = tuple(f"r{k}" for k in range(it["count"]))
        layers = ["base"]
        if it["id"] not in NO_SHADOW:
            layers.append("shadow")
        if it.get("glow"):
            layers.append("glow")
        specs.append(ItemSpec(it["id"], tuple(it["footprint"]), it["layout"], variants,
                              item_frames(it), tuple(layers), it["on"]))
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


# ---- the art list: keys the catalog cannot imply ----

def expand(pattern: str) -> list[str]:
    """Brace expansion: `{0-3}` is a numeric range, `{a,b}` alternatives; left to right."""
    m = re.search(r"\{([^{}]*)\}", pattern)
    if not m:
        return [pattern]
    body = m[1]
    r = re.fullmatch(r"(\d+)-(\d+)", body)
    opts = [str(n) for n in range(int(r[1]), int(r[2]) + 1)] if r else body.split(",")
    return [k for o in opts for k in expand(pattern[:m.start()] + o + pattern[m.end():])]


def _holds(req: str, cat: dict) -> bool:
    """One requirement of an art-list group, e.g. `visitor:owl`, `item:apple_tree`, `seasons`."""
    if req == "seasons":
        return bool(cat.get("seasons"))
    kind, _, ident = req.partition(":")
    if kind == "version":
        return cat.get("version", 1) >= int(ident)
    if kind == "visitor":
        return any(v["id"] == ident for v in cat["visitors"])
    if kind == "resident":
        return cat.get("resident", {}).get("id") == ident
    if kind == "item":
        return any(it["id"] == ident for it in cat["items"])
    if kind == "terrain":
        return any(t["id"] == ident for t in cat["terrain"])
    raise ValueError(f"art_list.json: unknown requirement {req!r}")


def load_art_list() -> dict:
    return json.loads(ART_LIST.read_text())


def art_list_keys(cat: dict, art: dict | None = None) -> list[str]:
    """Art-list keys whose group requirements the catalog meets."""
    art = art or load_art_list()
    keys = []
    for group in art["groups"]:
        if all(_holds(r, cat) for r in group.get("requires", ())):
            for p in group["keys"]:
                keys += expand(p)
    if cat.get("frames"):
        pieces = art["frame_pieces"]
        keys += [f"frame/{f['id']}/{p}" for f in cat["frames"]
                 if f["id"] not in art["engine_drawn_frames"] for p in pieces]
    return keys


def required_keys(cat: dict) -> list[str]:
    keys = terrain_keys(cat)
    for it, s in zip(cat["items"], item_specs(cat)):
        keys += [f"item/{s.id}/{layer}/{v}/f{f}"
                 for layer in s.layers for v in s.variants for f in range(s.frames)]
        # Season looks override the base layer; shadows and glows fall back to the plain key.
        if cat.get("seasons"):
            keys += [f"item/{s.id}/base/{v}/f{f}@{season}" for season in it.get("season_looks", ())
                     for v in s.variants for f in range(s.frames)]
        # Growth stages override the base layer only (the shadow stays the plain key).
        stages = it.get("growth", {}).get("stages", 0)
        keys += [f"item/{s.id}/base/{v}/g{g}/f{f}" for v in s.variants for g in range(stages)
                 for f in range(s.frames)]
    for v in cat["visitors"]:
        keys += [f"critter/{v['id']}/{a}/f{f}" for a, n in critter_anims(v["id"]).items() for f in range(n)]
    keys += art_list_keys(cat)
    seen = set()
    return [k for k in keys if not (k in seen or seen.add(k))]


def referenced_anims(cat: dict) -> dict[str, set[str]]:
    """Animation names the catalog asks each visitor (and the resident) to play."""
    out = {}

    def walk(node, names):
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ("anim", "call_anim") and isinstance(val, str):
                    names.add(val)
                else:
                    walk(val, names)
        elif isinstance(node, list):
            for val in node:
                walk(val, names)

    for v in cat["visitors"]:
        names = set()
        walk([v.get("activities", []), v.get("startle", {}), v.get("pet", {})], names)
        out[v["id"]] = names - ENGINE_ANIMS
    if "resident" in cat:
        names = set()
        walk(cat["resident"].get("routines", {}), names)
        out[cat["resident"]["id"]] = names - ENGINE_ANIMS
    return out
