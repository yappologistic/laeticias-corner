"""City life: the facts a region's life data stands on, and the checks that keep it true.

A city's region file (world-tech §2.6; living-world §2-§5) says who is where at each hour, what
they do there, which goods move along which chains, and what happens when. This module reads the
built world the way the engine will (slot spots from the geometry files, the region's path graph,
its districts) into a `RegionView`, and checks a region document against it:

  L1  references: actor kinds, animations, goods, items, slots, nodes, districts, densities,
      groups, cards and audio files all exist (goods awaiting art may name a stand-in in
      `pending.goods`)
  L2  reach: every slot a routine uses exists in the region and is reachable on the path graph
      from where the actor lives
  L3  capacity: at no hour do the stated populations need more of a slot than it has
  L4  chains: closed (each stage's input made upstream, the last stage a sink) and steady over a
      simulated week (`lifesim`)
  L5  populations: per-chunk and live-window caps at every hour; busy districts never empty in
      their active hours, never a crowd at night
  L6  cards: every figure and placed landmark has one, within its length band
  L7  names and spelling: no retired name, one transliteration and British spelling throughout
  L8  events: no two events can hold the same route at once
  L9  sound: every audio file and family named is in a manifest; no event, working role or
      populated district is silent (`sound.check`)
  L10 look: `theme.look` and district looks complete and in range (`look.check`)
  L11 names: a name and caption for the region, its era, a name for every district

Population model (what `max_per_chunk` means, for the engine's actor round): a district entry
spawns `density[hour] * max_per_chunk` actors per chunk-sized share (1 024 tiles) of the
district, so a district that covers a sliver of a chunk spawns a sliver of a crowd. `per_item`
entries spawn `count` per placed instance of the item in the district. A screenful (250 tiles)
of a district then shows `0.85 * 250 / 1024` of a chunk's visible people moving with purpose.
"""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from plan import world_plan as P

from . import landform
from . import seasons as SEAS
from .compose import NONE16, World, live_items
from .coords import COLS, ROWS, to_grid, to_plan
from .graph import Graph
from .raster import path_tiles

CHUNK_TILES = P.CHUNK * P.CHUNK
SCREEN_TILES = 250          # living-world §1.1: a screenful at the default zoom
REACH = 24                  # tiles from a slot spot to the path graph (validate.SLOT_REACH)
LIVE_BLOCK = 3              # the live window: the view's chunk and one ring (living-world §7.1)
LIVE_ACTORS = 800           # the engine's live cap (tuning::life::kLiveCap; living-world §7.5 said 400)
GO_SECONDS = 25             # nominal travel time of a `go` step when estimating routine shares
LONG_SECONDS = 300          # an `until` step held for the block
WEEK_CYCLE = 12             # calendar days until month (12) and week day (4) repeat together:
                            # day n is month n mod 12, season (n / 3) mod 4, week day n mod 4

MOVING = 0.85               # share of visible people moving with purpose at any moment
# Area kinds (living-world §1.1): movers with purpose per screenful, minimum and cap; the hours a
# district of that kind is expected to be busy (the midday rest is left out); the cap at night
# (23:00-04:00). A chunk of the district holds at most cap * 1024 / 250 people.
AREA = {
    "centre":  {"min": 12, "cap": 40, "night": 10, "active": [(7, 12), (14, 18)]},
    "town":    {"min": 8, "cap": 28, "night": 6, "active": [(7, 12), (14, 17)]},
    "country": {"min": 4, "cap": 16, "night": 3, "active": [(7, 11), (15, 17)]},
    "road":    {"min": 2, "cap": 10, "night": 3, "active": [(8, 17)]},
    "sea":     {"min": 2, "cap": 10, "night": 3, "active": [(8, 17)]},
    "wild":    {"min": 0, "cap": 8, "night": 3, "active": []},
}

# Card kinds and their length bands in words (persepolis.md §4.3 and athens.md §4.3: 40-60 for
# people; landmark and idea cards as the bibles write them).
CARD_WORDS = {"figure": (40, 60), "landmark": (18, 75), "idea": (40, 125), "delegation": (14, 60),
              "role": (12, 60), "event": (12, 60)}

# Names retired by the fact-check (fact-check.md §1.4, §1.5, §2.4): a name and the cards that may
# still use it (an empty tuple: none). Matching is case-insensitive on whole words.
RETIRED = {
    "parsa": {"Baradkama": (), "Baratkama": (), "New Year audience": (), "griffin capital": (),
              "griffin capitals": (), "Nowruz": ("new_year",), "nōg rōz": ("new_year",)},
    "athens": {"captured shields": (), "Iktinos's Telesterion": ()},
    # rome.md §1 and §7.2 as corrected (fact-check.md §3): the Parilia was "now called" the Romaia
    # by Athenaeus's time, not renamed by decree; Marcus is four on the day; Ovid's flocks are
    # smoked at twilight, not sprinkled at dawn; earlier emperors had beards too.
    "rome": {"renamed the Romaia": (), "renamed by Hadrian": (), "aged five": (),
             "first emperor to wear a beard": (), "sprinkled the flock": (),
             "sprinkled the sheep": ()},
}
# One transliteration per name (the corrected bibles' forms): wrong form -> right form.
SPELLING = {
    "parsa": {"Apadana": "Apadāna", "Tachara": "Tačara", "Hadish": "Hadiš", "Parsa": "Pārsa",
              "Ahura Mazda": "Auramazdā", "Ahuramazda": "Auramazdā", "Auramazda": "Auramazdā",
              "Daryavaush": "Dārayavauš", "Xshayarsha": "Xšayāršā",
              "Kurush": "Kūruš", "Artaxshacha": "Artaxšaça", "Tishtrya": "Tištrya",
              "Irtashduna": "Irtašduna", "Mithradata": "Miθradāta", "Rtakama": "Ṛtakāmā",
              "Pediesse": "Pediese", "Bel-iddin": "Bēl-iddin", "Farnadata": "Farnadāta",
              "Dadush": "Daduš", "Yauna": "Yaunā", "Persian Gate ": "Persian Gates "},
    "athens": {"Perikles": "Pericles", "Phidias": "Pheidias", "Mnesicles": "Mnesikles",
               "Alkibiades": "Alcibiades", "Themistokles": "Themistocles",
               "Sokrates": "Socrates", "Sophokles": "Sophocles", "Ceramicus": "Kerameikos",
               "Peiraieus": "Piraeus", "Peiraeus": "Piraeus", "Akropolis": "Acropolis",
               "Hephaestus": "Hephaistos", "Hephaesteion": "Hephaisteion",
               "Theseion": "Hephaisteion", "Areopagos": "Areopagus", "Dipylon gate": "Dipylon"},
    # Latin forms in card titles, English in running text (rome.md, "Names"); one form each.
    "rome": {"Romaea": "Romaia", "Iuvenal": "Juvenal", "Juvenalis": "Iuvenalis",
             "Apollodoros": "Apollodorus", "Antinoos": "Antinous", "Trajanus": "Traianus",
             "Colosseo": "Colosseum", "Aesculapios": "Aesculapius", "Asklepios": "Aesculapius",
             "Ianiculum": "Janiculum", "Velabro": "Velabrum"},
}
# British spelling (living-world: user-facing text is British).
AMERICAN = {"color": "colour", "center": "centre", "honor": "honour", "harbor": "harbour",
            "gray": "grey", "theater": "theatre", "favor": "favour", "neighbor": "neighbour",
            "labor": "labour", "jewelry": "jewellery", "plow": "plough", "armor": "armour",
            "meter": "metre", "traveler": "traveller", "odor": "odour", "molded": "moulded",
            "mold": "mould", "fiber": "fibre", "vapor": "vapour"}

