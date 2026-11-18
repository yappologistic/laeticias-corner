"""The Palatine and the Circus Maximus valley (rome.md §2.3 D8-D9, §3.2): the Domus Flavia
(throne hall, basilica, peristyle with its fountain maze, the dining hall between nymphaea), the
Domus Augustana with its curved exedra over the Circus, the Domus Tiberiana, the garden
"stadium", the Temple of Apollo, the House of Augustus, the Hut of Romulus, the Lupercal at the
foot of the hill, the Circus Maximus at s = 0.33 and the Porta Capena where the Via Appia
begins."""

import math

import numpy as np

import materials as M
import roman as RM
from arch import carve, ellipsoid, fill, revolve, rod, slab
from setbuild import Landmark
from sets.rome.common import S33, S65, T, box_hedge, lamp, laurel, paving, plane_tree, referrer, torch
from voxel import hash01, value_noise

ref = referrer("sets.rome.palatine")
S = S65


def _hall(m, box, h, seed, roof_axis, porch_face=None, n_cols=0, glow=0.0, facing="veneer"):
    """A palace hall: brick walls faced in marble on the outside, a tiled gable roof, tall
    arched windows of glass, an optional porch of columns before its door."""
    RM.wall(m, box, 0.0, h, facing, seed, "marble" if facing == "veneer" else None)
    RM.cornice(m, box, h - 1.4, 1.4, 1.0)
    across = (box[3] - box[2]) if roof_axis == "x" else (box[1] - box[0])
    RM.gable(m, (box[0] - 1.0, box[1] + 1.0, box[2] - 1.0, box[3] + 1.0), h, across / 2 * 0.34, roof_axis, seed=seed)
    for f in ("+x", "+y"):
        L = RM.face_length(f, *box)
        for s0 in np.arange(5.0, L - 8.0, 11.0):
            RM.window(m, f, box, s0, 4.0, h * 0.5, h * 0.25, arched=True, glass=True, lit=glow)
    if porch_face and n_cols:
        L = RM.face_length(porch_face, *box)
        a = RM.face_point(porch_face, box, 4.0, -5.0)
        b = RM.face_point(porch_face, box, L - 4.0, -5.0)
        o = RM.ROrder("corinthian", D=0.9, H=h / S.v(1.0) * 0.6, shaft="porphyry" if seed % 2 else "giallo",
                      fluted=False)
        for i in range(n_cols):
            f_ = i / max(n_cols - 1, 1)
            RM.column(m, a[0] + (b[0] - a[0]) * f_, a[1] + (b[1] - a[1]) * f_, 0.0, o, S)


