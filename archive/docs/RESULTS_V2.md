# NeuroWalker RESULTS_V2

All numbers are SIMULATION (MuJoCo) on a 2 vCPU sandbox, final evaluation seeds 0-9 (10 per cell), read from results/v2_*_0-9.jsonl and docs/v2_tables.md. Seeds 100-109 were used only for tuning and debugging. The controller is "connectome-inspired": a spiking network wired from fly connectome data driving a hexapod CPG. It is not an emulation of a fly. ROS 2 and Docker were not verified. Nothing here is measured on any physical GPU or robot.

Statistics (Stage 5): paired bootstrap on per-seed differences (same seed in both arms), 100,000 resamples of the 10 differences, percentile 95% CI, rng seed 12345, Holm correction across each table family, d_z effect size, Wilson 95% intervals for falls. The v1 ci95 was the Student-t half-width t(0.975, 9) * sd / sqrt(10); it was verified as that formula in scripts/make_report.py. Distances are per scenario length, so they compare controllers within a cell, not across cells (fault and healthy+healing cells run longer).

## 1. Tables: mean distance m (falls/10), seeds 0-9

PPO below is training seed 0 only (models/ppo_residual.zip); the 5-training-seed mean is in table 1b.

| cell | tripod | tuned tripod | connectome | shuffled | random graph | filter | MLP | PPO s0 |
|---|---|---|---|---|---|---|---|---|
| flat | 2.63 (0) | 2.62 (0) | 2.76 (0) | 2.38 (0) | 2.49 (0) | 2.27 (0) | 2.97 (0) | 1.44 (0) |
| rough1 | 2.68 (0) | 2.65 (0) | 2.78 (0) | 2.38 (0) | 2.48 (0) | 2.28 (0) | 2.91 (0) | 1.51 (0) |
| rough3 | 2.62 (0) | 2.58 (0) | 2.73 (0) | 2.38 (0) | 2.45 (0) | 2.29 (0) | 2.85 (0) | 1.55 (0) |
| push 48 N | 2.02 (5) | 1.68 (6) | 2.23 (5) | 1.35 (8) | 1.62 (7) | 1.32 (8) | 2.34 (5) | 0.83 (10) |
| slope10 | 2.15 (0) | 2.09 (0) | 1.56 (3) | 2.00 (1) | 2.20 (0) | 2.09 (0) | 1.11 (5) | 1.58 (0) |
| slope15 | 0.19 (8) | 1.96 (0) | -0.09 (10) | not run | not run | not run | not run | 1.49 (0) |
| slope20 | -0.12 (10) | -0.10 (10) | -0.08 (10) | not run | not run | not run | not run | 1.22 (0) |
| disable_leg (no heal) | 1.70 (10) | 2.65 (7) | 1.31 (10) | not run | not run | not run | not run | 2.35 (0) |
| disable_leg + healing | 2.42 (3) | 2.85 (4) | 1.32 (10) | 1.91 (6) | 1.69 (8) | 1.42 (8) | 1.43 (10) | 2.40 (1) |
| lock_joint + healing | 2.80 (0) | 2.19 (0) | 3.64 (0) | 3.18 (0) | 3.34 (0) | 3.08 (0) | 3.64 (0) | 1.80 (0) |
| sensor_dropout + healing | 3.70 (0) | 3.67 (0) | 3.93 (0) | 3.34 (0) | 3.49 (0) | 3.17 (0) | 4.15 (0) | 0.87 (0) |
| fault_sequential | 1.57 (10) | 2.31 (10) | 1.31 (10) | not run | not run | not run | not run | 1.67 (10) |
| fault_sequential + healing | 1.77 (10) | 2.36 (10) | 1.32 (10) | not run | not run | not run | not run | 1.80 (10) |
| healthy + healing | 3.70 (0) | 3.67 (0) | 3.93 (0) | not run | not run | not run | not run | 1.18 (0) |

Wilson intervals for every falls/10 are in docs/v2_tables.md (0/10 = 0.00-0.28, 5/10 = 0.24-0.76, 10/10 = 0.72-1.00). With n=10 a 0/10 and a 3/10 are not well separated.

Paired CIs, connectome minus other, distance in m [95% CI] (full list incl. d_z and Holm p: docs/v2_tables.md and results/v2_stats.json):

