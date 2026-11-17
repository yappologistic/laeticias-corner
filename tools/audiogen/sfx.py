"""Short mono effects. Each starts and ends at silence, stays soft and below ~8 kHz,
and is built from a few physical-ish layers (modes, filtered noise, voiced glides)."""

import numpy as np
from scipy import signal

import instruments as ins
import music
from dsp import (bandpass, fade, formant_noise, glide, highpass, impulse_response, line,
                 lowpass, midi_hz, perc, phase_of, place, ramp_in, secs, sweep_lowpass, times,
                 voice, wobble)


def modes(n, freqs, amps, decays, rng):
    """A struck object: decaying sine modes with random phases."""
    t = times(n)
    out = np.zeros(n)
    for f, a, d in zip(freqs, amps, decays):
        out += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / d)
    return out * ramp_in(n, secs(0.0006))  # random phases must not start with a step


def noise_burst(n, rng, lo, hi, attack, decay):
    return bandpass(rng.standard_normal(n), lo, hi) * perc(n, attack, decay)


def room(x, rng, wet=0.15, size=0.3):
    """A touch of small-room reverb, mixed to mono, tail kept."""
    ir = impulse_response(rng, size, size * 0.6, size * 0.3, predelay=0.004).mean(axis=1)
    out = wet * signal.oaconvolve(x, ir)
    out[: len(x)] += x
    return out


def finish(x, fade_in=0.002, fade_out=0.02, length=None):
    """Trim the inaudible tail (below -60 dB of peak), or cut / pad to exactly `length`
    seconds, and fade both ends to zero."""
    if length:
        x = np.pad(x, (0, max(0, secs(length) - len(x))))[: secs(length)]
    else:
        peak = np.max(np.abs(x))
        loud = np.nonzero(np.abs(x) > peak * 10 ** (-60 / 20))[0]
        x = x[: loud[-1] + 1] if len(loud) else x
    return fade(x, fade_in, fade_out)


# --- placement -------------------------------------------------------------------------


def place_soft(rng):
    """Leafy, earthy pat: a soft low thump, a muffled soil puff, and leaf rustle."""
    n = secs(0.22)
    t = times(n)
    thump = np.sin(phase_of(glide(n, [(0, 150), (0.08, 70)]))) * np.exp(-t / 0.035)
    soil = lowpass(rng.standard_normal(n), 900) * perc(n, 0.003, 0.03)
    rustle = np.zeros(n)
    for _ in range(9):
        g = secs(rng.uniform(0.004, 0.012))
        grain = bandpass(rng.standard_normal(g), 1500, 4500) * np.hanning(g)
        place(rustle, grain * rng.uniform(0.3, 1.0), secs(rng.uniform(0.0, 0.09)))
    return finish(room(thump + 0.6 * soil + 0.25 * rustle, rng, 0.1))


def place_wood(rng):
    """Wooden knock: a short block-like modal hit over a round low body."""
    n = secs(0.25)
    f0 = 340.0
    hit = modes(n, [f0, f0 * 2.31, f0 * 3.87, f0 * 5.4], [1.0, 0.55, 0.3, 0.12],
                [0.05, 0.03, 0.018, 0.01], rng)
    body = modes(n, [130, 210], [0.7, 0.3], [0.05, 0.035], rng)
    click = lowpass(rng.standard_normal(n) * perc(n, 0.0003, 0.002), 4000)
    return finish(room(lowpass(hit + body + 0.4 * click, 6000), rng, 0.12))


def place_stone(rng):
    """Stone clack: two small stones meeting, bright but short, with a grainy edge."""
    n = secs(0.2)
    f0 = 1250.0
    hit = modes(n, [f0, f0 * 1.63, f0 * 2.72, f0 * 3.9], [1.0, 0.7, 0.4, 0.15],
                [0.022, 0.016, 0.01, 0.007], rng)
    grit = noise_burst(n, rng, 1500, 5000, 0.0003, 0.006)
    thud = modes(n, [110, 180], [0.8, 0.4], [0.03, 0.02], rng)
    second = np.zeros(n)
    place(second, 0.35 * modes(secs(0.06), [f0 * 1.1, f0 * 1.9], [1.0, 0.5], [0.012, 0.008], rng),
          secs(0.028))
    mix = hit + 0.5 * grit + thud + second
    return finish(room(lowpass(mix, 6500), rng, 0.12))


def splash(rng):
    """Small water plop: the classic rising bubble 'bloop', a soft spray, droplets."""
    n = secs(0.45)
    t = times(n)
    bloop = np.sin(phase_of(glide(n, [(0, 260), (0.06, 820), (0.1, 900)]))) * perc(n, 0.002, 0.045)
    spray = noise_burst(n, rng, 600, 3500, 0.004, 0.06)
    drops = np.zeros(n)
    for _ in range(5):
        f = rng.uniform(900, 2000)
        m = secs(0.05)
        tm = times(m)
        d = np.sin(phase_of(f * (1 + 2 * tm))) * np.exp(-tm / 0.01)
        place(drops, d * rng.uniform(0.15, 0.35), secs(rng.uniform(0.08, 0.3)))
    under = lowpass(rng.standard_normal(n), 300) * np.exp(-t / 0.08)
    mix = lowpass(bloop + 0.35 * spray + drops + 0.4 * under, 4500, 4)
    return finish(room(mix, rng, 0.18), fade_out=0.04)


