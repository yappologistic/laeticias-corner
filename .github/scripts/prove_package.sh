#!/usr/bin/env bash
# Proves that a release archive runs as a player gets it: unpacked into an empty directory (never
# the build tree, on a machine without the source, so the game can only use the packaged assets),
# it prints its version, plays 300 frames headless, and draws the proof script's two screenshots
# (packaging/proof.lcs, software renderer), copied with the version line into OUT.
# Usage: prove_package.sh ARCHIVE PROOF_SCRIPT OUT
set -euo pipefail
archive=$(realpath "$1")
script=$(realpath "$2")
mkdir -p "$3"
out=$(realpath "$3")

work=$(mktemp -d)
case $archive in
  *.zip) (cd "$work" && 7z x -bd -y "$archive" > /dev/null) ;;
  *.tar.gz) tar -xzf "$archive" -C "$work" ;;
  *) echo "unknown archive type: $archive" >&2; exit 1 ;;
esac
dir=$(find "$work" -mindepth 1 -maxdepth 1 -type d)
exe=$dir/laeticias-corner
[[ -f $exe.exe ]] && exe=$exe.exe

export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
unset LAETICIA_ASSETS_DIR LAETICIA_SAVE_DIR

"$exe" --version | tee "$out/version.txt"
grep -q "^Laeticia's Corner " "$out/version.txt"
"$exe" --headless --frames 300 --save-dir "$work/save-run"
(cd "$work" && "$exe" --script "$script" --size 960x600 --seed 1 --save-dir "$work/save-shots")
cp "$work"/proof-home.png "$work"/proof-rome.png "$out/"
rm -rf "$work"
echo "proved: $(basename "$archive")"
