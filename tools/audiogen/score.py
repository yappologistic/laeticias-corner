"""Note-data notation and the renderer for the city pieces.

A part is a string of tokens separated by spaces, with `|` bar lines:

    E5'D5/1!    grace note(s) E5 then D5, one beat, accented
    D3+A3/2     a dyad (plucked as a quick strum), two beats
    A4/2_3=     two thirds of a beat (triplets), slurred from the previous note (pipes)
    r/0.5       half a beat of rest

Flags: `!` accent, `?` soft, `=` slur (reeds glide in without re-tonguing). Lengths are exact
fractions (`1.5`, `2_3`), so bar sums never drift. A `|` asserts that the line sits on a bar
boundary; a long note may cross several bars. Percussion parts use stroke letters instead of
pitches: D (low centre), T (edge), k (soft tap), C (clapper), K (krotala), Y (cymbals),
S (sistrum).

A piece is a dict: bpm, meter (bar lengths in beats, cycled), reverb, an optional rubato
(beats of push and pull per phrase), an optional offset (beats: where a positional loop's file
starts, so its seam falls between attacks), `blocks` (reverb a block at a time, for pieces of
minutes), and parts, each naming its voice, gain, pan and reverb send (`phrases`: a reed part
that rests for bars is played phrase by phrase). The render is an exact number of beats long with every tail folded onto the start."""

import re
from fractions import Fraction

import numpy as np

import ancient
from dsp import (SR, circular, highpass, impulse_response, lowpass, midi_hz, pan, place, secs,
                 with_reverb, wrap)

NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PITCH = r"[A-G]#?\d"
TOKEN = re.compile(rf"^((?:{PITCH}')*)({PITCH}(?:\+{PITCH})*|r|[DTkCKYS])/([\d._]+)([!?=]*)$")
ACCENT = {"!": 1.25, "?": 0.6}


def midi(name):
    """'F#5' -> 78."""
    return 12 * (int(name.lstrip("ABCDEFG#")) + 1) + NOTE_INDEX[name[0]] + name.count("#")


def length(text):
    return Fraction(*map(int, text.split("_"))) if "_" in text else Fraction(text)


def parse(text, meter):
    """Tokens -> list of events {beat, pitches|stroke, graces, beats, vel, slur}, and the
    total length in beats. Checks every bar line against the cycled meter."""
    bounds, b = [], Fraction(0)
    events, beat = [], Fraction(0)
    for tok in text.split():
        if tok == "|":
            while not bounds or bounds[-1] < beat:
                b += meter[len(bounds) % len(meter)]
                bounds.append(b)
            assert bounds[-1] == beat, f"bar line at beat {beat} is not on a bar boundary: {text[:60]}"
            continue
        m = TOKEN.match(tok)
        assert m, f"bad token {tok!r}"
        graces, body, size, flags = m.groups()
        beats = length(size)
        if body != "r":
            vel = np.prod([ACCENT[f] for f in flags if f in ACCENT]) if flags else 1.0
            ev = {"beat": beat, "beats": beats, "vel": float(vel), "slur": "=" in flags,
                  "graces": [midi(g) for g in graces.split("'") if g]}
            if body in "DTkCKYS" and len(body) == 1:
                ev["stroke"] = body
            else:
                ev["pitches"] = [midi(p) for p in body.split("+")]
            events.append(ev)
        beat += beats
    return events, beat


def fmt(beats):
    """A length as notation: 3, 1.5 or 2_3."""
    beats = Fraction(beats)
    if beats.denominator == 1:
        return str(beats.numerator)
    return f"{beats.numerator}_{beats.denominator}"


def sparse(meter, bars, notes):
    """A part that plays in only a few bars: `notes` maps a bar number (from 1) to its tokens;
    every other bar rests. Tokens longer than their bar carry on through the following bars
    (a held drone), padded with rest to the next bar line."""
    meter = [Fraction(m) for m in meter]
    assert all(1 <= b <= bars for b in notes), f"bars outside 1..{bars}: {sorted(notes)}"
    out, i = [], 1
    while i <= bars:
        text = notes.get(i)
        if text is None:
            out.append(f"r/{fmt(meter[(i - 1) % len(meter)])}")
            i += 1
            continue
        size = sum(length(TOKEN.match(tok).group(3)) for tok in text.split())
        span, j = Fraction(0), i
        while span < size:
            span += meter[(j - 1) % len(meter)]
            j += 1
        assert not any(i < b < j for b in notes), f"bar {i}'s notes run into a later entry"
        assert j - 1 <= bars, f"bar {i}'s notes run past the end"
        out.append(text + (f" r/{fmt(span - size)}" if span > size else ""))
        i = j
    return " | ".join(out)


