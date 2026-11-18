"""Greek figured relief and painting as 2D stencils, posed instead of hand-drawn.

A Greek pediment, metope, frieze or painted panel is a crowd of figures in action: people
striding, fighting, reclining, riding, horses rearing, centaurs. Here a figure is a 2D puppet:
joints in a unit box (feet at y = 0, crown at y = 1, facing +x) joined by limbs of given
widths, with drapery shapes, helmets, shields and weapons, rasterised at any height into a
stencil of `relief.CODES` characters (far limbs in shade codes, so they read behind). The same
poses give the 12 px metopes, the 10 px riders of the Ionic frieze, the 30 px figures of a
temple pediment and the flat figures of a painted panel or a pot.

Compositions return (image, cmap) pairs for `relief.emboss`: `pediment_image`, `metope_image`,
`frieze_image`, `panel_image`. Reusable by every set with Greek or Roman figured work.
"""

import math
from functools import lru_cache

import numpy as np

import relief as R

# ---------------------------------------------------------------- poses

# Joints: (x, y) in figure units, height 1. Names: head, neck, sh (shoulder), el_n/el_f
# (near/far elbow), ha_n/ha_f (hands), hip, kn_n/kn_f, ft_n/ft_f.
POSES = {
    "stand": dict(head=(0.02, 0.93), neck=(0.0, 0.85), sh=(0.0, 0.8), el_n=(0.04, 0.62), ha_n=(0.06, 0.47),
                  el_f=(-0.04, 0.62), ha_f=(-0.05, 0.47), hip=(0.0, 0.5), kn_n=(0.02, 0.26), ft_n=(0.04, 0.0),
                  kn_f=(-0.02, 0.26), ft_f=(-0.05, 0.0)),
    "stride": dict(head=(0.08, 0.92), neck=(0.05, 0.84), sh=(0.04, 0.79), el_n=(0.18, 0.7), ha_n=(0.3, 0.74),
                   el_f=(-0.1, 0.66), ha_f=(-0.2, 0.56), hip=(0.0, 0.49), kn_n=(0.14, 0.27), ft_n=(0.26, 0.0),
                   kn_f=(-0.1, 0.25), ft_f=(-0.24, 0.02)),
    # Lunging with the near arm raised to strike (Tyrannicides, Lapiths, Athena and Poseidon).
    "lunge": dict(head=(0.12, 0.9), neck=(0.09, 0.82), sh=(0.07, 0.77), el_n=(0.0, 0.94), ha_n=(0.08, 1.08),
                  el_f=(0.24, 0.72), ha_f=(0.38, 0.7), hip=(0.0, 0.47), kn_n=(0.2, 0.28), ft_n=(0.34, 0.0),
                  kn_f=(-0.16, 0.22), ft_f=(-0.32, 0.0)),
    "recoil": dict(head=(-0.12, 0.88), neck=(-0.09, 0.8), sh=(-0.07, 0.75), el_n=(0.06, 0.82), ha_n=(0.2, 0.9),
                   el_f=(-0.22, 0.62), ha_f=(-0.3, 0.5), hip=(0.0, 0.46), kn_n=(0.14, 0.24), ft_n=(0.3, 0.0),
                   kn_f=(-0.12, 0.24), ft_f=(-0.2, 0.0)),
    "fallen": dict(head=(0.42, 0.24), neck=(0.34, 0.24), sh=(0.3, 0.23), el_n=(0.32, 0.4), ha_n=(0.4, 0.5),
                   el_f=(0.22, 0.1), ha_f=(0.3, 0.02), hip=(0.0, 0.14), kn_n=(-0.18, 0.24), ft_n=(-0.4, 0.04),
                   kn_f=(-0.2, 0.08), ft_f=(-0.42, 0.0)),
    "kneel": dict(head=(0.06, 0.7), neck=(0.04, 0.62), sh=(0.03, 0.58), el_n=(0.14, 0.46), ha_n=(0.22, 0.4),
                  el_f=(-0.06, 0.44), ha_f=(-0.02, 0.32), hip=(-0.04, 0.3), kn_n=(0.16, 0.16), ft_n=(0.18, 0.0),
                  kn_f=(-0.06, 0.02), ft_f=(-0.3, 0.02)),
    "seated": dict(head=(0.04, 0.72), neck=(0.02, 0.64), sh=(0.02, 0.6), el_n=(0.1, 0.46), ha_n=(0.2, 0.42),
                   el_f=(-0.06, 0.46), ha_f=(0.02, 0.36), hip=(-0.04, 0.32), kn_n=(0.18, 0.32), ft_n=(0.2, 0.0),
                   kn_f=(0.16, 0.3), ft_f=(0.14, 0.0)),
    # Reclining along the floor, propped on the far elbow (river gods in pediment corners).
    "recline": dict(head=(-0.36, 0.42), neck=(-0.3, 0.36), sh=(-0.26, 0.33), el_n=(-0.08, 0.3), ha_n=(0.04, 0.22),
                    el_f=(-0.34, 0.14), ha_f=(-0.26, 0.04), hip=(0.06, 0.14), kn_n=(0.3, 0.2), ft_n=(0.52, 0.03),
                    kn_f=(0.3, 0.07), ft_f=(0.5, 0.0)),
    "walk": dict(head=(0.04, 0.93), neck=(0.02, 0.85), sh=(0.02, 0.8), el_n=(0.08, 0.63), ha_n=(0.14, 0.5),
                 el_f=(-0.06, 0.63), ha_f=(-0.1, 0.5), hip=(0.0, 0.5), kn_n=(0.08, 0.26), ft_n=(0.14, 0.0),
                 kn_f=(-0.06, 0.26), ft_f=(-0.12, 0.0)),
    # Carrying on the head or shoulder: both hands up to the load (water-carriers, kanephoroi).
    "carry": dict(head=(0.03, 0.9), neck=(0.02, 0.83), sh=(0.02, 0.79), el_n=(0.1, 0.9), ha_n=(0.06, 1.0),
                  el_f=(-0.08, 0.66), ha_f=(-0.06, 0.52), hip=(0.0, 0.5), kn_n=(0.06, 0.26), ft_n=(0.1, 0.0),
                  kn_f=(-0.05, 0.26), ft_f=(-0.1, 0.0)),
    "rider": dict(head=(0.04, 0.95), neck=(0.02, 0.87), sh=(0.01, 0.82), el_n=(0.12, 0.7), ha_n=(0.24, 0.68),
                  el_f=(0.08, 0.68), ha_f=(0.2, 0.66), hip=(-0.02, 0.52), kn_n=(0.14, 0.42), ft_n=(0.1, 0.18),
                  kn_f=(0.12, 0.42), ft_f=(0.08, 0.2)),
}