def domus_flavia(m):
    """The Domus Flavia, Domitian's state palace: on the north the throne hall (aula regia)
    between the basilica and the lararium, behind them the great peristyle with its octagonal
    fountain maze in a pool, on the south the dining hall (cenatio Iovis) with an oval nymphaeum
    on each side; marble facings, porphyry and giallo columns, gilded roof ornaments, lamps."""
    W, D = 14 * T, 11 * T
    _hall(m, (2.0, 3.6 * T, 4.2 * T, 9.8 * T), S.v(30.0), 501, "x", porch_face="-x", n_cols=6, glow=0.4)
    _hall(m, (2.0, 3.6 * T, 2.0, 4.0 * T), S.v(22.0), 502, "x", glow=0.3)
    _hall(m, (2.0, 3.6 * T, 10.0 * T, W - 2.0), S.v(18.0), 503, "x", glow=0.3)
    # Peristyle: a colonnade round a pool with the maze of low walls and an octagonal centre.
    px0, px1, py0, py1 = 3.9 * T, 7.4 * T, 1.5 * T, W - 1.5 * T
    paving(m, (px0, px1, py0, py1), 0.0, 0.8, "marble", 6.0, 6.0, 504)
    cx, cy = (px0 + px1) / 2, (py0 + py1) / 2
    fill(m, (px0 + 10, px1 - 10, py0 + 14, py1 - 14, 0.0, 1.2), "water",
         tone=lambda X, Y, Z: 0.3 * (np.sin((X + Y) * 1.6) > 0.85))

    def maze(X, Y, Z):
        u, v = np.abs(X - cx), np.abs(Y - cy)
        oct_ = np.maximum(np.maximum(u, v), (u + v) * 0.72)
        return ((oct_ % 6.0) < 0.9) & (oct_ < 30.0) & ~((np.abs(Y - cy) < 1.5) & (oct_ > 6.0))
    fill(m, (px0, px1, py0, py1, 0.0, 2.6), "marble", maze, tone=0.3)
    o = RM.ROrder("corinthian", D=0.65, H=6.0, shaft="giallo", fluted=False)
    for x in np.linspace(px0 + 4, px1 - 4, 6):
        for y in (py0 + 4, py1 - 4):
            RM.column(m, x, y, 0.8, o, S)
    for y in np.linspace(py0 + 4, py1 - 4, 12):
        for x in (px0 + 4, px1 - 4):
            RM.column(m, x, y, 0.8, o, S)
    RM.lean_to(m, (px0, px1, py0 - 6, py0 + 8), 0.8 + S.v(6.0), 0.8 + S.v(8.0), "-y", "terracotta", 505)
    RM.lean_to(m, (px0, px1, py1 - 8, py1 + 6), 0.8 + S.v(6.0), 0.8 + S.v(8.0), "+y", "terracotta", 506)
    # Dining hall with nymphaea.
    _hall(m, (7.6 * T, D - 2.0, 4.5 * T, 9.5 * T), S.v(24.0), 507, "x", porch_face="-x", n_cols=6, glow=0.5)
    for yc in (2.4 * T, W - 2.4 * T):
        RM.wall(m, (7.8 * T, D - 4.0, yc - 1.8 * T, yc + 1.8 * T), 0.0, 6.0, "veneer", 508, "cipollino")
        carve(m, (7.8 * T + 3, D - 7.0, yc - 1.8 * T + 3, yc + 1.8 * T - 3, 1.0, 6.0))
        fill(m, (7.8 * T + 3, D - 7.0, yc - 1.8 * T + 3, yc + 1.8 * T - 3, 0.0, 2.2), "water",
             lambda X, Y, Z, yc=yc: np.hypot((X - 9.2 * T) / 18.0, (Y - yc) / 22.0) <= 1,
             tone=lambda X, Y, Z: 0.3 * (np.sin(X + Y) > 0.8))
        revolve(m, 9.2 * T, yc, 0.0, 7.0, lambda t: 3.0 - 2.0 * t, "marble", tone=0.2)


