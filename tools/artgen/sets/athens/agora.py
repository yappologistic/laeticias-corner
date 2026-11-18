"""The Agora and the Kolonos Agoraios in 432 (athens.md §2.3 D3-D4, §3.2): the Hephaisteion
nearly finished on its hill, the small Royal Stoa, the Stoa of Zeus only rising, the Old
Bouleuterion and the round Tholos, the Painted Stoa on the north side, the Altar of the Twelve
Gods, the Tyrannicides, the south-east fountain house, the law-court enclosure, the boundary
stone, Simon's shop and the City Eleusinion."""

from dataclasses import replace

import numpy as np

import materials as M
from arch import carve, ellipsoid, fill, halo, rod, slab
from greek import (Order, Stoa, Temple, column, conical_roof, crepidoma, doric_entablature, hip_roof, house_wall,
                   marble_wall, pediment, poros_wall, stele, statue_base, stoa, temple, tiled_roof, vase)
from rig import Dress
from setbuild import Landmark
from sets.athens.common import (LAMP, S, T, altar, blocks, bronze_statue, drum, lamp_niche, olive_tree, referrer,
                                scaffold, tiles)

ref = referrer("sets.athens.agora")

# The Hephaisteion: Pentelic marble, 6 x 13 Doric columns 5.71 m high, lower diameter 1.02 m.
HEPHAISTEION = Order("doric", D=1.02, H=5.71, upper=0.78, arch_h=0.84, frieze_h=0.84, geison_h=0.42, geison_out=0.6)
STOA_DORIC = Order("doric", D=0.92, H=5.6, upper=0.8, arch_h=0.75, frieze_h=0.8, geison_h=0.4, geison_out=0.6,
                   material="poros")
STOA_IONIC = Order("ionic", D=0.7, H=7.0, upper=0.84, flutes=24, material="poros")


def hephaisteion(m):
    """6 x 13 Doric columns on three steps, distyle in antis porches with Ionic friezes over them,
    sculptured metopes on the east front (Herakles) and the first four of each flank at the east
    end (Theseus), the rest plain; nearly finished in 432, its cult statues not yet made. The
    front faces east (hidden); the west pediment's group is a choice (evidence is thin)."""
    t = Temple(order=HEPHAISTEION, axis="y", cols=(6, 13), steps=(S.v(0.36),) * 3, tread=1.4, edge=3.6,
               cella=(12.0, 24.0), porch="antis", porch_order=HEPHAISTEION,
               pediments=("small", "hephaisteion"),
               metopes={"-y": "herakles", "+x": ("theseus", {20, 21, 22, 23}), "-x": ("theseus", {0, 1, 2, 3})},
               frieze="porches", roof="marble", akroteria="floral", seed=221)
    temple(m, t, S, 1.0, 4 * T - 1.0, 1.0, 8 * T - 1.0)


def royal_stoa(m):
    """The Stoa Basileios: a small Doric stoa facing east onto the square, terracotta akroteria
    on its gables; the laws of Solon on revolving wooden boards (axones) and on stone (kyrbeis)
    displayed before it, with inscribed stelai."""
    st = Stoa(order=replace(STOA_DORIC, H=4.2, D=0.75), front="-y", n_cols=8, inner=replace(STOA_IONIC, D=0.55),
              n_inner=3, roof="terracotta", seed=231)
    stoa(m, st, S, 1.0, 5 * T - 1.0, 1.0, 2 * T - 1.0)
    # Law boards on their pivots and inscribed stones before the colonnade (east side).
    for i, x in enumerate((14.0, 30.0, 46.0, 62.0)):
        if i % 2 == 0:
            rod(m, (x - 3.0, 0.5, 4.0), (x + 3.0, 0.5, 4.0), 0.4, "wood")
            slab(m, x - 2.6, x + 2.6, 0.0, 1.2, 1.0, 7.0, "whitewash", tone=lambda X, Y, Z: -0.5 * ((Z * 2) % 1.4 < 0.4))
        else:
            stele(m, x, 1.2, 0.0, 4.0, 9.0, face="-y", subject="decree")


