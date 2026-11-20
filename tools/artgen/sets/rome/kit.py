"""The Rome kit (rome.md §3.3, §3.1, §6.3): apartment blocks (insulae) after the 2nd-century
blocks at Ostia, a corner block and a two-storey shop-house, the domus with its atrium and
peristyle, shop fronts by trade, a hot-food counter, the bakery with donkey mills and its oven,
the fullery, dyer, glass-blower and smithy, street fountains, crossroads shrines of the Lares,
a latrine, a neighbourhood bath, warehouses, a treadwheel crane, scaffolding, milestones,
market stalls, amphora stacks by origin, honorific statues and columns, lamps, braziers,
altars, tombs and columbaria, pergolas, wells, the watch-station of the vigiles, a farmstead
and shed for the Campagna, the relay station of the Via Appia, a travertine stair and quay,
and the Aqua Claudia's arcade as a joined item. Toy scale like the other kits (an adult 38-42
px); rotatable pieces face +y (their front is the lower-left face the camera sees at r0) and
every side differs, so the four rotations read as four different buildings."""

import math

import numpy as np

import waterworks

import materials as M
import roman as RM
from arch import carve, ellipsoid, face_box, fill, flight, halo, revolve, rod, slab
from models.nature import leaf_mass
from setbuild import Item
from sets.rome.common import FIRE, LAMP, TOGATE, cypress, laurel, stone_pine, treadwheel_crane
from sets.rome.ground import amphora
from voxel import Model, hash01, value_noise

T = 16
GROUND = 14.0          # height of a shop storey
STOREY = 12.0          # height of an apartment storey
SHUTTER = ("wood", "green_paint", "red_paint", "wood_light")


def _m(fw, fh, top, k, below=0, pad=4):
    return Model.empty(-pad, fw * T + pad, -pad, fh * T + pad, -below, top, k=k)


# ---------------------------------------------------------------- shop fronts and storeys

TRADES = ("baker", "wine", "oil", "cloth", "pottery", "lamp", "shoes", "books")


def shopfront(m, face, box, s0, w, h, trade, seed, open_=1.0):
    """A taberna opening: a wide doorway under a brick lintel arch, a masonry counter, the wooden
    shutter boards standing folded aside, goods by trade, a painted sign above, a lamp."""
    x0, x1, y0, y1 = box[:4]
    carve(m, face_box(face, x0, x1, y0, y1, 0.0, h, s0, s0 + w, -0.1, 7.0))
    fill(m, face_box(face, x0, x1, y0, y1, 0.0, 0.6, s0, s0 + w, -0.6, 7.0), "travertine", tone=0.25)
    fill(m, face_box(face, x0, x1, y0, y1, h, h + 1.2, s0 - 0.6, s0 + w + 0.6, -0.4, 0.2), "brick",
         tone=lambda X, Y, Z: 0.4 - 0.8 * ((((X + Y) * 2.0) % 1.0) < 0.3))
    fill(m, face_box(face, x0, x1, y0, y1, 0.0, h, s0 + w - 0.2, s0 + w + 0.0, 0.0, 7.0), "ink")
    fill(m, face_box(face, x0, x1, y0, y1, 0.0, 5.5, s0 + 0.5, s0 + w * 0.55, 1.2, 3.2), "brick" if seed % 2 else
         "whitewash", tone=0.15)
    fill(m, face_box(face, x0, x1, y0, y1, 5.5, 6.0, s0 + 0.3, s0 + w * 0.6, 1.0, 3.4), "marble", tone=0.3)
    for i in range(int(3 * open_)):        # the shutter boards stacked against the jamb
        fill(m, face_box(face, x0, x1, y0, y1, 0.0, h - 0.4, s0 + w - 1.8 + i * 0.4, s0 + w - 1.4 + i * 0.4, 0.4,
                         1.4 + i * 0.3), "wood", tone=-0.2 + 0.15 * i)
    sign = ("ochre", "cinnabar", "whitewash", "eblue")[seed % 4]
    fill(m, face_box(face, x0, x1, y0, y1, h + 1.4, h + 3.4, s0 + 1.0, s0 + w - 1.0, -0.2, 0.1), sign, tone=0.1)
    RM.inscription(m, face, box, s0 + 1.6, s0 + w - 1.6, h + 1.8, h + 3.0, "cinnabar" if sign != "cinnabar" else "ink")
    gx = lambda s, d: RM.face_point(face, box, s, d)
    if trade == "baker":
        for i in range(4):
            x, y = gx(s0 + 1.5 + i * 1.3, 2.2)
            ellipsoid(m, (x, y, 6.6), (0.6, 0.6, 0.45), "ochre", 0.3)
    elif trade in ("wine", "oil"):
        for i in range(3):
            x, y = gx(s0 + w * 0.7 + i * 0.1, 3.0 + i * 1.6)
            amphora(m, x, y, 0.6, "wine" if trade == "wine" else "dressel20")
    elif trade == "cloth":
        for i in range(3):
            x, y = gx(s0 + 1.2 + i * 1.8, 2.2)
            slab(m, x - 0.8, x + 0.8, y - 0.8, y + 0.8, 6.0, 7.4, ("cinnabar", "saffron", "eblue")[i], tone=0.2)
        a, b = gx(s0 + 0.5, 0.6), gx(s0 + w - 0.5, 0.6)
        rod(m, (a[0], a[1], h - 0.8), (b[0], b[1], h - 0.8), 0.2, "wood")
        x, y = gx(s0 + w * 0.4, 0.8)
        slab(m, x - 1.0, x + 1.0, y - 0.3, y + 0.3, h - 6.0, h - 0.8, "purple", tone=0.1)
    elif trade == "pottery":
        for i in range(4):
            x, y = gx(s0 + 1.2 + i * 1.4, 2.2)
            ellipsoid(m, (x, y, 6.8), (0.6, 0.6, 0.8), ("terracotta", "clay", "cinnabar")[i % 3], 0.3)
    elif trade == "lamp":
        for i in range(5):
            x, y = gx(s0 + 1.0 + i * 1.0, 2.2)
            ellipsoid(m, (x, y, 6.3), (0.45, 0.3, 0.25), "clay", 0.3)
        x, y = gx(s0 + w / 2, 1.0)
        fill(m, (x - 0.5, x + 0.5, y - 0.5, y + 0.5, h - 3.0, h - 2.0), "lamp")
        halo(m, x, y, h - 2.5, 8.0, LAMP, 0.7)
    elif trade == "shoes":
        for i in range(4):
            x, y = gx(s0 + 1.0 + i * 1.5, 0.8)
            rod(m, (x, y, h - 1.0), (x, y, h - 3.4), 0.35, "leather", 0.1)
    elif trade == "books":
        for i in range(3):
            x, y = gx(s0 + 1.0 + i * 1.8, 2.2)
            rod(m, (x - 0.8, y, 6.4), (x + 0.8, y, 6.4), 0.5, "linen", 0.3)
        a, b = gx(s0 + 0.5, 6.4), gx(s0 + w - 0.5, 6.4)
        for z in (2.0, 5.0, 8.0):
            slab(m, min(a[0], b[0]) - 0.3, max(a[0], b[0]) + 0.3, min(a[1], b[1]) - 0.3, max(a[1], b[1]) + 0.3,
                 z, z + 0.4, "wood", 0.0)
    x, y = gx(s0 - 0.8, -0.4)
    fill(m, (x - 0.4, x + 0.4, y - 0.4, y + 0.4, h - 3.0, h - 2.2), "lamp")
    halo(m, x, y, h - 2.6, 6.0, LAMP, 0.45, kind="door")


def windows(m, face, box, z, n, w=2.4, h=3.6, s_pad=3.0, seed=0, lit=0.35, glass=False):
    """A row of windows with wooden shutters folded back, some lit at night."""
    L = RM.face_length(face, *box[:4])
    if n <= 0:
        return
    step = (L - 2 * s_pad) / n
    for i in range(n):
        s0 = s_pad + (i + 0.5) * step - w / 2
        RM.window(m, face, box, s0, w, z, h, shutter=SHUTTER[(seed + i) % 4] if (seed + i) % 3 else None,
                  lit=lit if hash01(seed, i, 5) < 0.55 else 0.0, glass=glass and i % 2 == 0)


def balcony(m, face, box, z, s0, s1, seed=0, laundry=True):
    """A wooden balcony (maenianum) on brick corbels with a plank railing, laundry on a line."""
    x0, x1, y0, y1 = box[:4]
    for s in np.arange(s0 + 1.0, s1, 4.0):
        fill(m, face_box(face, x0, x1, y0, y1, z - 1.6, z, s - 0.6, s + 0.6, -3.0, 0.0), "brick", tone=0.1)
    fill(m, face_box(face, x0, x1, y0, y1, z, z + 0.7, s0, s1, -3.4, 0.0), "wood_light", tone=M.timber("x", seed))
    fill(m, face_box(face, x0, x1, y0, y1, z + 0.7, z + 3.4, s0, s1, -3.4, -3.0), "wood",
         lambda X, Y, Z: (((X + Y) % 1.6) < 0.6) | (Z > z + 2.8), tone=0.0)
    if laundry:
        for i, s in enumerate(np.arange(s0 + 1.5, s1 - 1.5, 3.0)):
            fill(m, face_box(face, x0, x1, y0, y1, z + 3.0, z + 5.6, s, s + 2.0, -3.6, -3.2),
                 ("linen", "cinnabar", "saffron", "eblue", "linen")[(i + seed) % 5], tone=0.2)
        a = RM.face_point(face, box, s0, 3.4)
        b = RM.face_point(face, box, s1, 3.4)
        rod(m, (a[0], a[1], z + 5.8), (b[0], b[1], z + 5.8), 0.12, "wood")


def _block(m, box, z0, z1, seed, finish="brick"):
    if finish == "brick":
        RM.wall(m, box, z0, z1, "brick", seed)
    else:
        RM.wall(m, box, z0, z1, "stucco", seed, finish)
        fill(m, (*box, z0, z0 + 1.6), "brick", tone=RM.brick(seed), only_solid=True)


def _string(m, box, z, mat="brick"):
    x0, x1, y0, y1 = box[:4]
    slab(m, x0 - 0.5, x1 + 0.5, y0 - 0.5, y1 + 0.5, z, z + 0.8, mat, tone=0.3)


# ---------------------------------------------------------------- insulae and houses

