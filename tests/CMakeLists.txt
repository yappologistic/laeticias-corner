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
# fails the run (non-zero exit) when one of its `expect` lines does not hold.
set(LC_SCRIPTS
  launch
  build_and_undo
  paint_terrain
  save_reload_a
  save_reload_b
  clock_phases
  photo_mode
  ui_states
  corrupt_save
  rain
)
set(LC_RUN_ENV "SDL_VIDEODRIVER=offscreen;SDL_AUDIODRIVER=dummy;LAETICIA_SAVE_DIR=${LC_SCRATCH}/unused")
foreach(name IN LISTS LC_SCRIPTS)
  set(out "${LC_SCRATCH}/run_${name}")
  set(save "${LC_SCRATCH}/save_${name}")
  if(name MATCHES "^save_reload_")
    set(save "${LC_SCRATCH}/save_reload")
  endif()
  add_test(NAME script_${name}
    COMMAND laeticias-corner --headless --size 1280x800 --seed 1
            --save-dir "${save}" --script "${CMAKE_CURRENT_SOURCE_DIR}/scripts/${name}.lcs"
    WORKING_DIRECTORY "${CMAKE_BINARY_DIR}")
  set_tests_properties(script_${name} PROPERTIES ENVIRONMENT "${LC_RUN_ENV}")
endforeach()

# Prepare clean save directories; the reload pair must run in order.
add_test(NAME prepare_saves COMMAND ${CMAKE_COMMAND} -E rm -rf
  "${LC_SCRATCH}/save_reload" "${LC_SCRATCH}/save_corrupt_save" "${LC_SCRATCH}/save_launch")
set_tests_properties(prepare_saves PROPERTIES FIXTURES_SETUP clean_saves)
foreach(name IN LISTS LC_SCRIPTS)
  set_property(TEST script_${name} APPEND PROPERTY FIXTURES_REQUIRED clean_saves)
endforeach()
set_tests_properties(script_save_reload_a PROPERTIES FIXTURES_SETUP reload)
set_tests_properties(script_save_reload_b PROPERTIES FIXTURES_REQUIRED "clean_saves;reload")
# The corrupt-save script needs a garbage file in place before launch.
add_test(NAME prepare_corrupt_save COMMAND ${CMAKE_COMMAND}
  -DFILE=${LC_SCRATCH}/save_corrupt_save/corner.json -P ${CMAKE_CURRENT_SOURCE_DIR}/write_garbage.cmake)
set_tests_properties(prepare_corrupt_save PROPERTIES FIXTURES_SETUP corrupt FIXTURES_REQUIRED clean_saves)
set_property(TEST script_corrupt_save APPEND PROPERTY FIXTURES_REQUIRED corrupt)

add_test(NAME bench COMMAND laeticias-corner --headless --size 1280x800 --seed 1 --bench --frames 240
         --save-dir "${LC_SCRATCH}/save_bench")
set_tests_properties(bench PROPERTIES ENVIRONMENT "${LC_RUN_ENV}")