def stoa_zeus(m):
    """The Stoa of Zeus Eleutherios as a building site (begun c. 430): the foundations and the
    first steps laid, a few columns standing as unfluted drums, scaffolding, blocks and drums
    lying ready, a crane."""
    seed = 241
    crepidoma(m, 4.0, 60.0, 4.0, 172.0, 0.0, (1.6, 1.6), 1.4, "poros", seed, sides=("-y",))
    for x0, x1, y0, y1 in ((4.0, 60.0, 4.0, 10.0), (54.0, 60.0, 4.0, 172.0), (4.0, 10.0, 4.0, 172.0)):
        poros_wall(m, x0, x1, y0, y1, 3.2, 8.0, seed + 1)
    for i, x in enumerate((24.0, 40.0, 56.0, 72.0)):
        column(m, x * 0.8 + 6, 12.0, 3.2, replace(STOA_DORIC, material="marble"), S, finish="drums",
               drums=1 + (i % 3), seed=i)
    scaffold(m, 20.0, 36.0, 6.0, 18.0, 3.2, 26.0, decks=2)
    for i, (x, y) in enumerate(((20.0, 40.0), (36.0, 64.0), (20.0, 96.0), (40.0, 120.0), (24.0, 150.0))):
        if i % 2:
            drum(m, x, y, 3.2, 3.6, 4.0, lying=True)
        else:
            blocks(m, x, y, 3.2, 2, seed + i)


def old_bouleuterion(m):
    """The Old Bouleuterion of the Council of 500: a square hall on a poros socle, plastered walls
    with high windows, a hipped tiled roof on interior posts, a small porch toward the square;
    lamplight at the windows when the Council sits late."""
    seed = 251
    W = 6 * T
    hb = 30.0
    for w in ((8.0, 12.0, 8.0, 88.0), (84.0, 88.0, 8.0, 88.0), (8.0, 88.0, 8.0, 12.0), (8.0, 88.0, 84.0, 88.0)):
        house_wall(m, *w, 0.0, hb, seed, socle=6.0, plaster="whitewash")
    for face, y in (("+x", 30.0), ("+x", 62.0), ("+y", 30.0), ("+y", 62.0)):
        if face == "+x":
            carve(m, (83.0, 89.0, y, y + 4.0, 20.0, 26.0))
            fill(m, (85.0, 86.0, y, y + 4.0, 20.0, 26.0), "lamp", tone=-0.6)
            halo(m, 88.0, y + 2.0, 23.0, 8.0, LAMP, 0.6)
        else:
            carve(m, (y, y + 4.0, 83.0, 89.0, 20.0, 26.0))
            fill(m, (y, y + 4.0, 85.0, 86.0, 20.0, 26.0), "lamp", tone=-0.6)
            halo(m, y + 2.0, 88.0, 23.0, 8.0, LAMP, 0.6)
    # A porch of two columns on the east (the square side) and a door on the south.
    small = Order("doric", D=0.62, H=4.4, upper=0.8, arch_h=0.55, frieze_h=0.6, geison_h=0.35, geison_out=0.45,
                  material="poros")
    for x in (38.0, 58.0):
        column(m, x, 2.5, 0.0, small, S)
    doric_entablature(m, (34.0, 62.0, 0.5, 8.0), S.v(small.H), small, S, [38.0, 58.0], [2.5], faces=("-y",),
                      seed=seed + 1)
    carve(m, (83.0, 89.0, 44.0, 52.0, 0.0, 16.0))
    fill(m, (86.0, 87.0, 44.0, 52.0, 0.0, 16.0), "cedar", tone=lambda X, Y, Z: -0.4 * ((Y % 2.0) < 0.3))
    hip_roof(m, 5.0, 91.0, 5.0, 91.0, hb, 14.0, material="terracotta", seed=seed + 2, apex=0.15)