def r_insula(v, frame, frames, k):
    """An insula (rome.md §3.1, after the 2nd-century blocks at Ostia): five storeys of
    brick-faced concrete, Trajan's height limit of 60 feet; tabernae with shutters and painted
    signs round the ground floor, the mezzanine windows over them, the brick-pedimented
    entrance to the stairs, a wooden balcony with laundry on the first floor, windows with
    shutters above, a light well in the middle, a low tiled roof. The street side (+y) has the
    shops and balcony, the east side more shops, the back small windows and a latrine chute,
    the north side a plastered stair tower painted in ochre."""
    m = _m(4, 3, 76, k)
    box = (2.0, 62.0, 2.0, 46.0)
    zt = GROUND + 6.0 + 3 * STOREY
    _block(m, box, 0.0, zt, 1001)
    carve(m, (22.0, 42.0, 16.0, 32.0, GROUND + 6.0, zt + 1.0))       # the light well
    fill(m, (22.0, 42.0, 16.0, 32.0, GROUND + 5.0, GROUND + 6.0), "brick", tone=-0.3)
    for i, s0 in enumerate((3.0, 13.0, 37.0, 47.0)):
        shopfront(m, "+y", box, s0, 8.5, GROUND - 2.0, TRADES[(i + v) % 8], 1002 + i)
    fill(m, face_box("+y", *box, 0.0, GROUND, 26.0, 34.0, -0.6, 0.2), "travertine", tone=0.2)
    carve(m, face_box("+y", *box, 0.0, GROUND - 3.0, 27.5, 32.5, -0.7, 5.0))
    fill(m, face_box("+y", *box, GROUND - 2.6, GROUND + 0.4, 25.0, 35.0, -0.9, 0.2), "brick",
         lambda X, Y, Z: Z < GROUND + 0.4 - np.abs(X - 32.0) * 0.5, tone=0.35)
    for i, s0 in enumerate((4.0, 16.0, 28.0)):
        shopfront(m, "+x", box, s0, 8.5, GROUND - 2.0, TRADES[(i + v + 4) % 8], 1006 + i)
    _string(m, box, GROUND)
    for f in ("+y", "+x", "-y", "-x"):
        windows(m, f, box, GROUND + 1.5, 6 if f in ("+y", "-y") else 4, w=1.8, h=2.2, seed=1010 + len(f))
        for j in range(3):
            z = GROUND + 6.0 + j * STOREY + 3.0
            n = (6 if f in ("+y", "-y") else 4) - (1 if j == 2 else 0)
            windows(m, f, box, z, n, seed=1020 + j * 7 + ord(f[1]), lit=0.4)
    _string(m, box, GROUND + 6.0)
    balcony(m, "+y", box, GROUND + 6.0, 3.0, 57.0, seed=1030)
    _string(m, box, GROUND + 6.0 + STOREY * 2)
    # The north side: a stair tower of the same brick-faced concrete, set into the block and
    # rising a little over it, lit by slit windows (a thin plastered slab standing proud of the
    # face read as a flat yellow post in every turned look, V7-011).
    box_t = (2.0, 14.0, -1.0, 3.0)
    _block(m, box_t, 0.0, zt + 4.0, 1031)
    for j in range(4):
        windows(m, "-y", box_t, GROUND + 2.0 + j * STOREY, 1, w=1.0, h=2.4, seed=1034 + j)
    RM.hip(m, (1.0, 15.0, -2.0, 4.0), zt + 4.0, 3.0, seed=1032)
    # The back: a latrine chute and soot over a cook-shop's vent.
    slab(m, 46.0, 50.0, 46.0, 48.0, 0.0, zt, "terracotta", tone=0.1)
    RM.hip(m, (0.5, 63.5, 0.5, 47.5), zt, 7.0, seed=1033)
    carve(m, (22.0, 42.0, 16.0, 32.0, zt - 1.0, zt + 8.0))
    return m


def r_insula_corner(v, frame, frames, k):
    """A corner insula of four storeys: a continuous wooden balcony round both street sides on
    brick corbels, shops on two sides with a corner pier, a painted stucco upper part, a small
    roof terrace with plants in pots."""
    m = _m(3, 3, 72, k)
    box = (2.0, 46.0, 2.0, 46.0)
    zt = GROUND + 2 * STOREY + 10.0
    _block(m, box, 0.0, GROUND + 4.0, 1101)
    _block(m, box, GROUND + 4.0, zt, 1102, "stucco_red" if v % 2 else "ochre")
    for i, s0 in enumerate((3.0, 14.0, 26.0)):
        shopfront(m, "+y", box, s0, 8.5, GROUND - 2.0, TRADES[(i + v + 2) % 8], 1103 + i)
        shopfront(m, "+x", box, s0 + 4.0, 8.5, GROUND - 2.0, TRADES[(i + v + 5) % 8], 1106 + i)
    _string(m, box, GROUND + 4.0)
    balcony(m, "+y", box, GROUND + 4.0, 1.0, 44.0, seed=1109)
    balcony(m, "+x", box, GROUND + 4.0, 1.0, 44.0, seed=1110, laundry=False)
    for f in ("+y", "+x", "-y", "-x"):
        for j in range(2):
            windows(m, f, box, GROUND + 7.0 + j * STOREY, 4, seed=1111 + j + ord(f[1]), lit=0.4)
    RM.hip(m, (0.5, 47.5, 0.5, 30.0), zt, 6.0, seed=1112)
    fill(m, (0.5, 47.5, 30.0, 47.5, zt - 0.5, zt + 0.5), "brick", tone=-0.1)
    for x in (10.0, 24.0, 38.0):
        revolve(m, x, 38.0, zt + 0.5, zt + 2.5, lambda t: 1.3, "terracotta", tone=0.2)
        leaf_mass(m, [(x, 38.0, zt + 4.0, 2.0)], 1113 + int(x), materials=(("leaf", 1.0),), under="leaf_dark")
    return m


def r_insula_low(v, frame, frames, k):
    """A two-storey shop-house: a taberna on the street with the family's room over it reached
    by a wooden stair inside, a tiled roof, a pergola and a hen run behind."""
    m = _m(3, 2, 52, k)
    box = (2.0, 46.0, 2.0, 28.0)
    zt = GROUND + STOREY + 2.0
    _block(m, box, 0.0, zt, 1201, "brick" if v % 2 == 0 else "whitewash")
    shopfront(m, "+y", box, 3.0, 9.0, GROUND - 2.0, TRADES[v % 8], 1202)
    shopfront(m, "+y", box, 20.0, 9.0, GROUND - 2.0, TRADES[(v + 3) % 8], 1203)
    fill(m, face_box("+y", *box, 0.0, GROUND - 3.0, 34.0, 39.0, -0.2, 2.0), "wood", tone=-0.2)
    _string(m, box, GROUND)
    windows(m, "+y", box, GROUND + 3.0, 3, seed=1204)
    windows(m, "+x", box, GROUND + 3.0, 2, seed=1205)
    windows(m, "-y", box, GROUND + 3.0, 2, seed=1206)
    RM.gable(m, (0.5, 47.5, 0.5, 29.5), zt, 6.0, "x", seed=1207)
    for x in (6.0, 18.0, 30.0):
        rod(m, (x, 30.0, 0.0), (x, 30.0, 10.0), 0.4, "wood")
    rod(m, (6.0, 30.0, 10.0), (30.0, 30.0, 10.0), 0.3, "wood")
    leaf_mass(m, [(12.0, 30.0, 10.5, 3.0), (24.0, 30.0, 10.5, 3.0)], 1208, materials=(("leaf", 0.7), ("leaf_light", 0.3)),
              under="leaf_dark", squash=0.6)
    return m


def r_domus(v, frame, frames, k):
    """A domus (rome.md §3.1): blank walls on the street, painted red below and white above,
    with shops let out at the front corners; the door between two pilasters under a little
    pediment; inside the atrium under a roof sloping inward to its square opening over the
    pool (impluvium), and at the back the peristyle garden with columns, box, roses and a
    fountain; laurels at the door."""
    m = _m(5, 4, 44, k)
    box = (2.0, 78.0, 2.0, 62.0)
    H = 18.0
    RM.wall(m, box, 0.0, H, "stucco", 1301, "whitewash")
    fill(m, (*box, 0.0, 5.0), "stucco_red", tone=0.0, only_solid=True)
    carve(m, (4.0, 76.0, 4.0, 60.0, 0.5, H + 1.0))
    fill(m, (4.0, 76.0, 4.0, 60.0, 0.0, 0.5), "marble", tone=M.paving(4.0, 4.0, 1302))
    # Rooms round the atrium (front half) under inward-sloping roofs.
    for rb in ((4.0, 40.0, 40.0, 60.0), (4.0, 14.0, 4.0, 40.0), (30.0, 40.0, 4.0, 40.0)):
        RM.wall(m, rb, 0.0, H - 2.0, "stucco", 1303, "whitewash")
    for rb, up in (((2.0, 42.0, 38.0, 62.0), "-y"), ((2.0, 16.0, 2.0, 38.0), "+x"), ((28.0, 42.0, 2.0, 38.0), "-x")):
        RM.lean_to(m, rb, H - 4.0, H + 2.0, {"-y": "+y", "+x": "-x", "-x": "+x"}[up], "terracotta", 1304)
    fill(m, (16.0, 28.0, 14.0, 30.0, 0.0, 1.2), "marble", tone=0.25)
    fill(m, (17.0, 27.0, 15.0, 29.0, 0.4, 1.1), "water", tone=lambda X, Y, Z: 0.3 * (np.sin(X + Y) > 0.8))
    # The peristyle garden behind.
    fill(m, (44.0, 76.0, 6.0, 58.0, 0.0, 0.8), "grass", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 1305) - 0.5))
    from sets.rome.common import box_hedge
    box_hedge(m, 50.0, 70.0, 12.0, 14.0, 0.8)
    box_hedge(m, 50.0, 70.0, 50.0, 52.0, 0.8)
    revolve(m, 60.0, 32.0, 0.8, 2.6, lambda t: 4.0, "marble", tone=0.2)
    fill(m, (56.0, 64.0, 28.0, 36.0, 1.6, 2.7), "water", lambda X, Y, Z: np.hypot(X - 60, Y - 32) < 3.2, tone=0.3)
    for x, y in ((52.0, 24.0), (68.0, 40.0), (52.0, 40.0), (68.0, 24.0)):
        fill(m, (x - 1.4, x + 1.4, y - 1.4, y + 1.4, 0.8, 3.0), "blossom", lambda X, Y, Z, x=x, y=y:
             np.hypot(X - x, Y - y) < 1.4, tone=0.2)
    o = RM.ROrder("tuscan", D=0.4, H=3.4, shaft="stucco_red", trim="whitewash", fluted=False)
    from arch import Scale
    for x in np.linspace(46.0, 74.0, 5):
        for y in (8.0, 56.0):
            RM.column(m, x, y, 0.8, o, Scale(1.0))
    RM.lean_to(m, (42.0, 78.0, 2.0, 12.0), H - 4.0, H, "-y", "terracotta", 1306)
    RM.lean_to(m, (42.0, 78.0, 52.0, 62.0), H - 4.0, H, "+y", "terracotta", 1307)
    RM.lean_to(m, (68.0, 78.0, 10.0, 54.0), H - 4.0, H, "+x", "terracotta", 1308)
    # The street side: door with pilasters, two shops, laurels.
    for i, s0 in enumerate((4.0, 26.0)):
        shopfront(m, "+y", box, s0, 8.0, GROUND - 2.0, TRADES[(v + 2 * i + 1) % 8], 1309 + i)
    fill(m, face_box("+y", *box, 0.0, 14.0, 16.0, 24.0, -1.0, 0.1), "whitewash", tone=0.3)
    carve(m, face_box("+y", *box, 0.0, 11.0, 17.5, 22.5, -1.1, 2.0))
    fill(m, face_box("+y", *box, 0.0, 11.0, 17.5, 22.5, 1.6, 2.0), "wood", tone=lambda X, Y, Z: -0.4 * ((Z % 3.0) < 0.5))
    fill(m, face_box("+y", *box, 14.0, 16.5, 15.0, 25.0, -1.4, 0.1), "whitewash",
         lambda X, Y, Z: Z < 16.5 - np.abs(X - 20.0) * 0.5, tone=0.35)
    laurel(m, 14.0, 65.0, 0.0, 12.0, seed=v)
    laurel(m, 26.0, 65.0, 0.0, 12.0, seed=v + 1)
    halo(m, 20.0, 63.0, 9.0, 8.0, LAMP, 0.5)
    return m


