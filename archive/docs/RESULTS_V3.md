# NeuroWalker RESULTS_V3

All numbers are SIMULATION (MuJoCo hexapod) on a 2 vCPU sandbox, final evaluation on seeds 0-9 (10 per cell), read from results/v2_*_0-9.jsonl and results/v3_*.jsonl. Anything tuned (tuned-tripod gains, hybrid nudge scales and pitch gate) was tuned on seeds 100-109 only. The controller is "connectome-inspired", not an emulation of a fly. ROS 2 and Docker are unverified. No claims about any physical GPU or robot. Statistics: paired bootstrap on per-seed differences, 100,000 resamples, percentile 95%, rng seed 12345; Wilson 95% intervals for falls. Local-only until pushed; all code is in the repo (scripts/stage1_v3.py, stage2_v3.py, stage3_v3.py, oracle_v3.py, stage4_v3.py, stage4_stats_v3.py, plan_v3.py, map_v3.py).

## Summary (what the data say)

1. Stage 1, claims register fixed: healing DOES help the plain tripod on a single disabled leg (falls 10/10 -> 3/10, Wilson 0.72-1.00 vs 0.11-0.60, distance +0.714 m [+0.323,+1.104]). It is NOT established for the tuned tripod (7/10 -> 4/10, Wilson intervals overlap, distance +0.203 m [-0.233,+0.649]) and does nothing for the connectome (10/10 -> 10/10).
2. Stage 2, why the connectome fails with healing: the connectome's own speed/frequency nudges, not the CMA-ES gait. Healed gait with nudges off: 3/10 falls (identical to tripod+healing); nudges clipped: 5/10; nudges halved: 9/10; unmodified: 10/10; CMA-ES run on the real connectome-driven controller: 10/10 (no gain). Per-channel (tuning seeds): speed+freq alone 10/10 falls, turn alone 5/10, stance alone 3/10.
3. Stage 3, recovery map: with healing, survival of leg losses depends mostly on WHICH leg. Healing helps the plain tripod in some cases and hurts in others. A free-gait oracle shows most double faults are physically walkable in this simulator, so most failures are planner/gait-family limits, not physics. See section 3 for the exact list.
4. Stage 4, hybrid: no overall win over a tuned tripod. It wins push recovery (falls 1/10 vs 6/10), is slightly ahead on flat/rough1/slope15 distance (mostly speed overshoot), ties 5 cells and loses single-leg+healing (8/10 vs 4/10 falls) and sequential-fault survival time.
5. Stage 5: video evidence plan only; nothing rendered.

## Stage 1: the record, fixed

Corrections to RESULTS_V2: (a) the sentence "healing does not help" is replaced by the cell-specific finding above; (b) falls now carry Wilson intervals; (c) every cell reports time-to-fall and speed-tracking error next to distance. Distance rewards walking faster than the 0.25 m/s command: the MLP and connectome have the largest distances partly because they overshoot, while the random graph tracks speed best (error 0.003). Speed error here is |episode mean speed - 0.25| m/s and is only meaningful on cells where the robot is meant to walk at the command speed (flat, rough, healthy); on slopes and faults it also includes the physical slowdown.

Columns: falls/10 (Wilson 95%); mean survival time s (t_end; = scenario length if no fall; censored); mean time-to-fall s among fallen episodes (n); speed error = mean |mean_speed - 0.25| m/s; distance m. 'ppo' = training seed 0 only.

