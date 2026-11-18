"""Faults of the placed world whose fix is the art lane's: a set's geometry file puts a slot
spot, a walk tile or a clearance where the layout cannot change it (landmarks stay where the
city files put them; kit spots move with their kit). Each entry turns that walkability error
(`worldgen/walkable.py`) into a warning naming what the art must change; an entry no fault
matches any more is an error (`build.sh --check`), so the list only shrinks.

Key: (rule, item id, slot id or "" for the whole item). The full list with coordinates is
`out/reports/world-walkable.md`.
"""

_UNDER = ("boats on this lane pass under it, and its geometry declares no clearance there "
          "(`under`, px above the water per deck piece: none, or 0 for a solid deck): the arch "
          "pieces need their real clearance")

ART: dict[tuple[str, str, str], str] = {
    # Kit spots inside their own footprint.
    ("W-L1", "parsa.p_workshop", "work"):
        "the work spots lie inside the workshop's footprint on tiles its geometry does not make "
        "walkable: walk tiles under them or the spots on the step outside",
    ("W-L1", "parsa.tripylon", "guard"): "the guard spots fall on the Tripylon stair's parapet "
                                         "tiles: put them on its walk tiles or beside the flight",
    # Walk tiles the geometry does not give.
    ("W-S3", "parsa.apadana_stair_e", ""):
        "its head runs into the Apadana's platform edge (grid (365..366, 60)) where the "
        "Apadana's geometry has no walk tile: walk tiles on the platform at the stair's head",
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