# ---------------------------------------------------------------- shops and workshops

def r_taberna(v, frame, frames, k):
    """A single shop front by trade (variants: baker, wine, oil, cloth, pottery, lamp, shoes,
    books) under one storey with a window and a tiled pent roof."""
    m = _m(1, 1, 36, k)
    box = (1.0, 15.0, 1.0, 15.0)
    _block(m, box, 0.0, GROUND + STOREY - 2.0, 1401 + v, "brick" if v % 3 else "ochre")
    shopfront(m, "+y", box, 2.0, 10.0, GROUND - 2.0, TRADES[v % 8], 1402 + v)
    windows(m, "+y", box, GROUND + 3.0, 1, seed=1403 + v)
    RM.lean_to(m, (0.0, 16.0, 0.0, 16.0), GROUND + STOREY - 2.0, GROUND + STOREY + 2.0, "-y", "terracotta", 1404)
    return m


def r_thermopolium(v, frame, frames, k):
    """A hot-food counter: an L-shaped masonry counter faced with marble scraps and painted
    with a lararium scene, big jars (dolia) sunk in it for chickpeas, lentils and wine, a
    brazier with a pot, shelves of cups; steam rising."""
    m = _m(1, 1, 34, k)
    box = (1.0, 15.0, 1.0, 15.0)
    _block(m, box, 0.0, GROUND + STOREY - 2.0, 1501, "stucco_red")
    carve(m, (2.0, 14.0, 2.0, 15.5, 0.0, GROUND - 2.0))
    fill(m, (6.0, 14.0, 11.0, 14.6, 0.0, 6.0), "marble", tone=lambda X, Y, Z: (hash01(np.floor(X).astype(np.int64),
                                                                                       np.floor(Z).astype(np.int64), 7) - 0.5) * 1.2)
    fill(m, (11.0, 14.6, 3.0, 14.6, 0.0, 6.0), "stucco_red", tone=0.1)
    fill(m, (6.0, 14.6, 3.0, 14.6, 6.0, 6.6), "marble", tone=0.3)
    for x, y in ((8.0, 12.8), (11.0, 12.8), (12.8, 9.0), (12.8, 5.5)):
        fill(m, (x - 1.0, x + 1.0, y - 1.0, y + 1.0, 6.0, 6.7), "ink", lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 0.9)
    revolve(m, 4.0, 12.0, 0.0, 4.0, lambda t: 1.2, "bronze", tone=0.2)
    ellipsoid(m, (4.0, 12.0, 5.0), (1.2, 1.2, 1.0), "clay", 0.2)
    fill(m, (3.0, 5.0, 11.0, 13.0, 3.6, 4.2), "ember")
    halo(m, 4.0, 12.0, 4.2, 6.0, FIRE, 0.5)
    for z in (8.0, 10.5):
        slab(m, 2.0, 10.0, 2.0, 3.0, z, z + 0.4, "wood", tone=0.0)
        for i in range(4):
            ellipsoid(m, (3.0 + i * 2.0, 2.6, z + 0.9), (0.5, 0.5, 0.5), "clay", 0.3)
    RM.lean_to(m, (0.0, 16.0, 0.0, 16.0), GROUND + STOREY - 2.0, GROUND + STOREY + 2.0, "-y", "terracotta", 1502)
    fill(m, face_box("+y", *box, GROUND - 1.0, GROUND + 1.5, 2.0, 14.0, -0.2, 0.1), "ochre", tone=0.2)
    return m


def r_bakery(v, frame, frames, k):
    """A bakery (pistrinum): hourglass-shaped lava mills turned by blindfolded donkeys walking
    round them (the mills turn between frames), the domed brick oven with its smoke, the
    kneading trough and the loaves stamped with the baker's mark on boards."""
    m = _m(3, 2, 40, k)
    box = (2.0, 46.0, 2.0, 30.0)
    RM.wall(m, (2.0, 46.0, 2.0, 6.0), 0.0, GROUND + 6.0, "brick", 1601)
    RM.wall(m, (2.0, 6.0, 2.0, 30.0), 0.0, GROUND + 6.0, "brick", 1602)
    RM.wall(m, (38.0, 46.0, 2.0, 30.0), 0.0, GROUND + 6.0, "brick", 1603)
    fill(m, (6.0, 38.0, 6.0, 30.0, 0.0, 0.6), "basalt", tone=M.paving(3.0, 3.0, 1604))
    turn = frame / max(frames, 1) * math.pi
    for i, (x, y) in enumerate(((14.0, 14.0), (26.0, 14.0))):
        revolve(m, x, y, 0.0, 2.0, lambda t: 3.6, "basalt", tone=0.1)
        revolve(m, x, y, 2.0, 5.0, lambda t: 1.2 + 1.4 * t, "basalt", tone=0.0)
        revolve(m, x, y, 5.0, 9.0, lambda t: 2.6 * (1 - t) + 1.0, "basalt", tone=-0.1)
        a = turn + i * 1.6
        bx, by = x + math.cos(a) * 1.6, y + math.sin(a) * 1.6
        rod(m, (x, y, 5.0), (x + math.cos(a) * 6.0, y + math.sin(a) * 6.0, 5.5), 0.35, "wood")
        dx, dy = x + math.cos(a) * 6.5, y + math.sin(a) * 6.5
        ellipsoid(m, (dx, dy, 4.6), (1.8 + abs(math.sin(a)) * 0.4, 1.8 + abs(math.cos(a)) * 0.4, 1.4), "felt", 0.1)
        ellipsoid(m, (dx + math.sin(a) * 2.0, dy - math.cos(a) * 2.0, 5.6), (0.8, 0.8, 0.8), "felt", 0.2)
        for lx in (-1.0, 1.0):
            rod(m, (dx + lx * math.sin(a), dy - lx * math.cos(a), 3.6), (dx + lx * math.sin(a), dy - lx * math.cos(a), 0.0),
                0.3, "felt", 0.0)
    revolve(m, 34.0, 22.0, 0.0, 8.0, lambda t: 6.0, "brick", tone=RM.brick(1605))
    fill(m, (26.0, 42.0, 14.0, 30.0, 8.0, 14.0), "brick",
         lambda X, Y, Z: ((X - 34.0) ** 2 + (Y - 22.0) ** 2 + ((Z - 8.0) * 1.0) ** 2) < 36.0, tone=RM.brick(1606))
    fill(m, (33.0, 35.0, 26.5, 28.5, 1.5, 5.5), "ember")
    halo(m, 34.0, 28.0, 3.5, 8.0, FIRE, 0.8)
    slab(m, 8.0, 12.0, 24.0, 29.0, 0.0, 4.0, "wood", tone=0.0)
    for i in range(6):
        ellipsoid(m, (16.0 + i * 3.0, 28.0, 5.0), (1.0, 1.0, 0.55), "ochre", 0.3)
    slab(m, 15.0, 33.0, 26.5, 29.5, 0.0, 4.5, "wood_light", tone=0.0)
    RM.lean_to(m, (0.0, 48.0, 0.0, 9.0), GROUND + 6.0, GROUND + 9.0, "-y", "terracotta", 1607)
    return m


def r_fullonica(v, frame, frames, k):
    """A fullery: a row of basins and stalls where workers tread cloth in water and urine,
    rinsing tanks, a press, cloth hanging on frames and racks to dry, an awning."""
    m = _m(3, 2, 34, k)
    RM.wall(m, (2.0, 46.0, 2.0, 5.0), 0.0, GROUND + 4.0, "brick", 1701)
    for i in range(5):
        x = 5.0 + i * 6.0
        slab(m, x, x + 5.0, 6.0, 12.0, 0.0, 3.0, "brick", tone=0.1)
        fill(m, (x + 0.6, x + 4.4, 6.6, 11.4, 1.0, 2.8), "water", tone=lambda X, Y, Z: 0.2 * (np.sin(X * 2 + frame) > 0.6))
    for t_ in range(3):
        x = 6.0 + t_ * 13.0
        slab(m, x, x + 11.0, 15.0, 22.0, 0.0, 3.2, "travertine", tone=0.2)
        fill(m, (x + 0.6, x + 10.4, 15.6, 21.4, 1.2, 3.0), "water", tone=0.3)
    for x in (6.0, 18.0, 30.0, 42.0):
        rod(m, (x, 26.0, 0.0), (x, 26.0, 14.0), 0.4, "wood")
    rod(m, (6.0, 26.0, 13.6), (42.0, 26.0, 13.6), 0.3, "wood")
    for i, x in enumerate(np.arange(7.5, 41.0, 5.0)):
        slab(m, x, x + 4.0, 25.6, 26.4, 5.0, 13.4, ("linen", "saffron", "cinnabar", "eblue", "linen", "purple", "ochre")[i % 7],
             tone=lambda X, Y, Z: 0.2 - 0.3 * ((Z % 2.0) < 0.4))
    fill(m, (2.0, 46.0, 2.0, 14.0, GROUND + 3.0, GROUND + 4.5), "linen",
         lambda X, Y, Z: np.abs(Z - (GROUND + 4.0 - (Y - 2.0) * 0.12)) < 0.4,
         tone=lambda X, Y, Z: 0.3 * ((X % 4.0) < 2.0) - 0.1)
    return m


