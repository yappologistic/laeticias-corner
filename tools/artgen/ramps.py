"""The ramp table the shader path reads (graphics-plan §2.3; schema in README.md "Data pages").

One ramp per material (`palette.MATERIALS`, the ramps the renderer quantises to), one per
palette group (`palette.GROUPS`, the ramps flat sprites resolve to) and, for the green ramps,
one per colour state of the seasons (`fresh`, `dry`, `dormant`, `turn`): the shader swaps a
ramp for its state's ramp, so a meadow or a canopy turns with the month without a sprite per
state. Every ramp is at most eight steps, dark to light; ids are stable across rebuilds (an id
belongs to its name in the committed `assets/atlas/ramps.json`; new names append), 1..255, 0
meaning "no pixel".

    tools/artgen/.venv/bin/python tools/artgen/ramps.py [OUT_DIR]   (default assets/atlas)
"""

import json
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import spec  # noqa: E402
from palette import (AUTUMN, EARTH, GROUPS, LEAF, MATERIALS, ROOF, SAND, STEPPE, STONE, STRAW, SUMMER,  # noqa: E402
                     TIBER, _rgb)

STEPS = 8
COMMITTED = spec.ASSETS / "atlas" / "ramps.json"

# What a ramp is made of: decides how light, weather and seasons treat its pixels.
CLASSES = ("ground", "grass", "crop", "stone", "marble", "plaster", "roof", "wood", "metal",
           "cloth", "skin", "foliage_deciduous", "foliage_evergreen", "water", "glass", "ink",
           "snow", "ice", "flame")
MATERIAL_CLASS = {
    "leaf": "foliage_deciduous", "leaf_dark": "foliage_evergreen", "blossom": "foliage_deciduous",
    "bark": "wood", "wood": "wood", "wood_light": "wood", "wood_grey": "wood", "stone": "stone",
    "slate": "roof", "roof": "roof", "red_paint": "plaster", "plaster": "plaster", "straw": "roof",
    "soil": "ground", "glass": "glass", "glass_cool": "glass", "glass_warm": "glass", "lamp": "flame",
    "fire": "flame", "ember": "flame", "metal": "metal", "cream": "plaster", "poppy": "cloth",
    "violet": "cloth", "yellow": "cloth", "orange": "cloth", "water": "water", "grass": "grass",
    "ink": "ink", "ginger": "skin", "skin": "skin", "hair": "skin", "cardigan": "cloth",
    "skirt": "cloth", "linen": "cloth", "leather": "cloth", "green_paint": "plaster",
    "blue_paint": "plaster", "white_paint": "plaster", "snow": "snow", "autumn": "foliage_deciduous",
    "gold_leaf": "foliage_deciduous", "rust_leaf": "foliage_deciduous",
    "limestone": "stone", "ashlar": "stone", "polished": "stone", "mudbrick": "plaster",
    "hematite": "plaster", "cinnabar": "plaster", "lapis": "plaster", "eblue": "plaster",
    "gold": "metal", "cedar": "wood", "purple": "cloth", "saffron": "cloth", "malachite": "cloth",
    "skin_olive": "skin", "skin_dark": "skin", "hair_black": "skin", "naqsh": "stone",
    "glaze_blue": "stone", "glaze_yellow": "stone", "wool": "cloth", "felt": "cloth",
    "bronze": "metal",
    "marble": "marble", "marble_rough": "marble", "poros": "stone", "eleusinian": "stone",
    "attic_rock": "stone", "terracotta": "roof", "clay": "ground", "gloss": "ink",
    "olive": "foliage_evergreen", "olive_silver": "foliage_evergreen", "summer": "grass",
    "pitch": "wood", "triglyph": "plaster", "ochre": "plaster", "whitewash": "plaster",
    "rust": "ground", "skin_tan": "skin", "bronze_cast": "metal", "gravel": "ground",
    "travertine": "stone", "brick": "stone", "tufa": "stone", "basalt": "stone", "giallo": "marble",
    "cipollino": "marble", "porphyry": "stone", "granite": "stone", "granite_pink": "stone",
    "stucco_red": "plaster", "tiber": "water", "gilt": "metal",
    "sand": "ground", "steppe": "grass", "sea": "water", "hide": "cloth",
}
GROUP_CLASS = {
    "ink": "ink", "earth": "ground", "leaf": "grass", "pine": "foliage_evergreen",
    "blossom": "foliage_deciduous", "stone": "stone", "roof": "roof", "straw": "crop",
    "water": "water", "plaster": "plaster", "violet": "cloth", "poppy": "cloth", "glow": "flame",
    "skin": "skin", "snow": "snow", "autumn": "foliage_deciduous", "limestone": "stone",
    "darkstone": "stone", "lapis": "plaster", "egypt_blue": "plaster", "cinnabar": "plaster",
    "hematite": "plaster", "gold": "metal", "cedar": "wood", "mudbrick": "plaster",
    "purple": "cloth", "saffron": "cloth", "malachite": "cloth", "skin_olive": "skin",
    "skin_dark": "skin", "naqsh": "stone", "marble": "marble", "poros": "stone",
    "attic_rock": "stone", "rust": "ground", "terracotta": "roof", "clay": "ground", "gloss": "ink",
    "olive": "foliage_evergreen", "summer": "grass", "pitch": "wood", "travertine": "stone",
    "brick": "stone", "tufa": "stone", "basalt": "stone", "giallo": "marble", "cipollino": "marble",
    "porphyry": "stone", "granite": "stone", "granite_pink": "stone", "stucco_red": "plaster",
    "tiber": "water", "sea": "water", "shallow": "water", "sand": "ground", "steppe": "grass",
    "haze": "stone", "sepia": "ink",
}
# Thin-shell depth for the height-field shadow march, px (graphics-plan §2.2); 255 = solid.
SHELL = {"foliage_deciduous": 6, "foliage_evergreen": 6, "grass": 6, "crop": 6, "cloth": 2, "skin": 8}
POROUS = {"ground", "grass", "crop", "stone", "marble", "plaster", "roof", "wood", "cloth"}
SNOW_ON = {"ground", "grass", "crop", "stone", "marble", "plaster", "roof", "wood", "metal",
           "cloth", "foliage_deciduous", "foliage_evergreen", "snow", "ice"}
