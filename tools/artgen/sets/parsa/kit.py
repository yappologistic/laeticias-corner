"""Pārsa's kit (persepolis.md §3.3): houses, workshops, stores, water works, altars, building
site gear, camp and garden pieces, walls. Toy scale like the home kit (a door about 46 px, an
adult 40 px), modelled in design units with the footprint's origin tile at (0, 0); rotatable
pieces face +y (their front is the lower-left face the camera sees at r0).
"""

import math

import numpy as np

import materials as M
from arch import (ashlar_tone, awning, carve, ellipsoid, face_box, fill, flight, halo, mark, merlons, mudbrick_wall,
                  plaster_tone, revolve, rod, slab, stair, stone_frame, tent)
from setbuild import Item
from voxel import Model, hash01

T = 16
LAMP = (255, 201, 92)
FIRE = (255, 154, 58)


def _m(fw, fh, top, k, below=0):
    return Model.empty(-2, fw * T + 2, -2, fh * T + 2, -below, top, k=k)


# ---------------------------------------------------------------- dwellings and stores

def _plaster(m, x0, x1, y0, y1, h, seed, plinth=1.2, material="mudbrick", amount=0.6):
    """A house wall: mud plaster with patches, straw and a damp foot on a rubble footing."""
    if plinth:
        slab(m, x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2, 0, plinth, "stone", tone=M.ashlar(plinth, 3.0, seed, spread=1.0))
    slab(m, x0, x1, y0, y1, plinth, h, material, tone=M.mud_plaster(seed, amount, plinth, 3.0))


def _house_roof(m, x0, x1, y0, y1, h, seed, clutter=2, parapet=1.4):
    M.beam_ends(m, "+y", (x0, x1, y0, y1), h - 1.0, spacing=3.2, r=0.6, out=0.8, s0=1.6)
    M.beam_ends(m, "+x", (x0, x1, y0, y1), h - 1.0, spacing=3.2, r=0.6, out=0.8, s0=1.6)
    M.roof(m, x0, x1, y0, y1, h + 0.6, seed=seed, kind="domestic", hatches=1, rollers=1, clutter=clutter,
           base=-0.5)
    slab(m, x0, x1, y0, y1, h + 0.6, h + 0.6 + parapet, "mudbrick", tone=M.mud_plaster(seed + 9, 0.4, h, 0.0))
    carve(m, (x0 + 1.0, x1 - 1.0, y0 + 1.0, y1 - 1.0, h + 0.61, h + 0.6 + parapet + 0.1))


def _door(m, face, box, s0, w, h, seed, frame="mudbrick"):
    """A plank door in a plain frame, a little worn at the foot, soot of the lamp above."""
    stone_frame(m, face, box, s0, w, 0.0, h, kind="door", leaf="cedar", frame_w=0.9, cornice_h=1.0, material=frame)
    x0, x1, y0, y1 = box[:4]
    M.stain(m, face_box(face, x0, x1, y0, y1, h + 1.5, h + 5.0, s0, s0 + w, -0.2, 0.5), lambda X, Y, Z: True, -0.4)


def _awning(m, x0, x1, y0, y1, z, cloth):
    """A cloth or reed awning on two poles, tied back to the wall."""
    for px, py in ((x1, y0), (x1, y1)):
        rod(m, (px, py, 0), (px, py, z), 0.35, "wood")
    fill(m, (x0, x1 + 0.6, y0 - 0.4, y1 + 0.4, z - 1.6, z + 0.6), cloth,
         lambda X, Y, Z: np.abs(Z - (z - 1.2 * (X - x0) / max(x1 - x0, 1))) < 0.45,
         tone=lambda X, Y, Z: 0.35 * ((Y * 0.8) % 2.0 < 0.9) - 0.1)


def p_house(v, frame, frames, k):
    """A mudbrick courtyard house. Every side is different, so its four rotations read as four
    households: a plank door with a lamp and a cloth awning on one side, the court gate and a
    bread oven on another, a stair up to the roof on a third, a dovecote corner and jars on the
    fourth; a pomegranate in the court, life on the roof (mats of produce, fodder, jars)."""
    m = _m(3, 3, 38, k)
    seed = 300
    rh, ch = 26.0, 16.0
    _plaster(m, 0, 20, 0, 48, rh, seed)                               # rooms along the north side
    _plaster(m, 20, 48, 0, 18, rh - 3.0, seed + 1, material="mudbrick", amount=0.8)   # a lower wing
    for w in ((20, 48, 45, 48), (45, 48, 18, 48)):
        _plaster(m, *w, ch, seed + 2, plinth=0.8)
        slab(m, *w, ch, ch + 0.8, "mudbrick", tone=0.2)
    house = (0, 20, 0, 48, 0, rh)
    wing = (20, 48, 0, 18, 0, rh - 3.0)
    # West: the house door, its lamp, a striped awning over a bench.
    _door(m, "+y", house, 6.0, 7.0, 15.0, seed)
    _awning(m, 0, 7, 32, 46, 14.0, "linen")
    slab(m, 1, 6, 40, 45, 0, 3.2, "wood", tone=M.timber("y", seed))
    fill(m, (8.4, 11.6, 48.2, 49.4, 12.0, 14.0), "lamp")
    halo(m, 10.0, 49.0, 13.0, 8.0, LAMP, 0.7, kind="door")
    # Small high windows; a niche with a lamp shelf.
    for face, b, s0 in (("+x", wing, 6.0), ("+x", house, 30.0), ("-x", house, 12.0), ("-y", house, 8.0), ("-y", wing, 10.0)):
        fill(m, face_box(face, *b[:4], 17.0, 19.5, s0, s0 + 3.0, -0.2, 1.2), "ink", tone=0.4)
        mark(m, face_box(face, *b[:4], 17.0, 19.5, s0, s0 + 3.0, -0.2, 0.0), "window")
    # South: the court gate, a bread oven beside it.
    carve(m, (45, 49, 26, 34, 0.5, 12.0))
    fill(m, (45.5, 46.5, 26, 34, 0.5, 12.0), "cedar", tone=lambda X, Y, Z: -0.4 * ((Y % 2.0) < 0.4))
    revolve(m, 52.0 - 4.0, 40.0, 0, 6.0, lambda t: 2.8 - 0.9 * t, "mudbrick", tone=M.mud_plaster(seed + 4, 0.5))
    # East: a mud stair climbing the wing wall to the roof.
    stair(m, 22, 46, -3.0, 0.0, 0, rh - 3.0, "+x", step=1.6, material="mudbrick")
    # North: a dovecote turret on the corner of the roof, jars at the foot of the wall.
    revolve(m, 4.0, 4.0, rh, rh + 8.0, lambda t: 3.2 - 0.8 * t, "mudbrick", tone=M.mud_plaster(seed + 5, 0.4))
    for i in range(4):
        fill(m, (1.5, 6.5, 1.5, 6.5, rh + 2.0 + i * 1.6, rh + 2.6 + i * 1.6), "ink",
             lambda X, Y, Z: np.hypot(X - 4.0, Y - 4.0) > 2.6, tone=0.3, only_solid=True)
    for i, y in enumerate((20.0, 24.0, 28.0)):
        revolve(m, -1.0, y, 0, 4.5, lambda t: 1.4 + 0.6 * np.sin(np.pi * t * 0.9), "roof", tone=0.1 * i)
    # The court: a pomegranate in flower, a water jar, a loom post.
    rod(m, (34, 32, 0), (34, 32, 9), 0.8, "bark")
    for cx, cy, cz in ((34, 32, 12), (31, 30, 11), (36, 35, 11)):
        ellipsoid(m, (cx, cy, cz), (3.4, 3.4, 2.8), "leaf_dark", tone=0.2)
    for px, py in ((32, 29), (36, 34), (33, 35)):
        fill(m, (px - 0.6, px + 0.6, py - 0.6, py + 0.6, 12.5, 13.6), "poppy")
    revolve(m, 26.0, 40.0, 0, 4.0, lambda t: 1.6 + 0.5 * np.sin(np.pi * t), "roof", tone=0.2)
    _house_roof(m, 0, 20, 0, 48, rh, seed, clutter=3)
    _house_roof(m, 20, 48, 0, 18, rh - 3.0, seed + 7, clutter=2)
    for px, py in ((14, 40), (40, 6)):
        rod(m, (px, py, rh + 1), (px + 0.4, py, rh + 7), 0.35, "wood")
    return m


