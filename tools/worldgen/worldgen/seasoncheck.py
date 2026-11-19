"""The seasons' checks (docs/design/seasons.md §6.5, and the world-data brief), run by
`build.sh --check` on the committed catalogs, region files and world seasonal data, and the
season needs file (`assets/world/season-needs.json`) the art and audio lanes work from.

  S1  climate named: every region file names a climate of the catalog, the one the plan gives it
  S2  no season pin: no region file pins a season (`season`, `theme.climate`)
  S3  climates complete: twelve entries in every month row, every class a placed item or terrain
      uses, values in range, `inherits` resolves, `sea` blocks only on sea climates, turn
      events from the calendar's vocabulary
  S4  states covered: every state a placed item or terrain can show is in its `season_states`
      or its `plain_state` (or `gone`)
  S5  moment: its festival is in the calendar on the moment's day
  S6  festivals: valid seasons, days and months; a festival's season and day agree with its
      months; events filtered by month or festival can happen
  S7  flood ranks: ranked tiles are flood ground within 12 tiles of their body, at most a level
      above it; every water body that floods has rank-1 tiles
  S8  snow: no snow line on the plains that never see snow (`mesopotamian`, `steppe`, `gulf`);
      lowland snow only where §2.4 has it; snow-capped backdrops exist
  S9  herds: both seasonal districts exist; the drove road joins them on the graph
  S10 tokens: `by_month` names a row the region's climate (or its coast) has, or twelve factors
  S11 dress: walkers given dress variants are kinds that change dress
  S12 audio and art: every seasonal bed, turn sound and art key exists or is on the needs list
  S13 captions: `era.caption` resolves for every season; no caption names a season or a month
      except `moment.caption`
  S14 the map: every tile's region resolves to a climate, and neighbouring climates are ones
      allowed to meet; a `touch` pair changes where the land does (a coast, a level, a seam)
  S15 the whole year: every region has its four seasons and twelve months of data
  S16 seasonal roles: a role that exists only in some months targets what is placed in its region
      with animations its kind has (the cities' L1-L4 run every month as well)
  S17 seasons kept: nothing appears out of its season (swallows in January, a harvest in winter)
  S18 snow ground: snow painted as terrain only where the region's climate keeps snow in every
      month at that level (the highest of its snow lines); elsewhere snow is the season's
  S19 snow sense: no lying snow on a lowland whose month is above freezing (+2 C mean), no
      summer snow below level 13, no palm under lying snow
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from plan import world_plan as P

from . import climates as C
from . import seasons as S
from .coords import COLS

LEVELS = set(C.WATER_LEVELS) | {"full"}
RANGES = {"wind": (0, 1), "fog": (0, 1), "dust": (0, 3), "storm": (0, 3), "showers": (0, 5),
          "clouds": (0, 5), "shimmer": (0, 1)}
NO_SNOW = {"mesopotamian", "steppe", "gulf"}
LOWLAND = {"med_green", "med_dry", "fars"}
SEA_REGIONS = {"tyrrhenian", "adriatic", "ionian_sea", "aegean", "saronic", "persian_gulf",
               "seam_ionian"}
WORDS = [w for w in (*C.SEASONS, *C.MONTH_NAMES)]


class Report:
    def __init__(self):
        self.items: list[tuple[str, str, str, str]] = []

    def bad(self, code, where, msg, level="error"):
        self.items.append((code, level, where, msg))

    @property
    def errors(self):
        return [x for x in self.items if x[1] == "error"]

    def lines(self) -> list[str]:
        errs = self.errors
        warns = [x for x in self.items if x[1] != "error"]
        return [f"{len(errs)} error(s), {len(warns)} warning(s)"] + \
            [f"{n:3}. {c} {lv}: {w}: {m}" for n, (c, lv, w, m) in enumerate(errs + warns, 1)]


# -- the catalogs --------------------------------------------------------------------------------

def check_climates(raw: dict, used: dict[str, set[str]], rep: Report) -> dict[str, dict]:
    """S3. `used`: climate -> classes placed in its regions."""
    turns = set(C.TURNS)
    out = {}
    for cid, c in raw.items():
        w = f"climate {cid}"
        seen, p = {cid}, c.get("inherits")
        while p:
            if p not in raw:
                rep.bad("S3", w, f"inherits {p!r}, which is not a climate")
                break
            if p in seen:
                rep.bad("S3", w, f"inherits round in a circle ({p})")
                break
            seen.add(p)
            p = raw[p].get("inherits")
        r = S.resolve(raw, cid)
        out[cid] = r
        for cls in sorted(used.get(cid, set()) | set(C.CLASSES)):
            row = r.get("classes", {}).get(cls)
            if cls in used.get(cid, set()) and row is None:
                rep.bad("S3", w, f"has no row for class {cls!r}, which its regions use")
                continue
            if row is not None and (len(row) != 12 or any(s not in C.STATES for s in row)):
                rep.bad("S3", w, f"class {cls!r} needs twelve states from {C.STATES}")
        for cls, row in r.get("set_classes", {}).items():
            if len(row) != 12 or any(s not in C.STATES for s in row):
                rep.bad("S3", w, f"set class {cls!r} needs twelve states")

        def twelve(path, row, lo=None, hi=None, allow_none=False):
            if not isinstance(row, list) or len(row) != 12:
                rep.bad("S3", w, f"{path} needs twelve entries (March first)")
                return
            for v in row:
                if v is None and allow_none:
                    continue
                if lo is not None and not (isinstance(v, (int, float)) and lo <= v <= hi):
                    rep.bad("S3", w, f"{path}: {v!r} is not in {lo}..{hi}")
                    return
        twelve("temp", r.get("temp"), -30, 50)
        sn = r.get("snow", {})
        twelve("snow.line", sn.get("line"), 0, 15, allow_none=True)
        if sn.get("perma") is not None and not 0 <= sn["perma"] <= 15:
            rep.bad("S3", w, "snow.perma must be a level 0..15")
        for k in ("settle", "melt"):
            if not 0 <= sn.get(k, 0) <= 1:
                rep.bad("S3", w, f"snow.{k} must be 0..1")
        for k in ("cold", "hot"):
            twelve(f"dress.{k}", r.get("dress", {}).get(k), 0, 1)
        for k, v in r.get("travel", {}).items():
            if k == "hours":
                continue
            if isinstance(v, list):
                twelve(f"travel.{k}", v, 0, 3)
            elif not 0 <= v <= 3:
                rep.bad("S3", w, f"travel.{k} must be 0..3")
        for k, v in r.get("water", {}).items():
            if k in ("ice", "colour"):
                continue
            if k.endswith("_rank"):
                twelve(f"water.{k}", v, 0, 3)
            elif not isinstance(v, list) or len(v) != 12 or any(x not in LEVELS for x in v):
                rep.bad("S3", w, f"water.{k} needs twelve levels from {sorted(LEVELS)}")
        for k, v in r.get("water", {}).get("colour", {}).items():
            if k not in LEVELS or len(v) != 3 or not all(0.5 <= x <= 1.5 for x in v):
                rep.bad("S3", w, f"water.colour.{k} must be a level and three factors 0.5..1.5")
        for s in C.SEASONS:
            g = r.get("grade", {}).get(s)
            if g is None or len(g) != 3 or not all(0.5 <= x <= 1.5 for x in g):
                rep.bad("S3", w, f"grade.{s} needs three factors 0.5..1.5")
            wx = r.get("weather", {}).get(s)
            if wx is None:
                rep.bad("S3", w, f"weather.{s} is missing")
                continue
            for k, (lo, hi) in RANGES.items():
                if k in wx and not (isinstance(wx[k], (int, float)) and lo <= wx[k] <= hi):
                    rep.bad("S3", w, f"weather.{s}.{k} must be {lo}..{hi}")
            t = r.get("turn_events", {}).get(s)
            if t not in turns:
                rep.bad("S3", w, f"turn event of {s} {t!r} is not in the calendar's turns")
        for m, t in r.get("month_turns", {}).items():
            if m not in C.MONTHS or t not in turns:
                rep.bad("S3", w, f"month turn {m}: {t!r} is not a month and a calendar turn")
        for k, ms in [("frost", r.get("frost", []))] + \
                [(f"work.{k}", v) for k, v in r.get("work", {}).items() if k != "building"] + \
                [(f"fauna.{k}", v) for k, v in r.get("fauna", {}).items()]:
            if any(m not in C.MONTHS for m in ms):
                rep.bad("S3", w, f"{k} names a month that is not one of {C.MONTHS}")
        if "sea" in c:
            for k in ("state", "sailing"):
                twelve(f"sea.{k}", c["sea"].get(k), 0, 3)
        coast = r.get("coast")
        if coast and "sea" not in raw.get(coast, {}):
            rep.bad("S3", w, f"coast {coast!r} is not a sea climate")
    sea_used = {C.REGION_CLIMATE[r] for r in SEA_REGIONS}
    for cid, c in raw.items():
        if "sea" in c and cid not in sea_used:
            rep.bad("S3", f"climate {cid}", "has a sea block but no sea region uses it")
    return out


def check_states(root: Path, world, clims: dict, rep: Report, docs: dict | None = None) -> None:
    """S4 on the set catalogs as committed (or the given set catalog documents)."""
    items_where, terr_where = S.placements(world)
    for set_ in ("world", "rome", "athens", "parsa"):
        doc = (docs or {}).get(set_) or \
            json.loads((root / f"assets/sets/{set_}/catalog.json").read_text())
        for sect, where in (("items", items_where), ("terrain", terr_where)):
            for e in doc.get(sect, []):
                states_problems(set_, e, where.get(e["id"], set()), clims, rep)


def states_problems(set_: str, e: dict, where: set[str], clims: dict, rep: Report) -> None:
    if "season_class" not in e:
        if e["id"] in C.SEASON_ITEMS.get(set_, {}) or e["id"] in C.SEASON_TERRAIN.get(set_, {}):
            rep.bad("S4", f"{set_} {e['id']}", "changes with the seasons but its catalog entry has "
                    "no season_class (run build.sh --seasons)")
        return
    if e["season_class"] not in C.CLASSES:
        rep.bad("S4", f"{set_} {e['id']}", f"season_class {e['season_class']!r} is not a class")
        return
    have = set(e.get("season_states", [])) | {e.get("plain_state"), "gone"}
    for cid in sorted(where):
        miss = S.needed_states(clims[cid], e) - have
        if miss:
            rep.bad("S4", f"{set_} {e['id']}", f"shows {sorted(miss)} in {cid} but its "
                    "season_states do not list them")


# -- region files --------------------------------------------------------------------------------

def _days_with(doc, f) -> list[int]:
    from .citylife import festival_on
    return [d for d in range(12) if festival_on(f, d)]


def check_region(doc: dict, clims: dict, raw: dict, files: set[str], needs_audio: set[str],
                 districts: set[str], graphs: dict, placed: dict, kinds: dict, rep: Report) -> None:
    rid = doc.get("id")
    w = rid
    cid = doc.get("climate")
    if cid is None:
        rep.bad("S1", w, "names no climate")
        return
    if cid not in clims:
        rep.bad("S1", w, f"climate {cid!r} is not in the catalog")
        return
    if rid in C.REGION_CLIMATE and C.REGION_CLIMATE[rid] != cid:
        rep.bad("S1", w, f"names {cid!r}; the plan gives it {C.REGION_CLIMATE[rid]!r}")
    if "season" in doc:
        rep.bad("S2", w, f"pins the season ({doc['season']!r}): the world calendar turns everywhere")
    if "climate" in doc.get("theme", {}):
        rep.bad("S2", w, "keeps the old theme.climate beside its climate")
    clim = clims[cid]
    fests = {f["id"]: f for f in doc.get("festivals", [])}
    # S5 moment
    m = doc.get("moment")
    if m:
        f = fests.get(m.get("festival"))
        day = S.day_of(m.get("season", "spring"), m.get("day", 1)) if m.get("season") in C.SEASONS else None
        if f is None:
            rep.bad("S5", w, f"moment festival {m.get('festival')!r} is not in the calendar")
        elif day is None or day not in _days_with(doc, f):
            rep.bad("S5", w, f"moment {m.get('season')} day {m.get('day')} is not a day of "
                    f"{m.get('festival')!r}")
        if m.get("calendar_day") not in (None, day):
            rep.bad("S5", w, "moment.calendar_day does not match its season and day")
    # S6 festivals
    for fid, f in fests.items():
        if "season" in f and f["season"] not in C.SEASONS:
            rep.bad("S6", w, f"festival {fid}: season {f['season']!r}")
        if "day" in f and f["day"] not in (1, 2, 3):
            rep.bad("S6", w, f"festival {fid}: day {f['day']!r} (a season has three)")
        if any(x not in C.MONTHS for x in f.get("months", [])):
            rep.bad("S6", w, f"festival {fid}: months must be from {C.MONTHS}")
        if "months" in f and "season" in f:
            want = {S.month_of(d) for d in range(12)
                    if S.season_of(d) == f["season"] and f.get("day") in (None, S.season_day(d))}
            if want != set(f["months"]):
                rep.bad("S6", w, f"festival {fid}: its season and day ({sorted(want)}) disagree "
                        f"with its months {f['months']}")
        if not _days_with(doc, f):
            rep.bad("S6", w, f"festival {fid} falls on no day of the year")
    from .citylife import event_on_day
    for e in doc.get("events", []):
        t = e.get("trigger", {})
        if any(x not in C.MONTHS for x in t.get("months", [])):
            rep.bad("S6", w, f"event {e['id']}: months must be from {C.MONTHS}")
        if t.get("on") in ("window", "calendar", "season_turn") and \
                not any(event_on_day(doc, e, d) for d in range(12)):
            rep.bad("S6", w, f"event {e['id']} can happen on no day of the year")
        for f in e.get("pending_sound", []):
            if f not in files and f not in needs_audio:
                rep.bad("S12", w, f"event {e['id']}: {f} is neither recorded nor on the needs list")
    # S9 herds
    for g in doc.get("groups", []):
        sea = g.get("seasonal")
        if not sea:
            continue
        for k in ("summer", "winter"):
            if sea.get(k) not in districts:
                rep.bad("S9", w, f"group {g['id']}: {k} pasture {sea.get(k)!r} is no district")
        rt = sea.get("route", {})
        if not _joined(graphs, rt.get("start", ""), rt.get("end", "")):
            rep.bad("S9", w, f"group {g['id']}: the drove road {rt} does not join its pastures")
        if any(x not in C.MONTHS for x in sea.get("move", [])):
            rep.bad("S9", w, f"group {g['id']}: move months")
    # S10 tokens
    for tk in doc.get("lanes_tokens", []):
        bm = tk.get("by_month")
        if bm is None:
            continue
        if isinstance(bm, str):
            if S.lookup_row(clim, raw, bm) is None:
                rep.bad("S10", w, f"token {tk.get('actor')}: {cid} has no {bm!r} row")
        elif len(bm) != 12 or not all(isinstance(v, (int, float)) and 0 <= v <= 3 for v in bm):
            rep.bad("S10", w, f"token {tk.get('actor')}: by_month needs twelve factors 0..3")
    # S11 dress
    roles = {r["id"]: r.get("actor") for r in doc.get("roles", [])}
    for d in doc.get("districts", []):
        for p in d.get("populations", []):
            v = p.get("variants")
            if not v:
                continue
            kind = roles.get(p.get("role", ""), p.get("actor"))
            if kind not in C.DRESS:
                rep.bad("S11", w, f"district {d['id']}: {kind} wears no seasonal dress")
            for k, row in v.items():
                if k not in ("cold", "hot") or not (row == "climate" or
                                                    (isinstance(row, list) and len(row) == 12)):
                    rep.bad("S11", w, f"district {d['id']}: variants.{k} must be 'climate' or twelve")
    # S12 seasonal beds
    th = doc.get("theme", {})
    for s, e in th.get("seasons", {}).items():
        for b in e.get("ambience", {}).get("beds", []):
            if b["file"] not in files and b["file"] not in needs_audio:
                rep.bad("S12", w, f"theme.seasons.{s}: bed {b['file']} is neither recorded nor "
                        "on the needs list")
    # S13 captions
    era = doc.get("era")
    if isinstance(era, dict):
        if "{year}" not in era.get("caption", ""):
            rep.bad("S13", w, "era.caption has no {year}")
        if set(era.get("year", {})) != set(C.SEASONS):
            rep.bad("S13", w, "era.year needs a year for each of the four seasons")
    elif era is not None:
        rep.bad("S13", w, "era must be an object (edge, caption, year)")
    for where, text in (("caption", doc.get("caption", "")),
                        ("era.caption", (era or {}).get("caption", "") if isinstance(era, dict) else "")):
        for word in WORDS:
            if word.lower() in text.lower().replace("{year}", "").split(" ") or \
                    f" {word.lower()}," in f" {text.lower()}":
                rep.bad("S13", w, f"{where} names {word!r}: only moment.caption may name a season")
    sn = th.get("snow")
    if sn is not None:
        line = sn.get("line", [])
        if len(line) != 12 or any(v is not None and not (isinstance(v, int) and 0 <= v <= 15)
                                  for v in line):
            rep.bad("S8", w, "theme.snow.line needs twelve levels (or nulls)")
        if cid in NO_SNOW and any(v is not None for v in line):
            rep.bad("S8", w, f"theme.snow puts snow on {cid} ground")
        bad_d = [d for d in sn.get("districts", []) if f"{rid}/{d}" not in districts]
        if bad_d:
            rep.bad("S8", w, f"theme.snow names districts {bad_d} the region does not have")
    # S15 the whole year
    for s in C.SEASONS:
        if s not in th.get("weather", {}):
            rep.bad("S15", w, f"theme.weather has no {s}")
        e = th.get("seasons", {}).get(s)
        if not e or "grade" not in e or "ground" not in e:
            rep.bad("S15", w, f"theme.seasons.{s} needs its grade and ground")
    for b in doc.get("water", []):
        if len(b.get("level", [])) != 12 or any(x not in C.WATER_LEVELS for x in b["level"]):
            rep.bad("S15", w, f"water {b.get('body')}: level needs twelve months")
        if "rank" in b and len(b["rank"]) != 12:
            rep.bad("S15", w, f"water {b.get('body')}: rank needs twelve months")
    # S16 seasonal roles (the stretches and towns: the cities' life checks cover theirs)
    if P.REGIONS.get(rid, ("",))[0] in ("stretch", "seam", "town"):
        for r in doc.get("roles", []):
            anims = kinds.get(r.get("actor"))
            if anims is None:
                rep.bad("S16", w, f"role {r['id']}: actor kind {r.get('actor')!r} is in no catalog")
                continue
            for rt in r.get("routines", {}).values():
                for st in rt.get("steps", []):
                    if st.get("anim") and st["anim"] not in anims:
                        rep.bad("S16", w, f"role {r['id']}: animation {st['anim']!r} not of {r['actor']}")
                    tgt = st.get("go", {})
                    if "item" in tgt and rid not in placed.get(tgt["item"], set()):
                        rep.bad("S16", w, f"role {r['id']}: {tgt['item']} is not placed in the region")
    # S17 seasons kept
    _kept(doc, clim, rep)


def _joined(graphs, a: str, b: str) -> bool:
    if ":" not in a or ":" not in b:
        return False
    la, na = a.split(":", 1)
    lb, nb = b.split(":", 1)
    if la != lb or la not in graphs:
        return False
    g = graphs[la]
    adj: dict[str, list[str]] = {}
    for e in g.edges:
        adj.setdefault(e.a, []).append(e.b)
        adj.setdefault(e.b, []).append(e.a)
    seen, todo = {na}, [na]
    while todo:
        n = todo.pop()
        if n == nb:
            return True
        for m in adj.get(n, []):
            if m not in seen:
                seen.add(m)
                todo.append(m)
    return False


# What may only appear in its months: (actor kinds, event id words, the climate's months).
def _kept(doc: dict, clim: dict, rep: Report) -> None:
    fa, wk = clim.get("fauna", {}), clim.get("work", {})
    swallow = set(fa.get("swallows", []) + fa.get("swifts", []))
    rules = [
        ({"rome.swallow", "world.swift"}, ("swallow", "swift"), swallow, "swallows and swifts"),
        ({"world.stork"}, ("stork",), set(fa.get("storks", [])), "storks"),
        ({"world.crane"}, ("cranes",), set(fa.get("cranes_pass", []) + fa.get("cranes_winter", [])),
         "cranes"),
        (set(), ("starling",), set(fa.get("starlings", [])), "starlings"),
        (set(), ("cicada",), set(fa.get("cicadas", [])), "cicadas"),
        (set(), ("vintage", "grape"), set(wk.get("vintage", [])), "the vintage"),
        (set(), ("olive_harvest", "olive_pick"), set(wk.get("olive", [])), "the olive harvest"),
        (set(), ("reap", "harvest_offering"), set(wk.get("harvest", [])), "the grain harvest"),
        (set(), ("thresh",), set(wk.get("threshing", [])), "threshing"),
        (set(), ("plough",), set(wk.get("ploughing", [])), "ploughing"),
        (set(), ("shear",), set(wk.get("shearing", [])), "shearing"),
        (set(), ("date_harvest",), set(wk.get("dates_harvest", [])), "the date harvest"),
    ]
    snowy = {C.MONTHS[i] for i, v in enumerate(clim.get("snow", {}).get("line", [None] * 12))
             if v is not None} | set(clim.get("snow", {}).get("lowland", {}).get("months", []))

    def months_of(f: dict, base=None) -> set[str]:
        ms = set(f.get("months", C.MONTHS))
        if "season" in f:
            ss = f["season"] if isinstance(f["season"], list) else [f["season"]]
            ms &= {m for s in ss for m in S.season_months(s)}
        return ms

    fest_months = {f["id"]: {S.month_of(d) for d in _days_with(doc, f)} for f in doc.get("festivals", [])}
    roles = {r["id"]: r.get("actor") for r in doc.get("roles", [])}
    w = doc["id"]
    for d in doc.get("districts", []):
        for p in d.get("populations", []):
            kind = roles.get(p.get("role", ""), p.get("actor"))
            ident = p.get("role") or ""
            ms = months_of(p.get("when", {}))
            for kinds, words, allowed, what in rules:
                if (kind in kinds or any(x in ident for x in words)) and allowed is not None \
                        and ms - allowed:
                    rep.bad("S17", w, f"district {d['id']}: {ident or kind} out in "
                            f"{sorted(ms - allowed, key=C.MONTHS.index)}, outside the months of {what}")
    for e in doc.get("events", []):
        if e.get("trigger", {}).get("on") == "season_turn":
            continue
        t = e.get("trigger", {})
        ms = months_of(t)
        if t.get("festival"):
            ms &= fest_months.get(t["festival"], set(C.MONTHS))
        kinds_cast = {c.get("actor") for c in e.get("cast", [])}
        for kinds, words, allowed, what in rules:
            if (kinds & kinds_cast or any(x in e["id"] for x in words)) and ms - allowed:
                rep.bad("S17", w, f"event {e['id']} can happen in "
                        f"{sorted(ms - allowed, key=C.MONTHS.index)}, outside the months of {what}")
        if any(x in e["id"] for x in ("snow", "flurry", "dusting")) and ms - snowy:
            rep.bad("S17", w, f"event {e['id']} brings snow in {sorted(ms - snowy)}, where none falls")


# -- the map -------------------------------------------------------------------------------------

def check_map(world, rep: Report) -> dict:
    """S14: climates on every tile and where they meet. Returns the boundary statistics."""
    reg, names = S.region_grid(world)
    missing = [n for n in names if n not in C.REGION_CLIMATE]
    for n in missing:
        rep.bad("S14", f"region {n}", "has no climate")
    if (reg < 0).any():
        rep.bad("S14", "map", f"{int((reg < 0).sum())} tiles belong to no region")
    cids = sorted(set(C.REGION_CLIMATE.values()))
    cmap = np.array([cids.index(C.REGION_CLIMATE.get(n, "med_green")) for n in names] + [-1])
    cl = cmap[np.where(reg < 0, len(names), reg)]
    lv = (world.L & 0x0F).astype(np.int16)
    tid = {t: i for i, t in enumerate(world.terrains)}
    water_ids = [tid[t] for t in ("world.sea", "world.shallows", "world.river", "rome.river_tiber",
                                  "parsa.water_channel", "water") if t in tid]
    wet = np.isin(world.T, water_ids)
    seam = np.isin(reg, [names.index(n) for n in names if P.REGIONS.get(n, ("",))[0] == "seam"])
    stats: dict[tuple, list[int]] = {}
    for a, b, la, lb, wa, wb, sa, sb in (
            (cl[:, 1:], cl[:, :-1], lv[:, 1:], lv[:, :-1], wet[:, 1:], wet[:, :-1], seam[:, 1:], seam[:, :-1]),
            (cl[1:, :], cl[:-1, :], lv[1:, :], lv[:-1, :], wet[1:, :], wet[:-1, :], seam[1:, :], seam[:-1, :])):
        m = (a != b) & (a >= 0) & (b >= 0)
        # A coast, a level, a seam; or open water (seas meet their coasts' climates at sea).
        land_change = (np.abs(la - lb) >= 1) | wa | wb | sa | sb
        for x, y, ch in zip(a[m].tolist(), b[m].tolist(), land_change[m].tolist()):
            k = tuple(sorted((cids[x], cids[y])))
            s = stats.setdefault(k, [0, 0])
            s[0] += 1
            s[1] += int(ch)
    for (x, y), (n, ch) in sorted(stats.items()):
        kind = C.touch(x, y)
        if kind is None:
            rep.bad("S14", f"climates {x} / {y}", f"meet on {n} tile edges but may not touch")
        elif kind == "touch" and n >= 40 and ch / n < 0.25:
            rep.bad("S14", f"climates {x} / {y}", f"meet on {n} edges, only {ch / n:.0%} of them "
                    "at a coast, a level or a seam (a `touch` pair changes where the land does)",
                    "warning")
    return {f"{a}/{b}": {"edges": n, "at_land_change": round(ch / n, 2), "kind": C.touch(a, b)}
            for (a, b), (n, ch) in sorted(stats.items())}


def check_flood(root: Path, world, bodies: list[dict], clims: dict, regions: dict, rep: Report) -> None:
    """S7 on the committed seasons.json against the world and the region files."""
    f = root / "assets/world/seasons.json"
    if not f.exists():
        rep.bad("S7", "world", "assets/world/seasons.json is missing (build.sh --seasons)")
        return
    doc = json.loads(f.read_text())
    tid = {t: i for i, t in enumerate(world.terrains)}
    ground = {tid[t] for t in S.FLOOD_GROUND if t in tid}
    lv = world.L & 0x0F
    from .coords import to_plan
    by = {(b["region"], b["name"]): b for b in bodies}
    ranked = {(fb["region"], fb["body"]): fb for fb in doc.get("flood", [])}
    for key, fb in ranked.items():
        b = by.get(key)
        if b is None:
            rep.bad("S7", f"flood {key}", "names a body the world does not have")
            continue
        wl = {(c, r): int(lv[r, c]) for c, r in b["tiles"]}
        for x, y, k in fb["tiles"]:
            c, r = to_plan(x, y)
            if int(world.T[r, c]) not in ground:
                rep.bad("S7", f"flood {key}", f"ranked tile ({x}, {y}) is {world.terrains[world.T[r, c]]}")
                break
            if k not in (1, 2, 3):
                rep.bad("S7", f"flood {key}", f"ranked tile ({x}, {y}) has rank {k}")
                break
            near = [wl[(a, bb)] for a in range(c - 12, c + 13) for bb in range(r - 12, r + 13)
                    if abs(a - c) + abs(bb - r) <= 12 and (a, bb) in wl]
            if not near or int(lv[r, c]) > max(near) + 1:
                rep.bad("S7", f"flood {key}", f"ranked tile ({x}, {y}) is over 12 tiles from its "
                        "water or more than a level above it")
                break
    for rid, rdoc in regions.items():
        for wb in rdoc.get("water", []):
            if "flood" in wb.get("level", []):
                fb = ranked.get((rid, wb["body"]))
                if fb is None or not any(t[2] == 1 for t in fb["tiles"]):
                    rep.bad("S7", rid, f"water {wb['body']} floods but has no rank-1 tiles")


def check_snow(raw: dict, clims: dict, root: Path, rep: Report) -> None:
    """S8."""
    for cid in NO_SNOW:
        if any(v is not None for v in clims[cid].get("snow", {}).get("line", [])):
            rep.bad("S8", f"climate {cid}", "has a snow line, but snow never falls there")
    for cid, c in clims.items():
        # A sea climate's islands keep the land climate they inherit (seasons.md §2.1).
        own = c if cid not in raw or "snow" in raw[cid] else {}
        if own.get("snow", {}).get("lowland") and cid not in LOWLAND:
            rep.bad("S8", f"climate {cid}", "has lowland snow, which §2.4 gives only "
                    f"{sorted(LOWLAND)}")
    wc = json.loads((root / "assets/sets/world/catalog.json").read_text())
    have = set(wc.get("art", {}).get("backdrops", []) + wc.get("art", {}).get("backdrops_nice", []))
    for bd in wc.get("art", {}).get("backdrop_snow", []):
        if bd not in have:
            rep.bad("S8", f"backdrop {bd}", "gets a snow cap but is not a backdrop of the world set")


def check_snow_ground(world, clims: dict, rep: Report) -> None:
    """S18: snow painted as ground lies only where its region's climate keeps snow in every
    month (at or above the highest of its twelve snow lines); everywhere else snow is a season
    the climate's line brings, never a terrain."""
    snow_t = [i for i, t in enumerate(world.terrains) if S.GROUND_OF.get(t) == "snow"]
    if not snow_t:
        return
    reg, names = S.region_grid(world)
    snow = np.isin(world.T, snow_t)
    lv = world.L & 0x0F
    for i, rid in enumerate(names):
        m = snow & (reg == i)
        if not m.any():
            continue
        cid = C.REGION_CLIMATE.get(rid, "")
        lasting = S.lasting_snow(clims.get(cid, {}))
        bad = m if lasting is None else m & (lv < lasting)
        if bad.any():
            r, c = (int(v[0]) for v in np.nonzero(bad))
            where = "it never keeps snow all year" if lasting is None else \
                f"it keeps snow all year only from level {lasting}"
            rep.bad("S18", rid, f"{int(bad.sum())} tile(s) of snow ground where its climate {cid} "
                    f"has none in some month ({where}); first at grid ({r}, {COLS - 1 - c}) "
                    f"level {int(lv[r, c])}")


