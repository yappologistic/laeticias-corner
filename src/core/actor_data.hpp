#pragma once
// Actor kinds compiled from the catalog (docs/design/living-world.md §2): every visitor read as a
// kind (§2.5) plus the resident (§2.6). Routines become one flat program of steps, blocks and
// pick options that the actor system interprets; nothing here allocates once compiled.

#include "core/iso.hpp"

#include <nlohmann/json_fwd.hpp>

#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace lc {

struct Catalog;

// How a kind gets about: walk on the home grid, swim on water, walk the shore, or fly.
enum class Locomotion : std::uint8_t { Walk, Swim, Shore, Fly };

enum class Verb : std::uint8_t {
    Go,
    Use,
    Take,
    Put,
    Wander,
    Wait,
    Enter,
    Exit,
    Follow,
    Say,
    Emit,
    Pick,
    Routine,
    Each,
    If
};

// Engine hooks for outcomes data cannot express (living-world.md §2.2 `effect`).
enum class Effect : std::uint8_t { None, WaterBed, CallHens, TossPebble, Cook, ReactLine };

// Where a target's slot is: on the item (lifted to its perch), on a free tile beside it, or
// either (the item's first slot, else on, else beside).
enum class Spot : std::uint8_t { Any, On, Beside };

// Engine-provided target sets for `{"poi": ...}`.
enum class Poi : std::uint8_t { Stroll, NewItems, Visitors, Nooks };

struct Target {
    enum class Kind : std::uint8_t {
        Items,    // item types in `ids`
        Tag,      // items carrying tag `id`
        SlotKind, // items with a slot of kind `slotKind` (and tag `id` when >= 0)
        Home,     // a slot on the actor's home item
        Here,
        Each,
        Bank,     // land next to water
        Shore,    // water next to land, or land next to water
        Resident, // the resident (follow her, or sit on her hat)
        Bedroll,  // the resident's sleeping spot when she has no home
        Poi,
        Nook // beside an instance of nook `id`
    };
    Kind kind = Kind::Here;
    std::vector<int> ids;
    int id = -1;       // tag, or nook
    int slot = -1;     // named slot (Catalog::slotNames), -1: chosen by `spot`
    int slotKind = -1; // Catalog::slotKinds
    Spot spot = Spot::Any;
    float within = 0; // tiles, 0: anywhere in the active area
    bool nearHome = false;
    Poi poi = Poi::Stroll;
};

enum class Until : std::uint8_t { None, Hour, Phase, Clear, Rain };

struct Step {
    Verb verb = Verb::Wait;
    Effect effect = Effect::None;
    Until until = Until::None;
    std::uint8_t anim = 0xFF;     // kind animation index, 0xFF: none (idle)
    std::uint8_t callAnim = 0xFF; // played every `every` seconds during a use
    std::uint8_t phases = 0;      // Until::Phase: phase bits
    float hour = 0;               // Until::Hour
    float dur0 = 0;               // seconds; dur1 <= 0 means "no duration"
    float dur1 = 0;
    float every0 = 0;
    float every1 = 0;
    float radius = 0;     // wander radius; follow spacing
    int target = -1;      // Target index
    int orElse = -1;      // fallback Target
    int a = -1;           // Pick: first option; If/Each: `do` block; Routine: routine; Say: line
                          // context; Take/Put: goods; Emit: sfx
    int b = 0;            // Pick: option count; If: `else` block (-1 none); Each: max
    int cond = -1;        // If: condition node
    int activity = -1;    // nook `prefer` key (Catalog::activityNames)
    bool nearest = false; // Each: nearest first
    bool onHat = false;   // Follow the resident by resting on her hat
};

struct Block {
    int first = 0; // into ActorProgram::blockSteps
    int count = 0;
};

struct PickOption {
    float weight = 1;
    int block = 0;
    int cond = -1;             // `when`
    std::uint8_t phases = 0xF; // `time`
    std::uint8_t seasons = 0xFF;
    float needsSitting = 0; // the resident must have sat this long nearby
    int activity = -1;      // prefer key: the option's id
};

struct Routine {
    std::string name;
    int block = 0;
    bool loop = false;
};

struct ScheduleBlock {
    float from = 0; // game hours, wrapping past midnight
    float to = 0;
    int routine = 0;
};

struct Interrupt {
    enum class On : std::uint8_t { Rain, PlacedNearby, Harvest };
    On on = On::Rain;
    int routine = 0;
    int priority = 0;
    float chance = 1;
    float cooldown = 0;
    float delay = 0; // the condition must hold this long first
};

struct ActorKind {
    std::string id;
    std::string sprite; // atlas key prefix
    int visitor = -1;   // catalog visitor index; -1: the resident
    Locomotion move = Locomotion::Walk;
    float speed = 1;
    int main = 0;              // the looping routine of a visitor
    std::vector<int> routines; // indices into ActorProgram::routines
    std::vector<ScheduleBlock> schedule;
    std::vector<Interrupt> interrupts;
    std::vector<std::string> anims; // 0 move, 1 idle, then what routines name
    int home = -1;                  // item it lives in / gathers round, -1: none
    bool line = false;              // swims in a line behind the first of its kind
    float startleRadius = 0;
    std::uint8_t startleAnim = 0xFF;
    std::uint32_t startleFrom = ~0u; // anims it reacts from (bits), all by default
    std::uint8_t petAnim = 0xFF;
    std::string petSound; // sfx path; empty: voice or the default pet sound
    std::string voice;
    std::uint8_t sleepAnim = 0xFF;  // the animation that means "asleep" (z's, waking to pet)
    std::uint8_t carryAnim = 0xFF;  // walking with goods in hand
    std::uint8_t rainAnim = 0xFF;   // walking in the rain (an umbrella)
    std::uint8_t waddleAnim = 0xFF; // a swimmer walking on land
    std::uint8_t waveAnim = 0xFF;   // greeting the player
    std::uint8_t callAnim = 0xFF;   // its call (the first `call_anim` it names)
    bool watches = false;           // turns to face the pointer while idle

    [[nodiscard]] int findRoutine(std::string_view name, const struct ActorProgram& p) const;
};

struct ActorProgram {
    std::vector<Step> steps;
    std::vector<int> blockSteps;
    std::vector<Block> blocks;
    std::vector<PickOption> options;
    std::vector<Target> targets;
    std::vector<Routine> routines;
};

// Compiles every visitor (read as a kind, docs/design/living-world.md §2.5) and, when enabled,
// the resident into `cat.kinds` and `cat.program`. Throws std::runtime_error naming the entry.
void compileActors(const nlohmann::json& root, Catalog& cat);

} // namespace lc
