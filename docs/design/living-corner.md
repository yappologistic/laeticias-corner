# Living Corner: design spec for batch 2

This is the source document for the next batch. The corner is the player's home region in what
will later become one continuous world map (§2.1, §13). It turns the toy into a small game with a gentle
goal structure: Laeticia and the visitors make wishes, granting them unlocks pieces, what you build
is recognised and used, the sketchbook fills, and the wild land around the corner opens up.
There is still no money, no timer that punishes and no fail state.

The companion file `docs/design/catalog.next.json` is the complete next catalog. Every table in
§5 is generated from the same data, so the two cannot disagree. If they ever seem to, the JSON wins.

User-facing text uses **British spelling** throughout (colour, favourite, cosy, grey).

## How to read this document

| You are | Read |
|---|---|
| Engine, task A (progress loop) | §1, §2, §3, §4 R1, R3, R4, R5, R7, R8, §5, §6 (marked **A**), §9, §11, §12, §13 |
| Engine, task B (life and front door; items 1–3 are `living-world.md` W1–W3) | §1, §2.1, §3, §4 R2, R6, R9, R10, R11, R12, §5, §6 (marked **B**), §9, §11, §12, §13 |
| Art | §1, §4 (skim R2, R4, R5, R6 for what the sprites do), §7 |
| Audio | §1, §4 R8 and R9, §8 |

Rule numbers (R1 to R12) match the twelve features in the brief.

---

## 1 Overview

### 1.1 The core loop

You build in a small cleared corner. What you build changes the corner: visitors arrive when their
needs are met, beds grow, compositions you make are recognised as **nooks**, and Laeticia, who lives
here, walks about using it all. Laeticia and the visitors make short, optional **wishes**; granting
one (by building what it asks for) unlocks new pieces. Every visitor seen and every nook found is a
page in Laeticia's **sketchbook**, and as the sketchbook fills, the wild land around the corner
opens in stages, each hiding something to find underneath, until the corner reaches an old road and
a gate where the wider world will one day begin. The music grows a layer at a time with
your progress. None of it can be lost, and nothing waits on real time.

```
            ┌──────────────────────────── build ◄───────────────────────────┐
            ▼                                                                │
   the corner changes ──► visitors arrive, nooks are recognised,             │
            │              beds grow, Laeticia uses what you made            │
            │                                │                               │
            ▼                                ▼                               │
   wishes are offered ◄── Laeticia and visitors notice things          new pieces
            │                                                                ▲
            └── grant a wish (build what it asks) ──► unlocks ───────────────┘
                                     │
          every new visitor and nook ▼
                         sketchbook pages ──► wild land opens (stages 1–4)
                                     └──────► music gains layers
```

### 1.2 Design guardrails

- **Nothing is ever taken away.** Unlocks, pages and opened land are permanent. Undoing a build after
  a wish was granted does not revoke the reward.
- **Nothing decays.** Ripe beds stay ripe, wishes never expire, the calendar only moves while you play.
- **The game never seizes the camera.** Flourishes happen where they happen; at most an edge chip
  points the way and you choose to look.
- **Everything is optional.** You can ignore every wish and still build freely with what you have.
  A world can also be started in Free build, with everything open from the start.
- **Quiet by default.** At most three open wishes, one new wish offer every 75 seconds at most,
  one speech bubble at a time.

### 1.3 The first ten minutes (new player)

| Time | What happens |
|---|---|
| 0:00 | Title screen over a softly drifting island at dawn. One button: **Begin**. A small dialog asks for a name for the world (default "Laeticia's Corner"). **Create**. |
| 0:05 | The island fades in. A cleared 20×20 corner at the front: a little pond with a lily pad, a meadow patch with one patch of daisies and one of poppies, a few oaks, two pines, a bench, a path stub. Behind it, dark bramble-covered wild land. Laeticia stands beside her bedroll and waves: "Oh, it's lovely. A bit bare, though." Ducks are already paddling on the pond. |
| 0:10 | Tour (R10.5): "Drag to look around." The player pans. |
| 0:18 | "Open Build to plant something." The drawer shows nine pieces. "Pick the daisies, then click the ground." A soft note plays on the place sound. |
| 0:30 | Laeticia's first wish slides into the wish tray: four flower patches. The card reads **3 / 4**. One more flower. The wish is granted with a warm four-note rise; Lavender and Berry bush appear in Build with a dot. Butterflies arrive. Laeticia: "A butterfly. Hold still, I'll draw it." The music-box melody joins the music. Tour ends: "That's all. Make yourself at home." |
| 1:30 | Second wish: a cottage. The player places it; the cat moves in at once. Smoke rises from the chimney. Veggie bed and Lamp post unlocked. |
| 3:00 | Two wishes open at once: a path to the cottage door (Laeticia), a bench by the cottage (the cat). Pine, cobble, blossom and mushrooms follow. The cat naps on the new bench. |
| 4:30 | Three veggie beds. They start as bare soil and sprout within three minutes. Hen coop and scarecrow unlocked. A coop brings hens. |
| 6:00 | Dusk. The lamps glow. A bench with a lamp and a tree beside it becomes the **Reading nook**: sparkles, a chime, a floating label, a new page. That is page 4 (ducks, butterflies, cat, nook) and the **west meadow opens**: brambles clear in a wave, revealing a stream that spills over the island's edge as a waterfall. |
| 7:30 | Night. Laeticia says goodnight and goes into the cottage; its windows glow. The "reading light" wish completes now that it is dark: campfire and stump unlocked. |
| 9:00 | Dawn. Laeticia waters the beds. The first bed ripens. "Something's ripe, if you want to pick it." The player clicks it; a carrot pops out and flies to her basket. Soup tonight; the well is unlocked. |
| 10:00 | Three open wishes, five pages, a strip of new land to fill, three music layers playing. |

### 1.4 Day three (a returning player)

Nothing changed while they were away: the corner opens at the moment they left it. Laeticia waves
("There you are. Kettle's on."). It is summer now, about forty minutes of play in. The wish tray
holds a hen wish (beds nearer the coop), a firefly wish (a dark patch of long grass) and a duck
wish. The sketchbook says **11 of 30 pages, 3 more until the old orchard opens**, and lists rarer
visitors as silhouettes with hints: "Watches from the pines at night." They try it, putting a stump
among pines, and pin the clock to night to see. An owl lands on the stump; a new page; the
orchard opens. Laeticia wanders over: "An old orchard. Somebody loved this place once." They spend
the rest of the session filling the orchard's gaps, then take a postcard of it at dusk with the
Pressed flowers frame.

---

## 2 The home region, saves and scope

### 2.1 One world, one home region

Later batches turn the game into **one continuous world map**. Laeticia's corner is the player's
own buildable **home region** on it; large prebuilt historical cities, and the land and sea between
them, lie elsewhere on the same map, reached by scrolling or by fast travel from an overview. There
are no separate levels.

In this batch the home region is the whole map: the 40×40 floating island. Everything is stored so
that nothing has to move when the world grows around it:

| Level | What it is |
|---|---|
| **Profile** | One per player: settings shared by every save |
| **World save** | One per save file (the title screen lists these): the whole world and all progress. A save is named after its home corner ("Plum Hollow") |
| **Home region** | Inside the world save: the buildable land, its map and items |

Every piece of saved state and where it belongs:

| State | Scope | Notes for the wider world |
|---|---|---|
| Volumes, mute, fullscreen, UI scale, reduce motion, chatter, grid, brush size, frame and caption choice, `onboarded`, last save played | Profile | shared by all saves |
| Name, free-build flag, created, play time | World (global) | |
| Clock time and pin, rain or snow | World (global) | one sky over the whole map |
| Calendar day, season pin | World (global) | the season is the same everywhere |
| Unlocked pieces, postcard frames, new-piece dots | World (global) | pieces can be used wherever building is allowed (today: the home region only) |
| Wishes: open, granted, snoozed, last offer | World (global) | goals are evaluated over the home region (§3.2); hooks in §13 |
| Clues | World (global) | |
| Visitors seen (sketchbook) | World (global) | later shown per region (§13) |
| Nooks discovered | World (global) | instances can only exist in the home region, the only buildable land |
| Harvest count, last harvest day | World (global) | |
| Music layers | World (global), derived from progress, not saved | |
| Terrain, items, growth | Home region | |
| Opened land stage | Home region | |
| Visitor presence, nook instances, Laeticia's state | Home region, recomputed on load, never saved | |

Rules, decided now:

- **Only the home region is buildable.** The rest of the world will be prebuilt, loaded from data
  and not saved; this design adds no saved state for it.
- **Home coordinates stay home-relative.** The home region keeps its own tile coordinates (0–39).
  When the world exists, the region sits at an origin offset inside the world grid; saves keep
  home-relative coordinates, so they never need rewriting when the world around them changes.
- **Conditions are evaluated over the home region.** A later batch may add an optional `region` key
  to `count`, `near` and `visitor`; without it they mean the home region, so every condition
  written now keeps its meaning. Progress terms (`progress`, `seen`) are global.
- **Laeticia lives in the home region** and offers her wishes there.

### 2.2 Files on disk

```
<save dir>/
  profile.json                     global settings (§2.3)
  worlds/<slug>/world.json         one world save (§2.4)
  worlds/<slug>/thumb.png          384×240 thumbnail of the home region for the worlds screen
  corner.v1.json                   the old single save after migration (kept, never read again)
postcards: see R12.4
```

`<save dir>` is resolved exactly as today (`--save-dir`, `$LAETICIA_SAVE_DIR`, SDL pref path).
`<slug>` is made from the name at creation: lowercase ASCII letters and digits, every other run of
characters becomes `-`, trimmed, at most 32 characters, `world` if empty, `-2`, `-3`… on collision.
Renaming a world never renames its folder.

### 2.3 `profile.json`

```json
{ "version": 1,
  "volume": { "music": 70, "effects": 85, "ambience": 60 }, "muted": false,
  "fullscreen": false, "ui_scale": "auto", "reduce_motion": false, "chatter": "chatty",
  "grid": false, "brush": 1, "frame": "plain", "caption": true,
  "onboarded": false, "last_world": "laeticias-corner" }
```

`ui_scale` is `"auto"` or one of 0.75, 1, 1.25, 1.5, 2. `chatter` is `"chatty"` or `"quiet"`.
`brush` is 1, 3 or 5. A missing or malformed profile falls back to these defaults field by field.
Written atomically, debounced 0.5 s after a change.

### 2.4 World save format, version 2

```json
{ "version": 2,
  "name": "Plum Hollow", "free_build": false,
  "created": "2026-11-17T10:42:00Z", "played": 5234.5,
  "clock": { "t": 0.31, "pin": "auto", "day": 7 }, "season_pin": "auto",
  "settings": { "rain": false },
  "progress": {
    "unlocked": ["oak", "bush", "…", "cobble"],
    "frames": ["plain", "starry"],
    "wishes": { "open": ["hen_fence"], "done": ["first_flowers", "a_roof"],
                "snoozed": { "reading_light": 4100.0 }, "last_offer": 4980.0 },
    "clues": ["owl"], "seen": ["duck", "cat"], "nooks": ["reading_nook"],
    "harvests": 3, "last_harvest_day": 6, "new": ["sunflowers"] },
  "home": { "map": { "w": 40, "h": 40 }, "palette": ["grass", "…"], "terrain": [0, 0, "…"],
            "items": [ { "id": "planter", "x": 24, "y": 31, "v": 2, "g": [1, 0.42] } ],
            "stage": 2 } }
```

- Everything outside `home` is global to the world save; `home` is the home region (§2.1).
- `played` is active play time in seconds (unpaused, not on the title screen). Wish snooze and
  offer pacing are measured against it.
- `clock.day` is the calendar day counter (R4.1). `season_pin` is `auto` or a season id.
- `progress.new` lists unlocked pieces whose "new" dot has not been seen yet.
- Item `g` is `[stage, progress]`, present only for items with `growth`. Coordinates are
  home-relative.
- `home.stage` is the highest opened land stage.
- Unknown ids are dropped with a warning, exactly as v1 does today. A save naming a newer version
  is refused and left untouched.

### 2.5 Migration from version 1

On launch, if `<save dir>/corner.json` exists (v1) and `<save dir>/worlds/` does not:

1. Read it with the v1 loader. If it fails, leave it alone and start as a first launch.
2. Create the world save "Laeticia's Corner" (`worlds/laeticias-corner/`). Copy the 20×20 terrain and
   items into the 40×40 home region at offset **(+20, +20)**, which is exactly land stage 0. Items
   keep their variants; planters get `g = [3, 0]` (ripe), since they already looked ripe.
3. **Unlocks:** the start palette **plus every piece that existed in v1** (`progression.legacy`: all 31
   original items and all five terrains). A returning player never loses a tool they had. The 11 new
   items, the frames and the clues still come from wishes.
4. **Wishes:** every wish whose reward is only `unlock` and whose pieces are all already unlocked is
   marked done silently. The rest are offered normally (an unlock wish that is partly covered grants
   only its new pieces).
5. `journal` becomes `progress.seen`. Clock time and pin carry over; the calendar starts at Spring,
   day 1. `settings.muted` moves to the profile; `settings.rain` stays in the world save.
6. Nooks already present are discovered silently at first load. Land stages whose page threshold is
   met open instantly, with their reveals, without the wave.
7. Write the v2 save and thumbnail, then rename `corner.json` to `corner.v1.json`.
8. Show one welcome card on first load: "Welcome back. Laeticia has started a sketchbook: *n* pages so
   far." Old photos in `<save dir>/photos/` stay where they are.

---

## 3 Condition vocabulary

One vocabulary is used by wish goals and gates, rare-visitor recipes, nooks and music layers.

### 3.1 Shape

A condition is a JSON object with **exactly one key**:

| Key | Value | True when |
|---|---|---|
| `all` | `[Condition, …]` | every entry is true (an empty list is true) |
| `any` | `[Condition, …]` | at least one entry is true (an empty list is false) |
| `not` | `Condition` | the inner condition is false |
| `count` | `Selector + {"min": N, "max": N}` | the number of matching items (instances) or terrain tiles in the home region is ≥ `min` (default 1) and ≤ `max` (if given) |
| `variety` | `{"tag": T, "min": N}` | at least N different item ids carrying tag T are present |
| `near` | `NearSpec` (below) | enough anchors each have everything listed in their surroundings |
| `time` | `["day", "dusk", "night", "dawn"]` (subset) | the current phase is listed |
| `season` | `["spring", "summer", "autumn", "winter"]` (subset) | the effective season is listed |
| `weather` | `"rain"` or `"clear"` | rain (or snow) is on / off |
| `visitor` | `{"id": V, "min": N}` | at least N critters of V are present in the home region and not leaving (default 1) |
| `seen` | `V` | visitor V is in the sketchbook |
| `nook` | `NookId` | at least one instance of that nook exists in the home region right now |
| `progress` | `{"wishes"\|"seen"\|"nooks"\|"pages"\|"harvests"\|"stage": N}` (one or more keys) | each listed counter is ≥ N |

**Selector** (picks what to count), exactly one of:

```json
{ "item": "bench" }   { "items": ["bridge", "stepping_stones"] }   { "tag": "flower" }
{ "terrain": "water" }   { "terrains": ["path", "cobble"] }
```

Tags are listed per item in the catalog (`items[].tags`). The tags in use: `flower`, `tree`,
`shrub`, `seat`, `light`, `line`, `crop`, `home`, `stone`, `crossing`.

**NearSpec**:

```json
{ "near": {
    "anchor": { "item": "bench" },
    "within": 1,
    "has": [ { "item": "lamp", "min": 1 }, { "tag": "tree", "min": 1 }, { "tag": "light", "max": 0 } ],
    "anchors": 1 } }
```

- `anchor`: a selector. Every matching item instance (or terrain tile) is a candidate anchor.
- `within`: 1 to 4. The anchor's **area** is every tile at Chebyshev distance 1..`within` from any
  tile of the anchor's footprint. The footprint itself is not part of the area.
- `has`: selectors with `min` (default 1) and optional `max`. An item counts once if any tile of its
  footprint lies in the area; the anchor instance itself never counts. Terrain counts tiles in the area.
- `anchors`: how many distinct anchors must satisfy every `has` entry (default 1).

### 3.2 Semantics and edge cases

- **Wild land does not exist for conditions.** Terrain counts, areas and item counts only consider
  opened tiles (nothing can be placed on wild tiles anyway). The world keeps per-terrain counts for
  opened tiles only.
- **Out-of-map tiles** in an area are simply not counted.
- **Time** uses the displayed phase, so a pinned clock counts. Pinning night to see the owl is fine.
- **Season** uses the effective season (the pin if set, otherwise the calendar).
- `max: 0` means "none of these in the area"; such an entry never needs anything unlocked.
- Items placed by a land reveal or the starter scene count exactly like placed ones, locked or not.

### 3.3 Evaluation

- Re-evaluate everything when: the world revision changed and no edit group is open (so a drag
  counts once, at release), debounced 0.25 s; the phase, season or weather changed; a visitor
  arrived or left; a progress counter changed.
- `near` stops as soon as `anchors` anchors pass. Everything is plain loops over the item list and
  the occupancy grid, no allocation. Budget: a full evaluation of every wish, recipe, nook and music
  condition stays under 1 ms on a full 40×40 map (add it to `--bench`).
- **Waiting display.** The evaluator has a mode that treats `time`, `season` and `weather` terms as
  true. If a wish goal is false normally but true in that mode, its card shows "Waiting for
  nightfall" (or dusk, dawn, daytime, a season, rain, clear skies), naming the first such term that
  is false.
- **Progress display.** If a wish goal is a top-level `count`, the card shows `current / min` with
  the wish's `progress` label ("3 / 4 flower patches"). Other goals show nothing until met.
