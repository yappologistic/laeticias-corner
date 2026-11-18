// The condition vocabulary (docs/design/living-corner.md §3) and the catalog's wish tree.

#include "core/catalog.hpp"
#include "core/condition.hpp"
#include "core/land.hpp"
#include "core/rng.hpp"
#include "core/world.hpp"
#include "test_support.hpp"

#include <doctest.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <set>

using namespace lc;

namespace {

int item(std::string_view id) {
    return *test::catalog().findItem(id);
}
int terrain(std::string_view id) {
    return *test::catalog().findTerrain(id);
}

struct Probe {
    ConditionSet set;
    std::vector<std::string> nooks{"reading_nook"};
    CondFacts facts;
    std::vector<int> present = std::vector<int>(test::catalog().visitors.size(), 0);
    std::vector<std::uint8_t> seen = std::vector<std::uint8_t>(test::catalog().visitors.size(), 0);
    std::vector<std::uint8_t> nookHere = std::vector<std::uint8_t>(1, 0);

    Probe() {
        set.setBaseTerrain(test::catalog().baseTerrain);
        facts.present = present;
        facts.seen = seen;
        facts.nookHere = nookHere;
    }
    int add(std::string_view text) {
        return set.compile(nlohmann::json::parse(text), test::catalog(), nooks, "test");
    }
    bool eval(std::string_view text, const World& w) { return set.eval(add(text), w, facts); }
};

void put(World& w, std::string_view id, int x, int y, int variant = 0) {
    w.addItem(makeItem(test::catalog(), item(id), variant, {x, y}));
}

} // namespace

TEST_CASE("conditions: logic, counts, variety and facts") {
    const Catalog& c = test::catalog();
    World w(c);
    Probe p;
    CHECK(p.eval(R"({"all": []})", w));
    CHECK_FALSE(p.eval(R"({"any": []})", w));
    CHECK(p.eval(R"({"not": {"any": []}})", w));
    put(w, "flowers_red", 1, 1);
    put(w, "flowers_white", 2, 1);
    put(w, "flowers_white", 3, 1);
    CHECK(p.eval(R"({"count": {"tag": "flower", "min": 3}})", w));
    CHECK_FALSE(p.eval(R"({"count": {"tag": "flower", "min": 4}})", w));
    CHECK(p.eval(R"({"count": {"item": "flowers_white", "min": 2, "max": 2}})", w));
    CHECK_FALSE(p.eval(R"({"count": {"items": ["flowers_white", "flowers_red"], "max": 2}})", w));
    CHECK(p.eval(R"({"count": {"item": "oak", "max": 0}})", w)); // with a max, min defaults to 0
    CHECK_FALSE(p.eval(R"({"count": {"item": "oak"}})", w));     // min defaults to 1
    CHECK(p.eval(R"({"variety": {"tag": "flower", "min": 2}})", w));
    CHECK_FALSE(p.eval(R"({"variety": {"tag": "flower", "min": 3}})", w));
    for (int x = 0; x < 5; ++x) w.setTerrain({x, 5}, c.waterTerrain);
    CHECK(p.eval(R"({"count": {"terrain": "water", "min": 5}})", w));
    CHECK(p.eval(R"({"count": {"terrains": ["water", "path"], "min": 5, "max": 5}})", w));

    p.facts.phase = Phase::Dusk;
    CHECK(p.eval(R"({"time": ["dusk", "night"]})", w));
    CHECK_FALSE(p.eval(R"({"time": ["day"]})", w));
    p.facts.season = *c.findSeason("winter");
    CHECK(p.eval(R"({"season": ["winter"]})", w));
    CHECK_FALSE(p.eval(R"({"season": ["spring", "summer"]})", w));
    CHECK(p.eval(R"({"weather": "clear"})", w));
    p.facts.raining = true;
    CHECK(p.eval(R"({"weather": "rain"})", w));

    const auto cat = static_cast<std::size_t>(*c.findVisitor("cat"));
    CHECK_FALSE(p.eval(R"({"seen": "cat"})", w));
    p.seen[cat] = 1;
    CHECK(p.eval(R"({"seen": "cat"})", w));
    CHECK_FALSE(p.eval(R"({"visitor": {"id": "cat"}})", w));
    p.present[cat] = 1;
    CHECK(p.eval(R"({"visitor": {"id": "cat"}})", w));
    CHECK_FALSE(p.eval(R"({"visitor": {"id": "cat", "min": 2}})", w));
    CHECK_FALSE(p.eval(R"({"nook": "reading_nook"})", w));
    p.nookHere[0] = 1;
    CHECK(p.eval(R"({"nook": "reading_nook"})", w));

    p.facts.counters = {2, 5, 1, 6, 0, 1};
    CHECK(p.eval(R"({"progress": {"wishes": 2, "pages": 6}})", w));
    CHECK_FALSE(p.eval(R"({"progress": {"wishes": 2, "harvests": 1}})", w));
    CHECK(p.eval(R"({"progress": {"stage": 1}})", w));

    // Bad content is refused, naming the context.
    for (const char* bad :
         {R"({"count": {"item": "unicorn"}})",
          R"({"near": {"anchor": {"item": "oak"}, "within": 5, "has": [{"item": "oak"}]}})",
          R"({"time": "day"})", R"({"progress": {"luck": 1}})",
          R"({"count": {"item": "oak", "tag": "tree"}})", R"({"all": [], "any": []})",
          R"({"nook": "nowhere"})", R"({"count": {"tag": "edible"}})"}) {
        CAPTURE(bad);
        CHECK_THROWS(p.add(bad));
    }
}

