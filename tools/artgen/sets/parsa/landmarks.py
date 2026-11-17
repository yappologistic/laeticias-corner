"""Pārsa's landmarks (persepolis.md §2.3, §3.2), modelled in grid axes: footprint offset dx runs
south (+x), dy west (+y), so the origin tile is the north-east corner and the south and west
faces are the ones the camera sees. One tile is 16 design units (4.7 m at s = 0.85); heights
use 5 s design units per metre (arch.Scale).
"""

import numpy as np

from arch import (Column, Scale, ashlar_tone, carve, column, cornice, cypress_band, ellipsoid, field_fill,
                  face_box, fill, flat_roof, glazed_panel, halo, inscription, lion_bull, merlons,
                  mudbrick_wall, plaster_tone, procession, revolve, rod, rosette_band, slab, stair,
                  stone_frame)
from setbuild import Landmark

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


# ---------------------------------------------------------------- the Apadāna

APA_COL = S.v(19.5)                     # base to saddle: 'more than 19 m' (Iranica)
APA_ROOF = APA_COL + 6.0
APA_HALL = APA_COL + 5.0                # the hall roof stands a little above the porticoes
APA_TOWER = APA_HALL + 12.0
PORTICO_ROWS = (6, 8, 10, 13, 15, 17)   # the wider central bay at 11..12 leads to the throne


def _incense_stand(m, x, y, h=16.0):
    """A tall bronze incense burner with a conical lid, as in the audience relief."""
    revolve(m, x, y, 0, 2.0, lambda t: 2.2 - 0.8 * t, "bronze", tone=0.1)
    rod(m, (x, y, 2.0), (x, y, h - 4.5), 0.5, "bronze", tone=0.2)
    revolve(m, x, y, h - 4.5, h - 2.5, lambda t: 1.2 + 1.0 * t, "bronze", tone=0.3)
    revolve(m, x, y, h - 2.5, h, lambda t: 2.2 * (1 - t) + 0.2, "gold", tone=0.2)


def _tower(m, x0, x1, y0, y1, top, seed):
    """A corner tower: mudbrick on a stone plinth, two storeys of stone-framed windows and
    niches, a glazed rosette frieze under stepped merlons."""
    mudbrick_wall(m, x0, x1, y0, y1, 0, top, plinth=4.0, seed=seed, dado=(6.0, "hematite"))
    wall = (x0, x1, y0, y1, 0, top)
    for face in ("+x", "+y", "-x", "-y"):
        L = (y1 - y0) if face in ("+x", "-x") else (x1 - x0)
        for i, s0 in enumerate((L * 0.2, L * 0.62)):
            stone_frame(m, face, wall, s0, 9.0, 20.0, 14.0, kind="niche" if i == 0 else "window")
            stone_frame(m, face, wall, s0, 9.0, 52.0, 12.0, kind="window" if (i + seed) % 2 else "niche")
        glazed_panel(m, face, wall, 2.0, L - 2.0, top - 12.0, top - 5.0, "rosettes")
    slab(m, x0 - 0.8, x1 + 0.8, y0 - 0.8, y1 + 0.8, top, top + 1.0, "limestone", tone=0.3)
    merlons(m, x0, x1, y0, y1, top + 1.0, 6.0, "limestone", pitch=7.0)
    # Lamplit windows on the upper storey of the faces the camera sees.
    for face in ("+x", "+y"):
        L = (y1 - y0) if face in ("+x", "-x") else (x1 - x0)
        b = face_box(face, x0, x1, y0, y1, 52.0, 63.0, L * 0.62 + 2.0, L * 0.62 + 7.0, 2.6, 3.4)
        if (seed + (face == "+y")) % 2:
            fill(m, b, "lamp", tone=-0.5)
            cx, cy = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2
            halo(m, cx, cy, 57.0, 9.0, LAMP, 0.7)


def _portico_roof(m, x0, x1, y0, y1, beam, outer):
    """A portico roof that ends just past the outer columns, so their capitals show."""
    flat_roof(m, x0, x1, y0, y1, APA_COL, beam_dir=beam, depth=6.0, beam_r=1.2, spacing=8.0,
              overhang=0.0, edge_mat="white_paint", top_mat="mudbrick")
    # A painted band of rosettes along the fascia of the outer faces.
    for face in outer:
        L = (y1 - y0) if face in ("+x", "-x") else (x1 - x0)
        rosette_band(m, face, (x0, x1, y0, y1, 0, 0), 0, L, APA_COL + 2.6, APA_COL + 5.2, depth=0.5,
                     material="lapis", petals="gold", step=4.0)
    merlons(m, x0, x1, y0, y1, APA_ROOF, 5.0, "limestone", pitch=6.0, sides=outer)