def domus_augustana(m):
    """The Domus Augustana, the emperors' residence: the upper peristyle with a pool and a
    little temple on an island, rooms round it, and on the south the curved exedra of the
    lower palace facing the Circus over high brick walls, a loggia on top."""
    W, D = 14 * T, 9 * T
    RM.wall(m, (2.0, 2.6 * T, 2.0, W - 2.0), 0.0, S.v(14.0), "veneer", 511, "marble")
    RM.hip(m, (1.0, 2.6 * T + 1.0, 1.0, W - 1.0), S.v(14.0), 8.0, seed=512)
    px0, px1 = 2.8 * T, 5.6 * T
    paving(m, (px0, px1, 2 * T, W - 2 * T), 0.0, 0.8, "marble", 6.0, 6.0, 513)
    fill(m, (px0 + 6, px1 - 6, 2 * T + 8, W - 2 * T - 8, 0.0, 1.0), "water",
         tone=lambda X, Y, Z: 0.3 * (np.sin((X - Y) * 1.4) > 0.85))
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.5, H=4.5), front="+x", cols=4, deep=1, podium=1.0,
                            pediment=None, acroteria=None, inscription=False, seed=514), S,
              (px0 + 14, px1 - 14, W / 2 - 14, W / 2 + 14), 0.8)
    for y0, y1 in ((2.0, 2 * T), (W - 2 * T, W - 2.0)):
        RM.wall(m, (px0, px1, y0, y1), 0.0, S.v(12.0), "brick", 515)
        RM.hip(m, (px0 - 1, px1 + 1, y0 - 1, y1 + 1), S.v(12.0), 6.0, seed=516)
    # The exedra over the Circus: a curved brick façade in three storeys of arched windows.
    cx, cy, R = D + 2 * T, W / 2, 3.6 * T
    el = RM.Ellipse(cx, cy, R, R * 1.2)
    RM.ring_facade(m, el, 0.0, [RM.Storey(S.v(9.0), "windows", "tuscan", material="brick"),
                                RM.Storey(S.v(8.0), "arcade", "corinthian", (0.5, 0.6), material="brick"),
                                RM.Storey(S.v(6.0), "arcade", "corinthian", (0.5, 0.6), material="travertine")],
                   30, 8.0, S, arc=(math.pi * 0.62, math.pi * 1.38 - 2 * math.pi), inward=True, seed=517)
    fill(m, (5.6 * T, D, 2.0, W - 2.0, 0.0, S.v(20.0)), "brick",
         lambda X, Y, Z: np.hypot((X - cx) / (R + 8.0), (Y - cy) / (R * 1.2 + 8.0)) > 1, tone=RM.brick(518))
    for f in ("+x", "+y"):
        L = RM.face_length(f, 5.6 * T, D, 2.0, W - 2.0)
        for s0 in np.arange(6.0, L - 8.0, 10.0):
            RM.window(m, f, (5.6 * T, D, 2.0, W - 2.0), s0, 3.0, S.v(14.0), 4.0, arched=True, lit=0.4, glass=True)
    RM.cornice(m, (5.6 * T, D, 2.0, W - 2.0), S.v(20.0) - 1.4, 1.4, 1.0)
    for x, y in ((6.2 * T, 3.0), (6.2 * T, W - 3.0)):
        torch(m, x, y, S.v(20.0), 5.0, 0.6)


def palatine_tiberiana(m):
    """The Domus Tiberiana on the north edge of the hill: a long palace block over arcaded
    substructures toward the Forum, gardens on its roof terraces."""
    W, D = 13 * T, 7 * T
    RM.wall(m, (2.0, D - 2.0, 2.0, W - 2.0), 0.0, S.v(12.0), "brick", 521)
    RM.arcade_front(m, "+x", (2.0, D - 2.0, 2.0, W - 2.0), 0.0, [(S.v(12.0), "tuscan", "brick")], 12, depth=2.0)
    # The roof garden (QA4 V-A-009: it read as flat brown): lawns between gravel walks.
    fill(m, (6.0, D - 6.0, 6.0, W - 6.0, S.v(12.0), S.v(12.0) + 1.0), "grass",
         tone=lambda X, Y, Z: (value_noise(X, Y, Z * 0, 3.0, 524) - 0.5) * 0.9)
    fill(m, (6.0, D - 6.0, 6.0, W - 6.0, S.v(12.0), S.v(12.0) + 1.0), "travertine",
         lambda X, Y, Z: (np.abs(X - D / 2) < 2.0) | ((Y - 6.0) % 36.0 < 3.0) | (np.abs(X - 8.0) < 2.0) |
         (np.abs(X - (D - 8.0)) < 2.0), tone=lambda X, Y, Z: (value_noise(X * 3, Y * 3, Z, 1.0, 525) - 0.5) * 0.6)
    for i in range(5):
        box_hedge(m, 8.0, D - 8.0, 10.0 + i * 36.0, 13.0 + i * 36.0, S.v(12.0) + 1.0)
        laurel(m, D / 2, 26.0 + i * 36.0, S.v(12.0) + 1.0, 14.0, seed=i)
    RM.wall(m, (2.0, 2.4 * T, 3 * T, 6 * T), S.v(12.0), S.v(20.0), "veneer", 522, "marble")
    RM.hip(m, (1.0, 2.4 * T + 1, 3 * T - 1, 6 * T + 1), S.v(20.0), 6.0, seed=523)


