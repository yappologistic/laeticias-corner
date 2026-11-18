"""Build one art set's atlas pages and geometry (world-tech.md §1): `build.sh --set parsa`.

Reads `assets/sets/<set>/catalog.json` (the set catalog: same schema as the home catalog for
terrain and items, plus `actors` and an `art` block), derives every key it implies, renders
them with the set's models (`sets/<set>/`), cuts large landmarks into pieces, packs the pages
`assets/atlas/<set>.<n>.png/json` and writes `assets/atlas/<set>.geom.json` (heights, pieces,
walk tiles, slots, emitters, carry points). Other sets and the home atlas are never touched.
"""

import importlib
import json
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool

import numpy as np

import pack
import rig
import spec
from bigrender import BigModel, render_big
from pack import Sprite
from render import render

SETS = spec.ROOT / "assets" / "sets"
PAGE = 4096
WALK_HEADROOM = 48          # px at 64x32: 1.5 tile.h above a walk tile's floor
MAX_PIECE = 8
FACINGS = ("front", "back")


# ---------- what the set modules provide ----------

@dataclass
class Landmark:
    """A big item: its builder, footprint (tiles along x, y), height range in design units and
    the geometry it declares. Walk tiles must stay clear below the headroom except, on stairs,
    for the floor itself (`floor`: walk tile -> floor height in design units). `water`: open
    water inside the footprint (a harbour basin), cut into pieces of its own and drawn before
    the boats on it. `climb`: for a stair, the direction one walks to go up ('+x', '-x',
    '+y', '-y')."""
    footprint: tuple
    z: tuple
    build: tuple                        # (module, function, kwargs as a sorted tuple)
    walk: list = field(default_factory=list)
    floor: dict = field(default_factory=dict)
    slots: dict = field(default_factory=dict)     # slot id -> [spot dicts, 't' in tiles]
    emitters: dict = field(default_factory=dict)  # name -> (x, y, z) design units
    district: int = 0                   # packing group: neighbours share a page
    water: list = field(default_factory=list)
    climb: str = ""


@dataclass
class Item:
    """A kit item: `build(variant, frame, frames, k) -> Model` in canonical orientation.
    `walk`: footprint tiles at r0 that walkers may enter (a fold's pen, a gate's passage).
    `slots` and `walk` may be functions of the look (`m<mask>` of a connect piece)."""
    build: object
    slots: dict = field(default_factory=dict)
    emitters: dict = field(default_factory=dict)  # name -> (x, y, z) design units at r0
    walk: list = field(default_factory=list)


# ---------- catalog -> keys ----------

def load_set(set_id: str):
    return importlib.import_module(f"sets.{set_id}")


def item_layers(it: dict) -> list[str]:
    if "layers" in it:
        return list(it["layers"])
    return ["base", "shadow"] + (["glow"] if it.get("glow") else [])


def item_rotations(it: dict) -> list[int]:
    if "rotations" in it:
        return list(it["rotations"])
    if it.get("landmark"):
        return [0]
    return list(range(it.get("count", 1))) if it["layout"] in ("rotate", "variant") else [0]


def item_variants(it: dict) -> list[str]:
    if it["layout"] == "connect":
        return [f"m{m}" for m in range(16)]
    return [f"r{k}" for k in item_rotations(it)]


def item_frames(it: dict, mod) -> int:
    return mod.FRAMES.get(it["id"], 4) if "fps" in it else 1


def actor_keys(a: dict) -> list[str]:
    prefix = a["sprite"]
    variants = a.get("variants", 0)
    vs = [f"/v{v}" for v in range(variants)] if variants else [""]
    keys = []
    for v in vs:
        for anim in a["anims"]:
            if prefix.startswith("critter/"):
                n = CRITTER_FRAMES.get(anim, 4)
            elif prefix.startswith(("cart/", "ship/")):
                n = 4                                   # world-tech.md §1.9: carts and ships
            else:
                n = rig.POSES.get(anim, 4)
            keys += [f"{prefix}{v}/{anim}_{fc}/f{f}" for fc in FACINGS for f in range(n)]
    return keys


