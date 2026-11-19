"""The Capitol and the Forum Romanum (rome.md §2.3 D1-D2, §3.2): the Temple of Jupiter
Optimus Maximus with its gilded roof facing south, the Arx with Juno Moneta, the Tabularium,
the temples of Concord, of Vespasian and Titus and of Saturn, the Rostra with ships' rams and
the Golden Milestone, the Curia, the Lapis Niger, the basilicas Aemilia and Iulia, the forum
square with the Lacus Curtius and the fig, olive and vine, the temples of Castor, of the deified
Caesar and of Vesta, the Regia, the House of the Vestals, the spring of Juturna and the Horrea
Piperataria. Monuments at s = 0.65 (one tile about 6.2 m)."""


import numpy as np

import waterworks

import materials as M
import roman as RM
from arch import Scale, carve, ellipsoid, fill, halo, revolve, rod, slab
from setbuild import Landmark
from sets.rome.common import (ARMOURED, CAPITOLINE, CASTOR, FIRE, GODDESS, S65, SATURN, SMALL, T, TEMPLE, TOGATE,
                              VESTAL, cypress, lamp, olive_tree, paving, referrer, tc)
from voxel import hash01

ref = referrer("sets.rome.forum")
S = S65


def capitolium(m):
    """The Capitolium as rebuilt by Domitian: a hexastyle Corinthian temple of Pentelic marble
    on a huge tufa podium faced in marble, three rows of columns before the front and a row
    down each flank, three cellae (Jupiter in the middle, Juno and Minerva at his sides) with
    three doors, the roof of gilded bronze tiles, the bronze chariot of Jupiter on the apex,
    the pediment with the Capitoline triad, statues and dedications crowding the platform."""
    t = RM.RTemple(order=CAPITOLINE, front="+x", cols=6, deep=3, plan="sine_postico", flank=7, podium=5.0,
                   podium_kind="marble", roof="gilt", pediment="triad", acroteria="quadriga", seed=201,
                   door_glow=0.6, stair_frac=0.18)
    h = RM.temple(m, t, S, (2.0, 10 * T - 2.0, 2.0, 9 * T - 2.0))
    cb = h["cella"]
    for s_ in (0.22, 0.78):     # the side doors of Juno's and Minerva's cellae
        L = cb[3] - cb[2]
        fill(m, (cb[1] - 0.6, cb[1] + 0.1, cb[2] + L * s_ - 3.0, cb[2] + L * s_ + 3.0, h["podium"], h["podium"] +
                 S.v(9.0)), "bronze", tone=lambda X, Y, Z: 0.4 * ((Z % 4.0) < 0.6) - 0.1)
    for i, y in enumerate((10.0, 9 * T - 10.0)):     # statues on the platform before the stairs
        RM.statue(m, 10 * T - 8.0, y, 0.0, 14.0, TOGATE if i else ARMOURED, material="bronze_cast", base=(4.0, 6.0))


def arx(m):
    """The Arx: the Temple of Juno Moneta on the north summit (the mint had stood beside it),
    a precinct wall and the augurs' platform."""
    RM.temple(m, RM.RTemple(order=TEMPLE, front="+x", cols=6, deep=2, plan="prostyle", podium=3.0, pediment="gods",
                            seed=211), S, (8.0, 6 * T - 4.0, 2 * T, 8 * T))
    RM.wall(m, (2.0, 4.0, 2.0, 9 * T - 2.0), 0.0, 8.0, "tufa", 212)
    RM.wall(m, (2.0, 6 * T - 2.0, 2.0, 4.0), 0.0, 8.0, "tufa", 213)
    slab(m, 3 * T, 5 * T, 4.0, 1.5 * T, 0.0, 3.0, "tufa", tone=0.2)
    for i in range(3):
        cypress(m, 12.0 + i * 14.0, 9 * T - 10.0, 0.0, h=34.0, seed=i)


