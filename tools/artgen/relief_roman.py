"""Roman relief compositions on the posed 2D figures of `relief_greek` (rome.md §3.2, §6.1):
pediment groups (the Capitoline triad, Mars Ultor with the gods of Rome's origin, a generic
group of gods), the unrolled spiral band of Trajan's Column (legionaries marching and
building, the emperor addressing the army, battles with Dacians in their caps, boats on the
Danube, trees and camps), the two panels in the passage of the Arch of Titus (the spoils of
Jerusalem with the menorah carried through an arch; Titus in the triumphal chariot crowned by
Victory), a sacrifice procession for altars and friezes, and the women's crafts of the Forum of
Nerva. Marble is shown carved with restrained paint and bronze attachments, so figures read by
their light and shade first."""

from functools import lru_cache

import numpy as np

from relief_greek import Canvas, chariot, horse, person

MARBLE_COLS = {"flesh": "marble", "drape": "marble", "drape2": "marble", "hair2": "marble", "bronze": "bronze",
               "horse": "marble", "shield": "bronze", "trim": "gold", "tree": "marble", "gift": "gold", "cap": "marble"}


def cols(i=0, **over):
    """Carved marble with a hint of paint on the cloaks (alternating) and bronze weapons."""
    c = dict(MARBLE_COLS)
    c["drape2"] = ("cinnabar", "marble", "ochre", "marble")[i % 4]
    c.update(over)
    return c


@lru_cache(maxsize=None)
def pediment_image(width, height, subject="gods"):
    """A pediment group in a triangle `width` x `height` px: 'triad' (Jupiter enthroned between
    Juno and Minerva, the Capitolium), 'mars' (Mars Ultor between Venus and Fortuna, Romulus
    and Roma seated, the Palatine and the Tiber reclining in the corners), 'gods' (a seated god
    between standing and seated figures)."""
    cv = Canvas(width, height)
    cx = width / 2
    base = height - 1

    def room(x):
        return max(0.0, height * (1 - abs(x - cx) / (width / 2)) - 1.0)

    def fig(x, i, pose="stand", **kw):
        div = {"seated": 0.72, "kneel": 0.7, "recline": 0.42}.get(pose, 1.0)
        h = min(room(x) / div * 0.92, height * 0.95)
        if h >= 5:
            person(cv, x, base, h, pose=pose, colours=cols(i), **kw)

    if subject == "triad":
        fig(cx, 0, "seated", facing=1, dress="himation", beard=True, held=("staff",))
        fig(cx - width * 0.11, 1, "seated", facing=1, dress="peplos", head="veil", held=("staff",))
        fig(cx + width * 0.11, 2, "seated", facing=-1, dress="peplos", head="helmet", held=("spear", "shield"))
        for side in (-1, 1):
            xx = cx + side * width * 0.27
            hh = room(xx) * 0.5
            if hh > 4:
                chariot(cv, xx, base, hh, facing=-side, colours=cols(3), driver=dict(dress="long", height=hh * 1.5),
                        pose="gallop")
            fig(cx + side * width * 0.43, 1, "recline", facing=side, dress="himation", beard=True)
    elif subject == "mars":
        fig(cx, 0, "stand", facing=1, dress="chiton", head="helmet", held=("spear", "shield"), beard=True)
        fig(cx - width * 0.09, 1, "stand", facing=1, dress="peplos", held=())
        fig(cx + width * 0.09, 2, "stand", facing=-1, dress="peplos", held=("staff",))
        fig(cx - width * 0.2, 3, "seated", facing=1, dress="chiton", beard=False, held=("staff",))
        fig(cx + width * 0.2, 1, "seated", facing=-1, dress="peplos", head="helmet", held=("spear",))
        fig(cx - width * 0.42, 0, "recline", facing=-1, dress="himation")
        fig(cx + width * 0.42, 2, "recline", facing=1, dress="himation", beard=True)
    elif subject == "eagle":     # an eagle with spread wings in a wreath with ribbons (bronze)
        c = {"bronze": "bronze_cast", "tree": "bronze_cast", "trim": "gold"}
        r = min(height * 0.42, width * 0.1)
        cy = base - height * 0.45
        for k_ in range(28):
            a = k_ / 28 * 2 * np.pi
            cv.disc((cx + np.cos(a) * r, cy + np.sin(a) * r * 0.9), max(0.8, r * 0.16), "E", c)
        for sgn in (-1, 1):
            cv.poly([(cx, cy), (cx + sgn * r * 0.9, cy - r * 0.6), (cx + sgn * r * 0.7, cy + r * 0.1)], "E", c)
            cv.capsule((cx + sgn * r * 1.05, cy + r * 0.8), (cx + sgn * width * 0.28, base - 1), max(0.6, r * 0.08),
                       "G", c)
        cv.disc((cx, cy - r * 0.3), max(1.0, r * 0.18), "E", c)
    else:
        fig(cx, 0, "seated", facing=1, dress="himation", beard=True, held=("staff",))
        for side in (-1, 1):
            fig(cx + side * width * 0.13, 1 + side, "stand", facing=-side, dress="peplos")
            fig(cx + side * width * 0.28, 2, "seated", facing=-side, dress="himation")
            fig(cx + side * width * 0.42, 3, "recline", facing=side, dress="himation", beard=side > 0)
    return cv.pair()


