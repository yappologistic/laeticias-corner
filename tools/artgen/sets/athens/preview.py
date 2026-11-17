"""Athens preview scenes (written to out/artgen/athens/): each landmark alone with walkers for
scale, the Acropolis after the bible's map plan (athens.md §2.3-2.6, plan coordinates c east,
r south), the Agora, a residential quarter, Piraeus, the procession on the Panathenaic Way,
every walker with its name, the kit and plants, and night scenes.

`python -m sets.athens.preview DIR id ...` composes quick looks of single landmarks from the
pages in DIR (a `--only` build), for iterating on one model."""

import json
import sys
from pathlib import Path

import setbuild
from setpreview import Pages, SetScene, save

P = "athens."
HOME = Path(__file__).resolve().parents[4] / "assets" / "atlas.json"


def _geom(out_dir):
    f = Path(out_dir) / "athens.geom.json"
    if not f.exists():
        return {}, {}
    g = json.loads(f.read_text())
    pieces = {i: e["r0"]["pieces"] for i, e in g["items"].items() if "pieces" in e.get("r0", {})}
    floors = {i: set(e["r0"]["floor_pieces"]) for i, e in g["items"].items() if "floor_pieces" in e.get("r0", {})}
    return pieces, floors


def _pieces_from_pages(pages, iid):
    """Pieces of a landmark rebuilt from the set module (for quick looks without geometry)."""
    lm = setbuild.load_set("athens").LANDMARKS[iid]
    fw, fh = lm.footprint
    if fw > setbuild.MAX_PIECE or fh > setbuild.MAX_PIECE or lm.walk:
        return setbuild.make_pieces(fw, fh, set(map(tuple, lm.walk)))
    return None


def landmark_scene(iid, cat, pieces, base="athens.dry_grass", ground=None, walkers=()):
    it = next(i for i in cat["items"] if i["id"] == iid)
    fw, fh = it["footprint"]
    s = SetScene(fw + 4, fh + 4, base, margin=16)
    if ground:
        s.paint(ground, 1, fw + 2, 1, fh + 2)
    s.add(iid, "r0", 2, 2, fw, fh, pieces.get(iid))
    for i, w in enumerate(walkers):
        s.actor(w, (fw + 2.4) * 16 + i * 10, (fh + 2.4) * 16 - i * 6)
    return s


def quick(out_dir, ids):
    out_dir = Path(out_dir)
    cat = json.loads((setbuild.SETS / "athens" / "catalog.json").read_text())
    pages = Pages(out_dir, ["athens"], 2, home=HOME)
    have = {i: e["r0"]["pieces"] for i, e in json.loads((out_dir / "athens.geom.json").read_text())["items"].items()
            if "pieces" in e.get("r0", {})} if (out_dir / "athens.geom.json").exists() else {}
    for iid in ids:
        iid = iid if iid.startswith(P) else P + iid
        pieces = {iid: have.get(iid) or _pieces_from_pages(pages, iid)}
        base = "athens.dry_grass" if "terrain/athens.dry_grass/v0" in pages.rects else "grass"
        walkers = [w for w in ("walker/athens.citizen/v0/idle_front", "walker/athens.hoplite/v0/guard_front")
                   if f"{w}/f0" in pages.rects]
        s = landmark_scene(iid, cat, pieces, base=base, walkers=walkers)
        name = iid.split(".", 1)[1]
        save(s.render(pages), out_dir, name, scales=(1, 2))
        save(s.render(pages, night=True), out_dir, name + "_night", scales=(1,))
    print(f"quick looks in {out_dir}")


