"""Babylon in spring c. 470 BC (world.md §4.3; persepolis.md §3.7): the Ishtar Gate, the
Processional Way, the double inner wall with its towers, a glazed lion wall for lining the way,
and Etemenanki. Grid axes as everywhere in the set: +x south, +y west, the camera sees the
south and west faces. The gate and the way are drawn at s = 0.5 (one tile 8 m), Etemenanki at
s = 0.35 (one tile 11.4 m) so its 91.5 m base and the south stair fit its 12 x 12 tiles.

Sources (out/reports/art-waypoints.md): Koldewey's excavations as summarised by the Pergamon
Museum's reconstruction (blue glazed ground, yellow-brown aurochs and white-and-yellow
mušḫuššu in alternating rows, rosette borders; the lions of the way white with yellow manes on
blue above an orange border); the Esagila tablet's stages as read by Schmid (91.5 m square
base 33 m high, then 78, 60, 51, 42 and 33 m squares, the temple on top) with the triple stair
on the south side; Nebuchadnezzar's inscriptions for the blue-glazed upper temple.
"""

import numpy as np

import materials as M
import relief as R
from arch import Scale, brick_tone, carve, face_box, face_frame, face_length, fill, merlons, rod, slab, stair
from setbuild import Item, Landmark
from voxel import Model, hash01, value_noise

T = 16
SB = Scale(0.5)                 # the gate, the way and the walls
SE = Scale(0.35)                # Etemenanki


def ref(fn, **kw):
    return ("sets.parsa.babylon", fn, tuple(sorted(kw.items())))


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


# ---------------------------------------------------------------- glazed brick

def reeds(seed, every=4.0):
    """Mudbrick laid in courses with a dark layer of reed matting every few courses, as the
    excavators found in Babylon's walls and towers."""
    b = brick_tone(1.0, 2.6, seed)

    def tone(X, Y, Z):
        return b(X, Y, Z) * 0.6 - 0.9 * ((Z % every) < 0.45) + (value_noise(X + Y, Y - X, Z, 9.0, seed) - 0.5) * 0.5
    return tone


def glazed_mass(m, x0, x1, y0, y1, z1, seed, z0=0.0, foot=1.6):
    """A brick mass faced with blue glazed brick above a foot of plain baked brick set in
    bitumen."""
    slab(m, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, z0, z0 + foot, "cream", tone=brick_tone(0.8, 2.4, seed))
    slab(m, x0, x1, y0, y1, z0 + foot, z1, "glaze_blue", tone=M.glazed(1.0, 2.2, seed))


BULL = {"lion": "glaze_yellow", "gold": "lapis", "white_paint": "glaze_yellow"}
DRAGON = {"lion": "white_paint", "white_paint": "glaze_yellow", "gold": "glaze_yellow"}


