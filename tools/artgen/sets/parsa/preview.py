"""Pārsa preview scenes (written to out/artgen/parsa/): the terrace laid out after the bible's
map plan (persepolis.md §2.3–2.6, local plan coordinates c east, r south), each landmark alone
with a figure for scale, a delegation on the great stairway, a paradise garden, a street of
the lower town, every walker with its name, the kit and plants, and a night scene."""

import json

from PIL import Image, ImageDraw

import setbuild
from setpreview import Pages, SetScene, save

P = "parsa."
NOBLE = "walker/parsa.noble/v0/idle_front"


class Plan:
    """Map plan coordinates onto a scene: grid tx = r - r0, ty = c1 - c (world.md §3.2)."""

    def __init__(self, c0, c1, r0, r1):
        self.c0, self.c1, self.r0, self.r1 = c0, c1, r0, r1
        self.s = SetScene(r1 - r0 + 1, c1 - c0 + 1, P + "plain_grass")

    def t(self, c, r):
        return r - self.r0, self.c1 - c

    def rect(self, c0, c1, r0, r1):
        """(x0, x1, y0, y1) grid tiles of a plan rectangle (inclusive)."""
        return r0 - self.r0, r1 - self.r0, self.c1 - c1, self.c1 - c0

    def paint(self, tid, c0, c1, r0, r1):
        self.s.paint(P + tid, *self.rect(c0, c1, r0, r1))

    def level(self, lv, c0, c1, r0, r1, edge=P + "ashlar"):
        self.s.raise_(lv, *self.rect(c0, c1, r0, r1), edge=edge)

    def place(self, item, c0, r0, c1, r1, pieces, var="r0"):
        """A landmark whose plan footprint is c0..c1, r0..r1: origin tile = its NE corner."""
        x, y = self.t(c1, r0)
        fw, fh = r1 - r0 + 1, c1 - c0 + 1
        self.s.add(P + item, var, x, y, fw, fh, pieces.get(P + item))

    def kit(self, item, c, r, var="r0", fw=1, fh=1, frame=0):
        x, y = self.t(c, r)
        if 0 <= x < self.s.w and 0 <= y < self.s.h:
            self.s.add(P + item, var, x, y, fw, fh, frame=frame)

    def walker(self, key, c, r, dx=8.0, dy=8.0, z=None, mirror=False, frame=0):
        x, y = self.t(c, r)
        self.s.actor(key, x * 16 + dx, y * 16 + dy, z, mirror, frame=frame)


def _geom(out_dir):
    g = json.loads((out_dir / "parsa.geom.json").read_text())
    pieces = {i: e["r0"]["pieces"] for i, e in g["items"].items() if "pieces" in e.get("r0", {})}
    floors = {i: set(e["r0"]["floor_pieces"]) for i, e in g["items"].items() if "floor_pieces" in e.get("r0", {})}
    return pieces, floors


# ---------------------------------------------------------------- the terrace

