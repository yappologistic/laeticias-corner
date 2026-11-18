"""Carried lights (out/reports/world-nights.md §7): a hand lamp, a torch and a lantern, each a
small model anchored at the grip, drawn by the engine at the hand point the geometry gives for
every frame of a light-bearer's walk and stand (`hand_at`). Four frames of a flame that leans
and breathes; the glow layer is the flame and a soft halo. Sets list theirs in the catalog's
`art.props` as `<set>.lamp`, `<set>.torch`, `<set>.lantern`; the material follows the set."""

import math

from arch import ellipsoid, halo, rod
from palette import GLOW, _rgb
from voxel import Model

FRAMES = 4
FLAME = _rgb(GLOW[1])
# A set's lamps: Attic and Italian lamps are fired clay, Persian ones bronze.
LAMP_BODY = {"parsa": "bronze", "world": "clay"}


def _flame(m: Model, x, y, z, r, h, frame):
    lean = 0.25 * math.sin(frame / FRAMES * 2 * math.pi)
    breathe = 1.0 + 0.12 * math.cos(frame / FRAMES * 2 * math.pi + 0.7)
    ellipsoid(m, (x + lean * 0.5, y, z + h * 0.45 * breathe), (r, r, h * 0.55 * breathe), "fire", tone=0.2)
    ellipsoid(m, (x + lean, y, z + h * 0.65 * breathe), (r * 0.5, r * 0.5, h * 0.35 * breathe), "lamp")


def model(prop_id: str, frame: int, k: int) -> Model:
    set_id, name = prop_id.split(".")
    m = Model.empty(-4, 4, -4, 4, -5, 9, k=k)
    m.hover = True                      # held in the air: no ground contact
    if name == "lamp":                  # a palm-sized oil lamp, the wick at its nozzle
        body = LAMP_BODY.get(set_id, "terracotta")
        ellipsoid(m, (0.0, 0.0, 0.4), (1.1, 0.9, 0.5), body, tone=0.2)
        rod(m, (0.6, 0.0, 0.6), (1.5, 0.0, 0.7), 0.35, body, tone=0.3)
        _flame(m, 1.6, 0.0, 0.9, 0.35, 1.3, frame)
        halo(m, 1.6, 0.0, 1.6, 4.0, FLAME, 0.7)
    elif name == "torch":               # pine splints bound round a staff, a pitch-soaked head
        rod(m, (0.0, 0.0, -3.0), (0.2, 0.0, 3.0), 0.35, "wood", tone=0.1)
        ellipsoid(m, (0.2, 0.0, 3.0), (0.55, 0.55, 0.7), "bark", tone=0.2)
        _flame(m, 0.25, 0.0, 3.4, 0.7, 2.6, frame)
        halo(m, 0.3, 0.0, 4.8, 7.0, FLAME, 0.9)
    elif name == "lantern":             # a bronze lantern with horn panes, hanging from the hand
        rod(m, (0.0, 0.0, 0.0), (0.0, 0.0, -0.9), 0.12, "bronze")
        ellipsoid(m, (0.0, 0.0, -1.0), (0.6, 0.6, 0.25), "bronze", tone=0.3)
        ellipsoid(m, (0.0, 0.0, -2.1), (0.65, 0.65, 0.9), "lamp", tone=-0.2 + 0.15 * (frame % 2))
        ellipsoid(m, (0.0, 0.0, -3.1), (0.6, 0.6, 0.2), "bronze", tone=0.2)
        halo(m, 0.0, 0.0, -2.1, 5.0, FLAME, 0.8)
    else:
        raise KeyError(f"props: no prop {prop_id!r}")
    return m


def keys(prop_id: str) -> list[str]:
    return [f"prop/{prop_id}/f{f}" for f in range(FRAMES)] + [f"prop/{prop_id}/glow/f{f}" for f in range(FRAMES)]