STEP_VERBS = ("go", "use", "take", "put", "wander", "wait", "enter", "exit", "follow", "say",
              "emit", "pick", "routine", "each", "if")
TARGET_STEPS = ("go", "use", "enter", "exit")


@dataclass
class Problem:
    code: str
    level: str
    where: str
    message: str

    def text(self) -> str:
        return f"{self.code} {self.level}: {self.where}: {self.message}"


@dataclass
class Instance:
    """One placed item of the region with its slot spots (plan tiles) and their graph nodes."""
    item: str
    district: str
    c: int
    r: int
    pw: int
    ph: int
    spots: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    nodes: dict[str, str | None] = field(default_factory=dict)


@dataclass
class RegionView:
    region: str
    kinds: dict[str, set[str]]                      # actor kind -> its animations
    goods: set[str]
    audio: set[str]
    slots: dict[str, dict[str, dict]]               # item -> slot id -> {"kind", "cap"}
    instances: list[Instance]
    nodes: dict[str, tuple[int, int, str | None]]   # node -> (c, r, kind), plan coordinates
    adj: dict[str, list[tuple[str, int]]]           # node -> [(neighbour, tiles)]
    ports: set[str]                                  # "lane:port"
    districts: dict[str, dict]                       # name -> {"tiles", "walk", "chunks", "bbox"}
    landmarks: list[str] = field(default_factory=list)
    item_cards: dict[str, str] = field(default_factory=dict)   # placed item -> its catalog card
    layer: str = ""
    _comp: dict[str, int] | None = None

    def has_node(self, n: str) -> bool:
        """A node of the region's graph, named bare or as `<layer>:<id>` (as the engine reads),
        or `next`: the next node of the event's route."""
        return n in self.nodes or n == "next" or (
            bool(self.layer) and n.startswith(self.layer + ":") and
            n[len(self.layer) + 1:] in self.nodes)

    def component(self, node: str) -> int:
        if self._comp is None:
            comp: dict[str, int] = {}
            for start in sorted(self.nodes):
                if start in comp:
                    continue
                k = len(set(comp.values()))
                q = deque([start])
                comp[start] = k
                while q:
                    n = q.popleft()
                    for m, _ in self.adj.get(n, []):
                        if m not in comp:
                            comp[m] = k
                            q.append(m)
            self._comp = comp
        return self._comp.get(node, -1)

    def distances(self, start: str) -> dict[str, int]:
        """Path-graph distance in tiles from a node to every node it reaches (Dijkstra)."""
        import heapq
        dist = {start: 0}
        h = [(0, start)]
        while h:
            d, n = heapq.heappop(h)
            if d > dist.get(n, 1 << 30):
                continue
            for m, w in self.adj.get(n, []):
                nd = d + w
                if nd < dist.get(m, 1 << 30):
                    dist[m] = nd
                    heapq.heappush(h, (nd, m))
        return dist

    def of_item(self, item: str, districts: set[str] | None = None) -> list[Instance]:
        return [i for i in self.instances if i.item == item and
                (districts is None or i.district in districts)]


# -- reading the built world ------------------------------------------------------------------

def _set_docs(root: Path, sets: list[str]) -> list[dict]:
    out = []
    for s in sets:
        f = root / f"assets/sets/{s}/catalog.json"
        if f.exists():
            out.append(json.loads(f.read_text()))
    return out


def content_facts(root: Path, sets: list[str]) -> tuple[dict, set, set]:
    """(actor kinds -> animations, goods ids, audio files) from the set catalogs and manifests."""
    kinds: dict[str, set[str]] = {}
    goods: set[str] = set()
    for doc in _set_docs(root, sets):
        for a in doc.get("actors", []):
            anims = a.get("anims", {})
            kinds[a["id"]] = set(anims) if isinstance(anims, dict) else set(anims)
        goods |= {g["id"] for g in doc.get("goods", [])}
    audio: set[str] = set()
    for s in dict.fromkeys(list(sets) + ["home"]):      # home's voices serve the world's animals
        f = root / f"assets/audio/{s}/manifest.json"
        if f.exists():
            for e in json.loads(f.read_text()).get("files", []):
                if (root / "assets/audio" / e["file"]).exists():
                    audio.add(e["file"])
    return kinds, goods, audio


def _graph_labels(g: Graph, walk: np.ndarray, lv: np.ndarray, stair: np.ndarray,
                  rect: tuple[int, int, int, int], slope=None) -> dict[tuple[int, int], str]:
    """Each walkable tile within REACH steps of the graph -> the node a walker reaches first."""
    c0, r0, c1, r1 = rect
    lab: dict[tuple[int, int], str] = {}
    q: deque = deque()
    for e in g.edges:
        a, b = g.node(e.a), g.node(e.b)
        if a is None or b is None:
            continue
        pts = [to_plan(*a.at), *[to_plan(*v) for v in e.via], to_plan(*b.at)]
        course = path_tiles(pts)
        half = len(course) / 2
        for i, t in enumerate(course):
            if t not in lab:
                lab[t] = e.a if i < half else e.b
    for n in g.nodes:
        lab[to_plan(*n.at)] = n.id
    depth = {t: 0 for t in lab}
    q.extend(sorted(lab))
    while q:
        c, r = q.popleft()
        d = depth[(c, r)]
        if d >= REACH:
            continue
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c + dc, r + dr)
            if n in lab or not (c0 - 2 <= n[0] <= c1 + 2 and r0 - 2 <= n[1] <= r1 + 2):
                continue
            if not (0 <= n[0] < COLS and 0 <= n[1] < ROWS) or not walk[n[1], n[0]]:
                continue
            if not landform.step_ok(lv, stair, slope, (c, r), n):
                continue
            lab[n] = lab[(c, r)]
            depth[n] = d + 1
            q.append(n)
    return lab


