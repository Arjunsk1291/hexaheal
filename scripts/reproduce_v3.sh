#!/usr/bin/env bash
# HexaHeal v3 reproduction (MuJoCo simulation). Usage: scripts/reproduce_v3.sh [tables|full]
#  tables (default, ~1 min): rebuild every table and figure from the committed result files in results/v3/.
#  full (hours on 2 vCPU): re-run every episode on seeds 0-9 (deterministic, so results should match the committed files exactly), then rebuild the tables.
# PPO runs must NOT have MUJOCO_GL=osmesa set. Everything is simulation.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-tables}" = "full" ]; then
  mkdir -p results/v3.rerun && mv results/v3/hh3_*.jsonl results/v3.rerun/ 2>/dev/null || true
  for c in tripod tuned ppo v1 v2A v2B; do python scripts/hh_final.py "$c"; done
  python scripts/hh3_oracle.py
  python scripts/hh3_latency.py results/v3/v2_config_base.json 0.0 0.2 0.4 0.7 1.0 1.5
  for c in tripod tuned; do python scripts/hh3_fault2.py "$c"; done
  python scripts/hh3_fault2.py v2B results/v3/v2_config_base.json _baseconfig
fi
python scripts/hh3_stats.py stage1
python scripts/hh3_stage2_doc.py
python scripts/hh3_latency_plot.py
python scripts/hh3_fault2_stats.py
