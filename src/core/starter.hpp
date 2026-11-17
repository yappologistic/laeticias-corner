#pragma once
// The home region a brand-new world starts with (catalog `starter`), its later stages still wild.

#include "core/catalog.hpp"
#include "core/world.hpp"

namespace lc {

// Entries that no longer fit are skipped.
[[nodiscard]] World makeStarterWorld(const Catalog& cat);

} // namespace lc
