set(LC_SCRATCH "${CMAKE_CURRENT_BINARY_DIR}/scratch")

add_executable(lc_tests
  test_main.cpp
  test_support.cpp
  test_core.cpp
  test_conditions.cpp
  test_saves.cpp
  test_progress.cpp
  test_engine.cpp
  test_coverage.cpp
)
target_link_libraries(lc_tests PRIVATE lc_engine lc_doctest)
target_compile_definitions(lc_tests PRIVATE
  LC_TEST_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets"
  LC_TEST_SCRATCH_DIR="${LC_SCRATCH}"
  LC_TEST_FIXTURES_DIR="${CMAKE_CURRENT_SOURCE_DIR}/fixtures")
lc_project_target(lc_tests)
# doctest 2.4.12 includes <ciso646> under Clang, which libstdc++ 16 flags with a #warning that
# cannot be silenced per header; it is harmless, so only that diagnostic is relaxed for tests.
target_compile_options(lc_tests PRIVATE $<$<CXX_COMPILER_ID:Clang>:-Wno-\#warnings>)

set(LC_HEADLESS_ENV "SDL_VIDEODRIVER=dummy;SDL_AUDIODRIVER=dummy")
add_test(NAME unit COMMAND lc_tests --test-case-exclude=*coverage*,capture:*)
# Missing art or audio fails the run (shadows are optional per the contract).
add_test(NAME coverage COMMAND lc_tests --test-case=*coverage* --success=false)
set_tests_properties(unit PROPERTIES ENVIRONMENT "${LC_HEADLESS_ENV}")
set_tests_properties(coverage PROPERTIES ENVIRONMENT "${LC_HEADLESS_ENV};LAETICIA_STRICT_COVERAGE=1")

# Scripted headless runs through the real executable. Each script lives in tests/scripts/ and
# fails the run (non-zero exit) when one of its `expect` lines does not hold. Entries are
# test-name|script|size|labels; screenshots land in <build>/shots/. Runs at large sizes are slow
# with the software renderer and carry the "heavy" label: the default presets skip them.
set(LC_SCRIPTS
  "launch_960|launch_960x600|960x600|"
  "build_and_undo|build_and_undo|640x400|"
  "paint_terrain|paint_terrain|640x400|"
  "undo_drag|undo_drag|640x400|"
  "modifier_pan|modifier_pan|640x400|"
  "save_reload_a|save_reload_a|640x400|"
  "save_reload_b|save_reload_b|640x400|"
  "clock_phases|clock_phases|640x400|"
  "photo_mode|photo_mode|640x400|"
  "ui_states|ui_states|960x600|"
  "drawer_tabs|drawer_tabs|640x400|"
  "drawer_unlocks|drawer_unlocks|960x600|"
  "wish_first|wish_first|640x400|"
  "sketchbook|sketchbook|960x600|"
  "nook|nook|960x600|"
  "wish_waiting|wish_waiting|960x600|"
  "ui_tiny|ui_sizes|320x240|"
  "ui_small|ui_sizes|960x600|"
  "glass_small|glass|960x600|heavy"
  "corrupt_save|corrupt_save|640x400|"
  "migrate_v1|migrate_v1|640x400|"
  "rain|rain|640x400|"
  "visitors|visitors|640x400|"
  "clickthrough|clickthrough|640x400|"
  "ghost_edges|ghost_edges|640x400|"
  "launch_1280|launch_1280x800|1280x800|heavy"
  "launch_1080|launch_1920x1080|1920x1080|heavy"
  "launch_1440|launch_2560x1440|2560x1440|heavy"
  "launch_4k|launch_3840x2160|3840x2160|heavy"
  "ui_4k|ui_sizes|3840x2160|heavy"
  "glass_hd|glass|1920x1080|heavy"
)
foreach(size 960x600 1280x800 1920x1080 2560x1440 3840x2160)
  set(SIZE ${size})
  configure_file(scripts/launch.lcs.in "${CMAKE_CURRENT_BINARY_DIR}/scripts/launch_${size}.lcs" @ONLY)
endforeach()
set(LC_RUN_ENV "${LC_HEADLESS_ENV};LAETICIA_SAVE_DIR=${LC_SCRATCH}/unused")
set(LC_SAVE_DIRS "")
foreach(entry IN LISTS LC_SCRIPTS)
  string(REPLACE "|" ";" parts "${entry}")
  list(GET parts 0 name)
  list(GET parts 1 script)
  list(GET parts 2 size)
  list(GET parts 3 labels)
  set(save "${LC_SCRATCH}/save_${name}")
  if(name MATCHES "^save_reload_")
    set(save "${LC_SCRATCH}/save_reload")
  endif()
  set(file "${CMAKE_CURRENT_SOURCE_DIR}/scripts/${script}.lcs")
  if(script MATCHES "^launch_")
    set(file "${CMAKE_CURRENT_BINARY_DIR}/scripts/${script}.lcs")
  endif()
  list(APPEND LC_SAVE_DIRS "${save}")
  add_test(NAME script_${name}
    COMMAND laeticias-corner --headless --size ${size} --seed 1 --save-dir "${save}" --script "${file}"
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}")
  set_tests_properties(script_${name} PROPERTIES ENVIRONMENT "${LC_RUN_ENV}"
    FIXTURES_REQUIRED clean_saves)
  if(labels)
    set_tests_properties(script_${name} PROPERTIES LABELS "${labels}")
  endif()
endforeach()

# Every run starts from a clean save directory; the reload pair runs in order.
list(APPEND LC_SAVE_DIRS "${LC_SCRATCH}/save_missing_art"
     "${LC_SCRATCH}/save_audio" "${LC_SCRATCH}/save_bench")
list(REMOVE_DUPLICATES LC_SAVE_DIRS)
add_test(NAME prepare_saves COMMAND ${CMAKE_COMMAND} -E rm -rf ${LC_SAVE_DIRS})
set_tests_properties(prepare_saves PROPERTIES FIXTURES_SETUP clean_saves)
set_tests_properties(script_save_reload_a PROPERTIES FIXTURES_SETUP reload)
set_tests_properties(script_save_reload_b PROPERTIES FIXTURES_REQUIRED "clean_saves;reload")
# The corrupt-save run needs a garbage file in place before launch.
add_test(NAME prepare_corrupt_save COMMAND ${CMAKE_COMMAND}
  -DFILE=${LC_SCRATCH}/save_corrupt_save/worlds/laeticias-corner/world.json -P ${CMAKE_CURRENT_SOURCE_DIR}/write_garbage.cmake)
set_tests_properties(prepare_corrupt_save PROPERTIES FIXTURES_SETUP corrupt FIXTURES_REQUIRED clean_saves)
set_tests_properties(script_corrupt_save PROPERTIES FIXTURES_REQUIRED "clean_saves;corrupt")

# A real save from the first release, migrated on launch.
add_test(NAME prepare_migrate_v1 COMMAND ${CMAKE_COMMAND} -E copy
  ${CMAKE_CURRENT_SOURCE_DIR}/fixtures/save_v1.json ${LC_SCRATCH}/save_migrate_v1/corner.json)
set_tests_properties(prepare_migrate_v1 PROPERTIES FIXTURES_SETUP migrate FIXTURES_REQUIRED clean_saves)
set_tests_properties(script_migrate_v1 PROPERTIES FIXTURES_REQUIRED "clean_saves;migrate")

# A save directory the game cannot write to.
if(UNIX)
  set(ro "${LC_SCRATCH}/save_read_only")
  add_test(NAME prepare_read_only COMMAND ${CMAKE_COMMAND} -DMODE=prepare -DDIR=${ro}
    -P ${CMAKE_CURRENT_SOURCE_DIR}/read_only_dir.cmake)
  add_test(NAME cleanup_read_only COMMAND ${CMAKE_COMMAND} -DMODE=cleanup -DDIR=${ro}
    -P ${CMAKE_CURRENT_SOURCE_DIR}/read_only_dir.cmake)
  set_tests_properties(prepare_read_only PROPERTIES FIXTURES_SETUP read_only FIXTURES_REQUIRED clean_saves)
  set_tests_properties(cleanup_read_only PROPERTIES FIXTURES_CLEANUP read_only)
  add_test(NAME script_read_only
    COMMAND laeticias-corner --headless --size 640x400 --seed 1 --save-dir "${ro}"
            --script "${CMAKE_CURRENT_SOURCE_DIR}/scripts/read_only.lcs"
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}")
  set_tests_properties(script_read_only PROPERTIES ENVIRONMENT "${LC_RUN_ENV}"
    FIXTURES_REQUIRED "clean_saves;read_only")
endif()

# Missing cliff art shows a visible placeholder.
set(missing "${LC_SCRATCH}/assets_missing")
add_test(NAME prepare_missing_art COMMAND ${CMAKE_COMMAND} -DSRC=${CMAKE_SOURCE_DIR}/assets
  -DOUT=${missing} -P ${CMAKE_CURRENT_SOURCE_DIR}/make_missing_assets.cmake)
set_tests_properties(prepare_missing_art PROPERTIES FIXTURES_SETUP missing_art)
add_test(NAME script_missing_art
  COMMAND laeticias-corner --headless --size 640x400 --seed 1 --assets "${missing}"
          --save-dir "${LC_SCRATCH}/save_missing_art"
          --script "${CMAKE_CURRENT_SOURCE_DIR}/scripts/missing_art.lcs"
  WORKING_DIRECTORY "${CMAKE_BINARY_DIR}")
set_tests_properties(script_missing_art PROPERTIES ENVIRONMENT "${LC_RUN_ENV}"
  FIXTURES_REQUIRED "clean_saves;missing_art")

# The mix of a drag-paint, a mute toggle and a day/night crossfade, captured headless and checked
# for clipping and clicks.
set(capture "${LC_SCRATCH}/capture.wav")
add_test(NAME audio_capture
  COMMAND laeticias-corner --headless --size 640x400 --seed 1 --audio-out "${capture}"
          --save-dir "${LC_SCRATCH}/save_audio"
          --script "${CMAKE_CURRENT_SOURCE_DIR}/scripts/audio_capture.lcs"
  WORKING_DIRECTORY "${CMAKE_BINARY_DIR}")
set_tests_properties(audio_capture PROPERTIES ENVIRONMENT "${LC_RUN_ENV}"
  FIXTURES_SETUP audio FIXTURES_REQUIRED clean_saves)
add_test(NAME audio_capture_check COMMAND lc_tests --test-case=capture:*)
set_tests_properties(audio_capture_check PROPERTIES ENVIRONMENT "LC_AUDIO_CAPTURE=${capture}"
  FIXTURES_REQUIRED audio)

# Frame budget (CLAUDE.md: under 2 ms for update + draw submission) on the GPU path, windowless.
# Sanitizer builds run many times slower, so there the bench only has to run cleanly. Skipped
# (exit 77) where no GPU renderer can be created.
if(LC_SANITIZE)
  set(LC_BUDGET "")
else()
  set(LC_BUDGET --budget-ms 2)
endif()
add_test(NAME bench
  COMMAND laeticias-corner --bench --renderer opengl --size 1920x1080 --seed 1 --frames 240
          ${LC_BUDGET} --save-dir "${LC_SCRATCH}/save_bench")
# The planned 1024x512 world, built up around the camera: reported, not yet held to the budget
# (see out/reports/engine-foundation.md for the numbers and the next step).
add_test(NAME bench_world
  COMMAND laeticias-corner --bench --renderer opengl --size 1920x1080 --seed 1 --frames 240
          --map 1024x512 --density 0.6 --save-dir "${LC_SCRATCH}/save_bench")
set(LC_BENCH_ENV "${LC_RUN_ENV}")
if(LC_SANITIZE)
  # The GPU driver and D-Bus behind the offscreen EGL path leak a few allocations of their own;
  # project code is leak-checked by every software-rendered test.
  list(APPEND LC_BENCH_ENV "ASAN_OPTIONS=detect_leaks=0")
endif()
set_tests_properties(bench bench_world PROPERTIES ENVIRONMENT "${LC_BENCH_ENV}" SKIP_RETURN_CODE 77
  FIXTURES_REQUIRED clean_saves RUN_SERIAL TRUE)
set_tests_properties(bench_world PROPERTIES LABELS heavy)
