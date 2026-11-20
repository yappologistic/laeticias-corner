"""The one curated palette and the material ramps built from it.

Ramps run dark -> light and shift hue as they go: shadows lean cool (blue/plum), highlights lean
warm (yellow/cream). Nothing is pure black or white; the darkest ink is a deep plum.
"""

from dataclasses import dataclass


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


INK = "#2a2136"
EARTH = ["#4a3034", "#6b4539", "#8f6343", "#b2875a", "#cfab79", "#e8d4a4"]
LEAF = ["#22343b", "#2b4a41", "#376247", "#4a7d47", "#679a48", "#91b752", "#c6d872"]
PINE = ["#1e3a3c", "#285046", "#36694f"]
BLOSSOM = ["#6a3d5e", "#8f4363", "#c4687f", "#e597a6", "#f6c9c8"]
STONE = ["#333449", "#4d4f63", "#6c6f7e", "#8f939c", "#b6b8b6", "#dbd8cb"]
ROOF = ["#4c2333", "#78303b", "#a3463f", "#c86849", "#e29464"]
STRAW = ["#8a6b3a", "#b49449", "#d8bb5f", "#f0dd91"]
WATER = ["#273560", "#2f4f7c", "#3b729b", "#5596b4", "#86c0cc", "#c4e3dc"]
PLASTER = ["#7a6b78", "#a0928f", "#cdbfac", "#efe5cc", "#fbf5e4"]
VIOLET = ["#3e3366", "#5d4993", "#8869bf", "#b49de0"]
POPPY = ["#c5333d", "#ec6550"]
GLOW = ["#ff9a3a", "#ffc95c", "#ffeba4"]
# Laeticia's skin: a warm shadow, mid and light, with the blossom pinks for her cheeks.
SKIN = ["#b97a66", "#dea488", "#f3cdb0"]
# Snow: blue shadow, cool grey, near white (never pure white).
SNOW = ["#9fb2c6", "#cbd9e0", "#eef3f0"]
# Autumn leaves between the roof rusts and the straw golds.
AUTUMN = ["#b9612c", "#dd8f37"]

PALETTE = [INK, *EARTH, *LEAF, *PINE, *BLOSSOM, *STONE, *ROOF, *STRAW, *WATER, *PLASTER, *VIOLET,
           *POPPY, *GLOW, *SKIN, *SNOW, *AUTUMN]
assert len(set(PALETTE)) == len(PALETTE)


@dataclass(frozen=True)
class Material:
    name: str
    ramp: tuple[tuple[int, int, int], ...]
    bias: float = 0.0          # shifts the lit level up/down the ramp
    glow: tuple[int, int, int] | None = None   # emissive colour added at night
    texture: float = 0.0       # amplitude of per-voxel tone noise, in ramp steps


def _m(name, ramp, **kw) -> Material:
    return Material(name, tuple(_rgb(c) for c in ramp), **kw)


