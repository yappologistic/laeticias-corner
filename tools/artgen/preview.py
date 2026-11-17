"""Compose test scenes from the packed atlas the way the engine draws them and write them next to
the build's previews (out/artgen/ at 3x for the default build; 1x and 2x for finer tiles).

Draw order: terrain row by row (grass base, then the overlay chosen by its neighbour mask), the
rim cliffs, all item shadows, then items and critters back to front. Night multiplies the frame
by a cool tint and adds the glow layers on top.
"""

import json

import numpy as np
from PIL import Image

import spec
from voxel import hash01

BG = (54, 62, 84)
NIGHT_TINT = np.array([0.34, 0.38, 0.62])
CHARS = {".": "grass", "m": "meadow", "p": "path", "c": "cobble", "w": "water"}


class Atlas:
    def __init__(self, build: spec.Build):
        doc = json.loads(build.atlas_json.read_text())
        self.image = Image.open(build.atlas_png).convert("RGBA")
        self.k = build.k
        self.rects = doc["sprites"]
        self.cache = {}

    def get(self, key):
        if key not in self.cache:
            r = self.rects.get(key)
            if r is None:
                k = self.k
                im = Image.new("RGBA", (8 * k, 8 * k), (255, 0, 255, 255))
                self.cache[key] = (im, 4 * k, 8 * k)
            else:
                im = self.image.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
                self.cache[key] = (im, r["ox"], r["oy"])
        return self.cache[key]

    def look(self, key, season):
        """The season's look of a key when the atlas has one, else the plain key."""
        if season and f"{key}@{season}" in self.rects:
            return f"{key}@{season}"
        return key

    def frames(self, prefix):
        n = 0
        while f"{prefix}/f{n}" in self.rects:
            n += 1
        return max(n, 1)


