"""The Tiber and its port (rome.md §2.3 D12-D13, D16, §3.2): Tiber Island shaped like a ship
with the Temple of Aesculapius and its obelisk mast, the stone bridges Fabricius, Cestius and
Aemilius and the wooden Sublicius, the Forum Boarium's temples of Portunus and of Hercules
Victor and the Ara Maxima, the Emporium wharf and the Porticus Aemilia warehouse, the Horrea
Galbana and Monte Testaccio.

Bridges are three tiles wide: the deck is the middle row of walk tiles with its floor height
(`walk_z`), the outer rows carry the parapets and cutwaters, so the parapets never stand on a
walk tile (rome.md gives two rows; noted in the report)."""

import math

import numpy as np

import materials as M
import roman as RM
from arch import carve, ellipsoid, fill, revolve, rod, slab
from setbuild import Landmark
from sets.rome.common import S65, T, cypress, lamp, paving, referrer, tc, treadwheel_crane
from sets.rome.ground import amphora
from voxel import hash01, value_noise

ref = referrer("sets.rome.river")
S = S65
DECK = 9.0           # deck floor above the water at the abutments, design units (18 px)


def _deck_z(n, hump=3.0):
    """Floor height of each deck tile: rising gently to the middle of the bridge."""
    return [DECK + hump * math.sin(math.pi * (i + 0.5) / n) for i in range(n)]


def stone_bridge(m, n, arches, material="travertine", seed=0, voussoir="tufa"):
    """A stone bridge along y over `n` tiles: piers with pointed cutwaters on both sides, round
    arches (`arches`: [(y0, y1)] spans), travertine and tufa facing, little relieving arches in
    the piers, a paved deck in the middle row, parapets on the outer rows."""
    L = n * T

    def deck_top(Y):
        f = np.clip(Y / L, 0, 1)
        return DECK + 3.0 * np.sin(np.pi * f)
    x0, x1 = T - 2.0, 2 * T + 2.0
    fill(m, (x0, x1, 0.0, L, -4.0, DECK + 3.0), material, lambda X, Y, Z: Z < deck_top(Y) - 0.8,
         tone=M.ashlar(2.4, 6.0, seed, spread=0.4))
    for (a0, a1) in arches:
        spring = 0.5
        carve(m, (x0 - 1, x1 + 1, a0, a1, -4.0, DECK),
              lambda X, Y, Z, a0=a0, a1=a1: RM.arch_mask(Y, Z, a0, a1 - a0, -4.0, spring))
        fill(m, (x0, x1, a0 - 1.6, a1 + 1.6, spring, DECK + 2.0), voussoir,
             lambda X, Y, Z, a0=a0, a1=a1: (Z >= spring) & (np.hypot(Y - (a0 + a1) / 2, Z - spring) >= (a1 - a0) / 2) &
             (np.hypot(Y - (a0 + a1) / 2, Z - spring) < (a1 - a0) / 2 + 1.6) & ((X < x0 + 1.0) | (X > x1 - 1.0)),
             tone=lambda X, Y, Z, a0=a0, a1=a1: 0.3 - 0.8 * (((np.arctan2(Z - spring, Y - (a0 + a1) / 2) * 6 / np.pi) %
                                                               1.0) < 0.15), only_solid=True)
    piers = sorted({round(a, 2) for (a0, a1) in arches for a in (a0, a1)})
    for i in range(0, len(piers) - 1):
        if any(abs(piers[i] - a1) < 0.1 for (_a0, a1) in arches) and any(abs(piers[i + 1] - a0) < 0.1
                                                                            for (a0, _a1) in arches):
            yc = (piers[i] + piers[i + 1]) / 2
            w = (piers[i + 1] - piers[i]) / 2
            for xs, sgn in ((x0, -1), (x1, 1)):     # cutwaters
                fill(m, (xs - 7.0, xs + 7.0, yc - w, yc + w, -4.0, DECK - 1.0), material,
                     lambda X, Y, Z, xs=xs, sgn=sgn, yc=yc, w=w: ((X - xs) * sgn >= 0) &
                     ((X - xs) * sgn < 6.0 * (1 - np.abs(Y - yc) / w)), tone=0.1)
            RM.opening(m, "+x", (x0, x1, yc - w, yc + w), 2.0 * w * 0.3, 2.0 * w * 0.4, 1.0, 4.0, 1.5)
    # Deck paving and parapets (just outside the walk row).
    fill(m, (T, 2 * T, 0.0, L, DECK - 1.0, DECK + 3.2), "basalt",
         lambda X, Y, Z: (Z < deck_top(Y)) & (Z >= deck_top(Y) - 1.0),
         tone=lambda X, Y, Z: (hash01(np.floor(X / 2.4).astype(np.int64), np.floor(Y / 2.4).astype(np.int64), seed)
                               - 0.5) * 0.8)
    for xp in (T - 2.0, 2 * T):
        fill(m, (xp, xp + 2.0, 0.0, L, DECK - 1.0, DECK + 7.0), material,
             lambda X, Y, Z: (Z < deck_top(Y) + 3.6) & (Z >= deck_top(Y) - 1.0),
             tone=lambda X, Y, Z: 0.3 * (Z > deck_top(Y) + 3.0) - 0.05)


