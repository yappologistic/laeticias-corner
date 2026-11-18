"""Each region's year (docs/design/seasons.md §1, §2, §3, §6.2): what every region file gets so
the world turns through the seasons everywhere, and the helpers the cities' own seasonal modules
(`regions/<city>/seasons.py`) use.

`apply(doc, ...)` runs on every region document before its sound and look are wired (so the
seasonal roles and events it adds get their sounds); `finish(doc)` runs after. Together they
write:

- `climate` (seasons.md §2.1) and no `season` pin; `era` {`edge`, `caption`, `year`, `months`};
  a season-free `caption`; `moment` where the region has a famous day;
- `theme.weather` per season (the climate's defaults under the region's own) with `months`
  exceptions; `theme.seasons.<season>`: `grade`, `look`, `haze`, `ground` (the ground states the
  region really shows, with their months), `ambience` (seasonal beds that replace the year-round
  ones), `snow` (the snow line over the region's own heights);
- `water[]`: every river, stream, channel and pond with its level and flood rank by month;
- tokens by month (`by_month`: the climate's `sailing`, `grain`, `barge`, `caravan`, `road` or
  `courier` row); `harbours[]` laid up when the sea is closed;
- dress variants on every walker whose kind changes dress (`variants`);
- birds and herds by month (storks, cranes, swifts; flocks between summer and winter pastures
  along the drove roads, `groups[].seasonal`); seasonal farm work on the land between the
  cities, as roles that exist only in their months;
- the turns of the seasons as `season_turn` events, with a line per season in `strings`.
"""

from __future__ import annotations

import copy

import numpy as np

from plan import world_plan as P

from . import climates as C
from . import seasons as S
from .coords import to_grid, to_plan

# -- eras, captions and moments ----------------------------------------------------------------

YEARS = {
    "rome": {"spring": "AD 126", "summer": "AD 126", "autumn": "AD 126", "winter": "AD 126/127",
             "months": {"jan": "AD 127", "feb": "AD 127"}},
    "athens": {"spring": "432 BC", "summer": "432 BC", "autumn": "432/431 BC",
               "winter": "432/431 BC", "months": {}},
    "parsa": {"spring": "c. 470 BC", "summer": "c. 470 BC", "autumn": "c. 470/469 BC",
              "winter": "c. 470/469 BC", "months": {}},
}
ERA_NOTE = {"athens": "still at peace: the war begins in the spring of 431, which the calendar "
                      "never reaches, because spring returns to 432"}
# The famous day of each region that has one (seasons.md §1.3): season, season day, festival,
# and the caption shown while it runs.
MOMENTS = {
    "rome": ("spring", 2, "parilia", "Roma · the Parilia, 21 April AD 126"),
    "athens": ("summer", 2, "panathenaia", "Ἀθῆναι · the Panathenaia, summer 432 BC"),
    "parsa": ("spring", 2, "spring_audience", "Pārsa · the spring audience, c. 470 BC"),
    "ostia": ("spring", 1, "navigium_isidis", "Ostia · the ship of Isis, 5 March AD 126"),
    "alban_mount": ("spring", 3, "feriae_latinae", "Mons Albanus · the Latin Festival, AD 126"),
    "eleusis": ("autumn", 1, "mysteries", "Eleusis · the Mysteries, autumn 432 BC"),
    "olympia": ("summer", 3, "olympia", "Olympia · the 87th Olympic festival, 432 BC"),
    "sparta": ("summer", 3, "karneia", "Sparta · the Karneia, 432 BC"),
    "delphi": ("spring", 1, "pythia_returns", "Delphi · the god returns, spring 432 BC"),
    "babylon": ("winter", 2, "king_in_babylon", "Babylon · the king's winter, c. 470/469 BC"),
}
SEASON_WORDS = ("spring", "summer", "autumn", "winter", "April", "March", "May", "June", "July",
                "August", "September", "October", "November", "December", "January", "February")


def side_of(rid: str) -> str | None:
    from .places import side
    return side(rid)


def era(doc: dict, rid: str) -> None:
    s = side_of(rid)
    edge = doc.get("era")
    if isinstance(edge, dict):
        edge = edge.get("edge")
    if s is None:
        doc.pop("era", None)
        return
    name = doc.get("native") if doc.get("native") and P.REGIONS[rid][0] == "city" else doc.get("name")
    y = YEARS[s]
    out = {"edge": edge, "caption": f"{name or rid} · {{year}}",
           "year": {k: y[k] for k in C.SEASONS}}
    if y["months"]:
        out["months"] = dict(y["months"])
    if s in ERA_NOTE:
        out["note"] = ERA_NOTE[s]
    doc["era"] = out


def moment(doc: dict, rid: str) -> None:
    if rid not in MOMENTS:
        doc.pop("moment", None)
        return
    season, day, fest, caption = MOMENTS[rid]
    doc["moment"] = {"season": season, "day": day, "festival": fest, "caption": caption,
                     "calendar_day": S.day_of(season, day),
                     "month": S.month_of(S.day_of(season, day))}


# -- weather and themes ------------------------------------------------------------------------

def weather(doc: dict, clim: dict) -> None:
    th = doc.setdefault("theme", {})
    have = th.get("weather", {})
    out = {}
    for s in C.SEASONS:
        out[s] = {**clim.get("weather", {}).get(s, {}), **have.get(s, {})}
    months = {**clim.get("weather", {}).get("months", {}), **have.get("months", {})}
    if months:
        out["months"] = months
    th["weather"] = out


def _region_mask(world, rid: str) -> np.ndarray:
    ids = [i for i, n in enumerate(world.districts) if n.split("/", 1)[0] == rid]
    return np.isin(world.D, ids) if ids else np.zeros(world.D.shape, dtype=bool)


def _terrains(world, mask) -> set[str]:
    return {world.terrains[i] for i in np.unique(world.T[mask]).tolist()
            if 0 <= i < len(world.terrains)}


EARTH = {"world.road_earth", "rome.packed_earth", "athens.packed_earth", "parsa.packed_earth",
         "rome.mud_bank", "world.alluvium", "world.field", "athens.riverbed"}
WATER_T = {"world.sea", "world.shallows", "world.river", "rome.river_tiber", "parsa.water_channel",
           "water"}
