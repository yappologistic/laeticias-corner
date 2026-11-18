"""The Roman-time waypoints outside the city (rome.md §3.7), unique landmarks at s about 0.45
and the harbour basins symbolic in plan: Trajan's hexagonal basin at Portus, the lighthouse of
Claudius's outer harbour, the Square of the Guilds and the Capitolium of Ostia (pieces of the
Ostia town, the rest of which is kit), the sanctuary of Jupiter Latiaris on the Alban Mount,
the harbour of Brundisium with the column at the end of the Via Appia, the amphitheatre of
Capua, Trajan's arch at Beneventum and Hadrian's villa at Tibur under construction."""

import math

import numpy as np

import materials as M
import relief_roman as RR
import roman as RM
from arch import carve, ellipsoid, fill, halo, revolve, slab
from setbuild import Landmark
from sets.rome.common import FIRE, S45, T, TOGATE, paving, referrer, scaffold, stone_pine, tc, treadwheel_crane
from sets.rome.ground import amphora
from voxel import hash01, value_noise

ref = referrer("sets.rome.ostia")
S = S45


def _water(m, box, z0, z1, mask=None):
    fill(m, (*box, z0, z1), "water", mask,
         tone=lambda X, Y, Z: 0.3 * (np.sin((X * 0.7 + Y) * 0.9) > 0.9) - 0.2 * (value_noise(X, Y, Z, 6.0, 801) > 0.6))


def _horrea_row(m, x0, x1, y0, y1, h, seed, door_face="+x"):
    """A range of brick warehouses with a tiled roof and a door to each store."""
    RM.wall(m, (x0, x1, y0, y1), 0.0, h, "brick", seed)
    L = RM.face_length(door_face, x0, x1, y0, y1)
    for s0 in np.arange(2.0, L - 5.0, 7.0):
        RM.opening(m, door_face, (x0, x1, y0, y1), s0, 3.6, 0.0, h * 0.45, 1.5, frame="travertine")
    axis = "y" if (y1 - y0) > (x1 - x0) else "x"
    RM.gable(m, (x0 - 0.8, x1 + 0.8, y0 - 0.8, y1 + 0.8), h, min(x1 - x0, y1 - y0) * 0.22, axis, seed=seed + 1)


def portus_hexagon(m):
    """Trajan's hexagonal basin at Portus (opened c. 112, about 358 m a side), drawn symbolic in
    plan: the hexagon of water lined with travertine quays and mooring stones, ranges of
    warehouses round it, the canal mouth to the Tiber on the south-east, a small temple and
    the harbour office. Ships moor at the quay spots."""
    W, D = 20 * T, 18 * T
    cx, cy = D / 2, W / 2
    R = 7.2 * T

    def hexd(X, Y, r):
        u, v = np.abs(X - cx), np.abs(Y - cy)
        return np.maximum(u * 0.866 + v * 0.5, v) <= r
    fill(m, (0.0, D, 0.0, W, -3.0, 1.5), "travertine", lambda X, Y, Z: hexd(X, Y, R + 14.0),
         tone=M.paving(6.0, 4.0, 802))
    carve(m, (0.0, D, 0.0, W, -1.0, 2.0), lambda X, Y, Z: hexd(X, Y, R))
    _water(m, (0.0, D, 0.0, W), -2.0, -1.0, lambda X, Y, Z: hexd(X, Y, R))
    # The canal mouth on the south-east side.
    carve(m, (D - 3 * T, D, 2.0, 2 * T, -1.0, 2.0))
    _water(m, (D - 3 * T, D, 2.0, 2 * T), -2.0, -1.0)
    for i in range(6):          # mooring stones round the edge
        a = i * math.pi / 3 + math.pi / 6
        for f in np.linspace(-0.4, 0.4, 5):
            x = cx + math.cos(a) * R * 0.98 - math.sin(a) * f * R
            y = cy + math.sin(a) * R * 0.98 + math.cos(a) * f * R
            revolve(m, x, y, 1.5, 4.0, lambda t: 1.0, "travertine", tone=0.3)
    # Warehouse ranges round the hexagon.
    for i in range(6):
        a = i * math.pi / 3 + math.pi / 6
        ux, uy = math.cos(a), math.sin(a)
        mx, my = cx + ux * (R + 2.2 * T), cy + uy * (R + 2.2 * T)
        L = R * 0.9
        for k_ in range(3):
            f = (k_ - 1) * L * 0.62
            x, y = mx - uy * f, my + ux * f
            _horrea_row(m, x - 9.0, x + 9.0, y - 9.0, y + 9.0, 11.0, 803 + i * 3 + k_,
                        door_face=("+x" if ux > 0.3 else "-x" if ux < -0.3 else ("+y" if uy > 0 else "-y")))
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.9, H=8.0), front="+x", cols=4, deep=2, podium=2.0,
                            pediment="gods", seed=821), S, (2.0, 3 * T, W / 2 - 1.2 * T, W / 2 + 1.2 * T), 1.5)
    RM.statue(m, cx, cy - R - 6.0, 1.5, 12.0, TOGATE, material="bronze_cast", base=(4.0, 5.0))


