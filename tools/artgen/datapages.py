"""The shader path's pages beside every colour page (graphics-plan §2; schema in README.md "Data
pages"): the packed page `<page>.p.png` with its side file `<page>.p.json`, and the set's
half-size shadow page `<set>.s.png` + `.json`.

The packed page has the colour page's size and rectangles. A sprite rendered from a model, or a
flat sprite drawn per pixel (ground, overlays, faces), holds one 32-bit word per pixel: ramp and
step (its exact colour through ramps.png), normal, height, the baked-sun bit and the snow bit.
A colour-only sprite (shadows, glows, effects, weather, sky, interface, painted backdrops, the
hand-drawn flyers, anything translucent) holds its colour unchanged, so the packed page can
stand in for the colour page on its own; the side file lists those keys.
"""

import json
import re

import numpy as np
from PIL import Image

import pack
import ramps
from pack import Sprite

RAW_PREFIX = ("fx/", "weather/", "sky/", "ui/", "title/", "frame/", "backdrop/")
FLAT_PREFIX = ("terrain/", "edge/", "wild/")
# Sprites that stand still: snow may lie on them (people, animals, carts and goods move).
STILL_PREFIX = ("item/", "terrain/", "edge/", "wild/")
FACE = re.compile(r"edge/[^/]*_(se|sw)(?:/|$)")
UP_CODE, PX_CODE = 15, 30          # normal codes: 0 and +1 (n = (code - 15) / 15)


def kind(key: str, t: Sprite) -> str:
    """'model' (rendered with a data word), 'flat' (drawn per pixel, data from its key) or
    'raw' (colour only)."""
    if "/shadow/" in key or "/glow/" in key or key.startswith(RAW_PREFIX):
        return "raw"
    if t.data is not None:
        return "model"
    a = t.rgba[..., 3]
    if key.startswith("critter/") or ((a > 0) & (a < 255)).any():
        return "raw"          # hand-drawn flyers; translucent overlays (foam, flow, falls)
    if key.startswith(FLAT_PREFIX):
        return "flat"
    raise SystemExit(f"datapages: {key} has no data word and is not a flat or colour-only sprite")


def flat_data(key: str, t: Sprite) -> np.ndarray:
    """Geometry bits of a flat sprite: ground faces up at height 0, in the sun, open to the sky;
    a face under a tile edge faces +x (se) or +y (sw) and its height falls one px per px from
    its top down to 0 at its lowest pixel in each column (the engine adds the level of the
    face's foot)."""
    solid = t.rgba[..., 3] == 255
    H, W = solid.shape
    m = FACE.match(key)
    if m is None:
        geo = (UP_CODE << 11) | (UP_CODE << 16) | (1 << 30) | (1 << 31)
        return np.where(solid, np.uint32(geo), np.uint32(0)).astype(np.uint32)
    nx, ny = (PX_CODE, UP_CODE) if m[1] == "se" else (UP_CODE, PX_CODE)
    rows = np.arange(H)[:, None]
    bottom = np.where(solid.any(0), H - 1 - np.argmax(solid[::-1], 0), 0)[None, :]
    h = np.clip(bottom - rows, 0, 511).astype(np.uint32)
    geo = (np.uint32(nx) << 11) | (np.uint32(ny) << 16) | (h << 21) | np.uint32(1 << 30)
    return np.where(solid, geo, np.uint32(0)).astype(np.uint32)