SPECULAR_CLASSES = {"metal", "glass", "water", "ice", "marble"}
SPECULAR_MATERIALS = {"polished", "glaze_blue", "glaze_yellow", "gloss", "pitch", "basalt"}
SWAY = {"foliage_deciduous", "foliage_evergreen", "grass", "crop", "cloth"}

# Response fields of docs/design/realism.md §5.2, by class (a ramp's own colours where named).
# Light through leaves, grass and cloth: `translucency` 0..1 and the transmitted colour `trans`.
TRANSLUCENCY = {"foliage_deciduous": 0.6, "foliage_evergreen": 0.35, "grass": 0.4, "crop": 0.4, "cloth": 0.25}
TRANS = {"foliage_deciduous": LEAF[6], "foliage_evergreen": LEAF[5], "grass": SUMMER[3], "crop": STRAW[3]}
# Wet ground: steps a porous pixel drops on its ramp at full wetness, and the sheen of flat wet
# pixels (0.06 porous, 0.12 stone and marble).
WET_STEPS = {"ground": 2, "grass": 1, "crop": 1, "stone": 1, "marble": 1, "plaster": 2, "roof": 1, "wood": 2,
             "cloth": 2}
GLOSS = {"stone": 0.12, "marble": 0.12}
# Glints: the share of sunlit pixels at the top step that sparkle (snow 0.6 %, metal and glaze).
SPARKLE = {"snow": 0.006, "ice": 0.006, "metal": 0.004}
SPARKLE_MATERIALS = {"glaze_blue": 0.003, "glaze_yellow": 0.003, "gloss": 0.003, "gold": 0.004}
# Water ramps: the bed seen through shallow water and how fast depth hides it (rgb per 70 px).
BED = {"water": (SAND[1], (2.4, 1.0, 0.65)), "pal.water": (SAND[1], (2.4, 1.0, 0.65)),
       "sea": (SAND[2], (2.4, 1.0, 0.65)), "pal.sea": (SAND[2], (2.4, 1.0, 0.65)),
       "pal.shallow": (SAND[3], (2.4, 1.0, 0.65)),
       "tiber": (TIBER[2], (3.4, 2.2, 1.8)), "pal.tiber": (TIBER[2], (3.4, 2.2, 1.8))}

