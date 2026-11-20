"""The application icon: the home corner in one small picture. Deterministic.

Usage: tools/artgen/build.sh --icon [--out DIR] [--check]

Every small size is its own drawing on its own pixel grid (16, 24, 32, 48, 64 and 128 are
drawn natively, simplified as they shrink; 16 and 24 are placed pixel by pixel); 256 and 512
are whole-number enlargements of the 128 drawing, so no size is ever resampled smoothly. The
picture is the home corner: a block of grassy land with Laeticia's red-roofed cottage (its
gable window lit) and a round tree, in the game's 2:1 projection and palette, drawn as polygons
in grid units (one unit is 2 px across and 1 px down, heights in px) filled at pixel centres,
so every edge is a clean two-pixel step, each object outlined in the palette's ink.

Writes assets/icon/icon-<size>.png and assets/icon/laeticias-corner.ico (16-64 as 32-bit
bitmaps, 256 as PNG, as Windows expects).
--check rebuilds everything in memory and fails if a committed file differs by one byte.
"""

import argparse
import io
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from palette import BLOSSOM, EARTH, GLOW, INK, LEAF, PALETTE, PLASTER, POPPY, ROOF, STONE, _rgb
from voxel import hash01

NATIVE = (16, 24, 32, 48, 64, 128)
ENLARGED = {256: 2, 512: 4}          # size: factor applied to the 128 drawing
ICO = (16, 24, 32, 48, 64, 256)
ROOT = Path(__file__).resolve().parents[2]
LIGHT = np.array([-0.55, -0.65, 0.52]) / np.linalg.norm([-0.55, -0.65, 0.52])  # upper left


def _c(h):
    return (*_rgb(h), 255)


