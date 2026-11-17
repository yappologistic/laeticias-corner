#pragma once
// The small scene a brand-new corner starts with, so first launch is never an empty slab.

#include "core/catalog.hpp"
#include "core/world.hpp"

namespace lc {

// Entries naming ids the catalog lacks, or that no longer fit, are skipped.
[[nodiscard]] World makeStarterWorld(const Catalog& cat);

} // namespace lc
