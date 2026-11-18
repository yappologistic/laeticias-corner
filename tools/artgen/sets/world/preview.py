"""World preview scenes (written to out/artgen/world/): a coast with sea bands, foam and a
harbour; each biome as a field with its plants; biome transitions; a river with a bridge, a
ford and boats; the three civilisations' roads across changing ground with milestones and a
station; a mountain pass of stacked faces; a shepherd with his flock; ships under sail and
moored; the sheets of walkers, animals, kit and plants; the backdrop strips.

Scenes draw like the engine: per-tile base and overlay, shore foam on sea tiles beside land,
river flow, edge faces stacked under raised tiles (the sea cliff's animated foot where it
meets water), shadows, then items and actors back to front. City-set pages are loaded beside
the world page, as the engine keeps them resident near their regions."""

import json

import numpy as np
from PIL import Image, ImageDraw

import setbuild
import spec
from setpreview import BG, NIGHT_TINT, Pages, SetScene, save
from voxel import hash01

W_ = "world."
WATER = {"world.sea", "world.shallows", "world.river"}


class WorldScene(SetScene):
    """SetScene with a base per tile, eight base looks, foam, flow and connect masks."""

    def __init__(self, w, h, base="world.steppe", margin=24):
        super().__init__(w, h, base, margin=margin)
        self.bases = {}
        self.flow = {}

    def base_rect(self, tid, x0, x1, y0, y1):
        for x in range(max(0, x0), min(self.w, x1 + 1)):
            for y in range(max(0, y0), min(self.h, y1 + 1)):
                self.bases[(x, y)] = tid

    def connect(self, item_id, tiles):
        """Place a connect piece on each tile with its neighbour mask."""
        tiles = set(tiles)
        for (x, y) in tiles:
            m = 0
            for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
                if (x + dx, y + dy) in tiles:
                    m |= bit
            self.add(item_id, f"m{m}", x, y)

    def _water_mask(self, x, y):
        """Sea and shallows count as one water for the sea's mask, so they meet edge to edge."""
        m = 0
        for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.w and 0 <= ny < self.h and self.over.get((nx, ny)) in ("world.sea", "world.shallows"):
                m |= bit
        return m

    def water_at(self, x, y):
        return self.over.get((x, y)) in WATER

    def render(self, pages: Pages, night=False, frame=0, scale_lv=None):
        k = pages.k
        L = 8 * k
        top_lv = int(self.level.max())
        mg = self.margin * k
        self.ox = 16 * k * self.h + mg
        self.oy = mg + top_lv * L + 140 * k
        Wd = 16 * k * (self.w + self.h) + 2 * mg
        Hd = 8 * k * (self.w + self.h) + 2 * mg + top_lv * L + 180 * k
        img = Image.new("RGBA", (Wd, Hd), BG + (255,))

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

        order = sorted(((int(self.level[x, y]), x + y, x, y) for x in range(self.w) for y in range(self.h)))
        for lv, _d, x, y in order:
            ax, ay = anchor(x, y, lv)
            base = self.bases.get((x, y), self.base)
            nv = 8 if base.startswith(W_) else 4
            blit(f"terrain/{base}/v{int(hash01(x, y, 99) * nv)}", ax, ay)
            tid = self.over.get((x, y))
            if tid == "world.shallows":     # shallows lie over the sea (the engine's water group)
                blit(fkey(f"terrain/world.sea/m{self._water_mask(x, y)}"), ax, ay)
            if tid == "world.sea":
                blit(fkey(f"terrain/{tid}/m{self._water_mask(x, y)}"), ax, ay)
            elif tid:
                blit(fkey(f"terrain/{tid}/m{self._mask(x, y, tid)}"), ax, ay)
            if tid in ("world.sea", "world.shallows"):
                land = 0
                for bit, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and not self.water_at(nx, ny):
                        land |= bit
                if land:
                    blit(fkey(f"terrain/world.sea/foam/m{land}"), ax, ay)
            if (x, y) in self.flow:
                d, mirror = self.flow[(x, y)]
                blit(f"terrain/world.river/flow_{d}/f{frame % 8}", ax, ay, mirror=mirror)
            for side, (dx, dy) in (("se", (1, 0)), ("sw", (0, 1))):
                nx, ny = x + dx, y + dy
                inside = 0 <= nx < self.w and 0 <= ny < self.h
                below = self.level[nx, ny] if inside else 0
                drop = lv - int(below)
                mat = self.edge.get((x, y))
                if drop > 0 and mat:
                    wet = inside and self.water_at(nx, ny)
                    for b in range(drop):
                        v = int(hash01(x, y, b, 7) * 4)
                        key = f"edge/{mat}_{side}/v{v}"
                        if b == 0 and f"edge/{mat}_{side}/top" in pages.rects:
                            key = f"edge/{mat}_{side}/top"
                        if b == drop - 1 and wet and f"edge/{mat}_{side}/v{v}/f0" in pages.rects:
                            key = f"edge/{mat}_{side}/v{v}/f{frame % 4}"
                        blit(key, ax, ay + b * L)
        for item_id, var, tx, ty, fw, fh, pieces, f in self.items:
            key = f"item/{item_id}/shadow/{var}"
            if f"{key}/f0" in pages.rects:
                blit(fkey(key, f), *anchor(tx, ty, self.level[tx, ty]))
        draws = []
        for item_id, var, tx, ty, fw, fh, pieces, f in self.items:
            lv = self.level[tx, ty]
            draws.append((tx + fw - 1 + ty + fh - 1, tx, 0, ("item", f"item/{item_id}/base/{var}", tx, ty, lv, f)))
        for prefix, x, y, z, mirror, glow, f in self.actors:
            tx, ty = int(x // 16), int(y // 16)
            zz = self.level[min(max(tx, 0), self.w - 1), min(max(ty, 0), self.h - 1)] * 8 if z is None else z
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


def _rng(seed):
    return np.random.Generator(np.random.PCG64(seed))


def scatter(s, item, n, x0, x1, y0, y1, variants, seed, avoid=(), fw=1, fh=1, keep=None):
    """Place up to n items in a rectangle on free tiles (not water, not taken)."""
    rng = _rng(seed)
    taken = {(it[2] + a, it[3] + b) for it in s.items for a in range(it[4]) for b in range(it[5])} | set(avoid)
    for _ in range(n * 4):
        if n <= 0:
            break
        x, y = int(rng.integers(x0, x1 + 1)), int(rng.integers(y0, y1 + 1))
        cells = {(x + a, y + b) for a in range(fw) for b in range(fh)}
        if any(c in taken or s.water_at(*c) or not (0 <= c[0] < s.w and 0 <= c[1] < s.h) for c in cells):
            continue
        if keep and not keep(x, y):
            continue
        s.add(W_ + item if "." not in item else item, f"r{int(rng.integers(0, variants))}", x, y, fw, fh)
        taken |= cells
        n -= 1


def blob(s, tid, cx, cy, r, seed, base=False):
    """A noisy round patch of an overlay (or base) terrain."""
    rng = _rng(seed)
    for x in range(int(cx - r - 2), int(cx + r + 3)):
        for y in range(int(cy - r - 2), int(cy + r + 3)):
            d = np.hypot(x - cx, y - cy) + rng.uniform(-1.2, 1.2)
            if d < r and 0 <= x < s.w and 0 <= y < s.h:
                if base:
                    s.bases[(x, y)] = tid
                else:
                    s.paint(tid, x, x, y, y)


# ---------------------------------------------------------------- scenes

def coast():
    """An Aegean cove: land behind (top), a sandy beach, turquoise shallows and the sea in front,
    a rocky headland with sea cliffs on the left, a mole with a beacon and a jetty with boats."""
    s = WorldScene(34, 30, "world.sand")
    for x in range(34):
        for y in range(30):
            shore = 12 + int(2.5 * np.sin(y * 0.35)) + (3 if 8 < y < 18 else 0)
            if x >= shore + 2:
                s.paint("world.sea", x, x, y, y)
            elif x >= shore:
                s.paint("world.shallows", x, x, y, y)
    # The headland: raised rock with sea cliffs, its foot in the sea.
    for x in range(4, 20):
        for y in range(0, 7):
            if x < 20 - abs(y - 3) * 1.5:
                s.over.pop((x, y), None)
                s.raise_(2 if x < 16 else 1, x, x, y, y, edge="world.coast")
                s.paint("world.scrub" if (x + y) % 5 else "world.rock", x, x, y, y)
    blob(s, "world.scrub", 4, 18, 4.5, 1)
    blob(s, "world.scrub", 3, 26, 3.0, 2)
    blob(s, "world.pasture", 6, 12, 2.5, 3)
    for x in range(0, 9):
        s.paint("world.road_earth", x, x, 21, 21)
    s.paint("world.road_earth", 9, 11, 21, 21)
    # Harbour works: a mole running out to sea with a beacon, a jetty, huts and racks.
    s.connect(W_ + "mole", [(x, 25) for x in range(14, 22)])
    s.add(W_ + "beacon", "r0", 22, 25)
    s.connect(W_ + "jetty", [(x, 15) for x in range(12, 18)])
    s.add(W_ + "fish_hut", "r1", 9, 16, 2, 1)
    s.add(W_ + "fish_hut", "r1", 9, 11, 2, 1)
    s.add(W_ + "drying_rack", "r0", 11, 19)
    s.add(W_ + "drying_rack", "r1", 11, 13)
    s.add(W_ + "driftwood", "r0", 12, 22)
    s.add(W_ + "driftwood", "r1", 13, 9)
    scatter(s, "p_maquis", 9, 0, 8, 8, 29, 4, 11)
    scatter(s, "t_oleaster", 3, 0, 6, 10, 28, 2, 12)
    scatter(s, "p_wildflowers", 6, 2, 10, 8, 29, 1, 13, keep=lambda x, y: True)
    scatter(s, "boulder", 4, 0, 12, 7, 29, 2, 14)
    for x, y, v in ((5, 2, 0), (8, 4, 1), (11, 1, 2), (13, 3, 0)):
        s.add(W_ + "p_maquis", f"r{v}", x, y)
    s.add(W_ + "crag", "r0", 9, 1, 2, 2)
    s.add(W_ + "milestone", "r0", 7, 22)
    s.add(W_ + "wayside_shrine", "r1", 8, 20)
    # Life: boats, gulls, fishermen.
    s.actor("ship/world.fishing_boat/idle_front", 18.5 * 16, 16.6 * 16, 0)
    s.actor("ship/world.fishing_boat/idle_back", 16.5 * 16, 14.4 * 16, 0, mirror=True)
    s.actor("ship/world.fishing_boat/move_front", 25 * 16, 10 * 16, 0)
    s.actor("ship/world.fishing_boat/row_back", 26 * 16, 21 * 16, 0, frame=1)
    s.actor("ship/world.phoenician/idle_front", 18.5 * 16, 27.2 * 16, 0)
    s.actor("critter/world.gull/idle_front", 17.4 * 16, 25.5 * 16, 14)
    s.actor("critter/world.gull/idle_back", 20.4 * 16, 25.3 * 16, 14)
    s.actor("critter/world.gull/move_front", 22 * 16, 18 * 16, 60, frame=1)
    s.actor("critter/world.gull/move_back", 15 * 16, 20 * 16, 72, frame=3)
    s.actor("walker/world.fisher/v0/work_low_front", 12.4 * 16, 18.6 * 16)
    s.actor("walker/world.fisher/v1/carry_back", 10.4 * 16, 15.6 * 16, mirror=True)
    s.actor("walker/world.sailor/v0/haul_front", 14.5 * 16, 15.5 * 16, 6)
    s.actor("walker/world.traveller/v0/move_front", 5.5 * 16, 21.5 * 16)
    s.actor("fx/world.spray", 19.6 * 16, 2.5 * 16, 0)
    return s


BIOMES = {
    "latium": dict(base="rome.grass_spring", over=[("rome.field_spring", 3, 3, 3), ("world.rock", 9, 9, 1.5)],
                   plants=[("t_oak", 5, 4), ("rome.t_stone_pine", 1, 3), ("rome.t_cypress", 1, 2), ("p_wildflowers", 6, 1),
                           ("boulder", 3, 2), ("field_hut", 1, 1), ("haystack", 2, 2)],
                   animals=["critter/world.sheep/v0/graze_front", "critter/world.ox/idle_front", "critter/world.goat/v1/idle_back"]),
    "greece": dict(base="athens.dry_grass", over=[("world.scrub", 8, 3, 3), ("world.rock", 10, 9, 1.6)],
                   plants=[("athens.t_olive", 6, 3), ("p_maquis", 7, 4), ("athens.t_cypress", 1, 2), ("p_thistle", 5, 3),
                           ("p_wildflowers", 4, 1), ("boulder", 3, 2), ("cairn", 1, 2)],
                   animals=["critter/world.goat/v0/graze_front", "critter/world.goat/v1/idle_front", "critter/world.donkey/v1/idle_back"]),
    "apennines": dict(base="rome.grass_spring", over=[("world.forest_floor", 6, 6, 4.5), ("world.scree", 2, 10, 2)],
                      plants=[("t_beech", 7, 3), ("t_fir", 5, 3), ("t_oak", 3, 4), ("crag", 1, 3), ("boulder", 3, 2)],
                      animals=["critter/world.eagle/move_front", "critter/world.raven/idle_front"]),
    "taurus": dict(base="world.steppe", over=[("world.forest_floor", 5, 5, 4), ("world.rock", 9, 9, 2), ("world.snow", 1, 10, 1.5)],
                   plants=[("t_cedar", 6, 2), ("t_fir", 4, 3), ("t_juniper", 3, 3), ("crag", 1, 3)], animals=["critter/world.eagle/move_back"]),
    "anatolia": dict(base="world.steppe", over=[("world.field", 2, 2, 2.2), ("world.scree", 9, 8, 1.6)],
                     plants=[("p_thistle", 8, 3), ("p_wildflowers", 5, 1), ("t_juniper", 2, 3), ("boulder", 4, 2),
                             ("t_oak", 1, 4), ("tumulus", 1, 2)],
                     animals=["critter/world.sheep/v1/graze_front", "critter/world.dog/idle_front", "critter/world.stork/peck_front"]),
    "mesopotamia": dict(base="world.alluvium", over=[("world.field", 3, 3, 3.5), ("world.marsh", 9, 9, 2.5)],
                        plants=[("t_palm", 6, 2), ("parsa.t_date", 3, 2), ("t_tamarisk", 3, 3), ("t_reeds", 6, 4),
                                ("reed_hut", 1, 4), ("shaduf", 1, 4)],
                        animals=["critter/world.ox/graze_front", "critter/world.donkey/v0/idle_front", "critter/world.stork/idle_front"]),
    "desert": dict(base="world.sand", over=[("world.gravel_desert", 3, 3, 4), ("world.dune", 9, 9, 3), ("world.salt_flat", 9, 2, 1.6)],
                   plants=[("t_tamarisk", 2, 3), ("p_thistle", 4, 3), ("t_pistachio", 1, 2), ("p_wildflowers", 3, 1),
                           ("tent_black", 1, 2), ("cistern", 1, 2), ("cairn", 1, 2)],
                   animals=["critter/world.gazelle/graze_front", "critter/world.gazelle/idle_back"]),
    "zagros": dict(base="world.steppe", over=[("world.rock", 3, 8, 2), ("world.scree", 8, 2, 1.5)],
                   plants=[("t_oak_zagros", 7, 3), ("t_pistachio", 3, 2), ("t_juniper", 2, 3), ("p_wildflowers", 5, 1),
                           ("crag", 1, 3), ("boulder", 2, 2)],
                   animals=["critter/world.goat/v0/idle_front", "critter/world.goat/v0/graze_back"]),
}


def biome(name, seed):
    b = BIOMES[name]
    s = WorldScene(12, 12, b["base"])
    for i, (tid, cx, cy, r) in enumerate(b["over"]):
        blob(s, tid, cx, cy, r, seed + i)
    if name == "mesopotamia":
        for y in range(12):
            s.paint("world.river", 6, 6, y, y)
            s.flow[(6, y)] = ("e", True)
    sizes = {"crag": (2, 2), "tumulus": (3, 3), "reed_hut": (2, 2), "tent_black": (2, 2), "cistern": (2, 2)}
    for i, (item, n, nv) in enumerate(b["plants"]):
        fw, fh = sizes.get(item, (1, 1))
        scatter(s, item, n, 0, 11, 0, 11, nv, seed + 10 + i, fw=fw, fh=fh)
    for i, a in enumerate(b["animals"]):
        z = 40 if "eagle" in a else None
        s.actor(a, (3.5 + i * 3.0) * 16, (8.5 - i * 2.0) * 16, z)
    return s


def transitions():
    """How the biomes meet: steppe to desert gravel to dunes and sand; steppe to field to silt
    with a canal; rock, scree and snow on the heights; scrub and pasture patches."""
    s = WorldScene(30, 20, "world.steppe")
    s.base_rect("world.sand", 20, 29, 0, 19)
    s.base_rect("world.alluvium", 0, 29, 14, 19)
    s.base_rect("world.sand", 20, 29, 14, 19)
    for x in range(16, 24):
        for y in range(0, 14):
            if x - 16 + (y % 3) * 0.6 > 0.5:
                s.paint("world.gravel_desert", x, x, y, y)
    blob(s, "world.dune", 26, 6, 3.2, 21)
    for x in range(0, 20):
        s.paint("world.field", x, x, 12, 13)
        s.paint("world.river", x, x, 15, 15)
        s.flow[(x, 15)] = ("e", False)
    blob(s, "world.marsh", 6, 18, 2.2, 22)
    blob(s, "world.rock", 4, 4, 3.0, 23)
    blob(s, "world.scree", 7, 6, 2.0, 24)
    blob(s, "world.snow", 3, 3, 1.4, 25)
    blob(s, "world.scrub", 11, 4, 2.4, 26)
    blob(s, "world.pasture", 12, 9, 2.0, 27)
    blob(s, "world.fallow", 16, 17, 1.6, 28)
    s.raise_(1, 2, 7, 1, 7, edge="world.rock")
    s.raise_(2, 3, 5, 2, 4, edge="world.rock")
    scatter(s, "p_thistle", 6, 8, 18, 0, 11, 3, 31)
    scatter(s, "t_palm", 4, 0, 19, 16, 19, 2, 32)
    scatter(s, "t_reeds", 5, 0, 19, 16, 17, 4, 33)
    scatter(s, "t_tamarisk", 2, 20, 28, 12, 19, 3, 34)
    scatter(s, "boulder", 3, 8, 22, 0, 10, 4, 35)
    return s


def river():
    """A river two tiles wide crossing the land: a Roman arch bridge, a timber bridge, a ford of
    stepping stones and a pontoon of boats; reeds on the banks, a reed boat and a hide boat."""
    s = WorldScene(34, 16, "world.alluvium")
    for x in range(34):
        for y in (7, 8):
            s.paint("world.river", x, x, y, y)
            s.flow[(x, y)] = ("e", False)
    for y in list(range(0, 7)) + list(range(9, 16)):
        s.paint("world.road_earth", 4, 4, y, y)
        s.paint("rome.basalt_paving", 13, 14, y, y)
        s.paint("world.road_royal", 27, 28, y, y)
    s.add(W_ + "ford", "r0", 4, 7)
    s.add(W_ + "ford", "r1", 4, 8)
    s.connect(W_ + "bridge_arch", [(13, 7), (13, 8)])
    s.connect(W_ + "bridge_arch", [(14, 7), (14, 8)])
    s.connect(W_ + "bridge_timber", [(21, 7), (21, 8)])
    s.connect(W_ + "pontoon", [(27, 7), (27, 8)])
    s.connect(W_ + "pontoon", [(28, 7), (28, 8)])
    for x in range(0, 34):
        for y in (6, 9):
            if x % 3 != 1 and x not in (4, 13, 14, 21, 27, 28):
                s.add(W_ + "t_reeds", f"r{(x * 7 + y) % 4}", x, y)
    scatter(s, "t_palm", 3, 30, 33, 0, 5, 2, 41)
    scatter(s, "t_tamarisk", 3, 22, 33, 10, 15, 3, 42)
    scatter(s, "parsa.t_poplar", 3, 6, 11, 10, 15, 2, 43)
    scatter(s, "t_oak", 3, 6, 12, 0, 5, 4, 44)
    s.add(W_ + "shaduf", "r0", 31, 6)
    s.add(W_ + "milestone", "r1", 12, 3)
    s.actor("ship/world.reed_boat/move_front", 9 * 16, 7.6 * 16, 0)
    s.actor("ship/world.quffa/move_back", 24.5 * 16, 8.2 * 16, 0)
    s.actor("ship/world.kelek/idle_front", 31 * 16, 8.0 * 16, 0)
    s.actor("walker/world.traveller/v1/move_front", 4.5 * 16, 7.0 * 16, 2)
    s.actor("walker/world.muleteer/v0/move_front", 13.5 * 16, 10.5 * 16)
    s.actor("critter/world.mule/v1/move_front", 13.5 * 16, 9.0 * 16, 18)
    s.actor("critter/world.donkey/v1/move_back", 27.5 * 16, 5.0 * 16, mirror=True)
    s.actor("critter/world.stork/peck_front", 18.5 * 16, 10.5 * 16)
    return s


def roads():
    """The three roads: a Roman via of polygonal basalt with milestones and tombs across green
    Latium; a Greek earth road with a herm and a shrine over dry hills; the Persian Royal Road,
    broad and graded, with its station, a watchtower and a beacon across the steppe."""
    s = WorldScene(36, 20, "world.steppe")
    s.base_rect("rome.grass_spring", 0, 35, 0, 5)
    s.base_rect("athens.dry_grass", 0, 35, 7, 12)
    for x in range(36):
        s.paint("rome.basalt_paving", x, x, 2, 3)
        s.paint("world.road_earth", x, x, 9, 9)
        s.paint("world.road_royal", x, x, 16, 17)
    blob(s, "world.scrub", 8, 11, 2.0, 51)
    blob(s, "world.scrub", 26, 7, 2.2, 52)
    blob(s, "world.scree", 30, 14, 1.5, 53)
    for x in (4, 20):
        s.add("rome.r_milestone", "r0", x, 4)
    s.add("rome.r_tomb", "r0", 10, 0)
    s.add("rome.t_cypress", "r0", 9, 1)
    s.add("rome.t_stone_pine", "r1", 13, 0)
    scatter(s, "t_oak", 4, 0, 35, 0, 0, 4, 54)
    scatter(s, "p_wildflowers", 6, 0, 35, 4, 5, 1, 55)
    s.add("athens.g_herm", "r0", 12, 10)
    s.add("athens.g_shrine", "r0", 22, 10)
    scatter(s, "athens.t_olive", 6, 0, 35, 7, 8, 3, 56)
    scatter(s, "p_maquis", 6, 0, 35, 10, 12, 4, 57)
    s.add(W_ + "terrace_wall", "m10", 2, 11)
    s.connect(W_ + "terrace_wall", [(x, 11) for x in range(28, 34)])
    s.add(W_ + "royal_station", "r0", 6, 12, 4, 4)
    s.add(W_ + "watchtower", "r0", 18, 13, 2, 2)
    s.add(W_ + "beacon", "r0", 28, 19)
    s.add("parsa.p_well", "r0", 24, 15)
    s.add("parsa.p_trough", "r0", 25, 15)
    scatter(s, "p_thistle", 8, 0, 35, 13, 19, 3, 58, keep=lambda x, y: y not in (16, 17))
    s.actor("walker/world.traveller/v0/move_back", 15.5 * 16, 3.5 * 16, mirror=True)
    s.actor("walker/world.merchant/v1/move_front", 17.5 * 16, 9.4 * 16)
    s.actor("critter/world.donkey/v1/move_front", 18.8 * 16, 9.4 * 16)
    s.actor("walker/world.traveller/v2/idle_front", 22.5 * 16, 11.3 * 16)
    s.actor("walker/world.muleteer/v1/move_front", 30.5 * 16, 16.5 * 16)
    for i in range(3):
        s.actor("critter/world.mule/v1/move_front", (27.5 - i * 1.6) * 16, 16.5 * 16, frame=i)
    s.actor("critter/world.mule/v0/idle_front", 7.5 * 16, 16.3 * 16)
    return s


def mountain_pass():
    """A pass between two massifs: limestone faces stacked six levels, snow on the tops, a summit
    horn and a snow dome, crags and scree, the road climbing by a ramp and stairs, a watchtower
    on a shoulder and a beacon on the height."""
    s = WorldScene(24, 24, "world.steppe")
    rng = _rng(61)
    for x in range(24):
        for y in range(24):
            d1 = np.hypot(x - 5, y - 6) + rng.uniform(-1, 1)
            d2 = np.hypot(x - 19, y - 17) + rng.uniform(-1, 1)
            lv = int(max(0, 7 - d1 * 0.9, 6 - d2 * 0.9))
            if lv > 0 and not (10 <= x + y <= 13 and lv < 3):
                s.raise_(lv, x, x, y, y, edge="world.snow" if lv >= 5 else "world.rock")
                s.paint("world.snow" if lv >= 5 else "world.rock" if lv >= 3 else "world.scree", x, x, y, y)
    for t in range(24):          # the road runs through the saddle in axis-parallel steps
        for (x, y) in ((t, 23 - t), (t + 1, 23 - t)):
            if 0 <= x < 24 and 0 <= y < 24 and s.level[x, y] == 0:
                s.paint("world.road_royal", x, x, y, y)
    s.add(W_ + "peak", "r0", 3, 4, 3, 3)
    s.add(W_ + "peak", "r1", 18, 15, 3, 3)
    if s.level[9, 9] == s.level[10, 10]:
        s.add(W_ + "crag", "r1", 9, 9, 2, 2)
    scatter(s, "t_oak_zagros", 6, 0, 23, 0, 23, 3, 62, keep=lambda x, y: s.level[x, y] in (1, 2))
    scatter(s, "t_juniper", 4, 0, 23, 0, 23, 3, 63, keep=lambda x, y: s.level[x, y] in (2, 3))
    scatter(s, "boulder", 6, 0, 23, 0, 23, 4, 64, keep=lambda x, y: s.level[x, y] == 0)
    s.add(W_ + "watchtower", "r1", 14, 2, 2, 2)
    s.actor("walker/world.traveller/v1/move_back", 12.5 * 16, 11.5 * 16, mirror=True)
    s.actor("critter/world.eagle/move_front", 10 * 16, 6 * 16, 120)
    s.actor("critter/world.goat/v0/idle_front", 8.5 * 16, 14.5 * 16)
    return s


def flock():
    """A shepherd with his flock on the steppe: fat-tailed and Mediterranean sheep, goats, the
    dog, a stone fold with its hut, a tumulus on the skyline."""
    s = WorldScene(18, 14, "world.steppe")
    blob(s, "world.pasture", 9, 7, 4.5, 71)
    s.add(W_ + "sheepfold", "r0", 2, 2, 3, 3)
    s.add(W_ + "tumulus", "r0", 13, 0, 3, 3)
    scatter(s, "p_thistle", 6, 0, 17, 0, 13, 3, 72)
    scatter(s, "boulder", 3, 0, 17, 0, 13, 4, 73)
    rng = _rng(74)
    for i in range(14):
        kind = ("critter/world.sheep/v1", "critter/world.sheep/v0", "critter/world.goat/v0", "critter/world.goat/v1")[i % 4]
        anim = ("graze", "idle", "move")[int(rng.integers(0, 3))]
        fac = ("front", "back")[int(rng.integers(0, 2))]
        s.actor(f"{kind}/{anim}_{fac}", (7 + rng.uniform(0, 7)) * 16, (5 + rng.uniform(0, 6)) * 16, frame=int(rng.integers(0, 4)),
                mirror=bool(rng.integers(0, 2)))
    s.actor("walker/athens.herder/v0/move_front", 6.5 * 16, 9.0 * 16)
    s.actor("critter/world.dog/run_front", 12.5 * 16, 11.8 * 16, frame=1)
    s.actor("critter/world.dog/sleep_front", 4.5 * 16, 5.8 * 16)
    s.actor("critter/world.sheep/v1/idle_front", 3.5 * 16, 3.5 * 16)
    s.actor("critter/world.sheep/v0/idle_back", 3.2 * 16, 3.0 * 16)
    return s


def ships():
    """Ships of the sea lanes: a Phoenician merchantman under sail, rowing and moored, fishing
    boats in every state, a reed boat and rafts near the shore."""
    s = WorldScene(30, 16, "world.sand")
    for x in range(30):
        for y in range(16):
            if y >= 3:
                s.paint("world.sea" if y >= 5 else "world.shallows", x, x, y, y)
    s.connect(W_ + "jetty", [(6, y) for y in range(1, 9)])
    s.connect(W_ + "mole", [(18, y) for y in range(2, 11)])
    s.actor("ship/world.phoenician/move_front", 12 * 16, 12 * 16, 0)
    s.actor("ship/world.phoenician/idle_back", 21.5 * 16, 7.0 * 16, 0)
    s.actor("ship/world.phoenician/row_front", 26 * 16, 13 * 16, 0, frame=2)
    s.actor("ship/world.fishing_boat/idle_front", 7.6 * 16, 6.0 * 16, 0)
    s.actor("ship/world.fishing_boat/slack_back", 4.5 * 16, 9.0 * 16, 0)
    s.actor("ship/world.fishing_boat/move_front", 9.0 * 16, 14.5 * 16, 0, frame=1)
    s.actor("ship/world.fishing_boat/row_front", 15.0 * 16, 8.5 * 16, 0, frame=2)
    s.actor("fx/world.wake", 7.2 * 16, 14.0 * 16, 0, frame=2)
    s.actor("fx/world.dolphin", 16 * 16, 13.5 * 16, 0, frame=2)
    s.actor("fx/world.whitecap", 24 * 16, 9 * 16, 0, frame=2)
    s.actor("fx/world.whitecap", 3 * 16, 13 * 16, 0, frame=1)
    s.actor("walker/world.sailor/v1/carry_front", 6.5 * 16, 3.5 * 16, 6)
    s.actor("critter/world.gull/idle_front", 18.5 * 16, 6.5 * 16, 14)
    return s


def actor_sheet(pages, cat, cols=8):
    """Every walker, animal and boat of the set, in each of its animations' first frame."""
    k = pages.k
    rows = []
    for a in cat["actors"]:
        n = max(1, a.get("variants", 1))
        for v in range(n):
            pre = a["sprite"] + (f"/v{v}" if a.get("variants") else "")
            rows.append((a["name"] + (f" {v}" if n > 1 else ""), [f"{pre}/{anim}_front/f0" for anim in a["anims"]]))
    cw, ch = 46 * k, 56 * k
    ncol = max(len(r[1]) for r in rows) + 2
    big = {"ship/world.phoenician"}
    img = Image.new("RGBA", (ncol * cw, sum((2 if r[1][0].rsplit("/", 2)[0] in big else 1) for r in rows) * ch), (96, 120, 80, 255))
    d = ImageDraw.Draw(img)
    y = 0
    for name, keys in rows:
        hh = ch * (2 if keys[0].rsplit("/", 2)[0] in big else 1)
        d.text((4, y + 4), name[:22], fill=(255, 250, 230, 255))
        for i, key in enumerate(keys):
            im, ox, oy = pages.get(key)
            cx = (i + 2) * cw + cw // 2
            img.alpha_composite(im, (int(cx - ox), int(y + hh - 6 * k - oy)))
        y += hh
    return img


def item_sheet(pages, cat, ids, cols=8):
    k = pages.k
    cw, ch = 110 * k, 100 * k
    rows = (len(ids) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * ch), (120, 104, 84, 255))
    d = ImageDraw.Draw(img)
    for i, iid in enumerate(ids):
        it = next(t for t in cat["items"] if t["id"] == iid)
        x, y = (i % cols) * cw, (i // cols) * ch
        looks = ["m5", "m10"] if it["layout"] == "connect" else [f"r{n}" for n in range(min(it.get("count", 1), 4))]
        for j, v in enumerate(looks):
            for layer in ("shadow", "base"):
                key = f"item/{iid}/{layer}/{v}/f0"
                if key in pages.rects:
                    im, ox, oy = pages.get(key)
                    img.alpha_composite(im, (x + cw // (len(looks) + 1) * (j + 1) - ox, y + ch - 24 * k - oy))
        d.text((x + 4, y + ch - 12), iid.split(".")[1], fill=(255, 250, 230, 255))
    return img


def backdrops(pages, cat):
    art = cat["art"]
    ids = list(art.get("backdrops", [])) + list(art.get("backdrops_nice", []))
    k = pages.k
    strips = []
    for b in ids:
        ims = [pages.get(f"backdrop/{b}/day/v{n}") for n in range(2)]
        W = sum(im.width for im, _o, _p in ims)
        H = max(im.height for im, _o, _p in ims)
        row = Image.new("RGBA", (W + 256 * k // 2, H), (150, 180, 210, 255))
        x, yb = 0, 0
        for im, ox, oy in ims:       # consecutive segments: the second starts where the first's edge ends
            row.alpha_composite(im, (x, yb))
            x += im.width
            yb += 128 * k
        strips.append(row.crop((0, 0, W, H + 0)))
    Wm = max(s.width for s in strips)
    img = Image.new("RGBA", (Wm, sum(s.height for s in strips)), (150, 180, 210, 255))
    y = 0
    for st in strips:
        img.alpha_composite(st, (0, y))
        y += st.height
    return img


def flat_sheet(pages, prefixes, cols=16, cell=(40, 40), bg=(110, 120, 100, 255)):
    k = pages.k
    keys = sorted(kk for kk in pages.rects if any(kk.startswith(p) for p in prefixes))
    cw, ch = cell[0] * k, cell[1] * k
    rows = (len(keys) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * ch), bg)
    for i, key in enumerate(keys):
        im, ox, oy = pages.get(key)
        x, y = (i % cols) * cw, (i // cols) * ch
        img.alpha_composite(im, (int(x + cw / 2 - im.width / 2), int(y + ch / 2 - im.height / 2)))
    return img


def main(build, out_dir):
    cat = json.loads((setbuild.SETS / "world" / "catalog.json").read_text())
    atlas = spec.ASSETS / "atlas"
    pages = Pages(out_dir, ["world"], build.k)
    city = Pages(atlas, ["rome", "athens", "parsa"], build.k)
    for kk, r in city.rects.items():
        if kk not in pages.rects:
            pages.rects[kk] = r
            pages.images[kk] = city.images[kk]
    dst = build.previews
    save(coast().render(pages), dst, "coast", scales=(1, 2))
    save(coast().render(pages, night=True, frame=1), dst, "coast_night", scales=(1,))
    for i, name in enumerate(BIOMES):
        save(biome(name, 100 + 37 * i).render(pages), dst / "biomes", name, scales=(1, 2))
    save(transitions().render(pages), dst, "transitions", scales=(1, 2))
    save(river().render(pages), dst, "river", scales=(1, 2))
    save(roads().render(pages), dst, "roads", scales=(1, 2))
    save(roads().render(pages, night=True), dst, "roads_night", scales=(1,))
    save(mountain_pass().render(pages), dst, "mountain_pass", scales=(1, 2))
    save(flock().render(pages), dst, "flock", scales=(1, 2))
    save(ships().render(pages, frame=1), dst, "ships", scales=(1, 2))
    save(actor_sheet(pages, cat), dst, "actors", scales=(1, 2))
    kit = [it["id"] for it in cat["items"] if not it["id"].split(".")[1].startswith(("t_", "p_"))
           and it["id"] not in (W_ + "boulder", W_ + "crag", W_ + "peak", W_ + "driftwood")]
    plants = [it["id"] for it in cat["items"] if it["id"] not in kit]
    save(item_sheet(pages, cat, kit), dst, "kit", scales=(1, 2))
    save(item_sheet(pages, cat, plants), dst, "plants", scales=(1, 2))
    save(backdrops(pages, cat), dst, "backdrops", scales=(1,))
    save(flat_sheet(pages, ["terrain/world."], cols=24, cell=(34, 18)), dst, "terrain_sheet", scales=(2,))
    save(flat_sheet(pages, ["edge/world."], cols=24, cell=(18, 26)), dst, "faces_sheet", scales=(2,))
    save(flat_sheet(pages, ["fx/world.", "goods/world.", "ui/marker_"], cols=20, cell=(36, 36)), dst, "fx_goods_markers",
         scales=(2,))
    save(flat_sheet(pages, ["weather/"], cols=4, cell=(264, 100), bg=(90, 110, 80, 255)), dst, "weather", scales=(1,))
    print(f"previews in {dst}")