def terrace(pieces, floors, night=False, crop=(24, 126, 16, 122)):
    p = Plan(*crop)
    s = p.s
    s.floors = floors
    s.backdrop = P + "kuh_rahmat"
    p.paint("field_barley", 24, 25, 16, 60)
    p.paint("gravel", 26, 48, 36, 60)
    p.paint("packed_earth", 24, 48, 49, 51)
    p.paint("packed_earth", 22, 24, 52, 122)
    p.paint("garden_bed", 26, 54, 16, 34)
    p.paint("water_channel", 40, 41, 16, 34)
    p.paint("water_channel", 26, 54, 20, 20)
    p.paint("water_channel", 50, 51, 60, 122)
    p.paint("rough_ground", 120, 126, 16, 122)
    # The terrace and its platforms.
    p.level(6, 56, 119, 22, 118)
    p.paint("paving_stone", 56, 119, 22, 118)
    p.level(7, 60, 83, 54, 77)
    p.paint("paving_red", 60, 64, 58, 73)
    p.level(7, 87, 93, 71, 78)
    p.level(8, 63, 70, 82, 91)
    p.level(9, 76, 85, 88, 101)
    p.level(7, 86, 99, 86, 112)
    p.level(8, 120, 126, 16, 122, edge=P + "ashlar")
    # Landmarks after the bible's coordinates.
    p.place("great_stair", 49, 37, 55, 54, pieces)
    p.place("gate_all_lands", 64, 42, 69, 47, pieces)
    p.place("apadana", 60, 54, 83, 77, pieces)
    p.place("apadana_stair_n", 65, 51, 78, 53, pieces)
    p.place("apadana_stair_e", 84, 60, 86, 71, pieces)
    p.place("tacara", 63, 82, 70, 91, pieces)
    p.place("tacara_stair_s", 63, 92, 70, 94, pieces)
    p.place("hadish", 76, 88, 85, 101, pieces)
    p.place("hadish_stair_w", 72, 92, 75, 97, pieces)
    p.place("tripylon", 87, 71, 93, 78, pieces)
    p.place("tripylon_stair", 88, 69, 92, 70, pieces)
    p.place("hall_100", 93, 48, 108, 67, pieces)
    p.place("treasury", 100, 79, 116, 108, pieces)
    p.place("harem", 86, 86, 99, 112, pieces)
    p.place("garrison", 96, 22, 119, 34, pieces)
    p.place("south_stores", 80, 113, 99, 118, pieces)
    p.place("cistern", 122, 60, 126, 64, pieces)
    p.place("paradise_gate", 26, 24, 30, 28, pieces)
    if crop[2] <= 12:
        p.place("pavilion", 32, 12, 37, 17, pieces)
    # The processional road walled from the Gate to the Hall forecourt.
    for c in range(70, 93):
        p.kit("p_wall", c, 42, var="m5")
        p.kit("p_wall", c, 47, var="m5")
    for r in range(18, 122, 1):
        if r % 8 == 0:
            continue
        p.kit("fort_wall", 120, r, var="m10")
    for r in range(24, 122, 8):
        p.kit("fort_tower", 121, r - 1, fw=2, fh=2)
    # Gardens and plaza life.
    for r in range(17, 34, 2):
        p.kit("t_cypress", 39, r, var=f"r{r % 3}")
        p.kit("t_cypress", 43, r, var=f"r{(r + 1) % 3}")
    for c, r in ((31, 20), (35, 30), (47, 22), (50, 30), (28, 32)):
        p.kit("t_plane", c, r, var=f"r{c % 2}")
    for c, r in ((33, 23), (36, 25), (46, 26), (48, 18), (52, 25), (30, 18)):
        p.kit("t_almond" if (c + r) % 2 else "t_pomegranate", c, r, var="r0")
    for r in range(60, 118, 3):
        p.kit("t_poplar", 49, r, var=f"r{r % 2}")
    for c, r in ((30, 40), (34, 44), (40, 56), (44, 52)):
        p.kit("p_tent", c, r, var=f"r{c % 2}", fw=2, fh=2)
    p.kit("p_horse_line", 28, 46, fw=3)
    p.kit("p_fire_altar", 60, 40)
    p.kit("p_fire_altar", 72, 49)
    # A delegation crossing from the stairway to the Gate, guards, nobles, builders.
    for i, key in enumerate(("walker/parsa.usher/v0/move_back", "walker/parsa.del_lydians_lead/v0/move_back",
                             "walker/parsa.del_lydians_bearer/v0/move_back", "walker/parsa.del_lydians_bearer/v1/move_back")):
        p.walker(key, 58 + i, 44, dy=10)
    for c, r in ((56, 43), (56, 48), (63, 43), (63, 46), (70, 58), (70, 62)):
        p.walker("walker/parsa.guard_spear/v0/guard_front", c, r)
    for c, r in ((75, 79), (78, 80), (88, 82)):
        p.walker("walker/parsa.noble/v1/talk_front", c, r)
    for c, r in ((96, 69), (100, 69), (104, 68), (99, 47), (102, 46)):
        p.walker("walker/parsa.mason/v0/work_high_front", c, r)
    for c, r in ((40, 45), (36, 50), (45, 57)):
        p.walker("walker/parsa.child/v0/run_front", c, r)
    # The town of Pārsa on the plain (D4): courtyard houses, workers' rows, workshops, granaries.
    for i, r in enumerate(range(64, 112, 5)):
        p.kit("p_house", 28, r, var=f"r{i % 4}", fw=3, fh=3)
        p.kit("p_house", 33, r + 1, var=f"r{(i + 1) % 4}", fw=3, fh=3)
        p.kit("p_house_small", 38, r, var="r0", fw=2, fh=2)
        p.kit("p_house_small", 40, r, var="r0", fw=2, fh=2)
        if i % 2:
            p.kit("p_workshop", 43, r + 1, var="r1", fw=3, fh=2)
        else:
            p.kit("p_granary", 44, r + 1, var="r0", fw=2, fh=2)
    p.kit("p_brickfield", 25, 92, fw=2, fh=2)
    p.kit("p_kiln", 27, 95)
    p.paint("packed_earth", 26, 47, 62, 63)
    return s


