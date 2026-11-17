"""Compose test scenes from the packed atlas the way the engine draws them; write out/artgen/*.png.

Draw order: terrain row by row (grass base, then the overlay chosen by its neighbour mask), the
rim cliffs, all item shadows, then items and critters back to front. Night multiplies the frame
by a cool tint and adds the glow layers on top.
"""

import json

import numpy as np
from PIL import Image

import spec
from voxel import hash01

SCALE = 3
BG = (54, 62, 84)
NIGHT_TINT = np.array([0.34, 0.38, 0.62])
CHARS = {".": "grass", "m": "meadow", "p": "path", "c": "cobble", "w": "water"}


class Atlas:
    def __init__(self):
        doc = json.loads(spec.ATLAS_JSON.read_text())
        self.image = Image.open(spec.ATLAS_PNG).convert("RGBA")
        self.rects = doc["sprites"]
        self.cache = {}

    def get(self, key):
        if key not in self.cache:
            r = self.rects.get(key)
            if r is None:
                im = Image.new("RGBA", (8, 8), (255, 0, 255, 255))
                self.cache[key] = (im, 4, 8)
            else:
                im = self.image.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
                self.cache[key] = (im, r["ox"], r["oy"])
        return self.cache[key]

    def frames(self, prefix):
        n = 0
        while f"{prefix}/f{n}" in self.rects:
            n += 1
        return max(n, 1)


class Scene:
    def __init__(self, rows: list[str], cliffs=True, margin=24):
        self.h = len(rows)
        self.w = len(rows[0])
        self.terrain = [[CHARS[rows[ty][tx]] for ty in range(self.h)] for tx in range(self.w)]
        self.items = []
        self.critters = []
        self.cliffs = cliffs
        self.ox = 16 * self.h + margin
        self.oy = margin + 70
        self.size = (16 * (self.w + self.h) + 2 * margin, 8 * (self.w + self.h) + 2 * margin + 110)

    def add(self, item_id, variant, tx, ty, footprint=(1, 1)):
        self.items.append((item_id, variant, tx, ty, footprint))

    def critter(self, key, x, y, z=0.0, mirror=False, glow=False):
        """`glow` critters are emissive: at night they are drawn after the grade."""
        self.critters.append((key, x, y, z, mirror, glow))

    def anchor(self, tx, ty):
        return self.ox + (tx - ty) * 16, self.oy + (tx + ty) * 8

    def mask(self, tx, ty):
        t = self.terrain[tx][ty]
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < self.w and 0 <= ny < self.h and self.terrain[nx][ny] == t:
                m |= bit
        return m

    def render(self, atlas: Atlas, frame=0, night=False) -> Image.Image:
        img = Image.new("RGBA", self.size, BG + (255,))

        def blit(key, ax, ay, mirror=False, target=img):
            im, ox, oy = atlas.get(key)
            if mirror:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
                ox = im.width - 1 - ox
            target.alpha_composite(im, (int(ax - ox), int(ay - oy)))

        def fkey(prefix):
            return f"{prefix}/f{frame % atlas.frames(prefix)}"

        for d in range(self.w + self.h - 1):
            for tx in range(self.w):
                ty = d - tx
                if not 0 <= ty < self.h:
                    continue
                ax, ay = self.anchor(tx, ty)
                v = int(hash01(tx, ty, 99) * 4)
                blit(f"terrain/grass/v{v}", ax, ay)
                t = self.terrain[tx][ty]
                if t != "grass":
                    blit(fkey(f"terrain/{t}/m{self.mask(tx, ty)}"), ax, ay)
        if self.cliffs:
            for tx in range(self.w):
                blit("edge/cliff_sw", *self.anchor(tx, self.h - 1))
            for ty in range(self.h):
                blit("edge/cliff_se", *self.anchor(self.w - 1, ty))
        for item_id, var, tx, ty, _fp in self.items:
            if f"item/{item_id}/shadow/{var}/f0" in atlas.rects:
                blit(fkey(f"item/{item_id}/shadow/{var}"), *self.anchor(tx, ty))
        drawables = []
        for item_id, var, tx, ty, (fw, fh) in self.items:
            drawables.append(((tx + fw - 1) + (ty + fh - 1), tx, 0, ("item", item_id, var, tx, ty)))
        for key, x, y, z, mirror, glow in self.critters:
            if not (night and glow):
                drawables.append((x / 16 + y / 16 - 1, x / 16, 1, ("critter", key, x, y, z, mirror)))
        drawables.sort(key=lambda d: d[:3])

        def blit_critter(key, x, y, z, mirror, target=img):
            blit(fkey(key), self.ox + (x - y), self.oy + (x + y) / 2 - z, mirror, target)

        for *_s, what in drawables:
            if what[0] == "item":
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
            for key, x, y, z, mirror, glow in self.critters:
                if glow:
                    blit_critter(key, x, y, z, mirror, img)
        return img


