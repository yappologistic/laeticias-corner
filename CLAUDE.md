# Laeticia's Corner

A cozy isometric pixel-art diorama builder. You are handed a small floating corner of land and
decorate it: paint ground, plant trees and flowers, place cottages and garden pieces. There is no
score, money, timers or fail state. The hook is that the diorama is alive: what you build decides
who visits (ducks find ponds, a cat moves into the cottage, fireflies come out at night).

Everything in this game is original: its own art, palette, UI, names, sounds and music.

## Non-negotiables

- **Small, fast, correct.** Prefer the simplest design that is right. No speculative abstractions,
  no dead code, no TODO debt, no copy-paste. If a feature cannot be finished properly, leave it out.
- **Read the docs before using an API.** SDL3 differs from SDL2 in many places; check the headers
  in `/usr/include/SDL3` and the SDL3 wiki/migration guide instead of relying on memory.
- **Never touch the user's desktop.** All automated runs are headless: `SDL_VIDEODRIVER=offscreen`
  (or `dummy`) and `SDL_AUDIODRIVER=dummy`. Never open a visible window, never play sound through
  the speakers, never grab input. Tests write only inside the build tree or a temp dir, and never
  read or write the real save location.
- **Everything is tested.** Logic has unit tests; rendering, UI and input flows are covered by
  scripted headless runs that produce screenshots. A change is done when the build is warning-free
  and `ctest` passes under both the release and the sanitizer presets.
- **Stay in your lane.** Edit only the paths you own (see Ownership). If you need a change in
  someone else's area or in a contract file, report it instead of making it.

## Machine courtesy

The owner uses this computer while agents work, and disk space is limited.

- At most 4 parallel build jobs (`cmake --build … -j4`, `ctest -j2`) and at most two headless game
  processes at once. Prefix long CPU-heavy commands with `nice -n 19`.
- Build trees: only `build/release` and `build/asan` are kept. Anything else (extra presets, QA
  copies, worktrees) lives under `out/` and is deleted by whoever created it before they finish.
- Keep `out/` small: delete scratch renders, intermediate audio, old screenshots and saves when
  done. Never write large files outside the project. No downloads over a few MB without a reason.
- One agent at a time edits `src/` and `tests/` (the engine lane). Art (`tools/artgen`, atlases),
  audio (`tools/audiogen`, `assets/audio`), world building (`tools/worldgen`, `assets/world`,
  `assets/regions`, one agent per layer) and read-only work (QA, research, design docs) run
  beside it.
- Worldgen previews go to `out/worldgen/` and are deleted when done.

## Stack

- C++23, CMake (presets) + Ninja, GCC or Clang. One executable: `laeticias-corner`.
- SDL3 ≥ 3.4 (system package) for window, 2D GPU renderer, input, audio, PNG load/save.
- nlohmann_json (system package) for the catalog, atlas manifest and save files.
- doctest for tests. `stb_truetype` (UI text) and `stb_vorbis` (music/ambience decoding) vendored
  under `third_party/` with their licence text. Nothing else without a written justification.
- Tools (asset generators) are Python 3 under `tools/`, deterministic (fixed seeds), with pinned
  `requirements.txt` and a local `.venv`. Generated assets are committed; tools must reproduce them.

## Layout and ownership

