"""Rome beyond the old centre (rome.md §2.3 D11, D15, D17-D18, §3.2): the Castra Praetoria at
s = 0.4, the suburban villa with its
vineyard on the Via Appia and the synagogue of a Transtiberim community; and as kit (rotatable,
placed along routes): the Aqua Claudia arcade as a joined item, the tombs of the Via Appia."""


import numpy as np

import roman as RM
from arch import carve, fill, rod, slab
from setbuild import Landmark
from sets.rome.common import S4, S65, T, box_hedge, cypress, lamp, paving, referrer, stone_pine, torch
from voxel import value_noise

ref = referrer("sets.rome.outer")


def castra_praetoria(m):
    """The Castra Praetoria at s = 0.4: the Praetorian Guard's camp, a rectangle of brick walls
    with crenellations, towers along them and a gate in the middle of each side; inside, rows
    of barracks with tiled roofs, the headquarters (principia) with its shrine of the standards
    and a parade ground."""
    S = S4
    W, D = 18 * T, 15 * T
    H = S.v(8.0)
    for wb in ((2.0, 7.0, 2.0, W - 2.0), (D - 7.0, D - 2.0, 2.0, W - 2.0), (2.0, D - 2.0, 2.0, 7.0),
               (2.0, D - 2.0, W - 7.0, W - 2.0)):
        RM.wall(m, wb, 0.0, H, "brick", 721)
        fill(m, (*wb, H, H + 2.6), "brick", lambda X, Y, Z: (((X + Y) % 5.0) < 2.6), tone=RM.brick(722))
    for x in np.linspace(2.0, D - 2.0, 6):
        for y in np.linspace(2.0, W - 2.0, 7):
            on_edge = x in (2.0, D - 2.0) or y in (2.0, W - 2.0)
            if on_edge:
                RM.wall(m, (max(0.0, x - 6.0), min(D, x + 6.0), max(0.0, y - 6.0), min(W, y + 6.0)), 0.0, H + 6.0,
                        "brick", 723)
                RM.hip(m, (max(0.0, x - 6.5), min(D, x + 6.5), max(0.0, y - 6.5), min(W, y + 6.5)), H + 6.0, 3.0,
                       seed=724)
    for face, wb, s0 in (("+x", (D - 7.0, D - 2.0, 2.0, W - 2.0), W / 2 - 8.0), ("+y", (2.0, D - 2.0, W - 7.0, W - 2.0),
                                                                                 D / 2 - 8.0)):
        RM.opening(m, face, wb, s0, 12.0, 0.0, 9.0, 6.0, frame="travertine")
        torch(m, *RM.face_point(face, wb, s0 - 2.0, -1.0), 0.0, 6.0, 0.7)
        torch(m, *RM.face_point(face, wb, s0 + 14.0, -1.0), 0.0, 6.0, 0.7)
    fill(m, (7.0, D - 7.0, 7.0, W - 7.0, 0.0, 0.6), "poros", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 725) -
                                                                                    0.5) * 0.4)
    for i in range(7):     # barracks rows
        x0 = 14.0 + i * 26.0
        if 5 * T < x0 < 9 * T:
            continue
        for y0, y1 in ((14.0, 7 * T), (11 * T, W - 14.0)):
            RM.wall(m, (x0, x0 + 12.0, y0, y1), 0.0, 9.0, "stucco", 726, "whitewash")
            RM.gable(m, (x0 - 1.0, x0 + 13.0, y0 - 1.0, y1 + 1.0), 9.0, 4.0, "y", seed=727 + i)
            for s0 in np.arange(4.0, y1 - y0 - 4.0, 8.0):
                RM.window(m, "+x", (x0, x0 + 12.0, y0, y1), s0, 2.0, 2.0, 5.0, lit=0.25)
    pb = (6 * T, 9 * T, 7.5 * T, 10.5 * T)
    RM.wall(m, pb, 0.0, S.v(12.0), "veneer", 728, "marble")
    RM.gable(m, (pb[0] - 1, pb[1] + 1, pb[2] - 1, pb[3] + 1), S.v(12.0), 8.0, "x", seed=729)
    for y in np.linspace(pb[2] + 4.0, pb[3] - 4.0, 4):
        RM.column(m, pb[1] + 4.0, y, 0.0, RM.ROrder("corinthian", D=0.8, H=8.0), S)