CRITTER_FRAMES = {"move": 6, "idle": 2, "graze": 4, "sleep": 2, "flap": 4, "peck": 4}


def required_keys(cat: dict, mod, pieces: dict) -> list[str]:
    keys = []
    for t in cat.get("terrain", []):
        if t.get("base"):
            keys += [f"terrain/{t['id']}/v{n}" for n in range(t["variants"])]
        else:
            frames = mod.FRAMES.get(t["id"], 4) if "fps" in t else 1
            keys += [f"terrain/{t['id']}/m{m}/f{f}" for m in range(16) for f in range(frames)]
    for it in cat["items"]:
        n = item_frames(it, mod)
        for layer in item_layers(it):
            for v in item_variants(it):
                if layer == "base" and it["id"] in pieces:
                    keys += [f"item/{it['id']}/base/{v}/p{i}/f{f}" for i in range(len(pieces[it["id"]]))
                             for f in range(n)]
                else:
                    keys += [f"item/{it['id']}/{layer}/{v}/f{f}" for f in range(n)]
        for state in it.get("states", ()):
            keys += [f"item/{it['id']}/{state}/{v}/f{f}" for v in item_variants(it) for f in range(n)]
    for a in cat.get("actors", []):
        keys += actor_keys(a)
    art = cat.get("art", {})
    for e in art.get("edges", ()):
        keys += [f"edge/{e}_{side}/v{n}" for side in ("se", "sw") for n in range(4)]
        keys += [f"edge/{e}_{side}/top" for side in ("se", "sw")]
    looks = getattr(mod, "BACKDROP_LOOKS", {})
    for b in art.get("backdrops", ()):
        times, count = looks.get(b, (("day", "night"), 4))
        keys += [f"backdrop/{b}/{t}/v{n}" for t in times for n in range(count)]
    for fxid in art.get("fx", ()):
        keys += [f"fx/{fxid}/f{f}" for f in range(mod.FRAMES.get(fxid, 6))]
    for g in cat.get("goods", []):        # living-world.md §3.2: the carried unit and 1..stack at a slot
        keys += [g["sprite"]] + [f"{g['sprite']}/s{n}" for n in range(1, g.get("stack", 3) + 1)]
    if hasattr(mod, "extra_keys"):      # keys a set's art implies beyond the shared scheme
        keys += mod.extra_keys(cat)
    seen = set()
    return [k for k in keys if not (k in seen or seen.add(k))]


# ---------- pieces (world-tech.md §1.3) ----------

def make_pieces(fw: int, fh: int, walk: set, water: set = frozenset()) -> list[list[int]]:
    """Walk tiles in straight runs of up to 8 (the longer axis first), then open-water tiles
    the same way; the other tiles in rectangles of at most 8 x 8, largest first, then
    row-major. Returns [dx, dy, w, h]."""
    owner = np.full((fw, fh), -1, np.int64)
    pieces = []
    for open_ in (walk, water):
        for x in range(fw):
            for y in range(fh):
                if (x, y) not in open_ or owner[x, y] >= 0:
                    continue
                nx = 1
                while nx < MAX_PIECE and x + nx < fw and (x + nx, y) in open_ and owner[x + nx, y] < 0:
                    nx += 1
                ny = 1
                while ny < MAX_PIECE and y + ny < fh and (x, y + ny) in open_ and owner[x, y + ny] < 0:
                    ny += 1
                w, h = (nx, 1) if nx >= ny else (1, ny)
                owner[x:x + w, y:y + h] = len(pieces)
                pieces.append([x, y, w, h])
    solid = np.array([[(x, y) not in walk and (x, y) not in water for y in range(fh)] for x in range(fw)])
    if fw <= MAX_PIECE and fh <= MAX_PIECE and not walk and not water:
        return [[0, 0, fw, fh]]
    while True:
        free = solid & (owner < 0)
        if not free.any():
            break
        best = None
        for x in range(fw):
            for y in range(fh):
                if not free[x, y]:
                    continue
                for w in range(1, min(MAX_PIECE, fw - x) + 1):
                    if not free[x + w - 1, y]:
                        break
                    h = 1
                    while h < MAX_PIECE and y + h < fh and free[x:x + w, y + h].all():
                        h += 1
                    if best is None or w * h > best[0]:
                        best = (w * h, x, y, w, h)
        _a, x, y, w, h = best
        owner[x:x + w, y:y + h] = len(pieces)
        pieces.append([x, y, w, h])
    return pieces


