// Wishes: offer order and pacing on a fake play clock, granting after a hold, snoozing.

#include "core/edit.hpp"
#include "core/progression.hpp"
#include "core/starter.hpp"
#include "core/tuning.hpp"
#include "test_support.hpp"

#include <doctest.h>

#include <algorithm>

using namespace lc;

namespace {

struct Game {
    const Catalog& cat = test::catalog();
    World world = makeStarterWorld(cat);
    Progress progress{cat};
    Progression rules{cat};
    std::vector<int> present = std::vector<int>(cat.visitors.size(), 0);
    std::vector<std::uint8_t> seen = std::vector<std::uint8_t>(cat.visitors.size(), 0);
    std::vector<std::uint8_t> nooks = std::vector<std::uint8_t>(cat.nooks.size(), 0);
    Phase phase = Phase::Day;
    double played = 0;
    std::vector<ProgressEvent> log;

    CondFacts facts() const {
        CondFacts f;
        f.phase = phase;
        f.present = present;
        f.seen = seen;
        f.nookHere = nooks;
        f.counters[static_cast<std::size_t>(Counter::Wishes)] =
            static_cast<int>(progress.granted.size());
        return f;
    }
    // Advances play time in simulation steps, re-evaluating after world changes as the game does.
    void run(double seconds) {
        const auto steps = static_cast<int>(seconds / tuning::kStepSeconds + 0.5);
        for (int i = 0; i < steps; ++i) {
            played += tuning::kStepSeconds;
            rules.tick(world, progress, facts(), played, true);
            for (const auto& e : rules.events()) log.push_back(e);
            rules.clearEvents();
        }
    }
    void changed() { rules.evaluate(world, progress, facts(), played); }
    int wish(std::string_view id) const { return *cat.findWish(id); }
    bool isOpen(std::string_view id) const {
        return std::ranges::find(progress.open, wish(id)) != progress.open.end();
    }
    bool done(std::string_view id) const {
        return progress.wishes[static_cast<std::size_t>(wish(id))].state == WishState::Done;
    }
    void place(std::string_view item, int x, int y, int v = 0) {
        world.addItem(makeItem(cat, *cat.findItem(item), v, {x, y}));
        changed();
    }
};

} // namespace

TEST_CASE("the first wish comes after 30 s and is granted once its goal holds for 1.5 s") {
    Game g;
    g.run(29.0);
    CHECK(g.progress.open.empty());
    g.run(1.5);
    REQUIRE(g.isOpen("first_flowers"));
    REQUIRE(g.log.size() == 1);
    CHECK(g.log[0].kind == ProgressEvent::Kind::WishOffered);
    CHECK_FALSE(g.log[0].already);
    // The starter scene has two flower patches: the card reads 2 / 4.
    const WishStatus& st = g.rules.status(g.wish("first_flowers"));
    CHECK(st.count == 2);
    CHECK(st.min == 4);
    CHECK_FALSE(st.ready);
    g.place("flowers_white", 30, 30);
    CHECK(g.rules.status(g.wish("first_flowers")).count == 3);
    g.place("flowers_red", 31, 30);
    CHECK(g.rules.status(g.wish("first_flowers")).ready);
    g.run(1.0);
    CHECK_FALSE(g.done("first_flowers")); // still in its hold
    g.run(1.0);
    CHECK(g.done("first_flowers"));
    CHECK(g.progress.items[static_cast<std::size_t>(*g.cat.findItem("flowers_violet"))]);
    CHECK(g.progress.newItems[static_cast<std::size_t>(*g.cat.findItem("berry_bush"))]);
    CHECK(g.log.back().kind == ProgressEvent::Kind::WishGranted);
    CHECK(g.progress.open.empty());
}

TEST_CASE("a passing state during an undo does not grant a wish") {
    Game g;
    g.run(31);
    REQUIRE(g.isOpen("first_flowers"));
    g.place("flowers_white", 30, 30);
    g.place("flowers_red", 31, 30);
    g.run(1.0);
    // Undone before the hold is over.
    g.world.removeItem(*g.world.itemIndexAt({31, 30}));
    g.changed();
    g.run(5.0);
    CHECK_FALSE(g.done("first_flowers"));
    g.place("flowers_red", 31, 30);
    g.run(2.0);
    CHECK(g.done("first_flowers"));
}

TEST_CASE("offers come one at a time, 75 s apart (30 s with none open), at most three") {
    Game g;
    g.progress.unlockEverything(g.cat);
    // Everything the early storyline needs is already built, so goals hold at once...
    g.place("flowers_white", 30, 30);
    g.place("flowers_red", 31, 30);
    g.run(31);
    REQUIRE(g.isOpen("first_flowers"));
    CHECK(g.log.back().already);
    // ...and an offered wish that is already met is granted 3 s later.
    g.run(1.5);
    CHECK_FALSE(g.done("first_flowers"));
    g.run(1.0);
    CHECK(g.done("first_flowers"));
    // The next offer waits from the grant: 30 s, since nothing is open.
    const double granted = g.played;
    g.run(29.0);
    CHECK(g.progress.open.empty());
    g.run(2.0);
    CHECK(g.isOpen("a_roof"));
    CHECK(g.played - granted >= tuning::kWishOfferGapEmpty);
    // With one open, the next comes 75 s later; never more than three.
    g.run(74.0);
    CHECK(g.progress.open.size() == 1);
    g.run(2.0);
    CHECK(g.progress.open.size() == 1); // a_roof gates the rest: nothing else is offerable yet
    g.place("cottage", 24, 32);
    g.run(2.0);
    CHECK(g.done("a_roof"));
    // Many wishes follow a_roof; they arrive one by one and the tray stops at three.
    g.run(30.5 + 75 * 4);
    CHECK(std::cmp_equal(g.progress.open.size(), tuning::kMaxOpenWishes));
    // Catalog order: the storyline comes first.
    CHECK(g.isOpen("path_to_door"));
    CHECK(g.isOpen("three_beds"));
    CHECK(g.isOpen("reading_light"));
}

