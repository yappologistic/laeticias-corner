"""The southern Campus Martius (rome.md §2.3 D14, §3.2): Hadrian's Pantheon, newly finished,
facing north onto its colonnaded forecourt, the Baths of Agrippa, the Theatre of Marcellus at
s = 0.5 with its arcaded curve to the south-west, the Porticus Octaviae, the Temple of Matidia,
the Saepta Iulia, the Iseum, the Stadium of Domitian and the Theatre of Pompey."""

import math

import numpy as np

import roman as RM
from arch import carve, fill, halo, revolve, slab
from setbuild import Landmark
from sets.rome.common import LAMP, PANTHEON_GREY, PANTHEON_PINK, PORTICO, S5, S65, T, TOGATE, GODDESS, lamp, paving, referrer
from voxel import value_noise

ref = referrer("sets.rome.campus")


# ---------------------------------------------------------------- the Pantheon

def pantheon(m):
    """The Pantheon (rome.md §3.1): the brick rotunda with its three cornices and relieving
    arches, the stepped rings round the foot of the dome, the dome 43.3 m across covered with
    gilded bronze tiles, the oculus open to the sky (the coffered inside seen through it), the
    high intermediate block with its own pediment, and the portico facing north: sixteen
    monolithic Corinthian columns (eight across the front of grey granite, the rest pink) with
    white marble bases and capitals, the inscription of Agrippa kept by Hadrian, a pediment
    with a bronze eagle and wreath, bronze doors between niches."""
    S = S65
    cx, cy = 5 * T + 72.0, 72.0
    R = 71.5                                         # outer radius of the drum (55.7 m wall to wall)
    Ri = S.h(43.3) / 2
    zb = 0.0
    # The drum: brick, a marble foot, three cornices, relieving arches traced in the brick.
    revolve(m, cx, cy, zb, zb + 2.0, lambda t: R + 1.0, "marble", tone=0.25)

    def drum_tone(X, Y, Z):
        a = np.arctan2(Y - cy, X - cx) * R
        arch = np.abs(np.hypot((a % 36.0) - 18.0, (Z % 34.0) - 8.0) - 14.0) < 0.6
        return RM.brick(71)(X, Y, Z) - 0.5 * arch
    zc = [S.v(12.0), S.v(21.5), S.v(29.0)]
    revolve(m, cx, cy, zb + 2.0, zc[2], lambda t: R, "brick", tone=drum_tone)
    carve(m, (cx - Ri, cx + Ri, cy - Ri, cy + Ri, zb + 2.0, zc[2] - 4.0),
          lambda X, Y, Z: np.hypot(X - cx, Y - cy) < Ri)
    for i, z in enumerate(zc):
        revolve(m, cx, cy, z - 1.6, z, lambda t, i=i: R + 0.6 + 0.9 * t, "marble",
                tone=lambda X, Y, Z, z=z: 0.35 * (Z > z - 0.5) - 0.2 * ((Z % 0.8) < 0.3))
    # Interior floor of coloured marble (porphyry, giallo and granite circles in squares).
    fill(m, (cx - Ri, cx + Ri, cy - Ri, cy + Ri, zb, zb + 1.0), "giallo",
         lambda X, Y, Z: np.hypot(X - cx, Y - cy) < Ri, tone=0.0)
    fill(m, (cx - Ri, cx + Ri, cy - Ri, cy + Ri, zb, zb + 1.0), "porphyry",
         lambda X, Y, Z: (np.hypot(((X - cx) % 12.0) - 6.0, ((Y - cy) % 12.0) - 6.0) < 3.0) &
         (np.hypot(X - cx, Y - cy) < Ri), tone=0.1, only_solid=True)
    # The dome: step rings round its foot, gilded bronze tiles, the oculus.
    zd = zc[2]
    RM.dome(m, cx, cy, zd - 4.0, R - 1.5, material="gilt", rise=S.v(43.3) - zd + 4.0, thick=6.0, steps=7,
            step_h=2.6, step_mat="whitewash", oculus=S.h(9.0) / 2, inner="whitewash", coffers=True, tiles=True,
            seed=72)
    halo(m, cx, cy, zb + 6.0, 34.0, LAMP, 0.35)       # the oculus's light on the floor (card)
    # The intermediate block with its upper pediment, faced in brick with marble cornices.
    pw = S.h(33.1)
    y0, y1 = cy - pw / 2 - 1.0, cy + pw / 2 + 1.0
    bx0, bx1 = 5 * T - S.h(6.0), 5 * T + 14.0
    blk = (bx0, bx1, y0, y1)
    RM.wall(m, blk, zb, S.v(25.0), "brick", 73)
    for z in zc[:2]:
        RM.cornice(m, blk, z - 1.6, 1.6, 0.8, "marble")
    zbt = S.v(25.0)
    rise2 = (y1 - y0) / 2 * 0.36
    RM.pediment(m, "-x", (bx0 - 1.0, bx1, y0 - 1.0, y1 + 1.0), zbt, rise2, S, "marble")
    fill(m, (bx0, bx1 - 1.0, y0, y1, zbt - 0.5, zbt + rise2),
         "marble", lambda X, Y, Z: Z < zbt + rise2 * (1 - np.abs(Y - cy) / ((y1 - y0) / 2)) - 1.0, tone=-0.3)
    RM.gable(m, (bx0 - 1.0, bx1, y0 - 1.0, y1 + 1.0), zbt, rise2, "x", material="bronze_cast", seed=74)
    # The portico: 8 grey columns across, two rows of 4 pink behind making three aisles.
    px1 = bx0
    px0 = px1 - S.h(15.5)
    zp = S.v(1.3)
    for i in range(5):        # steps up to the portico floor
        slab(m, px0 - 6.0 + i * 1.2, px1, y0 + 1.0, y1 - 1.0, i * zp / 5, (i + 1) * zp / 5, "marble",
             tone=lambda X, Y, Z: 0.35 * ((Z % (zp / 5)) > zp / 5 - 0.4))
    paving(m, (px0, px1, y0 + 1.0, y1 - 1.0), zp - 0.5, zp, "marble", 6.0, 6.0, 75)
    o = PANTHEON_GREY
    r = o.r(S)
    ys = list(np.linspace(y0 + r * 1.9, y1 - r * 1.9, 8))
    xf = px0 + r * 1.9
    for j, y in enumerate(ys):
        RM.column(m, xf, y, zp, o, S, seed=j)
    for row, xr in enumerate((xf + (px1 - xf) * 0.42, xf + (px1 - xf) * 0.8)):
        for j in (0, 2, 5, 7):
            RM.column(m, xr, ys[j], zp, PANTHEON_PINK, S, seed=10 + j + row)
    # The portico's back wall with the bronze doors between niches (statues of Augustus and
    # Agrippa stood in them).
    back = (px1 - 2.0, px1, ys[2] - r, ys[5] + r)
    RM.wall(m, back, zp, zp + S.v(14.15), "veneer", 76, "marble")
    dw = S.h(7.3)
    fill(m, (px1 - 2.6, px1 - 0.6, cy - dw / 2, cy + dw / 2, zp, zp + S.v(12.0)), "bronze",
         tone=lambda X, Y, Z: 0.4 * (((Z - zp) % 5.0) < 0.6) + 0.3 * ((((Y - cy) % 4.0) < 0.5)) - 0.15)
    for yy in (ys[1] + 2.0, ys[6] - 2.0):
        RM.opening(m, "-x", (px1 - 3.0, px1, yy - 6.0, yy + 6.0), 3.0, 6.0, zp + 2.0, zp + 14.0, 1.8,
                   back="marble")
        RM.statue(m, px1 - 1.6, yy, zp + 2.0, 13.0, TOGATE, material="bronze_cast", keep=())
    # Entablature with the inscription, pediment with the eagle, the roof on bronze trusses
    # (the roof tiles bronze too).
    span = (px0 + r * 0.5, px1, y0, y1)
    ent = o.entablature(S)
    zt = zp + S.v(o.H)
    ze = RM.entablature(m, span, zt, ent, faces=("-x", "+y", "-y"), material="marble", seed=77, inscribe=("-x",))
    rise = (y1 - y0) / 2 * 0.38
    rb = (span[0] - 1.6, span[1], y0 - 1.6, y1 + 1.6)
    fill(m, (*span, ze - 0.5, ze + rise), "marble",
         lambda X, Y, Z: Z < ze + rise * (1 - np.abs(Y - cy) / ((y1 - y0) / 2)) - 1.6, tone=-0.3)
    RM.gable(m, rb, ze, rise, "x", material="bronze_cast", seed=78)
    RM.pediment(m, "-x", rb, ze, rise, S, "marble", subject="eagle")
    lamp(m, px1 - 3.0, cy - dw / 2 - 2.0, zp + 8.0, 0.5)
    lamp(m, px1 - 3.0, cy + dw / 2 + 2.0, zp + 8.0, 0.5)