- `nook` instances are enumerated by the same `near` code: each passing anchor is one instance, with
  its area kept for hover outlines and for behaviours that prefer the nook.

---

## 4 Rules

### R1 Wishes and unlocks

**R1.1 Unlocks.** A world save has one global set of unlocked terrain, item and frame ids. A new world starts
with `progression.start`: Ground: grass, meadow, path, water. Items: oak, bush, poppies, daisies,
tall grass, rock, bench, fence, cottage. Frame: plain. Everything else comes from wishes (the full
tree is in §5). Free-build worlds start with everything unlocked.

- The Build drawer lists only unlocked pieces. Each tab ends with a dimmed **"+N"** tile (lock icon)
  when that tab still has locked pieces; its tooltip reads "N more to discover. Grant wishes to
  unlock them." Clicking it opens the sketchbook on the Wishes tab. It is hidden once a tab is complete.
- Locked pieces that are already in the world (starter scene, land reveals, migrated saves) can be
  moved and removed; undo can restore them. They cannot be placed again until unlocked, and the
  eyedropper refuses them ("Not unlocked yet").
- A newly unlocked piece gets a dot on its drawer tile, its tab and the Build button until the
  pointer hovers the tile (`progress.new`).

**R1.2 Wish data** (`wishes[]` in the catalog, documented in §11):

```json
{ "id": "path_to_door", "giver": "laeticia", "after": ["a_roof"],
  "requires": { "progress": { "stage": 1 } },
  "text": "A path up to the door, so I stop tracking mud inside.",
  "goal": { "near": { "anchor": { "item": "cottage" }, "within": 1,
                      "has": [ { "terrains": ["path", "cobble"], "min": 3 } ] } },
  "thanks": "Much better. My boots thank you.",
  "reward": { "unlock": ["cobble", "pine"] } }
```

`giver` is `laeticia` or a visitor id. `after`: wishes that must be granted first. `requires`
(optional): an extra condition that must hold at the moment of offering. `progress` (optional):
label for a top-level `count` goal. `reward` has one or more of `unlock` (item and terrain ids),
`frame` (a frame id) and `clue` (a rare visitor id whose exact recipe becomes visible in the
sketchbook).

**R1.3 Wish states.** `locked` → `offerable` → `open` → `granted`, plus `snoozed`.

- **Offerable** when: not open, granted or snoozed; every `after` wish is granted; `requires` holds;
  every item and terrain that the goal needs (all selectors with a positive `min`) is unlocked;
  and the giver is available (below).
- **Giver available**: a visitor giver must be present in the home region. Laeticia must be out and about
  (not inside or asleep), so she never offers at night. Until task B adds her to the world, treat
  her as available in every phase but night.
- **Snoozed** wishes return to the pool after 600 s of play, ranked after unsnoozed ones.

**R1.4 Pacing.** Checked once a second while playing (not paused, not in photo mode, not during the
tour except where the tour offers the first wish).

- At most **3** open wishes.
- A new offer needs **75 s** of play since the last offer or grant (**30 s** if no wish is open).
- The wish chosen is the **first offerable one in catalog order** (that order is the gentle
  storyline; it also makes scripted runs deterministic).
- Offering: the card slides into the wish tray with `sfx/wish.wav`. If the giver is on screen, a
  small sparkle marker floats above it for 6 s. Laeticia also says a `wish_offer` line.
- Wishes never expire and never nag. There is no reminder.

**R1.5 Granting.** When an open wish's goal is true at two evaluations at least 1.5 s apart (so a
passing state during a drag or an undo does not count), it is granted:

- The card glows and leaves the tray; the giver shows a heart (`fx/heart`) or, for Laeticia, the
  wish's `thanks` in her bubble. `sfx/wish_granted.wav`.
- An unlock ribbon (a wide toast) shows "Wish granted" and the new pieces' icons: "New in Build:
  Cobble, Pine". Frames: "New postcard frame: Starry night". Clues: "Laeticia's note added to the
  sketchbook".
- If the goal was already true when the wish was offered, it is granted 3 s after the offer and
  Laeticia says an `already_done` line instead of `wish_offer`.
- Rewards are permanent (guardrail 1). The `wishes` counter goes up by one.

**R1.6 Not now.** Every open card has a small "Not now" action (in the sketchbook card, and on
right-click in the tray). It snoozes the wish (R1.3) and frees the slot. No penalty.

**R1.7 Save data:** `progress.wishes.open`, `.done`, `.snoozed` (id → `played` time when it may
return), `.last_offer`; `progress.unlocked`, `.frames`, `.clues`, `.new`.

### R2 Visitors that use what you build

> **Built on the shared actor system** (`living-world.md` §2, task W1). The catalog's visitor
> entries are read as actor kinds there; the `activities` below are its `pick` options, unchanged.

**R2.1 Activity model.** Each visitor has a list of **activities** in the catalog. A critter is
always in one of these states:

```
             ┌────────────── pet click ───────────────┐
 Arriving ──►│ Choose ──► Travel ──► Act ──► Choose … │──► Leaving (fade 0.8 s)
 (fade 0.8 s)└───── startle (placement nearby) ───────┘
```

- **Choose**: pick an activity by `weight` among those whose `time` and `seasons` allow it and whose
  target exists (anything with a target that has no instance is skipped). If the visitor has a
  `cycle`, it runs the listed activity ids in order instead (bees). `wander` is the current
  behaviour and is always available.
- **Travel**: move to the activity's spot, at the habitat speed (land and water critters use the
  current straight-line move with `pathClear`; three failed attempts drop back to Choose).
  `spot: "on"` targets the item's footprint centre and lifts the critter to the item's `perch` height
  in pixels; `"beside"` targets the nearest free tile next to the footprint that the habitat allows.
  `{"here": true}` acts where the critter stands; `{"bank": true}` is a land tile next to water;
  `{"shore": true}` is a water tile next to land or a land tile next to water; `{"resident": true}`
  is Laeticia (follow at 1 tile, or sit on her hat for butterflies).
- **Act**: play `anim` for a random duration in `dur` seconds. `anim: "enter"` fades the critter
  into the item (alpha 0) for the duration and back out (bees in the hive, hens in the coop).
  `every` plus `call_anim`: during the activity, every `every` seconds play `call_anim` once and the
  visitor's voice (owl hoots, frog croaks, heron strikes).
- **Pet**: see R2.4. **Startle**: see R2.5.
- An activity that targets an item stops early if that item is removed or moved.

The facing of a sitting or perched critter follows the item's rotation where it has one: `r0` faces
+x (front), `r1` faces +y (front, mirrored), `r2` faces −x (back, mirrored), `r3` faces −y (back).
This is an art contract for seats (bench, picnic table, hammock): the open side faces that way.

