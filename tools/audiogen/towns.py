"""Town pieces: short loops for the Roman, Greek and Persian towns, each built from its
capital's material (mode, final, motif, instruments) so a town sounds related to its city,
in a few pieces per family so that neighbouring towns never share one. Each is a day piece
and its night arrangement of the same bars (the engine plays the two together, sample-aligned,
and cross-fades them by the clock). Lighter than the capitals' pieces: two or three voices,
rests between the phrases, and the last bars left to the town's own sound.

| family | piece | towns | final, tempo | voices (day; night) |
|---|---|---|---|---|
| Roman (Rome's F mode, motif F A C) | forum | Ostia, Capua | F, 84, bars of 3 and 4 | cithara, tibia, frame drum; lyre, far tibia |
| | hills | Tibur, Beneventum | F, 56 | syrinx, lyre; far syrinx, barbitos |
| | shrine | Alban Mount, Brundisium | F, 56, rubato | tibia, cithara; far tibia, lyre |
| Greek (Athens's E Dorian, motif E A B E) | polis | Corinth, Olympia, Ephesus | E, 90, 6/4 dactyls | kithara, aulos, krotala; barbitos, far aulos |
| | march | the Academy, Sparta | E, 90 | aulos with its drone pipe, lyra, frame drum; far aulos, barbitos |
| | sanctuary | Delphi, Delos | E (mese A), 60, rubato | kithara, a far aulos; barbitos |
| | harbour | Eleusis, Corcyra | E, 90, a lilting 3 | lyra, aulos; barbitos, far aulos |
| Persian (Pārsa's D mode, motif D E F A) | court | Susa, Pasargadae | D, 80 | angular harp, lute; harp, hummed drone |
| | caravan | the Persian Gates, Halys | D, 80 | double pipe with drone, frame drum walk; lute, hummed drone |
| | west | Sardis, Sidon | D, 80, triplet lilt | lyre, double pipe; barbitos, far pipe |
| | river | Babylon, the Euphrates crossing, Gordion | D, 60, 3/4 | lute, harp dyads; harp, hummed drone |"""

import score


def piece(bpm, meter, bars, phrase, reverb, parts, **extra):
    """A town piece: each part's notes given as {bar: tokens}, the other bars resting. Phrases
    begin every `phrase` beats or at the listed beats; the engine may start the piece a beat
    before any of them (its fade-in then lands on the phrase's first note), and the file
    itself starts a beat before the first bar, in the closing rest, so its seam falls in quiet."""
    total = sum(meter[i % len(meter)] for i in range(bars))
    starts = range(0, total, phrase) if isinstance(phrase, int) else phrase
    return {"bpm": bpm, "meter": meter, "phrase": [(b - 1) % total for b in starts],
            "offset": total - 1, "tail": 7.0, "reverb": reverb, "blocks": True, **extra,
            "parts": {name: {**p, "notes": score.sparse(meter, bars, p["notes"]),
                             "phrases": True}
                      for name, p in parts.items()}}


def hum(notes, bars, meter, gain=0.06):
    """A night drone of three hummed voices."""
    return {"voice": "hum", "vowel": "m", "voices": 3, "notes": score.sparse(meter, bars, notes),
            "gain": gain, "pan": 0.0, "send": 0.6, "vel": 0.6}


# --- Roman towns --------------------------------------------------------------------------------

