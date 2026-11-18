#include "worldview/cell_cache.hpp"

#include "worldview/cells.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>

namespace lc::worldview {
namespace {

constexpr std::size_t kSlotBytes =
    static_cast<std::size_t>(tuning::kCellTexels) * tuning::kCellTexels * 4;
constexpr int kPerPage = tuning::kCellPageSlotsX * tuning::kCellPageSlotsY;
constexpr int kPageW = tuning::kCellTexels * tuning::kCellPageSlotsX;
constexpr int kPageH = tuning::kCellTexels * tuning::kCellPageSlotsY;

} // namespace

CellCache::CellCache(SDL_Renderer* renderer, std::size_t budget)
    : renderer_(renderer), maxSlots_(std::max<std::size_t>(kPerPage, budget / kSlotBytes)) {}

Vec2 CellCache::pageSize() {
    return {static_cast<float>(kPageW), static_cast<float>(kPageH)};
}

int CellCache::find(std::uint64_t key) {
    const auto it = byKey_.find(key);
    if (it == byKey_.end()) return -1;
    used_[static_cast<std::size_t>(it->second)] = frame_;
    return it->second;
}

int CellCache::acquire(std::uint64_t key) {
    int i = -1;
    if (slots_.size() < maxSlots_) {
        const auto n = static_cast<int>(slots_.size());
        const int page = n / kPerPage;
        if (page == static_cast<int>(pages_.size())) {
            TexturePtr t{SDL_CreateTexture(renderer_, kTextureFormat, SDL_TEXTUREACCESS_TARGET,
                                           kPageW, kPageH)};
            if (!t) {
                SDL_Log("cells: cannot create a cache page: %s", SDL_GetError());
                maxSlots_ = slots_.size();
            } else {
                pages_.push_back(std::move(t));
            }
        }
        if (slots_.size() < maxSlots_) {
            const int k = n % kPerPage;
            CellSlot s;
            s.page = page;
            s.x = (k % tuning::kCellPageSlotsX) * tuning::kCellTexels;
            s.y = (k / tuning::kCellPageSlotsX) * tuning::kCellTexels;
            slots_.push_back(s);
            used_.push_back(0);
            i = n;
        }
    }
    if (i < 0) {
        i = lruSlot(used_, frame_);
        if (i < 0) return -1;
        byKey_.erase(slots_[static_cast<std::size_t>(i)].key);
    }
    CellSlot& s = slots_[static_cast<std::size_t>(i)];
    s.key = key;
    s.complete = false;
    s.animated = false;
    s.ready = true;
    used_[static_cast<std::size_t>(i)] = frame_;
    byKey_[key] = i;
    return i;
}

void CellCache::reserve(std::size_t budget) {
    maxSlots_ = std::max(maxSlots_, budget / kSlotBytes);
}

std::size_t CellCache::budget() const {
    // Slots come in whole cache pages.
    return (maxSlots_ + kPerPage - 1) / kPerPage * kPerPage * kSlotBytes;
}

void CellCache::clear() {
    byKey_.clear();
    for (CellSlot& s : slots_) s.key = ~0ULL;
}

std::size_t CellCache::bytes() const {
    return pages_.size() * kSlotBytes * kPerPage;
}

} // namespace lc::worldview
