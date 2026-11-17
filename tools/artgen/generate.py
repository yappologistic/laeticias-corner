"""Build the sprite atlas (atlas.png + atlas.json) from the catalog. Deterministic.

Usage: tools/artgen/build.sh [--tile W] [--out DIR] [--preview]

The tile width comes from the catalog (`tile.w`) unless --tile overrides it; the atlas goes to
assets/ unless --out names another directory (previews then go there too).
"""

import sys
import time
from multiprocessing import Pool

import fx
import pack
import spec
import terrain
import validate
from models import critters, registry
from render import render


def _item_job(job):
    item_id, layout, variant, frame, frames, footprint, layers, k = job
    fw, fh = footprint
    build = registry.ITEMS[item_id]
    n = int(variant[1:])  # r<n> or m<mask>
    if layout == "rotate":
        model = build(0, frame, frames, k).rotated(n, fw, fh)
    else:
        model = build(n, frame, frames, k)
    out = render(model, "glow" in layers)
    result = {f"item/{item_id}/base/{variant}/f{frame}": out.base}
    if "shadow" in layers:
        result[f"item/{item_id}/shadow/{variant}/f{frame}"] = out.shadow
    if "glow" in layers:
        result[f"item/{item_id}/glow/{variant}/f{frame}"] = out.glow
    return result


def _critter_job(job):
    cid, anim, frame, frames, k = job
    return {f"critter/{cid}/{anim}/f{frame}": critters.sprite(cid, anim, frame, frames, k)}


def build_sprites(k: int) -> dict[str, pack.Sprite]:
    cat = spec.load_catalog()
    jobs = []
    for s in spec.item_specs(cat):
        for v in s.variants:
            for f in range(s.frames):
                jobs.append((s.id, s.layout, v, f, s.frames, s.footprint, s.layers, k))
    critter_jobs = [(v["id"], a, f, n, k) for v in cat["visitors"]
                    for a, n in spec.CRITTER_ANIMS.items() for f in range(n)]
    sprites = terrain.build(cat, spec.WATER_FRAMES, k)
    sprites.update(fx.build(spec.FX_FRAMES, k))
    # Big jobs first so the pool stays busy; results are merged by key, so order is irrelevant.
    with Pool() as pool:
        for part in pool.imap_unordered(_item_job, jobs, chunksize=1):
            sprites.update(part)
        for part in pool.imap_unordered(_critter_job, critter_jobs, chunksize=4):
            sprites.update(part)
    return sprites


def main(argv) -> int:
    build, args = spec.parse_build(argv)
    t0 = time.time()
    sprites = build_sprites(build.k)
    build.out.mkdir(parents=True, exist_ok=True)
    w, h = pack.write_atlas(sprites, build.atlas_png, build.atlas_json)
    print(f"atlas {w}x{h} for {build.tile_w}x{build.tile_h} tiles, {len(sprites)} sprites "
          f"in {time.time() - t0:.1f}s")
    status = validate.main(build)
    if args.preview:
        import preview
        preview.main(build)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
