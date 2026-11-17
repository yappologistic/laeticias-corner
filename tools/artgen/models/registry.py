"""Item id -> model builder(variant_or_mask, frame, frames) in canonical orientation."""

from models import garden, homes, nature

_SOURCES = {
    nature: ("oak", "pine", "blossom", "bush", "berry_bush", "tall_grass", "flowers_red",
             "flowers_white", "flowers_violet", "mushrooms", "rock", "stump", "reeds", "lily_pads"),
    garden: ("hedge", "fence", "planter", "beehive", "scarecrow", "well", "lamp", "bench",
             "picnic_table", "campfire", "bridge"),
    homes: ("cottage", "toolshed", "coop", "greenhouse", "barn", "windmill"),
}
ITEMS = {name: getattr(module, name) for module, names in _SOURCES.items() for name in names}
