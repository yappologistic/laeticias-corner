#pragma once
// A set catalog `assets/sets/<set>/catalog.json` (docs/design/world-tech.md §1.12): terrain,
// items, actors, goods and the art block of one set. Ids are `<set>.<name>`.

#include "core/catalog.hpp"

#include <array>
#include <cstdint>
#include <expected>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace lc::world {

struct SetTerrain {
    std::string id;
    std::string name;
    bool base = false;
    std::string under; // the base drawn under an overlay; empty for a base
    int variants = 1;
    int edges = 0; // 16 for overlays with masks
    float fps = 0;
    std::vector<std::string> faces; // edge materials raised tiles may use (aux picks one)
    bool water = false;
    bool paved = false;
    std::optional<std::array<std::uint8_t, 3>> colour; // flat look while the set has no art
};

// Slot behaviour (living-world.md §2.3); its positions come from the geometry file.
struct SlotBehaviour {
    std::string id;
    std::string kind;
    int cap = 1;
};

struct SetItem {
    std::string id;
    std::string name;
    int footW = 1; // grid extents at r0
    int footH = 1;
    Layout layout = Layout::Variant;
    int count = 1;
    Surface on = Surface::Land;
    bool walkable = false;
    bool landmark = false;
    std::vector<int> rotations; // rendered rotations
    float scale = 1;
    int height = 0;
    std::vector<std::string> layers;
    std::vector<std::string> states;
    bool occluder = false;
    std::string card;
    std::string standIn; // a home item drawn in its place while the set has no art
    int rise = 0;        // stairs and ramps: levels climbed from the foot to the head
    char axis = 0;       // 'x' or 'y' at r0 when rise > 0
    float fps = 0;
    std::vector<SlotBehaviour> slots;
    std::vector<std::pair<std::string, std::string>> emitters; // point name, effect
};

struct SetActor {
    std::string id;
    std::string name;
    std::string sprite;
    int variants = 1;
    std::vector<std::pair<std::string, float>> anims; // pose, fps
    int sizeW = 0;                                    // depth footprint in tiles; 0 for people
    int sizeH = 0;
};

struct SetGoods {
    std::string id;
    std::string name;
    std::string sprite;
    int stack = 1;
};

struct SetArt {
    std::vector<std::string> edges;
    std::vector<std::string> backdrops;
    std::vector<std::string> fx;
};

struct SetCatalog {
    std::string set;
    std::string file;
    std::vector<SetTerrain> terrain;
    std::vector<SetItem> items;
    std::vector<SetActor> actors;
    std::vector<SetGoods> goods;
    SetArt art;
};

// A terrain is water when its catalog says `"water": true`, or, while the catalogs do not state
// it, when its name (after the set prefix) is one worldgen treats as water. One list, here.
[[nodiscard]] bool waterByName(std::string_view terrainId);

[[nodiscard]] std::expected<SetCatalog, std::string>
parseSetCatalog(std::string_view text, std::string_view file, std::string_view set);

} // namespace lc::world
