"""The `world` set: the land and sea between the cities (docs/design/sets/world.md), on one page
resident everywhere. Natural ground, water and faces in `ground`, the plants and natural props
in `plants`, the connective kit of every era in `kit`, people on the shared rig in `people`,
animals, birds and boats in `animals`, the sky, weather, effects and map markers in `sky`,
carried goods in `goods`. No landmarks: everything is kit, so every piece rotates."""

import re

from sets.world import animals, goods, ground, kit, people, plants, sky

LANDMARKS = {}
ITEMS = {**kit.ITEMS, **plants.ITEMS}
STATES = {}
FRAMES = {"world.sea": ground.FRAMES_WATER, "world.shallows": ground.FRAMES_WATER, "world.river": ground.FRAMES_WATER,
          **kit.FRAMES, **plants.FRAMES, **sky.FX_FRAMES}
# Day-only strips of two looks (world.md §6.1, decision 4: the engine grades them for night).
BACKDROP_LOOKS = {"world.bd_far_hills": (("day",), 2)}
COAST_FRAMES = 4


def extra_keys(cat):
    """Keys the world's art implies beyond the shared scheme: shore foam (a sea tile with no
    land beside it has none), the interior looks of the commonest overlays, river flow, the animated foot of the sea cliff, the nice-to-have
    faces, strips and effects, the weather sprites and the map markers."""
    art = cat.get("art", {})
    keys = [f"terrain/world.sea/foam/m{m}/f{f}" for m in range(1, 16) for f in range(ground.FRAMES_WATER)]
    for tid, n in ground.INTERIOR.items():
        frames = ground.FRAMES_WATER if tid in ground.WATER_OVERLAYS else 1
        keys += [f"terrain/{tid}/m15/v{v}/f{f}" for v in range(1, n) for f in range(frames)]
    keys += [f"terrain/world.river/flow_{d}/f{f}" for d in ("n", "e") for f in range(ground.FLOW_FRAMES)]
    keys += [f"edge/world.coast_{s}/v{n}/f{f}" for s in ("se", "sw") for n in range(4) for f in range(COAST_FRAMES)]
    for e in art.get("edges_nice", ()):
        keys += [f"edge/{e}_{side}/v{n}" for side in ("se", "sw") for n in range(4)]
        keys += [f"edge/{e}_{side}/top" for side in ("se", "sw")]
    for b in art.get("backdrops_nice", ()):
        keys += [f"backdrop/{b}/day/v{n}" for n in range(2)]
    for fxid in art.get("fx_nice", ()):
        keys += [f"fx/{fxid}/f{f}" for f in range(FRAMES.get(fxid, 6))]
    for group in ("weather", "weather_nice"):
        for kind, n in art.get(group, {}).items():
            keys += [f"weather/{kind}_v{v}" for v in range(n)]
    for group in ("markers", "markers_nice"):
        keys += [f"ui/marker_{icon}" for icon in art.get(group, ())]
    return keys


def actor_sprite(kind, variant, anim, facing, frame, k):
    if kind in animals.KINDS:
        return animals.sprite(kind, variant, anim, facing, frame, k)
    return people.sprite(kind, variant, anim, facing, frame, k)


def carry_at(kind, k):
    return people.carry_at(kind, k)


TERRAIN_KEY = re.compile(r"terrain/(world\.\w+)/(?:v(\d+)|m(\d+)/f(\d+))")


def _flat(key, k):
    if m := TERRAIN_KEY.fullmatch(key):
        tid, var, mask, frame = m.groups()
        if var is not None:
            return ground.BASES[tid](int(var), k)
        if tid in ground.WATER_OVERLAYS:
            return ground.WATER_OVERLAYS[tid](int(mask), int(frame), k)
        return ground.OVERLAYS[tid](int(mask), k)
    if m := re.fullmatch(r"terrain/(world\.\w+)/m15/v(\d+)/f(\d+)", key):
        tid, var, frame = m[1], int(m[2]), int(m[3])
        if tid in ground.WATER_OVERLAYS:
            return ground.WATER_OVERLAYS[tid](15, frame, k, var=var)
        return ground.OVERLAYS[tid](15, k, var=var)
    if m := re.fullmatch(r"terrain/world\.sea/foam/m(\d+)/f(\d+)", key):
        return ground.foam(int(m[1]), int(m[2]), k)
    if m := re.fullmatch(r"terrain/world\.river/flow_([ne])/f(\d+)", key):
        return ground.flow(m[1], int(m[2]), k)
    if m := re.fullmatch(r"edge/(world\.\w+)_(se|sw)/(?:v(\d)(?:/f(\d))?|(top))", key):
        face, side, v, f, top = m.groups()
        if face == "world.coast":
            return ground.coast_face(side, int(v or 0), k, top=bool(top), frame=None if f is None else int(f))
        return ground.FACES[face](side, int(v or 0), k, top=bool(top))
    if m := re.fullmatch(r"backdrop/(world\.\w+)/day/v(\d)", key):
        return sky.backdrop(m[1], int(m[2]), k)
    if m := re.fullmatch(r"weather/(\w+)_v(\d)", key):
        return sky.weather(m[1], int(m[2]), k)
    if m := re.fullmatch(r"ui/marker_(\w+)", key):
        return sky.marker(m[1], k)
    if m := re.fullmatch(r"fx/(world\.\w+)/f(\d+)", key):
        return sky.fx(m[1], int(m[2]), FRAMES[m[1]], k)
    if key.startswith("goods/"):
        return goods.sprite(key, k)
    raise KeyError(key)


def flat(keys, cat, k):
    return {key: _flat(key, k) for key in keys}
