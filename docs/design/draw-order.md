# Draw order and where things may be

One contract for what is under, on and over what, and who may stand where, obeyed by every
drawable at every zoom level and in both render paths, with the data rules and tests that keep
it. It replaces the scattered special cases in `src/render/scene.cpp`, `src/worldview/order.*`,
`gather.cpp` and `renderer.cpp` (as on `t3/integrate-game-world` at 0217232) with one model.
The evidence behind every decision is `out/reports/draw-order-audit.md` (the fault catalogue,
counts by cause, the data offenders, walking in place).

Contents: 0 on one page · 1 the model · 2 the global layer list · 3 every zoom level and cache ·
4 both render paths · 5 where things may be (validator rules) · 6 tests · 7 work plan ·
8 sources.

---

## 0. On one page

**What is wrong today.** Two problems look alike on screen and are not the same:

1. *Draw order.* At ½ and ¼ every person on open ground is painted over the cached city
   (`WorldView::prepareActorsTimed` puts every actor with `item < 0` into `coarse_`, drawn after
   the impostor cells with nothing over them): a walker in the street behind a row of insulae is
   drawn on their roofs, and zooming back in "fixes" it because the native level merges actors
   into the painter's order. At 1× the order is mostly right but rests on special cases: the
   depth test ignores height (`lc::behind` compares footprints only), so boats under a bridge are
   drawn over its deck; raised ground hides items but never actors; glow is added over whatever
   stands in front of a lamp; the home's objects are drawn over the world's impostors at ½;
   flyers in the home are always drawn last.
2. *Where things may be.* The walk data and the graphs are clean where routes run (no graph node
   or edge course on a roof, a wall, water or a level change without a stair, in all 29 layers,
   by the engine's own check and an independent scan), and no live actor was found standing where
   the map forbids it. What exists is local: a few landmarks whose walk tiles no step reaches,
   one stair whose head misses its terrace, slot spots inside buildings or on islands no graph
   reaches, walkable reed beds. Walking in place has two causes, neither in the walk data: an
   event cast held still in its walk animation, and wander targets too close to the walker.

**The answer.**

- *One depth model.* Every drawable is an axis-aligned **box**: a footprint rectangle in tile
  coordinates and a height range in pixels above level 0. Whether `a` is behind `b` is decided by
  one comparator (§1.3): the first separating axis of x, y, then height. On any single pixel the
  nearer of two surfaces is the one whose ground point lies further down the screen
  (`n = screen y + height`, §1.1), so the same model gives a per-pixel depth for the GPU.
- *One order.* `Key = (band, rank, sub)`: the band from the global layer list (§2); inside the
  depth-sorted band, the rank from a topological sort of the comparator over the boxes whose
  screen rectangles overlap, ties broken by nearness and then by a stable id; `sub` orders the
  parts of one thing (a carrier before its goods). The order is a strict total order per frame,
  deterministic, and independent of the camera (§1.4).
- *One list of layers* (§2): sixteen bands from the far backdrop to the interface, each drawable
  class in exactly one.
- *Every zoom keeps it* (§3): at 1× the painter's order; at ½ and ¼ actors and the home are
  tested against the cached city instead of being drawn over it: a per-tile "how tall is what
  stands here" field cuts each actor at the row where something nearer covers it (both paths,
  cheap, the first fix), and on the shader path a per-pixel nearness companion of each impostor
  cell makes the test exact.
- *Where things may be is enforced at build time* (§5): validator rules for walk tiles,
  `walk_z`, `climb`, stairs, decks, overhead pieces, graph nodes and edges, slots and
  footprints, in `tools/worldgen` and `tools/artgen`, with the audit's offenders as fixtures.
- *Violations cannot hide* (§6): an order oracle over sampled overlapping pairs, property tests
  of the comparator, a whole-world cycle scan, golden shots of the hard places at every zoom, and
  a debug view that colours depth and band and names the key under the pointer.

**Order of work** (§7): first the coarse-zoom cut (fixes the owner's visible bug, about one
engine task); then the comparator with height and the merge as one sort at 1×; then the data
validators and fixes; then glow and the home at the borders; then the per-pixel test on the
shader path. Nothing later throws an earlier step away: the cut stays the Classic path's coarse
test and the comparator is what every path sorts by.

---

## 1. The model

### 1.1 Coordinates and the one depth number

- A **tile** is `(tx, ty)`; positions are continuous tile coordinates (`x.5` is a tile centre).
  `+x` runs down-right, `+y` down-left (CLAUDE.md, Projection).
- **Height** `z` is in art pixels above level 0: a tile at level `L` has its ground at
  `z = L · tile.level` (16 px at 64 × 32); a landmark floor adds its `walk_z`; an actor stands at
  `floorZ` (stairs interpolate); a flyer adds its altitude; a sprite pixel adds its own height
  above the anchor's ground (the packed page's `h`, `graphics-plan.md` §2.2).
- The **ground row** of a point is `u = (tx + ty) · hh` (world px, `hh = tile.h / 2`): the screen
  row the point would have if it were lowered to level 0. A point's screen row is `sy = u − z`.
- **Nearness** of a point is `n = sy + z = u` for comparisons on one pixel. Proof: two surface
  points `p`, `q` drawn on the same pixel have `sy_p = sy_q`, so `u_p − z_p = u_q − z_q`. The
  camera looks down and forward along the screen's vertical, so moving toward it along that ray
  raises both `u` and `z` by the same amount; therefore the point with the larger `u` (and so
  the larger `z`) is the nearer one. Equivalently `n = sy + z`, an exact integer for pixel art
  at 1× (`sy` and `z` are whole art pixels).
- Range: the world's ground rows run to `(1280 + 448) · 16 = 27 648` px, heights to
  `15 · 16 + 511 = 751` px, so `n < 32 768`: **16 bits hold the nearness of every pixel of the
  world exactly**. The home region uses the same numbers in its own grid offset by its origin.

Consequences used below: an upright actor (a vertical card standing at its feet) has one
nearness for all its pixels, its feet's `u`; a box's pixels have nearness within its
footprint's ground-row range, whatever its level; elevation decides between two things only
where their footprints overlap (one over the other).

### 1.2 Every drawable is a box

`Box { foot: FRect (tiles), z0, z1: px above level 0, band, id }`. `id` is stable and
deterministic: `(kind, map item index or actor key, piece index, part)`, never a page or a
pointer. How each class makes its box:

