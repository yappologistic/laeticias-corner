#include "world/layer_file.hpp"

#include <algorithm>
#include <array>

namespace lc::world {
namespace {

constexpr std::array<std::uint8_t, 4> kMagic{'L', 'C', 'W', 'L'};
constexpr int kVersion = 1;
constexpr std::size_t kHeader = 24;
constexpr std::size_t kItemBytes = 8;

class Reader {
public:
    Reader(std::span<const std::uint8_t> d, std::string_view file) : d_(d), file_(file) {}

    [[nodiscard]] std::size_t pos() const { return pos_; }
    [[nodiscard]] std::size_t left() const { return d_.size() - pos_; }
    [[nodiscard]] bool need(std::size_t n) const { return left() >= n; }
    std::uint8_t u8() { return d_[pos_++]; }
    std::uint16_t u16() {
        const auto v = static_cast<std::uint16_t>(d_[pos_] | (d_[pos_ + 1] << 8));
        pos_ += 2;
        return v;
    }
    std::int16_t i16() { return static_cast<std::int16_t>(u16()); }
    std::uint32_t u32() {
        const std::uint32_t v = d_[pos_] | (std::uint32_t{d_[pos_ + 1]} << 8) |
                                (std::uint32_t{d_[pos_ + 2]} << 16) |
                                (std::uint32_t{d_[pos_ + 3]} << 24);
        pos_ += 4;
        return v;
    }
    std::string str(std::size_t n) {
        std::string s(reinterpret_cast<const char*>(d_.data() + pos_), n);
        pos_ += n;
        return s;
    }
    [[nodiscard]] std::string err(const std::string& msg) const {
        return std::string(file_) + ": " + msg;
    }

private:
    std::span<const std::uint8_t> d_;
    std::string_view file_;
    std::size_t pos_ = 0;
};

std::string tile(const LayerFile& lf, std::size_t cell) {
    const auto w = static_cast<std::size_t>(lf.w);
    return "grid (" + std::to_string(lf.x0 + static_cast<int>(cell % w)) + ", " +
           std::to_string(lf.y0 + static_cast<int>(cell / w)) + ")";
}

} // namespace

std::expected<LayerFile, std::string> parseLayer(std::span<const std::uint8_t> data, int gridW,
                                                 int gridH, std::string_view file) {
    Reader r(data, file);
    if (!r.need(kHeader)) return std::unexpected(r.err("shorter than the 24-byte header"));
    for (const std::uint8_t m : kMagic)
        if (r.u8() != m) return std::unexpected(r.err("bad magic (not an LCWL layer)"));
    const int version = r.u16();
    if (version != kVersion)
        return std::unexpected(r.err("version " + std::to_string(version) + " is not supported"));
    if (r.u16() != 0) return std::unexpected(r.err("reserved header field is not 0"));
    LayerFile lf;
    lf.x0 = r.i16();
    lf.y0 = r.i16();
    lf.w = r.u16();
    lf.h = r.u16();
    if (lf.w == 0 || lf.h == 0) return std::unexpected(r.err("empty layer rect"));
    if (lf.x0 < 0 || lf.y0 < 0 || lf.x0 + lf.w > gridW || lf.y0 + lf.h > gridH)
        return std::unexpected(
            r.err("layer rect (" + std::to_string(lf.x0) + ", " + std::to_string(lf.y0) +
                  ") size " + std::to_string(lf.w) + " x " + std::to_string(lf.h) + " leaves the " +
                  std::to_string(gridW) + " x " + std::to_string(gridH) + " grid"));
    const int nTerrain = r.u16();
    const int nDistrict = r.u16();
    const int nItem = r.u16();
    if (r.u16() != 0) return std::unexpected(r.err("reserved table count is not 0"));
    if (nTerrain > kCellTransparent)
        return std::unexpected(r.err(std::to_string(nTerrain) + " terrain ids; at most 254"));
    if (nDistrict > 0xFF + 1)
        return std::unexpected(r.err(std::to_string(nDistrict) + " districts; at most 256"));
    for (int i = 0; i < nTerrain + nDistrict + nItem; ++i) {
        if (!r.need(1)) return std::unexpected(r.err("string table truncated"));
        const std::size_t n = r.u8();
        if (!r.need(n)) return std::unexpected(r.err("string table truncated"));
        std::string s = r.str(n);
        if (s.empty()) return std::unexpected(r.err("empty string in the string table"));
        if (i < nTerrain)
            lf.terrains.push_back(std::move(s));
        else if (i < nTerrain + nDistrict)
            lf.districts.push_back(std::move(s));
        else
            lf.itemIds.push_back(std::move(s));
    }
    const std::size_t cells = static_cast<std::size_t>(lf.w) * static_cast<std::size_t>(lf.h);
    constexpr std::array<const char*, 3> kPlane{"T", "L", "D"};
    std::array<std::vector<std::uint8_t>*, 3> planes{&lf.terrain, &lf.level, &lf.district};
    for (std::size_t p = 0; p < 3; ++p) {
        std::vector<std::uint8_t>& out = *planes[p];
        out.resize(cells);
        std::size_t filled = 0;
        while (filled < cells) {
            if (!r.need(2))
                return std::unexpected(r.err(std::string("plane ") + kPlane[p] + " truncated"));
            const std::uint8_t v = r.u8();
            const std::size_t run = std::size_t{r.u8()} + 1;
            if (filled + run > cells)
                return std::unexpected(r.err(std::string("plane ") + kPlane[p] +
                                             ": a run passes the end of the plane"));
            std::fill_n(out.begin() + static_cast<std::ptrdiff_t>(filled), run, v);
            filled += run;
        }
    }
    for (std::size_t c = 0; c < cells; ++c) {
        const std::uint8_t t = lf.terrain[c];
        if (t == kCellTransparent) continue;
        if (t != kCellNoGround && t >= nTerrain)
            return std::unexpected(r.err("plane T: value " + std::to_string(t) + " at " +
                                         tile(lf, c) + " is not one of the " +
                                         std::to_string(nTerrain) + " terrain ids"));
        if (lf.level[c] & kLevelReserved)
            return std::unexpected(r.err("plane L: reserved bit 7 set at " + tile(lf, c)));
        if (t != kCellNoGround && lf.district[c] >= nDistrict)
            return std::unexpected(r.err("plane D: value " + std::to_string(lf.district[c]) +
                                         " at " + tile(lf, c) + " is not one of the " +
                                         std::to_string(nDistrict) + " districts"));
    }
    if (!r.need(4)) return std::unexpected(r.err("item count missing"));
    const std::uint32_t count = r.u32();
    if (r.left() != std::size_t{count} * kItemBytes)
        return std::unexpected(r.err("item block holds " + std::to_string(r.left()) + " bytes, " +
                                     std::to_string(count) + " items need " +
                                     std::to_string(std::size_t{count} * kItemBytes) +
                                     " (truncated, or trailing bytes)"));
    lf.items.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
        LayerItem it;
        it.id = r.u16();
        it.x = r.u16();
        it.y = r.u16();
        it.variant = r.u8();
        it.flags = r.u8();
        const std::string where = "item " + std::to_string(i);
        if (it.id >= nItem)
            return std::unexpected(r.err(where + ": id index " + std::to_string(it.id) +
                                         " is not one of the " + std::to_string(nItem) +
                                         " item ids"));
        if (it.x >= lf.w || it.y >= lf.h)
            return std::unexpected(r.err(where + " (" + lf.itemIds[it.id] + "): origin (" +
                                         std::to_string(it.x) + ", " + std::to_string(it.y) +
                                         ") is outside the layer rect"));
        if (it.flags != 0)
            return std::unexpected(
                r.err(where + " (" + lf.itemIds[it.id] + "): reserved flags are not 0"));
        lf.items.push_back(it);
    }
    return lf;
}

} // namespace lc::world
