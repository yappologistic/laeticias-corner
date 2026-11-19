# Strict warnings and optional sanitizers for first-party targets only; vendored code is built
# separately (see third_party/) so these flags never have to be relaxed.

set(LC_WARNINGS -Wall -Wextra -Wpedantic -Wshadow -Wconversion -Werror)

if(LC_SANITIZE)
  set(LC_SANITIZER_FLAGS -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
  # Vendored code and the test framework must be instrumented too, or ASan reports
  # container-overflow false positives across the boundary.
  add_compile_options(${LC_SANITIZER_FLAGS})
  add_link_options(${LC_SANITIZER_FLAGS})
endif()

if(MINGW)
  # GCC checks formats marked printf against Microsoft's printf on MinGW, which knows no %zu;
  # SDL_Log formats with SDL's own printf, which does. SDL's switch drops its format marks there
  # only: Linux builds keep checking every SDL_Log.
  add_compile_definitions(SDL_DISABLE_ANALYZE_MACROS)
endif()

function(lc_project_target target)
  target_compile_options(${target} PRIVATE ${LC_WARNINGS})
  if(MINGW)
    # GCC keeps std::print's Windows console support in a library of its own.
    target_link_libraries(${target} PRIVATE stdc++exp)
  endif()
endfunction()

# Windows looks for DLLs beside the program: SDL3.dll is copied next to each program that links
# it, so the build tree's game, viewer and tests run where they are built.
function(lc_runtime_dlls target)
  if(WIN32)
    add_custom_command(TARGET ${target} POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different $<TARGET_RUNTIME_DLLS:${target}>
              $<TARGET_FILE_DIR:${target}>
      COMMAND_EXPAND_LISTS VERBATIM)
  endif()
endfunction()
