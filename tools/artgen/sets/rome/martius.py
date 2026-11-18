"""The northern Campus Martius in April AD 126 (rome.md §2.3 D14, §3.2): the Saepta Iulia (as
Hadrian restored it after the fire of 80, a hall of luxury shops), the Iseum Campense (Domitian's
rebuilding), the Stadium of Domitian and the Theatre of Pompey with the temple of Venus Victrix
on its cavea; and on the Oppian the Baths of Trajan (dedicated 109). Grid axes: +x south,
+y west; the camera sees the south and west faces. Scales are the bible's: s = 0.35 for the
Saepta, the Iseum, the Stadium and the Baths, 0.4 for the theatre, whose cavea is drawn at
57 m radius instead of about 75 m so that it fits its 12 x 12 tiles."""

import math

import numpy as np

import materials as M
import roman as RM
from arch import carve, face_box, face_length, fill, halo, slab
from setbuild import Landmark
from sets.rome.common import LAMP, PORTICO, S35, S4, T, GODDESS, paving, plane_tree, referrer
from voxel import value_noise

ref = referrer("sets.rome.martius")

GRANITE = RM.ROrder("corinthian", D=1.0, H=9.0, shaft="granite", trim="marble", fluted=False)
CIPOLLINO = RM.ROrder("corinthian", D=0.9, H=8.0, shaft="cipollino", trim="marble", fluted=False)


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def awning(m, x0, x1, y0, y1, z, cloth):
    """A shop awning on two poles: a sagging cloth with a striped edge."""
    for (x, y) in ((x1, y0), (x1, y1)):
        fill(m, (x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0.0, z), "wood", tone=0.1)
    fill(m, (x0, x1, y0, y1, z - 1.2, z + 0.4), cloth,
         lambda X, Y, Z: np.abs(Z - (z - 0.6 * ((X - x0) / max(x1 - x0, 0.1)))) < 0.35,
         tone=lambda X, Y, Z: 0.35 * ((Y % 2.0) < 1.0) - 0.1)


# ---------------------------------------------------------------- the Saepta Iulia

