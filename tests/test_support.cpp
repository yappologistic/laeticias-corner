#include "test_support.hpp"

#include <doctest.h>

#include <cstdlib>

namespace lc::test {

std::filesystem::path assetsDir() {
    return LC_TEST_ASSETS_DIR;
}

const std::string& catalogText() {
    static const std::string text = [] {
        auto t = readTextFile(assetsDir() / "catalog.json");
        if (!t) {
            FAIL(t.error());
        }
        return *t;
    }();
    return text;
}

const Catalog& catalog() {
    static const Catalog cat = [] {
        auto c = parseCatalog(catalogText());
        if (!c) {
            FAIL(c.error());
        }
        return *c;
    }();
    return cat;
}

std::filesystem::path tempDir(const std::string& name) {
    const auto dir = std::filesystem::path(LC_TEST_SCRATCH_DIR) / name;
    std::filesystem::remove_all(dir);
    std::filesystem::create_directories(dir);
    return dir;
}

} // namespace lc::test