PAVED = {"rome.basalt_paving", "rome.travertine_paving", "athens.marble_paving",
         "parsa.paving_stone", "parsa.paving_red", "world.road_royal", "athens.gravel",
         "parsa.gravel", "rome.brick_ground"}


def _months_in(ms, season) -> list[str]:
    return [m for m in S.season_months(season) if m in ms]


def ground(clim: dict, terr: set[str], levels: tuple[int, int], water: list[dict],
           season: str) -> dict:
    """The ground states a region shows in a season, each with its months (only those true of
    this region's ground: no mud without earth roads, no snow below the line)."""
    out: dict[str, list[str]] = {}
    wet = clim.get("wet_floor", {})
    if terr & EARTH and wet.get("months"):
        ms = _months_in(wet["months"], season)
        if ms:
            out["muddy"] = ms
    dust = clim.get("dust", {}).get("months", [])
    if terr & (EARTH | PAVED) and dust:
        ms = _months_in(dust, season)
        if ms:
            out["dusty"] = ms
    line = clim.get("snow", {}).get("line", [None] * 12)
    lo, hi = levels
    snowy = [m for m in S.season_months(season)
             if line[S.month_index(m)] is not None and hi >= line[S.month_index(m)]]
    if snowy:
        out["snow"] = snowy
    low = clim.get("snow", {}).get("lowland")
    if low and terr - WATER_T:
        ms = _months_in(low.get("months", []), season)
        if ms:
            out["snow_dusted" if low.get("settle", True) else "flurries"] = ms
    fr = _months_in(clim.get("frost", []), season)
    if fr:
        out["frost"] = fr
    for b in water:
        for i, lv in enumerate(b["level"]):
            m = C.MONTHS[i]
            if m not in S.season_months(season):
                continue
            key = {"flood": "flooded", "dry": "dry_beds", "low": "low_water"}.get(lv)
            if key and m not in out.get(key, []):
                out.setdefault(key, []).append(m)
    ice = clim.get("water", {}).get("ice")
    if ice and water:
        ms = _months_in(ice.get("months", []), season)
        if ms:
            out["frozen"] = ms
    return {k: sorted(v, key=S.month_index) for k, v in sorted(out.items())}


# Where a region's own heights are built (a city's raised hills, a palace terrace) its levels
# overstate the land's height: the snow line there, by month, and the districts it falls on
# (seasons.md §2.4: in Rome at most a rare dusting; at Athens snow on Pentelikon and Lykabettos,
# only a flurry in the city; at Pārsa snow on the mountain behind the terrace all winter and on
# the plain on a few January days, the climate's lowland rule).
N = None
REGION_SNOW = {
    "rome": {"line": [N] * 12},
    "athens": {"line": [N, N, N, N, N, N, N, N, N, 10, 9, 10],
               "districts": ["pentelikon", "lykabettos", "hymettos"]},
    "parsa": {"line": [15, N, N, N, N, N, N, N, 15, 14, 14, 14], "districts": ["slope"]},
    "alban_mount": {"line": [N, N, N, N, N, N, N, N, N, 10, 9, 10]},
    "corinth": {"line": [N, N, N, N, N, N, N, N, N, N, 7, N]},
}


def themes(doc: dict, clim: dict, world, rid: str, water: list[dict], beds: dict) -> None:
    """`theme.seasons`: grade, look, haze, ground, snow line and beds per season."""
    th = doc.setdefault("theme", {})
    mask = _region_mask(world, rid)
    terr = _terrains(world, mask) if mask.any() else set()
    over = REGION_SNOW.get(rid)
    if over:
        th["snow"] = dict(over)
        if over.get("districts"):
            ids = [world.districts.index(f"{rid}/{d}") for d in over["districts"]
                   if f"{rid}/{d}" in world.districts]
            mask = np.isin(world.D, ids)
        clim = dict(clim, snow=dict(clim.get("snow", {}), line=over["line"]))
    else:
        th.pop("snow", None)
    lv = (world.L & 0x0F)[mask] if mask.any() else np.zeros(1, dtype=np.uint8)
    levels = (int(lv.min()), int(lv.max())) if lv.size else (0, 0)
    base_haze = th.get("haze", {}).get("strength", 0.12)
    have = th.get("seasons", {})
    out = {}
    line = clim.get("snow", {}).get("line", [None] * 12)
    for s in C.SEASONS:
        h = have.get(s, {})
        look = {**clim.get("look", {}).get(s, {}), **h.get("look", {})}
        e = {"grade": h.get("grade") or clim.get("grade", {}).get(s, [1.0, 1.0, 1.0])}
        if look:
            e["look"] = look
        e["haze"] = round(max(0.0, min(1.0, base_haze * (1 + look.get("haze", 0.0)))), 3)
        e["ground"] = ground(clim, terr, levels, water, s)
        ms = S.season_months(s)
        e["snow_line"] = [line[S.month_index(m)] for m in ms]
        b = h.get("ambience") or beds.get(s)
        if b:
            e["ambience"] = b
        out[s] = e
    th["seasons"] = out


# -- water ---------------------------------------------------------------------------------------

def water(doc: dict, clim: dict, bodies: list[dict], ranked: set[str]) -> list[dict]:
    """The region's waters with their level by month (the climate's row for the kind) and flood
    rank; a body with no flood-ranked ground beside it rises `high`, never `flood`."""
    rid = doc["id"]
    rows = clim.get("water", {})
    out = []
    for b in bodies:
        if b["region"] != rid:
            continue
        kind = b["kind"]
        level = list(rows.get(kind) or rows.get("river" if kind == "lake" else "stream") or
                     ["normal"] * 12)
        level = ["normal" if lv == "full" else lv for lv in level] if kind != "channel" else \
            ["high" if lv == "full" else lv for lv in level]
        rank = list(rows.get(f"{kind}_rank", [0] * 12)) if kind == "river" else [0] * 12
        if (rid, b["name"]) not in ranked:
            level = ["high" if lv == "flood" else lv for lv in level]
            rank = [0] * 12
        else:
            rank = [max(1, r) if lv == "flood" else r for r, lv in zip(rank, level)]
        cs = [c for c, _ in b["tiles"]]
        rs = [r for _, r in b["tiles"]]
        g = [to_grid(c, r) for c in (min(cs), max(cs)) for r in (min(rs), max(rs))]
        e = {"body": b["name"], "kind": kind, "tiles": len(b["tiles"]),
             "rect": [int(min(x for x, _ in g)), int(min(y for _, y in g)),
                      int(max(x for x, _ in g)), int(max(y for _, y in g))],
             "level": level}
        if any(rank):
            e["rank"] = rank
        col = rows.get("colour")
        if col:
            e["colour"] = {lv: col[lv] for lv in C.WATER_LEVELS if lv in col and lv in level}
        if rows.get("ice"):
            e["ice"] = rows["ice"]
        out.append(e)
    if out:
        doc["water"] = out
    else:
        doc.pop("water", None)
    return out


