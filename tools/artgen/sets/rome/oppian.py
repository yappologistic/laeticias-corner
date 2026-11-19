"""The Baths of Trajan on the Oppian (dedicated AD 109; rome.md §3.2), at s = 0.35: the first of
the great imperial baths, a huge symmetrical bath block set in a walled precinct with gardens.
The real complex is turned about 36 degrees to face the afternoon sun to the south-west; here
its axis runs north-south on the grid with the caldarium to the south (toward the camera).
Grid axes: +x south, +y west."""

import math

import numpy as np

import materials as M
import roman as RM
from arch import carve, face_box, face_length, fill, halo, slab
from setbuild import Landmark
from sets.rome.common import LAMP, PORTICO, S35, T, GODDESS, lawn, paving, plane_tree, referrer
from voxel import value_noise

ref = referrer("sets.rome.oppian")
S = S35
N = 30 * T
AX = N / 2                       # the axis (y)
H_BLOCK = S.v(18.0)
H_ROOM = S.v(13.0)
H_WALL = S.v(9.0)


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def _hall(m, box, h, seed, roof="vault", axis="y", windows=("+x", "+y"), win_h=None):
    """A brick-faced concrete hall with tall arched glass windows and a vaulted or flat roof."""
    RM.wall(m, box, 0.0, h, "brick", seed)
    for face in windows:
        L = face_length(face, *box)
        n = max(1, int(L // 14))
        for i in range(n):
            s0 = (i + 0.5) * L / n - 2.5
            RM.window(m, face, box, s0, 5.0, h * 0.42, win_h or h * 0.4, arched=True, glass=True)
    RM.cornice(m, box, h, 1.2, 0.6)
    if roof == "vault":
        RM.vault_roof(m, box, h + 1.2, axis, "whitewash", tiles=True, seed=seed)
    elif roof == "groin":
        RM.groin_roof(m, box, h + 1.2, "whitewash", seed=seed)
    else:
        fill(m, (box[0] + 0.5, box[1] - 0.5, box[2] + 0.5, box[3] - 0.5, h, h + 1.2), "whitewash",
             tone=lambda X, Y, Z: (value_noise(X, Y, Z, 6.0, seed) - 0.5) * 0.4)


def _court(m, box, seed, sand=True):
    """An open court cut through the block: sand for exercise or a paved floor."""
    x0, x1, y0, y1 = box
    carve(m, (x0, x1, y0, y1, 0.8, H_BLOCK + 40.0))
    fill(m, (x0, x1, y0, y1, 0.0, 0.8), "poros" if sand else "travertine",
         tone=(lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, seed) - 0.5) * 0.6) if sand else M.paving(5.0, 4.0, seed))