def beast_rows(m, face, box, s0, s1, z_lo, z_hi, seed, toward=1, pitch=8.0, first=0, sunk=False):
    """Rows of striding beasts in relief on the glazed face of `box` between s0..s1 and
    z_lo..z_hi: aurochs and mušḫuššu in alternate rows (`first` picks the top row's beast),
    walking toward +s (toward=1) or -s, centred in their span and staggered row to row, with
    a band of rosettes along the top."""
    W = int(round((s1 - s0) * 2))
    if W < 22:
        return
    bands = R.image(W, 8)
    for x in range(1, W - 7, 9):
        R.stamp(bands, R.ROSETTE, x, 1)
    bands[0, :] = "G"
    R.emboss(m, face, box, s0, z_hi, bands, colours={"petal": "white_paint", "heart": "glaze_yellow",
                                                       "gold": "glaze_yellow"}, sunk=sunk)
    n = 0
    z = z_hi - 6.0
    while z - 5.0 >= z_lo:
        beast = R.GLAZE_BULL if (n + first) % 2 == 0 else R.GLAZE_DRAGON
        cols = BULL if (n + first) % 2 == 0 else DRAGON
        st = beast if toward > 0 else R.mirror(beast)
        img = R.image(W, len(st))
        bw = len(st[0])
        count = max(1, (W + 6) // (bw + 10))
        span = count * bw + (count - 1) * 10
        x = (W - span) // 2 + (3 if n % 2 and W - span > 8 else 0)
        for _ in range(count):
            R.stamp(img, st, x, 0)
            x += bw + 10
        R.emboss(m, face, box, s0, z, img, colours=cols, sunk=sunk)
        z -= pitch
        n += 1


def glazed_merlons(m, x0, x1, y0, y1, z, h, sides=("+x", "-x", "+y", "-y")):
    M.parapet(m, x0, x1, y0, y1, z, h, material="glaze_blue", sides=sides, pitch=h * 1.3)


# ---------------------------------------------------------------- the Ishtar Gate

ARCH_W = 32.0                   # the passage spans the two walk tiles (dy 2..3)
SPRING = 25.0                   # springing above the walk headroom (24 du)


def _arch(Y, Z, cy, w, spring, rise):
    """Inside an arched opening of width w centred on cy: a jamb to `spring`, then a
    semi-elliptical vault of `rise`."""
    u = (Y - cy) / (w / 2)
    return (np.abs(u) < 1) & ((Z < spring) | (((Z - spring) / rise) ** 2 + u ** 2 < 1))


def _gate_body(m, x0, x1, y0, y1, h, towers, tower_h, rise, seed, faces_seen):
    """One gate of the pair: a glazed curtain across the whole width with the arched passage
    through it, two towers flanking the passage, beasts on every face the camera sees."""
    cy = 48.0
    glazed_mass(m, x0, x1, y0, y1, h, seed)
    glazed_merlons(m, x0, x1, y0, y1, h, 4.0)
    M.roof(m, x0 + 1.2, x1 - 1.2, y0 + 1.2, y1 - 1.2, h, seed=seed, hatches=0, rollers=0, base=-0.6)
    for (tx0, tx1, ty0, ty1) in towers:
        glazed_mass(m, tx0, tx1, ty0, ty1, tower_h, seed + 1)
        glazed_merlons(m, tx0, tx1, ty0, ty1, tower_h, 4.0)
        M.roof(m, tx0 + 1.2, tx1 - 1.2, ty0 + 1.2, ty1 - 1.2, tower_h, seed=seed, hatches=0, rollers=0, base=-0.6)
        # Yellow and white edge bands down the tower corners, framing the rows of beasts.
        for face in ("+x", "+y"):
            L = face_length(face, tx0, tx1, ty0, ty1)
            for s0 in (0.0, L - 1.6):
                fill(m, face_box(face, tx0, tx1, ty0, ty1, 1.6, tower_h, s0, s0 + 1.6, -0.4, 0.3), "glaze_yellow",
                     tone=lambda X, Y, Z: M.glazed(1.0, 2.2, seed)(X, Y, Z) + 0.6 * ((Z % 4.0) < 2.0))
    # The passage, vaulted: carved through curtain and towers' inner flanks.
    carve(m, (x0 - 4, x1 + 4, cy - ARCH_W / 2, cy + ARCH_W / 2, 0.0, SPRING + rise),
          lambda X, Y, Z: _arch(Y, Z, cy, ARCH_W, SPRING, rise))
    # The archivolt on the south face: a yellow and a white band round the vault and down the jambs.
    for (r0, r1, mat) in ((0.0, 1.4, "glaze_yellow"), (1.4, 2.6, "white_paint")):
        def ring(X, Y, Z, r0=r0, r1=r1):
            inner = _arch(Y, Z, cy, ARCH_W + 2 * r0, SPRING, rise + r0)
            outer = _arch(Y, Z, cy, ARCH_W + 2 * r1, SPRING, rise + r1)
            return outer & ~inner
        fill(m, (x1 - 0.5, x1 + 0.6, cy - ARCH_W / 2 - 3, cy + ARCH_W / 2 + 3, 1.6, SPRING + rise + 3), mat,
             ring, tone=M.glazed(1.0, 2.2, seed + 3), only_empty=False)
    # Beasts: on the curtain between and beside the towers, and on the towers, walking toward
    # the passage; the passage walls carry them too.
    for face in faces_seen:
        if face == "+x":
            spans = []
            edges = sorted([y0, y1] + [v for t in towers for v in (t[2], t[3])])
            for a, b in zip(edges[0::2], edges[1::2]):
                if not a < cy < b:                      # the passage itself carries no relief
                    spans.append((x0, x1, y0, y1, a, b, h))
            for (tx0, tx1, ty0, ty1) in towers:
                spans.append((tx0, tx1, ty0, ty1, ty0, ty1, tower_h))
            for (bx0, bx1, by0, by1, a, b, top) in spans:
                if b - a < 11:
                    continue
                box = (bx0, bx1, by0, by1, 0, top)
                s0, s1 = by1 - b, by1 - a                 # +x face: s runs toward -y
                toward = 1 if (a + b) / 2 > cy else -1    # west of the passage they walk east
                beast_rows(m, "+x", box, s0 + 0.8, s1 - 0.8, 3.0, top - 1.0, seed, toward)
        else:   # the west end
            beast_rows(m, "+y", (x0, x1, y0, y1, 0, h), 0.8, x1 - x0 - 0.8, 3.0, h - 1.0, seed, 1, first=1)
            for (tx0, tx1, ty0, ty1) in towers:
                if ty1 >= y1 - 0.1:
                    beast_rows(m, "+y", (tx0, tx1, ty0, ty1, 0, tower_h), 0.8, tx1 - tx0 - 0.8, 3.0,
                               tower_h - 1.0, seed, 1)
    # The passage's west wall (its face looks east, +y side of the east jamb is hidden; the
    # east wall's face looks west and shows through the arch).
    jb = (x0, x1, cy - ARCH_W / 2 - 8.0, cy - ARCH_W / 2, 0, SPRING)
    beast_rows(m, "+y", jb, 0.8, x1 - x0 - 0.8, 3.0, SPRING - 1.0, seed + 5, -1, pitch=8.0, first=1, sunk=True)


def ishtar_gate(m):
    """The double gate of Nebuchadnezzar II (c. 575 BC) as it stood under Xerxes: the smaller
    outer gate in the outer wall (north) and the taller main gate in the inner wall (south,
    toward the camera), each a glazed-brick curtain with towers flanking an arched passage,
    the blue ground set with rows of aurochs and mušḫuššu in relief, rosette borders, stepped
    merlons. The passage is two tiles wide so the Royal Road's walkers pass through."""
    cy = 48.0
    # Paving through the passage and the court: limestone slabs in bitumen.
    slab(m, 0.0, 64.0, cy - ARCH_W / 2, cy + ARCH_W / 2, 0.0, 0.5, "limestone", tone=M.paving(2.2, 2.2, 601))
    # The outer (front) gate: lower, its towers projecting north (hidden).
    _gate_body(m, 4.0, 27.0, 5.0, 91.0, 40.0, [(0.0, 30.0, 18.0, cy - ARCH_W / 2), (0.0, 30.0, cy + ARCH_W / 2, 78.0)],
               50.0, 9.0, 603, ("+x",))
    # The court between the gates is open; the main (inner) gate: taller, deeper, its towers
    # projecting both ways.
    _gate_body(m, 36.0, 61.0, 0.0, 96.0, 56.0, [(33.0, 64.0, 13.0, cy - ARCH_W / 2), (33.0, 64.0, cy + ARCH_W / 2, 83.0)],
               68.0, 14.0, 607, ("+x", "+y"))
    # Bronze-sheathed cedar door leaves folded back into the passage's outer reveals (hidden
    # in the jambs, so the walk tiles stay clear); bronze pivot shoes show at the foot.
    for y in (cy - ARCH_W / 2 - 1.2, cy + ARCH_W / 2 + 0.2):
        slab(m, 61.0, 63.0, y, y + 1.0, 0.0, 2.0, "bronze", tone=0.2)


def _ishtar_landmark():
    walk = tiles(0, 3, 2, 3)
    return Landmark((4, 6), (0, 78), ref("ishtar_gate"), walk=walk,
                    slots={"guard": [{"t": [4, 1], "face": "+x"}, {"t": [4, 4], "face": "+x"}],
                           "admire": [{"t": [5, 2], "face": "-x"}, {"t": [5, 3], "face": "-x"}]},
                    district=7)


# ---------------------------------------------------------------- the Processional Way

def processional_way(m):
    """Aj-ibur-šapû south of the gate: a raised roadbed paved down the middle with big
    limestone slabs and along both margins with smaller slabs of red breccia, all laid in
    bitumen (the slabs bore Nebuchadnezzar's name on their hidden edges), a kerb of baked
    brick and a gutter at each side."""
    L = 14 * T
    breccia = M.paving(1.4, 1.3, 613)
    stone = M.paving(2.1, 2.1, 615, joint=0.35)
    slab(m, 0.0, L, 1.6, 30.4, 0.0, 0.9, "hematite",
         tone=lambda X, Y, Z: breccia(X, Y, Z) * 0.8 - 0.5 + (hash01(np.floor(X / 0.4).astype(np.int64),
                                                               np.floor(Y / 0.4).astype(np.int64), 7) - 0.5) * 0.7)
    slab(m, 0.0, L, 7.0, 25.0, 0.0, 0.95, "cream",
         tone=lambda X, Y, Z: stone(X, Y, Z) - 0.35 * ((Y > 12.0) & (Y < 20.0)) -
         0.3 * (value_noise(X, Y, Z, 5.0, 619) > 0.62))
    for y0, y1 in ((1.0, 1.6), (30.4, 31.0)):
        slab(m, 0.0, L, y0, y1, 0.0, 0.3, "ink", tone=-0.2)
    for y0, y1 in ((0.0, 1.0), (31.0, 32.0)):
        slab(m, 0.0, L, y0, y1, 0.0, 0.95, "cream", tone=brick_tone(0.6, 1.6, 617))


def _way_landmark():
    return Landmark((14, 2), (0, 2), ref("processional_way"), walk=tiles(0, 13, 0, 1), district=7)


# ---------------------------------------------------------------- walls and towers

def _lion_band(m, face, box, L, z_top, flip, seed):
    """A glazed lion frieze: rosettes above, one striding lion per tile (white with a yellow
    mane, or yellow with a red mane), an orange-brown band below."""
    W = int(round(L * 2))
    img = R.image(W, 22)
    img[0, :] = "G"
    for x in range(1, W - 6, 9):
        R.stamp(img, R.ROSETTE, x, 1)
    img[8, :] = "G"
    st = R.mirror(R.GLAZE_LION) if flip else R.GLAZE_LION
    cmap = {}
    for i, x in enumerate(range(4, W - len(st[0]) + 1, 32)):
        cols = {"lion": "white_paint", "mane": "glaze_yellow"} if (i + seed) % 2 == 0 else \
            {"lion": "glaze_yellow", "mane": "cinnabar"}
        R.stamp(img, st, x, 10, cols, cmap)
    img[21, :] = "G"
    R.emboss(m, face, box, 0.0, z_top, img, colours={"petal": "white_paint", "heart": "glaze_yellow",
                                                      "gold": "glaze_yellow", "white_paint": "glaze_yellow"},
             cmap=cmap)
    fill(m, face_box(face, *box[:4], z_top - 14.0, z_top - 11.0, 0, L, -0.2, 0.4), "cinnabar",
         tone=M.glazed(1.0, 2.2, seed))


def lion_wall(v, frame, frames, k):
    """A stretch of the glazed walls that lined the Processional Way: baked brick faced with
    blue glaze, a frieze of striding lions on both faces walking toward the gate (-x when the
    wall runs along x), rosettes, an orange band, stepped merlons."""
    m = Model.empty(-1, 17, -1, 17, 0, 24, k=k)
    along_x = bool(v & 10) and not (v & 5)
    t = 3.6
    if along_x:
        x0, x1, y0, y1 = (0.0 if v & 8 else 8.0 - t), (16.0 if v & 2 else 8.0 + t), 8.0 - t, 8.0 + t
    else:
        x0, x1, y0, y1 = 8.0 - t, 8.0 + t, (0.0 if v & 1 else 8.0 - t), (16.0 if v & 4 else 8.0 + t)
    if not along_x and not (v & 5):     # a lone piece runs along x like the way
        x0, x1, y0, y1 = 0.0, 16.0, 8.0 - t, 8.0 + t
        along_x = True
    glazed_mass(m, x0, x1, y0, y1, 18.0, 621)
    box = (x0, x1, y0, y1, 0, 18.0)
    faces = ("+y", "-y") if along_x else ("+x", "-x")
    for f in faces:
        _lion_band(m, f, box, face_length(f, x0, x1, y0, y1), 15.0, f in ("+y", "-x"), 0)
    sides = faces + tuple(f for f, ok in (("+x", x1 < 16), ("-x", x0 > 0), ("+y", y1 < 16), ("-y", y0 > 0))
                          if ok and f not in faces)
    glazed_merlons(m, x0, x1, y0, y1, 18.0, 3.0, sides=sides)
    return m


def _wall_run(m, x0, x1, y0, y1, h, seed):
    slab(m, x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, 0.0, 2.0, "cream", tone=brick_tone(0.8, 2.4, seed))
    slab(m, x0, x1, y0, y1, 2.0, h, "mudbrick", tone=reeds(seed))


def babylon_wall(v, frame, frames, k):
    """A piece of Babylon's double inner wall: Imgur-Enlil, thick, and Nemetti-Enlil, thinner,
    with the military road between, both of mudbrick in courses with reed-mat layers on a
    baked-brick foot, stepped merlons. Two rows of pieces side by side make the pair: the row
    with its neighbour to the south (+x) is the outer wall, the one with it to the north the
    inner; a piece runs along y unless it continues along x on both sides."""
    m = Model.empty(-1, 17, -1, 17, 0, 40, k=k)
    x_run = (v & 10) == 10 and (v & 5) != 5
    if x_run:
        boxes = [(0.0, 16.0, 3.0, 13.0)]
        sides = ("+y", "-y")
    else:
        if v & 2 and not v & 8:          # the outer wall, its road to the south
            x0, x1 = 3.0, 9.0
        elif v & 8 and not v & 2:        # the inner wall, broad
            x0, x1 = 1.0, 14.0
        else:
            x0, x1 = 3.0, 13.0
        boxes = [(x0, x1, 0.0, 16.0)]
        sides = ("+x", "-x")
    for b in boxes:
        _wall_run(m, *b, 31.0, 631)
        merlons(m, *b, 31.0, 4.0, "mudbrick", pitch=4.6, sides=sides, thick=1.3)
        fill(m, (b[0] + 1.3, b[1] - 1.3, b[2], b[3], 31.0, 31.6), "mudbrick", tone=0.3)
    return m


def babylon_tower(v, frame, frames, k):
    """A tower of the inner wall, 2 x 2: mudbrick with reed layers on a baked-brick foot,
    projecting over both walls, slit windows and a door onto the wall walk, stepped merlons."""
    m = Model.empty(-1, 33, -1, 33, 0, 58, k=k)
    _wall_run(m, 1.0, 31.0, 1.0, 31.0, 48.0, 641)
    for face in ("+x", "+y", "-x", "-y"):
        for z in (20.0, 34.0):
            for s in (8.0, 21.0):
                fill(m, face_box(face, 1.0, 31.0, 1.0, 31.0, z, z + 5.0, s, s + 1.5, -0.2, 2.0), "ink", tone=0.3)
    slab(m, 0.4, 31.6, 0.4, 31.6, 48.0, 49.2, "cream", tone=brick_tone(0.6, 2.0, 643))
    merlons(m, 1.0, 31.0, 1.0, 31.0, 49.2, 5.0, "mudbrick", pitch=5.6, thick=1.4)
    M.roof(m, 2.4, 29.6, 2.4, 29.6, 49.2, seed=645, hatches=1, rollers=0, base=-0.4)
    return m


# ---------------------------------------------------------------- Etemenanki

# Stages after the Esagila tablet (Schmid's reading), in metres: (side, height). The sixth
# stage's dimensions are missing from the tablet and are interpolated.
STAGES = ((91.5, 33.0), (78.0, 18.0), (60.0, 6.0), (51.0, 6.0), (42.0, 6.0), (33.0, 6.0))
TEMPLE = (24.0, 21.0, 15.0)


def _stage_face(m, box, z0, z1, seed, pitch):
    """A stage's mantle of buff baked brick: shallow buttresses with recesses between (the
    Babylonian temple façade), dark bitumen courses every few rows, weathering streaks; a
    brick-paved terrace on top with a bitumen-sealed edge."""
    x0, x1, y0, y1 = box
    base = brick_tone(0.9, 2.6, seed)

    def tone(X, Y, Z):
        streak = (value_noise(X * 0.2 + Y * 0.2, X - Y, Z * 0.15, 6.0, seed) - 0.5) * 0.7
        return base(X, Y, Z) * 0.7 + streak - 0.7 * ((Z % 7.0) < 0.5)
    slab(m, x0, x1, y0, y1, z0, z1, "mudbrick", tone=tone)
    for face in ("+x", "+y", "-x", "-y"):
        L = face_length(face, x0, x1, y0, y1)
        for s in np.arange(pitch * 0.5, L - pitch * 0.4, pitch):
            fill(m, face_box(face, x0, x1, y0, y1, z0 + 1.5, z1 - 1.0, s - pitch * 0.18, s + pitch * 0.18, -0.9, 0.0),
                 "mudbrick", tone=lambda X, Y, Z: base(X, Y, Z) * 0.6 + 0.3)
        fill(m, face_box(face, x0, x1, y0, y1, z1 - 1.2, z1, 0, L, -0.3, 0.6), "ink", tone=0.1)
    fill(m, (x0 + 0.6, x1 - 0.6, y0 + 0.6, y1 - 0.6, z1 - 0.5, z1), "mudbrick", only_solid=True,
         tone=lambda X, Y, Z: M.paving(1.6, 1.6, seed)(X, Y, Z) * 0.6 - 0.2)


def etemenanki(m):
    """The ziggurat of Marduk as it stood (its state under Xerxes is debated; it is shown
    standing): six brick stages on a 91.5 m square base, each a mantle of baked brick with
    buttressed faces over a mudbrick core, low parapets on the terraces, and on top the
    temple faced with blue glazed brick under a cedar roof. On the south side, toward the
    camera, the triple stair: a central flight projecting from the face to the first terrace
    with two lateral flights climbing along the face to meet it at a gatehouse, and small
    flights up the higher stages."""
    cx = 64.0 + 1.0           # the tower's centre line across (x); the stair runs south of it
    cy = 96.0
    z = 0.0
    tops = []
    for i, (side, h) in enumerate(STAGES):
        a = SE.h(side) / 2
        H = SE.v(h)
        box = (cx - a, cx + a, cy - a, cy + a)
        _stage_face(m, box, z, z + H, 651 + i, 9.0 if i < 2 else 6.0)
        z += H
        tops.append((box, z))
        # A low brick parapet round each terrace edge.
        M.parapet(m, box[0], box[1], box[2], box[3], z, 2.2, material="mudbrick", pitch=3.0)
    # The temple on the top: glazed blue, gold-framed door to the south, cedar beam ends.
    tw, td, th = SE.h(TEMPLE[1]) / 2, SE.h(TEMPLE[0]) / 2, SE.v(TEMPLE[2])
    tb = (cx - tw, cx + tw, cy - td, cy + td)
    glazed_mass(m, *tb, z + th, 661, z0=z, foot=0.8)
    for face in ("+x", "+y", "-x", "-y"):
        L = face_length(face, *tb)
        for s in np.arange(3.0, L - 2.0, 5.0):
            fill(m, face_box(face, *tb, z + 1.0, z + th - 2.0, s, s + 1.8, -0.7, 0.0), "glaze_blue",
                 tone=M.glazed(1.0, 2.2, 663))
        band = R.image(int(L * 2), 8)
        for x in range(1, int(L * 2) - 7, 9):
            R.stamp(band, R.ROSETTE, x, 1)
        R.emboss(m, face, (*tb, z, z + th), 0.0, z + th - 0.8, band,
                 colours={"petal": "white_paint", "heart": "gold"})
    M.beam_ends(m, "+x", (*tb, z, z + th), z + th - 6.0, spacing=2.6, r=0.45, out=0.7)
    M.beam_ends(m, "+y", (*tb, z, z + th), z + th - 6.0, spacing=2.6, r=0.45, out=0.7)
    slab(m, tb[0] - 0.6, tb[1] + 0.6, tb[2] - 0.6, tb[3] + 0.6, z + th, z + th + 1.0, "cedar", tone=0.2)
    M.parapet(m, tb[0] - 0.6, tb[1] + 0.6, tb[2] - 0.6, tb[3] + 0.6, z + th + 1.0, 2.6, material="glaze_blue",
              pitch=3.2, cap="gold")
    door = face_box("+x", *tb, z, z + 9.0, td - 3.0, td + 3.0, -0.6, 1.5)
    carve(m, door)
    fill(m, face_box("+x", *tb, z, z + 9.0, td - 3.0, td + 3.0, 1.5, 2.0), "gold",
         tone=lambda X, Y, Z: 0.5 * ((Z % 2.0) < 0.4) - 0.1)
    fill(m, face_box("+x", *tb, z + 9.0, z + 10.0, td - 4.0, td + 4.0, -0.8, 0.0), "gold", tone=0.3)
    # The triple stair on the south face of the first stage.
    (b1, z1) = tops[0]
    sx = b1[1]                                    # the south face
    sw = SE.h(9.0)                                # the central flight's width
    stair(m, sx, 192.0, cy - sw / 2, cy + sw / 2, 0.0, z1, "-x", step=0.9, material="mudbrick", parapet=1.6,
          par_h=2.4, par_mat="mudbrick")
    lw = SE.h(7.0)
    for sgn in (-1, 1):                           # the lateral flights, up along the face to the centre
        y_far = cy + sgn * (SE.h(STAGES[0][0]) / 2 - 1.0)
        y_near = cy + sgn * (sw / 2 + 4.0)
        y0, y1 = sorted((y_far, y_near))
        stair(m, sx, sx + lw, y0, y1, 0.0, z1 - 1.0, "-y" if sgn > 0 else "+y", step=0.9, material="mudbrick",
              parapet=1.4, par_h=2.2, par_mat="mudbrick")
    # The gatehouse where the three flights meet, on the first terrace's edge.
    gb = (sx - 10.0, sx + 1.0, cy - sw / 2 - 3.0, cy + sw / 2 + 3.0)
    _stage_face(m, gb, z1, z1 + 14.0, 673, 5.0)
    carve(m, (sx - 11.0, sx + 2.0, cy - 3.5, cy + 3.5, z1, z1 + 8.0),
          lambda X, Y, Z: _arch(Y, Z, cy, 7.0, z1 + 5.5, 2.5))
    M.parapet(m, *gb, z1 + 14.0, 2.4, material="mudbrick", pitch=3.0)
    # Flights up the higher stages, laid along each terrace beside the face and climbing
    # toward the axis, alternately from the east and from the west.
    for i in range(1, len(tops)):
        (bi, zi), (bp, zp) = tops[i], tops[i - 1]
        run = max(10.0, 1.25 * (zi - zp))
        if i % 2:
            y0, y1, up = cy + 5.0, cy + 5.0 + run, "-y"
        else:
            y0, y1, up = cy - 5.0 - run, cy - 5.0, "+y"
        stair(m, bi[1], min(bi[1] + 5.0, bp[1] - 0.5), y0, y1, zp, zi, up, step=0.9, material="mudbrick",
              parapet=0.8, par_h=1.6, par_mat="mudbrick")
    # Upper temple stair.
    (bt, zt) = tops[-1]
    stair(m, tb[1], bt[1] - 0.5, cy - 2.5, cy + 2.5, zt, zt + 1.0, "-x", step=0.5, material="limestone")


def _etemenanki_landmark():
    return Landmark((12, 12), (0, 170), ref("etemenanki"),
                    slots={"pray": [{"t": [12, 5], "face": "-x"}, {"t": [12, 6], "face": "-x"}],
                           "priest": [{"t": [12, 7], "face": "-x"}]}, district=7)


LANDMARKS = {
    "parsa.ishtar_gate": _ishtar_landmark(),
    "parsa.processional_way": _way_landmark(),
    "parsa.etemenanki": _etemenanki_landmark(),
}


ITEMS = {"parsa.babylon_wall": Item(babylon_wall), "parsa.babylon_tower": Item(babylon_tower),
         "parsa.lion_wall": Item(lion_wall)}
