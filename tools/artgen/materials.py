"""The materials layer for big architecture: surface textures as tone functions and the small
built details that make a wall, a roof or a floor read as made by hands.

Tones are functions of voxel-centre coordinates (design units, grid axes) returning ramp steps
to add to the lit level, as `arch.fill` expects. Details are drawn with `arch.fill`, each as
one periodic mask over a strip, so a whole row of beam ends or spouts costs one fill and every
helper is safe to call for the whole building on every chunk (`bigrender`).

Reusable by every set: nothing here is Persian except the defaults the Pārsa set passes.
"""

import numpy as np

from arch import FACES, face_box, face_frame, face_length, face_normal, fill, rod
from voxel import hash01, value_noise


def _i(a):
    return np.floor(a).astype(np.int64)


# ---------------------------------------------------------------- textures

def ashlar(course=3.0, block=7.0, seed=1, joint=0.35, polygonal=0.0, spread=0.7, odd=0.12):
    """Dressed stone in courses: each block its own tone (a few `odd` blocks warmer or darker,
    as stone from different beds), hairline dark joints, a lit upper arris, the lower part of
    each block a touch darker where dust and rain settle, small chips at the corners.
    `polygonal` skews the joints of each course (fitted terrace masonry)."""
    def tone(X, Y, Z):
        along = X + Y
        row = np.floor(Z / course)
        r = row.astype(np.int64)
        skew = polygonal * (hash01(r, seed) - 0.5) * ((Z % course) / course - 0.5) * block
        width = block * (0.75 + 0.5 * hash01(r, seed, 3))
        a = along + hash01(r, seed, 5) * width + skew
        col = _i(a / width)
        u, v = a % width, Z % course
        h = hash01(r, col, seed)
        jn = (v < joint) | (u < joint)
        top = (v >= course - joint * 1.5) & ~jn
        oddb = hash01(r, col, seed, 9)
        t = (h - 0.5) * spread + np.where(oddb < odd, -0.55, 0) + np.where(oddb > 1 - odd * 0.6, 0.4, 0)
        t = t - 0.25 * (1 - v / course) + 0.45 * top - 0.95 * jn
        chip = (hash01(_i(along * 2), _i(Z * 2), seed, 11) < 0.025) & ((u < 1.2) | (v < 0.8))
        return t - 0.8 * chip
    return tone


def mud_plaster(seed=3, amount=0.55, z0=0.0, damp=5.0, patches=True):
    """Hand-smoothed mud plaster on mudbrick: broad soft blotches, patched repairs a shade off
    the wall around them, flecks of chopped straw, faint rain streaks, and a darker band of
    damp and splash at the foot with a ragged upper edge. `z0` is the foot of the wall."""
    def tone(X, Y, Z):
        along = X + Y
        broad = value_noise(along * 0.6, (X - Y) * 0.6, Z * 0.8, 7.0, seed) - 0.5
        fine = value_noise(along * 2.0, X - Y, Z * 2.0, 2.2, seed + 1) - 0.5
        t = broad * amount + fine * 0.18
        if patches:
            pa, pz = _i(along / 9.0), _i(Z / 7.0)
            ph = hash01(pa, pz, seed, 2)
            inside = ((along % 9.0) > 1.5 + ph * 2) & ((along % 9.0) < 6.5 + ph * 2) & \
                ((Z % 7.0) > 1.0 + ph) & ((Z % 7.0) < 5.0 + ph)
            t = t + np.where((ph < 0.18) & inside, (hash01(pa, pz, seed, 4) - 0.4) * 0.7, 0)
        straw = hash01(_i(along * 2), _i(Z * 2), _i((X - Y) * 2), seed, 6) < 0.035
        streak = (value_noise(along * 3.0, X * 0, Z * 0.15, 3.0, seed + 7) > 0.82) * -0.25
        edge = damp * (0.7 + 0.6 * value_noise(along, X * 0, Z * 0, 5.0, seed + 8))
        foot = (Z - z0) < edge
        return t + 0.45 * straw + streak - 0.55 * foot - 0.25 * ((Z - z0) < edge * 0.45)
    return tone


