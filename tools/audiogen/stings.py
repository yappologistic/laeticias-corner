"""Small musical moments for weather and time: a storm clearing, first snow, a rainbow,
sunrise and nightfall, in the home music's key (D lydian, on its own music box, felt piano,
harp and glass) and in each city's mode on its own instruments (Rome: F lydian-type, cithara,
tibia, hydraulis; Athens: Dorian on E, kithara, aulos, barbitos; Pārsa: the D mode, harp,
double pipe, hummed voices). The existing music is not touched; these play over it softly."""

import numpy as np

import ancient as an
import instruments as ins
import sounds as sd
from atmos import entry
from dsp import midi_hz, place, secs

LENGTH = 2.2  # every sting rings out within this, so it never outstays its moment


def hz(m):
    return float(midi_hz(m))


def score(events, rng, length=LENGTH):
    """events: (start s, maker(rng) -> mono) pairs, mixed into one sting."""
    out = np.zeros(secs(length + 3))
    for at, make in events:
        place(out, make(rng), secs(at))
    return out


def finish(x, rng, wet=0.45, size=1.6):
    return sd.finish_sfx(x, rng, wet, size, fade_out=0.5, longest=LENGTH)


def reed(kind, notes, length=LENGTH):
    """A slurred reed line: notes are (start, dur, midi, vel)."""
    return lambda rng: an.reed_phrase(kind, [(s, d, hz(m), v, k > 0, ()) for k, (s, d, m, v)
                                             in enumerate(notes)], secs(length), rng)


def pluck(kind, m, vel, dur=2.6):
    return lambda rng: an.string(kind, hz(m), dur, vel, rng)


def arp(kind, notes, gap, vel, start=0.0):
    return [(start + gap * k, pluck(kind, m, vel)) for k, m in enumerate(notes)]


# --- home: D lydian --------------------------------------------------------------------


def home_sunrise(rng):
    """Sunrise: a warm low fifth, then the music box climbing D F# A E and glass opening."""
    ev = [(0.0, lambda r: 0.6 * ins.felt_piano(hz(50), 2.4, 0.4, r)),
          (0.02, lambda r: 0.5 * ins.felt_piano(hz(57), 2.4, 0.35, r)),
          (0.3, lambda r: 0.4 * ins.glass(hz(69), 2.4, 0.5, r))]
    ev += [(0.35 + 0.28 * k, (lambda m: lambda r: ins.tine(hz(m), 2.2, 0.55, r))(m))
           for k, m in enumerate((74, 78, 81, 88))]
    return finish(score(ev, rng), rng)


def home_nightfall(rng):
    """Nightfall: the felt piano stepping down A F# D B, a low D settling under glass."""
    ev = [(0.4 * k, (lambda m: lambda r: 0.7 * ins.felt_piano(hz(m), 1.8, 0.35, r))(m))
          for k, m in enumerate((69, 66, 62, 59))]
    ev += [(1.2, lambda r: 0.6 * ins.felt_piano(hz(38), 1.6, 0.3, r)),
           (0.6, lambda r: 0.35 * ins.glass(hz(74), 2.2, 0.4, r))]
    return finish(score(ev, rng), rng)


def home_storm_clear(rng):
    """A storm clearing: the harp running up D A E F# A, a bright tine on top, light."""
    ev = [(0.11 * k, (lambda m: lambda r: ins.harp(hz(m), 2.4, 0.6, r))(m))
          for k, m in enumerate((62, 69, 76, 78, 81))]
    ev += [(0.65, lambda r: 0.7 * ins.tine(hz(83), 2.0, 0.5, r)),
           (0.2, lambda r: 0.35 * ins.glass(hz(76), 2.4, 0.45, r))]
    return finish(score(ev, rng), rng)


def home_first_snow(rng):
    """First snow: high music-box notes falling slowly, F# E C# A, soft as flakes."""
    ev = [(0.4 * k, (lambda m: lambda r: ins.tine(hz(m), 2.0, 0.4, r))(m))
          for k, m in enumerate((90, 88, 85, 81))]
    ev += [(0.0, lambda r: 0.3 * ins.glass(hz(81), 2.6, 0.35, r)),
           (0.8, lambda r: 0.25 * ins.bell(hz(74), 2.0, 0.3, r))]
    return finish(score(ev, rng), rng)


# --- Rome: F lydian-type ---------------------------------------------------------------


def rome_sunrise(rng):
    ev = [(0.0, lambda r: 0.35 * an.hydraulis(hz(53), 1.8, 0.5, r)),
          (0.0, lambda r: 0.3 * an.hydraulis(hz(60), 1.8, 0.5, r))]
    return finish(score(ev + arp("cithara", (65, 69, 72, 77), 0.3, 0.7, 0.4), rng), rng)


def rome_nightfall(rng):
    ev = [(0.6, lambda r: 0.25 * an.hydraulis(hz(41), 1.6, 0.5, r))]
    return finish(score(ev + arp("cithara", (72, 69, 67, 65), 0.45, 0.6), rng), rng)


