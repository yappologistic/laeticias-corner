"""The travelling themes: music for the land and sea between the cities (world set).

Five lands and the sea, each a day piece and its night arrangement of the same bars (the engine
plays the two together, sample-aligned, and cross-fades them by the clock). Sparse on purpose:
each loop is four phrase groups, and every group opens with a bar of breath and ends in rests,
so the music sounds a little under half the time and the land's own beds carry the rest of a
journey. A group's first bar is where the engine may start the piece (its phrase starts).

All six share the cities' seven-note set (the white notes: Rome's F, Athens's E and Pārsa's D
modes are all on it), so no two neighbours can clash at a border; each land has its own final
and melodic shape:

| piece | final | tempo | voices (day / night) |
|---|---|---|---|
| italy | D (D E G A B core; F and C passing) | 56, 4/4 | syrinx + lyre / tibia + lyre |
| greece | E (Dorian species, falling A G F E) | 60, 6/4 dactyls | lyra + syrinx / barbitos + aulos |
| sea | A (the mese, A–E drone) | 48, 4/4 rubato | aulos and drone pipe / hummed voices, a lyre |
| levant | G (G A B C D E F) | 60, 4/4 | lyre + double pipe, a frame drum / lute + pipe |
| mesopotamia | C (C–C), dyads | 60, 3/4 | harp dyads + lute ostinato / harp + hummed drone |
| iran | D (Pārsa's mode, motif D E F A) | 60, 4/4 | angular harp + double pipe / harp + hummed voices |

The Italian theme leans on D E A B, the notes it shares with the home's D lydian, and lands on
the home's own final D, so the corner and its country meet without a clash."""

import score

# --- Italy: a shepherd's syrinx on the hills, a traveller's lyre answering --------------------

ITALY_BARS = 40
ITALY_SYRINX = {
    2: "D5/1.5 E5/0.5 A5/2", 3: "G5/1 E5/0.5 D5/0.5 E5/2", 4: "A5/1 B5/1 A5/0.5 G5/0.5 E5/1",
    5: "D5/3 r/1", 6: "E5/1 G5/1 A5/1.5 B5/0.5", 7: "A5/1 G5/1 E5/1 G5/1", 8: "D5/4",
    16: "r/1 D6/1.5 B5/0.5 A5/1", 17: "G5/1 E5/1 D5/2",
    22: "A5/0.5 B5/0.5 D6/2 B5/1", 23: "A5/1 G5/0.5 A5/0.5 B5/2", 24: "A5/1 G5/1 E5/1 D5/1",
    25: "E5/2 G5/2", 26: "A5/4",
    32: "D5/1.5 E5/0.5 A5/2", 33: "G5/1 E5/1 D5/2",
}
ITALY_LYRE = {
    5: "D4+A4/4", 9: "r/2 E4/1 A4/1", 10: "D4/4",
    12: "D4/1 E4/1 G4/1.5 A4/0.5", 13: "B4/2 A4/1 G4/1", 14: "E4/1 G4/1 A4/2", 15: "D4/4",
    18: "D3+A3/4", 24: "C4+G4/4", 27: "A3+E4/4",
    34: "A4/1 G4/1 E4/1 G4/1", 35: "D4/4", 36: "D3+A3/4",
}
ITALY = {
    "bpm": 56, "meter": [4], "phrase": 40, "tail": 8.0,
    "reverb": (3.0, 2.2, 1.2, 0.04),  # open hillside: a long, soft, distant tail
    "wet": 0.9,
    "parts": {
        "syrinx": {"voice": "syrinx", "notes": score.sparse([4], ITALY_BARS, ITALY_SYRINX),
                   "gain": 0.8, "pan": 0.2, "send": 0.45, "vel": 0.8, "jitter": 0.012},
        "lyre": {"voice": "lyra", "notes": score.sparse([4], ITALY_BARS, ITALY_LYRE),
                 "gain": 2.57, "pan": -0.25, "spread": 0.3, "send": 0.35, "ring": 5.0,
                 "vel": 0.7, "strum": 0.05},
    },
}
ITALY_NIGHT = score.nocturne(ITALY, {
    "syrinx": {"voice": "tibia", "octave": -12, "gain": 0.0525, "send": 0.8, "vel": 0.6,
               "legato": True},
    "lyre": {"gain": 0.75, "ring": 7.0, "vel": 0.55, "send": 0.5},
})

