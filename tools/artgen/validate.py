"""Check an atlas against the catalog and the tile size: keys, rects, anchors, ground diamonds,
frame counts and palette use."""

import json
import re
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

import spec
from palette import PALETTE


def diamond(tile_w: int) -> np.ndarray:
    """The contract's ground diamond as a (tile_w/2, tile_w - 2) mask with the top vertex at
    column tile_w/2 - 1: rows 2, 6, ... tile_w - 2, tile_w - 2, ... 2 px wide."""
    h, w = tile_w // 2, tile_w - 2
    y = np.arange(h)[:, None]
    half = np.minimum(y, h - 1 - y) * 2 + 1
    return np.abs(np.arange(w)[None, :] + 0.5 - w / 2) < half


def validate(build: spec.Build) -> list[str]:
    cat = spec.load_catalog()
    doc = json.loads(build.atlas_json.read_text())
    errors = []
    if set(doc) != {"version", "image", "sprites"} or doc["version"] != 1:
        errors.append("manifest must be exactly {version: 1, image, sprites}")
    img = Image.open(build.atlas_png)
    if img.mode != "RGBA":
        errors.append(f"atlas mode is {img.mode}, expected RGBA")
    W, H = img.size
    if max(W, H) > 4096:
        errors.append(f"atlas {W}x{H} exceeds 4096")
    sprites = doc["sprites"]
    required = spec.required_keys(cat)
    missing = [k for k in required if k not in sprites]
    extra = sorted(set(sprites) - set(required))
    errors += [f"missing sprite {k}" for k in missing]
    errors += [f"unexpected sprite {k}" for k in extra]

    alpha = img.getchannel("A")
    reach = 160 * build.k
    for k, r in sprites.items():
        x, y, w, h, ox, oy = (r[f] for f in ("x", "y", "w", "h", "ox", "oy"))
        if w < 1 or h < 1 or x < 0 or y < 0 or x + w > W or y + h > H:
            errors.append(f"{k}: rect {x},{y} {w}x{h} outside {W}x{H}")
            continue
        # Anchors may legitimately sit outside a trimmed rect (a shadow cast away from the
        # footprint), but never absurdly far from it.
        if not (-reach <= ox <= w + reach and -reach <= oy <= h + reach):
            errors.append(f"{k}: anchor ({ox},{oy}) far outside {w}x{h}")
        if k.startswith(("item/", "terrain/", "critter/", "edge/")) and w * h > 1:
            if alpha.crop((x, y, x + w, y + h)).getbbox() is None:
                errors.append(f"{k}: sprite is fully transparent")

    # Whole-tile ground sprites cover exactly the contract diamond, anchored at its top vertex.
    rgba = np.asarray(img)
    want = diamond(build.tile_w)
    full = [k for k in sprites if re.fullmatch(r"terrain/[^/]+/(v\d+|m15/f\d+)|ui/tile_\w+", k)]
    for k in full:
        r = sprites[k]
        if (r["w"], r["h"], r["ox"], r["oy"]) != (want.shape[1], want.shape[0], build.tile_w // 2 - 1, 0):
            errors.append(f"{k}: {r['w']}x{r['h']} anchored ({r['ox']},{r['oy']}) is not the "
                          f"{build.tile_w}x{build.tile_h} tile diamond")
        elif not np.array_equal(rgba[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"], 3] > 0, want):
            errors.append(f"{k}: coverage differs from the tile diamond")

    # Every coloured pixel comes from the palette; shadows are pure black with alpha.
    allowed = {int(c[1:], 16) for c in PALETTE}
    for k, r in sprites.items():
        px = rgba[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]].reshape(-1, 4)
        px = px[px[:, 3] > 0].astype(np.int64)
        codes = set(np.unique((px[:, 0] << 16) | (px[:, 1] << 8) | px[:, 2]).tolist())
        bad = codes - ({0} if "/shadow/" in k else allowed)
        if bad:
            errors.append(f"{k}: {len(bad)} colours outside the palette")

    # Every layer of an item variant has the same number of frames.
    frames = defaultdict(set)
    for k in sprites:
        m = re.fullmatch(r"item/([^/]+)/([^/]+)/([^/]+)/f(\d+)", k)
        if m:
            frames[(m[1], m[2], m[3])].add(int(m[4]))
    per_item = defaultdict(set)
    for (item, _layer, _var), fs in frames.items():
        if fs != set(range(len(fs))):
            errors.append(f"{item}: frames not contiguous from f0")
        per_item[item].add(len(fs))
    errors += [f"{item}: layers/variants disagree on frame count {sorted(n)}"
               for item, n in per_item.items() if len(n) > 1]
    return errors


def main(build: spec.Build) -> int:
    errors = validate(build)
    for e in errors:
        print("atlas:", e, file=sys.stderr)
    n = len(json.loads(build.atlas_json.read_text())["sprites"])
    print(f"validate: {n} sprites, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(spec.parse_build(sys.argv[1:])[0]))
