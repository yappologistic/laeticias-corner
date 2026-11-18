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
    if fw > setbuild.MAX_PIECE or fh > setbuild.MAX_PIECE or lm.walk or lm.water:
        return setbuild.make_pieces(fw, fh, set(map(tuple, lm.walk)), set(map(tuple, lm.water)))
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


def quick(out_dir, ids, night=True, save_dir=None):
    out_dir = Path(out_dir)
    save_dir = Path(save_dir or out_dir)
    cat = _cat()
    pages = Pages(out_dir, ["rome"], 2, home=HOME)
    for iid in ids:
        iid = iid if iid.startswith(P) else P + iid
        walkers = [w for w in WALKERS if f"{w}/f0" in pages.rects]
        s = landmark_scene(iid, cat, pages, walkers)
        name = iid.split(".", 1)[1]
        save(s.render(pages), save_dir, name, scales=(1, 2) if save_dir != out_dir else (1,))
        if night:
            save(s.render(pages, night=True), save_dir, name + "_night", scales=(1,))
    print(f"quick looks in {save_dir}")


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
    "trajan_forum": (72, 96, 29, 41), "basilica_ulpia": (74, 94, 24, 28), "trajan_column": (80, 88, 20, 23),
    "trajan_temple": (80, 88, 13, 18), "trajan_markets": (97, 109, 16, 33), "augustus_forum": (98, 110, 34, 46),
    "caesar_forum": (85, 96, 43, 52), "nerva_forum": (111, 114, 41, 52), "pacis": (115, 128, 40, 54),
    "palatine_tiberiana": (100, 112, 78, 84), "domus_flavia": (110, 123, 85, 95),
    "domus_augustana": (113, 126, 96, 104), "palatine_stadium": (127, 132, 86, 104),
    "apollo_palatinus": (101, 106, 91, 96), "house_augustus": (101, 105, 97, 101), "casa_romuli": (99, 99, 102, 102),
    "lupercal": (97, 98, 104, 105), "circus_maximus": (82, 132, 108, 117), "porta_capena": (133, 136, 118, 121),
    "portunus": (70, 71, 96, 98), "hercules_victor": (73, 75, 99, 101), "ara_maxima": (77, 78, 97, 98),
    "tiber_island": (50, 60, 86, 92), "pons_fabricius": (61, 64, 87, 89), "pons_cestius": (46, 49, 89, 91),
    "pons_aemilius": (52, 61, 96, 98), "pons_sublicius": (52, 61, 106, 108), "emporium": (61, 85, 140, 159),
    "horrea_galbana": (67, 84, 151, 156), "testaccio": (86, 96, 148, 158), "trajan_baths": (144, 173, 20, 49),
    "castra_praetoria": (158, 175, 0, 14), "suburban_villa": (150, 166, 140, 154), "synagogue": (24, 28, 104, 107),
    "saepta": (48, 56, 8, 30), "iseum": (58, 64, 14, 22), "stadium_domitian": (12, 21, 2, 26),
    "pompey_theatre": (26, 37, 36, 47),
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


def _w(kind, v=0, anim="idle", facing="front"):
    return f"walker/rome.{kind}/v{v}/{anim}_{facing}"


def _f(fid, anim="idle", facing="front"):
    return f"figure/rome.{fid}/{anim}_{facing}"


def crowd(pl, area, seed, kinds, n):
    """Scatter walkers of `kinds` [(kind, variants, anims)] over plan `area` (c0, c1, r0, r1)."""
    import random
    rng = random.Random(seed)
    c0, c1, r0, r1 = area
    for i in range(n):
        kind, nv, anim = kinds[i % len(kinds)]
        pl.walker(_w(kind, rng.randrange(nv), anim, rng.choice(("front", "back"))), rng.randint(c0, c1),
                  rng.randint(r0, r1), dx=rng.uniform(3, 13), dy=rng.uniform(3, 13), mirror=rng.random() < 0.5,
                  frame=rng.randrange(6))