# --- Greece and the Aegean shore: a lyra in dactyls, Pan's pipes from the hills ---------------

GREECE_BARS = 32
GREECE_LYRA = {
    2: "E4/2 A4/1 B4/1 C5/2", 3: "B4/2 A4/1 G4/1 A4/2", 4: "E5/4 D5/2", 5: "C5/2 B4/1 A4/1 B4/2",
    6: "A4/2 G4/1 F4/1 E4/2", 7: "E3+B3/6",
    13: "E3+B3/6", 14: "A4/2 G4/1 F4/1 E4/2",
    18: "A4/2 C5/1 D5/1 E5/2", 19: "D5/2 C5/1 B4/1 C5/2", 20: "A4/4 r/2",
    26: "E4/2 A4/1 B4/1 E5/2", 27: "D5/2 C5/1 B4/1 A4/2", 28: "G4/2 F4/1 G4/1 E4/2",
    29: "E4/6", 30: "E3+B3/6",
}
GREECE_SYRINX = {
    7: "r/3 E5/1 G5/1 A5/1", 8: "B5/2 A5/1 G5/1 E5/2",
    10: "A5/2 B5/1 C6/1 B5/2", 11: "A5/2 G5/1 E5/1 G5/2", 12: "A5/6",
    22: "E5/2 D5/1 C5/1 B4/2", 23: "A4/6",
}
GREECE = {
    "bpm": 60, "meter": [6], "phrase": 48, "tail": 8.0,
    "reverb": (2.8, 2.0, 1.1, 0.035),  # a valley among olive terraces
    "wet": 0.9,
    "parts": {
        "lyra": {"voice": "lyra", "notes": score.sparse([6], GREECE_BARS, GREECE_LYRA),
                 "gain": 1.0, "pan": -0.15, "spread": 0.35, "send": 0.35, "ring": 5.0,
                 "vel": 0.75, "strum": 0.05},
        "syrinx": {"voice": "syrinx", "notes": score.sparse([6], GREECE_BARS, GREECE_SYRINX),
                   "gain": 0.183, "pan": 0.35, "send": 0.6, "vel": 0.75, "jitter": 0.012},
    },
}
GREECE_NIGHT = score.nocturne(GREECE, {
    "lyra": {"voice": "barbitos", "gain": 1.0, "ring": 8.0, "vel": 0.6},
    "syrinx": {"voice": "aulos", "octave": -12, "gain": 0.0784, "send": 0.9, "vel": 0.55,
               "legato": True},
})

# --- The sea lanes: the ship's piper over a held drone; at night the rowers hum ---------------

