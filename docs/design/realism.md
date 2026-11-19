# Realism: the next techniques, ranked

What comes after the graphics plan's E3 to raise realism and atmosphere per millisecond while the
frame stays hand-made pixel art. It builds on `docs/design/graphics-plan.md` (the data contract,
the pass order, tiers E1–E11), `docs/design/quality-bar.md` (golden scenes G1–G12, M1–M5, the
numbers) and the studies behind them; it does not repeat them. Where this document and the plan
differ on a pass that both describe, this document's version is the proposal and the plan stays
in force until the owner or the orchestrator adopts it. Evidence (offline experiments on frames
composed from the committed packed pages, sources, open questions): the untracked report
`out/reports/realism-research.md` with stills under `out/reports/shots/realism/`.

Contents: 0 on one page · 1 the one new piece of infrastructure · 2 the techniques, ranked ·
3 the pixel-art rules these techniques must keep · 4 cost per tier · 5 what the art generator must
add · 6 order of work after E3 · 7 what not to do.

---

## 0. On one page

The plan's E4–E7 make light move (relight, sun path, height-field shadows, water, weather). What
it does not yet have is light that *meets things*: lamps whose light stops at walls and throws
people's shadows, sky light that is weaker in a narrow street than on an open square, leaves and
awnings that glow when the low sun is behind them, water whose colour comes from depth and whose
surface catches the sun, ground that shines when wet and holds snow in the shade. Each of those is
a cheap test against the data the packed pages already carry, provided the engine keeps **one
top-down height field per chunk** (§1) beside the screen buffers. Measured on the offline frames:

| # | Technique | What it adds | GPU at 1440p (High) | Tier |
|---|---|---|---|---|
| R1 | Lamps in 3D with visibility | night pools stopped by walls; people throw shadows away from lamps; windows light the street | 0.15–0.25 ms | Medium (8 steps), High (14) |
| R2 | Sky visibility and bent-normal sky light; soft sun penumbra | narrow streets, wall feet, courtyards and under-canopy darker by enclosure; sky light with a direction; shadows hard at the caster, soft far away | ≈ 0 per frame (baked into cells) + 0.05 actors; penumbra free inside E5's march | all (baked) |
| R3 | Water shading v2 | colour from depth over a bed, a Fresnel-weighted mirror broken by flowing wave normals, caustics in sunlit shallows, glints when the sun nears the view's mirror | 0.25–0.4 ms (water pixels only) | Medium without the mirror, High |
| R4 | Translucency and wrap for leaves, grass and cloth | backlit canopies glow at their rims instead of going dark at every dawn and dusk; leaf flicker; gusts that silver the grass | 0.04 ms | all |
| R5 | Wet ground and puddles | porous ground a step darker, wet paving mirroring figures, puddles in low and enclosed ground reflecting the street | 0.1–0.3 ms while wet | Medium (sheen), High (puddle mirror) |
| R6 | Snow that builds and thaws by light | partial cover by facing and shelter, drifts at wall feet; thaw first where the day's sun reached, so snow lingers in the shade of buildings and on the shaded roof slope | ≈ 0 per frame (exposure baked) | all |
| R7 | One bounce from sunlit surfaces | warm street light on the feet of shaded walls, coloured spill near bright walls | 0.1 ms | High |
| R8 | Image formation | light colour applied at ~45 %, per-light graded tables, a hue-keeping shoulder, split tone by the light's temperature, bloom from glow only | ≈ 0.01 ms | all |

**The three the owner would notice most:** R1 (night stops looking like a tinted overlay and starts
looking lit), R3 (the river and harbours read as water with depth and a surface), R4 with R2
(every low sun currently turns canopies and streets into flat dark shapes; with these they glow
and recede). R6 is the most *storytelling* one: a thaw that follows the shadows of buildings.

**The generator must add** (§5): a small *occlusion-tops* page per item and rotation (top height,
underside height and a material code per 4 × 4 px of ground), per-ramp response fields in
`ramps.json`, and a facing on door and window light points. The packed word itself stays as A1
built it.

---

## 1. The top map: one height field per chunk, top-down

Every technique below asks the same question: *what stands between this point and that
direction?* The plan answers it in screen space (march along the screen through each pixel's
height, with a thin-shell guess because a screen height says nothing about how deep a thing is).
In 2:1 iso that guess fails exactly where realism lives: a wall is a thin shell on screen but solid
in the world; an arcade's floor is under a roof that the screen marks as the roof's height. A
**top-down height field** answers it in world space: columns are solid from the ground to their
top, so no shell is needed, and directions are true 3D directions.

- **What it is.** Per streamed chunk (the same chunks the cells use), a texture over the chunk's
  ground area at **4 art px per texel** in world X and Y (an eighth of a tile; the offline study
  used 2 px, and 4 px matches the occlusion-tops pages of §5.1) (the generator's voxel axes:
  `sx = X − Y`, `sy = (X + Y)/2 − Z`, `h = Z`), RG16: `top` = highest surface (px), `under` = the
  lowest underside above the floor where something overhangs (arcade roof, bridge deck, awning,
  canopy; 0 where nothing does), plus an R8 material code of the top (solid, foliage, cloth,
  water). A max-mip chain of `top` (Tevs, Ihrke & Seidel 2008) lets marches skip open air in big
  steps.