class Scene:
    """Tiles, items and critters; critter positions are in design units (16 per tile)."""

    def __init__(self, rows: list[str], cliffs=True, margin=24):
        self.h = len(rows)
        self.w = len(rows[0])
        self.terrain = [[CHARS[rows[ty][tx]] for ty in range(self.h)] for tx in range(self.w)]
        self.items = []
        self.critters = []
        self.cliffs = cliffs
        self.margin = margin
        self.wild = set()        # tiles still wild: darkened grass and a bramble thicket

    def add(self, item_id, variant, tx, ty, footprint=(1, 1)):
        self.items.append((item_id, variant, tx, ty, footprint))

    def critter(self, key, x, y, z=0.0, mirror=False, glow=False, on=0.0):
        """`glow` critters are emissive: at night they are drawn after the grade. `on` lifts the
        draw order, for an actor using an item (lying in the hammock)."""
        self.critters.append((key, x, y, z, mirror, glow, on))

    def anchor(self, tx, ty):
        return self.ox + (tx - ty) * 16 * self.k, self.oy + (tx + ty) * 8 * self.k

    def mask(self, tx, ty):
        t = self.terrain[tx][ty]
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < self.w and 0 <= ny < self.h and self.terrain[nx][ny] == t:
                m |= bit
        return m

    def render(self, atlas: Atlas, frame=0, night=False, season=None) -> Image.Image:
        k = self.k = atlas.k
        margin = self.margin * k
        self.ox = 16 * k * self.h + margin
        self.oy = margin + 70 * k
        self.size = (16 * k * (self.w + self.h) + 2 * margin,
                     8 * k * (self.w + self.h) + 2 * margin + 110 * k)
        img = Image.new("RGBA", self.size, BG + (255,))

        def blit(key, ax, ay, mirror=False, target=img):
            im, ox, oy = atlas.get(key)
            if mirror:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
                ox = im.width - 1 - ox
            target.alpha_composite(im, (int(ax - ox), int(ay - oy)))

        def fkey(prefix):
            return atlas.look(f"{prefix}/f{frame % atlas.frames(prefix)}", season)

        for d in range(self.w + self.h - 1):
            for tx in range(self.w):
                ty = d - tx
                if not 0 <= ty < self.h:
                    continue
                ax, ay = self.anchor(tx, ty)
                v = int(hash01(tx, ty, 99) * 4)
                if (tx, ty) in self.wild:   # the engine darkens and cools wild grass
                    im, ox, oy = atlas.get(atlas.look(f"terrain/grass/v{v}", season))
                    arr = np.asarray(im).astype(np.float32)
                    arr[..., :3] *= (0.62, 0.68, 0.74)
                    img.alpha_composite(Image.fromarray(arr.astype(np.uint8), "RGBA"), (int(ax - ox), int(ay - oy)))
                    continue
                blit(atlas.look(f"terrain/grass/v{v}", season), ax, ay)
                t = self.terrain[tx][ty]
                if t != "grass":
                    blit(fkey(f"terrain/{t}/m{self.mask(tx, ty)}"), ax, ay)
        if self.cliffs:
            falls = []
            for tx in range(self.w):
                blit("edge/cliff_sw", *self.anchor(tx, self.h - 1))
                if self.terrain[tx][self.h - 1] == "water":
                    falls.append(("sw", tx, self.h - 1))
            for ty in range(self.h):
                blit("edge/cliff_se", *self.anchor(self.w - 1, ty))
                if self.terrain[self.w - 1][ty] == "water":
                    falls.append(("se", self.w - 1, ty))
            for face, tx, ty in falls:
                if f"edge/fall_{face}/f0" in atlas.rects:
                    ax, ay = self.anchor(tx, ty)
                    blit(fkey(f"edge/fall_{face}"), ax, ay)
                    blit(fkey("fx/mist"), ax + (8 if face == "se" else -8) * k, ay + 52 * k)
        for item_id, var, tx, ty, _fp in self.items:
            shadow = f"item/{item_id}/shadow/{var.split('/')[0]}"     # stages share the plain shadow
            if f"{shadow}/f0" in atlas.rects:
                blit(fkey(shadow), *self.anchor(tx, ty))
        drawables = []
        for tx, ty in self.wild:
            if hash01(tx, ty, 5) < 0.8:
                drawables.append((tx + ty, tx, 0, ("wild", int(hash01(tx, ty, 6) * 6), tx, ty)))
        for item_id, var, tx, ty, (fw, fh) in self.items:
            drawables.append(((tx + fw - 1) + (ty + fh - 1), tx, 0, ("item", item_id, var, tx, ty)))
        for key, x, y, z, mirror, glow, on in self.critters:
            if not (night and glow):
                drawables.append((x / 16 + y / 16 - 1 + on, x / 16, 1, ("critter", key, x, y, z, mirror)))
        drawables.sort(key=lambda d: d[:3])

        def blit_critter(key, x, y, z, mirror, target=img):
            blit(fkey(key), self.ox + (x - y) * k, self.oy + ((x + y) / 2 - z) * k, mirror, target)

        for *_s, what in drawables:
            if what[0] == "wild":
                _, v, tx, ty = what
                blit(f"wild/thicket/v{v}", *self.anchor(tx, ty))
            elif what[0] == "item":
                _, item_id, var, tx, ty = what
                blit(fkey(f"item/{item_id}/base/{var}"), *self.anchor(tx, ty))
            else:
                blit_critter(*what[1:])
        if night:
            arr = np.asarray(img).astype(np.float32)
            arr[..., :3] *= NIGHT_TINT
            glow = Image.new("RGBA", self.size, (0, 0, 0, 0))
            for item_id, var, tx, ty, _fp in self.items:
                key = fkey(f"item/{item_id}/glow/{var}")
                if key in atlas.rects:
                    blit(key, *self.anchor(tx, ty), target=glow)
            g = np.asarray(glow).astype(np.float32)
            arr[..., :3] += g[..., :3] * (g[..., 3:4] / 255)
            img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
            for key, x, y, z, mirror, glow, _on in self.critters:
                if glow:
                    blit_critter(key, x, y, z, mirror, img)
        return img


def save(build: spec.Build, img: Image.Image, name: str):
    """The default build's previews are enlarged 3x; finer builds are written at 1x and 2x."""
    build.previews.mkdir(parents=True, exist_ok=True)
    for scale, suffix in ((3, ""),) if build.k == 1 else ((1, ""), (2, "_2x")):
        out = build.previews / name.replace(".png", f"{suffix}.png")
        img.resize((img.width * scale, img.height * scale), Image.NEAREST).save(out)