def r_dyeworks(v, frame, frames, k):
    """A dyer's shop: round lead-lined vats over little furnaces, madder red, woad blue and
    saffron yellow, dyed cloth drying on poles, steam."""
    m = _m(2, 2, 32, k)
    RM.wall(m, (2.0, 30.0, 2.0, 5.0), 0.0, GROUND + 2.0, "brick", 1801)
    for i, (x, y, dye) in enumerate(((10.0, 12.0, "cinnabar"), (22.0, 12.0, "lapis"), (16.0, 22.0, "saffron"))):
        revolve(m, x, y, 0.0, 4.0, lambda t: 3.6, "brick", tone=RM.brick(1802 + i))
        fill(m, (x - 3, x + 3, y - 3, y + 3, 3.0, 4.1), dye, lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 2.8,
             tone=0.2)
        fill(m, (x - 1, x + 1, y + 2.6, y + 3.8, 0.5, 2.0), "ember")
    for x in (4.0, 28.0):
        rod(m, (x, 28.0, 0.0), (x, 28.0, 13.0), 0.4, "wood")
    rod(m, (4.0, 28.0, 12.6), (28.0, 28.0, 12.6), 0.3, "wood")
    for i, x in enumerate((6.0, 12.0, 18.0, 24.0)):
        slab(m, x, x + 4.0, 27.6, 28.4, 5.0, 12.4, ("cinnabar", "lapis", "saffron", "purple")[i], tone=0.2)
    return m


def r_glass(v, frame, frames, k):
    """A glass workshop: a small domed furnace glowing through its openings, the glassblower's
    bench and pipes, shelves of blown cups and flasks in blue-green glass."""
    m = _m(2, 2, 32, k)
    RM.wall(m, (2.0, 30.0, 2.0, 14.0), 0.0, GROUND + 4.0, "brick", 1901)
    RM.gable(m, (1.0, 31.0, 1.0, 15.0), GROUND + 4.0, 4.0, "x", seed=1902)
    revolve(m, 16.0, 22.0, 0.0, 6.0, lambda t: 5.0, "brick", tone=RM.brick(1903))
    fill(m, (10.0, 22.0, 16.0, 28.0, 6.0, 10.0), "brick",
         lambda X, Y, Z: (X - 16.0) ** 2 + (Y - 22.0) ** 2 + ((Z - 6.0) * 1.2) ** 2 < 25.0, tone=0.0)
    for a in (0.0, 1.6, 3.2):
        x, y = 16.0 + math.cos(a) * 4.9, 22.0 + math.sin(a) * 4.9
        fill(m, (x - 1.0, x + 1.0, y - 1.0, y + 1.0, 3.0, 5.0), "ember")
    halo(m, 16.0, 22.0, 5.0, 12.0, FIRE, 0.9)
    slab(m, 4.0, 10.0, 16.0, 18.0, 0.0, 4.0, "wood", tone=0.0)
    for z in (4.0, 8.0):
        slab(m, 3.0, 13.0, 14.6, 15.4, z, z + 0.4, "wood", tone=0.0)
        for i in range(4):
            ellipsoid(m, (4.5 + i * 2.4, 14.9, z + 1.0), (0.6, 0.5, 0.8), "glass_cool", 0.3)
    return m


def r_smithy(v, frame, frames, k):
    """A smithy: the forge hearth with bellows and a hood, the anvil on its block, tools on the
    wall, iron bars; the fire glowing at night."""
    m = _m(2, 2, 34, k)
    RM.wall(m, (2.0, 30.0, 2.0, 12.0), 0.0, GROUND + 4.0, "brick", 2001)
    RM.lean_to(m, (1.0, 31.0, 1.0, 22.0), GROUND, GROUND + 6.0, "-y", "terracotta", 2002)
    for x in (2.0, 30.0):
        rod(m, (x, 21.0, 0.0), (x, 21.0, GROUND), 0.5, "wood")
    slab(m, 6.0, 14.0, 12.0, 18.0, 0.0, 5.0, "brick", tone=0.1)
    fill(m, (7.0, 13.0, 13.0, 17.0, 5.0, 5.8), "ember")
    halo(m, 10.0, 15.0, 6.0, 10.0, FIRE, 0.9)
    fill(m, (6.0, 14.0, 12.0, 15.0, 9.0, 16.0), "brick", lambda X, Y, Z: (X - 10.0) ** 2 < 16.0 * (1 - (Z - 9.0) / 8.0),
         tone=-0.2)
    ellipsoid(m, (16.0, 15.0, 3.0), (2.0, 1.4, 1.2), "leather", 0.1)
    slab(m, 20.0, 24.0, 18.0, 22.0, 0.0, 3.6, "wood", tone=0.0)
    slab(m, 19.5, 24.5, 19.0, 21.0, 3.6, 5.0, "metal", tone=0.3)
    for i in range(4):
        rod(m, (20.0 + i * 2.0, 12.4, 8.0), (20.0 + i * 2.0, 12.4, 12.0), 0.3, "metal", 0.3)
    return m


# ---------------------------------------------------------------- street furniture

def r_lacus(v, frame, frames, k):
    """A street fountain (lacus): a rectangular basin of four stone slabs clamped with iron, a
    pillar with a spout carved as a head, water running; the kerb worn by jugs."""
    m = _m(1, 1, 18, k)
    slab(m, 3.0, 13.0, 2.0, 12.0, 0.0, 4.0, "travertine" if v == 0 else "tufa", tone=M.ashlar(4.0, 10.0, 2101, spread=0.4))
    carve(m, (3.8, 12.2, 2.8, 11.2, 3.3, 4.1))
    slab(m, 7.0, 9.0, 1.0, 3.0, 0.0, 9.0, "travertine", tone=0.2)
    ellipsoid(m, (8.0, 3.2, 7.4), (1.0, 0.7, 1.1), "travertine", 0.4)
    land = waterworks.stream(m, (8.0, 3.9, 7.0), (0.0, 1.9), 3.3, frame, frames, r=0.4, seed=2103)
    waterworks.surface(m, (3.8, 12.2, 2.8, 11.2), 3.3, frame, frames, sources=[land], seed=2104, depth_units=2.0)
    for x in (3.0, 13.0):
        rod(m, (x, 2.0, 4.0), (x, 12.0, 4.0), 0.2, "metal", 0.3)
    return m


def r_compitum(v, frame, frames, k):
    """A crossroads shrine of the Lares (compitum): a small altar before a painted niche with the
    two dancing Lares and the Genius of the emperor, a garland, a lamp lit at dusk."""
    m = _m(1, 1, 22, k)
    slab(m, 3.0, 13.0, 1.0, 6.0, 0.0, 15.0, "stucco_red", tone=0.0)
    carve(m, (4.5, 11.5, 4.5, 6.2, 5.0, 12.0))
    fill(m, (4.5, 11.5, 4.4, 4.8, 5.0, 12.0), "whitewash", tone=0.2)
    for x in (6.0, 10.0):
        fill(m, (x - 0.6, x + 0.6, 4.6, 5.0, 6.0, 10.0), "cinnabar", tone=0.2)
        ellipsoid(m, (x, 4.8, 10.6), (0.5, 0.3, 0.5), "skin_tan", 0.3)
    fill(m, (2.5, 13.5, 0.5, 6.5, 15.0, 17.0), "terracotta", lambda X, Y, Z: Z < 17.0 - np.abs(X - 8.0) * 0.35, tone=0.2)
    slab(m, 5.5, 10.5, 8.0, 11.0, 0.0, 5.0, "travertine", tone=0.2)
    slab(m, 5.0, 11.0, 7.5, 11.5, 5.0, 5.8, "travertine", tone=0.35)
    fill(m, (7.0, 9.0, 9.0, 10.0, 5.8, 6.6), "lamp")
    halo(m, 8.0, 9.5, 6.4, 8.0, LAMP, 0.8)
    rod(m, (4.0, 6.4, 13.0), (12.0, 6.4, 13.0), 0.5, "leaf", 0.2)
    return m


def r_latrine(v, frame, frames, k):
    """A public latrine: a room with marble seats along three walls over the running channel,
    a water channel at the feet, a small fountain at the door."""
    m = _m(2, 2, 28, k)
    box = (2.0, 30.0, 2.0, 30.0)
    RM.wall(m, box, 0.0, GROUND + 2.0, "brick", 2201)
    carve(m, (5.0, 27.0, 5.0, 27.0, 0.5, GROUND + 3.0))
    for wb in ((5.0, 9.0, 5.0, 27.0), (5.0, 27.0, 5.0, 9.0), (23.0, 27.0, 5.0, 27.0)):
        slab(m, *wb, 0.0, 4.0, "marble", tone=lambda X, Y, Z: 0.3 - 0.9 * ((((X + Y) % 3.0) < 1.0) & (Z > 3.5)))
    fill(m, (9.0, 23.0, 9.0, 11.0, 0.0, 0.6), "water", tone=0.2)
    RM.hip(m, (1.0, 31.0, 1.0, 31.0), GROUND + 2.0, 5.0, seed=2202)
    carve(m, (12.0, 20.0, 12.0, 20.0, GROUND, GROUND + 8.0))
    RM.opening(m, "+y", box, 11.0, 6.0, 0.0, 8.0, 3.0, frame="travertine")
    return m