**R2.2 Per-visitor behaviour** (exact data in the catalog's `visitors[].activities`):

| Visitor | Activities (weight, duration) | Special | New animations |
|---|---|---|---|
| Cat | nap on a [seat] by day and dusk (3, 30–60 s); sleep beside a campfire at dusk and night (5, 40–80 s); sit by the cottage door (2, 10–25 s); groom (2, 4–8 s); follow Laeticia by day (1, 10–20 s); sleep by the cottage at night (2) | pet: sits and purrs. Placing within 1 tile of a sleeping cat wakes it: `stretch`, then Choose | `sleep`, `sit`, `groom`, `stretch` |
| Hens | peck beside a veggie bed (4, 4–10 s); peck where they stand (3, 3–6 s); wander (2) | `home: coop`: when their time ends (night) they walk to the nearest coop and enter instead of fading where they stand, and come out of it at dawn. When Laeticia scatters feed within 6 tiles, every hen travels to her and pecks for 6 s. After a harvest, hens within 5 tiles go and peck at that bed. Startle 1.5 tiles | `peck`, `flap` |
| Ducks | wander (3); dabble (2, 2–5 s); at night, waddle onto a bank and sleep (10, 60–120 s) | `line: true`: the first duck leads; each other duck targets a point 0.7 tiles behind the one before it, so they swim in a line. They sleep side by side on the bank, preferring a Duck cove. Startle 2 tiles | `dabble`, `sleep`, `waddle_front`, `waddle_back`, `flap` |
| Bees | cycle: sip at a [flower] within 6 tiles of the hive, sip again, enter the hive (3–6 s) | `hide_in_rain`: they stay in the hive (hidden) while it rains | none |
| Butterflies | rest on a [flower] (4, 3–8 s); wander (2); rest on Laeticia's hat once she has sat for 20 s within 4 tiles (1, 6–12 s) | `hide_in_rain` (fade out until it stops) | `rest` |
| Fireflies | wander near what attracted them | prefer a Firefly hollow | none |

Rare visitors use the same model (R3.3).

**R2.3 Hens and ducks at times they do not visit.** Today a critter whose time has ended fades where
it stands. Visitors with `home` walk home first (hens). Ducks have `time: any` and simply switch to
`sleep_bank` at night.

**R2.4 Petting.** With no tool selected, hovering a critter shows a hand cursor and, after 0.5 s,
its name. Clicking it:

- The critter stops, faces the camera, plays its `pet.anim` (or idle) for 1.5 s, then resumes
  where it was (the activity timer keeps running).
- A heart (`fx/heart`) rises from its head. It plays `pet.sound` if set, else its `voice`, else
  `sfx/pet.wav`.
- Each critter has a 4 s cooldown; clicks during it do nothing.
- Hit test: the critter's current frame rectangle inflated by 4 px at 1×, topmost by depth first.
  Air critters are easy to click thanks to the inflation.
- A sleeping critter wakes to be petted (cat: `stretch` first). Petting has no other effect.
- Clicking Laeticia instead makes her say a `click` line (8 s cooldown).

**R2.5 Startle.** When the player places, moves or removes an item within `startle.radius` tiles of
a critter that has `startle`: it plays `startle.anim` (if any) for 0.6 s, then travels at 2.5× speed
to a spot 2–3 tiles further from the cause, then Chooses. `only_from` limits it to certain current
animations (the cat only reacts while asleep). Each critter: 5 s cooldown.

**R2.6 Save data:** none. Critters are recomputed on load (as today).

### R3 Rare visitors

**R3.1 Definition.** Rare visitors are ordinary `visitors[]` entries with `"rare": true`, an empty
`needs` object, `max: 1` and a `recipe` condition. Their `time` is `any`; time-of-day lives in the
recipe. `seasons` limits when they come. The eight: owl, heron, hedgehog, fox, frog, koi, robin,
deer (recipes in §5).

**R3.2 Arrival and stays.**

- When the recipe becomes true it must stay true for a random **20–60 s** before the visitor
  arrives (halved by the Orchard nook for the deer). The first arrival is guaranteed.
- After discovery, a visit lasts **180–360 s**, then the visitor goes away for **120–240 s** and comes
  back if the recipe still holds. Before discovery there is no away time.
- It leaves (fade) as soon as the recipe stops holding.
- First arrival: the usual "New visitor" toast with a rarer stinger (`sfx/discover.wav` already
  exists), a page, and Laeticia's `first_<id>` line if she can see it (within 12 tiles).

**R3.3 Behaviour.**

| Visitor | Habitat | What it does | Pet | Startle |
|---|---|---|---|---|
| Owl | air | perches on a stump or pine (`perch` height) for 30–90 s, hoots every 40–90 s; flies between perches; leaves at dawn because the recipe needs night | `hoot` | none |
| Heron | **shore** (new habitat: water next to land, or land next to water) | stands still on the shore 20–40 s, strikes (`fish`) every 8–20 s; prefers a Little harbour | none | 2 tiles, walks off |
| Hedgehog | land | forages beside shrubs 5–12 s, wanders | `curl` | none |
| Fox | land | dozes on a hay bale 40–90 s, wanders | `sleep` | 2 tiles |
| Frog | water | sits on lily pads 10–30 s, croaks every 10–30 s, hops between pads (its move animation) | `croak` | none |
| Koi | water | swims slowly; `underwater: true`: drawn before lily pads and bridges at 60% alpha with a cool tint; surfaces only for the fish-jump delight | ripple and heart | none |
| Robin | land | perches on the bird feeder 5–15 s, follows Laeticia while she waters, wanders | idle | none |
| Deer | land | grazes beside an apple tree 20–40 s, walks slowly | idle | 3 tiles, walks off |

**R3.4 Sketchbook entries.** Before discovery a rare visitor shows a **silhouette** (its `idle_front`
f0 drawn as a solid dark shape by the engine; no extra art) and its vague `hint`. If the player has
its clue (from a wish), the exact `clue` text shows beneath under "Laeticia's note". After discovery:
the sprite, name and `blurb`. The rare section of the Visitors tab appears once four common visitors
have been seen. Common visitors also show their `hint` while undiscovered (today they show "? ? ?").

### R4 Things that change over time

**R4.1 Calendar.**

- The clock keeps its 12-minute cycle. A **new day begins at midnight** (`t = 0.75`, in the middle
  of the night, so changes happen in the dark). `clock.day` counts days from 0.
- Each season lasts **3 days** (36 minutes of play); a year is 12 days. Season index =
  `(day / 3) % 4` (spring, summer, autumn, winter); day within the season = `day % 3 + 1`.
  New worlds start on Spring, day 1, at `t = 0.2`. The calendar is global: one season for the whole map.
- **The calendar only moves while the clock runs on auto.** A pinned clock stops the days. The
  pin's glide never advances the day, even when it crosses midnight.
- **Season pin** (calendar popover, §6.4): "Follow the days" or "Always spring/summer/autumn/winter".
  It overrides the effective season and leaves the day counter alone.
- Absence is invisible: the world reopens exactly where it was.

**R4.2 What changes with the season.**

| | Spring | Summer | Autumn | Winter |
|---|---|---|---|---|
| Colour grade (multiply over the world, before day/night) | 0.98, 1.02, 0.96 | 1.03, 1.00, 0.94 | 1.06, 0.96, 0.86 | 0.90, 0.95, 1.06 |
| Sprite looks (art) | grass with tiny flowers; blossom in bloom (its base art); apple tree in blossom | base art; blossom in leaf | grass browning; oak, blossom and apple tree in autumn colour | grass snow-dusted; oak, blossom and apple bare; pines snow-capped |
| Falling things | petals from blossom trees; leaves at 0.5× | leaves 1× | leaves 3× | none |
| Day ambience | `amb/birds.ogg` | `amb/birds.ogg` | `amb/autumn.ogg` | `amb/winter.ogg` |
| Night ambience | `amb/night_spring.ogg` | `amb/crickets.ogg` | `amb/crickets.ogg` | `amb/night_winter.ogg` |
| Rain toggle (until natural weather arrives with `living-world.md` task W3, which makes it Natural / Rain here / Clear here) | rain | rain | rain | **snow** (`fx/snowflake`, no rain bed, no ripples, winter ambience +3 dB) |
| Visitors | all but fireflies; frog, hedgehog | all; frog, hedgehog | no butterflies; hedgehog, deer | no butterflies, bees, fireflies, hedgehog; robin, deer |
| Beds | grow | grow | grow | paused unless within 2 tiles of a greenhouse |

- The grade is a per-channel multiply applied with the existing world colour modulation, so it
  costs nothing and behaves the same on every renderer. There is no saturation step.
- Sprite looks switch at the midnight that starts a season. The grade glides from the old season's
  values to the new over the following 3 minutes (midnight to the end of dawn). A manual season pin
  swaps sprites at once and glides the grade over 2 s.
- At the first dawn of a season, `sfx/season.wav` plays and Laeticia says the season's `line` as
  she steps out.
- Season data lives in `seasons[]` in the catalog (grade, ambience, falling-thing multipliers,
  `rain_as`, line).

**R4.3 Sprite resolution with seasons and growth.** Extend the atlas scheme (art list §7.1):

- A sprite key may carry a season suffix: `<key>@<season>`, for example `item/oak/base/r0/f1@autumn`
  or `terrain/grass/v2@winter`. Items list the looks the art provides in `season_looks`.
- Growth items insert a stage segment before the frame: `item/planter/base/r2/g1/f0`.
- The engine resolves each sprite once per season change into its sprite tables, trying in order:
  stage + season, stage, season, plain key. Shadows and glows use the same rule, so a missing
  `@winter` shadow simply falls back to the plain shadow. Nothing is looked up per frame.

**R4.4 Veggie beds grow.**

- The planter has `growth: {"stages": 4, "seconds": 180, "harvest": true}`. Stages: `g0` bare soil
  just planted, `g1` sprouts, `g2` leafy, `g3` ripe (the crop of its variant, the current art).
- Each bed stores `stage` and `progress` (0..1). Every simulation step, if `stage < 3`:
  `progress += dt / 180 × multiplier`; at 1 it moves to the next stage with a small pop (the existing
  place pop) and resets. Ripe in 9 minutes of play from planting.
- Multiplier: 1, ×2 while raining (not snow), ×1.25 inside a Kitchen garden, ×0 in winter unless a
  greenhouse is within 2 tiles. Growth uses play time, so a pinned clock still grows beds.
- Laeticia's morning watering adds 0.25 progress, once per bed per day.
- New beds start at `g0`. Undo and redo restore a bed with the growth it had (growth is part of the
  item record that edits store). Ripe beds stay ripe forever.

**R4.5 Harvest.** With no tool, hovering a ripe bed shows "Ripe · click to pick"; clicking it:

- the bed returns to `g0`; `harvests` and `last_harvest_day` update; `sfx/harvest.wav`;
- a produce sprite (`fx/produce`, frame = the bed's crop variant) pops up and flies to Laeticia's
  basket if she is within 12 tiles (she then carries it home: `carry` walk, and the chimney
  smoke thickens for 90 s), otherwise it rises and fades;
- hens within 5 tiles come to peck at the bed; after a harvest, a Lakeside lunch nook gets Laeticia's
  lunch that day.

Harvest is an interaction, not an edit: it is not on the undo stack. What it gives is deliberately
non-economic: it feeds the `first_harvest` wish, Laeticia's cooking and lunch, and the hens.
The first time any bed ripens in a world, the hint line says "Ripe beds can be picked. Click one."

**R4.6 Petals and leaves.** Blossom trees shed `fx/petal` in spring (0.03 per second per tree × the
season's `petal` multiplier); petals that land on water float for 6 s, drifting. Leaves use the
existing `fx/leaf` with the season's `leaf` multiplier, from oaks, apple trees and blossom outside
spring. Pines shed nothing.

**R4.7 Save data:** `clock.day`, `season_pin`; per item `g`; `progress.harvests`, `last_harvest_day`.

### R5 Land you earn

**R5.1 Stages.** The buildable home region (today the 40×40 map) grows outward in five stages (rectangles in §5.6; they tile the map
exactly once). Stage 0, the front 20×20 corner (x and y 20–39), is open from the start. The others
open when the sketchbook's **pages** (visitors seen + nooks found, 30 in all) reach 4, 9, 14 and 20:

```
         (0,0) ┌──────────── x ────────────►
               │══ road ════ ⌂ gate ═════════│  y 0–1: road and wall (stage 4)
               │  4 ░ high wood ░░░░░░░░░░░░│  y 0–7
               │░░┌─────────┬───────────────┤
               │░░│ 3 old   │ 2 far pond    │  y 8–19
           y   │░░│ orchard │               │
           │   │░░├─────────┼───────────────┤
           ▼   │░░│ 1 west  │ 0 the corner  │  y 20–39
               │░░│ meadow  │   (start)     │
               └──┴─────────┴───────────────┘ (39,39)
              x 0–7  8–19      20–39
   Screen: (0,0) is the top vertex, (39,39) the bottom vertex nearest the viewer.
```

Stage 0 is the bottom quarter of the diamond nearest the viewer, so wild land always sits behind
or beside what you build, never in front of it.

**R5.2 Wild land.**

- Wild tiles cannot be built on, painted, or used as a move destination: "This land is still wild".
  Ground critters never enter them; air critters may fly over but never target them.
- Look: the grass base darkened to 70% and cooled (engine), with a `wild/thicket/v<n>` bramble
  sprite on four tiles out of five, variant and skip chosen by a hash of the tile position, so the
  pattern is stable. The cliff rim under wild land is unchanged.
- Hovering a wild tile shows `ui/tile_bad` and a tooltip: "Wild land · opens at 9 pages (3 more)".

**R5.3 Opening.** When the page count reaches a threshold, the next stage opens (several thresholds
at once open one after another, 4 s apart):

- Data first: the tiles become open immediately and the stage's `reveal` terrain and items are
  written in (items only onto free tiles; they always are). Reveals are not on the undo stack.
- Visual: brambles clear in a wave from the boundary with open land outwards, each tile 0.08 s × its
  distance after the first, with `fx/clear` and a short fade (3 s for a typical stage).
  `sfx/land_open.wav`. Reveal items pop in as the wave passes. Reduce motion: a 1 s fade instead.
- A toast: "New land: The west meadow". If the stage is off screen, an edge chip "New land" with an
  arrow appears for 8 s; clicking it pans the camera there. The camera never moves on its own.
- Laeticia walks to the new edge and says the stage's `line`.
- Free-build worlds open every stage at creation, with reveals.

**R5.4 What each stage hides.** The west meadow has a stream that falls off the south-west rim
(a waterfall), lavender and a stump. The far pond has a pond with a rowing boat and a creek to the
south-east rim (another waterfall). The old orchard has four apple trees in a broken grid, a broken
stone wall and a hay bale (the `orchard_mended` wish asks you to fill the gaps). The high wood is a
pine forest around a spring pool whose brook falls off the south-west rim, and at its far edge the
road, the wall and the gate (R5.6).

**R5.5 Save data:** `home.stage` (home region). Wild tiles are derived from the stage, never saved.

**R5.6 The edge of the corner.** The last stage ends at a natural boundary rather than a wall of
brambles. Along the far north-east rim (y = 0) runs an old **road**; inside it a dry-stone wall
(y = 1) closes the home region, broken by one **gate**, a rose arch at (20, 1) with a lamp beside
it, and a path leads from the gate down through the wood (x = 20, y 2–7) towards the far pond.
All of it is revealed by stage 4 from existing pieces (stone wall, rose arch, lamp, path), and
Laeticia's line for that stage is "A whole wood. And a road. Where does that go?" Reaching the
edge should feel like the start of something: the road is visibly going somewhere.

The gate is not interactive in this batch. Hovering it shows the tooltip "The road out" (a new
string), nothing more.

**R5.7 Present state, and what changes when the world exists.**

| Now (this batch) | When the surrounding world exists |
|---|---|
| The home region is the whole 40×40 map, drawn as a floating island with cliff faces under the south-east and south-west rims and sky all round | The island rim, cliffs and sky around the home region go away; the neighbouring world terrain is drawn right up to the region's edge and the camera can scroll beyond it |
| The road along y = 0 runs to the rim at both ends and stops in the sky | The road continues out of the region in both directions; the gate becomes the home region's door to the world and its first fast-travel point |
| Water reaching the south rims falls off as waterfalls (§5.8, #1) | Those streams flow on into the world instead; the waterfall delight applies only where the world itself has a drop |
| Wild stages are brambles inside the region | Unchanged: wild stages stay inside the home region. Land outside the region is never buildable and is drawn as the world, never as brambles |
| The two south rims are the edge of everything | They meet the world: the design for the cities decides what lies there (a shore on the south-west, farmland on the south-east are the obvious fits for the streams and the stage-0 path) |

### R6 Laeticia

> **Built on the shared actor system** (`living-world.md` §2.6, task W2). Her routine in R6.2 is
> data in the catalog's `resident.schedule`, `routines` and `interrupts`, written in game hours
> (`hour = (6 + 24 × t) mod 24`: dawn 03:00–06:00, day 06:00–18:00, dusk 18:00–21:00, night
> 21:00–03:00). This section stays the authority for what the data does not express: movement
> costs, interrupts' priorities, home choice, bubbles.

**R6.1 Who she is.** Laeticia spent forty years as a botanical illustrator, drawing other people's
gardens for books she never kept, and in her late sixties has finally got a scrap of land of her own.
She is practical and dry, talks to plants without embarrassment, and notices small things: the
way a hen tilts its head, the first frost on a bench. The sketchbook is hers; every page in it is a
drawing she made.

Look (for art): tall and a little stooped, grey hair in a loose bun, round glasses, moss-green
cardigan over a cream blouse, a long rust skirt and an apron with deep pockets, sturdy boots. She
carries a satchel with the sketchbook.

**R6.2 Daily routine.** Her schedule is a function of the clock (`t`), evaluated whenever she
finishes an activity:

| Clock | Block | What she does |
|---|---|---|
| 0.875–0.94 (dawn) | Wake | Steps out of the home cottage door (or gets up from the bedroll): `stretch` 2 s, `morning` line (or the season line at the first dawn of a season) |
| 0.94–0.20 | Chores | Waters each veggie bed, nearest first, at most 6 (`water`, 3 s each, +0.25 growth; skipped in rain or snow, and in winter for beds no greenhouse covers). Then, if there is a coop and hens are present, scatters feed beside it (`scatter`, 4 s; the hens gather) |
| 0.20–0.35 | Leisure | Weighted choice: sit on a bench (sit 20–40 s, then 50% `read` 20–40 s); lie in the hammock and read (30–60 s) if there is one; lunch at a Lakeside lunch picnic table if she harvested today. A Reading nook makes its bench 4× as likely |
| 0.35–0.50 | Stroll | Walks to 3–5 points of interest: nooks, items placed in the last 10 minutes (3× weight), visitors. At each: `admire` (idle 2 s, maybe a line) or `sketch` sitting on the ground facing a visitor or nook (15–25 s) |
| 0.50–0.625 (dusk) | Evening | Sits by a campfire (`warm`, 20–40 s) or else on a bench near a lamp; `dusk` line |
| 0.625–0.875 (night) | Home | Walks to the home cottage door and goes in (hidden; the windows already glow). Without a cottage: lies down on her bedroll (`sleep`) beside the campfire if there is one, else at the bedroll spot. Nook routines: Moon garden (once a night, a 30 s stroll to it and back) |

Nook routines: Wishing well (when a stroll passes within 3 tiles of the well: `toss`, `sfx/well.wav`);
Lakeside lunch (above); Woodland walk (the stroll prefers its path); Village square (sketch there).

**R6.3 Interrupts** (highest first):

- **Shelter.** Rain or snow starts: after 5 s she walks home (or to the nearest tree without a
  cottage) and waits; `rain_start` or `snow_start`. When it stops: `rain_stop`, resume.
- **Displaced.** Something is placed on her tile or her seat is removed or moved: she steps to the
  nearest walkable tile within 3 (0.5 s). If there is none, she fades out and reappears at her home
  door (the only time she teleports).
- **React.** A placement within 8 tiles while she is idle, walking or sitting (not reading): always
  for the first ever placement of an item id in this corner, otherwise 30%, at most once every 20 s.
  She turns to it, idles 2 s and says a `place_<tag>` line (the item's first tag; `place_water` for
  painted water; `place_other` without a tag).
- **Clicked.** Turns to the camera, `click` line, 8 s cooldown.
- **Ambient talk.** With chatter on Chatty: an `idle` line every 60–120 s while she is visible and
  not reading. Quiet: only wishes, thanks, first sightings and season lines.

**R6.4 Home and the bedroll.** Her home is the first cottage in the item list. If it is removed she
picks the next cottage; with none she says a `home_lost` line and goes back to the bedroll. Before
any cottage exists she sleeps on the bedroll (`sleep` shows her lying on it; the bedroll is part
of that sprite, not an item) at `starter.resident` in a new world, or beside the campfire, or at
the open tile nearest the centre of stage 0. Line at bedtime: `no_cottage_night`.

**R6.5 Movement.** A* on the tile grid, 8 directions without corner cutting, recomputed on demand
(at most once per 0.25 s) and when the world revision changes along her route. Cost per tile: path,
cobble, bridge and stepping stones 1.0; everything else 1.6; blocked: non-walkable items, water
without a crossing, wild land. Speed 1.1 tiles/s on path and cobble, 0.9 elsewhere. Unreachable
targets are dropped. She goes in and out through the tile in front of the cottage door (the tile
adjacent to the footprint on the door side for its rotation: `r0` +x, `r1` +y, `r2` −x, `r3` −y).

**R6.6 Speech bubbles.** A glass bubble above her head at native resolution, one at a time, at most
two lines; visible for 2.5 s + 0.05 s per character, fading in and out over 0.2 s. A line is never
repeated until every other line of that context has been used. Each bubble plays one of three soft
wordless murmurs (`sfx/laeticia_1..3.wav`). She is silent during photo mode. Bubbles follow her
when the camera moves; off-screen bubbles are dropped.

**R6.7 Clock pinned.** With the clock pinned, her schedule runs on a private clock that loops the
blocks of the pinned phase (day: chores, leisure, stroll, repeat; dusk: evening; night: home, with
the moon-garden stroll every 6 minutes if that nook exists; dawn: wake, then chores).

**R6.8 Save data:** none. On load she appears in the state her schedule implies (inside at night,
otherwise at her home door or bedroll), and waves with a `greet` line if she is visible.

### R7 Named nooks

**R7.1 Data.** `nooks[]`: `id`, `name`, `condition` (must contain exactly one `near`, at the top level
or directly inside a top-level `all`; that `near`'s anchors are the nook's instances), `teaser`
(shown in the sketchbook before discovery), `blurb` (after), `gift` (a sentence saying what it does)
and `effects`. Sixteen nooks are listed in §5.

**R7.2 Discovery.** The first time any instance of a nook exists in a world (nooks can only be built in
the home region; the discovered list is global):

- The instance's area tiles pulse with `ui/tile_area` (alpha 0 → 0.5 → 0 over 1.6 s); eight
  `fx/sparkle` bursts around it; a glass label with the nook's name floats above the anchor for
  3.5 s; `sfx/nook.wav`.
- Toast: "New nook: Reading nook · 13 of 30 pages". The `nooks` and `pages` counters go up.
- Laeticia, if idle within 15 tiles, walks over and says a `nook_found` line.
- Reduce motion: no pulse, just the label and sound.
- Further instances, or the same nook re-forming after being broken, are silent.

**R7.3 Instances and hover.** With no tool, hovering a nook's anchor item shows its name in the
tooltip and outlines its area with `ui/tile_area`. Holding Tab shows every instance (R11.6).

**R7.4 Effects** (while at least one instance exists):

| Effect | JSON | Meaning |
|---|---|---|
| prefer | `{"prefer": {"who": "duck", "activity": "sleep_bank"}}` | when `who` chooses that activity, targets inside a nook area weigh 4× (for `wander`, wander targets are drawn from the area half the time) |
| cap | `{"cap": {"visitor": "firefly", "add": 4}}` | raises that visitor's `max` |
| growth | `{"growth": 1.25}` | beds inside the area grow faster |
| fx | `{"fx": {"name": "apple", "seasons": ["autumn"]}}` or `{"fx": {"name": "leaf", "mul": 2}}` | ambient falling things inside the area (apples: one per tree per 40 s, they lie for 20 s, then fade) |
| routine | `{"routine": "lunch" \| "moon_stroll" \| "pebble"}` | adds that block to Laeticia's day (R6.2) |
| rare_rate | `{"rare_rate": {"visitor": "deer", "mul": 2}}` | divides that rare visitor's arrival delay |

`who` is a visitor id or `laeticia`; Laeticia's activity ids are `water`, `feed`, `sit`, `read`,
`lie`, `lunch`, `sketch`, `warm`, `stroll`, `admire`.

**R7.5 Save data:** `progress.nooks` (discovered ids, global). Instances are recomputed (home region).

### R8 Music that grows with the corner

**R8.1 Stems.** Each piece (day: D major/lydian; night: B dorian; both 72 bpm, 4/4, 32 bars) is
split into five stems rendered from the same session, so they sum to the full mix:

| Stem id | Day | Night | Plays when |
|---|---|---|---|
| `pad` | warm pad | darker pad | always |
| `keys` | felt piano chords | felt piano chords | always |
| `melody` | music box melody | the night lead | after the first wish is granted (`progress.wishes ≥ 1`) |
| `bass` | bass | bass | once 5 visitor kinds have been seen |
| `colour` | new: soft wooden flute counter-line and a brushed shaker | new: bowed cello harmonics and a low clarinet line | once 4 nooks have been found |

The conditions are in `audio.stems[].when` (condition vocabulary). The full mixes
`music/day.ogg` and `music/night.ogg` stay and play on the title screen.

**R8.2 Playback.**

- All stems are exactly 32 bars = **106.667 s = 4,704,000 samples** at 44.1 kHz and share one master
  sample position. Stems are streamed (one stb_vorbis decoder per playing stem); only unlocked stems
  of the audible pieces are decoded. During the day/night crossfade both pieces' unlocked stems play.
- A newly unlocked stem seeks to the master position and fades in from silence over 4 bars
  (13.33 s), starting on the next bar line (every 3.333 s). On load, unlocked stems start at full level.
- Day/night crossfade is unchanged (driven by `lighting.night`). The pause menu ducks music by 6 dB.
- With music volume at 0 or muted, nothing is decoded.

**R8.3 Tuned placement notes.** Ten notes, one shared set for both pieces, because D major
pentatonic and B minor pentatonic are the same pitches: D4 E4 F♯4 A4 B4 D5 E5 F♯5 A5 B5
(`sfx/note_0` … `sfx/note_9`). Each placement plays its material sound (as now, with pitch jitter)
plus one note at `kNoteLevel`. The note is chosen by a phrase walker:

```
state: idx, dir (+1/−1), len, phraseLen, lastTime
on placement at time now:
  if no previous note or now − lastTime > 2.0 s:
      idx = random of {0, 2, 3}        # D4, F♯4 or A4
      dir = +1; len = 0; phraseLen = random 4..6
  else if len ≥ phraseLen:             # cadence: land on a D or an A
      idx = nearest of {0, 3, 5, 8} to idx in direction dir (or nearest if none that way)
      len = 0; phraseLen = random 4..6
  else:
      if random < 0.2: dir = −dir
      idx += dir × (random of {1, 1, 1, 2})
      if idx < 0 or idx > 9: dir = −dir; reflect idx back into 0..9
  play note idx; len += 1; lastTime = now
```

- Drag placement: one note per piece, but notes closer than 90 ms are skipped.
- Line placement (R11.4): the whole line plays as a rising arpeggio, one walker step up every 45 ms,
  at most 8 notes.
- Painting: one note at the start of a stroke and one every 6 tiles. Rectangle paint: one note.
- Removing, rotating, undo and redo play their existing sounds and no note.
- The walker uses the game's seeded RNG, so scripted runs are reproducible.

### R9 Small moments of delight

> **Built on the shared event scheduler** (`living-world.md` §5, events H1–H15, task W3). The
> waterfall, lamp moths and the cat watching the cursor are states, not events, and stay as written.

The full list with triggers, rarity and assets is in §5.8. Rules shared by all of them:

- They never block input, never move the camera and never interrupt a speech bubble.
- Each has a cooldown so it stays special; random ones use the game's seeded RNG.
- Reduce motion turns off the ones marked so in the table and thins particles to 30%.

### R10 A proper front door

**R10.1 Flow.**

```
launch ─► title ─┬─ Continue ─────────────► world (last played)
                 ├─ Worlds ──► worlds ───┬─ Play ──► world
                 │                       ├─ New ───► name dialog ─► world (tour if first time)
                 │                       ├─ Rename (inline)
                 │                       └─ Delete ─► confirm
                 ├─ Settings ─► settings ─► back
                 └─ Quit
first launch (no saves): title shows Begin ─► name dialog ─► world + tour
in a world: Esc (nothing to cancel) or ☰ ─► pause ─┬─ Resume
                                                   ├─ Settings
                                                   ├─ Open postcards folder
                                                   ├─ Back to worlds (save + thumbnail first)
                                                   └─ Quit (save + thumbnail first)
```

Closing the window behaves like Quit. There are no "are you sure" prompts except Delete, because
nothing can be lost.

Each save file is a **whole world**: its home region and all its progress. Several saves are several
independent worlds; nothing is shared between them except the profile.

**R10.2 Title screen.** The home region of the last played world renders behind a glass panel, the
clock at its saved time, the camera drifting 4 px/s across it; water and critters animate, no
simulation runs. With no saves, it shows the starter scene at dawn. Music: the full day mix (or
night mix if that world's clock is at night). The logo is the `title/logo` sprite.

**R10.3 Worlds screen.** A grid of cards, one per world save, newest played first, plus a dashed
**New world** card.
Each card: thumbnail, name, "Autumn, day 3 · 14 pages", and on hover or selection, Play, Rename
and Delete. Rename edits the name in place (Enter confirms, Esc cancels, 1–28 characters after
trimming, no two worlds with the same name: "You already have a world with that name").
Delete asks: "Delete “Plum Hollow”?" / "The whole world goes, corner and all. Its postcards stay where
they are. This can't be undone." [Keep it] [Delete]. Delete removes the world's folder. A save that
fails to load shows "This world couldn't be opened" with a Back button; its file is left untouched
and the error logged.

**R10.4 New world dialog.** Name field (the world is named after its home corner) (default "Laeticia's Corner", then "Laeticia's Corner 2"…),
a **Free build** toggle ("Everything unlocked and all land open from the start. Wishes still come,
just for the company."), [Cancel] [Create]. Creates the world save, builds the home region from `starter` and opens it.
Text entry uses SDL text input while the field is focused.

**R10.5 First-minute tour.** Runs when a world opens and the profile is not `onboarded`. A small
coach card sits above the bottom dock with the step text and a "Skip tour" link. Steps advance by
doing; only step 1 times out.

| Step | Coach text | Highlight | Done when |
|---|---|---|---|
| 1 | Drag to look around. | none | any pan or zoom, or 6 s |
| 2 | Open Build to plant something. | Build button pulses | drawer opens |
| 3 | Pick the daisies, then click the ground. | daisies tile pulses | any item placed |
| 4 | Laeticia has a wish. Granting it unlocks new pieces. | wish tray | `first_flowers` granted (it is offered at the start of this step; skipped if already done) |
| 5 | Ctrl+Z undoes anything. J opens the sketchbook. | undo button, sketchbook button | 5 s |
| 6 | That's all. Make yourself at home. | none | 4 s |

Laeticia says the `tour` line at step 1. Visitor toasts are held during steps 1–3 and shown after.
Skipping or finishing sets `onboarded`. Settings has "Replay the tour".

**R10.6 Pause.** Stops the simulation (clock, critters, growth, Laeticia, wish pacing); the world
blurs behind the glass; music ducks 6 dB; ambience continues.

**R10.7 Settings** (from title and pause; changes apply at once and save to the profile):
Music, Effects, Ambience volume (0–100 in steps of 5, slider plus arrow keys), Mute all (M),
Fullscreen (F11), Interface size (Auto, 75%, 100%, 125%, 150%, 200%; multiplies the DPI scale),
Reduce motion, Show grid (G), Laeticia's chatter (Chatty or Quiet), Replay the tour.

**R10.8 Reduce motion** does: camera snaps instead of easing; panels fade instead of sliding;
particles (leaves, petals, snow, rain) at 30%; no nook pulse ring; land opens with a 1 s fade; no
shooting-star streaks; no gust wave; no lamp moths. Critters and Laeticia still animate.

**R10.9 Thumbnails.** On leaving a world, on quit and every 5 minutes of play, render the world
pass (no UI, no bubbles) into an offscreen 384×240 target framed on the opened home region, and write
`thumb.png` atomically.

### R11 Builder comforts

**R11.1 Tools.** None (pointer: pet, harvest, click the well), Place, Paint, Remove, **Move**. The
eyedropper is a one-shot action, not a tool.

**R11.2 Move (V).** Click an item to pick it up; it becomes the ghost (keeping its variant) and its
tiles look empty. Click to put it down (same validity rules as placing; R rotates or cycles the
variant). Esc or right-click puts it back where it was. A successful move is one undo step (remove
and add in one group); cancelling leaves no undo step (the editor gains `abort()`, which reverts the
open group). Locked items can be moved. Critters and Laeticia using the item are displaced (R2.1, R6.3).
Picking up plays `sfx/pick.wav`. Hint: "Click something to pick it up · Esc to cancel", while carrying: "Click to put it down · R to
rotate · Esc to put it back".

**R11.3 Eyedropper.** Middle-click or Alt+click on the map, with any tool: on an item, switch to
Place with that item and variant; on bare ground, switch to Paint with that terrain. `I` arms a
one-shot pick for trackpads (pipette cursor, next click picks, Esc cancels). Locked: warning "Not
unlocked yet" and nothing changes. Never touches the undo stack.

**R11.4 Line placement.** With Place and a 1×1 item, Shift+drag places a straight line along x or
along y (whichever the drag covers more), previewing every ghost; invalid tiles show red and are
skipped. Release places all valid ones as one undo step. Ideal for fences, hedges and walls.
Without Shift, drag placement works as today.

**R11.5 Brush and rectangles.**

- Paint brush sizes 1, 3, 5 (a square of tiles centred on the pointer). `[` and `]` step down and
  up; the hint line shows "Brush 3×3". Blocked tiles inside the brush are skipped, not refused. A
  stroke is one undo step.
- Paint + Shift+drag fills a rectangle of tiles (preview with `ui/tile_ok`). One undo step.
- Remove + Shift+drag removes every item whose footprint touches the rectangle (preview: their
  footprints tinted with `ui/tile_bad`). One undo step.

**R11.6 Grid and footprints.**

- **G** toggles a faint diamond grid (`ui/tile_grid`) over opened tiles, above terrain, below items
  (alpha 0.14 by day, 0.10 at night). Saved in the profile.
- **Hold Tab** to show every item's footprint (`ui/tile_area`, low alpha) and every nook instance's
  area outline with its name in a small glass pill. Release hides it. Clicks keep working.

**R11.7 Shortcuts** (complete list; new ones in bold):

| Key | Action |
|---|---|
| B / X / **V** | Build drawer / Remove / **Move** |
| **I**, **middle-click**, **Alt+click** | **Eyedropper** |
| R | Rotate or next look (Place, Move) |
| **[ / ]** | **Brush size** (Paint) |
| **Shift+drag** | **Line** (Place, 1×1) / **rectangle** (Paint, Remove) |
| **G** / **hold Tab** | **Grid** / **footprints and nooks** |
| Ctrl+Z / Ctrl+Shift+Z, Ctrl+Y | Undo / redo |
| WASD, arrows / wheel, + − / Home | Pan / zoom / recentre |
| C / N / J / P | Clock / rain or snow / sketchbook / photo mode |
| M / F11 | Mute / fullscreen |
| Esc | Cancel the tool, else close the open panel, else pause |
| Photo mode: Space or Enter / **F** / **T** / **H** / P or Esc | Take postcard / **next frame** / **caption** / **hide bar** / leave |

### R12 Postcards

**R12.1 Photo mode (P)** hides the interface as today, and shows a slim glass **photo bar** at the
bottom that fades out after 2 s without pointer movement and returns when the pointer moves. The
camera can still pan and zoom. Laeticia's bubbles are hidden.

**R12.2 Frames.** `frames[]`: Plain (start), Pressed flowers, Watercolour, Starry night (from wishes).
Plain is a 2-pixel cream border drawn by the engine. The others are nine-slice pixel-art frames
(`frame/<id>/tl … br`, edges tiled) drawn at the world's integer zoom, so they match the art.
F or the bar's arrows cycle unlocked frames; the choice is remembered in the profile.

**R12.3 Caption.** On by default (T toggles): the world's name (its home corner's name), then "Spring, day 2 · 17 November 2026"
(in-game date, then the real date in English), set in the UI font at the bottom left, on the
frame's `plate` sprite (or on a soft dark band for Plain). Month names live in `strings.hpp`.

**R12.4 Taking one.** Space or Enter (or the bar's button) hides the bar for one frame, renders the
frame and caption over the view at window resolution, saves a PNG, plays `sfx/shutter.wav` with the
existing flash, and toasts "Postcard saved". Files go to:

1. `<save dir>/postcards/<slug>/` when `--save-dir` or `$LAETICIA_SAVE_DIR` is set (always the case in
   tests);
2. otherwise `<Pictures>/Laeticia's Corner/<slug>/` (`SDL_GetUserFolder(SDL_FOLDER_PICTURES)`);
3. falling back to `<pref path>/postcards/<slug>/`.

File name: `<slug>-YYYYMMDD-HHMMSS.png`, adding `-2`, `-3` on collision. "Open folder" (bar and
pause menu) calls `SDL_OpenURL` with the folder's `file://` URL. Failures toast "Couldn't save the
postcard". Postcard taking never changes the world save.

---

## 5 Content tables

Generated from the same data as `catalog.next.json`. `[tag]` means any item with that tag; "within N" is the Chebyshev area of §3.1.

### 5.1 Wishes (all 36, in priority order)

Priority is the order below (see R1.4). `after` lists wishes that must be granted first; `requires` is an extra offer gate.

| # | id | Giver | After / requires | Wish text | Goal | Reward | Thanks |
|---|---|---|---|---|---|---|---|
| 1 | `first_flowers` | Laeticia | — | It's a bit bare, isn't it? A few more flowers would help. Four patches, say. | 4 [flower] in total | Lavender, Berry bush | There. Now it smells like somewhere. |
| 2 | `a_roof` | Laeticia | first_flowers | I've slept under the stars two nights running. A cottage would be lovely. | 1 Cottage in total | Veggie bed, Lamp post | A door that closes. A kettle. I'm home. |
| 3 | `path_to_door` | Laeticia | a_roof | A path up to the door, so I stop tracking mud inside. | Cottage with 3 Path or Cobble tiles within 1 | Cobble, Pine | Much better. My boots thank you. |
| 4 | `cat_bench` | The cat | a_roof; seen cat | The cat keeps sitting right where a bench would go, just by the cottage. | Cottage with 1 Bench within 2 | Blossom tree, Mushrooms | The cat has claimed it. Of course. |
| 5 | `three_beds` | Laeticia | a_roof | Three veggie beds, and we'll always have something to cook. | 3 Veggie bed in total | Hen coop, Scarecrow | Little rows. I do love little rows. |
| 6 | `first_harvest` | Laeticia | three_beds | When something in the beds is ripe, pick it and I'll make soup. | harvests ≥ 1 | Well | Soup tonight. I'll leave the pot on. |
| 7 | `reading_light` | Laeticia | a_roof | I'd like to read outside after dark. A lamp beside a bench? | dusk/night AND Bench with 1 [light] within 2 | Campfire, Stump | Just enough light for one more chapter. |
| 8 | `hen_fence` | Hens | three_beds; seen hen | The hens wander off at every chance. A bit of fence round the coop? | Hen coop with 4 [line] within 2 | Hedge, Tool shed | They're pretending they don't mind. |
| 9 | `duck_hideout` | Ducks | —; seen duck | The ducks would like somewhere to hide. Some tall grass along the water? | 3× Tall grass with 1 Water tiles within 1 | Reeds, Lily pads | Three heads, then none. Then three again. |
| 10 | `slow_lavender` | Butterflies | first_flowers; seen butterfly | The butterflies slow right down over the lavender. Three patches of it? | 3 Lavender in total | Beehive | The bees will hear about this. |
| 11 | `bee_meadow` | Bees | slow_lavender; seen bee | The bees fly a long way for flowers. Six near the hive would help. | Beehive with 6 [flower] within 3 | Sunflowers | The hum's gone warm and lazy. |
| 12 | `bigger_pond` | Laeticia | duck_hideout | A bigger pond, so the ducks have room to argue. | 16 Water tiles in total | Footbridge, Stepping stones | They're arguing already. Perfect. |
| 13 | `dry_feet` | Laeticia | bigger_pond | I'd love to get across the water without wading. | 1 [crossing] in total | Rowing boat | Dry feet. Small miracles. |
| 14 | `cat_fireside` | The cat | reading_light; seen cat | The cat has found the warm side of the campfire. Somewhere to sit beside it? | night AND Campfire with 1 [seat] within 2 | Log pile | Two of us by the fire now. Three, counting the cat. |
| 15 | `little_wood` | Laeticia | path_to_door, cat_bench | More trees, of different kinds. A little wood to walk in. | 10 [tree] in total AND 3 kinds of [tree] | Apple tree | Listen to that. Leaves. |
| 16 | `shady_bench` | Laeticia | little_wood | A bench under the trees, for listening to the birds. | Bench with 3 [tree] within 2 | Bird feeder | Shade and birdsong. That's my afternoon gone. |
| 17 | `two_trees` | Laeticia | shady_bench | Two apple trees side by side would suit something I have in mind. | Apple tree with 1 Apple tree within 1 | Hammock | Now. About that something. |
| 18 | `hens_watch` | Hens | hen_fence; seen hen | The hens watch the veggie beds like it's the theatre. Beds nearer the coop? | Hen coop with 2 Veggie bed within 3 | Hay bale | Front-row seats, and they know it. |
| 19 | `garden_hedge` | Laeticia | hen_fence | A hedge would keep the wind off the garden. Eight lengths, say. | 8 Hedge in total | Rose arch | Shelter. You can hear the difference. |
| 20 | `garden_gate` | Laeticia | garden_hedge | An arch set into the hedge, like a proper garden gate. | Rose arch with 2 [line] within 1 | frame: Pressed flowers | I've walked through it four times. Just because. |
| 21 | `lunch_view` | Laeticia | bigger_pond | I'd like to eat lunch looking at the water. A bench by the pond? | Bench with 3 Water tiles within 2 | Picnic table | Bread, cheese and ducks. Lovely. |
| 22 | `trowel` | Laeticia | hen_fence | My trowel keeps going missing. A shed near the beds? | Tool shed with 1 Veggie bed within 3 | Greenhouse | Found it. It was in my pocket all along. |
| 23 | `winter_greens` | Laeticia | trowel | With a greenhouse beside the beds, we could grow things through the winter. | Greenhouse with 2 Veggie bed within 2 | clue: robin | Speaking of winter, a robin comes to feeders by hedges. |
| 24 | `hay_stack` | Laeticia | hens_watch | Stack a few hay bales and I'll start dreaming about a barn. | 3 Hay bale in total | Barn | It smells like August in there. |
| 25 | `nearly_a_farm` | Laeticia | hay_stack | A barn and six beds. A windmill would make it a farm. | 1 Barn in total AND 6 Veggie bed in total | Windmill | Look at it turn. I could watch it all day. |
| 26 | `duck_lilies` | Ducks | duck_hideout; seen duck | The ducks keep nosing at the lily pads. A few more would please them no end. | 4 Lily pads in total | frame: Watercolour | Paddling in circles. Pure bliss. |
| 27 | `dark_meadow` | Fireflies | —; seen firefly | The fireflies glow brightest far from the lamps. A dark patch of long grass? | night AND Tall grass with 4 Tall grass, no [light] within 3 | frame: Starry night | Like the sky came down for a look. |
| 28 | `market_square` | Laeticia | path_to_door; stage ≥ 1 | A little square of cobbles, for sitting out. We've no market, but still. | 12 Cobble tiles in total | Fountain | There. Now it's a square. |
| 29 | `orchard_mended` | Laeticia | little_wood; stage ≥ 3 | Someone planted an orchard here long ago. Shall we fill the gaps? | 6 Apple tree in total | Stone wall | I found their old wall stones. We can mend it now. |
| 30 | `hen_dusk` | Hens | hens_watch; seen hen | The hens fuss at dusk, as if something's watching. A light by the coop? | dusk AND Hen coop with 1 [light] within 2 | clue: fox | Calmer now. Whatever it was, it's only curious. |
| 31 | `cat_pines` | The cat | cat_fireside; seen cat | At night the cat stares into the pines. Something lives there. Or could. | Pine with 3 Pine within 2 | clue: owl | Whatever it's waiting for, it seems very sure. |
| 32 | `duck_reeds` | Ducks | bigger_pond; seen duck | The ducks keep to the far side lately, watching the reeds. More reeds? | 6 Reeds in total | clue: heron | Something tall stood there at dawn. I'm sure of it. |
| 33 | `firefly_pond` | Fireflies | dark_meadow, duck_hideout; seen firefly | The fireflies love the pond at night. Reeds and lily pads, close together? | 2× Lily pads with 1 Reeds within 1 | clue: frog | Someone small went 'plop' just now. |
| 34 | `snuffling` | Laeticia | cat_fireside | I heard snuffling under the bushes last night. A log pile near them, perhaps? | Log pile with 2 [shrub] within 2 | clue: hedgehog | If it comes back, it has somewhere to sleep. |
| 35 | `apples_turning` | Laeticia | little_wood; autumn | The apples are turning. Plant a few more, and see who comes for them. | 3 Apple tree in total | clue: deer | Leave some on the ground. Just in case. |
| 36 | `deep_water` | Laeticia | dry_feet | A big pond with a bridge to lean on. I like watching water from a bridge. | 24 Water tiles in total AND Footbridge with 2 Lily pads within 2 | clue: koi | Was that orange? Something orange, down deep. |

### 5.2 Unlock tree

Start palette: Ground — Grass, Meadow, Path, Water. Items — Oak, Bush, Poppies, Daisies, Tall grass, Rock, Bench, Fence, Cottage. Frame — Plain.

```
first_flowers [Laeticia] → Lavender, Berry bush
  a_roof [Laeticia] → Veggie bed, Lamp post
    path_to_door [Laeticia] → Cobble, Pine
      little_wood [Laeticia] → Apple tree (+after cat_bench)
        shady_bench [Laeticia] → Bird feeder
          two_trees [Laeticia] → Hammock
        orchard_mended [Laeticia] → Stone wall
        apples_turning [Laeticia] → clue: deer
      market_square [Laeticia] → Fountain
    cat_bench [The cat] → Blossom tree, Mushrooms
    three_beds [Laeticia] → Hen coop, Scarecrow
      first_harvest [Laeticia] → Well
      hen_fence [Hens] → Hedge, Tool shed
        hens_watch [Hens] → Hay bale
          hay_stack [Laeticia] → Barn
            nearly_a_farm [Laeticia] → Windmill
          hen_dusk [Hens] → clue: fox
        garden_hedge [Laeticia] → Rose arch
          garden_gate [Laeticia] → frame: Pressed flowers
        trowel [Laeticia] → Greenhouse
          winter_greens [Laeticia] → clue: robin
    reading_light [Laeticia] → Campfire, Stump
      cat_fireside [The cat] → Log pile
        cat_pines [The cat] → clue: owl
        snuffling [Laeticia] → clue: hedgehog
  slow_lavender [Butterflies] → Beehive
    bee_meadow [Bees] → Sunflowers
duck_hideout [Ducks] → Reeds, Lily pads
  bigger_pond [Laeticia] → Footbridge, Stepping stones
    dry_feet [Laeticia] → Rowing boat
      deep_water [Laeticia] → clue: koi
    lunch_view [Laeticia] → Picnic table
    duck_reeds [Ducks] → clue: heron
  duck_lilies [Ducks] → frame: Watercolour
dark_meadow [Fireflies] → frame: Starry night
  firefly_pond [Fireflies] → clue: frog (+after duck_hideout)
```

Reachability (checked by the build script, and to be re-checked by an engine unit test): every item, terrain, frame and clue is granted by exactly one reachable wish; no wish's goal references a piece that is still locked when it becomes offerable.

### 5.3 Visitors: seasons, hints and recipes

| id | Name | Rare | Habitat | Seasons | Appears when | Hint (before) | Clue (after the hint wish) | Blurb (after discovery) |
|---|---|---|---|---|---|---|---|---|
| `duck` | Ducks |  | water | spring, summer, autumn, winter | 6 Water tiles | They look for open water. A good-sized pond will do. | — | They found the pond all by themselves. |
| `hen` | Hens |  | land | spring, summer, autumn, winter | 1 Hen coop; day only | They need somewhere to roost. | — | Busy, opinionated, and very fond of the coop. |
| `cat` | The cat |  | land | spring, summer, autumn, winter | 1 Cottage | Cats choose houses, not people. | — | Moved in the moment the cottage had a roof. |
| `butterfly` | Butterflies |  | air | spring, summer | 4 of Poppies/Daisies/Lavender; day only | Flowers, and plenty of them. | — | Four flower patches is all it takes. |
| `bee` | Bees |  | air | spring, summer, autumn | 1 Beehive; day only | They'll need a hive to come home to. | — | Humming between the hive and the blooms. |
| `firefly` | Fireflies |  | air | summer, autumn | 3 of Tall grass/Reeds; night only | Long grass on summer nights. | — | They only come out when the lamps do. |
| `owl` | The owl | yes | air | spring, summer, autumn, winter | night AND Stump with 3 Pine within 2 | Watches from the pines at night. | At night: a stump with three pines within two tiles. | Sits on the stump like it was carved there. Blinks about once an hour. |
| `heron` | The heron | yes | shore | spring, summer, autumn, winter | dawn/day AND 20 Water tiles in total AND 4× Reeds with 2 Water tiles within 1 | Fishes where the reeds grow thick. | At dawn or by day: a pond of twenty tiles and four reeds, each touching two water tiles. | Patience on two very long legs. |
| `hedgehog` | The hedgehog | yes | land | spring, summer, autumn | dusk/night AND Log pile with 2 [shrub], 1 Veggie bed within 2 | Snuffles about after dark, near shelter and something to eat. | At dusk or night, outside winter: a log pile with two shrubs and a veggie bed within two tiles. | Eats the slugs, ignores the lettuce. The perfect guest. |
| `fox` | The fox | yes | land | spring, summer, autumn, winter | dusk/dawn AND Hay bale with 3 Tall grass within 3 AND 8 [tree] in total | Likes somewhere warm and strawy at the edges of the day. | At dusk or dawn: a hay bale with three tall grass within three tiles, and eight trees. | Curls up on the hay and pretends not to see the hens. |
| `frog` | The frog | yes | water | spring, summer | 2× Lily pads with 1 Reeds, 1 Lily pads within 1 | Sings where lily pads and reeds meet. | In spring or summer: two lily pads, each with a reed and another lily pad beside it. | Sings for an hour after rain. Nobody asked it to. |
| `koi` | The koi | yes | water | spring, summer, autumn, winter | day AND 24 Water tiles in total AND Footbridge with 2 Lily pads within 2 | Something bright moves under a bridge. | By day: a pond of twenty-four tiles and a footbridge with two lily pads within two tiles. | Older than the corner, probably. It isn't telling. |
| `robin` | The robin | yes | land | winter | dawn/day AND Bird feeder with 2 Hedge within 2 | Comes when it's cold, to a feeder. | On winter mornings and days: a bird feeder with two lengths of hedge within two tiles. | Follows Laeticia round the beds, hoping she'll dig something up. |
| `deer` | The deer | yes | land | autumn, winter | dawn/dusk AND Apple tree with 2 Apple tree within 3 AND 16 [tree] in total | Steps out of a big wood in the cold seasons. | In autumn or winter, at dawn or dusk: three apple trees close together, and sixteen trees in all. | Takes one apple, very politely, and is gone. |

### 5.4 Nooks (16)

| id | Name | Recipe | Journal teaser (before) | Blurb (after) | Gift | Effects |
|---|---|---|---|---|---|---|
| `reading_nook` | Reading nook | Bench with 1 Lamp post, 1 [tree] within 1 | Somewhere to read after dark. | A bench, a lamp, and a tree for shade. | Laeticia reads here in the afternoons. | `[{"prefer": {"who": "laeticia", "activity": "read"}}]` |
| `lakeside_lunch` | Lakeside lunch | Picnic table with 3 Water tiles within 2 | Lunch with a view of the water. | A picnic table close enough to hear the ducks. | After a harvest, Laeticia eats lunch here and the ducks drift over. | `[{"routine": "lunch"}, {"prefer": {"who": "duck", "activity": "wander"}}]` |
| `kitchen_garden` | Kitchen garden | Veggie bed with 3 Veggie bed, 1 Scarecrow within 2 | Beds, and someone to guard them. | Four beds and a scarecrow keeping an eye on them. | Beds here grow a little faster, and the hens come to peck. | `[{"growth": 1.25}, {"prefer": {"who": "hen", "activity": "peck_bed"}}]` |
| `firefly_hollow` | Firefly hollow | night AND Tall grass with 3 Tall grass, 1 Mushrooms, no [light] within 2 | Long grass, mushrooms, and no lamps. | A dark, damp, grassy place the fireflies adore. | Fireflies gather here, and more of them come. | `[{"prefer": {"who": "firefly", "activity": "wander"}}, {"cap": {"visitor": "firefly", "add": 4}}]` |
| `hen_yard` | Hen yard | Hen coop with 4 [line], 1 Hay bale within 2 | A fenced yard with hay to scratch in. | A coop, a fence, and hay to scratch about in. | The hens spend their afternoons here. | `[{"prefer": {"who": "hen", "activity": "peck"}}]` |
| `duck_cove` | Duck cove | Lily pads with 2 Reeds, 8 Water tiles within 2 | Lily pads, reeds, and room to swim. | A sheltered bit of pond with lilies and reeds. | The ducks sleep on this bank at night. | `[{"prefer": {"who": "duck", "activity": "sleep_bank"}}]` |
| `bee_garden` | Bee garden | Beehive with 5 [flower], 1 Lavender, 1 Sunflowers within 2 | A hive in a garden of many flowers. | Lavender, sunflowers, and a hive in the middle of it all. | Two more bees join the hive. | `[{"cap": {"visitor": "bee", "add": 2}}]` |
| `orchard` | Orchard | Apple tree with 4 Apple tree within 3 | Apple trees, planted close. | Five apple trees, close enough to share their bees. | Apples fall in autumn, and the deer come sooner. | `[{"fx": {"name": "apple", "seasons": ["autumn"]}}, {"rare_rate": {"visitor": "deer", "mul": 2}}]` |
| `village_square` | Village square | Fountain with 10 Cobble tiles, 1 [seat], 1 Lamp post within 2 | Cobbles, a fountain, a seat and a lamp. | A fountain on cobbles, with a seat and a lamp. | Laeticia sketches here on fine afternoons. | `[{"prefer": {"who": "laeticia", "activity": "sketch"}}]` |
| `campfire_circle` | Campfire circle | Campfire with 2 [seat], 1 Log pile within 2 | A fire with seats and wood to burn. | Two seats, a fire, and a pile of logs to keep it going. | Laeticia and the cat sit here together at dusk. | `[{"prefer": {"who": "laeticia", "activity": "warm"}}, {"prefer": {"who": "cat", "activity": "warm"}}]` |
| `secret_garden` | Secret garden | Rose arch with 6 Hedge, 3 [flower], 1 Bench within 3 | Behind a hedge, through an arch. | Hedges all round, flowers inside, and a bench to hide on. | Butterflies gather here. | `[{"prefer": {"who": "butterfly", "activity": "rest"}}]` |
| `little_harbour` | Little harbour | Rowing boat with 1 [crossing], 1 Lamp post within 2 | A boat, a way across, and a light. | A rowing boat tied up by a lamp and a crossing. | The heron fishes here, and the ducks paddle past. | `[{"prefer": {"who": "heron", "activity": "fish"}}, {"prefer": {"who": "duck", "activity": "wander"}}]` |
| `woodland_walk` | Woodland walk | Path tiles with 8 [tree], 1 Mushrooms within 2 | A path through the trees. | A path under the branches, mushrooms along the edge. | Laeticia takes her evening stroll here, and leaves fall thicker. | `[{"prefer": {"who": "laeticia", "activity": "stroll"}}, {"fx": {"name": "leaf", "mul": 2}}]` |
| `farmyard` | Farmyard | Barn with 1 Hen coop, 2 Hay bale, 2 Veggie bed within 2 | Barn, coop, hay and beds together. | A barn with hens, hay and beds around it. | The cat naps on the hay. | `[{"prefer": {"who": "cat", "activity": "nap"}}]` |
| `moon_garden` | Moon garden | night AND Daisies with 3 Daisies, 1 Bench, 1 Lamp post within 2 | White flowers by lamplight. | Daisies that glow in the lamplight, and a bench to see them from. | Laeticia steps out at night to see it. | `[{"routine": "moon_stroll"}]` |
| `wishing_well` | Wishing well | Well with 4 Cobble tiles, 2 [flower] within 2 | A well on cobbles, among flowers. | A well with cobbles round it and flowers at its feet. | Laeticia tosses in a pebble when she passes. | `[{"routine": "pebble"}]` |

### 5.5 Laeticia's lines

Context keys are the `resident.lines` keys. Each bubble is at most 52 characters.

| Context | When | Lines |
|---|---|---|
| `tour` | Onboarding step 1 only | Oh, it's lovely. A bit bare, though. |
| `greet` | Corner loaded, she is visible (waves) | There you are. Kettle's on. · Hello again. Come and see. · Oh good, I was hoping you'd come by. · Back again? Good. I've news. |
| `morning` | She leaves home at dawn | Another day. Let's see what's grown. · Up with the birds, as usual. · Cold dew, warm tea. Good morning. · Right. Watering can, then breakfast. |
| `dusk` | First idle moment after dusk starts | Lovely light. It never lasts. · The sky's doing its show again. · One more cup of tea, then bed. |
| `night` | Walking home at night | That's me done. Goodnight. · Bed. My knees insist. · Goodnight, corner. |
| `no_cottage_night` | Lying down on the bedroll | Stars again. They are very nice stars. · The ground's harder than I remember. · Someday, a roof. Tonight, a blanket. |
| `home_lost` | Her home cottage was removed | Well. Back to the stars, then. · I'll find somewhere to sleep. Somehow. |
| `rain_start` | Rain starts (not winter) | Rain. The beds will be pleased. · I'll be inside if anyone wants me. · There goes my washing. |
| `rain_stop` | Rain or snow stops | That's better. Smell that. · Everything looks freshly painted. · Out we go, then. |
| `snow_start` | Snow starts (winter rain) | Snow. I'll put the kettle on. · Look at it come down. Not a sound. |
| `wish_offer` | She offers a wish | I've had a thought. · Can I ask you something? · Just an idea. No hurry at all. · I've been meaning to say something. |
| `already_done` | An offered wish was already satisfied | Oh. You'd already done it. · Well, look at that. It's already there. |
| `place_flower` | Reaction: [flower] placed | Oh, that colour. · The bees will find that by lunch. · I'll press one for the sketchbook. |
| `place_tree` | Reaction: [tree] placed | Something to sit under in fifty years. · Hello, tree. · Good spot. It'll like the light there. |
| `place_water` | Reaction: water painted | More pond. The ducks approve. · I do like the sound of water. · Mind I don't fall in. |
| `place_home` | Reaction: [home] placed | A whole building. Look at you. · I'll have a peek inside later. · That changes the skyline. |
| `place_light` | Reaction: [light] placed | That'll be cosy after dark. · Good. I'm forever tripping over things. |
| `place_seat` | Reaction: [seat] placed | Somewhere to sit. My favourite thing. · I'll test that later. Thoroughly. |
| `place_crop` | Reaction: [crop] placed | Neat rows. I approve. · Something to fuss over. Wonderful. |
| `place_line` | Reaction: [line] placed | Tidy. Very tidy. · Good fences make good hens. |
| `place_stone` | Reaction: [stone] placed | Solid. That'll outlast us both. · I do like a good rock. |
| `place_other` | Reaction: anything else | Oh, that's nice. · Now there's an idea. · I wouldn't have thought of that. |
| `harvest_ready` | First ripe bed of the day, if not harvested within 30 s | Something's ripe, if you want to pick it. · The beds are ready when you are. |
| `harvest_done` | After a harvest she can see | Lovely. Soup tonight. · I'll take that in. Thank you. · That smells like dinner already. |
| `nook_found` | She arrives at a newly discovered nook | Oh, that's a proper little spot. · I'll have to sketch that. · That deserves a name. Let me think. |
| `click` | Player clicks her | Yes? I'm listening. · Did you know daisies close at night? · My sketchbook's nearly full. Nearly. · Hello, you. · Forty years drawing other people's gardens. · I'm not old. I'm well watered. |
| `idle` | Ambient, every 60–120 s while visible (Chatty only) | I talk to the plants. They don't mind. · Hm. That corner wants a little something. · The light here is good for drawing. · I wonder who lived here before. · Quiet. Just how I like it. · I could sit here all afternoon. |
| `first_duck` | First sighting of ducks | Ducks already. They don't waste time. |
| `first_hen` | First sighting of hens | Hens. Opinionated ones, by the look. |
| `first_cat` | First sighting of the cat | Well. I suppose we have a cat now. |
| `first_butterfly` | First sighting of butterflies | A butterfly. Hold still, I'll draw it. |
| `first_bee` | First sighting of bees | Bees. Mind the hive, it's their house. |
| `first_firefly` | First sighting of fireflies | Fireflies. I haven't seen those in years. |
| `first_owl` | First sighting of the owl | An owl. Don't stare, you'll make it shy. |
| `first_heron` | First sighting of the heron | A heron. Stand still and it might stay. |
| `first_hedgehog` | First sighting of the hedgehog | A hedgehog. Little snuffling thing. |
| `first_fox` | First sighting of the fox | A fox. It's only curious. I think. |
| `first_frog` | First sighting of the frog | Someone's singing in the lily pads. |
| `first_koi` | First sighting of the koi | Something orange in the deep water. |
| `first_robin` | First sighting of the robin | A robin. It thinks it owns the place. |
| `first_deer` | First sighting of the deer | Shh. A deer. Don't move. |

Plus one line per land stage (`land.stages[].line`) and per season (`seasons[].line`). Total: 101 lines.

### 5.6 Land stages

| # | id | Name | Area (inclusive rects) | Tiles | Opens at | Revealed underneath | Line |
|---|---|---|---|---|---|---|---|
| 0 | `corner` | The corner | [[20, 20, 39, 39]] | 400 | 0 pages | Starter scene (new worlds) or the v1 map (migrated saves) | — |
| 1 | `west_meadow` | The west meadow | [[8, 20, 19, 39]] | 240 | 4 pages | Meadow ×48, Water ×18; Lavender ×3, Mushrooms ×1, Stump ×1, Tall grass ×2, Reeds ×2, Rock ×1, Oak ×1, Pine ×1 | The brambles are gone. There's a stream back there. |
| 2 | `far_pond` | The far pond | [[20, 8, 39, 19]] | 240 | 9 pages | Water ×32; Lily pads ×2, Reeds ×2, Rowing boat ×1, Blossom tree ×2, Rock ×1, Oak ×1 | There was a pond back there all along. |
| 3 | `old_orchard` | The old orchard | [[8, 8, 19, 19]] | 144 | 14 pages | Meadow ×54, Path ×3; Apple tree ×4, Stone wall ×5, Hay bale ×1 | An old orchard. Somebody loved this place once. |
| 4 | `high_wood` | The high wood | [[0, 0, 7, 39], [8, 0, 39, 7]] | 576 | 20 pages | Water ×21, Path ×46; Pine ×13, Oak ×3, Reeds ×2, Log pile ×1, Mushrooms ×2, Rock ×2, Rose arch ×1, Lamp post ×1, Stone wall ×39 | A whole wood. And a road. Where does that go? |

### 5.7 Seasons

The season table is R4.2; the data is `seasons[]` in the catalog. Season lines: Spring "Spring.
Everything's showing off." · Summer "Summer. Long days and short shadows." · Autumn "Autumn. My
favourite. Don't tell the others." · Winter "First snow. Boots on."

### 5.8 Delights

Rarity column: how often it can happen at most. "RM" = what reduce motion does.

| # | Delight | Trigger | Rarity / cooldown | Art | Audio | RM |
|---|---|---|---|---|---|---|
| 1 | Waterfall | Any opened water tile on the south-east rim (x = 39) or south-west rim (y = 39): a falling-water face hangs below it over the cliff, with mist at the bottom | Always, while the water is there | `edge/fall_se`, `edge/fall_sw` (4 frames), `fx/mist` | `amb/waterfall.ogg`, level = min(1, rim water tiles / 6) × `kWaterfallLevel` | kept |
| 2 | Rainbow | Rain turned off after at least 60 s of rain, during the day phase, not in winter | Once per in-game day; fade in 3 s, hold 40 s, fade out 5 s | `sky/rainbow`, drawn behind the island | `sfx/rainbow.wav` | kept |
| 3 | Shooting star | Night, clear sky | Random, on average every 50 s | `fx/star_streak` moved by the engine along a shallow diagonal with a fading trail | `sfx/twinkle.wav` at 30% | off |
| 4 | Owl call | The owl is present: with its `hoot` every 40–90 s. Not yet seen but 5+ pines at night: a distant call every 4–6 minutes, as a hint | as stated | owl `hoot` | `sfx/owl.wav` (35% for the distant one) | kept |
| 5 | Trees rustle | An item placed, moved or removed within 1 tile of a tree: the tree plays its sway frames at 8 fps for 0.6 s and drops 2 leaves (petals for blossom in spring, nothing in winter) | 0.3 s global cooldown | existing sway frames, `fx/leaf`, `fx/petal` | `sfx/rustle.wav` | sound only |
| 6 | Ducks startle | Placement, move or removal within 2 tiles of a duck (R2.5): flap and paddle off fast, ripples | 5 s per duck | duck `flap`, `fx/ripple` | duck voice + `sfx/flap.wav` | kept |
| 7 | Hens scatter | The same within 1.5 tiles of a hen | 5 s per hen | hen `flap` | hen voice + `sfx/flap.wav` | kept |
| 8 | Cat stretches | Placement within 1 tile of a sleeping cat: it wakes, stretches, wanders off | 5 s | cat `stretch` | `sfx/cat.wav` at 60% | kept |
| 9 | Cooking smoke | After a harvest Laeticia carries home, the home chimney puffs twice as often with two puffs per emission for 90 s | per harvest | existing `fx/smoke` | none | kept |
| 10 | Frog chorus | The frog is present and it is raining, or rain stopped less than 60 s ago: it croaks every 4–8 s | for 60 s after rain | frog `croak` | `sfx/frog.wav` | kept |
| 11 | After-rain and dawn chorus | Rain stops by day: birds ambience ×1.6 for 20 s. Dawn (t 0.875–0.92): birds ×1.4 | each time | none | existing `amb/birds.ogg` level | kept |
| 12 | Butterfly on her hat | Butterfly activity `hat` (R2.2) | at most once per sit | none | none | kept |
| 13 | Floating petals | Petals that land on water float and drift for 6 s | spring | `fx/petal` | none | 30% |
| 14 | Season stinger | First dawn of a season, with Laeticia's season line | 4 per year | none | `sfx/season.wav` | kept |
| 15 | Lamp moths | Night: two moths circle each lamp head (radius 10 px), drawn after night grading at 70% brightness so they look lamp-lit | always at night | `fx/moth` | none | off |
| 16 | Gust | By day, every 2–4 minutes: a wave crosses the map left to right over 2 s; trees, tall grass, reeds, flowers and sunflowers play their sway frames at 3× as it passes; 6 leaves; the windmill turns 2× for 3 s | 2–4 min | existing sway frames, `fx/leaf` | `sfx/gust.wav` | sound only |
| 17 | Fish jump | Day or dusk, if the home region has 8+ water tiles: a fish arcs out of a water tile with no item on it | on average every 90 s | `fx/fish_jump` | `sfx/splash.wav` at 40% | kept |
| 18 | Well plip | Clicking a well with no tool; Laeticia's pebble toss (Wishing well nook) | 1 s per well | Laeticia `toss` | `sfx/well.wav` | kept |
| 19 | The cat watches | A sitting or idle cat within 3 tiles of the hovered tile turns to face the pointer | always | none | none | kept |
| 20 | Fireflies in sync | 8+ fireflies present: they blink in unison for 6 s | every 40–60 s | none | none | kept |
| 21 | Sleepy z's | Sleeping critters and Laeticia on the bedroll | one every 3 s | `fx/zzz` | none | off |

---

## 6 UI

All new panels use the existing dark frosted glass panel, the Nunito text sizes and Lucide icons
(the engine adds the codepoints it needs: settings, menu, move, pipette, grid, lock, sparkles,
flower, sun, leaf, snowflake, frame, image, folder-open, heart, pencil, trash, chevron-left/right).
**A** and **B** mark which engine task owns each piece. Reference size 1280×800.

### 6.1 Main screen (A, B)

```
┌─────────────────────┐                                      ┌──────────────────────────────┐
│ Plum Hollow         │ ◄ click: calendar (6.4)              │ ✦ Wishes                  2  │ ◄ tray (6.2)
│ ☀ Day · Spring 2    │                                      │ (◉) A path up to the door…   │
└─────────────────────┘                                      │ (◉) Six flowers near the h…  │
                                                             │      4 / 6                   │
                        ╭─────────────────────╮              └──────────────────────────────┘
                        │ Hello, tree.        │  ◄ Laeticia's bubble, anchored to her head
                        ╰──────────┬──────────╯
                                   ▼  (world)
                                                   ┌──────────┐
                                                   │ New land ▸│ ◄ edge chip, only after a stage opens off screen
                                                   └──────────┘
┌─────────┐ ┌───┐ ┌───┐        ┌───┬───┬───┬───┬───┐               ┌───┬───┬───┬───┬───┐
│ + Build•│ │ ⌫ │ │ ✥ │        │ ☰ │ ◎ │ ☼ │ ☂ │ ▤ │               │ ↶ │ ↷ │ ⌂ │ − │ + │
└─────────┘ └───┘ └───┘        └───┴───┴───┴───┴───┘               └───┴───┴───┴───┴───┘
 Build  Remove Move             Menu Photo Clock Rain Sketchbook     Undo Redo Home Zoom
                 Click to place · R to rotate · Shift-drag for a straight line   ◄ hint line
```

- The bottom-left group gains **Move** (tooltip "Move · V"). The eyedropper has no button; the Build
  and Move tooltips mention "Alt-click to copy".
- The bottom-centre dock's sound button becomes **Menu** (☰, opens pause). Mute stays on M and in
  Settings. The rain button shows a snowflake in winter (tooltip "Snow · N").
- The sketchbook button replaces the journal button (same place, icon book-open, "Sketchbook · J").
- Title card: second line adds the season: "☀ Day · Spring 2" (icon per phase as today; the season
  name and day after it).
- Hint line additions are listed in 6.10.
- **Hidden until relevant:** wish tray (until the first offer), edge chip (after an off-screen stage
  opens), harvest hint (first ripe bed), brush size (Paint only), "+N" drawer tiles (only while a tab
  has locked pieces), Nooks tab (until the first nook), Rarer visitors section (after four common
  visitors), coach card (tour only).

### 6.2 Wish tray (A)

Top right, 300 px wide at 1×, stacked cards, one per open wish (max 3):

```
┌──────────────────────────────────┐
│ ✦ Wishes                     2   │  header; click toggles collapsed (header only)
├──────────────────────────────────┤
│ (portrait) A path up to the door,│  giver portrait 28 px: Laeticia's portrait or the
│            so I stop tracking…   │  visitor's idle_front f0; text 2 lines max, ellipsis
├──────────────────────────────────┤
│ (portrait) Six flowers near the  │
│            hive would help.      │
│            ▓▓▓▓▓▓░░ 4 / 6        │  progress (count goals) or "Waiting for nightfall"
└──────────────────────────────────┘
```

States: normal; hover (lighter glass, full text in a tooltip); **ready** (the 1.5 s before granting:
soft gold edge glow); entering (slides in from the right 0.25 s); leaving (fades up 0.3 s).
Right-click a card: small menu "Not now". Clicking a card opens the sketchbook's Wishes tab at it.
The tray hides while the sketchbook is open (same corner of the screen) and in photo mode.

### 6.3 Sketchbook (A; replaces the Visitors journal, same position and size)

```
┌ Sketchbook ───────────────────────────────────────────── ✕ ┐
│ 13 of 30 pages   ▓▓▓▓▓▓▓▓▓░░░░░  1 more until the old orchard │
│ [ Wishes ]  [ Visitors ]  [ Nooks ]                           │
├───────────────────────────────────────────────────────────────┤
│ Open                                                          │
│ (◉) Six flowers near the hive would help.          Not now    │
│     ▓▓▓▓░░ 4 / 6                                              │
│ (◉) I'd like to read outside after dark…           Not now    │
│     Waiting for nightfall                                     │
│ Granted                                                       │
│ (◉) There. Now it smells like somewhere.   ✓ Lavender, Berry… │
│ …                                                             │
└───────────────────────────────────────────────────────────────┘
```

- Header: page count, a thin progress bar to the next land stage and "N more until <stage name>"
  ("Every part of the map is open" when done).
- **Wishes tab:** Open (with Not now), then Granted, newest first, showing the thanks line and the
  reward. Snoozed wishes are not listed (they will come back).
- **Visitors tab:** common visitors as today (sprite or silhouette, name, blurb or hint, "here now"
  dot); then **Rarer visitors**: silhouette and hint, plus "Laeticia's note: <clue>" once clued, or
  sprite, name and blurb once seen.
- **Nooks tab:** discovered nooks (name, blurb, gift in a smaller line) and undiscovered ones as
  "? ? ?" with their teaser in dim italics.
- Tabs switch with a click or ←/→ while the panel is open; `sfx/page.wav` on each switch.
- Scrolls with the wheel when longer than the panel.

### 6.4 Calendar popover (A)

Opens below the title card when it is clicked; closes on Esc or clicking elsewhere.

```
┌ Calendar ─────────────────────┐
│ Spring · day 2 of 3           │
│ [✿ Spring][☀ Summer][❦ Autumn][❄ Winter]   current one highlighted
│ Seasons                       │
│ (•) Follow the days           │
│ ( ) Always spring             │
│ ( ) Always summer             │
│ ( ) Always autumn             │
│ ( ) Always winter             │
└───────────────────────────────┘
```

### 6.5 Title screen (B)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ (the last world's home region, drifting)                                     │
│   ┌───────────────────────────┐                                              │
│   │   [ title/logo sprite ]   │                                              │
│   │                           │                                              │
│   │ [ Continue · Plum Hollow ]│   first launch: [ Begin ]                    │
│   │ [ Worlds                 ]│   hidden on first launch                     │
│   │ [ Settings               ]│                                              │
│   │ [ Quit                   ]│                                              │
│   └───────────────────────────┘                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Keyboard: ↑/↓ move focus, Enter activates, Esc does nothing on the title. Buttons have hover,
pressed, focused and disabled states like the existing pills.

### 6.6 Worlds screen, dialogs (B)

```
┌ Your worlds ──────────────────────────────────────────────────────── Back · Esc ┐
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌ ─ ─ ─ ─ ─ ─ ┐              │
│ │  thumb.png   │ │  thumb.png   │ │  thumb.png   │ │      +       │              │
│ │              │ │              │ │              │ │  New world   │              │
│ └──────────────┘ └──────────────┘ └──────────────┘ └ ─ ─ ─ ─ ─ ─ ┘              │
│  Plum Hollow      Laeticia's Corner Fernbank                                     │
│  Autumn, day 3 · 14 pages                                                        │
│  [ Play ] [✎] [🗑]   ◄ on hover / keyboard focus                                  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌ Name your world ───────────────────┐     ┌──────────────────────────────────────┐
│ [ Laeticia's Corner_            ]  │     │ Delete “Plum Hollow”?                │
│ ( ) Free build                     │     │ The whole world goes, corner and     │
│     Everything unlocked and all    │     │ all. Its postcards stay where they   │
│     land open from the start.      │     │ are. This can't be undone.           │
│     Wishes still come, just for    │     │            [ Keep it ]  [ Delete ]   │
│     the company.                   │     └──────────────────────────────────────┘
│            [ Cancel ]  [ Create ]  │      Delete is the non-default button; Enter = Keep it
└────────────────────────────────────┘
```

### 6.7 Pause menu and settings (B)

```
        ┌───────────────────────────┐        ┌ Settings ────────────────────────────────┐
        │          Paused           │        │ Sound                                     │
        │ [ Resume            Esc ] │        │  Music        ──────────●──── 70          │
        │ [ Settings              ] │        │  Effects      ────────────●── 85          │
        │ [ Open postcards folder ] │        │  Ambience     ───────●─────── 60          │
        │ [ Back to worlds        ] │        │  Mute all                    M   [ off ]  │
        │ [ Quit                  ] │        │ Display                                   │
        └───────────────────────────┘        │  Fullscreen                F11   [ off ]  │
                                             │  Interface size        [ Auto       ▾ ]  │
                                             │  Reduce motion                   [ off ]  │
                                             │  Show grid                   G   [ off ]  │
                                             │ Laeticia                                  │
                                             │  Chatter            [ Chatty | Quiet ]    │
                                             │ Help                                      │
                                             │  First-minute tour             [ Replay ] │
                                             │                                 [ Done ]  │
                                             └───────────────────────────────────────────┘
```

Sliders: drag, click on the track, or focus and ←/→ (steps of 5). Moving the Effects slider plays
`sfx/ui_click.wav` at the new level once per 0.15 s.

### 6.8 Photo bar (B)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ‹ Frame: Pressed flowers › F │ Caption ● T │ Hide bar H │ ◉ Take postcard  Space │ 📂 │ ✕ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Fades after 2 s without pointer movement. Locked frames are not offered.

### 6.9 Coach card (B) and unlock ribbon (A)

```
╭──────────────────────────────────────────────────╮
│ Open Build to plant something.        Skip tour  │   above the bottom-centre dock
╰──────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────╮
│ ✦ Wish granted                                   │   wider toast, top centre, 4 s
│ New in Build:  [icon] Cobble   [icon] Pine       │
╰──────────────────────────────────────────────────╯
```

### 6.10 New interface strings (final text; they go in `strings.hpp`)

| Where | Text |
|---|---|
| Tools | Move · Copy (Alt-click) · Brush 1×1 · Brush 3×3 · Brush 5×5 |
| Hints | Click something to pick it up · Esc to cancel / Click to put it down · R to rotate · Esc to put it back / Click and drag to paint · [ ] brush size · Shift-drag for a rectangle · Esc to cancel / Click to remove · Shift-drag to clear an area · Esc to cancel / " · Shift-drag for a straight line" (appended for 1×1 items) / Click something to copy it · Esc to cancel / Ripe beds can be picked. Click one. |
| Warnings | This land is still wild · Not unlocked yet · Nothing to pick up here |
| Tooltips | Ripe · click to pick · The road out · Wild land · opens at {n} pages ({k} more) · {n} more to discover. Grant wishes to unlock them. · Sketchbook · Menu · Snow · Move |
| Toasts | Wish granted · New in Build: {list} · New postcard frame: {name} · Laeticia's note added to the sketchbook · New nook: {name} · {n} of {total} pages · New land: {name} · New land (edge chip) · Postcard saved · Couldn't save the postcard · Welcome back. Laeticia has started a sketchbook: {n} pages so far. |
| Wish states | Wishes · Not now · Waiting for nightfall · Waiting for dusk · Waiting for dawn · Waiting for daytime · Waiting for {season} · Waiting for rain · Waiting for clear skies · Open · Granted |
| Sketchbook | Sketchbook · Wishes · Visitors · Nooks · {n} of {total} pages · {k} more until {stage} · Every part of the map is open · Rarer visitors · Laeticia's note: · Here now |
| Calendar | Calendar · {Season} · day {d} of 3 · Seasons · Follow the days · Always spring · Always summer · Always autumn · Always winter |
| Title | Continue · {name} · Begin · Worlds · Settings · Quit |
| Worlds | Your worlds · New world · Play · Rename · Delete · Back · {Season}, day {d} · {n} pages · This world couldn't be opened |
| Dialogs | Name your world · Free build · Everything unlocked and all land open from the start. Wishes still come, just for the company. · Create · Cancel · Give it a name first · You already have a world with that name · Delete “{name}”? · The whole world goes, corner and all. Its postcards stay where they are. This can't be undone. · Keep it · Delete |
| Pause | Paused · Resume · Settings · Open postcards folder · Back to worlds · Quit |
| Settings | Settings · Sound · Music · Effects · Ambience · Mute all · Display · Fullscreen · Interface size · Auto · Reduce motion · Show grid · Laeticia · Chatter · Chatty · Quiet · Help · First-minute tour · Replay · Done |
| Tour | Drag to look around. · Open Build to plant something. · Pick the daisies, then click the ground. · Laeticia has a wish. Granting it unlocks new pieces. · Ctrl+Z undoes anything. J opens the sketchbook. · That's all. Make yourself at home. · Skip tour |
| Photo bar | Frame · Caption · Hide bar · Take postcard · Open folder · Close |
| Dates | January … December (full English month names) |

---

## 7 Art list

All sizes are approximate at the new 64×32 tile density. Keys follow the CLAUDE.md scheme; the
extensions below are new. "Must" items are needed for task A or B to look finished; "nice" items
can follow, since the engine always falls back (season looks to the plain key, missing sprites to
the placeholder).

### 7.1 Scheme extensions

| Extension | Form | Rule |
|---|---|---|
| Season looks | `<any key>@spring\|@summer\|@autumn\|@winter` | Optional override of any sprite for one season. Items list which looks exist in `season_looks`; the generator reads it. The plain key is the fallback, so a base that already shows one season (blossom's base is in bloom, i.e. spring) needs overrides only for the others. |
| Growth stages | `item/<id>/<layer>/<variant>/g<stage>/f<frame>` | For items with `growth`. `g0` bare soil, `g1` sprouts, `g2` leafy, `g3` ripe. Layers may omit `g` (planter shadows stay `item/planter/shadow/r<k>/f0`). |
| Directional or plain animations | `critter/<id>/<anim>_front\|_back/f<n>` or `critter/<id>/<anim>/f<n>` | New animations may be plain (no suffix): the engine uses the same frames for front and back and mirrors for the left-facing directions. The four original animations stay directional. |
| Resident | `critter/laeticia/<anim>/f<n>` | Laeticia uses the critter scheme. Anchor: ground contact point. |
| Portrait | `ui/portrait/laeticia` | 28×28 head and shoulders for wish cards. |
| Wild land | `wild/thicket/v<n>` | Anchored like terrain items (top vertex of the tile). |
| Waterfalls | `edge/fall_se/f<n>`, `edge/fall_sw/f<n>` | Anchored like `edge/cliff_*`, drawn over the cliff face. |
| Sky | `sky/rainbow` | Anchor: bottom centre of the arc. |
| Title | `title/logo` | Drawn at UI scale, integer multiples only. |
| Postcard frames | `frame/<id>/tl, t, tr, l, r, bl, b, br, plate` | Nine-slice minus the centre (transparent); `t`, `b`, `l`, `r` tile. `plate` is the caption backing. |
| Produce | `fx/produce/f<k>` | Frame `k` is the crop of planter variant `r<k>` (not an animation). |

### 7.2 New items (must, 94 sprites)

| Item | Footprint, layout | Keys | Count | Size | Look |
|---|---|---|---|---|---|
| Apple tree | 1×1, variant ×2, sway 2 frames | `item/apple_tree/base/r0-1/f0-1` (+ `@spring`, `@autumn`, `@winter`), `…/shadow/r0-1/f0-1` | 16 + 4 | 64×96 | Rounded fruit tree, smaller than the oak; base: green with red apples; spring: white blossom; autumn: orange leaves, apples; winter: bare grey-brown branches |
| Sunflowers | 1×1, variant ×4 | base r0-3, shadow r0-3 | 8 | 40×64 | Three or four tall stems, big yellow faces turned south-east |
| Log pile | 1×1, rotate ×2 | base r0-1, shadow r0-1 | 4 | 56×36 | Stacked split logs, pale cut ends, a little moss |
| Stepping stones | 1×1, variant ×4, on water, walkable | base r0-3 (no shadow) | 4 | 56×24 | Three or four flat grey stones with a wet rim, sitting in the water |
| Stone wall | 1×1, connect | base m0-15, shadow m0-15 | 32 | 64×40 | Knee-high dry-stone wall, grey and ochre stones, moss on top; connects like the fence |
| Rose arch | 1×1, rotate ×2, walkable | base r0-1, shadow r0-1 | 4 | 60×80 | Painted white wooden arch climbed by pink roses; r0 opening faces +x |
| Bird feeder | 1×1, rotate ×1 | base r0, shadow r0 | 2 | 24×56 | Wooden post with a little roofed tray of seed |
| Hay bale | 1×1, variant ×2 | base r0-1, shadow r0-1 | 4 | 48×36 | Round golden bale (r0) and square bale (r1), loose straw at the foot |
| Hammock | 2×1, rotate ×2 | base r0-1, shadow r0-1 | 4 | 110×56 | Two wooden posts with a striped cream and green canvas hammock; r0 runs along x |
| Fountain | 2×2, rotate ×1, 4 frames | base r0/f0-3, shadow r0/f0-3 | 8 | 128×96 | Round stone basin with a two-tier spout; water animates in 4 frames |
| Rowing boat | 2×1, rotate ×2, on water | base r0-1, shadow r0-1 | 4 | 96×48 | Small wooden boat, faded blue paint, two oars shipped, moored with a rope |

### 7.3 Growth, seasons and existing items

| What | Keys | Count | Must/nice | Look |
|---|---|---|---|---|
| Veggie bed stages | `item/planter/base/r0-3/g0-3/f0` | 16 | must | `g0` raked dark soil in the bed frame; `g1` small green sprouts in rows; `g2` leafy, crop not yet visible; `g3` ripe (today's art per crop) |
| Grass by season | `terrain/grass/v0-3@spring`, `@autumn`, `@winter` | 12 | must | spring: fresher green with a few tiny white and yellow flowers; autumn: olive and straw tones; winter: thin snow with grass showing through |
| Oak by season | `item/oak/base/r0-3/f0-1@autumn`, `@winter` | 16 | must | autumn: orange, rust and gold canopy; winter: bare branches |
| Blossom by season | `item/blossom/base/r0-3/f0-1@summer`, `@autumn`, `@winter` | 24 | must | summer: green leaves; autumn: red-orange; winter: bare (the base stays the spring bloom) |
| Pine in winter | `item/pine/base/r0-3/f0-1@winter` | 8 | must | snow along the tiers |
| Meadow by season | `terrain/meadow/m0-15/f0@autumn`, `@winter` | 32 | nice | autumn: seed heads, gold; winter: snow-dusted stubble |
| Shrubs in winter | `item/bush/base/r0-3/f0@winter`, `item/berry_bush/…@winter`, `item/hedge/base/m0-15/f0@winter` | 24 | nice | a cap of snow |
| Flowers in winter | `item/flowers_*/base/r0-3/f0@winter` (×3), `item/sunflowers/base/r0-3/f0@winter` | 16 | nice | dried seed heads, bent stems |
| Bare-tree shadows | `item/oak/shadow/r0-3/f0-1@winter`, `item/blossom/shadow/r0-3/f0-1@winter`, `item/apple_tree/shadow/r0-1/f0-1@winter` | 20 | nice | thin branch shadows |

### 7.4 Critters

Existing visitors, new animations (must, 37):

| Key | Frames | Look |
|---|---|---|
| `critter/cat/sleep` | 2 | curled up, tail over nose, slow breathing |
| `critter/cat/sit` | 2 | sitting upright, tail flick |
| `critter/cat/groom` | 4 | licking a paw, washing an ear |
| `critter/cat/stretch` | 4 | front legs out, back arched, then shake |
| `critter/hen/peck` | 3 | head down to the ground and up |
| `critter/hen/flap` | 3 | wings out, a small hop |
| `critter/duck/dabble` | 3 | tail up, head under water |
| `critter/duck/sleep` | 2 | sitting on the bank, head tucked under a wing |
| `critter/duck/waddle_front`, `waddle_back` | 4 + 4 | walking on land |
| `critter/duck/flap` | 3 | wings beating, splash |
| `critter/butterfly/rest` | 3 | landed, wings slowly opening and closing |

Rare visitors (must, 112): each has `move_front`, `move_back` (4 frames each) and `idle_front`,
`idle_back` (2 frames each), plus the specials listed.

| Visitor | Size | Specials | Look |
|---|---|---|---|
| Owl | 24×28 | `hoot` 3 | tawny owl, round face, ear tufts low; flying frames for move |
| Heron | 40×56 | `fish` 4 (neck strike down and back) | grey heron, long neck folded, black crest stripe; slow wading walk |
| Hedgehog | 20×14 | `curl` 2 | brown-grey spines, pointed snout, tiny feet |
| Fox | 36×24 | `sleep` 2 | russet fox, white chest, dark socks, brush tail |
| Frog | 12×10 | `croak` 2 (throat sac) | small green frog, gold eye; move is a hop |
| Koi | 24×10 | none | orange and white carp seen from above at a slant; drawn under water by the engine |
| Robin | 12×12 | none | round little bird, orange-red breast; move is a hop |
| Deer | 44×52 | `graze` 3 | roe deer, slender, warm brown, white rump |

Laeticia (must, 74):

| Key | Frames | Look |
|---|---|---|
| `move_front`, `move_back` | 6 + 6 | walking, satchel swinging (22×46) |
| `idle_front`, `idle_back` | 2 + 2 | standing, a breath |
| `sit_front`, `sit_back` | 2 + 2 | seated (on a bench, stump, picnic bench or hay), hands in lap |
| `read_front`, `read_back` | 2 + 2 | seated, reading the sketchbook, page turn |
| `water_front`, `water_back` | 4 + 4 | tilting a green watering can, droplets |
| `scatter_front`, `scatter_back` | 4 + 4 | throwing grain from her apron pocket |
| `carry_front`, `carry_back` | 6 + 6 | walking with a basket on her hip |
| `lie_front`, `lie_back` | 2 + 2 | lying in the hammock reading (drawn over the hammock, anchored at its centre) |
| `sketch` | 2 | sitting on the ground, sketchbook on her knees, pencil moving |
| `warm` | 2 | standing, hands held out to a fire |
| `sleep` | 2 | lying on her bedroll under a patchwork blanket (bedroll included) |
| `stretch` | 4 | arms up, morning stretch |
| `wave` | 4 | one hand raised, waving |
| `toss` | 3 | tossing a pebble underarm |
| `ui/portrait/laeticia` | 1 | head and shoulders, glasses, bun, green cardigan (28×28) |

### 7.5 Effects, land, sky, interface (must, 85)

| Key | Frames | Size | Look |
|---|---|---|---|
| `fx/heart` | 4 | 9×8 | small pink pixel heart rising and fading |
| `fx/petal` | 4 | 4×4 | pink petal tumbling |
| `fx/snowflake` | 4 | 3×3 | white flake, slight twinkle |
| `fx/moth` | 2 | 3×3 | pale moth, wings |
| `fx/fish_jump` | 6 | 16×16 | silver fish arcing out of the water and back, with splash |
| `fx/star_streak` | 1 | 48×3 | white-to-transparent streak |
| `fx/apple` | 2 | 6×6 | red apple falling (f0), lying in the grass (f1) |
| `fx/clear` | 6 | 48×32 | burst of bramble leaves and dust as a thicket clears |
| `fx/mist` | 4 | 40×16 | soft white spray at a waterfall's foot |
| `fx/zzz` | 3 | 8×10 | small "z" drifting up |
| `fx/produce` | 4 | 14×14 | the crop of each bed variant, matching the four crops of today's planter looks |
| `edge/fall_se`, `edge/fall_sw` | 4 + 4 | 64×56 | falling water sheets over the cliff face, white foam lines moving down |
| `wild/thicket/v0-5` | 6 | 64×56 | dark brambles, nettles and briar on overgrown grass; dense, low-contrast, cool and dim so it reads as background |
| `sky/rainbow` | 1 | 480×160 | soft pastel arc, mostly transparent, faded ends |
| `ui/tile_grid` | 1 | 64×32 | 1-pixel diamond outline, white |
| `ui/tile_area` | 1 | 64×32 | full diamond, white, soft edge (tinted and faded by the engine) |
| `title/logo` | 1 | 320×96 | hand-lettered pixel logotype "Laeticia's Corner" with a sprig of blossom; cream with a moss-green outline |
| `frame/pressed_flowers/*` | 9 | corners 48×48, edges 32 | cream paper with pressed daisies, poppies and lavender at the corners |
| `frame/watercolour/*` | 9 | same | soft blue-green watercolour wash edges, ragged paper |
| `frame/starry/*` | 9 | same | deep blue border with small gold stars and a crescent moon top right |

### 7.6 Totals

| Group | Must | Nice |
|---|---|---|
| New items | 94 | — |
| Growth | 16 | — |
| Season looks | 60 | 92 |
| Existing visitors' animations | 37 | — |
| Rare visitors | 112 | — |
| Laeticia (incl. portrait) | 74 | 12 (`umbrella_front`, `umbrella_back`, 6 + 6: walking under an umbrella in the rain) |
| Effects, land, sky, interface, title, frames | 85 | 2 (`fx/footprint` in snow, `fx/egg` by the coop) |
| **Total** | **478** | **106** |

Order of work: Laeticia, wild land and growth first (task A shows wishes and land; task B needs her),
then new items, season looks, rare visitors, effects and frames.

---

## 8 Audio list

Formats follow CLAUDE.md: music and ambience are seamless whole-file loops, Ogg Vorbis, 44.1 kHz
stereo, true peak ≤ −1 dB; effects are WAV, 44.1 kHz, 16-bit mono, peak ≤ −3 dB, no clicks.

### 8.1 Music stems (10)

| File | Length | Description |
|---|---|---|
| `music/day_pad.ogg` | 106.667 s (4,704,000 samples) | the day piece's warm pad |
| `music/day_keys.ogg` | same | felt piano chords |
| `music/day_melody.ogg` | same | music box melody |
| `music/day_bass.ogg` | same | bass |
| `music/day_colour.ogg` | same | new: wooden flute counter-line answering the melody, brushed shaker on the off-beats |
| `music/night_pad.ogg` | same | the night piece's pad |
| `music/night_keys.ogg` | same | felt piano chords |
| `music/night_melody.ogg` | same | the night lead |
| `music/night_bass.ogg` | same | bass |
| `music/night_colour.ogg` | same | new: bowed cello harmonics and a low clarinet line |

- Rendered from the same session as `music/day.ogg` and `music/night.ogg` (which stay, as the title
  mixes), sample-aligned, identical length, each a seamless loop on its own and in any combination.
- Loudness: the sum of all five stems of a piece sits at about −18 LUFS integrated with true peak
  ≤ −1 dB (so the full set equals the current mix plus the colour stem). Each stem keeps its natural
  level inside that mix; do not normalise stems individually.
- Pad and keys alone must sound complete and calm, since that is what a new world hears first.

### 8.2 Ambience (5)

| File | Length | Description |
|---|---|---|
| `amb/autumn.ogg` | 60–90 s | autumn day: wind through drying leaves, a few distant birds, occasional leaf skitter |
| `amb/winter.ogg` | 60–90 s | winter day: soft cold wind, sparse small-bird calls, muffled stillness; also the snow bed |
| `amb/night_spring.ogg` | 60–90 s | spring night: light breeze, very distant tree frogs, no crickets |
| `amb/night_winter.ogg` | 60–90 s | winter night: near silence, faint wind, an occasional creak of a branch |
| `amb/waterfall.ogg` | 30–60 s | close small waterfall: steady fall, splashes, no rumble below 80 Hz |

Beds sit at −21 to −23 LUFS like the existing ones.

### 8.3 Effects (36)

| File | Length | Description |
|---|---|---|
| `sfx/note_0.wav` … `sfx/note_9.wav` | 1.2 s each | kalimba-like pluck matching the music-box timbre, natural decay: D4, E4, F♯4, A4, B4, D5, E5, F♯5, A5, B5 (A4 = 440 Hz), balanced to each other |
| `sfx/owl.wav` | 1.5 s | tawny owl "hoo… hoo-hoo", soft |
| `sfx/heron.wav` | 0.8 s | one low, gentle "kraak", distant |
| `sfx/hedgehog.wav` | 0.8 s | snuffling and a tiny squeak |
| `sfx/fox.wav` | 0.6 s | a soft huffing chirp, never a scream |
| `sfx/frog.wav` | 0.7 s | two-note croak |
| `sfx/robin.wav` | 1.0 s | short liquid trill |
| `sfx/deer.wav` | 0.5 s | soft snort |
| `sfx/laeticia_1.wav`, `_2`, `_3` | 0.3–0.5 s | wordless murmurs: a thoughtful "mm", a warm "hm-hm", a small amused breath |
| `sfx/purr.wav` | 1.2 s | cat purr |
| `sfx/pet.wav` | 0.4 s | soft rustle and a tiny chime, for voiceless critters |
| `sfx/wish.wav` | 0.8 s | paper slip and two rising notes (D5, A5) |
| `sfx/wish_granted.wav` | 1.4 s | warm four-note rise D–F♯–A–D on kalimba and soft bell |
| `sfx/nook.wav` | 2.0 s | shimmering pentatonic arpeggio, harp and glass |
| `sfx/land_open.wav` | 3.0 s | rising rustle sweep of leaves with a low warm swell |
| `sfx/season.wav` | 2.5 s | soft chime with a breath of wind |
| `sfx/harvest.wav` | 0.5 s | earthy pluck and a leafy pop |
| `sfx/rustle.wav` | 0.6 s | leaves shaking in a tree |
| `sfx/flap.wav` | 0.5 s | a few wing beats |
| `sfx/gust.wav` | 2.5 s | a passing gust of wind |
| `sfx/rainbow.wav` | 3.0 s | gentle rising shimmer |
| `sfx/twinkle.wav` | 0.6 s | tiny high sparkle |
| `sfx/well.wav` | 1.0 s | pebble plip with a deep echo |
| `sfx/pick.wav` | 0.25 s | soft lift, for picking up with the move tool |
| `sfx/page.wav` | 0.35 s | sketchbook page turn |

Placement and voice effects are balanced by their loudest 100 ms as today; notes are played by the
engine about 8 dB under the place sounds (`kNoteLevel`), so render them at normal effect level.

---

## 9 Engine work breakdown

Two tasks of roughly equal size, run one after the other in the engine lane. The game is playable
and shippable after each.

### Task A: the progress loop

Makes the corner a game: wishes, unlocks, pages, land, seasons, growth and the growing music.
Critters keep today's wandering; Laeticia exists only as the voice and portrait on wish cards.

1. **Catalog v2**: accept `version: 2`, 64×32 tiles and the 40×40 map (projection constants follow
   the tile size); parse and validate every new section and field in §11 with errors that name the
   entry; keep v1 field meanings. Port the reachability check from the design build (every unlock
   reachable, no wish needing a locked piece) as a unit test over the real catalog.
2. **Condition evaluator** (`src/core`): §3, with the waiting mode and progress readout, and nook
   instance enumeration. Opened-tile terrain counts in `World`.
3. **Saves**: profile, worlds folder, v2 world save with global progress and the home region,
   v1 migration (§2.5), thumbnails (R10.9). Until task B adds the worlds screen, the game opens
   the last world or creates one.
4. **Unlocks and drawer**: filtering, "+N" tile, new dots.
5. **Wishes**: R1 offer, pacing, grant, snooze; wish tray (6.2); unlock ribbon (6.9).
6. **Sketchbook** (6.3) replacing the journal, with rare silhouettes, hints and clues.
7. **Rare visitor presence** (R3.1, R3.2) and per-visitor `seasons`, using today's wander motion.
8. **Nooks**: detection, discovery flourish, hover outline (R7.1–R7.3), `growth` and `cap` effects.
9. **Land**: wild rendering and refusal, page thresholds, reveals, opening wave, edge chip, the
   road-and-gate boundary (R5).
10. **Calendar and seasons**: day counter, season pin and calendar popover (6.4), grades, sprite
    resolution with `@season` and `g<stage>` (R4.3), seasonal ambience, snow, petals and leaves.
11. **Growth and harvest** (R4.4, R4.5), growth in the item record and the save.
12. **Music stems and tuned notes** (R8).

Tests (unit): each condition operator, area rules (footprint excluded, anchor excluded, wild tiles
excluded, `max: 0`, `anchors`); waiting mode; wish offer order and pacing with a fake play clock;
grant stability across an undo; snooze; v1 → v2 migration from fixture saves (offset, legacy
unlocks, silently done wishes, journal, muted moving to the profile); v2 round trip; slug rules;
land coverage and reveal placement; calendar boundaries at midnight and pin behaviour; growth timing
with each multiplier; sprite resolver fallback order; note walker sequence for a fixed seed; stem
unlock fade bookkeeping.
Tests (scripted, with shots): first wish granted by placing flowers; wish waiting for nightfall
then granting at dusk; nook flourish; land stage 1 opening (shots mid-wave and after); the four
seasons at day; snow at night; ripe bed harvest; sketchbook tabs; drawer "+N" tile.
Bench: condition evaluation under 1 ms with a full map; frame budget unchanged.

### Task B: life and the front door

Makes it feel alive and finished: behaviours, Laeticia, delights, the title flow, builder comforts,
postcards.

Items 1–3 are the first three tasks of the shared simulation layer and are specified and tested
there (`living-world.md` §10); they are not built separately for the corner:

1. **Visitor behaviours** (R2, R3.3) = task **W1 Actors**.
2. **Laeticia** (R6) and the nook `prefer`, `routine`, `fx` and `rare_rate` effects = task
   **W2 Laeticia and goods-lite**.
3. **Delights** (§5.8) = task **W3 Events, wind, weather, sound**, which also brings natural weather
   and positional sound.
4. **Front door** (R10): title, worlds screen with thumbnails, new, rename and delete, pause,
   settings with the profile, reduce motion, text input.
5. **Tour** (R10.5).
6. **Builder comforts** (R11): move with `Editor::abort()`, eyedropper, line placement, brush sizes,
   rectangles, grid, Tab overlay, new shortcuts and hints.
7. **Postcards** (R12): photo bar, frames, caption, folders, open folder.

Tests (unit): activity choice weights and filters for a fixed seed; cycle order; line-follow
spacing; petting cooldown; startle radius and `only_from`; A* costs, crossings and wild land;
schedule block at each clock value and with a pin; line rotation without repeats; move = one undo
step, cancelled move = none; line and rectangle tools as one undo step; brush skipping blocked
tiles; postcard file naming and collisions; world rename and duplicate rules.
Tests (scripted, with shots): title, worlds screen, new world with free build, rename, delete
with confirmation; settings sliders and reduce motion; pause; the full tour; cat napping on a bench,
ducks sleeping on the bank at night, bees entering the hive; petting a hen; Laeticia's day at four
clock times; move, eyedropper, line fence, rectangle erase, grid, Tab overlay; photo bar with each
frame and the caption, postcard count.

### Risks

| Risk | Mitigation |
|---|---|
| **Art volume** (478 must sprites) gates both tasks | The engine falls back everywhere (season looks, growth stages, missing anims fall back to idle, placeholders), so engine work never waits on art. Art order in §7.6. Rare visitors can land last. |
| **The 40×40 home region at 64×32 tiles is 2560 px wide at 1×**, larger than most windows | Zoom 1 still shows the opened corner (1280 px) comfortably at 1280×800; wild land is background and may be cut off at the edges. The camera margin must allow panning to every tile. A half-scale overview level (linear filtering, allowed by the projection contract) is the natural whole-region view, and later the fast-travel overview of the world; it is not needed in this batch. |
| Migration bugs could cost a player their world | Never overwrite the v1 file; rename only after the v2 file and thumbnail are written; fixture tests with real v1 saves. |
| Pacing feels slow or fast | All pacing numbers are in §12; scripted runs log time-to-page for the first 30 minutes so the orchestrator can tune once by hand. |
| Stem drift or clicks on unlock | One master sample counter, seek on unlock, fade from silence on bar lines; a unit test checks seek position arithmetic. |
| Condition cost grows with content | Debounced, event-driven evaluation; `near` early exit; bench gate. |
| Laeticia blocking the player's view or path | She never blocks placement (she steps aside); bubbles are small and fade; Quiet chatter setting. |
| Determinism of scripted runs with more randomness | Everything random uses the one seeded RNG; scripts pin clock and season where shots matter. |
| Text overflow at large UI scales | Wish text ≤ 80 characters, bubbles ≤ 52, tested at 200% in a scripted shot. |

---

## 10 Out of scope and cuts

| Cut or simplified | Why |
|---|---|
| Real-time seasons, growth or visitor arrivals | Would punish absence and invite clock changing; play time is fair and simple. |
| Automatic weather | Rain stays a toggle; a forced rainy session is a small punishment. |
| Snowy versions of every item; frozen water | Grass, trees and pines carry winter; a colour grade does the rest. Frozen water would break ducks, koi and the heron. |
| Saturation in the season grade | Not available cheaply on every SDL renderer; multiply plus sprite looks is enough. |
| Produce as an inventory or currency | Harvest is a gesture with a social effect, not a resource. |
| Friendship meters, named visitors, gifts | Too close to an economy; petting is its own reward. |
| Dialogue choices | One-line bubbles keep Laeticia light and the writing small. |
| Laeticia indoors, an interior view | A second renderer for one room; windows glowing says enough. |
| Elevation, cliffs or terraces inside the map | Changes the projection contract; not needed for this loop. |
| Season-specific music | Stems already make the music change; per-season variants would double the score. |
| ~~Positional (panned) sound~~ | No longer cut: designed in `living-world.md` §9 and built in task W3. |
| Multi-select, copy and paste, blueprints | Move, line and rectangle cover the common needs. |
| Custom key bindings | Not needed yet; every shortcut is listed in tooltips. |
| Localisation | Strings are centralised so it stays possible. |
| More rare visitors (a hare, a swan, bats) | Eight is the art budget; the data model takes more without engine work. |
| Egg collecting, footprints in snow, an umbrella walk | Nice-to-have art listed in §7.6; no rules depend on them. |
| The wider world map, cities, fast travel and the overview | Next batches; §2.1 scopes the saved state and §13 lists the hooks. |

---

## 11 Catalog v2 field reference

Everything in v1 keeps its meaning. New and changed fields:

**Top level**

| Field | Meaning |
|---|---|
| `version` | now `2` |
| `tile` | `{"w": 64, "h": 32}`; the projection constants in CLAUDE.md double (top vertex `sx = (tx − ty) × 32`, `sy = (tx + ty) × 16`) |
| `map` | `{"w": 40, "h": 40}`: the home region's size (today the whole map) |
| `seasons[]` | `id`, `name`, `days` (season length in days), `grade.mul` (RGB multiply), `ambience.day` / `.night` (files from `audio.ambience`), `fx.petal` / `.leaf` (multipliers), optional `rain_as: "snow"`, `line` |
| `land` | the home region's stages. `measure: "pages"`, `stages[]`: `id`, `name`, `rects` (inclusive `[x0, y0, x1, y1]` in home-region coordinates), `pages` (threshold), optional `line`, optional `reveal` `{terrain: [{id, rect}], items: [{id, x, y, v}]}` |
| `starter` | The home region of a new world: `terrain` (`{id, rect}`), `items` (`{id, x, y, v}`), `resident` (`[x, y]` bedroll spot). Replaces the tables in `starter.cpp`. |
| `progression` | `start` (`terrain`, `items`, `frames` unlocked in a new world); `legacy` (`terrain`, `items` unlocked for saves migrated from v1) |
| `frames[]` | `id`, `name` of postcard frames |
| `wishes[]` | R1.2 |
| `nooks[]` | R7.1 |
| `resident` | `id`, `name`, `voice` (list of sfx names; one is played per bubble), `blurb` (sketchbook front page), `lines` (context → list of lines; contexts in §5), `schedule`, `routines`, `interrupts` (her day as actor data, `living-world.md` §2.2 and §2.6) |

**`items[]`** (all optional)

| Field | Meaning |
|---|---|
| `tags` | list of tag names for conditions and reaction lines; the first tag picks Laeticia's `place_<tag>` line |
| `perch` | pixel height a critter sitting or perching `on` the item is lifted to |
| `deck` | a walkable item's floor in pixels above the ground (a footbridge's planks, stepping stones' tops; 0 to 64): whoever stands on it is drawn at that height and in the draw order over it, between a bridge's rails (`draw-order.md` §1.5 d) |
| `season_looks` | seasons for which the art supplies `@season` base sprites (R4.3) |
| `growth` | `{stages, seconds, harvest}`: number of growth stages, play seconds per stage, whether a ripe item can be picked |
| `click_sound` | sfx name played when the item is clicked with no tool |
| `slots` | named interaction points (seat, door, tend, feed, entrance, warm, lie, light…), `living-world.md` §2.3; items without them get implicit `on` and `beside` slots |

The cottage's `smoke_at` is now `[[20, -38], [-4, -30], [-20, -42], [4, -50]]` (64×32 density).

**`visitors[]`** (all optional; `needs` stays required and may be `{}`)

| Field | Meaning |
|---|---|
| `habitat` | adds `"shore"` (R3.3) |
| `seasons` | seasons in which it may visit (default all) |
| `hint` | vague sketchbook text before discovery |
| `rare` | `true` for rare visitors (R3) |
| `recipe` | condition; must also hold for the visitor to come (rare visitors use only this) |
| `clue` | exact recipe text revealed by a `clue` reward |
| `activities[]` | `id`, `anim` (or `"enter"`), `at` (selector, `{"here"}`, `{"bank"}`, `{"shore"}`, `{"resident"}`), `spot` (`on` or `beside`), `time`, `seasons`, `dur` `[min, max]` s, `weight`, `within` (tiles from the visitor's home anchor), `every` `[min, max]` s with `call_anim`, `needs_sitting` (seconds Laeticia must have sat) |
| `cycle` | activity ids run in order instead of weighted choice |
| `line` | ducks: followers swim in a line behind the leader |
| `home` | item id the visitor walks into when its time ends, and comes out of |
| `hide_in_rain` | hides (in its home item, or by fading) while it rains or snows |
| `startle` | `{radius, anim, only_from}` (R2.5) |
| `pet` | `{anim, sound}` (R2.4) |
| `underwater` | drawn below water items at 60% alpha with a cool tint |

**`audio`**

| Field | Meaning |
|---|---|
| `music` | now also lists every stem file; `music/day.ogg` and `music/night.ogg` are the title mixes |
| `ambience` | adds the five new beds |
| `sfx` | adds the 36 new effects |
| `stems` | `{"day": [...], "night": [...]}`, each `{id, file, when?}`; `when` is a condition, absent = always |
| `notes` | the ten note files in scale order (R8.3) |

---

## 12 Tunables

New entries for `tuning.hpp` (content numbers such as grades and growth seconds live in the catalog).

| Name | Value | Used by |
|---|---|---|
| `kMaxOpenWishes` | 3 | R1.4 |
| `kWishOfferGap` / `kWishOfferGapEmpty` | 75 s / 30 s | R1.4 |
| `kWishSnooze` | 600 s | R1.3 |
| `kWishGrantHold` | 1.5 s | R1.5 |
| `kWishAlreadyDoneDelay` | 3 s | R1.5 |
| `kConditionDebounce` | 0.25 s | §3.3 |
| `kRareDelayMin` / `Max` | 20 / 60 s | R3.2 |
| `kRareStayMin` / `Max`, `kRareAwayMin` / `Max` | 180 / 360 s, 120 / 240 s | R3.2 |
| `kPetCooldown`, `kPetSeconds`, `kPetHitInflate` | 4 s, 1.5 s, 4 px | R2.4 |
| `kStartleSpeed`, `kStartleCooldown` | 2.5×, 5 s | R2.5 |
| `kLineSpacing` | 0.7 tiles | R2.2 ducks |
| `kMidnight` | 0.75 | R4.1 |
| `kSeasonGradeGlide` | 0.25 of a cycle (midnight to the end of dawn); 2 s for a manual pin | R4.2 |
| `kRainGrowth`, `kWaterBoost` | 2×, 0.25 | R4.4 |
| `kPetalsPerSecondPerTree` | 0.03 | R4.6 |
| `kLandWaveStep`, `kLandStageGap` | 0.08 s per tile, 4 s | R5.3 |
| `kWildDim`, `kWildThicketChance` | 0.70, 0.8 | R5.2 |
| `kResidentSpeedPath` / `Other` | 1.1 / 0.9 tiles/s | R6.5 |
| `kResidentPathCost` | 1.0 path, 1.6 other | R6.5 |
| `kReactRadius`, `kReactChance`, `kReactCooldown` | 8 tiles, 0.3, 20 s | R6.3 |
| `kIdleLineMin` / `Max` | 60 / 120 s | R6.3 |
| `kBubbleBase`, `kBubblePerChar` | 2.5 s, 0.05 s | R6.6 |
| `kNookPulse`, `kNookLabel` | 1.6 s, 3.5 s | R7.2 |
| `kNookPreferWeight` | 4× | R7.4 |
| `kStemFadeBars` | 4 | R8.2 |
| `kNoteLevel` | 0.4 (about −8 dB) | R8.3 |
| `kNoteMinGap`, `kNotePhraseReset`, `kLineNoteStep` | 90 ms, 2.0 s, 45 ms | R8.3 |
| `kWaterfallLevel` | 0.5 | §5.8 |
| `kShootingStarMean`, `kFishJumpMean`, `kGustMin` / `Max` | 50 s, 90 s, 120 / 240 s | §5.8 |
| `kThumbnailInterval` | 300 s | R10.9 |
| `kPhotoBarFade` | 2 s | R12.1 |
| `kReduceMotionParticles` | 0.3 | R10.8 |

---

## 13 Hooks for the wider world

Not designed here, only kept open. Nothing below is in this batch's tasks.

- **The road and the gate** (R5.6) are the seam. Later the gate becomes the home region's first
  fast-travel point and the road continues into the world. Laeticia gets a `road` line context
  used near the gate at dusk, in the spirit of "Someone used to walk that road every market day."
  and "Where do you suppose it ends up?" (examples of the voice, to be written with the cities).
- **Laeticia stays home.** She does not travel; she sees you off at the gate and greets you on
  return with `greet` lines. This keeps her routine, pathing and wishes inside the home region.
- **Sketchbook per region.** Today's tabs become the Home section; each region you reach later adds
  its own tab (who was seen there, its sights). Visitors already have one global "seen" list, so a
  region tab is a filter plus that region's own entries. Pages from every region count toward the
  same total, so travelling also helps the home region open (harmless once all its stages are open).
- **Travel wishes.** The wish model already fits: a `giver` can later be someone met elsewhere, and
  two condition terms would cover travel without changing existing ones: `{"visited": "<region>"}`
  and a `region` key on `count` / `near` / `visitor` (§2.1). Laeticia's natural travel wish asks for
  a postcard of a far place (a `{"postcard": "<region>"}` term), and its reward can be a piece in
  that place's style for the home region.
- **Travellers on the road.** A road visitor type that passes along y = 0 outside the wall, never
  entering the home region, would make the edge feel lived-in before the world exists.
- **Global time.** Clock, weather and the calendar are already global (§2.1), so a city sees the same
  season and sky as home. Postcard captions add the region's name.
- **Saved state.** The world save gains `regions_visited` and nothing else unless a later batch lets
  players change other regions; home coordinates stay home-relative (§2.1).
