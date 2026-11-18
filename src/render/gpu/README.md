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
| `src/worldview/world_lights.hpp` | the world data's lights (`lights.profiles`, `light_points`) by map chunk |
| `src/app/app_gpu.cpp` | renderer choice and fallback, the bench's tier cases |

## A frame

1. **Scene**: the world (cells, items, landmark pieces, actors, the home through its hooks) into
   the world target as today, but in neutral daylight: no ambient multiply, no glow in it. Trees,
   vines, reeds, crops and small plants are bent in four strips by one world-wide wind with gust
   crests rolling downwind (their stepped wiggle frames dropped); banners, awnings and parasols
   lean and keep their own frames. SDL's renderer takes custom fragment shaders only, so the bend
   is in the vertices (ten per swaying sprite), on the CPU, a few microseconds a frame.
2. **Lights**: one pool per burning light of the visible chunks (and the home's lamps) into the
   light target, additive: an ellipse on the ground `(1 - (d/R)^2)^2` (R the profile's radius in
   tiles) below the pool's centre and reaching up the walls behind to near the flame's height
   above it. Colour, strength, hours (with `dusk`/`dawn`, windows and doors lit one by one), rain
   (`dim`, `out`) and flicker by style (`steady`, `gutter`, `breathe`, `leap`, depth ≤ 0.08) come
   from the region files.
3. **Glow**: glow layers (only of items the data lights, in regions with light points), the
   coarse levels' glow and, at the overview, every light as a warm point, into the glow target.
4. **Bloom**: dual-filter halvings of the glow target (3 levels on Low, 5 on Medium and High) and
   back up.
5. **Final** (onto the window over the region's three-stop sky): the shadow layer's coverage
   tints shade toward the regions' `theme.look.shade` (shade is the sky's colour); the grade
   (white balance and exposure, split toning, an S-curve and shoulder on lightness, midtone
   saturation, then the cool low-light shift at night); lamp light added as `albedo × light` plus
   a warm share, in six bands dithered by a 4 × 4 Bayer cell anchored to world art pixels (no
   crawl when panning); haze by zoom; the glow layer sharp and its bloom. Sampled "sharp": whole
   texels stay whole and a camera between window pixels glides by one blended pixel at texel
   edges, never by a blur.

## Tiers in this round

| Tier | Draws |
|---|---|
| Classic | today's frame |
| Low | grade, cool shade, lamp pools, glow, 3-level bloom, sway |
| Medium | Low with 5-level bloom |
| High | as Medium; its own passes (height-field shadows, reflections) need the packed pages of task A1 |

## Shaders

`cmake --build --preset release --target shaders` recompiles the SPIR-V with `glslc` (pinned:
shaderc 2026.4, the system package here); the `shaders_fresh` test fails when a blob is stale and
skips with any other glslc. Interface (SDL 3.4): input location 0 colour, 1 uv; the drawn texture
at set 2 binding 0 and the extra samplers after it (SDL 3.4.20 takes at most five); uniforms at
set 3 binding 0. Every texture a shader samples is `ABGR8888`. Sampler bindings and uniforms are
fixed per render state, so each pass and bloom level has its own state.

## Headless and teardown

The windowless `gpu` renderer has no window (the offscreen video driver's Vulkan has no surface):
it draws into a texture the window's size, which stands in for the window (`App::screenTarget`).
GPU objects go before the renderer: `Post` is owned by `WorldView`, which the app destroys
before its renderer, and its destructor flushes queued draws before releasing its states.