| Path | Contents | Owner |
|---|---|---|
| `src/core/` | Pure game logic, no SDL: world grid, catalog, placement, undo/redo, save, visitors, clock | engine |
| `src/render/`, `src/ui/`, `src/audio/`, `src/app/` | SDL-facing code | engine |
| `tests/`, `CMakeLists.txt`, `CMakePresets.json`, `cmake/`, `third_party/`, `.clang-*` | Build, tests, tooling config | engine |
| `tools/artgen/`, `assets/atlas.png`, `assets/atlas.json`, `assets/atlas/` | Sprite generator and its output: the home page, set pages, manifests, geometry | art |
| `tools/worldgen/worldgen/`, `tools/worldgen/plan/`, `tools/worldgen/fixtures/`, `tools/worldgen/build.sh`, `assets/world/world.json`, `assets/world/layers/base.*`, `assets/world/overview.png` | World authoring tool, world plan, base layer, overview, test world | worldgen core |
| `tools/worldgen/regions/<layer>/`, `assets/world/layers/<layer>.*`, `assets/regions/<region>.json` for the regions in that layer | One authored place: layout, graph, life and text | the builder of that layer (one agent per layer) |
| `assets/sets/<set>/catalog.json` | Set content contracts | orchestrator, or the agent whose brief says so |
| `docs/design/sets/` | Draft set catalogs | design |
| `tools/audiogen/`, `assets/audio/` | Audio generator and its output | audio |
| `assets/fonts/` | Bundled UI fonts + licences | engine |
| `docs/design/` | Game design specs: rules, content tables, art and audio lists for each batch | design |
| `assets/catalog.json`, `CLAUDE.md` | Contracts | orchestrator, or the agent whose brief says so |

`src/core` must not include SDL headers. Dependencies point one way: `app → ui/render/audio → core`.

## Code standards

- `-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror` on project code. No warnings suppressed
  without a comment saying why. `.clang-format` and `.clang-tidy` are part of the repo; code is
  formatted before every commit.
- RAII everywhere; no raw `new`/`delete`, no owning raw pointers. SDL handles wrapped in
  `std::unique_ptr` with custom deleters. Check every SDL call that can fail.
- Value types and plain structs first; no inheritance where a `struct` + function does the job.
  No singletons or mutable globals. `const` and `[[nodiscard]]` where they help.
- Fixed-timestep simulation (60 Hz) decoupled from rendering; one seed owned by the game, from
  which independent streams (per actor, per event, per chunk) may be derived, so scripted runs are
  reproducible.
- No per-frame heap allocation in the steady state. One texture atlas, sprites batched; draw calls
  stay in the low tens. Frame budget: under 2 ms CPU for update + draw submission with a full map.
- Comments explain *why*, not what. Public headers get a one-line purpose comment.
- All user-visible strings and tunable numbers live in one place each, not scattered literals
  (interface text in `src/ui/strings.hpp`, simulation numbers in `src/core/tuning.hpp`, interface
  spacing in `src/ui/theme.hpp`, content in the catalog); a region's text lives in its file
  under `assets/regions/`.

## Git

- Branch `main`, local only. Small logical commits in Conventional Commits style
  (`feat(render): …`, `fix(core): …`, `test: …`, `chore: …`, `assets: …`).
- Several agents share this checkout. Stage and commit **only your own paths**
  (`git add <paths>` then `git commit -m … -- <paths>`); if `index.lock` is busy, wait and retry.
  Never `git add -A`, never rewrite history, never commit build output, virtualenvs or scratch files.
- The working tree is shared and other agents have uncommitted work in it at all times. Never run
  `git stash`, `git reset`, `git checkout -- <path>`, `git restore`, `git clean` or anything else that
  changes or hides files you do not own. To compare against an older version, use
  `git worktree add out/<name> <commit>` and delete it afterwards.

## Content contract

`assets/catalog.json` is the single source of truth for what exists: terrain, items, visitors and
audio files. The engine loads it at runtime; the generators read it to know what to produce.

It is `"version": 2`; its fields are documented in `docs/design/living-corner.md` §11 and
validated by the engine, which names the offending entry. Besides `terrain`, `categories`,
`items`, `visitors` and `audio` it holds the progress loop as data: `seasons`, `land` (stages
by sketchbook pages, their reveals, the `gate`), `starter`, `progression` (`start` and `legacy`
unlocks), `frames`, `wishes`, `nooks` and `resident` (Laeticia: name, lines, her day). Wish
goals and gates, nook recipes, rare-visitor recipes and stem conditions share one condition
vocabulary (`living-corner.md` §3). Item fields added by the engine round: `sheds` (`"leaves"`
or `"blossom"`: what a tree drops), `shelter` (beds within this many tiles grow when the season
rests them), and `perch` may list one height per variant; a season may set `growth` (0: beds
rest). `tile.level`, `sets`, `world` and terrain `faces`/`under` are for the world
(`docs/design/world-tech.md` §6.2) and ignored by the engine until it builds it.

