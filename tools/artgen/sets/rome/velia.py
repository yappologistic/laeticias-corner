"""The Velia and the Colosseum valley (rome.md §2.3 D6, §3.2): the Amphitheatrum Flavium at
s = 0.6, the Colossus of the Sun on its new base, the Meta Sudans, the Arch of Titus on the
Via Sacra, and the Temple of Venus and Roma as Hadrian's building site."""

import math

import numpy as np

import materials as M
import relief_roman as RR
import roman as RM
from arch import ellipsoid, fill, halo, revolve, rod, slab
from setbuild import Landmark
from sets.rome.common import LAMP, S6, S65, SUN_GOD, T, drums, paving, referrer, scaffold, torch, treadwheel_crane
from voxel import hash01, value_noise

ref = referrer("sets.rome.velia")


# ---------------------------------------------------------------- the Colosseum

def colosseum(m):
    """The Flavian amphitheatre (rome.md §3.1): an ellipse 188 x 156 m and 48.5 m high, the long
    axis east-west. Three storeys of 80 arches framed by Tuscan, Ionic and Corinthian half
    columns, statues in the arches of the second and third, an attic with Corinthian pilasters,
    small windows in alternate bays and the corbels and masts of the awning; four axial
    entrances (the north one the emperor's), numbered public arches. Inside: ambulatories,
    the cavea rising in marble and travertine tiers with stairs and vomitoria, the colonnade of
    the top gallery under its roof, the marble podium round the sand of the arena, and on the
    north side the awning partly drawn."""
    S = S6
    cx, cy = 12 * T, 14 * T
    a, b = S.h(156) / 2 - 1.5, S.h(188) / 2 - 1.5           # semi-axes along x (N-S) and y (E-W)
    el = RM.Ellipse(cx, cy, a, b)
    z0 = S.v(1.0)
    # The travertine platform with two steps round the building.
    for i, (grow, zz) in enumerate(((5.0, 0.0), (2.5, z0 * 0.5))):
        fill(m, (cx - a - grow, cx + a + grow, cy - b - grow, cy + b + grow, zz, zz + z0 * 0.5), "travertine",
             lambda X, Y, Z, g=grow: np.hypot((X - cx) / (a + g), (Y - cy) / (b + g)) <= 1,
             tone=M.plus(M.paving(5.0, 3.5, 41 + i), lambda X, Y, Z, zz=zz: 0.3 * (Z > zz + z0 * 0.5 - 0.5)))
    thick = S.h(2.6)
    storeys = [RM.Storey(S.v(10.5), "arcade", "tuscan", (0.62, 0.66), numbers=True),
               RM.Storey(S.v(11.85), "arcade", "ionic", (0.6, 0.6), statues=True),
               RM.Storey(S.v(11.6), "arcade", "corinthian", (0.6, 0.6), statues=True),
               RM.Storey(S.v(14.45), "attic", "corinthian", (0.2, 0.5), masts=3)]
    top = RM.ring_facade(m, el, z0, storeys, 80, thick, S, gaps=(0, 20, 40, 60), phase=0.5, seed=7)
    z1 = z0 + storeys[0].h
    z2 = z1 + storeys[1].h
    z3 = z2 + storeys[2].h
    # Ambulatory behind the façade: floors at each storey and the inner wall of travertine and
    # tufa with its own arches in shadow.
    amb = S.h(5.0)
    core_out = RM.Ellipse(cx, cy, a - thick - amb, b - thick - amb)

    def ring(el_o, el_i):
        def mk(X, Y, Z):
            ro = np.hypot((X - cx) / el_o.a, (Y - cy) / el_o.b)
            ri = np.hypot((X - cx) / el_i.a, (Y - cy) / el_i.b) if el_i else 2.0
            return (ro <= 1) & (ri > 1)
        return mk
    el_wall = RM.Ellipse(cx, cy, a - thick + 0.2, b - thick + 0.2)
    for zz in (z0, z1, z2):
        fill(m, (cx - a, cx + a, cy - b, cy + b, zz - 0.8, zz), "travertine", ring(el_wall, core_out), tone=-0.3)
    # The core under the cavea: solid, faced with the inner arcades (dark recesses).
    arena = RM.Ellipse(cx, cy, S.h(54) / 2, S.h(86) / 2)
    podium = RM.Ellipse(cx, cy, arena.a + S.h(3.0), arena.b + S.h(3.0))
    gallery_in = RM.Ellipse(cx, cy, a - thick - S.h(7.0), b - thick - S.h(7.0))
    z_pod = S.v(4.0)
    zc_top = z3 - S.v(1.0)

    def core(X, Y, Z):
        ro = np.hypot((X - cx) / core_out.a, (Y - cy) / core_out.b)
        rp = np.hypot((X - cx) / podium.a, (Y - cy) / podium.b)
        rg = np.hypot((X - cx) / gallery_in.a, (Y - cy) / gallery_in.b)
        f = np.clip((rp - 1) / np.maximum((rp - 1) + (1 - rg), 1e-3), 0, 1)    # under the sloping cavea
        lim = np.where(rg < 1, z_pod + (zc_top - z_pod) * f - 1.0, zc_top)
        return (ro <= 1) & (rp > 1) & (Z < lim)
    fill(m, (cx - a, cx + a, cy - b, cy + b, 0.0, zc_top), "tufa", core,
         tone=lambda X, Y, Z: RM.brick(5)(X, Y, Z) * 0.3 - 0.2)
    RM.ring_facade(m, RM.Ellipse(cx, cy, core_out.a, core_out.b), z0,
          [RM.Storey(storeys[0].h, "arcade", "tuscan", (0.55, 0.62), material="tufa"),
           RM.Storey(storeys[1].h, "arcade", "tuscan", (0.5, 0.6), material="tufa"),
           RM.Storey(storeys[2].h - S.v(1.0), "arcade", "tuscan", (0.5, 0.6), material="tufa")],
          80, S.h(2.0), S, gaps=(0, 20, 40, 60), phase=0.5, seed=9)
    # The cavea: marble tiers from the podium to the top gallery, travertine above.
    RM.cavea(m, podium, gallery_in, z_pod + 1.0, zc_top, material="marble", upper_mat="travertine", bands=3,
             aisles=40, seed=3)
    # The podium wall round the arena, faced with marble, a bronze railing along its top.
    fill(m, (cx - podium.a, cx + podium.a, cy - podium.b, cy + podium.b, 0.0, z_pod + 1.0), "marble",
         lambda X, Y, Z: (np.hypot((X - cx) / podium.a, (Y - cy) / podium.b) <= 1) &
         (np.hypot((X - cx) / (arena.a + 0.1), (Y - cy) / (arena.b + 0.1)) > 1),
         tone=RM.marble_veneer(5, 5.0, 2.5))
    fill(m, (cx - podium.a, cx + podium.a, cy - podium.b, cy + podium.b, z_pod + 1.0, z_pod + 2.4), "bronze",
         lambda X, Y, Z: (np.abs(np.hypot((X - cx) / (arena.a + 0.6), (Y - cy) / (arena.b + 0.6)) - 1) < 0.006) &
         ((((np.arctan2(Y - cy, X - cx) * 90) % 1.0) < 0.3) | (Z > z_pod + 2.0)), tone=0.3)
    # The arena: sand over the wooden floor, raked lines, a few trapdoor outlines.
    fill(m, (cx - arena.a, cx + arena.a, cy - arena.b, cy + arena.b, 0.0, 1.0), "poros",
         lambda X, Y, Z: np.hypot((X - cx) / arena.a, (Y - cy) / arena.b) <= 1,
         tone=lambda X, Y, Z: (value_noise(X * 2, Y * 2, Z, 2.0, 5) - 0.5) * 0.6 + 0.25 * (np.sin(Y * 1.3) > 0.85)
         - 0.5 * ((np.abs(X - cx) < 18) & (((Y - cy) % 12.0) < 0.5) & (np.abs(Y - cy) < 60)))
    # The top gallery: a floor over the third storey, a colonnade on its inner edge and a roof
    # sloping from the attic down to the columns.
    zg = z3
    fill(m, (cx - a, cx + a, cy - b, cy + b, zg - 1.0, zg), "travertine", ring(el_wall, gallery_in), tone=0.1)
    ncol = 160
    col_el = RM.Ellipse(cx, cy, gallery_in.a + 1.2, gallery_in.b + 1.2)
    hcol = top - zg - S.v(2.0)

    def colonnade(X, Y, Z):
        th, s, d = col_el.polar(X, Y)
        u = (s / (col_el.L / ncol)) % 1.0
        so = (np.minimum(u, 1 - u)) * col_el.L / ncol
        return (so ** 2 + d ** 2 < 0.55 ** 2) & (Z >= zg) & (Z < zg + hcol)
    fill(m, (cx - a, cx + a, cy - b, cy + b, zg, zg + hcol), "marble", colonnade, tone=0.2)

    def roof(X, Y, Z):
        ro = np.hypot((X - cx) / (a - thick + 0.5), (Y - cy) / (b - thick + 0.5))
        ri = np.hypot((X - cx) / gallery_in.a, (Y - cy) / gallery_in.b)
        f = np.clip((ri - 1) / np.maximum((ri - 1) + (1 - ro), 1e-3), 0, 1)
        zr = zg + hcol + f * (top - 1.5 - zg - hcol)
        return (ro <= 1) & (ri > 0.995) & (Z < zr + 1.0) & (Z >= zr - 0.5)
    fill(m, (cx - a, cx + a, cy - b, cy + b, zg + hcol - 1, top), "terracotta", roof,
         tone=lambda X, Y, Z: 0.3 * ((np.arctan2(Y - cy, X - cx) * 140) % 1.0 < 0.35) - 0.2)
    # The emperor's box on the north side of the minor axis (a canopied platform).
    bx = cx - podium.a - 2.0
    slab(m, bx - 6.0, bx + 1.0, cy - 9.0, cy + 9.0, z_pod, z_pod + 6.0, "marble", tone=0.25)
    for yy in (cy - 8.0, cy + 8.0):
        for xx in (bx - 5.0, bx):
            rod(m, (xx, yy, z_pod + 6.0), (xx, yy, z_pod + 18.0), 0.5, "porphyry", tone=0.3)
    slab(m, bx - 6.0, bx + 1.0, cy - 9.0, cy + 9.0, z_pod + 18.0, z_pod + 19.5, "purple", tone=0.2)
    # The awning (velarium) partly drawn over the north side: strips of sailcloth from the top
    # of the attic down toward the arena, ropes to the masts.
    def sails(X, Y, Z):
        th = np.arctan2((Y - cy) / b, (X - cx) / a)
        north = np.abs(th) > 2.2
        ro = np.hypot((X - cx) / (a - thick), (Y - cy) / (b - thick))
        f = np.clip((1 - ro) / 0.2, 0, 1)
        zs = top + 3.0 - f * 9.0 - 1.2 * np.sin(np.pi * f) * (np.cos(th * 40) > 0)
        strip = ((th * 40 / np.pi) % 1.0) < 0.93
        return north & strip & (ro <= 1) & (ro > 0.8) & (np.abs(Z - zs) < 0.45)
    fill(m, (cx - a, cx + a, cy - b, cy + b, top - 12.0, top + 5.0), "linen", sails,
         tone=lambda X, Y, Z: 0.1 + 0.3 * (((np.arctan2((Y - cy) / b, (X - cx) / a) * 20 / np.pi) % 1.0) < 0.5)
         - 0.5 * (((np.arctan2((Y - cy) / b, (X - cx) / a) * 40 / np.pi) % 1.0) > 0.86))
    # Torches at the axial entrances for game nights.
    for th in (0.0, math.pi / 2):
        for dth in (-0.06, 0.06):
            x, y = el.point(th + dth, 1.5)
            torch(m, x, y, z0, h=7.0, strength=0.8)


