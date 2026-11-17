#pragma once
// Loading audio files into the mixer's formats, plus format checks for the coverage test.

#include <expected>
#include <filesystem>
#include <string>
#include <vector>

namespace lc {

inline constexpr int kMixRate = 44100;

// Any WAV SDL can read, converted to 44.1 kHz mono float.
[[nodiscard]] std::expected<std::vector<float>, std::string>
loadWavMono(const std::filesystem::path& file);

struct WavInfo {
    int rate = 0;
    int channels = 0;
    int bits = 0;
    float peak = 0; // linear, 0..1
};
[[nodiscard]] std::expected<WavInfo, std::string> probeWav(const std::filesystem::path& file);

struct OggInfo {
    int rate = 0;
    int channels = 0;
    double seconds = 0;
};
[[nodiscard]] std::expected<OggInfo, std::string> probeOgg(const std::vector<unsigned char>& bytes);

[[nodiscard]] std::expected<std::vector<unsigned char>, std::string>
readBinaryFile(const std::filesystem::path& file);

} // namespace lc
