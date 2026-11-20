"""The Athens kit (athens.md §3.3): courtyard houses of several sizes, workshops, market stalls,
kilns, wheels, forges, looms, presses, threshing floors, wells, fountains, graves, stelai,
statue bases, cranes, scaffolds, braziers, lamps, couches, the city wall with towers and
gates, the Long Walls, track markers and a marble stair. Toy scale like the home kit (a door
about 46 px, an adult 40 px); rotatable pieces face +y (their front is the lower-left face the
camera sees at r0), and every side differs, so the four rotations read as different places."""

import math

import numpy as np

import waterworks

import materials as M
from arch import carve, ellipsoid, face_box, fill, flight, halo, mark, revolve, rod, slab
from greek import city_wall, herm, house_wall, stele, statue_base, tiled_roof, vase
from setbuild import Item
from sets.athens.common import FIRE, LAMP, crane, lamp_niche, olive_tree, scaffold
from voxel import Model, Rng, hash01, value_noise

T = 16


def _m(fw, fh, top, k, below=0):
    return Model.empty(-3, fw * T + 3, -3, fh * T + 3, -below, top, k=k)


def _door(m, face, box, s0, w, h, leaf="cedar", lamp=True):
    """A plank door in a plastered reveal, a lamp in a niche beside it, soot above."""
    x0, x1, y0, y1 = box[:4]
    carve(m, face_box(face, x0, x1, y0, y1, 0.0, h, s0, s0 + w, -0.2, 1.2))
    fill(m, face_box(face, x0, x1, y0, y1, 0.0, h, s0, s0 + w, 1.0, 1.6), leaf,
         tone=lambda X, Y, Z: -0.45 * (((X + Y) % 2.2) < 0.4))
    fill(m, face_box(face, x0, x1, y0, y1, h, h + 1.0, s0 - 0.8, s0 + w + 0.8, -0.4, 0.2), "wood", tone=0.1)
    M.stain(m, face_box(face, x0, x1, y0, y1, h + 1.0, h + 5.0, s0, s0 + w, -0.2, 0.5), lambda X, Y, Z: True, -0.35)
    if lamp:
        bx = face_box(face, x0, x1, y0, y1, h - 5.0, h - 3.6, s0 + w + 1.4, s0 + w + 2.6, -0.6, 0.2)
        fill(m, bx, "lamp")
        halo(m, (bx[0] + bx[1]) / 2, (bx[2] + bx[3]) / 2, h - 4.2, 8.0, LAMP, 0.7, kind="door")
    else:
        mark(m, face_box(face, x0, x1, y0, y1, h - 1.0, h, s0, s0 + w, -0.6, 0.0), "door")


def _window(m, face, box, s0, z0, w=2.0, h=2.6, shutter=None):
    x0, x1, y0, y1 = box[:4]
    fill(m, face_box(face, x0, x1, y0, y1, z0, z0 + h, s0, s0 + w, -0.1, 0.8), "ink", tone=0.0)
    mark(m, face_box(face, x0, x1, y0, y1, z0, z0 + h, s0, s0 + w, -0.1, 0.0), "window", max(3.0, w * 1.6))
    if shutter:
        fill(m, face_box(face, x0, x1, y0, y1, z0, z0 + h, s0 + w, s0 + w + 1.2, -0.5, 0.0), shutter, tone=0.1)


def _room(m, x0, x1, y0, y1, h, seed, plaster="whitewash", ridge="x", rise=None, roof=True):
    house_wall(m, x0, x1, y0, y1, 0.0, h, seed, socle=3.0, plaster=plaster)
    if roof:
        tiled_roof(m, x0 - 1.5, x1 + 1.5, y0 - 1.5, y1 + 1.5, h, rise or min(x1 - x0, y1 - y0) * 0.22, axis=ridge,
                   material="terracotta", kind="laconian", seed=seed + 3, antefixes=False)


def _court(m, x0, x1, y0, y1, seed, fig=True):
    """A courtyard floor of beaten earth and pebbles, the household altar of Zeus of the court,
    a cistern mouth, a fig or a vine."""
    fill(m, (x0, x1, y0, y1, 0.0, 0.5), "gravel", tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z, 1.0, seed) - 0.5) * 0.6)
    slab(m, x0 + 2.0, x0 + 5.0, y0 + 2.0, y0 + 4.5, 0.0, 3.4, "whitewash", tone=0.2)        # the altar
    fill(m, (x1 - 6.0, x1 - 2.0, y1 - 6.0, y1 - 2.0, 0.0, 2.0), "poros",
         lambda X, Y, Z: np.hypot(X - (x1 - 4.0), Y - (y1 - 4.0)) < 1.9, tone=0.2)
    fill(m, (x1 - 6.0, x1 - 2.0, y1 - 6.0, y1 - 2.0, 1.0, 2.1), "ink",
         lambda X, Y, Z: np.hypot(X - (x1 - 4.0), Y - (y1 - 4.0)) < 1.0, tone=0.0)
    if fig:
        _fig(m, (x0 + x1) / 2 + 2.0, (y0 + y1) / 2, 0.0, 15.0, seed)


def _fig(m, x, y, z, h, seed):
    from models.nature import leaf_mass
    rng = Rng(960, seed)
    for a in (0.5, 2.6, 4.4):
        rod(m, (x, y, z), (x + 3.2 * math.cos(a), y + 3.2 * math.sin(a), z + h * 0.55), 0.6, "wood_grey", tone=0.1)
    clumps = [(x + 4.0 * math.cos(a), y + 4.0 * math.sin(a), z + h * 0.7 + rng.uniform(-1, 1), 3.4)
              for a in (0.0, 2.1, 4.2)] + [(x, y, z + h * 0.88, 3.6)]
    leaf_mass(m, clumps, 961 + seed, materials=(("leaf", 0.8), ("leaf_light", 0.2)), under="leaf_dark", cluster=(2.6, 3.4),
              level=-0.5)


# ---------------------------------------------------------------- houses