def tabularium(m):
    """The Tabularium (the state record office) at the foot of the Capitol: a massive tufa
    substructure with small windows, the arcaded gallery above with Doric half columns
    looking down the Forum (east), the corridor of brick behind."""
    W, D = 5 * T, 12 * T                      # y, x
    wb = (2.0, D - 2.0, 2.0, W - 2.0)
    zb = S.v(15.0)
    slab(m, *wb, 0.0, zb, "tufa", tone=M.ashlar(S.v(0.6), 7.0, 221, joint=0.35, spread=0.7))
    for s_ in np.arange(8.0, D - 12.0, 14.0):
        RM.window(m, "-y", wb, s_, 2.4, zb * 0.55, 3.2)
        RM.window(m, "+x", wb, 10.0, 2.4, zb * 0.55, 3.2)
    RM.cornice(m, wb, zb - 1.4, 1.4, 0.8, "travertine")
    gb = (2.0, D - 2.0, 2.0, W * 0.55)
    RM.wall(m, gb, zb, zb + S.v(8.5), "tufa", 222)
    RM.arcade_front(m, "-y", gb, zb, [(S.v(8.5), "tuscan", "travertine")], 11, depth=5.0)
    RM.wall(m, (2.0, D - 2.0, W * 0.55, W - 2.0), zb, zb + S.v(12.0), "brick", 223)
    RM.lean_to(m, (1.0, D - 1.0, 1.0, W * 0.6), zb + S.v(8.5), zb + S.v(10.5), "+y", "terracotta", 224)
    RM.gable(m, (1.0, D - 1.0, W * 0.53, W - 1.0), zb + S.v(12.0), 6.0, "x", seed=225)


def concord(m):
    """The Temple of Concord: a wide transverse cella (a gallery of famous art inside) with a
    hexastyle porch on its long east side, facing the Forum."""
    W, D = 4 * T, 7 * T
    RM.wall(m, (4.0, D - 4.0, 4.0, W * 0.62), S.v(3.0), S.v(3.0) + S.v(13.0), "marble", 231)
    slab(m, 2.0, D - 2.0, 2.0, W * 0.64, 0.0, S.v(3.0), "marble", tone=M.ashlar(2.4, 6.0, 232, spread=0.3))
    RM.gable(m, (2.0, D - 2.0, 2.0, W * 0.66), S.v(16.0), 10.0, "x", material="terracotta", seed=233)
    RM.temple(m, RM.RTemple(order=SMALL, front="-y", cols=6, deep=2, podium=3.0, pediment="gods", seed=234,
                            stair_frac=0.3), S, (D / 2 - 26.0, D / 2 + 26.0, W * 0.45, W - 1.0))


def vespasian(m):
    """The Temple of Vespasian and Titus: hexastyle Corinthian on a high podium, facing east."""
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.4, H=15.2), front="-y", cols=6, deep=2, podium=4.0,
                            pediment="gods", seed=241), S, (2.0, 4 * T - 2.0, 2.0, 4 * T - 2.0))


def saturn(m):
    """The Temple of Saturn, the state treasury (aerarium) in its high podium: an Ionic hexastyle
    porch of grey and pink granite shafts, facing east over the Forum; the treasury's door in
    the podium, an inscribed frieze."""
    t = RM.RTemple(order=SATURN, front="-y", cols=6, deep=3, podium=6.0, podium_kind="travertine", pediment="gods",
                   seed=251, stair_frac=0.24)
    h = RM.temple(m, t, S, (2.0, 4 * T - 2.0, 2.0, 7 * T - 2.0))
    fill(m, (4 * T - 2.6, 4 * T - 1.8, 30.0, 38.0, 0.0, 9.0), "bronze", tone=lambda X, Y, Z: 0.4 * ((Z % 3.0) < 0.5))


