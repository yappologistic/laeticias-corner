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

function(lc_project_target target)
  target_compile_options(${target} PRIVATE ${LC_WARNINGS})
endfunction()
