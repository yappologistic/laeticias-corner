#include "audio/decode.hpp"

#include "platform/sdl_ptr.hpp"

#define STB_VORBIS_HEADER_ONLY
// stb_vorbis ships as one .c file; HEADER_ONLY exposes just its declarations.
#include <stb_vorbis.c> // NOLINT(bugprone-suspicious-include)

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iterator>
#include <memory>

namespace lc {
namespace {

struct Wav {
    SDL_AudioSpec spec{};
    SdlBuffer data;
    Uint32 len = 0;
};

std::expected<Wav, std::string> readWav(const std::filesystem::path& file) {
    Wav w;
    Uint8* buf = nullptr;
    if (!SDL_LoadWAV(file.string().c_str(), &w.spec, &buf, &w.len))
        return std::unexpected(file.string() + ": " + SDL_GetError());
    w.data.reset(buf);
    return w;
}

} // namespace

std::expected<std::vector<unsigned char>, std::string>
readBinaryFile(const std::filesystem::path& file) {
    std::ifstream in(file, std::ios::binary);
    if (!in) return std::unexpected("cannot open " + file.string());
    std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)), {});
    if (bytes.empty()) return std::unexpected(file.string() + " is empty");
    return bytes;
}

std::expected<std::vector<float>, std::string> loadWavMono(const std::filesystem::path& file) {
    auto wav = readWav(file);
    if (!wav) return std::unexpected(wav.error());
    const SDL_AudioSpec dst{SDL_AUDIO_F32, 1, kMixRate};
    Uint8* out = nullptr;
    int outLen = 0;
    if (!SDL_ConvertAudioSamples(&wav->spec, static_cast<const Uint8*>(wav->data.get()),
                                 static_cast<int>(wav->len), &dst, &out, &outLen)) {
        return std::unexpected(file.string() + ": " + SDL_GetError());
    }
    const SdlBuffer owned(out);
    std::vector<float> samples(static_cast<std::size_t>(outLen) / sizeof(float));
    std::memcpy(samples.data(), out, samples.size() * sizeof(float));
    return samples;
}

std::expected<WavInfo, std::string> probeWav(const std::filesystem::path& file) {
    auto wav = readWav(file);
    if (!wav) return std::unexpected(wav.error());
    WavInfo info{wav->spec.freq, wav->spec.channels,
                 static_cast<int>(SDL_AUDIO_BITSIZE(wav->spec.format)), 0};
    auto mono = loadWavMono(file);
    if (!mono) return std::unexpected(mono.error());
    for (float s : *mono) info.peak = std::max(info.peak, std::abs(s));
    return info;
}

std::expected<OggInfo, std::string> probeOgg(const std::vector<unsigned char>& bytes) {
    int err = 0;
    const std::unique_ptr<stb_vorbis, decltype(&stb_vorbis_close)> v(
        stb_vorbis_open_memory(bytes.data(), static_cast<int>(bytes.size()), &err, nullptr),
        &stb_vorbis_close);
    if (!v)
        return std::unexpected("not a readable Ogg Vorbis stream (error " + std::to_string(err) +
                               ")");
    const stb_vorbis_info i = stb_vorbis_get_info(v.get());
    return OggInfo{static_cast<int>(i.sample_rate), i.channels,
                   stb_vorbis_stream_length_in_seconds(v.get())};
}

} // namespace lc
