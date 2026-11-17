#include "render/sprites.hpp"

#include <algorithm>
#include <format>

namespace lc {
namespace {

constexpr std::array<const char*, 4> kCritterAnims{"move_front", "move_back", "idle_front",
                                                   "idle_back"};
constexpr std::array<const char*, static_cast<std::size_t>(Fx::Count)> kFxNames{
    "smoke", "ripple", "sparkle", "raindrop", "leaf", "clear", "petal", "snowflake", "produce"};

// Collects prefix/f0, f1, ... until the first gap, each frame in its `suffix` look (a season)
// where there is one. With a placeholder, a missing f0 is logged and replaced; without one the
// set stays empty (optional layers).
FrameSet frames(Atlas& atlas, const std::string& prefix, std::optional<SpriteId> placeholder,
                std::string_view suffix = {}) {
    FrameSet set;
    for (int f = 0;; ++f) {
        const std::string key = std::format("{}/f{}", prefix, f);
        const auto id = atlas.find(key);
        if (!id) break;
        const auto look = suffix.empty() ? std::nullopt : atlas.find(key + std::string(suffix));
        set.frames.push_back(look.value_or(*id));
    }
    if (set.frames.empty() && placeholder)
        set.frames.push_back(atlas.resolve(prefix + "/f0", *placeholder));
    return set;
}

// A growth stage's frames: stage and season, stage, season, plain, frame by frame.
FrameSet stageFrames(Atlas& atlas, const std::string& prefix, int stage, std::string_view suffix,
                     const FrameSet& plain) {
    FrameSet set;
    for (std::size_t f = 0; f < plain.frames.size(); ++f) {
        const std::string key = std::format("{}/g{}/f{}", prefix, stage, f);
        auto id = suffix.empty() ? std::nullopt : atlas.find(key + std::string(suffix));
        if (!id) id = atlas.find(key);
        set.frames.push_back(id.value_or(plain.frames[f]));
    }
    return set;
}

std::string variantKey(const ItemDef& def, int v) {
    return def.layout == Layout::Connect ? std::format("m{}", v) : std::format("r{}", v);
}

int variantSlots(const ItemDef& def) {
    return def.layout == Layout::Connect ? 16 : def.count;
}

} // namespace

SpriteTables buildSpriteTables(Atlas& atlas, const Catalog& cat, int season) {
    SpriteTables t;
    const std::string suffix =
        season >= 0 ? "@" + cat.seasons[static_cast<std::size_t>(season)].id : std::string{};
    float shadowPeak = 0.0f;
    for (const auto& terr : cat.terrain) {
        std::vector<SpriteId> base;
        std::array<FrameSet, 16> overlay;
        if (terr.base) {
            for (int v = 0; v < terr.variants; ++v) {
                const std::string key = std::format("terrain/{}/v{}", terr.id, v);
                const auto look = suffix.empty() ? std::nullopt : atlas.find(key + suffix);
                base.push_back(look ? *look : atlas.resolve(key, atlas.placeholderTile()));
            }
        } else {
            for (int m = 0; m < 16; ++m)
                overlay[static_cast<std::size_t>(m)] =
                    frames(atlas, std::format("terrain/{}/m{}", terr.id, m),
                           atlas.placeholderTile(), suffix);
        }
        t.terrainBase.push_back(std::move(base));
        t.terrainOverlay.push_back(std::move(overlay));
    }

    for (const auto& def : cat.items) {
        ItemSprites s;
        for (int v = 0; v < variantSlots(def); ++v) {
            const std::string prefix = std::format("item/{}/", def.id);
            const std::string vk = variantKey(def, v);
            s.base.push_back(frames(atlas, prefix + "base/" + vk, atlas.placeholderBox(), suffix));
            // Shadows are optional (flat things have none).
            FrameSet shadow = frames(atlas, prefix + "shadow/" + vk, std::nullopt, suffix);
            for (const SpriteId f : shadow.frames)
                shadowPeak = std::max(shadowPeak, atlas.normalizeAlpha(f));
            s.shadow.push_back(std::move(shadow));
            FrameSet glow =
                def.glow ? frames(atlas, prefix + "glow/" + vk, std::nullopt, suffix) : FrameSet{};
            if (def.glow && glow.empty()) atlas.reportMissing(prefix + "glow/" + vk + "/f0");
            s.light.push_back(glow.empty() ? std::nullopt
                                           : atlas.alphaCentroid(glow.frames.front()));
            s.glow.push_back(std::move(glow));
        }
        for (int g = 0; g < def.growth.stages; ++g) {
            std::vector<FrameSet> byVariant;
            for (int v = 0; v < variantSlots(def); ++v)
                byVariant.push_back(
                    stageFrames(atlas, std::format("item/{}/base/{}", def.id, variantKey(def, v)),
                                g, suffix, s.base[static_cast<std::size_t>(v)]));
            s.stages.push_back(std::move(byVariant));
        }
        t.items.push_back(std::move(s));
    }

    for (const auto& v : cat.visitors) {
        std::array<FrameSet, 4> anims;
        for (std::size_t a = 0; a < 4; ++a)
            anims[a] = frames(atlas, std::format("critter/{}/{}", v.id, kCritterAnims[a]),
                              atlas.placeholderBox());
        t.critters.push_back(std::move(anims));
    }
    for (std::size_t f = 0; f < t.fx.size(); ++f)
        t.fx[f] = frames(atlas, std::format("fx/{}", kFxNames[f]), atlas.placeholderBox());
    t.cliffSE = atlas.resolve("edge/cliff_se", atlas.placeholderEdgeSE());
    t.cliffSW = atlas.resolve("edge/cliff_sw", atlas.placeholderEdgeSW());
    t.tileOk = atlas.resolve("ui/tile_ok", atlas.placeholderTile());
    t.tileBad = atlas.resolve("ui/tile_bad", atlas.placeholderTile());
    t.tileArea = atlas.resolve("ui/tile_area", atlas.placeholderTile());
    for (int v = 0;; ++v) {
        const auto id = atlas.find(std::format("wild/thicket/v{}", v));
        if (!id) break;
        t.thickets.push_back(*id);
    }
    if (t.thickets.empty()) atlas.reportMissing("wild/thicket/v0");
    t.fallSE = frames(atlas, "edge/fall_se", atlas.placeholderEdgeSE());
    t.fallSW = frames(atlas, "edge/fall_sw", atlas.placeholderEdgeSW());
    t.placeholder = atlas.placeholderBox();
    if (shadowPeak > 0.0f) t.shadowOpacity = shadowPeak;

    // How far ground sprites reach beyond their tile's diamond, for sizing cached ground chunks.
    const auto extend = [&](SpriteId id) {
        const Sprite& sp = atlas.sprite(id);
        t.groundReach.left = std::max(t.groundReach.left, sp.ox - atlas.iso().hw);
        t.groundReach.right = std::max(t.groundReach.right, sp.w - sp.ox - atlas.iso().hw);
        t.groundReach.top = std::max(t.groundReach.top, sp.oy);
        t.groundReach.bottom = std::max(t.groundReach.bottom, sp.h - sp.oy - atlas.iso().tileH());
    };
    for (const auto& base : t.terrainBase)
        for (const SpriteId id : base) extend(id);
    for (const auto& overlay : t.terrainOverlay)
        for (const auto& set : overlay)
            for (const SpriteId id : set.frames) extend(id);
    extend(t.cliffSE);
    extend(t.cliffSW);
    for (const SpriteId id : t.thickets) extend(id);
    for (const SpriteId id : t.fallSE.frames) extend(id);
    for (const SpriteId id : t.fallSW.frames) extend(id);
    return t;
}

SpriteId thumbnail(const SpriteTables& t, Thumb kind, int index) {
    const auto i = static_cast<std::size_t>(index);
    const auto first = [&](const auto& frames) {
        return frames.empty() ? t.placeholder : frames.front();
    };
    if (index < 0) return t.placeholder;
    switch (kind) {
    case Thumb::Terrain:
        if (i >= t.terrainBase.size() || i >= t.terrainOverlay.size()) break;
        // Base terrain has variants; overlay terrain shows its fully surrounded piece.
        return t.terrainBase[i].empty() ? first(t.terrainOverlay[i][15].frames)
                                        : t.terrainBase[i].front();
    case Thumb::Item:
        if (i >= t.items.size() || t.items[i].base.empty()) break;
        return first(t.items[i].base.front().frames);
    case Thumb::Visitor:
        if (i >= t.critters.size()) break;
        return first(t.critters[i][static_cast<std::size_t>(CritterAnim::IdleFront)].frames);
    }
    return t.placeholder;
}

std::vector<std::string> requiredSpriteKeys(const Catalog& cat) {
    std::vector<std::string> keys;
    for (const auto& terr : cat.terrain) {
        if (terr.base) {
            for (int v = 0; v < terr.variants; ++v)
                keys.push_back(std::format("terrain/{}/v{}", terr.id, v));
        } else {
            for (int m = 0; m < 16; ++m)
                keys.push_back(std::format("terrain/{}/m{}/f0", terr.id, m));
        }
    }
    for (const auto& def : cat.items) {
        for (int v = 0; v < variantSlots(def); ++v) {
            const std::string vk = variantKey(def, v);
            keys.push_back(std::format("item/{}/base/{}/f0", def.id, vk));
            if (def.glow) keys.push_back(std::format("item/{}/glow/{}/f0", def.id, vk));
        }
    }
    for (const auto& v : cat.visitors)
        for (const char* a : kCritterAnims)
            keys.push_back(std::format("critter/{}/{}/f0", v.id, a));
    for (const char* f : kFxNames) keys.push_back(std::format("fx/{}/f0", f));
    for (const char* k : {"edge/cliff_se", "edge/cliff_sw", "ui/tile_ok", "ui/tile_bad",
                          "ui/tile_area", "wild/thicket/v0", "edge/fall_se/f0", "edge/fall_sw/f0"})
        keys.emplace_back(k);
    return keys;
}

} // namespace lc
