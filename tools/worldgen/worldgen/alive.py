"""How alive the whole world is, in the data's numbers, and the checks that keep it alive.

`build.sh --alive` reads every region file over the composed world and prints, per region and
stretch, per hour block (dawn, morning, midday, afternoon, dusk, evening, small hours) and month,
the expected actors out of doors (people, animals, birds) and the token travellers and ships on
its lanes; the share of the map where a screen holds nothing alive, by day and at 02:00; and the
worst-case live count in the engine's active area (chunks touching the view grown by
`kLiveMargin`, capped at `kLiveCap`), at 1x and at the 1/4 zoom of a 1440p window. Reports go to
`out/worldgen/alive/` (`alive.md`, `alive.json`).

Numbers use the engine's population formula (citylife.population): `density[hour] x
max_per_chunk x tiles / 1024`, `per_item` x placed instances, counted only while a role's
schedule has a visible block, with `months` honoured (the data's meaning; the engine reads them
once its months round lands). Tokens count their instances and their group's members, share of
the month from `by_month`, spread along their line.

Checks (`check`, run by `--alive` and `--check`):
  A1  no populated region or stretch has zero expected life in a daytime block (morning,
      midday, afternoon) of any month
  A2  no 1x active area asks for more than the live cap from the lanes' own data (zoomed out,
      or with a city in reach, the engine scales crowds to the cap: reported as warnings)
  A3  every traffic token has both ends, a path, a rest stop on its way, hours and offsets
  A4  `months` filters: valid names; no population, token or event doubled in a month by two
      entries of one family; a family split by months leaves no hole inside the year
  A5  every region has an event besides the season turns in every season
  A6  no two large events of one region can run at once
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from plan import world_plan as P

from . import citylife as CL
from . import climates as C
from . import seasons as SEAS
from .compose import NONE16, live_items
from .coords import COLS, ROWS, to_plan
from .raster import path_tiles

LIVE_CAP = 800             # tuning::life::kLiveCap
LIVE_MARGIN = 12           # tuning::life::kLiveMargin
CHUNK = P.CHUNK
SCREEN = 45                # a 1920 x 1080 screen at 1x holds about 2 025 tiles (audit-alive §0)
EMPTY = 0.5                # fewer actors expected in a screen than this: nothing alive there
# Active areas in chunks per side: a 1440p window's view (2560/64 + 1440/32 = 85 tiles at 1x,
# four times that at 1/4) grown by the margin, as chunks it can touch.
WINDOWS = {"1x": -(-(85 + 2 * LIVE_MARGIN) // CHUNK) + 1,
           "quarter": -(-(340 + 2 * LIVE_MARGIN) // CHUNK) + 1}
BLOCKS = {"dawn": (5, 7), "morning": (7, 11), "midday": (11, 14), "afternoon": (14, 17),
          "dusk": (17, 20), "evening": (20, 23), "small hours": (23, 29)}
DAYTIME = ("morning", "midday", "afternoon")
CHECK_HOURS = [6.0, 9.0, 12.5, 15.5, 18.5, 21.5, 2.5]   # one hour in each block, for --check
MONTHS = C.MONTHS
BIRDS = ("gull", "stork", "crane", "eagle", "swift", "raven", "pigeon", "swallow", "owl",
         "hoopoe", "goose", "hen", "rooster", "heron")
ANIMALS = ("sheep", "goat", "ox", "donkey", "mule", "dog", "horse", "cat", "pig", "camel",
           "dromedary", "gazelle", "heifer", "zebu", "bull", "ram", "buffalo", "oryx", "lion",
           "okapi", "hound", "racehorse")
CITIES = {rid for rid, v in P.REGIONS.items() if v[0] == "city"}


def category(kind: str) -> str:
    name = kind.split(".")[-1]
    if any(name == b or name.startswith(b) for b in BIRDS):
        return "birds"
    if any(a in name for a in ANIMALS):
        return "animals"
    return "people"


# -- the world as the life data sees it ---------------------------------------------------------

@dataclass
class Facts:
    """Districts (tiles, index raster) and per-item instances by region and district."""
    D: np.ndarray
    districts: list[str]
    tiles: dict[str, int]
    items: dict[tuple[str, str, str], list[tuple[int, int]]] = field(default_factory=dict)


def region_layer(rid: str, graphs: dict) -> str:
    return rid if rid in graphs else "base"


def facts(world, graphs: dict) -> Facts:
    u, c = np.unique(world.D, return_counts=True)
    tiles = {world.districts[d]: int(n) for d, n in zip(u.tolist(), c.tolist()) if d != NONE16}
    f = Facts(world.D, world.districts, tiles)
    for _, it in live_items(world):
        d = int(world.D[it.r, it.c])
        if d == NONE16:
            continue
        rid = world.districts[d].split("/", 1)[0]
        if region_layer(rid, graphs) != it.layer:
            continue
        dist = CL._district_at(world, it, rid)
        if dist:
            f.items.setdefault((rid, dist, it.id), []).append((it.c, it.r))
    return f


def resolve_row(doc: dict, tk: dict, raw: dict) -> list[float]:
    """A token's twelve monthly shares: its `by_month` (a climate row or factors), its months."""
    row = tk.get("by_month", 1.0)
    if isinstance(row, str):
        cid = C.REGION_CLIMATE.get(doc["id"])
        got = SEAS.lookup_row(SEAS.resolve(raw, cid), raw, row) if cid else None
        row = got if got is not None else [1.0] * 12
    if isinstance(row, (int, float)):
        row = [float(row)] * 12
    ms = tk.get("when", {}).get("months")
    return [min(1.0, float(v)) if (not ms or m in ms) else 0.0 for m, v in zip(MONTHS, row)]