def apadana(m):
    hall = (5 * T + 1.5, 19 * T - 1.5, 5 * T + 1.5, 19 * T - 1.5)   # inset: nothing on walk tiles
    hx0, hx1, hy0, hy1 = hall
    wt = 9.0
    # The hall: thick walls of mudbrick on stone, plastered and painted red where they face the
    # porticoes, with a glazed frieze under the roof; doors and windows in stone frames.
    for wall in ((hx0, hx0 + wt, hy0, hy1), (hx1 - wt, hx1, hy0, hy1),
                 (hx0, hx1, hy0, hy0 + wt), (hx0, hx1, hy1 - wt, hy1)):
        mudbrick_wall(m, *wall, 0, APA_HALL, plinth=3.0, seed=11, material="cinnabar", dado=(5.0, "hematite"))
    north = (hx0, hx0 + wt, hy0, hy1, 0, APA_HALL)
    west = (hx0, hx1, hy1 - wt, hy1, 0, APA_HALL)
    east = (hx0, hx1, hy0, hy0 + wt, 0, APA_HALL)
    L = hy1 - hy0
    for face, wall in (("-x", north), ("+y", west), ("-y", east)):
        stone_frame(m, face, wall, L / 2 - 8.0, 16.0, 0.0, 42.0, kind="door", leaf="gold")
        for s0 in (L * 0.14, L * 0.78):
            stone_frame(m, face, wall, s0, 12.0, 0.0, 32.0, kind="door", leaf="bronze")
        for s0 in (L * 0.32, L * 0.6):
            stone_frame(m, face, wall, s0, 9.0, 16.0, 16.0, kind="window")
        inscription(m, face, wall, L / 2 - 7.0, L / 2 + 7.0, 52.0, 58.0)
        glazed_panel(m, face, wall, 0, L, APA_COL - 12.0, APA_COL - 5.0, "rosettes")
    flat_roof(m, hx0, hx1, hy0, hy1, APA_HALL, beam_dir="y", depth=6.0, beam_r=1.2, spacing=9.0,
              overhang=0.0, edge_mat="white_paint")
    for face in ("+x", "-x", "+y", "-y"):
        rosette_band(m, face, (hx0, hx1, hy0, hy1, 0, 0), 0, hx1 - hx0, APA_HALL + 2.6, APA_HALL + 5.2,
                     depth=0.5, material="lapis", petals="gold", step=4.0)
    merlons(m, hx0, hx1, hy0, hy1, APA_HALL + 6.0, 4.0, "limestone", pitch=5.0)
    # Porticoes: two rows of six columns each.
    bulls = Column(S.h(0.8), APA_COL, base="bell", capital="bull", beam="y")
    for x in (tc(1), tc(3)):
        for d in PORTICO_ROWS:
            column(m, x, tc(d), 0.0, bulls)
    _portico_roof(m, tc(1) - 7.0, 5 * T, 5 * T, 19 * T, "y", ("-x",))
    griffins = Column(S.h(0.8), APA_COL, base="bell", capital="griffin", beam="x")
    lions = Column(S.h(0.8), APA_COL, base="bell", capital="lion", beam="x")
    for d in PORTICO_ROWS:
        for y in (tc(20), tc(22)):
            column(m, tc(d), y, 0.0, griffins)
        for y in (tc(1), tc(3)):
            column(m, tc(d), y, 0.0, lions)
    _portico_roof(m, 5 * T, 19 * T, 19 * T, tc(22) + 7.0, "x", ("+y",))
    _portico_roof(m, 5 * T, 19 * T, tc(1) - 7.0, 5 * T, "x", ("-y",))
    # South service rooms: a lower closed range.
    sx0 = 19 * T
    sx0 = 19 * T + 1.5
    mudbrick_wall(m, sx0, 24 * T, 5 * T, 19 * T, 0, 52.0, plinth=3.0, seed=13, dado=(5.0, "hematite"))
    srooms = (sx0, 24 * T, 5 * T, 19 * T, 0, 52.0)
    for i in range(5):
        stone_frame(m, "+x", srooms, 14.0 + i * 44.0, 8.0, 0.0, 22.0, kind="door" if i % 2 else "niche",
                    leaf="cedar")
        stone_frame(m, "+x", srooms, 34.0 + i * 44.0, 7.0, 28.0, 10.0, kind="window")
    slab(m, sx0, 24 * T, 5 * T, 19 * T, 52.0, 54.0, "mudbrick", tone=plaster_tone(21, 0.3))
    merlons(m, sx0, 24 * T, 5 * T, 19 * T, 54.0, 5.0, "limestone", pitch=6.0, sides=("+x",))
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
    return Landmark(
        (24, 24), (0, 112), ref("apadana"), walk=walk,
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

def relief_front(m, face, wall, s0, s1, z0, z1, kind="delegations", seed=0):
    """A stair façade carved in registers (persepolis.md §3.1): figures in profile between
    rosette borders, a cypress row along the top, an inscription panel in the middle."""
    H = z1 - z0
    rosette_band(m, face, wall, s0, s1, z0, z0 + H * 0.14, material="limestone", petals="gold")
    regs = 2 if H > 12 else 1
    rh = (H * 0.72) / regs
    for i in range(regs):
        a = z0 + H * 0.16 + i * rh
        procession(m, face, wall, s0, s1, a, a + rh * 0.95, seed=seed + i, spears=(kind == "guards"),
                   facing=1 if i % 2 == 0 else -1,
                   kinds=("persian", "mede") if kind != "servants" else ("mede",))
    cypress_band(m, face, wall, s0, s1, z1 - H * 0.12, z1)


def relief_stair(m, fw, fh, rise, axis, low, flights, front_kind="delegations", seed=0, merlon=True):
    """A Pārsa stair block of `rise` design units: straight flights (tile ranges across the
    axis) climbing from the `low` end along `axis`, low stone parapets crowned with stepped
    merlons, and the faces between and beside the flights carved and painted."""
    X1, Y1 = fw * T, fh * T
    along_x = axis == "x"
    up = ("+" if low == "lo" else "-") + axis
    occupied = []
    for a, b in flights:
        c0, c1 = a * T, (b + 1) * T
        occupied.append((c0, c1))
        if along_x:
            stair(m, 0, X1, c0, c1, 0, rise, up, step=1.2, material="limestone")
        else:
            stair(m, c0, c1, 0, Y1, 0, rise, up, step=1.2, material="limestone")
    # Solid blocks (parapets and the carved centre) wherever no flight runs.
    edges = sorted({0, *(c for ab in occupied for c in ab), (Y1 if along_x else X1)})
    span = Y1 if along_x else X1
    for c0, c1 in zip(edges, edges[1:]):
        if any(a <= c0 and c1 <= b for a, b in occupied):
            continue
        top = rise + 4.0
        box = (0, X1, c0, c1, 0, top) if along_x else (c0, c1, 0, Y1, 0, top)
        slab(m, *box, "limestone", tone=ashlar_tone(3.0, 8.0, seed + 31))
        face = ("-" if low == "lo" else "+") + axis
        fb = box
        L = c1 - c0
        if L > 20:
            relief_front(m, face, fb, 1.0, L - 1.0, 1.0, top - 1.0, front_kind, seed)
        else:
            lion_bull(m, face, fb, 1.0, L - 1.0, 1.5, top - 1.5, flip=c0 > span / 2)
        if merlon:
            merlons(m, *box[:4], top, 2.6, "limestone", pitch=3.0, sides=(face,))


def _stair_landmark(fn, fw, fh, rise, axis, low, flights, district, **kw):
    """Walk tiles along each flight; floors rise with the steps (design units)."""
    walk, floor = [], {}
    n = fw if axis == "x" else fh
    for a, b in flights:
        for c in range(a, b + 1):
            for i in range(n):
                t = (i, c) if axis == "x" else (c, i)
                walk.append(t)
                frac = (i + 1) / n if low == "lo" else (n - i) / n
                floor[t] = rise * frac + 1.2
    return Landmark((fw, fh), (0, int(rise) + 12), ref(fn, **kw), walk=walk, floor=floor, district=district)


def apadana_stair_n(m):
    relief_stair(m, 3, 14, 8.0, "x", "lo", [(1, 2), (11, 12)], "delegations", seed=3)


def apadana_stair_e(m):
    relief_stair(m, 12, 3, 8.0, "y", "lo", [(1, 2), (9, 10)], "delegations", seed=5)


def tacara_stair_s(m):
    relief_stair(m, 3, 8, 16.0, "x", "hi", [(1, 1), (6, 6)], "guards", seed=7)


def hadish_stair_w(m):
    relief_stair(m, 6, 4, 24.0, "y", "hi", [(1, 1), (4, 4)], "servants", seed=9)


def tripylon_stair(m):
    relief_stair(m, 2, 5, 8.0, "x", "lo", [(0, 0), (4, 4)], "nobles", seed=11, merlon=True)


def stair_relief_kit(m):
    relief_stair(m, 2, 1, 8.0, "x", "lo", [(0, 0)], seed=13)


# ---------------------------------------------------------------- the great stairway

GS_STEP = 1.4


def great_stair(m):
    """Two symmetrical stairs against the terrace face: the lower flights start side by side
    at the centre and climb outward to square landings, the upper flights turn back and climb
    inward to one top landing (persepolis.md §2.3). Shallow broad steps, low plain parapets;
    no reliefs (they are on the Apadāna)."""
    L1, L2 = 24.0, 48.0                       # landing and terrace heights (3 and 6 levels)
    wall = ashlar_tone(4.0, 10.0, 41, polygonal=0.4)
    # The mass under everything, faced with big ashlar blocks.
    slab(m, 0, 48, 16, 112, 0, L1, "ashlar", tone=wall)               # north landing
    slab(m, 240, 288, 16, 112, 0, L1, "ashlar", tone=wall)            # south landing
    slab(m, 48, 112, 16, 64, 0, L1, "ashlar", tone=wall)              # under the upper flights
    slab(m, 176, 240, 16, 64, 0, L1, "ashlar", tone=wall)
    slab(m, 112, 176, 0, 64, 0, L2, "ashlar", tone=wall)              # top landing and centre face
    slab(m, 0, 112, 0, 16, 0, L2, "ashlar", tone=wall)                # backing against the terrace
    slab(m, 176, 288, 0, 16, 0, L2, "ashlar", tone=wall)
    # Flights.
    stair(m, 48, 128, 64, 112, 0, L1, "-x", step=GS_STEP)
    stair(m, 160, 240, 64, 112, 0, L1, "+x", step=GS_STEP)
    stair(m, 48, 112, 16, 64, L1, L2, "+x", step=GS_STEP)
    stair(m, 176, 240, 16, 64, L1, L2, "-x", step=GS_STEP)
    # Paving of the landings.
    for x0, x1, y0, y1, z in ((0, 48, 16, 112, L1), (240, 288, 16, 112, L1), (112, 176, 0, 64, L2)):
        slab(m, x0, x1, y0, y1, z - 0.6, z, "limestone", tone=ashlar_tone(20, 6.0, 43))
    # Low parapets: along the outer edge of the lower flights and landings, along the inner
    # edge of the upper flights and the top landing, at the ends of the landings.
    P = 2.4
    stair(m, 48, 128, 108, 112, L1 * 0 + P, L1 + P, "-x", step=GS_STEP, material="limestone")
    stair(m, 160, 240, 108, 112, P, L1 + P, "+x", step=GS_STEP, material="limestone")
    for x0, x1 in ((0, 48), (240, 288)):
        slab(m, x0, x1, 108, 112, 0, L1 + P + 0.6, "limestone", tone=0.2)
    slab(m, 0, 4, 16, 112, 0, L1 + P + 0.6, "limestone", tone=0.2)
    slab(m, 284, 288, 16, 112, 0, L1 + P + 0.6, "limestone", tone=0.2)
    stair(m, 48, 112, 60, 64, L1 + P, L2 + P, "+x", step=GS_STEP)
    stair(m, 176, 240, 60, 64, L1 + P, L2 + P, "-x", step=GS_STEP)
    slab(m, 112, 176, 60, 64, 0, L2 + P + 0.6, "limestone", tone=0.2)


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
            floor[(d, y)] = L1 * (128 - 16 * d) / 80 + GS_STEP
    for d in range(10, 15):                             # lower flight south
        for y in (4, 5):
            walk.append((d, y))
            floor[(d, y)] = L1 * (16 * (d + 1) - 160) / 80 + GS_STEP
    for x in (1, 2, 15, 16):                            # landings
        for y in range(1, 6):
            walk.append((x, y))
            floor[(x, y)] = L1
    for d in range(3, 7):                               # upper flight north, rising to +x
        for y in (1, 2):
            walk.append((d, y))
            floor[(d, y)] = L1 + (L2 - L1) * (16 * (d + 1) - 48) / 64 + GS_STEP
    for d in range(11, 15):                             # upper flight south, rising to -x
        for y in (1, 2):
            walk.append((d, y))
            floor[(d, y)] = L1 + (L2 - L1) * (240 - 16 * d) / 64 + GS_STEP
    for x in range(7, 11):                              # the top landing
        for y in (0, 1, 2):
            walk.append((x, y))
            floor[(x, y)] = L2
    return Landmark((18, 7), (0, 60), ref("great_stair"), walk=walk, floor=floor,
                    slots={"guard": [{"t": [7, 0], "face": "+y"}, {"t": [10, 0], "face": "+y"}],
                           "storyteller": [{"t": [8, 7], "face": "+y"}]},
                    district=0)


# ---------------------------------------------------------------- the Gate of All Lands

GATE_COL = S.v(16.5)                       # the commonly repeated figure (persepolis.md §11)


def gate_all_lands(m):
    top = GATE_COL + 6.0
    wt = 11.0
    seed = 51
    walls = [(0, wt, 0, 96), (96 - wt, 96, 0, 31.5), (96 - wt, 96, 64.5, 96),
             (0, 31.5, 96 - wt, 96), (64.5, 96, 96 - wt, 96), (0, 31.5, 0, wt), (64.5, 96, 0, wt)]
    for w in walls:
        mudbrick_wall(m, *w, 0, top, plinth=3.0, seed=seed, dado=(5.0, "hematite"))
    # Lintels over the three doors.
    for box in ((32, 64, 96 - wt, 96), (32, 64, 0, wt), (96 - wt, 96, 32, 64)):
        slab(m, *box, 50.0, top, "mudbrick", tone=plaster_tone(seed))
    # Stone jambs and cornices of the west and east doors (the colossi's blocks).
    for y0, y1, face in ((96 - wt - 2, 96 + 1, "+y"), (-1, wt + 2, "-y")):
        for x0 in (28.0, 64.0):
            slab(m, x0, x0 + 4.0, y0, y1, 0, 50.0, "limestone", tone=0.2)
        slab(m, 28.0, 68.0, y0, y1, 50.0, 54.0, "limestone", tone=0.1)
        cornice(m, 28.0, 68.0, y0 + 0.5, y1 - 0.5, 54.0, 5.0, 1.2, "limestone")
    stone_frame(m, "+x", (96 - wt, 96, 0, 96, 0, top), 32.0, 32.0, 0.0, 40.0, kind="door", leaf="gold")
    carve(m, (96 - wt - 1, 97, 32, 64, 0, 40))
    # The colossi: bulls striding out of the west door, winged human-headed bulls at the east.
    for cx in (24.0, 72.0):
        colossus(m, cx, 84.0, +1, 34.0, 40.0)
        colossus(m, cx, 12.0, -1, 34.0, 44.0, human=True)
    # The trilingual XPa panels high on the façades above the colossi.
    for face, wall in (("+y", (0, 96, 96 - wt, 96, 0, top)), ("-y", (0, 96, 0, wt, 0, top))):
        for s0 in (8.0, 70.0):
            inscription(m, face, wall, s0, s0 + 18.0, 56.0, 66.0)
        glazed_panel(m, face, wall, 0, 96, top - 9.0, top - 3.0, "rosettes")
    for face, wall in (("+x", (96 - wt, 96, 0, 96, 0, top)), ("-x", (0, wt, 0, 96, 0, top))):
        glazed_panel(m, face, wall, 0, 96, top - 9.0, top - 3.0, "rosettes")
    # Four columns with double-bull capitals carry the roof.
    col = Column(S.h(0.85), GATE_COL, base="bell", capital="bull", beam="y")
    for x in (tc(1), tc(4)):
        for y in (tc(1), tc(4)):
            column(m, x, y, 0.0, col)
    flat_roof(m, 0, 96, 0, 96, GATE_COL, beam_dir="y", depth=6.0, beam_r=1.2, spacing=9.0, overhang=0.0,
              edge_mat="white_paint")
    merlons(m, 0, 96, 0, 96, top, 5.0, "limestone", pitch=6.0)
    # Torches in brackets beside the west and east doors.
    for y, yy in ((97.0, 98.5), (-1.0, -2.5)):
        for x in (20.0, 76.0):
            rod(m, (x, y, 30.0), (x, yy, 36.0), 0.5, "bronze")
            fill(m, (x - 0.8, x + 0.8, yy - 0.8, yy + 0.8, 36.0, 38.5), "fire")
            halo(m, x, yy, 38.0, 12.0, LAMP, 0.8)


def _gate_landmark():
    walk = tiles(2, 3, 0, 5) + [(1, 2), (1, 3), (4, 2), (4, 3), (5, 2), (5, 3)]
    return Landmark((6, 6), (0, 96), ref("gate_all_lands"), walk=walk,
                    slots={"guard": [{"t": [2, 6], "face": "+y"}, {"t": [3, 6], "face": "+y"},
                                     {"t": [2, -1], "face": "-y"}, {"t": [3, -1], "face": "-y"}]},
                    emitters={"torch_w": (20.0, 98.5, 39.0), "torch_e": (20.0, -2.5, 39.0)}, district=0)


# ---------------------------------------------------------------- palaces

def _hall_walls(m, x0, x1, y0, y1, top, seed, material="mudbrick", t=8.0):
    for w in ((x0, x0 + t, y0, y1), (x1 - t, x1, y0, y1), (x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1)):
        mudbrick_wall(m, *w, 0, top, plinth=3.0, seed=seed, material=material, dado=(5.0, "hematite"))


def _windows(m, face, wall, n, z0, h, w, kind="window", material="limestone", lead=0.12):
    x0, x1, y0, y1, _a, _b = wall
    L = (y1 - y0) if face in ("+x", "-x") else (x1 - x0)
    for i in range(n):
        s0 = L * lead + (L * (1 - 2 * lead) - w) * (i / max(n - 1, 1))
        stone_frame(m, face, wall, s0, w, z0, h, kind=kind if (i % 2 == 0 or kind != "mixed") else "niche",
                    material=material)


TAC_COL = S.v(12.0)


def tacara(m):
    """Darius's small palace: dark polished stone frames ('hall of mirrors'), a hall of 12
    columns behind a portico of 8 on the south, the DPa inscription on the portico."""
    top = TAC_COL + 6.0
    seed = 61
    _hall_walls(m, 0, 110.5, 0, 128, top, seed)
    south = (102.5, 110.5, 0, 128, 0, top)
    stone_frame(m, "+x", south, 48.0, 32.0, 0.0, 34.0, kind="door", leaf="gold", material="polished")
    for s0 in (14.0, 92.0):
        stone_frame(m, "+x", south, s0, 12.0, 6.0, 20.0, kind="window", material="polished")
    west = (0, 112, 120, 128, 0, top)
    _windows(m, "+y", west, 4, 10.0, 18.0, 11.0, material="polished")
    north = (0, 8, 0, 128, 0, top)
    _windows(m, "-x", north, 3, 10.0, 18.0, 11.0, material="polished")
    east = (0, 112, 0, 8, 0, top)
    _windows(m, "-y", east, 4, 10.0, 18.0, 11.0, material="polished")
    flat_roof(m, 0, 110.5, 0, 128, TAC_COL, beam_dir="y", depth=6.0, spacing=8.0, overhang=0.0, edge_mat="white_paint")
    merlons(m, 0, 110.5, 0, 128, top, 5.0, "limestone", pitch=6.0, sides=("-x", "-y", "+y"))
    # The portico: antae at the sides, two rows of four columns.
    for y0, y1 in ((0, 14), (114, 128)):
        mudbrick_wall(m, 112, 158, y0, y1, 0, top, plinth=3.0, seed=seed, dado=(5.0, "hematite"))
        stone_frame(m, "+x", (112, 158, y0, y1, 0, top), 2.0, 10.0, 6.0, 20.0, kind="niche", material="polished")
        inscription(m, "+x", (112, 158, y0, y1, 0, top), 2.0, 12.0, 30.0, 40.0, material="polished")
    col = Column(S.h(0.65), TAC_COL, base="bell", capital="bull", beam="x", material="limestone")
    for x in (tc(7), tc(9)):
        for d in (1, 3, 4, 6):
            column(m, x, tc(d), 0.0, col)
    flat_roof(m, 112, 158, 0, 128, TAC_COL, beam_dir="x", depth=6.0, spacing=8.0, overhang=0.0, edge_mat="white_paint")
    rosette_band(m, "+x", (112, 158, 0, 128, 0, 0), 0, 128, TAC_COL + 2.6, TAC_COL + 5.2, depth=0.5,
                 material="lapis", petals="gold", step=4.0)
    merlons(m, 112, 158, 0, 128, top, 5.0, "limestone", pitch=6.0, sides=("+x", "+y", "-y"))
    for face, wall in (("+y", (0, 158, 0, 128, 0, top)),):
        glazed_panel(m, face, wall, 2, 156, top - 9.0, top - 3.0, "rosettes")
    halo(m, 112.0, 64.0, 18.0, 14.0, LAMP, 0.6)


def _tacara_landmark():
    walk = [(8, d) for d in range(1, 7)] + [(7, 2), (7, 5), (9, 2), (9, 5)]
    return Landmark((10, 8), (0, 72), ref("tacara"), walk=walk,
                    slots={"guard": [{"t": [9, 2], "face": "+x"}, {"t": [9, 5], "face": "+x"}]}, district=2)


HAD_COL = S.v(15.0)


def hadish(m):
    """Xerxes's palace on the highest platform: a hall of 36 columns behind a portico of 12 on
    the north, rooms down the west and south sides with stone door and window frames."""
    top = HAD_COL + 6.0
    seed = 71
    _hall_walls(m, 65.5, 224, 0, 160, top, seed)
    # Rooms along the west and south sides (lower, flat roofed).
    mudbrick_wall(m, 65.5, 224, 128, 160, 0, top - 14.0, plinth=3.0, seed=seed, dado=(5.0, "hematite"))
    west = (65.5, 224, 128, 160, 0, top - 14.0)
    _windows(m, "+y", west, 6, 0.0, 26.0, 11.0, kind="mixed")
    slab(m, 65.5, 224, 128, 160, top - 14.0, top - 12.0, "mudbrick", tone=plaster_tone(seed))
    merlons(m, 65.5, 224, 128, 160, top - 12.0, 4.0, "limestone", pitch=5.0, sides=("+y",))
    south = (192, 224, 0, 128, 0, top)
    _windows(m, "+x", south, 5, 8.0, 20.0, 11.0, kind="mixed")
    glazed_panel(m, "+x", (64, 224, 0, 160, 0, top), 2, 158, top - 9.0, top - 3.0, "rosettes")
    glazed_panel(m, "+y", (64, 224, 0, 128, 0, top), 2, 158, top - 9.0, top - 3.0, "rosettes")
    flat_roof(m, 64, 224, 0, 128, HAD_COL, beam_dir="y", depth=6.0, spacing=8.0, overhang=0.0, edge_mat="white_paint")
    merlons(m, 64, 224, 0, 128, top, 5.0, "limestone", pitch=6.0)
    # The north portico.
    col = Column(S.h(0.7), HAD_COL, base="bell", capital="bull", beam="y")
    for x in (tc(1), tc(3)):
        for d in (1, 2, 4, 5, 7, 8):
            column(m, x, tc(d), 0.0, col)
    flat_roof(m, 18, 64, 0, 160, HAD_COL, beam_dir="y", depth=6.0, spacing=8.0, overhang=0.0, edge_mat="white_paint")
    merlons(m, 18, 64, 0, 160, top, 5.0, "limestone", pitch=6.0, sides=("-x", "+y", "-y"))
    north = (65.5, 73.5, 0, 160, 0, top)
    stone_frame(m, "-x", north, 64.0, 32.0, 0.0, 38.0, kind="door", leaf="gold")
    inscription(m, "+y", (64, 224, 0, 160, 0, top), 20.0, 40.0, top - 20.0, top - 12.0)
    for d, z in ((2, 22.0), (7, 22.0)):
        halo(m, 224.0, tc(d) + 8, z, 12.0, LAMP, 0.6)


def _hadish_landmark():
    cols = {(x, d) for x in (1, 3) for d in (1, 2, 4, 5, 7, 8)}
    walk = [t for t in tiles(0, 3, 0, 9) if t not in cols]
    return Landmark((14, 10), (0, 84), ref("hadish"), walk=walk,
                    slots={"stroll": [{"t": [2, 3]}, {"t": [0, 6]}, {"t": [2, 9]}]}, district=2)


TRI_COL = S.v(11.0)


def tripylon(m):
    """The small central hall with three doors and four columns; its stone door jambs show
    the king walking with attendants (here as painted reliefs on the frames)."""
    top = TRI_COL + 6.0
    seed = 81
    _hall_walls(m, 0, 128, 0, 112, top, seed, t=12.0)
    for face, wall, s0 in (("-x", (0, 12, 0, 112, 0, top), 40.0), ("+x", (116, 128, 0, 112, 0, top), 40.0),
                           ("-y", (0, 128, 0, 12, 0, top), 48.0)):
        stone_frame(m, face, wall, s0, 32.0, 0.0, 34.0, kind="door", leaf="gold")
        carve(m, face_box(face, *wall[:4], 0, 34.0, s0, s0 + 32.0, -1.0, 13.0))
        procession(m, face, wall, s0 - 10.0, s0 - 1.5, 4.0, 22.0, seed=seed, facing=1, period=8.0)
        procession(m, face, wall, s0 + 33.5, s0 + 42.0, 4.0, 22.0, seed=seed + 1, facing=-1, period=8.0)
    _windows(m, "+y", (0, 128, 100, 112, 0, top), 3, 14.0, 16.0, 10.0, kind="niche")
    col = Column(S.h(0.6), TRI_COL, base="bell", capital="bull", beam="y")
    for x in (tc(2), tc(5)):
        for y in (tc(2), tc(4)):
            column(m, x, y, 0.0, col)
    flat_roof(m, 0, 128, 0, 112, TRI_COL, beam_dir="y", depth=6.0, spacing=8.0, overhang=0.0, edge_mat="white_paint")
    glazed_panel(m, "+x", (0, 128, 0, 112, 0, top), 2, 110, top - 9.0, top - 3.0, "rosettes")
    glazed_panel(m, "+y", (0, 128, 0, 112, 0, top), 2, 126, top - 9.0, top - 3.0, "rosettes")
    merlons(m, 0, 128, 0, 112, top, 5.0, "limestone", pitch=6.0)


def _tripylon_landmark():
    cols = {(2, 2), (2, 4), (5, 2), (5, 4)}
    walk = [t for t in tiles(1, 6, 1, 5) if t not in cols] + [(0, 3), (7, 3), (3, 0), (4, 0)]
    return Landmark((8, 7), (0, 76), ref("tripylon"), walk=walk,
                    slots={"guard": [{"t": [-1, 2], "face": "-x"}, {"t": [-1, 4], "face": "-x"}]}, district=2)


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
        slab(m, *w, 0, 3.0, "ashlar", tone=ashlar_tone(3.0, 6.0, seed))
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
    for x in (tc(1), tc(3)):
        for d in range(1, 16, 2):
            h = float(np.sin(x * 3.1 + d * 7.7) * 9131.7 % 1.0)
            if h < 0.5:
                column(m, x, tc(d), 0.0, col_full)
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
           material="mudbrick", halls=True):
    """A flat-roofed mudbrick range. `doors`/`windows`: (face, s0, width) on its own box.
    `wood_court`: (x0, x1, y0, y1) open court ringed with painted wooden columns."""
    mudbrick_wall(m, x0, x1, y0, y1, 0, h, plinth=2.5, seed=seed, material=material)
    box = (x0, x1, y0, y1, 0, h)
    for face, s0, w in doors:
        stone_frame(m, face, box, s0, w, 0.0, min(22.0, h - 8), kind="door", leaf="cedar")
    for face, s0, w in windows:
        stone_frame(m, face, box, s0, w, h - 12.0, 5.0, kind="window")
    slab(m, x0, x1, y0, y1, h, h + 1.6, "mudbrick", tone=plaster_tone(seed + 3, 0.3))
    if halls:
        _roofscape(m, x0, x1, y0, y1, h + 1.6, seed)
    if merlon_sides:
        merlons(m, x0, x1, y0, y1, h + 1.6, 3.5, "mudbrick", pitch=4.5, sides=merlon_sides)
    if wood_court:
        cx0, cx1, cy0, cy1 = wood_court
        carve(m, (cx0, cx1, cy0, cy1, -1.0, h + 14))
        wood = Column(1.6, h - 4.0, base="square", capital="wood", flutes=0, material="cinnabar")
        for x in np.arange(cx0 + 8, cx1 - 4, 16):
            for y in (cy0 + 8, cy1 - 8):
                column(m, x, y, 0.0, wood)
        for y in np.arange(cy0 + 24, cy1 - 20, 16):
            for x in (cx0 + 8, cx1 - 8):
                column(m, x, y, 0.0, wood)
        # Porch roofs round the court on the painted columns.
        for b in ((cx0, cx1, cy0, cy0 + 14), (cx0, cx1, cy1 - 14, cy1), (cx0, cx0 + 14, cy0, cy1), (cx1 - 14, cx1, cy0, cy1)):
            slab(m, *b, h - 4.0, h - 1.0, "cedar", tone=0.1)
            slab(m, *b, h - 1.0, h + 1.6, "mudbrick", tone=plaster_tone(seed, 0.3))


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
            slab(m, a0, a1, b0, b1, z, z + up, "mudbrick", tone=plaster_tone(seed + i * 7 + j, 0.25))
            stone_frame(m, "+x", (a0, a1, b0, b1, z, z + up), (b1 - b0) * 0.4, 4.0, z + 0.6, up - 1.6,
                        kind="window", frame_w=0.6, cornice_h=0.6)
            slab(m, a0 - 0.3, a1 + 0.3, b0 - 0.3, b1 + 0.3, z + up, z + up + 0.8, "mudbrick", tone=0.3)


