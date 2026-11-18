#pragma once
// Slots for cells (worldview/cells.hpp) in shared page textures under a memory budget, reused
// least-recently-used. What goes into a slot is the renderer's business. Looking a cell up and
// taking a slot allocate nothing: the index is a fixed open-addressing table.

#include "core/iso.hpp"
#include "platform/sdl_ptr.hpp"

#include <cstdint>
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
    std::uint8_t period = 1;      // steps in its animation's loop (1: nothing in it moves)
};

class CellCache {
public:
    // `warm`: cache pages are made and touched as soon as the budget allows them (a driver
    // stalls a frame on the first draw into a fresh 32 MiB target; better at load than in play).
    CellCache(SDL_Renderer* renderer, std::size_t budget, bool warm);

    void beginFrame() { ++frame_; }
    // The slot holding `key` (marked used this frame), or -1.
    [[nodiscard]] int find(std::uint64_t key);
    // The same without marking it used.
    [[nodiscard]] int peek(std::uint64_t key) const;
    // A slot for `key`: a fresh one, or the least recently used one not used this frame nor in
    // the `spare` frames before it (or -1).
    [[nodiscard]] int acquire(std::uint64_t key, std::uint64_t spare = 0);
    [[nodiscard]] CellSlot& slot(int i) { return slots_[static_cast<std::size_t>(i)]; }
    [[nodiscard]] const CellSlot& slot(int i) const { return slots_[static_cast<std::size_t>(i)]; }
    [[nodiscard]] SDL_Texture* page(int p) const {
        return pages_[static_cast<std::size_t>(p)].get();
    }
    [[nodiscard]] static Vec2 pageSize(); // texels of a cache page
    void clear();
    // Raises the memory budget (never lowers it).
    void reserve(std::size_t budget);
    [[nodiscard]] std::size_t budget() const;
    [[nodiscard]] std::size_t bytes() const;
    [[nodiscard]] int cached() const { return live_; }
    // Slots the budget holds.
    [[nodiscard]] std::size_t capacity() const { return maxSlots_; }

private:
    bool addPage();
    void rehash();
    void insert(std::uint64_t key, int slot);
    void erase(std::uint64_t key);
    [[nodiscard]] std::size_t home(std::uint64_t key) const;

    SDL_Renderer* renderer_;
    std::size_t maxSlots_;
    bool warm_;
    std::vector<TexturePtr> pages_;
    std::vector<CellSlot> slots_;
    std::vector<std::uint64_t> used_; // frame each slot was last used
    // Open addressing over slot indices: kEmpty ends a probe, kGone (a removed entry) does not.
    std::vector<int> table_;
    int gone_ = 0;
    int live_ = 0;
    std::uint64_t frame_ = 1;
};

} // namespace lc::worldview