# id 0 is empty space; ids are list positions + 1.
MATERIALS = [
    _m("leaf", LEAF, texture=0.35),
    _m("leaf_dark", [LEAF[0], *PINE, LEAF[3], LEAF[4]], texture=0.4),
    _m("blossom", [*BLOSSOM, PLASTER[4]], texture=0.6),
    _m("bark", [INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3]], texture=0.4),
    _m("wood", [INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3], EARTH[4]], texture=0.3),
    _m("wood_light", [EARTH[1], EARTH[2], EARTH[3], EARTH[4], EARTH[5]], texture=0.3),
    _m("wood_grey", [STONE[0], STONE[1], EARTH[1], STONE[2], STONE[3], PLASTER[2]], texture=0.3),
    _m("stone", [INK, *STONE], texture=0.5),
    # Slate roofs keep their shingle rows legible on the shaded slope: little noise, lifted.
    _m("slate", [INK, STONE[0], STONE[1], STONE[2], STONE[3], STONE[4]], bias=0.3, texture=0.12),
    _m("roof", [INK, *ROOF], texture=0.3),
    _m("red_paint", [INK, ROOF[0], ROOF[1], ROOF[2], ROOF[3]], texture=0.2),
    _m("plaster", [STONE[1], *PLASTER], texture=0.2),
    _m("straw", [EARTH[1], *STRAW], texture=0.6),
    _m("soil", [INK, EARTH[0], EARTH[1], EARTH[2]], texture=0.6),
    _m("glass", [STONE[0], WATER[0], WATER[1], WATER[2], WATER[4]], glow=_rgb(GLOW[1])),
    _m("glass_cool", [STONE[1], WATER[2], WATER[3], WATER[4], WATER[5]]),
    # Greenhouse panes: same look by day, a dim lamplit warmth at night.
    _m("glass_warm", [STONE[1], WATER[2], WATER[3], WATER[4], WATER[5]], glow=_rgb(EARTH[2])),
    _m("lamp", [GLOW[0], GLOW[1], GLOW[2], PLASTER[4]], bias=1.2, glow=_rgb(GLOW[2])),
    _m("fire", [ROOF[2], ROOF[3], GLOW[0], GLOW[1], GLOW[2]], bias=0.8, glow=_rgb(GLOW[1])),
    _m("ember", [ROOF[1], ROOF[2], GLOW[0]], bias=1.5, glow=_rgb(GLOW[0])),
    _m("metal", [INK, STONE[0], STONE[1], STONE[2], STONE[4]]),
    _m("cream", [PLASTER[0], PLASTER[1], PLASTER[2], PLASTER[3], PLASTER[4]], texture=0.2),
    _m("poppy", [ROOF[0], ROOF[1], POPPY[0], POPPY[1], ROOF[4]]),
    _m("violet", [INK, *VIOLET]),
    _m("yellow", [EARTH[2], STRAW[1], STRAW[2], STRAW[3], GLOW[2]]),
    _m("orange", [EARTH[0], EARTH[2], ROOF[3], GLOW[0], ROOF[4]]),
    _m("water", WATER),
    _m("grass", [LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]], texture=0.5),
    _m("ink", [INK, STONE[0], STONE[1]]),
    _m("ginger", [EARTH[0], EARTH[1], EARTH[2], ROOF[3], ROOF[4], STRAW[3]]),
    # Laeticia: cloth is smooth (little grain) so folds and limbs read at 1x; her face is lifted
    # so it stays readable on the shaded +x side.
    _m("skin", [EARTH[1], SKIN[0], SKIN[1], SKIN[2], PLASTER[4]], bias=0.7),
    _m("hair", [STONE[0], STONE[1], STONE[2], STONE[3], STONE[4], STONE[5]], bias=-0.2, texture=0.15),
    _m("cardigan", [LEAF[0], LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5]], bias=0.2, texture=0.1),
    _m("skirt", [ROOF[0], ROOF[1], ROOF[2], ROOF[3], ROOF[4]], bias=0.2, texture=0.08),
    _m("linen", [PLASTER[0], PLASTER[1], PLASTER[2], PLASTER[3], PLASTER[4]], texture=0.08),
    _m("leather", [INK, EARTH[0], EARTH[1], EARTH[2], EARTH[3], EARTH[4]], texture=0.1),
    _m("green_paint", [PINE[0], LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]], bias=0.9, texture=0.05),
    _m("blue_paint", [INK, WATER[0], WATER[1], WATER[2], WATER[3], WATER[4]], bias=0.3, texture=0.35),
    _m("white_paint", [STONE[2], PLASTER[1], PLASTER[2], PLASTER[3], PLASTER[4]], bias=0.4, texture=0.1),
    _m("snow", [STONE[2], SNOW[0], SNOW[1], SNOW[2], PLASTER[4]], bias=0.6, texture=0.1),
    _m("autumn", [ROOF[0], ROOF[1], ROOF[2], AUTUMN[0], AUTUMN[1], STRAW[2], STRAW[3]], texture=0.4),
    _m("gold_leaf", [EARTH[1], EARTH[2], STRAW[0], STRAW[1], STRAW[2], STRAW[3], GLOW[2]], texture=0.4),
    _m("rust_leaf", [INK, ROOF[0], ROOF[1], ROOF[2], AUTUMN[0], ROOF[4]], texture=0.4),
]

# ---- region extensions ----
# Each region adds its own colours and materials; home sprites only ever use PALETTE, and
# region pages may use PALETTE plus their region's colours (validate.py checks both). New
# materials are appended, so the ids of the home materials never change.

