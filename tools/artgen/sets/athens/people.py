"""The people of Athens in 432 as dress data on the shared rig (rig.py), following athens.md §6.2
(the dress reference, row by row and its list of common mistakes), §3.6 (walker kinds), §7.2
(the Panathenaic procession), §6.7 (visitors) and §4 (named figures). Colours are generous but
true to the evidence: undyed wool for workers and the enslaved, dyed and bordered wool and
linen for citizens and women, purple for the metics in the procession; hoplites with open
Attic and pilos helmets more than Corinthian ones, each shield its own blazon; Scythian
archers in trousers and pointed caps; nobody in a toga, nobody in Roman armour, beardless young
riders, women outdoors at fountains, markets and festivals, no veil over a face."""

from dataclasses import replace

from rig import Dress, carry_table, person_sprite
from sets.athens.animals import horse_mount

D = Dress
TAN, OLIVE, PALE = "skin_tan", "skin_olive", "skin"

MAN = D(skin=TAN, hair="cedar", hair_style="short", beard="full", garment="himation", colour="wool", feet="shoes")
WOMAN = D(body="woman", skin=TAN, hair="gloss", hair_style="knot", beard="none", garment="chiton_long", colour="linen",
          feet="shoes", jewels=("earrings",))
WORKER = D(skin=OLIVE, hair="cedar", hair_style="short", beard="short", garment="exomis", colour="wool", feet="bare")
SLAVE_W = D(body="woman", skin=OLIVE, hair="cedar", hair_style="short", beard="none", garment="long_tunic",
            colour="wool", belt="wool", feet="bare")
CHILD = D(body="child", skin=TAN, hair="cedar", hair_style="short", beard="none", garment="chiton", colour="wool",
          feet="bare", jewels=("amulet",))
HOPLITE = D(skin=TAN, hair="cedar", hair_style="short", beard="full", garment="chiton", colour="cinnabar",
            worn=("corslet", "greaves", "xiphos"), head="attic_helmet", head_mat="bronze_cast", head_trim="cinnabar",
            hand_l="dory", hand_r="aspis", pattern_mat="cinnabar", trim="gloss", feet="bare")
YOUTH = D(skin=TAN, hair="cedar", hair_style="curly", beard="none", garment="chiton", colour="ochre", cape="cinnabar",
          head="petasos_back", head_mat="straw", feet="boots", feet_mat="leather")

# kind: (name, anims, [dresses]) -- anims with their fps, as the catalog lists them.
MOVE = {"move": {"fps": 8}, "idle": {"fps": 3}}


def _a(**extra):
    return {**MOVE, **{k: {"fps": v} for k, v in extra.items()}}


