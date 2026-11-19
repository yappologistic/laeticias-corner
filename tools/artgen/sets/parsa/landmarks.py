"""Pārsa's landmarks (persepolis.md §2.3, §3.2), modelled in grid axes: footprint offset dx runs
south (+x), dy west (+y), so the origin tile is the north-east corner and the south and west
faces are the ones the camera sees. One tile is 16 design units (4.7 m at s = 0.85); heights
use 5 s design units per metre (arch.Scale).

Surfaces come from the materials layer (`materials`: ashlar, mud plaster, roofs, beam ends,
spouts, parapets, curtains) and carved and glazed ornament from `relief`, so every wall,
roof and stair front carries the texture and paint the bible describes.
"""

import numpy as np

import materials as M
import relief as R
from arch import (Column, Scale, carve, column, cornice, ellipsoid, entablature, face_box, face_length, field_fill,
                  fill, flat_roof, halo, inscription, revolve, rod, rosette_band, slab, stair, stone_frame)
from setbuild import Landmark
from voxel import hash01, value_noise

S = Scale(0.85)
T = 16                                  # design units per tile
LAMP = (255, 201, 92)


def tc(d):
    """Centre of tile row/column d."""
    return d * T + T / 2


def ref(fn, **kw):
    return ("sets.parsa.landmarks", fn, tuple(sorted(kw.items())))