TEST_CASE("givers must be about, gates must hold, and pieces must be unlocked") {
    Game g;
    g.phase = Phase::Night;
    g.run(60);
    CHECK(g.progress.open.empty()); // Laeticia offers nothing at night
    g.phase = Phase::Dusk;
    g.run(1.5);
    CHECK(g.isOpen("first_flowers"));
    // A visitor's wish needs that visitor seen (its gate) and present (the giver).
    const int duckWish = g.wish("duck_hideout");
    CHECK_FALSE(g.rules.offerable(duckWish, g.world, g.progress, g.facts(), g.played));
    g.seen[static_cast<std::size_t>(*g.cat.findVisitor("duck"))] = 1;
    CHECK_FALSE(g.rules.offerable(duckWish, g.world, g.progress, g.facts(), g.played));
    g.present[static_cast<std::size_t>(*g.cat.findVisitor("duck"))] = 2;
    CHECK(g.rules.offerable(duckWish, g.world, g.progress, g.facts(), g.played));
    // A wish whose goal needs a locked piece waits: path_to_door needs path or cobble (path is
    // unlocked) but only once a_roof is granted.
    CHECK_FALSE(
        g.rules.offerable(g.wish("path_to_door"), g.world, g.progress, g.facts(), g.played));
    // cat_pines needs pines, unlocked only by path_to_door.
    for (const char* id : {"first_flowers", "a_roof", "reading_light", "cat_fireside"})
        g.progress.wishes[static_cast<std::size_t>(g.wish(id))].state = WishState::Done;
    g.seen[static_cast<std::size_t>(*g.cat.findVisitor("cat"))] = 1;
    g.present[static_cast<std::size_t>(*g.cat.findVisitor("cat"))] = 1;
    CHECK_FALSE(g.rules.offerable(g.wish("cat_pines"), g.world, g.progress, g.facts(), g.played));
    g.progress.items[static_cast<std::size_t>(*g.cat.findItem("pine"))] = 1;
    CHECK(g.rules.offerable(g.wish("cat_pines"), g.world, g.progress, g.facts(), g.played));
}

TEST_CASE("Not now frees the slot; the wish returns after 600 s, after the others") {
    Game g;
    g.run(31);
    REQUIRE(g.isOpen("first_flowers"));
    g.rules.snooze(g.wish("first_flowers"), g.progress, g.played);
    CHECK(g.progress.open.empty());
    g.run(100);
    CHECK(g.progress.open.empty()); // nothing else is offerable before first_flowers is granted
    g.run(tuning::kWishSnooze - 100 + 2);
    CHECK(g.isOpen("first_flowers"));
    // Waiting display: a dusk-or-night goal names the hour it waits for.
    g.progress.wishes[static_cast<std::size_t>(g.wish("first_flowers"))].state = WishState::Done;
    g.progress.open.clear();
    g.progress.wishes[static_cast<std::size_t>(g.wish("a_roof"))].state = WishState::Done;
    g.progress.unlockEverything(g.cat);
    g.place("lamp", 30, 29);
    g.run(31);
    REQUIRE(g.isOpen("path_to_door"));
    g.run(76);
    g.run(76);
    REQUIRE(g.isOpen("reading_light"));
    const WishStatus& st = g.rules.status(g.wish("reading_light"));
    CHECK_FALSE(st.ready);
    REQUIRE(st.waiting >= 0);
    CHECK(g.cat.conditions.node(st.waiting).kind == CondKind::Time);
    g.phase = Phase::Dusk;
    g.changed();
    g.run(2);
    CHECK(g.done("reading_light"));
}

TEST_CASE("nooks are found when built, once, with their effects") {
    Game g;
    const int reading = *g.cat.findNook("reading_nook");
    g.changed();
    CHECK(g.progress.nooks[static_cast<std::size_t>(reading)] == 0);
    g.place("lamp", 30, 29);
    g.place("oak", 28, 28);
    CHECK(g.progress.nooks[static_cast<std::size_t>(reading)] == 1);
    CHECK(g.rules.nookHere()[static_cast<std::size_t>(reading)] == 1);
    REQUIRE(g.rules.events().size() == 1);
    CHECK(g.rules.events()[0].kind == ProgressEvent::Kind::NookFound);
    g.rules.clearEvents();
    // Broken and re-formed: present again, found only once.
    g.world.removeItem(*g.world.itemIndexAt({30, 29}));
    g.changed();
    CHECK(g.rules.nookHere()[static_cast<std::size_t>(reading)] == 0);
    g.place("lamp", 30, 29);
    CHECK(g.rules.events().empty());
    // Effects: the firefly hollow allows more fireflies; a kitchen garden speeds its beds.
    CHECK(g.rules.extraVisitors(*g.cat.findVisitor("firefly")) == 0);
    for (int x = 24; x < 28; ++x) g.place("planter", x, 37);
    g.place("scarecrow", 25, 38);
    CHECK(g.rules.nookGrowth(g.world, {24, 37, 25, 38}) == doctest::Approx(1.25f));
    CHECK(g.rules.nookGrowth(g.world, {35, 30, 36, 31}) == doctest::Approx(1.0f));
}
