"""The imperial fora at s = 0.5 (rome.md §2.3 D3-D4, §3.2): Trajan's Forum with its gilded
horseman, colonnades and hemicycles, the Basilica Ulpia, Trajan's Column between its two
libraries, the Temple of the deified Trajan, Trajan's Markets climbing the Quirinal, the Forum of
Augustus with Mars Ultor against its grey firewall, the Forum of Caesar with Venus Genetrix, the
narrow Forum of Nerva and the garden of the Templum Pacis."""

import math

import numpy as np

import materials as M
import relief_roman as RR
import roman as RM
from arch import fill, slab
from rig import Dress
from setbuild import Landmark
from sets.rome.common import GIALLO, PAVONAZZETTO, S5, T, TOGATE, box_hedge, lamp, paving, referrer, tc
from voxel import hash01

ref = referrer("sets.rome.fora")
S = S5

DACIAN = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="long", beard="full", garment="tunic",
               colour="purple", trousers="purple", cape="purple", head="pilos",
               head_mat="purple", feet="boots")
TRAJAN = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="short", beard="none", garment="tunic",
               colour="gold", worn=("cuirass",), cape="gold", feet="boots", hand_l="spear")
TRAJAN_RIDER = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="short", beard="none", garment="tunic",
                     colour="gold", worn=("cuirass",), cape="gold", feet="boots", mount="horse")


def _attic_figures(m, line_a, line_b, z, n, h, material="porphyry"):
    """Statues of captive Dacians standing over a colonnade's attic (porphyry and pavonazzetto
    figures stood there)."""
    (ax, ay), (bx, by) = line_a, line_b
    for i in range(n):
        f = (i + 0.5) / n
        RM.statue(m, ax + (bx - ax) * f, ay + (by - ay) * f, z, h, DACIAN, material=material, keep=())


def trajan_forum(m):
    """The Forum of Trajan (dedicated 112): a vast square paved in white marble, Trajan's gilded
    bronze equestrian statue in the middle, colonnades of pavonazzetto on the east and west
    sides two steps up with captive Dacians standing over their attics and shields with
    portraits between, the great hemicycles behind them, and the south front with the
    triumphal gate toward the Forum of Augustus. The open square is walkable."""
    W, D = 25 * T, 13 * T
    paving(m, (0.0, D, 3 * T, W - 3 * T), 0.0, 0.8, "marble", 8.0, 6.0, 401)
    o = PAVONAZZETTO
    H = S.v(o.H)
    for side in (0, 1):
        y_line = 3 * T + 6.0 if side == 0 else W - 3 * T - 6.0
        front = "+y" if side == 0 else "-y"
        y0, y1 = (3 * T - 12.0, y_line + 4.0) if side == 0 else (y_line - 4.0, W - 3 * T + 12.0)
        slab(m, 0.0, D - 2 * T, y0, y1, 0.0, 2.0, "marble", tone=0.25)          # the colonnade's two steps
        RM.colonnade(m, (6.0, y_line), (D - 2 * T - 6.0, y_line), 2.0, 11, o, S, 18.0, front, roof="terracotta",
                     back=False, seed=402 + side)
        # Attic over the colonnade with Dacians and shields.
        ab = (2.0, D - 2 * T - 2.0, y_line - 3.0, y_line + 3.0)
        za = 2.0 + H + o.entablature(S) * 0.75
        RM.wall(m, ab, za, za + 10.0, "marble", 404)
        for i in range(10):
            x = 6.0 + (i + 0.5) * (D - 2 * T - 12.0) / 10
            fill(m, (x - 2.5, x + 2.5, ab[2] - 0.6, ab[3] + 0.6, za + 3.0, za + 8.0), "gold",
                 lambda X, Y, Z, x=x: np.hypot(X - x, Z - za - 5.5) < 2.4, tone=0.3, only_solid=False)
        _attic_figures(m, (6.0, y_line), (D - 2 * T - 6.0, y_line), za + 10.0, 9, 11.0)
        # The hemicycle behind: a semicircular brick-and-marble exedra with niches.
        cx = D / 2 - T
        cy = 3 * T - 10.0 if side == 0 else W - 3 * T + 10.0
        R = 3 * T - 8.0
        el = RM.Ellipse(cx, cy, R * 1.4, R)
        arc = (-math.pi, 0.0) if side == 0 else (0.0, math.pi)
        RM.ring_facade(m, el, 0.0, [RM.Storey(S.v(9.0), "arcade", "corinthian", (0.5, 0.6), material="marble"),
                                    RM.Storey(S.v(6.0), "blind", "corinthian", material="marble")],
                       28, 6.0, S, arc=arc, inward=True, seed=405 + side)
        fill(m, (cx - R * 1.6, cx + R * 1.6, cy - R - 8, cy + R + 8, S.v(15.0) - 0.5, S.v(15.0) + 4.0), "terracotta",
             lambda X, Y, Z, el=el, arc=arc: (np.hypot((X - cx) / (el.a + 6.5), (Y - cy) / (el.b + 6.5)) <= 1) &
             (np.hypot((X - cx) / (el.a - 0.5), (Y - cy) / (el.b - 0.5)) > 1) &
             RM._in_arc(np.arctan2((Y - cy) / el.b, (X - cx) / el.a), arc), tone=-0.1)
    # The south front: a wall with the central triumphal gate (Trajan in a six-horse chariot
    # stood on it; shown with the usual quadriga).
    sb = (D - 6.0, D - 2.0, 3 * T, W - 3 * T)
    RM.wall(m, sb, 0.0, S.v(12.0), "marble", 406)
    RM.cornice(m, sb, S.v(12.0) - 1.0, 1.0, 0.8)
    for s0 in np.arange(8.0, sb[3] - sb[2] - 8.0, 12.0):
        if abs(s0 + 3.0 - (sb[3] - sb[2]) / 2) > 30.0:
            RM.opening(m, "+x", sb, s0, 6.0, 3.0, 13.0, 2.0, back="giallo")
    RM.triumphal_arch(m, (D - 2 * T, D, W / 2 - 1.5 * T, W / 2 + 1.5 * T), "+x", S, z0=0.0, bays=1,
                      order=RM.ROrder("composite", D=1.1, H=11.0, shaft="giallo"), seed=407)
    # The equestrian statue on its tall base in the middle of the square.
    cx, cy = tc(6) + 8.0, W / 2
    from greek import statue_base
    zb = statue_base(m, cx, cy, 0.8, 10.0, 8.0, material="marble")
    RM.statue(m, cx, cy, zb, 12.5, TRAJAN_RIDER, material="gilt", keep=())