def tholos(m):
    """The Tholos, where the fifty prytaneis on duty dine and a third of them sleep: a round
    building on a stone socle with plastered walls, a conical roof of lozenge-shaped tiles with
    a finial, a small kitchen annex on the north with its chimney smoking, lamplit door."""
    seed = 261
    cx, cy, r = 40.0, 40.0, 36.0
    fill(m, (cx - r - 1, cx + r + 1, cy - r - 1, cy + r + 1, 0.0, 5.0), "poros",
         lambda X, Y, Z: np.hypot(X - cx, Y - cy) <= r + 0.6, tone=M.ashlar(2.5, 6.0, seed, spread=0.6))
    fill(m, (cx - r, cx + r, cy - r, cy + r, 5.0, 28.0), "whitewash",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) <= r) & (np.hypot(X - cx, Y - cy) > r - 4.0),
         tone=M.mud_plaster(seed, 0.5, 5.0, 2.0))
    fill(m, (cx - r, cx + r, cy - r, cy + r, 5.0, 28.0), "whitewash", lambda X, Y, Z: np.hypot(X - cx, Y - cy) <= r - 4.0,
         tone=-0.4)
    # The door on the east and windows; a moulded eave course.
    carve(m, (cx - 4.0, cx + 4.0, cy - r - 1, cy - r + 5, 5.0, 19.0))
    fill(m, (cx - 4.0, cx + 4.0, cy - r + 3.5, cy - r + 4.5, 5.0, 19.0), "lamp", tone=-0.4)
    halo(m, cx, cy - r + 2.0, 12.0, 10.0, LAMP, 0.7)
    for a in (0.8, 2.3, 3.9, 5.4):
        wx, wy = cx + np.cos(a) * (r - 1), cy + np.sin(a) * (r - 1)
        fill(m, (wx - 1.5, wx + 1.5, wy - 1.5, wy + 1.5, 19.0, 23.0), "ink", tone=0.0)
    fill(m, (cx - r - 1.5, cx + r + 1.5, cy - r - 1.5, cy + r + 1.5, 26.5, 28.5), "poros",
         lambda X, Y, Z: np.hypot(X - cx, Y - cy) <= r + 1.4, tone=0.3)
    conical_roof(m, cx, cy, r + 2.0, 28.5, 22.0, seed=seed + 1)
    ellipsoid(m, (cx, cy, 51.5), (2.0, 2.0, 2.4), "terracotta", tone=0.3)
    # The kitchen annex on the north (-x) with its chimney.
    for w in ((0.0, 8.0, 26.0, 54.0), (0.0, 12.0, 26.0, 29.0), (0.0, 12.0, 51.0, 54.0)):
        house_wall(m, *w, 0.0, 16.0, seed + 2, socle=3.0, plaster="mudbrick")
    tiled_roof(m, -1.0, 12.0, 24.0, 56.0, 16.0, 3.0, axis="y", material="terracotta", kind="laconian", seed=seed + 3)
    slab(m, 3.0, 7.0, 46.0, 50.0, 16.0, 23.0, "mudbrick", tone=-0.2)


def stoa_poikile(m):
    """The Painted Stoa on the north side of the square, facing south: a long Doric colonnade
    with an inner row of Ionic columns, and on the back wall the great painted wooden panels
    (Marathon, the Amazons, the fall of Troy, Oinoe); no captured shields yet in 432 (those of
    Pylos and Skione came in 425 and 421). Its ends open, so walkers stroll the aisle between the colonnade and the inner row."""
    st = Stoa(order=STOA_DORIC, front="+x", inner=STOA_IONIC, n_inner=6, inner_at=0.27,
              panels=("oinoe", "amazons", "troy", "marathon"), shields=0, roof="terracotta", open_ends=True,
              seed=271)
    stoa(m, st, S, 0.0, 3 * T, 0.0, 10 * T, col_tiles=range(10))
    lamp_niche(m, 6.0, 40.0, 14.0, 0.4)
    lamp_niche(m, 6.0, 120.0, 14.0, 0.4)