| Drawable | `foot` | `z0` … `z1` | Notes |
|---|---|---|---|
| Item (unsplit, ≤ 8 × 8, no walk tiles) | its footprint | ground of its origin tile … `+ h` (geometry `h`) | the anchor's level, as drawn |
| Landmark piece | the piece's rectangle (≤ 8 × 8) | as its item | pieces partition the item's pixels (world-tech §1.3) |
| Walk-run piece ("roof above you") | its 1 × n run | floor `+ headroom` (48 px) … top | walk tiles carry nothing below the headroom (§5 W1), so the piece starts there |
| Floor piece (stair flight, walk floor) | its rectangle | ground … highest `walk_z` + tread (2 px) | the treads under a walker |
| Stair or ramp item | its footprint | foot level … head level | a flight wider than 1 tile is split into floor pieces per tread row (§5 S4) |
| Deck (walkable item: bridge, quay, mole, pier) | per piece, 1 × n along the span | deck underside (`under`, §5 O1) … parapet top | the water or road under it is ground |
| Raised ground tile (top and faces) | its tile | 0 … `L · tile.level` | only tiles that can hide something enter the sort (§1.5 e) |
| Actor (walker, animal, cart, figure) | a square of side `2 · 0.2` tiles round its feet | `floorZ` … `+ sprite height` | ships and carts too: their depth is their keel or axle point, not their hull's area (§1.5 h) |
| Carried goods, riders, a butterfly on the hat | the carrier's box | the carrier's | `sub = carrier.sub + 1`: always right after the carrier |
| Flyer (bird, butterfly, insect, kite) | the square round the ground point under it | ground + altitude … `+ sprite height` | §1.5 g |
| Effect with depth (smoke at an emitter, petals, moths, ripples) | the square round its emitter | the emitter's height … `+ size` | particles are boxes in the actor merge, within their budget |
| Ghost, fade, placement preview (home) | the item's footprint | as the item | the build tool's ghost is sorted, not overlaid |

The depth-sorted band holds only boxes. Everything flat (ground, decals, shadows, glow, weather,
markers) is in a band of its own and needs no box (§2).

### 1.3 The comparator

```
// a is drawn before b (b is nearer). Called only for pairs whose screen rectangles overlap.
bool before(const Box& a, const Box& b):
    // 1. Footprints separated along x: the one with the smaller x is behind.
    if (a.foot.x1 <= b.foot.x0) return true;    if (b.foot.x1 <= a.foot.x0) return false;
    // 2. Along y, the same.
    if (a.foot.y1 <= b.foot.y0) return true;    if (b.foot.y1 <= a.foot.y0) return false;
    // 3. Footprints overlap: one is over the other. Separated in height: the lower is behind.
    if (a.z1 <= b.z0) return true;              if (b.z1 <= a.z0) return false;
    // 4. Overlapping in all three (an intersection, or a thing partly under another):
    //    the higher base is nearer, then the smaller nearness, then the id.
    if (a.z0 != b.z0) return a.z0 < b.z0;
    if (nearness(a) != nearness(b)) return nearness(a) < nearness(b);
    return a.id < b.id;
nearness(box) = (foot.x0 + foot.x1 + foot.y0 + foot.y1) · hh / 2 + (z0 + z1) / 2   // tie-break only
```