def _lerp_pose(a, b, t):
    return {k: (a[k][0] * (1 - t) + b[k][0] * t, a[k][1] * (1 - t) + b[k][1] * t) for k in a}


class Canvas:
    """A code grid with painter's order (later strokes cover earlier ones) and per-pixel
    colour slots, so one image carries many dresses."""

    def __init__(self, w, h):
        self.img = R.image(w, h)
        self.cmap = {}

    @property
    def w(self):
        return self.img.shape[1]

    @property
    def h(self):
        return self.img.shape[0]

    def plot(self, x, y, ch, colours=None):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < self.w and 0 <= yi < self.h:
            self.img[yi, xi] = ch
            if colours:
                self.cmap[(yi, xi)] = colours
            else:
                self.cmap.pop((yi, xi), None)

    def capsule(self, p, q, r, ch, colours=None):
        (x0, y0), (x1, y1) = p, q
        lo_x, hi_x = int(math.floor(min(x0, x1) - r)), int(math.ceil(max(x0, x1) + r))
        lo_y, hi_y = int(math.floor(min(y0, y1) - r)), int(math.ceil(max(y0, y1) + r))
        dx, dy = x1 - x0, y1 - y0
        dd = dx * dx + dy * dy or 1e-6
        rr = max(r, 0.5) ** 2
        for yy in range(max(lo_y, 0), min(hi_y + 1, self.h)):
            for xx in range(max(lo_x, 0), min(hi_x + 1, self.w)):
                t = min(max(((xx - x0) * dx + (yy - y0) * dy) / dd, 0.0), 1.0)
                ex, ey = xx - (x0 + t * dx), yy - (y0 + t * dy)
                if ex * ex + ey * ey <= rr:
                    self.plot(xx, yy, ch, colours)

    def disc(self, c, r, ch, colours=None, ry=None):
        cx, cy = c
        ry = ry or r
        for yy in range(int(cy - ry - 1), int(cy + ry + 2)):
            for xx in range(int(cx - r - 1), int(cx + r + 2)):
                if ((xx - cx) / max(r, 0.5)) ** 2 + ((yy - cy) / max(ry, 0.5)) ** 2 <= 1.0:
                    self.plot(xx, yy, ch, colours)

    def poly(self, pts, ch, colours=None, stripe=None):
        """A filled polygon; `stripe` = (period, ch2) draws vertical fold lines in ch2."""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        for yy in range(max(int(min(ys)), 0), min(int(max(ys)) + 1, self.h)):
            for xx in range(max(int(min(xs)), 0), min(int(max(xs)) + 1, self.w)):
                if _inside(xx + 0.0, yy + 0.0, pts):
                    c = ch
                    if stripe and (xx % stripe[0]) == 0:
                        c = stripe[1]
                    self.plot(xx, yy, c, colours)

    def blit(self, other: "Canvas", ox, oy):
        for (yy, xx) in zip(*np.nonzero(other.img != ".")):
            tx, ty = xx + ox, yy + oy
            if 0 <= tx < self.w and 0 <= ty < self.h:
                self.img[ty, tx] = other.img[yy, xx]
                c = other.cmap.get((yy, xx))
                if c:
                    self.cmap[(ty, tx)] = c
                else:
                    self.cmap.pop((ty, tx), None)

    def mirrored(self) -> "Canvas":
        out = Canvas(self.w, self.h)
        out.img = self.img[:, ::-1].copy()
        out.cmap = {(y, self.w - 1 - x): v for (y, x), v in self.cmap.items()}
        return out

    def pair(self):
        return self.img, self.cmap


def _inside(x, y, pts):
    inside = False
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            xc = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < xc:
                inside = not inside
    return inside


# ---------------------------------------------------------------- people

