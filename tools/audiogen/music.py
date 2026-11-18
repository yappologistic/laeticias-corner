"""The two music loops, written as note data and rendered with the instruments.

Both pieces share one pitch world (D lydian = B dorian: D E F# G# A B C#, with G natural
borrowed freely) and one tempo, so the engine's day/night crossfade never clashes.
The night piece reuses the day motif (A B C# A) at half speed over B minor harmony."""

import numpy as np
from scipy import signal

import instruments as ins
from dsp import (SR, circular, highpass, impulse_response, lowpass, midi_hz, pan, place, secs,
                 wrap)

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


def parse_melody(text, bar_beats=4):
    """'r/1 A5/0.5 | ...' -> [(beat, midi, beats)]; every bar must hold exactly bar_beats."""
    notes, beat = [], 0.0
    for bar_no, bar in enumerate(text.split("|")):
        bar_start = beat
        for tok in bar.split():
            name, length = tok.split("/")
            if name != "r":
                notes.append((beat, midi(name), float(length)))
            beat += float(length)
        assert abs(beat - bar_start - bar_beats) < 1e-9, f"bar {bar_no + 1} != {bar_beats}: {bar}"
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


STEMS = ("pad", "keys", "melody", "bass")  # sum to the mix; "colour" is extra


def render(piece, rng, colour_rng=None):
    """Render a piece to a stereo loop of exactly its bar count, tails wrapped. With
    colour_rng, also return the stems {id: loop}: pad, keys, melody and bass sum to the
    mix (same notes, same room, same tails), colour is the extra layer in the same room."""
    beat_s = 60.0 / piece["bpm"]
    total_beats = 0.0
    events = []  # (bus, beat, render_fn, pan, stem)
    for sec in piece["sections"]:
        chords, chord_beats = parse_chords(sec["chords"])
        melody, mel_beats = parse_melody(sec["melody"])
        assert chord_beats == mel_beats, sec["chords"]
        base = total_beats
        for beat, name, beats in chords:
            b = base + beat
            for nb, m, nlen, vel in accompaniment(sec["piano"], b, name, beats):
                events.append(("piano", nb, ("piano", m, nlen * beat_s, vel * sec["piano_vel"]),
                               (m - 62) / 36, "keys"))
            bass_pc, voicing = CHORDS[name]
            if sec["bass"]:
                events.append(("bass", b, ("bass", bass_midi(bass_pc), beats * beat_s,
                                           sec["bass"]), 0.0, "bass"))
            pad_notes = [bass_midi(bass_pc) + 12] + [midi(v) for v in voicing.split()]
            for m in pad_notes:
                events.append(("pad", b, ("pad", m, beats * beat_s, sec["pad"]), 0.0, "pad"))
        for beat, m, nlen in melody:
            vel = sec["lead_vel"] * (1.0 if nlen >= 1 else 0.85)
            events.append((sec["lead"], base + beat, (sec["lead"], m, nlen * beat_s, vel), 0.25,
                           "melody"))
        total_beats += chord_beats

    loop_n = secs(total_beats * beat_s)
    assert loop_n == round(total_beats * beat_s * SR), "loop must be an exact number of samples"
    tail = secs(piece["tail"])
    with_stems = colour_rng is not None
    # With stems, each stem keeps its own dry and reverb-send sums, weighted exactly like the
    # mix, and the mix is their sum (every note belongs to one stem and the room is linear), so
    # no bus buffers are needed; float32 keeps a 106 s piece's buffers under 400 MB (the
    # rounding sits some 140 dB down).
    buf = np.float32 if with_stems else np.float64
    buses = {} if with_stems else {name: np.zeros((loop_n + tail, 2)) for name in piece["mix"]}
    stems = {s: (np.zeros((loop_n + tail, 2), buf), np.zeros((loop_n + tail, 2), buf))
             for s in STEMS} if with_stems else {}
    for bus, beat, (kind, m, dur, vel), position, stem in events:
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
        if with_stems:
            gain, send = piece["mix"][bus]
            place(stems[stem][0], x * gain, at)
            place(stems[stem][1], x * (gain * send), at)
        else:
            place(buses[bus], x, at)

    ir = impulse_response(rng, piece["reverb"][0], piece["reverb"][1], piece["reverb"][2])

    def finish(dry, send):
        # The room, tail wrap and tone filters one channel at a time (each channel is
        # independent, so this equals the stereo computation with a third of the memory).
        out = np.empty((loop_n, 2))
        for c in range(2):
            wet = signal.oaconvolve(np.asarray(send[:, c], np.float64), ir[:, c])
            wet[: len(dry)] += dry[:, c]
            out[:, c] = circular(lambda y: lowpass(highpass(y, 35, 2), 9000, 2), wrap(wet, loop_n))
        return out

    if not with_stems:
        dry = sum(buses[b] * piece["mix"][b][0] for b in buses)
        send = sum(buses[b] * piece["mix"][b][0] * piece["mix"][b][1] for b in buses)
        return finish(dry, send)
    out = {}
    mix = np.zeros((loop_n, 2))
    for s in STEMS:  # one stem's room at a time, its buffers freed as it is finished
        y = finish(*stems.pop(s))
        mix += y
        out[s] = y.astype(np.float32)
    out["colour"] = finish(*colour(piece, colour_rng, loop_n + tail)).astype(np.float32)
    return mix, out