# Pārsa, spring c. 470 BC: warm polished limestone, painted and gilded stone, glazed brick,
# cedar, buff mudbrick plaster, the dyes of the court robes and the skins of many peoples.
LIMESTONE = ["#37323c", "#514952", "#6f6560", "#8f8478", "#b0a492", "#cfc3ac", "#e8dec6"]
DARKSTONE = ["#22212b", "#2f2e39", "#45434d"]          # the Tačara's dark polished stone
LAPIS = ["#1f2557", "#2a3a85", "#3a56b0", "#5f7fd0"]
EGYPT_BLUE = ["#2f6e9e", "#4d93c2", "#86bfdc"]
CINNABAR = ["#6e1c22", "#9c2a2a", "#c63f30", "#e2663f"]
HEMATITE = ["#4f2422", "#6e3329", "#8c4733"]           # red plastered floors
GOLD = ["#6b4a1a", "#9a7226", "#c99d36", "#e8c75a", "#f8e9a0"]
CEDAR = ["#3f241e", "#5f3626", "#834d33", "#a96c47"]
MUDBRICK = ["#776049", "#9a7e62", "#bb9f7e", "#d5bd99", "#e9d8b6"]
PURPLE = ["#341838", "#552452", "#7a346c", "#a14f86"]
SAFFRON = ["#b67b1c", "#dca23a"]
MALACHITE = ["#2c604c", "#468a68", "#74b38a"]
SKIN_OLIVE = ["#6a4434", "#8d5f45", "#b07f5c", "#cc9c76"]
SKIN_DARK = ["#33221f", "#4d3328", "#6c4734"]
NAQSH = ["#5d4c50", "#80696a", "#a28a82", "#c2ab9c", "#dccabb"]   # Naqsh-e Rostam's pinkish cliff

# Athens, summer 432 BC: warm Pentelic marble weathering to honey, yellow poros, grey Eleusinian
# and Acropolis limestone with its rusty stains, orange Attic clay and terracotta, black gloss,
# pitch-black hulls, the silver-green olive and summer-gold grass; the painted colours (Egyptian
# blue, cinnabar, ochre, gold, green) are shared with the Pārsa ramps.
MARBLE = ["#4b4552", "#6d6569", "#928882", "#b7ab9c", "#d4c8b2", "#e9dec6", "#f6eedb"]
POROS = ["#5c4b3b", "#7f6a50", "#a28a66", "#c0a87e", "#d9c497"]
ATTIC_ROCK = ["#46413f", "#635b55", "#837a6f", "#a3998b", "#c0b6a6", "#dad1c0"]
RUST = ["#8a5a43", "#a8714f"]                           # iron stains on the rock, red earth
TERRACOTTA = ["#5b2b24", "#87412d", "#ad5b37", "#cb7a48", "#e09c66", "#efbf8c"]
CLAY = ["#7c4a30", "#a5643c", "#c4804f", "#d9a072"]       # Attic clay, unfired and fired
GLOSS = ["#17141b", "#25202a", "#38323f"]               # black gloss of fine pottery
OLIVE = ["#3a4638", "#53634a", "#72825d", "#93a27a", "#b8c39d"]
SUMMER = ["#7a6f3c", "#9c8d4a", "#bba95c", "#d3c07a"]     # summer-dry grass and stubble
PITCH = ["#141217", "#211c24", "#322b35"]

# Rome, April AD 126 (rome.md §3.1): warm travertine with its holes, red-orange brick of the
# concrete facings, grey-brown tufa, grey-black basalt paving, the coloured marbles of the
# empire (giallo antico, green cipollino, red porphyry, grey and pink Egyptian granite),
# painted stucco in red and yellow ochre, and the muddy yellow-green "flavus Tiberis".
TRAVERTINE = ["#4d4234", "#6d5f4c", "#918066", "#b3a081", "#ccbb98", "#e1d3b0", "#efe4c6"]
BRICK = ["#47221d", "#6a3125", "#8a432e", "#a95839", "#c2724a", "#d68f63"]
TUFA = ["#3b3631", "#564d46", "#72675c", "#8f8170", "#aa9c87", "#c4b7a0"]
BASALT = ["#1d1d24", "#2a2a33", "#393943", "#4b4b55", "#5f5f69", "#77777f"]
GIALLO = ["#86672a", "#ad883b", "#cca753", "#e3c576"]
CIPOLLINO = ["#4c6856", "#6c8a75", "#91ad98"]
PORPHYRY = ["#3a1921", "#58242f", "#77333f"]
GRANITE = ["#434549", "#5d5f66", "#7b7d83", "#9a9ca0"]
GRANITE_PINK = ["#6c4c46", "#8f665c", "#b1887a", "#cda798"]
STUCCO_RED = ["#772c21", "#9b3d2b", "#ba583d", "#cf7a59"]
TIBER = ["#475034", "#5d6840", "#74814d", "#8e9961", "#a7b17a", "#c1c698"]