def person(cv: Canvas, x, base, height, pose="stand", dress="chiton", facing=1, head="bare", held=(),
           colours=None, beard=False, nude=False, cloak=None, scale_w=1.0):
    """Draw one figure with its feet at (x, base) (pixel row of the ground line, y down), `height`
    px tall, facing +1 (right) or -1. `dress`: chiton (short), peplos (long, belted, overfold),
    himation (long mantle, diagonal folds), long (priest, musician), exomis, none. `head`: bare,
    helmet (crested Attic), corinthian, petasos, wreath, veil, pilos, phrygian. `held`: spear,
    trident, shield, sword, staff, branch, basket, hydria, tray, lyre, aulos, axe, club, torch,
    reins, olive."""
    P = POSES[pose] if isinstance(pose, str) else pose
    H = height
    w = max(1.0, H * 0.06 * scale_w)       # limb radius
    col = colours or {}

    def pt(name, dx=0.0, dy=0.0):
        jx, jy = P[name]
        return (x + facing * (jx + dx) * H, base - (jy + dy) * H)

    skin = "N"
    skin_far = "n"
    cl = col or None
    # Far limbs first, in shade.
    cv.capsule(pt("hip"), pt("kn_f"), w * 1.05, skin_far, cl)
    cv.capsule(pt("kn_f"), pt("ft_f"), w * 0.9, skin_far, cl)
    cv.capsule(pt("sh"), pt("el_f"), w * 0.9, skin_far if nude or dress in ("chiton", "exomis") else "u", cl)
    cv.capsule(pt("el_f"), pt("ha_f"), w * 0.8, skin_far, cl)
    if cloak:   # a short cloak (chlamys) flying behind from the shoulders
        sx, sy = pt("sh")
        cv.poly([(sx, sy), (sx - facing * H * 0.26, sy + H * 0.06), (sx - facing * H * 0.3, sy + H * 0.3),
                 (sx - facing * H * 0.05, sy + H * 0.22)], "I", cl)
    if "shield" in held:        # the round shield on the far arm, seen from outside
        hx, hy = pt("el_f")
        cv.disc((hx + facing * H * 0.05, hy + H * 0.02), H * 0.13, "Z", cl)
        cv.disc((hx + facing * H * 0.05, hy + H * 0.02), H * 0.13 * 0.6, "z", cl)
    # Torso.
    shx, shy = pt("sh")
    hpx, hpy = pt("hip")
    tw = H * 0.085 * scale_w
    torso_ch = skin if nude or dress == "exomis" else "U"
    cv.poly([(shx - tw, shy), (shx + tw, shy), (hpx + tw * 0.9, hpy), (hpx - tw * 0.9, hpy)], torso_ch, cl)
    if dress == "exomis":   # one shoulder bare, the tunic from the far shoulder down
        cv.poly([(shx - facing * tw, shy), (hpx + tw, hpy + H * 0.02), (hpx - tw, hpy + H * 0.02)], "U", cl)
    # Near leg (under drapery for long dresses).
    cv.capsule(pt("hip"), pt("kn_n"), w * 1.1, skin, cl)
    cv.capsule(pt("kn_n"), pt("ft_n"), w * 0.95, skin, cl)
    # Drapery below the waist.
    if not nude and dress != "none":
        hem = {"chiton": 0.3, "exomis": 0.32, "peplos": 0.03, "himation": 0.06, "long": 0.02}.get(dress, 0.3)
        kx = (P["kn_n"][0] + P["kn_f"][0]) / 2
        fx_n, fx_f = P["ft_n"][0], P["ft_f"][0]
        spread = max(abs(fx_n - fx_f), 0.12)
        lo_y = base - hem * H
        left = x + facing * (min(fx_n, fx_f) - 0.03) * H if hem < 0.2 else x + facing * (kx - spread * 0.6) * H
        right = x + facing * (max(fx_n, fx_f) + 0.03) * H if hem < 0.2 else x + facing * (kx + spread * 0.6) * H
        if pose in ("seated", "kneel", "recline", "fallen", "rider"):
            # Drapery over the thighs to the knees.
            k = pt("kn_n")
            cv.capsule(pt("hip"), k, w * 1.8, "U", cl)
            if hem < 0.2 and pose == "seated":
                cv.poly([(k[0] - H * 0.06, k[1]), (k[0] + H * 0.08, k[1]), (k[0] + H * 0.06, base - H * 0.04),
                         (k[0] - H * 0.06, base - H * 0.04)], "U", cl, stripe=(2, "u"))
        else:
            cv.poly([(hpx - tw * 1.1, hpy), (hpx + tw * 1.1, hpy), (max(left, right), lo_y), (min(left, right), lo_y)],
                    "U", cl, stripe=(2 if H > 14 else 3, "u"))
        if dress == "peplos":   # the overfold (apoptygma) to the hips, belted
            cv.poly([(shx - tw * 1.2, shy + H * 0.02), (shx + tw * 1.2, shy + H * 0.02),
                     (hpx + tw * 1.25, hpy + H * 0.04), (hpx - tw * 1.25, hpy + H * 0.04)], "U", cl)
            cv.capsule((hpx - tw, hpy - H * 0.06), (hpx + tw, hpy - H * 0.06), max(0.5, H * 0.015), "u", cl)
        if dress == "himation":   # the mantle's diagonal from the far shoulder across the body
            cv.poly([(shx - facing * tw * 1.2, shy), (shx + facing * tw * 0.4, shy + H * 0.02),
                     (hpx + facing * tw * 1.3, hpy - H * 0.05), (hpx + facing * tw * 1.1, lo_y + H * 0.1),
                     (hpx - facing * tw * 1.3, lo_y + H * 0.2)], "I", cl, stripe=(3, "i"))
    # Near arm.
    cv.capsule(pt("sh"), pt("el_n"), w, skin if nude or dress in ("chiton", "exomis") else "U", cl)
    cv.capsule(pt("el_n"), pt("ha_n"), w * 0.85, skin, cl)
    # Head and hair.
    hx, hy = pt("head")
    hr = max(1.0, H * 0.07)
    cv.capsule(pt("neck"), (hx, hy), w * 0.8, skin, cl)
    cv.disc((hx, hy), hr, skin, cl)
    hair = "J"
    cv.disc((hx - facing * hr * 0.35, hy - hr * 0.35), hr * 0.85, hair, cl)
    if beard:
        cv.disc((hx + facing * hr * 0.35, hy + hr * 0.7), hr * 0.55, hair, cl)
    if head in ("helmet", "corinthian"):
        cv.disc((hx - facing * hr * 0.1, hy - hr * 0.25), hr * 1.1, "E", cl)
        cv.capsule((hx - facing * hr * 1.4, hy - hr * 1.0), (hx + facing * hr * 0.6, hy - hr * 2.0), max(0.6, hr * 0.5),
                   "B", cl)        # the crest
        if head == "corinthian":
            cv.capsule((hx + facing * hr * 0.6, hy), (hx + facing * hr * 0.7, hy + hr * 0.9), max(0.5, hr * 0.35),
                       "E", cl)
    elif head == "petasos":
        cv.capsule((hx - hr * 1.7, hy - hr * 0.6), (hx + hr * 1.7, hy - hr * 0.6), max(0.6, hr * 0.35), "I", cl)
        cv.disc((hx, hy - hr * 0.9), hr * 0.7, "I", cl)
    elif head == "wreath":
        cv.capsule((hx - hr, hy - hr * 0.5), (hx + hr, hy - hr * 0.5), max(0.5, hr * 0.3), "T", cl)
    elif head == "veil":
        cv.disc((hx - facing * hr * 0.25, hy - hr * 0.2), hr * 1.15, "I", cl)
        cv.disc((hx + facing * hr * 0.3, hy + hr * 0.1), hr * 0.62, skin, cl)
    elif head == "pilos":
        cv.poly([(hx - hr, hy - hr * 0.4), (hx + hr, hy - hr * 0.4), (hx, hy - hr * 2.3)], "I", cl)
    elif head == "phrygian":   # the soft Scythian or Amazon cap
        cv.disc((hx, hy - hr * 0.4), hr * 1.1, "I", cl)
        cv.capsule((hx, hy - hr * 1.2), (hx + facing * hr * 1.2, hy - hr * 1.6), max(0.5, hr * 0.45), "I", cl)
    # What they hold.
    hnx, hny = pt("ha_n")
    hfx, hfy = pt("ha_f")
    for h in held:
        if h in ("spear", "trident", "staff", "torch"):
            hx0, hy0 = (hnx, hny)
            top = (hx0 + facing * H * 0.12, hy0 - H * 0.55) if pose in ("lunge",) else (hx0 + facing * H * 0.02, hy0 - H * 0.6)
            bot = (hx0 - (top[0] - hx0) * 0.6, hy0 + (hy0 - top[1]) * 0.6)
            cv.capsule(bot, top, max(0.4, H * 0.012), "P" if h == "staff" else "E", cl)
            if h == "trident":
                for d in (-1, 0, 1):
                    cv.capsule((top[0] + d * H * 0.035, top[1] + H * 0.02), (top[0] + d * H * 0.04, top[1] - H * 0.07),
                               0.45, "E", cl)
            if h == "torch":
                cv.disc(top, max(1.0, H * 0.04), "G", cl)
        elif h in ("sword", "axe", "club"):
            tip = (hnx + facing * H * 0.12, hny - H * 0.2)
            cv.capsule((hnx, hny), tip, max(0.45, H * 0.018 * (2 if h == "club" else 1)), "E" if h != "club" else "P", cl)
            if h == "axe":
                cv.disc(tip, max(0.8, H * 0.04), "E", cl)
        elif h == "branch":
            cv.capsule((hnx, hny), (hnx + facing * H * 0.05, hny - H * 0.3), 0.45, "P", cl)
            for i in range(3):
                cv.disc((hnx + facing * H * (0.03 + 0.02 * i), hny - H * (0.15 + 0.07 * i)), max(0.6, H * 0.03), "T", cl)
        elif h in ("basket", "hydria", "tray"):
            top = pt("head", 0.0, 0.1)
            if h == "basket":
                cv.poly([(top[0] - H * 0.09, top[1] - H * 0.03), (top[0] + H * 0.09, top[1] - H * 0.03),
                         (top[0] + H * 0.06, top[1] + H * 0.04), (top[0] - H * 0.06, top[1] + H * 0.04)], "G", cl)
            elif h == "hydria":
                cv.disc((hnx, hny - H * 0.05), max(1.0, H * 0.07), "V", cl, ry=max(1.0, H * 0.08))
            else:
                cv.capsule((hnx - H * 0.08, hny - H * 0.02), (hnx + H * 0.08, hny - H * 0.02), max(0.5, H * 0.02), "V", cl)
        elif h == "lyre":
            cv.capsule((hfx, hfy), (hfx + facing * H * 0.02, hfy - H * 0.18), max(0.5, H * 0.02), "P", cl)
            cv.disc((hfx, hfy + H * 0.02), max(0.8, H * 0.05), "V", cl)
        elif h == "aulos":
            cv.capsule(pt("head", 0.05, -0.02), (hnx + facing * H * 0.05, hny), 0.45, "P", cl)
        elif h == "reins":
            cv.capsule((hnx, hny), (hnx + facing * H * 0.35, hny + H * 0.05), 0.4, "Q", cl)
        elif h == "olive":
            cv.disc((hnx + facing * H * 0.04, hny - H * 0.08), max(0.8, H * 0.06), "T", cl)


