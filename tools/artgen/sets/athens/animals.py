"""Athens's animals, ships and carts (athens.md §3.3, §3.6, §7.2): the small fine horses of the
Parthenon frieze, donkeys with charcoal panniers, mules, plough oxen and the garlanded heifers
of the procession, sheep and goats, Laconian and Molossian dogs, a pig, hens, the little owl of
Athena; triremes, merchant ships and fishing boats; the ox cart with a marble block, the
procession chariot and the quarry sledge. Quadrupeds use the shared builder of the Pārsa set
(proportions and markings as data); like critters they face +x, anchored under the body."""

import math

import numpy as np

from arch import ellipsoid, fill, rod, slab
from rig import Body, Dress, Frame, draw, pose
from sets.parsa.animals import Beast, SIZE, _merge, _render, _wheel, quadruped
from sets.athens.piraeus import hull
from greek import paste
from voxel import Model

BEASTS = {
    "athens.horse": Beast(8.6, 7.8, 1.45, 3.4, 0.75, 1.0, coat="cedar", mane="gloss", tail="long"),
    "athens.donkey": Beast(6.8, 5.4, 1.5, 2.0, 0.55, 1.0, coat="wood_grey", belly="cream", tail="tuft", ears="long"),
    "athens.mule": Beast(7.8, 6.6, 1.5, 2.6, 0.6, 1.0, coat="cedar", tail="tuft", ears="long"),
    "athens.ox": Beast(9.0, 7.0, 2.1, 1.6, 0.2, 1.1, coat="felt", horns="bull", tail="tuft", dewlap=True),
    "athens.heifer": Beast(8.4, 6.4, 1.9, 1.6, 0.25, 1.0, coat="whitewash", horns="bull", tail="tuft"),
    "athens.sheep": Beast(5.6, 4.0, 1.8, 1.3, 0.4, 0.8, coat="wool", mane="wool", tail="bushy", leg=0.32),
    "athens.goat": Beast(5.4, 4.4, 1.3, 1.6, 0.6, 0.8, coat="felt", belly="wool", horns="ram", tail="tuft", leg=0.3),
    "athens.dog_laconian": Beast(5.8, 4.6, 0.95, 1.8, 0.6, 0.8, coat="ochre", tail="thin", leg=0.3),
    "athens.dog_molossian": Beast(6.4, 5.0, 1.4, 1.6, 0.5, 1.0, coat="gloss", tail="bushy", leg=0.36),
    "athens.pig": Beast(5.6, 3.4, 1.6, 0.8, 0.1, 0.9, coat="clay", tail="thin", leg=0.3),
}


def owl(anim, frame, frames, k):
    """The little owl (Athene noctua), Athena's bird, common on the rock: round, brown with pale
    spots, big yellow eyes; bobbing when it perches, wings out when it flies."""
    m = Model.empty(-6, 6, -6, 6, 0, 10, k=k)
    bd = Body(m, rot=np.eye(3) / 1.6)
    flying = anim == "move"
    bob = 0.25 * (frame % 2)
    bd.blob((0, 0, 2.0 + bob), (1.2, 1.1, 1.5), "cedar", 0.1)
    bd.put((((bd.X * 3 + bd.Z * 2) % 1.0) < 0.25) & ((bd.X / 1.3) ** 2 + (bd.Y / 1.2) ** 2 + ((bd.Z - 2.0 - bob) / 1.6) ** 2
                                                      <= 1), "cream", 0.2)
    bd.blob((0.2, 0, 3.6 + bob), (1.0, 1.0, 0.9), "cedar", 0.2)
    for y in (0.45, -0.45):
        bd.blob((0.95, y, 3.7 + bob), (0.2, 0.3, 0.3), "yellow", 0.6)
    if flying:
        a = (0.4, 1.0, 0.4, -0.2)[frame % 4]
        for s in (1, -1):
            bd.limb((0, s * 0.8, 2.6), (-0.3, s * 3.2, 2.6 + a * 1.5), 0.5, "cedar", 0.1)
    else:
        for y in (0.4, -0.4):
            bd.limb((0.1, y, 0.8), (0.3, y, 0.0), 0.15, "yellow")
    return m