# -- tokens, harbours, dress -------------------------------------------------------------------

SHIPS = ("merchantman", "merchant", "trireme", "phoenician", "egyptian_sailor", "grain")
RIVER_BOATS = ("reed_boat", "quffa", "kelek", "barge")
FISHING = [0.7, 0.8, 1, 1, 1, 1, 1, 0.9, 0.7, 0.5, 0.5, 0.6]


def token_row(tk: dict) -> str | list | None:
    a = tk.get("actor", "")
    name = a.split(".")[-1]
    if tk.get("note", "").startswith("flocks") or tk.get("group") == "drove":
        return None
    if "grain" in tk.get("lane", "") or tk.get("carry") == "world.goods_sacks" and tk.get("lane"):
        return "grain"
    if name == "fishing_boat" or name == "fishing":
        return FISHING
    if name in RIVER_BOATS:
        return "barge"
    if any(s in name for s in SHIPS):
        return "sailing"
    if name == "courier":
        return "courier"
    if name in ("caravan_driver", "muleteer") or tk.get("group") in ("caravan", "mule_train"):
        return "caravan"
    if tk.get("route"):
        return "road"
    return None


def tokens(doc: dict, clim: dict, raw: dict) -> None:
    for tk in doc.get("lanes_tokens", []):
        if "by_month" in tk:
            continue
        row = token_row(tk)
        if row is None:
            continue
        if isinstance(row, str):
            if S.lookup_row(clim, raw, row) is None:
                row = "road" if S.lookup_row(clim, raw, "road") else None
            if row is None:
                continue
        tk["by_month"] = row
        if row == "caravan" and clim.get("travel", {}).get("hours"):
            tk["travel_hours"] = clim["travel"]["hours"]


HARBOUR_DISTRICTS = ("harbour", "harbours", "portus", "piraeus", "quay", "sea")


def harbours(doc: dict, clim: dict, raw: dict) -> None:
    """Harbour zones whose ships are laid up while the sea is closed (the sailing row under 0.3):
    hulls hauled ashore on their slipways and beaches, shipwrights at work."""
    if P.REGIONS[doc["id"]][0] not in ("city", "town") or doc.get("harbours"):
        return
    ships = [tk for tk in doc.get("lanes_tokens", []) if tk.get("by_month") == "sailing"]
    zones = [d["id"] for d in doc.get("districts", []) if d["id"] in HARBOUR_DISTRICTS]
    if ships and zones and S.lookup_row(clim, raw, "sailing"):
        doc["harbours"] = [{"zone": z, "laid_up": "sailing", "below": 0.3,
                            "props": ["world.hull_ashore"]} for z in zones]


def dress(doc: dict) -> None:
    roles = {r["id"]: r.get("actor", "") for r in doc.get("roles", [])}
    for d in doc.get("districts", []):
        for p in d.get("populations", []):
            kind = roles.get(p.get("role", ""), p.get("actor") or roles.get(p.get("role", "")))
            want = C.DRESS.get(kind or "")
            if want and "variants" not in p:
                p["variants"] = {k: "climate" for k in ("cold", "hot") if want in (k, "both")}


def normalise_filters(doc: dict) -> None:
    """`seasons` on a population or token becomes the filter vocabulary's `when.season`."""
    for d in doc.get("districts", []):
        for p in d.get("populations", []):
            if "seasons" in p:
                p.setdefault("when", {})["season"] = p.pop("seasons")
    for tk in doc.get("lanes_tokens", []):
        w = tk.get("when", {})
        if "seasons" in w:
            w["season"] = w.pop("seasons")


# -- helpers for the cities' seasonal modules --------------------------------------------------

def sibling(path: str, name: str):
    """A region's own seasonal module beside its life module (`regions/<layer>/<name>.py`)."""
    import importlib.util
    from pathlib import Path
    f = Path(path).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"worldgen_{f.parent.name}_{name}", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def monthly(entry: dict, factors: list[float] | None = None,
            density: dict[str, str] | None = None) -> list[dict]:
    """One population entry split into entries by month: `factors` (twelve) scale its numbers,
    `density` ({month: curve}) swaps its density curve in those months. Months of factor 0 drop
    out; months that agree share one entry (with `when.months`), and an entry that is the same
    all year keeps no month filter."""
    factors = factors or [1.0] * 12
    groups: dict[tuple, list[str]] = {}
    for i, m in enumerate(C.MONTHS):
        f = round(factors[i], 3)
        if f <= 0:
            continue
        dens = (density or {}).get(m, entry.get("density"))
        groups.setdefault((f, dens), []).append(m)
    out = []
    for (f, dens), ms in groups.items():
        e = copy.deepcopy(entry)
        if dens is not None:
            e["density"] = dens
        for k in ("max_per_chunk", "count"):
            if k in e and f != 1.0:
                e[k] = round(e[k] * f, 2)
        if len(ms) < 12:
            w = e.setdefault("when", {})
            if "months" in w:
                ms = [m for m in ms if m in w["months"]]
                if not ms:
                    continue
            w["months"] = ms
        out.append(e)
    return out


def vary(doc: dict, rule) -> None:
    """Rewrite every population entry that `rule(district_id, entry)` answers with
    (factors, density map) into its monthly entries."""
    for d in doc.get("districts", []):
        new = []
        for p in d.get("populations", []):
            r = rule(d["id"], p)
            new += monthly(p, *r) if r else [p]
        d["populations"] = new


