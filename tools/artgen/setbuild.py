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
import props
import rig
import slopes
import spec
from bigrender import BigModel, clearance, passage, render_big
from pack import Sprite
from palette import palette_for
from render import render

SETS = spec.ROOT / "assets" / "sets"
PAGE = 4096
WALK_HEADROOM = 48          # px at 64x32: 1.5 tile.h above a walk tile's floor
MAX_PIECE = 8
# Pages a set may fill (graphics-plan §2.5: every set keeps its page count).
MAX_PAGES = {"parsa": 2, "athens": 2, "rome": 4, "world": 1}
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


def anim_frames(mod, a: dict, anim: str) -> int:
    """Frames of one animation of an actor: the set's `anim_frames(kind, anim)` where it gives
    one (a page budget), else the scheme's (people, animals, carts, ships)."""
    n = getattr(mod, "anim_frames", lambda kind, anim: None)(a["id"], anim)
    if n:
        return n
    prefix = a["sprite"]
    if prefix.startswith("critter/"):
        return CRITTER_FRAMES.get(anim, 4)
    if prefix.startswith("cart/"):
        return rig.CART_FRAMES if anim == "move" else 4
    if prefix.startswith("ship/"):
        return 4                                        # world-tech.md §1.9: ships
    return rig.POSES.get(anim, 4)


def actor_keys(a: dict, mod) -> list[str]:
    prefix = a["sprite"]
    variants = a.get("variants", 0)
    vs = [f"/v{v}" for v in range(variants)] if variants else [""]
    keys = []
    for v in vs:
        for anim in a["anims"]:
            n = anim_frames(mod, a, anim)
            keys += [f"{prefix}{v}/{anim}_{fc}/f{f}" for fc in FACINGS for f in range(n)]
    return keys


CRITTER_FRAMES = rig.CRITTER_FRAMES
WEDGE_LOOKS = 4
SLOPE_KEY = re.compile(r"terrain/([^/]+)/slope/(\w+)/v(\d+)")


def slope_looks(t: dict) -> int:
    """Looks per slope shape (art-smooth-land.md §3.3): two for a base ground, which covers most
    hillsides, one for an overlay (its tile's interior look)."""
    return 2 if t.get("base") else 1


def required_keys(cat: dict, mod, pieces: dict, kit_pieces: dict | None = None) -> list[str]:
    """Every key the set catalog implies. `pieces`: landmark id -> its pieces; `kit_pieces`: kit
    item id -> {variant: pieces} for kit items with walk tiles (their whole sprites stay too)."""
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
                    if layer == "base" and v in (kit_pieces or {}).get(it["id"], {}):
                        keys += [f"item/{it['id']}/base/{v}/p{i}/f0" for i in range(len(kit_pieces[it["id"]][v]))]
        for state in it.get("states", ()):
            keys += [f"item/{it['id']}/{state}/{v}/f{f}" for v in item_variants(it) for f in range(n)]
    for a in cat.get("actors", []):
        keys += actor_keys(a, mod)
    art = cat.get("art", {})
    looks = getattr(mod, "EDGE_VARIANTS", {})
    for e in art.get("edges", ()):
        keys += [f"edge/{e}_{side}/v{n}" for side in ("se", "sw") for n in range(looks.get(e, 4))]
        keys += [f"edge/{e}_{side}/top" for side in ("se", "sw")]
        if e in looks:              # natural faces: the wedge under a slope's falling edge
            keys += [f"edge/{e}_{side}/w{w}/v{n}" for side in ("se", "sw") for w in (0, 1) for n in range(WEDGE_LOOKS)]
    terrain = {t["id"]: t for t in cat.get("terrain", [])}
    for tid in art.get("slopes", ()):
        keys += [f"terrain/{tid}/slope/{shape}/v{n}" for shape in slopes.SHAPES
                 for n in range(slope_looks(terrain[tid]))]
    bd_looks = getattr(mod, "BACKDROP_LOOKS", {})
    for b in art.get("backdrops", ()):
        times, count = bd_looks.get(b, (("day", "night"), 4))
        keys += [f"backdrop/{b}/{t}/v{n}" for t in times for n in range(count)]
    for fxid in art.get("fx", ()):
        keys += [f"fx/{fxid}/f{f}" for f in range(mod.FRAMES.get(fxid, 6))]
    for g in cat.get("goods", []):        # living-world.md §3.2: the carried unit and 1..stack at a slot
        keys += [g["sprite"]] + [f"{g['sprite']}/s{n}" for n in range(1, g.get("stack", 3) + 1)]
    for pid in art.get("props", ()):     # carried lights (props.py)
        keys += props.keys(pid)
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


