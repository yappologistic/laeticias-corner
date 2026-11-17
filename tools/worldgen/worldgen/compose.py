"""Compose layers into one world, by the engine's rule (world-tech §2.4 "Composition rule"):
layers apply in order, a non-transparent cell overwrites the cell below, and an item of a lower
layer whose footprint touches any non-transparent cell of a higher layer is dropped.

The world is held north-up in plan orientation, [R, C], with global string tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .coords import COLS, ROWS
from .layer import NO_GROUND, TRANSPARENT, PlanLayer

NONE16 = 0xFFFF


@dataclass
class WItem:
    id: str
    c: int
    r: int
    pw: int
    ph: int
    k: int
    layer: str
    src: str = ""

    def tiles(self):
        for r in range(self.r, self.r + self.ph):
            for c in range(self.c, self.c + self.pw):
                yield c, r


@dataclass
class World:
    terrains: list[str] = field(default_factory=list)
    districts: list[str] = field(default_factory=list)
    layers: list[str] = field(default_factory=list)
    T: np.ndarray = None  # uint16 global terrain index or NONE16 (no ground)
    L: np.ndarray = None  # uint8 level byte
    D: np.ndarray = None  # uint16 district index or NONE16
    owner: np.ndarray = None  # uint8 index into layers of the layer that set the cell
    items: list[WItem] = field(default_factory=list)
    occ: np.ndarray = None  # int32 item index or -1
    dropped: list[tuple[WItem, str]] = field(default_factory=list)
    overlaps: list[tuple[WItem, WItem, tuple[int, int]]] = field(default_factory=list)

    def terrain_id(self, c: int, r: int) -> str | None:
        t = int(self.T[r, c])
        return None if t == NONE16 else self.terrains[t]

    def level(self, c: int, r: int) -> int:
        return int(self.L[r, c]) & 0x0F


def compose(layers: list[tuple[str, PlanLayer]], srcs: dict[str, list[str]] | None = None) -> World:
    w = World()
    w.T = np.full((ROWS, COLS), NONE16, dtype=np.uint16)
    w.L = np.zeros((ROWS, COLS), dtype=np.uint8)
    w.D = np.full((ROWS, COLS), NONE16, dtype=np.uint16)
    w.owner = np.zeros((ROWS, COLS), dtype=np.uint8)
    w.occ = np.full((ROWS, COLS), -1, dtype=np.int32)
    t_index: dict[str, int] = {}
    d_index: dict[str, int] = {}
    for li, (name, pl) in enumerate(layers):
        w.layers.append(name)
        sl = (slice(pl.r0, pl.r0 + pl.h), slice(pl.c0, pl.c0 + pl.w))
        set_m = pl.T != TRANSPARENT
        tmap = np.zeros(256, dtype=np.uint16)
        for i, t in enumerate(pl.terrains):
            if t not in t_index:
                t_index[t] = len(w.terrains)
                w.terrains.append(t)
            tmap[i] = t_index[t]
        tmap[NO_GROUND] = NONE16
        dmap = np.full(256, NONE16, dtype=np.uint16)
        for i, d in enumerate(pl.districts):
            if d not in d_index:
                d_index[d] = len(w.districts)
                w.districts.append(d)
            dmap[i] = d_index[d]
        # Drop lower items touching cells this layer sets.
        if w.items:
            touched = np.unique(w.occ[sl][set_m])
            for idx in touched[touched >= 0].tolist():
                it = w.items[idx]
                if it.layer != name:
                    w.dropped.append((it, name))
                    _clear(w, idx)
        w.T[sl][set_m] = tmap[pl.T[set_m]]
        w.L[sl][set_m] = pl.L[set_m]
        w.D[sl][set_m] = np.where(pl.T[set_m] == NO_GROUND, NONE16, dmap[pl.D[set_m]])
        w.owner[sl][set_m] = li
        src_list = (srcs or {}).get(name)
        for n, it in enumerate(pl.items):
            wi = WItem(it.id, it.c, it.r, it.pw, it.ph, it.variant, name,
                       src_list[n] if src_list and n < len(src_list) else f"{name}.lcw")
            idx = len(w.items)
            w.items.append(wi)
            for c, r in wi.tiles():
                if not (0 <= r < ROWS and 0 <= c < COLS):
                    continue
                if w.occ[r, c] >= 0:
                    w.overlaps.append((w.items[w.occ[r, c]], wi, (c, r)))
                else:
                    w.occ[r, c] = idx
    return w


def _clear(w: World, idx: int) -> None:
    it = w.items[idx]
    it.layer = it.layer + "!dropped"
    for c, r in it.tiles():
        if 0 <= r < ROWS and 0 <= c < COLS and w.occ[r, c] == idx:
            w.occ[r, c] = -1


def live_items(w: World):
    for i, it in enumerate(w.items):
        if not it.layer.endswith("!dropped"):
            yield i, it
