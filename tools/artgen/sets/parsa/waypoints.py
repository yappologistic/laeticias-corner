"""The Persian waypoints of the Royal Road in spring c. 470 BC (world.md §4.3): Darius's palace
at Susa, Palace P and its garden at Pasargadae, the gates at the Halys, the guarded station at
the Persian Gates and the road head at Sardis. Grid axes: +x south, +y west; the camera sees the
south and west faces.

Susa is drawn at s = 0.4 in a plan compressed to its 12 x 14 tiles: the apadana (36 columns in
a square hall, porticoes of twelve on the north, west and east, corner towers) north of the
residence's northern range, of which two of its three courts are shown with glazed-brick
friezes of archers and lions. Pasargadae at s = 0.5: Palace P with its hall of thirty columns
and the long portico on the garden side, the garden's stone channels and basins, a pavilion.
The road stations at s = 0.5 are Achaemenid in manner; their form is not known from remains.
"""

import numpy as np

import materials as M
import relief as R
from arch import (Column, Scale, carve, column, ellipsoid, entablature, face_box, face_length, fill, halo, rod,
                  slab, stone_frame)
from setbuild import Landmark
from sets.parsa.landmarks import crown, door, frieze, standard, wall
from voxel import value_noise

T = 16
SS = Scale(0.4)                 # Susa
SP = Scale(0.5)                 # Pasargadae and the stations
LAMP = (255, 201, 92)
FIRE = (255, 154, 58)


def ref(fn, **kw):
    return ("sets.parsa.waypoints", fn, tuple(sorted(kw.items())))


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def flat_top(m, x0, x1, y0, y1, z, seed, parapet=3.0, sides=("+x", "-x", "+y", "-y"), mat="mudbrick"):
    """A plastered flat roof on a wall top, stepped merlons on the given sides."""
    M.roof(m, x0, x1, y0, y1, z, seed=seed, hatches=0, rollers=0, base=-0.5)
    if parapet:
        M.parapet(m, x0, x1, y0, y1, z, parapet, material=mat, sides=sides, pitch=parapet * 1.3)


def glazed_band(m, face, box, s0, s1, z_top, kind, seed):
    """A glazed frieze that also fits narrow walls (Susa type: archers, lions, rosettes)."""
    if s1 - s0 >= 12:
        frieze(m, face, box, s0, s1, z_top, kind, seed)


# ---------------------------------------------------------------- Susa

SUSA_COL = SS.v(19.5)           # the apadana's columns, near 20 m
SUSA_HALL = SUSA_COL + 6.0
SUSA_TOWER = SUSA_COL + 14.0
RES_H = 26.0                    # the residence's ranges
AX0, AY0 = 4.0, 59.0            # the apadana's north-east corner
TW, HS = 22.0, 61.0             # tower side, hall side


def _susa_tower(m, x0, x1, y0, y1, seed):
    wall(m, x0, x1, y0, y1, SUSA_TOWER, seed, plinth=4.0, dado_h=4.0)
    box = (x0, x1, y0, y1, 0, SUSA_TOWER)
    for face in ("+x", "+y"):
        L = face_length(face, x0, x1, y0, y1)
        for s0 in (L * 0.2, L * 0.62):
            stone_frame(m, face, box, s0, 4.0, 10.0, 16.0, kind="niche")
        stone_frame(m, face, box, L * 0.5 - 1.5, 3.0, SUSA_TOWER - 14.0, 5.0, kind="window")
        glazed_band(m, face, box, 1.5, L - 1.5, SUSA_TOWER - 1.5, "lions" if seed % 2 else "rosettes", seed)
    zt = crown(m, x0, x1, y0, y1, SUSA_TOWER, ("+x", "+y", "-x", "-y"), seed, parapet=4.0, spout_every=0)
    M.roof(m, x0 + 1, x1 - 1, y0 + 1, y1 - 1, zt - 4.0 - 1.4, seed=seed, hatches=1, rollers=0, base=-0.5)