def palatine_stadium(m):
    """The Palatine "stadium": a long sunken garden like a racecourse, two-storey porticoes
    round it, a curved south end, a great viewing exedra on the east, planes and box hedges."""
    W, D = 6 * T, 19 * T
    RM.wall(m, (2.0, D - 2.0, 2.0, W - 2.0), 0.0, S.v(9.0), "brick", 531)
    carve(m, (8.0, D - 8.0, 8.0, W - 8.0, 0.0, S.v(9.0)))
    fill(m, (8.0, D - 8.0, 8.0, W - 8.0, 0.0, 1.0), "grass", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 532) - 0.5))
    box_hedge(m, 20.0, D - 20.0, W / 2 - 2.0, W / 2 + 2.0, 1.0)
    for x in np.arange(24.0, D - 20.0, 26.0):
        plane_tree(m, x, 20.0, 1.0, 34.0, seed=int(x))
    o = RM.ROrder("corinthian", D=0.55, H=5.0, shaft="granite_pink", fluted=False)
    for x in np.linspace(12.0, D - 12.0, 24):
        for y in (11.0, W - 11.0):
            RM.column(m, x, y, 0.0, o, S)
    RM.lean_to(m, (2.0, D - 2.0, 2.0, 13.0), S.v(5.5), S.v(9.0), "-y", "terracotta", 533)
    RM.lean_to(m, (2.0, D - 2.0, W - 13.0, W - 2.0), S.v(5.5), S.v(9.0), "+y", "terracotta", 534)


def apollo_palatinus(m):
    """The Temple of Apollo Palatinus, Augustus's temple of Luna marble, facing the Circus."""
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.4, H=13.0), front="+x", cols=6, deep=2,
                            plan="peripteral", podium=4.0, pediment="gods", roof="terracotta", seed=541),
              S, (2.0, 6 * T - 2.0, 2.0, 6 * T - 2.0))
    laurel(m, 6 * T - 4.0, 4.0, 0.0, 18.0, seed=1)
    laurel(m, 6 * T - 4.0, 6 * T - 4.0, 0.0, 18.0, seed=2)


def house_augustus(m):
    """The House of Augustus: modest rooms round two peristyles, painted walls (the brightest
    in red and yellow ochre), laurels at the door."""
    W, D = 5 * T, 5 * T
    for wb in ((2.0, 2 * T, 2.0, W - 2.0), (3 * T, D - 2.0, 2.0, W - 2.0), (2 * T, 3 * T, 2.0, 2 * T)):
        RM.wall(m, wb, 0.0, S.v(7.0), "stucco", 551, "ochre")
        RM.hip(m, (wb[0] - 1, wb[1] + 1, wb[2] - 1, wb[3] + 1), S.v(7.0), 5.0, seed=552)
    paving(m, (2 * T, 3 * T, 2 * T, W - 2.0), 0.0, 0.6, "brick", 3.0, 3.0, 553)
    laurel(m, D - 1.0, W / 2 - 6.0, 0.0, 14.0, seed=3)
    laurel(m, D - 1.0, W / 2 + 6.0, 0.0, 14.0, seed=4)