CROWD = [("citizen", 4, "move"), ("togatus", 3, "talk"), ("matron", 3, "move"), ("working_woman", 4, "move"),
         ("child", 4, "run"), ("enslaved", 4, "carry"), ("senator", 2, "move"), ("freedman", 3, "talk"),
         ("lictor", 2, "move"), ("syrian_merchant", 1, "talk"), ("greek_teacher", 1, "talk")]


def forum(pages):
    """The Capitol, the Forum Romanum, the imperial fora and the Velia after the map plan
    (rome.md §2.3-2.6), the forum crowd and the senators at the Curia."""
    pl = Plan(62, 130, 10, 82)
    pl.level(6, 66, 85, 44, 66)
    pl.level(7, 70, 78, 44, 49)
    pl.paint("tufa_rock", 66, 85, 44, 66)
    pl.paint("travertine_paving", 70, 79, 50, 61)
    pl.paint("travertine_paving", 86, 122, 52, 77)
    pl.paint("basalt_paving", 87, 128, 64, 65)
    pl.paint("basalt_paving", 96, 97, 40, 52)
    pl.paint("basalt_paving", 100, 101, 77, 82)
    pl.level(1, 123, 130, 60, 75, edge=P + "brick")
    pl.level(2, 97, 109, 10, 22, edge=P + "brick")
    pl.paint("travertine_paving", 72, 128, 13, 54)
    pl.paint("basalt_paving", 96, 97, 10, 52)
    pl.place_all(pages)
    crowd(pl, (95, 107, 59, 68), 1, CROWD, 60)
    crowd(pl, (76, 92, 31, 39), 2, CROWD, 30)
    for i, (c, r) in enumerate(((95, 57), (96, 57), (94, 57))):
        pl.walker(_w("senator", i % 2, "move"), c, r)
    pl.walker(_f("hadrian", "gesture"), 100, 62)
    for c in (101, 102):
        pl.walker(_w("lictor", c % 2, "move"), c, 62)
    pl.walker(_f("apollodorus", "gesture"), 84, 24)
    pl.walker(_f("vestalis_maxima", "move"), 115, 70)
    return pl.s


def colosseum_valley(pages):
    """The Velia and the Colosseum valley: the Arch of Titus on the Via Sacra, the building site
    of Venus and Roma, the Colossus, the Meta Sudans and the amphitheatre, crowds at the arches."""
    pl = Plan(118, 175, 54, 92)
    pl.paint("travertine_paving", 143, 175, 62, 90)
    pl.paint("basalt_paving", 118, 147, 69, 70)
    pl.level(1, 118, 143, 58, 76, edge=P + "brick")
    pl.place_all(pages)
    crowd(pl, (140, 175, 86, 91), 3, CROWD, 40)
    crowd(pl, (120, 145, 68, 71), 4, CROWD, 16)
    for i in range(8):
        pl.walker(_w("builder", i % 3, "work_high"), 128 + i * 2, 74)
    return pl.s


def _houses(pl, pages, area, seed, kinds=("r_insula", "r_insula_low", "r_insula_corner", "r_domus")):
    """Fill a plan area with blocks of houses on a grid of lanes, skipping landmark footprints."""
    import random
    rng = random.Random(seed)
    c0, c1, r0, r1 = area
    taken = set()
    for (it, var, tx, ty, fw, fh, pieces, f) in pl.s.items:
        for x in range(tx - 1, tx + fw + 1):
            for y in range(ty - 1, ty + fh + 1):
                taken.add((x, y))
    sizes = {"r_insula": (4, 3), "r_insula_low": (3, 2), "r_insula_corner": (3, 3), "r_domus": (5, 4),
             "r_horrea": (4, 4), "r_bath_small": (4, 3), "r_bakery": (3, 2), "r_villa_farm": (3, 3)}
    r = r0
    while r <= r1 - 3:
        c = c1
        while c >= c0 + 3:
            kind = rng.choice(kinds)
            rot = rng.choice((0, 3))
            fw, fh = sizes[kind]
            dc, dr = (fw, fh) if rot % 2 == 0 else (fh, fw)       # plan extents (c, r)
            x, y = pl.t(c, r)
            cells = {(x + i, y + j) for i in range(dr) for j in range(dc)}
            if not cells & taken and c - dc + 1 >= c0 and r + dr - 1 <= r1:
                pl.s.add(P + kind, f"r{rot}", x, y, dr, dc)
                taken |= {(a + i, b + j) for (a, b) in cells for i in (-1, 0, 1) for j in (-1, 0, 1)}
            c -= dc + 1
        r += 5