POND = [
    "..............",
    ".ww...w.......",
    ".www..ww..w.w.",
    "..w....w......",
    "......www.....",
    ".www..w.w..ww.",
    ".w.w..www..ww.",
    ".www..........",
    "...........w..",
    ".wwww.....www.",
    ".wwww..w...w..",
    ".wwww.www.....",
    ".wwww..w......",
    "..............",
]


def terrain_scene():
    rows = [
        "......mmmmmm..........",
        "..mm..mmmmmmm.........",
        ".mmmm.mmmpmmm..wwww...",
        ".mm...mmmpmm..wwwwww..",
        "......mmmpm...wwwwww..",
        "pppppppppppppppwwww...",
        "......c..p.....ww.....",
        "..ccc.c..p............",
        "..ccccccppppp...ccc...",
        "..ccc....p..p...ccc...",
        "......mm.p..pppcccc...",
        "....mmmmmp......cc....",
        "...mmmmm.p............",
        "......................",
    ]
    return Scene(rows)


def pond_scene():
    return Scene(POND)


def item_sheet(ids, cat, cols=None, gap=2, base="."):
    """Every variant of each item laid out on a grass field, one row per item."""
    items = {it["id"]: it for it in cat["items"]}
    rows_spec = []
    for item_id in ids:
        it = items[item_id]
        n = 16 if it["layout"] == "connect" else it["count"]
        rows_spec.append((item_id, n, it))
    width = max(sum(max(it["footprint"]) + gap for _ in range(n)) for _, n, it in rows_spec) + gap
    placements, ty = [], gap
    for item_id, n, it in rows_spec:
        fw, fh = it["footprint"]
        tx = gap
        for k in range(n):
            w, h = (fh, fw) if it["layout"] == "rotate" and k % 2 else (fw, fh)
            v = f"m{k}" if it["layout"] == "connect" else f"r{k}"
            placements.append((item_id, v, tx, ty, (w, h)))
            tx += max(fw, fh) + gap
        ty += max(fw, fh) + gap
    terrain = "w" if base == "w" else "."
    scene = Scene([terrain * width for _ in range(ty)])
    for p in placements:
        scene.add(*p)
    return scene


MAZE = [
    "hhhhhhhhh.hh",
    "h.......h..h",
    "h.hhhhh.hh.h",
    "h.h...h....h",
    "h.h.h.hhhh.h",
    "h...h......h",
    "hhhhh.h.hh.h",
    "h.....h.h..h",
    "h.hhhhh.h.hh",
    "h.......h...",
    "hhhhhhhhhhhh",
]


def maze_scene():
    rows = ["." * 16 for _ in range(16)]
    scene = Scene(rows)
    grid = {(x + 1, y + 1) for y, r in enumerate(MAZE) for x, c in enumerate(r) if c == "h"}
    fences = {(x, 14) for x in range(2, 15)} | {(15, y) for y in range(2, 15)}

    def mask_of(cells, x, y):
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            m |= bit if (x + dx, y + dy) in cells else 0
        return m

    for x, y in sorted(grid):
        scene.add("hedge", f"m{mask_of(grid, x, y)}", x, y)
    for x, y in sorted(fences):
        scene.add("fence", f"m{mask_of(fences, x, y)}", x, y)
    scene.add("lamp", "r0", 6, 6)
    scene.add("bench", "r0", 2, 2)
    return scene


VILLAGE = [
    "....................",
    "..mmm.......ww......",
    ".mmmmm.....wwww.....",
    ".mmmm......wwwww....",
    "..mm.......wwww.....",
    ".......p....ww......",
    ".......p............",
    "pppppppppppppp......",
    ".......c.......p....",
    "......ccc......p....",
    ".....ccccc.....p....",
    "......ccc......pppp.",
    ".......c.........p..",
    ".......p.........p..",
    ".......p.....mmm.p..",
    ".......p....mmmmmp..",
    ".......p.....mmm.p..",
    "...................p",
    "....................",
    "....................",
]