def _susa_apadana(m):
    x0, y0 = AX0, AY0
    hx0, hx1, hy0, hy1 = x0 + TW, x0 + TW + HS, y0 + TW, y0 + TW + HS
    # The hall: red-plastered walls toward the porticoes behind which 36 columns carry the roof.
    for w, mat in (((hx0, hx0 + 5, hy0, hy1), "cinnabar"), ((hx1 - 5, hx1, hy0, hy1), "mudbrick"),
                   ((hx0, hx1, hy0, hy0 + 5), "cinnabar"), ((hx0, hx1, hy1 - 5, hy1), "cinnabar")):
        wall(m, *w, SUSA_HALL, 701, plinth=2.0, material=mat, dado_h=4.0, amount=0.3)
    westw = (hx0, hx1, hy1 - 5, hy1, 0, SUSA_HALL)
    door(m, "+y", westw, HS / 2 - 5.0, 10.0, 24.0, leaf="gold")
    for s0 in (HS * 0.16, HS * 0.74):
        door(m, "+y", westw, s0, 6.0, 18.0, leaf="bronze")
    M.curtain(m, (hx0 + HS / 2 - 7.0, hy1 + 0.5), (hx0 + HS / 2 + 7.0, hy1 + 0.5), 30.0, 0.6, "white_paint",
              fringe="purple", tied=22.0)
    frieze(m, "+y", westw, 1.0, HS - 1.0, SUSA_COL - 2.0, "archers", 703)
    zt = crown(m, hx0, hx1, hy0, hy1, SUSA_HALL, ("+x", "-x", "+y", "-y"), 705, parapet=3.5)
    M.roof(m, hx0 + 1, hx1 - 1, hy0 + 1, hy1 - 1, zt - 3.5 - 1.4, seed=707, hatches=3, rollers=1, base=-0.5)
    # Porticoes of two rows of six columns: north and east (behind), west (seen).
    pitch = HS / 6
    rows = [hx0 + pitch * (i + 0.5) for i in range(6)]
    for (bx0, bx1, by0, by1, cols, faces, beam) in (
            (x0, hx0, hy0, hy1, [(x, y) for x in (x0 + 6.0, x0 + 16.0) for y in
                                 [hy0 + pitch * (i + 0.5) for i in range(6)]], ("-x", "+y", "-y"), "y"),
            (hx0, hx1, hy1, y0 + 2 * TW + HS, [(x, y) for x in rows for y in (hy1 + 6.0, hy1 + 16.0)],
             ("+y", "+x", "-x"), "x"),
            (hx0, hx1, y0, hy0, [(x, y) for x in rows for y in (y0 + 6.0, y0 + 16.0)], ("-y", "+x", "-x"), "x")):
        c = Column(SS.h(0.8), SUSA_COL, base="bell", capital="bull", beam=beam)
        for (cx, cy) in cols:
            column(m, cx, cy, 0.0, c)
        lines = sorted({x for x, _ in cols}) if beam == "x" else sorted({y for _, y in cols})
        zr = entablature(m, bx0, bx1, by0, by1, SUSA_COL, main="y" if beam == "x" else "x", lines=lines,
                         outer=faces, seed=709)
        M.parapet(m, bx0 - 0.4, bx1 + 0.4, by0 - 0.4, by1 + 0.4, zr, 3.5, material="limestone", sides=faces,
                  stripes=((0.6, "cinnabar"), (0.6, "lapis")))
        M.roof(m, bx0, bx1, by0, by1, zr, seed=711, hatches=0, rollers=1, base=-0.5)
    # South of the hall, between the south towers: a lower closed range toward the residence.
    sx0, sx1 = hx1, hx1 + TW
    wall(m, sx0 + 1.0, sx1 - 1.0, hy0, hy1, 30.0, 713, plinth=2.0, dado_h=3.0)
    box = (sx0 + 1.0, sx1 - 1.0, hy0, hy1, 0, 30.0)
    for i in range(4):
        stone_frame(m, "+x", box, 6.0 + i * 15.0, 5.0, 0.0, 13.0, kind="door" if i % 2 else "niche", leaf="cedar")
    flat_top(m, sx0 + 1.0, sx1 - 1.0, hy0, hy1, 30.0, 715, parapet=2.6, sides=("+x",))
    for i, (tx, ty) in enumerate(((x0, y0), (x0, hy1), (hx1, y0), (hx1, hy1))):
        _susa_tower(m, tx + 0.8, tx + TW - 0.8, ty + 0.8, ty + TW - 0.8, 717 + i)
    standard(m, hx1 + TW / 2, hy1 + TW / 2, SUSA_TOWER + 2.0, h=12.0)


