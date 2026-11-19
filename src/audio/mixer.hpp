#pragma once
// Small software mixer on one SDL audio stream: one-shot effects with pitch, looping Ogg
// ambience with smooth gain ramps, music stems that play in step from one master sample position
// and fade in on a bar line when unlocked, a faded master mute and a peak limiter that only acts
// above its ceiling, and snow's muffle: the ambience beds (all but those marked dry) pass a
// low-pass the game fades in and out. The audio thread only reads immutable sample data, atomics
// and a single-producer/single-consumer command ring. In capture mode there is no device: the game
// pulls samples itself (for headless analysis of what the player would hear).

#include "platform/sdl_ptr.hpp"

#include <array>
#include <atomic>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

struct stb_vorbis;

namespace lc {

struct AudioList;

class Mixer {
public:
    Mixer();
    ~Mixer();
    Mixer(const Mixer&) = delete;
    Mixer& operator=(const Mixer&) = delete;

    // Loads every effect, ambience bed and music stem the catalog lists; missing or unreadable
    // ones become silence.
    void load(const std::filesystem::path& audioDir, const AudioList& list);
    // More effects and loops (the world's regions), before open(); files already loaded are
    // skipped.
    void loadMore(const std::filesystem::path& audioDir, std::span<const std::string> sfx,
                  std::span<const std::string> loops);
    // A loop that is not a stem starts from `sample` the next time it is mixed (a phrase start).
    void seekLoop(int loop, std::uint64_t sample);
    // Opens the default playback device. Without one the game simply stays silent.
    bool open();
    // No device: render() is called by the owner instead, from one thread.
    void startCapture() { capture_ = true; }
    // Mixes `frames` stereo frames into `out` (capture mode).
    void render(float* out, int frames);
    // Fades out and closes the device.
    void close();

    [[nodiscard]] int sfxIndex(std::string_view file) const;
    // `pan` places the sound from -1 (left) to 1 (right); 0 is centred.
    void play(int sfx, float gain, float pitch, float pan = 0);
    // Loops are ambience beds and music stems, by file; -1 when the file is not loaded.
    [[nodiscard]] int loopIndex(std::string_view file) const;
    void setLoopGain(int loop, float gain);
    // The gain a loop was last asked for (0 for no such loop): what the game wants heard.
    [[nodiscard]] float loopTarget(int loop) const {
        return loop >= 0 && static_cast<std::size_t>(loop) < kMaxLoops
                   ? loopTargets_[static_cast<std::size_t>(loop)].load(std::memory_order_relaxed)
                   : 0.0f;
    }
    [[nodiscard]] static constexpr std::size_t maxLoops() { return kMaxLoops; }
    void setLoopPan(int loop, float pan);
    // Snow's muffle on the ambience beds, 0 (open) .. 1 (the full low-pass), glided to; a `dry`
    // loop (the snow beds, already muffled) never passes it.
    void setMuffle(float amount) { muffleTarget_.store(amount, std::memory_order_relaxed); }
    void setLoopDry(int loop, bool dry);
    // A loop that is music though not a stem (a city's piece, the title's full mix): on the music
    // bus, never muffled. Set before open().
    void setLoopMusic(int loop);
    // A music stem joins: at once (`instant`, e.g. when a world opens), or from silence over a
    // few bars starting on the next bar line. Stems not unlocked stay silent and undecoded.
    void unlockStem(int loop, bool instant);
    // Extra gain on a piece's stems while its stem `lead` is not yet in (a quieter opening needs
    // lifting); it fades away as the lead fades in. `stems` are the piece's loops.
    void setMakeup(std::span<const int> stems, int lead, float gain);
    void setMuted(bool muted) { muted_.store(muted); }
    // The player's volumes (0..1) for music (stems), effects (one-shots) and ambience (the other
    // loops), glided to so a slider never clicks.
    enum class Bus : std::uint8_t { Music, Effects, Ambience };
    void setBus(Bus bus, float gain) {
        busTargets_[static_cast<std::size_t>(bus)].store(gain, std::memory_order_relaxed);
    }
    // Every stem goes quiet and locked again (another world opens with its own progress).
    void resetStems();
    // Share of the audio callback's time budget spent mixing (smoothed, 0..1; 0 without a device).
    [[nodiscard]] float load() const { return load_.load(std::memory_order_relaxed); }
    // Fade-in level (0..1) a stem has reached; read only in capture mode, where the game thread
    // is the one mixing.
    [[nodiscard]] float stemLevel(int loop) const {
        return loop >= 0 && static_cast<std::size_t>(loop) < loops_.size()
                   ? stemLevel_[static_cast<std::size_t>(loop)]
                   : 0.0f;
    }
    // Capture mode: the energy (sum of squares, both channels, before the master and the
    // limiter) each bus has put out since the last call, then zeroed: music, effects, ambience.
    [[nodiscard]] std::array<double, 3> takeBusEnergy() { return std::exchange(busEnergy_, {}); }
    // Master sample position of the music (for tests of the arithmetic's wiring).
    [[nodiscard]] std::uint64_t musicPosition() const { return musicPos_; }

private:
    struct Voice {
        int sfx = -1;
        double pos = 0;
        float step = 1;
        float left = 0; // gain per channel
        float right = 0;
    };
    struct VorbisCloser {
        void operator()(stb_vorbis* v) const;
    };
    struct LoopTrack {
        std::string file;
        std::vector<unsigned char> bytes;
        std::unique_ptr<stb_vorbis, VorbisCloser> vorbis;
        int channels = 0;
        float gain = 0;
        bool stem = false;           // plays in step with the music's master position
        bool music = false;          // on the music bus (stems, and pieces that loop freely)
        std::uint64_t length = 0;    // samples, for stems
        std::uint64_t at = ~0ULL;    // decoder position the stem is at, ~0: not playing
        std::uint64_t fadeStart = 0; // stem: when its fade-in began (master samples)
        bool fading = false;
        int lead = -1;    // stem: the loop whose arrival removes the makeup gain
        float makeup = 1; // stem: gain while `lead` is not in
    };
    struct Command {
        int sfx;
        float gain;
        float pitch;
        float pan;
    };
    static constexpr std::size_t kVoices = 24;
    static constexpr std::size_t kRing = 64;
    static constexpr int kChunk = 256;

