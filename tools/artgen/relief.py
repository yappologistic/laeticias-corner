"""Low relief and friezes drawn from small pixel stencils, embossed onto a wall face.

At landmark scale a carved figure is a dozen pixels tall, so it is drawn, not modelled: a
stencil is a list of strings, one character per voxel (one screen pixel at 64x32), and each
character names a paint (`CODES`). A frieze is composed as a 2D image of stencils, then
`emboss` lays it on a face of a wall box: every painted voxel stands proud of the surface by
its relief depth (one voxel by default), so the renderer's own light gives each figure a lit
top edge and a shadowed underside, and the paint gives it colour. Colour slots (robe, cap,
coat, ...) are filled per figure, so one stencil serves many dresses.

Stencils face right (+s along the face as seen from outside); `mirror` turns them. Images
are (rows, cols) arrays with row 0 at the top. Faces and (s, d) follow `arch.face_frame`.
Reusable by every set: the stencil library holds Achaemenid subjects; other sets add theirs.
"""

from functools import lru_cache

import numpy as np

from arch import face_box, face_frame, fill

# Paint codes: char -> (slot or material, tone, relief depth in voxels). A slot name is looked
# up in the figure's colours; anything else is a material name.
CODES = {
    "S": ("stone", 1.1, 1),          # bare carved stone: faces, hands, feet
    "s": ("stone", -0.35, 1),        # carved stone in shade: inner contours
    "K": ("hair_black", 0.2, 1),     # hair and beards, painted blue-black
    "C": ("cap", 0.2, 1),
    "c": ("cap", -0.5, 1),
    "R": ("robe", 0.15, 1),
    "r": ("robe", -0.7, 1),          # a fold
    "B": ("trim", 0.3, 1),           # borders, belts, pattern
    "D": ("coat", 0.0, 1),           # the kandys coat
    "L": ("legs", 0.0, 1),           # trousers
    "X": ("felt", -0.3, 1),          # shoes
    "P": ("cedar", 0.4, 1),          # spear shafts, staffs
    "G": ("gold", 0.3, 1),
    "g": ("gold", -0.6, 1),
    "Q": ("leather", 0.2, 1),        # bow cases, quivers
    "V": ("gift", 0.3, 1),           # gifts carried
    "v": ("gift", -0.5, 1),
    "W": ("white_paint", 0.3, 1),
    "A": ("beast", 0.35, 1),         # animal bodies
    "a": ("beast", -0.6, 1),
    "M": ("mane", 0.0, 1),
    "Y": ("lion", 0.3, 1),
    "y": ("lion", -0.6, 1),
    "T": ("tree", 0.2, 1),
    "t": ("tree", -0.7, 1),
    "O": ("petal", 0.3, 1),
    "o": ("heart", 0.2, 1),
    "F": ("wing", 0.25, 1),
    "f": ("wing", -0.6, 1),
    "#": ("frame", 0.3, 1),          # panel frames and register lines
    "_": ("frame", -0.2, 0),         # paint on the surface, no relief
}

DEFAULT = {"stone": "limestone", "cap": "felt", "robe": "cinnabar", "trim": "gold", "coat": "lapis",
           "legs": "saffron", "gift": "gold", "beast": "limestone", "mane": "hair_black", "lion": "saffron",
           "tree": "malachite", "petal": "gold", "heart": "cinnabar", "wing": "lapis", "frame": "limestone"}


def stencil(*rows):
    w = max(len(r) for r in rows)
    return tuple(r.ljust(w, ".") for r in rows)


def mirror(st):
    return tuple(r[::-1] for r in st)


def overlay(base, top, dx=0, dy=0):
    """`top` drawn over `base` at column dx, row dy (both stencils); the result is widened to
    hold both."""
    h = max(len(base), len(top) + dy)
    w = max(len(base[0]), len(top[0]) + dx)
    grid = [list(r.ljust(w, ".")) for r in base] + [["."] * w for _ in range(h - len(base))]
    for j, r in enumerate(top):
        for i, ch in enumerate(r):
            if ch != ".":
                grid[j + dy][i + dx] = ch
    return tuple("".join(r) for r in grid)


# ---------------------------------------------------------------- the stencil library