def g_house(v, frame, frames, k):
    """A courtyard house (athens.md §3.1): rooms of plastered mudbrick on stone footings round a
    court, tiled roofs, few small windows on the street, one door with a lamp and a herm beside
    it; the court with its altar, cistern and fig; the andron's window on one side, a lean-to
    store with jars on another, an oven and stacked brushwood on the back."""
    m = _m(3, 3, 40, k)
    seed = 600
    _room(m, 0.0, 18.0, 0.0, 48.0, 24.0, seed, ridge="y")                              # the main range (north)
    _room(m, 18.0, 48.0, 0.0, 16.0, 22.0, seed + 1, ridge="x", plaster="mudbrick")      # the east wing
    _room(m, 30.0, 48.0, 16.0, 48.0, 20.0, seed + 2, ridge="y")                         # the andron wing (south)
    house_wall(m, 18.0, 30.0, 45.0, 48.0, 0.0, 14.0, seed + 3, socle=3.0)              # the court wall on the street
    slab(m, 17.5, 30.5, 44.5, 48.5, 14.0, 15.0, "terracotta", tone=0.2)
    _court(m, 18.0, 30.0, 16.0, 45.0, seed)
    # The street (+y): the door with its lamp, a herm, small high windows.
    _door(m, "+y", (18.0, 30.0, 45.0, 48.0), 3.0, 6.0, 12.0)
    herm(m, 31.5, 50.0, 0.0, 10.0)
    for s0 in (4.0, 11.0):
        _window(m, "+y", (0.0, 18.0, 0.0, 48.0), s0, 15.0, shutter="cedar")
    _window(m, "+y", (30.0, 48.0, 16.0, 48.0), 8.0, 13.0)
    # The south side (+x): the andron's window, a bench under a vine on poles.
    _window(m, "+x", (30.0, 48.0, 16.0, 48.0), 12.0, 9.0, w=4.0, h=4.0, shutter="eblue")
    slab(m, 49.0, 51.0, 22.0, 34.0, 0.0, 2.8, "poros", tone=0.2)
    # The back (-y): an oven and stacked brushwood.
    fill(m, (4.0, 12.0, -3.0, 0.0, 0.0, 7.0), "mudbrick", lambda X, Y, Z: np.hypot(X - 8.0, (Z - 0.0) * 0.9) < 4.0,
         tone=-0.1)
    for i in range(4):
        rod(m, (26.0 + i * 1.2, -2.0, 0.6 + (i % 2)), (40.0, -2.0, 0.6 + (i % 2)), 0.5, "wood")
    # The north (-x): storage jars against the wall.
    for i in range(3):
        vase(m, -1.5, 12.0 + i * 4.5, 0.0, 6.0, "pithos", figure="plain", body="clay")
    return m


def g_house_small(v, frame, frames, k):
    """A small house that is also a workshop: one room and a yard, the shop opening on the
    street with a counter, a lean-to of reeds, a roof stair of mudbrick."""
    m = _m(2, 2, 34, k)
    seed = 620
    _room(m, 0.0, 18.0, 0.0, 32.0, 22.0, seed, ridge="y", plaster="mudbrick")
    house_wall(m, 18.0, 32.0, 0.0, 3.0, 0.0, 12.0, seed + 1, socle=2.0)
    house_wall(m, 29.0, 32.0, 0.0, 32.0, 0.0, 12.0, seed + 1, socle=2.0)
    _court(m, 18.0, 29.0, 3.0, 32.0, seed, fig=False)
    # The shop front (+y): a wide opening, a counter with pots.
    carve(m, (3.0, 15.0, 30.5, 33.0, 0.0, 13.0))
    fill(m, (3.0, 15.0, 31.0, 31.6, 0.0, 13.0), "ink", tone=0.0)
    slab(m, 3.0, 15.0, 32.0, 35.0, 0.0, 6.0, "wood", tone=M.timber("x", seed))
    for i in range(3):
        vase(m, 5.0 + i * 4.0, 33.5, 6.0, 4.0, ("krater", "amphora", "hydria")[i], figure="redfigure")
    lamp_niche(m, 16.4, 33.2, 14.0)
    # A reed lean-to on two poles over the yard (+x side), a stair to the roof (-y side).
    for x, y in ((31.0, 8.0), (31.0, 24.0)):
        rod(m, (x, y, 0.0), (x, y, 14.0), 0.5, "wood")
    fill(m, (18.0, 32.0, 6.0, 26.0, 13.0, 14.6), "straw", tone=lambda X, Y, Z: -0.35 * ((Y * 2) % 1.0 < 0.3))
    for i in range(6):
        slab(m, 4.0 + i * 2.0, 6.0 + i * 2.0, -3.0, 0.0, 0.0, 3.5 * (i + 1), "mudbrick", tone=0.2)
    return m


def g_house_two(v, frame, frames, k):
    """A two-storey house: the upper room with a small timber balcony over the street, its
    shutters open, the stair outside, a tiled roof."""
    m = _m(3, 2, 48, k)
    seed = 640
    house_wall(m, 0.0, 32.0, 0.0, 32.0, 0.0, 34.0, seed, socle=3.0)
    tiled_roof(m, -1.5, 33.5, -1.5, 33.5, 34.0, 7.0, axis="x", material="terracotta", kind="laconian", seed=seed + 1)
    _room(m, 32.0, 48.0, 0.0, 32.0, 20.0, seed + 2, ridge="y", plaster="mudbrick")
    _door(m, "+y", (0.0, 32.0, 0.0, 32.0), 4.0, 6.0, 12.0)
    _window(m, "+y", (0.0, 32.0, 0.0, 32.0), 16.0, 22.0, w=4.0, h=5.0, shutter="malachite")
    slab(m, 14.0, 26.0, 32.0, 36.0, 19.5, 20.5, "wood", tone=M.timber("x", seed))      # the balcony
    for x in (14.0, 20.0, 26.0):
        rod(m, (x, 35.5, 20.5), (x, 35.5, 24.0), 0.3, "wood")
        rod(m, (x, 32.0, 17.0), (x, 35.0, 19.5), 0.35, "wood")
    rod(m, (14.0, 35.5, 24.0), (26.0, 35.5, 24.0), 0.35, "wood")
    for i in range(7):     # the outside stair on the +x side
        slab(m, 32.0, 36.0, 4.0 + i * 3.0, 7.0 + i * 3.0, 0.0, 20.0 * (i + 1) / 7, "mudbrick", tone=0.2)
    _window(m, "+x", (32.0, 48.0, 0.0, 32.0), 18.0, 10.0, shutter="cedar")
    return m