def trajan_baths(m):
    """Apollodorus's baths for Trajan: in the middle of the block, on the axis, the open
    swimming pool (natatio) at the north, the frigidarium under three great cross vaults, the
    tepidarium and the caldarium projecting south with its apse and walls of glass; a
    palaestra court with a colonnade either side; halls, changing rooms and service rooms
    round them under vaults and flat roofs, the furnace flues smoking; then gardens with plane
    trees in front, and the walled precinct with its two side exedrae (libraries) and the
    great south exedra with its tiers of seats."""
    seed = 361
    # The precinct: gardens on lawns, gravel walks, the enclosure wall with gates west and east.
    fill(m, (0.0, N, 0.0, N, 0.0, 0.8), "grass", tone=lawn(seed))
    paving(m, (300.0, 440.0, AX - 8.0, AX + 8.0), 0.0, 0.9, "travertine", 5.0, 4.0, seed + 1)
    paving(m, (322.0, 334.0, 14.0, N - 14.0), 0.0, 0.9, "travertine", 5.0, 4.0, seed + 2)
    for (box) in ((6.0, 470.0, 12.0, 18.0), (6.0, 470.0, N - 18.0, N - 12.0), (6.0, 12.0, 12.0, N - 12.0),
                  (464.0, 470.0, 12.0, N - 12.0)):
        RM.wall(m, box, 0.0, H_WALL, "stucco", seed + 3, material="whitewash")
    carve(m, (320.0, 336.0, 0.0, 20.0, 0.0, H_WALL + 2.0))
    carve(m, (320.0, 336.0, N - 20.0, N, 0.0, H_WALL + 2.0))
    for x in (318.0, 336.0):
        for y in (11.0, N - 19.0):
            slab(m, x, x + 2.0, y, y + 8.0, 0.0, H_WALL + 3.0, "travertine", tone=RM.travertine(seed=seed + 4))
    # The side exedrae (libraries) bulging into the precinct from the long walls: curved walls
    # with tall niches for the book presses, open to the garden.
    for yc, sg in ((18.0, 1), (N - 18.0, -1)):
        cx, R = 200.0, 46.0

        def ex(X, Y, Z, yc=yc, sg=sg):
            r = np.hypot(X - cx, Y - yc)
            return (r < R) & (r > R - 5.0) & ((Y - yc) * sg > 0)
        fill(m, (cx - R, cx + R, min(yc, yc + sg * R), max(yc, yc + sg * R), 0.0, H_ROOM), "brick", ex,
             tone=RM.brick(seed + 5))
        for kk in range(7):
            a = (kk + 0.5) * math.pi / 7
            nx, ny = cx - R * math.cos(a) * 0.95, yc + sg * (R - 3.0) * math.sin(a)
            carve(m, (nx - 1.8, nx + 1.8, ny - 1.8, ny + 1.8, 2.0, H_ROOM * 0.75))
        fill(m, (cx - R - 1, cx + R + 1, min(yc, yc + sg * R) - 1, max(yc, yc + sg * R) + 1, H_ROOM, H_ROOM + 1.2),
             "travertine", lambda X, Y, Z, yc=yc, sg=sg: (np.abs(np.hypot(X - cx, Y - yc) - (R - 2.5)) < 3.2) &
             ((Y - yc) * sg > 0), tone=0.3)
    # The great south exedra with tiers of seats facing the garden.
    sxc, SR = 470.0, 60.0
    def seats(X, Y, Z):
        r = np.hypot(X - sxc, Y - AX)
        return (r < SR) & (r > SR - 22.0) & (X < sxc) & (Z < (r - (SR - 22.0)) * 0.7 + 1.0)
    fill(m, (sxc - SR, sxc, AX - SR, AX + SR, 0.0, 20.0), "marble", seats,
         tone=lambda X, Y, Z: 0.4 * ((Z % 1.4) > 0.9) - 0.3 * ((Z % 1.4) < 0.4))
    fill(m, (sxc - SR - 1, sxc, AX - SR - 1, AX + SR + 1, 0.0, H_ROOM), "brick",
         lambda X, Y, Z: (np.abs(np.hypot(X - sxc, Y - AX) - SR) < 2.5) & (X < sxc), tone=RM.brick(seed + 6))
    # Plane trees along the precinct walls and the block's front.
    for x in np.arange(310.0, 450.0, 22.0):
        if 300.0 < x < 356.0:              # the gates' walks stay clear
            continue
        for y in (34.0, N - 34.0):
            plane_tree(m, x, y, 0.8, h=30.0, seed=int(x + y))
    for y in np.arange(34.0, N - 30.0, 30.0):
        if abs(y - AX) > 20.0:
            plane_tree(m, 289.0, y, 0.8, h=26.0, seed=int(y) + 7)
    # The block: a ring of halls and rooms under flat roofs, then the courts and the axis halls.
    bx0, bx1, by0, by1 = 24.0, 286.0, 70.0, N - 70.0
    RM.wall(m, (bx0, bx1, by0, by1), 0.0, H_ROOM, "brick", seed + 7)
    for face in ("+x", "+y"):
        L = face_length(face, bx0, bx1, by0, by1)
        for s0 in np.arange(8.0, L - 8.0, 12.0):
            RM.window(m, face, (bx0, bx1, by0, by1), s0, 4.0, H_ROOM * 0.45, H_ROOM * 0.35, arched=True, glass=True)
    for face in ("+x", "+y", "-x", "-y"):
        Lf = face_length(face, bx0, bx1, by0, by1)
        fill(m, face_box(face, bx0, bx1, by0, by1, H_ROOM - 1.2, H_ROOM, 0.0, Lf, -0.6, 1.0), "travertine", tone=0.3)
    # The rooms round the block under tiled roofs in bays, each bay's ridge across the range.
    def tiles_roof(X, Y, Z):
        u = (X + Y) % 24.0
        return Z < H_ROOM + 3.5 - np.abs(u - 12.0) * 0.28
    fill(m, (bx0 + 0.5, bx1 - 0.5, by0 + 0.5, by1 - 0.5, H_ROOM, H_ROOM + 4.0), "terracotta", tiles_roof,
         tone=lambda X, Y, Z: 0.3 * (((X - Y) % 2.2) < 0.7) - 0.25 * (np.abs(((X + Y) % 24.0) - 12.0) < 0.6))
    # The palaestrae: open sanded courts with colonnades on three sides.
    for (y0, y1, front) in ((by0 + 12.0, by0 + 92.0, "-y"), (by1 - 92.0, by1 - 12.0, "+y")):
        _court(m, (100.0, 250.0, y0, y1), seed + 8)
        yc = y1 - 6.0 if front == "-y" else y0 + 6.0
        RM.colonnade(m, (106.0, yc), (244.0, yc), 0.0, 14, PORTICO, S, 8.0, front, seed=seed + 9)
    # The natatio: an open pool at the north end of the axis, behind a columned screen.
    _court(m, (bx0 + 6.0, 96.0, AX - 74.0, AX + 74.0), seed + 10, sand=False)
    fill(m, (bx0 + 12.0, 92.0, AX - 68.0, AX + 68.0, 0.0, 0.9), "water", tone=0.1)
    RM.colonnade(m, (94.0, AX - 66.0), (94.0, AX + 66.0), 0.0, 12, PORTICO, S, 0.5, "-x", back=False, seed=seed + 11)
    # The frigidarium: three cross-vaulted bays along y, the highest roofs of the baths.
    fx0, fx1 = 100.0, 166.0
    for i in range(3):
        y0 = AX - 75.0 + i * 50.0
        box = (fx0, fx1, y0, y0 + 50.0)
        RM.wall(m, box, 0.0, H_BLOCK, "brick", seed + 12)
        for face in ("+y", "+x"):
            L = face_length(face, *box)
            RM.window(m, face, box, L / 2 - 8.0, 16.0, H_BLOCK * 0.55, H_BLOCK * 0.38, arched=True, glass=True)
        RM.groin_roof(m, box, H_BLOCK, "whitewash", seed=seed + 13 + i)
    RM.cornice(m, (fx0, fx1, AX - 75.0, AX + 75.0), H_BLOCK, 1.4, 0.7)
    # The tepidarium and the caldarium with its apse, projecting south.
    _hall(m, (166.0, 196.0, AX - 30.0, AX + 30.0), H_BLOCK - 6.0, seed + 16, roof="vault", axis="x")
    cb = (196.0, 286.0, AX - 50.0, AX + 50.0)
    _hall(m, cb, H_BLOCK - 2.0, seed + 17, roof="vault", axis="x", win_h=H_BLOCK * 0.5)
    acx, ar = 286.0, 30.0
    def apse(X, Y, Z):
        return (np.hypot(X - acx, Y - AX) < ar) & (X >= acx)
    fill(m, (acx, acx + ar, AX - ar, AX + ar, 0.0, H_BLOCK - 2.0), "brick", apse, tone=RM.brick(seed + 18))
    for k in range(5):
        a = -math.pi / 2 + (k + 0.5) * math.pi / 5
        RM.window(m, "+x", (acx, acx + ar * math.cos(a) + 0.5, AX - ar, AX + ar), (ar - ar * math.sin(a)) - 3.0, 6.0,
                  H_BLOCK * 0.4, H_BLOCK * 0.45, arched=True, glass=True)
    fill(m, (acx, acx + ar, AX - ar, AX + ar, H_BLOCK - 2.0, H_BLOCK - 2.0 + ar), "whitewash",
         lambda X, Y, Z: (X >= acx) & (np.hypot(np.hypot(X - acx, Y - AX), Z - (H_BLOCK - 2.0)) < ar) &
         (np.hypot(np.hypot(X - acx, Y - AX), Z - (H_BLOCK - 2.0)) > ar - 2.0),
         tone=lambda X, Y, Z: 0.3 * ((np.arctan2(Y - AX, X - acx) * 10) % 1.0 < 0.2) - 0.1)
    # Furnace flues either side of the caldarium; warm light in its windows.
    for y in (AX - 46.0, AX + 46.0):
        slab(m, 278.0, 284.0, y - 3.0, y + 3.0, 0.0, H_BLOCK + 8.0, "brick", tone=RM.brick(seed + 19))
        fill(m, (279.0, 283.0, y - 2.0, y + 2.0, H_BLOCK + 6.0, H_BLOCK + 8.0), "ink")
    for y in (AX - 30.0, AX, AX + 30.0):
        halo(m, 240.0, y, H_BLOCK * 0.6, 14.0, LAMP, 0.5)
    # Statues along the garden walk.
    for x in (330.0, 370.0, 410.0):
        for y in (AX - 14.0, AX + 14.0):
            RM.statue(m, x, y, 0.9, 9.0, GODDESS, material="marble", keep=(), base=(3.0, 3.0))


