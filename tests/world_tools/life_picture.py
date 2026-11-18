#!/usr/bin/env python3
"""Draws a life dump (`lifeinfo dump`, `laeticias-corner --life-dump`) as a top-down picture.

North up (worldgen's plan orientation: grid +x is south, +y is west), one tile = SCALE pixels:
the districts of the active area tinted and named, unwalkable ground dark, water blue; every live
actor a dot coloured by what it is (people by role, chain workers orange with their goods, event
casts magenta, named figures white, ships and caravans cyan), running events' routes as lines,
chain stocks as small squares. A header gives the clock, the counts and the busiest districts
against the data's population. Needs Pillow (tools/worldgen's virtualenv has it).

Usage: life_picture.py DUMP.json [OUT.png]    (several dumps: one picture each)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE = 6
AREA_TINT = {"centre": (214, 190, 120), "town": (190, 170, 130), "country": (150, 170, 110),
             "road": (170, 160, 140), "sea": (90, 130, 170), "wild": (120, 130, 100)}
SOURCE_COLOUR = {"chain": (255, 140, 30), "cast": (230, 60, 200), "figure": (255, 255, 255),
                 "token": (60, 220, 240)}


def hue(name: str) -> tuple[int, int, int]:
    h = hashlib.md5(name.encode()).digest()
    return (60 + h[0] % 170, 60 + h[1] % 170, 60 + h[2] % 170)


def draw(dump: dict, out: Path) -> None:
    gx0, gy0, gx1, gy1 = dump["ground"]["rect"]
    codes = [int(v) for v in dump["ground"]["tiles"].split()]
    w, h = gx1 - gx0, gy1 - gy0
    names = dump["ground"]["names"]
    area_of = {d["map"]: d["area"] for d in dump["districts"]}

    # Plan orientation: column = (gy1 - 1 - ty), row = tx.
    def px(x: float, y: float) -> tuple[float, float]:
        return ((gy1 - y) * SCALE, (x - gx0) * SCALE)

    header = 64
    img = Image.new("RGB", (h * SCALE, w * SCALE + header), (24, 26, 34))
    dr = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    sums: dict[int, list[float]] = {}
    for i, code in enumerate(codes):
        x, y = gx0 + i % w, gy0 + i // w
        d, walk, water, level = code // 64, bool(code & 32), bool(code & 16), code & 15
        if water:
            col = (54, 92, 140)
        elif d == 255:
            col = (40, 42, 46)
        else:
            base = AREA_TINT.get(area_of.get(d, ""), (140, 140, 130))
            col = tuple(int(c * (0.75 + 0.03 * level)) for c in base)
            if not walk:
                col = tuple(int(c * 0.45) for c in col)
            s = sums.setdefault(d, [0, 0, 0])
            s[0] += x
            s[1] += y
            s[2] += 1
        cx, cy = px(x + 1, y)
        dr.rectangle([cx, cy + header, cx + SCALE - 1, cy + SCALE - 1 + header], fill=col)
    # District borders: a darker pixel where the district changes.
    for i, code in enumerate(codes):
        x, y = gx0 + i % w, gy0 + i // w
        d = code // 64
        if x + 1 < gx1 and codes[i + 1] // 64 != d or y + 1 < gy1 and codes[i + w] // 64 != d:
            cx, cy = px(x + 1, y)
            dr.point((cx, cy + header), fill=(20, 20, 20))
    ax0, ay0, ax1, ay1 = dump["active"]
    a, b = px(ax1, ay0), px(ax0, ay1)
    dr.rectangle([min(a[0], b[0]), min(a[1], b[1]) + header, max(a[0], b[0]), max(a[1], b[1]) + header],
                 outline=(250, 250, 250))
    vx0, vy0, vx1, vy1 = dump["view"]
    a, b = px(vx1, vy0), px(vx0, vy1)
    dr.rectangle([min(a[0], b[0]), min(a[1], b[1]) + header, max(a[0], b[0]), max(a[1], b[1]) + header],
                 outline=(255, 230, 120))
    for e in dump["events"]:
        pts = [px(p[0] + 0.5, p[1] + 0.5) for p in e["route"]]
        pts = [(p[0], p[1] + header) for p in pts]
        if len(pts) > 1:
            dr.line(pts, fill=(255, 120, 220), width=2)
        if e["active"] and e["place"][0] >= 0:
            p = px(*e["place"])
            dr.text((p[0] + 4, p[1] + header - 6), e["id"], font=font, fill=(255, 160, 230))
    for s in dump["stocks"]:
        p = px(s["x"], s["y"])
        dr.rectangle([p[0] - 3, p[1] + header - 3, p[0] + 3, p[1] + header + 3], outline=(255, 200, 60))
        dr.text((p[0] + 4, p[1] + header - 4), str(s["count"]), font=font, fill=(255, 200, 60))
    for act in dump["actors"]:
        if not act["visible"]:
            continue
        p = px(act["x"], act["y"])
        p = (p[0], p[1] + header)
        col = SOURCE_COLOUR.get(act["source"]) or hue(act["role"] or act["kind"])
        r = 2.5 if act["state"] != "travel" else 2
        dr.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col,
                   outline=(0, 0, 0) if act["state"] in ("act", "wander") else None)
        if act["goods"]:
            dr.rectangle([p[0] + 2, p[1] - 5, p[0] + 5, p[1] - 2], fill=(255, 230, 90))
        if act["source"] == "figure":
            dr.text((p[0] + 3, p[1] - 4), act["kind"].split(".")[-1], font=font, fill=(255, 255, 255))
    for d, (sx, sy, n) in sums.items():
        if n < 30:
            continue
        p = px(sx / n + 0.5, sy / n)
        dr.text((p[0] - 15, p[1] + header - 5), names[str(d)].split("/")[-1], font=font,
                fill=(255, 255, 255))
    st = dump["stats"]
    hh = dump["hour"]
    dr.text((6, 4), f"{dump['label']}  day {dump['day']} ({dump['season']}) {int(hh):02d}:{int(round(hh % 1 * 60)) % 60:02d}"
            f"{'  rain' if dump['rain'] else ''}", font=font, fill=(250, 250, 240))
    dr.text((6, 18), f"live {st['live']} (people {st['population']}, figures {st['figures']}, chain workers "
            f"{st['chain_workers']}, casts {st['cast']}, ships/caravans {st['tokens_live']})  events "
            f"{st['running_events']}  scale {st['scale']}", font=font, fill=(220, 220, 210))
    busy = sorted(dump["districts"], key=lambda d: -d["expected"])[:6]
    dr.text((6, 32), "district live/data: " + ", ".join(
        f"{d['district']} {d['live']}/{d['expected']:.0f}" for d in busy), font=font, fill=(220, 220, 210))
    dr.text((6, 46), "dots: people by role (ringed: at work or lingering), orange chain workers, magenta "
            "event casts, white figures; squares: goods", font=font, fill=(170, 170, 160))
    img.save(out)


def main() -> int:
    args = [Path(a) for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2
    if len(args) == 2 and args[1].suffix == ".png":
        draw(json.loads(args[0].read_text()), args[1])
        print(args[1])
        return 0
    for a in args:
        out = a.with_suffix(".png")
        draw(json.loads(a.read_text()), out)
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
