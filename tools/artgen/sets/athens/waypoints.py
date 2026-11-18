"""The Greek waypoints in the summer of 432 BC (world.md §4.2; athens.md as fact-checked):
Delphi's temple of Apollo with the altar of the Chians and the serpent column, the Athenian
Treasury, Corinth's archaic temple of Apollo, the summit of Acrocorinth, the diolkos, the
sanctuary of Apollo on Delos, the terrace of the Naxian lions and the archaic Artemision at
Ephesus. Grid axes: +x south, +y west; the camera sees the south and west faces, so temples
fronting east show their flank and west end.

Scales: s = 0.65 for the temples at Delphi and Corinth, 0.9 for the Treasury, 0.5 for Delos,
Acrocorinth and the diolkos, 1.0 for the lions, 0.53 for the Artemision (its 55 x 115 m
stylobate fills the 8 x 16 tiles).
"""

from dataclasses import replace

import numpy as np

import materials as M
from arch import Scale, carve, cylinder, ellipsoid, face_box, field_fill, fill, rod, slab
from greek import (Order, Temple, column, crepidoma, geison_ring, marble_wall, paint_band, paint_ring, temple,
                   tiled_roof, pediment)
from rig import Dress
from setbuild import Landmark
from sets.athens.common import FIRE, altar, blocks, bronze_statue, drum, olive_tree, paving, referrer, tiles
from voxel import value_noise

ref = referrer("sets.athens.waypoints")
T = 16
S65, S9, S5, S1, SA = Scale(0.65), Scale(0.9), Scale(0.5), Scale(1.0), Scale(0.53)

# ---------------------------------------------------------------- Delphi

# The Alkmaionid temple (late 6th century): 6 x 15 Doric columns of stuccoed limestone (poros), its east
# front of Parian marble (Herodotus 5.62); the column dimensions are approximate.
DELPHI = Order("doric", D=1.75, H=10.6, upper=0.77, arch_h=1.4, frieze_h=1.5, geison_h=0.65, geison_out=0.8,
               material="marble")
VOTARY = Dress(garment="none", beard="full", hair="cedar", hair_style="short", feet="bare")
CHARIOTEER = Dress(garment="chiton", colour="white_paint", beard="none", hair="cedar", hair_style="short", feet="bare")


def serpent_column(m, x, y, z, h, S):
    """The Plataian dedication of 479: three bronze serpents twisted into one column, their
    heads spreading under a golden tripod cauldron (the gold was taken in the 4th century)."""
    for i in range(3):
        a0 = i * 2 * np.pi / 3
        pts = [(x + 0.9 * np.cos(a0 + t * 9.0), y + 0.9 * np.sin(a0 + t * 9.0), z + 2.0 + t * (h - 4.0))
               for t in np.linspace(0, 1, 28)]
        for p, q in zip(pts, pts[1:]):
            rod(m, p, q, 0.75, "bronze", tone=0.15 * (i - 1))
        a = a0 + 9.0
        ellipsoid(m, (x + 2.0 * np.cos(a), y + 2.0 * np.sin(a), z + h - 1.5), (1.3, 1.3, 0.8), "bronze", tone=0.3)
    slab(m, x - 2.8, x + 2.8, y - 2.8, y + 2.8, z, z + 2.0, "poros", tone=M.ashlar(1.0, 3.0, 5))
    fill(m, (x - 3.5, x + 3.5, y - 3.5, y + 3.5, z + h - 0.5, z + h + 3.5), "gold",
         lambda X, Y, Z: np.hypot(X - x, Y - y) < 3.4 - 1.6 * ((Z - (z + h - 0.5)) / 4.0 - 1) ** 2, tone=0.3)
    for i in range(3):
        a = i * 2 * np.pi / 3 + 0.5
        rod(m, (x + 3.0 * np.cos(a), y + 3.0 * np.sin(a), z + h + 3.0), (x + 3.4 * np.cos(a), y + 3.4 * np.sin(a),
                                                                         z + h + 5.0), 0.35, "gold")