_ROME_NEW = [*TRAVERTINE, *BRICK, *TUFA, *BASALT, *GIALLO, *CIPOLLINO, *PORPHYRY, *GRANITE, *GRANITE_PINK,
             *STUCCO_RED, *TIBER]

REGION_COLOURS = {
    "parsa": [*LIMESTONE, *DARKSTONE, *LAPIS, *EGYPT_BLUE, *CINNABAR, *HEMATITE, *GOLD, *CEDAR,
              *MUDBRICK, *PURPLE, *SAFFRON, *MALACHITE, *SKIN_OLIVE, *SKIN_DARK, *NAQSH],
    "athens": [*DARKSTONE, *LAPIS, *EGYPT_BLUE, *CINNABAR, *GOLD, *CEDAR, *MUDBRICK, *PURPLE, *SAFFRON,
               *MALACHITE, *SKIN_OLIVE, *SKIN_DARK, *MARBLE, *POROS, *ATTIC_ROCK, *RUST, *TERRACOTTA, *CLAY,
               *GLOSS, *OLIVE, *SUMMER, *PITCH],
}
# Rome shares every Pārsa and Athens colour (painted stone, dyes, marble, terracotta, skins).
REGION_COLOURS["rome"] = list(dict.fromkeys([*REGION_COLOURS["parsa"], *REGION_COLOURS["athens"], *_ROME_NEW]))
# The world between the cities shares every city colour (its kit stands beside theirs) and adds
# the open sea in depth, turquoise shallows over sand, the pale sand of beaches and deserts, the
# gold-grey steppe, Anatolian basalt, the blue haze of far ranges and the sepia ink of the map.
SEA = ["#15213f", "#1b2d55", "#22406f", "#2b5588", "#376c9f", "#4d86b4"]
SHALLOW = ["#2d7385", "#3a8f9c", "#4fabaf", "#74c6bd", "#a4dccd"]
SAND = ["#8e7656", "#ae946b", "#c9b083", "#dec99d", "#ede0bc", "#f7efd6"]
STEPPE = ["#6e6a45", "#8a8455", "#a69e66", "#bfb47c", "#d4c995"]
HAZE = ["#5d6a86", "#76839c", "#929db1", "#adb6c5", "#c8cfd8"]
SEPIA = ["#4a3524", "#6e5136", "#94724e"]
_WORLD_NEW = [*SEA, *SHALLOW, *SAND, *STEPPE, *HAZE, *SEPIA]
REGION_COLOURS["world"] = list(dict.fromkeys([*REGION_COLOURS["rome"], *_WORLD_NEW]))
for _cols in REGION_COLOURS.values():
    assert len(set(_cols)) == len(_cols) and not set(_cols) & set(PALETTE)


def palette_for(region: str | None) -> list[str]:
    """Colours a sprite of `region` may use (None: the home region)."""
    return PALETTE + REGION_COLOURS.get(region or "", [])