def words(key: str, t: Sprite) -> np.ndarray | None:
    """The packed words of a sprite (H, W uint32), or None for a colour-only sprite."""
    k = kind(key, t)
    if k == "raw":
        return None
    pre = t.data if k == "model" else flat_data(key, t)
    cols, mat_ramp, gcodes, gid, gstep, snow_ok = ramps.arrays()
    rgba = t.rgba.astype(np.int64)
    opaque = t.rgba[..., 3] == 255
    if (t.rgba[..., 3] > 0).sum() != opaque.sum():
        raise SystemExit(f"datapages: {key} is translucent but carries data")
    if (pre[opaque] == 0).any():
        raise SystemExit(f"datapages: {key}: {int((pre[opaque] == 0).sum())} coloured pixels without data")
    out = np.zeros(pre.shape, np.uint32)
    if not opaque.any():
        return out
    code = (rgba[..., 0] << 16 | rgba[..., 1] << 8 | rgba[..., 2])[opaque]
    p = pre[opaque]
    hint = mat_ramp[np.minimum((p >> 3) & 0xFF, len(mat_ramp) - 1)] if k == "model" else np.zeros(p.size, np.int64)
    match = cols[hint] == code[:, None]
    has = match.any(1) & (hint > 0)
    ramp = np.where(has, hint, 0)
    step = np.where(has, match.argmax(1), 0)
    gi = np.clip(np.searchsorted(gcodes, code), 0, len(gcodes) - 1)
    known = gcodes[gi] == code
    if (~has & ~known).any():
        bad = sorted({"#%06x" % c for c in code[~has & ~known]})
        raise SystemExit(f"datapages: {key}: colours on no ramp {bad[:6]}")
    ramp = np.where(has, ramp, gid[gi])
    step = np.where(has, step, gstep[gi])
    snow = ((p >> 31) & 1).astype(bool) & snow_ok[ramp] & key.startswith(STILL_PREFIX)
    w = (p & np.uint32(0x7FFFF800)) | (ramp.astype(np.uint32) << 3) | step.astype(np.uint32) | \
        (snow.astype(np.uint32) << 31)
    out[opaque] = w
    return out


def rgba_word(rgba: np.ndarray) -> np.ndarray:
    v = rgba.astype(np.uint32)
    return v[..., 0] | v[..., 1] << 8 | v[..., 2] << 16 | v[..., 3] << 24


