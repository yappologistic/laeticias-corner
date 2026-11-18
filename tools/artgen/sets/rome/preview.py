"""Rome preview scenes (written to out/artgen/rome/): each landmark alone with walkers for
scale, the Forum with the imperial fora, the Colosseum valley, the Campus Martius with the
Pantheon, the Palatine and the Circus, a street of insulae, the Tiber with the island and the
wharves, an aqueduct crossing the fields, Portus, every walker with its name, the kit and the
plants, and night scenes.

`python -m sets.rome.preview DIR id ...` composes quick looks of single landmarks from the
pages in DIR (a `--only` build), for iterating on one model."""

import json
import sys
from pathlib import Path

import setbuild
from setpreview import Pages, SetScene, save

P = "rome."
HOME = Path(__file__).resolve().parents[4] / "assets" / "atlas.json"


def _cat():
    return json.loads((setbuild.SETS / "rome" / "catalog.json").read_text())


def _pieces(iid):
    lm = setbuild.load_set("rome").LANDMARKS[iid]
    fw, fh = lm.footprint
    if fw > setbuild.MAX_PIECE or fh > setbuild.MAX_PIECE or lm.walk:
        return setbuild.make_pieces(fw, fh, set(map(tuple, lm.walk)))
    return None


def landmark_scene(iid, cat, pages, walkers=()):
    it = next(i for i in cat["items"] if i["id"] == iid)
    fw, fh = it["footprint"]
    base = "rome.grass_spring" if "terrain/rome.grass_spring/v0" in pages.rects else "grass"
    s = SetScene(fw + 4, fh + 4, base, margin=16)
    if "terrain/rome.travertine_paving/m0/f0" in pages.rects:
        s.paint("rome.travertine_paving", 1, fw + 2, 1, fh + 2)
    s.add(iid, "r0", 2, 2, fw, fh, _pieces(iid))
    for i, w in enumerate(walkers):
        s.actor(w, (fw + 2.4) * 16 + i * 10, (fh + 2.4) * 16 - i * 6)
    return s


WALKERS = ("walker/rome.citizen/v0/idle_front", "walker/rome.praetorian/v0/guard_front")


def quick(out_dir, ids, night=True):
    out_dir = Path(out_dir)
    cat = _cat()
    pages = Pages(out_dir, ["rome"], 2, home=HOME)
    for iid in ids:
        iid = iid if iid.startswith(P) else P + iid
        walkers = [w for w in WALKERS if f"{w}/f0" in pages.rects]
        s = landmark_scene(iid, cat, pages, walkers)
        name = iid.split(".", 1)[1]
        save(s.render(pages), out_dir, name, scales=(1,))
        if night:
            save(s.render(pages, night=True), out_dir, name + "_night", scales=(1,))
    print(f"quick looks in {out_dir}")


# Plan footprints (c0, c1, r0, r1), rome.md §2.3; where the art changed a footprint (the Arch of
# Titus's three-tile front, the Pantheon with its portico, the bridges' three rows) it is noted
# in the report.
PLAN = {
    "capitolium": (70, 78, 51, 60), "arx": (70, 78, 44, 49), "tabularium": (81, 85, 53, 64),
    "concord": (86, 89, 54, 60), "vespasian": (86, 89, 61, 64), "saturn": (87, 93, 65, 68),
    "rostra": (91, 94, 59, 61), "curia": (93, 96, 53, 56), "lapis_niger": (95, 95, 57, 57),
    "aemilia": (97, 112, 53, 58), "forum_square": (95, 107, 59, 68), "julia": (94, 109, 69, 76),
    "castor": (110, 114, 69, 76), "lacus_iuturnae": (115, 115, 72, 73), "divus_julius": (108, 111, 61, 65),
    "regia": (112, 114, 62, 63), "vesta": (112, 114, 66, 68), "vestals": (115, 121, 65, 71),
    "piperataria": (116, 124, 56, 61), "arch_titus": (123, 123, 68, 70), "venus_roma": (125, 142, 62, 73),
    "colossus": (144, 146, 64, 66), "meta_sudans": (144, 145, 76, 77), "colosseum": (148, 175, 64, 87),
    "pantheon": (36, 44, 8, 21), "pantheon_court": (34, 46, 0, 7), "agrippa_baths": (34, 46, 23, 31),
    "marcellus": (56, 71, 72, 83), "octavia": (50, 60, 62, 70), "matidia": (48, 53, 0, 5),
}


