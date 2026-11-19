"""Re-render some items or actors of a set and splice them into its existing pages, for a fix
that must land without a full set rebuild (a big set takes an hour or more).

    tools/artgen/.venv/bin/python tools/artgen/setpatch.py rome rome.r_lamp rome.r_insula --dir DIR

Every key of the named ids (`item/<id>/…`, `<kind>/<id>/…` for actors) is rendered as a full
build renders it (setbuild.build_set with `only`); a sprite that fits its old rectangle (and
shares it with no key left as it was) is written there, the rest go in a band added at the foot
of the last page with room (pages grow in 256-row steps up to 4096). Then the touched rectangles
of the packed twins are rewritten, the shadow, occlusion and water pages are rebuilt from what
was there plus the new sprites, and the geometry entries of the named ids are replaced. `DIR`
holds the set's files (a scratch copy of assets/atlas: validate it with setvalidate before
installing). The packing is not what a full build would make; the next full build replaces it."""

from __future__ import annotations

import argparse
import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

import datapages
import pack
import setbuild
import spec
from pack import Sprite


def _pages(d: Path, set_id: str):
    files = sorted((p for p in d.glob(f"{set_id}.*.json") if re.fullmatch(rf"{set_id}\.\d+\.json", p.name)),
                   key=lambda p: int(p.name.split(".")[1]))
    out = []
    for f in files:
        doc = json.loads(f.read_text())
        png = f.with_name(doc["image"])
        colour = np.array(Image.open(png).convert("RGBA"))
        packed = np.array(Image.open(datapages.packed_path(png)).convert("RGBA"))
        side = json.loads(datapages.packed_side(png).read_text())
        out.append({"png": png, "man": doc["sprites"], "colour": colour, "packed": packed,
                    "raw": set(side["colour_only"]), "side": side})
    return out