def village_scene(night=False):
    s = Scene(VILLAGE)
    for args in [("cottage", "r0", 2, 8, (2, 2)), ("toolshed", "r3", 5, 9, (1, 1)),
                 ("barn", "r0", 9, 13, (3, 2)), ("windmill", "r1", 16, 1, (2, 2)),
                 ("greenhouse", "r0", 17, 8, (2, 2)), ("coop", "r0", 13, 9, (1, 1)),
                 ("well", "r0", 7, 10, (1, 1)), ("lamp", "r0", 9, 9, (1, 1)),
                 ("lamp", "r0", 6, 6, (1, 1)), ("campfire", "r0", 4, 15, (1, 1)),
                 ("bench", "r1", 5, 15, (1, 1)), ("picnic_table", "r0", 2, 17, (2, 1)),
                 ("bridge", "r1", 12, 3, (1, 1)), ("beehive", "r0", 2, 5, (1, 1)),
                 ("beehive", "r3", 4, 4, (1, 1)), ("scarecrow", "r0", 15, 15, (1, 1)),
                 ("planter", "r0", 13, 15, (1, 1)), ("planter", "r1", 14, 16, (1, 1)),
                 ("planter", "r2", 13, 16, (1, 1)), ("planter", "r3", 14, 15, (1, 1))]:
        s.add(*args)
    trees = [("oak", 0, 0), ("oak", 1, 1), ("pine", 0, 3), ("pine", 1, 0), ("oak", 18, 18),
             ("blossom", 10, 6), ("pine", 19, 5), ("pine", 18, 4), ("blossom", 19, 12),
             ("oak", 0, 19), ("pine", 1, 18), ("oak", 19, 16), ("blossom", 6, 1)]
    for i, (t, x, y) in enumerate(trees):
        s.add(t, f"r{i % 4}", x, y)
    small = [("bush", 3, 2), ("berry_bush", 8, 3), ("flowers_red", 2, 3), ("flowers_white", 4, 2),
             ("flowers_violet", 3, 1), ("flowers_red", 13, 8), ("tall_grass", 15, 5),
             ("reeds", 10, 2), ("reeds", 14, 4), ("lily_pads", 13, 2), ("lily_pads", 12, 4),
             ("rock", 16, 6), ("mushrooms", 1, 14), ("stump", 2, 13), ("tall_grass", 10, 17),
             ("tall_grass", 11, 18), ("rock", 7, 18), ("bush", 0, 11), ("flowers_violet", 12, 14)]
    for i, (t, x, y) in enumerate(small):
        s.add(t, f"r{i % 4}", x, y)
    s.critter("critter/duck/move_front", 13 * 16 + 2, 3 * 16 + 4)
    s.critter("critter/duck/idle_back", 12 * 16 + 4, 1 * 16 + 10)
    s.critter("critter/hen/move_front", 12 * 16 + 4, 11 * 16)
    s.critter("critter/hen/idle_front", 13 * 16 + 8, 11 * 16 + 8, mirror=True)
    s.critter("critter/cat/idle_front", 4 * 16 + 8, 11 * 16 + 4)
    s.critter("critter/butterfly/move_front", 3 * 16, 3 * 16, z=14)
    s.critter("critter/bee/move_front", 3 * 16, 5 * 16, z=10)
    if night:  # fireflies only come out at night
        for x, y, z in ((10 * 16 + 4, 17 * 16 + 2, 12), (11 * 16 + 9, 18 * 16 + 6, 18),
                        (15 * 16 + 9, 5 * 16 + 4, 10), (10 * 16 + 12, 2 * 16 + 9, 16)):
            s.critter("critter/firefly/move_front", x, y, z=z, glow=True)
    return s


FOREST = [
    "..............",
    "..............",
    "..............",
    "..............",
    "..............",
    ".........p....",
    ".........p....",
    ".........p....",
    ".........ppppp",
    "..............",
    "...mm.........",
    "..mmmm........",
    "...mm.........",
    "..............",
]


