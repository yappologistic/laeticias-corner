"""The two music loops, written as note data and rendered with the instruments.

Both pieces share one pitch world (D lydian = B dorian: D E F# G# A B C#, with G natural
borrowed freely) and one tempo, so the engine's day/night crossfade never clashes.
The night piece reuses the day motif (A B C# A) at half speed over B minor harmony."""

import numpy as np

import instruments as ins
from dsp import (SR, circular, highpass, impulse_response, lowpass, midi_hz, pan, place, secs,
                 with_reverb, wrap)

NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    """'F#5' -> 78. Sharps only; the pieces never need flats."""
    pitch = NOTE_INDEX[name[0]] + name.count("#")
    return 12 * (int(name.lstrip("ABCDEFG#")) + 1) + pitch


# Chord name -> (bass pitch class, right-hand voicing). The bass is placed in B1..A#2.
CHORDS = {
    "Dmaj9": ("D", "F#4 A4 C#5 E5"),
    "Dmaj9/F#": ("F#", "D4 A4 C#5 E5"),
    "E/D": ("D", "E4 G#4 B4"),
    "E/B": ("B", "G#4 B4 E5"),
    "Gmaj7": ("G", "F#4 B4 D5"),
    "Gmaj9": ("G", "F#4 A4 B4 D5"),
    "Gmaj7#11": ("G", "F#4 B4 C#5"),
    "G6/9": ("G", "E4 A4 B4 D5"),
    "Bm9": ("B", "D4 F#4 A4 C#5"),
    "Bm9/D": ("D", "F#4 A4 B4 C#5"),
    "F#m7": ("F#", "E4 A4 C#5"),
    "F#m11": ("F#", "E4 A4 B4 C#5"),
    "F#7sus4": ("F#", "E4 B4 C#5"),
    "Em9": ("E", "G4 B4 D5 F#5"),
    "Em11": ("E", "G4 A4 D5"),
    "A13sus": ("A", "G4 B4 D5 F#5"),
    "A9sus4": ("A", "D4 G4 B4"),
    "Asus4": ("A", "D4 E4 A4"),
    "A7": ("A", "E4 G4 C#5"),
}


def bass_midi(pc):
    m = midi(pc + "2")
    return m - 12 if m > 46 else m


def parse_melody(text):
    """'r/1 A5/0.5 | ...' -> [(beat, midi, beats)]; every bar must hold exactly 4 beats."""
    notes, beat = [], 0.0
    for bar_no, bar in enumerate(text.split("|")):
        bar_start = beat
        for tok in bar.split():
            name, length = tok.split("/")
            if name != "r":
                notes.append((beat, midi(name), float(length)))
            beat += float(length)
        assert abs(beat - bar_start - 4) < 1e-9, f"bar {bar_no + 1} of melody is not 4 beats: {bar}"
    return notes, beat


def parse_chords(text):
    """'Dmaj9:4 E/D:4' -> [(beat, name, beats)]."""
    out, beat = [], 0.0
    for tok in text.split():
        name, length = tok.rsplit(":", 1)
        assert name in CHORDS, name
        out.append((beat, name, float(length)))
        beat += float(length)
    return out, beat


def accompaniment(style, start, name, beats):
    """Felt-piano accompaniment notes (beat, midi, beats, velocity) for one chord."""
    bass_pc, voicing = CHORDS[name]
    root = bass_midi(bass_pc) + 12
    rh = [midi(v) for v in voicing.split()]
    notes = [(start, root, beats, 0.42)]
    if style == "roll":
        if beats >= 4:
            notes.append((start + 2, root + 7, beats - 2, 0.28))
            notes += [(start + 2.5, rh[1], 1.0, 0.2), (start + 3.5, rh[-1], 0.5, 0.18)]
        notes += [(start + 0.5 + 0.06 * i, m, beats - 0.5, 0.26) for i, m in enumerate(rh)]
    elif style == "arp":
        order = [rh[0], rh[1], rh[-1], rh[2 % len(rh)]]
        notes += [(start + b, order[b], 1.25, 0.2 if b else 0.24) for b in range(int(beats))]
    elif style == "whole":
        notes.append((start + 0.05, root + 7, beats, 0.26))
        notes += [(start + 0.25 + 0.08 * i, m, beats - 0.25, 0.22) for i, m in enumerate(rh)]
        if beats >= 8:
            notes.append((start + 4.5, rh[-1], 3.0, 0.14))
    return notes