HEX_MOORING = [{"t": [9 + dx, 10 + dy], "face": f} for dx, dy, f in ((-5, 0, "+x"), (5, 0, "-x"), (-2, -5, "+y"),
                                                                     (2, 5, "-y"), (3, -4, "+y"), (-3, 4, "-y"))]


def portus_lighthouse(m):
    """The lighthouse of Claudius's harbour at Portus, built on the sunken ship that had carried
    Caligula's obelisk: a tower of diminishing storeys on its island of concrete blocks, the
    fire burning on top (lit at night)."""
    c = 1.5 * T
    fill(m, (0.0, 3 * T, 0.0, 3 * T, -3.0, 3.0), "tufa", lambda X, Y, Z: np.hypot(X - c, Y - c) < 22.0,
         tone=M.ashlar(2.0, 5.0, 831, spread=0.9))
    z = 3.0
    for i, (w, h, mat) in enumerate(((15.0, 24.0, "travertine"), (11.0, 20.0, "travertine"), (8.0, 14.0, "brick"),
                                     (5.0, 10.0, "brick"))):
        RM.wall(m, (c - w, c + w, c - w, c + w), z, z + h, "travertine" if mat == "travertine" else "brick", 832 + i)
        RM.cornice(m, (c - w, c + w, c - w, c + w), z + h - 1.0, 1.0, 0.8, "travertine")
        for f in ("+x", "+y"):
            RM.window(m, f, (c - w, c + w, c - w, c + w), w - 1.5, 3.0, z + h * 0.4, h * 0.3, arched=True,
                      lit=0.3)
        z += h
    revolve(m, c, c, z, z + 3.0, lambda t: 4.0, "bronze", tone=0.2)
    for i in range(6):
        a = i * 1.05
        ellipsoid(m, (c + math.cos(a) * 1.4, c + math.sin(a) * 1.4, z + 5.0), (1.6, 1.6, 3.0), "fire", 0.2 * (i % 2))
    halo(m, c, c, z + 5.0, 30.0, FIRE, 1.0)