def casa_romuli(m):
    """The Hut of Romulus: a small oval hut of wattle and daub with a steep thatched roof and a
    wooden porch post, piously rebuilt whenever damaged; a fence round it."""
    c = 8.0
    fill(m, (1.0, 15.0, 2.0, 14.0, 0.0, 6.0), "mudbrick",
         lambda X, Y, Z: np.hypot((X - c) / 5.5, (Y - c) / 4.6) <= 1,
         tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z * 2, 2.0, 561) - 0.5) * 0.7)
    fill(m, (0.0, 16.0, 0.0, 16.0, 6.0, 15.0), "straw",
         lambda X, Y, Z: np.hypot((X - c) / 6.6, (Y - c) / 5.6) <= 1 - (Z - 6.0) / 9.0,
         tone=lambda X, Y, Z: -0.4 * ((Z * 1.5) % 1.0 < 0.3) + 0.1)
    fill(m, (13.0, 14.6, 7.0, 9.0, 0.0, 4.5), "ink")
    rod(m, (14.6, 6.0, 0.0), (14.6, 6.0, 7.0), 0.4, "wood")
    rod(m, (14.6, 10.0, 0.0), (14.6, 10.0, 7.0), 0.4, "wood")


def lupercal(m):
    """The Lupercal: the cave at the foot of the Palatine where the she-wolf nursed the twins,
    a shrine front of tufa, the bronze she-wolf with Romulus and Remus, and a fig tree (the
    Ficus Ruminalis tradition)."""
    from arch import field_fill
    field_fill(m, (0.0, 2 * T, 0.0, 2 * T, 0.0, 22.0),
               lambda X, Y, Z: Z - (20.0 - 0.8 * X + 3.0 * value_noise(X, Y, Z * 0, 5.0, 571) - 6.0 * (Y > 20)),
               "tufa", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 572) - 0.5) * 0.8)
    carve(m, (12.0, 2 * T, 8.0, 22.0, 0.0, 10.0),
          lambda X, Y, Z: np.hypot((Y - 15.0) / 6.0, Z / 9.0) < 1)
    fill(m, (12.0, 2 * T, 8.0, 22.0, 0.0, 9.0), "ink",
         lambda X, Y, Z: (np.hypot((Y - 15.0) / 5.0, Z / 8.0) < 1) & (X < 16.0), tone=0.0)
    slab(m, 2 * T - 6.0, 2 * T - 2.0, 9.0, 21.0, 0.0, 2.0, "tufa", tone=0.2)
    # The she-wolf: a bronze beast standing over two small boys.
    ellipsoid(m, (2 * T - 4.0, 15.0, 4.4), (1.6, 3.4, 1.4), "bronze_cast", 0.2)
    ellipsoid(m, (2 * T - 4.0, 11.8, 5.4), (1.0, 1.2, 1.0), "bronze_cast", 0.3)
    for yy in (13.0, 17.4):
        for xx in (-0.9, 0.9):
            rod(m, (2 * T - 4.0 + xx, yy, 3.6), (2 * T - 4.0 + xx, yy, 2.0), 0.4, "bronze_cast", 0.1)
    for yy in (14.5, 16.0):
        ellipsoid(m, (2 * T - 4.0, yy, 2.6), (0.6, 0.6, 0.6), "bronze_cast", 0.3)
    from sets.athens.kit import _fig
    _fig(m, 2 * T - 6.0, 26.0, 0.0, 14.0, 573)