def region_view(world: World, cat, graphs: dict[str, Graph], root: Path, rid: str,
                layer: str | None = None) -> RegionView:
    """The region as the life data sees it, from the composed world and the committed graphs."""
    from .validate import walk_map  # the walkability rule V5/V7 use
    layer = layer or rid
    kind_, set_, _t, rect, _b = P.REGIONS[rid]
    kinds, goods, audio = content_facts(root, cat.sets)
    walk, stair = walk_map(world, cat)
    slope = landform.slope_tiles(world, cat, root)   # one-level steps by slopes (art §3.2)
    lv = world.L & 0x0F
    g = graphs.get(layer, Graph(layer))
    lab = _graph_labels(g, walk, lv, stair, rect, slope)
    c0, r0, c1, r1 = rect
    slots: dict[str, dict[str, dict]] = {}
    for iid, d in cat.items.items():
        sl = {s["id"]: {"kind": s.get("kind"), "cap": int(s.get("cap", 1))}
              for s in d.extra.get("slots", []) if isinstance(s, dict) and "id" in s}
        if sl:
            slots[iid] = sl
    instances: list[Instance] = []
    landmarks: list[str] = []
    item_cards: dict[str, str] = {}
    for _, it in live_items(world):
        if it.layer != layer:
            continue
        d = cat.items.get(it.id)
        dist = _district_at(world, it, rid)
        inst = Instance(it.id, dist, it.c, it.r, it.pw, it.ph)
        ne_c = it.c + it.pw - 1
        for sid, spots in cat.slots(it.id, it.k).items():
            inst.spots[sid] = [(ne_c - s["t"][1], it.r + s["t"][0]) for s in spots]
        inst.spots["beside"] = [(c, r) for c, r in _ring(it)
                                if 0 <= c < COLS and 0 <= r < ROWS and walk[r, c]]
        for sid, tiles in inst.spots.items():
            post = cat.slot_kind(it.id, sid) == "mooring" and it.pw * it.ph <= 4
            inst.nodes[sid] = _node_for(tiles, lab, walk, inst, post)
        instances.append(inst)
        if d is not None and d.landmark and d.rise == 0:
            landmarks.append(it.id)
        if d is not None and d.card:
            item_cards[it.id] = d.card
    nodes = {n.id: (*to_plan(*n.at), n.kind) for n in g.nodes}
    adj: dict[str, list[tuple[str, int]]] = {}
    for e in g.edges:
        if e.a not in nodes or e.b not in nodes:
            continue
        pts = [to_plan(*g.node(e.a).at), *[to_plan(*v) for v in e.via], to_plan(*g.node(e.b).at)]
        w = max(1, len(path_tiles(pts)) - 1)
        adj.setdefault(e.a, []).append((e.b, w))
        adj.setdefault(e.b, []).append((e.a, w))
    ports = {f"{ln.id}:{p.id}" for ln in g.lanes for p in ln.ports}
    districts: dict[str, dict] = {}
    D = world.D[r0:r1 + 1, c0:c1 + 1]
    W = walk[r0:r1 + 1, c0:c1 + 1]
    for di in sorted(set(np.unique(D).tolist()) - {NONE16}):
        name = world.districts[di]
        if not name.startswith(rid + "/"):
            continue
        m = D == di
        js, is_ = np.nonzero(m)
        chunks: dict[tuple[int, int], int] = {}
        for j, i in zip(js.tolist(), is_.tolist()):
            tx, ty = to_grid(i + c0, j + r0)
            key = (tx // P.CHUNK, ty // P.CHUNK)
            chunks[key] = chunks.get(key, 0) + 1
        districts[name.split("/", 1)[1]] = {
            "tiles": int(m.sum()), "walk": int((m & W).sum()), "chunks": chunks,
            "bbox": (int(is_.min()) + c0, int(js.min()) + r0, int(is_.max()) + c0,
                     int(js.max()) + r0)}
    return RegionView(rid, kinds, goods, audio, slots, instances, nodes, adj, ports, districts,
                      sorted(set(landmarks)), dict(sorted(item_cards.items())), layer)


def _ring(it):
    for c in range(it.c - 1, it.c + it.pw + 1):
        yield c, it.r - 1
        yield c, it.r + it.ph
    for r in range(it.r, it.r + it.ph):
        yield it.c - 1, r
        yield it.c + it.pw, r


def _district_at(world: World, it, rid: str) -> str:
    for c, r in [(it.c, it.r), *_ring(it)]:
        if 0 <= c < COLS and 0 <= r < ROWS and world.D[r, c] != NONE16:
            name = world.districts[int(world.D[r, c])]
            if name.startswith(rid + "/"):
                return name.split("/", 1)[1]
    return ""


def _node_for(tiles, lab, walk, inst, post: bool = False) -> str | None:
    for c, r in tiles:
        if (c, r) in lab:
            return lab[(c, r)]
        # A spot on the item's own tile is used from the walkable tile beside it (V7's rule).
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (c + dc, r + dr) in lab:
                return lab[(c + dc, r + dr)]
    if post:
        # A boat moored off a quay post is worked from the quay beside the post (V7's rule for
        # `mooring` slots): the spot itself is water, the post's own tile is not walkable.
        for t in inst.spots.get("beside", []):
            if t in lab:
                return lab[t]
    return None


# -- reading the life data ---------------------------------------------------------------------

def hour_of(s: str) -> float:
    h, m = s.split(":")
    return int(h) + int(m) / 60


def in_hours(hours, h: float) -> bool:
    a, b = hour_of(hours[0]), hour_of(hours[1])
    return a <= h < b if a <= b else (h >= a or h < b)


def _as_list(v) -> list:
    return v if isinstance(v, list) else [v]


def filters_pass(f: dict, h: float, day: int, season: str, festivals: set[str]) -> bool:
    """A filter (`hours`, `days`, `season`, `months`, `festival`, `not_festival`, `weather`) on
    calendar day `day` (its month is `day mod 12`) in `season`."""
    if "hours" in f and not in_hours(f["hours"], h):
        return False
    if "days" in f:
        d = f["days"]
        if day % d["every"] != d.get("offset", 0) % d["every"]:
            return False
    if "season" in f and season not in _as_list(f["season"]):
        return False
    if "months" in f and SEAS.month_of(day) not in f["months"]:
        return False
    if "festival" in f and f["festival"] not in festivals:
        return False
    if "not_festival" in f and f["not_festival"] in festivals:
        return False
    if f.get("weather") not in (None, "clear"):
        return False
    return True


def block_at(role: dict, h: float, day: int, season: str, festivals: set[str]) -> dict | None:
    for b in role.get("schedule", []):
        if filters_pass(b, h, day, season, festivals):
            return b
    return None


def walk_steps(steps, routines: dict, seen: tuple = ()):
    """Every step of a routine, depth first, through pick, if, each and routine calls."""
    for s in steps:
        yield s
        if "pick" in s:
            for opt in s["pick"]:
                if "steps" in opt:
                    yield from walk_steps(opt["steps"], routines, seen)
                elif "routine" in opt and opt["routine"] not in seen and opt["routine"] in routines:
                    yield from walk_steps(routines[opt["routine"]]["steps"], routines,
                                          seen + (opt["routine"],))
                else:
                    yield opt
        if "if" in s:
            yield from walk_steps(s.get("do", []), routines, seen)
            yield from walk_steps(s.get("else", []), routines, seen)
        if "each" in s:
            yield from walk_steps(s.get("do", []), routines, seen)
        if "routine" in s and s["routine"] not in seen and s["routine"] in routines:
            yield from walk_steps(routines[s["routine"]]["steps"], routines, seen + (s["routine"],))


def _mean(v) -> float:
    return (v[0] + v[1]) / 2 if isinstance(v, list) else float(v)


def step_seconds(s: dict) -> float:
    if "go" in s:
        return GO_SECONDS
    if any(k in s for k in ("use", "wait", "wander", "enter", "follow")):
        if "dur" in s:
            return _mean(s["dur"])
        inner = s.get("wait") if isinstance(s.get("wait"), dict) else {}
        if "dur" in inner:
            return _mean(inner["dur"])
        return LONG_SECONDS
    return 1.0


def routine_shares(routine_id: str, routines: dict, seen=()) -> list[tuple[dict, dict | None, float]]:
    """(step, the target it acts at, share of the routine's time) for each acting step. A `use`
    or `wait` at `here` acts at the target of the `go` before it."""
    out: list[tuple[dict, dict | None, float]] = []
    r = routines.get(routine_id)
    if r is None or routine_id in seen:
        return out

    def flat(steps, weight, last):
        for s in steps:
            if "go" in s:
                last = s["go"]
                out.append((s, s["go"], step_seconds(s) * weight))
            elif "use" in s:
                t = s["use"]
                tgt = last if t.get("here") else t
                out.append((s, tgt, step_seconds(s) * weight))
            elif "pick" in s:
                opts = s["pick"]
                tot = sum(o.get("weight", 1) for o in opts) or 1
                start = last
                for o in opts:
                    w = weight * o.get("weight", 1) / tot
                    if "steps" in o:
                        flat(o["steps"], w, start)
                    elif "routine" in o:
                        for st, tg, sec in routine_shares(o["routine"], routines,
                                                          seen + (routine_id,)):
                            out.append((st, tg, sec * w))
                    else:
                        tgt = o.get("at") or o.get("use")
                        out.append((o, tgt, step_seconds(o) * w))
                last = None   # which option ran is not known after the pick
            elif "if" in s:
                last = flat(s.get("do", []), weight, last)
            elif "each" in s:
                last = flat(s.get("do", []), weight * s["each"].get("max", 3), last)
            elif "routine" in s:
                for st, tg, sec in routine_shares(s["routine"], routines, seen + (routine_id,)):
                    out.append((st, tg, sec * weight))
            else:
                if "wander" in s:
                    last = None   # it has walked away from the last target
                out.append((s, last if s.get("wait") else None, step_seconds(s) * weight))
        return last

    flat(r.get("steps", []), 1.0, None)
    tot = sum(sec for _, _, sec in out) or 1.0
    return [(s, t, sec / tot) for s, t, sec in out]


def routine_visible(routine_id: str, routines: dict) -> bool:
    """False when the routine puts the actor indoors for its block (an `enter` held `until`)."""
    r = routines.get(routine_id, {})
    return not any("enter" in s and "until" in s for s in r.get("steps", []))


def roles_by_id(doc: dict) -> dict[str, dict]:
    return {r["id"]: r for r in doc.get("roles", [])}


def festival_on(f: dict, day: int) -> bool:
    """A calendar entry on calendar day `day`: by its `months`, else its `season` and season
    `day` (counted from 1; no day: every day of the season)."""
    if "months" in f:
        return SEAS.month_of(day) in f["months"]
    return f.get("season") in (None, SEAS.season_of(day)) and \
        f.get("day") in (None, SEAS.season_day(day))


def festivals_on(doc: dict, day: int) -> set[str]:
    """Festivals on calendar day `day`."""
    return {f["id"] for f in doc.get("festivals", []) if festival_on(f, day)}


def season_of(day: int) -> str:
    return SEAS.season_of(day)


def area_of(d: dict, day: int) -> str:
    """A district's area kind on calendar day `day`: its `seasonal_area` in those months (a
    terrace whose court is away is a working place, not a crowd), else its `area`."""
    sa = d.get("seasonal_area")
    if sa and SEAS.month_of(day) in sa.get("months", []):
        return sa["area"]
    return d.get("area", "town")


def population(doc: dict, view: RegionView, h: float, day: int, season: str,
               festivals: set[str]) -> dict[str, dict[str, float]]:
    """district -> role -> actors present at hour h (fractional; the engine rounds by hash)."""
    out: dict[str, dict[str, float]] = {}
    dens = doc.get("densities", {})
    for d in doc.get("districts", []):
        info = view.districts.get(d["id"])
        if info is None:
            continue
        row = out.setdefault(d["id"], {})
        for p in d.get("populations", []):
            if not filters_pass(p.get("when", {}), h, day, season, festivals):
                continue
            curve = dens.get(p.get("density", "always"), [1.0] * 24)
            f = curve[int(h) % 24]
            if "per_item" in p:
                n = len(view.of_item(p["per_item"], {d["id"]})) * p.get("count", 1) * f
            else:
                n = f * p.get("max_per_chunk", 0) * info["tiles"] / CHUNK_TILES
            key = p.get("role") or p.get("actor")
            row[key] = row.get(key, 0.0) + n
    return out


# -- checks ------------------------------------------------------------------------------------

def check(doc: dict, view: RegionView, sim=None) -> list[Problem]:
    """Every check on one region document; `sim` overrides the chain simulator (tests)."""
    out: list[Problem] = []
    rid = doc.get("id", view.region)

    def bad(code, where, msg, level="error"):
        out.append(Problem(code, level, f"{rid}: {where}", msg))

    roles = roles_by_id(doc)
    _check_refs(doc, view, roles, bad)
    _check_reach_and_capacity(doc, view, roles, bad)
    _check_chains(doc, view, roles, bad, sim)
    _check_populations(doc, view, roles, bad)
    _check_cards(doc, view, bad)
    _check_names(doc, rid, bad)
    _check_events(doc, bad)
    _check_sound_and_look(doc, view, bad)
    return out


def _check_sound_and_look(doc, view, bad):
    """L9 sound: every audio file and family a region names is in a manifest; no event,
    working role or populated district is silent. L10 look: `theme.look` and district looks
    have their fields, in range."""
    from . import look, places, sound
    _files, families = sound.manifests(Path(__file__).resolve().parents[3])
    for level, where, msg in sound.check(doc, view.audio, families):
        bad("L9", where, msg, level)
    for level, where, msg in look.check(doc):
        bad("L10", where, msg, level)
    for level, where, msg in places.check(doc):
        bad("L11", where, msg, level)


def _kind_of(doc: dict, roles: dict, key: str) -> str | None:
    if key in roles:
        return roles[key].get("actor")
    return key if "." in key else None


def _check_refs(doc, view, roles, bad):
    pending = doc.get("pending", {}).get("goods", {})
    for g, stand in pending.items():
        if g in view.goods:
            bad("L1", f"pending goods {g}", "exists in a catalog now: drop it from `pending`",
                "warning")
        elif stand not in view.goods:
            bad("L1", f"pending goods {g}", f"stand-in {stand!r} is not in any catalog")

    def goods_ok(where, g):
        if g not in view.goods and g not in pending:
            bad("L1", where, f"goods {g!r} is in no catalog (and not pending with a stand-in)")

    dens = doc.get("densities", {})
    for name, curve in dens.items():
        if len(curve) != 24 or any(not 0 <= v <= 1 for v in curve):
            bad("L1", f"density {name}", "needs 24 values in 0..1")
    groups = {g["id"] for g in doc.get("groups", [])}
    cards = doc.get("cards", {})
    known_d = set(view.districts)
    for d in doc.get("districts", []):
        if d["id"] not in known_d:
            bad("L1", f"district {d['id']}", "is not a district of the region's layer")
        if d.get("area") not in AREA:
            bad("L1", f"district {d['id']}", f"area {d.get('area')!r} is not one of {sorted(AREA)}")
        for p in d.get("populations", []):
            key = p.get("role") or p.get("actor")
            kind = _kind_of(doc, roles, key or "")
            if kind is None or kind not in view.kinds:
                bad("L1", f"district {d['id']}", f"population {key!r}: no such role or actor kind")
            if "density" in p and p["density"] not in dens:
                bad("L1", f"district {d['id']}", f"density {p['density']!r} is not defined")
            if "per_item" in p and p["per_item"] not in view.slots and \
                    not view.of_item(p["per_item"]):
                bad("L1", f"district {d['id']}", f"per_item {p['per_item']!r} is not placed")
    for d in sorted(known_d - {x["id"] for x in doc.get("districts", [])}):
        bad("L1", f"district {d}", "has no entry in the region file (who is there?)")
    for r in doc.get("roles", []):
        where = f"role {r['id']}"
        kind = r.get("actor")
        anims = view.kinds.get(kind)
        if anims is None:
            bad("L1", where, f"actor kind {kind!r} is in no set catalog")
            continue
        routines = r.get("routines", {})
        for b in r.get("schedule", []) + r.get("interrupts", []):
            ids = [b["routine"]] if "routine" in b else [o["routine"] for o in b.get("pick", [])]
            for rt in ids:
                if rt not in routines:
                    bad("L1", where, f"schedule names routine {rt!r}, which it does not define")
        for rid_, rt in routines.items():
            for s in walk_steps(rt.get("steps", []), routines):
                _check_step(s, f"{where}.{rid_}", anims, view, doc, roles, groups, goods_ok, bad)
        if "home" in r:
            _check_target(r["home"], f"{where} home", view, doc, roles, bad)
        if r.get("card") and r["card"] not in cards:
            bad("L1", where, f"card {r['card']!r} is missing")
    for g in doc.get("groups", []):
        for m in [g.get("leader", {})] + g.get("members", []):
            key = m.get("role") or m.get("actor")
            kind = _kind_of(doc, roles, key or "")
            if kind not in view.kinds:
                bad("L1", f"group {g['id']}", f"member {key!r}: no such role or actor kind")
            if "carry" in m:
                goods_ok(f"group {g['id']}", m["carry"])
    for f in doc.get("figures", []):
        if f.get("actor") and f["actor"] not in view.kinds:
            bad("L1", f"figure {f.get('card')}", f"actor {f['actor']!r} is in no set catalog")
        if f.get("card") not in cards:
            bad("L1", f"figure {f.get('actor')}", f"card {f.get('card')!r} is missing")
        anims = view.kinds.get(f.get("actor"), set())
        routines = f.get("routines", {})
        for b in f.get("schedule", []):
            if b.get("routine") not in routines:
                bad("L1", f"figure {f.get('card')}", f"schedule names routine {b.get('routine')!r}")
        for rid_, rt in routines.items():
            for s in walk_steps(rt.get("steps", []), routines):
                _check_step(s, f"figure {f.get('card')}.{rid_}", anims, view, doc, roles, groups,
                            goods_ok, bad)
    for e in doc.get("events", []):
        where = f"event {e['id']}"
        for n in e.get("route", []):
            if not view.has_node(n):
                bad("L1", where, f"route node {n!r} is not in the region's graph")
        for c in e.get("cast", []):
            for g in c.get("rotate", []):
                if g not in groups:
                    bad("L1", where, f"rotation names group {g!r}, which is not defined")
            if "rotate" in c:
                continue
            if "group" in c:
                if c["group"] not in groups:
                    bad("L1", where, f"cast group {c['group']!r} is not defined")
            else:
                key = c.get("role") or c.get("actor")
                if _kind_of(doc, roles, key or "") not in view.kinds:
                    bad("L1", where, f"cast {key!r}: no such role or actor kind")
        for k in ("sfx",):
            if k in e and e[k] not in view.audio:
                bad("L1", where, f"sound {e[k]!r} is not in the audio manifests")
        if "ambience" in e and e["ambience"]["file"] not in view.audio:
            bad("L1", where, f"ambience {e['ambience']['file']!r} is not in the audio manifests")
        for s in walk_steps(e.get("steps", []), {}):
            _check_step(s, where, None, view, doc, roles, groups, goods_ok, bad)
        if e.get("card") and e["card"] not in cards:
            bad("L1", where, f"card {e['card']!r} is missing")
        trig = e.get("trigger", {})
        if trig.get("festival") and trig["festival"] not in {f["id"] for f in doc.get("festivals", [])}:
            bad("L1", where, f"festival {trig['festival']!r} is not in the calendar")
    th = doc.get("theme", {})
    amb = th.get("ambience", {})
    for b in amb.get("beds", []) + amb.get("zones", []) + amb.get("loops", []):
        if b["file"] not in view.audio:
            bad("L1", "theme", f"ambience {b['file']!r} is not in the audio manifests")
    for d in doc.get("districts", []):
        for b in d.get("theme", {}).get("beds", []):
            if b["file"] not in view.audio:
                bad("L1", f"district {d['id']}", f"bed {b['file']!r} is not in the manifests")
    for k in ("day", "night"):
        f = th.get("music", {}).get(k)
        if f and f not in view.audio:
            bad("L1", "theme", f"music {f!r} is not in the audio manifests")
    for c in doc.get("chains", []):
        for st in c.get("stages", []):
            for k in ("makes", "needs", "sink", "carry"):
                if k in st:
                    goods_ok(f"chain {c['id']}", st[k])
            if _kind_of(doc, roles, st.get("by", "")) not in view.kinds:
                bad("L1", f"chain {c['id']}", f"stage by {st.get('by')!r}: no such role or kind")
            for k in ("slot", "from", "to"):
                if k in st:
                    _check_slot_ref(st[k], f"chain {c['id']}", view, bad)


def _check_slot_ref(ref: str, where: str, view, bad):
    if ref.startswith(("node:", "portal:")):
        if ref.split(":", 1)[1] not in view.nodes:
            bad("L1", where, f"{ref!r}: no such node")
        return
    item, _, slot = ref.rpartition(".")
    if not view.of_item(item):
        bad("L1", where, f"{ref!r}: item {item!r} is not placed in the region")
    elif slot != "beside" and slot not in view.slots.get(item, {}):
        bad("L1", where, f"{ref!r}: {item} has no slot {slot!r}")


def _check_target(t: dict, where: str, view, doc, roles, bad):
    if not isinstance(t, dict):
        return
    if "item" in t:
        if not view.of_item(t["item"]):
            bad("L1", where, f"item {t['item']!r} is not placed in the region")
            return
        slot = t.get("slot") or ("beside" if t.get("spot") == "beside" else None)
        if slot and slot != "beside" and slot not in view.slots.get(t["item"], {}):
            bad("L1", where, f"{t['item']} has no slot {slot!r}")
    if "node" in t and not view.has_node(t["node"]):
        bad("L1", where, f"node {t['node']!r} is not in the region's graph")
    if "zone" in t and t["zone"] not in view.districts:
        bad("L1", where, f"zone {t['zone']!r} is not a district of the region")
    if "port" in t and not any(p.endswith(":" + t["port"]) for p in view.ports):
        bad("L1", where, f"port {t['port']!r} is on no lane of the region")
    if "slot_kind" in t and not any(s["kind"] == t["slot_kind"] for it in view.slots.values()
                                    for s in it.values()):
        bad("L1", where, f"no item has slots of kind {t['slot_kind']!r}")
    if "actor" in t and _kind_of(doc, roles, t["actor"]) not in view.kinds:
        bad("L1", where, f"actor {t['actor']!r} is unknown")
    if "else" in t:
        _check_target(t["else"], where, view, doc, roles, bad)


def _check_step(s, where, anims, view, doc, roles, groups, goods_ok, bad):
    verbs = [k for k in STEP_VERBS if k in s]
    if not verbs and not ("at" in s or "id" in s):
        bad("L1", where, f"step {json.dumps(s)[:60]} has no verb")
    for v in TARGET_STEPS:
        if v in s:
            _check_target(s[v], where, view, doc, roles, bad)
    if "at" in s:
        _check_target(s["at"], where, view, doc, roles, bad)
    if "anim" in s and anims is not None and s["anim"] not in anims:
        bad("L1", where, f"animation {s['anim']!r} is not one the actor kind has {sorted(anims)}")
    for k in ("take", "put"):
        if k in s:
            goods_ok(where, s[k])
            if anims is not None and k == "take" and "carry" not in anims:
                bad("L1", where, "takes goods but its kind has no `carry` animation")
    for k in ("make", "need"):
        if k in s:
            goods_ok(where, s[k])
    if "emit" in s and "sfx" in s["emit"] and s["emit"]["sfx"] not in view.audio:
        bad("L1", where, f"sound {s['emit']['sfx']!r} is not in the audio manifests")
    if "say" in s:
        bad("L1", where, "`say` is for the resident only")
    if "follow" in s and "group" in s["follow"] and s["follow"]["group"] not in groups:
        bad("L1", where, f"follows unknown group {s['follow']['group']!r}")


def _role_districts(doc, role_id) -> set[str]:
    return {d["id"] for d in doc.get("districts", []) for p in d.get("populations", [])
            if p.get("role") == role_id}


def _candidates(view: RegionView, t: dict, role: dict, homes: set[str]) -> list[tuple[Instance, str]]:
    """(instance, slot) pairs a target may resolve to, scoped to the role's districts when the
    target says `within` (or `district`)."""
    if not isinstance(t, dict):
        return []
    scope = None
    if "district" in t:
        scope = {t["district"]}
    if "home" in t:
        h = role.get("home", {})
        item = h.get("item")
        slot = t["home"] if isinstance(t["home"], str) else h.get("slot")
        return [(i, slot) for i in view.of_item(item, scope or homes or None)] if item else []
    if "item" in t:
        slot = t.get("slot") or ("beside" if t.get("spot") == "beside" else "beside")
        insts = view.of_item(t["item"], scope)
        if "within" in t and homes:
            boxes = [view.districts[d]["bbox"] for d in homes if d in view.districts]
            R = t["within"]
            insts = [i for i in insts if any(b[0] - R <= i.c <= b[2] + R and
                                             b[1] - R <= i.r <= b[3] + R for b in boxes)]
        return [(i, slot) for i in insts]
    if "slot_kind" in t:
        out = []
        for i in view.instances:
            if scope and i.district not in scope:
                continue
            for sid, s in view.slots.get(i.item, {}).items():
                if s["kind"] == t["slot_kind"]:
                    out.append((i, sid))
        if "within" in t and homes:
            boxes = [view.districts[d]["bbox"] for d in homes if d in view.districts]
            R = t["within"]
            out = [(i, s) for i, s in out if any(b[0] - R <= i.c <= b[2] + R and
                                                 b[1] - R <= i.r <= b[3] + R for b in boxes)]
        return out
    return []


def _start_nodes(view, role, homes) -> set[int]:
    """Graph components the role's actors start in: its home's or its districts' nodes."""
    comps = set()
    h = role.get("home", {})
    if "item" in h:
        for i in view.of_item(h["item"], homes or None):
            n = i.nodes.get(h.get("slot", "beside")) or i.nodes.get("beside")
            if n:
                comps.add(view.component(n))
    if "node" in h and h["node"] in view.nodes:
        comps.add(view.component(h["node"]))
    if not comps:
        for nid, (c, r, _k) in view.nodes.items():
            for d in homes:
                b = view.districts.get(d, {}).get("bbox")
                if b and b[0] <= c <= b[2] and b[1] <= r <= b[3]:
                    comps.add(view.component(nid))
    return comps


def _check_reach_and_capacity(doc, view, roles, bad):
    for r in doc.get("roles", []):
        homes = _role_districts(doc, r["id"])
        start = _start_nodes(view, r, homes)
        routines = r.get("routines", {})
        seen_targets = set()
        for rt in routines.values():
            for s in walk_steps(rt.get("steps", []), routines):
                for v in TARGET_STEPS + ("at",):
                    t = s.get(v)
                    if not isinstance(t, dict) or not any(k in t for k in ("item", "home", "slot_kind")):
                        continue
                    key = json.dumps(t, sort_keys=True)
                    if key in seen_targets:
                        continue
                    seen_targets.add(key)
                    cands = _candidates(view, t, r, homes)
                    if not cands:
                        bad("L2", f"role {r['id']}", f"target {key} has no instance in reach of "
                            f"{sorted(homes) or 'its home'}")
                        continue
                    reach = [(i, s_) for i, s_ in cands
                             if i.nodes.get(s_) and (not start or
                                                     view.component(i.nodes[s_]) in start)]
                    if not reach:
                        bad("L2", f"role {r['id']}", f"target {key}: none of its {len(cands)} "
                            "slot(s) can be reached on the path graph from where it starts")
    # L3: expected occupancy of each slot pool at every hour of every week day.
    for day in range(WEEK_CYCLE):
        fest = festivals_on(doc, day)
        season = season_of(day)
        for h in range(24):
            pop = population(doc, view, h + 0.5, day, season, fest)
            demand: dict[str, float] = {}
            cap: dict[str, int] = {}
            for dist, row in pop.items():
                for role_id, n in row.items():
                    r = roles.get(role_id)
                    if r is None or n <= 0:
                        continue
                    b = block_at(r, h + 0.5, day, season, fest)
                    if b is None:
                        continue
                    picks = [(b["routine"], 1.0)] if "routine" in b else \
                        [(o["routine"], o.get("weight", 1)) for o in b.get("pick", [])]
                    tot = sum(w for _, w in picks) or 1
                    for rt, w in picks:
                        for s, t, share in routine_shares(rt, r.get("routines", {})):
                            if "use" not in s and not ("at" in s) or not isinstance(t, dict):
                                continue
                            cands = _candidates(view, t, r, {dist})
                            pool = [(i, sid) for i, sid in cands if sid != "beside"]
                            if not pool:
                                continue
                            key = "|".join(sorted({f"{i.item}.{sid}" for i, sid in pool})) + \
                                ("@" + dist if "within" in t or "home" in t else "")
                            demand[key] = demand.get(key, 0.0) + n * share * w / tot
                            cap[key] = sum(view.slots.get(i.item, {}).get(sid, {}).get("cap", 1)
                                           for i, sid in pool)
            for key, need in sorted(demand.items()):
                if need > cap[key] + 1e-6:
                    bad("L3", f"day {day} {h:02d}:30", f"slots {key} need {need:.1f} places, "
                        f"they have {cap[key]}")


def chain_factor(c: dict, day: int) -> float:
    """How hard a chain works on calendar day `day`: 0 outside its `months` or `season`, else its
    `by_month` factor (its period is divided by it)."""
    if "months" in c and SEAS.month_of(day) not in c["months"]:
        return 0.0
    if "season" in c and season_of(day) not in _as_list(c["season"]):
        return 0.0
    return float(c.get("by_month", [1.0] * 12)[day % 12])


def present(doc: dict, role_id: str, day: int, h: float, festivals: set[str]) -> bool:
    """Some district holds the role at hour h of calendar day `day`."""
    for d in doc.get("districts", []):
        for p in d.get("populations", []):
            if p.get("role") == role_id and \
                    filters_pass(p.get("when", {}), h, day, season_of(day), festivals):
                return True
    return False


def _check_chains(doc, view, roles, bad, sim):
    from . import lifesim
    run = sim or lifesim.simulate
    for c in doc.get("chains", []):
        where = f"chain {c['id']}"
        st = c.get("stages", [])
        if not st:
            bad("L4", where, "has no stages")
            continue
        have: set[str] = set()
        for i, s in enumerate(st):
            need = s.get("needs") or s.get("carry") or s.get("sink")
            if i == 0 and "makes" not in s:
                bad("L4", where, "the first stage must make something (a rate-limited source)")
            if need and i > 0 and need not in have:
                bad("L4", where, f"stage {i} needs {need!r}, which no stage before it makes")
            if "makes" in s:
                have.add(s["makes"])
            if "carry" in s:
                have.add(s["carry"])
        if "sink" not in st[-1]:
            bad("L4", where, "the last stage must be a sink, where the goods are visibly used")
        if len(c.get("by_month", [1] * 12)) != 12:
            bad("L4", where, "by_month needs twelve factors (March first)")
            continue
        hours = c.get("hours", ["06:00", "18:00"])
        days = [d for d in range(WEEK_CYCLE) if chain_factor(c, d) > 0]
        if not days:
            bad("L4", where, "never runs: no month of the year has it")
            continue
        # Its workers are out in its hours on every day it runs (seasonal work included).
        for s in st:
            r = roles.get(s.get("by"))
            if r is None or (c.get("event") and not r.get("schedule")):
                continue   # cast by the chain's event, which keeps their hours
            placed = _role_districts(doc, r["id"])   # chain-only workers are the chain's puppets
            for d in days:
                # Festivals aside (a holiday rests the chain with its workers): who works in
                # this month at all?
                ok = any((not placed or present(doc, r["id"], d, h + 0.5, set())) and
                         block_at(r, h + 0.5, d, season_of(d), set()) is not None and
                         routine_visible((block_at(r, h + 0.5, d, season_of(d), set()) or {})
                                         .get("routine", ""), r.get("routines", {}))
                         for h in range(24) if in_hours(hours, h + 0.5))
                if not ok:
                    bad("L4", where, f"stage worker {s['by']!r} is not out at work in the "
                        f"chain's hours {hours} in {SEAS.month_of(d)} ({season_of(d)}), when "
                        "the chain runs")
                    break
        # The week-long simulation at every pace the chain keeps through the year.
        paces: dict[float, list[str]] = {}
        for d in days:
            paces.setdefault(chain_factor(c, d), []).append(SEAS.month_of(d))
        for f, ms in sorted(paces.items()):
            if f != 1.0:
                res = run(dict(c, period=c["period"] / f), view, roles, days=6, warmup=2)
            else:
                res = run(c, view, roles)
            for msg in res.get("errors", []):
                bad("L4", where, msg + ("" if len(paces) == 1 else
                                        f" (at {f:g} pace, {', '.join(ms)})"))


def _check_populations(doc, view, roles, bad):
    for day in range(WEEK_CYCLE):
        fest = festivals_on(doc, day)
        season = season_of(day)
        area = {d["id"]: area_of(d, day) for d in doc.get("districts", [])}
        for h in range(24):
            pop = population(doc, view, h + 0.5, day, season, fest)
            chunk_tot: dict[tuple[int, int], float] = {}
            for dist, row in pop.items():
                info = view.districts[dist]
                a = AREA.get(area.get(dist, "town"), AREA["town"])
                vis = 0.0
                total = 0.0
                for role_id, n in row.items():
                    total += n
                    r = roles.get(role_id)
                    b = block_at(r, h + 0.5, day, season, fest) if r else {"routine": ""}
                    if r is None or b is None:
                        continue
                    rt = b.get("routine") or (b.get("pick") or [{}])[0].get("routine", "")
                    if routine_visible(rt, r.get("routines", {})):
                        vis += n
                for ck, wt in info["chunks"].items():
                    chunk_tot[ck] = chunk_tot.get(ck, 0.0) + total * wt / max(1, info["tiles"])
                per_chunk = total * CHUNK_TILES / max(1, info["tiles"])
                cap_chunk = a["cap"] * CHUNK_TILES / SCREEN_TILES
                if per_chunk > cap_chunk + 1e-6:
                    bad("L5", f"district {dist} day {day} {h:02d}:30",
                        f"{per_chunk:.0f} actors per chunk, the cap for {area.get(dist)} is "
                        f"{cap_chunk:.0f}")
                screen = screen_movers(info, vis)
                if screen > a["cap"] + 1e-6:
                    bad("L5", f"district {dist} day {day} {h:02d}:30",
                        f"{screen:.0f} movers per screenful, over the cap {a['cap']}")
                night = h >= 23 or h < 4
                if night and screen > a["night"] + 1e-6:
                    bad("L5", f"district {dist} day {day} {h:02d}:30",
                        f"{screen:.0f} movers per screenful at night, over {a['night']}")
                if any(lo <= h < hi for lo, hi in a["active"]) and screen + 1e-6 < a["min"]:
                    bad("L5", f"district {dist} day {day} {h:02d}:30",
                        f"only {screen:.1f} movers per screenful in a busy hour, the minimum for "
                        f"{area.get(dist)} is {a['min']}")
            keys = sorted(chunk_tot)
            for (cx, cy) in keys:
                block = sum(v for (x, y), v in chunk_tot.items()
                            if cx <= x < cx + LIVE_BLOCK and cy <= y < cy + LIVE_BLOCK)
                if block > LIVE_ACTORS:
                    # A warning: living-world §1.1's minimums over a dense core (most of a 3 x 3
                    # window busy) need more than §7.5's live budget; the engine round decides.
                    bad("L5", f"chunks from ({cx}, {cy}) day {day} {h:02d}:30",
                        f"{block:.0f} actors in a {LIVE_BLOCK} x {LIVE_BLOCK} live window, over "
                        f"{LIVE_ACTORS}", "warning")
                    break


def screen_movers(info: dict, visible: float) -> float:
    """Movers with purpose in a screenful of a district holding `visible` people out of doors."""
    return visible * MOVING * SCREEN_TILES / max(1, info["tiles"])


def words(text: str) -> int:
    return len(re.findall(r"[\w'’\-]+", text))


def _check_cards(doc, view, bad):
    cards = doc.get("cards", {})
    for cid, c in sorted(cards.items()):
        kind = c.get("kind")
        if kind not in CARD_WORDS:
            bad("L6", f"card {cid}", f"kind {kind!r} is not one of {sorted(CARD_WORDS)}")
            continue
        for k in ("title", "text"):
            if not c.get(k):
                bad("L6", f"card {cid}", f"has no {k}")
        if kind in ("figure", "landmark") and not c.get("epithet"):
            bad("L6", f"card {cid}", "has no epithet")
        lo, hi = CARD_WORDS[kind]
        n = words(c.get("text", ""))
        if not lo <= n <= hi:
            bad("L6", f"card {cid}", f"{n} words; a {kind} card has {lo}-{hi}")
    for f in doc.get("figures", []):
        c = cards.get(f.get("card"))
        if c and c.get("kind") != "figure":
            bad("L6", f"figure {f.get('card')}", "its card must be of kind `figure`")
    for lm in view.landmarks:
        short = lm.split(".", 1)[1]
        if short not in cards:
            bad("L6", f"landmark {lm}", f"has no card {short!r}")
    for item, cid in view.item_cards.items():
        if cid not in cards:
            bad("L6", f"item {item}", f"its catalog names card {cid!r}, which is missing")
    for cid in doc.get("delegations", []):
        if cid not in cards:
            bad("L6", f"delegation {cid}", "has no card")


def _texts(doc):
    for cid, c in doc.get("cards", {}).items():
        for k in ("title", "epithet", "text"):
            if c.get(k):
                yield f"card {cid}.{k}", cid, c[k]
    for k, v in doc.get("strings", {}).items():
        yield f"string {k}", None, v
    for r in doc.get("roles", []):
        yield f"role {r['id']}.name", None, r.get("name", "")
        for rt in r.get("routines", {}).values():
            for s in walk_steps(rt.get("steps", []), r.get("routines", {})):
                if "label" in s:
                    yield f"role {r['id']} label", None, s["label"]
    if doc.get("caption"):
        yield "caption", None, doc["caption"]
    era = doc.get("era")
    for k, v in ((era or {}).items() if isinstance(era, dict) else [("edge", era)]):
        if isinstance(v, str) and v:
            yield f"era.{k}", None, v
    if doc.get("moment", {}).get("caption"):
        yield "moment.caption", None, doc["moment"]["caption"]


def _check_names(doc, rid, bad):
    retired = RETIRED.get(rid, {})
    spelling = SPELLING.get(rid, {})
    for where, cid, text in _texts(doc):
        for name, allowed in retired.items():
            if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I) and cid not in allowed:
                bad("L7", where, f"uses the retired name {name!r}")
        for wrong, right in spelling.items():
            if re.search(r"(?<![\w-])" + re.escape(wrong) + r"(?![\wāšθçūṛēī])", text):
                bad("L7", where, f"writes {wrong!r}; the region's form is {right!r}")
        for us, uk in AMERICAN.items():
            if re.search(r"(?<!\w)" + us + r"(s|ed|ing)?(?!\w)", text, re.I):
                bad("L7", where, f"American spelling {us!r}; write {uk!r}")