def pons_fabricius(m):
    """The Pons Fabricius (62 BC) from the Campus to the island: two great arches of tufa faced
    in travertine and brick, a small arch through the central pier for floodwater."""
    stone_bridge(m, 4, [(4.0, 30.0), (34.0, 60.0)], seed=601)


def pons_cestius(m):
    """The Pons Cestius from the island to Transtiberim: one great arch and two small ones."""
    stone_bridge(m, 4, [(2.0, 14.0), (17.0, 47.0), (50.0, 62.0)], seed=602)


def pons_aemilius(m):
    """The Pons Aemilius, the first stone bridge (rebuilt under Augustus): six arches."""
    stone_bridge(m, 10, [(4.0 + i * 26.0, 24.0 + i * 26.0) for i in range(6)], seed=603)


def pons_sublicius(m):
    """The Pons Sublicius, the sacred wooden bridge on timber piles: no iron allowed in it."""
    L = 10 * T
    for y in np.arange(6.0, L - 4.0, 12.0):
        for x in (T - 1.0, T + 6.0, 2 * T - 6.0, 2 * T + 1.0):
            rod(m, (x, y, -4.0), (x, y, DECK - 1.0), 0.9, "wood", tone=0.1)
        rod(m, (T - 3.0, y, DECK - 1.5), (2 * T + 3.0, y, DECK - 1.5), 0.7, "wood", tone=0.2)
        for x in (T - 2.0, 2 * T + 2.0):    # cutwater posts upstream
            rod(m, (x, y, -4.0), (x - 4.0 if x < T else x + 4.0, y, 2.0), 0.6, "wood", tone=0.0)
    slab(m, T, 2 * T, 0.0, L, DECK - 1.0, DECK, "wood_light", tone=M.timber("x", 604))
    for xp in (T - 1.6, 2 * T + 0.4):
        rod(m, (xp + 0.6, 0.0, DECK + 3.0), (xp + 0.6, L, DECK + 3.0), 0.4, "wood", tone=0.2)
        for y in np.arange(2.0, L, 8.0):
            rod(m, (xp + 0.6, y, DECK - 1.0), (xp + 0.6, y, DECK + 3.0), 0.35, "wood")