def piece_index(pieces, fw, fh) -> np.ndarray:
    idx = np.zeros((fw, fh), np.int64)
    for i, (x, y, w, h) in enumerate(pieces):
        idx[x:x + w, y:y + h] = i
    return idx


# ---------- jobs ----------

ITEM_KEY = re.compile(r"item/([^/]+)/([^/]+)/([^/]+)/f(\d+)")
ACTOR_KEY = re.compile(r"(walker|figure|critter|cart|ship)/([^/]+)(?:/v(\d+))?/(\w+)_(front|back)/f(\d+)")


def _set_mod(set_id):
    return load_set(set_id)


def _item_job(args):
    set_id, item_id, layout, variant, frame, frames, footprint, layers, k = args
    mod = _set_mod(set_id)
    item: Item = mod.ITEMS[item_id]
    n = int(variant[1:])
    fw, fh = footprint
    if layout == "rotate":
        model = item.build(0, frame, frames, k).rotated(n, fw, fh)
    else:
        model = item.build(n, frame, frames, k)
    out = render(model, "glow" in layers, cull=True)
    sprites = {"base": out.base, "shadow": out.shadow, "glow": out.glow}
    res = {f"item/{item_id}/{layer}/{variant}/f{frame}": sprites[layer] for layer in layers}
    zmax = int(np.nonzero((model.mat > 0).any(axis=(0, 1)))[0].max() + 1 + model.z0) if model.mat.any() else 0
    return res, {(item_id, variant): {"h": int(out.base.oy), "top": zmax}}


def _state_job(args):
    set_id, item_id, layout, state, variant, frame, frames, footprint, k = args
    mod = _set_mod(set_id)
    n = int(variant[1:])
    fw, fh = footprint
    build = mod.STATES[(item_id, state)]
    model = build(0 if layout == "rotate" else n, frame, frames, k)
    if layout == "rotate":
        model = model.rotated(n, fw, fh)
    return {f"item/{item_id}/{state}/{variant}/f{frame}": render(model, False).base}, {}


def _actor_job(args):
    set_id, kind, prefix, variant, anim, facing, frame, k = args
    mod = _set_mod(set_id)
    key = f"{prefix}{'' if variant is None else f'/v{variant}'}/{anim}_{facing}/f{frame}"
    return {key: mod.actor_sprite(kind, variant, anim, facing, frame, k)}, {}


def _flat_job(args):
    set_id, keys, cat, k = args
    return _set_mod(set_id).flat(keys, cat, k), {}


def _run(job):
    fn, args = job
    return fn(args)


