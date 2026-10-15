#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
arena_python=python
if [ -x .venv/bin/python ]; then arena_python=.venv/bin/python; fi
exec "$arena_python" scripts/validate.py "$@"