### Projection

2:1 isometric. The tile cell size comes from `tile` in the catalog (64×32 px at 1×; nothing in
the engine or generators may hard-code it). With half-width `hw = tile.w / 2` and half-height
`hh = tile.h / 2`, the top vertex of tile `(tx, ty)` is at `sx = (tx - ty) * hw`,
`sy = (tx + ty) * hh`; the rasterised ground diamond spans `x ∈ [sx-hw+1, sx+hw-1)`,
`y ∈ [sy, sy+tile.h)` (rows 2, 6, … wide, mirrored) so tiles meet with no gap or overlap.
`+x` runs down-right, `+y` runs down-left. Neighbour bits for masks:
N `(tx, ty-1)` = 1, E `(tx+1, ty)` = 2, S `(tx, ty+1)` = 4, W `(tx-1, ty)` = 8.
The world is drawn at an integer scale with nearest-neighbour sampling; a half-scale overview
level may use linear filtering. Map size comes from `map` in the catalog.

### Atlas (`assets/atlas.png` + `assets/atlas.json`)

```json
{ "version": 1, "image": "atlas.png",
  "sprites": { "<key>": { "x": 0, "y": 0, "w": 32, "h": 16, "ox": 16, "oy": 0 } } }
```

`(ox, oy)` is the pixel inside the sprite that sits on the anchor. For terrain and items the anchor
is the **top vertex of the footprint's origin tile** (smallest `tx`, `ty`) at ground level; for
visitors and effects it is the ground contact point. Keys:

| Key | Meaning |
|---|---|
| `terrain/<id>/v<n>` | Base terrain variant `n` (full diamond) |
| `terrain/<id>/m<mask>/f<frame>` | Overlay terrain: `mask` = bits of neighbours of the **same** terrain; edges facing other terrain are rounded off to transparent so the base shows through. `f0` only unless animated |
| `item/<id>/<layer>/<variant>/f<frame>` | `layer` ∈ `base`, `shadow`, `glow`. `variant` is `r<k>` for `rotate`/`variant` layouts (`k < count`) and `m<mask>` for `connect` layouts (bits of same-item neighbours) |
| `critter/<id>/<anim>/f<frame>` | `anim` ∈ `move_front`, `move_back`, `idle_front`, `idle_back`. `front` faces `+x` (down-right), `back` faces `-y` (up-right); the engine mirrors for the other two directions |
| `fx/<name>/f<frame>` | `smoke`, `ripple`, `sparkle`, `raindrop`, `leaf` |
| `edge/cliff_se`, `edge/cliff_sw` | One-tile-wide cliff face drawn under the map's south-east / south-west rim |
| `ui/tile_ok`, `ui/tile_bad` | Tile highlight diamonds for the placement cursor |
| `<any key>@<season>` | Optional look of any sprite for one season; the plain key is the fallback |
| `item/<id>/base/<variant>/g<stage>/f<frame>` | Growth stage of an item with `growth` (looked up: stage and season, stage, season, plain) |
| `critter/<id>/<anim>/f<frame>` (plain) | Extra animations without `_front`/`_back` (front frames, mirrored) |
| `critter/laeticia/…`, `ui/portrait/laeticia` | The resident on the critter scheme; her 28×28 portrait for wish cards |
| `wild/thicket/v<n>` | Brambles on wild land, anchored like terrain |
| `edge/fall_se/f<n>`, `edge/fall_sw/f<n>` | Water falling over the rim, anchored and drawn like the cliff faces |
| `ui/tile_area`, `ui/tile_grid` | Soft white diamond (nook areas, tinted) and a 1-px outline |
| `fx/<name>/f<frame>` (more) | also `clear`, `petal`, `snowflake`, `produce` (frame k: the crop of bed variant k), `heart`, `moth`, `fish_jump`, `star_streak`, `apple`, `mist`, `zzz` |
| `sky/rainbow`, `title/logo`, `frame/<id>/<tl…br, plate>` | Sky, logotype and postcard frames (anchors at the top-left pixel where noted in the art report) |
| `item/<id>/<layer>/r<k>/p<i>/f<n>` | Piece `i` of a split item (`base` only) |
| `item/<id>/<state>/<variant>/f<n>` | A slot state drawn instead of `base` |
| `edge/<material>_<se\|sw>/v<n>` (`/top`, `/v<n>/f<k>`) | One level of face under a tile edge, a cap band, an animated face |
| `terrain/world.sea/foam/m<mask>/f<k>`, `terrain/world.river/flow_<n\|e>/f<k>` | Shore foam (mask = land neighbours), river flow (mirrored for w, s) |
| `walker/<kind>/v<k>/<anim>_<front\|back>/f<n>` (`/glow/f<n>`) | Anonymous people on the shared rig |
| `figure/<id>/<anim>_<front\|back>/f<n>` | Named people |
| `ship/<kind>/v<k>/<anim>_<front\|back>/f<n>`, `cart/…` | Ships, carts with their animals |
| `goods/<id>`, `goods/<id>/s<1-3>` | Carried goods, slot stacks |
| `backdrop/<id>/<day\|night\|winter>/v<n>` | Strip segments behind the north and east world edges |
| `weather/<kind>_v<n>`, `ui/marker_<icon>` | Weather sprites; overview markers |

