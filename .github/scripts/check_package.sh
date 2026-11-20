#!/usr/bin/env bash
# Checks that an unpacked release package depends on nothing a player has to install.
#   Linux:   the game and SDL need only glibc (no C++ runtime), the game finds SDL through
#            $ORIGIN, SDL can load X11, Wayland, PipeWire, PulseAudio and ALSA, and the newest
#            glibc symbol used is printed (the minimum glibc); the launcher (a desktop file named
#            by the application id) and the 256 px icon it names are there.
#   Windows: every DLL the game and SDL import is shipped beside them or is part of Windows (in
#            System32, or an API set), and the game is a windowed (GUI subsystem) program that
#            carries its icon and its manifest as resources.
# Usage: check_package.sh DIR
set -euo pipefail
dir=$1
fail() { echo "check_package: $*" >&2; exit 1; }

case $(uname -s) in
  Linux)
    game=$dir/laeticias-corner
    sdl=$dir/libSDL3.so.0
    [[ -f $game && -e $sdl ]] || fail "the game or libSDL3.so.0 is missing"
    for f in "$game" "$sdl"; do
      echo "== $(basename "$f") needs:"
      readelf -d "$f" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/  \1/p' | tee "$RUNNER_TEMP/needed"
      while read -r lib; do
        case $lib in
          libSDL3.so.0 | libc.so.6 | libm.so.6 | libdl.so.2 | libpthread.so.0 | librt.so.1 | \
            ld-linux-x86-64.so.2) ;;
          *) fail "$(basename "$f") needs $lib, which a player may not have" ;;
        esac
      done < "$RUNNER_TEMP/needed"
    done
    readelf -d "$game" | grep -E '(RUNPATH|RPATH).*\[\$ORIGIN\]' > /dev/null ||
      fail "the game does not look for SDL beside itself"
    for lib in libX11.so.6 libwayland-client.so.0 libdecor-0.so.0 libpipewire-0.3.so.0 \
      libpulse.so.0 libasound.so.2; do
      grep -q "$lib" "$sdl" || fail "SDL was built without $lib"
    done
    desktop=$(find "$dir" -maxdepth 1 -name '*.desktop' -print -quit)
    [[ -n $desktop ]] || fail "the launcher (a .desktop file) is missing"
    icon=$(sed -n 's/^Icon=//p' "$desktop")
    [[ $(basename "$desktop" .desktop) == "$icon" ]] ||
      fail "$(basename "$desktop") names the icon $icon, not its own id"
    file "$dir/$icon.png" | grep -q 'PNG image data, 256 x 256, 8-bit/color RGBA' ||
      fail "$icon.png is not a 256 x 256 RGBA picture"
    if command -v desktop-file-validate > /dev/null; then
      desktop-file-validate "$desktop" || fail "$(basename "$desktop") is not a valid desktop file"
    fi
    glibc=$(objdump -T "$game" "$sdl" | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1)
    echo "newest glibc version needed: $glibc, by:"
    objdump -T "$game" "$sdl" | grep -F "($glibc)" | awk '{print "  " $NF}' | sort -u
    ;;
  MINGW* | MSYS*)
    sys=$(cygpath -u "$SYSTEMROOT")/System32
    for f in "$dir"/laeticias-corner.exe "$dir"/SDL3.dll; do
      [[ -f $f ]] || fail "$(basename "$f") is missing"
      echo "== $(basename "$f") imports:"
      objdump -p "$f" | sed -n 's/^\s*DLL Name: //p' | tr -d '\r' | tee "$RUNNER_TEMP/imports"
      while read -r dll; do
        # api-ms-win-* are API sets: names the loader of Windows 10 and newer maps to its own
        # DLLs (the C runtime among them), with no file of that name needed.
        [[ ${dll,,} == api-ms-win-* ]] && continue
        [[ -f $dir/$dll || -f $sys/$dll ]] ||
          [[ -n $(find "$sys" -maxdepth 1 -iname "$dll" -print -quit) ]] ||
          fail "$(basename "$f") imports $dll, which is neither shipped nor part of Windows"
      done < "$RUNNER_TEMP/imports"
    done
    objdump -p "$dir"/laeticias-corner.exe > "$RUNNER_TEMP/headers"
    grep -q 'Subsystem.*(Windows GUI)' "$RUNNER_TEMP/headers" ||
      fail "the game is not a windowed (GUI subsystem) program"
    # The resource directory's types: 3 RT_ICON (the pictures), 0xe RT_GROUP_ICON (the icon
    # Explorer shows), 0x18 RT_MANIFEST.
    for type in 000003 00000e 000018; do
      grep -qE "^[0-9a-f]+   Entry: ID: 0x$type," "$RUNNER_TEMP/headers" ||
        fail "the game carries no resource of type 0x$type (icon or manifest)"
    done
    ;;
  *) fail "unknown system $(uname -s)" ;;
esac
echo "check_package: $dir is self-contained"