PALMS = {"world.t_palm", "parsa.t_date"}
LYING_MAX_T = 2.0       # deg C: the mean of a month whose lowland holds lying snow, at most
SUMMER = ("jun", "jul", "aug")
SUMMER_SNOW_MIN = 13    # summer snow only on the highest ground


def snow_rows(world, clims: dict) -> list[dict]:
    """Per region with land: its climate, base level, highest ground, and per month whether snow
    lies on its lowland (the plan's base level), on its highest ground, and may fall on the
    lowland on some days (`lowland` months)."""
    reg, names = S.region_grid(world)
    lv = (world.L & 0x0F)
    sea = np.isin(world.T, [i for i, t in enumerate(world.terrains)
                            if t in ("world.sea", "world.shallows")]) | (world.T == 0xFFFF)
    out = []
    for i, rid in enumerate(names):
        cid = C.REGION_CLIMATE.get(rid, "")
        m = (reg == i) & ~sea
        if rid not in P.REGIONS or not m.any() or cid not in clims:
            continue
        sn = clims[cid].get("snow", {})
        line = sn.get("line") or [None] * 12
        low = set(sn.get("lowland", {}).get("months", []))
        base, top = P.REGIONS[rid][4], int(lv[m].max())
        out.append({"region": rid, "climate": cid, "base": base, "top": top,
                    "lowland": [v is not None and base >= v for v in line],
                    "heights": [v is not None and top >= v for v in line],
                    "dusting": [mo in low for mo in C.MONTHS], "line": line})
    return out