- `rotate`: `r<k>` is the model turned `k × 90°` clockwise seen from above; footprint `[w, h]`
  becomes `[h, w]` for odd `k`. `variant`: `r<k>` are different looks of the same thing.
- The manifest is authoritative for frame counts; the catalog gives `fps`.
- `base` is lit for neutral daylight, sun from the upper-left. `shadow` is the cast shadow on the
  ground only (black with alpha). `glow` holds only the emissive pixels (windows, lamps, fire) and
  is drawn additively at dusk and night. Day/night grading is done by the engine, not baked.
- The `shadow` layer is optional: flat things (lily pads, ground decals) have none.
- Shadows are composited as one layer (overlapping shadows must not double-darken).
- Emissive things are drawn after night grading: item `glow` layers (palette colour, halo strength
  in alpha, additive) and visitors marked `"glow": true` in the catalog.
- `smoke_at` on an item lists, per `r<k>`, the pixel offset from the anchor to the chimney top.
- Flying visitors are anchored at the bottom of the body; the engine adds altitude. `edge/*`
  sprites anchor at the rim tile's top vertex. `fx/raindrop`: `f0` is the falling streak, later
  frames are the splash.
- A missing sprite must never crash: the engine draws an obvious placeholder and logs once.

### Audio (`assets/audio/`)

Files are listed under `audio` in the catalog. Everything under `music/` and `amb/` is a seamless
whole-file loop, Ogg Vorbis, 44.1 kHz stereo, true peak ≤ −1 dB; music sits at about −18 LUFS
integrated and ambience beds at −21 to −23. Effects: WAV, 44.1 kHz, 16-bit mono, peak ≤ −3 dB,
balanced against each other by their loudest 100 ms, no clicks at the start or end. A visitor's
`voice` value `<v>` plays `sfx/<v>.wav`. The engine crossfades `day`/`night` music and ambience with
the clock, adds slight random pitch to placement sounds, and treats a missing file as silence.

Music in play is `audio.stems` (`day` and `night`, five stems each, all exactly 4 704 000 samples):
every stem plays from one master sample position; one whose `when` condition becomes true joins
on the next bar line (147 000 samples) and fades in over four bars. `music/day.ogg` and
`music/night.ogg` are the full mixes for the title screen. `audio.notes` are the ten tuned
placement notes in scale order, played without pitch jitter. Each season names its day and night
ambience beds (`seasons[].ambience`).

### Sets, ids and the world

