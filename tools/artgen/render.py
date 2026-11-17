"""Exact ray casting of voxel models into the 2:1 projection, with palette-ramp shading.

Screen: sx = x - y, sy = (x + y) / 2 - z, anchor at world (0, 0, 0). Pixels are sampled at their
centres, so ground diamonds of neighbouring tiles partition the screen with no gaps or overlap.
Every ray through a pixel centre runs along (1, 1, 1); along it, cell boundaries fall at fixed
fractions of t, so three samples per unit of t visit every voxel the ray crosses.
"""

from dataclasses import dataclass

import numpy as np

from palette import MATERIALS
from pack import Sprite
from voxel import Model, box_blur, hash01

SUN = np.array([-0.45, 0.28, 0.85], np.float32)
SUN /= np.linalg.norm(SUN)
# Ground shadows use a higher sun than the shading so they stay compact on a crowded map.
SHADOW_SUN = np.array([-0.38, 0.16, 0.91], np.float32)
SHADOW_SUN /= np.linalg.norm(SHADOW_SUN)
AMBIENT, DIFFUSE = 0.42, 0.58
FACE_NORMALS = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], np.float32)  # top, +x, +y
SHADOW_ALPHA = (0, 58, 88, 116)
AO_PAD = 5

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
                  np.float32) / 16 + 1 / 32

N_MAT = len(MATERIALS) + 1
RAMP_LEN = np.array([0] + [len(m.ramp) for m in MATERIALS], np.float32)
BIAS = np.array([0] + [m.bias for m in MATERIALS], np.float32)
TEXTURE = np.array([0] + [m.texture for m in MATERIALS], np.float32)
GLOWS = np.array([(0, 0, 0)] + [m.glow or (0, 0, 0) for m in MATERIALS], np.uint8)
HAS_GLOW = np.array([False] + [m.glow is not None for m in MATERIALS])
RAMPS = np.zeros((N_MAT, 8, 3), np.uint8)
for _i, _m in enumerate(MATERIALS):
    RAMPS[_i + 1, :len(_m.ramp)] = _m.ramp
    RAMPS[_i + 1, len(_m.ramp):] = _m.ramp[-1]


def dither(value, px, py, band=0.55):
    """Floor `value` after a restrained ordered dither: only fractions near .5 get mixed."""
    frac = value - np.floor(value)
    f = np.clip((frac - 0.5) / band + 0.5, 0, 1)
    return np.floor(value) + (f > BAYER4[py % 4, px % 4])


@dataclass
class Layers:
    base: Sprite
    shadow: Sprite
    glow: Sprite | None


def _bounds(model: Model):
    nx, ny, nz = model.mat.shape
    xs = (model.x0, model.x0 + nx)
    ys = (model.y0, model.y0 + ny)
    zs = (model.z0, model.z0 + nz)
    sx = [x - y for x in xs for y in ys]
    sy = [(x + y) / 2 - z for x in xs for y in ys for z in zs]
    return int(np.floor(min(sx))), int(np.ceil(max(sx))), int(np.floor(min(sy))), int(np.ceil(max(sy)))


def _occupancy(model: Model, pad: int):
    """Solid mask (context voxels included) padded by `pad`; below z = 0 is solid ground
    unless the model hovers."""
    occ = np.pad(model.mat > 0, pad)
    if not model.hover:
        ground = np.arange(occ.shape[2]) + model.z0 - pad < 0
        occ[:, :, ground] = True
    return occ


def _sample(grid, p, x0, y0, z0, pad):
    i = np.clip(np.floor(p[:, 0]).astype(np.int64) - x0 + pad, 0, grid.shape[0] - 1)
    j = np.clip(np.floor(p[:, 1]).astype(np.int64) - y0 + pad, 0, grid.shape[1] - 1)
    k = np.clip(np.floor(p[:, 2]).astype(np.int64) - z0 + pad, 0, grid.shape[2] - 1)
    return grid[i, j, k]


def _ambient_occlusion(model: Model, centre, nrm):
    """How enclosed each surface point is: blurred solidity probed a little way along the normal."""
    occ = _occupancy(model, AO_PAD).astype(np.float32)
    near, far = box_blur(occ, 1), box_blur(occ, 3)
    args = (model.x0, model.y0, model.z0, AO_PAD)
    a = _sample(near, centre + nrm * 1.6, *args)
    b = _sample(far, centre + nrm * 3.5, *args)
    return np.clip(1.08 - 0.55 * a - 0.75 * b, 0.5, 1.0)


