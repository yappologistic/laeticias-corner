"""The people of Pārsa as dress data on the shared rig (rig.py), following persepolis.md §6.2
(the dress reference, row by row), §3.6 (walker kinds), §4 (named figures) and §6.6–6.7 (the
delegations of the Apadāna reliefs). Women do not appear on the reliefs; their dress is the
bible's reconstruction (weak evidence). Persian men are never clean-shaven, swords are the short
straight akinakes, no veil ever covers a woman's face."""

from dataclasses import replace

from rig import Dress, carry_table, person_sprite

D = Dress

# ---- the two court costumes ----
PERSIAN = D(garment="court_robe", head="fluted_cap", head_mat="wool", jewels=("torque", "bracelets", "earrings"),
            feet="shoes")
MEDE = D(garment="tunic", trousers="wool", coat="cinnabar", belt="gold", head="round_cap", head_mat="wool",
         feet="boots", worn=("akinakes",), jewels=("torque", "earrings"))
WORKER = D(garment="tunic", colour="wool", belt="leather", beard="short", head="felt_cap", head_mat="felt",
           feet="bare", hair_style="short")
WOMAN = D(body="woman", beard="none", hair_style="braid", garment="long_tunic", colour="wool", belt="cinnabar",
          head="headcloth", head_mat="linen", feet="bare", jewels=("necklace",))
CHILD = D(body="child", beard="none", hair_style="short", garment="tunic", colour="linen", feet="bare",
          jewels=("amulet",))

