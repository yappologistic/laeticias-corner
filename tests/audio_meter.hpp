#pragma once
// A loudness meter for captured mixes (interleaved stereo float at 44.1 kHz): ITU-R BS.1770
// K-weighted loudness (integrated with its gates, short-term), a 4x oversampled true peak, the
// stereo balance, the balance of low, middle and high bands, and the largest jump of the
// momentary loudness between neighbouring 100 ms steps. For tests only.

#include <algorithm>
#include <cmath>
#include <numbers>
#include <span>
#include <vector>

namespace lc::meter {

struct Biquad {
    double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
    double x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    double run(double x) {
        const double y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
        x2 = x1;
        x1 = x;
        y2 = y1;
        y1 = y;
        return y;
    }
};

// The cookbook's shelf and pass filters, normalised.
inline Biquad shelf(double fs, double f0, double gainDb, double q) {
    const double a = std::pow(10.0, gainDb / 40.0);
    const double w = 2.0 * std::numbers::pi * f0 / fs;
    const double alpha = std::sin(w) / (2.0 * q);
    const double c = std::cos(w);
    const double s = 2.0 * std::sqrt(a) * alpha;
    const double a0 = (a + 1) - (a - 1) * c + s;
    return {a * ((a + 1) + (a - 1) * c + s) / a0, -2 * a * ((a - 1) + (a + 1) * c) / a0,
            a * ((a + 1) + (a - 1) * c - s) / a0, 2 * ((a - 1) - (a + 1) * c) / a0,
            ((a + 1) - (a - 1) * c - s) / a0};
}
inline Biquad pass(double fs, double f0, double q, bool high) {
    const double w = 2.0 * std::numbers::pi * f0 / fs;
    const double alpha = std::sin(w) / (2.0 * q);
    const double c = std::cos(w);
    const double a0 = 1 + alpha;
    const double k = high ? (1 + c) / 2 : (1 - c) / 2;
    return {k / a0, (high ? -2 * k : 2 * k) / a0, k / a0, -2 * c / a0, (1 - alpha) / a0};
}

struct Reading {
    double integrated = -100; // LUFS
    double shortMax = -100;   // LUFS, 3 s windows
    double truePeak = -100;   // dBTP
    double balance = 0;       // dB, left over right
    double low = 0;           // dB, the band's energy against the whole: < 250 Hz
    double high = 0;          // > 4 kHz
    double jump = 0;          // LU, largest step of the momentary loudness (400 ms, 100 ms hop)
};

inline double lufs(double meanSquare) {
    return -0.691 + 10.0 * std::log10(meanSquare + 1e-20);
}

inline Reading measure(std::span<const float> s, double fs = 44100.0) {
    Reading r;
    const std::size_t frames = s.size() / 2;
    if (frames < static_cast<std::size_t>(fs * 0.4)) return r;
    // K-weighting per channel; bands on the mono sum.
    std::vector<double> k(frames, 0.0); // sum over channels of the K-weighted square
    double el = 0, er = 0, total = 0, low = 0, high = 0;
    Biquad lp = pass(fs, 250.0, 0.7071, false);
    Biquad hp = pass(fs, 4000.0, 0.7071, true);
    for (int ch = 0; ch < 2; ++ch) {
        Biquad pre = shelf(fs, 1681.974450955533, 3.999843853973347, 0.7071752369554196);
        Biquad rlb = pass(fs, 38.13547087602444, 0.5003270373238773, true);
        for (std::size_t i = 0; i < frames; ++i) {
            const double x = s[i * 2 + static_cast<std::size_t>(ch)];
            const double y = rlb.run(pre.run(x));
            k[i] += y * y;
            (ch == 0 ? el : er) += x * x;
        }
    }
    for (std::size_t i = 0; i < frames; ++i) {
        const double m = 0.5 * (s[i * 2] + s[i * 2 + 1]);
        const double l = lp.run(m);
        const double h = hp.run(m);
        total += m * m;
        low += l * l;
        high += h * h;
    }
    r.balance = 10.0 * std::log10((el + 1e-20) / (er + 1e-20));
    r.low = 10.0 * std::log10((low + 1e-20) / (total + 1e-20));
    r.high = 10.0 * std::log10((high + 1e-20) / (total + 1e-20));
    // Momentary blocks of 400 ms every 100 ms; prefix sums for the windows.
    std::vector<double> sum(frames + 1, 0.0);
    for (std::size_t i = 0; i < frames; ++i) sum[i + 1] = sum[i] + k[i];
    const auto window = [&](std::size_t from, std::size_t len) {
        return (sum[from + len] - sum[from]) / static_cast<double>(len);
    };
    const auto block = static_cast<std::size_t>(fs * 0.4);
    const auto hop = static_cast<std::size_t>(fs * 0.1);
    std::vector<double> blocks;
    for (std::size_t at = 0; at + block <= frames; at += hop) blocks.push_back(window(at, block));
    for (std::size_t i = 1; i < blocks.size(); ++i)
        r.jump = std::max(r.jump, std::abs(lufs(blocks[i]) - lufs(blocks[i - 1])));
    // Integrated: the absolute gate at -70 LUFS, then the relative one 10 LU under the mean.
    double gated = 0;
    int n = 0;
    for (const double b : blocks)
        if (lufs(b) > -70.0) {
            gated += b;
            ++n;
        }
    if (n > 0) {
        const double rel = lufs(gated / n) - 10.0;
        double g2 = 0;
        int n2 = 0;
        for (const double b : blocks)
            if (lufs(b) > -70.0 && lufs(b) > rel) {
                g2 += b;
                ++n2;
            }
        if (n2 > 0) r.integrated = lufs(g2 / n2);
    }
    const auto st = static_cast<std::size_t>(fs * 3.0);
    for (std::size_t at = 0; at + st <= frames; at += hop)
        r.shortMax = std::max(r.shortMax, lufs(window(at, st)));
    if (frames < st) r.shortMax = lufs(window(0, frames));
    // True peak: 4x oversampling with a windowed sinc (12 taps a phase).
    constexpr int kTaps = 12;
    double peak = 0;
    for (int ch = 0; ch < 2; ++ch)
        for (std::size_t i = kTaps; i + kTaps < frames; ++i)
            for (int phase = 0; phase < 4; ++phase) {
                double v = 0;
                for (int t = -kTaps / 2 + 1; t <= kTaps / 2; ++t) {
                    const double x = static_cast<double>(t) - phase / 4.0;
                    const double sinc =
                        x == 0 ? 1.0 : std::sin(std::numbers::pi * x) / (std::numbers::pi * x);
                    const double win =
                        0.5 + 0.5 * std::cos(std::numbers::pi * x / (kTaps / 2.0 + 1.0));
                    v += s[(i + static_cast<std::size_t>(t + kTaps)) * 2 - kTaps * 2 +
                           static_cast<std::size_t>(ch)] *
                         sinc * win;
                }
                peak = std::max(peak, std::abs(v));
            }
    r.truePeak = 20.0 * std::log10(peak + 1e-12);
    return r;
}

} // namespace lc::meter