class Plan:
    """Map plan coordinates onto a scene: grid tx = r - r0, ty = c1 - c (world.md §3.2)."""

    def __init__(self, c0, c1, r0, r1, base="rome.grass_spring"):
        self.c0, self.c1, self.r0, self.r1 = c0, c1, r0, r1
        self.s = SetScene(r1 - r0 + 1, c1 - c0 + 1, base)

    def t(self, c, r):
        return r - self.r0, self.c1 - c

    def rect(self, c0, c1, r0, r1):
        return r0 - self.r0, r1 - self.r0, self.c1 - c1, self.c1 - c0

    def paint(self, tid, c0, c1, r0, r1):
        self.s.paint(tid if "." in tid else P + tid, *self.rect(c0, c1, r0, r1))

    def level(self, lv, c0, c1, r0, r1, edge=P + "tufa"):
        self.s.raise_(lv, *self.rect(c0, c1, r0, r1), edge=edge)

    def place(self, item, pages, c0=None, c1=None, r0=None, r1=None):
        """A landmark whose plan footprint is c0..c1, r0..r1: origin tile = its NE corner."""
        c0, c1, r0, r1 = PLAN[item] if c0 is None else (c0, c1, r0, r1)
        if f"item/{P}{item}/base/r0/f0" not in pages.rects and f"item/{P}{item}/base/r0/p0/f0" not in pages.rects:
            return
        x, y = self.t(c1, r0)
        self.s.add(P + item, "r0", x, y, r1 - r0 + 1, c1 - c0 + 1, _pieces(P + item))

    def place_all(self, pages, names=None):
        for name, (c0, c1, r0, r1) in PLAN.items():
            if names is not None and name not in names:
                continue
            if c0 >= self.c0 and c1 <= self.c1 and r0 >= self.r0 and r1 <= self.r1:
                self.place(name, pages)

    def kit(self, item, c, r, var="r0", fw=1, fh=1, frame=0):
        x, y = self.t(c, r)
        if 0 <= x < self.s.w and 0 <= y < self.s.h:
            self.s.add(P + item, var, x, y, fw, fh, frame=frame)

    def walker(self, key, c, r, dx=8.0, dy=8.0, z=None, mirror=False, frame=0):
        x, y = self.t(c, r)
        self.s.actor(key, x * 16 + dx, y * 16 + dy, z, mirror, frame=frame)


def forum(pages):
    """The Capitol, the Forum Romanum and the Velia after the map plan (rome.md §2.3-2.6)."""
    pl = Plan(62, 130, 40, 82)
    pl.level(6, 66, 85, 44, 66)
    pl.level(7, 70, 78, 44, 49)
    pl.paint("tufa_rock", 66, 85, 44, 66)
    pl.paint("travertine_paving", 70, 79, 50, 61)
    pl.paint("travertine_paving", 86, 122, 52, 77)
    pl.paint("basalt_paving", 87, 128, 64, 65)
    pl.paint("basalt_paving", 96, 97, 40, 52)
    pl.paint("basalt_paving", 100, 101, 77, 82)
    pl.level(1, 123, 130, 60, 75, edge=P + "brick")
    pl.place_all(pages)
    return pl.s


def terrain_sheet(pages):
    """Every terrain in a strip, with each face material under a raised block."""
    ids = [t["id"] for t in _cat()["terrain"] if not t.get("base")]
    s = SetScene(6 * len(ids) + 2, 10, "rome.grass_spring", margin=24)
    for i, tid in enumerate(ids):
        s.paint(tid, 1 + i * 6, 4 + i * 6, 1, 8)
    for i, e in enumerate(_cat()["art"]["edges"]):
        s.raise_(3, 2 + i * 8, 5 + i * 8, 8, 9, edge=e)
    return s


def main(build, out_dir):
    out_dir = Path(out_dir)
    pages = Pages(out_dir, ["rome"], 2, home=HOME)
    save(terrain_sheet(pages).render(pages), out_dir, "terrain", scales=(1, 2))
    f = forum(pages)
    save(f.render(pages), out_dir, "forum", scales=(1, 0.5))
    save(f.render(pages, night=True), out_dir, "forum_night", scales=(0.5,))
    quick(out_dir, [i["id"] for i in _cat()["items"] if i.get("landmark")], night=False)


if __name__ == "__main__":
    if sys.argv[2:3] == ["--scenes"]:
        main(None, sys.argv[1])
    else:
        quick(sys.argv[1], sys.argv[2:])