def _court(m, cx0, cx1, cy0, cy1, seed, door_s=None):
    """An open court: a paved floor of fired brick, its inner walls (the north one facing the
    camera, the east one too) faced with glazed friezes; doors between the courts."""
    fill(m, (cx0, cx1, cy0, cy1, 0.0, 0.5), "cream", tone=M.paving(1.8, 1.8, seed))
    carve(m, (cx0, cx1, cy0, cy1, 0.5, RES_H + 8.0))
    north = (cx0 - 10.0, cx0, cy0, cy1, 0, RES_H)
    east = (cx0, cx1, cy0 - 10.0, cy0, 0, RES_H)
    Ln, Le = cy1 - cy0, cx1 - cx0
    # Glazed brick: the archers in procession over a band of rosettes; the lions on the east wall.
    fill(m, face_box("+x", *north[:4], 2.0, RES_H - 2.0, 0, Ln, -0.4, 0.2), "glaze_blue", tone=M.glazed(1.0, 2.2, seed))
    frieze(m, "+x", north, 1.0, Ln - 1.0, RES_H - 3.0, "archers", seed)
    frieze(m, "+x", north, 1.0, Ln - 1.0, RES_H - 15.0, "rosettes", seed + 1)
    fill(m, face_box("+y", *east[:4], 2.0, RES_H - 2.0, 0, Le, -0.4, 0.2), "glaze_blue", tone=M.glazed(1.0, 2.2, seed + 2))
    frieze(m, "+y", east, 1.0, Le - 1.0, RES_H - 3.0, "lions", seed + 2)
    frieze(m, "+y", east, 1.0, Le - 1.0, RES_H - 13.0, "rosettes", seed + 3)
    if door_s is not None:
        door(m, "+x", north, door_s, 6.0, 15.0, leaf="cedar")
        door(m, "+y", east, Le / 2 - 3.0, 6.0, 15.0, leaf="cedar")


def susa_palace(m):
    """Darius's palace at Susa on its citadel mound: the apadana with bull-capital columns,
    porticoes and corner towers to the north; south of it the residence of mudbrick in the
    Babylonian manner (Darius's foundation charter names Babylonian brickmakers), its courts
    lined with glazed-brick archers, lions and rosettes, its outer faces buttressed with a
    glazed band under the merlons and the main gate toward the town."""
    _susa_apadana(m)
    rx0, rx1, ry0, ry1 = 114.0, 190.0, 4.0, 220.0
    wall(m, rx0, rx1, ry0, ry1, RES_H, 731, plinth=2.5, dado_h=3.0, amount=0.45)
    _court(m, 128.0, 176.0, 18.0, 98.0, 733, door_s=20.0)
    _court(m, 128.0, 176.0, 112.0, 206.0, 737, door_s=40.0)
    # Roofs, merlons on the outer faces and round the courts.
    for (a, b, c, d) in ((rx0, 128.0, ry0, ry1), (176.0, rx1, ry0, ry1), (128.0, 176.0, ry0, 18.0),
                         (128.0, 176.0, 98.0, 112.0), (128.0, 176.0, 206.0, ry1)):
        M.roof(m, a, b, c, d, RES_H, seed=739 + int(a + c), hatches=1, rollers=0, base=-0.5)
    M.parapet(m, rx0, rx1, ry0, ry1, RES_H, 3.0, material="mudbrick", pitch=3.9)
    for (a, b, c, d) in ((128.0, 176.0, 18.0, 98.0), (128.0, 176.0, 112.0, 206.0)):
        M.parapet(m, a - 0.8, b + 0.8, c - 0.8, d + 0.8, RES_H, 2.2, material="mudbrick", pitch=3.0)
    # Outer faces: buttresses, a glazed rosette band, windows; the gate on the south side.
    box = (rx0, rx1, ry0, ry1, 0, RES_H)
    for face in ("+x", "+y"):
        L = face_length(face, rx0, rx1, ry0, ry1)
        for s in np.arange(5.0, L - 3.0, 11.0):
            fill(m, face_box(face, rx0, rx1, ry0, ry1, 2.5, RES_H, s, s + 4.0, -1.2, 0.0), "mudbrick",
                 tone=M.mud_plaster(741, 0.4, 2.5, 3.0))
        fill(m, face_box(face, rx0, rx1, ry0, ry1, RES_H - 6.0, RES_H - 0.5, 0, L, -1.4, 0.0), "glaze_blue",
             tone=M.glazed(1.0, 2.2, 743))
        band = R.image(int(L * 2), 9)
        band[0, :] = "G"
        band[8, :] = "G"
        for x in range(1, int(L * 2) - 7, 9):
            R.stamp(band, R.ROSETTE, x, 1)
        R.emboss(m, face, _grow_face(face, box, 1.4), 0.0, RES_H - 1.0, band,
                 colours={"petal": "white_paint", "heart": "glaze_yellow", "gold": "glaze_yellow"})
        for s in np.arange(10.5, L - 6.0, 22.0):
            stone_frame(m, face, box, s, 2.4, 14.0, 4.0, kind="window")
    # The gate toward the town (its node lies south of the palace's west end).
    gs = (rx0 + 0.0, rx1, ry0, ry1, 0, RES_H)
    gate = face_box("+x", *gs[:4], 0, RES_H + 8.0, 12.0, 32.0, -3.0, 0.0)
    wall(m, *gate[:4], RES_H + 8.0, 745, plinth=2.5, dado_h=3.0)
    gb = (*gate[:4], 0, RES_H + 8.0)
    door(m, "+x", gb, 6.0, 8.0, 18.0, leaf="gold")
    frieze(m, "+x", gb, 0.8, 19.2, RES_H + 6.0, "rosettes", 747)
    M.parapet(m, *gate[:4], RES_H + 8.0, 3.0, material="mudbrick", pitch=3.9)
    halo(m, gate[1] + 1.0, (gate[2] + gate[3]) / 2, 14.0, 9.0, LAMP, 0.5)