def paint(rng):
    """Very short soft brush-on-soil swish, gentle enough to repeat rapidly."""
    n = secs(0.085)
    env = np.sin(np.pi * np.arange(n) / n) ** 1.5
    brush = bandpass(rng.standard_normal(n), 700, 3200) * env
    soil = lowpass(rng.standard_normal(n), 400) * env
    return finish(lowpass(brush + 0.8 * soil, 5000, 4), 0.003, 0.015)


def remove(rng):
    """Soft poof: an airy puff whose colour sinks as it fades, with a faint drop."""
    n = secs(0.32)
    cutoff = glide(n, [(0, 2200), (0.3, 300)])
    puff = sweep_lowpass(rng.standard_normal(n), cutoff)
    puff *= perc(n, 0.012, 0.08)
    sink = np.sin(phase_of(glide(n, [(0, 320), (0.2, 160)]))) * perc(n, 0.01, 0.06)
    return finish(room(lowpass(puff, 3500, 4) + 0.5 * sink, rng, 0.15), fade_out=0.05)


def rotate(rng):
    """Light turn: a quick airy swish rising in colour, ending in a tiny wooden tick."""
    n = secs(0.16)
    t = times(n)
    env = np.sin(np.pi * np.clip(t / 0.11, 0, 1)) ** 2
    swish = bandpass(rng.standard_normal(n), 900, 2600) * env
    tick = np.zeros(n)
    place(tick, modes(secs(0.04), [1900, 3100], [1.0, 0.4], [0.006, 0.004], rng), secs(0.1))
    return finish(lowpass(0.6 * swish + tick, 5000, 4))


def invalid(rng):
    """Muted 'nope': two soft low notes falling a minor third, round and short."""
    out = np.zeros(secs(0.42))
    for i, (m, at) in enumerate(((57, 0.0), (54, 0.13))):  # A3 -> F#3
        n = secs(0.25)
        t = times(n)
        f = midi_hz(m)
        ph = 2 * np.pi * f * t
        x = (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)) * perc(n, 0.008, 0.07)
        place(out, x * (1.0 if i == 0 else 0.85), secs(at))
    return finish(lowpass(room(out, rng, 0.1), 2000))


def _two_tines(rng, first, second):
    """Two quick music-box notes; the shared gesture behind undo and redo."""
    out = np.zeros(secs(0.5))
    for i, m in enumerate((first, second)):
        x = ins.tine(midi_hz(m), 0.4, 0.6, rng) * np.exp(-times(secs(0.4)) / 0.09)
        place(out, x * (1.0 if i else 0.8), secs(0.07 * i))
    return finish(room(out, rng, 0.12), fade_out=0.06)


def undo(rng):
    return _two_tines(rng, 81, 76)  # A5 -> E5: a step back


def redo(rng):
    return _two_tines(rng, 78, 83)  # F#5 -> B5: the same step forward, a little higher


# --- interface -------------------------------------------------------------------------


def ui_hover(rng):
    """Barely-there tick."""
    n = secs(0.03)
    return finish(modes(n, [1700, 2900], [1.0, 0.3], [0.004, 0.002], rng), 0.0005, 0.008)


def ui_click(rng):
    """Soft click: a small rounded tap with a hint of body."""
    n = secs(0.06)
    x = modes(n, [950, 2100, 3300], [1.0, 0.5, 0.15], [0.01, 0.005, 0.003], rng)
    x += 0.15 * lowpass(rng.standard_normal(n) * perc(n, 0.0002, 0.0015), 5000)
    return finish(x, 0.0005, 0.012)


def _pop(rng, start, end):
    """A small bubble-like pop gliding between two pitches."""
    n = secs(0.12)
    x = np.sin(phase_of(glide(n, [(0, start), (0.07, end)]))) * perc(n, 0.004, 0.035)
    x += 0.3 * np.sin(2 * phase_of(glide(n, [(0, start), (0.07, end)]))) * perc(n, 0.004, 0.02)
    return finish(room(x, rng, 0.08), 0.001, 0.02)


def ui_open(rng):
    return _pop(rng, 420, 880)


def ui_close(rng):
    return _pop(rng, 880, 420)


def shutter(rng):
    """Camera shutter: an opening snap, a short mechanical whirr, a closing clack."""
    n = secs(0.2)
    out = np.zeros(n)
    for at, f, level in ((0.0, 2400, 1.0), (0.075, 1800, 0.8)):
        m = secs(0.04)
        click = noise_burst(m, rng, 1500, 6000, 0.0002, 0.003)
        click += modes(m, [f, f * 1.7, 700], [0.6, 0.3, 0.4], [0.008, 0.005, 0.012], rng)
        place(out, click * level, secs(at))
    whirr = bandpass(rng.standard_normal(n), 800, 2500) * np.clip(
        line(n, [(0, 0), (0.01, 0.12), (0.07, 0.12), (0.08, 0)]), 0, None)
    return finish(room(lowpass(out + whirr, 7000), rng, 0.1))