def delphi_apollo(m):
    """The temple terrace at Delphi in 432 BC: the Alkmaionid temple of Apollo (poros, stuccoed
    and painted, a terracotta-tiled roof, the west pediment with the battle of gods and giants
    in view; the marble east front with Apollo's arrival faces away), the altar of the Chians
    before its east front in dark limestone with white marble base and crown, the serpent
    column of Plataia beside it, bronze votive statues on bases along the south flank, the
    terrace paved in limestone. No theatre: the stone theatre is 4th century."""
    paving(m, 0.0, 96.0, 0.0, 192.0, 0.0, 1.0, material="poros", seed=801, slab_x=5.0, slab_y=4.0)
    t = Temple(order=DELPHI, axis="y", cols=(6, 15), steps=(S65.v(0.4),) * 3, tread=1.5, edge=3.6,
               cella=(10.0, 22.0), porch="antis", porch_order=replace(DELPHI, H=10.0, D=1.6),
               pediments=("small", "gigantomachy"), metopes={}, roof="terracotta", akroteria="floral",
               door_glow=True, seed=803)
    temple(m, t, S65, 20.0, 76.0, 28.0, 178.0, z0=1.0)
    # The altar of the Chians (early 5th century) before the east front.
    ax, ay = 48.0, 12.0
    slab(m, ax - 9.0, ax + 9.0, ay - 6.0, ay + 6.0, 1.0, 2.6, "marble", tone=M.ashlar(1.6, 5.0, 805, spread=0.2))
    slab(m, ax - 8.0, ax + 8.0, ay - 5.0, ay + 5.0, 2.6, 7.6, "slate", tone=M.ashlar(1.6, 4.0, 807, spread=0.3))
    slab(m, ax - 8.6, ax + 8.6, ay - 5.6, ay + 5.6, 7.6, 8.8, "marble", tone=0.3)
    fill(m, (ax - 7.0, ax + 7.0, ay - 4.0, ay + 4.0, 8.8, 9.2), "ink", tone=0.1)
    slab(m, ax - 3.0, ax + 3.0, ay + 6.0, ay + 10.0, 1.0, 2.0, "marble", tone=0.2)      # the ramp to it
    serpent_column(m, 72.0, 12.0, 1.0, S65.v(6.5), S65)
    # Votive bronzes along the south flank: athletes and a chariot group's driver.
    for i, y in enumerate(np.arange(42.0, 170.0, 26.0)):
        slab(m, 82.0, 88.0, y - 3.0, y + 3.0, 1.0, 4.0, "poros", tone=M.ashlar(1.5, 3.0, 809 + i))
        bronze_statue(m, CHARIOTEER if i % 3 == 1 else VOTARY, 85.0, y, 4.0, 11.0, turns=1)
    olive_tree(m, 90.0, 184.0, 1.0, h=16.0, seed=11)


def _delphi_landmark():
    return Landmark((6, 12), (0, 90), ref("delphi_apollo"),
                    slots={"pray": [{"t": [2, -1], "face": "+y"}, {"t": [3, -1], "face": "+y"}],
                           "consult": [{"t": [6, 3], "face": "-x"}], "priest": [{"t": [4, -1], "face": "+y"}]},
                    district=20)


TREASURY = Order("doric", D=0.8, H=4.6, upper=0.8, arch_h=0.6, frieze_h=0.65, geison_h=0.33, geison_out=0.45)


def athenian_treasury(m):
    """The Athenian Treasury (about 500-490 BC; Pausanias ties it to Marathon): a small Doric
    building of Parian marble, two columns in antis at its east front (hidden), thirty metopes
    with Theseus on the south side toward the Sacred Way (in view) and Herakles on the north,
    the triangular Marathon base along its south side."""
    paving(m, 0.0, 32.0, 0.0, 48.0, 0.0, 0.8, material="poros", seed=811, slab_x=4.0, slab_y=4.0)
    t = Temple(order=TREASURY, axis="y", cols=(2, 2), steps=(S9.v(0.35), S9.v(0.35)), tread=0.9, edge=2.6,
               peripteral=False, cella=(2.0, 6.0), porch="antis",
               pediments=("small", "small"), metopes={"+x": "theseus", "-x": "herakles", "-y": "herakles"},
               roof="marble", akroteria="floral", seed=813)
    temple(m, t, S9, 2.0, 26.0, 4.0, 46.0, z0=0.8)
    # The Marathon base: a low step along the south side with bronze figures (Miltiades and
    # the heroes; the group is attested only by Pausanias, its date debated).
    slab(m, 27.0, 31.5, 8.0, 44.0, 0.8, 2.6, "poros", tone=M.ashlar(1.0, 4.0, 815))
    for y in (14.0, 26.0, 38.0):
        bronze_statue(m, VOTARY, 29.2, y, 2.6, 8.0, turns=1)