def g_herm(v, frame, frames, k):
    m = _m(1, 1, 22, k)
    slab(m, 3.5, 12.5, 3.5, 12.5, 0.0, 1.5, "poros", tone=0.2)
    herm(m, 8.0, 8.0, 1.5, 17.0)
    return m


def g_shrine(v, frame, frames, k):
    """A small roadside shrine: a whitewashed altar with a fire-blackened top, a little votive
    stele and a lamp; garlands."""
    m = _m(1, 1, 20, k)
    slab(m, 3.0, 13.0, 4.0, 12.0, 0.0, 1.2, "poros", tone=0.2)
    slab(m, 5.0, 11.0, 5.0, 11.0, 1.2, 8.0, "whitewash", tone=M.mud_plaster(7, 0.4, 1.2, 1.0))
    slab(m, 4.5, 11.5, 4.5, 11.5, 8.0, 9.0, "whitewash", tone=0.3)
    fill(m, (6.0, 10.0, 6.0, 10.0, 9.0, 9.4), "ink", tone=0.0)
    ellipsoid(m, (8.0, 8.0, 10.2), (1.0, 1.0, 1.4), "fire", tone=0.2)
    halo(m, 8.0, 8.0, 10.5, 8.0, FIRE, 0.6)
    fill(m, (4.5, 11.5, 11.4, 12.0, 6.0, 7.0), "olive", tone=0.2)
    stele(m, 8.0, 3.0, 1.2, 3.0, 8.0, face="+y", subject="decree")
    return m


STALL_GOODS = ("pottery", "fish", "garlands", "figs", "perfume", "sandals")


def g_stall(v, frame, frames, k, closed=False):
    """A market stall of the Agora: a wooden trestle under a cloth awning on poles, wicker screens,
    the goods by trade (variant: pottery, fish, garlands, figs and cheese, perfume, sandals).
    `closed`: after the market, the goods taken in and the board under a tied cloth."""
    m = _m(2, 1, 30, k)
    trade = STALL_GOODS[v % len(STALL_GOODS)]
    seed = 660 + v
    cloth = ("saffron", "eblue", "cinnabar", "malachite", "purple", "ochre")[v % 6]
    for x, y in ((2.0, 2.0), (2.0, 14.0), (30.0, 2.0), (30.0, 14.0)):
        rod(m, (x, y, 0.0), (x, y, 19.0 if y < 8 else 15.0), 0.45, "wood")
    fill(m, (0.0, 32.0, 0.0, 16.0, 13.0, 20.5), cloth,
         lambda X, Y, Z: np.abs(Z - (19.0 - (Y - 2.0) * 0.33 - 0.6 * np.sin(X * 0.35 + frame))) < 0.45,
         tone=lambda X, Y, Z: 0.35 * ((X % 4.0) < 2.0) - 0.15)
    slab(m, 3.0, 29.0, 8.0, 14.0, 6.0, 7.0, "wood_light", tone=M.timber("x", seed))
    for x in (4.0, 28.0):
        slab(m, x - 0.6, x + 0.6, 9.0, 13.0, 0.0, 6.0, "wood", tone=0.0)
    fill(m, (2.5, 29.5, 1.0, 2.2, 0.0, 9.0), "straw", tone=lambda X, Y, Z: -0.3 * (((X + Z) % 1.6) < 0.4))   # wicker
    rng = Rng(seed)
    if closed:
        fill(m, (2.6, 29.4, 7.4, 14.6, 7.0, 10.0), cloth,
             lambda X, Y, Z: Z < 9.6 - 0.8 * np.abs(Y - 11.0) / 3.6, tone=lambda X, Y, Z: -0.25 - 0.3 * ((X % 6.0) < 0.6))
        for x in (8.0, 16.0, 24.0):
            rod(m, (x, 7.3, 7.2), (x, 14.7, 7.2), 0.25, "straw", tone=0.3)
        return m
    if trade == "pottery":
        for i in range(6):
            vase(m, 5.0 + i * 4.0, 11.0, 7.0, 3.6 + rng.uniform(0, 1.5),
                 ("amphora", "krater", "hydria", "lekythos")[i % 4], figure="redfigure" if i % 2 else "blackfigure")
    elif trade == "fish":
        for i in range(8):
            ellipsoid(m, (5.0 + i * 3.0, 11.0 + (i % 2), 7.6), (1.4, 0.5, 0.45), "metal", tone=0.4)
        slab(m, 22.0, 28.0, 9.0, 13.0, 7.0, 8.0, "water", tone=0.2)
    elif trade == "garlands":
        for i in range(5):
            rod(m, (4.0 + i * 5.0, 2.5, 16.0), (6.5 + i * 5.0, 2.5, 13.5), 0.7, "olive", tone=0.2)
            ellipsoid(m, (6.0 + i * 5.0, 11.0, 7.8), (1.6, 1.6, 0.8), ("cinnabar", "saffron", "olive")[i % 3], tone=0.3)
    elif trade == "figs":
        for i in range(4):
            ellipsoid(m, (6.0 + i * 6.0, 11.0, 7.8), (2.4, 2.0, 1.0), "straw", tone=0.0)
            ellipsoid(m, (6.0 + i * 6.0, 11.0, 8.6), (1.8, 1.5, 0.7), "purple" if i % 2 else "whitewash", tone=0.3)
    elif trade == "perfume":
        for i in range(9):
            vase(m, 5.0 + i * 2.6, 11.0 + (i % 2), 7.0, 2.6, "lekythos", figure="whiteground" if i % 2 else "plain",
                 body="gloss")
    else:
        for i in range(6):
            slab(m, 5.0 + i * 3.8, 7.6 + i * 3.8, 10.0, 12.0, 7.0, 7.6, "leather", tone=0.2)
            rod(m, (5.0 + i * 3.8, 2.6, 15.0), (5.0 + i * 3.8, 2.6, 11.0), 0.4, "leather")
    return m