WALKERS = {
    "citizen": ("Citizen in a himation", _a(talk=4, sit=2, gesture=4), [
        replace(MAN, colour="wool", hand_l="staff"), replace(MAN, colour="lapis", trim="saffron"),
        replace(MAN, colour="cinnabar", hair="gloss", hand_l="staff"), replace(MAN, colour="ochre", beard="short")]),
    "elder": ("Old man with a staff", _a(sit=2), [
        replace(MAN, body="elder", garment="chiton_long", colour="linen", mantle="wool", hair="snow", hand_l="staff"),
        replace(MAN, body="elder", garment="chiton_long", colour="wool", mantle="eblue", hair="snow", hand_l="staff")]),
    "youth": ("Young man in chlamys and petasos", _a(), [
        YOUTH, replace(YOUTH, colour="whitewash", cape="purple"), replace(YOUTH, colour="eblue", cape="ochre",
                                                                          head="petasos")]),
    "woman": ("Citizen woman", _a(carry=8, carry_idle=3, throw=4), [
        replace(WOMAN, colour="saffron", mantle="cinnabar", mantle_head=True),
        replace(WOMAN, colour="linen", mantle="eblue", mantle_head=True, jewels=("earrings", "necklace")),
        replace(WOMAN, garment="peplos", colour="cinnabar", trim="saffron", head="sakkos", head_mat="eblue"),
        replace(WOMAN, colour="whitewash", mantle="purple", head="fillet", head_mat="saffron")]),
    "working_woman": ("Working woman (seller, wool-worker)", _a(serve=4, throw=4), [
        replace(WOMAN, garment="peplos", colour="wool", head="sakkos", head_mat="ochre", feet="bare", jewels=()),
        replace(WOMAN, colour="ochre", mantle="wool", head="sakkos", head_mat="cinnabar", jewels=()),
        replace(WOMAN, garment="peplos", colour="mudbrick", trim="cinnabar", feet="bare", jewels=())]),
    "child": ("Girl or boy", _a(run=8, kneel=2), [
        CHILD, replace(CHILD, garment="none", jewels=("amulet",)),
        replace(CHILD, garment="peplos", colour="saffron", hair_style="long"),
        replace(CHILD, colour="eblue", hand_l="wax_tablet")]),
    "enslaved_man": ("Enslaved worker in an exomis", _a(carry=8, carry_idle=3, work_low=4, haul=4), [
        WORKER, replace(WORKER, colour="felt", head="pilos", head_mat="felt"),
        replace(WORKER, colour="mudbrick", beard="none", skin=PALE, hair="ochre"),
        replace(WORKER, colour="linen", skin="skin_dark", beard="none")]),
    "enslaved_woman": ("Enslaved woman (nurse, water carrier)", _a(carry=8, carry_idle=3, stir=4), [
        SLAVE_W, replace(SLAVE_W, colour="felt", skin=PALE, hair="ochre", hold="front", hand_l="baby"),
        replace(SLAVE_W, colour="linen", hold="head", hand_l="hydria")]),
    "scythian": ("Scythian archer", _a(guard=3, gesture=4), [
        D(skin=PALE, hair="ochre", beard="full", garment="tunic", colour="saffron", pattern="dots", pattern_mat="gloss",
          trousers="cinnabar", head="pointed_hood", head_mat="cinnabar", worn=("gorytos",), feet="boots",
          hand_l="red_rope"),
        D(skin=PALE, hair="cedar", beard="full", garment="tunic", colour="eblue", pattern="squares", pattern_mat="saffron",
          trousers="ochre", head="pointed_hood", head_mat="saffron", worn=("gorytos",), feet="boots", hand_l="bow")]),
    "metic": ("Metic trader", _a(talk=4, serve=4), [
        replace(MAN, garment="chiton_long", colour="whitewash", mantle="cinnabar", hair="cedar", jewels=("bracelets",)),
        replace(MAN, colour="malachite", trim="saffron"),
        replace(MAN, garment="chiton", colour="ochre", cape="eblue", hand_l="wax_tablet")]),
    "hoplite": ("Hoplite", _a(march=8, guard=3), [
        HOPLITE,
        replace(HOPLITE, colour="eblue", head="pilos", head_mat="bronze_cast", pattern_mat="whitewash", trim="cinnabar"),
        replace(HOPLITE, colour="ochre", head="corinthian", head_trim="whitewash", pattern_mat="gloss", trim="saffron")]),
    "rower": ("Rower and sailor", _a(haul=4), [
        replace(WORKER, head="pilos", head_mat="felt", hand_l="oar"),
        replace(WORKER, colour="linen", beard="none", hand_l="oar"),
        replace(WORKER, garment="exomis", colour="felt", head="pilos", head_mat="wool")]),
    "potter": ("Potter", _a(throw=4, carry=8, carry_idle=3), [
        replace(WORKER, colour="clay", hand_l="pot"), replace(WORKER, colour="wool", skin=TAN, beard="full")]),
    "painter": ("Vase painter", _a(write=4), [
        replace(WORKER, garment="chiton", colour="linen", skin=TAN, beard="full", hand_r="brush", hand_l="pot"),
        replace(WORKER, garment="chiton", colour="ochre", skin=TAN, hand_r="brush")]),
    "smith": ("Bronze-smith", _a(work_high=4), [
        replace(WORKER, head="pilos", head_mat="felt", belt="leather", hand_r="hammer", hand_l="tongs"),
        replace(WORKER, colour="felt", head="pilos", head_mat="leather", belt="leather", hand_r="hammer")]),
    "mason": ("Mason", _a(work_high=4, carry=8, carry_idle=3, haul=4), [
        replace(WORKER, hand_r="mallet", hand_l="chisel"), replace(WORKER, colour="linen", skin=TAN, hand_r="mallet")]),
    "sculptor": ("Sculptor", _a(work_high=4), [
        replace(WORKER, garment="chiton", colour="whitewash", skin=TAN, beard="full", hand_r="mallet", hand_l="chisel"),
        replace(WORKER, colour="linen", skin=TAN, hand_r="mallet", hand_l="chisel")]),
    "farmer": ("Farmer", _a(work_low=4, carry=8, carry_idle=3), [
        replace(WORKER, head="petasos", head_mat="straw", hand_r="hoe", skin=TAN),
        replace(WORKER, colour="felt", head="pilos", head_mat="felt", hand_r="sickle")]),
    "herder": ("Shepherd and goatherd", _a(), [
        replace(WORKER, cape="felt", head="petasos", head_mat="straw", hand_l="crook", feet="boots"),
        replace(WORKER, cape="wool", head="pilos", head_mat="felt", hand_l="crook")]),
    "priest": ("Priest and priestess", _a(pour=4, pray=4), [
        replace(MAN, garment="chiton_long", colour="whitewash", mantle="whitewash", head="wreath", head_mat="olive",
                hand_l="phiale", hair_style="long"),
        replace(WOMAN, colour="saffron", mantle="whitewash", head="fillet", head_mat="cinnabar", hand_l="key")]),
    "philosopher": ("Philosopher and talker", _a(talk=4, gesture=4), [
        replace(MAN, colour="felt", hand_l="staff", feet="bare"), replace(MAN, colour="whitewash", trim="cinnabar")]),
    "athlete": ("Athlete", _a(run=8, wrestle=4, scrape=4), [
        D(skin=TAN, hair="cedar", hair_style="short", beard="none", garment="none", feet="bare", worn=("aryballos",),
          hand_r="strigil"),
        D(skin=OLIVE, hair="gloss", hair_style="curly", beard="none", garment="none", feet="bare", hand_l="discus")]),
    "musician": ("Aulos and kithara player", _a(play=4), [
        D(skin=TAN, hair="gloss", hair_style="short", beard="none", garment="long_tunic", colour="cinnabar",
          pattern="dots", pattern_mat="saffron", head="wreath", head_mat="olive", worn=("phorbeia",), hand_l="aulos",
          feet="shoes"),
        D(skin=TAN, hair="cedar", hair_style="curly", beard="short", garment="long_tunic", colour="eblue", pattern="dots",
          pattern_mat="whitewash", mantle="saffron", head="wreath", head_mat="olive", hand_l="kithara", feet="shoes")]),
    # The Panathenaic procession (athens.md §7.2).
    "kanephoros": ("Basket-bearer (kanephoros)", _a(), [
        D(body="woman", skin=TAN, hair="gloss", hair_style="long", beard="none", garment="peplos", colour="whitewash",
          trim="saffron", head="fillet", head_mat="saffron", hold="head", hand_l="kanoun", feet="shoes",
          jewels=("earrings", "necklace")),
        D(body="woman", skin=TAN, hair="cedar", hair_style="long", beard="none", garment="peplos", colour="saffron",
          trim="cinnabar", head="fillet", head_mat="olive", hold="head", hand_l="kanoun", feet="shoes",
          jewels=("earrings",))]),
    "hydriaphoros": ("Water-carrier of the procession", _a(), [
        replace(YOUTH, cape=None, head="wreath", head_mat="olive", colour="whitewash", hold="shoulder", hand_l="hydria"),
        replace(YOUTH, cape=None, head="wreath", head_mat="olive", colour="ochre", hold="shoulder", hand_l="hydria")]),
    "skaphephoros": ("Metic tray-bearer in purple", _a(), [
        replace(MAN, garment="chiton_long", colour="purple", head="wreath", head_mat="olive", hold="front",
                hand_l="tray"),
        replace(MAN, garment="chiton_long", colour="purple", hair="cedar", head="wreath", head_mat="olive",
                hold="front", hand_l="tray")]),
    "metic_daughter": ("Metic daughter with sunshade or stool", _a(), [
        replace(WOMAN, colour="whitewash", mantle="saffron", hand_l="skiadion", pattern_mat="eblue"),
        replace(WOMAN, colour="eblue", mantle="whitewash", hold="front", hand_l="stool")]),
    "thallophoros": ("Elder with an olive branch", _a(), [
        replace(MAN, body="elder", colour="whitewash", hair="snow", head="wreath", head_mat="olive", hand_l="branch"),
        replace(MAN, body="elder", colour="linen", trim="cinnabar", hair="snow", head="wreath", head_mat="olive",
                hand_l="branch")]),
    "marshal": ("Marshal of the procession", _a(gesture=4), [
        replace(MAN, colour="cinnabar", trim="gloss", head="wreath", head_mat="olive", hand_l="staff")]),
    "peplos_bearer": ("Bearer of Athena's new robe", _a(), [
        D(body="woman", skin=TAN, hair="gloss", hair_style="long", beard="none", garment="peplos", colour="whitewash",
          trim="saffron", head="fillet", head_mat="saffron", hold="front", hand_l="cloth", pattern_mat="saffron",
          feet="shoes")]),
    "drover": ("Youth leading a sacrificial heifer", _a(), [
        replace(YOUTH, cape=None, head="wreath", head_mat="olive", colour="whitewash", hold="lead"),
        replace(YOUTH, cape="cinnabar", head="wreath", head_mat="olive", hold="lead")]),
    "cavalryman": ("Horseman of the procession", _a(), [
        replace(YOUTH, mount=horse_mount), replace(YOUTH, cape="purple", head="petasos", mount=horse_mount),
        replace(YOUTH, cape="saffron", colour="whitewash", head="attic_helmet", head_mat="bronze_cast",
                head_trim="whitewash", mount=horse_mount)]),
    "chorus": ("Chorus member rehearsing", _a(dance=6), [
        D(skin=TAN, hair="gloss", beard="none", garment="long_tunic", colour="saffron", pattern="dots",
          pattern_mat="cinnabar", hand_l="mask", feet="boots"),
        D(skin=TAN, hair="cedar", beard="none", garment="long_tunic", colour="eblue", pattern="squares",
          pattern_mat="saffron", hand_l="mask", feet="boots")]),
    # Visitors (athens.md §6.2, §6.7).
    "thracian": ("Thracian", _a(), [
        D(skin=PALE, hair="ochre", beard="full", garment="chiton", colour="ochre", cape="cinnabar", pattern="dots",
          head="fox_cap", head_mat="orange", feet="boots", hand_l="dory")]),
    "spartan": ("Spartan visitor", _a(), [
        D(skin=TAN, hair="cedar", hair_style="long", beard="full", garment="chiton", colour="wool", cape="cinnabar",
          feet="bare", hand_l="staff")]),
    "ionian": ("Ionian merchant", _a(talk=4), [
        replace(MAN, garment="chiton_long", colour="saffron", mantle="purple", hair_style="curly",
                jewels=("bracelets", "earrings"))]),
    "persian_envoy": ("Persian envoy", _a(), [
        D(skin=TAN, hair="gloss", hair_style="bunch", beard="full", garment="tunic", colour="eblue", trousers="saffron",
          coat="cinnabar", belt="gold", head="round_cap", head_mat="wool", feet="boots", jewels=("torque",))]),
}

