#!/usr/bin/env bash
# setup + actual simulation runs + integrity checks + report
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v uv >/dev/null; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock
  .venv/bin/python -m pip install --no-deps -e .
else
  test -d .venv || uv venv --python 3.10 .venv
  uv pip sync --python .venv/bin/python requirements.lock
  uv pip install --python .venv/bin/python --no-deps -e .
fi
export MUJOCO_GL=egl
export PYTHONPATH="$PWD/src:$PWD/scripts${PYTHONPATH:+:$PYTHONPATH}"
.venv/bin/python -m pytest -q
.venv/bin/python scripts/release_run.py "$@"
.venv/bin/python scripts/release_demo.py
.venv/bin/python scripts/release_report.py