def factors(base: float = 1.0, **by: float) -> list[float]:
    """Twelve factors: `base`, with month spans as keyword names (`dec_feb=0.8`, `jul=0.5`)."""
    return C.by_month({k.replace("_", "-"): v for k, v in by.items()}, base)


def in_months(when: list[str]) -> dict:
    return {"months": list(when)}


# -- birds, herds and work on the land ---------------------------------------------------------

def fauna(doc: dict, clim: dict) -> None:
    """Storks, cranes and swifts by month over the open land; stork entries already there get the
    climate's months instead of a season."""
    fa = clim.get("fauna", {})
    for d in doc.get("districts", []):
        if d["id"] != "land":
            continue
        pops = [p for p in d.get("populations", []) if p.get("actor") != "world.stork"]
        if fa.get("storks"):
            pops.append({"actor": "world.stork", "density": "daytime", "max_per_chunk": 1,
                         "when": in_months(fa["storks"])})
        cranes = sorted(set(fa.get("cranes_pass", [])) | set(fa.get("cranes_winter", [])),
                        key=S.month_index)
        if cranes:
            pops.append({"actor": "world.crane", "density": "daytime",
                         "max_per_chunk": 2 if fa.get("cranes_winter") else 1,
                         "when": in_months(cranes)})
        if fa.get("swifts") or fa.get("swallows"):
            pops.append({"actor": "world.swift", "density": "daytime", "max_per_chunk": 1,
                         "when": in_months(fa.get("swifts") or fa["swallows"])})
        d["populations"] = pops


# Transhumance (seasons.md §3.8; Varro on Apulia and the mountains): the summer pastures, the
# winter pastures they come down to, and the months on the road between.
TRANSHUMANCE = [("apennines", "latium_italy"), ("arcadia", "greece"), ("zagros", "susiana"),
                ("taurus", "east_med"), ("syrian_steppe", "mesopotamia")]


def _route_between(graphs, world, high: str, low: str) -> tuple[str, str] | None:
    """Two base nodes, one in each region, joined on the base graph (shortest hop count)."""
    base = graphs.get("base")
    if base is None:
        return None
    from .compose import NONE16

    def region_at(n):
        c, r = to_plan(*n.at)
        d = int(world.D[r, c])
        return None if d == NONE16 else world.districts[d].split("/", 1)[0]

    nodes = {n.id: n for n in base.nodes}
    adj: dict[str, list[str]] = {}
    for e in base.edges:
        adj.setdefault(e.a, []).append(e.b)
        adj.setdefault(e.b, []).append(e.a)
    starts = sorted(n.id for n in base.nodes if region_at(n) == high
                    and (n.kind == "station" or "_farm_" in n.id or n.id in adj))
    goals = {n.id for n in base.nodes if region_at(n) == low and
             (n.kind == "station" or "_farm_" in n.id)}
    if not starts or not goals:
        return None
    from collections import deque
    best = None
    for s0 in starts[:40]:
        q, seen = deque([(s0, 0)]), {s0}
        while q:
            n, dd = q.popleft()
            if n in goals:
                if best is None or (dd, s0, n) < best:
                    best = (dd, s0, n)
                break
            for m in sorted(adj.get(n, [])):
                if m not in seen and m in nodes:
                    seen.add(m)
                    q.append((m, dd + 1))
    return (best[1], best[2]) if best else None


def transhumance(docs: dict, world, graphs, clims: dict) -> None:
    """Herds that summer on the high pastures and winter below (or, on the steppe, the
    reverse), with the drove road between their districts."""
    for high, low in TRANSHUMANCE:
        if high not in docs or low not in docs:
            continue
        hc = clims[C.REGION_CLIMATE[high]]
        tr = hc.get("transhumance") or clims[C.REGION_CLIMATE[low]].get("transhumance")
        if not tr:
            continue
        route = _route_between(graphs, world, high, low)
        if route is None:
            continue
        hd = {d["id"] for d in docs[high]["districts"]}
        ld = {d["id"] for d in docs[low]["districts"]}
        summer = f"{high}/{'pasture' if 'pasture' in hd else 'land'}"
        winter = f"{low}/{'pasture' if 'pasture' in ld else 'farm' if 'farm' in ld else 'land'}"
        set_ = P.REGIONS[high][1]
        from .life import SHEPHERD
        herder = SHEPHERD.get(set_, "world.muleteer")
        group = {"id": "transhumance", "formation": "cluster", "radius": 3,
                 "leader": {"actor": herder},
                 "members": [{"actor": "world.sheep", "variant": 1 if set_ == "parsa" else 0,
                              "count": 10}, {"actor": "world.goat", "count": 4},
                             {"actor": "world.dog", "count": 1}],
                 "seasonal": {"summer": summer, "winter": winter,
                              "summer_months": tr["high"], "winter_months": tr["low"],
                              "move": tr["up"] + tr["down"],
                              "route": {"start": f"base:{route[0]}", "end": f"base:{route[1]}"}}}
        docs[high]["groups"] = [g for g in docs[high]["groups"] if g["id"] != "transhumance"] + [group]
        docs[high]["lanes_tokens"].append(
            {"actor": herder, "group": "transhumance", "count": 1,
             "route": {"start": f"base:{route[0]}", "end": f"base:{route[1]}"},
             "when": in_months(tr["up"] + tr["down"]),
             "note": "flocks moving between the summer and the winter pastures"})


def drove_months(doc: dict, clim: dict) -> None:
    """The stretches' drove tokens move in the transhumance months (else May and October)."""
    tr = clim.get("transhumance") or {}
    move = (tr.get("up", []) + tr.get("down", [])) or ["may", "oct"]
    for tk in doc.get("lanes_tokens", []):
        w = tk.get("when", {})
        if tk.get("group") == "drove" and w.get("season") == ["spring", "autumn"]:
            tk["when"] = in_months(move)