# -- one region's expected actors -------------------------------------------------------------

def region_counts(doc: dict, F: Facts, h: float, month: int) -> list[tuple[str, str, float]]:
    """[(district or "@c,r" for a per-item placement, category, actors out of doors)] at hour h
    of the month (calendar day = month index: its season, festivals and week day)."""
    day = month
    season = SEAS.season_of(day)
    fest = CL.festivals_on(doc, day)
    roles = CL.roles_by_id(doc)
    dens = doc.get("densities", {})
    out = []
    for d in doc.get("districts", []):
        name = f"{doc['id']}/{d['id']}"
        if name not in F.tiles:
            continue
        for p in d.get("populations", []):
            if not CL.filters_pass(p.get("when", {}), h, day, season, fest):
                continue
            key = p.get("role") or p.get("actor")
            r = roles.get(key)
            if r is not None:
                b = CL.block_at(r, h, day, season, fest)
                if b is None:
                    continue
                rt = b.get("routine") or (b.get("pick") or [{}])[0].get("routine", "")
                if not CL.routine_visible(rt, r.get("routines", {})):
                    continue
                kind = r["actor"]
            else:
                kind = key
            f = dens.get(p.get("density", "always"), [1.0] * 24)[int(h) % 24]
            if f <= 0:
                continue
            cat = category(kind)
            if "per_item" in p:
                for (c, rr) in F.items.get((doc["id"], d["id"], p["per_item"]), []):
                    out.append((f"@{c},{rr}", cat, p.get("count", 1) * f))
            else:
                out.append((name, cat, f * p.get("max_per_chunk", 0) * F.tiles[name] / 1024))
    return out


def token_lines(doc: dict, graphs: dict, joined) -> list[tuple[dict, list[tuple[int, int]]]]:
    """Each token with the plan tiles of its line."""
    out = []
    for tk in doc.get("lanes_tokens", []):
        if "lane" in tk:
            layer, lid = tk["lane"].split(":", 1)
            ln = next((x for x in graphs.get(layer).lanes if x.id == lid), None) \
                if layer in graphs else None
            pts = path_tiles([to_plan(*p) for p in ln.points]) if ln else []
        else:
            p = joined.path(tk["route"]["start"], tk["route"]["end"])
            pts = joined.course(p[0]) if p else []
        out.append((tk, pts))
    return out


def token_people(tk: dict, groups: dict) -> float:
    g = groups.get(tk.get("group"))
    members = sum(m.get("count", 1) for m in g.get("members", [])) if g else 0
    return float(tk.get("count", 1)) * (1 + members)


# -- the whole world ---------------------------------------------------------------------------

@dataclass
class Result:
    regions: dict = field(default_factory=dict)      # rid -> block -> month -> {cat: n}
    tokens: dict = field(default_factory=dict)       # rid -> month -> instances (people)
    empty: dict = field(default_factory=dict)        # "jun 10:00" -> share of tiles
    windows: dict = field(default_factory=dict)      # "1x"/"quarter" -> worst
    routes: list = field(default_factory=list)       # (rid, actor, from-to, count, months, hours)