def circus_maximus(m):
    """The Circus Maximus at s = 0.33: the long sand track inside tiers of seating on three
    sides, the outer façade three storeys of arcades with shops below; down the middle the
    barrier (spina) with Augustus's obelisk, shrines, the seven bronze dolphins and the seven
    eggs that count the laps, basins of water and the turning posts (metae) at each end; the
    twelve starting gates (carceres) between towers at the west end, the imperial box
    (pulvinar) on the Palatine side, and the triple arch of Titus in the curved east end."""
    Sc = S33
    W, D = 51 * T, 10 * T                # y (west), x (south)
    R = D / 2 - 1.0                      # radius of the curved end
    cx, cy = D / 2, R + 1.0
    thick = 7.0
    cav = Sc.h(30.0)
    zt = Sc.v(28.0)
    storeys = [RM.Storey(Sc.v(10.0), "shops", "tuscan", (0.55, 0.6), material="travertine"),
               RM.Storey(Sc.v(9.5), "arcade", "tuscan", (0.6, 0.62), material="travertine"),
               RM.Storey(Sc.v(8.5), "arcade", "corinthian", (0.55, 0.6), material="travertine")]
    el = RM.Ellipse(cx, cy, R, R)
    RM.ring_facade(m, el, 0.0, storeys, 40, thick, Sc, arc=(-math.pi, 0.0), seed=581)
    x_end = W - 4 * T                    # carceres line
    for side, (x0, x1) in ((1, (D - 1.0 - thick, D - 1.0)), (-1, (1.0, 1.0 + thick))):
        wb = (x0, x1, cy, x_end)
        face = "+x" if side > 0 else "-x"
        RM.wall(m, wb, 0.0, zt, "travertine", 582)
        L = x_end - cy
        RM.arcade_front(m, face, wb, 0.0, [(storeys[0].h, "tuscan", "travertine"), (storeys[1].h, "tuscan", "travertine"),
                                           (storeys[2].h, "corinthian", "travertine")], int(L / 16), depth=3.0)
    # Seating: straight sides and the curved end, steps every 2 units, three zones.
    track_x0, track_x1 = 1.0 + thick + cav, D - 1.0 - thick - cav

    def seats(X, Y, Z):
        north = (X >= 1.0 + thick) & (X < track_x0) & (Y >= cy) & (Y < x_end)
        south = (X > track_x1) & (X <= D - 1.0 - thick) & (Y >= cy) & (Y < x_end)
        r = np.hypot(X - cx, Y - cy)
        curve = (Y < cy) & (r < R - thick) & (r > R - thick - cav)
        f = np.where(north, (track_x0 - X) / cav, np.where(south, (X - track_x1) / cav,
                                                           (r - (R - thick - cav)) / cav))
        top = np.floor((2.0 + (zt - 6.0) * np.clip(f, 0, 1)) / 2.0) * 2.0
        return (north | south | curve) & (Z < top + 2.0)

    def stone(X, Y, Z):
        return 0.45 * ((Z % 2.0) > 1.3) - 0.35 + 0.3 * ((np.floor(Y / 40.0) % 2) == 0) * ((Z % 2.0) > 1.3)
    fill(m, (0.0, D, 0.0, x_end, 0.0, zt), "marble", seats, stone)
    fill(m, (0.0, D, 0.0, x_end, zt * 0.55, zt), "wood_light", lambda X, Y, Z: seats(X, Y, Z), stone,
         only_solid=True)
    # The track: sand, and the spina down its middle.
    fill(m, (track_x0, track_x1, 2.0, x_end, 0.0, 0.8), "poros",
         tone=lambda X, Y, Z: (value_noise(X * 2, Y * 0.5, Z, 2.0, 583) - 0.5) * 0.6 - 0.3 * (np.sin(Y * 0.4) > 0.9))
    sx = D / 2 + 2.0
    sy0, sy1 = cy + Sc.h(70.0), x_end - Sc.h(90.0)
    slab(m, sx - 4.0, sx + 4.0, sy0, sy1, 0.0, 3.0, "marble", tone=0.2)
    fill(m, (sx - 3.0, sx + 3.0, sy0 + 2, sy1 - 2, 2.0, 3.0), "water",
         tone=lambda X, Y, Z: 0.3 * (np.sin(Y * 1.3) > 0.8))
    RM.obelisk(m, sx, (sy0 + sy1) / 2, 3.0, Sc.v(23.7), Sc.h(2.5), material="granite_pink", base_h=Sc.v(3.0))
    for i, yy in enumerate((sy0 + 30.0, sy1 - 30.0)):     # the egg and dolphin counters on columns
        for xx in (sx - 2.0, sx + 2.0):
            rod(m, (xx, yy - 8.0, 3.0), (xx, yy - 8.0, 14.0), 0.6, "marble", 0.2)
            rod(m, (xx, yy + 8.0, 3.0), (xx, yy + 8.0, 14.0), 0.6, "marble", 0.2)
        slab(m, sx - 2.6, sx + 2.6, yy - 9.0, yy + 9.0, 14.0, 15.0, "marble", tone=0.3)
        for k_ in range(7):
            y_ = yy - 7.5 + k_ * 2.5
            if i == 0:
                ellipsoid(m, (sx, y_, 16.0), (0.8, 0.8, 1.0), "marble", 0.4)
            else:
                rod(m, (sx, y_ - 0.6, 15.4), (sx, y_ + 0.6, 17.0), 0.55, "bronze_cast", 0.3)
    for yy in (sy0 + 60.0, sy1 - 60.0, (sy0 + sy1) / 2 - 50.0, (sy0 + sy1) / 2 + 50.0):
        RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.6, H=5.0), front="+x", cols=4, deep=1,
                                podium=1.0, pediment=None, acroteria=None, inscription=False, seed=int(yy)),
                  Sc, (sx - 3.5, sx + 3.5, yy - 6.0, yy + 6.0), 3.0)
    for yy in (sy0 - 6.0, sy1 + 6.0):     # the metae: three gilded cones on a half-round base
        revolve(m, sx, yy, 0.0, 3.0, lambda t: 5.0, "marble", tone=0.2)
        for d_ in (-2.6, 0.0, 2.6):
            revolve(m, sx + d_, yy, 3.0, 14.0, lambda t: 1.4 * (1 - t) + 0.2, "gilt", tone=0.2)
    # The carceres: twelve gates in a slightly curved line between two towers.
    for i in range(12):
        g = (i + 0.5) / 12
        x = track_x0 + (track_x1 - track_x0) * g
        y = x_end - 6.0 * math.sin(math.pi * g)
        slab(m, x - 3.6, x + 3.6, y - 3.0, y + 3.0, 0.0, Sc.v(9.0), "travertine", tone=0.1)
        fill(m, (x - 2.8, x + 2.8, y - 3.2, y - 2.4, 0.0, Sc.v(6.0)), "wood",
             tone=lambda X, Y, Z: -0.5 * ((X % 1.2) < 0.4))
    for x in (track_x0 - 6.0, track_x1 + 6.0):
        RM.wall(m, (x - 8.0, x + 8.0, x_end - 8.0, x_end + 8.0), 0.0, Sc.v(16.0), "travertine", 584)
        RM.cornice(m, (x - 8.0, x + 8.0, x_end - 8.0, x_end + 8.0), Sc.v(16.0) - 1.0, 1.0, 0.6)
    RM.wall(m, (track_x0, track_x1, x_end + 2.0, W - 2.0), 0.0, Sc.v(11.0), "travertine", 585)
    RM.arcade_front(m, "+y", (track_x0, track_x1, x_end + 2.0, W - 2.0), 0.0, [(Sc.v(11.0), "tuscan", "travertine")],
                    5, depth=2.0)
    RM.lean_to(m, (track_x0 - 2, track_x1 + 2, x_end - 4.0, W - 1.0), Sc.v(11.0), Sc.v(13.0), "+y", "terracotta", 586)
    # The pulvinar on the north side: a temple front among the seats.
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.9, H=8.0), front="+x", cols=6, deep=1, podium=3.0,
                            pediment="gods", seed=587), Sc, (1.0 + thick + 2.0, track_x0 + 2.0, W * 0.45 - 16.0,
                                                             W * 0.45 + 16.0), Sc.v(14.0))
    # The triple arch of Titus in the curved east end.
    RM.triumphal_arch(m, (cx - 22.0, cx + 22.0, 1.0, 9.0), "+y", Sc, z0=0.0, bays=3,
                      order=RM.ROrder("composite", D=1.0, H=13.0), seed=588)
    for y in (W * 0.45 - 20.0, W * 0.45, W * 0.45 + 20.0):     # lamps at the imperial box
        lamp(m, 1.0 + thick + 3.0, y, Sc.v(14.0), 0.5)