def p_house_small(v, frame, frames, k):
    """A workers' house: one plastered cell, each side its own: the door under a reed awning,
    a stair to the roof, a bread oven, fuel stacked against the wall."""
    m = _m(2, 2, 30, k)
    seed = 310
    _plaster(m, 2, 30, 2, 30, 22.0, seed, amount=0.8)
    box = (2, 30, 2, 30, 0, 22.0)
    _door(m, "+y", box, 10.0, 7.0, 14.0, seed)
    _awning(m, 2, 9, 18, 30, 12.0, "straw")
    fill(m, face_box("+x", 2, 30, 2, 30, 16.0, 18.5, 12.0, 15.0, -0.2, 1.2), "ink", tone=0.4)
    mark(m, face_box("+x", 2, 30, 2, 30, 16.0, 18.5, 12.0, 15.0, -0.2, 0.0), "window")
    stair(m, 6, 28, -1.0, 2.0, 0, 22.0, "-x", step=1.6, material="mudbrick")
    revolve(m, 33.0 - 2.0, 8.0, 0, 5.0, lambda t: 2.4 - 0.8 * t, "mudbrick", tone=M.mud_plaster(seed + 2, 0.5))
    fill(m, (4, 9, -1.5, 2, 0, 6.0), "straw", tone=lambda X, Y, Z: (hash01(np.floor(X * 2).astype(np.int64),
                                                                            np.floor(Z * 2).astype(np.int64), seed) - 0.5))
    _house_roof(m, 2, 30, 2, 30, 22.0, seed, clutter=2, parapet=1.2)
    fill(m, (12.4, 15.6, 30.2, 31.2, 14.0, 15.5), "lamp")
    halo(m, 14.0, 31.0, 15.0, 6.0, LAMP, 0.6, kind="door")
    return m


def p_granary(v, frame, frames, k):
    """A domed mudbrick storehouse with sealed doors (clay sealings on the bolts)."""
    m = _m(2, 2, 32, k)
    revolve(m, 16, 16, 0, 16.0, lambda t: 13.0 - 0.5 * t, "mudbrick", tone=plaster_tone(320, 0.4))
    revolve(m, 16, 16, 16.0, 27.0, lambda t: 12.5 * np.sqrt(np.clip(1 - t * t, 0, 1)) + 0.3, "mudbrick",
            tone=plaster_tone(321, 0.4))
    for face in ("+y", "+x"):
        b = face_box(face, 3, 29, 3, 29, 0.5, 11.0, 10.0, 16.0, -1.5, 0.5)
        fill(m, b, "cedar", tone=lambda X, Y, Z: -0.4 * ((Z % 2.0) < 0.4))
        cx, cy = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2
        ellipsoid(m, (cx + (1.2 if face == "+x" else 0), cy + (1.2 if face == "+y" else 0), 6.0), (0.9, 0.9, 0.9),
                  "soil", tone=0.6)
    fill(m, (14.5, 17.5, 14.5, 17.5, 27.0, 28.0), "mudbrick", tone=0.3)
    return m


def p_workshop(v, frame, frames, k):
    """A craft yard under a shade of poles and reed mats: on one side a potter's bench with
    jars drying, on another a loom under the shade, a forge hearth with bellows and its glow,
    bricks stacked along the back wall."""
    m = _m(3, 2, 28, k)
    _plaster(m, 0, 48, 0, 4, 14.0, 330, amount=0.8)
    slab(m, 0, 48, 0, 4, 14.0, 15.0, "mudbrick", tone=0.2)
    awning(m, 2, 46, 4, 26, 20.0, cloth="straw", sag=0.4)
    # A potter's bench and new jars drying.
    slab(m, 8, 22, 10, 14, 0, 6.0, "wood_light", tone=M.timber("x", 331))
    slab(m, 8, 22, 10, 14, 6.0, 7.0, "cedar", tone=0.3)
    for i, (x, y) in enumerate(((10, 18), (13, 20), (16, 18), (19, 21))):
        revolve(m, x, y, 0, 5.5, lambda t: 1.4 + 0.9 * np.sin(np.pi * t * 0.9), "mudbrick", tone=0.5 + 0.1 * i)
    # A loom: two beams on posts, a patterned cloth on it.
    for x in (28.0, 36.0):
        rod(m, (x, 8, 0), (x, 8, 16), 0.4, "wood")
    rod(m, (28, 8, 15.5), (36, 8, 15.5), 0.45, "wood")
    fill(m, (28.5, 35.5, 7.6, 8.4, 4.0, 15.0), "cinnabar",
         tone=lambda X, Y, Z: 0.6 * (((X + Z) % 2.0) < 0.6) - 0.5 * ((Z % 3.0) < 0.5))
    fill(m, (28.5, 35.5, 7.4, 8.6, 9.0, 10.5), "lapis", tone=0.1, only_solid=True)
    # A smithy hearth with its bellows and glow.
    revolve(m, 40, 20, 0, 3.0, lambda t: 3.2 - 0.4 * t, "stone", tone=-0.2)
    fill(m, (38.5, 41.5, 18.5, 21.5, 2.0, 3.6), "ember")
    fill(m, (43, 47, 18, 22, 0.5, 3.0), "leather", lambda X, Y, Z: np.hypot(X - 45, Y - 20) < 2.0, tone=0.1)
    halo(m, 40, 20, 4.0, 10.0, FIRE, 0.9)
    # Bricks stacked against the back wall.
    for i in range(4):
        for j in range(3 - (i % 2)):
            slab(m, 4 + i * 0.3, 7.6, 4.4 + j * 3.4, 7.4 + j * 3.4, i * 1.2, i * 1.2 + 1.1, "mudbrick",
                 tone=0.2 + 0.2 * float(hash01(i, j, 333)))
    return m