FORUM = piece(84, [3, 4], 24, 14, (2.6, 2.0, 1.2, 0.025), {  # a small town's colonnaded forum
    "cithara": {"voice": "cithara", "gain": 1.0, "pan": -0.1, "spread": 0.4, "send": 0.3,
                "ring": 4.0, "vel": 0.8, "notes": {
                    1: "F4/1 A4/1 C5/1", 2: "E5/2 D5/1 C5/1", 3: "D5/2 B4/1",
                    4: "C5/1.5 A4/0.5 G4/2", 5: "A4/1 C5/1 D5/1", 6: "C5/2 A4/1 G4/1",
                    7: "A4/2 G4/1", 8: "F4/4", 13: "F4/1 G4/1 A4/1", 14: "B4/2 A4/1 G4/1",
                    15: "A4/2 C5/1", 16: "D5/4", 17: "C5/1 B4/1 A4/1", 18: "G4/2 A4/1 B4/1",
                    19: "C5/2 A4/1", 20: "F4/4"}},
    "tibia": {"voice": "tibia", "gain": 0.105, "pan": 0.25, "send": 0.35, "vel": 0.75, "notes": {
        9: "C5/1 D5/1 E5/1", 10: "F5/2 E5/1 C5/1", 11: "D5/2 B4/1", 12: "C5/4",
        17: "C5/3", 18: "G4/2 B4/2", 19: "C5/2 A4/1", 20: "F4/4"}},
    "low": {"voice": "cithara", "gain": 0.374, "pan": -0.25, "send": 0.3, "ring": 4.0,
            "strum": 0.04, "vel": 0.6, "notes": {
                1: "F3+C4/3", 5: "F3+C4/3", 8: "F3+C4/4", 9: "C3+G3/3", 12: "C3+G3/4",
                13: "F3+C4/3", 16: "G3+D4/4", 17: "F3+C4/3", 20: "F3+C4/4"}},
    "drum": {"voice": "drum", "gain": 0.167, "pan": -0.35, "send": 0.35, "tune": 84.0,
             "vel": 0.65, "notes": {b: ("D/1 k/1? k/1?" if b % 2 else "D/1 k/1? T/1 k/1?")
                                    for b in range(13, 21)}},
})
FORUM_NIGHT = score.nocturne(FORUM, {
    "cithara": {"voice": "lyra", "gain": 0.9, "vel": 0.6, "ring": 6.0, "send": 0.4},
    "tibia": {"gain": 0.0242, "send": 0.85, "vel": 0.6},
    "low": {"voice": "lyra", "gain": 0.291, "vel": 0.5},
    "drum": None,
})

HILLS = piece(56, [4], 20, [0, 40], (2.8, 2.0, 1.1, 0.035), {  # a hill town above its valley
    "syrinx": {"voice": "syrinx", "gain": 0.75, "pan": 0.2, "send": 0.45, "vel": 0.8,
               "jitter": 0.012, "notes": {
                   2: "C5/1 F5/1 G5/1.5 A5/0.5", 3: "G5/1 F5/1 D5/2", 4: "C5/1 D5/1 F5/1 G5/1",
                   5: "A5/3 r/1", 8: "C6/1 A5/1 G5/1 F5/1", 9: "G5/2 A5/2", 10: "F5/4",
                   15: "F5/1 G5/1 A5/1 C6/1", 16: "B5/1 A5/1 G5/2", 17: "A5/2 F5/2",
                   18: "G5/1 F5/1 D5/1 C5/1", 19: "F5/4"}},
    "lyre": {"voice": "lyra", "gain": 2.57, "pan": -0.25, "spread": 0.3, "send": 0.35,
             "ring": 5.0, "vel": 0.7, "strum": 0.05, "notes": {
                 5: "F3+C4/4", 6: "A4/1 G4/1 F4/1 D4/1", 7: "C4/2 F4/2", 10: "F3+C4/4",
                 12: "F4/1 A4/1 C5/1 D5/1", 13: "C5/2 B4/1 A4/1", 14: "G4/2 A4/2",
                 19: "F3+C4/4"}},
})
HILLS_NIGHT = score.nocturne(HILLS, {
    "syrinx": {"gain": 0.143, "send": 0.85, "vel": 0.65},
    "lyre": {"voice": "barbitos", "gain": 1.0, "ring": 8.0, "vel": 0.6},
})