def load_docs(root: Path, regions: Path | None = None) -> dict[str, dict]:
    regions = regions or root / "assets/regions"
    return {f.stem: json.loads(f.read_text()) for f in sorted(regions.glob("*.json"))}


def _box(a: np.ndarray, n: int) -> np.ndarray:
    """Sum over the n x n window centred on each tile (edges clipped)."""
    c = np.pad(a, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    h = n // 2
    r0 = np.clip(np.arange(a.shape[0]) - h, 0, a.shape[0])
    r1 = np.clip(np.arange(a.shape[0]) + h + 1, 0, a.shape[0])
    c0 = np.clip(np.arange(a.shape[1]) - h, 0, a.shape[1])
    c1 = np.clip(np.arange(a.shape[1]) + h + 1, 0, a.shape[1])
    return c[r1][:, c1] - c[r0][:, c1] - c[r1][:, c0] + c[r0][:, c0]


def chunk_sums(a: np.ndarray) -> np.ndarray:
    rr, cc = a.shape[0] // CHUNK, a.shape[1] // CHUNK
    return a[:rr * CHUNK, :cc * CHUNK].reshape(rr, CHUNK, cc, CHUNK).sum(axis=(1, 3))


def window_max(chunks: np.ndarray, n: int) -> tuple[float, tuple[int, int]]:
    """The largest sum of an n x n block of chunks and its top-left chunk (row, col)."""
    s = np.pad(chunks, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    rr, cc = chunks.shape
    n_r, n_c = min(n, rr), min(n, cc)
    w = s[n_r:, n_c:] - s[:-n_r, n_c:] - s[n_r:, :-n_c] + s[:-n_r, :-n_c]
    i = int(np.argmax(w))
    return float(w.flat[i]), divmod(i, w.shape[1])


def measure(world, graphs: dict, root: Path, docs: dict[str, dict], hours=None,
            months=None) -> Result:
    from .traffic import Joined
    F = facts(world, graphs)
    joined = Joined(graphs)
    raw = SEAS.raw_climates(root)
    dindex = {n: i for i, n in enumerate(F.districts)}
    res = Result()
    lines = {rid: token_lines(doc, graphs, joined) for rid, doc in docs.items()}
    arrays = {rid: [(tk, _rc(pts)) for tk, pts in ls] for rid, ls in lines.items()}
    groups = {rid: {g["id"]: g for g in doc.get("groups", [])} for rid, doc in docs.items()}
    city_mask = np.zeros((ROWS, COLS), bool)
    for rid in CITIES:
        c0, r0, c1, r1 = P.REGIONS[rid][3]
        city_mask[r0:r1 + 1, c0:c1 + 1] = True
    city_chunks = chunk_sums(city_mask.astype(np.float32)) > 0
    water = np.isin(world.T, [i for i, t in enumerate(world.terrains)
                              if "sea" in t or "shallows" in t])
    hours = hours if hours is not None else [h + 0.5 for h in range(24)]
    months = months if months is not None else list(range(12))
    worst = {k: (0.0, None, "") for k in WINDOWS}
    worst_lane = {k: (0.0, None, "") for k in WINDOWS}
    for m in months:
        shares = {rid: [(tk, pts, token_people(tk, groups[rid]) * resolve_row(docs[rid], tk, raw)[m])
                        for tk, pts in arrays[rid]] for rid in docs}
        for rid in docs:
            res.tokens.setdefault(rid, {})[MONTHS[m]] = round(sum(
                n for tk, _p, n in shares[rid]), 1)
        for h in hours:
            grid = np.zeros((ROWS, COLS), np.float32)
            lane_grid = np.zeros((ROWS, COLS), np.float32)
            vals = np.zeros(len(F.districts) + 1, np.float32)
            lane_vals = np.zeros_like(vals)
            for rid, doc in docs.items():
                tot = {"people": 0.0, "animals": 0.0, "birds": 0.0}
                for where, cat, n in region_counts(doc, F, h, m):
                    tot[cat] += n
                    if where.startswith("@"):
                        c, r = (int(x) for x in where[1:].split(","))
                        grid[r, c] += n
                        if rid not in CITIES:
                            lane_grid[r, c] += n
                    else:
                        vals[dindex[where]] += n / F.tiles[where]
                        if rid not in CITIES:
                            lane_vals[dindex[where]] += n / F.tiles[where]
                hh = int(h) % 24
                hours_in = [b for b, (a, z) in BLOCKS.items() if a <= hh < z or a <= hh + 24 < z]
                for b in hours_in:
                    cell = res.regions.setdefault(rid, {}).setdefault(b, {}).setdefault(
                        MONTHS[m], {"people": 0.0, "animals": 0.0, "birds": 0.0, "n": 0})
                    for k in tot:
                        cell[k] += tot[k]
                    cell["n"] += 1
                for tk, pts, n in shares[rid]:
                    if n <= 0 or not len(pts[0]) or \
                            not _in_hours(tk.get("hours", ["00:00", "24:00"]), h):
                        continue
                    each = n / len(pts[0])
                    np.add.at(grid, pts, each)
                    if rid not in CITIES:
                        np.add.at(lane_grid, pts, each)
            Dx = np.where(F.D == NONE16, len(F.districts), F.D)
            grid += vals[Dx]
            lane_grid += lane_vals[Dx]
            label = f"{MONTHS[m]} {int(h):02d}:00"
            box = _box(grid, SCREEN)
            dead = box < EMPTY
            res.empty[label] = [float(dead.mean()), float(dead[~water].mean()),
                                float(dead[water].mean())]
            ch, lch = chunk_sums(grid), chunk_sums(lane_grid)
            for k, n in WINDOWS.items():
                v, at = window_max(ch, n)
                if v > worst[k][0]:
                    city = bool(city_chunks[at[0]:at[0] + n, at[1]:at[1] + n].any())
                    worst[k] = (v, at, label + _where(at, n) + (" (reaches a city)" if city else ""))
                v, at = window_max(lch, n)
                if v > worst_lane[k][0]:
                    worst_lane[k] = (v, at, label + _where(at, n))
    for k in WINDOWS:
        res.windows[k] = {"all": worst[k], "lanes": worst_lane[k], "chunks": WINDOWS[k]}
    for rid, doc in docs.items():
        for tk, pts in lines[rid]:
            ends = tk.get("lane") or f"{tk['route']['start']} - {tk['route']['end']}"
            row = resolve_row(doc, tk, raw)
            res.routes.append((rid, tk["actor"], ends, tk.get("count", 1), tk.get("group", ""),
                               [round(x, 2) for x in row], tk.get("hours"), len(pts),
                               tk.get("note", "")))
    return res


def _where(at: tuple[int, int], n: int) -> str:
    """A window of n x n chunks from chunk (row, col), in plan coordinates."""
    r0, c0 = at[0] * CHUNK, at[1] * CHUNK
    return f", C {c0}-{c0 + n * CHUNK - 1} R {r0}-{min(ROWS, r0 + n * CHUNK) - 1}"


def _rc(pts: list[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Plan tiles as index arrays (rows, columns), inside the map."""
    a = np.array([(r, c) for c, r in pts if 0 <= r < ROWS and 0 <= c < COLS], np.int64)
    if not len(a):
        return (np.zeros(0, np.int64), np.zeros(0, np.int64))
    return (a[:, 0], a[:, 1])


def _in_hours(hours, h: float) -> bool:
    a, b = CL.hour_of(hours[0]), CL.hour_of(hours[1])
    if b >= 24 and a == 0:
        return True
    return a <= h < b if a <= b else (h >= a or h < b)


# -- checks ----------------------------------------------------------------------------------

def check_daytime(regions: dict) -> list[tuple[str, str, str]]:
    """A1 on measured blocks: [(level, where, message)]."""
    out = []
    for rid, blocks in sorted(regions.items()):
        populated = any(c["people"] + c["animals"] + c["birds"] > 0
                        for b in blocks.values() for c in b.values())
        if not populated:
            continue
        for b in DAYTIME:
            for m, c in blocks.get(b, {}).items():
                if c["people"] + c["animals"] + c["birds"] <= 0:
                    out.append(("error", f"{rid} {b} {m}", "no life expected out of doors"))
    return out


def check_windows(windows: dict) -> list[tuple[str, str, str]]:
    """A2 on measured windows: at 1x, where every actor is seen, the lanes' own data stays under
    the cap; zoomed out, and wherever a city is in reach, the engine scales crowds to the cap
    and a count over it is a warning."""
    out = []
    for k, w in windows.items():
        v, _at, label = w["lanes"]
        if v > LIVE_CAP:
            out.append(("error" if k == "1x" else "warning", f"active area {k}",
                        f"the lanes' own data asks for {v:.0f} actors at {label}, over the cap "
                        f"{LIVE_CAP}" + ("" if k == "1x" else " (scaled by the engine)")))
        v, _at, label = w["all"]
        if v > LIVE_CAP:
            out.append(("warning", f"active area {k}", f"{v:.0f} actors at {label} (the engine "
                        f"scales a city's crowd to its cap {LIVE_CAP})"))
    return out


def check_tokens(docs: dict, graphs: dict, joined) -> list[tuple[str, str, str]]:
    """A3: both ends, a path, rest stops on the way, hours, offsets."""
    out = []
    for rid, doc in sorted(docs.items()):
        for tk in doc.get("lanes_tokens", []):
            where = f"{rid} token {tk.get('id', tk['actor'])}"
            rest = tk.get("rest") or []
            if not rest:
                out.append(("error", where, "has no rest stop (where it waits outside its hours)"))
            hours = tk.get("hours")
            if not (isinstance(hours, list) and len(hours) == 2):
                out.append(("error", where, "has no hours [from, to]"))
            if len(tk.get("offsets", [])) != int(tk.get("count", 1)):
                out.append(("error", where, "needs one offset per instance"))
            if "lane" in tk:
                layer, lid = tk["lane"].split(":", 1)
                ln = next((x for x in graphs[layer].lanes if x.id == lid), None) \
                    if layer in graphs else None
                if ln is None:
                    out.append(("error", where, f"lane {tk['lane']} does not exist"))
                    continue
                ports = {p.id for p in ln.ports}
                for r in rest:
                    if r not in ports:
                        out.append(("error", where, f"rest {r!r} is not a port of {tk['lane']}"))
                continue
            a, b = tk["route"]["start"], tk["route"]["end"]
            if a not in joined.adj or b not in joined.adj:
                out.append(("error", where, f"route end {a if a not in joined.adj else b} does "
                            "not exist"))
                continue
            p = joined.path(a, b)
            if p is None:
                out.append(("error", where, f"no path from {a} to {b}"))
                continue
            for r in rest:
                if r not in p[0]:
                    out.append(("error", where, f"rest {r} is not on its way"))
    return out


def _month_set(f: dict) -> set[str]:
    return set(f.get("months") or MONTHS)


def _family_key(p: dict) -> str:
    w = {k: v for k, v in p.get("when", {}).items() if k != "months"}
    return json.dumps([p.get("role") or p.get("actor"), p.get("per_item"), p.get("density"),
                       p.get("variant"), w], sort_keys=True)


def _hole(ms: set[str]) -> bool:
    """A set of months with a gap that is not one run of the year (cyclic)."""
    if not ms or len(ms) == 12:
        return False
    idx = [MONTHS.index(m) for m in ms]
    runs = sum(1 for i in idx if (i - 1) % 12 not in idx)
    return runs > 1


def check_months(docs: dict) -> list[tuple[str, str, str]]:
    """A4: month names; doubles within a family of entries; holes inside a split family."""
    out = []
    valid = set(MONTHS)

    def names(where, ms):
        bad_ = [m for m in ms if m not in valid]
        if bad_:
            out.append(("error", where, f"months {bad_} are not month names"))

    for rid, doc in sorted(docs.items()):
        for d in doc.get("districts", []):
            fam: dict[str, list[set[str]]] = {}
            for p in d.get("populations", []):
                ms = p.get("when", {}).get("months")
                if ms is not None:
                    names(f"{rid} district {d['id']}", ms)
                fam.setdefault(_family_key(p), []).append(_month_set(p.get("when", {})))
            for key, sets in fam.items():
                who = json.loads(key)[0]
                for i, a in enumerate(sets):
                    for b in sets[i + 1:]:
                        if a & b:
                            out.append(("error", f"{rid} district {d['id']} {who}",
                                        f"two entries both hold {sorted(a & b, key=MONTHS.index)}"))
                if len(sets) > 1 and _hole(set().union(*sets)):
                    out.append(("error", f"{rid} district {d['id']} {who}",
                                "entries split by months leave a hole inside the year"))
        for tk in doc.get("lanes_tokens", []):
            ms = tk.get("when", {}).get("months")
            if ms is not None:
                names(f"{rid} token {tk.get('id')}", ms)
            row = tk.get("by_month")
            if isinstance(row, list) and len(row) != 12:
                out.append(("error", f"{rid} token {tk.get('id')}", "by_month needs 12 factors"))
        for e in doc.get("events", []):
            ms = e.get("trigger", {}).get("months")
            if ms is not None:
                names(f"{rid} event {e['id']}", ms)
        seen: dict[str, set[str]] = {}
        for f in doc.get("festivals", []):
            if "months" in f:
                names(f"{rid} festival {f['id']}", f["months"])
            if f["id"] in seen:
                out.append(("error", f"{rid} festival {f['id']}", "is listed twice"))
            seen[f["id"]] = set(f.get("months", []))
        for c in doc.get("chains", []):
            if "months" in c:
                names(f"{rid} chain {c['id']}", c["months"])
    return out


def _event_seasons(e: dict) -> set[str]:
    t = e.get("trigger", {})
    if "months" in t:
        return {SEAS.season_of(MONTHS.index(m)) for m in t["months"] if m in MONTHS}
    if "season" in t:
        s = t["season"]
        return set(s if isinstance(s, list) else [s])
    return set(C.SEASONS)


def check_events(docs: dict) -> list[tuple[str, str, str]]:
    """A5 and A6."""
    out = []
    for rid, doc in sorted(docs.items()):
        evs = [e for e in doc.get("events", []) if e.get("trigger", {}).get("on") != "season_turn"]
        have = set().union(*(_event_seasons(e) for e in evs)) if evs else set()
        for s in C.SEASONS:
            if s not in have:
                out.append(("error", f"{rid} {s}", "no event but the season's turn"))
        byid = {e["id"]: e for e in evs}
        large = [(e, _plan(doc, e, byid)) for e in evs if e.get("size") == "large"]
        large = [(e, p) for e, p in large if p is not None]
        for i, (a, (da, (a0, a1))) in enumerate(large):
            for b, (db, (b0, b1)) in large[i + 1:]:
                if not da & db or _follows(a, b, byid) or _follows(b, a, byid):
                    continue
                if a0 < b1 and b0 < a1:
                    out.append(("error", f"{rid} events {a['id']} / {b['id']}",
                                "two large events can run at once"))
    return out


def _plan(doc: dict, e: dict, byid: dict, depth: int = 0):
    """(calendar days, (start, end) game hours) of a planned event; an `after` event follows
    its event's end; events started by arrivals, weather or other happenings are unplanned."""
    t = e.get("trigger", {})
    on = t.get("on")
    if on in ("window", "calendar", "season_turn"):
        return ({d for d in range(CL.WEEK_CYCLE) if CL.event_on_day(doc, e, d)},
                CL.event_window(e))
    if on == "after" and depth < 8 and t.get("event") in byid:
        p = _plan(doc, byid[t["event"]], byid, depth + 1)
        if p is None:
            return None
        days, (_a, end) = p
        return days, (end, end + max(e.get("duration", [0, 0])) / 30.0)
    return None


def _follows(a: dict, b: dict, byid: dict) -> bool:
    """`a` runs only after `b` (directly or along a chain of `after` triggers)."""
    seen = 0
    while a.get("trigger", {}).get("on") == "after" and seen < 8:
        nxt = byid.get(a["trigger"].get("event"))
        if nxt is None:
            return False
        if nxt is b:
            return True
        a, seen = nxt, seen + 1
    return False


def check(docs: dict, graphs: dict, res: Result | None = None) -> list[tuple[str, str, str]]:
    from .traffic import Joined
    out = [("A3",) + x for x in check_tokens(docs, graphs, Joined(graphs))]
    out += [("A4",) + x for x in check_months(docs)]
    out += [("A5/A6",) + x for x in check_events(docs)]
    if res is not None:
        out += [("A1",) + x for x in check_daytime(res.regions)]
        out += [("A2",) + x for x in check_windows(res.windows)]
    return out


# -- the report ---------------------------------------------------------------------------------

def table(res: Result, before: Result | None = None) -> str:
    def avg(cell):
        return (cell["people"] / cell["n"], cell["animals"] / cell["n"], cell["birds"] / cell["n"])

    lines = ["# How alive the world is (data)", "",
             "Expected actors out of doors per region and hour block, averaged over the block's "
             "hours; people / animals / birds; year mean, with the leanest month's people in "
             "brackets. Tokens: travellers and ships on the region's lanes (instances with their "
             "groups), year mean.", ""]
    head = "| Region | kind | " + " | ".join(BLOCKS) + " | tokens |"
    lines += [head, "|" + "---|" * (len(BLOCKS) + 3)]
    for rid in sorted(res.regions, key=lambda r: (P.REGIONS.get(r, ("z",))[0], r)):
        row = [rid, P.REGIONS.get(rid, ("?",))[0]]
        for b in BLOCKS:
            cells = res.regions[rid].get(b, {})
            if not cells:
                row.append("-")
                continue
            ms = [avg(c) for c in cells.values()]
            p = sum(x[0] for x in ms) / len(ms)
            a = sum(x[1] for x in ms) / len(ms)
            bi = sum(x[2] for x in ms) / len(ms)
            lean = min(x[0] for x in ms)
            txt = f"{p:.0f} / {a:.0f} / {bi:.0f} ({lean:.0f})"
            if before and rid in before.regions and b in before.regions[rid]:
                bm = [avg(c) for c in before.regions[rid][b].values()]
                txt += f" ← {sum(x[0] for x in bm) / len(bm):.0f}"
            row.append(txt)
        tok = res.tokens.get(rid, {})
        row.append(f"{sum(tok.values()) / max(1, len(tok)):.0f}")
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "Share of the map where a 1080p screen at 1x expects fewer than "
              f"{EMPTY} actors or token travellers (all tiles / land / sea):", "",
              "| When | now | " + ("before |" if before else ""),
              "|---|---|" + ("---|" if before else "")]

    def fmt(v):
        return " / ".join(f"{x:.1%}" for x in v)
    for k, v in res.empty.items():
        if k.split()[1] not in ("02:00", "06:00", "10:00", "13:00", "16:00", "19:00", "22:00"):
            continue
        lines.append(f"| {k} | {fmt(v)} |" + (f" {fmt(before.empty[k])} |" if before and k in
                                                before.empty else ""))
    lines += ["", "Worst active area (chunks touching a 1440p view grown by the margin):", ""]
    for k, w in res.windows.items():
        lines.append(f"- {k} ({w['chunks']} x {w['chunks']} chunks): all data {w['all'][0]:.0f} "
                     f"at {w['all'][2]}; lanes' own data (no city) {w['lanes'][0]:.0f} at "
                     f"{w['lanes'][2]}")
    return "\n".join(lines) + "\n"


def run(b, before_dir: Path | None = None, hours=None, months=None) -> bool:
    world = b.composed()
    docs = load_docs(b.root)
    res = measure(world, b.graphs, b.root, docs, hours, months)
    before = None
    if before_dir is not None:
        before = measure(world, b.graphs, b.root, load_docs(b.root, before_dir), hours, months)
    probs = check(docs, b.graphs, res)
    out = b.reports / "alive"
    out.mkdir(parents=True, exist_ok=True)
    text = table(res, before)
    text += "\n## Checks\n\n" + ("\n".join(f"- {c} {lv}: {w}: {m}" for c, lv, w, m in probs)
                                 or "none") + "\n"
    (out / "alive.md").write_text(text)
    (out / "alive.json").write_text(json.dumps(
        {"regions": res.regions, "tokens": res.tokens, "empty": res.empty,
         "windows": {k: {"all": [v["all"][0], v["all"][2]], "lanes": [v["lanes"][0], v["lanes"][2]]}
                     for k, v in res.windows.items()},
         "routes": res.routes, **({"before": {"regions": before.regions, "empty": before.empty,
                                              "tokens": before.tokens}} if before else {})},
        indent=0))
    errs = [p for p in probs if p[1] == "error"]
    print(f"alive: {len(errs)} error(s), {len(probs) - len(errs)} warning(s) -> {out / 'alive.md'}")
    for c, lv, w, m in errs[:20]:
        print(f"   {c} {lv}: {w}: {m}")
    return not errs
