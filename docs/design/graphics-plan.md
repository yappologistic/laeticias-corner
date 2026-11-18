# The graphics plan

One plan for how Laeticia's Corner comes to look and move as the owner asks ("Where this is going"
in `CLAUDE.md`). It brings together five studies that overlap and sometimes disagree:
`docs/design/look.md` (art direction, pass plan, the `gpu` driver probe),
`out/reports/graphics-rnd.md` with branch `t3/pixel-art-rendering-rd` (the working prototype),
`out/reports/depth-research.md` with branch `t3/isometric-depth-rendering` (offline depth studies),
`out/reports/quality-research.md` with `docs/design/quality-bar.md` (the standard and the golden
scenes), and `docs/design/seasons.md`. Where this plan and an earlier document differ, this plan
wins for rendering and art data; `quality-bar.md` still wins for acceptance numbers.

Contents: 0 one page · 1 the target · 2 the data contract · 3 the render pipeline · 4 how the
branches come together · 5 the work plan · 6 risks and the owner's decisions.

---

## 0. On one page

**What we build.** The R&D prototype's look (relit art, height-field sun shadows, layered water with
reflections, clouds, wind, bloom, lights at every zoom), finished with the depth study's best four
passes (sun through the back of the view, ambient occlusion at two scales, depth darkening, height
fog) and kept as pixel art by the quality research's rule: light first, then back onto each
material's own colour ramp, with a dither anchored to the world. It runs on SDL's `gpu` render
driver; today's renderers stay as the Classic fallback.

**The one big change to the prototypes.** The R&D branch drew every sprite twice (colour, then a
data page of normal and height). That cost one extra 64 MiB texture per atlas page (+318 MiB at
1440p) and up to 1.35 ms of CPU (the second sprite pass), the two reasons it missed the budget. Here
the generator writes **one packed page per atlas page** for the shader path: each pixel holds its
material ramp and step (which *is* its colour, because every pixel is a palette colour), its
normal, its height, a baked-self-shadow bit and a snow bit. The engine draws the scene **once**,
into one target, and decodes the colour when it lights it. On the shader path the packed page
replaces the colour page, so texture memory does not grow; with shadow sprites moved to small pages
of their own (needed only by Classic and Low), the worst resident set **falls** from 336 to 272 MiB.

**Order.** `t3/integrate-game-world` merges into `main` first (as planned). Neither R&D branch is
merged: both pin old art and world data, and their generator edits collide with the art lane's
twelve-frame walks (§4). Their code is ported, task by task, onto branches from `main`.

**The first five tasks** (§5 has all of them):

| # | Task | Lane | What the owner sees |
|---|---|---|---|
| E1 | The look's foundation in the game: `gpu` driver in the window with the fallback chain, Look and Clouds settings, region grade from `theme.look`, bloom, warm light pools with flicker, wind sway world-wide, smooth camera composite | engine | Every place graded with a warm key and cool shade instead of a brown or orange multiply; lamps glow with soft halos and warm pools; trees, reeds and banners bend in one wind with gusts rolling through, in every region |
| W1 | Lit nights: window glow, door torches, braziers and bridge lamps placed in Rome, Athens and Pārsa (with art A2 for the glow layers) | world + art | Cities at night lit from inside, warm against a moonlit blue, visible from every zoom |
| A1 | The data contract in the generator: packed pages, shadow pages at half size, ramp table with classes; every set rebuilt | art | (enables everything below; soft half-size shadows on the Classic path) |
| E2 | Water and clouds: layered water everywhere from the tile water field (bands, flow, shore line, foam, sparkles, rain rings, sky and clouds in it), the cloud deck and its shadows at quarter resolution, the Clouds toggle | engine | Water that moves like water at every zoom, sea beyond the edges; clouds drifting with their shadows sweeping over roofs and sea |
| E3 | Golden harness and metric panel, seasonal day length | engine | (every later change judged on the twelve golden scenes; the owner approves sheets, not promises) |

E1 and W1 run in parallel; A1 runs beside E1 and E2; E4 (relight on the packed pages, sun path,
ramp snap) follows E3 and A1 and is the step that makes light behave like light.

**Cost per tier**, whole frame at 1440p on the test machine's mid-range laptop GPU, busiest city
view with crowds, weather and UI (estimates built on the R&D measurements, §3.5):

| Tier | Average | 99th percentile (target) | Headroom to 8.3 ms | Texture memory (Rome in view) |
|---|---|---|---|---|
| Classic | 1.6 ms | ≤ 3 ms | > 5 ms | ≈ 420 MiB |
| Low | 2.7 ms | ≤ 5 ms | > 3 ms | ≈ 490 MiB |
| Medium | 3.4 ms | ≤ 6 ms | > 2 ms | ≈ 485 MiB |
| High | 4.2 ms | ≤ 6.5 ms | ≈ 1.8 ms | ≈ 500 MiB |

**The owner decides** (§6.2): how dark night may go (recommended: unlit median luma 28–38, never a
blue film, every inhabited view lit); whether buildings in front of the pointer fade (recommended:
yes, a dithered fade, everywhere; true roof-off interiors only for three buildings, later); whether
tall things lean slightly as the camera pans (recommended: yes, small, after watching
`out/reports/shots/depth/clips/forum_pan_compare.mp4`).

---

## 1. The target

### 1.1 The look in words

**A city by day** (the Forum at 10:00, G4). A sunlit miniature at a calm mid key: lit travertine,
marble and plaster keep their material's warmth (cream, honey, white-gold), never grey; shade is the
sky's colour (blue-violet, lighter than black by a lot) and holds most of the frame's cool pixels.
Shadows are long enough to fall across the square and fold over steps, soft at their far ends,
always touching their casters. The darkest values are in enclosed space: arcades, eaves, alleys, wall
feet, under every figure. Roofs stand clear of the street behind them by a breath of darkness.
Accents (cinnabar, lapis, gilt, banners, clothes) are the only strongly saturated colour. Nothing is
pale, nothing is one hue, and every gradient is made of the art's own ramp steps and dither.

**A city at dusk** (the Tiber island at 19:30, G5). The low sun lays copper bands across whatever it
still reaches; everything else falls into violet shade. Lamps are being lit one by one; each makes a
warm pool that stops at walls. The river holds the dusk sky, the bridges and the lamps as wobbling
streaks. Dusk is gold and violet, not an orange wash: no 30° hue band holds more than 70 % of the
frame (`quality-bar.md` §4.4).