def p_kiln(v, frame, frames, k):
    """A domed clay kiln, soot-blackened at the vents, its fire mouth glowing."""
    m = _m(1, 1, 26, k)
    revolve(m, 8, 8, 0, 18.0, lambda t: 6.5 * np.sqrt(np.clip(1 - t ** 1.6, 0, 1)) + 0.6, "mudbrick",
            tone=lambda X, Y, Z: M.mud_plaster(340, 0.6, 0, 2.0)(X, Y, Z) - 0.9 * (Z > 14) - 0.4 * (Z > 16.5))
    carve(m, (6, 10, 12, 16, 1.0, 6.0))
    fill(m, (6, 10, 11, 12, 1.0, 6.0), "ember")
    M.stain(m, (5, 11, 12, 16, 5.0, 11.0), lambda X, Y, Z: True, -0.8)
    revolve(m, 8, 8, 17.5, 19.5, lambda t: 1.4, "mudbrick", tone=-0.9)
    for i in range(3):
        fill(m, (12.5 + i * 0.4, 14.5, 1 + i * 2.2, 3 + i * 2.2, 0, 1.4 + i * 0.3), "wood", tone=0.1)
    halo(m, 8, 14, 3.0, 9.0, FIRE, 0.9)
    return m


def p_brickfield(v, frame, frames, k):
    """Rows of square mudbricks drying in the sun, two wooden moulds."""
    m = _m(2, 2, 6, k)
    for i in range(6):
        for j in range(6):
            x, y = 3 + i * 4.5, 3 + j * 4.5
            slab(m, x, x + 3.2, y, y + 3.2, 0, 1.4, "mudbrick", tone=0.2 + 0.25 * float(hash01(i, j, 350)))
    for x, y in ((29, 6), (29, 18)):
        slab(m, x - 2, x + 2, y - 4, y + 4, 0, 1.2, "wood_light", tone=0.2)
        carve(m, (x - 1.2, x + 1.2, y - 3.2, y + 3.2, 0.4, 1.3))
    return m


def p_oven(v, frame, frames, k):
    """A tanūr: a cylindrical clay oven sunk in the ground, a glow in its mouth."""
    m = _m(1, 1, 14, k)
    revolve(m, 8, 8, 0, 10.0, lambda t: 4.5 - 1.0 * t, "mudbrick", tone=plaster_tone(360, 0.4))
    carve(m, (5.5, 10.5, 5.5, 10.5, 7.0, 11.0), lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 2.3)
    fill(m, (5.5, 10.5, 5.5, 10.5, 6.4, 7.0), "ember", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 2.3)
    halo(m, 8, 8, 10.0, 6.0, FIRE, 0.7)
    return m


def p_well(v, frame, frames, k):
    """A stone well ring with a sweep: a pole pivoting on a post, a stone counterweight."""
    m = _m(1, 1, 30, k)
    revolve(m, 8, 8, 0, 4.0, lambda t: 4.5, "stone", tone=ashlar_tone(2.0, 3.0, 370))
    carve(m, (4, 12, 4, 12, 0.5, 5.0), lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.0)
    fill(m, (4, 12, 4, 12, 0.5, 1.0), "water", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.0)
    rod(m, (1.5, 14, 0), (1.5, 14, 16.0), 0.7, "wood")
    a = (0.25, -0.15)[frame % 2]
    p = np.array([1.5, 14, 16.0])
    d = np.array([math.cos(a) * 0.7, -math.cos(a) * 0.7, math.sin(a)])
    rod(m, p - d * 9, p + d * 12, 0.45, "wood_light")
    ellipsoid(m, tuple(p - d * 9 + (0, 0, -0.8)), (1.6, 1.6, 1.4), "stone", tone=0.1)
    tip = p + d * 12
    rod(m, tuple(tip), (tip[0], tip[1], 6.0 + 4.0 * a), 0.15, "straw")
    revolve(m, tip[0], tip[1], 4.0 + 4.0 * a, 6.5 + 4.0 * a, lambda t: 1.0 + 0.4 * t, "leather", tone=0.2)
    return m


def _channel(m, mask, frame, kerb="limestone"):
    """A narrow dressed-stone channel with arms to same-item neighbours (N -y, E +x, S +y,
    W -x), its water glinting differently each frame."""
    w, kb = 3.0, 1.6
    c = 8.0
    arms = {1: (c - w - kb, c + w + kb, -1, c + w + kb), 2: (c - w - kb, 17, c - w - kb, c + w + kb),
            4: (c - w - kb, c + w + kb, c - w - kb, 17), 8: (-1, c + w + kb, c - w - kb, c + w + kb)}
    boxes = [(c - w - kb, c + w + kb, c - w - kb, c + w + kb)] + [arms[b] for b in (1, 2, 4, 8) if mask & b]
    for b in boxes:
        slab(m, b[0], b[1], b[2], b[3], 0, 2.6, kerb, tone=ashlar_tone(2.6, 4.0, 380))
    inner = []
    for b in boxes:
        ib = (max(b[0], c - w) if b[0] > -1 else -1, min(b[1], c + w) if b[1] < 17 else 17,
              max(b[2], c - w) if b[2] > -1 else -1, min(b[3], c + w) if b[3] < 17 else 17)
        inner.append(ib)
        carve(m, (*ib, 0.8, 3.0))
        fill(m, (*ib, 0.6, 1.4), "water",
             tone=lambda X, Y, Z: 1.8 * (((X + Y * 0.6 + frame * 2.0) % 5.0) < 0.6) - 1.5 +
             0.5 * (((X - Y + frame * 1.3) % 3.0) < 0.4))
    return m


def p_channel(v, frame, frames, k):
    m = Model.empty(0, 16, 0, 16, 0, 4, k=k)
    m.hover = False
    return _channel(m, v, frame)


def p_basin(v, frame, frames, k):
    """A square stone basin where channels meet, a ripple ring moving outward."""
    m = Model.empty(0, 16, 0, 16, 0, 5, k=k)
    slab(m, 0.5, 15.5, 0.5, 15.5, 0, 3.4, "limestone", tone=ashlar_tone(3.4, 5.0, 390))
    carve(m, (2.5, 13.5, 2.5, 13.5, 0.8, 4.0))
    r = 1.5 + frame * 1.4
    fill(m, (2.5, 13.5, 2.5, 13.5, 0.6, 1.6), "water",
         tone=lambda X, Y, Z: 1.8 * (np.abs(np.hypot(X - 8, Y - 8) - r) < 0.5) - 1.4)
    return m