def twelve_gods(m):
    """The Altar of the Twelve Gods, from which distances from Athens are reckoned: a square
    precinct fenced by a parapet of marble slabs on a low step, openings on two sides, the altar
    in the middle."""
    seed = 281
    slab(m, 2.0, 30.0, 2.0, 30.0, 0.0, 1.2, "poros", tone=0.2)
    for w in ((2.0, 30.0, 2.0, 3.6), (2.0, 30.0, 28.4, 30.0), (2.0, 3.6, 2.0, 30.0), (28.4, 30.0, 2.0, 30.0)):
        marble_wall(m, *w, 1.2, 6.5, seed=seed, orthostate=0.0, toichobate=0.0)
        slab(m, w[0] - 0.3, w[1] + 0.3, w[2] - 0.3, w[3] + 0.3, 6.5, 7.2, "marble", tone=0.3)
    carve(m, (12.0, 20.0, 27.0, 31.0, 1.2, 8.0))
    carve(m, (27.0, 31.0, 12.0, 20.0, 1.2, 8.0))
    altar(m, 16.0, 16.0, 1.2, 8.0, 6.0, 3.6, fire=False, steps=False)


# The Tyrannicides by Kritios and Nesiotes (477/6): Harmodios young and beardless striking
# overhead, Aristogeiton bearded, his cloak over his outstretched arm.
HARMODIOS = Dress(skin="skin_tan", garment="none", beard="none", hair="cedar", hair_style="curly", feet="bare",
                  hand_r="sword")
ARISTOGEITON = Dress(skin="skin_tan", garment="none", beard="full", hair="cedar", hair_style="short", feet="bare",
                     cape="bronze_cast")


def tyrannicides(m):
    """The bronze pair on a marble base with its epigram: the young Harmodios striding forward
    with his sword raised to strike, the bearded Aristogeiton beside him, his cloak over his
    outstretched arm, both striding in step toward the tyrant."""
    zb = statue_base(m, 16.0, 16.0, 0.0, 18.0, 5.0)
    bronze_statue(m, HARMODIOS, 13.0, 19.0, zb, 20.0, anim="work_high", frame=0)
    bronze_statue(m, ARISTOGEITON, 19.0, 13.0, zb, 20.0, anim="gesture", frame=2)


def se_fountain(m):
    """The south-east fountain house: a long building on the south side of the square, its
    porch of Doric columns in antis on the north (the square side) with water running from
    lion-head spouts into the draw basin, the reservoirs at the ends under a tiled roof."""
    seed = 291
    small = Order("doric", D=0.5, H=3.2, upper=0.8, arch_h=0.45, frieze_h=0.5, geison_h=0.3, geison_out=0.4,
                  material="poros")
    hb = S.v(small.H)
    for w in ((24.0, 60.0, 2.0, 5.0), (24.0, 60.0, 59.0, 62.0), (56.0, 60.0, 2.0, 62.0), (36.0, 39.0, 5.0, 59.0)):
        poros_wall(m, *w, 0.0, hb + 4.0, seed)
    for y in (16.0, 32.0, 48.0):
        column(m, 26.0, y, 0.0, small, S)
    zg = doric_entablature(m, (24.0, 60.0, 2.0, 62.0), hb, small, S, [26.0], [16.0, 32.0, 48.0], faces=("-x",),
                           seed=seed + 1)
    tiled_roof(m, 21.0, 63.0, 0.0, 64.0, zg, 5.0, axis="y", material="terracotta", seed=seed + 2)
    for face in ("-y", "+y"):
        pediment(m, face, 21.0, 63.0, 0.0, 64.0, zg, 5.0, small, S, subject=None, akroteria="floral")
    # Lion-head spouts in the porch's back wall, water falling into the basin.
    for y in (12.0, 24.0, 40.0, 52.0):
        ellipsoid(m, (35.4, y, 9.0), (1.0, 1.3, 1.3), "bronze", tone=0.3)
        fill(m, (33.6, 34.6, y - 0.5, y + 0.5, 3.0, 8.4), "water", tone=0.5)
    slab(m, 28.0, 36.0, 5.0, 59.0, 0.0, 3.0, "poros", tone=0.2)
    fill(m, (29.0, 35.0, 6.0, 58.0, 2.0, 3.1), "water", tone=0.3)


