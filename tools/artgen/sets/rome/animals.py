"""Rome's animals, boats and carts (rome.md §3.3, §3.6, §6.3, §7.2-7.3): donkeys of the mills
and loads, mules, oxen of the night carts, horses and the Cappadocian racehorses, the
Molossian guard dog and a little house dog, cats (common in houses by now), sheep and goats of
the Parilia and Trastevere, pigs, geese, hens, pigeons on the temple roofs, gulls over the
Emporium and swallows back in April; the towed Tiber barge and the round-hulled grain ship
with its square sail and artemon; the heavy ox cart (by night), the mule carriage, the
curtained litter with its bearers, and the racing chariot in the four faction colours.
Quadrupeds use the shared builder of the Pārsa set (proportions and markings as data); like
critters they face +x, anchored under the body."""

import math
from dataclasses import replace

import numpy as np

from arch import ellipsoid, fill, rod, slab
from rig import CART_FRAMES, CRITTER_FRAMES, WALK_FRAMES, WALK_STRIDE, Body, Dress, Frame, draw, pose
from sets.parsa.animals import SIZE, Beast, _merge, _render, _wheel, bird_feet, quadruped, stride
from greek import paste
from voxel import Model

BEASTS = {
    "rome.donkey": Beast(6.8, 5.4, 1.5, 2.0, 0.55, 1.0, coat="wood_grey", belly="cream", tail="tuft", ears="long"),
    "rome.mule": Beast(7.8, 6.6, 1.5, 2.6, 0.6, 1.0, coat="cedar", tail="tuft", ears="long"),
    "rome.ox": Beast(9.0, 7.0, 2.1, 1.6, 0.2, 1.1, coat="cream", horns="bull", tail="tuft", dewlap=True),
    "rome.horse": Beast(8.8, 8.0, 1.5, 3.4, 0.75, 1.0, coat="cedar", mane="hair_black", tail="long"),
    "rome.racehorse": Beast(9.2, 8.2, 1.4, 3.6, 0.8, 1.0, coat="felt", mane="hair_black", tail="tied",
                            topknot=True),
    "rome.dog_molossian": Beast(6.4, 5.0, 1.4, 1.6, 0.5, 1.0, coat="felt", tail="bushy", leg=0.36),
    "rome.dog": Beast(5.0, 3.6, 0.9, 1.4, 0.6, 0.75, coat="ochre", belly="cream", tail="thin", leg=0.28),
    "rome.cat": Beast(3.6, 2.4, 0.7, 0.9, 0.7, 0.6, coat="ginger", tail="long", ears="round", leg=0.2),
    "rome.sheep": Beast(5.6, 4.0, 1.8, 1.3, 0.4, 0.8, coat="wool", mane="wool", tail="bushy", leg=0.32),
    "rome.goat": Beast(5.4, 4.4, 1.3, 1.6, 0.6, 0.8, coat="felt", belly="wool", horns="ram", tail="tuft", leg=0.3),
    "rome.pig": Beast(5.6, 3.4, 1.6, 0.8, 0.1, 0.9, coat="clay", tail="thin", leg=0.3),
}


def _bird(m, coat, belly, beak, flying, t, scale=1.0, tail=1.0):
    bd = Body(m, rot=np.eye(3) / scale)
    bd.blob((0, 0, 2.0), (1.6, 0.9, 0.9), coat, 0.1)
    bd.blob((0.2, 0, 1.6), (1.2, 0.75, 0.6), belly, 0.2)
    bd.blob((1.4, 0, 2.7), (0.6, 0.5, 0.55), coat, 0.2)
    bd.limb((1.8, 0, 2.6), (2.4, 0, 2.4), 0.15, beak)
    bd.limb((-1.2, 0, 2.2), (-2.6 * tail, 0, 2.3), 0.35, coat, -0.1)
    if flying:
        a = 0.4 + 0.8 * math.sin(2 * math.pi * t)     # one wingbeat a cycle
        for s in (1, -1):
            bd.limb((0, s * 0.6, 2.4), (-0.5, s * 3.4, 2.4 + a * 1.4), 0.45, coat, 0.1)
    else:
        for y in (0.35, -0.35):
            bd.limb((0.2, y, 1.2), (0.2, y, 0.0), 0.12, beak)