def g_table_banker(v, frame, frames, k):
    """The money-changer's table (trapeza): a plain board on trestles, stacks of silver owls,
    a balance and a stool."""
    m = _m(1, 1, 14, k)
    slab(m, 2.0, 14.0, 4.0, 12.0, 6.0, 7.0, "wood_light", tone=M.timber("x", 3))
    for x in (3.0, 13.0):
        slab(m, x - 0.5, x + 0.5, 5.0, 11.0, 0.0, 6.0, "wood", tone=0.0)
    for i in range(4):
        fill(m, (4.0 + i * 2.0, 5.4 + i * 2.0, 6.0, 7.4, 7.0, 7.6 + 0.4 * i), "metal", tone=0.6)
    rod(m, (10.0, 9.0, 7.0), (10.0, 9.0, 11.0), 0.2, "bronze")
    rod(m, (8.0, 9.0, 11.0), (12.0, 9.0, 11.0), 0.2, "bronze")
    slab(m, 6.0, 10.0, 0.0, 3.0, 0.0, 4.0, "wood", tone=0.1)
    return m


def g_kiln(v, frame, frames, k, firing=False):
    """A potter's updraught kiln: a domed clay chamber on its firebox, soot-blackened at the vent,
    the stoking mouth glowing, brushwood stacked by it. `firing`: flames out of the stoking mouth
    and the vent, the brushwood half burnt."""
    m = _m(1, 1, 26, k)
    revolve(m, 8, 8, 0, 18.0, lambda t: 6.5 * np.sqrt(np.clip(1 - t ** 1.6, 0, 1)) + 0.6, "clay",
            tone=lambda X, Y, Z: M.mud_plaster(640, 0.5, 0, 2.0)(X, Y, Z) - 0.9 * (Z > 14) - 0.4 * (Z > 16.5))
    carve(m, (6, 10, 12, 16, 1.0, 6.0))
    fill(m, (6, 10, 11, 12, 1.0, 6.0), "ember")
    M.stain(m, (5, 11, 12, 16, 5.0, 11.0), lambda X, Y, Z: True, -0.8)
    revolve(m, 8, 8, 17.5, 19.5, lambda t: 1.4, "clay", tone=-0.9)
    for i in range(1 if firing else 3):
        fill(m, (12.5 + i * 0.4, 14.5, 1 + i * 2.2, 3 + i * 2.2, 0, 1.4 + i * 0.3), "wood", tone=0.1)
    if firing:
        fill(m, (6.5, 9.5, 15.5, 17.5, 1.0, 7.5), "ember",
             lambda X, Y, Z: np.abs(X - 8.0) < 1.6 - (Z - 1.0) * 0.2 - (Y - 15.5) * 0.25)
        fill(m, (7.0, 9.0, 7.0, 9.0, 19.5, 23.0), "ember", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 1.1 - (Z - 19.5) * 0.3)
    halo(m, 8, 14, 3.0, 9.0, FIRE, 1.0 if firing else 0.9)
    return m


def g_wheel(v, frame, frames, k):
    """A potter's wheel: a heavy disc turned by a boy, a pot rising on it (2 frames of spin)."""
    m = _m(1, 1, 10, k)
    revolve(m, 8, 8, 0.0, 3.0, lambda t: 1.2, "wood", tone=0.0)
    a0 = frame * 0.8
    fill(m, (2.0, 14.0, 2.0, 14.0, 3.0, 4.2), "wood_light", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 5.2,
         tone=lambda X, Y, Z: 0.35 * ((np.arctan2(Y - 8, X - 8) + a0) % 1.6 < 0.3) - 0.1)
    vase(m, 8.0, 8.0, 4.2, 4.0, "krater", figure="plain", body="clay")
    slab(m, 10.0, 14.0, 12.0, 15.0, 0.0, 3.0, "wood", tone=0.1)                       # the potter's seat
    return m


def g_pots(v, frame, frames, k):
    """Pots drying and stacked: black-gloss cups, red-figure kraters, transport amphorae."""
    m = _m(1, 1, 16, k)
    rng = Rng(680 + v)
    for i, (x, y) in enumerate(((4.0, 4.0), (9.0, 4.5), (13.0, 5.0), (5.0, 10.0), (10.0, 11.0), (13.5, 12.0))):
        kind = ("transport", "amphora", "krater", "hydria", "transport", "lekythos")[(i + v) % 6]
        vase(m, x, y, 0.0, 4.5 + rng.uniform(0, 3.0), kind,
             figure="plain" if kind == "transport" else ("redfigure", "blackfigure")[i % 2], body="clay")
    return m


def g_forge(v, frame, frames, k):
    """A bronze-smith's hearth: a clay hearth with a crucible in the coals, leather bellows, an
    anvil stone, moulds and a half-cast cauldron."""
    m = _m(1, 1, 18, k)
    slab(m, 2.0, 10.0, 3.0, 13.0, 0.0, 5.0, "clay", tone=M.mud_plaster(700, 0.5, 0, 1.0))
    fill(m, (3.0, 9.0, 4.0, 12.0, 5.0, 5.6), "ember", tone=0.0)
    revolve(m, 6.0, 8.0, 5.0, 7.0, lambda t: 1.4 - 0.3 * t, "clay", tone=-0.3)
    halo(m, 6.0, 8.0, 6.0, 10.0, FIRE, 0.9)
    for i in range(2):
        ellipsoid(m, (12.0, 5.0 + i * 5.0, 2.0), (1.8, 1.6, 1.2), "leather", tone=0.1)
    slab(m, 11.0, 14.0, 11.0, 14.0, 0.0, 3.4, "stone", tone=0.2)
    ellipsoid(m, (12.5, 2.5, 2.0), (1.6, 1.6, 1.4), "bronze_cast", tone=0.3)
    rod(m, (2.0, 13.0, 5.0), (2.0, 13.0, 15.0), 0.6, "clay", tone=-0.8)                # the flue
    return m


