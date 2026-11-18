# The look of the world

What the game should look like, why it looks pale and stale today, and the render, art, audio and
data work that gets it there without breaking the performance budget. The engine lane builds on the
world renderer described in `src/worldview/README.md` (branch `t3/add-world-viewer-renderer`, being
merged into the game on `t3/integrate-game-world`). The home island's renderer (`src/render/scene.cpp`)
keeps working for worlds without `assets/world/world.json` and gets the same passes where cheap.

Contents: 1 diagnosis · 2 visual direction · 3 rendering plan · 4 art plan · 5 sound of weather ·
6 work plan · 7 mock-ups · 8 decisions to confirm.

---

## 0. What SDL 3.4 gives us (measured here, not assumed)

Installed: SDL **3.4.20** (`pkg-config --modversion sdl3`). Render drivers built in: `opengl`,
`opengles2`, `vulkan`, `gpu`, `software`. Machine: development machine's GPU, NVIDIA Vulkan ICD. Probes were
small C++ programs run headless (`offscreen` or `dummy` video driver, no window shown, no audio),
then deleted.

| Question | `software` | `opengl` / `opengles2` | `gpu` (SDL_GPU on Vulkan) |
|---|---|---|---|
| Built-in blend modes `BLEND`, `BLEND_PREMULTIPLIED`, `ADD`, `ADD_PREMULTIPLIED`, `MOD`, `MUL` | yes | yes | yes |
| Custom blend modes (`SDL_ComposeCustomBlendMode`) | **none** ("That operation is not supported") | screen (`ONE, ONE_MINUS_SRC_COLOR`), 2× multiply (`DST_COLOR, SRC_COLOR`), `MAXIMUM`, `DST_ALPHA` masking: yes on both; reverse subtract only on `opengles2` | all tested |
| Texture address modes (`SDL_SetRenderTextureAddressMode`, `WRAP`) | yes | yes | yes |
| `SDL_SCALEMODE_PIXELART` (new in 3.4) | yes | yes | yes |
| Custom fragment shaders (`SDL_CreateGPURenderState`) | no | no | **yes** |
| Available under the `dummy` video driver | yes | no | no ("No supported SDL_GPU backend found") |
| Available under `offscreen` | yes | yes (EGL) | **only windowless**: `SDL_CreateGPURenderer(device, nullptr)` works; `SDL_CreateRenderer(window, "gpu")` fails for want of `VK_EXT_headless_surface` |

Custom shaders on the `gpu` renderer, as verified:

- A fragment shader is a SPIR-V blob (DXIL for Direct3D 12, MSL for Metal are the other formats).
  Interface: input `location 0` = vertex colour, `location 1` = UV; the drawn texture at
  `set 2, binding 0`; extra samplers at `set 2, binding 1…`; uniforms at `set 3, binding 0`.
  Written in GLSL and compiled with `glslc` (installed here, `/usr/bin/glslc`): a 3-line build step,
  no runtime dependency if the blobs are committed.
- A 3D colour lookup (16³ as a 256 × 16 strip, extra sampler) graded `(51, 102, 204)` to exactly the
  expected `(204, 102, 204)`.
- Uniforms set between two draws in one frame apply per draw (the renderer flushes on change).
- A render target can be bound as an extra sampler (the reflection and shadow layers need this).
- **Two pitfalls found.** (1) A texture created as `SDL_PIXELFORMAT_ARGB8888` (the game's
  `kTextureFormat` today) is stored swizzled: a custom shader reading it sees red and blue swapped
  (red read back as blue). (2) A texture created as `SDL_PIXELFORMAT_RGBA8888` exposes no
  `SDL_PROP_TEXTURE_GPU_TEXTURE_POINTER` (null), and binding it crashed the probe. Textures that
  shaders read must be `SDL_PIXELFORMAT_ABGR8888` (`SDL_PIXELFORMAT_RGBA32` on little-endian).
- Cost at 2560 × 1440: a full-screen copy plus a one-pixel readback (to wait for the GPU) took
  0.39–0.41 ms per frame; the same copy through the lookup shader 0.41 ms; through a 7-fetch
  distortion shader 0.39–0.40 ms. The readback dominates: **the passes themselves cost less than the
  0.02 ms noise** on this GPU.