def ostia_guilds(m):
    """The Square of the Guilds at Ostia (Piazzale delle Corporazioni): a long colonnaded
    square behind the theatre, a small temple in the middle, the offices of the shipping guilds
    in the porticoes, each with its black-and-white mosaic (a ship, a lighthouse, an elephant,
    amphorae) on the pavement before it."""
    W, D = 12 * T, 6 * T
    fill(m, (0.0, D, 0.0, W, 0.0, 0.6), "grass", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 841) - 0.5) * 0.7)
    o = RM.ROrder("tuscan", D=0.6, H=5.0, shaft="brick", trim="travertine", fluted=False)
    for a, b, front in (((6.0, 6.0), (6.0, W - 6.0), "+x"), ((D - 6.0, 6.0), (D - 6.0, W - 6.0), "-x")):
        RM.colonnade(m, a, b, 0.0, 16, o, S, 10.0, front, seed=int(a[0]))
        xm = a[0] + (5.0 if front == "+x" else -9.0)
        for i in range(12):
            y = 10.0 + i * (W - 20.0) / 12
            fill(m, (xm, xm + 4.0, y, y + 12.0, 0.0, 0.7), "whitewash", tone=0.2)
            fill(m, (xm, xm + 4.0, y, y + 12.0, 0.0, 0.75), "gloss",
                 lambda X, Y, Z, y=y, i=i: (hash01(np.floor(X * 2).astype(np.int64), np.floor((Y - y) * 2).astype(np.int64),
                                                   i, 842) < 0.45) & (np.abs(X - xm - 2.0) < 1.6), tone=0.1,
                 only_solid=True)
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.6, H=5.5), front="+x", cols=4, deep=1, podium=1.5,
                            pediment="gods", seed=843), S, (D / 2 - 18.0, D / 2 + 18.0, W / 2 - 14.0, W / 2 + 14.0))


def ostia_capitolium(m):
    """The Capitolium of Ostia (Hadrianic, 120s): a tall temple of brick faced with marble on a
    high podium with a broad stair, facing the forum."""
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.3, H=13.0), front="+x", cols=6, deep=2, podium=5.0,
                            podium_kind="brick", cella_kind="brick", pediment="triad", seed=851, stair_frac=0.3),
              S, (2.0, 6 * T - 2.0, 2.0, 4 * T - 2.0))


def latiaris(m):
    """The sanctuary of Jupiter Latiaris on the summit of the Alban Mount, where the consuls held
    the Latin Festival: a small temple in a walled precinct on the rocky top, a great altar,
    the paved Via Sacra coming up, holm oaks and pines."""
    W, D = 6 * T, 6 * T
    from arch import field_fill
    field_fill(m, (0.0, D, 0.0, W, 0.0, 10.0), lambda X, Y, Z: Z - (8.0 - 0.06 * (np.hypot(X - D / 2, Y - W / 2)) ** 1.2 +
                                                                      value_noise(X, Y, Z * 0, 5.0, 861) * 2.0),
               "tufa", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 862) - 0.5) * 0.8)
    paving(m, (12.0, D - 12.0, 12.0, W - 12.0), 7.0, 8.0, "travertine", 5.0, 4.0, 863)
    RM.temple(m, RM.RTemple(order=RM.ROrder("tuscan", D=0.9, H=7.0, shaft="tufa", trim="tufa", fluted=False),
                            front="+x", cols=4, deep=2, podium=2.0, podium_kind="tufa", cella_kind="stucco",
                            pediment="gods", seed=864), S, (14.0, 3.6 * T, W / 2 - 22.0, W / 2 + 22.0), 8.0)
    slab(m, 4 * T, 4 * T + 10.0, W / 2 - 6.0, W / 2 + 6.0, 8.0, 12.0, "tufa", tone=0.2)
    fill(m, (4 * T + 2.0, 4 * T + 8.0, W / 2 - 4.0, W / 2 + 4.0, 12.0, 13.0), "ember")
    halo(m, 4 * T + 5.0, W / 2, 14.0, 10.0, FIRE, 0.6)
    for wb in ((8.0, 10.0, 8.0, W - 8.0), (D - 10.0, D - 8.0, 8.0, W - 8.0 - 20.0), (8.0, D - 8.0, 8.0, 10.0),
               (8.0, D - 8.0, W - 10.0, W - 8.0)):
        RM.wall(m, wb, 6.0, 11.0, "tufa", 865)
    for i, (x, y) in enumerate(((6.0, 6.0), (D - 6.0, 10.0), (10.0, W - 6.0))):
        stone_pine(m, x, y, 4.0, 30.0, seed=i)


