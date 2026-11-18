cmake_minimum_required(VERSION 3.28)
project(laeticias_corner VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(LC_SANITIZE "Build with AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
option(LC_TESTS "Build the test suite" ON)

include(cmake/ProjectOptions.cmake)

find_package(SDL3 3.4 REQUIRED CONFIG)
find_package(nlohmann_json 3.11 REQUIRED)

add_subdirectory(third_party)

# Pure game logic: no SDL allowed (enforced by not linking it).
add_library(lc_core STATIC
  src/core/actor_data.cpp
  src/core/actors.cpp
  src/core/catalog.cpp
  src/core/clock.cpp
  src/core/condition.cpp
  src/core/edit.cpp
  src/core/events.cpp
  src/core/growth.cpp
  src/core/land.cpp
  src/core/notes.cpp
  src/core/path.cpp
  src/core/perf.cpp
  src/core/progress.cpp
  src/core/progression.cpp
  src/core/save.cpp
  src/core/speech.cpp
  src/core/starter.cpp
  src/core/visitors.cpp
  src/core/weather.cpp
  src/core/world.cpp
  src/core/worlds.cpp
  src/core/writer.cpp
)
target_include_directories(lc_core PUBLIC src)
target_link_libraries(lc_core PUBLIC nlohmann_json::nlohmann_json)
lc_project_target(lc_core)

# SDL-facing engine pieces, split from main() so tests can link them.
add_library(lc_engine STATIC
  src/app/app.cpp
  src/app/options.cpp
  src/app/script.cpp
  src/app/app_script.cpp
  src/app/app_bench.cpp
  src/app/app_benchmark.cpp
  src/app/app_build.cpp
  src/app/app_front.cpp
  src/app/app_photo.cpp
  src/app/app_life.cpp
  src/app/app_perf.cpp
  src/app/window_state.cpp
  src/audio/mixer.cpp
  src/audio/decode.cpp
  src/audio/wav.cpp
  src/render/atlas.cpp
  src/platform/batch.cpp
  src/render/blur.cpp
  src/render/camera.cpp
  src/render/depth.cpp
  src/render/draw.cpp
  src/render/fx.cpp
  src/render/ground.cpp
  src/render/scene.cpp
  src/render/sprites.cpp
  src/ui/font.cpp
  src/ui/hud.cpp
  src/ui/menus.cpp
  src/ui/painter.cpp
  src/ui/profiler.cpp
)
target_link_libraries(lc_engine PUBLIC lc_core SDL3::SDL3 PRIVATE lc_stb)
target_compile_definitions(lc_engine PUBLIC LC_SOURCE_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets")
lc_project_target(lc_engine)

add_executable(laeticias-corner src/app/main.cpp)
target_link_libraries(laeticias-corner PRIVATE lc_engine)
lc_project_target(laeticias-corner)

if(LC_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

# --- World data runtime (src/world/) -------------------------------------------------------------
# Loads, validates and serves the prebuilt world (layers, graphs, regions, set catalogs, atlas
# manifests, geometry). Pure logic like lc_core: no SDL.
add_library(lc_world STATIC
  src/world/atlas_pages.cpp
  src/world/content.cpp
  src/world/digest.cpp
  src/world/geometry.cpp
  src/world/graph_file.cpp
  src/world/json_util.cpp
  src/world/layer_file.cpp
  src/world/loader.cpp
  src/world/region_file.cpp
  src/world/road_graph.cpp
  src/world/set_catalog.cpp
  src/world/world_file.cpp
  src/world/world_map.cpp
)
target_link_libraries(lc_world PUBLIC lc_core)
lc_project_target(lc_world)

# City life (src/life/): the regions' people, chains, events, figures and tokens simulated over
# the world. Pure logic: no SDL.
add_library(lc_life STATIC
  src/life/chains.cpp
  src/life/city.cpp
  src/life/data.cpp
  src/life/paths.cpp
  src/life/report.cpp
  src/life/session.cpp
)
target_link_libraries(lc_life PUBLIC lc_world)
lc_project_target(lc_life)

# Debugging aid for city life: summary, problems, chains (the worldgen cross-check), dumps, the
# city bench and the roaming soak.
add_executable(lifeinfo src/life/lifeinfo_main.cpp)
target_link_libraries(lifeinfo PRIVATE lc_life)
target_compile_definitions(lifeinfo PRIVATE LC_LIFEINFO_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets")
lc_project_target(lifeinfo)

# Debugging aid for world builders and QA: summary, validation, region and tile dumps, digest.
add_executable(worldinfo src/world/worldinfo_main.cpp)
target_link_libraries(worldinfo PRIVATE lc_world)
target_compile_definitions(worldinfo PRIVATE LC_WORLDINFO_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets")
lc_project_target(worldinfo)

if(LC_TESTS)
  add_executable(lc_world_tests
    tests/world_main.cpp
    tests/world_support.cpp
    tests/world_formats.cpp
    tests/world_map.cpp
    tests/world_real.cpp
  )
  target_link_libraries(lc_world_tests PRIVATE lc_world lc_doctest)
  target_compile_definitions(lc_world_tests PRIVATE
    LC_WORLD_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets"
    LC_WORLD_FIXTURES_DIR="${CMAKE_SOURCE_DIR}/tests/fixtures/world")
  lc_project_target(lc_world_tests)
  # Same doctest/libstdc++ <ciso646> warning as lc_tests (see tests/CMakeLists.txt).
  target_compile_options(lc_world_tests PRIVATE $<$<CXX_COMPILER_ID:Clang>:-Wno-\#warnings>)
  add_test(NAME world_unit COMMAND lc_world_tests "--test-case-exclude=perf:*,real world: the digest*")
  # The digest against tools/worldgen's own reader, made at test time from today's data (skipped
  # without worldgen's virtualenv).
  add_test(NAME world_digest COMMAND ${CMAKE_COMMAND}
    -DPY=${CMAKE_SOURCE_DIR}/tools/worldgen/.venv/bin/python
    -DSCRIPT=${CMAKE_SOURCE_DIR}/tests/world_tools/world_digest.py
    -DOUT=${CMAKE_CURRENT_BINARY_DIR}/world_digest.json
    -DTESTS=$<TARGET_FILE:lc_world_tests>
    -DENV=LC_WORLD_DIGEST
    "-DCASE=real world: the digest*"
    -P ${CMAKE_SOURCE_DIR}/tests/world_tools/digest_check.cmake)
  set_tests_properties(world_digest PROPERTIES SKIP_RETURN_CODE 77)
  # Load time, memory and query throughput on the committed world; budgets assert in optimised
  # builds only (sanitizer builds report the figures).
  add_test(NAME world_perf COMMAND lc_world_tests --test-case=perf:*)
  add_test(NAME worldinfo_summary COMMAND worldinfo summary)

  add_executable(lc_life_tests tests/world_main.cpp tests/world_support.cpp tests/life_tests.cpp)
  target_link_libraries(lc_life_tests PRIVATE lc_life lc_doctest)
  target_compile_definitions(lc_life_tests PRIVATE
    LC_WORLD_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets"
    LC_WORLD_FIXTURES_DIR="${CMAKE_SOURCE_DIR}/tests/fixtures/world")
  lc_project_target(lc_life_tests)
  target_compile_options(lc_life_tests PRIVATE $<$<CXX_COMPILER_ID:Clang>:-Wno-\#warnings>)
  add_test(NAME life_unit COMMAND lc_life_tests "--test-case-exclude=city:*,*lifesim*")
  add_test(NAME life_city COMMAND lc_life_tests "--test-case=city:*")
  # The chains against tools/worldgen's own simulator, made at test time from today's data
  # (skipped without worldgen's virtualenv).
  add_test(NAME life_chains COMMAND ${CMAKE_COMMAND}
    -DPY=${CMAKE_SOURCE_DIR}/tools/worldgen/.venv/bin/python
    -DSCRIPT=${CMAKE_SOURCE_DIR}/tests/world_tools/life_chains.py
    -DOUT=${CMAKE_CURRENT_BINARY_DIR}/life_chains.json
    -DTESTS=$<TARGET_FILE:lc_life_tests>
    -DENV=LC_LIFE_CHAINS
    "-DCASE=*lifesim*"
    -P ${CMAKE_SOURCE_DIR}/tests/world_tools/digest_check.cmake)
  set_tests_properties(life_chains PROPERTIES SKIP_RETURN_CODE 77)
  add_test(NAME lifeinfo_summary COMMAND lifeinfo summary)
endif()