# Colour states of the seasons (seasons.md §4.3) the shader makes by swapping ramps; the other
# states (bare, bloom, fruit, crops' stages, snow looks) change shapes and stay drawn.
STATES = ("fresh", "dry", "dormant", "turn", "green", "bare", "gone")
# The states each green ramp has, by what it is (seasons.md §4.3: grass greens, dries and goes
# dormant, and a woodland floor turns under fallen leaves; deciduous leaves come fresh, dry in
# drought and turn in autumn). The engine picks the state by the item's or terrain's season class.
# The engine reads a ramp's states by the climate's month words (look-notes-for-art.md §1): with no
# state for a month's word a ramp keeps its plain colours (`bare` falls back to `dormant`, then
# `dry`; `gone` to `dry`). Leaves wither (`dormant`) and fall to twigs (`bare`); blossom shows only
# in its bloom months (leaf colours `fresh`/`green` otherwise); meadow flowers fade into the grass.
GRASS_STATES = ("fresh", "dry", "dormant", "turn")
LEAF_STATES = ("fresh", "dry", "dormant", "turn", "bare")
BLOOM_STATES = ("fresh", "green", "turn", "dormant", "bare")
FLOWER_STATES = ("green", "dry", "gone")
STATE_RAMPS = {"leaf": LEAF_STATES, "grass": GRASS_STATES, "summer": GRASS_STATES, "steppe": GRASS_STATES,
               "pal.leaf": GRASS_STATES, "pal.summer": GRASS_STATES, "pal.steppe": GRASS_STATES,
               "autumn": LEAF_STATES, "gold_leaf": LEAF_STATES, "rust_leaf": LEAF_STATES,
               "pal.autumn": LEAF_STATES, "blossom": BLOOM_STATES, "pal.blossom": BLOOM_STATES,
               "pal.violet": FLOWER_STATES, "pal.poppy": FLOWER_STATES}
# Which climate class a ramp's states follow, where its ramp class alone does not say (the
# engine's rule otherwise: class grass follows grass, foliage_deciduous follows deciduous).
# `pal.leaf` keeps the grass's months: the ground tiles are drawn with it.
FOLLOWS = {"blossom": "early_bloom", "pal.blossom": "early_bloom",
           "pal.violet": "wildflower", "pal.poppy": "wildflower"}
# Each state: one hue family it is drawn from (palette colours) and a lightness shift (Oklab L). Steps darker than
# KEEP_L (outlines, deep crevices) keep their colour, so silhouettes do not change.
STATE_FAMILIES = {
    "fresh": (lambda: LEAF, 0.05),
    "dry": (lambda: [EARTH[0], EARTH[1], *SUMMER, STRAW[3]], 0.0),
    "dormant": (lambda: [EARTH[0], EARTH[1], *STEPPE], -0.02),
    "turn": (lambda: [ROOF[0], ROOF[1], ROOF[2], *AUTUMN, STRAW[2], STRAW[3]], 0.0),
    "green": (lambda: LEAF, 0.0),
    # Twigs: warm grey-browns (the cool greys read lavender on blossom's light steps).
    "bare": (lambda: [EARTH[0], EARTH[1], EARTH[2], EARTH[3], SAND[1], SAND[2]], -0.06),
    "gone": (lambda: [EARTH[0], EARTH[1], *SUMMER, STRAW[3]], 0.0),
}
KEEP_L = 0.33


def oklab_l(rgb) -> float:
    """Oklab lightness of an sRGB colour (0..1)."""
    c = np.asarray(rgb, np.float64) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = lin
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt([l_, m_, s_])
    return float(0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720453 * s_)


@dataclass
class Ramp:
    name: str
    colours: list                     # [(r, g, b)] dark to light
    cls: str
    material: str | None = None
    group: str | None = None
    state_of: str | None = None
    state: str | None = None
    specular: bool = False
    states: dict = field(default_factory=dict)  # state -> ramp name
    id: int = 0

    def entry(self) -> dict:
        d = {"id": self.id, "name": self.name}
        if self.material:
            d["material"] = self.material
        if self.group:
            d["group"] = self.group
        if self.state_of:
            d["state_of"], d["state"] = self.state_of, self.state
        d.update({
            "steps": len(self.colours),
            "colours": ["#%02x%02x%02x" % c for c in self.colours],
            "L": [round(oklab_l(c), 4) for c in self.colours],
            "class": self.cls,
            "shell": SHELL.get(self.cls, 255),
            "porous": self.cls in POROUS,
            "snow": self.cls in SNOW_ON,
            "specular": self.specular,
            "sway": self.cls in SWAY,
            "translucency": TRANSLUCENCY.get(self.cls, 0.0),
            "wet_steps": WET_STEPS.get(self.cls, 0),
            "gloss": GLOSS.get(self.cls, 0.06 if self.cls in POROUS else 0.0),
            "sparkle": SPARKLE_MATERIALS.get(self.material or "", SPARKLE.get(self.cls, 0.0)),
        })
        if d["translucency"]:
            d["trans"] = TRANS.get(self.cls) or "#%02x%02x%02x" % self.colours[-1]
        if self.name in FOLLOWS:
            d["follows"] = FOLLOWS[self.name]
        base = self.state_of or self.name
        if self.cls == "water" and base in BED:
            bed, absorb = BED[base]
            d["bed"], d["absorb"] = bed, list(absorb)
        return d


