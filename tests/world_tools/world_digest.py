#!/usr/bin/env python3
"""Digest of the committed world as tools/worldgen reads it, for the C++ cross-check.

The digest is defined in src/world/digest.hpp. This script reads the layers with worldgen's own
reader (worldgen.layer.read_lcw), composes them with worldgen's own composition
(worldgen.compose.compose) and reads the graphs with worldgen.graph.read_graph, applying the
engine's rule for ids: an item resolves only from assets/catalog.json and the set catalogs
(drafts and plan/provisional.py stand-ins are worldgen's, not the engine's); others are counted as
unresolved and left out before composing. The C++ test (tests/world_real.cpp) compares its own
digest of the same files with the committed output, so both readers must agree byte for byte.

Regenerate the fixture after any change to assets/world/ or the catalogs (repository root):

    tools/worldgen/.venv/bin/python tests/world_tools/world_digest.py \
        > tests/fixtures/world/digest.json

(`tools/worldgen/build.sh --test` creates that virtualenv on first use.)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/worldgen"))

from worldgen.catalog import Catalog  # noqa: E402
from worldgen.compose import NONE16, compose, live_items  # noqa: E402
from worldgen.coords import COLS  # noqa: E402
from worldgen.graph import read_graph  # noqa: E402
from worldgen.layer import grid_to_plan, read_lcw  # noqa: E402

CHUNK = 32
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK = 0xFFFFFFFFFFFFFFFF


def fnv(data: bytes) -> int:
    h = FNV_OFFSET
    for b in data:
        h = ((h ^ b) * FNV_PRIME) & MASK
    return h


def main() -> int:
    cat = Catalog(ROOT)
    world_dir = ROOT / "assets/world"
    world = json.loads((world_dir / "world.json").read_text())
    gw, gh = world["grid"]

    def footprint(iid: str, variant: int) -> tuple[int, int]:
        fx, fy = cat.items[iid].footprint_k(variant)
        return (fy, fx)  # plan (east-west, north-south) extents

    layers, names, graphs = [], [], {}
    unresolved: Counter = Counter()
    portals: set[str] = set()
    merged = 0
    for ref in world["layers"]:
        f = world_dir / ref["file"]
        if not f.exists():
            continue
        lg = read_lcw(f.read_bytes(), (gw, gh))
        known = {i for i, iid in enumerate(lg.item_ids)
                 if iid in cat.items and cat.items[iid].source == "catalog"}
        for it in lg.items:
            if it.id_index not in known:
                unresolved[lg.item_ids[it.id_index]] += 1
        lg.items = [it for it in lg.items if it.id_index in known]
        layers.append((ref["id"], grid_to_plan(lg, footprint)))
        names.append(ref["id"])
        gf = world_dir / ref.get("graph", "")
        if ref.get("graph") and gf.exists():
            g = read_graph(gf.read_text())
            graphs[ref["id"]] = {"nodes": len(g.nodes), "edges": len(g.edges),
                                 "lanes": len(g.lanes)}
            for n in g.nodes:
                if n.kind == "portal":
                    if n.id in portals:
                        continue
                    portals.add(n.id)
                merged += 1
    w = compose(layers)

    # Grid orientation: G[ty][tx] = P[r = tx][c = COLS - 1 - ty].
    T = w.T.T[::-1]
    L = w.L.T[::-1]
    D = w.D.T[::-1]
    tnames = [t.encode() + b"\0" for t in w.terrains]
    dnames = [d.encode() + b"\0" for d in w.districts]
    cx_n, cy_n = (gw + CHUNK - 1) // CHUNK, (gh + CHUNK - 1) // CHUNK
    items_by_chunk: dict[int, list] = {}
    counts: Counter = Counter()
    for _, it in live_items(w):
        tx, ty = it.r, COLS - 1 - (it.c + it.pw - 1)
        counts[it.id] += 1
        items_by_chunk.setdefault((ty // CHUNK) * cx_n + tx // CHUNK, []).append(
            (ty, tx, it.id, it.k))
    chunks = []
    for cy in range(cy_n):
        for cx in range(cx_n):
            ys = slice(cy * CHUNK, min((cy + 1) * CHUNK, gh))
            xs = slice(cx * CHUNK, min((cx + 1) * CHUNK, gw))
            t = b"".join(b"\0" if v == NONE16 else tnames[v] for v in T[ys, xs].ravel().tolist())
            lv = bytes(L[ys, xs].ravel().tolist())
            d = b"".join(b"\0" if v == NONE16 else dnames[v] for v in D[ys, xs].ravel().tolist())
            ib = bytearray()
            for y, x, iid, k in sorted(items_by_chunk.get(cy * cx_n + cx, [])):
                ib += iid.encode() + b"\0" + x.to_bytes(2, "little") + y.to_bytes(2, "little")
                ib += bytes((k,))
            chunks.append([f"{fnv(t):016x}", f"{fnv(lv):016x}", f"{fnv(d):016x}",
                           f"{fnv(bytes(ib)):016x}"])
    doc = {
        "version": 1,
        "grid": [gw, gh],
        "chunk": CHUNK,
        "layers": names,
        "items_total": sum(counts.values()),
        "item_counts": dict(sorted(counts.items())),
        "unresolved": dict(sorted(unresolved.items())),
        "graphs": dict(sorted(graphs.items())),
        "merged_nodes": merged,
        "chunks": chunks,
    }
    sys.stdout.write(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
