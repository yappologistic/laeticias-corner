"""Laeticia's Corner: the borderland around the home region (world-tech §4.1, world.md §7).

The home region itself (C 40..79, R 40..79) is left transparent: it belongs to the player and the
engine writes it from the save. Around it: meadows and a beech wood on the headland (world level
2), the old road along C 79 north past a wayside shrine to the world's edge and south through the
misty dell (level 1) to Rome's Via Aurelia, a track west to the jetty, two farmsteads, the home's
streams running on to the sea cliff. The sea is the base layer's (transparent here).

Local plan coordinates = world plan coordinates (the corner's origin is (0, 0)); local level 0 is
world level 2.
"""

from worldgen.dsl import Layout
from worldgen.shapes import Ellipse, Line, Poly, Rect

HOME = Rect(40, 40, 79, 79)
DELL = Rect(88, 0, 95, 111)


def coast_west(L: Layout, r: int, start: int) -> int:
    """First column west of `start` on row r whose ground below is not land (the cliff edge)."""
    c = start
    while c > 0 and L.below_terrain(c - 1, r) not in ("world.sea", "world.shallows"):
        c -= 1
    return c


def coast_south(L: Layout, c: int, start: int) -> int:
    r = start
    while r < 111 and L.below_terrain(c, r + 1) not in ("world.sea", "world.shallows"):
        r += 1
    return r


