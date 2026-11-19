"""Measuring lit nights (graphics plan W1): from the light points of the committed region files,
an estimate of what share of each 1x view would be warm-lit at dusk, at night and in the small
hours, how dark the dark between the pools is, and a night preview of the view.

The model: a view is the 2560 x 1440 screen at the view's zoom, in the game's 2:1 projection;
the moonlit ground is the terrain's colour at 16 % plus a cool sky (median luma about 32, the
owner's 28-38); each light adds its colour by `strength * (1 - (d / radius)^2)^2` (the usual windowed
falloff of a point light) with a lit core
of a quarter tile (the glow sprite itself). A pixel is warm-lit by the quality bar's rule
(r > b + 30 and luma >= 90). The engine's falloff will differ in detail; the point is where light
is and is not, and how much of it.

  build.sh --nights [REGION ...] [--preview]     table to out/worldgen/night/nights.md
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from plan import world_plan as P

from . import lights as LT
from . import rng
from .compose import NONE16, World, live_items
from .coords import COLS
from .preview import font, terrain_colours

SCREEN = (2560, 1440)
PX = 4                     # preview: one preview pixel per 4 screen pixels at 1x
CITIES = ("athens", "rome", "parsa")
HOURS = {"dusk": 19.5, "night": 22.0, "small hours": 2.0}
# Golden scenes and the views the brief names: (region, district, zoom, preview name).
NAMED = [("athens", "agora", 2, "agora_g7"), ("athens", "agora", 1, "agora"),
         ("athens", "acropolis", 1, "acropolis"), ("athens", "piraeus", 1, "piraeus"),
         ("rome", "forum", 1, "forum"), ("rome", "subura", 1, "subura"),
         ("parsa", "terrace", 1, "parsa_terrace"), ("parsa", "town", 1, "parsa_town"),
         ("ostia", "portus", 1, "portus")]
# The cities' busiest views by day (QA6 V6-019 measured them at 22:00 on the engine's look path):
# the Appia's tombs outside the Porta Capena, the Acropolis, the wall over Skambonidai and the
# king's paradise at Pārsa. After dark they were as dark as the country (a sanctuary's lamp, the
# gate's watch), so they are held to the village bar, never lit like streets.
BUSIEST = [("rome", "rome_busiest", (243, 161)), ("athens", "athens_centre", (660, 300)),
           ("athens", "athens_busiest", (704, 231)), ("parsa", "parsa_busiest", (1172, 326))]
TARGET = (2.0, 8.0)        # % of a city view warm-lit at dusk and at night (quality bar §4.3)
VILLAGE = (1.0, 4.0)       # ... of a village view: fewer than VILLAGE_BUILT buildings in it
VILLAGE_BUILT = 40
HAMLET_BUILT = 12          # a stop of a few houses round an inn or a shrine: a light all night
# Quarters nobody lives in after dark (a quarry worked by day, the Academy's grove outside the
# walls): dark by design.
NIGHT_EMPTY = {("parsa", "quarry"), ("academy", "grove")}


def _items(world: World):
    return {(*LT.grid_origin(it), it.id): it for _, it in live_items(world)}


def light_list(doc: dict, items: dict, h: float, festival: str | None = None,
               chance: dict | None = None):
    """[(c, r, radius, strength, colour rgb)] burning at hour h (plan coordinates, floats)."""
    profs = doc.get("lights", {}).get("profiles", {})
    out = []
    for pt in doc.get("light_points", []):
        p = profs[pt[3]]
        only = p.get("only")
        if only is not None:
            if only.startswith("event:"):
                if (chance or {}).get(only[6:], 0.0) < 0.5 and festival is None:
                    continue
            elif only != festival:
                continue
        if not LT.lit_at(p, h):
            continue
        it = items.get((pt[0], pt[1], pt[2]))
        if it is None:
            continue
        c, r = it.c + it.pw / 2, it.r + it.ph / 2
        if len(pt) == 5:   # emitters sit apart along the item's long side
            k = (rng.hash64(pt[4]) % 1000) / 1000 - 0.5
            if it.pw >= it.ph:
                c += k * it.pw * 0.8
            else:
                r += k * it.ph * 0.8
        s = p["strength"] * (p.get("festivals", {}).get(festival, p.get("festivals", {}).get("*", 1.0))
                             if festival else 1.0)
        col = tuple(int(p["colour"][i:i + 2], 16) for i in (1, 3, 5))
        out.append((c, r, p["radius"], min(s, 1.0), col, p["kind"]))
    return out


def _event_chances(doc: dict) -> dict:
    return {e["id"]: float(e.get("trigger", {}).get("chance", 0.0)) for e in doc.get("events", [])
            if e.get("trigger", {}).get("on") == "window"}


class Canvas:
    """One view: screen pixels mapped to fractional plan tiles, the night ground under them."""

    def __init__(self, world: World, cat, atlas, centre: tuple[float, float], zoom: int):
        w, h = SCREEN[0] // PX, SCREEN[1] // PX
        hw, hh = 32 / PX * zoom, 16 / PX * zoom          # half tile on the preview at this zoom
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
        X = (xs - w / 2) / hw                            # tx - ty, in tiles
        Y = (ys - h / 2) / hh                            # tx + ty, in tiles
        c0, r0 = centre
        tx0, ty0 = r0, COLS - 1 - c0
        tx = tx0 + (X + Y) / 2
        ty = ty0 + (Y - X) / 2
        self.R = tx                                      # plan row = grid tx
        self.C = COLS - 1 - ty                           # plan column
        ri = np.clip(np.floor(self.R).astype(int), 0, world.T.shape[0] - 1)
        ci = np.clip(np.floor(self.C).astype(int), 0, world.T.shape[1] - 1)
        t = world.T[ri, ci].astype(np.int64)
        cols = terrain_colours(world, cat, atlas)
        t = np.where(t == NONE16, len(cols) - 1, t)
        base = cols[t]
        occ = world.occ[ri, ci] >= 0
        lvl = (world.L[ri, ci] & 0x0F).astype(np.float64)
        shade = 0.16 + 0.004 * lvl
        sky = np.array([6.0, 10.0, 28.0])
        night = base * shade[..., None] + sky
        night[occ] = night[occ] * 0.85 + np.array([10.0, 9.0, 8.0])
        # footprint edges read as walls in the moonlight
        edge = occ & ~np.roll(occ, 1, axis=0)
        night[edge] += 10
        self.night = night
        self.inside = (world.T[ri, ci] != NONE16)
        idx = np.unique(world.occ[ri, ci][occ])
        defs = [cat.items.get(world.items[i].id) for i in idx.tolist()]
        self.built = sum(1 for d in defs if d is not None and d.has_door)
        self.monuments = sum(1 for d in defs if d is not None and d.landmark)
        self.size = (w, h)
        self.k = (hw, hh, tx0, ty0)

    def box(self, c: float, r: float, rad: float):
        """The preview rows and columns a light of this radius can reach (or None)."""
        hw, hh, tx0, ty0 = self.k
        w, h = self.size
        X = (r - tx0) - (COLS - 1 - c - ty0)
        Y = (r - tx0) + (COLS - 1 - c - ty0)
        px, py = w / 2 + X * hw, h / 2 + Y * hh
        ex, ey = (rad + 1) * 2 * hw, (rad + 1) * 2 * hh
        x0, x1 = max(int(px - ex), 0), min(int(px + ex) + 1, w)
        y0, y1 = max(int(py - ey), 0), min(int(py + ey) + 1, h)
        return None if x0 >= x1 or y0 >= y1 else (slice(y0, y1), slice(x0, x1))

    def light(self, lights) -> np.ndarray:
        add = np.zeros_like(self.night)
        for c, r, rad, s, col, _ in lights:
            box = self.box(c, r, rad)
            if box is None:
                continue
            d = np.hypot(self.C[box] - c, self.R[box] - r)
            i = s * np.clip(1 - (d / rad) ** 2, 0, 1) ** 2
            i = np.where(d <= 0.25, np.maximum(i, 0.9), i)   # the source's own glow
            add[box] += i[..., None] * np.array(col, dtype=np.float64) * 0.75
        return np.clip(self.night + add, 0, 255)


def metrics(img: np.ndarray, inside: np.ndarray) -> dict:
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    lit = (r > b + 30) & (luma >= 90) & inside
    n = max(int(inside.sum()), 1)
    unlit = luma[inside & ~lit]
    spill = (r > b + 12) & inside
    return {"lit": 100.0 * lit.sum() / n, "spill": 100.0 * spill.sum() / n,
            "median": float(np.median(unlit)) if unlit.size else 0.0,
            "iqr": float(np.subtract(*np.percentile(unlit, [75, 25]))) if unlit.size else 0.0,
            "p98_lights": float(np.percentile(luma[lit], 98)) if lit.any() else 0.0}


def district_centres(world: World, rid: str) -> dict[str, tuple[float, float]]:
    out = {}
    for i, name in enumerate(world.districts):
        reg, _, d = name.partition("/")
        if reg != rid:
            continue
        rr, cc = np.nonzero(world.D == i)
        if rr.size:
            out[d] = (float(np.median(cc)), float(np.median(rr)))
    return out


def views(doc: dict, world: World) -> list[tuple[str, str, int, tuple[float, float], bool]]:
    """(view name, district, zoom, centre, inhabited) for a region: every populated quarter at
    1x, and the named views."""
    rid = doc["id"]
    centres = district_centres(world, rid)
    out = []
    for d in doc.get("districts", []):
        if d["id"] in centres and LT.inhabited(doc, d) and \
                all(max(abs(centres[d["id"]][0] - v[3][0]), abs(centres[d["id"]][1] - v[3][1])) > 16
                    for v in out):
            out.append((d["id"], d["id"], 1, centres[d["id"]], True))
    for reg, dist, zoom, name in NAMED:
        if reg == rid and dist in centres and not any(v[0] == name for v in out):
            out.append((name, dist, zoom, centres[dist], True))
    # A town is seen first where the map's journey opens: its marker.
    points = [(n, at) for reg, n, at in BUSIEST if reg == rid]
    if P.REGIONS[rid][0] == "town":
        points += [("arrival", at) for reg, at, _i in P.MARKERS if reg == rid]
    for name, (c, r) in points:
        d = world.D[r, c]
        dist = world.districts[d].split("/", 1)[-1] if d != NONE16 else None
        out.append((name, dist, 1, (c + 0.5, r + 0.5), True))
    return out


def measure(doc: dict, world: World, cat, atlas, items=None):
    items = items or _items(world)
    chance = _event_chances(doc)
    fests = [f["id"] for f in doc.get("festivals", [])]
    rows = []
    for name, dist, zoom, centre, inhabited in views(doc, world):
        cv = Canvas(world, cat, atlas, centre, zoom)
        area = next((d.get("area") for d in doc.get("districts", []) if d["id"] == dist), None)
        row = {"view": name, "zoom": zoom,
               "hamlet": P.REGIONS[doc["id"]][0] == "town" and cv.built < HAMLET_BUILT,
               "village": P.REGIONS[doc["id"]][0] == "town" or (
                   area != "centre" and cv.built < VILLAGE_BUILT / zoom ** 2 and cv.monuments < 3),
               "empty": (doc["id"], dist) in NIGHT_EMPTY,
               "busy": any(n == name for _r, n, _a in BUSIEST), "arrival": name == "arrival"}
        for label, h in HOURS.items():
            ls = light_list(doc, items, h, chance=chance)
            m = metrics(cv.light(ls), cv.inside)
            row[label] = m | {"n": sum(1 for x in ls if _in_view(cv, x))}
        best = None
        only = {p.get("only") for p in doc.get("lights", {}).get("profiles", {}).values()}
        for f in [x for x in fests if x in only] or fests[:1]:
            ls = light_list(doc, items, HOURS["night"], festival=f, chance=chance)
            m = metrics(cv.light(ls), cv.inside)
            if best is None or m["lit"] > best[1]["lit"]:
                best = (f, m)
        if best:
            row["festival"] = {"id": best[0]} | best[1]
        rows.append(row)
    return rows


def _in_view(cv: Canvas, light) -> bool:
    return cv.box(light[0], light[1], -0.9) is not None


def verdict(row: dict) -> str:
    if row.get("empty"):
        return "dark by design (worked by day only)"
    bad = []
    lo, hi = VILLAGE if row.get("busy") or row.get("arrival") else \
        (0.0, VILLAGE[1]) if row.get("hamlet") else VILLAGE if row.get("village") else TARGET
    for label in ("dusk", "night"):
        v = round(row[label]["lit"], 1)
        if v < lo:
            bad.append(f"{label} dark")
        elif v > hi:
            bad.append(f"{label} floodlit")
    if row["small hours"]["n"] == 0:
        bad.append("no light in the small hours")
    return "ok" if not bad else ", ".join(bad)


def preview(doc: dict, world: World, cat, atlas, name: str, out: Path, items=None) -> Path:
    items = items or _items(world)
    for reg, dist, zoom, pname in NAMED:
        if pname == name:
            break
    centre = district_centres(world, doc["id"])[dist]
    cv = Canvas(world, cat, atlas, centre, zoom)
    chance = _event_chances(doc)
    panels = []
    for label in ("dusk", "night"):
        img = cv.light(light_list(doc, items, HOURS[label], chance=chance))
        m = metrics(img, cv.inside)
        im = Image.fromarray(img.astype(np.uint8))
        d = ImageDraw.Draw(im)
        d.text((8, 6), f"{name} {zoom}x  {label} {HOURS[label]:05.2f}h  warm-lit {m['lit']:.1f} %  "
               f"unlit median {m['median']:.0f}", font=font(Path(__file__).resolve().parents[3], 13),
               fill=(230, 230, 220))
        panels.append(im)
    w, h = panels[0].size
    sheet = Image.new("RGB", (w, h * 2 + 4), (0, 0, 0))
    sheet.paste(panels[0], (0, 0))
    sheet.paste(panels[1], (0, h + 4))
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{name}.png"
    sheet.save(f)
    return f


def table(rows_by_region: dict) -> str:
    lines = ["| Region | View | Zoom | Dusk lit % | Dusk median | Night lit % | Night median | "
             "Night IQR | p98 at lights | Lights in view (dusk/night/small hours) | "
             "Small hours lit % | Festival night lit % | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for rid, rows in rows_by_region.items():
        for row in rows:
            dk, nt, sh = row["dusk"], row["night"], row["small hours"]
            fe = row.get("festival")
            lines.append(
                f"| {rid} | {row['view']}{' (hamlet)' if row.get('hamlet') else ' (village)' if row.get('village') else ''} | {row['zoom']}x | {dk['lit']:.1f} | {dk['median']:.0f} | "
                f"{nt['lit']:.1f} | {nt['median']:.0f} | {nt['iqr']:.0f} | {nt['p98_lights']:.0f} | "
                f"{dk['n']}/{nt['n']}/{sh['n']} | {sh['lit']:.1f} | "
                f"{(fe['id'] + ' ' + format(fe['lit'], '.1f')) if fe else '-'} | {verdict(row)} |")
    return "\n".join(lines) + "\n"


def run(b, rids: list[str], want_preview: bool) -> bool:
    world = b.composed()
    items = _items(world)
    out = b.reports / "night"
    rows = {}
    for rid in rids:
        f = b.root / "assets/regions" / f"{rid}.json"
        doc = LT.apply(json.loads(f.read_text()), world, b.cat)
        rows[rid] = measure(doc, world, b.cat, b.atlas, items)
        if want_preview:
            for reg, _, _, name in NAMED:
                if reg == rid:
                    print(f"   preview {preview(doc, world, b.cat, b.atlas, name, out, items)}")
    text = table(rows)
    out.mkdir(parents=True, exist_ok=True)
    (out / "nights.md").write_text(text)
    print(text)
    return all(verdict(r) == "ok" or r.get("empty") for rs in rows.values() for r in rs)