def rostra(m):
    """The Rostra Augusti: a curved-fronted platform faced with marble and studded with the
    bronze rams of captured ships, a railing, honorific columns and statues on top; the Golden
    Milestone (miliarium aureum) beside it."""
    W, D = 4 * T, 3 * T
    zh = S.v(3.5)
    fill(m, (2.0, D - 2.0, 2.0, W - 8.0, 0.0, zh), "marble",
         lambda X, Y, Z: (Y > 8.0) | (np.hypot((X - D / 2) / (D / 2 - 2.0), (Y - 8.0) / 7.0) <= 1),
         tone=RM.marble_veneer(261, 4.0, 3.0))
    for i in range(7):      # the rams in two rows along the east face
        x = 6.0 + i * (D - 12.0) / 6
        for zz in (zh * 0.35, zh * 0.7):
            rod(m, (x, 3.0, zz), (x, -0.5, zz - 0.6), 0.9, "bronze_cast", tone=0.3)
            ellipsoid(m, (x, -0.8, zz - 0.7), (0.9, 1.0, 0.7), "bronze_cast", 0.4)
    fill(m, (2.0, D - 2.0, 2.0, W - 8.0, zh, zh + 2.6), "bronze",
         lambda X, Y, Z: (((X + Y) % 2.0) < 0.5) | (Z > zh + 2.2), tone=0.2, only_empty=True)
    # The rail is a ring of posts and a top bar round the edge; inside it the marble deck is
    # open to the sky (the carve once stopped under the bar's height and left a bronze lid
    # over the whole platform, V7-013).
    carve(m, (4.0, D - 4.0, 4.0, W - 10.0, zh, zh + 2.7))
    for x, y in ((8.0, 18.0), (D - 8.0, 18.0)):
        RM.column(m, x, y, zh, RM.ROrder("corinthian", D=0.8, H=8.0), S)
        RM.statue(m, x, y, zh + S.v(8.0) + 0.5, 10.0, TOGATE, material="gold", keep=())
    RM.statue(m, D / 2, 30.0, zh, 13.0, ARMOURED, material="bronze_cast")
    # The Golden Milestone: a marble column clad in gilded bronze naming the distances.
    revolve(m, D - 6.0, W - 4.0, 0.0, 9.0, lambda t: 1.6 - 0.2 * t, "gold", tone=0.2)


def curia(m):
    """The Curia Iulia, the Senate house: a tall brick hall faced with stucco imitating marble
    blocks on its front, a plain gable, a porch of columns before the bronze doors (the porch
    of Augustus's day), lamps at the door."""
    W, D = 4 * T, 4 * T
    hb = (4.0, D - 12.0, 6.0, W - 6.0)
    H = S.v(21.0)
    RM.wall(m, hb, 0.0, H, "brick", 271)
    fill(m, (hb[1] - 0.5, hb[1] + 0.3, hb[2], hb[3], 0.0, H), "whitewash",
         tone=M.ashlar(2.6, 8.0, 272, joint=0.25, spread=0.15), only_empty=False)
    RM.cornice(m, hb, H - 1.4, 1.4, 1.0, "travertine")
    RM.pediment(m, "+x", (hb[0] - 1.0, hb[1] + 1.0, hb[2] - 1.0, hb[3] + 1.0), H, 9.0, S, "whitewash")
    RM.gable(m, (hb[0] - 1.0, hb[1] + 1.0, hb[2] - 1.0, hb[3] + 1.0), H, 9.0, "x", seed=273)
    for i in range(3):     # three windows high in the front
        RM.window(m, "+x", hb, 8.0 + i * 13.0, 5.0, H * 0.62, 6.0, glass=True, lit=0.4)
    fill(m, (hb[1] - 0.6, hb[1] + 0.2, W / 2 - 4.0, W / 2 + 4.0, 3.0, 17.0), "bronze",
         tone=lambda X, Y, Z: 0.4 * ((Z % 3.5) < 0.5) - 0.1)
    slab(m, hb[1], D - 2.0, 6.0, W - 6.0, 0.0, 3.0, "marble", tone=0.25)
    for y in np.linspace(10.0, W - 10.0, 4):
        RM.column(m, D - 5.0, y, 3.0, RM.ROrder("corinthian", D=0.75, H=7.0), S)
    slab(m, hb[1], D - 2.0, 6.0, W - 6.0, 3.0 + S.v(7.0), 4.5 + S.v(7.0), "marble", tone=0.3)
    lamp(m, hb[1] + 1.0, W / 2 - 6.0, 9.0, 0.6)
    lamp(m, hb[1] + 1.0, W / 2 + 6.0, 9.0, 0.6)