def _treasury_landmark():
    return Landmark((2, 3), (0, 48), ref("athenian_treasury"), slots={"visit": [{"t": [2, 1], "face": "-x"}]},
                    district=20)


# ---------------------------------------------------------------- Corinth

# The archaic temple of Apollo (c. 540 BC): 6 x 15 stocky monolithic Doric columns 7.2 m high,
# lower diameter about 1.75 m, of poros under white stucco; a double cella.
CORINTH = Order("doric", D=1.75, H=7.2, upper=0.72, entasis=0.0, flutes=20, arch_h=1.45, frieze_h=1.5,
                geison_h=0.7, geison_out=0.85, material="marble")


def corinth_apollo(m):
    """Corinth's temple of Apollo on its hill: monolithic columns with broad flaring capitals
    (archaic Doric), heavy entablature, painted terracotta roof and akroteria, the cella in
    two parts; the hilltop round it is rock with a little soil and a few olives."""
    field_fill(m, (0.0, 96.0, 0.0, 192.0, 0.0, 2.0),
               lambda X, Y, Z: Z - (1.2 + (value_noise(X, Y, Z * 0, 9.0, 821) - 0.5) * 1.2), "attic_rock",
               tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 823) - 0.5) * 1.2)
    t = Temple(order=CORINTH, axis="y", cols=(6, 15), steps=(S65.v(0.42),) * 3, tread=1.4, edge=3.8,
               cella=(10.0, 18.0), porch="antis", porch_order=replace(CORINTH, H=6.8, D=1.6),
               pediments=("small", "small"), roof="terracotta", akroteria="floral", seed=825)
    temple(m, t, S65, 18.0, 78.0, 24.0, 172.0, z0=1.5)
    for (x, y, h) in ((8.0, 12.0, 14.0), (88.0, 182.0, 13.0), (8.0, 184.0, 15.0)):
        olive_tree(m, x, y, 1.5, h=h, seed=int(x + y))


def _corinth_landmark():
    return Landmark((6, 12), (0, 80), ref("corinth_apollo"), slots={"pray": [{"t": [2, -1], "face": "+y"}]},
                    district=21)


APHRODITE = Order("doric", D=0.6, H=4.2, upper=0.8, arch_h=0.5, frieze_h=0.55, geison_h=0.3, geison_out=0.4,
                  material="poros")


def acrocorinth_summit(m):
    """The top of Acrocorinth: a crown of grey limestone outcrops, the small temple of Aphrodite
    (Strabo's 'small temple') in antis on its levelled top, a circuit wall of polygonal masonry
    round the summit with a gate on the path's side."""
    def rock(X, Y, Z):
        r = np.hypot(X - 24.0, Y - 24.0)
        top = 9.0 - np.clip(r - 14.0, 0, None) * 0.7 + (value_noise(X, Y, Z * 0, 5.0, 831) - 0.5) * 4.0
        top = np.where((np.abs(X - 22.0) < 9.0) & (np.abs(Y - 24.0) < 13.0), 9.0, top)
        return Z - np.maximum(top, 0.5)
    field_fill(m, (0.0, 48.0, 0.0, 48.0, 0.0, 14.0), rock, "attic_rock",
               tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.6, 833) - 0.5) * 1.4)
    t = Temple(order=APHRODITE, axis="y", cols=(2, 2), steps=(1.0, 1.0), tread=0.8, edge=2.2, peripteral=False,
               cella=(2.0, 5.0), porch="antis", pediments=("small", "small"), roof="terracotta", seed=835)
    temple(m, t, S5, 14.0, 30.0, 12.0, 36.0, z0=9.0)
    # The circuit: polygonal blocks on the rim, a gate on the west.
    def ring(X, Y, Z):
        r = np.hypot(X - 24.0, Y - 24.0)
        gate = (Y > 36.0) & (np.abs(X - 24.0) < 3.0)
        return (np.abs(r - 20.5) < 1.6) & ~gate
    fill(m, (0.0, 48.0, 0.0, 48.0, 0.0, 22.0), "poros",
         lambda X, Y, Z: ring(X, Y, Z) & (Z < 9.0 - np.clip(np.hypot(X - 24.0, Y - 24.0) - 14.0, 0, None) * 0.7 + 9.5),
         tone=M.ashlar(2.2, 4.0, 837, polygonal=0.8))
    altar(m, 22.0, 6.0, 9.0, 4.0, 3.0, 2.4, fire=False, material="poros")