def colour(piece, rng, n):
    """The colour layer's dry and reverb-send buffers: its voices' note lines plus, for
    the day, a brushed shaker on the off-beats of the sections that ask for it."""
    beat_s = 60.0 / piece["bpm"]
    dry, send = np.zeros((n, 2), np.float32), np.zeros((n, 2), np.float32)  # as the stems

    def add(x, beat, voice):
        gain, wet, position = piece["colour"][voice]
        at = max(0, secs(beat * beat_s + rng.normal(0, 0.006)))
        x = pan(x * gain, position)
        place(dry, x, at)
        place(send, x * wet, at)

    base = 0.0
    for sec in piece["sections"]:
        for voice, (text, bar_beats, vel) in sec["colour"].items():
            for beat, m, nlen in parse_melody(text, bar_beats)[0]:
                v = vel * rng.uniform(0.92, 1.04)
                add(COLOUR_VOICES[voice](midi_hz(m), nlen * beat_s, v, rng), base + beat, voice)
        beats = parse_chords(sec["chords"])[1]
        for k in range(int(beats) if sec.get("shaker") else 0):
            v = sec["shaker"] * (1.0 if k % 2 else 0.75) * rng.uniform(0.85, 1.0)
            add(ins.shaker(v, rng), base + k + 0.5, "shaker")
        base += beats
    return dry, send