TEST_CASE("conditions: near areas exclude the footprint, the anchor and wild land") {
    const Catalog& c = test::catalog();
    World w(c);
    Probe p;
    // A cottage (2x2) with path all round its door side.
    put(w, "cottage", 10, 10);
    const char* path3 = R"({"near": {"anchor": {"item": "cottage"}, "within": 1,
                            "has": [{"terrains": ["path", "cobble"], "min": 3}]}})";
    w.setTerrain({12, 10}, terrain("path"));
    w.setTerrain({12, 11}, terrain("path"));
    CHECK_FALSE(p.eval(path3, w));
    // Terrain under the footprint is not part of the area.
    w.setTerrain({10, 10}, terrain("path"));
    CHECK_FALSE(p.eval(path3, w));
    w.setTerrain({12, 12}, terrain("cobble")); // the diagonal counts (Chebyshev)
    CHECK(p.eval(path3, w));
    // Two tiles away is outside within 1.
    w.setTerrain({12, 12}, c.baseTerrain);
    w.setTerrain({13, 10}, terrain("path"));
    CHECK_FALSE(p.eval(path3, w));

    // The anchor never counts itself; an item counts once however many of its tiles are near.
    put(w, "bench", 20, 20);
    const char* twoBenches = R"({"near": {"anchor": {"item": "bench"}, "within": 1,
                                 "has": [{"item": "bench", "min": 1}]}})";
    CHECK_FALSE(p.eval(twoBenches, w));
    put(w, "barn", 21, 18); // 3x2: tiles (21..23, 18..19), two of them touch the bench's area
    CHECK(p.eval(R"({"near": {"anchor": {"item": "bench"}, "within": 1,
                     "has": [{"item": "barn", "min": 1, "max": 1}]}})",
                 w));
    put(w, "bench", 21, 21);
    CHECK(p.eval(twoBenches, w));
    CHECK(p.eval(R"({"near": {"anchor": {"item": "bench"}, "within": 2,
                     "has": [{"item": "bench"}], "anchors": 2}})",
                 w));
    CHECK_FALSE(p.eval(R"({"near": {"anchor": {"item": "bench"}, "within": 2,
                           "has": [{"item": "bench"}], "anchors": 3}})",
                       w));
    // max 0: "none of these in the area".
    const char* dark = R"({"near": {"anchor": {"item": "bench"}, "within": 2,
                           "has": [{"tag": "light", "max": 0}]}})";
    CHECK(p.eval(dark, w));
    put(w, "lamp", 18, 20);
    CHECK(p.eval(dark, w)); // the second bench is still dark
    put(w, "lamp", 23, 23);
    CHECK_FALSE(p.eval(dark, w));

    // Instances: every passing anchor, with its footprint.
    const int near = p.add(twoBenches);
    std::vector<NearInstance> found;
    p.set.instances(near, w, found);
    CHECK(found.size() == 2);

    // Wild tiles do not exist for conditions: neither in areas nor in totals.
    World v(c);
    applyLand(v, c, 0);
    const int water = c.waterTerrain;
    v.setTerrain({20, 20}, water);
    v.setTerrain({20, 21}, water);
    put(v, "reeds", 21, 21);
    const char* reedsInWater = R"({"near": {"anchor": {"item": "reeds"}, "within": 1,
                                   "has": [{"terrain": "water", "min": 2}]}})";
    CHECK(p.eval(reedsInWater, v));
    CHECK(p.eval(R"({"count": {"terrain": "grass", "min": 398, "max": 398}})", v));
    // Terrain on a wild tile (only a damaged save could put it there) is not counted.
    v.setTerrain({20, 21}, c.baseTerrain);
    v.setTerrain({19, 21}, water);
    CHECK(v.isWild({19, 21}));
    CHECK_FALSE(p.eval(reedsInWater, v));

    // Terrain anchors: each matching tile is an anchor.
    World t(c);
    for (int x = 5; x < 9; ++x) t.setTerrain({x, 5}, terrain("path"));
    for (int x = 5; x < 9; ++x) put(t, "oak", x, 7);
    const char* walk = R"({"near": {"anchor": {"terrain": "path"}, "within": 2,
                          "has": [{"tag": "tree", "min": 4}]}})";
    CHECK(p.eval(walk, t));
    std::vector<NearInstance> tiles;
    p.set.instances(p.add(walk), t, tiles);
    CHECK(tiles.size() == 2); // the middle two path tiles reach all four oaks
}

