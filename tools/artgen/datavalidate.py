"""Check the shader path's pages against their colour pages (README.md "Data pages"): the ramp
table (well formed, ids stable against the committed table), every colour page's packed twin
(same size; a coloured pixel with no data, data outside every sprite, a ramp or step outside the
table, a decoded colour that is not the pixel's, normals off the unit sphere, snow where snow
cannot lie, heights that disagree with where the pixel sits on screen for the item's footprint)
and the half-size shadow page (every shadow sprite, at half size).

    tools/artgen/.venv/bin/python tools/artgen/datavalidate.py [home | <set> ...]
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import datapages
import setbuild
import spec

SLACK = 12           # px at 64x32 a figure may reach outside its footprint
REACH = 32           # px an item may reach outside its footprint (a stone pine's crown, a quay's wall)
ITEM = re.compile(r"item/([^/]+)/[^/]+/(r\d+|m\d+)/")


def _rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def _words(img: np.ndarray) -> np.ndarray:
    v = img.astype(np.uint32)
    return v[..., 0] | v[..., 1] << 8 | v[..., 2] << 16 | v[..., 3] << 24


def check_ramps(ramp_dir: Path) -> tuple[list[str], dict]:
    errors = []
    doc = json.loads((ramp_dir / "ramps.json").read_text())
    img = _rgba(ramp_dir / doc["texture"])
    table = {}
    for e in doc["ramps"]:
        rid = e["id"]
        if not 1 <= rid <= 255 or rid in table:
            errors.append(f"ramps: id {rid} of {e['name']} out of 1..255 or repeated")
            continue
        cols = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in e["colours"]]
        if not 1 <= len(cols) <= doc["steps"] or e["steps"] != len(cols):
            errors.append(f"ramps: {e['name']} has {len(cols)} steps")
        if rid >= img.shape[0] or any(tuple(img[rid, i, :3]) != c or img[rid, i, 3] != 255
                                      for i, c in enumerate(cols)) or (img[rid, len(cols):, 3] != 0).any():
            errors.append(f"ramps: row {rid} of ramps.png differs from {e['name']}")
        if e["class"] not in doc["classes"]:
            errors.append(f"ramps: {e['name']} has an unknown class {e['class']}")
        table[rid] = (e, np.array([(a << 16) | (b << 8) | c for a, b, c in cols], np.int64))
    names = {e["name"] for e, _ in table.values()}
    for e, _ in table.values():
        for st, rid in e.get("states", {}).items():
            if rid not in table or table[rid][0].get("state_of") != e["name"]:
                errors.append(f"ramps: {e['name']}'s state {st} names ramp {rid}, not its own")
    try:
        old = subprocess.run(["git", "show", "HEAD:assets/atlas/ramps.json"], cwd=spec.ROOT,
                             capture_output=True, text=True, check=True).stdout
        for e in json.loads(old)["ramps"]:
            mine = next((x for x, _ in table.values() if x["name"] == e["name"]), None)
            if mine is not None and mine["id"] != e["id"]:
                errors.append(f"ramps: {e['name']} moved from id {e['id']} to {mine['id']}")
            elif mine is None and e["name"] not in names:
                pass                    # a retired ramp keeps its id unused (ids only append)
            used = {x["id"] for x, _ in table.values() if x["name"] != e["name"]}
            if mine is None and e["id"] in used:
                errors.append(f"ramps: retired id {e['id']} ({e['name']}) reused")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass                            # no committed table yet
    return errors, table


def footprints(cat: dict) -> dict:
    return {it["id"]: (tuple(it["footprint"]), it["layout"]) for it in cat["items"]}


def check_page(png: Path, table: dict, feet: dict, hh: int) -> list[str]:
    errors = []
    man = json.loads(png.with_suffix(".json").read_text())["sprites"]
    side = png.with_name(png.stem + ".p.json")
    ppng = png.with_name(png.stem + ".p.png")
    if not side.exists() or not ppng.exists():
        return [f"{png.name}: no packed twin"]
    pdoc = json.loads(side.read_text())
    colour = _rgba(png)
    packed = _words(_rgba(ppng))
    if packed.shape != colour.shape[:2]:
        return [f"{ppng.name}: {packed.shape[::-1]} is not the colour page's size"]
    raw = set(pdoc["colour_only"])
    if raw - set(man):
        errors.append(f"{side.name}: colour-only keys not on the page {sorted(raw - set(man))[:3]}")
    cwords = _words(colour)
    covered = np.zeros(packed.shape, bool)
    steps = np.zeros(256, np.int64)
    snow_ok = np.zeros(256, bool)
    lut = np.full((256, 8), -1, np.int64)
    for rid, (e, cols) in table.items():
        steps[rid] = len(cols)
        snow_ok[rid] = e["snow"]
        lut[rid, :len(cols)] = cols
    for key, r in man.items():
        ys, xs = slice(r["y"], r["y"] + r["h"]), slice(r["x"], r["x"] + r["w"])
        covered[ys, xs] = True
        w = packed[ys, xs]
        if key in raw:
            if not np.array_equal(w, cwords[ys, xs]):
                errors.append(f"{key}: colour-only sprite differs on the packed page")
            continue
        c = colour[ys, xs]
        opaque = c[..., 3] == 255
        if ((c[..., 3] > 0) & ~opaque).any():
            errors.append(f"{key}: translucent pixels in a sprite with data")
        ramp = (w >> 3) & 0xFF
        if (opaque & (ramp == 0)).any():
            errors.append(f"{key}: {int((opaque & (ramp == 0)).sum())} coloured pixels with no data")
        if (~opaque & (w != 0)).any():
            errors.append(f"{key}: data on {int((~opaque & (w != 0)).sum())} transparent pixels")
        if not opaque.any():
            continue
        wo, ro, so = w[opaque], ramp[opaque].astype(np.int64), (w[opaque] & 7).astype(np.int64)
        if (steps[ro] == 0).any():
            errors.append(f"{key}: ramp ids outside the table {sorted(set(ro[steps[ro] == 0].tolist()))[:4]}")
            continue
        if (so >= steps[ro]).any():
            errors.append(f"{key}: steps past their ramp's end")
            continue
        code = (c[..., 0].astype(np.int64) << 16 | c[..., 1].astype(np.int64) << 8 | c[..., 2])[opaque]
        if (lut[ro, so] != code).any():
            errors.append(f"{key}: {int((lut[ro, so] != code).sum())} pixels decode to another colour")
        nxc, nyc = (wo >> 11) & 31, (wo >> 16) & 31
        if (nxc > 30).any() or (nyc > 30).any():
            errors.append(f"{key}: normal codes past 30")
        nx, ny = (nxc.astype(np.float32) - 15) / 15, (nyc.astype(np.float32) - 15) / 15
        if (nx * nx + ny * ny > 1.1).any():      # half a code (1/30) on each axis
            errors.append(f"{key}: normals off the unit sphere")
        snow = (wo >> 31) & 1 == 1
        nz = np.sqrt(np.maximum(0, 1 - nx * nx - ny * ny))
        if (snow & ~snow_ok[ro]).any() or (snow & (nz <= 0.55)).any():
            errors.append(f"{key}: snow bit on a ramp snow does not lie on, or on a steep face")
        h = ((w >> 21) & 511).astype(np.int64)
        rows = np.broadcast_to(np.arange(r["h"])[:, None], h.shape)
        rel = r["oy"] - rows                     # px above the anchor's row
        m = ITEM.match(key)
        if m and m[1] in feet:
            (fw, fh), layout = feet[m[1]]
            if layout == "rotate" and m[2].startswith("r") and int(m[2][1:]) % 2:
                fw, fh = fh, fw
            lo, hi = rel - 1 - REACH, rel + (fw + fh) * hh + 1 + REACH
        elif key.startswith(("terrain/", "wild/")):
            lo, hi = rel - 1 - SLACK, rel + 2 * hh + 1 + SLACK
        elif key.startswith(("walker/", "figure/", "critter/", "goods/", "cart/", "ship/")):
            # Anchored at the ground contact, reaching about a tile (a cart or ship four) each way.
            reach = (4 if key.startswith(("cart/", "ship/")) else 1) * hh + 1 + SLACK
            lo, hi = rel - reach, rel + reach
        else:
            continue
        bad = opaque & ((h < lo) | (h > hi))
        if bad.any():
            errors.append(f"{key}: {int(bad.sum())} heights disagree with where the pixels sit")
    outside = (packed != 0) & ~covered
    if outside.any():
        errors.append(f"{ppng.name}: {int(outside.sum())} data pixels outside every sprite")
    return errors


def check_shadows(shadow_json: Path, pages: list[Path]) -> list[str]:
    if not shadow_json.exists():
        return [f"no shadow page {shadow_json.name}"]
    doc = json.loads(shadow_json.read_text())
    errors = [] if doc.get("scale") == 0.5 else [f"{shadow_json.name}: scale is not 0.5"]
    half = doc["sprites"]
    for p in pages:
        for key, r in json.loads(p.read_text())["sprites"].items():
            if "/shadow/" not in key:
                continue
            s = half.get(key)
            if s is None:
                errors.append(f"{key}: missing from {shadow_json.name}")
            elif s["w"] > r["w"] // 2 + 1 or s["h"] > r["h"] // 2 + 1:
                errors.append(f"{key}: not at half size on {shadow_json.name}")
    return errors


def _sprite_words(pages, key):
    """(words H x W, ox, oy) of a sprite from the packed pages {manifest sprites, packed words}."""
    for man, packed in pages:
        r = man.get(key)
        if r is not None:
            return packed[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]], r["ox"], r["oy"]
    return None


def _ground_xy(w, ox, oy):
    """Per pixel of a sprite: its height, its grid position (voxels from the anchor) and whether
    it faces up; the screen position and height give the point (sy = (x + y) / 2 - h)."""
    rows, cols = np.mgrid[:w.shape[0], :w.shape[1]]
    h = ((w >> 21) & 511).astype(np.float32)
    sx, sy = cols - ox + 0.5, rows - oy + 0.5
    nx = (((w >> 11) & 31).astype(np.float32) - 15) / 15
    ny = (((w >> 16) & 31).astype(np.float32) - 15) / 15
    up = (((w >> 3) & 255) > 0) & (1 - nx * nx - ny * ny > 0.81)
    return h, sy + h + sx / 2, sy + h - sx / 2, up


def check_depth(name: str, atlas_dir: Path, pages) -> list[str]:
    """What the global depth test will stand on: heights continuous across a landmark's piece
    seams, walk tiles' floors at the geometry's `walk_z`, stair treads rising toward `climb`."""
    errors = []
    geom_file = atlas_dir / f"{name}.geom.json"
    if not geom_file.exists():
        return errors
    geom = json.loads(geom_file.read_text())
    hw = geom["tile"][0] // 2
    for iid, entry in geom["items"].items():
        for v, g in entry.items():
            if "pieces" in g:
                parts = [_sprite_words(pages, f"item/{iid}/base/{v}/p{i}/f0") for i in range(len(g["pieces"]))]
                if any(p_ is None for p_ in parts):
                    errors.append(f"{iid} {v}: a piece is missing from the packed pages")
                    continue
                ox = max(p_[1] for p_ in parts)
                oy = max(p_[2] for p_ in parts)
                W = max(ox - p_[1] + p_[0].shape[1] for p_ in parts)
                H = max(oy - p_[2] + p_[0].shape[0] for p_ in parts)
                whole = np.zeros((H, W), np.uint32)
                owner = np.full((H, W), -1, np.int64)
                for i, (w, pox, poy) in enumerate(parts):
                    y0, x0 = oy - poy, ox - pox
                    has = ((w >> 3) & 255) > 0
                    if (owner[y0:y0 + w.shape[0], x0:x0 + w.shape[1]][has] >= 0).any():
                        errors.append(f"{iid} {v}: pieces overlap")
                    whole[y0:y0 + w.shape[0], x0:x0 + w.shape[1]][has] = w[has]
                    owner[y0:y0 + w.shape[0], x0:x0 + w.shape[1]][has] = i
                # Each pixel's height and screen place put it on a footprint tile: it must be one
                # of its own piece's (pieces are cut by the tile of the front-most surface), so a
                # height wrong at a seam shows as a pixel standing in the neighbouring piece.
                fw = max(x + w_ for x, _y, w_, _h in g["pieces"])
                fh = max(y + h_ for _x, y, _w, h_ in g["pieces"])
                _hh, gx, gy, _up = _ground_xy(whole, ox, oy)
                tx, ty = np.clip(gx / hw, 0, fw - 1e-3), np.clip(gy / hw, 0, fh - 1e-3)
                # Below the anchor's ground (piers in a river, a basin's floor) heights are 0:
                # such pixels cannot be placed, so only those above it are held to their tiles.
                placed = _hh > 0
                slack = 1.5 / hw
                bad = total = 0
                for i, (px, py, pw, ph) in enumerate(g["pieces"]):
                    m = (owner == i) & placed
                    total += int(m.sum())
                    bad += int((m & ((tx < px - slack) | (tx > px + pw + slack) |
                                     (ty < py - slack) | (ty > py + ph + slack))).sum())
                if bad > 0.005 * max(total, 1):
                    errors.append(f"{iid} {v}: {bad} of {total} pixels stand outside their piece's tiles "
                                  "(heights wrong at the seams)")
                if "walk_z" in g:
                    hh_, gx, gy, up = _ground_xy(whole, ox, oy)
                    wz = {tuple(map(int, t.split(","))): z for t, z in g["walk_z"].items()}
                    for (tx_, ty_), z in wz.items():
                        # Only what a walker could stand on or hit: a roof over a stoa's floor
                        # stands above the headroom and hides the floor itself.
                        sel = up & (np.floor(gx / hw) == tx_) & (np.floor(gy / hw) == ty_) & \
                            (hh_ < z + setbuild.WALK_HEADROOM * hw // 32)
                        # A stair tile holds several treads: allow half its rise to the next tile.
                        rise = max((abs(z - wz[n]) for n in ((tx_ + 1, ty_), (tx_ - 1, ty_), (tx_, ty_ + 1),
                                                              (tx_, ty_ - 1)) if n in wz), default=0)
                        if sel.sum() >= 8 and abs(float(np.median(hh_[sel])) - z) > 6 + rise / 2:
                            errors.append(f"{iid} {v}: the floor of walk tile {tx_},{ty_} stands at "
                                          f"{np.median(hh_[sel]):.0f} px, walk_z says {z}")
            if "climb" in g and "pieces" not in g:
                found = _sprite_words(pages, f"item/{iid}/base/{v}/f0")
                if found is None:
                    continue
                hh_, gx, gy, up = _ground_xy(*found)
                if up.sum() < 8:
                    continue
                # The treads' middle band: cheek walls stand at both sides of a stair.
                across = (gy if g["climb"][1] == "x" else gx)
                lo, hi = np.percentile(across[up], (25, 75))
                sel = up & (across >= lo) & (across <= hi)
                along = {"+x": gx, "-x": -gx, "+y": gy, "-y": -gy}[g["climb"]][sel]
                if sel.sum() < 8 or np.std(along) == 0 or np.std(hh_[sel]) == 0 or \
                        np.corrcoef(along, hh_[sel])[0, 1] < 0.5:
                    errors.append(f"{iid} {v}: the treads do not rise toward {g['climb']}")
    return errors


def order_rules(iid: str, item: dict, entry: dict, keys, level: int) -> list[str]:
    """The art-side rules of draw-order.md §5.1 for one item: `item` its catalog entry, `entry`
    its geometry ({variant: ...}), `keys` the sprite keys on the set's pages, `level` tile.level
    px. P1 pieces where there are walk tiles or a footprint over 8 x 8, walk tiles in runs of
    their own; P2 art for every piece; P3 `tops` for every look and `roof` only over walk tiles;
    W2 every walk tile reached from the footprint's edge by steps of at most half a level; W3 neighbouring walk floors within half a level unless one floor piece holds both; W4 a walk
    floor not above the item and more than three levels up only on a stair or a terrace; S1 a
    stair's `climb` along its catalog `axis`; O1 a clearance (`under`) for every piece."""
    errors = []
    fw0, fh0 = item["footprint"]
    for v, g in entry.items():
        turned = item.get("layout") == "rotate" and v.startswith("r") and int(v[1:]) % 2
        fw, fh = (fh0, fw0) if turned else (fw0, fh0)
        walk = {tuple(t) for t in g.get("walk", [])}
        pieces = g.get("pieces", [])
        if (walk or fw > 8 or fh > 8) and not pieces:
            errors.append(f"{iid} {v}: P1 walk tiles or a footprint over 8 x 8 but no pieces")
        for i, (x, y, w, h) in enumerate(pieces):
            tiles_ = {(x + a, y + b) for a in range(w) for b in range(h)}
            if tiles_ & walk and (tiles_ - walk or (w > 1 and h > 1)):
                errors.append(f"{iid} {v}: P1 piece {i} mixes walk tiles with others or is not a run")
            if f"item/{iid}/base/{v}/p{i}/f0" not in keys:
                errors.append(f"{iid} {v}: P2 piece {i} has no art")
        tops = g.get("tops")
        if tops is None or len(tops) != fh or any(len(r) != fw for r in tops):
            errors.append(f"{iid} {v}: P3 no tops for its {fw} x {fh} footprint")
        bad_roof = [t for t in g.get("roof", {}) if tuple(map(int, t.split(","))) not in walk]
        if bad_roof:
            errors.append(f"{iid} {v}: P3 roof over tiles that are not walk tiles {bad_roof[:3]}")
        wz = {tuple(map(int, t.split(","))): z for t, z in g.get("walk_z", {}).items()}
        floors = [{(x + a, y + b) for a in range(w) for b in range(h)}
                  for i, (x, y, w, h) in enumerate(pieces) if i in set(g.get("floor_pieces", []))]
        for (x, y), z in wz.items():
            for nb in ((x + 1, y), (x, y + 1)):    # a stair's floors rise by design ("climb")
                if nb in wz and abs(wz[nb] - z) > level // 2 and "climb" not in g and \
                        not any((x, y) in f and nb in f for f in floors):
                    errors.append(f"{iid} {v}: W3 walk floors ({x},{y}) {z} px and {nb} {wz[nb]} px "
                                  "more than half a level apart outside one floor piece")
            if z > g.get("h", 0):
                errors.append(f"{iid} {v}: W4 walk floor ({x},{y}) at {z} px above the item's top")
        if walk:                # W2: reachable from the footprint's edge by steps a walker takes
            def ok(a_, b_):
                return abs(wz.get(a_, 0) - wz.get(b_, 0)) <= level // 2 or "climb" in g or \
                    any(a_ in f and b_ in f for f in floors)
            todo = [t for t in walk if t[0] in (0, fw - 1) or t[1] in (0, fh - 1)]
            seen = set(todo)
            while todo:
                x, y = todo.pop()
                for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nb in walk and nb not in seen and ok((x, y), nb):
                        seen.add(nb)
                        todo.append(nb)
            if walk - seen:
                errors.append(f"{iid} {v}: W2 walk tiles no step reaches from the edge {sorted(walk - seen)[:4]}")
        if wz and max(wz.values()) > 3 * level and "climb" not in g and not g.get("terrace"):
            errors.append(f"{iid} {v}: W4 a walk floor {max(wz.values())} px up on an item that is not a "
                          "stair and not marked a terrace")
        if item.get("rise") and v == "r0" and "axis" in item and g.get("climb", "  ")[1] != item["axis"]:
            errors.append(f"{iid} r0: S1 climbs {g.get('climb')} across its catalog axis {item['axis']}")
        if pieces and len(g.get("under", [])) != len(pieces):
            errors.append(f"{iid} {v}: O1 no clearance (under) for each piece")
    return errors