# ---------------------------------------------------------------- landmark sheet

LANDMARK_ORDER = ("great_stair", "gate_all_lands", "apadana", "apadana_stair_n", "apadana_stair_e", "tacara",
                  "tacara_stair_s", "hadish", "hadish_stair_w", "tripylon", "tripylon_stair", "hall_100", "treasury",
                  "harem", "garrison", "south_stores", "cistern", "quarry", "paradise_gate", "pavilion",
                  "road_station", "naqsh_cliff", "kaba", "cyrus_tomb")


def landmark_scene(name, cat, pieces, ground="paving_stone"):
    it = next(i for i in cat["items"] if i["id"] == P + name)
    fw, fh = it["footprint"]
    s = SetScene(fw + 4, fh + 4, P + "plain_grass", margin=16)
    s.paint(P + ground, 1, fw + 2, 1, fh + 2)
    s.add(P + name, "r0", 2, 2, fw, fh, pieces.get(P + name))
    s.actor("walker/parsa.noble/v0/idle_front", (fw + 2.5) * 16, (fh + 2.5) * 16)
    s.actor("walker/parsa.guard_spear/v0/guard_front", (fw + 2.5) * 16 + 12, (fh + 1.5) * 16)
    return s


# ---------------------------------------------------------------- the stairway