TEST_CASE("conditions: waiting mode, progress readout and needed pieces") {
    const Catalog& c = test::catalog();
    World w(c);
    Probe p;
    put(w, "bench", 5, 5);
    put(w, "lamp", 6, 5);
    const int lit =
        p.add(R"({"all": [{"time": ["dusk", "night"]}, {"near": {"anchor": {"item": "bench"},
                              "within": 2, "has": [{"tag": "light", "min": 1}]}}]})");
    p.facts.phase = Phase::Day;
    CHECK_FALSE(p.set.eval(lit, w, p.facts));
    p.facts.waiting = true;
    CHECK(p.set.eval(lit, w, p.facts)); // only the hour is missing
    p.facts.waiting = false;
    const auto waitingFor = p.set.firstWaiting(lit, p.facts);
    REQUIRE(waitingFor);
    CHECK(p.set.node(*waitingFor).kind == CondKind::Time);
    p.facts.phase = Phase::Night;
    CHECK_FALSE(p.set.firstWaiting(lit, p.facts));
    CHECK(p.set.eval(lit, w, p.facts));

    const int flowers = p.add(R"({"count": {"tag": "flower", "min": 4}})");
    put(w, "flowers_red", 1, 1);
    const auto prog = p.set.countProgress(flowers, w);
    REQUIRE(prog);
    CHECK(prog->first == 1);
    CHECK(prog->second == 4);
    CHECK_FALSE(p.set.countProgress(lit, w));

    std::vector<int> needs;
    p.set.needed(p.add(R"({"all": [{"near": {"anchor": {"item": "tall_grass"}, "within": 3,
                            "has": [{"item": "tall_grass", "min": 4}, {"tag": "light", "max": 0}]}},
                           {"not": {"count": {"item": "barn"}}}]})"),
                 needs);
    // The anchor and the positive entry; neither the "none" entry nor anything under `not`.
    CHECK(needs.size() == 2);
}

