# HexaHeal pre-registration (committed before any Stage 4/5 result exists)

Simulation only (MuJoCo, 2 vCPU sandbox). Status of everything here: protocol, not results.

## Data discipline
- Tuning, debugging and design choices: seeds 100-109 only. Final evaluation: seeds 0-9 only, run once per final configuration. No eval-seed result may change a design choice. If a bug is found after evaluation, the fix is reported as a post-hoc rerun.

## Cases and episodes
- 21 leg-loss cases: 6 single legs and 15 pairs (R1,R2,R3,L1,L2,L3; indices 0-5). Leg(s) disabled at t = 4.0 s, flat terrain, 14 s episode, commanded speed 0.25 m/s, 10 seeds each (the existing `dl_*` scenarios).
- "Survives" on a seed: no fall by 14 s.

## Controllers (rows of the matrix)
plain tripod; tuned tripod (pitch feedback, kp 1.2, no healing); tuned tripod + healing v1 (the current repo healer); tuned tripod + healing v2 Tier A; tuned tripod + healing v2 Tier B; PPO residual (single reference model, `models/ppo_residual.zip`, no healing); oracle row (Stage 2 gaits, faults from t=0, 15 s, an upper bound with different conditions, shown separately and never counted as a controller).
- Healing v2 Tier A: offline gait library built from tuning-seed search, looked up by the detected fault set. Upper-bound style result, not online learning.
- Healing v2 Tier B: online search after detection with a fixed deterministic sim-time budget. Budget cap fixed now: at most 60 candidate rollouts, each charged 0.075 s of simulated time (4.5 sim-s) as in v1; the cap may be lowered during tuning, never raised after seeing eval data. No wall-clock budget.
- Search space for v2 (both tiers): per-leg phase offsets, duty cycle, amplitude, leg lift (the free-gait family in `src/neurowalker/freegait.py`).

## Primary metric
N_surv(controller) = number of the 21 cases in which the controller survives on at least 7 of 10 seeds. Secondary per case: survival with Wilson 95% interval, time-to-fall, speed-tracking error (RMSE of 1 s-window forward speed vs 0.25 m/s over t in [4, 14] s, with speed counted as 0 after a fall).

## Gap and "closes the gap" (defined now)
- Reference gap: G(controller) = 17 - N_surv(controller), where 17 is the number of cases whose oracle gait holds up in Stage 2 (MEASURED). Gap is reported before (healing v1) and after (Tier A, Tier B).
- "Closes the gap" requires BOTH: (1) Tier B gets at least 3 more cases than tuned tripod + healing v1 in N_surv, and (2) the 95% paired bootstrap CI of that difference excludes zero (10,000 resamples of the 10 seeds jointly across all cases, seed-matched).
- Tier A is reported separately and is never used to claim closure. If Tier B does not meet (1) and (2), the verdict is "no closure", whatever Tier A shows.

## Healing diagnostics (reported, not gated)
Fault-identification accuracy (exact set of legs), detection time, false-positive rate on healthy runs (seeds 0-9 healthy episodes, healing on), and a diagnosis of every case where v2 or v1 lowers survival versus its no-healing counterpart (e.g. R2+L3).

## What would count against me
Closure not met; v2 lowering survival in more cases than it raises; false positives on healthy runs above 1 of 10; Tier B needing a budget above the cap.