def r_bath_small(v, frame, frames, k):
    """A neighbourhood bath (balneum): brick halls with barrel-vaulted roofs, big arched windows
    of glass facing the afternoon sun, the furnace room with its smoking flue and woodpile, an
    entrance with a painted sign, a small exercise yard."""
    m = _m(4, 3, 46, k)
    box = (2.0, 40.0, 2.0, 46.0)
    RM.wall(m, box, 0.0, 22.0, "brick", 2301)
    for f in ("+x", "+y"):
        L = RM.face_length(f, *box)
        for s0 in np.arange(5.0, L - 8.0, 10.0):
            RM.window(m, f, box, s0, 5.0, 10.0, 7.0, arched=True, glass=True, lit=0.45)
    RM.vault_roof(m, (2.0, 40.0, 2.0, 24.0), 22.0, "x", "whitewash", seed=2302)
    RM.vault_roof(m, (2.0, 40.0, 24.0, 46.0), 22.0, "x", "whitewash", seed=2303)
    RM.wall(m, (40.0, 62.0, 2.0, 18.0), 0.0, 14.0, "brick", 2304)
    RM.gable(m, (39.0, 63.0, 1.0, 19.0), 14.0, 4.0, "x", seed=2305)
    slab(m, 52.0, 56.0, 4.0, 8.0, 0.0, 30.0, "brick", tone=RM.brick(2306))
    fill(m, (52.6, 55.4, 4.6, 7.4, 28.0, 30.1), "ink")
    for i in range(5):
        rod(m, (42.0 + i * 1.2, 20.0, 0.6 + (i % 2)), (60.0, 20.0, 0.6 + (i % 2)), 0.6, "wood")
    fill(m, (42.0, 60.0, 24.0, 44.0, 0.0, 0.7), "poros", tone=0.0)
    RM.opening(m, "+y", box, 16.0, 6.0, 0.0, 9.0, 3.0, frame="travertine")
    fill(m, face_box("+y", *box, 15.0, 17.5, 13.0, 25.0, -0.2, 0.1), "ochre", tone=0.2)
    return m


