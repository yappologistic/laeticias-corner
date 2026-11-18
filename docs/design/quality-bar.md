# The quality bar

What "good enough to ship" means for every visual, motion, audio, interface and performance
change, phrased so that a reviewer with screenshots, short clips and measurements can say **pass**
or **fail**. It sits beside `look.md` (visual direction and the render pass plan), `seasons.md`
and `living-world.md`, and it outranks their acceptance numbers where they differ (§1.2 says
which). The research behind it, with sources and the measurements of the game as it is, is the
untracked report `out/reports/quality-research.md`.

Contents: 1 principles and how to use this · 2 golden scenes · 3 pixel art · 4 lighting and
colour · 5 water, weather and seasons · 6 animation and motion · 7 crowds and life · 8 terrain
and layout · 9 audio · 10 interface and text · 11 performance · 12 review procedure · 13
references.

---

## 1. Principles and how to use this

### 1.1 Five rules every change is judged by

1. **Every pixel is a decision.** Dynamic light, weather and grading must leave the frame made of
   palette ramps, readable clusters and clean contours: light first, then quantise, in art-pixel
   space, with a dither anchored to the world.
2. **Value and temperature before detail.** Each frame has a clear value structure, a warm key
   and a cool counterpoint. Detail that breaks the value structure is noise.
3. **Nothing on screen is still, nothing jitters.** Something moves in every part of the view;
   all motion is evenly spaced, and a pixel changes only when what it shows changes.
4. **The ground is a place.** The 85 % of the screen that is ground carries material, wear and
   small life at a calm value, at every zoom and in every region.
5. **Measured, not asserted.** A change passes when its golden scenes, metrics and clips pass,
   judged against the approved baseline. Thresholds marked *(cal.)* are calibrated on approved
   frames before they gate (§12.3); the rest gate now.

### 1.2 Changes to earlier targets

- `look.md` §2.1 day key: replaced by §4.1 here (softer key, cool share in cities). Dawn, dusk and
  night rows stay, with the night additions of §4.3.
- `look.md` §4.4 ("normal maps: not worth it"): superseded by the per-pixel data pages (normal,
  height, material) the graphics R&D round is adding; their use is governed by §3.4 and §5.3.

### 1.3 Terms

- **Art pixel**: one pixel of the atlas at 1×. **Screen pixel**: one pixel of the window.
- **World area**: the frame minus interface rectangles.
- **Unlit pixels**: world pixels not within 3 tiles of a light, not glow, not specular.
- **Ramp**: a material's ordered colour list in the palette (`tools/artgen/palette.py`).
- Oklab and its lightness L as defined by Ottosson (2020); ΔE_OK is Euclidean distance in Oklab.

---

## 2. Golden scenes

Every visual change is judged on the golden scenes it can affect (all of them when in doubt),
rendered headless on the shader path (windowless) and on the classic path, at 2560×1440 unless
stated, interface hidden except where noted. Each scene is a fixed seed, place, hour, season,
weather and zoom, kept as a script in `tests/scripts/golden/` with the approved frames.

| ID | Place | Time, season, weather | Zoom | What it guards |
|---|---|---|---|---|
| G1 | Home corner, stage 3, cottage, beds and pond in view, Laeticia watering, ducks out | 16:00, summer, clear | 2× | charm baseline: props, figures, ground richness, warm key |
| G2 | Home pond with a lamp on the bank | dusk, autumn, shower clearing | 3× | water layers, reflections, warm light pools, falling leaves, wet ground |
| G3 | Home corner whole island | 23:00, winter, snowing | 1× | night readability, snow cover, warm windows, cliff rims |
| G4 | Rome, Forum Romanum with the Basilica Julia and the temples | 10:00, spring (Parilia), clear | 1× | city value structure, roof families, crowds with purpose |
| G5 | Rome, Tiber island with Pons Fabricius and Pons Cestius | 19:30, summer, clear | 2× | river water, bridges meeting banks, dusk lights, reflections |
| G6 | Athens, Acropolis from the south slope, the Parthenon centred | 07:30, summer (Panathenaia), clear | 1× | marble brightest on screen, long morning shadows, rock darks |
| G7 | Athens, Agora with the stoas | 22:00, summer, clear | 2× | city at night: lit windows, doors, torches, pools, moon shade |
| G8 | Pārsa, the terrace with the Apadāna and the Great Stair | 06:30, spring (audience), mist | 2× | large flat roofs, honey dawn on stone, cool shadows, mist |
| G9 | Pārsa town below the terrace | 12:00, winter, after snowfall | 1× | seasons on city art: snow on what faces up, bare trees, frozen water |
| G10 | Saronic gulf sea lane with ships and the Piraeus shore | 15:00, autumn, storm front arriving | ½ | weather front, sea state, rain only under cells, wind on sails |
| G11 | World overview | dusk, spring, mixed weather | overview | far lights, haze, nothing still, no popping when zooming in |
| G12 | Zagros, the road through the Persian Gates | 11:00, autumn, windy | 1× | the land between: relief that reads, clutter, travellers, herds |

