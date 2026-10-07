# HexaHeal v3 pre-registration (committed before any v3 result exists)

Everything here is MuJoCo simulation on a 2 vCPU sandbox. Nothing is hardware. This file is protocol, not results. Every number later reported carries a tag: MEASURED (from a result file in `results/`), GUESS (my estimate), or UNKNOWN. **No result will be dropped**: every run that is made is reported, including failures and negative results, with the same prominence as positive ones.

## Data discipline (unchanged)
Tuning and every design choice: seeds 100-109 only. Final evaluation: seeds 0-9 only, each final configuration run once. If a bug is found after evaluation, the fix is reported as a post-hoc rerun and labelled so. Local commits only, no push.

## Stage 1 - the "recovered" definition (fixed now)
Episode: fault at t = 4.0 s, flat ground, 14 s, commanded 0.25 m/s (as before).
- **upright** = no fall during the 14 s episode.
- **recovered** = upright AND mean forward speed over the last 8 s of the episode (t in [6, 14] s) is at least 50% of 0.25 m/s, i.e. (x(14) - x(6)) / 8 >= **0.125 m/s**. A run that fell is never recovered.
- **standing still** = upright but not recovered (speed below 0.125 m/s over the last 8 s). Counted per case.
- A case is "recovered" (resp. "upright") for a controller if it is so on at least 7 of 10 seeds. N_recovered and N_upright = number of the 21 cases (6 single, 15 double leg losses) meeting that.
- All 7 rows (plain tripod, tuned tripod, healing v1, v2 Tier A, v2 Tier B, PPO reference, oracle) are re-run on seeds 0-9 with the final-8-s speed logged, then scored with both definitions. Both matrices are published. The oracle row is re-run on seeds 0-9 with the same rule (it keeps its different conditions: faults from t = 0, 15 s episode with the last 8 s window t in [7, 15]; it is an upper bound, not a controller).
- Headline comparison: plain tripod vs healing v2 Tier B, N_recovered and N_upright, paired bootstrap 95% CI (10,000 resamples of the 10 seeds jointly across cases, seed-matched). v1 stays as its own row with the note that it lowered results.
- Earlier "survives" claims are renamed "stays upright" unless re-scored as recovered.

## Stage 2 - weak-spot fixes (time-boxed)
Targets: v2 below plain tripod on R2+R3 and L2+L3; Tier B noise on R1 and R1+R3; R3+L1 (oracle walks, controllers 0-1/10). At most **2 tuning rounds on seeds 100-109, then freeze**. A "do no harm" rule is tested: after the fault is confirmed, if the current gait is still working (forward speed over the last 1.5 s at least 50% of 0.25 m/s AND body pitch within the existing fall-margin limit) the gait is not replaced. Speed/pitch thresholds are fixed before round 1 and are not tuned beyond the 2 rounds. The final configuration is run once on seeds 0-9. Every change is reported, including those that did not help. Ablation (rule on/off) is on tuning seeds.

## Stage 3 - latency sweep
- Faults: the 6 single-leg losses plus 4 double losses chosen by this fixed rule: among the 15 pairs, the 4 with the most Tier B survivors on tuning seeds 100-109 (file `results/hh_tune_B_b60.jsonl`), ties to the lowest case index. Applying it now gives **R1+L2 (dl_0_4), R1+L3 (dl_0_5), R2+L1 (dl_1_3), R2+L2 (dl_1_4)** (all 10/10 upright on tuning seeds). This is a stated bias: the pairs where healing can work.
- Artificial response delay before healing starts (added to the detection-to-plan time): 0, 0.2, 0.4, 0.7, 1.0, 1.5 s. Seeds 0-9. Controllers: healing v2 Tier B (final Stage 2 config) and plain tripod (no healing, so no delay applies; its flat line is measured once per case and shown as the reference).
- Metric: recovered fraction (Stage 1 definition) versus delay, pooled over the 10 cases x 10 seeds, with Wilson 95% intervals; also per-case curves and upright fraction. Measured detection time is marked.
- "Tolerable delay" = the largest swept delay whose pooled recovered fraction is at least 0.7, stated as a swept grid point (no interpolation claim), plus plain words.

## Stage 4 - second fault type
Faults on the single legs only (subset stated): (a) femur joint locked at its current angle at t = 4 s; (b) leg torque reduced to 30% at t = 4 s; legs R1..L3, 12 cases x 10 seeds, seeds 0-9, controllers plain tripod, tuned tripod and v2 Tier B (final config, unchanged, no tuning on these faults; its detector was built for leg loss and may not detect them). Reported as measured with both definitions. If v2 does not generalize, that is the result.

## Claim rules (decided now)
- "A beats B" on N_recovered: SUPPORTED if the paired bootstrap 95% CI of the difference excludes zero in A's favour; PARTIAL if the point estimate favours A with CI including zero; NOT SUPPORTED otherwise (including if B is better). Per-case claims need Wilson intervals that do not overlap, else PARTIAL.
- Latency claim: SUPPORTED only for the swept grid and the pooled set of 10 cases. Anything about other faults, terrain, or hardware is UNKNOWN.
- Gap to oracle: reported with the oracle row from the same rule; "closes the gap" needs at least 3 more recovered cases than the reference with a CI excluding zero (as in the earlier pre-registration).
- Claims on hardware, ROS 2, GPU or real-time performance: UNKNOWN.