TEST_CASE("catalog: every nook has one near, and the wish tree unlocks everything once") {
    const Catalog& c = test::catalog();
    CHECK(c.wishes.size() == 36);
    CHECK(c.nooks.size() == 16);
    CHECK(c.visitors.size() + c.nooks.size() == 30); // pages in all
    for (const NookDef& n : c.nooks) CHECK(c.conditions.node(n.near).kind == CondKind::Near);
    CHECK(c.stages.size() == 5);
    CHECK(c.stages[1].pages == 4);
    CHECK(c.stages.back().pages == 20);

    // Unlocks from the start set, each wish's ancestors (its `after` chain) and nothing else.
    std::set<int> grantedItems(c.start.items.begin(), c.start.items.end());
    std::set<int> grantedTerrain(c.start.terrain.begin(), c.start.terrain.end());
    std::set<int> grantedFrames(c.start.frames.begin(), c.start.frames.end());
    std::set<int> clues;
    for (const WishDef& w : c.wishes) {
        for (const int i : w.reward.items) CHECK_MESSAGE(grantedItems.insert(i).second, w.id);
        for (const int t : w.reward.terrain) CHECK_MESSAGE(grantedTerrain.insert(t).second, w.id);
        if (w.reward.frame >= 0) CHECK_MESSAGE(grantedFrames.insert(w.reward.frame).second, w.id);
        if (w.reward.clue >= 0) CHECK_MESSAGE(clues.insert(w.reward.clue).second, w.id);
    }
    CHECK(grantedItems.size() == c.items.size());
    CHECK(grantedTerrain.size() == c.terrain.size());
    CHECK(grantedFrames.size() == c.frames.size());
    CHECK(std::cmp_equal(clues.size(), std::ranges::count_if(c.visitors, [](const VisitorDef& v) {
                             return v.rare;
                         })));

    // Offered in catalog order once their earlier wishes are granted and every piece their goal
    // needs is unlocked (the offer rule), all 36 wishes come round: nothing waits on a piece
    // that only a later wish could unlock.
    std::set<int> items(c.start.items.begin(), c.start.items.end());
    std::set<int> terrains(c.start.terrain.begin(), c.start.terrain.end());
    std::vector<bool> granted(c.wishes.size(), false);
    for (bool progress = true; progress;) {
        progress = false;
        for (std::size_t wi = 0; wi < c.wishes.size(); ++wi) {
            const WishDef& w = c.wishes[wi];
            if (granted[wi] || !std::ranges::all_of(w.after, [&](int a) {
                    return granted[static_cast<std::size_t>(a)];
                }))
                continue;
            const bool ready = std::ranges::all_of(w.needed, [&](int s) {
                const Selector& sel = c.conditions.selector(s);
                return std::ranges::any_of(sel.ids, [&](int id) {
                    return sel.terrain ? terrains.contains(id) : items.contains(id);
                });
            });
            if (!ready) continue;
            granted[wi] = true;
            progress = true;
            items.insert(w.reward.items.begin(), w.reward.items.end());
            terrains.insert(w.reward.terrain.begin(), w.reward.terrain.end());
        }
    }
    for (std::size_t wi = 0; wi < c.wishes.size(); ++wi)
        CHECK_MESSAGE(granted[wi], c.wishes[wi].id << " can never be offered");
}

TEST_CASE("conditions: a multi-tile item counts when any tile is in reach of a terrain anchor") {
    // QA2-12: the item's top-left tile is the anchor tile itself, so the old "first tile" rule
    // never counted it although the rest of it lies in the area.
    const Catalog& c = test::catalog();
    World w(c);
    Probe p;
    w.setTerrain({10, 10}, terrain("path"));
    put(w, "barn", 10, 10);
    const char* near = R"({"near": {"anchor": {"terrain": "path"}, "within": 1,
                                    "has": [{"item": "barn", "min": 1}]}})";
    CHECK(p.eval(near, w));
    // Counted once even though several of its tiles are in the area.
    CHECK_FALSE(p.eval(R"({"near": {"anchor": {"terrain": "path"}, "within": 1,
                                    "has": [{"item": "barn", "min": 2}]}})",
                       w));
}