# Seasonal work on the land between the cities (seasons.md §3.7): the work, the climate's months
# for it, who does it, where, and how they look doing it. Each is a role whose population exists
# only in its months; the targets are the kit the base places on farms.
FARMER = {"rome": "rome.farmer", "athens": "athens.farmer", "parsa": "parsa.farmer"}
TREE = {"rome": "rome.t_olive", "athens": "athens.t_olive"}
WORK = [
    # (role id, work key, name, target item (or None: the fields), anim, max per chunk)
    ("ploughman", "ploughing", "Ploughing and sowing", None, "work_low", 2),
    ("reaper", "harvest", "Reaping", None, "work_low", 3),
    ("thresher", "threshing", "Threshing and winnowing", "world.haystack", "work_low", 2),
    ("haymaker", "hay", "Haymaking", "world.haystack", "work_low", 2),
    ("pruner", "pruning", "Pruning the vines and trees", None, "work_low", 1),
    ("vintager", "vintage", "Vintage and treading", "world.treading_vat", "work_low", 2),
    ("olive_picker", "olive", "Olive harvest", "olive", "work_low", 3),
    ("charcoal_burner", "charcoal", "Charcoal burning", "world.charcoal_kiln", "work_low", 1),
    ("date_picker", "dates_harvest", "Date harvest", "world.t_palm", "work_low", 2),
    ("canal_clearer", "canals", "Clearing the canals", "world.shaduf", "work_low", 2),
]
WORK_HOURS = (("06:00", "11:30"), ("14:00", "18:30"))
HOT_HOURS = (("05:00", "10:00"), ("16:00", "19:30"))


def land_work(doc: dict, clim: dict, world, placed: dict[str, set[str]]) -> None:
    """Roles for the seasonal work on a stretch's farms, each out only in its months."""
    rid = doc["id"]
    set_ = P.REGIONS[rid][1]
    farm = next((d for d in doc.get("districts", []) if d["id"] == "farm"), None)
    if farm is None or set_ not in FARMER:
        return
    work = clim.get("work", {})
    hot = set(clim.get("travel", {}).get("hours", {}).get("months", []))
    roles = []
    for rid_, key, name, target, anim, n in WORK:
        ms = work.get(key)
        if not ms:
            continue
        tgt = TREE.get(set_) if target == "olive" else target
        if target is not None and (tgt is None or rid not in placed.get(tgt, set())):  # by region
            continue
        actor = FARMER[set_]
        if anim not in KIND_ANIMS.get(actor, {anim}):
            anim = "idle"
        steps = []
        if tgt:
            steps.append({"go": {"item": tgt, "spot": "beside", "within": 48}})
        else:
            steps.append({"wander": {"radius": 10}, "dur": [20, 40]})
        steps += [{"use": {"here": True}, "anim": anim, "dur": [30, 60]},
                  {"wander": {"radius": 6}, "dur": [10, 20]},
                  {"use": {"here": True}, "anim": anim, "dur": [20, 40]}]
        hours = HOT_HOURS if hot & set(ms) else WORK_HOURS
        roles.append({"id": rid_, "actor": actor, "name": name,
                      "schedule": [{"hours": list(h), "routine": "work"} for h in hours],
                      "routines": {"work": {"loop": True, "steps": steps}}})
        farm["populations"].append({"role": rid_, "density": "fields", "max_per_chunk": n,
                                    "when": in_months(ms)})
        if key == "ploughing":
            farm["populations"].append({"actor": "world.ox", "density": "fields",
                                        "max_per_chunk": 1, "when": in_months(ms)})
    if roles:
        doc["roles"] = [r for r in doc.get("roles", []) if r["id"] not in {x["id"] for x in roles}] + roles


KIND_ANIMS: dict[str, set[str]] = {}
AUDIO: set[str] = set()
STAND_IN = {"sfx": "sfx/world/seam.wav", "ambience": "amb/world/river_2.ogg"}


def load_kinds(root) -> None:
    from .citylife import content_facts
    if not KIND_ANIMS:
        kinds, _g, audio = content_facts(root, ["world", "rome", "athens", "parsa"])
        KIND_ANIMS.update(kinds)
        AUDIO.update(audio)


# -- turns of the seasons ----------------------------------------------------------------------

TURN_LINES = {
    "swallows_return": "The swallows are back under the eaves.",
    "storks_arrive": "The storks are back on their nests.",
    "cranes_overhead": "Cranes call high overhead, flying in a long V.",
    "cicadas_begin": "The cicadas have started.",
    "first_rains": "The first rain. The whole land smells of dust and earth.",
    "first_snow": "Snow on the heights.",
    "first_frost": "Frost on the ground this morning.",
    "first_dust": "Dust on the wind: the dry months have come.",
    "heat_haze": "The air shimmers over the land at noon.",
    "flood_rising": "The river is rising over the low fields.",
    "snowmelt": "Meltwater roars down the gorges.",
    "braziers_lit": "Braziers glow in the doorways against the cold.",
    "ships_hauled_ashore": "The sea is closed. Ships are hauled up on the shore for the winter.",
    "sailing_opens": "The sea opens: the first ships put out.",
    "storms_return": "Autumn storms over the sea.",
    "meltemi": "The north wind whitens the sea in the afternoons.",
    "shamal": "The north-west wind blows dust over the water.",
    "vintage_begins": "The grapes are in: the vintage begins.",
    "ploughing_begins": "Ploughing time: oxen in the fields.",
    "date_harvest": "Climbers in the palms: the date harvest.",
    "flocks_up": "The flocks are on the high pastures.",
    "flocks_down": "The flocks come down to the lowlands.",
    "leaves_turn": "The woods are turning copper and gold.",
    "first_green": "A green flush over the land.",
    "court_leaves": "The court rides out for the cool of the north.",
}


