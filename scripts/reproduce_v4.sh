#!/usr/bin/env bash
# HexaHeal v4. "tables": rebuild stats and figures from committed results (about a minute). "full": re-run the v4 episodes (Tier B+ and Tier B, 210 runs each; deterministic; long on 2 vCPU).
set -e
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
if [ "${1:-tables}" = "full" ]; then
  rm -f results/v4/hh4_final_*.jsonl
  python3 scripts/hh4_final.py v2B & python3 scripts/hh4_final.py v2Bplus & wait
fi
python3 scripts/hh4_stats.py
python3 scripts/hh4_figs.py