def build_set(set_id: str, cat: dict, k: int, pool, only=None):
    mod = _set_mod(set_id)
    items = {it["id"]: it for it in cat["items"]}
    landmarks = {i: lm for i, lm in mod.LANDMARKS.items() if i in items}
    pieces = {}
    for i, lm in landmarks.items():
        fw, fh = lm.footprint
        if fw > MAX_PIECE or fh > MAX_PIECE or lm.walk or lm.water:
            pieces[i] = make_pieces(fw, fh, set(map(tuple, lm.walk)), set(map(tuple, lm.water)))
    keys = required_keys(cat, mod, pieces)
    if only:
        keys = [k_ for k_ in keys if any(o in k_ for o in only)]
    keyset = set(keys)
    jobs, flat = [], defaultdict(list)
    item_groups = defaultdict(list)
    lm_wanted = set()
    for key in keys:
        if m := ITEM_KEY.fullmatch(key):
            iid, layer, variant, frame = m.groups()
            if iid in landmarks:
                lm_wanted.add(iid)
                continue
            if layer in ("base", "shadow", "glow"):
                item_groups[(iid, variant, int(frame))].append(layer)
            else:
                it = items[iid]
                jobs.append((_state_job, (set_id, iid, it["layout"], layer, variant, int(frame), item_frames(it, mod),
                                          tuple(it["footprint"]), k)))
        elif key.startswith("item/") and "/p" in key:
            lm_wanted.add(key.split("/")[1])
        elif m := ACTOR_KEY.fullmatch(key):
            kind_type, kid, v, anim, facing, frame = m.groups()
            prefix = f"{kind_type}/{kid}"
            jobs.append((_actor_job, (set_id, kid, prefix, None if v is None else int(v), anim, facing, int(frame), k)))
        else:
            flat[key.split("/")[0]].append(key)
    for (iid, variant, frame), layers in item_groups.items():
        it = items[iid]
        jobs.append((_item_job, (set_id, iid, it["layout"], variant, frame, item_frames(it, mod),
                                 tuple(it["footprint"]), tuple(sorted(layers)), k)))
    jobs.sort(key=lambda j: 0 if j[0] is _item_job else 1)
    for group, ks in flat.items():
        for i in range(0, len(ks), 24):
            jobs.append((_flat_job, (set_id, ks[i:i + 24], cat, k)))
    sprites, meta = {}, {}
    t0 = time.time()
    for part, info in pool.imap_unordered(_run, jobs, chunksize=4):
        sprites.update(part)
        meta.update(info)
    print(f"  kit, actors, ground: {len(sprites)} sprites in {time.time() - t0:.1f}s")
    lm_info = {}
    for iid in sorted(lm_wanted):
        t1 = time.time()
        lm = landmarks[iid]
        it = items[iid]
        x1, y1 = lm.footprint[0] * spec.DESIGN_TILE, lm.footprint[1] * spec.DESIGN_TILE
        pad = 4
        big = BigModel(lm.build, (-pad, x1 + pad, -pad, y1 + pad, lm.z[0], lm.z[1]))
        layers = item_layers(it)
        r = render_big(big, k, pool, lm.footprint, want_glow="glow" in layers)
        fw, fh = lm.footprint
        if iid in pieces:
            idx = piece_index(pieces[iid], fw, fh)
            tile = r.tiles
            solid = r.base.rgba[..., 3] > 0
            owner = idx[np.clip(tile[0], 0, fw - 1), np.clip(tile[1], 0, fh - 1)]
            for i in range(len(pieces[iid])):
                part = r.base.rgba.copy()
                part[~(solid & (owner == i))] = 0
                sprites[f"item/{iid}/base/r0/p{i}/f0"] = Sprite(part, r.base.ox, r.base.oy)
        else:
            sprites[f"item/{iid}/base/r0/f0"] = r.base
        if "shadow" in layers:
            sprites[f"item/{iid}/shadow/r0/f0"] = _clip_hidden(r.shadow, r.base)
        if "glow" in layers:
            sprites[f"item/{iid}/glow/r0/f0"] = r.glow
        lm_info[iid] = {"h": int(r.base.oy), "top": r.top, "column": r.column}
        print(f"  {iid}: {r.base.rgba.shape[1]}x{r.base.rgba.shape[0]} px, "
              f"{len(pieces.get(iid, [1]))} pieces, {time.time() - t1:.1f}s")
    missing = sorted(keyset - set(sprites))
    if missing:
        raise SystemExit(f"setbuild: builders did not make {len(missing)} keys, e.g. {missing[:5]}")
    return {key: sprites[key] for key in keys}, pieces, meta, lm_info


def _clip_hidden(shadow: Sprite, base: Sprite) -> Sprite:
    """Drop the shadow pixels that lie under the landmark's own opaque pixels: the base is
    always drawn over them, so they are never seen, and a big closed building's shadow
    sprite shrinks to its cast band and front contact strip."""
    a = shadow.rgba.copy()
    h, w = a.shape[:2]
    y0, x0 = shadow.oy - base.oy, shadow.ox - base.ox
    bh, bw = base.rgba.shape[:2]
    ys0, ys1 = max(y0, 0), min(y0 + bh, h)
    xs0, xs1 = max(x0, 0), min(x0 + bw, w)
    if ys0 < ys1 and xs0 < xs1:
        cover = base.rgba[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0, 3] == 255
        a[ys0:ys1, xs0:xs1][cover] = 0
    return Sprite(a, shadow.ox, shadow.oy)