# ---------------------------------------------------------------- the Colossus and the Meta Sudans

def colossus(m):
    """The Colossus: Nero's bronze statue remade as the Sun, about 30-35 m tall (here about 32 m
    with its crown of rays), moved by Hadrian next to the amphitheatre on a tall base of brick
    faced with marble."""
    S = S65
    c = 1.5 * T
    bw = S.h(15.0) / 2
    bh = S.v(6.0)
    slab(m, c - bw - 1, c + bw + 1, c - bw - 1, c + bw + 1, 0.0, 1.5, "marble", tone=0.25)
    slab(m, c - bw, c + bw, c - bw, c + bw, 1.5, bh, "marble", tone=RM.marble_veneer(3, 7.0, 6.0))
    RM.cornice(m, (c - bw, c + bw, c - bw, c + bw), bh, 1.6, 1.0)
    RM.inscription(m, "+x", (c - bw, c + bw, c - bw, c + bw), 3.0, 2 * bw - 3.0, bh * 0.45, bh * 0.75, "gold", rows=2)
    RM.statue(m, c, c, bh + 1.6, S.v(32.0) - S.v(2.5), SUN_GOD, material="bronze_cast", keep=("gold",))
    halo(m, c, c, bh + S.v(29.0), 22.0, LAMP, 0.45)