def saepta(m):
    """The Saepta Iulia: a vast enclosure 310 m long, long porticoes on its two long sides
    (the Porticus of Meleager and of the Argonauts, named for their paintings), the open court
    paved in travertine and lined with booths of the luxury trades, the roofed Diribitorium at
    its south end; brick faced with stucco outside, marble and painted walls in the porticoes."""
    S = S35
    L, W = 23 * T, 9 * T
    H = S.v(13.0)
    # The court.
    paving(m, (0.0, L, 0.0, W), 0.0, 0.8, "travertine", 7.0, 5.0, 301)
    # Outer walls: the west wall (in view) brick and stucco with high windows; east wall; north wall.
    for box, kind in (((2.0, L - 64.0, W - 5.0, W - 1.0), "stucco"), ((2.0, L - 64.0, 1.0, 5.0), "stucco"),
                      ((2.0, 6.0, 1.0, W - 1.0), "stucco")):
        RM.wall(m, box, 0.0, H, kind, 303, material="whitewash")
    westw = (2.0, L - 64.0, W - 5.0, W - 1.0)
    for s0 in np.arange(10.0, L - 76.0, 14.0):
        RM.window(m, "+y", westw, s0, 4.0, H * 0.55, H * 0.25, arched=True)
    # The entrances: a gap in the north wall (dy 4) and in the west wall (dx 9..10), the east
    # wall (dx 12); arches over them stay above the walkers' headroom.
    carve(m, (0.0, 7.0, 64.0, 80.0, 0.0, H + 1.0))
    carve(m, (144.0, 176.0, W - 6.0, W + 1.0, 0.0, H + 1.0))
    carve(m, (192.0, 208.0, 0.0, 6.0, 0.0, H + 1.0))
    for (x0, x1, y0, y1) in ((0.0, 7.0, 62.0, 64.0), (0.0, 7.0, 80.0, 82.0), (142.0, 144.0, W - 6.0, W),
                             (176.0, 178.0, W - 6.0, W), (190.0, 192.0, 0.0, 6.0), (208.0, 210.0, 0.0, 6.0)):
        slab(m, x0, x1, y0, y1, 0.0, H + 3.0, "travertine", tone=RM.travertine(seed=305))
    for (a, b) in ((2.0, 142.0), (178.0, L - 64.0)):
        RM.cornice(m, (a, b, W - 5.0, W - 1.0), H, 1.4, 0.6, faces=("+y", "-y"))
    # The porticoes inside both long walls: columns on the edge of the court, a lean-to roof.
    # Columns stand on the tile line dy 2 / dy 6, so the court between stays walkable.
    for (a, b, n) in ((12.0, 184.0, 15), (216.0, L - 70.0, 8)):
        RM.colonnade(m, (a, 30.0), (b, 30.0), 0.0, n, CIPOLLINO, S, 22.0, "+y", back=False, seed=307)
    for (a, b, n) in ((12.0, 136.0, 11), (184.0, L - 70.0, 12)):
        RM.colonnade(m, (a, W - 30.0), (b, W - 30.0), 0.0, n, CIPOLLINO, S, 22.0, "-y", back=False, seed=309)
    # Paintings on the back walls of the east portico (seen across the court): panels.
    for s in np.arange(16.0, L - 80.0, 16.0):
        if 180.0 < s < 212.0:                  # the east entrance
            continue
        fill(m, (s, s + 11.0, 5.0, 5.6, 3.0, H - 4.0), ("cinnabar", "ochre", "eblue")[int(s // 16) % 3],
             tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 311) - 0.5) * 0.8)
    # Booths of the luxury trades under the porticoes: counters with cloth awnings.
    for i, x in enumerate(np.arange(20.0, L - 84.0, 22.0)):
        if not 136.0 < x < 184.0 and not 184.0 < x < 214.0:
            awning(m, x, x + 9.0, 18.0, 27.0, 7.0, ("linen", "cinnabar", "saffron")[i % 3])
            slab(m, x + 1.0, x + 8.0, 18.0, 20.0, 0.8, 3.4, "wood", tone=0.1)
        if not 132.0 < x < 184.0:
            awning(m, x + 4.0, x + 13.0, W - 27.0, W - 18.0, 7.0, ("eblue", "linen", "purple")[i % 3])
            slab(m, x + 5.0, x + 12.0, W - 20.0, W - 18.0, 0.8, 3.4, "wood", tone=0.1)
    # The Diribitorium: a great roofed hall closing the south end (the widest roof in Rome).
    dx0 = L - 62.0
    RM.wall(m, (dx0, L - 2.0, 1.0, W - 1.0), 0.0, H * 1.35, "brick", 313)
    for face in ("+x", "+y"):
        box = (dx0, L - 2.0, 1.0, W - 1.0)
        Lf = face_length(face, *box)
        for s0 in np.arange(8.0, Lf - 10.0, 12.0):
            RM.window(m, face, box, s0, 4.5, H * 0.7, H * 0.4, arched=True, glass=True)
        RM.opening(m, face, box, Lf / 2 - 5.0, 10.0, 0.0, H * 0.55, 2.4, frame="travertine")
    RM.cornice(m, (dx0, L - 2.0, 1.0, W - 1.0), H * 1.35, 1.6, 0.8)
    RM.gable(m, (dx0 - 1.0, L - 1.0, 0.0, W), H * 1.35 + 1.6, 18.0, "y", seed=315, antefixes=True)
    for x in (40.0, 120.0, 200.0):
        halo(m, x, 24.0, 8.0, 8.0, LAMP, 0.4)