def event_window(e) -> tuple[float, float]:
    t = e.get("trigger", {})
    hrs = t.get("hours") or e.get("hours") or ["00:00", "24:00"]
    a = hour_of(hrs[0])
    b = hour_of(hrs[1]) if hrs[1] != "24:00" else 24.0
    dur = max(e.get("duration", [0, 0])) / 30.0   # 30 real seconds per game hour
    if b < a:
        b += 24
    return a, b + dur


def event_on_day(doc: dict, e: dict, day: int, fest: set[str] | None = None) -> bool:
    """Whether an event's trigger allows it on calendar day `day` (its festival, season, months,
    week days and festival exclusions; chance and hours aside)."""
    t = e.get("trigger", {})
    fest = festivals_on(doc, day) if fest is None else fest
    if t.get("festival") and t["festival"] not in fest:
        return False
    if t.get("not_festival") and t["not_festival"] in fest:
        return False
    if t.get("season") and season_of(day) not in _as_list(t["season"]):
        return False
    if t.get("months") and SEAS.month_of(day) not in t["months"]:
        return False
    if "days" in t and day % t["days"]["every"] != t["days"].get("offset", 0) % t["days"]["every"]:
        return False
    if t.get("on") == "season_turn" and season_day(day) != 1 and not t.get("months"):
        return False
    return True


