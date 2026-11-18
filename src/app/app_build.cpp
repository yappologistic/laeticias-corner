// Building: the tools under the pointer (place, paint, remove, move), the eyedropper, straight
// lines of one-tile pieces, paint brushes and rectangles, area removal, and what each previews
// (docs/design/living-corner.md R11). Every stroke, line, area or move is one undo step.

#include "app/app_impl.hpp"
#include "ui/strings.hpp"

#include <algorithm>
#include <cmath>
#include <format>

namespace lc {
namespace {

// 4-connected walk from a (exclusive) to b (inclusive), so drags never leave diagonal gaps.
template <typename F>
void walkLine(TilePos a, TilePos b, F&& visit) {
    const int tx = b.x - a.x;
    const int ty = b.y - a.y;
    TilePos c = a;
    while (c != b) {
        const int rx = b.x - c.x;
        const int ry = b.y - c.y;
        if (std::abs(rx) * std::abs(ty) >= std::abs(ry) * std::abs(tx) && rx != 0)
            c.x += rx > 0 ? 1 : -1;
        else
            c.y += ry > 0 ? 1 : -1;
        visit(c);
    }
}

constexpr std::string_view kPickSfx = "sfx/pick.wav";

} // namespace

std::string_view placeWarning(PlaceResult r) {
    switch (r) {
    case PlaceResult::Ok: return {};
    case PlaceResult::OutOfBounds: return strings::kWarnEdge;
    case PlaceResult::Wild: return strings::kWarnWild;
    case PlaceResult::Occupied: return strings::kWarnOccupied;
    case PlaceResult::NeedsLand: return strings::kWarnLand;
    case PlaceResult::NeedsWater: return strings::kWarnWater;
    }
    return {};
}

void App::warn(std::string_view text) {
    warning_ = text;
    warnTime_ = tuning::kWarnSeconds;
}

Item App::ghostItem(TilePos hover) const {
    const auto& def = cat_.items[static_cast<std::size_t>(selection_)];
    const Footprint fp = footprintOf(def, variant_);
    // Centre multi-tile footprints on the cursor.
    Item it =
        makeItem(cat_, selection_, variant_, {hover.x - (fp.w - 1) / 2, hover.y - (fp.h - 1) / 2});
    if (carry_) {
        // A piece being moved keeps how far it has grown.
        it.stage = carry_->stage;
        it.growth = carry_->growth;
    }
    return it;
}

TileRect App::shapeRect() const {
    const TilePos b = hover_.value_or(anchor_);
    return TileRect{std::min(anchor_.x, b.x), std::min(anchor_.y, b.y),
                    std::max(anchor_.x, b.x) + 1, std::max(anchor_.y, b.y) + 1}
        .clipped(world_.bounds());
}

void App::shapeTiles(std::vector<TilePos>& out) const {
    out.clear();
    const TilePos b = hover_.value_or(anchor_);
    if (shape_ == Shape::Line) {
        // Along x or along y, whichever the drag covers more.
        const bool alongX = std::abs(b.x - anchor_.x) >= std::abs(b.y - anchor_.y);
        const int n = alongX ? b.x - anchor_.x : b.y - anchor_.y;
        const int step = n < 0 ? -1 : 1;
        for (int k = 0; k != n + step; k += step)
            out.push_back(alongX ? TilePos{anchor_.x + k, anchor_.y}
                                 : TilePos{anchor_.x, anchor_.y + k});
        return;
    }
    const TileRect r = shapeRect();
    for (int y = r.y0; y < r.y1; ++y)
        for (int x = r.x0; x < r.x1; ++x) out.push_back({x, y});
}

void App::brushTiles(TilePos centre, std::vector<TilePos>& out) const {
    out.clear();
    const int half = brush_ / 2;
    for (int y = centre.y - half; y <= centre.y + half; ++y)
        for (int x = centre.x - half; x <= centre.x + half; ++x)
            if (world_.inBounds({x, y})) out.push_back({x, y});
}

const std::vector<Ghost>& App::buildGhosts() {
    ghosts_.clear();
    if (!hover_ || photo_ || drag_ == Drag::Pan) return ghosts_;
    const TilePos h = *hover_;
    const auto tile = [&](TilePos t, bool valid) {
        Ghost g;
        g.mode = Ghost::Mode::Tile;
        g.tile = t;
        g.valid = valid;
        ghosts_.push_back(g);
    };
    if (pipette_) {
        tile(h, true);
        return ghosts_;
    }
    switch (tool_) {
    case Tool::None:
        // An empty hand over wild land shows it cannot be used yet.
        if (world_.isWild(h)) tile(h, false);
        break;
    case Tool::Place:
        if (shape_ == Shape::Line) {
            shapeTiles(scratchTiles_);
            for (const TilePos t : scratchTiles_) {
                Ghost g;
                g.mode = Ghost::Mode::Item;
                g.item = ghostItem(t);
                g.valid = canPlace(world_, cat_, g.item) == PlaceResult::Ok;
                ghosts_.push_back(g);
            }
            break;
        }
        [[fallthrough]];
    case Tool::Move:
        if (tool_ == Tool::Move && !carry_) {
            // What a click would pick up.
            if (const Item* it = world_.itemAt(h))
                for (int y = it->pos.y; y < it->pos.y + it->h; ++y)
                    for (int x = it->pos.x; x < it->pos.x + it->w; ++x) tile({x, y}, true);
            break;
        }
        {
            Ghost g;
            g.mode = Ghost::Mode::Item;
            g.item = ghostItem(h);
            g.valid = canPlace(world_, cat_, g.item) == PlaceResult::Ok;
            ghosts_.push_back(g);
        }
        break;
    case Tool::Paint:
        if (shape_ == Shape::Rect)
            shapeTiles(scratchTiles_);
        else
            brushTiles(h, scratchTiles_);
        for (const TilePos t : scratchTiles_) {
            const auto r = canPaint(world_, cat_, t, selection_);
            tile(t, r == PaintResult::Ok || r == PaintResult::Unchanged);
        }
        break;
    case Tool::Remove:
        if (shape_ == Shape::Rect) {
            // Every item whose footprint touches the rectangle.
            const TileRect r = shapeRect();
            world_.forEachItemIn(r, [&](const Item& it) {
                Ghost g;
                g.mode = Ghost::Mode::Remove;
                g.tile = it.pos;
                ghosts_.push_back(g);
            });
            for (int y = r.y0; y < r.y1; ++y)
                for (int x = r.x0; x < r.x1; ++x)
                    if (world_.itemAt({x, y}) == nullptr) tile({x, y}, false);
            break;
        }
        {
            Ghost g;
            g.mode = Ghost::Mode::Remove;
            g.tile = h;
            g.valid = world_.itemAt(h) != nullptr;
            ghosts_.push_back(g);
        }
        break;
    }
    return ghosts_;
}

std::string_view App::toolHint() const {
    if (pipette_) return strings::kHintPipette;
    switch (tool_) {
    case Tool::None:
        // The first time anything ripens, say what to do with it.
        return anyRipe_ && progress_.harvests == 0 ? strings::kHintRipe : std::string_view{};
    case Tool::Place: {
        const auto& def = cat_.items[static_cast<std::size_t>(selection_)];
        const bool row = oneTile(def);
        if (def.count <= 1) return row ? strings::kHintPlaceRow : strings::kHintPlaceFixed;
        if (def.layout == Layout::Rotate)
            return row ? strings::kHintPlaceRowRotate : strings::kHintPlace;
        return row ? strings::kHintPlaceRowVariant : strings::kHintPlaceVariant;
    }
    case Tool::Paint:
        toolHintText_ =
            std::vformat(strings::kHintPaintBrush, std::make_format_args(brush_, brush_));
        return toolHintText_;
    case Tool::Remove: return strings::kHintRemove;
    case Tool::Move: return carry_ ? strings::kHintMoveCarry : strings::kHintMovePick;
    }
    return {};
}

void App::eyedrop(TilePos t) {
    // A one-shot copy of what is under the pointer; it never touches the undo history.
    pipette_ = false;
    if (const Item* it = world_.itemAt(t)) {
        if (progress_.items[it->type] == 0) {
            warn(strings::kWarnLocked);
            return;
        }
        const int variant = cat_.items[it->type].layout == Layout::Connect ? 0 : it->variant;
        setTool(Tool::Place, it->type);
        variant_ = variant;
    } else if (world_.hasGround(t) && !world_.isWild(t)) {
        const int terrain = world_.terrainAt(t);
        if (progress_.terrain[static_cast<std::size_t>(terrain)] == 0) {
            warn(strings::kWarnLocked);
            return;
        }
        setTool(Tool::Paint, terrain);
    } else {
        return;
    }
    play(sfx::kClick, tuning::kUiSfxLevel);
}

void App::pickUp(TilePos t) {
    const Item* it = world_.itemAt(t);
    if (it == nullptr) {
        warn(strings::kWarnNothingToPick);
        return;
    }
    // The move is one undo step: the removal and the placing share a group, and putting the
    // piece back where it was leaves no step at all (abort).
    const Item picked = *it;
    editor_.begin();
    (void)editor_.remove(world_, t);
    carry_ = picked;
    selection_ = picked.type;
    variant_ = cat_.items[picked.type].layout == Layout::Connect ? 0 : picked.variant;
    disturbed(picked.rect(), -2, false);
    play(kPickSfx, tuning::kSfxLevel, true);
}

void App::putDown(TilePos t) {
    const Item item = ghostItem(t);
    if (editor_.place(world_, cat_, item) != PlaceResult::Ok) {
        play(sfx::kInvalid);
        return;
    }
    editor_.commit();
    carry_.reset();
    scene_->onPlaced(item, rng_);
    disturbed(item.rect(), item.type, false);
    play(cat_.items[item.type].sound, tuning::kSfxLevel, true);
    markDirty();
}

void App::cancelMove() {
    if (!carry_) return;
    (void)editor_.abort(world_);
    carry_.reset();
}

void App::finishShape() {
    // A line, rectangle or area is laid down whole on release, as one undo step.
    const Shape shape = shape_;
    shapeTiles(scratchTiles_); // while the shape is still known
    shape_ = Shape::None;
    editor_.begin();
    int done = 0;
    if (tool_ == Tool::Remove) {
        areaItems_.clear();
        world_.forEachItemIn(shapeRect(), [&](const Item& it) { areaItems_.push_back(it.pos); });
        for (const TilePos p : areaItems_) {
            const Item* it = world_.itemAt(p);
            if (it == nullptr) continue;
            const Item removed = *it;
            (void)editor_.remove(world_, p);
            scene_->onRemoved(removed);
            disturbed(removed.rect(), -2, false);
            ++done;
        }
        if (done > 0) play(sfx::kRemove, tuning::kSfxLevel, true);
    } else {
        for (const TilePos t : scratchTiles_) {
            if (shape == Shape::Line) {
                const Item item = ghostItem(t);
                const bool fresh = world_.itemCount(item.type) == 0;
                if (editor_.place(world_, cat_, item) != PlaceResult::Ok) continue;
                scene_->onPlaced(item, rng_);
                disturbed(item.rect(), item.type, fresh);
            } else if (editor_.paint(world_, cat_, t, selection_) == PaintResult::Ok) {
                if (selection_ == cat_.waterTerrain)
                    disturbed({t.x, t.y, t.x + 1, t.y + 1}, -1, false);
            } else {
                continue;
            }
            ++done;
        }
        if (done > 0) {
            if (shape == Shape::Line) {
                play(cat_.items[static_cast<std::size_t>(selection_)].sound, tuning::kSfxLevel,
                     true);
                // A line plays a little run of the phrase as it lands.
                pendingNotes_ = std::min(done, tuning::kLineNotes);
            } else {
                const auto& snd = cat_.terrain[static_cast<std::size_t>(selection_)].sound;
                play(snd.empty() ? sfx::kPaint : std::string_view(snd), tuning::kSfxLevel, true);
                playNote();
            }
        }
    }
    editor_.commit();
    if (done > 0)
        markDirty();
    else
        play(sfx::kInvalid);
}

void App::applyTool(TilePos t, bool first) {
    World& w = world_;
    switch (tool_) {
    case Tool::None:
    case Tool::Move: break;
    case Tool::Place: {
        const Item item = ghostItem(t);
        const bool fresh = w.itemCount(item.type) == 0;
        const auto r = editor_.place(w, cat_, item);
        if (r == PlaceResult::Ok) {
            scene_->onPlaced(item, rng_);
            disturbed(item.rect(), item.type, fresh);
            play(cat_.items[item.type].sound, tuning::kSfxLevel, true);
            playNote();
            markDirty();
        } else if (first) {
            play(sfx::kInvalid);
        }
        break;
    }
    case Tool::Paint: {
        if (first) strokeTiles_ = 0;
        // The brush paints a square around the pointer; blocked tiles inside it are skipped.
        brushTiles(t, scratchTiles_);
        bool painted = false;
        PaintResult centre = PaintResult::Unchanged;
        for (const TilePos p : scratchTiles_) {
            const auto r = editor_.paint(w, cat_, p, selection_);
            if (p == t) centre = r;
            if (r != PaintResult::Ok) continue;
            painted = true;
            if (selection_ == cat_.waterTerrain) disturbed({p.x, p.y, p.x + 1, p.y + 1}, -1, false);
        }
        if (painted) {
            // A note when a stroke starts and every few tiles after.
            if (strokeTiles_++ % tuning::kPaintNoteEvery == 0) playNote();
            if (simTime_ - lastPaintSound_ > tuning::kPaintSoundGap) {
                const auto& snd = cat_.terrain[static_cast<std::size_t>(selection_)].sound;
                play(snd.empty() ? sfx::kPaint : std::string_view(snd), tuning::kSfxLevel, true);
                lastPaintSound_ = simTime_;
            }
            markDirty();
        } else if (centre == PaintResult::BlockedByItem || centre == PaintResult::Wild) {
            if (first) play(sfx::kInvalid);
            warn(centre == PaintResult::Wild ? strings::kWarnWild : strings::kWarnPaint);
        }
        break;
    }
    case Tool::Remove: {
        if (const Item* it = w.itemAt(t)) {
            const Item removed = *it;
            (void)editor_.remove(w, t);
            scene_->onRemoved(removed);
            disturbed(removed.rect(), -2, false);
            play(sfx::kRemove, tuning::kSfxLevel, true);
            markDirty();
        } else if (first) {
            warn(strings::kWarnNothing);
        }
        break;
    }
    }
}

void App::worldInput() {
    const bool uiOwns = hud_.wantsMouse() && drag_ != Drag::Tool;
    hover_.reset();
    if (mouseInside_ && !uiOwns && !photo_) {
        const TilePos t = cat_.iso().tileAt(view_.screenToWorld(mouse_, screen()));
        if (world_.hasGround(t)) hover_ = t;
    }
    // Whole notches step the zoom; small deltas (touchpads, smooth wheels) add up to a step.
    if (uiOwns) wheelAcc_ = 0;
    for (; wheelAcc_ >= 1.0f; wheelAcc_ -= 1.0f) zoomBy(1, mouse_);
    for (; wheelAcc_ <= -1.0f; wheelAcc_ += 1.0f) zoomBy(-1, mouse_);
    wheel_ = 0;
    // A middle click (no drag) copies what is under the pointer.
    if (std::exchange(middleClick_, false) && hover_ && !photo_) eyedrop(*hover_);

    if (panPending_) {
        panPending_ = false;
        if (!uiOwns && drag_ == Drag::None) drag_ = Drag::Pan;
    }
    const bool alt = (mods_ & SDL_KMOD_ALT) != 0;
    const bool shift = (mods_ & SDL_KMOD_SHIFT) != 0;
    if (leftPressed_ && !uiOwns && drag_ == Drag::None) {
        if ((pipette_ || alt) && hover_ && !photo_) {
            eyedrop(*hover_);
        } else if (tool_ == Tool::None || photo_) {
            drag_ = Drag::Pan;
            lastPan_ = pressStart_ = mouse_;
        } else if (const auto t = hover_) {
            if (tool_ == Tool::Move) {
                if (carry_)
                    putDown(*t);
                else
                    pickUp(*t);
            } else if (shift && (tool_ == Tool::Paint || tool_ == Tool::Remove ||
                                 oneTile(cat_.items[static_cast<std::size_t>(selection_)]))) {
                // Shift starts a straight line (one-tile pieces) or a rectangle (paint, remove).
                drag_ = Drag::Tool;
                shape_ = tool_ == Tool::Place ? Shape::Line : Shape::Rect;
                anchor_ = *t;
            } else {
                drag_ = Drag::Tool;
                editor_.begin();
                applyTool(*t, true);
                lastTile_ = *t;
            }
        }
    }
    if (drag_ == Drag::Tool && shape_ == Shape::None && hover_ && *hover_ != lastTile_) {
        const bool repeat =
            tool_ != Tool::Place || oneTile(cat_.items[static_cast<std::size_t>(selection_)]);
        if (repeat) walkLine(lastTile_, *hover_, [&](TilePos t) { applyTool(t, false); });
        lastTile_ = *hover_;
    }
    if (leftReleased_) {
        if (drag_ == Drag::Tool) {
            if (shape_ != Shape::None)
                finishShape();
            else
                editor_.commit();
        }
        // A click (not a drag) takes the photo in photo mode, or picks a ripe bed.
        const bool click = drag_ == Drag::Pan && !rightDown_ &&
                           std::hypot(mouse_.x - pressStart_.x, mouse_.y - pressStart_.y) <
                               tuning::kClickSlop * density_;
        if (click && photo_) {
            capturePending_ = true;
        } else if (click && tool_ == Tool::None) {
            // An actor under the pointer is petted (she answers); else a ripe bed is picked;
            // else an item with a sound of its own plays it (the well's plip).
            if (const auto who = actorUnder(mouse_)) {
                (void)actors_.pet(*who);
            } else if (const auto t = hover_; t && !pick(*t)) {
                if (const Item* it = world_.itemAt(*t);
                    it && !cat_.items[it->type].clickSound.empty())
                    playAt(cat_.items[it->type].clickSound, tuning::kSfxLevel,
                           {static_cast<float>(t->x) + 0.5f, static_cast<float>(t->y) + 0.5f});
            }
        }
        if (drag_ != Drag::None && !rightDown_) drag_ = Drag::None;
    }
}

} // namespace lc