def pigeon(anim, frame, frames, k):
    """A pigeon of the temple roofs: blue-grey with a green-violet sheen at the neck."""
    m = Model.empty(-6, 7, -6, 6, 0, 9, k=k)
    _bird(m, "stone", "slate", "cinnabar", anim == "move", frame / frames, 1.5)
    bd = Body(m, rot=np.eye(3) / 1.5)
    bd.blob((1.1, 0, 2.5), (0.45, 0.55, 0.4), "malachite", 0.3)
    return m


def gull(anim, frame, frames, k):
    m = Model.empty(-7, 7, -7, 7, 0, 9, k=k)
    _bird(m, "whitewash", "whitewash", "yellow", anim == "move", frame / frames, 1.3)
    return m


def swallow(anim, frame, frames, k):
    """A swallow, back in April: dark blue back, pale belly, the long forked tail."""
    m = Model.empty(-6, 6, -6, 6, 0, 8, k=k)
    _bird(m, "lapis", "cream", "ink", anim == "move", frame / frames, 2.0, tail=1.5)
    return m


def goose(anim, frame, frames, k):
    """A goose (the Capitol's sacred geese had saved Rome): white, orange bill, long neck."""
    m = Model.empty(-6, 8, -4, 4, 0, 11, k=k)
    bd = Body(m, rot=np.eye(3) / 1.3)
    peck = anim in ("peck", "graze") and frame % 2 == 1
    bd.blob((0, 0, 2.2), (1.9, 1.1, 1.1), "whitewash", 0.1)
    hz = 4.6 - (2.6 if peck else 0.0)
    bd.limb((1.4, 0, 2.8), (1.9, 0, hz), 0.45, "whitewash", 0.2)
    bd.blob((2.1, 0, hz + 0.2), (0.6, 0.45, 0.5), "whitewash", 0.3)
    bd.limb((2.5, 0, hz + 0.1), (3.2, 0, hz - 0.1), 0.2, "orange")
    for y, (fx, fz) in zip((0.4, -0.4), bird_feet(frame / frames, anim == "move")):
        bd.limb((0.2, y, 1.2), (0.2 + fx, y, fz), 0.15, "orange")
    return m


def hen(anim, frame, frames, k):
    from sets.athens.animals import hen as athens_hen
    return athens_hen(anim, frame, frames, k)


BIRDS = {"rome.pigeon": pigeon, "rome.gull": gull, "rome.swallow": swallow, "rome.goose": goose, "rome.hen": hen}
WALKING_BIRDS = {"rome.goose": 1.3, "rome.hen": 1.4}   # walking birds: body scale (strides)
CRITTERS = {**{k_: None for k_ in BEASTS}, **BIRDS}
CRITTER_ANIMS = {
    "rome.donkey": ("graze",), "rome.mule": ("graze",), "rome.ox": ("graze",), "rome.horse": ("graze",),
    "rome.racehorse": ("graze",), "rome.dog_molossian": ("sleep",), "rome.dog": ("sleep",), "rome.cat": ("sleep",),
    "rome.sheep": ("graze",), "rome.goat": ("graze",), "rome.pig": ("graze",), "rome.pigeon": ("peck",),
    "rome.gull": (), "rome.swallow": (), "rome.goose": ("peck",), "rome.hen": ("peck",),
}
CRITTER_NAMES = {
    "rome.donkey": "Donkey", "rome.mule": "Mule", "rome.ox": "Ox", "rome.horse": "Horse",
    "rome.racehorse": "Cappadocian racehorse", "rome.dog_molossian": "Molossian guard dog", "rome.dog": "House dog",
    "rome.cat": "Cat", "rome.sheep": "Sheep", "rome.goat": "Goat", "rome.pig": "Pig", "rome.pigeon": "Pigeon",
    "rome.gull": "Gull", "rome.swallow": "Swallow", "rome.goose": "Goose", "rome.hen": "Hen",
}