def p_qanat_shaft(v, frame, frames, k):
    """A ring of spoil round a shaft opening; one look has a wooden windlass."""
    m = _m(1, 1, 16, k)
    fill(m, (0, 16, 0, 16, 0, 5), "soil", lambda X, Y, Z: (np.abs(np.hypot(X - 8, Y - 8) - 5.0) < 2.8) &
         (Z < 4.0 - (np.hypot(X - 8, Y - 8) - 5.0) ** 2 * 0.4), tone=lambda X, Y, Z: (hash01(
             np.floor(X * 2).astype(np.int64), np.floor(Y * 2).astype(np.int64), 400) - 0.5) * 1.2)
    fill(m, (5, 11, 5, 11, 0, 0.4), "ink", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 2.0)
    if v == 1:
        for y in (4.5, 11.5):
            rod(m, (8, y, 0), (8, y, 8.0), 0.45, "wood")
        rod(m, (8, 4, 8.0), (8, 12, 8.0), 0.8, "wood_light")
        rod(m, (8, 8, 8.0), (8, 8, 1.0), 0.15, "straw")
    return m


def p_fire_altar(v, frame, frames, k):
    """A stepped stone altar, three steps at the foot and three at the top as on the royal
    tomb reliefs, a bowl of fire on it."""
    m = _m(1, 1, 24, k)
    z = 0.0
    for i in range(3):
        r = 6.5 - i * 1.0
        slab(m, 8 - r, 8 + r, 8 - r, 8 + r, z, z + 1.6, "limestone", tone=0.15)
        z += 1.6
    slab(m, 5.3, 10.7, 5.3, 10.7, z, z + 7.0, "limestone", tone=0.1)
    z += 7.0
    for i in range(3):
        r = 3.6 + i * 1.0
        slab(m, 8 - r, 8 + r, 8 - r, 8 + r, z, z + 1.4, "limestone", tone=0.25)
        z += 1.4
    revolve(m, 8, 8, z, z + 1.5, lambda t: 3.0 + 1.0 * t, "bronze", tone=0.2)
    fill(m, (5, 11, 5, 11, z + 1.0, z + 3.0), "fire", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.6 - (Z - z - 1.0))
    halo(m, 8, 8, z + 2.0, 12.0, FIRE, 1.0)
    return m


def p_incense(v, frame, frames, k):
    """A tall bronze incense burner with a conical lid, as in the audience relief."""
    m = _m(1, 1, 20, k)
    from sets.parsa.landmarks import _incense_stand
    _incense_stand(m, 8, 8)
    fill(m, (7, 9, 7, 9, 13.0, 13.8), "ember")
    halo(m, 8, 8, 13.5, 4.0, FIRE, 0.5)
    return m


def p_brazier(v, frame, frames, k):
    m = _m(1, 1, 14, k)
    for a in (0.3, 2.4, 4.5):
        rod(m, (8 + 3.5 * math.cos(a), 8 + 3.5 * math.sin(a), 0), (8 + 2 * math.cos(a), 8 + 2 * math.sin(a), 7.0),
            0.35, "bronze")
    revolve(m, 8, 8, 6.5, 9.0, lambda t: 2.4 + 1.4 * t, "bronze", tone=0.2)
    fill(m, (4, 12, 4, 12, 8.5, 11.0), "fire", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.6 - (Z - 8.5) * 1.2)
    halo(m, 8, 8, 9.5, 11.0, FIRE, 0.9)
    return m


def p_torch(v, frame, frames, k):
    """A torch in an iron bracket on a short post (set against walls and towers)."""
    m = _m(1, 1, 18, k)
    rod(m, (8, 2, 0), (8, 2, 12.0), 0.8, "wood")
    rod(m, (8, 2, 10.0), (8, 5, 12.5), 0.3, "metal")
    rod(m, (8, 5, 11.0), (8, 5.4, 14.0), 0.5, "wood")
    ellipsoid(m, (8, 5.4, 15.0), (0.9, 0.9, 1.5), "fire")
    halo(m, 8, 5.4, 15.0, 10.0, FIRE, 0.9)
    return m


def p_lamp(v, frame, frames, k):
    """A doorway lamp: a bronze lamp hung from an iron arm on a plastered door post (the
    houses' and stores' doors at night, where a torch would be too much)."""
    m = _m(1, 1, 18, k)
    slab(m, 6.5, 9.5, 1.0, 3.5, 0.0, 14.0, "mudbrick", tone=M.mud_plaster(330, 0.4))
    slab(m, 6.0, 10.0, 0.5, 4.0, 14.0, 15.0, "cedar", tone=0.1)
    rod(m, (8.0, 3.5, 12.5), (8.0, 6.5, 12.5), 0.25, "metal")
    rod(m, (8.0, 6.5, 12.5), (8.0, 6.5, 11.2), 0.12, "metal")
    ellipsoid(m, (8.0, 6.5, 10.6), (1.0, 0.8, 0.5), "bronze", tone=0.3)
    ellipsoid(m, (8.8, 6.5, 11.3), (0.35, 0.35, 0.7), "fire")
    halo(m, 8.6, 6.5, 11.2, 7.0, LAMP, 0.8)
    return m


def p_parasol(v, frame, frames, k):
    """The royal parasol on its stand: a gilded shaft, a purple canopy with a gold fringe."""
    m = _m(1, 1, 32, k)
    revolve(m, 8, 8, 0, 1.5, lambda t: 2.4 - 0.6 * t, "bronze")
    rod(m, (8, 8, 0), (8, 8, 28.0), 0.4, "gold")
    fill(m, (0, 16, 0, 16, 24.0, 28.5), "purple",
         lambda X, Y, Z: (np.hypot(X - 8, Y - 8) < 7.5) & (np.abs(Z - (28.0 - (np.hypot(X - 8, Y - 8) / 7.5) ** 1.5 * 3.5)) < 0.6),
         tone=lambda X, Y, Z: 0.3 - 0.5 * ((np.arctan2(Y - 8, X - 8) * 4 / np.pi) % 1.0 < 0.15))
    fill(m, (0, 16, 0, 16, 23.5, 25.0), "gold", lambda X, Y, Z: np.abs(np.hypot(X - 8, Y - 8) - 7.3) < 0.5)
    ellipsoid(m, (8, 8, 29.0), (0.7, 0.7, 0.9), "gold", tone=0.4)
    return m


def p_throne(v, frame, frames, k):
    """A throne with lion's feet and a high back, gilded on cedar, and its footstool."""
    m = _m(1, 1, 22, k)
    for x, y in ((4, 4), (4, 11), (11, 4), (11, 11)):
        rod(m, (x, y, 0.6), (x, y, 8.0), 0.6, "gold", tone=0.2)
        ellipsoid(m, (x, y, 0.8), (0.9, 0.9, 0.8), "gold", tone=0.4)
    slab(m, 3, 12, 3, 12, 8.0, 9.4, "cedar", tone=0.3)
    slab(m, 3.6, 11.4, 3.6, 11.4, 9.4, 10.2, "purple", tone=0.2)
    slab(m, 3, 4.6, 3, 12, 9.4, 20.0, "cedar", tone=0.1)
    slab(m, 3.2, 4.4, 3.2, 11.8, 18.0, 19.0, "gold", tone=0.3)
    slab(m, 13, 15.5, 5.5, 9.5, 0, 3.0, "gold", tone=0.1)
    return m