def hen(anim, frame, frames, k, rooster=False):
    """A hen or a rooster scratching and pecking in a courtyard."""
    m = Model.empty(-6, 7, -4, 4, 0, 9, k=k)
    bd = Body(m, rot=np.eye(3) / 1.4)
    peck = anim == "peck" and frame % 2 == 1
    coat = "orange" if rooster else "wool"
    bd.blob((0, 0, 2.0), (1.6, 1.0, 1.1), coat, 0.1)
    hz = 3.2 - (1.4 if peck else 0.0)
    bd.blob((1.2, 0, hz), (0.6, 0.55, 0.6), coat, 0.2)
    bd.limb((1.6, 0, hz + 0.6), (1.0, 0, hz + 0.9), 0.3, "cinnabar")
    bd.limb((1.7, 0, hz - 0.1), (2.2, 0, hz - 0.3), 0.15, "yellow")
    bd.limb((-1.4, 0, 2.4), (-2.4, 0, 3.6 if rooster else 3.0), 0.5, "malachite" if rooster else coat, 0.1)
    for y in (0.35, -0.35):
        bd.limb((0.2, y, 1.0), (0.2 + (0.4 if anim == "move" and frame % 2 else 0), y, 0.0), 0.12, "yellow")
    return m


BIRDS = {"athens.owl": owl, "athens.hen": hen, "athens.rooster": lambda a, f, n, k: hen(a, f, n, k, rooster=True)}
CRITTERS = {**{k_: None for k_ in BEASTS}, **BIRDS}


def horse_mount(b0: Body, phase: float):
    """A frieze horse under a rider (a callable rig mount): returns the saddle height."""
    beast = BEASTS["athens.horse"]
    sub = quadruped(beast, "move", int(phase * 6) % 6, 6, b0.m.k)
    paste(b0.m, sub, 0.0, 0.0, 0.0)
    return beast.height * SIZE + 1.0


# ---------------------------------------------------------------- ships