**A city at night** (the Agora at 22:00, G7). Dark and readable: moonlit planes in cool blue-grey
with their value structure intact (unlit IQR ≥ 12); warm light only where there is a source (windows,
doors, torches, braziers), 2–8 % of the view, with bloom on the sources and pools on the ground.
Every light stays lit at every zoom down to the overview, where towns sparkle.

**Water** (G2, G5, G10, M3). Still pixel art that never stops moving: a few hard depth bands from
pale shallows to a dark middle, a bright shore line, foam that breathes, ripple dashes moving with
the current, short sparkles on the sun's side, rings when it rains, white water at falls. Everything
within reach of the water is mirrored exactly below its foot, rippled in whole art pixels. The sea
continues past the world's edge into haze.

**The countryside from far out** (the overview and quarter scale, G11, G12). Relief reads as
landform: higher ground lighter, valleys holding mist at dawn, haze rising with distance and zoom
toward the region's air colour (15 % at half, 22 % at quarter, 30 % at the overview, `look.md`
§2.4) while the darks stay dark. Cloud shadows cross it; rivers flow; towns glow at night; roads
carry moving specks of people and carts.

**A figure walking** (M2). Twelve-frame cycles with planted feet, frames chosen by distance walked
(done on `main` and on `t3/integrate-game-world`); at 2× and above placed to the screen pixel while
staying whole art pixels; lit by the same sun (a shaded side, a cast shadow and contact darkness at
its feet); taking the shadow of a building it walks into; no two neighbours in step.

### 1.2 Numbers and scenes

- The acceptance numbers are `quality-bar.md` §4.1 (key and temperature by hour), §4.2–§4.4, §5 and
  §6, measured on the twelve golden scenes G1–G12 and the motion clips M1–M5 of §2 there. The
  `targets` in each region's `theme.look` still carry `look.md` §2.1's older numbers (cool share ≥ 8 %
  in cities) and are replaced by §4.1's (task W2).
- Two hue rules added here, because the studies broke them in opposite directions (measured on
  `out/reports/shots/depth/stills/forum_*_1x.png`, square paving, brightest 40 % as "lit"):

  | Frame | Lit paving (r, g, b) | Shade (r, g, b) | Verdict |
  |---|---|---|---|
  | Today, classic | 246, 234, 199 | 205, 192, 158 | pale, no shade colour |
  | R&D look, High | 224, 215, 193 | 123, 123, 120 | lit right; shade grey, not cool |
  | Depth combination | 189, 192, 192 | 97, 101, 108 | lit travertine turned grey: overshoot |

  **Lit warm stone keeps r − b ≥ 20 at day (≥ 35 at dawn and dusk); shade has b − r ≥ 6 at day
  (≥ 10 at dawn and dusk).** The cool share of §4.1 must come from shade, water, sky and haze, never
  from cooling lit planes.
- Approved references for the grade: the art director's mock-ups `out/look/mockups/parsa_dawn_after.png`
  (honey roofs, violet paving, vivid lapis and cinnabar) and `forum_midday_after.png`, and the R&D
  golden frames `G5_*_high` and `G8_*_high` as the starting baseline once E3 renders them in-game.

### 1.3 Disagreements, settled

