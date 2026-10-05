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

{{S1}}

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

{{ORACLE}}

{{LONG}}

Survivors/10 (no fall by 14 s) for each case and the oracle result:

{{MAP}}

Reading the map (oracle faults act from t=0 for 10 s; controller cells disable legs at 4 s and run to 14 s, so the two are comparable in kind only):
- Planner limits (the oracle walks, the controllers do not): R1, L1 and L3 alone (oracle 10/10 survive; L1 and L3 every controller 0/10; R1 only plain tripod+healing 10/10, tuned 0/10); R1+R3, R1+L2, R2+L1 and R3+L1 (oracle walks, tuned+healing 0-3/10); L1+L3 (oracle walks, tuned+healing 0/10); R2+R3 with tuned+healing (0/10). The healing layer rescales the diagnosed leg and global tripod parameters, and cannot express the per-leg phase shifts the oracle uses.
- Not found by the oracle (R1+R2, R1+L1, R1+L3, R3+L3, L1+L2): every controller also fails them. With 2 restarts x 30 generations no walking gait was found. This is NOT a proof of physical impossibility; see the long-budget rerun below.
- Survived by every controller with no help: R2, L2, and R2+L2.
- Healing is not monotone good: it lowers survival in R2+L3 (tuned 10 -> 3), R2+R3 (tuned 2 -> 0, tripod 10 -> 8), R3+L2 (tripod 10 -> 8) and others, because diagnose/replan interrupts a gait that was already working.
Verdict: the recovery map is complete (840 episodes). Most failures of walkable cases are planner limits; five doubles had no walking gait found by the oracle (physics limit unproven).

## Stage 4: hybrid controller (tuned-tripod pitch feedback + healing + connectome nudges)

Design: tuned-tripod stance feedback (kp 1.2) + the healing layer + connectome speed/frequency/turn nudges. Stage 2 and tuning showed ungated nudges break slope15 (7-10/10 falls within 0.6 s) and single-leg recovery, so the chosen variant `h_half_pg` scales speed/freq nudges x0.5, keeps the turn nudge, switches nudges off when the low-passed |pitch| > 0.10 rad, and off after the first fault suspicion. Chosen on seeds 100-109 by a fixed rule (fewest total falls over 6 cells: h_half_pg 8, h_half_pg2 9, h_none 11, h_full_pg 15, h_half 18, h_clip 18, h_turn 18, h_full 24, h_speed 24). Final seeds 0-9. `h_none` is the same wrapper with nudges at 0 (tuned tripod + healing). MLP version of the hybrid was not run.

{{S4}}

Verdict: the hybrid WINS push (falls 1/10 vs 6/10) and small flat/rough1/slope15/healthy distance gains (partly speed overshoot), TIES 5 cells, and LOSES single-leg + healing (falls 8/10 vs 4/10) and sequential-fault survival time. It does not beat tuned tripod + healing overall. Versus PPO (5 training seeds averaged) most distance wins reflect PPO walking slowly (1.88 m flat vs 2.72 m); PPO has the fewest falls on fault cells and survives slope20 where the hybrid does not.

## Stage 5: video evidence plan (plan only, nothing rendered)

{{PLAN}}

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