WALKERS = {
    "noble": [replace(PERSIAN, colour=c, trim=t, head_mat=h, hand_r=l) for c, t, h, l in (
        ("purple", "gold", "wool", "lotus"), ("cinnabar", "saffron", "felt", None),
        ("lapis", "gold", "saffron", "lotus"), ("saffron", "cinnabar", "wool", None))],
    "usher": [replace(MEDE, colour=c, trousers=t, coat=co, hand_l="staff") for c, t, co in (
        ("lapis", "saffron", "cinnabar"), ("cinnabar", "lapis", "purple"), ("malachite", "cinnabar", "lapis"),
        ("saffron", "purple", "cinnabar"))],
    # The guard's robes patterned with rosettes or squares on blue or yellow (the Susa bricks).
    "guard_spear": [replace(PERSIAN, colour=c, pattern=p, pattern_mat=pm, trim=t, head=h, head_mat=hm,
                            hand_l="spear", worn=("quiver", "bow_back"), jewels=("earrings", "bracelets"))
                    for c, p, pm, t, h, hm in (
        ("eblue", "dots", "saffron", "saffron", "fillet", "gold"), ("lapis", "squares", "white_paint", "white_paint",
                                                                   "fluted_cap", "wool"),
        ("saffron", "dots", "cinnabar", "cinnabar", "fillet", "gold"))],
    "guard_mede": [replace(MEDE, colour=c, trousers=t, coat=co, head=h, head_mat=hm, hand_l="spear",
                           worn=("gorytos", "akinakes")) for c, t, co, h, hm in (
        ("lapis", "wool", "cinnabar", "round_cap", "wool"), ("cinnabar", "saffron", "lapis", "hood", "felt"),
        ("malachite", "wool", "purple", "round_cap", "cream"))],
    "archer": [replace(MEDE, colour=c, coat=None, head="hood", head_mat=hm, hand_l="bow", worn=("quiver",))
               for c, hm in (("lapis", "felt"), ("cinnabar", "wool"), ("saffron", "felt"))],
    "cavalryman": [replace(MEDE, colour=c, coat=None, head="hood", head_mat="felt", worn=("gorytos",), mount="horse",
                           hand_l="lance") for c in ("lapis", "cinnabar")],
    "elamite": [D(garment="cloak_long", colour=c, pattern="fringe", trim=t, head="headband", head_mat="gold",
                  hair_style="curly", feet="shoes") for c, t in (("saffron", "cinnabar"), ("malachite", "saffron"))],
    "scribe": [replace(MEDE, colour=c, coat=None, trousers=t, worn=("seal_cord",), hand_l="tablet", hand_r="stylus")
               for c, t in (("wool", "felt"), ("eblue", "wool"), ("linen", "lapis"))],
    "mason": [replace(WORKER, colour=c, hand_r="mallet", hand_l="chisel") for c in ("wool", "linen", "felt")],
    "labourer": [replace(WORKER, colour=c, head=h) for c, h in (("wool", "felt_cap"), ("felt", "none"),
                                                                 ("linen", "felt_cap"), ("mudbrick", "none"))],
    "craftsman": [replace(WORKER, colour=c, trousers=t, hand_r="hammer") for c, t in (
        ("wool", None), ("linen", "felt"), ("felt", None), ("eblue", "wool"))],
    "woman_worker": [replace(WOMAN, colour=c, shawl=s, hold=h, hand_l=j) for c, s, h, j in (
        ("wool", "mudbrick", None, None), ("linen", "felt", "shoulder", "jar"), ("mudbrick", "wool", None, "spindle"),
        ("felt", "linen", "shoulder", "jar"))],
    "overseer_woman": [replace(WOMAN, colour=c, shawl=s, veil=v, head="headcloth", head_mat="cream", feet="shoes",
                               jewels=("necklace", "earrings")) for c, s, v in (
        ("cinnabar", "saffron", "linen"), ("lapis", "cream", "cream"))],
    "child": [CHILD, replace(CHILD, colour="wool"),
              replace(CHILD, hair_style="braid", garment="long_tunic", colour="linen"),
              replace(CHILD, hair_style="braid", garment="long_tunic", colour="mudbrick")],
    "gardener": [replace(WORKER, colour=c, hand_r="spade", hand_l=None) for c in ("linen", "wool", "felt")],
    "farmer": [replace(WORKER, colour=c, cape=cp, hand_r="hoe") for c, cp in (
        ("wool", None), ("felt", "felt"), ("linen", None), ("mudbrick", "wool"))],
    "shepherd": [replace(WORKER, colour=c, cape="felt", hand_l="crook") for c in ("wool", "linen")],
    "groom": [replace(MEDE, colour=c, coat=None, head="hood", head_mat="felt", worn=()) for c in ("felt", "wool", "lapis")],
    "caravan_driver": [replace(WORKER, colour=c, cape="felt", head="hood", head_mat=h, hand_l="staff", feet="shoes")
                       for c, h in (("wool", "linen"), ("felt", "wool"))],
    "courier": [replace(MEDE, colour="cinnabar", coat=None, head="hood", head_mat="felt", worn=("gorytos",),
                        mount="horse", hand_r="scroll")],
    # The magus: Median dress in plain light colours, the hood drawn over the mouth, the twig bundle.
    "magus": [replace(MEDE, colour=c, coat=co, trousers="wool", head="hood_mouth", head_mat="white_paint", belt=None,
                      worn=(), jewels=(), hand_l="barsom") for c, co in (("linen", "white_paint"), ("cream", "linen"))],
    # Servants climb the Hadiš stair in Median dress, hoods over the mouth, with dishes, skins, kids.
    "servant": [replace(MEDE, colour=c, coat=None, head="hood_mouth", head_mat=hm, worn=(), jewels=(), hold="front",
                        hand_l=g) for c, hm, g in (("wool", "linen", "dish"), ("felt", "wool", "wineskin"),
                                                    ("lapis", "cream", "kid_goat"))],
    "musician": [replace(WOMAN, colour="cinnabar", shawl="saffron", veil="linen", head="headcloth", head_mat="cream",
                         feet="shoes", hand_l="harp"),
                 replace(MEDE, colour="malachite", coat=None, worn=(), hand_l="pipes"),
                 replace(WOMAN, colour="lapis", shawl="cream", feet="shoes", hand_l="drum")],
    "parasol_bearer": [replace(PERSIAN, colour="saffron", trim="cinnabar", beard="none", head="fillet", head_mat="gold",
                               hand_l="parasol")],
    "storyteller": [replace(WORKER, body="elder", garment="long_tunic", colour="wool", cape="felt", hair="snow",
                            beard="full", hand_l="staff", feet="shoes")],
}