def g_loom(v, frame, frames, k):
    """A warp-weighted loom leaning against the wall: two uprights, the cloth beam, the warp
    threads with a patterned band woven, clay loom weights hanging in a row."""
    m = _m(1, 1, 26, k)
    for y in (2.0, 14.0):
        rod(m, (6.0, y, 0.0), (8.5, y, 22.0), 0.5, "wood")
    rod(m, (8.5, 1.0, 21.0), (8.5, 15.0, 21.0), 0.6, "wood")
    fill(m, (6.0, 9.0, 2.6, 13.4, 7.0, 21.0), "wool",
         lambda X, Y, Z: np.abs(X - (6.0 + (Z / 22.0) * 2.5)) < 0.35,
         tone=lambda X, Y, Z: -0.3 * ((Y % 0.8) < 0.3))
    fill(m, (6.0, 9.0, 2.6, 13.4, 15.0, 21.0), "cinnabar",
         lambda X, Y, Z: np.abs(X - (6.0 + (Z / 22.0) * 2.5)) < 0.45, tone=0.1)
    fill(m, (6.0, 9.0, 2.6, 13.4, 17.0, 18.5), "saffron",
         lambda X, Y, Z: (np.abs(X - (6.0 + (Z / 22.0) * 2.5)) < 0.5) & ((Y % 2.0) < 1.0), tone=0.2)
    for i in range(9):
        ellipsoid(m, (6.6, 3.0 + i * 1.2, 5.6), (0.6, 0.5, 0.8), "clay", tone=0.1)
    return m


def g_press(v, frame, frames, k):
    """A beam olive press: the long lever beam fixed in a wall socket at one end, weighted with
    stones at the other, pressing a stack of olive baskets on the stone bed with its spout."""
    m = _m(2, 1, 22, k)
    slab(m, 0.0, 4.0, 2.0, 14.0, 0.0, 18.0, "poros", tone=M.ashlar(2.4, 5.0, 720, spread=0.6))
    fill(m, (6.0, 16.0, 3.0, 13.0, 0.0, 3.0), "poros", lambda X, Y, Z: np.hypot(X - 11.0, Y - 8.0) < 5.0, tone=0.2)
    rod(m, (15.5, 8.0, 1.5), (18.0, 8.0, 0.8), 0.5, "poros")
    for i in range(4):
        revolve(m, 11.0, 8.0, 3.0 + i * 1.6, 4.4 + i * 1.6, lambda t: 3.2, "straw", tone=-0.2 * (i % 2))
    rod(m, (2.0, 8.0, 12.0), (30.0, 8.0, 8.0), 1.0, "wood", tone=M.timber("x", 3))
    for i in range(3):
        slab(m, 26.0 + i * 0.6, 30.0, 6.0, 10.0, 3.0 * i, 3.0 * i + 2.8, "stone", tone=0.2 * i)
    return m


def g_threshing(v, frame, frames, k):
    """A threshing floor on a hill: a paved circle with a kerb of stones, the last straw of the
    harvest raked in drifts, a winnowing fork."""
    m = _m(3, 3, 6, k)
    c, r = 24.0, 21.0
    fill(m, (c - r, c + r, c - r, c + r, 0.0, 0.6), "poros", lambda X, Y, Z: np.hypot(X - c, Y - c) < r,
         tone=M.paving(5.0, 4.0, 740))
    fill(m, (c - r - 1, c + r + 1, c - r - 1, c + r + 1, 0.0, 1.8), "stone",
         lambda X, Y, Z: np.abs(np.hypot(X - c, Y - c) - r) < 0.9, tone=lambda X, Y, Z: (hash01(
             np.floor(np.arctan2(Y - c, X - c) * 12).astype(np.int64), 741) - 0.5) * 1.2)
    fill(m, (c - r, c + r, c - r, c + r, 0.6, 2.4), "straw",
         lambda X, Y, Z: (np.abs(np.hypot(X - c, Y - c) - 12.0) < 4.0) & (Z < 0.6 + 1.6 * value_noise(X, Y, Z * 0, 3.0, 742)),
         tone=0.1)
    rod(m, (10.0, 34.0, 0.8), (22.0, 38.0, 1.4), 0.3, "wood")
    return m


def g_well(v, frame, frames, k):
    """A well head: a round marble or terracotta curb worn by ropes, a wooden frame and pulley."""
    m = _m(1, 1, 22, k)
    revolve(m, 8, 8, 0.0, 5.0, lambda t: 4.2 - 0.3 * t, "marble", tone=lambda X, Y, Z: 0.2 * (Z > 4.4))
    fill(m, (5, 11, 5, 11, 2.0, 5.1), "ink", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 2.7, tone=0.0)
    for y in (3.5, 12.5):
        rod(m, (8.0, y, 0.0), (8.0, y, 17.0), 0.5, "wood")
    rod(m, (8.0, 3.0, 16.5), (8.0, 13.0, 16.5), 0.5, "wood")
    ellipsoid(m, (8.0, 8.0, 15.6), (0.9, 0.5, 0.9), "wood_light", tone=0.2)
    rod(m, (8.0, 8.0, 15.0), (8.0, 8.0, 6.0), 0.15, "straw")
    vase(m, 13.0, 13.0, 0.0, 4.5, "hydria", figure="redfigure")
    return m


def g_grave_stele(v, frame, frames, k):
    """A grave in the Kerameikos: a painted relief stele with a palmette crown (the farewell of
    a seated woman and a standing figure), white-ground lekythoi left at its foot."""
    m = _m(1, 1, 24, k)
    slab(m, 3.0, 13.0, 5.0, 11.0, 0.0, 2.0, "poros", tone=0.2)
    stele(m, 8.0, 8.0, 2.0, 8.0, 16.0, face="+y", subject="farewell")
    for i, x in enumerate((4.0, 7.0, 11.5)):
        vase(m, x, 12.5, 0.0, 4.0 + i * 0.4, "lekythos", figure="whiteground")
    return m


def g_grave_mound(v, frame, frames, k):
    """An earth grave mound ringed with stones, grass and asphodel on it, a marker stone."""
    m = _m(2, 2, 14, k)
    fill(m, (2.0, 30.0, 2.0, 30.0, 0.0, 10.0), "soil",
         lambda X, Y, Z: Z < 10.0 * np.clip(1 - (np.hypot(X - 16, Y - 16) / 13.0) ** 2, 0, 1), tone=0.0)
    fill(m, (2.0, 30.0, 2.0, 30.0, 0.0, 10.0), "summer",
         lambda X, Y, Z: (Z > 10.0 * np.clip(1 - (np.hypot(X - 16, Y - 16) / 13.0) ** 2, 0, 1) - 1.0), tone=0.1,
         only_solid=True)
    fill(m, (1.0, 31.0, 1.0, 31.0, 0.0, 2.0), "stone", lambda X, Y, Z: np.abs(np.hypot(X - 16, Y - 16) - 13.5) < 1.0,
         tone=0.1)
    slab(m, 15.0, 17.0, 14.0, 18.0, 9.0, 14.0, "marble", tone=0.2)
    return m