def pantheon_court(m):
    """The forecourt north of the Pantheon: a long paved square closed by colonnades of grey
    granite on three sides, an arch at its north end."""
    S = S65
    W, D = 13 * T, 8 * T
    paving(m, (0.0, D, 0.0, W), 0.0, 1.0, "travertine", 6.0, 4.5, 81)
    for (a, b, front, depth) in (((2.0, 8.0), (D - 4.0, 8.0), "-y", 12.0), ((2.0, W - 8.0), (D - 4.0, W - 8.0), "+y", 12.0)):
        RM.colonnade(m, a, b, 1.0, 9, RM.ROrder("corinthian", D=0.9, H=8.0, shaft="granite", fluted=False), S, depth,
                     {"-y": "+y", "+y": "-y"}[front], roof="terracotta", seed=82)
    RM.colonnade(m, (8.0, 20.0), (8.0, W - 20.0), 1.0, 10, RM.ROrder("corinthian", D=0.9, H=8.0, shaft="granite",
                                                                      fluted=False), S, 7.0, "+x", seed=83)
    RM.statue(m, D / 2, W / 2, 1.0, 18.0, TOGATE, material="bronze_cast", base=(5.0, 6.0))


# ---------------------------------------------------------------- the Baths of Agrippa

def agrippa_baths(m):
    """The Baths of Agrippa, restored after the fire of 80: a great round domed hall in the
    middle, barrel-vaulted halls to either side with tall arched windows of glass, a palaestra
    court with a colonnade on the south (in view), brick walls, the furnace flues smoking."""
    S = S65
    W, D = 13 * T, 9 * T
    cx, cy = 3.6 * T, W / 2
    RM.wall(m, (8.0, 6 * T, 10.0, W - 10.0), 0.0, S.v(14.0), "brick", 91)
    for s0 in np.arange(10.0, W - 30.0, 18.0):
        RM.window(m, "+x", (8.0, 6 * T, 10.0, W - 10.0), s0, 6.0, S.v(4.0), S.v(5.0), arched=True, glass=True)
    RM.vault_roof(m, (8.0, 6 * T, 10.0, cy - 22.0), S.v(14.0), "y", "whitewash", tiles=True, seed=92)
    RM.vault_roof(m, (8.0, 6 * T, cy + 22.0, W - 10.0), S.v(14.0), "y", "whitewash", tiles=True, seed=93)
    rr = S.h(25.0) / 2
    revolve(m, cx, cy, 0.0, S.v(18.0), lambda t: rr, "brick", tone=RM.brick(94))
    RM.cornice(m, (cx - rr, cx + rr, cy - rr, cy + rr), S.v(18.0) - 1.4, 1.4, 0.6)
    RM.dome(m, cx, cy, S.v(18.0), rr - 0.5, material="whitewash", rise=rr * 0.85, thick=3.0, oculus=3.0,
            tiles=False, coffers=False, seed=95)
    # The palaestra: a sanded court with a colonnade before the south front.
    fill(m, (6 * T, D - 4.0, 12.0, W - 12.0, 0.0, 0.8), "poros",
         tone=lambda X, Y, Z: (value_noise(X, Y, Z, 3.0, 96) - 0.5) * 0.5)
    RM.colonnade(m, (D - 8.0, 14.0), (D - 8.0, W - 14.0), 0.0, 13, PORTICO, S, 8.0, "+x", seed=97)
    for x, y in ((14.0, 12.0), (14.0, W - 12.0), (60.0, 14.0)):
        slab(m, x - 2.0, x + 2.0, y - 2.0, y + 2.0, 0.0, S.v(17.0), "brick", tone=RM.brick(98))
        fill(m, (x - 1.0, x + 1.0, y - 1.0, y + 1.0, S.v(17.0) - 2.0, S.v(17.0)), "ink")


