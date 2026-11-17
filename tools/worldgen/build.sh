#!/bin/sh
# World authoring: ./build.sh <layer>… | --all | --check | --preview <layer>|world [--no-write]
# Compiles layers into assets/world/, validates the composed world, writes reports and previews
# to out/worldgen/. Creates the pinned virtualenv on first use. `./build.sh --test` runs the tests.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$here/.venv/bin/python" ]; then
    python3 -m venv "$here/.venv"
    "$here/.venv/bin/pip" install --quiet -r "$here/requirements.txt"
fi
cd "$here"
if [ "$1" = "--test" ]; then
    shift
    exec nice -n 19 "$here/.venv/bin/python" -m unittest discover -s tests -t . "$@"
fi
exec nice -n 19 "$here/.venv/bin/python" -m worldgen.build "$@"
