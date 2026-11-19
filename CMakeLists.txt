cmake_minimum_required(VERSION 3.28)
project(laeticias_corner VERSION 0.1.0 LANGUAGES C CXX)
# The pre-release suffix (empty for a final release): the one place it is written. The release
# tag is "v" followed by LC_VERSION.
set(LC_VERSION_SUFFIX "-prealpha.1")
set(LC_VERSION "${PROJECT_VERSION}${LC_VERSION_SUFFIX}")
# The system the build is for, as the release archives name it.
string(TOLOWER "${CMAKE_SYSTEM_NAME}" LC_PLATFORM)
if(WIN32 AND CMAKE_SIZEOF_VOID_P EQUAL 8)
  string(APPEND LC_PLATFORM "-x64")
else()
  string(APPEND LC_PLATFORM "-${CMAKE_SYSTEM_PROCESSOR}")
endif()
# The reverse-domain application id: SDL's app metadata (Wayland's app_id, X11's WM_CLASS) and
# the Linux package's desktop file and icon are named by it, so desktops match the running
# window to its launcher. Underscore, not hyphen: desktop file ids follow D-Bus name rules.
set(LC_APP_ID "io.github.yappologistic.laeticias_corner")
# For the release workflow: the archive's name without reading this file.
file(WRITE "${CMAKE_BINARY_DIR}/version.txt" "${LC_VERSION}\n")

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(LC_SANITIZE "Build with AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
option(LC_TESTS "Build the test suite" ON)
# Release packages carry no C++ runtime to install: libstdc++ and libgcc (and on Windows
# winpthreads) go into each binary.
option(LC_STATIC_RUNTIME "Link the C++ runtime statically (release packages)" OFF)

include(cmake/ProjectOptions.cmake)

if(LC_STATIC_RUNTIME)
  # Before the dependencies, so a fetched SDL needs no runtime DLL of the compiler either.
  if(MINGW)
    add_link_options(-static)
  else()
    add_link_options(-static-libstdc++ -static-libgcc)
  endif()
endif()

# System packages when they are installed (the developer's usual case); otherwise the pinned
# releases below, checked against their SHA-256, are downloaded and built with the project. SDL
# is then built as a shared library that the package carries beside the game.
include(FetchContent)
set(SDL_SHARED ON)
set(SDL_STATIC OFF)
set(SDL_TEST_LIBRARY OFF)
set(SDL_EXAMPLES OFF)
set(JSON_BuildTests OFF)
FetchContent_Declare(SDL3
  URL https://github.com/libsdl-org/SDL/releases/download/release-3.4.20/SDL3-3.4.20.tar.gz
  URL_HASH SHA256=f3bb06f55bed9557227a700af2ea62e49497ebdf58037732a731a5fb3ef8581f
  FIND_PACKAGE_ARGS 3.4 CONFIG)
FetchContent_Declare(nlohmann_json
  URL https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
  URL_HASH SHA256=42f6e95cad6ec532fd372391373363b62a14af6d771056dbfc86160e6dfff7aa
  FIND_PACKAGE_ARGS 3.11)
FetchContent_MakeAvailable(SDL3 nlohmann_json)

add_subdirectory(third_party)

# What the pure libraries may ask the system (no SDL).
add_library(lc_platform STATIC src/platform/memory.cpp)
target_include_directories(lc_platform PUBLIC src)
lc_project_target(lc_platform)

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

# The shader path's fragment shaders (src/render/gpu/README.md): GLSL sources and their SPIR-V both
# committed in assets/shaders/, the blobs embedded here, so neither glslc nor a runtime file is
# needed to build or run. `cmake --build --preset release --target shaders` recompiles the blobs
# with glslc (pinned: shaderc 2026.4); the `shaders_fresh` test checks them against the sources.
set(LC_SHADER_DIR ${CMAKE_SOURCE_DIR}/assets/shaders)
set(LC_SHADER_NAMES final bloom_down bloom_up shade clouds packed)
set(LC_SHADER_BLOBS "")
foreach(name ${LC_SHADER_NAMES})
  list(APPEND LC_SHADER_BLOBS ${LC_SHADER_DIR}/${name}.spv)
endforeach()
set(LC_SHADER_CPP ${CMAKE_BINARY_DIR}/generated/gpu_shaders.cpp)
string(JOIN "|" LC_SHADER_ARG ${LC_SHADER_BLOBS})
add_custom_command(OUTPUT ${LC_SHADER_CPP}
  COMMAND ${CMAKE_COMMAND} "-DSHADERS=${LC_SHADER_ARG}" -DOUT=${LC_SHADER_CPP}
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_shaders.cmake
  DEPENDS ${LC_SHADER_BLOBS} ${CMAKE_SOURCE_DIR}/cmake/embed_shaders.cmake
  COMMENT "Embedding the shader path's shaders" VERBATIM)
find_program(LC_GLSLC glslc)
if(LC_GLSLC)
  set(LC_SHADER_COMMANDS "")
  foreach(name ${LC_SHADER_NAMES})
    list(APPEND LC_SHADER_COMMANDS COMMAND ${LC_GLSLC} -O -fshader-stage=frag
         ${LC_SHADER_DIR}/${name}.frag -o ${LC_SHADER_DIR}/${name}.spv)
  endforeach()
  add_custom_target(shaders ${LC_SHADER_COMMANDS}
    COMMENT "Compiling assets/shaders/*.frag to SPIR-V" VERBATIM)
endif()

# SDL-facing engine pieces (render, interface, audio), linked by the world renderer and the app.
add_library(lc_engine STATIC
  ${LC_SHADER_CPP}
  src/audio/mixer.cpp
  src/audio/decode.cpp
  src/audio/wav.cpp
  src/render/atlas.cpp
  src/platform/batch.cpp
  src/platform/process.cpp
  src/render/blur.cpp
  src/render/camera.cpp
  src/render/decks.cpp
  src/render/depth.cpp
  src/render/order.cpp
  src/render/draw.cpp
  src/render/fx.cpp
  src/render/gpu/look.cpp
  src/render/gpu/decoder.cpp
  src/render/gpu/post.cpp
  src/render/gpu/seasons.cpp
  src/render/ground.cpp
  src/render/scene.cpp
  src/render/sprites.cpp
  src/ui/font.cpp
  src/ui/hud.cpp
  src/ui/map_screen.cpp
  src/ui/menus.cpp
  src/ui/painter.cpp
  src/ui/profiler.cpp
)
target_link_libraries(lc_engine PUBLIC lc_core lc_life lc_platform SDL3::SDL3 PRIVATE lc_stb)
target_compile_definitions(lc_engine PUBLIC LC_SOURCE_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets")
lc_project_target(lc_engine)

if(LC_TESTS)
  enable_testing()
endif()

# --- World data runtime (src/world/) -------------------------------------------------------------
# Loads, validates and serves the prebuilt world (layers, graphs, regions, set catalogs, atlas
# manifests, geometry). Pure logic like lc_core: no SDL.
add_library(lc_world STATIC
  src/world/atlas_pages.cpp
  src/world/content.cpp
  src/world/digest.cpp
  src/world/figures.cpp
  src/world/geometry.cpp
  src/world/graph_file.cpp
  src/world/json_util.cpp
  src/world/layer_file.cpp
  src/world/loader.cpp
  src/world/region_file.cpp
  src/world/road_graph.cpp
  src/world/set_catalog.cpp
  src/world/slopes.cpp
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
target_link_libraries(lc_life PUBLIC lc_world PRIVATE lc_platform)
lc_project_target(lc_life)

# Debugging aid for city life: summary, problems, chains (the worldgen cross-check), dumps, the
# city bench and the roaming soak.
add_executable(lifeinfo src/life/lifeinfo_main.cpp)
target_link_libraries(lifeinfo PRIVATE lc_life)
target_compile_definitions(lifeinfo PRIVATE LC_LIFEINFO_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets")
lc_project_target(lifeinfo)

# Debugging aid for world builders and QA: summary, validation, region and tile dumps, digest.
add_executable(worldinfo src/world/worldinfo_main.cpp)
target_link_libraries(worldinfo PRIVATE lc_world lc_platform)
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

# --- World renderer and viewer (src/worldview/) --------------------------------------------------
# Draws the prebuilt world: atlas pages streamed by set, cached ground cells and impostors,
# depth-sorted landmark pieces, region themes and the overview; laeticias-world shows it headless.
find_package(Threads REQUIRED)
add_library(lc_worldview STATIC
  src/worldview/actor_looks.cpp
  src/worldview/camera.cpp
  src/worldview/cell_cache.cpp
  src/worldview/cells.cpp
  src/worldview/city_sound.cpp
  src/worldview/cover.cpp
  src/worldview/gather.cpp
  src/worldview/overview.cpp
  src/worldview/page_atlas.cpp
  src/worldview/page_runs.cpp
  src/worldview/places.cpp
  src/worldview/renderer.cpp
  src/worldview/renderer_gpu.cpp
  src/worldview/renderer_terrain.cpp
  src/worldview/script.cpp
  src/worldview/soundscape.cpp
  src/worldview/terrain.cpp
  src/worldview/theme.cpp
  src/worldview/weather_field.cpp
  src/worldview/viewer.cpp
  src/worldview/world_lights.cpp
  src/worldview/world_sprites.cpp
)
target_link_libraries(lc_worldview PUBLIC lc_engine lc_world Threads::Threads)
lc_project_target(lc_worldview)

# The game: the app (main loop, input, scripts, bench, front door) over the engine and the world,
# split from main() so tests can link it.
set(LC_VERSION_CPP ${CMAKE_BINARY_DIR}/generated/version.cpp)
# Run on every build so `--version` names the commit built; the source is rewritten only when its
# text changes, so an unchanged commit recompiles nothing.
add_custom_target(lc_version
  COMMAND ${CMAKE_COMMAND} -DSOURCE_DIR=${CMAKE_SOURCE_DIR} -DOUT=${LC_VERSION_CPP}
          -DVERSION=${LC_VERSION} -DPLATFORM=${LC_PLATFORM}
          -P ${CMAKE_SOURCE_DIR}/cmake/version.cmake
  BYPRODUCTS ${LC_VERSION_CPP}
  COMMENT "Stamping the version" VERBATIM)
add_library(lc_app STATIC
  ${LC_VERSION_CPP}
  src/app/app.cpp
  src/app/options.cpp
  src/app/script.cpp
  src/app/app_script.cpp
  src/app/app_bench.cpp
  src/app/app_benchmark.cpp
  src/app/app_city.cpp
  src/app/app_build.cpp
  src/app/app_front.cpp
  src/app/app_gpu.cpp
  src/app/app_photo.cpp
  src/app/app_life.cpp
  src/app/app_perf.cpp
  src/app/window_state.cpp
  src/app/app_world.cpp
  src/app/identity.cpp
)
target_compile_definitions(lc_app PRIVATE LC_APP_ID="${LC_APP_ID}")
target_link_libraries(lc_app PUBLIC lc_worldview)
add_dependencies(lc_app lc_version)
lc_project_target(lc_app)

add_executable(laeticias-corner src/app/main.cpp src/platform/alloc_count.cpp)
target_link_libraries(laeticias-corner PRIVATE lc_app)
lc_project_target(laeticias-corner)
lc_runtime_dlls(laeticias-corner)
if(WIN32)
  # A window, no console; the manifest makes the process's narrow code page UTF-8, the encoding
  # SDL and the game's paths and arguments are in.
  enable_language(RC)
  configure_file(packaging/windows/laeticias-corner.rc.in
                 ${CMAKE_BINARY_DIR}/generated/laeticias-corner.rc @ONLY)
  target_sources(laeticias-corner PRIVATE ${CMAKE_BINARY_DIR}/generated/laeticias-corner.rc)
  set_target_properties(laeticias-corner PROPERTIES WIN32_EXECUTABLE TRUE)
else()
  # The installed game finds the SDL beside it.
  set_target_properties(laeticias-corner PROPERTIES INSTALL_RPATH "$ORIGIN")
endif()

# The release package: `cmake --install <build> --prefix <dir>` lays out the game, its assets,
# the licences and, when SDL was built here, SDL beside the game.
install(TARGETS laeticias-corner RUNTIME DESTINATION .)
install(DIRECTORY assets/ DESTINATION assets)
install(FILES LICENSE LICENSE-ASSETS LICENSING.md THIRD-PARTY.md DESTINATION .)
if(WIN32)
  install(FILES packaging/windows/README.txt DESTINATION .)
else()
  install(FILES packaging/linux/README.txt DESTINATION .)
endif()
if(TARGET SDL3-shared)
  install(TARGETS SDL3-shared
    RUNTIME DESTINATION .
    LIBRARY DESTINATION . NAMELINK_SKIP
    ARCHIVE DESTINATION lib EXCLUDE_FROM_ALL)
  install(FILES ${sdl3_SOURCE_DIR}/LICENSE.txt DESTINATION licenses RENAME SDL-LICENSE.txt)
endif()
# The licence texts of what is compiled into the game (THIRD-PARTY.md lists them); the fonts'
# sit beside them in assets/fonts/. MinGW-w64's runtime and winpthreads, linked in statically on
# Windows, ask for theirs in the binary's documentation.
install(FILES third_party/stb/LICENSE DESTINATION licenses RENAME stb-LICENSE.txt)
if(DEFINED nlohmann_json_SOURCE_DIR)
  install(FILES ${nlohmann_json_SOURCE_DIR}/LICENSE.MIT DESTINATION licenses
          RENAME nlohmann_json-LICENSE.txt)
endif()
if(MINGW)
  install(FILES packaging/windows/licenses/mingw-w64-runtime-COPYING.txt
                packaging/windows/licenses/winpthreads-COPYING.txt DESTINATION licenses)
endif()

if(LC_TESTS)
  add_subdirectory(tests)
endif()

add_executable(laeticias-world src/worldview/viewer_main.cpp)
target_link_libraries(laeticias-world PRIVATE lc_worldview)
lc_project_target(laeticias-world)
lc_runtime_dlls(laeticias-world)

if(LC_TESTS)
  add_executable(lc_worldview_tests
    tests/worldview_main.cpp
    tests/worldview_depth.cpp
    tests/worldview_gpu.cpp
    tests/worldview_logic.cpp
    tests/worldview_render.cpp
  )
  target_link_libraries(lc_worldview_tests PRIVATE lc_worldview lc_doctest)
  target_compile_definitions(lc_worldview_tests PRIVATE
    LC_WORLDVIEW_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets")
  lc_project_target(lc_worldview_tests)
  lc_runtime_dlls(lc_worldview_tests)
  # Same doctest/libstdc++ <ciso646> warning as lc_tests (see tests/CMakeLists.txt).
  target_compile_options(lc_worldview_tests PRIVATE $<$<CXX_COMPILER_ID:Clang>:-Wno-\#warnings>)
  set(LC_WORLDVIEW_ENV "SDL_VIDEODRIVER=dummy;SDL_AUDIODRIVER=dummy")
  add_test(NAME worldview_unit COMMAND lc_worldview_tests)
  set_tests_properties(worldview_unit PROPERTIES ENVIRONMENT "${LC_WORLDVIEW_ENV}")

  # Scripted viewer runs (tests/scripts/world/*.lws): shots land in <build>/shots/world/, and an
  # `expect` that does not hold fails the run.
  file(GLOB LC_WORLD_SCRIPTS CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/tests/scripts/world/*.lws")
  foreach(script ${LC_WORLD_SCRIPTS})
    get_filename_component(name ${script} NAME_WE)
    add_test(NAME world_script_${name}
      COMMAND laeticias-world --script ${script} --shots "${CMAKE_BINARY_DIR}/shots/world")
    set_tests_properties(world_script_${name} PROPERTIES ENVIRONMENT "${LC_WORLDVIEW_ENV}")
  endforeach()

  # The bench cases at 1080p on the GPU path, windowless; budgets assert in optimised builds
  # (sanitizer builds report). Skipped (exit 77) where no GPU renderer can be created.
  if(LC_SANITIZE)
    set(LC_WORLD_BUDGET --no-budget)
  else()
    set(LC_WORLD_BUDGET "")
  endif()
  add_test(NAME world_bench
    COMMAND laeticias-world --bench --renderer opengl --size 1920x1080 ${LC_WORLD_BUDGET})
  set(LC_WORLD_BENCH_ENV "")
  if(LC_SANITIZE)
    # The GPU driver behind the offscreen EGL path leaks allocations of its own.
    set(LC_WORLD_BENCH_ENV "ASAN_OPTIONS=detect_leaks=0")
  endif()
  set_tests_properties(world_bench PROPERTIES SKIP_RETURN_CODE 77 RUN_SERIAL TRUE
    ENVIRONMENT "${LC_WORLD_BENCH_ENV}")
endif()