Why this and not today's `behind`: (1) and (2) are today's axis test; today's test then falls
back to footprint centres whenever both axes or neither separate, which is right for
side-by-side sprites but wrong for anything over anything (a deck over a boat, a roof over a
walker), because centres ignore height; (3) is the missing case (the separating plane is
horizontal: the camera looks down, so what is above is nearer). Two cases that today's code
writes as special rules fall out of (3) and (4): the walk-run piece is drawn after a walker
standing under it (its `z0` is the floor plus the 48 px headroom: above a walker's `z1` rule 3
decides, and a tall walker whose head reaches into the roof still has the lower `z0`, so rule 4
decides the same way), and the floor piece is drawn before a walker on it (the walker's `z0`, the
tread, is above the floor piece's base).

**Properties.**

- *Antisymmetric and total on a pair*: exactly one of `before(a, b)`, `before(b, a)` holds for
  `a ≠ b` (every branch is decided by a strict comparison or by distinct ids).
- *Acyclic where the world is ground-standing* (every box's footprint disjoint from every
  other's that its screen rectangle meets, the common case: buildings, pieces, trees, people on
  the ground): two such prisms overlap on screen only if their footprints' sweeps along the
  view's ground direction `(1, 1)` meet, and the "is behind along `(1, 1)`" relation of disjoint
  convex sets in the plane has no cycle (Guibas and Yao 1980: disjoint convex objects can always
  be translated one by one in any fixed direction without collision; a cycle would block that).
  Rules (1) and (2) agree with that relation for rectangles whose sweeps meet.
- *Stacked boxes* (overlapping footprints: decks, roofs over walk runs, floors) can in principle
  close a cycle with a third box beside them; the data rules make this impossible in practice:
  overhead pieces are split to 1 × n runs along the passage, movers have point-sized footprints,
  and a mover's footprint lies wholly inside or wholly outside each overhead piece (§5 O1–O3).
  This is not left to faith: the whole world's static boxes are scanned for cycles at build and
  in a test (§6.3), and the runtime sort reports any cycle it has to break (debug view, log once
  per pair) instead of hiding it.
- *Strict weak ordering of the keys*: the per-frame key `(band, rank, sub)` is a strict total
  order (ranks are distinct positions in one sequence), hence a strict weak ordering; the
  comparator itself is never handed to `std::sort` (it is not transitive across non-overlapping
  pairs, which is why the order is a topological sort, §1.4).

### 1.4 The order

1. **Bands** first (§2): a drawable of band `B` is drawn after every drawable of a lower band.
2. **Inside the depth-sorted band**: edges from `before` between every pair whose screen
   rectangles overlap (the `ScreenGrid` of `render/depth.hpp`), then Kahn's topological sort.
   Among the ready elements the next one is chosen by (bound page first, to keep draw calls
   down: any order of mutually independent elements is correct), then smallest `nearness`, then
   smallest `id`. Today's `PageOrder` already does exactly this; it gains the height rule and the
   stable id.
3. **Static and moving**: the static elements are sorted on a worker over a region larger than
   the view (as today). Each frame, the actors and the static elements whose screen rectangles
   meet any actor (the *touched set*, typically a few hundred) are sorted together by the same
   rule, with the static order kept as edges between overlapping touched statics; the result is
   spliced into the static order at the touched statics' positions. This replaces
   `ActorMerge`'s bound propagation, whose crossing bounds today keep an actor "seen" after a
   static in front of it (`hi = max(hi, lo)`). Cost: one Kahn pass over the touched set, the
   same order of work as today's bounds and pairs, allocation-free once warm.
4. **Determinism and stability**: the order depends only on the set of boxes (camera position
   enters only through which elements are gathered and culled, never through a key), ties go to
   `nearness` and the stable id, pages only choose among independent elements, so a frame and
   its replay are identical and a pan never flips two overlapping things. Culling removes
   elements but never reorders the rest (a topological order restricted to a subset is still a
   topological order of that subset).
5. **Where the order is a constraint of no pair** (things whose screen rectangles do not meet),
   any position is correct; the oracle (§6.1) checks only overlapping pairs, which is all that
   can be seen.

### 1.5 The hard cases, one by one

a. **Footprints larger than one tile, and pieces.** A footprint up to 8 × 8 is one box. Larger
   ones, and any with walk tiles, are split into pieces by the art tool (world-tech §1.3); each
   piece is a box with its item's heights. A landmark whose geometry lists pieces but whose page
   has no piece art is a data error (§5 P2), not a reason to draw the whole sprite at one rank
   (today's fallback in `Gatherer::run`, which makes a correct order impossible).

b. **Things that span cells and chunks.** Boxes live in the world, not in cells: the static
   sort runs over a gathered region whose rectangle covers every sprite meeting the view
   (`Reach`), so a landmark crossing a cell or chunk edge is one element (or its pieces) in one
   order. Cached cells (§3) are drawn from that order clipped to the cell; a sprite crossing two
   cells is drawn into both with the same rank, so the seam is exact.

c. **Elevation, stairs and ramps; an actor climbing.** An actor's `z0` is `floorZ`, interpolated
   along a stair as today (`placeOnTrack`); its footprint is the square round its feet, which
   moves across the flight's floor pieces. Against a floor piece its `z0` is at or above the
   tread (rule 3 or 4: the walker is over the tread); against the flight's parapets (non-walk
   pieces beside the run) rule 1 or 2 decides by position, so a walker passes behind the far
   parapet and in front of the near one. Elevation never reorders things whose footprints are
   disjoint (§1.1): a house below the Acropolis and a person on top of it are ordered by where
   they stand, which is what the eye sees.

d. **Bridges and anything one can be under and over.** The deck is split into 1 × n pieces
   along the span, each a box from the clearance `under` (geometry, §5 O1) to the parapet top;
   piers and abutments are their own pieces from the ground up. A boat under the span has a
   point footprint inside the deck piece and `z1` ≤ `under` (lanes under a bridge are for boats
   that fit, §5 O2): rule 3 puts it before the deck. A walker on the deck stands at the deck's
   `walk_z` with its footprint inside the same piece: rule 3 or 4 puts it after. Arches, gates
   and porticoes work the same way: the passage is a walk run whose piece starts at the
   headroom.

e. **Raised ground.** A raised tile `Q` (level `L > 0`) enters the depth-sorted band when it can
   hide anything behind it: a tile `P` behind it (`P = Q − (a, b)`, `a, b ≥ 0`,
   `a + b ≤ L − L_P + 1`) that holds an item **or is walkable** (today only items count, so
   people walking behind a hill or a terrace edge are drawn over it). The rule is static and
   per chunk; world-tech V11 bounds how many tiles it adds (≤ 25 % of a region's walkable
   tiles hidden).

f. **Interiors of colonnades and gates.** Columns stand on their own 1 × 1 non-walk pieces with
   walk tiles between (world-tech §1.3); a walker on a walk tile is ordered against each column
   by rules 1 and 2: after the columns behind it, before the ones in front. The roof over the
   walk tiles is the walk-run piece, after the walker by rule 3/4. No special case remains.

g. **Flying things.** A flyer's box stands on the ground point under it with `z0` = that
   ground plus its altitude. Over open ground it orders like a person; over a roof its
   footprint overlaps the roof's piece and its `z0` above the roof's top puts it after (rule 3);
   behind a tower it is hidden by it (rule 1/2). Today's home rule "flyers after everything" is
   replaced; the butterfly on her hat is a rider (h).

h. **Carried goods, riders, ships and carts.** Goods, a rider baked into the mount's sprite, a
   butterfly on the hat: the carrier's box and `sub + 1`, so nothing can come between them.
   Ships and carts are long, but they move and must pass under bridges and beside quays: their
   depth is a point (the keel's or the axle's centre), their screen rectangle their whole
   sprite. A ship moored beside a quay is ordered against the quay's 1 × n pieces by that point.

i. **Ties.** Rule 4 ends in the stable id; the topological sort picks by bound page, nearness,
   id. No floating-point key is compared without a deterministic fallback, so there is no
   flicker between frames and two runs are byte-identical (`determinism_check`).

j. **The home inside the world.** The home is one element of the world's static sort (`Hole`,
   its footprint the 40 × 40 rectangle) at native zoom, as today: its scene draws at that rank
   with its own order inside, which obeys this same comparator (home items are boxes, home
   actors and flyers as above). At ½ and ¼ the same rank splits the world's cached cells that
   overlap the hole into a part before and a part after it (§3.3).

---

## 2. The global layer list

Every drawable class the game has, in exactly one band. Bands are drawn in this order at every
zoom; "sorted" bands use §1.4, "flat" bands have a fixed rule inside them. This table is the one
place where the order of everything is written down: code names the band (`enum class Band`
in `src/render/bands.hpp`, shared by the home scene and the world renderer) and never decides an
order of its own.

| # | Band | Inside the band | What belongs here |
|---|---|---|---|
| B0 | **Sky** | flat | sky gradient, stars, the sky behind the world's edges |
| B1 | **Far backdrop** | flat, by edge then position | backdrop strips behind the north and east world edges; the sea and haze beyond the grid (`drawBeyond`) under them, never over them |
| B2 | **Ground** | flat, diagonal tile order (`tx + ty`, then `tx`) | terrain bases and overlays, water and its animation, faces under tile edges stacked by level, the cap band; the home's ground; cached as level-0 cells |
| B3 | **Ground decals** | flat, as B2 | paths, wet ground, puddles, snow cover on the ground, clutter baked into cells, the placement grid, nook areas, footprint and tile highlights (`ui/tile_*`) |
| B4 | **Shore foam and water surface effects** | flat | foam by land mask, ripples, rain rings, fish rings, petals floating on water, under-water visitors (the home's fish, drawn faded) |
| B5 | **Cast shadows** | flat, one composited layer | item and piece shadow sprites, actor and flyer ovals, cloud shadows; drawn into one layer, composited once (no double darkening); on the shader path replaced by height-field shadows in the resolve |
| B6 | **The world in depth** | **sorted** (§1.3–§1.4) | items, landmark pieces, walk-run and floor pieces, stairs and ramps, decks, raised ground tiles that hide something, every actor (walkers, animals, carts, ships, figures, the resident, visitors), carried goods and riders, flyers, effects with depth (smoke, petals in the air, moths, sparks, falling leaves), placement ghosts and fades, the home as one element |
| B7 | **Occluder fade** | sorted with B6 (same rank, drawn instead of the element) | the dithered or alpha fade of a roof or landmark over the pointer, a followed figure or the resident; never a second draw on top |
| B8 | **Weather** | flat, by screen row | rain streaks and splashes, snowflakes, mist banks, the cloud deck on the shader path (depth-tested particles on the shader path, `graphics-plan.md` E7) |
| B9 | **Grading** | one pass | the clock's ambient times the region grade (multiply), haze; or the shader path's resolve |
| B10 | **Glow and lights** | flat, additive, **occluded** (§4.4) | item and piece glow layers, emissive actors (fireflies, torches carried), light pools, lamp halos, moths' shine; drawn after grading, hidden where something nearer stands in front of the light |
| B11 | **Sky effects** | flat | rainbow, shooting stars, lightning flash, bloom |
| B12 | **World-space markers** | flat, by nearness of the anchor | hover outline of the actor or landmark under the pointer, speech bubbles and hearts, card anchors and place markers (`ui/marker_*`), the placement cursor's valid/invalid diamonds, journal pins |
| B13 | **Screen overlays on the world** | flat | haze composite, the postcard frame, the photo bar's guides |
| B14 | **Interface** | the UI's own order | glass panels, drawer, docks, tray, sketchbook, cards, toasts, tooltips, the profiler |
| B15 | **Debug** | flat | the debug views of §6.5 |

**Rules.**

1. A drawable has one band for its whole life. If it must sometimes be over and sometimes under
   another class, both are in B6 and the comparator decides; a new band is never the answer to
   an ordering bug.
2. **Adding a class**: if it stands somewhere in the world and something can be in front of it
   or behind it, it is a B6 box (§1.2 says how to make its box: footprint, `z0`, `z1`, `id`);
   if it lies flat on the ground it goes to B3 or B4; if it is light it goes to B10 and must be
   occludable; if it is about the world but not of it (an outline, a bubble, a marker) it goes
   to B12. The class is added to the table above in the same change, and to the order oracle's
   class list (§6.1).
3. A flat band never reads the depth-sorted band's order, and the depth-sorted band never
   contains a flat thing; the only coupling is B10's occlusion (§4.4) and B5's coverage.
4. Speech bubbles, hearts and z's float above their actor and are not occluded (they are
   B12: they must stay readable); the actor itself is.

