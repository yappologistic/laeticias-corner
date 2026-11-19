#include "worldview/cell_cache.hpp"

#include "worldview/cells.hpp"
#include "worldview/tuning.hpp"

#include <algorithm>
#include <bit>

namespace lc::worldview {
namespace {

constexpr std::size_t kSlotBytes =
    static_cast<std::size_t>(tuning::kCellTexels) * tuning::kCellTexels * 4;
constexpr int kPerPage = tuning::kCellPageSlotsX * tuning::kCellPageSlotsY;
constexpr int kPageW = tuning::kCellTexels * tuning::kCellPageSlotsX;
constexpr int kPageH = tuning::kCellTexels * tuning::kCellPageSlotsY;
constexpr int kEmpty = -1;
constexpr int kGone = -2;

// Slots come in whole cache pages.
std::size_t wholePages(std::size_t slots) {
    return (slots + kPerPage - 1) / kPerPage * kPerPage;
}

} // namespace

CellCache::CellCache(SDL_Renderer* renderer, std::size_t budget, bool warm)
    : renderer_(renderer), maxSlots_(0), warm_(warm) {
    reserve(budget);
}

Vec2 CellCache::pageSize() {
    return {static_cast<float>(kPageW), static_cast<float>(kPageH)};
}

std::size_t CellCache::home(std::uint64_t key) const {
    // Fibonacci hashing: cell keys differ in a few low bits of each field.
    return static_cast<std::size_t>((key * 0x9E3779B97F4A7C15ULL) >> 32) & (table_.size() - 1);
}

int CellCache::peek(std::uint64_t key) const {
    for (std::size_t i = home(key);; i = (i + 1) & (table_.size() - 1)) {
        const int s = table_[i];
        if (s == kEmpty) return -1;
        if (s >= 0 && slots_[static_cast<std::size_t>(s)].key == key) return s;
    }
}

int CellCache::find(std::uint64_t key) {
    const int s = peek(key);
    if (s >= 0) used_[static_cast<std::size_t>(s)] = frame_;
    return s;
}

void CellCache::insert(std::uint64_t key, int slot) {
    std::size_t i = home(key);
    while (table_[i] >= 0) i = (i + 1) & (table_.size() - 1);
    if (table_[i] == kGone) --gone_;
    table_[i] = slot;
    ++live_;
}

void CellCache::erase(std::uint64_t key) {
    for (std::size_t i = home(key);; i = (i + 1) & (table_.size() - 1)) {
        const int s = table_[i];
        if (s == kEmpty) return;
        if (s < 0 || slots_[static_cast<std::size_t>(s)].key != key) continue;
        table_[i] = kGone;
        ++gone_;
        --live_;
        return;
    }
}

void CellCache::rehash() {
    // In place: the table keeps its size, so nothing is allocated.
    std::ranges::fill(table_, kEmpty);
    gone_ = 0;
    live_ = 0;
    for (std::size_t s = 0; s < slots_.size(); ++s)
        if (slots_[s].key != ~0ULL) insert(slots_[s].key, static_cast<int>(s));
}

bool CellCache::addPage() {
    TexturePtr t{
        SDL_CreateTexture(renderer_, kTextureFormat, SDL_TEXTUREACCESS_TARGET, kPageW, kPageH)};
    if (!t) {
        SDL_Log("cells: cannot create a cache page: %s", SDL_GetError());
        return false;
    }
    if (warm_) {
        // Cleared and read back, so the driver allocates it now.
        SDL_Texture* out = SDL_GetRenderTarget(renderer_);
        const SDL_Rect one{0, 0, 1, 1};
        if (!SDL_SetRenderTarget(renderer_, t.get()) ||
            !SDL_SetRenderDrawColorFloat(renderer_, 0, 0, 0, 0) || !SDL_RenderClear(renderer_))
            SDL_Log("cells: %s", SDL_GetError());
        if (const SurfacePtr px{SDL_RenderReadPixels(renderer_, &one)}; !px)
            SDL_Log("cells: %s", SDL_GetError());
        if (!SDL_SetRenderTarget(renderer_, out)) SDL_Log("cells: %s", SDL_GetError());
    }
    pages_.push_back(std::move(t));
    return true;
}

int CellCache::acquire(std::uint64_t key, std::uint64_t spare) {
    int i = -1;
    if (slots_.size() < maxSlots_) {
        const auto n = static_cast<int>(slots_.size());
        const int page = n / kPerPage;
        if (page == static_cast<int>(pages_.size()) && !addPage()) maxSlots_ = slots_.size();
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
        i = lruSlot(used_, frame_, spare);
        if (i < 0) return -1;
        if (slots_[static_cast<std::size_t>(i)].key != ~0ULL)
            erase(slots_[static_cast<std::size_t>(i)].key);
        if (gone_ > static_cast<int>(table_.size() / 4)) {
            slots_[static_cast<std::size_t>(i)].key = ~0ULL;
            rehash();
        }
    }
    CellSlot& s = slots_[static_cast<std::size_t>(i)];
    s.key = key;
    s.complete = false;
    s.period = 1;
    s.ready = true;
    used_[static_cast<std::size_t>(i)] = frame_;
    insert(key, i);
    return i;
}

void CellCache::reserve(std::size_t budget) {
    const std::size_t slots = wholePages(std::max<std::size_t>(kPerPage, budget / kSlotBytes));
    if (slots <= maxSlots_) return;
    maxSlots_ = slots;
    // Everything a slot or the index will ever need, now: taking a slot allocates nothing.
    slots_.reserve(maxSlots_);
    used_.reserve(maxSlots_);
    table_.assign(std::bit_ceil(maxSlots_ * 4), kEmpty);
    rehash();
    if (warm_)
        while (pages_.size() * kPerPage < maxSlots_ && addPage()) {}
}

std::size_t CellCache::budget() const {
    return maxSlots_ * kSlotBytes;
}

void CellCache::clear() {
    for (CellSlot& s : slots_) s.key = ~0ULL;
    rehash();
}

void CellCache::staleAll() {
    for (CellSlot& s : slots_) {
        s.complete = false;
        s.generation = ~0u;
    }
}

std::size_t CellCache::bytes() const {
    return pages_.size() * kSlotBytes * kPerPage;
}

} // namespace lc::worldview