def lawcourt(m):
    """The rectangular enclosure (a law court, perhaps the Heliaia: debated): a high wall of
    poros on rubble round an open court, an entrance on the north, benches along the inside."""
    seed = 301
    W, Lh = 6 * T, 7 * T
    for w in ((4.0, 92.0, 4.0, 8.0), (4.0, 92.0, Lh - 8.0, Lh - 4.0), (4.0, 8.0, 4.0, Lh - 4.0), (88.0, 92.0, 4.0, Lh - 4.0)):
        house_wall(m, *w, 0.0, 14.0, seed, socle=6.0, plaster="mudbrick")
    carve(m, (3.0, 9.0, 48.0, 64.0, 0.0, 14.0))      # the entrance, a whole tile wide
    for x, y0, y1 in ((12.0, 12.0, 46.0), (12.0, 66.0, Lh - 12.0), (80.0, 12.0, Lh - 12.0)):   # benches, open at the door
        slab(m, x, x + 3.0, y0, y1, 0.0, 2.4, "wood", tone=M.timber("y", seed))


def horos(m):
    """The boundary stone of the Agora: a marble post inscribed 'I am the boundary of the Agora'
    (the letters too small to read at this size)."""
    slab(m, 5.0, 11.0, 5.0, 11.0, 0.0, 9.0, "marble", tone=M.ashlar(9.0, 20.0, 5, joint=0.1, spread=0.3))
    fill(m, (5.0, 11.0, 10.6, 11.2, 4.0, 8.0), "cinnabar",
         lambda X, Y, Z: ((Z * 2) % 1.2 < 0.5) & ((X * 2.5) % 1.0 < 0.6), tone=-0.3, only_solid=True)


def simon_shop(m):
    """Simon the shoemaker's house and shop at the corner of the Agora: a small mudbrick house on
    a stone socle with a tiled roof, the shop door open with a workbench before it, leather and
    lasts, a lamp; hobnails and his cup were found here."""
    seed = 311
    for w in ((4.0, 28.0, 4.0, 7.0), (4.0, 28.0, 41.0, 44.0), (4.0, 7.0, 4.0, 44.0), (25.0, 28.0, 4.0, 44.0)):
        house_wall(m, *w, 0.0, 18.0, seed, socle=3.0)
    carve(m, (24.0, 29.0, 18.0, 26.0, 0.0, 12.0))
    fill(m, (26.0, 27.0, 18.0, 26.0, 0.0, 12.0), "ink", tone=0.0)
    tiled_roof(m, 2.0, 30.0, 2.0, 46.0, 18.0, 5.0, axis="y", material="terracotta", kind="laconian", seed=seed + 1)
    slab(m, 29.0, 31.0, 14.0, 30.0, 0.0, 3.6, "wood", tone=M.timber("y", seed))
    rod(m, (30.0, 16.0, 3.6), (30.0, 22.0, 3.8), 0.3, "leather")
    vase(m, 30.0, 34.0, 0.0, 3.0, "amphora", figure="plain")
    lamp_niche(m, 28.6, 28.0, 13.0, 0.5)


