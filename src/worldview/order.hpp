#pragma once
// Painter's order for the world's elements (docs/design/world-tech.md §4.4): items, the pieces of
// split landmarks, and raised ground tiles that hide something behind them. The exact topological
// order of render/depth.hpp, with a page-aware tie-break: among the elements whose predecessors
// are all drawn, one on the texture page already bound is preferred, so page switches (draw
// calls) stay few. Pure logic (no SDL).

#include "core/iso.hpp"
#include "render/depth.hpp"

#include <cstdint>
#include <span>
#include <vector>

namespace lc::worldview {

struct OrderItem {
    FRect foot;   // footprint, tile coordinates
    FRect screen; // world px box of everything it draws
    std::uint16_t page = 0;
    bool ground = false; // a raised ground tile (drawn under anything standing on it)
};

// True when a must be drawn before b: the footprint rule, except that ground goes under any
// item whose footprint covers it.
[[nodiscard]] bool drawnBefore(const OrderItem& a, const OrderItem& b);

class PageOrder {
public:
    // Orders `items` so that every pair of overlapping screen boxes is drawn back to front.
    // Deterministic: ties go to the bound page, then the shallower footprint, then the index.
    void sort(std::span<const OrderItem> items, float cell, std::vector<std::uint32_t>& order);

private:
    ScreenGrid grid_;
    std::vector<FRect> screens_;
    std::vector<std::uint32_t> edgeFrom_;
    std::vector<std::uint32_t> edgeTo_;
    std::vector<std::uint32_t> start_;
    std::vector<std::uint32_t> next_;
    std::vector<std::uint32_t> cursor_;
    std::vector<int> indegree_;
    std::vector<std::uint8_t> done_;
    std::vector<std::vector<std::pair<float, std::uint32_t>>> ready_; // per page, min-heaps
};

// Page switches along an order (what each one costs is a draw call).
[[nodiscard]] int pageSwitches(std::span<const OrderItem> items,
                               std::span<const std::uint32_t> order);

} // namespace lc::worldview
