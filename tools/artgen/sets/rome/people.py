"""The people of Rome in April 126 as dress data on the shared rig (rome.md §6.2, the dress
reference row by row and its common mistakes; §3.6 walker kinds; §6.3 occupations; §7.2 the
Parilia; §4 named figures). Most people wear belted tunics of undyed or coloured wool; the
toga only on citizens in formal dress, senators and magistrates (Hadrian required it in public
business), with its purple border only for magistrates and freeborn boys; matrons in stola and
palla over the head; beards in Hadrian's fashion on many men (lighter beard tones so faces read
at 1x); Praetorians in the city mostly in tunic and cloak, on parade with cuirass and crested
helmet; legionaries in plate armour only on campaign (veterans and recruits here), auxiliaries
in mail; enslaved people dressed like free workers (no uniform: they show by their tasks);
nobody in purple who should not be, no thumbs, no gladiators outside the arena."""

from dataclasses import replace

from rig import Dress, carry_table, person_sprite
from sets.rome.animals import horse_mount

D = Dress
TAN, OLIVE, PALE, DARK = "skin_tan", "skin_olive", "skin", "skin_dark"

MAN = D(skin=TAN, hair="cedar", hair_style="short", beard="curly", beard_mat="ochre", garment="tunic", colour="wool",
        belt="leather", feet="shoes")
TOGA = replace(MAN, garment="toga", colour="linen", under="wool", belt=None, feet="shoes")
WOMAN = D(body="woman", skin=TAN, hair="cedar", hair_style="knot", beard="none", garment="stola", colour="saffron",
          under="linen", mantle="eblue", mantle_head=True, feet="shoes", jewels=("earrings",))
WORKER_W = D(body="woman", skin=OLIVE, hair="cedar", hair_style="tied", beard="none", garment="long_tunic",
             colour="wool", belt="leather", head="headcloth", head_mat="linen", feet="shoes")
CHILD = D(body="child", skin=TAN, hair="cedar", hair_style="short", beard="none", garment="tunic", colour="linen",
          belt="wool", feet="shoes", jewels=("bulla",))
SOLDIER = D(skin=TAN, hair="cedar", hair_style="short", beard="short", beard_mat="ochre", garment="tunic",
            colour="cinnabar", worn=("segmentata", "cingulum", "gladius", "focale"), head="galea", head_mat="metal",
            head_trim="bronze", hand_l="scutum", hand_r="pilum", pattern_mat="cinnabar", feet="boots")
WORKER = D(skin=OLIVE, hair="cedar", hair_style="short", beard="short", beard_mat="ochre", garment="exomis",
           colour="wool", belt="leather", feet="bare")


def _a(**extra):
    return {"move": {"fps": 8}, "idle": {"fps": 3}, **{k: {"fps": v} for k, v in extra.items()}}