# ---------------------------------------------------------------- horses and centaurs

HORSE_POSES = {
    #             (front legs, hind legs, neck lift, body tilt)
    "walk": ((0.18, -0.12), (0.1, -0.1), 0.0, 0.0),
    "gallop": ((0.42, 0.25), (-0.3, -0.15), 0.1, 0.0),
    "rear": ((0.35, 0.5), (0.05, -0.05), 0.35, 0.45),
    "stand": ((0.02, -0.02), (0.02, -0.02), 0.0, 0.0),
}


def horse(cv: Canvas, x, base, height, pose="walk", facing=1, ch="H", shade="h", colours=None, rider=None,
          centaur=None, mane="K"):
    """A horse `height` px to the withers... its body about 1.3 x height long, its hooves on
    `base`; `rider` = person kwargs to seat on it; `centaur` = person kwargs whose torso
    rises from the withers instead of a neck."""
    cl = colours or None
    fl, hl, lift, tilt = HORSE_POSES[pose]
    H = height
    L = H * 1.25
    body_y = base - H * 0.68
    # The body tilts up at the front when rearing (rotate about the hind quarters).
    ca, sa = math.cos(tilt), math.sin(tilt)

    def P(u, v):          # u along the body (+ forward), v up, relative to the hind quarters
        rx, ry = u * ca - v * sa, u * sa + v * ca
        return (x + facing * (rx - L * 0.45), body_y - ry)

    leg_r = max(0.6, H * 0.055)
    # Far legs (shade).
    for (u0, swing), far in ((((L * 0.82), fl[1]), True), (((L * 0.12), hl[1]), True)):
        top = P(u0, 0)
        foot = (top[0] + facing * swing * H, base if tilt == 0 or u0 < L * 0.5 else top[1] + H * 0.5)
        knee = ((top[0] + foot[0]) / 2 + facing * H * 0.06, (top[1] + foot[1]) / 2)
        cv.capsule(top, knee, leg_r, shade, cl)
        cv.capsule(knee, foot, leg_r * 0.8, shade, cl)
    # Body: barrel, chest, quarters.
    cv.capsule(P(L * 0.1, 0), P(L * 0.85, H * 0.04), H * 0.2, ch, cl)
    cv.disc(P(L * 0.12, H * 0.02), H * 0.21, ch, cl)
    cv.disc(P(L * 0.84, H * 0.03), H * 0.21, ch, cl)
    # Tail.
    tq = P(-L * 0.04, H * 0.08)
    cv.capsule(tq, (tq[0] - facing * H * 0.18, tq[1] + H * 0.35), max(0.6, H * 0.05), mane, cl)
    # Near legs.
    for u0, swing in ((L * 0.82, fl[0]), (L * 0.12, hl[0])):
        top = P(u0, 0)
        if tilt and u0 > L * 0.5:     # rearing: forelegs folded up in the air
            knee = (top[0] + facing * H * 0.2, top[1] + H * 0.12)
            foot = (knee[0] - facing * H * 0.05, knee[1] + H * 0.22)
        else:
            foot = (top[0] + facing * swing * H, base)
            knee = ((top[0] + foot[0]) / 2 + facing * H * 0.05, (top[1] + foot[1]) / 2)
        cv.capsule(top, knee, leg_r * 1.15, ch, cl)
        cv.capsule(knee, foot, leg_r * 0.85, ch, cl)
    if centaur:
        # The human torso rises from the withers.
        wx, wy = P(L * 0.86, H * 0.12)
        kw = dict(centaur)
        th = kw.pop("height", H * 1.1)
        person(cv, wx - facing * th * 0.0, wy + th * 0.5, th, facing=facing, nude=True, **kw)
        return
    # Neck and head.
    n0 = P(L * 0.86, H * 0.12)
    n1 = P(L * 1.05, H * (0.55 + lift))
    cv.capsule(n0, n1, H * 0.13, ch, cl)
    cv.capsule(n0, (n1[0] - facing * H * 0.05, n1[1] - H * 0.04), max(0.6, H * 0.05), mane, cl)
    head_end = (n1[0] + facing * H * 0.24, n1[1] + H * 0.16)
    cv.capsule(n1, head_end, H * 0.08, ch, cl)
    cv.plot(n1[0] - facing * H * 0.02, n1[1] - H * 0.1, ch, cl)      # ears
    if rider:
        kw = dict(rider)
        rh = kw.pop("height", H * 1.15)
        sx, sy = P(L * 0.55, H * 0.2)
        person(cv, sx, sy + rh * 0.52, rh, pose="rider", facing=facing, **kw)