def discover(rng):
    """Happy chime: A5 D6 F#6 A6 on the music box, the day theme's key (D major)."""
    out = np.zeros(secs(1.8))
    for i, m in enumerate((81, 86, 90, 93)):
        x = ins.tine(midi_hz(m), 1.5, 0.75, rng)
        place(out, x * (0.75 + 0.1 * i), secs(0.09 * i))
    return finish(room(out, rng, 0.25, 1.0), fade_out=0.3)


# --- animals ---------------------------------------------------------------------------


def duck(rng):
    """A mallard's 'QUACK-quack': nasal, a little raspy (period doubling), each call
    snapping open and sagging in pitch, the second softer and lower."""
    out = np.zeros(secs(0.5))
    for i, (at, scale, level) in enumerate(((0.0, 1.0, 1.0), (0.22, 0.93, 0.7))):
        dur = 0.17 - 0.02 * i
        n = secs(dur)
        f0 = glide(n, [(0, 300 * scale), (0.025, 330 * scale), (dur, 245 * scale)])
        f1 = line(n, [(0, 600), (0.03, 950), (dur, 750)])
        f2 = line(n, [(0, 1300), (0.03, 1600), (dur, 1400)])
        formants = [(f1, 300, 1.0), (f2, 350, 0.8), (2600, 500, 0.3), (3500, 700, 0.08)]
        x = voice(f0, formants, rng, tilt=0.7, jitter=0.012, shimmer=0.12, breath=0.25, sub=0.35)
        env = ramp_in(n, secs(0.008)) * np.exp(-np.clip(times(n) - 0.03, 0, None) / 0.07)
        place(out, x * env * ramp_in(n, secs(0.03))[::-1] * level, secs(at))
    return finish(room(lowpass(out, 5000), rng, 0.08))


def hen(rng):
    """Contented clucking: two short 'buk's, then a rising, rough 'bu-kaawk', each with a
    tiny burst of breath at its onset like a real syllable."""
    out = np.zeros(secs(0.7))
    calls = ((0.0, 0.055, 330, 300, 0.75, 0.0), (0.15, 0.055, 345, 305, 0.7, 0.0),
             (0.31, 0.045, 360, 330, 0.6, 0.0), (0.37, 0.24, 430, 380, 1.0, 0.3))
    for at, dur, top, end, level, rough in calls:
        n = secs(dur)
        long = dur > 0.1
        pts = [(0, top), (dur * 0.35, top * (1.35 if long else 1.05)), (dur, end)]
        f1 = line(n, [(0, 450), (dur * 0.3, 850 if long else 650), (dur, 600)])
        formants = [(f1, 250, 1.0), (1700 if long else 1300, 400, 0.45), (2900, 600, 0.12)]
        x = voice(glide(n, pts), formants, rng, tilt=0.9, jitter=0.015, shimmer=0.15,
                  breath=0.3, sub=rough)
        env = (ramp_in(n, secs(0.004)) * np.exp(-times(n) / (dur * 0.6))
               * ramp_in(n, secs(0.015))[::-1])
        place(out, x * env * level, secs(at))
    return finish(room(lowpass(out, 5000), rng, 0.08))


def cat(rng):
    """A friendly 'mrrp-miaow': a purred trill opening into an 'ee-ah-ow' whose mouth
    closes as the pitch arches and sags, with breath and the slight waver of a real cat."""
    dur = 0.6
    n = secs(dur)
    t = times(n)
    f0 = glide(n, [(0, 380), (0.1, 450), (0.22, 640), (0.36, 680), (0.48, 560), (dur, 470)])
    f1 = line(n, [(0, 400), (0.12, 450), (0.25, 900), (0.42, 750), (dur, 480)])
    f2 = line(n, [(0, 1700), (0.12, 2200), (0.25, 1700), (0.42, 1200), (dur, 950)])
    formants = [(f1, 220, 1.0), (f2, 300, 0.6), (3300, 500, 0.15), (4500, 800, 0.05)]
    x = voice(f0 * (1 + 0.006 * np.sin(2 * np.pi * 7 * t)), formants, rng, tilt=1.0,
              jitter=0.008, shimmer=0.08, breath=0.18)
    trill = 1 - 0.55 * (t < 0.13) * (0.5 + 0.5 * np.cos(2 * np.pi * 26 * t))
    env = np.clip(line(n, [(0, 0), (0.025, 0.5), (0.13, 0.6), (0.3, 1.0), (0.45, 0.7),
                           (dur, 0)]), 0, 1)
    return finish(room(lowpass(x * trill * env, 5500), rng, 0.08), fade_out=0.04)


# --- tuned placement notes -------------------------------------------------------------

