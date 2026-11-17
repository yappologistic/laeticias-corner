"""Command line: compile layers, validate the composed world, write previews.

  python -m worldgen.build <layer>...      compile and validate those layers (base first if asked)
  python -m worldgen.build --all           the base, then every layer that has a layout
  python -m worldgen.build --check         validate the committed layers as they are
  python -m worldgen.build --preview <layer>|world
Options: --root DIR (project root), --out DIR (world data; default <root>/assets/world),
         --reports DIR (default <root>/out/worldgen), --no-write (validate only).

A layer compiles against the committed files of every other layer, so builders working on
different layers never wait on each other. Exit status 1 when any error was found.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import resource
import sys
import time
from pathlib import Path

from PIL import ImageDraw

from plan import world_plan as P

from . import base as base_mod
from . import compiler, compose, preview, validate
from .catalog import Atlas, Catalog
from .coords import COLS, ROWS
from .dsl import Issue, Layout
from .graph import Graph, read_graph, write_graph
from .shapes import Rect
from .layer import grid_to_plan, plan_to_grid, read_lcw, write_lcw

HERE = Path(__file__).resolve().parent.parent  # tools/worldgen


class Builder:
    def __init__(self, root: Path, out: Path | None = None, reports: Path | None = None,
                 write: bool = True):
        self.root = Path(root).resolve()
        self.out = Path(out) if out else self.root / "assets/world"
        self.reports = Path(reports) if reports else self.root / "out/worldgen"
        self.write = write
        self.cat = Catalog(self.root)
        self.atlas = Atlas(self.root)
        self.layers: dict = {}   # name -> PlanLayer (committed or freshly built)
        self.graphs: dict[str, Graph] = {}
        self.layouts: dict[str, Layout] = {}
        self.extra: dict[str, list[Issue]] = {}
        self.stats: dict[str, dict] = {}
        self.order = [n for n, _, _ in P.LAYERS]

    # -- files ------------------------------------------------------------------------------

    def footprint(self, iid: str, variant: int):
        d = self.cat.items.get(iid)
        if d is None:
            return (1, 1)
        fx, fy = d.footprint_k(variant)
        return (fy, fx)

    def load_committed(self) -> None:
        for name in self.order:
            if name in self.layers:
                continue
            f = self.out / "layers" / f"{name}.lcw"
            if f.exists():
                self.layers[name] = grid_to_plan(read_lcw(f.read_bytes(), (ROWS, COLS)),
                                                 self.footprint)
                gf = self.out / "layers" / f"{name}.graph.json"
                if gf.exists():
                    self.graphs[name] = read_graph(gf.read_text())

    def write_layer(self, name: str) -> dict:
        pl = self.layers[name]
        data = write_lcw(plan_to_grid(pl, self.footprint))
        gtext = write_graph(self.graphs[name])
        sizes = {"lcw": len(data), "graph": len(gtext.encode())}
        if self.write:
            d = self.out / "layers"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{name}.lcw").write_bytes(data)
            (d / f"{name}.graph.json").write_text(gtext)
            self.write_world_json()
        return sizes

    def world_json(self) -> str:
        doc = {
            "version": 1,
            "grid": [ROWS, COLS],
            "chunk": P.CHUNK,
            "home": {"origin": [P.HOME["origin_plan"][1],
                                COLS - P.HOME["origin_plan"][0] - P.HOME["size"][0]],
                     "size": list(P.HOME["size"]), "level": P.HOME["level"],
                     "region": P.HOME["region"]},
            "layers": [{"id": n, "file": f"layers/{n}.lcw", "graph": f"layers/{n}.graph.json"}
                       for n in self.order],
            "regions": [{"id": rid, "set": v[1], "kind": v[0], "time": v[2],
                         "life": f"regions/{rid}.json"} for rid, v in P.REGIONS.items()],
            "markers": [{"region": rid, "at": [r, COLS - 1 - c], "icon": icon}
                        for rid, (c, r), icon in P.MARKERS],
        }
        lines = ["{"]
        keys = list(doc)
        for i, k in enumerate(keys):
            v = doc[k]
            comma = "," if i + 1 < len(keys) else ""
            if isinstance(v, list) and v and isinstance(v[0], dict):
                lines.append(f'  "{k}": [')
                for j, e in enumerate(v):
                    lines.append("    " + json.dumps(e, ensure_ascii=False) +
                                 ("," if j + 1 < len(v) else ""))
                lines.append("  ]" + comma)
            else:
                lines.append(f'  "{k}": ' + json.dumps(v, ensure_ascii=False) + comma)
        lines.append("}")
        return "\n".join(lines) + "\n"

    def write_world_json(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "world.json").write_text(self.world_json())

    # -- building ---------------------------------------------------------------------------

    def composed(self, upto: str | None = None) -> compose.World:
        """Compose the known layers in order (stopping before `upto` when given)."""
        seq = []
        srcs = {}
        for n in self.order:
            if n == upto:
                break
            if n in self.layers:
                seq.append((n, self.layers[n]))
                if n in self.layouts:
                    srcs[n] = [p.src for p in self.layouts[n].items if not p.removed]
        return compose.compose(seq, srcs)

    def build_base(self) -> None:
        t = time.time()
        L, g, st = base_mod.build_base(self.cat)
        L.views = {k: Rect(*v) for k, v in P.BASE_VIEWS.items()}
        pl, issues = compiler.compile_layer(L)
        self.layers["base"], self.graphs["base"], self.layouts["base"] = pl, g, L
        self.extra["base"] = issues + [Issue("V5", "error", "base", f"route failed: {f}")
                                       for f in st.get("route_failures", [])]
        st["compile_s"] = round(time.time() - t, 2)
        self.stats["base"] = st

    def layout_path(self, name: str) -> Path:
        return HERE / "regions" / name / "layout.py"

    def build_layer(self, name: str) -> None:
        t = time.time()
        spec = next((x for x in P.LAYERS if x[0] == name), None)
        if spec is None:
            raise SystemExit(f"unknown layer {name!r}; the plan's layers are {self.order}")
        _, rect, regions = spec
        region = regions[0]
        kind, set_, _time, _rr, base_level = P.REGIONS[region]
        src = self.layout_path(name)
        if not src.exists():
            raise SystemExit(f"no layout for {name!r} at {src}")
        L = Layout(layer=name, region=region, set=set_, origin=(rect[0], rect[1]),
                   size=(rect[2] - rect[0] + 1, rect[3] - rect[1] + 1), base_level=base_level,
                   catalog=self.cat, regions=regions,
                   source=str(src.relative_to(HERE)))
        L.below = self.composed(upto=name)
        mod_spec = importlib.util.spec_from_file_location(f"worldgen_region_{name}", src)
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)
        mod.build(L)
        pl, issues = compiler.compile_layer(L)
        g, gissues = compiler.derive_graph(L)
        self.layers[name], self.graphs[name], self.layouts[name] = pl, g, L
        self.extra[name] = L.issues + issues + gissues
        self.stats[name] = {"compile_s": round(time.time() - t, 2),
                            "items": len(pl.items), "nodes": len(g.nodes), "edges": len(g.edges)}

    def check(self, name: str, world: compose.World) -> list[Issue]:
        spec = next(x for x in P.LAYERS if x[0] == name)
        regions = list(P.REGIONS) if name == "base" else spec[2]
        tg = validate.Target(name, regions, self.layers[name], self.graphs.get(name, Graph(name)),
                             self.layouts.get(name), self.extra.get(name, []))
        t = time.time()
        built = set(self.layers)
        issues = validate.validate(world, self.cat, self.root, tg, self.graphs, built)
        self.stats.setdefault(name, {})["validate_s"] = round(time.time() - t, 2)
        return issues

    # -- reports and previews ---------------------------------------------------------------

    def report(self, name: str, issues: list[Issue], sizes: dict | None) -> Path:
        d = self.reports / name
        d.mkdir(parents=True, exist_ok=True)
        pl = self.layers[name]
        origin = (pl.c0, pl.r0)
        errs = [i for i in issues if i.level == "error"]
        warns = [i for i in issues if i.level != "error"]
        lines = [f"layer {name}: {len(errs)} error(s), {len(warns)} warning(s)",
                 f"stats: {json.dumps(self.stats.get(name, {}))}"]
        if sizes:
            lines.append(f"sizes: {json.dumps(sizes)}")
        lines.append("")
        for n, i in enumerate(errs + warns, 1):
            lines.append(f"{n:3}. " + i.text(origin))
        f = d / "report.txt"
        f.write_text("\n".join(lines) + "\n")
        return f

    def previews(self, name: str, world: compose.World, issues: list[Issue]) -> list[Path]:
        d = self.reports / name
        d.mkdir(parents=True, exist_ok=True)
        pl = self.layers[name]
        rect = (pl.c0, pl.r0, pl.c0 + pl.w - 1, pl.r0 + pl.h - 1)
        out = []
        px = 1 if name == "base" else 4
        m = preview.map_image(world, self.cat, self.atlas, rect, px, [self.graphs[name]],
                              items=True)
        m.save(d / "map.png")
        out.append(d / "map.png")
        dr = ImageDraw.Draw(m)
        for n, i in enumerate([i for i in issues if i.level == "error"] +
                              [i for i in issues if i.level != "error"], 1):
            if i.at is None:
                continue
            x, y = (i.at[0] - rect[0]) * px + px // 2, (i.at[1] - rect[1]) * px + px // 2
            col = (230, 30, 30) if i.level == "error" else (250, 200, 40)
            dr.ellipse((x - 6, y - 6, x + 6, y + 6), outline=col, width=2)
            dr.text((x + 7, y - 7), str(n), fill=col)
        m.save(d / "issues.png")
        out.append(d / "issues.png")
        L = self.layouts.get(name)
        if L is not None and L.views:
            pw = compose.compose([(n, self.layers[n]) for n in self.order if n in self.layers])
            if name == "corner" or any(v.contains(*P.HOME["origin_plan"]) for v in L.views.values()):
                preview.home_preview(pw, self.cat, self.root)
            iso = preview.IsoRenderer(pw, self.cat, self.atlas, self.root)
            for vname, r in L.views.items():
                img = iso.render(r.bounds(), 1, title=f"{name} · {vname}")
                f = d / f"close_{vname}.png"
                img.save(f)
                out.append(f)
            for p in L.items:
                d_ = self.cat.items.get(p.id)
                if p.removed or not d_ or not d_.landmark:
                    continue
                g = 6
                img = iso.render((p.c - g, p.r - g, p.c + p.pw - 1 + g, p.r + p.ph - 1 + g), 1,
                                 title=f"{name} · {p.name or p.id}")
                f = d / f"close_{p.name or p.id.split('.', 1)[-1]}.png"
                img.save(f)
                out.append(f)
            if iso.missing:
                (d / "missing_art.txt").write_text("\n".join(sorted(iso.missing)) + "\n")
        return out

    def preview_world(self, world: compose.World) -> list[Path]:
        d = self.reports / "world"
        d.mkdir(parents=True, exist_ok=True)
        graphs = list(self.graphs.values())
        preview.map_image(world, self.cat, self.atlas, None, 1, graphs, items=True,
                          districts=False).save(d / "world.png")
        ov = preview.overview_image(world, self.cat, self.atlas, self.root, 2, graphs)
        ov.save(d / "overview_full.png")
        target = self.out / "overview.png"
        if self.write:
            self.out.mkdir(parents=True, exist_ok=True)
            ov.quantize(colors=96, method=2, dither=0).save(target, optimize=True)
        return [d / "world.png", d / "overview_full.png", target]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="worldgen")
    ap.add_argument("layers", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preview", action="store_true",
                    help="write previews for the named layers ('world' for the overview)")
    ap.add_argument("--root", default=str(HERE.parent.parent))
    ap.add_argument("--out")
    ap.add_argument("--reports")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    b = Builder(Path(a.root), a.out, a.reports, write=not a.no_write)
    names = list(a.layers)
    want_world = "world" in names
    names = [n for n in names if n != "world"]
    if a.all:
        names = ["base"] + [n for n in b.order if n != "base" and b.layout_path(n).exists()]
    b.load_committed()
    if not a.check:
        for n in names:
            print(f"building {n} …", flush=True)
            if n == "base":
                b.build_base()
            else:
                b.build_layer(n)
        targets = names
    else:
        targets = [n for n in b.order if n in b.layers]
    if not targets and not want_world:
        ap.print_usage()
        return 2
    world = b.composed()
    failed = False
    for n in targets:
        issues = b.check(n, world)
        errs = sum(1 for i in issues if i.level == "error")
        sizes = b.write_layer(n) if (not a.check and errs == 0) else None
        f = b.report(n, issues, sizes)
        print(f"{n}: {errs} error(s), {len(issues) - errs} warning(s) -> {f}")
        for i in [i for i in issues if i.level == "error"][:12]:
            print("   " + i.text((b.layers[n].c0, b.layers[n].r0)))
        if errs:
            failed = True
            if not a.check:
                print(f"   {n} not written: fix the errors first")
        if a.preview:
            for p in b.previews(n, world, issues):
                print(f"   preview {p}")
    if want_world and a.preview:
        for p in b.preview_world(world):
            print(f"   preview {p}")
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"done in {time.time() - t0:.1f} s, peak memory {rss:.0f} MB")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