def p_crane(v, frame, frames, k):
    """Shear legs: two timber legs lashed at the top, guy ropes, a block and a hanging stone."""
    m = _m(2, 1, 58, k)
    sw = (0.0, 1.0)[frame % 2]
    top = (16.0 + sw, 8.0, 54.0)
    for y in (2.0, 14.0):
        rod(m, (4.0, y, 0.0), top, 0.8, "wood_light")
    rod(m, top, (30.0, 8.0, 0.0), 0.2, "straw")
    rod(m, top, (top[0], 8.0, 20.0), 0.2, "straw")
    ellipsoid(m, (top[0], 8.0, 51.0), (1.0, 1.0, 1.2), "wood", tone=0.2)
    slab(m, top[0] - 3, top[0] + 3, 5.5, 10.5, 14.0, 20.0, "limestone", tone=0.3)
    for y in (2.0, 14.0):
        slab(m, 2.0, 6.0, y - 1.5, y + 1.5, 0, 1.0, "stone")
    return m


def p_scaffold(v, frame, frames, k):
    """Lashed poles round a column shaft still rising (two heights)."""
    h = (36.0, 56.0)[v]
    m = _m(1, 1, int(h) + 6, k)
    from arch import column, Column
    column(m, 8, 8, 0.0, Column(2.4, h - 2.0, base="square", capital="none", flutes=16))
    from sets.parsa.landmarks import _scaffold
    _scaffold(m, 8, 8, h - 2.0, 5.5)
    return m


def p_drum_stack(v, frame, frames, k):
    m = _m(1, 1, 14, k)
    for i in range(2):
        rod(m, (3, 4 + i * 6, 2.5), (13, 4 + i * 6, 2.5), 2.4, "limestone", tone=0.2)
    revolve(m, 8, 7, 5.0, 9.0, lambda t: 2.6, "limestone", tone=lambda X, Y, Z: 0.4 * (np.cos(np.arctan2(Y - 7, X - 8) * 12) > 0.3))
    slab(m, 3, 7, 11, 15, 0, 5.0, "limestone", tone=0.35)
    return m


def p_jars(v, frame, frames, k):
    m = _m(1, 1, 14, k)
    for i, (x, y, h) in enumerate(((5, 5, 10), (11, 6, 9), (6, 11, 8), (11, 11, 10))):
        revolve(m, x, y, 0, h, lambda t, h=h: 1.0 + 1.9 * np.clip(np.sin(np.pi * np.clip(t * 1.05, 0, 1)), 0, 1) ** 0.8,
                "mudbrick", tone=0.1 * i)
        revolve(m, x, y, h, h + 1.2, lambda t: 1.1, "mudbrick", tone=-0.3)
    return m


def p_sacks(v, frame, frames, k):
    m = _m(1, 1, 10, k)
    for i, (x, y) in enumerate(((5, 5), (10, 6), (6, 10.5))):
        ellipsoid(m, (x, y, 3.4), (2.6, 2.4, 3.4), "straw", tone=0.1 * i)
        fill(m, (x - 1, x + 1, y - 1, y + 1, 6.4, 7.6), "straw", tone=-0.3)
    revolve(m, 11.5, 11.5, 0, 3.0, lambda t: 2.0, "wood_light", tone=0.2)
    fill(m, (10, 13, 10, 13, 2.4, 3.0), "yellow", lambda X, Y, Z: np.hypot(X - 11.5, Y - 11.5) < 1.6)
    return m


def p_scribe_desk(v, frame, frames, k):
    """A reed mat, a board of clay tablets drying, a jar of clay, styluses, a leather scroll."""
    m = _m(1, 1, 8, k)
    slab(m, 2, 14, 3, 13, 0, 0.5, "straw", tone=lambda X, Y, Z: -0.3 * ((X % 1.5) < 0.4))
    slab(m, 3, 9, 4, 10, 0.5, 1.4, "wood_light", tone=0.1)
    for i in range(3):
        for j in range(2):
            slab(m, 3.6 + i * 1.9, 5.0 + i * 1.9, 4.8 + j * 2.6, 6.6 + j * 2.6, 1.4, 2.1, "mudbrick", tone=0.4)
    revolve(m, 11.5, 10, 0.5, 5.0, lambda t: 1.6 + 0.4 * np.sin(np.pi * t), "mudbrick", tone=0.1)
    rod(m, (10.5, 4.5, 0.8), (13.0, 7.0, 0.8), 0.7, "linen", tone=0.3)
    rod(m, (9.5, 11.5, 0.8), (12.5, 12.5, 0.8), 0.2, "cedar")
    return m


def p_scales(v, frame, frames, k):
    """A balance with pans, duck-shaped weights and pieces of silver."""
    m = _m(1, 1, 18, k)
    slab(m, 6.5, 9.5, 6.5, 9.5, 0, 1.0, "cedar")
    rod(m, (8, 8, 1.0), (8, 8, 14.0), 0.4, "bronze")
    rod(m, (8, 2.5, 13.5), (8, 13.5, 13.5), 0.3, "bronze")
    for y in (3.0, 13.0):
        rod(m, (8, y, 13.4), (8, y, 8.0), 0.12, "straw")
        revolve(m, 8, y, 7.4, 8.2, lambda t: 1.8, "bronze", tone=0.3)
    for i, x in enumerate((2.5, 4.5)):
        ellipsoid(m, (x, 12.0, 1.0), (1.1 - 0.3 * i, 0.8, 0.9), "polished", tone=0.6)
        ellipsoid(m, (x + 0.8, 12.0, 1.8), (0.4, 0.35, 0.4), "polished", tone=0.6)
    for x, y in ((12, 3), (13, 5), (12.5, 4)):
        fill(m, (x - 0.5, x + 0.5, y - 0.5, y + 0.5, 0, 0.6), "snow", tone=0.5)
    return m