def eleusinion(m):
    """The City Eleusinion, sanctuary of Demeter and Kore on the Panathenaic Way: a precinct
    wall with a gate and, inside, a small poros temple and an altar."""
    seed = 321
    for w in ((0.0, 80.0, 0.0, 3.0), (0.0, 80.0, 77.0, 80.0), (0.0, 3.0, 0.0, 80.0), (77.0, 80.0, 0.0, 80.0)):
        house_wall(m, *w, 0.0, 10.0, seed, socle=4.0, plaster="whitewash")
    carve(m, (76.0, 81.0, 34.0, 46.0, 0.0, 10.0))
    small = Order("doric", D=0.6, H=4.0, upper=0.8, arch_h=0.5, frieze_h=0.55, geison_h=0.3, geison_out=0.4,
                  material="poros")
    t = Temple(order=small, axis="x", cols=(4, 6), steps=(1.2, 1.2), tread=1.0, edge=2.6, peripteral=False,
               cella=(4.0, 6.0), porch="prostyle", porch_cols=4, pediments=("small", "small"), roof="terracotta",
               seed=seed + 1)
    temple(m, t, S, 12.0, 56.0, 20.0, 60.0)
    altar(m, 66.0, 40.0, 0.0, 6.0, 4.0, 3.0, fire=False)
    olive_tree(m, 10.0, 70.0, 0.0, h=20.0, seed=7)


LANDMARKS = {
    "athens.hephaisteion": Landmark((4, 8), (0, 64), ref("hephaisteion"), district=2),
    "athens.royal_stoa": Landmark((5, 2), (0, 48), ref("royal_stoa"),
                                  slots={"herald": [{"t": [2, -1], "face": "-y"}]}, district=2),
    "athens.stoa_zeus": Landmark((11, 4), (0, 40), ref("stoa_zeus"),
                                 slots={"mason": [{"t": [5, -1], "face": "+y"}, {"t": [8, -1], "face": "+y"}]},
                                 district=2),
    "athens.old_bouleuterion": Landmark((6, 6), (0, 48), ref("old_bouleuterion"),
                                        slots={"door": [{"t": [6, 3], "face": "-x"}]}, district=2),
    "athens.tholos": Landmark((5, 5), (0, 56), ref("tholos"), slots={"door": [{"t": [2, -1], "face": "+y"}]},
                              emitters={"smoke": (5.0, 48.0, 23.5)}, district=2),
    "athens.stoa_poikile": Landmark((3, 10), (0, 48), ref("stoa_poikile"), walk=[(1, dy) for dy in range(10)],
                                    floor={(1, dy): 1.6 for dy in range(10)},
                                    slots={"stroll": [{"t": [1, 2]}, {"t": [1, 5]}, {"t": [1, 8]}],
                                           "philosopher": [{"t": [1, 4], "face": "-y"}],
                                           "sit": [{"t": [1, 6], "face": "-x"}]}, district=2),
    "athens.twelve_gods": Landmark((2, 2), (0, 12), ref("twelve_gods"), district=2),
    "athens.tyrannicides": Landmark((2, 2), (0, 40), ref("tyrannicides"), district=2),
    "athens.se_fountain": Landmark((4, 4), (0, 40), ref("se_fountain"), walk=[(0, dy) for dy in range(4)],
                                   slots={"fill": [{"t": [0, 1], "face": "+x"}, {"t": [0, 2], "face": "+x"}]},
                                   emitters={"spout_a": (34.0, 24.0, 8.0), "spout_b": (34.0, 40.0, 8.0)}, district=2),
    # The open court is walkable from the entrance; jurors sit along the two benches.
    "athens.lawcourt": Landmark((6, 7), (0, 16), ref("lawcourt"), district=2,
                                walk=[(0, 3)] + tiles(1, 4, 1, 5),
                                slots={"jurors": [{"t": [1, y], "face": "-x"} for y in range(1, 6)] +
                                                 [{"t": [4, y], "face": "+x"} for y in range(1, 6)],
                                       "speaker": [{"t": [2, 3], "face": "+x"}, {"t": [3, 3], "face": "-x"}]}),
    "athens.horos": Landmark((1, 1), (0, 10), ref("horos"), district=2),
    "athens.simon_shop": Landmark((2, 3), (0, 28), ref("simon_shop"),
                                  slots={"work": [{"t": [2, 1], "face": "+y"}], "sit": [{"t": [2, 2], "face": "-x"}]},
                                  district=2),
    "athens.eleusinion": Landmark((5, 5), (0, 40), ref("eleusinion"), district=2),
}