NOTES = ("D4", "E4", "F#4", "A4", "B4", "D5", "E5", "F#5", "A5", "B5")  # D major pentatonic


def note(index):
    """Renderer for tuned placement note `index`: a kalimba tine (the music box's voice)
    with a padded strike, 1.2 s of natural decay and a touch of room, so quick building
    plays a soft phrase whose tails overlap without clashing."""
    f = midi_hz(music.midi(NOTES[index]))

    def render(rng):
        out = np.zeros(secs(1.2))
        # A shorter ring than the music's tines, the same for every pitch, so rapid notes
        # overlap as a soft phrase instead of piling up into a sustained cluster.
        x = ins.tine(f, 1.2, 0.6, rng) * np.exp(-times(secs(1.2)) / 0.45)
        place(out, highpass(room(x, rng, 0.12, 0.6), 150)[: len(out)], 0)
        return fade(out, 0.0015, 0.25)
    return render


# --- interface stingers ----------------------------------------------------------------


def paper(rng, dur, lo=900, hi=5500):
    """Paper sliding: band-limited noise crinkled by an irregular grain envelope."""
    n = secs(dur)
    crinkle = np.abs(lowpass(rng.standard_normal(n), 90)) * 4 + 0.3
    swell = np.sin(np.pi * times(n) / dur) ** 1.5
    return bandpass(rng.standard_normal(n), lo, hi) * crinkle * swell


def tines(rng, notes, spacing, ring, vel=0.7, rise=0.0):
    """A quick run of music-box tines (names), each a little louder than the last."""
    out = np.zeros(secs(spacing * len(notes) + ring))
    for i, name in enumerate(notes):
        x = ins.tine(midi_hz(music.midi(name)), ring, vel * (1 + rise * i), rng)
        place(out, x, secs(spacing * i))
    return out


def wish(rng):
    """A wish card slipping into the tray, then two rising notes, D5 and A5."""
    out = np.zeros(secs(0.8))
    place(out, 0.35 * paper(rng, 0.16), 0)
    place(out, tines(rng, ("D5", "A5"), 0.13, 0.6), secs(0.12))
    return finish(room(out, rng, 0.15, 0.6), fade_out=0.15, length=0.8)


def wish_granted(rng):
    """Warm four-note rise D5 F#5 A5 D6 on the kalimba, the top doubled by a soft bell,
    over a quiet low D that gives it a floor."""
    out = np.zeros(secs(1.4))
    place(out, tines(rng, ("D5", "F#5", "A5", "D6"), 0.1, 1.0, 0.65, 0.08), 0)
    place(out, 0.35 * ins.bell(midi_hz(86), 1.1, 1.0, rng), secs(0.3))
    hum = ins.pad(midi_hz(50), 0.6, 1.0, rng, attack=0.15, release=0.6, cutoff=900).mean(axis=1)
    place(out, 0.25 * hum / np.max(np.abs(hum)), 0)
    return finish(room(out, rng, 0.2, 0.8), fade_out=0.3, length=1.4)


def nook(rng):
    """A nook found: a shimmering pentatonic harp arpeggio rising over two octaves,
    with rubbed-glass tones blooming under the top."""
    out = np.zeros(secs(2.0))
    for i, name in enumerate(("D4", "A4", "D5", "E5", "F#5", "A5", "B5", "D6")):
        place(out, ins.harp(midi_hz(music.midi(name)), 1.6, 0.55 + 0.04 * i, rng), secs(0.075 * i))
    for name, at in (("A5", 0.45), ("D6", 0.55), ("F#5", 0.5)):
        place(out, 0.12 * ins.glass(midi_hz(music.midi(name)), 1.4, 1.0, rng), secs(at))
    return finish(room(out, rng, 0.25, 1.0), fade_out=0.35, length=2.0)


def land_open(rng):
    """New land opening: a sweep of leaf rustle rising in density and colour, carried
    by a low warm D swell that blooms and settles."""
    n = secs(3.0)
    t = times(n)
    density = np.clip(line(n, [(0, 0.0), (1.4, 1.0), (2.2, 0.7), (3.0, 0.0)]), 0, 1)
    leaves = np.zeros(n)
    for _ in range(260):
        at = int(rng.choice(n, p=density / density.sum()))
        g = secs(rng.uniform(0.004, 0.015))
        centre = 1200 + 2500 * t[at] / 3.0
        grain = bandpass(rng.standard_normal(g), centre * 0.6, min(centre * 1.6, 6500))
        place(leaves, grain * np.hanning(g) * rng.uniform(0.3, 1.0), at)
    swell = sum(ins.pad(midi_hz(m), 1.8, 1.0, rng, attack=1.0, release=1.2, cutoff=900).mean(axis=1)
                for m in (38, 50, 57, 62))
    wind = sweep_lowpass(rng.standard_normal(n), glide(n, [(0, 300), (1.5, 1800), (3.0, 500)]))
    wind *= density / (np.std(wind) + 1e-12)
    out = 0.35 * leaves + 0.05 * wind
    place(out, 0.5 * swell / np.max(np.abs(swell)), 0)
    return finish(room(lowpass(out, 6500, 4), rng, 0.2, 1.0), fade_out=0.4, length=3.0)