# Heads, 9 wide, rows 0..5; bodies 9 wide, rows 6..15. Faces look right.
HEADS = {
    # Persian: straight fluted felt cap, hair bunched at the nape, full curled beard.
    "persian": stencil("...CcC...", "...CcC...", "..KSSS...", "..KSSSS..", "..KKKS...", "...KKK..."),
    # Median: rounded felt cap with a flap over the neck.
    "mede": stencil("...CCC...", "..CCCCc..", "..CKSSS..", "..CKSSSS.", "..CKKKS..", "...KKK..."),
    # Twisted fillet over curled hair (a spearman of the guard).
    "fillet": stencil(".........", "..KBBB...", "..KSSS...", "..KSSSS..", "..KKKS...", "...KKK..."),
    # Hood with flaps tied under the chin (Armenians, Cappadocians, Sagartians).
    "hood": stencil("...CCC...", "..CCCCC..", "..CCSSS..", "..CCSSSS.", "..CCCCS..", "...CCK..."),
    # Hood drawn over mouth and chin (Parthians, Arians, the magus).
    "face_hood": stencil("...CCC...", "..CCCCC..", "..CCSSS..", "..CCCCCC.", "..CCCCC..", "...CCC..."),
    # Tall pointed hood (Saka).
    "pointed": stencil("....C....", "...Cc....", "..CCCC...", "..CSSSS..", "..CKKS...", "..CKKK..."),
    # Conical cap with a tassel (Babylonians).
    "conical": stencil("...CC....", "..CCCcG..", "..KSSS...", "..KSSSS..", "..KKKS...", "...KKK..."),
    # Tall cone (Lydians).
    "cone": stencil("....C....", "...CCC...", "..KSSS...", "..KSSSS..", "..KKKS...", "...KKK..."),
    # Wreath on curled hair, bare-headed peoples (Elamites, Ionians, Bactrians, Carians).
    "wreath": stencil(".........", "..TKKT...", "..KSSS...", "..KSSSS..", "..KKKS...", "...KK...."),
    # Short curly hair, no beard (Kushites, Indians by convention here: long hair tied).
    "bare": stencil(".........", "..KKK....", "..KSSS...", "..KSSSS..", "..KSSS...", "...SS...."),
    # The king: tall crenellated crown, long squared beard.
    "king": stencil("..GgGg...", "..GGGG...", "..KSSS...", "..KSSSS..", "..KKKS...", "..KKKK..."),
}

BODIES = {
    # Persian court robe: wide sleeves, a belt, the skirt flaring in pleats at the back.
    "robe": stencil("..RRRR...", "..RRRRR..", ".RRRBRR..", ".RRrRRr..", "RRrRRRr..", "RRrRRRrr.",
                    "RRrRRRRr.", "RRRRRRRR.", ".RBRRRBR.", "..XX.XX.."),
    # Median dress: knee tunic with belt, the kandys hanging at the back, trousers, boots.
    "median": stencil("..RRRR...", ".DRRRRR..", ".DRRBRR..", ".DRRRRR..", ".DRRRRR..", "..RRRRR..",
                      "..LL.LL..", "..LL..LL.", ".LL...LL.", ".XX...XX."),
    # Riding costume without the coat (delegations), a striding step.
    "riding": stencil("..RRRR...", "..RRRRR..", "..RRBRR..", "..RRRRR..", "..RRRRR..", "..RRRR...",
                      "..LL.LL..", "..LL..LL.", ".LL...LL.", ".XX...XX."),
    # Long robe falling straight with a fringe (Babylonians, Syrians, Arabs, Elamites).
    "long": stencil("..RRRR...", "..RRRRR..", "..RRBRR..", "..RRRRR..", "..RRrRR..", "..RRrRR..",
                    "..RRrRR..", "..RRRRR..", "..BBBBB..", "..XX.XX.."),
    # Striped long garment (Lydians, Ionians).
    "striped": stencil("..RRRR...", "..BBBBB..", "..RRRRR..", "..BBBBB..", "..RRRRR..", "..BBBBB..",
                       "..RRRRR..", "..BBBBB..", "..RRRRR..", "..SS.SS.."),
    # Wrapped lower garment, bare chest (Indians, Kushites by convention).
    "wrap": stencil("..SSSS...", "..SSSSS..", "..SSSS...", "..RRRRR..", "..RRRRR..", "..RRRRR..",
                    "..RRrRR..", "..RRRR...", "..SS.SS..", "..SS.SS.."),
}