def treasury(m):
    """Low, flat-roofed mudbrick with plastered walls, small high windows and columned halls
    of plastered and painted wooden columns round open courts; guarded doors."""
    h = 34.0
    seed = 101
    _range(m, 0, 480, 0, 272, h, seed,
           doors=[("+y", 210.0, 16.0), ("+x", 40.0, 14.0)],
           windows=[("+y", s, 5.0) for s in range(30, 460, 36)] + [("+x", s, 5.0) for s in range(20, 260, 36)],
           wood_court=(48, 176, 120, 248))
    for court in ((240, 352, 40, 152), (380, 460, 150, 250)):
        cx0, cx1, cy0, cy1 = court
        carve(m, (cx0, cx1, cy0, cy1, -1.0, h + 14))
        wood = Column(1.6, h - 4.0, base="square", capital="wood", flutes=0, material="cinnabar")
        for x in np.arange(cx0 + 8, cx1 - 4, 16):
            for y in (cy0 + 8, cy1 - 8):
                column(m, x, y, 0.0, wood)
        for b in ((cx0, cx1, cy0, cy0 + 14), (cx0, cx1, cy1 - 14, cy1)):
            slab(m, *b, h - 4.0, h - 1.0, "cedar", tone=0.1)
            slab(m, *b, h - 1.0, h + 1.6, "mudbrick", tone=plaster_tone(seed, 0.3))
    # Guards' torches either side of the west door.
    for x in (206.0, 230.0):
        halo(m, x, 273.0, 20.0, 9.0, LAMP, 0.5)