def p_tent(v, frame, frames, k):
    """A delegation's tent on the plain: a ridge tent of striped wool with a door flap tied
    open over a patterned rug on one side and a felt-walled porch awning on the other (its
    two rotations read as two different camps), guy ropes to pegs, a pennant on the pole."""
    m = _m(2, 2, 30, k)
    tent(m, 3, 29, 5, 27, 0, 21.0, cloth="wool", stripe="cinnabar", ridge="x", door_face="+x")
    for x in (3.0, 29.0):
        rod(m, (x, 16, 0), (x, 16, 22.5), 0.45, "wood")
    rod(m, (29.0, 16, 22.5), (29.0, 16, 27.0), 0.3, "wood")
    fill(m, (28.8, 29.2, 16.3, 20.0, 24.0, 27.0), "saffron",
         lambda X, Y, Z: (Z - 24.0) > (Y - 16.3) * 0.6, tone=0.2)
    for px, py, tx, ty in ((3, 16, -1, 16), (29, 16, 32, 16), (16, 5, 16, 1), (16, 27, 16, 31)):
        rod(m, (px, py, 18.0 if px in (3, 29) else 4.0), (tx, ty, 0.3), 0.15, "linen")
    # The rug before the door (south) and the porch awning (west) on felt panels.
    fill(m, (30, 34, 9, 23, 0, 0.4), "cinnabar",
         tone=lambda X, Y, Z: 0.5 * (((X + Y) % 2.0) < 0.6) - 0.6 * ((np.abs(Y - 16) > 6) | (X > 33.3)))
    awning(m, 8, 24, 27, 31, 11.0, cloth="felt", poles=True, sag=0.3)
    slab(m, 8, 24, 30.6, 31.0, 0, 7.0, "felt", tone=lambda X, Y, Z: 0.4 * ((X % 4.0) < 0.5) - 0.1)
    for i, x in enumerate((12.0, 15.0)):
        revolve(m, x, 29.0, 0, 3.2, lambda t: 1.0 + 0.5 * np.sin(np.pi * t), "bronze", tone=0.1 * i)
    halo(m, 31.0, 16.0, 6.0, 9.0, LAMP, 0.7)
    return m


def p_loom(v, frame, frames, k):
    """An upright two-beam loom with patterned cloth growing on it."""
    m = _m(1, 1, 22, k)
    for y in (2.0, 14.0):
        rod(m, (8, y, 0), (8, y, 20.0), 0.5, "wood")
    rod(m, (8, 2, 19.0), (8, 14, 19.0), 0.6, "wood_light")
    rod(m, (8, 2, 2.0), (8, 14, 2.0), 0.6, "wood_light")
    fill(m, (7.6, 8.4, 2.5, 13.5, 2.6, 18.5), "linen", lambda X, Y, Z: ((Y * 2) % 1.0) < 0.3, tone=0.4)
    fill(m, (7.6, 8.6, 2.5, 13.5, 2.6, 10.0), "cinnabar",
         tone=lambda X, Y, Z: 0.5 * ((np.floor(Y) + np.floor(Z)) % 2 == 0) - 0.1)
    fill(m, (7.5, 8.7, 2.5, 13.5, 8.5, 10.0), "lapis", tone=0.2)
    return m


def p_horse_line(v, frame, frames, k):
    m = _m(3, 1, 16, k)
    for x in (3, 24, 45):
        rod(m, (x, 8, 0), (x, 8, 12.0), 0.7, "wood")
    rod(m, (3, 8, 11.0), (45, 8, 11.0), 0.2, "straw")
    for x in (13, 34):
        revolve(m, x, 12, 0, 3.0, lambda t: 2.2 + 0.4 * t, "straw", tone=-0.1)
        fill(m, (x - 2, x + 2, 10, 14, 2.6, 3.4), "yellow", lambda X, Y, Z: np.hypot(X - x, Y - 12) < 2.0)
    return m


def p_trough(v, frame, frames, k):
    m = _m(1, 1, 7, k)
    slab(m, 2, 14, 4.5, 11.5, 0, 5.0, "limestone", tone=ashlar_tone(5.0, 6.0, 420))
    carve(m, (3, 13, 5.5, 10.5, 1.5, 6.0))
    slab(m, 3, 13, 5.5, 10.5, 1.5, 3.6, "water", tone=0.2)
    return m


def p_threshing(v, frame, frames, k):
    """A beaten-earth threshing floor with a kerb of stones and heaps of straw and grain."""
    m = _m(3, 3, 6, k)
    fill(m, (0, 48, 0, 48, 0, 0.6), "soil", lambda X, Y, Z: np.hypot(X - 24, Y - 24) < 21,
         tone=lambda X, Y, Z: 0.6 + 0.3 * ((np.hypot(X - 24, Y - 24) % 3.0) < 0.8))
    for a in np.linspace(0, 2 * math.pi, 26, endpoint=False):
        ellipsoid(m, (24 + 21.5 * math.cos(a), 24 + 21.5 * math.sin(a), 0.8), (1.3, 1.3, 1.0), "stone", tone=0.1)
    for (x, y, r) in ((16, 30, 6.0), (30, 18, 4.5)):
        ellipsoid(m, (x, y, 1.0), (r, r, r * 0.55), "straw", tone=0.3)
    ellipsoid(m, (28, 30, 0.8), (3.0, 3.0, 1.6), "yellow", tone=0.1)
    return m


def p_dovecote(v, frame, frames, k):
    m = _m(1, 1, 28, k)
    revolve(m, 8, 8, 0, 22.0, lambda t: 5.5 - 1.2 * t, "mudbrick", tone=plaster_tone(430, 0.4))
    revolve(m, 8, 8, 22.0, 25.0, lambda t: 4.6 * (1 - t) + 0.6, "mudbrick", tone=0.2)
    for z in (8.0, 13.0, 18.0):
        for a in (0.3, 1.1, 1.9):
            x, y = 8 + 5.2 * math.cos(a), 8 + 5.2 * math.sin(a)
            fill(m, (x - 0.6, x + 0.6, y - 0.6, y + 0.6, z, z + 1.2), "ink")
    return m


def p_carpet(v, frame, frames, k):
    """A knotted pile carpet: a field of squares in a border of riders and deer."""
    m = _m(2, 1, 2, k)
    base = ("cinnabar", "lapis")[v % 2] if v < 2 else "cinnabar"
    slab(m, 2, 30, 2, 14, 0, 0.6, base, tone=lambda X, Y, Z: 0.5 * ((np.floor(X / 2) + np.floor(Y / 2)) % 2 == 0) - 0.2)
    fill(m, (2, 30, 2, 14, 0, 0.7), "saffron",
         lambda X, Y, Z: (X < 4) | (X > 28) | (Y < 4) | (Y > 12), tone=lambda X, Y, Z: 0.5 * ((X + Y) % 3.0 < 1.0))
    fill(m, (2, 30, 2, 14, 0, 0.75), "malachite", lambda X, Y, Z: ((X < 3) | (X > 29) | (Y < 3) | (Y > 13)) &
         ((np.floor(X) + np.floor(Y)) % 2 == 0))
    return m


def p_archery_butt(v, frame, frames, k):
    m = _m(1, 1, 16, k)
    for x in (4.0, 12.0):
        rod(m, (x, 10, 0), (x, 7, 11.0), 0.4, "wood")
    fill(m, (3, 13, 6, 9, 2.0, 13.0), "straw", lambda X, Y, Z: np.hypot(X - 8, Z - 7.5) < 5.2, tone=0.1)
    fill(m, (3, 13, 8.8, 9.4, 2.0, 13.0), "cinnabar", lambda X, Y, Z: np.abs(np.hypot(X - 8, Z - 7.5) - 2.6) < 0.7)
    fill(m, (3, 13, 8.8, 9.4, 2.0, 13.0), "white_paint", lambda X, Y, Z: np.hypot(X - 8, Z - 7.5) < 1.1)
    rod(m, (6.5, 9.5, 8.5), (5.5, 12.0, 9.5), 0.15, "cedar")
    return m


