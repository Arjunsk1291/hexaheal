# HexaHeal v4 - Stage 2 results (MEASURED; MuJoCo simulation only, 2 vCPU sandbox; seeds 0-9; no hardware)

Pre-registration: docs/PREREGISTRATION_V4.md (committed before the run). Scripts: scripts/hh4_final.py, scripts/hh4_stats.py. Data: results/v4/.

## Verdict: the warm start did NOT pass its rule (no gain)

Rule: at least +2 recovered cases vs Tier B (N >= 8) AND the paired bootstrap 95% CI excludes zero.

Tier B+ recovered 9 of 21 vs Tier B 6: difference +3, 95% CI [0, 6]. N and the point estimate meet the rule; the interval touches zero, so the rule fails. Verdict: **no gain by the pre-registered rule**. The point estimate is positive, the evidence is not enough to call it real. The library is leave-one-case-out (the failed set and its mirror are removed), so this is not a lookup of the answer. Latency sweep NOT re-run for Tier B+ (rule failed); the Tier B sweep stands.

| controller | recovered cases /21 | upright cases /21 | recovered runs /210 | upright runs /210 | upright but standing still /210 |
|---|---|---|---|---|---|
| plain tripod | 0 | 6 | 0 | 75 | 75 |
| Tier B (re-run) | 6 | 12 | 69 | 123 | 54 |
| Tier B+ (warm start) | 9 | 14 | 90 | 129 | 39 |
| oracle (upper bound) | 15 | 18 | 164 | 190 | 26 |

Paired bootstrap (10,000 resamples of seeds jointly, rng seed 0): Tier B+ minus plain tripod recovered +9 [7, 10]; Tier B minus plain tripod +6 [4, 8]; upright Tier B+ minus Tier B +2 [0, 3].
The Tier B re-run reproduces the v3 Tier B results on all 210 runs (determinism check, MEASURED).

## Stand-still diagnostic for Tier B (v3 config, 210 runs)

MEASURED: planning starts on average 0.36 s after the fault (the detection time); the robot then stands for exactly 4.6 s in every run that planned (it is a fixed simulated-time budget, not an adaptive one); the new gait starts about 5 s after the fault, i.e. at about 9 s of the 14 s run. The metric 'recovered' uses the last 8 s (6 s to 14 s), so about 3 s of that window is standing. GUESS: this shortens the window where speed can accumulate and caps how fast a recovered run can look; it was not tested by changing the window.
MEASURED: of 123 upright Tier B runs, 18 never reach 0.125 m/s over any 2 s window after the fault, and 54 end the run not recovered. First-walk times are about 4 s after the fault for most cases, which is before the gait switch, so they come from the old gait (damaged tripod) still moving, not from the re-planned gait. A strict count of runs whose first walking window starts at or after the switch is only 13 of 123 (approximation, GUESS: time to first recovered step after the switch was not logged separately).

| case | upright runs /10 | never walk | mean stand s | mean first-walk s after fault |
|---|---|---|---|---|
| dl_0 | 5 | 0 | 4.6 | 4.31 |
| dl_1 | 9 | 0 | 4.6 | 3.97 |
| dl_2 | 8 | 1 | 4.6 | 4.11 |
| dl_3 | 8 | 0 | 4.6 | 4.01 |
| dl_4 | 10 | 0 | 4.6 | 3.99 |
| dl_5 | 9 | 0 | 4.6 | 3.92 |
| dl_0_1 | 0 | 0 | - | - |
| dl_0_2 | 6 | 5 | 4.6 | 4.68 |
| dl_0_3 | 0 | 0 | - | - |
| dl_0_4 | 9 | 1 | 4.6 | 4.27 |
| dl_0_5 | 9 | 2 | 4.6 | 4.04 |
| dl_1_2 | 0 | 0 | - | - |
| dl_1_3 | 9 | 0 | 4.6 | 3.87 |
| dl_1_4 | 10 | 4 | 4.6 | 4.2 |
| dl_1_5 | 8 | 0 | 4.6 | 4.21 |
| dl_2_3 | 0 | 0 | - | - |
| dl_2_4 | 10 | 1 | 4.6 | 4.16 |
| dl_2_5 | 0 | 0 | - | - |
| dl_3_4 | 0 | 0 | - | - |
| dl_3_5 | 8 | 0 | 4.6 | 4.38 |
| dl_4_5 | 5 | 4 | 4.6 | 4.72 |

(cases with 0 upright runs have no data)

## Claims register (v4)

| claim | value | label | file |
|---|---|---|---|
| Warm start passes pre-registered rule | no | MEASURED | results/v4/stage2_stats.json |
| Tier B+ recovered cases | 9 of 21 (Tier B 6) | MEASURED | results/v4/hh4_final_v2Bplus_0-9.jsonl |
| Tier B stands still before the new gait | 4.6 s, all planning runs | MEASURED | results/v4/hh4_final_v2B_0-9.jsonl |
| Standing shortens the recovered window | - | GUESS | not tested |
| Physical limit for the 9 unsolved cases | - | UNKNOWN | no controller found one; not proof of impossibility |

## Everything that failed or did not help

- Warm start: no gain by the rule (above).
- v3 tuning rounds (do-no-harm, steady-state fitness): worse than the base config (docs/V3_stage2.md).
- Healing v1: 0 recovered, fewer upright than plain tripod.
- PPO: 1 recovered case.
- 9 of 21 cases are never recovered by any controller (R1+R2, R1+R3, R1+L1, R1+L2, R2+R3, R3+L1, R3+L3, L1+L2, L2+L3).
- Front-leg loss is latency-limited: R1 and L1 go to 0/10 recovered at a 0.2 s diagnosis delay.
- Connectome-inspired controller: a small MLP beat it; archived.