Not verified: a visible window on the `gpu` driver (not allowed from automation; it is SDL's
standard path), any other GPU (mid-range laptop GPUs and integrated graphics are assumed 3–8× slower
than the development machine's GPU), Windows and macOS. macOS would need MSL blobs (cross-compiled offline)
and is out of scope unless the owner wants it.

**What this means.** Without shaders, the 2D renderer can only multiply, add and alpha-blend. That
gives an affine colour change per channel (`c × m + a`), additive bloom from the blur chain, light
pools, cloud shadows and sky gradients. It **cannot** do a tone curve, saturation, split toning,
hue-band changes, reflections masked to water with ripple distortion, wet sheen or heat shimmer.
Those need the `gpu` driver.

---

## 1. Diagnosis

Screenshots are under `out/reports/shots/` (engine), `out/qa4/shots/` (independent QA) and
`out/artgen/` (art previews). Image statistics below were measured on these frames: luma 0–255,
saturation as HSV S, "warm" and "cool" as the share of pixels with red above blue (or blue above
red) by more than 4 %.

| Frame | p2 luma | median | p98 | mean S | S > 55 % | warm | cool |
|---|---|---|---|---|---|---|---|
| Home, busy afternoon (`life/6_busy_afternoon`) | 47 | 103 | 215 | 37 % | 10 % | 17 % | 22 % |
| Rome 1×, day (`worldview/9_rome_1x_day`) | 55 | 139 | 230 | 43 % | 32 % | 90 % | 3 % |
| Athens Acropolis 1× (`worldview/4_…`) | 65 | 140 | 232 | 31 % | 6 % | 97 % | 1 % |
| Athens Agora 1×, dusk (`worldview/6_…`) | 42 | 98 | 148 | 67 % | **85 %** | 98 % | 0 % |
| Pārsa terrace 1×, day (`worldview/1_…`) | 44 | **162** | 215 | **28 %** | 7 % | 87 % | 2 % |
| Pārsa terrace, dawn as the engine grades it | 44 | 125 | **162** | 33 % | 5 % | 87 % | 2 % |
| Home pond, dusk (engine, this pass) | 33 | 73 | 157 | 51 % | 19 % | 86 % | 3 % |

### 1.1 The causes, shared by every region

1. **One light, one colour.** Grading is a flat multiply of the whole frame (home: `SDL_BLENDMODE_MUL`
   light map; world: `MOD` by ambient × region keyframe, then a haze quad). A multiply keeps every
   hue and only darkens it, so dusk is a brown filter (`out/qa4/shots/V-D-005_home_grading.png`: dusk
   is olive, dawn is grey-green) or an orange wash (Rome and the Agora at dusk). There is never a warm
   key against a cool shade: the cities have **0–3 % cool pixels** in any frame. That, more than
   anything, is "stale".
2. **Compressed values.** Dawn and dusk lose their highlights (Pārsa at dawn: p98 162, nothing
   brighter than a mid-tone); noon loses its darks (Athens: p2 65). Shadows are a black layer at a
   fixed ~0.4 opacity: grey, short, the same at 7 am as at noon.
3. **Big flat surfaces with nothing on them**, made worse by (1) and (2): Pārsa's flat roofs (the
   largest single surfaces in the game), the Forum square, the Acropolis paving, the home meadow at
   1×, and the whole world set, which is still flat diamonds (QA V-A-001: 85 % of the world's tiles).
4. **Water does not behave like water.** It is an opaque animated tile: no sky in it, no reflection,
   no light at night. The sea is a two-blue checkerboard; the Tiber an olive lawn (QA V-A-004).
5. **No atmosphere or sky.** The world ends in straight diagonals against a flat gradient
   (QA V-D-001). Zooming out adds no aerial perspective; distance looks as sharp as the foreground.
6. **Little motion per screen.** Cities have no actors yet (the crowds round is coming), and nothing
   else moves: no smoke, flags, birds, foliage sway or water flow in the world view.
7. **Light pools hold the hue.** A lamp at home makes a green-yellow pool on grass because the pool
   is multiplied into the light map (`out/look/mockups/pond_dusk_before.png`). Warm light needs an
   added component.

### 1.2 Region by region

**Home** (`out/artgen/hd/village.png`, `out/reports/shots/night_1080p.png`, `life/*`). The bar for
charm: storybook greens, saturated small props with dark outlines, crisp cast shadows, the floating
island's cliffs, warm windows and lamp pools at night, critters everywhere. **Protect all of it**,
including the night look (moody, readable, exposure capped per sprite). Weak: the meadow at 1× is
one flat green; dusk and dawn are flat multiplies; the pond at dusk is grey-blue with no sky; light
pools turn grass yellow-green.

**Rome** (`worldview/9_rome_1x_day`, `10_rome_quarter_scale`, `qa4/shots/V-D-005_rome_grading`).
The best city fabric in the world: insula quarters, warm brick, the Forum's temples, the Colosseum
valley. **Protect the fabric and the terracotta.** Weak: the roofs are a pale salmon of one hue over
the whole frame (90 % warm, 3 % cool); the Forum square is a large cream plane; shadows are short
grey wedges; dusk turns the city into one saturated orange; the Tiber is a lawn; at quarter scale
the grass between quarters is a uniform lime; at night glow specks sit on insula roofs, not in the
windows (QA V-A-010).

**Athens** (`worldview/4_athens_acropolis_south_1x`, `6_athens_agora_dusk_1x`, `out/artgen/athens/`).
The Parthenon reads instantly, painted pediment and all: **protect it**, and the houses, which are
nearly at home's level. Weak: the Acropolis is grey rubble terraces with no dark values (p2 65);
marble and paving sit at the same value, so the temple does not glow white against its rock; dry
grass is a speckle that reads as dirt; asphodels read as crowds (QA V-A-008); stairs are white
slabs; at dusk the Agora is a single orange (85 % of pixels above 55 % saturation).

**Pārsa** (`worldview/1_parsa_terrace_1x_day`, `3_parsa_quarter_scale`, `out/artgen/parsa/`). The
terrace at 2× is the most impressive set piece in the game: **protect the Apadāna, the Hall of a
Hundred Columns site, the Great Stair, the lapis friezes and the red porticoes.** Weak: the frame is
high-key and pale (median 162, mean saturation 28 %); the flat roofs are vast empty beige planes; the
paving is a grey grid; at dawn the engine's multiply leaves a lilac-brown film with no highlights;
around the terrace, flat grey world tiles and stacked rock cubes (no world art yet).

**The land and sea between** (`worldview/8_world_overview`, `qa4/shots/V-A-004_*`, `V-B-006_*`,
`V-D-001_*`). Flat diamonds, a checkerboard sea, cube mountains, one-level relief confetti, hard world
edges. The art and relief work is already queued (QA top twenty); this document adds the look targets
it must meet (§2) and the engine passes that make it read (§3).

**UI** (`out/reports/shots/frontdoor/*`, the docks in `life/*`). The quiet glass works: legible,
consistent, unobtrusive. **Protect it.** Two notes: the glass samples the world blur, so it inherits
the new grade for free; the overview has no markers or labels (QA V-D-005), and the era caption is a
faint line of text at the top. Both belong to the integration round, not this one.

---

## 2. Visual direction

> **A sunlit miniature that breathes.** Every scene has a warm key and a cool counterpoint; colour
> lives in the light, not only in the paint. Water holds the sky. Something moves in every part of
> the screen. The pixel grid is sacred: effects add light, not blur.

### 2.1 Targets the graded frame must meet

Measured on the world area of a 1440p frame (UI excluded), per region and hour. These are the
acceptance numbers for the grade and art tasks; headless tests assert them with the script
language's image statistics.

| Hour | p2 luma | median | p98 | mean S | S > 55 % | warm / cool pixels |
|---|---|---|---|---|---|---|
| Day | 20–45 | 100–135 | 205–230 | 33–48 % | 8–30 % | cool ≥ 8 % in cities, ≥ 15 % at home and on coasts |
| Dawn | 10–30 | 70–125 | 180–215 | 30–45 % | ≤ 25 % | warm 35–75 %, cool ≥ 7 % |
| Dusk | 8–25 | 45–85 | 165–215 | 38–55 % | ≤ 40 % | warm 55–80 %, cool ≥ 8 % |
| Night | 4–14 | 22–45 | ≥ 200 only at lights | 18–35 % | ≤ 10 % | cool ≥ 50 % of unlit pixels |

By material, at day (luma / saturation): grass 90–140 / 35–55 %; dry earth and paving 115–175 /
15–35 %, marble paving ≤ 215; lit roof planes 135–190, never one flat value over more than 4 × 4
tiles; a wall's shaded side at least 25 % darker than its lit side; foliage 55–130 / 35–65 %, deepest
shade 35–55; water 65–130 / 35–60 %, hue 190–215°, sea at least 15 % darker than the land beside it;
accents (paint, lapis, cinnabar, banners, clothes) S ≥ 55 % and 2–6 % of a city frame. Nothing is
pure black (minimum 4) or pure white except lights and specular glints.

### 2.2 One palette discipline, four identities

What unifies every set: the same light model (§2.3), the same shadow-tint family per hour, one
master table of colour ramps that all sets draw from (five steps per material, hue-shifted: shadows
toward blue-violet, highlights toward warm yellow), dark coloured outlines on small props and
figures, the same saturation ceiling for large surfaces (≤ 45 %) and floor for accents (≥ 55 %).

What distinguishes each region (mid-tone anchors for the lit side at day; ramps are built around
them):

| Region | Large surfaces | Accents | Light character |
|---|---|---|---|
| Home | grass `#5DA54A`, shade `#3E7A3A`, path `#C9A46A` | flower reds, cottage red `#B8402F`, blossom pink | storybook: saturated, soft, the warmest nights |
| Rome | terracotta `#B8512F` (ramp `#6E2A1E`→`#E08A5A`), travertine `#E6DCC4`, brick `#9A4A32`, basalt `#3A3A40` | umbrella-pine green `#3E5B2E`, gilded bronze `#D9A93A`, banner and awning dyes | honey-gold, smoky haze; dusk is Rome's signature, gold not orange |
| Athens | marble `#F1EDE3` (shade `#B7B4C8`), dry gold earth `#C9A465`, limestone rock `#A39A8A` | painted frieze blue `#2A5BA8` and red `#B2342A`, olive silver-green `#8C9A6B`, sea `#1F5E8C` | brilliant, high contrast, short blue shadows; marble the brightest thing on screen |
| Pārsa | limestone `#C9B79C` (shade `#8E8597`), mud plaster `#C8A27A`, paving `#A89F94` | lapis `#2648A0`, cinnabar `#B8322A`, gold `#D8AE3E`, garden green `#4E8A3A` | crisp mountain air, cool shadows, stone that turns honey at dawn and rose at dusk |

### 2.3 Light

- **The sun stays screen-relative** (art is lit from the upper left; `world.md` §3.2), but it moves:
  through the day the shadow direction swings ±25° around the baked direction (morning shadows lean
  toward screen right, evening toward screen bottom) and its length follows the sun's height: 2.2×
  the baked length at the first and last light, 0.7× at noon. Shadows fade out after sunset and are
  replaced by faint moon shadows (0.25 opacity, cool) on clear nights.
- **Two lights, not one multiply.** Sunlit pixels get the sun's colour (white-gold at noon, honey at
  dawn, copper at dusk); pixels in the shadow layer get the sky's colour (blue at noon, violet at
  dawn and dusk). Cloud shadows and overcast reduce only the sun term, so a cloud makes the ground
  cool and soft, never grey.