| Question | Studies said | Decision |
|---|---|---|
| How cool is the shade | depth combination: blue-grey everything (Forum, lilac Pārsa dawn); R&D: warm but grey shade; mock-ups: warm lit, violet shade | the mock-ups, by the hue rules of §1.2. The depth frames had no region grade; their value structure (p2 23–29) is kept, their colour is not |
| Sun path | `look.md`: ±25° swing; R&D: 110° from the baked direction; depth: through the back of the view, right at dawn, top at noon, left at dusk | **depth's path** (170°), so shadows fall toward the viewer where they are seen; elevation never under 15° in play; noon height by month (`seasons.md` §3.11); sky light by hemisphere (`0.62 + 0.38·n_z`), sun 1.8× sky with exposure on the unshadowed median. Low tier clamps the swing to ±25° so its sheared shadow sprites stay right |
| Shadows | sheared sprites (`look.md` P2) vs height field (R&D) | height field on Medium and High; half-size shadow sprites, sheared, on Classic and Low only |
| Normal maps | `look.md` §4.4: not worth it | superseded (as `quality-bar.md` §1.2 already says): the packed page carries normals at no extra resident memory |
| Snap to palette | R&D: from colour through a 64³ lookup; quality research: exact ramp per pixel | exact: the packed page stores ramp and step, so at the baked sun the frame equals the atlas **byte for byte** (stronger than the bar's 99 % within one step) |
| Tilt-shift | depth: strongest "model village" cue, shrinks the cities, smears pixels | rejected for play. Dithered focus plus 5–10 % colour focus only for postcards and arrival push-ins (later) |
| Rim light | depth: frost-like noise on grass at 1× | rejected; the generator's coloured outlines already separate silhouettes |
| Height fog | depth: greys flat ground | only where there is relief, at dawn, in rain and with zoom, per region and hour (`theme.look`); off on flat ground at 1× by day; every air pass must keep p2 inside the bar |
| Real 3D | depth §4: not now | not pursued. The one experiment that would reopen it: one hero landmark as a real voxel mesh inside the existing frame, judged on a still against its sprite, a ±15° turn and a pan for crawl, and cost (later, X1) |
| Sea-level water mask | `look.md` P1: alpha code in the cells; R&D: material in the data layer | the ramp class of the packed page (water ramps) plus the tile water field (one texel per tile) |
| Engine AO vs the generator's | depth: bake static AO; R&D: live 3 and 7 px | the generator's own AO stays in the colours (it is light-independent and cancels in the relight); the engine adds only what it cannot know: occlusion between objects and enclosure (§3) |
| Camera while moving | `t3/integrate-game-world` filters the world layer linearly while moving | sprites at whole window pixels in a window-resolution target, camera offset in window pixels; zoom transitions in `SDL_SCALEMODE_PIXELART`; never a linear blur (`quality-bar.md` §6.1) |

---

## 2. One data contract for the art generator

Defined once. Every set (home, world, Rome, Athens, Pārsa) emits all of it in one rebuild (task A1);
nothing in §3 or §5 asks for another channel. A later rebuild changes art, not the format.

### 2.1 Files per set

| File | What | Who reads it |
|---|---|---|
| `assets/atlas/<set>.<n>.png` + `.json` | the colour page as today, base, glow and state sprites, **without shadow sprites** | Classic path; validators; the reference for the packed page |
| `assets/atlas/<set>.<n>.p.png` | the **packed page**, same size and rects as the colour page, for every sprite rendered from a model (§2.2) | shader path, instead of the colour page |
| `assets/atlas/<set>.s.png` + `.json` | the **shadow page**: every `…/shadow/…` sprite at half size (`"scale": 0.5` in the manifest), drawn ×2 with linear filtering | Classic and Low only |
| `assets/atlas/ramps.png` + `ramps.json` | the ramp table: one row per palette ramp, eight steps dark to light; per ramp its class and flags (§2.3) | shader path |
| home: `assets/atlas.p.png`, `assets/atlas.s.png` (+ `.json`) | the same for the home atlas | as above |

Glow sprites stay colour sprites (they are emissive colour, added after the light). Effects,
weather sprites, smoke, mist, the hand-drawn critters, UI, logo and frames are not model renders and
stay colour-only; the shader path draws them in its colour passes (§3.1). The manifest gains
`"packed": true` per page that has a packed twin; the atlas key scheme in `CLAUDE.md` is unchanged
(the packed page is addressed through the colour page's manifest).

### 2.2 The packed pixel

`ABGR8888` (the format shaders can sample, `look.md` §0), read as a 32-bit word
`w = r | g << 8 | b << 16 | a << 24`, sampled nearest only:

| Bits | Field | Notes |
|---|---|---|
| 0–2 | `step` | ramp step 0–7, dark to light: with `ramp`, the pixel's exact palette colour |
| 3–10 | `ramp` | ramp id 1–255 in `ramps.json`; **0 = no pixel** |
| 11–15 | `nx` | world normal x, 5 bits, signed (`n = code/15.5 − 1`) |
| 16–20 | `ny` | world normal y, 5 bits; `nz = sqrt(max(0, 1 − nx² − ny²))` |
| 21–29 | `h` | height above the anchor's ground, art px, 0–511 |
| 30 | `lit` | 1 where the generator's sun reached the voxel (its baked self-shadow, separated so a moving sun never doubles a shadow) |
| 31 | `snow` | snow catcher (`seasons.md` §4.2): an up-facing, sky-open face of a material snow lies on |

Why these widths: heights on today's pages reach 314 px (Rome), 244 (Pārsa), 118 (world), measured
on the R&D data pages; 9 bits leave 60 % headroom and the set validator fails any taller sprite.
Five-bit normals err by under 2°, below half a ramp step after snapping; large faces are exact
(axis normals are representable). If the baked-sun invariant (§2.6) ever fails because of them,
the fallback layout widens `nx` and `ny` to 6 bits by dropping the `snow` bit (snow then comes from
`nz` and the ramp class alone) and narrowing `ramp` to 7 bits (127 ramps; 100 are used today): a
recorded contract change, decided in A1 before any set is committed. Flat sprites (terrain, overlays, edge
faces, decals) carry the same word: their normal (up for ground, the face's side for faces) and a
height (0, or falling one px per px down a face).

What is **not** in the pixel, and why:

- **Material flags** (foliage, cloth, water, metal, marble, porous, snow-eligible): per ramp, in
  `ramps.json`; a ramp belongs to one material, so a per-pixel flag would repeat it.
- **Thickness**: per ramp class (`shell` in px: foliage 6, cloth 2, figures 8, solid 255), the R&D
  thin-shell rule made data. A per-pixel thickness page is the one later addition allowed, only if
  column and pole shadows smear in G4 and G6 after task E5 (decided there, on frames).
- **Baked ambient occlusion**: stays in the colour. The relight is a ratio of new to baked light,
  and the generator's AO multiplies both, so it cancels; the engine adds only occlusion it alone can
  see (between objects, and enclosure at large radii).
- **Emissive**: the glow sprites, as today.

### 2.3 The ramp table

`tools/artgen/ramps.py` (from the R&D branch, extended) writes, from `palette.MATERIALS` in order:
`ramps.png` (row = ramp, eight texels dark to light, alpha 0 past the ramp's last step) and
`ramps.json`: per ramp `id`, `material`, `steps`, Oklab `L` per step, `class` (`ground`, `grass`,
`crop`, `stone`, `marble`, `plaster`, `roof`, `wood`, `metal`, `cloth`, `skin`, `foliage_deciduous`,
`foliage_evergreen`, `water`, `glass`, `ink`, `snow`, `ice`), `shell`, `porous` (wet darkening),
`snow` (eligible), `specular` (metal, marble, glaze, wet paving sheen). Ids are stable across
rebuilds (new ramps append); 255 is the limit. The engine also uploads a **graded copy** of the
table every frame (≤ 255 × 8 colours on the CPU, ≤ 0.02 ms): grading the palette, not the pixels.

### 2.4 How the art itself changes

- Albedo: unchanged by A1. The baked self-shadow stays in the colour (the Classic path needs it); the
  `lit` bit lets the shader path undo it exactly. The R&D branch verified that writing data beside
  the pages leaves colour pages byte-identical.
- Shadow sprites leave the base pages for the half-size shadow page. Base pages are repacked:
  Rome 4 → 3 pages, Pārsa 3 → 2, Athens stays at 2, each with room for the seasons' states (`seasons.md` §4.4
  counted on exactly this space), world and home unchanged. Height-field shadows replace them on
  Medium and High; cloud shadow sprites (`weather/cloud_shadow_v*`) are dropped (the procedural deck
  matches its own shadows).
- The albedo-blue-bit snow catcher of `seasons.md` §4.2 is **not** used: the bit lives in the packed
  page and colour pages stay exactly on the palette.
- Art that changes colour (Oklab ramps, structured texture on large planes, figure readability,
  seasonal states, lit-night glow layers) is batched into **one quality rebuild per set** after A1
  (tasks A3–A6), so no set is rebuilt more than twice in this plan.

### 2.5 Memory, per region and per tier

Pages are held in 4096² slots of 64 MiB (`src/worldview` on `t3/integrate-game-world`); the home
atlas is 16 MiB. Shadow areas measured from today's manifests (shadow sprites' share of page area):
Rome 59 MiB of its pages, Athens 25, Pārsa 27, world 4, home 3; at half size a quarter of that.

| Resident set (home + world + the city in view) | Today | Classic | Low | Medium / High |
|---|---|---|---|---|
| City pages | Rome 4 slots 256 · Athens 2 · Pārsa 3 | Rome 3 (192) · Athens 2 (128) · Pārsa 2 (128) colour | same, packed | same, packed |
| World + home pages | 64 + 16 | 80 | 80 | 80 |
| Shadow page (half size) | in the pages | 16 | 16 | — |
| **Pages, worst (Rome)** | **336 MiB** | **288** | **288** | **272** |
| Cell cache (level 0 packed on the shader path; companions for impostors, §3.3) | 96 | 96 | 128 | 128 |
| Look targets at 1440p (window-resolution, RGBA8, §3.1) | ≈ 30 (view, blur) | ≈ 30 | ≈ 65 | ≈ 75 / 90 |
| Overview | 9 | 9 | 9 | 9 |
| **Texture total, Rome at 1440p** | ≈ 470 | **≈ 420** | **≈ 490** | **≈ 485 / 500** |

Against the budgets: the page budget (320 MiB, `src/worldview/tuning.hpp`, world-tech §4.14) holds
on every tier with room for a neighbouring city during travel inside the 640 MiB ceiling.
**Budget changes proposed** (for `CLAUDE.md` "Performance" and world-tech §4.14): cell cache
96 → 128 MiB on the shader path; a stated look-target budget of ≤ 96 MiB at 1440p (≤ 216 MiB at 4K);
the 1080p bench memory ceiling (`kBenchWorldMemoryMiB`, 832) re-measured, not raised in advance
(pages fall by 48 MiB, targets rise by 35–60 MiB). The R&D prototype's 709 MiB at 1440p is not
repeated: the shader path costs ≈ 15–30 MiB over today, not 318. **Low on small GPUs** drops the cell companions (no shadows at half and quarter scale),
the reflection target and bloom's two finest levels: ≈ 400 MiB at 1080p.

### 2.6 Build, repository and checks

- Build time: the packing is an array per sprite; a full rebuild stays the set build time (R&D, on
  this machine under load: Rome 30 min, Pārsa 16, Athens 15.5, world 7, home 1.5).
- Repository: packed pages compress like the R&D data pages, about 75 % of the colour pages
  (≈ 20 MB for all sets today); shadow pages ≈ 2 MB; colour pages shrink by the shadow area. Each
  full rebuild of every set adds ≈ 45 MB of history, hence at most two (§2.4).
- Checks in `tools/artgen/setvalidate.py`: packed and colour pages agree (decoding `ramp`/`step`
  through `ramps.png` reproduces every opaque colour pixel exactly; coverage identical); heights
  ≤ 511; normals unit within rounding; `snow` only on eligible ramps with `nz > 0.55`; the shadow
  page covers every `…/shadow/…` key; ramp ids stable against the committed `ramps.json`. Engine
  coverage test: every page marked `packed` has its twin.

---

## 3. One render pipeline for the engine

### 3.1 The frame on the shader path

Native zoom (1×–3×), in order. Targets are **window-resolution** (sprites drawn at the zoom with
nearest sampling, placed on whole window pixels; heights and dither in art pixels), so actors and
camera move by screen pixels at 2× and 3× and one pass serves every native zoom; the 2×/3× cost is
the 1× cost, which is the budgeted case.

1. **Scene** (one pass, one target of packed words): ground cells (level 0, cached, packed), items,
   landmark pieces, actors, all in today's painter's order through one sprite shader that adds the
   ground level to `h` (from the vertex colour), applies season and weather per sprite (vertex
   colour: snow cover, wetness, frost; `snow` bit → the snow ramp), wind sway by strips, and fades
   occluders by a **world-anchored dither** (a packed target cannot alpha-blend; dithered fade is
   pixel art). Draws: as today's scene (≤ 40).
2. **Lights**: one additive quad per light from a per-region light list built on the worker (glow
   layers' centres and heights; colour, radius and flicker from `theme.look.lights`), reading the
   scene's height and normal: falloff, wrapped facing, flicker below half a ramp step. Glow sprites
   into the glow target.
3. **Shadows and occlusion** (half resolution, depth-aware upsample): the sun march over the height
   field (bias growing with distance, world-anchored jitter, thin shells by ramp class), the cloud
   shadow (sampled from the deck texture), contact occlusion (8 samples, 2–8 px) and the depth
   darkening term (`blur(nearness) − nearness`, nearness = `2·sy + 3·h`). Enclosure occlusion
   (16–64 px) is **baked** into each level-0 cell as a quarter-resolution field when the cell builds,
   from the ground and the static items gathered for it (`quality-bar.md` §11: baked work stays
   baked).
4. **Resolve**: decode colour; relight by the ratio `(sky·hemi·ao + sun·N·L·shadow·clouds) /
   (0.42 + 0.58·max(0, N·S₀)·lit)`; move the pixel to its fractional place on its own ramp (by the
   ramp's Oklab L); dither with the generator's 4×4 band (0.55) indexed by world art pixel; take the
   colour from the graded ramp table; tint by the light's colour; add local light (`albedo × light`
   plus a small warm term, so a lamp on grass is amber). Sun updates are stepped every 2 s and
   cross-faded so dither bands never crawl.
5. **Water** (only on water pixels, by ramp class): bands from the tile shore field, two-phase flow
   ripples, shore line, foam, sparkles on the sun's side, rain rings, white water; reflections by the
   height-field march (High), lit, rippled in whole art pixels, lamps as stretched streaks; sky and
   cloud deck where nothing stands.
6. **Air**: height fog and haze by region, hour, weather and zoom; light shafts at low sun and in
   mist (High, chosen places, from a shadow-height map time-sliced when the sun moves).
7. **Colour passes**: cloud deck (quarter-resolution texture, one fbm per texel, posterised, clearing
   round the pointer), weather particles depth-tested against the height field, smoke, mist, petals
   and leaves, translucent effects, all lit by the hour's sun and sky uniforms.
8. **Bloom** from the glow target (dual filter, 3 or 5 levels) and **final**: 3D lookup for the
   non-palette colour (effects, UI-free world), weather modifiers (overcast, storm, after-rain),
   lightning flash, bloom added, camera offset, `SDL_SCALEMODE_PIXELART` during zoom transitions.
9. **Interface** samples the finished frame for its glass, as today.

SDL 3.4.20 allows at most five samplers beside the drawn texture in one render state (found on the
R&D branch); the split above keeps every pass within it. The home island draws into the same targets
through the same sprite shader (home atlas packed page), so the home region gets the same light;
`src/render/scene.cpp`'s multiply light map is used only on Classic.

### 3.2 Every pass

Status: **RT** works in real time on `t3/pixel-art-rendering-rd` (`src/worldview/fx/`, shaders in
`fx/shaders/composite.frag`, `light.frag`, `data_*.frag`); **OFF** offline study only
(`tools/depthlab/depthfx.py` on `t3/isometric-depth-rendering`); **IG** in the game on
`t3/integrate-game-world`; **NEW** idea or plan only. Cost: GPU at 1440p on the test machine;
**m** measured (R&D tier differences), **e** estimated from fetch counts.

| Pass | Source and status | GPU ms | Reads | Low | Medium | High | Classic |
|---|---|---|---|---|---|---|---|
| Scene, one packed pass | R&D colour + data passes (RT), merged into one (NEW) | 0.25 e (removes the R&D data pass: CPU −0.6 to −1.35 m) | packed page | ✓ | ✓ | ✓ | colour pages as today |
| Wind sway by strips | R&D `renderer.cpp` (RT) | ≈ 0 | item kind; ramp class later | ✓ | ✓ | ✓ | ✓ |
| Occluder dithered fade | `look.md` P3 (NEW) | ≈ 0 | — | ✓ | ✓ | ✓ | ✓ (alpha fade) |
| Local lights, flicker | R&D `light.frag` (RT); light list on worker (NEW) | 0.10–0.15 m | h, normal, `theme.look.lights` | ✓ | ✓ | ✓ | glow + additive pools |
| Lights at every zoom | IG (`2e4767f`) and R&D far lights (RT) | 0.02 | light list | ✓ | ✓ | ✓ | ✓ |
| Relight, sun path, hemisphere sky | R&D resolve (RT) + depth D1 (OFF) | 0.15 e | normal, `lit` | ✓ (swing ±25°) | ✓ | ✓ | flat multiply |
| Palette snap, world dither | R&D `0b26213` (RT) on exact ramp ids (NEW) | 0.05 e | `ramp`, `step` | ✓ | ✓ | ✓ | — |
| Height-field sun shadows | R&D (RT, full res 24/44 steps) + depth D2 hygiene (OFF) | 0.30 (16 steps) / 0.50 (32 jittered), half res, e | h, ramp shell | sheared half-size sprites | ✓ | ✓ | baked sprites, black |
| Contact AO (live) | R&D (RT, 3 and 7 px) | 0.10 e | h, normal | — | ✓ | ✓ | — |
| Enclosure AO (baked in cells) | depth D4 (OFF) | 0 per frame; cell build +10 % | static heights | ✓ | ✓ | ✓ | — |
| Depth darkening | depth D3 (OFF) | 0.10 e | h | — | ✓ | ✓ | — |
| Layered water | R&D (RT) | 0.20–0.30 m | water class, tile field | ✓ | ✓ | ✓ | animated tiles |
| Water reflections | R&D (RT) | 0.20–0.30 m (water pixels only) | h | sky only | sky only | ✓ | — |
| Clouds: deck + shadows | R&D (RT, 0.7–0.9 m at full res) → quarter-res texture (NEW) | 0.20 e (shadows only 0.10) | wind, weather field | shadows only (default) | ✓ | ✓ | cloud shadows as today (IG) |
| Haze by zoom, height fog | IG haze; depth E1 fog (OFF) | 0.05 e | h, `theme.look.haze`/`fog` | ✓ | ✓ | ✓ | haze quad |
| Light shafts | depth X1 (OFF) | 0.15 e (dawn, dusk, mist only) | shadow-height map | — | — | ✓ | — |
| Weather: rain, snow, splashes, puddles | IG (world-wide field `d5d79eb`); depth-tested particles (NEW) | 0.05–0.10 e | h, weather field | ✓ | ✓ | ✓ | ✓ (no depth test) |
| Wet, snow, frost, mud, dust, ice, flood | `seasons.md` §3–§4 (NEW) | ≈ 0 (in scene and resolve) | `snow`, ramp `porous`/`snow`, vertex data | ✓ | ✓ | ✓ | ground states only |
| Bloom | R&D (RT) | 0.10 / 0.15 m | glow target | 3 levels | 5 | 5 | 3 levels (blur chain) |
| Grade and final | `look.md` P8 (NEW; `theme.look` written) | 0.10 e | graded ramp table, 3D lookup | ✓ | ✓ | ✓ | affine fit (MOD + ADD) |
| Lean parallax | depth D5 (OFF; vertex shear) | 0 GPU, ≈ 0.02 CPU | sprite height | if approved | ✓ | ✓ | ✓ (vertex only) |
| Focus for moments | depth X2 (OFF) | 0.15 e | h | postcards and arrivals only, later | | | |

**Settings** (profile, settings screen, script verbs `look` and `clouds`): `Look: Classic / Low /
Medium / High` (default High with a discrete GPU, Medium on integrated graphics, Classic where no
`gpu` device can be made or a start-up pass-through check reads wrong channels); `Clouds: On /
Shadows only / Off` (On draws the deck thin at 1× and fuller zoomed out; Shadows only keeps their
shadows and the darker water under them; Off removes both); `Lean` on/off if adopted. Reduce motion
wins over all: halves sway, removes sparkles, rain rings, flashes and lean.

### 3.3 Every zoom level

Nothing may exist only at 1×. What each level shows:

| | Native 1×–3× | Half and quarter (impostor cells) | Overview |
|---|---|---|---|
| Grade, haze, fog, weather modifiers | ✓ | ✓, haze 15 % / 22 % | ✓, haze 30 % |
| Lights | point lights with pools | the same list, radius scaled, pools as soft quads | warm points (IG) |
| Relight and sun shadows | full | from an RGBA8 **companion** per impostor cell (normal 8+8, height 16 as max of 2×2) built with the cell: relight and shadows without palette snap (impostors are filtered) | none: shadows are sub-pixel at that scale |
| Occlusion | baked + contact | baked enclosure halved with the cell | baked into the overview build |
| Water | full | bands, flow, foam and sky from the tile field (fixes the R&D checkerboard sea at half zoom); reflections from the companion on High | flow and sky tint from the tile field |
| Clouds | thin, clearing round the pointer | 0.45 / 0.65 | 0.8 |
| Motion | sway, actors, particles | actors over impostors (IG), particles, water, cloud shadows; impostors do not sway | water, clouds, lights, weather |

### 3.4 What the Classic path shows

Today's frame plus everything that needs no shader: half-size soft shadow sprites, wind sway world-
wide, lights at every zoom, bloom from the existing blur chain, warm additive pools, the cloud
shadows and weather of the world-wide field, an alpha occluder fade, ground snow and the
generator's seasonal states (roofs keep their art in winter: the documented degradation of
`seasons.md` §4.2). The software-renderer screenshot tests keep running on it; the look gets its
own suite on the windowless `gpu` path that skips (exit 77) without a device.

### 3.5 Frame cost per tier

Anchors (measured, `out/reports/graphics-rnd.md` §4, 1440p, GPU waited for every frame): Classic
1.16–1.64 ms average; R&D High 4.0 (Pārsa terrace) and 5.2 (Tiber) with p99 8.3 and 10.05, of which
the data pass and the per-frame light gather cost +0.6 to +1.35 ms CPU, the full-resolution cloud
deck +0.7–0.9 and the full-resolution shadow march +0.7–1.3. This plan removes the data pass
(one packed scene pass), moves the light list to the worker, and runs shadows and clouds at half and
quarter resolution, as the R&D report's own E-R1 proposed.

| Part (busy city centre, crowds ≤ 800 live, rain, UI open) | Classic | Low | Medium | High |
|---|---|---|---|---|
| CPU: update, emission, submission | 0.6 | 0.65 | 0.7 | 0.7 |
| CPU: city simulation and crowd preparation (gate 0.6 + prep) | 0.8 | 0.8 | 0.8 | 0.8 |
| GPU: scene, lights, bloom, final | 0.5 | 0.6 | 0.65 | 0.65 |
| GPU: relight, snap, water | — | 0.5 | 0.5 | 0.55 |
| GPU: shadows, occlusion, depth darkening | — | 0.05 | 0.5 | 0.7 |
| GPU: reflections, shafts | — | — | — | 0.45 |
| GPU: clouds (on), fog, weather | 0.1 | 0.2 | 0.35 | 0.35 |
| **Whole frame average (partial CPU/GPU overlap)** | **≈ 1.6** | **≈ 2.7** | **≈ 3.4** | **≈ 4.2** |
| CPU average (gate 2 ms) | 1.4 | 1.45 | 1.5 | 1.5 |

Headroom to the 99th-percentile line of 8.3 ms: 2 ms or more on High at 1440p. At 4K the GPU parts
grow about 2.25×: High lands near the line, so 4K defaults to Medium (or High with the half-
resolution passes at quarter resolution); integrated graphics (assumed 3–8× slower, not measured)
default to Medium, and Low must meet the budget there (`quality-bar.md` §11), which only a real
integrated GPU can confirm (§6).

---

## 4. How the branches come together

1. **`t3/integrate-game-world` → `main`**, by the engine agent that owns it, once the crowds drawing
   (`8d9fb5f` and what follows) passes its gates. It merges into today's `main` without conflicts
   (checked with `git merge-tree`). Everything below branches from that `main`.
2. **`t3/isometric-depth-rendering` is not merged, wholesale or by cherry-pick.** It merged the R&D
   branch and then *pinned the art and world data back* to the R&D branch's versions (`580fd1d`:
   Pārsa, world and set catalogs; `bcaf07b`: worldgen and region code): merging it would revert the
   art and world lanes' newer work (`git merge-tree` against `main`: conflicts in every Athens,
   Pārsa and world page, `tools/artgen`, `tools/worldgen`). What it contributes is knowledge and two
   small things: the `gbuffer` script verb (`d562b5b`, ~40 lines in `src/worldview`), ported in E3
   so frames can still be dumped for study, and the pass recipes in `tools/depthlab/depthfx.py`,
   which E5 and E8 turn into shaders.
