"""Trim sprites, shelf-pack them into one atlas and write the PNG + manifest."""

import json
from dataclasses import dataclass

import numpy as np
from PIL import Image

PAD = 1  # transparent gutter around every rect so linear filtering never bleeds


@dataclass
class Sprite:
    """An RGBA image (H, W, 4 uint8) and the pixel (ox, oy) that sits on the anchor."""
    rgba: np.ndarray
    ox: int
    oy: int


def trim(s: Sprite) -> Sprite:
    alpha = s.rgba[:, :, 3]
    ys, xs = np.nonzero(alpha)
    if len(xs) == 0:  # keep empty frames addressable as a 1x1 transparent pixel at the anchor
        return Sprite(np.zeros((1, 1, 4), np.uint8), 0, 0)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return Sprite(s.rgba[y0:y1, x0:x1].copy(), s.ox - int(x0), s.oy - int(y0))


def pack(sprites: dict[str, Sprite], max_side: int = 4096):
    """Shelf packing, tallest first; returns (atlas RGBA array, {key: (x, y, w, h, ox, oy)})."""
    trimmed = {k: trim(s) for k, s in sprites.items()}
    order = sorted(trimmed, key=lambda k: (-trimmed[k].rgba.shape[0], -trimmed[k].rgba.shape[1], k))
    area = sum((t.rgba.shape[0] + PAD) * (t.rgba.shape[1] + PAD) for t in trimmed.values())
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
    atlas, manifest = pack(sprites)
    Image.fromarray(atlas, "RGBA").save(png_path, optimize=True)
    doc = {"version": 1, "image": png_path.name, "sprites": manifest}
    json_path.write_text(json.dumps(doc, indent=1, sort_keys=False) + "\n")
    return atlas.shape[1], atlas.shape[0]