def roof_plaster(seed=5, amount=0.45):
    """A flat mud roof seen from above: trowelled in sweeps, rolled smooth in lanes, patched,
    with fine cracks; low contrast so it stays calm but never flat."""
    def tone(X, Y, Z):
        broad = value_noise(X * 0.5, Y * 0.5, Z * 0, 9.0, seed) - 0.5
        sweep = np.sin((X * 0.8 + Y * 0.35) + 3.0 * value_noise(X, Y, Z * 0, 6.0, seed + 1)) * 0.12
        lane = (np.abs(((Y + 0.3 * X) % 11.0) - 5.5) < 0.6) * -0.12
        crack = np.abs(value_noise(X, Y, Z * 0, 4.5, seed + 2) - 0.5) < 0.01
        pa, pb = _i(X / 13.0), _i(Y / 10.0)
        patch = (hash01(pa, pb, seed, 3) < 0.15) & ((X % 13.0) > 3) & ((X % 13.0) < 10) & \
            ((Y % 10.0) > 2) & ((Y % 10.0) < 8)
        return broad * amount + sweep + lane - 0.45 * crack + patch * (hash01(pa, pb, seed, 4) - 0.3) * 0.6
    return tone


def timber(axis="x", seed=7, amount=0.5):
    """Wood grain running along `axis` with a knot here and there."""
    def tone(X, Y, Z):
        along, across = (X, Y) if axis == "x" else (Y, X)
        g = np.sin(across * 5.0 + Z * 3.0 + 2.5 * value_noise(along * 0.3, across, Z, 3.0, seed)) * 0.5 + 0.5
        knot = hash01(_i(along / 3.0), _i(across * 2), seed) < 0.02
        return (g - 0.5) * amount - 0.6 * knot
    return tone


def paving(slab_x=7.0, slab_y=5.0, seed=9, joint=0.3, wear=None):
    """Fitted floor slabs on a horizontal surface: staggered rows, one tone per slab, hairline
    joints, and optionally a worn lane (`wear(X, Y)` in [0, 1]) polished lighter by feet."""
    def tone(X, Y, Z):
        row = _i(Y / slab_y)
        off = (row % 2) * slab_x * 0.5 + hash01(row, seed) * 2.0
        col = _i((X + off) / slab_x)
        jn = ((Y % slab_y) < joint) | (((X + off) % slab_x) < joint)
        h = hash01(row, col, seed)
        t = (h - 0.5) * 0.6 - 1.1 * jn + (value_noise(X, Y, Z * 0, 6.0, seed + 1) - 0.5) * 0.3
        if wear is not None:
            t = t + 0.35 * wear(X, Y)
        return t
    return tone


def glazed(course=1.0, brick=2.4, seed=11):
    """Glazed brick: a glassy face per brick with a bright lip along its top, dark joints."""
    def tone(X, Y, Z):
        row = _i(Z / course)
        a = X + Y + (row % 2) * brick * 0.5
        jn = ((Z % course) < 0.22) | ((a % brick) < 0.22)
        lip = (Z % course) > course - 0.3
        return -0.9 * jn + 0.35 * lip + (hash01(row, _i(a / brick), seed) - 0.5) * 0.45
    return tone


def plus(*tones):
    """Sum of tone functions and constants."""
    def tone(X, Y, Z):
        return sum(t(X, Y, Z) if callable(t) else t for t in tones)
    return tone


# ---------------------------------------------------------------- details on walls

