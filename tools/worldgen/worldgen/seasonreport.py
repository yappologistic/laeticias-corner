"""A year in the life (docs/design/seasons.md): month by month, what each region's data makes of
it, so the seasons can be read and seen before the engine draws them.

`build.sh --city <region>… --year [--preview]` writes `out/worldgen/seasons/<region>_year.md`
for those cities, and `build.sh --year-all` the same for every region file; with `--preview` the
season maps: `<region>_seasons.png`, the same hour in each season (districts shaded by movers per
screenful over the ground as that month shows it, snow above the line, flooded fields), for the
city centres, and `<region>_land.png`, the ground in each season for a stretch of countryside.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from plan import world_plan as P

from . import citylife as CL
from . import climates as C
from . import seasons as S
from .preview import font

# Ground colours by class and state (the overview's palette, seasons.md §4.5).
STATE_RGB = {"fresh": (126, 170, 82), "green": (98, 146, 70), "dry": (196, 172, 104),
             "dormant": (140, 132, 98), "bloom": (176, 168, 120), "turn": (178, 128, 60),
             "bare": (128, 110, 92), "fruit": (110, 120, 70), "ploughed": (128, 96, 68),
             "sprout": (140, 160, 96), "ripe": (214, 186, 92), "stubble": (190, 170, 120),
             "spring": (126, 170, 82), "summer": (98, 146, 70), "autumn": (178, 128, 60),
             "winter": (200, 204, 210), "gone": (150, 140, 110)}
FIXED_RGB = {"sea": (40, 78, 118), "water": (64, 110, 150), "rock": (130, 124, 116),
             "sand": (214, 196, 150), "snow": (236, 240, 246), "paved": (170, 160, 146),
             "earth": (150, 124, 92), "none": (16, 18, 24)}
CLASS_OF = {"grass": "grass", "crop": "crop", "forest": "deciduous", "evergreen": "evergreen",
            "scrub": "grass", "steppe": "grass", "marsh": "reed"}


def ground_image(world, root: Path, rect, month: int, px: int = 2) -> Image.Image:
    """The ground of a plan rect as month `month` shows it: each tile's class in its climate's
    state, snow above the month's line, flood water on ranked ground in flood months."""
    from .catalog import Catalog
    c0, r0, c1, r1 = rect
    cat = Catalog(root)
    gc = S.ground_classes(world, cat)               # grid image [y, x]
    plan = np.ascontiguousarray(gc.T[:, ::-1])      # back to plan [r, c]
    sub = plan[r0:r1 + 1, c0:c1 + 1]
    reg, names = S.region_grid(world)
    rsub = reg[r0:r1 + 1, c0:c1 + 1]
    lv = (world.L & 0x0F)[r0:r1 + 1, c0:c1 + 1]
    clims = S.resolved(root)
    over = {}
    for f in (root / "assets/regions").glob("*.json"):
        sn = json.loads(f.read_text()).get("theme", {}).get("snow")
        if sn:
            over[f.stem] = sn
    D = world.D[r0:r1 + 1, c0:c1 + 1]
    h, w = sub.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for ri in np.unique(rsub).tolist():
        if ri < 0:
            continue
        cid = C.REGION_CLIMATE.get(names[ri], "med_green")
        clim = clims[cid]
        rid = names[ri]
        line = (over.get(rid) or clim.get("snow", {})).get("line", [None] * 12)[month]
        m = rsub == ri
        snow_on = m
        if over.get(rid, {}).get("districts"):
            ids = [world.districts.index(f"{rid}/{d}") for d in over[rid]["districts"]
                   if f"{rid}/{d}" in world.districts]
            snow_on = m & np.isin(D, ids)
        for k, gname in enumerate(S.GROUND_CLASSES):
            mm = m & (sub == k)
            if not mm.any():
                continue
            if gname in FIXED_RGB:
                col = FIXED_RGB[gname]
            else:
                cls = CLASS_OF.get(gname, "grass")
                state = S.class_row(clim, cls, True)[month]
                col = STATE_RGB.get(state, (98, 146, 70))
                if gname == "steppe" and state in ("green", "fresh"):
                    col = tuple(int(v * 0.92) for v in col)
            rgb[mm] = col
        if line is not None:
            snow = snow_on & (lv >= line) & (sub != S.GROUND_CLASSES.index("sea")) & \
                (sub != S.GROUND_CLASSES.index("water"))
            rgb[snow] = (236, 240, 246)
    f = root / "assets/world/seasons.json"
    if f.exists():
        from .coords import to_plan
        for fb in json.loads(f.read_text()).get("flood", []):
            cid = C.REGION_CLIMATE.get(fb["region"], "med_green")
            rows = clims[cid].get("water", {})
            rank = (rows.get("river_rank") or [0] * 12)[month]
            if not rank:
                continue
            for x, y, k in fb["tiles"]:
                c, r = to_plan(x, y)
                if k <= rank and c0 <= c <= c1 and r0 <= r <= r1:
                    rgb[r - r0, c - c0] = (120, 110, 80)
    return Image.fromarray(rgb).resize((w * px, h * px), Image.NEAREST)