def suburban_villa(m):
    """A suburban villa on the Via Appia: the owner's house round an atrium and a peristyle
    garden with a pool and statues, the farm wing with its wine press and storage jars, a
    vineyard on trellises, an orchard, umbrella pines and cypresses along the drive."""
    S = S65
    W, D = 17 * T, 15 * T
    hb = (2.0, 6 * T, 2.0, 8 * T)
    RM.wall(m, hb, 0.0, S.v(7.0), "stucco", 731, "whitewash")
    carve(m, (2 * T, 4 * T, 2 * T, 6 * T, 1.0, S.v(7.0) + 1.0))
    fill(m, (2 * T, 4 * T, 2 * T, 6 * T, 0.0, 1.0), "grass", tone=0.0)
    fill(m, (2.6 * T, 3.4 * T, 3.4 * T, 4.6 * T, 0.0, 1.5), "water", tone=0.2)
    box_hedge(m, 2 * T + 3, 4 * T - 3, 2 * T + 3, 2 * T + 6, 1.0)
    for x in np.linspace(2 * T + 3, 4 * T - 3, 4):
        for y in (2 * T + 2, 6 * T - 2):
            RM.column(m, x, y, 0.0, RM.ROrder("tuscan", D=0.4, H=3.5, shaft="whitewash", trim="whitewash",
                                              fluted=False), S)
    RM.hip(m, (hb[0] - 1, hb[1] + 1, hb[2] - 1, hb[3] + 1), S.v(7.0), 6.0, seed=732)
    carve(m, (2 * T, 4 * T, 2 * T, 6 * T, S.v(7.0) - 1.0, S.v(7.0) + 7.0))
    for s0 in np.arange(6.0, 8 * T - 10.0, 14.0):
        RM.window(m, "+x", hb, s0, 3.0, 8.0, 5.0, shutter="wood", lit=0.35)
    fb = (2.0, 4 * T, 9 * T, 14 * T)
    RM.wall(m, fb, 0.0, S.v(5.0), "brick", 733)
    RM.gable(m, (fb[0] - 1, fb[1] + 1, fb[2] - 1, fb[3] + 1), S.v(5.0), 6.0, "y", seed=734)
    from sets.rome.ground import amphora
    for i in range(8):
        amphora(m, 4 * T + 4.0, 9 * T + 4.0 + i * 5.0, 0.0, "wine")
    for row in range(7):          # vine rows on trellises
        x = 7 * T + row * 16.0
        for y in np.arange(2 * T, W - 2 * T, 8.0):
            rod(m, (x, y, 0.0), (x, y, 8.0), 0.3, "wood")
        rod(m, (x, 2 * T, 8.0), (x, W - 2 * T, 8.0), 0.25, "wood")
        from models.nature import leaf_mass
        leaf_mass(m, [(x, y, 8.0, 2.6) for y in np.arange(2 * T + 4, W - 2 * T, 12.0)], 735 + row,
                  materials=(("leaf", 0.7), ("grass", 0.3)), under="leaf_dark", squash=0.6)
    for i in range(5):
        stone_pine(m, D - 8.0, 20.0 + i * 50.0, 0.0, 40.0, seed=i)
    for i in range(4):
        cypress(m, 6 * T + 4.0, 10.0 + i * 16.0, 0.0, h=30.0, seed=i)


def synagogue(m):
    """A synagogue of a Transtiberim community (its form is not known archaeologically): a
    modest house-like building of brick with a courtyard and a basin for washing, a tiled
    roof, a lamp at the door."""
    S = S65
    W, D = 5 * T, 4 * T
    hb = (2.0, D - 2.0, 2.0, 3 * T)
    RM.wall(m, hb, 0.0, S.v(8.0), "brick", 741)
    RM.gable(m, (hb[0] - 1, hb[1] + 1, hb[2] - 1, hb[3] + 1), S.v(8.0), 7.0, "y", seed=742)
    for s0 in (6.0, 18.0, 30.0):
        RM.window(m, "+x", hb, s0, 3.0, 9.0, 5.0, arched=True, lit=0.4)
    RM.wall(m, (2.0, D - 2.0, 3 * T, W - 2.0), 0.0, 6.0, "stucco", 743, "whitewash")
    carve(m, (6.0, D - 6.0, 3 * T, W - 6.0, 0.5, 7.0))
    paving(m, (6.0, D - 6.0, 3 * T, W - 6.0), 0.0, 0.5, "brick", 3.0, 3.0, 744)
    slab(m, D / 2 - 4.0, D / 2 + 4.0, 3.6 * T, 3.6 * T + 6.0, 0.0, 2.2, "marble", tone=0.2)
    fill(m, (D / 2 - 3.0, D / 2 + 3.0, 3.6 * T + 1.0, 3.6 * T + 5.0, 1.0, 2.0), "water", tone=0.2)
    lamp(m, D - 1.0, 3 * T - 4.0, 9.0, 0.6)


LANDMARKS = {
    "rome.castra_praetoria": Landmark((15, 18), (0, 48), ref("castra_praetoria"), district=8,
                                      slots={"guard": [{"t": [15, 8], "face": "+x"}, {"t": [15, 10], "face": "+x"}],
                                             "drill": [{"t": [16, 7]}, {"t": [16, 9]}, {"t": [17, 8]}]}),
    "rome.suburban_villa": Landmark((15, 17), (0, 56), ref("suburban_villa"), district=8,
                                    slots={"work": [{"t": [8, -1], "face": "+y"}]}),
    "rome.synagogue": Landmark((4, 5), (0, 40), ref("synagogue"), district=8,
                               slots={"door": [{"t": [4, 1], "face": "+x"}]}),
}

INFO = {
    "rome.castra_praetoria": ("Castra Praetoria", 0.4, 70, "BSG", "castra_praetoria"),
    "rome.suburban_villa": ("Suburban villa with vineyard", 0.65, 70, "BSG", "suburban_villa"),
    "rome.synagogue": ("Synagogue of Transtiberim", 0.65, 60, "BSG", "synagogue"),
}