# Things held, drawn over the figure. Columns may run past the body to the right.
HELD = {
    "spear": stencil("........G", "........G", "........P", "........P", "........P", "........P",
                     "......SSP", "........P", "........P", "........P", "........P", "........P",
                     "........P", "........P", "........P", "........G"),
    "staff": stencil("", "", "", "", "", "", "......SS.", ".......P.", ".......P.", ".......P.",
                     ".......P.", ".......P.", ".......P.", ".......P.", ".......P.", ".......P."),
    "bowcase": stencil("", "", "", "", "", "", "", "", "Q........", "QQ.......", "QQ.......", ".Q......."),
    "quiver": stencil("", "", "", "", "", "Q........", "Q........", "Q........", "Q........", "", "", ""),
    "vessel": stencil("", "", "", "", "", "", ".....SVV.", "......VV.", "......v..", ),
    "bowl": stencil("", "", "", "", "", "", ".....SVVV", "......vv.", ),
    "garment": stencil("", "", "", "", "", "", ".....SVV.", ".....VVV.", ".....VvV.", ".....VV.."),
    "pole": stencil("", "", "", "", "....V...V", "....PPPPP", "...vVv.vV"),
    "shield": stencil("", "", "", "", "", "", ".....VVV.", ".....VvV.", ".....VVV.", "......V.."),
    "lotus": stencil("", "", "", "", "", "......T..", "......T..", ".....SP.."),
    "kid": stencil("", "", "", "", ".....VV..", "....VVVV.", ".....SVV.", ".....V.V."),
    "wineskin": stencil("", "", "", "", "", "", ".....VVV.", "....SVVV.", ".....VVv."),
    "hand_back": stencil("", "", "", "", "", "", "S.......", "SR......"),
}


@lru_cache(maxsize=None)
def figure(head="persian", body="robe", held=()):
    """A standing figure 16 rows tall facing right: a head, a body and things held."""
    st = HEADS[head] + BODIES[body]
    for h in held:
        st = overlay(st, HELD[h])
    return st


# Animals of the delegations and the hunt, facing right, 12-14 rows tall.
BEASTS = {
    "horse": stencil(
        "............M...", "...........MAA..", "..........MAAAA.", ".........MAAa.AA", "........MAAA....",
        "..AAAAAAAAAA....", ".AAAAAAAAAAA....", "MAAAAAAAAAAa....", "M.AAaaaaAAa.....", "..Aa.....Aa.....",
        "..a.a....a.a....", "..a..a...a..a...", ".XX..X..XX..X..."),
    "bull": stencil(
        "............GG..", "...........AAAA.", "..........AAAAAA", "..AAAAAAAAAAAa..", ".AAAAAAAAAAAAa..",
        "aAAAAAAAAAAAa...", "a.AAAAAAAAAAa...", "..AAaaaaaAAa....", "..Aa.....Aa.....", "..a.a....a.a....",
        "..a..a...a..a...", ".XX..X..XX..X..."),
    "camel": stencil(
        "..............AA", ".............AAA", "....AA.......A..", "...AAAA.....AA..", "..AAAAAA...AA...",
        ".AAAAAAAAAAAA...", ".AAAAAAAAAAA....", "aAAAAAAAAAAa....", "..AAaaaaaaa.....", "..Aa.....Aa.....",
        "..a.a....a.a....", "..a..a...a..a...", "..a..a...a..a...", ".XX..X..XX..X..."),
    "ram": stencil(
        "..........GG..", ".........GAAG.", "..AAAAAAAAAAA.", ".AAAAAAAAAAAa.", "aAAAAAAAAAAa..",
        "..AAaaaaAAa...", "..a.a...a.a...", ".XX.X..XX.X..."),
}

