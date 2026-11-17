"""Interface and sky art drawn at pixel scale: Laeticia's portrait, the rainbow, the title
logotype and the postcard frames. Everything here is drawn for the 64x32 density and enlarged
(or halved) by whole factors for other builds; UI anchors are the top-left pixel unless noted."""

import math

import numpy as np

from pack import Sprite
from palette import (BLOSSOM, EARTH, GLOW, INK, LEAF, PINE, PLASTER, POPPY, ROOF, SKIN, SNOW, STONE,
                     STRAW, VIOLET, WATER, _rgb)
from render import dither
from voxel import hash01


def _rgba(h, w):
    return np.zeros((h, w, 4), np.uint8)


def _fill(rgba, mask, color, alpha=255):
    rgba[mask, :3] = _rgb(color)
    rgba[mask, 3] = alpha


def _outline(rgba, color=INK, alpha=255):
    """A 1-pixel outline round everything opaque."""
    solid = rgba[..., 3] > 0
    pad = np.pad(solid, 1)
    ring = ~solid & (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:])
    _fill(rgba, ring, color, alpha)


def _scaled(rgba, k, ox=0, oy=0) -> Sprite:
    if k >= 2:
        f = k // 2
        return Sprite(rgba.repeat(f, 0).repeat(f, 1), ox * f, oy * f)
    return Sprite(rgba[::2, ::2].copy(), ox // 2, oy // 2)


# ---- portrait ----

def portrait(k: int) -> Sprite:
    """Head and shoulders, 28x28: grey bun, round glasses, rosy cheeks, moss-green cardigan
    over a cream blouse, the satchel strap across her chest. Lit from the upper left."""
    n = 28
    py, px = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    rgba = _rgba(n, n)

    def ell(cx, cy, rx, ry):
        return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1

    def shade(cx, cy, rx, ry):
        """-1 lit (upper left) .. +1 shaded (lower right) across an ellipse."""
        return ((px - cx) / rx * 0.6 + (py - cy) / ry * 0.8)

    # Shoulders and cardigan.
    body = (py > 20.0) & (np.abs(px - 13.5) < 6.5 + (py - 20.0) * 1.3)
    sh = shade(13.5, 24, 10, 6)
    _fill(rgba, body, LEAF[2])
    _fill(rgba, body & (sh < -0.35), LEAF[3])
    _fill(rgba, body & (sh > 0.45), LEAF[1])
    _fill(rgba, body & (np.abs(px - 13.5) < 1.6 + (py - 20.0) * 0.5) & (py < 25.5), PLASTER[3])
    _fill(rgba, body & (np.abs(px - 12.5) < 0.6 + (py - 20.0) * 0.5) & (py < 25.5) & (px < 13.5), PLASTER[4])
    _fill(rgba, body & (np.abs((px - 16.0) - (py - 21.0) * -1.0) < 0.75) & (py > 20.5), EARTH[2])  # strap
    # Neck.
    _fill(rgba, (np.abs(px - 13.5) < 2.0) & (py > 17.0) & (py <= 20.5), SKIN[0])
    # Face.
    face = ell(13.5, 13.0, 6.2, 7.0)
    fs = shade(13.5, 13.0, 6.2, 7.0)
    _fill(rgba, face, SKIN[1])
    _fill(rgba, face & (fs < -0.4), SKIN[2])
    _fill(rgba, face & (fs > 0.55), SKIN[0])
    # Hair: a cap down to the brow and over the ears, the bun up behind on the right.
    bun = ell(17.0, 4.2, 3.4, 3.0)
    cap = ell(13.5, 10.5, 7.4, 7.2) & ((py < 9.6 + 0.08 * (px - 13.5) ** 2) | (np.abs(px - 13.5) > 5.6))
    cap &= py < 15.5
    hair = bun | cap
    hs = shade(13.0, 7.0, 7.0, 6.0)
    strands = ((px * 0.8 + py * 0.35 + np.sin(py * 0.9) * 1.2) % 2.6) < 0.8
    _fill(rgba, hair, STONE[3])
    _fill(rgba, hair & (hs < -0.3), STONE[4])
    _fill(rgba, hair & (hs < -0.75), STONE[5])
    _fill(rgba, hair & (hs > 0.35), STONE[2])
    _fill(rgba, hair & strands & (hs > -0.6), STONE[2])
    _fill(rgba, bun & (np.abs(np.hypot(px - 17.0, py - 4.2) - 1.6) < 0.5), STONE[2])
    _fill(rgba, (np.abs((py - 2.2) - (px - 19.5) * 0.45) < 0.5) & (px > 18.5) & (px < 22.5), STRAW[2])  # pin
    # Glasses: two round rims and a bridge, eyes behind them, a glint on each lens.
    for ex in (10.5, 16.5):
        d = np.hypot(px - ex, py - 12.8)
        _fill(rgba, (d > 1.6) & (d < 2.5), EARTH[1])
        _fill(rgba, (np.abs(px - ex) < 0.6) & (np.abs(py - 13.0) < 0.6), INK)
        _fill(rgba, (np.abs(px - ex - 1.0) < 0.5) & (np.abs(py - 12.0) < 0.5), SNOW[2])
    _fill(rgba, (np.abs(py - 12.5) < 0.5) & (px > 12.8) & (px < 14.2), EARTH[1])
    # Brows (grey), nose, cheeks and a small smile.
    for ex in (10.6, 16.4):
        _fill(rgba, (np.abs(py - 9.5) < 0.5) & (np.abs(px - ex) < 1.6), STONE[2])
    _fill(rgba, (np.abs(px - 14.0) < 0.5) & (py > 14.0) & (py < 15.5), SKIN[0])
    for cx in (9.4, 17.6):
        _fill(rgba, (np.abs(px - cx) < 1.0) & (np.abs(py - 16.5) < 0.5), BLOSSOM[3])
    smile = ((np.abs(py - 17.5) < 0.5) & (np.abs(px - 13.5) < 1.1)) | \
        ((np.abs(py - 16.5) < 0.5) & (np.abs(np.abs(px - 13.5) - 1.5) < 0.5))
    _fill(rgba, smile, ROOF[2])
    _outline(rgba)
    return _scaled(rgba, k)


# ---- sky ----

def rainbow(k: int) -> Sprite:
    """A soft pastel arc, mostly transparent, its ends fading into the haze; anchored at the
    bottom centre of the arc."""
    w, h = 480, 160
    py, px = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    rgba = _rgba(h, w)
    cx, cy = w / 2, h + 70.0
    r = np.hypot((px - cx) / 1.0, (py - cy) * 1.35)
    outer, band = 228.0, 7.0
    colors = (BLOSSOM[3], ROOF[4], STRAW[3], LEAF[6], WATER[4], VIOLET[3])
    fade = np.clip((cy - py - 75) / 75, 0, 1) ** 0.8    # ends fade out towards the horizon
    for i, c in enumerate(colors):
        ring = (r <= outer - i * band) & (r > outer - (i + 1) * band)
        a = (110 * fade * np.where((r > outer - 0.6 * band) & (i == 0), 0.6, 1.0)).astype(np.uint8)
        # A restrained ordered dither on the faint ends keeps the alpha in a few clean steps.
        a = np.where(dither(a / 40.0, px.astype(np.int64), py.astype(np.int64)) >= 1, a, 0)
        sel = ring & (a > 0)
        rgba[sel, :3] = _rgb(c)
        rgba[sel, 3] = a[sel]
    return _scaled(rgba, k, w // 2, h - 1)


# ---- title ----

# Hand-lettered glyphs: '#' is stroke, rows top to bottom, all sitting on one baseline (the last
# row). Capitals are 11 rows tall, lowercase 7, with ascenders where they belong.
GLYPHS = {
    "L": ("##.....", "##.....", "##.....", "##.....", "##.....", "##.....", "##.....", "##.....",
          "##.....", "##....#", ".######"),
    "a": (".####.", "....##", ".#####", "##..##", "##..##", "##.###", ".##.##"),
    "e": (".####.", "##..##", "##..##", "######", "##....", "##...#", ".####."),
    "t": (".##..", ".##..", ".##..", "#####", ".##..", ".##..", ".##..", ".##..", ".##.#", "..##."),
    "i": ("##", "..", "##", "##", "##", "##", "##", "##", "##"),
    "c": (".####", "##..#", "##...", "##...", "##...", "##..#", ".####"),
    "'": ("##", "##", ".#", "#.", "..", "..", "..", "..", "..", "..", ".."),
    "s": (".####", "##...", "##...", ".###.", "...##", "...##", "####."),
    "C": ("..#####.", ".##...##", "##.....#", "##......", "##......", "##......", "##......",
          "##......", "##.....#", ".##...##", "..#####."),
    "o": (".####.", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."),
    "r": ("##.###", "####..", "##....", "##....", "##....", "##....", "##...."),
    "n": ("##.##.", "###.##", "##..##", "##..##", "##..##", "##..##", "##..##"),
}
TITLE_SCALE = 3


def _word(text, bounce_seed):
    """A word's stroke mask at the glyph scale, each letter bobbing a pixel for a hand feel."""
    cells = []
    for i, ch in enumerate(text):
        g = np.array([[c == "#" for c in row] for row in GLYPHS[ch]])
        cells.append((g, int(round(math.sin(i * 1.7 + bounce_seed) * 0.6))))
    w = sum(g.shape[1] for g, _b in cells) + len(cells) - 1
    mask = np.zeros((13, w), bool)
    x = 0
    for g, bob in cells:
        top = 12 - g.shape[0] + bob
        mask[top:top + g.shape[0], x:x + g.shape[1]] |= g
        x += g.shape[1] + 1
    return mask


def _sprig(rgba, x0, y0):
    """A blossom sprig: a curving twig, leaves and five-petalled flowers."""
    h, w = rgba.shape[:2]
    py, px = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    pts = [(x0 + t * 70, y0 + 18 - 22 * math.sin(t * 2.2) * 0.6 + t * 6) for t in np.linspace(0, 1, 120)]
    for x, y in pts:
        _fill(rgba, (np.abs(px - x) < 1.0) & (np.abs(py - y) < 1.0), EARTH[1])
    for t, side in ((0.25, 1), (0.5, -1), (0.75, 1)):
        x, y = pts[int(t * 119)]
        lx, ly = x + 4, y + side * 5
        leaf = ((px - lx) * 0.8 + (py - ly) * 0.6) ** 2 / 20 + ((px - lx) * -0.6 + (py - ly) * 0.8) ** 2 / 5 <= 1
        _fill(rgba, leaf, LEAF[3])
        _fill(rgba, leaf & (py < ly), LEAF[4])
    for t, r in ((0.12, 6.0), (0.4, 7.0), (0.66, 6.0), (0.95, 5.0)):
        x, y = pts[int(t * 119)]
        y -= 3
        ang = np.arctan2(py - y, px - x)
        rho = np.hypot(px - x, py - y)
        petals = rho <= r * (0.62 + 0.38 * np.abs(np.cos(ang * 2.5)))
        _fill(rgba, petals, BLOSSOM[3])
        _fill(rgba, petals & (rho < r * 0.6) & ((px - x) + (py - y) < 0), BLOSSOM[4])
        _fill(rgba, petals & (rho > r * 0.8), BLOSSOM[2])
        _fill(rgba, rho < 1.6, STRAW[2])


def title_logo(k: int) -> Sprite:
    """'Laeticia's Corner' hand-lettered in cream with a moss-green outline and a blossom
    sprig, 320x96."""
    W, H = 320, 96
    rgba = _rgba(H, W)
    s = TITLE_SCALE
    words = (("Laeticia's", 8, 4, 0.3), ("Corner", 118, 46, 1.9))
    fill = np.zeros((H, W), bool)
    lower = np.zeros((H, W), bool)
    for text, x, y, seed in words:
        m = _word(text, seed).repeat(s, 0).repeat(s, 1)
        h, w = m.shape
        fill[y:y + h, x:x + w] |= m
        # The lower third of each stroke row band is shaded, so the letters feel inked.
        rows = np.arange(h)[:, None] % (s * 13) >= s * 9
        lower[y:y + h, x:x + w] |= m & rows
    _sprig(rgba, 12, 52)
    sprig = rgba[..., 3] > 0
    pad = lambda a, n: np.pad(a, n)
    grow = lambda a, n: np.any([pad(a, n)[n + dy:n + dy + H, n + dx:n + dx + W]
                                for dy in range(-n, n + 1) for dx in range(-n, n + 1)
                                if dx * dx + dy * dy <= n * n + 1], axis=0)
    outer = grow(fill, 3)
    moss = grow(fill, 2)
    shadow = np.zeros_like(fill)
    shadow[3:, 2:] = outer[:-3, :-2]
    _fill(rgba, shadow & ~outer & ~sprig, INK, 110)
    _fill(rgba, outer & ~moss, PINE[0])
    _fill(rgba, moss & ~fill, LEAF[2])
    _fill(rgba, moss & ~fill & np.roll(moss & ~fill, 1, 0) & ~np.roll(moss, 2, 0), LEAF[3])
    _fill(rgba, fill, PLASTER[4])
    _fill(rgba, lower, PLASTER[3])
    # A highlight pixel row along the top of each stroke.
    top = fill & ~np.roll(fill, 1, 0)
    _fill(rgba, top, SNOW[2])
    return _scaled(rgba, k)


# ---- postcard frames ----

BAND = 16           # border thickness in pixels; corners are 48x48, edges tile every 32
CORNER, EDGE = 48, 32


def _frame_band(style, w, h, sides, x_off, y_off):
    """The border band for a piece: `sides` lists which outer edges it runs along ('t', 'b',
    'l', 'r'); offsets place the piece in a notional frame so textures continue (16-periodic)."""
    rgba = _rgba(h, w)
    py, px = np.mgrid[0:h, 0:w]
    gx, gy = px + x_off, py + y_off
    dist = np.full((h, w), 99.0)
    for side in sides:
        d = {"t": py, "b": h - 1 - py, "l": px, "r": w - 1 - px}[side]
        dist = np.minimum(dist, d)
    inside = dist < BAND
    # Speckle repeats every 32 px along the band (the edge period); a seam where a corner meets
    # an edge only shuffles sparse specks, so it never shows.
    n = hash01(gx % 32, gy % 32, {"pressed_flowers": 1, "watercolour": 2, "starry": 3}[style])
    if style == "pressed_flowers":
        _fill(rgba, inside, PLASTER[3])
        _fill(rgba, inside & (n < 0.12), PLASTER[2])
        _fill(rgba, inside & (n > 0.93), PLASTER[4])
        _fill(rgba, inside & (dist < 1), PLASTER[1])
        _fill(rgba, inside & (dist >= BAND - 1), PLASTER[1])
        _fill(rgba, inside & (np.abs(dist - 3) < 0.5) & ((gx + gy) % 4 < 2), PLASTER[2])  # stitched line
    elif style == "watercolour":
        wave = 1.6 * np.sin((gx + gy) * 2 * math.pi / 32) + 0.8 * np.sin((gx - gy) * 2 * math.pi / 16 + 1)
        wash = dist < BAND - 3 + wave
        ragged = dist < 3 + (n < 0.3)
        _fill(rgba, inside & wash, WATER[4])
        _fill(rgba, inside & wash & (np.sin((gx * 0.7 + gy * 0.4) * 2 * math.pi / 32) > 0.4), LEAF[5])
        _fill(rgba, inside & wash & (dist > BAND - 7 + wave), WATER[5])
        _fill(rgba, inside & ragged, PLASTER[4])
        rgba[..., 3] = np.where(inside & (wash | ragged), np.where(ragged, 255, 215), 0)
    else:
        _fill(rgba, inside, WATER[0])
        _fill(rgba, inside & (dist > BAND - 3), VIOLET[0])
        _fill(rgba, inside & (dist < 1), STRAW[2])
        _fill(rgba, inside & (np.abs(dist - BAND + 1) < 0.5), STRAW[1])
        star = inside & (dist > 2) & (dist < BAND - 3) & (n > 0.975)
        _fill(rgba, star, GLOW[1])
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            _fill(rgba, np.roll(np.roll(star & (n > 0.985), dy, 0), dx, 1) & inside, STRAW[3])
    return rgba


def _pressed_flower(rgba, cx, cy, kind):
    h, w = rgba.shape[:2]
    py, px = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    rho, ang = np.hypot(px - cx, py - cy), np.arctan2(py - cy, px - cx)
    if kind == "daisy":
        petals = (rho < 6.5) & (np.cos(ang * 8) > -0.1) & (rho > 1.5)
        _fill(rgba, petals, PLASTER[4])
        _fill(rgba, petals & (rho > 5), PLASTER[2])
        _fill(rgba, rho <= 2.0, STRAW[2])
        stem = (np.abs(px - cx - (py - cy) * 0.3) < 0.7) & (py > cy + 6) & (py < cy + 16)
        _fill(rgba, stem, LEAF[3])
    elif kind == "poppy":
        petals = rho < 6.0 * (0.8 + 0.2 * np.cos(ang * 4))
        _fill(rgba, petals, POPPY[1])
        _fill(rgba, petals & (np.cos(ang * 4) < -0.6), POPPY[0])
        _fill(rgba, rho < 1.8, INK)
        stem = (np.abs(py - cy - (px - cx) * 0.4) < 0.7) & (px > cx + 5) & (px < cx + 15)
        _fill(rgba, stem, LEAF[3])
    else:   # a lavender sprig
        for j in range(7):
            fx, fy = cx + j * 1.6, cy - j * 2.2
            _fill(rgba, np.hypot(px - fx, py - fy) < 1.4, VIOLET[2 if j % 2 else 3])
        stem = (np.abs((px - cx) * 2.2 + (py - cy) * 1.6) < 1.6) & (py > cy) & (py < cy + 12)
        _fill(rgba, stem, LEAF[3])


def _moon(rgba, cx, cy):
    h, w = rgba.shape[:2]
    py, px = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
    crescent = (np.hypot(px - cx, py - cy) < 7.5) & (np.hypot(px - cx - 3.5, py - cy + 2.0) >= 6.5)
    _fill(rgba, crescent, GLOW[2])
    _fill(rgba, crescent & (px - cx < -3.5), GLOW[1])


def frame_piece(style: str, piece: str, k: int) -> Sprite:
    """One nine-slice piece. Corners are 48x48 (the band runs along both outer edges, with the
    style's ornament inside); t/b are 32x16 and l/r 16x32 and tile; the centre is not drawn.
    `plate` is a 128x24 caption backing."""
    if piece == "plate":
        rgba = _frame_band(style, 128, 24, ("t", "b", "l", "r"), 0, 0)
        fill = {"pressed_flowers": PLASTER[4], "watercolour": WATER[5], "starry": WATER[1]}[style]
        inner = rgba[..., 3] == 0
        _fill(rgba, inner, fill, 235)
        return _scaled(rgba, k)
    sides = {"tl": "tl", "tr": "tr", "bl": "bl", "br": "br", "t": "t", "b": "b", "l": "l", "r": "r"}[piece]
    w = CORNER if len(piece) == 2 else (EDGE if piece in ("t", "b") else BAND)
    h = CORNER if len(piece) == 2 else (EDGE if piece in ("l", "r") else BAND)
    x_off = 0 if "l" in piece else (CORNER if piece in ("t", "b") else 0)
    y_off = 0 if "t" in piece else (CORNER if piece in ("l", "r") else 0)
    rgba = _frame_band(style, w, h, tuple(sides), x_off, y_off)
    if len(piece) == 2:
        # Ornaments sit in the corner's inner square, mirrored so all four point inwards.
        ox = 14 if "l" in piece else w - 14
        oy = 14 if "t" in piece else h - 14
        if style == "pressed_flowers":
            kinds = {"tl": "daisy", "tr": "poppy", "bl": "lavender", "br": "daisy"}[piece]
            _pressed_flower(rgba, ox, oy, kinds)
            _pressed_flower(rgba, ox + (9 if "l" in piece else -9), oy + (-6 if "t" in piece else 6),
                            "lavender" if kinds != "lavender" else "poppy")
        elif style == "watercolour":
            py, px = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5
            bloom = np.hypot(px - ox + (4 if "l" in piece else -4), py - oy + (4 if "t" in piece else -4)) < 12
            add = bloom & (rgba[..., 3] == 0)
            _fill(rgba, add, WATER[4], 160)
            _fill(rgba, add & (hash01(px.astype(np.int64), py.astype(np.int64), 5) < 0.3), LEAF[5], 160)
        elif piece == "tr":
            _moon(rgba, ox + 2, oy - 2)
    return _scaled(rgba, k)


def build(keys: list[str], cat: dict, k: int) -> dict[str, Sprite]:
    out = {}
    for key in keys:
        if key == "ui/portrait/laeticia":
            out[key] = portrait(k)
        elif key == "sky/rainbow":
            out[key] = rainbow(k)
        elif key == "title/logo":
            out[key] = title_logo(k)
        elif key.startswith("frame/"):
            _f, style, piece = key.split("/")
            out[key] = frame_piece(style, piece, k)
        else:
            raise KeyError(key)
    return out