def kit_walk(item: "Item", it: dict, v: str) -> list:
    """A kit item's walk tiles in look `v` (turned with the item)."""
    walk = (item.walk(v) if callable(item.walk) else item.walk) if item else []
    n = int(v[1:]) if v.startswith("r") and it["layout"] == "rotate" else 0
    fw, fh = it["footprint"]
    return sorted(tuple(_rot_tile(t, n, fw, fh)) for t in walk)


def kit_piece_map(cat: dict, mod) -> dict:
    """Pieces of the kit items with walk tiles, per look (draw-order.md §5 P1): walk tiles in
    runs of their own, so a walker on them is ordered against the item round them."""
    out = {}
    for it in cat["items"]:
        item = mod.ITEMS.get(it["id"])
        if item is None or it["id"] in mod.LANDMARKS or not item.walk:
            continue
        for v in item_variants(it):
            walk = kit_walk(item, it, v)
            if walk:
                n = int(v[1:]) if v.startswith("r") and it["layout"] == "rotate" else 0
                fw, fh = it["footprint"] if n % 2 == 0 else it["footprint"][::-1]
                out.setdefault(it["id"], {})[v] = make_pieces(fw, fh, set(walk))
    return out


def columns(model, fw: int, fh: int):
    """((fw, fh, top) bool: solid at that height (px above the anchor's ground) on that footprint
    tile, (fw, fh) clearance (bigrender.clearance), (fw, fh) a boat's passage (bigrender.passage)),
    from the model's own voxels (context excluded)."""
    vis = model.visible() > 0
    t = spec.DESIGN_TILE * model.k
    nz = max(0, model.z0 + vis.shape[2])
    col = np.zeros((fw, fh, max(nz, 1)), bool)
    tx = (np.arange(vis.shape[0]) + model.x0) // t
    ty = (np.arange(vis.shape[1]) + model.y0) // t
    z = np.arange(vis.shape[2]) + model.z0
    for x in range(fw):
        for y in range(fh):
            sub = vis[tx == x][:, ty == y]
            if sub.size:
                c = sub.any(axis=(0, 1))
                col[x, y, z[(z >= 0) & c]] = True
    above = vis[:, :, max(0, -model.z0):]
    return col, clearance(above, model.x0, model.y0, fw, fh, t), passage(above, model.x0, model.y0, fw, fh, t)


