#pragma once
// Atlas page manifests of the sets (`assets/atlas/<set>.<n>.json`, docs/design/world-tech.md
// §1.2): JSON only, no pixels. Every key of every page goes into one key space so the renderer can
// resolve a sprite to its page before the page is loaded.

#include <cstdint>
#include <expected>
#include <filesystem>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace lc::world {

struct PageSprite {
    std::uint16_t page = 0; // index into AtlasPages::pages
    std::uint16_t x = 0;
    std::uint16_t y = 0;
    std::uint16_t w = 0;
    std::uint16_t h = 0;
    std::int16_t ox = 0;
    std::int16_t oy = 0;
};

struct AtlasPage {
    std::string set;
    int index = 0;     // n of <set>.<n>
    std::string image; // file name beside the manifest
    std::string file;  // the manifest, for messages
    int sprites = 0;
};

// Pages are limited to 4096 x 4096 (world-tech §1.2).
inline constexpr int kMaxPageSide = 4096;

class AtlasPages {
public:
    // Parses one manifest into the key space. A key already on another page is an error naming
    // both pages.
    [[nodiscard]] std::expected<void, std::string> add(std::string_view text, std::string_view file,
                                                       std::string_view set, int index);
    [[nodiscard]] const PageSprite* find(std::string_view key) const;
    [[nodiscard]] const std::vector<AtlasPage>& pages() const { return pages_; }
    [[nodiscard]] std::size_t size() const { return sprites_.size(); }
    [[nodiscard]] std::size_t memoryBytes() const;

private:
    struct Hash {
        using is_transparent = void;
        std::size_t operator()(std::string_view s) const {
            return std::hash<std::string_view>{}(s);
        }
    };
    std::vector<AtlasPage> pages_;
    std::unordered_map<std::string, PageSprite, Hash, std::equal_to<>> sprites_;
};

// Loads `<dir>/<set>.0.json`, `<set>.1.json`, ... until the next index is missing.
[[nodiscard]] std::expected<void, std::string>
loadSetPages(AtlasPages& pages, const std::filesystem::path& dir, std::string_view set);

} // namespace lc::world
