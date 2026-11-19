"""Faults of the placed world whose fix is the art lane's: a set's geometry file puts a slot
spot, a walk tile or a clearance where the layout cannot change it (landmarks stay where the
city files put them; kit spots move with their kit). Each entry turns that walkability error
(`worldgen/walkable.py`) into a warning naming what the art must change; an entry no fault
matches any more is an error (`build.sh --check`), so the list only shrinks.

Key: (rule, item id, slot id or "" for the whole item). The full list with coordinates is
`out/reports/world-walkable.md`.
"""

# Measured on the art of 2026-11 (`assets/atlas/<set>.geom.json`): the bridges declare `under`
# only for the middle row of their pieces (16-18 px) and 0 for the rows a boat meets first, and
# the boats on these lanes stand 58-74 px above the water (their sprites' anchors).
_UNDER = ("boats on this lane pass under it and its geometry declares no clearance a boat fits "
          "(`under`, px above the water per deck piece): the arch's clearance on every row the "
          "boat passes (both faces as well as the middle), as high as the arch is drawn")

ART: dict[tuple[str, str, str], str] = {
    # Walk tiles the geometry does not give.
    ("W-S3", "parsa.apadana_stair_e", ""):
        "its head runs into the Apadana's platform edge (grid (365..366, 60)) where the "
        "Apadana's geometry has no walk tile: walk tiles on the platform at the stair's head",
    # Clearances under crossings.
    ("W-O2", "rome.pons_sublicius", ""): _UNDER,
    ("W-O2", "rome.pons_aemilius", ""): _UNDER,
    ("W-O2", "rome.pons_fabricius", ""): _UNDER,
    ("W-O2", "world.bridge_arch", ""): _UNDER,
    ("W-O2", "world.bridge_timber", ""): _UNDER,
}