3. **`t3/pixel-art-rendering-rd` is not merged either; its code is ported.** Against `main` it
   conflicts in `CMakeLists.txt`, `src/app/script.cpp`, `src/core/tuning.hpp` and seven
   `tools/artgen` files (`render.py`, `pack.py`, `bigrender.py`, `rig.py`, `models/resident.py`,
   `sets/parsa/animals.py`, and `walkcycle.py` added on both sides); against
   `t3/integrate-game-world` in `renderer.cpp`/`.hpp` (both added lights at every zoom). Its
   committed data pages (`*.n.png`) belong to old colour pages and to the format replaced in §2.
   Port, by reading files from the branch (`git show <branch>:<path>`), never by merging:
   - **engine** (E1, E2, E4–E6): `src/worldview/fx/` (`look.*`, `tuning.hpp`, `shaders/*.frag`,
     `common.glsl`, README), `cmake/embed_shaders.cmake`, `tests/worldview_look.cpp`, the viewer's
     script verbs (`look`, `clouds`, `sky`, `rain`, `wind`, `cursor`, `clockrate`, `record`), the
     sway strips, the far lights where `main`'s own (`2e4767f`) do not already cover them, and the
     teardown order (GPU objects released before SDL quits; the R&D report found heap corruption
     otherwise). Rewritten on the way: the data pass (gone), the light gather (worker), clouds and
     shadows at reduced resolution, the colour-to-ramp lookup (replaced by exact ramp ids).
   - **art** (A1): `render.py`'s normal and height capture (`Shaded.nrm`, `hz`), the aligned page
     writing in `pack.py`, `bigrender.py`'s carrying of data through chunk composites, `ramps.py`.
     **Not** taken: `rig.py`, `walkcycle.py`, `models/resident.py`, `sets/parsa/animals.py` and
     `critters.py` walk changes, all superseded by the art lane's twelve-frame walks on `main`
     (`fde6036`, `out/reports/art-motion.md`), which already have the natural stride.