LION_BULL = stencil(
    "...MM.....................",
    "..MMMMY...........G.G.....",
    ".MMMMMYY.........AAAA.....",
    ".MMMMMYYY.......AAAAAA....",
    "..MMMYYYYYAAAAAAAAAAAA....",
    "...YYYYYYAAAAAAAAAAAa.....",
    "...YYYYYYAAAAAAAAAAAa.....",
    "..YYY.YYAAAAAAAAAAAAa.....",
    ".YY...YAAAAAAAAAAAAAaa....",
    "YY....YAAAAAAAAAAAAaa.A...",
    "Y.....YYaAAAAAAAAa...AA...",
    "......Y.aa.....aa....A....",
    ".....YY.a.......a.........",
    ".....Y..a.......a.........",
    "....YY..aa......aa........",
)

CYPRESS = stencil("..T..", "..T..", ".TTT.", ".TtT.", ".TTT.", "TTtTT", ".TTT.", "TTtTT", "TTTTT",
                  "TTtTT", "TTTTT", "TTtTT", ".TTT.", "..s..", "..s..", "..s..")

ROSETTE = stencil(".O.O.O.", "O.OOO.O", ".OOoOO.", "OOoooOO", ".OOoOO.", "O.OOO.O", ".O.O.O.")
ROSETTE_S = stencil(".O.O.", "OOoOO", ".ooo.", "OOoOO", ".O.O.")

WINGED_DISC = stencil(
    ".........KGK.........",
    ".........KSK.........",
    "..FFFF..RRRRR..FFFF..",
    "FFFFFFFFRGGGRFFFFFFFF",
    ".fFFFFFFGG.GGFFFFFFf.",
    "..ffFFFFRGGGRFFFFff..",
    "....fff..RRR..fff....",
    ".........FFF.........",
    "........FfFfF........",
)

# The king walking under the parasol held by an attendant behind him (door jambs).
KING_PARASOL = stencil(
    "..GGGGGGGGGGG..",
    ".GOOOOOOOOOOOG.",
    "..G.G.GPG.G.G..",
    ".......P.......",
    ".......PGgGg...",
    ".......PGGGG...",
    ".......KSSS....",
    "..CC...KSSSS...",
    "..CC...KKKS....",
    ".KSSS..KKKK....",
    ".KSSSSRRRRRSS..",
    ".KKKS.RRRRRRP..",
    "..RRSSRRRBRRP..",
    ".RRRRRRrRRRrP..",
    ".RRRRRRrRRRrP..",
    "RRrRRRRrRRRrP..",
    "RRrRRRRRRRRrrP.",
    "RRrRRRRRRRRRrP.",
    "RRRRRRRRRRRRRP.",
    "RRRRRRRBRRRRBP.",
    ".XX.XX.RRRRRRR.",
    "........XX.XX..",
)

# The royal hero stabbing a rearing lion-griffin (door jambs of the palaces).
HERO_GRIFFIN = stencil(
    "...GgG.....G.......",
    "...GGG....GAA......",
    "..KSSS...GAAAA.....",
    "..KSSSS...AAG......",
    "..KKKS.SSSAA.......",
    "..RRRRRP.AAAFF.....",
    ".RRRRR...AAAFFF....",
    ".RRRBR...AAAAFF....",
    ".RRrRRR..AAAAa.....",
    "RRrRRRr..AAAAa.....",
    "RRrRRRrr..AAAa.....",
    "RRRRRRRr..Aa.Aa....",
    "RRRRRRRR..a...a....",
    ".RBRRRBR..a...a....",
    "..XX.XX..XX..XX....",
)

# Glazed-brick subjects (Susa type), drawn on a blue brick ground.
GLAZE_LION = stencil(
    "................MM.....",
    "...............MMYY....",
    "..y...........MMMYYY...",
    ".y.YYYYYYYYYYMMMMY.YY..",
    "y..YYYYYYYYYYYMMMY.....",
    "..YYYYYYYYYYYYYMMY.....",
    "..YYYyyyyyyYYYYM.......",
    "..YYy......yYYy........",
    "..Yy.......Yy.Y........",
    ".YY.......YY...Y.......",
    "WW.......WW...WW.......",
)
GLAZE_ARCHER = stencil(
    "...KKK....", "..KKKKW...", "..KSSS....", "..KSSSS...", "..KKKS....", "...KK.Q...",
    "..RRRRQ.G.", ".RBRBR.SSP", ".RRRRR..P.", ".RBRBRB.P.", "RRRRRRR.P.", "RBRBRBR.P.",
    "RRRRRRRRP.", "RBRBRBRBP.", ".RRRRRRR..", "..WW.WW.G.")