def _wall(m, mask, h, t, fort=False):
    """A wall piece with arms to same-item neighbours (N -y, E +x, S +y, W -x)."""
    c = 8.0
    boxes = [(c - t, c + t, c - t, c + t)]
    if mask & 1:
        boxes.append((c - t, c + t, -0.5, c))
    if mask & 2:
        boxes.append((c, 16.5, c - t, c + t))
    if mask & 4:
        boxes.append((c - t, c + t, c, 16.5))
    if mask & 8:
        boxes.append((-0.5, c, c - t, c + t))
    for b in boxes:
        mudbrick_wall(m, *b, 0, h, plinth=4.0 if fort else 1.6, plinth_mat="ashlar", seed=440 + int(fort))
        slab(m, *b, h, h + 0.8, "mudbrick", tone=0.2)
    for b in boxes:
        x0, x1, y0, y1 = b
        sides = [f for f, ok in (("+x", x1 < 16), ("-x", x0 > 0), ("+y", y1 < 16), ("-y", y0 > 0)) if ok]
        if x1 - x0 > y1 - y0:
            sides = ["+y", "-y"]
        elif y1 - y0 > x1 - x0:
            sides = ["+x", "-x"]
        merlons(m, x0, x1, y0, y1, h + 0.8, 4.0 if fort else 3.0, "mudbrick", pitch=4.0, sides=sides,
                thick=1.2)
    return m


def p_wall(v, frame, frames, k):
    return _wall(Model.empty(-1, 17, -1, 17, 0, 26, k=k), v, 18.0, 2.2)


def fort_wall(v, frame, frames, k):
    return _wall(Model.empty(-1, 17, -1, 17, 0, 36, k=k), v, 26.0, 3.6, fort=True)


def p_wall_gate(v, frame, frames, k):
    """A gate in the wall (the wall runs along y): a passage under a cedar lintel, the wooden
    leaves standing open against the jambs, the wall raised a little over the gate. The
    passage stays clear for 1.5 tile heights so walkers pass through (the item is walkable)."""
    m = Model.empty(-1, 17, -1, 17, 0, 36, k=k)
    mudbrick_wall(m, 5.8, 10.2, -0.5, 16.5, 0, 30.0, plinth=1.6, seed=450)
    carve(m, (5.0, 11.0, 1.2, 14.8, 0.5, 24.6))
    slab(m, 5.0, 11.0, 0.6, 15.4, 24.6, 26.0, "cedar", tone=M.timber("y", 451))
    for y0 in (1.2, 14.2):
        fill(m, (5.4, 10.6, y0, y0 + 0.6, 0.5, 23.5), "cedar", tone=lambda X, Y, Z: -0.5 * ((X % 2.0) < 0.35) + 0.1)
    merlons(m, 5.8, 10.2, -0.5, 16.5, 30.0, 3.5, "mudbrick", pitch=4.0, sides=("+x", "-x"), thick=1.2)
    return m


def fort_tower(v, frame, frames, k):
    """A square tower of the mountain fortification: mudbrick on a stone foot, merlons, slit
    windows, a torch."""
    m = _m(2, 2, 52, k)
    mudbrick_wall(m, 1, 31, 1, 31, 0, 44.0, plinth=6.0, seed=460)
    for face in ("+x", "+y"):
        for z in (18.0, 32.0):
            fill(m, face_box(face, 1, 31, 1, 31, z, z + 4.0, 13.5, 15.5, -0.2, 1.5), "ink", tone=0.3)
    slab(m, 0.5, 31.5, 0.5, 31.5, 44.0, 45.0, "mudbrick", tone=0.3)
    merlons(m, 1, 31, 1, 31, 45.0, 5.0, "mudbrick", pitch=6.0)
    rod(m, (31.5, 16, 30.0), (33.0, 16, 33.0), 0.3, "metal")
    ellipsoid(m, (33.0, 16, 34.0), (0.9, 0.9, 1.4), "fire")
    halo(m, 33.0, 16, 34.0, 12.0, FIRE, 0.9)
    return m


def stair_relief(v, frame, frames, k):
    """A short stone flight two tiles wide rising one level over one tile: four deep steps with
    lit nosings and shaded risers between ashlar cheek walls crowned with stepped merlons (QA4
    V-A-005). Like every kit stair it climbs away from its front: toward -y at r0 (the
    geometry's `climb`)."""
    m = Model.empty(-1, 33, -1, 17, 0, 16, k=k)
    flight(m, 0.5, 31.5, 0.0, 16.0, 8.0, 4, "limestone", tone=M.ashlar(2.0, 6.0, 13, spread=0.3), cheek=2.4)
    for x0, x1 in ((0.5, 2.9), (29.1, 31.5)):
        merlons(m, x0, x1, 0.0, 6.0, 10.4, 2.4, "limestone", pitch=3.0, sides=("+x", "-x"), thick=2.0)
    return m


def drain_outfall(v, frame, frames, k, rain=False):
    """A grated drain mouth high on the terrace face (the face along the tile's -x edge at r0),
    its dark stain down the stone; the 'rain' state spouts water into a splash."""
    m = Model.empty(-1, 17, -1, 17, 0, 40, k=k)
    m.hover = False
    slab(m, -0.5, 1.6, 5.5, 10.5, 30.0, 34.0, "limestone", tone=0.3)
    fill(m, (1.0, 1.7, 6.2, 9.8, 30.6, 33.4), "ink", tone=0.2,
         mask=lambda X, Y, Z: ~(((Y * 2.0) % 1.0) < 0.3))
    fill(m, (-0.4, 0.2, 6.5, 9.5, 0.5, 30.0), "ink", lambda X, Y, Z: (hash01(
        np.floor(Y * 2).astype(np.int64), np.floor(Z).astype(np.int64), 470) < 0.55 - Z / 80), tone=1.0)
    if rain:
        for i in range(10):
            t = ((i / 10) + frame * 0.25) % 1.0
            x = 1.6 + 6.0 * t
            z = 31.5 - 31.0 * t * t
            fill(m, (x - 0.8, x + 0.8, 6.8, 9.2, z - 1.2, z + 1.0), "water", tone=0.6)
        fill(m, (4, 13, 3, 13, 0, 0.8), "water", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 4.0,
             tone=lambda X, Y, Z: 0.8 * (np.abs(np.hypot(X - 8, Y - 8) - 1.5 - frame) < 0.5))
    return m


