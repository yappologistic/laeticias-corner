# Layer `corner`

Regions: `corner` (C 0..95, R 0..111) and `seam_dell` (the dell, C 88..95 inside this layer).

Status: first version (WG0).

Built:
- The home region C 40..79, R 40..79 left transparent (the engine writes it from the save).
- Headland at world level 2 with a 2-level `world.coast` cliff where it meets the base's sea.
- The old road (home `path`, 1 wide) along C 79: north past the wayside shrine (C 80, R 20) and
  hedgerows to the world's north edge; south to R 92, east into the dell (level 1) down a ramp,
  south to portal `corner_road_s` (94, 111), where the base road continues to Rome's `aurelia_w`.
- Graph edges through the home rect from (79, 39) to (79, 80) via the gate node (78, 60).
- Track west to a cove (level 1) and the plank jetty at C 33 with a rowboat; the base sea lane
  `corner_portus` leaves from there.
- The home's two west streams and the far pond's creek continue to the coast as `world.river`,
  each as wide as the home's own where it crosses the rim (west meadow two tiles, narrowing to
  one at the cliff's lip); the track crosses the creek on `world.bridge_timber`.
- Two farmsteads (by the south road; by the shrine with sunflowers and beehives), a windmill on
  a track in the beech wood (oaks and pines stand in for beech), meadows, scattered trees,
  flowers, cliff-top rocks; the dell in meadow with tall grass and reeds.

Missing / deviations:
- `world.wayside_shrine`, `world.milestone`, `world.ramp`, `world.river` are provisional ids
  (no `world` set catalog or art yet).
- Sheep and the shepherd are actors (region file, not this layer). No region file yet.
- `world.md` §7's 20 × 20 plot and its wall are replaced by the 40 × 40 home region (world-tech
  §4.0); the home's own road, wall and gate are home content.