def meta_sudans(m):
    """The Meta Sudans: a tall cone of brick faced with marble, water welling from its top and
    running down its sides into a wide round basin."""
    S = S65
    c = T
    rb = S.h(16.0) / 2
    revolve(m, c, c, 0.0, 2.0, lambda t: rb, "marble", tone=0.2)
    fill(m, (c - rb, c + rb, c - rb, c + rb, 1.0, 2.2), "water",
         lambda X, Y, Z: np.hypot(X - c, Y - c) < rb - 1.0, tone=lambda X, Y, Z: 0.3 * (np.sin((X + Y) * 2) > 0.8))
    h = S.v(17.0)
    rc = S.h(5.0) / 2
    revolve(m, c, c, 2.0, 2.0 + h * 0.3, lambda t: rc * (1.25 - 0.1 * t), "marble", tone=RM.marble_veneer(5, 4.0, 4.0))
    for i in range(8):     # niches round the drum
        a = i * math.pi / 4
        x, y = c + math.cos(a) * rc * 1.15, c + math.sin(a) * rc * 1.15
        fill(m, (x - 1.2, x + 1.2, y - 1.2, y + 1.2, 4.0, 4.0 + h * 0.18), "ink",
             lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) < 1.0, tone=0.0)
    # The cone: a broad concave meta of marble-faced brick (QA4 V-A-010: stripes made it read
    # as a lighthouse), crowned by a bronze bud from which the water wells.
    revolve(m, c, c, 2.0 + h * 0.3, 2.0 + h, lambda t: rc * (1.05 - 0.85 * t ** 0.8), "marble",
            tone=lambda X, Y, Z: RM.marble_veneer(6, 5.0, 4.0)(X, Y, Z) * 0.5 - 0.1)
    revolve(m, c, c, 2.0 + h, 2.0 + h + 2.4, lambda t: 0.9 * np.sin(np.pi * np.clip(t, 0.05, 1.0)) + 0.2, "bronze",
            tone=0.3)
    # A film of water glistening down the cone's foot into the basin (no stripes: QA4 V-A-010).
    fill(m, (c - rc * 1.4, c + rc * 1.4, c - rc * 1.4, c + rc * 1.4, 2.0 + h * 0.3, 2.0 + h * 0.42), "water",
         lambda X, Y, Z: np.abs(np.hypot(X - c, Y - c) - rc * 1.05 - 0.2) < 0.3, tone=0.3)
    ellipsoid(m, (c, c, 2.0 + h + 0.6), (1.4, 1.4, 1.0), "water", 0.5)