SHRINE = piece(56, [4], 24, [0, 32, 52, 88], (3.0, 2.2, 1.3, 0.03), {  # before a temple on its height
    "tibia": {"voice": "tibia", "gain": 0.3, "pan": 0.2, "send": 0.4, "vel": 0.75, "notes": {
        2: "F4/1 A4/1 C5/2", 3: "C5/2 D5/1 C5/1", 4: "B4/2 A4/2", 5: "G4/4",
        10: "F5/2 E5/1 D5/1", 11: "C5/2 A4/2", 12: "B4/1 A4/1 G4/2", 13: "A4/4",
        19: "F4/1 A4/1 D5/2", 20: "C5/2 B4/1 A4/1", 21: "G4/3 A4/1", 22: "F4/4"}},
    "cithara": {"voice": "cithara", "gain": 1.78, "pan": -0.15, "spread": 0.4, "send": 0.3,
                "ring": 5.0, "vel": 0.75, "notes": {
                    6: "A4/1 C5/1 E5/2", 7: "D5/2 C5/1 B4/1", 8: "C5/4",
                    15: "F4/1 G4/1 A4/2", 16: "B4/1 A4/1 G4/2", 17: "A4/2 F4/2", 18: "E4/4"}},
    "low": {"voice": "cithara", "gain": 0.605, "pan": -0.3, "send": 0.3, "ring": 5.0,
            "strum": 0.05, "vel": 0.55, "notes": {
                2: "F3+C4/4", 6: "A3+E4/4", 8: "C3+G3/4", 10: "F3+C4/4", 13: "F3+C4/4",
                15: "F3+C4/4", 18: "C3+G3/4", 19: "F3+C4/4", 22: "F3+C4/4"}},
}, rubato=(0.2, 8))
SHRINE_NIGHT = score.nocturne(SHRINE, {
    "tibia": {"gain": 0.0294, "send": 0.85, "vel": 0.6},
    "cithara": {"voice": "lyra", "gain": 0.9, "vel": 0.6, "ring": 7.0},
    "low": {"voice": "lyra", "gain": 0.217, "vel": 0.5},
})

# --- Greek towns --------------------------------------------------------------------------------

POLIS = piece(90, [6], 16, [0, 42, 72, 90], (2.4, 1.8, 1.0, 0.02), {  # a market square under its stoa
    "kithara": {"voice": "kithara", "gain": 1.0, "pan": -0.1, "spread": 0.4, "send": 0.3,
                "ring": 4.0, "vel": 0.8, "notes": {
                    1: "E4/2 A4/1 B4/1 C5/2", 2: "B4/2 A4/1 G4/1 A4/2", 3: "C5/2 D5/1 E5/1 D5/2",
                    4: "C5/2 B4/1 A4/1 B4/2", 5: "E5/2 D5/1 C5/1 B4/2", 6: "A4/2 G4/1 F4/1 E4/2",
                    7: "E4+B4/6", 9: "A4/2 C5/1 D5/1 E5/2", 10: "F5/2 E5/1 D5/1 C5/2",
                    11: "D5/2 C5/1 B4/1 A4/2", 12: "B4/4 r/2", 13: "E4/2 A4/1 B4/1 E5/2",
                    14: "D5/2 C5/1 B4/1 A4/2", 15: "G4/2 F4/1 G4/1 E4/2"}},
    "aulos": {"voice": "aulos", "gain": 0.0953, "pan": 0.3, "send": 0.35, "vel": 0.7, "notes": {
        5: "E5/3 C5/1 B4/2", 6: "A4/3 F4/1 E4/2", 9: "A4/3 D5/1 E5/2", 10: "F5/3 D5/1 C5/2",
        11: "D5/3 B4/1 A4/2", 12: "B4/4 r/2", 14: "D5/3 B4/1 A4/2", 15: "G4/3 F4/1 E4/2"}},
    "low": {"voice": "kithara", "gain": 0.365, "pan": -0.25, "send": 0.3, "ring": 4.0,
            "strum": 0.04, "vel": 0.55, "notes": {
                1: "E3+B3/6", 5: "E3+B3/6", 9: "A2+E3/6", 13: "E3+B3/6", 16: "E3+B3/6"}},
    "krotala": {"voice": "drum", "gain": 0.171, "pan": 0.4, "send": 0.4, "tune": 1500.0,
                "vel": 0.6, "notes": {b: "K/2 K/1? K/1? K/2" for b in range(9, 13)}},
})
POLIS_NIGHT = score.nocturne(POLIS, {
    "kithara": {"voice": "barbitos", "gain": 1.0, "vel": 0.6, "ring": 7.0, "send": 0.4},
    "aulos": {"gain": 0.0484, "send": 0.85, "vel": 0.6},
    "low": {"voice": "barbitos", "gain": 0.365, "vel": 0.5},
    "krotala": None,
})