def forest_scene():
    """A small wood of every tree variant beside the cottage, to judge their scale and mix."""
    s = Scene(FOREST)
    s.add("cottage", "r0", 9, 3, (2, 2))
    trees = [("oak", 0, 1, 1), ("pine", 0, 3, 0), ("blossom", 0, 5, 1), ("oak", 1, 1, 4),
             ("pine", 1, 0, 6), ("oak", 2, 3, 3), ("blossom", 1, 6, 4), ("pine", 2, 2, 8),
             ("oak", 3, 4, 6), ("pine", 3, 7, 0), ("blossom", 2, 0, 10), ("blossom", 3, 6, 9),
             ("oak", 0, 9, 11), ("pine", 0, 12, 9)]
    for t, v, x, y in trees:
        s.add(t, f"r{v}", x, y)
    for t, v, x, y in [("bush", 0, 2, 5), ("mushrooms", 1, 3, 5), ("stump", 0, 5, 3),
                       ("flowers_white", 2, 3, 11), ("flowers_red", 0, 2, 12), ("rock", 0, 8, 8),
                       ("tall_grass", 1, 1, 12), ("berry_bush", 3, 7, 6)]:
        s.add(t, f"r{v}", x, y)
    s.critter("critter/cat/idle_front", 9 * 16 + 4, 5 * 16 + 6)
    return s


def field_scene():
    """A wide plain grass field with one meadow patch: gentle patches, no static."""
    n = 22
    rows = []
    for y in range(n):
        r = ""
        for x in range(n):
            dx, dy = (x - 13.5) / 5.5, (y - 8.5) / 4.0
            r += "m" if dx * dx + dy * dy + 0.25 * hash01(x, y, 7) < 1 else "."
        rows.append(r)
    s = Scene(rows)
    for t, v, x, y in [("tall_grass", 0, 5, 15), ("tall_grass", 2, 6, 16), ("flowers_white", 1, 14, 9),
                       ("rock", 1, 17, 18)]:
        s.add(t, f"r{v}", x, y)
    return s


def _anims(atlas: Atlas, prefix: str) -> list[tuple[str, int]]:
    """Every animation under a key prefix in the atlas, with its frame count, in key order."""
    names = sorted({k.rsplit("/", 1)[0] for k in atlas.rects if k.startswith(prefix + "/") and "/f" in k})
    return [(n, atlas.frames(n)) for n in names]


