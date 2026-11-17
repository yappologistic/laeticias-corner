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

    def critter(self, key, x, y, z=0.0, mirror=False):
        self.critters.append((key, x, y, z, mirror))

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
            blit(fkey(f"item/{item_id}/shadow/{var}"), *self.anchor(tx, ty))
        drawables = []
        for item_id, var, tx, ty, (fw, fh) in self.items:
            drawables.append(((tx + fw - 1) + (ty + fh - 1), tx, 0, ("item", item_id, var, tx, ty)))
        for key, x, y, z, mirror in self.critters:
            drawables.append((x / 16 + y / 16 - 1, x / 16, 1, ("critter", key, x, y, z, mirror)))
        drawables.sort(key=lambda d: d[:3])
        for *_s, what in drawables:
            if what[0] == "item":
                _, item_id, var, tx, ty = what
                blit(fkey(f"item/{item_id}/base/{var}"), *self.anchor(tx, ty))
            else:
                _, key, x, y, z, mirror = what
                blit(fkey(key), self.ox + (x - y), self.oy + (x + y) / 2 - z, mirror)
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
    rows, placements, ty = [], [], gap
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
    sheet = sprite_sheet(atlas, cat)
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(spec.OUT / "sprites.png")
    print(f"previews in {spec.OUT}")


if __name__ == "__main__":
    main()