def season(rng):
    """A new season: a breath of wind swelling and passing under a soft chime, A5 and D6
    with a bell an octave down."""
    n = secs(2.5)
    t = times(n)
    breath = sweep_lowpass(rng.standard_normal(n), glide(n, [(0, 250), (1.0, 1400), (2.5, 300)]))
    breath = highpass(breath, 150) * np.sin(np.pi * np.clip(t / 2.4, 0, 1)) ** 2
    out = 0.1 * breath / (np.std(breath) + 1e-12)
    place(out, tines(rng, ("A5", "D6"), 0.16, 1.8, 0.6), secs(0.35))
    place(out, 0.3 * ins.bell(midi_hz(74), 1.8, 1.0, rng), secs(0.35))
    return finish(room(out, rng, 0.25, 1.0), fade_out=0.4, length=2.5)


# --- garden and nature -----------------------------------------------------------------


def leaf_grains(n, rng, count, density, lo=1500, hi=5500):
    """Dry leaf rustle: many tiny band-limited noise grains placed by a density curve."""
    out = np.zeros(n)
    p = density / density.sum()
    for at in rng.choice(n, count, p=p):
        g = secs(rng.uniform(0.003, 0.012))
        grain = bandpass(rng.standard_normal(g), lo, hi) * np.hanning(g)
        place(out, grain * rng.uniform(0.3, 1.0), int(at))
    return out


def harvest(rng):
    """Picking a crop: an earthy pluck as the stem lets go, a crumble of soil, and a
    leafy pop as it comes free."""
    n = secs(0.5)
    t = times(n)
    pluck = ins.harp(midi_hz(57), 0.4, 1.0, rng)  # A3, warm and short
    pluck = np.concatenate([pluck * np.exp(-times(len(pluck)) / 0.12), np.zeros(n)])[:n]
    soil = lowpass(rng.standard_normal(n), 700) * perc(n, 0.004, 0.05)
    out = 0.8 * pluck + 0.5 * soil
    m = secs(0.06)
    pop = np.sin(phase_of(glide(m, [(0, 380), (0.04, 760)]))) * perc(m, 0.002, 0.018)
    place(out, 0.7 * pop, secs(0.09))
    out += 0.3 * leaf_grains(n, rng, 25, np.exp(-np.abs(t - 0.13) / 0.05))
    return finish(room(lowpass(out, 6000), rng, 0.1), length=0.5)


def rustle(rng):
    """Leaves shaking in a tree: three quick shakes of dry rustle, fading."""
    n = secs(0.6)
    t = times(n)
    density = sum(a * np.exp(-((t - c) / 0.05) ** 2) for c, a in ((0.08, 1.0), (0.24, 0.8),
                                                                    (0.4, 0.45))) + 0.02
    out = leaf_grains(n, rng, 220, density) + 0.1 * lowpass(rng.standard_normal(n), 900) * density
    return finish(lowpass(out, 6500, 4), 0.003, 0.08, length=0.6)


def flap(rng):
    """A few wing beats: soft feathery thumps of air, slowing as the bird gets away."""
    out = np.zeros(secs(0.5))
    at = 0.0
    for i in range(4):
        n = secs(0.09)
        t = times(n)
        env = (t / 0.02) ** 2 * np.exp(-t / 0.02) / np.exp(-2) * 0.25
        air = bandpass(rng.standard_normal(n), 200, 1800) * env
        feather = bandpass(rng.standard_normal(n), 1500, 4500) * env * 0.25
        place(out, (air + feather) * (1 - 0.15 * i), secs(at))
        at += 0.085 + 0.025 * i
    return finish(room(lowpass(out, 5000, 4), rng, 0.08), fade_out=0.05, length=0.5)


def gust(rng):
    """A passing gust: wind rising through the trees and dying away, a little rustle
    riding its crest."""
    n = secs(2.5)
    t = times(n)
    env = np.clip(line(n, [(0, 0), (1.0, 1.0), (1.4, 0.9), (2.5, 0)]), 0, 1) ** 1.5
    cutoff = glide(n, [(0, 250), (1.1, 1500), (2.5, 300)])
    wind = highpass(sweep_lowpass(rng.standard_normal(n), cutoff), 90)
    wind *= env * wobble(n, rng, 0.25, 4.0) / (np.std(wind) + 1e-12)
    leaves = leaf_grains(n, rng, 200, env**2 + 0.01)
    return finish(lowpass(0.5 * wind + 0.25 * leaves, 6000, 4), 0.01, 0.1, length=2.5)