Motion goldens (3-second clips at 120 fps, presentation-timed): **M1** pan across G4 at 1× at a
constant 300 screen px/s; **M2** following Laeticia walking 6 tiles in G1 at 2× and at 3×;
**M3** G2's pond for 3 s with no input; **M4** zoom 1× → 2× → 1× toward the cursor over G4;
**M5** G10 storm for 3 s.

Interface goldens: the title, the build drawer open over G4, the sketchbook over G1, the world
map, a city card with Greek text, at 1920×1080 and 960×600.

---

## 3. Pixel art (generator output and anything drawn into the world)

### 3.1 Palette and ramps

- [ ] Every ramp's lightness steps are even: each step's ΔL within ±30 % of the ramp's mean step.
- [ ] Hue rotates monotonically along each ramp: darker steps toward blue/violet, lighter toward
      yellow; chroma is highest at a middle step.
- [ ] No two steps of one ramp closer than ΔE_OK 0.04. Darkest step L ≥ 0.18, lightest ≤ 0.95
      (nothing pure black or white except lights and glints).
- [ ] The darkest two steps of every material belong to one shared shade family (violet-blue ink).
- [ ] A new set adds colours only through `palette_for(set)`; every opaque pixel of every page is
      a palette colour (the set validator checks it).

### 3.2 Structure

- [ ] **Orphan pixels** (an opaque pixel differing from all 8 neighbours by ≥ 2 ramp steps or by
      material; outline pixels and declared glints excluded): share per sprite ≤ the approved home
      atlas's 90th percentile *(cal.)*.
- [ ] Large planes (roofs, paving, squares, dry ground over 2 × 2 tiles) carry **structured**
      variation (courses, slabs, patches, wear paths, stains of ≥ 2 px), never per-pixel random
      tone noise; at 1× no plane larger than 4 × 4 tiles is one flat value.
- [ ] Lines keep monotone run lengths; no doubled outline pixels; no pillow shading (shading
      follows the light, not the outline).
- [ ] Outlines are selective and coloured: darker on the lower and shaded side, the fill's darkest
      step, never pure black; no gaps longer than 1 px on the shaded side.

### 3.3 Figures and animals (at 1×)

- [ ] **Silhouette test**: filled solid against the ground, the figure's role is guessable (head,
      body, carried thing or tool, stride) by two reviewers out of three.
- [ ] The head is a distinct mass wider than the neck, hair or headgear as its own value; arms
      separate from the torso by a gap or a value break in at least the passing frame; the walk's
      silhouette width changes by ≥ 2 px between contact and passing frames.
- [ ] One accent per figure with saturation ≥ 55 %; the outer ring of the figure differs from its
      usual ground by ΔL ≥ 0.10 along ≥ 60 % of the outline.
- [ ] Animals show their defining silhouette features at 1× (horns, ears, tail, legs, snout);
      no rounded lump without legs separated in the walk.

### 3.4 Run-time effects keep the art's discipline