def lapis_niger(m):
    """The Lapis Niger: a square of black marble paving in the Comitium within a low fence."""
    fill(m, (2.0, 14.0, 2.0, 14.0, 0.0, 0.8), "gloss", tone=lambda X, Y, Z: (hash01(np.floor(X).astype(np.int64),
                                                                                       np.floor(Y).astype(np.int64), 3) - 0.5) * 0.6)
    fill(m, (1.0, 15.0, 1.0, 15.0, 0.0, 3.0), "marble",
         lambda X, Y, Z: ((X < 2.0) | (X > 14.0) | (Y < 2.0) | (Y > 14.0)) & ((((X + Y) % 2.0) < 0.6) | (Z > 2.4)), 0.2)


def aemilia(m):
    """The Basilica Aemilia: a two-storey arcaded front of white marble along the Forum square
    (south), shops (tabernae) behind the lower arcade, the great hall behind with its high nave
    and clerestory."""
    box = (2.0, 6 * T - 1.0, 2.0, 16 * T - 2.0)
    RM.basilica(m, box, "+x", S, 16, [(S.v(9.5), "tuscan", "marble"), (S.v(8.5), "ionic", "marble")], 18.0,
                S.v(13.0), S.v(24.0), seed=281, statue_mat="marble")
    for i in range(16):      # shop counters and goods glimpsed behind the lower arcade
        y = 2.0 + (i + 0.5) * (16 * T - 4.0) / 16
        slab(m, 6 * T - 18.0, 6 * T - 16.0, y - 3.0, y + 3.0, 0.0, 3.0, "brick", tone=0.1)


def forum_square(m):
    """The forum square: travertine paving with the bronze letters of an old inscription, the
    Lacus Curtius well-head, honorary columns with gilded statues, statues on bases, and the
    fig, olive and vine Pliny saw growing in the Forum. All open tiles are walk tiles."""
    W, D = 13 * T, 10 * T
    paving(m, (0.0, D, 0.0, W), 0.0, 0.6, "travertine", 7.0, 5.0, 291)
    # Surdinus's inscription in bronze letters set into the paving (QA4 V-A-009: not a yellow
    # patch): a line of dark bronze glyphs with gaps between the words.
    fill(m, (4 * T + 1.0, 4 * T + 3.0, 2 * T, 11 * T, 0.4, 0.7), "bronze",
         lambda X, Y, Z: ((np.floor(Y * 2) % 3) < 2) & (np.floor(Y / 7.0) % 4 != 3) &
         (hash01(np.floor(Y * 2).astype(np.int64), np.floor(X * 2).astype(np.int64), 291) < 0.7),
         tone=-0.3, only_solid=True)
    # The Lacus Curtius: a round well-head in a paved enclosure (tile 7, 3).
    x, y = tc(7), tc(3)
    slab(m, x - 6.0, x + 6.0, y - 6.0, y + 6.0, 0.0, 1.2, "marble", tone=0.25)
    revolve(m, x, y, 1.2, 4.2, lambda t: 2.6, "marble", tone=0.2)
    fill(m, (x - 2, x + 2, y - 2, y + 2, 3.5, 4.3), "ink", lambda X, Y, Z: np.hypot(X - x, Y - y) < 1.8)
    # The fig, the olive and the vine (tile 7, 5..6).
    from sets.athens.kit import _fig
    _fig(m, tc(7) - 2.0, tc(5), 0.0, 16.0, 292)
    olive_tree(m, tc(6), tc(6), 0.0, h=18.0, seed=293)
    for i in range(3):
        rod(m, (tc(7) + 4.0, tc(6) - 4.0 + i * 4.0, 0.0), (tc(7) + 4.0, tc(6) - 4.0 + i * 4.0, 9.0), 0.35, "wood")
    from models.nature import leaf_mass
    leaf_mass(m, [(tc(7) + 4.0, tc(6), 9.5, 3.4)], 294, materials=(("leaf", 1.0),), under="leaf_dark", squash=0.6)
    # Honorary columns with gilded statues (tiles (1, 2), (1, 6), (1, 10)) and statues on bases.
    for tx, ty in ((1, 2), (1, 6), (1, 10)):
        xx, yy = tc(tx), tc(ty)
        slab(m, xx - 3.0, xx + 3.0, yy - 3.0, yy + 3.0, 0.0, 4.0, "marble", tone=0.2)
        RM.column(m, xx, yy, 4.0, RM.ROrder("corinthian", D=0.9, H=9.0, shaft="granite", fluted=False), S)
        RM.statue(m, xx, yy, 4.0 + S.v(9.0), 10.0, TOGATE, material="gold", keep=())
    for i, (tx, ty) in enumerate(((5, 1), (5, 11), (9, 8))):
        RM.statue(m, tc(tx), tc(ty), 0.0, 12.0, (TOGATE, ARMOURED, GODDESS)[i], material="bronze_cast", base=(5.0, 5.0))


