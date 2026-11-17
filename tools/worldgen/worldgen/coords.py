"""Plan <-> grid conversion (world-tech conventions): tx = R, ty = COLS - 1 - C.

Plan coordinates (C, R) are north-up (C east, R south); grid coordinates (tx, ty) are the
engine's (+x down-right = south, +y down-left = west). Everything worldgen authors and validates
is in plan coordinates; only the file writers and readers speak grid.
"""

from __future__ import annotations

from plan.world_plan import GRID_COLS as COLS, GRID_ROWS as ROWS

FACINGS = {"west": 0, "north": 1, "east": 2, "south": 3}  # kit r<k> by compass facing
FACING_NAMES = {v: k for k, v in FACINGS.items()}
# Grid direction of the front face of a rotate kit for each k: r0 faces +y (west).
GRID_FRONT = {0: (0, 1), 1: (-1, 0), 2: (0, -1), 3: (1, 0)}
# Plan step (dc, dr) for each compass word.
PLAN_STEP = {"west": (-1, 0), "north": (0, -1), "east": (1, 0), "south": (0, 1)}


def to_grid(c: int, r: int) -> tuple[int, int]:
    return (r, COLS - 1 - c)


def to_plan(tx: int, ty: int) -> tuple[int, int]:
    return (COLS - 1 - ty, tx)


def where(c: int, r: int, origin: tuple[int, int] | None = None) -> str:
    """Human description of a world plan tile: local (if an origin is given), plan and grid."""
    tx, ty = to_grid(c, r)
    loc = f"local ({c - origin[0]}, {r - origin[1]}) = " if origin else ""
    return f"{loc}plan ({c}, {r}) = grid ({tx}, {ty})"
