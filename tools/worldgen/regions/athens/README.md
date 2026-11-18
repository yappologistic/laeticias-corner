# Athens layer

Status: complete

Athens at the Panathenaia, summer 432 BC (`docs/design/cities/athens.md`). World rect C 576..735,
R 220..379; local (c, r) = world (C − 576, R − 220); local level 0 = world level 1.

- `layout.py` builds the layer in stages: levels as one array (the Acropolis, hills, edges, stair
  runs carved in), ground, water, ways, landmarks and stair runs, walls, districts, quarters
  (lanes and houses), the Agora and the rock's detail, the Kerameikos, Piraeus, the country,
  named nodes, finishing passes, previews.
- `assets/regions/athens.json` is this region's life and text: theme, district populations,
  figures, groups, events with their routes over the named nodes, chains, sea-lane tokens, cards.
- Portals: `sacred_way_w` (0, 16), `academy_road_n` (4, 0), `acharnai_n` (41, 0), `mesogeia_e`
  (159, 45). Lanes: `kantharos` (its last point meets the plan's Saronic and Aegean lanes),
  `zea`, `mounychia`.

- The Acropolis' slopes are a few tall faces with ledges: north 10 → 5 (the Peripatos' ledge)
  → 2 → 0; south 10 → 6 (the ledge the theatre's cavea meets) → 3 (the sanctuaries' ledge) → 0.
  A broad marble flight (`approach_steps`) leads from the Panathenaic Way to the approach; the
  way up to the Propylaia is the sightline `propylaia_approach` (V15).
- The quarry road climbs Pentelikon's foot in two legs of three ramps with a bend at 3 to the
  quarry's lip (6; bible: rise 6 over 30 tiles); the hillside is shaped to the road.

Build: `tools/worldgen/build.sh athens [--preview]`.