def _grow_face(face, box, by):
    """The wall box with `face` pushed out by `by` (to emboss onto a buttressed band)."""
    x0, x1, y0, y1, z0, z1 = box
    return {"+x": (x0, x1 + by, y0, y1, z0, z1), "-x": (x0 - by, x1, y0, y1, z0, z1),
            "+y": (x0, x1, y0, y1 + by, z0, z1), "-y": (x0, x1, y0 - by, y1, z0, z1)}[face]


def _susa_landmark():
    return Landmark((12, 14), (0, 70), ref("susa_palace"),
                    slots={"guard": [{"t": [12, 11], "face": "+x"}, {"t": [12, 13], "face": "+x"}],
                           "petition": [{"t": [12, 12], "face": "-x"}]},
                    emitters={}, district=8)


# ---------------------------------------------------------------- Pasargadae

P_HALL = SP.v(11.0)             # Palace P's hall columns (about 11 m)
P_PORT = SP.v(7.0)              # the portico's columns


def _bw_column(m, x, y, h, r):
    """A Pasargadae column: a square plinth of black stone and a torus of white limestone
    under an unfluted white shaft (the two-coloured bases of Cyrus's palaces), a plain
    wooden capital block under the beam."""
    slab(m, x - r * 2.0, x + r * 2.0, y - r * 2.0, y + r * 2.0, 0.0, 1.4, "slate", tone=0.15)
    fill(m, (x - r * 1.6, x + r * 1.6, y - r * 1.6, y + r * 1.6, 1.4, 2.6), "limestone",
         lambda X, Y, Z: np.hypot(X - x, Y - y) < r * (1.6 - 0.4 * np.abs(Z - 2.0) / 0.6), tone=0.3)
    column(m, x, y, 2.6, Column(r, h - 2.6, base="plain", capital="wood", flutes=0, material="cream", paint=False))