def porta_capena(m):
    """The Porta Capena in the old Servian wall: a tufa gate under an aqueduct branch (the
    "wet gate": the channel dripped on those passing), the Via Appia through it."""
    W, D = 4 * T, 4 * T
    for y0, y1 in ((2.0, T), (3 * T, W - 2.0)):
        slab(m, 0.0, D, y0, y1, 0.0, S.v(12.0), "tufa", tone=M.ashlar(2.4, 5.0, 591, spread=0.8))
        RM.cornice(m, (0.0, D, y0, y1), S.v(12.0) - 1.0, 1.0, 0.6, "tufa")
    RM.aqueduct(m, D / 2 - 5.0, D / 2 + 5.0, 2.0, W - 2.0, "y", 0.0, S.v(17.0),
                arches=((T, 3 * T, S.v(10.0)),), material="tufa", seed=592)
    fill(m, (D / 2 - 5.0, D / 2 + 5.0, T, 3 * T, S.v(9.0), S.v(10.0)), "water",
         lambda X, Y, Z: hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), 593) < 0.15,
         tone=0.3, only_solid=False)


LANDMARKS = {
    "rome.domus_flavia": Landmark((11, 14), (0, 112), ref("domus_flavia"), district=5),
    "rome.domus_augustana": Landmark((9, 14), (0, 96), ref("domus_augustana"), district=5),
    "rome.palatine_tiberiana": Landmark((7, 13), (0, 80), ref("palatine_tiberiana"), district=5),
    "rome.palatine_stadium": Landmark((19, 6), (0, 64), ref("palatine_stadium"), district=5),
    "rome.apollo_palatinus": Landmark((6, 6), (0, 96), ref("apollo_palatinus"), district=5),
    "rome.house_augustus": Landmark((5, 5), (0, 40), ref("house_augustus"), district=5),
    "rome.casa_romuli": Landmark((1, 1), (0, 20), ref("casa_romuli"), district=5),
    "rome.lupercal": Landmark((2, 2), (0, 28), ref("lupercal"), district=5),
    "rome.circus_maximus": Landmark((10, 51), (0, 64), ref("circus_maximus"), district=6,
                                    slots={"spectator": [{"t": [10, 15], "face": "-x"}, {"t": [10, 30], "face": "-x"},
                                                         {"t": [10, 40], "face": "-x"}]}),
    "rome.porta_capena": Landmark((4, 4), (0, 64), ref("porta_capena"), district=6,
                                  walk=[(x, y) for x in range(4) for y in (1, 2)]),
}

INFO = {
    "rome.domus_flavia": ("Domus Flavia", 0.65, 130, "BSG", "domus_flavia"),
    "rome.domus_augustana": ("Domus Augustana", 0.65, 160, "BSG", "domus_augustana"),
    "rome.palatine_tiberiana": ("Domus Tiberiana", 0.65, 90, "BS", "palatine_tiberiana"),
    "rome.palatine_stadium": ("Palatine stadium garden", 0.65, 50, "BS", "palatine_stadium"),
    "rome.apollo_palatinus": ("Temple of Apollo Palatinus", 0.65, 110, "BS", "apollo_palatinus"),
    "rome.house_augustus": ("House of Augustus", 0.65, 50, "BS", "house_augustus"),
    "rome.casa_romuli": ("Hut of Romulus", 0.65, 36, "BS", "casa_romuli"),
    "rome.lupercal": ("Lupercal", 0.65, 20, "B", "lupercal"),
    "rome.circus_maximus": ("Circus Maximus", 0.33, 90, "BSG", "circus_maximus"),
    "rome.porta_capena": ("Porta Capena", 0.65, 70, "BS", "porta_capena"),
}
