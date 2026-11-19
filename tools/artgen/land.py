"""Natural land faces: one level of rock, earth, snow or sea cliff under a raised tile edge
(`edge/<material>_<se|sw>/v<n>`, its rim band `/top`, a sea cliff's animated foot `/v<n>/f<k>`).

The engine stacks one face per level and picks each level's look at random, so a cliff of three
levels is three independent draws. To read as one mass of land rather than a stack of blocks:

- Nothing marks the band: no strata, courses or shading tied to the band's top or foot.
- Every field repeats every band down the face and every tile edge along it, and the looks
  differ only where no neighbour sees it: rock breaks into facets on a staggered lattice whose
  row on the band's seam is common to every look (a seam pixel is never claimed by a look's own
  facets), so facets, cracks and stains run on across levels whatever looks are drawn.
- Long features are vertical (joints, drip stains, runnels, roots), as on real banks and cliffs.
- The rim band rounds the lip: the turf or rock shoulder hangs over the edge in uneven tufts
  with the shadow under it, so the top edge is never the tile's straight line.

Lengths are design units times `k` (16 units per tile edge); one-pixel marks stay one pixel."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import terrain as home
from pack import Sprite
from validate import diamond
from voxel import hash01, value_noise


# ---------------------------------------------------------------- face geometry

def face_columns(k, side):
    """Screen columns of one level of face under a tile edge: x relative to the anchor (the
    tile's top vertex) and the first row of face below the ground diamond's lower edge.

    A face covers exactly the 16k columns its tile steps along the edge (x 0..16k-1 under
    the south-east edge, -16k..-1 under the south-west one), so faces of a run of tiles meet
    with no gap or overlap. The diamond itself is two columns narrower than that step; the
    face's outermost column lies under the next tile of the run, and its first row follows
    that tile's lower edge (the same edge line, half a tile up)."""
    want = diamond(32 * k)
    h, w = want.shape
    rows = np.arange(h)[:, None]
    bottom = np.where(want, rows, -1).max(axis=0)            # per diamond column
    left = -(16 * k - 1)                                     # x of the diamond's first column

    def bottom_at(x):
        i = x - left
        if 0 <= i < w:
            return int(bottom[i])
        step = 16 * k if side == "se" else -16 * k           # the next tile along the edge
        return int(bottom[x - step - left]) - 8 * k
    xs = np.arange(0, 16 * k) if side == "se" else np.arange(-16 * k, 0)
    return xs, np.array([bottom_at(int(x)) + 1 for x in xs])


def face_grid(side, k, above):
    """Pixel grid of one level of face: for each pixel its distance along the face from the
    bottom vertex `s` (px), its row inside the band `d` (0 at the rim) and whether it is on
    the face; plus the sprite size and anchor."""
    xs, first = face_columns(k, side)
    band = 8 * k
    H, W = 16 * k + above, 16 * k
    x0 = 0 if side == "se" else -16 * k
    py, px = np.mgrid[0:H, 0:W]
    s = np.zeros((H, W)); d = np.full((H, W), -999.0)
    for x, f in zip(xs, first):
        col = x - x0
        if 0 <= col < W:
            s[:, col] = x if side == "se" else -x
            d[:, col] = py[:, col] - (f + above - 8 * k)
    return px, py, s, d, band, H, W, -x0, above - 8 * k


def periodic(s, d, W, band, scale, seed, v=0):
    """Smooth noise repeating every face width along s and every band down d, so faces stack
    and join; variants differ only away from the tile edges."""
    a = np.sin(2 * np.pi * s / W)
    b = np.cos(2 * np.pi * s / W)
    c = np.sin(2 * np.pi * d / band)
    e = np.cos(2 * np.pi * d / band)
    n = value_noise(a * scale + 7, b * scale + 3, (c + 2 * e) * scale * 0.7, 1.0, seed)
    if v:
        win = np.sin(np.pi * np.clip(s / W, 0, 1))
        n = n * (1 - win) + value_noise(s / 3.0 + v * 31, d / 3.0, e * 3, 1.0, seed + v) * win
    return n


@dataclass(frozen=True)
class Stone:
    """A natural face material. Ramps run dark to light; `kind` picks the build."""
    kind: str                     # "rock", "earth", "snow" or "coast"
    rock: tuple                   # the face's own ramp (rock, or soil for earth)
    cover: tuple                  # what grows on the lip and ledges (grass, dry grass, scrub)
    seed: int
    stain: tuple = ()             # rust, lichen or salt streaks; empty for none
    shrub: tuple = ()             # shrubs on ledges; empty for none
    stones: tuple = ()            # stones in an earth bank
    snow: tuple = ()              # snow ramp (snow faces)
    surf: tuple = ()              # surf ramp (sea cliffs' animated foot)
    cell: float = 5.0             # facet width in design units (along the face)
    rows: int = 2                 # facet rows per level
    jag: float = 1.0              # how broken the rock is (crack width, facet tilt)


def _face(side, k, above):
    px, py, s, d, band, H, W, ox, oy = face_grid(side, k, above)
    return px, py, s, d, float(band), H, W, ox, oy


def _cells(s, d, W, band, ncol, nrow, seed, v, jitter=0.8):
    """Facets on a staggered lattice repeating every W along the face and every band down it.
    Row 0 sits on the band's seam and is the same in every look; the others move with `v` and are
    kept away from the seam (their distance grows there), so seam rows agree across looks.
    Returns the nearest and second distances, the facet's hash pair and its centre's offset."""
    cw, ch = W / ncol, band / nrow
    d1 = np.full(s.shape, 1e9, np.float32)
    d2 = np.full(s.shape, 1e9, np.float32)
    ha = np.zeros(s.shape, np.float32)
    hb = np.zeros(s.shape, np.float32)
    oy = np.zeros(s.shape, np.float32)
    near_seam = np.cos(np.pi * (d % band) / band) ** 2          # 1 on the seam, 0 mid-band
    jb = np.floor(d / ch).astype(np.int64)
    for dj in (-1, 0, 1, 2):
        j = jb + dj
        jm = j % nrow
        own = jm != 0
        var = np.where(own, v, 0)
        stagger = np.where(jm % 2 == 1, 0.5 * cw, 0.0)
        ib = np.floor((s - stagger) / cw).astype(np.int64)
        for di in (-1, 0, 1):
            i = ib + di
            im = i % ncol
            h1 = hash01(im, jm, seed, var, 1)
            h2 = hash01(im, jm, seed, var, 2)
            cx = (i + 0.5) * cw + stagger + (h1 - 0.5) * jitter * cw
            cy = j * ch + (h2 - 0.5) * jitter * ch * 0.8
            dist = np.hypot(s - cx, (d - cy) * 1.25)
            dist = dist + own * near_seam * 2.5 * ch                 # a look's facets keep off the seam
            closer = dist < d1
            d2 = np.where(closer, d1, np.minimum(d2, dist))
            d1 = np.where(closer, dist, d1)
            ha = np.where(closer, hash01(im, jm, seed, var, 3), ha)
            hb = np.where(closer, hash01(im, jm, seed, var, 4), hb)
            oy = np.where(closer, d - cy, oy)
    return d1, d2, ha, hb, oy


def _sun(side):
    """How a facet turned along the face meets the sun (from the upper left, -x and +y): the
    +y face (sw) is the sun side and is lit from its far end; the +x face (se) is in shade and
    lit a little from its outer corner. Returns (base level, weight of a turn along s)."""
    return (0.0, 0.9) if side == "sw" else (-0.9, -0.35)


def _rock(m: Stone, side, v, k, px, py, s, d, W, band):
    """Rock facets: each a lit or shaded plane leaning its own way, darker toward its foot,
    cracks between them with a lit upper lip; vertical joints and drip stains run across."""
    base, along = _sun(side)
    ncol = max(2, round(16 / m.cell))
    # Facets on a warped lattice (its rows wander up and down along the face and lean with it,
    # repeating each band), so they break like rock rather than lie in courses like a wall.
    warp_d = d + 0.32 * band * np.sin(2 * np.pi * (s / W + 0.15 * np.sin(2 * np.pi * d / band))) \
        + 0.12 * band * np.sin(2 * np.pi * 3 * s / W + 1.7)
    warp_s = s + 0.18 * W * np.sin(2 * np.pi * d / band + 2 * np.pi * s / W)
    d1, d2, ha, hb, oy = _cells(warp_s, warp_d, W, band, ncol, m.rows, m.seed, v)
    tilt = (ha - 0.5) * 2.0
    up = hb - 0.35
    ch = band / m.rows
    mass = periodic(s, d, W, band, 0.7, m.seed + 13, v) - 0.5        # big lit and shaded masses
    lvl = 3.1 + base + tilt * along * 0.8 * m.jag + up * 0.8 - np.clip(oy / ch, -0.6, 0.8) * 0.6 \
        + mass * along * 1.6
    gap = d2 - d1
    open_ = periodic(s, d, W, band, 2.2, m.seed + 14, v) > 0.36      # some facets fuse, unbroken
    crack = (gap < 0.5 * k * m.jag) & open_
    rim = (gap >= 0.5 * k * m.jag) & (gap < 1.3 * k * m.jag) & (oy < 0) & open_
    lvl = lvl - crack * 1.6 + rim * 0.5
    joint = (np.abs(periodic(s, d * 0.15, W, band, 2.0, m.seed + 5) - 0.5) < 0.022) & ~crack
    lvl = lvl - joint * 1.0
    grain = periodic(s, d, W, band, 3.5, m.seed + 6, v)
    lvl = lvl + (grain - 0.5) * 0.5 + (hash01(px, py, m.seed + 7 + v) - 0.5) * 0.35
    P = (px, py)
    rgb = home._paint(m.rock, lvl, *P, k=k)
    if m.stain:
        # Thin weathering streaks down the face, here and there, never a stripe per tile.
        drip = (periodic(s * 2.0, d * 0.1, W, band, 2.4, m.seed + 8) > 0.74) & \
            (periodic(s, d, W, band, 1.0, m.seed + 12, v) > 0.45) & ~crack
        rgb = np.where(drip[..., None], home._paint(m.stain, lvl - 0.8, *P, k=k), rgb)
    if m.shrub:
        # A shrub clings in a crack's upper lip here and there, away from the seams.
        mid = np.sin(np.pi * (d % band) / band) > 0.45
        seed_px = rim & mid & (hash01(np.floor(s / (3 * k)).astype(np.int64) % (W // (3 * k) or 1),
                                      np.floor(d / (4 * k)).astype(np.int64), m.seed + 9, v) < 0.07)
        bush = np.zeros_like(seed_px)
        for dy in range(0, 2 * k + 1):
            for dx in (-1, 0, 1):
                bush |= np.roll(np.roll(seed_px, -dy, 0), dx, 1) & (hash01(px, py - dy, m.seed + 10) < 0.75)
        rgb = np.where(bush[..., None], home._paint(m.shrub, 1.9 + base + hash01(px, py, m.seed + 11) * 1.4,
                                                    *P, k=k), rgb)
    return rgb, lvl, crack, up


def _pebbles(s, d, W, band, k, seed, v, density, size):
    """Rounded stones on a jittered lattice repeating across the face and down it: for each
    pixel the offset from its stone's centre in units of the stone's radius (inside < 1) and a
    hash per stone. Looks own the stones away from the seams; the seam rows are common."""
    cell = size * 2.4 * k
    nu, nd = max(1, round(W / cell)), max(1, round(band / cell))
    cu, cd = W / nu, band / nd
    best = np.full(s.shape, 9.0, np.float32)
    du = np.zeros(s.shape, np.float32)
    dv = np.zeros(s.shape, np.float32)
    hh = np.zeros(s.shape, np.float32)
    iu0 = np.floor(s / cu).astype(np.int64)
    id0 = np.floor(d / cd).astype(np.int64)
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            iu, idd = iu0 + a, id0 + b
            ju, jd = iu % nu, idd % nd
            var = np.where(np.sin(np.pi * ((idd + 0.5) * cd % band) / band) > 0.5, v, 0)
            keep = hash01(ju, jd, seed, var, 1) < density
            r = size * k * (0.6 + 0.6 * hash01(ju, jd, seed, var, 2))
            cx = (iu + 0.5 + (hash01(ju, jd, seed, var, 3) - 0.5) * 0.6) * cu
            cy = (idd + 0.5 + (hash01(ju, jd, seed, var, 4) - 0.5) * 0.6) * cd
            ex, ey = (s - cx) / r, (d - cy) / (r * 0.8)
            e = np.hypot(ex, ey)
            take = keep & (e < best)
            best = np.where(take, e, best)
            du = np.where(take, ex, du)
            dv = np.where(take, ey, dv)
            hh = np.where(take, hash01(ju, jd, seed, var, 5), hh)
    return best, du, dv, hh


def _earth(m: Stone, side, v, k, px, py, s, d, W, band):
    """An earth bank: soil in soft clods (no layers, no streaks), darker damp hollows, rounded
    stones bedded in it (lit on their upper side, a dark seam below), and in some looks a tuft of
    grass holding on mid-face with its blades hanging."""
    base, along = _sun(side)
    d1, d2, ha, hb, oy = _cells(s, d, W, band, max(2, round(16 / m.cell)), m.rows, m.seed, v, jitter=0.9)
    lump = (ha - 0.5) * along * 0.5 + (hb - 0.5) * 0.35 - np.clip(oy / (band / m.rows), -0.6, 0.8) * 0.45
    broad = periodic(s, d, W, band, 1.2, m.seed + 3, v)
    fine = periodic(s, d, W, band, 5.0, m.seed + 4, v)
    damp = broad < 0.3
    lvl = 2.9 + base + lump + (broad - 0.5) * 0.8 + (fine - 0.5) * 0.5 - damp * 0.5 \
        - ((d2 - d1) < 0.35 * k) * 0.5 + (hash01(px, py, m.seed + 5 + v) - 0.5) * 0.3
    P = (px, py)
    rgb = home._paint(m.rock, lvl, *P, k=k)
    if m.stones:
        for seed, dens, size in ((m.seed + 6, 0.2, 1.2), (m.seed + 16, 0.07, 2.2)):
            e, du, dv, hh = _pebbles(s, d, W, band, k, seed, v, dens, size)
            seam = (e >= 1) & (e < 1.0 + 0.9 / k) & (dv > -0.2)
            stone = e < 1
            rgb = np.where(seam[..., None], home._paint(m.rock, lvl - 1.4, *P, k=k), rgb)
            slvl = 2.2 + base * 0.6 + hh * 0.8 - dv * 1.4 + du * along * 0.8
            rgb = np.where(stone[..., None], home._paint(m.stones, slvl, *P, k=k), rgb)
    tuft = (periodic(s, d, W, band, 1.8, m.seed + 7, v) > 0.7) & (np.sin(np.pi * (d % band) / band) > 0.3)
    blade = tuft & (hash01(np.floor(s).astype(np.int64), np.floor(d / (2 * k)).astype(np.int64), m.seed + 8) < 0.55)
    glvl = 2.6 + base - ((d % band) / band) * 0.8 + (hash01(px, py, m.seed + 9) - 0.5)
    rgb = np.where(blade[..., None], home._paint(m.cover, glvl, *P, k=k), rgb)
    return rgb, lvl, np.zeros_like(blade), np.zeros(s.shape, np.float32)


def _lip(m: Stone, side, v, k, px, py, s, d, W, band, rgb, above):
    """The rim band's shoulder: the ground's turf (or the rock's broken edge) hangs over the
    top of the face in uneven tufts with single blades at their tips, a lit rounded shoulder of
    soil or rock under it, the turf's shadow along its lower edge and pale roots below; a few
    blades stand up over the edge itself. Returns the colours and the pixels above the rim."""
    base, _along = _sun(side)
    col = np.floor(s).astype(np.int64) % W
    P = (px, py)
    hang = (1.0 + 2.6 * periodic(s, d * 0, W, band, 3.0, m.seed + 20, v)) * k
    hang = hang * (0.6 + 0.4 * hash01(col, m.seed + 21, v)) + 1.5 * k * hash01(col, m.seed + 22, v) ** 4
    if m.kind == "snow":
        drift = (1.5 + 2.8 * periodic(s, d * 0, W, band, 2.0, m.seed + 23, v)) * k
        corn = (d >= 0) & (d < drift)
        lift = above * (0.25 + 0.75 * periodic(s, d * 0, W, band, 2.5, m.seed + 24, v))
        over = (d < 0) & (d >= -lift * 0.5)
        lvl = 3.5 + base * 0.6 - (d > drift - k) * 1.3 + (hash01(px, py, m.seed + 25) - 0.5) * 0.4
        rgb = np.where((corn | over)[..., None], home._paint(m.snow, lvl, *P, k=k, band=0.3), rgb)
        return rgb, over
    turf = (d >= 0) & (d < hang)
    shadow = (d >= hang) & (d < hang + max(1, k // 2) + 0.5)
    shoulder = (d >= hang + 1) & (d < hang + 2.2 * k)
    under = home._paint(m.rock, 3.6 + base * 0.5 + (hash01(px, py, m.seed + 26) - 0.5) * 0.6, *P, k=k)
    rgb = np.where(shoulder[..., None], under, rgb)
    rgb = np.where(shadow[..., None], home._paint(m.rock, 1.0 + base * 0.4, *P, k=k), rgb)
    tl = 2.7 + base * 0.7 - (d / np.maximum(hang, 1)) * 0.9 + (hash01(col, m.seed + 27) - 0.5) * 1.2
    rgb = np.where(turf[..., None], home._paint(m.cover, tl, *P, k=k), rgb)
    if m.kind == "earth":
        for i in range(3):
            rs = W * hash01(m.seed + 28, v, i)
            ln = (3 + 4 * hash01(m.seed + 29, v, i)) * k
            path = rs + 1.3 * k * np.sin(d / (2.2 * k) + 6.28 * hash01(m.seed + 30, v, i))
            root = (np.abs(((s - path + W / 2) % W) - W / 2) < 0.5) & (d > hang + 1) & (d < hang + ln)
            rgb = np.where(root[..., None], home._paint(m.rock, 4.4 + base, *P, k=k), rgb)
    tall = above * hash01(col, m.seed + 31, v) * (hash01(col // 2, m.seed + 32, v) < 0.45)
    over = (d < 0) & (d >= -tall)
    rgb = np.where(over[..., None], home._paint(m.cover, 2.4 + base * 0.6 + (hash01(px, py, m.seed + 33) - 0.5),
                                                *P, k=k), rgb)
    return rgb, over


def _surf(m: Stone, side, v, k, px, py, s, d, W, band, rgb, lvl, frame, frames):
    """The level that stands in the sea: wet dark rock low down, a wave-cut notch, and surf
    running up the face and drawing back with the frames, spray thrown above it."""
    base, _ = _sun(side)
    t = frame / frames
    P = (px, py)
    wet = d > band - 4.5 * k
    notch = (d > band - 3.2 * k) & (d < band - 1.6 * k)
    rgb = np.where(wet[..., None], home._paint(m.rock, lvl - 1.3, *P, k=k), rgb)
    rgb = np.where(notch[..., None], home._paint(m.rock, 1.1 + base * 0.5, *P, k=k), rgb)
    wob = periodic(s, d * 0, W, band, 2.0, m.seed + 40, v) - 0.5
    run = (1.8 + 2.4 * (0.5 + 0.5 * math.sin(2 * math.pi * t)) + wob * 2.0) * k
    surf = d > band - run
    spray = (d > band - run - 2.2 * k) & ~surf & (hash01(px, py, m.seed + 41 + frame) < 0.3)
    rgb = np.where(surf[..., None], home._paint(m.surf, 2.0 + hash01(px, py, m.seed + 42 + frame) * 2.0, *P, k=k), rgb)
    return np.where(spray[..., None], home._paint(m.surf, np.full(s.shape, 9.0), *P, k=k), rgb)


def face(m: Stone, side: str, v: int, k: int, top: bool = False, frame: int | None = None,
         frames: int = 4, wedge: int | None = None) -> Sprite:
    """One level of natural face under the +x (`se`) or +y (`sw`) edge, look `v`; `top` is the
    rim band (it replaces the uppermost level, drawn after the ground); `frame` the sea's foot.
    `wedge` is the uppermost level under a slope's edge, whose top falls a whole level along it:
    0 when it is high at the edge's outer corner (s = 0), 1 when high at its far end."""
    above = 5 * k if top else 0
    px, py, s, d, band, H, W, ox, oy = _face(side, k, above)
    if wedge is not None:
        fall = band * np.clip((s if wedge == 0 else W - s) / W, 0, 1)
        d_lip = d - fall
    # a wedge reaches two rows up under the slope, which is drawn over it, so no seam opens
    on = (d >= 0) & (d < band) & ((d_lip >= (0 if top else -2)) if wedge is not None else True)
    dd = np.where(on, d, np.clip(d, 0, band - 1))
    if m.kind == "earth":
        rgb, lvl, crack, up = _earth(m, side, v, k, px, py, s, dd, W, band)
    else:
        rgb, lvl, crack, up = _rock(m, side, v, k, px, py, s, dd, W, band)
    base, _ = _sun(side)
    if m.kind == "snow":
        # Snow lies on the facets that turn up, on their upper part, and in the cracks' lips.
        drift = periodic(s, dd, W, band, 2.6, m.seed + 52, v)
        lying = (up + (drift - 0.5) * 0.9 > 0.2) & ~crack
        lying &= hash01(px, py, m.seed + 50 + v) < 0.94
        rgb = np.where(lying[..., None], home._paint(m.snow, 2.6 + base * 0.6 + up, px, py, k=k, band=0.3), rgb)
    if m.kind == "coast" and m.stain:
        salt = periodic(s, dd * 0.3, W, band, 1.6, m.seed + 51, v) > 0.64
        rgb = np.where((salt & ~crack)[..., None], home._paint(m.stain, lvl - 2.6, px, py, k=k), rgb)
    if frame is not None:
        rgb = _surf(m, side, v, k, px, py, s, dd, W, band, rgb, lvl, frame, frames)
    alpha = on
    if top:
        dl = d_lip if wedge is not None else d
        rgb, over = _lip(m, side, v, k, px, py, s, dl, W, band, rgb, above)
        alpha = on | (over & (d < band))
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha * 255
    return Sprite(rgba, ox, oy)