def season_day(day: int) -> int:
    return SEAS.season_day(day)


def _check_events(doc, bad):
    ev = [e for e in doc.get("events", []) if e.get("route")]
    days = {e["id"]: {d for d in range(WEEK_CYCLE) if event_on_day(doc, e, d)} for e in ev}
    for i, a in enumerate(ev):
        for b in ev[i + 1:]:
            ra, rb = a["route"], b["route"]
            pa = {(ra[k], ra[k + 1]) for k in range(len(ra) - 1)}
            pa |= {(y, x) for x, y in pa}
            shared = [(rb[k], rb[k + 1]) for k in range(len(rb) - 1) if (rb[k], rb[k + 1]) in pa]
            if not shared:
                continue
            (a0, a1), (b0, b1) = event_window(a), event_window(b)
            overlap = (a0 < b1 and b0 < a1) or (a0 < b1 - 24 and b0 - 24 < a1) or \
                (a0 - 24 < b1 and b0 < a1 - 24)
            # An event that runs past midnight meets the next day's events too.
            da, db = days[a["id"]], days[b["id"]]
            late = (a1 > 24 and {(d + 1) % WEEK_CYCLE for d in da} & db) or \
                (b1 > 24 and {(d + 1) % WEEK_CYCLE for d in db} & da)
            if overlap and (da & db or late):
                bad("L8", f"events {a['id']} / {b['id']}",
                    f"can hold the same route ({shared[0][0]} - {shared[0][1]}) at the same time")