def build(L: Layout) -> None:
    land = L.land_below()
    sea = L.sea_below()
    L.fill("grass", level=0, district="meadows")
    L.transparent(sea)
    L.level(L.coast_below(), 0, face="world.coast")

    # The misty dell: one level down, the seam with Rome.
    L.district("seam_dell/dell", DELL)
    L.paint(DELL - sea, "meadow")
    L.level(DELL, -1)

    # The wood, the coast and the farms.
    L.district("wood", Poly([(14, 0), (78, 0), (78, 34), (60, 38), (40, 36), (22, 40), (14, 30)]))
    L.district("coast", Rect(0, 86, 87, 111) - Rect(70, 80, 87, 111))
    L.district("farms", Rect(80, 76, 87, 92) | Rect(56, 12, 72, 30))

    # Meadow patches and wild edges.
    for i, (c, r, rx, ry) in enumerate([(30, 64, 6, 4), (24, 80, 5, 3), (54, 90, 7, 3),
                                        (84, 50, 3, 6), (50, 28, 6, 3), (70, 104, 5, 3)]):
        L.paint(Ellipse(c, r, rx, ry) - HOME - sea, "meadow")

    # The old road (home path continued), north to the world's edge and south to the dell.
    north = L.street([(79, 39), (79, 0)], width=1, paving="path", kind="road")
    south = L.street([(79, 80), (79, 92), (84, 94), (92, 94), (93, 100), (94, 111)], width=1,
                     paving="path", kind="road", portal="corner_road_s")
    L.stair("world.ramp", rect=(88, 94, 91, 94), face="east")
    L.node("world_edge_n", (79, 0), kind="dest")
    L.node("home_n", (79, 39), kind=None)
    L.node("home_s", (79, 80), kind=None)
    L.node("home_gate", (78, 60), kind="gate")
    L.edge("home_n", "home_gate", via=[(79, 60)])
    L.edge("home_gate", "home_s", via=[(79, 60)])
    L.district("road", Line([(79, 0), (79, 39)], 1) | Line([(79, 80), (79, 92), (84, 94),
                                                            (87, 94)], 1))

    # Hedgerows along the road, with gaps, and the wayside shrine with no named god.
    L.row(Line([(80, 2), (80, 17)], 1), "hedge", every=1)
    L.row(Line([(80, 23), (80, 36)], 1), "hedge", every=1)
    L.row(Line([(78, 4), (78, 13)], 1), "hedge", every=1)
    shrine = L.place("world.wayside_shrine", at=(80, 20), face="west", name="wayside_shrine")
    L.place("lamp", at=(80, 21))
    L.place("bench", at=(78, 20), face="east")
    L.node("shrine", (79, 20), kind="dest")
    L.place("world.milestone", at=(80, 86), face="west", name="milestone")

    # The track west to the jetty: down a ramp into a cove one level below the headland, then
    # out over the water on planks. The far pond's creek crosses the track on a plank bridge.
    jetty_c = 33
    shore = coast_south(L, jetty_c, 90)
    cove = Ellipse(jetty_c, shore, 6, 3) - sea
    # The cove lies at the sea's level, so the planks (drawn at the water's level) meet it.
    L.level(cove, -2, face="world.coast")
    L.paint(cove, "meadow")
    L.district("coast", cove)
    L.level(Rect(jetty_c, shore - 6, jetty_c, shore - 2), -1)
    L.stair("world.ramp", rect=(jetty_c, shore - 6, jetty_c, shore - 3), face="south")
    L.stair("world.stair_earth", rect=(jetty_c, shore - 1, jetty_c, shore), face="south")
    L.street([(79, 92), (70, 93), (64, 95), (56, 96), (44, 96), (jetty_c, shore - 10),
              (jetty_c, shore)], width=1, paving="path", kind="track")
    for r in range(shore + 1, min(shore + 10, 111)):
        L.place("bridge", at=(jetty_c, r), face="north")
    end = min(shore + 9, 110)
    L.place("rowboat", at=(jetty_c + 1, end - 1), face="north")
    for dc in (-2, 2, -3, 3):
        if L.terrain_at(jetty_c + dc, shore - 1) == "meadow":
            L.place("lamp", at=(jetty_c + dc, shore - 1))
            break
    L.node("jetty", (jetty_c, end), kind="dest")
    L.node("jetty_foot", (jetty_c, shore), kind=None)
    L.edge("jetty_foot", "jetty", kind="quay")

    # Streams from the home's west rim to the sea cliff, and the far pond's creek to the south.
    for r, name in ((44, "high_wood"), (52, "west_meadow")):
        mouth = coast_west(L, r, 39)
        L.river([(39, r), (33, r + 1), (26, r), (mouth, r)], width=1, banks={"reeds": 0.25},
                seed=name)
    creek_end = coast_south(L, 64, 96)
    L.river([(64, 80), (66, 88), (64, 95), (63, creek_end)], width=1, banks={"reeds": 0.2},
            seed="creek")
    L.place("bridge", at=(64, 95), face="west")

    # Farmstead by the south road, between the road and the dell.
    L.place("cottage", at=(82, 80), face="west", name="south_farm")
    L.place("barn", at=(84, 85), face="west")
    L.place("coop", at=(81, 84), face="west")
    L.place("hay_bale", at=(81, 89))
    L.place("hay_bale", at=(83, 90), variant=1)
    L.row(Line([(86, 77), (86, 83)], 1), "fence", every=1)
    L.scatter(Rect(80, 76, 87, 92), {"flowers_white": 1, "tall_grass": 2}, 0.12, seed="farmyard")

    # Farmstead by the shrine: cottage, sunflower field and the windmill on the rise.
    L.place("cottage", at=(66, 22), face="east", name="shrine_farm")
    L.place("toolshed", at=(64, 21), face="east")
    L.place("well", at=(69, 25))
    L.place("beehive", at=(70, 18))
    L.place("beehive", at=(71, 19))
    L.fields(Rect(56, 14, 63, 24), "sunflowers", plot=(4, 2), seed="sunflowers")
    L.row(Line([(55, 13), (64, 13)], 1), "stone_wall", every=1)
    L.row(Line([(55, 14), (55, 26)], 1), "stone_wall", every=1)
    L.place("windmill", at=(29, 17), face="east", name="windmill")
    L.street([(79, 27), (66, 27), (54, 30), (42, 26), (32, 18)], width=1, paving="path", kind="track")

    # The beech wood (oaks stand in for beech in the home set), thicker to the north and west,
    # with clearings; blossom and bushes along its fringe.
    wood = Poly([(14, 0), (78, 0), (78, 12), (70, 30), (54, 34), (40, 36), (22, 40), (14, 30)])
    L.scatter(wood - Ellipse(30, 18, 11, 9) - Rect(53, 11, 74, 31), {"oak": 3, "pine": 2},
              0.36, seed="beech_wood", clump=0.8)
    L.scatter(Rect(14, 0, 87, 39) - wood, {"blossom": 1, "bush": 2, "oak": 1}, 0.05,
              seed="wood_fringe")
    # The headland: scattered trees, bushes and rocks, flowers in the meadows.
    open_land = land - HOME - DELL - wood
    L.scatter(open_land, {"oak": 2, "pine": 1, "bush": 3, "rock": 1, "berry_bush": 1}, 0.035,
              seed="headland", clump=0.6)
    L.scatter(open_land, {"flowers_red": 1, "flowers_white": 1, "flowers_violet": 1,
                          "tall_grass": 3, "mushrooms": 0.3}, 0.05, seed="flowers", clump=0.5)
    L.scatter(L.coast_below(), {"rock": 2, "tall_grass": 1}, 0.12, seed="cliff_top")
    L.scatter(DELL - sea, {"tall_grass": 3, "reeds": 1, "bush": 1}, 0.12, seed="dell")

    L.view("home_setting", Rect(20, 22, 103, 112))
    L.view("road_south", Rect(70, 78, 97, 112))
    L.view("shrine", Rect(62, 4, 92, 32))
    L.view("jetty", Rect(18, 84, 52, 111))
    L.view("dell", Rect(80, 90, 103, 124))
