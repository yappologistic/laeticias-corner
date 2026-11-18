"""What the Roman towns' life modules share (Ostia and Portus, the Alban Mount, Brundisium): the
roles they borrow from Rome's life module by id, with the role cards those roles name, so a baker
or a neighbour behaves and reads the same in every Roman place; the time conventions; the theme.

The towns load this file by path (`regions/<layer>/life.py`), as the Ostia layout loads
`common.py`.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("worldgen_life_rome_shared", Path(__file__).resolve().parent / "life.py")
ROME = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ROME)

R = ROME.R
DENSITIES = ROME.DENSITIES
RAIN = ROME.RAIN
loop, once, per, ev, window = ROME.loop, ROME.once, ROME.per, ROME.ev, ROME.window
shelter_door, home_for = ROME.shelter_door, ROME.home_for


def borrow(*ids: str) -> list[dict]:
    """Rome's roles by id, unchanged (their routines name only kit found in every Roman town)."""
    roles = {r["id"]: r for r in ROME.roles()}
    return [copy.deepcopy(roles[i]) for i in ids]


def role_cards(roles: list[dict]) -> dict:
    """The cards the given roles name (role or idea cards), from Rome's text."""
    every = {**ROME.idea_cards("idea"), **ROME.role_cards("role")}
    return {r["card"]: every[r["card"]] for r in roles if r.get("card") in every}


def theme(beds: list[dict], zones: list[dict] = (), loops: list[dict] = (), weather_note: str = "") -> dict:
    """Rome's grading, haze and climate (the same April light along the coast and in the hills)."""
    return {
        "grading": ROME.GRADING, "haze": {"colour": [0.93, 0.91, 0.85], "strength": 0.1}, "climate": "rome",
        "weather": {"spring": {"showers": 2, "clouds": 2, "wind": 0.4, "wind_from": "west",
                               "note": weather_note or "April showers; the west wind in the afternoons"},
                    "summer": {"showers": 0, "clouds": 1, "wind": 0.35},
                    "autumn": {"showers": 3, "clouds": 3, "wind": 0.45},
                    "winter": {"showers": 3, "clouds": 4, "wind": 0.5}},
        "ambience": {"beds": beds, "zones": list(zones), "loops": list(loops)},
        "music": {"day": "music/rome/day.ogg", "night": "music/rome/night.ogg"},
        "arrive": "sfx/rome/arrive.wav",
    }