| cell | shuffled | random graph | filter | MLP |
|---|---|---|---|---|
| flat | +0.376 [+0.321,+0.422] | +0.266 [+0.205,+0.325] | +0.489 [+0.437,+0.537] | -0.213 [-0.267,-0.164] |
| rough1 | +0.403 [+0.365,+0.450] | +0.304 [+0.266,+0.345] | +0.495 [+0.467,+0.526] | -0.126 [-0.175,-0.075] |
| rough3 | +0.349 [+0.308,+0.392] | +0.275 [+0.235,+0.315] | +0.437 [+0.408,+0.466] | -0.125 [-0.160,-0.091] |
| push | +0.882 [+0.293,+1.543] | +0.612 [+0.127,+1.261] | +0.915 [+0.358,+1.559] | -0.105 [-0.167,-0.042] |
| slope10 | -0.433 [-1.127,+0.192] | -0.635 [-1.325,+0.004] | -0.531 [-1.208,+0.110] | +0.448 [-0.412,+1.336] |
| disable_leg+healing | -0.593 [-1.041,-0.162] | -0.371 [-0.754,-0.046] | -0.095 [-0.513,+0.226] | -0.107 [-0.168,-0.046] |
| lock_joint+healing | +0.469 | +0.307 | +0.563 | +0.007 [-0.111,+0.146] |
| sensor_dropout+healing | +0.592 | +0.447 | +0.763 | -0.221 [-0.279,-0.169] |

Connectome minus tripod: flat +0.125 [+0.072,+0.175]; slope10 -0.586 [-1.287,+0.061]; slope15 -0.283 [-0.721,+0.023]; push +0.209 [-0.391,+0.812] (not different from zero). Connectome minus tuned tripod: flat +0.144 [+0.094,+0.191]; slope15 -2.053 [-2.234,-1.849]; disable_leg+healing -1.527 [-1.920,-1.143]; push +0.553 [-0.268,+1.362] (includes zero).

### 1b. PPO across 5 training seeds (seed 0 + seeds 1-4), each evaluated on eval seeds 0-9
Mean of the 5 per-training-seed mean distances, sd across training seeds, min-max, falls over all 50 episodes:
flat 1.878 (sd 0.322; 1.438-2.265; 0/50); rough3 1.902 (0.273; 1.554-2.246; 0/50); push 1.530 (0.765; 0.826-2.526; 28/50); slope10 1.732 (0.121; 0/50); slope15 1.530 (0.066; 0/50); slope20 1.193 (0.178; 0/50); disable_leg+healing 1.731 (1.102; 0.397-2.665; 2/50); lock_joint+healing 1.924 (0.936; 0/50); sensor_dropout+healing 2.399 (0.898; 0/50). All other cells are in docs/v2_tables.md. PPO is slow (about 1.9 m on flat vs 2.6-3.0 m for the CPG controllers) and varies a lot between training seeds on fault cells, so single-seed PPO numbers from v1 should not be quoted.

### 1c. Nudge magnitude (mean abs per control step, connectome)
speed_gain 0.2695, freq_scale 0.1667, turn 0.1537, stance 0.0335. Per variant: docs/v2_tables.md. The turn channel differs most (connectome and shuffled 0.14-0.15, filter 0.04).

## 2. Verdict against docs/PREREGISTRATION.md

Rule 1, "connectome wiring matters": the connectome had to beat ALL of shuffled, random graph, filter and MLP on flat, rough1 and rough3 distance, with paired 95% CIs excluding zero and an effect above 0.1 m. It beats shuffled, random graph and filter. It LOSES to the MLP on all three cells (-0.213, -0.126, -0.125 m; CIs exclude zero in the wrong direction). Verdict in plain words: NO EVIDENCE THE WIRING MATTERS under the rule as written.
Honest reading: the MLP was fit to imitate the connectome's own input-output behaviour, so the result says the function the connectome computes can be reproduced by a tiny network, and that a scrambled or random graph computes a worse function. It does not show the real structure is useless, and it does not show it is needed. Post-hoc, not pre-registered: distance rewards overshooting the 0.25 m/s target. Mean flat speed is MLP 0.297, connectome 0.276, tripod 0.2635, random graph 0.249, shuffled 0.238, filter 0.227. By absolute speed-tracking error the random graph is best (0.003) and the connectome is worst after the MLP (0.026 vs MLP 0.047). So "walks farther" is not the same as "tracks the command better".