| cell | controller | falls/10 (Wilson) | mean survival s | time-to-fall s (n fallen) | speed err m/s | distance m |
|---|---|---|---|---|---|---|
| flat | tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0135 | 2.635 |
| flat | tuned_tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0116 | 2.616 |
| flat | connectome | 0/10 (0.00-0.28) | 10.00 | - | 0.0260 | 2.760 |
| flat | shuffled | 0/10 (0.00-0.28) | 10.00 | - | 0.0116 | 2.384 |
| flat | random_graph | 0/10 (0.00-0.28) | 10.00 | - | 0.0027 | 2.494 |
| flat | filter | 0/10 (0.00-0.28) | 10.00 | - | 0.0229 | 2.271 |
| flat | mlp | 0/10 (0.00-0.28) | 10.00 | - | 0.0473 | 2.973 |
| flat | ppo | 0/10 (0.00-0.28) | 10.00 | - | 0.1062 | 1.438 |
| rough1 | tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0179 | 2.679 |
| rough1 | tuned_tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0150 | 2.650 |
| rough1 | connectome | 0/10 (0.00-0.28) | 10.00 | - | 0.0280 | 2.780 |
| rough1 | shuffled | 0/10 (0.00-0.28) | 10.00 | - | 0.0123 | 2.377 |
| rough1 | random_graph | 0/10 (0.00-0.28) | 10.00 | - | 0.0024 | 2.476 |
| rough1 | filter | 0/10 (0.00-0.28) | 10.00 | - | 0.0216 | 2.284 |
| rough1 | mlp | 0/10 (0.00-0.28) | 10.00 | - | 0.0406 | 2.906 |
| rough1 | ppo | 0/10 (0.00-0.28) | 10.00 | - | 0.0986 | 1.514 |
| rough3 | tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0122 | 2.622 |
| rough3 | tuned_tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0088 | 2.583 |
| rough3 | connectome | 0/10 (0.00-0.28) | 10.00 | - | 0.0226 | 2.726 |
| rough3 | shuffled | 0/10 (0.00-0.28) | 10.00 | - | 0.0123 | 2.377 |
| rough3 | random_graph | 0/10 (0.00-0.28) | 10.00 | - | 0.0049 | 2.451 |
| rough3 | filter | 0/10 (0.00-0.28) | 10.00 | - | 0.0211 | 2.289 |
| rough3 | mlp | 0/10 (0.00-0.28) | 10.00 | - | 0.0351 | 2.851 |
| rough3 | ppo | 0/10 (0.00-0.28) | 10.00 | - | 0.0946 | 1.554 |
| push | tripod | 5/10 (0.24-0.76) | 8.28 | 4.56 (5) | 0.0118 | 2.022 |
| push | tuned_tripod | 6/10 (0.31-0.83) | 7.48 | 4.47 (6) | 0.0206 | 1.678 |
| push | connectome | 5/10 (0.24-0.76) | 8.20 | 4.40 (5) | 0.0211 | 2.231 |
| push | shuffled | 8/10 (0.49-0.94) | 5.96 | 4.45 (8) | 0.0273 | 1.350 |
| push | random_graph | 7/10 (0.40-0.89) | 6.69 | 4.42 (7) | 0.0123 | 1.620 |
| push | filter | 8/10 (0.49-0.94) | 5.97 | 4.46 (8) | 0.0310 | 1.317 |
| push | mlp | 5/10 (0.24-0.76) | 8.21 | 4.42 (5) | 0.0337 | 2.336 |
| push | ppo | 10/10 (0.72-1.00) | 4.36 | 4.36 (10) | 0.0605 | 0.826 |
| slope10 | tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0352 | 2.148 |
| slope10 | tuned_tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0413 | 2.087 |
| slope10 | connectome | 3/10 (0.11-0.60) | 7.38 | 1.27 (3) | 0.1021 | 1.563 |
| slope10 | shuffled | 1/10 (0.02-0.40) | 9.99 | 9.88 (1) | 0.0502 | 1.996 |
| slope10 | random_graph | 0/10 (0.00-0.28) | 10.00 | - | 0.0302 | 2.198 |
| slope10 | filter | 0/10 (0.00-0.28) | 10.00 | - | 0.0406 | 2.094 |
| slope10 | mlp | 5/10 (0.24-0.76) | 5.54 | 1.08 (5) | 0.1587 | 1.115 |
| slope10 | ppo | 0/10 (0.00-0.28) | 10.00 | - | 0.0924 | 1.576 |
| slope15 | tripod | 8/10 (0.49-0.94) | 3.31 | 1.64 (8) | 0.2917 | 0.190 |
| slope15 | tuned_tripod | 0/10 (0.00-0.28) | 10.00 | - | 0.0540 | 1.960 |
| slope15 | connectome | 10/10 (0.72-1.00) | 0.77 | 0.77 (10) | 0.3799 | -0.093 |
| slope15 | ppo | 0/10 (0.00-0.28) | 10.00 | - | 0.1013 | 1.487 |
| slope20 | tripod | 10/10 (0.72-1.00) | 0.58 | 0.58 (10) | 0.4638 | -0.123 |
| slope20 | tuned_tripod | 10/10 (0.72-1.00) | 0.75 | 0.75 (10) | 0.3856 | -0.101 |
| slope20 | connectome | 10/10 (0.72-1.00) | 0.43 | 0.43 (10) | 0.4417 | -0.083 |
| slope20 | ppo | 0/10 (0.00-0.28) | 10.00 | - | 0.1283 | 1.217 |
| fault_disable_leg | tripod | 10/10 (0.72-1.00) | 11.56 | 11.56 (10) | 0.1026 | 1.703 |
| fault_disable_leg | tuned_tripod | 7/10 (0.40-0.89) | 11.49 | 10.41 (7) | 0.0180 | 2.646 |
| fault_disable_leg | connectome | 10/10 (0.72-1.00) | 6.52 | 6.52 (10) | 0.0475 | 1.312 |
| fault_disable_leg | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.0822 | 2.349 |
| fault_disable_leg+healing | tripod | 3/10 (0.11-0.60) | 12.74 | 9.79 (3) | 0.0628 | 2.417 |
| fault_disable_leg+healing | tuned_tripod | 4/10 (0.17-0.69) | 11.95 | 8.87 (4) | 0.0187 | 2.849 |
| fault_disable_leg+healing | connectome | 10/10 (0.72-1.00) | 6.49 | 6.49 (10) | 0.0454 | 1.322 |
| fault_disable_leg+healing | shuffled | 6/10 (0.31-0.83) | 10.75 | 8.58 (6) | 0.0753 | 1.915 |
| fault_disable_leg+healing | random_graph | 8/10 (0.49-0.94) | 9.32 | 8.15 (8) | 0.0690 | 1.693 |
| fault_disable_leg+healing | filter | 8/10 (0.49-0.94) | 8.26 | 6.83 (8) | 0.0798 | 1.417 |
| fault_disable_leg+healing | mlp | 10/10 (0.72-1.00) | 6.47 | 6.47 (10) | 0.0287 | 1.429 |
| fault_disable_leg+healing | ppo | 1/10 (0.02-0.40) | 13.72 | 11.24 (1) | 0.0754 | 2.403 |
| fault_lock_joint | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.1563 | 1.311 |
| fault_lock_joint | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.1596 | 1.266 |
| fault_lock_joint | connectome | 0/10 (0.00-0.28) | 14.00 | - | 0.0298 | 3.083 |
| fault_lock_joint | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.0783 | 2.403 |
| fault_lock_joint+healing | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0502 | 2.798 |
| fault_lock_joint+healing | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0939 | 2.185 |
| fault_lock_joint+healing | connectome | 0/10 (0.00-0.28) | 14.00 | - | 0.0144 | 3.644 |
| fault_lock_joint+healing | shuffled | 0/10 (0.00-0.28) | 14.00 | - | 0.0232 | 3.175 |
| fault_lock_joint+healing | random_graph | 0/10 (0.00-0.28) | 14.00 | - | 0.0159 | 3.337 |
| fault_lock_joint+healing | filter | 0/10 (0.00-0.28) | 14.00 | - | 0.0299 | 3.082 |
| fault_lock_joint+healing | mlp | 0/10 (0.00-0.28) | 14.00 | - | 0.0125 | 3.637 |
| fault_lock_joint+healing | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.1215 | 1.799 |
| fault_sensor_dropout | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0143 | 3.700 |
| fault_sensor_dropout | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0122 | 3.671 |
| fault_sensor_dropout | connectome | 0/10 (0.00-0.28) | 14.00 | - | 0.0309 | 3.933 |
| fault_sensor_dropout | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.1823 | 0.948 |
| fault_sensor_dropout+healing | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0143 | 3.700 |
| fault_sensor_dropout+healing | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0122 | 3.671 |
| fault_sensor_dropout+healing | connectome | 0/10 (0.00-0.28) | 14.00 | - | 0.0309 | 3.933 |
| fault_sensor_dropout+healing | shuffled | 0/10 (0.00-0.28) | 14.00 | - | 0.0114 | 3.341 |
| fault_sensor_dropout+healing | random_graph | 0/10 (0.00-0.28) | 14.00 | - | 0.0023 | 3.486 |
| fault_sensor_dropout+healing | filter | 0/10 (0.00-0.28) | 14.00 | - | 0.0236 | 3.169 |
| fault_sensor_dropout+healing | mlp | 0/10 (0.00-0.28) | 14.00 | - | 0.0467 | 4.154 |
| fault_sensor_dropout+healing | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.1876 | 0.873 |
| fault_reduce_torque | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.1954 | 0.765 |
| fault_reduce_torque | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.1938 | 0.786 |
| fault_reduce_torque | connectome | 0/10 (0.00-0.28) | 14.00 | - | 0.1488 | 1.416 |
| fault_reduce_torque | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.2125 | 0.526 |
| fault_reduce_torque+healing | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.1345 | 1.617 |
| fault_reduce_torque+healing | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.1806 | 0.972 |
| fault_reduce_torque+healing | connectome | 1/10 (0.02-0.40) | 13.42 | 8.18 (1) | 0.0439 | 2.762 |
| fault_reduce_torque+healing | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.2013 | 0.682 |
| fault_sequential | tripod | 10/10 (0.72-1.00) | 9.61 | 9.61 (10) | 0.0864 | 1.572 |
| fault_sequential | tuned_tripod | 10/10 (0.72-1.00) | 9.80 | 9.80 (10) | 0.0145 | 2.305 |
| fault_sequential | connectome | 10/10 (0.72-1.00) | 6.52 | 6.52 (10) | 0.0475 | 1.312 |
| fault_sequential | ppo | 10/10 (0.72-1.00) | 10.87 | 10.87 (10) | 0.0967 | 1.665 |
| fault_sequential+healing | tripod | 10/10 (0.72-1.00) | 10.34 | 10.34 (10) | 0.0775 | 1.767 |
| fault_sequential+healing | tuned_tripod | 10/10 (0.72-1.00) | 10.37 | 10.37 (10) | 0.0229 | 2.355 |
| fault_sequential+healing | connectome | 10/10 (0.72-1.00) | 6.49 | 6.49 (10) | 0.0454 | 1.322 |
| fault_sequential+healing | ppo | 10/10 (0.72-1.00) | 10.74 | 10.74 (10) | 0.0817 | 1.801 |
| healthy+healing | tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0143 | 3.700 |
| healthy+healing | tuned_tripod | 0/10 (0.00-0.28) | 14.00 | - | 0.0122 | 3.671 |
| healthy+healing | connectome | 0/10 (0.00-0.28) | 14.00 | - | 0.0309 | 3.933 |
| healthy+healing | ppo | 0/10 (0.00-0.28) | 14.00 | - | 0.1657 | 1.180 |