Design and formats: `docs/design/world-tech.md`. In short:

- Content outside the home set lives in **sets** (`world`, `rome`, `athens`, `parsa`), each with a
  catalog `assets/sets/<set>/catalog.json` (same schema as `assets/catalog.json` plus `actors`,
  `goods` and `art`). `assets/catalog.json` lists them in `sets`. Every id outside the home set is
  `<set>.<name>`; home ids have no dot. Ids are unique across all catalogs.
- A set's art is on pages `assets/atlas/<set>.<n>.png` + `.json` (today's manifest schema, at most
  4096 × 4096 each) and its geometry in `assets/atlas/<set>.geom.json` (pieces, walk tiles, slot
  spots, emitters, carry points, per rendered rotation). Catalog slots give behaviour, geometry
  files give positions; both must cover each other.
- Footprints over 8 × 8, or with walk tiles, are split into rectangular **pieces** of at most
  8 × 8 tiles (`…/r<k>/p<i>/f<n>`), depth-sorted as items. Walk tiles carry nothing lower than
  `1.5 × tile.h` px above their floor. Landmarks are modelled in grid axes and use `r0`.
- Elevation: integer levels 0..15, `tile.level` px each; faces `edge/<material>_<se|sw>/v<n>`, one
  level tall, stacked. Stairs and ramps are items with `rise` and `axis`, footprint at the lower level.
- The world is `assets/world/world.json` plus layer files (`layers/<id>.lcw`, binary, composed in
  order) and graphs (`layers/<id>.graph.json`); region life, theme and text are
  `assets/regions/<region>.json`. All are generated or validated by `tools/worldgen`.

## Game rules

The design is `docs/design/living-corner.md`; this is what the engine does today.

- The home region is 40×40 tiles in five land stages. A new world opens on the front 20×20 corner
  (the catalog's starter scene); the rest is wild (dimmed brambles: no building, painting or
  walking). Stages open at 4, 9, 14 and 20 sketchbook pages (visitors seen plus nooks found),
  clearing in a wave and revealing their terrain and pieces; the last brings the road, wall and
  gate.
- Building: ground tools paint by click-drag; items occupy their footprint, one per tile, `on`
  says land, water or either, and painting the wrong ground under an item is refused. Build drawer
  → pick → ghost (valid/invalid tint) → click, drag for 1×1 pieces; `R` rotates or cycles looks;
  Remove deletes; everything is undoable (`Ctrl+Z` / `Ctrl+Shift+Z`), drags as one step. The
  drawer lists only unlocked pieces (lock tile "+N" while a tab has more; dots on new ones).
- Wishes: the first offerable wish in catalog order is offered after 30 s of play with none open,
  75 s otherwise, at most three, from Laeticia (not at night) or a present visitor. A goal that
  holds for 1.5 s grants the wish and its unlocks, frame or clue; "Not now" snoozes it for 600 s.
  Nothing is ever taken away.
- Visitors come by `needs` and season; rare ones by their recipe after it holds 20–60 s, staying
  180–360 s. Nooks are recognised from their recipes and kept in the sketchbook (`J`), which also
  holds the wishes and the visitors (rarer ones as silhouettes with hints).
- Time: the clock cycles day → dusk → night → dawn and can be pinned; a calendar day begins at
  midnight while it runs, three days a season; the season can be pinned from the title card.
  Seasons change looks, grade, ambience, falling things and visitors; winter rain is snow. Veggie
  beds grow through four stages in play time (faster in rain, resting in winter unless near a
  greenhouse) and ripe ones are picked with an empty hand.
- Music grows in stems with progress; each placement also plays a tuned note of a little phrase.
- Camera: drag or WASD/arrows to pan, wheel or `+`/`-` to zoom in steps toward the cursor, `Home`
  recentres on the open land. The world autosaves (atomic write) and reopens where it was left.
  Photo mode hides the UI and saves a PNG.
