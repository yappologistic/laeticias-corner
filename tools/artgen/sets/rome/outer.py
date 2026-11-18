"""Rome beyond the old centre (rome.md §2.3 D7, D11, D15, D17-D18, §3.2): the Baths of Trajan
on the Oppian at s = 0.35, the Castra Praetoria at s = 0.4, the suburban villa with its
vineyard on the Via Appia and the synagogue of a Transtiberim community; and as kit (rotatable,
placed along routes): the Aqua Claudia arcade as a joined item, the tombs of the Via Appia."""

import math

import numpy as np

import roman as RM
from arch import carve, fill, revolve, rod, slab
from setbuild import Landmark
from sets.rome.common import S35, S4, S65, T, box_hedge, cypress, lamp, paving, plane_tree, referrer, stone_pine, torch
from voxel import value_noise

ref = referrer("sets.rome.outer")


def trajan_baths(m):
    """The Baths of Trajan (109) by Apollodorus at s = 0.35: the first of the great imperial
    baths, a vast symmetrical block in an enclosure with exedrae, gardens between; on the
    central axis the open swimming pool (natatio), the great cross-vaulted cold hall
    (frigidarium), the tepidarium and the caldarium with its windows to the south-west sun,
    palaestras with colonnades to each side; furnace flues smoking."""
    S = S35
    W, D = 30 * T, 30 * T
    # The enclosure wall with its exedrae and the garden.
    RM.wall(m, (2.0, 8.0, 2.0, W - 2.0), 0.0, S.v(14.0), "brick", 701)
    RM.wall(m, (2.0, D - 2.0, 2.0, 8.0), 0.0, S.v(14.0), "brick", 702)
    RM.wall(m, (2.0, D - 2.0, W - 8.0, W - 2.0), 0.0, S.v(14.0), "brick", 703)
    for yc in (6 * T, W - 6 * T):
        el = RM.Ellipse(D - 4 * T, yc, 3 * T, 3 * T)
        RM.ring_facade(m, el, 0.0, [RM.Storey(S.v(14.0), "windows", "tuscan", material="brick")], 20, 6.0, S,
                       arc=(-math.pi / 2, math.pi / 2), seed=704)
    fill(m, (8.0, D - 2.0, 8.0, W - 8.0, 0.0, 0.8), "grass", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 4.0, 705) -
                                                                                     0.5) * 0.8)
    for i in range(8):
        plane_tree(m, 26.0 + i * 50.0, 30.0, 0.8, 30.0, seed=i)
        plane_tree(m, 26.0 + i * 50.0, W - 30.0, 0.8, 30.0, seed=i + 9)
    # The bath block.
    bx0, bx1, by0, by1 = 4 * T, 22 * T, 5 * T, W - 5 * T
    RM.wall(m, (bx0, bx1, by0, by1), 0.0, S.v(20.0), "brick", 706)
    cy = W / 2
    # Natatio (north), open to the sky.
    carve(m, (bx0 + 6.0, bx0 + 4 * T, cy - 6 * T, cy + 6 * T, 1.0, S.v(20.0) + 1.0))
    fill(m, (bx0 + 6.0, bx0 + 4 * T, cy - 6 * T, cy + 6 * T, 0.0, 1.5), "water",
         tone=lambda X, Y, Z: 0.3 * (np.sin((X + Y) * 1.2) > 0.85))
    # Frigidarium: three groin-vaulted bays rising above the block.
    for i in range(3):
        y0 = cy - 5 * T + i * (10 * T / 3)
        RM.wall(m, (bx0 + 4 * T + 4.0, bx0 + 9 * T, y0, y0 + 10 * T / 3), 0.0, S.v(30.0), "brick", 707 + i)
        RM.groin_roof(m, (bx0 + 4 * T + 4.0, bx0 + 9 * T, y0, y0 + 10 * T / 3), S.v(30.0), "whitewash", seed=710 + i)
        RM.window(m, "+y", (bx0 + 4 * T + 4.0, bx0 + 9 * T, y0, y0 + 10 * T / 3), 10.0, 30.0, S.v(22.0), S.v(5.0),
                  arched=True, glass=True)
    # Tepidarium and caldarium: a domed hall and a great apsed hall with big windows to the south.
    tx = bx0 + 11 * T
    revolve(m, tx, cy, 0.0, S.v(24.0), lambda t: 2.4 * T, "brick", tone=RM.brick(713))
    RM.dome(m, tx, cy, S.v(24.0), 2.4 * T - 1.0, "whitewash", rise=2.0 * T, thick=4.0, oculus=6.0, tiles=False,
            coffers=False, seed=714)
    cb = (bx0 + 13.5 * T, bx1, cy - 5 * T, cy + 5 * T)
    RM.wall(m, cb, 0.0, S.v(28.0), "brick", 715)
    for s0 in np.arange(12.0, cb[3] - cb[2] - 30.0, 36.0):
        RM.window(m, "+x", cb, s0, 24.0, S.v(8.0), S.v(14.0), arched=True, glass=True, lit=0.3)
    RM.vault_roof(m, cb, S.v(28.0), "y", "whitewash", tiles=False, seed=716)
    # Palaestras with colonnades in the wings.
    for y0, y1, front in ((by0 + 8.0, by0 + 6 * T, "+y"), (by1 - 6 * T, by1 - 8.0, "-y")):
        carve(m, (bx0 + 6 * T, bx0 + 13 * T, y0, y1, 1.0, S.v(20.0) + 1.0))
        fill(m, (bx0 + 6 * T, bx0 + 13 * T, y0, y1, 0.0, 1.0), "poros", tone=0.0)
        yy = y0 + 6.0 if front == "+y" else y1 - 6.0
        RM.colonnade(m, (bx0 + 6 * T + 6.0, yy), (bx0 + 13 * T - 6.0, yy), 0.0, 12,
                     RM.ROrder("corinthian", D=1.0, H=9.0, shaft="granite", fluted=False), S, 8.0,
                     "-y" if front == "+y" else "+y", seed=int(y0))
    RM.lean_to(m, (bx0 - 1, bx1 + 1, by0 - 1, by0 + 5 * T), S.v(20.0), S.v(22.0), "-y", "terracotta", 717)
    RM.lean_to(m, (bx0 - 1, bx1 + 1, by1 - 5 * T, by1 + 1), S.v(20.0), S.v(22.0), "+y", "terracotta", 718)
    for x, y in ((bx1 - 6.0, by0 + 10.0), (bx1 - 6.0, by1 - 10.0), (bx1 - 30.0, cy)):
        slab(m, x - 2.0, x + 2.0, y - 2.0, y + 2.0, 0.0, S.v(32.0), "brick", tone=RM.brick(719))


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
    "rome.trajan_baths": Landmark((30, 30), (0, 104), ref("trajan_baths"), district=8,
                                  emitters={"steam_n": (5 * T, 6 * T, 70.0), "steam_s": (21 * T, 24 * T, 70.0)}),
    "rome.castra_praetoria": Landmark((15, 18), (0, 48), ref("castra_praetoria"), district=8,
                                      slots={"guard": [{"t": [15, 8], "face": "+x"}, {"t": [15, 10], "face": "+x"}],
                                             "drill": [{"t": [16, 7]}, {"t": [16, 9]}, {"t": [17, 8]}]}),
    "rome.suburban_villa": Landmark((15, 17), (0, 56), ref("suburban_villa"), district=8,
                                    slots={"work": [{"t": [8, -1], "face": "+y"}]}),
    "rome.synagogue": Landmark((4, 5), (0, 40), ref("synagogue"), district=8,
                               slots={"door": [{"t": [4, 1], "face": "+x"}]}),
}

INFO = {
    "rome.trajan_baths": ("Baths of Trajan", 0.35, 110, "BSG", "trajan_baths"),
    "rome.castra_praetoria": ("Castra Praetoria", 0.4, 70, "BSG", "castra_praetoria"),
    "rome.suburban_villa": ("Suburban villa with vineyard", 0.65, 70, "BSG", "suburban_villa"),
    "rome.synagogue": ("Synagogue of Transtiberim", 0.65, 60, "BSG", "synagogue"),
}