def render(piece, rng):
    """Render a piece to a stereo loop of exactly its bar count, tails wrapped."""
    beat_s = 60.0 / piece["bpm"]
    total_beats = 0.0
    events = []  # (bus, beat, render_fn, pan)
    for sec in piece["sections"]:
        chords, chord_beats = parse_chords(sec["chords"])
        melody, mel_beats = parse_melody(sec["melody"])
        assert chord_beats == mel_beats, sec["chords"]
        base = total_beats
        for beat, name, beats in chords:
            b = base + beat
            for nb, m, nlen, vel in accompaniment(sec["piano"], b, name, beats):
                events.append(("piano", nb, ("piano", m, nlen * beat_s, vel * sec["piano_vel"]),
                               (m - 62) / 36))
            bass_pc, voicing = CHORDS[name]
            if sec["bass"]:
                events.append(("bass", b, ("bass", bass_midi(bass_pc), beats * beat_s,
                                           sec["bass"]), 0.0))
            pad_notes = [bass_midi(bass_pc) + 12] + [midi(v) for v in voicing.split()]
            for m in pad_notes:
                events.append(("pad", b, ("pad", m, beats * beat_s, sec["pad"]), 0.0))
        for beat, m, nlen in melody:
            vel = sec["lead_vel"] * (1.0 if nlen >= 1 else 0.85)
            events.append((sec["lead"], base + beat, (sec["lead"], m, nlen * beat_s, vel), 0.25))
        total_beats += chord_beats

    loop_n = secs(total_beats * beat_s)
    assert loop_n == round(total_beats * beat_s * SR), "loop must be an exact number of samples"
    tail = secs(piece["tail"])
    buses = {name: np.zeros((loop_n + tail, 2)) for name in piece["mix"]}
    for bus, beat, (kind, m, dur, vel), position in events:
        jitter = 0.0 if kind in ("pad", "bass") else rng.normal(0, 0.006)
        at = max(0, secs(beat * beat_s + jitter))
        vel *= rng.uniform(0.92, 1.04)
        f = midi_hz(m)
        if kind == "piano":
            x = pan(ins.felt_piano(f, dur, vel, rng), position)
        elif kind == "box":
            x = pan(ins.tine(f * piece["box_octave"], 6.0, vel, rng), position)
        elif kind == "pad":
            x = ins.pad(f, dur + 0.4, vel, rng, cutoff=piece["pad_cutoff"])
        else:
            x = pan(ins.sub_bass(f, dur, vel), position)
        place(buses[bus], x, at)

    ir = impulse_response(rng, piece["reverb"][0], piece["reverb"][1], piece["reverb"][2])
    dry = sum(buses[b] * piece["mix"][b][0] for b in buses)
    send = sum(buses[b] * piece["mix"][b][0] * piece["mix"][b][1] for b in buses)
    out = wrap(with_reverb(dry, send, ir), loop_n)
    return circular(lambda y: lowpass(highpass(y, 35, 2), 9000, 2), out)


# --- the pieces ------------------------------------------------------------------------

DAY_A = "Dmaj9:4 E/D:4 Dmaj9:4 Gmaj7:4 Bm9:4 F#m7:4 Gmaj9:4 A13sus:2 A7:2"