# ---- named figures (athens.md §4.1, §4.2); one look each, respectful and individual ----
FIGURE_ANIMS = {"pericles": _a(talk=4, gesture=4), "aspasia": _a(talk=4, sit=2), "socrates": _a(talk=4, sit=2),
                "sophocles": _a(talk=4, gesture=4), "euripides": _a(sit=2, write=4), "pheidias": _a(work_high=4),
                "mnesikles": _a(gesture=4), "protagoras": _a(talk=4, gesture=4), "meton": _a(gesture=4),
                "alcibiades": _a(), "solon": _a(talk=4), "themistocles": _a(gesture=4), "theseus": _a(),
                "rhapsode": _a(gesture=4, talk=4), "philinna": _a(throw=4, carry=8, carry_idle=3),
                "mania": _a(), "manes": _a(work_low=4), "kephalos": _a(talk=4), "sosias": _a(),
                "nikarete": _a(serve=4), "toxamis": _a(guard=3, gesture=4), "euphiletos": _a(work_low=4),
                "hegeso": _a(), "simon": _a(stir=4, talk=4)}

FIGURES = {
    "pericles": replace(MAN, hair="snow", colour="lapis", trim="saffron", head="corinthian", head_mat="bronze_cast",
                        head_trim="lapis", beard="full", hand_l="staff"),
    "aspasia": replace(WOMAN, colour="saffron", mantle="cinnabar", mantle_head=True, pattern="dots",
                       jewels=("earrings", "necklace", "bracelets")),
    "socrates": replace(MAN, colour="felt", hair="cedar", hair_style="balding", beard="full", feet="bare"),
    "sophocles": replace(MAN, body="elder", colour="whitewash", trim="saffron", hair="snow", head="wreath",
                         head_mat="olive", hand_l="staff"),
    "euripides": replace(MAN, colour="eblue", hair="cedar", beard="square", hand_l="scroll"),
    "pheidias": replace(WORKER, garment="chiton", colour="linen", skin=TAN, hair="snow", beard="full", belt="leather",
                        hand_r="mallet", hand_l="chisel"),
    "mnesikles": replace(MAN, colour="ochre", hand_l="staff", hand_r="wax_tablet"),
    "protagoras": replace(MAN, garment="chiton", colour="malachite", cape="purple", hair="snow", feet="boots",
                          hand_l="staff"),
    "meton": replace(MAN, colour="linen", trim="eblue", hand_l="staff"),
    "alcibiades": replace(YOUTH, cape="purple", colour="whitewash", hair_style="long", head="none", mount=horse_mount),
    "solon": replace(MAN, body="elder", garment="chiton_long", colour="linen", mantle="wool", hair="snow",
                     hand_l="staff"),
    "themistocles": replace(MAN, garment="chiton", colour="cinnabar", cape="lapis", head="corinthian",
                            head_mat="bronze_cast", feet="boots"),
    "theseus": D(skin=TAN, hair="cedar", hair_style="curly", beard="none", garment="chiton", colour="cinnabar",
                 cape="ochre", feet="boots", hand_l="club"),
    "rhapsode": replace(MAN, colour="purple", trim="saffron", head="wreath", head_mat="gold", hand_l="staff"),
    "philinna": replace(WOMAN, garment="peplos", colour="eblue", trim="saffron", head="sakkos", head_mat="cinnabar",
                        hand_l="spindle"),
    "mania": replace(SLAVE_W, colour="felt", hold="front", hand_l="baby"),
    "manes": replace(WORKER, head="pilos", head_mat="felt", colour="clay"),
    "kephalos": replace(MAN, body="elder", garment="chiton_long", colour="whitewash", mantle="lapis", hair="snow",
                        jewels=("bracelets",)),
    "sosias": replace(WORKER, skin=TAN, colour="felt", head="petasos", head_mat="straw", beard="full", feet="boots",
                      hand_l="staff"),
    "nikarete": replace(WOMAN, body="elder", colour="wool", mantle="ochre", hair="snow", hold="front", hand_l="bread"),
    "toxamis": replace(WALKERS["scythian"][2][0], hair="cedar"),
    "euphiletos": replace(WORKER, skin=TAN, colour="mudbrick", head="petasos", head_mat="straw", beard="full",
                          hand_r="hoe"),
    "hegeso": replace(CHILD, body="child", garment="peplos", colour="saffron", hair_style="long", hold="head",
                      hand_l="kanoun"),
    "simon": replace(WORKER, garment="exomis", colour="ochre", skin=TAN, beard="full", belt="leather"),
}