## Healing effect on a single disabled leg (paired by seed, with minus without healing)

| controller | falls no-heal | falls heal | survival-time diff s [95% CI] | distance diff m [95% CI] |
|---|---|---|---|---|
| tripod | 10/10 (0.72-1.00) | 3/10 (0.11-0.60) | +1.18 [-0.13, +2.34] | +0.714 [+0.323, +1.104] |
| tuned_tripod | 7/10 (0.40-0.89) | 4/10 (0.17-0.69) | +0.46 [-1.58, +2.44] | +0.203 [-0.233, +0.649] |
| connectome | 10/10 (0.72-1.00) | 10/10 (0.72-1.00) | -0.03 [-0.10, +0.03] | +0.010 [-0.001, +0.023] |
| ppo | 0/10 (0.00-0.28) | 1/10 (0.02-0.40) | -0.28 [-0.83, +0.00] | +0.054 [-0.227, +0.336] |


## Stage 2: why the connectome fails with healing (disable_leg R3 at 4 s, healing on, seeds 0-9)

| variant | falls/10 (Wilson) | mean survival s | verified recoveries | survival diff vs unchanged connectome [95% CI] |
|---|---|---|---|---|
| unchanged connectome + healing | 10/10 (0.72-1.00) | 6.49 | 0/10 | - |
| (a) healed gait, nudges OFF | 3/10 (0.11-0.60) | 12.74 | 7/10 | +6.24 s [+4.72,+7.57] |
| (b1) nudges x0.5 | 9/10 (0.60-0.98) | 8.11 | 1/10 | +1.61 s [+0.53,+3.28] |
| (b2) nudges clipped (0.15/0.10/0.10/0.05) | 5/10 (0.24-0.76) | 10.92 | 5/10 | +4.42 s [+2.28,+6.51] |
| (c) CMA-ES run on the connectome-driven controller | 10/10 (0.72-1.00) | 6.50 | 0/10 | +0.01 s [-0.02,+0.05] |
| plain tripod + healing (reference) | 3/10 (0.11-0.60) | 12.74 | 7/10 | - |