def _baths_landmark():
    # The lawns either side of the statue walk (dy 13..16 holds the paving and the statues),
    # each joined to its gate and to each other across the paving between the statues (dx 20,
    # 23 and 25 hold them), so either gate reaches the whole garden (draw-order audit V-W3).
    walk = sorted(set(tiles(19, 24, 3, 12) + tiles(19, 24, 17, 26) + [(20, y) for y in range(0, 3)] +
                      [(20, y) for y in range(27, 30)] + tiles(21, 22, 13, 16) + tiles(24, 24, 13, 16)))
    return Landmark((30, 30), (0, 104), ref("trajan_baths"), walk=walk,
                    slots={"bathe": [{"t": [19, 12], "face": "-x"}, {"t": [19, 17], "face": "-x"}],
                           "stroll": [{"t": [21, 8]}, {"t": [23, 20]}, {"t": [22, 11]}],
                           "exercise": [{"t": [20, 5]}, {"t": [20, 24]}]},
                    emitters={"steam_e": (281.0, AX - 46.0, H_BLOCK + 9.0), "steam_w": (281.0, AX + 46.0, H_BLOCK + 9.0)},
                    district=31)


LANDMARKS = {"rome.trajan_baths": _baths_landmark()}
INFO = {"rome.trajan_baths": ("Baths of Trajan", 0.35, 170, "BSG", "trajan_baths")}
