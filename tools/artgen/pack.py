"""Trim sprites, shelf-pack them into one atlas and write the PNG + manifest."""

import hashlib
import json
from dataclasses import dataclass

import numpy as np
from PIL import Image

PAD = 1  # transparent gutter around every rect so linear filtering never bleeds


@dataclass
class Sprite:
    """An RGBA image (H, W, 4 uint8) and the pixel (ox, oy) that sits on the anchor; `data`,
    for a sprite rendered from a model, its data word per pixel (H, W uint32, render.data_word),
    which datapages.py turns into the packed page."""
    rgba: np.ndarray
    ox: int
    oy: int
    data: np.ndarray | None = None
    glow: np.ndarray | None = None      # an actor's emissive layer, split off by the set build


def trim(s: Sprite) -> Sprite:
    alpha = s.rgba[:, :, 3]
    ys, xs = np.nonzero(alpha)
    if len(xs) == 0:  # keep empty frames addressable as a 1x1 transparent pixel at the anchor
        return Sprite(np.zeros((1, 1, 4), np.uint8), 0, 0, None if s.data is None else np.zeros((1, 1), np.uint32))
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    data = None if s.data is None else s.data[y0:y1, x0:x1].copy()
    return Sprite(s.rgba[y0:y1, x0:x1].copy(), s.ox - int(x0), s.oy - int(y0), data)


def signature(t: Sprite) -> bytes:
    """Equal for sprites that may share one rectangle: same pixels, anchor and data."""
    data = b"" if t.data is None else t.data.tobytes()
    return hashlib.sha1(t.rgba.tobytes() + repr((t.rgba.shape, t.ox, t.oy)).encode() + data).digest()


def pack(sprites: dict[str, Sprite], max_side: int = 4096):
    """Shelf packing, tallest first; returns (atlas RGBA array, {key: (x, y, w, h, ox, oy)}).
    Identical sprites (same pixels and anchor) share one rectangle."""
    trimmed = {k: trim(s) for k, s in sprites.items()}
    same, first = {}, {}
    for k in sorted(trimmed):
        t = trimmed[k]
        sig = signature(t)
        if sig in first:
            same[k] = first[sig]
        else:
            first[sig] = k
    unique = [k for k in trimmed if k not in same]
    order = sorted(unique, key=lambda k: (-trimmed[k].rgba.shape[0], -trimmed[k].rgba.shape[1], k))
    area = sum((trimmed[k].rgba.shape[0] + PAD) * (trimmed[k].rgba.shape[1] + PAD) for k in unique)
    width = 256
    while width * width < area * 1.15 and width < max_side:
        width *= 2
    while True:
        rects, x, y, shelf_h = {}, PAD, PAD, 0
        for k in order:
            h, w = trimmed[k].rgba.shape[:2]
            if x + w + PAD > width:
                x, y, shelf_h = PAD, y + shelf_h + PAD, 0
            rects[k] = (x, y)
            x += w + PAD
            shelf_h = max(shelf_h, h)
        height = y + shelf_h + PAD
        if height <= width or width >= max_side:
            break
        width *= 2
    for k, src in same.items():
        rects[k] = rects[src]
    side_h = 1
    while side_h < height:
        side_h *= 2
    if width > max_side or side_h > max_side:
        raise RuntimeError(f"atlas does not fit in {max_side}px")
    atlas = np.zeros((side_h, width, 4), np.uint8)
    manifest = {}
    for k in sorted(rects):
        t = trimmed[k]
        x, y = rects[k]
        h, w = t.rgba.shape[:2]
        atlas[y:y + h, x:x + w] = t.rgba
        manifest[k] = {"x": x, "y": y, "w": w, "h": h, "ox": t.ox, "oy": t.oy}
    return atlas, manifest


def write_atlas(sprites: dict[str, Sprite], png_path, json_path) -> tuple[int, int]:
    """The colour page and manifest, its packed twin, the half-size shadow page, the water page
    and the ramp table (`atlas/ramps.*` beside the page) for the shader path (datapages.py)."""
    import datapages
    import ramps
    atlas, manifest = pack(sprites)
    Image.fromarray(atlas, "RGBA").save(png_path, optimize=True)
    doc = {"version": 1, "image": png_path.name, "sprites": manifest}
    json_path.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n")
    ramps.write(png_path.parent / "atlas")
    trimmed = {k: trim(s) for k, s in sprites.items()}
    datapages.write_packed(png_path, manifest, trimmed, atlas.shape, "atlas/ramps.json")
    datapages.write_shadow_page(png_path.with_name(png_path.stem + ".s.png"), sprites)
    datapages.write_water_page(png_path.with_name(png_path.stem + ".w.png"), trimmed)
    return atlas.shape[1], atlas.shape[0]
