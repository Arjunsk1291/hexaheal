"""Writes docs/V3_stage2.md from the tuning-seed files (seeds 100-109 only)."""
import collections
import json
import sys

sys.path.insert(0, "scripts")
from hh_common import CASES

from neurowalker.hh_eval import case_name

V = [("tuned", "tuned tripod"), ("base", "Tier B base (HexaHeal config)"), ("r1_dnh", "round 1: + do-no-harm (1.0 s watch)"), ("r2_warm", "round 2: steady-state fitness (warm 1.5 s, rollout 4.5 s)")]
D = {}
for k, _ in V:
    D[k] = collections.defaultdict(list)
    for line in open(f"results/v3/tune_{k}.jsonl"):
        r = json.loads(line); D[k][r["case"]].append(r)
L = ["# HexaHeal v3 Stage 2: weak-spot fixes (MEASURED on tuning seeds 100-109 only; MuJoCo simulation)", "",
     "Two tuning rounds were allowed. Both were NEGATIVE: neither beat the existing Tier B config on recovered cases, so the config is frozen unchanged (results/v3/v2_config_final.json). The final seeds 0-9 run of the frozen config is the Stage 1 Tier B row (re-running it reproduced it exactly: 100/100 episodes identical in the Stage 3 delay-0 run).", "",
     "| variant | N_recovered (of 21) | N_upright (of 21) | recovered runs /210 | upright runs /210 |", "|---|---|---|---|---|"]
for k, nm in V:
    d = D[k]
    L.append(f"| {nm} | {sum(1 for v in d.values() if sum(x['recovered'] for x in v) >= 7)} | {sum(1 for v in d.values() if sum(not x['fell'] for x in v) >= 7)} | {sum(x['recovered'] for v in d.values() for x in v)} | {sum(not x['fell'] for v in d.values() for x in v)} |")
L += ["", "## Per case, upright / recovered runs of 10 (tuning seeds)", "", "| case | " + " | ".join(nm for _, nm in V) + " |", "|---|" + "---|" * len(V)]
for c in CASES:
    L.append(f"| {case_name(c)} | " + " | ".join(f"{sum(not x['fell'] for x in D[k][c])}/{sum(x['recovered'] for x in D[k][c])}" for k, _ in V) + " |")
L += ["", "## Diagnosis", "",
      "- **Do-no-harm rule (round 1) hurt.** It watches the current gait for 1.0 s after the fault is suspected and keeps it if speed >= 0.125 m/s and tilt < 0.35 rad. That delays healing by about a second; the front-leg cases (R1, L1, L3 and doubles with them) go from walking to falling. It almost never fires usefully, because the tuned tripod does not walk after a fault in 18 of 21 cases (it only stands or falls).",
      "- **The listed regressions (R2+R3, L2+L3) are not walking regressions.** In the old matrix they were 'survived' cases, but the tuned tripod only stood still there (0 recovered runs), so v2 cannot have lowered walking recovery. R2+R3 and L2+L3 remain unrecovered by every controller.",
      "- **Steady-state fitness (round 2) did not help.** Scoring search rollouts after a 1.5 s warm-up (longer 4.5 s rollouts, same 60-trial sim-time budget) raised upright runs slightly (136 vs 132) but lowered recovered runs (45 vs 77). Cause UNKNOWN; a GUESS is that the surrogate rollout on a model copy rewards gaits that look fast in a short window but stall once the 14 s episode settles.",
      "- **Still open (not fixed):** Tier B noise on R1 and R1+R3, and R3+L1 (oracle walks; every controller 0 recovered). Not resolved within 2 rounds.",
      "- Config frozen to the pre-existing Tier B config, so no tuning result changes the Stage 1 Tier B numbers."]
open("docs/V3_stage2.md", "w").write("\n".join(L) + "\n")
print("\n".join(L[:9]))