def _saepta_landmark():
    walk = tiles(1, 18, 2, 6) + [(0, 4), (9, 7), (10, 7), (9, 8), (10, 8), (12, 0), (12, 1)]
    walk = sorted(set(walk))
    return Landmark((23, 9), (0, 64), ref("saepta"), walk=walk,
                    slots={"shop": [{"t": [4, 2], "face": "-y"}, {"t": [8, 6], "face": "+y"}, {"t": [14, 2], "face": "-y"}],
                           "stroll": [{"t": [6, 4]}, {"t": [11, 4]}, {"t": [16, 3]}]},
                    district=30)


# ---------------------------------------------------------------- the Iseum Campense

def _sphinx(m, x, y, z, face, mat="granite"):
    """A crouching sphinx on a low plinth, facing along +y or -y."""
    sg = 1 if face == "+y" else -1
    slab(m, x - 2.0, x + 2.0, y - 4.5, y + 4.5, z, z + 1.6, "marble", tone=0.2)
    fill(m, (x - 1.6, x + 1.6, y - 4.0, y + 4.0, z + 1.6, z + 6.5), mat,
         lambda X, Y, Z: (((Y - y) * sg > -4.0) & (Z < z + 1.6 + 2.0 + 0.5 * np.clip((Y - y) * sg, -4, 1.5))) |
         ((((Y - y) * sg - 2.6) ** 2 / 2.0 + (X - x) ** 2 / 1.6 + (Z - z - 5.2) ** 2 / 2.2) < 1.0), tone=0.2)
    fill(m, (x - 1.7, x + 1.7, y + sg * 1.8 - 1.0, y + sg * 1.8 + 1.0, z + 4.5, z + 7.0), "gold",
         lambda X, Y, Z: np.abs(X - x) > 1.0, tone=0.2)