Variant (a) is the plain tripod plus healing by construction, so it shows the nudges are the cause. Mechanism (seed 100 log): fault at 4.0 s, detection 4.4 s, diagnosis 5.06 s, healed gait applied at 6.52 s (0.4 s detect + 0.6 s diagnose + about 1.5 s simulated search time), but after the leg loss the robot slows, the speed-error nudge saturates speed_gain/freq_scale at 1.5/1.4, pitch reaches -0.5 to -0.9 rad and the robot tips before the healed gait is applied. The fix that works is switching the speed/frequency nudges off (or capping them hard); changing the search does not help. Channel test on tuning seeds 100-109 only (falls/10): speed+freq 10, turn only 5, stance only 3. Verdict: DIAGNOSED; fixed only by removing the nudges, which removes the connectome from the loop.

## Stage 3: recovery map and oracle

Setup: leg(s) disabled simultaneously at 4.0 s on flat ground, 14 s episodes, seeds 0-9. Legs: R1,R2,R3 right, L1,L2,L3 left. Controllers: plain tripod and tuned tripod, each without and with healing (6 single + 15 double cases = 840 episodes). Oracle: offline CMA-ES over an open-loop FREE gait (global frequency/stride/lift/duty/turn/stance + per-leg phase, stride and lift) with the faults active from t=0; fitness on seeds 100-101, validated on seeds 0-9 for 10 s; "walks" = no fall and >= 1.0 m on >= 8/10 validation seeds. A walking oracle gait is an EXISTENCE PROOF in this simulator that the fault is physically survivable. A non-walking oracle is NOT a proof of impossibility: it only means this search family and budget found nothing.

Oracle cases finished: 21/21. Walks (>=8/10 validation seeds, no fall, >=1.0 m in 10 s): R1, R2, R3, L1, L2, L3, R1+R3, R1+L2, R2+R3, R2+L1, R2+L2, R2+L3, R3+L1, R3+L2, L1+L3, L2+L3. Did not reach the walking criterion within the budget: R1+R2 (6/10 falls), R1+L1 (5/10 falls), R1+L3 (4/10 falls), R3+L3 (5/10 falls), L1+L2 (2/10 falls).

Longer-budget rerun (80 generations x 3 restarts, popsize 16) of the cases that did not walk: R1+R2: no walking gait found (2/10 survive, mean 0.89 m); R1+L1: no walking gait found (5/10 survive, mean 2.07 m); R1+L3: WALKS (10/10 survive, mean 4.52 m); R3+L3: WALKS (10/10 survive, mean 1.29 m); L1+L2: no walking gait found (5/10 survive, mean 1.64 m).

Survivors/10 (no fall by 14 s) for each case and the oracle result:

Survival = no fall by 14 s with leg(s) disabled at 4.0 s (cell = survivors/10). Oracle column: offline CMA-ES over a free-gait family, faults from t=0, validated on seeds 0-9 over 10 s (walks = no fall and >= 1.0 m on >= 8/10 seeds).

| case | tripod | tripod+heal | tuned | tuned+heal | healing recoveries (tuned+heal, mean/run) | oracle: survivors/10, mean dist m | oracle walks? |
|---|---|---|---|---|---|---|---|
| dl_0 | 1/10 | 10/10 | 0/10 | 0/10 | 0.0 | 10/10, 4.33 | YES |
| dl_1 | 10/10 | 10/10 | 10/10 | 10/10 | 0.0 | 10/10, 3.94 | YES |
| dl_2 | 0/10 | 7/10 | 3/10 | 6/10 | 0.8 | 10/10, 4.06 | YES |
| dl_3 | 0/10 | 0/10 | 0/10 | 0/10 | 0.0 | 10/10, 2.33 | YES |
| dl_4 | 10/10 | 10/10 | 10/10 | 10/10 | 0.0 | 10/10, 2.99 | YES |
| dl_5 | 0/10 | 0/10 | 0/10 | 0/10 | 0.0 | 10/10, 4.61 | YES |
| dl_0_1 | 0/10 | 0/10 | 0/10 | 0/10 | 0.0 | 4/10, 0.53 | NO |
| dl_0_2 | 0/10 | 2/10 | 0/10 | 0/10 | 0.0 | 10/10, 1.89 | YES |
| dl_0_3 | 0/10 | 0/10 | 0/10 | 0/10 | 0.0 | 5/10, 2.07 | NO |
| dl_0_4 | 6/10 | 4/10 | 0/10 | 0/10 | 0.0 | 10/10, 3.49 | YES |
| dl_0_5 | 0/10 | 2/10 | 0/10 | 0/10 | 0.0 | 6/10, 2.09 | NO |
| dl_1_2 | 10/10 | 8/10 | 2/10 | 0/10 | 0.0 | 10/10, 1.10 | YES |
| dl_1_3 | 5/10 | 7/10 | 0/10 | 3/10 | 0.0 | 10/10, 2.74 | YES |
| dl_1_4 | 10/10 | 10/10 | 10/10 | 10/10 | 0.0 | 10/10, 5.14 | YES |
| dl_1_5 | 10/10 | 7/10 | 10/10 | 3/10 | 0.0 | 10/10, 2.98 | YES |
| dl_2_3 | 0/10 | 2/10 | 0/10 | 1/10 | 0.2 | 10/10, 3.98 | YES |
| dl_2_4 | 10/10 | 8/10 | 9/10 | 7/10 | 0.0 | 10/10, 3.74 | YES |
| dl_2_5 | 0/10 | 0/10 | 0/10 | 0/10 | 0.0 | 5/10, 0.42 | NO |
| dl_3_4 | 0/10 | 0/10 | 0/10 | 0/10 | 0.0 | 8/10, 0.53 | NO |
| dl_3_5 | 2/10 | 7/10 | 0/10 | 0/10 | 0.0 | 10/10, 1.96 | YES |
| dl_4_5 | 1/10 | 6/10 | 7/10 | 4/10 | 0.0 | 10/10, 1.39 | YES |