MARCH = piece(90, [4], 24, [0, 28, 48, 80, 88], (2.2, 1.6, 0.9, 0.02), {  # a road between fields and the walls
    "aulos": {"voice": "aulos", "gain": 0.22, "pan": 0.15, "send": 0.3, "vel": 0.75, "notes": {
        1: "E4/1 A4/1 B4/1 C5/1", 2: "B4/1 A4/1 G4/1 A4/1", 3: "B4/2 E5/2", 4: "D5/1 C5/1 B4/2",
        5: "C5/1 B4/1 A4/1 G4/1", 6: "F4/1 G4/1 A4/2", 7: "G4/1 F4/1 E4/2",
        13: "A4/1 C5/1 E5/1 D5/1", 14: "C5/1 B4/1 A4/2", 15: "B4/1 C5/1 D5/2", 16: "E5/4",
        17: "D5/1 C5/1 B4/1 A4/1", 18: "G4/1 A4/1 B4/2", 19: "A4/1 G4/1 F4/1 G4/1",
        20: "E4/4"}},
    "drone": {"voice": "aulos", "gain": 0.0607, "pan": 0.25, "send": 0.35, "vel": 0.6,
              "legato": True, "notes": {1: "E4/28", 13: "E4/32"}},
    "lyra": {"voice": "lyra", "gain": 1.24, "pan": -0.25, "spread": 0.3, "send": 0.3,
             "ring": 4.0, "vel": 0.75, "notes": {
                 9: "A4/1 B4/1 C5/1 D5/1", 10: "E5/2 D5/1 C5/1", 11: "B4/1 A4/1 B4/2",
                 12: "E4/4", 21: "E4/1 A4/1 B4/1 E5/1", 22: "E4+B4/4"}},
    "drum": {"voice": "drum", "gain": 0.179, "pan": -0.35, "send": 0.3, "tune": 90.0,
             "vel": 0.6, "notes": {b: "D/1 k/1? T/1 k/1?" for b in range(13, 21)}},
})
MARCH_NIGHT = score.nocturne(MARCH, {
    "aulos": {"gain": 0.0749, "send": 0.85, "vel": 0.6},
    "drone": {"gain": 0.0181, "send": 0.9},
    "lyra": {"voice": "barbitos", "gain": 1.0, "vel": 0.6, "ring": 7.0},
    "drum": None,
})

SANCTUARY = piece(60, [4], 24, [0, 20, 40, 60, 80], (3.2, 2.4, 1.4, 0.035), {  # a temple terrace in the hills
    "kithara": {"voice": "kithara", "gain": 1.0, "pan": -0.1, "spread": 0.4, "send": 0.35,
                "ring": 5.0, "vel": 0.75, "notes": {
                    2: "A4/1 B4/1 C5/2", 3: "D5/1 C5/1 B4/1 A4/1", 4: "B4/2 G4/2", 5: "A4/4",
                    7: "C5/1 D5/1 E5/2", 8: "F5/1 E5/1 D5/1 C5/1", 9: "D5/2 B4/2",
                    10: "C5/2 A4/2", 12: "A4/1 G4/1 F4/1 E4/1", 13: "F4/2 G4/2", 14: "A4/4",
                    17: "E4/1 A4/1 B4/2", 18: "C5/2 B4/1 A4/1", 19: "G4/1 F4/1 G4/2",
                    20: "E4/4"}},
    "low": {"voice": "kithara", "gain": 0.34, "pan": -0.3, "send": 0.35, "ring": 5.0,
            "strum": 0.05, "vel": 0.55, "notes": {
                2: "A2+E3/4", 5: "A2+E3/4", 7: "A2+E3/4", 10: "A2+E3/4", 12: "E3+B3/4",
                14: "A2+E3/4", 17: "E3+B3/4", 20: "E3+B3/4"}},
    "aulos": {"voice": "aulos", "gain": 0.0767, "pan": 0.45, "send": 0.8, "vel": 0.6, "notes": {
        22: "B4/1 A4/1 G4/1 F4/1", 23: "E4/4"}},
}, rubato=(0.2, 8))
SANCTUARY_NIGHT = score.nocturne(SANCTUARY, {
    "kithara": {"voice": "barbitos", "gain": 1.0, "vel": 0.6, "ring": 8.0, "send": 0.45},
    "low": {"voice": "barbitos", "gain": 0.316, "vel": 0.5},
    "aulos": {"gain": 0.0441, "send": 0.9},
})

