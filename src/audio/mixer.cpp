#include "audio/mixer.hpp"

#include "audio/decode.hpp"
#include "audio/stems.hpp"
#include "core/catalog.hpp"
#include "core/tuning.hpp"

#define STB_VORBIS_HEADER_ONLY
// stb_vorbis ships as one .c file; HEADER_ONLY exposes just its declarations.
#include <stb_vorbis.c> // NOLINT(bugprone-suspicious-include)

#include <algorithm>
#include <cmath>

namespace lc {
namespace {

float rampTowards(float v, float target, float maxStep) {
    return v < target ? std::min(target, v + maxStep) : std::max(target, v - maxStep);
}

} // namespace

Mixer::Mixer() {
    for (auto& t : loopTargets_) t.store(0.0f);
    for (auto& u : unlocked_) u.store(0);
}

void Mixer::VorbisCloser::operator()(stb_vorbis* v) const {
    stb_vorbis_close(v);
}

Mixer::~Mixer() {
    close();
}

void Mixer::load(const std::filesystem::path& dir, const AudioList& list) {
    for (const auto& name : list.sfx) {
        auto samples = loadWavMono(dir / name);
        if (!samples) {
            SDL_Log("audio: %s; it will be silent", samples.error().c_str());
            samples = std::vector<float>{};
        }
        sfxNames_.push_back(name);
        sfx_.push_back(std::move(*samples));
    }
    // Ambience beds, then the music stems (the full mixes belong to the title screen).
    std::vector<std::pair<std::string, bool>> files;
    files.reserve(list.ambience.size() + list.dayStems.size() + list.nightStems.size());
    for (const auto& f : list.ambience) files.emplace_back(f, false);
    for (const auto* piece : {&list.dayStems, &list.nightStems})
        for (const auto& s : *piece) files.emplace_back(s.file, true);
    loops_.reserve(std::min(files.size(), kMaxLoops));
    for (const auto& [file, stem] : files) {
        if (loops_.size() == kMaxLoops) {
            SDL_Log("audio: more than %zu loops; %s will be silent", kMaxLoops, file.c_str());
            continue;
        }
        LoopTrack& t = loops_.emplace_back();
        t.file = file;
        t.stem = stem;
        auto bytes = readBinaryFile(dir / file);
        if (!bytes) {
            SDL_Log("audio: %s; it will be silent", bytes.error().c_str());
            continue;
        }
        t.bytes = std::move(*bytes);
        int err = 0;
        t.vorbis.reset(stb_vorbis_open_memory(t.bytes.data(), static_cast<int>(t.bytes.size()),
                                              &err, nullptr));
        if (!t.vorbis) {
            SDL_Log("audio: %s is not readable Ogg Vorbis", file.c_str());
            continue;
        }
        const auto info = stb_vorbis_get_info(t.vorbis.get());
        if (static_cast<int>(info.sample_rate) != kMixRate || info.channels < 1 ||
            info.channels > 2) {
            SDL_Log("audio: %s must be 44.1 kHz mono or stereo; it will be silent", file.c_str());
            t.vorbis.reset();
            continue;
        }
        t.channels = info.channels;
        t.length = stb_vorbis_stream_length_in_samples(t.vorbis.get());
    }
}

int Mixer::loopIndex(std::string_view file) const {
    const auto it = std::ranges::find(loops_, file, &LoopTrack::file);
    return it == loops_.end() ? -1 : static_cast<int>(it - loops_.begin());
}

void Mixer::unlockStem(int loop, bool instant) {
    if (loop < 0 || std::cmp_greater_equal(loop, loops_.size())) return;
    int expected = 0;
    (void)unlocked_[static_cast<std::size_t>(loop)].compare_exchange_strong(expected,
                                                                            instant ? 2 : 1);
}

void Mixer::setMakeup(std::span<const int> stems, int lead, float gain) {
    for (const int s : stems) {
        if (s < 0 || std::cmp_greater_equal(s, loops_.size())) continue;
        loops_[static_cast<std::size_t>(s)].lead = lead;
        loops_[static_cast<std::size_t>(s)].makeup = gain;
    }
}

bool Mixer::open() {
    const SDL_AudioSpec spec{SDL_AUDIO_F32, 2, kMixRate};
    stream_.reset(SDL_OpenAudioDeviceStream(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec,
                                            &Mixer::callback, this));
    if (!stream_) {
        SDL_Log("audio: no playback device (%s); continuing silently", SDL_GetError());
        return false;
    }
    if (!SDL_ResumeAudioStreamDevice(stream_.get())) {
        SDL_Log("audio: cannot start playback: %s", SDL_GetError());
        stream_.reset();
        return false;
    }
    return true;
}

void Mixer::close() {
    if (!stream_) return;
    // Let the master gain ramp down so stopping never clicks.
    closing_.store(true);
    for (int i = 0; i < 20 && !silent_.load(); ++i) SDL_Delay(5);
    stream_.reset();
}

int Mixer::sfxIndex(std::string_view file) const {
    const auto it = std::ranges::find(sfxNames_, file);
    if (it == sfxNames_.end() || sfx_[static_cast<std::size_t>(it - sfxNames_.begin())].empty())
        return -1;
    return static_cast<int>(it - sfxNames_.begin());
}

void Mixer::render(float* out, int frames) {
    while (frames > 0) {
        const int n = std::min(frames, kChunk);
        mix(out, n);
        out += n * 2;
        frames -= n;
    }
}

void Mixer::play(int sfx, float gain, float pitch, float pan) {
    if (sfx < 0 || (!stream_ && !capture_)) return;
    const std::uint32_t head = head_.load(std::memory_order_relaxed);
    if (head - tail_.load(std::memory_order_acquire) >= kRing) return; // full: drop
    ring_[head % kRing] = {sfx, gain, pitch, std::clamp(pan, -1.0f, 1.0f)};
    head_.store(head + 1, std::memory_order_release);
}

void Mixer::setLoopGain(int loop, float gain) {
    if (loop < 0 || std::cmp_greater_equal(loop, loops_.size())) return;
    loopTargets_[static_cast<std::size_t>(loop)].store(gain, std::memory_order_relaxed);
}

void Mixer::setLoopPan(int loop, float pan) {
    if (loop < 0 || std::cmp_greater_equal(loop, loops_.size())) return;
    loopPans_[static_cast<std::size_t>(loop)].store(std::clamp(pan, -1.0f, 1.0f),
                                                    std::memory_order_relaxed);
}

void SDLCALL Mixer::callback(void* self, SDL_AudioStream* stream, int additional, int /*total*/) {
    auto& m = *static_cast<Mixer*>(self);
    int frames = additional / static_cast<int>(2 * sizeof(float));
    while (frames > 0) {
        const int n = std::min(frames, kChunk);
        m.mix(m.mixBuf_.data(), n);
        if (!SDL_PutAudioStreamData(stream, m.mixBuf_.data(),
                                    n * static_cast<int>(2 * sizeof(float))))
            return;
        frames -= n;
    }
}

void Mixer::decodeLoop(LoopTrack& t, float* dst, int frames) {
    int done = 0;
    int guard = 0;
    while (done < frames && guard++ < 4) {
        const int got = stb_vorbis_get_samples_float_interleaved(
            t.vorbis.get(), t.channels, decodeBuf_.data(), (frames - done) * t.channels);
        if (got == 0) {
            (void)stb_vorbis_seek_start(t.vorbis.get()); // seamless loop
            continue;
        }
        for (int i = 0; i < got; ++i) {
            const float l = decodeBuf_[static_cast<std::size_t>(i * t.channels)];
            const float r = t.channels == 2 ? decodeBuf_[static_cast<std::size_t>(i * 2 + 1)] : l;
            dst[(done + i) * 2] = l;
            dst[(done + i) * 2 + 1] = r;
        }
        done += got;
        guard = 0;
    }
    for (int i = done * 2; i < frames * 2; ++i) dst[i] = 0.0f;
}

void Mixer::mix(float* out, int frames) {
    std::fill(out, out + frames * 2, 0.0f);
    const float chunkSeconds = static_cast<float>(frames) / kMixRate;

    for (std::uint32_t tail = tail_.load(std::memory_order_relaxed);
         tail != head_.load(std::memory_order_acquire); ++tail) {
        const Command c = ring_[tail % kRing];
        const auto slot = std::ranges::find_if(voices_, [](const Voice& v) { return v.sfx < 0; });
        // Linear pan law: the centre stays at unity, the far side fades.
        if (slot != voices_.end())
            *slot = {c.sfx, 0.0, c.pitch, c.gain * std::min(1.0f, 1.0f - c.pan),
                     c.gain * std::min(1.0f, 1.0f + c.pan)};
        tail_.store(tail + 1, std::memory_order_release);
    }

    for (Voice& v : voices_) {
        if (v.sfx < 0) continue;
        const auto& s = sfx_[static_cast<std::size_t>(v.sfx)];
        const double last = static_cast<double>(s.size()) - 1.0;
        for (int i = 0; i < frames; ++i) {
            if (v.pos >= last) {
                v.sfx = -1;
                break;
            }
            const auto idx = static_cast<std::size_t>(v.pos);
            const auto frac = static_cast<float>(v.pos - static_cast<double>(idx));
            const float sample = s[idx] + (s[idx + 1] - s[idx]) * frac;
            out[i * 2] += sample * v.left;
            out[i * 2 + 1] += sample * v.right;
            v.pos += v.step;
        }
    }

    // Stem fades first: makeup gains read the lead stems' levels.
    const std::uint64_t pos0 = musicPos_;
    const std::uint64_t pos1 = pos0 + static_cast<std::uint64_t>(frames);
    const auto bar = static_cast<std::uint64_t>(tuning::kMusicBarSamples);
    std::array<float, kMaxLoops> level0{};
    for (std::size_t li = 0; li < loops_.size(); ++li) {
        LoopTrack& t = loops_[li];
        level0[li] = stemLevel_[li];
        if (!t.stem) continue;
        const int u = unlocked_[li].load(std::memory_order_relaxed);
        if (u == 2 && !t.fading) {
            stemLevel_[li] = 1.0f;
            level0[li] = 1.0f;
        } else if (u == 1 && !t.fading && stemLevel_[li] < 1.0f) {
            t.fading = true;
            t.fadeStart = nextBar(pos0, bar);
        }
        if (t.fading) {
            const std::uint64_t len = bar * static_cast<std::uint64_t>(tuning::kStemFadeBars);
            level0[li] = fadeLevel(pos0, t.fadeStart, len);
            stemLevel_[li] = fadeLevel(pos1, t.fadeStart, len);
            if (stemLevel_[li] >= 1.0f) t.fading = false;
        }
    }
    const bool hushed = master_ <= 0.0f && muted_.load();
    for (std::size_t li = 0; li < loops_.size(); ++li) {
        LoopTrack& t = loops_[li];
        if (!t.vorbis) continue;
        const float target = loopTargets_[li].load(std::memory_order_relaxed);
        const float g0 = t.gain;
        const float g1 = rampTowards(g0, target, chunkSeconds / tuning::kLoopFadeSeconds);
        t.gain = g1;
        if (g0 <= 0.0f && g1 <= 0.0f) {
            t.at = ~0ULL; // paused while inaudible; a stem finds its place again when heard
            continue;
        }
        float l0 = 1.0f;
        float l1 = 1.0f;
        if (t.stem) {
            l0 = level0[li];
            l1 = stemLevel_[li];
            // Nothing to hear: not unlocked yet, or everything is muted. Not decoded.
            if ((l0 <= 0.0f && l1 <= 0.0f) || hushed) {
                t.at = ~0ULL;
                continue;
            }
            if (t.lead >= 0) {
                const auto lead = static_cast<std::size_t>(t.lead);
                l0 *= 1.0f + (t.makeup - 1.0f) * (1.0f - level0[lead]);
                l1 *= 1.0f + (t.makeup - 1.0f) * (1.0f - stemLevel_[lead]);
            }
            // Every stem plays from the one master position, so they stay sample-aligned.
            const std::uint64_t want = loopOffset(pos0, t.length);
            if (t.at != want) {
                (void)stb_vorbis_seek(t.vorbis.get(), static_cast<unsigned>(want));
                t.at = want;
            }
            t.at = loopOffset(t.at + static_cast<std::uint64_t>(frames), t.length);
        }
        decodeLoop(t, loopBuf_.data(), frames);
        // Positional beds glide to where their source is on screen.
        const float p0 = pan_[li];
        const float p1 = rampTowards(p0, loopPans_[li].load(std::memory_order_relaxed),
                                     chunkSeconds / tuning::kLoopFadeSeconds);
        pan_[li] = p1;
        for (int i = 0; i < frames; ++i) {
            const float k = static_cast<float>(i) / static_cast<float>(frames);
            const float g = (g0 + (g1 - g0) * k) * (l0 + (l1 - l0) * k);
            const float pan = p0 + (p1 - p0) * k;
            out[i * 2] +=
                loopBuf_[static_cast<std::size_t>(i * 2)] * g * std::min(1.0f, 1.0f - pan);
            out[i * 2 + 1] +=
                loopBuf_[static_cast<std::size_t>(i * 2 + 1)] * g * std::min(1.0f, 1.0f + pan);
        }
    }
    musicPos_ = pos1;

    const float masterTarget = (muted_.load() || closing_.load()) ? 0.0f : 1.0f;
    const float m0 = master_;
    master_ = rampTowards(m0, masterTarget, chunkSeconds / tuning::kMasterFadeSeconds);
    // Peak limiter: transparent below the ceiling; above it the gain drops at once for that
    // sample and recovers smoothly, so a pile-up of effects is held down without clipping or the
    // distortion an always-on curve would add.
    const float release = 1.0f / (tuning::kLimiterReleaseSeconds * static_cast<float>(kMixRate));
    for (int i = 0; i < frames; ++i) {
        const float g = m0 + (master_ - m0) * static_cast<float>(i) / static_cast<float>(frames);
        const float l = out[i * 2] * g;
        const float r = out[i * 2 + 1] * g;
        const float peak = std::max(std::abs(l), std::abs(r));
        limit_ = std::min(1.0f, limit_ + release);
        if (peak * limit_ > tuning::kLimiterCeiling) limit_ = tuning::kLimiterCeiling / peak;
        out[i * 2] = l * limit_;
        out[i * 2 + 1] = r * limit_;
    }
    silent_.store(master_ <= 0.0f);
}

} // namespace lc