def chariot(cv: Canvas, x, base, height, facing=1, colours=None, driver=None, pose="gallop"):
    """A two-wheeled chariot behind a pair of horses (the near and the far), the driver in a
    long chiton."""
    H = height
    cl = colours or None
    horse(cv, x + facing * H * 1.0, base - 1, H, pose, facing, "h", "h", cl)   # the far horse
    horse(cv, x + facing * H * 0.85, base, H, pose, facing, "H", "h", cl)
    wx = x - facing * H * 0.25
    cv.disc((wx, base - H * 0.32), H * 0.32, "P", cl)
    cv.disc((wx, base - H * 0.32), H * 0.22, ".", None)
    cv.capsule((wx - H * 0.05, base - H * 0.32), (wx + H * 0.05, base - H * 0.32), 0.5, "P", cl)
    cv.poly([(wx - facing * H * 0.15, base - H * 0.5), (wx + facing * H * 0.35, base - H * 0.5),
             (wx + facing * H * 0.3, base - H * 0.8), (wx - facing * H * 0.1, base - H * 0.75)], "B", cl)
    cv.capsule((wx + facing * H * 0.3, base - H * 0.55), (x + facing * H * 0.7, base - H * 0.75), 0.5, "P", cl)
    if driver:
        kw = dict(driver)
        dh = kw.pop("height", H * 1.5)
        person(cv, wx + facing * H * 0.05, base - H * 0.45, dh, pose="stand", facing=facing, held=("reins",), **kw)


