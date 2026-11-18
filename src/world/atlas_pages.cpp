#include "world/atlas_pages.hpp"

#include "core/catalog.hpp"
#include "world/json_util.hpp"

namespace lc::world {

using namespace detail;

std::expected<void, std::string> AtlasPages::add(std::string_view text, std::string_view file,
                                                 std::string_view set, int index) {
    const std::string f(file);
    try {
        const json doc = parseDocument(text, f);
        requireVersion1(doc, f);
        if (pages_.size() >= 0xFFFF) fail(f + ": too many atlas pages");
        AtlasPage page;
        page.set = set;
        page.index = index;
        page.file = f;
        page.image = asString(field(doc, "image", f), f + ": image");
        const std::string expect = std::string(set) + "." + std::to_string(index) + ".png";
        if (page.image != expect)
            fail(f + ": image '" + page.image + "' should be '" + expect + "'");
        const auto pageIndex = static_cast<std::uint16_t>(pages_.size());
        const json& sprites = asObject(field(doc, "sprites", f), f + ": sprites");
        sprites_.reserve(sprites_.size() + sprites.size());
        for (const auto& [key, r] : sprites.items()) {
            const std::string c = f + ": sprites: " + key;
            PageSprite s;
            s.page = pageIndex;
            s.x =
                static_cast<std::uint16_t>(asInt(field(r, "x", c), c + ": x", 0, kMaxPageSide - 1));
            s.y =
                static_cast<std::uint16_t>(asInt(field(r, "y", c), c + ": y", 0, kMaxPageSide - 1));
            s.w = static_cast<std::uint16_t>(asInt(field(r, "w", c), c + ": w", 1, kMaxPageSide));
            s.h = static_cast<std::uint16_t>(asInt(field(r, "h", c), c + ": h", 1, kMaxPageSide));
            if (s.x + s.w > kMaxPageSide || s.y + s.h > kMaxPageSide)
                fail(c + ": the sprite leaves a 4096 x 4096 page");
            s.ox = static_cast<std::int16_t>(asInt(field(r, "ox", c), c + ": ox", -32768, 32767));
            s.oy = static_cast<std::int16_t>(asInt(field(r, "oy", c), c + ": oy", -32768, 32767));
            const auto [it, fresh] = sprites_.emplace(key, s);
            if (!fresh) fail(c + ": the key is also on " + pages_[it->second.page].file);
            ++page.sprites;
        }
        pages_.push_back(std::move(page));
        return {};
    } catch (const Invalid& e) {
        return std::unexpected(e.what());
    }
}

const PageSprite* AtlasPages::find(std::string_view key) const {
    const auto it = sprites_.find(key);
    return it == sprites_.end() ? nullptr : &it->second;
}

std::size_t AtlasPages::memoryBytes() const {
    std::size_t n = pages_.capacity() * sizeof(AtlasPage) + sprites_.bucket_count() * sizeof(void*);
    for (const auto& [key, s] : sprites_)
        n += sizeof(std::pair<const std::string, PageSprite>) + 2 * sizeof(void*) + key.capacity();
    return n;
}

std::expected<void, std::string> loadSetPages(AtlasPages& pages, const std::filesystem::path& dir,
                                              std::string_view set) {
    for (int n = 0;; ++n) {
        const auto file = dir / (std::string(set) + "." + std::to_string(n) + ".json");
        if (!std::filesystem::exists(file)) return {};
        const auto text = readTextFile(file);
        if (!text) return std::unexpected(text.error());
        if (auto ok = pages.add(*text, file.string(), set, n); !ok) return ok;
    }
}

} // namespace lc::world