class Plan:
    """Map plan coordinates onto a scene: grid tx = r - r0, ty = c1 - c (world.md §3.2)."""

    def __init__(self, c0, c1, r0, r1, base="athens.dry_grass"):
        self.c0, self.c1, self.r0, self.r1 = c0, c1, r0, r1
        self.s = SetScene(r1 - r0 + 1, c1 - c0 + 1, base)

    def t(self, c, r):
        return r - self.r0, self.c1 - c

    def rect(self, c0, c1, r0, r1):
        return r0 - self.r0, r1 - self.r0, self.c1 - c1, self.c1 - c0

    def paint(self, tid, c0, c1, r0, r1):
        self.s.paint(tid if "." in tid else P + tid, *self.rect(c0, c1, r0, r1))

    def level(self, lv, c0, c1, r0, r1, edge=P + "limestone"):
        self.s.raise_(lv, *self.rect(c0, c1, r0, r1), edge=edge)

    def place(self, item, c0, c1, r0, r1, pieces):
        """A landmark whose plan footprint is c0..c1, r0..r1: origin tile = its NE corner."""
        x, y = self.t(c1, r0)
        self.s.add(P + item, "r0", x, y, r1 - r0 + 1, c1 - c0 + 1, pieces.get(P + item))

    def kit(self, item, c, r, var="r0", fw=1, fh=1, frame=0):
        x, y = self.t(c, r)
        if 0 <= x < self.s.w and 0 <= y < self.s.h:
            self.s.add(P + item, var, x, y, fw, fh, frame=frame)

    def walker(self, key, c, r, dx=8.0, dy=8.0, z=None, mirror=False, frame=0):
        x, y = self.t(c, r)
        self.s.actor(key, x * 16 + dx, y * 16 + dy, z, mirror, frame=frame)


W_ = "walker/athens."


def _w(kind, v=0, anim="idle", facing="front"):
    return f"{W_}{kind}/v{v}/{anim}_{facing}"


def _f(fid, anim="idle", facing="front"):
    return f"figure/athens.{fid}/{anim}_{facing}"


# ---------------------------------------------------------------- the Acropolis

def acropolis(pieces, floors):
    """The rock after the map plan (athens.md §2.3-2.6): plateau at local level 10 with its
    sanctuaries, the slopes, the approach ramp with the procession climbing, the theatre and
    the Odeion on the south slope."""
    pl = Plan(44, 136, 62, 126)
    s = pl.s
    s.floors = floors
    # The rock: a broad lower slope, then sheer cliffs to the plateau (the Kimonian wall facing the
    # south cliff), the Nike bastion a level below the plateau at the west end.
    pl.level(3, 56, 130, 64, 103, edge=P + "earth")
    pl.level(5, 60, 126, 69, 103)
    pl.level(10, 64, 122, 73, 103)
    pl.level(9, 62, 65, 86, 96)
    pl.level(10, 62, 65, 84, 90)
    pl.paint("rock_limestone", 56, 130, 64, 103)
    pl.level(10, 66, 122, 103, 103, edge=P + "ashlar")
    pl.paint("rock_limestone", 62, 122, 73, 103)
    pl.paint("gravel", 66, 116, 86, 89)
    pl.paint("marble_paving", 95, 113, 89, 98)
    # The ramp's own ground at level 1, the theatre and Odeion on the flat below.
    pl.level(1, 48, 61, 86, 92, edge=P + "ashlar")
    pl.paint("gravel", 44, 47, 87, 91)
    for name, (c0, c1, r0, r1) in PLAN.items():
        if c0 >= 44 and c1 <= 136 and r0 >= 62 and r1 <= 126:
            pl.place(name, c0, c1, r0, r1, pieces)
    for c, r, i in ((52, 70, 0), (47, 100, 1), (132, 74, 2), (98, 122, 0), (60, 118, 1), (134, 98, 2)):
        pl.kit("t_olive", c, r, var=f"r{i}")
    for c, r in ((70, 116), (78, 120), (88, 118)):
        pl.kit("g_house", c, r, var=f"r{(c + r) % 4}", fw=3, fh=3)
    # The procession climbing the ramp and crossing the plateau to the altar.
    seq = [("marshal", 0), ("kanephoros", 0), ("kanephoros", 1), ("hydriaphoros", 0), ("skaphephoros", 0),
           ("metic_daughter", 0), ("thallophoros", 0), ("thallophoros", 1), ("musician", 0), ("musician", 1),
           ("drover", 0), ("peplos_bearer", 0)]
    for i, (kind, v) in enumerate(seq):
        c = 50 + i
        lift = 8 + 72.0 * (c - 48 + 0.5) / 14
        pl.walker(_w(kind, v, "move", "back"), c, 89, dx=8, dy=4 + (i % 2) * 8, z=min(lift, 80.0), frame=i)
    for i, (kind, v) in enumerate((("hoplite", 0), ("hoplite", 1), ("priest", 1), ("citizen", 1), ("woman", 0))):
        pl.walker(_w(kind, v, "move", "back"), 72 + i * 6, 88, z=80.0, frame=i)
    pl.walker(_f("pheidias", "work_high"), 116, 94, z=80.0)
    pl.walker(_w("priest", 0, "pour"), 113, 86, z=80.0)
    pl.walker(_f("mnesikles", "gesture"), 68, 88, z=80.0)
    return s


