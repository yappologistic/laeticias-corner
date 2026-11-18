"""The people of every road and shore (docs/design/sets/world.md §5.1) as dress data on the shared
rig (rig.py): travellers of any origin, Levantine and Ionian merchants, muleteers, fishermen,
sailors and loggers. One Mediterranean look serves every era for the working people of the
sea (world.md §11); nobody wears scallop shells, medieval hats or stirrups."""

from dataclasses import replace

from rig import Dress, carry_table, person_sprite, trade

D = Dress
TAN, OLIVE, DARK = "skin_tan", "skin_olive", "skin_dark"

WORKER = D(skin=OLIVE, hair="cedar", hair_style="short", beard="short", garment="exomis", colour="wool", feet="bare")

WALKERS = {
    "traveller": [
        # A knee tunic, a short pinned cloak, the broad travelling hat on the back, staff and bundle.
        D(skin=TAN, hair="cedar", hair_style="short", beard="short", garment="tunic", colour="ochre", belt="leather",
          cape="felt", head="petasos_back", head_mat="straw", feet="boots", feet_mat="leather", hand_l="staff"),
        # An ankle tunic, a wrapped shawl and a head cloth (the Near East).
        D(skin=OLIVE, hair="hair_black", beard="full", garment="long_tunic", colour="linen", pattern="stripes",
          pattern_mat="cinnabar", shawl="wool", head="headcloth", head_mat="cream", feet="shoes", hand_l="staff"),
        # A woman in a long tunic, her mantle drawn over the head.
        D(body="woman", skin=TAN, hair="cedar", hair_style="knot", beard="none", garment="chiton_long", colour="eblue",
          mantle="wool", mantle_head=True, feet="shoes", jewels=("earrings",)),
    ],
    "merchant": [
        # Phoenician or Levantine: a long fringed tunic with a sash, a conical cap, a beard.
        D(skin=OLIVE, hair="hair_black", beard="curled", garment="long_tunic", colour="purple", pattern="fringe",
          pattern_mat="saffron", belt="cinnabar", head="tall_cone", head_mat="cream", feet="shoes",
          jewels=("bracelets",), hand_l="seal"),
        # An Ionian Greek in chiton and himation.
        D(skin=TAN, hair="cedar", hair_style="curly", beard="full", garment="chiton_long", colour="linen", mantle="eblue",
          feet="shoes", hand_l="wax_tablet"),
    ],
    "muleteer": [
        D(skin=OLIVE, hair="cedar", hair_style="short", beard="short", garment="tunic", colour="wool", belt="leather",
          head="felt_cap", head_mat="felt", feet="bare", hand_l="staff"),
        D(skin=TAN, hair="hair_black", hair_style="short", beard="full", garment="tunic", colour="mudbrick",
          belt="wool", head="round_cap", head_mat="ochre", feet="shoes", hand_l="whip"),
    ],
    "fisher": [
        replace(WORKER, head="felt_cap", head_mat="felt", hand_l="net"),
        replace(WORKER, garment="tunic", colour="linen", belt="straw", beard="none", skin=TAN, hand_l="basket"),
    ],
    "sailor": [
        replace(WORKER, head="felt_cap", head_mat="felt", hand_l="rope"),
        replace(WORKER, colour="felt", skin=DARK, beard="none", head="headcloth", head_mat="cinnabar", hand_l="rope"),
    ],
    # The corner's country people, of no one age: a man with his hoe and broad straw hat, a woman
    # with her head cloth, both barefoot in undyed wool.
    "farmer": [
        replace(WORKER, garment="tunic", head="petasos", head_mat="straw", hand_r="hoe", skin=TAN),
        D(body="woman", skin=OLIVE, hair="cedar", hair_style="knot", beard="none", garment="long_tunic", colour="wool",
          belt="wool", head="headcloth", head_mat="linen", feet="bare", hand_r="sickle"),
    ],
    "logger": [
        replace(WORKER, garment="tunic", colour="felt", belt="leather", hand_r="axe", feet="boots"),
        replace(WORKER, garment="tunic", colour="ochre", belt="leather", head="felt_cap", head_mat="wool", hand_r="axe",
                feet="boots", skin=TAN),
    ],
}

# Each trade its own colour, so a mason reads apart from a gardener at 1x.
TRADES = {"fisher": "eblue", "sailor": "lapis", "logger": "malachite", "muleteer": "ochre", "farmer": "saffron"}
for _kind, _accent in TRADES.items():
    WALKERS[_kind] = trade(WALKERS[_kind], _accent)

# What the hands hold changes with the work being done.
WORK_PROPS = {
    "traveller": {"carry": dict(hand_l=None), "carry_idle": dict(hand_l=None), "sit": dict(hand_l=None)},
    "merchant": {"carry": dict(hand_l=None), "carry_idle": dict(hand_l=None), "serve": dict(hand_l="cup")},
    "muleteer": {"carry": dict(hand_l=None)},
    "fisher": {"work_low": dict(hand_l="net_cast"), "haul": dict(hand_l="rope"), "carry": dict(hand_l=None),
               "carry_idle": dict(hand_l=None), "sit": dict(hand_l="net")},
    "sailor": {"carry": dict(hand_l=None), "carry_idle": dict(hand_l=None)},
    "logger": {"haul": dict(hand_l="rope", hand_r=None)},
    "farmer": {"carry": dict(hand_r=None), "carry_idle": dict(hand_r=None)},
}


def _posed(kind, variant, anim):
    name = kind.split(".", 1)[1]
    d = WALKERS[name][variant or 0]
    return replace(d, **WORK_PROPS.get(name, {}).get(anim, {}))


def sprite(kind, variant, anim, facing, frame, k):
    return person_sprite(_posed(kind, variant, anim), anim, facing, frame, k)


def carry_at(kind, k):
    return carry_table(lambda anim: _posed(kind, 0, anim), k)