def campus(pages):
    """The southern Campus Martius: the Pantheon's dome behind its forecourt, the Baths of
    Agrippa with their pool, the Temple of Matidia, the Porticus Octaviae and the Theatre of
    Marcellus, apartment blocks between, the Tiber on the west."""
    pl = Plan(0, 72, 0, 84)
    pl.paint("river_tiber", 0, 7, 0, 40)
    pl.paint("river_tiber", 8, 22, 34, 58)
    pl.paint("river_tiber", 18, 40, 56, 72)
    pl.paint("river_tiber", 36, 46, 70, 84)
    pl.paint("river_tiber", 22, 32, 30, 35)
    pl.paint("travertine_paving", 34, 46, 0, 22)
    pl.paint("basalt_paving", 62, 64, 0, 84)
    pl.place_all(pages)
    _houses(pl, pages, (8, 72, 0, 84), 5)
    crowd(pl, (34, 46, 2, 7), 6, CROWD, 18)
    crowd(pl, (47, 70, 0, 84), 7, CROWD, 24)
    return pl.s


def baths(pages):
    """The Baths of Trajan on the Oppian at level 2, with houses round their precinct."""
    pl = Plan(138, 177, 14, 55)
    pl.level(2, 138, 177, 14, 55, edge=P + "brick")
    pl.place_all(pages)
    _houses(pl, pages, (138, 177, 14, 55), 9)
    return pl.s


def palatine_circus(pages):
    """The Palatine with its palaces over brick substructures, the Hut of Romulus and the
    Lupercal, and below them the Circus Maximus with a race on the track."""
    pl = Plan(80, 140, 76, 122)
    pl.level(6, 98, 136, 78, 106, edge=P + "brick")
    pl.paint("travertine_paving", 98, 136, 78, 106)
    pl.place_all(pages)
    crowd(pl, (100, 130, 82, 104), 8, [("praetorian", 2, "guard"), ("togatus", 3, "move"), ("matron", 3, "move"),
                                       ("enslaved", 4, "carry")], 24)
    for i in range(4):       # a race: four teams in the faction colours down the north lane
        pl.walker(f"cart/rome.racing_chariot/v{i}/move_back", 118 - i * 4, 110 + (i % 2), frame=i)
    pl.walker(_f("diocles"), 131, 116)
    pl.walker(_f("sabina", "talk"), 118, 92)
    pl.walker(_f("mesomedes", "play"), 120, 92)
    return pl.s


