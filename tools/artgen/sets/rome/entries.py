"""Catalog entries shared by the landmark, kit and plant tables (world-tech.md §1.12)."""

from sets.rome.landmarks import emitter_fx

LAYERS = {"B": "base", "S": "shadow", "G": "glow"}
SLOT_KIND = {"door": "door", "sell": "work", "work": "work", "fill": "use", "pray": "use", "mooring": "mooring",
             "seat": "seat"}


def kit_entry(iid, name, footprint, layout, count, layers, height, fps, item):
    """A kit or plant entry of the set catalog (world-tech.md §1.12)."""
    it = {"id": iid, "name": name, "footprint": list(footprint), "layout": layout, "count": count, "on": "land",
          "layers": [LAYERS[c] for c in layers], "height": height}
    if fps:
        it["fps"] = fps
    if item.slots:
        it["slots"] = slots_entry(item.slots)
    if item.emitters:
        it["emitters"] = {n: emitter_fx(n) for n in item.emitters}
    return it


def slots_entry(slots):
    return [{"id": sid, "kind": SLOT_KIND.get(sid, "stand"), "cap": len(spots)} for sid, spots in slots.items()]