def tiber_island(m):
    """Tiber Island faced with travertine as a ship: a prow at the downstream end with a carved
    head of Aesculapius's serpent-staff, the Temple of Aesculapius (the sick sleep in its
    porticoes), an obelisk standing as the mast, houses and trees, steps to the water. A paved
    way runs from the Fabricius' landing at the east end round the temple and along the
    portico to the Cestius' landing at the west end (ISLAND_WALK)."""
    W, D = 11 * T, 7 * T            # y along the river (east-west), x across
    cx, cy = D / 2, W / 2
    a, b = D / 2 - 6.0, W / 2 - 4.0
    zt = 8.0

    def hull(X, Y, Z):
        u = (Y - cy) / b
        half = a * np.sqrt(np.clip(1 - np.abs(u) ** 2.4, 0, 1))
        return np.abs(X - cx) <= half
    fill(m, (0.0, D, 0.0, W, -4.0, zt), "travertine", hull, tone=RM.travertine(2.6, 7.0, 611))
    fill(m, (0.0, D, 0.0, W, zt - 1.0, zt), "grass", lambda X, Y, Z: hull(X + 0 * Z, Y, Z) &
         (np.abs(X - cx) < a * 0.8 * np.sqrt(np.clip(1 - np.abs((Y - cy) / b) ** 2.4, 0, 1))),
         tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 612) - 0.5) * 0.8)
    for (tx, ty) in ISLAND_WALK:        # the paved way between the bridges
        fill(m, (tx * T, (tx + 1) * T, ty * T, (ty + 1) * T, zt - 1.0, zt), "travertine", hull,
             tone=lambda X, Y, Z: (hash01(np.floor(X / 3.0).astype(np.int64), np.floor(Y / 2.5).astype(np.int64), 618)
                                   - 0.5) * 0.7 - 0.6 * ((Y % 2.5) < 0.3))
    # The prow (downstream, west +y): a raised travertine ship's bow with the serpent-staff.
    fill(m, (cx - 7, cx + 6, W - 30.0, W, -4.0, zt + 6.0), "travertine",
         lambda X, Y, Z: hull(X, Y, Z) & (Y > W - 30.0) & (Z < zt + 6.0 * (Y - (W - 30.0)) / 26.0),
         tone=RM.travertine(2.0, 5.0, 613))
    fill(m, (cx + 2.0, cx + 5.0, W - 22.0, W - 12.0, 0.0, 6.0), "travertine",
         lambda X, Y, Z: np.hypot(Y - (W - 17.0), Z - 3.0) < 2.4, tone=0.4)
    RM.temple(m, RM.RTemple(order=RM.ROrder("ionic", D=0.8, H=8.0), front="-x", cols=6, deep=2, podium=2.0,
                            pediment="gods", seed=614), S, (cx - 20.0, cx + 18.0, cy - 30.0, cy + 6.0), zt)
    RM.colonnade(m, (cx + 20.0, cy - 30.0), (cx + 20.0, cy + 10.0), zt, 6,
                 RM.ROrder("tuscan", D=0.6, H=5.0, shaft="travertine", trim="travertine", fluted=False), S, 5.0, "+x",
                 seed=615)
    RM.obelisk(m, cx, cy + 26.0, zt, S.v(13.0), 3.4, base_h=4.0)
    for i, (x, y) in enumerate(((cx - 18.0, 104.0), (cx + 18.0, 14.0), (cx - 10.0, W - 44.0))):
        cypress(m, x, y, zt, h=24.0, seed=i)
    # The house stands beside the way on tile dx 1, behind the Fabricius' landing as seen,
    # so the landing at (2, 0)..(2, 2) shows as open paving.
    RM.wall(m, ISLAND_HOUSE, zt, zt + 12.0, "stucco", 616, "ochre")
    x0, x1, y0, y1 = ISLAND_HOUSE
    RM.hip(m, (x0 - 1.0, x1 + 1.0, y0 - 1.0, y1 + 1.0), zt + 12.0, 5.0, seed=617)
    lamp(m, cx + 21.0, cy - 10.0, zt + 6.0, 0.5)