def snow_table(rows: list[dict]) -> str:
    head = "| Region | Climate | Base | Top | " + " | ".join(m.title() for m in C.MONTHS) + " |"
    lines = ["# Snow by region and month (`build.sh --seasons`)", "",
             "Each month: **L** snow lies on the lowland (the region's base level), **H** only on "
             "its highest ground, *d* a dusting some days, - none. Lines are the climate's "
             "lowest level of lying snow.", "", head,
             "|---|---|---|---|" + "---|" * 12]
    for r in rows:
        cells = []
        for k in range(12):
            cells.append("L" if r["lowland"][k] else "H" if r["heights"][k] else
                         "d" if r["dusting"][k] else "-")
        lines.append(f"| {r['region']} | {r['climate']} | {r['base']} | {r['top']} | " +
                     " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def check_snow_sense(world, clims: dict, rep: Report) -> None:
    """S19: no obvious contradiction in the snow rows: lying snow on a region's lowland in a
    month whose mean there is above LYING_MAX_T; summer snow below SUMMER_SNOW_MIN; a palm or
    date palm standing where snow lies in some month."""
    for r in snow_rows(world, clims):
        temp = clims[r["climate"]].get("temp") or [None] * 12
        for k, mo in enumerate(C.MONTHS):
            if r["lowland"][k] and temp[k] is not None and temp[k] > LYING_MAX_T:
                rep.bad("S19", r["region"], f"snow lies on its lowland (level {r['base']}) in "
                        f"{mo}, whose mean is {temp[k]} C")
            v = r["line"][k]
            if mo in SUMMER and v is not None and v < SUMMER_SNOW_MIN:
                rep.bad("S19", f"climate {r['climate']}", f"snow down to level {v} in {mo}")
    reg, names = S.region_grid(world)
    seen = set()
    from .compose import live_items
    for _, it in live_items(world):
        if it.id not in PALMS or not (0 <= it.r < reg.shape[0]):
            continue
        rid = names[reg[it.r, it.c]] if reg[it.r, it.c] >= 0 else None
        line = clims.get(C.REGION_CLIMATE.get(rid, ""), {}).get("snow", {}).get("line") or []
        lvl = world.level(it.c, it.r)
        bad = [C.MONTHS[k] for k, v in enumerate(line) if v is not None and lvl >= v]
        if bad and (rid, it.id) not in seen:
            seen.add((rid, it.id))
            rep.bad("S19", rid, f"{it.id} at grid ({it.r}, {COLS - 1 - it.c}) level {lvl} stands "
                    f"under lying snow in {bad}")


# -- the needs file ------------------------------------------------------------------------------

def atlas_keys(root: Path) -> set[str]:
    keys = set()
    for f in sorted((root / "assets/atlas").glob("*.json")) + [root / "assets/atlas.json"]:
        if f.name.endswith(".geom.json") or not f.exists():
            continue
        keys |= set(json.loads(f.read_text()).get("sprites", {}))
    return keys


def _has_look(keys: set[str], prefix: str, state: str) -> bool:
    return any(k.startswith(prefix) and k.endswith("@" + state) for k in keys)


def needs(root: Path, world, regions: dict, files: set[str]) -> list[dict]:
    """Every seasonal art variant and audio file the data refers to that does not exist yet:
    `id`, `set`, `kind`, `season` (or months), `where` (regions using it), `count`."""
    keys = atlas_keys(root)
    sk = {k.split("/f")[0] for k in keys}
    placed = S.placed_regions(world)
    items_where, terr_where = S.placements(world)
    clims = S.resolved(root)
    out: dict[tuple, dict] = {}

    def add(id_, set_, kind, season, where, count=1, note=None):
        k = (id_, kind, json.dumps(season))
        e = out.setdefault(k, {"id": id_, "set": set_, "kind": kind, "season": season,
                               "where": [], "count": 0})
        for w in where:
            if w not in e["where"]:
                e["where"].append(w)
        e["count"] += count
        if note:
            e["note"] = note

    from .compose import live_items
    counts: dict[str, int] = {}
    for _, it in live_items(world):
        counts[it.id] = counts.get(it.id, 0) + 1
    tcount = {t: int((world.T == i).sum()) for i, t in enumerate(world.terrains)}
    for set_ in ("world", "rome", "athens", "parsa"):
        doc = json.loads((root / f"assets/sets/{set_}/catalog.json").read_text())
        for sect, prefix in (("items", "item/{}/base/"), ("terrain", "terrain/{}/")):
            for e in doc.get(sect, []):
                for st in e.get("season_states", []):
                    if st == "gone" or _has_look(keys, prefix.format(e["id"]), st):
                        continue
                    where = sorted((placed if sect == "items" else {}).get(e["id"], set()))
                    clim = sorted((items_where if sect == "items" else terr_where).get(e["id"], set()))
                    months = sorted({C.MONTHS[i] for cid in clim for i, s in
                                     enumerate(S.item_states(clims[cid], e)) if s == st} |
                                    ({"dec", "jan", "feb"} if st == "snow" else set()),
                                    key=C.MONTHS.index)
                    add(e["id"], set_, f"{'plant' if sect == 'items' else 'ground'} state @{st}",
                        _season_span(months), where or clim,
                        counts.get(e["id"], 0) if sect == "items" else tcount.get(e["id"], 0))
        # Dress: cold and hot walkers (variant_tags in the set catalog, art on the rig).
        for a in doc.get("actors", []):
            want = C.DRESS.get(a["id"])
            if not want:
                continue
            tags = set(a.get("variant_tags", {}).values())
            users = sorted({rid for rid, rd in regions.items() if a["id"] in _kinds_of(rd)})
            for k in ("cold", "hot"):
                if want in (k, "both") and k not in tags:
                    add(a["id"], set_, f"walker dress {k}", "winter" if k == "cold" else "summer",
                        users, len(users))
    # Overlays, backdrop snow caps, seasonal fx and props the data names.
    wc = json.loads((root / "assets/sets/world/catalog.json").read_text())
    for ov in wc.get("art", {}).get("overlays", []):
        if not any(k.startswith(f"terrain/{ov}/") for k in keys):
            add(ov, "world", "overlay", "winter" if ov != "world.flood" else "spring",
                ["world"], 1)
    for bd in wc.get("art", {}).get("backdrop_snow", []):
        if not any(k.startswith(f"backdrop/{bd}/snow/") for k in keys):
            users = sorted(rid for rid, rd in regions.items()
                           if bd in json.dumps(rd.get("theme", {}).get("look", {}).get("backdrop", {})))
            add(bd, "world", "backdrop snow cap", "winter", users, len(users))
    for rid, rd in sorted(regions.items()):
        for e in rd.get("events", []):
            for st in e.get("steps", []):
                fx = st.get("emit", {}).get("fx") if isinstance(st.get("emit"), dict) else None
                if fx and fx.startswith("fx/") and fx not in sk and not any(k.startswith(fx + "/") for k in keys):
                    add(fx, fx.split("/")[1].split(".")[0] if "." in fx else "home", "fx",
                        _event_season(e), [rid])
            for f in e.get("pending_sound", []):
                add(f, f.split("/")[1] if f.count("/") > 1 else "world", "audio",
                    _event_season(e), [rid])
        for s, th in rd.get("theme", {}).get("seasons", {}).items():
            for b in th.get("ambience", {}).get("beds", []):
                if b["file"] not in files:
                    add(b["file"], b["file"].split("/")[1], "audio bed",
                        _season_span(b.get("months") or S.season_months(s)), [rid])
        for h in rd.get("harbours", []):
            for prop in h.get("props", []):
                if not any(k.startswith(f"item/{prop}/") for k in keys):
                    add(prop, prop.split(".")[0], "seasonal prop", "winter", [rid])
    for t, spec in C.TURNS.items():
        for k in ("fx",):
            fx = spec.get(k)
            if fx and not any(x.startswith(fx + "/") for x in keys):
                add(fx, "world", "fx", "turn", [t])
    for f in (C.TURNS[t].get(k) for t in C.TURNS for k in ("sfx", "ambience")):
        if f and f not in files and not f.startswith("sfx/season"):
            add(f, f.split("/")[1], "audio", "turn", [t for t in C.TURNS
                                                      if f in (C.TURNS[t].get("sfx"), C.TURNS[t].get("ambience"))])
    for e in out.values():
        e["where"].sort()
    return [out[k] for k in sorted(out, key=lambda k: (out[k]["set"], out[k]["kind"], out[k]["id"],
                                                      str(out[k]["season"])))]


def _kinds_of(rd: dict) -> set[str]:
    roles = {r["id"]: r.get("actor") for r in rd.get("roles", [])}
    out = set(roles.values())
    for d in rd.get("districts", []):
        for p in d.get("populations", []):
            out.add(roles.get(p.get("role", ""), p.get("actor")))
    return out


def _event_season(e: dict):
    t = e.get("trigger", {})
    if t.get("months"):
        return _season_span(t["months"])
    if t.get("season"):
        return t["season"] if isinstance(t["season"], str) else "/".join(t["season"])
    return "all year"


def _season_span(months) -> str | list:
    ms = sorted(set(months), key=C.MONTHS.index)
    for s in C.SEASONS:
        if set(ms) == set(S.season_months(s)):
            return s
    return ms if len(ms) < 12 else "all year"


def needs_text(items: list[dict]) -> str:
    by: dict[str, dict[str, int]] = {}
    for e in items:
        by.setdefault(e["set"], {})
        by[e["set"]][e["kind"]] = by[e["set"]].get(e["kind"], 0) + 1
    lines = ["{", ' "version": 1,',
             ' "note": "Seasonal art and audio the world data refers to that does not exist yet '
             '(seasons.md §4.3, §3.12). Written by tools/worldgen/build.sh --seasons; checked by '
             '--check (S12). count: placed instances, painted tiles or regions using it.",',
             f' "summary": {json.dumps(by, ensure_ascii=False, sort_keys=True)},', ' "needs": [']
    for i, e in enumerate(items):
        lines.append("  " + json.dumps(e, ensure_ascii=False) + ("," if i + 1 < len(items) else ""))
    lines += [" ]", "}"]
    return "\n".join(lines) + "\n"


# -- the whole check -----------------------------------------------------------------------------

def run(b, world) -> Report:
    from . import sound
    from .citylife import content_facts
    rep = Report()
    root = b.root
    raw = S.raw_climates(root)
    cat_doc = json.loads((root / "assets/catalog.json").read_text())
    if "climates" not in cat_doc or "calendar" not in cat_doc:
        rep.bad("S3", "catalog", "assets/catalog.json has no climates or calendar (build.sh --seasons)")
    items_where, terr_where = S.placements(world)
    used: dict[str, set[str]] = {}
    for set_ in ("world", "rome", "athens", "parsa"):
        for iid, spec in list(C.SEASON_ITEMS.get(set_, {}).items()) + list(C.SEASON_TERRAIN.get(set_, {}).items()):
            for cid in items_where.get(iid, set()) | terr_where.get(iid, set()):
                used.setdefault(cid, set()).add(spec["season_class"])
    clims = check_climates(raw, used, rep)
    check_states(root, world, clims, rep)
    check_snow(raw, clims, root, rep)
    check_snow_ground(world, clims, rep)
    check_snow_sense(world, clims, rep)
    stats = check_map(world, rep)
    regions = {f.stem: json.loads(f.read_text()) for f in sorted((root / "assets/regions").glob("*.json"))}
    files, _fam = sound.manifests(root)
    nf = root / "assets/world/season-needs.json"
    need_doc = json.loads(nf.read_text()) if nf.exists() else {"needs": []}
    needs_audio = {e["id"] for e in need_doc.get("needs", []) if e["kind"].startswith("audio")}
    districts = set(world.districts)
    placed = S.placed_regions(world)
    kinds, _g, _a = content_facts(root, ["world", "rome", "athens", "parsa"])
    for rid in sorted(set(C.REGION_CLIMATE) - {"corner"}):
        if rid not in regions:
            rep.bad("S15", rid, "has no region file, so no year")
    for rid, rd in regions.items():
        check_region(rd, clims, raw, files, needs_audio, districts, b.graphs, placed, kinds, rep)
    check_flood(root, world, S.water_bodies(world), clims, regions, rep)
    want = needs_text(needs(root, world, regions, files))
    if not nf.exists() or nf.read_text() != want:
        rep.bad("S12", "world", "assets/world/season-needs.json does not list what the data needs "
                "(build.sh --seasons rewrites it)")
    rep.stats = stats
    return rep