def ship_model(kind, anim, frame, k):
    """Ships at s = 0.5 with their crews as dots: `move` under sail, `slack` sail hanging,
    `row` the oars sweeping, `idle` moored with the sail furled."""
    m = Model.empty(-50, 52, -18, 18, 0, 70, k=k)
    t = frame / 4
    if kind == "athens.trireme":
        L, beam = 84.0, 5.5
        hull(m, -L / 2, L / 2, 0.0, 0.0, beam=beam, depth=5.0)
        # Rowers' heads in the outrigger, oars in three banks.
        for x in np.arange(-L / 2 + 16, L / 2 - 14, 2.2):
            for s in (1, -1):
                ellipsoid(m, (x, s * (beam - 0.8), 5.6), (0.5, 0.5, 0.5), "skin_tan", tone=0.1)
        if anim == "row":
            sweep = math.sin(t * 2 * math.pi) * 2.0
            for x in np.arange(-L / 2 + 16, L / 2 - 14, 2.2):
                for s in (1, -1):
                    rod(m, (x, s * (beam + 1.0), 4.4), (x - sweep, s * (beam + 9.0), 0.4), 0.18, "wood_light")
        mast = anim in ("move", "slack")
        if mast:
            rod(m, (4.0, 0.0, 5.0), (4.0, 0.0, 44.0), 0.6, "wood")
            rod(m, (4.0, -12.0, 42.0), (4.0, 12.0, 42.0), 0.45, "wood")
            belly = 3.0 + 0.6 * math.sin(t * 2 * math.pi) if anim == "move" else 0.6
            fill(m, (0.0, 12.0, -12.0, 12.0, 20.0, 42.0), "linen",
                 lambda X, Y, Z: np.abs(X - (4.0 + belly * np.clip(1 - (Y / 12.0) ** 2, 0, 1) *
                                              np.clip(1 - ((Z - 31) / 11.0) ** 2, 0, 1))) < 0.45,
                 tone=lambda X, Y, Z: 0.3 * ((Y % 6.0) < 0.6) - 0.1)
        else:
            rod(m, (-20.0, 0.0, 6.0), (24.0, 0.0, 6.5), 0.6, "wood")               # mast lowered on deck
            rod(m, (-14.0, 0.5, 7.0), (18.0, 0.5, 7.2), 1.0, "linen", tone=0.1)
        rod(m, (-L / 2 + 4, 4.5, 4.0), (-L / 2 - 2, 6.0, 0.0), 0.5, "wood")          # steering oars
        rod(m, (-L / 2 + 4, -4.5, 4.0), (-L / 2 - 2, -6.0, 0.0), 0.5, "wood")
    elif kind == "athens.merchant":
        L = 52.0

        def half(X):
            tt = np.clip((X + L / 2) / L, 0, 1)
            return 8.0 * np.sin(np.pi * tt) ** 0.6 + 0.4

        fill(m, (-L / 2, L / 2, -9, 9, 0.0, 9.0), "wood",
             lambda X, Y, Z: (np.abs(Y) < half(X)) & (Z > 2.0 * (Y / 8.0) ** 2) &
             (Z < 7.0 + 2.0 * ((X + L / 2) / L - 0.5) ** 2 * 8),
             tone=lambda X, Y, Z: -0.4 * ((Z % 1.6) < 0.4) + 0.1)
        fill(m, (-L / 2 + 4, L / 2 - 4, -7, 7, 6.0, 7.0), "wood_light", lambda X, Y, Z: np.abs(Y) < half(X) - 1.0, tone=0.2)
        for i in range(6):
            from greek import vase
            vase(m, -12.0 + i * 4.0, (-1) ** i * 2.0, 7.0, 4.0, "transport", figure="plain")
        rod(m, (-L / 2 + 1, 0, 8.0), (-L / 2 - 4, 0, 16.0), 0.6, "wood")              # the stern post curving up
        rod(m, (-L / 2 + 6, 7.0, 8.0), (-L / 2 - 1, 8.0, 0.0), 0.5, "wood")
        sail = anim != "idle"
        rod(m, (0.0, 0.0, 7.0), (0.0, 0.0, 46.0 if sail else 30.0), 0.6, "wood")
        if sail:
            belly = 3.5 if anim == "move" else 0.6
            fill(m, (-3.0, 10.0, -14.0, 14.0, 18.0, 44.0), "cream",
                 lambda X, Y, Z: np.abs(X - belly * np.clip(1 - (Y / 14.0) ** 2, 0, 1) *
                                         np.clip(1 - ((Z - 31) / 13.0) ** 2, 0, 1)) < 0.45,
                 tone=lambda X, Y, Z: 0.3 * ((Z % 4.0) < 0.5) - 0.1)
            rod(m, (0.0, -14.0, 44.0), (0.0, 14.0, 44.0), 0.45, "wood")
        else:
            rod(m, (0.0, -10.0, 28.0), (0.0, 10.0, 28.0), 0.9, "cream", tone=0.1)
        if anim == "row":
            for x in (-6.0, 4.0, 14.0):
                for s in (1, -1):
                    rod(m, (x, s * 7.0, 6.0), (x - 2.0 * math.sin(t * 6.28), s * 13.0, 0.5), 0.2, "wood_light")
    else:   # a fishing boat with a fisherman casting his net
        L = 24.0
        fill(m, (-L / 2, L / 2, -5, 5, 0.0, 4.0), "eblue",
             lambda X, Y, Z: (np.abs(Y) < 4.0 * np.sin(np.pi * np.clip((X + L / 2) / L, 0, 1)) ** 0.7 + 0.3) &
             (Z > 1.5 * (Y / 4.0) ** 2), tone=lambda X, Y, Z: 0.3 * (Z > 3.4) - 0.1)
        fill(m, (-L / 2 + 2, L / 2 - 2, -3, 3, 3.0, 3.6), "wood_light", tone=0.1)
        d = Dress(garment="exomis", colour="wool", beard="full", hair_style="short", head="pilos", head_mat="felt",
                  feet="bare", skin="skin_olive")
        fr = Frame(d)
        p = pose("haul" if anim == "row" else "idle", frame % (4 if anim == "row" else 2), 4 if anim == "row" else 2,
                 fr, d)
        draw(Body(m, shift=(2.0, 0.0, 3.0)), d, p, fr)
        if anim in ("move", "slack"):
            rod(m, (-2.0, 0.0, 3.0), (-2.0, 0.0, 22.0), 0.4, "wood")
            fill(m, (-6.0, 4.0, -7.0, 7.0, 8.0, 21.0), "linen",
                 lambda X, Y, Z: np.abs(X - (-2.0 + (2.0 if anim == "move" else 0.4) * (1 - (Y / 7.0) ** 2))) < 0.4,
                 tone=0.0)
    return m


SHIPS = {"athens.trireme", "athens.merchant", "athens.fishing"}


# ---------------------------------------------------------------- carts

DRIVER = Dress(garment="exomis", colour="wool", beard="full", hair_style="short", head="petasos", head_mat="straw",
               feet="bare", skin="skin_olive", hand_l="staff")