# -- the year in the life ------------------------------------------------------------------------

def _active(when: dict, day: int) -> bool:
    return CL.filters_pass({k: v for k, v in when.items() if k not in ("hours", "festival",
                                                                       "not_festival", "days")},
                           12.0, day, CL.season_of(day), set())


def year_report(doc: dict, view, root: Path) -> str:
    clims = S.resolved(root)
    raw = S.raw_climates(root)
    cid = doc.get("climate", "med_green")
    clim = clims[cid]
    roles = CL.roles_by_id(doc)
    out = [f"# A year in the life: {doc.get('name')} ({clim.get('name')}, `{cid}`)", "",
           f"{clim.get('character', '')}. Written by `build.sh --year` from "
           f"`assets/regions/{doc['id']}.json` and the catalog's climates; one calendar day is one "
           "month (seasons.md §1.2).", ""]
    if doc.get("moment"):
        m = doc["moment"]
        out += [f"The famous day: **{m['caption']}** (calendar day {m.get('calendar_day')}, "
                f"{m.get('month')}).", ""]
    era = doc.get("era")
    out += ["| Month | Weather | Ground and fields | Who is out (10:30 / 21:30) | Seasonal work | "
            "Festivals and events | Ships, caravans | Birds |",
            "|---|---|---|---|---|---|---|---|"]
    th = doc.get("theme", {})
    tokens = doc.get("lanes_tokens", [])
    for day in range(12):
        mo = S.month_of(day)
        season = S.season_of(day)
        mi = S.month_index(mo)
        wx = {**th.get("weather", {}).get(season, {}), **th.get("weather", {}).get("months", {}).get(mo, {})}
        wtxt = ", ".join(f"{k} {v}" for k, v in wx.items() if k in ("showers", "clouds", "wind", "dust",
                                                                   "fog", "storm", "shimmer"))
        if wx.get("wind_from"):
            wtxt += f" from the {wx['wind_from']}"
        t = clim.get("temp", [None] * 12)[mi]
        if t is not None:
            wtxt = f"{clim['feel'][mi]} ({t} °C); " + wtxt
        line = clim.get("snow", {}).get("line", [None] * 12)[mi]
        if line is not None:
            wtxt += f"; snow above level {line}"
        ground = th.get("seasons", {}).get(season, {}).get("ground", {})
        gflags = [k for k, ms in ground.items() if mo in ms]
        cl = clim.get("classes", {})
        fields = [f"grass {cl.get('grass', ['?'] * 12)[mi]}", f"crops {cl.get('crop', ['?'] * 12)[mi]}",
                  f"trees {cl.get('deciduous', ['?'] * 12)[mi]}", f"vines {cl.get('vine', ['?'] * 12)[mi]}"]
        if mo in clim.get("work", {}).get("olive", []):
            fields.append("olives picked")
        wat = [f"{b['body']} {b['level'][mi]}" for b in doc.get("water", [])
               if b["level"][mi] not in ("normal",)]
        gtxt = ", ".join(fields + gflags + wat)
        fest = CL.festivals_on(doc, day)
        who = ""
        if view is not None:
            def tot(h):
                pop = CL.population(doc, view, h, day, season, fest)
                return sum(sum(r.values()) for r in pop.values()), pop
            n1, pop = tot(10.5)
            n2, _ = tot(21.5)
            busy = sorted(((sum(r.values()), d) for d, r in pop.items()), reverse=True)[:3]
            who = f"{n1:.0f} / {n2:.0f}: " + ", ".join(f"{d} {v:.0f}" for v, d in busy)
        else:
            kinds = []
            for d in doc.get("districts", []):
                for p in d.get("populations", []):
                    if _active(p.get("when", {}), day):
                        k = (p.get("role") or p.get("actor", "")).split(".")[-1]
                        if k not in kinds:
                            kinds.append(k)
            who = ", ".join(kinds[:8])
        seasonal = sorted({p.get("role") for d in doc.get("districts", []) for p in d.get("populations", [])
                           if p.get("role") and "months" in p.get("when", {}) and
                           mo in p["when"]["months"] and len(p["when"]["months"]) < 7})
        work = [k for k, ms in clim.get("work", {}).items() if k != "building" and mo in ms]
        wtx = ", ".join(seasonal) + (f" (the land: {', '.join(work)})" if work else "")
        evs = []
        for e in doc.get("events", []):
            tr = e.get("trigger", {})
            if not CL.event_on_day(doc, e, day, fest):
                continue
            if tr.get("festival") or tr.get("months") or tr.get("on") == "season_turn" or tr.get("season"):
                evs.append(e["id"].replace("turn_", "↻ "))
        ftxt = ", ".join(sorted(fest) + [e for e in evs if e not in fest])
        ships = []
        for tk in tokens:
            bm = tk.get("by_month")
            if bm is None:
                continue
            row = S.lookup_row(clim, raw, bm) if isinstance(bm, str) else bm
            if row:
                ships.append(f"{tk['actor'].split('.')[-1]} ×{row[mi]:g}")
        for h in doc.get("harbours", []):
            row = S.lookup_row(clim, raw, h.get("laid_up", "sailing"))
            if row and row[mi] < h.get("below", 0.3):
                ships.append(f"laid up at {h['zone']}")
        birds = [k for k, ms in clim.get("fauna", {}).items() if mo in ms and k not in ("bees", "eagles")]
        out.append(f"| {mo} ({season} {S.season_day(day)}) | {wtxt} | {gtxt} | {who} | {wtx} | "
                   f"{ftxt} | {', '.join(ships)} | {', '.join(birds)} |")
    out += ["", "## By season", ""]
    for s in C.SEASONS:
        e = th.get("seasons", {}).get(s, {})
        beds = [b["file"] for b in e.get("ambience", {}).get("beds", [])]
        out.append(f"- **{s}**: grade {e.get('grade')}, haze {e.get('haze')}, look {e.get('look', {})}, "
                   f"ground {e.get('ground', {})}, snow line {e.get('snow_line')}"
                   + (f", beds {beds}" if beds else ""))
    if isinstance(era, dict):
        out += ["", f"Caption: {era.get('caption')} with {era.get('year')}"]
    return "\n".join(out) + "\n"