DAY = {
    "bpm": 72,
    "tail": 8.0,
    "box_octave": 1.0,
    "pad_cutoff": 2200.0,
    "reverb": (3.0, 1.8, 0.9),  # length, low T60, high T60: a small warm room
    # bus -> (gain, reverb send)
    "mix": {"box": (0.55, 0.45), "piano": (1.0, 0.3), "pad": (0.028, 0.4), "bass": (0.4, 0.05)},
    "sections": [
        {   # A: the theme on the music box
            "chords": DAY_A,
            "melody": "r/1 A5/0.5 B5/0.5 C#6/1 A5/1 | B5/1.5 G#5/0.5 E5/2 "
                      "| r/0.5 F#5/0.5 A5/0.5 E6/1.5 D6/1 | B5/2.5 r/1.5 "
                      "| r/1 D6/0.5 C#6/0.5 B5/1 F#5/1 | A5/1.5 C#6/0.5 E5/2 "
                      "| r/0.5 F#5/0.5 G5/0.5 A5/0.5 B5/1 D6/1 | B5/1.5 D6/0.5 C#6/2",
            "lead": "box", "lead_vel": 0.8, "piano": "roll", "piano_vel": 1.0,
            "bass": 0.5, "pad": 1.0,
        },
        {   # B: the piano sings lower over the subdominant, gentle arpeggios
            "chords": "Gmaj9:4 F#m7:4 Em9:4 A13sus:4 Bm9:4 G6/9:4 Em9:4 Asus4:2 A7:2",
            "melody": "F#5/3 A5/1 | E5/1.5 C#5/0.5 A4/2 | r/1 B4/0.5 D5/0.5 F#5/1 G5/1 "
                      "| F#5/2 E5/2 | r/0.5 D5/0.5 F#5/0.5 A5/0.5 C#6/2 | B5/1.5 A5/0.5 E5/2 "
                      "| G5/1 F#5/1 D5/1 B4/1 | E5/2.5 r/1.5",
            "lead": "piano", "lead_vel": 0.62, "piano": "arp", "piano_vel": 0.85,
            "bass": 0.5, "pad": 1.1,
        },
        {   # A': the theme returns, answered higher
            "chords": DAY_A,
            "melody": "r/1 A5/0.5 B5/0.5 C#6/1 A5/1 | B5/1 G#5/1 B5/0.5 E6/1.5 "
                      "| D6/1.5 C#6/0.5 A5/1 F#5/1 | B5/1 A5/0.5 B5/0.5 D6/2 "
                      "| r/1 D6/0.5 C#6/0.5 B5/1 F#5/1 | A5/1.5 C#6/0.5 E6/2 "
                      "| r/0.5 D6/0.5 B5/0.5 A5/0.5 G5/1 F#5/1 | E5/1.5 F#5/0.5 E5/2",
            "lead": "box", "lead_vel": 0.8, "piano": "roll", "piano_vel": 1.0,
            "bass": 0.5, "pad": 1.0,
        },
        {   # C: a quiet lydian breath, mostly pad, sparse notes, leads home to D
            "chords": "Gmaj7#11:4 Dmaj9/F#:4 Em9:4 A9sus4:4 Gmaj9:4 F#m11:4 Em11:4 A13sus:4",
            "melody": "r/2 C#6/2 | A5/4 | r/1 F#5/1 G5/1 B5/1 | A5/3 r/1 "
                      "| r/2 D6/1 B5/1 | C#6/2 A5/2 | G5/1.5 F#5/0.5 E5/2 | r/2 E5/1 F#5/1",
            "lead": "box", "lead_vel": 0.65, "piano": "whole", "piano_vel": 0.8,
            "bass": 0.35, "pad": 1.5,
        },
    ],
}

NIGHT_A = "Bm9:8 E/B:8 Gmaj9:8 F#m11:8"

NIGHT = {
    "bpm": 72,
    "tail": 10.0,
    "box_octave": 2.0,  # the box sits an octave above the written line, clear of the pad
    "pad_cutoff": 1500.0,
    "reverb": (4.5, 3.0, 1.4),  # a larger, darker space
    "mix": {"box": (0.5, 0.7), "piano": (1.1, 0.45), "pad": (0.07, 0.5), "bass": (0.39, 0.05)},
    "sections": [
        {   # A: the day motif at half speed, on a distant music box
            "chords": NIGHT_A,
            "melody": "r/2 A4/1 B4/1 | C#5/3 A4/1 | B4/3 G#4/1 | E4/4 "
                      "| r/1 F#4/1 A4/1 E5/1 | D5/4 | C#5/2 B4/1 A4/1 | B4/4",
            "lead": "box", "lead_vel": 0.75, "piano": "whole", "piano_vel": 0.7,
            "bass": 0.4, "pad": 1.0,
        },
        {   # B: low felt piano takes the line
            "chords": "Em9:8 Bm9/D:8 Gmaj7#11:8 A13sus:8",
            "melody": "r/2 G4/1 B4/1 | F#5/4 | r/1 F#4/1 A4/1 C#5/1 | B4/4 "
                      "| r/2 C#5/2 | B4/2 A4/1 F#4/1 | r/1 E4/1 F#4/1 D5/1 | B4/2 r/2",
            "lead": "piano", "lead_vel": 0.5, "piano": "whole", "piano_vel": 0.6,
            "bass": 0.4, "pad": 1.1,
        },
        {   # A': theme again, a new cadence
            "chords": NIGHT_A,
            "melody": "r/2 A4/1 B4/1 | C#5/3 A4/1 | B4/3 G#4/1 | E4/4 "
                      "| r/1 F#4/1 A4/1 E5/1 | D5/4 | C#5/1 E5/1 B4/2 | A4/4",
            "lead": "box", "lead_vel": 0.75, "piano": "whole", "piano_vel": 0.7,
            "bass": 0.4, "pad": 1.0,
        },
        {   # C: almost only pad and space, a few notes leading back to B minor
            "chords": "Gmaj9:8 Dmaj9/F#:8 Em11:8 F#7sus4:8",
            "melody": "r/4 | r/2 B4/2 | A4/4 | r/4 | r/2 G4/1 A4/1 | B4/4 | r/4 | r/2 B4/1 C#5/1",
            "lead": "box", "lead_vel": 0.6, "piano": "whole", "piano_vel": 0.5,
            "bass": 0.3, "pad": 1.4,
        },
    ],
}


def day(rng):
    return render(DAY, rng)


def night(rng):
    return render(NIGHT, rng)