# kind: (name, anims, [dresses])
WALKERS = {
    "citizen": ("Citizen in a tunic", _a(talk=4, sit=2, gesture=4), [
        MAN, replace(MAN, colour="cinnabar", beard="none", hair_style="curls"),
        replace(MAN, colour="malachite", cloak="felt"), replace(MAN, colour="eblue", hair="hair_black",
                                                                beard_mat="cedar")]),
    "togatus": ("Citizen in a toga", _a(talk=4, gesture=4, sit=2), [
        TOGA, replace(TOGA, hair="snow", beard="none", body="elder"), replace(TOGA, hair_style="curls", hand_l="scroll")]),
    "senator": ("Senator (broad stripe and toga)", _a(talk=4, gesture=4, sit=2), [
        replace(TOGA, under="whitewash", clavi="purple", clavi_broad=True, hand_l="scroll", feet="boots",
                feet_mat="pitch"),
        replace(TOGA, body="elder", hair="snow", beard="none", under="whitewash", clavi="purple", clavi_broad=True,
                feet="boots", feet_mat="pitch")]),
    "matron": ("Matron in stola and palla", _a(talk=4, serve=4, pray=4), [
        replace(WOMAN, hair_style="coil", jewels=("earrings", "necklace")),
        replace(WOMAN, colour="malachite", mantle="saffron"),
        replace(WOMAN, colour="eblue", mantle="whitewash", mantle_head=False, hair_style="coil", hair="ochre")]),
    "working_woman": ("Working woman (seller, innkeeper, midwife)", _a(serve=4, carry=8, carry_idle=3, talk=4,
                                                                       throw=4), [
        WORKER_W, replace(WORKER_W, colour="ochre", head="none", hair_style="knot"),
        replace(WORKER_W, colour="cinnabar", head_mat="saffron", hold="head", hand_l="basket"),
        replace(WORKER_W, colour="linen", mantle="eblue", head="none", hair_style="knot", skin=TAN)]),
    "child": ("Child (boy with bulla, girl)", _a(run=8, kneel=2), [
        CHILD, replace(CHILD, colour="cinnabar", hand_l="hoop"),
        replace(CHILD, garment="long_tunic", colour="saffron", hair_style="knot", jewels=("lunula",), hand_l="doll"),
        replace(CHILD, garment="long_tunic", colour="eblue", hair_style="knot", jewels=("lunula",))]),
    "enslaved": ("Enslaved household worker", _a(carry=8, carry_idle=3, work_low=4), [
        replace(MAN, colour="wool", beard="none"), replace(MAN, colour="felt", skin=DARK, hair="hair_black",
                                                            beard="none"),
        replace(WORKER_W, colour="wool"), replace(MAN, colour="linen", skin=PALE, hair="ochre", beard="short",
                                                  beard_mat="ochre")]),
    "freedman": ("Freedman or freedwoman shopkeeper", _a(serve=4, talk=4, carry=8, carry_idle=3), [
        replace(MAN, colour="saffron", jewels=("bracelets",)), replace(WORKER_W, colour="cinnabar", head="none",
                                                                       hair_style="knot", skin=TAN),
        replace(MAN, colour="ochre", head="pilleus", head_mat="felt")]),
    "praetorian": ("Praetorian guard", _a(guard=3, march=8), [
        replace(SOLDIER, worn=("cuirass", "gladius"), head="galea", head_mat="bronze", head_trim="gold",
                cape="cinnabar", hand_l="oval_shield", hand_r="spear", pattern_mat="eblue", colour="whitewash"),
        replace(MAN, colour="whitewash", cloak="cinnabar", worn=("gladius",), hand_l="spear", feet="boots")]),
    "vigil": ("Vigil (fireman of the night watch)", _a(carry=8, carry_idle=3), [
        replace(WORKER, garment="tunic", colour="felt", cloak="wool", hand_l="bucket", hand_r="axe", feet="boots"),
        replace(WORKER, garment="tunic", colour="wool", hand_l="lantern", hand_r="hook_pole", feet="boots")]),
    "lictor": ("Lictor with fasces", _a(guard=3), [
        replace(MAN, colour="whitewash", cape="cinnabar", hand_l="fasces", beard="none"),
        replace(MAN, colour="linen", cape="cinnabar", hand_l="fasces")]),
    "vestal": ("Vestal Virgin", _a(pray=4, carry=8, carry_idle=3), [
        D(body="woman", skin=TAN, hair="cedar", hair_style="braids", beard="none", garment="stola", colour="whitewash",
          under="whitewash", head="suffibulum", head_mat="whitewash", head_trim="cinnabar", feet="shoes",
          hand_l="simpulum")]),
    "flamen": ("Flamen with the apex cap", _a(pray=4, pour=4), [
        replace(TOGA, cloak="saffron", head="apex", head_mat="whitewash", beard="none", hand_l="staff")]),
    "builder": ("Builder (bricklayer, treadwheel walker, marble cutter)", _a(work_high=4, haul=4, carry=8,
                                                                           carry_idle=3), [
        replace(WORKER, hand_r="trowel"), replace(WORKER, colour="mudbrick", head="pilos", head_mat="felt"),
        replace(WORKER, colour="linen", skin=TAN, hand_r="mallet", hand_l="chisel")]),
    "docker": ("Porter and docker", _a(carry=8, carry_idle=3, haul=4), [
        WORKER, replace(WORKER, skin=DARK, hair="hair_black", beard="none", colour="linen"),
        replace(WORKER, colour="felt", head="pilos", head_mat="wool")]),
    "hauler": ("Barge hauler", _a(haul=4), [
        replace(WORKER, hand_l="rope"), replace(WORKER, colour="mudbrick", hand_l="rope", beard="none")]),
    "carter": ("Carter (by night)", _a(), [
        replace(MAN, cloak="felt", cloak_hood=True, head="hood", head_mat="felt", hand_l="whip", feet="boots"),
        replace(MAN, colour="mudbrick", hand_l="lantern", feet="boots")]),
    "baker": ("Baker", _a(stir=4, carry=8, carry_idle=3), [
        replace(WORKER, garment="tunic", colour="linen", skin=TAN, head="felt_cap", head_mat="linen")]),
    "fuller": ("Fuller treading cloth", _a(work_low=4), [
        replace(WORKER, garment="exomis", colour="linen", feet="bare")]),
    "smith": ("Smith", _a(work_high=4), [
        replace(WORKER, colour="felt", head="pilos", head_mat="felt", belt="leather", hand_r="hammer")]),
    "glassblower": ("Glassblower", _a(play=4), [
        replace(WORKER, garment="tunic", colour="eblue", skin=OLIVE, hair="hair_black", beard="full",
                beard_mat="cedar", hand_l="staff")]),
    "musician": ("Musician (tibia and cornu)", _a(play=4), [
        replace(MAN, colour="whitewash", head="wreath", head_mat="leaf", hand_l="aulos", beard="none"),
        replace(MAN, colour="cinnabar", cape="felt", hand_l="cornu")]),
    "shepherd": ("Shepherd of the Parilia", _a(run=8), [
        replace(WORKER, garment="tunic", colour="felt", cape="wool", head="petasos", head_mat="straw",
                hand_l="crook", feet="boots"),
        replace(WORKER, garment="tunic", colour="wool", head="wreath", head_mat="leaf", hand_l="branch",
                feet="bare")]),
    "farmer": ("Vine-dresser and gardener", _a(work_low=4, work_high=4), [
        replace(WORKER, garment="tunic", colour="mudbrick", head="petasos", head_mat="straw", hand_r="pruning_knife"),
        replace(WORKER, garment="tunic", colour="felt", hand_r="hoe")]),
    "bather": ("Bather with oil flask and strigil", _a(sit=2, scrape=4), [
        replace(MAN, colour="linen", hand_l="flask"), replace(WOMAN, mantle_head=False, hand_l="flask")]),
    "teacher": ("Schoolteacher", _a(talk=4, write=4), [
        replace(MAN, garment="himation", colour="wool", beard="full", hand_l="staff")]),
    "legionary": ("Legionary (veteran or recruit)", _a(march=8, guard=3), [
        SOLDIER, replace(SOLDIER, colour="wool", pattern_mat="cinnabar")]),
    "auxiliary": ("Auxiliary in mail", _a(march=8, guard=3), [
        replace(SOLDIER, worn=("hamata", "cingulum", "gladius"), hand_l="oval_shield", hand_r="spear",
                pattern_mat="eblue", colour="wool")]),
    # Foreigners (rome.md §5, §6.2).
    "egyptian_sailor": ("Egyptian sailor", _a(haul=4), [
        D(skin=DARK, hair="hair_black", hair_style="short", beard="none", garment="tunic", colour="linen",
          feet="bare", hand_l="rope")]),
    "syrian_merchant": ("Syrian merchant", _a(talk=4), [
        D(skin=OLIVE, hair="hair_black", hair_style="curls", beard="full", beard_mat="cedar", garment="long_tunic",
          colour="saffron", trim="cinnabar", mantle="malachite", feet="shoes",
          jewels=("bracelets", "earrings"))]),
    "greek_teacher": ("Greek teacher and philosopher", _a(talk=4), [
        D(skin=TAN, hair="snow", hair_style="short", beard="full", beard_mat="snow", garment="himation", colour="wool",
          feet="shoes", hand_l="scroll")]),
    "gaul": ("Gaul in trousers", _a(), [
        D(skin=PALE, hair="ochre", hair_style="long", beard="short", beard_mat="ochre", garment="tunic",
          colour="malachite", pattern="squares", pattern_mat="cinnabar", trousers="wool", cloak="cinnabar",
          feet="boots", jewels=("torque",))]),
    "german_guard": ("German horse guard", _a(guard=3), [
        D(skin=PALE, hair="ochre", hair_style="tied", beard="full", beard_mat="ochre", garment="tunic",
          colour="felt", trousers="felt", cape="wool", feet="boots", hand_l="spear", hand_r="oval_shield",
          pattern_mat="malachite")]),
    "moorish_horseman": ("Moorish horseman", _a(), [
        D(skin=DARK, hair="hair_black", hair_style="curls", beard="short", garment="tunic", colour="whitewash",
          feet="bare", hand_l="spear", mount=horse_mount)]),
    # Kinds the life data asks for (world-life-rome.md): the Iseum's priest with his sistrum,
    # the baths' attendant, and the arena's pairs (murmillo, retiarius, thraex).
    "isis_priest": ("Priest of Isis with sistrum", _a(pray=4, play=4), [
        D(skin=OLIVE, hair="skin_olive", hair_style="short", beard="none", garment="long_tunic", colour="whitewash",
          mantle="linen", feet="bare", hand_l="sistrum")]),
    "bath_attendant": ("Bath attendant", _a(serve=4, carry=8, carry_idle=3), [
        replace(WORKER, garment="tunic", colour="linen", beard="none", hand_l="strigil", hand_r="flask")]),
    "gladiator": ("Gladiator (murmillo, retiarius, thraex)", _a(guard=3, wrestle=4), [
        replace(WORKER, garment="wrap", colour="linen", belt="bronze", head="galea", head_mat="bronze",
                head_trim="cinnabar", hand_l="scutum", worn=("gladius",), pattern_mat="cinnabar", feet="bare"),
        replace(WORKER, garment="wrap", colour="linen", belt="bronze", hand_l="trident", hand_r="net", feet="bare"),
        replace(WORKER, garment="wrap", colour="ochre", belt="bronze", head="galea", head_mat="bronze",
                head_trim="saffron", hand_l="oval_shield", worn=("gladius",), pattern_mat="saffron", feet="boots")]),
    "jewish_trader": ("Jewish trader of Transtiberim", _a(talk=4), [
        D(skin=OLIVE, hair="hair_black", hair_style="curls", beard="full", beard_mat="cedar", garment="long_tunic",
          colour="wool", mantle="linen", feet="shoes", hand_l="basket", pattern_mat="eblue")]),
}