def turn_events(doc: dict, clim: dict, root) -> None:
    """One event per season's first dawn (and per month the climate names), deterministic like
    any event: in the day plan, with what it shows and plays."""
    rid = doc["id"]
    evs = [e for e in doc.get("events", []) if e.get("trigger", {}).get("on") != "season_turn"]
    strings = doc.setdefault("strings", {})
    turns = [(s, None, t) for s, t in clim.get("turn_events", {}).items()] + \
        [(S.season_of(S.month_index(m)), m, t) for m, t in clim.get("month_turns", {}).items()]
    if any(h.get("laid_up") for h in doc.get("harbours", [])) and \
            clim.get("turn_events", {}).get("winter") == "braziers_lit":
        turns = [(s, m, "ships_hauled_ashore" if (s == "winter" and m is None) else t)
                 for s, m, t in turns]
    for season, month, t in sorted(turns, key=lambda x: (C.SEASONS.index(x[0]), x[1] or "")):
        spec = C.TURNS[t]
        if spec["show"] == "home":
            continue   # the corner's own turn belongs to the home catalog
        trig = {"on": "season_turn", "season": season, "hours": ["05:30", "07:00"]}
        if month:
            trig["months"] = [month]
        e = {"id": f"turn_{month or season}_{t}", "rarity": "festival", "size": "small",
             "trigger": trig, "duration": [40, 60], "turn": t, "show": spec["show"],
             "steps": [], "string": f"season_turn.{month or season}"}
        if spec.get("fx"):
            e["steps"].append({"emit": {"fx": spec["fx"]}})
        # Sounds not recorded yet play a stand-in and stay on the audio lane's list
        # (`pending_sound`, gathered into assets/world/season-needs.json).
        for k in ("sfx", "ambience"):
            f = spec.get(k)
            if not f:
                continue
            if f not in AUDIO:
                e.setdefault("pending_sound", []).append(f)
                f = STAND_IN.get(k)
            if k == "sfx":
                e["sfx"] = f
            else:
                e["ambience"] = {"file": f, "gain": 0.6}
        if not e.get("sfx") and not e.get("ambience"):
            e["sfx"] = "sfx/world/swifts.wav" if t == "cicadas_begin" else "sfx/world/seam.wav"
        if spec.get("actor"):
            e["cast"] = [{"actor": spec["actor"], "count": 6}]
        evs.append(e)
        strings.setdefault(f"season_turn.{month or season}", TURN_LINES[t])
    doc["events"] = evs


# -- the towns' and stretches' own seasons -----------------------------------------------------

def _ev(id_, months, hours, cast, steps, sfx, string, size="medium", rarity="festival", **kw):
    t = {"on": "window", "hours": hours, "chance": 1.0}
    if months:
        t["months"] = months
    return {"id": id_, "rarity": rarity, "size": size, "trigger": t | kw.pop("trigger", {}),
            "duration": kw.pop("duration", [120, 180]), "cast": cast, "steps": steps,
            "sfx": sfx, "string": string, **kw}


def _card(title, epithet, text):
    return {"title": title, "epithet": epithet, "text": text}


