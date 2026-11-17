#pragma once
// 32-bit float stereo WAV files, for capturing the mix headless and analysing it in tests.

#include <expected>
#include <filesystem>
#include <span>
#include <string>
#include <vector>

namespace lc {

// Interleaved stereo samples at kMixRate.
[[nodiscard]] std::expected<void, std::string> writeWavFloat(const std::filesystem::path& file,
                                                             std::span<const float> samples);
[[nodiscard]] std::expected<std::vector<float>, std::string>
readWavFloat(const std::filesystem::path& file);

} // namespace lc