- [ ] After relighting and grading, world pixels are quantised to their material's ramp (or to
      the graded palette) with an ordered dither indexed by **world** art-pixel coordinates. With
      the sun at the baked direction and a neutral grade, the shader path reproduces the atlas
      within 1 ramp step on ≥ 99 % of pixels.
- [ ] During a pan (M1) a static object's pixels do not change colour (dither does not swim).
- [ ] Bloom, haze and fog never blur the art: outside the glow layer's halos, edge contrast of
      the scene drops by < 5 % between the effect off and on.

---

## 4. Lighting and colour

### 4.1 Key and temperature by hour (world area, every region)

| Hour | p2 luma | median | p98 (unlit) | cool share | warm share | saturation > 55 % |
|---|---|---|---|---|---|---|
| Day | 18–45 | 95–125 | ≤ 205 (≤ 2 % of pixels may exceed 215: marble, snow, glints) | ≥ 20 % | ≤ 75 % | 6–25 % |
| Dawn | 10–30 | 70–115 | 170–205 | ≥ 25 % | 35–70 % | ≤ 25 % |
| Dusk | 8–25 | 45–85 | 160–205 | ≥ 25 % outside sunlit planes | 50–75 % | ≤ 35 % |
| Night | 4–14 | 22–45 | — | ≥ 60 % of unlit pixels | — | ≤ 10 % unlit |

- [ ] Shade is the sky's colour, not grey: the mean hue of cast-shadow pixels at day has b > r.
- [ ] A cloud's shadow lowers only the sun term (cooler and softer, never grey).
- [ ] Materials at day (luma / saturation): grass 85–135 / 30–50 %; earth and paving 110–170 /
      15–35 %; marble ≤ 215 and the brightest large surface where present; foliage deepest shade
      35–55; a wall's shaded side ≥ 25 % darker than its lit side.
- [ ] The darkest values sit in **occlusion** (under canopies, eaves, at wall feet, under figures),
      not in cast shadows: occluded pixels' median luma is lower than cast-shadow pixels' median.

### 4.2 Shadows and occlusion

- [ ] Shadow direction and length follow the sun model: at G6, the Parthenon's shadow is ≥ 2.5×
      longer at 07:30 than at 12:00.
