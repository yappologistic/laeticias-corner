"""Check a set's pages and geometry against its catalog (world-tech.md §1): keys, page limits,
rects, anchors, ground diamonds, palette, frame counts, pieces, walk tiles (headroom and
reachability), slot coverage and measured heights.

Usage: tools/artgen/.venv/bin/python tools/artgen/setvalidate.py parsa [--dir assets/atlas]
"""

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from PIL import Image

import setbuild
import spec
from palette import palette_for
from validate import diamond

MAX_PAGES = {"parsa": 2, "athens": 2, "rome": 3, "world": 1}


def validate(set_id: str, out_dir: Path, k: int, lm_info=None) -> tuple[list[str], list[str]]:
    cat = json.loads((setbuild.SETS / set_id / "catalog.json").read_text())
    mod = setbuild.load_set(set_id)
    errors, warnings = [], []
    pages = sorted(out_dir.glob(f"{set_id}.[0-9]*.json"), key=lambda p: int(p.name.split(".")[1]))
    if len(pages) > MAX_PAGES.get(set_id, 2):
        warnings.append(f"{len(pages)} pages exceed the set budget of {MAX_PAGES.get(set_id, 2)}")
    sprites, owner, images = {}, {}, {}
    for p in pages:
        doc = json.loads(p.read_text())
        if set(doc) != {"version", "image", "sprites"} or doc["version"] != 1:
            errors.append(f"{p.name}: manifest must be exactly {{version: 1, image, sprites}}")
        img = Image.open(out_dir / doc["image"])
        if img.mode != "RGBA" or max(img.size) > setbuild.PAGE:
            errors.append(f"{doc['image']}: {img.mode} {img.size}, expected RGBA within {setbuild.PAGE}")
        images[p.name] = np.asarray(img)
        for key, r in doc["sprites"].items():
            if key in sprites:
                errors.append(f"{key}: on two pages")
            sprites[key] = r
            owner[key] = p.name
    geom = json.loads((out_dir / f"{set_id}.geom.json").read_text())
    pieces = {iid: e["r0"]["pieces"] for iid, e in geom["items"].items() if "pieces" in e.get("r0", {})}
    required = setbuild.required_keys(cat, mod, pieces)
    errors += [f"missing sprite {k_}" for k_ in required if k_ not in sprites]
    errors += [f"unexpected sprite {k_}" for k_ in sorted(set(sprites) - set(required))]

    allowed = {int(c[1:], 16) for c in palette_for(set_id)}
    want = diamond(32 * k)
    frames = defaultdict(set)
    for key, r in sprites.items():
        rgba = images[owner[key]]
        H, W = rgba.shape[:2]
        x, y, w, h, ox, oy = (r[f] for f in ("x", "y", "w", "h", "ox", "oy"))
        if w < 1 or h < 1 or x < 0 or y < 0 or x + w > W or y + h > H:
            errors.append(f"{key}: rect {x},{y} {w}x{h} outside {W}x{H}")
            continue
        # Landmark shadows and glows are whole-building sprites whose pixels may lie far from the anchor.
        reach = setbuild.PAGE if "/p" in key or key.startswith("item/") and ("/shadow/" in key or "/glow/" in key) \
            else 160 * k
        if not (-reach <= ox <= w + reach and -reach <= oy <= h + reach):
            errors.append(f"{key}: anchor ({ox},{oy}) far outside {w}x{h}")
        px = rgba[y:y + h, x:x + w].reshape(-1, 4)
        px = px[px[:, 3] > 0].astype(np.int64)
        if len(px) == 0 and w * h > 1 and not re.search(r"/p\d+/", key):
            errors.append(f"{key}: sprite is fully transparent")
        codes = set(np.unique((px[:, 0] << 16) | (px[:, 1] << 8) | px[:, 2]).tolist())
        bad = codes - ({0} if "/shadow/" in key else allowed)
        if bad:
            errors.append(f"{key}: {len(bad)} colours outside the {set_id} palette")
        if re.fullmatch(r"terrain/[^/]+/(v\d+|m15/f\d+)", key):
            if (w, h, ox, oy) != (want.shape[1], want.shape[0], 16 * k - 1, 0):
                errors.append(f"{key}: {w}x{h} anchored ({ox},{oy}) is not the tile diamond")
            elif not np.array_equal(rgba[y:y + h, x:x + w, 3] > 0, want):
                errors.append(f"{key}: coverage differs from the tile diamond")
        m = re.fullmatch(r"item/([^/]+)/([^/]+/[^/]+/(?:p\d+/)?)f(\d+)", key)
        if m:
            frames[m[1]].add((m[2], int(m[3])))
    for iid, fs in frames.items():
        counts = defaultdict(set)
        for look, f in fs:
            counts[look].add(f)
        ns = {len(v) for v in counts.values()}
        if len(ns) > 1 or any(v != set(range(len(v))) for v in counts.values()):
            errors.append(f"{iid}: frames not contiguous or layers disagree")

    items = {it["id"]: it for it in cat["items"]}
    for iid, entry in geom["items"].items():
        it = items.get(iid)
        if it is None:
            errors.append(f"geom: {iid} is not in the catalog")
            continue
        want_slots = {s["id"] for s in it.get("slots", [])}
        for v, g in entry.items():
            have = set(g.get("slots", {}))
            if want_slots - have:
                errors.append(f"{iid} {v}: catalog slots without geometry {sorted(want_slots - have)}")
            if have - want_slots:
                errors.append(f"{iid} {v}: geometry slots not in the catalog {sorted(have - want_slots)}")
            want_em = set(it.get("emitters", {}))
            if want_em != set(g.get("emitters", {})):
                errors.append(f"{iid} {v}: emitters {sorted(g.get('emitters', {}))} != catalog {sorted(want_em)}")
        g = entry.get("r0", {})
        fw, fh = it["footprint"]
        if "pieces" in g:
            cover = np.zeros((fw, fh), np.int64)
            for x, y, w, h in g["pieces"]:
                cover[x:x + w, y:y + h] += 1
            if not (cover == 1).all():
                errors.append(f"{iid}: pieces do not partition the footprint")
        walk = {tuple(t) for t in g.get("walk", [])}
        water = {tuple(t) for t in g.get("water", [])}
        floor = {tuple(map(int, kk.split(","))): v for kk, v in g.get("walk_z", {}).items()}
        kinds = {s["id"]: s.get("kind") for s in it.get("slots", [])}
        if it.get("landmark"):       # a spot inside a landmark: walkers on walk tiles, boats on its water
            for sid, spots in g.get("slots", {}).items():
                for sp in spots:
                    t = tuple(sp["t"])
                    ok = water if kinds.get(sid) == "mooring" else walk
                    if 0 <= t[0] < fw and 0 <= t[1] < fh and t not in ok:
                        errors.append(f"{iid}: slot {sid} spot {list(t)} is inside the footprint on a "
                                      f"{'non-water' if ok is water else 'non-walk'} tile")
        if walk & water:
            errors.append(f"{iid}: tiles both walk and water {sorted(walk & water)[:4]}")
        if it.get("rise"):           # every stair says which way it climbs, in each rendered rotation
            for v, gv in entry.items():
                if gv.get("climb") not in ("+x", "-x", "+y", "-y"):
                    errors.append(f"{iid} {v}: stair without a climb direction")
        info = (lm_info or {}).get(iid)
        if walk and info is not None:
            col = info["column"]
            for (x, y) in sorted(walk):
                z0 = floor.get((x, y), 0) + 2 * k // 2
                z1 = floor.get((x, y), 0) + setbuild.WALK_HEADROOM * k // 2
                if col[x, y, z0:z1].any():
                    zs = np.nonzero(col[x, y, z0:z1])[0] + z0
                    errors.append(f"{iid}: walk tile ({x},{y}) has geometry {zs.min()}..{zs.max()} px above "
                                  f"its floor")
            seen = deque(t for t in walk if t[0] in (0, fw - 1) or t[1] in (0, fh - 1))
            reach = set(seen)
            while seen:
                x, y = seen.popleft()
                for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nb in walk and nb not in reach:
                        reach.add(nb)
                        seen.append(nb)
            if walk - reach:
                errors.append(f"{iid}: walk tiles not reachable from the edge {sorted(walk - reach)[:6]}")
        if info is not None and "height" in it:
            top = info["top"]
            if abs(top - it["height"] * k / 2) > 0.15 * it["height"] * k / 2:
                warnings.append(f"{iid}: measured height {top * 2 // k} px, catalog {it['height']} px")
    for a in cat.get("actors", []):
        if ("carry" in a["anims"]) != (a["id"] in geom["actors"]):
            errors.append(f"{a['id']}: carry animation and carry_at disagree")
    return errors, warnings


def main(set_id, out_dir, k, lm_info=None) -> int:
    errors, warnings = validate(set_id, Path(out_dir), k, lm_info)
    for w in warnings:
        print(f"{set_id}: warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"{set_id}: {e}", file=sys.stderr)
    print(f"setvalidate {set_id}: {len(errors)} problems, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--dir", type=Path, default=spec.ASSETS / "atlas")
    a = ap.parse_args()
    tile = spec.load_catalog()["tile"]["w"]
    sys.exit(main(a.set, a.dir, tile // (2 * spec.DESIGN_TILE)))