def pasargadae_garden(m):
    """Palace P (Cyrus, finished or inscribed under Darius) facing its garden: a hall of thirty
    columns (five by six) with black-and-white column bases and mudbrick walls with stone door
    frames, a long portico of two rows of columns on the garden side with the throne seat at
    its middle, corner rooms; the garden before it laid out with narrow stone water channels
    and square basins at intervals, beds and trees between, a small columned pavilion at its
    south-west corner. The four-part layout once read into the channels is debated; the
    channels here frame the garden and run down its axis from the throne seat."""
    seed = 751
    # Palace P: the hall.
    hx0, hx1, hy0, hy1 = 10.0, 52.0, 66.0, 128.0
    wall(m, hx0, hx1, hy0, hy1, P_HALL + 5.0, seed, plinth=2.0, dado_h=3.0, dado="hematite", amount=0.45)
    hall = (hx0, hx1, hy0, hy1, 0, P_HALL + 5.0)
    for face, L in (("+x", hy1 - hy0), ("+y", hx1 - hx0)):
        door(m, face, hall, L / 2 - 4.0, 8.0, 18.0, leaf="cedar", jambs="king" if face == "+x" else None)
        for s0 in (L * 0.18, L * 0.72):
            stone_frame(m, face, hall, s0, 4.0, 16.0, 6.0, kind="window", material="cream")
    flat_top(m, hx0, hx1, hy0, hy1, P_HALL + 5.0, seed + 1, parapet=2.6)
    # The long portico on the garden side (south) and the corner rooms at its ends.
    px0, px1 = hx1, hx1 + 20.0
    py0, py1 = 18.0, 176.0
    cols = [(x, y) for x in (px0 + 5.0, px0 + 14.0) for y in np.linspace(py0 + 4.0, py1 - 4.0, 20)]
    for (x, y) in cols:
        _bw_column(m, x, y, P_PORT, 0.85)
    zr = entablature(m, px0, px1, py0, py1, P_PORT, main="y", lines=[px0 + 5.0, px0 + 14.0],
                     outer=("+x", "+y", "-y"), seed=seed + 2, fascia="cedar")
    M.roof(m, px0, px1, py0, py1, zr, seed=seed + 3, hatches=0, rollers=1, base=-0.5)
    for (y0, y1) in ((py0 - 14.0, py0), (py1, py1 + 14.0)):
        wall(m, px0 - 10.0, px1, y0, y1, P_PORT + 7.0, seed + 4, plinth=2.0, dado_h=3.0, amount=0.45)
        flat_top(m, px0 - 10.0, px1, y0, y1, P_PORT + 7.0, seed + 5, parapet=2.4)
    # Back rooms flanking the hall.
    for (y0, y1) in ((py0, hy0), (hy1, py1)):
        wall(m, hx0 + 6.0, hx1, y0, y1, P_PORT + 4.0, seed + 6, plinth=1.6, dado_h=2.0, amount=0.45)
        flat_top(m, hx0 + 6.0, hx1, y0, y1, P_PORT + 4.0, seed + 7, parapet=0)
    # The throne seat: a stone bench at the middle of the portico facing the garden.
    cy = (py0 + py1) / 2
    slab(m, px0 + 1.0, px0 + 4.0, cy - 4.0, cy + 4.0, 0.0, 3.0, "cream", tone=0.3)
    slab(m, px0 + 0.5, px0 + 1.6, cy - 4.0, cy + 4.0, 3.0, 6.5, "cream", tone=0.1)
    # The garden on the tile grid: gravel walks on the south edge, the two ends and the axis
    # from the throne seat (dy 5..6); four beds of grass and flowers with trees, framed by
    # stone channels with square basins every 14 m; a pavilion in the south-west bed.
    gx0, gx1 = 74.0, 160.0
    fill(m, (gx0, gx1, 0.0, 192.0, 0.0, 0.5), "cream", tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.2, seed) - 0.5) * 0.9 - 0.3)
    beds = [(80.0, 144.0, 16.0, 80.0), (80.0, 144.0, 112.0, 176.0)]
    for i, (bx0, bx1, by0, by1) in enumerate(beds):
        fill(m, (bx0 + 3.0, bx1 - 3.0, by0 + 3.0, by1 - 3.0, 0.0, 0.9), "grass",
             tone=lambda X, Y, Z: (value_noise(X, Y, Z * 0, 3.0, seed + 9) - 0.5) * 1.2)
        n = int((bx1 - bx0) * (by1 - by0) / 22)
        for j in range(n):
            fx = bx0 + 4.0 + (bx1 - bx0 - 8.0) * float(value_noise(j * 7.1, 1.0 + i, 2.0, 1.0, seed + 11))
            fy = by0 + 4.0 + (by1 - by0 - 8.0) * float(value_noise(3.0 + i, j * 5.3, 1.0, 1.0, seed + 13))
            ellipsoid(m, (fx, fy, 0.9), (0.6, 0.6, 0.5), ("poppy", "white_paint", "saffron", "violet")[j % 4], tone=0.2)
        # Channels on the bed's four sides with basins at intervals.
        for (a0, a1, b0, along) in ((bx0 + 1.5, bx1 - 1.5, by0 + 1.5, "x"), (bx0 + 1.5, bx1 - 1.5, by1 - 1.5, "x"),
                                    (by0 + 1.5, by1 - 1.5, bx0 + 1.5, "y"), (by0 + 1.5, by1 - 1.5, bx1 - 1.5, "y")):
            _channel(m, a0, a1, b0, along, seed + 21)
    # Trees (cypresses and planes; the garden's species are not known) in rows in the beds.
    for i, (bx0, bx1, by0, by1) in enumerate(beds):
        for j, (tx, ty) in enumerate(((bx0 + 12.0, by0 + 12.0), (bx0 + 12.0, by1 - 12.0), (bx1 - 30.0, by0 + 12.0),
                                      (bx1 - 30.0, by1 - 12.0), ((bx0 + bx1) / 2 - 8.0, (by0 + by1) / 2))):
            if (i + j) % 2:
                rod(m, (tx, ty, 0.5), (tx, ty, 6.0), 0.5, "bark")
                ellipsoid(m, (tx, ty, 17.0), (2.8, 2.8, 12.0), "leaf_dark",
                          tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.2, seed + 17) - 0.5) * 1.6)
            else:
                rod(m, (tx, ty, 0.5), (tx, ty, 10.0), 0.8, "bark")
                ellipsoid(m, (tx, ty, 14.0), (5.6, 5.6, 5.0), "leaf",
                          tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.4, seed + 19) - 0.5) * 1.6)
    _channel(m, gx0 + 2.0, gx1 - 1.0, cy, "x", seed + 23)          # the axis
    # The pavilion: four stone columns, a timber roof, in the south-west bed.
    vx, vy = 128.0, 160.0
    for (x, y) in ((vx - 7.0, vy - 7.0), (vx + 7.0, vy - 7.0), (vx - 7.0, vy + 7.0), (vx + 7.0, vy + 7.0)):
        _bw_column(m, x, y, P_PORT - 2.0, 0.8)
    zr = entablature(m, vx - 10.0, vx + 10.0, vy - 10.0, vy + 10.0, P_PORT - 2.0, main="y",
                     lines=[vx - 7.0, vx + 7.0], seed=seed + 25, fascia="cedar")
    M.roof(m, vx - 10.0, vx + 10.0, vy - 10.0, vy + 10.0, zr, seed=seed + 27, hatches=0, rollers=0, base=-0.5)


