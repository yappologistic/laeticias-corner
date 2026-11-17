#include "audio/wav.hpp"

#include "audio/decode.hpp"

#include <cstdint>
#include <cstring>
#include <fstream>

namespace lc {
namespace {

constexpr std::uint16_t kFormatFloat = 3;
constexpr std::uint16_t kChannels = 2;
constexpr std::size_t kHeader = 44;

void put16(std::vector<char>& b, std::uint16_t v) {
    b.push_back(static_cast<char>(v & 0xFF));
    b.push_back(static_cast<char>(v >> 8));
}

void put32(std::vector<char>& b, std::uint32_t v) {
    for (int i = 0; i < 4; ++i) b.push_back(static_cast<char>((v >> (8 * i)) & 0xFF));
}

std::uint32_t get32(const std::vector<char>& b, std::size_t at) {
    std::uint32_t v = 0;
    for (std::size_t i = 0; i < 4; ++i)
        v |= static_cast<std::uint32_t>(static_cast<unsigned char>(b[at + i])) << (8 * i);
    return v;
}

} // namespace

std::expected<void, std::string> writeWavFloat(const std::filesystem::path& file,
                                               std::span<const float> samples) {
    const auto bytes = static_cast<std::uint32_t>(samples.size() * sizeof(float));
    std::vector<char> h;
    h.reserve(kHeader);
    h.insert(h.end(), {'R', 'I', 'F', 'F'});
    put32(h, 36 + bytes);
    h.insert(h.end(), {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
    put32(h, 16);
    put16(h, kFormatFloat);
    put16(h, kChannels);
    put32(h, kMixRate);
    put32(h, kMixRate * kChannels * 4);
    put16(h, kChannels * 4);
    put16(h, 32);
    h.insert(h.end(), {'d', 'a', 't', 'a'});
    put32(h, bytes);
    std::ofstream out(file, std::ios::binary | std::ios::trunc);
    out.write(h.data(), static_cast<std::streamsize>(h.size()));
    out.write(reinterpret_cast<const char*>(samples.data()), static_cast<std::streamsize>(bytes));
    if (!out) return std::unexpected("cannot write " + file.string());
    return {};
}

std::expected<std::vector<float>, std::string> readWavFloat(const std::filesystem::path& file) {
    std::ifstream in(file, std::ios::binary);
    std::vector<char> b((std::istreambuf_iterator<char>(in)), {});
    if (b.size() < kHeader || std::memcmp(b.data(), "RIFF", 4) != 0 ||
        std::memcmp(b.data() + 8, "WAVE", 4) != 0 ||
        static_cast<unsigned char>(b[20]) != kFormatFloat || b[22] != kChannels)
        return std::unexpected(file.string() + " is not a float stereo WAV");
    const std::uint32_t bytes = get32(b, 40);
    if (b.size() < kHeader + bytes) return std::unexpected(file.string() + " is truncated");
    std::vector<float> s(bytes / sizeof(float));
    std::memcpy(s.data(), b.data() + kHeader, s.size() * sizeof(float));
    return s;
}

} // namespace lc