def rome_storm_clear(rng):
    ev = [(0.0, pluck("cithara", 53, 0.6)), (0.02, pluck("cithara", 60, 0.5)),
          (0.15, reed("tibia", ((0.0, 0.35, 67, 0.6), (0.35, 0.35, 69, 0.7), (0.7, 1.1, 72, 0.7))))]
    return finish(score(ev, rng), rng)


def rome_rainbow(rng):
    ev = arp("cithara", (65, 69, 72, 76, 79), 0.1, 0.7)
    ev.append((0.55, lambda r: 0.25 * an.cymbals(0.4, r)))
    return finish(score(ev, rng), rng)


# --- Athens: Dorian on E ---------------------------------------------------------------


def athens_sunrise(rng):
    ev = [(0.0, pluck("kithara", 40, 0.6)), (0.02, pluck("kithara", 47, 0.5)),
          (0.8, reed("aulos", ((0.0, 1.6, 64, 0.45),)))]
    return finish(score(ev + arp("kithara", (64, 69, 71, 76), 0.28, 0.65, 0.35), rng), rng)


def athens_nightfall(rng):
    return finish(score(arp("barbitos", (57, 55, 53, 52), 0.45, 0.7), rng), rng)


def athens_storm_clear(rng):
    ev = [(0.0, pluck("kithara", 40, 0.6)),
          (0.1, reed("aulos", ((0.0, 0.3, 64, 0.5), (0.3, 0.3, 65, 0.55), (0.6, 0.3, 69, 0.6),
                               (0.9, 1.0, 71, 0.6))))]
    return finish(score(ev, rng), rng)


def athens_rainbow(rng):
    ev = arp("kithara", (64, 69, 71, 76), 0.1, 0.7) + [(0.42, pluck("lyra", 83, 0.5))]
    ev.append((0.5, lambda r: 0.3 * an.clapper(0.5, r, double=True)))
    return finish(score(ev, rng), rng)


# --- Pārsa: the D mode -----------------------------------------------------------------


def parsa_sunrise(rng):
    ev = [(0.0, lambda r: 0.4 * an.hum(hz(50), 1.6, 0.5, r)),
          (0.0, lambda r: 0.3 * an.hum(hz(57), 1.6, 0.5, r)),
          (1.1, reed("pipe", ((0.0, 1.3, 69, 0.45),)))]
    return finish(score(ev + arp("harp", (62, 64, 65, 69), 0.28, 0.7, 0.3), rng), rng)


def parsa_nightfall(rng):
    ev = [(0.3, lambda r: 0.4 * an.hum(hz(50), 1.4, 0.45, r))]
    return finish(score(ev + arp("harp", (69, 65, 64, 62), 0.45, 0.6), rng), rng)


def parsa_storm_clear(rng):
    ev = [(0.0, pluck("harp", 50, 0.6)), (0.02, pluck("harp", 57, 0.5)),
          (0.15, reed("pipe", ((0.0, 0.35, 65, 0.55), (0.35, 0.35, 67, 0.6), (0.7, 1.1, 69, 0.6))))]
    return finish(score(ev, rng), rng)


def parsa_rainbow(rng):
    return finish(score(arp("harp", (62, 65, 69, 72, 74), 0.1, 0.7), rng), rng)


def parsa_first_snow(rng):
    ev = arp("harp", (81, 77, 76, 74), 0.42, 0.4) + \
        [(0.0, lambda r: 0.25 * an.hum(hz(50), 1.8, 0.4, r))]
    return finish(score(ev, rng), rng)


# --- files -----------------------------------------------------------------------------

WHAT = {"sunrise": "the sun rising (dawn begins)", "nightfall": "night falling (dusk ends)",
        "storm_clear": "a storm clearing (rain stops after a storm cell)",
        "rainbow": "a rainbow (the rainbow event)", "first_snow": "the first snow of a winter"}


def files(set_name, prefix, makers, mode):
    out = {}
    for moment, make in makers.items():
        out[f"sfx/{prefix}{moment}.wav"] = entry(
            "sfx", make, -24.0, f"A soft sting for {WHAT[moment]}, in {mode}.", gain=0.8,
            tags=["sting", moment, set_name])
    return out


HOME = files("home", "sting_", {"sunrise": home_sunrise, "nightfall": home_nightfall,
                                "storm_clear": home_storm_clear, "first_snow": home_first_snow},
             "D lydian (the corner's key)")
ROME = files("rome", "rome/sting_", {"sunrise": rome_sunrise, "nightfall": rome_nightfall,
                                     "storm_clear": rome_storm_clear, "rainbow": rome_rainbow},
             "Rome's F lydian-type mode")
ATHENS = files("athens", "athens/sting_", {"sunrise": athens_sunrise, "nightfall": athens_nightfall,
                                           "storm_clear": athens_storm_clear,
                                           "rainbow": athens_rainbow}, "Athens' Dorian on E")
PARSA = files("parsa", "parsa/sting_", {"sunrise": parsa_sunrise, "nightfall": parsa_nightfall,
                                        "storm_clear": parsa_storm_clear, "rainbow": parsa_rainbow,
                                        "first_snow": parsa_first_snow}, "Pārsa's D mode")