COLOUR_VOICES = {"flute": ins.wooden_flute, "cello": ins.cello_harmonic, "clarinet": ins.clarinet}


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
    # colour voice -> (gain, reverb send, pan)
    "colour": {"flute": (0.21, 0.45, -0.35), "shaker": (0.03, 0.25, 0.4)},
    "sections": [
        {   # A: the theme on the music box
            "chords": DAY_A,
            "melody": "r/1 A5/0.5 B5/0.5 C#6/1 A5/1 | B5/1.5 G#5/0.5 E5/2 "
                      "| r/0.5 F#5/0.5 A5/0.5 E6/1.5 D6/1 | B5/2.5 r/1.5 "
                      "| r/1 D6/0.5 C#6/0.5 B5/1 F#5/1 | A5/1.5 C#6/0.5 E5/2 "
                      "| r/0.5 F#5/0.5 G5/0.5 A5/0.5 B5/1 D6/1 | B5/1.5 D6/0.5 C#6/2",
            "lead": "box", "lead_vel": 0.8, "piano": "roll", "piano_vel": 1.0,
            "bass": 0.5, "pad": 1.0,
            # the flute answers each two-bar phrase from below
            "colour": {"flute": ("r/4 | r/2 G#4/0.5 B4/0.5 C#5/1 | B4/1 A4/1 r/2 "
                                 "| r/2.5 D5/0.5 C#5/0.5 B4/0.5 | A4/2 r/2 "
                                 "| r/2 F#4/0.5 A4/0.5 C#5/1 | B4/2 r/2 "
                                 "| r/2 E5/0.5 D5/0.5 C#5/1", 4, 0.75)},
            "shaker": 1.0,
        },
        {   # B: the piano sings lower over the subdominant, gentle arpeggios
            "chords": "Gmaj9:4 F#m7:4 Em9:4 A13sus:4 Bm9:4 G6/9:4 Em9:4 Asus4:2 A7:2",
            "melody": "F#5/3 A5/1 | E5/1.5 C#5/0.5 A4/2 | r/1 B4/0.5 D5/0.5 F#5/1 G5/1 "
                      "| F#5/2 E5/2 | r/0.5 D5/0.5 F#5/0.5 A5/0.5 C#6/2 | B5/1.5 A5/0.5 E5/2 "
                      "| G5/1 F#5/1 D5/1 B4/1 | E5/2.5 r/1.5",
            "lead": "piano", "lead_vel": 0.62, "piano": "arp", "piano_vel": 0.85,
            "bass": 0.5, "pad": 1.1,
            "colour": {"flute": ("B4/3 r/1 | r/2 C#5/1 E5/1 | G4/2 r/2 | r/2 F#4/0.5 A4/0.5 B4/1 "
                                 "| r/2 E5/1 F#5/1 | D5/2 r/0.5 B4/0.5 A4/1 | r/4 "
                                 "| r/2.5 G4/0.5 A4/0.5 C#5/0.5", 4, 0.7)},
            "shaker": 0.85,
        },
        {   # A': the theme returns, answered higher
            "chords": DAY_A,
            "melody": "r/1 A5/0.5 B5/0.5 C#6/1 A5/1 | B5/1 G#5/1 B5/0.5 E6/1.5 "
                      "| D6/1.5 C#6/0.5 A5/1 F#5/1 | B5/1 A5/0.5 B5/0.5 D6/2 "
                      "| r/1 D6/0.5 C#6/0.5 B5/1 F#5/1 | A5/1.5 C#6/0.5 E6/2 "
                      "| r/0.5 D6/0.5 B5/0.5 A5/0.5 G5/1 F#5/1 | E5/1.5 F#5/0.5 E5/2",
            "lead": "box", "lead_vel": 0.8, "piano": "roll", "piano_vel": 1.0,
            "bass": 0.5, "pad": 1.0,
            "colour": {"flute": ("D5/2 r/2 | r/2 B4/1 G#4/1 | A4/2 r/2 | r/2 F#4/0.5 G4/0.5 B4/1 "
                                 "| C#5/2 r/2 | r/2 A4/0.5 C#5/0.5 E5/1 | D5/2 B4/2 "
                                 "| r/2 C#5/1 G4/1", 4, 0.75)},
            "shaker": 1.0,
        },
        {   # C: a quiet lydian breath, mostly pad, sparse notes, leads home to D
            "chords": "Gmaj7#11:4 Dmaj9/F#:4 Em9:4 A9sus4:4 Gmaj9:4 F#m11:4 Em11:4 A13sus:4",
            "melody": "r/2 C#6/2 | A5/4 | r/1 F#5/1 G5/1 B5/1 | A5/3 r/1 "
                      "| r/2 D6/1 B5/1 | C#6/2 A5/2 | G5/1.5 F#5/0.5 E5/2 | r/2 E5/1 F#5/1",
            "lead": "box", "lead_vel": 0.65, "piano": "whole", "piano_vel": 0.8,
            "bass": 0.35, "pad": 1.5,
            "colour": {"flute": ("B4/2 r/2 | r/4 | A4/1 r/3 | r/2 B4/1 D5/1 | D5/2 r/2 | r/4 "
                                 "| r/2 B4/2 | A4/2 r/2", 4, 0.6)},
        },
    ],
}

