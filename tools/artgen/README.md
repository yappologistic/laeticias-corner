# artgen

Deterministic generator for `assets/atlas.png` + `assets/atlas.json`.

```sh
tools/artgen/build.sh            # regenerate the atlas and validate it
tools/artgen/build.sh --preview  # also write contact sheets to out/artgen/ (3x, nearest)
```

The first run creates `tools/artgen/.venv` from the pinned `requirements.txt`. The same input
always produces byte-identical output. A full run takes a few seconds on a multi-core machine.

## How it works

- `spec.py` lists every key the catalog implies (and our frame counts).
- `palette.py` holds the one curated palette (56 colours) and the material ramps built from it.
- `voxel.py` is the modelling toolkit: a material grid with per-voxel normals and tone, boolean
  shape helpers (boxes, ellipsoids, cylinders, cones, capsules, gables), seeded noise, rotation.
  World units are voxels, 16 per tile edge; one voxel of height is one pixel.
- `render.py` ray-casts a model exactly into the 2:1 projection (pixel centres, so tiles
  partition the screen), shades it with one sun from the upper left, ambient occlusion, cast
  self-shadows and selective outlines, and quantises to the material's ramp with a restrained
  4x4 ordered dither. It also produces the ground `shadow` layer and the emissive `glow` layer.
- `models/` describe every item and visitor as voxel models; `terrain.py` and `fx.py` evaluate
  ground tiles, cliff faces, cursor diamonds and effects directly per pixel.
- `pack.py` trims each sprite, shelf-packs them with a 1 px gutter and writes the manifest.
- `validate.py` checks keys, rects, anchors, frame counts and palette use.
- `preview.py` composes test scenes from the packed atlas the way the engine draws them.

## Conventions worth knowing

- Overlay masks only ever depend on each edge's own bit: an open edge is fully covered and every
  inset tapers to zero at a corner beside an open edge, so neighbours agree on shared edges.
- Joined items (`hedge`, `fence`) are modelled with the neighbours' arms as unseen context, so
  light, leaves and outlines continue across the tile edge without a seam.
- Rotatable pieces are modelled facing +y (the windmill faces +x so both rotations show sails).
- Glow layers store halo strength in alpha; draw them with additive blending.
- Flying visitors are anchored at the bottom of the body; the engine adds the altitude.