def g_statue_base(v, frame, frames, k):
    """A dedication: a bronze youth on an inscribed marble base."""
    from rig import Dress
    from sets.athens.common import bronze_statue
    m = _m(1, 1, 34, k)
    zb = statue_base(m, 8.0, 8.0, 0.0, 9.0, 6.0)
    bronze_statue(m, Dress(garment="none", beard="none", hair="cedar", hair_style="curly", feet="bare"), 8.0, 8.0,
                  zb, 17.0, anim="talk", frame=1)
    return m


def g_stele_inscr(v, frame, frames, k):
    """An inscribed marble stele: a decree, a tribute list or building accounts, the letters
    painted red and too fine to read."""
    m = _m(1, 1, 22, k)
    slab(m, 4.0, 12.0, 6.0, 10.0, 0.0, 2.0, "poros", tone=0.2)
    stele(m, 8.0, 8.0, 2.0, 6.0, 16.0, face="+y", subject="decree", crown=None)
    return m


def g_crane(v, frame, frames, k):
    """A building crane (two frames of a slow swing)."""
    m = _m(2, 1, 60, k)
    crane(m, 10.0, 8.0, 0.0, 52.0, along="y", swing=frame * 2.0)
    return m


def g_scaffold(v, frame, frames, k):
    m = _m(1, 1, 50, k)
    scaffold(m, 2.0, 14.0, 2.0, 14.0, 0.0, 44.0, decks=3)
    return m


def g_brazier(v, frame, frames, k):
    """A bronze brazier on three legs with its coals, or a torch in a holder."""
    m = _m(1, 1, 16, k)
    for a in (0.0, 2.1, 4.2):
        rod(m, (8 + 3.0 * math.cos(a), 8 + 3.0 * math.sin(a), 0.0), (8 + 2.0 * math.cos(a), 8 + 2.0 * math.sin(a), 8.0),
            0.35, "bronze")
    revolve(m, 8, 8, 8.0, 10.5, lambda t: 2.4 + 1.2 * t, "bronze", tone=0.2)
    fill(m, (5, 11, 5, 11, 10.0, 11.0), "ember", lambda X, Y, Z: np.hypot(X - 8, Y - 8) < 3.0)
    ellipsoid(m, (8, 8, 12.0), (1.6, 1.6, 2.0), "fire", tone=0.3)
    halo(m, 8, 8, 12.0, 12.0, FIRE, 1.0)
    return m


def g_lamp(v, frame, frames, k):
    """A lampstand in the street (it stands free in streets and squares, so it reads from every
    side, V7-002): a stepped stone base, a slender stone shaft and a dish on top holding a clay
    oil lamp with its little flame."""
    m = _m(1, 1, 14, k)
    slab(m, 5.5, 10.5, 5.5, 10.5, 0.0, 1.0, "poros", tone=0.2)
    slab(m, 6.5, 9.5, 6.5, 9.5, 1.0, 1.8, "poros", tone=0.3)
    revolve(m, 8.0, 8.0, 1.8, 9.0, lambda t: 0.75 - 0.15 * t, "poros", tone=0.25)
    revolve(m, 8.0, 8.0, 9.0, 9.8, lambda t: 0.8 + 1.0 * t, "poros", tone=0.35)
    ellipsoid(m, (8.0, 8.0, 10.2), (1.4, 0.9, 0.5), "clay", tone=0.2)
    fill(m, (8.6, 9.6, 7.6, 8.4, 10.4, 11.8), "lamp")
    halo(m, 9.1, 8.0, 11.2, 9.0, LAMP, 0.8)
    return m


def g_couch(v, frame, frames, k):
    """A dining couch (kline) for the andron with a low table before it, cushions and a cup."""
    m = _m(2, 1, 12, k)
    slab(m, 2.0, 30.0, 6.0, 14.0, 4.0, 5.2, "wood", tone=M.timber("x", 780))
    for x in (3.0, 29.0):
        for y in (7.0, 13.0):
            slab(m, x - 0.6, x + 0.6, y - 0.6, y + 0.6, 0.0, 4.0, "wood", tone=0.0)
    slab(m, 2.0, 30.0, 6.0, 14.0, 5.2, 6.6, "linen", tone=lambda X, Y, Z: 0.2 * ((X % 6.0) < 1.0))
    ellipsoid(m, (4.0, 10.0, 7.4), (2.0, 3.0, 1.2), "cinnabar", tone=0.2)
    slab(m, 8.0, 24.0, 1.0, 5.0, 0.0, 3.0, "wood_light", tone=0.1)
    vase(m, 15.0, 3.0, 3.0, 2.4, "krater", figure="redfigure")
    return m


def _connect(m, mask, h, t, kind):
    """Draw a connect-layout wall tile: N (-y) = 1, E (+x) = 2, S (+y) = 4, W (-x) = 8."""
    sel = []
    if mask & 1:
        sel.append((8 - t, 8 + t, -0.01, 8 + t))
    if mask & 4:
        sel.append((8 - t, 8 + t, 8 - t, 16.01))
    if mask & 8:
        sel.append((-0.01, 8 + t, 8 - t, 8 + t))
    if mask & 2:
        sel.append((8 - t, 16.01, 8 - t, 8 + t))
    if not sel:
        sel.append((8 - t, 8 + t, 8 - t, 8 + t))
    for x0, x1, y0, y1 in sel:
        city_wall(m, x0, x1, y0, y1, 0.0, h, seed=800 if kind == "city" else 810, merlons=kind == "city",
                  grave_reuse=False)


def g_wall(v, frame, frames, k):
    """The Themistoclean city wall: a stone socle, a whitewashed mudbrick curtain, crenellations."""
    m = _m(1, 1, 40, k)
    _connect(m, int(v[1:]) if isinstance(v, str) else v, 32.0, 4.5, "city")
    return m


def g_long_wall(v, frame, frames, k):
    """A Long Wall segment: lower and plainer than the city wall, crenellated."""
    m = _m(1, 1, 34, k)
    _connect(m, int(v[1:]) if isinstance(v, str) else v, 26.0, 3.5, "city")
    return m