class Layer:
    """One object of the picture, painted on its own and outlined when composited."""

    def __init__(self, n):
        self.n = n
        self.rgba = np.zeros((n, n, 4), np.uint8)
        self.ys, self.xs = np.mgrid[0:n, 0:n]

    def fill(self, mask, col):
        self.rgba[mask] = _c(col)

    def poly(self, pts, col, clip=None):
        """Fill the pixels whose centres lie inside the polygon (even-odd rule)."""
        x, y = self.xs + 0.5, self.ys + 0.5
        inside = np.zeros((self.n, self.n), bool)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if y0 != y1:
                inside ^= ((y0 <= y) != (y1 <= y)) & (x < x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        if clip is not None:
            inside &= clip
        self.fill(inside, col)
        return inside

    def rect(self, x0, y0, x1, y1, col):
        self.fill((self.xs >= x0) & (self.xs < x1) & (self.ys >= y0) & (self.ys < y1), col)

    def dot(self, x, y, col):
        if 0 <= x < self.n and 0 <= y < self.n:
            self.rgba[y, x] = _c(col)

    @property
    def mask(self):
        return self.rgba[..., 3] > 0


def _grow(m):
    o = m.copy()
    o[1:] |= m[:-1]
    o[:-1] |= m[1:]
    o[:, 1:] |= m[:, :-1]
    o[:, :-1] |= m[:, 1:]
    return o


def composite(n, layers):
    """Back to front; each layer first lays a one-pixel ink ring round itself, so objects stay
    apart where they overlap and the whole picture holds on any background."""
    out = np.zeros((n, n, 4), np.uint8)
    for lay in layers:
        m = lay.mask
        out[_grow(m) & ~m] = _c(INK)
        out[m] = lay.rgba[m]
    return out


def fit(img, n, margin):
    """Centre the drawing on an n x n canvas by a whole-pixel shift."""
    ys, xs = np.nonzero(img[..., 3])
    w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    if w > n - 2 * margin or h > n - 2 * margin:
        raise ValueError(f"{n}: the drawing is {w}x{h}, more than {n - 2 * margin} square")
    out = np.zeros((n, n, 4), np.uint8)
    ox, oy = (n - w) // 2, (n - h + 1) // 2
    out[oy:oy + h, ox:ox + w] = img[ys.min():ys.min() + h, xs.min():xs.min() + w]
    return out


def iso(cx, cy):
    """Grid units to pixels: +x runs down-right, +y down-left, z (px) up."""
    return lambda x, y, z=0: (cx + 2 * (x - y), cy + (x + y) - z)


def ground(n, P, G, H, d):
    """The corner of land: a grass diamond G units square on an earth block H px deep. `d` is
    the level of detail: 1 plain, 2 grass marks, 3 a darker foot under the earth."""
    o = Layer(n)
    top = o.poly([P(0, 0), P(G, 0), P(G, G), P(0, G)], LEAF[4])
    # The sides keep to the diamond's own columns, as the game's tiles do ([sx-hw+1, sx+hw-1)).
    under = np.broadcast_to(top.any(0), top.shape)
    lip = max(1, H // 3)
    foot = max(1, H // 4) if d >= 3 else 0
    for face, earth, grass, low in ((((0, G), (G, G)), EARTH[2], LEAF[3], EARTH[1]),
                                    (((G, 0), (G, G)), EARTH[1], LEAF[2], EARTH[0])):
        (ax, ay), (bx, by) = face
        o.poly([P(ax, ay), P(bx, by), P(bx, by, -H), P(ax, ay, -H)], earth, under)
        o.poly([P(ax, ay), P(bx, by), P(bx, by, -lip), P(ax, ay, -lip)], grass, under)
        if foot:
            o.poly([P(ax, ay, foot - H), P(bx, by, foot - H), P(bx, by, -H), P(ax, ay, -H)],
                   low, under)
    if d >= 2:
        # Grass marks: a light blade over a dark root, sparse and hashed, like the lawn tiles.
        ys, xs = np.nonzero(top)
        pick = hash01(xs, ys, 1) < (0.05 if d >= 3 else 0.035)
        for x, y in zip(xs[pick], ys[pick]):
            if y + 1 < n and top[y + 1, x] and (y - 1 < 0 or top[y - 1, x]):
                o.dot(x, y, LEAF[5])
                o.dot(x, y + 1, LEAF[3])
    return o, top


FACES = dict(front=PLASTER[3], side=PLASTER[2], roof=ROOF[3], course=ROOF[2], ridge=ROOF[4],
             fascia=ROOF[1], verge=ROOF[1], back=ROOF[0], post_f=EARTH[2], post_s=EARTH[1],
             plinth_f=STONE[3], plinth_s=STONE[2])


def house(n, P, h, d):
    """The cottage: ridge along x, the gable end at +x. `h` gives the box in grid units, the
    wall height and the roof's rise in px, the overhang (units), the roof's thickness (px), and
    the openings: `door` and `front_win` on the +y wall, `side_win` (lit) in the gable, and
    `flowers` at the wall's foot; `courses` spaces the tile rows. `d` as for the ground, and 4
    adds the joints between the tiles."""
    K = FACES
    o = Layer(n)
    x0, x1, y0, y1, wall, rise, over, tk = h["box"]
    ym = (y0 + y1) / 2
    top = wall + rise
    ye, yb = y1 + over, y0 - over
    rx0, rx1 = x0 - over, x1 + over

    def wy(y, a0, a1, z0, z1, col):
        return o.poly([P(a0, y, z0), P(a1, y, z0), P(a1, y, z1), P(a0, y, z1)], col)

    def wx(x, b0, b1, z0, z1, col):
        return o.poly([P(x, b0, z0), P(x, b1, z0), P(x, b1, z1), P(x, b0, z1)], col)

    wy(y1, x0, x1, 0, wall, K["front"])
    o.poly([P(x1, y0), P(x1, y1), P(x1, y1, wall), P(x1, ym, top), P(x1, y0, wall)], K["side"])
    if d >= 3:
        # Plinth, timber posts at the corners and the head beam, as the game's cottage has.
        pz = max(1, wall // 8)
        bz = max(1, wall // 10)
        wy(y1, x0, x1, 0, pz, K["plinth_f"])
        wx(x1, y0, y1, 0, pz, K["plinth_s"])
        wy(y1, x0, x1, wall - bz, wall, K["post_f"])
        wx(x1, y0, y1, wall - bz, wall, K["post_s"])
    if d >= 3 and wall >= 12:
        post = 0.5
        wy(y1, x0, x0 + post, pz, wall, K["post_f"])
        wy(y1, x1 - post, x1, pz, wall, K["post_f"])
        wx(x1, y1 - post, y1, pz, wall, K["post_s"])
        wx(x1, y0, y0 + post, pz, wall, K["post_s"])
    for a0, a1, z0, z1 in h.get("front_win", ()):
        if d >= 3:
            wy(y1, a0 - 0.5, a1 + 0.5, z0 - 1, z1 + 1, K["post_f"])
        wy(y1, a0, a1, z0, z1, GLOW[1])
        if d >= 3:
            wy(y1, a0, (a0 + a1) / 2, (z0 + z1) / 2, z1, GLOW[2])
    a0, a1, z1 = h["door"]
    if d >= 3:
        wy(y1, a0 - 0.5, a1 + 0.5, 0, z1 + 1, K["post_f"])
    wy(y1, a0, a1, 0, z1, EARTH[1])
    for b0, b1, z0, z1 in h["side_win"]:
        if d >= 3:
            wx(x1, b0 - 0.5, b1 + 0.5, z0 - 1, z1 + 1, K["post_s"])
        wx(x1, b0, b1, z0, z1, GLOW[1])
        if d >= 3:
            wx(x1, b0, (b0 + b1) / 2, (z0 + z1) / 2, z1, GLOW[2])
    for a, col in h.get("flowers", ()):
        # A clump at the wall's foot: leaves, then blooms on top.
        leaf = max(2, wall // 5)
        wy(y1 + 0.5, a - 0.5, a + 0.5, 0, leaf, LEAF[3])
        wy(y1 + 0.5, a - 0.5, a, leaf - 1, leaf + 1, col)
        wy(y1 + 0.5, a, a + 0.5, leaf, leaf + max(1, wall // 10) + 1, col)
    # The roof: the front plane runs from the ridge down to the eave at the wall's top; its
    # back plane faces away at this pitch, so behind the ridge only the verge shows.
    o.poly([P(rx0, ym, top), P(rx1, ym, top), P(rx1, ye, wall), P(rx0, ye, wall)], K["roof"])
    if h.get("courses"):
        step = h["courses"]
        dz = (top - wall) / (ye - ym)
        yy = ym + step
        while yy < ye - 0.25:
            zz = top - dz * (yy - ym)
            o.poly([P(rx0, yy - 0.5, zz + dz * 0.5), P(rx1, yy - 0.5, zz + dz * 0.5),
                    P(rx1, yy, zz), P(rx0, yy, zz)], K["course"])
            if d >= 4:
                # Joints between the tiles of the course above, staggered row by row.
                row = round((yy - ym) / step)
                a = rx0 + 1 + 0.5 * (row % 2)
                while a < rx1 - 0.5:
                    jx, jy = P(a, yy - step / 2, zz + dz * step / 2)
                    o.rect(int(jx), int(jy) - 1, int(jx) + 1, int(jy) + 2, K["course"])
                    a += 1.5
            yy += step
        o.poly([P(rx0, ym, top), P(rx1, ym, top), P(rx1, ym + 0.5, top - dz * 0.5),
                P(rx0, ym + 0.5, top - dz * 0.5)], K["ridge"])
    o.poly([P(rx0, ye, wall), P(rx1, ye, wall), P(rx1, ye, wall - tk), P(rx0, ye, wall - tk)],
           K["fascia"])
    o.poly([P(rx1, ym, top), P(rx1, ye, wall), P(rx1, ye, wall - tk), P(rx1, ym, top - tk)],
           K["verge"])
    o.poly([P(rx1, yb, wall), P(rx1, ym, top), P(rx1, ym, top - tk), P(rx1, yb, wall - tk)],
           K["back"])
    return o


def chimney(n, P, c, d):
    """Stone stack behind the ridge; from 48 px a cap band and the flue's dark mouth."""
    x0, x1, y0, y1, z0, z1 = c
    o = Layer(n)
    o.poly([P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], STONE[4])
    o.poly([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], STONE[2])
    o.poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], STONE[3])
    if d >= 3:
        cap = max(2, (z1 - z0) // 8)
        o.poly([P(x0, y1, z1 - cap - 1), P(x1, y1, z1 - cap - 1), P(x1, y1, z1 - cap),
                P(x0, y1, z1 - cap)], STONE[2])
        o.poly([P(x1, y0, z1 - cap - 1), P(x1, y1, z1 - cap - 1), P(x1, y1, z1 - cap),
                P(x1, y0, z1 - cap)], STONE[1])
        mx, my = (x1 - x0) / 4, (y1 - y0) / 4
        o.poly([P(x0 + mx, y0 + my, z1), P(x1 - mx, y0 + my, z1), P(x1 - mx, y1 - my, z1),
                P(x0 + mx, y1 - my, z1)], INK)
    return o


def tree(n, P, t, d):
    """A broadleaf like the game's oak: a short trunk under a crown of round clumps, each lit
    as its own puff; from 48 px up every clump is studded with small leaf clusters. `t` is the
    trunk's foot in grid units, its height and width in px, and the clumps as (dx, dy, r) px
    from the trunk's top."""
    gx, gy, th, tw, clumps = t
    bx, by = P(gx, gy)
    tx, ty0 = int(bx) - tw // 2, int(by) - th
    clumps = [(bx + dx, ty0 + dy, r) for dx, dy, r in clumps]
    o = Layer(n)
    o.rect(tx, ty0, tx + tw, int(by), EARTH[1])
    if tw >= 2:
        o.rect(tx, ty0, tx + tw // 2, int(by), EARTH[2])
    if d >= 3:
        o.rect(tx, ty0, tx + tw, ty0 + max(2, th // 4), EARTH[0])  # the crown's shade
    cols = (LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]) if d >= 3 else \
        (LEAF[2], LEAF[3], LEAF[4], LEAF[5])
    cuts = (-0.05, 0.2, 0.45, 0.68, 0.88) if d >= 3 else (0.12, 0.48, 0.8)
    x, y = o.xs + 0.5, o.ys + 0.5
    for i, (qx, qy, qr) in enumerate(clumps):
        dx, dy = (x - qx) / qr, (y - qy) / qr
        d2 = dx * dx + dy * dy
        b = dx * LIGHT[0] + dy * LIGHT[1] + np.sqrt(np.clip(1 - d2, 0, 1)) * LIGHT[2]
        inside = d2 <= 1.0
        if d >= 3:
            # Leaf clusters on a jittered lattice: each a small dome that bumps the light and
            # frays the clump's edge.
            cell = max(3.0, qr / 3.2)
            gx, gy = np.floor(x / cell), np.floor(y / cell)
            best = np.full(x.shape, 9.0)
            bump = np.zeros(x.shape)
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    cx = (gx + ox + 0.5 + (hash01(gx + ox, gy + oy, 3, i) - 0.5) * 0.8) * cell
                    cy = (gy + oy + 0.5 + (hash01(gx + ox, gy + oy, 3, i, 1) - 0.5) * 0.8) * cell
                    r = np.hypot(x - cx, y - cy) / (cell * 0.75)
                    near = r < best
                    best = np.where(near, r, best)
                    lx, ly = (x - cx) / (cell * 0.75), (y - cy) / (cell * 0.75)
                    bump = np.where(near, lx * LIGHT[0] + ly * LIGHT[1], bump)
            b = b + 0.35 * bump - 0.12 * (best > 0.85)
            inside = (d2 <= 1.0) & ~((d2 > 0.8) & (best > 0.9))
        idx = np.digitize(b, cuts)
        for k, c in enumerate(cols):
            o.fill(inside & (idx == k), c)
    return o


# ---- hand-placed pixels ----------------------------------------------------------------------

# At 16 and 24 px a drawing from polygons smears the cottage into the land: there the cottage
# and its tree are placed pixel by pixel over the land block the code draws ('.' keeps the
# block), the same picture as the larger sizes with one window, one door and one crown.
LEGEND = {"k": INK, "R": ROOF[3], "h": ROOF[4], "r": ROOF[1], "W": PLASTER[3], "w": PLASTER[2],
          "Y": GLOW[1], "y": GLOW[2], "b": EARTH[1], "o": EARTH[2], "S": STONE[4], "s": STONE[2],
          "G": LEAF[4], "g": LEAF[3], "d": LEAF[2], "D": LEAF[1], "l": LEAF[5], "L": LEAF[6]}
HAND = {
    16: (5, 4, 2, (
        "...........kkk..",
        "...kk.....kLLlk.",
        "..khhkk..klLlGgk",
        ".kRRRhhkkkllGgdk",
        ".kRRRRRhhkGGgddk",
        "kRRRRRRRRr.gddk.",
        "krrRRRRRRrw.bk..",
        "kWWrrRRRrwYkb...",
        ".WWbWrrRrwYkb...",
        ".ggbWWWrwwwkb...",
        "...ggWWWwwwg.G..",
        ".....ggWwwg.....",
        ".......gg.......",
    )),
    24: (8, 5.5, 2, (
        ".........kk......kkkk...",
        ".....kk.kSsk....klLLlk..",
        "....khhkkSsk...klLLlGgk.",
        "...kRRRhhSsk..kllLlGGgdk",
        "...kRRRRRhhkk.klllGGggdk",
        "..kRRRRRRRRhhkkGlGGggddk",
        "..kRRRRRRRRRRhkGGGggddDk",
        ".kRRRRRRRRRRRrwkgGggddk.",
        ".kRRRRRRRRRRRrwwkgddDk..",
        "krrRRRRRRRRRrwwwwkkobk..",
        "kWWrrRRRRRRRrwwwww.obk..",
        "kWWWWrrRRRRrwyYwwwkobk..",
        "kWWbbWWrrRRrwYYwwwkob...",
        ".WWbbWWWWrrwwYYwwwkob...",
        "...bbWWWWWWwwwwwwwgobg..",
        ".....WWWWWWwwwwwwg.gg...",
        ".......WWWWwwwwgg.......",
        ".........WWwwgg.........",
        "...........gg...........",
    )),
}


def hand(n):
    cy, G, H, rows = HAND[n]
    land, _ = ground(n, iso(n // 2, cy), G, H, 1)
    img = composite(n, [land])
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != ".":
                img[y, x] = _c(LEGEND[c])
    return fit(img, n, 0)


# ---- the picture ----------------------------------------------------------------------------

# The drawn sizes: margin (px), the land (G units, H px deep), detail, the cottage (see house),
# its chimney (box in units, z in px) and the tree (see tree).
SIZES = {
    32: dict(m=1, G=7, H=3, d=2,
             h=dict(box=(0, 4.5, 1, 5, 6, 6, 0.5, 1), door=(1.5, 2.5, 4),
                    side_win=[(2.5, 3.5, 2, 4)]),
             ch=(3, 4, 2, 3, 6, 15), tree=(5.5, 1, 5, 2, [(0, -4, 4.8)])),
    48: dict(m=3, G=10, H=4, d=3,
             h=dict(box=(0.5, 6.5, 2, 7, 9, 8, 1, 2), door=(2, 3, 6), front_win=[(4, 5, 3, 6)],
                    side_win=[(4, 5, 3, 6)], flowers=[(1.5, POPPY[0]), (5.5, POPPY[1])],
                    courses=1),
             ch=(4, 5, 3, 4, 9, 22),
             tree=(8, 2, 8, 3, [(0, -6, 7), (3, -3, 5), (-3, -2, 4.5)])),
    64: dict(m=4, G=13.5, H=5, d=3,
             h=dict(box=(1, 8.5, 2.5, 9.5, 12, 11, 1, 2), door=(3, 4.5, 8),
                    front_win=[(5.5, 7, 4, 8)], side_win=[(5.5, 6.5, 4, 8), (5.5, 6.5, 13, 16)],
                    flowers=[(2, POPPY[0]), (5, PLASTER[4]), (7.5, POPPY[1])], courses=1.5),
             ch=(5.5, 7, 4, 5.5, 12, 30),
             tree=(10.5, 2.5, 11, 4, [(0, -8, 9.5), (4, -4, 6.5), (-5, -3, 6.5)])),
    128: dict(m=8, G=27.5, H=10, d=4,
              h=dict(box=(2, 17, 5, 19, 24, 22, 2, 4), door=(6, 9, 16),
                     front_win=[(11, 14, 8, 16)], side_win=[(11, 13, 8, 16), (11, 13, 26, 32)],
                     flowers=[(3, POPPY[0]), (4, POPPY[1]), (10.5, PLASTER[4]), (15, POPPY[0]),
                              (16, BLOSSOM[3])],
                     courses=1.5),
              ch=(11, 14, 8, 11, 24, 60),
              tree=(21, 5, 22, 8, [(0, -16, 19), (9, -8, 13), (-10, -6, 13)])),
}


def draw(n):
    """The picture at n x n px."""
    if n in HAND:
        return hand(n)
    t = SIZES[n]
    N = 2 * n
    P = iso(n, n // 2)
    land, top = ground(N, P, t["G"], t["H"], t["d"])
    if t["d"] >= 3:
        # Sun from the upper left: shade falls to the right of the cottage and the tree, and a
        # trodden path runs from the door to the edge of the land.
        x0, x1, y0, y1 = t["h"]["box"][:4]
        land.poly([P(x1, y0), P(x1 + 1.5, y0 - 0.5), P(x1 + 1.5, y1 - 0.5), P(x1, y1)], LEAF[3],
                  top)
        gx, gy = t["tree"][:2]
        land.poly([P(gx - 0.5, gy + 0.5), P(gx + 1.5, gy - 0.5), P(gx + 2, gy), P(gx, gy + 1)],
                  LEAF[3], top)
        a0, a1, _ = t["h"]["door"]
        G = t["G"]
        land.poly([P(a0 - 0.25, y1), P(a1 + 0.25, y1), P(a1 + 0.75, G), P(a0 - 0.75, G)],
                  EARTH[3], top)
        land.poly([P(a0, y1), P(a1, y1), P(a1 + 0.5, G), P(a0 - 0.5, G)], EARTH[4], top)
    layers = [land, chimney(N, P, t["ch"], t["d"]), house(N, P, t["h"], t["d"]),
              tree(N, P, t["tree"], t["d"])]
    return fit(composite(N, layers), n, t["m"])


# ---- output ---------------------------------------------------------------------------------

def drawings():
    pics = {n: draw(n) for n in NATIVE}
    for size, k in ENLARGED.items():
        pics[size] = np.repeat(np.repeat(pics[128], k, 0), k, 1)
    palette = {_c(h) for h in PALETTE}
    for n, a in pics.items():
        used = {tuple(int(v) for v in p) for p in a.reshape(-1, 4) if p[3]}
        if not used <= palette:
            raise ValueError(f"{n}: colours outside the palette: {sorted(used - palette)[:4]}")
        if set(np.unique(a[..., 3])) - {0, 255}:
            raise ValueError(f"{n}: partial alpha")
    return pics


def png_bytes(a):
    buf = io.BytesIO()
    Image.fromarray(a, "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def ico_bytes(pics):
    """An .ico with every size in ICO: 32-bit BGRA bitmaps with their AND mask below 256, the
    256 entry as PNG (what Windows expects since Vista, and the only way to keep it small)."""
    blobs = []
    for n in ICO:
        a = pics[n]
        if n >= 256:
            blobs.append(png_bytes(a))
            continue
        head = struct.pack("<IiiHHIIiiII", 40, n, 2 * n, 1, 32, 0, 0, 0, 0, 0, 0)
        bgra = a[::-1, :, [2, 1, 0, 3]].tobytes()
        row = ((n + 31) // 32) * 4
        mask = np.packbits(a[::-1, :, 3] == 0, axis=1)
        mask = np.pad(mask, ((0, 0), (0, row - mask.shape[1]))).tobytes()
        blobs.append(head + bgra + mask)
    out = struct.pack("<HHH", 0, 1, len(ICO))
    offset = 6 + 16 * len(ICO)
    for n, blob in zip(ICO, blobs):
        out += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    return out + b"".join(blobs)


def outputs():
    pics = drawings()
    files = {f"icon-{n}.png": png_bytes(pics[n]) for n in sorted(pics)}
    files["laeticias-corner.ico"] = ico_bytes(pics)
    return files


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "assets" / "icon")
    ap.add_argument("--check", action="store_true", help="compare with the files in --out")
    a = ap.parse_args(argv)
    files = outputs()
    if a.check:
        stale = [f for f, data in files.items()
                 if not (a.out / f).is_file() or (a.out / f).read_bytes() != data]
        extra = sorted(p.name for p in a.out.glob("*") if p.name not in files)
        for f in stale:
            print(f"icon: {f} differs from what the generator draws", file=sys.stderr)
        for f in extra:
            print(f"icon: {f} is not the generator's", file=sys.stderr)
        return 1 if stale or extra else 0
    a.out.mkdir(parents=True, exist_ok=True)
    for f, data in files.items():
        (a.out / f).write_bytes(data)
    print(f"icon: {len(files)} files in {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