def _driver(m, x, y, dress, anim, frame):
    fr = Frame(dress)
    a = "move" if anim == "move" else "idle"
    p = pose(a, frame * 6 // 4 if a == "move" else frame % 2, 6 if a == "move" else 2, fr, dress)
    draw(Body(m, shift=(x, y, 0.0)), dress, p, fr)


def cart_model(kind, variant, anim, frame, k):
    """Carts with their teams and drivers baked in (world-tech.md §1.9)."""
    turn = frame / 4 * (math.pi / 3) if anim == "move" else 0.0
    f6 = frame * 6 // 4
    team = "move" if anim == "move" else "idle"
    tf, tn = (f6 % 6, 6) if team == "move" else (frame % 2, 2)
    m = Model.empty(-46, 42, -16, 16, 0, 48, k=k)
    if kind == "athens.cart":
        # A heavy two-wheeled cart behind a yoke of oxen: a marble block from the quarry (v0),
        # transport amphorae (v1) or sacks of grain from Piraeus (v2).
        for y in (-5.0, 5.0):
            m = _merge(m, quadruped(BEASTS["athens.ox"], team, tf, tn, k), 18.0, y)
        rod(m, (14.0, -8, 13.5), (14.0, 8, 13.5), 0.9, "wood")
        rod(m, (14.0, 0, 13.0), (-12.0, 0, 9.5), 0.8, "wood")
        bd = Body(m)
        slab(m, -36, -12, -7, 7, 8.5, 10.0, "wood_light", tone=0.2)
        for y in (-8.4, 8.4):
            _wheel(bd, -24, 7.5, 7.2, y, turn, "wood")
        if variant == 0:
            slab(m, -33, -15, -5.5, 5.5, 10.0, 18.0, "marble", tone=0.3)
            rod(m, (-24, -6, 18.2), (-24, 6, 18.2), 0.3, "straw")
        elif variant == 1:
            from greek import vase
            for i in range(6):
                vase(m, -32.0 + (i % 3) * 7.0, -3.0 + (i // 3) * 6.0, 10.0, 6.5, "transport", figure="plain")
        else:
            for i, (x, y) in enumerate(((-31, -3), (-25, 3), (-19, -2), (-28, 2), (-21, 3))):
                ellipsoid(m, (x, y, 13.0 + (i // 3) * 3.0), (3.2, 2.6, 2.6), "straw", tone=0.1 * i)
        _driver(m, 16.0, 12.0, DRIVER, anim, frame)
    elif kind == "athens.sledge":
        # A marble block lashed on a wooden sledge, eased down the quarry road on ropes over
        # rollers, the brakemen walking behind.
        slab(m, -16, 16, -8, 8, 2.0, 4.5, "wood_light", tone=0.2)
        for x in (-12.0, -2.0, 8.0):
            rod(m, (x + (frame % 2) * 1.2, -9, 1.2), (x + (frame % 2) * 1.2, 9, 1.2), 1.2, "wood")
        slab(m, -12, 12, -6, 6, 4.5, 14.0, "marble", tone=0.3)
        for y in (-4.0, 4.0):
            rod(m, (-16.0, y, 4.0), (-34.0, y * 1.5, 9.0), 0.3, "straw", tone=0.2)
        _driver(m, -36.0, 6.0, DRIVER, anim, frame)
        _driver(m, -30.0, -7.0, DRIVER, anim, (frame + 2) % 4)
    else:
        # The procession chariot (the apobates race): a light car on two wheels behind a pair of
        # horses, the charioteer in a long white chiton holding the reins.
        for y in (-4.5, 4.5):
            m = _merge(m, quadruped(BEASTS["athens.horse"], team, tf, tn, k), 18.0, y)
        bd = Body(m)
        rod(m, (8.0, 0, 14.0), (-12.0, 0, 10.0), 0.7, "wood")
        slab(m, -22, -12, -5.5, 5.5, 8.0, 9.0, "wood", tone=0.2)
        fill(m, (-22, -12, -6, 6, 9.0, 15.0), "cinnabar", lambda X, Y, Z: (np.abs(Y) > 4.8) | (X > -13.0), tone=0.2)
        for y in (-6.6, 6.6):
            _wheel(bd, -17, 7.5, 7.4, y, turn, "wood")
        d = Dress(garment="chiton_long", colour="whitewash", beard="none", hair="cedar", hair_style="short",
                  feet="bare", skin="skin_tan", hold="front")
        fr = Frame(d)
        p = pose("idle", frame % 2, 2, fr, d)
        draw(Body(m, shift=(-16.0, 0.0, 9.0)), d, p, fr)
    return m


CARTS = {"athens.cart", "athens.sledge", "athens.chariot"}


def sprite(kind, variant, anim, facing, frame, k):
    if kind in CARTS:
        return _render(cart_model(kind, variant or 0, anim, frame, k), facing)
    if kind in SHIPS:
        return _render(ship_model(kind, anim, frame, k), facing)
    frames = {"move": 6, "idle": 2, "graze": 4, "peck": 4, "sleep": 2, "flap": 4}[anim]
    if kind in BIRDS:
        return _render(BIRDS[kind](anim, frame, frames, k), facing)
    return _render(quadruped(BEASTS[kind], anim, frame, frames, k), facing)