# Per town: festivals on their months, events, population factors by month (a rule of
# (district or "*", actor or "*") -> twelve factors), extra strings and cards.
TOWN_SEASONS = {
    "eleusis": {
        "festivals": [{"id": "mysteries", "season": "autumn", "day": 1, "hours": ["06:00", "22:00"]}],
        "events": [_ev("mysteries_arrival", None, ["15:00", "16:00"],
                       [{"actor": "athens.citizen", "count": 14}, {"actor": "athens.woman", "count": 8},
                        {"actor": "athens.priest", "count": 2}],
                       [{"go": {"node": "sacred_way_w"}}, {"go": {"node": "telesterion"}},
                        {"use": {"here": True}, "anim": "idle", "dur": [60, 90]}],
                       "sfx/world/chorus_far.wav", "mysteries", size="large",
                       trigger={"on": "calendar", "festival": "mysteries"}, duration=[240, 300],
                       route=["sacred_way_w", "eleusis_town", "telesterion"], card="mysteries")],
        "strings": {"mysteries": "The initiates arrive from Athens by the Sacred Way."},
        "cards": {"mysteries": _card("The Mysteries", "Eleusis, in Boedromion",
                                     "Each autumn the initiates walked the Sacred Way from Athens "
                                     "to Demeter's sanctuary, calling on Iakchos, and arrived at "
                                     "torchlight. What was shown inside the Telesterion was never "
                                     "told: to speak of it was a crime, and the secret was kept "
                                     "for a thousand years.")},
    },
    "olympia": {
        "festivals": [{"id": "olympia", "season": "summer", "day": 3, "hours": ["06:00", "20:00"]}],
        "events": [_ev("olympic_crowd", None, ["07:00", "08:00"],
                       [{"actor": "athens.citizen", "count": 16}, {"actor": "athens.athlete", "count": 8},
                        {"actor": "athens.ionian", "count": 6}, {"actor": "athens.priest", "count": 2}],
                       [{"go": {"node": "olympia_n"}}, {"go": {"node": "altis"}},
                        {"use": {"here": True}, "anim": "idle", "dur": [120, 180]}],
                       "sfx/world/cheer.wav", "olympia", size="large",
                       trigger={"on": "calendar", "festival": "olympia"}, duration=[300, 360],
                       route=["olympia_n", "altis"], card="olympia_festival")],
        "factors": {("*", "*"): factors(1.0, dec_feb=0.5, nov=0.7, mar=0.7)},
        "strings": {"olympia": "The truce holds: crowds from every Greek city fill the Altis."},
        "cards": {"olympia_festival": _card("The Olympic festival", "432 BC, the 87th",
                                            "Every fourth summer heralds proclaimed a truce and "
                                            "Greeks from every city came to Zeus' precinct: five "
                                            "days of sacrifice and contests, the great sacrifice "
                                            "of oxen at the ash altar, and the olive crown for the "
                                            "victors. 432 BC was a festival year; the Spartan "
                                            "stadion victor was praised by poets.")},
    },
    "sparta": {
        "festivals": [{"id": "karneia", "season": "summer", "day": 3, "hours": ["07:00", "20:00"]}],
        "events": [_ev("karneia_feast", None, ["17:00", "18:00"],
                       [{"actor": "athens.spartan", "count": 12}, {"actor": "athens.musician", "count": 2},
                        {"actor": "athens.citizen", "count": 4}],
                       [{"go": {"node": "sparta_shrine"}}, {"use": {"here": True}, "anim": "idle",
                                                             "dur": [90, 120]}],
                       "sfx/athens/aulos.wav", "karneia", trigger={"on": "calendar", "festival": "karneia"},
                       duration=[180, 240], route=["sparta_e", "sparta_shrine"], card="karneia")],
        "strings": {"karneia": "The Karneia: the Spartans feast in tents, and no army marches."},
        "cards": {"karneia": _card("The Karneia", "Apollo's festival at Sparta",
                                   "In late summer the Spartans kept the Karneia for Apollo: men "
                                   "feasted in tents in imitation of a camp, young men raced, and "
                                   "music contests were held. While it lasted no Spartan army "
                                   "marched, which is why only a few were at Thermopylae in 480.")},
    },
    "delphi": {
        "festivals": [{"id": "pythia_returns", "season": "spring", "day": 1, "hours": ["07:00", "18:00"]},
                      {"id": "god_away", "months": ["dec", "jan", "feb"], "hours": ["00:00", "24:00"]}],
        "events": [_ev("consultation_day", None, ["08:00", "09:00"],
                       [{"actor": "athens.citizen", "count": 8}, {"actor": "athens.ionian", "count": 4},
                        {"actor": "athens.priest", "count": 2}],
                       [{"go": {"node": "delphi_s"}}, {"go": {"node": "temple"}},
                        {"use": {"here": True}, "anim": "idle", "dur": [90, 120]}],
                       "sfx/world/hush.wav", "pythia_returns",
                       trigger={"on": "calendar", "festival": "pythia_returns"}, duration=[240, 300],
                       route=["delphi_s", "treasury", "temple"], card="god_away")],
        "factors": {("*", "athens.ionian"): factors(1.0, dec_feb=0.0),
                    ("*", "athens.citizen"): factors(1.0, dec_feb=0.3),
                    ("*", "*"): factors(1.0, dec_feb=0.6)},
        "strings": {"pythia_returns": "Apollo is back from the north: the first consultation of the year.",
                    "season_turn.winter": "The paean is silent: these three months belong to Dionysus."},
        "cards": {"god_away": _card("The god's winter", "Delphi, December to February",
                                    "Plutarch, a priest at Delphi, says that for the three winter "
                                    "months the paean fell silent and Dionysus was honoured "
                                    "instead, while Apollo was thought to be away in the north. "
                                    "No consultants queued; in spring the god returned and the "
                                    "Pythia spoke again, on the seventh day of the month.")},
    },
    "delos": {
        "factors": {("*", "*"): [0.5, 0.8, 1, 1, 1, 1, 1, 0.8, 0.5, 0.3, 0.3, 0.3]},
        "strings": {"season_turn.winter": "The sea is closed: few pilgrims reach the island now."},
    },
    "babylon": {
        "festivals": [{"id": "king_in_babylon", "months": ["dec", "jan", "feb"], "hours": ["00:00", "24:00"]}],
        "events": [_ev("royal_guard_winter", ["dec", "jan", "feb"], ["09:00", "10:00"],
                       [{"actor": "parsa.guard_spear", "count": 10}, {"actor": "parsa.guard_mede", "count": 6}],
                       [{"go": {"node": "ishtar_gate"}}, {"go": {"node": "etemenanki_court"}},
                        {"use": {"here": True}, "anim": "idle", "dur": [60, 90]}],
                       "sfx/parsa/horn.wav", "king_in_babylon", rarity="uncommon",
                       duration=[150, 210], route=["ishtar_gate", "n2", "etemenanki_court"],
                       card="winter_court"),
                   _ev("date_harvest", ["sep", "oct"], ["07:00", "08:00"],
                       [{"actor": "parsa.gardener", "count": 6}, {"actor": "parsa.labourer", "count": 4}],
                       [{"go": {"item": "parsa.t_date", "spot": "beside", "within": 40}},
                        {"use": {"here": True}, "anim": "work_high", "dur": [60, 90]}],
                       "sfx/world/chop.wav", "date_harvest", rarity="uncommon", duration=[180, 240]),
                   _ev("palm_pollination", ["mar", "apr"], ["08:00", "09:00"],
                       [{"actor": "parsa.gardener", "count": 4}],
                       [{"go": {"item": "parsa.t_date", "spot": "beside", "within": 40}},
                        {"use": {"here": True}, "anim": "work_high", "dur": [60, 90]}],
                       "sfx/world/rope.wav", "palm_pollination", rarity="uncommon", duration=[150, 200])],
        "factors": {("*", "parsa.guard_spear"): factors(1.0, dec_feb=2.0),
                    ("*", "*"): [1, 1, 1, 0.8, 0.7, 0.7, 0.9, 1, 1, 1, 1, 1]},
        "density": {"jun": "daytime_hot", "jul": "daytime_hot", "aug": "daytime_hot"},
        "strings": {"king_in_babylon": "Royal guards and banners at the palace: the court winters here, Greek writers say.",
                    "date_harvest": "Climbers in the palms cut the heavy clusters of dates.",
                    "palm_pollination": "Gardeners climb the palms to dust the female flowers."},
        "cards": {"winter_court": _card("The king's winter", "Babylon, as Greek writers say",
                                        "Xenophon writes that the Persian king spent seven winter "
                                        "months in Babylon, three spring months at Susa and two "
                                        "summer months at Ecbatana. Other Greek writers say much "
                                        "the same. The court's moves are not described in any "
                                        "Persian record, so the game shows them as Greek writers "
                                        "say.")},
    },
    "susa": {
        "factors": {("*", "*"): [1, 1, 1, 0.8, 0.7, 0.7, 0.9, 1, 1, 1, 1, 1]},
        "density": {"jun": "daytime_hot", "jul": "daytime_hot", "aug": "daytime_hot"},
        "strings": {"season_turn.summer": "Susa's summer: the streets are empty at midday, as Strabo says, "
                                          "hot enough to roast a lizard crossing them."},
    },
    "persian_gates": {"factors": {("*", "*"): factors(1.0, dec_feb=0.6, nov=0.8, mar=0.8)}},
    "pasargadae": {"factors": {("*", "*"): factors(1.0, dec_feb=0.6, nov=0.8)}},
    "halys": {"factors": {("*", "*"): factors(1.0, dec_feb=0.6, nov=0.8, mar=0.8)}},
    "gordion": {"factors": {("*", "*"): factors(1.0, dec_feb=0.6, nov=0.8, mar=0.8)}},
    "euphrates_crossing": {"factors": {("*", "*"): factors(1.0, dec_feb=0.6, nov=0.8, mar=0.8)}},
}
for _t in ("tibur", "capua", "beneventum", "corcyra", "academy", "corinth", "ephesus", "sardis",
           "sidon"):
    TOWN_SEASONS.setdefault(_t, {"factors": {("*", "*"): factors(1.0, dec_feb=0.8)}})
