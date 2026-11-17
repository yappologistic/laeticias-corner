#!/bin/sh
# Regenerate assets/atlas.png + assets/atlas.json (and validate). Pass --preview to also write
# contact sheets to out/artgen/. Creates the pinned virtualenv on first use.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$here/.venv/bin/python" ]; then
    python3 -m venv "$here/.venv"
    "$here/.venv/bin/pip" install --quiet -r "$here/requirements.txt"
fi
cd "$here"
exec "$here/.venv/bin/python" generate.py "$@"
