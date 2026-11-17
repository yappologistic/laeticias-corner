#!/usr/bin/env sh
# One-command regeneration of assets/audio: bootstraps the pinned venv, renders
# everything (or only names matching the given filters), then validates all files.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
[ -x "$here/.venv/bin/python" ] || python3 -m venv "$here/.venv"
"$here/.venv/bin/pip" install --quiet --disable-pip-version-check -r "$here/requirements.txt"
exec "$here/.venv/bin/python" "$here/generate.py" "$@"
