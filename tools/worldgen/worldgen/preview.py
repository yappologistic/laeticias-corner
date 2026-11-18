"""Previews from data files only (catalogs, atlas pages, geometry): no engine, no artgen code.

- `map_image`: north-up, N px per tile, terrain colours shaded by level, items as dots, graph
  edges as lines, district outlines faint.
- `overview_image`: the styled north-up world map (world-tech §3.6, §4.7).
- `iso_image`: an isometric close-up of a plan rect, drawn as the engine draws: ground by diagonal
  rows with stacked faces, shadows composited once, items and raised occluder tiles in the
  engine's rectangle depth order, placeholders for missing art. Rendered in horizontal strips at
  1x and reduced per strip, so memory stays bounded whatever the rect.
"""

from __future__ import annotations

import heapq
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from plan import world_plan as P

from . import rng
from .catalog import Atlas, Catalog
from .compose import NONE16, World, live_items
from .coords import COLS, ROWS, to_grid

FONT_DIR = "assets/fonts"


def font(root: Path, size: int, bold: bool = False):
    name = "Nunito-ExtraBold.ttf" if bold else "Nunito-SemiBold.ttf"
    try:
        return ImageFont.truetype(str(Path(root) / FONT_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


def tile_hash(x: int, y: int, salt: int = 0) -> int:
    """The engine's tileHash (src/core/rng.hpp), for the same terrain variant choice."""
    m = 0xFFFFFFFF
    h = ((x * 0x8DA6B343) & m) ^ ((y * 0xD8163841) & m) ^ ((salt * 0xCB1AB31F) & m)
    h ^= h >> 13
    h = (h * 0x5BD1E995) & m
    h ^= h >> 15
    return h


# --- colours ---------------------------------------------------------------------------------

def terrain_colours(world: World, cat: Catalog, atlas: Atlas) -> np.ndarray:
    out = np.zeros((len(world.terrains) + 1, 3), dtype=np.float64)
    for i, tid in enumerate(world.terrains):
        col = None
        t = cat.terrain.get(tid)
        if t is not None and t.colour:
            col = t.colour
        for key in (f"terrain/{tid}/v0", f"terrain/{tid}/m15/f0"):
            if col is None:
                col = atlas.mean_colour(key)
        if col is None:
            h = rng.hash64(tid)
            col = (80 + h % 120, 80 + (h >> 8) % 120, 80 + (h >> 16) % 120)
        out[i] = col
    out[-1] = (24, 26, 34)
    return out


def hillshade(level: np.ndarray) -> np.ndarray:
    lv = level.astype(np.float64)
    nw = np.pad(lv, 1, mode="edge")[:-2, :-2]
    return np.clip(1.0 + 0.07 * (nw - lv), 0.75, 1.2)


def _levels(world: World, sl) -> np.ndarray:
    return (world.L[sl] & 0x0F).astype(np.int16)


def map_image(world: World, cat: Catalog, atlas: Atlas, rect=None, px: int = 1,
              graphs=(), items: bool = True, districts: bool = True) -> Image.Image:
    c0, r0, c1, r1 = rect or (0, 0, COLS - 1, ROWS - 1)
    sl = (slice(r0, r1 + 1), slice(c0, c1 + 1))
    cols = terrain_colours(world, cat, atlas)
    T = world.T[sl].astype(np.int64)
    T = np.where(T == NONE16, len(world.terrains), T)
    lv = _levels(world, sl)
    rgb = cols[T] * hillshade(lv)[..., None]
    rgb *= (1.0 + 0.025 * lv)[..., None]
    water = np.isin(T, [i for i, t in enumerate(world.terrains) if cat.is_water(t)])
    depth = ((world.L[sl] >> 4) & 3).astype(np.float64)
    rgb[water] *= (1.0 - 0.09 * depth[water])[..., None]
    imp = (world.L[sl] & 0x40) > 0
    rgb[imp] *= 0.88
    if districts:
        D = world.D[sl].astype(np.int64)
        edge = np.zeros(D.shape, dtype=bool)
        edge[:, 1:] |= D[:, 1:] != D[:, :-1]
        edge[1:, :] |= D[1:, :] != D[:-1, :]
        rgb[edge] = rgb[edge] * 0.7 + np.array([255, 240, 200]) * 0.3
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    if px > 1:
        img = img.resize((img.width * px, img.height * px), Image.NEAREST)
    d = ImageDraw.Draw(img)
    if items:
        for _, it in live_items(world):
            if not (c0 <= it.c <= c1 and r0 <= it.r <= r1):
                continue
            idef = cat.items.get(it.id)
            plant = idef is not None and idef.footprint == (1, 1) and idef.layout == "variant"
            col = (34, 74, 34) if plant else (150, 40, 40)
            x0, y0 = (it.c - c0) * px, (it.r - r0) * px
            if px == 1:
                d.point((x0, y0), fill=col)
            else:
                d.rectangle((x0, y0, x0 + it.pw * px - 1, y0 + it.ph * px - 1),
                            fill=col if not plant else None, outline=col)
    for g in graphs:
        for e in g.edges:
            a, b = g.node(e.a), g.node(e.b)
            if a is None or b is None:
                continue
            pts = [a.at, *e.via, b.at]
            xy = [((COLS - 1 - ty - c0 + 0.5) * px, (tx - r0 + 0.5) * px) for tx, ty in pts]
            d.line(xy, fill=(250, 220, 90), width=max(1, px // 2))
        for ln in g.lanes:
            xy = [((COLS - 1 - ty - c0 + 0.5) * px, (tx - r0 + 0.5) * px) for tx, ty in ln.points]
            d.line(xy, fill=(230, 240, 255), width=1)
    return img


# --- overview ----------------------------------------------------------------------------------

PAPER = {"rome": (238, 224, 192), "athens": (241, 233, 208), "parsa": (236, 219, 182),
         "timeless": (228, 232, 206), "none": (236, 228, 204)}
SEPIA = (92, 66, 44)


def overview_image(world: World, cat: Catalog, atlas: Atlas, root: Path, px: int = 2,
                   graphs=()) -> Image.Image:
    """The styled north-up map at `px` pixels per tile."""
    cols = terrain_colours(world, cat, atlas)
    T = world.T.astype(np.int64)
    land = np.ones(T.shape, dtype=bool)
    water_ids = [i for i, t in enumerate(world.terrains) if cat.is_water(t)]
    sea_ids = [i for i, t in enumerate(world.terrains) if t in ("world.sea", "world.shallows")]
    sea = np.isin(T, sea_ids)
    river = np.isin(T, water_ids) & ~sea
    land = ~sea
    lv = (world.L & 0x0F).astype(np.int16)
    # Paper per time band, by district region.
    paper = np.zeros(T.shape + (3,))
    reg_time = {}
    for rid, v in P.REGIONS.items():
        reg_time[rid] = v[2]
    D = world.D.astype(np.int64)
    dist_time = np.array([PAPER.get(reg_time.get(d.split("/")[0], "none"), PAPER["none"])
                          for d in world.districts] + [PAPER["none"]], dtype=np.float64)
    paper = dist_time[np.where(D == NONE16, len(world.districts), D)]
    tcol = cols[np.where(T == NONE16, len(world.terrains), T)]
    rgb = paper * 0.72 + tcol * 0.28
    shade = np.clip(1.0 + 0.06 * (np.pad(lv, 1, mode="edge")[:-2, :-2] - lv), 0.8, 1.2)
    rgb *= shade[..., None]
    rgb *= (1.0 - 0.012 * lv)[..., None]
    depth = ((world.L >> 4) & 3).astype(np.float64)
    seacol = np.array([176, 196, 200], dtype=np.float64)
    rgb[sea] = seacol * (1.0 - 0.05 * depth[sea])[..., None]
    rgb[river] = (112, 150, 176)
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    img = img.resize((COLS * px, ROWS * px), Image.NEAREST)
    d = ImageDraw.Draw(img)
    # Coast lines in sepia: land pixels touching sea.
    coast = land & (np.pad(sea, 1)[1:-1, 2:] | np.pad(sea, 1)[1:-1, :-2] |
                    np.pad(sea, 1)[2:, 1:-1] | np.pad(sea, 1)[:-2, 1:-1])
    cm = np.kron(coast, np.ones((px, px), dtype=bool))
    a = np.asarray(img).copy()
    a[cm] = (a[cm] * 0.25 + np.array(SEPIA) * 0.75).astype(np.uint8)
    img = Image.fromarray(a, "RGB")
    d = ImageDraw.Draw(img)
    # Waves in the open sea.
    for r in range(6, ROWS, 14):
        for c in range((r * 7) % 18, COLS, 18):
            h = rng.hash64("wave", c, r)
            cc, rr = c + h % 7, r + (h >> 8) % 5
            if 0 <= rr < ROWS and 0 <= cc < COLS - 3 and sea[rr, cc] and depth[rr, cc] >= 3 \
                    and sea[rr, cc + 3]:
                x, y = cc * px, rr * px
                d.arc((x, y, x + 3 * px, y + 2 * px), 200, 340, fill=(128, 156, 168))
    # Mountains as small shaded triangles on a jittered grid.
    for r in range(4, ROWS, 7):
        for c in range(4, COLS, 8):
            h = rng.hash64("peak", c, r)
            cc, rr = c + h % 5 - 2, r + (h >> 8) % 5 - 2
            if not (0 <= rr < ROWS and 0 <= cc < COLS) or lv[rr, cc] < 8 or not land[rr, cc]:
                continue
            s = (2.2 + 0.35 * (lv[rr, cc] - 8)) * px
            x, y = cc * px, rr * px
            top = (x, y - s)
            d.polygon([top, (x - s * 0.9, y + s * 0.5), (x, y + s * 0.5)], fill=(214, 200, 170))
            d.polygon([top, (x, y + s * 0.5), (x + s * 0.9, y + s * 0.5)], fill=(150, 128, 98))
            d.line([(x - s * 0.9, y + s * 0.5), top, (x + s * 0.9, y + s * 0.5)], fill=SEPIA)
            if lv[rr, cc] >= 12:
                d.polygon([top, (x - s * 0.3, y - s * 0.55), (x + s * 0.3, y - s * 0.55)],
                          fill=(246, 246, 240))
    # The seams of time: a faint hatched band (the Ionian mist, the Ionian-coast haze).
    for rid in ("seam_ionian", "seam_ionia"):
        c0, r0, c1, r1 = P.REGIONS[rid][3]
        for k in range(r0, r1, 6):
            d.line([(c0 * px, k * px), (c1 * px, (k + 4) * px)], fill=(206, 196, 170), width=1)
    # Roads as built (every layer's road and track edges), lanes dotted, stations as squares.
    for g in graphs:
        city = P.REGIONS.get(g.layer, ("",))[0] in ("city", "home")
        for e in g.edges:
            a_, b_ = g.node(e.a), g.node(e.b)
            if city or not (a_ and b_) or e.kind not in ("road", "track", "bridge", "ford"):
                continue
            pts = [a_.at, *e.via, b_.at]
            xy = [((COLS - 1 - ty) * px + px / 2, tx * px + px / 2) for tx, ty in pts]
            d.line(xy, fill=(96, 58, 34) if e.kind != "track" else (138, 104, 72),
                   width=max(1, px if e.kind != "track" else px // 2))
        for ln in g.lanes:
            xy = [((COLS - 1 - ty) * px + px / 2, tx * px + px / 2) for tx, ty in ln.points]
            _dotted(d, xy, (70, 96, 120), px, 2 * px)
        for n in g.nodes:
            if n.kind == "station":
                x, y = (COLS - 1 - n.at[1]) * px, n.at[0] * px
                d.rectangle((x - px, y - px, x + px, y + px), fill=(150, 46, 36), outline=SEPIA)
    # Lands, ranges and rivers named in small capitals.
    f_land = font(root, 11 * px // 2, bold=True)
    f_river = font(root, 8 * px // 2)
    for name, (c, r) in P.LAND_LABELS:
        _text(d, (c * px, r * px), name, f_land, fill=(132, 104, 76))
    for name, (c, r) in P.RIVER_LABELS:
        _text(d, (c * px, r * px), name, f_river, fill=(70, 104, 132), halo=False)
    # Region frames for the three cities and the home, labels and markers.
    f_big = font(root, 15 * px // 2, bold=True)
    f_mid = font(root, 10 * px // 2, bold=True)
    f_small = font(root, 8 * px // 2)
    f_sea = font(root, 13 * px // 2)
    for rid in ("rome", "athens", "parsa", "corner"):
        c0, r0, c1, r1 = P.REGIONS[rid][3]
        _dashed_rect(d, (c0 * px, r0 * px, (c1 + 1) * px, (r1 + 1) * px), SEPIA)
    for rid, (c, r), icon in P.MARKERS:
        x, y = c * px, r * px
        label = P.LABELS.get(rid, rid)
        if icon == "town":
            d.ellipse((x - 2 * px, y - 2 * px, x + 2 * px, y + 2 * px), fill=(120, 40, 30),
                      outline=SEPIA)
            _text(d, (x + 3 * px, y - 5 * px), label, f_small)
        else:
            d.ellipse((x - 4 * px, y - 4 * px, x + 4 * px, y + 4 * px), fill=(150, 46, 36),
                      outline=SEPIA, width=px)
            _text(d, (x + 6 * px, y - 9 * px), label, f_big)
            band = P.TIME_BANDS.get(rid)
            if band:
                _text(d, (x + 6 * px, y + 3 * px), band, f_mid)
    for name, (c, r) in P.SEA_LABELS:
        _text(d, (c * px, r * px), name, f_sea, fill=(84, 110, 128), halo=False)
    return img


def _text(d, xy, s, f, fill=SEPIA, halo=True):
    if halo:
        x, y = xy
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            d.text((x + dx, y + dy), s, font=f, fill=(244, 236, 214))
    d.text(xy, s, font=f, fill=fill)


def _dotted(d, xy, fill, dot, gap):
    for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        n = int(length // (dot + gap))
        for i in range(n + 1):
            t = i * (dot + gap) / max(length, 1e-9)
            if t > 1:
                break
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            d.ellipse((x - dot / 2, y - dot / 2, x + dot / 2, y + dot / 2), fill=fill)


def _dashed_rect(d, box, fill, dash=8, gap=6):
    x0, y0, x1, y1 = box
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)),
                   ((x0, y1), (x0, y0))):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        n = int(length // (dash + gap)) + 1
        for i in range(n):
            t0 = i * (dash + gap) / length
            t1 = min(t0 + dash / length, 1)
            if t0 >= 1:
                break
            d.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                    (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=fill, width=2)


# --- isometric close-ups -----------------------------------------------------------------------

PLACEHOLDER_COLOURS = {
    "landmark": (196, 112, 86), "building": (214, 176, 112), "stair": (190, 170, 140),
    "water": (120, 150, 170), "wall": (168, 160, 150), "prop": (176, 172, 166),
    "plant": (110, 156, 92), "unknown": (220, 60, 200)}

FACE_COLOURS = {"water": (150, 196, 214), "world.coast": (168, 146, 112), "world.rock": (132, 124, 116),
                "world.earth": (140, 108, 76), "world.snow": (226, 230, 238)}


class IsoRenderer:
    """Draws plan rects of a composed world isometrically, as the engine does."""

    def __init__(self, world: World, cat: Catalog, atlas: Atlas, root: Path):
        self.w = world
        self.cat = cat
        self.atlas = atlas
        self.root = Path(root)
        self.hw = cat.tile_w // 2
        self.hh = cat.tile_h // 2
        self.lp = cat.level_px
        self.cols = terrain_colours(world, cat, atlas)
        self.font = font(root, 10)
        self.font_label = font(root, 11, bold=True)
        self._diamonds: dict = {}
        self._place: dict = {}
        self.missing: set[str] = set()

    # sprites and stand-ins -------------------------------------------------------------------

    def _diamond(self, rgb) -> Image.Image:
        key = tuple(int(v) for v in rgb)
        if key not in self._diamonds:
            w, h = 2 * self.hw, 2 * self.hh
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(im).polygon([(self.hw, 0), (w - 1, self.hh), (self.hw, h - 1),
                                        (0, self.hh)], fill=key + (255,))
            self._diamonds[key] = im
        return self._diamonds[key]

    def terrain_sprites(self, tid: str, tx: int, ty: int, mask: int, depth: int):
        """[(image, ox, oy)] for one tile's ground, base then overlay."""
        t = self.cat.terrain.get(tid)
        out = []
        base = self.cat.drawn_base(tid)
        tb = self.cat.terrain.get(base)
        nvar = tb.variants if tb else 1
        v = tile_hash(tx, ty, 1) % max(nvar, 1)
        s = self.atlas.get(f"terrain/{base}/v{v}")
        if s is None and t is not None and not t.base:
            s = None  # the overlay colour below covers the whole tile
        if s is not None:
            out.append(s)
        if t is not None and not t.base:
            o = self.atlas.get(f"terrain/{tid}/m{mask}/f0")
            if o is not None:
                out.append(o)
                return out
        if s is None or (t is not None and not t.base):
            idx = self.w.terrains.index(tid)
            col = self.cols[idx] * (0.96 + 0.08 * (tile_hash(tx, ty, 7) % 100) / 100.0)
            if self.cat.is_water(tid):
                col = col * (1.0 - 0.08 * depth)
            out.append((self._diamond(np.clip(col, 0, 255)), self.hw, 0))
        return out

    def item_sprite(self, item_id: str, k: int, mask: int, layer: str = "base"):
        d = self.cat.items.get(item_id)
        if d is None:
            return None
        vk = f"m{mask}" if d.layout == "connect" else f"r{k}"
        s = self.atlas.get(f"item/{item_id}/{layer}/{vk}/f0")
        if s is None and d.stand_in:
            sd = self.cat.items.get(d.stand_in)
            n = sd.count if sd else 1
            s = self.atlas.get(f"item/{d.stand_in}/{layer}/r{k % max(n, 1)}/f0")
        if s is None and layer == "base":
            self.missing.add(item_id)
        return s

    def piece_sprites(self, item_id: str, k: int):
        """[(piece rect (dx, dy, w, h), sprite)] of a split landmark (world-tech §1.3, §1.11),
        or None when the item is not split or a piece has no sprite."""
        rects = self.cat.geom.get(item_id, {}).get(f"r{k}", {}).get("pieces")
        if not rects:
            return None
        out = []
        for i, rc in enumerate(rects):
            s = self.atlas.get(f"item/{item_id}/base/r{k}/p{i}/f0")
            if s is None:
                self.missing.add(item_id)
                return None
            out.append((tuple(rc), s))
        return out

    def category(self, item_id: str) -> str:
        """What kind of thing a placeholder stands for, by its catalog entry."""
        d = self.cat.items.get(item_id)
        if d is None:
            return "unknown"
        if d.landmark:
            return "landmark"
        if d.rise > 0:
            return "stair"
        if d.on == "water" or "crossing" in d.extra.get("tags", []):
            return "water"
        if d.layout == "variant" and d.footprint == (1, 1) and d.stand_in:
            return "plant"
        if d.has_door or d.glow:
            return "building"
        if d.layout == "connect":
            return "wall"
        return "prop"

    def placeholder(self, item_id: str, fx: int, fy: int) -> tuple[Image.Image, int, int]:
        """A box of the catalog height over the footprint, coloured by category (landmark,
        building, stair, water deck, wall, prop, plant) with the id written on it, legible at
        1x: the label sits on the box, or above it when the box is narrower than the text."""
        key = (item_id, fx, fy)
        if key in self._place:
            return self._place[key]
        d = self.cat.items.get(item_id)
        hpx = int(d.height) if d and d.height else 32
        hw, hh = self.hw, self.hh
        top = (0, 0)
        right = (fx * hw, fx * hh)
        bottom = ((fx - fy) * hw, (fx + fy) * hh)
        left = (-fy * hw, fy * hh)
        xs = [p[0] for p in (top, right, bottom, left)]
        minx, maxx = min(xs), max(xs)
        label = item_id.split(".", 1)[-1]
        f = self.font_label
        tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(label, font=f))
        bw = maxx - minx + 2
        W = max(bw, tw + 6)
        pad = (W - bw) // 2
        above = 14 if tw + 4 > bw else 0
        H = (fx + fy) * hh + hpx + 2 + above
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        base = PLACEHOLDER_COLOURS[self.category(item_id)]
        a = 235 if fx * fy < 36 else 90

        def P_(p, up=0):
            return (p[0] - minx + 1 + pad, p[1] + hpx + 1 - up + above)

        def shade(k):
            return tuple(int(min(255, v * k)) for v in base) + (a,)

        dr.polygon([P_(left), P_(bottom), P_(bottom, hpx), P_(left, hpx)], fill=shade(0.92))
        dr.polygon([P_(bottom), P_(right), P_(right, hpx), P_(bottom, hpx)], fill=shade(0.74))
        dr.polygon([P_(top, hpx), P_(right, hpx), P_(bottom, hpx), P_(left, hpx)],
                   fill=shade(1.12))
        ink = (40, 34, 30, 255)
        for a_, b_ in ((left, bottom), (bottom, right)):
            dr.line([P_(a_), P_(b_)], fill=ink)
        dr.line([P_(top, hpx), P_(right, hpx), P_(bottom, hpx), P_(left, hpx), P_(top, hpx)],
                fill=ink)
        for p in (left, bottom, right):
            dr.line([P_(p), P_(p, hpx)], fill=ink)
        if above:
            tx, ty = (W - tw) / 2, 0
        else:
            cx, cy = P_(((left[0] + right[0]) / 2, (top[1] + bottom[1]) / 2), hpx // 2)
            tx, ty = cx - tw / 2, cy - 7
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            dr.text((tx + ox, ty + oy), label, font=f, fill=(255, 252, 244, 255))
        dr.text((tx, ty), label, font=f, fill=ink)
        self._place[key] = (im, -minx + 1 + pad, hpx + 1 + above)
        return self._place[key]

    # the frame ----------------------------------------------------------------------------

    def render(self, rect, scale: int = 1, title: str | None = None,
               max_px: int = 2048, strip: int = 512) -> Image.Image:
        """Isometric render of plan rect (c0, r0, c1, r1); scale is 1, 2 or 4 (1/scale size).
        Scale grows automatically so the image fits max_px."""
        c0, r0, c1, r1 = rect
        c0, r0 = max(c0, 0), max(r0, 0)
        c1, r1 = min(c1, COLS - 1), min(r1, ROWS - 1)
        rect = (c0, r0, c1, r1)  # a view may reach past the world's edge: draw what exists
        hw, hh, lp = self.hw, self.hh, self.lp
        tiles = [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
        txs = [r for c, r in tiles]
        tys = [COLS - 1 - c for c, r in tiles]
        xmin = (min(txs) - max(tys)) * hw - hw - 8
        xmax = (max(txs) - min(tys)) * hw + hw + 8
        ymin = (min(txs) + min(tys)) * hh - 15 * lp - 260
        ymax = (max(txs) + max(tys)) * hh + 2 * hh + 15 * lp + 8
        W, H = xmax - xmin, ymax - ymin
        while max(W, H) / scale > max_px:
            scale *= 2
        ops = self._ops(rect, xmin, ymin)
        out = Image.new("RGB", (W // scale, H // scale), (30, 34, 46))
        for y0 in range(0, H, strip):
            band = Image.new("RGBA", (W, min(strip, H - y0)), (30, 34, 46, 255))
            self._draw_band(band, ops, y0)
            band = band.convert("RGB")
            if scale > 1:
                band = band.reduce(scale)
            out.paste(band, (0, y0 // scale))
        if title:
            d = ImageDraw.Draw(out)
            _text(d, (10, 8), title, font(self.root, 16, True), fill=(250, 246, 236), halo=False)
        return out

    def _ops(self, rect, xmin, ymin):
        """Global draw list: ('g', x, y, img) ground, ('s', ...) shadow, ('i', ...) items, in
        order. Coordinates are frame pixels at 1x."""
        c0, r0, c1, r1 = rect
        w = self.w
        hw, hh, lp = self.hw, self.hh, self.lp
        T, L = w.T, w.L

        def lvl(c, r):
            if not (0 <= c < COLS and 0 <= r < ROWS) or T[r, c] == NONE16:
                return 0
            return int(L[r, c] & 0x0F)

        def screen(c, r, lv=None):
            tx, ty = to_grid(c, r)
            lv = lvl(c, r) if lv is None else lv
            return (tx - ty) * hw - xmin, (tx + ty) * hh - lv * lp - ymin

        ground = []
        # Diagonal rows in grid order: s = tx + ty ascending, tx ascending.
        gx0, gx1 = r0, r1
        gy0, gy1 = COLS - 1 - c1, COLS - 1 - c0
        tile_ops: dict = {}
        for s in range(gx0 + gy0, gx1 + gy1 + 1):
            for tx in range(max(gx0, s - gy1), min(gx1, s - gy0) + 1):
                ty = s - tx
                c, r = COLS - 1 - ty, tx
                t = int(T[r, c])
                if t == NONE16:
                    continue
                ops = self._tile_ops(c, r, t, lvl, screen)
                tile_ops[(c, r)] = ops
                ground += ops
        # Items in rect (origin inside, plus big items overlapping).
        elems = []
        occ_tiles = set()
        for idx, it in live_items(w):
            if it.c + it.pw - 1 < c0 or it.c > c1 or it.r + it.ph - 1 < r0 or it.r > r1:
                continue
            elems.append(("item", idx, it))
            for t_ in it.tiles():
                occ_tiles.add(t_)
        shadows = []
        drawn = []
        for kind, idx, it in elems:
            tx0, ty0 = to_grid(it.c + it.pw - 1, it.r)  # origin tile
            fx, fy = it.ph, it.pw
            lv = lvl(it.c + it.pw - 1, it.r)
            ax, ay = screen(it.c + it.pw - 1, it.r, lv)
            mask = self._connect_mask(it) if self.cat.items.get(it.id) and \
                self.cat.items[it.id].layout == "connect" else 0
            sh = self.item_sprite(it.id, it.k, mask, "shadow")
            if sh is not None:
                shadows.append((ax - sh[1], ay - sh[2], sh[0]))
            pieces = self.piece_sprites(it.id, it.k)
            if pieces:
                # A split landmark: each piece sorts by its own rect; all share the anchor.
                for (dx, dy, pw_, ph_), (im, ox, oy) in pieces:
                    box = (ax - ox, ay - oy, ax - ox + im.width, ay - oy + im.height)
                    drawn.append(((tx0 + dx, ty0 + dy, tx0 + dx + pw_, ty0 + dy + ph_), box,
                                  (ax - ox, ay - oy, im)))
                continue
            spr = self.item_sprite(it.id, it.k, mask)
            if spr is None:
                spr = self.placeholder(it.id, fx, fy)
            im, ox, oy = spr
            box = (ax - ox, ay - oy, ax - ox + im.width, ay - oy + im.height)
            drawn.append(((tx0, ty0, tx0 + fx, ty0 + fy), box, (ax - ox, ay - oy, im)))
        # Raised tiles that hide an item behind them join the depth sort (world-tech §4.3).
        for (c, r) in tile_ops:
            lq = lvl(c, r)
            if lq == 0:
                continue
            txq, tyq = to_grid(c, r)
            hides = False
            for a in range(0, lq + 2):
                for b in range(0, lq + 2 - a):
                    if a == 0 and b == 0:
                        continue
                    pc, pr = c + b, r - a  # P = Q - (a, b) in grid: tx - a, ty - b
                    if (pc, pr) in occ_tiles and lq - lvl(pc, pr) > 0 \
                            and a + b <= lq - lvl(pc, pr) + 1:
                        hides = True
                        break
                if hides:
                    break
            if hides:
                ops = tile_ops[(c, r)]
                xs = [o[1] for o in ops] + [o[1] + o[3].width for o in ops]
                ys = [o[2] for o in ops] + [o[2] + o[3].height for o in ops]
                drawn.append(((txq, tyq, txq + 1, tyq + 1), (min(xs), min(ys), max(xs), max(ys)),
                              ops))
        order = depth_order([d_[0] for d_ in drawn], [d_[1] for d_ in drawn])
        items = []
        for i in order:
            payload = drawn[i][2]
            if isinstance(payload, list):
                items += payload
            else:
                x, y, im = payload
                items.append(("i", x, y, im))
        return {"ground": ground, "shadows": shadows, "items": items}

    def _tile_ops(self, c, r, t, lvl, screen):
        w = self.w
        tid = w.terrains[t]
        tx, ty = to_grid(c, r)
        lv = lvl(c, r)
        x, y = screen(c, r, lv)
        aux = (int(w.L[r, c]) >> 4) & 3
        ops = []
        # Faces under the +x (south in plan) and +y (west in plan) edges, down to the neighbour.
        faces = self.cat.faces(tid)
        material = faces[aux] if aux < len(faces) else None
        if self.cat.is_water(tid):
            material = "water"
        for side, (nc, nr) in (("se", (c, r + 1)), ("sw", (c - 1, r))):
            ln = lvl(nc, nr)  # 0 off the map or over no ground
            for band in range(lv - ln):
                ops.append(("g", *self._face(side, material, x, y + band * self.lp, tx, ty,
                                             band)))
        mask = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nc, nr = COLS - 1 - (ty + dy), tx + dx
            if 0 <= nc < COLS and 0 <= nr < ROWS and w.T[nr, nc] == t:
                mask |= bit
        for im, ox, oy in self.terrain_sprites(tid, tx, ty, mask, aux):
            ops.append(("g", x - ox, y - oy, im))
        return ops

    def _face(self, side, material, x, y, tx, ty, band):
        key = None
        if material:
            v = tile_hash(tx, ty, 3 + band) % 4
            key = f"edge/{material}_{side}/v{v}"
            s = self.atlas.get(key)
            if s is not None:
                im, ox, oy = s
                return x - ox, y - oy, im
        col = np.array(FACE_COLOURS.get(material, (130, 110, 90)), dtype=np.float64)
        col = col * (0.78 if side == "se" else 0.95)
        fk = ("face", side, tuple(int(v) for v in col), material == "world.coast" and band == 0)
        if fk not in self._diamonds:
            hw, hh, lp = self.hw, self.hh, self.lp
            im = Image.new("RGBA", (hw + 1, hh + lp + 1), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            if side == "se":
                pts = [(hw, 0), (0, hh), (0, hh + lp), (hw, lp)]
            else:
                pts = [(0, 0), (hw, hh), (hw, hh + lp), (0, lp)]
            dr.polygon(pts, fill=tuple(int(v) for v in col) + (255,))
            if fk[3]:
                fp = [(p[0], p[1]) for p in pts[2:]]
                dr.line(fp[::-1], fill=(240, 244, 246, 255), width=2)
            self._diamonds[fk] = im
        im = self._diamonds[fk]
        if side == "se":
            return x, y + self.hh, im
        return x - self.hw, y + self.hh, im

    def _connect_mask(self, it) -> int:
        tx, ty = to_grid(it.c, it.r)
        mask = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nc, nr = COLS - 1 - (ty + dy), tx + dx
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                j = self.w.occ[nr, nc]
                if j >= 0 and self.w.items[j].id == it.id:
                    mask |= bit
        return mask

    def _draw_band(self, band: Image.Image, ops, y0: int) -> None:
        H = band.height

        def put(x, y, im):
            if y + im.height <= y0 or y >= y0 + H or x + im.width <= 0 or x >= band.width:
                return
            sx0, sy0 = max(0, -x), max(0, y0 - y)
            sx1, sy1 = min(im.width, band.width - x), min(im.height, y0 + H - y)
            if sx1 <= sx0 or sy1 <= sy0:
                return
            src = im if (sx0, sy0, sx1, sy1) == (0, 0, im.width, im.height) else \
                im.crop((sx0, sy0, sx1, sy1))
            band.alpha_composite(src, (x + sx0, y + sy0 - y0))

        for _, x, y, im in ops["ground"]:
            put(int(x), int(y), im)
        if ops["shadows"]:
            # One shadow layer: the darkest alpha wins, never doubling.
            alpha = np.zeros((H, band.width), dtype=np.uint8)
            for x, y, im in ops["shadows"]:
                x, y = int(x), int(y) - y0
                if y + im.height <= 0 or y >= H or x + im.width <= 0 or x >= band.width:
                    continue
                a = np.asarray(im.getchannel("A"))
                sx0, sy0 = max(0, -x), max(0, -y)
                sx1, sy1 = min(im.width, band.width - x), min(im.height, H - y)
                dst = alpha[y + sy0:y + sy1, x + sx0:x + sx1]
                np.maximum(dst, a[sy0:sy1, sx0:sx1], out=dst)
            shade = Image.new("RGBA", band.size, (0, 0, 0, 0))
            shade.putalpha(Image.fromarray(alpha))
            band.alpha_composite(shade)
        for _, x, y, im in ops["items"]:
            put(int(x), int(y), im)


def behind(a, b) -> bool:
    """The engine's rule (src/render/depth.cpp)."""
    sx = -1 if a[2] <= b[0] else (1 if b[2] <= a[0] else 0)
    sy = -1 if a[3] <= b[1] else (1 if b[3] <= a[1] else 0)
    if (sx == 0 and sy == 0) or (sx != 0 and sy != 0 and sx != sy):
        return sum(a) <= sum(b)
    return (sx if sx != 0 else sy) < 0


def depth_order(footprints, screens, cell: float = 128.0) -> list[int]:
    """Topological order over overlapping screen boxes, ties to the shallower centre, then index
    (DepthSorter in src/render/depth.cpp)."""
    n = len(footprints)
    buckets: dict = {}
    for i, (x0, y0, x1, y1) in enumerate(screens):
        for cy in range(int(y0 // cell), int(y1 // cell) + 1):
            for cx in range(int(x0 // cell), int(x1 // cell) + 1):
                buckets.setdefault((cx, cy), []).append(i)
    succ = [[] for _ in range(n)]
    indeg = [0] * n
    seen = set()
    for lst in buckets.values():
        for ai in range(len(lst)):
            for bi in range(ai + 1, len(lst)):
                i, j = lst[ai], lst[bi]
                key = (i, j) if i < j else (j, i)
                if key in seen:
                    continue
                p, q = screens[i], screens[j]
                if not (p[0] < q[2] and q[0] < p[2] and p[1] < q[3] and q[1] < p[3]):
                    continue
                seen.add(key)
                if behind(footprints[i], footprints[j]):
                    succ[i].append(j)
                    indeg[j] += 1
                else:
                    succ[j].append(i)
                    indeg[i] += 1
    key = [sum(f) for f in footprints]
    heap = [(key[i], i) for i in range(n) if indeg[i] == 0]
    heapq.heapify(heap)
    out, done = [], [False] * n
    while len(out) < n:
        if not heap:
            # A cycle: break it at the shallowest remaining element, as the engine does.
            i = min((k for k in range(n) if not done[k]), key=lambda k: (key[k], k))
            heap.append((key[i], i))
            indeg[i] = 0
        _, i = heapq.heappop(heap)
        if done[i]:
            continue
        done[i] = True
        out.append(i)
        for j in succ[i]:
            indeg[j] -= 1
            if indeg[j] == 0 and not done[j]:
                heapq.heappush(heap, (key[j], j))
    return out


def home_preview(world: World, cat: Catalog, root: Path) -> None:
    """Paint the home region's fully revealed starter land (all stages, from the home catalog
    catalog) into a composed world, for previews only; the engine writes the home from the save."""
    import json
    doc = json.loads((Path(root) / "assets/catalog.json").read_text())
    if "land" not in doc:
        return
    (hc, hr), (hw_, hh_) = P.HOME["origin_plan"], P.HOME["size"]
    lv = P.HOME["level"]
    did = world.districts.index("corner/home") if "corner/home" in world.districts else None
    if did is None:
        world.districts.append("corner/home")
        did = len(world.districts) - 1

    def tindex(t):
        if t not in world.terrains:
            world.terrains.append(t)
        return world.terrains.index(t)

    sl = (slice(hr, hr + hh_), slice(hc, hc + hw_))
    world.T[sl] = tindex("grass")
    world.L[sl] = lv
    world.D[sl] = did
    from .compose import WItem

    def home_to_plan(x, y):
        return hc + hw_ - 1 - y, hr + x  # home (x, y) -> plan (C, R) of that tile

    terr = list(doc.get("starter", {}).get("terrain", []))
    items = list(doc.get("starter", {}).get("items", []))
    for st in doc.get("land", {}).get("stages", []):
        terr += st.get("reveal", {}).get("terrain", [])
        items += st.get("reveal", {}).get("items", [])
    for t in terr:
        x0, y0, x1, y1 = t["rect"]
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                c, r = home_to_plan(x, y)
                world.T[r, c] = tindex(t["id"])
    for it in items:
        d = cat.items.get(it["id"])
        if d is None:
            continue
        k = it.get("v", 0)
        fx, fy = d.footprint_k(k)
        c_o, r_o = home_to_plan(it["x"], it["y"])  # origin tile = plan north-east corner
        wi = WItem(it["id"], c_o - (fy - 1), r_o, fy, fx, k, "home", "home")
        world.items.append(wi)
        for c, r in wi.tiles():
            if world.occ[r, c] < 0:
                world.occ[r, c] = len(world.items) - 1