def _acro_landmark():
    return Landmark((3, 3), (0, 36), ref("acrocorinth_summit"), district=21)


def diolkos(m):
    """The diolkos across the isthmus (about 600 BC): a trackway of poros slabs with two
    grooves 1.5 m apart worn and cut for the wheels, beaten earth either side; halfway along,
    a small ship on its wheeled cradle waits to be hauled over, propped and roped."""
    L = 20 * T
    fill(m, (0.0, L, 0.0, 32.0, 0.0, 0.5), "soil", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 841) - 0.5) * 0.9)
    slab(m, 0.0, L, 9.0, 23.0, 0.0, 0.9, "poros", tone=M.paving(3.5, 7.0, 843, joint=0.3))
    for yg in (12.6, 19.4):
        carve(m, (0.0, L, yg - 0.5, yg + 0.5, 0.45, 1.0))
        fill(m, (0.0, L, yg - 0.5, yg + 0.5, 0.3, 0.45), "poros", tone=-0.7)
    # The ship on its cradle (x 132..180): a timber cradle on four wheels in the grooves.
    cx0, cx1 = 134.0, 178.0
    slab(m, cx0, cx1, 10.0, 22.0, 2.4, 3.6, "wood", tone=M.timber("x", 845))
    for x in (cx0 + 4.0, cx1 - 4.0):
        for yg in (12.6, 19.4):
            fill(m, (x - 2.2, x + 2.2, yg - 0.5, yg + 0.5, 0.45, 4.8), "wood",
                 lambda X, Y, Z, x=x: np.hypot(X - x, Z - 2.6) < 2.2, tone=lambda X, Y, Z: 0.3 - 0.4 * ((X % 1.2) < 0.4))
    def hull(X, Y, Z):
        u = (X - (cx0 + cx1) / 2) / ((cx1 - cx0) / 2 + 3.0)
        half = 5.2 * np.sqrt(np.clip(1 - u ** 2, 0, 1))
        keel = 3.6 + 2.4 * u ** 2
        return (np.abs(Y - 16.0) < half * np.clip((Z - keel) / 4.0 + 0.35, 0, 1)) & (Z < 11.5 + 2.0 * u ** 4) & (Z > keel)
    fill(m, (cx0 - 4.0, cx1 + 4.0, 9.0, 23.0, 3.0, 16.0), "wood", hull,
         tone=lambda X, Y, Z: M.timber("x", 847)(X, Y, Z) + 0.3 * ((Z % 1.8) < 0.4))
    carve(m, (cx0, cx1 - 2.0, 12.4, 19.6, 9.6, 16.0))
    fill(m, (cx0 - 4.0, cx1 + 4.0, 9.0, 23.0, 3.0, 5.5), "pitch", hull, tone=0.1, only_solid=True)
    fill(m, (cx1 - 1.0, cx1 + 1.0, 14.5, 17.5, 9.0, 12.0), "cinnabar", tone=0.2, only_solid=True)
    rod(m, ((cx0 + cx1) / 2 + 4.0, 16.0, 9.0), ((cx0 + cx1) / 2 + 4.0, 16.0, 24.0), 0.45, "wood")
    rod(m, ((cx0 + cx1) / 2 + 4.0, 13.0, 22.0), ((cx0 + cx1) / 2 + 4.0, 19.0, 22.0), 0.3, "wood")
    for y in (11.0, 21.0):                    # props
        rod(m, (cx0 + 10.0, y - 3.0 if y < 16 else y + 3.0, 0.5), (cx0 + 10.0, y, 7.0), 0.4, "wood")
        rod(m, (cx1 - 10.0, y - 3.0 if y < 16 else y + 3.0, 0.5), (cx1 - 10.0, y, 7.0), 0.4, "wood")
    for y in (14.0, 18.0):                    # hauling ropes laid out ahead (south)
        fill(m, (cx1 + 3.0, cx1 + 30.0, y - 0.3, y + 0.3, 0.45, 0.95), "straw", tone=0.2)


