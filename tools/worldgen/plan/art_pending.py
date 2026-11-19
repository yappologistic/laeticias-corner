"""Faults of the placed world whose fix is the art lane's: a set's geometry file puts a slot
spot, a walk tile or a clearance where the layout cannot change it (landmarks stay where the
city files put them; kit spots move with their kit). Each entry turns that walkability error
(`worldgen/walkable.py`) into a warning naming what the art must change; an entry no fault
matches any more is an error (`build.sh --check`), so the list only shrinks.

Key: (rule, item id, slot id or "" for the whole item). The full list with coordinates is
`out/reports/world-walkable.md`.
"""

# The bridges' clearances have landed (geometry `pass`, art-smooth-land.md §8): lanes pass under
# a bridge only where their boats fit, which W-O2 holds as an error. Nothing is pending.
ART: dict[tuple[str, str, str], str] = {}
