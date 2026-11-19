"""Pārsa (Persepolis), spring c. 470 BC (docs/design/cities/persepolis.md).

World rect C 1136..1279, R 304..447; local (c, r) = world (C - 1136, R - 304); local level 0 =
world level 4 (the Marvdasht plain). The terrace stands against Kuh-e Raḥmat on the east; the
great double stairway climbs its west face from a gravel forecourt where the Royal Road from the
Persian Gates ends. The paradise garden lies north of the forecourt, the town of Pārsa south of
it, fields, a village and the river on the plain, Naqsh-e Rostam as a vignette in the north-west
corner behind a band of rough ground, the road station, cavalry ground and the delegations' camp
on the southern plain, and the qanat line along the south edge.

Order of the build: ground and elevation, water, ways, landmarks, districts and their fillers,
detail. Every coordinate below is from the bible's tables (§2.2-§2.6) unless a comment says why
it differs.
"""

import importlib.util
from pathlib import Path

import numpy as np

from worldgen import rng
from worldgen.dsl import Layout
from worldgen.finish import clear_doors, fit_faces, fords, free, glow_cap, orth, put, seam
from worldgen.shapes import Ellipse, Line, Mask, Rect

# Rome's clean-up passes for kit whose spots no walker can use.
_spec = importlib.util.spec_from_file_location(
    "worldgen_region_rome_common", Path(__file__).resolve().parent.parent / "rome" / "common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

N = 144
P = "parsa."
GRASS, FIELD, BED, EARTH = P + "plain_grass", P + "field_barley", P + "garden_bed", P + "packed_earth"
STONE, RED, GRAVEL, WATER = P + "paving_stone", P + "paving_red", P + "gravel", P + "water_channel"
ROUGH, RIVER, ROCK, SCREE = P + "rough_ground", "world.river", "world.rock", "world.scree"

TERRACE = Rect(56, 22, 119, 118)
BAND = Rect(120, 0, 124, 143)          # the slope foot behind the terrace, where the wall runs
WALL_C = 123                           # fortification line (bible c 119..124)
QUARRY = Rect(126, 100, 140, 118)
CISTERN = Rect(124, 60, 128, 64)
GARDEN = Rect(26, 8, 55, 34)           # paradise inside its wall (wall on the rim)
PLOT = Rect(44, 9, 54, 19)             # the player's walled garden plot (bible §10)
PLAZA = Rect(26, 35, 46, 60)
TOWN = Rect(0, 62, 48, 112)
S1 = Rect(0, 0, 20, 17)                # Naqsh-e Rostam vignette inside its rough band
S1_BAND = Rect(21, 0, 24, 21) | Rect(0, 18, 24, 21)
CAMP = Rect(58, 122, 112, 134)

# Paradise channels: the inlet along r 22 from the canal, north to the pavilion and beyond, the
# pavilion's arms, the south axis, the branch that leaves as the town canal, and the south-east
# arm that ends at its sluice by the wall.
GARDEN_WATER = [
    [(54, 21), (54, 22), (36, 22)],
    [(35, 22), (35, 18)],
    [(35, 11), (35, 9)],
    [(31, 15), (28, 15)],
    [(38, 15), (42, 15)],
    [(35, 23), (35, 32)],
    [(34, 22), (32, 22), (32, 33)],
    [(52, 23), (52, 33)],
]

RIVER_PTS = [(104, 0), (98, 2), (90, 3), (82, 2), (74, 3), (66, 2), (58, 2), (50, 2), (42, 3),
             (34, 2), (29, 1), (27, 0)]


# The residential wing's L-shaped footprint has its origin tile (the engine's level for the whole
# item) in the corridor notch at the terrace's level: the wing stands there in full, its art's
# plinth carrying the platform, so every footprint tile is at one level (W-V3).
HAREM_LEVEL = ("the engine draws the wing from its origin tile, in the corridor notch at the "
               "terrace's level; the platform is the art's plinth (W-V3: one level per footprint)")

def build(L: Layout) -> None:
    cc, rr = np.meshgrid(np.arange(N), np.arange(N))

    def noise(scale, key, octaves=3):
        return rng.fbm(cc + L.origin[0], rr + L.origin[1], scale, rng.hash64("parsa", key),
                       octaves=octaves)

    def mask(m) -> Mask:
        return Mask(0, 0, np.asarray(m, dtype=bool))

    streets = []

    def street(points, **kw):
        s = way(L, points, **kw)
        streets.append(s)
        return s

    # =========================================================================================
    # 1. Ground and elevation
    # =========================================================================================
    L.fill(GRASS, level=0, district="plain")

    # Kuh-e Raḥmat: the slope foot (level 7) carries the wall; above it bare limestone climbs to
    # the east edge (11 = world 15), where the backdrop takes over. The mountain rises in ridges
    # (contours every four or five columns, bent by noise, each a one-level scarp) cut by gullies
    # that come down westward every dozen rows, with scree in the gullies and fanning out at
    # their feet. North and south of the terrace the plain climbs the foothills in three
    # benches (2, 4, 6) to meet it.
    x = (cc - 125) / 18.0
    ridge = 8 + x * 3.8 + (noise(22.0, "mountain") - 0.5) * 1.4 + (noise(7.0, "crags") - 0.5) * 0.5
    wob = (noise(16.0, "gully_wobble") - 0.5) * 7
    gully = np.clip(1 - np.abs(np.sin(np.pi * (rr + wob) / 13.0)) / 0.3, 0, 1)
    mount = np.clip(np.floor(ridge - np.minimum(gully * 2, 1) * (1.5 + 2.0 * x)), 8, 11)
    foot = np.clip(2 * np.floor(((cc - 104) * 0.45 + (noise(11.0, "foothills") - 0.5) * 2.0) / 2),
                   0, 6)
    outside_terrace = (rr < 22) | (rr > 118)
    lv = np.zeros((N, N), dtype=int)
    lv = np.where(outside_terrace & (cc >= 108) & (cc < 120), foot, lv)
    lv = np.where((cc >= 120) & (cc <= 124), 7, lv)
    lv = np.where(cc >= 125, mount, lv)
    for k in range(1, 12):
        L.level(mask(lv == k), k, face=P + "rock")
    slope = mask((cc >= 125) | ((lv > 0) & (cc >= 100)))
    L.paint(slope, ROCK)
    fan = (cc >= 118) & (cc < 132) & \
        (np.clip(1 - np.abs(np.sin(np.pi * (rr + wob) / 13.0)) / (0.15 + 0.03 * np.clip(132 - cc, 0, None)),
                 0, 1) > 0.3)
    L.paint(mask((cc >= 125) & (gully > 0.25) & (noise(4.0, "gully_scree") > 0.2)), SCREE)
    L.paint(mask(fan & (noise(3.0, "fan_scree") > 0.35)), SCREE)
    L.paint(mask((cc >= 100) & (cc < 125) & (lv > 0) & (noise(5.0, "scree") > 0.6)), SCREE)
    L.paint(mask((cc >= 100) & (cc < 120) & (lv > 0) & (lv < 4) & (noise(6.0, "grassy") > 0.5)),
            ROUGH)
    L.paint(BAND, ROUGH)
    L.paint(Rect(120, 0, 124, 143) & mask(noise(4.0, "band_rock") > 0.62), ROCK)
    # Everything above the slope foot is cliff and scree: no walker goes there, except the quarry
    # with its approach, the cistern and the shrine ledge.
    cut = (QUARRY | Rect(124, 99, 125, 119) | CISTERN | Rect(124, 38, 130, 44)).mask(0, 0, N, N)
    L.impassable(mask((cc >= 125) & ~cut))
    L.impassable(mask((cc >= 100) & (cc < 120) & (lv >= 2)))
    L.district("slope", Rect(120, 0, 143, 143))
    L.district("slope", mask((cc >= 100) & (cc < 120) & outside_terrace & (lv > 0)))

    # The terrace: one level of six (96 px of fitted grey ashlar on the visible west and south
    # faces), paved in large slabs; the building platforms rise one to three levels more.
    L.level(TERRACE, 6, face=P + "ashlar")
    L.paint(TERRACE, STONE)
    for rect, k in ((Rect(60, 54, 83, 77), 7),      # Apadāna
                    (Rect(87, 71, 93, 78), 7),      # Tripylon
                    (Rect(63, 82, 70, 91), 8),      # Tačara
                    (Rect(76, 88, 85, 101), 9)):    # Hadiš, the highest platform
        L.level(rect, k, face=P + "ashlar")
    # The residential wing stands at the terrace's level with the corridor down its east side to
    # the Treasury's west door (HAREM_LEVEL).
    L.moved("harem", rect=(86, 86, 99, 112), level=6, why=HAREM_LEVEL)
    # Painted red plaster under the porticoes and passages walkers use (walk tiles' floors).
    for rect in (Rect(65, 54, 78, 58), Rect(60, 59, 64, 72), Rect(64, 44, 69, 45),
                 Rect(66, 46, 67, 47), Rect(64, 89, 69, 91), Rect(76, 88, 85, 91),
                 Rect(88, 72, 92, 77)):
        L.paint(rect, RED)

    # The quarry floor, the cistern and the mountain shrine's ledge are cut into the slope.
    L.level(QUARRY | Rect(124, 99, 125, 119), 7, face=P + "rock")
    L.paint(QUARRY | Rect(124, 99, 125, 119), ROCK)
    L.level(CISTERN, 8, face=P + "rock")
    L.level(Rect(126, 38, 130, 44), 8, face=P + "rock")
    L.level(Rect(124, 41, 125, 41), 7)
    L.paint(Rect(126, 38, 130, 44), ROUGH)
    L.district("quarry", QUARRY | Rect(124, 99, 125, 119))

    # Naqsh-e Rostam: the cliff rises behind its own small plain; a band of rough, stony ground
    # without a road separates the vignette from the city's plain (world.md §6).
    L.paint(S1_BAND, ROUGH)
    L.paint(S1_BAND & mask(noise(3.0, "band_stones") > 0.6), SCREE)
    L.paint(Rect(0, 9, 20, 17) & mask(noise(5.0, "naqsh_ground") > 0.58), ROUGH)
    L.district("naqsh", S1 | S1_BAND)

    # Dry ground on the southern plain and the foothills: grazing, not ploughland.
    south = Rect(20, 135, 119, 143)
    L.paint(south & mask(noise(7.0, "steppe") > 0.52), ROUGH)
    L.district("southern_plain", south)

    # =========================================================================================
    # 2. Ways (laid before water so crossings become fords, and before every filler)
    # =========================================================================================
    # The Royal Road from the Persian Gates: packed earth, three wide, into the forecourt.
    royal = street([(0, 50), (9, 51), (18, 50), (26, 50)], width=3, paving=EARTH, kind="road",
                   portal="royal_road_w")
    # The road to Pasargadae leaves the Royal Road at the forecourt's corner, runs north past the
    # paradise's glazed-brick gate, along the garden's north wall, and fords the canal and river.
    pasargadae = street([(25, 49), (25, 30), (25, 7), (34, 6), (46, 6), (54, 5), (54, 0)], width=1,
                        paving=EARTH, kind="road", portal="pasargadae_n")
    # The town spur south to the road station (bible c 22; one column west to leave room for the
    # town channel beside it).
    spur = street([(21, 52), (21, 70), (22, 82), (21, 96), (21, 110), (18, 113), (18, 118)],
                  width=2, paving=EARTH, kind="road")

    # The forecourt: gravel, with a processional strip from the road's end to the stairway foot.
    L.paint(PLAZA | Rect(47, 35, 48, 56), GRAVEL)
    L.district("forecourt", PLAZA | Rect(47, 35, 55, 59))
    proc = street([(26, 50), (34, 47), (46, 45), (48, 45)], width=2, paving=STONE)
    street([(36, 35), (36, 47)], width=1, paving=GRAVEL)                  # from the garden gate
    street([(25, 26), (31, 26)], width=1, paving=RED)                     # through the glazed gate
    L.node("royal_road_end", (27, 50))
    L.node("great_stair_foot", (48, 45))
    L.node("stair_plaza", (36, 52))

    # Terrace ways: the landing to the Gate of All Lands, the Gate's own passage, the walled
    # processional road to the Hall forecourt, the street east of the Apadāna (split round the
    # Tripylon), the courts north of the Hadiš and south of the Tačara.
    street([(56, 45), (63, 45)], width=2, paving=STONE)                   # landing → Gate (west door)
    street([(63, 44), (70, 44)], width=1, paving=RED)                     # through the Gate
    gate_road = street([(70, 44), (92, 44)], width=4, paving=STONE)       # bible r 43..46
    street([(57, 47), (58, 50), (71, 50)], width=1, paving=STONE)         # round the Gate's south
    street([(66, 48), (66, 50)], width=1, paving=STONE)                   # Gate south door
    east_st = street([(89, 47), (89, 68)], width=3, paving=STONE)         # bible c 88..90
    street([(85, 72), (85, 81)], width=1, paving=STONE)                   # west of the Tripylon,
    # clear of the Apadāna's east stair (rows 64..71), whose sides walkers cannot cross
    court = street([(57, 80), (99, 80)], width=2, paving=STONE)          # courts r 80..81
    street([(71, 82), (71, 96)], width=1, paving=STONE)                   # Tačara / Hadiš lane
    street([(99, 81), (99, 103)], width=1, paving=STONE)                  # to the Treasury's west door
    street([(57, 96), (75, 96)], width=2, paving=STONE)                   # Tačara's south court
    street([(91, 36), (118, 36)], width=1, paving=STONE)                  # below the garrison
    street([(100, 36), (100, 44)], width=1, paving=STONE)                 # forecourt cross-path
    street([(92, 44), (111, 44)], width=1, paving=STONE)                  # through the building site
    street([(94, 75), (118, 75)], width=2, paving=STONE)                  # masons' yard
    street([(118, 36), (118, 74)], width=2, paving=STONE)                 # east service street,
    street([(114, 77), (118, 77), (118, 110)], width=2, paving=STONE)     # round the haul ramp
    street([(100, 110), (118, 110)], width=2, paving=STONE)               # treasury's south door
    street([(57, 104), (79, 104)], width=1, paving=STONE)                 # Hadiš kitchens
    street([(76, 104), (76, 117)], width=1, paving=STONE)
    street([(76, 117), (79, 117)], width=1, paving=STONE)
    street([(58, 50), (58, 100), (57, 104)], width=1, paving=STONE)       # west edge walk
    street([(56, 30), (95, 30)], width=1, paving=STONE)                   # north court
    street([(58, 30), (58, 47)], width=1, paving=STONE)
    L.node("stair_top", (57, 45))
    L.node("gate_all_lands", (63, 45))
    L.node("hall_forecourt", (100, 41))
    L.node("north_court", (76, 30))
    L.node("archive", (113, 36))
    L.node("garrison_gate", (95, 36))
    L.node("palace_court", (78, 84))
    L.node("hadish_kitchens", (79, 104))
    L.node("treasury_door", (114, 110))
    L.node("masons_yard", (104, 74))
    L.node("haul_ramp", (115, 76))

    # Haul road from the quarry: through a gap in the wall, north along the slope foot, down a
    # ramp to the masons' yard south of the Hall of a Hundred Columns (bible §6.3 chain 1-3).
    L.paint(Rect(120, 76, 125, 110), EARTH)
    haul = street([(125, 109), (121, 109), (121, 76), (120, 76)], width=1, paving=EARTH,
                  kind="track")
    L.node("quarry_face", (125, 109))
    # The mountain shrine above the wall.
    street([(121, 41), (123, 41)], width=1, paving=ROUGH, kind="track")
    street([(121, 41), (121, 76)], width=1, paving=EARTH, kind="track")   # the guards' round
    street([(121, 12), (121, 41)], width=1, paving=EARTH, kind="track")
    street([(121, 110), (121, 130)], width=1, paving=EARTH, kind="track")
    L.node("mountain_shrine", (128, 41))

    # The plain south of the terrace: the camp road from the town past the terrace foot.
    camp_road = street([(47, 88), (47, 113), (54, 113), (54, 122), (75, 122), (104, 122)],
                       width=2, paving=EARTH, kind="road")
    street([(92, 119), (92, 122)], width=1, paving=EARTH)                 # the south stair's foot
    L.node("delegation_camp", (86, 128))

    # Naqsh-e Rostam: a faint footpath only (rough ground, no paving).
    street([(25, 16), (20, 15), (14, 11), (9, 10)], width=1, paving=ROUGH, kind="track")
    L.node("naqsh_tomb", (9, 10))
    L.node("kaba", (13, 12))

    # =========================================================================================
    # 3. Water: river, canal, garden channels, the terrace-foot channel, town and field canals,
    #    the qanat
    # =========================================================================================
    L.river(RIVER_PTS, width=3, terrain=RIVER, seed="river")
    L.district("river", Line(RIVER_PTS, 5))
    # The main canal leaves the river at c 60 and runs west along r 4..5, then down to the
    # paradise's north-east side (the player's plot takes the corner itself).
    canal = [(61, 3), (60, 5), (57, 5), (57, 21), (55, 21)]
    L.channel(canal, terrain=WATER)
    # Paradise: four quarters round the pavilion over the channel crossing.
    for pts in GARDEN_WATER:
        L.channel(pts, terrain=WATER)
    # The outlet through the south wall to the town canal. The channel along the terrace foot
    # (c 50..51) starts below the stairway, gathers the terrace's drains and runs south and west
    # to the town canal, so no water crosses the approach to the Great Stair.
    L.channel([(32, 34), (32, 35), (24, 35), (24, 48), (24, 52), (24, 70), (25, 82), (24, 96),
               (24, 111), (17, 112), (15, 112)], terrain=WATER)
    L.channel([(50, 56), (50, 112)], terrain=WATER, width=2)
    L.channel([(49, 112), (25, 112)], terrain=WATER)
    # The field canal in the south-west, fed by the town canal and the qanat's outflow.
    L.channel([(15, 112), (14, 120), (14, 139)], terrain=WATER)
    L.channel([(18, 139), (14, 139), (6, 139)], terrain=WATER)
    L.channel([(14, 126), (3, 126)], terrain=WATER)
    # The west fields' distributary from the town canal.
    L.channel([(24, 40), (15, 40), (6, 41)], terrain=WATER)
    L.channel([(24, 57), (4, 57)], terrain=WATER)
    # The qanat: shaft mounds every two tiles from the mountain foot to the fields (bible §2.5,
    # nice-to-have, debated: see the region README).
    for c in range(119, 18, -2):
        L.place(P + "p_qanat_shaft", at=(c, 139), variant=(c // 2) % 2)
    L.node("qanat_outflow", (18, 138))

    # Fords and slab bridges wherever a way crosses water.
    fords(L, streets)

    # =========================================================================================
    # 4. Landmarks (bible §2.3; each rect is checked by V4)
    # =========================================================================================
    L.stair(P + "great_stair", rect=(49, 37, 55, 54), face="west", name="great_stair")
    L.place(P + "gate_all_lands", rect=(64, 42, 69, 47), name="gate_all_lands")
    apadana = L.place(P + "apadana", rect=(60, 54, 83, 77), name="apadana")
    L.stair(P + "apadana_stair_n", rect=(65, 51, 78, 53), face="north", name="apadana_stair_n")
    # The east stair is hidden from the camera and leads to the closed east portico: no path.
    L.place(P + "apadana_stair_e", rect=(84, 60, 86, 71), name="apadana_stair_e")
    if apadana is not None and (72, 56) in {(c - L.origin[0], r - L.origin[1])
                                            for c, r in L.walk_tiles(apadana)}:
        L.place(P + "p_throne", at=(72, 56), face="north", name="throne")  # walk tile (2, 11)
    # The west portico over the plain: a short relief stair from the terrace edge.
    L.stair(P + "stair_relief", rect=(59, 65, 59, 66), face="west", name="apadana_stair_w")
    L.place(P + "tacara", rect=(63, 82, 70, 91), name="tacara")
    L.stair(P + "tacara_stair_s", rect=(63, 92, 70, 94), face="south", name="tacara_stair_s")
    L.place(P + "hadish", rect=(76, 88, 85, 101), name="hadish")
    L.stair(P + "hadish_stair_w", rect=(72, 87, 75, 92), face="west", name="hadish_stair_w")
    L.place(P + "tripylon", rect=(87, 71, 93, 78), name="tripylon")
    L.stair(P + "tripylon_stair", rect=(88, 69, 92, 70), face="north", name="tripylon_stair")
    L.stair(P + "stair_relief", rect=(90, 79, 91, 79), face="south", name="tripylon_stair_s")
    L.stair(P + "stair_relief", rect=(94, 74, 94, 75), face="east", name="tripylon_stair_e")
    # The Hall of a Hundred Columns: the set models its north portico with the hall, so the
    # footprint runs from the portico (bible r 48..51) to the hall's south wall (r 67).
    hall = L.place(P + "hall_100", rect=(93, 48, 108, 67), name="hall_100")
    L.place(P + "treasury", rect=(100, 79, 116, 108), name="treasury")
    L.place(P + "harem", rect=(86, 86, 99, 112), name="harem")
    L.place(P + "garrison", rect=(96, 22, 119, 34), name="garrison")
    L.place(P + "south_stores", rect=(80, 113, 99, 118), name="south_stores")
    L.place(P + "cistern", rect=CISTERN, name="cistern")
    L.place(P + "quarry", rect=QUARRY, name="quarry")
    L.place(P + "paradise_gate", rect=(26, 24, 30, 28), name="paradise_gate")
    L.place(P + "pavilion", rect=(32, 12, 37, 17), name="pavilion")
    station = L.place(P + "road_station", rect=(20, 114, 28, 121), name="road_station")
    L.place(P + "naqsh_cliff", rect=(0, 0, 20, 8), name="naqsh_cliff")
    L.place(P + "kaba", rect=(10, 13, 12, 15), name="kaba")

    # The ramp from the terrace up to the slope foot, for the stone sledges.
    L.stair("world.ramp", rect=(116, 76, 119, 76), face="west", name="haul_ramp")
    L.stair("world.stair_earth", rect=(124, 41, 125, 41), face="west", name="shrine_steps")
    _south_stair(L)

    # The fortification on the slope: mudbrick on a stone foot, square towers every 8 rows, gaps
    # where the haul road, the shrine path and the cistern's channel pass.
    L.wall(Line([(WALL_C, 10), (WALL_C, 40)], 1), P + "fort_wall", tower=P + "fort_tower", every=8)
    L.wall(Line([(WALL_C, 42), (WALL_C, 108)], 1), P + "fort_wall", tower=P + "fort_tower",
           every=8)
    L.wall(Line([(WALL_C, 110), (WALL_C, 130)], 1), P + "fort_wall", tower=P + "fort_tower",
           every=8)

    # =========================================================================================
    # 5. Districts
    # =========================================================================================
    L.district("terrace", TERRACE)
    L.district("audience", Rect(56, 36, 92, 79))
    L.district("building_site", Rect(90, 36, 119, 78))
    L.district("garrison", Rect(96, 22, 119, 35))
    L.district("palaces", Rect(56, 80, 99, 118))
    L.district("treasury", Rect(100, 79, 119, 118))
    L.district("fields", Rect(26, 0, 56, 7) - Line(RIVER_PTS, 5))
    L.district("fields", Rect(0, 22, 24, 61))
    L.district("fields", Rect(0, 113, 19, 143))
    L.district("village", Rect(1, 24, 17, 40))
    L.district("paradise", GARDEN)
    L.district("garden_strip", Rect(49, 55, 55, 118))
    L.district("forecourt", PLAZA | Rect(47, 35, 55, 59))
    L.district("town", Rect(22, 62, 48, 86))
    L.district("workers", Rect(0, 62, 21, 112))
    L.district("crafts", Rect(22, 87, 48, 112))
    L.district("station", Rect(20, 113, 34, 126))
    L.district("cavalry", Rect(35, 113, 55, 134))
    L.district("camp", Rect(56, 119, 112, 134))
    L.district("stables", Rect(58, 6, 99, 21))
    L.district("southern_plain", Rect(20, 135, 119, 143))
    L.district("river", Line(RIVER_PTS, 5))

    # =========================================================================================
    # 6. Quarters, gardens, fields and their detail
    # =========================================================================================
    _paradise(L, noise)
    _forecourt(L)
    _town(L, spur, noise)
    _terrace_detail(L)
    _plain(L, noise)
    _naqsh(L)

    # Juniper and thorn cling to the ridges, boulders and crags lie below the scarps (the slope
    # is impassable, so they are placed one by one rather than scattered on walkable ground).
    roll = rng.hash01(cc + L.origin[0], rr + L.origin[1], rng.hash64("parsa", "mountain_kit"))
    kind = rng.hash01(cc + L.origin[0], rr + L.origin[1], rng.hash64("parsa", "mountain_pick"))
    kit = ["world.boulder", "world.boulder", "world.p_thistle", "world.t_juniper"]
    for r, c in zip(*np.nonzero((cc >= 126) & (gully < 0.2) & ~cut & (roll < 0.05))):
        if L.OCC[r, c] < 0:
            L.place(kit[int(kind[r, c] * len(kit))], at=(int(c), int(r)))

    # Kit whose slot spots (the set's basins, sluices, kilns, ovens, horse lines and troughs
    # gained them) fall on closed ground or beyond a walker's reach goes, as in Rome.
    # The kilns, the throne and the scribes' desks stay: the region's life works at them (V7
    # still judges them).
    keep = frozenset({P + "p_kiln", P + "p_throne", P + "p_scribe_desk"})
    clear_doors(L)
    C.drop_bad_spots(L, keep)
    C.drop_unreached(L, keep=keep)
    glow_cap(L, {P + "p_house_small": 0, P + "p_house": 1, P + "p_workshop": 2, P + "p_oven": 3})
    seam(L, GRASS, ROUGH)
    fit_faces(L, P + "rock")

    # =========================================================================================
    # 7. Checks and previews
    # =========================================================================================
    L.expect("great_stair", rect=(49, 37, 55, 54), level=0)
    L.expect("apadana", rect=(60, 54, 83, 77), level=7)
    L.expect("hadish", rect=(76, 88, 85, 101), level=9)
    # The arrival: the forecourt, the Great Stair and the landing before the Gate (V15).
    L.sightline("great_stair", PLAZA | Rect(47, 35, 70, 60))
    L.view("whole_terrace", Rect(46, 18, 124, 122))
    L.view("terrace_front", Rect(44, 32, 92, 82))
    L.view("palaces", Rect(56, 76, 120, 124))
    L.view("whole_region", Rect(0, 0, 143, 143))
    L.view("forecourt", Rect(18, 30, 66, 64))
    L.view("garden", Rect(22, 4, 60, 38))
    L.view("town", Rect(0, 58, 50, 114))
    L.view("camp", Rect(54, 114, 118, 138))
    L.view("road_west", Rect(0, 36, 34, 66))
    L.view("station", Rect(10, 108, 60, 143))
    L.view("north_plain", Rect(56, 0, 120, 24))


# =============================================================================================
# helpers
# =============================================================================================

def way(L: Layout, points, **kw):
    return L.street(orth(points), **kw)


def _south_stair(L: Layout) -> None:
    """The narrow south stair (bible: the original access, rise 6). The set has no single item
    for it, so it is built as six relief flights climbing west along the terrace's south face,
    each landing one level higher, from the plain at c 92 to the terrace at c 79 (r 119..120).
    """
    c = 90
    for k in range(6):
        L.level(Rect(c, 119, c + 1, 120), k, face=P + "ashlar")
        L.paint(Rect(c, 119, c + 1, 120), STONE)
        L.stair(P + "stair_relief", rect=(c, 119, c, 120), face="east",
                name="south_stair" if k == 0 else f"south_stair_{k}")
        L.level(Rect(c - 1, 119, c - 1, 120), k + 1, face=P + "ashlar")
        L.paint(Rect(c - 1, 119, c - 1, 120), STONE)
        c -= 2
    L.level(Rect(78, 119, 79, 120), 6, face=P + "ashlar")
    L.paint(Rect(78, 119, 79, 120), STONE)
    way(L, [(78, 119), (78, 117)], width=1, paving=STONE)
    L.district("palaces", Rect(78, 119, 92, 120))


def _paradise(L: Layout, noise) -> None:
    """Walled paradise (partetaš): a formal garden round the pavilion over the channel crossing,
    stone channels with square basins, the glazed-brick gate on the west wall (facing the
    Pasargadae road) opening on an axis of cypresses, orchards and flower beds in the quarters,
    the player's walled plot in the north-east corner."""
    # Wall, with openings for the south gate (c 36..37), the outlets (c 32, c 52) and the inlet.
    L.wall(Line([(26, 8), (55, 8)], 1), P + "p_wall")
    L.wall(Line([(55, 9), (55, 20)], 1), P + "p_wall")
    L.wall(Line([(55, 22), (55, 34)], 1), P + "p_wall")
    L.wall(Line([(26, 9), (26, 34)], 1), P + "p_wall")
    for c0, c1 in ((27, 31), (33, 35), (38, 51), (53, 54)):
        L.wall(Line([(c0, 34), (c1, 34)], 1), P + "p_wall")
    # The player's plot: its own low wall, left empty inside (garden soil).
    L.wall(Line([(43, 9), (43, 20)], 1), P + "p_wall")
    L.wall(Line([(44, 20), (54, 20)], 1), P + "p_wall")
    L.paint(PLOT, BED)

    inner = Rect(27, 9, 54, 33) - Rect(43, 9, 54, 20)
    L.paint(inner, BED)
    # Gravel walks: the gate axis (r 26), the pavilion's south walk (c 36), a walk along the
    # inlet (r 21), the pavilion's surround.
    for rect in (Rect(31, 26, 53, 26), Rect(36, 18, 36, 33), Rect(36, 21, 53, 21),
                 Rect(31, 11, 38, 11), Rect(31, 18, 38, 18), Rect(31, 11, 31, 18),
                 Rect(38, 11, 38, 18)):
        L.paint(rect, GRAVEL)
    walks = [way(L, [(31, 26), (53, 26)], width=1, paving=GRAVEL),
             way(L, [(36, 18), (36, 35)], width=1, paving=GRAVEL),
             way(L, [(36, 21), (53, 21)], width=1, paving=GRAVEL),
             way(L, [(36, 18), (38, 18), (38, 11), (31, 11), (31, 18), (36, 18)], width=1,
                      paving=GRAVEL)]
    L.node("pavilion", (36, 18))
    L.node("paradise_gate_w", (25, 26))
    L.node("garden_south_gate", (36, 34))
    for pts in GARDEN_WATER:                       # water wins where it meets the walks
        L.channel(pts, terrain=WATER)
    fords(L, walks)
    # Square basins where channels meet or end; sluices where the water turns (task 3: open the
    # garden channels at dawn).
    for c, r in ((35, 22), (32, 22), (35, 32), (28, 15), (42, 15), (35, 9), (52, 33)):
        L.place(P + "p_basin", at=(c, r))
    for c, r in ((53, 22), (44, 22), (52, 24)):
        L.place(P + "p_sluice", at=(c, r), face="west")
    # Cypress rows flank the gate axis and the south walk; planes at the axis ends.
    L.row(Line([(33, 25), (53, 25)], 1), P + "t_cypress", every=2)
    L.row(Line([(33, 27), (53, 27)], 1), P + "t_cypress", every=2)
    L.row(Line([(37, 28), (37, 33)], 1), P + "t_cypress", every=2)
    L.row(Line([(34, 28), (34, 33)], 1), P + "t_cypress", every=2, offset=1)
    for c, r in ((27, 9), (42, 9), (27, 33), (53, 33), (30, 10), (39, 10), (30, 19), (39, 19)):
        L.place(P + "t_plane", at=(c, r), variant=(c + r) % 2)
    quarters = [(Rect(38, 28, 51, 33), {P + "t_pomegranate": 3, P + "t_almond": 3,
                                         P + "t_fig": 1}),
                (Rect(27, 29, 31, 33), {P + "t_almond": 2, P + "t_date": 1}),
                (Rect(27, 9, 30, 14), {P + "t_pomegranate": 2, P + "t_vine": 1}),
                (Rect(39, 9, 42, 14), {P + "t_almond": 2, P + "t_pomegranate": 1}),
                (Rect(27, 16, 30, 23), {P + "t_almond": 1, P + "t_date": 1, P + "t_fig": 1}),
                (Rect(39, 16, 42, 19), {P + "t_pomegranate": 1, P + "t_almond": 1}),
                (Rect(37, 23, 51, 24), {P + "t_pomegranate": 1, P + "t_vine": 1})]
    for i, (shape, kit) in enumerate(quarters):
        L.scatter(shape, kit, 0.42, min_gap=1, seed=f"orchard{i}")
    L.scatter(inner, {P + "p_lilies": 3, P + "p_rose": 2}, 0.2, seed="beds")


def _forecourt(L: Layout) -> None:
    """The stairway forecourt: horse lines and troughs for arriving riders, banners and braziers
    at the stairway foot, plane trees for shade, a well."""
    for c in (28, 31, 34, 38, 41):
        L.place(P + "p_horse_line", at=(c, 58), face="north")
    for c in (30, 37, 44):
        L.place(P + "p_trough", at=(c, 56), face="north")
    L.place(P + "p_well", at=(42, 38))
    for at in ((45, 43), (45, 48), (48, 39), (48, 52)):
        L.place(P + "p_banner", at=at)
    for at in ((44, 41), (44, 50)):
        L.place(P + "p_brazier", at=at)
    for at in ((27, 36), (27, 44), (45, 36), (45, 59), (27, 59), (33, 37)):
        L.place(P + "t_plane", at=at, variant=at[0] % 2)
    L.place(P + "p_jars", at=(29, 53))
    L.place(P + "p_sacks", at=(30, 53))
    # The terrace foot: drain outfalls in the west face every 10 rows spill into the channel.
    for r in (62, 72, 82, 92, 102, 112):
        L.place(P + "drain_outfall", at=(55, r), face="west")
    # The garden strip below the terrace: cypress row by the face, poplars by the channel.
    L.row(Line([(53, 57), (53, 111)], 1), P + "t_cypress", every=2)
    L.row(Line([(49, 58), (49, 110)], 1), P + "t_poplar", every=3)
    L.scatter(Rect(52, 56, 54, 111), {P + "p_lilies": 2, P + "p_rose": 1}, 0.25, seed="strip")


def _town(L: Layout, spur, noise) -> None:
    """The town of Pārsa: courtyard houses near the forecourt thinning out to the south-west,
    rows of workers' houses west of the spur, a craft quarter by the canal (brickfield, kilns,
    weavers, dyers), the granary yard with its scribes, a small Elamite shrine."""
    E = EARTH
    # Streets: wandering lanes off the spur; the upper street links the forecourt.
    upper = way(L, [(22, 63), (30, 62), (38, 63), (46, 61), (46, 60)], width=2, paving=E)
    lanes = [
        way(L, [(23, 70), (31, 71), (40, 69), (47, 70)], width=1, paving=E),
        way(L, [(23, 79), (30, 78), (36, 80), (47, 79)], width=1, paving=E),
        way(L, [(23, 88), (34, 89), (44, 87), (48, 88)], width=1, paving=E),
        way(L, [(23, 98), (31, 97), (39, 99), (47, 98)], width=1, paving=E),
        way(L, [(23, 106), (35, 107), (44, 105)], width=1, paving=E),
        way(L, [(36, 63), (35, 72), (37, 80), (36, 90)], width=1, paving=E),
        way(L, [(44, 70), (43, 79)], width=1, paving=E),
        way(L, [(30, 89), (29, 98)], width=1, paving=E),
        # west of the spur: the workers' quarter
        way(L, [(20, 66), (12, 65), (1, 66)], width=1, paving=E),
        way(L, [(20, 74), (10, 75), (3, 74)], width=1, paving=E),
        way(L, [(20, 83), (12, 84), (2, 82)], width=1, paving=E),
        way(L, [(20, 93), (9, 92), (1, 93)], width=1, paving=E),
        way(L, [(20, 103), (14, 102), (6, 104), (1, 103)], width=1, paving=E),
        way(L, [(4, 93), (3, 98), (4, 103)], width=1, paving=E),
        way(L, [(12, 65), (11, 75), (12, 84), (10, 92), (14, 102)], width=1, paving=E),
    ]
    fords(L, [upper, *lanes])
    for nid, at in (("town_square", (31, 71)), ("granary_yard", (29, 102)),
                    ("weavers", (41, 80)), ("brickfield", (39, 99)), ("dye_yard", (25, 88)),
                    ("goldsmith", (41, 63)), ("elamite_shrine", (12, 84)),
                    ("workers_quarter", (11, 75))):
        L.node(nid, at)

    # Special places first, so the house filler flows round them.
    # Granary yard: granaries round a court where the scribes measure and seal (ration day).
    for at, face in (((25, 99), "north"), ((25, 102), "north"), ((33, 99), "west"),
                     ((33, 102), "west")):
        L.place(P + "p_granary", at=at, face=face)
    L.paint(Rect(27, 99, 32, 104), GRAVEL)
    for at in ((28, 100), (30, 100)):      # (31, 100) is the east granary's door step
        L.place(P + "p_scribe_desk", at=at, face="south")
    L.place(P + "p_scales", at=(31, 103))
    for at in ((28, 104), (30, 104), (27, 103)):
        L.place(P + "p_sacks", at=at)
    L.place(P + "p_jars", at=(32, 104))
    # Brickfield and kilns (Bēl-iddin) by the canal; drying fields in rows with gaps.
    for at in ((38, 92), (41, 92), (43, 92), (38, 95), (44, 95), (40, 101), (43, 101)):
        L.place(P + "p_brickfield", at=at)
    # The kiln by the road, its loading side (west, a slot in the set now) kept free of the
    # brickfields; the old second and third kilns would load onto a brickfield or where no way
    # reaches.
    L.place(P + "p_kiln", at=(46, 93))
    L.place(P + "p_workshop", at=(41, 95), face="south")
    # Weaving workshop (Ṛtakāmā's forty weavers): sheds with upright looms in a yard.
    L.place(P + "p_workshop", at=(38, 81), face="north")
    L.place(P + "p_workshop", at=(42, 81), face="north")
    weave = way(L, [(41, 80), (41, 86)], width=1, paving=GRAVEL)
    for at, face in (((42, 83), "north"), ((42, 84), "north"), ((42, 85), "north"),
                     ((40, 83), "west"), ((40, 85), "west")):
        L.place(P + "p_loom", at=at, face=face)
    # Dye yard by the canal: vats (jars) and cloth on lines (looms) beside the water.
    for at in ((26, 90), (26, 93), (27, 95)):
        L.place(P + "p_jars", at=at)
    L.place(P + "p_workshop", at=(27, 91), face="west")
    L.place(P + "p_loom", at=(26, 95), face="west")
    # Goldsmith near the terrace (Pediese).
    L.place(P + "p_workshop", at=(42, 64), face="north")
    L.place(P + "p_scales", at=(45, 65))
    # The Elamite shrine: a walled court with an offering table and incense.
    L.wall(Line([(11, 77), (15, 77)], 1), P + "p_wall")
    L.wall(Line([(11, 78), (11, 81)], 1), P + "p_wall")
    L.wall(Line([(15, 78), (15, 81)], 1), P + "p_wall")
    L.place(P + "p_incense", at=(13, 78))
    L.place(P + "p_basin", at=(12, 78))
    L.place(P + "p_fire_altar", at=(14, 79))
    L.place(P + "t_plane", at=(13, 81))

    # Houses: three neighbourhoods, each its own kit and seed; density falls to the south-west.
    # Courtyard houses take the frontage first; smaller houses, stores and sheds fill in.
    near = Rect(22, 62, 48, 86)
    near_front = [upper, *lanes[:3], lanes[5], lanes[6]]
    L.houses(near, {P + "p_house": 1}, front=near_front, gap=0.12, seed="upper_town")
    L.houses(near, {P + "p_house_small": 3, P + "p_granary": 0.5}, front=near_front, gap=0.2,
             seed="upper_town_fill")
    crafts = Rect(22, 87, 48, 111) - Rect(26, 99, 32, 105)   # the granary court stays open
    crafts_front = [lanes[2], lanes[3], lanes[4], lanes[7]]
    L.houses(crafts, {P + "p_house": 2, P + "p_workshop": 1}, front=crafts_front, gap=0.25,
             seed="crafts")
    L.houses(crafts, {P + "p_house_small": 3, P + "p_granary": 0.3}, front=crafts_front,
             gap=0.2, seed="crafts_fill")
    workers = Rect(0, 62, 20, 111)
    L.houses(workers, {P + "p_house_small": 5, P + "p_house": 1.5},
             front=lanes[8:], gap=0.15, seed="workers")
    # Yards: bread ovens, jars, wells, a few dovecotes; trees in courtyards and gardens.
    town = Rect(0, 62, 48, 111)
    L.scatter(town, {P + "p_oven": 2, P + "p_jars": 2, P + "p_sacks": 1, P + "p_well": 0.6,
                     P + "p_dovecote": 0.5}, 0.035, min_gap=2, seed="yards")
    trees = L.scatter(town, {P + "t_pomegranate": 2, P + "t_fig": 2, P + "t_almond": 1,
                             P + "t_vine": 2, P + "t_poplar": 1}, 0.06, seed="town_trees", clump=0.7)
    # A tree never stands where someone works: the workshops' spots lie on the step outside.
    spots = {(c, r) for q in L.items if not q.removed for v in q.slots.values() for c, r, _f in v}
    for t in trees:
        if any(x in spots for x in t.tiles()):
            L.remove(t)
    # Kitchen gardens on the town's open ground toward the fields.
    L.paint(Rect(1, 105, 13, 111) & free(L, Rect(1, 105, 13, 111)), BED)
    # Poplars along the town canal, willows where it leaves the town.
    L.row(Line([(23, 53), (23, 110)], 1), P + "t_poplar", every=3)


def _terrace_detail(L: Layout) -> None:
    """Guards' posts, fire altars, braziers and torches, the building site's stone and timber,
    the Hadiš kitchens, the archive corner."""
    # Stair top and Gate: banners, torches, braziers.
    for at in ((56, 42), (56, 48), (62, 42), (62, 48)):
        L.place(P + "p_banner", at=at)
    for at in ((60, 43), (60, 47)):
        L.place(P + "p_brazier", at=at)
    # The processional road, walled on both sides, torches along the walls.
    L.wall(Line([(70, 42), (88, 42)], 1), P + "p_wall")
    L.wall(Line([(70, 47), (87, 47)], 1), P + "p_wall")
    L.wall(Line([(91, 42), (92, 42)], 1), P + "p_wall")
    for c in (73, 79, 85):
        L.place(P + "p_torch", at=(c, 41), face="south")
    # North court: the dawn fire altars, incense at the Apadāna's north stair.
    for at in ((74, 33), (78, 33)):
        L.place(P + "p_fire_altar", at=at)
    for at in ((64, 49), (79, 49)):
        L.place(P + "p_incense", at=at)
    # The building site: stacked drums and capital blocks, shear-leg cranes (the ox sledges and
    # carts are actors, world-tech §1.9).
    for at in ((91, 38), (93, 38), (95, 38), (103, 38), (105, 39), (108, 38), (92, 45),
               (106, 45), (110, 46), (96, 70), (98, 72), (110, 70), (112, 72), (104, 77),
               (95, 77)):
        L.place(P + "p_drum_stack", at=at, face="west" if at[0] % 2 else "north")
    for at in ((96, 46), (102, 45), (98, 69), (106, 69)):
        L.place(P + "p_crane", at=at, face="west")
    for at in ((112, 40), (113, 41), (110, 77)):
        L.place(P + "p_jars", at=at)
    # The Tripylon may still be unfinished in 470 (fact-check §1.3: Xerxes and Artaxerxes I):
    # scaffold poles against its walls, where they leave the doors and stairs free.
    for at in ((86, 72), (86, 76), (94, 72), (89, 79), (92, 79)):
        put(L, P + "p_scaffold", at)
    # The archive in the fortification's north-east corner (where the tablets were found).
    for at in ((114, 38), (116, 38)):
        L.place(P + "p_scribe_desk", at=at, face="south")
    for at in ((114, 40), (115, 40), (116, 40)):
        L.place(P + "p_jars", at=at)
    # Garrison: braziers at its gate, banners.
    for at in ((94, 33), (94, 37)):
        L.place(P + "p_brazier", at=at)
    # Treasury door: scales, guards' braziers.
    L.place(P + "p_scales", at=(112, 112))
    for at in ((110, 112), (116, 112)):
        L.place(P + "p_brazier", at=at)
    # Hadiš kitchens: tanūr ovens, jars, sacks in the court south of the palace.
    for at in ((77, 103), (80, 103), (83, 103)):
        L.place(P + "p_oven", at=at)
    for at in ((78, 106), (79, 106), (82, 106), (84, 105)):
        L.place(P + "p_jars", at=at)
    L.place(P + "p_sacks", at=(81, 106))
    # Guard posts: a brazier and a banner at the corners of the courts and along the edges,
    # banners down the processional road, scribes registering visitors by the Gate.
    for at in ((57, 23), (93, 23), (57, 40), (94, 40), (57, 79), (99, 79), (57, 117),
               (99, 112), (117, 79), (117, 117), (84, 78), (60, 101)):
        put(L, P + "p_brazier", at)
        put(L, P + "p_banner", (at[0] + 1, at[1]))
    for c in range(71, 92, 4):
        put(L, P + "p_banner", (c, 48))
    for at in ((71, 41), (73, 41)):
        put(L, P + "p_scribe_desk", at, "south")
    for at in ((75, 41), (76, 41)):
        put(L, P + "p_jars", at)
    for at in ((70, 43), (70, 46)):
        put(L, P + "p_incense", at)
    # The Tačara and Hadiš courts: incense before the porticoes, a throne-dais carpet.
    for at in ((64, 96), (69, 96), (77, 86), (84, 86)):
        put(L, P + "p_incense", at)
    put(L, P + "p_carpet", (79, 86), "north")
    # The royal kitchens' service yard south of the Tačara court: a walled yard of sheds,
    # bread ovens, storerooms and a well; servants carry the dishes up the Hadiš stair.
    for pts in ([(59, 106), (65, 106)], [(68, 106), (74, 106)], [(59, 107), (59, 116)],
                [(74, 107), (74, 116)], [(60, 116), (73, 116)]):
        L.wall(Line(pts, 1), P + "p_wall")
    way(L, [(66, 104), (66, 111), (70, 111)], width=1, paving=STONE)
    L.node("royal_kitchens", (66, 110))
    for at in ((60, 108), (67, 108), (71, 108)):
        put(L, P + "p_workshop", at, "north")
    for at in ((61, 112), (63, 112), (70, 111), (72, 111)):
        put(L, P + "p_oven", at)
    for at in ((65, 113), (68, 113)):
        put(L, P + "p_granary", at, "north")
    put(L, P + "p_well", (71, 114))
    for at in ((60, 114), (61, 114), (62, 115), (72, 113)):
        put(L, P + "p_jars" if at[0] % 2 else P + "p_sacks", at)
    # Torches at the palaces' stairs, braziers in the courts.
    for at in ((62, 94), (72, 94), (72, 86), (84, 82)):
        L.place(P + "p_torch", at=at, face="south")
    for at in ((60, 82), (96, 82)):
        L.place(P + "p_brazier", at=at)


def _plain(L: Layout, noise) -> None:
    """Fields, village, stables, station and caravan yard, cavalry ground, the delegations'
    camp, pastures and the trees of the plain."""
    # --- river banks: willows and reeds, poplars by the canal -------------------------------
    band = Line(RIVER_PTS, 7) - Line(RIVER_PTS, 3)
    L.scatter(band, {P + "t_willow": 3, "world.t_reeds": 4, P + "t_poplar": 1}, 0.35,
              seed="banks", clump=0.6)
    L.row(Line([(58, 8), (58, 21)], 1), P + "t_poplar", every=2)

    # --- fields (D6) and the village ---------------------------------------------------------
    L.fields(Rect(27, 4, 53, 5) | Rect(27, 7, 53, 7), FIELD, plot=(5, 2), seed="north_strip")
    west = Rect(0, 22, 23, 61) - Rect(1, 24, 17, 40)
    # Grass balks between the plots, so the roads stand out from the fields.
    L.fields(west, FIELD, plot=(5, 4), path=GRASS, seed="west_fields")
    L.fields(Rect(0, 113, 13, 143) | Rect(15, 122, 19, 143), FIELD, plot=(4, 5), path=GRASS,
             seed="south_fields")
    # Poplars along the Royal Road's last stretch to the forecourt.
    L.row(Line([(1, 48), (23, 48)], 1), P + "t_poplar", every=4, offset=1)
    L.row(Line([(1, 53), (19, 53)], 1), P + "t_poplar", every=4, offset=3)
    village = Rect(1, 24, 17, 40)
    vlane = way(L, [(24, 33), (17, 32), (9, 33), (3, 31)], width=1, paving=EARTH)
    vlane2 = way(L, [(9, 33), (8, 26)], width=1, paving=EARTH)
    fords(L, [vlane, vlane2])
    L.node("village", (9, 33))
    L.place(P + "p_threshing", at=(11, 35))
    L.place(P + "p_threshing", at=(3, 36))
    L.node("threshing_floor", (12, 34))
    L.houses(village, {P + "p_house": 2, P + "p_house_small": 2, P + "p_granary": 1},
             front=[vlane, vlane2], gap=0.15, seed="village")
    L.scatter(village, {P + "p_dovecote": 1, P + "p_oven": 1, P + "p_well": 0.5,
                        P + "p_sacks": 1}, 0.05, min_gap=2, seed="village_yards")
    L.scatter(village, {P + "t_almond": 1, P + "t_pomegranate": 1, P + "t_poplar": 1}, 0.08,
              seed="village_trees")
    # Poplars along the field canals, a few trees at field corners.
    L.row(Line([(23, 36), (23, 48)], 1), P + "t_poplar", every=3)
    L.scatter(west | Rect(0, 113, 19, 143), {P + "t_poplar": 2, P + "t_almond": 1,
                                             P + "t_plane": 1}, 0.012, min_gap=3, seed="field_trees")

    # --- royal stables north of the terrace --------------------------------------------------
    for i, (c0, r0, c1, r1) in enumerate(((62, 9, 73, 18), (77, 9, 88, 18), (92, 10, 99, 18))):
        L.wall(Line([(c0, r0), (c1, r0)], 1), P + "p_wall")
        L.wall(Line([(c0, r0 + 1), (c0, r1)], 1), P + "p_wall")
        L.wall(Line([(c1, r0 + 1), (c1, r1)], 1), P + "p_wall")
        L.wall(Line([(c0 + 1, r1), (c0 + 3, r1)], 1), P + "p_wall")
        L.wall(Line([(c0 + 6, r1), (c1 - 1, r1)], 1), P + "p_wall")
        L.place(P + "p_horse_line", at=(c0 + 2, r0 + 3), face="north")
        L.place(P + "p_horse_line", at=(c0 + 2, r0 + 6), face="north")
        L.place(P + "p_trough", at=(c1 - 2, r0 + 2))
    stab = way(L, [(54, 5), (59, 7), (59, 20), (80, 21), (96, 20)], width=1, paving=EARTH,
                    kind="track")
    fords(L, [stab])
    L.node("royal_stables", (80, 21))
    L.houses(Rect(60, 19, 99, 21) - Rect(57, 20, 99, 21), {P + "p_granary": 1}, front=[stab],
             gap=0.5, seed="stable_stores")
    L.scatter(Rect(59, 4, 103, 21), {P + "t_poplar": 1, P + "t_plane": 1, P + "t_almond": 1},
              0.03, min_gap=2, seed="stable_trees")
    L.scatter(Rect(59, 4, 112, 21), {P + "p_steppe": 2, P + "p_lilies": 1}, 0.08, seed="north_tufts")

    # --- road station and caravan yard (D7) --------------------------------------------------
    L.paint(Rect(29, 113, 34, 126), EARTH)
    yard = way(L, [(18, 113), (34, 113)], width=1, paving=EARTH)
    way(L, [(28, 127), (34, 127), (34, 114)], width=1, paving=EARTH, kind="track")
    way(L, [(18, 118), (19, 118)], width=1, paving=EARTH)
    L.node("royal_road_station", (19, 117))
    L.node("caravan_yard", (31, 119))
    for at in ((30, 115), (30, 121)):
        L.place(P + "p_horse_line", at=at, face="north")
    for at in ((33, 118), (29, 124)):
        L.place(P + "p_trough", at=at)
    L.place(P + "p_well", at=(33, 124))
    for at in ((30, 117), (31, 117), (33, 116), (31, 124), (32, 125)):
        L.place(P + "p_sacks" if at[0] % 2 else P + "p_jars", at=at)

    # --- cavalry and archery ground (D8) -----------------------------------------------------
    L.paint(Ellipse(43, 125, 7, 8) - Ellipse(43, 125, 5, 6), EARTH)
    L.paint(Ellipse(43, 125, 4, 5), GRAVEL)
    for r in range(123, 134, 3):
        L.place(P + "p_archery_butt", at=(54, r), face="west")
    way(L, [(52, 116), (43, 116), (43, 120)], width=1, paving=EARTH, kind="track")
    way(L, [(53, 133), (53, 114), (55, 114)], width=1, paving=EARTH, kind="track")  # shooting line
    L.node("archery_ground", (53, 128))
    L.node("cavalry_ground", (43, 120))
    for at in ((36, 115), (39, 115)):
        L.place(P + "p_horse_line", at=at, face="north")
    L.place(P + "p_trough", at=(46, 115))

    # --- the delegations' camp on the plain south of the terrace ----------------------------
    # Each delegation pitches its tents round its own fire, doors turned to it where the tents
    # allow, horses tethered at one side, a banner, carpets and baggage; no two pitches alike.
    camps = [(61, 126), (71, 129), (81, 125), (91, 129), (100, 125), (66, 133), (80, 133),
             (96, 133), (106, 129)]
    ring = [((-1, -3), "west"), ((2, -3), "west"), ((2, -1), "north"), ((-4, -3), "west"),
            ((-4, 0), "north"), ((2, 1), "west"), ((-2, 1), "west")]
    lanes = [L.street(orth([(c, r - 1), (c, 122)]), width=1, paving=EARTH, kind="track")
             for c, r in camps]
    fords(L, lanes)
    for i, (c, r) in enumerate(camps):
        st = rng.stream("parsa", "camp", i)
        L.paint(Ellipse(c, r, 4 + st.randint(0, 2), 2 + st.randint(0, 1)), EARTH)
        L.place(P + "p_brazier", at=(c, r))
        order = sorted(ring, key=lambda t: rng.hash64("parsa", "tents", i, t[0]))
        for (dc, dr), face in order[: 2 + st.randint(0, 3)]:
            put(L, P + "p_tent", (c + dc, r + dr), face)
        side = -1 if st.chance(0.5) else 1
        put(L, P + "p_horse_line", (c + side * 5 - 1, r + st.randint(-2, 1)),
             "west" if st.chance(0.5) else "north")
        put(L, P + "p_banner", (c + 1, r - 1))
        for item in (P + "p_carpet", P + "p_jars", P + "p_sacks", P + "p_jars"):
            if st.chance(0.6):
                put(L, item, (c + st.randint(-3, 3), r + st.randint(-1, 2)), "north")
    pitches = Rect(0, 0, 0, 0) - Rect(0, 0, 0, 0)
    for c, r in camps:
        pitches = pitches | Rect(c - 7, r - 4, c + 7, r + 3)
    L.scatter(CAMP - pitches, {P + "p_steppe": 2, P + "p_lilies": 1}, 0.06, seed="camp_tufts")
    L.scatter(Rect(56, 119, 112, 121), {P + "t_poplar": 1}, 0.12, min_gap=3, seed="camp_poplars")

    # --- southern plain and qanat (D9): pasture, sheep folds, tulips -------------------------
    way(L, [(23, 132), (28, 132), (28, 127)], width=1, paving=EARTH, kind="track")
    for i, (c0, r0) in enumerate(((22, 128), (58, 136), (88, 136))):
        L.wall(Line([(c0, r0), (c0 + 5, r0)], 1), P + "p_wall")
        L.wall(Line([(c0, r0 + 1), (c0, r0 + 3)], 1), P + "p_wall")
        L.wall(Line([(c0 + 5, r0 + 1), (c0 + 5, r0 + 3)], 1), P + "p_wall")
        L.wall(Line([(c0 + 3, r0 + 3), (c0 + 4, r0 + 3)], 1), P + "p_wall")
        L.place(P + "p_trough", at=(c0 + 2, r0 + 1))
    L.scatter(Rect(20, 127, 119, 143) - pitches, {P + "p_steppe": 4, P + "p_lilies": 2,
                                                  P + "p_rose": 1},
              0.1, seed="pasture", clump=0.6)
    L.scatter(Rect(20, 127, 103, 143), {P + "t_almond": 1, P + "t_poplar": 1, P + "t_fig": 1},
              0.01, min_gap=4, seed="pasture_trees")
    L.node("sheepfold", (23, 132))
    # Foothills: tufts and scrub on the lower slopes.
    L.scatter(Rect(100, 0, 119, 21) | Rect(100, 119, 119, 143), {P + "p_steppe": 3},
              0.18, seed="foothill_tufts")


def _naqsh(L: Layout) -> None:
    """Naqsh-e Rostam: the cliff with Darius I's tomb facing south, the Ka'ba-ye Zartosht in
    front of it, a fire altar; a gravel court before the tomb, steppe and a few trees."""
    L.paint(Rect(5, 9, 15, 11), GRAVEL)
    L.place(P + "p_fire_altar", at=(6, 11))
    L.scatter(Rect(0, 9, 20, 17), {P + "p_steppe": 3, P + "p_lilies": 1}, 0.12, seed="naqsh_tufts")
    L.scatter(Rect(14, 12, 20, 17), {P + "t_cypress": 1, P + "t_almond": 1}, 0.06, min_gap=2,
              seed="naqsh_trees")
    L.scatter(S1_BAND, {P + "p_steppe": 1}, 0.2, seed="band_tufts")