def rainbow(rng):
    """A rainbow appearing: a slow rising shimmer of glass and tines up the D major
    pentatonic, over a soft bloom of the tonic chord."""
    n = secs(3.0)
    out = np.zeros(n)
    names = ("D5", "E5", "F#5", "A5", "B5", "D6", "E6", "F#6", "A6")
    for i, name in enumerate(names):
        f = midi_hz(music.midi(name))
        place(out, 0.5 * ins.tine(f, 1.4, 0.4 + 0.03 * i, rng), secs(0.2 + 0.22 * i))
        place(out, 0.25 * ins.glass(f, 1.2, 1.0, rng), secs(0.25 + 0.22 * i))
    bloom = sum(ins.pad(midi_hz(m), 1.6, 1.0, rng, attack=1.2, release=1.2, cutoff=1500)
                .mean(axis=1) for m in (62, 66, 69, 74))
    place(out, 0.4 * bloom / np.max(np.abs(bloom)), 0)
    return finish(room(lowpass(out, 6500, 4), rng, 0.3, 1.2), fade_out=0.5, length=3.0)


def twinkle(rng):
    """A tiny sparkle for a shooting star: three quick, soft high tines."""
    out = tines(rng, ("F#6", "A6", "D7"), 0.045, 0.45, 0.5, -0.15)
    return finish(room(lowpass(out, 6500, 4), rng, 0.2, 0.6), fade_out=0.12, length=0.6)


def well(rng):
    """A pebble into the well: a small plip, then its echo coming back up the shaft,
    darker with each return, over a deep hollow resonance."""
    n = secs(1.0)
    m = secs(0.05)
    tm = times(m)
    plip = np.sin(phase_of(glide(m, [(0, 650), (0.04, 1500)]))) * np.exp(-tm / 0.012)
    plip = plip * ramp_in(m, 4) + 0.2 * lowpass(rng.standard_normal(m), 3000) * np.exp(-tm / 0.002)
    dry = np.zeros(n)
    place(dry, plip, 0)
    out = dry.copy()
    echo = dry
    for k in range(1, 10):
        echo = lowpass(echo, 2500 - 180 * k) * 0.55
        shifted = np.zeros(n)
        place(shifted, echo, secs(0.085 * k))
        out += shifted
    boom = modes(n, [92, 184], [1.0, 0.3], [0.25, 0.12], rng) * ramp_in(n, secs(0.02))
    return finish(room(out + 0.25 * boom, rng, 0.3, 1.0), fade_out=0.25, length=1.0)


def pick(rng):
    """Picking something up: a soft upward lift of air and a light tick as it leaves."""
    n = secs(0.22)
    t = times(n)
    env = np.sin(np.pi * np.clip(t / 0.16, 0, 1)) ** 2
    lift = bandpass(rng.standard_normal(n), 500, 2200) * env
    blip = np.sin(phase_of(glide(n, [(0, 380), (0.12, 640)]))) * env * np.exp(-t / 0.08)
    tick = np.zeros(n)
    place(tick, modes(secs(0.03), [1500, 2600], [1.0, 0.3], [0.004, 0.003], rng), 0)
    out = lowpass(0.4 * lift + 0.5 * blip + 0.6 * tick, 5500, 4)
    return finish(out, 0.001, 0.04, length=0.25)


def page(rng):
    """A sketchbook page turning: a papery swish that peaks and lands with a soft flap."""
    n = secs(0.35)
    out = np.zeros(n)
    place(out, paper(rng, 0.26, 700, 5000), 0)
    m = secs(0.08)
    flop = lowpass(rng.standard_normal(m), 700) * perc(m, 0.003, 0.02)
    place(out, 0.6 * flop, secs(0.24))
    return finish(lowpass(out, 6500, 4), 0.004, 0.04, length=0.35)


# --- critters --------------------------------------------------------------------------


def pet(rng):
    """Petting a voiceless critter: a soft brush of fur and a tiny heart chime."""
    n = secs(0.4)
    t = times(n)
    fur = bandpass(rng.standard_normal(n), 1200, 4500) * np.sin(np.pi * np.clip(t / 0.2, 0, 1)) ** 2
    out = 0.3 * fur
    place(out, tines(rng, ("A5", "D6"), 0.06, 0.3, 0.5), secs(0.1))
    return finish(room(out, rng, 0.15, 0.5), fade_out=0.08, length=0.4)


def purr(rng):
    """A cat purring: a breathy 26 Hz flutter on the out-breath, a softer, slightly
    faster one on the in-breath, through a small nasal throat."""
    out = np.zeros(secs(1.2))
    for at, dur, rate, level in ((0.0, 0.62, 25.0, 1.0), (0.67, 0.5, 27.5, 0.6)):
        n = secs(dur)
        rate_curve = rate * wobble(n, rng, 0.04, 5.0)
        cycle = np.mod(np.cumsum(rate_curve) / 44100, 1.0)
        pulses = (0.5 - 0.5 * np.cos(2 * np.pi * cycle)) ** 5
        source = pulses * (0.4 + rng.standard_normal(n))
        formants = [(250, 180, 1.0), (650, 300, 0.35), (1500, 500, 0.06)]
        throat = formant_noise(n, formants, rng) * pulses + 0.6 * lowpass(source, 900)
        env = np.sin(np.pi * times(n) / dur) ** 0.7
        place(out, lowpass(highpass(throat, 80), 1200) * env * level, secs(at))
    return finish(out, 0.02, 0.05, length=1.2)


