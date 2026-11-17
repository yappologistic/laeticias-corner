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
MAT = {m.name: i + 1 for i, m in enumerate(MATERIALS)}
for _m_ in MATERIALS:
    assert all("#%02x%02x%02x" % c in PALETTE for c in _m_.ramp), _m_.name