SEA_BARS = 36
SEA_AULOS = {
    2: "E4/2 A4/2", 3: "B4/1 C5/1 B4/2", 4: "A4/4", 5: "G4/2 E4/2", 6: "A4/4",
    11: "C5/2 D5/1 E5/1", 12: "D5/2 C5/2", 13: "B4/2 A4/1 G4/1", 14: "A4/4",
    20: "E5/4", 21: "D5/2 E5/2", 22: "A4/8",
    29: "E4/2 A4/2", 30: "B4/1 C5/1 B4/1 G4/1", 31: "A4/8",
}
SEA_DRONE = {2: "A3/20", 11: "A3/16", 20: "E3/16", 29: "A3/16"}
SEA = {
    "bpm": 48, "meter": [4], "phrase": 36, "rubato": (0.25, 36), "tail": 9.0,
    "reverb": (3.5, 2.6, 1.4, 0.05),  # open water: a wide, far tail
    "wet": 1.0,
    "parts": {
        "aulos": {"voice": "aulos", "notes": score.sparse([4], SEA_BARS, SEA_AULOS),
                  "gain": 0.5, "pan": 0.1, "send": 0.6, "vel": 0.7, "legato": True},
        "drone": {"voice": "aulos", "notes": score.sparse([4], SEA_BARS, SEA_DRONE),
                  "gain": 0.141, "pan": -0.2, "send": 0.7, "vel": 0.6, "legato": True},
    },
}
SEA_NIGHT = score.nocturne(SEA, {
    "aulos": {"voice": "hum", "vowel": "o", "voices": 3, "octave": -12, "gain": 0.9,
              "send": 0.6, "vel": 0.7},
    # A lyre on deck sounds each phrase's first long note and its close, high over the hum.
    "lyre": {"voice": "lyra", "gain": 1.2, "pan": -0.3, "spread": 0.3, "send": 0.5, "ring": 7.0,
             "vel": 0.55, "strum": 0.06, "notes": score.sparse([4], SEA_BARS, {
                 2: "A3+E4/4", 4: "A4/4", 6: "E4+A4/4", 11: "C5/4", 14: "A4/4", 20: "E4+B4/4",
                 22: "A3+E4/4", 29: "A3+E4/4", 31: "A4/4"})},
    "drone": {"voice": "hum", "vowel": "m", "voices": 3, "octave": -12, "gain": 0.27,
              "send": 0.7, "vel": 0.6},
})

# --- Anatolia and the Levant: a lyre (the kinnor of the coast), the Phrygian double pipe ------

LEVANT_BARS = 40
LEVANT_PIPE = {
    2: "G4/1 A4/1 B4/2", 3: "D5/1.5 C5/0.5 B4/1 A4/1", 4: "B4/2 G4/2", 5: "F4/1 G4/1 A4/2",
    6: "G4/4", 17: "D5/2 B4/2", 18: "G4/4",
    23: "B4/1 C5/1 D5/2", 24: "C5/1 B4/1 A4/2", 25: "B4/1 A4/1 G4/1 F4/1", 26: "G4/4",
}
LEVANT_DRONE = {2: "G3/20", 17: "G3/8", 23: "G3/16"}
LEVANT_LYRE = {
    7: "D4+G4/2 B4/1 A4/1", 8: "G4/4",
    12: "G4/1 B4/1 D5/1 E5/1", 13: "F5/2 E5/1 D5/1", 14: "C5/1 B4/1 A4/2", 15: "B4/1 A4/1 G4/2",
    32: "G4/1 A4/1 B4/2", 33: "D5/2 C5/1 B4/1", 34: "A4/2 F4/1 A4/1", 35: "G4/4",
    36: "G3+D4/4",
}
LEVANT_DRUM = {b: "D/1 k/1? T/1 k/1?" for b in range(22, 28)}
LEVANT = {
    "bpm": 60, "meter": [4], "phrase": 40, "tail": 8.0,
    "reverb": (2.6, 1.8, 1.0, 0.03),  # a caravan road between rock and steppe
    "wet": 0.85,
    "parts": {
        "pipe": {"voice": "pipe", "notes": score.sparse([4], LEVANT_BARS, LEVANT_PIPE),
                 "gain": 0.45, "pan": 0.2, "send": 0.45, "vel": 0.75},
        "drone": {"voice": "pipe", "notes": score.sparse([4], LEVANT_BARS, LEVANT_DRONE),
                  "gain": 0.147, "pan": 0.3, "send": 0.5, "vel": 0.6, "legato": True},
        "lyre": {"voice": "lyra", "notes": score.sparse([4], LEVANT_BARS, LEVANT_LYRE),
                 "gain": 3.57, "pan": -0.25, "spread": 0.3, "send": 0.35, "ring": 5.0,
                 "vel": 0.75},
        "drum": {"voice": "drum", "notes": score.sparse([4], LEVANT_BARS, LEVANT_DRUM),
                 "gain": 0.494, "pan": -0.4, "send": 0.4, "tune": 88.0, "vel": 0.55},
    },
}
LEVANT_NIGHT = score.nocturne(LEVANT, {
    "pipe": {"gain": 0.0314, "send": 0.85, "vel": 0.6},
    "drone": {"gain": 0.0112, "send": 0.9},
    "lyre": {"voice": "lute", "gain": 0.8, "ring": 3.5, "vel": 0.6},
    "drum": None,
})