---

## 3. Every zoom level and cache

### 3.1 What each level draws today (0217232) and what is wrong

| Level | Static content | Actors and the home | Fault |
|---|---|---|---|
| Native 1×, 2×, 3× | level-0 cells (ground, faces, foam, cap bands) cached; items, pieces and raised tiles that hide an item gathered on a worker and drawn live in `PageOrder`'s order | merged into the static order by `ActorMerge` (bounds, page-aware); home drawn at the hole's rank | merge bounds can cross (actor drawn after a static in front of it); height not in the comparator; raised ground hides items only; glow unoccluded |
| Half ½ (level-1 impostor cells) | 1024-px blocks of ground, shadow layer and every static element in order, halved with filtering, cached | **every actor on open ground drawn over the cells** (`coarse_`, sorted by `x + y` only), actors on walk tiles under roofs skipped; the home's objects drawn over the cells | people on roofs (the owner's bug); the home's trees and cottage over the world's buildings south and east of the home |
| Quarter ¼ (level-2 impostor cells) | the same, halved twice | the same | the same |
| Overview | the generated map image | none | — |

### 3.2 The options for actors at ½ and ¼

The cached city is a picture; the actors move. The question is how an actor in the picture's
depth is hidden by what stands in front of it.

| Option | How | Memory | CPU per frame | GPU / draws | Exactness | Verdict |
|---|---|---|---|---|---|---|
| A. Cells split back/front at actor rows | rebuild the cells touched by actors each frame, or keep layers per row band | a layer per row band (×4–8 cells) | rebuilding impostors (1–3 ms a block today) | +1 draw per layer | exact | rejected: rebuild cost breaks the 2 ms budget; row bands cannot follow moving actors |
| B. Per-pixel nearness companion + shader test | each impostor cell stores 16-bit nearness per texel (§1.1); the actor's fragment shader samples it and discards where the city is nearer | RGBA8 companion: +100 % of the cell cache (+96 MiB at the default budget); **+0 if shared** with the impostor companion `graphics-plan.md` §3.3 already plans (normal 8+8, height 16: nearness = texel row + height) | 0 | +1 fetch per actor pixel (< 0.02 ms at 1440p for 800 actors); actor draws under one render state (+1–3 draws) | exact per texel (½: 2 world px) | **the GPU path**, when the companion lands (E5) |
| C. Redraw occluders over actors | gather the static elements at ½ and ¼ as at 1× and draw the ones in front of each actor again over it | none | gather 4–16× more elements (Rome at ¼: ~30 000) on the worker; 0.3–0.8 ms main thread to emit | +20–60 draws (occluders on many pages) | exact (painter's) | rejected: draw calls over the 40 budget, worker load at ¼ |
| D. **Cut at the covering row** (CPU, both paths) | a per-tile *top* field of the static city (§3.4); for each actor, the screen row below which something nearer covers its column; draw only the actor's sprite rows above it (a sub-rectangle quad on the same page, no clip rect) | 1 byte per tile: 573 KB for the world (or per chunk on demand) | ≤ 24 lookups per actor: ~0.05 ms for 800 actors | 0 extra draws | exact for box-shaped occluders whose top edge is level across the actor (± 2 px at ½ on a roof slope); a gap narrower than the actor (between columns) is closed | **first fix, both paths; stays the Classic path's coarse test** |

**Recommendation.** D now, in both paths: it fixes the visible bug in one engine task, costs
nothing measurable, and is deterministic for screenshots. B when the shader path's impostor
companion exists: the same rule per texel, so the two paths agree except inside gaps narrower
than an actor at ½ and ¼ (2–4 px wide), which the golden tests mask (§6.4). The 1× path stays
the exact painter's order in both paths.

### 3.3 The home at ½ and ¼

The hole is one element of the static order (§1.5 j). When an impostor block whose rectangle
meets the hole's screen rectangle is built, its static elements are drawn in order into the
block **up to the hole's rank**, and those after it into a second, *front* block (only the
blocks meeting the hole: 4–9 cells at ½, 2–4 at ¼; +4–9 slots of 1 MiB, +1 draw). The frame
draws the cells, then the home's ground and objects (cut against the world's top field like any
actor where they stand at its rim), then the front blocks. The home's own actors are cut by D
against the home's items' tops as well, so a hen behind the cottage is hidden at ½ as at 1×.

### 3.4 The top field