# ---------- geometry ----------

def _rot_tile(t, n, fw, fh):
    """A footprint offset (dx, dy) turned n quarter turns clockwise (as Model.rotated)."""
    x, y = t
    for _ in range(n % 4):
        x, y = fh - 1 - y, x
        fw, fh = fh, fw
    return [x, y]


def _emitter(pt, n, fw, fh, k):
    """Pixel offset from the anchor of a model point (design units) on the item turned n
    quarter turns, as Model.rotated turns the grid."""
    x, y, z = pt
    for _ in range(n % 4):
        x, y = fh * spec.DESIGN_TILE - y, x
        fw, fh = fh, fw
    return [int(round((x - y) * k)), int(round(((x + y) / 2 - z) * k))]


def _rot_face(face, n):
    order = ["-x", "-y", "+x", "+y"]       # north, east, south, west turn clockwise
    return order[(order.index(face) + n) % 4] if face in order else face


def geometry(set_id, cat, mod, pieces, meta, lm_info, k):
    out = {"version": 1, "set": set_id, "tile": [32 * k, 16 * k], "items": {}, "actors": {}}
    for it in cat["items"]:
        iid = it["id"]
        entry = {}
        fw, fh = it["footprint"]
        if iid in mod.LANDMARKS:
            lm = mod.LANDMARKS[iid]
            info = lm_info.get(iid)
            if info is None:
                continue
            g = {"h": info["h"]}
            if iid in pieces:
                g["pieces"] = pieces[iid]
            if lm.walk:
                g["walk"] = [list(t) for t in lm.walk]
            if lm.water:
                g["water"] = [list(t) for t in lm.water]
            if lm.floor:
                g["walk_z"] = {f"{x},{y}": int(round(z * k)) for (x, y), z in sorted(lm.floor.items())}
            if (lm.floor or lm.water) and iid in pieces:
                # Pieces that are floors (stair treads, decks) or open water: drawn before the
                # actors standing or floating on them.
                under = set(lm.floor) | set(map(tuple, lm.water))
                g["floor_pieces"] = [i for i, (x, y, w, h) in enumerate(pieces[iid])
                                     if all((xx, yy) in under for xx in range(x, x + w) for yy in range(y, y + h))]
            if lm.climb:
                g["climb"] = lm.climb
            if lm.slots:
                g["slots"] = lm.slots
            if lm.emitters:
                g["emitters"] = {n: [int(round((x - y) * k)), int(round(((x + y) / 2 - z) * k))]
                                 for n, (x, y, z) in lm.emitters.items()}
            entry["r0"] = g
        else:
            item = mod.ITEMS.get(iid)
            for v in item_variants(it):
                info = meta.get((iid, v))
                if info is None:
                    continue
                g = {"h": info["h"]}
                n = int(v[1:]) if v.startswith("r") and it["layout"] == "rotate" else 0
                if item and item.slots:
                    # A connect piece may place its spots by its look (a jetty along x or y).
                    slots = item.slots(v) if callable(item.slots) else item.slots
                    g["slots"] = {sid: [dict(s, t=_rot_tile(s["t"], n, fw, fh),
                                             **({"face": _rot_face(s["face"], n)} if "face" in s else {}))
                                        for s in spots] for sid, spots in slots.items()}
                if item and item.emitters:
                    g["emitters"] = {name: _emitter(pt, n, fw, fh, k) for name, pt in item.emitters.items()}
                walk = (item.walk(v) if callable(item.walk) else item.walk) if item else []
                if walk:
                    g["walk"] = sorted(_rot_tile(t, n, fw, fh) for t in walk)
                if it.get("rise"):      # kit stairs climb away from their front: r0 toward -y
                    g["climb"] = _rot_face("-y", n)
                entry[v] = g
        if entry:
            out["items"][iid] = entry
    for a in cat.get("actors", []):
        if "carry" in a["anims"] or "carry_idle" in a["anims"]:
            out["actors"][a["id"]] = {"carry_at": mod.carry_at(a["id"], k)}
    return out