# ---------------------------------------------------------------- images

def image(width, height):
    """An empty frieze image: per pixel a code character."""
    return np.full((height, width), ".", "<U1")


def stamp(img, st, x, y, colours=None, cmap=None):
    """Draw stencil `st` into `img` with its top-left at (x, y). `cmap` collects per-pixel
    colour overrides as {(row, col): slots}; it is how one image holds many dresses."""
    for j, r in enumerate(st):
        yy = y + j
        if not 0 <= yy < img.shape[0]:
            continue
        for i, ch in enumerate(r):
            xx = x + i
            if ch != "." and 0 <= xx < img.shape[1]:
                img[yy, xx] = ch
                if cmap is not None and colours:
                    cmap[(yy, xx)] = colours


def emboss(m, face, wall, s0, z_top, img, colours=None, cmap=None, depth=1, k=None, sunk=False):
    """Lay image `img` on `face` of the wall box `wall` = (x0,x1,y0,y1,z0,z1), its left edge at
    `s0` and its top at `z_top` (design units). One image pixel is one voxel (at k = 2; at
    other k the image is resampled nearest). Painted pixels stand proud of the surface by
    their relief depth in voxels; `_` paints the surface itself. `sunk` carves the ground
    back instead, so the figures end flush with the wall face and nothing stands out of it
    (reliefs facing a walk tile, whose headroom must stay clear)."""
    k = k or m.k
    H, W = img.shape
    x0, x1, y0, y1 = wall[:4]
    colours = {**DEFAULT, **(colours or {})}
    # Resolve every pixel to (material, tone, relief).
    tones = np.zeros((H, W), np.float32)
    reliefs = np.zeros((H, W), np.float32)
    matimg = np.full((H, W), "", object)
    for j, i in zip(*np.nonzero(img != ".")):
        slot, tone, rel = CODES[img[j, i]]
        pal = colours if cmap is None else {**colours, **cmap.get((j, i), {})}
        matimg[j, i] = pal.get(slot, slot)
        tones[j, i] = tone
        reliefs[j, i] = rel * depth
    mats = {name: matimg == name for name in sorted(set(matimg[matimg != ""].tolist()))}
    maxrel = (reliefs.max() + 0.01) / k
    if sunk:   # the same relief, cut into a face moved back by its depth
        from arch import carve
        x0, x1, y0, y1 = _shrink(face, (x0, x1, y0, y1), maxrel)
        wall = (x0, x1, y0, y1)
        carve(m, face_box(face, x0, x1, y0, y1, z_top - H / 2.0, z_top, s0, s0 + W / 2.0, -maxrel, 0.0))
    # One image pixel is half a design unit: one voxel at k = 2.
    box = face_box(face, x0, x1, y0, y1, z_top - H / 2.0, z_top + 0.01, s0, s0 + W / 2.0, -maxrel, 1.0 / k)

    def lookup(X, Y, Z):
        s, d = face_frame(face, X, Y, Z, x0, x1, y0, y1)
        col = np.floor((s - s0) * 2.0).astype(np.int64)
        row = np.floor((z_top - Z) * 2.0).astype(np.int64)
        col, row, d = np.broadcast_arrays(col, row, d)
        ok = (col >= 0) & (col < W) & (row >= 0) & (row < H)
        return np.clip(col, 0, W - 1), np.clip(row, 0, H - 1), ok, d

    for name, sel in mats.items():
        def mask(X, Y, Z, sel=sel):
            col, row, ok, dd = lookup(X, Y, Z)
            rel = reliefs[row, col] / k
            on = ok & sel[row, col]
            return on & (dd >= -rel - 1e-4) & ((dd < 0) | ((rel == 0) & (dd < 1.0 / k)))

        def tone(X, Y, Z):
            col, row, _ok, _dd = lookup(X, Y, Z)
            return tones[row, col]
        fill(m, box, name, mask, tone)


