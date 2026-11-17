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
| `tools/artgen/`, `assets/atlas.png`, `assets/atlas.json` | Sprite generator and its output | art |
| `tools/audiogen/`, `assets/audio/` | Audio generator and its output | audio |
| `assets/fonts/` | Bundled UI fonts + licences | engine |
| `assets/catalog.json`, `CLAUDE.md` | Contracts | orchestrator only |

`src/core` must not include SDL headers. Dependencies point one way: `app → ui/render/audio → core`.

## Code standards

- `-Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror` on project code. No warnings suppressed
  without a comment saying why. `.clang-format` and `.clang-tidy` are part of the repo; code is
  formatted before every commit.
- RAII everywhere; no raw `new`/`delete`, no owning raw pointers. SDL handles wrapped in
  `std::unique_ptr` with custom deleters. Check every SDL call that can fail.
- Value types and plain structs first; no inheritance where a `struct` + function does the job.
  No singletons or mutable globals. `const` and `[[nodiscard]]` where they help.
- Fixed-timestep simulation (60 Hz) decoupled from rendering; one seeded RNG owned by the game so
  scripted runs are reproducible.
- No per-frame heap allocation in the steady state. One texture atlas, sprites batched; draw calls
  stay in the low tens. Frame budget: under 2 ms CPU for update + draw submission with a full map.
- Comments explain *why*, not what. Public headers get a one-line purpose comment.
- All user-visible strings and tunable numbers live in one place each, not scattered literals.

## Git

- Branch `main`, local only. Small logical commits in Conventional Commits style
  (`feat(render): …`, `fix(core): …`, `test: …`, `chore: …`, `assets: …`).
- Several agents share this checkout. Stage and commit **only your own paths**
  (`git add <paths>` then `git commit -m … -- <paths>`); if `index.lock` is busy, wait and retry.
  Never `git add -A`, never rewrite history, never commit build output, virtualenvs or scratch files.

## Content contract

`assets/catalog.json` is the single source of truth for what exists: terrain, items, visitors and
audio files. The engine loads it at runtime; the generators read it to know what to produce.

### Projection

2:1 isometric. Tile diamond is 32×16 px at 1×. The top vertex of tile `(tx, ty)` is at
`sx = (tx - ty) * 16`, `sy = (tx + ty) * 8`; the diamond spans `x ∈ [sx-16, sx+16)`,
`y ∈ [sy, sy+16)`. `+x` runs down-right, `+y` runs down-left. Neighbour bits for masks:
N `(tx, ty-1)` = 1, E `(tx+1, ty)` = 2, S `(tx, ty+1)` = 4, W `(tx-1, ty)` = 8.
The world is always drawn at an integer scale with nearest-neighbour sampling.

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

- `rotate`: `r<k>` is the model turned `k × 90°` clockwise seen from above; footprint `[w, h]`
  becomes `[h, w]` for odd `k`. `variant`: `r<k>` are different looks of the same thing.
- The manifest is authoritative for frame counts; the catalog gives `fps`.
- `base` is lit for neutral daylight, sun from the upper-left. `shadow` is the cast shadow on the
  ground only (black with alpha). `glow` holds only the emissive pixels (windows, lamps, fire) and
  is drawn additively at dusk and night. Day/night grading is done by the engine, not baked.
- A missing sprite must never crash: the engine draws an obvious placeholder and logs once.

### Audio (`assets/audio/`)

Files are listed under `audio` in the catalog. Music and ambience: seamless loops, Ogg Vorbis,
44.1 kHz stereo, about −18 LUFS, true peak ≤ −1 dB. Effects: WAV, 44.1 kHz, 16-bit mono, peak
≤ −3 dB, no clicks at the start or end. The engine crossfades `day`/`night` music and ambience with
the clock, adds slight random pitch to placement sounds, and treats a missing file as silence.

## Game rules (v0)

- Map is 20×20 tiles. Ground tools paint terrain by click-drag. Items occupy their footprint; one
  item per tile; `on` says whether they need land, water or either. Painting water under a land
  item (or land under a water item) is refused.
- Build menu → pick → ghost follows the cursor (valid/invalid tint) → click places, drag places
  repeatedly for 1×1 pieces. `R` rotates / cycles variants. Remove tool deletes. Everything is
  undoable (`Ctrl+Z` / `Ctrl+Shift+Z`), including drags as one step.
- Camera: drag or WASD/arrows to pan, wheel or `+`/`-` to zoom in integer steps toward the cursor,
  `Home` recentres. Clock cycles day → dusk → night → dawn and can be pinned. Rain can be toggled.
- Visitors appear and leave according to `visitors[].needs`; a journal lists who has been seen.
- The corner autosaves (atomic write) and restores on launch. Photo mode hides the UI and saves a PNG.
- UI is minimal and quiet: a title, a build button and drawer, a small dock of round controls,
  contextual hint text, tooltips with shortcuts. It is drawn at native resolution (the world stays
  pixel-scaled), scales with DPI, and every state has hover/pressed/disabled feedback.

## Running

Fill in by the engine owner once presets exist: configure, build, test, sanitizer run, headless
scripted run with screenshots, asset regeneration commands.