def g_wall_tower(v, frame, frames, k):
    """A wall tower with a tiled pyramid roof, small windows, a torch at night."""
    from greek import hip_roof
    m = _m(2, 2, 56, k)
    city_wall(m, 2.0, 30.0, 2.0, 30.0, 0.0, 44.0, seed=820, merlons=False)
    for s in (10.0, 20.0):
        fill(m, (s - 1.0, s + 1.0, 29.6, 30.4, 34.0, 38.0), "ink", tone=0.0)
        fill(m, (29.6, 30.4, s - 1.0, s + 1.0, 34.0, 38.0), "ink", tone=0.0)
    slab(m, 1.0, 31.0, 1.0, 31.0, 44.0, 45.2, "poros", tone=0.3)
    hip_roof(m, 0.0, 32.0, 0.0, 32.0, 45.2, 9.0, material="terracotta", seed=821)
    rod(m, (24.0, 31.0, 24.0), (24.0, 32.5, 27.0), 0.4, "bronze")
    ellipsoid(m, (24.0, 32.8, 28.0), (0.8, 0.8, 1.2), "fire", tone=0.3)
    halo(m, 24.0, 32.8, 28.0, 10.0, FIRE, 0.8)
    return m


def g_wall_gate(v, frame, frames, k):
    """A small gate in the city wall, one wall tile wide (the wall runs along y): the curtain
    raised a little over a passage under a timber lintel, wooden leaves standing open against
    the jambs. It goes between wall towers or wall tiles; the passage stays clear for 1.5 tile
    heights, so walkers pass through (the item is walkable)."""
    m = _m(1, 1, 44, k)
    city_wall(m, 3.0, 13.0, -0.01, 16.01, 0.0, 36.0, seed=830, merlons=True)
    carve(m, (2.0, 14.0, 1.4, 14.6, 0.0, 25.0))
    slab(m, 2.4, 13.6, 1.0, 15.0, 25.0, 26.6, "wood", tone=M.timber("y", 832))
    for y0 in (1.4, 14.0):
        slab(m, 3.0, 9.5, y0, y0 + 0.6, 0.0, 24.0, "wood", tone=M.timber("x", 833))
    return m


def g_running_track(v, frame, frames, k):
    """A stone start sill of the gymnasium track with its grooves and a turning post."""
    m = _m(1, 1, 10, k)
    slab(m, 1.0, 15.0, 6.0, 10.0, 0.0, 0.8, "marble", tone=lambda X, Y, Z: -0.6 * (np.abs(Y - 8.0) < 0.3))
    slab(m, 7.0, 9.0, 1.0, 3.0, 0.0, 8.0, "marble", tone=0.2)
    return m


def g_fountain(v, frame, frames, k):
    """A neighbourhood fountain house: a small Doric porch on two columns before a basin, water
    from a bronze lion's head, a step worn by hydriai."""
    from greek import Order, column
    from arch import Scale
    m = _m(2, 2, 36, k)
    house_wall(m, 0.0, 14.0, 0.0, 32.0, 0.0, 24.0, 840, socle=4.0, plaster="whitewash")
    small = Order("doric", D=0.5, H=4.0, upper=0.8, material="poros")
    for y in (6.0, 26.0):
        column(m, 26.0, y, 0.0, small, Scale(1.0))
    slab(m, 12.0, 29.0, 2.0, 30.0, 20.0, 24.0, "poros", tone=M.ashlar(4.0, 30.0, 841, spread=0.3))
    tiled_roof(m, -1.5, 30.0, -1.5, 33.5, 24.0, 6.0, axis="x", material="terracotta", seed=842)
    slab(m, 14.0, 22.0, 4.0, 28.0, 0.0, 3.0, "poros", tone=0.2)
    carve(m, (15.0, 21.0, 5.0, 27.0, 2.4, 3.1))
    ellipsoid(m, (14.6, 16.0, 10.0), (0.9, 1.2, 1.2), "bronze_cast", tone=0.3)
    land = waterworks.stream(m, (15.4, 16.0, 9.4), (2.2, 0.0), 2.4, frame, frames, r=0.5, seed=845)
    waterworks.surface(m, (15.0, 21.0, 5.0, 27.0), 2.4, frame, frames, sources=[land], seed=846)
    return m


def g_workshop(v, frame, frames, k):
    """A potter's workshop yard in the Kerameikos: a roofed work room open on one side with the
    wheel, shelves of drying pots, a clay-settling tank, the kiln in the yard."""
    m = _m(2, 2, 36, k)
    seed = 860
    house_wall(m, 0.0, 14.0, 0.0, 32.0, 0.0, 20.0, seed, socle=3.0, plaster="mudbrick")
    for y in (2.0, 16.0, 30.0):
        rod(m, (13.5, y, 0.0), (13.5, y, 19.0), 0.6, "wood")
    tiled_roof(m, -1.5, 16.0, -1.5, 33.5, 20.0, 4.0, axis="y", material="terracotta", kind="laconian", seed=seed + 1)
    for i in range(2):     # shelves of drying pots inside the work room
        slab(m, 1.0, 3.0, 4.0, 28.0, 6.0 + i * 5.0, 6.6 + i * 5.0, "wood", tone=0.0)
        for j in range(6):
            vase(m, 2.0, 6.0 + j * 4.0, 6.6 + i * 5.0, 3.0, ("krater", "amphora", "hydria")[j % 3], figure="plain")
    revolve(m, 9.0, 12.0, 0.0, 3.0, lambda t: 1.0, "wood")
    fill(m, (5.0, 13.0, 8.0, 16.0, 3.0, 4.0), "wood_light", lambda X, Y, Z: np.hypot(X - 9, Y - 12) < 4.0, tone=0.2)
    slab(m, 18.0, 30.0, 2.0, 12.0, 0.0, 3.0, "poros", tone=0.2)                       # the settling tank
    fill(m, (19.0, 29.0, 3.0, 11.0, 1.0, 3.1), "clay", tone=-0.2)
    revolve(m, 24.0, 24.0, 0, 16.0, lambda t: 6.0 * np.sqrt(np.clip(1 - t ** 1.6, 0, 1)) + 0.6, "clay",
            tone=lambda X, Y, Z: -0.9 * (Z > 12))
    fill(m, (22.0, 26.0, 28.0, 31.0, 1.0, 5.0), "ember")
    halo(m, 24.0, 30.0, 3.0, 9.0, FIRE, 0.8)
    return m