# ---- named figures (rome.md §4.1, §4.2): one look each, respectful and individual ----
FIGURE_ANIMS = {
    "hadrian": _a(talk=4, gesture=4), "sabina": _a(talk=4), "antinous": _a(), "marcus": _a(),
    "apollodorus": _a(gesture=4), "juvenal": _a(talk=4), "suetonius": _a(write=4), "mesomedes": _a(play=4),
    "soranus": _a(talk=4), "diocles": _a(), "vestalis_maxima": _a(pray=4), "plotina": _a(), "trajan": _a(),
    "numa": _a(), "scipio": _a(), "caesar": _a(), "cicero": _a(gesture=4), "castor": _a(),
    "claudia_helpis": _a(serve=4), "vibius_primus": _a(stir=4), "aelius_eutyches": _a(write=4), "apion": _a(haul=4),
    "mulvius": _a(), "flavius_valens": _a(), "felicula": _a(run=8, kneel=2), "rufina": _a(throw=4),
    "sextus": _a(carry=8, carry_idle=3), "iulia_ianuaria": _a(talk=4),
}

FIGURES = {
    # Hadrian: the short curly beard he made fashionable, curled hair; the toga with a purple
    # border on state occasions, a laurel wreath for the festival.
    "hadrian": replace(TOGA, hair_style="curls", beard="curly", beard_mat="cedar", trim="purple", under="whitewash",
                       head="wreath", head_mat="leaf", jewels=("ring",)),
    # Sabina: stola and palla, the high coil of her portrait hairstyle with a diadem-like band.
    "sabina": replace(WOMAN, colour="purple", under="linen", mantle="saffron", mantle_head=False, hair_style="coil",
                      head="fillet", head_mat="gold", jewels=("earrings", "necklace", "bracelets")),
    "antinous": D(skin=TAN, hair="cedar", hair_style="curls", beard="none", garment="tunic", colour="whitewash",
                  cape="eblue", feet="boots", hand_l="spear", mount=horse_mount),
    "marcus": replace(CHILD, garment="toga", colour="linen", under="linen", trim="purple"),
    "apollodorus": D(skin=OLIVE, hair="snow", hair_style="short", beard="full", beard_mat="snow", garment="himation",
                     colour="wool", feet="shoes", hand_l="staff", hand_r="scroll"),
    "juvenal": replace(TOGA, body="elder", colour="wool", under="felt", hair="snow", beard="none"),
    "suetonius": replace(MAN, colour="whitewash", clavi="purple", beard="none", hand_l="wax_tablet",
                         jewels=("ring",)),
    "mesomedes": D(skin=TAN, hair="cedar", hair_style="curls", beard="short", beard_mat="cedar",
                   garment="long_tunic", colour="eblue", trim="gold", mantle="saffron", head="wreath",
                   head_mat="gold", feet="shoes", hand_l="kithara"),
    "soranus": D(skin=TAN, hair="hair_black", hair_style="short", beard="full", beard_mat="cedar", garment="himation",
                 colour="linen", feet="shoes", hand_l="basket"),
    "diocles": D(skin=TAN, hair="cedar", hair_style="short", beard="none", garment="tunic", colour="whitewash",
                 worn=("straps",), head="leather_cap", head_mat="leather", feet="boots", hand_l="whip"),
    "vestalis_maxima": replace(WALKERS["vestal"][2][0], body="woman", hand_l="simpulum",
                               head_trim="purple"),
    "plotina": replace(WOMAN, body="elder", colour="whitewash", mantle="eblue", mantle_head=False, hair="snow",
                       hair_style="coil"),
    "trajan": D(skin=TAN, hair="snow", hair_style="short", beard="none", garment="tunic", colour="cinnabar",
                worn=("cuirass",), cape="purple", feet="boots", hand_l="spear"),
    "numa": replace(TOGA, body="elder", hair="snow", beard="full", beard_mat="snow", hand_l="scroll"),
    "scipio": replace(TOGA, beard="none", hair_style="short"),
    "caesar": replace(TOGA, beard="none", hair="cedar", trim="purple", head="wreath", head_mat="leaf"),
    "cicero": replace(TOGA, body="elder", hair="snow", beard="none", hand_l="scroll"),
    "castor": D(skin=TAN, hair="cedar", hair_style="curls", beard="none", garment="tunic", colour="whitewash",
                cape="cinnabar", head="pilleus", head_mat="whitewash", feet="boots", hand_l="spear", mount=horse_mount),
    "claudia_helpis": replace(WORKER_W, colour="cinnabar", head="none", hair_style="knot", skin=TAN,
                              jewels=("earrings",)),
    "vibius_primus": replace(WORKER, garment="tunic", colour="linen", skin=TAN, head="felt_cap", head_mat="linen",
                             beard="curly"),
    "aelius_eutyches": replace(MAN, colour="eblue", beard="none", hand_l="wax_tablet", jewels=("ring",)),
    "apion": replace(WALKERS["egyptian_sailor"][2][0], colour="whitewash"),
    "mulvius": replace(WORKER, garment="tunic", colour="felt", cloak="felt", head="pilos", head_mat="felt",
                       hand_l="staff", beard="full"),
    "flavius_valens": replace(WALKERS["vigil"][2][0], colour="cinnabar", beard="none"),
    "felicula": replace(CHILD, garment="long_tunic", colour="saffron", hair_style="knot", jewels=("lunula",)),
    "rufina": replace(WORKER_W, colour="eblue", mantle="linen", mantle_head=True, head="none", skin=OLIVE,
                      hand_l="spindle"),
    "sextus": replace(WORKER, garment="tunic", colour="wool", skin=PALE, hair="ochre", beard="short"),
    "iulia_ianuaria": replace(WORKER_W, colour="malachite", head_mat="whitewash", hand_l="basket"),
}