TRAJ_SOLID = {(6, 12), (6, 13), (7, 12), (7, 13)}
TRAJ_WALK = [(x, y) for x in range(0, 10) for y in range(4, 21) if (x, y) not in TRAJ_SOLID]


def basilica_ulpia(m):
    """The Basilica Ulpia, the largest of Rome's basilicas: its long south front on the forum
    with three projecting porches of giallo antico columns up a flight of steps, captive Dacians
    over the attic, a high nave with a clerestory and gilded bronze roof tiles."""
    W, D = 21 * T, 5 * T
    box = (2.0, D - 6.0, 2.0, W - 2.0)
    RM.basilica(m, box, "+x", S, 18, [(S.v(9.5), "corinthian", "marble"), (S.v(8.0), "corinthian", "marble")],
                18.0, S.v(15.0), S.v(26.0), seed=411, gilt_roof=True, statue_mat="marble")
    slab(m, D - 8.0, D, 4.0, W - 4.0, 0.0, 1.6, "marble", tone=lambda X, Y, Z: 0.35 * (Z > 1.0))
    for yc in (W * 0.2, W / 2, W * 0.8):     # the three porches
        RM.colonnade(m, (D - 3.0, yc - 22.0), (D - 3.0, yc + 22.0), 1.6, 4, GIALLO, S, 5.0, "+x", back=False,
                     seed=int(yc))
        _attic_figures(m, (D - 3.0, yc - 20.0), (D - 3.0, yc + 20.0), 1.6 + S.v(9.0) + 7.0, 4, 10.0)