def stairway(pieces, floors):
    p = Plan(44, 62, 34, 58)
    p.s.floors = floors
    p.paint("gravel", 44, 48, 34, 58)
    p.level(6, 56, 62, 34, 58)
    p.paint("paving_stone", 56, 62, 34, 58)
    p.place("great_stair", 49, 37, 55, 54, pieces)
    s = p.s
    gx, gy = p.t(55, 37)            # stair origin tile in the scene
    z = lambda lv: lv
    # A delegation climbing the north flights: the usher leading the Lydians up the lower flight,
    # the Medes ahead of them on the upper flight. Heights follow the steps (design units).
    lower = lambda dx: 24.0 * (128 - 16 * dx) / 80          # lower flight north, rising to -x
    upper = lambda dx: 24.0 + 24.0 * (16 * dx - 48) / 64    # upper flight north, rising to +x
    seq = [("walker/parsa.usher/v1/move_back", 7.4, 4.6, lower(7.4)), ("walker/parsa.del_lydians_lead/v0/move_back", 6.6, 4.9, lower(6.6)),
           ("walker/parsa.del_lydians_bearer/v0/move_back", 5.7, 4.6, lower(5.7)), ("walker/parsa.del_lydians_bearer/v1/move_back", 4.8, 4.9, lower(4.8)),
           ("walker/parsa.usher/v2/move_front", 5.9, 1.6, upper(5.9)), ("walker/parsa.del_medes_lead/v0/move_front", 5.1, 1.9, upper(5.1)),
           ("walker/parsa.del_medes_bearer/v0/move_front", 4.3, 1.6, upper(4.3)), ("walker/parsa.del_medes_bearer/v1/move_front", 3.5, 1.9, upper(3.5))]
    for key, dx, dy, zz in seq:      # climbing north (-x) is the back view mirrored
        s.actor(key, (gx + dx) * 16, (gy + dy) * 16, zz, mirror="move_back" in key)
    s.actor("walker/parsa.guard_spear/v1/guard_front", (gx + 7.5) * 16, (gy + 0.4) * 16, 48)
    s.actor("walker/parsa.guard_spear/v2/guard_front", (gx + 10.5) * 16, (gy + 0.4) * 16, 48)
    for i, key in enumerate(("walker/parsa.del_saka_lead/v0/idle_front", "walker/parsa.del_saka_bearer/v0/idle_front",
                             "walker/parsa.del_arabs_bearer/v0/idle_front", "critter/parsa.dromedary/idle_front")):
        s.actor(key, (gx + 8.5) * 16 + i * 6, (gy + 8.0 + i * 0.6) * 16, 0)
    return s


# ---------------------------------------------------------------- the garden

def garden(pieces):
    s = SetScene(22, 22, P + "plain_grass", margin=16)
    s.paint(P + "garden_bed", 1, 20, 1, 20)
    s.paint(P + "gravel", 7, 14, 7, 14)
    s.add(P + "pavilion", "r0", 8, 8, 6, 6, pieces.get(P + "pavilion"))
    for i in range(1, 21):
        if not 8 <= i <= 13:
            s.add(P + "p_channel", "m10", i, 10)
            s.add(P + "p_channel", "m5", 10, i)
    for b in ((3, 3), (17, 3), (3, 17), (17, 17)):
        s.add(P + "p_basin", "r0", *b, frame=1)
    for i in range(2, 21, 2):
        s.add(P + "t_cypress", f"r{i % 3}", 1, i)
        s.add(P + "t_cypress", f"r{(i + 1) % 3}", i, 1)
    for (x, y) in ((5, 5), (15, 5), (5, 15)):
        s.add(P + "t_plane", f"r{x % 2}", x, y)
    for (x, y) in ((4, 7), (7, 4), (15, 15), (13, 17), (17, 13), (6, 13), (13, 6)):
        s.add(P + ("t_almond" if (x + y) % 2 else "t_pomegranate"), "r0", x, y)
    for (x, y) in ((19, 6), (19, 15)):
        s.add(P + "t_date", "r0", x, y)
    for (x, y) in ((3, 12), (12, 3), (18, 9)):
        s.add(P + "p_lilies", f"r{x % 2}", x, y)
    s.add(P + "t_vine", "r0", 16, 19)
    s.add(P + "p_rose", "r0", 8, 19)
    s.actor("walker/parsa.gardener/v0/work_low_front", 6.5 * 16, 9.4 * 16)
    s.actor("walker/parsa.gardener/v1/pour_front", 14.5 * 16, 11.5 * 16)
    s.actor("walker/parsa.musician/v0/play_front", 10.4 * 16, 10.6 * 16)
    s.actor("walker/parsa.musician/v1/play_front", 11.6 * 16, 12.2 * 16)
    s.actor("figure/parsa.amestris/idle_front", 12.6 * 16, 10.5 * 16)
    s.actor("critter/parsa.hoopoe/peck_front", 16.5 * 16, 7.5 * 16, frame=1)
    return s


# ---------------------------------------------------------------- the lower town