def nocturne(piece, changes, **top):
    """The night arrangement of a piece: the same bars at the same tempo (the engine plays day
    and night together, sample-aligned, and cross-fades them by the clock), with parts given
    to softer voices (`changes` maps a part to the keys it changes), left out (None), or new
    parts of the night's own."""
    night = {**piece, **top, "parts": {}}
    for name, part in piece["parts"].items():
        if name in changes and changes[name] is None:
            continue
        night["parts"][name] = {**part, **changes.get(name, {})}
    for name, part in changes.items():  # a night-only part (a hummed drone)
        if name not in piece["parts"] and part is not None:
            night["parts"][name] = part
    return night


def bar_count(beats, meter):
    """Whole bars in `beats` under the cycled meter (asserts it ends on a bar line)."""
    n, b = 0, Fraction(0)
    while b < beats:
        b += meter[n % len(meter)]
        n += 1
    assert b == beats, f"{beats} beats is not a whole number of bars"
    return n


def timing(piece, total):
    """Beat -> seconds, with optional rubato: each phrase eases in, flows, and broadens at
    its end; the curve is periodic in the phrase, so the loop length stays exact."""
    beat_s = 60.0 / piece["bpm"]
    push, phrase = piece.get("rubato", (0.0, 8))
    assert push == 0 or total % phrase == 0, "rubato phrases must tile the loop"
    k = push * 2 * np.pi / phrase
    assert k < 0.8, "rubato too strong: time would run backwards"

    def at(b):
        b = float(b)
        return beat_s * (b + push * np.sin(2 * np.pi * b / phrase))

    return at


def breaths(notes, gap=1.0):
    """Reed notes grouped into phrases wherever the player rests at least `gap` seconds."""
    groups = [[notes[0]]]
    for prev, note in zip(notes, notes[1:]):
        if note[0] - (prev[0] + prev[1]) >= gap:
            groups.append([])
        groups[-1].append(note)
    return groups


def render_part(part, events, at, n, rng):
    """One part to a stereo buffer of n samples (dry, before gain)."""
    voice = part["voice"]
    out = np.zeros((n, 2))
    position = part.get("pan", 0.0)
    jitter = part.get("jitter", 0.006)
    if voice in ancient.PIPES:
        notes = []
        for ev in events:
            start = at(ev["beat"])
            dur = at(ev["beat"] + ev["beats"]) - start - (0.0 if part.get("legato") else 0.03)
            notes.append((start, dur, float(midi_hz(ev["pitches"][0] + part.get("octave", 0))),
                          ev["vel"] * part.get("vel", 0.8), ev["slur"],
                          [float(midi_hz(g + part.get("octave", 0))) for g in ev["graces"]]))
        if not part.get("phrases"):
            return pan(ancient.reed_phrase(voice, notes, n, rng), position)
        # A part that rests for bars at a time is played phrase by phrase (the player breathes
        # in the rests), each phrase in its own short buffer, so a long sparse piece stays small.
        for phrase in breaths(notes):
            t0 = phrase[0][0]
            end = max(s + d for s, d, *_ in phrase) + 0.2
            shifted = [(s - t0, *rest) for s, *rest in phrase]
            place(out, pan(ancient.reed_phrase(voice, shifted, secs(end - t0), rng), position),
                  secs(t0))
        return out
    for ev in events:
        start = at(ev["beat"]) + rng.normal(0, jitter)
        dur = at(ev["beat"] + ev["beats"]) - at(ev["beat"])
        vel = ev["vel"] * part.get("vel", 0.8) * rng.uniform(0.9, 1.04)
        if "stroke" in ev:
            s = ev["stroke"]
            if s in "DTk":
                x = ancient.frame_drum(s, vel, rng, part.get("tune", 92.0))
            elif s in "CK":
                x = ancient.clapper(vel, rng, part.get("tune", 1300.0), double=s == "K")
            elif s == "Y":
                x = ancient.cymbals(vel, rng, part.get("tune", 1180.0))
            else:
                x = ancient.sistrum(vel, rng)
            place(out, pan(x, position), max(0, secs(start)))
            continue
        pitches = [p + part.get("octave", 0) for p in ev["pitches"]]
        for i, m in enumerate(pitches):
            f = float(midi_hz(m))
            spread = position + part.get("spread", 0.0) * (m - 62) / 24
            t0 = start + i * part.get("strum", 0.03)
            if voice in ancient.STRINGS:
                ring = max(dur + 0.3, part.get("ring", 2.5))
                damp = dur + 0.05 if part.get("damp") else None
                for gi, gm in enumerate(ev["graces"]):
                    gx = ancient.string(voice, float(midi_hz(gm + part.get("octave", 0))), 0.4,
                                        vel * 0.7, rng, damp=0.08)
                    place(out, pan(gx, spread), max(0, secs(t0 - 0.07 * (len(ev["graces"]) - gi))))
                x = ancient.string(voice, f, ring, vel, rng, damp=damp)
            elif voice == "organ":
                x = ancient.hydraulis(f, dur, vel, rng)
            elif voice == "horn":
                x = ancient.horn(f, dur, vel, rng, part.get("bright", 1.0))
            elif voice == "hum":
                x = sum(ancient.hum(f * (1 + d), dur, vel / part.get("voices", 1), rng,
                                    vowel=part.get("vowel", "m"))
                        for d in np.linspace(-0.004, 0.004, part.get("voices", 1)))
            elif voice == "flute":
                x = ancient.flute(f, dur, vel, rng)
            elif voice == "syrinx":
                x = ancient.syrinx(f, dur, vel, rng)
            else:
                raise ValueError(voice)
            place(out, pan(x, spread), max(0, secs(t0)))
    return out