def trajan_column(m):
    """Trajan's Column (113): Luna marble, 100 Roman feet on a pedestal carved with captured
    arms, the door to the spiral stair and the tomb chamber for Trajan's ashes, the spiral band
    of the Dacian wars in 23 turns, the bronze statue of Trajan on top; the two libraries
    (Greek and Latin) face each other across the little court, their large windows on it."""
    W, D = 9 * T, 4 * T
    paving(m, (0.0, D, 0.0, W), 0.0, 0.6, "marble", 5.0, 5.0, 421)
    for y0, y1 in ((2.0, 3.5 * T), (W - 3.5 * T, W - 2.0)):
        lb = (4.0, D - 4.0, y0, y1)
        RM.wall(m, lb, 0.0, S.v(17.0), "brick", 422)
        face = "+y" if y0 < 10 else "-y"
        for s0 in (8.0, 24.0, 40.0):
            RM.window(m, face, lb, s0, 7.0, S.v(5.0), S.v(7.0), arched=True, glass=True, lit=0.3)
        RM.colonnade(m, (D - 6.0, y0 + 4.0), (D - 6.0, y1 - 4.0), 0.6, 4, RM.ROrder("corinthian", D=0.8, H=8.0,
                     shaft="granite", fluted=False), S, 5.0, "+x", back=False, seed=int(y0))
        RM.gable(m, (3.0, D - 3.0, y0 - 1.0, y1 + 1.0), S.v(17.0), 7.0, "y", seed=423)
    img = RR.spiral_image(2600, 6, seed=3)
    RM.spiral_column(m, tc(1) + 8.0, tc(4), 0.6, S, image=img, statue_dress=TRAJAN)


def trajan_temple(m):
    """The Temple of the deified Trajan north of the Column (its place and form are debated):
    a great octastyle temple of grey granite columns, facing south."""
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=2.0, H=17.7, shaft="granite", fluted=False), front="+x",
                            cols=8, deep=3, plan="peripteral", podium=4.0, pediment="gods", seed=431),
              S, (2.0, 6 * T - 2.0, 2.0, 9 * T - 2.0))


def trajan_markets(m):
    """Trajan's Markets on the Quirinal slope: the great brick hemicycle facing the forum, shop
    doors at street level, a storey of arched windows framed by pilasters under alternating
    pediments, a setback storey above; behind it terraces of shops rising up the hill, the
    Via Biberatica curving across, and at the top the great vaulted market hall. Lamps in
    the shops at night."""
    W, D = 13 * T, 18 * T
    cx, cy = D / 2, W + 14.0
    R = 6 * T
    el = RM.Ellipse(cx, cy, R, R)
    arc = (-math.pi, 0.0)
    z = RM.ring_facade(m, el, 0.0, [RM.Storey(S.v(6.5), "shops", "tuscan", (0.55, 0.5), material="brick"),
                                    RM.Storey(S.v(6.0), "windows", "tuscan", material="brick"),
                                    RM.Storey(S.v(5.0), "windows", "tuscan", material="brick")],
                       44, 12.0, S, arc=arc, inward=True, seed=441)
    fill(m, (0.0, D, 0.0, W + 20.0, 0.0, z), "brick",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) > R + 11.0) & (np.hypot(X - cx, Y - cy) < R + 3 * T) &
         (Y < cy) & (Z < z - 3.0), tone=RM.brick(442))
    # Window frames: pilasters and pediments on the second storey.
    for i in range(22):
        th = -math.pi + (i + 0.5) * math.pi / 22
        x, y = el.point(th, -0.4)
        ztop = S.v(6.5) + S.v(6.0) * 0.75
        if i % 2:
            fill(m, (x - 3, x + 3, y - 3, y + 3, ztop, ztop + 2.4), "travertine",
                 lambda X, Y, Z, x=x, y=y: (np.hypot(X - x, Y - y) < 2.8) &
                 (Z < ztop + 2.4 - np.abs(np.hypot(X - x, Y - y)) * 0.8), tone=0.3)
        else:
            fill(m, (x - 3, x + 3, y - 3, y + 3, ztop, ztop + 2.4), "travertine",
                 lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 2.8, tone=0.2)
        if 7 <= i <= 14:          # lamps in the shops at the middle of the curve
            lamp(m, x, y, 3.0, 0.45, r=6.0)
    RM.lean_to(m, (cx - R - 3 * T, cx + R + 3 * T, 0.0, cy - R - 10.0), z - 3.0, z + 4.0, "-y", "terracotta", 443)
    # The upper terraces and the Via Biberatica, then the great hall.
    for i, (x0, x1, y0, y1, h) in enumerate(((4.0, D - 4.0, 2.0, 3 * T, z + 14.0),
                                             (4.0, 7 * T, 3 * T, 6 * T, z + 6.0))):
        RM.wall(m, (x0, x1, y0, y1), 0.0, h, "brick", 444 + i)
        for f_ in ("+x", "+y"):
            L = (y1 - y0) if f_ == "+x" else (x1 - x0)
            for s0 in np.arange(5.0, L - 6.0, 9.0):
                RM.window(m, f_, (x0, x1, y0, y1), s0, 3.0, h - 10.0, 4.0, arched=True, lit=0.3)
        RM.lean_to(m, (x0 - 1, x1 + 1, y0 - 1, y1 + 1), h, h + 3.0, "-y" if i == 0 else "-x", "terracotta", 446 + i)
    hall = (5 * T, 13 * T, 2.0, 2.6 * T)
    RM.wall(m, hall, z + 14.0, z + 30.0, "brick", 448)
    for i in range(6):
        RM.groin_roof(m, (hall[0] + i * (hall[1] - hall[0]) / 6, hall[0] + (i + 1) * (hall[1] - hall[0]) / 6,
                          hall[2], hall[3]), z + 30.0, "whitewash", seed=449 + i)
    paving(m, (7 * T, D - 4.0, 3 * T, 4.2 * T), z + 6.0, z + 7.0, "basalt", 3.0, 3.0, 450)