def brundisium_harbour(m):
    """The harbour of Brundisium where the Via Appia meets the sea: travertine quays round the
    inner basin with mooring stones and bollards, warehouses, a crane, amphorae for Greece and
    the East, and the column marking the road's end (its date is debated: a simple marker)."""
    W, D = 16 * T, 12 * T
    slab(m, 0.0, 5 * T, 0.0, W, -3.0, 1.5, "travertine", tone=RM.travertine(2.4, 7.0, 871))
    paving(m, (0.0, 5 * T, 0.0, W), 1.0, 1.5, "travertine", 6.0, 4.0, 872)
    _water(m, (5 * T, D, 0.0, W), -2.0, -1.0)
    for ty in BR_BOLLARDS:
        revolve(m, 5 * T - 4.0, tc(ty), 1.5, 4.0, lambda t: 1.0, "travertine", tone=0.3)
    for i in range(4):
        _horrea_row(m, 6.0, 3 * T - 4.0, 6.0 + i * 4 * T, 4 * T - 4.0 + i * 4 * T, 12.0, 873 + i)
    for i, (tx, ty) in enumerate(BR_AMPHORAE):
        for j in range(8):
            amphora(m, tx * T + 2.0 + (j % 4) * 3.6, ty * T + 3.0 + (j // 4) * 6.0, 1.5,
                    ("wine", "dressel20", "african")[i])
    treadwheel_crane(m, tc(BR_CRANE[0]), tc(BR_CRANE[1]), 1.5, 40.0, along="x", load="marble")
    slab(m, 3 * T + 4.0, 3 * T + 12.0, 15 * T + 4.0, 15 * T + 12.0, 1.5, 4.5, "marble", tone=0.25)
    RM.column(m, 3 * T + 8.0, 15 * T + 8.0, 4.5, RM.ROrder("corinthian", D=1.1, H=12.0, shaft="cipollino",
                                                           fluted=False), S)


def capua_amphitheatre(m):
    """The amphitheatre of Capua, the second largest in Italy: four storeys of arcades in
    travertine with keystone busts of gods, its arena surrounded by marble seats."""
    W, D = 10 * T, 8 * T
    el = RM.Ellipse(D / 2, W / 2, D / 2 - 2.0, W / 2 - 2.0)
    top = RM.ring_facade(m, el, 0.0, [RM.Storey(S.v(9.0), "arcade", "tuscan", (0.6, 0.62)),
                                      RM.Storey(S.v(9.0), "arcade", "tuscan", (0.6, 0.6), statues=True),
                                      RM.Storey(S.v(9.0), "arcade", "tuscan", (0.6, 0.6), statues=True),
                                      RM.Storey(S.v(6.0), "attic", "tuscan", (0.2, 0.5), masts=1)],
                         56, 5.0, S, gaps=(0, 14, 28, 42), phase=0.5, seed=881)
    arena = RM.Ellipse(D / 2, W / 2, el.a * 0.42, el.b * 0.52)
    upper = RM.Ellipse(D / 2, W / 2, el.a - 7.0, el.b - 7.0)
    fill(m, (0.0, D, 0.0, W, 0.0, top - 4.0), "tufa",
         lambda X, Y, Z: (np.hypot((X - D / 2) / upper.a, (Y - W / 2) / upper.b) <= 1) &
         (np.hypot((X - D / 2) / arena.a, (Y - W / 2) / arena.b) > 1) & (Z < 2.0), tone=-0.2)
    RM.cavea(m, arena, upper, 3.0, top - 4.0, material="marble", upper_mat="travertine", bands=3, aisles=28, seed=882)
    fill(m, (0.0, D, 0.0, W, 0.0, 1.0), "poros", lambda X, Y, Z: np.hypot((X - D / 2) / arena.a, (Y - W / 2) / arena.b)
         <= 1, tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 883) - 0.5) * 0.6)