def g_farmstead(v, frame, frames, k):
    """An Attic farmstead outside the walls: a stone house with a tower room (as Attic farms had
    for storage and safety), a walled yard with a pen, an olive, beehives of clay."""
    from greek import hip_roof
    m = _m(3, 3, 52, k)
    seed = 880
    house_wall(m, 0.0, 20.0, 0.0, 30.0, 0.0, 20.0, seed, socle=6.0, plaster="mudbrick", socle_mat="attic_rock")
    tiled_roof(m, -1.5, 21.5, -1.5, 31.5, 20.0, 5.0, axis="y", material="terracotta", kind="laconian", seed=seed + 1)
    house_wall(m, 20.0, 34.0, 0.0, 14.0, 0.0, 38.0, seed + 2, socle=38.0, plaster="mudbrick", socle_mat="attic_rock")
    hip_roof(m, 19.0, 35.0, -1.0, 15.0, 38.0, 6.0, material="terracotta", seed=seed + 3)
    for w in ((20.0, 48.0, 45.0, 48.0), (45.0, 48.0, 14.0, 48.0), (0.0, 20.0, 45.0, 48.0)):
        house_wall(m, *w, 0.0, 8.0, seed + 4, socle=8.0, plaster="mudbrick", socle_mat="attic_rock")
    _door(m, "+y", (0.0, 20.0, 0.0, 30.0), 6.0, 6.0, 12.0)
    olive_tree(m, 32.0, 30.0, 0.0, h=18.0, seed=seed)
    for i in range(3):
        rod(m, (4.0 + i * 3.0, 40.0, 1.5), (4.0 + i * 3.0, 43.0, 1.5), 1.4, "clay", tone=0.2)
    return m


def stair_marble(v, frame, frames, k):
    """A marble stair of one level (16 px) rising toward -y across two tiles: four deep steps
    with lit nosings and shaded risers between poros cheek walls (QA4 V-A-005)."""
    m = _m(1, 2, 12, k)
    flight(m, 0.5, 15.5, 0.0, 32.0, 8.0, 4, "marble", tone=M.ashlar(2.0, 5.0, 591, spread=0.25), cheek_mat="poros")
    return m


def _item(fn, slots=None, emitters=None):
    return Item(fn, slots=slots or {}, emitters=emitters or {})


ITEMS = {f"athens.{n}": it for n, it in {
    "g_house": _item(g_house, {"door": [{"t": [1, 3], "face": "+y"}]}),
    "g_house_small": _item(g_house_small, {"door": [{"t": [0, 2], "face": "+y"}], "sell": [{"t": [0, 2], "face": "-y"}]}),
    "g_house_two": _item(g_house_two, {"door": [{"t": [0, 2], "face": "+y"}]}),
    "g_herm": _item(g_herm),
    "g_shrine": _item(g_shrine, {"pray": [{"t": [0, 1], "face": "-y"}]}, {"fire": (8.0, 8.0, 11.5)}),
    "g_stall": _item(g_stall, {"sell": [{"t": [0, -1], "face": "+y"}], "buy": [{"t": [1, 1], "face": "-y"}]}),
    "g_table_banker": _item(g_table_banker, {"work": [{"t": [0, -1], "face": "+y"}]}),
    "g_kiln": _item(g_kiln, {"stoke": [{"t": [0, 1], "face": "-y"}]}, {"smoke": (8.0, 8.0, 20.0)}),
    "g_wheel": _item(g_wheel, {"throw": [{"t": [0, 1], "face": "-y"}]}),
    "g_pots": _item(g_pots),
    "g_forge": _item(g_forge, {"work": [{"t": [1, 0], "face": "-x"}]}, {"smoke": (2.0, 13.0, 15.5)}),
    "g_loom": _item(g_loom, {"weave": [{"t": [1, 0], "face": "-x"}]}),
    "g_press": _item(g_press, {"work": [{"t": [1, 1], "face": "-y"}]}),
    "g_threshing": _item(g_threshing, {"work": [{"t": [1, 1]}, {"t": [2, 2]}]}),
    "g_well": _item(g_well, {"draw": [{"t": [1, 0], "face": "-x"}]}),
    "g_grave_stele": _item(g_grave_stele, {"mourn": [{"t": [0, 1], "face": "-y"}]}),
    "g_grave_mound": _item(g_grave_mound),
    "g_statue_base": _item(g_statue_base),
    "g_stele_inscr": _item(g_stele_inscr, {"read": [{"t": [0, 1], "face": "-y"}]}),
    "g_crane": _item(g_crane),
    "g_scaffold": _item(g_scaffold),
    "g_brazier": _item(g_brazier, {}, {"fire": (8.0, 8.0, 13.0)}),
    "g_lamp": _item(g_lamp),
    "g_couch": _item(g_couch, {"recline": [{"t": [0, 0], "face": "+y", "z": 12}]}),
    "g_wall": _item(g_wall),
    "g_long_wall": _item(g_long_wall),
    "g_wall_tower": _item(g_wall_tower, {}, {"torch": (24.0, 32.8, 29.0)}),
    "g_wall_gate": _item(g_wall_gate),
    "g_running_track": _item(g_running_track),
    "g_fountain": _item(g_fountain, {"fill": [{"t": [1, 2], "face": "-y"}]}),
    "g_workshop": _item(g_workshop, {"throw": [{"t": [1, 2], "face": "-y"}]}, {"smoke": (24.0, 24.0, 18.0)}),
    "g_farmstead": _item(g_farmstead, {"door": [{"t": [0, 3], "face": "+y"}]}),
    "stair_marble": _item(stair_marble),
}.items()}

# Looks the life data switches (living-world §2.5): drawn instead of the base layer.
STATES = {
    ("athens.g_kiln", "firing"): lambda v, f, n, k: g_kiln(v, f, n, k, firing=True),
    ("athens.g_stall", "open"): g_stall,
    ("athens.g_stall", "closed"): lambda v, f, n, k: g_stall(v, f, n, k, closed=True),
}

FRAMES = {"athens.g_wheel": 2, "athens.g_crane": 2, "athens.g_stall": 2, "athens.g_fountain": 3}
