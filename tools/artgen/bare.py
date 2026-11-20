"""Winter looks of deciduous trees (`item/<id>/base/<look>/f<n>@winter`): the tree's own model
with its leaves gone. Branches run from the trunk's top toward where each clump of leaves hung,
thinner as they go, and a sparse fringe of twigs keeps the crown's outline, so a winter wood is
grey-brown lace rather than summer crowns (V7-001). Derived from the summer model, so every
tree, rotation and variant gets its own bare crown with nothing drawn twice."""

from __future__ import annotations

import numpy as np

from arch import rod
from palette import MAT
from voxel import Model, hash01

LEAVES = ("leaf", "leaf_dark", "autumn", "gold_leaf", "rust_leaf", "blossom", "olive", "olive_silver", "grass", "leaf_light")
WOOD = ("bark", "wood", "wood_light", "wood_grey", "cedar")
CELL = 3.0          # design units: one branch per cell of leaves


def winter(m: Model, seed: int) -> Model:
    """`m` with its leaves replaced by bare branches and twigs (in place; returned)."""
    leaf_ids = np.array([MAT[n] for n in LEAVES if n in MAT])
    wood_ids = np.array([MAT[n] for n in WOOD if n in MAT])
    leafy = np.isin(m.mat, leaf_ids)
    if not leafy.any():
        return m
    k = m.k
    X, Y, Z = m.coords()
    X, Y, Z = (np.broadcast_to(a, m.mat.shape) for a in (X, Y, Z))
    wood = np.isin(m.mat, wood_ids)
    lx, ly, lz = X[leafy], Y[leafy], Z[leafy]
    if wood.any():
        wz = Z[wood]
        top = wz.max()
        near = wood & (Z >= top - 1.0)
        tx, ty, tz = X[near].mean(), Y[near].mean(), float(top)
    else:
        tx, ty, tz = lx.mean(), ly.mean(), float(lz.min())
    # The twigs at the crown's edge: leaf voxels with open air beside them, a sparse share.
    pad = np.pad(leafy, 1)
    inner = pad[:-2, 1:-1, 1:-1] & pad[2:, 1:-1, 1:-1] & pad[1:-1, :-2, 1:-1] & pad[1:-1, 2:, 1:-1] \
        & pad[1:-1, 1:-1, 2:]
    shell = leafy & ~inner
    ii = np.argwhere(shell)
    keep = hash01(ii[:, 0], ii[:, 1], ii[:, 2], seed) < 0.07
    m.mat[leafy] = 0
    # Branches: one per cell of former leaves, from the trunk's top (or a fork half way) to it.
    cx, cy, cz = (np.floor(a / CELL).astype(np.int64) for a in (lx, ly, lz))
    cells = {}
    for a, b, c, x, y, z in zip(cx, cy, cz, lx, ly, lz):
        s = cells.setdefault((a, b, c), [0.0, 0.0, 0.0, 0])
        s[0] += x; s[1] += y; s[2] += z; s[3] += 1
    for (a, b, c), (sx, sy, sz, n) in sorted(cells.items()):
        if n < 3:
            continue
        px, py, pz = sx / n, sy / n, sz / n
        if hash01(a, b, c, seed + 1) > 0.45:
            continue
        mid = (tx + (px - tx) * 0.45, ty + (py - ty) * 0.45, tz + (pz - tz) * 0.35)
        rod(m, (tx, ty, tz - 0.5), mid, 0.3, "bark", tone=-0.1)
        rod(m, mid, (px, py, pz), 0.14, "wood_grey", tone=0.1)
    for (i, j, l) in ii[keep]:
        if 0 <= i < m.mat.shape[0] and 0 <= j < m.mat.shape[1] and 0 <= l < m.mat.shape[2]:
            m.mat[i, j, l] = MAT["wood_grey"]
            m.tone[i, j, l] = 0.15
    return m