def _channel(m, a0, a1, b, along, seed):
    """A narrow channel of dressed limestone with water in it, square basins every 14 m."""
    def box(c0, c1, w):
        return (c0, c1, b - w, b + w) if along == "x" else (b - w, b + w, c0, c1)
    slab(m, *box(a0, a1, 1.0), 0.0, 0.8, "limestone", tone=M.ashlar(0.8, 2.0, seed))
    fill(m, (*box(a0, a1, 0.4), 0.0, 0.8), "water", tone=0.2)
    for c in np.arange(a0 + 6.0, a1 - 3.0, 28.0):
        slab(m, *box(c - 2.2, c + 2.2, 2.2), 0.0, 0.8, "limestone", tone=0.25)
        fill(m, (*box(c - 1.5, c + 1.5, 1.5), 0.0, 0.8), "water", tone=0.0)


def _pasargadae_landmark():
    # Walks along the garden's frame and down the axis; the beds, palace and pavilion are not
    # walked on. The south edge opens onto the road (node south of dy 9).
    walk = sorted(set([(x, y) for x in range(5, 10) for y in (5, 6)] + [(9, y) for y in range(0, 12)] +
                      [(x, 0) for x in range(5, 10)] + [(x, 11) for x in range(5, 10)]))
    return Landmark((10, 12), (0, 40), ref("pasargadae_garden"), walk=walk,
                    slots={"stroll": [{"t": [7, 5]}, {"t": [9, 3]}, {"t": [9, 8]}],
                           "gardener": [{"t": [7, 6], "face": "+y"}],
                           "throne": [{"t": [5, 6], "face": "+x"}]}, district=9)


# ---------------------------------------------------------------- the stations

def _yard_wall(m, boxes, h, seed, merl=3.0):
    for b in boxes:
        wall(m, *b, h, seed, plinth=2.5, dado=None, amount=0.5)
        M.parapet(m, *b, h, merl, material="mudbrick", pitch=merl * 1.3)


def _gate_tower(m, x0, x1, y0, y1, h, seed, faces=("+x", "+y")):
    wall(m, x0, x1, y0, y1, h, seed, plinth=3.0, dado=None, material="mudbrick", amount=0.5)
    box = (x0, x1, y0, y1, 0, h)
    for face in faces:
        L = face_length(face, x0, x1, y0, y1)
        for z in (h * 0.45, h * 0.72):
            fill(m, face_box(face, x0, x1, y0, y1, z, z + 3.5, L / 2 - 0.7, L / 2 + 0.7, -0.2, 2.0), "ink", tone=0.3)
    slab(m, x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, h, h + 0.8, "cedar", tone=0.2)
    M.beam_ends(m, "+x", box, h - 0.6, spacing=2.4, r=0.4, out=0.6)
    M.beam_ends(m, "+y", box, h - 0.6, spacing=2.4, r=0.4, out=0.6)
    M.parapet(m, x0, x1, y0, y1, h + 0.8, 3.0, material="mudbrick", pitch=3.9)


