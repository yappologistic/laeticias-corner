"""Shared fixtures: a tiny world in the corner's rect, built from code, never from committed data."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from worldgen import compiler, compose
from worldgen.catalog import Atlas, Catalog
from worldgen.dsl import Layout
from worldgen.validate import Target, validate

ROOT = Path(__file__).resolve().parents[3]
RECT = (10, 10, 41, 33)  # a 32 x 24 test layer inside the corner region


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return Catalog(ROOT)


@lru_cache(maxsize=1)
def atlas() -> Atlas:
    return Atlas(ROOT)


def ground_layout(name: str = "under", rect=(0, 0, 63, 47)) -> Layout:
    """A flat grass base under the test layer (layer 'base' of the fixture world)."""
    L = Layout(layer=name, region="corner", set="home", origin=rect[:2],
               size=(rect[2] - rect[0] + 1, rect[3] - rect[1] + 1), base_level=2,
               catalog=catalog(), regions=["corner"])
    L.fill("grass", district="meadows")
    return L


def layout(rect=RECT) -> Layout:
    L = Layout(layer="corner", region="corner", set="home", origin=rect[:2],
               size=(rect[2] - rect[0] + 1, rect[3] - rect[1] + 1), base_level=2,
               catalog=catalog(), regions=["corner"], source="test")
    return L


def check(L: Layout, under: Layout | None = None, root: Path = ROOT):
    """Compile, compose over `under` (flat grass by default) and validate; returns issues."""
    under = under or ground_layout()
    upl, _ = compiler.compile_layer(under)
    pl, issues = compiler.compile_layer(L)
    g, gissues = compiler.derive_graph(L)
    world = compose.compose([("base", upl), (L.layer, pl)],
                            {L.layer: [p.src for p in L.items if not p.removed]})
    tg = Target(L.layer, L.regions, pl, g, L, L.issues + issues + gissues)
    return validate(world, catalog(), root, tg, {L.layer: g}, {L.layer})


def codes(issues, level="error"):
    return sorted({i.code for i in issues if i.level == level})