MATERIALS += [
    _m("limestone", LIMESTONE[:6], texture=0.25),
    _m("ashlar", [INK, *LIMESTONE[:6]], texture=0.45),
    _m("polished", [INK, *DARKSTONE, LIMESTONE[2], LIMESTONE[4]], texture=0.05),
    _m("mudbrick", MUDBRICK, texture=0.3),
    _m("hematite", [INK, *HEMATITE, CINNABAR[2]], texture=0.2),
    _m("cinnabar", [INK, *CINNABAR], bias=0.2, texture=0.1),
    _m("lapis", [INK, *LAPIS], bias=0.2, texture=0.1),
    _m("eblue", [LAPIS[0], LAPIS[1], *EGYPT_BLUE], bias=0.2, texture=0.1),
    _m("gold", GOLD, bias=0.4, texture=0.2),
    _m("cedar", [INK, *CEDAR], texture=0.3),
    _m("purple", [INK, *PURPLE], bias=0.2, texture=0.08),
    _m("saffron", [EARTH[1], *SAFFRON, GOLD[3], GOLD[4]], bias=0.2, texture=0.08),
    _m("malachite", [PINE[0], *MALACHITE, LEAF[6]], bias=0.2, texture=0.08),
    _m("skin_olive", [*SKIN_OLIVE, SKIN[1]], bias=1.1),
    _m("skin_dark", [*SKIN_DARK, SKIN_OLIVE[1], SKIN_OLIVE[2]], bias=1.0),
    _m("hair_black", [INK, DARKSTONE[0], DARKSTONE[1], LAPIS[0], LAPIS[1]], bias=-0.3, texture=0.1),
    _m("naqsh", NAQSH, texture=0.45),
    _m("glaze_blue", [LAPIS[0], LAPIS[1], LAPIS[2], EGYPT_BLUE[1], EGYPT_BLUE[2]], bias=0.3, texture=0.05),
    _m("glaze_yellow", [EARTH[2], SAFFRON[0], GOLD[3], GOLD[4], PLASTER[4]], bias=0.3, texture=0.05),
    _m("wool", [EARTH[1], MUDBRICK[1], MUDBRICK[2], MUDBRICK[3], MUDBRICK[4]], bias=0.2, texture=0.08),
    _m("felt", [INK, EARTH[0], EARTH[1], EARTH[2], MUDBRICK[2]], bias=0.2, texture=0.1),
    _m("bronze", [INK, CEDAR[1], GOLD[0], GOLD[1], GOLD[2], GOLD[3]], bias=0.2, texture=0.1),
]
# Athens (appended, so the home and Pārsa ids never change).
MATERIALS += [
    _m("marble", MARBLE, bias=0.15, texture=0.12),
    _m("marble_rough", MARBLE[:6], texture=0.45),          # quarry faces, unfinished blocks
    _m("poros", [INK, *POROS], texture=0.4),
    _m("eleusinian", [INK, *DARKSTONE, MARBLE[1], MARBLE[2]], texture=0.15),
    _m("attic_rock", [INK, *ATTIC_ROCK], texture=0.45),
    _m("terracotta", TERRACOTTA, texture=0.15),
    _m("clay", [TERRACOTTA[0], *CLAY, TERRACOTTA[5]], bias=0.1, texture=0.1),
    _m("gloss", [INK, *GLOSS, STONE[1]], texture=0.05),
    _m("olive", OLIVE, texture=0.35),
    # The silvery undersides of olive leaves: grey-green, never lighter than the leaf ramps'
    # middle (a near-white top step read as blossom at 1x, V7-001).
    _m("olive_silver", [OLIVE[0], OLIVE[1], OLIVE[2], STONE[3], OLIVE[3]], texture=0.4),
    _m("summer", [EARTH[1], *SUMMER, STRAW[3]], bias=-0.7, texture=0.5),
    _m("pitch", [INK, *PITCH, STONE[1]], texture=0.1),
    _m("triglyph", [INK, PITCH[1], LAPIS[0], LAPIS[1], LAPIS[2]], bias=0.1, texture=0.05),
    _m("ochre", [EARTH[1], EARTH[2], SAFFRON[0], SAFFRON[1], GOLD[3]], bias=0.1, texture=0.08),
    _m("whitewash", [MARBLE[2], PLASTER[1], PLASTER[2], PLASTER[3], PLASTER[4]], bias=0.5, texture=0.2),
    _m("rust", [EARTH[0], *RUST, CLAY[2]], texture=0.3),
    _m("skin_tan", [SKIN_OLIVE[1], SKIN_OLIVE[2], SKIN_OLIVE[3], SKIN[1], SKIN[2]], bias=1.0),
    # Cast bronze kept polished: a warm brown-gold, darker than gilding.
    _m("bronze_cast", [INK, CEDAR[0], CEDAR[1], CEDAR[2], GOLD[1], GOLD[2]], bias=0.3, texture=0.08),
    _m("gravel", [STONE[1], POROS[1], POROS[2], STONE[3], POROS[3], MARBLE[4]], texture=0.7),
]
# Rome (appended after Athens).
MATERIALS += [
    _m("travertine", TRAVERTINE, bias=0.1, texture=0.35),
    _m("brick", [INK, *BRICK], texture=0.3),
    _m("tufa", [INK, *TUFA], texture=0.45),
    _m("basalt", [INK, *BASALT], texture=0.4),
    _m("giallo", [EARTH[1], *GIALLO, PLASTER[3]], bias=0.2, texture=0.15),
    _m("cipollino", [PINE[0], *CIPOLLINO, MARBLE[4]], bias=0.2, texture=0.2),
    _m("porphyry", [INK, *PORPHYRY, CINNABAR[1]], bias=0.2, texture=0.25),
    _m("granite", [INK, *GRANITE, MARBLE[4]], bias=0.2, texture=0.3),
    _m("granite_pink", [GRANITE_PINK[0], *GRANITE_PINK, MARBLE[5]], bias=0.2, texture=0.3),
    _m("stucco_red", [INK, *STUCCO_RED], bias=0.1, texture=0.15),
    _m("tiber", TIBER, texture=0.2),
    # Gilded bronze roof tiles: the gold ramp kept low so a whole roof glows without glaring.
    _m("gilt", [CEDAR[1], GOLD[0], GOLD[1], GOLD[2], GOLD[3], GOLD[4]], bias=-0.2, texture=0.2),
]
# The world set (appended after Rome).
MATERIALS += [
    _m("sand", SAND, texture=0.4),
    _m("steppe", [EARTH[1], *STEPPE], bias=-0.3, texture=0.5),
    _m("sea", SEA, texture=0.15),
    _m("hide", [INK, EARTH[0], EARTH[1], SAND[0], SAND[1], SAND[2]], texture=0.25),
]
# Light leaves in deciduous crowns: the grass's colours (so a crown's plain look is unchanged)
# on a foliage ramp, so on the shader path they turn with the trees' months, not the meadows'.
MATERIALS += [
    _m("leaf_light", [LEAF[1], LEAF[2], LEAF[3], LEAF[4], LEAF[5], LEAF[6]], texture=0.5),
]
MAT = {m.name: i + 1 for i, m in enumerate(MATERIALS)}
_ALL = set(PALETTE).union(*REGION_COLOURS.values())
for _m_ in MATERIALS:
    assert all("#%02x%02x%02x" % c in _ALL for c in _m_.ramp), _m_.name