def _diolkos_landmark():
    walk = [t for t in tiles(0, 19, 0, 1) if not (8 <= t[0] <= 11)]
    return Landmark((20, 2), (0, 26), ref("diolkos"), walk=walk,
                    slots={"haul": [{"t": [12, 0], "face": "-x"}, {"t": [12, 1], "face": "-x"}]}, district=21)


# ---------------------------------------------------------------- Delos

POROS_NAOS = Order("doric", D=0.8, H=5.0, upper=0.78, arch_h=0.6, frieze_h=0.65, geison_h=0.35, geison_out=0.5,
                   material="poros")
DELIANS = Order("doric", D=1.2, H=5.9, upper=0.78, arch_h=0.8, frieze_h=0.85, geison_h=0.4, geison_out=0.55,
                material="marble")
KOUROS = Dress(garment="none", beard="none", hair="cedar", hair_style="long", feet="bare")


def delos_sanctuary(m):
    """The sanctuary of Apollo on Delos in 432 BC, its temples facing west: the old poros temple
    (Porinos Naos, later 6th century), the marble temple of the Delians begun after 478 and
    left unfinished when the League's treasury went to Athens in 454 (its platform laid, a few
    columns standing as drums, blocks waiting); the long Oikos of the Naxians with its porch;
    the Naxian colossus of Apollo, nearly 9 m of marble, on its inscribed base; the archaic
    temple of Artemis; an altar; paving and stelai. The temple of the Athenians is later (425)."""
    paving(m, 0.0, 128.0, 0.0, 160.0, 0.0, 0.7, material="marble_rough", seed=851, slab_x=5.0, slab_y=4.0)
    # The Porinos Naos.
    t = Temple(order=POROS_NAOS, axis="y", cols=(4, 4), steps=(1.2, 1.2), tread=1.0, edge=2.4, peripteral=False,
               cella=(3.0, 8.0), porch="prostyle", porch_cols=4, pediments=("small", "small"), roof="terracotta",
               seed=853)
    temple(m, t, S5, 6.0, 34.0, 56.0, 100.0, z0=0.7)
    # The temple of the Delians, unfinished: three steps, the stylobate, columns as drums.
    (sx0, sx1, sy0, sy1), zs = crepidoma(m, 42.0, 74.0, 36.0, 104.0, 0.7, (1.4, 1.4, 1.4), 1.0, "marble", 855)
    axx = np.linspace(sx0 + 2.6, sx1 - 2.6, 6)
    axy = np.linspace(sy0 + 2.6, sy1 - 2.6, 13)
    for i, x in enumerate(axx):
        for j, y in enumerate(axy):
            if i in (0, 5) or j in (0, 12):
                n = (2, 3, 1, 4, 0, 2, 3)[(i + j) % 7] if (i == 5 or j == 12) else (1 if (i + j) % 3 else 0)
                if n:
                    column(m, x, y, zs, DELIANS, S5, finish="drums", drums=n)
    blocks(m, 80.0, 52.0, 0.7, 5, 857)
    blocks(m, 80.0, 88.0, 0.7, 4, 859)
    drum(m, 36.0, 112.0, 0.7, 2.6, 3.0, lying=True)
    # The Oikos of the Naxians: a long hall with a columned porch on the west.
    marble_wall(m, 90.0, 110.0, 24.0, 80.0, 0.7, 14.0, seed=861)
    for x in (93.0, 100.0, 107.0):
        column(m, x, 84.0, 0.7, replace(POROS_NAOS, material="marble", H=4.6), S5)
    slab(m, 89.0, 111.0, 80.0, 86.5, 12.2, 14.0, "marble", tone=0.1)
    tiled_roof(m, 88.5, 111.4, 23.0, 87.0, 14.0, 5.0, axis="y", material="terracotta", seed=863)
    pediment(m, "+y", 88.5, 111.4, 23.0, 87.0, 14.0, 5.0, POROS_NAOS, S5, subject=None, akroteria="floral")
    # The Naxian colossus beside the Oikos, on its inscribed base.
    slab(m, 96.0, 106.0, 98.0, 108.0, 0.7, 4.2, "marble_rough", tone=M.ashlar(1.4, 4.0, 865))
    bronze_statue(m, KOUROS, 101.0, 103.0, 4.2, 22.0, material="marble", keep=())
    # The archaic temple of Artemis (north-west).
    ta = Temple(order=replace(POROS_NAOS, material="marble_rough", H=4.4), axis="y", cols=(2, 2), steps=(1.0, 1.0),
                tread=0.8, edge=2.2, peripteral=False, cella=(2.0, 5.0), porch="antis",
                pediments=("small", "small"), roof="terracotta", seed=867)
    temple(m, ta, S5, 8.0, 34.0, 114.0, 148.0, z0=0.7)
    altar(m, 56.0, 136.0, 0.7, 8.0, 5.0, 3.2, fire=True, material="marble")
    for (x, y) in ((76.0, 116.0), (82.0, 124.0), (40.0, 150.0)):
        slab(m, x - 1.0, x + 1.0, y - 2.0, y + 2.0, 0.7, 7.0, "marble", tone=0.2)