# ---------------------------------------------------------------- the Arch of Titus

def arch_titus(m):
    """The Arch of Titus (after AD 81) on the Via Sacra at the top of the Velia: a single bay of
    Pentelic marble with Composite half columns, Victories in the spandrels, the attic with its
    inscription to the deified Titus, a bronze chariot group on top; inside the passage the
    two panels, the spoils of Jerusalem with the menorah and Titus's triumph. Drawn at
    s = 0.75 so the passage is one walk tile wide with true proportions (rome.md asks 1 x 2)."""
    from arch import Scale
    S = Scale(0.75)
    pier = (S.h(13.5) - T) / 2
    box = (T - pier, 2 * T + pier, 2.0, T - 2.0)
    size = (int(3 * T * 2), int(S.v(3.0) * 2))
    RM.triumphal_arch(m, box, "+y", S, z0=0.0, bays=1, order=RM.ROrder("composite", D=0.85, H=8.4),
                      material="marble", relief=[RR.spoils_image(*size), RR.triumph_image(*size)], seed=31,
                      pier=pier)


# ---------------------------------------------------------------- the Temple of Venus and Roma

def venus_roma(m):
    """Hadrian's Temple of Venus and Roma as a building site in 126 (begun c. 121, dedicated
    135): the vast platform on the Velia faced with marble, two cellae back to back (Venus
    facing east, Roma west) with their walls rising unevenly in brick-faced concrete, part of
    the white marble Corinthian peristyle standing on the long south side, the rest stumps
    and bases; treadwheel cranes, scaffolds, column drums and capitals in rows on the
    platform, blocks and a marble-cutters' shed, the double colonnade of grey granite begun
    along the precinct's edge."""
    S = S65
    W, D = 18 * T, 12 * T                       # y (E-W) and x (N-S) extents
    zp = S.v(3.0)
    # The platform with steps on the long sides.
    slab(m, 4.0, D - 4.0, 4.0, W - 4.0, 0.0, zp, "travertine", tone=RM.travertine(3.0, 7.0, 51))
    paving(m, (6.0, D - 6.0, 6.0, W - 6.0), zp - 0.5, zp, "marble", 7.0, 5.0, 52)
    for i in range(4):
        slab(m, D - 4.0 + i * 0.0, D - 4.0 + (i + 1) * 0.9, 10.0, W - 10.0, 0.0, zp - i * zp / 4, "marble",
             tone=lambda X, Y, Z: 0.35 * (Z > zp - 1))
    # The temple stylobate in the middle.
    tx0, tx1, ty0, ty1 = 2.6 * T, D - 2.6 * T, 2.0 * T, W - 2.0 * T
    slab(m, tx0, tx1, ty0, ty1, zp, zp + S.v(1.4), "marble", tone=M.ashlar(2.4, 8.0, 53, spread=0.3))
    zs = zp + S.v(1.4)
    o = RM.ROrder("corinthian", D=1.8, H=15.0)
    r = o.r(S)
    xs = list(np.linspace(tx0 + r * 1.8, tx1 - r * 1.8, 10))
    ys = list(np.linspace(ty0 + r * 1.8, ty1 - r * 1.8, 20))
    H = S.v(o.H)
    for j, y in enumerate(ys):
        for x in (xs[0], xs[-1]):
            south = x == xs[-1]
            if south and 4 <= j <= 12:              # the finished stretch of the south flank
                RM.column(m, x, y, zs, o, S, seed=j)
            elif hash01(j, int(x), 61) < 0.55:      # stumps of drums
                n = 1 + int(hash01(j, int(x), 62) * 3)
                fill(m, (x - r, x + r, y - r, y + r, zs, zs + n * S.v(1.4)), "marble",
                     lambda X, Y, Z, x=x, y=y: np.hypot(X - x, Y - y) <= r * 0.95,
                     tone=lambda X, Y, Z: -0.45 * (((Z - zs) % S.v(1.4)) < 0.4))
    for x in xs[1:-1]:
        for y in (ys[0], ys[-1]):
            fill(m, (x - r * 1.4, x + r * 1.4, y - r * 1.4, y + r * 1.4, zs, zs + 1.5), "marble", tone=0.3)
    # Architrave blocks on the finished stretch.
    slab(m, xs[-1] - r * 1.2, xs[-1] + r * 1.2, ys[4] - r, ys[12] + r, zs + H, zs + H + S.v(1.6), "marble",
         tone=M.ashlar(S.v(1.6), 14.0, 63, spread=0.2))
    # The two cellae back to back, walls rising in brick-faced concrete, the apse-less fronts.
    cx0, cx1 = tx0 + 2.4 * T * 0.55, tx1 - 2.4 * T * 0.55
    mid = W / 2
    wt = S.h(3.0)
    for (y0, y1, h) in ((ty0 + 1.6 * T, mid - 0.8, H * 0.75), (mid + 0.8, ty1 - 1.6 * T, H * 0.5)):
        for wb, hh in (((cx0, cx0 + wt, y0, y1), h), ((cx1 - wt, cx1, y0, y1), h * 0.85),
                       ((cx0, cx1, y0, y0 + wt) if y0 < mid else (cx0, cx1, y1 - wt, y1), h * 0.55)):
            def ragged(X, Y, Z, hh=hh):
                return Z < zs + hh - 6.0 * value_noise(X * 0.3, Y * 0.3, 0 * Z, 5.0, 64)
            fill(m, (*wb, zs, zs + hh), "brick", ragged, tone=RM.brick(65))
        scaffold(m, cx0 - 4.0, cx0 - 1.0, y0 + 6.0, y1 - 6.0, zs, zs + h + 6.0, decks=4)
    slab(m, cx0, cx1, mid - 0.8, mid + 0.8, zs, zs + H * 0.65, "brick", tone=RM.brick(66))
    # Cranes, drums and capitals in rows, blocks, the cutters' shed.
    treadwheel_crane(m, xs[-1] - 10.0, ys[14] + 4.0, zs, S.v(22.0), along="x", load="marble")
    treadwheel_crane(m, cx0 - 8.0, ys[3], zs, S.v(20.0), along="x", load="marble", swing=2.0)
    for i in range(3):
        drums(m, tx1 - 7.0 - i * 4.5, ty0 + 8.0, zs, r * 0.9, 5, seed=i, along="y")
    for i in range(5):
        xx, yy = cx1 + 6.0 + (i % 2) * 6.0, mid - 30.0 + i * 12.0
        fill(m, (xx - 3, xx + 3, yy - 3, yy + 3, zs, zs + 4.5), "marble",
             lambda X, Y, Z, xx=xx, yy=yy: np.maximum(np.abs(X - xx), np.abs(Y - yy)) < 1.6 + 1.2 * (Z - zs) / 4.5,
             tone=lambda X, Y, Z: 0.25 - 0.5 * (np.cos((np.arctan2(Y, X)) * 10) > 0.6))
    for i in range(6):
        slab(m, 8.0 + i * 5.0, 12.0 + i * 5.0, W - 16.0, W - 9.0, zp, zp + 3.0 + (i % 3), "marble",
             tone=lambda X, Y, Z: (value_noise(X, Y, Z, 2.0, 67) - 0.5) * 0.6)
    slab(m, D - 20.0, D - 8.0, 10.0, 26.0, zp, zp + 7.0, "wood", tone=M.timber("y", 68))
    slab(m, D - 21.0, D - 7.0, 9.0, 27.0, zp + 7.0, zp + 8.0, "terracotta", tone=0.1)


