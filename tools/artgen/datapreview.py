"""Preview scenes drawn from the packed pages instead of the colour pages (README.md "Data
pages"): normals, heights, ramp classes, the baked-sun and snow bits, and the colour states the
shader makes by swapping ramps (autumn's `turn`, winter's `dormant` with snow on what catches it).

    tools/artgen/.venv/bin/python tools/artgen/datapreview.py [set ...]   (from the repository root)

Writes out/artgen/data/<set>/<scene>_<view>.png: one landmark scene and one street per set.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import setbuild
import spec
from setpreview import Pages

VIEWS = ("colour", "normal", "height", "class", "sun_snow", "autumn", "winter")
CLASS_RGB = {"ground": (150, 112, 70), "grass": (110, 170, 60), "crop": (220, 200, 80), "stone": (150, 150, 160),
             "marble": (235, 230, 215), "plaster": (230, 200, 160), "roof": (190, 80, 60), "wood": (120, 80, 50),
             "metal": (220, 180, 60), "cloth": (200, 60, 160), "skin": (240, 170, 140),
             "foliage_deciduous": (40, 140, 40), "foliage_evergreen": (20, 90, 70), "water": (40, 90, 220),
             "glass": (120, 220, 240), "ink": (30, 30, 40), "snow": (255, 255, 255), "ice": (180, 230, 255),
             "flame": (255, 120, 0)}


def _table():
    doc = json.loads((spec.ASSETS / "atlas" / "ramps.json").read_text())
    colours = np.zeros((256, 8, 3), np.uint8)
    cls = np.zeros((256, 3), np.uint8)
    remap = {st: np.arange(256) for st in doc["states"]}
    snow_ramp = None
    for e in doc["ramps"]:
        for i, c in enumerate(e["colours"]):
            colours[e["id"], i] = [int(c[j:j + 2], 16) for j in (1, 3, 5)]
        colours[e["id"], len(e["colours"]):] = colours[e["id"], len(e["colours"]) - 1]
        cls[e["id"]] = CLASS_RGB[e["class"]]
        for st, rid in e.get("states", {}).items():
            remap[st][e["id"]] = rid
        if e["name"] == "snow":
            snow_ramp = e["id"]
    return colours, cls, remap, snow_ramp


def visualise(colour: np.ndarray, packed: np.ndarray, raw_mask: np.ndarray, view: str) -> np.ndarray:
    """One page drawn as `view`; colour-only sprites keep their colour."""
    colours, cls, remap, snow_ramp = _table()
    v = packed.astype(np.uint32)
    w = v[..., 0] | v[..., 1] << 8 | v[..., 2] << 16 | v[..., 3] << 24
    ramp, step = ((w >> 3) & 255).astype(np.int64), (w & 7).astype(np.int64)
    nx = (((w >> 11) & 31).astype(np.float32) - 15) / 15
    ny = (((w >> 16) & 31).astype(np.float32) - 15) / 15
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    h = ((w >> 21) & 511).astype(np.float32)
    lit, snow = (w >> 30) & 1 == 1, (w >> 31) & 1 == 1
    out = colour.copy()
    data = (ramp > 0) & ~raw_mask
    if view == "colour":
        return out
    if view == "normal":
        rgb = np.stack([(nx + 1) / 2, (ny + 1) / 2, nz], -1) * 255
    elif view == "height":
        t = np.clip(h / 320, 0, 1)
        band = (h.astype(np.int64) // 16) % 2 == 0
        rgb = np.stack([t, 1 - np.abs(t - 0.5) * 2, 1 - t], -1) * (200 + 55 * band[..., None])
    elif view == "class":
        rgb = cls[ramp]
    elif view == "sun_snow":
        rgb = colours[ramp, step] * np.where(lit, 1.0, 0.45)[..., None]
        rgb[snow] = (255, 255, 255)
    elif view == "autumn":          # leaves turn, grass dries
        turn = remap["turn"][ramp]
        rgb = colours[np.where(turn != ramp, turn, remap["dry"][ramp]), step]
    else:                           # winter: dormant ground and leaves, snow where it catches
        rgb = colours[remap["dormant"][ramp], step].astype(np.float32)
        sn = colours[snow_ramp, np.clip(step, 1, 4)]
        rgb[snow] = sn[snow]
    out[data, :3] = np.clip(rgb, 0, 255).astype(np.uint8)[data]
    out[data, 3] = 255
    return out


class DataPages(Pages):
    """A set's pages (and the home atlas) with every page image replaced by its `view`."""

    def __init__(self, out_dir: Path, sets, k, home=None, view="normal"):
        super().__init__(out_dir, sets, k, home)
        by_image = {}
        for key, img in self.images.items():
            by_image.setdefault(id(img), (img, []))[1].append(key)
        files = [p for s in sets for p in sorted(Path(out_dir).glob(f"{s}.[0-9]*.json"))
                 if len(p.name.split(".")) == 3] + ([Path(home)] if home else [])
        for f in files:
            doc = json.loads(f.read_text())
            png = f.parent / doc["image"]
            colour = np.asarray(Image.open(png).convert("RGBA"))
            side = json.loads(png.with_name(png.stem + ".p.json").read_text())
            packed = np.asarray(Image.open(png.with_name(png.stem + ".p.png")).convert("RGBA"))
            raw = np.zeros(colour.shape[:2], bool)
            for key in side["colour_only"]:
                r = doc["sprites"][key]
                raw[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]] = True
            img = Image.fromarray(visualise(colour, packed, raw, view), "RGBA")
            for key in doc["sprites"]:
                self.images[key] = img
        self.cache = {}


def scenes(set_id: str, pages_dir: Path):
    """(name, scene builder taking the pages) for one landmark scene and one street."""
    mod = __import__(f"sets.{set_id}.preview", fromlist=["x"])
    if set_id == "rome":
        return [("forum", mod.forum), ("street", mod.street)]
    pieces, floors = mod._geom(pages_dir) if hasattr(mod, "_geom") else ({}, {})
    if set_id == "parsa":
        return [("terrace", lambda p: mod.terrace(pieces, floors)), ("town", lambda p: mod.town(pieces))]
    if set_id == "athens":
        cat = json.loads((setbuild.SETS / "athens" / "catalog.json").read_text())

        def parthenon(p):
            s = mod.landmark_scene("athens.parthenon", cat, pieces, walkers=(mod._w("citizen", 0),))
            s.floors = floors
            return s
        return [("parthenon", parthenon), ("quarter", lambda p: mod.quarter())]
    return [("roads", lambda p: mod.roads()), ("pass", lambda p: mod.mountain_pass())]


def main(sets) -> int:
    atlas = spec.ASSETS / "atlas"
    home = getattr(__import__("sets.athens.preview", fromlist=["x"]), "HOME", None)
    for s in sets:
        dst = spec.PREVIEWS / "data" / s
        dst.mkdir(parents=True, exist_ok=True)
        for view in VIEWS:
            pages = DataPages(atlas, [s], 2, home=home if s in ("athens", "rome") else None, view=view)
            for name, build in scenes(s, atlas):
                img = build(pages).render(pages)
                img.convert("RGB").save(dst / f"{name}_{view}.png", optimize=True)
        print(f"datapreview {s}: {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["world", "parsa", "athens", "rome"]))
