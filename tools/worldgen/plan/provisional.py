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

TERRAIN = [
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
]


def _plant(i, stand_in, height=80, walkable=False):
    return {"id": i, "footprint": [1, 1], "layout": "variant", "count": 4, "on": "land",
            "height": height, "stand_in": stand_in, "walkable": walkable}


def _mark(i, fp, height):
    return {"id": i, "footprint": fp, "layout": "rotate", "count": 4, "rotations": [0],
            "on": "land", "landmark": True, "height": height}


def _kit(i, fp, height, count=4, on="land", **kw):
    return {"id": i, "footprint": fp, "layout": "rotate", "count": count, "on": on,
            "height": height, **kw}


ITEMS = [
    # rome plants until the rome set catalog is committed
    _plant("rome.t_stone_pine", "pine", 120), _plant("rome.t_cypress", "pine", 110),
    _plant("rome.t_oak", "oak", 80), _plant("rome.t_plane", "oak", 110),
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
    # Waypoint landmarks proposed for the city sets (docs/design/sets/world.md §4, city files
    # §3.7). Footprints are the plans' rects (grid [x, y] = [rows, columns] at r0), heights from
    # the city files. They draw as labelled placeholders until the athens and parsa sets add them.
    *[_mark(i, fp, h) for i, fp, h in (
        ("athens.delphi_apollo", [6, 12], 100), ("athens.athenian_treasury", [2, 3], 50),
        ("athens.castalian_spring", [2, 2], 20), ("athens.corinth_apollo", [6, 12], 90),
        ("athens.acrocorinth_summit", [3, 3], 70), ("athens.diolkos", [20, 2], 4),
        ("athens.naxian_lions", [2, 8], 40), ("athens.delos_sanctuary", [8, 10], 70),
        ("athens.artemision", [8, 16], 150),
        ("parsa.royal_road_head", [4, 4], 60), ("parsa.halys_gates", [8, 4], 80),
        ("parsa.ferry_station", [6, 6], 40), ("parsa.ishtar_gate", [4, 6], 140),
        ("parsa.processional_way", [14, 2], 60), ("parsa.etemenanki", [12, 12], 260),
        ("parsa.susa_palace", [12, 14], 150), ("parsa.gates_station", [6, 8], 60),
        ("parsa.pasargadae_garden", [10, 12], 70),
    )],
    # Babylon's wall kit (city file §3.7: "babylon_wall (kit) 1 x 1 / 2 x 2 tower").
    {"id": "parsa.babylon_wall", "footprint": [1, 1], "layout": "connect", "count": 16,
     "on": "land", "height": 70},
    _kit("parsa.babylon_tower", [2, 2], 100, count=1),
]

# Stand-ins the world set retired (docs/design/sets/world.md §0.2): the city sets' own trees.
RETIRED = {"world.t_plane": "athens.t_plane, parsa.t_plane or rome.t_plane by region set",
           "world.t_poplar": "athens.t_poplar, parsa.t_poplar or rome.t_poplar by region set",
           "world.t_pine_aleppo": "athens.t_pine"}