def olive_tree(cv: Canvas, x, base, height, colours=None):
    """The olive Athena gave the city, gnarled, in the middle of the west pediment."""
    cl = colours or None
    H = height
    cv.capsule((x, base), (x - H * 0.06, base - H * 0.45), max(0.8, H * 0.05), "P", cl)
    cv.capsule((x - H * 0.06, base - H * 0.45), (x + H * 0.1, base - H * 0.7), max(0.6, H * 0.035), "P", cl)
    for cx, cy, r in ((0.0, 0.72, 0.18), (-0.14, 0.62, 0.14), (0.16, 0.66, 0.14), (0.05, 0.88, 0.12)):
        cv.disc((x + cx * H, base - cy * H), r * H, "T", cl, ry=r * H * 0.7)
        cv.disc((x + cx * H + 1, base - cy * H + 1), r * H * 0.5, "t", cl, ry=r * H * 0.35)


# ---------------------------------------------------------------- compositions

# Painted marble: skin a warm flesh tone, hair brown, dress in reds, blues, ochres, greens and
# violets with darker folds; bronze attachments gilded or brown.
DRESS = ("cinnabar", "eblue", "ochre", "malachite", "purple", "saffron", "lapis", "whitewash")


def dress_cols(i, flesh="marble", hair="cedar", horse="marble"):
    return {"flesh": flesh, "drape": DRESS[i % len(DRESS)], "drape2": DRESS[(i + 3) % len(DRESS)],
            "hair2": hair, "bronze": "gold", "horse": horse, "shield": "bronze", "trim": "gold", "tree": "olive",
            "gift": "bronze", "cap": "eblue"}  # the shield face: bronze rim, painted ground