# --- Mesopotamia: harp dyads over a long-necked lute, by the rivers ---------------------------

MESO_BARS = 56
LUTE_WALK = "C3/1 G3/1 C4/1"
MESO_HARP = {
    3: "C4+G4/2 E4/1", 4: "F4/1 E4/1 D4/1", 5: "E4+A4/2 G4/1", 6: "C4+G4/3",
    7: "A4/1 G4/1 E4/1", 8: "F4/1 E4/1 D4/1", 9: "C4/3",
    16: "G4/1 A4/1 C5/1", 17: "D5/2 C5/1", 18: "A4+E5/3", 19: "G4/1 E4/1 G4/1",
    20: "A4/2 G4/1", 21: "E4+C5/3",
    34: "C4+G4/3",
    44: "C4+G4/2 E4/1", 45: "F4/1 E4/1 D4/1", 46: "E4+A4/2 G4/1", 47: "D4+A4/3",
    48: "B3/1 C4/1 D4/1", 49: "C4+G4/3",
}
MESO_LUTE = {
    **{b: LUTE_WALK for b in (2, 3, 4, 5, 6, 7, 8)}, 10: "C3/3",
    **{b: LUTE_WALK for b in (16, 17, 19, 20)}, 18: "A2/1 E3/1 A3/1", 21: "C3/3",
    30: "C4/1 D4/1 E4/1", 31: "G4/2 E4/1", 32: "D4/1 C4/1 D4/1", 33: "E4/3",
    **{b: LUTE_WALK for b in (44, 45, 46, 48)}, 47: "D3/1 A3/1 D4/1", 49: "C3/3",
}
MESOPOTAMIA = {
    "bpm": 60, "meter": [3], "phrase": 42, "tail": 8.0,
    "reverb": (2.4, 1.6, 0.9, 0.025),  # a mud-brick courtyard by the river
    "wet": 0.85,
    "parts": {
        "harp": {"voice": "harp", "notes": score.sparse([3], MESO_BARS, MESO_HARP),
                 "gain": 1.0, "pan": -0.15, "spread": 0.35, "send": 0.35, "ring": 6.0,
                 "vel": 0.75, "strum": 0.06},
        "lute": {"voice": "lute", "notes": score.sparse([3], MESO_BARS, MESO_LUTE),
                 "gain": 1.38, "pan": 0.3, "send": 0.3, "ring": 2.5, "vel": 0.6},
    },
}
MESOPOTAMIA_NIGHT = score.nocturne(MESOPOTAMIA, {
    "harp": {"gain": 0.85, "ring": 8.0, "vel": 0.6, "send": 0.45},
    "lute": None,
    "hum": {"voice": "hum", "vowel": "m", "voices": 3, "gain": 0.128, "pan": 0.0, "send": 0.6,
            "vel": 0.6, "notes": score.sparse([3], MESO_BARS, {
                2: "C3+G3/27", 16: "C3+G3/18", 30: "C3+G3/15", 44: "C3+G3/24"})},
})

# --- The Iranian plateau: Pārsa's harp on the high road, a far double pipe --------------------

