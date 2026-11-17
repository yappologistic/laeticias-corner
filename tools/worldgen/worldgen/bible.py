"""Landmark coordinate tables of the city files (docs/design/cities/<city>.md §2.3).

Rows look like
  | `apadana` | Apadāna with corner towers | c 60..83, r 54..77 | 24 × 24 | 7 | … |
and give, in the region's local plan coordinates, the footprint rect and the local level (a
single number, a range "0 → 6" or "7–9", or blank). Rows without a `c a..b, r a..b` rect (outlines,
roads, world rects) are skipped: only rect landmarks can be checked by position.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|")
RECT = re.compile(r"^\s*c\s*(\d+)\s*\.\.\s*(\d+)\s*,\s*r\s*(\d+)\s*\.\.\s*(\d+)\s*$")
LEVEL = re.compile(r"^\s*(\d+)\s*(?:(?:→|–|-|\.\.)\s*(\d+))?\s*$")


@dataclass
class Landmark:
    id: str
    name: str
    rect: tuple[int, int, int, int]  # local plan, inclusive
    level: tuple[int, int] | None    # (low, high); a single level has low == high
    line: int


def parse(path: Path) -> dict[str, Landmark]:
    out: dict[str, Landmark] = {}
    in_table = False
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if line.startswith("### "):
            in_table = line.startswith("### 2.3")
            continue
        if not in_table:
            continue
        m = ROW.match(line)
        if not m:
            continue
        lid, name, rect, _wh, level = (g.strip() for g in m.groups())
        r = RECT.match(rect)
        if not r:
            continue
        c0, c1, r0, r1 = (int(x) for x in r.groups())
        lv = None
        mm = LEVEL.match(level)
        if mm:
            lo = int(mm.group(1))
            lv = (lo, int(mm.group(2)) if mm.group(2) else lo)
        out[lid] = Landmark(lid, name, (c0, r0, c1, r1), lv, n)
    return out


CITY_FILES = {"rome": "rome.md", "athens": "athens.md", "parsa": "persepolis.md"}


def for_region(root: Path, region: str) -> tuple[dict[str, Landmark], str | None]:
    f = CITY_FILES.get(region)
    if not f:
        return {}, None
    p = Path(root) / "docs/design/cities" / f
    return (parse(p), f"docs/design/cities/{f}") if p.exists() else ({}, None)