def arch_beneventum(m):
    """Trajan's arch at Beneventum (dedicated 114) where the Via Traiana leaves the Appia: a
    single bay of marble covered in reliefs of the emperor's deeds, Victories in the spandrels,
    the attic inscribed; the road passes under it (one walk tile)."""
    from arch import Scale
    Sb = Scale(0.75)
    pier = (Sb.h(15.6) - T) / 2
    img, cmap = RR.triumph_image(int(2 * T * 2), int(Sb.v(3.0) * 2))
    RM.triumphal_arch(m, (2.0, T - 2.0, T - pier, 2 * T + pier), "+x", Sb, z0=0.0, bays=1,
                      order=RM.ROrder("composite", D=0.85, H=8.5), relief=(img, cmap), seed=891, pier=pier)
    for face, box in (("+x", (2.0, T - 2.0, T - pier, 2 * T + pier)),):
        L = RM.face_length(face, *box)
        for s0 in (1.0, L - pier + 1.0):
            sp, sc = RR.sacrifice_image(int((pier - 2.0) * 2), 14)
            from relief import emboss
            emboss(m, face, box, s0, 14.0 + Sb.v(1.2) + 8.0, sp, cmap=sc)


def hadrian_villa(m):
    """Hadrian's villa at Tibur, rising since about 118: the round Maritime Theatre (a little
    house on an island in a moat inside a ring colonnade), the long Pecile pool with its
    portico, a domed hall in scaffolding, cranes and stacked materials."""
    W, D = 24 * T, 22 * T
    fill(m, (0.0, D, 0.0, W, 0.0, 0.6), "grass", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 4.0, 901) - 0.5) * 0.8)
    cx, cy, R = 5 * T, 6 * T, 3.6 * T
    revolve(m, cx, cy, 0.0, S.v(9.0), lambda t: R, "brick", tone=RM.brick(902))
    carve(m, (cx - R, cx + R, cy - R, cy + R, 0.6, S.v(9.0) + 1.0), lambda X, Y, Z: np.hypot(X - cx, Y - cy) < R - 3.0)
    _water(m, (cx - R, cx + R, cy - R, cy + R), 0.0, 1.0, lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < R - 10.0) &
           (np.hypot(X - cx, Y - cy) > R - 20.0))
    for i in range(24):
        a = i * math.pi / 12
        RM.column(m, cx + math.cos(a) * (R - 6.0), cy + math.sin(a) * (R - 6.0), 0.6,
                  RM.ROrder("ionic", D=0.6, H=5.5), S)
    RM.wall(m, (cx - 16.0, cx + 16.0, cy - 16.0, cy + 16.0), 0.0, 14.0, "stucco", 903, "whitewash")
    RM.hip(m, (cx - 17.0, cx + 17.0, cy - 17.0, cy + 17.0), 14.0, 5.0, seed=904)
    # The Pecile: a long pool inside a great portico.
    px0, px1, py0, py1 = 11 * T, 20 * T, 3 * T, W - 3 * T
    RM.wall(m, (px0, px1, py0, py0 + 4.0), 0.0, S.v(9.0), "brick", 905)
    RM.wall(m, (px0, px1, py1 - 4.0, py1), 0.0, S.v(9.0), "brick", 906)
    _water(m, (px0 + 3 * T, px1 - 3 * T, py0 + 3 * T, py1 - 3 * T), 0.0, 1.0)
    slab(m, px0 + 3 * T - 2.0, px1 - 3 * T + 2.0, py0 + 3 * T - 2.0, py1 - 3 * T + 2.0, 0.0, 0.8, "marble", tone=0.2)
    RM.colonnade(m, (px0 + 8.0, py0 + 12.0), (px1 - 8.0, py0 + 12.0), 0.0, 10, RM.ROrder("corinthian", D=0.7, H=6.5),
                 S, 8.0, "+y", back=False, seed=907)
    # A domed hall in scaffolding, materials and cranes.
    hx, hy = 6 * T, 17 * T
    revolve(m, hx, hy, 0.0, S.v(14.0), lambda t: 2.2 * T, "brick", tone=RM.brick(908))
    RM.dome(m, hx, hy, S.v(14.0), 2.2 * T - 1.0, "brick", rise=1.4 * T, thick=4.0, oculus=8.0, tiles=False,
            coffers=False, seed=909)
    carve(m, (hx - 2.2 * T, hx, hy - 2.2 * T, hy + 2.2 * T, S.v(14.0) + 8.0, S.v(14.0) + 2 * T))
    scaffold(m, hx - 2.4 * T, hx - 2.0 * T, hy - 20.0, hy + 20.0, 0.0, S.v(14.0) + 12.0, decks=4)
    treadwheel_crane(m, hx + 3 * T, hy, 0.0, 44.0, along="x", load="marble")
    for i in range(5):
        slab(m, 16 * T + i * 8.0, 16 * T + i * 8.0 + 6.0, 15 * T, 17 * T, 0.0, 3.0 + i % 2, "marble", tone=0.1)