PLAN = {
    "parthenon": (96, 112, 90, 97), "old_temple": (88, 98, 79, 84), "pandroseion": (84, 87, 79, 82),
    "promachos": (80, 81, 84, 85), "propylaia": (66, 75, 81, 91), "nike_bastion": (62, 65, 91, 95),
    "approach": (48, 61, 86, 92), "brauronion": (78, 86, 95, 100), "chalkotheke": (88, 94, 98, 101),
    "great_altar": (114, 116, 84, 86), "zeus_polieus": (116, 120, 79, 83), "sculpt_yard": (113, 121, 88, 98),
    "theatre": (104, 118, 104, 120), "dionysos_temple": (106, 112, 121, 124), "odeion": (120, 132, 102, 115),
    "hephaisteion": (11, 18, 42, 45), "royal_stoa": (20, 21, 31, 35), "stoa_zeus": (20, 23, 38, 48),
    "old_bouleuterion": (20, 25, 50, 55), "tholos": (21, 25, 57, 61), "stoa_poikile": (30, 39, 26, 28),
    "twelve_gods": (34, 35, 31, 32), "tyrannicides": (40, 41, 40, 41), "se_fountain": (46, 49, 58, 61),
    "lawcourt": (30, 36, 57, 62), "horos": (26, 26, 62, 62), "simon_shop": (26, 28, 63, 64),
    "eleusinion": (54, 58, 66, 70),
}
LEVEL = {"parthenon": 10, "old_temple": 10, "pandroseion": 10, "promachos": 10, "propylaia": 10, "nike_bastion": 9,
         "approach": 1, "brauronion": 10, "chalkotheke": 10, "great_altar": 10, "zeus_polieus": 10, "sculpt_yard": 10,
         "hephaisteion": 2, "eleusinion": 2}


# ---------------------------------------------------------------- the Agora