def iseum(m):
    """The Iseum Campense as Domitian rebuilt it: a walled precinct entered from the east and
    west, its avenue (dromos) lined with sphinxes and two red granite obelisks (Rome's Egyptian
    obelisks from the Iseum are known), the temple of Isis to the north in Roman form with
    Egyptian touches (a cavetto cornice, grey granite columns, gilded uraei), and the
    hemicycle of the Serapeum closing the south with statues in its niches; palms and a
    garden bed; incense at the altar. The precinct was longer (about 220 m): the plan here is
    shortened to its footprint."""
    S = S35
    L, W = 9 * T, 7 * T
    paving(m, (0.0, L, 0.0, W), 0.0, 0.7, "travertine", 6.0, 5.0, 321)
    # Precinct walls with gates on the cross axis (dx 4).
    for box in ((0.0, 3.0, 0.0, W), (3.0, 64.0, 0.0, 3.0), (80.0, L, 0.0, 3.0), (3.0, 64.0, W - 3.0, W),
                (80.0, L, W - 3.0, W)):
        RM.wall(m, box, 0.0, S.v(9.0), "stucco", 323, material="whitewash")
    for (x0, y0, y1) in ((62.0, 0.0, 3.4), (80.0, 0.0, 3.4), (62.0, W - 3.4, W), (80.0, W - 3.4, W)):
        slab(m, x0, x0 + 2.0, y0, y1, 0.0, S.v(11.0), "granite", tone=0.1)
        a, b = (x0 - 0.8, x0 + 2.0) if x0 < 70 else (x0, x0 + 2.8)    # caps stay off the gate's tile
        fill(m, (a, b, y0 - 0.4, y1 + 0.4, S.v(11.0), S.v(11.0) + 1.5), "granite", tone=0.35)
    # The temple of Isis at the north end, facing south down the dromos.
    RM.temple(m, RM.RTemple(order=GRANITE, front="+x", cols=4, deep=2, plan="prostyle", podium=2.4,
                            cella_kind="stucco", cella_mat="cream", roof="terracotta", pediment=None,
                            acroteria="none", inscription=False, seed=325, door_glow=0.5),
              S, (4.0, 46.0, 34.0, 78.0))
    # The dromos (dy 3): sphinxes on both sides, obelisks at the head of it.
    for x in (50.0, 58.0, 84.0, 92.0, 100.0):
        _sphinx(m, x, 41.5, 0.7, "+y")
        _sphinx(m, x, 70.5, 0.7, "-y")
    for y in (36.0, 76.0):
        RM.obelisk(m, 54.0, y, 0.7, S.v(18.0), 2.6, base_h=3.0)
    # The Serapeum's hemicycle at the south end: a curved wall with niches and statues, a
    # half dome over the apse.
    cx, cy, R = L - 4.0, W / 2, 34.0
    def hemi(X, Y, Z):
        r = np.hypot(X - cx, Y - cy)
        return (r < R) & (r > R - 5.0) & (X < cx)
    fill(m, (cx - R, cx, cy - R, cy + R, 0.0, S.v(12.0)), "brick", hemi, tone=RM.brick(327))
    fill(m, (cx - R, cx, cy - R, cy + R, 0.0, S.v(12.0)), "whitewash",
         lambda X, Y, Z: hemi(X, Y, Z) & (np.hypot(X - cx, Y - cy) < R - 4.4), tone=0.2, only_solid=True)
    for k in range(7):
        a = math.pi / 2 + (k + 0.5) * math.pi / 7
        nx, ny = cx + (R - 4.0) * math.cos(a), cy + (R - 4.0) * math.sin(a)
        carve(m, (nx - 2.0, nx + 2.0, ny - 2.0, ny + 2.0, 2.0, 12.0))
        RM.statue(m, nx, ny, 2.0, 9.0, GODDESS, material="marble", keep=())
    fill(m, (cx - R, cx, cy - R, cy + R, S.v(12.0), S.v(12.0) + R * 0.6), "terracotta",
         lambda X, Y, Z: (X < cx) & (np.hypot(np.hypot(X - cx, Y - cy), (Z - S.v(12.0)) / 0.6) < R) &
         (np.hypot(np.hypot(X - cx, Y - cy), (Z - S.v(12.0)) / 0.6) > R - 2.0),
         tone=lambda X, Y, Z: 0.3 * ((np.arctan2(Y - cy, X - cx) * 18) % 1.0 < 0.3) - 0.1)
    # Altar with incense, a palm garden either side of the dromos.
    slab(m, 52.0 - 26.0, 52.0 - 20.0, 52.0, 60.0, 0.7, 4.5, "marble", tone=0.25)
    for (x, y) in ((86.0, 14.0), (100.0, 18.0), (86.0, 98.0), (100.0, 94.0), (18.0, 14.0), (18.0, 98.0)):
        fill(m, (x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0.7, 13.0), "bark", tone=lambda X, Y, Z: 0.3 * ((Z % 1.4) < 0.5))
        for k in range(8):
            a = k * math.pi / 4
            fill(m, (x - 5, x + 5, y - 5, y + 5, 10.0, 15.0), "leaf",
                 lambda X, Y, Z, a=a: (np.abs((X - x) * math.sin(a) - (Y - y) * math.cos(a)) < 0.6) &
                 ((X - x) * math.cos(a) + (Y - y) * math.sin(a) > 0) &
                 (np.abs(Z - (14.0 - 0.12 * ((X - x) ** 2 + (Y - y) ** 2))) < 0.6), tone=0.1)
    halo(m, 30.0, 56.0, 6.0, 7.0, LAMP, 0.5)


def _iseum_landmark():
    walk = sorted(set([(x, 3) for x in range(3, 6)] + [(4, y) for y in range(7)]))
    return Landmark((9, 7), (0, 60), ref("iseum"), walk=walk,
                    slots={"pray": [{"t": [3, 3], "face": "-x"}], "priest": [{"t": [4, 3], "face": "-x"}],
                           "visit": [{"t": [5, 3], "face": "+x"}]}, district=30)