# Brundisium quay furniture by tile (x 3..4 is the quay, y along it); the rest of the quay walks.
BR_BOLLARDS = (1, 5, 9, 13)
BR_AMPHORAE = ((3, 4), (3, 9), (3, 12))
BR_CRANE = (4, 7)
BR_SOLID = {(4, y) for y in BR_BOLLARDS} | set(BR_AMPHORAE) | {BR_CRANE, (3, 7), (4, 6), (4, 8), (5, 7), (3, 15)}
BR_WALK = [(x, y) for x in (3, 4) for y in range(16) if (x, y) not in BR_SOLID]

LANDMARKS = {
    "rome.portus_hexagon": Landmark((18, 20), (-3, 40), ref("portus_hexagon"), district=9,
                                    slots={"mooring": HEX_MOORING}),
    "rome.portus_lighthouse": Landmark((3, 3), (-3, 112), ref("portus_lighthouse"), district=9),
    "rome.ostia_guilds": Landmark((6, 12), (0, 40), ref("ostia_guilds"), district=9),
    "rome.ostia_capitolium": Landmark((6, 4), (0, 96), ref("ostia_capitolium"), district=9),
    "rome.latiaris": Landmark((6, 6), (0, 64), ref("latiaris"), district=9,
                              slots={"sacrifice": [{"t": [6, 3], "face": "-x"}]}),
    "rome.brundisium_harbour": Landmark((12, 16), (-3, 64), ref("brundisium_harbour"), district=9,
                                        walk=BR_WALK, floor={t: 1.5 for t in BR_WALK},
                                        slots={"mooring": [{"t": [4, 2], "face": "+x"}, {"t": [4, 10], "face": "+x"},
                                                           {"t": [4, 14], "face": "+x"}]}),
    "rome.capua_amphitheatre": Landmark((8, 10), (0, 88), ref("capua_amphitheatre"), district=9),
    "rome.arch_beneventum": Landmark((1, 3), (0, 80), ref("arch_beneventum"), district=9, walk=[(0, 1)]),
    "rome.hadrian_villa": Landmark((22, 24), (0, 64), ref("hadrian_villa"), district=9),
}

INFO = {
    "rome.portus_hexagon": ("Trajan's harbour at Portus", 0.11, 40, "BS", "portus_hexagon"),
    "rome.portus_lighthouse": ("Lighthouse of Portus", 0.45, 160, "BSG", "portus_lighthouse"),
    "rome.ostia_guilds": ("Square of the Guilds, Ostia", 0.45, 40, "BS", "ostia_guilds"),
    "rome.ostia_capitolium": ("Capitolium of Ostia", 0.45, 110, "BS", "ostia_capitolium"),
    "rome.latiaris": ("Sanctuary of Jupiter Latiaris", 0.45, 70, "BSG", "latiaris"),
    "rome.brundisium_harbour": ("Harbour of Brundisium", 0.45, 70, "BS", "brundisium_harbour"),
    "rome.capua_amphitheatre": ("Amphitheatre of Capua", 0.45, 110, "BS", "capua_amphitheatre"),
    "rome.arch_beneventum": ("Arch of Trajan at Beneventum", 0.75, 100, "BS", "arch_beneventum"),
    "rome.hadrian_villa": ("Hadrian's Villa at Tibur", 0.45, 110, "BS", "hadrian_villa"),
}
