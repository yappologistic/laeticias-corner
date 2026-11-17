"""Item id -> model builder(variant_or_mask, frame, frames) in canonical orientation, and the
one entry point for critter sprites."""

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