def beam_ends(m, face, wall, z, spacing=4.0, r=0.9, out=1.2, material="cedar", paint=None, s0=None, s1=None):
    """A row of round roof-beam ends standing out of a wall face at height `z` (their centre),
    one every `spacing`. `paint` colours the end grain (palaces painted their beam ends)."""
    x0, x1, y0, y1 = wall[:4]
    L = face_length(face, x0, x1, y0, y1)
    s0 = spacing * 0.5 if s0 is None else s0
    s1 = L if s1 is None else s1
    box = face_box(face, x0, x1, y0, y1, z - r, z + r, s0 - r, s1, -out, 0.5)

    def mask(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = ((s - s0 + r) % spacing) - r
        return (u * u + (Z - z) ** 2 <= r * r) & (d < 0.5) & (s < s1)

    def nrm(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = ((s - s0 + r) % spacing) - r
        n = face_normal(face)
        # Rounded logs: the normal leans with the position on the end so it reads as a cylinder.
        w = 0.6 * (Z - z) / r
        return (n[0] + X * 0, n[1] + Y * 0, w + u * 0)

    fill(m, box, material, mask, tone=lambda X, Y, Z: 0.2 + 0.4 * (Z > z + r * 0.3), normal=nrm)
    if paint:
        def end(X, Y, Z):
            s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            u = ((s - s0 + r) % spacing) - r
            return (u * u + (Z - z) ** 2 <= (r * 0.62) ** 2) & (d < -out + 0.55) & (s < s1)
        fill(m, box, paint, end, tone=0.3)


def spouts(m, face, wall, z, spacing=24.0, length=2.4, material="cedar", streak=True, offset=0.0):
    """Drain spouts: short open channels jutting from a wall below the roof edge at `z`, each
    with a dark streak of rain-washed plaster under it."""
    x0, x1, y0, y1, wz0, _wz1 = wall
    L = face_length(face, x0, x1, y0, y1)
    s_first = spacing * 0.5 + offset
    box = face_box(face, x0, x1, y0, y1, z - 0.8, z + 0.6, 0, L, -length, 0.2)

    def mask(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        u = np.abs(((s - s_first + spacing / 2) % spacing) - spacing / 2)
        return (u < 0.7) & (d < 0.2) & (s > 1) & (s < L - 1)
    fill(m, box, material, mask, tone=0.3)
    if streak:
        sb = face_box(face, x0, x1, y0, y1, wz0, z - 0.8, 0, L, -0.01, 0.45)

        def wet(X, Y, Z):
            s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            u = np.abs(((s - s_first + spacing / 2) % spacing) - spacing / 2)
            fade = np.clip((Z - wz0) / max(z - wz0, 1), 0, 1)
            return (u < 0.5 + 0.9 * (1 - fade)) & (hash01(_i(Z * 2), _i(s * 2), 31) < 0.35 + 0.6 * fade)
        _paint_existing(m, sb, wet, -0.9)


def _paint_existing(m, box, mask, tone):
    """Add `tone` to voxels already present in `box` where `mask` holds (stains, wear)."""
    w = m.box_window(*box)
    if w is None:
        return
    sl, X, Y, Z = w
    sel = np.broadcast_to(mask(X, Y, Z), m.mat[sl].shape) & (m.mat[sl] > 0)
    if sel.any():
        m.tone[sl][sel] += tone


def stain(m, box, mask, tone):
    """Darken or lighten what is already there (soot over a door, a worn step, a wet streak)."""
    _paint_existing(m, box, mask, tone)


def painted_bands(m, wall, z0, bands, sides=FACES, out=0.05):
    """Horizontal painted bands round a wall box from `z0` upward: [(height, material), ...]
    (the red and blue stripes under a parapet)."""
    x0, x1, y0, y1 = wall[:4]
    z = z0
    for h, mat in bands:
        for face in sides:
            L = face_length(face, x0, x1, y0, y1)
            fill(m, face_box(face, x0, x1, y0, y1, z, z + h, 0, L, -out, 0.5), mat, tone=0.1)
        z += h
    return z


def parapet(m, x0, x1, y0, y1, z, height=4.0, pitch=None, material="mudbrick", sides=FACES, thick=None,
            cap=None, stripes=()):
    """A parapet of stepped merlons (three steps a side) on a roof rim, optionally standing on
    painted stripes and with a plaster cap of another material on each tooth."""
    for h, mat in stripes:
        for face in sides:
            L = face_length(face, x0, x1, y0, y1)
            fill(m, face_box(face, x0, x1, y0, y1, z, z + h, 0, L, -0.15, 1.2), mat, tone=0.15)
        z += h
    pitch = pitch or height * 1.25
    thick = thick or max(1.0, height * 0.32)

    def tooth(s):
        u = np.abs((s % pitch) - pitch / 2) / (pitch / 2)
        return np.clip(np.floor((1 - u) * 4.0) / 3.0, 0, 1) * height

    for face in sides:
        L = face_length(face, x0, x1, y0, y1)
        box = face_box(face, x0, x1, y0, y1, z, z + height, 0, L, 0, thick)

        def mask(X, Y, Z, face=face):
            s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
            return (Z - z) < np.maximum(tooth(s), height * 0.2)

        fill(m, box, material, mask,
             tone=lambda X, Y, Z: 0.35 * ((Z - z) % (height / 3) > height / 3 - 0.5) - 0.15)
        if cap:
            def top(X, Y, Z, face=face):
                s, _d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
                t = np.maximum(tooth(s), height * 0.2)
                return ((Z - z) < t) & ((Z - z) >= t - 0.5)
            fill(m, box, cap, top, tone=0.4)
    return z + height


# ---------------------------------------------------------------- roofs

def roof(m, x0, x1, y0, y1, z, seed=1, material="mudbrick", kind="palace", hatches=1, rollers=1, clutter=0,
         fields=None, base=-0.8):
    """Dress a flat roof surface at height `z` over [x0,x1)x[y0,y1): packed mud plaster a shade
    darker than the whitened walls, then what lives on a roof. `fields` = (nx, ny) divides a
    big roof into drainage fields by low plaster ridges, each field dished toward its middle.
    `kind` 'palace': hatches with timber frames, a stone roller or two. 'domestic': a hatch
    with a ladder, a roller, and `clutter` things drying or stored (reed mats, jars, fodder,
    fuel, produce spread on a cloth)."""
    tone = roof_plaster(seed)
    if fields:
        fx, fy = (x1 - x0) / fields[0], (y1 - y0) / fields[1]

        def dished(X, Y, Z):
            u = np.abs(((X - x0) % fx) / fx - 0.5) * 2
            v = np.abs(((Y - y0) % fy) / fy - 0.5) * 2
            return tone(X, Y, Z) + base + 0.35 * np.maximum(u, v) ** 2
        fill(m, (x0, x1, y0, y1, z - 0.6, z), material, tone=dished)

        def ridge(X, Y, Z):
            a, b = (X - x0) % fx, (Y - y0) % fy
            return (np.minimum(a, fx - a) < 0.45) | (np.minimum(b, fy - b) < 0.45)
        fill(m, (x0 + 1, x1 - 1, y0 + 1, y1 - 1, z, z + 0.5), material, ridge, tone=base + 0.6)
    else:
        fill(m, (x0, x1, y0, y1, z - 0.6, z), material, tone=plus(tone, base))
    rng = np.random.Generator(np.random.PCG64([seed, 77]))
    W, D = x1 - x0, y1 - y0

    def spot(w, d):
        return (x0 + 2 + rng.uniform(0, max(W - w - 4, 0.1)), y0 + 2 + rng.uniform(0, max(D - d - 4, 0.1)))
    for _ in range(hatches):
        hx, hy = spot(5.0, 5.0)
        fill(m, (hx - 0.5, hx + 5.5, hy - 0.5, hy + 5.5, z, z + 0.8), "cedar", tone=timber("x", seed))
        fill(m, (hx + 0.6, hx + 4.4, hy + 0.6, hy + 4.4, z - 3.0, z + 0.9), "ink", tone=-1.0)
        if kind == "domestic":
            rod(m, (hx + 1.6, hy + 1.2, z - 2.0), (hx + 1.6, hy + 1.2, z + 4.0), 0.3, "wood")
            rod(m, (hx + 3.4, hy + 1.2, z - 2.0), (hx + 3.4, hy + 1.2, z + 4.0), 0.3, "wood")
    for _ in range(rollers):
        rx, ry = spot(5.0, 2.0)
        rod(m, (rx, ry + 1.2, z + 1.1), (rx + 4.0, ry + 1.2, z + 1.1), 1.1, "limestone", tone=0.1)
    if kind != "domestic":
        return
    for i in range(clutter):
        what = int(rng.integers(0, 5))
        cx, cy = spot(6.0, 5.0)
        if what == 0:      # a reed mat with something drying on it
            fill(m, (cx, cx + 6, cy, cy + 4.5, z, z + 0.4), "straw",
                 tone=lambda X, Y, Z: -0.35 * ((Y * 2.0) % 1.0 < 0.3) + 0.1)
            for j in range(5):
                px, py = cx + 1 + rng.uniform(0, 4), cy + 0.8 + rng.uniform(0, 3)
                fill(m, (px - 0.5, px + 0.5, py - 0.5, py + 0.5, z + 0.4, z + 0.9),
                     ("saffron", "cinnabar", "malachite")[int(rng.integers(0, 3))], tone=0.2)
        elif what == 1:    # storage jars
            for j in range(int(rng.integers(2, 4))):
                px, py = cx + j * 1.9, cy + 1.5 + rng.uniform(-0.5, 0.5)
                fill(m, (px - 1.0, px + 1.0, py - 1.0, py + 1.0, z, z + 3.0), "roof",
                     lambda X, Y, Z, px=px, py=py: np.hypot(X - px, Y - py) < 0.95 - 0.25 * np.abs(Z - z - 1.6) ** 1.5 / 2,
                     tone=0.1)
        elif what == 2:    # a stack of fodder or brushwood fuel
            fill(m, (cx, cx + 5, cy, cy + 3.5, z, z + 2.2), "straw",
                 lambda X, Y, Z: (Z - z) < 2.2 - 0.25 * ((X - cx - 2.5) ** 2) / 1.5,
                 tone=lambda X, Y, Z: (hash01(_i(X * 2), _i(Z * 2), seed) - 0.5) * 0.9)
        elif what == 3:    # a cloth spread out with grain or pulses
            col = ("linen", "cinnabar", "lapis")[int(rng.integers(0, 3))]
            fill(m, (cx, cx + 5, cy, cy + 4, z, z + 0.3), col, tone=0.0)
            fill(m, (cx + 1, cx + 4, cy + 1, cy + 3, z + 0.3, z + 0.8), "straw",
                 lambda X, Y, Z: (Z - z - 0.3) < 0.5 * (1 - np.hypot((X - cx - 2.5) / 1.5, (Y - cy - 2) / 1.0)), 0.3)
        else:              # a low bench and a basket
            fill(m, (cx, cx + 4, cy, cy + 1.6, z, z + 1.4), "wood", tone=timber("x", seed))
            fill(m, (cx + 4.6, cx + 6.2, cy, cy + 1.6, z, z + 1.6), "straw", tone=-0.1)


def curtain(m, a, b, z_top, z_bot, material="cinnabar", fringe="gold", tied=0.0, thick=0.5):
    """A cloth hung between two points (a, b) = (x, y) in plan under a beam, falling in folds,
    with a fringe along its foot; `tied` > 0 gathers it to both sides from that height down,
    so the middle stays open."""
    ax, ay = a
    bx, by = b
    L = float(np.hypot(bx - ax, by - ay))
    ux, uy = (bx - ax) / L, (by - ay) / L
    lo = np.minimum(np.array(a), np.array(b)) - 1.0
    hi = np.maximum(np.array(a), np.array(b)) + 1.0

    def frame(X, Y):
        t = (X - ax) * ux + (Y - ay) * uy
        n = -(X - ax) * uy + (Y - ay) * ux
        return t, n

    def mask(X, Y, Z):
        t, n = frame(X, Y)
        fold = 0.35 * np.sin(t * 2.2)
        inside = (t >= 0) & (t <= L) & (np.abs(n - fold) < thick)
        if tied:
            h = np.clip((z_top - Z) / max(z_top - tied, 1e-3), 0, 1)
            w = L * 0.5 * (1 - 0.8 * np.clip((Z - z_bot) / max(tied - z_bot, 1e-3), 0, 1))
            gap = np.where(Z < tied, (t > w * 0.5) & (t < L - w * 0.5), False)
            inside = inside & ~gap & (h >= 0)
        return inside

    def tone(X, Y, Z):
        t, _n = frame(X, Y)
        return 0.45 * np.cos(t * 2.2) - 0.1

    box = (lo[0], hi[0], lo[1], hi[1], z_bot, z_top)
    fill(m, box, material, mask, tone)
    fill(m, box, fringe, lambda X, Y, Z: mask(X, Y, Z) & (Z < z_bot + 0.8), tone=0.2)
    fill(m, box, fringe, lambda X, Y, Z: mask(X, Y, Z) & (Z > z_top - 0.7), tone=0.0)