def agora(pieces, floors):
    """The civic square after the map plan: the Kolonos Agoraios with the Hephaisteion, the west
    side buildings, the Painted Stoa, the Panathenaic Way crossing the gravel, plane trees,
    stalls and the morning crowd."""
    pl = Plan(4, 62, 22, 72)
    s = pl.s
    s.floors = floors
    pl.level(2, 6, 19, 32, 58, edge=P + "earth")
    pl.level(2, 53, 59, 65, 71, edge=P + "ashlar")
    pl.paint("gravel", 20, 52, 26, 62)
    pl.paint("rock_limestone", 6, 19, 32, 58)
    pl.paint("packed_earth", 22, 30, 63, 70)
    for name, (c0, c1, r0, r1) in PLAN.items():
        if c0 >= 4 and c1 <= 62 and r0 >= 22 and r1 <= 72:
            pl.place(name, c0, c1, r0, r1, pieces)
    for c, r in ((44, 34), (46, 46), (30, 44), (26, 36), (50, 52), (36, 52)):
        pl.kit("t_plane", c, r, var=f"r{(c + r) % 2}")
    for i, (c, r) in enumerate(((40, 48), (42, 48), (44, 50), (38, 50), (40, 52), (46, 54))):
        pl.kit("g_stall", c, r, var=f"r{i}", fw=1, fh=2)
    pl.kit("g_table_banker", 36, 46, var="r0")
    for c, r in ((14, 60), (10, 62), (16, 30)):
        pl.kit("t_olive", c, r, var=f"r{c % 3}")
    for c, r in ((22, 65), (32, 66)):
        pl.kit("g_house_small", c, r, var=f"r{c % 4}", fw=2, fh=2)
    crowd = [("citizen", 0, 42, 44), ("citizen", 1, 39, 47), ("woman", 0, 43, 52), ("working_woman", 0, 41, 50),
             ("metic", 0, 37, 48), ("enslaved_man", 1, 45, 48), ("scythian", 0, 33, 40), ("scythian", 1, 29, 47),
             ("child", 0, 47, 50), ("citizen", 3, 35, 38), ("philosopher", 0, 34, 27), ("philosopher", 1, 32, 27),
             ("ionian", 0, 44, 38), ("enslaved_woman", 2, 47, 57), ("woman", 1, 48, 57), ("elder", 0, 22, 40)]
    for i, (kind, v, c, r) in enumerate(crowd):
        pl.walker(_w(kind, v, "talk" if kind in ("citizen", "metic", "philosopher") and i % 2 else "idle"), c, r,
                  frame=i)
    pl.walker(_f("socrates", "talk"), 33, 27)
    pl.walker(_f("simon", "stir"), 27, 65)
    pl.walker(_f("nikarete", "serve"), 39, 51)
    pl.walker(_f("sosias", "move"), 50, 44)
    pl.s.actor("critter/athens.donkey/move_front", (44 - 22) * 16 + 4, (62 - 52) * 16 + 4)
    return s


# ---------------------------------------------------------------- a quarter, Piraeus, the procession

def quarter(night=False):
    """A residential block of Melite: courtyard houses in all four rotations along narrow lanes,
    a two-storey house, workshops, a fountain, herms at the doors, a shrine at the crossing."""
    s = SetScene(26, 24, P + "dry_grass", margin=24)
    s.paint(P + "packed_earth", 0, 25, 10, 11)
    s.paint(P + "packed_earth", 12, 13, 0, 23)
    lots = [(1, 1, "g_house", 3, 3, 0), (1, 5, "g_house", 3, 3, 1), (5, 1, "g_house_two", 3, 2, 0),
            (5, 5, "g_house_small", 2, 2, 2), (8, 5, "g_workshop", 2, 2, 0), (1, 14, "g_house", 3, 3, 2),
            (5, 14, "g_house", 3, 3, 3), (1, 18, "g_house_small", 2, 2, 1), (5, 18, "g_house_two", 3, 2, 1),
            (15, 1, "g_house", 3, 3, 1), (19, 1, "g_house", 3, 3, 0), (15, 5, "g_house_small", 2, 2, 3),
            (15, 14, "g_house", 3, 3, 0), (19, 14, "g_farmstead", 3, 3, 0), (15, 18, "g_house_two", 3, 2, 2),
            (19, 18, "g_house_small", 2, 2, 0), (22, 6, "g_fountain", 2, 2, 1)]
    for x, y, iid, fw, fh, r in lots:
        rw, rh = (fw, fh) if r % 2 == 0 else (fh, fw)
        s.add(P + iid, f"r{r}", x, y, rw, rh)
    for x, y, iid, v in ((13, 12, "g_shrine", "r0"), (9, 12, "g_herm", "r1"), (14, 9, "g_herm", "r0"),
                         (9, 2, "g_kiln", "r0"), (10, 3, "g_pots", "r1"), (4, 10, "t_olive", "r1"),
                         (17, 9, "g_well", "r0"), (21, 11, "t_cypress", "r0"), (11, 16, "g_loom", "r0")):
        s.add(P + iid, v, x, y)
    people = [("woman", 0, 12.5, 6), ("enslaved_woman", 2, 23.5, 8.5), ("working_woman", 2, 23, 9.3),
              ("child", 1, 12.6, 15), ("child", 2, 13.2, 15.6), ("citizen", 2, 6, 10.6), ("enslaved_man", 0, 18, 10.5),
              ("potter", 0, 9.5, 4.5), ("herder", 1, 2, 11.3), ("elder", 1, 13.2, 19)]
    for i, (kind, v, x, y) in enumerate(people):
        s.actor(_w(kind, v, "move" if i % 3 else "idle"), x * 16, y * 16, frame=i)
    s.actor("critter/athens.goat/graze_front", 2.6 * 16, 11.8 * 16)
    s.actor("critter/athens.hen/peck_front", 3.0 * 16, 3.0 * 16)
    s.actor("critter/athens.dog_laconian/idle_front", 12.4 * 16, 8 * 16)
    return s