def _shrink(face, rect, by):
    """A box rect with `face` moved inward by `by`."""
    x0, x1, y0, y1 = rect
    return {"+x": (x0, x1 - by, y0, y1), "-x": (x0 + by, x1, y0, y1), "+y": (x0, x1, y0, y1 - by),
            "-y": (x0, x1, y0 + by, y1)}[face]


# ---------------------------------------------------------------- compositions

def register(width, figures, period, start=0, facing=1, height=16, gap_every=0, gap=None):
    """A register `height` pixels tall: figures [(stencil, colours)] cycled every `period`
    pixels; with `gap_every` = n a divider stencil `gap` stands after every n figures."""
    img = image(width, height)
    cmap = {}
    x, n, i = start, 0, 0
    while x < width:
        if gap_every and n == gap_every and gap is not None:
            st = gap
            stamp(img, st, x, height - len(st), None, cmap)
            x += len(st[0]) + 2
            n = 0
            continue
        st, col = figures[i % len(figures)]
        if facing < 0:
            st = mirror(st)
        stamp(img, st, x, height - len(st), col, cmap)
        x += period if len(st[0]) <= period else len(st[0]) + 2
        n += 1
        i += 1
    if facing < 0:
        img = img[:, ::-1]
        cmap = {(j, width - 1 - c): v for (j, c), v in cmap.items()}
    return img, cmap


def band(width, st, period, height=None, y=0):
    """A border of one ornament repeated (rosettes, cypresses)."""
    h = height or len(st)
    img = image(width, h)
    for x in range(0, width, period):
        stamp(img, st, x, y)
    return img


def stack(*parts):
    """Stack (img, cmap) parts vertically, the first on top."""
    imgs, cmaps = [], {}
    y = 0
    for p in parts:
        img, cm = p if isinstance(p, tuple) else (p, {})
        imgs.append(img)
        for (j, c), v in cm.items():
            cmaps[(j + y, c)] = v
        y += img.shape[0]
    w = max(i.shape[1] for i in imgs)
    out = np.concatenate([np.pad(i, ((0, 0), (0, w - i.shape[1])), constant_values=".") for i in imgs])
    return out, cmaps


def rule(width, ch="#", height=1):
    img = image(width, height)
    img[:] = ch
    return img


# Dresses for the processions (persepolis.md §6.2): robe and cap colours rotate so a row reads
# as patterned reds, blues and yellows, beards blue-black, gold at the details.
ROBES = ("cinnabar", "lapis", "saffron", "purple", "eblue", "malachite")


def guards(n_colours=ROBES, spears=True):
    """Alternating Persian spearmen and Median guards with bow cases."""
    out = []
    for i, robe in enumerate(n_colours):
        trim = "gold" if robe != "saffron" else "white_paint"
        if i % 2 == 0:
            st = figure("persian", "robe", ("spear",) if spears else ())
            out.append((st, {"robe": robe, "trim": trim, "cap": "wool"}))
        else:
            st = figure("mede", "median", ("bowcase", "spear") if spears else ("bowcase",))
            out.append((st, {"robe": robe, "trim": trim, "cap": "felt", "coat": ROBES[(i + 2) % 6],
                             "legs": ROBES[(i + 3) % 6]}))
    return out


def nobles():
    """Persian and Median nobles climbing, holding lotus flowers (Tripylon, Apadāna)."""
    out = []
    for i, robe in enumerate(ROBES):
        if i % 2 == 0:
            out.append((figure("persian", "robe", ("lotus",)), {"robe": robe, "trim": "gold"}))
        else:
            out.append((figure("mede", "median", ("lotus",)), {"robe": robe, "coat": ROBES[(i + 3) % 6],
                                                               "legs": ROBES[(i + 1) % 6], "trim": "gold"}))
    return out


def servants():
    """Servants in Median dress carrying a kid, a wineskin, covered dishes (Hadiš stairs)."""
    out = []
    for i, (held, robe) in enumerate((("kid", "saffron"), ("wineskin", "eblue"), ("bowl", "cinnabar"),
                                      ("vessel", "malachite"))):
        out.append((figure("mede", "median", (held,)),
                    {"robe": robe, "coat": "lapis", "legs": "cinnabar", "trim": "gold",
                     "gift": {"kid": "wool", "wineskin": "leather", "bowl": "gold", "vessel": "bronze"}[held]}))
    return out