# ---------------------------------------------------------------- the Stadium of Domitian

def stadium_domitian(m):
    """Domitian's stadium for Greek athletic games: a long arena (the later Piazza Navona) with
    its curved end to the north and the straight end with the main gate to the south; tiered
    seats on vaults all round; outside, two storeys of travertine arcades with engaged
    columns, an attic with pilasters, statues in the upper arches."""
    S = S35
    L, W = 25 * T, 10 * T
    R = W / 2 - 1.0
    cy = W / 2
    cxn = R + 1.0                                      # the centre of the curved north end

    def inside(X, Y, off=0.0):
        """The plan of the building: a long rectangle ending in a half circle at the north."""
        rr = np.where(X < cxn, np.hypot(X - cxn, Y - cy), np.abs(Y - cy))
        return (rr < R - off) & (X < L - 2.0 - off)
    H1, H2, HA = S.v(9.0), S.v(8.5), S.v(4.0)
    ztop = H1 + H2
    th = 7.0
    # The façade ring: solid between the outer line and `th` inside it, arcades cut through.
    fill(m, (0.0, L, 0.0, W, 0.0, ztop + HA), "travertine",
         lambda X, Y, Z: inside(X, Y) & ~inside(X, Y, th),
         tone=RM.travertine(seed=331))
    # Arcades on the west flank and the south end (in view), then the attic.
    west = (cxn, L - 2.0, 1.0, W - 1.0)
    RM.arcade_front(m, "+y", west, 0.0, [(H1, "tuscan", "travertine"), (H2, "ionic", "travertine")], 22,
                    seed=333, statue_mat="marble", depth=th - 1.0)
    south = (cxn, L - 2.0, 1.0, W - 1.0)
    RM.arcade_front(m, "+x", south, 0.0, [(H1, "tuscan", "travertine"), (H2, "ionic", "travertine")], 9,
                    seed=335, statue_mat="marble", depth=th - 1.0)
    for face in ("+y", "+x"):
        Lf = face_length(face, *west)
        for s in np.arange(4.0, Lf - 2.0, Lf / (22 if face == "+y" else 9)):
            fill(m, face_box(face, *west, ztop, ztop + HA, s - 0.6, s + 0.6, -0.5, 0.0), "travertine", tone=0.3)
    # The curved end's façade: plain arches cut round the half circle (hidden mostly).
    for k in range(10):
        a = math.pi / 2 + (k + 0.5) * math.pi / 10
        px, py = cxn + (R - 3.0) * math.cos(a), cy + (R - 3.0) * math.sin(a)
        carve(m, (px - 2.4, px + 2.4, py - 2.4, py + 2.4, 0.0, H1 * 0.6))
    # A crowning band along the outer faces (the gallery behind the attic stays open).
    for face in ("+x", "+y"):
        Lf = face_length(face, *west)
        fill(m, face_box(face, *west, ztop + HA - 1.2, ztop + HA, 0.0, Lf, -0.6, th - 1.0), "travertine", tone=0.35)
    # The seats: rising from the arena wall to the gallery under the attic.
    ar = 26.0                                           # arena inset from the façade
    def seat(X, Y, Z):
        rr = np.where(X < cxn, np.hypot(X - cxn, Y - cy), np.abs(Y - cy))
        dist = R - th - rr                                  # depth inside the façade ring
        d = np.where(X < cxn, dist, np.minimum(dist, (L - 2.0 - th) - X))
        h = ztop - 1.0 - d * (ztop - 5.0) / (ar - th)
        return (d > 0) & (d < ar - th) & (Z < h) & inside(X, Y, th)
    fill(m, (0.0, L, 0.0, W, 0.0, ztop), "marble", seat,
         tone=lambda X, Y, Z: 0.45 * ((Z % 1.6) > 1.1) - 0.3 * ((Z % 1.6) < 0.4))
    # Aisles of stairs down the seats (darker lines).
    for x in np.arange(cxn + 12.0, L - 20.0, 26.0):
        fill(m, (x - 1.0, x + 1.0, 0.0, W, 0.0, ztop), "travertine", seat, tone=-0.3, only_solid=True)
    # The arena: sand, a low podium wall round it, the south gate's passage.
    fill(m, (0.0, L, 0.0, W, 0.0, 0.6), "poros",
         lambda X, Y, Z: inside(X, Y, ar), tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 337) - 0.5) * 0.7)
    fill(m, (0.0, L, 0.0, W, 0.0, 5.0), "marble", lambda X, Y, Z: inside(X, Y, ar - 1.2) & ~inside(X, Y, ar),
         tone=0.25)
    carve(m, (L - 2.0 - ar - 1.0, L, cy - 5.0, cy + 5.0, 0.6, H1 * 0.62))
    # Athletes' statues on the podium wall and an awning mast or two.
    for x in np.arange(cxn + 30.0, L - 40.0, 60.0):
        RM.statue(m, x, cy + (R - ar + 0.5), 5.0, 8.0, GODDESS, material="bronze_cast")