def town(pieces):
    s = SetScene(20, 16, P + "plain_grass", margin=16)
    s.paint(P + "packed_earth", 0, 19, 7, 8)
    s.paint(P + "packed_earth", 9, 10, 0, 15)
    for i, (x, y) in enumerate(((1, 1), (5, 1), (1, 11), (12, 11), (16, 11))):
        s.add(P + "p_house", f"r{i % 4}", x, y, 3, 3)
    for x in range(12, 20, 2):
        s.add(P + "p_house_small", "r0", x, 2, 2, 2)
    s.add(P + "p_workshop", "r0", 1, 5, 3, 2)
    s.add(P + "p_granary", "r0", 15, 5, 2, 2)
    s.add(P + "p_granary", "r1", 17, 5, 2, 2)
    s.add(P + "p_brickfield", "r0", 5, 11, 2, 2)
    s.add(P + "p_kiln", "r0", 7, 13)
    s.add(P + "p_oven", "r0", 4, 5)
    s.add(P + "p_well", "r0", 11, 6)
    s.add(P + "p_loom", "r0", 6, 5)
    s.add(P + "p_jars", "r0", 8, 5)
    s.add(P + "p_sacks", "r0", 14, 6)
    s.add(P + "p_scribe_desk", "r0", 14, 9)
    s.add(P + "p_scales", "r0", 13, 9)
    s.add(P + "p_dovecote", "r0", 11, 13)
    s.add(P + "t_pomegranate", "r1", 9, 13)
    s.add(P + "p_fire_altar", "r0", 18, 8)
    for key, x, y in (("walker/parsa.woman_worker/v1/move_front", 3.5, 7.5), ("walker/parsa.woman_worker/v0/throw_front", 6.5, 6.7),
                      ("walker/parsa.woman_worker/v2/stir_front", 4.5, 6.6), ("walker/parsa.child/v0/run_front", 9.5, 9.5),
                      ("walker/parsa.child/v2/kneel_front", 10.6, 10.2), ("walker/parsa.scribe/v0/write_front", 14.5, 10.4),
                      ("figure/parsa.baradkama/serve_front", 13.5, 10.5), ("walker/parsa.labourer/v0/carry_front", 12.5, 7.5),
                      ("figure/parsa.bel_iddin/stir_front", 7.5, 11.6), ("walker/parsa.magus/v0/pour_front", 18.4, 9.4),
                      ("walker/parsa.overseer_woman/v0/gesture_front", 7.4, 7.6), ("walker/parsa.craftsman/v1/work_high_front", 2.5, 6.8),
                      ("walker/parsa.farmer/v1/move_back", 16.5, 7.5), ("critter/parsa.zebu/move_front", 17.5, 7.7),
                      ("cart/parsa.p_cart/v0/move_front", 6.0, 8.0)):
        s.actor(key, x * 16, y * 16)
    return s


# ---------------------------------------------------------------- sheets

def _ascii(text):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", text.replace("θ", "th").replace("ç", "c"))
                   if ord(c) < 128)