def halys_gates(m):
    """The gates at the Halys that one must pass to cross the river, with a strong guard post
    (Herodotus 5.52): a gatehouse of mudbrick on a stone foot astride the road, two towers
    flanking a timber-lintelled passage, walls running north and south along the bank, the
    guard's barracks and a lean-to for horses inside the north wall, a fire basket on a tower."""
    seed = 761
    # The road passes along y on dx 3..4 (x 48..80).
    _yard_wall(m, [(4.0, 10.0, 6.0, 58.0), (88.0, 94.0, 6.0, 58.0), (4.0, 46.0, 52.0, 58.0),
                   (82.0, 128.0, 52.0, 58.0), (118.0, 124.0, 6.0, 58.0)], 22.0, seed)
    # Gate towers either side of the passage, on the west face (the camera's side).
    for (a, b) in ((30.0, 47.5), (80.5, 98.0)):
        _gate_tower(m, a, b, 44.0, 62.0, 34.0, seed + 1)
    for (a, b) in ((30.0, 47.5), (80.5, 98.0)):
        _gate_tower(m, a, b, 2.0, 18.0, 30.0, seed + 2, faces=("+x",))
    # Lintels high over the passage (above the walk headroom).
    for y in (46.0, 4.0):
        slab(m, 47.0, 81.0, y, y + 14.0, 26.0, 29.0, "cedar", tone=M.timber("x", seed))
    M.parapet(m, 47.0, 81.0, 46.0, 60.0, 29.0, 3.0, material="mudbrick", pitch=3.9, sides=("+y", "-y"))
    # Barracks north of the road.
    wall(m, 10.0, 30.0, 18.0, 52.0, 18.0, seed + 3, plinth=2.0, dado=None)
    box = (10.0, 30.0, 18.0, 52.0, 0, 18.0)
    stone_frame(m, "+x", box, 12.0, 5.0, 0.0, 10.0, kind="door", leaf="cedar")
    stone_frame(m, "+x", box, 24.0, 3.0, 9.0, 4.0, kind="window")
    flat_top(m, 10.0, 30.0, 18.0, 52.0, 18.0, seed + 4, parapet=0)
    M.beam_ends(m, "+x", box, 17.4, spacing=2.6, r=0.4, out=0.6)
    # The horse lean-to south of the road.
    for y in np.arange(22.0, 52.0, 8.0):
        rod(m, (110.0, y, 0.0), (110.0, y, 13.0), 0.6, "wood")
    slab(m, 94.0, 118.0, 18.0, 52.0, 13.0, 14.2, "straw", tone=lambda X, Y, Z: -0.3 * ((Y % 2.0) < 0.5))
    slab(m, 100.0, 104.0, 22.0, 48.0, 0.0, 2.6, "limestone", tone=-0.2)
    # A fire basket on the north-west tower; a standard on the south-west.
    rod(m, (39.0, 53.0, 37.8), (39.0, 53.0, 41.0), 0.3, "metal")
    ellipsoid(m, (39.0, 53.0, 42.0), (1.2, 1.2, 1.4), "fire")
    halo(m, 39.0, 53.0, 42.0, 12.0, FIRE, 0.9)
    standard(m, 89.0, 53.0, 37.8, h=10.0)


def _halys_landmark():
    walk = tiles(3, 4, 0, 3)
    return Landmark((8, 4), (0, 56), ref("halys_gates"), walk=walk,
                    slots={"guard": [{"t": [3, 3], "face": "+y"}, {"t": [4, 3], "face": "+y"}],
                           "seal_check": [{"t": [3, 2], "face": "+y"}, {"t": [4, 2], "face": "+y"}]},
                    emitters={"fire": (39.0, 53.0, 42.5)}, district=10)


def gates_station(m):
    """The guarded station at the west mouth of the Persian Gates: a walled yard of mudbrick
    on a high rubble foot, a square watch tower at its south-west corner over the road, the
    gate in the south wall toward the road, the guards' room and a stable inside, a beacon
    pan on the tower."""
    seed = 771
    _yard_wall(m, [(2.0, 8.0, 2.0, 126.0), (2.0, 94.0, 2.0, 8.0), (2.0, 94.0, 120.0, 126.0),
                   (88.0, 94.0, 2.0, 56.0), (88.0, 94.0, 88.0, 101.0)], 22.0, seed)
    # Rubble foot under the walls (the station stands on the scree of the defile).
    fill(m, (0.0, 96.0, 0.0, 128.0, 0.0, 3.0), "limestone",
         lambda X, Y, Z: ((X < 10) | (X > 86) | (Y < 10) | (Y > 118)) & ~((X > 79) & (Y > 63) & (Y < 81)) &
         (Z < 2.5 + value_noise(X, Y, Z, 2.0, seed) * 1.5),
         tone=lambda X, Y, Z: (value_noise(X, Y, Z, 1.2, seed + 1) - 0.5) * 1.6)
    for (a, b) in ((55.0, 63.6), (80.4, 89.0)):
        _gate_tower(m, 86.0, 96.0, a, b, 30.0, seed + 2)
    slab(m, 86.0, 96.0, 63.0, 81.0, 25.5, 28.0, "cedar", tone=M.timber("y", seed))
    # The watch tower at the south-west corner.
    _gate_tower(m, 70.0, 96.0, 100.0, 126.0, 46.0, seed + 3)
    ellipsoid(m, (83.0, 113.0, 50.5), (2.2, 2.2, 1.0), "metal", tone=-0.3)
    ellipsoid(m, (83.0, 113.0, 51.6), (1.4, 1.4, 1.5), "fire")
    halo(m, 83.0, 113.0, 51.6, 14.0, FIRE, 0.9)
    # Guards' room along the north wall, a stable shed along the east.
    wall(m, 8.0, 30.0, 8.0, 80.0, 20.0, seed + 4, plinth=2.0, dado=None)
    box = (8.0, 30.0, 8.0, 80.0, 0, 20.0)
    for s in (10.0, 40.0):
        stone_frame(m, "+x", box, s, 5.0, 0.0, 11.0, kind="door", leaf="cedar")
    stone_frame(m, "+y", box, 12.0, 3.0, 10.0, 4.0, kind="window")
    flat_top(m, 8.0, 30.0, 8.0, 80.0, 20.0, seed + 5, parapet=2.0, sides=("+x", "+y"))
    for x in np.arange(40.0, 86.0, 9.0):
        rod(m, (x, 26.0, 0.0), (x, 26.0, 13.0), 0.6, "wood")
    slab(m, 36.0, 88.0, 8.0, 28.0, 13.0, 14.2, "straw", tone=lambda X, Y, Z: -0.3 * ((X % 2.0) < 0.5))
    halo(m, 33.0, 30.0, 12.0, 8.0, LAMP, 0.5)