def harem(m):
    """Rows of apartments round courts: small four-column halls opening on the courts, stone
    door frames with royal reliefs, lamps at the doors."""
    h = 30.0
    seed = 111
    _range(m, 0, 288, 16, 224, h, seed, doors=[("+y", s, 12.0) for s in (20.0, 110.0, 200.0)],
           windows=[("+y", s, 5.0) for s in (60.0, 150.0, 240.0)])
    _range(m, 288, 432, 0, 224, h, seed + 1, doors=[("+x", s, 12.0) for s in (30.0, 100.0, 170.0)] +
           [("+y", 60.0, 12.0)], windows=[("+x", s, 5.0) for s in (64.0, 134.0, 204.0)])
    for cx0, cx1, cy0, cy1 in ((24, 120, 60, 200), (150, 270, 60, 200), (310, 410, 40, 190)):
        carve(m, (cx0, cx1, cy0, cy1, -1.0, h + 14))
        col = Column(1.8, h - 4.0, base="bell", capital="protome", beam="y", flutes=12)
        for x in (cx0 + 10, cx0 + 26):
            for y in (cy0 + 40, cy1 - 40):
                column(m, x, y, 0.0, col)
        slab(m, cx0, cx0 + 34, cy0, cy1, h - 4.0, h + 1.6, "mudbrick", tone=plaster_tone(seed, 0.3))
        stone_frame(m, "+x", (cx0, cx0 + 34, cy0, cy1, 0, h - 4.0), (cy1 - cy0) / 2 - 6, 12.0, 0.0, 20.0,
                    kind="door", leaf="gold", material="polished")
        halo(m, cx0 + 35, (cy0 + cy1) / 2, 18.0, 8.0, LAMP, 0.6)
    for y in (26.0, 116.0, 206.0):
        halo(m, 22.0 + y * 0.3, 225.0, 18.0, 8.0, LAMP, 0.6)