# ---------------------------------------------------------------- boats

def _hull(m, L, beam, depth, mat="wood", stern_post=True):
    def half(X):
        t = np.clip((X + L / 2) / L, 0, 1)
        return beam * np.sin(np.pi * t) ** 0.55 + 0.4

    fill(m, (-L / 2, L / 2, -beam - 1, beam + 1, 0.0, depth + 3.0), mat,
         lambda X, Y, Z: (np.abs(Y) < half(X)) & (Z > depth * 0.3 * (Y / beam) ** 2) &
         (Z < depth + 1.5 * ((X / (L / 2)) ** 2)),
         tone=lambda X, Y, Z: -0.4 * ((Z % 1.6) < 0.4) + 0.1)
    fill(m, (-L / 2 + 3, L / 2 - 3, -beam, beam, depth - 1.0, depth), "wood_light",
         lambda X, Y, Z: np.abs(Y) < half(X) - 1.0, tone=0.2)
    if stern_post:     # the swan-neck stern post curving up and forward
        rod(m, (-L / 2 + 1, 0, depth), (-L / 2 - 3, 0, depth + 7.0), 0.7, mat)
        rod(m, (-L / 2 - 3, 0, depth + 7.0), (-L / 2 - 1, 0, depth + 10.0), 0.6, mat)
        ellipsoid(m, (-L / 2 - 0.6, 0, depth + 10.4), (0.9, 0.7, 0.8), "gold", 0.3)