def piraeus(pieces, floors):
    """Piraeus: the Kantharos quay and the Zea sheds on the water, triremes and merchantmen in
    the harbour, the Hippodamian grid behind."""
    s = SetScene(30, 40, P + "dry_grass", margin=20)
    s.floors = floors
    for x in range(30):
        for y in range(40):
            if x >= 18:
                s.over[(x, y)] = "water"
    s.add(P + "harbour", "r0", 8, 2, 10, 18, pieces.get(P + "harbour"))
    s.add(P + "shipsheds", "r0", 12, 22, 6, 16, pieces.get(P + "shipsheds"))
    for i, (x, y) in enumerate(((1, 2), (1, 6), (5, 2), (1, 22), (5, 22), (1, 26), (5, 26), (1, 30), (5, 30))):
        s.add(P + ("g_house" if i % 3 else "g_house_two"), f"r{i % 4}", x, y, 3, 3 if i % 3 else 2)
    s.paint(P + "packed_earth", 0, 7, 20, 21)
    s.actors += [("ship/athens.trireme/v0/row_front", 23 * 16, 10 * 16, 0, False, False, 0),
                 ("ship/athens.merchant/v0/idle_front", 20 * 16, 6 * 16, 0, False, False, 0),
                 ("ship/athens.trireme/v0/move_back", 26 * 16, 26 * 16, 0, False, False, 1),
                 ("ship/athens.fishing/v0/slack_front", 24 * 16, 34 * 16, 0, False, False, 2)]
    for i, (kind, v, x, y) in enumerate((("rower", 0, 16, 6), ("rower", 1, 16.5, 9), ("metic", 1, 14, 4),
                                         ("enslaved_man", 0, 16, 12), ("ionian", 0, 14, 10))):
        s.actor(_w(kind, v, "haul" if kind == "rower" else "idle"), x * 16, y * 16, z=1.6, frame=i)
    s.actor(_f("kephalos", "talk"), 13.5 * 16, 7 * 16)
    return s


