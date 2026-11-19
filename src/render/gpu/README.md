# src/render/gpu: the shader path (graphics plan task E1)

The Look setting's tiers above Classic (`docs/design/graphics-plan.md` §3), on SDL's `gpu`
render driver with custom fragment shaders (SDL ≥ 3.4). Classic is today's frame on any
renderer and the fallback wherever this path cannot be made; headless runs stay on it unless
`--quality` asks otherwise, so every software-rendered screenshot test is unchanged.

## Files

| File | What |
|---|---|
| `look.hpp` | pure: tiers, the region grade from `theme.look` (per phase, blended by clock, region weights and season), the wind's lean, flames' flicker |
| `post.hpp` | `Post`: shaders, sampler, render states, the light, glow and bloom targets, the final pass; `createRenderer` (the `gpu` driver on Vulkan with SPIR-V) |
| `tuning.hpp` | every number of the path |
| `assets/shaders/*.frag` + `.spv` | GLSL sources and their SPIR-V, both committed; `cmake/embed_shaders.cmake` embeds the blobs |
| `src/worldview/renderer_gpu.cpp` | the world renderer's half: grade per frame, pools, glow, bloom, sway, the composite |
| `src/worldview/world_lights.hpp` | the world data's lights (`lights.profiles`, `light_points`) by map chunk; festival nights from city life |
| `src/app/app_gpu.cpp` | renderer choice and fallback, the bench's tier cases |

## A frame

1. **Scene**: the world (cells, items, landmark pieces, actors, the home through its hooks) into
   the world target as today, but in neutral daylight: no ambient multiply, no glow in it. The
   shadow layer is laid on where the classic composite is, by multiplying with the classic
   darkening in the region's `theme.look.shade` colour (`shade.frag`), so everything drawn after
   it covers it exactly as it covers a black shadow: shade is the sky's colour only where a
   shadow falls. Trees, vines, reeds, crops and small plants are bent in four strips by one
   world-wide wind with gust crests rolling downwind (their stepped wiggle frames dropped);
   banners, awnings and parasols lean and keep their own frames. SDL's renderer takes custom
   fragment shaders only, so the bend is in the vertices (ten per swaying sprite, on the CPU).
   Water tiles stay still in the cells and are **marked**: the cell's alpha is lowered a step
   (to 0.98) under them by a blend that keeps colour (`Post::markBlend`), one blend switch per
   diagonal; anything drawn over water later restores alpha 1 (the home's pieces through
   `Post::coverBlend`, so one drawn faintly, a ghost or a fade, does too). The home's ground
   goes over the world's rim tiles under it once `Post::cut` (`cut.frag`) has taken their alpha
   away where it covers them, so its water keeps its marks up to the home's last row. The tile
   **water field** round the view (shore distance, river flow, flags and level; at most 512², rebuilt on
   a worker as the view pans) feeds the final pass.
2. **Lights**: one pool per burning light of the visible chunks (the list cached and rebuilt on
   a chunk crossing, an hour step or every 30 frames; flicker per frame), the home's lamps and
   city life's actors who carry a light, into the glow target's alpha (stored at 0.4 so
   overlapping flames do not clip; ONE/ONE/ADD on alpha), additive: an ellipse on the ground `(1 - (d/R)^2)^2` below the pool's centre, and
   above it a fade up the walls behind to half strength at near the flame's height. Colour,
   strength, hours (with `dusk`/`dawn`, windows and doors lit one by one), rain (`dim`, `out`),
   festivals (brighter, or lit only that night; `only: event:<id>` while the event runs) and
   flicker by style come from the region files.
3. **Glow** (the same target's rgb): glow layers (only of items the data lights, in regions with light points), the
   carried flames as points, the coarse levels' glow and, at the overview, every light as a warm
   point, into the glow target.
4. **Bloom**: dual-filter halvings of the glow target (none on Low, 3 levels on Medium, 5 on
   High) and back up. **Clouds** (`clouds.frag`, a quarter of the target, one draw; cleared once
   when the sky is empty or the setting is Off): the weather field's cells shaped by drifting
   noise, red the deck seen, green its shadow offset toward the sun. **Mean**: the world target
   sampled to 64 × 32 and halved to one texel, one level a frame.
5. **Final** (onto the window over the region's three-stop sky): exposure toward the hour's key
   from the scene's mean (by day never darker than the art; night lifted or held to one key); the
   grade (white balance and exposure, split toning whose cool darks come only with twilight and
   night, an S-curve about the scene's own middle by day, a shoulder, saturation never below the
   art's by day, a warm lift in sunlit highlights, a low sun's warmth at dawn and dusk, then the
   cool shift of low light at night); lamp light screened on as its amber share plus a little of
   the albedo, in six bands dithered by a 4 × 4 Bayer cell anchored to world art pixels; haze by
   zoom and hour that leans only what is lit (thin near by day); the glow layer sharp and its
   bloom. Before the grade, open water (marked pixels) is redrawn in layers from the field:
   depth bands, a ripple advected along the flow in two cross-faded phases, rain rings, on High
   what stands at its edge mirrored and fading; after it the sky in the water, the shore line,
   foam and glints. Cloud shadows lower the sunlight in dithered steps; the deck goes over
   everything in three posterised steps, thin near and fuller far. Sampled "sharp": whole texels stay whole, a camera between window pixels glides by one
   blended pixel at texel edges, never by a blur.

## Tiers in this round

| Tier | Draws |
|---|---|
| Classic | today's frame |
| Low | grade, cool shade, lamp pools, glow (no bloom), sway, water in 3 bands, clouds |
| Medium | Low with 3-level bloom and 4 water bands |
| High | Medium with 5-level bloom and water reflections; height-field shadows wait for the packed pages |

## Shaders

`cmake --build --preset release --target shaders` recompiles the SPIR-V with `glslc` (pinned:
shaderc 2026.4, the system package here); the `shaders_fresh` test fails when a blob is stale and
skips with any other glslc. Interface (SDL 3.4): input location 0 colour, 1 uv; the drawn texture
at set 2 binding 0 and the extra samplers after it (SDL 3.4.20 takes at most five); uniforms at
set 3 binding 0 (the final pass uses all five: glow, bloom, mean, water field, clouds).
Every texture a shader samples is `ABGR8888`. Sampler bindings and uniforms are
fixed per render state, so each pass and bloom level has its own state.

## Headless and teardown

The windowless `gpu` renderer has no window (the offscreen video driver's Vulkan has no surface):
it draws into a texture the window's size, which stands in for the window (`App::screenTarget`).
GPU objects go before the renderer: `Post` is owned by `WorldView`, which the app destroys
before its renderer, and its destructor flushes queued draws before releasing its states.