@lru_cache(maxsize=None)
def pediment_image(width, height, subject="west"):
    """A pediment group filling a triangle `width` x `height` px (apex at the top centre):
    'west', Athena and Poseidon springing apart from the olive (Parthenon, in view); 'east',
    the birth of Athena; 'hephaisteion' (Theseus, by tradition); 'small' (a generic group for
    small temples). Figures shrink toward the corners as the slope comes down."""
    cv = Canvas(width, height)
    cx = width / 2
    base = height - 1

    def room(x):             # tympanum height above the floor at column x
        return max(0.0, height * (1 - abs(x - cx) / (width / 2)) - 1.0)

    def standing(x, i, **kw):
        h = min(room(x) * 0.95, height * 0.92)
        if h >= 5:
            person(cv, x, base, h, colours=dress_cols(i), **kw)
        return h

    if subject == "west":
        # Centre: the olive, Athena (left, moving left) and Poseidon (right) leaping apart.
        olive_tree(cv, cx, base, height * 0.9, dress_cols(0))
        standing(cx - width * 0.05, 2, pose="lunge", facing=-1, dress="peplos", head="helmet", held=("spear", "shield"))
        standing(cx + width * 0.055, 1, pose="lunge", facing=1, nude=True, beard=True, cloak=True, held=("trident",))
        # Behind each: a chariot with rearing horses (Nike drives Athena's, Amphitrite Poseidon's).
        for side, i in ((-1, 4), (1, 6)):
            xx = cx + side * width * 0.2
            hh = room(xx) * 0.5
            chariot(cv, xx, base, hh, facing=side, colours=dress_cols(i, horse="marble"),
                    driver=dict(dress="long", height=hh * 1.55), pose="rear")
        # Messengers, then the Attic heroes and their families, seated and kneeling.
        standing(cx - width * 0.31, 3, pose="stride", facing=1, dress="chiton", head="petasos", cloak=True)
        standing(cx + width * 0.31, 5, pose="stride", facing=-1, dress="peplos")
        for side in (-1, 1):
            for j, (u, pose) in enumerate(((0.36, "seated"), (0.4, "kneel"), (0.43, "seated"))):
                xx = cx + side * width * u
                h = room(xx) / (0.72 if pose == "seated" else 0.7) * 0.92
                if h >= 5:
                    person(cv, xx, base, h, pose=pose, facing=-side, dress="peplos" if j % 2 else "himation",
                           colours=dress_cols(j + (2 if side > 0 else 5)))
        # River gods recline in the corners.
        for side, i in ((-1, 1), (1, 7)):
            xx = cx + side * width * 0.465
            h = room(xx - side * width * 0.03) / 0.42 * 0.9
            person(cv, xx, base, max(h, 6), pose="recline", facing=side, dress="himation", beard=True,
                   colours=dress_cols(i))
    elif subject == "east":
        standing(cx - width * 0.03, 1, pose="seated", facing=1, dress="himation", beard=True)   # Zeus (seated tall)
        standing(cx + width * 0.05, 2, pose="stand", facing=-1, dress="peplos", head="helmet", held=("spear", "shield"))
        standing(cx - width * 0.12, 3, pose="recoil", facing=-1, nude=True, beard=True, held=("axe",))   # Hephaistos
        standing(cx + width * 0.14, 5, pose="stride", facing=1, dress="peplos")                       # Nike or Iris
        for side in (-1, 1):
            for j, u in enumerate((0.24, 0.3, 0.36)):
                xx = cx + side * width * u
                h = room(xx) / 0.72 * 0.92
                if h >= 5:
                    person(cv, xx, base, h, pose="seated", facing=side, dress="peplos" if j else "himation",
                           colours=dress_cols(j + 4))
        # Helios rising with his horses (left), Selene sinking (right): heads above the floor.
        for side, i in ((-1, 6), (1, 7)):
            xx = cx + side * width * 0.44
            h = room(xx) * 0.9
            for d in range(2):
                horse(cv, xx - side * d * h * 0.3, base + h * 0.35, h * 0.9, "stand", -side, "H", "h",
                      dress_cols(i))
    elif subject in ("hephaisteion", "gigantomachy"):
        for side in (-1, 1):
            for j, u in enumerate((0.04, 0.14, 0.26, 0.36)):
                xx = cx + side * width * u
                pose = ("lunge", "recoil", "kneel", "fallen")[j]
                h = room(xx) / (0.7 if pose == "kneel" else 0.3 if pose == "fallen" else 1.0) * 0.9
                if h >= 5:
                    person(cv, xx, base, min(h, height * 0.92), pose=pose, facing=-side if j else side,
                           nude=j % 2 == 0, dress="chiton", head="helmet" if j == 1 else "bare",
                           held=("sword",) if j == 0 else ("shield",) if j == 1 else (), colours=dress_cols(j + side))
    else:   # small: a central god between seated figures
        standing(cx, 2, pose="stand", facing=1, dress="peplos", head="helmet", held=("spear",))
        for side in (-1, 1):
            for j, u in enumerate((0.18, 0.32)):
                xx = cx + side * width * u
                h = room(xx) / 0.72 * 0.92
                if h >= 5:
                    person(cv, xx, base, h, pose="seated", facing=-side, dress="himation", colours=dress_cols(j + 3))
    return cv.pair()


METOPE_THEMES = {
    # Parthenon (bible §3.1): east gods v giants, west Greeks v Amazons, north the sack of Troy,
    # south Lapiths v centaurs. Hephaisteion: Herakles (east) and Theseus (flanks).
    "centaur": ("centaur", "lapith"),
    "amazon": ("amazon", "greek"),
    "giant": ("god", "giant"),
    "troy": ("greek", "trojan"),
    "herakles": ("herakles", "beast"),
    "theseus": ("theseus", "foe"),
}


@lru_cache(maxsize=None)
def metope_image(width, height, theme, i):
    """One metope (about 9 x 12 px at the Parthenon's scale): a pair in combat, varied by i."""
    cv = Canvas(width, height)
    base = height - 1
    H = height * 0.92
    v = i % 4
    c1, c2 = dress_cols(i), dress_cols(i + 3)
    left, right = width * 0.32, width * 0.7
    if theme == "centaur":
        horse(cv, right - width * 0.05, base, height * 0.45, "rear" if v % 2 else "gallop", -1, "H", "h", c2,
              centaur=dict(pose="lunge", beard=True, height=height * 0.55, colours=c2))
        person(cv, left, base, H * (0.85 if v != 3 else 0.6), pose=("lunge", "stride", "recoil", "kneel")[v], facing=1,
               nude=True, cloak=True, held=("sword",) if v != 2 else (), colours=c1)
    elif theme == "amazon":
        if v % 2:
            horse(cv, right, base, height * 0.5, "rear", -1, "H", "h", c2,
                  rider=dict(dress="chiton", head="phrygian", height=height * 0.5, colours=c2))
        else:
            person(cv, right, base, H, pose="recoil", facing=-1, dress="chiton", head="phrygian", held=("axe",),
                   colours=c2)
        person(cv, left, base, H, pose="lunge", facing=1, nude=True, head="helmet", held=("shield", "spear"), colours=c1)
    elif theme == "giant":
        person(cv, left, base, H, pose="lunge", facing=1, dress="peplos" if v % 2 else "chiton",
               head="helmet" if v == 1 else "bare", held=("spear",) if v != 2 else ("trident",), colours=c1)
        person(cv, right, base, H * (0.6 if v == 0 else 0.9), pose="kneel" if v == 0 else "recoil", facing=-1,
               nude=True, beard=True, held=("shield",), colours=c2)
    elif theme == "troy":
        person(cv, left, base, H, pose="stride" if v % 2 else "lunge", facing=1, head="helmet", dress="chiton",
               held=("spear", "shield"), colours=c1)
        person(cv, right, base, H, pose="recoil" if v != 2 else "stand", facing=-1, dress="peplos" if v == 2 else "chiton",
               colours=c2)
    elif theme in ("herakles", "theseus"):
        person(cv, left, base, H, pose="lunge", facing=1, nude=True, beard=theme == "herakles",
               held=("club",) if theme == "herakles" else ("sword",), colours=c1)
        if theme == "herakles" and v % 2:
            horse(cv, right, base, height * 0.42, "rear", -1, "H", "h", {**c2, "horse": "ochre"})
        else:
            person(cv, right, base, H * (0.7 if v == 1 else 0.95), pose="kneel" if v == 1 else "recoil", facing=-1,
                   nude=True, beard=True, colours=c2)
    return cv.pair()