def save(img: Image.Image, name: str):
    spec.OUT.mkdir(parents=True, exist_ok=True)
    img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST).save(spec.OUT / name)


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


def sprite_sheet(atlas: Atlas, cat) -> Image.Image:
    """Critter animations and effects, one row each, anchors marked by the cell layout."""
    rows = []
    for v in cat["visitors"]:
        for anim, n in spec.CRITTER_ANIMS.items():
            rows.append((f"critter/{v['id']}/{anim}", n, v["habitat"]))
    for name, n in spec.FX_FRAMES.items():
        rows.append((f"fx/{name}", n, "fx"))
    cell = 28
    img = Image.new("RGBA", (cell * 7, cell * len(rows)), BG + (255,))
    ground = {"water": (59, 114, 155), "land": (74, 125, 71), "air": (103, 154, 72), "fx": (70, 80, 110)}
    for r, (prefix, n, habitat) in enumerate(rows):
        for f in range(n):
            x0, y0 = f * cell, r * cell
            img.paste(ground[habitat] + (255,), (x0, y0, x0 + cell - 1, y0 + cell - 1))
            im, ox, oy = atlas.get(f"{prefix}/f{f}")
            img.alpha_composite(im, (x0 + cell // 2 - ox, y0 + cell - 6 - oy))
            if habitat == "land" or habitat == "air":
                im2 = im.transpose(Image.FLIP_LEFT_RIGHT)
                if f == 0:
                    img.paste(ground[habitat] + (255,), (6 * cell, y0, 7 * cell - 1, y0 + cell - 1))
                    img.alpha_composite(im2, (6 * cell + cell // 2 - (im.width - 1 - ox), y0 + cell - 6 - oy))
    return img


def main():
    cat = spec.load_catalog()
    atlas = Atlas()
    save(terrain_scene().render(atlas), "terrain.png")
    nature = ["oak", "pine", "blossom", "bush", "berry_bush", "tall_grass", "flowers_red",
              "flowers_white", "flowers_violet", "mushrooms", "rock", "stump", "reeds"]
    save(item_sheet(nature, cat, gap=1).render(atlas), "nature.png")
    garden = ["planter", "beehive", "scarecrow", "well", "lamp", "bench", "picnic_table",
              "campfire"]
    save(item_sheet(garden, cat, gap=1).render(atlas), "garden.png")
    homes = ["cottage", "toolshed", "coop", "greenhouse", "barn", "windmill"]
    save(item_sheet(homes, cat, gap=1).render(atlas), "homes.png")
    save(item_sheet(homes, cat, gap=1).render(atlas, night=True), "homes_night.png")
    save(pond_scene().render(atlas), "pond.png")
    for f in range(2):
        save(pond_scene().render(atlas, frame=f), f"pond_f{f}.png")
    save(maze_scene().render(atlas), "maze.png")
    save(village_scene().render(atlas), "village.png")
    save(village_scene(night=True).render(atlas, night=True), "village_night.png")
    save(forest_scene().render(atlas), "forest.png")
    save(field_scene().render(atlas), "field.png")
    sheet = sprite_sheet(atlas, cat)
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(spec.OUT / "sprites.png")
    print(f"previews in {spec.OUT}")


if __name__ == "__main__":
    main()