def report_lines(problems: list[Problem]) -> list[str]:
    errs = [p for p in problems if p.level == "error"]
    warns = [p for p in problems if p.level != "error"]
    return [f"{len(errs)} error(s), {len(warns)} warning(s)"] + \
        [f"{n:3}. {p.text()}" for n, p in enumerate(errs + warns, 1)]


# -- authoring helpers (the region life modules write their data with these) -------------------

def go(**target) -> dict:
    return {"go": target}


def use(target: dict | None = None, anim: str = "idle", dur=None, until=None, **kw) -> dict:
    """A `use` step; the target is a dict, or item/slot/spot/within keywords, else `here`."""
    if target is None and "item" in kw:
        target = {k: kw.pop(k) for k in ("item", "slot", "spot", "within") if k in kw}
    s = {"use": target or {"here": True}, "anim": anim}
    if dur is not None:
        s["dur"] = list(dur)
    if until is not None:
        s["until"] = until
    s.update(kw)
    return s


def wait(dur=None, until=None) -> dict:
    return {"wait": {"dur": list(dur)} if dur else {"until": until}}


def wander(radius: int = 4, dur=(20, 40), zone: str | None = None) -> dict:
    w = {"zone": zone} if zone else {"radius": radius}
    return {"wander": w, "dur": list(dur)}