# ---------------------------------------------------------------- the Theatre of Marcellus

def marcellus(m):
    """The Theatre of Marcellus (s = 0.5): the travertine curve of the cavea facing south-west
    in two arcaded storeys, Doric then Ionic half columns, under a closed attic with
    Corinthian pilasters; inside the stepped cavea, the orchestra and the stage with its
    columned scaenae frons; the stage building's high back wall to the north-east."""
    S = S5
    W, D = 16 * T, 12 * T
    R = 96.0
    cx, cy = R * 0.707 + 2.0, R * 0.707 + 2.0 + (W - D) * 0.5 + 6.0
    el = RM.Ellipse(cx, cy, R, R)
    arc = (-math.pi / 4, 3 * math.pi / 4)
    thick = S.h(3.0)
    storeys = [RM.Storey(S.v(11.0), "arcade", "tuscan", (0.6, 0.62)),
               RM.Storey(S.v(11.0), "arcade", "ionic", (0.58, 0.6)),
               RM.Storey(S.v(10.6), "blind", "corinthian", (0.2, 0.5))]
    top = RM.ring_facade(m, el, 0.0, storeys, 84, thick, S, arc=arc, seed=101, phase=0.5)
    orch = RM.Ellipse(cx, cy, R * 0.3, R * 0.3)
    upper = RM.Ellipse(cx, cy, R - thick - 4.0, R - thick - 4.0)

    def p_(X, Y):     # distance along the axis toward the south-west (negative: the stage side)
        return ((X - cx) + (Y - cy)) / math.sqrt(2)

    def q_(X, Y):
        return ((X - cx) - (Y - cy)) / math.sqrt(2)
    # Solid under the seats, faced inside with dark arches (the ambulatory hidden).
    fill(m, (cx - R, cx + R, cy - R, cy + R, 0.0, top - 6.0), "tufa",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < R - thick - 3.0) & (np.hypot(X - cx, Y - cy) > R * 0.3) &
         (p_(X, Y) > 0) & (Z < 2.0 + (top - 8.0) * np.clip((np.hypot(X - cx, Y - cy) - R * 0.3) / (R * 0.62), 0, 1)),
         tone=-0.2)
    RM.cavea(m, orch, upper, 2.0, top - 6.0, arc=arc, material="marble", upper_mat="travertine", bands=2, aisles=26,
             seed=103)
    # Top gallery roof between attic and seats.
    fill(m, (cx - R, cx + R, cy - R, cy + R, top - 6.0, top - 1.0), "terracotta",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < R - thick + 0.5) & (np.hypot(X - cx, Y - cy) > R - thick - 5.0) &
         (p_(X, Y) > 0) & (Z < top - 6.0 + (np.hypot(X - cx, Y - cy) - (R - thick - 5.0)) * 0.9),
         tone=lambda X, Y, Z: 0.3 * ((np.arctan2(Y - cy, X - cx) * 120) % 1.0 < 0.4) - 0.2)
    # Orchestra paved in coloured marble.
    fill(m, (cx - R * 0.3, cx + R * 0.3, cy - R * 0.3, cy + R * 0.3, 0.0, 1.0), "giallo",
         lambda X, Y, Z: (np.hypot(X - cx, Y - cy) < R * 0.3) & (p_(X, Y) > 0),
         tone=lambda X, Y, Z: -0.4 * ((np.floor((X + Y) / 4.0) % 2) == 0))
    # The stage (pulpitum) and the scaenae frons: three storeys of columns of coloured marble
    # before a wall with three doors, the stage roof, the outer back wall in travertine.
    L = R * 0.95
    fill(m, (cx - R, cx + R, cy - R, cy + R, 0.0, S.v(1.5)), "marble",
         lambda X, Y, Z: (p_(X, Y) <= 0) & (p_(X, Y) > -S.h(8.0)) & (np.abs(q_(X, Y)) < L), tone=0.1)
    fill(m, (cx - R, cx + R, cy - R, cy + R, 0.0, top + 4.0), "travertine",
         lambda X, Y, Z: (p_(X, Y) <= -S.h(8.0)) & (p_(X, Y) > -S.h(13.0)) & (np.abs(q_(X, Y)) < L * 1.04),
         tone=RM.travertine(3.0, 7.0, 104))
    for storey in range(3):
        zz = S.v(1.5) + storey * S.v(8.0)
        for i in range(-6, 7):
            q = i * L / 6.5
            px = -S.h(7.0)
            x = cx + (px + q) / math.sqrt(2)
            y = cy + (px - q) / math.sqrt(2)
            RM.column(m, x, y, zz, RM.ROrder("corinthian", D=0.7, H=7.2, shaft=("giallo", "cipollino", "granite_pink")
                                             [storey], fluted=False), S, seed=i)
    for d in (-1, 0, 1):    # the three doors (valvae) in the stage wall
        q = d * L * 0.4
        px = -S.h(8.0)
        x, y = cx + (px + q) / math.sqrt(2), cy + (px - q) / math.sqrt(2)
        fill(m, (x - 6, x + 6, y - 6, y + 6, S.v(1.5), S.v(1.5) + 14.0), "ink",
             lambda X, Y, Z, x=x, y=y: (np.abs(q_(X, Y) - q) < 3.0) & (np.abs(p_(X, Y) - px) < 1.0), tone=0.0)
    fill(m, (cx - R, cx + R, cy - R, cy + R, top - 2.0, top + 6.0), "terracotta",
         lambda X, Y, Z: (p_(X, Y) <= -S.h(4.0)) & (p_(X, Y) > -S.h(13.0)) & (np.abs(q_(X, Y)) < L * 1.04) &
         (Z < top + 6.0 - (p_(X, Y) + S.h(13.0)) * 0.35), tone=lambda X, Y, Z: 0.3 * ((q_(X, Y) % 2.4) < 0.8) - 0.2)