# ---------- packing ----------

class Skyline:
    """Bottom-left skyline packing into one page: far denser than shelves when sprites of
    very different heights (walker frames, landmark pieces, shadows) share a page."""

    def __init__(self, width, height):
        self.W, self.H = width, height
        self.sky = [[0, 0, width]]          # segments [x, y, w], left to right

    def fit(self, w, h):
        best = None
        sky = self.sky
        for i in range(len(sky)):
            x = sky[i][0]
            if x + w > self.W:
                break
            y, j, left = 0, i, w
            while left > 0:
                y = max(y, sky[j][1])
                left -= sky[j][2]
                j += 1
            if y + h <= self.H and (best is None or y < best[1]):
                best = (x, y)
        return best

    def place(self, x, y, w, h):
        out, x1 = [], x + w
        for sx, sy, sw in self.sky:
            if sx + sw <= x or sx >= x1:
                out.append([sx, sy, sw])
                continue
            if sx < x:
                out.append([sx, sy, x - sx])
            if sx + sw > x1:
                out.append([x1, sy, sx + sw - x1])
        out.append([x, y + h, w])
        out.sort()
        merged = [out[0]]
        for seg in out[1:]:
            if seg[1] == merged[-1][1] and merged[-1][0] + merged[-1][2] == seg[0]:
                merged[-1][2] += seg[2]
            else:
                merged.append(seg)
        self.sky = merged


