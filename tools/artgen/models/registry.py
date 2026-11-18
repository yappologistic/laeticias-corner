"""Item id -> model builder(variant_or_mask, frame, frames) in canonical orientation, and the
one entry point for critter sprites."""

import rig
import spec
from models import critters, garden, homes, nature, resident, wildlife

_SOURCES = {
    nature: ("oak", "pine", "blossom", "bush", "berry_bush", "tall_grass", "flowers_red",
             "flowers_white", "flowers_violet", "mushrooms", "rock", "stump", "reeds", "lily_pads",
             "apple_tree", "sunflowers", "log_pile", "stepping_stones"),
    garden: ("hedge", "fence", "planter", "beehive", "scarecrow", "well", "lamp", "bench",
             "picnic_table", "campfire", "bridge", "stone_wall", "arbor", "bird_feeder", "hay_bale",
             "hammock", "fountain", "rowboat"),
    homes: ("cottage", "toolshed", "coop", "greenhouse", "barn", "windmill"),
}
ITEMS = {name: getattr(module, name) for module, names in _SOURCES.items() for name in names}


def critter_sprite(cid: str, anim: str, frame: int, frames: int, k: int):
    """Any visitor or the resident: voxel models, or hand-drawn stencils for tiny flyers."""
    kind, facing = critters.split_anim(anim)
    if cid == "laeticia":
        return critters.render_model(resident.model(kind, frame, frames, k), facing)
    build = critters.MODELS.get(cid) or wildlife.MODELS.get(cid)
    if build is None:
        return critters.flyer(cid, kind, facing, frame, k)
    return critters.render_model(build(kind, frame, frames, k), facing)


def strides(sprites) -> dict[str, float]:
    """Tiles one cycle of each walking animation covers (`critter/<id>/<anim>`), for the engine
    to play walks by distance walked; only animations the atlas has (`strides.py` does the same
    for the sets). Swims, flights and hops have none."""
    def two(reach):     # two feet, each on the ground half the cycle
        return 4 * reach * critters.S

    def four(reach):    # four feet in a four-beat walk
        return 2 * reach / rig.BEAST_DUTY * critters.S
    units = {"laeticia/move": 4 * resident.STEP, "laeticia/carry": 4 * resident.STEP,
             "laeticia/umbrella": 4 * resident.STEP, "hen/move": two(critters.HEN_REACH),
             "duck/waddle": two(critters.DUCK_REACH), "cat/move": four(critters.CAT_REACH),
             "fox/move": four(wildlife.FOX_REACH), "deer/move": four(wildlife.DEER_REACH),
             "heron/move": two(wildlife.HERON_REACH), "hedgehog/move": four(wildlife.HEDGEHOG_REACH)}
    return {f"critter/{a}": round(u / spec.DESIGN_TILE, 3) for a, u in units.items()
            if f"critter/{a}_front/f0" in sprites}
