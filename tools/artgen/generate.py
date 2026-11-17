"""Build assets/atlas.png + assets/atlas.json from the catalog. Deterministic.

Usage: tools/artgen/build.sh [--preview]
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
    item_id, layout, variant, frame, frames, footprint, layers = job
    fw, fh = footprint
    build = registry.ITEMS[item_id]
    k = int(variant[1:])  # r<k> or m<mask>
    if layout == "rotate":
        model = build(0, frame, frames).rotated(k, fw, fh)
    else:
        model = build(k, frame, frames)
    out = render(model, "glow" in layers)
    result = {f"item/{item_id}/base/{variant}/f{frame}": out.base}
    if "shadow" in layers:
        result[f"item/{item_id}/shadow/{variant}/f{frame}"] = out.shadow
    if "glow" in layers:
        result[f"item/{item_id}/glow/{variant}/f{frame}"] = out.glow
    return result


def _critter_job(job):
    cid, anim, frame, frames = job
    return {f"critter/{cid}/{anim}/f{frame}": critters.sprite(cid, anim, frame, frames)}


def build_sprites() -> dict[str, pack.Sprite]:
    cat = spec.load_catalog()
    jobs = []
    for s in spec.item_specs(cat):
        for v in s.variants:
            for f in range(s.frames):
                jobs.append((s.id, s.layout, v, f, s.frames, s.footprint, s.layers))
    critter_jobs = [(v["id"], a, f, n) for v in cat["visitors"]
                    for a, n in spec.CRITTER_ANIMS.items() for f in range(n)]
    sprites = terrain.build(cat, spec.WATER_FRAMES)
    sprites.update(fx.build(spec.FX_FRAMES))
    # Big jobs first so the pool stays busy; results are merged by key, so order is irrelevant.
    with Pool() as pool:
        for part in pool.imap_unordered(_item_job, jobs, chunksize=1):
            sprites.update(part)
        for part in pool.imap_unordered(_critter_job, critter_jobs, chunksize=4):
            sprites.update(part)
    return sprites


def main() -> int:
    t0 = time.time()
    sprites = build_sprites()
    w, h = pack.write_atlas(sprites, spec.ATLAS_PNG, spec.ATLAS_JSON)
    print(f"atlas {w}x{h}, {len(sprites)} sprites in {time.time() - t0:.1f}s")
    status = validate.main()
    if "--preview" in sys.argv[1:]:
        import preview
        preview.main()
    return status


if __name__ == "__main__":
    sys.exit(main())