def check_water(water_json: Path, pages: list[Path]) -> list[str]:
    """The water page: its rectangles are the colour rectangles' size and anchor, and every item
    sprite with a body of water on a water ramp has one (datapages.water_sprite)."""
    if not water_json.exists():
        return [f"{water_json.name}: missing"]
    doc = json.loads(water_json.read_text())
    errors = []
    wclass = datapages.water_classes()
    for p in pages:
        man = json.loads(p.with_suffix(".json").read_text())["sprites"]
        raw = set(json.loads(p.with_name(p.stem + ".p.json").read_text())["colour_only"])
        words = _words(_rgba(p.with_name(p.stem + ".p.png")))
        for key, r in man.items():
            if not key.startswith("item/") or key in raw or "/shadow/" in key or "/glow/" in key:
                continue
            w = words[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]]
            n = int(wclass[(w >> 3) & 0xFF][w != 0].sum())
            e = doc["sprites"].get(key)
            if n >= datapages.WATER_MIN and e is None:
                errors.append(f"{key}: {n} water pixels and no water-page entry")
            elif e is not None and (e["w"], e["h"], e["ox"], e["oy"]) != (r["w"], r["h"], r["ox"], r["oy"]):
                errors.append(f"{key}: its water-page rectangle is not its colour rectangle")
    return errors