def _stadium_landmark():
    return Landmark((25, 10), (0, 56), ref("stadium_domitian"),
                    slots={"spectator": [{"t": [25, 4], "face": "-x"}, {"t": [25, 5], "face": "-x"}],
                           "entrance": [{"t": [25, 6], "face": "-x"}]}, district=30)


# ---------------------------------------------------------------- the Theatre of Pompey

def pompey_theatre(m):
    """Pompey's theatre (dedicated 55 BC), Rome's first in stone: the cavea's arcaded curve to
    the west in three storeys (Tuscan, Ionic, Corinthian half columns) under a closed attic, and
    at the top of the seats, on the axis, the temple of Venus Victrix to which the seats were
    the stairway; inside the stepped cavea, the orchestra and the stage with its columned
    front, the stage building's high back wall to the east and beyond it the start of the
    porticus with its plane trees (where Caesar was killed in the curia of Pompey)."""
    S = S4
    N = 12 * T
    cx, cy = N / 2, 66.0
    R = 92.0
    el = RM.Ellipse(cx, cy, R, R)
    arc = (0.0, math.pi)                              # the half toward +y (west)
    thick = S.h(4.0)
    storeys = [RM.Storey(S.v(8.5), "arcade", "tuscan", (0.6, 0.62)),
               RM.Storey(S.v(8.5), "arcade", "ionic", (0.58, 0.6), statues=True),
               RM.Storey(S.v(8.0), "blind", "corinthian", (0.2, 0.5))]
    top = RM.ring_facade(m, el, 0.0, storeys, 56, thick, S, arc=arc, seed=341, phase=0.5)
    orch = RM.Ellipse(cx, cy, R * 0.28, R * 0.28)
    upper = RM.Ellipse(cx, cy, R - thick - 4.0, R - thick - 4.0)
    fill(m, (cx - R, cx + R, cy, cy + R, 0.0, top - 6.0), "tufa",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < R - thick - 3.0) & (np.hypot(X - cx, Y - cy) > R * 0.28) &
         (Y > cy) & (Z < 2.0 + (top - 8.0) * np.clip((np.hypot(X - cx, Y - cy) - R * 0.28) / (R * 0.64), 0, 1)),
         tone=-0.2)
    RM.cavea(m, orch, upper, 2.0, top - 6.0, arc=arc, material="marble", upper_mat="travertine", bands=3, aisles=18,
             seed=343)
    fill(m, (cx - R * 0.28, cx + R * 0.28, cy - R * 0.28, cy + R * 0.28, 0.0, 1.0), "giallo",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < R * 0.28) & (Y > cy - 2.0), tone=M.paving(3.0, 3.0, 345))
    # The stage and the stage building (scaena) to the east, its columned front toward the seats.
    slab(m, cx - 70.0, cx + 70.0, cy - 14.0, cy - 2.0, 0.0, 3.0, "wood", tone=M.timber("x", 347))
    RM.wall(m, (cx - 74.0, cx + 74.0, cy - 30.0, cy - 14.0), 0.0, top + 4.0, "brick", 349)
    front = (cx - 74.0, cx + 74.0, cy - 30.0, cy - 14.0)
    for i, x in enumerate(np.linspace(cx - 64.0, cx + 64.0, 13)):
        for z0, h in ((3.0, S.v(7.0)), (3.0 + S.v(7.0) + 2.0, S.v(6.0))):
            RM.column(m, x, cy - 11.0, z0, RM.ROrder("corinthian", D=0.7, H=h / S.v(1.0), shaft="giallo" if i % 2 else
                                                    "granite_pink", trim="marble", fluted=False), S)
        if i % 4 == 2:
            RM.opening(m, "+y", front, x - (cx - 74.0) - 4.0, 8.0, 3.0, 14.0, 2.0, frame="marble")
    for zb in (3.0 + S.v(7.0), top - 2.0):
        slab(m, cx - 66.0, cx + 66.0, cy - 13.5, cy - 9.0, zb, zb + 2.0, "marble", tone=0.2)
    RM.cornice(m, front, top + 4.0, 1.6, 0.8, faces=("+y", "-y", "+x", "-x"))
    RM.gable(m, (cx - 75.0, cx + 75.0, cy - 31.0, cy - 13.0), top + 5.6, 8.0, "x", seed=351)
    # The temple of Venus Victrix on the top of the cavea, facing the stage (east); behind the
    # façade its podium rises from the ground as a tall arcaded substructure.
    sub = (cx - 20.0, cx + 20.0, cy + R - 12.0, N - 1.0)
    RM.wall(m, sub, 0.0, top - 6.0, "travertine", 357)
    for s0 in (6.0, 17.0, 28.0):
        RM.opening(m, "+y", sub, s0, 6.0, 0.0, 9.0, 2.0, frame="travertine")
    RM.cornice(m, sub, top - 6.0, 1.2, 0.6, "travertine", faces=("+y", "+x", "-x"))
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.2, H=12.0), front="-y", cols=6, deep=2,
                            plan="prostyle", podium=3.0, pediment="gods", seed=353, door_glow=0.4),
              S, (cx - 18.0, cx + 18.0, cy + R - thick - 34.0, N - 2.0), z0=top - 6.0)
    # The start of the porticus beyond the stage: a colonnade and plane trees in rows.
    RM.colonnade(m, (8.0, 25.0), (N - 8.0, 25.0), 0.0, 14, PORTICO, S, 10.0, "-y", seed=355)
    for x in np.arange(20.0, N - 10.0, 34.0):
        plane_tree(m, x, 8.0, 0.0, h=30.0, seed=int(x))


def _pompey_landmark():
    return Landmark((12, 12), (0, 120), ref("pompey_theatre"),
                    slots={"spectator": [{"t": [5, 12], "face": "-y"}, {"t": [7, 12], "face": "-y"}],
                           "pray": [{"t": [6, 12], "face": "-y"}]}, district=30)


LANDMARKS = {
    "rome.saepta": _saepta_landmark(),
    "rome.iseum": _iseum_landmark(),
    "rome.stadium_domitian": _stadium_landmark(),
    "rome.pompey_theatre": _pompey_landmark(),
}

INFO = {
    "rome.saepta": ("Saepta Iulia", 0.35, 106, "BSG", "saepta"),
    "rome.iseum": ("Iseum Campense", 0.35, 90, "BSG", "iseum"),
    "rome.stadium_domitian": ("Stadium of Domitian", 0.35, 76, "BS", "stadium_domitian"),
    "rome.pompey_theatre": ("Theatre of Pompey", 0.4, 200, "BSG", "pompey_theatre"),
}