`top(t)` is the highest point, in px above level 0, of anything static standing on tile `t`
(ground at its level, items, pieces, floors), from the geometry: per item and rotation the art
tool emits `tops: [byte per footprint tile]` in `<set>.geom.json` (max voxel height on that tile
above the anchor; home items in the home geometry), and the engine adds the tile's level. Walk
tiles report their floor, not the roof above them (`roof` holds the roof's height separately,
so an actor on a walk run is covered from the roof's row). Built per chunk on the worker at
load, updated with the home's edits, 1 byte per tile (`top / 4`, rounded up).

**The cut** for an actor whose feet are at `(fx, fy)` with nearness `n_a` and screen column
`x_a`: walk the tiles straight down the screen from the feet, `(⌊fx⌋ + k, ⌊fy⌋ + k)` and their
two half-overlapping neighbours, for `k = 1 … K` (`K` = tallest top in the region / `tile.h`,
≤ 24); each tile with `top > 0` covers the actor's column from its top edge at that column,
`row(t) = sy(t) − top(t) + |x_a − x(t)| / 2`, down to its ground. The cut row is the smallest
such row; the actor's sprite rows above it are drawn, the rest not; an actor whose head is below
the cut is skipped. A tile in the same row as the feet counts only when the comparator puts it
in front (an actor on a walk run is covered by its `roof`).

### 3.5 Cost against the budgets

| Item | Today | After D | After B |
|---|---|---|---|
| Memory | cell cache 96 MiB (+ up to 1.5× by window), page slots | + 0.6 MB top field, + 4–9 MiB home front blocks | + 0 beyond `graphics-plan.md` E5's companion (+96 MiB if built alone) |
| CPU at ½/¼, 800 actors | sort by `x + y` | + 0.05 ms cut | same |
| Draw calls at ½/¼ | cells by page + actors by page | + 1 (home front blocks) | + 1–3 (render state) |
| 1× | merge 0.2–0.8 ms | touched-set sort ≤ the same (§1.4) | same |

---

## 4. Both render paths

### 4.1 The Classic path (painter's order)

What is drawn in which order is §2 and §1.4; what must be split for a painter's order to be
correct at all:

- every footprint over 8 × 8 and every item with walk tiles: pieces (world-tech §1.3);
- every walk run: its own 1 × n piece starting at the headroom;
- every stair flight wider than one tile: floor pieces per tread row, parapets as their own
  pieces;
- every deck one can pass under: 1 × n pieces along the span with `under` set;
- nothing else: trees, houses, statues, carts and people are single boxes.

At ½ and ¼ the Classic path uses the cut (§3.2 D). Glow is occluded by silhouettes (§4.4).

### 4.2 The GPU path (per-pixel nearness)

SDL 3.4's renderer gives custom fragment shaders (`SDL_GPURenderState`: a fragment shader, up to
five extra samplers) but **no depth attachment**: a depth test is a shader that samples a
nearness texture written in an earlier pass and discards. That decides the design:

1. **Static nearness is written where static content is cached**: the impostor companion (and,
   when the shader path draws level-0 cells and items into its packed scene, a nearness target
   beside it). Each static pixel's nearness is computed in the sprite shader from what the
   packed page already holds: `n = (anchor.y − oy + row) + level · tile.level + h` (world px at
   1×), the anchor already raised by the level, `h` the packed pixel's height (`graphics-plan.md`
   §2.2). No new art channel is needed: **the height the packed page carries is the depth**.
2. **Encoding**: 16-bit unsigned nearness, `R = n >> 8`, `G = n & 255` in an RGBA8 target
   (formats SDL's renderer can sample), always sampled **nearest**, never filtered (filtering
   mixes the bytes). Impostor halving takes one texel of each 2 × 2 by the same rule as the
   colour's coverage (nearest), not an average.
3. **Actors** test per pixel: an actor is an upright card, all its pixels at its feet's nearness
   `n_a` (§1.1); discard where `n_static > n_a + ε` with `ε = 6` px (a third of a tile row,
   so a person against a wall is not eaten by the wall's own foot). Actors among themselves stay
   in painter's order by the comparator (they are few per pixel and need blending).
4. **Alpha edges**: nearness is written only by pixels with alpha ≥ ½ (the generator's sprites
   have hard edges; filtered impostor edges take the nearer texel); translucent things (shadows,
   glow, smoke, haze, weather) never write nearness.
5. **Shadows** are a band (B5) and never depth-tested; on the shader path they come from the
   height field in the resolve and fall over actors by the same field.
6. **Additive glow** (B10) is tested against nearness: a light's fragment is discarded where the
   static nearness at that pixel is nearer than the light's own (from its emitter's position),
   and live actors in front of a light mask it through their coverage (§4.4).
