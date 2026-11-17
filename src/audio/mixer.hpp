#pragma once
// Small software mixer on one SDL audio stream: one-shot effects with pitch, looping Ogg
// music/ambience with smooth gain ramps, a faded master mute and a peak limiter that only acts
// above its ceiling. The audio thread only reads immutable sample data, atomics and a
// single-producer/single-consumer command ring. In capture mode there is no device: the game
// pulls samples itself (for headless analysis of what the player would hear).

#include "platform/sdl_ptr.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

struct stb_vorbis;

namespace lc {

struct AudioList;

enum class Loop : std::uint8_t { DayMusic, NightMusic, Birds, Crickets, Rain, Water, Count };

// Catalog file each loop plays.
inline constexpr std::array<std::string_view, static_cast<std::size_t>(Loop::Count)> kLoopFiles{
    "music/day.ogg",    "music/night.ogg", "amb/birds.ogg",
    "amb/crickets.ogg", "amb/rain.ogg",    "amb/water.ogg"};

class Mixer {
public:
    Mixer();
    ~Mixer();
    Mixer(const Mixer&) = delete;
    Mixer& operator=(const Mixer&) = delete;

    // Loads every file the catalog lists; missing or unreadable ones become silence.
    void load(const std::filesystem::path& audioDir, const AudioList& list);
    // Opens the default playback device. Without one the game simply stays silent.
    bool open();
    // No device: render() is called by the owner instead, from one thread.
    void startCapture() { capture_ = true; }
    // Mixes `frames` stereo frames into `out` (capture mode).
    void render(float* out, int frames);
    // Fades out and closes the device.
    void close();

    [[nodiscard]] int sfxIndex(std::string_view file) const;
    void play(int sfx, float gain, float pitch);
    void setLoopGain(Loop loop, float gain);
    void setMuted(bool muted) { muted_.store(muted); }

private:
    struct Voice {
        int sfx = -1;
        double pos = 0;
        float step = 1;
        float gain = 0;
    };
    struct VorbisCloser {
        void operator()(stb_vorbis* v) const;
    };
    struct LoopTrack {
        std::vector<unsigned char> bytes;
        std::unique_ptr<stb_vorbis, VorbisCloser> vorbis;
        int channels = 0;
        float gain = 0;
    };
    struct Command {
        int sfx;
        float gain;
        float pitch;
    };
    static constexpr std::size_t kVoices = 24;
    static constexpr std::size_t kRing = 64;
    static constexpr int kChunk = 256;

    static void SDLCALL callback(void* self, SDL_AudioStream* stream, int additional, int total);
    void mix(float* out, int frames);
    void decodeLoop(LoopTrack& t, float* dst, int frames);

    std::vector<std::string> sfxNames_;
    std::vector<std::vector<float>> sfx_;
    std::array<LoopTrack, static_cast<std::size_t>(Loop::Count)> loops_{};
    std::array<std::atomic<float>, static_cast<std::size_t>(Loop::Count)> loopTargets_{};
    std::array<Command, kRing> ring_{};
    std::atomic<std::uint32_t> head_{0}; // written by the game thread
    std::atomic<std::uint32_t> tail_{0}; // written by the audio thread
    std::atomic<bool> muted_{false};
    std::atomic<bool> closing_{false};
    std::atomic<bool> silent_{true}; // master gain has reached zero while closing
    bool capture_ = false;
    // Audio-thread state.
    std::array<Voice, kVoices> voices_{};
    float master_ = 0;
    float limit_ = 1; // limiter gain, recovers slowly after a peak
    std::array<float, kChunk * 2> mixBuf_{};
    std::array<float, kChunk * 2> decodeBuf_{}; // raw decoder output
    std::array<float, kChunk * 2> loopBuf_{};   // one loop's stereo chunk
    AudioStreamPtr stream_;
};

} // namespace lc