SQUARE_SOLID = {(7, 3), (7, 5), (6, 6), (7, 6), (1, 2), (1, 6), (1, 10), (5, 1), (5, 11), (9, 8), (5, 6), (6, 5),
                (6, 7), (8, 6), (8, 5), (7, 7), (7, 4), (6, 4), (8, 4)}
SQUARE_WALK = [(x, y) for x in range(10) for y in range(13) if (x, y) not in SQUARE_SOLID]


def julia(m):
    """The Basilica Iulia, seat of the centumviral court: a two-storey hall of arcades on piers
    with Tuscan half columns, open on its north front to the Forum, a high nave with a
    clerestory; gaming boards scratched into its steps."""
    box = (2.0, 8 * T - 2.0, 2.0, 16 * T - 2.0)
    RM.basilica(m, box, "-x", S, 16, [(S.v(10.0), "tuscan", "marble"), (S.v(9.0), "tuscan", "marble")], 26.0,
                S.v(14.0), S.v(25.0), seed=301)
    RM.basilica(m, box, "+x", S, 16, [(S.v(10.0), "tuscan", "marble"), (S.v(9.0), "tuscan", "marble")], 18.0,
                S.v(14.0), S.v(25.0), seed=302)
    for i in range(4):      # steps on the Forum side, gaming boards scratched in
        slab(m, 0.0 + i * 0.8, 2.0, 2.0, 16 * T - 2.0, i * 0.8, (i + 1) * 0.8, "marble",
             tone=lambda X, Y, Z: 0.3 - 0.6 * ((np.floor(Y) % 9 == 0) & ((np.floor(X * 2) % 2) == 0)))


def castor(m):
    """The Temple of Castor and Pollux: octastyle Corinthian of white marble on a very high
    podium (three of its columns stand today), peripteral, facing north onto the Forum with a
    speakers' platform before the porch."""
    RM.temple(m, RM.RTemple(order=CASTOR, front="-x", cols=8, deep=3, plan="peripteral", flank=11, podium=7.0,
                            pediment="gods", stairs="rostra", seed=311),
              S, (2.0, 8 * T - 2.0, 2.0, 5 * T - 2.0))