4. **Delete when the port is done** (orchestrator, after E6): both branches and their worktrees,
   after tagging them `archive/graphics-rnd` and `archive/depth-rnd` so the studies stay
   reproducible. `tools/depthlab` is **not** kept in `main`: it is offline prototype code whose
   passes now live in shaders, and the golden harness (E3) measures frames in the engine; the tag
   keeps it. Reports and evidence under `out/reports/` stay until the owner approves the first
   golden baseline, then their videos are deleted (disk).

Expected friction: the art agent finishing walks and Pārsa's third page right now (uncommitted
`tools/artgen` and `assets/atlas/parsa.*` in the shared tree) must commit before A1 starts; A1 then
works on `main` directly. Engine tasks each take a branch from `main`, merge back when their gates
pass, and the next starts from the result: no long-lived look branch.

---

## 5. The work plan

### 5.1 Lanes and how many at once

At most seven agents: **one engine agent** (`src/`, `tests/`, build files) at a time, each task on
its own branch; **one art agent** in `tools/artgen` at a time; **up to two world-data agents** (one
per layer, `tools/worldgen/regions/<layer>`, `assets/regions/`); **one audio agent**; **one QA
agent** (read-only: renders, measures, reviews sheets). Every engine task ends warning-free with
`ctest` green under `release` and `asan`, the world bench cases at 1080p, 1440p and 4K on the
`gpu` path at its tier and on `opengl` Classic (Pārsa terrace, Agora at dusk, Acropolis at night,
Tiber, pan, flight, overview, the crowd and city cases), whole frame p99 ≤ 8.3 ms, worst ≤ 16.6,
CPU ≤ 2 ms, scene draws ≤ 40, post ≤ 16, the soak flat; every visual task ends with QA's golden
review (`quality-bar.md` §12) and, where motion is the point, a clip.