assert len(MATERIALS) < 255

# Every palette colour belongs to exactly one named group (the lists above, dark to light); the
# ramp table (ramps.py) gives each group a ramp of its own, so a sprite drawn per pixel (ground,
# faces) finds every colour it uses on exactly one ramp.
GROUPS = {
    "ink": [INK], "earth": EARTH, "leaf": LEAF, "pine": PINE, "blossom": BLOSSOM, "stone": STONE,
    "roof": ROOF, "straw": STRAW, "water": WATER, "plaster": PLASTER, "violet": VIOLET,
    "poppy": POPPY, "glow": GLOW, "skin": SKIN, "snow": SNOW, "autumn": AUTUMN,
    "limestone": LIMESTONE, "darkstone": DARKSTONE, "lapis": LAPIS, "egypt_blue": EGYPT_BLUE,
    "cinnabar": CINNABAR, "hematite": HEMATITE, "gold": GOLD, "cedar": CEDAR, "mudbrick": MUDBRICK,
    "purple": PURPLE, "saffron": SAFFRON, "malachite": MALACHITE, "skin_olive": SKIN_OLIVE,
    "skin_dark": SKIN_DARK, "naqsh": NAQSH, "marble": MARBLE, "poros": POROS,
    "attic_rock": ATTIC_ROCK, "rust": RUST, "terracotta": TERRACOTTA, "clay": CLAY, "gloss": GLOSS,
    "olive": OLIVE, "summer": SUMMER, "pitch": PITCH, "travertine": TRAVERTINE, "brick": BRICK,
    "tufa": TUFA, "basalt": BASALT, "giallo": GIALLO, "cipollino": CIPOLLINO, "porphyry": PORPHYRY,
    "granite": GRANITE, "granite_pink": GRANITE_PINK, "stucco_red": STUCCO_RED, "tiber": TIBER,
    "sea": SEA, "shallow": SHALLOW, "sand": SAND, "steppe": STEPPE, "haze": HAZE, "sepia": SEPIA,
}
_grouped = [c for g in GROUPS.values() for c in g]
assert len(_grouped) == len(set(_grouped)) and set(_grouped) == _ALL