def street(pages, night=False):
    """A street of the Subura: insulae with shops, a corner block, a bakery and a hot-food
    counter, a street fountain and a crossroads shrine, the life of the street (or the carts,
    the watch and the lamps of the night)."""
    s = SetScene(26, 30, "rome.grass_spring", margin=24)
    s.paint("rome.basalt_paving", 0, 25, 13, 15)
    s.paint("rome.packed_earth", 11, 13, 0, 29)
    s.paint("rome.basalt_paving", 11, 13, 13, 15)
    s.add(P + "r_insula", "r0", 1, 8, 3, 4)
    s.add(P + "r_insula_corner", "r0", 7, 9, 3, 3)
    s.add(P + "r_insula", "r0", 15, 8, 3, 4)
    s.add(P + "r_bakery", "r0", 21, 10, 2, 3)
    s.add(P + "r_insula_low", "r0", 1, 2, 2, 3)
    s.add(P + "r_thermopolium", "r0", 5, 12, 1, 1)
    s.add(P + "r_taberna", "r2", 4, 12, 1, 1)
    s.add(P + "r_taberna", "r5", 6, 12, 1, 1)
    s.add(P + "r_insula", "r3", 1, 17, 4, 3)
    s.add(P + "r_domus", "r3", 16, 17, 5, 4)
    s.add(P + "r_insula_corner", "r3", 7, 17, 3, 3)
    s.add(P + "r_bath_small", "r3", 22, 17, 4, 3)
    s.add(P + "r_lacus", "r0", 14, 16, 1, 1, frame=0)
    s.add(P + "r_compitum", "r0", 10, 12, 1, 1)
    s.add(P + "r_stall", "r1", 18, 14, 1, 2, frame=0)
    s.add(P + "r_vigiles", "r0", 1, 24, 2, 3)
    s.add(P + "r_lamp", "r0", 4, 16, 1, 1)
    s.add(P + "t_plane", "r0", 12, 22, 1, 1)
    import random
    rng = random.Random(9)
    if night:
        kinds = [("vigil", 2, "move"), ("carter", 2, "move")]
        for i in range(6):
            k_, nv, a = kinds[i % 2]
            s.actor(_w(k_, i % nv, a, rng.choice(("front", "back"))), rng.uniform(2, 24) * 16, rng.uniform(13.2, 15.6) * 16,
                    frame=i)
        s.actor("cart/rome.cart/v0/move_front", 6 * 16, 14.5 * 16, frame=1)
    else:
        kinds = CROWD + [("baker", 1, "carry"), ("docker", 3, "carry"), ("working_woman", 4, "carry")]
        for i in range(34):
            k_, nv, a = kinds[i % len(kinds)]
            on_street = rng.random() < 0.8
            x = rng.uniform(1, 25) if on_street else rng.uniform(11.2, 13.8)
            y = rng.uniform(13.2, 15.8) if on_street else rng.uniform(1, 28)
            s.actor(_w(k_, rng.randrange(nv), a, rng.choice(("front", "back"))), x * 16, y * 16,
                    mirror=rng.random() < 0.5, frame=rng.randrange(6))
        s.actor(_w("working_woman", 0, "carry"), 14.6 * 16, 17.2 * 16)
        s.actor(_f("claudia_helpis", "serve"), 5.5 * 16, 13.4 * 16)
        s.actor(_f("juvenal", "talk"), 9 * 16, 14.4 * 16)
        s.actor(_f("felicula", "kneel"), 15.2 * 16, 15.4 * 16)
        s.actor("critter/rome.cat/sleep_front", 4.5 * 16, 13.3 * 16)
        s.actor("critter/rome.dog/idle_front", 20.4 * 16, 15.4 * 16)
        s.actor("critter/rome.donkey/move_front", 17 * 16, 14 * 16, frame=2)
    return s


def tiber(pages):
    """The Tiber with the island, its bridges and the Forum Boarium: the round temple of
    Hercules and the temple of Portunus, barges towed up to the quays."""
    pl = Plan(40, 90, 80, 112)
    pl.paint("river_tiber", 46, 49, 80, 112)
    pl.paint("river_tiber", 61, 64, 80, 95)
    pl.paint("river_tiber", 49, 61, 80, 85)
    pl.paint("river_tiber", 49, 61, 93, 112)
    pl.paint("river_tiber", 50, 60, 85, 93)
    pl.paint("mud_bank", 44, 45, 80, 112)
    pl.paint("travertine_paving", 66, 80, 94, 104)
    pl.place_all(pages)
    for r in range(99, 112, 3):
        pl.kit("quay", 62, r, "r1")
    pl.kit("p_reeds", 45, 84, "r0", frame=0)
    pl.kit("p_reeds", 45, 103, "r1", frame=1)
    pl.s.actor("ship/rome.barge/v0/move_front", (102 - 80) * 16 + 8, (90 - 55) * 16 + 8, frame=1)
    pl.s.actor("ship/rome.barge/v0/idle_front", (109 - 80) * 16 + 8, (90 - 58) * 16 + 4)
    for i in range(3):
        pl.walker(_w("hauler", i % 2, "haul"), 63 - 0 * i, 92 - i * 2 + 10)
    crowd(pl, (66, 80, 94, 104), 10, CROWD + [("docker", 3, "carry")], 26)
    pl.walker(_f("soranus", "talk"), 55, 89)
    return pl.s