- **Ambient amount:** shade is 45–60 % of lit at day, 35–45 % at dawn and dusk, and at night the
  moonlight ambient keeps unlit areas at luma 22–45, cool. Lamps, windows and fire are the only warm
  light at night, and they add light (warm, with bloom) instead of multiplying the hue under them.

### 2.4 Atmosphere

- **Haze by distance and zoom.** At 1× the frame leans 0–8 % toward the region's haze colour from
  bottom to top of the screen; at half scale up to 15 %, at quarter scale 22 %, at the overview 30 %
  toward a horizon colour. High ground reads lighter and bluer when zoomed out.
- **Regional air.** Rome: warm smoke haze, stronger in the afternoon, mist on the Tiber at dawn.
  Athens: thin warm haze toward the sea, heat shimmer on paving at noon (subtle, optional). Pārsa:
  clear and cool; dust breezes in summer (ochre tint, motes); mist on the plain at dawn. Seas: haze
  toward the horizon, sea mist at the seams. Zagros and Apennines: low cloud and fog in valleys.
- **Night mist** over water and low ground, thin, drifting.

### 2.5 What "alive" means on screen

At any moment, in a 1× view at 1440p: at least **12 independent moving things in a city** (people
aside: smoke, flags, awnings, birds, water, foliage, lamp flicker), **6 in the countryside**, and
water that always moves. Measured as the share of world pixels that change between two frames 0.5 s
apart, with actors hidden: ≥ 1.5 % in a city, ≥ 0.8 % in countryside, ≥ 2 % where water fills a
third of the view. Reduce motion (living-corner R10.8) halves these and removes flashes.

---

## 3. Rendering plan

### 3.1 Renderer path: recommendation

**Use SDL's `gpu` render driver as the primary path, with the current renderers as a "classic"
fallback.** The `gpu` driver is the same 2D renderer API the game already uses (batching,
`SDL_RenderGeometry`, targets, blend modes all unchanged), plus custom fragment shaders for a few
full-screen and layer passes. It runs on Vulkan on Linux and Windows. When no GPU device can be
made, the game falls back to `opengl` (or `software` headless) with the classic look: today's grade
plus an added lift, coloured light pools, bloom and black shadows.

Why not stay on the plain 2D renderer: the most important improvements (§1.1 points 1, 2 and 4) are
per-pixel colour work that blend modes cannot do (§0). Why not a custom renderer on SDL_GPU directly:
it would rewrite the batching, targets and sprite code that already meet the budget, for nothing the
GPU render state does not already give.

Risks and their answers:

| Risk | Answer |
|---|---|
| The `gpu` driver is newer than `opengl` | keep `opengl` as the fallback; the bench runs both; a setting forces classic |
| Format swizzle and null GPU texture pointers (§0) | all targets and pages that shaders sample are `ABGR8888`; a unit check reads one pixel through a pass-through shader at start-up and falls back to classic if the channels come back wrong |
| Sampler bindings are fixed when a render state is created | targets are allocated with headroom and never shrink (as today); recreate the state on the rare resize |
| Headless tests use `software` (no shaders) | screenshot tests keep the classic path for logic; a new "look" suite runs the `gpu` path windowless under `offscreen` and skips with exit 77 when no Vulkan device exists, like the bench |
| Shaders need a compiler | GLSL sources and the compiled `.spv` blobs are both committed; `glslc` is needed only to regenerate them (a CMake check rebuilds them when it is present and a test fails if a blob is stale). No runtime or build dependency is added |
| macOS | not covered (needs MSL); if wanted, cross-compile the same GLSL offline and commit the blobs |
| Draw calls | post passes are a fixed count of full-screen quads, not batch breaks; budget them separately (§3.4) |

### 3.2 The frame, pass by pass

Native level (zoom 1×–3×). Half and quarter scale and the overview use the same final pass and sky;
their content comes from the impostor cells as today.

```
P0 sky & horizon   window space: gradient, sun/moon, stars, clouds, backdrops, the sea beyond the edge
P1 ground cells    cached (as today) + macro colour variation + water coded in alpha
P2 shadow layer    shadow sprites with the sun's shear and length; cloud shadows; composited tinted
P3 objects         as today + wind sway + occluder fade
P4 reflections     items, actors and lights near water, mirrored, into their own layer   [gpu]
P5 weather         rain/snow streaks, splashes, puddles (coded as water), fog strips, lightning
P6 glow            emissive layers, after grading (as today)
P7 bloom           glow layer down and up the existing blur chain
P8 final           water + colour lookup + haze + bloom + flash, scaled to the window      [gpu]
P9 interface       glass blur samples the finished frame (as today)
```