@lru_cache(maxsize=None)
def spiral_image(width, height, seed=0):
    """The unrolled band of Trajan's Column, `height` px tall: scenes in turn of legionaries
    marching behind standards, building a camp wall, the emperor addressing the army from a
    platform, battle with Dacians (caps, long trousers, oblong shields), a boat on the river,
    trees dividing the scenes."""
    cv = Canvas(width, height)
    base = height - 1
    H = height * 0.95
    rng = np.random.Generator(np.random.PCG64([seed, 113]))
    x = 2.0
    scene = 0
    while x < width - 4:
        kind = ("march", "build", "speech", "battle", "boat", "march", "battle")[scene % 7]
        if kind == "march":
            for i in range(5):
                person(cv, x, base, H, pose="walk", facing=1, dress="chiton", head="helmet",
                       held=("shield",) if i % 2 else ("spear", "shield"), colours=cols(i))
                x += H * 0.42
        elif kind == "build":
            cv.poly([(x, base), (x + H * 1.8, base), (x + H * 1.8, base - H * 0.45), (x, base - H * 0.45)], "U",
                    cols(0), stripe=(3, "u"))
            for i in range(3):
                person(cv, x + H * (0.3 + i * 0.6), base - H * 0.1, H * 0.9, pose="carry", facing=1, dress="chiton",
                       held=("tray",), colours=cols(i))
            x += H * 2.2
        elif kind == "speech":
            cv.poly([(x, base), (x + H * 0.6, base), (x + H * 0.6, base - H * 0.25), (x, base - H * 0.25)], "U",
                    cols(1))
            person(cv, x + H * 0.3, base - H * 0.25, H * 0.8, pose="stand", facing=1, dress="himation", beard=False,
                   cloak=True, colours=cols(2, drape2="purple"))
            x += H * 0.8
            for i in range(3):
                person(cv, x, base, H, pose="stand", facing=-1, dress="chiton", head="helmet", held=("spear",),
                       colours=cols(i))
                x += H * 0.35
        elif kind == "battle":
            for i in range(4):
                pose = ("lunge", "stride", "recoil", "fallen")[int(rng.integers(0, 4))]
                dacian = i % 2 == 1
                person(cv, x, base, H, pose=pose, facing=-1 if dacian else 1, dress="chiton",
                       head="pilos" if dacian else "helmet", beard=dacian,
                       held=("sword", "shield") if not dacian else ("sword",), colours=cols(i))
                x += H * 0.45
        elif kind == "boat":
            cv.poly([(x, base - H * 0.12), (x + H * 1.4, base - H * 0.12), (x + H * 1.2, base), (x + H * 0.2, base)],
                    "P", cols(0))
            for i in range(2):
                person(cv, x + H * (0.4 + i * 0.5), base - H * 0.12, H * 0.8, pose="stand", facing=1, dress="chiton",
                       head="helmet", held=("spear",), colours=cols(i))
            x += H * 1.6
        # A tree between scenes.
        cv.capsule((x + 1, base), (x + 1, base - H * 0.6), max(0.5, H * 0.05), "P", cols(0))
        cv.disc((x + 1, base - H * 0.75), max(1.0, H * 0.2), "T", cols(0), ry=max(1.0, H * 0.16))
        x += H * 0.4
        scene += 1
    return cv.pair()


