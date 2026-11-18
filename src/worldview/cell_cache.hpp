#pragma once
// Slots for cells (worldview/cells.hpp) in shared page textures under a memory budget, reused
// least-recently-used. What goes into a slot is the renderer's business.

#include "core/iso.hpp"
#include "platform/sdl_ptr.hpp"

#include <cstdint>
#include <unordered_map>
#include <vector>

namespace lc::worldview {

struct CellSlot {
    std::uint64_t key = ~0ULL;
    int page = 0;
    int x = 0; // texel position in the page
    int y = 0;
    std::uint32_t generation = 0; // atlas generation it was drawn with
    bool complete = false;        // every sprite's page was resident
    bool ready = true;            // drawn (impostors fill in over a few frames)
    bool animated = false;        // holds animated terrain
    std::uint64_t anim = 0;       // animation step it was drawn at
};

class CellCache {
public:
    CellCache(SDL_Renderer* renderer, std::size_t budget);

    void beginFrame() { ++frame_; }
    // The slot holding `key` (marked used this frame), or -1.
    [[nodiscard]] int find(std::uint64_t key);
    // A slot for `key`: a fresh one, or the least recently used one not used this frame (or -1).
    [[nodiscard]] int acquire(std::uint64_t key);
    [[nodiscard]] CellSlot& slot(int i) { return slots_[static_cast<std::size_t>(i)]; }
    [[nodiscard]] SDL_Texture* page(int p) const {
        return pages_[static_cast<std::size_t>(p)].get();
    }
    [[nodiscard]] static Vec2 pageSize(); // texels of a cache page
    void clear();
    // Raises the memory budget (never lowers it).
    void reserve(std::size_t budget);
    [[nodiscard]] std::size_t bytes() const;
    [[nodiscard]] int cached() const { return static_cast<int>(byKey_.size()); }

private:
    SDL_Renderer* renderer_;
    std::size_t maxSlots_;
    std::vector<TexturePtr> pages_;
    std::vector<CellSlot> slots_;
    std::vector<std::uint64_t> used_; // frame each slot was last used
    std::unordered_map<std::uint64_t, int> byKey_;
    std::uint64_t frame_ = 1;
};

} // namespace lc::worldview
