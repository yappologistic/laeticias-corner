"""Flat-shaded stand-in atlas with every final key, size and anchor (replaced by the real art)."""

import numpy as np

import pack
import spec

HEIGHT = {"oak": 40, "pine": 44, "blossom": 38, "bush": 12, "berry_bush": 12, "tall_grass": 10,
          "rock": 8, "stump": 6, "reeds": 14, "lily_pads": 1, "hedge": 14, "fence": 10,
          "planter": 6, "beehive": 14, "scarecrow": 26, "well": 22, "lamp": 32, "bench": 8,
          "picnic_table": 8, "campfire": 8, "bridge": 6, "cottage": 40, "toolshed": 22,
          "coop": 18, "greenhouse": 30, "barn": 44, "windmill": 64}


def prism(fw: int, fh: int, height: int, color, alpha: int = 255) -> pack.Sprite:
    """Box over a fw x fh tile footprint, `height` px tall, anchored at the origin tile's top vertex."""
    W, H = 16 * (fw + fh), 8 * (fw + fh) + height
    ox, oy = 16 * fh, height
    px, py = np.meshgrid(np.arange(W), np.arange(H))
    sx, sy = px - ox + 0.5, py - oy + 0.5
    out = np.zeros((H, W, 4), np.uint8)
    for z in range(height + 1):
        xw, yw = sy + z + sx / 2, sy + z - sx / 2
        inside = (xw >= 0) & (yw >= 0) & (xw < 16 * fw) & (yw < 16 * fh)
        shade = 1.0 if z == height else (0.8 if sx[0, 0] < 0 else 0.6)
        tone = np.where(sx < (fw - fh) * 8, 0.8, 0.6) if z < height else 1.0
        rgb = (np.array(color)[None, None, :] * np.asarray(tone)[..., None] * shade / shade)
        out[inside, :3] = np.broadcast_to(rgb, out.shape[:2] + (3,))[inside]
        out[inside, 3] = alpha
    return pack.Sprite(out, ox, oy)


def build() -> dict[str, pack.Sprite]:
    cat = spec.load_catalog()
    sprites = {}
    colors = {"grass": (90, 150, 70), "meadow": (140, 180, 80), "path": (180, 150, 100),
              "cobble": (150, 150, 160), "water": (70, 120, 180)}
    for k in spec.terrain_keys(cat):
        sprites[k] = prism(1, 1, 0, colors[k.split("/")[1]])
    for s in spec.item_specs(cat):
        for v in s.variants:
            k = int(v[1:]) if v.startswith("r") else 0
            fw, fh = s.footprint if (s.layout != "rotate" or k % 2 == 0) else s.footprint[::-1]
            for f in range(s.frames):
                h = HEIGHT.get(s.id, 6)
                sprites[f"item/{s.id}/base/{v}/f{f}"] = prism(fw, fh, h, (200, 120, 90))
                if "shadow" in s.layers:
                    sh = prism(fw, fh, 0, (0, 0, 0), 90)
                    sprites[f"item/{s.id}/shadow/{v}/f{f}"] = pack.Sprite(sh.rgba, sh.ox - 4, sh.oy)
                if "glow" in s.layers:
                    sprites[f"item/{s.id}/glow/{v}/f{f}"] = prism(1, 1, 2, (255, 200, 100))
    for v in cat["visitors"]:
        for a, n in spec.CRITTER_ANIMS.items():
            for f in range(n):
                s = prism(1, 1, 6, (240, 230, 200))
                small = pack.Sprite(s.rgba[::2, ::2].copy(), s.ox // 2, s.rgba.shape[0] // 2)
                sprites[f"critter/{v['id']}/{a}/f{f}"] = small
    for name, n in spec.FX_FRAMES.items():
        for f in range(n):
            sprites[f"fx/{name}/f{f}"] = pack.Sprite(np.full((4, 4, 4), 220, np.uint8), 2, 4)
    sprites["edge/cliff_se"] = prism(1, 1, 24, (120, 80, 60))
    sprites["edge/cliff_sw"] = prism(1, 1, 24, (140, 95, 70))
    sprites["ui/tile_ok"] = prism(1, 1, 0, (160, 240, 160), 120)
    sprites["ui/tile_bad"] = prism(1, 1, 0, (240, 120, 120), 120)
    return sprites


if __name__ == "__main__":
    w, h = pack.write_atlas(build(), spec.ATLAS_PNG, spec.ATLAS_JSON)
    print(f"placeholder atlas {w}x{h}")
