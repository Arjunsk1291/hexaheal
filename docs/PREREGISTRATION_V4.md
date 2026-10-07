# HexaHeal v4 pre-registration (committed before any v4 run)

MuJoCo simulation on a 2 vCPU sandbox; nothing here is hardware. Every number later reported is tagged MEASURED, GUESS or UNKNOWN. No result will be dropped. Local commits only. Vocabulary: **upright** = no fall; **recovered** = no fall AND at least 0.125 m/s over the last 8 s of the episode (docs/PREREGISTRATION_V3.md); **standing still** = upright but not recovered. Tuning seeds 100-109, evaluation seeds 0-9, simulated time only.

## Hypothesis (one principled improvement)
Warm-starting the online CMA-ES search of healing v2 Tier B from the nearest gait in the offline library raises the number of recovered cases above Tier B (6 of 21, MEASURED in v3) at the same budget (at most 60 rollouts x 0.075 simulated seconds).

## Warm-start controller ("Tier B+")
- Identical to Tier B (frozen v3 config in `results/v3/v2_config_final.json`: detector, stand-while-planning, search space, popsize 6, sigma0 0.25, 60 trials, 3 s rollouts) except the CMA-ES start point x0: instead of the fixed tripod-like default, x0 is the library gait whose failed-leg set is nearest to the DIAGNOSED set. Starting point is evaluated as trial 1 and counts against the 60 trials (as the default x0 did). No other change; no new hyperparameters; sigma0 and population size are not tuned.
- **Library, leave-one-case-out.** The library is the Stage 2 oracle search results (best search fitness on tuning seeds 100-101 per case, files `results/v3_oracle*.jsonl`), so it contains only tuning-seed information. For an evaluation episode whose true failed set is S, the entries for S and for its left-right mirror are removed from the library before lookup (mirror maps legs R1,R2,R3,L1,L2,L3 to L1,L2,L3,R1,R2,R3). The evaluation harness passes S to the library filter only; the controller never sees S in any other way.
- **Nearest** = smallest size of the symmetric difference between the diagnosed set D and a library entry's failed set; ties go to the entry earliest in the canonical case order (R1..L3, then pairs in lexicographic order). If the diagnosis is empty nothing is planned (as before).
- No tuning is allowed for Tier B+. A bug-finding smoke test on tuning seeds is allowed; its results are not used to choose anything. Tier B+ is run once on seeds 0-9, 21 cases x 10 seeds.

## Decision rule (fixed now)
The warm start counts as an improvement only if Tier B+ gets **at least +2 recovered cases versus Tier B** (N_recovered of at least 8 against 6) AND the paired bootstrap 95% CI of that difference (10,000 resamples of the 10 seeds jointly across cases, seed-matched, rng seed 0) excludes zero. Otherwise the verdict is "no gain", reported at equal prominence. Also reported, not gating: recovered, upright and standing-still per case; the same difference versus the plain tripod; upright counts with CIs.

## Stand-still diagnostic for Tier B (v3 config, seeds 0-9)
Per case, from the same runs: (1) time spent standing before the new gait starts = time from the diagnosis (PLAN state) to RUN state, taken from the controller log; (2) time to the first recovered step = first time t after the fault such that the mean forward speed over [t, t+2 s] is at least 0.125 m/s with no fall (reported as "never" if none); (3) the fraction of upright runs that never walk = upright runs with last-8 s speed below 0.125 m/s. For each stage of the pipeline (detect, plan, switch, walk) the cause of standing still is labelled MEASURED when a logged quantity shows it and GUESS otherwise.

## Latency sweep
If Tier B+ passes the rule, re-run the v3 sweep for it: delays 0, 0.2, 0.4, 0.7, 1.0, 1.5 s on the same 10 cases (6 single legs + R1+L2, R1+L3, R2+L1, R2+L2), seeds 0-9. Those 10 cases were chosen from tuning-seed results as cases where healing can work (a stated bias). If it does not pass, the Tier B sweep from v3 stays as the reported curve.

## Claims
A claim is SUPPORTED only if its paired bootstrap CI excludes zero in the stated direction; PARTIAL if only the point estimate favours it; NOT SUPPORTED otherwise. Anything about hardware, other terrain, other faults or other speeds is UNKNOWN. Words "solved", "novel", "state of the art" are not used.
