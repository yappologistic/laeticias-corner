"""Provisional content: stand-ins for ids whose set catalogs do not exist yet.

These entries let the plan and the first layers be written before the design lane publishes
`assets/sets/<set>/catalog.json` (world-tech §1.12). They are worldgen's guesses, never a
contract: any id defined by a real catalog or a draft overrides the entry here, every use of a
provisional id is reported (V1 warning), and an entry should be deleted once its set catalog
exists. Ids and footprints follow the city files' tables (footprint here is grid [x, y] at r0:
x = north-south, y = east-west for a model facing west).

`colour` is the preview colour of a terrain without art. `stand_in` names a home sprite the
previews draw for a plant without art, so country previews can be judged before the art exists.
"""

_W = ["world.earth", "world.coast", "world.rock"]

TERRAIN = [
    # world set (world-tech §1.7)
    {"id": "world.sand", "base": True, "variants": 4, "colour": [222, 204, 160],
     "faces": ["world.coast", "world.earth"]},
    {"id": "world.steppe", "base": True, "variants": 4, "colour": [184, 172, 112], "faces": _W},
    {"id": "world.alluvium", "base": True, "variants": 4, "colour": [150, 156, 96],
     "faces": ["world.earth", "world.coast"]},
    {"id": "world.sea", "under": "world.sand", "fps": 4, "water": True, "colour": [44, 96, 146]},
    {"id": "world.shallows", "under": "world.sand", "fps": 4, "water": True,
     "colour": [70, 138, 164]},
    {"id": "world.river", "under": "world.sand", "fps": 8, "water": True,
     "colour": [66, 124, 160]},
    {"id": "world.rock", "under": "world.steppe", "colour": [132, 124, 114],
     "faces": ["world.rock", "world.coast", "world.snow"]},
    {"id": "world.snow", "under": "world.steppe", "colour": [234, 238, 244],
     "faces": ["world.snow", "world.rock"]},
    {"id": "world.marsh", "under": "world.alluvium", "colour": [104, 136, 92],
     "faces": ["world.earth"]},
    {"id": "world.road_earth", "under": "world.steppe", "colour": [170, 142, 102],
     "faces": ["world.earth"]},
    {"id": "world.field", "under": "world.steppe", "colour": [196, 174, 92],
     "faces": ["world.earth"]},
    {"id": "world.scree", "under": "world.steppe", "colour": [158, 148, 128],
     "faces": ["world.rock"]},
    # rome
    {"id": "rome.grass_spring", "base": True, "variants": 4, "colour": [98, 146, 66],
     "faces": ["world.earth", "world.coast", "world.rock", "rome.tufa"]},
    {"id": "rome.basalt_paving", "under": "rome.grass_spring", "colour": [92, 92, 98],
     "faces": ["rome.tufa", "world.earth", "world.coast"]},
    {"id": "rome.travertine_paving", "under": "rome.grass_spring", "colour": [212, 204, 180],
     "faces": ["rome.tufa", "world.earth", "world.coast"]},
    {"id": "rome.brick_ground", "under": "rome.grass_spring", "colour": [168, 96, 70]},
    {"id": "rome.packed_earth", "under": "rome.grass_spring", "colour": [166, 138, 98],
     "faces": ["world.earth", "world.coast"]},
    {"id": "rome.field_spring", "under": "rome.grass_spring", "colour": [136, 166, 78],
     "faces": ["world.earth"]},
    {"id": "rome.vineyard_soil", "under": "rome.grass_spring", "colour": [128, 102, 74]},
    {"id": "rome.mud_bank", "under": "rome.grass_spring", "colour": [124, 110, 82]},
    # athens
    {"id": "athens.dry_grass", "base": True, "variants": 4, "colour": [182, 168, 106],
     "faces": ["world.earth", "world.coast", "world.rock", "athens.limestone"]},
    {"id": "athens.field_stubble", "under": "athens.dry_grass", "colour": [206, 184, 118],
     "faces": ["world.earth"]},
    {"id": "athens.olive_soil", "under": "athens.dry_grass", "colour": [158, 136, 94],
     "faces": ["world.earth"]},
    # parsa
    {"id": "parsa.plain_grass", "base": True, "variants": 4, "colour": [148, 158, 94],
     "faces": ["world.earth", "world.rock", "parsa.ashlar"]},
    {"id": "parsa.field_barley", "under": "parsa.plain_grass", "colour": [186, 178, 94],
     "faces": ["world.earth"]},
]