def emporium_scene(pages):
    """The Emporium: the quay with barges and dockers, the Porticus Aemilia, the Horrea
    Galbana and Monte Testaccio."""
    pl = Plan(52, 100, 136, 159)
    pl.paint("river_tiber", 52, 60, 136, 159)
    pl.place_all(pages)
    for i, r in enumerate((142, 147, 152, 157)):
        pl.s.actor("ship/rome.barge/v0/idle_front", (r - 136) * 16, (100 - 58) * 16 + 4 * i, frame=i)
    crowd(pl, (61, 66, 140, 159), 11, [("docker", 3, "carry"), ("egyptian_sailor", 1, "haul"),
                                       ("enslaved", 4, "carry"), ("freedman", 3, "talk")], 30)
    pl.walker(_f("apion", "haul"), 63, 146)
    pl.walker(_f("aelius_eutyches", "write"), 66, 150)
    return pl.s


def portus(pages):
    """Portus: Trajan's hexagonal basin with ships at the quays, the lighthouse, and pieces of
    Ostia (the Square of the Guilds, the Capitolium, insulae and warehouses)."""
    s = SetScene(36, 44, "rome.grass_spring", margin=24)
    s.paint("rome.travertine_paving", 0, 35, 22, 43)
    s.add(P + "portus_hexagon", "r0", 0, 0, 18, 20, _pieces(P + "portus_hexagon"))
    s.add(P + "portus_lighthouse", "r0", 20, 2, 3, 3)
    s.add(P + "ostia_guilds", "r0", 22, 24, 6, 12, _pieces(P + "ostia_guilds"))
    s.add(P + "ostia_capitolium", "r0", 22, 38, 6, 4)
    for (x, y, k_, var, fw, fh) in ((30, 24, "r_insula", "r0", 3, 4), (30, 30, "r_insula", "r0", 3, 4),
                                    (30, 36, "r_horrea", "r0", 4, 4), (25, 2, "r_horrea", "r0", 4, 4),
                                    (25, 8, "r_insula_corner", "r0", 3, 3), (31, 8, "r_insula_low", "r3", 3, 2)):
        s.add(P + k_, var, x, y, fw, fh)
    for i, (x, y) in enumerate(((19.0, 9.0), (20.5, 14.0))):      # moored outside the basin's footprint
        s.actor("ship/rome.merchantman/v0/idle_front", x * 16, y * 16, frame=i)
    s.actor("ship/rome.merchantman/v0/move_front", 26 * 16, 16 * 16, frame=2)
    import random
    rng = random.Random(12)
    for i in range(24):
        k_, nv, a = [("docker", 3, "carry"), ("egyptian_sailor", 1, "move"), ("freedman", 3, "move"),
                     ("citizen", 4, "move")][i % 4]
        s.actor(_w(k_, rng.randrange(nv), a, rng.choice(("front", "back"))), rng.uniform(18, 35) * 16,
                rng.uniform(22, 43) * 16, frame=i)
    return s


def walker_sheet(pages):
    from sets.parsa.preview import walker_sheet as sheet
    return sheet(pages, _cat())


def terrain_sheet(pages):
    """Every terrain in a strip, with each face material under a raised block."""
    ids = [t["id"] for t in _cat()["terrain"] if not t.get("base")]
    s = SetScene(6 * len(ids) + 2, 10, "rome.grass_spring", margin=24)
    for i, tid in enumerate(ids):
        s.paint(tid, 1 + i * 6, 4 + i * 6, 1, 8)
    for i, e in enumerate(_cat()["art"]["edges"]):
        s.raise_(3, 2 + i * 8, 5 + i * 8, 8, 9, edge=e)
    return s