def ship_model(kind, anim, frame, k):
    """The round-hulled merchant ship of the grain fleet (rome.md §3.3) and the towed Tiber
    barge: `move` under sail (or towed), `slack` sail hanging, `row` sweeps out, `idle` moored."""
    m = Model.empty(-44, 44, -18, 18, 0, 64, k=k)
    t = frame / 4
    if kind == "rome.merchantman":
        L, beam, depth = 56.0, 9.0, 8.0
        _hull(m, L, beam, depth)
        slab(m, -L / 2 + 4, -L / 2 + 14, -5, 5, depth, depth + 5.0, "wood", tone=0.1)     # the stern cabin
        slab(m, -L / 2 + 3.5, -L / 2 + 14.5, -5.5, 5.5, depth + 5.0, depth + 5.8, "terracotta", tone=0.2)
        for s in (1, -1):
            rod(m, (-L / 2 + 6, s * 8.0, depth + 1.0), (-L / 2 - 2, s * 9.0, 0.0), 0.6, "wood")      # steering oars
        for i in range(6):
            ellipsoid(m, (-6.0 + i * 4.5, (-1) ** i * 2.4, depth + 1.6), (2.2, 1.8, 1.6), "wool", 0.1)
        sail = anim in ("move", "slack")
        rod(m, (4.0, 0.0, depth), (4.0, 0.0, 52.0 if sail else 40.0), 0.7, "wood")
        rod(m, (L / 2 - 6, 0.0, depth), (L / 2 + 6, 0.0, depth + 16.0), 0.5, "wood")             # the artemon mast
        if sail:
            belly = 4.0 + 0.6 * math.sin(t * 2 * math.pi) if anim == "move" else 0.7
            fill(m, (0.0, 14.0, -15.0, 15.0, 22.0, 50.0), "cream",
                 lambda X, Y, Z: np.abs(X - (4.0 + belly * np.clip(1 - (Y / 15.0) ** 2, 0, 1) *
                                              np.clip(1 - ((Z - 36) / 14.0) ** 2, 0, 1))) < 0.45,
                 tone=lambda X, Y, Z: 0.3 * ((Z % 4.0) < 0.5) - 0.1 - 0.4 * ((np.abs(Y) < 1.0)))
            rod(m, (4.0, -15.0, 50.0), (4.0, 15.0, 50.0), 0.45, "wood")
            fill(m, (L / 2 - 2, L / 2 + 8, -5.0, 5.0, depth + 6.0, depth + 15.0), "cream",
                 lambda X, Y, Z: np.abs(X - (L / 2 + 2.0 + (Z - depth - 6.0) * 0.5 + belly * 0.3)) < 0.45, tone=0.0)
        else:
            rod(m, (4.0, -11.0, 38.0), (4.0, 11.0, 38.0), 1.0, "cream", tone=0.1)
        if anim == "row":
            for x in (-4.0, 6.0, 16.0):
                for s in (1, -1):
                    rod(m, (x, s * 8.0, depth), (x - 2.0 * math.sin(t * 6.28), s * 15.0, 0.5), 0.25, "wood_light")
    else:
        # The Tiber barge (caudicaria): flat and broad, a mast forward for the tow rope, sacks
        # and amphorae heaped amidships, the steersman at the long oar.
        L, beam, depth = 52.0, 8.0, 5.0
        _hull(m, L, beam, depth, stern_post=False)
        for i in range(10):
            x, y = -14.0 + (i % 5) * 6.0, (-1) ** (i // 5) * 3.0
            if i % 3:
                ellipsoid(m, (x, y, depth + 1.6), (2.4, 2.0, 1.8), "wool", 0.1)
            else:
                from sets.rome.ground import amphora
                amphora(m, x, y, depth, "dressel20")
        rod(m, (L / 2 - 12, 0.0, depth), (L / 2 - 12, 0.0, depth + 24.0), 0.5, "wood")
        if anim == "move":       # the tow rope running forward to the haulers on the bank
            rod(m, (L / 2 - 12, 0.0, depth + 24.0), (L / 2 + 14, 16.0, depth + 6.0), 0.15, "straw", 0.2)
        rod(m, (-L / 2 + 2, 2.0, depth + 2.0), (-L / 2 - 8, 4.0, 0.0), 0.6, "wood")
        d = Dress(garment="tunic", colour="felt", beard="full", beard_mat="cedar", hair_style="short", head="pilos",
                  head_mat="felt", feet="bare", skin="skin_olive")
        fr = Frame(d)
        p = pose("haul" if anim == "row" else "idle", frame % (4 if anim == "row" else 2), 4 if anim == "row" else 2,
                 fr, d)
        draw(Body(m, shift=(-L / 2 + 6.0, 0.0, depth)), d, p, fr)
    return m


SHIPS = {"rome.merchantman", "rome.barge"}


# ---------------------------------------------------------------- carts, litters, chariots

def _person(m, x, y, z, dress, anim, frame, cycle=None):
    fr = Frame(dress)
    p = pose("move", frame, CART_FRAMES, fr, dress, cycle) if anim == "move" else pose("idle", frame % 2, 2, fr, dress)
    draw(Body(m, shift=(x, y, z)), dress, p, fr)


def cart_stride(kind) -> float:
    """Ground one cycle of a cart's `move` covers, design units (its team's walk; the litter
    at its bearers' step)."""
    return {"rome.cart": stride(BEASTS["rome.ox"]), "rome.carriage": stride(BEASTS["rome.mule"]),
            "rome.racing_chariot": stride(BEASTS["rome.racehorse"])}.get(kind, 4 * WALK_STRIDE)


CARTER = Dress(garment="tunic", colour="felt", belt="leather", beard="short", beard_mat="ochre", hair_style="short",
               head="hood", head_mat="felt", cloak="felt", cloak_hood=True, feet="boots", skin="skin_olive",
               hand_l="whip")
BEARER = Dress(garment="tunic", colour="cinnabar", belt="leather", beard="none", hair="cedar", hair_style="short",
               feet="bare", skin="skin_olive")
FACTIONS = ("whitewash", "cinnabar", "malachite", "lapis")       # Whites, Reds, Greens, Blues


def cart_model(kind, variant, anim, frame, k):
    """Carts with their teams and drivers baked in (world-tech.md §1.9)."""
    n = CART_FRAMES
    turn = frame / n * (math.pi / 3) if anim == "move" else 0.0
    team = "move" if anim == "move" else "idle"
    tf, tn = (frame, n) if team == "move" else (frame % 2, 2)
    m = Model.empty(-46, 44, -16, 16, 0, 48, k=k)
    bd = Body(m)
    if kind == "rome.cart":
        # The heavy plaustrum behind a yoke of oxen, solid wheels, a lantern for the night:
        # building stone (v0), amphorae (v1), sacks of grain (v2).
        for y in (-5.0, 5.0):
            m = _merge(m, quadruped(BEASTS["rome.ox"], team, tf, tn, k), 18.0, y)
        bd = Body(m)
        rod(m, (14.0, -8, 13.5), (14.0, 8, 13.5), 0.9, "wood")
        rod(m, (14.0, 0, 13.0), (-12.0, 0, 9.5), 0.8, "wood")
        slab(m, -36, -12, -7, 7, 8.5, 10.0, "wood_light", tone=0.2)
        for y in (-8.4, 8.4):
            _wheel(bd, -24, 7.5, 7.2, y, turn, "wood")
        if variant == 0:
            slab(m, -33, -15, -5.5, 5.5, 10.0, 17.0, "travertine", tone=0.3)
        elif variant == 1:
            from sets.rome.ground import amphora
            for i in range(6):
                amphora(m, -32.0 + (i % 3) * 7.0, -3.0 + (i // 3) * 6.0, 10.0, "dressel20")
        else:
            for i, (x, y) in enumerate(((-31, -3), (-25, 3), (-19, -2), (-28, 2), (-21, 3))):
                ellipsoid(m, (x, y, 13.0 + (i // 3) * 3.0), (3.2, 2.6, 2.6), "wool", tone=0.1 * i)
        rod(m, (-12.0, 7.0, 10.0), (-12.0, 7.0, 18.0), 0.25, "wood")
        ellipsoid(m, (-12.0, 7.0, 17.0), (0.8, 0.8, 1.1), "lamp", 0.2)
        _person(m, 16.0, 12.0, 0.0, CARTER, anim, frame, stride(BEASTS["rome.ox"]))
    elif kind == "rome.carriage":
        # A travelling raeda: a four-wheeled covered carriage behind two mules.
        for y in (-4.5, 4.5):
            m = _merge(m, quadruped(BEASTS["rome.mule"], team, tf, tn, k), 18.0, y)
        bd = Body(m)
        slab(m, -34, -8, -7, 7, 8.0, 10.0, "wood", tone=0.1)
        fill(m, (-34, -8, -7, 7, 10.0, 21.0), "felt", lambda X, Y, Z: (Z - 10.0) < 11.0 * np.sqrt(np.clip(1 - (Y / 7.0) ** 2, 0, 1)),
             tone=lambda X, Y, Z: -0.4 * ((X % 4.0) < 0.6))
        for x in (-30.0, -12.0):
            for y in (-8.0, 8.0):
                _wheel(bd, x, 5.0, 4.8, y, turn, "wood")
        _person(m, -6.0, 0.0, 8.0, replace(CARTER, cloak=None, head="none"), "idle", frame)
    elif kind == "rome.litter":
        # A curtained litter (lectica) on long poles, borne by four bearers in matching tunics.
        slab(m, -10, 10, -6, 6, 16.0, 17.0, "wood", tone=0.2)
        fill(m, (-10, 10, -6, 6, 17.0, 27.0), "cinnabar",
             lambda X, Y, Z: (np.abs(Y) > 5.2) | (np.abs(X) > 9.2) | (Z > 26.0),
             tone=lambda X, Y, Z: -0.4 * (((X + Y) % 2.0) < 0.5))
        for x in (-9.5, 9.5):
            for y in (-5.5, 5.5):
                rod(m, (x, y, 17.0), (x, y, 26.0), 0.35, "gold")
        for y in (-7.0, 7.0):
            rod(m, (-26.0, y, 18.0), (26.0, y, 18.0), 0.6, "wood", 0.2)
        for i, (x, y) in enumerate(((20.0, -7.0), (20.0, 7.0), (-20.0, -7.0), (-20.0, 7.0))):
            _person(m, x, y, 0.0, BEARER, anim, (frame + i * n // 4) % n)
    else:
        # A racing quadriga of the Circus in its faction's colour (variant: Whites, Reds, Greens,
        # Blues), the charioteer with laced bands round his body and the reins tied round him.
        col = FACTIONS[variant % 4]
        for i, y in enumerate((-9.0, -3.0, 3.0, 9.0)):
            m = _merge(m, quadruped(BEASTS["rome.racehorse"], team, (tf + i * tn // 4) % tn, tn, k), 20.0, y)
        bd = Body(m)
        rod(m, (8.0, 0, 13.0), (-10.0, 0, 9.0), 0.6, "wood")
        slab(m, -18, -9, -5.0, 5.0, 7.0, 8.0, "wood", tone=0.2)
        fill(m, (-18, -9, -5.5, 5.5, 8.0, 13.0), col, lambda X, Y, Z: (np.abs(Y) > 4.6) | (X > -10.0), tone=0.2)
        for y in (-6.0, 6.0):
            _wheel(bd, -14, 6.0, 5.8, y, turn, "wood")
        d = Dress(garment="tunic", colour=col, worn=("straps",), head="leather_cap", head_mat="leather", beard="none",
                  hair="cedar", hair_style="short", feet="boots", skin="skin_tan", hold="front")
        fr = Frame(d)
        draw(Body(m, shift=(-14.0, 0.0, 8.0)), d, pose("idle", frame % 2, 2, fr, d), fr)
    return m


CARTS = {"rome.cart": ("Heavy ox cart (plaustrum)", 3), "rome.carriage": ("Travel carriage (raeda)", 1),
         "rome.litter": ("Litter with bearers", 1), "rome.racing_chariot": ("Racing quadriga", 4)}


def sprite(kind, variant, anim, facing, frame, k):
    if kind in CARTS:
        return _render(cart_model(kind, variant or 0, anim, frame, k), facing)
    if kind in SHIPS:
        return _render(ship_model(kind, anim, frame, k), facing)
    frames = CRITTER_FRAMES[anim]
    if kind in BIRDS:
        return _render(BIRDS[kind](anim, frame, frames, k), facing)
    return _render(quadruped(BEASTS[kind], anim, frame, frames, k), facing)


def actors_catalog():
    out = []
    for kid in CRITTERS:
        anims = {"move": {"fps": 8}, "idle": {"fps": 3}, **{a: {"fps": 3} for a in CRITTER_ANIMS[kid]}}
        out.append({"id": kid, "name": CRITTER_NAMES[kid], "sprite": f"critter/{kid}", "anims": anims})
    for kid, (name, variants) in CARTS.items():
        out.append({"id": kid, "name": name, "sprite": f"cart/{kid}", "variants": variants,
                    "anims": {"move": {"fps": 6}, "idle": {"fps": 2}}, "size": [2, 1]})
    for kid, name, size in (("rome.merchantman", "Roman merchant ship", [5, 2]), ("rome.barge", "Tiber barge", [4, 1])):
        out.append({"id": kid, "name": name, "sprite": f"ship/{kid}", "variants": 1,
                    "anims": {"move": {"fps": 4}, "slack": {"fps": 2}, "row": {"fps": 4}, "idle": {"fps": 2}},
                    "size": size})
    return out


def horse_mount(b0: Body, phase: float):
    """A horse under a rider (a callable rig mount): returns the saddle height."""
    beast = BEASTS["rome.horse"]
    paste(b0.m, quadruped(beast, "move", round(phase * WALK_FRAMES) % WALK_FRAMES, WALK_FRAMES, b0.m.k), 0.0, 0.0, 0.0)
    return beast.height * SIZE + 1.0


horse_mount.stride = stride(BEASTS["rome.horse"])   # the walk cycle the rider is drawn over (design units)