def procession():
    """The Panathenaic procession on the Way through the Kerameikos: the marshal, basket-bearers,
    water-carriers, metics in purple with trays and their daughters with sunshade and stool,
    elders with olive branches, musicians, heifers led by youths, the robe, hoplites, the
    horsemen and a chariot, with the crowd along the road."""
    s = SetScene(8, 36, P + "dry_grass", margin=16)
    s.paint(P + "gravel", 2, 5, 0, 35)
    seq = [("marshal", 0), ("kanephoros", 0), ("kanephoros", 1), ("peplos_bearer", 0), ("hydriaphoros", 0),
           ("hydriaphoros", 1), ("skaphephoros", 0), ("skaphephoros", 1), ("metic_daughter", 0), ("metic_daughter", 1),
           ("thallophoros", 0), ("thallophoros", 1), ("musician", 0), ("musician", 1), ("drover", 0), ("drover", 1),
           ("hoplite", 0), ("hoplite", 1), ("hoplite", 2)]
    y = 2.0
    for i, (kind, v) in enumerate(seq):
        s.actor(_w(kind, v, "move", "back"), (3.2 + (i % 2) * 1.2) * 16, y * 16, frame=i)
        if kind == "drover":
            s.actor("critter/athens.heifer/move_back", (3.8 + (i % 2) * 1.2) * 16, (y + 0.8) * 16, frame=i)
            y += 0.8
        y += 1.1
    for i in range(3):
        s.actor(_w("cavalryman", i, "move", "back"), 3.8 * 16, (y + 1.5 + i * 2.2) * 16, frame=i)
    s.actor("cart/athens.chariot/move_back", 3.8 * 16, (y + 9.5) * 16)
    for i, (kind, v) in enumerate((("citizen", 0), ("woman", 1), ("child", 3), ("elder", 1), ("woman", 2),
                                   ("enslaved_woman", 1), ("citizen", 2), ("metic", 2), ("child", 0), ("scythian", 0))):
        s.actor(_w(kind, v), (1.0 if i % 2 else 6.6) * 16, (3 + i * 3.1) * 16)
    for y in (6, 14, 22, 30):
        s.add(P + "g_herm", "r1", 6, y)
        s.add(P + "t_olive", f"r{y % 3}", 7, y + 2)
    return s


def main(build, out_dir):
    from sets.parsa.preview import anim_sheet, item_sheet, walker_sheet
    cat = json.loads((setbuild.SETS / "athens" / "catalog.json").read_text())
    pages = Pages(out_dir, ["athens"], build.k, home=HOME)
    pieces, floors = _geom(out_dir)
    dst = build.previews
    for it in cat["items"]:
        if it.get("landmark"):
            iid = it["id"]
            s = landmark_scene(iid, cat, pieces, walkers=(_w("citizen", 0), _w("hoplite", 0, "guard")))
            s.floors = floors
            save(s.render(pages), dst / "landmarks", iid.split(".")[1], scales=(1,))
    img = acropolis(pieces, floors).render(pages)
    save(img, dst, "acropolis", scales=(1, 0.5))
    save(acropolis(pieces, floors).render(pages, night=True), dst, "acropolis_night", scales=(0.5,))
    save(agora(pieces, floors).render(pages), dst, "agora", scales=(1, 0.5))
    save(quarter().render(pages), dst, "quarter", scales=(1, 2))
    save(quarter().render(pages, night=True), dst, "quarter_night", scales=(1, 2))
    save(piraeus(pieces, floors).render(pages), dst, "piraeus", scales=(1, 0.5))
    save(procession().render(pages), dst, "procession", scales=(1, 2))
    save(walker_sheet(pages, cat, cols=12), dst, "walkers", scales=(1, 2))
    save(anim_sheet(pages, [_w("potter", 0).rsplit("/", 1)[0], _w("hoplite", 0).rsplit("/", 1)[0],
                            _w("athlete", 0).rsplit("/", 1)[0], "figure/athens.socrates", "critter/athens.horse",
                            "cart/athens.cart/v0"]), dst, "animations", scales=(2,))
    kit_ids = [it["id"] for it in cat["items"] if not it.get("landmark") and it["id"].split(".")[1][:2] not in ("t_", "p_")]
    plants = [it["id"] for it in cat["items"] if it["id"].split(".")[1][:2] in ("t_", "p_")]
    save(item_sheet(pages, cat, kit_ids), dst, "kit", scales=(1, 2))
    save(item_sheet(pages, cat, plants), dst, "plants", scales=(1, 2))
    print(f"previews in {dst}")


if __name__ == "__main__":
    quick(sys.argv[1], sys.argv[2:])