HARBOUR = piece(90, [3], 32, [0, 24, 33, 60, 72, 87], (2.6, 1.9, 1.0, 0.03), {  # a quay on a sheltered bay
    "lyra": {"voice": "lyra", "gain": 1.0, "pan": -0.1, "spread": 0.35, "send": 0.35,
             "ring": 4.5, "vel": 0.75, "notes": {
                 1: "E4/2 A4/1", 2: "B4/2 C5/1", 3: "B4/1 A4/1 G4/1", 4: "A4/3", 5: "C5/2 B4/1",
                 6: "A4/2 G4/1", 7: "F4/2 G4/1", 8: "E4/3", 13: "A4/2 B4/1", 14: "C5/2 D5/1",
                 15: "E5/2 D5/1", 16: "C5/3", 17: "B4/2 A4/1", 18: "G4/2 A4/1", 19: "B4/2 G4/1",
                 20: "A4/3", 25: "E4/2 A4/1", 26: "B4/2 C5/1", 27: "B4/1 A4/1 G4/1",
                 28: "F4/2 E4/1", 29: "E4/3"}},
    "aulos": {"voice": "aulos", "gain": 0.0968, "pan": 0.35, "send": 0.45, "vel": 0.7, "notes": {
        9: "E5/2 D5/1", 10: "C5/2 B4/1", 11: "A4/3", 21: "E5/2 D5/1", 22: "C5/2 B4/1",
        23: "A4/2 G4/1", 24: "A4/3"}},
    "low": {"voice": "lyra", "gain": 0.47, "pan": -0.3, "send": 0.3, "ring": 4.5, "strum": 0.05,
            "vel": 0.55, "notes": {
                1: "A2+E3/3", 5: "A2+E3/3", 8: "E3+B3/3", 13: "A2+E3/3", 16: "C3+G3/3",
                17: "A2+E3/3", 20: "A2+E3/3", 25: "A2+E3/3", 29: "E3+B3/3"}},
})
HARBOUR_NIGHT = score.nocturne(HARBOUR, {
    "lyra": {"voice": "barbitos", "gain": 1.0, "vel": 0.6, "ring": 7.0, "send": 0.4},
    "aulos": {"gain": 0.0511, "send": 0.85, "vel": 0.6},
    "low": {"voice": "barbitos", "gain": 0.426, "vel": 0.5},
})

# --- Persian towns ------------------------------------------------------------------------------

COURT = piece(80, [4], 24, 16, (2.4, 1.8, 1.0, 0.02), {  # a satrap's columned hall
    "harp": {"voice": "harp", "gain": 1.0, "pan": -0.1, "spread": 0.4, "send": 0.3, "ring": 6.0,
             "vel": 0.75, "notes": {
                 1: "D4/1 E4/1 F4/1 A4/1", 2: "G4/2 F4/1 E4/1", 3: "F4/1 G4/1 A4/2", 4: "D4/4",
                 5: "A4/1 B4/1 C5/1 D5/1", 6: "C5/2 A4/1 G4/1", 7: "A4/1 G4/1 F4/1 E4/1",
                 8: "D4/4", 13: "F4/1 A4/1 D5/2", 14: "C5/1 B4/1 A4/2", 15: "G4/1 A4/1 F4/1 E4/1",
                 16: "D4/4", 17: "D5/1 C5/1 A4/1 G4/1", 18: "F4/2 G4/1 A4/1",
                 19: "E4/2 F4/1 E4/1", 20: "D4/4"}},
    "lute": {"voice": "lute", "gain": 1.01, "pan": 0.3, "send": 0.25, "ring": 2.5, "vel": 0.6,
             "notes": {**{b: "D3/2 A3/2" for b in (1, 2, 3, 5, 6, 7, 13, 14, 15, 17, 18, 19)},
                       4: "D3/4", 8: "D3/4", 16: "D3/4", 20: "D3/4",
                       9: "D4/0.5 E4/0.5 F4/1 E4/1 D4/1", 10: "A3/2 C4/1 D4/1",
                       11: "E4/1 D4/1 C4/1 A3/1", 12: "D4/4"}},
})
COURT_NIGHT = score.nocturne(COURT, {
    "harp": {"gain": 0.85, "vel": 0.6, "ring": 8.0, "send": 0.45},
    "lute": None,
    "hum": hum({1: "D3+A3/32", 13: "D3+A3/32"}, 24, [4], 0.0933),
})