# Tools change with the work being done (the dress carries the walking look).
WORK_PROPS = {
    "working_woman": {"carry": dict(hold=None, hand_l=None), "carry_idle": dict(hold=None, hand_l=None)},
    "enslaved": {"work_low": dict(hand_r="broom")},
    "builder": {"carry": dict(hand_l=None, hand_r=None), "carry_idle": dict(hand_l=None, hand_r=None),
                "haul": dict(hand_l="rope", hand_r=None)},
    "baker": {"carry": dict(hand_l=None), "carry_idle": dict(hand_l=None)},
    "farmer": {"work_high": dict(hand_r="pruning_knife"), "work_low": dict(hand_r="hoe")},
    "teacher": {"write": dict(hand_l="wax_tablet", hand_r="stylus")},
    "suetonius": {"write": dict(hand_l="wax_tablet", hand_r="stylus")},
    "aelius_eutyches": {"write": dict(hand_l="wax_tablet", hand_r="stylus")},
    "sextus": {"carry": dict(), "carry_idle": dict()},
    "flamen": {"pour": dict(hand_l="phiale")},
    "vestal": {"pray": dict(hand_l=None), "carry": dict(hand_l=None), "carry_idle": dict(hand_l=None)},
    "vigil": {"carry": dict(hand_r=None), "carry_idle": dict(hand_r=None)},
    "freedman": {"carry": dict(), "carry_idle": dict()},
    "docker": {"haul": dict(hand_l="rope")},
    "bather": {"scrape": dict(hand_l="strigil")},
    "bath_attendant": {"carry": dict(hand_l=None, hand_r=None), "carry_idle": dict(hand_l=None, hand_r=None)},
    "isis_priest": {"pray": dict(hand_l=None)},
    "vestalis_maxima": {"pray": dict(hand_l=None)},
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


def actors_catalog():
    out = []
    for name, (title, anims, dresses) in WALKERS.items():
        out.append({"id": f"rome.{name}", "name": title, "sprite": f"walker/rome.{name}", "variants": len(dresses),
                    "anims": anims})
    for name, anims in FIGURE_ANIMS.items():
        out.append({"id": f"rome.{name}", "name": FIGURE_NAMES[name], "sprite": f"figure/rome.{name}", "anims": anims})
    return out


FIGURE_NAMES = {
    "hadrian": "Hadrianus", "sabina": "Vibia Sabina", "antinous": "Antinous", "marcus": "Marcus Annius Verus",
    "apollodorus": "Apollodorus of Damascus", "juvenal": "Iuvenalis", "suetonius": "Suetonius",
    "mesomedes": "Mesomedes", "soranus": "Soranus", "diocles": "Gaius Appuleius Diocles",
    "vestalis_maxima": "Virgo Vestalis Maxima", "plotina": "Plotina (a memory)", "trajan": "Traianus (a memory)",
    "numa": "Numa (a memory)", "scipio": "Scipio Africanus (a memory)", "caesar": "Divus Iulius (a memory)",
    "cicero": "Cicero (a memory)", "castor": "Castor and Pollux (an apparition)", "claudia_helpis": "Claudia Helpis",
    "vibius_primus": "Lucius Vibius Primus", "aelius_eutyches": "Publius Aelius Eutyches", "apion": "Apion",
    "mulvius": "Quintus Mulvius", "flavius_valens": "Titus Flavius Valens", "felicula": "Felicula",
    "rufina": "Rufina", "sextus": "Sextus", "iulia_ianuaria": "Iulia Ianuaria",
}
