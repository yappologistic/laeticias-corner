"""A city's life without the engine: the day-in-the-life report and the activity maps, and the
command that writes a city's region file from its `regions/<layer>/life.py`.

`build.sh --city parsa athens [--preview] [--no-write]` builds each region document, checks it
(`citylife.check`), writes `assets/regions/<region>.json` when it is clean, the report
`out/worldgen/life/<region>_check.txt` and the day in the life `out/worldgen/life/<region>_day.md`,
and with `--preview` the activity maps `out/worldgen/life/<region>_<day>.png` (districts shaded
by movers per screenful at dawn, noon, dusk and night, the routes of the events under way drawn
over them).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from plan import world_plan as P

from . import citylife as CL
from . import lifesim, rng
from .compose import NONE16
from .preview import font

HERE = Path(__file__).resolve().parent.parent
# A life module may set its own PANELS (name, hour) for its maps.
PANELS = [("dawn", 5.0), ("noon", 12.0), ("dusk", 19.5), ("night", 23.5)]


def life_module(layer: str):
    src = HERE / "regions" / layer / "life.py"
    if not src.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"worldgen_life_{layer}", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dumps(doc: dict) -> str:
    """Stable, diff-friendly JSON: one top-level key per line block, one entry per line."""
    lines = ["{"]
    keys = list(doc)
    for i, k in enumerate(keys):
        v = doc[k]
        comma = "," if i + 1 < len(keys) else ""
        if isinstance(v, list) and v:
            lines.append(f' "{k}": [')
            for j, e in enumerate(v):
                lines.append("  " + json.dumps(e, ensure_ascii=False) + ("," if j + 1 < len(v) else ""))
            lines.append(" ]" + comma)
        elif isinstance(v, dict) and v and k != "theme":
            lines.append(f' "{k}": {{')
            ks = list(v)
            for j, kk in enumerate(ks):
                lines.append(f"  {json.dumps(kk, ensure_ascii=False)}: " +
                             json.dumps(v[kk], ensure_ascii=False) + ("," if j + 1 < len(ks) else ""))
            lines.append(" }" + comma)
        else:
            lines.append(f' "{k}": ' + json.dumps(v, ensure_ascii=False) + comma)
    lines.append("}")
    return "\n".join(lines) + "\n"


# -- the day in the life ----------------------------------------------------------------------

def _visible(doc, roles, row, h, day, season, fest):
    vis = {}
    for role_id, n in row.items():
        r = roles.get(role_id)
        b = CL.block_at(r, h, day, season, fest) if r else None
        if r is None or b is None:
            continue
        rt = b.get("routine") or (b.get("pick") or [{}])[0].get("routine", "")
        if CL.routine_visible(rt, r.get("routines", {})):
            vis[role_id] = n
    return vis


def screen_movers(view, dist, vis_total) -> float:
    return CL.screen_movers(view.districts[dist], vis_total)


def events_at(doc, h: float, day: int, season: str, fest: set[str]) -> list[dict]:
    out = []
    for e in doc.get("events", []):
        t = e.get("trigger", {})
        if t.get("festival") and t["festival"] not in fest:
            continue
        if t.get("not_festival") and t["not_festival"] in fest:
            continue
        if t.get("season") and season not in t["season"]:
            continue
        if "days" in t and day % t["days"]["every"] != t["days"].get("offset", 0):
            continue
        if t.get("on") not in ("window", "calendar"):
            continue
        if "chance" in t and rng.hash64(f"{doc['id']}:{e['id']}:{day}") % 1000 >= t["chance"] * 1000:
            continue   # the day plan's draw (living-world §5.2), the same on every run
        a, b = CL.event_window(e)
        if a <= h < b or a <= h + 24 < b:
            out.append(e)
    return out


def chains_at(doc, h: float) -> list[str]:
    return [c["id"] for c in doc.get("chains", []) if CL.in_hours(c.get("hours", ["06:00", "18:00"]), h)]


def day_report(doc: dict, view, problems: list) -> str:
    roles = CL.roles_by_id(doc)
    season = doc.get("season", "spring")
    area = {d["id"]: d.get("area") for d in doc.get("districts", [])}
    out = [f"# A day in the life: {doc.get('name')} ({season})", "",
           f"{doc.get('caption', '')}. Written by `build.sh --city {doc['id']}` from "
           f"`assets/regions/{doc['id']}.json`; numbers are the population model's (actors "
           "present; movers per screenful = visible actors x 0.85 x 250 tiles / the district's "
           "tiles).", ""]
    out += [f"Checks: {CL.report_lines(problems)[0]}.", ""]
    for day, label in _days(doc):
        fest = CL.festivals_on(doc, season, day % 3) | set(label[1])
        out += [f"## {label[0]}", "", "| Hour | Present | Visible | Busiest districts (movers per "
                "screenful) | Chains running | Events |", "|---|---:|---:|---|---|---|"]
        for h in range(24):
            hh = h + 0.5
            pop = CL.population(doc, view, hh, day, season, fest)
            present = sum(sum(r.values()) for r in pop.values())
            vis_d = {d: _visible(doc, roles, row, hh, day, season, fest) for d, row in pop.items()}
            visible = sum(sum(v.values()) for v in vis_d.values())
            busy = sorted(((screen_movers(view, d, sum(v.values())), d) for d, v in vis_d.items()),
                          reverse=True)[:4]
            busy_s = ", ".join(f"{d} {m:.0f}" for m, d in busy if m >= 0.5)
            ch = chains_at(doc, hh)
            ev = [e["id"] for e in events_at(doc, hh, day, season, fest)]
            out.append(f"| {h:02d}:30 | {present:.0f} | {visible:.0f} | {busy_s} | "
                       f"{len(ch)} | {', '.join(ev)} |")
        out.append("")
    out += ["## Districts", "", "| District | Area | Tiles | Who (by share at 10:30) | "
            "Movers per screenful at 05:00 / 10:30 / 13:00 / 16:30 / 19:30 / 23:30 |",
            "|---|---|---:|---|---|"]
    for d in sorted(view.districts):
        cells = []
        who = ""
        for hh in (5.0, 10.5, 13.0, 16.5, 19.5, 23.5):
            pop = CL.population(doc, view, hh, 1, season, set())
            vis = _visible(doc, roles, pop.get(d, {}), hh, 1, season, set())
            cells.append(f"{screen_movers(view, d, sum(vis.values())):.0f}")
            if hh == 10.5:
                tot = sum(pop.get(d, {}).values()) or 1
                top = sorted(pop.get(d, {}).items(), key=lambda x: -x[1])[:5]
                who = ", ".join(f"{k} {v / tot:.0%}" for k, v in top if v > 0)
        out.append(f"| {d} | {area.get(d)} | {view.districts[d]['tiles']} | {who} | "
                   f"{' / '.join(cells)} |")
    out += ["", "## Chains (simulated week)", "", "| Chain | Hours | Period | Units used per day | "
            "Stages: share of working time waiting / full |", "|---|---|---:|---|---|"]
    for c in doc.get("chains", []):
        res = lifesim.simulate(c, view, roles)
        parts = []
        for s, st in zip(c["stages"], res.get("stages", [])):
            w = max(1, st["work"])
            parts.append(f"{s.get('by')} {st['starve'] / w:.0%}/{st['block'] / w:.0%}")
        out.append(f"| {c['id']} | {'-'.join(c.get('hours', []))} | {c['period']} | "
                   f"{res.get('per_day')} | {'; '.join(parts)} |")
    out += ["", "## Events", "", "| Event | When | Rarity | Route | Cast |", "|---|---|---|---|---|"]
    for e in doc.get("events", []):
        t = e.get("trigger", {})
        when = t.get("on", "")
        if t.get("hours"):
            when += f" {t['hours'][0]}-{t['hours'][1]}"
        for k in ("festival", "season", "days", "every"):
            if k in t:
                when += f" {k} {json.dumps(t[k], ensure_ascii=False)}"
        cast = sum(c.get("count", 1) for c in e.get("cast", []))
        out.append(f"| {e['id']} | {when} | {e.get('rarity', '')} | "
                   f"{' → '.join(e.get('route', [])[:8])} | {cast} |")
    return "\n".join(out) + "\n"


def _days(doc) -> list[tuple[int, tuple[str, tuple]]]:
    """The days the report and maps show: an ordinary day and each special one."""
    days = doc.get("days_shown") or [{"day": 1, "label": "An ordinary day (week day 1)"}]
    return [(d["day"], (d["label"], tuple(d.get("festivals", [])))) for d in days]


# -- activity maps ----------------------------------------------------------------------------

def _shade(v: float) -> tuple[int, int, int]:
    """0 (empty) .. 1 (at the area's cap) on a night-blue to amber ramp."""
    stops = [(0.0, (34, 40, 66)), (0.15, (52, 82, 120)), (0.35, (70, 140, 140)),
             (0.6, (214, 190, 90)), (1.0, (240, 120, 50))]
    v = max(0.0, min(1.0, v))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            f = (v - a) / (b - a)
            return tuple(int(ca[k] + (cb[k] - ca[k]) * f) for k in range(3))
    return stops[-1][1]


def activity_map(doc: dict, view, world, root: Path, day: int, label: str,
                 fest: tuple = (), panels=PANELS) -> Image.Image:
    roles = CL.roles_by_id(doc)
    season = doc.get("season", "spring")
    area = {d["id"]: d.get("area", "town") for d in doc.get("districts", [])}
    rid = doc["id"]
    c0, r0, c1, r1 = P.REGIONS[rid][3]
    w, h = c1 - c0 + 1, r1 - r0 + 1
    px = 3
    D = world.D[r0:r1 + 1, c0:c1 + 1]
    names = {i: n.split("/", 1)[1] for i, n in enumerate(world.districts) if n.startswith(rid + "/")}
    fT, fS = font(root, 16, True), font(root, 11)
    pw, ph = w * px, h * px
    cols = 2 if len(panels) <= 4 else 3
    rows = -(-len(panels) // cols)
    img = Image.new("RGB", (pw * cols + 10 * cols + 10, (ph + 40) * rows + 50), (22, 24, 30))
    dr = ImageDraw.Draw(img)
    dr.text((10, 8), f"{doc.get('name')} · {label}", font=fT, fill=(240, 236, 226))
    fests = set(fest) | CL.festivals_on(doc, season, day % 3)
    for k, (pname, hh) in enumerate(panels):
        ox, oy = 10 + (k % cols) * (pw + 10), 40 + (k // cols) * (ph + 40)
        pop = CL.population(doc, view, hh, day, season, fests)
        val = {}
        total = 0.0
        for d, row in pop.items():
            vis = sum(_visible(doc, roles, row, hh, day, season, fests).values())
            total += vis
            val[d] = screen_movers(view, d, vis) / CL.AREA[area.get(d, "town")]["cap"]
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[:] = (16, 18, 24)
        for di, n in names.items():
            rgb[D == di] = _shade(val.get(n, 0.0))
        occ = world.occ[r0:r1 + 1, c0:c1 + 1] >= 0
        rgb[occ] = (rgb[occ] * 0.72).astype(np.uint8)
        im = Image.fromarray(rgb).resize((pw, ph), Image.NEAREST)
        img.paste(im, (ox, oy))
        for e in events_at(doc, hh, day, season, fests):
            pts = [((view.nodes[n][0] - c0) * px + ox + 1, (view.nodes[n][1] - r0) * px + oy + 1)
                   for n in e.get("route", []) if n in view.nodes]
            if len(pts) > 1:
                dr.line(pts, fill=(255, 250, 240), width=3)
                dr.text((pts[-1][0] + 4, pts[-1][1] - 6), e["id"], font=fS, fill=(255, 250, 240))
        for d, v in val.items():
            b = view.districts[d]["bbox"]
            if v >= 0.25:
                cx = ((b[0] + b[2]) / 2 - c0) * px + ox
                cy = ((b[1] + b[3]) / 2 - r0) * px + oy
                dr.text((cx - 12, cy - 5), d, font=fS, fill=(250, 250, 250))
        dr.text((ox, oy + ph + 4), f"{pname} {int(hh):02d}:{int(hh % 1 * 60):02d} · "
                f"{total:.0f} visible · chains {len(chains_at(doc, hh))}", font=fS,
                fill=(220, 220, 210))
    return img


# -- the command ------------------------------------------------------------------------------

def finish_doc(doc: dict, world, b) -> dict:
    """What every region file gets beside its life: its sound and its look."""
    from . import look, places, sound
    doc = sound.apply(places.apply(doc), world, b.cat, b.root)
    return look.apply(doc, world, b.cat, b.root)


def run(b, rids: list[str], preview: bool, write: bool) -> bool:
    """Build, check and write the region files of the cities with a life module."""
    world = b.composed()
    out_dir = b.reports / "life"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = True
    for rid in rids:
        layer = next(n for n, _, regs in P.LAYERS if rid in regs)
        mod = life_module(layer)
        if mod is None:
            raise SystemExit(f"no regions/{layer}/life.py for {rid!r}")
        view = CL.region_view(world, b.cat, b.graphs, b.root, rid, layer)
        doc = finish_doc(mod.build(view), world, b)
        problems = CL.check(doc, view)
        errs = [p for p in problems if p.level == "error"]
        (out_dir / f"{rid}_check.txt").write_text("\n".join(CL.report_lines(problems)) + "\n")
        (out_dir / f"{rid}_day.md").write_text(day_report(doc, view, problems))
        print(f"{rid}: life {len(errs)} error(s), {len(problems) - len(errs)} warning(s) -> "
              f"{out_dir / (rid + '_check.txt')}")
        for p in errs[:15]:
            print("   " + p.text())
        if errs:
            ok = False
        elif write:
            (b.root / "assets/regions" / f"{rid}.json").write_text(dumps(doc))
        if preview:
            for day, (label, fest) in _days(doc):
                f = out_dir / f"{rid}_day{day}.png"
                activity_map(doc, view, world, b.root, day, label, fest,
                             getattr(mod, "PANELS", PANELS)).save(f)
                print(f"   preview {f}")
    return ok


def check_regions(b) -> int:
    """Sound (L9), look (L10) and names and eras (L11) errors in every committed region file,
    cities or not."""
    from . import look, places, sound
    files, families = sound.manifests(b.root)
    n = 0
    for f in sorted((b.root / "assets/regions").glob("*.json")):
        doc = json.loads(f.read_text())
        probs = [("L9",) + x for x in sound.check(doc, files, families)] + \
                [("L10",) + x for x in look.check(doc)] + \
                [("L11",) + x for x in places.check(doc)]
        errs = [x for x in probs if x[1] == "error"]
        if errs:
            print(f"{doc.get('id')}: sound and look {len(errs)} error(s)")
            for code, level, where, msg in errs[:8]:
                print(f"   {code} {level}: {doc.get('id')}: {where}: {msg}")
        n += len(errs)
    return n


def check_committed(b, world) -> int:
    """Errors in the committed region files of every city with a life module (`--check`)."""
    n = 0
    for layer, _, regs in P.LAYERS:
        if life_module(layer) is None:
            continue
        for rid in regs:
            f = b.root / "assets/regions" / f"{rid}.json"
            if not f.exists():
                continue
            view = CL.region_view(world, b.cat, b.graphs, b.root, rid, layer)
            problems = CL.check(json.loads(f.read_text()), view)
            errs = [p for p in problems if p.level == "error"]
            print(f"{rid}: life {len(errs)} error(s), {len(problems) - len(errs)} warning(s)")
            for p in errs[:12]:
                print("   " + p.text())
            n += len(errs)
    return n