def augustus_forum(m):
    """The Forum of Augustus with the Temple of Mars Ultor (2 BC): an octastyle Corinthian
    temple of white marble on a high podium facing south down the square, against the huge
    grey tufa firewall that shut out the Subura; porticoes on the sides with niches for the
    statues of the great men of Rome (summi viri), and the exedra with Aeneas carrying Anchises
    and leading Ascanius, Romulus with the spoils facing him."""
    W, D = 13 * T, 13 * T
    paving(m, (6 * T, D - 2.0, 2.0, W - 2.0), 0.0, 0.8, "marble", 7.0, 6.0, 461)
    # The firewall: tufa blocks, irregular in plan along the north and east, 33 m high.
    zf = S.v(33.0)

    def firewall(X, Y, Z):
        north = (X < 10.0 + 4.0 * np.sin(Y * 0.05)) & (Y < W - 2.0)
        east = (Y < 10.0 + 3.0 * np.sin(X * 0.06)) & (X < D - 2.0)
        return (north | east) & (Z < zf - 4.0 * (hash01(np.floor((X + Y) / 9).astype(np.int64), 7) > 0.8))
    fill(m, (0.0, D, 0.0, W, 0.0, zf), "tufa", firewall, tone=M.ashlar(S.v(0.6), 6.0, 462, spread=0.8, odd=0.2))
    for z in (S.v(10.0), S.v(22.0)):
        fill(m, (0.0, D, 0.0, W, z, z + 1.0), "travertine", lambda X, Y, Z: firewall(X, Y, Z * 0 + z), tone=0.3,
             only_solid=True)
    t = RM.RTemple(order=RM.ROrder("corinthian", D=1.76, H=17.7), front="+x", cols=8, deep=3, plan="sine_postico",
                   flank=7, podium=3.5, pediment="mars", acroteria="statues", seed=463)
    RM.temple(m, t, S, (12.0, 6.5 * T, 12.0 + 4 * T - 2.0, 12.0 + 8 * T))
    # West portico with niches of the summi viri and the exedra.
    pb = (6 * T, D - 4.0, W - 7.0, W - 2.0)
    RM.wall(m, pb, 0.0, S.v(16.0), "marble", 464, "marble")
    RM.lean_to(m, (6 * T, D - 4.0, W - 3 * T - 8.0, W - 1.0), S.v(9.0) + 4.0, S.v(16.0), "+y", "terracotta", 466)
    for s0 in np.arange(6.0, pb[1] - pb[0] - 8.0, 10.0):
        RM.opening(m, "-y", pb, s0, 5.0, 2.0, 12.0, 2.0, back="giallo")
    RM.colonnade(m, (6 * T + 4.0, W - 3 * T - 6.0), (D - 8.0, W - 3 * T - 6.0), 1.0, 9, GIALLO, S, 10.0, "-y",
                 back=False, seed=465)
    from sets.rome.common import ARMOURED as ROMULUS
    aeneas = Dress(body="man", skin="skin_tan", hair="cedar", hair_style="curls", beard="short", garment="tunic",
                   colour="marble", worn=("cuirass",), cape="marble", hold="front", hand_l="baby", feet="boots")
    RM.statue(m, 8.5 * T, W - 1.5 * T, 0.8, 16.0, aeneas, material="marble", base=(6.0, 5.0))
    RM.statue(m, 11 * T, W - 1.5 * T, 0.8, 16.0, ROMULUS, material="marble", base=(6.0, 5.0))
    RM.statue(m, 10 * T, 6 * T, 0.8, 18.0, TOGATE, material="gold", keep=(), base=(6.0, 7.0))


