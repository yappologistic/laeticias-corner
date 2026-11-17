#include "audio/mixer.hpp"

#include "audio/decode.hpp"
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
}

Mixer::~Mixer() {
    close();
    for (auto& t : loops_)
        if (t.vorbis != nullptr) stb_vorbis_close(t.vorbis);
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
    for (std::size_t i = 0; i < loops_.size(); ++i) {
        const auto listed = [&](const std::vector<std::string>& v) {
            return std::ranges::find(v, kLoopFiles[i]) != v.end();
        };
        if (!listed(list.music) && !listed(list.ambience)) continue;
        LoopTrack& t = loops_[i];
        auto bytes = readBinaryFile(dir / kLoopFiles[i]);
        if (!bytes) {
            SDL_Log("audio: %s; it will be silent", bytes.error().c_str());
            continue;
        }
        t.bytes = std::move(*bytes);
        int err = 0;
        t.vorbis =
            stb_vorbis_open_memory(t.bytes.data(), static_cast<int>(t.bytes.size()), &err, nullptr);
        if (t.vorbis == nullptr) {
            SDL_Log("audio: %.*s is not readable Ogg Vorbis",
                    static_cast<int>(kLoopFiles[i].size()), kLoopFiles[i].data());
            continue;
        }
        const auto info = stb_vorbis_get_info(t.vorbis);
        if (static_cast<int>(info.sample_rate) != kMixRate || info.channels < 1 ||
            info.channels > 2) {
            SDL_Log("audio: %.*s must be 44.1 kHz mono or stereo; it will be silent",
                    static_cast<int>(kLoopFiles[i].size()), kLoopFiles[i].data());
            stb_vorbis_close(t.vorbis);
            t.vorbis = nullptr;
            continue;
        }
        t.channels = info.channels;
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

void Mixer::play(int sfx, float gain, float pitch) {
    if (sfx < 0 || !stream_) return;
    const std::uint32_t head = head_.load(std::memory_order_relaxed);
    if (head - tail_.load(std::memory_order_acquire) >= kRing) return; // full: drop
    ring_[head % kRing] = {sfx, gain, pitch};
    head_.store(head + 1, std::memory_order_release);
}

void Mixer::setLoopGain(Loop loop, float gain) {
    loopTargets_[static_cast<std::size_t>(loop)].store(gain, std::memory_order_relaxed);
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
            t.vorbis, t.channels, decodeBuf_.data(), (frames - done) * t.channels);
        if (got == 0) {
            (void)stb_vorbis_seek_start(t.vorbis); // seamless loop
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
        if (slot != voices_.end()) *slot = {c.sfx, 0.0, c.pitch, c.gain};
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
            const float sample = (s[idx] + (s[idx + 1] - s[idx]) * frac) * v.gain;
            out[i * 2] += sample;
            out[i * 2 + 1] += sample;
            v.pos += v.step;
        }
    }

    for (std::size_t li = 0; li < loops_.size(); ++li) {
        LoopTrack& t = loops_[li];
        if (t.vorbis == nullptr) continue;
        const float target = loopTargets_[li].load(std::memory_order_relaxed);
        if (t.gain <= 0.0f && target <= 0.0f) continue; // paused while inaudible
        const float g0 = t.gain;
        const float g1 = rampTowards(g0, target, chunkSeconds / tuning::kLoopFadeSeconds);
        t.gain = g1;
        decodeLoop(t, loopBuf_.data(), frames);
        for (int i = 0; i < frames; ++i) {
            const float g = g0 + (g1 - g0) * static_cast<float>(i) / static_cast<float>(frames);
            out[i * 2] += loopBuf_[static_cast<std::size_t>(i * 2)] * g;
            out[i * 2 + 1] += loopBuf_[static_cast<std::size_t>(i * 2 + 1)] * g;
        }
    }

    const float masterTarget = (muted_.load() || closing_.load()) ? 0.0f : 1.0f;
    const float m0 = master_;
    master_ = rampTowards(m0, masterTarget, chunkSeconds / tuning::kMasterFadeSeconds);
    for (int i = 0; i < frames; ++i) {
        const float g = m0 + (master_ - m0) * static_cast<float>(i) / static_cast<float>(frames);
        for (int c = 0; c < 2; ++c) {
            // Gentle soft clip so overlapping effects never wrap or crackle.
            const float x = out[i * 2 + c] * g;
            out[i * 2 + c] = x / (1.0f + std::abs(x) * 0.25f);
        }
    }
    silent_.store(master_ <= 0.0f);
}

} // namespace lc