Wilson 95% for k/10: 0/10 0.00-0.28, 3/10 0.11-0.60, 5/10 0.24-0.76, 7/10 0.40-0.89, 10/10 0.72-1.00.


Reading the map (oracle faults act from t=0 for 10 s; controller cells disable legs at 4 s and run to 14 s, so the two are comparable in kind only):
- Planner limits (the oracle walks, the controllers do not): R1, L1 and L3 alone (oracle 10/10 survive; L1 and L3 every controller 0/10; R1 only plain tripod+healing 10/10, tuned 0/10); R1+R3, R1+L2, R2+L1 and R3+L1 (oracle walks, tuned+healing 0-3/10); L1+L3 (oracle walks, tuned+healing 0/10); R2+R3 with tuned+healing (0/10). The healing layer rescales the diagnosed leg and global tripod parameters, and cannot express the per-leg phase shifts the oracle uses.
- With the short budget (2 restarts x 30 generations) no walking gait was found for R1+R2, R1+L1, R1+L3, R3+L3, L1+L2. The long-budget rerun (below) found walking gaits for R1+L3 and R3+L3, so those two are planner limits after all (every controller fails them). Still no walking gait found for R1+R2, R1+L1 and L1+L2 (two adjacent same-side pairs and the two front legs): these are the candidates for physics limits, but absence of a found gait is NOT a proof of impossibility.
- Survived by every controller with no help: R2, L2, and R2+L2.
- Healing is not monotone good: it lowers survival in R2+L3 (tuned 10 -> 3), R2+R3 (tuned 2 -> 0, tripod 10 -> 8), R3+L2 (tripod 10 -> 8) and others, because diagnose/replan interrupts a gait that was already working.
Verdict: the recovery map is complete (840 episodes). Most failures of walkable cases are planner limits; three doubles (R1+R2, R1+L1, L1+L2) had no walking gait found by the long-budget oracle (physics limit unproven).

## Stage 4: hybrid controller (tuned-tripod pitch feedback + healing + connectome nudges)

Design: tuned-tripod stance feedback (kp 1.2) + the healing layer + connectome speed/frequency/turn nudges. Stage 2 and tuning showed ungated nudges break slope15 (7-10/10 falls within 0.6 s) and single-leg recovery, so the chosen variant `h_half_pg` scales speed/freq nudges x0.5, keeps the turn nudge, switches nudges off when the low-passed |pitch| > 0.10 rad, and off after the first fault suspicion. Chosen on seeds 100-109 by a fixed rule (fewest total falls over 6 cells: h_half_pg 8, h_half_pg2 9, h_none 11, h_full_pg 15, h_half 18, h_clip 18, h_turn 18, h_full 24, h_speed 24). Final seeds 0-9. `h_none` is the same wrapper with nudges at 0 (tuned tripod + healing). MLP version of the hybrid was not run.

Hybrid = variant `h_half_pg`: tuned-tripod pitch feedback (kp=1.2) + healing layer + connectome speed/freq nudges x0.5 and turn nudge x1, nudges gated off when the low-passed |pitch| > 0.10 rad or after the first fault suspicion. `h_none` = same wrapper with all nudges 0 (tuned tripod + healing).