CARAVAN = piece(80, [4], 24, 16, (2.4, 1.6, 0.9, 0.025), {  # a road station between ridges
    "pipe": {"voice": "pipe", "gain": 0.4, "pan": 0.15, "send": 0.35, "vel": 0.75, "notes": {
        1: "A4/2 G4/1 F4/1", 2: "E4/1 F4/1 G4/2", 3: "A4/1 C5/1 B4/1 A4/1", 4: "G4/4",
        5: "F4/1 G4/1 A4/2", 6: "D5/2 C5/1 A4/1", 7: "G4/1 F4/1 E4/1 F4/1", 8: "D4/4",
        13: "D5/1 C5/1 A4/2", 14: "B4/1 A4/1 G4/2", 15: "A4/1 G4/1 F4/1 E4/1", 16: "F4/2 D4/2",
        17: "A4/2 C5/1 D5/1", 18: "C5/1 A4/1 G4/2", 19: "F4/1 E4/1 F4/1 G4/1", 20: "D4/4"}},
    "drone": {"voice": "pipe", "gain": 0.117, "pan": 0.25, "send": 0.4, "vel": 0.6,
              "legato": True, "notes": {1: "D4/32", 13: "D4/32"}},
    "drum": {"voice": "drum", "gain": 0.546, "pan": -0.3, "send": 0.3, "tune": 80.0, "vel": 0.65,
             "notes": {b: "D/1 k/1? D/1 r/1" for b in range(1, 21)}},
})
CARAVAN_NIGHT = score.nocturne(CARAVAN, {
    "pipe": {"voice": "lute", "gain": 0.7, "ring": 3.0, "vel": 0.6, "send": 0.35},
    "drone": None,
    "drum": None,
    "hum": hum({1: "D3+A3/32", 13: "D3+A3/32"}, 24, [4], 0.0396),
})

WEST = piece(80, [4], 24, 16, (2.4, 1.8, 1.0, 0.025), {  # a terrace over a western harbour
    "lyre": {"voice": "lyra", "gain": 1.0, "pan": -0.1, "spread": 0.35, "send": 0.3,
             "ring": 4.5, "vel": 0.75, "notes": {
                 1: "D4/2_3 E4/2_3 F4/2_3 A4/2", 2: "G4/2_3 F4/2_3 E4/2_3 F4/2",
                 3: "A4/1 C5/1 D5/2", 4: "C5/2_3 A4/2_3 G4/2_3 A4/2",
                 5: "F4/2_3 G4/2_3 A4/2_3 B4/1 A4/1", 6: "G4/2 F4/1 E4/1",
                 7: "F4/2_3 E4/2_3 D4/2_3 E4/2", 8: "D4/4",
                 17: "D4/2_3 E4/2_3 F4/2_3 A4/2", 18: "C5/2 B4/1 A4/1",
                 19: "G4/2_3 F4/2_3 E4/2_3 F4/1 E4/1", 20: "D4/4"}},
    "pipe": {"voice": "pipe", "gain": 0.129, "pan": 0.3, "send": 0.4, "vel": 0.7, "notes": {
        9: "A4/2 C5/1 D5/1", 10: "C5/1 A4/1 G4/2", 11: "A4/1 G4/1 F4/1 E4/1", 12: "D4/4",
        13: "F4/1 G4/1 A4/2", 14: "D5/2 C5/1 A4/1", 15: "G4/1 F4/1 E4/2", 16: "D4/4"}},
    "low": {"voice": "lyra", "gain": 0.444, "pan": -0.3, "send": 0.3, "ring": 4.5, "strum": 0.05,
            "vel": 0.55, "notes": {b: "D3+A3/4" for b in (1, 4, 8, 9, 12, 16, 17, 20)}},
})
WEST_NIGHT = score.nocturne(WEST, {
    "lyre": {"voice": "barbitos", "gain": 1.0, "vel": 0.6, "ring": 7.0, "send": 0.4},
    "pipe": {"gain": 0.0542, "send": 0.85, "vel": 0.6},
    "low": {"voice": "barbitos", "gain": 0.284, "vel": 0.5},
})