def sprite_sheet(atlas: Atlas, cat, ids=None, cell_units=28) -> Image.Image:
    """Critter animations and effects, one row each, anchors marked by the cell layout."""
    rows = []
    habitat = {v["id"]: v["habitat"] for v in cat["visitors"]}
    for cid in ids or [v["id"] for v in cat["visitors"]]:
        for name, n in _anims(atlas, f"critter/{cid}"):
            rows.append((name, n, {"shore": "water"}.get(habitat.get(cid, "land"), habitat.get(cid, "land"))))
    if ids is None:
        rows += [(name, n, "fx") for name, n in _anims(atlas, "fx")]
    k = atlas.k
    cell = cell_units * k
    img = Image.new("RGBA", (cell * 7, cell * len(rows)), BG + (255,))
    ground = {"water": (59, 114, 155), "land": (74, 125, 71), "air": (103, 154, 72), "fx": (70, 80, 110)}
    for r, (prefix, n, habitat) in enumerate(rows):
        for f in range(min(n, 6)):
            x0, y0 = f * cell, r * cell
            img.paste(ground[habitat] + (255,), (x0, y0, x0 + cell - 1, y0 + cell - 1))
            im, ox, oy = atlas.get(f"{prefix}/f{f}")
            img.alpha_composite(im, (x0 + cell // 2 - ox, y0 + cell - 6 * k - oy))
            if habitat == "land" or habitat == "air":
                im2 = im.transpose(Image.FLIP_LEFT_RIGHT)
                if f == 0:
                    img.paste(ground[habitat] + (255,), (6 * cell, y0, 7 * cell - 1, y0 + cell - 1))
                    img.alpha_composite(im2, (6 * cell + cell // 2 - (im.width - 1 - ox),
                                              y0 + cell - 6 * k - oy))
    return img


# ---- batch 2 previews ----

def laeticia_sheet(atlas: Atlas) -> Image.Image:
    """Every Laeticia animation, one row each (front and back side by side), on grass, with the
    portrait in the corner; anchors marked with a magenta pixel."""
    k = atlas.k
    rows = _anims(atlas, "critter/laeticia")
    cw, ch = 30 * k, 34 * k
    width = max(n for _a, n in rows)
    img = Image.new("RGBA", (cw * width + 160 * k, ch * len(rows)), (74, 125, 71, 255))
    for r, (name, n) in enumerate(rows):
        for f in range(n):
            im, ox, oy = atlas.get(f"{name}/f{f}")
            ax, ay = f * cw + cw // 2, r * ch + ch - 6 * k
            img.alpha_composite(im, (ax - ox, ay - oy))
            img.putpixel((ax, ay), (255, 0, 255, 255))
    im, _ox, _oy = atlas.get("ui/portrait/laeticia")
    img.alpha_composite(im.resize((im.width * 3, im.height * 3), Image.NEAREST), (cw * width + 20 * k, 10 * k))
    return img


def growth_scene() -> Scene:
    """Each veggie bed variant through its four stages, then the plain (ripe) key."""
    s = Scene(["." * 12 for _ in range(6)], cliffs=False)
    for v in range(4):
        for g in range(4):
            s.add("planter", f"r{v}/g{g}", 1 + g * 2, 1 + v)
        s.add("planter", f"r{v}", 10, 1 + v)
    return s


SEASON_ROWS = [
    "..........",
    "..mmm.....",
    ".mmmm..ww.",
    "..mm..www.",
    "......ww..",
    "....pp....",
    "....p.....",
    "..........",
    "..........",
    "..........",
]


def season_scene() -> Scene:
    s = Scene(SEASON_ROWS)
    for t, v, x, y in [("oak", 0, 1, 5), ("blossom", 1, 7, 6), ("pine", 2, 0, 1), ("apple_tree", 0, 3, 8),
                       ("apple_tree", 1, 5, 8), ("bush", 0, 2, 7), ("berry_bush", 1, 8, 1), ("pine", 0, 9, 4),
                       ("oak", 2, 7, 9), ("flowers_red", 0, 2, 3), ("sunflowers", 1, 5, 1), ("stump", 0, 1, 9)]:
        s.add(t, f"r{v}", x, y)
    hedge = [(x, 3) for x in range(3, 6)]
    for x, y in hedge:
        s.add("hedge", f"m{(2 if (x + 1, y) in hedge else 0) | (8 if (x - 1, y) in hedge else 0)}", x, y)
    s.add("cottage", "r0", 6, 4, (2, 2))
    s.critter("critter/laeticia/idle_front", 5 * 16 + 8, 6 * 16 + 8)
    return s


def wild_gate_scene() -> Scene:
    """The far rim of the home region: road, dry-stone wall broken by the rose-arch gate with a
    lamp, the path down through the wood, wild brambles on land not yet earned."""
    rows = ["pppppppppppppp"] + ["......p......."] * 2 + ["." * 14] * 9
    rows[3] = "......p......."
    s = Scene(rows)
    for x in range(14):
        if x != 6:
            s.add("stone_wall", f"m{(2 if x + 1 != 6 and x < 13 else 0) | (8 if x - 1 != 6 and x > 0 else 0)}", x, 1)
    s.add("arbor", "r1", 6, 1)
    s.add("lamp", "r0", 7, 2)
    for x, y, v in ((2, 3, 0), (10, 2, 1), (12, 4, 2), (1, 6, 3), (4, 2, 1)):
        s.add("pine", f"r{v}", x, y)
    s.add("oak", "r1", 9, 4)
    s.add("log_pile", "r0", 3, 5)
    s.add("mushrooms", "r1", 8, 3)
    s.wild = {(x, y) for x in range(14) for y in range(6, 12) if x + (y - 6) * 2 < 30 and not (x > 6 and y < 8)}
    s.critter("critter/laeticia/wave", 6 * 16 + 8, 4 * 16 + 4)
    return s


def delight_scene() -> Scene:
    """A stream running off both south rims as waterfalls, a pond with the koi, the heron and
    the frog, and the rainbow behind (drawn by `delights`)."""
    rows = [
        "............",
        ".....ww.....",
        "....wwww....",
        "....wwwww...",
        ".....www....",
        "......w.....",
        "......wwwwww",
        "......w.....",
        "......w.....",
        "......w.....",
        "......w.....",
        "......w.....",
    ]
    s = Scene(rows)
    s.add("lily_pads", "r1", 5, 2)
    s.add("lily_pads", "r3", 7, 4)
    s.add("rowboat", "r0", 4, 3, (2, 1))
    s.add("reeds", "r0", 3, 3)
    s.add("reeds", "r2", 8, 2)
    s.add("bridge", "r0", 6, 8)
    s.add("stepping_stones", "r1", 8, 6)
    s.add("fountain", "r0", 1, 8, (2, 2))
    s.add("hammock", "r0", 8, 9, (2, 1))
    s.add("bird_feeder", "r0", 2, 5)
    s.add("apple_tree", "r0", 1, 1)
    s.add("blossom", "r2", 10, 3)
    s.critter("critter/koi/move_front", 6 * 16 + 4, 2 * 16 + 8)
    s.critter("critter/heron/fish", 3 * 16 + 10, 4 * 16 + 4)
    s.critter("critter/frog/croak", 5 * 16 + 8, 2 * 16 + 8, z=0.5)
    s.critter("critter/laeticia/lie_front", 9 * 16 + 0, 9 * 16 + 8, z=8, on=2)
    s.critter("critter/robin/idle_front", 2 * 16 + 8, 5 * 16 + 8, z=17)
    return s


def delights(atlas: Atlas) -> Image.Image:
    scene = delight_scene()
    img = scene.render(atlas)
    im, ox, oy = atlas.get("sky/rainbow")
    sky = Image.new("RGBA", img.size, (150, 186, 214, 255))      # a daytime sky, as the engine draws it
    sky.alpha_composite(im, (img.width // 2 - ox, int(img.height * 0.36) - oy))
    island = np.asarray(img).copy()
    base = (np.abs(island[..., :3].astype(int) - BG).sum(-1) == 0)
    out = np.where(base[..., None], np.asarray(sky), island).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")
    # A row of the effects along the top, with a shooting star.
    x = 10 * atlas.k
    for name in ("heart", "petal", "snowflake", "moth", "fish_jump", "apple", "clear", "zzz", "produce"):
        for f in range(atlas.frames(f"fx/{name}")):
            fim, fox, foy = atlas.get(f"fx/{name}/f{f}")
            img.alpha_composite(fim, (x, 30 * atlas.k - foy))
            x += fim.width + 2 * atlas.k
        x += 6 * atlas.k
    sim, sox, soy = atlas.get("fx/star_streak/f0")
    img.alpha_composite(sim, (img.width - 80 * atlas.k, 50 * atlas.k))
    return img


def ui_sheet(atlas: Atlas, cat) -> Image.Image:
    """Title logotype, portrait, the postcard frames assembled round a blank card, tile marks."""
    k = atlas.k
    W, H = 240 * k // 2, 160 * k // 2
    img = Image.new("RGBA", (W * 3 + 40 * k, 420 * k // 2), (54, 62, 84, 255))
    logo, _ox, _oy = atlas.get("title/logo")
    img.alpha_composite(logo, (10, 10))
    por, _ox, _oy = atlas.get("ui/portrait/laeticia")
    img.alpha_composite(por.resize((por.width * 2, por.height * 2), Image.NEAREST), (logo.width + 30, 10))
    for name, x in (("ui/tile_grid", logo.width + 120), ("ui/tile_area", logo.width + 200)):
        t, _ox, _oy = atlas.get(name)
        img.alpha_composite(t, (x, 30))
    frames = [f["id"] for f in cat.get("frames", []) if f"frame/{f['id']}/tl" in atlas.rects]
    for i, style in enumerate(frames):
        card = Image.new("RGBA", (W, H), (110, 150, 100, 255))
        p = {n: atlas.get(f"frame/{style}/{n}")[0] for n in ("tl", "t", "tr", "l", "r", "bl", "b", "br", "plate")}
        c, e, b = p["tl"].width, p["t"].width, p["t"].height
        for x in range(c, W - c, e):
            card.alpha_composite(p["t"], (x, 0))
            card.alpha_composite(p["b"], (x, H - b))
        for y in range(c, H - c, e):
            card.alpha_composite(p["l"], (0, y))
            card.alpha_composite(p["r"], (W - b, y))
        card.alpha_composite(p["tl"], (0, 0))
        card.alpha_composite(p["tr"], (W - c, 0))
        card.alpha_composite(p["bl"], (0, H - c))
        card.alpha_composite(p["br"], (W - c, H - c))
        card.alpha_composite(p["plate"], (c // 2, H - c + 2))
        img.alpha_composite(card, (10 + i * (W + 10), logo.height + 30))
    return img


NEW_ITEMS = ["apple_tree", "sunflowers", "log_pile", "stepping_stones", "stone_wall", "arbor", "bird_feeder",
             "hay_bale", "hammock", "fountain", "rowboat"]


def main_batch2(build: spec.Build, atlas: Atlas, cat):
    if "critter/laeticia/idle_front/f0" not in atlas.rects:
        return
    sheet = laeticia_sheet(atlas)
    save(build, sheet, "laeticia.png")
    sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(build.previews / "laeticia_3x.png")
    rare = [v["id"] for v in cat["visitors"] if v.get("rare")]
    save(build, sprite_sheet(atlas, cat, rare, 36), "rare_visitors.png")
    save(build, sprite_sheet(atlas, cat, ["cat", "hen", "duck", "butterfly"]), "critter_anims.png")
    save(build, growth_scene().render(atlas), "growth.png")
    scene = season_scene()
    looks = [scene.render(atlas, season=s) for s in spec.SEASONS]
    grid = Image.new("RGBA", (looks[0].width * 2, looks[0].height * 2))
    for i, im in enumerate(looks):
        grid.paste(im, ((i % 2) * im.width, (i // 2) * im.height))
    save(build, grid, "seasons.png")
    save(build, wild_gate_scene().render(atlas), "wild_gate.png")
    save(build, wild_gate_scene().render(atlas, night=True), "wild_gate_night.png")
    save(build, delights(atlas), "delights.png")
    save(build, ui_sheet(atlas, cat), "ui.png")
    items = [i for i in NEW_ITEMS if any(it["id"] == i for it in cat["items"])]
    save(build, item_sheet(items, cat, gap=1).render(atlas), "items_new.png")
    save(build, item_sheet(["oak", "blossom", "pine", "apple_tree"], cat, gap=1).render(atlas, season="autumn"),
         "trees_autumn.png")
    save(build, item_sheet(["oak", "blossom", "pine", "apple_tree"], cat, gap=1).render(atlas, season="winter"),
         "trees_winter.png")


def main(build: spec.Build):
    cat = build.load_catalog()
    atlas = Atlas(build)
    save(build, terrain_scene().render(atlas), "terrain.png")
    nature = ["oak", "pine", "blossom", "bush", "berry_bush", "tall_grass", "flowers_red",
              "flowers_white", "flowers_violet", "mushrooms", "rock", "stump", "reeds"]
    save(build, item_sheet(nature, cat, gap=1).render(atlas), "nature.png")
    garden = ["planter", "beehive", "scarecrow", "well", "lamp", "bench", "picnic_table",
              "campfire"]
    save(build, item_sheet(garden, cat, gap=1).render(atlas), "garden.png")
    homes = ["cottage", "toolshed", "coop", "greenhouse", "barn", "windmill"]
    save(build, item_sheet(homes, cat, gap=1).render(atlas), "homes.png")
    save(build, item_sheet(homes, cat, gap=1).render(atlas, night=True), "homes_night.png")
    save(build, pond_scene().render(atlas), "pond.png")
    for f in range(2):
        save(build, pond_scene().render(atlas, frame=f), f"pond_f{f}.png")
    save(build, maze_scene().render(atlas), "maze.png")
    save(build, village_scene().render(atlas), "village.png")
    save(build, village_scene(night=True).render(atlas, night=True), "village_night.png")
    save(build, forest_scene().render(atlas), "forest.png")
    save(build, field_scene().render(atlas), "field.png")
    main_batch2(build, atlas, cat)
    sheet = sprite_sheet(atlas, cat)
    zoom = max(1, 4 // build.k)
    sheet.resize((sheet.width * zoom, sheet.height * zoom), Image.NEAREST).save(
        build.previews / "sprites.png")
    print(f"previews in {build.previews}")


if __name__ == "__main__":
    main()