def _raycast(model: Model, px, py, mat_grid):
    sx, sy = px + 0.5, py + 0.5
    a, b = sy + sx / 2, sy - sx / 2
    even = (px % 2) == 0
    nx, ny, nz = model.mat.shape
    n = px.size
    mat = np.zeros(n, np.uint8)
    face = np.zeros(n, np.int8)
    ii = np.zeros(n, np.int64)
    jj = np.zeros(n, np.int64)
    kk = np.zeros(n, np.int64)
    depth = np.full(n, -1e9, np.float32)
    todo = np.ones(n, bool)
    for k in range(model.z0 + nz - 1, model.z0 - 1, -1):
        for s, frac in enumerate((0.875, 0.5, 0.125)):
            t = k + frac
            i = np.floor(a + t).astype(np.int64) - model.x0
            j = np.floor(b + t).astype(np.int64) - model.y0
            inside = todo & (i >= 0) & (i < nx) & (j >= 0) & (j < ny)
            if not inside.any():
                continue
            idx = np.nonzero(inside)[0]
            m = mat_grid[i[idx], j[idx], k - model.z0]
            got = idx[m > 0]
            if got.size == 0:
                continue
            mat[got] = m[m > 0]
            ii[got], jj[got], kk[got] = i[got], j[got], k - model.z0
            depth[got] = t
            if s == 0:
                face[got] = 0
            else:
                x_face = even[got] == (s == 2)
                face[got] = np.where(x_face, 1, 2)
            todo[got] = False
        if not todo.any():
            break
    return mat, face, ii, jj, kk, depth


def _shadowed(occ, origin, x0, y0, z0, pad, zmax, sun=SUN, step=0.5):
    """True where a ray from origin (N,3) toward the sun hits a solid voxel."""
    hit = np.zeros(len(origin), bool)
    steps = int(np.ceil((zmax - origin[:, 2].min()) / (sun[2] * step))) + 1
    for s in range(1, steps + 1):
        p = origin + sun * (s * step)
        i = np.floor(p[:, 0]).astype(np.int64) - x0 + pad
        j = np.floor(p[:, 1]).astype(np.int64) - y0 + pad
        k = np.floor(p[:, 2]).astype(np.int64) - z0 + pad
        ok = ~hit & (i >= 0) & (i < occ.shape[0]) & (j >= 0) & (j < occ.shape[1]) & \
            (k >= 0) & (k < occ.shape[2])
        hit[ok] = occ[i[ok], j[ok], k[ok]]
    return hit


def _texture_noise(ii, jj, kk, x0, y0, z0):
    return hash01(ii + x0, jj + y0, kk + z0, 7) - 0.5


def render_base(model: Model):
    """Return (rgba, glow_rgba or None, ox, oy) for the model's visible surfaces."""
    c0, c1, r0, r1 = _bounds(model)
    W, H = c1 - c0, r1 - r0
    py, px = np.mgrid[r0:r1, c0:c1]
    px, py = px.ravel(), py.ravel()
    mat, face, ii, jj, kk, depth = _raycast(model, px, py, model.visible())
    # Outlines follow the whole shape, context included, so a hedge cut at the tile edge
    # gets no seam line where the neighbour's arm continues it.
    if model.ghost is None:
        outline_solid, outline_depth = mat > 0, depth
    else:
        full_mat, _f, _i, _j, _k, full_depth = _raycast(model, px, py, model.mat)
        outline_solid, outline_depth = full_mat > 0, np.where(mat > 0, depth, full_depth)
    hit = mat > 0
    level = np.zeros(px.size, np.float32)
    if hit.any():
        h = np.nonzero(hit)[0]
        m, f = mat[h], face[h]
        fn = FACE_NORMALS[f]
        nrm = model.nrm[ii[h], jj[h], kk[h]]
        has = np.linalg.norm(nrm, axis=1) > 0
        nrm = np.where(has[:, None], nrm, fn)
        # Smooth normals must still face the side we see, or the shading flips.
        nrm = np.where((nrm * fn).sum(1, keepdims=True) > -0.2, nrm, fn)
        centre = np.stack([ii[h] + model.x0 + 0.5, jj[h] + model.y0 + 0.5,
                           kk[h] + model.z0 + 0.5], 1).astype(np.float32)
        ao = _ambient_occlusion(model, centre, nrm)
        origin = centre + fn * 0.51 + SUN * 0.75
        pad = 2
        occ = _occupancy(model, pad)
        lit = ~_shadowed(occ, origin, model.x0, model.y0, model.z0, pad,
                         model.z0 + model.mat.shape[2])
        diffuse = np.clip(nrm @ SUN, 0, 1) * np.where(lit, 1.0, 0.25)
        light = (AMBIENT + DIFFUSE * diffuse) * ao
        n = RAMP_LEN[m]
        lv = (light - 0.22) / 0.72 * (n - 1) + BIAS[m] + model.tone[ii[h], jj[h], kk[h]]
        lv += TEXTURE[m] * _texture_noise(ii[h], jj[h], kk[h], model.x0, model.y0, model.z0)
        level[h] = lv

    mat2 = mat.reshape(H, W)
    lvl = level.reshape(H, W)
    dep = depth.reshape(H, W)
    solid = mat2 > 0
    # Selective outline: darken the silhouette (more on the shadow side) and front edges.
    pad_s = np.pad(outline_solid.reshape(H, W), 1)
    pad_d = np.pad(np.where(outline_solid, outline_depth, -1e9).reshape(H, W), 1,
                   constant_values=-1e9)
    up, down = ~pad_s[:-2, 1:-1], ~pad_s[2:, 1:-1]
    left, right = ~pad_s[1:-1, :-2], ~pad_s[1:-1, 2:]
    lvl = lvl - solid * (0.9 * (up | left) + 1.6 * (down | right))
    front = np.zeros_like(solid)
    for nb in (pad_d[:-2, 1:-1], pad_d[2:, 1:-1], pad_d[1:-1, :-2], pad_d[1:-1, 2:]):
        front |= (nb > -1e8) & (dep - nb > 3.0)
    lvl = lvl - solid * front * 1.0
    pyy, pxx = np.mgrid[r0:r1, c0:c1]
    idx = np.clip(dither(lvl, pxx, pyy), 0, RAMP_LEN[mat2] - 1).astype(np.int64)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = RAMPS[mat2, idx]
    rgba[..., 3] = np.where(solid, 255, 0)

    glow = None
    if HAS_GLOW[mat2].any() or model.halos:
        glow = np.zeros((H, W, 4), np.uint8)
        g = HAS_GLOW[mat2]
        glow[g, :3] = GLOWS[mat2[g]]
        glow[g, 3] = 255
        for halo in model.halos:
            hx, hy = halo.x - halo.y, (halo.x + halo.y) / 2 - halo.z
            d = np.hypot(pxx + 0.5 - hx, (pyy + 0.5 - hy) * 1.6) / halo.radius
            inten = halo.strength * np.clip(1 - d, 0, 1) ** 1.6 * 3
            q = dither(inten, pxx, pyy)
            q = np.clip(q, 0, 3)
            # Halo strength lives in alpha: additive blending scales the colour by it.
            alpha = (q / 3 * 0.6 * 255).astype(np.uint8)
            add = (alpha > glow[..., 3]) & ~g
            glow[add, :3] = halo.rgb
            glow[add, 3] = alpha[add]
    return rgba, glow, -c0, -r0