def _delos_landmark():
    walk = sorted(set([(7, y) for y in range(10)] + [(x, 9) for x in range(3, 8)] + [(x, 8) for x in range(4, 8)]))
    return Landmark((8, 10), (0, 56), ref("delos_sanctuary"), walk=walk,
                    slots={"pray": [{"t": [4, 8], "face": "-x"}, {"t": [5, 9], "face": "-y"}],
                           "priest": [{"t": [3, 9], "face": "-x"}],
                           "pilgrim": [{"t": [7, 3], "face": "-x"}, {"t": [7, 6], "face": "-x"}]},
                    district=22)


def _lion(m, x, y, z, h, seed):
    """One of the Naxian lions (about 600 BC): lean and long-legged, sitting up on its haunches
    with straight forelegs, the head raised, the jaws open, facing +x."""
    s = h / 17.0
    def e(c, r, mat="marble_rough"):
        ellipsoid(m, (x + c[0] * s, y + c[1] * s, z + c[2] * s), (r[0] * s, r[1] * s, r[2] * s), mat,
                  tone=lambda X, Y, Z: (value_noise(X, Y, Z, 0.9, seed) - 0.5) * 1.1)
    e((-3.0, 0.0, 3.4), (3.4, 2.6, 3.4))           # haunches
    e((-0.6, 0.0, 7.2), (3.0, 2.1, 4.8))           # body rising
    e((1.6, 0.0, 10.6), (2.6, 2.3, 2.6))           # chest
    e((2.8, 0.0, 13.6), (2.3, 1.9, 2.1))           # head
    e((4.8, 0.0, 13.0), (1.4, 1.1, 1.0))           # muzzle
    carve(m, (x + 4.4 * s, x + 6.6 * s, y - 0.9 * s, y + 0.9 * s, z + 12.5 * s, z + 13.0 * s))   # open jaws
    for side in (-1, 1):
        rod(m, (x + 2.4 * s, y + side * 1.2 * s, z), (x + 2.0 * s, y + side * 1.2 * s, z + 9.5 * s), 0.85 * s,
            "marble_rough")
        e((-3.4, side * 2.0, 1.0), (2.6, 0.8, 1.0))     # hind paws folded
    rod(m, (x - 6.0 * s, y + 1.5 * s, z + 0.5), (x - 2.0 * s, y + 3.0 * s, z + 0.5), 0.5 * s, "marble_rough")