TEST_CASE("conditions: near agrees with a literal reading of the spec on random worlds") {
    // A differential check (QA2): every anchor's footprint grown by `within`, every item counted
    // once if any of its tiles lies in that area outside the anchor, terrain tile by tile.
    const Catalog& c = test::catalog();
    const int path = terrain("path");
    const std::vector<int> kinds = {item("barn"), item("hammock"), item("oak"), item("bench")};
    struct Case {
        const char* json;
        bool terrainAnchor;
        int anchor;
        int has;
        int min;
        int within;
    };
    const Case cases[] = {
        {R"({"near": {"anchor": {"terrain": "path"}, "within": 1, "has": [{"item": "barn"}]}})",
         true, path, kinds[0], 1, 1},
        {R"({"near": {"anchor": {"terrain": "path"}, "within": 2,
              "has": [{"item": "hammock", "min": 2}]}})",
         true, path, kinds[1], 2, 2},
        {R"({"near": {"anchor": {"item": "bench"}, "within": 1, "has": [{"item": "barn"}]}})",
         false, kinds[3], kinds[0], 1, 1},
        {R"({"near": {"anchor": {"item": "oak"}, "within": 2,
              "has": [{"item": "hammock", "min": 2}]}})",
         false, kinds[2], kinds[1], 2, 2},
    };
    Rng rng(20261117);
    for (int round = 0; round < 60; ++round) {
        World w(c);
        const TileRect zone{4, 4, 16, 16};
        for (int k = 0; k < 6; ++k)
            w.setTerrain({rng.range(zone.x0, zone.x1 - 1), rng.range(zone.y0, zone.y1 - 1)}, path);
        for (int k = 0; k < 14; ++k) {
            const int type = kinds[static_cast<std::size_t>(rng.range(0, 3))];
            const Item it = makeItem(
                c, type, 0, {rng.range(zone.x0, zone.x1 - 1), rng.range(zone.y0, zone.y1 - 1)});
            bool free = true;
            for (int y = it.pos.y; y < it.pos.y + it.h; ++y)
                for (int x = it.pos.x; x < it.pos.x + it.w; ++x) free = free && !w.itemAt({x, y});
            if (free) w.addItem(it);
        }
        for (const Case& cs : cases) {
            std::vector<TileRect> anchors;
            if (cs.terrainAnchor) {
                for (int y = 0; y < w.height(); ++y)
                    for (int x = 0; x < w.width(); ++x)
                        if (w.terrainAt({x, y}) == cs.anchor)
                            anchors.push_back({x, y, x + 1, y + 1});
            } else {
                for (const Item& it : w.items())
                    if (it.type == cs.anchor) anchors.push_back(it.rect());
            }
            bool expected = false;
            for (const TileRect& fp : anchors) {
                const TileRect area = TileRect{fp.x0 - cs.within, fp.y0 - cs.within,
                                               fp.x1 + cs.within, fp.y1 + cs.within}
                                          .clipped(w.bounds());
                int n = 0;
                for (const Item& it : w.items()) {
                    if (it.type != cs.has || it.rect() == fp) continue;
                    bool in = false;
                    for (int y = it.pos.y; y < it.pos.y + it.h; ++y)
                        for (int x = it.pos.x; x < it.pos.x + it.w; ++x)
                            in =
                                in || (area.contains(TilePos{x, y}) && !fp.contains(TilePos{x, y}));
                    n += in ? 1 : 0;
                }
                expected = expected || n >= cs.min;
            }
            Probe p;
            CHECK_MESSAGE(p.eval(cs.json, w) == expected, "round " << round << ": " << cs.json);
        }
    }
}
