"""Everything worldgen knows about content: catalogs, atlas pages and geometry files.

Sources, in order of authority (an id is taken from the first that defines it):
  1. `assets/catalog.json` (home set) and `assets/sets/<set>/catalog.json`        "catalog"
  2. drafts: `docs/design/sets/<set>.json` for a set without a catalog yet       "draft"
  3. `tools/worldgen/plan/provisional.py`, worldgen's stand-ins for sets whose
     catalogs do not exist yet                                                     "provisional"
Ids from 2 and 3 validate with a warning (V1), so layouts can be written before the set catalogs
land, and nothing slips through once they do.

Atlas pages: `assets/atlas.json` (+ png) for the home set, `assets/atlas/<set>.<n>.json` for sets.
Geometry: `assets/atlas/<set>.geom.json` (world-tech §1.10).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from plan import provisional

SETS_DEFAULT = ["world", "rome", "athens", "parsa"]
# Terrains walkers cannot stand on and `on: water` items need. Catalog terrain may say
# `"water": true`; otherwise these names (the part after the set prefix) decide.
WATER_NAMES = {"water", "sea", "shallows", "river", "river_tiber", "water_channel"}


def set_of(ident: str) -> str:
    return ident.split(".", 1)[0] if "." in ident else "home"


@dataclass
class TerrainDef:
    id: str
    base: bool
    under: str | None
    variants: int
    fps: int
    water: bool
    faces: list[str]
    colour: tuple[int, int, int] | None
    source: str
    file: str


@dataclass
class ItemDef:
    id: str
    footprint: tuple[int, int]  # grid (x extent, y extent) at r0
    layout: str
    count: int
    on: str
    walkable: bool
    landmark: bool
    rotations: list[int]
    rise: int
    axis: str | None
    height: int | None
    glow: bool
    layers: list[str]
    card: str | None
    stand_in: str | None
    source: str
    file: str
    extra: dict = field(default_factory=dict)

    @property
    def has_door(self) -> bool:
        """Buildings people enter: home `homes`, a catalog door slot beside the item, or a
        provisional `door` flag. Their door must open onto a walkable tile (V7)."""
        if self.extra.get("category") == "homes" or self.extra.get("door"):
            return True
        return any(s.get("kind") == "door" and s.get("where") != "on"
                   for s in self.extra.get("slots", []) if isinstance(s, dict))

    def footprint_k(self, k: int) -> tuple[int, int]:
        fx, fy = self.footprint
        return (fy, fx) if self.layout == "rotate" and k % 2 == 1 else (fx, fy)


class Catalog:
    def __init__(self, root: Path):
        self.root = Path(root)
        home = json.loads((self.root / "assets/catalog.json").read_text())
        self.tile_w = int(home["tile"]["w"])
        self.tile_h = int(home["tile"]["h"])
        # world-tech §1.6: tile.level, default half a tile height until the catalog states it.
        self.level_px = int(home["tile"].get("level", self.tile_h // 2))
        self.sets: list[str] = list(home.get("sets", SETS_DEFAULT))
        self.terrain: dict[str, TerrainDef] = {}
        self.items: dict[str, ItemDef] = {}
        self.base_terrain_home = next(t["id"] for t in home["terrain"] if t.get("base"))
        self._load_doc(home, "catalog", "assets/catalog.json")
        for s in self.sets:
            real = self.root / f"assets/sets/{s}/catalog.json"
            draft = self.root / f"docs/design/sets/{s}.json"
            if real.exists():
                self._load_doc(json.loads(real.read_text()), "catalog", f"assets/sets/{s}/catalog.json")
            elif draft.exists():
                self._load_doc(json.loads(draft.read_text()), "draft", str(draft.relative_to(self.root)))
        self._load_provisional()
        self.retired: dict[str, str] = dict(provisional.RETIRED)
        self.geom = self._load_geometry()

    # -- loading ----------------------------------------------------------------------------

    def _terrain(self, t: dict, source: str, file: str) -> TerrainDef:
        tid = t["id"]
        base = bool(t.get("base", False))
        under = t.get("under")
        if not base and under is None and set_of(tid) == "home":
            under = self.base_terrain_home
        name = tid.split(".", 1)[-1]
        colour = t.get("colour")
        return TerrainDef(
            id=tid, base=base, under=under, variants=int(t.get("variants", 1)),
            fps=int(t.get("fps", 0)), water=bool(t.get("water", name in WATER_NAMES)),
            faces=list(t.get("faces", [])), colour=tuple(colour) if colour else None,
            source=source, file=file)

    def _item(self, i: dict, source: str, file: str) -> ItemDef:
        layout = i.get("layout", "variant")
        landmark = bool(i.get("landmark", False))
        count = int(i.get("count", 16 if layout == "connect" else 1))
        rotations = i.get("rotations")
        if rotations is None:
            rotations = [0] if landmark else (list(range(count)) if layout == "rotate" else [0])
        layers = i.get("layers") or (["base", "shadow", "glow"] if i.get("glow") else ["base", "shadow"])
        known = {"id", "name", "footprint", "layout", "count", "on", "walkable", "landmark",
                 "rotations", "rise", "axis", "height", "glow", "layers", "card", "stand_in"}
        return ItemDef(
            id=i["id"], footprint=tuple(i.get("footprint", [1, 1])), layout=layout, count=count,
            on=i.get("on", "land"), walkable=bool(i.get("walkable", False)), landmark=landmark,
            rotations=list(rotations), rise=int(i.get("rise", 0)), axis=i.get("axis"),
            height=i.get("height"), glow="glow" in layers, layers=list(layers),
            card=i.get("card"), stand_in=i.get("stand_in"), source=source, file=file,
            extra={k: v for k, v in i.items() if k not in known})

    def _load_doc(self, doc: dict, source: str, file: str) -> None:
        for t in doc.get("terrain", []):
            if t["id"] not in self.terrain:
                self.terrain[t["id"]] = self._terrain(t, source, file)
        for i in doc.get("items", []):
            if i["id"] not in self.items:
                self.items[i["id"]] = self._item(i, source, file)

    def _load_provisional(self) -> None:
        file = "tools/worldgen/plan/provisional.py"
        for t in provisional.TERRAIN:
            if t["id"] not in self.terrain:
                self.terrain[t["id"]] = self._terrain(t, "provisional", file)
        for i in provisional.ITEMS:
            if i["id"] not in self.items:
                self.items[i["id"]] = self._item(i, "provisional", file)

    def _load_geometry(self) -> dict:
        geom: dict = {}
        d = self.root / "assets/atlas"
        if d.is_dir():
            for f in sorted(d.glob("*.geom.json")):
                doc = json.loads(f.read_text())
                for iid, rots in doc.get("items", {}).items():
                    geom[iid] = rots
        return geom

    # -- queries ----------------------------------------------------------------------------

    def is_water(self, terrain_id: str) -> bool:
        t = self.terrain.get(terrain_id)
        return bool(t and t.water)

    def drawn_base(self, terrain_id: str) -> str:
        """The base terrain drawn under a tile of this terrain (itself when it is a base)."""
        t = self.terrain.get(terrain_id)
        if t is None or t.base:
            return terrain_id
        return t.under or terrain_id

    def faces(self, terrain_id: str) -> list[str]:
        """Edge materials a raised tile of this terrain may use (the level byte's aux picks one).
        An overlay that lists none uses the faces of the base drawn under it."""
        t = self.terrain.get(terrain_id)
        if t is None:
            return []
        if t.faces or t.base:
            return t.faces
        b = self.terrain.get(t.under or "")
        return b.faces if b else []

    def slots(self, item_id: str, k: int) -> dict:
        """Slot spots from the geometry file for rotation k ({} when there is no geometry)."""
        return self.geom.get(item_id, {}).get(f"r{k}", {}).get("slots", {})

    def walk_tiles(self, item_id: str, k: int) -> list[tuple[int, int]]:
        return [tuple(t) for t in self.geom.get(item_id, {}).get(f"r{k}", {}).get("walk", [])]

    def slot_kind(self, item_id: str, slot_id: str) -> str | None:
        """The catalog `kind` of an item's slot (`mooring` spots are a boat's, on water)."""
        d = self.items.get(item_id)
        for s in d.extra.get("slots", []) if d else []:
            if isinstance(s, dict) and s.get("id") == slot_id:
                return s.get("kind")
        return None


class Atlas:
    """All atlas pages present, as one key space. Images load lazily, sprites are cached."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.where: dict[str, tuple[Path, dict]] = {}
        pages = [self.root / "assets/atlas.json"]
        d = self.root / "assets/atlas"
        if d.is_dir():
            pages += sorted(p for p in d.glob("*.json") if not p.name.endswith(".geom.json"))
        for manifest in pages:
            if not manifest.exists():
                continue
            doc = json.loads(manifest.read_text())
            png = manifest.parent / doc["image"]
            for key, rect in doc["sprites"].items():
                self.where.setdefault(key, (png, rect))
        self._images: dict[Path, Image.Image] = {}
        self._cache: dict[str, tuple[Image.Image, int, int] | None] = {}

    def has(self, key: str) -> bool:
        return key in self.where

    def get(self, key: str) -> tuple[Image.Image, int, int] | None:
        """(RGBA sprite, ox, oy) or None when the key is on no page."""
        if key in self._cache:
            return self._cache[key]
        found = self.where.get(key)
        out = None
        if found:
            png, r = found
            if png not in self._images:
                self._images[png] = Image.open(png).convert("RGBA")
            im = self._images[png].crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
            out = (im, int(r["ox"]), int(r["oy"]))
        self._cache[key] = out
        return out

    def frames(self, prefix: str) -> int:
        n = 0
        while f"{prefix}/f{n}" in self.where:
            n += 1
        return n

    def mean_colour(self, key: str) -> tuple[int, int, int] | None:
        s = self.get(key)
        if s is None:
            return None
        import numpy as np
        a = np.asarray(s[0], dtype=np.float64)
        w = a[..., 3:4] / 255.0
        if w.sum() == 0:
            return None
        rgb = (a[..., :3] * w).sum(axis=(0, 1)) / w.sum()
        return tuple(int(round(v)) for v in rgb)