def portunus(m):
    """The Temple of Portunus by the river harbour: a small Ionic temple on a podium of tufa,
    pseudo-peripteral (half columns round the cella), stuccoed travertine (it survives)."""
    RM.temple(m, RM.RTemple(order=RM.ROrder("ionic", D=0.9, H=8.3, shaft="travertine", trim="travertine"), front="-x",
                            cols=4, deep=2, plan="pseudo", podium=2.6, podium_kind="tufa", cella_kind="stucco",
                            pediment="gods", seed=621, stair_frac=0.24), S, (2.0, 3 * T - 2.0, 2.0, 2 * T - 2.0))


def hercules_victor(m):
    """The round Temple of Hercules Victor in the Forum Boarium: twenty Corinthian columns of
    white Pentelic marble round a marble cella on stepped base (it survives)."""
    RM.round_temple(m, 1.5 * T, 1.5 * T, 0.0, 1.5 * T - 1.5, 20, RM.ROrder("corinthian", D=0.83, H=10.6), S,
                    steps=3, roof="terracotta", door_face="-y", seed=631)


def ara_maxima(m):
    """The Ara Maxima of Hercules: a great altar of tufa on a platform, burnt offerings."""
    slab(m, 3.0, 2 * T - 3.0, 3.0, 2 * T - 3.0, 0.0, 2.0, "tufa", tone=0.2)
    slab(m, 8.0, 2 * T - 8.0, 6.0, 2 * T - 6.0, 2.0, 8.0, "tufa", tone=M.ashlar(2.0, 5.0, 641, spread=0.6))
    RM.cornice(m, (8.0, 2 * T - 8.0, 6.0, 2 * T - 6.0), 8.0, 1.0, 0.6, "tufa")
    fill(m, (10.0, 2 * T - 10.0, 9.0, 2 * T - 9.0, 9.0, 9.6), "ink")


