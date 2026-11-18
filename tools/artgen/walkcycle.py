"""Walk-cycle films and strips from the built pages (graphics-rnd.md §2.9): walkers crossing a
tiled ground with their frames chosen by distance walked over the declared stride, as the
engine plays them, so sliding feet, pops and uneven spacing show.

    tools/artgen/.venv/bin/python tools/artgen/walkcycle.py OUT_DIR SET KIND[:VARIANT[:ANIM]] ...

SET is a set id (`rome`, `athens`, `parsa`, `world`) or `home`. Writes OUT_DIR/strip.png (each
cycle's frames, both facings, 3x) and OUT_DIR/frames_1x/NNNNN.png, OUT_DIR/frames_2x/NNNNN.png
(eight seconds at 60 fps, nearest-neighbour; one panel per walker and facing, the camera
following it over the ground), for ffmpeg.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import spec

FPS = 60
SECONDS = 8
SPEED = 0.9                  # tiles per second (src/core/tuning.hpp kWalkSpeed)
GROUND = ((92, 128, 76), (80, 114, 66))
PANEL = 112                  # px at 1x: one walker per panel


class Pages:
    """Sprites of one set (or the home atlas) read from its built pages."""

    def __init__(self, set_id: str):
        root = spec.ASSETS
        files = [root / "atlas.json"] if set_id == "home" else \
            sorted(p for p in (root / "atlas").glob(f"{set_id}.[0-9]*.json") if len(p.name.split(".")) == 3)
        self.sprites, self.images, self.strides = {}, {}, {}
        for f in files:
            doc = json.loads(f.read_text())
            img = np.asarray(Image.open(f.with_name(doc["image"])).convert("RGBA"))
            for key, s in doc["sprites"].items():
                self.sprites[key] = (img, s)
            self.strides.update(doc.get("strides", {}))
        if set_id != "home":
            cat = json.loads((root / "sets" / set_id / "catalog.json").read_text())
            for a in cat.get("actors", []):
                for anim, e in a["anims"].items():
                    if "stride" in e:
                        self.strides[f"{a['sprite']}/{anim}"] = e["stride"]

    def frames(self, prefix: str) -> list:
        out, n = [], 0
        while f"{prefix}/f{n}" in self.sprites:
            img, s = self.sprites[f"{prefix}/f{n}"]
            out.append((img[s["y"]:s["y"] + s["h"], s["x"]:s["x"] + s["w"]], s["ox"], s["oy"]))
            n += 1
        return out


def ground(scale: int, w: int, h: int) -> np.ndarray:
    """Isometric tiles in two greens (64 x 32 at 1x), so motion against the ground shows."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / 64 + yy / 32, yy / 32 - xx / 64
    g = ((np.floor(u) + np.floor(v)) % 2).astype(np.int64)
    img = np.asarray(GROUND, np.uint8)[g]
    return img.repeat(scale, 0).repeat(scale, 1)


def paste(canvas, spr, x, y, scale):
    rgba, ox, oy = spr
    if scale > 1:
        rgba = rgba.repeat(scale, 0).repeat(scale, 1)
    h, w = rgba.shape[:2]
    x0, y0 = int(round(x)) - ox * scale, int(round(y)) - oy * scale
    Hc, Wc = canvas.shape[:2]
    xs0, ys0, xs1, ys1 = max(0, x0), max(0, y0), min(Wc, x0 + w), min(Hc, y0 + h)
    if xs0 >= xs1 or ys0 >= ys1:
        return
    src = rgba[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0].astype(np.float32)
    a = src[..., 3:4] / 255
    dst = canvas[ys0:ys1, xs0:xs1].astype(np.float32)
    canvas[ys0:ys1, xs0:xs1] = (dst * (1 - a) + src[..., :3] * a).astype(np.uint8)


def walkers(pages: Pages, specs: list[str], set_id: str):
    """(prefix without facing, stride) per requested kind."""
    out = []
    for item in specs:
        kind, variant, anim = (item.split(":") + [None, None])[:3]
        anim = anim or "move"
        if set_id == "home":
            base = f"critter/{kind}"
        else:
            hit = [k for k in pages.sprites if k.split("/")[1] == kind and f"/{anim}_front/" in k]
            base = hit[0].split(f"/{anim}_front/")[0] if hit else f"walker/{kind}"
            if "/v" in base:
                base = base.rsplit("/v", 1)[0] + f"/v{variant or 0}"
        stride_key = base.split("/v")[0] if set_id != "home" else base
        out.append((f"{base}/{anim}", pages.strides.get(f"{stride_key}/{anim}")))
    return out


def main(out: str, set_id: str, *kinds: str) -> int:
    out_dir = Path(out)
    pages = Pages(set_id)
    chosen = walkers(pages, list(kinds), set_id)
    # The strip: every frame of both facings, 3x.
    rows = []
    for prefix, _s in chosen:
        for facing in ("front", "back"):
            fr = pages.frames(f"{prefix}_{facing}")
            cell = max([max(f[0].shape[1], 2 * max(f[1], f[0].shape[1] - f[1])) for f in fr] + [8]) + 4
            hgt = max([f[0].shape[0] for f in fr] + [8]) + 6
            row = np.zeros((hgt, cell * max(len(fr), 1), 3), np.uint8)
            row[...] = GROUND[0]
            for i, f in enumerate(fr):
                paste(row, f, i * cell + cell // 2, hgt - 3 - (f[0].shape[0] - f[2]), 1)
            rows.append(row)
    sw = max(r.shape[1] for r in rows)
    sheet = np.concatenate([np.pad(r, ((0, 0), (0, sw - r.shape[1]), (0, 0))) for r in rows])
    Image.fromarray(sheet).resize((sw * 3, sheet.shape[0] * 3), Image.NEAREST).save(out_dir / "strip.png")
    # The films: one panel per walker and facing, the camera following the walker, so the
    # ground scrolls under it at walking speed and a planted foot must move with the ground.
    lanes = [(p, s_, fc) for p, s_ in chosen for fc in ("front", "back")]
    cycles = {(p, fc): pages.frames(f"{p}_{fc}") for p, _s, fc in lanes}
    cols = min(4, len(lanes))
    rows_n = -(-len(lanes) // cols)
    for scale in (1, 2):
        frames_dir = out_dir / f"frames_{scale}x"
        frames_dir.mkdir(parents=True, exist_ok=True)
        big = ground(scale, PANEL + 128, PANEL + 64)
        for fi in range(FPS * SECONDS):
            t = fi / FPS
            film = np.zeros((rows_n * PANEL * scale, cols * PANEL * scale, 3), np.uint8)
            for li, (prefix, stride, facing) in enumerate(lanes):
                cyc = cycles[(prefix, facing)]
                dist = SPEED * t
                dy = 16 if facing == "front" else -16
                ox, oy = int(round(dist * 32 * scale)) % (64 * scale), int(round(dist * dy * scale)) % (32 * scale)
                panel = big[oy:oy + PANEL * scale, ox:ox + PANEL * scale].copy()
                if cyc:
                    phase = dist / stride if stride else t * 1.2
                    paste(panel, cyc[int(phase * len(cyc)) % len(cyc)], PANEL * scale // 2, PANEL * scale * 3 // 4, scale)
                r, c = divmod(li, cols)
                film[r * PANEL * scale:(r + 1) * PANEL * scale, c * PANEL * scale:(c + 1) * PANEL * scale] = panel
            Image.fromarray(film).save(frames_dir / f"{fi:05d}.png")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main(*sys.argv[1:]))
