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
  src/core/progress.cpp
  src/core/progression.cpp
  src/core/save.cpp
  src/core/speech.cpp
  src/core/starter.cpp
  src/core/visitors.cpp
  src/core/weather.cpp
  src/core/world.cpp
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
  src/app/app_life.cpp
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
  src/ui/painter.cpp
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
