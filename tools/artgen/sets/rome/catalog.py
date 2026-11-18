"""Write the Rome set catalog `assets/sets/rome/catalog.json` (world-tech.md §1.12, §6.3) from
the set's modules, so the contract and the models never disagree: landmarks and kit with their
footprints, layers, slots and emitters, plants, terrain with their faces, actors with their
anims, goods and the art block. `python -m sets.rome.catalog` (from tools/artgen)."""

import json
import sys

import spec
from sets.rome import landmarks
from sets.rome.entries import LAYERS, slots_entry

def landmark_items():
    out = []
    for iid, lm in landmarks.LANDMARKS.items():
        name, scale, height, layers, card = landmarks.INFO[iid]
        it = {"id": iid, "name": name, "footprint": list(lm.footprint), "layout": "rotate", "count": 4,
              "on": landmarks.ON.get(iid, "land"), "rotations": [0], "landmark": True, "scale": scale, "height": height,
              "layers": [LAYERS[c] for c in layers], "occluder": max(lm.footprint) > 2 or height > 80, "card": card}
        if lm.slots:
            it["slots"] = slots_entry(lm.slots)
        if lm.emitters:
            it["emitters"] = {n: landmarks.emitter_fx(n) for n in lm.emitters}
        out.append(it)
    return out


def build():
    from sets import rome
    cat = {"version": 1, "set": "rome"}
    extra = getattr(rome, "CATALOG", {})
    cat["terrain"] = extra.get("terrain", [])
    cat["items"] = landmark_items() + extra.get("items", [])
    cat["actors"] = extra.get("actors", [])
    cat["goods"] = extra.get("goods", [])
    cat["art"] = extra.get("art", {"edges": [], "fx": []})
    return cat


def dump(cat):
    """One catalog entry per line, like the other set catalogs: easy to diff and to read."""
    lines = ["{"]
    keys = list(cat)
    for i, k in enumerate(keys):
        v = cat[k]
        end = "," if i < len(keys) - 1 else ""
        if isinstance(v, list):
            lines.append(f' "{k}": [')
            lines += [f"  {json.dumps(e, ensure_ascii=False)}{',' if j < len(v) - 1 else ''}" for j, e in enumerate(v)]
            lines.append(f" ]{end}")
        else:
            lines.append(f' "{k}": {json.dumps(v, ensure_ascii=False)}{end}')
    return "\n".join(lines + ["}"]) + "\n"


def main():
    path = spec.ROOT / "assets" / "sets" / "rome" / "catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(build()))
    print(f"wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