@lru_cache(maxsize=None)
def frieze_image(width, height, subject="procession", seed=0):
    """A continuous Ionic frieze `height` px tall (the Parthenon's procession: horsemen,
    chariots, elders, water-carriers, sacrificial animals, girls)."""
    cv = Canvas(width, height)
    base = height - 1
    x = 2.0
    i = seed
    seq = ("rider", "rider", "rider", "chariot", "elder", "elder", "hydria", "heifer", "girl", "girl", "rider")
    while x < width - 4:
        what = seq[i % len(seq)]
        c = dress_cols(i)
        if what == "rider":
            horse(cv, x + height * 0.55, base, height * 0.55, "gallop" if i % 3 else "walk", 1, "H", "h",
                  {**c, "horse": "ochre" if i % 2 else "cedar"},
                  rider=dict(dress="chiton", cloak=True, head="petasos" if i % 4 == 0 else "bare", height=height * 0.6,
                             colours=c))
            x += height * 1.1
        elif what == "chariot":
            chariot(cv, x + height * 0.5, base, height * 0.5, 1, c, driver=dict(dress="long", height=height * 0.72))
            x += height * 1.5
        elif what == "heifer":
            person(cv, x + 2, base, height * 0.9, pose="walk", dress="himation", colours=c)
            horse(cv, x + height * 0.8, base, height * 0.42, "walk", 1, "H", "h", {**c, "horse": "whitewash"})
            x += height * 1.3
        else:
            person(cv, x + 2, base, height * 0.92, pose="carry" if what in ("hydria", "girl") and i % 2 else "walk",
                   dress="peplos" if what == "girl" else "himation", beard=what == "elder",
                   held=("hydria",) if what == "hydria" else ("branch",) if what == "elder" else (), colours=c)
            x += height * 0.45
        i += 1
    return cv.pair()


@lru_cache(maxsize=None)
def panel_image(width, height, subject="marathon"):
    """A large painted panel (Stoa Poikile: Marathon, the Amazons, Troy, Oinoe): rows of
    fighters over a painted landscape line, flat paint on a pale ground."""
    cv = Canvas(width, height)
    base = height - 2
    rng = np.random.Generator(np.random.PCG64([sum(map(ord, subject)), 5]))
    H = height * 0.55
    x = 3.0
    i = 0
    while x < width - 3:
        c = dress_cols(i)
        if subject == "amazons" and i % 3 == 1:
            horse(cv, x + H * 0.6, base, H * 0.55, "gallop", -1 if i % 2 else 1, "H", "h", {**c, "horse": "cedar"},
                  rider=dict(dress="chiton", head="phrygian", height=H * 0.55, colours=c))
            x += H * 1.2
            continue
        pose = ("lunge", "stride", "recoil", "fallen")[int(rng.integers(0, 4))]
        enemy = i % 2 == 1
        if subject == "marathon" and enemy:
            person(cv, x, base - rng.integers(0, 3), H, pose=pose, facing=-1, dress="chiton", head="phrygian",
                   held=("axe",), colours={**c, "drape": "saffron"})
        else:
            person(cv, x, base - rng.integers(0, 3), H, pose=pose, facing=1, dress="chiton", head="helmet",
                   held=("spear", "shield"), colours=c)
        x += H * (0.45 if pose != "fallen" else 0.6)
        i += 1
    return cv.pair()


@lru_cache(maxsize=None)
def stele_image(width, height, subject="farewell"):
    """A grave stele's relief: a seated woman and a standing figure clasping hands (the
    first Classical stelae, from about 430), or a standing youth."""
    cv = Canvas(width, height)
    base = height - 1
    if subject == "farewell":
        person(cv, width * 0.32, base, height * 0.95, pose="seated", facing=1, dress="himation", head="veil",
               colours=dress_cols(1))
        person(cv, width * 0.72, base, height * 0.92, pose="stand", facing=-1, dress="peplos", colours=dress_cols(4))
    else:
        person(cv, width * 0.5, base, height * 0.95, pose="stand", facing=1, nude=True, cloak=True, colours=dress_cols(2))
    return cv.pair()
