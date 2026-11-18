"""Build the sprite atlas (atlas.png + atlas.json) from the catalog. Deterministic.

Usage: tools/artgen/build.sh [--catalog PATH] [--tile W] [--out DIR] [--preview]
       tools/artgen/build.sh --set parsa [--tile W] [--out DIR] [--preview] [--only KEY...]

The required keys (spec.required_keys: what the catalog implies plus art_list.json) drive the
whole build: every key is produced by exactly one job, and a key nobody can make is an error.
The tile width comes from the catalog (`tile.w`) unless --tile overrides it; the atlas goes to
assets/ unless --out names another directory (previews then go there too).
"""

import json
import re
import sys
import time
from collections import defaultdict
from multiprocessing import Pool

import decor
import fx
import pack
import spec
import terrain
import validate
from models import registry
from render import render

ITEM_KEY = re.compile(r"item/([^/]+)/([^/]+)/([^/]+)/(?:g(\d+)/)?f(\d+)(?:@(\w+))?")
CRITTER_KEY = re.compile(r"critter/([^/]+)/([^/]+)/f(\d+)")
# Flat sprites (drawn per pixel, not modelled) by key prefix.
MODULES = {"terrain": terrain, "fx": fx, "decor": decor}
FLAT = (("terrain/", "terrain"), ("edge/", "terrain"), ("wild/", "terrain"), ("ui/tile", "terrain"),
        ("fx/", "fx"), ("ui/portrait/", "decor"), ("sky/", "decor"), ("title/", "decor"),
        ("frame/", "decor"))
WORKERS = spec.WORKERS


def _item_job(job):
    item_id, layout, variant, frame, frames, footprint, stage, season, layers, k = job
    fw, fh = footprint
    build = registry.ITEMS[item_id]
    n = int(variant[1:])  # r<n> or m<mask>
    kw = {}
    if stage is not None:
        kw["stage"] = stage
    if season is not None:
        kw["season"] = season
    if layout == "rotate":
        model = build(0, frame, frames, k, **kw).rotated(n, fw, fh)
    else:
        model = build(n, frame, frames, k, **kw)
    out = render(model, "glow" in layers)
    g = "" if stage is None else f"g{stage}/"
    s = "" if season is None else f"@{season}"
    sprites = {"base": out.base, "shadow": out.shadow, "glow": out.glow}
    return {f"item/{item_id}/{layer}/{variant}/{g}f{frame}{s}": sprites[layer] for layer in layers}


def _critter_job(job):
    cid, anim, frame, frames, k = job
    return {f"critter/{cid}/{anim}/f{frame}": registry.critter_sprite(cid, anim, frame, frames, k)}


def _flat_job(job):
    module, keys, cat, k = job
    return MODULES[module].build(keys, cat, k)


def _jobs(cat: dict, keys: list[str], k: int):
    items = {it["id"]: it for it in cat["items"]}
    item_groups = defaultdict(list)
    critter_frames = defaultdict(int)
    flat = defaultdict(list)
    for key in keys:
        if m := ITEM_KEY.fullmatch(key):
            item_id, layer, variant, stage, frame, season = m.groups()
            stage = None if stage is None else int(stage)
            item_groups[(item_id, variant, int(frame), stage, season)].append(layer)
        elif m := CRITTER_KEY.fullmatch(key):
            critter_frames[(m[1], m[2])] = max(critter_frames[(m[1], m[2])], int(m[3]) + 1)
        else:
            module = next((mod for prefix, mod in FLAT if key.startswith(prefix)), None)
            if module is None:
                raise SystemExit(f"artgen: no builder for {key}")
            flat[module].append(key)
    jobs = []
    for (item_id, variant, frame, stage, season), layers in item_groups.items():
        it = items[item_id]
        jobs.append((_item_job, (item_id, it["layout"], variant, frame, spec.item_frames(it),
                                 tuple(it["footprint"]), stage, season, tuple(sorted(layers)), k)))
    # Big footprints first so the pool stays busy; results are merged by key, so the order
    # never shows in the output.
    jobs.sort(key=lambda j: -j[1][5][0] * j[1][5][1])
    jobs += [(_critter_job, (cid, anim, f, n, k)) for (cid, anim), n in critter_frames.items()
             for f in range(n)]
    jobs += [(_flat_job, (mod, ks, cat, k)) for mod, ks in flat.items()]
    return jobs


def _run(job):
    fn, args = job
    return fn(args)


def build_sprites(cat: dict, k: int) -> dict[str, pack.Sprite]:
    keys = spec.required_keys(cat)
    sprites = {}
    with Pool(WORKERS) as pool:
        for part in pool.imap_unordered(_run, _jobs(cat, keys, k), chunksize=1):
            sprites.update(part)
    missing = sorted(set(keys) - set(sprites))
    if missing:
        raise SystemExit(f"artgen: builders did not make {len(missing)} keys, e.g. {missing[:5]}")
    return {key: sprites[key] for key in keys}


def main(argv) -> int:
    build, args = spec.parse_build(argv)
    if args.set:
        import setbuild
        return setbuild.main(build, args)
    t0 = time.time()
    sprites = build_sprites(build.load_catalog(), build.k)
    build.out.mkdir(parents=True, exist_ok=True)
    w, h = pack.write_atlas(sprites, build.atlas_png, build.atlas_json)
    # The home walks' strides (tiles per cycle), beside the manifest (whose fields are fixed).
    (build.out / "atlas").mkdir(exist_ok=True)
    (build.out / "atlas" / "home.strides.json").write_text(
        json.dumps({"version": 1, "strides": registry.strides(sprites)}, indent=1) + "\n")
    print(f"atlas {w}x{h} for {build.tile_w}x{build.tile_h} tiles, {len(sprites)} sprites "
          f"in {time.time() - t0:.1f}s")
    status = validate.main(build)
    if args.preview:
        import preview
        preview.main(build)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