| cell | arm | falls/10 (Wilson) | mean survival s | mean distance m | speed err m/s |
|---|---|---|---|---|---|
| flat | h_half_pg | 0.0/10 (0.00-0.28) | 10.00 | 2.723 | 0.0223 |
| flat | h_none | 0.0/10 (0.00-0.28) | 10.00 | 2.616 | 0.0116 |
| flat | tuned | 0.0/10 (0.00-0.28) | 10.00 | 2.616 | 0.0116 |
| flat | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 10.00 | 1.878 | 0.0622 |
| rough1 | h_half_pg | 0.0/10 (0.00-0.28) | 10.00 | 2.709 | 0.0209 |
| rough1 | h_none | 0.0/10 (0.00-0.28) | 10.00 | 2.650 | 0.0150 |
| rough1 | tuned | 0.0/10 (0.00-0.28) | 10.00 | 2.650 | 0.0150 |
| rough1 | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 10.00 | 1.911 | 0.0589 |
| rough3 | h_half_pg | 0.0/10 (0.00-0.28) | 10.00 | 2.587 | 0.0126 |
| rough3 | h_none | 0.0/10 (0.00-0.28) | 10.00 | 2.583 | 0.0088 |
| rough3 | tuned | 0.0/10 (0.00-0.28) | 10.00 | 2.583 | 0.0088 |
| rough3 | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 10.00 | 1.902 | 0.0598 |
| push | h_half_pg | 1.0/10 (0.02-0.40) | 11.24 | 2.907 | 0.0216 |
| push | h_none | 6.0/10 (0.31-0.83) | 7.48 | 1.769 | 0.0191 |
| push | tuned | 6.0/10 (0.31-0.83) | 7.48 | 1.678 | 0.0206 |
| push | ppo (n_train=5, falls/10 averaged) | 5.6/10 (0.31-0.83) | 7.71 | 1.530 | 0.0519 |
| slope10 | h_half_pg | 0.0/10 (0.00-0.28) | 10.00 | 2.081 | 0.0419 |
| slope10 | h_none | 0.0/10 (0.00-0.28) | 10.00 | 2.087 | 0.0413 |
| slope10 | tuned | 0.0/10 (0.00-0.28) | 10.00 | 2.087 | 0.0413 |
| slope10 | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 10.00 | 1.732 | 0.0768 |
| slope15 | h_half_pg | 0.0/10 (0.00-0.28) | 10.00 | 1.988 | 0.0512 |
| slope15 | h_none | 0.0/10 (0.00-0.28) | 10.00 | 1.960 | 0.0540 |
| slope15 | tuned | 0.0/10 (0.00-0.28) | 10.00 | 1.960 | 0.0540 |
| slope15 | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 10.00 | 1.530 | 0.0970 |
| slope20 | h_half_pg | 10.0/10 (0.72-1.00) | 0.79 | -0.094 | 0.3711 |
| slope20 | h_none | 10.0/10 (0.72-1.00) | 0.75 | -0.101 | 0.3856 |
| slope20 | tuned | 10.0/10 (0.72-1.00) | 0.75 | -0.101 | 0.3856 |
| slope20 | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 10.00 | 1.193 | 0.1307 |
| fault_disable_leg+healing | h_half_pg | 8.0/10 (0.49-0.94) | 8.53 | 1.939 | 0.0180 |
| fault_disable_leg+healing | h_none | 4.0/10 (0.17-0.69) | 11.95 | 2.849 | 0.0187 |
| fault_disable_leg+healing | tuned | 4.0/10 (0.17-0.69) | 11.95 | 2.849 | 0.0187 |
| fault_disable_leg+healing | ppo (n_train=5, falls/10 averaged) | 0.4/10 (0.00-0.28) | 13.90 | 1.731 | 0.1252 |
| fault_lock_joint+healing | h_half_pg | 0.0/10 (0.00-0.28) | 14.00 | 1.520 | 0.1414 |
| fault_lock_joint+healing | h_none | 0.0/10 (0.00-0.28) | 14.00 | 2.185 | 0.0939 |
| fault_lock_joint+healing | tuned | 0.0/10 (0.00-0.28) | 14.00 | 2.185 | 0.0939 |
| fault_lock_joint+healing | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 14.00 | 1.924 | 0.1126 |
| fault_sensor_dropout+healing | h_half_pg | 0.0/10 (0.00-0.28) | 14.00 | 3.686 | 0.0133 |
| fault_sensor_dropout+healing | h_none | 0.0/10 (0.00-0.28) | 14.00 | 3.671 | 0.0122 |
| fault_sensor_dropout+healing | tuned | 0.0/10 (0.00-0.28) | 14.00 | 3.671 | 0.0122 |
| fault_sensor_dropout+healing | ppo (n_train=5, falls/10 averaged) | 0.0/10 (0.00-0.28) | 14.00 | 2.399 | 0.0786 |
| fault_sequential+healing | h_half_pg | 10.0/10 (0.72-1.00) | 7.69 | 1.844 | 0.0110 |
| fault_sequential+healing | h_none | 10.0/10 (0.72-1.00) | 10.37 | 2.355 | 0.0229 |
| fault_sequential+healing | tuned | 10.0/10 (0.72-1.00) | 10.37 | 2.355 | 0.0229 |
| fault_sequential+healing | ppo (n_train=1, falls/10 averaged) | 10.0/10 (0.72-1.00) | 10.74 | 1.801 | 0.0817 |
| healthy+healing | h_half_pg | 0.0/10 (0.00-0.28) | 14.00 | 3.827 | 0.0233 |
| healthy+healing | h_none | 0.0/10 (0.00-0.28) | 14.00 | 3.671 | 0.0122 |
| healthy+healing | tuned | 0.0/10 (0.00-0.28) | 14.00 | 3.671 | 0.0122 |
| healthy+healing | ppo (n_train=1, falls/10 averaged) | 0.0/10 (0.00-0.28) | 14.00 | 1.180 | 0.1657 |

## Paired comparisons (hybrid minus other); verdict by the pre-stated rule