def pack_pages(sprites: dict, groups: list[list[str]], page=PAGE, fresh=(), order="height"):
    """Pack keys group by group into pages of at most page x page (skyline, tallest first within
    a group); a group whose index is in `fresh` starts on a new page. Earlier pages stay open,
    so small sprites of a later group fill gaps left on them. Returns [(atlas RGBA, manifest)]."""
    trimmed = {k: pack.trim(s) for k, s in sprites.items()}
    pad = pack.PAD
    pages: list[tuple[Skyline, dict]] = [(Skyline(page - pad, page - pad), {})]
    first_open = 0
    for gi, keys in enumerate(groups):
        if gi in fresh and pages[-1][1]:
            first_open = len(pages)
            pages.append((Skyline(page - pad, page - pad), {}))
        if order == "maxside":         # longest side first: denser when the set is nearly full
            seq = sorted(keys, key=lambda k_: (-max(trimmed[k_].rgba.shape[:2]), k_))
        else:
            seq = sorted(keys, key=lambda k_: (-trimmed[k_].rgba.shape[0], -trimmed[k_].rgba.shape[1], k_))
        for key in seq:
            h, w = trimmed[key].rgba.shape[:2]
            if w + 2 * pad > page or h + 2 * pad > page:
                raise SystemExit(f"setbuild: {key} ({w}x{h}) does not fit a {page} page")
            for sky, rects in pages[first_open:]:
                spot = sky.fit(w + pad, h + pad)
                if spot:
                    break
            else:
                pages.append((Skyline(page - pad, page - pad), {}))
                sky, rects = pages[-1]
                spot = sky.fit(w + pad, h + pad)
            sky.place(*spot, w + pad, h + pad)
            rects[key] = (spot[0] + pad, spot[1] + pad)
    out = []
    for _sky, rects in pages:
        height = max(yy + trimmed[k_].rgba.shape[0] for k_, (_xx, yy) in rects.items()) + pad
        height = min(page, -(-height // 256) * 256)
        atlas = np.zeros((height, page, 4), np.uint8)
        manifest = {}
        for k_ in sorted(rects):
            t = trimmed[k_]
            xx, yy = rects[k_]
            h, w = t.rgba.shape[:2]
            atlas[yy:yy + h, xx:xx + w] = t.rgba
            manifest[k_] = {"x": xx, "y": yy, "w": w, "h": h, "ox": t.ox, "oy": t.oy}
        out.append((atlas, manifest))
    return out


def page_groups(keys, cat, mod):
    """Packing groups: kit and actors, each landmark district, then shadows and glows. Districts
    a set lists in `LATE_DISTRICTS` (landmarks added after its pages were laid out) follow as
    one last group with their own shadows and glows, on pages of their own, so the earlier
    pages keep their layout."""
    lm_ids = {it["id"]: mod.LANDMARKS[it["id"]].district for it in cat["items"] if it["id"] in mod.LANDMARKS}
    late = getattr(mod, "LATE_DISTRICTS", frozenset())
    small, layer, landmark, later = [], [], defaultdict(list), []
    for key in keys:
        parts = key.split("/")
        if parts[0] == "item" and lm_ids.get(parts[1]) in late:
            later.append(key)
        elif "/shadow/" in key or "/glow/" in key:
            layer.append(key)
        elif parts[0] == "item" and parts[1] in lm_ids:
            landmark[lm_ids[parts[1]]].append(key)
        else:
            small.append(key)
    groups = [small, *[landmark[d] for d in sorted(landmark)], layer]
    if getattr(mod, "ONE_GROUP", False):     # a full set packs densest as one group, tallest first
        groups = [[k_ for g in groups for k_ in g]]
    return groups + [later] if later else groups, ({len(groups)} if later else set())


# ---------- main ----------

def main(build: spec.Build, args) -> int:
    set_id = args.set
    cat_path = SETS / set_id / "catalog.json"
    cat = json.loads(cat_path.read_text())
    mod = _set_mod(set_id)
    t0 = time.time()
    with Pool(min(4, max(1, __import__("os").cpu_count() // 2))) as pool:
        sprites, pieces, meta, lm_info = build_set(set_id, cat, build.k, pool, args.only)
    out_dir = build.out
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = list(sprites)
    groups, late = page_groups(keys, cat, mod)
    layer_i = len(groups) - 1 - len(late)
    order = getattr(mod, "PACK_ORDER", "height")
    pages = pack_pages(sprites, groups, fresh=late, order=order)
    if len(groups) - len(late) == 1:           # one group: no separate shadow page to try
        layer_i = None
    # Shadows and glows on their own page when that costs no extra page.
    alone = pack_pages(sprites, groups, fresh=({layer_i} if layer_i is not None else set()) | late, order=order)
    if len(alone) <= max(len(pages), getattr(mod, "ALONE_PAGES", 2) + len(late)):
        pages = alone
    for old in out_dir.glob(f"{set_id}.*.png"):
        old.unlink()
    for old in out_dir.glob(f"{set_id}.*.json"):
        if old.name != f"{set_id}.geom.json":
            old.unlink()
    from PIL import Image
    total = 0
    for n, (atlas, manifest) in enumerate(pages):
        png = out_dir / f"{set_id}.{n}.png"
        Image.fromarray(atlas, "RGBA").save(png, optimize=True)
        doc = {"version": 1, "image": png.name, "sprites": manifest}
        (out_dir / f"{set_id}.{n}.json").write_text(json.dumps(doc, indent=1) + "\n")
        total += png.stat().st_size
        print(f"page {png.name}: {atlas.shape[1]}x{atlas.shape[0]}, {len(manifest)} sprites, "
              f"{png.stat().st_size / 1e6:.2f} MB")
    if not args.only:
        geom = geometry(set_id, cat, mod, pieces, meta, lm_info, build.k)
        (out_dir / f"{set_id}.geom.json").write_text(json.dumps(geom, indent=1) + "\n")
    print(f"set {set_id}: {len(sprites)} sprites on {len(pages)} pages ({total / 1e6:.2f} MB) "
          f"in {time.time() - t0:.1f}s")
    import setvalidate
    status = 0 if args.only else setvalidate.main(set_id, out_dir, build.k, lm_info)
    if args.preview:
        importlib.import_module(f"sets.{set_id}.preview").main(build, out_dir)
    return status


if __name__ == "__main__":
    b, a = spec.parse_build(sys.argv[1:])
    sys.exit(main(b, a))