def garrison(m):
    """Barracks of the guard round a drill court, an armoury hall, a mudbrick gate tower."""
    h = 28.0
    seed = 121
    _range(m, 0, 208, 0, 384, h, seed, doors=[("+x", s, 10.0) for s in range(30, 380, 60)],
           windows=[("+x", s, 4.0) for s in range(54, 380, 60)], merlon_sides=("+x", "+y", "-x", "-y"))
    carve(m, (40, 168, 80, 300, -1.0, h + 8))          # the drill court
    # The gate tower on the west side, taller, with torches.
    mudbrick_wall(m, 70, 138, 352, 400, 0, 32.0, plinth=3.0, seed=seed, dado=(5.0, "hematite"))
    tower = (70, 138, 352, 400, 0, 32.0)
    stone_frame(m, "+y", tower, 24.0, 20.0, 0.0, 22.0, kind="door", leaf="bronze")
    carve(m, (94, 114, 340, 401, 0.6, 22.0))
    _windows(m, "+x", tower, 2, 22.0, 6.0, 7.0)
    slab(m, 70, 138, 352, 400, 32.0, 33.6, "mudbrick")
    merlons(m, 70, 138, 352, 400, 33.6, 4.0, "mudbrick", pitch=5.0)
    # Braziers in the drill court.
    for (x, y) in ((104.0, 130.0), (104.0, 250.0)):
        revolve(m, x, y, 0, 6.0, lambda t: 1.0 + 1.6 * t ** 2, "bronze", tone=0.2)
        fill(m, (x - 2.4, x + 2.4, y - 2.4, y + 2.4, 5.0, 7.5), "fire",
             lambda X, Y, Z: np.hypot(X - x, Y - y) < 2.4 - (Z - 5.0) * 0.6)
        halo(m, x, y, 7.0, 14.0, LAMP, 0.9)
    for x in (66.0, 142.0):
        halo(m, x, 401.0, 24.0, 10.0, LAMP, 0.6)


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
    """The mountain's limestone, cut back in steps where the blocks come out: rough natural rock
    behind, smooth vertical cut faces in front with rows of wedge slots, half-detached blocks on
    the benches, rubble ramps down to the terrace road (westward, +y)."""
    from voxel import value_noise

    def slope(X, Y):            # natural ground rising eastward (towards -y), rugged
        n = value_noise(X, Y, X * 0, 22.0, 141) - 0.5
        return np.clip((240 - Y) / 240, 0, 1) ** 0.8 * 40.0 + n * 10.0

    def cut(X, Y):              # three benches cut into the front of the slope
        u = (Y - 60) / 150
        return np.where(u < 0.33, 34.0, np.where(u < 0.66, 22.0, 9.0))

    inside = lambda X, Y: (X > 40) & (X < 264) & (Y > 60) & (Y < 210)
    top = lambda X, Y: np.where(inside(X, Y), np.minimum(slope(X, Y), cut(X, Y)), slope(X, Y))
    field_fill(m, (0, 304, 0, 240, 0, 64), lambda X, Y, Z: Z - top(X, Y), "limestone",
         tone=lambda X, Y, Z: np.where(inside(X, Y) & (Z > top(X, Y) - 1.0), 0.35, 0.0) +
         (value_noise(X, Y, Z, 4.0, 143) - 0.5) * np.where(inside(X, Y), 0.4, 1.4))
    # Wedge slots along the front edges of the benches.
    for yb, z in ((60 + 150 * 0.33, 34.0), (60 + 150 * 0.66, 22.0)):
        carve(m, (44, 260, yb - 0.4, yb + 1.0, z - 2.5, z - 1.0),
              lambda X, Y, Z: (X % 4.0) < 1.2)
    for (x, y, z, w) in ((70, 70, 34, 14), (170, 76, 34, 10), (220, 120, 22, 12), (110, 128, 22, 9),
                         (60, 175, 9, 12), (200, 180, 9, 10)):
        slab(m, x, x + w, y, y + w * 0.7, z, z + 9.0, "limestone", tone=0.3)
        carve(m, (x - 0.6, x + w + 0.6, y + w * 0.7, y + w * 0.7 + 0.8, z + 0.5, z + 9.0))
    for x0, x1 in ((20, 60), (240, 284)):
        fill(m, (x0, x1, 120, 240, 0, 40), "stone",
             lambda X, Y, Z: Z < np.clip((240 - Y) / 120 * 26, 0, None) + (hash_t(X * 2, Y * 2) - 0.5) * 3,
             tone=lambda X, Y, Z: (hash_t(X * 3, Y * 3 + Z) - 0.5) * 1.6)


