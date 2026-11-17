# Living World: one simulation layer for the corner and the cities

This spec defines **one** system that makes everything in the world move: animals, Laeticia,
citizens, workers, soldiers, envoys, carts, pack animals, ships, flocks and weather. The corner and
the cities use the same data shapes and the same engine code. It builds on `living-corner.md`
(Laeticia, visitor behaviours, seasons, delights) and on `cities/world.md` (scale, orientation,
elevation, landmarks, walkers, cards), and it assumes the owner's latest direction: **one
continuous world map** (up to 1024 × 512 tiles) holding the home region, Rome, Athens and Pārsa, and
the land and sea between them.

User-facing text uses British spelling. Times of day are written as game hours (§4.1).

## How to read this document

| You are | Read |
|---|---|
| Engine | everything; the build order is §10 |
| Art | §2.3 (animations), §3.2 (goods sprites), §5 (asset column), §6, §10 (per task) |
| Audio | §5 (asset column), §9, §10 (per task) |
| City researcher | §2 and §3 (how walkers, figures, chains and events are written as data), §11 (notes for `world.md`) |

---

## 1 Principle and targets

### 1.1 The rule of thumb

> **In any screenful of inhabited world, the player can see at least N things moving with purpose,
> and at least one thing happening that was not happening a minute ago. Never more than the cap.**

- A **screenful** is the view at the default zoom (zoom 2 at 1280 × 800, about 250 tiles of
  ground). Targets scale with the visible ground area at other zooms, and the cap scales with it too.
- **Moving with purpose** means an actor travelling to a target or performing a work or leisure
  animation at a slot. Standing idle does not count; wind sway, water and smoke do not count.
- **A new happening** is any of: an event starting (§5), goods changing hands at a slot (§3), a
  weather change reaching the view, a routine change that alters a scene (shutters opening, lamps
  being lit, a ship mooring, a flock leaving its fold).

| Area kind | Moving with purpose: minimum / target / cap | New happenings per minute: minimum / cap | Large events visible at once (cap) |
|---|---|---|---|
| City centre (forum, agora, terrace, harbour front) | 12 / 20 / 40 | 2 / 6 | 1 |
| Town and working districts | 8 / 14 / 28 | 1 / 4 | 1 |
| Countryside, farmland, villages | 4 / 8 / 16 | 1 / 3 | 1 |
| Roads between regions | 2 / 4 / 10 | 1 / 2 | 1 |
| Sea and coast | 2 / 4 / 10 (ships, boats, birds, dolphins) | 1 / 2 | 1 |
| Wilderness (mountains, woods, steppe) | 2 / 3 / 8 (animals, birds, weather) | 1 per 2 min / 2 | 1 |
| The home corner | 3 / 6 / 20 (Laeticia, visitors) | 1 / 3 | 1 |

Readability rules that keep it cozy:

- Walking speed 0.8–1.2 tiles/s for people, slower for carts and oxen; nothing darts except
  startled birds.
- At most one crowd (more than 8 actors bunched within 4 tiles) per screen.
- At most one speech bubble on screen, and at most two actors gesturing at once.
- No more than one new event **start** per 20 s per screen. A deferred event waits for its next
  window, it is never dropped silently from a schedule (§5.2).
- Sound follows the same caps (§9).

### 1.2 How it is tested

A **liveliness probe** (a `--bench` mode and a script command `expect lively`) samples the camera at
fixed seeded points in each area kind over a 10-minute simulated run at 4× time speed and records,
per sample, the count of purposeful movers in view and the happenings in the past 60 s. The test
passes when 95% of samples are inside the minimum and cap columns. It runs on the synthetic test
world from task W4 and later on each city.

---

## 2 The actor model

### 2.1 Overview

Everything that moves is an **actor** of some **kind**. A kind is data. Each actor is a small fixed
record in a pool. Behaviour has five layers, each data-driven:

```
presence ──► schedule ──► routine (steps) ──► locomotion ──► slots and animations
 (why it      (which routine    (what it does, in       (how it gets     (where it acts,
  exists)      at this hour,     order: go, use, take,   there: walk,     what it looks like
               day, season,      put, wait, enter,       swim, sail a     doing it, what it
               weather)          follow, pick, each…)    lane, fly, drift) sounds like)
```

Interrupts (rain, a startle, a click, an event call-up) push a temporary routine and resume the
previous one after.

### 2.2 Kind definition: exact JSON shape

Actor kinds live in an `actors` list: shared kinds in the catalog, region kinds in each region's data
file (§11). Every field below is optional unless marked.

```json
{
  "id": "baker_rome",                       // required, unique
  "name": "Baker",                          // shown on hover and in the card
  "region": "rome",                         // absent = shared / home region
  "sprite": "walker/baker_rome",            // key prefix; critters use "critter/<id>", figures "figure/<id>"
  "variants": 3,                            // colour variants: <prefix>/<v>/<anim>/f<n> for walkers
  "anims": {                                // anim name → atlas anim, fps and frame sound events
    "move": { "fps": 8 }, "idle": { "fps": 2 },
    "knead": { "fps": 6, "events": { "2": "dough" } },
    "carry": { "fps": 8, "goods_at": [0, -26] }
  },
  "locomotion": { "mode": "walk", "speed": 0.9, "network": "roads" },
  "home": { "item": "r_bakery", "slot": "door" },
  "presence": { "population": { "per_item": "r_bakery", "count": 2 } },
  "schedule": [
    { "hours": ["03:00", "08:00"], "routine": "bake" },
    { "hours": ["08:00", "13:00"], "routine": "sell" },
    { "hours": ["13:00", "17:00"], "pick": [ { "routine": "rest", "weight": 2 }, { "routine": "errand", "weight": 1 } ] },
    { "hours": ["17:00", "03:00"], "routine": "home" }
  ],
  "interrupts": [ { "when": { "weather": "rain" }, "routine": "shelter", "priority": 2 } ],
  "routines": {
    "bake": { "loop": true, "steps": [
      { "go": { "item": "r_mill", "slot": "out", "near": "home" } },
      { "take": "flour" },
      { "go": { "home": "trough" } }, { "put": "flour" },
      { "use": { "home": "trough" }, "anim": "knead", "dur": [6, 9] },
      { "use": { "home": "oven" }, "anim": "peel", "dur": [8, 12], "make": "bread" } ] },
    "sell": { "loop": true, "steps": [ { "use": { "home": "counter" }, "anim": "serve", "dur": [10, 20] } ] },
    "rest": { "steps": [ { "go": { "slot_kind": "sit", "within": 8 } }, { "use": { "here": true }, "anim": "sit", "dur": [60, 120] } ] },
    "errand": { "steps": [ { "go": { "node": "forum_market" } }, { "wander": { "radius": 3 }, "dur": [20, 40] }, { "go": { "home": "door" } } ] },
    "home": { "steps": [ { "go": { "home": "door" } }, { "enter": { "home": "door" }, "until": { "hour": "03:00" } } ] },
    "shelter": { "steps": [ { "go": { "slot_kind": "shelter", "within": 6, "else": { "home": "door" } } },
                            { "use": { "here": true }, "anim": "idle", "until": { "weather": "clear" } } ] }
  },
  "card": "baker_rome",                     // card id in the region's strings
  "sound": { "voice": "sfx/rome_vendor_call", "every": [20, 40], "when_step": "sell" }
}
```

(JSON has no comments; they are annotations for this document.)

**Presence** says why an actor exists. Exactly one of:

| Form | Meaning | Used by |
|---|---|---|
| `{"needs": {...}}` / `{"recipe": Condition}` | the corner's visitor rules (`living-corner.md` §3, R3); count from `max` | ducks, hens, cat, rare visitors |
| `{"resident": true}` | exactly one, always present in its region | Laeticia, named figures with `presence: present` in the city files |
| `{"population": {...}}` | spawned per district or per item: `per_item` + `count`, or `district` + `density` (an hourly curve, 24 values 0–1, times `max`) | citizens, workers, gardeners, shepherds |
| `{"cast": "<event id>"}` | exists only while that event runs | processions, delegations, wedding parties |
| `{"token": {...}}` | a global moving thing that exists everywhere on the map in abstract form (§7.3) | ships, caravans, couriers, flocks of migrating birds, weather cells |

**Schedule** blocks are checked in order; the first whose filters all pass gives the routine (or a
weighted `pick` of routines, decided once per block per actor from its seed). Filters, all optional:
`hours` `[from, to]` (wraps past midnight), `phase` (list), `days` (`{"every": 4, "offset": 1}`),
`festival` (id), `season` (list), `weather` (`rain`, `clear`, `snow`, `storm`, `fog`, `dust`),
`when` (any condition from `living-corner.md` §3). The corner's visitors use `time` and `seasons`
as before; they are filters with the same meaning.

**Routine steps** (each step is an object with one verb key plus options):