# ---- the delegations of the Apadāna stairs (persepolis.md §6.2, in the order of the relief) ----
RIDER = replace(MEDE, coat=None, worn=(), jewels=())
_g = lambda **kw: kw
DELEGATIONS = {
    "medes": (replace(MEDE, colour="lapis", coat="cinnabar"),
              [_g(hold="front", hand_l="pitcher"), _g(hold="front", hand_l="garment", pattern_mat="purple")]),
    "elamites": (D(garment="cloak_long", colour="saffron", trim="cinnabar", hair_style="curly", head="wreath",
                   head_mat="malachite", feet="shoes", worn=("akinakes",)),
                 [_g(hand_l="bow"), _g(hold="front", hand_l="cub")]),
    "armenians": (replace(RIDER, colour="cinnabar", head="hood", head_mat="felt"),
                  [_g(hold="front", hand_l="amphora"), _g(hold="lead")]),
    "parthians": (replace(RIDER, colour="malachite", head="hood_mouth", head_mat="wool"),
                  [_g(hold="front", hand_l="bowl"), _g(hold="lead", cape="saffron")]),
    "babylonians": (D(garment="long_tunic", colour="lapis", pattern="fringe", trim="saffron", head="conical_tassel",
                      head_mat="cinnabar", head_trim="saffron", feet="shoes"),
                    [_g(hold="front", hand_l="bowl"), _g(hold="front", hand_l="garment", pattern_mat="cinnabar")]),
    "lydians": (D(garment="striped_robe", colour="cinnabar", pattern_mat="cream", head="tall_cone", head_mat="saffron",
                  feet="pointed"),
                [_g(hold="front", hand_l="armlets"), _g(hold="front", hand_l="phial")]),
    "arians": (replace(RIDER, colour="wool", cape="felt", head="hood", head_mat="linen"),
               [_g(hold="front", hand_l="bowl"), _g(hold="lead")]),
    "syrians": (D(garment="long_tunic", colour="eblue", belt="cinnabar", head="headband", head_mat="cinnabar",
                  feet="shoes"),
                [_g(hold="front", hand_l="ingot"), _g(hold="front", hand_l="garment", pattern_mat="saffron")]),
    "cappadocians": (replace(RIDER, colour="saffron", cape="cinnabar", head="hood", head_mat="wool", feet="shoes"),
                     [_g(hold="front", hand_l="garment", pattern_mat="lapis"), _g(hold="lead")]),
    "saka": (replace(RIDER, colour="malachite", trousers="cinnabar", head="pointed_hood", head_mat="saffron",
                     worn=("gorytos", "akinakes")),
             [_g(hold="front", hand_l="rings"), _g(hold="front", hand_l="garment", pattern_mat="malachite")]),
    "egyptians": (D(garment="kilt", colour="linen", shawl="linen", beard="none", hair_style="short", feet="bare",
                    skin="skin_olive"),
                  [_g(hold="front", hand_l="cloth"), _g(hold="front", hand_l="bowl")]),
    "ionians": (D(garment="striped_robe", colour="lapis", pattern_mat="linen", hair_style="curly", feet="shoes"),
                [_g(hold="front", hand_l="cup"), _g(hold="front", hand_l="cloth")]),
    "bactrians": (replace(RIDER, colour="saffron", trousers="lapis", head="wreath", head_mat="malachite",
                          hair_style="knot", jewels=("earrings",)),
                  [_g(hold="front", hand_l="bowl"), _g(hold="lead")]),
    "gandharans": (D(garment="sleeveless", colour="wool", cape="cinnabar", feet="bare"),
                   [_g(hand_l="lance", hand_r="shield_round"), _g(hold="lead")]),
    "arachosians": (replace(RIDER, colour="cinnabar", trousers="wool", head="wreath", head_mat="saffron",
                            head_trim="cinnabar", beard="none", jewels=("earrings",)),
                    [_g(hold="front", hand_l="bowl"), _g(hold="lead")]),
    "sagartians": (replace(RIDER, colour="felt", head="hood_mouth", head_mat="wool", beard="none"),
                   [_g(hold="front", hand_l="garment", pattern_mat="saffron"), _g(hold="lead")]),
    "sogdians": (replace(RIDER, colour="eblue", head="tight_cap", head_mat="felt"),
                 [_g(hand_l="axes"), _g(hold="front", hand_l="rings")]),
    "indians": (D(garment="wrap", colour="linen", hair_style="tied", feet="bare", skin="skin_dark"),
                [_g(hold="pole"), _g(hand_l="axe")]),
    "thracians": (D(garment="chiton", colour="cinnabar", head="felt_cap", head_mat="felt", feet="boots",
                    hair_style="short"),
                  [_g(hand_l="spear", hand_r="shield_round"), _g(hold="lead")]),
    "arabs": (D(garment="long_tunic", colour="wool", pattern="fringe", trim="cinnabar", feet="shoes"),
              [_g(hold="lead"), _g(hold="front", hand_l="garment", pattern_mat="wool")]),
    "carians": (D(garment="striped_robe", colour="saffron", pattern_mat="lapis", head="wreath", head_mat="malachite",
                  feet="shoes"),
                [_g(hand_l="spear", hand_r="shield_round"), _g(hold="lead")]),
    "libyans": (D(garment="tunic", colour="linen", cape="felt", feet="bare", hair_style="short"),
                [_g(hold="lead"), _g(hold="front", hand_l="bowl")]),
    "kushites": (D(garment="wrap", colour="white_paint", hair_style="curly", beard="short", feet="bare",
                   skin="skin_dark"),
                 [_g(hold="front", hand_l="tusk"), _g(hold="front", hand_l="bowl")]),
}
for name, (look, bearers) in DELEGATIONS.items():
    WALKERS[f"del_{name}_lead"] = [look]
    WALKERS[f"del_{name}_bearer"] = [replace(look, **b) for b in bearers]

# ---- named figures (persepolis.md §4) ----
KING = D(body="king", garment="royal_robe", colour="purple", trim="gold", beard="square", head="crown", head_mat="gold",
         jewels=("torque", "bracelets", "earrings"), hand_l="staff", hand_r="lotus", feet="shoes")