def caesar_forum(m):
    """The Forum of Caesar: a long narrow square closed by colonnades, the Temple of Venus
    Genetrix (restored by Trajan in 113) at its north-west end facing south down the square,
    Caesar's equestrian statue before it, the Basilica Argentaria of the bankers behind the
    west colonnade."""
    W, D = 12 * T, 10 * T
    paving(m, (0.0, D, 2 * T, W - 2 * T), 0.0, 0.8, "marble", 7.0, 6.0, 471)
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.4, H=15.0), front="+x", cols=8, deep=3,
                            plan="sine_postico", flank=6, podium=4.0, pediment="gods", seed=472),
              S, (2.0, 4 * T + 6.0, W - 4.5 * T, W - 2.0))
    o = RM.ROrder("corinthian", D=0.9, H=9.0)
    RM.colonnade(m, (4 * T + 6.0, 2 * T + 4.0), (D - 4.0, 2 * T + 4.0), 0.8, 8, o, S, 10.0, "+y", seed=473)
    RM.colonnade(m, (5 * T, W - 2 * T - 4.0), (D - 4.0, W - 2 * T - 4.0), 0.8, 7, o, S, 10.0, "-y", seed=474)
    bb = (4 * T, D - 2.0, W - 1.6 * T, W - 2.0)
    RM.wall(m, bb, 0.0, S.v(18.0), "brick", 475)
    RM.arcade_front(m, "+y", bb, 0.0, [(S.v(9.0), "tuscan", "travertine"), (S.v(9.0), "tuscan", "travertine")], 6)
    RM.gable(m, (bb[0] - 1.0, bb[1] + 1.0, bb[2] - 1.0, bb[3] + 1.0), S.v(18.0), 6.0, "x", seed=476)
    RM.statue(m, 6 * T, W / 2, 0.8, 12.0, TRAJAN_RIDER, material="bronze_cast", keep=(), base=(8.0, 6.0))


def nerva_forum(m):
    """The Forum of Nerva (Transitorium): a long narrow passage between walls, the columns
    standing close before the walls carrying a projecting entablature with the frieze of
    women's crafts and Minerva in the attic; the Temple of Minerva at the north end."""
    W, D = 4 * T, 12 * T
    paving(m, (0.0, D, 0.0, W), 0.0, 0.8, "marble", 6.0, 5.0, 481)
    for y0, y1, face in ((0.0, 4.0, "+y"), (W - 4.0, W, "-y")):
        wb = (3 * T, D, y0, y1)
        RM.wall(m, wb, 0.0, S.v(17.0), "tufa", 482)
        yc = y1 + 3.0 if face == "+y" else y0 - 3.0
        for x in np.linspace(3 * T + 6.0, D - 6.0, 8):
            RM.column(m, x, yc, 0.8, RM.ROrder("corinthian", D=1.0, H=10.0), S)
        img, cmap = RR.crafts_image(int((D - 3 * T) * 2), 8)
        eb = (3 * T, D, min(y0, yc - 3.0), max(y1, yc + 3.0))
        RM.wall(m, eb, 0.8 + S.v(10.0), 0.8 + S.v(10.0) + 6.0, "marble", 483)
        from relief import emboss
        emboss(m, face, eb, 0.0, 0.8 + S.v(10.0) + 5.0, img, cmap=cmap)
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.2, H=12.0), front="+x", cols=6, deep=2,
                            podium=3.5, pediment="gods", seed=484), S, (2.0, 3 * T + 8.0, 4.0, W - 4.0))