def render(piece, rng, parts_out=False, one_shot=None):
    """Render a piece to a stereo loop of exactly its length, tails folded onto the start.
    With parts_out, also return each part's own (dry + wet) loop for level checks; with
    one_shot (seconds), render a phrase that is not a loop: no folding, cut to that length."""
    meter = [Fraction(m) for m in piece["meter"]]
    parsed = {name: parse(p["notes"], meter) for name, p in piece["parts"].items()}
    lengths = {name: total for name, (_, total) in parsed.items()}
    total = next(iter(lengths.values()))
    assert all(v == total for v in lengths.values()), f"parts differ in length: {lengths}"
    bar_count(total, meter)
    at = timing(piece, total)
    loop_n = secs(at(total))
    assert abs(at(total) * SR - loop_n) < 1e-6, "loop must be an exact number of samples"
    n = max(loop_n + secs(piece.get("tail", 8.0)), secs(one_shot or 0))
    length_s, t_low, t_high, predelay = piece["reverb"]
    ir = impulse_response(rng, length_s, t_low, t_high, predelay=predelay)
    dry, send = np.zeros((n, 2)), np.zeros((n, 2))
    stems = {}
    for name, part in piece["parts"].items():
        # In place, so a long piece holds as few full-length buffers as it can.
        x = render_part(part, parsed[name][0], at, n, rng)
        x *= part["gain"]
        dry += x
        if parts_out:
            stems[name] = (x, x * part["send"])
            send += stems[name][1]
        else:
            x *= part["send"]
            send += x
        del x

    def finish(d, s):
        if one_shot:
            out = with_reverb(d, s, ir, piece.get("wet", 1.0))[: secs(one_shot)]
            return lowpass(highpass(out, 35, 2), 8000, 2)
        out = wrap(with_reverb(d, s, ir, piece.get("wet", 1.0), piece.get("blocks", False)),
                   loop_n)
        for c in range(2):  # a channel at a time: the same filter, half the temporaries
            out[:, c] = circular(lambda y: lowpass(highpass(y, 35, 2), 8000, 2), out[:, c])
        return out

    mix = finish(dry, send)
    del dry, send
    if piece.get("offset") and not one_shot:
        # A positional loop has no musical start: begin it between attacks, not on a downbeat.
        shift = secs(at(Fraction(piece["offset"]).limit_denominator(64)))
        mix = np.roll(mix, -shift, axis=0)
    if not parts_out:
        return mix
    return mix, {k: finish(*v) for k, v in stems.items()}


def info(piece):
    """Loop facts the engine needs: length, tempo, metre and where phrases begin."""
    meter = [Fraction(m) for m in piece["meter"]]
    total = parse(next(iter(piece["parts"].values()))["notes"], meter)[1]
    at = timing(piece, total)
    # Phrases every `phrase` beats, or at the listed beats where a piece's phrases are uneven
    # (each in the breath before a phrase, so the engine's fade-in lands on its first note).
    phrase = piece.get("phrase", 8)
    starts = phrase if isinstance(phrase, (list, tuple)) else range(0, int(total), phrase)
    assert all(0 <= b < total for b in starts), "phrase starts outside the piece"
    return {"bpm": piece["bpm"], "meter": [int(m) for m in meter],
            "bars": bar_count(total, meter), "beats": int(total),
            "samples": secs(at(total)),
            "phrase_starts_s": [float(round((at(b) - at(piece.get("offset", 0))) % at(total), 4))
                                for b in starts]}
