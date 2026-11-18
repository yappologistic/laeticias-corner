"""A deterministic simulator of the chain rules (living-world §3.3), for checking chains offline.

One second per tick over a simulated week (four game days of 720 s; the clock starts at 06:00).
The first day fills the empty chain (`warmup` days for a chain slowed by its month); the shares
and the daily counts are judged on the others.
A chain runs only inside its `hours`. Every slot holds at most three units; a source makes one
unit per `period` while its slot has room; a transform turns one input into one output in `dur`
seconds (default half a period); a carrier takes up to `units` (default 1) from one slot to
another along the path graph at its walking speed and walks back (`workers` carriers may share a
stage; a transform may put its output
in another slot of its workplace, `out`); a sink uses one unit every
`dur` seconds (default a third of a period). The result says how often each stage starved
(waited for input) or was blocked (its output full), how many units reached the sink each day,
and what is wrong with the chain, if anything.
"""

from __future__ import annotations

DAY = 720
CAP = 3
STARVE = 0.85      # a workplace may wait for input at most this share of its working time
BLOCK = 0.65       # a source may stand full at most this share of its working time
SPEED = {"walk": 0.9, "cart": 0.6}


def _hour(t: int) -> float:
    return (6 + 24 * (t % DAY) / DAY) % 24


def _active(hours, h: float) -> bool:
    from .citylife import in_hours
    return in_hours(hours, h)


def _node(ref: str, near: str | None, view) -> tuple[str | None, str]:
    """(graph node, description) of a stage's slot reference."""
    if ref.startswith(("node:", "portal:")):
        n = ref.split(":", 1)[1]
        return (n if n in view.nodes else None), ref
    item, _, slot = ref.rpartition(".")
    insts = [i for i in view.of_item(item) if i.nodes.get(slot)]
    if not insts:
        return None, ref
    if near and near in view.nodes:
        dist = view.distances(near)
        insts.sort(key=lambda i: (dist.get(i.nodes[slot], 1 << 30), i.c, i.r))
    return insts[0].nodes[slot], ref