# ---------------------------------------------------------------- smaller N pieces

def octavia(m):
    """The Porticus Octaviae: a colonnaded precinct with the temples of Jupiter and Juno inside,
    a gateway propylon on the south, Cornelia's seated statue in the portico."""
    S = S65
    W, D = 11 * T, 9 * T
    paving(m, (0.0, D, 0.0, W), 0.0, 1.0, "travertine", 6.0, 4.5, 111)
    o = RM.ROrder("corinthian", D=0.8, H=7.5, shaft="cipollino", fluted=False)
    for a, b, front in (((4.0, 4.0), (4.0, W - 4.0), "+x"), ((D - 6.0, 4.0), (D - 6.0, 60.0), "-x"),
                        ((D - 6.0, W - 60.0), (D - 6.0, W - 4.0), "-x"), ((10.0, 4.0), (D - 10.0, 4.0), "+y"),
                        ((10.0, W - 4.0), (D - 10.0, W - 4.0), "-y")):
        n = max(3, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 9))
        RM.colonnade(m, a, b, 1.0, n, o, S, 6.0, front, seed=112 + n)
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.9, H=8.0), front="+x", cols=6, deep=2,
                            plan="peripteral", podium=2.0, pediment="gods", seed=113), S, (16.0, D - 18.0, 14.0, 74.0), 1.0)
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=0.9, H=8.0), front="+x", cols=6, deep=2,
                            plan="peripteral", podium=2.0, pediment="gods", seed=114), S, (16.0, D - 18.0, W - 74.0, W - 14.0),
              1.0)
    RM.triumphal_arch(m, (D - 14.0, D - 1.0, W / 2 - 22.0, W / 2 + 22.0), "+x", S, z0=1.0, bays=1,
                      order=RM.ROrder("corinthian", D=0.8, H=8.0), quadriga=False, seed=115)
    RM.statue(m, D - 12.0, 30.0, 1.0, 13.0, GODDESS, material="marble", anim="sit", base=(5.0, 4.0))