# Delegations: (head, body, held, robe, cap, beast) after persepolis.md §6.2.
DELEGATIONS = (
    ("mede", "riding", "vessel", "lapis", "felt", None),             # Medes
    ("wreath", "long", "bowl", "saffron", "felt", None),              # Elamites
    ("hood", "riding", "vessel", "cinnabar", "felt", "horse"),        # Armenians
    ("face_hood", "riding", "bowl", "malachite", "wool", "camel"),    # Parthians
    ("conical", "long", "garment", "eblue", "lapis", "bull"),         # Babylonians
    ("cone", "striped", "vessel", "cinnabar", "saffron", "horse"),    # Lydians
    ("wreath", "long", "garment", "lapis", "felt", "ram"),            # Syrians
    ("pointed", "riding", "garment", "malachite", "felt", "horse"),   # Saka
    ("bare", "wrap", "pole", "white_paint", "felt", None),            # Indians
    ("wreath", "striped", "garment", "lapis", "felt", None),          # Ionians
)


def delegations(seed=0, usher_robe="cinnabar"):
    """Delegations led by the hand by an usher in Median dress, gift-bearers behind, an animal
    led by the last, cypress trees between delegations."""
    out = []
    n = len(DELEGATIONS)
    for j in range(n):
        head, body, held, robe, cap, beast = DELEGATIONS[(j + seed) % n]
        out.append((figure("mede", "median", ("staff",)),
                    {"robe": usher_robe if j % 2 == 0 else "purple", "coat": "lapis", "legs": "saffron"}))
        for i in range(2):
            out.append((figure(head, body, (held,)), {"robe": robe, "cap": cap, "trim": "gold",
                                                     "legs": "felt", "gift": "gold"}))
        if beast:
            out.append((BEASTS[beast], {"beast": {"horse": "cedar", "bull": "limestone", "camel": "wool",
                                                  "ram": "wool"}[beast], "mane": "hair_black"}))
        out.append((CYPRESS, {}))
    return out


# The audience: the king enthroned under his canopy with the crown prince behind, incense
# burners before him, an official in Median dress bowing with his hand before his mouth.
AUDIENCE = stencil(
    "..GgG..GgGg.....................",
    "..GGG..GGGG.....................",
    ".KSSS..KSSS.................CCC.",
    ".KSSSS.KSSSS...............CCCCC",
    ".KKKS..KKKS.......G......SSSSKC.",
    ".KKKK..KKKK..G...GGG.....SSKKKC.",
    "..RRRRPRRRRRSS..G.G.......KKK...",
    ".RRRRRPRRRRR.P..G.G.....RRRRRR..",
    ".RRBRRPRRBRR.P..G.G....DRRRRRRD.",
    ".RRRRRPRRRRRRRRRG.G....DRRBRRRD.",
    "RRrRRRPGRRRRRRRRG.G....DRRRRRRD.",
    "RRrRRRPGGGGGRRRRG.G....DRRRRRR..",
    "RRrRRRPG...GRRR.G.G.....LL..LL..",
    "RRRRRRPG...GXXX.G.G.....LL..LL..",
    ".RBRBRPG...GGGGGGGGG...LL....LL.",
    "..XX.XXG...G.G.GG.GG...XX....XX.",
)

KINDS = {"guards": guards, "nobles": nobles, "servants": servants}


