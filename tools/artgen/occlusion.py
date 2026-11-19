"""Occlusion tops (docs/design/realism.md §1, §5.1): for every item look, the top-down height
field the engine's top map is splatted from, so sun, sky and lamp light pass under arcades,
bridge decks, awnings and canopies and are stopped by walls, where a screen-space height cannot
tell.

One small sprite per item and look on the set's page `<set>.o.png` + `.o.json`, on a grid
aligned with the world's X and Y (the voxel axes: screen x = X - Y, y = (X + Y) / 2 - Z, all in
art px at 1x) at TEXEL art px per texel; `ox`, `oy` in the manifest are the texel column and row
of the item's anchor (the footprint origin's corner, X = Y = 0), so texel (c, r) covers
X in [TEXEL (c - ox), TEXEL (c - ox + 1)), Y likewise with r and oy. RGBA8, raw (not
premultiplied):

- R: the top of the texel's columns, px / 2 (the highest solid voxel + 1);
- G: the underside, px / 2: where open space lies under something (an arcade's ceiling, a
  deck's soffit, an awning, a canopy) the lowest solid above that space; 0 where the texel is
  solid from its floor up (a wall stops a ray at every height up to R);
- B: the material of the top (CODES: 1 solid, 2 foliage, 3 cloth, 4 water, 5 glass);
- A: coverage, the share of the texel's voxel columns holding anything (255 all).

A ray at height z over a texel is blocked when z < R*2 and (G = 0 or z >= G*2): it passes over
the top and under the underside. Texels the item does not cover are all zero."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from pack import Sprite

TEXEL = 4                       # art px per texel in world X and Y (realism.md §1)
MIN_GAP = 10                    # px of open space under something that count as room (a crouch)
CODES = {"solid": 1, "foliage": 2, "cloth": 3, "water": 4, "glass": 5}
CLASS_CODE = {"foliage_deciduous": CODES["foliage"], "foliage_evergreen": CODES["foliage"], "crop": CODES["foliage"],
              "cloth": CODES["cloth"], "water": CODES["water"], "ice": CODES["water"], "glass": CODES["glass"]}


@lru_cache(maxsize=1)
def material_codes() -> np.ndarray:
    """Code (CODES) per voxel material id (0 empty), by the material's ramp class."""
    from palette import MATERIALS
    from ramps import MATERIAL_CLASS
    out = np.zeros(len(MATERIALS) + 1, np.uint8)
    for i, m in enumerate(MATERIALS):
        out[i + 1] = CLASS_CODE.get(MATERIAL_CLASS.get(m.name, ""), CODES["solid"])
    return out


def columns(solid: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per voxel column of `solid` (nx, ny, nz; z index 0 at ground level): whether it holds
    anything, its top (px, the highest solid + 1) and its underside (px; 0 when solid from its
    floor up: no open space of MIN_GAP or more between the floor and something above)."""
    nx, ny, nz = solid.shape
    has = solid.any(axis=2)
    if nz == 0:
        z0 = np.zeros((nx, ny), np.int64)
        return has, z0, z0
    top = np.where(has, nz - np.argmax(solid[:, :, ::-1], axis=2), 0)
    low = np.argmax(solid, axis=2)                          # the lowest solid
    z = np.arange(nz)[None, None, :]
    # Standing on the ground (its lowest solid at the floor): the first gap above that run.
    after = z >= low[..., None]
    empty_after = ~solid & after
    first_empty = np.where(empty_after.any(axis=2), np.argmax(empty_after, axis=2), nz)
    above = solid & (z >= first_empty[..., None])
    nxt = np.where(above.any(axis=2), np.argmax(above, axis=2), nz)
    standing = low < MIN_GAP
    under = np.where(standing, np.where((nxt < nz) & (nxt - first_empty >= MIN_GAP), nxt, 0), low)
    return has, top, np.where(has, under, 0)


def tops(solid: np.ndarray, topmat: np.ndarray, x0: int, y0: int) -> Sprite:
    """The occlusion sprite of voxels `solid` (nx, ny, nz with z index 0 at ground level, 1 voxel
    = 1 art px) whose first column sits at X = x0, Y = y0 px from the anchor; `topmat` (nx, ny)
    the material code of each column's top."""
    has, top, under = columns(solid)
    nx, ny = has.shape
    c0, r0 = int(np.floor(x0 / TEXEL)), int(np.floor(y0 / TEXEL))
    c1, r1 = int(np.ceil((x0 + nx) / TEXEL)), int(np.ceil((y0 + ny) / TEXEL))
    W, H = max(c1 - c0, 1), max(r1 - r0, 1)
    # Pad the columns onto whole texels.
    pa, pb = x0 - c0 * TEXEL, y0 - r0 * TEXEL

    def grid(a, fill=0):
        out = np.full((W * TEXEL, H * TEXEL), fill, a.dtype)
        out[pa:pa + nx, pb:pb + ny] = a
        return out.reshape(W, TEXEL, H, TEXEL).transpose(0, 2, 1, 3).reshape(W, H, TEXEL * TEXEL)
    h, t, u, m = grid(has), grid(top), grid(under), grid(topmat)
    count = h.sum(axis=2)
    texel_top = t.max(axis=2)
    pick = np.argmax(t, axis=2)
    mat = np.take_along_axis(m, pick[..., None], axis=2)[..., 0]
    # Under: open space where most of the covered columns have it; then the lowest of them.
    open_ = h & (u > 0)
    n_open = open_.sum(axis=2)
    lowest = np.where(open_, u, 1 << 20).min(axis=2)
    texel_under = np.where((n_open * 2 > count) & (count > 0), lowest, 0)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 0] = np.clip((texel_top.T + 1) // 2, 0, 255)
    rgba[..., 1] = np.clip(texel_under.T // 2, 0, 255)
    rgba[..., 2] = np.where(count.T > 0, mat.T, 0)
    rgba[..., 3] = np.round(count.T * 255 / (TEXEL * TEXEL)).astype(np.uint8)
    rgba[rgba[..., 3] == 0] = 0
    return Sprite(rgba, -c0, -r0)


def of_model(model) -> Sprite:
    """The occlusion sprite of a (kit) model: its voxels at and above ground level."""
    zero = max(-model.z0, 0)
    mat = model.mat[:, :, zero:]
    solid = mat > 0
    nz = solid.shape[2]
    if nz:
        idx = np.where(solid.any(axis=2), nz - 1 - np.argmax(solid[:, :, ::-1], axis=2), 0)
        topm = material_codes()[np.take_along_axis(mat, idx[..., None], axis=2)[..., 0]]
    else:
        topm = np.zeros(solid.shape[:2], np.uint8)
    return tops(solid, topm, model.x0, model.y0)
