# artgen

Deterministic generator for `assets/atlas.png` + `assets/atlas.json`.

```sh
tools/artgen/build.sh            # regenerate assets/atlas.{png,json} and validate it
tools/artgen/build.sh --preview  # also write preview scenes to out/artgen/ (3x, nearest)
tools/artgen/build.sh --tile 64 --out out/artgen/hd --preview   # 64x32 tiles, elsewhere
```

The tile size comes from `tile.w` in `assets/catalog.json` (`tile.h` is half of it) unless
`--tile` overrides it; it must be a multiple of 32. `--out` writes the atlas and the previews
to another directory (previews of finer tiles are written at 1x and, as `*_2x.png`, at 2x).

The first run creates `tools/artgen/.venv` from the pinned `requirements.txt`. The same input
always produces byte-identical output. A 32x16 run takes a few seconds on a multi-core
machine; 64x32 needs about eight times the CPU (roughly ten seconds on 16 idle cores).

## How it works

- `spec.py` lists every key the catalog implies (and our frame counts) and parses the build
  options into a `Build`: tile width, output paths and `k`, the voxels per design unit.
- `palette.py` holds the one curated palette (57 colours) and the material ramps built from it.
- `voxel.py` is the modelling toolkit: a material grid with per-voxel normals and tone, boolean
  shape helpers (boxes, ellipsoids, cylinders, cones, capsules, gables), seeded noise, rotation.
  Models are written in design units, 16 per tile edge, and sampled with `k` voxels per unit
  (`k = tile.w / 32`); one voxel of height is one pixel. `Model.fine` (k >= 2) gates detail
  smaller than a design unit (leaves, shingles, hinges, mullions): the coarse grid keeps its
  established look and the 32x16 atlas stays reproducible byte for byte.
- `render.py` ray-casts a model exactly into the 2:1 projection (pixel centres, so tiles
  partition the screen), shades it with one sun from the upper left, ambient occlusion, cast
  self-shadows and selective outlines, and quantises to the material's ramp with a restrained
  4x4 ordered dither. It also produces the ground `shadow` layer and the emissive `glow` layer.
- `models/` describe every item and the walking visitors as voxel models; the tiny flyers
  (butterfly, bee, firefly) are hand-drawn pixel stencils, since voxels would only make blobs at
  that size. `terrain.py` and `fx.py` evaluate ground tiles, cliff faces, cursor diamonds and
  effects directly per pixel.
- Lengths that set the look (occlusion reach, contact shadow, crevice width) are in design
  units; pixel-sized things (outlines, dither, 1 px marks) stay pixel-sized, so finer tiles
  read as finer art, not as enlarged sprites.
- `pack.py` trims each sprite, shelf-packs them with a 1 px gutter and writes the manifest.
- `validate.py` checks keys, rects, anchors, frame counts and palette use.
- `preview.py` composes test scenes from the packed atlas the way the engine draws them.

## Conventions worth knowing

- Overlay masks only ever depend on each edge's own bit: an open edge is fully covered and every
  inset tapers to zero at a corner beside an open edge, so neighbours agree on shared edges.
- Joined items (`hedge`, `fence`) are modelled with the neighbours' arms as unseen context, so
  light, leaves and outlines continue across the tile edge without a seam.
- Rotatable pieces are modelled facing +y (the windmill faces +x so both rotations show sails).
- Trees are clumps studded with small leaf clusters (`leaf_mass`); each cluster shades as its own
  puff, so canopies read as lit tufts with dark crevices. Their crowns sway clump by clump.
- Lawn grass is flat; variants differ only in a few hand-shaped marks and clumps, so a field of
  randomly chosen variants shows gentle patches. Meadow and cliffs repeat exactly per tile, so
  their marks are dense or hand-placed and smooth to keep the repeat from reading as a pattern.
- Glow layers store halo strength in alpha; draw them with additive blending.
- Flying visitors are anchored at the bottom of the body; the engine adds the altitude.