def _grow(page, rows):
    h = page["colour"].shape[0]
    new_h = min(4096, -(-(h + rows) // 256) * 256)
    if new_h <= h:
        return False
    for key in ("colour", "packed"):
        a = page[key]
        page[key] = np.concatenate([a, np.zeros((new_h - h,) + a.shape[1:], a.dtype)], 0)
    return True


def splice(pages, sprites: dict) -> dict:
    """Write `sprites` (key -> Sprite, already trimmed) into `pages`. Returns key -> page index."""
    where = {}
    users = {}
    for n, pg in enumerate(pages):
        for key, r in pg["man"].items():
            where[key] = n
            users.setdefault((n, r["x"], r["y"]), set()).add(key)
    homeless = []
    for key, t in sorted(sprites.items()):
        h, w = t.rgba.shape[:2]
        n = where.get(key)
        if n is not None:
            r = pages[n]["man"][key]
            alone = users[(n, r["x"], r["y"])] <= set(sprites)
            if alone:   # clear the old rectangle (every key on it is being replaced)
                pages[n]["colour"][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = 0
                pages[n]["packed"][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = 0
            if alone and w <= r["w"] and h <= r["h"]:
                pages[n]["man"][key] = {"x": r["x"], "y": r["y"], "w": w, "h": h, "ox": t.ox, "oy": t.oy}
                continue
            del pages[n]["man"][key]
        homeless.append(key)
    if homeless:
        # A band at the foot of the last page: shelves of the homeless sprites, tallest first.
        pg_i = len(pages) - 1
        pg = pages[pg_i]
        W = pg["colour"].shape[1]
        pad = pack.PAD
        order = sorted(homeless, key=lambda k_: (-sprites[k_].rgba.shape[0], k_))
        x, y0 = pad, pg["colour"].shape[0]
        y, shelf = y0 + pad, 0
        spots = {}
        for key in order:
            h, w = sprites[key].rgba.shape[:2]
            if x + w + pad > W:
                x, y, shelf = pad, y + shelf + pad, 0
            spots[key] = (x, y)
            x += w + pad
            shelf = max(shelf, h)
        need = y + shelf + pad - y0
        if not _grow(pg, need) or pg["colour"].shape[0] < y0 + need:
            raise SystemExit(f"setpatch: {len(homeless)} sprites do not fit on {pg['png'].name}")
        for key, (x, y) in spots.items():
            t = sprites[key]
            pg["man"][key] = {"x": x, "y": y, "w": t.rgba.shape[1], "h": t.rgba.shape[0], "ox": t.ox, "oy": t.oy}
        for key in homeless:
            where[key] = pg_i
    for key, t in sprites.items():
        n = where[key]
        r = pages[n]["man"][key]
        pages[n]["colour"][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = t.rgba
        w = datapages.words(key, t)
        if w is None:
            pages[n]["raw"].add(key)
            w = datapages.rgba_word(t.rgba)
        else:
            pages[n]["raw"].discard(key)
        pages[n]["packed"][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = datapages.word_rgba(w)
    return where


def _old_sprites(png: Path, man: dict, drop: set) -> dict:
    img = np.array(Image.open(png).convert("RGBA"))
    return {k: Sprite(img[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]].copy(), r["ox"], r["oy"])
            for k, r in man.items() if k not in drop}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("set")
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args(argv)
    set_id, d = a.set, a.dir
    cat = json.loads((setbuild.SETS / set_id / "catalog.json").read_text())
    mod = setbuild.load_set(set_id)
    k = json.loads(spec.CATALOG.read_text())["tile"]["w"] // 32
    only = [f"/{i}/" for i in a.ids]
    with Pool(spec.WORKERS) as pool:
        sprites, pieces, meta, lm_info = setbuild.build_set(set_id, cat, k, pool, only)
    sprites = {key: s for key, s in sprites.items() if any(o in key or key.startswith(f"{setbuild.OCC_PREFIX}item/{o[1:-1]}/")
                                                          for o in only)}
    occ = {key[len(setbuild.OCC_PREFIX):]: sprites.pop(key) for key in [x for x in sprites if x.startswith(setbuild.OCC_PREFIX)]}
    shadows = {key: sprites.pop(key) for key in [x for x in sprites if "/shadow/" in x]}
    trimmed = {key: pack.trim(s) for key, s in sprites.items()}
    import ramps
    ramps.write(d)          # the shared table the new sprites' words index
    pages = _pages(d, set_id)
    # Pages from before shadows left the colour pages: their shadows are on the shadow page
    # already (which the engine draws), so they leave the colour pages here.
    on_s = set(json.loads((d / f"{set_id}.s.json").read_text())["sprites"])
    for pg in pages:
        for key in [x for x in pg["man"] if "/shadow/" in x]:
            if key not in on_s and key not in shadows:
                raise SystemExit(f"setpatch: {key} is on no shadow page")
            r = pg["man"].pop(key)
            if not any(o["x"] == r["x"] and o["y"] == r["y"] for o in pg["man"].values()):
                pg["colour"][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = 0
                pg["packed"][r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = 0
            pg["raw"].discard(key)
    splice(pages, trimmed)
    written = []
    for pg in pages:
        Image.fromarray(pg["colour"], "RGBA").save(pg["png"], optimize=True)
        pg["png"].with_suffix(".json").write_text(
            json.dumps({"version": 1, "image": pg["png"].name, "sprites": dict(sorted(pg["man"].items()))}, indent=1) + "\n")
        Image.fromarray(pg["packed"], "RGBA").save(datapages.packed_path(pg["png"]), optimize=True)
        side = dict(pg["side"], colour_only=sorted(pg["raw"] & set(pg["man"])))
        datapages.packed_side(pg["png"]).write_text(json.dumps(side, indent=1) + "\n")
        written.append((pg["png"], pg["man"]))
        print(f"page {pg['png'].name}: {pg['colour'].shape[1]}x{pg['colour'].shape[0]}, {len(pg['man'])} sprites")
    # Shadow page: what was there, the patched ids' shadows replaced.
    sp = d / f"{set_id}.s.json"
    sdoc = json.loads(sp.read_text())
    keep = _old_sprites(sp.with_name(sdoc["image"]), sdoc["sprites"], set(shadows) | {
        x for x in sdoc["sprites"] if any(o in x for o in only)})
    halves = keep | {key: datapages.half(pack.trim(s)) for key, s in shadows.items()}
    atlas, man = pack.pack(halves)
    Image.fromarray(atlas, "RGBA").save(sp.with_name(sdoc["image"]), optimize=True)
    sp.write_text(json.dumps({"version": 1, "image": sdoc["image"], "scale": 0.5, "sprites": man}, indent=1) + "\n")
    # Occlusion page.
    op = d / f"{set_id}.o.json"
    if op.exists():
        odoc = json.loads(op.read_text())
        keep = _old_sprites(op.with_name(odoc["image"]), odoc["sprites"], set(occ) | {
            x for x in odoc["sprites"] if any(x.startswith(f"item/{i}/") for i in a.ids)})
        datapages.write_occlusion_page(op.with_name(odoc["image"]), keep | occ)
    # Water page, from the pages as written.
    datapages.write_water_page(d / f"{set_id}.w.png", written)
    # Geometry: the named ids' entries replaced.
    gp = d / f"{set_id}.geom.json"
    geom = json.loads(gp.read_text())
    new = setbuild.geometry(set_id, cat, mod, pieces, meta, lm_info, k)
    for i in a.ids:
        for part in ("items", "actors"):
            if i in new[part]:
                geom[part][i] = new[part][i]
    gp.write_text(setbuild.compact_json(geom))
    print(f"setpatch {set_id}: {len(trimmed)} sprites, {len(shadows)} shadows, {len(occ)} occlusion tops")
    return 0


if __name__ == "__main__":
    sys.exit(main())