# Tools change with the work being done (the dress carries the walking look).
WORK_PROPS = {
    "woman": {"carry": dict(mantle_head=False), "carry_idle": dict(mantle_head=False),
              "throw": dict(mantle_head=False, hand_l="spindle")},
    "working_woman": {"throw": dict(hand_l="spindle"), "serve": dict(hand_l="bread")},
    "enslaved_man": {"work_low": dict(hand_r="hoe"), "haul": dict(hand_l="rope")},
    "enslaved_woman": {"carry": dict(hold=None, hand_l=None), "carry_idle": dict(hold=None, hand_l=None),
                       "stir": dict(hold=None, hand_l=None)},
    "potter": {"carry": dict(hand_l=None), "carry_idle": dict(hand_l=None)},
    "mason": {"carry": dict(hand_l=None, hand_r=None), "carry_idle": dict(hand_l=None, hand_r=None),
              "haul": dict(hand_l="rope", hand_r=None)},
    "rower": {"haul": dict(hand_l="rope")},
    "farmer": {"carry": dict(hand_r=None), "carry_idle": dict(hand_r=None)},
    "priest": {"pray": dict(hand_l=None)},
    "philinna": {"carry": dict(hand_l=None), "carry_idle": dict(hand_l=None)},
    "euripides": {"write": dict(hand_l="wax_tablet", hand_r="stylus")},
}


def dress_for(kind: str, variant) -> Dress:
    name = kind.split(".", 1)[1]
    if name in FIGURES:
        return FIGURES[name]
    return WALKERS[name][2][variant or 0]


def _posed(kind, variant, anim):
    name = kind.split(".", 1)[1]
    return replace(dress_for(kind, variant), **WORK_PROPS.get(name, {}).get(anim, {}))


def sprite(kind, variant, anim, facing, frame, k):
    return person_sprite(_posed(kind, variant, anim), anim, facing, frame, k)


def carry_at(kind, k):
    return carry_table(lambda anim: _posed(kind, 0, anim), k)
