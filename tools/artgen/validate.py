"""Check the committed atlas against the catalog: keys, rects, anchors, frame counts."""

import json
import re
import sys
from collections import defaultdict

import numpy as np
from PIL import Image

import spec
from palette import PALETTE


def validate() -> list[str]:
    cat = spec.load_catalog()
    doc = json.loads(spec.ATLAS_JSON.read_text())
    errors = []
    if set(doc) != {"version", "image", "sprites"} or doc["version"] != 1:
        errors.append("manifest must be exactly {version: 1, image, sprites}")
    img = Image.open(spec.ATLAS_PNG)
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
    for k, r in sprites.items():
        x, y, w, h, ox, oy = (r[f] for f in ("x", "y", "w", "h", "ox", "oy"))
        if w < 1 or h < 1 or x < 0 or y < 0 or x + w > W or y + h > H:
            errors.append(f"{k}: rect {x},{y} {w}x{h} outside {W}x{H}")
            continue
        # Anchors may legitimately sit outside a trimmed rect (a shadow cast away from the
        # footprint), but never absurdly far from it.
        if not (-160 <= ox <= w + 160 and -160 <= oy <= h + 160):
            errors.append(f"{k}: anchor ({ox},{oy}) far outside {w}x{h}")
        if k.startswith(("item/", "terrain/", "critter/", "edge/")) and w * h > 1:
            if alpha.crop((x, y, x + w, y + h)).getbbox() is None:
                errors.append(f"{k}: sprite is fully transparent")

    # Every coloured pixel comes from the palette; shadows are pure black with alpha.
    rgba = np.asarray(img)
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


def main() -> int:
    errors = validate()
    for e in errors:
        print("atlas:", e, file=sys.stderr)
    n = len(json.loads(spec.ATLAS_JSON.read_text())["sprites"])
    print(f"validate: {n} sprites, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