- **Built from.** The occlusion-tops pages (§5.1) splatted with max at each item's placement and
  level, plus terrain levels; built on the worker with the cell (static), the actors' tops
  splatted each frame into a small separate overlay (8 px texels, a few hundred quads). Until §5.1
  exists, splat the visible packed pixels (`X, Y` from screen and `h`): the offline study did
  exactly that and it works except under overhangs and behind tall buildings (holes filled by the
  neighbours' max).
- **How a march uses it.** A ray from `P + 3n` toward direction `D` samples `top` at
  `P.xy + D.xy·t`; it is blocked where `top > P.z + D.z·t` *and* (`under` = 0 or
  `under < P.z + D.z·t`). That one rule lets sun and lamp light pass under arcades, bridge decks
  and colonnade roofs and through doorways.
- **Memory and cost.** A 64 × 64-tile chunk is 2 048 × 2 048 px of ground → 512² texels × 5 B ≈
  1.3 MiB; the resident ring round a view (3 × 3 chunks at 1×) ≈ 12 MiB, which fits beside the
  plan's look targets (≈ 75–90 MiB on High) inside its stated 96 MiB only if the reflection and
  bloom targets stay at their measured sizes; otherwise the look-target budget grows by 16 MiB
  (recorded for `CLAUDE.md` "Performance" when R0 lands). Build: a splat per item, ≈ 0.2 ms per
  chunk on the worker.
- **Acceptance.** Debug view (script verb `look topmap`) on G4: every building a solid block of its
  roof height; arcades and the bridge decks of G5 carry `under`; no hole where the screen showed
  ground behind a tall building after the fill.

---

## 2. The techniques, ranked

Order is effect per millisecond on the owner's ask ("light behaves like light", "water behaves
like water", "nothing pale, flat or stale", four seasons). Each entry: what it adds · data
(have / must add) · algorithm · cost and tier · risks · acceptance.

### R1. Lamps in 3D, stopped by walls

**Adds:** night light that behaves like light: pools that end at walls and spill through doorways,
figures and props that throw shadows away from each lamp, walls lit only on the side that faces
the flame.

**Data.** Have: the light list (`theme.look.lights`, `light_points`, geometry `lights`, carried
lights), `h` and the normal per pixel, the top map. Must add: a facing (`dir`) on door and window
light points (§5.3), so their light goes out into the street rather than along their own wall.

**Algorithm.** One additive quad per light, as E1 draws, but the fragment shader computes:

1. The pixel's world point `P` (`X, Y` from screen position and `h`; `Z = h`), the light at `Lp`
   (its emitter's place and height).
2. `V = Lp − P`, `d = |V|`; falloff `(1 − (d/R)²)²`; facing `clamp((n·V̂ + w)/(1 + w))` with
   `w = 0.25` (wrap, so the terminator is soft); a cone `smoothstep(cos θo, cos θi, dir·(−V̂))`
   for door and window lights.
3. Visibility: 8 (Medium) or 14 (High) samples from `P + 3n` toward `Lp` through the top map,
   skipping the last 6 px before the light; soft by the smallest clearance over distance,
   `vis = min(vis, clamp(0.5 + clearance/(0.06·t + 1)))`; actors' overlay included, so a
   figure between a lamp and the paving leaves a dark streak behind it.
4. Accumulate into the light target at **art resolution** (half the window at 2×, a third at
   3×), depth-aware upsample in the resolve.

The resolve then adds lamp light **after** the ramp snap, as the plan already orders it (relight
by sun and sky in exposure-normalised space, snap, colour from the graded table, then
`albedo × light` in 6–8 dithered bands plus the small warm term). The offline study found two
rules that make this read:

- **Snap after exposure.** The sun-and-sky relight must be divided by the hour's exposure *before*
  the snap; otherwise every moonlit pixel lands below its ramp's darkest step and the night loses
  its value structure (unlit IQR collapses). Night darkness then comes from the graded table.
- **Bands, not a gradient, but enough of them.** Six bands made visible plateaus on wide pools;
  use 8 for pools wider than 3 tiles.

**Cost.** Per lit pixel `lights × samples`; a city view at night: ≈ 40 % of the art pixels inside
some pool, 2 lights each on average, 14 samples, at art resolution (¼ of the window at 2×): ≈ 10 M
dependent fetches → **0.15–0.25 ms** at 1440p on the test GPU (calibrated on the R&D shadow
march, ≈ 0.03 ms per sample per full-resolution pixel). Medium: 8 samples, ≈ 0.1 ms. Low: today's
pools (no visibility). CPU: unchanged (the cached pool list).

**Risks.** Lights inside a sprite's own volume (a lantern under an eave) self-occlude: start the
march past the light's own item (skip its tiles in the top map, by item id in the material
channel's spare values, or the last 6 px). Hundreds of window lights: cap per view by brightness
and distance (the pool cache already sorts them).

**Acceptance.** G7 and the Forum at 22:00: (a) behind any wall that stands between a lamp and the
ground, the ground's luma is within 5 of the unlit ground nearby on ≥ 80 % of the shadowed
pixels; (b) each figure within 2 tiles of a lamp has a shadow streak ≥ 6 px long on the side away
from it; (c) window light lands on the street in front of the window, not on its wall; (d) the
bar's night numbers still hold (warm-lit 2–8 %, unlit IQR ≥ 12, median 22–45).

### R2. Sky visibility, bent-normal sky light, soft penumbra

**Adds:** enclosure at every scale (streets darker than squares, courtyards and wall feet deep,
the ground under a canopy dim), sky light that comes from where the sky is open (bluer from above,
warmer from the sun's side of the sky), and sun shadows that are sharp where they leave the caster
and soften with distance.

**Data.** Have: normal and `h`; the top map (§1). Nothing new from the generator.

**Algorithm (horizon-based, after Jimenez et al. 2016 and Bavoil et al. 2008, in world space).**

1. For each texel of the cell (static content), 8 directions in world XY; along each, the top map
   at radii 3, 7, 14, 28, 56, 96 px from `P + 4n`; keep the largest `tan = (top − P.z)/r`; a
   face's own plane hides the half of the sky behind it (`tan ≥ −(n_xy·d)/n_z`).
2. Per direction the open arc is from the horizon to the zenith: `open = 1 − sin(horizon)`;
   visibility `V` = mean of `open`; bent normal = normalised sum of `open ×` the middle direction
   of the open arc.
3. Sky light in the resolve: `sky(bent) · V · 1.15`, where `sky(b) = mix(horizon, zenith, b.z) +
   sunSide · max(0, b·sunXY)`, colours from the region's `theme.look` by hour. This replaces the
   plan's `0.62 + 0.38·n_z` hemisphere term and its separate enclosure bake; the plan's live
   contact AO stays for actors only.
4. **Bake** `V` (8 bits) and the bent normal (2 × 8 bits, octahedral) into the cell companion
   when the cell builds (static geometry does not change); actors and their surroundings get a
   live 8-sample version (radii 2–8 px) in the shadow pass.
5. Soft sun shadow: E5's march runs through the top map instead of the screen, with
   `vis = min(vis, clamp(0.5 + clearance/(k·t + 1)))` (Quilez's min-ratio soft shadow; `k` =
   0.08 gives a penumbra that widens with distance like a sun of ≈ 0.5° plus scattering). With a
   max-mip, 32 jittered samples cost what 12–16 plain ones did.

**Cost.** Baked: a cell build does 48 lookups per texel at quarter resolution (≈ +10 % cell build,
the figure the plan already reserved for its enclosure bake); per frame 0 plus ≈ 0.05 ms for the
actors' live term. The penumbra is free inside E5's march; the top-map march with max-mip is ≈ 0.2
ms at half resolution against E5's 0.3–0.5.

**Risks.** Too dark: in the experiment the street's shaded walls fell near the ramp floor until
the sun was held to ≈ 1.5× the sky (the plan's 1.8× with exposure on the unshadowed median is the
same rule) and the snap kept a floor of 0.55 × the darkest step. Keep the bar's rule that the
darkest values sit in occlusion, but never black: nothing below the ramp's darkest step × 0.55.

**Acceptance.** G4 at 10:00: median luma of the street floors between buildings ≤ 0.85 × the
open square's; occluded median < cast-shadow median (`quality-bar.md` §4.1); no pixel of a lit
material darker than its darkest step × 0.55; G6 at 07:30: the Parthenon's shadow edge sharp
(≤ 2 px transition) at its base and ≥ 6 px soft at its far end.

### R3. Water shading v2

**Adds:** water that has depth (colour from how much water lies over a sandy or silty bed), a
surface (wave normals moving with the flow, so the mirror and the sky break up the way water
does), light under it (caustics in sunlit shallows) and on it (glints).

**Data.** Have: the water ramp class, the tile water field (shore distance, flow), the mirror
march (E2 on High), the cloud deck. Must add: per water ramp a `bed` colour and an `absorb` triple
in `ramps.json` (§5.2). The coverage gaps the owner's screenshots show are content and engine
work, listed here because they decide what the owner sees: the Portus basin and the home pond
still draw the art's water (the basin appears to be water drawn inside the landmark's own
sprite rather than water terrain, so the marking pass never sees it: R3 confirms and marks it by
the water ramp class; the home scene is not marked, `engine-gfx-e2.md` §R3.7), and water at different levels shows as boxes with pale
sides (needs falls and rapids faces, §5.4).

**Algorithm (resolve, water pixels only).**

1. **Wave normals:** a sum of 6–9 directional waves on the ground plane, domain-warped
   (`X + 6·sin(0.05·Y)`), wavelengths 8–60 px, amplitudes falling ×0.62 per octave, advected
   along the tile flow with the plan's two-phase cross-fade; `n = normalize(−∂h/∂X, −∂h/∂Y, 1)`.
   Calm near banks (amplitude × `smoothstep(0, 12 px, shore distance)`); stronger with wind.
2. **Fresnel:** the iso view is one direction, `v = (1,1,1)/√3`, 54.7° from vertical, where flat
   water reflects ≈ 5 %. The wave normals vary it; the stylised strength is `3 × Schlick(n·v)`
   capped at 0.6, so reflections read without turning the river into a mirror.
3. **Under the surface:** `bed · exp(−absorb · depth) + body · (1 − exp(−absorb · depth))`, depth
   from the tile shore field in world distance (not screen distance: the screen-space version drew
   octagonal rings); `absorb` takes red first (2.4, 1.0, 0.65 per 70 px), so shallows go
   green-gold and depths blue.
4. **Caustics:** in the shallow band (`depth < 1/3`) and only where the sun reaches (the sun
   march's result), a pattern of two warped sine networks, `clamp((|sin a|·|sin b| − 0.55)·3)`,
   advected slowly, adding ≤ 25 % of the sun term.
5. **Mirror:** the existing march, offset by the wave normal's x in whole art pixels; lamps as
   vertical streaks (the plan's E6).
6. **Glints (from the slope statistics of a wind-roughened sea, Cox & Munk 1954):** a pixel glints
   when `(reflect(−S, n)·v)^600 > 0.6` and the sun reaches it. Because the camera is
   orthographic there is **no glitter path**: every water pixel sees the sun from the same angle,
   so glints spread over all the water, densest when the sun is near the mirror of the view
   (behind the view at ≈ 35° elevation, which is where the plan's sun path goes in the morning and
   evening) and absent when it is far from it. Measured at 6.7° from the mirror: 1.9 % of water
   pixels glint; the bar allows ≤ 1 %, so the threshold or the wave amplitude goes down in tuning.
7. **Back onto the water ramp:** lightness picks a step on the pixel's own water ramp with the
   world dither; two thirds of the ramp colour plus one third of the computed colour keeps the
   mirror's hue (a pure snap lost the reflections' colour).

**Cost.** ALU for the waves ≈ 0.02 ms; the mirror is the cost: E2 measured ≈ 0.7 ms at 1× walking
40 steps per water pixel. A column max-mip of `h − d/2` (the reflection test) lets the march stride
8 px through open sky and refine: ≈ 0.2–0.3 ms. Medium: steps 1–4, 6, 7 without the mirror (sky
and clouds only). Low: E2 as it is.

**Risks.** Smooth gradients from the wave field (the first attempt read as corrugated metal and
as a soft render): always snap to the water ramp, keep strokes in whole pixels, prefer broken
domain-warped waves to clean sines. Rivers must not lose their identity: a muddy river keeps its
silt bed colour in `ramps.json`.

**Acceptance.** G2, G5, G10 and the Ostia view: ≥ 3 depth bands, shallow lighter and more
saturated (bar §5.1); glints 0.3–1.0 % of water pixels with the sun within 15° of the view's
mirror and < 0.05 % beyond 40°; caustics only in sunlit shallows (none in cast shadow, none at
night); mirror offsets in whole art pixels; M3 continuity holds; every water body in G2 and the
Portus basin drawn by this path (no art water left on the shader path).

### R4. Translucency and wrap for leaves, grass and cloth

**Adds:** with the plan's sun through the back of the view, every dawn and dusk is backlit; opaque
canopies facing the viewer go dark and flat. Light through leaves gives them glowing rims and a
lit interior, grass a thin golden sheen, awnings colour. Leaf flicker and gust silvering make the
wind visible in the light, not only in the sway.

**Data.** Have: ramp class and `shell` (foliage 6, cloth 2), normal, the sun's visibility. Must add
(§5.2): per ramp `translucency` (0–1) and a transmission colour (`trans`, e.g. yellow-green for
leaves, the cloth's own colour for awnings).

**Algorithm (after Barré-Brisebois & Bouchard 2011 and the wrap term of Green 2004).**

- Thickness proxy: distance (px) from the pixel to its sprite's silhouette within the same class
  group, by an 8-tap ring test in the scene pass (capped at 8); `T = exp(−dist/shell') ·
  (0.35 + 0.65·max(0, −n·S))`, with `shell'` = 9 for foliage, 3 for cloth.
- Transmitted light: `sun · T · translucency · sunVis · (0.4 + 0.6·max(0, −S·v)) · trans`, added
  before the snap (it moves pixels up their own ramp; the ramp's hue shift does the rest).
- Wrap on foliage: `sun · clamp((n·S + 0.5)/1.5) · 0.35 · sunVis`.
- Grass: `sun · 0.22 · max(0, −S·v) · sunVis · trans(grass)`.
- **Leaf flicker:** for foliage pixels, a world-anchored value noise advected by the wind,
  ±1 ramp step only (never more), its rate by wind strength: the canopy twinkles in a breeze.
- **Gust silvering:** where a gust crest passes (the E1 wind field already has crests), grass
  ramps move one step lighter and a little cooler for 0.4–0.8 s (blades bent show their undersides);
  bands roll downwind across meadows and crops.

**Cost.** The ring test only on foliage and cloth pixels (≈ 15 % of a view): ≈ 0.04 ms; the rest
is ALU. All tiers.

**Risks.** Glow everywhere at noon: weight by `max(0, −S·v)`, which is near zero with the sun in
front. Cloth translucency barely showed at 1× in the study (awning tops face the sun and the sky);
keep its strength low and judge at 2–3×. **Coloured shadows through awnings and dappled shadows
through canopies** were tried (transmission multiplied along the shadow march by the occluder's
material): at 1–2× they read as noise, not colour; left out (§7).

**Acceptance.** G8 at dawn and the Agora with the sun behind the view at 15–20°: the median luma of
the canopies' visible pixels ≥ 1.2 × the opaque version (measured +26 % in the study); none of it at
noon (≤ 1.05 ×); flicker never moves a pixel more than one step; a gust crossing a meadow visible
as a moving lighter band in a 3 s clip (M-clip of G12).

### R5. Wet ground and puddles

**Adds:** rain that changes surfaces, not only the air: porous ground a step darker, paving that
mirrors the people on it, puddles in the low and enclosed places reflecting the street and the
sky, rings when it rains.

**Data.** Have: `porous`, `specular`, class, the weather field's wetness, the mirror march, sky
visibility (R2). Must add: per ramp `wet_steps` and `gloss` (§5.2).

**Algorithm (Lagarde's rain and wet-surface model, reduced to ramps).**

1. Wet darkening: multiply the porous pixel's relight ratio by `0.55` at full wetness (it drops
   `wet_steps` ≈ 1–2 steps on its own ramp: measured luma −21 %, inside the bar's 10–25 %), non-
   porous by 0.85.
2. Sheen on flat wet pixels (`n_z > 0.9`): `mirror · (0.06 porous, 0.12 stone) · wetness`; the
   mirror is the water march's, so figures and lamps streak on wet paving.
3. Puddles where `noise(X, Y)·0.65 + noise(X/3, Y/3)·0.35 + (1 − V)·0.5 > 0.68` on paved and earth
   ground at floor level (`V` = R2's sky visibility, so wall feet and ruts fill first); inside:
   `0.3 · wet + 0.6 · mirror`, the mirror rippled in whole pixels, rain rings while it rains; a
   darker rim. Puddles grow with accumulated rain and dry from the edges (threshold moves with
   wetness), the mud season's floor (`seasons.md`) keeps them.
4. The sky colour in puddles is the sky's **darker** zenith (×0.6): the first attempt with the
   bright horizon colour read as snow patches.

**Cost.** Only while wetness > 0: the mirror on flat wet pixels (half resolution, shared with R3):
0.1–0.3 ms. Medium: steps 1, 2 with sky only, puddles as darker patches; High: all.

**Risks.** Paleness: sheen lifts dark basalt toward grey if it exceeds ≈ 0.12. Puddles on slopes:
`n_z > 0.9` and floor level only.

**Acceptance.** G2 and a Rome street after a shower: porous luma −10 to −25 %; puddles 5–15 % of
paved ground (study: 11 %), each reflecting what stands beside it in whole pixels, cut at its edge;
none on roofs or walls; dry ground within 120 s of game time after the rain stops (they shrink
from the edges).

### R6. Snow that builds and thaws by light

**Adds:** winter that reads as weather on a real place: a first dusting on what faces up and is
open to the sky, deep drifts at wall feet, thaw that follows the sun (sunny roof slopes bare, the
shaded slope white; snow lying on in the shadows of buildings while open squares go dark and wet).

**Data.** Have: the `snow` bit, normal, `h`, sky visibility (R2), the top map. Must add: nothing
per pixel; per ramp a snow ramp choice if different materials should wear different snow (optional).

**Algorithm (accumulation by exposure, in the spirit of Ohlsson & Seipel 2004).**

1. Catch per pixel: `clamp((n_z − 0.55)/0.35) · (0.25 + 0.75·shelter) + drift`, with
   `shelter = clamp((V − 0.35)/0.4)` (eaves and canopies keep the ground beneath bare) and
   `drift = clamp((0.75 − V)·2, 0, 0.4)` on floor-level pixels (enclosed corners collect).
2. Cover `c` from the climate (0 → 1 over a snowfall); a pixel is white where
   `catch·0.9 + noise·0.55 > 1.25 − c` (`noise` world-anchored, two octaves), so cover grows as
   patches, not as a fade.
3. **Exposure map:** per top-map texel, the day's sun energy: five sun positions along the plan's
   path through the top map, `Σ vis·max(0, n·S)/max(S_z, 0.3) / 5`; **baked per chunk once per
   game day** (time-sliced on the worker; it changes only with the season's sun).
4. Thaw: melt where `noise·0.5 + (1 − exposure)·0.9 + catch·0.2 < 0.78 − melt`, `melt` rising
   with warm sunny hours; melted ground is wet (R5) for a while.
5. Snow pixels take the snow ramp at a step from their baked light (the relight works on it like
   any ramp); sparkle: a world-hashed 0.6 % of sunlit snow pixels at the top step, re-hashed every
   few seconds, never in shade.

**Cost.** Per frame ALU only (≈ 0.01 ms); the exposure bake ≈ 5 marches per texel per chunk per
day on the worker. All tiers (Low: catch and cover without exposure).

**Risks.** Blotchy noise: the second octave must stay ≥ 7 px or the melt edge looks like
camouflage; dark bare basalt inside snow read as holes in the study: bare paving inside cover
should be wet-dark, not its dry dark.

**Acceptance.** G9 and G3: no snow on faces with `n_z < 0.55` or under eaves (bar §5.3); after one
sunny thaw day the snow share in pixels with exposure < 0.15 is ≥ 2.5 × the share in pixels with
exposure > 0.5 (study: 69 % against 20 %); a timelapse clip of a thaw over the Pārsa town showing
sunny slopes clearing first.

### R7. One bounce from sunlit surfaces

**Adds:** reflected light: the warm street lighting the bottom storeys of the shaded wall opposite,
a bright plaster wall tinting the ground beside it; at night the lamp-lit ground lifting the wall
behind the lamp.

**Data.** Have: albedo (the ramp colour), normal, `h`, the top map, the sun's visibility.

**Algorithm (a radiance grid on the ground, gathered SSDO-style; Ritschel et al. 2009,
Kaplanyan & Dachsbacher 2010).**

1. Radiance grid per chunk at 8 px texels (quarter tile): splat `albedo × direct light` of every
   visible pixel (sun, sky, lamps) with its height; blur 3 passes. Updated when the sun steps
   (every few seconds) and when lights change; dynamic actors ignored.
2. Gather in the resolve at art resolution: 12–24 taps on rings of 6–48 px round `P + 2n`, weight
   `max(0, n·dir)/(1 + (d/24)²)`, strength 3.5 (tuned on the study).
3. Added before the snap (it moves pixels up their ramps); its colour keeps the source's hue at
   45 % (R8).

**Cost.** Grid splat and blur ≈ 0.02 ms when it updates; gather 12 taps at art resolution ≈ 0.09
ms. High only.

**Risks.** Blocky light: gather from the grid with bilinear filtering (nearest drew orange squares
on the ground). Its effect is small at 1× (visible at 2–3× on wall feet); it is the first thing to
drop if High is over budget.

**Acceptance.** G4 at 10:00 at 2×: the lowest 8 px of a shaded wall standing on sunlit paving have
(r − b) ≥ 6 above the same wall 40 px higher; no bounce on surfaces facing away from the source.

### R8. Image formation

**Adds:** the colour of light without the colour of a filter: shade that is sky-coloured but not
cyan, warm light that is honey, not orange, highlights that roll off instead of clipping, lamps
that bloom softly.

**Data.** Have: the graded ramp table (plan §2.3), the glow target, `theme.look`.

**Algorithm.**

1. **Light colour at ~45 %.** Applying the light's chromaticity in full (as the R&D resolve and the
   study's first runs did) turns shade on grass teal and shaded marble navy; at 45 % the shade
   stays recognisably the material's own (saturated pixels > 55 %: 22 % → 11 % on the street).
2. **Per-light graded tables** keep the palette: instead of tinting each pixel by a continuous
   light colour (6 700 distinct colours in a 1000 × 650 crop), grade the ramp table three times per
   frame (sun-lit, shade, lamp-lit; ≤ 255 × 8 × 3 colours on the CPU, ≈ 0.05 ms) and pick by the
   pixel's dominant light, blending by dither where two compete.
3. **Split tone by the light's temperature,** not by luminance (the E1 lesson): where the light is
   bluer than white, a touch of violet; where warmer, honey.
4. **Hue-keeping shoulder:** roll luminance off above 0.8 with `tanh`, desaturating ≤ 35 % toward
   white at the very top (the reason display transforms of the AgX family exist: bright saturated
   lights must not skew hue or clip).
5. **Bloom from the glow layer only** (as built), two scales; night strength as E1.

**Cost.** ALU and a CPU table: ≈ 0.01 ms GPU. All tiers.

**Acceptance.** G1 and G4: saturated share inside the bar (6–25 % day); shade on grass not more
than 25° of hue from the grass's own; the §1.2 hue rules of the plan hold; no lamp pixel clipping
to (255, 255, 255) except glint and flame cores.

### Beyond the eight (smaller, sound, later)

- **Light shafts** only where geometry makes them certain: lighthouse and lantern beams, sun
  through colonnades and windows at low sun, as a few analytic additive quads per opening
  oriented by the sun, depth-tested against `h` (the depth study's full march was faint and costly
  over open paving).
- **Smoke and steam lit by fires**: each particle samples the light list (nearest two lights) and
  the sun's visibility at its point; warm undersides above braziers.
- **Stars and moon in water**: the mirror already falls back to the sky; give the night sky stars
  and a moon glitter at the moon's mirror angle (R3 step 6 with the moon).
- **Birds' and clouds' shadows on everything**: flying actors cast a shadow at their ground point
  offset along the sun by altitude (one quad each, multiplied in the shadow pass).
- **Petals, leaves and snow that settle**: decals splatted into the cell's ground cache, faded by
  the season (zero per frame).

---

## 3. Pixel-art rules these techniques must keep

Measured on the Forum (sun turned by 1°; share of world pixels whose colour changes; distinct
colours in a 1000 × 650 crop):

| Variant | Crawl per degree | Colours | Look |
|---|---|---|---|
| Smooth (albedo × light, no snap) | 4.2 % | 27 800 | a filtered render; arcade interiors fall to black |
| Snap, no dither | 1.7 % | 6 500 | hard contour bands across paving |
| **Snap, world-anchored 4 × 4 band 0.55** (the generator's) | 1.7 % | 6 700 | crisp; transitions as the art's own dither |
| Snap, full ordered dither | 1.9 % | 3 700 | screen-door texture on every plane |

Rules, adopted from that and from the experiments:

1. Every light term that changes a pixel's *value* (sun, sky, bounce, translucency, wetness)
   goes in before the snap; every *added* light (lamps) goes after it in 6–8 dithered bands;
   only glints, flames, glow and the water's computed hue may leave the ramp.
2. The sun moves in **steps of 0.25°** (≈ 0.4 % of pixels change per step, below notice), never
   cross-faded (a cross-fade of two dithered frames is off-palette for its duration). This refines
   the plan's "stepped every 2 s and cross-faded".
3. Light buffers run at **art resolution** (the art's own pixel), upsampled by depth: a shadow or a
   pool edge is never finer than an art pixel, and 2× and 3× cost a quarter and a ninth of 1×.
4. Smooth gradients belong only to the sky, haze, fog, bloom halos and the water's depth tint
   *before* its snap; never to a lit surface.
5. A floor under every snap: nothing lit goes below 0.55 × its darkest step (keeps the bar's "no
   pure black").
6. Noise for water, puddles, snow and flicker is world-anchored and integer-hashed (the R&D
   lesson: float hashes show their lattice far from the origin).

---

## 4. Cost per tier

GPU at 1440p on the test machine, busiest city view, estimates calibrated on the R&D measurements
(a dependent sample per full-resolution pixel ≈ 0.03 ms):

| Pass | Low | Medium | High | Replaces |
|---|---|---|---|---|
| Top map (worker build; per-frame actor overlay) | 0.01 | 0.01 | 0.01 | — |
| R1 lamps with visibility | (E1 pools) | 0.10 | 0.20 | E1 pools |
| R2 sky visibility (baked) + actors live | 0.00 | 0.05 | 0.05 | plan's contact AO for static, enclosure bake |
| R2 penumbra in E5's march via max-mip | (sprites) | 0.15 | 0.20 | E5 0.3–0.5 |
| R3 water v2 | (E2) | 0.08 | 0.30 | E2 water + mirror ≈ 0.9 at 1× |
| R4 translucency, flicker, silvering | 0.04 | 0.04 | 0.04 | — |
| R5 wet and puddles (only while wet) | 0.01 | 0.05 | 0.25 | plan's wet sheen |
| R6 snow (only in winter) | 0.01 | 0.01 | 0.01 | — |
| R7 bounce | — | — | 0.10 | — |
| R8 image formation | 0.01 | 0.01 | 0.01 | — |
| **Net against the plan's tier** | ≈ +0.05 | ≈ −0.05 | ≈ −0.2 to +0.1 | |

High stays inside the plan's 4.2 ms average and its 1.8 ms headroom to the 8.3 ms line: the water
mirror's max-mip and the top-map march pay for the new passes. CPU: unchanged except the per-light
tables (≈ 0.05 ms) and the actors' overlay splat (a few hundred quads in the existing batch).
Memory: top map ≈ 12 MiB resident, radiance grid ≈ 3 MiB, cell companions +3 bytes per texel at
quarter resolution (≈ +6 MiB). Every number above is an estimate until the bench measures it; E3's
harness and the bench cases (Rome busiest, Agora 22:00, Ostia water, a snow city, rain) gate each
task.

---

## 5. What the art generator must add

The packed word is full and stays as A1 built it. Additions are beside it:

1. **Occlusion-tops page** per set (`<set>.o.png` + `.o.json`), one small sprite per item, look
   and rotation (and per piece for split landmarks): world-aligned (X, Y) grid at 4 px per texel
   over the footprint, RGBA8: R = top height / 2, G = underside height / 2 where something
   overhangs walkable or open space (0 = solid to the ground), B = material code of the top
   (solid, foliage, cloth, water, glass), A = coverage. From the voxel model directly (max and
   min occupied z per column), so arcades, colonnades, bridge decks, awnings and canopies are
   right where the screen cannot know. Size: a few KB per landmark; the whole of Rome well under
   1 MB. Validator: every packed item has its tops; tops agree with the packed heights (max of the
   column ≥ max `h` of the pixels whose ground position falls in it).
2. **Per-ramp response fields** in `ramps.json` (no page change): `translucency` (0–1) and `trans`
   (transmission colour), `wet_steps` and `gloss`, `sparkle` (snow, metal, glaze), for water
   ramps `bed` (colour) and `absorb` (rgb per 70 px), optional `snow_ramp` per material.
3. **Light facings:** each geometry `lights` entry (`door_k`, `window_k`) gains `dir` (the wall's
   outward normal, grid axes) and an optional `cone` (degrees), so R1 throws window light onto the
   street.
4. **Falls and rapids faces for the world's water levels:** `edge/world.fall_se` / `_sw`
   (animated, colour-only like the home's falls) and a rapids overlay for a flow tile that
   descends; with the engine drawing them where water tiles meet a lower water tile, the boxes of
   water with pale sides disappear.

Nothing here changes a colour page; a rebuild of each set adds only the tops page and the
geometry fields (it can ride on the plan's A3–A6 quality rebuilds, no extra rebuild).

---

## 6. Order of work after E3

Sizes in agent-hours (one agent, the plan's 2–4 hour units). Engine tasks branch from `main` one
at a time; art tasks run beside them.

| # | Task | Lane | Needs | Size | Fold into |
|---|---|---|---|---|---|
| A7 | Occlusion-tops pages, ramp response fields, light `dir`, world falls faces (§5) | art | A1 | 6 h (+ rebuilds with A3–A6) | — |
| R0 | Top map per chunk: build from packed pixels now, from tops pages when A7 lands; max-mip; actor overlay; debug view | engine | E4 | 4 h | before E5 |
| R2 | Sky visibility + bent normal baked in cell companions; sky light by bent normal; top-map sun march with penumbra | engine | R0 | 4 h | E5 |
| R8 | Light colour at 45 %, per-light graded tables, temperature split tone, shoulder; sun in 0.25° steps | engine | E4 | 3 h | E4 polish |
| R1 | Lamps in 3D with visibility, window cones, bands 8 | engine | R0, A7 (`dir`) | 4 h | after E5 |
| R4 | Translucency, wrap, leaf flicker, gust silvering | engine | E4, A7 (fields; defaults until then) | 3 h | after E5 |
| R3 | Water v2 (waves, Fresnel, bed, caustics, glints, max-mip mirror); the water coverage audit (Portus basin, home pond, levels → falls) | engine | E5, A7 | 6 h | E6 |
| R5 | Wet and puddles | engine | R3, R2 | 3 h | E7 |
| R6 | Snow build and thaw by exposure | engine | R2, S-E1 | 3 h | E7 |
| R7 | Bounce grid | engine | R2 | 3 h | after E7 (High) |
| Q | Golden review per task: the acceptance checks above, a clip where motion is the point | QA | each | 1 h each | — |

The first owner-visible gain comes from R2 + R8 (day frames gain volume and lose the filter look),
then R1 (nights), then R3 (water); R4 can be pulled earlier by any agent, it is small and
independent.

---

## 7. What not to do, and why

- **Screen-space 2D global illumination (radiance cascades, jump-flood distance fields in the
  screen plane).** In 2:1 iso the screen's y mixes height and depth: light marched in the screen
  plane climbs over roofs to the street behind. The top map is the right space, and the one
  bounce of R7 on it captures what matters at a tenth of the cost.
- **Physically based subsurface scattering** (diffusion profiles, separable blurs): the art's
  pixels are larger than any scattering radius worth showing; thickness-based translucency (R4)
  gives the visible part.
- **Coloured and dappled shadows through cloth and leaves** (tried): unreadable at 1–2×.
- **Smooth, unsnapped lighting** for any lit surface (§3: it doubles crawl and turns the art into
  a render).
- **Temporal anti-aliasing or temporal accumulation** of light: it smears whole-pixel art and
  ghosts behind walkers; every pass here converges in one frame.
- **Film grain, vignette, chromatic aberration, lens dirt**: grain fights the world-anchored dither
  and crawls; the others are camera artefacts in a picture that is not photographed.
- **Froxel volumetric fog**: an orthographic view from above has little depth range; the analytic
  height fog of E8 plus R4's backlight and R1's light gives the air without a 3D grid.
- **HDR output** now: the art is display-referred and the palette is the look; revisit only with
  a real HDR display to judge on, and then only for lights, glints and the sun's disc in water.
- **A glitter path to the sun on water**: it is a perspective effect; under an orthographic camera
  it would be painted, not lit (R3 step 6 explains what the physics gives instead).
- **Full-strength light colour** on surfaces (R8 step 1): it reads as a filter, the owner's "pale,
  flat or stale" in another form.

---

## References

- Barré-Brisebois, C., Bouchard, M. "Approximating Translucency for a Fast, Cheap and Convincing
  Subsurface Scattering Look", GDC 2011; GPU Pro 2 (2011).
  https://www.ea.com/frostbite/news/approximating-translucency-for-a-fast-cheap-and-convincing-subsurface-scattering-look
- Green, S. "Real-Time Approximations to Subsurface Scattering", GPU Gems ch. 16 (2004).
  https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-16-real-time-approximations-subsurface-scattering
- Jimenez, J., Wu, X.-C., Pesce, A., Jarabo, A. "Practical Realtime Strategies for Accurate Indirect
  Occlusion" (GTAO, bent normals), 2016. https://www.iryoku.com/downloads/Practical-Realtime-Strategies-for-Accurate-Indirect-Occlusion.pdf
- Bavoil, L., Sainz, M., Dimitrov, R. "Image-Space Horizon-Based Ambient Occlusion", SIGGRAPH 2008 talk.
- Tevs, A., Ihrke, I., Seidel, H.-P. "Maximum Mipmaps for Fast, Accurate, and Scalable Dynamic Height
  Field Rendering", I3D 2008. https://pure.mpg.de/pubman/item/item_1325622_5/component/file_3590464/i3d08.pdf
- Quilez, I. "Soft shadows in raymarched SDFs". https://iquilezles.org/articles/rmshadows/
- Ritschel, T., Grosch, T., Seidel, H.-P. "Approximating Dynamic Global Illumination in Image
  Space" (SSDO), I3D 2009.
- Kaplanyan, A., Dachsbacher, C. "Cascaded Light Propagation Volumes for Real-Time Indirect
  Illumination", I3D 2010.
- Cox, C., Munk, W. "Measurement of the Roughness of the Sea Surface from Photographs of the
  Sun's Glitter", JOSA 44 (1954). https://doi.org/10.1364/JOSA.44.000838
- Tessendorf, J. "Simulating Ocean Water", SIGGRAPH course notes (2001–2004).
- Vlachos, A. Flow maps for water, SIGGRAPH 2010 Advances in Real-Time Rendering course (the
  two-phase advection R3 reuses; linked in `out/reports/graphics-rnd.md`).
- Wallace, E. "Rendering Realtime Caustics in WebGL" (2016).
  https://medium.com/@evanwallace/rendering-realtime-caustics-in-webgl-2a99a29a0b2c
- Lagarde, S. "Water drop 2a/2b: dynamic rain and its effects" (2013).
  https://seblagarde.wordpress.com/2013/01/03/water-drop-2a-dynamic-rain-and-its-effects/
- Ohlsson, P., Seipel, S. "Real-time Rendering of Accumulated Snow", SIGRAD 2004.
- Sousa, T. GPU Gems 3 ch. 16, vegetation animation and shading (2008): layered bending and leaf
  translucency. https://developer.nvidia.com/gpugems/GPUGems3/gpugems3_ch16.html
- Hillaire, S. "A Scalable and Production Ready Sky and Atmosphere Rendering Technique", EGSR 2020.
  https://diglib.eg.org/handle/10.1111/cgf14050
- Wronski, B. "Volumetric Fog", SIGGRAPH 2014 Advances course (why froxels are not needed here).
  https://www.advances.realtimerendering.com/s2014/wronski/bwronski_volumetric_fog_siggraph2014.pdf
- Jimenez, J. "Next Generation Post Processing", SIGGRAPH 2014 Advances course (bloom).
- AgX display transform (Sobotka et al.): hue-keeping highlight roll-off.
  https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/agx/
- Holland, D. "3D Pixel Art Rendering" (2024): normals and depth for one-pixel outlines and
  convex-edge highlights. https://davidholland.netlify.app/articles/3d-pixel-art-rendering