def naxian_lions(m):
    """The terrace of the lions on Delos: a row of marble lions dedicated by the Naxians about
    600 BC (nine to sixteen in all; nine here), seated on their haunches on rectangular bases
    along a low terrace, facing the sacred lake."""
    slab(m, 2.0, 30.0, 0.0, 128.0, 0.0, 1.2, "marble_rough", tone=M.ashlar(1.2, 6.0, 871, spread=0.3))
    for i, y in enumerate(np.linspace(8.0, 120.0, 9)):
        slab(m, 9.0, 23.0, y - 4.0, y + 4.0, 1.2, 4.2, "marble_rough", tone=M.ashlar(1.5, 4.0, 873 + i, spread=0.4))
        _lion(m, 15.0, y, 4.2, 18.0, 875 + i)


def _lions_landmark():
    return Landmark((2, 8), (0, 28), ref("naxian_lions"), slots={"look": [{"t": [2, 3], "face": "-x"},
                                                                           {"t": [2, 5], "face": "-x"}]},
                    district=22)


# ---------------------------------------------------------------- Ephesus

ARTEMIS = Order("ionic", D=1.7, H=15.0, upper=0.85, flutes=40, material="marble")


def artemision(m):
    """The archaic temple of Artemis at Ephesus as it stood in 432 BC (begun about 560 with
    Croesus's gifts; Pliny's 120 years of building put its last work near this date; burned in
    356): a dipteral Ionic temple of marble on two steps, eight columns across the west front
    and twenty-one down each flank in the outer ring, an inner ring within; the lowest drums
    of the front columns carved with figures (Croesus's columnae caelatae), Ionic capitals with
    broad volutes, an architrave and a dentil course under the tall sima carved with figures
    and pierced by lion-head spouts. Whether the sekos was roofed or open is debated; it is
    shown under a gabled tile roof."""
    seed = 881
    (sx0, sx1, sy0, sy1), zs = crepidoma(m, 2.0, 126.0, 2.0, 254.0, 0.0, (1.6, 1.6), 1.6, "marble", seed)
    e = 4.2
    ax = np.linspace(sx0 + e, sx1 - e, 8)
    ay = np.linspace(sy0 + e, sy1 - e, 21)
    pitch_x, pitch_y = ax[1] - ax[0], ay[1] - ay[0]
    cols = [(x, y) for x in ax for y in ay if x in (ax[0], ax[-1]) or y in (ay[0], ay[-1])]
    inner = [(x, y) for x in ax[1:-1] for y in ay[1:-1] if x in (ax[1], ax[-2]) or y in (ay[1], ay[-2])]
    for (x, y) in cols + inner:
        column(m, x, y, zs, ARTEMIS, SA, face="y" if x in (ax[0], ax[-1]) else "x")
    # Columnae caelatae: the lowest drum of each front column carved with a ring of figures.
    r0 = ARTEMIS.r(SA)
    for (x, y) in cols + inner:
        if y in (ay[-1], ay[-2], ay[0]):
            fill(m, (x - r0 - 1, x + r0 + 1, y - r0 - 1, y + r0 + 1, zs + 1.8, zs + 6.0), "marble",
                 lambda X, Y, Z, x=x, y=y: (np.hypot(X - x, Y - y) < r0 + 0.5),
                 tone=lambda X, Y, Z, x=x, y=y: 0.5 * (np.sin(np.arctan2(Y - y, X - x) * 14.0) > 0.3) - 0.35 *
                 ((Z - zs) % 2.1 < 0.5) - 0.2)
    # The sekos walls inside the inner ring.
    cx0, cx1 = ax[2] - 2.0, ax[-3] + 2.0
    cy0, cy1 = ay[3], ay[-3]
    H = SA.v(ARTEMIS.H)
    for w in ((cx0, cx0 + 2.4, cy0, cy1), (cx1 - 2.4, cx1, cy0, cy1), (cx0, cx1, cy0, cy0 + 2.4)):
        marble_wall(m, *w, zs, zs + H, seed=seed + 1)
    # The pronaos at the west: two rows of columns before the sekos door.
    for x in np.linspace(cx0 + 4.0, cx1 - 4.0, 4):
        for y in (ay[-3] + pitch_y * 0.5, ay[-2] - pitch_y * 0.1):
            column(m, x, y, zs, ARTEMIS, SA, face="x")
    # Entablature: architrave in three fasciae, dentils, the carved sima with lion spouts.
    rt = ARTEMIS.r(SA) * ARTEMIS.upper + 0.4
    box = (ax[0] - rt, ax[-1] + rt, ay[0] - rt, ay[-1] + rt)
    za = zs + H
    for i, (dz, out) in enumerate(((1.4, 0.0), (1.4, 0.35), (1.6, 0.7))):
        slab(m, box[0] - out, box[1] + out, box[2] - out, box[3] + out, za, za + dz, "marble",
             tone=0.25 * (i % 2) - 0.1)
        za += dz
    def dent(X, Y, Z):
        return ((np.floor(X / 1.1) + np.floor(Y / 1.1)) % 2) == 0
    fill(m, (box[0] - 1.6, box[1] + 1.6, box[2] - 1.6, box[3] + 1.6, za, za + 1.3), "marble", dent, tone=0.3)
    slab(m, box[0] - 1.0, box[1] + 1.0, box[2] - 1.0, box[3] + 1.0, za, za + 1.3, "marble", tone=-0.4)
    za += 1.3
    slab(m, box[0] - 2.2, box[1] + 2.2, box[2] - 2.2, box[3] + 2.2, za, za + 1.0, "marble", tone=0.35)
    za += 1.0
    # The sima: a parapet of carved figures (painted) along the flanks and the fronts.
    sb = (box[0] - 2.2, box[1] + 2.2, box[2] - 2.2, box[3] + 2.2)
    for face in ("+x", "-x", "+y", "-y"):
        fill(m, face_box(face, *sb, za, za + 3.6, 0, 400.0, 0.0, 1.0), "marble",
             tone=lambda X, Y, Z: 0.4 * (np.sin((X + Y) * 2.2) > 0.4) - 0.2)
        paint_band(m, face, (*sb, za, za + 3.6), za + 2.8, za + 3.6, "egg_dart", ["eblue", "cinnabar"], out=0.2)
        paint_band(m, face, (*sb, za, za + 3.6), za + 0.0, za + 0.6, "beads", ["gold", "cinnabar"], out=0.2)
    for x in np.arange(sb[0] + 4.0, sb[1] - 2.0, pitch_x):
        for yy in (sb[3] + 0.6, sb[2] - 0.6):
            ellipsoid(m, (x, yy, za + 1.6), (1.0, 0.8, 0.9), "marble", tone=0.4)
    for y in np.arange(sb[2] + 4.0, sb[3] - 2.0, pitch_y):
        ellipsoid(m, (sb[1] + 0.6, y, za + 1.6), (0.8, 1.0, 0.9), "marble", tone=0.4)
    # The roof: a low gable along the length, the fronts with plain tympana and akroteria.
    half = (sb[1] - sb[0]) / 2
    rise = half * 0.26
    fill(m, (box[0] + 2.0, box[1] - 2.0, box[2] + 2.0, box[3] - 2.0, za - 0.5, za + rise), "marble",
         lambda X, Y, Z: Z < za + rise * (1 - np.abs(X - (sb[0] + sb[1]) / 2) / half) - 1.5, tone=-0.3)
    tiled_roof(m, sb[0], sb[1], sb[2], sb[3], za + 3.0, rise, axis="y", material="terracotta", seed=seed + 3)
    for face in ("-y", "+y"):
        pediment(m, face, sb[0], sb[1], sb[2], sb[3], za + 3.0, rise, ARTEMIS, SA, subject=None, ground="marble",
                 akroteria="floral")


def _artemision_landmark():
    return Landmark((8, 16), (0, 76), ref("artemision"),
                    slots={"pray": [{"t": [3, 16], "face": "-y"}, {"t": [5, 16], "face": "-y"}],
                           "priest": [{"t": [4, 16], "face": "-y"}]}, district=23)


LANDMARKS = {
    "athens.delphi_apollo": _delphi_landmark(),
    "athens.athenian_treasury": _treasury_landmark(),
    "athens.corinth_apollo": _corinth_landmark(),
    "athens.acrocorinth_summit": _acro_landmark(),
    "athens.diolkos": _diolkos_landmark(),
    "athens.delos_sanctuary": _delos_landmark(),
    "athens.naxian_lions": _lions_landmark(),
    "athens.artemision": _artemision_landmark(),
}
