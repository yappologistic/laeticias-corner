"""Faults of the placed world whose fix is the art lane's: a set's geometry file puts a slot
spot, a walk tile or a clearance where the layout cannot change it (landmarks stay where the
city files put them; kit spots move with their kit). Each entry turns that walkability error
(`worldgen/walkable.py`) into a warning naming what the art must change; an entry no fault
matches any more is an error (`build.sh --check`), so the list only shrinks.

Key: (rule, item id, slot id or "" for the whole item). The full list with coordinates is
`out/reports/world-walkable.md`.
"""

_UNDER = ("its geometry declares no clearance (`under`, px above the water per deck piece): "
          "boats on this lane pass under its arches")
_NEIGHBOUR = "the spot falls on the neighbouring landmark at its city-file rect: move it to the "

ART: dict[tuple[str, str, str], str] = {
    # Kit spots inside their own footprint.
    ("W-L1", "rome.mutatio", "change"):
        "the change spots lie inside the station's footprint on tiles its geometry does not "
        "make walkable: walk tiles under them (a yard) or the spots on the step outside",
    ("W-L1", "parsa.p_workshop", "work"):
        "the work spots lie inside the workshop's footprint on tiles its geometry does not make "
        "walkable: walk tiles under them or the spots on the step outside",
    # Landmark spots on a neighbouring landmark (both at their city-file rects).
    ("W-L1", "rome.curia", "senator"): _NEIGHBOUR + "Comitium side clear of the Lapis Niger",
    ("W-L1", "rome.lacus_iuturnae", "fill"): _NEIGHBOUR + "basin's open side, off the Castor",
    ("W-L1", "rome.vesta", "vestal"): _NEIGHBOUR + "temple's free side, off the House of the "
                                                   "Vestals",
    ("W-L1", "rome.trajan_column", "read"): _NEIGHBOUR + "court between the libraries, off the "
                                                         "Basilica Ulpia",
    ("W-L1", "rome.trajan_markets", "shop"): _NEIGHBOUR + "Markets' street side, off Trajan's "
                                                          "Forum",
    ("W-L1", "rome.pantheon", "visit"): _NEIGHBOUR + "porch's own step, off the forecourt's "
                                                     "colonnade",
    ("W-L1", "parsa.tripylon", "guard"): "the guard spots fall on the Tripylon stair's parapet "
                                         "tiles: put them on its walk tiles or beside the flight",
    # Walk tiles the geometry does not give.
    ("W-S3", "parsa.apadana_stair_e", ""):
        "its head runs into the Apadana's platform edge (grid (365..366, 60)) where the "
        "Apadana's geometry has no walk tile: walk tiles on the platform at the stair's head",
    ("W-L3", "rome.portus_hexagon", "mooring"):
        "the basin's quay ring has no walk tiles, so no one reaches the moored ships: walk tiles "
        "on the quays round the basin",
    # Clearances under crossings.
    ("W-O2", "rome.pons_sublicius", ""): _UNDER,
    ("W-O2", "rome.pons_aemilius", ""): _UNDER,
    ("W-O2", "rome.pons_fabricius", ""): _UNDER,
    ("W-O2", "rome.tiber_island", ""):
        "the lane runs down the island's east channel inside its footprint: the channel's tiles "
        "as `water` (open to boats) or a clearance under its bridges",
    ("W-O2", "world.bridge_arch", ""): _UNDER,
    ("W-O2", "world.bridge_timber", ""): _UNDER,
}