def stair_facade(width, height, kind="delegations", seed=0, facing=1, centre=None, period=12):
    """A stair front carved in registers (persepolis.md §3.1): a rosette border along the top,
    registers of figures 16 px tall divided by fine rules, a plain base. `centre` puts one
    scene in the middle of the top register ('audience' or 'disc') with guards facing it."""
    regs = max(1, (height - 7) // 17)
    parts = [band(width, ROSETTE_S, 6, height=6, y=0)]
    for i in range(regs):
        if centre and i == 0:
            img, cmap = image(width, 16), {}
            sc = AUDIENCE if centre == "audience" else WINGED_DISC
            cx = (width - len(sc[0])) // 2
            stamp(img, sc, cx, 16 - len(sc), {"robe": "purple", "coat": "lapis", "legs": "saffron", "cap": "felt"},
                  cmap)
            g = guards()
            left, lcm = register(max(cx - 2, 1), g, period, facing=1)
            right, rcm = register(max(width - cx - len(sc[0]) - 2, 1), g, period, facing=-1)
            img[:, :left.shape[1]] = np.where(left != ".", left, img[:, :left.shape[1]])
            cmap.update(lcm)
            x2 = cx + len(sc[0]) + 2
            img[:, x2:x2 + right.shape[1]] = np.where(right != ".", right, img[:, x2:x2 + right.shape[1]])
            cmap.update({(j, c + x2): v for (j, c), v in rcm.items()})
            parts.append((img, cmap))
        else:
            figs = delegations(seed + i) if kind == "delegations" else KINDS[kind]()
            parts.append(register(width, figs, period, start=(i * 5 + seed) % period,
                                  facing=facing if i % 2 == 0 else (facing if kind != "guards" else -facing)))
        parts.append(rule(width, "_"))
    used = sum((p[0] if isinstance(p, tuple) else p).shape[0] for p in parts)
    if used < height:
        parts.append(rule(width, "_", height - used))
    img, cmap = stack(*parts)
    return img[:height], cmap


# The Ishtar-Gate type beasts in glazed brick: a striding bull and a mušḫuššu dragon with its
# serpent head, scaly body, lion forelegs, eagle hind legs and scorpion tail.
GLAZE_BULL = stencil(
    "..............GG...",
    ".............YYYY..",
    "..y.........YYYYYY.",
    ".y.YYYYYYYYYYYYy...",
    "y..YYYYYYYYYYYY....",
    "...YYYYYYYYYYYy....",
    "...YYyyyyyyYYy.....",
    "...Yy......Yy......",
    "...Y.Y.....Y.Y.....",
    "..WW..W...WW..W....",
)
GLAZE_DRAGON = stencil(
    "...............WW..",
    "..............WWWW.",
    ".y............WW...",
    "y.y..........YW....",
    "..yYYYYYYYYYYY.....",
    "...YYWYWYWYYYY.....",
    "...YYYYYYYYYYY.....",
    "...yYy.....YY......",
    "..W..W.....Y.Y.....",
    ".WW..WW...WW..W....",
)

# Darius I's tomb, upper register (Naqsh-e Rostam): the throne platform borne by two rows of
# the peoples with raised arms; the king on a three-stepped dais, bow in hand, before the fire
# altar; the winged figure in its disc above, the moon disc at the corner.
def naqsh_upper(width=68, height=62):
    img = image(width, height)
    bearer = stencil("SS.SS", ".SSS.", ".KSK.", "..R..", ".RRR.", ".RRR.", "..L..", ".L.L.")
    for row, y in ((0, height - 9), (1, height - 19)):
        for x in range(2 + row * 3, width - 6, 6):
            stamp(img, bearer, x, y)
        img[y - 1, 1:width - 1] = "#"
    img[height - 20, 1:width - 1] = "#"
    img[height - 21, 0:width] = "#"
    base = height - 22
    for i in range(3):
        img[base - i, 12 + i * 2:28 - i * 2] = "#"
    king = stencil("..GgG.", "..GGG.", ".KSSS.", ".KSSSS", ".KKKS.", ".KKKK.", ".RRRRS", "RRRRR.",
                   "RRBRRG", "RRRRRG", "RRrRRG", "RRrRR.", "RRRRR.", ".RRRR.", ".XX.X.")
    stamp(img, king, 16, base - 3 - len(king))
    altar = stencil(".GGGG.", "GGGGGG", "######", ".####.", "..##..", "..##..", ".####.", "######")
    stamp(img, altar, 42, base - len(altar) + 1)
    stamp(img, stencil("..G..", ".GGG.", "GGGGG"), 42 + 0, base - len(altar) - 3)
    stamp(img, WINGED_DISC, (width - len(WINGED_DISC[0])) // 2, 2)
    stamp(img, stencil(".OOO.", "OO.OO", "O...O", "OO.OO", ".OOO."), width - 8, 3)
    return img