def emporium(m):
    """The Emporium: a long travertine quay with ramps down to the water and mooring stones,
    the cargo of the barges stacked on it, a treadwheel crane, and behind it the Porticus
    Aemilia, a giant warehouse of brick and concrete vaults in many bays stepping up the
    slope, its roofs in rows (s = 0.25 for the warehouse, rome.md). The quay is walkable."""
    W, D = 25 * T, 11 * T          # quay along x (r 140..150), warehouse east of it
    qx0, qy0, qy1 = 0.0, W - 6 * T, W
    slab(m, 0.0, D, qy0, qy1, -4.0, 2.0, "travertine", tone=RM.travertine(2.4, 8.0, 651))
    paving(m, (0.0, D, qy0, qy1), 1.5, 2.0, "travertine", 7.0, 4.0, 652)
    for x in np.arange(10.0, D, 40.0):     # ramps down to the water, mooring stones along the edge
        fill(m, (x, x + 10.0, qy1 - 6.0, qy1, -4.0, 2.0), "travertine",
             lambda X, Y, Z: Z < 2.0 - (Y - (qy1 - 6.0)) * 0.9, tone=0.2)
        carve(m, (x, x + 10.0, qy1 - 6.0, qy1, 0.0, 2.1), lambda X, Y, Z: Z > 2.0 - (Y - (qy1 - 6.0)) * 0.9)
    for tx in EMP_BOLLARDS:
        revolve(m, tc(tx), qy1 - 4.0, 2.0, 5.0, lambda t: 1.3 - 0.4 * t, "travertine", tone=0.3)
    for i, (tx, ty) in enumerate(EMP_AMPHORAE):
        for j in range(8):
            amphora(m, tx * T + 3.5 + (j % 4) * 3.0, ty * T + 3.5 + (j // 4) * 6.0, 2.0,
                    ("dressel20", "wine", "african")[i % 3])
    for tx, ty in EMP_SACKS:
        for j in range(6):
            ellipsoid(m, (tx * T + 4.0 + (j % 3) * 4.0, ty * T + 5.0 + (j // 3) * 5.0, 4.0), (2.2, 2.0, 2.0), "wool", 0.1)
    bx, by = EMP_BLOCK      # a marble block landed by the crane, clear of the lane along the wharf
    slab(m, bx * T + 3.0, bx * T + 12.0, by * T + 4.0, by * T + 12.0, 2.0, 6.0, "marble", tone=0.2)
    treadwheel_crane(m, tc(EMP_CRANE[0]), tc(EMP_CRANE[1]), 2.0, 46.0, along="y", load="marble")
    # The Porticus Aemilia: 50 bays of barrel vaults stepping up toward the east.
    ws = 0.25 / 0.65                # the warehouse drawn at s = 0.25 inside a 0.65 landmark
    wx0, wx1, wy0, wy1 = 2 * T, 11 * T, 6.0, qy0 - 8.0
    n = 18
    for i in range(n):
        y0 = wy0 + i * (wy1 - wy0) / n
        y1 = wy0 + (i + 1) * (wy1 - wy0) / n - 1.0
        zb = 2.0 + (n - i) * 0.5
        RM.wall(m, (wx0, wx1, y0, y1 + 1.0), 0.0, zb + 16.0 * ws * 2.6, "brick", 653 + i)
        RM.vault_roof(m, (wx0, wx1, y0, y1 + 1.0), zb + 16.0 * ws * 2.6, "x", "terracotta", tiles=True, seed=670 + i)
        RM.opening(m, "+x", (wx0, wx1, y0, y1 + 1.0), 2.0, (y1 - y0) - 4.0, 0.0, 9.0, 2.0,
                   frame="travertine")
    lamp(m, wx1 + 2.0, wy1 - 10.0, 8.0, 0.5)


# The way across the island (floor on the island): from the Pons Fabricius' landing at the east
# end (2, 0) round the temple's east side, along the portico where the sick sleep (dx 5 and 6)
# and up to the Pons Cestius' landing at the west end (4, 10).
ISLAND_HOUSE = (21.0, 30.5, 28.0, 44.0)   # x, y in design units, its roof clear of tile dx 2
ISLAND_WALK = sorted({(2, 0), (2, 1), (2, 2), (3, 2), (4, 2), *((5, y) for y in range(2, 10)), (4, 9), (4, 10),
                      (6, 4), (6, 5), (6, 6)})
ON = {"rome.tiber_island": "water", "rome.pons_fabricius": "water", "rome.pons_cestius": "water",
      "rome.pons_aemilius": "water", "rome.pons_sublicius": "water"}

# Quay furniture by tile (x across r 140..150, y from c 85 west to c 61): bollards on the edge,
# stacks of amphorae and sacks, the crane, the marble blocks; every other quay tile is walkable.
# The wharf goes on south of r 150 (c 61..66, r 151..159) as kit quay beside the Horrea Galbana.
EMP_BOLLARDS = (1, 4, 7, 10)
EMP_AMPHORAE = ((1, 20), (3, 22), (9, 20))
EMP_SACKS = ((5, 21), (10, 22))
EMP_CRANE = (8, 22)
EMP_BLOCK = (9, 23)
# Row 19, the wharf's inner edge, stays open end to end (the Via Ostiensis runs along it).
EMP_SOLID = {(x, 24) for x in EMP_BOLLARDS} | set(EMP_AMPHORAE) | set(EMP_SACKS) | {EMP_CRANE, (7, 22), (8, 21), (8, 23),
                                                                                    (7, 21), EMP_BLOCK}
EMP_WALK = [(x, y) for x in range(11) for y in range(19, 25) if (x, y) not in EMP_SOLID]


def horrea_galbana(m):
    """The Horrea Galbana, the great grain warehouses: long ranges of storerooms round three
    courtyards, plain brick walls with small windows, a tufa porch at the entrance."""
    W, D = 18 * T, 6 * T
    RM.wall(m, (2.0, D - 2.0, 2.0, W - 2.0), 0.0, S.v(9.0), "brick", 681)
    for i in range(3):
        y0 = 2.0 + i * (W - 4.0) / 3 + 14.0
        y1 = 2.0 + (i + 1) * (W - 4.0) / 3 - 14.0
        carve(m, (16.0, D - 16.0, y0, y1, 0.5, S.v(9.0) + 1.0))
        paving(m, (16.0, D - 16.0, y0, y1), 0.0, 0.5, "brick", 3.0, 3.0, 682 + i)
        for x in np.linspace(20.0, D - 20.0, 4):
            ellipsoid(m, (x, (y0 + y1) / 2, 3.0), (2.4, 2.0, 2.2), "wool", 0.1)
    for s0 in np.arange(6.0, W - 8.0, 10.0):
        RM.window(m, "+x", (2.0, D - 2.0, 2.0, W - 2.0), s0, 1.6, S.v(6.0), 2.2)
    for s0 in np.arange(6.0, D - 8.0, 10.0):
        RM.window(m, "+y", (2.0, D - 2.0, 2.0, W - 2.0), s0, 1.6, S.v(6.0), 2.2)
    RM.opening(m, "+x", (2.0, D - 2.0, 2.0, W - 2.0), W / 2 - 6.0, 12.0, 0.0, 10.0, 3.0, frame="tufa")
    for i in range(3):
        y0 = 2.0 + i * (W - 4.0) / 3 + 14.0
        y1 = 2.0 + (i + 1) * (W - 4.0) / 3 - 14.0
        RM.lean_to(m, (1.0, 17.0, y0 - 14.0, y1 + 14.0), S.v(9.0), S.v(9.0) + 5.0, "-x", "terracotta", 690 + i)
        RM.lean_to(m, (D - 17.0, D - 1.0, y0 - 14.0, y1 + 14.0), S.v(9.0), S.v(9.0) + 5.0, "+x", "terracotta", 693 + i)
    for i in range(4):
        y = 2.0 + i * (W - 4.0) / 3
        RM.lean_to(m, (16.0, D - 16.0, max(1.0, y - 14.0), min(W - 1.0, y + 14.0)), S.v(9.0), S.v(9.0) + 3.0, "-x",
                   "terracotta", 697 + i)


def testaccio(m):
    """Monte Testaccio as it stood in 126 (about half its later height): a hill of broken Baetican
    oil amphorae (Dressel 20) thrown in terraces, the fresh dumps reddish, the older ones
    whitened with lime against the smell, carts and porters on the ramp."""
    W, D = 11 * T, 12 * T          # 11 east-west (c 86..96), 12 north-south (r 148..159)
    cx, cy = D / 2, W / 2

    def top(X, Y):
        r = np.hypot((X - cx) / (D / 2 - 4), (Y - cy) / (W / 2 - 4))
        return 30.0 * np.clip(1 - r, 0, 1) ** 0.8 + 2.0 * np.sin(r * 18.0)
    from arch import field_fill

    def tone(X, Y, Z):
        sherd = hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), np.floor(Z * 2).astype(np.int64), 701)
        return (sherd - 0.5) * 1.2 - 0.6 * ((Z % 3.0) < 0.5)
    field_fill(m, (0.0, D, 0.0, W, 0.0, 34.0), lambda X, Y, Z: Z - top(X, Y), "clay", tone=tone)
    fill(m, (0.0, D, 0.0, W, 0.0, 34.0), "whitewash",
         lambda X, Y, Z: (Z > top(X, Y) - 1.0) & (value_noise(X, Y, 0 * Z, 3.0, 702) > 0.66),
         tone=lambda X, Y, Z: (hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), 703) - 0.5) * 0.8,
         only_solid=True)
    for i in range(10):     # amphorae lying on the fresh dump
        a = i * 0.7
        x, y = cx + math.cos(a) * 20.0, cy + math.sin(a) * 26.0
        amphora(m, x, y, float(top(np.array(x), np.array(y))) - 1.0, "dressel20")