def p_banner(v, frame, frames, k):
    """The royal standard: a golden eagle with spread wings on a tall shaft (Xenophon), a red
    cloth hanging below it, moving in the wind."""
    m = _m(1, 1, 38, k)
    rod(m, (8, 8, 0), (8, 8, 32.0), 0.45, "cedar")
    ellipsoid(m, (8, 8, 33.4), (1.2, 1.0, 1.4), "gold", tone=0.3)
    ellipsoid(m, (8.8, 8, 34.6), (0.7, 0.6, 0.6), "gold", tone=0.4)
    for side in (-1, 1):
        rod(m, (8, 8, 33.6), (8 - 0.6, 8 + side * 4.0, 36.0), 0.6, "gold", tone=0.2)
    ph = 2 * math.pi * frame / frames
    fill(m, (6, 16, 6, 10, 20.0, 31.0), "cinnabar",
         lambda X, Y, Z: (X > 8.2) & (X < 8.2 + 7.0 - (31 - Z) * 0.2) &
         (np.abs(Y - 8 - 1.2 * np.sin((X - 8) * 0.9 - ph)) < 0.5),
         tone=lambda X, Y, Z: 0.4 * np.sin((X - 8) * 0.9 - ph) + 0.3 * ((Z % 3.0) < 0.6))
    return m


def p_sluice(v, frame, frames, k, open_=False):
    """A wooden sluice board in a stone frame across a channel; 'open' raises it."""
    m = Model.empty(-1, 17, -1, 17, 0, 12, k=k)
    _channel(m, 1 | 4, 0)
    for x in (3.4, 12.6):
        slab(m, x - 1.0, x + 1.0, 6.5, 9.5, 0, 9.0, "limestone", tone=0.2)
    slab(m, 2.4, 13.6, 6.5, 9.5, 9.0, 10.2, "limestone", tone=0.3)
    z = 5.0 if open_ else 0.8
    slab(m, 4.6, 11.4, 7.5, 8.5, z, z + 5.0, "cedar", tone=lambda X, Y, Z: -0.4 * ((Z % 1.6) < 0.3))
    return m


ITEMS = {f"parsa.{name}": Item(fn, slots=slots, emitters=em) for name, fn, slots, em in (
    ("p_house", p_house, {"door": [{"t": [0, 3], "face": "+y"}]}, {}),
    ("p_house_small", p_house_small, {"door": [{"t": [0, 2], "face": "+y"}]}, {}),
    ("p_granary", p_granary, {"door": [{"t": [0, 2], "face": "+y"}],
                                 "queue": [{"t": [1, 2], "face": "-y"}, {"t": [1, 3], "face": "-y"}, {"t": [0, 3], "face": "-y"}]}, {}),
    ("p_workshop", p_workshop, {"work": [{"t": [0, 2], "face": "-y"}, {"t": [1, 2], "face": "-y"},
                                          {"t": [2, 2], "face": "-y"}]}, {}),
    ("p_kiln", p_kiln, {"load": [{"t": [0, 1], "face": "-y"}]}, {"smoke": (8.0, 8.0, 20.0)}),
    ("p_brickfield", p_brickfield, {"mould": [{"t": [2, 0], "face": "-x"}, {"t": [2, 1], "face": "-x"}]}, {}),
    ("p_oven", p_oven, {"bake": [{"t": [0, 1], "face": "-y"}]}, {"smoke": (8.0, 8.0, 11.0)}),
    ("p_well", p_well, {"draw": [{"t": [1, 0], "face": "-x"}]}, {}),
    ("p_channel", p_channel, {}, {}),
    ("p_basin", p_basin, {"fill": [{"t": [0, 1], "face": "-y"}]}, {}),
    ("p_qanat_shaft", p_qanat_shaft, {}, {}),
    ("p_fire_altar", p_fire_altar, {"tend": [{"t": [1, 0], "face": "-x"}]}, {"fire": (8.0, 8.0, 18.0)}),
    ("p_incense", p_incense, {}, {"smoke": (8.0, 8.0, 16.5)}),
    ("p_brazier", p_brazier, {}, {"fire": (8.0, 8.0, 10.5)}),
    ("p_torch", p_torch, {}, {"flame": (8.0, 5.4, 16.0)}),
    ("p_lamp", p_lamp, {}, {}),
    ("p_parasol", p_parasol, {}, {}),
    ("p_throne", p_throne, {"seat": [{"t": [0, 0], "face": "+x", "z": 18}]}, {}),
    ("p_crane", p_crane, {"rope": [{"t": [2, 0], "face": "-x"}]}, {}),
    ("p_scaffold", p_scaffold, {}, {}),
    ("p_drum_stack", p_drum_stack, {"carve": [{"t": [0, 1], "face": "-y"}]}, {}),
    ("p_jars", p_jars, {}, {}),
    ("p_sacks", p_sacks, {}, {}),
    ("p_scribe_desk", p_scribe_desk, {"write": [{"t": [0, 1], "face": "-y"}]}, {}),
    ("p_scales", p_scales, {"weigh": [{"t": [0, 1], "face": "-y"}]}, {}),
    ("p_tent", p_tent, {"door": [{"t": [2, 0], "face": "+x"}]}, {}),
    ("p_loom", p_loom, {"weave": [{"t": [1, 0], "face": "-x"}]}, {}),
    ("p_horse_line", p_horse_line, {"groom": [{"t": [0, 1], "face": "-y"}, {"t": [2, 1], "face": "-y"}]}, {}),
    ("p_trough", p_trough, {"groom": [{"t": [0, 1], "face": "-y"}]}, {}),
    ("p_threshing", p_threshing, {"thresh": [{"t": [1, 3], "face": "-y"}, {"t": [3, 1], "face": "-x"}]}, {}),
    ("p_dovecote", p_dovecote, {}, {}),
    ("p_carpet", p_carpet, {}, {}),
    ("p_archery_butt", p_archery_butt, {}, {}),
    ("p_wall", p_wall, {}, {}),
    ("p_wall_gate", p_wall_gate, {}, {}),
    ("fort_wall", fort_wall, {}, {}),
    ("fort_tower", fort_tower, {}, {"torch": (33.0, 16.0, 35.0)}),
    ("stair_relief", stair_relief, {}, {}),
    ("drain_outfall", drain_outfall, {}, {}),
    ("p_banner", p_banner, {}, {}),
    ("p_sluice", p_sluice, {"open": [{"t": [1, 0], "face": "-x"}]}, {}),
)}

STATES = {
    ("parsa.drain_outfall", "rain"): lambda v, f, n, k: drain_outfall(v, f, n, k, rain=True),
    ("parsa.p_sluice", "open"): lambda v, f, n, k: p_sluice(v, f, n, k, open_=True),
    # 'lit' gates the glow layer (living-world §2.5): the look is the plain one.
    ("parsa.p_torch", "lit"): p_torch,
    ("parsa.p_lamp", "lit"): p_lamp,
    ("parsa.p_brazier", "lit"): p_brazier,
}

FRAMES = {"parsa.p_well": 2, "parsa.p_crane": 2, "parsa.p_channel": 4, "parsa.p_basin": 4, "parsa.p_banner": 6}
