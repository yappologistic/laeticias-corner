"""Layer files `.lcw` (world-tech §2.4): writer, reader, and the plan <-> grid plane conversion.

A `LayerGrid` is exactly what the file holds (grid orientation, x fastest). A `PlanLayer` is the
same data north-up in plan coordinates, which is how worldgen builds and checks layers.

Level byte: bits 0-3 level, bits 4-5 aux, bit 6 impassable, bit 7 reserved.
Terrain plane values: table index, TRANSPARENT (0xFE) or NO_GROUND (0xFF).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np

from .coords import COLS

MAGIC = b"LCWL"
VERSION = 1
TRANSPARENT = 0xFE
NO_GROUND = 0xFF
MAX_TERRAINS = 0xFE  # indices 0..253

LEVEL_MASK = 0x0F
AUX_SHIFT = 4
IMPASSABLE = 0x40


class LayerFormatError(ValueError):
    pass


@dataclass
class LayerItem:
    id_index: int
    x: int  # relative to x0
    y: int  # relative to y0
    variant: int
    flags: int = 0


@dataclass
class LayerGrid:
    x0: int
    y0: int
    w: int
    h: int
    terrains: list[str]
    districts: list[str]
    item_ids: list[str]
    T: np.ndarray  # uint8 [h, w], row = y
    L: np.ndarray
    D: np.ndarray
    items: list[LayerItem] = field(default_factory=list)


@dataclass
class PlanItem:
    id: str
    c: int  # plan origin of the footprint: its north-west tile
    r: int
    pw: int  # plan width (east-west) and height (north-south)
    ph: int
    variant: int


@dataclass
class PlanLayer:
    """Plan-oriented layer: arrays [h, w] over plan rect (c0, r0)..(c0 + w - 1, r0 + h - 1)."""

    c0: int
    r0: int
    w: int
    h: int
    terrains: list[str]
    districts: list[str]
    T: np.ndarray  # uint8 index into terrains, TRANSPARENT or NO_GROUND
    L: np.ndarray  # uint8 level byte
    D: np.ndarray  # uint8 index into districts
    items: list[PlanItem] = field(default_factory=list)


# --- RLE -----------------------------------------------------------------------------------

def rle_encode(values: np.ndarray) -> bytes:
    v = values.ravel()
    if v.size == 0:
        return b""
    out = bytearray()
    # Run boundaries, then split long runs into chunks of 256.
    change = np.flatnonzero(np.diff(v)) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [v.size]))
    for s, e in zip(starts.tolist(), ends.tolist()):
        val = int(v[s])
        n = e - s
        while n > 0:
            k = min(n, 256)
            out += bytes((val, k - 1))
            n -= k
    return bytes(out)


def rle_decode(data: bytes, pos: int, n: int) -> tuple[np.ndarray, int]:
    out = np.empty(n, dtype=np.uint8)
    filled = 0
    while filled < n:
        if pos + 2 > len(data):
            raise LayerFormatError("plane truncated")
        val, run = data[pos], data[pos + 1] + 1
        if filled + run > n:
            raise LayerFormatError("run past the end of a plane")
        out[filled:filled + run] = val
        filled += run
        pos += 2
    return out, pos


# --- file ----------------------------------------------------------------------------------

def _string(s: str) -> bytes:
    b = s.encode()
    if len(b) > 255:
        raise LayerFormatError(f"string too long for a layer table: {s!r}")
    return bytes((len(b),)) + b


def write_lcw(lg: LayerGrid) -> bytes:
    if len(lg.terrains) > MAX_TERRAINS:
        raise LayerFormatError(f"{len(lg.terrains)} terrain ids; at most {MAX_TERRAINS}")
    if len(lg.districts) > 256 or len(lg.item_ids) > 0xFFFF:
        raise LayerFormatError("too many districts or item ids for one layer")
    out = bytearray()
    out += MAGIC + struct.pack("<HH", VERSION, 0)
    out += struct.pack("<hhHH", lg.x0, lg.y0, lg.w, lg.h)
    out += struct.pack("<HHHH", len(lg.terrains), len(lg.districts), len(lg.item_ids), 0)
    for s in (*lg.terrains, *lg.districts, *lg.item_ids):
        out += _string(s)
    for plane in (lg.T, lg.L, lg.D):
        if plane.shape != (lg.h, lg.w):
            raise LayerFormatError("plane shape does not match the layer rect")
        out += rle_encode(plane.astype(np.uint8))
    out += struct.pack("<I", len(lg.items))
    for it in lg.items:
        out += struct.pack("<HHHBB", it.id_index, it.x, it.y, it.variant, it.flags)
    return bytes(out)


def read_lcw(data: bytes, grid: tuple[int, int] | None = None) -> LayerGrid:
    """Parse and check a layer as the engine does (world-tech §2.4 "Validation by the engine")."""
    if len(data) < 24 or data[:4] != MAGIC:
        raise LayerFormatError("bad magic")
    version, _ = struct.unpack_from("<HH", data, 4)
    if version != VERSION:
        raise LayerFormatError(f"unsupported version {version}")
    x0, y0, w, h = struct.unpack_from("<hhHH", data, 8)
    nt, nd, ni, _ = struct.unpack_from("<HHHH", data, 16)
    if grid and (x0 < 0 or y0 < 0 or x0 + w > grid[0] or y0 + h > grid[1]):
        raise LayerFormatError("layer rect outside the grid")
    pos = 24
    strings = []
    for _ in range(nt + nd + ni):
        if pos >= len(data):
            raise LayerFormatError("string table truncated")
        n = data[pos]
        if pos + 1 + n > len(data):
            raise LayerFormatError("string table truncated")
        strings.append(data[pos + 1:pos + 1 + n].decode())
        pos += 1 + n
    planes = []
    for _ in range(3):
        p, pos = rle_decode(data, pos, w * h)
        planes.append(p.reshape(h, w))
    if pos + 4 > len(data):
        raise LayerFormatError("item count missing")
    (count,) = struct.unpack_from("<I", data, pos)
    pos += 4
    if pos + 8 * count != len(data):
        raise LayerFormatError("item block size does not match the count (or trailing bytes)")
    items = []
    for _ in range(count):
        idx, x, y, v, f = struct.unpack_from("<HHHBB", data, pos)
        pos += 8
        if idx >= ni or x >= w or y >= h:
            raise LayerFormatError("item outside the layer or id index out of range")
        items.append(LayerItem(idx, x, y, v, f))
    return LayerGrid(x0, y0, w, h, strings[:nt], strings[nt:nt + nd], strings[nt + nd:],
                     planes[0], planes[1], planes[2], items)


# --- orientation -----------------------------------------------------------------------------

def plan_to_grid(pl: PlanLayer, footprint) -> LayerGrid:
    """`footprint(id, variant)` gives an item's plan (pw, ph) for its stored variant."""
    # Grid plane G[j][i] (j = y - y0, i = x - x0) = A[i][w - 1 - j]: transpose, then flip rows.
    def g(a):
        return np.ascontiguousarray(a.T[::-1])

    x0 = pl.r0
    y0 = COLS - 1 - (pl.c0 + pl.w - 1)
    item_ids = sorted({it.id for it in pl.items})
    index = {s: i for i, s in enumerate(item_ids)}
    items = []
    for it in pl.items:
        tx = it.r
        ty = COLS - 1 - (it.c + it.pw - 1)  # origin tile = north-east corner in plan
        items.append(LayerItem(index[it.id], tx - x0, ty - y0, it.variant))
    items.sort(key=lambda i: (i.y, i.x, i.id_index, i.variant))
    return LayerGrid(x0, y0, pl.h, pl.w, list(pl.terrains), list(pl.districts), item_ids,
                     g(pl.T), g(pl.L), g(pl.D), items)


def grid_to_plan(lg: LayerGrid, footprint) -> PlanLayer:
    """Inverse of plan_to_grid; `footprint(id, variant)` gives the item's plan (pw, ph)."""
    def p(a):
        return np.ascontiguousarray(a[::-1].T)

    c0 = COLS - 1 - (lg.y0 + lg.h - 1)
    r0 = lg.x0
    items = []
    for it in lg.items:
        iid = lg.item_ids[it.id_index]
        pw, ph = footprint(iid, it.variant)
        tx, ty = lg.x0 + it.x, lg.y0 + it.y
        c = COLS - 1 - ty - (pw - 1)
        items.append(PlanItem(iid, c, tx, pw, ph, it.variant))
    return PlanLayer(c0, r0, lg.h, lg.w, list(lg.terrains), list(lg.districts),
                     p(lg.T), p(lg.L), p(lg.D), items)