def matidia(m):
    """Hadrian's temple to his deified mother-in-law Matidia (after 119): a large Corinthian
    temple with columns of cipollino, facing south."""
    S = S65
    RM.temple(m, RM.RTemple(order=RM.ROrder("corinthian", D=1.7, H=17.0, shaft="cipollino", fluted=False),
                            front="+x", cols=8, deep=3, plan="peripteral", podium=3.0, pediment="gods", seed=121),
              S, (2.0, 6 * T - 2.0, 2.0, 6 * T - 2.0))


LANDMARKS = {
    "rome.pantheon": Landmark((14, 9), (0, 160), ref("pantheon"), district=1,
                              slots={"visit": [{"t": [-1, 4], "face": "+x"}, {"t": [-1, 3], "face": "+x"}]}),
    "rome.pantheon_court": Landmark((8, 13), (0, 64), ref("pantheon_court"), district=1),
    "rome.agrippa_baths": Landmark((9, 13), (0, 96), ref("agrippa_baths"), district=1,
                                   slots={"bathe": [{"t": [9, 6], "face": "-x"}, {"t": [9, 7], "face": "-x"}]},
                                   emitters={"steam_w": (14.0, 12.0, 70.0), "steam_e": (14.0, 13 * T - 12.0, 70.0)}),
    "rome.marcellus": Landmark((12, 16), (0, 96), ref("marcellus"), district=1),
    "rome.octavia": Landmark((9, 11), (0, 72), ref("octavia"), district=1),
    "rome.matidia": Landmark((6, 6), (0, 128), ref("matidia"), district=1),
}

INFO = {
    "rome.pantheon": ("Pantheon", 0.65, 280, "BSG", "pantheon"),
    "rome.pantheon_court": ("Forecourt of the Pantheon", 0.65, 60, "BS", "pantheon_court"),
    "rome.agrippa_baths": ("Baths of Agrippa", 0.65, 90, "BSG", "agrippa_baths"),
    "rome.marcellus": ("Theatre of Marcellus", 0.5, 165, "BS", "marcellus"),
    "rome.octavia": ("Porticus Octaviae", 0.65, 100, "BS", "octavia"),
    "rome.matidia": ("Temple of Matidia", 0.65, 110, "BS", "matidia"),
}