def word_rgba(w: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(w.astype("<u4")).view(np.uint8).reshape(w.shape + (4,))


def packed_page(shape, manifest: dict, trimmed: dict) -> tuple[np.ndarray, list[str]]:
    """The packed twin of one colour page: (RGBA uint8 array, sorted colour-only keys)."""
    out = np.zeros(shape[:2], np.uint32)
    raw = []
    for key in sorted(manifest):
        r = manifest[key]
        t = trimmed[key]
        w = words(key, t)
        if w is None:
            raw.append(key)
            w = rgba_word(t.rgba)
        out[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = w
    return word_rgba(out), raw


def packed_path(png):
    return png.with_name(png.stem + ".p.png")


def packed_side(png):
    return png.with_name(png.stem + ".p.json")


def write_packed(png, manifest: dict, trimmed: dict, shape, ramps_rel: str) -> None:
    """`<page>.p.png` and `<page>.p.json` beside the colour page `png`."""
    img, raw = packed_page(shape, manifest, trimmed)
    out = packed_path(png)
    Image.fromarray(img, "RGBA").save(out, optimize=True)
    doc = {"version": 1, "packed": out.name, "colour": png.name, "ramps": ramps_rel, "colour_only": raw}
    packed_side(png).write_text(json.dumps(doc, indent=1) + "\n")


def half(t: Sprite) -> Sprite:
    """A shadow sprite at half size: alpha averaged over 2 x 2 blocks, padded first so the
    anchor lands on a whole texel (drawn x2 with linear filtering it sits where it did)."""
    a = t.rgba[..., 3].astype(np.float32)
    pl, pt = t.ox % 2, t.oy % 2
    H, W = a.shape
    a = np.pad(a, ((pt, (H + pt) % 2), (pl, (W + pl) % 2)))
    h2, w2 = a.shape[0] // 2, a.shape[1] // 2
    out = np.zeros((h2, w2, 4), np.uint8)
    out[..., 3] = np.round(a.reshape(h2, 2, w2, 2).mean((1, 3))).astype(np.uint8)
    return Sprite(out, (t.ox + pl) // 2, (t.oy + pt) // 2)


def write_shadow_page(png, sprites: dict) -> tuple[int, int, int]:
    """Every `…/shadow/…` sprite at half size on one page `png` + its manifest (`"scale": 0.5`).
    Returns (width, height, sprites)."""
    keys = sorted(k for k in sprites if "/shadow/" in k)
    halves = {k: half(pack.trim(sprites[k])) for k in keys}
    atlas, manifest = pack.pack(halves)
    Image.fromarray(atlas, "RGBA").save(png, optimize=True)
    doc = {"version": 1, "image": png.name, "scale": 0.5, "sprites": manifest}
    png.with_suffix(".json").write_text(json.dumps(doc, indent=1) + "\n")
    return atlas.shape[1], atlas.shape[0], len(manifest)


# ---------------------------------------------------------------- water page

WATER_DEPTH_CAP = 40        # art px: a harbour basin's depth; small basins stay shallower by size
WATER_MIN = 8               # fewer water pixels than this in a sprite is a glint, not a body


def water_classes() -> np.ndarray:
    """True per ramp id whose class is water."""
    ramps_, _ = ramps.table()
    out = np.zeros(256, bool)
    for r in ramps_:
        out[r.id] = r.cls == "water"
    return out


def _depth(mask: np.ndarray) -> np.ndarray:
    """Distance in ground px from each water pixel to the nearest pixel that is not water (a
    screen row is two ground px deep in the 2:1 view), by a chamfer pass in both directions."""
    big = 1 << 14
    d = np.where(mask, big, 0).astype(np.int64)
    d = np.pad(d, 1)
    H, W = d.shape
    for _ in range(2):
        for y in range(1, H - 1):
            row = np.minimum(d[y], d[y - 1] + 2)
            row = np.minimum(row, np.minimum(np.roll(d[y - 1], 1), np.roll(d[y - 1], -1)) + 3)
            for x in range(1, W - 1):
                row[x] = min(row[x], row[x - 1] + 1)
            d[y] = row
        d = d[::-1, ::-1]
    return d[1:-1, 1:-1]


def water_sprite(words_: np.ndarray, ox: int, oy: int, water: np.ndarray) -> Sprite | None:
    """The water data of one sprite from its packed words, anchored like its colour sprite and
    covering only its water: R 255 on open water (the pixels on a water ramp: rims, steps and
    anything standing in the water are not), G its depth in art px below the surface (from the
    rim, capped), B the bed (1: a built basin's floor), A 255 on water (the rectangle is the
    water's bounds; the anchor puts it over the colour sprite)."""
    mask = water[(words_ >> 3) & 0xFF] & (words_ != 0)
    if mask.sum() < WATER_MIN:
        return None
    depth = np.clip(_depth(mask), 0, WATER_DEPTH_CAP)
    rgba = np.zeros(words_.shape + (4,), np.uint8)
    rgba[..., 0] = mask * 255
    rgba[..., 1] = np.where(mask, depth, 0)
    rgba[..., 2] = mask * 1
    rgba[..., 3] = mask * 255
    return Sprite(rgba, ox, oy)


def write_water_page(png, pages: list) -> tuple[int, int, int]:
    """Every item sprite holding water (a basin, a harbour, a fountain's bowl, a cistern) on one
    page `png` + manifest, from the written pages ([(colour png, manifest)]: the packed twins
    give each pixel's ramp), so the shader path marks their water and gives it depth as it does
    for water tiles. Returns (width, height, count)."""
    water = water_classes()
    out = {}
    for colour, manifest in pages:
        side = json.loads(packed_side(colour).read_text())
        raw = set(side["colour_only"])
        packed = np.asarray(Image.open(packed_path(colour)).convert("RGBA"))     # words built per sprite
        for key in sorted(manifest):
            if not key.startswith("item/") or key in raw or "/shadow/" in key or "/glow/" in key:
                continue
            r = manifest[key]
            sub = rgba_word(packed[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]])
            if (s := water_sprite(sub, r["ox"], r["oy"], water)) is not None:
                out[key] = s
    atlas, man = pack.pack(out) if out else (np.zeros((1, 1, 4), np.uint8), {})
    Image.fromarray(atlas, "RGBA").save(png, optimize=True)
    doc = {"version": 1, "image": png.name, "anchor": "as the colour sprite's",
           "channels": {"r": "water (255)", "g": "depth px", "b": "bed (1 basin)"}, "sprites": man}
    png.with_suffix(".json").write_text(json.dumps(doc, indent=1) + "\n")
    return atlas.shape[1], atlas.shape[0], len(man)