def owl(rng):
    """A tawny owl, soft and a little far: 'hooo' ... 'hu-hoooo', the last note
    quavering."""
    out = np.zeros(secs(1.5))
    for at, dur, f, quaver in ((0.0, 0.36, 395, 0.0), (0.6, 0.11, 380, 0.0), (0.73, 0.5, 410, 1.0)):
        n = secs(dur)
        t = times(n)
        f0 = glide(n, [(0, f * 0.95), (min(0.06, dur / 3), f * 1.02), (dur, f * 0.94)])
        f0 *= 1 + 0.012 * quaver * np.sin(2 * np.pi * 11 * t) * np.clip(t / dur * 2 - 0.5, 0, 1)
        formants = [(f0 * 1.0, 200, 1.0), (850, 300, 0.05)]
        x = voice(f0, formants, rng, tilt=2.0, jitter=0.003, shimmer=0.04, breath=0.12)
        env = np.sin(np.pi * t / dur) ** 0.8 * (1 - 0.3 * quaver * t / dur)
        place(out, x * env, secs(at))
    return finish(room(lowpass(out, 2500), rng, 0.35, 1.2), fade_out=0.1, length=1.5)


def heron(rng):
    """A heron far off: one low, rough 'kraak', softened by distance."""
    n = secs(0.42)
    t = times(n)
    f0 = glide(n, [(0, 190), (0.06, 215), (0.42, 160)])
    f1 = line(n, [(0, 500), (0.06, 800), (0.42, 650)])
    formants = [(f1, 300, 1.0), (1300, 400, 0.6), (2400, 500, 0.2)]
    x = voice(f0, formants, rng, tilt=0.8, jitter=0.03, shimmer=0.25, breath=0.4, sub=0.5)
    env = ramp_in(n, secs(0.012)) * np.exp(-t / 0.25) * ramp_in(n, secs(0.06))[::-1]
    out = np.concatenate([x * env, np.zeros(secs(0.4))])
    return finish(room(lowpass(out, 2800), rng, 0.35, 1.0), fade_out=0.1, length=0.8)


def hedgehog(rng):
    """A hedgehog foraging: quick wet snuffles through a small nose, then a tiny squeak."""
    out = np.zeros(secs(0.8))
    at = 0.0
    while at < 0.55:
        dur = rng.uniform(0.03, 0.06)
        n = secs(dur)
        formants = [(rng.uniform(700, 1000), 300, 1.0), (2200, 600, 0.5), (3600, 800, 0.2)]
        sniff = formant_noise(n, formants, rng) * np.sin(np.pi * times(n) / dur) ** 2
        place(out, sniff * rng.uniform(0.5, 1.0), secs(at))
        at += dur + rng.uniform(0.02, 0.07)
    n = secs(0.07)
    f0 = glide(n, [(0, 1500), (0.03, 1900), (0.07, 1600)])
    squeak = voice(f0, [(1900, 600, 1.0), (3800, 800, 0.2)], rng, tilt=1.5, breath=0.2)
    place(out, 0.35 * squeak * np.sin(np.pi * times(n) / 0.07), secs(0.66))
    return finish(room(lowpass(out, 6000), rng, 0.08), fade_out=0.04, length=0.8)


def fox(rng):
    """A fox, friendly: a soft breathy huff, then a short chirruping 'wow-ow'."""
    out = np.zeros(secs(0.6))
    n = secs(0.12)
    huff = formant_noise(n, [(700, 400, 1.0), (1500, 500, 0.5)], rng) * perc(n, 0.006, 0.04)
    place(out, 0.8 * huff, 0)
    for at, dur, pts in ((0.16, 0.13, [(0, 520), (0.05, 760), (0.13, 600)]),
                         (0.32, 0.18, [(0, 600), (0.06, 820), (0.18, 520)])):
        n = secs(dur)
        f0 = glide(n, pts)
        f1 = line(n, [(0, 600), (dur * 0.4, 1000), (dur, 700)])
        formants = [(f1, 300, 1.0), (1700, 400, 0.5), (2800, 500, 0.15)]
        x = voice(f0, formants, rng, tilt=1.0, jitter=0.01, shimmer=0.1, breath=0.25)
        place(out, x * np.sin(np.pi * times(n) / dur) ** 0.8, secs(at))
    return finish(room(lowpass(out, 5000), rng, 0.12), fade_out=0.05, length=0.6)