### 5.2 Tasks

**M** must-have, **S** should-have, **L** later. Sizes are one agent, 2–4 hours.

| # | Task | Lane | Needs | Deliverable | Acceptance | |
|---|---|---|---|---|---|---|
| **E1** | **Foundation in the game.** `gpu` driver on the window with the fallback chain (`gpu` → `opengl` → `software`) and the start-up channel check; `ABGR8888` for sampled textures; shader embedding (sources and SPIR-V committed); Look and Clouds settings in profile, settings screen and scripts; final pass with the region grade from `theme.look` (two lookups by phase, baked on a worker), haze by zoom; bloom from glow; warm additive pools and flicker; wind sway by strips for every region's trees, reeds, cloth; camera composite on whole window pixels and pixel-art scaling in transitions; teardown order | engine | integrate merged | branch merged to `main` | G4, G5, G7 graded per §1.2 hue rules and `quality-bar.md` §4.4; lit pools amber (r > g) at G2/G7; clip of a breeze over the home and the Forum (sway in one wind, trunks still); M1 displacement s.d. ≤ 0.5 px; Classic shots unchanged where the look is neutral; bench | M |
| **W1** | **Lit nights**: window, door, torch, brazier and bridge-lamp lights placed per district in Rome, Athens and Pārsa (placements, `theme.look.lights` kinds); two agents, one per layer | world | A2 glow sprites where missing | region layers rebuilt, validated | `quality-bar.md` §4.3 on G7 and the Forum and Pārsa terrace at 22:00 (Classic already): warm lit 2–8 %, p98 at lights ≥ 160 | M |
| **A2** | Glow layers for lit nights: insula, house and shop windows (fixing the misaligned insula glow, QA V-A-010), torches, braziers, lamps; colour pages only (no format change) | art | — | set pages | coverage test; glow sits in windows at 2× | M |
| **A1** | **The data contract** (§2): packed pages, half-size shadow pages, `ramps.png`/`ramps.json`, `lit` and `snow` bits, flat sprites, all sets and the home atlas rebuilt; validator checks of §2.6 | art | art lane's walk round committed | pages + manifests committed | colour pages pixel-identical per sprite; packed decode reproduces every colour pixel; Rome 3 pages; heights ≤ 511; snow bit read back on known roof and wall pixels | M |
| **E2** | **Water and clouds**: layered water from the tile shore field at every level (bands, flow, shore line, foam, sparkles on the sun's side, rain rings, falls), sky and cloud deck in it; narrow-channel rule; sea beyond the world's edges; cloud deck at quarter resolution with shadows; Clouds toggle; deck fading over the home while a tool is active | engine | E1 | merged | M3 clip (no frame steps; strokes ≤ 1 art px per frame; 3–10 % of water); G2, G5, G10 water checks of `quality-bar.md` §5.1; sea at ½ without checkerboard; clouds on/shadows/off shots; clouds ≤ 0.25 ms | M |
| **E3** | **Golden harness**: `tests/scripts/golden/` G1–G12 and M1–M5 on both paths, the metric panel (luma percentiles, warm/cool, the §1.2 hue rules, colourfulness, lit share, ambient motion, FLIP against approved frames), seasonal day length in the clock, the `gbuffer` verb | engine | E2 | scripts + baseline sheet | the twelve scenes render headless with metrics; QA sheet to the owner for the first approval | M |
| **E4** | **Light on the packed pages**: the one-pass packed scene (cells, items, pieces, actors, home), resolve with relight, sun through the back of the view, hemisphere sky, `lit` undoing baked self-shadow, exact ramp snap with world dither, stepped sun updates; packed pages streamed in the existing slots | engine | E3, A1 | merged | at the baked sun with neutral grade, no shadows and no air, the resolved scene equals the colour pages drawn the same way **byte for byte** on G1 and G4; M1 pan: no static pixel changes colour; dawn walls facing away not brighter than the ground; G4, G6, G8 against §4.1; CPU ≤ 2 ms at the Acropolis by night; no frame over 16.6 ms flying between cities | M |
| **E5** | **Shadows, occlusion, depth**: height-field sun shadows at half resolution (32 jittered steps High, 16 Medium; bias; shells by class), shadow-height map for actors, contact AO, baked enclosure AO in cells, depth darkening; impostor companions (shadows at ½ and ¼); half-size sheared shadow sprites on Low | engine | E4 | merged | G6 shadow 07:30/12:00 ≥ 2.5×; shadows touch casters; occluded median < cast-shadow median (`quality-bar.md` §4.1); no roof stipple; column shadows continuous; forum timelapse clip 07:00 → 18:00 | M |
| **W2** | `theme.look` update for every region and stretch: `targets` to `quality-bar.md` §4.1 and §1.2 here, `fog` (base height, scale, density, colour by phase), `shafts` (places), night levels; worldgen `look.py` validators | world (core) | — | regions rebuilt | `build.sh --check`; seeded failures reported | M |
| **A3–A5** | **Quality rebuild, one set each** (Pārsa, Rome, Athens): Oklab ramp check and fixes, structured texture on large planes (Pārsa roofs and paving, Rome roof families, Forum travertine, Athens ground speckle into strokes), figure accents and lower outlines, the seasons' plant and ground states for that set (`seasons.md` tasks 4, 9, 12) and their generator helpers (task 2 minus the snow bit, already in A1) | art | A1; seasons task 3 | set pages | `quality-bar.md` §3.1–§3.3; previews against §4.1 materials; page counts unchanged; seasons' sheets | M |
| **A6** | World set and home quality rebuild with world states, overlays, backdrop snow caps (`seasons.md` task 8), atmosphere sprites (`look.md` A3 minus cloud shadows), ground clutter decals | art | A1 | pages | as A3; world page ≤ 4096 × 2816 | M |
| **S-E1** | Seasons: calendar and climates (`seasons.md` task 1) | engine | E3 | merged | as `seasons.md` §7 | M |
| **E6** | **Water polish and reflections**: height-field reflections on High, lamp streaks, glints by the sun's side, reflections from impostor companions at ½, wet paving sheen | engine | E5 | merged | G2 and G5 reflections cut at the water's edge, offset in whole pixels; lamp streaks at night; M3 | M |
| **E7** | **Weather and seasons on the look**: snow on what faces up (packed `snow` bit, cover by climate and altitude), frost, wet and puddles, mud, dust, ice, flood (`seasons.md` tasks 7 and 15 merged into one), depth-tested rain and snow, weather grade modifiers, lightning | engine | E5, S-E1, A6 overlays | merged | G3, G9, G10; `seasons.md` §7.1 snow checks; `quality-bar.md` §5.2–§5.3; bench cases `snow_city`, `season_turn` | M |
| **E8** | **Air and edges**: height fog and haze by region, hour, weather and zoom; sky and edges (backdrops, sea past the edges); light shafts on High | engine | E5, W2, A6 | merged | G8 terrace out of dawn mist with p2 in band; G11 haze by zoom; contrast falling with depth at ½ | S |
| **E9** | **Ambient motion world-wide**: smoke at emitters, petals and leaves by class and wind, moths, waterfalls at drops, bird flocks, dithered occluder fade for the pointer and followed figure; the liveliness metric | engine | E4; A6 flocks | merged | liveliness ≥ 1.5 % city, 0.8 % countryside, 2 % water (`quality-bar.md` §7) | M |
| **E10** | Clutter baked into ground cells (blue-noise by biome and season, contact shade, tall tufts sway) | engine | A6 decals, E5 | merged | `quality-bar.md` §8 ground richness on G1, G4, G12; zero per-frame cost | S |
| **E11** | Lean parallax (vertex shear, picking corrected), if the owner approves | engine | E4 | merged | M1 and M4: no tearing; ≤ 8 art px at the edge for the tallest landmark | S |
| **S1** | Weather and air audio: rain by surface, wind by strength, thunder by distance, a living rain bed (today's has LRA 0.1 LU) | audio | — | audio set | `quality-bar.md` §9; captured mixes in E7 | S |
| **Q1…** | Golden review after each visual task; integrated-GPU and Windows check the moment hardware is available | QA | each task | review report | `quality-bar.md` §12 | M |
| X2 | Roof-off interiors: Laeticia's cottage, the Apadāna, the Parthenon | art + engine | E9 | | hover at 2× shows inside | L |
| X3 | Focus for postcards and arrivals | engine | E8 | | never during play | L |
| X1 | Real-3D landmark experiment (§1.3) | engine | E5 | decision note | the three judgements of depth §4 | L |
| X4 | Per-pixel thickness page, only if E5's frames show smeared thin-caster shadows | art + engine | E5 | | | L |

### 5.3 The order and what runs beside what

```
engine:  [integrate merges] → E1 → E2 → E3 → S-E1 → E4 → E5 → E6 → E7 → E9 → E8 → E10/E11
art:     [walks round ends] → A2 → A1 → A3 → A4 → A5 → A6
world:   W1 (Rome, Athens) → W1 (Pārsa) → W2 → seasons tasks 3, 5, 10, 13, 17
audio:   S1, seasons task 16
QA:      golden reviews after E1, E2, E3 (first baseline), E4, E5 …
```

Seasons' remaining engine tasks (11 seasonal life, 14 the Set the scene panel) take the engine slot
after E9; they touch life and UI, not the look.

### 5.4 Where the owner's list lands

| Owner's ask | Task |
|---|---|
| Smooth water everywhere, at every zoom | E2 (layered water from the tile field at all levels), E6 |
| Reflections | E2 (sky and clouds), E6 (objects and lamps, High) |
| Lights at every zoom | done on `t3/integrate-game-world` (`2e4767f`); E1 keeps them and adds pools and bloom; W1 and A2 give cities lights to show |
| Ambient motion by wind | E1 (sway everywhere, all tiers), E9 (smoke, leaves, petals, flocks) |
| Clouds, with a toggle | E2 |
| Fluid walks | done (`main` `fde6036`, integrate `bcee7c4`, `8d9fb5f`); E1's composite and E5's actor shadows finish them; checked by M2 in E3 |
| "3D-ness" | E4 (moving sun), E5 (shadows, occlusion, depth darkening), E8 (fog, shafts), E11 (lean) |
| Four seasons everywhere | A1 (`snow` bit), A3–A6 (states), S-E1, E7 |
| Nothing pale or stale | §1 targets, E1 grade, A3–A5 art, gated by E3 |

---

## 6. Risks and the owner's decisions

### 6.1 Risks

- **Shader portability.** SPIR-V covers Vulkan on Linux and Windows. On Windows SDL's GPU layer may
  choose Direct3D 12, which needs DXIL; E1 requests Vulkan through SDL's GPU driver hint and falls
  back to Classic if it cannot, and DXIL blobs cross-compiled offline are added if Windows testing
  shows Vulkan missing. macOS needs Metal shaders (MSL, cross-compiled offline from the same GLSL)
  and a test machine: out of scope until the owner asks.
- **Memory on 6 GB cards**: comfortable (≈ 0.5 GB of textures on High at 1440p, §2.5). The tighter
  case is 2 GB integrated graphics: Low drops the companions, reflections and bloom's finest levels.
- **The pixel-art character under relighting**: guarded by construction (exact ramp and step, world
  dither, byte-identical at the baked sun) and by E4's tests; residual risks are dither bands moving
  as the sun moves (stepped sun updates) and lamp flicker crossing a step (kept under half a step).
- **The packed format**: five-bit normals and 9-bit heights are new; A1 and E4 test the invariant,
  and §2.2 names the fallback layout. A tall future landmark over 511 px must be split.
- **SDL's young `gpu` driver**: its windowed path, vsync and frame pacing were never run here
  (automation stays headless); the windowless path works. The five-sampler limit of 3.4.20 shapes
  the passes.
- **Art rebuild time and history**: about 1.5 hours of machine time per full rebuild under load and
  ≈ 45 MB of history; the plan holds it to two rebuilds per set.
- **Not verifiable without a real window and other hardware**: the feel of motion at 120 Hz, present
  and swap cost, integrated GPUs, Windows, high-DPI scaling of the window-resolution targets. QA
  writes a short checklist for the owner's first windowed run after E1.

### 6.2 The owner's decisions

1. **How dark night may go.** Recommendation: unlit median luma 28–38 (inside the bar's 22–45),
   cool, with readable value contrast; every inhabited view carrying warm light (2–8 % in cities);
   no darker, because night is a third of play and the cities are the reward.
2. **Buildings that hide what you look at.** Recommendation: a dithered fade of anything standing
   in front of the pointer, the followed figure or Laeticia, everywhere (E9); true roof-off
   interiors only for Laeticia's cottage, the Apadāna and the Parthenon, later (X2).
3. **The lean.** Recommendation: adopt it small (≤ 8 art px at the screen edge for the tallest
   landmark), on by default, off with reduce motion, after watching
   `out/reports/shots/depth/clips/forum_pan_compare.mp4` (left flat, right lean).

Settled here without needing the owner unless the owner disagrees: tilt-shift and rim light rejected, no
real 3D (one experiment kept for later), clouds on by default (thin at 1×), High by default on a
discrete GPU, macOS out of scope.