def tiles(x0, x1, y0, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


# ---------------------------------------------------------------- shared pieces

def wall(m, x0, x1, y0, y1, z1, seed, plinth=3.0, material="mudbrick", dado="hematite", dado_h=5.0, z0=0.0,
         amount=0.55):
    """A mudbrick wall on a dressed stone plinth: hand-smoothed plaster with patches, straw and
    a damp foot, a painted dado above the plinth."""
    if plinth > 0:
        slab(m, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, z0, z0 + plinth, "ashlar",
             tone=M.ashlar(plinth, 7.0, seed, spread=0.5))
    slab(m, x0, x1, y0, y1, z0 + plinth, z1, material, tone=M.mud_plaster(seed, amount, z0 + plinth, 3.0))
    if dado:
        slab(m, x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, z0 + plinth, z0 + plinth + dado_h, dado,
             tone=M.mud_plaster(seed + 1, 0.3, z0 + plinth, 1.5))


def crown(m, x0, x1, y0, y1, z, outer, seed, parapet=5.0, stripes=True, fascia="lapis", spout_every=28.0):
    """The palace crown over a wall top at `z`: joist ends, a painted fascia, the cavetto
    cornice with painted tongues, the plastered roof, red and blue stripes and stepped merlons
    on the outer faces; drain spouts below. Returns the top of the merlons."""
    zr = entablature(m, x0, x1, y0, y1, z, main="y", lines=(), outer=outer, fascia=fascia, seed=seed)
    if spout_every:
        for face in outer:
            M.spouts(m, face, (x0, x1, y0, y1, 0, z), z - 1.0, spacing=spout_every, material="limestone",
                     offset=seed % 7)
    st = ((0.7, "cinnabar"), (0.7, "lapis")) if stripes else ()
    return M.parapet(m, x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, zr, parapet, material="limestone", sides=outer,
                     stripes=st)


def roof_furniture(m, x0, x1, y0, y1, z, seed, hatches=2, rollers=2, fields=None):
    if fields is None:
        fields = (max(1, int(round((x1 - x0) / 40))), max(1, int(round((y1 - y0) / 40))))
    M.roof(m, x0, x1, y0, y1, z, seed=seed, kind="palace", hatches=hatches, rollers=rollers, fields=fields)


def frieze(m, face, box, s0, s1, z_top, kind="rosettes", seed=0):
    """A glazed-brick frieze: a blue brick ground with yellow borders and a row of subjects in
    yellow, white and green ('rosettes', 'lions', 'archers'), set proud of the wall."""
    W = int(round((s1 - s0) * 2))
    H = {"rosettes": 10, "lions": 15, "archers": 20}[kind]
    x0, x1, y0, y1 = box[:4]
    fill(m, face_box(face, x0, x1, y0, y1, z_top - H / 2.0, z_top, s0, s1, -0.5, 0.5), "glaze_blue",
         tone=M.glazed(1.0, 2.2, seed))
    img = R.image(W, H)
    img[0, :] = "G"
    img[H - 1, :] = "G"
    if kind == "rosettes":
        for x in range(1, W - 7, 9):
            R.stamp(img, R.ROSETTE, x, 1)
        cols = {"petal": "white_paint", "heart": "glaze_yellow"}
    elif kind == "lions":
        for x in range(2, W - 22, 26):
            R.stamp(img, R.GLAZE_LION, x, 2)
        cols = {"lion": "glaze_yellow", "mane": "malachite"}
    else:
        for i, x in enumerate(range(2, W - 10, 12)):
            R.stamp(img, R.GLAZE_ARCHER, x, 2)
        cols = {"robe": "glaze_yellow", "trim": "white_paint", "gift": "gold"}
    cols["gold"] = "glaze_yellow"
    R.emboss(m, face, box, s0, z_top, img, colours={**cols, "stone": "skin_dark"} if kind == "archers" else cols,
             depth=1)


PLUS_S = {"+x": "-y", "-x": "+y", "+y": "+x", "-y": "-x"}     # the direction s grows along a face
OPPOSITE = {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y"}


def door(m, face, wall_box, s0, width, height, leaf="gold", material="limestone", jambs=None):
    """A monumental stone door frame (`arch.stone_frame`) with gilded leaves, and optionally
    carved jamb reliefs facing each other across the passage ('king': the king walking under
    his parasol; 'hero': the royal hero stabbing a lion-griffin)."""
    stone_frame(m, face, wall_box, s0, width, 0.0, height, kind="door", leaf=leaf, material=material)
    if not jambs:
        return
    x0, x1, y0, y1 = wall_box[:4]
    thick = (x1 - x0) if face in ("+x", "-x") else (y1 - y0)
    st = R.KING_PARASOL if jambs == "king" else R.HERO_GRIFFIN
    fw = len(st[0]) / 2.0
    z_top = min(height - 1.0, len(st) / 2.0 + 2.0)
    for side in (0, 1):
        if side == 0:      # the left jamb, its face looking along +s
            jb = face_box(face, x0, x1, y0, y1, 0, height, s0 - 2.0, s0, 0, thick)
            jf = PLUS_S[face]
        else:
            jb = face_box(face, x0, x1, y0, y1, 0, height, s0 + width, s0 + width + 2.0, 0, thick)
            jf = OPPOSITE[PLUS_S[face]]
        stn = st if side == 0 else R.mirror(st)
        img = R.image(len(st[0]), len(st))
        R.stamp(img, stn, 0, 0)
        R.emboss(m, jf, jb, max((thick - fw) / 2.0, 0.2), z_top, img,
                 colours={"robe": "purple", "petal": "purple", "stone": material})


# ---------------------------------------------------------------- the Apadāna

APA_COL = S.v(19.5)                     # base to saddle: 'more than 19 m' (Iranica)
APA_HALL = APA_COL + 12.0               # the hall's crown shows above the portico parapets
APA_TOWER = APA_COL + 20.0              # towers rise above everything (stairs to the roofs)
PORTICO_ROWS = (6, 8, 10, 13, 15, 17)   # the wider central bay at 11..12 leads to the throne


def _incense_stand(m, x, y, h=16.0):
    """A tall bronze incense burner with a conical lid, as in the audience relief."""
    revolve(m, x, y, 0, 2.0, lambda t: 2.2 - 0.8 * t, "bronze", tone=0.1)
    rod(m, (x, y, 2.0), (x, y, h - 4.5), 0.5, "bronze", tone=0.2)
    revolve(m, x, y, h - 4.5, h - 2.5, lambda t: 1.2 + 1.0 * t, "bronze", tone=0.3)
    revolve(m, x, y, h - 2.5, h, lambda t: 2.2 * (1 - t) + 0.2, "gold", tone=0.2)


def _tower(m, x0, x1, y0, y1, top, seed):
    """A corner tower: plastered mudbrick on a high stone plinth, tall blind niches in stone
    frames, one row of small windows high up where the stair turns, a glazed frieze of
    rosettes and lions under the painted crown."""
    wall(m, x0, x1, y0, y1, top, seed, plinth=6.0, dado_h=6.0)
    box = (x0, x1, y0, y1, 0, top)
    for face in ("+x", "+y", "-x", "-y"):
        L = face_length(face, x0, x1, y0, y1)
        for s0 in (L * 0.18, L * 0.5 - 4.5, L * 0.82 - 9.0):
            stone_frame(m, face, box, s0, 9.0, 14.0, 30.0, kind="niche")
        stone_frame(m, face, box, L * 0.5 - 3.0, 6.0, 60.0, 9.0, kind="window")
        frieze(m, face, box, 2.0, L - 2.0, top - 2.0, "lions" if (seed + len(face)) % 2 else "rosettes", seed)
    zt = crown(m, x0, x1, y0, y1, top, ("+x", "+y", "-x", "-y"), seed, parapet=6.0, spout_every=0)
    zr = zt - 6.0 - 1.4
    roof_furniture(m, x0, x1, y0, y1, zr, seed, hatches=0, rollers=0, fields=(2, 2))
    # The head of the tower stair: a small plastered kiosk with a door; the royal standard.
    kx, ky = x0 + 10.0, y0 + 10.0
    wall(m, kx, kx + 14.0, ky, ky + 12.0, zr + 11.0, seed + 5, plinth=0.0, dado=None, z0=zr)
    stone_frame(m, "+x", (kx, kx + 14.0, ky, ky + 12.0, zr, zr + 11.0), 4.0, 4.5, zr, 7.0, kind="door", leaf="cedar")
    M.roof(m, kx - 0.5, kx + 14.5, ky - 0.5, ky + 12.5, zr + 11.6, seed=seed, hatches=0, rollers=0, base=-0.4)
    M.parapet(m, kx - 0.5, kx + 14.5, ky - 0.5, ky + 12.5, zr + 11.6, 2.0, material="limestone")
    standard(m, (x0 + x1) / 2 + 6.0, (y0 + y1) / 2 + 6.0, zr, cloth=("cinnabar", "purple")[seed % 2])
    # A lamplit window or two on the faces the camera sees.
    for face in ("+x", "+y"):
        if (seed + (face == "+y")) % 2:
            L = face_length(face, x0, x1, y0, y1)
            b = face_box(face, x0, x1, y0, y1, 60.0, 69.0, L * 0.5 - 2.0, L * 0.5 + 2.0, 2.6, 3.4)
            fill(m, b, "lamp", tone=-0.5)
            halo(m, (b[0] + b[1]) / 2, (b[2] + b[3]) / 2, 64.0, 9.0, LAMP, 0.6)


def _hall_wall_face(m, face, box, L, seed):
    """The hall's walls toward the porticoes: red-painted plaster in tall panels framed in
    white and gold, the great doors and windows in grey stone frames, inscription panels,
    a glazed frieze of guards under the clerestory."""
    x0, x1, y0, y1 = box[:4]
    # Hangings tied back before the great door (Esther 1:6: white, green and blue hangings on
    # cords of fine linen and purple, in Xerxes's palace at Susa).
    for s_a, s_b, colr in ((L / 2 - 10.0, L / 2 + 10.0, ("lapis", "malachite", "white_paint")[seed % 3]),):
        M.curtain(m, on_face(face, box, s_a), on_face(face, box, s_b), 50.0, 0.6, colr, fringe="purple", tied=36.0)
    for i, s in enumerate(np.arange(4.0, L - 8.0, 20.0)):
        fill(m, face_box(face, x0, x1, y0, y1, 9.0, APA_COL - 14.0, s, s + 0.6, -0.06, 0.4), "white_paint", tone=0.2)
    door(m, face, box, L / 2 - 9.0, 18.0, 46.0, leaf="gold")
    for s0 in (L * 0.14, L * 0.78):
        door(m, face, box, s0, 12.0, 34.0, leaf="bronze")
    for s0 in (L * 0.32, L * 0.6):
        stone_frame(m, face, box, s0, 9.0, 18.0, 18.0, kind="window")
    inscription(m, face, box, L / 2 - 8.0, L / 2 + 8.0, 54.0, 62.0)
    frieze(m, face, box, 1.0, L - 1.0, APA_COL - 4.0, "archers", seed)


def on_face(face, box, s, out=0.6):
    """The plan point at `s` along `face` of a box, `out` in front of it."""
    x0, x1, y0, y1 = box[:4]
    return {"+y": (x0 + s, y1 + out), "-y": (x1 - s, y0 - out), "-x": (x0 - out, y0 + s),
            "+x": (x1 + out, y1 - s)}[face]


def standard(m, x, y, z, h=18.0, cloth="cinnabar"):
    """The royal standard: a golden eagle with spread wings on a tall shaft, a red pennant."""
    rod(m, (x, y, z), (x, y, z + h), 0.35, "cedar")
    fill(m, (x - 0.6, x + 0.6, y - 2.6, y + 2.6, z + h, z + h + 1.0), "gold", tone=0.3)
    ellipsoid(m, (x, y, z + h + 1.4), (0.7, 0.7, 1.0), "gold", tone=0.4)
    fill(m, (x - 0.2, x + 0.2, y + 0.3, y + 4.5, z + h - 5.0, z + h - 1.0), cloth,
         lambda X, Y, Z: (Z - (z + h - 5.0)) > (Y - y) * 0.4 + 0.3 * np.sin(Y * 1.5), tone=0.2)


def _portico(m, x0, x1, y0, y1, faces, cols, cap, beam, seed):
    """A portico of 12 columns under a painted entablature, the outer faces crowned with
    stripes and merlons."""
    c = Column(S.h(0.8), APA_COL, base="bell", capital=cap, beam=beam)
    for (x, y) in cols:
        column(m, x, y, 0.0, c)
    # The main beams lie in the saddles across the protomes, one line per column row.
    lines = sorted({x for x, _ in cols}) if beam == "x" else sorted({y for _, y in cols})
    main = "y" if beam == "x" else "x"
    zr = entablature(m, x0, x1, y0, y1, APA_COL, main=main, lines=lines, outer=faces, seed=seed)
    M.parapet(m, x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, zr, 5.0, material="limestone", sides=faces,
              stripes=((0.7, "cinnabar"), (0.7, "lapis")))
    roof_furniture(m, x0, x1, y0, y1, zr, seed + 2, hatches=0, rollers=1,
                   fields=(6, 1) if x1 - x0 > y1 - y0 else (1, 6))


def apadana(m):
    hall = (5 * T + 1.5, 19 * T - 1.5, 5 * T + 1.5, 19 * T - 1.5)   # inset: nothing on walk tiles
    hx0, hx1, hy0, hy1 = hall
    wt = 9.0
    # Red-painted toward the porticoes, plain plaster toward the service rooms.
    for w, mat in (((hx0, hx0 + wt, hy0, hy1), "cinnabar"), ((hx1 - wt, hx1, hy0, hy1), "mudbrick"),
                   ((hx0, hx1, hy0, hy0 + wt), "cinnabar"), ((hx0, hx1, hy1 - wt, hy1), "cinnabar")):
        wall(m, *w, APA_HALL, 11, plinth=3.0, material=mat, dado_h=6.0, amount=0.3 if mat == "cinnabar" else 0.55)
    north = (hx0, hx0 + wt, hy0, hy1, 0, APA_HALL)
    west = (hx0, hx1, hy1 - wt, hy1, 0, APA_HALL)
    east = (hx0, hx1, hy0, hy0 + wt, 0, APA_HALL)
    south = (hx1 - wt, hx1, hy0, hy1, 0, APA_HALL)
    L = hy1 - hy0
    for face, w in (("-x", north), ("+y", west), ("-y", east)):
        _hall_wall_face(m, face, w, L, 11)
    zt = crown(m, hx0, hx1, hy0, hy1, APA_HALL, ("+x", "-x", "+y", "-y"), 13, parapet=5.0)
    roof_furniture(m, hx0 + 1, hx1 - 1, hy0 + 1, hy1 - 1, zt - 5.0 - 1.4, 14, hatches=4, rollers=2, fields=(6, 6))
    # Porticoes: two rows of six columns each. The north portico has the full composite bull
    # capitals; the west portico (seen) double bulls and the east double lions, both set
    # directly on the fluted shaft without the palm and volute stage (Iranica, "Apadana").
    hang = ("white_paint", "malachite", "lapis")
    north_cols = [(x, tc(d)) for x in (tc(1), tc(3)) for d in PORTICO_ROWS]
    _portico(m, tc(1) - 7.0, 5 * T, 5 * T, 19 * T, ("-x", "+y", "-y"), north_cols, "bull", "y", 21)
    west_cols = [(tc(d), y) for d in PORTICO_ROWS for y in (tc(20), tc(22))]
    _portico(m, 5 * T, 19 * T, 19 * T, tc(22) + 7.0, ("+y", "+x", "-x"), west_cols, "bull_protome", "x", 23)
    east_cols = [(tc(d), y) for d in PORTICO_ROWS for y in (tc(1), tc(3))]
    _portico(m, 5 * T, 19 * T, tc(1) - 7.0, 5 * T, ("-y", "+x", "-x"), east_cols, "lion_protome", "x", 25)
    # South service rooms: a lower closed range with plain doors, beam ends and spouts.
    sx0 = 19 * T + 1.5
    sh = 52.0
    wall(m, sx0, 24 * T, 5 * T, 19 * T, sh, 15, plinth=3.0, dado_h=5.0)
    srooms = (sx0, 24 * T, 5 * T, 19 * T, 0, sh)
    for i in range(5):
        stone_frame(m, "+x", srooms, 14.0 + i * 44.0, 8.0, 0.0, 22.0, kind="door" if i % 2 else "niche",
                    leaf="cedar")
        stone_frame(m, "+x", srooms, 34.0 + i * 44.0, 7.0, 28.0, 10.0, kind="window")
    M.beam_ends(m, "+x", srooms, sh - 1.0, spacing=4.0, r=0.8, out=1.0)
    M.spouts(m, "+x", srooms, sh - 2.5, spacing=30.0, material="limestone")
    M.roof(m, sx0, 24 * T, 5 * T, 19 * T, sh + 0.6, seed=16, kind="palace", hatches=2, rollers=1, fields=(1, 5))
    M.parapet(m, sx0, 24 * T, 5 * T, 19 * T, sh + 0.6, 3.5, material="mudbrick", sides=("+x",))
    # Corner towers, rising above the roofs.
    for i, (x0, y0) in enumerate(((0, 0), (0, 19 * T), (19 * T, 0), (19 * T, 19 * T))):
        _tower(m, x0 + 1.5, x0 + 5 * T - 1.5, y0 + 1.5, y0 + 5 * T - 1.5, APA_TOWER, i)
    # Bronze incense stands flanking the throne bay of the north portico.
    for y in (tc(10) - 6.0, tc(13) + 6.0):
        _incense_stand(m, tc(1) + 5.0, y)
        halo(m, tc(1) + 5.0, y, 15.0, 5.0, LAMP, 0.5)


def _apadana_landmark():
    columns = {(1, d) for d in PORTICO_ROWS} | {(3, d) for d in PORTICO_ROWS}
    walk = [t for t in tiles(0, 4, 5, 18) if t not in columns]
    wcols = {(d, 20) for d in PORTICO_ROWS} | {(d, 22) for d in PORTICO_ROWS}
    walk += [t for t in tiles(5, 18, 19, 23) if t not in wcols]
    # The east portico, where the east stair's flights land (its head at y 0, x 7-8 and
    # 15-16), before the hall's east doors.
    ecols = {(d, 1) for d in PORTICO_ROWS} | {(d, 3) for d in PORTICO_ROWS}
    walk += [t for t in tiles(5, 18, 0, 4) if t not in ecols]
    return Landmark(
        (24, 24), (0, 122), ref("apadana"), walk=walk,
        slots={"audience": [{"t": [0, 11], "face": "+x"}, {"t": [0, 12], "face": "+x"},
                            {"t": [1, 11], "face": "+x"}, {"t": [1, 12], "face": "+x"}],
               "usher": [{"t": [2, 13], "face": "-y"}],
               "guard": [{"t": [0, 9], "face": "-x"}, {"t": [0, 14], "face": "-x"},
                         {"t": [18, 23], "face": "+y"}, {"t": [5, 23], "face": "+y"}],
               "stroll": [{"t": [11, 21]}, {"t": [7, 19]}, {"t": [15, 23]}]},
        emitters={"incense_l": (tc(1) + 5.0, tc(10) - 6.0, 16.5), "incense_r": (tc(1) + 5.0, tc(13) + 6.0, 16.5)},
        district=1)


# ---------------------------------------------------------------- sculpture

def colossus(m, cx, cy, face, length, height, human=False, rough=False, material="limestone"):
    """A colossal guardian bull in profile on its plinth, striding out along y (`face` +1 for
    west, -1 for east): a plain bull, or (human=True) a winged bull with a bearded human head
    under a tall feathered crown (the lamassu of the Gate's east door). `rough` blocks it out
    as a mason would, half finished (Hall of a Hundred Columns)."""
    L, H = length, height
    w = max(3.0, L * 0.16)
    y0 = cy - face * L * 0.5                     # rump end
    f = face
    tone = (lambda X, Y, Z: -0.5 * ((np.floor(Z) + np.floor(Y * 0.7)) % 3 == 0)) if rough else 0.15
    slab(m, cx - w * 1.1, cx + w * 1.1, min(y0, y0 + f * L), max(y0, y0 + f * L), 0, H * 0.08, material, tone=0.0)
    zb = H * 0.08
    if rough:
        # A dressed block with the foreparts emerging at the front.
        slab(m, cx - w, cx + w, min(y0, y0 + f * L * 0.6), max(y0, y0 + f * L * 0.6), zb, zb + H * 0.62,
             material, tone=tone)
        ellipsoid(m, (cx, y0 + f * L * 0.72, zb + H * 0.5), (w * 0.95, L * 0.22, H * 0.32), material, tone=tone)
        ellipsoid(m, (cx, y0 + f * L * 0.9, zb + H * 0.68), (w * 0.7, L * 0.13, H * 0.15), material, tone=tone)
        return
    # Body and legs.
    ellipsoid(m, (cx, y0 + f * L * 0.48, zb + H * 0.52), (w, L * 0.44, H * 0.22), material, tone=0.15)
    for lat in (-0.55, 0.55):
        for along, ph in ((0.18, 0.0), (0.8, 1.0)):
            yy = y0 + f * L * along
            stride = f * L * 0.05 * (ph if lat > 0 else -ph)
            rod(m, (cx + lat * w, yy, zb + H * 0.42), (cx + lat * w, yy + stride, zb), w * 0.32, material, tone=-0.1)
            slab(m, cx + lat * w - w * 0.35, cx + lat * w + w * 0.35, yy + stride - 1.0, yy + stride + 1.0, zb,
                 zb + 1.2, material, tone=-0.3)
    # Chest, neck, head.
    ellipsoid(m, (cx, y0 + f * L * 0.82, zb + H * 0.56), (w * 1.05, L * 0.16, H * 0.24), material, tone=0.2)
    hy, hz = y0 + f * L * 0.98, zb + H * (0.78 if human else 0.72)
    if human:
        # Wings rising from the shoulders, feathered in rows.
        def wing(X, Y, Z):
            u = (Y - (y0 + f * L * 0.25)) * f / (L * 0.65)
            v = (Z - (zb + H * 0.5)) / (H * 0.5)
            return (u > 0) & (u < 1) & (v > 0) & (v < 0.35 + 0.6 * u)
        for lat in (-1, 1):
            xx = cx + lat * w * 1.0
            fill(m, (xx - 0.8, xx + 0.8, min(y0, y0 + f * L), max(y0, y0 + f * L), zb + H * 0.45, zb + H),
                 material, wing, tone=lambda X, Y, Z: 0.4 * ((Z * 1.4) % 1.0 < 0.35) - 0.1)
        ellipsoid(m, (cx, hy, hz), (w * 0.62, L * 0.11, H * 0.12), material, tone=0.25)
        # Long beard in rows of curls, the tall crown with horns and a feathered rim.
        fill(m, (cx - w * 0.6, cx + w * 0.6, hy - 3, hy + 3, hz - H * 0.24, hz - H * 0.04), "hair_black",
             lambda X, Y, Z: (Y - hy) * f > -L * 0.04,
             tone=lambda X, Y, Z: -0.4 * ((Z * 1.6) % 1.0 < 0.4) + 0.2)
        revolve(m, cx, hy - f * 0.5, hz + H * 0.08, hz + H * 0.26, lambda t: w * 0.6 - 0.2 * t, material, ribs=10,
                tone=0.1)
        fill(m, (cx - w * 0.7, cx + w * 0.7, hy - 3, hy + 3, hz + H * 0.24, hz + H * 0.28), "gold",
             lambda X, Y, Z: np.hypot(X - cx, Y - hy + f * 0.5) < w * 0.68, tone=0.3)
        for lat in (-1, 1):
            rod(m, (cx + lat * w * 0.5, hy, hz + H * 0.1), (cx + lat * w * 0.7, hy + f * 1.5, hz + H * 0.14), 0.5, material)
    else:
        rod(m, (cx, y0 + f * L * 0.86, zb + H * 0.62), (cx, hy, hz), w * 0.55, material, tone=0.2)
        ellipsoid(m, (cx, hy + f * L * 0.03, hz - H * 0.02), (w * 0.55, L * 0.09, H * 0.1), material, tone=0.25)
        for lat in (-1, 1):
            rod(m, (cx + lat * w * 0.4, hy, hz + H * 0.06), (cx + lat * w * 0.8, hy + f * L * 0.04, hz + H * 0.16),
                0.6, "gold", tone=0.2)
        fill(m, (cx - w, cx + w, hy - 4, hy + 4, hz - H * 0.15, hz - H * 0.05), material,
             lambda X, Y, Z: (np.abs(X - cx) < w * 0.5) & ((Y - hy) * f < 0), tone=-0.3)   # dewlap
    if f:  # a painted eye on the sculpture's face
        for lat in (-1, 1):
            fill(m, (cx + lat * w * 0.55 - 0.5, cx + lat * w * 0.55 + 0.5, hy - 0.6, hy + 0.6, hz, hz + 1.0),
                 "hair_black")


# ---------------------------------------------------------------- relief stairs

def steps(m, x0, x1, y0, y1, z0, z1, up, step=1.2, seed=0, wear=True):
    """A flight of dressed steps: each tread with a lit nosing and a shadowed riser foot, the
    middle of the flight worn a shade lighter by feet."""
    stair(m, x0, x1, y0, y1, z0, z1, up, step=step, material="limestone")
    # Treads sit a step down the ramp so their lit nosings and shadowed risers both show.
    M.stain(m, (x0, x1, y0, y1, z0, z1 + step), lambda X, Y, Z: True, -0.7)
    if wear:
        along_x = up in ("+x", "-x")
        c, half = ((y0 + y1) / 2, (y1 - y0) / 2) if along_x else ((x0 + x1) / 2, (x1 - x0) / 2)

        def lane(X, Y, Z):
            a = Y if along_x else X
            return np.abs(a - c) < half * 0.45
        M.stain(m, (x0, x1, y0, y1, z0, z1 + step), lane, 0.3)


def relief_wing(m, face, box, s0, s1, z_bottom, z_top, kind, seed, facing=1, centre=None):
    """A stair front carved in registers between rosette borders (relief.stair_facade)."""
    W = int((s1 - s0) * 2)
    H = int((z_top - z_bottom) * 2)
    if W < 8 or H < 12:
        return
    img, cmap = R.stair_facade(W, H, kind, seed, facing, centre)
    R.emboss(m, face, box, s0, z_top, img, cmap=cmap)


def lion_bull(m, face, box, s0, s1, z_bottom, z_top, flip=False):
    """The stair-triangle emblem: a lion leaping onto a bull from behind, under a rosette band."""
    W = int((s1 - s0) * 2)
    H = int((z_top - z_bottom) * 2)
    img = R.image(W, H)
    for x in range(0, W - 4, 6):
        R.stamp(img, R.ROSETTE_S, x, 0)
    st = R.LION_BULL if not flip else R.mirror(R.LION_BULL)
    R.stamp(img, st, max((W - len(st[0])) // 2, 0), H - len(st) - 1)
    R.emboss(m, face, box, s0, z_top, img, colours={"lion": "saffron", "mane": "cedar", "beast": "limestone"})


def relief_stair(m, fw, fh, rise, axis, low, flights, front_kind="delegations", seed=0, centre=None):
    """A Pārsa stair block of `rise` design units: straight flights (tile ranges across the
    axis) climbing from the `low` end along `axis`, parapets crowned with stepped merlons and
    carved on their inner faces with guards climbing beside the steps, and the fronts between
    and beside the flights carved and painted: registers of figures, lion-and-bull panels."""
    X1, Y1 = fw * T, fh * T
    along_x = axis == "x"
    up = ("+" if low == "lo" else "-") + axis
    front = ("-" if low == "lo" else "+") + axis
    occupied = []
    for a, b in flights:
        c0, c1 = a * T, (b + 1) * T
        occupied.append((c0, c1))
        if along_x:
            steps(m, 0, X1, c0, c1, 0, rise, up, seed=seed)
        else:
            steps(m, c0, c1, 0, Y1, 0, rise, up, seed=seed)
    edges = sorted({0, *(c for ab in occupied for c in ab), (Y1 if along_x else X1)})
    span = Y1 if along_x else X1
    top = rise + 4.0
    for c0, c1 in zip(edges, edges[1:]):
        if any(a <= c0 and c1 <= b for a, b in occupied):
            continue
        box = (0, X1, c0, c1, 0, top) if along_x else (c0, c1, 0, Y1, 0, top)
        slab(m, *box, "limestone", tone=M.ashlar(3.0, 9.0, seed + 31, spread=0.45))
        fill(m, (box[0] - 0.01, box[1] + 0.01, box[2] - 0.01, box[3] + 0.01, top - 0.6, top), "limestone",
             tone=M.plus(M.paving(9.0, 6.0, seed + 33), -0.2))
        L = c1 - c0
        if L > 20:
            mid = (c0 + c1) / 2
            is_centre = centre is not None and abs(mid - span / 2) < 1
            relief_wing(m, front, box, 1.0, L - 1.0, 0.5, top - 0.5, front_kind, seed + int(c0),
                        facing=1 if mid < span / 2 else -1, centre=centre if is_centre else None)
        else:
            lion_bull(m, front, box, 0.5, L - 0.5, 0.5, top - 0.5, flip=c0 > span / 2)
        M.parapet(m, *box[:4], top, 2.8, material="limestone", pitch=3.4, sides=(front,))
        _climbing_guards(m, box, c0, c1, occupied, along_x, low, rise, top, X1 if along_x else Y1)


def _climbing_guards(m, box, c0, c1, occupied, along_x, low, rise, top, L2):
    """Guards climbing step by step on the inner faces of a parapet block beside its flights,
    wherever the parapet stands tall enough above the steps to hold them."""
    g = R.guards()
    for face, edge in ((("+y" if along_x else "+x"), c1), (("-y" if along_x else "-x"), c0)):
        if not any(abs(edge - (a if face[0] == "+" else b)) < 0.1 for a, b in occupied):
            continue
        dir_s = 1 if face in ("+y", "-x") else -1          # how s runs against the axis
        upslope = 1 if low == "lo" else -1
        for i, a in enumerate(np.arange(3.0, L2 - 3.0, 6.5)):
            floor = rise * (a / L2 if low == "lo" else 1 - a / L2) + 1.2
            if top - floor < 8.6:
                continue
            st, col = g[i % len(g)]
            if dir_s * upslope < 0:
                st = R.mirror(st)
            img = R.image(len(st[0]), len(st))
            R.stamp(img, st, 0, 0)
            s_pos = a if dir_s > 0 else L2 - a
            R.emboss(m, face, box, s_pos - len(st[0]) / 4.0, floor + 8.2, img, colours=col, sunk=True)


def _stair_landmark(fn, fw, fh, rise, axis, low, flights, district, **kw):
    """Walk tiles along each flight; floors rise with the steps (design units)."""
    walk, floor = [], {}
    n = fw if axis == "x" else fh
    for a, b in flights:
        for c in range(a, b + 1):
            for i in range(n):
                t = (i, c) if axis == "x" else (c, i)
                walk.append(t)
                # The tread at the tile's middle: the foot tile half a flight-tile above the
                # ground (≤ 8 px for these flights), the head tile half one below the top.
                frac = (i + 0.5) / n if low == "lo" else (n - i - 0.5) / n
                floor[t] = rise * frac + 1.2
    up = ("+" if low == "lo" else "-") + axis
    return Landmark((fw, fh), (0, int(rise) + 12), ref(fn, **kw), walk=walk, floor=floor, district=district,
                    climb=up)


APA_N = (3, 14, 8.0, "x", "lo", [(1, 2), (11, 12)])
APA_E = (12, 3, 8.0, "y", "lo", [(1, 2), (9, 10)])
TAC_S = (3, 8, 16.0, "x", "hi", [(2, 2), (5, 5)])      # flights land on the portico's walk tiles
HAD_W = (6, 4, 24.0, "y", "hi", [(1, 1), (4, 4)])
TRI_N = (2, 5, 8.0, "x", "lo", [(2, 2)])                # one flight onto the north door's tile


def apadana_stair_n(m):
    relief_stair(m, *APA_N, "delegations", seed=3, centre="audience")


def apadana_stair_e(m):
    relief_stair(m, *APA_E, "delegations", seed=5, centre="audience")


def tacara_stair_s(m):
    relief_stair(m, *TAC_S, "guards", seed=7, centre="disc")


def hadish_stair_w(m):
    relief_stair(m, *HAD_W, "servants", seed=9)


def tripylon_stair(m):
    relief_stair(m, *TRI_N, "nobles", seed=11)


def stair_relief_kit(m):
    relief_stair(m, 2, 1, 8.0, "x", "lo", [(0, 0)], seed=13)


# ---------------------------------------------------------------- the great stairway

# Each side climbs 63 steps to its landing and 48 more to the top, on long shallow treads
# (persepolis.md §3.2): the two flights keep that ratio (21 : 16 drawn steps) and about the
# same tread, the lower flight being the longer one.
GS_LOW = 24.0 / 21
GS_UP = 24.0 / 16


def great_stair(m):
    """Two symmetrical stairs against the terrace face: the lower flights start side by side
    at the centre and climb outward to square landings, the upper flights turn back and climb
    inward to one top landing (persepolis.md §2.3). Shallow broad steps, low plain parapets,
    the mass faced with huge fitted blocks; no reliefs (they are on the Apadāna)."""
    L1, L2 = 24.0, 48.0                       # landing and terrace heights (3 and 6 levels)
    big = M.ashlar(6.0, 16.0, 41, polygonal=0.5, spread=0.55)
    for box in ((0, 48, 16, 112, 0, L1), (240, 288, 16, 112, 0, L1), (48, 112, 16, 64, 0, L1),
                (176, 240, 16, 64, 0, L1), (112, 176, 0, 64, 0, L2), (0, 112, 0, 16, 0, L2), (176, 288, 0, 16, 0, L2)):
        slab(m, *box, "ashlar", tone=big)
    # Flights.
    steps(m, 48, 128, 64, 112, 0, L1, "-x", step=GS_LOW)
    steps(m, 160, 240, 64, 112, 0, L1, "+x", step=GS_LOW)
    steps(m, 48, 112, 16, 64, L1, L2, "+x", step=GS_UP)
    steps(m, 176, 240, 16, 64, L1, L2, "-x", step=GS_UP)
    # Paving of the landings.
    for x0, x1, y0, y1, z in ((0, 48, 16, 112, L1), (240, 288, 16, 112, L1), (112, 176, 0, 64, L2)):
        slab(m, x0, x1, y0, y1, z - 0.6, z, "limestone", tone=M.paving(10.0, 8.0, 43))
    # Low parapets with a rounded coping: along the outer edge of the lower flights and the
    # landings, along the inner edge of the upper flights and the top landing.
    P = 2.6

    def parapet_run(x0, x1, y0, y1, z0, z1, up, step):
        stair(m, x0, x1, y0, y1, z0 + P, z1 + P, up, step=step, material="limestone")
        M.stain(m, (x0, x1, y0, y1, z0, z1 + P + 2), lambda X, Y, Z: True, 0.2)
    parapet_run(48, 128, 108, 112, 0, L1, "-x", GS_LOW)
    parapet_run(160, 240, 108, 112, 0, L1, "+x", GS_LOW)
    for x0, x1 in ((0, 48), (240, 288)):
        slab(m, x0, x1, 108, 112, 0, L1 + P + 0.6, "limestone", tone=M.ashlar(3.0, 12.0, 45, spread=0.4))
    slab(m, 0, 4, 16, 112, 0, L1 + P + 0.6, "limestone", tone=M.ashlar(3.0, 12.0, 46, spread=0.4))
    slab(m, 284, 288, 16, 112, 0, L1 + P + 0.6, "limestone", tone=M.ashlar(3.0, 12.0, 47, spread=0.4))
    parapet_run(48, 112, 60, 64, L1, L2, "+x", GS_UP)
    parapet_run(176, 240, 60, 64, L1, L2, "-x", GS_UP)
    slab(m, 112, 176, 60, 64, 0, L2 + P + 0.6, "limestone", tone=M.ashlar(3.0, 12.0, 48, spread=0.4))
    # A worn, warm coping along every parapet top.
    for box in ((0, 48, 108, 112), (240, 288, 108, 112), (0, 4, 16, 112), (284, 288, 16, 112), (112, 176, 60, 64)):
        z = L2 + P + 0.6 if box[2] == 60 else L1 + P + 0.6
        fill(m, (*box, z - 0.5, z), "limestone", tone=0.45)


def _great_stair_landmark():
    walk, floor = [], {}
    L1, L2 = 24.0, 48.0
    for x in (8, 9):
        for y in (4, 5, 6):
            walk.append((x, y))
            floor[(x, y)] = 0.0
    for d in range(3, 8):                               # lower flight north, rising to -x
        for y in (4, 5):
            walk.append((d, y))
            floor[(d, y)] = L1 * (128 - 16 * d) / 80 + GS_LOW
    for d in range(10, 15):                             # lower flight south
        for y in (4, 5):
            walk.append((d, y))
            floor[(d, y)] = L1 * (16 * (d + 1) - 160) / 80 + GS_LOW
    for x in (1, 2, 15, 16):                            # landings
        for y in range(1, 6):
            walk.append((x, y))
            floor[(x, y)] = L1
    for d in range(3, 7):                               # upper flight north, rising to +x
        for y in (1, 2):
            walk.append((d, y))
            floor[(d, y)] = L1 + (L2 - L1) * (16 * (d + 1) - 48) / 64 + GS_UP
    for d in range(11, 15):                             # upper flight south, rising to -x
        for y in (1, 2):
            walk.append((d, y))
            floor[(d, y)] = L1 + (L2 - L1) * (240 - 16 * d) / 64 + GS_UP
    for x in range(7, 11):                              # the top landing
        for y in (0, 1, 2):
            walk.append((x, y))
            floor[(x, y)] = L2
    return Landmark((18, 7), (0, 60), ref("great_stair"), walk=walk, floor=floor,
                    slots={"guard": [{"t": [7, 0], "face": "+y"}, {"t": [10, 0], "face": "+y"}],
                           "storyteller": [{"t": [8, 7], "face": "+y"}]},
                    district=0, climb="-y")


# ---------------------------------------------------------------- the Gate of All Lands

GATE_COL = S.v(16.5)                       # the commonly repeated figure (persepolis.md §11)


def gate_all_lands(m):
    top = GATE_COL + 4.0
    wt = 11.0
    seed = 51
    walls = [(0, wt, 0, 96), (96 - wt, 96, 0, 31.5), (96 - wt, 96, 64.5, 96),
             (0, 31.5, 96 - wt, 96), (64.5, 96, 96 - wt, 96), (0, 31.5, 0, wt), (64.5, 96, 0, wt)]
    for w in walls:
        wall(m, *w, top, seed, plinth=4.0, dado_h=6.0)
    # Lintels over the three doors, the doors about 10 m high.
    dh = S.v(10.0)
    for box in ((32, 64, 96 - wt, 96), (32, 64, 0, wt), (96 - wt, 96, 32, 64)):
        slab(m, *box, dh + 4.0, top, "mudbrick", tone=M.mud_plaster(seed, 0.5, dh, 0.0))
    # Stone jambs and cornices of the west and east doors (the colossi's blocks).
    for y0, y1 in ((96 - wt - 2, 96 + 1), (-1, wt + 2)):
        for x0 in (28.0, 64.0):
            slab(m, x0, x0 + 4.0, y0, y1, 0, dh, "limestone", tone=M.ashlar(4.0, 30.0, seed + int(x0), spread=0.3))
        slab(m, 28.0, 68.0, y0, y1, dh, dh + 4.0, "limestone", tone=0.15)
        cornice(m, 28.0, 68.0, y0 + 0.5, y1 - 0.5, dh + 4.0, 5.0, 1.2, "limestone")
        fill(m, (26.5, 69.5, y0 - 1.0, y1 + 1.0, dh + 8.5, dh + 9.0), "gold", tone=0.2, only_solid=True)
    door(m, "+x", (96 - wt, 96, 0, 96, 0, top), 32.0, 32.0, dh - 2.0, leaf="gold")
    carve(m, (96 - wt - 1, 97, 32, 64, 0, dh - 2.0))
    # The colossi: bulls striding out of the west door, winged human-headed bulls at the east.
    for cx in (24.0, 72.0):
        colossus(m, cx, 84.0, +1, 34.0, 40.0)
        colossus(m, cx, 12.0, -1, 34.0, 44.0, human=True)
    # The trilingual XPa panels high on the façades above the colossi; glazed friezes.
    for face, w in (("+y", (0, 96, 96 - wt, 96, 0, top)), ("-y", (0, 96, 0, wt, 0, top))):
        for s0 in (6.0, 71.0):
            inscription(m, face, w, s0, s0 + 19.0, 50.0, 62.0)
        frieze(m, face, w, 1.0, 95.0, top - 2.0, "rosettes", seed)
    for face, w in (("+x", (96 - wt, 96, 0, 96, 0, top)), ("-x", (0, wt, 0, 96, 0, top))):
        frieze(m, face, w, 1.0, 95.0, top - 2.0, "rosettes", seed + 1)
    # Four columns with double-bull capitals carry the roof.
    col = Column(S.h(0.85), GATE_COL, base="bell", capital="bull", beam="y")
    for x in (tc(1), tc(4)):
        for y in (tc(1), tc(4)):
            column(m, x, y, 0.0, col)
    zt = crown(m, 0, 96, 0, 96, top, ("+x", "+y", "-x", "-y"), seed, parapet=5.0, spout_every=32.0)
    roof_furniture(m, 8, 88, 8, 88, zt - 5.0 - 1.4, seed, hatches=1, rollers=1)
    # Torches in brackets beside the west and east doors.
    for y, yy in ((97.0, 98.5), (-1.0, -2.5)):
        for x in (20.0, 76.0):
            rod(m, (x, y, 30.0), (x, yy, 36.0), 0.5, "bronze")
            fill(m, (x - 0.8, x + 0.8, yy - 0.8, yy + 0.8, 36.0, 38.5), "fire")
            halo(m, x, yy, 38.0, 12.0, LAMP, 0.8)
            M.stain(m, (x - 2, x + 2, min(y, yy) - 2, max(y, yy) + 2, 38.0, 50.0),
                    lambda X, Y, Z: True, -0.4)


def _gate_landmark():
    walk = tiles(2, 3, 0, 5) + [(1, 2), (1, 3), (4, 2), (4, 3), (5, 2), (5, 3)]
    return Landmark((6, 6), (0, 104), ref("gate_all_lands"), walk=walk,
                    slots={"guard": [{"t": [2, 6], "face": "+y"}, {"t": [3, 6], "face": "+y"},
                                     {"t": [2, -1], "face": "-y"}, {"t": [3, -1], "face": "-y"}]},
                    emitters={"torch_w": (20.0, 98.5, 39.0), "torch_e": (20.0, -2.5, 39.0)}, district=0)


# ---------------------------------------------------------------- palaces

def _hall_walls(m, x0, x1, y0, y1, top, seed, material="mudbrick", t=8.0):
    for w in ((x0, x0 + t, y0, y1), (x1 - t, x1, y0, y1), (x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1)):
        wall(m, *w, top, seed, plinth=3.0, material=material, dado_h=5.0)


def _windows(m, face, wall_box, n, z0, h, w, kind="window", material="limestone", lead=0.12):
    x0, x1, y0, y1, _a, _b = wall_box
    L = (y1 - y0) if face in ("+x", "-x") else (x1 - x0)
    for i in range(n):
        s0 = L * lead + (L * (1 - 2 * lead) - w) * (i / max(n - 1, 1))
        stone_frame(m, face, wall_box, s0, w, z0, h, kind=kind if (i % 2 == 0 or kind != "mixed") else "niche",
                    material=material)


def _portico_block(m, x0, x1, y0, y1, H, cols, cap, beam, faces, seed, r=None):
    """Columns with their painted entablature, stripes and merlons on the outer faces."""
    c = Column(r or S.h(0.65), H, base="bell", capital=cap, beam=beam)
    for (x, y) in cols:
        column(m, x, y, 0.0, c)
    lines = sorted({x for x, _ in cols}) if beam == "x" else sorted({y for _, y in cols})
    zr = entablature(m, x0, x1, y0, y1, H, main="y" if beam == "x" else "x", lines=lines, outer=faces, seed=seed)
    M.parapet(m, x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, zr, 5.0, material="limestone", sides=faces,
              stripes=((0.7, "cinnabar"), (0.7, "lapis")))
    roof_furniture(m, x0, x1, y0, y1, zr, seed + 2, hatches=0, rollers=1)
    return zr


TAC_COL = S.v(12.0)


def tacara(m):
    """Darius's small palace: frames of dark polished stone (the 'hall of mirrors' sheen) so
    many that the walls between are narrow piers, a hall of 12 columns behind a portico of 8
    on the south, the king under his parasol carved on the door jambs, DPa on the antae."""
    top = TAC_COL + 4.0
    seed = 61
    _hall_walls(m, 0, 110.5, 0, 128, top, seed)
    south = (102.5, 110.5, 0, 128, 0, top)
    door(m, "+x", south, 48.0, 32.0, 36.0, leaf="gold", material="polished", jambs="king")
    for s0 in (8.0, 26.0, 88.0, 106.0):
        stone_frame(m, "+x", south, s0, 12.0, 4.0, 22.0, kind="window" if s0 in (26.0, 88.0) else "niche",
                    material="polished")
    west = (0, 112, 120, 128, 0, top)
    _windows(m, "+y", west, 6, 8.0, 22.0, 10.0, kind="mixed", material="polished", lead=0.06)
    north = (0, 8, 0, 128, 0, top)
    _windows(m, "-x", north, 5, 8.0, 22.0, 10.0, kind="mixed", material="polished", lead=0.06)
    east = (0, 112, 0, 8, 0, top)
    _windows(m, "-y", east, 6, 8.0, 22.0, 10.0, kind="mixed", material="polished", lead=0.06)
    for face, w in (("+y", west), ("-y", east), ("-x", north)):
        frieze(m, face, w, 2.0, face_length(face, *w[:4]) - 2.0, top - 2.0, "rosettes", seed)
    zt = crown(m, 0, 110.5, 0, 128, top, ("-x", "-y", "+y"), seed, parapet=5.0)
    roof_furniture(m, 0, 110.5, 0, 128, zt - 6.4, seed, hatches=2, rollers=1, fields=(3, 3))
    # The portico: antae with niches and the DPa panels, two rows of four columns.
    for y0, y1 in ((0, 14), (114, 128)):
        wall(m, 112, 158, y0, y1, top, seed, plinth=3.0, dado_h=5.0)
        stone_frame(m, "+x", (112, 158, y0, y1, 0, top), 2.0, 10.0, 6.0, 20.0, kind="niche", material="polished")
        inscription(m, "+x", (112, 158, y0, y1, 0, top), 2.0, 12.0, 32.0, 42.0, material="polished")
    cols = [(x, tc(d)) for x in (tc(7), tc(9)) for d in (1, 3, 4, 6)]
    _portico_block(m, 112, 158, 0, 128, TAC_COL, cols, "bull", "x", ("+x", "+y", "-y"), seed + 3)
    halo(m, 112.0, 64.0, 18.0, 14.0, LAMP, 0.6)


def _tacara_landmark():
    walk = [(8, d) for d in range(1, 7)] + [(7, 2), (7, 5), (9, 2), (9, 5)]
    return Landmark((10, 8), (0, 76), ref("tacara"), walk=walk,
                    slots={"guard": [{"t": [9, 2], "face": "+x"}, {"t": [9, 5], "face": "+x"}]}, district=2)


HAD_COL = S.v(15.0)


def hadish(m):
    """Xerxes's palace on the highest platform: a hall of 36 columns behind a portico of 12 on
    the north, rooms down the west and south sides with stone door and window frames, the
    king and his attendants carved on the great door's jambs, XPe-type panels."""
    top = HAD_COL + 4.0
    seed = 71
    _hall_walls(m, 65.5, 224, 0, 160, top, seed)
    # Rooms along the west side (lower, flat roofed, with domestic life on the roof).
    rh = top - 16.0
    wall(m, 65.5, 224, 128, 160, rh, seed + 1, plinth=3.0, dado_h=5.0)
    west = (65.5, 224, 128, 160, 0, rh)
    _windows(m, "+y", west, 6, 0.0, 26.0, 11.0, kind="mixed")
    M.beam_ends(m, "+y", west, rh - 1.0, spacing=4.0, r=0.8, out=1.0)
    M.spouts(m, "+y", west, rh - 2.4, spacing=34.0, material="limestone")
    M.roof(m, 65.5, 224, 128, 160, rh + 0.6, seed=seed, kind="palace", hatches=2, rollers=1, fields=(4, 1))
    M.parapet(m, 65.5, 224, 128, 160, rh + 0.6, 3.5, material="limestone", sides=("+y",),
              stripes=((0.6, "cinnabar"),))
    south = (192, 224, 0, 128, 0, top)
    _windows(m, "+x", south, 5, 8.0, 22.0, 11.0, kind="mixed")
    frieze(m, "+x", (64, 224, 0, 160, 0, top), 2, 126, top - 2.0, "lions", seed)
    frieze(m, "+y", (64, 224, 0, 128, 0, top), 2, 158, top - 2.0, "rosettes", seed)
    zt = crown(m, 64, 224, 0, 128, top, ("+x", "+y", "-y", "-x"), seed, parapet=5.0)
    roof_furniture(m, 64, 224, 0, 128, zt - 6.4, seed, hatches=3, rollers=2, fields=(4, 3))
    # The north portico.
    cols = [(x, tc(d)) for x in (tc(1), tc(3)) for d in (1, 2, 4, 5, 7, 8)]
    _portico_block(m, 18, 64, 0, 160, HAD_COL, cols, "bull", "y", ("-x", "+y", "-y"), seed + 3, r=S.h(0.7))
    north = (65.5, 73.5, 0, 160, 0, top)
    door(m, "-x", north, 64.0, 32.0, 40.0, leaf="gold", jambs="king")
    inscription(m, "+y", (64, 224, 0, 160, 0, top), 20.0, 40.0, top - 22.0, top - 12.0)
    for d, z in ((2, 22.0), (7, 22.0)):
        halo(m, 224.0, tc(d) + 8, z, 12.0, LAMP, 0.6)


def _hadish_landmark():
    cols = {(x, d) for x in (1, 3) for d in (1, 2, 4, 5, 7, 8)}
    walk = [t for t in tiles(0, 3, 0, 9) if t not in cols]
    return Landmark((14, 10), (0, 88), ref("hadish"), walk=walk,
                    slots={"stroll": [{"t": [2, 3]}, {"t": [0, 6]}, {"t": [2, 9]}]}, district=2)


TRI_COL = S.v(11.0)


def tripylon(m):
    """The small central hall with three doors and four columns; its door jambs show the king
    walking under his parasol with attendants, carved and painted."""
    top = TRI_COL + 4.0
    seed = 81
    _hall_walls(m, 0, 128, 0, 112, top, seed, t=12.0)
    for face, w, s0 in (("-x", (0, 12, 0, 112, 0, top), 40.0), ("+x", (116, 128, 0, 112, 0, top), 40.0),
                        ("-y", (0, 128, 0, 12, 0, top), 48.0)):
        door(m, face, w, s0, 32.0, 34.0, leaf="gold", jambs="king")
        carve(m, face_box(face, *w[:4], 0, 34.0, s0, s0 + 32.0, -1.0, 13.0))
    _windows(m, "+y", (0, 128, 100, 112, 0, top), 3, 12.0, 18.0, 10.0, kind="niche")
    frieze(m, "+y", (0, 128, 0, 112, 0, top), 2, 126, top - 2.0, "rosettes", seed)
    frieze(m, "+x", (0, 128, 0, 112, 0, top), 2, 110, top - 2.0, "rosettes", seed + 1)
    col = Column(S.h(0.6), TRI_COL, base="bell", capital="bull", beam="y")
    for x in (tc(2), tc(5)):
        for y in (tc(2), tc(4)):
            column(m, x, y, 0.0, col)
    zt = crown(m, 0, 128, 0, 112, top, ("+x", "+y", "-x", "-y"), seed, parapet=5.0)
    roof_furniture(m, 0, 128, 0, 112, zt - 6.4, seed, hatches=1, rollers=1, fields=(3, 3))


def _tripylon_landmark():
    cols = {(2, 2), (2, 4), (5, 2), (5, 4)}
    walk = [t for t in tiles(1, 6, 1, 5) if t not in cols] + [(0, 3), (7, 3), (3, 0), (4, 0)]
    return Landmark((8, 7), (0, 76), ref("tripylon"), walk=walk,
                    # The guards flank the north door inside the hall: outside it the stair stands.
                    slots={"guard": [{"t": [1, 2], "face": "-x"}, {"t": [1, 4], "face": "-x"}]}, district=2)


# ---------------------------------------------------------------- the Hall of a Hundred Columns

H100_COL = S.v(13.5)


def _scaffold(m, cx, cy, h, r):
    """Lashed timber poles round a rising column, with ledgers every few metres."""
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        x, y = cx + dx * r, cy + dy * r
        rod(m, (x, y, 0), (x, y, h + 4.0), 0.4, "wood_light", tone=0.1)
    for z in np.arange(8.0, h + 4.0, 8.0):
        for a, b in (((-1, -1), (1, -1)), ((-1, 1), (1, 1)), ((-1, -1), (-1, 1)), ((1, -1), (1, 1))):
            rod(m, (cx + a[0] * r, cy + a[1] * r, z), (cx + b[0] * r, cy + b[1] * r, z), 0.3, "wood", tone=0.2)
        fill(m, (cx - r, cx + r, cy - r, cy + r, z - 0.4, z + 0.2), "wood_light",
             lambda X, Y, Z: (np.abs(X - cx) > r * 0.55) & (np.abs(Y - cy) < r * 0.4), tone=0.0)


def hall_100(m):
    """Begun by Xerxes, finished by Artaxerxes I: in 470 a building site. The stone door
    frames stand, mudbrick walls are rising, about a third of the hundred columns are up, some
    crowned, others half built in scaffolds beside earth ramps; drums lie stacked, a capital
    waits on rollers, the portico's two colossal bulls are still being blocked out."""
    seed = 91
    hx0, hx1, hy0, hy1 = 64, 320, 0, 256
    # Rising walls: courses of mudbrick on a finished stone plinth, the stone frames full height.
    for w, face in (((hx0, hx0 + 8, hy0, hy1), "-x"), ((hx1 - 8, hx1, hy0, hy1), "+x"),
                    ((hx0, hx1, hy0, hy0 + 8), "-y"), ((hx0, hx1, hy1 - 8, hy1), "+y")):
        def course(X, Y, Z, w=w):
            u = (X + Y) * 0.15
            return Z < 8.0 + 9.0 * (np.sin(u) * 0.5 + 0.5) * (np.cos(u * 0.37) > -0.2)
        slab(m, *w, 0, 3.0, "ashlar", tone=M.ashlar(3.0, 6.0, seed))
        fill(m, (*w, 3.0, 20.0), "mudbrick", course, tone=lambda X, Y, Z: -0.6 * ((Z % 1.5) < 0.3) + 0.2)
        wall = (*w, 0, 50.0)
        L = 256
        for s0 in (60.0, 180.0):
            fb = face_box(face, *w, 0, 44.0, s0 - 2.5, s0 + 18.5, -0.6, 8.6)
            slab(m, *fb[:4], 0, 44.0, "limestone", tone=0.2)
            carve(m, face_box(face, *w, 0, 38.0, s0 + 0.5, s0 + 15.5, -1.0, 9.0))
            cornice(m, *fb[:4], 44.0, 5.0, 1.0, "limestone")
    # The hundred columns: completion falls off from the portico southward.
    col_full = Column(S.h(0.7), H100_COL, base="square", capital="bull", beam="y")
    xs = [hx0 + 20 + 24 * i for i in range(10)]
    ys = [hy0 + 20 + 24 * j for j in range(10)]
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            h = float(np.sin(i * 12.9898 + j * 78.233) * 43758.5453 % 1.0)
            done = 1.0 - i / 10.0 * 0.9
            if h < done * 0.55:
                column(m, x, y, 0.0, col_full)
            elif h < done * 0.75:
                column(m, x, y, 0.0, Column(S.h(0.7), H100_COL * 0.7, base="square", capital="none"))
            elif h < done + 0.15:
                hh = H100_COL * (0.25 + 0.4 * ((h * 7) % 1.0))
                column(m, x, y, 0.0, Column(S.h(0.7), hh, base="square", capital="none"))
                _scaffold(m, x, y, hh, 5.0)
            else:
                column(m, x, y, 0.0, Column(S.h(0.7), 6.0, base="square", capital="none"))
    # Stone chippings spread over the site, thickest round the working columns; a reed shade
    # over the masons' bench by the portico.
    fill(m, (hx0 + 8, hx1 - 8, hy0 + 8, hy1 - 8, 0, 0.5), "limestone",
         lambda X, Y, Z: hash01(np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), seed) <
         0.08 + 0.25 * (value_noise(X, Y, Z * 0, 18.0, seed) > 0.6), tone=0.5)
    for x, y in ((4, 140), (4, 164), (18, 140), (18, 164)):
        rod(m, (x, y, 0), (x, y, 15.0), 0.4, "wood")
    fill(m, (2, 20, 138, 166, 15.0, 15.8), "straw", tone=lambda X, Y, Z: -0.35 * ((Y * 2.0) % 1.0 < 0.3))
    slab(m, 6, 16, 148, 156, 0, 4.0, "wood", tone=M.timber("y", seed))
    # Earth ramps up to two rising shafts, drums, a capital on rollers.
    for (x, y, h) in ((xs[5], ys[3], 24.0), (xs[7], ys[7], 18.0)):
        fill(m, (x - 6, x + 6, y + 4, y + 40, 0, h), "soil",
             lambda X, Y, Z, y=y, h=h: Z < h * (1 - (Y - y - 4) / 36),
             tone=lambda X, Y, Z: -0.3 * ((X + Z) % 2.0 < 0.5))
    for (x, y) in ((hx0 + 30, 236.0), (200.0, 120.0), (280.0, 40.0)):
        for n in range(3):
            rod(m, (x - 3, y + n * 4.5, 2.2), (x + 3, y + n * 4.5, 2.2), 2.2, "limestone", tone=0.2)
        rod(m, (x - 3, y + 2.2, 6.0), (x + 3, y + 2.2, 6.0), 2.2, "limestone", tone=0.3)
    slab(m, 240, 252, 180, 194, 2.0, 12.0, "limestone", tone=0.25)      # a capital block on rollers
    for yy in (181.0, 187.0, 193.0):
        rod(m, (238, yy, 1.0), (254, yy, 1.0), 1.0, "wood_light")
    # The north portico: two rows of eight columns, some still rising, colossal bulls roughed out.
    # Its finished capitals are human-headed bulls (fact-check §1.2).
    col_portico = Column(S.h(0.7), H100_COL, base="square", capital="hhbull", beam="y")
    for x in (tc(1), tc(3)):
        for d in range(1, 16, 2):
            h = float(np.sin(x * 3.1 + d * 7.7) * 9131.7 % 1.0)
            if h < 0.5:
                column(m, x, tc(d), 0.0, col_portico)
            else:
                hh = H100_COL * (0.35 + 0.4 * h)
                column(m, x, tc(d), 0.0, Column(S.h(0.7), hh, base="square", capital="none"))
                _scaffold(m, x, tc(d), hh, 5.0)
    for y, f in ((4.0, -1), (252.0, 1)):
        # Blocked out where they will stand, facing north: a dressed block, foreparts emerging.
        slab(m, 8, 60, y - 4.5, y + 4.5, 0, 4.0, "limestone")
        slab(m, 22, 60, y - 4.0, y + 4.0, 4.0, 34.0, "limestone",
             tone=lambda X, Y, Z: -0.5 * ((np.floor(Z) + np.floor(X * 0.7)) % 3 == 0))
        ellipsoid(m, (18.0, y, 22.0), (8.0, 3.8, 12.0), "limestone", tone=-0.2)
        ellipsoid(m, (10.0, y, 30.0), (5.0, 3.0, 6.0), "limestone", tone=-0.1)


def _h100_landmark():
    return Landmark((20, 16), (0, 76), ref("hall_100"),
                    slots={"mason": [{"t": [20, d], "face": "-x"} for d in (2, 5, 8, 11, 13, 15)],
                           "hoist": [{"t": [-1, 4], "face": "+x"}, {"t": [-1, 11], "face": "+x"}]},
                    emitters={"dust_a": (200.0, 120.0, 8.0), "dust_b": (120.0, 200.0, 8.0)}, district=3)


# ---------------------------------------------------------------- lower ranges

def _range(m, x0, x1, y0, y1, h, seed, doors=(), windows=(), merlon_sides=("+x", "+y"), wood_court=None,
           material="mudbrick", halls=True, spouts=True):
    """A flat-roofed mudbrick range: plaster with its patches and damp foot, beam ends under
    the roof edge, spouts with their streaks, a roof in drainage fields with hatches, rollers
    and raised hall roofs. `doors`/`windows`: (face, s0, width) on its own box.
    `wood_court`: (x0, x1, y0, y1) open court ringed with painted wooden columns."""
    wall(m, x0, x1, y0, y1, h, seed, plinth=2.5, material=material, dado_h=4.0)
    box = (x0, x1, y0, y1, 0, h)
    for face, s0, w in doors:
        stone_frame(m, face, box, s0, w, 0.0, min(22.0, h - 8), kind="door", leaf="cedar")
        # Soot from the lamps over the doorway.
        fb = face_box(face, x0, x1, y0, y1, min(22.0, h - 8) + 3, h - 1, s0, s0 + w, -0.1, 0.5)
        M.stain(m, fb, lambda X, Y, Z: True, -0.35)
    for face, s0, w in windows:
        stone_frame(m, face, box, s0, w, h - 12.0, 5.0, kind="window")
    for face in merlon_sides:
        M.beam_ends(m, face, box, h - 1.0, spacing=4.0, r=0.75, out=0.9)
        if spouts:
            M.spouts(m, face, box, h - 2.2, spacing=36.0, material="cedar", offset=seed % 11)
    nx, ny = max(1, int(round((x1 - x0) / 48))), max(1, int(round((y1 - y0) / 48)))
    M.roof(m, x0, x1, y0, y1, h + 0.6, seed=seed + 3, kind="palace", hatches=max(1, nx * ny // 6),
           rollers=max(1, nx * ny // 8), fields=(nx, ny))
    if halls:
        _roofscape(m, x0, x1, y0, y1, h + 0.6, seed)
    if merlon_sides:
        M.parapet(m, x0, x1, y0, y1, h + 0.6, 3.5, material="mudbrick", pitch=4.5, sides=merlon_sides)
    if wood_court:
        _wood_court(m, *wood_court, h, seed)


def _wood_court(m, cx0, cx1, cy0, cy1, h, seed, sides=4):
    """An open court ringed with plastered and painted wooden columns under porch roofs, the
    court floor paved."""
    carve(m, (cx0, cx1, cy0, cy1, -1.0, h + 14))
    fill(m, (cx0, cx1, cy0, cy1, 0, 0.4), "limestone", tone=M.paving(8.0, 6.0, seed))
    wood = Column(1.6, h - 4.0, base="square", capital="wood", flutes=0, material="cinnabar")
    for x in np.arange(cx0 + 8, cx1 - 4, 16):
        for y in (cy0 + 8, cy1 - 8):
            column(m, x, y, 0.0, wood)
    porches = [(cx0, cx1, cy0, cy0 + 14), (cx0, cx1, cy1 - 14, cy1)]
    if sides == 4:
        for y in np.arange(cy0 + 24, cy1 - 20, 16):
            for x in (cx0 + 8, cx1 - 8):
                column(m, x, y, 0.0, wood)
        porches += [(cx0, cx0 + 14, cy0, cy1), (cx1 - 14, cx1, cy0, cy1)]
    for b in porches:
        slab(m, *b, h - 4.0, h - 1.0, "cedar", tone=M.timber("x", seed))
        slab(m, *b, h - 1.0, h + 1.6, "mudbrick", tone=M.plus(M.roof_plaster(seed), -0.6))
        # The porch fascia painted in red and blue bands.
        M.painted_bands(m, b, h - 4.0, ((1.0, "lapis"), (1.0, "cinnabar")), out=0.05)


def _roofscape(m, x0, x1, y0, y1, z, seed, cell=48.0):
    """Big ranges are many halls under one outline: some halls stand higher (their clerestory
    windows lit them), so the roof reads as blocks with low parapets, not one slab."""
    from voxel import hash01 as h01
    nx, ny = int((x1 - x0) // cell), int((y1 - y0) // cell)
    for i in range(nx):
        for j in range(ny):
            r = float(h01(i, j, seed))
            if r < 0.45:
                continue
            a0, a1 = x0 + 6 + i * cell, x0 + (i + 1) * cell - 6
            b0, b1 = y0 + 6 + j * cell, y0 + (j + 1) * cell - 6
            up = 3.0 + 4.0 * r
            slab(m, a0, a1, b0, b1, z, z + up, "mudbrick", tone=M.mud_plaster(seed + i * 7 + j, 0.4, z, 0.8))
            for face in ("+x", "+y"):
                L = face_length(face, a0, a1, b0, b1)
                for s0 in np.arange(4.0, L - 6.0, 9.0):
                    stone_frame(m, face, (a0, a1, b0, b1, z, z + up), s0, 3.0, z + 0.8, up - 2.0,
                                kind="window", frame_w=0.6, cornice_h=0.6)
            M.roof(m, a0 - 0.3, a1 + 0.3, b0 - 0.3, b1 + 0.3, z + up + 0.6, seed=seed + i + j, hatches=0,
                   rollers=0, base=-0.6)
            M.parapet(m, a0 - 0.3, a1 + 0.3, b0 - 0.3, b1 + 0.3, z + up + 0.6, 1.2, material="mudbrick", pitch=2.0)


def treasury(m):
    """Low, flat-roofed mudbrick with plastered walls, small high windows and columned halls
    of plastered and painted wooden columns round open courts; the west door set back in a
    porch where the treasurer receives the gifts, guarded."""
    h = 34.0
    seed = 101
    _range(m, 0, 480, 0, 272, h, seed,
           doors=[("+x", 40.0, 14.0)],
           windows=[("+y", s, 5.0) for s in range(30, 460, 36) if not 190 < s < 250] +
           [("+x", s, 5.0) for s in range(20, 260, 36)],
           wood_court=(48, 176, 120, 248))
    # The porch: tiles (13, 16) and (14, 16) open to the west, the door at their back.
    carve(m, (208, 240, 256, 273, 0, h - 6.0))
    door(m, "+y", (208, 240, 240, 256, 0, h), 0.0, 32.0, 24.0, leaf="bronze")
    fill(m, (204, 244, 254, 272, h - 6.0, h - 3.0), "cedar", tone=M.timber("x", seed))
    for court in ((240, 352, 40, 152), (380, 460, 150, 250)):
        _wood_court(m, *court, h, seed, sides=2)
    # Guards' torches either side of the porch.
    for x in (204.0, 244.0):
        halo(m, x, 273.0, 20.0, 9.0, LAMP, 0.5)


def harem(m):
    """Rows of apartments round courts: small four-column halls opening on the courts, stone
    door frames with royal reliefs, lamps at the doors. The strip along its east side is the
    open passage to the Treasury's porch (walk tiles)."""
    h = 30.0
    seed = 111
    _range(m, 0, 288, 16.5, 224, h, seed, doors=[("+y", s, 12.0) for s in (20.0, 110.0, 200.0)],
           windows=[("+y", s, 5.0) for s in (60.0, 150.0, 240.0)])
    _range(m, 288.5, 432, 0, 224, h, seed + 1, doors=[("+x", s, 12.0) for s in (30.0, 100.0, 170.0)] +
           [("+y", 60.0, 12.0)], windows=[("+x", s, 5.0) for s in (64.0, 134.0, 204.0)])
    for cx0, cx1, cy0, cy1 in ((24, 120, 60, 200), (150, 270, 60, 200), (310, 410, 40, 190)):
        carve(m, (cx0, cx1, cy0, cy1, -1.0, h + 14))
        fill(m, (cx0, cx1, cy0, cy1, 0, 0.4), "limestone", tone=M.paving(7.0, 6.0, seed))
        col = Column(1.8, h - 4.0, base="bell", capital="protome", beam="y", flutes=12)
        for x in (cx0 + 10, cx0 + 26):
            for y in (cy0 + 40, cy1 - 40):
                column(m, x, y, 0.0, col)
        slab(m, cx0, cx0 + 34, cy0, cy1, h - 4.0, h - 2.0, "cedar", tone=M.timber("y", seed))
        slab(m, cx0, cx0 + 34, cy0, cy1, h - 2.0, h + 1.6, "mudbrick", tone=M.plus(M.roof_plaster(seed), -0.6))
        M.painted_bands(m, (cx0, cx0 + 34, cy0, cy1), h - 4.0, ((0.8, "lapis"), (0.8, "cinnabar")), sides=("+x",))
        door(m, "+x", (cx0, cx0 + 34, cy0, cy1, 0, h - 4.0), (cy1 - cy0) / 2 - 6, 12.0, 20.0, leaf="gold",
             material="polished")
        # A tree and a basin in each court.
        tx, ty = cx1 - 22, (cy0 + cy1) / 2
        fill(m, (tx - 5, tx + 5, ty - 5, ty + 5, 0, 1.2), "limestone", tone=0.3)
        fill(m, (tx - 4, tx + 4, ty - 4, ty + 4, 0.4, 1.0), "water", tone=0.2)
        halo(m, cx0 + 35, (cy0 + cy1) / 2, 18.0, 8.0, LAMP, 0.6)
    for y in (26.0, 116.0, 206.0):
        halo(m, 22.0 + y * 0.3, 225.0, 18.0, 8.0, LAMP, 0.6)


def garrison(m):
    """Barracks of the guard round a drill court, an armoury hall, a mudbrick gate tower on
    the west with a passage through to the court."""
    h = 28.0
    seed = 121
    _range(m, 0, 208, 0, 384, h, seed, doors=[("+x", s, 10.0) for s in range(30, 380, 60)],
           windows=[("+x", s, 4.0) for s in range(54, 380, 60)], merlon_sides=("+x", "+y", "-x", "-y"))
    carve(m, (48, 160, 80, 288, -1.0, h + 8))          # the drill court: tiles dx 3..9, dy 5..17
    carve(m, (96, 112, 288, 385, -1.0, h + 8))         # the passage under the gate tower: dx 6, dy 18..23
    # The gate tower on the west side, taller, with torches; the passage runs beneath it.
    wall(m, 70, 138, 336, 384, 34.0, seed, plinth=3.0, dado_h=5.0)
    tower = (70, 138, 336, 384, 0, 34.0)
    carve(m, (96, 112, 330, 385, 0, 26.0))
    stone_frame(m, "+y", tower, 25.0, 18.0, 0.0, 25.0, kind="door", leaf="bronze")
    carve(m, (96, 112, 330, 385, 0, 25.0))
    _windows(m, "+x", tower, 2, 27.0, 5.0, 7.0)
    M.roof(m, 70, 138, 336, 384, 34.6, seed=seed, hatches=1, rollers=0, base=-0.5)
    M.parapet(m, 70, 138, 336, 384, 34.6, 4.0, material="mudbrick", pitch=5.0)
    # Braziers in two corners of the drill court (tiles left off the walk).
    for (x, y) in ((56.0, 88.0), (152.0, 280.0)):
        revolve(m, x, y, 0, 6.0, lambda t: 1.0 + 1.6 * t ** 2, "bronze", tone=0.2)
        fill(m, (x - 2.4, x + 2.4, y - 2.4, y + 2.4, 5.0, 7.5), "fire",
             lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 2.4 - (Z - 5.0) * 0.6)
        halo(m, x, y, 7.0, 14.0, LAMP, 0.9)
    for x in (66.0, 142.0):
        halo(m, x, 385.0, 24.0, 10.0, LAMP, 0.6)


def south_stores(m):
    _range(m, 0, 96, 0, 320, 20.0, 131, doors=[("+x", s, 9.0) for s in range(14, 320, 30)],
           merlon_sides=("+x", "+y"), halls=False)


# ---------------------------------------------------------------- the slope

def cistern(m):
    """A basin cut into the rock, its water still, a channel mouth on its west side."""
    rock = lambda X, Y, Z: (hash_t(X, Y) - 0.5) * 0.8
    slab(m, 0, 80, 0, 80, 0, 6.0, "limestone", tone=rock)
    carve(m, (12, 68, 12, 68, 1.5, 7.0))
    slab(m, 12, 68, 12, 68, 1.5, 2.2, "water", tone=0.2)
    carve(m, (36, 44, 68, 81, 2.0, 7.0))
    slab(m, 36, 44, 68, 80, 2.0, 2.5, "water", tone=0.3)
    for x0, y0 in ((4, 4), (70, 70), (70, 6)):
        ellipsoid(m, (x0 + 3, y0 + 3, 6.5), (4.0, 3.5, 2.5), "limestone", tone=-0.2)


def hash_t(X, Y):
    from voxel import value_noise
    return value_noise(X, Y, X * 0 + Y * 0, 3.0, 7)


def quarry(m):
    """The mountain's limestone cut back in steps where the blocks come out: rough weathered
    rock with ledges behind, smooth cut faces with tool marks and rows of wedge slots in
    front, two benches with half-detached blocks, rubble ramps at the sides, and the working
    floor at the foot of the lowest face, where the cutters stand (walk tiles dx 3..16,
    dy 8..14)."""
    def slope(X, Y):            # natural ground rising eastward (towards -y), rugged
        n = value_noise(X, Y, X * 0, 22.0, 141) - 0.5
        return np.clip((240 - Y) / 240, 0, 1) ** 0.8 * 42.0 + n * 8.0

    def cut(X, Y):              # the floor and two benches stepping up eastward
        return np.where(Y >= 128, 0.0, np.where(Y >= 72, 18.0, 34.0))

    inside = lambda X, Y: (X > 40) & (X < 264) & (Y > 16)
    top = lambda X, Y: np.where(inside(X, Y), np.minimum(np.maximum(slope(X, Y), 0.0), cut(X, Y)), slope(X, Y))

    def tone(X, Y, Z):
        cutf = inside(X, Y) & (Z > top(X, Y) - 1.0)
        marks = 0.25 * ((X * 1.3 + Z * 0.4) % 1.6 < 0.4)          # chisel striations on cut faces
        strata = 0.35 * (np.sin(Z * 0.9 + value_noise(X, Y, Z, 30.0, 147) * 4) > 0.6)
        rough = (value_noise(X, Y, Z, 4.0, 143) - 0.5) * 1.2
        return np.where(cutf, 0.4 + marks - 0.1, rough + strata - 0.2)
    field_fill(m, (0, 304, 0, 240, 0, 66), lambda X, Y, Z: Z - top(X, Y), "limestone", tone=tone)
    # Wedge slots along the edges of the benches, waiting for wet wooden wedges.
    for yb, z in ((128.0, 18.0), (72.0, 34.0)):
        carve(m, (44, 260, yb - 0.6, yb + 0.8, z - 2.5, z - 1.0), lambda X, Y, Z: (X % 4.0) < 1.2)
    # Blocks part cut from the benches: separated by trenches, standing on their beds.
    for (x, y, z, w) in ((70, 80, 18, 14), (170, 86, 18, 10), (110, 30, 34, 12), (210, 36, 34, 9)):
        carve(m, (x - 1.2, x + w + 1.2, y - 1.2, y + w * 0.7 + 1.2, z, z + 12.0))
        slab(m, x, x + w, y, y + w * 0.7, z, z + 9.0, "limestone", tone=M.plus(M.ashlar(9.0, 40.0, x), 0.2))
    # Rubble ramps at both sides, chippings spread at the foot.
    for x0, x1 in ((0, 40), (264, 304)):
        fill(m, (x0, x1, 40, 240, 0, 40), "stone",
             lambda X, Y, Z: Z < np.clip((240 - Y) / 200 * 34, 0, None) + (hash_t(X * 2, Y * 2) - 0.5) * 3,
             tone=lambda X, Y, Z: (hash_t(X * 3, Y * 3 + Z) - 0.5) * 1.6)
    # A shade of poles and reed mats where the cutters keep their tools and water jars.
    for x, y in ((20, 210), (36, 210), (20, 232), (36, 232)):
        rod(m, (x, y, 0), (x, y, 16.0), 0.4, "wood")
    fill(m, (18, 38, 208, 234, 16.0, 16.8), "straw", tone=lambda X, Y, Z: -0.35 * ((X * 2.0) % 1.0 < 0.3))
    for i, (x, y) in enumerate(((24, 214), (27, 216), (30, 214))):
        fill(m, (x - 1, x + 1, y - 1, y + 1, 0, 3.0), "roof",
             lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 1.0 - 0.15 * np.abs(Z - 1.6), tone=0.1)


# ---------------------------------------------------------------- the plain

def paradise_gate(m):
    """A mudbrick gate faced with glazed bricks: a blue ground with yellow and white bulls and
    dragons in relief, row above row, after Tol-e Ajori (an Ishtar-Gate type). The passage is
    shown with a flat timber lintel; the original superstructure is unknown."""
    top = 46.0

    def beasts(face, box, L, seed):
        fill(m, face_box(face, *box[:4], 2.5, top, 0, L, -0.3, 0.5), "glaze_blue", tone=M.glazed(1.0, 2.2, seed))
        for i, z in enumerate((17.0, 29.0, 41.0)):
            W = int(L * 2) - 2
            img = R.image(W, 11)
            img[10, :] = "G"
            st = R.GLAZE_BULL if i % 2 == 0 else R.GLAZE_DRAGON
            for x in range(1, W - len(st[0]), len(st[0]) + 3):
                R.stamp(img, st if face in ("+y", "-x") else R.mirror(st), x, 0)
            R.emboss(m, face, box, 0.5, z, img, colours={"lion": "glaze_yellow", "gold": "glaze_yellow",
                                                        "frame": "glaze_yellow"})
    for x0, x1 in ((0, 30.5), (49.5, 80)):
        wall(m, x0, x1, 6, 74, top, 151, plinth=2.5, material="glaze_blue", dado=None)
        box = (x0, x1, 6, 74, 0, top)
        for face in ("+y", "-y", "+x", "-x"):
            if (face == "+x" and x0 == 0) or (face == "-x" and x0 > 40):
                continue
            beasts(face, box, face_length(face, x0, x1, 6, 74), 151)
        M.roof(m, x0 + 1, x1 - 1, 7, 73, top, seed=153, hatches=0, rollers=0, base=-0.5)
        M.parapet(m, x0, x1, 6, 74, top, 6.0, material="glaze_blue", pitch=7.0)
    slab(m, 32, 48, 6, 74, 30.0, 42.0, "glaze_blue", tone=M.glazed(1.0, 2.2, 155))
    M.roof(m, 33, 47, 7, 73, 42.0, seed=155, hatches=0, rollers=0, base=-0.5)
    rod(m, (31, 74.5, 30.0), (49, 74.5, 30.0), 1.2, "cedar")
    rod(m, (31, 5.5, 30.0), (49, 5.5, 30.0), 1.2, "cedar")
    frieze(m, "+y", (32, 48, 6, 74, 0, 42.0), 0, 16.0, 41.0, "rosettes", 155)
    M.parapet(m, 32, 48, 6, 74, 42.0, 5.0, material="glaze_blue", pitch=6.0)


PAVILION_COLS = {(1, 1), (1, 4), (4, 1), (4, 4), (1, 2), (1, 3), (4, 2), (4, 3)}


def pavilion(m):
    """An open columned pavilion over the channel crossing: slender painted wooden columns on
    stone bases, a flat roof with a painted fascia, carpets laid inside, lanterns."""
    h = 34.0
    col = Column(1.7, h, base="bell", capital="wood", flutes=0, material="cinnabar")
    for t in PAVILION_COLS:
        column(m, tc(t[0]), tc(t[1]), 0.0, col)
    flat_roof(m, 14, 82, 14, 82, h, beam_dir="y", depth=5.0, beam_r=1.0, spacing=6.0, overhang=2.0,
              edge_mat="white_paint")
    for face in ("+x", "+y", "-x", "-y"):
        rosette_band(m, face, (14, 82, 14, 82, 0, 0), 0, 68, h + 2.0, h + 4.4, depth=0.5, material="lapis",
                     petals="gold", step=4.0)
    M.parapet(m, 14, 82, 14, 82, h + 5.0, 3.5, material="white_paint", pitch=4.5)
    for (x0, x1, y0, y1, c) in ((20, 34, 38, 58, "cinnabar"), (62, 76, 38, 58, "lapis")):
        slab(m, x0, x1, y0, y1, 0, 0.6, c, tone=lambda X, Y, Z: 0.5 * (((X + Y) % 4.0) < 1.0) - 0.4 *
             ((np.abs(X - (x0 + x1) / 2) > (x1 - x0) / 2 - 1.2) | (np.abs(Y - (y0 + y1) / 2) > (y1 - y0) / 2 - 1.2)))
    for (x, y) in ((tc(1) + 3, tc(2) + 8), (tc(4) - 3, tc(3) - 8)):
        rod(m, (x, y, h), (x, y, h - 6.0), 0.2, "bronze")
        ellipsoid(m, (x, y, h - 7.5), (1.0, 1.0, 1.4), "lamp")
        halo(m, x, y, h - 7.5, 10.0, LAMP, 0.8)


def _pavilion_landmark():
    walk = [t for t in tiles(0, 5, 0, 5) if t not in PAVILION_COLS]
    return Landmark((6, 6), (0, 48), ref("pavilion"), walk=walk,
                    slots={"music": [{"t": [2, 2], "face": "+x"}, {"t": [2, 3], "face": "+x"},
                                     {"t": [3, 3], "face": "-x"}]}, district=4)


def road_station(m):
    """A walled yard with a stable range, a storeroom, a room for the official; the gate west."""
    seed = 161
    for w in ((0, 6, 0, 144), (122, 128, 0, 144), (0, 128, 0, 6), (0, 46.5, 138, 144), (81.5, 128, 138, 144)):
        wall(m, *w, 18.0, seed, plinth=2.0, dado=None)
        M.parapet(m, *w, 18.0, 3.0, material="mudbrick", pitch=4.0)
    # Gate posts and a lintel above head height (the walk tiles under it stay clear).
    rod(m, (46.5, 140, 0), (46.5, 140, 27.0), 1.2, "cedar")
    rod(m, (81.5, 140, 0), (81.5, 140, 27.0), 1.2, "cedar")
    slab(m, 45, 83, 137.5, 142.5, 25.0, 28.0, "cedar", tone=0.2)
    # Stables along the north side: an open shed on posts with a reed roof.
    for y in np.arange(14, 140, 18):
        rod(m, (34, y, 0), (34, y, 18.0), 0.7, "wood")
    slab(m, 6, 36, 6, 138, 18.0, 20.0, "straw", tone=lambda X, Y, Z: -0.3 * ((Y % 2.0) < 0.5))
    for y in np.arange(16, 136, 18):
        slab(m, 22, 30, y, y + 6, 0, 3.0, "limestone", tone=-0.2)
    # Storeroom and the official's room along the east side.
    _range(m, 65.5, 122, 6, 78.5, 24.0, seed, doors=[("-x", 10.0, 10.0), ("+y", 20.0, 10.0)],
           windows=[("+x", 20.0, 4.0)], merlon_sides=("+x", "+y"), spouts=False)
    halo(m, 70.0, 75.0, 14.0, 9.0, LAMP, 0.6)


def _road_station_landmark():
    walk = tiles(3, 6, 5, 7) + [(3, 8), (4, 8)] + [(3, y) for y in range(1, 5)]
    return Landmark((8, 9), (0, 40), ref("road_station"), walk=sorted(set(walk)),
                    slots={"seal_check": [{"t": [3, 8], "face": "+y"}, {"t": [4, 7], "face": "+y"}],
                           "door": [{"t": [3, 1], "face": "+x"}]}, district=5)


# ---------------------------------------------------------------- Naqsh-e Rostam

def naqsh_cliff(m):
    """The pinkish cliff with Darius I's cross-shaped tomb façade facing south: a blank lower
    arm; the middle arm a palace front with four engaged columns with bull capitals and a door;
    the upper arm the king on a three-stepped dais before a fire altar, under the winged figure,
    on a throne platform carried by the subject peoples; Gobryas and Aspathines at the sides;
    DNa and DNb panels."""
    from voxel import value_noise

    def front(Y):          # the cliff face, near x = 112, gently irregular
        return 112.0 + (value_noise(Y, Y * 0, Y * 0, 28.0, 171) - 0.5) * 14.0

    def ends(Y):           # the outcrop falls away at both ends instead of stopping in a section
        return np.clip(np.minimum(Y - 4, 332 - Y) / 70.0, 0, 1) ** 0.7

    def ridge(Y):
        return (104.0 + (value_noise(Y, Y * 0, Y * 0, 40.0, 173) - 0.5) * 24.0) * ends(Y)

    def rock(X, Y, Z):
        a = X - (front(Y) * (0.55 + 0.45 * ends(Y)) - np.clip(Z - ridge(Y) + 30, 0, None) * 0.8 +
                 (value_noise(X, Y, Z, 6.0, 175) - 0.5) * 3)
        b = Z - (ridge(Y) + (value_noise(X, Y, Z * 0, 9.0, 177) - 0.5) * 8 - np.clip(X - 60, 0, None) * 0.1)
        return np.maximum(a, b)

    field_fill(m, (0, 144, 0, 336, 0, 120), rock, "naqsh",
         tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 181) - 0.5) * 0.9 +
         (value_noise(X * 0.3, Y, Z * 2.5, 6.0, 179) - 0.5) * 0.8)
    # Scree at the foot.
    fill(m, (90, 144, 0, 336, 0, 12), "naqsh", lambda X, Y, Z: Z < np.clip(16 - (X - front(Y)) * 0.6, 0, 12) +
         (hash_t(X * 2, Y * 2) - 0.5) * 2, tone=lambda X, Y, Z: (hash_t(X * 4, Y * 4) - 0.5) * 1.6 - 0.2)
    # The tomb, recessed into a dressed plane.
    cy, xf = 168.0, 104.0
    def cross(Y, Z):
        vert = (np.abs(Y - cy) < 17) & (Z > 14) & (Z < 109)
        horiz = (np.abs(Y - cy) < 36) & (Z > 44) & (Z < 78)
        return vert | horiz
    carve(m, (xf, 144, cy - 40, cy + 40, 12, 112), lambda X, Y, Z: cross(Y, Z))
    carve(m, (xf - 5, xf, cy - 40, cy + 40, 12, 112), lambda X, Y, Z: cross(Y, Z))
    xf -= 5
    fill(m, (xf - 2, xf, cy - 40, cy + 40, 12, 112), "naqsh", lambda X, Y, Z: cross(Y, Z), tone=0.6)
    # Middle arm: the palace front.
    face_x = xf
    for yy in (cy - 27, cy - 9, cy + 9, cy + 27):
        fill(m, (face_x - 0.5, face_x + 2.2, yy - 1.8, yy + 1.8, 46, 70), "naqsh",
             lambda X, Y, Z, yy=yy: np.hypot(X - face_x, Y - yy) < 1.8, tone=0.5)
        fill(m, (face_x - 0.5, face_x + 3.0, yy - 3.5, yy + 3.5, 70, 74), "naqsh", tone=0.6)
        for side in (-1, 1):
            fill(m, (face_x - 0.5, face_x + 3.0, yy + side * 2.0 - 1.4, yy + side * 2.0 + 1.4, 71, 75), "naqsh",
                 tone=0.3)
    fill(m, (face_x - 0.5, face_x + 2.0, cy - 36, cy + 36, 74, 78), "naqsh", tone=0.4,
         mask=lambda X, Y, Z: ((Y * 1.2) % 2.0 < 1.2) | (Z > 76.5))
    carve(m, (face_x - 0.5, face_x + 6, cy - 4.5, cy + 4.5, 46, 60))
    fill(m, (face_x + 5, face_x + 6, cy - 4.5, cy + 4.5, 46, 60), "polished", tone=-1.5)
    cornice(m, face_x - 0.5, face_x + 0.5, cy - 6, cy + 6, 60, 3.0, 0.8, "naqsh")
    # Upper arm: the throne platform borne by the peoples, the king before the fire altar,
    # the winged figure in its disc above (relief.naqsh_upper).
    img = R.naqsh_upper(68, 60)
    R.emboss(m, "+x", (0, face_x, 0, 336, 0, 0), 336 - (cy + 17), 108.5, img,
             colours={"stone": "naqsh", "robe": "naqsh", "legs": "naqsh", "frame": "naqsh", "gold": "naqsh",
                      "trim": "naqsh", "wing": "naqsh", "petal": "naqsh", "hair_black": "naqsh", "felt": "naqsh",
                      "heart": "naqsh"})
    # Gobryas and Aspathines beside the façade, and the inscription panels.
    for yy in (cy - 46, cy + 42):
        fill(m, (face_x - 1.0, face_x + 1.0, yy, yy + 4, 46, 62), "naqsh", tone=0.45)
        fill(m, (face_x - 1.0, face_x + 1.0, yy + 0.8, yy + 3.2, 62, 64.5), "naqsh", tone=0.55)
    inscription(m, "+x", (0, face_x, 0, 336, 0, 0), cy - 12, cy + 12, 25.0, 40.0, material="naqsh")
    inscription(m, "+x", (0, face_x, 0, 336, 0, 0), cy - 34, cy - 19, 80.0, 100.0, material="naqsh")


def kaba(m):
    """Ka'ba-ye Zartosht: a square tower of pale limestone with blind windows of dark stone,
    a stair of thirty steps to its single high door on the north side; purpose debated."""
    S1 = Scale(0.85)
    half = S1.h(7.3) / 2
    c = 24.0
    top = S1.v(12.0)
    for i, z in enumerate((0.0, 1.6, 3.2)):
        slab(m, c - half - 4 + i * 1.3, c + half + 4 - i * 1.3, c - half - 4 + i * 1.3, c + half + 4 - i * 1.3,
             z, z + 1.6, "limestone", tone=0.1)
    slab(m, c - half, c + half, c - half, c + half, 4.8, top, "cream", tone=M.ashlar(2.2, 5.5, 191))
    cornice(m, c - half, c + half, c - half, c + half, top, 2.2, 0.8, "limestone")
    slab(m, c - half - 0.5, c + half + 0.5, c - half - 0.5, c + half + 0.5, top + 2.2, top + 3.0, "limestone", tone=0.3)
    for face in ("+x", "+y", "-x", "-y"):
        wall = (c - half, c + half, c - half, c + half, 0, top)
        L = 2 * half
        rows = ((12.0, 3) , (24.0, 3), (36.0, 2))
        for z, n in rows:
            for j in range(n):
                s0 = L * (0.18 + 0.64 * j / max(n - 1, 1)) - 1.6
                if face == "-x" and z < 30 and abs(s0 + 1.6 - L / 2) < 4:
                    continue
                fill(m, face_box(face, *wall[:4], z, z + 5.5, s0, s0 + 3.2, -0.3, 0.6), "polished", tone=-0.4)
    # The door and its stair on the north face (hidden in the default view).
    door_z = S1.v(6.35)
    carve(m, face_box("-x", c - half, c + half, c - half, c + half, door_z, door_z + 8.0, half - 3.0, half + 3.0, -0.5, 2.0))
    fill(m, face_box("-x", c - half, c + half, c - half, c + half, door_z, door_z + 8.0, half - 3.0, half + 3.0, 2.0, 2.6),
         "polished", tone=-1.0)
    stair(m, 0.5, c - half, c - 3.5, c + 3.5, 0, door_z, "+x", step=1.0)


def cyrus_tomb(m):
    """The tomb of Cyrus at Pasargadae: six stone steps carrying a small gabled chamber with a
    low door. Modelled on the grid axes with the door on the west side; the real door faces
    north-west (Iranica, 'Cyrus v. Tomb')."""
    S1 = Scale(1.0)
    cx, cy = 40.0, 40.0
    a, b = S1.h(13.35) / 2, S1.h(12.3) / 2
    z = 0.0
    for i, hgt in enumerate((1.05, 1.05, 1.0, 0.575, 0.575, 0.575)):
        shrink = S1.h(0.55) * i
        h = S1.v(hgt)
        slab(m, cx - a + shrink, cx + a - shrink, cy - b + shrink, cy + b - shrink, z, z + h, "cream",
             tone=M.ashlar(h, 7.0, 201 + i))
        z += h
    ca, cb = S1.h(6.4) / 2, S1.h(5.35) / 2
    wall_h = S1.v(2.4)
    slab(m, cx - ca, cx + ca, cy - cb, cy + cb, z, z + wall_h, "cream", tone=M.ashlar(S1.v(0.8), 6.0, 211))
    slab(m, cx - ca - 0.6, cx + ca + 0.6, cy - cb - 0.6, cy + cb + 0.6, z + wall_h, z + wall_h + 1.2, "cream", tone=0.3)
    ridge = S1.v(2.0)
    fill(m, (cx - ca - 0.6, cx + ca + 0.6, cy - cb - 0.6, cy + cb + 0.6, z + wall_h + 1.2, z + wall_h + 1.2 + ridge),
         "cream", lambda X, Y, Z: (Z - z - wall_h - 1.2) < ridge * (1 - np.abs(X - cx) / (ca + 0.6)),
         tone=lambda X, Y, Z: 0.25 * ((Y % 5.0) < 0.5) + 0.2 * np.sign(cx - X))
    dw, dh = S1.h(0.78), S1.v(1.39)
    carve(m, (cx - dw / 2, cx + dw / 2, cy + cb - 2.0, cy + cb + 0.5, z + 0.4, z + 0.4 + dh))
    fill(m, (cx - dw / 2, cx + dw / 2, cy + cb - 2.2, cy + cb - 1.8, z + 0.4, z + 0.4 + dh), "ink", tone=0.5)

LANDMARKS = {
    "parsa.great_stair": _great_stair_landmark(),
    "parsa.gate_all_lands": _gate_landmark(),
    "parsa.apadana": _apadana_landmark(),
    "parsa.apadana_stair_n": _stair_landmark("apadana_stair_n", *APA_N, 1),
    "parsa.apadana_stair_e": _stair_landmark("apadana_stair_e", *APA_E, 1),
    "parsa.tacara": _tacara_landmark(),
    "parsa.tacara_stair_s": _stair_landmark("tacara_stair_s", *TAC_S, 2),
    "parsa.hadish": _hadish_landmark(),
    "parsa.hadish_stair_w": _stair_landmark("hadish_stair_w", *HAD_W, 2),
    "parsa.tripylon": _tripylon_landmark(),
    "parsa.tripylon_stair": _stair_landmark("tripylon_stair", *TRI_N, 2),
    "parsa.hall_100": _h100_landmark(),
    "parsa.treasury": Landmark((30, 17), (0, 60), ref("treasury"), walk=[(13, 16), (14, 16)],
                               slots={"gift_drop": [{"t": [13, 17], "face": "-y"}, {"t": [14, 17], "face": "-y"}],
                                      "guard": [{"t": [12, 17], "face": "+y"}, {"t": [15, 17], "face": "+y"}],
                                      "treasurer": [{"t": [13, 16], "face": "+y"}]}, district=3),
    "parsa.harem": Landmark((27, 14), (0, 48), ref("harem"), walk=[(dx, 0) for dx in range(18)], district=3),
    "parsa.garrison": Landmark((13, 24), (0, 66), ref("garrison"),
                               walk=[t for t in tiles(3, 9, 5, 17) if t not in ((3, 5), (9, 17))] +
                               [(6, dy) for dy in range(18, 24)],
                               slots={"drill": [{"t": [5, 8 + i]} for i in range(6)]},
                               emitters={"brazier": (56.0, 88.0, 7.5)}, district=3),
    "parsa.south_stores": Landmark((6, 20), (0, 32), ref("south_stores"), district=3),
    "parsa.cistern": Landmark((5, 5), (0, 16), ref("cistern"), district=3),
    "parsa.quarry": Landmark((19, 15), (0, 62), ref("quarry"), walk=tiles(3, 15, 8, 14),
                             slots={"cut": [{"t": [5, 8], "face": "-y"}, {"t": [9, 8], "face": "-y"},
                                            {"t": [14, 8], "face": "-y"}, {"t": [6, 10], "face": "-y"}]},
                             emitters={"dust": (88.0, 132.0, 4.0)}, district=3),
    "parsa.paradise_gate": Landmark((5, 5), (0, 60), ref("paradise_gate"), walk=[(2, y) for y in range(5)], district=4),
    "parsa.pavilion": _pavilion_landmark(),
    "parsa.road_station": _road_station_landmark(),
    "parsa.naqsh_cliff": Landmark((9, 21), (0, 132), ref("naqsh_cliff"), district=6),
    "parsa.kaba": Landmark((3, 3), (0, 60), ref("kaba"), district=6),
    "parsa.cyrus_tomb": Landmark((5, 5), (0, 56), ref("cyrus_tomb"), district=6),
}