# Home terrains get faces in world-tech §6.2; used only while the home catalog has none.
FACES_PENDING = {"grass": ["world.earth", "world.coast"]}


def _plant(i, stand_in, height=80, walkable=False):
    return {"id": i, "footprint": [1, 1], "layout": "variant", "count": 4, "on": "land",
            "height": height, "stand_in": stand_in, "walkable": walkable}


def _kit(i, fp, height, count=4, on="land", **kw):
    return {"id": i, "footprint": fp, "layout": "rotate", "count": count, "on": on,
            "height": height, **kw}


ITEMS = [
    # plants
    _plant("rome.t_stone_pine", "pine", 120), _plant("rome.t_cypress", "pine", 110),
    _plant("rome.t_oak", "oak", 80), _plant("rome.t_plane", "oak", 110),
    _plant("world.t_poplar", "pine", 100), _plant("world.t_plane", "oak", 110),
    _plant("world.t_oak", "oak", 80), _plant("world.t_beech", "oak", 90),
    _plant("world.t_fir", "pine", 100), _plant("world.t_cedar", "pine", 110),
    _plant("world.t_palm", "pine", 100), _plant("world.t_tamarisk", "bush", 40),
    _plant("world.t_pine_aleppo", "pine", 90),
    _plant("athens.t_olive", "bush", 55), _plant("athens.t_cypress", "pine", 110),
    _plant("parsa.t_cypress", "pine", 110),
    {"id": "world.t_reeds", "footprint": [1, 1], "layout": "variant", "count": 4, "on": "any",
     "height": 30, "stand_in": "reeds", "walkable": True},
    # world kit
    _kit("world.wayside_shrine", [1, 1], 44),
    _kit("world.milestone", [1, 1], 26),
    _kit("world.stair_earth", [1, 2], 20, rise=1, axis="y"),
    _kit("world.ramp", [1, 4], 18, rise=1, axis="y"),
    {"id": "world.ford", "footprint": [1, 1], "layout": "variant", "count": 2, "on": "water",
     "height": 6, "walkable": True},
    # rome (rome.md §3.3, §3.7)
    _kit("rome.r_insula", [3, 4], 140, door=True), _kit("rome.r_insula_corner", [3, 3], 140, door=True),
    _kit("rome.r_insula_low", [2, 3], 85, door=True), _kit("rome.r_horrea", [4, 4], 60, door=True),
    _kit("rome.r_taberna", [1, 1], 50, door=True), _kit("rome.r_lacus", [1, 1], 24),
    _kit("rome.r_compitum", [1, 1], 36), _kit("rome.r_milestone", [1, 1], 30),
    _kit("rome.r_amphorae", [1, 1], 26), _kit("rome.r_stall", [1, 2], 40),
    _kit("rome.r_crane", [2, 2], 140), _kit("rome.r_tomb", [2, 2], 50),
    _kit("rome.r_statue", [1, 1], 60), _kit("rome.r_bakery", [2, 3], 60, door=True),
    _kit("rome.r_temple", [5, 3], 90, door=True),
    _kit("rome.quay_mooring", [1, 1], 12, on="any"),
    {"id": "rome.pons_span", "footprint": [1, 1], "layout": "rotate", "count": 2, "on": "water",
     "height": 20, "walkable": True, "stand_in": "bridge"},
    {"id": "rome.portus_hexagon", "footprint": [18, 20], "layout": "rotate", "count": 4,
     "rotations": [0], "on": "any", "landmark": True, "height": 40},
    {"id": "rome.portus_lighthouse", "footprint": [3, 3], "layout": "rotate", "count": 4,
     "rotations": [0], "on": "land", "landmark": True, "height": 160, "glow": True},
]