# ---------------------------------------------------------------- the plain

def paradise_gate(m):
    """A mudbrick gate faced with glazed bricks: a blue ground with yellow-white bulls and
    dragons in relief, after Tol-e Ajori (an Ishtar-Gate type). The passage is shown with a
    flat timber lintel; the original superstructure is unknown."""
    top = 46.0
    for x0, x1 in ((0, 30.5), (49.5, 80)):
        mudbrick_wall(m, x0, x1, 6, 74, 0, top, plinth=2.5, seed=151, material="glaze_blue")
        for face in ("+y", "-y", "+x", "-x"):
            if (face == "+x" and x0 == 0) or (face == "-x" and x0 > 40):
                continue
            box = (x0, x1, 6, 74, 0, top)
            L = (74 - 6) if face in ("+x", "-x") else (x1 - x0)
            for z in (6.0, 18.0, 30.0):
                glazed_panel(m, face, box, 1.0, L - 1.0, z, z + 10.0, "beasts")
        slab(m, x0 + 1, x1 - 1, 7, 73, top - 0.6, top, "mudbrick", tone=plaster_tone(153, 0.3))
        merlons(m, x0, x1, 6, 74, top, 6.0, "glaze_blue", pitch=7.0)
    slab(m, 32, 48, 6, 74, 30.0, 42.0, "glaze_blue", tone=0.0)
    slab(m, 33, 47, 7, 73, 41.4, 42.0, "mudbrick", tone=plaster_tone(155, 0.3))
    rod(m, (31, 74.5, 30.0), (49, 74.5, 30.0), 1.2, "cedar")
    rod(m, (31, 5.5, 30.0), (49, 5.5, 30.0), 1.2, "cedar")
    glazed_panel(m, "+y", (32, 48, 6, 74, 0, 42.0), 0, 16.0, 31.0, 41.0, "rosettes")
    merlons(m, 32, 48, 6, 74, 42.0, 5.0, "glaze_blue", pitch=6.0)


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
    merlons(m, 14, 82, 14, 82, h + 5.0, 3.5, "white_paint", pitch=4.5)
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
        mudbrick_wall(m, *w, 0, 18.0, plinth=2.0, seed=seed)
        merlons(m, *w, 18.0, 3.0, "mudbrick", pitch=4.0, sides=("+x", "+y", "-x", "-y"))
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
           windows=[("+x", 20.0, 4.0)], merlon_sides=("+x", "+y"))
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
    # Upper arm: throne platform on two rows of bearers, the king on his dais, the altar, the
    # winged figure in a disc above.
    procession(m, "+x", (0, face_x, 0, 336, 0, 0), cy - 15, cy + 15, 80.0, 86.0, depth=0.8, ground="naqsh",
               seed=183, period=2.4, colours=("naqsh",), kinds=("mede",))
    procession(m, "+x", (0, face_x, 0, 336, 0, 0), cy - 15, cy + 15, 87.0, 93.0, depth=0.8, ground="naqsh",
               seed=185, period=2.4, colours=("naqsh",), kinds=("persian",))
    for i, z in enumerate((94.0, 95.2, 96.4)):
        fill(m, (face_x - 0.9 + 0.3 * i, face_x, cy - 13 + i * 1.5, cy - 3 - i * 1.5, z, z + 1.2), "naqsh", tone=0.4)
    fill(m, (face_x - 1.2, face_x, cy - 10, cy - 6, 97.6, 106.0), "naqsh", tone=0.5)          # the king
    fill(m, (face_x - 1.2, face_x, cy - 9.2, cy - 6.8, 106.0, 107.6), "naqsh", tone=0.6)
    rod(m, (face_x - 0.8, cy - 5.5, 99.0), (face_x - 0.8, cy - 3.5, 101.0), 0.4, "naqsh")       # the bow
    fill(m, (face_x - 1.2, face_x, cy + 5, cy + 9, 94.0, 100.0), "naqsh", tone=0.4)           # fire altar
    fill(m, (face_x - 1.2, face_x, cy + 4, cy + 10, 99.5, 100.6), "naqsh", tone=0.5)
    fill(m, (face_x - 1.4, face_x, cy - 1.6, cy + 1.6, 102.0, 105.0), "naqsh", tone=0.6,
         mask=lambda X, Y, Z: np.hypot(Y - cy, Z - 103.5) < 1.6)
    fill(m, (face_x - 1.0, face_x, cy - 8, cy + 8, 103.0, 104.4), "naqsh", tone=0.5)          # wings
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
    slab(m, c - half, c + half, c - half, c + half, 4.8, top, "cream", tone=ashlar_tone(2.2, 5.5, 191))
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
             tone=ashlar_tone(h, 7.0, 201 + i))
        z += h
    ca, cb = S1.h(6.4) / 2, S1.h(5.35) / 2
    wall_h = S1.v(2.4)
    slab(m, cx - ca, cx + ca, cy - cb, cy + cb, z, z + wall_h, "cream", tone=ashlar_tone(S1.v(0.8), 6.0, 211))
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
    "parsa.apadana_stair_n": _stair_landmark("apadana_stair_n", 3, 14, 8.0, "x", "lo", [(1, 2), (11, 12)], 1),
    "parsa.apadana_stair_e": _stair_landmark("apadana_stair_e", 12, 3, 8.0, "y", "lo", [(1, 2), (9, 10)], 1),
    "parsa.tacara": _tacara_landmark(),
    "parsa.tacara_stair_s": _stair_landmark("tacara_stair_s", 3, 8, 16.0, "x", "hi", [(1, 1), (6, 6)], 2),
    "parsa.hadish": _hadish_landmark(),
    "parsa.hadish_stair_w": _stair_landmark("hadish_stair_w", 6, 4, 24.0, "y", "hi", [(1, 1), (4, 4)], 2),
    "parsa.tripylon": _tripylon_landmark(),
    "parsa.tripylon_stair": _stair_landmark("tripylon_stair", 2, 5, 8.0, "x", "lo", [(0, 0), (4, 4)], 2),
    "parsa.hall_100": _h100_landmark(),
    "parsa.treasury": Landmark((30, 17), (0, 60), ref("treasury"),
                               slots={"gift_drop": [{"t": [13, 17], "face": "-y"}, {"t": [14, 17], "face": "-y"}],
                                      "guard": [{"t": [12, 17], "face": "+y"}, {"t": [15, 17], "face": "+y"}],
                                      "treasurer": [{"t": [13, 16], "face": "+y"}]}, district=3),
    "parsa.harem": Landmark((27, 14), (0, 48), ref("harem"), district=3),
    "parsa.garrison": Landmark((13, 24), (0, 66), ref("garrison"),
                               slots={"drill": [{"t": [5, 8 + i]} for i in range(6)]},
                               emitters={"brazier": (104.0, 130.0, 7.5)}, district=3),
    "parsa.south_stores": Landmark((6, 20), (0, 32), ref("south_stores"), district=3),
    "parsa.cistern": Landmark((5, 5), (0, 16), ref("cistern"), district=3),
    "parsa.quarry": Landmark((19, 15), (0, 60), ref("quarry"),
                             slots={"cut": [{"t": [5, 6], "face": "-y"}, {"t": [9, 5], "face": "-y"},
                                            {"t": [14, 8], "face": "-y"}, {"t": [6, 10], "face": "-y"}]},
                             emitters={"dust": (80.0, 90.0, 34.0)}, district=3),
    "parsa.paradise_gate": Landmark((5, 5), (0, 60), ref("paradise_gate"), walk=[(2, y) for y in range(5)], district=4),
    "parsa.pavilion": _pavilion_landmark(),
    "parsa.road_station": _road_station_landmark(),
    "parsa.naqsh_cliff": Landmark((9, 21), (0, 132), ref("naqsh_cliff"), district=6),
    "parsa.kaba": Landmark((3, 3), (0, 60), ref("kaba"), district=6),
    "parsa.cyrus_tomb": Landmark((5, 5), (0, 56), ref("cyrus_tomb"), district=6),
}