    static void SDLCALL callback(void* self, SDL_AudioStream* stream, int additional, int total);
    void mix(float* out, int frames);
    void decodeLoop(LoopTrack& t, float* dst, int frames);
    void muffleBeds(float* out, int frames, float chunkSeconds);
    void addLoop(const std::filesystem::path& dir, const std::string& file, bool stem);

    std::vector<std::string> sfxNames_;
    std::vector<std::vector<float>> sfx_;
    static constexpr std::size_t kMaxLoops = 256;
    std::vector<LoopTrack> loops_; // fixed once loaded
    std::array<std::atomic<float>, kMaxLoops> loopTargets_{};
    std::array<std::atomic<float>, kMaxLoops> loopPans_{};
    std::array<std::atomic<std::int64_t>, kMaxLoops> seekTo_{}; // -1: none (set in the ctor)
    std::array<float, kMaxLoops> pan_{}; // audio thread: each loop's pan, gliding to its target
    std::array<std::atomic<int>, kMaxLoops> unlocked_{}; // 0 locked, 1 fade in, 2 instant
    std::array<std::atomic<bool>, kMaxLoops> dry_{};     // past the muffle
    std::atomic<float> muffleTarget_{0};
    std::array<Command, kRing> ring_{};
    std::atomic<std::uint32_t> head_{0}; // written by the game thread
    std::atomic<std::uint32_t> tail_{0}; // written by the audio thread
    std::atomic<bool> muted_{false};
    std::atomic<float> load_{0};
    std::array<std::atomic<float>, 3> busTargets_{};
    std::array<float, 3> bus_{1, 1, 1}; // audio thread: each bus's gain, gliding to its target
    std::atomic<bool> resetStems_{false};
    std::atomic<bool> closing_{false};
    std::atomic<bool> silent_{true}; // master gain has reached zero while closing
    bool capture_ = false;
    // Audio-thread state.
    std::array<Voice, kVoices> voices_{};
    float master_ = 0;
    float limit_ = 1;                          // limiter gain, recovers slowly after a peak
    std::uint64_t musicPos_ = 0;               // master sample position of the music
    std::array<float, kMaxLoops> stemLevel_{}; // fade-in level of each stem
    std::array<float, kChunk * 2> mixBuf_{};
    std::array<float, kChunk * 2> decodeBuf_{};     // raw decoder output
    std::array<float, kChunk * 2> loopBuf_{};       // one loop's stereo chunk
    std::array<float, kChunk * 2> bedBuf_{};        // the beds that pass the muffle, summed
    std::array<float, kChunk * 2> dryBuf_{};        // the beds that do not
    std::array<float, kChunk * 2> musicBuf_{};      // the stems
    std::array<double, 3> busEnergy_{};             // capture mode: music, effects, ambience
    float muffle_ = 0;                              // audio thread: the muffle's mix, gliding
    std::array<std::array<float, 4>, 2> lowpass_{}; // per channel: x1, x2, y1, y2
    AudioStreamPtr stream_;
};

} // namespace lc