def simulate(chain: dict, view, roles: dict, days: int = 4, warmup: int = 1) -> dict:
    stages = chain["stages"]
    period = float(chain["period"])
    hours = chain.get("hours", ["06:00", "18:00"])
    errors: list[str] = []
    # Where the goods sit after each stage, and the graph node of every slot reference.
    loc: list[str] = []
    nodes: dict[str, str | None] = {}
    for i, s in enumerate(stages):
        if "carry" in s:
            if i > 0 and loc and s["from"] != loc[-1]:
                errors.append(f"stage {i} carries from {s['from']!r} but the goods are at "
                              f"{loc[-1]!r} (the chain is broken)")
            for k in ("from", "to"):
                nodes[s[k]] = _node(s[k], s.get("near"), view)[0]
            loc.append(s["to"])
        else:
            if i > 0 and loc and s["slot"] != loc[-1] and ("needs" in s or "sink" in s):
                errors.append(f"stage {i} works at {s['slot']!r} but the goods are at "
                              f"{loc[-1]!r} (the chain is broken)")
            nodes[s["slot"]] = _node(s["slot"], s.get("near"), view)[0]
            loc.append(s.get("out", s["slot"]))
    for ref, n in nodes.items():
        if n is None:
            errors.append(f"slot {ref!r} cannot be reached on the path graph")
    if errors:
        return {"errors": errors, "stages": [], "per_day": [0] * days}
    count: dict[tuple[str, str], int] = {}
    stat = [{"work": 0, "starve": 0, "block": 0, "done": 0} for _ in stages]
    # Every worker of every stage: a carry stage may have several carriers sharing its slots.
    run = [(i, s) for i, s in enumerate(stages)
           for _ in range(s.get("workers", 1) if "carry" in s else 1)]
    state = [{"t": 0.0, "phase": "idle", "hand": 0} for _ in run]
    travel: list[float] = []
    for s in stages:
        if "carry" in s:
            d = view.distances(nodes[s["from"]]).get(nodes[s["to"]])
            if d is None:
                errors.append(f"no path from {s['from']!r} to {s['to']!r}")
                d = 0
            kind = roles.get(s["by"], {}).get("actor", s["by"])
            mode = "cart" if any(w in kind for w in ("cart", "sledge")) else "walk"
            speed = roles.get(s["by"], {}).get("locomotion", {}).get("speed", SPEED[mode])
            travel.append(d / speed)
        else:
            travel.append(0.0)
    if errors:
        return {"errors": errors, "stages": [], "per_day": [0] * days}
    made = 0
    sunk_day = [0] * days
    for t in range(days * DAY):
        on = _active(hours, _hour(t))
        if t == DAY * warmup:   # judge the chain once it has filled
            stat = [{"work": 0, "starve": 0, "block": 0, "done": 0} for _ in stages]
        for k, (i, s) in enumerate(run):
            st, sm = state[k], stat[i]
            if "carry" in s:
                src, dst, g = (s["from"], s["carry"]), (s["to"], s["carry"]), s["carry"]
                if st["phase"] == "idle":
                    if not on:
                        continue
                    sm["work"] += 1
                    room = CAP - count.get(dst, 0)
                    if count.get(src, 0) > 0 and room > 0:
                        n = min(s.get("units", 1), count[src], room)
                        count[src] -= n
                        st.update(phase="out", t=travel[i], hand=n)
                    elif count.get(src, 0) == 0:
                        sm["starve"] += 1
                    else:
                        sm["block"] += 1
                elif st["phase"] == "out":
                    sm["work"] += 1
                    st["t"] -= 1
                    if st["t"] <= 0:
                        room = CAP - count.get(dst, 0)
                        if room >= st["hand"]:
                            count[dst] = count.get(dst, 0) + st["hand"]
                            sm["done"] += st["hand"]
                            st.update(phase="back", t=travel[i], hand=0)
                        else:
                            sm["block"] += 1
                elif st["phase"] == "back":
                    st["t"] -= 1
                    if st["t"] <= 0:
                        st["phase"] = "idle"
                continue
            if not on:
                continue
            sm["work"] += 1
            here = s["slot"]
            if "sink" in s:
                key = (here, s["sink"])
                dur = s.get("dur", period / 3)
                if count.get(key, 0) > 0:
                    st["t"] += 1
                    if st["t"] >= dur:
                        count[key] -= 1
                        st["t"] = 0
                        sm["done"] += 1
                        sunk_day[t // DAY] += 1
                else:
                    sm["starve"] += 1
            elif "needs" in s:
                inp, out = (here, s["needs"]), (s.get("out", here), s["makes"])
                dur = s.get("dur", period / 2)
                if st["phase"] == "idle":
                    if count.get(out, 0) >= CAP:
                        sm["block"] += 1
                    elif count.get(inp, 0) > 0:
                        count[inp] -= 1
                        st.update(phase="work", t=dur)
                    else:
                        sm["starve"] += 1
                else:
                    st["t"] -= 1
                    if st["t"] <= 0:
                        if count.get(out, 0) < CAP:
                            count[out] = count.get(out, 0) + 1
                            sm["done"] += 1
                            st["phase"] = "idle"
                        else:
                            sm["block"] += 1
            else:
                out = (here, s["makes"])
                if count.get(out, 0) >= CAP:
                    sm["block"] += 1
                    continue
                st["t"] += 1
                if st["t"] >= period:
                    count[out] = count.get(out, 0) + 1
                    made += 1
                    sm["done"] += 1
                    st["t"] = 0
        for k, v in count.items():
            if not 0 <= v <= CAP:
                errors.append(f"slot {k[0]!r} holds {v} {k[1]} (allowed 0..{CAP})")
                return {"errors": errors, "stages": stat, "per_day": sunk_day}
    # One unit in, one out at every transform: what was made is used, held or being worked.
    held = sum(count.values()) + sum(st["hand"] for st in state) + \
        sum(1 for (_, s), st in zip(run, state) if "needs" in s and st["phase"] == "work")
    if made != sum(sunk_day) + held:
        errors.append(f"made {made} units but used {sum(sunk_day)} and hold {held}")
    for i, (s, sm) in enumerate(zip(stages, stat)):
        w = max(1, sm["work"])
        what = s.get("by", "?")
        # A carrier or a sink waiting is masked by a believable idle (living-world §3.3 rule 4);
        # a workplace that turns goods into others must not stand idle for want of them.
        if "needs" in s and sm["starve"] / w > STARVE:
            errors.append(f"stage {i} ({what}) waits for goods {sm['starve'] / w:.0%} of its "
                          "working time (it starves)")
        if "makes" in s and "needs" not in s and sm["block"] / w > BLOCK:
            errors.append(f"stage {i} ({what}) stands full {sm['block'] / w:.0%} of its working "
                          "time (the chain downstream cannot keep up)")
        if "carry" in s and travel[i] > 3 * period:
            errors.append(f"stage {i} ({what}) walks {travel[i]:.0f} s each way, over three "
                          "periods")
    for d, n in enumerate(sunk_day):
        if d >= warmup and n < 1:
            errors.append(f"nothing reached the sink on day {d}")
            break
    return {"errors": errors, "stages": stat, "per_day": sunk_day, "travel": travel}
