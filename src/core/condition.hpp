#pragma once
// The shared condition vocabulary (wish goals and gates, rare-visitor recipes, nooks, music
// stems), compiled from catalog JSON into flat arrays and evaluated without allocating.
// Semantics: docs/design/living-corner.md §3. Defaults decided here: a selector's `min` is 1,
// or 0 when a `max` is given (so `{"tag": "light", "max": 0}` means "none").

#include "core/clock.hpp"
#include "core/iso.hpp"

#include <nlohmann/json_fwd.hpp>

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace lc {

struct Catalog;
class World;

enum class CondKind : std::uint8_t {
    All,
    Any,
    Not,
    Count,
    Variety,
    Near,
    Time,
    Season,
    Weather,
    Visitor,
    Seen,
    Nook,
    Progress
};

// The counters a `progress` term can name, in this order.
enum class Counter : std::uint8_t { Wishes, Seen, Nooks, Pages, Harvests, Stage, Count };
inline constexpr std::size_t kCounters = static_cast<std::size_t>(Counter::Count);
using Counters = std::array<int, kCounters>;

// What to count: item instances (by id, ids or tag) or terrain tiles (by id or ids).
struct Selector {
    bool terrain = false;
    bool tag = false;
    std::vector<std::uint8_t> match; // per item type, or per terrain index
    std::vector<int> ids;            // the indices that match
};

struct Has {
    int selector = 0;
    int min = 1;
    int max = -1; // -1: no upper bound
};

struct CondNode {
    CondKind kind = CondKind::All;
    int first = 0; // children (All/Any/Not) or `has` entries (Near): [first, first + count)
    int count = 0;
    int selector = -1; // Count, Variety (tag selector), Near (anchor)
    int min = 1;
    int max = -1;
    int within = 1;        // Near
    int anchors = 1;       // Near
    std::uint8_t mask = 0; // Time (phase bits), Season (season bits), Weather (1 = rain)
    int id = -1;           // Visitor, Seen (visitor index), Nook (nook index)
    Counters progress{};   // Progress: thresholds, -1 when not listed
};

// Facts that are not in the world: clock, weather, who is here, what has been achieved.
struct CondFacts {
    Phase phase = Phase::Day;
    int season = 0;
    bool raining = false;
    std::span<const int> present;           // critters per visitor, not counting leavers
    std::span<const std::uint8_t> seen;     // per visitor
    std::span<const std::uint8_t> nookHere; // per nook: an instance exists now
    Counters counters{};
    // Waiting mode (§3.3): time, season and weather terms count as true.
    bool waiting = false;
};

// A passing anchor of a `near` term: its footprint and the reach of its area.
struct NearInstance {
    TileRect footprint;
    int within = 1;
};

class ConditionSet {
public:
    // Compiles one condition; throws std::runtime_error naming `ctx` on invalid content.
    // `nookIds` resolves `nook` terms (nooks may be referenced before they are parsed).
    int compile(const nlohmann::json& j, const Catalog& cat, std::span<const std::string> nookIds,
                const std::string& ctx);

    [[nodiscard]] bool eval(int node, const World& world, const CondFacts& facts) const;
    // Every passing anchor of a `near` node (all of them, not just the `anchors` it needs),
    // written into `out` (cleared first; its storage is reused).
    void instances(int nearNode, const World& world, std::vector<NearInstance>& out) const;
    // The node of the single `near` in a nook condition: top level, or directly in a top `all`;
    // -1 when there is none or more than one.
    [[nodiscard]] int nookNear(int root) const;

    // The first time/season/weather term (depth first) that is false under `facts`, if any.
    [[nodiscard]] std::optional<int> firstWaiting(int node, const CondFacts& facts) const;
    // A top-level `count`: its current total and the `min` it needs.
    [[nodiscard]] std::optional<std::pair<int, int>> countProgress(int node,
                                                                   const World& world) const;
    // Selectors whose matches the condition needs present (positive minimums, outside `not`).
    void needed(int node, std::vector<int>& out) const;

    [[nodiscard]] const CondNode& node(int i) const { return nodes_[static_cast<std::size_t>(i)]; }
    [[nodiscard]] const Selector& selector(int i) const {
        return selectors_[static_cast<std::size_t>(i)];
    }
    [[nodiscard]] std::size_t size() const { return nodes_.size(); }
    void setBaseTerrain(int base) { base_ = base; }

private:
    int compileSelector(const nlohmann::json& j, const Catalog& cat, const std::string& ctx);
    [[nodiscard]] int countMatches(int selector, const World& world) const;
    // Counts passing anchors of a near node, stopping once `stopAt` pass (0: never stop);
    // passing anchors are appended to `out` when it is given.
    int nearPass(const CondNode& n, const World& world, int stopAt,
                 std::vector<NearInstance>* out) const;
    [[nodiscard]] bool anchorPasses(const CondNode& n, const World& world, TileRect footprint,
                                    const void* anchorItem) const;

    std::vector<CondNode> nodes_;
    std::vector<int> children_;
    std::vector<Has> has_;
    std::vector<Selector> selectors_;
    int base_ = 0;
};

} // namespace lc