LANDMARKS = {
    "rome.colosseum": Landmark((24, 28), (0, 168), ref("colosseum"), district=4,
                               slots={"entrance": [{"t": [24, 13], "face": "-x"}, {"t": [24, 14], "face": "-x"}],
                                      "emperor": [{"t": [-1, 14], "face": "+x"}]}),
    "rome.colossus": Landmark((3, 3), (0, 168), ref("colossus"), district=4),
    "rome.meta_sudans": Landmark((2, 2), (0, 64), ref("meta_sudans"), district=4,
                                 slots={"fill": [{"t": [2, 1], "face": "-x"}]}),
    "rome.arch_titus": Landmark((3, 1), (0, 80), ref("arch_titus"), district=4, walk=[(1, 0)]),
    "rome.venus_roma": Landmark((12, 18), (0, 112), ref("venus_roma"), district=4,
                                slots={"work": [{"t": [12, 6], "face": "-x"}, {"t": [12, 11], "face": "-x"}]}),
}

INFO = {
    "rome.colosseum": ("Amphitheatrum Flavium (Colosseum)", 0.6, 290, "BSG", "colosseum"),
    "rome.colossus": ("Colossus of the Sun", 0.65, 250, "BSG", "colossus"),
    "rome.meta_sudans": ("Meta Sudans", 0.65, 110, "BS", "meta_sudans"),
    "rome.arch_titus": ("Arch of Titus", 0.75, 100, "BS", "arch_titus"),
    "rome.venus_roma": ("Temple of Venus and Roma (building site)", 0.65, 150, "BS", "venus_roma"),
}