LANDMARKS = {
    "rome.tiber_island": Landmark((7, 11), (-4, 80), ref("tiber_island"), district=7, walk=ISLAND_WALK,
                                  floor={t: 8.0 for t in ISLAND_WALK},
                                  slots={"sleep": [{"t": [5, 4]}, {"t": [5, 6]}]}),
    "rome.pons_fabricius": Landmark((3, 4), (-4, 24), ref("pons_fabricius"), district=7,
                                    walk=[(1, y) for y in range(4)],
                                    floor={(1, y): z for y, z in enumerate(_deck_z(4))}),
    "rome.pons_cestius": Landmark((3, 4), (-4, 24), ref("pons_cestius"), district=7,
                                  walk=[(1, y) for y in range(4)], floor={(1, y): z for y, z in enumerate(_deck_z(4))}),
    "rome.pons_aemilius": Landmark((3, 10), (-4, 24), ref("pons_aemilius"), district=7,
                                   walk=[(1, y) for y in range(10)],
                                   floor={(1, y): z for y, z in enumerate(_deck_z(10))}),
    "rome.pons_sublicius": Landmark((3, 10), (-4, 20), ref("pons_sublicius"), district=7,
                                    walk=[(1, y) for y in range(10)], floor={(1, y): DECK for y in range(10)}),
    "rome.portunus": Landmark((3, 2), (0, 64), ref("portunus"), district=7),
    "rome.hercules_victor": Landmark((3, 3), (0, 72), ref("hercules_victor"), district=7),
    "rome.ara_maxima": Landmark((2, 2), (0, 16), ref("ara_maxima"), district=7,
                                slots={"sacrifice": [{"t": [2, 1], "face": "-x"}]}),
    "rome.emporium": Landmark((11, 25), (-4, 48), ref("emporium"), district=7, walk=EMP_WALK,
                              floor={t: 2.0 for t in EMP_WALK},
                              slots={"mooring": [{"t": [x, 25], "face": "-y"} for x in (0, 3, 6, 9)],
                                     "unload": [{"t": [4, 22]}, {"t": [9, 21]}, {"t": [6, 21]}]}),
    "rome.horrea_galbana": Landmark((6, 18), (0, 48), ref("horrea_galbana"), district=7,
                                    slots={"door": [{"t": [6, 9], "face": "+x"}]}),
    "rome.testaccio": Landmark((12, 11), (0, 40), ref("testaccio"), district=7,
                               slots={"dump": [{"t": [6, 11], "face": "-y"}]}),
}

INFO = {
    "rome.tiber_island": ("Tiber Island and the Temple of Aesculapius", 0.65, 90, "BSG", "tiber_island"),
    "rome.pons_fabricius": ("Pons Fabricius", 0.65, 40, "BS", "pons_fabricius"),
    "rome.pons_cestius": ("Pons Cestius", 0.65, 40, "BS", "pons_cestius"),
    "rome.pons_aemilius": ("Pons Aemilius", 0.65, 40, "BS", "pons_aemilius"),
    "rome.pons_sublicius": ("Pons Sublicius", 0.65, 30, "BS", "pons_sublicius"),
    "rome.portunus": ("Temple of Portunus", 0.65, 70, "BS", "portunus"),
    "rome.hercules_victor": ("Temple of Hercules Victor", 0.65, 70, "BS", "hercules_victor"),
    "rome.ara_maxima": ("Ara Maxima", 0.65, 20, "BS", "ara_maxima"),
    "rome.emporium": ("Emporium and Porticus Aemilia", 0.65, 60, "BSG", "emporium"),
    "rome.horrea_galbana": ("Horrea Galbana", 0.65, 60, "BS", "horrea_galbana"),
    "rome.testaccio": ("Monte Testaccio", 0.65, 64, "B", "testaccio"),
}