def kit_sheet(pages, prefix=("r_", "tomb", "mutatio", "stair", "quay"), rotations=True):
    """Every kit item in each of its looks, in rows, on a travertine-paved strip."""
    items = [i for i in _cat()["items"] if not i.get("landmark") and i["id"].split(".", 1)[1].startswith(prefix)
             and i["layout"] != "connect"]
    rows, x, y, rh = [], 1, 1, 0
    width = 64
    for it in items:
        fw, fh = it["footprint"]
        looks = it["count"] if (rotations or it["layout"] == "variant") else 1
        for k_ in range(looks):
            w_, h_ = (fw, fh) if k_ % 2 == 0 or it["layout"] == "variant" else (fh, fw)
            if y + w_ + 1 > width:
                y, x, rh = 1, x + rh + 1, 0
            rows.append((it["id"], f"r{k_}", x, y, w_, h_))
            y += w_ + 1
            rh = max(rh, h_)
    s = SetScene(x + rh + 2, width, "rome.grass_spring", margin=20)
    for iid, var, tx, ty, w_, h_ in rows:
        s.paint("rome.travertine_paving", tx, tx + h_ - 1, ty, ty + w_ - 1)
        s.add(iid, var, tx, ty, h_, w_)
    return s


def aqueduct_strip(pages):
    """The Aqua Claudia arcade crossing fields: a run with a corner and an end."""
    s = SetScene(14, 22, "rome.grass_spring", margin=20)
    s.paint("rome.field_spring", 0, 13, 0, 21)
    s.paint("rome.basalt_paving", 0, 13, 8, 8)            # a street passing under one arch
    path = [(6, y) for y in range(1, 15)] + [(x, 14) for x in range(7, 12)]
    cells = set(path)
    for (x, y) in path:
        m = sum(b for b, (dx, dy) in ((1, (0, -1)), (2, (1, 0)), (4, (0, 1)), (8, (-1, 0))) if (x + dx, y + dy) in cells)
        s.add("rome.aqua_claudia", f"m{m}", x, y)
    for i, y in enumerate((3, 9, 17)):
        s.add("rome.t_stone_pine", f"r{i % 3}", 10, y)
    return s


def main(build, out_dir):
    """Read the pages in `out_dir`, write the previews to the build's preview folder."""
    pages = Pages(Path(out_dir), ["rome"], 2, home=HOME)
    page_dir, out_dir = Path(out_dir), Path(build.previews if build is not None else out_dir)
    save(terrain_sheet(pages).render(pages), out_dir, "terrain", scales=(1, 2))
    f = forum(pages)
    save(f.render(pages), out_dir, "forum", scales=(1, 0.5))
    save(f.render(pages, night=True), out_dir, "forum_night", scales=(0.5,))
    for name, scene, scales in (("colosseum_valley", colosseum_valley, (1, 0.5)), ("campus", campus, (1, 0.5)),
                                ("palatine_circus", palatine_circus, (1, 0.5)), ("tiber", tiber, (1, 0.5)),
                                ("emporium", emporium_scene, (1, 0.5)), ("portus", portus, (1, 0.5)),
                                ("aqueduct", aqueduct_strip, (1, 2)), ("baths", baths, (1, 0.5))):
        save(scene(pages).render(pages), out_dir, name, scales=scales)
    save(street(pages).render(pages), out_dir, "street", scales=(1, 2))
    save(street(pages, night=True).render(pages, night=True), out_dir, "street_night", scales=(1, 2))
    walker_sheet(pages).convert("RGB").save(out_dir / "walkers_2x.png")
    save(kit_sheet(pages).render(pages), out_dir, "kit", scales=(1,))
    save(kit_sheet(pages, prefix=("t_", "p_"), rotations=False).render(pages), out_dir, "plants", scales=(1, 2))
    quick(page_dir, [i["id"] for i in _cat()["items"] if i.get("landmark")], night=False,
          save_dir=out_dir / "landmarks")


if __name__ == "__main__":
    if sys.argv[2:3] == ["--scenes"]:
        main(None, sys.argv[1])
    else:
        quick(sys.argv[1], sys.argv[2:])