| Step | Options | Meaning |
|---|---|---|
| `go` | Target, `else` Target | travel there with the kind's locomotion; reserve the slot on arrival |
| `use` | Target slot, `anim`, `dur` or `until`, `make` / `need` goods, `effect` | occupy a slot and animate; `need` waits for goods in the slot, `make` puts goods there at the end |
| `take` / `put` | goods id | move one unit of goods between hands and the current slot (§3) |
| `wander` | `radius` or `zone`, `dur` | drift between random free tiles near the current point (today's behaviour) |
| `wait` | `dur` or `until` | stand where it is |
| `enter` / `exit` | door slot, `dur` or `until` | fade into a building or item (hidden, still simulated as "inside"); `exit` comes out of it |
| `follow` | `{"actor": id}` or `{"leader": true}` or `{"resident": true}`, `dur`, `spacing` | keep behind another actor |
| `say` | line context | speech bubble (resident only, `living-corner.md` R6.6) |
| `emit` | `sfx` and/or `fx` | one-shot at the actor's position |
| `pick` | list of options, each `{weight, when?, …}` holding one step, `"routine": id` or `"steps": [...]` | weighted choice among options whose filters pass. **The corner's `visitors[].activities` entries are valid `pick` options as written** |
| `routine` | routine id | run another routine of the same kind, then continue |
| `each` | `{target set, max, order}`, `do: [steps]` | repeat the inner steps for each matching slot or point (water every bed); inside, the target `{"each": true}` is the current one |
| `if` | condition, `do: [steps]`, `else: [steps]` | branch |

`until` takes `{"hour": "hh:mm"}`, `{"phase": …}`, `{"weather": …}`, `{"event": "<id>"}` (until that
event starts or ends) or `{"goods": …}` (until the slot holds something).

`effect` names one of a small fixed set of engine hooks for game-specific outcomes that data
cannot express: `water_bed`, `call_hens`, `toss_pebble`, `cook`, `light_lamp`, `open_shutters`,
`close_shutters`, `ring`, `scatter_seed`, `react_line` (turn to the item just placed and say its
`place_<tag>` line), `unload` (a moored ship hands its cargo to the quay slots). New hooks are added in code, listed here, and never more
than one per behaviour.

**Targets** (one of): `{"item": id, "slot": slot id, "near": "self" | "home", "within": R}` (or
`"tag"` in place of `"item"`);
`{"home": slot id}` (a slot on the actor's home item); `{"slot_kind": kind, "tag": tag, "within": R}`;
`{"node": id}` (a named node of the region's path graph); `{"zone": id}`; `{"actor": kind}`;
`{"here": true}`; `{"each": true}`; `{"port": id}` (a port node on the actor's lane);
`{"poi": set}` (engine-provided target sets: `stroll`, `new_items`, `visitors`, `nooks`); and the
corner's `{"bank": true}`, `{"shore": true}`, `{"resident": true}`, `{"bedroll": true}`.

**Actor conditions.** Wherever a condition appears in actor data (`when`, `if`, interrupts), the
condition vocabulary of `living-corner.md` §3 is extended with terms about the actor itself:
`{"home": true}` (it has a home item), `{"harvested_today": true}` (the corner's harvest flag),
`{"startle": R}` (a placement, move or removal within R tiles just happened) and
`{"event": id}` (that event, or the engine event `placed_nearby`, is active or just fired).

**Locomotion modes:**

| Mode | Moves over | Path source | Notes |
|---|---|---|---|
| `walk` | land, walkable items, crossings, stairs (height interpolated, `world.md` §4) | region path graph (`network: roads`), local grid search inside the live window for the last stretch and for the home region | people, pack animals, carts (`turn_radius` makes carts take corners wide), land critters |
| `swim` | water tiles | straight lines with clear checks inside the live window (today's corner behaviour) | ducks, koi, frogs |
| `sail` | a named sea or river **lane** (authored polyline with ports) | the lane itself | ships, barges, fishing boats; `towed_by` for barges pulled by oxen on a towpath lane |
| `fly` | anything, at an altitude | straight lines or a lane (migration) | birds, bees, butterflies, fireflies, the owl |
| `drift` | anything | the shared wind (§6.2) times `factor` | weather cells, floating petals and leaves, smoke |

**Groups** (processions, delegations, caravans, flocks, the ducks' line, a ship and its crew) are a
`groups` list:

```json
{ "id": "delegation_lydian", "leader": { "actor": "usher_parsa" },
  "members": [ { "actor": "lydian_noble", "count": 1 },
               { "actor": "lydian_bearer", "count": 2, "carry": "gift_vessels" },
               { "actor": "horse_chariot", "count": 1 } ],
  "formation": { "kind": "line", "spacing": 0.8 } }
```

Formations: `line` (each member targets a point `spacing` tiles behind the previous one: the
ducks), `pairs` (two abreast), `cluster` (a loose blob around the leader within `radius`: sheep,
a crowd), `attached` (members drawn at fixed offsets on the leader: rowers in a boat, riders on
horses). Only the leader pathfinds.

### 2.3 Slots: interaction points on items and buildings

Items and landmarks gain an optional `slots` list. A slot is a place an actor can stand, sit or work:

```json
"slots": [
  { "id": "seat",  "kind": "sit",   "where": "on", "cap": 1, "facing": "rotation" },
  { "id": "door",  "kind": "door",  "where": "tile", "tiles": { "r0": [[2, 1]], "r1": [[1, 2]], "r2": [[-1, 0]], "r3": [[0, -1]] } },
  { "id": "oven",  "kind": "work",  "where": "tile", "tiles": { "r0": [[1, 2]] }, "anim": "peel", "holds": { "bread": 3 } },
  { "id": "counter", "kind": "stall", "where": "tile", "tiles": { "r0": [[0, 2]] }, "states": ["closed", "open"] },
  { "id": "buyer", "kind": "customer", "where": "tile", "tiles": { "r0": [[0, 3], [1, 3]] }, "cap": 2 }
]
```

- `where`: `on` (footprint centre, lifted to the item's `perch`), `beside` (any free walkable tile
  next to the footprint), `tile` (explicit tile offsets from the origin tile, per rotation; offsets
  for unlisted rotations are rotated from `r0` by the engine).
- `cap`: how many actors at once (default 1). Reservations are made when an actor chooses the step.
- `facing`: `rotation` (the item's rotation decides, as in `living-corner.md` R2.1), `item` (face the
  item), `out` (face away).
- `holds`: goods counters with a maximum (§3).
- `states`: visual states drawn as extra item layers (`item/<id>/<state>/<variant>/f<n>`, an
  extension of the layer list), switched by `effect` hooks or by time (§4). A state named `lit` needs no sprite: it
  gates the item's existing `glow` layer (lamps, braziers).
- **Implicit slots.** An item without `slots` still offers `on` (if it has a `perch`) and `beside`,
  so every corner activity written so far keeps working unchanged.

Slot kinds: `sit`, `lie`, `stand`, `work`, `door`, `stall`, `customer`, `queue` (a line of tiles, the
first free one is taken), `mooring`, `perch`, `graze`, `feed`, `light`, `tend`, `shelter`, `stage`
(a speaker; nearby `audience` slots fill in a ring).

### 2.4 The runtime record

Each actor is a fixed 96-byte record (§7.5): kind, variant, seed, routine id, step index, step
phase (travelling or acting), timers, position, target, reserved slot, goods in hand (one type, up
to 3 units), group id and slot in formation, facing, animation time, flags. An actor's behaviour
for a game day is a pure function of its seed, the clock and the world it can see, so it can be
re-created at any moment (§7.4).

### 2.5 Fitting what exists: the corner's visitors

A `visitors[]` entry in the catalog **is** an actor kind: the engine reads it as one, with these
rules, so the catalog does not change:

- `needs` / `recipe` → `presence`; `max`, `time`, `seasons` → presence limits and filters.
- `habitat` → locomotion (`land` → `walk` on the home grid, `water` → `swim`, `air` → `fly`,
  `shore` → `walk` limited to shore tiles).
- `activities` → a looping routine `{"loop": true, "steps": [{"pick": activities}]}`.
- `cycle` → a looping routine whose steps are those activities in order.
- `line` → a group with formation `line`; `home` → the presence's leaving behaviour walks to that
  item's door and `enter`s; `hide_in_rain` → an interrupt on rain that `enter`s the home item or
  fades.

Written out in the canonical form:

```json
{ "id": "duck", "sprite": "critter/duck", "presence": { "needs": { "terrain": { "water": 6 } }, "max": 4 },
  "locomotion": { "mode": "swim", "speed": 0.6 }, "group": { "formation": { "kind": "line", "spacing": 0.7 } },
  "routines": { "default": { "loop": true, "steps": [ { "pick": [
    { "id": "wander", "weight": 3 },
    { "id": "dabble", "at": { "here": true }, "anim": "dabble", "dur": [2, 5], "weight": 2 },
    { "id": "sleep_bank", "at": { "bank": true }, "anim": "sleep", "time": ["night"], "dur": [60, 120], "weight": 10 } ] } ] } },
  "interrupts": [ { "when": { "startle": 2 }, "routine": "flee", "priority": 3 } ] }

{ "id": "cat", "sprite": "critter/cat", "presence": { "needs": { "items": { "cottage": 1 } }, "max": 1 },
  "locomotion": { "mode": "walk", "speed": 0.9 },
  "routines": { "default": { "loop": true, "steps": [ { "pick": [
    { "id": "nap", "at": { "tag": "seat" }, "spot": "on", "anim": "sleep", "time": ["day", "dusk"], "dur": [30, 60], "weight": 3 },
    { "id": "warm", "at": { "item": "campfire" }, "spot": "beside", "anim": "sleep", "time": ["dusk", "night"], "dur": [40, 80], "weight": 5 },
    { "id": "doorstep", "at": { "item": "cottage", "slot": "door" }, "anim": "sit", "dur": [10, 25], "weight": 2 },
    { "id": "follow", "at": { "resident": true }, "time": ["day"], "dur": [10, 20], "weight": 1 } ] } ] } } }

{ "id": "bee", "sprite": "critter/bee", "presence": { "needs": { "items": { "beehive": 1 } }, "max": 6 },
  "locomotion": { "mode": "fly", "speed": 1.6 },
  "routines": { "default": { "loop": true, "steps": [
    { "use": { "tag": "flower", "within": 6, "near": "home" }, "anim": "idle", "dur": [2, 4] },
    { "use": { "tag": "flower", "within": 6, "near": "home" }, "anim": "idle", "dur": [2, 4] },
    { "enter": { "item": "beehive", "slot": "entrance" }, "dur": [3, 6] } ] } },
  "interrupts": [ { "when": { "weather": "rain" }, "routine": "hive", "priority": 2 } ] }
```

### 2.6 Laeticia as an actor

Her routine table in `living-corner.md` R6.2 becomes data in the catalog's `resident` entry
(`schedule`, `routines`, `interrupts`; added to `catalog.next.json` in this revision). Hours use the
mapping of §4.1 (dawn 03:00–06:00, day 06:00–18:00, dusk 18:00–21:00, night 21:00–03:00).

```json
"schedule": [
  { "hours": ["03:00", "04:30"], "routine": "wake" },
  { "hours": ["04:30", "10:45"], "routine": "chores" },
  { "hours": ["10:45", "14:30"], "routine": "leisure" },
  { "hours": ["14:30", "18:00"], "routine": "stroll" },
  { "hours": ["18:00", "21:00"], "routine": "evening" },
  { "hours": ["21:00", "03:00"], "routine": "home" } ],
"routines": {
  "wake":    { "steps": [ { "if": { "home": true }, "do": [ { "exit": { "home": "door" } } ] },
                          { "use": { "here": true }, "anim": "stretch", "dur": [2, 2] }, { "say": "morning" } ] },
  "chores":  { "steps": [
      { "each": { "item": "planter", "slot": "tend", "max": 6, "order": "nearest" },
        "do": [ { "go": { "each": true } }, { "use": { "each": true }, "anim": "water", "dur": [3, 3], "effect": "water_bed" } ] },
      { "if": { "visitor": { "id": "hen" } },
        "do": [ { "go": { "item": "coop", "slot": "feed" } }, { "use": { "item": "coop", "slot": "feed" }, "anim": "scatter", "dur": [4, 4], "effect": "call_hens" } ] },
      { "routine": "leisure" } ] },
  "leisure": { "steps": [ { "pick": [
      { "weight": 3, "steps": [ { "go": { "slot_kind": "sit", "tag": "seat" } }, { "use": { "here": true }, "anim": "sit", "dur": [20, 40] },
                                { "pick": [ { "weight": 1, "use": { "here": true }, "anim": "read", "dur": [20, 40] }, { "weight": 1, "wait": { "dur": [1, 1] } } ] } ] },
      { "weight": 2, "when": { "count": { "item": "hammock", "min": 1 } },
        "steps": [ { "go": { "item": "hammock", "slot": "lie" } }, { "use": { "item": "hammock", "slot": "lie" }, "anim": "lie", "dur": [30, 60] } ] },
      { "weight": 4, "when": { "all": [ { "nook": "lakeside_lunch" }, { "harvested_today": true } ] },
        "steps": [ { "go": { "item": "picnic_table", "slot": "seat" } }, { "use": { "item": "picnic_table", "slot": "seat" }, "anim": "sit", "dur": [40, 60] } ] } ] } ] },
  "stroll":  { "steps": [ { "each": { "poi": "stroll", "max": 4 },
      "do": [ { "go": { "each": true } }, { "pick": [ { "weight": 2, "use": { "here": true }, "anim": "idle", "dur": [2, 2] },
                                                          { "weight": 1, "use": { "here": true }, "anim": "sketch", "dur": [15, 25] } ] } ] } ] },
  "evening": { "steps": [ { "say": "dusk" }, { "pick": [
      { "weight": 3, "when": { "count": { "item": "campfire", "min": 1 } },
        "steps": [ { "go": { "item": "campfire", "slot": "warm" } }, { "use": { "item": "campfire", "slot": "warm" }, "anim": "warm", "dur": [20, 40] } ] },
      { "weight": 1, "steps": [ { "go": { "slot_kind": "sit", "tag": "seat" } }, { "use": { "here": true }, "anim": "sit", "dur": [20, 40] } ] } ] } ] },
  "home":    { "steps": [ { "say": "night" }, { "if": { "home": true },
      "do": [ { "go": { "home": "door" } }, { "enter": { "home": "door" }, "until": { "hour": "03:00" } } ],
      "else": [ { "say": "no_cottage_night" }, { "go": { "bedroll": true } }, { "use": { "here": true }, "anim": "sleep", "until": { "hour": "03:00" } } ] } ] },
  "shelter": { "steps": [ { "say": "rain_start" }, { "if": { "home": true },
      "do": [ { "go": { "home": "door" } }, { "enter": { "home": "door" }, "until": { "weather": "clear" } } ],
      "else": [ { "go": { "tag": "tree", "slot": "beside" } }, { "wait": { "until": { "weather": "clear" } } } ] }, { "say": "rain_stop" } ] },
  "react":   { "steps": [ { "use": { "here": true }, "anim": "idle", "dur": [2, 2], "effect": "react_line" } ] } },
"interrupts": [
  { "when": { "weather": "rain" }, "routine": "shelter", "priority": 3 },
  { "when": { "event": "placed_nearby" }, "routine": "react", "priority": 1, "chance": 0.3, "cooldown": 20 } ]
```

The nook routines of `living-corner.md` R7.4 (`moon_stroll`, `pebble`; `lunch` is the third
leisure option above) are inserted by the engine into these routines while their nook exists,
exactly as that spec says; `{"bedroll": true}` is her bedroll spot (R6.4). Everything else in R6 (movement costs, bubbles, displacement) is the generic system.

### 2.7 City examples

**A potter (Athens, Kerameikos)**, part of the pottery chain (§3.3, C7):

```json
{ "id": "potter_athens", "name": "Potter", "region": "athens", "sprite": "walker/potter_athens", "variants": 3,
  "anims": { "throw": { "fps": 6, "events": { "0": "wheel_creak" } }, "carry": { "fps": 8, "goods_at": [0, -24] } },
  "locomotion": { "mode": "walk", "speed": 0.9, "network": "roads" },
  "home": { "item": "a_potters_workshop", "slot": "door" },
  "presence": { "population": { "per_item": "a_potters_workshop", "count": 1 } },
  "schedule": [ { "hours": ["06:00", "17:00"], "routine": "work" }, { "hours": ["17:00", "06:00"], "routine": "home" } ],
  "routines": {
    "work": { "loop": true, "steps": [
      { "use": { "home": "wheel" }, "anim": "throw", "dur": [12, 18], "need": "clay", "make": "pot_raw" },
      { "take": "pot_raw" }, { "go": { "item": "a_kiln", "near": "home", "slot": "load" } }, { "put": "pot_raw" },
      { "go": { "home": "wheel" } } ] },
    "home": { "steps": [ { "go": { "home": "door" } }, { "enter": { "home": "door" }, "until": { "hour": "06:00" } } ] } },
  "card": "potter_athens" }
```

**A Roman baker** is the example in §2.2.

**A tribute delegation (Pārsa)**, a group cast by the audience event (§5, P1):

```json
{ "id": "audience_delegation", "group": "delegation_lydian",
  "routines": { "default": { "steps": [
    { "go": { "node": "royal_road_station" } }, { "use": { "item": "p_road_station", "slot": "seal_check" }, "anim": "idle", "dur": [6, 8] },
    { "go": { "node": "great_stair_foot" } }, { "go": { "node": "gate_all_nations" } },
    { "go": { "node": "apadana_north_portico" } }, { "use": { "item": "apadana", "slot": "audience" }, "anim": "bow", "dur": [10, 14] },
    { "go": { "item": "p_treasury", "slot": "gift_drop" } }, { "put": "gift_vessels" },
    { "go": { "node": "royal_road_station" } }, { "enter": { "item": "p_road_station", "slot": "door" } } ] } } }
```

**A merchant ship (Piraeus ↔ Ostia lane)**, a token actor (§7.3):

```json
{ "id": "merchant_ship", "name": "Merchant ship", "sprite": "ship/merchant", "variants": 2,
  "anims": { "sail": { "fps": 2 }, "row": { "fps": 4 }, "moored": { "fps": 1 } },
  "locomotion": { "mode": "sail", "speed": 0.7, "lane": "piraeus_ostia" },
  "presence": { "token": { "count": 3, "spacing": "even" } },
  "routines": { "default": { "loop": true, "steps": [
    { "go": { "port": "piraeus", "slot": "mooring" } },
    { "use": { "here": true }, "anim": "moored", "dur": [90, 120], "effect": "unload", "make": "amphorae" },
    { "go": { "port": "ostia", "slot": "mooring" } },
    { "use": { "here": true }, "anim": "moored", "dur": [90, 120], "effect": "unload", "make": "grain_sacks" } ] } },
  "sound": { "loop": "sfx/ship_creak", "radius": 6 } }
```

Mooring starts the harbour's `ship_arrived` event (§5, S1), which calls dock workers to the mooring's
`load` slots; their routines carry the goods along the quay.

**A weather cell** is also an actor: `{"id": "rain_cell", "locomotion": {"mode": "drift", "factor": 1.0},
"presence": {"token": {"climate": true}}, "effect_area": {"kind": "rain", "radius": 10}}` (§6.1).

---

## 3 Chains you can watch

### 3.1 Principle

A chain is a line of slots where something is made, carried, transformed and finally used up, with
the goods **visible** in hands, on carts and stacked at slots. There is no economy the player
manages: no prices, no stock screen, no failure. Chains exist so that a curious player can follow a
sack of grain from a ship to a loaf in a customer's hand.

### 3.2 Goods

```json
"goods": [ { "id": "bread", "name": "Bread", "sprite": "goods/bread", "stack": 3 } ]
```

- **Carried sprite** `goods/<id>` drawn at the actor animation's `goods_at` offset (in hands, on the
  head, on a shoulder, on a cart bed, in a ship's hold as deck cargo).
- **Stacks** `goods/<id>/s1`, `s2`, `s3` drawn at a slot that `holds` that goods, showing 1–3 units.
- A slot's counter is 0..`max` (at most 3). Hands hold one goods type, up to 3 units (a cart or pack
  animal: its own `holds`).

### 3.3 Keeping chains running forever

Each chain is declared, so the engine can run it with no stockpiling and no starving:

```json
{ "id": "rome_bread", "period": 120,
  "stages": [
    { "slot": "r_tiber_wharf.unload",   "makes": "grain_sacks", "by": "merchant_ship" },
    { "carry": "grain_sacks", "from": "r_tiber_wharf.unload", "to": "r_mill.in", "by": "porter_rome" },
    { "slot": "r_mill.grind",  "needs": "grain_sacks", "makes": "flour", "by": "donkey_mill" },
    { "carry": "flour", "from": "r_mill.out", "to": "r_bakery.trough", "by": "baker_rome" },
    { "slot": "r_bakery.oven", "needs": "flour", "makes": "bread", "by": "baker_rome" },
    { "slot": "r_bakery.counter", "sink": "bread", "by": "customer_rome" } ] }
```

Rules:

1. **Sources are rate-limited, never empty.** A source stage makes one unit per `period` (a ship
   unloads, a field yields, a quarry block is cut). If its slot is full, the worker does a visible
   rest (sit, wipe brow, chat) instead of producing.
2. **Capacity is tiny.** Every slot holds at most 3. Producers stop at full; carriers only pick up
   what exists. Stockpiles cannot grow.
3. **Sinks always consume.** The last stage removes goods in a way you can see: a customer walks
   off with bread and goes home; a block becomes part of the temple (a short `fx/dust` and the
   carvers move on to the next stone); a pot is loaded and the ship sails. Customers are spawned by
   the sink's district density, so a sink never waits forever; if no customer comes within
   `period`, the vendor "sells to someone inside" (the unit vanishes with a small bell sound).
4. **Starving is masked.** A stage waiting for input plays a believable idle (sweeping, chatting,
   sharpening tools) with a `need` icon only when hovered.
5. **Clocked when unseen.** In abstract mode (§7) a chain is a phase: `T mod period` tells which
   hop each unit is on, so when the camera arrives the cart is somewhere along the road with the
   right goods, and the stacks show the counters the formula implies. Full simulation starts from
   that state and may drift with crowding; it is re-derived from the formula next time the area is
   abstract.

### 3.4 The chains

| # | Chain | Region | Stages (goods in brackets) | Period |
|---|---|---|---|---|
| C1 | Kitchen garden | home | ripe bed → Laeticia's basket (produce) → cottage door (cook: chimney smoke thickens) | player-triggered (harvest), `living-corner.md` R4.5 |
| C2 | Hen feed | home | Laeticia's apron (feed) → coop feed slot → hens peck around her | daily, chores block |
| C3 | Stone for the terrace | Pārsa | quarry face (block) → rope team with sledge → masons' yard (squared block) → sculptor (relief block) → hall wall (sink: block set in place) | 240 s |
| C4 | Bread rations | Pārsa | barley field (sheaves) → threshing floor with oxen (grain) → granary, scribe writes a tablet (grain) → grinders (flour) → tanūr oven (bread) → ration queue (sink: workers walk off with bread) | 180 s |
| C5 | Gifts of the peoples | Pārsa | delegation on the road (gift vessels, cloth, a lioness cart) → road station → stairway → Apadāna audience → treasury (weighed, recorded) → storerooms (sink) | the audience event, every 12 game minutes in spring (`persepolis.md` §6.9) |
| C6 | Wool to robes | Pārsa | sheep fold (fleece) → shearing → dye vats by the canal (yarn) → weavers (cloth) → a noble on the terrace (sink) | 300 s |
| C7 | Pottery | Athens | clay pit (clay) → potter's wheel (raw pot) → kiln (fired pot; smoke) → painter (painted pot) → shop shelf → cart → Piraeus ship (sink: loaded, ship leaves) | 200 s |
| C8 | Olive oil | Athens | olive grove (olives, autumn) or store jars (rest of the year) → press (oil jars) → agora stall (sink: customers) and amphorae → Piraeus | 240 s |
| C9 | Bread | Rome | grain ship at the Tiber wharf (sacks) → porters → donkey mill (flour) → bakery oven (bread) → counter (sink: a customer walks off eating) | 120 s |
| C10 | Marble for a temple | Rome | marble ship at the river wharf (block) → ox cart (night only, §4.5) → sculptors' yard (carved drum) → treadwheel crane at the temple site (sink: drum set) | 300 s |
| C11 | Fish | sea, Rome, Athens | fishing boat (fish) → quay → fish stall (sink: customers; sometimes a cat, event W12) | 150 s |
| C12 | Water | Athens, Rome | fountain house (water jar) → water carriers → houses (sink: enter door) | 90 s |

### 3.5 Noticing and following a chain

- Goods changing hands play a small pop and a soft material sound at the slot (wood, cloth, clay,
  stone), and count as a happening (§1.1).
- Hovering a carrier shows "Carrying flour to the bakery". Hovering a slot shows what it holds and
  what it waits for.
- Clicking any chain actor opens its card with a **chain strip** under the text: the chain's stage
  icons in a row, the current one highlighted, and a **Follow** button (§8.2). While following,
  the next stage's slot gets a soft outline (`ui/tile_area`) so the player sees where the goods go.
- The region's sketchbook tab (`living-corner.md` §13) lists chains the player has followed from
  start to sink as "Seen from start to finish". This is the only record and is a page like any other.

---

## 4 Time

### 4.1 One clock for the whole world

- The world has **one clock** (the corner's: `t` in [0, 1), 12 real minutes per day at 1×) and **one
  calendar** (day counter, 3-day seasons, 12-day year; `living-corner.md` R4.1). There are no time
  zones: the cities are memories of different centuries on one map, and one sky keeps the world
  readable. Regions differ in **climate**, not in hour.
- **Game hours** for authoring: `hour = (6 + 24 × t) mod 24`. With today's phase boundaries this
  gives dawn 03:00–06:00, day 06:00–18:00, dusk 18:00–21:00, night 21:00–03:00. Players never see
  hours; they see light.
- **Week.** A 4-day week (`day mod 4`, numbered 0–3) stands for the real market rhythms, compressed:
  Rome's market day (every eighth day in reality) is day 0; Athens has a market every morning and an
  Assembly on day 2; Pārsa's ration day is day 3.
- **Festivals** are calendar entries:

```json
{ "id": "panathenaia", "region": "athens", "season": "summer", "day": 2, "hours": ["06:00", "12:00"] }
```

| Festival | Region | When (season, day of season) | What changes |
|---|---|---|---|
| Panathenaia | Athens | summer, day 2, morning | the great procession (A1); crowds on the Acropolis; music |
| Spring audience | Pārsa | every spring day | delegations every 12 game minutes (P1) |
| Harvest offering | Pārsa | summer, day 1 | threshing-floor offering (P10) |
| Fire evening | Pārsa | winter, day 1, dusk | fire-altar gathering (P11) |
| Parilia | Rome | spring, day 2 | shepherds' bonfires at dusk, people leaping the fires; tradition says Hadrian renamed the day Romaea around this time (R12) |
| Races day | Rome | every day 0 afternoon | chariot races heard from the Circus (R5) |
| Olive harvest | Athens | autumn, all days | beating the trees in the groves (A6) |
| Ploughing | everywhere farmed | autumn, day 1 | ox teams in fields; cranes overhead (W3) |

Seasons are global (`living-corner.md` R4.2). Each city's own "moment" (Athens summer, Pārsa spring,
Rome April) is the season in which its signature festival happens; in the other seasons the city
runs its everyday life and its other seasonal events.

### 4.2 How routines key off time

All through schedule filters (§2.2): hours, phase, week day, festival, season, weather. Concrete
patterns every region uses:

| Pattern | How |
|---|---|
| **Shops open and close** | a vendor's `open` routine starts with `effect: open_shutters` on its stall slot (state `open`) and ends with `close_shutters`. Hours per vendor kind. When the stall's area is abstract the state is the formula's (open between the hours) |
| **Lamps lit by a lamplighter** | lamps have a `light` slot with states `unlit`/`lit` (the glow layer is drawn only when lit). A lamplighter's `dusk` routine `each`es the lamps on its route with `effect: light_lamp`. In abstract areas, and in the home region (no lamplighter), each lamp lights at dusk start + a hash of its position × 20 s, so the result is identical either way |
| **Sheltering from rain** | an interrupt on `weather: rain` with `shelter` (porticoes, doorways, trees, awnings carry `shelter` slots), else go home. Vendors pull awnings in (state). Animals bunch under trees |
| **Day and night creatures** | presence filters: swifts and cicadas by day in summer; bats and owls at dusk and night; frogs at night by water; fireflies on summer nights (as the corner) |
| **Cicadas stop at dusk** | a sound emitter (§9) with hours 09:00–18:00, `season: summer`, `weather: clear`, in Athens and the countryside; it fades over 20 s when its window closes |
| **The harbour gets busy** | a ship mooring raises the `ship_arrived` event; dock workers' `harbour` routine waits `until: {"event": "ship_arrived"}`, then carries goods; gulls follow |
| **Night carts in Rome** | wheeled carts may enter the city only between dusk and dawn (§4.5); by day they wait at the gates |

### 4.3 Climates

Each region has a climate: weather weights per season, temperature band (for which sounds and
animals), dust, fog and snow likelihood, and a grading shift. One clock drives them all; the
climate only changes what that clock brings.

| Region | Spring | Summer | Autumn | Winter |
|---|---|---|---|---|
| Home | showers | warm, clear | wind, rain | snow |
| Rome and Latium | showers, warm | hot, clear, thunderstorms inland | rain | rain, cold clear days, no snow in the city |
| Athens and Attica | clear, breezy | hot, dry, haze, cicadas, the north wind | first rains | rain, mild, snow on the far mountains |
| Pārsa and Fārs | showers (Tištrya), channels full | hot, dust breezes, the court absent from the terrace (`persepolis.md` §6.8) | dry, clear | cold, snow on the mountain, few travellers |
| Sea | calm, the sailing season opens | calm, steady winds | storms begin | rough; ships rare (sailing mostly ceased in winter) |

### 4.4 Weather and the player

The corner's rain toggle (N) becomes a three-way choice when natural weather lands (task W3):
**Natural** (default) → **Rain here** → **Clear here**, applying to the region under the camera.
Natural weather is described in §6.

### 4.5 One historical rule worth showing

Rome restricted wheeled traffic inside the city by day (a regulation of the late Republic that
continued into the Empire; exceptions included building work). The game shows it: by day, carts
wait at the gates and porters carry; at dusk, carts roll in, and the night has the rumble of wheels
(event R1). The Roman card for the night cart says so, with "probably" where the details are
uncertain.

---

## 5 Events

### 5.1 Definition

```json
{ "id": "ship_arrived", "region": "athens", "zone": "piraeus_quay",
  "trigger": { "on": "token_arrived", "actor": "merchant_ship" },
  "size": "medium", "duration": [90, 120], "cooldown": 300,
  "cast": [ { "actor": "dock_worker_athens", "count": 6, "from": "district" } ],
  "steps": [ { "emit": { "sfx": "sfx/ship_bell" } } ],
  "ambience": { "file": "amb/harbour_busy.ogg", "gain": 0.6 } }
```

Triggers: `window` (a time window per day with a probability), `calendar` (a festival), `token_arrived`
(a ship, caravan or courier reaches a node), `weather` (a cell starts or passes), `reactive` (a
local condition among live actors, e.g. a cat within 2 tiles of a fish stall with fish), `chain`
(a sink consumed), `player` (a touch, §8), `after` (another event ended).

### 5.2 Scheduling

- **Scheduled events** (window, calendar, token, weather) are decided by a **day plan** per region,
  computed at the start of each game day from `hash(world seed, region, event, day, window)`:
  whether it happens and at what offset in its window. Overlaps between large events of one region
  are resolved in the plan by priority, so the plan never needs runtime deferral. Because the plan
  is a pure function, an event is equally "happening" whether the area is live or abstract, and the
  camera can arrive in the middle of a procession and see it at the right point.
- **Reactive events** only happen in the live area, using the region's random stream; they have a
  cooldown per region and the per-screen caps of §1.1 (one new start per 20 s; deferral re-checks
  after 5 s and gives up after 60 s, which is acceptable for reactive moments only).
- **Rarity classes**: Ambient (several times an hour of play), Common (a few times per game day),
  Uncommon (about once per game day), Rare (once every few game days), Festival (calendar).

### 5.3 The events

Regions: **H** home, **A** Athens, **P** Pārsa, **R** Rome, **S** sea and coasts, **L** land between
(countryside, roads), **W** anywhere. "Corner" marks events already in `living-corner.md` §5.8 (with
the delight number); they are implemented as events on this scheduler, not separately.

| # | Event | Region | Trigger | What the player sees and hears | Duration | Rarity | Assets | Corner |
|---|---|---|---|---|---|---|---|---|
| H1 | Rainbow | H, W | weather: a rain cell leaves the view by day | arc behind the land, soft shimmer | 48 s | Uncommon | `sky/rainbow`, `sfx/rainbow` | #2 |
| H2 | Shooting star | W | window: night, clear | a streak across the sky, tiny twinkle | 1 s | Ambient | `fx/star_streak`, `sfx/twinkle` | #3 |
| H3 | Owl call | H, A, P, L | reactive: owl present at night (Athens: the little owl on the Acropolis) | hoot, the owl's head turns | 2 s | Common | owl `hoot`, `sfx/owl` | #4 |
| H4 | Trees rustle | H, zones | player: placement near a tree | sway, leaves fall | 0.6 s | Ambient | existing | #5 |
| H5 | Ducks startle | H | player: placement near ducks | flap, paddle away, quacks | 3 s | Ambient | duck `flap` | #6 |
| H6 | Hens scatter | H | player: placement near hens | flap and hop away | 2 s | Ambient | hen `flap` | #7 |
| H7 | Cat stretches | H | player: placement near the sleeping cat | stretch, stroll off | 3 s | Common | cat `stretch` | #8 |
| H8 | Cooking smoke | H | chain C1 sink | chimney puffs thicker | 90 s | Common | existing | #9 |
| H9 | Frog chorus | H, L | weather: after rain, frog present | croaks every few seconds | 60 s | Common | frog `croak` | #10 |
| H10 | Dawn chorus | W | window: dawn start | birdsong swells | 60 s | daily | existing beds | #11 |
| H11 | Butterfly on her hat | H | reactive | a butterfly lands on Laeticia | 6–12 s | Common | none | #12 |
| H12 | Season turns | W | calendar: first dawn of a season | chime; Laeticia's season line | 3 s | Festival | `sfx/season` | #14 |
| H13 | Gust | W | window: day, every 2–4 min, travels with the wind | a wave of sway crosses the screen, leaves, flags snap | 2 s | Ambient | `sfx/gust` | #16 |
| H14 | Fish jump | H, S, L rivers | window: day or dusk | a fish arcs from the water | 1 s | Ambient | `fx/fish_jump` | #17 |
| H15 | Fireflies in sync | H, L | reactive: 8+ fireflies | unison blinking | 6 s | Common | none | #20 |
| H16 | Traveller on the road | H | window: day, once the home road exists | someone walks the road outside the wall, waves if Laeticia is near the gate | 40 s | Common | generic traveller walker | new |
| W1 | Storm from the sea | S then L | weather: a storm cell spawns offshore and drifts onshore | dark cloud line, whitecaps, distant thunder, lightning flashes, then rain sweeps in; ships run for port | 3–5 min | Rare | `weather/*`, `fx/lightning_flash`, `amb/storm`, `sfx/thunder_far` | |
| W2 | Valley fog at dawn | L, P, R | window: dawn, clear, autumn/spring | low fog lying in low tiles, burning off as the sun rises | 3 min | Common | `weather/fog_v0-3` | |
| W3 | Cranes migrating | L, S | calendar: autumn day 1 and spring day 1 | a V of cranes crossing high, bugling; farmers look up (Hesiod's ploughing sign) | 40 s | Festival | `bird/crane` flock, `sfx/cranes` | |
| W4 | Swifts at dusk | A, R, P | window: summer dusk | screaming swifts swirl over roofs | 2 min | daily | `bird/swift`, `sfx/swifts` | |
| W5 | Bats come out | W towns | window: dusk | bats flit around lamps and trees | 3 min | daily | `bird/bat` | |
| W6 | Cloud shadows | W | weather: cloud cells | soft shadows slide over the ground | continuous | Ambient | `weather/cloud_shadow_v0-3` | |
| W7 | Shower passes | W | weather: rain cell | rain area crosses, people shelter, ground darkens, puddles, then drying | 1–3 min | Common | `fx/raindrop`, `fx/puddle` | |
| W8 | Dust breeze | P, L east | weather: dust cell, summer afternoon | ochre haze drifts, people cover faces, awnings flap | 2 min | Common in summer | `weather/dust_v0-3`, `amb/dust_wind` | |
| W9 | Snow on the peaks | P, A backdrops | calendar: winter | backdrop mountains turn white | season | Festival | `backdrop/*@winter` | |
| W10 | Dogs bark across town | W towns | window: night | one dog barks, another answers far away | 5 s | Common | `sfx/dog_far` | |
| W11 | Lamps lit | W towns | window: dusk | the lamplighter's round; lamps come on one by one | 3 min | daily | lamplighter walker, `sfx/lamp_light` | |
| W12 | A cat steals a fish | R, A, S quays | reactive: cat near a fish stall with fish | the cat slinks in, grabs, runs; the vendor shouts and laughs | 6 s | Uncommon | town cat `steal` anim, `goods/fish`, `sfx/vendor_shout` | |
| W13 | A child chases pigeons | A, R | reactive: pigeons on a plaza, child nearby | pigeons burst up and resettle | 5 s | Common | `bird/pigeon`, `sfx/pigeons_up` | |
| S1 | Ship arrives and unloads | S, A, R | token: a merchant ship reaches its mooring | sail furls, ropes thrown, porters carry amphorae and sacks, gulls wheel | 2 min | Common | ship anims, dock workers, `sfx/ship_bell`, `amb/harbour_busy` | |
| S2 | Fishing fleet | S | window: leave at dawn, return late morning | small boats row out in a loose line, come back with gulls behind | 2 × 2 min | daily | fishing boat, `bird/gull` | |
| S3 | Dolphins | S | window: day, near a ship | dolphins arc beside the bow | 30 s | Uncommon | `fx/dolphin` | |
| S4 | Trireme drill | S near Athens | window: morning | a trireme rows past in time to a piper and a call; oars flash | 90 s | Uncommon | `ship/trireme`, `sfx/oars_rhythm` | |
| S5 | Becalmed | S | weather: wind strength below 0.1 | sails hang slack, crews take to the oars | until wind | Uncommon | ship `row` anim | |
| S6 | Grain fleet | S, R | calendar: spring, day 1 | a line of big grain ships comes in to the harbour together; the harbour fills | 4 min | Festival | 3 ships, `sfx/ship_bell` | |
| S7 | Sea swell after a storm | S | after: W1 | larger waves, foam on every shore, ships pitch | 5 min | Rare | sea state 3 shore foam | |
| L1 | Shepherd leads the flock | L, P, A | window: dawn out, dusk in | a cluster of sheep and goats moves along a track, a dog circling, bells | 2 min | daily | sheep, goat, dog, shepherd, `sfx/sheep_bells` | |
| L2 | Reapers in the field | L, P, R | season: early summer, day | a row of reapers moves through grain; sheaves left behind | 3 min | daily in season | reaper walker, sheaf goods | |
| L3 | Threshing with oxen | L, P, A | season: summer, day | oxen circle the threshing floor; chaff blows downwind | 3 min | daily in season | ox, `fx/chaff` | |
| L4 | Ploughing | L | calendar: autumn | ox teams turn the soil, birds follow the plough | 3 min | Festival | ox team, ploughman | |
| L5 | Mule train | L | window: day | a string of mules with packs passes along the road | 60 s | Common | mule, muleteer | |
| L6 | Courier at the gallop | L Royal Road, P | window: day, every few hours | a rider gallops station to station; at the station a fresh horse is waiting (the Royal Road relay) | 30 s | Common | courier rider, `sfx/hooves_gallop` | |
| L7 | Caravan arrives at dusk | P, L | window: dusk | camels and donkeys file into the station yard, packs come down, fires are lit | 3 min | daily | camel, donkey, drivers, `sfx/camel` | |
| A1 | Panathenaic procession | A | calendar: Panathenaia | the procession winds from the Dipylon gate through the agora up to the Acropolis: the robe carried for Athena, maidens with baskets, musicians, cattle for the sacrifice, riders | 8 min | Festival | procession cast (city file), `music sting`, `sfx/aulos` | |
| A2 | A philosopher draws a crowd | A | window: morning, agora, any day | one man in the stoa talks; listeners gather in a ring (stage and audience slots), some argue, some leave | 4 min | daily | figure (named in the city file), listeners | |
| A3 | Assembly on the Pnyx | A | window: week day 2, morning | citizens stream uphill, a speaker on the platform, a murmur rises and falls | 6 min | Uncommon | citizens, `amb/assembly` | |
| A4 | Kiln firing in the Kerameikos | A | chain C7, each firing | a column of smoke, the potter peers in, pots come out glowing then cool | 2 min | Common | `fx/smoke_column`, kiln states | |
| A5 | Chorus rehearsal | A | window: morning, theatre | a chorus practises steps and song in the orchestra; a few watch | 3 min | Uncommon | chorus walkers, `sfx/chorus_far` | |
| A6 | Olive harvest | A, L | festival: autumn | people beat branches with sticks, nets on the ground, baskets fill | 3 min | Festival | olive pickers, `goods/olives` | |
| A7 | Wedding procession | A | window: dusk, any day, rare | torches, the bride in a cart, singing, flute; they walk to the groom's house | 3 min | Rare | wedding cast, `sfx/wedding_song` | |
| A8 | Athletes at the gymnasium | A | window: morning | runners and wrestlers train, a trainer watches | 4 min | Common | athlete walkers | |
| A9 | Water at the fountain house | A, R | window: dawn | women with jars queue and chat at the fountain | 3 min | daily | water carriers, `amb/fountain` | |
| A10 | Symposium lights | A | window: night | a courtyard glows, lyre and laughter drift out | 5 min | Common | `sfx/lyre_far` | |
| P1 | Audience of the delegations | P | festival: spring audience, every 12 game minutes | a delegation climbs the great stair behind an usher, gifts in hand, into the Apadāna; then to the treasury | 6 min | Festival (spring) | delegation sets, usher, guards, `sfx/horn` | |
| P2 | Fire offering at dawn | P | window: dawn | the magus rekindles the fire altar, a chant, smoke rises straight | 2 min | daily | magus, `fx/fire_altar`, `sfx/chant` | |
| P3 | Water turn | P, L | window: dawn | a farmer opens a channel; water runs down the furrows, glinting | 2 min | daily | farmer, channel water states | |
| P4 | Ration day | P | week day 3, morning | a queue at the granary, scribes measure barley, write tablets; workers leave with bread and jars | 6 min | Uncommon | scribes, workers, C4 goods | |
| P5 | Tištrya on the ridge | P | weather: spring shower | a faint white horse with golden ears on the mountain ridge, gone when the rain stops (`persepolis.md`, Tištrya, shrine/apparition) | the shower | Rare | apparition sprite | |
| P6 | Storyteller at the stair plaza | P | window: dusk | a storyteller, children and workers sit in a ring | 4 min | daily | storyteller, audience | |
| P7 | Royal ride on the plain | P | window: afternoon | riders and a chariot cross the plain, dust behind | 2 min | Uncommon | riders, chariot | |
| P8 | Change of guard | P, R | window: morning and dusk | guards march to posts, swap, march back | 90 s | daily | guards, `sfx/march` | |
| P9 | Tablets drying | P | window: noon | rows of clay tablets laid out in the sun by scribes | 20 min | daily | `goods/tablet` stacks | |
| P10 | Harvest offering | P | festival: harvest offering | farmers bring sheaves to the threshing floor, a priest offers bread | 4 min | Festival | priest, farmers | |
| P11 | Fire evening | P | festival: fire evening | people gather around the fire altar at dusk | 6 min | Festival | crowd | |
| P12 | Storks on the roofs | P | season: spring, day | storks clatter their bills on a nest | 10 s | Common | `bird/stork`, `sfx/stork_clatter` | |
| R1 | Night carts roll in | R | window: dusk to dawn | carts queue at the gates by day; at dusk they roll in, wheels rumbling on stone | night | daily | ox and mule carts, `sfx/cart_rumble` | |
| R2 | Morning callers | R | window: dawn | clients queue at a patron's door, the doorkeeper lets them in one by one | 4 min | daily | clients, doorkeeper | |
| R3 | Baths open | R | window: afternoon | crowds stream into the baths, steam from the vents | 3 h | daily | bathers, `fx/steam` | |
| R4 | Market day | R | week day 0 | extra stalls open in the forum, crowds thicken, vendors call | morning | Uncommon | stalls, vendors | |
| R5 | Races at the Circus | R | week day 0, afternoon | a roar rises and falls from the Circus; banners in the crowd | 20 min | Uncommon | `amb/circus_roar` | |
| R6 | Barges towed up the Tiber | R | window: day | oxen on the towpath pull a barge upstream; ropes creak | 3 min | Common | ox, barge, `sfx/rope_creak` | |
| R7 | Crane lifts a column drum | R | chain C10 sink | men in the treadwheel walk, the drum rises and is set; a cheer | 2 min | Uncommon | treadwheel crane states, workers | |
| R8 | Watchmen's round | R | window: night | the night watch walks with buckets and lamps | 2 min | daily | watchmen | |
| R9 | School under an awning | R | window: morning | a teacher and pupils with wax tablets under an awning by the forum | 1 h | daily | teacher, pupils | |
| R10 | Wedding procession | R | window: dusk, rare | torches, flute players, the bride led to her new home, nuts thrown | 3 min | Rare | wedding cast | |
| R11 | Street performer | R | window: afternoon | an acrobat or juggler draws a small ring of watchers | 3 min | Common | performer, audience | |
| R12 | Parilia bonfires | R, L | festival: Parilia | bonfires on the hills and in the streets; shepherds and young people leap over them | dusk to night | Festival | bonfire `fx`, leaping anim | |
| R13 | Fountain overflow play | R | window: hot day | children splash at a street fountain | 2 min | Common | children | |

Total: **78 events** (15 already designed for the corner, 63 new). Any city file may add more in the
same shape; this list is the baseline the engine and the asset lists are sized for.

---

## 6 Weather and nature as moving things

### 6.1 Weather cells

A weather cell is a token actor with `drift` locomotion:

| Field | Meaning |
|---|---|
| `kind` | `cloud`, `rain`, `storm`, `fog`, `dust`, `snow` |
| centre, radius | in tiles (cloud 8–20, rain 6–14, storm 16–30, fog follows low ground, dust 10–24) |
| velocity | the shared wind (§6.2) × `factor` (storms 1.2, fog 0.2) |
| intensity | an envelope: grow 20%, hold, fade 20% of its lifetime |
| lifetime | 2–10 game minutes |

- Cells spawn at the upwind edge of a region (or offshore for storms) from the climate table, decided
  by the region's day plan (§5.2), so they are deterministic. At most 6 cells per region, 24 in the
  world.
- **Clouds** draw soft shadows on the ground (`weather/cloud_shadow_v0-3`, large soft sprites
  multiplied at 25% under the world grading). **Rain** spawns raindrops only inside the cell's area
  and raises a **wetness** value per 8 × 8 tile block (rises 0.02/s under rain, dries 0.005/s); wet
  blocks darken ground by up to 15% and, above 0.6, show puddle decals (`fx/puddle`, hashed onto
  path and cobble tiles) with ripples while raining. **Fog** sits on tiles below the surrounding
  level (`world.md` §4 elevation) at dawn, drawn as layered translucent strips (`weather/fog_v0-3`)
  that drift and thin as the hour advances. **Dust** tints the area ochre and blows particles.
  **Snow** is rain in winter (`living-corner.md` R4.2) and settles on the peaks' backdrops.
- Weather at the camera (the strongest cell covering the view centre) drives the sky grey-out,
  rain sounds, and actor interrupts in the live area. Actors outside cells keep going about their day.
- The home region keeps working before the world exists: the rain toggle forces a rain cell over it.

### 6.2 Wind everything shares

- One wind vector for the world: direction drifts slowly with time (deterministic noise over game
  hours) plus a per-region bias (Athens summer: the north wind), strength 0–1 from the climate, plus
  **gust waves** that travel along the wind (the corner's gust delight, generalised).
- What reads it: tree, grass, reed and crop sway speed and amplitude; smoke and dust particles
  (moved by the vector); flags, banners, awnings and sails (art draws them blowing toward screen
  right; the engine mirrors them when the wind's screen-x component is negative, and picks `slack`
  or `full` frames by strength); weather cell drift; floating petals and leaves; chaff from threshing.
- On screen there are only two lean directions (left and right), which is all 2:1 pixel art can
  show cleanly; that is deliberate.

### 6.3 Sea, shores and rivers

- **Sea state** 0–3 per sea area, from the wind strength and storms. It drives the water animation
  speed, whitecaps (`fx/whitecap`) on open water at 2+, shore foam strength (an overlay on water
  tiles touching land, `terrain/water/foam/m<mask>/f<n>`), and ship pitch (a ±1 px bob per frame).
- **No tides.** The Mediterranean's tides are tiny; showing them would be wrong. Waves and swell do
  the work.
- **Rivers flow.** River tiles carry a flow direction (authored as polylines in the region map and
  rasterised to one of four grid directions). River water uses a directional overlay
  (`terrain/river/<n|e|s|w>/f<n>`, the engine mirrors two of them) that scrolls downstream, and
  `drift` objects on rivers (petals, leaves, a duck at rest) move with the flow. Barges go down with
  the current and up behind towing oxen (event R6).

### 6.4 Crops and animals with rhythms

- **Crops** are items with growth stages keyed by **calendar and climate**, not by the player:
  each crop lists, per region climate, the stage for each season (barley in Fārs: winter green,
  spring tall green, summer gold then stubble, autumn ploughed). Sprites use the corner's growth
  segment (`g<stage>`, `living-corner.md` R4.3). Reapers and threshers (events L2, L3) move the field
  from gold to stubble across the harvest day, tile by tile in their path.
- **Animal rhythms** are schedule filters: flocks out at dawn, back at dusk (L1); hens roost at dusk
  (corner); oxen work mornings and rest in the heat; swifts by day, bats at dusk, owls at night;
  cicadas at midday in summer; frogs at night by water; storks in spring.

---

## 7 Simulation at scale

### 7.1 Chunks and tiers

The world (up to 1024 × 512 tiles) is divided into **chunks of 32 × 32 tiles** (512 chunks at full
size). Every chunk is in one of three tiers, recomputed when the camera moves:

| Tier | Which chunks | What runs | Rate |
|---|---|---|---|
| **Live** | chunks touching the view rectangle grown by one chunk on each side | full actors: routines, locomotion, slots, goods, animation, sound, reactive events | every simulation step (60 Hz) |
| **Warm** | the next ring of one chunk | actors exist and move along their routines so they walk into view naturally; no animation, sound or reactive events | 10 Hz |
| **Abstract** | everything else | no actors. District activity curves, chain phases, the day plan, tokens | tokens at 1 Hz; the rest evaluated only on demand |

Hysteresis: a chunk drops a tier only when it has been outside the tier's ring for 2 s, so camera
jitter does not churn actors. A followed actor keeps its chunk and the eight around it Live.

### 7.2 Districts

Each region's map assigns every walkable tile to a **district** (`world.md` districts: agora, the
Kerameikos, the Subura, the terrace, the town of Pārsa, a village, a field). A district lists its
actor kinds with an hourly density curve (24 values) and a maximum per chunk. This is all the
abstract model of "people" there is.

### 7.3 Tokens

Tokens are the few things that must exist everywhere because they travel far: ships on lanes,
caravans and mule trains on roads, couriers, migrating flocks and weather cells. A token is
`{kind, lane or route, phase}` where the position is a function of time: a ship's position on its
lane is `lane.length × ((T + offset) mod period) / period`, with its port stays inside the period.
Limit: 256 tokens in the world. Arrival at a node raises `token_arrived` for the day plan, live or
not. When a token enters a Warm chunk it becomes a full actor (with its group); leaving, it becomes
a token again at its computed phase.

### 7.4 Materialisation: arriving somewhere that was alive all along

When a chunk becomes Warm:

1. For each district kind in the chunk, spawn `density(hour) × max` actors (rounded by hash), each
   with a **spawn key** `hash(world seed, region, chunk, kind, index, day)` that becomes its seed.
   Population actors bound to items (`per_item`) are keyed by the item instead, so the same baker
   always belongs to the same bakery.
2. Choose its schedule block for the current hour, its routine (seeded pick), and **where in the
   routine it is**: each routine has a nominal duration per step (from `dur` means and route lengths);
   the elapsed time since the block started, plus a seeded offset, picks the step and the progress
   in it. A traveller is placed on its route at that fraction; a worker is placed at its slot
   mid-animation; goods in hands and slot counters come from the chain phase (§3.3).
3. Group and cast actors of a running event are placed along the event's route at the event's
   elapsed time.
4. Spawning is spread over frames: at most 40 actors materialise per frame from a queue, ordered by
   distance to the view, so the frame budget holds when the camera jumps (fast travel shows a 0.4 s
   crossfade, which covers the first second of spawning).

Nothing about ordinary actors is saved. Only the day plan's inputs (seed, clock, calendar) and the
home region's state are. Leaving and returning shows the same people doing what they would be doing
now. Small personal deviations (an actor you petted, one that sheltered from rain) are forgotten when
its chunk goes Abstract; nobody can tell.

### 7.5 Budgets

| Item | Budget |
|---|---|
| Live actors | ≤ 400 simulated, of which ≤ 120 on screen (the area caps of §1.1 keep it lower) |
| Warm actors | ≤ 600 at 10 Hz |
| Tokens | ≤ 256 at 1 Hz |
| Actor record | 96 bytes, POD, in a preallocated pool of 1 024 (96 KB); kinds, routines and slots are shared, read-only |
| Slot state | 4 bytes per slot instance (reservation count, state, goods counter) for Live and Warm chunks only |
| Region tables | path graph and next-hop tables ≤ 1 MB per region; lanes ≤ 64 KB |
| CPU per frame (update only) | ≤ 0.6 ms of the 2 ms frame budget: Live actors ≤ 0.40 ms (≈ 1 µs each), Warm ≤ 0.08 ms, tokens, day plan, weather and events ≤ 0.05 ms, pathfinding ≤ 0.07 ms (queue), materialisation amortised inside the same budget |
| Draw | actors are sprites in the existing batches; no new draw calls beyond extra atlas pages; sorting reuses the item depth sort (`world.md` §8 item 3) |
| Allocation | none per frame: pools, fixed queues, and per-region tables built at load |

### 7.6 Pathfinding

- **Road graph per region**: nodes at junctions, doors, slots and landmarks' entrances; edges are the
  authored paths (`world.md` §8 item 8) with lengths and kinds (street, stair, towpath, quay).
  Typically 500–2 000 nodes.
- **Next-hop tables** toward each **destination node** (markets, gates, temples, quays, stations,
  district centres: at most 64 per region): one Dijkstra per destination at load, stored as a
  16-bit next-hop per node. An actor going to a destination reads its next hop in O(1). Trips between
  arbitrary nodes use A* on the small graph, cached (512 entries per region) and queued (at most
  8 searches per frame).
- **Last stretch**: from the graph node to a slot, a bounded grid search inside the Live window
  (at most 24 × 24 tiles). The home region uses this grid search alone (Laeticia, `living-corner.md`
  R6.5), since it is small.
- **Crowds**: when an event gathers many actors to one place (a procession's destination, a
  philosopher's ring, a bonfire), the engine builds one **flow field** on the Live grid toward the
  target (a BFS over at most 64 × 64 tiles, once per event) and the cast descend it with light
  separation steering.
- **Sea and river lanes**: authored polylines; ships never search.
- **Avoidance**: separation only, among actors sharing a tile bucket; no full local avoidance.
- **No per-actor A* across the world, ever.**

### 7.7 Determinism

- Every random choice in the system comes from streams derived from the game's one seed:
  `SplitMix64(seed ^ key)` with the key of the actor, region, event or day. This keeps the
  `CLAUDE.md` rule of one seeded generator owned by the game while letting actors be created in any
  order without changing each other.
- The day plan, token positions, chain phases and materialisation are pure functions of (seed, clock,
  calendar, region data), tested by recomputing them in a fresh process.
- Live simulation is deterministic for a given input script (fixed step, ordered updates by actor
  index, streams per actor).

---

## 8 The player's touch

### 8.1 In the home region

Everything in `living-corner.md`: building attracts visitors, Laeticia reacts, nooks change routines,
wishes. Unchanged; it now runs on this system.

### 8.2 Following any actor

- **F** with the pointer over an actor, or **Follow** on its card. The camera eases to keep the actor
  within the centre 30% of the screen, at the current zoom.
- A small glass pill at the top centre: "Following the baker · Taking bread to the stall · Esc to
  stop". The second part is the current step, from a short `label` on routine steps (optional; the
  verb and target name are used when absent: "Going to the mill").
- Following stops on any pan input, Esc, or when the actor leaves (enters a building: the camera
  waits 5 s at the door, then "Gone inside" and stop; a token leaving the region: "Sailed for Ostia").
- Works for animals, Laeticia, ships, delegations (follows the leader) and weather cells.

### 8.3 Gentle touches in the cities

Each touch has a cooldown, never changes saved state (apart from the journal's "seen" entries), and
is offered only by the hover cursor (hand) and the tooltip, never by a button.

| Touch | Where | What follows |
|---|---|---|
| Click a figure or walker | anywhere | its card (`world.md` §5): title, text, chain strip if any, Follow |
| Open a stall's shutters | a closed stall within an hour of opening time | the vendor comes out early, calls once; two nearby walkers drift over |
| Ring a bell or strike a gong | marked bells (a harbour bell, a shrine bell, a station gong) | pigeons or sparrows burst up, people nearby glance up, a keeper comes out and looks around |
| Feed the pigeons | a plaza with pigeons | seed scatters (`fx/seed`), pigeons crowd in, a child runs over (W13 after) |
| Light a lamp | an unlit lamp at dusk | it lights now; the lamplighter skips it and nods; moths arrive |
| Pet an animal | dogs, cats, donkeys, horses at rest, goats | heart, voice, a short reaction (`living-corner.md` R2.4) |
| Splash a fountain | street fountains | a splash; children nearby come to play (R13) |
| Knock on a door | marked house doors | a shutter opens, someone looks out, waves, closes it |

### 8.4 Watching time

Time controls fit a cozy game because watching is the point:

- **1×, 2×, 4×** world speed and **Hold** (the world freezes, the camera stays free; useful for
  postcards). Keys **1**, **2**, **3** and **0**; also in the calendar popover (`living-corner.md`
  §6.4) as four small buttons.
- Speed scales the simulation clock (actors, events, weather, growth, calendar). Wish pacing and
  play-time counters keep using real seconds, so wishes stay quiet at 4×.
- Hold is not pause: there is no menu and no blur; the ambience keeps its current bed at a lower
  level and one-shots stop.

---

## 9 Sound of a living place

### 9.1 Layers

| Layer | Driven by | Example |
|---|---|---|
| Region music | the region the view centre is in; crossfade over 8 tiles at region borders; day/night as today; stems in the home region | Athens day music fades in as you scroll east over the sea |
| Area beds | zones in the region map (`world.md` §8 item 11) and the current weather and season | sea wind on the Acropolis, the water channels of Pārsa, rain |
| **Count-driven beds** | the number of visible actors of listed kinds: gain = `min(1, sqrt(count / full))` | market murmur by visible vendors and customers (`full` 12); crowd roar at the Circus; harbour busy-ness by dock workers |
| Positional loops | an actor's step or a slot's state | the smith's hammering only while the smith `use`s the anvil; a ship's creak; a fountain |
| Positional one-shots | animation frame events, steps (`emit`), events | a hoof on each step frame of a passing cart; a vendor's call; a door; goods changing hands |

### 9.2 Placement and mixing

- **Stereo pan** by the source's screen x (−1 at the left edge, +1 at the right; clamped at ±0.8 so
  nothing sits in one ear). **Distance gain**: 1 within 6 tiles of the view centre, falling linearly
  to 0 at 1.2 × the half-diagonal of the view. Zoom does not change gains.
- **Budgets**: at most 12 one-shot voices and 8 loops at once (music stems count as one loop per
  piece, area and count beds one each). When over budget, the farthest and quietest are dropped
  first; one-shots of the same sound within 80 ms merge into one.
- **Levels**: music about −18 LUFS, beds −21 to −23 (`CLAUDE.md`); count-driven beds at full count
  sit at bed level; positional one-shots are mixed by their loudest 100 ms like other effects, played
  at `kPositionalLevel`. When count-driven beds together exceed −20 LUFS short-term, music ducks by
  up to 3 dB over 2 s, so a busy market can be heard over the score.
- The corner's "no positional sound" cut is reversed by this section (edit made in
  `living-corner.md` §10).

---

## 10 Build order

Six engine tasks, each sized for one agent, run in order in the engine lane. W1–W3 make the corner
lively and replace parts of `living-corner.md` task B; W4–W6 scale to the world. The city
infrastructure itself (regions on one map, large maps, elevation, landmarks, multiple atlases) is
the city engine track of `world.md` §8 and is a prerequisite of W4.

| Task | Builds | Alive on screen when done | Tests | Art | Audio |
|---|---|---|---|---|---|
| **W1 Actors** | actor kinds and the visitor reading of §2.5; pool, routines (all steps but `each`/`if`), schedule filters, interrupts, locomotion `walk` (home grid), `swim`, `fly`; implicit and explicit slots with reservations; groups with `line` and `cluster`; petting and startle (`living-corner.md` R2.4–R2.5); hover names | the corner's visitors use what you build: the cat naps on the bench, ducks swim in a line and sleep on the bank, bees commute, hens go home to the coop | unit: schedule filter matrix; pick weights for a fixed seed; slot reservation and release; line spacing; routine step transitions; record size is 96 bytes. Scripted: cat on bench, ducks at night, bees entering the hive, petting a hen (shots). Bench: 400 synthetic actors ≤ 0.4 ms | the corner's critter animations (`living-corner.md` §7.4) | none new |
| **W2 Laeticia and goods-lite** | `each`, `if`, `say`, `effect` hooks; the resident presence; her schedule and routines from `catalog.next.json`; bubbles and lines; reactions; nook routines; goods in hands and slot stacks (C1, C2) | Laeticia's whole day: wakes, waters, feeds the hens, reads, sketches, warms at the fire, goes home; carries the harvest home | unit: her block at each hour and with a pinned clock; each-order; goods counters capped at 3; line rotation. Scripted: her day at four clock times; a harvest carried home | Laeticia (`living-corner.md` §7.4), `goods/produce` (reuses `fx/produce`), `goods/feed` | `sfx/laeticia_*` (already listed) |
| **W3 Events, wind, weather, sound** | the event scheduler (day plan and reactive), all H events; the shared wind and gust waves; weather cells (rain, cloud), wetness and puddles; the three-way weather toggle; positional sound, count-driven beds, budgets | clouds drift over the corner, a shower crosses it and the paths darken, a rainbow follows; gusts ripple through the garden; everything leans the same way | unit: day plan identical across runs and across "visited/not visited"; cell drift positions at given times; wetness curve; pan and gain maths; voice budget drops. Scripted: shower crossing with shots before, during and after; rainbow | `weather/cloud_shadow_v0-3`, `fx/puddle`, flag mirroring needs none | `sfx/thunder_far` (later), existing beds |
| **W4 Scale** | chunks and tiers, districts and densities, tokens and lanes, materialisation, road graphs, next-hop tables, cached A*, flow fields, follow camera, time speed and Hold, the liveliness probe | on the synthetic test world (a 512 × 256 map with two towns, a road, a sea lane and a field): scroll anywhere and people are mid-errand, ships are on their way, nothing pops | unit: materialisation reproducible for a chunk at a time; token positions; next-hop correctness against Dijkstra; queue limits. Bench: camera sweeps across the test world at 4× with ≤ 2 ms frames and ≤ 40 spawns per frame; liveliness probe passes | generic walker set (2 kinds × 3 variants), cart, ship test sprites | positional test set |
| **W5 Chains and touches** | chain declarations, sources/sinks, clocked phases, slot states (shutters, lamps), the lamplighter pattern, chain strip on cards, following a chain, the city touches | on the test world: bread moves from a ship to a bakery to a customer; shutters open in the morning and close at dusk; lamps are lit on a round | unit: chain phase formula vs live run after N periods (counters never exceed 3, never negative); sink fallback; slot state at given hours in both tiers. Scripted: follow a sack from ship to customer (shots at each stage) | `goods/*` for the test chain, stall state layers | goods-change sounds (wood, cloth, clay, stone) |
| **W6 City life** (one per city: W6a Athens, W6b Pārsa, W6c Rome, plus sea and roads with the first) | the region data: districts, populations, schedules, chains, events, lanes, climate; no new engine features, only data and the region's actor art | each city meets the liveliness targets; its festival plays; its chains run | liveliness probe per city; event table coverage (every event fires in a 2-game-day 4× run); frame budget at the city's busiest hour | the city's walker, animal, goods and event sprites (from the city files and §5) | the city's beds, count beds and one-shots |

### 10.1 What moves from the corner spec onto this system

- `living-corner.md` R2 (visitor behaviours, petting, startle) **is** W1. The catalog's visitor
  entries are read as actor kinds (§2.5); no catalog change is needed for them.
- `living-corner.md` R6 (Laeticia) **is** W2. Her routine becomes data (`resident.schedule`,
  `routines`, `interrupts`, added to `catalog.next.json`); R6 keeps the rules the data does not
  express (movement costs, bubbles, displacement, home choice).
- `living-corner.md` R9 and §5.8 (delights) **are** W3 events (H1–H15). The waterfall, lamp moths
  and the cat watching the cursor are states rather than events and stay as written.
- `living-corner.md` task B in §9 is therefore W1 + W2 + W3 plus the front door, builder comforts and
  postcards (which stay a separate task, "B′").
- Items gain explicit `slots` in `catalog.next.json` where the corner needs named ones (bench seat,
  cottage door, planter tend, coop feed, beehive entrance, campfire warm, hammock lie, picnic seats,
  well, lamp light, hay bale and stump seats). Everything else uses implicit slots.

---

## 11 Notes for `world.md` (city researcher)

`world.md` was written for separate places; under the one-map direction these sections should be
read as follows (not edited here; the researcher owns that file):

- `place.json` `walkers`, `figures` and `events` become `actors` (§2), `groups`, `events` (§5),
  plus `districts`, `chains` (§3), `lanes` and `climate` (§4.3) in each region's data file.
- `figures[].presence` (present, statue, memory, shrine, reenactor) maps to actor presence:
  `present` → `resident`; `memory` → a schedule block at dusk and night with a translucent draw flag;
  `shrine` apparitions → event-cast actors tied to weather or festivals (P5); `statue` → a landmark
  card, not an actor; `reenactor` → festival cast.
- `place.json` `clock.day_length_s` per place does not apply: one clock (§4.1).
- The occupation tables (`persepolis.md` §6.3) are already in the right form: each row is an actor
  kind with a slot, steps, a time window and an output; the "visible chains" lines are chain
  declarations (§3.4 C3–C6 are taken from them).
- Walker kinds with animation lists (`persepolis.md` §3.6) map to `anims`; add `carry` with a
  `goods_at` offset to every kind that carries.

---

## 12 Risks

| Risk | Mitigation |
|---|---|
| Content volume: each city needs dozens of walker kinds, animations and goods | Kinds share routines and slots; colour variants multiply looks cheaply; the generic walker set ships first; liveliness targets are met with the must-have kinds |
| Materialised actors looking "placed" (all mid-step at once) | seeded offsets within steps; 30% of spawns start in travel; warm ring lets actors walk in from off-screen |
| Live drift from the clocked chain and day plan producing visible jumps | changes happen only when an area goes Abstract and comes back; the warm ring and hysteresis keep that off-screen |
| CPU at busy hours in dense cities | hard caps per chunk; budgets per tier; the bench gates each W6 task |
| Too much going on | the caps of §1.1, one event start per 20 s, one crowd per screen, sound budgets; the probe fails on over-cap as well as under |
| Historical accuracy in routines and events | every city event comes from the city files; where uncertain (night carts, the Romaea renaming) the card says "probably" or "tradition says" |
| One seed, many streams | derived streams keep the one-seed rule; flagged here for the orchestrator in case `CLAUDE.md` should say so explicitly |
| The corner losing its intimacy among cities | the home region keeps its own targets (3–6 movers), its own music stems and Laeticia; cities are elsewhere on the map |
