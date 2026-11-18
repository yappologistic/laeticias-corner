// Counts the game's heap allocations per thread (platform/process.hpp), so the profiler and the
// benchmarks can show that a steady frame makes none (CLAUDE.md "Code standards"). Linked into
// the game's executable only. Sanitizer builds keep their own operator new, which checks more
// than this one counts.

#include "platform/process.hpp"

#include <cstdlib>
#include <new>

// GCC names the sanitizer with a macro, Clang with a feature test.
#if defined(__SANITIZE_ADDRESS__)
#define LC_SANITIZED 1
#elif defined(__has_feature)
#if __has_feature(address_sanitizer)
#define LC_SANITIZED 1
#endif
#endif

#if !defined(LC_SANITIZED)

namespace {

void* counted(std::size_t size) {
    lc::noteAlloc();
    // malloc(0) may return null; operator new may not.
    if (void* p = std::malloc(size != 0 ? size : 1)) return p;
    throw std::bad_alloc();
}

void* counted(std::size_t size, std::align_val_t align) {
    lc::noteAlloc();
    const auto a = static_cast<std::size_t>(align);
    // aligned_alloc wants a size that is a multiple of the alignment.
    const std::size_t n = (size + a - 1) / a * a;
    if (void* p = std::aligned_alloc(a, n != 0 ? n : a)) return p;
    throw std::bad_alloc();
}

// Counting starts before main: every allocation of the game is seen.
const struct Enable {
    Enable() { lc::enableAllocCounting(); }
} kEnable;

} // namespace

void* operator new(std::size_t size) {
    return counted(size);
}
void* operator new[](std::size_t size) {
    return counted(size);
}
void* operator new(std::size_t size, std::align_val_t align) {
    return counted(size, align);
}
void* operator new[](std::size_t size, std::align_val_t align) {
    return counted(size, align);
}
void* operator new(std::size_t size, const std::nothrow_t&) noexcept {
    lc::noteAlloc();
    return std::malloc(size != 0 ? size : 1);
}
void* operator new[](std::size_t size, const std::nothrow_t&) noexcept {
    lc::noteAlloc();
    return std::malloc(size != 0 ? size : 1);
}
// Everything above comes from malloc or aligned_alloc: free releases both.
void operator delete(void* p) noexcept {
    std::free(p);
}
void operator delete[](void* p) noexcept {
    std::free(p);
}
void operator delete(void* p, std::size_t) noexcept {
    std::free(p);
}
void operator delete[](void* p, std::size_t) noexcept {
    std::free(p);
}
void operator delete(void* p, std::align_val_t) noexcept {
    std::free(p);
}
void operator delete[](void* p, std::align_val_t) noexcept {
    std::free(p);
}
void operator delete(void* p, std::size_t, std::align_val_t) noexcept {
    std::free(p);
}
void operator delete[](void* p, std::size_t, std::align_val_t) noexcept {
    std::free(p);
}
void operator delete(void* p, const std::nothrow_t&) noexcept {
    std::free(p);
}
void operator delete[](void* p, const std::nothrow_t&) noexcept {
    std::free(p);
}

#endif
