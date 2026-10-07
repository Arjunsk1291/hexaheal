> Recovery note (simulation): this is the original measured report. Some linked raw v3 files were lost; see RECOVERY_20261007.md.

# HexaHeal v3 results

**Everything here is MuJoCo simulation on a 2 vCPU sandbox. Nothing is hardware.** Tags: MEASURED = from a result file in `results/v3/` (seeds 0-9 for evaluation, seeds 100-109 for tuning only); GUESS = my estimate; UNKNOWN = not measured. Protocol was fixed before the runs: `docs/PREREGISTRATION_V3.md`. No result was dropped.

## What changed from the earlier numbers from the first metric
The first metric meant no fall by 14 s. v3 splits it: **upright** = no fall; **recovered** = upright AND at least 0.125 m/s (50% of 0.25 m/s) over the last 8 s. A robot that stays on its feet but stops walking is upright, not recovered.

## Headline (MEASURED, seeds 0-9, 21 leg-loss cases, case counts when held on at least 7 of 10 seeds)
| controller | N_recovered | N_upright | upright runs that are standing still (of 210) |
|---|---|---|---|
| plain tripod | 0 | 6 | 75 of 75 |
| tuned tripod | 0 | 6 | 58 of 61 |
| healing v1 | 0 | 4 | 47 of 54 |
| healing v2 Tier A (offline library; upper-bound style) | 12 | 13 | 13 of 128 |
| healing v2 Tier B (online search; the realistic one) | 6 | 12 | 54 of 123 |
| PPO reference | 1 | 12 | 107 of 117 |
| oracle (offline upper bound, different conditions) | 15 | 18 | 26 of 190 |

Paired bootstrap (10,000 resamples of the 10 seeds): Tier B minus plain tripod = **+6 recovered [+4, +8]** and **+6 upright [+3, +7]**. Healing v1 minus plain tripod: +0 recovered [0, +1], **-2 upright [-4, -1]** (it lowered results). Tier B minus PPO: +5 recovered [+3, +7], +0 upright [-2, +3]. Tier A minus Tier B: +6 recovered [+4, +8], +1 upright [-1, +2].

Gap to the oracle (recovered): 15 minus N: Tier B 9, Tier A 3, tuned tripod 15, v1 15. Full matrices (both definitions, Wilson intervals, standing-still counts per case): `docs/V3_stage1.md`.

## Claims register
| # | claim | status | evidence |
|---|---|---|---|
| 1 | Most runs counted as successes in the old matrix were standing still, not walking (plain tripod, tuned tripod, v1, PPO) | SUPPORTED | 75/75, 58/61, 47/54, 107/117 upright runs below 0.125 m/s (MEASURED) |
| 2 | v2 Tier B recovers more cases than plain tripod | SUPPORTED | +6 [+4, +8] recovered; +6 [+3, +7] upright |
| 3 | v2 Tier B recovers as many cases as the offline library (Tier A) | NOT SUPPORTED | A is +6 [+4, +8] recovered; Tier B stands still in 54 upright runs |
| 4 | Tier B closes the gap to the oracle | NOT SUPPORTED | 6 vs 15 recovered (gap 9); not met under either metric |
| 5 | Tier B beats the PPO reference | PARTIAL | +5 recovered (PPO mostly stands still); tie on upright, CI includes 0 |
| 6 | Healing v1 lowers results | SUPPORTED (upright) | -2 [-4, -1]; on recovered it is flat (0 vs 0) |
| 7 | A "do no harm" rule removes the v2 regressions | NOT SUPPORTED | made things worse on tuning seeds: 2 vs 6 recovered cases (`docs/V3_stage2.md`) |
| 8 | A steady-state search fitness fixes Tier B standing still | NOT SUPPORTED | 45 vs 77 recovered runs on tuning seeds |
| 9 | Recovery depends on how fast healing starts | SUPPORTED on the swept grid | pooled recovered 55% at 0 s, 44% at 0.4 s, 30% at 1.0 s, 15% at 1.5 s (10 cases x 10 seeds); plain tripod 0% |
| 10 | There is a tolerable delay (pooled recovered at least 0.7) | NOT SUPPORTED | no swept delay reaches 0.7, even 0 s (55%) |
| 11 | v2 Tier B generalizes to other fault types | NOT SUPPORTED (no added value) | locked femur / 30% torque: plain tripod 12/12 cases, tuned and v2 11/12; v2 detects locks, never 30% torque |
| 12 | Results transfer to hardware, rough terrain, other speeds | UNKNOWN | not tested |
| 13 | The oracle failures prove those cases are physically impossible | UNKNOWN | search failure only |

## What failed (same prominence as what worked)
- Do-no-harm rule (round 1) lowered recovered cases from 6 to 2 on tuning seeds: its 1 s watch delays healing and the front-leg cases fall. It almost never fired usefully, because the tuned tripod walks in only 1 of 21 cases after a fault.
- Steady-state fitness (round 2) lowered recovered runs from 77 to 45 on tuning seeds. Cause UNKNOWN (GUESS: short model rollouts reward gaits that stall later).
- The old R2+R3 and L2+L3 "regressions" were not walking regressions: the tuned tripod only stood still there.
- Tier B is half standing still (54 of 123 upright runs). Never recovered by any controller: R1+R2, R1+L1, R2+R3, L1+L2, R3+L3, L2+L3. R3+L1: the oracle walks it (10/10), every controller 0-1/10.
- Healing v1 never recovers any case under the new definition and loses 2 upright cases to the tuned tripod.
- On the second fault type v2 added nothing, and R3 femur lock stays at 0/10 recovered for tuned and v2.
- Front-leg faults are latency-limited: R1 and L1 go to 0/10 recovered at a 0.2 s delay (Stage 3).
- Stage 3 faults were chosen from tuning-seed results as cases where healing can work, so the curve is optimistic about healing, not about the robot in general.
- Open from Stage 2 and not fixed: Tier B noise on R1 and R1+R3.

## Stages
- Stage 1: `docs/V3_stage1.md`. Stage 2: `docs/V3_stage2.md` (two negative tuning rounds, config frozen, final seeds-0-9 run reproduces exactly). Stage 3: `docs/V3_latency.md`, `docs/media_v3/latency_curve.png`. Stage 4: `docs/V3_fault2.md`.
- Reproduce: `make reproduce-v3` (rebuilds every table from the committed results, about a minute) or `bash scripts/reproduce_v3.sh full` (hours on 2 vCPU; deterministic).
- Earlier docs that use the first metric (`docs/RESULTS_HexaHeal_v2_survival.md`, `hh_tables.md`, `hh_ablation.md`) now carry a banner: there it means upright.