Rule 2, "healing works on sequential faults": needed detection of the second fault in at least 8/10 seeds and no more falls than the single-fault healing cell. Second-fault detection (detect2_s) occurred where a robot was still upright (tripod 0.340 s, PPO 0.292 s after the second fault), but all controllers fall in 10/10 sequential episodes with or without healing, and the connectome falls ~6.5 s after the first fault, before the second one happens. Verdict: NOT MET. Detection works; recovery does not (0 of 30 baseline sequential-healing episodes survive). On the single-fault disable_leg+healing cell the connectome falls 10/10.
The healthy+healing cell had 0 false alarms in 30/30 episodes.

Rule 3 (tuned tripod): reported honestly. A one-parameter analytic pitch-feedback tripod (kp=1.2, tuned on seeds 100-109 only) has 0/10 falls on slope15 where the connectome falls 10/10 and the plain tripod 8/10, and it is far ahead of the connectome on disable_leg+healing distance (+1.53 m) although it still falls 4/10 there. It beats the connectome on slopes and on that fault; the connectome beats it by 0.14 m on flat. No learned or connectome controller beats this simple baseline on slopes.

## 3. Claims register (rebuilt from v2 data)

- SUPPORTED: v2 results are reproducible (3 idle + 3 loaded runs bit-identical, results/repro_check.json) after the fixes.
- SUPPORTED: healthy robot triggers no false healing alarms (0/30).
- SUPPORTED: the real connectome walks farther on flat/rough than shuffled, random-graph or filter variants (all CIs exclude zero, all above 0.1 m).
- NOT SUPPORTED: "the connectome wiring matters" (MLP beats it; pre-registered rule fails).
- NOT SUPPORTED: "healing helps" (v1 claim), "healing handles sequential faults", or "the connectome keeps most of its speed with a disabled leg" (all from contaminated v1 data; v2 shows 10/10 falls for the connectome).
- PARTIAL: second-fault detection works while upright; recovery does not.
- PARTIAL: on push, the connectome has the highest distance among CPG variants except MLP, but falls 5/10 like tripod and MLP (CIs vs tripod include zero).
- NOT SUPPORTED: connectome robustness on slopes (slope10 3/10 falls, slope15 10/10); a tuned tripod does better.
- PARTIAL: PPO is robust to slopes and lost legs (0 falls on slopes, 0/50 falls on most fault cells) but is slow and varies a lot between training seeds.
- NOT TESTED: any claim about real hardware, a GTX 1660 Ti, ROS 2 or Docker.

## 4. Final answers

Does the connectome wiring matter? Not by the rule I wrote before running anything. It beats scrambled wiring, random graphs and a no-network filter, but a small MLP imitating it beats it on flat/rough distance. Say "connectome-inspired controller whose function a small network can reproduce", not "the wiring matters".

Does the healing layer work on sequential faults? Detection works, recovery does not: 0/30 survive the sequential cell, and the connectome never gets a verified recovery.

## 5. v1 contamination (state leak)

In v1 the healing search mutated the shared controller's CPG parameters and leg_stride_scale, so later episodes on the same controller object inherited the searched gait (demo: tripod seed 101, x at 4 s was 1.0175 fresh vs 1.3329 after one healing episode). Fix: the wrapper applies its gait only inside its own act() and restores the base gait; the wall-time search budget was also replaced with a simulated-time budget (0.075 s per trial). Deterministic check: connectome disable_leg+healing seed 8 gave bit-identical results over 3 idle + 3 loaded runs and FALLS at 6.5 s; v1 had it surviving.
Invalidated: all v1 "+healing" cells, and any v1 cell run after a healing episode on the same controller object, including the 30/38/49% numbers on carousel slide 6 and post 3, the "38% speed kept" claim and "healing helps". These must not be quoted.

## 6. What went wrong or could not be run

- The v1 healing contamination above, and the numba-less sandbox (SNN pure Python, 420-450 ms per step; the v4 media were rendered that way). Installing numba 0.68.0 gave about 100x speedup.
- The v1 story video attempts fell (6.1 s and 6.5 s); no recovery footage exists; video is parked.
- Variants shuffled, random graph, filter and MLP were run only on the 8 ablation cells; they were not run on slope15/20, plain disable_leg or sequential cells.
- PPO training used 1,180,000 steps per seed; 5 training seeds total (spread is large on fault cells, only 10 eval seeds each).
- The MLP is a stateless fit to connectome outputs on random inputs; a better-trained or recurrent MLP might behave differently.
- n = 10 seeds per cell gives wide CIs; slope10 and push comparisons are inconclusive.
- Pre-existing ruff F841 in scripts/make_story.py (old file). ROS 2 and Docker remain UNVERIFIED.