def lacus_iuturnae(m):
    """The spring of Juturna: a square marble basin with a pier in the middle carrying the
    statues of the Dioscuri and their horses."""
    slab(m, 2.0, 2 * T - 2.0, 2.0, T - 2.0, 0.0, 2.6, "marble", tone=0.25)
    # The basin is sunk in the marble (its water was buried in the slab before: no pixel of it showed).
    carve(m, (3.0, 2 * T - 3.0, 3.0, T - 3.0, 1.8, 2.7))
    waterworks.surface(m, (3.0, 2 * T - 3.0, 3.0, T - 3.0), 1.8, 0, 1, seed=2351, depth_units=2.5)
    slab(m, T - 3.0, T + 3.0, 5.0, 11.0, 0.0, 4.0, "marble", tone=0.2)
    from rig import Dress
    twin = Dress(body="man", garment="none", hair_style="curly", beard="none", head="pilleus", head_mat="marble",
                 hand_l="spear", feet="bare")
    RM.statue(m, T - 1.5, 8.0, 4.0, 10.0, twin, material="marble", keep=())
    RM.statue(m, T + 1.5, 8.0, 4.0, 10.0, twin, material="marble", keep=())


def divus_julius(m):
    """The Temple of the deified Julius, built where Caesar was cremated: hexastyle on a podium
    facing west, with a speakers' platform before it faced with ships' rams and a round altar
    in a niche in its front."""
    h = RM.temple(m, RM.RTemple(order=TEMPLE, front="+y", cols=6, deep=2, podium=4.0, pediment="gods",
                                stairs="rostra", seed=321), S, (2.0, 5 * T - 2.0, 2.0, 4 * T - 2.0))
    for i in range(5):
        x = 16.0 + i * 12.0
        rod(m, (x, 4 * T - 4.0, 5.0), (x, 4 * T + 0.5, 4.4), 0.8, "bronze_cast", tone=0.3)
    x = 2.5 * T
    RM.opening(m, "+y", (2.0, 5 * T - 2.0, 2.0, 4 * T - 2.0), x - 5.0, 10.0, 0.0, 6.0, 4.0, back="marble")
    revolve(m, x, 4 * T - 4.5, 0.0, 4.5, lambda t: 2.4, "marble", tone=0.2)


def regia(m):
    """The Regia, office of the Pontifex Maximus: a small marble building, its trapezoid court."""
    RM.wall(m, (4.0, 2 * T - 4.0, 4.0, 3 * T - 4.0), 0.0, S.v(8.0), "marble", 331)
    RM.gable(m, (3.0, 2 * T - 3.0, 3.0, 3 * T - 3.0), S.v(8.0), 6.0, "y", seed=332)
    fill(m, (2 * T - 4.5, 2 * T - 3.5, 20.0, 26.0, 0.0, 11.0), "bronze", tone=0.2)


VESTA_S = Scale(0.85)


def vesta(m):
    """The Temple of Vesta: round, twenty Corinthian columns on a high round podium, a conical
    roof with a smoke opening at its top; the eternal fire glowing at the door at night. Drawn
    at s = 0.85, filling its 3 x 3 tiles, so the roof shows over Castor's and the Regia's
    eaves (QA4 V-B-003: at the monuments' 0.65 it was hidden)."""
    RM.round_temple(m, 1.5 * T, 1.5 * T, 0.0, 1.5 * T - 0.8, 20, RM.ROrder("corinthian", D=0.55, H=6.8), VESTA_S,
                    steps=6, roof="bronze_cast", smoke_hole=True, door_face="-y", glow=0.9, seed=341)
    halo(m, 1.5 * T, 1.5 * T, 38.0, 10.0, FIRE, 0.5)