ROYAL_WOMAN = D(body="woman", beard="none", hair_style="braid", garment="long_tunic", colour="purple", trim="gold",
                pattern="dots", pattern_mat="saffron", head="veil_crown", head_mat="cream", veil="cream",
                jewels=("collar", "earrings", "bracelets"), feet="shoes")
FIGURES = {
    "xerxes": KING,
    "amestris": ROYAL_WOMAN,
    "artaxerxes": D(body="child", garment="court_robe", colour="purple", trim="gold", beard="none", head="fillet",
                    head_mat="gold", mount="pony", hand_l="bow", feet="shoes"),
    "maus": replace(MEDE, colour="eblue", coat="lapis", worn=("seal_cord", "akinakes"), hand_l="tablet",
                    hand_r="seal"),
    "artemisia": D(body="woman", beard="none", hair_style="braid", garment="striped_robe", colour="saffron",
                   pattern_mat="lapis", cape="cinnabar", head="wreath", head_mat="gold", feet="shoes",
                   jewels=("earrings", "necklace")),
    "cyrus": D(garment="cloak_long", colour="saffron", trim="cinnabar", pattern="fringe", head="fillet", head_mat="gold",
               beard="full", feet="shoes"),
    "darius": replace(KING, hair="snow"),
    "atossa": replace(ROYAL_WOMAN, body="elder", colour="cinnabar", hair="snow", hand_l="staff"),
    "irtashduna": replace(ROYAL_WOMAN, colour="lapis", hand_l="tablet", hand_r="seal"),
    "parnakka": replace(MEDE, colour="saffron", coat="purple", worn=("seal_cord", "akinakes"), hand_l="tablet"),
    "mithradata": replace(MEDE, colour="linen", coat=None, trousers="lapis", worn=("seal_cord",), hand_l="scroll",
                          hand_r="stylus"),
    "rtakama": replace(WOMAN, colour="cinnabar", shawl="saffron", veil="cream", head_mat="cream", feet="shoes",
                       jewels=("necklace", "earrings")),
    "hermon": replace(WORKER, garment="chiton", colour="linen", head="none", hair_style="curly", hand_r="mallet",
                      hand_l="chisel"),
    "bel_iddin": replace(WORKER, colour="wool", head="headband", head_mat="cinnabar", hand_l="brick_mould"),
    "pediese": D(garment="kilt", colour="white_paint", beard="none", hair_style="short", feet="bare",
                 jewels=("collar",), hand_r="hammer"),
    "manes": replace(WORKER, colour="saffron", head="felt_cap", head_mat="cinnabar", hand_r="adze"),
    "farnadata": replace(MEDE, colour="malachite", coat="cinnabar", hand_l="tablet"),
    "irdumartiya": replace(WORKER, colour="felt", cape="wool", hand_r="hoe"),
    "dadush": replace(CHILD, colour="wool"),
    "udusana": replace(CHILD, hair_style="braid", garment="long_tunic", colour="linen"),
}

# Tools change with the work being done (the dress carries the walking look).
WORK_PROPS = {
    "gardener": {"pour": dict(hand_l="jar", hand_r=None), "work_high": dict(hand_r="pruning_knife")},
    "farmer": {"haul": dict(hand_r=None)},
    "magus": {"pour": dict(hand_l="ladle", hand_r=None)},
    "woman_worker": {"throw": dict(hold=None, hand_l=None), "stir": dict(hold=None, hand_l=None),
                     "carry": dict(hold=None, hand_l=None), "carry_idle": dict(hold=None, hand_l=None)},
    "labourer": {"carry": dict(), "carry_idle": dict()},
    "scribe": {"carry": dict(hand_l=None, hand_r=None), "carry_idle": dict(hand_l=None, hand_r=None)},
    "mason": {"carry": dict(hand_l=None, hand_r=None), "carry_idle": dict(hand_l=None, hand_r=None)},
    "servant": {"carry": dict(hold=None, hand_l=None), "carry_idle": dict(hold=None, hand_l=None)},
    "xerxes": {"sit": dict(hand_l="staff")},
}


def dress_for(kind: str, variant) -> Dress:
    name = kind.split(".", 1)[1]
    if name in FIGURES:
        return FIGURES[name]
    return WALKERS[name][variant or 0]


def _posed(kind, variant, anim):
    d = dress_for(kind, variant)
    name = kind.split(".", 1)[1]
    return replace(d, **WORK_PROPS.get(name, {}).get(anim, {}))


def sprite(kind, variant, anim, facing, frame, k, frames=None):
    return person_sprite(_posed(kind, variant, anim), anim, facing, frame, k, frames)


def carry_at(kind, k):
    return carry_table(lambda anim: _posed(kind, 0, anim), k)