def grid_rect(view: RegionView, district: str) -> list[int]:
    """A district's bounding box as a region-file rect (grid [x0, y0, x1, y1], inclusive)."""
    c0, r0, c1, r1 = view.districts[district]["bbox"]
    return [r0, COLS - 1 - c1, r1, COLS - 1 - c0]


def curve(points: dict[int, float]) -> list[float]:
    """24 hourly values from a few (hour: value) points, held flat between them."""
    out, v = [], points.get(0, 0.0)
    for h in range(24):
        v = points.get(h, v)
        out.append(round(v, 2))
    return out


def sched(*blocks) -> list[dict]:
    """[(from, to, routine)] -> schedule blocks (an hour no block covers is indoors or away)."""
    return [{"hours": [a, b], "routine": r} for a, b, r in blocks]


def role(id_, actor, name, schedule, routines, **kw) -> dict:
    r = {"id": id_, "actor": actor, "name": name, "schedule": schedule, "routines": routines}
    r.update(kw)
    return r


def pop(role_, density, n, **kw) -> dict:
    """A district population: `n` per chunk-sized share of the district at density 1."""
    p = {"role": role_, "density": density, "max_per_chunk": n}
    p.update(kw)
    return p


def per(role_, item, count=1, density="always", **kw) -> dict:
    """A population bound to a placed item: `count` per instance in the district."""
    p = {"role": role_, "per_item": item, "count": count, "density": density}
    p.update(kw)
    return p


def card(kind, title, epithet, text) -> dict:
    c = {"kind": kind, "title": title, "text": text}
    if epithet:
        c["epithet"] = epithet
    return c
