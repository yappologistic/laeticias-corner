"""Ostia and Portus, AD 126 (rome.md §3.7): the template waypoint town.

World rect C 100..170, R 184..239; local (c, r) = world (C - 100, R - 184); local level 0 = world
level 1. The Tiber comes in from Rome's south edge at local (52, 0) and reaches the sea at about
(26, 45). North-west of the mouth, Trajan's hexagonal basin (`portus_hexagon`, 20 x 18) behind
Claudius's outer harbour with the lighthouse on its mole; south-east of the mouth, the town of
Ostia (`ostia_town`, kit, about 24 x 16) on a decumanus and cardo, its forum and Capitolium, the
river harbour with quays; the Via Ostiensis leaves north-east for Rome past tombs and pines.

Water sits one level below the land (world level 0), so river banks and quays read as
embankments. The coast follows the base layer's generated shoreline.
"""

from worldgen.dsl import Layout
from worldgen.shapes import Line, Poly, Rect

TIBER = [(52, 0), (49, 10), (44, 19), (38, 27), (32, 35), (28, 41), (26, 46)]


def build(L: Layout) -> None:
    sea = L.sea_below()
    L.fill("rome.grass_spring", level=0, district="fields")
    L.paint(sea, "world.sea")
    L.level(sea, -1)
    L.district("sea", sea)
    L.level(L.coast_below(), 0, face="world.coast")

    # --- Portus: the outer harbour (open to the sea), the lighthouse mole, the hexagon ------
    outer = Poly([(1, 27), (12, 26), (16, 30), (14, 36), (6, 38), (0, 36)]) | (sea & Rect(0, 30, 20, 55))
    L.paint(outer, "world.sea")
    L.level(outer, -1)
    L.district("portus", Rect(0, 8, 30, 40))
    L.district("sea", outer)
    # Moles: two arms of travertine closing the outer harbour, the lighthouse island between.
    L.paint(Line([(12, 26), (16, 30), (16, 34)], 1), "rome.travertine_paving")
    L.level(Line([(12, 26), (16, 30), (16, 34)], 1), 0)
    L.paint(Rect(5, 37, 7, 39), "rome.travertine_paving")
    L.level(Rect(5, 37, 7, 39), 0, face="world.coast")
    L.place("rome.portus_lighthouse", rect=(5, 37, 7, 39), name="portus_lighthouse")

    # --- the road between Portus and Ostia, over the Tiber on spans (laid before any houses) --
    bridge_road = [(24, 15), (34, 17), (40, 20), (47, 22), (52, 28), (56, 38)]
    L.street(bridge_road, width=1, paving="rome.basalt_paving", kind="road")
    L.node("portus", (24, 15))

    # Trajan's basin: a hexagon of harbour water inside a quay ring, warehouses round it.
    hexa = Rect(4, 9, 23, 26)
    L.level(hexa, -1)
    L.paint(hexa, "rome.travertine_paving")
    basin = Poly([(9, 11), (18, 11), (21, 17), (18, 24), (9, 24), (6, 17)])
    L.paint(basin, "world.sea")
    L.place("rome.portus_hexagon", rect=hexa, name="portus_hexagon")
    L.channel([(13, 24), (12, 27)], terrain="world.sea", width=2)  # basin mouth to the outer harbour
    L.level(Rect(12, 25, 13, 27), -1)
    # The Fossa Traiana: a canal from the basin to the Tiber.
    L.channel([(23, 20), (30, 22), (39, 25)], terrain="world.river", width=2)
    L.level(Line([(23, 20), (30, 22), (39, 25)], 2), -1)
    L.houses(Rect(0, 4, 30, 8) | Rect(24, 8, 30, 19), {"rome.r_horrea": 3, "rome.r_insula_low": 1},
             front=[L.street([(2, 7), (28, 7), (28, 19)], width=1, paving="rome.packed_earth")],
             gap=0.1, seed="portus_horrea")

    # --- the Tiber, its quays and the river harbour ------------------------------------------
    L.paint(Line([(46, 20), (41, 27), (35, 36), (31, 43)], 3), "rome.travertine_paving")
    L.river(TIBER, width=5, terrain="world.river", banks={"world.t_reeds": 0.25}, seed="tiber")
    L.level(Line(TIBER, 5), -1)
    L.district("river", Line(TIBER, 7))
    L.row(Line([(45, 22), (40, 29), (36, 35)], 1), "rome.quay_mooring", every=3)
    L.lane("tiber_ostia", TIBER[:5], kind="river", ports={"rome_edge": 0, "ostia_quay": 4})
    for c, r in Line(bridge_road, 1).path():
        if L.terrain_at(c + L.origin[0], r + L.origin[1]) == "world.river":
            L.place("rome.pons_span", at=(c, r), face="north")

    # --- Ostia: decumanus, cardo, forum and Capitolium, lanes, insulae ------------------------
    forum = Rect(39, 35, 48, 38)
    town = Rect(30, 28, 56, 47) - Line(TIBER, 9) - sea - forum
    L.district("town", town | forum)
    dec = L.street([(33, 39), (57, 39), (63, 30), (63, 0)], width=2, paving="rome.basalt_paving",
                   kind="road", portal="ostiensis")
    cardo = L.street([(43, 41), (43, 48)], width=2, paving="rome.basalt_paving")
    north = L.street([(37, 38), (37, 33)], width=1, paving="rome.basalt_paving")
    lanes = [L.street([(34, 44), (55, 44)], width=1, paving="rome.packed_earth"),
             L.street([(50, 30), (50, 47)], width=1, paving="rome.packed_earth"),
             L.street([(44, 31), (55, 31)], width=1, paving="rome.packed_earth")]
    L.paint(forum, "rome.travertine_paving")
    L.place("rome.r_temple", rect=(41, 32, 45, 34), face="south", name="capitolium")
    L.place("rome.r_statue", at=(39, 36))
    L.place("rome.r_statue", at=(48, 36))
    L.place("rome.r_lacus", at=(46, 37))
    L.node("forum", (44, 37))
    L.node("quay", (37, 33))
    L.houses(town, {"rome.r_insula": 3, "rome.r_insula_low": 3, "rome.r_horrea": 1,
                    "rome.r_taberna": 2, "rome.r_bakery": 0.6},
             front=[dec, cardo, north, *lanes], gap=0.12, seed="ostia")
    L.scatter(town, {"rome.r_amphorae": 2, "rome.r_lacus": 0.5, "rome.r_compitum": 0.5}, 0.03,
              seed="yards")

    # --- outside the walls: tombs and pines along the Via Ostiensis, market gardens ----------
    L.district("road", Line([(57, 39), (63, 30), (63, 0)], 5))
    L.row(Line([(61, 29), (61, 3)], 1), "rome.r_tomb", every=5, face="east", offset=1)
    L.row(Line([(66, 28), (66, 2)], 1), "rome.t_stone_pine", every=3)
    L.fields(Rect(56, 41, 70, 52) - sea, "rome.field_spring", plot=(4, 3), path="rome.packed_earth",
             seed="gardens")
    L.fields(Rect(52, 4, 59, 24), "rome.field_spring", plot=(3, 4), path="rome.packed_earth",
             seed="north_gardens")
    L.scatter(Rect(0, 0, 70, 55) - town, {"rome.t_stone_pine": 3, "rome.t_cypress": 1,
                                         "rome.t_oak": 1}, 0.05, seed="country", clump=0.7)

    L.expect("portus_hexagon", rect=(4, 9, 23, 26), level=-1)
    L.expect("portus_lighthouse", rect=(5, 37, 7, 39), level=0)
    L.view("town", Rect(28, 26, 58, 52))
    L.view("portus", Rect(0, 6, 30, 40))
    L.view("whole", Rect(0, 0, 70, 55))
