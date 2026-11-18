#!/usr/bin/env python3
"""Chains of every region with a life file, simulated by tools/worldgen's own simulator.

Runs worldgen.lifesim.simulate (four days of one-second ticks from 06:00) on each chain of the
committed region files, over the region views worldgen's checks use, and prints JSON: per chain
its errors, the per-stage statistics, the units used per day, each carrier's travel time and the
final stock of every (slot, goods) counter. `lifeinfo chains` prints the same from the engine;
the `life_chains` test compares the two. The simulator's source is used unchanged except that its
final return also hands back the counters (lifesim keeps them in a local).

Usage (repository root): tools/worldgen/.venv/bin/python tests/world_tools/life_chains.py
"""

from __future__ import annotations

import inspect
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/worldgen"))

from plan import world_plan as P  # noqa: E402
from worldgen import citylife as CL  # noqa: E402
from worldgen import lifesim  # noqa: E402
from worldgen.build import Builder  # noqa: E402


def patched_simulate():
    src = inspect.getsource(lifesim)
    old = 'return {"errors": errors, "stages": stat, "per_day": sunk_day, "travel": travel}'
    if old not in src:
        raise SystemExit("lifesim.simulate's final return changed; update life_chains.py")
    src = src.replace(old, 'return {"errors": errors, "stages": stat, "per_day": sunk_day, '
                           '"travel": travel, "count": count}')
    mod = types.ModuleType("lifesim_counted")
    mod.__dict__["__package__"] = "worldgen"
    exec(compile(src, "lifesim_counted", "exec"), mod.__dict__)  # noqa: S102
    return mod.simulate


def main() -> int:
    simulate = patched_simulate()
    b = Builder(ROOT, write=False)
    b.load_committed()
    world = b.composed()
    out = {}
    for layer, _, regs in P.LAYERS:
        for rid in regs:
            f = ROOT / "assets/regions" / f"{rid}.json"
            if not f.exists():
                continue
            doc = json.loads(f.read_text())
            if not doc.get("chains"):
                continue
            view = CL.region_view(world, b.cat, b.graphs, ROOT, rid, layer)
            roles = CL.roles_by_id(doc)
            for c in doc["chains"]:
                res = simulate(c, view, roles)
                counts = {f"{k[0]}|{k[1]}": v for k, v in sorted(res.get("count", {}).items())}
                out[f"{rid}/{c['id']}"] = {
                    "errors": res["errors"],
                    "per_day": res["per_day"],
                    "stages": [[s["work"], s["starve"], s["block"], s["done"]]
                               for s in res["stages"]],
                    "travel": [round(t, 6) for t in res.get("travel", [])],
                    "count": counts,
                }
    sys.stdout.write(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
