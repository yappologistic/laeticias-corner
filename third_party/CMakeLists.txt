# Vendored single-file libraries. Compiled with warnings off: they are upstream code we do not
# modify, and project warning flags must stay strict for our own sources.
add_library(lc_stb STATIC stb/stb_impl.c)
target_include_directories(lc_stb SYSTEM PUBLIC stb)
target_compile_options(lc_stb PRIVATE -w)

add_library(lc_doctest INTERFACE)
target_include_directories(lc_doctest SYSTEM INTERFACE doctest)