Each pass below: what it does, how, data, cost at 1440p (budget), quality levels, how it is tested.
GPU costs are budgets for a mid-range laptop GPU, sized from the probe (§0) with a 5–10× margin.

#### P0 Sky, horizon and world edges

- **Does:** a three-stop sky gradient by hour and region (the hex tables in each city file §8), sun
  and moon discs, stars (a fixed star field texture, brighter and denser over Pārsa and at sea,
  dimmed by Rome's smoke), two cloud decks drifting with the wind. Behind the north and east edges
  the backdrop strips (`backdrop/<id>/<day|night|winter>/v<n>`, already in the contract) with aerial
  haze. Beyond the south and west edges, where the world ends at sea, **the sea goes on**: one quad
  of the sea texture with `SDL_TEXTURE_ADDRESS_WRAP` (verified on every driver) fading into the
  horizon colour. Land edges keep their faces, as the home island does.
- **Why it matters:** the sky is rarely seen directly in a top-down view, but it is seen **in the
  water**. The same sky colours feed P8's reflections, so the sea at dusk is rose and violet.
- **Cost:** < 0.05 ms GPU, < 0.02 ms CPU, 3–6 draws. **Data:** sky stops per region and phase in the
  region theme; star and cloud textures (world set). **Test:** shots of the four corners of the world
  at ½ and ¼ scale at day and dusk; no pixel of the flat clear colour remains; the sea continues past
  the edge (mean colour of a rect beyond the rim within the sea's range).

#### P1 Ground cells: macro variation and the water code

- **Macro variation**, baked when a cell is built (zero per-frame cost): each tile's colour is
  multiplied by a low-frequency noise (±4 % value, ±3° hue, ±5 % saturation, 12–24-tile features),
  so large fields of one terrain stop repeating. Off near paths and buildings where it would fight
  the art.
- **Water code:** water tiles are drawn into the cell with alpha `1 − (8 + 4 × depth band) / 255`
  instead of 1. Anything drawn later over water (boats, bridges, objects in front) writes alpha 1
  and so erases the code, which makes it an exact, free, per-pixel water mask with depth for P8. The
  classic path ignores it; the 3 % sky that would show through is drawn under it in sea colour.
  Puddles (P5) carry the same code.
- **Cost:** cell build +5 %; no per-frame cost. **Test:** unit (variation is deterministic and
  bounded); scripted: alpha of a sea pixel, of a pixel under a boat, of a land pixel.

#### P2 Shadows: the sun moves, edges soften, shade turns cool

- **Direction and length:** each shadow sprite is drawn as a quad sheared and stretched about its
  anchor (four vertices through `SDL_RenderGeometry`, already how sprites are drawn): stretch along
  the baked shadow axis by the sun's length factor, shear by its swing (§2.3). Correct for the
  silhouette of a ground-projected shadow within ±25°; beyond that it would detach from the base, so
  the swing stops there.
- **Why not re-bake shadows per hour:** shadows already fill most of a page per city (measured:
  `athens.1` 83 % shadow, `rome.2` 90 %, `parsa.1` 52 %, world 12 %). A second baked direction
  would add about one page per city, over the page budget.
- **Soft edges:** shadow sprites move to **half resolution** (an art contract change, §4.3) and are
  drawn ×2 with linear filtering into the shadow layer: a one-pixel penumbra at 1× that grows softer
  with length. This also frees about half a page per city.
- **Tint:** on the `gpu` path the shadow layer is composited with a small shader:
  `c × mix(1, skyShadowColour, opacity × a × sunStrength)`, so shade takes the sky's blue or violet
  and fades with clouds and night. Classic path: black at opacity, as today.
- **Cloud shadows** (home already has them) join the same layer in the world, from the weather cells.
- **Cost:** CPU +0.03 ms (four floats per shadow quad), GPU < 0.05 ms. **Quality:** Low: fixed
  direction, black; Medium: moving and tinted; High: + moon shadows. **Test:** unit (shear and length
  by hour); scripted: shots at 07:00, 12:00, 18:00 of the Parthenon: the shadow's bounding box length
  ratio ≥ 2.5 between dawn and noon; mean hue of shadow pixels at noon is blue (b > r).

#### P3 Objects: sway and fade

- **Wind sway:** trees, reeds, crops and grass tufts drawn as two quads, the upper part sheared by
  the wind and gust (`Weather::gustAt`), in whole art pixels (0, ±1, ±2), so the grid holds. Home
  already sways trees; this generalises it to the world's native level (impostors do not sway).
- **Occluder fade:** an item whose screen box covers the cursor, the followed actor or Laeticia, and
  stands in front of it, fades to 35 % over 150 ms (a `ScreenGrid` query, which exists). Must-have
  and cheap. **Roof-off interiors** for a few landmarks are a nice-to-have (§3.3).
- **Cost:** < 0.05 ms CPU. **Test:** scripted: cursor behind the Basilica Julia, expect the item's
  alpha ≤ 0.4; a tree's top rows move between two frames in wind, its trunk does not.

#### P4 Reflections (`gpu` path)

- **Does:** items, actors, ships and glow sprites within 6 tiles of water are drawn a second time,
  **mirrored vertically about their ground anchor**, into a reflection layer. For a 2:1 isometric
  view this is exact for anything standing on flat ground at the water's level: a point h pixels
  above its base appears h pixels below it. Bridges, quays, boats, trees on banks, the Tiber island,
  lamps and lit windows all reflect; at night the lights draw long wobbling streaks.
- **How:** the gathered region already knows which elements touch water tiles (one bit per element,
  set when it is gathered on the worker thread). Same sprites, same pages, same batching: 3–6 more
  draws.
- **Cost:** CPU < 0.1 ms (≤ 400 extra sprites), GPU < 0.1 ms, +15 MB target. **Quality:** Medium:
  sky only (no P4); High: mirrored objects and lights. **Test:** scripted: a lamp by the home pond at
  night; expect warm pixels (r > b + 30) inside the pond rect below the lamp, none above it.

#### P5 Weather layer

- Rain streaks slanted by the wind's screen-x (sheared quads, 3 lengths by intensity), splashes and
  rings (exist), snow drifting with the wind, puddle decals on paths and paving once a block's
  wetness passes 0.6 (they carry the water code, so P8 makes them mirror lamps and sky), fog strips
  on low ground at dawn and over rivers at night (layered, drifting, thinning with the hour),
  lightning bolts (fx sprites) and the ground flash at the strike.
- **Cost:** CPU ≤ 0.15 ms at 2 500 live particles (the pool holds 4 096), GPU < 0.1 ms.
  **Test:** scripted shower: wet blocks darken (mean luma of a paving rect drops 10–20 %), puddles
  appear only on path or paving tiles, rain falls only under the cell.

#### P6 Glow, and warm light that adds

- Glow layers as today (after grading, additive). Light pools change from "multiply into the light
  map" to **light × albedo + a small added warm term**, so a lamp on grass makes amber, not lime.
  Lamps and torches flicker (±8 % at 6–9 Hz noise, per light seed); fire altars and kilns breathe
  slower. Fix the misaligned insula glow (QA V-A-010) in art.
- **Cost:** none new. **Test:** scripted night at home: pool pixels have r > g (amber), not g > r.

#### P7 Bloom (every path)

- The glow layer goes down and up the existing dual-filter blur chain (`src/render/blur.cpp`, which
  already works on the software renderer) and is added at 20–35 % by hour: strong at night and dusk,
  off at noon except specular glints and lightning. Only emissive pixels bloom, never the whole
  frame, so the pixel art stays crisp.
- **Cost:** GPU < 0.15 ms (the chain's levels sum to about a third of the frame), 8–10 draws.
  **Quality:** Low: off; Medium: 3 levels; High: 5. **Test:** scripted night: luma falls off
  smoothly over 6–20 px around a lantern; pixels beyond 40 px unchanged within 2 levels.

#### P8 Final pass (`gpu` path)

One shader, drawn while scaling the art-resolution frame to the window (nearest at whole zooms,
`SDL_SCALEMODE_PIXELART` during zoom transitions instead of today's linear blur):

1. **Water** (alpha-coded pixels): body colour darkened by depth band → plus the reflection layer
   sampled with a ripple offset in whole art pixels (amplitude by sea state), falling back to the sky
   colour from P0 where the layer is empty → plus foam (art) → plus **sun glints**: a hashed sparkle
   on ripple crests, dense along the sun's side at dawn and dusk, white at noon, moon-silver at night.
2. **Colour grade:** two lookups (32³, 1024 × 32 strips), the current phase and the next, mixed by
   the clock. Each lookup is baked on a worker thread from the region look parameters (§3.5) blended
   by the camera's region weights, only when the weights move by more than 2 % (at most 4 times a
   second). One source of truth, many regions, two texture reads.
3. **Weather modifiers** as uniforms: overcast lowers contrast 25 % and saturation 15 % and cools the
   white balance; a storm darkens 25 % with a grey-green cast; the air after rain is 8 % more
   saturated with half the haze for two minutes; dust adds ochre and haze; lightning adds a 80–150 ms
   blue-white flash with a second flicker (none with reduce motion).
4. **Haze** by screen height and zoom (§2.4), toward the region's haze colour, plus fog density from
   P5's half-resolution fog layer.
5. **Bloom** added from P7.

- **Cost:** GPU ≤ 0.35 ms at 1440p on a mid-range laptop GPU (16 texture reads; measured cost on the
  development machine's GPU below noise). CPU ≤ 0.02 ms per frame, lookups baked off the main thread
  (~0.3 ms each on a worker). **Classic path:** the lookup is reduced to its best affine fit per
  channel (a `MOD` quad and an `ADD` quad), haze as today, no water work.
- **Test:** unit: lookup baking (identity parameters give an identity lookup within 1/255; known
  split-tone values); scripted `--renderer gpu`: the §2.1 statistics per region and hour (Rome,
  Athens, Pārsa, home, a sea lane; dawn, day, dusk, night); a pass-through check that the gpu and
  classic paths agree within 2/255 when the look parameters are neutral.

#### P9 Interface

Unchanged. The glass blur samples the finished frame, so it takes the grade and the dusk with it.

### 3.3 Occluder fade and interiors: evaluation

- **Fade** (P3): high value (the Temple of Vesta problem, QA V-B-003, people behind colonnades),
  trivial cost. **Must-have.**
- **Interiors:** roof-off state sprites (`item/<id>/roof_off/<variant>/f<n>`, the existing state
  scheme) shown when the camera is at 2× or more and the cursor rests on the building. Value: great
  moments (the Apadāna's forest of columns, Athena Parthenos in the Parthenon's cella, a Roman
  taberna, Laeticia's cottage). Cost: art per building of 1/8 to 1/4 page plus interior props; the
  half-resolution shadows (§4.3) free that space. **Nice-to-have, after the must-haves:** Laeticia's
  cottage first (it is home), then the Apadāna, then the Parthenon. No more than six in all.

### 3.4 Budgets

| Pass | CPU ms | GPU ms (mid-range, 1440p) | Draws | Texture memory |
|---|---|---|---|---|
| P0 sky, edges | 0.02 | 0.05 | 3–6 | star, cloud textures 4 MB |
| P2 shadows (sun, tint) | +0.03 | 0.05 | as today | −½ page per city (half-res shadows) |
| P3 sway, fade | 0.05 | — | as today | — |
| P4 reflections | 0.10 | 0.10 | 3–6 | 15 MB target |
| P5 weather | 0.15 | 0.10 | 2–4 | fog layer 4 MB |
| P6–P7 glow, bloom | 0.02 | 0.15 | 8–10 | 5 MB chain |
| P8 final | 0.02 | 0.35 | 1 | two lookups 0.3 MB |
| **Added** | **≤ 0.4** | **≤ 0.8** | **≤ 25** | **≈ 30 MB** |

Today's world frame at 1440p is 0.44–0.78 ms average, 0.9–1.3 ms p99 on the development machine's GPU (the
worldview README). With the additions and a 3–5× slower GPU the busiest view stays near 4–6 ms p99,
inside 8.3 ms. **Draw-call budget:** keep world-tech's ≤ 40 for the scene (P1–P6) and count the post
chain (P7–P8, P0) separately at ≤ 16, plus UI ≤ 16. Post draws are full-screen quads of fixed count;
they cost fill, not CPU.

**Settings slider** (`Look: Classic / Low / Medium / High`, default High where a GPU device exists,
Classic otherwise): Classic is the fallback path; Low: lookup grade, fixed shadows, no reflections,
no bloom; Medium: + moving tinted shadows, sky reflections, bloom 3 levels, fog; High: + mirrored
reflections, moon shadows, bloom 5 levels, dust motes. Reduce motion is independent and wins.

### 3.5 Data the passes read

- **Region look** (replaces `theme.grading` multipliers in `assets/regions/<region>.json`, a contract
  change): per phase (dawn, day, dusk, night) `wb` (rgb), `exposure`, `shadow_tint` and `high_tint`
  (rgb) with `tint`, `contrast`, `saturation`, `shoulder`, optional hue bands (`terracotta`,
  `foliage`, `water`: hue, saturation and value shifts); plus `sky` (three stops), `sun` and
  `shade` colours, `haze` (colour, strength), `stars` density. Defaults per region come from §2.2 and
  the city files' §8 tables; the mock-up parameters in `out/look/mockups/make.py` are a tested
  starting point.
- **Core** (`src/core/look.hpp`, pure, no SDL): parameters → lookup bytes; sun model by clock (swing,
  length, colours); weather → grade modifiers; liveliness metric. Unit-tested.
- **Render** (`src/render/post.{hpp,cpp}`, shared by the island scene and the world view): device
  check, render states, shader blobs, lookups, bloom, final pass, the classic fallback.

### 3.6 Weather system v2

Built on `living-world.md` §6 (cells, wind, sea state) and today's `Weather` (cells, gusts, wetness):

- **Fronts.** Each region's climate and the day plan (deterministic from the seed and the calendar
  day) schedule fronts: a band of 3–6 cells (cloud → rain → storm core → rain → clearing) entering
  upwind and crossing a region in 3–8 game minutes. At most 6 cells per region, 24 in the world.
- **Storms:** strikes every 6–20 s inside the cell; flash (P8), bolt and ground flash (P5); thunder
  delayed by distance from the view centre (0.03 s per tile), the near crack under 15 tiles, rolling
  thunder to 40, a far rumble beyond. Wind rises, sea state goes to 3.
- **Rain and snow** fall only under their cells, slanted by the wind; snow is rain in a snowy season.
  **Snow settles** as a cover value per 8 × 8 block (rises while it snows, melts in sun and by
  season): ground tiles get a snow decal by cover; home items switch to their `@winter` looks by
  cover; city roofs keep their art (a whole winter set per city is out of budget).
- **Sea state** 0–3 per sea area drives the water animation speed, whitecaps (`fx/world.whitecap`),
  foam strength, ripple amplitude in P8 and ship bob.
- **Fog banks** at dawn on low ground and rivers; **dust** in summer in Pārsa and the Syrian steppe;
  **rainbows** after a shower in sunlight, opposite the sun's side, 20–40 s.
- **Weather drives:** grade (P8 modifiers), shadows (sun strength), sound (§5), actors (shelter
  interrupts exist; city crowds thin to 40 % in rain), and events (`living-world.md` §5).
- **Tests:** unit: front scheduling is deterministic per seed and day; storm strike timing; snow cover
  rises and melts. Scripted: `fast` through a front over Rome, asserting the cells' order, the rain
  only under the rain cells, the thunder delays in the captured mix.

### 3.7 Ambient motion and particles

| Source | How | Who supplies |
|---|---|---|
| Smoke from hearths, bakeries, kilns, baths, altars | particle emitters at the geometry's emitter points, leaning with the wind, thicker at meal hours | engine, geometry (exists) |
| Flags, banners, awnings, laundry, sails | 4-frame wind animation (`slack`/`full` by wind strength), mirrored when the wind's screen-x is negative (`living-world.md` §6.2) | art frames, engine |
| Birds | flocks of 8–40 as one fx actor each: starlings wheeling over Rome at dusk, swifts over Athens, storks and hoopoes at Pārsa, gulls at sea, ducks and herons at home | engine, art (2–3 frame flaps) |
| Insects | bees, butterflies (exist), dragonflies over water, moths at lamps (exist), fireflies (exist) | engine |
| Water | animated frames, river flow overlays, ripples, glints, whitecaps | art, engine |
| Foliage | sway (P3), falling leaves and petals by season (exist at home) | engine |
| Light | lamp and fire flicker (P6), window lights switching on through dusk one by one | engine |
| Air | dust motes in low sun (Pārsa, Athens), heat shimmer (High only, off by default, whole-pixel row offsets on paving at noon) | engine |

Particles: ≤ 2 500 live in view, ≤ 0.15 ms CPU per frame. The liveliness test (§2.5) is the
acceptance check.

---

## 4. Art plan

### 4.1 What the generators must supply

| Need | For | Done how |
|---|---|---|
| World set terrain, faces, foam, river flow (QA V-A-001), meeting §2.1 targets | 85 % of the world | art, already queued; this document sets the values |
| Backdrops for the north and east edges, day/night/winter | P0 | art (world set) |
| Star field, two cloud deck textures, cloud shadow blobs, fog strips, lightning bolts (4), puddle decals (4), snow cover decals, whitecaps, rain streaks (3 lengths), dust motes | P0, P5 | art (world set page has about 40 % free) |
| Wind frames for flags, banners, awnings, laundry, sails (≈ 10 kinds per set, 4 frames each) | motion | art |
| Bird flock sprites (starling, swift, stork, gull, heron) | motion | art (world set) |
| Half-resolution shadow sprites | P2, page budget | art tool: render shadows at ½ scale; manifest flags them |
| Roof-off states for up to six buildings | §3.3 | art, nice-to-have |
| **Not needed:** normal or height maps | | see §4.4 |
| **Not needed:** wet variants of sprites | | the engine darkens and adds sheen; puddles are decals |
| **Not needed:** flow maps | | rivers already use directional flow overlays; P8's ripple is procedural |

### 4.2 Vibrancy pass per set: before → after

Each item names the offender, the screenshot, and the target. Re-run the §2.1 statistics on the
art previews after each change.

- **Pārsa** (`worldview/1_parsa_terrace_1x_day`):
  - *Flat roofs*: one beige value over planes of 10–20 tiles. → Mud-plaster mottling in 3 values
    (≤ 6 % apart) with repair patches, a 2-px soft occlusion along the inner parapet edge, dust drifts
    at the parapet feet, stair heads, drains and light wells kept, roof value 6–8 % below the lit wall
    so the lapis frieze band reads as the brightest colour edge. On town houses: rooftop life
    (drying fruit, mats, a ladder, an awning) where the plan allows.
  - *Paving*: a grey grid of equal slabs. → 3–4 slab tones, joints a step darker and thinner, worn
    paths along the processional routes, the grid line contrast halved.
  - *Stone*: high-key, saturation 28 %. → limestone mid-tone `#C9B79C` lit, shade `#8E8597` (cool),
    median luma toward 130.
  - *Mountain and plain*: flat rock cubes. → world-set rock faces and peaks (V-A-001) with
    elevation-lighter tops.
- **Rome** (`worldview/9_rome_1x_day`):
  - *Roofs*: one salmon hue over the city. → terracotta ramp per §2.2 with 3 roof families (new red,
    weathered brown-red, sun-bleached orange) mixed by block; ridges and eaves a step darker.
  - *Tiber*: olive lawn. → river water matching the world river, with mud-bank edges (V-A-004).
  - *Forum square*: a cream plane. → travertine slab tones, worn centre, statue bases' shadow, drains;
    people will do the rest.
  - *Quarter scale grass*: lime. → `rome.grass_spring` toward `#6E9A48` with darker field patches.
- **Athens** (`worldview/4_athens_acropolis_south_1x`, `6_athens_agora_dusk_1x`):
  - *Acropolis rock*: grey rubble terraces without darks. → limestone `#A39A8A` with strong
    crevice darks (luma ≤ 50) and pale lit ledges, so the Parthenon's marble stands 15 % brighter
    than the rock around it.
  - *Asphodel* reads as crowds (V-A-008) → clumps with leaves and a flower spike, green dominant.
  - *Stairs as slabs* (V-A-005) → treads with a dark riser line every step.
  - *Dry grass speckle* → fewer, longer strokes in two golds, larger calm areas.
- **Home**: protect. Meadow: two more grass variants with clover and tiny flowers at low density;
  the engine's macro variation (P1) does the rest.
- **Figures (all sets)** (`out/artgen/athens/walkers_2x.png`): small and beige on beige ground. →
  every walker gets one accent of saturation ≥ 55 % (cloak, sash, headdress, basket) and a coloured
  dark outline on the lower and shaded side (generated procedurally in the art tool), so a figure
  reads at 1× against paving of its own value.

### 4.3 Procedural in the generator vs engine effects

- **In the generator:** ramps and hue shifting from the master table; outlines; mottling and slab
  tones (noise in the voxel colours, deterministic); half-resolution shadows; wind frames
  (vertex-displaced cloth); bird flaps.
- **In the engine:** everything that depends on time, weather or position: grade, sun swing, shadow
  tint, reflections, wetness, macro variation, haze, sway, flicker.

**Page budget** (world-tech §1.2: world ≤ 1 page, Pārsa ≤ 2, Athens ≤ 2, Rome ≤ 3; all at their
limit today). Measured fill: `athens.1` 74 % (83 % of it shadows), `parsa.1` 80 % (52 % shadows),
`rome.2` 82 % (90 % shadows), `world.0` 4096 × 2304 (room for about 1 800 more rows). Half-resolution
shadows cut shadow area by 75 %, freeing roughly 0.5–0.75 page per city, which pays for wind frames,
puddles and interiors without raising the budget. **Propose:** adopt half-resolution shadows before
adding any new art to the city sets.

### 4.4 Normal maps: not worth it

A lighting pass with normals would relight faces as the sun moves. For this art it would double
every page (each sprite needs a normal sprite: 320 MB → 640 MB), and most sprites are 10–40 px tall,
where relit faces read as noise rather than form. The sun swing, the two-light shadow tint and the
grade give the time-of-day drama at no page cost. Revisit only if, after P2 and P8, landmarks at
dawn and dusk still look flat, and then as a per-landmark face mask (top / left / right, one byte
per pixel at half resolution), not full normals.

---

## 5. Sound of weather and atmosphere

What exists (`assets/audio/*/manifest.json`): beds `amb/rain.ogg`, `amb/world/storm.ogg`,
`amb/world/sea.ogg`, `amb/world/mountain.ogg`, `amb/parsa/rain.ogg`, `amb/world/seam.ogg`;
effects `sfx/gust.wav`, `sfx/world/thunder_far.wav`, `sfx/splash.wav`, `sfx/world/gull.wav`.

To match the passes above:

- **Wind by strength:** three beds crossfaded by the shared wind (breeze, steady wind, gale), plus
  gust swells timed to the gust waves already crossing the map, panned by where the wave is.
- **Rain by surface:** light and heavy rain on soft ground, on tiled roofs, on stone paving and on
  water, mixed by the share of each material in view (the count-driven bed rule of `living-world.md`
  §9.1, applied to surfaces); drips and gutters for a minute after rain stops.
- **Thunder:** near crack (3 variants), mid roll (3), far rumble (exists, 2 more variants), played at
  the delay of §3.6 and panned to the strike.
- **Sea by state:** calm lap, waves, rough surf with spray, chosen by sea state and mixed by the sea
  share in view; the existing sea bed becomes the middle layer.
- **Snow:** muffled wind bed; the world's beds lose high frequencies by snow cover.
- **Fog and seams:** the existing seam drone and bed; a soft low bed under dawn fog.
- **Dawn and dusk choruses** per region already exist as events; they key to the sun model.

Levels follow `CLAUDE.md`: beds −21 to −23 LUFS, effects balanced by their loudest 100 ms; weather
beds count toward the 8-loop budget, so wind and rain each take one slot with layers crossfaded
inside it.

---

## 6. Work plan

One agent per task. **Must** tasks give the look; **nice** tasks deepen it. Engine tasks are on a
branch from the integrated game (after `t3/integrate-game-world` lands) and touch only
`src/render/`, `src/worldview/`, `src/core/look.*`, `src/core/weather.*` and their tests.

**Beside the crowds round.** The crowds round edits the actor system. Render tasks E1, E2, E4, E5 and
E6b touch none of it and could run beside it on their own branch, but `CLAUDE.md` allows one agent in
`src/` and `tests/` at a time: running them in parallel needs the orchestrator's exception (§8).
E3's actor reflections and E7's occluder fade for actors touch emission order and should follow the
crowds round, or take a tiny interface from it (the frame's actor sprite list). Art, audio and world
data tasks run beside anything.

Order chosen for visible improvement early: E1 and E2 change every frame everywhere; A1 fixes the
worst offenders in the art that exists; E3 makes the most-seen surface (water) come alive.

| # | Task | Lane | Needs | Must? | Impact | Cost | Acceptance |
|---|---|---|---|---|---|---|---|
| **E1** | `gpu` renderer path with classic fallback; shader toolchain (GLSL + committed SPIR-V); `ABGR8888` for sampled textures; region look parameters → baked lookups (`src/core/look`); P8 grade + haze; coloured shadow composite; settings slider | engine | integration landed; W1 defaults (can start with built-ins) | must | **very high**: every frame, every region | 1.5 days | unit (lookup baking, pass-through agreement); `--renderer gpu` shots meet §2.1 at Rome, Athens, Pārsa, home, a sea lane × 4 hours; bench at 1440p `--renderer gpu` and `opengl`: p99 ≤ 8.3 ms, worst ≤ 16.6, CPU ≤ 2 ms, scene draws ≤ 40, post ≤ 16; software and classic shots unchanged where the look is neutral |
| **E2** | Bloom on glow (all paths), warm additive light pools, lamp and fire flicker, windows lighting one by one at dusk | engine | — (E1 for the High levels only) | must | high: every dusk and night | 0.5 day | night shots: lantern halo falloff, amber pools (r > g); profiler: bloom ≤ 0.15 ms GPU at 1440p |
| **A1** | Vibrancy pass on existing city art: Pārsa roofs and paving, Rome roof families and Tiber, Athens rock, asphodel and stairs, walker accents and outlines | art | — | must | high: the three cities at every zoom | 1 day (three sets; can split by set) | previews meet §2.1 materials; QA V-A-004/005/008 closed; page counts unchanged |
| **E3** | Water: P1 water code, P8 water (depth, sky, glints, ripple), P4 mirrored reflections of items and lights (actors after the crowds round), sea beyond the edges | engine | E1 | must | high: sea, rivers, ponds, the Tiber, night lights | 1 day | lamp-by-the-pond night script (§3.2 P4); dusk sea shot with rose and violet in the water; bench as E1 |
| **A2** | Half-resolution shadows in the art tool and manifests, all sets re-baked | art | contract change confirmed (§8) | must | medium (softer shadows) and frees ½–¾ page per city | 0.5 day | pages shrink as measured; shadow shots compare within tolerance; coverage test green |
| **E4** | Sun model: shadow swing and length, half-res shadow drawing, moon shadows, cloud shadows in the world | engine | E1, A2 | must | medium-high: dawn and dusk drama | 0.5–1 day | Parthenon at 07:00/12:00/18:00 (length ratio ≥ 2.5; noon shade blue) |
| **E5** | Sky and edges: P0 gradients, sun and moon, stars, cloud decks, backdrops, the sea continuing past the edges, haze by zoom | engine | E1; A3 for backdrops (placeholder strips until then) | must | high when zoomed out (QA V-D-001) | 1 day | corner shots at ½ and ¼; no flat clear colour; overview haze |
| **A3** | World set atmosphere sprites: backdrops (north and east, day/night/winter), stars, clouds, fog strips, bolts, puddles, snow decals, whitecaps, rain streaks, flocks | art | — | must | enables E5, E6 | 1 day | coverage test; previews |
| **W1** | Region look parameters for every region and stretch (§3.5 schema), sky stops, haze; climates gain storm, fog and dust frequencies | world data (each layer's builder; defaults by worldgen core) | schema confirmed (§8) | must | tunes E1 per place | 0.5 day | `build.sh --check` validates; §2.1 statistics per region |
| **E6a** | Weather v2 core: fronts, storms and strike timing, sea state per area, snow cover, fog and dust cells, weather → grade modifiers | engine (core) | — | must | dynamic skies everywhere | 1 day | unit tests (§3.6); determinism check unchanged |
| **E6b** | Weather v2 render: slanted rain and snow, lightning flash and bolts, puddles and wet sheen, fog strips, whitecaps, rainbows; the weather beds wired | engine | E1, E3, E6a, A3, S1 | must | high in any rain | 1 day | shower script (§3.2 P5); storm script with captured thunder delays; bench in rain at 1440p |
| **S1** | Weather and atmosphere audio set (§5) | audio | — | must | completes E6 | 1 day | loudness and loop checks of `tools/audiogen`; mixer capture in E6b |
| **E7** | Ambient motion: sway in the world, flag and awning frames by wind, smoke emitters, bird flocks, occluder fade, the liveliness metric and its test | engine | A4; after the crowds round for actor fade | must | high: "alive" | 1 day | liveliness ≥ §2.5 in city, countryside and sea views; fade script |
| **A4** | Wind frames for flags, banners, awnings, laundry, sails; flock sprites | art | A2 (space) | must | enables E7 | 0.5–1 day | previews; pages within budget |
| E8 | Interiors: roof-off states for Laeticia's cottage, the Apadāna, the Parthenon (then at most three more) | art + engine | A2, E7 | nice | high delight, narrow reach | 1 day + 0.5 | hover at 2× shows the interior; pages within budget |
| E9 | Heat shimmer, dust motes, moonlight path on the sea, night mist | engine | E1, E3 | nice | atmosphere | 0.5 day | High only; bench unchanged within 0.1 ms |
| E10 | Face mask experiment for landmarks at dawn and dusk (§4.4) | engine + art | after E4 | nice | maybe | 0.5 day probe | decide from shots |

Every engine task ends with the build warning-free and `ctest` green under `release` and `asan`, the
worldview bench cases (Pārsa terrace, Agora at dusk, Acropolis at night, pan, flight, overview) at
1080p, 1440p and 4K on both paths, and the soak run flat in memory.

---

## 7. Mock-ups

Paint-overs from existing frames, made with `out/look/mockups/make.py` (numpy and Pillow).
**They are mock-ups, not engine output.** Every per-pixel step in them is what one lookup does in P8;
every spatial step (bloom, reflection, light pool, haze, cloud shadow, mist) is one of the passes
above. Each comes as `…_before.png`, `…_after.png` and `…_compare.png` (before on top).

- **Home pond at dusk** (`out/look/mockups/pond_dusk_compare.png`). Before: the game at dusk,
  headless (`src_pond.lcs`). After: graded from a day frame of the same view, as the engine grades
  its ungraded frame (the ducks moved between captures). Shows the warm sun side against a violet far
  side, the dusk sky in the pond with sunset glitter, an amber lamp pool instead of a lime one, a
  lantern with bloom, fireflies. Median luma 73 → 45, cool pixels 3 % → 9 %.
- **Roman Forum at midday** (`forum_midday_compare.png`). Before: `worldview/9_rome_1x_day`. After:
  deeper terracotta, cooler shade, a highlight shoulder on travertine, two drifting cloud shadows, the
  domus pool holding the noon sky, light smoke haze over the far city. p2 55 → 28, p98 230 → 216.
- **Pārsa terrace at dawn** (`parsa_dawn_compare.png`). Before: the day frame through the engine's
  own dawn grade (the clock's dawn ambient × Pārsa's dawn keyframe, then its haze lean), not a
  captured frame. After: cool violet paving, honey-gold on the sunlit walls, lapis and cinnabar kept
  vivid while plain stone is calmed, morning cloud dapple breaking up the flat roofs, mist on the
  plain, torches still burning. p98 162 → 200.

What they cannot show: shadows changing direction and length, any motion, mirrored landmarks (the
pond's reflection is approximated per column), and the art changes of §4.2 (the roofs are still
the roofs, which is the point of A1).

---

## 8. Decisions to confirm

1. **Renderer path:** `gpu` driver primary (Vulkan, SPIR-V), `opengl`/`software` as the classic
   fallback. Linux and Windows; macOS not covered unless asked.
2. **Committed shader blobs:** GLSL sources and compiled SPIR-V both in the repo, `glslc` only to
   regenerate. This is the written justification for the toolchain step; nothing is added at run
   time.
3. **Texture format** for anything shaders sample becomes `ABGR8888` (the engine's `kTextureFormat`
   is `ARGB8888` today).
4. **Half-resolution shadow sprites** (art contract change in `CLAUDE.md` and world-tech §1.5):
   frees ½–¾ page per city and gives soft edges.
5. **Draw-call budget split:** scene ≤ 40, post chain ≤ 16, UI ≤ 16.
6. **Region file schema:** `theme.look` replaces `theme.grading` (§3.5).
7. **Sun stays screen-relative**, swinging ±25° through the day.
8. **Engine lane:** an exception for render-only tasks (E1, E2, E4, E5, E6b) to run beside the crowds
   round on their own branch, or run them after it.
9. **Interiors:** confirm the first three (Laeticia's cottage, the Apadāna, the Parthenon) or drop
   them.