def order_geometry(col: np.ndarray, clear: np.ndarray, gap: np.ndarray, walk, walk_z: dict, pieces, k: int,
                   water=(), crossing=False) -> dict:
    """What the global draw order needs of an item in one look (draw-order.md §3.4, §5 O1):
    `tops`, the highest point in px above the anchor's ground of what stands on each footprint
    tile, rows by dy (a walk tile gives its floor); `roof`, over each walk tile with something
    above the headroom, that thing's top; `under`, per piece, the clearance where something can
    pass beneath it: the most room under it on its walk and water tiles (`clear`: under an arch's
    crown, a deck's underside between the piers; 0 for a piece with neither, eaves included). An
    unsplit crossing (a kit bridge) gives one value for its whole footprint."""
    fw, fh = col.shape[:2]
    head = WALK_HEADROOM * k // 2
    top = np.where(col.any(axis=2), col.shape[2] - np.argmax(col[:, :, ::-1], axis=2), 0)
    out = {"tops": [[int(top[x, y]) for x in range(fw)] for y in range(fh)]}
    roof = {}
    for (x, y) in sorted(map(tuple, walk)):
        floor = int(walk_z.get((x, y), 0))
        out["tops"][y][x] = floor
        above = np.nonzero(col[x, y, floor + head:])[0]
        if above.size:
            roof[f"{x},{y}"] = int(top[x, y])
    if roof:
        out["roof"] = roof
    passable = set(map(tuple, walk)) | set(map(tuple, water))
    if pieces:
        out["under"] = [max([int(clear[a, b]) for a in range(x, x + w) for b in range(y, y + h)
                             if (a, b) in passable], default=0) for x, y, w, h in pieces]
    elif crossing and clear.max() > 0:
        out["under"] = [int(clear.max())]
    if water or crossing:
        # What may pass through each tile (art-smooth-land.md §8): px a boat's whole height must
        # stay under, rows by dy like `tops`; 255 open sky, 0 nothing passes.
        out["pass"] = [[int(gap[x, y]) for x in range(fw)] for y in range(fh)]
    return out


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
    set_id, item_id, layout, variant, frame, frames, footprint, layers, k, pieces, crossing, deck = args
    mod = _set_mod(set_id)
    item: Item = mod.ITEMS[item_id]
    n = int(variant[1:])
    fw, fh = footprint
    if layout == "rotate":
        model = item.build(0, frame, frames, k).rotated(n, fw, fh)
    else:
        model = item.build(n, frame, frames, k)
    out = render(model, "glow" in layers, cull=True, hit=bool(pieces))
    sprites = {"base": out.base, "shadow": out.shadow, "glow": out.glow}
    res = {f"item/{item_id}/{layer}/{variant}/f{frame}": sprites[layer] for layer in layers}
    rfw, rfh = (fh, fw) if layout == "rotate" and n % 2 else (fw, fh)
    if pieces and frame == 0:       # walk tiles in runs of their own, cut as the landmarks' are
        t = spec.DESIGN_TILE * k
        idx = piece_index(pieces, rfw, rfh)
        vx, vy = out.hit
        owner = idx[np.clip(vx // t, 0, rfw - 1), np.clip(vy // t, 0, rfh - 1)]
        solid = out.base.rgba[..., 3] > 0
        for i in range(len(pieces)):
            keep = solid & (owner == i)
            part = out.base.rgba.copy()
            part[~keep] = 0
            res[f"item/{item_id}/base/{variant}/p{i}/f0"] = Sprite(part, out.base.ox, out.base.oy,
                                                                   np.where(keep, out.base.data, 0).astype(np.uint32))
    zmax = int(np.nonzero((model.mat > 0).any(axis=(0, 1)))[0].max() + 1 + model.z0) if model.mat.any() else 0
    walk = kit_walk(item, {"layout": layout, "footprint": footprint}, variant)
    if frame:                       # every frame of a look shares its geometry: frame 0 gives it
        return res, {}
    order = order_geometry(*columns(model, rfw, rfh), walk, {}, pieces, k, crossing=crossing)
    if deck and not walk:           # a deck walked over whole (bridges, jetties, pontoons, moles):
        # its floor by walk tiles and their heights, as the engine's loader wants (walk_z only
        # on listed walk tiles, src/world/geometry.cpp)
        order["walk"] = [[x, y] for x in range(rfw) for y in range(rfh)]
        order["walk_z"] = deck_heights(model, rfw, rfh)
    return res, {(item_id, variant): {"h": int(out.base.oy), "top": zmax, "lights": _lights(model, k), **order}}


def is_deck(it: dict) -> bool:
    """A kit piece walked on as a floor of its own (bridges, jetties, pontoons, moles, fords):
    a crossing, or walkable over water; not a plant one walks through."""
    return not it.get("landmark") and ("crossing" in it.get("tags", ()) or
                                       (bool(it.get("walkable")) and it.get("on") in ("water", "either")))


def deck_heights(model, fw: int, fh: int) -> dict:
    """The floor a walker stands on over each footprint tile of a walkable kit piece: the top of
    what is solid over the tile's middle quarter (the deck between the rails), px above the ground,
    `{"dx,dy": px}` like a landmark's `walk_z`; 0 where nothing stands there (a ford's bed)."""
    t = spec.DESIGN_TILE * model.k
    q = 3 * t // 8                  # the middle quarter of the tile: inside any rails or bollards
    solid = model.mat > 0
    out = {}
    for x in range(fw):
        for y in range(fh):
            a, b = x * t - model.x0 + q, y * t - model.y0 + q
            sub = solid[max(a, 0):max(a + t // 4, 0), max(b, 0):max(b + t // 4, 0)]
            has = sub.any(axis=(0, 1))
            out[f"{x},{y}"] = int(max(0, np.nonzero(has)[0].max() + 1 + model.z0)) if has.any() else 0
    return out


# The spread of light out of a doorway and a window, degrees (realism.md §5.3, R1's cone).
LIGHT_CONE = {"door": 120, "window": 90}


def _facing(model, h) -> list[int] | None:
    """The outward normal (grid axes) of the wall a light point sits in: of the four ways along
    the ground, the one that is open in front of the point while the opposite side is solid
    (the wall behind it); None for a light standing free."""
    k = model.k
    px, py, pz = (int(round(c * k)) - o for c, o in ((h.x, model.x0), (h.y, model.y0), (h.z, model.z0)))
    nx, ny, nz = model.mat.shape
    if not (0 <= pz < nz):
        return None
    reach = 3 * k

    def solid(dx, dy):
        n = 0
        for i in range(1, reach + 1):
            x, y = px + dx * i, py + dy * i
            if 0 <= x < nx and 0 <= y < ny and model.mat[x, y, pz]:
                n += 1
        return n
    best, score = None, 0
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sc = solid(-d[0], -d[1]) - solid(*d)
        if sc > score:
            best, score = list(d), sc
    return best


def _lights(model, k) -> dict:
    """The model's door and window light points (halos and marks with a kind), as pixel offsets
    from the anchor with their height and the way their light goes out (`dir`, the wall's
    outward normal in grid axes, and `cone` in degrees):
    `{"door_0": {"at": [x, y], "z": z, "dir": [1, 0], "cone": 120}, ...}`."""
    out, seen = {}, defaultdict(int)
    for h in sorted((h for h in model.halos + model.marks if h.kind), key=lambda h: (h.kind, h.x, h.y, h.z)):
        name = f"{h.kind}_{seen[h.kind]}"
        seen[h.kind] += 1
        out[name] = {"at": [int(round((h.x - h.y) * k)), int(round(((h.x + h.y) / 2 - h.z) * k))],
                     "z": int(round(h.z * k))}
        face = _facing(model, h)
        if face is not None:
            out[name]["dir"] = face
            out[name]["cone"] = LIGHT_CONE.get(h.kind, 90)
    return out


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
    s = mod.actor_sprite(kind, variant, anim, facing, frame, k)
    out = {key: s}
    if s.glow is not None:      # a lantern or torch on the figure or cart: its glow frame
        out[key.rsplit("/", 1)[0] + f"/glow/f{frame}"] = Sprite(s.glow, s.ox, s.oy)
        s.glow = None
    return out, {}


def _prop_job(args):
    pid, frame, k = args
    out = render(props.model(pid, frame, k), True)
    return {f"prop/{pid}/f{frame}": out.base, f"prop/{pid}/glow/f{frame}": out.glow}, {}


def _flat_job(args):
    set_id, keys, cat, k = args
    return _set_mod(set_id).flat(keys, cat, k), {}


def _slope_job(args):
    """Every shape of one slope look: the terrain's flat interior (an overlay over its base)
    laid on each shape and lit (slopes.py)."""
    set_id, tid, v, shapes, cat, k = args
    mod = _set_mod(set_id)
    t = next(t for t in cat["terrain"] if t["id"] == tid)
    base = tid if t.get("base") else t["under"]
    nbase = next(b for b in cat["terrain"] if b["id"] == base)["variants"]
    want = [f"terrain/{base}/v{v % nbase}"] + ([] if t.get("base") else [f"terrain/{tid}/m15/f0"])
    flats = mod.flat(want, cat, k)
    flat = flats[want[0]]
    rgba = flat.rgba.copy()
    for key in want[1:]:
        over = flats[key].rgba
        a = over[..., 3:4].astype(np.float32) / 255
        rgba[..., :3] = np.where(a > 0.5, over[..., :3], rgba[..., :3])
    pal = slopes.palette_codes(palette_for(set_id))
    lay = Sprite(rgba, flat.ox, flat.oy)
    return {f"terrain/{tid}/slope/{shape}/v{v}": slopes.slope_sprite(lay, shape, k, 8 * k, pal)
            for shape in shapes}, {}


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
    kit_pieces = kit_piece_map(cat, mod)
    keys = required_keys(cat, mod, pieces, kit_pieces)
    if only:
        keys = [k_ for k_ in keys if any(o in k_ for o in only)]
    keyset = set(keys)
    jobs, flat = [], defaultdict(list)
    item_groups = defaultdict(list)
    slope_groups = defaultdict(list)
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
            if key.split("/")[1] in landmarks:    # a kit item's pieces come with its look's frame 0
                lm_wanted.add(key.split("/")[1])
        elif key.startswith("prop/"):
            pid, rest = key[5:].split("/", 1)
            if not rest.startswith("glow/"):
                jobs.append((_prop_job, (pid, int(rest[1:]), k)))
        elif m := SLOPE_KEY.fullmatch(key):
            slope_groups[(m[1], int(m[3]))].append(m[2])
        elif m := ACTOR_KEY.fullmatch(key):
            kind_type, kid, v, anim, facing, frame = m.groups()
            prefix = f"{kind_type}/{kid}"
            jobs.append((_actor_job, (set_id, kid, prefix, None if v is None else int(v), anim, facing, int(frame), k)))
        else:
            flat[key.split("/")[0]].append(key)
    for (iid, variant, frame), layers in item_groups.items():
        it = items[iid]
        jobs.append((_item_job, (set_id, iid, it["layout"], variant, frame, item_frames(it, mod),
                                 tuple(it["footprint"]), tuple(sorted(layers)), k,
                                 kit_pieces.get(iid, {}).get(variant), bool(it.get("crossing") or it.get("walkable")),
                                 is_deck(it))))
    for (tid, v), shapes in slope_groups.items():
        jobs.append((_slope_job, (set_id, tid, v, tuple(shapes), cat, k)))
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
                keep = solid & (owner == i)
                part = r.base.rgba.copy()
                part[~keep] = 0
                data = np.where(keep, r.base.data, 0).astype(np.uint32)
                sprites[f"item/{iid}/base/r0/p{i}/f0"] = Sprite(part, r.base.ox, r.base.oy, data)
        else:
            sprites[f"item/{iid}/base/r0/f0"] = r.base
        if "shadow" in layers:
            sprites[f"item/{iid}/shadow/r0/f0"] = _clip_hidden(r.shadow, r.base)
        if "glow" in layers:
            sprites[f"item/{iid}/glow/r0/f0"] = r.glow
        floor = {t: int(round(z * k)) for t, z in lm.floor.items()}
        lm_info[iid] = {"h": int(r.base.oy), "top": r.top, "column": r.column,
                        "order": order_geometry(r.column, r.clear, r.passage, lm.walk, floor, pieces.get(iid), k,
                                                lm.water, crossing=it.get("on") == "water")}
        print(f"  {iid}: {r.base.rgba.shape[1]}x{r.base.rgba.shape[0]} px, "
              f"{len(pieces.get(iid, [1]))} pieces, {time.time() - t1:.1f}s")
    missing = sorted(keyset - set(sprites))
    if missing:
        raise SystemExit(f"setbuild: builders did not make {len(missing)} keys, e.g. {missing[:5]}")
    glows = sorted(k_ for k_ in sprites if k_ not in keyset and "/glow/" in k_)
    meta["glow_at"] = _glow_at({k_: sprites[k_] for k_ in glows})
    meta["kit_pieces"] = kit_pieces
    return {key: sprites[key] for key in keys + glows}, pieces, meta, lm_info


def _glow_at(glows: dict) -> dict:
    """Per actor with glow frames (variant 0): the alpha-weighted centre of each frame's glow,
    as a pixel offset from the anchor, for the light pool it casts."""
    out = defaultdict(dict)
    for key, s in glows.items():
        m = ACTOR_KEY.fullmatch(key.replace("/glow/", "/"))
        if m is None or (m[3] not in (None, "0")):
            continue
        a = s.rgba[..., 3].astype(np.float64)
        ys, xs = np.mgrid[:a.shape[0], :a.shape[1]]
        at = [int(round((a * xs).sum() / a.sum())) - s.ox, int(round((a * ys).sum() / a.sum())) - s.oy]
        frames = out[m[2]].setdefault(f"{m[4]}_{m[5]}", {})
        frames[int(m[6])] = at
    return {aid: {anim: [fr[i] for i in sorted(fr)] for anim, fr in anims.items()} for aid, anims in out.items()}


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
            g.update(info["order"])
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
                if info.get("lights"):  # door and window light points (world-nights.md §7)
                    g["lights"] = info["lights"]
                if v in meta.get("kit_pieces", {}).get(iid, {}):
                    g["pieces"] = meta["kit_pieces"][iid][v]
                for key in ("tops", "roof", "under", "pass", "walk", "walk_z"):
                    if key in info:
                        g[key] = info[key]
                entry[v] = g
        if entry:
            out["items"][iid] = entry
    people = getattr(mod, "people", None)
    for a in cat.get("actors", []):
        entry = {}
        if "carry" in a["anims"] or "carry_idle" in a["anims"]:
            entry["carry_at"] = mod.carry_at(a["id"], k)
        # Where a carried light sits, frame by frame (props.py), for people on foot.
        hands = {an: anim_frames(mod, a, an) for an in HAND_ANIMS if an in a["anims"]}
        if people is not None and hands and a["sprite"].startswith(("walker/", "figure/")) \
                and people._posed(a["id"], 0, next(iter(hands))).mount is None:
            entry["hand_at"] = rig.hand_table(lambda an, aid=a["id"]: people._posed(aid, 0, an), hands, k)
        if a["id"] in meta.get("glow_at", {}):
            entry["glow_at"] = meta["glow_at"][a["id"]]
        if entry:
            out["actors"][a["id"]] = entry
    return out


HAND_ANIMS = ("move", "idle", "march", "run")


def compact_json(doc) -> str:
    """JSON with one key per line but every list of numbers on one line (geometry files hold
    thousands of short points)."""
    text = json.dumps(doc, indent=1)
    num = r"-?\d+(?:\.\d+)?"
    return re.sub(rf"\[\s*((?:{num},\s*)*{num})\s*\]", lambda m: "[" + re.sub(r",\s+", ", ", m[1]) + "]", text) + "\n"


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


def pack_pages(sprites: dict, groups: list[tuple[list[str], bool]], page=PAGE):
    """Pack groups of keys into pages of at most page x page (skyline, longest side first). An
    atomic group lands whole on the first page with room for all of it (a new page when none
    has), so a district or a city's people never straddle two pages; a non-atomic group fills
    gaps sprite by sprite from the first page on. Identical sprites of one group (same pixels,
    anchor and data: a two-pose loop stored as four frames, a still cart's idle) share one
    rectangle; the manifest lists every key. Returns [(atlas RGBA, manifest)]."""
    trimmed = {k: pack.trim(s) for k, s in sprites.items()}
    # Sharing stays inside a group: a sprite pointing at a twin on another page would make the
    # engine switch pages for it in the middle of a district's draw order (an empty landmark
    # piece shared across districts cost the Acropolis some fifty draws a frame).
    group_of = {k_: i for i, (keys, _atomic) in enumerate(groups) for k_ in keys}
    first: dict[tuple, str] = {}
    same: dict[str, str] = {}          # key -> the earlier key (in sorted order) it shares pixels with
    for k_ in sorted(trimmed):
        sig = (group_of.get(k_, -1), pack.signature(trimmed[k_]))
        if sig in first:
            same[k_] = first[sig]
        else:
            first[sig] = k_
    pad = pack.PAD
    pages: list[tuple[Skyline, dict]] = []

    def size(key):
        h, w = trimmed[key].rgba.shape[:2]
        if w + 2 * pad > page or h + 2 * pad > page:
            raise SystemExit(f"setbuild: {key} ({w}x{h}) does not fit a {page} page")
        return w + pad, h + pad

    def place_all(sky: Skyline, rects: dict, seq) -> bool:
        trial = Skyline(sky.W, sky.H)
        trial.sky = [list(seg) for seg in sky.sky]
        got = {}
        for key in seq:
            spot = trial.fit(*size(key))
            if spot is None:
                return False
            trial.place(*spot, *size(key))
            got[key] = (spot[0] + pad, spot[1] + pad)
        sky.sky = trial.sky
        rects.update(got)
        return True

    def new_page():
        pages.append((Skyline(page - pad, page - pad), {}))
        return pages[-1]

    for keys, atomic in groups:
        seq = sorted((k_ for k_ in keys if k_ not in same), key=lambda k_: (-max(size(k_)), k_))
        if not seq:
            continue
        if atomic and (any(place_all(sky, rects, seq) for sky, rects in pages) or place_all(*new_page(), seq)):
            continue
        for key in seq:                # a non-atomic group, or one larger than a page
            for sky, rects in pages:
                if (spot := sky.fit(*size(key))) is not None:
                    break
            else:
                sky, rects = new_page()
                spot = sky.fit(*size(key))
            sky.place(*spot, *size(key))
            rects[key] = (spot[0] + pad, spot[1] + pad)
    placed = {k_: n for n, (_sky, rects) in enumerate(pages) for k_ in rects}
    for k_, src in same.items():
        pages[placed[src]][1][k_] = pages[placed[src]][1][src]
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


FILLER_PREFIX = ("terrain/", "edge/", "backdrop/", "fx/", "weather/", "ui/")


def page_groups(keys, cat, mod) -> list[tuple[list[str], bool]]:
    """Packing groups by what one view draws together (out/reports/perf-notes-for-art.md): the
    city's people with the kit and plants they move among (seasonal looks beside their plain
    sprites), then each landmark district whole (a set's `DISTRICT_ORDER` first: its busiest
    views share the people's page when they fit), then glows, shadows, ground, faces, backdrops
    and effects filling the gaps: the engine draws glows and shadows in passes of their own
    sorted by page and caches ground in cells, so where they sit costs a draw at most."""
    lm_ids = {it["id"]: mod.LANDMARKS[it["id"]].district for it in cat["items"] if it["id"] in mod.LANDMARKS}
    people, glow, shadow, filler, landmark = [], [], [], [], defaultdict(list)
    for key in keys:
        parts = key.split("/")
        if "/shadow/" in key:
            shadow.append(key)
        elif "/glow/" in key:
            glow.append(key)
        elif parts[0] == "item" and parts[1] in lm_ids:
            landmark[lm_ids[parts[1]]].append(key)
        elif key.startswith(FILLER_PREFIX):
            filler.append(key)
        else:
            people.append(key)
    first = [d for d in getattr(mod, "DISTRICT_ORDER", ()) if d in landmark]
    order = first + sorted(d for d in landmark if d not in first)
    return [(people, True), *[(landmark[d], True) for d in order], (glow + shadow + filler, False)]


# ---------- main ----------

def main(build: spec.Build, args) -> int:
    set_id = args.set
    cat_path = SETS / set_id / "catalog.json"
    cat = json.loads(cat_path.read_text())
    mod = _set_mod(set_id)
    t0 = time.time()
    with Pool(spec.WORKERS) as pool:
        sprites, pieces, meta, lm_info = build_set(set_id, cat, build.k, pool, args.only)
    out_dir = build.out
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = page_groups(list(sprites), cat, mod)
    budget = MAX_PAGES.get(set_id, 2)
    pages = pack_pages(sprites, groups)
    if len(pages) > budget:     # districts may straddle pages; the people stay whole
        print(f"  {len(pages)} pages: districts packed loosely to keep {budget}")
        pages = pack_pages(sprites, [groups[0], ([k_ for g, _a in groups[1:] for k_ in g], False)])
    for old in out_dir.glob(f"{set_id}.*.png"):
        old.unlink()
    for old in out_dir.glob(f"{set_id}.*.json"):
        if old.name != f"{set_id}.geom.json":
            old.unlink()
    from PIL import Image
    import datapages
    import ramps
    ramps.write(out_dir)
    trimmed = {k_: pack.trim(s) for k_, s in sprites.items()}
    total = 0
    for n, (atlas, manifest) in enumerate(pages):
        png = out_dir / f"{set_id}.{n}.png"
        Image.fromarray(atlas, "RGBA").save(png, optimize=True)
        doc = {"version": 1, "image": png.name, "sprites": manifest}
        (out_dir / f"{set_id}.{n}.json").write_text(json.dumps(doc, indent=1) + "\n")
        datapages.write_packed(png, manifest, trimmed, atlas.shape, "ramps.json")
        size = png.stat().st_size + datapages.packed_path(png).stat().st_size
        total += size
        print(f"page {png.name}: {atlas.shape[1]}x{atlas.shape[0]}, {len(manifest)} sprites, "
              f"{png.stat().st_size / 1e6:.2f} MB + packed {datapages.packed_path(png).stat().st_size / 1e6:.2f} MB")
    sw, sh_, sn = datapages.write_shadow_page(out_dir / f"{set_id}.s.png", sprites)
    total += (out_dir / f"{set_id}.s.png").stat().st_size
    print(f"shadow page {set_id}.s.png: {sw}x{sh_}, {sn} sprites at half size")
    ww, wh, wn = datapages.write_water_page(out_dir / f"{set_id}.w.png", trimmed)
    total += (out_dir / f"{set_id}.w.png").stat().st_size
    print(f"water page {set_id}.w.png: {ww}x{wh}, {wn} sprites holding water")
    if not args.only:
        geom = geometry(set_id, cat, mod, pieces, meta, lm_info, build.k)
        (out_dir / f"{set_id}.geom.json").write_text(compact_json(geom))
    print(f"set {set_id}: {len(sprites)} sprites on {len(pages)} pages ({total / 1e6:.2f} MB) "
          f"in {time.time() - t0:.1f}s")
    import gc
    import setvalidate
    del sprites, trimmed, pages, meta        # the validator reads the pages back: free the images first
    gc.collect()
    status = 0 if args.only else setvalidate.main(set_id, out_dir, build.k, lm_info)
    if args.preview:
        importlib.import_module(f"sets.{set_id}.preview").main(build, out_dir)
    return status


if __name__ == "__main__":
    b, a = spec.parse_build(sys.argv[1:])
    sys.exit(main(b, a))