7. **The Classic path stays the visually identical fallback at 1×** (both are the painter's
   order; the GPU path adds nothing to 1× ordering until it draws a packed scene, and then the
   painter's order still decides inside it). At ½ and ¼ the two differ only where an actor shows
   through a gap narrower than itself (B shows it, D hides it): the golden tests compare the two
   paths with those pixels masked.

### 4.3 Which part relies on which path

| Part | Relies on | Why |
|---|---|---|
| Static order at every level (cells, impostors, 1× objects) | the comparator and the topological sort (both paths) | exact, cached, no per-frame cost |
| Actors at 1× | the comparator, touched-set sort (both paths) | exact, cheap, needs no shader |
| Actors and the home at ½ and ¼ | the cut (Classic); per-pixel nearness (GPU, when the companion exists) | the cut is right everywhere a box is; the texel test adds the gaps |
| Glow | silhouettes (Classic), nearness test (GPU) | §4.4 |
| Weather particles | flat band (Classic); nearness-tested (GPU, E7) | rain behind a roof is hidden on the GPU path only: an accepted difference |
| Picking | the order and per-pixel alpha (both) | §4.5 |

### 4.4 Glow that something stands in front of

Today every visible element's glow is added after grading with nothing over it, at every level,
so a lamp behind a column or a person shows through them and light pools fall on roofs. The rule:
a glow is drawn in its owner's rank, and everything drawn after it in B6 that overlaps it is
drawn again **as a black silhouette** into the glow layer (the home scene's glow pass already
does exactly this, `Scene::drawEntries(p, true)`), including actors. Only elements whose boxes
meet a glow box take part (the home's `glowRects_` filter), so the cost is a fraction of a frame's
draws at night. At ½ and ¼ the glow of static lights is baked into a glow companion of each
impostor block with the same silhouettes (built with the block, 1 layer per block at half
resolution: +24 MiB at the default budget, or shared with the shader path's light list), and
actors cut by D are cut in the glow layer too.

### 4.5 Picking, cards and markers

What the pointer is over is the topmost drawable under it by the same order: walk B6 in reverse
draw order and test the sprite's alpha at the pointer (the art pixel), not its screen rectangle.
This fixes the class of "the click opened the wrong landmark's card" (a large landmark's
rectangle covers much more than its pixels). Markers and card anchors (B12) anchor at the
landmark's origin tile raised by its `h / 2`, never at a rectangle's corner.

---

## 5. Where things may be: the rules, as validators

The renderer draws what the data says; it must never be the place that keeps people off roofs.
These rules make "who may stand where" a build-time fact. **Engine walk model** below means the
rules of `src/world/world_map.cpp` (`index`, `floorZ`, `edgeZ`, `walkNeighbours`, stair heads),
mirrored line for line by `tools/worldgen/worldgen/walk.py` (`EngineWalk`); every rule is checked
against that mirror, never against a second idea of walkability. Each rule names its tool, its
level (error fails the build) and its fixture: a failing case from the audit (grid tile, layer)
that the rule's test must reject. The audit's full offender list is in
`out/reports/draw-order-audit.md` part 1.

### 5.1 Pieces, walk tiles and floors (art: `tools/artgen/datavalidate.py`, per model and rotation)

| # | Rule | Level | Fixture |
|---|---|---|---|
| P1 | An item with walk tiles, or a footprint over 8 × 8, lists `pieces`; walk tiles form 1 × n pieces of their own; non-walk rectangles never mix walk tiles (world-tech §1.3) | error | `world.royal_station` (r0–r3, 3 walk tiles, no pieces), `world.sheepfold` (2 walk tiles, no pieces), `rome.aqua_claudia` (m0, m5, m10: a walk tile, no pieces) |
| P2 | Every listed piece has art for every rendered rotation (`item/<id>/base/r<k>/p<i>/f0`); a missing piece is an error, not a whole-sprite fallback | error | a model with `pieces` and its piece sprites deleted |
| P3 | `tops` (one byte per footprint tile, §3.4) and, for walk tiles, `roof` are emitted for every item and rotation, home items included | error | a model with no `tops` |
| W1 | A walk tile holds no voxel between 2 px and the headroom (48 px) above its floor (`walk_z` or 0) | error | today's column-on-walk-tile fixture |
| W2 | Every walk tile is reachable from the footprint's edge through walk tiles and stairs, by steps the engine walk model allows (heights from `walk_z`) | error | a closed courtyard model |
| W3 | `walk_z` of 4-adjacent walk tiles differ by at most half a level unless both are in one floor piece (`floor_pieces`); a walk tile on the footprint's edge has a `walk_z` within half a level of the ground outside at the item's level (or is a stair's foot or head) | error | `athens.harbour` walk tile (370, 689), `walk_z` 5, unreachable |
| W4 | `walk_z` never exceeds the item's `h`; a walk floor more than 3 levels above the item's level is listed in the model as a terrace (`terrace: true`) or is an error (no roofs as floors by accident) | error | none found today (kept as a guard) |
| S1 | A stair's or ramp's treads rise toward `climb`, and `climb` agrees with the catalog `axis` at r0 (or the catalog drops `axis` for kit stairs) | error | `parsa.stair_relief` (`axis: "x"`, climbs across y; world README note 6) |
| S2 | Floor pieces of a flight cover exactly its walk tiles; parapets are non-walk pieces | error | — |
| O1 | An item one can pass under (catalog `crossing` over water or a road, gates, arches, walk runs) declares `under`, the clearance in px above its base, per piece; its deck pieces are 1 × n along the passage | error | `rome.pons_fabricius` (an unsplit deck over the Tiber: barges are drawn over it) |

### 5.2 The placed world (worldgen: `tools/worldgen/worldgen/validate.py`, every build and `--check`)

| # | Rule | Level | Fixture (grid tile, layer) |
|---|---|---|---|
| V3 | Every footprint tile at one level (as today) — **it is not enforced on Pārsa today** | error | `parsa.harem` (390, 44), parsa: levels 10 and 11 |
| V5 | (as today) Walk steps between levels only through a stair or ramp | error | — |
| V17 | (as today) Every graph edge's course walkable step by step under the engine walk model; every node on a walkable tile | error | clean today in all 29 layers; keep |
| G1 | Every region graph is one walk component with its dest nodes (V6 by edges **and** by the engine walk model) | error | — |
| G2 | A graph node never stands on a non-walk tile of a landmark or under a footprint (V17 says "unwalkable"; G2 names the item) | error | — |
| S3 | A placed stair's head side has walkable tiles at `foot + rise` and none at another level that the stair would join; its foot side likewise at `foot` | error | `parsa.hadish_stair_w` (391, 68), parsa: head side (391, 67) at level 10, 13 wanted |
| D1 | Every walkable item on water (deck) meets the bank or another deck at both ends by allowed steps (within a level for decks) | error | `world.mole` (289, 302), base: the step from (288, 302) is 48 px |
| D2 | A walkable item stands on water only if it is a crossing (bridge, ford, quay, mole, pier, boardwalk); plants and reeds are never `walkable` | error | `world.t_reeds` (373, 184), (379, 203), (397, 204), base; (184, 263), (171, 265), euphrates_crossing |
| W5 | Every placed landmark's walk tiles are reachable from outside its footprint under the engine walk model (W2 in place, with the neighbours the layout gives it) | error | `rome.trajan_baths` (44, 1010), rome: the south run (65, 1037)–(65, 1039) ends at (65, 1040), not walkable; 63 of 126 walk tiles sealed |
| L1 | Every slot spot stands on a tile walkers may stand on, or is a seat (`z > 0`) on its own item's walk tile; a spot under another item is an error (a layout collision); a spot inside its own item's non-walk tile is an error (the geometry must put it on the step outside, or the catalog must make it `beside`) | error | `rome.curia` senator under `rome.lapis_niger`; `rome.pantheon` visit under `rome.pantheon_court`; `parsa.p_workshop` work ×21; `athens.g_farmstead` door ×20; `rome.mutatio` change ×18 (88 spots in all, audit part 1) |
| L2 | Every slot spot is on a walk component some graph of its region reaches (V7 as written; **today it does not catch these**: extend it to the base layer and to the engine walk model) | error | `world.sheepfold` pens and gates (Anatolia, Iranian plateau), `world.royal_station` (Anatolia, Taurus): 93 spots on islands |
| L3 | Mooring spots are on water a lane reaches; other spots are never on water | error | — (moorings on water are correct today) |
| O2 | Lanes under a crossing carry only boats whose sprite height fits its `under` | error | barges on the Tiber under `rome.pons_fabricius` |
| O3 | No mover's lane or course runs along the edge of an overhead piece (half in, half out); courses cross overhead pieces through whole tiles | warning | — |
| T1 | `tops` and `roof` (§3.4) of every placed item fit the level grid: an item's top ≤ 15 levels + its `h` | error | — |

### 5.3 The life data (worldgen life checks and `lifeinfo problems`)

| # | Rule | Level | Fixture |
|---|---|---|---|
| A1 | A wander target is at least 2 tiles from where the walker stands (or the walker idles) | engine rule, tested in `life_tests` | the 42 milling walkers of the audit (Forum, Agora, Ostia, Brundisium, roads) |
| A2 | A cast held in place (an event waiting, a procession's head stopped) plays its idle animation, never `move` | engine rule | the line of ten `rome.citizen` at (88.2–88.9, 1062.3–1066.0), Forum 10:00 |
| A3 | `move`-family animations phase by distance walked only (never by the clock) | engine rule | `actor_looks.cpp` `cycleFrame` below 0.05 tiles/s |
| A4 | An actor whose sprite is longer than a tile (horse, ox, camel, cart, ship) keeps its feet at least half its length from any non-walk tile beside its course (life's lateral offset), or the comparator cannot place its overhanging body | warning | horses on `parsa.great_stair`'s landing (341, 88) drawn over its parapet |
| A5 | Every actor kind states its sprite height (`h`) and, if longer than a tile, a point footprint (ships, carts, oxen teams) | error | — |

---

## 6. Tests that make violations impossible to miss

### 6.1 The order oracle (`tests/order_oracle.cpp`, engine; runs in `ctest` both presets)

For a scene, every pair of drawables whose **drawn pixels** overlap (sprite alpha ≥ ½ at the
same art pixel, not just their rectangles) must be drawn so that the nearer by the model wins:
the oracle computes, for each overlapping pixel, both surfaces' nearness from §1.1 (static
sprites: from the packed page's `h`, or from the box's `z` range where no packed page exists;
actors: their feet), and asserts that the one drawn later is the nearer (Classic) or that the
depth test keeps the nearer (GPU). Scenes:

- **Fixtures** (hand-made, small): a colonnade with an actor on every walk tile; a gate with a
  walk run and actors passing through; a bridge with a boat under it and a walker on it; a
  stair with walkers on every tread and beside the parapets; a terrace edge with walkers behind
  and on top; a pinwheel of pieces; a flyer over a roof and behind a tower; goods on a carrier;
  a long ship beside a quay; the home's cottage with a hen behind it and a butterfly on her hat.
- **The real world, sampled**: 200 random views (seeded) over Rome, Athens, Pārsa, two towns and
  two roads at 1×, with city life settled at a busy hour; every overlapping pair checked.
- **Coarse levels**: the same views at ½ and ¼, checking that no actor pixel is drawn where the
  top field (Classic) or the impostor nearness (GPU) says something nearer covers it, and that
  an actor in the open is drawn.

A failure prints both drawables (class, id, tile, band, key, ranks) and writes a cropped shot
with both outlined.

### 6.2 Properties of the comparator (`tests/order_props.cpp`)

On 100 000 random box pairs and triples drawn from the classes of §1.2 (seeded): antisymmetry
(`before(a, b) != before(b, a)` for `a ≠ b`); no 3-cycle among ground-standing boxes whose
screens overlap pairwise (Guibas–Yao; a counterexample fails the test and prints it); for
stacked boxes satisfying §5 O1–O3, no 3-cycle either; stability: translating every box by whole
tiles, or moving the camera, leaves the order of overlapping pairs unchanged; determinism: the
same input in shuffled order gives the same output order; the touched-set sort (§1.4) equals a
full re-sort of statics and actors on random scenes (today's "actor merge equals a full
re-sort" test, now exact, crossings included).

### 6.3 The whole-world cycle scan (`worldinfo order`, run by a test and by `build.sh --check`)

Sorts every chunk's static boxes (items, pieces, raised tiles that hide something) with the
runtime comparator and reports every cycle Kahn's sort has to break, with the boxes involved.
Zero is the gate. It also reports pieces without art, items with walk tiles and no pieces, and
decks without `under`.

### 6.4 Golden shots of the hard places (`tests/scripts/order/*.lcs`, both paths)

Each at 1×, ½ and ¼, by day and at night, with city life settled and the clock pinned, asserting
image statistics (as `expect luma/color/lit`) in the regions where the fault would show, and
compared against approved frames: the Forum and the Basilica Ulpia (people behind the
basilica at ½: no actor-coloured pixels on its roof), the insulae south of the Capitol, the Pons
Fabricius with a barge under it, the Capitol's stair, the Propylaia with the Panathenaic
procession passing through, the Stoa Poikile's colonnade, the Pārsa Great Stair with horses, the
Gate of All Lands and the Apadāna's portico, Ostia's quays, the home's east and north borders
with the world at ½, the cottage with the resident and the butterfly, a lamp-lit street with a
walker passing in front of a lit window. Pixels where an actor may show through a gap narrower
than itself are masked when the two paths are compared.

### 6.5 The debug view (`F4` cycles, also script verb `set debug order depth|band|key|off`)

- **depth**: every drawn pixel coloured by its nearness (a repeating hue ramp every 64 px, so
  steps are visible), actors in white outline; an actor whose colour does not match the surface
  it stands on stands in the wrong place.
- **band**: every pixel coloured by its band (§2's table as a legend).
- **key**: under the pointer, the topmost drawable's class, id, tile, `z0…z1`, band, rank and
  `sub`, and the drawables it was ordered against (the edges into and out of it), with any
  broken cycle marked in red.
- **cut**: at ½ and ¼, each actor's cut row as a line and the tiles that decided it.

### 6.6 Where each test lives

| Test | File | Label |
|---|---|---|
| comparator properties, touched-set sort, fixtures oracle | `tests/order_props.cpp`, `tests/order_oracle.cpp` | unit |
| real-world oracle | `tests/order_oracle.cpp` (`world` case) | `heavy` on software, normal on `opengl` |
| cycle scan | `worldinfo order` in `tests/world_tests.cpp` | unit |
| golden shots | `tests/scripts/order/*.lcs` | scripted |
| validators | `tools/worldgen/tests/test_order_rules.py`, `tools/artgen/tests/test_datavalidate.py` | tool tests |
| walking in place | `tests/life_tests.cpp` (A1–A3: no actor in a `move` animation over 3 s with less than 0.3 tiles of progress, at the ten places of the audit) | unit |

---

## 7. Work plan

One engine agent at a time in `src/` and `tests/`; art and worldgen beside it. Sizes are one
agent's hours. Each engine task ends warning-free with `ctest` green under `release` and `asan`
and the `--bench` gates at 1080p and 1440p (the city cases included).

| # | Task | Lane, files | Needs | Hours | Frame time | Done when |
|---|---|---|---|---|---|---|
| **O1** | **The coarse cut (the owner's bug).** Top field per chunk from the geometry (`tops` when present, else the item's `h` over its footprint and the tile's level for ground; walk tiles: floor, roofed by the item's `h`), built on the worker; the cut at ½ and ¼ for city actors (sub-rectangle quads, no clip rects), replacing the `coarse_` list's "drawn over everything" and its "skip if under a roof" rule; the debug `cut` view | engine: `src/worldview/renderer.cpp`, new `src/worldview/tops.hpp/.cpp`, `tuning.hpp` | — | 4 | +0.05 ms CPU at ½/¼ with 800 actors; 0 draws | golden shots at ½ and ¼ of the Forum, the insulae, the Propylaia and the Pārsa terrace show no actor on a roof; people in open streets still drawn; the oracle's coarse case passes on 50 views |
| **O2** | **One comparator, one sort.** `Box` and `Band` (`src/render/bands.hpp`), the comparator with height (§1.3) and stable ids in `PageOrder` and the home's `DepthSorter`; raised tiles hiding walkable tiles join the sort (§1.5 e); the touched-set sort replaces `ActorMerge`'s bounds (§1.4); the home's actors placed by the same sort (no "after the last item behind" insertion) and flyers as boxes; riders and goods as `sub` | engine: `src/render/depth.*`, `src/render/scene.cpp`, `src/worldview/order.*`, `gather.cpp`, `renderer.cpp` | O1 | 6 | ±0.1 ms (touched-set Kahn vs bounds); draws unchanged (page-aware choice kept) | comparator property tests and fixture oracle green; the real-world oracle green at 1× on 200 views; the barge under the Pons Fabricius and the procession in the Propylaia drawn right; `determinism_check` green |
| **O3** | **Tests and the debug view**: order oracle (fixtures, real world, coarse), property tests, `worldinfo order` cycle scan, golden scripts §6.4, `F4` debug views | engine: `tests/`, `src/world/worldinfo_main.cpp`, `src/worldview/` | O2 | 4 | 0 (debug only) | all listed tests exist and pass; a deliberately broken comparator fails them |
| **A-O1** | **Geometry for order**: `tops` and `roof` per item and rotation for every set and the home; split `world.royal_station`, `world.sheepfold`, `rome.aqua_claudia` into pieces (P1); decks of every crossing (`rome.pons_*`, `world.bridge_*`, quays, moles) into 1 × n pieces with `under` (O1); validators P1–P3, W3, W4, S1, O1 with fixtures | art: `tools/artgen/`, `assets/atlas/*.geom.json`, set pages where pieces change | — (beside O1) | 6 | 0 | `datavalidate` green on all sets; fixtures rejected; pages within their counts |
| **W-O1** | **World validators**: V3 enforced on every layer, S3, D1, D2, W5, L1, L2 (V7 extended to the base layer and the engine walk model), L3, O2, O3, T1, G1, G2 with the audit's offenders as fixtures in `tools/worldgen/tests/test_order_rules.py` | worldgen core: `tools/worldgen/worldgen/validate.py`, `walk.py`, tests | — (beside O1) | 4 | 0 | `build.sh --check` lists exactly the audit's offenders before the fixes and none after |
| **W-O2** | **Data fixes**: `parsa.harem` level, `parsa.hadish_stair_w` head, `rome.trajan_baths` south run, Rome's colliding slots (curia, pantheon, lacus Iuturnae, Trajan's column, Vesta); the base layer's mole (289, 302), sheepfold and royal-station islands (join them to the roads or move them), slots inside items; the world set's reeds not `walkable` (set catalog: orchestrator or the brief's agent) | the layer builders (rome, parsa, base) and the orchestrator for `assets/sets/world/catalog.json` | W-O1 | 2 per layer | 0 | `build.sh --check` clean |
| **O4** | **Glow, the home's borders, picking**: glow occluded by silhouettes at 1× and baked with silhouettes into a glow companion per impostor block; the home's front blocks at ½ and ¼ (§3.3); picking by per-pixel alpha in reverse order (§4.5) | engine: `renderer.cpp`, `scene.cpp`, `cell_cache.*` | O2 | 5 | +0.1–0.2 ms GPU at night at 1× (silhouettes of elements near lights); +24 MiB glow companions at coarse (or 0 shared with E5); +1 draw at ½/¼ near home | no light pool on a roof, no window glow over a passer-by; the home's border at ½ golden shot; clicks on the Agora pick the drawn landmark |
| **O5** | **Per-pixel nearness on the shader path**: nearness in the impostor companion (`graphics-plan.md` E5) and the actor test shader; the Classic cut kept as the fallback; the paths' golden comparison with gap masks | engine | O4, graphics-plan E4/E5 | 4 | +< 0.02 ms GPU; +1–3 draws at ½/¼ | the coarse oracle passes per texel on the GPU path; Classic and GPU agree outside masked gaps |
| **L-O1** | **Walking in place** (§5.3 A1–A3): `move` animations phased by distance only; held casts and stopped walkers idle; wander targets ≥ 2 tiles; population `speedNow` measured | engine (life): `src/life/city.cpp`, `src/worldview/actor_looks.cpp` | — (the fixing agent's current task) | 2 | 0 | the walking-in-place test of §6.6 at the audit's ten places reports 0 |

**Order.** O1 first (it fixes what the owner sees, and nothing later replaces it: the cut stays
the Classic coarse test and the top field feeds O5's checks); A-O1 and W-O1 run beside it; then
O2 (the model), O3 (the tests that hold it), W-O2 (data, as validators land), O4, and O5 with the
graphics plan's E5. L-O1 is already running.

**Risks.** (1) The touched-set sort in a dense crowd: bounded by the touched set (the bench's
800-actor cases measure it; fall back to splitting the touched set by screen strips if it
exceeds 0.3 ms). (2) The cut is approximate at sloped roof edges and closes gaps at ½ and ¼:
accepted, and O5 removes it on the shader path. (3) Splitting decks and the three walk-tile
items changes pages: one rebuild of the world and Rome sets, within their page counts. (4) The
cycle scan may find real cycles in today's layouts: each is fixed by a split (data) or reported,
never hidden. (5) Glow silhouettes cost draws at night: limited to elements meeting a glow
rectangle, measured in the night bench cases.

---

## 8. Sources

- Shaun Lebron, *Isometric Blocks* (the separating-axis test for isometric boxes, cycles, the
  topological sort): <https://shaunlebron.github.io/IsometricBlocks/>
- L. J. Guibas and F. F. Yao, "On translating a set of rectangles", *Proceedings of the 12th ACM
  Symposium on Theory of Computing* (1980), 154–160 (disjoint convex objects in the plane can be
  moved one by one in any direction: the "behind" relation along a direction has no cycle).
- Jay Teealao, *Isometric: depth sorting* (screen-space bucketing, pair tests, topological
  sort as a pipeline): <https://jayteealao.github.io/Isometric/concepts/depth-sorting/>
- SDL 3.4, `SDL_render.h`: `SDL_GPURenderStateCreateInfo` (a fragment shader and extra samplers
  in the 2D renderer; no depth-stencil target, hence the sampled-nearness test of §4.2).
- `docs/design/world-tech.md` §1.3 (pieces, walk tiles), §3.5 (validators), §4.3–§4.4
  (elevation, the depth order); `docs/design/graphics-plan.md` §2.2 (the packed pixel's height),
  §3.3 (impostor companions); `src/world/README.md` (the engine walk model as implemented).
- `out/reports/draw-order-audit.md`: the fault catalogue, the data offenders and walking in
  place, with shots under `out/reports/shots/draworder/`.