def vestals(m):
    """The House of the Vestals: a two-storey house of brick round a long courtyard with three
    pools in a row, a colonnade round the court, statues of senior Vestals, rooms behind."""
    W, D = 7 * T, 7 * T
    H = S.v(9.0)
    for wb in ((2.0, 20.0, 2.0, W - 2.0), (D - 20.0, D - 2.0, 2.0, W - 2.0), (20.0, D - 20.0, 2.0, 18.0),
               (20.0, D - 20.0, W - 18.0, W - 2.0)):
        RM.wall(m, wb, 0.0, H, "brick", 351)
        RM.hip(m, (wb[0] - 1.0, wb[1] + 1.0, wb[2] - 1.0, wb[3] + 1.0), H, 9.0, seed=352)
    for s_ in np.arange(8.0, W - 12.0, 12.0):
        RM.window(m, "+x", (D - 20.0, D - 2.0, 2.0, W - 2.0), s_, 3.0, H * 0.6, 4.0, shutter="wood", lit=0.35)
    paving(m, (20.0, D - 20.0, 18.0, W - 18.0), 0.0, 0.6, "marble", 5.0, 5.0, 353)
    for i in range(3):
        y0 = 24.0 + i * 24.0
        fill(m, (34.0, D - 34.0, y0, y0 + 16.0, 0.0, 1.4), "marble", tone=0.2)
        fill(m, (35.0, D - 35.0, y0 + 1.0, y0 + 15.0, 0.4, 1.2), "water",
             tone=lambda X, Y, Z: 0.3 * (np.sin((X + Y) * 1.5) > 0.8))
    o = RM.ROrder("corinthian", D=0.55, H=5.5, shaft="cipollino", fluted=False)
    for x in np.linspace(24.0, D - 24.0, 7):
        for y in (22.0, W - 22.0):
            RM.column(m, x, y, 0.6, o, S)
    for x in (30.0, D - 30.0):
        RM.statue(m, x, W / 2, 0.6, 11.0, VESTAL, material="marble", base=(3.6, 4.0))


def piperataria(m):
    """The Horrea Piperataria: Domitian's brick warehouses for pepper and spices from India, small
    barred windows, a court."""
    W, D = 9 * T, 6 * T
    wb = (2.0, D - 2.0, 2.0, W - 2.0)
    RM.wall(m, wb, 0.0, S.v(11.0), "brick", 361)
    carve(m, (20.0, D - 20.0, 22.0, W - 22.0, 1.0, S.v(11.0)))
    paving(m, (20.0, D - 20.0, 22.0, W - 22.0), 0.0, 1.0, "travertine", 5.0, 4.0, 362)
    for f in ("+x", "+y"):
        for s_ in np.arange(6.0, (W if f == "+x" else D) - 8.0, 8.0):
            RM.window(m, f, wb, s_, 1.6, S.v(7.0), 2.4)
            if s_ % 32 < 8:
                RM.opening(m, f, wb, s_ - 1.0, 4.0, 0.0, 6.0, 1.5, frame="travertine")
    RM.hip(m, (1.0, D - 1.0, 1.0, W - 1.0), S.v(11.0), 8.0, seed=363)