- [ ] Shadows touch their casters (no gap between an object's base and its shadow) and soften
      with distance from the caster; no hard dark parallelogram reads as a slab.
- [ ] Every standing item and figure has contact occlusion at its base (≥ 1 px darker band or
      soft ellipse); none float.

### 4.3 Night

- [ ] Inhabited views are lit: in a city at night, warm lit pixels (r > b + 30, luma ≥ 90) are
      2–8 % of the world area; in a village 1–4 %; at least one warm light per screen anywhere
      people live; p98 at the lights ≥ 160.
- [ ] Lights make **pools** on the ground and walls near them (amber on grass: r > g), stopped by
      walls, spilling through doors and colonnades; flicker ≤ ±8 % and never across a full ramp step.
- [ ] Unlit night keeps value contrast: luma IQR of unlit pixels ≥ 12.
- [ ] Every light persists at every zoom level as a warm point (no light vanishes when zooming out).

### 4.4 Grade

- [ ] Grading changes the palette or quantised colours, not the pixel structure (§3.4).
- [ ] No grade turns a frame one hue: at no hour does one 30°-hue band hold > 70 % of world pixels.
- [ ] A region's identity holds across hours: its accent colours stay ≥ 45 % saturated at dawn,
      day and dusk.

---

## 5. Water, weather and seasons

### 5.1 Water

- [ ] Hue 180–215°; value 15–35 % below adjacent land; ≥ 3 depth bands in any water wider than
      3 tiles, the shallow band lighter and more saturated than the deep.
- [ ] A 1–2 px shore line or foam on every land–water edge, animated with a 2–5 s period, never
      in phase along more than 6 tiles.
- [ ] Surface motion is continuous (no visible frame steps): over M3, highlight strokes move by
      ≤ 1 art px per presented frame and cover 3–10 % of the water area; rivers' strokes move with
      the flow.
- [ ] Reflections of every object within 1 tile of the water, offset only in whole art pixels,
      darker and cooler than the object, cut where the water ends; lights reflect as vertical
      wobbling streaks at night.
- [ ] Sparkles ≤ 1 % of water pixels, 1–2 px, living 0.2–0.6 s, on the sun's side.
- [ ] Water at an image edge, a cell edge or the world's edge continues without seam or change of
      animation phase.

### 5.2 Weather

- [ ] Rain falls only under rain cells; streaks lean with the wind's screen direction; splashes
      on ground and rings on water appear within 1 s of rain starting.
- [ ] A weather change reaching the view changes **light, surfaces and motion** within 10 s
      (grade, wetness or snow, particles or sway).
- [ ] Wet porous ground and paving darken 10–25 % in luma; paving gains sky- or lamp-coloured sheen.
- [ ] Wind is one field: trees, grass tufts, cloth, smoke, rain and clouds lean the same way, gusts
      travel downwind as visible waves.
- [ ] Reduce motion halves weather motion and removes lightning flashes.

### 5.3 Seasons in every region

- [ ] Each region shows its climate's season (`seasons.md` §2) in every golden scene it appears
      in: ≥ 8 % of world pixels change between two seasons of one view (actors hidden).
- [ ] Snow settles on surfaces facing up (from the data page normals) and not on vertical faces or
      under eaves; it follows climate and altitude (no snow in the Mesopotamian lowlands or the
      Gulf in winter); ground snow melts first on the sunny side.
- [ ] Deciduous foliage turns in autumn and is bare in winter where the climate says; evergreens do
      not change; dry-summer grass turns straw in the Mediterranean dry climates.
- [ ] Ground clutter changes with the season (blossom, flowers, litter, snow-capped stones).

---

## 6. Animation and motion

### 6.1 Smoothness

- [ ] **Camera**: over M1, displayed scene displacement per presented frame has a standard
      deviation ≤ 0.5 screen px (no art-pixel stepping); the camera is placed at sub-art-pixel
      precision by offsetting the upscaled image.
- [ ] **Actors at zoom ≥ 2** are placed at screen-pixel precision (their sprites stay whole art
      pixels); over M2, the walker's screen displacement per frame varies by ≤ 1 screen px.
- [ ] Zoom transitions keep pixels square and crisp (sharp-bilinear or pixel-art scale mode), never
      a linear blur; ease 250–350 ms, no overshoot.
- [ ] No animation reads as stepped: water, smoke, clouds and sway are continuous; frame-based
      cycles play at ≥ 8 fps.

### 6.2 Character animation

- [ ] Walk cycles are **stride-locked** (frame chosen by distance travelled): feet slide ≤ 1 art px
      per cycle at any speed in the actor's range.
- [ ] People walk with ≥ 8 frames at the native page, quadrupeds ≥ 6, with contact poses held
      longer than passing poses and a 1-px vertical bob.
- [ ] Turning shows a turn frame or a short hold (≥ 0.08 s); sitting, standing and lifting show
      anticipation (≥ 2 frames).
- [ ] Cloth, hair, tails and carried things lag the body by a frame (secondary motion).
- [ ] No two neighbouring actors of one kind are in phase: cycle phase, speed (±8 %) and idle holds
      vary per actor from its seed.

### 6.3 Feel

- [ ] Every input is answered visibly in the next presented frame and audibly within 20 ms.
- [ ] Hover feedback ≤ 50 ms; appearing interface eases out over 120–220 ms; placement shows a
      pop in whole-art-pixel steps, a dust puff and its note within the same frame.
- [ ] Camera follow uses a critically damped spring (half-life 70–110 ms), framerate-independent.

---

## 7. Crowds and life

- [ ] `living-world.md` §1.1 counts hold (purposeful movers, happenings, caps), measured by the
      liveliness probe.
- [ ] **Purpose is visible**: ≥ 60 % of moving people carry or lead something, or walk in a pair or
      group; every working slot plays a work loop with its prop (motion at least every 1.5 s).
- [ ] People meet: in a city-centre view at least one pair stops, faces and gestures per minute.
- [ ] Variety: no two adjacent figures share dress variant and animation phase; no lockstep groups
      except processions and formations meant to march.
- [ ] Ambient motion with actors hidden: ≥ 1.5 % of world pixels change between frames 0.5 s apart
      in a city, ≥ 0.8 % in countryside, ≥ 2 % where water fills a third of the view (`look.md`
      §2.5).
- [ ] Something rare starting in view is surfaced once, softly (a sound and a brief mark at the
      place; no modal), and can be followed until it ends; the journal can recount it.
- [ ] Figures never stand inside solids, float above or sink below their floor, or walk through
      walls; bridges, stairs and gates are walked where they meet what they join.

---

## 8. Terrain and layout

- [ ] **Ground richness**: open ground at 1× carries small clutter (tufts, stones, flowers, stalks,
      litter, weeds in joints) at 10–35 % cover by biome, each piece with its own contact shade,
      value within ±1 ramp step of the ground except accents (≤ 15 % of clutter).
- [ ] No visible tiling: no repeated pattern at the tile period readable at 1× or ½ (two reviewers
      out of three, on G1, G4 and G12); variant choice by irregular cells larger than a tile.
- [ ] Terrain transitions are rounded and organic (corner-based), never a stair of diamond edges
      along a coast, field or path.
- [ ] Relief reads as landform: slopes step at most one level per 3 tiles except declared cliffs;
      rivers descend monotonically and change level only at falls or rapids.
- [ ] Every connection meets: a bridge's deck meets both banks at their level, a stair meets both
      floors, a road enters a gate, a jetty meets water and land (zero open ends in the connection
      check).
- [ ] On roads and sea lanes, every 1440p view at native zoom contains at least one authored point
      of interest and one moving thing.
- [ ] Nothing floats: every decal and piece sits on its level (the float check passes).

---

## 9. Audio

- [ ] Loudness per `CLAUDE.md` (music about −18 LUFS, beds −21 to −23, effects balanced by their
      loudest 100 ms, true peak ≤ −1 dB); a mixed 60-s capture of any golden scene sits at
      −20 to −16 LUFS integrated.
- [ ] **No static beds**: loudness range of rain and wind beds 2–5 LU, of nature beds 4–12 LU
      (EBU R128 LRA); no bed has LRA < 1.5 LU.
- [ ] **No audible loops**: in any 60-s capture, no 2-s window repeats another with normalised
      cross-correlation > 0.9, except deliberate music repeats.
- [ ] Every bed carries an event layer: discrete sounds (drops, gusts, calls, tools) with ≥ 3
      variants each, pitch ±3–5 %, gain ±3 dB, placed by world position.
- [ ] Sound follows sight: every visible source of a placed loop (water, fire, workshop, crowd) is
      heard from its screen side within 0.1 s of entering view; distance softens highs; occluded
      sources are low-passed.
- [ ] Weather is heard: rain by surface in view, wind by strength, thunder delayed by distance.
- [ ] Music: no 30-s passage repeats exactly within 20 minutes in the same region and hour;
      silences between pieces during exploration.
- [ ] Synthesised plucked and keyboard instruments carry a body resonance (no bare-wire tone);
      struck objects use modal resonances with per-hit variation.

---

## 10. Interface and text

- [ ] **Every string renders**: a glyph-coverage test over every catalog, region file and
      interface string passes with zero missing glyphs (fallback font chain for Greek and other
      scripts).
- [ ] Right-to-left and shaped scripts render in correct order and joined forms, or are not shown.
- [ ] Contrast: every text style ≥ 4.5:1 (large text and icons ≥ 3:1) against the brightest 5 %
      of the blurred backgrounds the panel shows in the golden scenes.
- [ ] Minimum text size 13 px at 1080p and interface size 100 %; nothing clipped or overlapping at
      960×600; long titles elide or wrap, never overflow.
- [ ] Status, marker and nook colours stay distinguishable under protan, deutan and tritan
      simulation (Machado et al. 2009, full severity): ΔE_OK ≥ 0.08 between any two that mean
      different things, or a second cue (shape, icon, label).
- [ ] No more than three flashes per second; reduce motion removes flashes, camera eases and
      screen-wide motion.
- [ ] Every interactive element has hover, pressed and disabled states; tooltips appear ≤ 600 ms.
- [ ] Messages belong to the place they show in (no home notice while the camera is in a city).

---

## 11. Performance

The budgets of `CLAUDE.md` "Performance" are part of this bar. Added checks for visual work:

- [ ] Each look tier states its cost per pass; the Low tier meets the frame budget at 1440p on an
      integrated GPU, Medium and High on a mid-range laptop GPU (bench on both before merge).
- [ ] No texture creation, readback or synchronous gather on the main thread after start-up;
      worst frame ≤ 16.6 ms across fast travel and zooms.
- [ ] Animation time comes from presentation timing; a run with jittered frame deltas shows no
      visible stutter (M1 criteria hold).
- [ ] Baked work stays baked: clutter, static occlusion and macro variation cost nothing per frame.

---

## 12. Review procedure

### 12.1 For every visual, motion, audio or interface change

1. **Render** the affected golden scenes and motion clips before and after (shader and classic
   paths), plus the interface goldens if any interface changed.
2. **Measure** the metric panel per frame: luma p2/p50/p98, cool and warm shares, saturation share,
   colourfulness (Hasler and Süsstrunk 2003), lit-pixel share at night, ambient-motion share,
   orphan-pixel share for new art, perceptual difference maps against the approved frames
   (FLIP, Andersson et al. 2020); audio captures: LUFS, LRA, true peak, repetition.
3. **Compare** with the absolute targets of §3–§11 and with the baseline: a change may move a
   metric away from its target only with a written reason the art director accepts.
4. **Review** a contact sheet (before, after, difference map, the clips) against the checklists;
   every item is pass, fail or not affected, and a fail cites the crop or measurement.
5. **Approve**: the owner sees visual changes on the golden sheet; approved frames become the new
   baseline (small PNGs kept with the golden scripts).

### 12.2 Gates

- A change that fails any ungated-by-calibration item, or regresses a golden scene's metric
  outside its target, is not done.
- Performance gates (`--bench`, `--soak`) and `ctest` under both presets, as `CLAUDE.md` requires.

### 12.3 Calibration of *(cal.)* thresholds

Before a *(cal.)* item gates, measure it on the approved frames (home art and the golden scenes the
owner has approved), record the distribution in the golden folder, and set the threshold at the
approved set's 90th percentile (or 10th for minimums). Re-calibrate only when the owner approves a
new baseline.

### 12.4 What metrics cannot judge

Charm, composition and whether a place feels like itself. Metrics catch regressions and extremes;
the golden-scene review and the owner judge the rest. Learned aesthetic scores trained on
photographs are not used as gates.

---

## 13. References

Cited by title, author and year; full links and notes in `out/reports/quality-research.md` §13.

- Ottosson, B. "A perceptual color space for image processing" (Oklab), 2020.
- Gerstner, T., DeCarlo, D., Alexa, M., Finkelstein, A., Gingold, Y., Nealen, A. "Pixelated Image
  Abstraction", NPAR 2012.
- Inglis, T., Vogel, D., Kaplan, C. "Rasterizing and Antialiasing Vector Line Art in the Pixel Art
  Style", NPAR 2013.
- Ulichney, R. "The void-and-cluster method for dither array generation", SPIE 1993.
- Yliluoma, J. "Arbitrary-palette positional dithering algorithm".
- Holland, D. "3D Pixel Art Rendering", 2024.
- Quilez, I. "Soft shadows in raymarched SDFs", 2010.
- Rong, G., Tan, T.-S. "Jump Flooding in GPU with Applications to Voronoi Diagram and Distance
  Transform", I3D 2006.
- Sannikov, A. "Radiance Cascades: A Novel Approach to Calculating Global Illumination", 2023;
  Freeman, Sannikov, Margel, "Holographic Radiance Cascades for 2D Global Illumination", 2025.
- Kaplanyan, A., Dachsbacher, C. "Cascaded Light Propagation Volumes for Real-Time Indirect
  Illumination", I3D 2010.
- Bjørge, M. "Bandwidth-Efficient Rendering", SIGGRAPH 2015 course.
- Selan, J. "Using Lookup Tables to Accelerate Color Transformations", GPU Gems 2, 2005.
- Gurney, J. *Color and Light*, 2010.
- Kirk, A., O'Brien, J. "Perceptually Based Tone Mapping for Low-Light Conditions", SIGGRAPH 2011.
- Vlachos, A. Flow-mapped water, SIGGRAPH 2010 Advances in Real-Time Rendering course.
- Finch, M. "Effective Water Simulation from Physical Models", GPU Gems, 2004.
- Lagarde, S. "Water drop" series on dynamic rain and wet surfaces, 2012–2013.
- Fearing, P. "Computer Modelling of Fallen Snow", SIGGRAPH 2000.
- Dobashi, Y., Kaneda, K., Yamashita, H., Okita, T., Nishita, T. "A Simple, Efficient Method for
  Realistic Animation of Clouds", SIGGRAPH 2000.
- Thomas, F., Johnston, O. *The Illusion of Life*, 1981. Williams, R. *The Animator's Survival
  Kit*, 2001.
- Rosen, D. "An Indie Approach to Procedural Animation", GDC 2014.
- Holden, D. "Spring-It-On: The Game Developer's Spring-Roll-Call", 2021.
- Swink, S. *Game Feel*, 2008.
- Ladavac, A. "The Elusive Frame Timing: A Case Study for Smoothness Over Speed", GDC 2018.
- Reynolds, C. "Steering Behaviors for Autonomous Characters", GDC 1999.
- Emerson, E. "Crowd Pathfinding and Steering Using Flow Field Tiles", Game AI Pro, 2013.
- Ryan, J. *Curating Simulated Storyworlds*, PhD thesis, UC Santa Cruz, 2018.
- Maïm, J., Yersin, B., Thalmann, D. "Unique Character Instances for Crowds", IEEE CG&A 2009.
- Lagae, A., Dutré, P. "An Alternative for Wang Tiles: Colored Edges versus Colored Corners",
  ACM TOG 2006.
- Mikkelsen, M. "Practical Real-Time Hex-Tiling", JCGT 2022. Heitz, E., Neyret, F. "High-Performance
  By-Example Noise using a Histogram-Preserving Blending Operator", HPG 2018.
- Bridson, R. "Fast Poisson Disk Sampling in Arbitrary Dimensions", SIGGRAPH 2007.
- Génevaux, J.-D. et al. "Terrain Generation Using Procedural Models Based on Hydrology", SIGGRAPH
  2013. Cordonnier, G. et al. "Large Scale Terrain Generation from Tectonic Uplift and Fluvial
  Erosion", Eurographics 2016.
- Galin, E. et al. "Procedural Generation of Roads", Eurographics 2010.
- *The London Charter for the Computer-based Visualisation of Cultural Heritage*, 2009.
- Farnell, A. *Designing Sound*, 2010. Smith, J. O. *Physical Audio Signal Processing*.
- van den Doel, K., Kry, P., Pai, D. "FoleyAutomatic: Physically-based Sound Effects for Interactive
  Simulation and Animation", SIGGRAPH 2001.
- Liu, S., Cheng, H., Tong, Y. "Physically-Based Statistical Simulation of Rain Sound", SIGGRAPH 2019.
- EBU R 128 and ITU-R BS.1770 (loudness).
- W3C, *Web Content Accessibility Guidelines 2.2*, 2023.
- Machado, G., Oliveira, M., Fernandes, L. "A Physiologically-based Model for Simulation of Color
  Vision Deficiency", IEEE TVCG 2009.
- Hasler, D., Süsstrunk, S. "Measuring colourfulness in natural images", SPIE 2003.
- Rosenholtz, R., Li, Y., Nakano, L. "Measuring Visual Clutter", Journal of Vision 2007.
- Andersson, P. et al. "FLIP: A Difference Evaluator for Alternating Images", 2020.