def pacis(m):
    """The Templum Pacis: a square garden with long water channels and flower beds between
    rows of roses, porticoes of red granite on three sides holding works of art (the menorah
    from Jerusalem among them), the temple hall and the library on the east side."""
    W, D = 14 * T, 15 * T
    for i in range(6):          # beds and channels running north-south
        y0 = 3 * T + i * 1.4 * T
        fill(m, (3 * T, D - 3 * T, y0, y0 + 0.7 * T, 0.0, 1.0), "soil", tone=-0.1)
        box_hedge(m, 3 * T, D - 3 * T, y0, y0 + 2.0, 1.0)
        fill(m, (3 * T, D - 3 * T, y0 + 0.7 * T, y0 + 0.7 * T + 3.0, 0.0, 1.0), "marble", tone=0.2)
        fill(m, (3 * T, D - 3 * T, y0 + 0.7 * T + 0.6, y0 + 0.7 * T + 2.4, 0.4, 1.0), "water",
             tone=lambda X, Y, Z: 0.3 * (np.sin(X * 0.8) > 0.85))
        for x in np.arange(3 * T + 6.0, D - 3 * T, 14.0):
            fill(m, (x - 1.4, x + 1.4, y0 + 4.0, y0 + 9.0, 1.0, 3.6), "blossom",
                 lambda X, Y, Z, x=x: np.hypot(X - x, (Z - 2.0) * 1.2) < 1.6, tone=0.2)
    o = RM.ROrder("corinthian", D=0.9, H=9.0, shaft="granite_pink", fluted=False)
    RM.colonnade(m, (2 * T, 2 * T), (2 * T, W - 2 * T), 0.0, 12, o, S, 2 * T - 4.0, "+x", seed=491)
    RM.colonnade(m, (D - 2 * T, 2 * T), (D - 2 * T, W - 2 * T), 0.0, 12, o, S, 2 * T - 4.0, "-x", seed=492)
    RM.colonnade(m, (2 * T + 8.0, W - 2 * T), (D - 2 * T - 8.0, W - 2 * T), 0.0, 10, o, S, 2 * T - 4.0, "-y", seed=493)
    hb = (5 * T, 10 * T, 2.0, 2 * T)
    RM.wall(m, hb, 0.0, S.v(20.0), "brick", 494)
    RM.colonnade(m, (5 * T + 4.0, 2 * T + 3.0), (10 * T - 4.0, 2 * T + 3.0), 0.0, 6,
                 RM.ROrder("corinthian", D=1.2, H=13.0, shaft="granite_pink", fluted=False), S, 4.0, "+y", back=False,
                 seed=495)
    RM.gable(m, (hb[0] - 1.0, hb[1] + 1.0, hb[2] - 1.0, hb[3] + 6.0), S.v(20.0), 10.0, "x", seed=496)


LANDMARKS = {
    "rome.trajan_forum": Landmark((13, 25), (0, 96), ref("trajan_forum"), district=3, walk=TRAJ_WALK,
                                  slots={"crowd": [{"t": [3, 8]}, {"t": [5, 16]}, {"t": [8, 10]}, {"t": [9, 15]}],
                                         "apollodorus": [{"t": [2, 12], "face": "-x"}]}),
    "rome.basilica_ulpia": Landmark((5, 21), (0, 112), ref("basilica_ulpia"), district=3),
    "rome.trajan_column": Landmark((4, 9), (0, 104), ref("trajan_column"), district=3,
                                   slots={"read": [{"t": [4, 2], "face": "-x"}, {"t": [4, 6], "face": "-x"}]}),
    "rome.trajan_temple": Landmark((6, 9), (0, 128), ref("trajan_temple"), district=3),
    "rome.trajan_markets": Landmark((18, 13), (0, 120), ref("trajan_markets"), district=3,
                                    slots={"shop": [{"t": [5, 13], "face": "-y"}, {"t": [9, 13], "face": "-y"},
                                                    {"t": [13, 13], "face": "-y"}]}),
    "rome.augustus_forum": Landmark((13, 13), (0, 104), ref("augustus_forum"), district=3),
    "rome.caesar_forum": Landmark((10, 12), (0, 96), ref("caesar_forum"), district=3),
    "rome.nerva_forum": Landmark((12, 4), (0, 80), ref("nerva_forum"), district=3),
    "rome.pacis": Landmark((15, 14), (0, 80), ref("pacis"), district=3),
}

INFO = {
    "rome.trajan_forum": ("Forum of Trajan", 0.5, 120, "BS", "trajan_forum"),
    "rome.basilica_ulpia": ("Basilica Ulpia", 0.5, 125, "BS", "basilica_ulpia"),
    "rome.trajan_column": ("Trajan's Column and libraries", 0.5, 200, "BSG", "trajan_column"),
    "rome.trajan_temple": ("Temple of Divus Traianus", 0.5, 140, "BS", "trajan_temple"),
    "rome.trajan_markets": ("Trajan's Markets", 0.5, 160, "BSG", "trajan_markets"),
    "rome.augustus_forum": ("Forum of Augustus and Temple of Mars Ultor", 0.5, 165, "BS", "augustus_forum"),
    "rome.caesar_forum": ("Forum of Caesar and Temple of Venus Genetrix", 0.5, 120, "BS", "caesar_forum"),
    "rome.nerva_forum": ("Forum of Nerva", 0.5, 110, "BS", "nerva_forum"),
    "rome.pacis": ("Templum Pacis", 0.5, 90, "BS", "pacis"),
}