| other | cell | metric used | diff [95% CI] | distance diff m [95% CI] | verdict |
|---|---|---|---|---|---|
| tuned | flat | distance | +0.107 [+0.068, +0.139] | +0.107 [+0.068, +0.139] | WIN |
| tuned | rough1 | distance | +0.059 [+0.029, +0.091] | +0.059 [+0.029, +0.091] | WIN |
| tuned | rough3 | distance | +0.004 [-0.049, +0.055] | +0.004 [-0.049, +0.055] | TIE |
| tuned | push | t_end | +3.752 [+1.476, +6.030] | +1.229 [+0.617, +1.814] | WIN |
| tuned | slope10 | distance | -0.005 [-0.020, +0.010] | -0.005 [-0.020, +0.010] | TIE |
| tuned | slope15 | distance | +0.027 [+0.019, +0.037] | +0.027 [+0.019, +0.037] | WIN |
| tuned | slope20 | t_end | +0.036 [-0.008, +0.086] | +0.007 [+0.004, +0.011] | TIE |
| tuned | fault_disable_leg+healing | t_end | -3.420 [-5.428, -1.494] | -0.910 [-1.432, -0.438] | LOSS |
| tuned | fault_lock_joint+healing | distance | -0.665 [-1.205, +0.003] | -0.665 [-1.204, +0.003] | TIE |
| tuned | fault_sensor_dropout+healing | distance | +0.015 [-0.014, +0.043] | +0.015 [-0.014, +0.043] | TIE |
| tuned | fault_sequential+healing | t_end | -2.686 [-3.904, -1.556] | -0.511 [-0.773, -0.275] | LOSS |
| tuned | healthy+healing | distance | +0.155 [+0.118, +0.190] | +0.155 [+0.118, +0.190] | WIN |
| h_none | flat | distance | +0.107 [+0.069, +0.139] | +0.107 [+0.068, +0.139] | WIN |
| h_none | rough1 | distance | +0.059 [+0.028, +0.090] | +0.059 [+0.028, +0.091] | WIN |
| h_none | rough3 | distance | +0.004 [-0.049, +0.056] | +0.004 [-0.049, +0.055] | TIE |
| h_none | push | t_end | +3.752 [+1.476, +6.030] | +1.138 [+0.480, +1.764] | WIN |
| h_none | slope10 | distance | -0.005 [-0.020, +0.010] | -0.005 [-0.020, +0.010] | TIE |
| h_none | slope15 | distance | +0.027 [+0.019, +0.037] | +0.027 [+0.019, +0.037] | WIN |
| h_none | slope20 | t_end | +0.036 [-0.008, +0.086] | +0.007 [+0.004, +0.011] | TIE |
| h_none | fault_disable_leg+healing | t_end | -3.420 [-5.438, -1.498] | -0.910 [-1.431, -0.434] | LOSS |
| h_none | fault_lock_joint+healing | distance | -0.665 [-1.204, +0.002] | -0.665 [-1.205, +0.007] | TIE |
| h_none | fault_sensor_dropout+healing | distance | +0.015 [-0.014, +0.043] | +0.015 [-0.014, +0.044] | TIE |
| h_none | fault_sequential+healing | t_end | -2.686 [-3.898, -1.562] | -0.511 [-0.772, -0.275] | LOSS |
| h_none | healthy+healing | distance | +0.155 [+0.118, +0.190] | +0.155 [+0.118, +0.190] | WIN |
| ppo | flat | distance | +0.845 [+0.802, +0.875] | +0.845 [+0.802, +0.875] | WIN |
| ppo | rough1 | distance | +0.798 [+0.772, +0.823] | +0.798 [+0.772, +0.823] | WIN |
| ppo | rough3 | distance | +0.685 [+0.604, +0.759] | +0.685 [+0.605, +0.759] | WIN |
| ppo | push | t_end | +3.524 [+1.521, +4.766] | +1.377 [+0.839, +1.744] | WIN |
| ppo | slope10 | distance | +0.349 [+0.268, +0.436] | +0.349 [+0.269, +0.436] | WIN |
| ppo | slope15 | distance | +0.457 [+0.294, +0.591] | +0.457 [+0.293, +0.590] | WIN |
| ppo | slope20 | t_end | -9.214 [-9.278, -9.150] | -1.287 [-1.352, -1.225] | LOSS |
| ppo | fault_disable_leg+healing | t_end | -5.370 [-6.918, -3.452] | +0.208 [-0.043, +0.523] | LOSS |
| ppo | fault_lock_joint+healing | distance | -0.404 [-0.704, -0.068] | -0.404 [-0.704, -0.066] | LOSS |
| ppo | fault_sensor_dropout+healing | distance | +1.287 [+1.246, +1.326] | +1.287 [+1.246, +1.326] | WIN |
| ppo | fault_sequential+healing | t_end | -3.056 [-3.890, -2.160] | +0.044 [-0.099, +0.202] | LOSS |
| ppo | healthy+healing | distance | +2.647 [+2.529, +2.754] | +2.647 [+2.531, +2.755] | WIN |

Win/tie/loss counts over cells: vs tuned: {'WIN': 5, 'TIE': 5, 'LOSS': 2}; vs h_none: {'WIN': 5, 'TIE': 5, 'LOSS': 2}; vs ppo: {'WIN': 8, 'LOSS': 4}


Verdict: the hybrid WINS push (falls 1/10 vs 6/10) and small flat/rough1/slope15/healthy distance gains (partly speed overshoot), TIES 5 cells, and LOSES single-leg + healing (falls 8/10 vs 4/10) and sequential-fault survival time. It does not beat tuned tripod + healing overall. Versus PPO (5 training seeds averaged) most distance wins reflect PPO walking slowly (1.88 m flat vs 2.72 m); PPO has the fewest falls on fault cells and survives slope20 where the hybrid does not.

## Stage 5: video evidence plan (plan only, nothing rendered)

Selection rule (fixed in advance): every seed 0-9 of a chosen cell is shown, in seed order, no cherry-picking. A 10-robot grid = the same cell, 10 seeds, one controller per grid; two grids side by side compare controllers. Each row below is the recorded outcome for that seed so you can check it before anything is rendered. T = time of fall in s (episode length 14 s unless stated); OK = no fall.

## Candidate A (clearest single story): single disabled leg, plain tripod, with vs without healing

### A1 without healing
- tripod  / fault_disable_leg: falls 10/10, mean distance 1.70 m
- per seed 0-9: s0:T=11.86, s1:T=11.26, s2:T=12.40, s3:T=12.90, s4:T=11.04, s5:T=10.42, s6:T=11.74, s7:T=11.00, s8:T=11.76, s9:T=11.22

### A2 with healing
- tripod  / fault_disable_leg+healing: falls 3/10, mean distance 2.42 m
- per seed 0-9: s0:OK, s1:OK, s2:T=9.90, s3:OK, s4:T=9.18, s5:OK, s6:OK, s7:T=10.28, s8:OK, s9:OK

## Candidate B: same cell, connectome (healing does NOT help it)

### B1 connectome no healing
- connectome  / fault_disable_leg: falls 10/10, mean distance 1.31 m
- per seed 0-9: s0:T=6.12, s1:T=6.30, s2:T=7.38, s3:T=6.02, s4:T=7.34, s5:T=6.92, s6:T=5.60, s7:T=6.32, s8:T=6.46, s9:T=6.74

### B2 connectome with healing
- connectome  / fault_disable_leg+healing: falls 10/10, mean distance 1.32 m
- per seed 0-9: s0:T=6.12, s1:T=6.30, s2:T=7.08, s3:T=6.02, s4:T=7.46, s5:T=6.78, s6:T=5.60, s7:T=6.32, s8:T=6.50, s9:T=6.74