def frog(rng):
    """A frog's two-note croak: a pulsed, throaty 'rrib' and a slightly higher 'bit'."""
    out = np.zeros(secs(0.7))
    for at, dur, f, rate in ((0.0, 0.24, 175, 34.0), (0.34, 0.2, 200, 38.0)):
        n = secs(dur)
        t = times(n)
        f0 = glide(n, [(0, f), (dur, f * 0.9)])
        formants = [(520, 250, 1.0), (1300, 400, 0.45), (2300, 500, 0.12)]
        x = voice(f0, formants, rng, tilt=0.8, jitter=0.01, shimmer=0.1, breath=0.2)
        pulses = (0.5 + 0.5 * np.sin(2 * np.pi * rate * t)) ** 2
        place(out, x * pulses * np.sin(np.pi * t / dur) ** 0.6, secs(at))
    return finish(room(lowpass(out, 4000), rng, 0.15), fade_out=0.05, length=0.7)


def robin(rng):
    """A robin: a short liquid phrase of sliding notes that ends in a quick trill."""
    out = np.zeros(secs(1.0))
    at = 0.0
    for a, b, dur in ((2800, 3400, 0.08), (3600, 2900, 0.07), (2500, 3100, 0.09),
                      (4000, 3300, 0.06)):
        n = secs(dur)
        x = np.sin(phase_of(glide(n, [(0, a), (dur, b)]) * wobble(n, rng, 0.01, 30)))
        place(out, x * np.sin(np.pi * times(n) / dur) ** 0.7, secs(at))
        at += dur + 0.035
    for k in range(9):
        n = secs(0.035)
        f = 3200 * (1 - 0.015 * k)
        x = np.sin(phase_of(glide(n, [(0, f * 1.12), (0.035, f * 0.85)])))
        place(out, x * np.sin(np.pi * times(n) / 0.035) * (1 - 0.06 * k), secs(at + 0.05 * k))
    return finish(room(lowpass(out, 6500, 4), rng, 0.15, 0.6), fade_out=0.06, length=1.0)


def deer(rng):
    """A deer's soft snort: a quick fluttering push of air through the nostrils."""
    n = secs(0.4)
    t = times(n)
    formants = [(450, 300, 1.0), (1200, 500, 0.6), (2500, 800, 0.2)]
    air = formant_noise(n, formants, rng)
    flutter = 1 + 0.5 * np.sin(2 * np.pi * 38 * t + rng.uniform(0, 6.3))
    env = ramp_in(n, secs(0.006)) * np.exp(-t / 0.08)
    out = np.concatenate([air * flutter * env, np.zeros(secs(0.1))])
    return finish(room(lowpass(out, 4500), rng, 0.12), fade_out=0.08, length=0.5)


# --- Laeticia --------------------------------------------------------------------------

HUM = [(250, 120, 1.0), (1050, 250, 0.06), (2300, 350, 0.04), (3000, 450, 0.015)]  # closed lips


def hum(rng, dur, pts, breath=0.15, onset=0.0):
    """One wordless hummed syllable of a warm adult voice, optionally with a breathy
    'h' before the voicing begins."""
    n = secs(dur)
    x = voice(glide(n, pts), HUM, rng, tilt=1.6, jitter=0.005, shimmer=0.05, breath=breath)
    env = np.sin(np.pi * np.clip(times(n) / dur, 0, 1)) ** 0.6
    out = np.concatenate([np.zeros(secs(onset)), x * env])
    if onset:
        m = secs(onset + 0.03)
        h = formant_noise(m, [(500, 400, 1.0), (1500, 500, 0.5), (2500, 600, 0.3)], rng)
        out[:m] += 0.25 * np.std(x) / np.std(h) * h * np.sin(np.pi * times(m) / (onset + 0.03))
    return out


def laeticia_1(rng):
    """A thoughtful 'mm': a hum that dips and lifts, as if weighing something up."""
    out = hum(rng, 0.42, [(0, 205), (0.18, 190), (0.42, 212)])
    return finish(room(lowpass(out, 4000), rng, 0.06), 0.01, 0.06, length=0.45)


def laeticia_2(rng):
    """A warm 'hm-hm' of agreement: two short hums, up then gently down."""
    out = np.zeros(secs(0.45))
    place(out, hum(rng, 0.15, [(0, 215), (0.15, 245)], onset=0.03), 0)
    place(out, hum(rng, 0.2, [(0, 235), (0.2, 200)], onset=0.025), secs(0.22))
    return finish(room(lowpass(out, 4000), rng, 0.06), 0.005, 0.05, length=0.5)


def laeticia_3(rng):
    """A small amused breath: two quick nasal out-breaths with a touch of voice."""
    out = np.zeros(secs(0.4))
    for at, level in ((0.0, 1.0), (0.15, 0.7)):
        n = secs(0.13)
        t = times(n)
        air = formant_noise(n, [(500, 300, 1.0), (1300, 400, 0.5), (2600, 600, 0.25)], rng)
        env = ramp_in(n, secs(0.01)) * np.exp(-t / 0.045)
        tone = voice(glide(n, [(0, 250), (0.13, 215)]), HUM, rng, tilt=1.6) * np.exp(-t / 0.03)
        x = air / np.std(air) * env + 0.6 * tone / np.std(tone) * ramp_in(n, secs(0.01))
        place(out, x * level, secs(at))
    return finish(room(lowpass(out, 5000), rng, 0.06), 0.003, 0.05, length=0.35)