def r_horrea(v, frame, frames, k):
    """A warehouse (horrea): ranges of vaulted storerooms round a court, a travertine-framed
    gateway on the street, small high windows, tiled roofs."""
    m = _m(4, 4, 40, k)
    box = (2.0, 62.0, 2.0, 62.0)
    RM.wall(m, box, 0.0, 18.0, "brick", 2401)
    carve(m, (16.0, 48.0, 16.0, 48.0, 0.6, 19.0))
    fill(m, (16.0, 48.0, 16.0, 48.0, 0.0, 0.6), "brick", tone=M.paving(3.0, 3.0, 2402))
    for f in ("+x", "+y"):
        for s0 in np.arange(6.0, 56.0, 8.0):
            RM.window(m, f, box, s0, 1.6, 12.0, 2.2)
    RM.opening(m, "+y", box, 26.0, 12.0, 0.0, 10.0, 3.0, frame="travertine")
    for rb, up in (((1.0, 17.0, 1.0, 63.0), "-x"), ((47.0, 63.0, 1.0, 63.0), "+x"), ((17.0, 47.0, 1.0, 17.0), "-y"),
                   ((17.0, 47.0, 47.0, 63.0), "+y")):
        RM.lean_to(m, rb, 18.0, 22.0, {"-x": "+x", "+x": "-x", "-y": "+y", "+y": "-y"}[up], "terracotta", 2403)
    for i in range(6):
        ellipsoid(m, (22.0 + (i % 3) * 8.0, 24.0 + (i // 3) * 14.0, 2.4), (2.4, 2.0, 2.0), "wool", 0.1)
    return m


def r_crane(v, frame, frames, k):
    """A treadwheel crane: a great wheel walked by men turning the drum, two tall jib legs
    guyed back, a marble block on the rope (the wheel turns between frames)."""
    m = _m(2, 2, 76, k)
    treadwheel_crane(m, 14.0, 12.0, 0.0, 70.0, along="y", load="marble", swing=frame * 0.6)
    return m


def r_scaffold(v, frame, frames, k):
    """Scaffolding of lashed poles with putlog decks and a ladder."""
    from sets.athens.common import scaffold
    m = _m(1, 1, 64, k)
    scaffold(m, 2.0, 14.0, 2.0, 14.0, 0.0, 60.0, decks=4)
    for y in (5.0, 8.0):                                    # the ladder: rails and rungs
        rod(m, (14.8, y, 0.0), (14.8, y, 58.0), 0.4, "wood", 0.1)
    for z in np.arange(1.0, 58.0, 3.0):
        rod(m, (14.8, 5.0, z), (14.8, 8.0, z), 0.35, "wood", 0.1)
    return m


def r_milestone(v, frame, frames, k):
    """A milestone: a cylinder of stone on a square base, inscribed with the emperor's name and
    titles and the miles from Rome."""
    m = _m(1, 1, 18, k)
    slab(m, 4.0, 12.0, 4.0, 12.0, 0.0, 2.0, "travertine" if v == 0 else "tufa", tone=0.2)
    revolve(m, 8.0, 8.0, 2.0, 15.0, lambda t: 2.8, "travertine" if v == 0 else "marble", tone=0.1)
    fill(m, (5.0, 11.0, 5.0, 11.0, 6.0, 12.0), "cinnabar",
         lambda X, Y, Z: (np.hypot(X - 8.0, Y - 8.0) > 2.55) & (np.cos(np.arctan2(Y - 8.0, X - 8.0) - 0.8) > 0.3) &
         ((np.floor(Z * 2) % 3) < 2) & (hash01(np.floor((X + Y) * 2).astype(np.int64), np.floor(Z * 2).astype(np.int64), 21) < 0.6),
         tone=0.1, only_solid=True)
    revolve(m, 8.0, 8.0, 15.0, 15.8, lambda t: 2.9, "travertine", tone=0.4)
    return m


STALL = ("fruit", "fish", "garum", "samian", "flowers", "bread")


def r_stall(v, frame, frames, k):
    """A market stall: a trestle under a striped awning on poles (it flaps between frames), the
    goods by trade (variants: fruit and vegetables, fish, garum jars, red samian ware from
    Gaul, flowers and garlands for the festival, bread)."""
    m = _m(2, 1, 28, k)
    trade = STALL[v % len(STALL)]
    cloth = ("saffron", "eblue", "cinnabar", "malachite", "linen", "ochre")[v % 6]
    for x, y in ((2.0, 2.0), (2.0, 14.0), (30.0, 2.0), (30.0, 14.0)):
        rod(m, (x, y, 0.0), (x, y, 18.0 if y < 8 else 14.0), 0.45, "wood")
    fill(m, (0.0, 32.0, 0.0, 16.0, 12.0, 19.5), cloth,
         lambda X, Y, Z: np.abs(Z - (18.0 - (Y - 2.0) * 0.33 - 0.6 * np.sin(X * 0.35 + frame * 2))) < 0.45,
         tone=lambda X, Y, Z: 0.35 * ((X % 4.0) < 2.0) - 0.15)
    slab(m, 3.0, 29.0, 8.0, 14.0, 6.0, 7.0, "wood_light", tone=M.timber("x", 2501))
    for x in (4.0, 28.0):
        slab(m, x - 0.6, x + 0.6, 9.0, 13.0, 0.0, 6.0, "wood", tone=0.0)
    if trade == "fruit":
        for i in range(5):
            ellipsoid(m, (6.0 + i * 5.0, 11.0, 7.8), (2.2, 2.0, 1.0), "straw", 0.0)
            ellipsoid(m, (6.0 + i * 5.0, 11.0, 8.6), (1.6, 1.4, 0.6), ("poppy", "leaf", "yellow", "violet", "orange")[i], 0.3)
    elif trade == "fish":
        for i in range(8):
            ellipsoid(m, (5.0 + i * 3.0, 11.0 + (i % 2), 7.6), (1.4, 0.5, 0.45), "metal", tone=0.4)
    elif trade == "garum":
        for i in range(5):
            amphora(m, 6.0 + i * 5.0, 11.0, 7.0, "african" if i % 2 else "wine")
    elif trade == "samian":
        for i in range(8):
            ellipsoid(m, (5.0 + i * 3.0, 11.0, 7.6), (1.2, 1.2, 0.6), "cinnabar", tone=0.2)
    elif trade == "flowers":
        for i in range(5):
            rod(m, (4.0 + i * 5.0, 2.5, 15.0), (6.5 + i * 5.0, 2.5, 12.5), 0.7, "leaf", tone=0.2)
            ellipsoid(m, (6.0 + i * 5.0, 11.0, 7.8), (1.6, 1.6, 0.8), ("poppy", "blossom", "yellow")[i % 3], tone=0.3)
    else:
        for i in range(7):
            ellipsoid(m, (5.0 + i * 3.6, 11.0, 7.6), (1.3, 1.3, 0.6), "ochre", 0.3)
    return m


def r_amphorae(v, frame, frames, k):
    """A stack of amphorae by origin (variants: Spanish oil in globular Dressel 20s, Gallic wine
    in slender jars, African oil in cylinders, Eastern wine), some lying in a pyramid."""
    m = _m(1, 1, 22, k)
    kind = ("dressel20", "wine", "african", "eastern")[v % 4]
    mat = {"dressel20": "clay", "wine": "terracotta", "african": "clay", "eastern": "giallo"}[kind]
    # QA4 V-A-010: upright jars in rows read as candles. Most lie stacked in a pyramid, necks
    # out, as they were stored and shipped; two stand leaning against the stack.
    r = 2.4 if kind == "dressel20" else 1.6
    for layer, (n, z) in enumerate(((3, r), (2, 3 * r - 0.8), (1, 5 * r - 1.6))):
        for i in range(n):
            x = 8.0 + (i - (n - 1) / 2) * 2 * r
            fill(m, (x - r, x + r, 1.5, 13.0, z - r, z + r), mat,
                 lambda X, Y, Z, x=x, z=z: np.hypot(X - x, Z - z) < r * np.clip(np.sin(np.pi * (Y - 1.5) / 11.5) * 1.3, 0.3, 1.0),
                 tone=lambda X, Y, Z: 0.15 * ((Y % 3.0) < 0.4) + (hash01(np.floor(Y).astype(np.int64), layer, v) - 0.5) * 0.3)
            fill(m, (x - 0.7, x + 0.7, 12.5, 15.0, z - 0.7, z + 0.7), mat, tone=0.3)
    amphora(m, 13.5, 4.0, 0.0, kind)
    amphora(m, 3.0, 13.0, 0.0, kind)
    return m


def r_statue(v, frame, frames, k):
    """An honorific statue on an inscribed base: a togate citizen in marble, a general in
    bronze armour, a woman in stola and palla, an equestrian bronze (by rotation's look)."""
    m = _m(1, 1, 40, k)
    from greek import statue_base
    zb = statue_base(m, 8.0, 8.0, 0.0, 7.0, 9.0, material="marble")
    RM.statue(m, 8.0, 8.0, zb, 18.0, TOGATE, material="marble")
    return m


def r_column_honor(v, frame, frames, k):
    """An honorary column with a gilded statue on top."""
    m = _m(1, 1, 64, k)
    from arch import Scale
    slab(m, 3.0, 13.0, 3.0, 13.0, 0.0, 5.0, "marble", tone=M.ashlar(5.0, 10.0, 2601, spread=0.2))
    RM.column(m, 8.0, 8.0, 5.0, RM.ROrder("corinthian", D=0.75, H=8.0, shaft="granite", fluted=False), Scale(1.0))
    RM.statue(m, 8.0, 8.0, 45.0, 12.0, TOGATE, material="gilt", keep=())
    return m


def r_lamp(v, frame, frames, k):
    """A street lantern on its own post (it stands free in streets and squares, so it reads
    from every side, V7-002): a travertine footing, a wooden post, an iron bracket with a bronze
    lantern of horn panes hanging from it, lit."""
    m = _m(1, 1, 20, k)
    slab(m, 6.0, 10.0, 6.0, 10.0, 0.0, 1.6, "travertine", tone=0.2)
    slab(m, 7.3, 8.7, 7.3, 8.7, 1.6, 15.0, "wood", tone=lambda X, Y, Z: 0.15 - 0.3 * ((Z % 3.0) < 0.3))
    slab(m, 7.0, 9.0, 7.0, 9.0, 15.0, 15.6, "bronze", tone=0.2)
    rod(m, (8.0, 8.0, 14.4), (8.0, 4.4, 14.4), 0.3, "metal", 0.1)
    rod(m, (8.0, 6.0, 12.6), (8.0, 4.6, 14.2), 0.2, "metal", 0.1)
    rod(m, (8.0, 4.4, 14.4), (8.0, 4.4, 13.0), 0.15, "bronze")
    ellipsoid(m, (8.0, 4.4, 11.6), (0.9, 0.9, 1.3), "lamp", 0.2)
    ellipsoid(m, (8.0, 4.4, 12.8), (0.8, 0.8, 0.3), "bronze", 0.3)
    ellipsoid(m, (8.0, 4.4, 10.2), (0.7, 0.7, 0.25), "bronze", 0.2)
    halo(m, 8.0, 4.4, 11.6, 10.0, LAMP, 0.9)
    return m


def r_brazier(v, frame, frames, k):
    """A bronze brazier on lion's feet with its coals burning."""
    m = _m(1, 1, 16, k)
    for a in (0.0, 2.1, 4.2):
        rod(m, (8 + 3.0 * math.cos(a), 8 + 3.0 * math.sin(a), 0.0), (8 + 2.0 * math.cos(a), 8 + 2.0 * math.sin(a), 8.0),
            0.35, "bronze")
    revolve(m, 8, 8, 8.0, 10.5, lambda t: 2.4 + 1.2 * t, "bronze", tone=0.2)
    fill(m, (5, 11, 5, 11, 10.0, 11.0), "ember", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.0)
    ellipsoid(m, (8, 8, 12.0), (1.6, 1.6, 2.0), "fire", tone=0.3)
    halo(m, 8, 8, 12.0, 12.0, FIRE, 1.0)
    return m


def r_bonfire(v, frame, frames, k):
    """A Parilia bonfire at a crossroads (rome.md §8): a heap of straw and bean stalks round a
    few stakes, burning, for the shepherds to leap over at nightfall."""
    m = _m(1, 1, 16, k)
    for a in (0.4, 1.9, 3.3, 4.8):
        rod(m, (8 + 4.5 * math.cos(a), 8 + 4.5 * math.sin(a), 0.0), (8 + 0.8 * math.cos(a), 8 + 0.8 * math.sin(a), 8.5),
            0.4, "wood", 0.1)
    revolve(m, 8, 8, 0.0, 5.5, lambda t: 5.6 * (1 - t) ** 0.8 + 0.6, "straw",
            tone=lambda X, Y, Z: 0.4 * (value_noise(X * 2, Y * 2, Z * 2, 1.0, 2711) - 0.5))
    fill(m, (4, 12, 4, 12, 3.5, 6.0), "ember", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.8 - (Z - 3.5))
    ellipsoid(m, (8, 8, 8.0), (2.4, 2.4, 3.2), "fire", tone=0.2)
    ellipsoid(m, (8.3, 8, 10.4), (1.2, 1.2, 1.8), "lamp")
    halo(m, 8, 8, 8.5, 16.0, FIRE, 1.0)
    return m


def r_altar(v, frame, frames, k):
    """An altar of marble carved with garlands and ox skulls, the fire on top, incense smoke."""
    m = _m(1, 1, 18, k)
    slab(m, 3.0, 13.0, 3.0, 13.0, 0.0, 1.4, "marble", tone=0.2)
    slab(m, 4.5, 11.5, 4.5, 11.5, 1.4, 9.0, "marble", tone=0.1)
    for f in ("+x", "+y", "-x", "-y"):
        RM._garlands(m, f, (4.5, 11.5, 4.5, 11.5), 4.0, 8.0, "marble", 2801)
    slab(m, 4.0, 12.0, 4.0, 12.0, 9.0, 10.0, "marble", tone=0.35)
    for x in (4.5, 11.5):
        rod(m, (x, 4.5, 10.4), (x, 11.5, 10.4), 0.6, "marble", 0.3)
    ellipsoid(m, (8.0, 8.0, 11.0), (1.4, 1.4, 1.2), "fire", 0.2)
    halo(m, 8.0, 8.0, 11.0, 9.0, FIRE, 0.7)
    return m


def r_tomb(v, frame, frames, k):
    """A small tomb with a columbarium: a brick chamber with a pediment, its walls inside full of
    niches for urns, a marble inscription panel over the door, a garden plot with a cypress."""
    m = _m(2, 2, 36, k)
    box = (4.0, 26.0, 4.0, 22.0)
    RM.wall(m, box, 0.0, 18.0, "brick", 2901)
    RM.cornice(m, box, 18.0, 1.0, 0.6, "travertine")
    RM.gable(m, (3.0, 27.0, 3.0, 23.0), 19.0, 4.0, "x", seed=2902)
    fill(m, face_box("+y", *box, 11.0, 15.0, 6.0, 16.0, -0.3, 0.1), "marble", tone=0.3)
    RM.inscription(m, "+y", box, 7.0, 15.0, 11.6, 14.4, "cinnabar", rows=2)
    carve(m, face_box("+y", *box, 0.0, 9.0, 8.5, 13.5, -0.1, 2.0))
    for f in ("+x",):
        for row in range(3):
            for s0 in np.arange(3.0, 16.0, 3.0):
                RM.opening(m, f, box, s0, 1.6, 3.0 + row * 4.5, 4.5 + row * 4.5, 0.8, back="ink", keystone=False)
    cypress(m, 28.0, 28.0, 0.0, h=26.0, seed=v)
    return m


def tomb_drum(v, frame, frames, k):
    """A great round drum tomb of the Via Appia (like Caecilia Metella's): a square podium faced
    with travertine, the drum with a frieze of garlands and ox skulls and an inscription panel,
    an earth mound planted with cypresses on top."""
    m = _m(3, 3, 52, k)
    c = 24.0
    slab(m, 4.0, 44.0, 4.0, 44.0, 0.0, 10.0, "travertine", tone=RM.travertine(2.6, 7.0, 3001))
    revolve(m, c, c, 10.0, 30.0, lambda t: 17.0, "travertine", tone=RM.travertine(2.6, 6.0, 3002))
    revolve(m, c, c, 26.0, 30.0, lambda t: 17.4, "marble", tone=lambda X, Y, Z: 0.3 - 0.6 * (
        np.abs(((np.arctan2(Y - c, X - c) * 6) % 1.0) - 0.5) < 0.08))
    fill(m, (c + 14.0, c + 18.0, c - 5.0, c + 5.0, 16.0, 23.0), "marble", lambda X, Y, Z: np.hypot(X - c, Y - c) > 16.5,
         tone=0.3)
    revolve(m, c, c, 30.0, 36.0, lambda t: 16.5 * (1 - 0.35 * t), "soil", tone=-0.1)
    for a in np.linspace(0, 2 * math.pi, 5, endpoint=False):
        cypress(m, c + math.cos(a) * 7.0, c + math.sin(a) * 7.0, 34.0, h=16.0, seed=int(a * 10))
    return m


def tomb_house(v, frame, frames, k):
    """A house tomb: a two-storey brick tomb with pilasters and a pediment, a marble door frame
    and inscription, painted inside."""
    m = _m(2, 2, 40, k)
    box = (4.0, 28.0, 6.0, 26.0)
    RM.wall(m, box, 0.0, 26.0, "brick", 3101)
    for s in (2.0, 18.0):
        RM.pilaster(m, "+y", box, s, 1.0, 24.0, 2.0, RM.ROrder("corinthian", shaft="brick", trim="travertine"))
    RM.cornice(m, box, 24.0, 2.0, 0.8, "travertine")
    RM.gable(m, (3.0, 29.0, 5.0, 27.0), 26.0, 5.0, "x", seed=3102)
    fill(m, face_box("+y", *box, 0.0, 10.0, 8.0, 16.0, -0.4, 0.1), "marble", tone=0.3)
    carve(m, face_box("+y", *box, 0.0, 9.0, 9.5, 14.5, -0.5, 2.0))
    RM.inscription(m, "+y", box, 7.0, 17.0, 13.0, 17.0, "cinnabar", rows=2)
    return m


def tomb_altar(v, frame, frames, k):
    """An altar tomb: an inscribed marble altar on a base with a portrait of the dead in relief."""
    m = _m(1, 1, 22, k)
    slab(m, 3.0, 13.0, 3.0, 13.0, 0.0, 2.0, "travertine", tone=0.2)
    slab(m, 4.5, 11.5, 4.5, 11.5, 2.0, 14.0, "marble", tone=0.1)
    RM.inscription(m, "+y", (4.5, 11.5, 4.5, 11.5), 1.0, 6.0, 4.0, 9.0, "cinnabar", rows=3)
    ellipsoid(m, (8.0, 11.7, 11.5), (1.2, 0.4, 1.4), "marble", 0.4)
    slab(m, 4.0, 12.0, 4.0, 12.0, 14.0, 15.0, "marble", tone=0.35)
    for x in (4.5, 11.5):
        rod(m, (x, 4.5, 15.4), (x, 11.5, 15.4), 0.6, "marble", 0.3)
    return m


def r_vine(v, frame, frames, k):
    """A pergola with vines on posts, young leaves in April."""
    m = _m(1, 1, 22, k)
    for x, y in ((2.0, 2.0), (2.0, 14.0), (14.0, 2.0), (14.0, 14.0)):
        rod(m, (x, y, 0.0), (x, y, 14.0), 0.4, "wood")
    for y in (2.0, 8.0, 14.0):
        rod(m, (2.0, y, 14.0), (14.0, y, 14.0), 0.3, "wood")
    leaf_mass(m, [(5.0, 5.0, 15.0, 3.0), (11.0, 6.0, 15.0, 3.0), (6.0, 12.0, 15.0, 3.0), (12.0, 12.0, 14.5, 2.6)],
              3201 + v, materials=(("leaf", 0.6), ("leaf_light", 0.4)), under="leaf_dark", squash=0.5)
    return m


def r_well(v, frame, frames, k):
    """A garden well-head of marble with a bronze pulley frame and a basin beside it."""
    m = _m(1, 1, 20, k)
    revolve(m, 7.0, 7.0, 0.0, 4.0, lambda t: 3.0, "marble", tone=0.2)
    fill(m, (5, 9, 5, 9, 3.0, 4.1), "ink", lambda X, Y, Z: np.hypot(X - 7, Y - 7) < 2.0)
    for y in (4.0, 10.0):
        rod(m, (7.0, y, 4.0), (7.0, y, 12.0), 0.3, "bronze")
    rod(m, (7.0, 4.0, 12.0), (7.0, 10.0, 12.0), 0.3, "bronze")
    slab(m, 10.0, 15.0, 10.0, 15.0, 0.0, 2.0, "marble", tone=0.2)
    fill(m, (10.6, 14.4, 10.6, 14.4, 1.0, 2.1), "water", tone=0.2)
    return m


def r_vigiles(v, frame, frames, k):
    """A watch-station of the vigiles (excubitorium): a brick house with a wide door, leather
    buckets and hooked poles hanging by it, a pump, a lamp burning all night."""
    m = _m(3, 2, 40, k)
    box = (2.0, 46.0, 2.0, 30.0)
    RM.wall(m, box, 0.0, GROUND + STOREY, "brick", 3301)
    RM.opening(m, "+y", box, 18.0, 10.0, 0.0, 9.0, 3.0, frame="travertine")
    windows(m, "+y", box, GROUND + 3.0, 4, seed=3302, lit=0.6)
    RM.hip(m, (1.0, 47.0, 1.0, 31.0), GROUND + STOREY, 6.0, seed=3303)
    for i in range(5):
        x = 4.0 + i * 2.6
        rod(m, (x, 31.0, 10.0), (x, 31.0, 8.6), 0.15, "leather")
        rod(m, (x, 31.0, 8.0), (x, 31.0, 6.4), 0.9, "leather", 0.1)
    for x in (36.0, 40.0):
        rod(m, (x, 31.0, 0.0), (x + 1.0, 31.0, 18.0), 0.25, "wood")
        rod(m, (x + 1.0, 31.0, 18.0), (x + 2.4, 31.0, 17.0), 0.25, "metal", 0.3)
    halo(m, 30.0, 31.0, 12.0, 9.0, LAMP, 0.8)
    fill(m, (29.4, 30.6, 30.4, 31.4, 11.4, 12.6), "lamp")
    return m


def r_villa_farm(v, frame, frames, k):
    """A Campagna farmstead (villa rustica): a stuccoed house with a tiled roof round a yard,
    the barn, a threshing floor, a wine press, storage jars half buried, a pine."""
    m = _m(3, 3, 44, k)
    RM.wall(m, (2.0, 22.0, 2.0, 46.0), 0.0, 16.0, "stucco", 3401, "whitewash")
    RM.gable(m, (1.0, 23.0, 1.0, 47.0), 16.0, 5.0, "y", seed=3402)
    windows(m, "+x", (2.0, 22.0, 2.0, 46.0), 9.0, 4, seed=3403)
    RM.wall(m, (22.0, 46.0, 2.0, 16.0), 0.0, 12.0, "brick", 3404)
    RM.gable(m, (21.0, 47.0, 1.0, 17.0), 12.0, 4.0, "x", seed=3405)
    revolve(m, 34.0, 32.0, 0.0, 0.8, lambda t: 9.0, "poros", tone=0.0)
    for i in range(4):
        revolve(m, 26.0 + i * 4.0, 44.0, 0.0, 2.0, lambda t: 1.6, "clay", tone=0.2)
    stone_pine(m, 44.0, 44.0, 0.0, 36.0, seed=v)
    return m


def r_shed(v, frame, frames, k):
    """A field shed: a lean-to of timber and reed thatch for tools and hay."""
    m = _m(1, 2, 20, k)
    for x, y in ((2.0, 2.0), (2.0, 30.0), (14.0, 2.0), (14.0, 30.0)):
        rod(m, (x, y, 0.0), (x, y, 12.0 if x < 8 else 9.0), 0.5, "wood")
    RM.lean_to(m, (0.0, 16.0, 0.0, 32.0), 9.0, 13.0, "-x", "straw", 3501)
    ellipsoid(m, (8.0, 16.0, 2.6), (5.0, 9.0, 3.0), "straw", 0.2)
    return m


def mutatio(v, frame, frames, k):
    """A relay station of the state post (mutatio) on the Via Appia: a walled court with stables
    for changing mules, the station house, a trough and a well, and the little inn (caupona)
    beside the gate with its painted sign and a lamp."""
    m = _m(6, 4, 36, k)
    box = (2.0, 94.0, 2.0, 62.0)
    for wb in ((2.0, 4.0, 2.0, 62.0), (92.0, 94.0, 2.0, 62.0), (2.0, 94.0, 2.0, 4.0)):
        RM.wall(m, wb, 0.0, 9.0, "stucco", 3601, "whitewash")
    RM.wall(m, (4.0, 30.0, 4.0, 60.0), 0.0, 16.0, "brick", 3602)
    RM.gable(m, (3.0, 31.0, 3.0, 61.0), 16.0, 5.0, "y", seed=3603)
    windows(m, "+x", (4.0, 30.0, 4.0, 60.0), 8.0, 4, seed=3604, lit=0.4)
    RM.wall(m, (40.0, 92.0, 4.0, 18.0), 0.0, 11.0, "brick", 3605)
    RM.lean_to(m, (39.0, 93.0, 3.0, 26.0), 11.0, 13.0, "-y", "terracotta", 3606)
    for x in (44.0, 56.0, 68.0, 80.0):
        rod(m, (x, 25.0, 0.0), (x, 25.0, 11.0), 0.5, "wood")
    slab(m, 50.0, 70.0, 30.0, 33.0, 0.0, 3.0, "travertine", tone=0.2)
    fill(m, (51.0, 69.0, 30.8, 32.2, 1.0, 3.1), "water", tone=0.2)
    revolve(m, 80.0, 44.0, 0.0, 4.0, lambda t: 2.6, "travertine", tone=0.2)
    fill(m, (40.0, 94.0, 18.0, 60.0, 0.0, 0.5), "poros", tone=0.0)
    ib = (60.0, 92.0, 46.0, 62.0)
    RM.wall(m, ib, 0.0, GROUND + 6.0, "stucco", 3607, "stucco_red")
    shopfront(m, "+y", ib, 6.0, 9.0, GROUND - 2.0, "wine", 3608)
    RM.gable(m, (59.0, 93.0, 45.0, 63.0), GROUND + 6.0, 4.0, "x", seed=3609)
    return m


def stair_travertine(v, frame, frames, k):
    """A travertine stair of one level (16 px) rising toward -y across two tiles: four deep
    steps with lit nosings and shaded risers between brick cheek walls (QA4 V-A-005)."""
    m = _m(1, 2, 12, k, pad=2)
    flight(m, 0.5, 15.5, 0.0, 32.0, 8.0, 4, "travertine", tone=RM.travertine(2.0, 6.0, 859), cheek_mat="brick")
    return m


def quay(v, frame, frames, k):
    """A travertine quay segment on the Tiber: a paved edge over the embankment with a mooring
    stone and a bronze ring, steps down to the water on the second look."""
    m = _m(1, 1, 10, k, below=8, pad=2)
    slab(m, 0.0, 16.0, 0.0, 16.0, -8.0, 0.6, "travertine", tone=RM.travertine(2.4, 8.0, 3701 + v))
    revolve(m, 4.0, 13.0, 0.6, 3.6, lambda t: 1.2 - 0.3 * t, "travertine", tone=0.3)
    fill(m, (6.0, 9.0, 15.4, 16.4, -5.0, -2.0), "bronze", lambda X, Y, Z: np.abs(np.hypot(X - 7.5, Z + 3.5) - 1.1) < 0.35,
         tone=0.3)
    if v:
        for i in range(4):
            carve(m, (6.0, 14.0, 16.0 - (i + 1) * 2.0, 16.1, 0.6 - (i + 1) * 2.0, 0.7))
    return m


def aqua_claudia(v, frame, frames, k):
    """The Aqua Claudia arcade (with the Anio Novus above it) as a joined item: tall piers of
    rusticated tufa ashlar, the brick attic and the covered channels on top. The piers stand on
    the tile edges, half in each of two neighbouring tiles, so every straight piece is one
    whole arch a street can pass under (its tile is walkable; QA4 V-B-002); a corner or an end
    turns or closes on a pier in the middle, with a narrow arch out to each edge pier.
    Variant `m<mask>`: N (-y) 1, E (+x) 2, S (+y) 4, W (-x) 8."""
    mask = v
    m = _m(1, 1, 84, k, pad=2)
    H, half, spring, t = 80.0, 2.0, 52.0, 3.0
    straight = mask in (5, 10) or mask == 0
    if straight:
        along_x = mask == 10
        box = (0.0, 16.0, 8.0 - t, 8.0 + t) if along_x else (8.0 - t, 8.0 + t, 0.0, 16.0)
        RM.aqueduct(m, *box, "x" if along_x else "y", 0.0, H, arches=((half, 16.0 - half, spring),),
                    material="tufa", seed=3801)
        return m
    RM.aqueduct(m, 8.0 - t, 8.0 + t, 8.0 - t, 8.0 + t, "x" if mask & 10 else "y", 0.0, H, material="tufa", seed=3801)
    for bit, box, axis, arch in ((2, (8.0, 16.0, 8.0 - t, 8.0 + t), "x", (8.0 + t, 16.0 - half)),
                                 (8, (0.0, 8.0, 8.0 - t, 8.0 + t), "x", (half, 8.0 - t)),
                                 (4, (8.0 - t, 8.0 + t, 8.0, 16.0), "y", (8.0 + t, 16.0 - half)),
                                 (1, (8.0 - t, 8.0 + t, 0.0, 8.0), "y", (half, 8.0 - t))):
        if mask & bit:
            RM.aqueduct(m, *box, axis, 0.0, H, arches=((arch[0], arch[1], spring),), material="tufa", seed=3801)
    return m


def _item(fn, slots=None, emitters=None):
    return Item(fn, slots=slots or {}, emitters=emitters or {})


def _walk_item(fn):
    """A joined piece whose straight looks are walkable (the aqueduct's single arches)."""
    return Item(fn, walk=lambda v: [(0, 0)] if v in ("m0", "m5", "m10") else [])


ITEMS = {f"rome.{n}": it for n, it in {
    "r_insula": _item(r_insula, {"door": [{"t": [2, 3], "face": "+y"}], "sell": [{"t": [0, 3], "face": "-y"},
                                                                                  {"t": [3, 3], "face": "-y"}]}),
    "r_insula_corner": _item(r_insula_corner, {"sell": [{"t": [1, 3], "face": "-y"}, {"t": [3, 1], "face": "-x"}]}),
    "r_insula_low": _item(r_insula_low, {"door": [{"t": [2, 2], "face": "+y"}], "sell": [{"t": [0, 2], "face": "-y"}]}),
    "r_domus": _item(r_domus, {"door": [{"t": [1, 4], "face": "+y"}], "salutatio": [{"t": [1, 5]}, {"t": [0, 5]},
                                                                                     {"t": [2, 5]}]}),
    "r_taberna": _item(r_taberna, {"sell": [{"t": [0, 1], "face": "-y"}]}),
    "r_thermopolium": _item(r_thermopolium, {"serve": [{"t": [0, 1], "face": "-y"}]}, {"steam": (4.0, 12.0, 8.0)}),
    "r_bakery": _item(r_bakery, {"work": [{"t": [1, 2], "face": "-y"}]}, {"smoke": (34.0, 22.0, 16.0)}),
    "r_fullonica": _item(r_fullonica, {"work": [{"t": [0, 2], "face": "-y"}, {"t": [1, 2], "face": "-y"}]}),
    "r_dyeworks": _item(r_dyeworks, {"work": [{"t": [1, 2], "face": "-y"}]}, {"steam": (16.0, 22.0, 6.0)}),
    "r_glass": _item(r_glass, {"work": [{"t": [0, 2], "face": "-y"}]}, {"smoke": (16.0, 22.0, 12.0)}),
    "r_smithy": _item(r_smithy, {"work": [{"t": [1, 2], "face": "-y"}]}, {"smoke": (10.0, 13.0, 17.0)}),
    "r_lacus": _item(r_lacus, {"fill": [{"t": [0, 1], "face": "-y"}]}, {"spout": (8.0, 3.6, 7.0)}),
    "r_compitum": _item(r_compitum, {"pray": [{"t": [0, 1], "face": "-y"}]}, {"incense": (8.0, 9.5, 7.0)}),
    "r_latrine": _item(r_latrine),
    "r_bath_small": _item(r_bath_small, {"door": [{"t": [1, 3], "face": "+y"}]}, {"smoke": (54.0, 6.0, 31.0)}),
    "r_horrea": _item(r_horrea, {"door": [{"t": [2, 4], "face": "+y"}]}),
    "r_crane": _item(r_crane, {"work": [{"t": [0, 2], "face": "-y"}]}),
    "r_scaffold": _item(r_scaffold),
    "r_milestone": _item(r_milestone),
    "r_stall": _item(r_stall, {"sell": [{"t": [0, -1], "face": "+y"}], "buy": [{"t": [1, 1], "face": "-y"}]}),
    "r_amphorae": _item(r_amphorae),
    "r_statue": _item(r_statue),
    "r_column_honor": _item(r_column_honor),
    "r_lamp": _item(r_lamp),
    "r_brazier": _item(r_brazier, {}, {"fire": (8.0, 8.0, 13.0)}),
    "r_bonfire": _item(r_bonfire, {}, {"bonfire": (8.0, 8.0, 11.0)}),
    "r_altar": _item(r_altar, {"sacrifice": [{"t": [0, 1], "face": "-y"}]}, {"incense": (8.0, 8.0, 12.0)}),
    "r_tomb": _item(r_tomb, {"mourn": [{"t": [0, 2], "face": "-y"}]}),
    "tomb_drum": _item(tomb_drum),
    "tomb_house": _item(tomb_house),
    "tomb_altar": _item(tomb_altar),
    "r_vine": _item(r_vine),
    "r_well": _item(r_well, {"draw": [{"t": [1, 0], "face": "-x"}]}),
    "r_vigiles": _item(r_vigiles, {"door": [{"t": [1, 2], "face": "+y"}]}),
    "r_villa_farm": _item(r_villa_farm, {"door": [{"t": [1, -1], "face": "+x"}]}),
    "r_shed": _item(r_shed),
    "mutatio": _item(mutatio, {"door": [{"t": [4, 4], "face": "+y"}], "change": [{"t": [2, 4]}, {"t": [3, 4]}]}),
    "stair_travertine": _item(stair_travertine),
    "quay": _item(quay, {"mooring": [{"t": [0, 1], "face": "+y"}]}),
    "aqua_claudia": _walk_item(aqua_claudia),
}.items()}

FRAMES = {"rome.r_bakery": 2, "rome.r_crane": 2, "rome.r_stall": 2, "rome.r_lacus": 2, "rome.r_fullonica": 2}

# Catalog facts: name, footprint, layout, count, layers, bible height, fps (animated).
KIT_INFO = {
    "r_insula": ("Insula (apartment block)", (4, 3), "rotate", 4, "BSG", 140, 0),
    "r_insula_corner": ("Corner insula with balcony", (3, 3), "rotate", 4, "BSG", 140, 0),
    "r_insula_low": ("Two-storey shop-house", (3, 2), "rotate", 4, "BSG", 85, 0),
    "r_domus": ("Domus", (5, 4), "rotate", 4, "BSG", 80, 0),
    "r_taberna": ("Shop front", (1, 1), "variant", 8, "BSG", 50, 0),
    "r_thermopolium": ("Street counter (hot food)", (1, 1), "rotate", 4, "BSG", 50, 0),
    "r_bakery": ("Bakery with donkey mills and oven", (3, 2), "rotate", 4, "BSG", 60, 2),
    "r_fullonica": ("Fullery", (3, 2), "rotate", 4, "BS", 50, 2),
    "r_dyeworks": ("Dyer's shop", (2, 2), "rotate", 4, "BS", 50, 0),
    "r_glass": ("Glass workshop", (2, 2), "rotate", 4, "BSG", 50, 0),
    "r_smithy": ("Smithy", (2, 2), "rotate", 4, "BSG", 50, 0),
    "r_lacus": ("Street fountain (lacus)", (1, 1), "rotate", 2, "B", 24, 3),
    "r_compitum": ("Crossroads shrine of the Lares", (1, 1), "rotate", 2, "BSG", 36, 0),
    "r_latrine": ("Public latrine", (2, 2), "rotate", 4, "BS", 40, 0),
    "r_bath_small": ("Neighbourhood bath (balneum)", (4, 3), "rotate", 4, "BSG", 70, 0),
    "r_horrea": ("Warehouse (horrea)", (4, 4), "rotate", 4, "BS", 60, 0),
    "r_crane": ("Treadwheel crane", (2, 2), "rotate", 2, "BS", 140, 2),
    "r_scaffold": ("Scaffolding", (1, 1), "rotate", 1, "BS", 120, 0),
    "r_milestone": ("Milestone", (1, 1), "rotate", 2, "B", 30, 0),
    "r_stall": ("Market stall", (2, 1), "variant", 6, "BS", 40, 2),
    "r_amphorae": ("Amphora stack", (1, 1), "variant", 4, "BS", 26, 0),
    "r_statue": ("Honorific statue on base", (1, 1), "rotate", 4, "BS", 60, 0),
    "r_column_honor": ("Honorary column", (1, 1), "rotate", 1, "BS", 100, 0),
    "r_lamp": ("Lantern", (1, 1), "rotate", 4, "BSG", 10, 0),
    "r_brazier": ("Brazier", (1, 1), "rotate", 1, "BSG", 24, 0),
    "r_bonfire": ("Parilia bonfire", (1, 1), "rotate", 1, "BSG", 26, 0),
    "r_altar": ("Altar", (1, 1), "rotate", 2, "BSG", 24, 0),
    "r_tomb": ("Small tomb with columbarium", (2, 2), "rotate", 4, "BS", 50, 0),
    "tomb_drum": ("Drum tomb of the Via Appia", (3, 3), "rotate", 4, "BS", 110, 0),
    "tomb_house": ("House tomb", (2, 2), "rotate", 4, "BS", 70, 0),
    "tomb_altar": ("Altar tomb", (1, 1), "rotate", 4, "BS", 40, 0),
    "r_vine": ("Pergola with vines", (1, 1), "rotate", 2, "B", 40, 0),
    "r_well": ("Garden well and basin", (1, 1), "rotate", 1, "B", 20, 0),
    "r_vigiles": ("Watch-station of the vigiles", (3, 2), "rotate", 4, "BSG", 60, 0),
    "r_villa_farm": ("Farmstead (villa rustica)", (3, 3), "rotate", 4, "BS", 70, 0),
    "r_shed": ("Field shed", (1, 2), "rotate", 4, "BS", 30, 0),
    "mutatio": ("Relay station of the state post", (6, 4), "rotate", 4, "BSG", 50, 0),
    "stair_travertine": ("Travertine stair", (1, 2), "rotate", 4, "B", 16, 0),
    "quay": ("Tiber quay", (1, 1), "rotate", 4, "B", 10, 0),
    "aqua_claudia": ("Aqua Claudia arcade", (1, 1), "connect", 1, "BS", 160, 0),
}


def catalog_items():
    from sets.rome.entries import kit_entry
    out = []
    for n, (name, fp, layout, count, layers, height, fps) in KIT_INFO.items():
        it = kit_entry(f"rome.{n}", name, fp, layout, count, layers, height, fps, ITEMS[f"rome.{n}"])
        if n == "stair_travertine":
            it.update(rise=1, axis="y")
        out.append(it)
    return out