def _gates_landmark():
    walk = tiles(2, 4, 3, 5) + [(5, 4)]
    return Landmark((6, 8), (0, 56), ref("gates_station"), walk=sorted(set(walk)),
                    slots={"guard": [{"t": [6, 3], "face": "+x"}, {"t": [6, 4], "face": "+x"}],
                           "door": [{"t": [2, 4], "face": "-x"}]},
                    emitters={"beacon": (83.0, 113.0, 52.0)}, district=10)


def royal_road_head(m):
    """The first station of the Royal Road at Sardis (the road's start: Herodotus 5.52-54):
    a walled yard with a columned porch where the travel seals were shown, a storeroom, a
    trough and hitching posts, and by the gate a dressed stone stele with an inscription panel
    (shown blank: Aramaic was the empire's language of administration, but no such marker is
    known). The gate opens north onto the road."""
    seed = 781
    _yard_wall(m, [(2.0, 6.0, 2.0, 15.0), (2.0, 6.0, 49.0, 62.0), (58.0, 62.0, 2.0, 62.0),
                   (2.0, 62.0, 58.0, 62.0), (2.0, 62.0, 2.0, 6.0)], 16.0, seed, merl=2.4)
    for y in (14.2, 49.8):                                      # gate posts either side of the opening
        slab(m, 2.0, 6.0, y - 0.9, y + 0.9, 0.0, 18.0, "cedar", tone=M.timber("x", seed))
        slab(m, 1.6, 6.4, y - 1.3, y + 1.3, 18.0, 19.0, "cinnabar", tone=0.2)
    # The porch: four wooden columns on stone bases before the official's room (south side).
    wall(m, 38.0, 58.0, 8.0, 56.0, 18.0, seed + 1, plinth=2.0, dado=None)
    rb = (38.0, 58.0, 8.0, 56.0, 0, 18.0)
    stone_frame(m, "-x", rb, 20.0, 6.0, 0.0, 11.0, kind="door", leaf="cedar")
    for y in (14.0, 26.0, 38.0, 50.0):
        column(m, 35.0, y, 0.0, Column(0.9, 13.0, base="square", capital="wood", flutes=0, material="cinnabar"))
    slab(m, 32.4, 38.0, 8.0, 56.0, 13.0, 14.5, "cedar", tone=M.timber("y", seed + 2))
    flat_top(m, 32.4, 58.0, 8.0, 56.0, 18.0, seed + 3, parapet=2.0, sides=("+x", "+y"))
    # Trough and hitching posts along the east wall, the stele beside the gate.
    slab(m, 12.0, 26.0, 7.0, 12.0, 0.0, 2.6, "limestone", tone=0.1)
    fill(m, (12.6, 25.4, 7.6, 11.4, 1.8, 2.6), "water", tone=0.1)
    for x in (13.0, 19.0, 25.0):
        rod(m, (x, 14.0, 0.0), (x, 14.0, 6.0), 0.4, "wood")
    slab(m, 8.0, 10.5, 51.0, 56.0, 0.0, 13.0, "cream", tone=M.ashlar(13.0, 5.0, seed + 4))
    fill(m, (10.4, 10.7, 51.8, 55.2, 4.0, 11.5), "cream", tone=-0.25)
    for z in np.arange(5.0, 11.0, 1.2):
        fill(m, (10.5, 10.75, 52.2, 54.8, z, z + 0.4), "cream", tone=-0.7,
             mask=lambda X, Y, Z: ((Y * 3.1).astype(int) % 3) != 0)
    halo(m, 33.0, 32.0, 12.0, 8.0, LAMP, 0.5)


def _road_head_landmark():
    walk = tiles(0, 1, 1, 2)
    return Landmark((4, 4), (0, 40), ref("royal_road_head"), walk=walk,
                    slots={"seal_check": [{"t": [1, 2], "face": "-x"}], "groom": [{"t": [0, 1], "face": "-y"}],
                           "door": [{"t": [1, 1], "face": "+x"}]}, district=10)


LANDMARKS = {
    "parsa.susa_palace": _susa_landmark(),
    "parsa.pasargadae_garden": _pasargadae_landmark(),
    "parsa.halys_gates": _halys_landmark(),
    "parsa.gates_station": _gates_landmark(),
    "parsa.royal_road_head": _road_head_landmark(),
}