RIVER = piece(60, [3], 32, 12, (2.4, 1.6, 0.9, 0.025), {  # a brick quay on the river
    "lute": {"voice": "lute", "gain": 0.8, "pan": 0.2, "send": 0.3, "ring": 3.0, "vel": 0.7,
             "notes": {
                 1: "D4/1 E4/1 F4/1", 2: "A4/2 G4/1", 3: "F4/1 E4/1 F4/1", 4: "D4/3",
                 5: "F4/1 G4/1 A4/1", 6: "C5/2 A4/1", 7: "G4/1 F4/1 E4/1", 8: "F4/3",
                 17: "A4/1 B4/1 C5/1", 18: "D5/2 C5/1", 19: "A4/1 G4/1 A4/1", 20: "F4/3",
                 21: "G4/1 F4/1 E4/1", 22: "D4/1 E4/1 F4/1", 23: "E4/2 C4/1", 24: "D4/3"}},
    "harp": {"voice": "harp", "gain": 0.398, "pan": -0.2, "spread": 0.35, "send": 0.35,
             "ring": 6.0, "vel": 0.7, "strum": 0.06, "notes": {
                 4: "D3+A3/3", 9: "D4+A4/2 F4/1", 10: "E4+A4/2 G4/1", 11: "F4+C5/2 A4/1",
                 12: "D4+A4/3", 13: "C4+G4/2 E4/1", 14: "D4+A4/2 F4/1", 15: "E4+B4/2 G4/1",
                 16: "D4+A4/3", 24: "D3+A3/3", 25: "D4+A4/3", 28: "D3+A3/3"}},
})
RIVER_NIGHT = score.nocturne(RIVER, {
    "lute": {"voice": "harp", "gain": 0.8, "ring": 7.0, "vel": 0.6, "send": 0.4},
    "harp": {"gain": 0.596, "ring": 8.0, "vel": 0.55, "send": 0.45},
    "hum": hum({1: "D3+A3/24", 9: "D3+A3/24", 17: "D3+A3/24", 25: "D3+A3/24"}, 32, [3], 0.0674),
})

# (set, piece name) -> day, night, towns, voices by day and night
PIECES = {
    ("rome", "forum"): (FORUM, FORUM_NIGHT, "Ostia, Capua",
                        "cithara theme with tibia answers and a frame drum", "lyre, far tibia"),
    ("rome", "hills"): (HILLS, HILLS_NIGHT, "Tibur, Beneventum",
                        "syrinx with a lyre answering", "far syrinx, barbitos"),
    ("rome", "shrine"): (SHRINE, SHRINE_NIGHT, "Alban Mount, Brundisium",
                         "sacrificial tibia hymn with the cithara", "far tibia, lyre"),
    ("athens", "polis"): (POLIS, POLIS_NIGHT, "Corinth, Olympia, Ephesus",
                          "kithara in dactyls, aulos in heterophony, krotala",
                          "barbitos, far aulos"),
    ("athens", "march"): (MARCH, MARCH_NIGHT, "the Academy, Sparta",
                          "aulos with its drone pipe, lyra, a frame drum's step",
                          "far aulos, barbitos"),
    ("athens", "sanctuary"): (SANCTUARY, SANCTUARY_NIGHT, "Delphi, Delos",
                              "kithara hymn on the mese, a far aulos closing", "barbitos"),
    ("athens", "harbour"): (HARBOUR, HARBOUR_NIGHT, "Eleusis, Corcyra",
                            "lyra in a lilting three, aulos answers", "barbitos, far aulos"),
    ("parsa", "court"): (COURT, COURT_NIGHT, "Susa, Pasargadae",
                         "angular harp over a lute's drone", "harp, hummed drone"),
    ("parsa", "caravan"): (CARAVAN, CARAVAN_NIGHT, "the Persian Gates, Halys",
                           "double pipe with drone over a frame drum's walk",
                           "lute, hummed drone"),
    ("parsa", "west"): (WEST, WEST_NIGHT, "Sardis, Sidon",
                        "lyre in a triplet lilt, double pipe answers", "barbitos, far pipe"),
    ("parsa", "river"): (RIVER, RIVER_NIGHT, "Babylon, the Euphrates crossing, Gordion",
                         "long-necked lute, harp dyads", "harp, hummed drone"),
}


def renderer(p):
    return lambda rng: score.render(p, rng)


def files(set_name):
    """The FILES table of one set's town pieces."""
    out = {}
    for (s, name), (day, night, towns, by_day, by_night) in PIECES.items():
        if s != set_name:
            continue
        for when, p, voices in (("day", day, by_day), ("night", night, by_night)):
            out[f"music/{s}/town_{name}_{when}.ogg"] = dict(
                kind="music", render=renderer(p), piece=p, lufs=-18.0, quality=2, gain=0.6,
                ceiling=-2.0, when=when, where=f"towns: {towns}",
                purpose=f"Town piece ({name}), {when}: {voices}.")
    return out


ROME, ATHENS, PARSA = files("rome"), files("athens"), files("parsa")
