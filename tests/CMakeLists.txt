set(LC_SCRATCH "${CMAKE_CURRENT_BINARY_DIR}/scratch")

add_executable(lc_tests
  test_main.cpp
  test_support.cpp
  test_core.cpp
  test_engine.cpp
  test_coverage.cpp
)
target_link_libraries(lc_tests PRIVATE lc_engine lc_doctest)
target_compile_definitions(lc_tests PRIVATE
  LC_TEST_ASSETS_DIR="${CMAKE_SOURCE_DIR}/assets"
  LC_TEST_SCRATCH_DIR="${LC_SCRATCH}")
lc_project_target(lc_tests)

# Each doctest case is its own ctest entry so failures are easy to spot.
add_test(NAME unit COMMAND lc_tests --test-case-exclude=*coverage*)
add_test(NAME coverage COMMAND lc_tests --test-case=*coverage* --success=false)
set_tests_properties(unit coverage PROPERTIES
  ENVIRONMENT "SDL_VIDEODRIVER=offscreen;SDL_AUDIODRIVER=dummy")

# Scripted headless runs through the real executable. Each script lives in tests/scripts/ and
# fails the run (non-zero exit) when one of its `expect` lines does not hold. Entries are
# test-name|script|size; screenshots land in <build>/shots/.
set(LC_SCRIPTS
  "launch|launch|1280x800"
  "build_and_undo|build_and_undo|1280x800"
  "paint_terrain|paint_terrain|1280x800"
  "save_reload_a|save_reload_a|1280x800"
  "save_reload_b|save_reload_b|1280x800"
  "clock_phases|clock_phases|1280x800"
  "photo_mode|photo_mode|1280x800"
  "ui_states|ui_states|1280x800"
  "ui_small|ui_sizes|960x600"
  "ui_4k|ui_sizes|3840x2160"
  "corrupt_save|corrupt_save|1280x800"
  "rain|rain|1280x800"
  "visitors|visitors|1280x800"
)
set(LC_RUN_ENV "SDL_VIDEODRIVER=offscreen;SDL_AUDIODRIVER=dummy;LAETICIA_SAVE_DIR=${LC_SCRATCH}/unused")
set(LC_SAVE_DIRS "")
foreach(entry IN LISTS LC_SCRIPTS)
  string(REPLACE "|" ";" parts "${entry}")
  list(GET parts 0 name)
  list(GET parts 1 script)
  list(GET parts 2 size)
  set(save "${LC_SCRATCH}/save_${name}")
  if(name MATCHES "^save_reload_")
    set(save "${LC_SCRATCH}/save_reload")
  endif()
  list(APPEND LC_SAVE_DIRS "${save}")
  add_test(NAME script_${name}
    COMMAND laeticias-corner --headless --size ${size} --seed 1
            --save-dir "${save}" --script "${CMAKE_CURRENT_SOURCE_DIR}/scripts/${script}.lcs"
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}")
  set_tests_properties(script_${name} PROPERTIES ENVIRONMENT "${LC_RUN_ENV}" FIXTURES_REQUIRED clean_saves)
endforeach()
list(REMOVE_DUPLICATES LC_SAVE_DIRS)

# Every run starts from a clean save directory; the reload pair runs in order.
add_test(NAME prepare_saves COMMAND ${CMAKE_COMMAND} -E rm -rf ${LC_SAVE_DIRS})
set_tests_properties(prepare_saves PROPERTIES FIXTURES_SETUP clean_saves)
set_tests_properties(script_save_reload_a PROPERTIES FIXTURES_SETUP reload)
set_tests_properties(script_save_reload_b PROPERTIES FIXTURES_REQUIRED "clean_saves;reload")
# The corrupt-save run needs a garbage file in place before launch.
add_test(NAME prepare_corrupt_save COMMAND ${CMAKE_COMMAND}
  -DFILE=${LC_SCRATCH}/save_corrupt_save/corner.json -P ${CMAKE_CURRENT_SOURCE_DIR}/write_garbage.cmake)
set_tests_properties(prepare_corrupt_save PROPERTIES FIXTURES_SETUP corrupt FIXTURES_REQUIRED clean_saves)
set_tests_properties(script_corrupt_save PROPERTIES FIXTURES_REQUIRED "clean_saves;corrupt")

add_test(NAME bench COMMAND laeticias-corner --headless --size 1280x800 --seed 1 --bench --frames 240
         --save-dir "${LC_SCRATCH}/save_bench")
set_tests_properties(bench PROPERTIES ENVIRONMENT "${LC_RUN_ENV}")