def check(name: str, atlas_dir: Path | None = None) -> list[str]:
    """`name`: 'home' or a set id."""
    root = spec.ASSETS
    atlas_dir = atlas_dir or (root / "atlas")
    if name == "home":
        home_dir = atlas_dir.parent
        pages = [home_dir / "atlas.png"]
        cat = json.loads(spec.CATALOG.read_text())
        ramp_dir, shadow = atlas_dir, home_dir / "atlas.s.json"
    else:
        pages = sorted((p for p in atlas_dir.glob(f"{name}.*.png") if re.fullmatch(rf"{name}\.\d+\.png", p.name)),
                       key=lambda p: int(p.name.split(".")[1]))
        cat = json.loads((root / "sets" / name / "catalog.json").read_text())
        ramp_dir, shadow = atlas_dir, atlas_dir / f"{name}.s.json"
    errors, table = check_ramps(ramp_dir)
    hh = json.loads(spec.CATALOG.read_text())["tile"]["h"] // 2
    feet = footprints(cat)
    for p in pages:
        errors += check_page(p, table, feet, hh)
    errors += check_shadows(shadow, [p.with_suffix(".json") for p in pages])
    errors += check_water(shadow.with_name(shadow.name.replace(".s.json", ".w.json")), pages)
    if name != "home":
        packed = [(json.loads(p.with_suffix(".json").read_text())["sprites"],
                   _words(_rgba(p.with_name(p.stem + ".p.png")))) for p in pages]
        errors += check_depth(name, atlas_dir, packed)
        geom_file = atlas_dir / f"{name}.geom.json"
        if geom_file.exists():
            keys = {k for man, _w in packed for k in man}
            level = json.loads(spec.CATALOG.read_text())["tile"]["level"]
            items = {it["id"]: it for it in cat["items"]}
            for iid, entry in json.loads(geom_file.read_text())["items"].items():
                if iid in items:
                    errors += order_rules(iid, items[iid], entry, keys, level)
    return errors


def main(names) -> int:
    status = 0
    for n in names:
        errs = check(n)
        for e in errs:
            print(f"{n}: {e}", file=sys.stderr)
        print(f"datavalidate {n}: {len(errs)} problems")
        status |= bool(errs)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["home", "world", "parsa", "athens", "rome"]))
