"""Compose preview scenes from a set's packed pages the way the engine will draw them
(world-tech.md §1.6): terrain at integer levels with edge faces stacked under raised tiles,
item shadows, then items, landmark pieces and actors back to front; night multiplies the frame
by a cool tint and adds glow layers. Shared by every set's preview module."""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

BG = (54, 62, 84)
NIGHT_TINT = np.array([0.34, 0.38, 0.62])


class Pages:
    """All pages of one or more sets (plus the home atlas) as one key space."""

    def __init__(self, out_dir: Path, sets, k, home=None):
        self.k = k
        self.rects, self.images, self.cache = {}, {}, {}
        files = [p for s in sets for p in sorted(Path(out_dir).glob(f"{s}.[0-9]*.json"))]
        if home:
            files.append(Path(home))
        for f in files:
            doc = json.loads(f.read_text())
            img = Image.open(f.parent / doc["image"]).convert("RGBA")
            for key, r in doc["sprites"].items():
                self.rects[key] = r
                self.images[key] = img

    def get(self, key):
        if key not in self.cache:
            r = self.rects.get(key)
            if r is None:
                k = self.k
                self.cache[key] = (Image.new("RGBA", (6 * k, 6 * k), (255, 0, 255, 255)), 3 * k, 6 * k)
            else:
                img = self.images[key]
                self.cache[key] = (img.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])), r["ox"], r["oy"])
        return self.cache[key]

    def frames(self, prefix):
        n = 0
        while f"{prefix}/f{n}" in self.rects:
            n += 1
        return max(n, 1)