# -- maps ------------------------------------------------------------------------------------------

SEASON_DAYS = [1, 4, 7, 10]     # April, July, October, January: one day of each season


def season_map(doc: dict, view, world, root: Path, hour: float, days=SEASON_DAYS) -> Image.Image:
    """The same hour on a day of each season: the ground as the month shows it, districts shaded
    by movers per screenful (the activity map's ramp) over it, event routes drawn."""
    from .lifereport import _shade, _visible, events_at
    rid = doc["id"]
    c0, r0, c1, r1 = P.REGIONS[rid][3]
    px = 3
    w, h = (c1 - c0 + 1) * px, (r1 - r0 + 1) * px
    fT, fS = font(root, 16, True), font(root, 11)
    img = Image.new("RGB", (w * 2 + 30, (h + 44) * 2 + 50), (22, 24, 30))
    dr = ImageDraw.Draw(img)
    dr.text((10, 8), f"{doc.get('name')} · the same hour ({int(hour):02d}:{int(hour % 1 * 60):02d}) "
            "in each season", font=fT, fill=(240, 236, 226))
    roles = CL.roles_by_id(doc)
    D = world.D[r0:r1 + 1, c0:c1 + 1]
    names = {i: n.split("/", 1)[1] for i, n in enumerate(world.districts) if n.startswith(rid + "/")}
    for k, day in enumerate(days):
        ox, oy = 10 + (k % 2) * (w + 10), 40 + (k // 2) * (h + 44)
        season, mo = S.season_of(day), S.month_of(day)
        base = np.asarray(ground_image(world, root, (c0, r0, c1, r1), S.month_index(mo), 1)).copy()
        fest = CL.festivals_on(doc, day)
        pop = CL.population(doc, view, hour, day, season, fest)
        area = {d["id"]: CL.area_of(d, day) for d in doc.get("districts", [])}
        total = 0.0
        for di, n in names.items():
            vis = sum(_visible(doc, roles, pop.get(n, {}), hour, day, season, fest).values())
            total += vis
            v = CL.screen_movers(view.districts[n], vis) / CL.AREA[area.get(n, "town")]["cap"] \
                if n in view.districts else 0
            if v <= 0.02:
                continue
            m = D == di
            col = np.array(_shade(v), dtype=float)
            base[m] = (base[m] * 0.45 + col * 0.55).astype(np.uint8)
        occ = world.occ[r0:r1 + 1, c0:c1 + 1] >= 0
        base[occ] = (base[occ] * 0.75).astype(np.uint8)
        img.paste(Image.fromarray(base).resize((w, h), Image.NEAREST), (ox, oy))
        for e in events_at(doc, hour, day, season, fest):
            pts = [((view.nodes[n][0] - c0) * px + ox + 1, (view.nodes[n][1] - r0) * px + oy + 1)
                   for n in e.get("route", []) if n in view.nodes]
            if len(pts) > 1:
                dr.line(pts, fill=(255, 250, 240), width=3)
                dr.text((pts[-1][0] + 4, pts[-1][1] - 6), e["id"], font=fS, fill=(255, 250, 240))
        extra = ", ".join(sorted(fest))[:60]
        dr.text((ox, oy + h + 4), f"{season} · {mo} · {total:.0f} visible" + (f" · {extra}" if extra else ""),
                font=fS, fill=(220, 220, 210))
    return img


def land_map(rid: str, world, root: Path, rect=None, px: int = 2) -> Image.Image:
    """The ground of a stretch in each season (April, July, October, January)."""
    c0, r0, c1, r1 = rect or P.REGIONS[rid][3]
    w, h = (c1 - c0 + 1) * px, (r1 - r0 + 1) * px
    fT, fS = font(root, 16, True), font(root, 11)
    img = Image.new("RGB", (w * 2 + 30, (h + 30) * 2 + 50), (22, 24, 30))
    dr = ImageDraw.Draw(img)
    dr.text((10, 8), f"{rid.replace('_', ' ').title()} · the land in each season", font=fT,
            fill=(240, 236, 226))
    for k, day in enumerate(SEASON_DAYS):
        ox, oy = 10 + (k % 2) * (w + 10), 40 + (k // 2) * (h + 30)
        mo = S.month_of(day)
        img.paste(ground_image(world, root, (c0, r0, c1, r1), S.month_index(mo), px), (ox, oy))
        dr.text((ox, oy + h + 4), f"{S.season_of(day)} · {mo}", font=fS, fill=(220, 220, 210))
    return img


# -- the command ---------------------------------------------------------------------------------

CENTRES = {"rome": 10.5, "athens": 10.5, "parsa": 10.5}
LAND = {"attica_north": None, "anatolia": (852, 60, 1040, 280)}


def run(b, rids: list[str], preview: bool) -> None:
    from .lifereport import life_module
    world = b.composed()
    out_dir = b.reports / "seasons"
    out_dir.mkdir(parents=True, exist_ok=True)
    for rid in rids:
        doc = json.loads((b.root / "assets/regions" / f"{rid}.json").read_text())
        layer = next((n for n, _, regs in P.LAYERS if rid in regs), None)
        view = CL.region_view(world, b.cat, b.graphs, b.root, rid, layer) \
            if layer and life_module(layer) else None
        (out_dir / f"{rid}_year.md").write_text(year_report(doc, view, b.root))
        print(f"   year {out_dir / (rid + '_year.md')}")
        if preview and view is not None and rid in CENTRES:
            f = out_dir / f"{rid}_seasons.png"
            season_map(doc, view, world, b.root, CENTRES[rid]).save(f)
            print(f"   preview {f}")
    if preview:
        for rid, rect in LAND.items():
            f = out_dir / f"{rid}_land.png"
            land_map(rid, world, b.root, rect).save(f)
            print(f"   preview {f}")


def run_all(b) -> None:
    """A year in the life for every region file."""
    rids = sorted(f.stem for f in (b.root / "assets/regions").glob("*.json"))
    run(b, rids, False)