# A town's day in the heat: out early and late, empty streets at midday.
HOT_DAY = [0, 0, 0, 0, 0.2, 0.6, 0.9, 1, 1, 0.8, 0.5, 0.25, 0.1, 0.1, 0.2, 0.4, 0.7, 0.9, 1,
           0.8, 0.5, 0.2, 0.05, 0]

STRETCH_SEASONS = {
    "latium_italy": {"events": [
        _ev("starlings", ["oct", "nov", "dec", "jan", "feb"], ["17:00", "18:30"], [],
            [{"emit": {"fx": "fx/world.starlings"}}], "sfx/world/swifts.wav", "starlings",
            size="small", rarity="common", duration=[60, 90])],
        "strings": {"starlings": "Clouds of starlings wheel over the Campagna at dusk."}},
    "mesopotamia": {"events": [
        _ev("date_harvest", ["sep", "oct"], ["07:00", "08:00"],
            [{"actor": "parsa.gardener", "count": 4}],
            [{"go": {"item": "parsa.t_date", "spot": "beside", "within": 64}},
             {"use": {"here": True}, "anim": "work_high", "dur": [60, 90]}],
            "sfx/world/chop.wav", "date_harvest", rarity="uncommon", duration=[180, 240])],
        "strings": {"date_harvest": "Climbers in the palms cut the heavy clusters of dates."}},
    "attica_north": {"token_factors": {"world.goods_charcoal": factors(1.0, dec_feb=2.0, jun_aug=0.5)}},
}


def towns_and_stretches(doc: dict, rid: str) -> None:
    spec = TOWN_SEASONS.get(rid) or STRETCH_SEASONS.get(rid)
    if not spec:
        return
    fest = {f["id"] for f in doc.get("festivals", [])}
    doc["festivals"] = doc.get("festivals", []) + [f for f in spec.get("festivals", [])
                                                   if f["id"] not in fest]
    have = {e["id"] for e in doc.get("events", [])}
    layer = rid if P.REGIONS[rid][0] == "town" else "base"
    pre = (lambda n: n if ":" in n else f"{layer}:{n}")
    for e in spec.get("events", []):
        if e["id"] in have:
            continue
        e = copy.deepcopy(e)
        if "route" in e:
            e["route"] = [pre(n) for n in e["route"]]
        for st in e.get("steps", []):
            if "node" in st.get("go", {}):
                st["go"]["node"] = pre(st["go"]["node"])
        doc.setdefault("events", []).append(e)
    doc.setdefault("strings", {}).update(spec.get("strings", {}))
    doc.setdefault("cards", {}).update(spec.get("cards", {}))
    if spec.get("density"):
        doc.setdefault("densities", {})["daytime_hot"] = HOT_DAY
    rules = spec.get("factors", {})
    dens = spec.get("density")
    if rules or dens:
        def rule(dist, p):
            key = p.get("actor") or p.get("role")
            f = rules.get((dist, key)) or rules.get(("*", key)) or rules.get((dist, "*")) or \
                rules.get(("*", "*"))
            d = dens if p.get("density") == "daytime" else None
            return (f, d) if (f or d) else None
        vary(doc, rule)
    for tk in doc.get("lanes_tokens", []):
        f = spec.get("token_factors", {}).get(tk.get("carry", ""))
        if f:
            tk["by_month"] = f


# -- the whole pass ----------------------------------------------------------------------------

class Context:
    """What `apply` needs from the built world, computed once per run."""

    def __init__(self, world, graphs, cat, root):
        from . import seasons as S_
        self.world, self.graphs, self.cat, self.root = world, graphs, cat, root
        self.raw = S_.raw_climates(root)
        self.clims = {cid: S_.resolve(self.raw, cid) for cid in self.raw}
        self.bodies = S_.water_bodies(world)
        self.flood = S_.flood_ranks(world, self.bodies, self.clims)
        self.ranked = {(f["region"], f["body"]) for f in self.flood if f["tiles"]}
        self.placed = S_.placed_regions(world)
        load_kinds(root)


_CTX: dict[int, Context] = {}


def context(world, graphs, cat, root) -> Context:
    k = id(world)
    if k not in _CTX:
        _CTX.clear()
        _CTX[k] = Context(world, graphs, cat, root)
    return _CTX[k]


def apply(doc: dict, world, graphs, cat, root, beds: dict | None = None) -> dict:
    rid = doc["id"]
    ctx = context(world, graphs, cat, root)
    cid = C.REGION_CLIMATE[rid]
    clim = ctx.clims[cid]
    doc.pop("season", None)
    doc.get("theme", {}).pop("climate", None)
    era(doc, rid)
    moment(doc, rid)
    normalise_filters(doc)
    weather(doc, clim)
    wat = water(doc, clim, ctx.bodies, ctx.ranked)
    themes(doc, clim, world, rid, wat, beds or {})
    towns_and_stretches(doc, rid)
    tokens(doc, clim, ctx.raw)
    harbours(doc, clim, ctx.raw)
    if P.REGIONS[rid][0] == "stretch":
        fauna(doc, clim)
        drove_months(doc, clim)
        land_work(doc, clim, world, ctx.placed)
    dress(doc)
    turn_events(doc, clim, root)
    # `climate` sits with the region's identity at the top of the file.
    out = {}
    for k, v in doc.items():
        out[k] = v
        if k == "caption":
            out["climate"] = cid
    out.setdefault("climate", cid)
    return out


def finish(doc: dict, root) -> dict:
    """After sound and look: cicadas sing in their climate's months."""
    cid = doc.get("climate")
    if cid is None:
        return doc
    ctx = next(iter(_CTX.values()), None)
    clim = ctx.clims[cid] if ctx else S.resolved(root)[cid]
    snd = doc.get("theme", {}).get("sound", {})
    cic = clim.get("fauna", {}).get("cicadas")
    if "cicadas" in snd:
        if cic:
            snd["cicadas"]["months"] = cic
        else:
            snd.pop("cicadas")
    return doc