class SetScene:
    """A grid of tiles with terrain and levels, items (whole or in pieces) and actors."""

    def __init__(self, w, h, base, margin=40):
        self.w, self.h = w, h
        self.base = base
        self.over = {}                  # (tx, ty) -> overlay terrain id
        self.level = np.zeros((w, h), np.int64)
        self.edge = {}                  # (tx, ty) -> edge material of its faces
        self.items = []                 # (id, variant, tx, ty, fw, fh, pieces or None, frame)
        self.floors = {}                # item id -> indices of pieces that are stair floors
        self.backdrop = None            # backdrop id drawn along the y = 0 (east) edge
        self.actors = []                # (key prefix, x, y, z, mirror, glow) in design units
        self.margin = margin
        self.labels = []

    def paint(self, tid, x0, x1, y0, y1):
        for x in range(max(0, x0), min(self.w, x1 + 1)):
            for y in range(max(0, y0), min(self.h, y1 + 1)):
                self.over[(x, y)] = tid

    def raise_(self, lv, x0, x1, y0, y1, edge=None):
        for x in range(max(0, x0), min(self.w, x1 + 1)):
            for y in range(max(0, y0), min(self.h, y1 + 1)):
                self.level[x, y] = lv
                if edge:
                    self.edge[(x, y)] = edge

    def add(self, item_id, variant, tx, ty, fw=1, fh=1, pieces=None, frame=0):
        self.items.append((item_id, variant, tx, ty, fw, fh, pieces, frame))

    def actor(self, prefix, x, y, z=None, mirror=False, glow=False, frame=0):
        """An actor at design-unit position (x, y); z defaults to its tile's level."""
        self.actors.append((prefix, x, y, z, mirror, glow, frame))

    def label(self, text, tx, ty, dz=0):
        self.labels.append((text, tx, ty, dz))

    def _mask(self, x, y, tid):
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.w and 0 <= ny < self.h and self.over.get((nx, ny)) == tid:
                m |= bit
        return m

    def render(self, pages: Pages, night=False, frame=0, scale_lv=None):
        k = pages.k
        L = 8 * k                       # px per level
        top_lv = int(self.level.max())
        mg = self.margin * k
        self.ox = 16 * k * self.h + mg
        self.oy = mg + top_lv * L + 140 * k + (200 * k if self.backdrop else 0)
        W = 16 * k * (self.w + self.h) + 2 * mg
        H = 8 * k * (self.w + self.h) + 2 * mg + top_lv * L + 180 * k + (200 * k if self.backdrop else 0)
        img = Image.new("RGBA", (W, H), BG + (255,))

        def anchor(tx, ty, lv=0):
            return self.ox + (tx - ty) * 16 * k, self.oy + (tx + ty) * 8 * k - lv * L

        def blit(key, ax, ay, target=img, mirror=False):
            im, ox, oy = pages.get(key)
            if mirror:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
                ox = im.width - 1 - ox
            target.alpha_composite(im, (int(ax - ox), int(ay - oy)))

        def fkey(prefix, f=frame):
            return f"{prefix}/f{f % pages.frames(prefix)}"

        from voxel import hash01
        if self.backdrop:
            for seg in range(0, self.w, 16):
                v = int(hash01(seg, 31) * 4)
                ax, ay = anchor(seg, 0, int(self.level[seg, 0]))
                blit(f"backdrop/{self.backdrop}/{'night' if night else 'day'}/v{v}", ax, ay)
        order = sorted(((int(self.level[x, y]), x + y, x, y) for x in range(self.w) for y in range(self.h)))
        for lv, _d, x, y in order:
            ax, ay = anchor(x, y, lv)
            blit(f"terrain/{self.base}/v{int(hash01(x, y, 99) * 4)}", ax, ay)
            tid = self.over.get((x, y))
            if tid:
                blit(fkey(f"terrain/{tid}/m{self._mask(x, y, tid)}"), ax, ay)
            for side, (dx, dy) in (("se", (1, 0)), ("sw", (0, 1))):
                nx, ny = x + dx, y + dy
                below = self.level[nx, ny] if (0 <= nx < self.w and 0 <= ny < self.h) else 0
                drop = lv - int(below)
                mat = self.edge.get((x, y))
                if drop > 0 and mat:
                    for b in range(drop):
                        v = int(hash01(x, y, b, 7) * 4)
                        key = f"edge/{mat}_{side}/top" if b == 0 and f"edge/{mat}_{side}/top" in pages.rects \
                            else f"edge/{mat}_{side}/v{v}"
                        blit(key, ax, ay + b * L)
        for item_id, var, tx, ty, fw, fh, pieces, f in self.items:
            key = f"item/{item_id}/shadow/{var}"
            if f"{key}/f0" in pages.rects:
                blit(fkey(key, f), *anchor(tx, ty, self.level[tx, ty]))
        draws = []
        for item_id, var, tx, ty, fw, fh, pieces, f in self.items:
            lv = self.level[tx, ty]
            if pieces:
                for i, (px, py, pw, ph) in enumerate(pieces):
                    # Stair floors sort by their back tile, under every actor standing on them;
                    # other pieces by their front tile, over the actors inside them.
                    if i in self.floors.get(item_id, ()):
                        depth = tx + px + ty + py - 1.5
                    else:
                        depth = tx + px + pw - 1 + ty + py + ph - 1
                    draws.append((depth, tx + px, 0,
                                  ("item", f"item/{item_id}/base/{var}/p{i}", tx, ty, lv, f)))
            else:
                draws.append((tx + fw - 1 + ty + fh - 1, tx, 0, ("item", f"item/{item_id}/base/{var}", tx, ty, lv, f)))
        for prefix, x, y, z, mirror, glow, f in self.actors:
            tx, ty = int(x // 16), int(y // 16)
            zz = self.level[min(max(tx, 0), self.w - 1), min(max(ty, 0), self.h - 1)] * 8 if z is None else z
            if not (night and glow):
                draws.append((x / 16 + y / 16 - 1, x / 16, 1, ("actor", prefix, x, y, zz, mirror, f)))
        draws.sort(key=lambda d: d[:3])
        for *_s, what in draws:
            if what[0] == "item":
                _, key, tx, ty, lv, f = what
                blit(fkey(key, f), *anchor(tx, ty, lv))
            else:
                _, prefix, x, y, z, mirror, f = what
                blit(fkey(prefix, f), self.ox + (x - y) * k, self.oy + ((x + y) / 2 - z) * k, mirror=mirror)
        if night:
            arr = np.asarray(img).astype(np.float32)
            arr[..., :3] *= NIGHT_TINT
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            for item_id, var, tx, ty, fw, fh, pieces, f in self.items:
                key = f"item/{item_id}/glow/{var}"
                if f"{key}/f0" in pages.rects:
                    blit(fkey(key, f), *anchor(tx, ty, self.level[tx, ty]), target=glow)
            g = np.asarray(glow).astype(np.float32)
            arr[..., :3] += g[..., :3] * (g[..., 3:4] / 255)
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        if self.labels:
            d = ImageDraw.Draw(img)
            for text, tx, ty, dz in self.labels:
                ax, ay = anchor(tx, ty, self.level[min(tx, self.w - 1), min(ty, self.h - 1)])
                d.text((ax - 3 * len(text), ay - dz * k), text, fill=(250, 240, 210, 255))
        return img


def save(img: Image.Image, out_dir: Path, name: str, scales=(1, 2)):
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in scales:
        suffix = "" if s == 1 else f"_{s}x" if s >= 1 else "_half"
        im = img if s == 1 else img.resize((int(img.width * s), int(img.height * s)),
                                           Image.NEAREST if s > 1 else Image.BOX)
        im.convert("RGB").save(out_dir / f"{name}{suffix}.png", optimize=True)
