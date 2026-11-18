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

Build: `tools/worldgen/build.sh athens [--preview]`.