@lru_cache(maxsize=None)
def spoils_image(width, height):
    """The spoils of Jerusalem (the south panel in the Arch of Titus's passage): wreathed men
    carrying the seven-branched lampstand on a litter, the table and the trumpets, placards on
    poles, moving toward an arch at the right."""
    cv = Canvas(width, height)
    base = height - 1
    H = height * 0.8
    x = 2.0
    i = 0
    while x < width - H * 0.9:
        if i % 5 == 2:          # the menorah on its litter
            for d in (-0.2, 0.2):
                person(cv, x + d * H, base, H, pose="walk", facing=1, dress="chiton", head="wreath", colours=cols(i))
            mx, my = x, base - H * 0.95
            cv.capsule((mx - H * 0.4, my + H * 0.05), (mx + H * 0.4, my + H * 0.05), max(0.6, H * 0.03), "P", cols(i))
            cv.capsule((mx, my), (mx, my - H * 0.42), max(0.6, H * 0.025), "G", cols(i))
            for k_ in (1, 2, 3):
                r = H * 0.07 * k_
                for sgn in (-1, 1):
                    cv.capsule((mx, my - H * 0.12), (mx + sgn * r, my - H * 0.12), max(0.5, H * 0.015), "G", cols(i))
                    cv.capsule((mx + sgn * r, my - H * 0.12), (mx + sgn * r, my - H * 0.42), max(0.5, H * 0.02), "G",
                               cols(i))
            x += H * 0.7
        elif i % 5 == 4:        # a placard on a pole
            person(cv, x, base, H, pose="walk", facing=1, dress="chiton", head="wreath", held=("staff",), colours=cols(i))
            cv.poly([(x + H * 0.0, base - H * 1.25), (x + H * 0.25, base - H * 1.25), (x + H * 0.25, base - H * 1.05),
                     (x, base - H * 1.05)], "W", cols(i))
            x += H * 0.4
        else:
            person(cv, x, base, H, pose="walk", facing=1, dress="himation" if i % 2 else "chiton", head="wreath",
                   held=("tray",) if i % 3 == 0 else (), colours=cols(i))
            x += H * 0.35
        i += 1
    ax = width - H * 0.7       # the arch they pass through
    cv.poly([(ax, base), (ax + H * 0.6, base), (ax + H * 0.6, base - H * 1.2), (ax, base - H * 1.2)], "U", cols(0))
    cv.disc((ax + H * 0.3, base - H * 0.5), H * 0.2, ".", None, ry=H * 0.45)
    return cv.pair()


@lru_cache(maxsize=None)
def triumph_image(width, height):
    """Titus in the four-horse chariot crowned by Victory, led by lictors with fasces and a
    personification of Rome (the north panel)."""
    cv = Canvas(width, height)
    base = height - 1
    H = height * 0.8
    x = 3.0
    for i in range(3):
        person(cv, x, base, H, pose="walk", facing=1, dress="himation", head="wreath", held=("staff",), colours=cols(i))
        x += H * 0.33
    chariot(cv, x + H * 0.35, base, H * 0.55, facing=1, colours=cols(1, horse="marble"),
            driver=dict(dress="himation", height=H * 0.9))
    person(cv, x + H * 0.0, base - H * 0.35, H * 0.85, pose="stride", facing=1, dress="peplos", colours=cols(2))
    x += H * 1.6
    while x < width - 3:
        person(cv, x, base, H, pose="walk", facing=1, dress="chiton", head="wreath", held=("staff",), colours=cols(3))
        x += H * 0.35
    return cv.pair()


@lru_cache(maxsize=None)
def sacrifice_image(width, height):
    """A sacrifice: a priest with covered head at an altar, a flute player, attendants leading
    a bull, a pig and a sheep (suovetaurilia)."""
    cv = Canvas(width, height)
    base = height - 1
    H = height * 0.9
    x = 2.0
    i = 0
    while x < width - 4:
        if i % 4 == 0:
            cv.poly([(x, base), (x + H * 0.25, base), (x + H * 0.25, base - H * 0.35), (x, base - H * 0.35)], "U", cols(0))
            x += H * 0.35
            person(cv, x, base, H, pose="stand", facing=-1, dress="himation", head="veil", colours=cols(1))
        elif i % 4 == 1:
            person(cv, x, base, H, pose="stand", facing=-1, dress="long", held=("aulos",), colours=cols(2))
        else:
            person(cv, x, base, H, pose="walk", facing=-1, dress="chiton", head="wreath", colours=cols(i))
            horse(cv, x + H * 0.35, base, H * (0.42 if i % 4 == 2 else 0.3), "walk", -1, "H", "h",
                  cols(i, horse="marble"))
            x += H * 0.4
        x += H * 0.38
        i += 1
    return cv.pair()


@lru_cache(maxsize=None)
def crafts_image(width, height):
    """Women spinning and weaving under Minerva (the frieze of the Forum of Nerva)."""
    cv = Canvas(width, height)
    base = height - 1
    H = height * 0.9
    x = 2.0
    i = 0
    while x < width - 4:
        pose = ("stand", "seated", "walk", "kneel")[i % 4]
        person(cv, x, base, H, pose=pose, facing=1 if i % 2 else -1, dress="peplos",
               head="helmet" if i % 9 == 4 else "bare", held=("basket",) if i % 3 == 0 else (), colours=cols(i))
        x += H * 0.42
        i += 1
    return cv.pair()