IRAN_BARS = 40
IRAN_HARP = {
    2: "D4/1 E4/1 F4/1 A4/1", 3: "G4/2 F4/1 E4/1", 4: "F4/1.5 E4/0.5 D4/2", 5: "A3+E4/4",
    12: "A4/1 C5/1 D5/2", 13: "C5/1 A4/1 G4/1 A4/1", 14: "F4/2 E4/1 F4/1", 15: "D4/4",
    25: "D3+A3/2 F4/1 E4/1", 26: "D4/4",
    32: "D4/1 E4/1 F4/1 A4/1", 33: "B4/2 A4/1 G4/1", 34: "A4/1 G4/1 F4/1 E4/1", 35: "D4/4",
    36: "D3+A3/4",
}
IRAN_PIPE = {
    7: "A4/2 G4/1 F4/1", 8: "E4/2 D4/2", 17: "D5/4", 18: "C5/2 A4/2",
    22: "D4/1 E4/1 F4/2", 23: "G4/1 F4/1 E4/2", 24: "D4/4",
}
IRAN = {
    "bpm": 60, "meter": [4], "phrase": 40, "tail": 8.0,
    "reverb": (3.2, 2.2, 1.2, 0.04),  # the high plain under the mountains
    "wet": 0.9,
    "parts": {
        "harp": {"voice": "harp", "notes": score.sparse([4], IRAN_BARS, IRAN_HARP),
                 "gain": 1.0, "pan": -0.1, "spread": 0.35, "send": 0.35, "ring": 6.0,
                 "vel": 0.75, "strum": 0.05},
        "pipe": {"voice": "pipe", "notes": score.sparse([4], IRAN_BARS, IRAN_PIPE),
                 "gain": 0.117, "pan": 0.35, "send": 0.7, "vel": 0.7},
    },
}
IRAN_NIGHT = score.nocturne(IRAN, {
    "harp": {"gain": 0.85, "ring": 8.0, "vel": 0.6, "send": 0.45},
    "pipe": {"voice": "hum", "vowel": "o", "voices": 3, "gain": 0.175, "send": 0.7, "vel": 0.6},
})

PIECES = {"italy": (ITALY, ITALY_NIGHT), "greece": (GREECE, GREECE_NIGHT), "sea": (SEA, SEA_NIGHT),
          "levant": (LEVANT, LEVANT_NIGHT), "mesopotamia": (MESOPOTAMIA, MESOPOTAMIA_NIGHT),
          "iran": (IRAN, IRAN_NIGHT)}

WHERE = {
    "italy": "the Italian countryside and hills: Latium, the Apennines",
    "greece": "Greece and the Aegean's shores: Greece, Arcadia, northern Attica, Thrace, Ionia",
    "sea": "the sea lanes: the Tyrrhenian, Adriatic, Ionian, Saronic and Aegean seas, the Gulf",
    "levant": "Anatolia and the Levant: Anatolia, the Taurus, the coast of Syria, the steppe",
    "mesopotamia": "between the rivers: Mesopotamia and Susiana",
    "iran": "the Iranian plateau and the Zagros",
}
VOICES = {
    "italy": ("a syrinx with a lyre answering", "the tune on a far tibia, the lyre ringing"),
    "greece": ("a lyra in dactyls, Pan's pipes from the hills", "a barbitos, a far aulos"),
    "sea": ("the ship's piper on the aulos over a held drone", "the rowers humming the tune"),
    "levant": ("a lyre, the double pipe and a frame drum's walk", "a long-necked lute, far pipes"),
    "mesopotamia": ("harp dyads over a long-necked lute", "the harp over a hummed drone"),
    "iran": ("an angular harp, a far double pipe", "the harp over hummed women's voices"),
}


def renderer(piece):
    return lambda rng: score.render(piece, rng)


FILES = {}
for land, (day_piece, night_piece) in PIECES.items():
    for piece in (day_piece, night_piece):
        piece["blocks"] = True  # three minutes long: reverb a block at a time
        for part in piece["parts"].values():
            part["phrases"] = True  # reeds breathe in the long rests: rendered phrase by phrase
    for when, piece, voices in (("day", day_piece, VOICES[land][0]),
                                ("night", night_piece, VOICES[land][1])):
        FILES[f"music/world/travel_{land}_{when}.ogg"] = dict(
            kind="music", render=renderer(piece), piece=piece, lufs=-18.0, quality=2, gain=0.5,
            ceiling=-2.0, when=when, where=WHERE[land],
            purpose=f"Travelling theme, {when}: {voices}; sparse, the land's beds carry the rests.")