def render_shadow(model: Model) -> Sprite:
    """Cast shadow (plus soft contact darkening) on the ground plane z = 0, black with alpha."""
    nx, ny, nz = model.mat.shape
    zmax = model.z0 + nz
    reach = max(zmax, 0) / SHADOW_SUN[2]
    gx0, gx1 = model.x0, model.x0 + nx - SHADOW_SUN[0] * reach
    gy0, gy1 = model.y0 - SHADOW_SUN[1] * reach, model.y0 + ny
    corners_x = [gx0, gx1]
    corners_y = [gy0, gy1]
    sxs = [x - y for x in corners_x for y in corners_y]
    sys_ = [(x + y) / 2 for x in corners_x for y in corners_y]
    c0, c1 = int(np.floor(min(sxs))), int(np.ceil(max(sxs)))
    r0, r1 = int(np.floor(min(sys_))), int(np.ceil(max(sys_)))
    py, px = np.mgrid[r0:r1, c0:c1]
    sx, sy = px + 0.5, py + 0.5
    gx, gy = (sy + sx / 2).ravel(), (sy - sx / 2).ravel()
    pad = 2
    occ = np.pad(model.visible() > 0, pad)
    origin = np.stack([gx, gy, np.full_like(gx, 0.05)], 1).astype(np.float32)
    cast = _shadowed(occ, origin, model.x0, model.y0, model.z0, pad, zmax, SHADOW_SUN)
    # Contact darkening: how much solid sits right next to this ground point.
    k0 = -model.z0
    contact = np.zeros(gx.size, np.float32)
    if 0 <= k0 < nz:
        layer = (model.visible()[:, :, k0:k0 + 3] > 0).any(axis=2)
        lp = np.pad(layer, 3)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                i = np.floor(gx).astype(np.int64) - model.x0 + dx + 3
                j = np.floor(gy).astype(np.int64) - model.y0 + dy + 3
                ok = (i >= 0) & (i < lp.shape[0]) & (j >= 0) & (j < lp.shape[1])
                contact[ok] += lp[i[ok], j[ok]] * (1.0 / (1 + abs(dx) + abs(dy)))
    level = np.maximum(cast * 1.9, np.clip(contact / 3.0, 0, 1) * 3.0)
    q = np.clip(dither(level.reshape(py.shape), px, py), 0, 3).astype(np.int64)
    if model.hover:
        q[:] = 0
    rgba = np.zeros(py.shape + (4,), np.uint8)
    rgba[..., 3] = np.array(SHADOW_ALPHA, np.uint8)[q]
    return Sprite(rgba, -c0, -r0)


def render(model: Model, want_glow: bool) -> Layers:
    base, glow, ox, oy = render_base(model)
    glow_sprite = None
    if want_glow:
        if glow is None:
            glow = np.zeros_like(base)
        glow_sprite = Sprite(glow, ox, oy)
    return Layers(Sprite(base, ox, oy), render_shadow(model), glow_sprite)