- UI is quiet glass: title card (world, phase, season day; calendar), build button and drawer,
  docks of round controls, wish tray, sketchbook, ribbons, hints and tooltips. It is drawn at
  native resolution (the world stays pixel-scaled), scales with DPI, and every state has
  hover/pressed/disabled feedback.

## Running

Presets: `release`, `asan` (Debug + ASan/UBSan) with GCC; `clang-release`, `clang-asan` with Clang.
Build output goes to `build/<preset>/`.

```sh
cmake --preset release && cmake --build --preset release -j4   # configure + build
ctest --preset release            # unit, coverage, scripted runs, audio capture, GPU budget bench
ctest --preset release-full       # also the "heavy" label: large window sizes, 1024x512 bench
cmake --preset asan && cmake --build --preset asan -j4 && ctest --preset asan
clang-format -i src/*/*.[ch]pp tests/*.[ch]pp
run-clang-tidy -p <clang build dir> "src/.*"     # any clang configure under out/, then delete it
```

The default presets run two tests at a time and skip the `heavy` label (the software renderer is
slow at big sizes); they finish in about two minutes. Coverage is strict: missing art or audio
fails (shadow layers are optional). The `bench` tests use the windowless `opengl` driver, assert
the frame budget, and are skipped (exit 77) where no GPU renderer can be created.

Headless runs (never a visible window or sound; `--script`, `--bench` and `--audio-out` imply
`--headless`):

```sh
B=build/release/laeticias-corner
$B --headless --size 1280x800 --save-dir /tmp/lc --frames 300           # just run
$B --script tests/scripts/visitors.lcs --save-dir /tmp/lc               # scripted, shots to cwd
$B --script tests/scripts/audio_capture.lcs --audio-out /tmp/lc/mix.wav --save-dir /tmp/lc
$B --bench --renderer opengl --size 1920x1080 --save-dir /tmp/lc-bench  # 40x40 timings
$B --bench --renderer opengl --map 1024x512 --density 0.5 --budget-ms 2 --save-dir /tmp/lc-bench
```

- Script language: documented at the top of `src/app/script.hpp`; scripted tests live in
  `tests/scripts/` and write screenshots to `build/<preset>/shots/`. Besides input it can hold
  keys and buttons (`press`, `keydown` ...), set state (clock, season, day, land stage, unlocks,
  play time and growth stepped forward) and assert state and image statistics. The first ten
  minutes of a new world run end to end in `first_ten.lcs`.
- Save format: version 3, documented at the top of `src/core/save.hpp` (versioned, tolerant;
  versions 1 and 2 migrate on launch). A save directory holds `profile.json`,
  `worlds/<slug>/world.json` with `thumb.png`, and `corner.v1.json` after a migration.
- Saves go to `--save-dir`, else `$LAETICIA_SAVE_DIR`, else SDL's pref path. Assets come from
  `--assets`, `$LAETICIA_ASSETS_DIR`, `<exe dir>/assets`, then the source tree.
- Headless uses the `dummy` video driver with the software renderer (reproducible screenshots);
  `--renderer opengl` switches to the `offscreen` driver (EGL, still windowless) for GPU timings.
  Without `--size` a headless window is 1280x800.
- `--bench` fills the map (dense around the centre, sparse elsewhere), times every condition of
  the progress loop at once, runs at night in the rain with the drawer and sketchbook open, and
  reports update/draw times (average, 95th percentile, worst) at 1x and at the half-scale
  overview, plus memory; `--budget-ms` makes it exit 3 when a frame is over that budget or the
  conditions take over 1 ms.
- Interactive play: `$B` with no flags. The window opens on a share of the display it is on and
  remembers its size, place and fullscreen state (`window.json` beside the save). Do not run it
  from automation.

Asset regeneration (owned by the art, audio and world agents):

```sh
tools/artgen/build.sh                    # the home atlas
tools/artgen/build.sh --set parsa        # a set's pages and geometry
tools/audiogen/generate.sh
tools/worldgen/build.sh parsa            # compile and validate one layer (previews: --preview parsa)
tools/worldgen/build.sh --check          # validate the composed world
```