def _state_ramp(src: Ramp, state: str) -> Ramp:
    family, shift = STATE_FAMILIES[state]
    pool = sorted({_rgb(c) for c in family()}, key=oklab_l)
    lums = [oklab_l(c) for c in pool]
    out, floor = [], -1.0
    for c in src.colours:
        L = oklab_l(c)
        if L < KEEP_L:
            out.append(c)
            floor = max(floor, L)
            continue
        cand = [i for i, l_ in enumerate(lums) if l_ >= floor - 1e-9] or list(range(len(pool)))
        i = min(cand, key=lambda i: (abs(lums[i] - (L + shift)), i))
        out.append(pool[i])
        floor = lums[i]
    return Ramp(f"{src.name}@{state}", out, src.cls, state_of=src.name, state=state)


def _wanted() -> list[Ramp]:
    ramps = [Ramp(m.name, list(m.ramp), MATERIAL_CLASS[m.name], material=m.name,
                  specular=MATERIAL_CLASS[m.name] in SPECULAR_CLASSES or m.name in SPECULAR_MATERIALS)
             for m in MATERIALS]
    ramps += [Ramp(f"pal.{g}", [_rgb(c) for c in cols], GROUP_CLASS[g], group=g,
                   specular=GROUP_CLASS[g] in SPECULAR_CLASSES)
              for g, cols in GROUPS.items()]
    by_name = {r.name: r for r in ramps}
    for name, states in STATE_RAMPS.items():
        src = by_name[name]
        for st in states:
            sr = _state_ramp(src, st)
            src.states[st] = sr.name
            ramps.append(sr)
    for r in ramps:
        assert 1 <= len(r.colours) <= STEPS, r.name
    return ramps


@lru_cache(maxsize=1)
def table() -> tuple:
    """The ramps with their ids: (ramps in id order, {name: Ramp})."""
    ramps = _wanted()
    known = {}
    if COMMITTED.exists():
        known = {e["name"]: e["id"] for e in json.loads(COMMITTED.read_text())["ramps"]}
    nxt = max(known.values(), default=0) + 1
    for r in ramps:
        if r.name in known:
            r.id = known[r.name]
        else:
            r.id, nxt = nxt, nxt + 1
    if max(r.id for r in ramps) > 255:
        raise SystemExit("ramps: more than 255 ramp ids")
    ramps.sort(key=lambda r: r.id)
    return ramps, {r.name: r for r in ramps}


def arrays():
    """Lookup arrays for resolving pixels: (colours (256, 8) int64 codes with -1 past a ramp's
    end, material id -> ramp id (uint8), sorted colour codes with their group ramp id and step,
    snow-eligible flag per ramp id)."""
    return _arrays()


@lru_cache(maxsize=1)
def _arrays():
    ramps, by_name = table()
    cols = np.full((256, STEPS), -1, np.int64)
    snow = np.zeros(256, bool)
    for r in ramps:
        for i, (a, b, c) in enumerate(r.colours):
            cols[r.id, i] = (a << 16) | (b << 8) | c
        snow[r.id] = r.cls in SNOW_ON
    mat_ramp = np.zeros(len(MATERIALS) + 1, np.int64)
    for i, m in enumerate(MATERIALS):
        mat_ramp[i + 1] = by_name[m.name].id
    codes, gid, gstep = [], [], []
    for g in GROUPS:
        r = by_name[f"pal.{g}"]
        for i, (a, b, c) in enumerate(r.colours):
            codes.append((a << 16) | (b << 8) | c)
            gid.append(r.id)
            gstep.append(i)
    order = np.argsort(codes)
    return (cols, mat_ramp, np.asarray(codes, np.int64)[order], np.asarray(gid, np.int64)[order],
            np.asarray(gstep, np.int64)[order], snow)


def write(out_dir: Path) -> None:
    """`ramps.png` (row = ramp id, eight texels dark to light, alpha 0 past the ramp's end; row 0
    empty) and `ramps.json` beside it."""
    ramps, _ = table()
    rows = max(r.id for r in ramps) + 1
    img = np.zeros((rows, STEPS, 4), np.uint8)
    for r in ramps:
        for i, c in enumerate(r.colours):
            img[r.id, i, :3] = c
            img[r.id, i, 3] = 255
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(out_dir / "ramps.png", optimize=True)
    doc = {"version": 1, "texture": "ramps.png", "steps": STEPS, "classes": list(CLASSES),
           "states": list(STATES), "ramps": []}
    for r in ramps:
        e = r.entry()
        if r.states:
            e["states"] = {st: next(x.id for x in ramps if x.name == n) for st, n in r.states.items()}
        doc["ramps"].append(e)
    (out_dir / "ramps.json").write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else spec.ASSETS / "atlas"
    write(out)
    print(f"ramps: {len(table()[0])} ramps -> {out}")