def walker_sheet(pages, cat, cols=10, cell=(96, 104)):
    k = pages.k
    kinds = []
    for a in cat["actors"]:
        n = max(1, a.get("variants", 1))
        for v in range(n):
            pre = a["sprite"] + (f"/v{v}" if a.get("variants") else "")
            anim = "idle" if "idle" in a["anims"] else next(iter(a["anims"]))
            kinds.append((a["name"] + (f" {v}" if n > 1 else ""), pre, anim))
    cw, ch = cell[0] * k // 2, cell[1] * k // 2 + 10
    rows = (len(kinds) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * ch), (96, 120, 80, 255))
    d = ImageDraw.Draw(img)
    for i, (name, pre, anim) in enumerate(kinds):
        x, y = (i % cols) * cw, (i // cols) * ch
        key = f"{pre}/{anim}_front/f0"
        im, ox, oy = pages.get(key)
        img.alpha_composite(im, (x + cw // 2 - ox, y + ch - 14 - oy))
        d.text((x + 2, y + ch - 12), _ascii(name)[:18], fill=(255, 250, 230, 255))
    return img


def anim_sheet(pages, prefixes):
    k = pages.k
    rows = []
    for pre in prefixes:
        keys = sorted({kk.rsplit("/f", 1)[0] for kk in pages.rects if kk.startswith(pre + "/")})
        rows.append(keys)
    cw, ch = 28 * k, 52 * k
    W = max(sum(pages.frames(k_) for k_ in r) for r in rows) * cw
    img = Image.new("RGBA", (W, len(rows) * ch), (96, 120, 80, 255))
    for ri, r in enumerate(rows):
        x = 0
        for k_ in r:
            for f in range(pages.frames(k_)):
                im, ox, oy = pages.get(f"{k_}/f{f}")
                img.alpha_composite(im, (x + cw // 2 - ox, ri * ch + ch - 6 - oy))
                x += cw
    return img


def item_sheet(pages, cat, ids, cols=8):
    k = pages.k
    cw, ch = 110 * k, 90 * k
    rows = (len(ids) + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * ch), (120, 104, 84, 255))
    d = ImageDraw.Draw(img)
    for i, iid in enumerate(ids):
        x, y = (i % cols) * cw, (i // cols) * ch
        v = "m5" if any(it["id"] == iid and it["layout"] == "connect" for it in cat["items"]) else "r0"
        for layer in ("shadow", "base"):
            key = f"item/{iid}/{layer}/{v}/f0"
            if key in pages.rects:
                im, ox, oy = pages.get(key)
                img.alpha_composite(im, (x + cw // 2 - ox, y + ch - 30 * k - oy))
        d.text((x + 4, y + ch - 12), iid.split(".")[1], fill=(255, 250, 230, 255))
    return img


def main(build, out_dir):
    cat = json.loads((setbuild.SETS / "parsa" / "catalog.json").read_text())
    pages = Pages(out_dir, ["parsa"], build.k)
    pieces, floors = _geom(out_dir)
    dst = build.previews
    img = terrace(pieces, floors).render(pages)
    save(img, dst, "terrace", scales=(1, 0.5))
    img = terrace(pieces, floors).render(pages, night=True)
    save(img, dst, "terrace_night", scales=(0.5,))
    for name in LANDMARK_ORDER:
        s = landmark_scene(name, cat, pieces, "paving_red" if name in ("apadana", "pavilion") else "paving_stone")
        save(s.render(pages), dst / "landmarks", name, scales=(1,))
    save(stairway(pieces, floors).render(pages), dst, "stairway", scales=(1, 2))
    save(garden(pieces).render(pages), dst, "garden", scales=(1, 2))
    save(town(pieces).render(pages), dst, "town", scales=(1, 2))
    save(town(pieces).render(pages, night=True), dst, "town_night", scales=(1, 2))
    save(walker_sheet(pages, cat), dst, "walkers", scales=(1, 2))
    save(anim_sheet(pages, ["walker/parsa.mason/v0", "walker/parsa.woman_worker/v1", "walker/parsa.usher/v0",
                            "walker/parsa.guard_spear/v0", "figure/parsa.xerxes", "critter/parsa.nisaean_horse",
                            "cart/parsa.p_sledge/v0"]), dst, "animations", scales=(2,))
    kit_ids = [it["id"] for it in cat["items"] if not it.get("landmark") and not it["id"].split(".")[1].startswith(("t_",))]
    plants = [it["id"] for it in cat["items"] if it["id"].split(".")[1].startswith("t_") or
              it["id"].split(".")[1] in ("p_barley", "p_wheat", "p_lilies", "p_rose", "p_steppe")]
    save(item_sheet(pages, cat, kit_ids), dst, "kit", scales=(1, 2))
    save(item_sheet(pages, cat, plants), dst, "plants", scales=(1, 2))
    print(f"previews in {dst}")