NIGHT_A = "Bm9:8 E/B:8 Gmaj9:8 F#m11:8"
# Glassy cello harmonics swell in after each chord change; the clarinet answers low.
NIGHT_A_COLOUR = {
    "cello": ("r/2 F#5/6 | r/2 E5/6 | r/2 D5/6 | r/2 C#5/6", 8, 0.8),
    "clarinet": ("r/4 | r/2 F#3/2 | G#3/4 | r/2 B3/1 G#3/1 | F#3/4 | r/2 D4/1 B3/1 | C#4/4 "
                 "| r/2 E4/1 C#4/1", 4, 0.7),
}

NIGHT = {
    "bpm": 72,
    "tail": 10.0,
    "box_octave": 2.0,  # the box sits an octave above the written line, clear of the pad
    "pad_cutoff": 1500.0,
    "reverb": (4.5, 3.0, 1.4),  # a larger, darker space
    "mix": {"box": (0.5, 0.7), "piano": (1.1, 0.45), "pad": (0.07, 0.5), "bass": (0.39, 0.05)},
    "colour": {"cello": (0.1, 0.7, -0.4), "clarinet": (0.19, 0.5, 0.3)},
    "sections": [
        {   # A: the day motif at half speed, on a distant music box
            "chords": NIGHT_A,
            "melody": "r/2 A4/1 B4/1 | C#5/3 A4/1 | B4/3 G#4/1 | E4/4 "
                      "| r/1 F#4/1 A4/1 E5/1 | D5/4 | C#5/2 B4/1 A4/1 | B4/4",
            "lead": "box", "lead_vel": 0.75, "piano": "whole", "piano_vel": 0.7,
            "bass": 0.4, "pad": 1.0,
            "colour": NIGHT_A_COLOUR,
        },
        {   # B: low felt piano takes the line
            "chords": "Em9:8 Bm9/D:8 Gmaj7#11:8 A13sus:8",
            "melody": "r/2 G4/1 B4/1 | F#5/4 | r/1 F#4/1 A4/1 C#5/1 | B4/4 "
                      "| r/2 C#5/2 | B4/2 A4/1 F#4/1 | r/1 E4/1 F#4/1 D5/1 | B4/2 r/2",
            "lead": "piano", "lead_vel": 0.5, "piano": "whole", "piano_vel": 0.6,
            "bass": 0.4, "pad": 1.1,
            "colour": {"cello": ("r/2 B4/6 | r/2 F#5/6 | r/2 D5/6 | r/2 E5/6", 8, 0.8),
                       "clarinet": ("E3/4 | r/2 G3/1 B3/1 | D4/4 | r/2 F#3/2 | G3/4 | r/2 B3/2 "
                                    "| A3/4 | r/2 B3/1 D4/1", 4, 0.65)},
        },
        {   # A': theme again, a new cadence
            "chords": NIGHT_A,
            "melody": "r/2 A4/1 B4/1 | C#5/3 A4/1 | B4/3 G#4/1 | E4/4 "
                      "| r/1 F#4/1 A4/1 E5/1 | D5/4 | C#5/1 E5/1 B4/2 | A4/4",
            "lead": "box", "lead_vel": 0.75, "piano": "whole", "piano_vel": 0.7,
            "bass": 0.4, "pad": 1.0,
            "colour": NIGHT_A_COLOUR,
        },
        {   # C: almost only pad and space, a few notes leading back to B minor
            "chords": "Gmaj9:8 Dmaj9/F#:8 Em11:8 F#7sus4:8",
            "melody": "r/4 | r/2 B4/2 | A4/4 | r/4 | r/2 G4/1 A4/1 | B4/4 | r/4 | r/2 B4/1 C#5/1",
            "lead": "box", "lead_vel": 0.6, "piano": "whole", "piano_vel": 0.5,
            "bass": 0.3, "pad": 1.4,
            "colour": {"cello": ("r/2 B4/6 | r/2 C#5/6 | r/2 D5/6 | r/2 E5/6", 8, 0.7),
                       "clarinet": ("r/4 | G3/4 | r/4 | F#3/4 | r/4 | E3/4 | r/4 "
                                    "| F#3/2 C#4/2", 4, 0.6)},
        },
    ],
}


def day(rng):
    return render(DAY, rng)


def night(rng):
    return render(NIGHT, rng)