LANDMARKS = {
    "rome.capitolium": Landmark((10, 9), (0, 136), ref("capitolium"), district=2,
                                slots={"sacrifice": [{"t": [10, 4], "face": "-x"}]}),
    "rome.arx": Landmark((6, 9), (0, 96), ref("arx"), district=2),
    "rome.tabularium": Landmark((12, 5), (0, 112), ref("tabularium"), district=2),
    "rome.concord": Landmark((7, 4), (0, 96), ref("concord"), district=2),
    "rome.vespasian": Landmark((4, 4), (0, 112), ref("vespasian"), district=2),
    "rome.saturn": Landmark((4, 7), (0, 112), ref("saturn"), district=2),
    "rome.rostra": Landmark((3, 4), (0, 56), ref("rostra"), district=2,
                            slots={"orator": [{"t": [1, -1], "face": "-y"}]}),
    "rome.curia": Landmark((4, 4), (0, 96), ref("curia"), district=2,
                           slots={"door": [{"t": [4, 2], "face": "+x"}], "senator": [{"t": [4, 2]}, {"t": [4, 3]}]}),
    "rome.lapis_niger": Landmark((1, 1), (0, 8), ref("lapis_niger"), district=2),
    "rome.aemilia": Landmark((6, 16), (0, 112), ref("aemilia"), district=2,
                             slots={"shop": [{"t": [6, 3], "face": "-x"}, {"t": [6, 8], "face": "-x"},
                                             {"t": [6, 12], "face": "-x"}]}),
    "rome.forum_square": Landmark((10, 13), (0, 48), ref("forum_square"), district=2, walk=SQUARE_WALK,
                                  slots={"crowd": [{"t": [3, 4]}, {"t": [4, 7]}, {"t": [6, 9]}, {"t": [8, 3]},
                                                   {"t": [2, 8]}, {"t": [5, 5]}],
                                         "school": [{"t": [8, 11], "face": "-y"}]}),
    "rome.julia": Landmark((8, 16), (0, 112), ref("julia"), district=2,
                           slots={"court": [{"t": [-1, 4], "face": "+x"}, {"t": [-1, 8], "face": "+x"}],
                                  "game": [{"t": [-1, 11], "face": "+x"}]}),
    "rome.castor": Landmark((8, 5), (0, 128), ref("castor"), district=2),
    "rome.lacus_iuturnae": Landmark((2, 1), (0, 24), ref("lacus_iuturnae"), district=2,
                                    slots={"fill": [{"t": [1, -1], "face": "+y"}]}),
    "rome.divus_julius": Landmark((5, 4), (0, 96), ref("divus_julius"), district=2),
    "rome.regia": Landmark((2, 3), (0, 40), ref("regia"), district=2),
    "rome.vesta": Landmark((3, 3), (0, 96), ref("vesta"), district=2,
                           slots={"vestal": [{"t": [1, 3], "face": "-y"}]}, emitters={"smoke": (24.0, 24.0, 60.0)}),
    "rome.vestals": Landmark((7, 7), (0, 48), ref("vestals"), district=2,
                             slots={"door": [{"t": [7, 3], "face": "+x"}]}),
    "rome.piperataria": Landmark((6, 9), (0, 56), ref("piperataria"), district=2,
                                 slots={"door": [{"t": [6, 2], "face": "+x"}]}),
}

INFO = {
    "rome.capitolium": ("Temple of Iuppiter Optimus Maximus (Capitolium)", 0.65, 200, "BSG", "capitolium"),
    "rome.arx": ("Arx and the Temple of Juno Moneta", 0.65, 110, "BS", "arx"),
    "rome.tabularium": ("Tabularium", 0.65, 150, "BS", "tabularium"),
    "rome.concord": ("Temple of Concord", 0.65, 120, "BS", "concord"),
    "rome.vespasian": ("Temple of Vespasian and Titus", 0.65, 120, "BS", "vespasian"),
    "rome.saturn": ("Temple of Saturn", 0.65, 140, "BS", "saturn"),
    "rome.rostra": ("Rostra", 0.65, 40, "BS", "rostra"),
    "rome.curia": ("Curia Iulia (Senate house)", 0.65, 140, "BSG", "curia"),
    "rome.lapis_niger": ("Lapis Niger", 0.65, 6, "B", "lapis_niger"),
    "rome.aemilia": ("Basilica Aemilia", 0.65, 130, "BS", "aemilia"),
    "rome.forum_square": ("Forum square", 0.65, 30, "B", "forum_square"),
    "rome.julia": ("Basilica Iulia", 0.65, 130, "BS", "julia"),
    "rome.castor": ("Temple of Castor and Pollux", 0.65, 160, "BS", "castor"),
    "rome.lacus_iuturnae": ("Spring of Juturna", 0.65, 20, "B", "lacus_iuturnae"),
    "rome.divus_julius": ("Temple of Divus Iulius", 0.65, 115, "BS", "divus_julius"),
    "rome.regia": ("Regia", 0.65, 50, "BS", "regia"),
    "rome.vesta": ("Temple of Vesta", 0.85, 100, "BSG", "vesta"),
    "rome.vestals": ("House of the Vestals", 0.65, 70, "BSG", "vestals"),
    "rome.piperataria": ("Horrea Piperataria", 0.65, 70, "BS", "piperataria"),
}