## Candidate C: tuned tripod single leg

### C1 tuned no healing
- tuned_tripod  / fault_disable_leg: falls 7/10, mean distance 2.65 m
- per seed 0-9: s0:T=8.36, s1:T=10.14, s2:OK, s3:T=13.18, s4:OK, s5:T=9.74, s6:T=10.54, s7:T=8.80, s8:T=12.14, s9:OK

### C2 tuned with healing
- tuned_tripod  / fault_disable_leg+healing: falls 4/10, mean distance 2.85 m
- per seed 0-9: s0:OK, s1:OK, s2:T=8.94, s3:OK, s4:T=9.88, s5:T=8.44, s6:OK, s7:T=8.22, s8:OK, s9:OK

## Candidate D: 15 degree slope, connectome vs tuned tripod

### D1 connectome slope15
- connectome  / slope15: falls 10/10, mean distance -0.09 m
- per seed 0-9: s0:T=0.66, s1:T=0.58, s2:T=0.96, s3:T=0.80, s4:T=1.24, s5:T=0.70, s6:T=0.86, s7:T=0.58, s8:T=0.66, s9:T=0.62

### D2 tuned tripod slope15
- tuned_tripod  / slope15: falls 0/10, mean distance 1.96 m
- per seed 0-9: s0:OK, s1:OK, s2:OK, s3:OK, s4:OK, s5:OK, s6:OK, s7:OK, s8:OK, s9:OK

## Candidate E: hybrid on the same single-leg cell and slope

### E1 hybrid disable_leg+healing
- hybrid h_half_pg / fault_disable_leg+healing: falls 8/10, mean distance 1.94 m
- per seed 0-9: s0:T=8.66, s1:T=6.28, s2:T=8.62, s3:OK, s4:T=6.14, s5:T=7.46, s6:T=6.26, s7:T=7.30, s8:OK, s9:T=6.56

### E2 hybrid slope15
- hybrid h_half_pg / slope15: falls 0/10, mean distance 1.99 m
- per seed 0-9: s0:OK, s1:OK, s2:OK, s3:OK, s4:OK, s5:OK, s6:OK, s7:OK, s8:OK, s9:OK

## Recommendation

- Best 10-robot comparison on current evidence: A1 vs A2 (the only cell where healing visibly changes the plain tripod: 10/10 falls to 3/10). It must be described as 'healing helps the plain tripod on one leg loss' and NOT 'healing helps the connectome' (B2 falls 10/10) and NOT generally (Stage 3 map: it hurts in several double-fault cases).
- D1 vs D2 shows the simple tuned tripod beating the connectome on slopes; it is an honest-negative clip, not a promotional one.
- Anything about the hybrid waits for the final Stage 4 table (docs/v3_stage4_tables.md).
- Every clip must carry an on-screen label: 'MuJoCo simulation, connectome-inspired controller, seeds 0-9 shown in order'. No claims about real hardware, ROS 2 or Docker.


## Verdict per stage

- Stage 1: DONE. Healing helps the plain tripod on one leg loss; not established for the tuned tripod or connectome.
- Stage 2: DONE. Cause = connectome speed/frequency nudges. Fix = remove or cap them; changing the CMA-ES search does not fix it.
- Stage 3: DONE (oracle gaps listed above). Mostly planner limits; physics limits unproven.
- Stage 4: DONE. Hybrid wins push only; no overall win; loses single-leg healing.
- Stage 5: DONE as a plan; no rendering.

## Claims register (rebuilt from V2+V3 data)

- SUPPORTED: healing reduces falls of the plain tripod on a single disabled leg (10/10 -> 3/10).
- NOT SUPPORTED: healing helps the tuned tripod (7/10 -> 4/10, intervals overlap), the connectome (10/10 -> 10/10), or sequential faults.
- SUPPORTED: the connectome's speed/frequency nudges cause its post-fault falls (nudges off: 3/10, on: 10/10).
- SUPPORTED: a one-parameter pitch-feedback tripod survives slopes where the connectome falls (slope15 0/10 vs 10/10 falls, seeds 0-9).
- SUPPORTED: in the simulator most double leg losses admit a walking gait (oracle); most controller failures are planner limits.
- NOT SUPPORTED: "the connectome wiring matters" (V2: a small MLP imitating it beats it; unchanged).
- PARTIAL: hybrid improves push recovery (1/10 vs 6/10 falls), no overall advantage over the tuned tripod.
- PARTIAL: oracle "no walking gait found" cases are not proven physically impossible.
- NOT TESTED: real hardware, ROS 2, Docker, any GPU.

## What failed or was not done

- Hybrid single-leg+healing is worse than the tuned tripod (8/10 vs 4/10 falls) because nudges act before detection.
- The healing layer hurts several double-fault cases (list above); not fixed here.
- The oracle searched 2 restarts x 30 generations (fitness on 2 seeds) per case; non-walking cases were rerun with a larger budget (see above), still not a proof of impossibility. The oracle uses faults from t=0 and an open-loop gait family, so it says nothing about detection delay.
- Per-channel nudge diagnosis was run on tuning seeds 100-109 only (not re-run on seeds 0-9).
- The MLP version of the hybrid, a connectome hybrid with an MLP in place of the SNN, was not run.
- PPO sequential-fault and healthy+healing cells exist for training seed 0 only; other PPO training seeds were not run there.
- n = 10 seeds per cell: many CIs are wide; "TIE" often means undetermined.
- The recovery map covers only disable_leg faults on flat ground, simultaneous at 4 s.
- CI: GitHub Actions failures of Oct 4 were fixed on Oct 5; runs for the V3 pushes should be re-checked.
