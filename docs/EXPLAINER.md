# HexaHeal explained in plain language

**Everything here is MuJoCo simulation. Nothing was run on a real robot.** Numbers are MEASURED (in `results/v3/`), GUESS or UNKNOWN. This page is meant to let me defend each design choice in an interview. Results: `docs/RESULTS_V3.md`.

## The question
A six-legged robot loses one or two legs mid-walk. Can software notice which legs failed and change how it walks fast enough to keep going? There are 21 possible cases (6 single legs, 15 pairs). For each controller I count the cases it handles on at least 7 of 10 random starts.

## The most important correction: "upright" is not "recovered"
- **Upright** = the robot never fell in 14 s.
- **Recovered** = upright AND it still walked at least half the commanded speed (0.125 m/s of 0.25) over the last 8 s.
- Why: my first metric only checked for falls. Re-scoring showed most of the runs counted as successes were standing still (plain tripod: 75 of 75 upright runs). Counting a motionless robot as a success would have been wrong. Both numbers are always reported.

## Modules, one by one
- **Environment and faults** (`env.py`, `faults.py`): the MuJoCo hexapod, 18 joints. A fault is injected at 4 s: a leg disabled (main study), a joint locked at its current angle, or leg torque cut to 30% (Stage 4).
- **Tripod gait** (`tripod.py`): the legs move in two alternating groups of three. A simple repeating pattern; it does not know about faults. The **tuned tripod** adds a small body-tilt correction (one number, picked on practice seeds).
- **Detector** (`HealthMonitor` in `healing.py`): compares what each joint was commanded to do with where it actually is. During a healthy baseline window it learns the normal error; later, a joint whose error rises well above baseline, or whose sensor goes flat, or a large body tilt, raises a suspicion. It must stay suspicious for 8 control steps (about 0.3 s) to avoid false alarms. It then keeps the peak error for a short confirmation time and names the set of legs whose joints look dead. Measured: detection about 0.34 s after the fault, 0 false alarms on 10 healthy runs per healing controller.
- **Planner, healing v2** (`healing2.py`): once legs are named, the robot **stands still** while it plans (this alone was the largest factor in an ablation on practice seeds: walking on with a broken leg often tips it before the new gait is ready). Then it switches to a new gait.
  - **Tier A** looks the gait up in a library built offline for each fault set. It is upper-bound style: the library was searched offline, not learned live.
  - **Tier B** searches online with CMA-ES (an evolutionary search) in short simulated trials of a model copy. The search is charged a fixed amount of *simulated* time (60 trials x 0.075 s), never wall-clock time, so results are repeatable. Tier B is the realistic version.
- **Free-gait parameters** (`freegait.py`): the search space. A gait is 24 numbers: frequency, stride, lift, duty cycle (fraction of the cycle a foot is on the ground), a turn bias, a stance adjustment, plus per-leg phase offset, stride scale and lift scale. The tripod is one point in this space.
- **Oracle** (`scripts/hh3_oracle.py`): a long offline search for the best gait for each case, with the fault known from t=0. It cheats on purpose, so it is an upper bound on what the simulator allows, not a competitor. If it finds nothing that is not a proof of physical impossibility (UNKNOWN).
- **PPO reference** (`rl.py`): a learned correction added to the tripod, used as one reference baseline, not as the main subject.
- **Metrics** (`hh_eval.py`): upright, recovered, time-to-fall, speed-tracking error (root-mean-square gap to 0.25 m/s, speed counted as 0 after a fall), and the last-8 s speed that defines "recovered".
- **Statistics** (`hh3_stats.py`): per-case **Wilson intervals** (a 95% range for a proportion with only 10 trials); **paired bootstrap** for differences between controllers: resample the 10 seeds with replacement, recompute the case counts, repeat 10,000 times, take the 2.5th and 97.5th percentiles. Paired because every controller sees the same 10 starts.

## Why these design choices
- Practice seeds (100-109) for every choice, test seeds (0-9) only for final numbers: so I cannot tune to the test. A pre-registration (`PREREGISTRATION_V3.md`) was committed before the v3 runs: definitions, delay sweep, second fault, claim rules, and "no result is dropped".
- Fixed simulated-time budget instead of wall-clock: runs are the same on any machine (tests check this).
- Tripod baselines are tuned on practice seeds so the comparison is not against a straw man.
- I report negative results at equal prominence: two Stage 2 fixes failed, v1 made things worse, v2 did not help on the second fault type.

## What happened (MEASURED, seeds 0-9)
- Plain and tuned tripod recover 0 of 21 cases; they stay upright in 6. v1 recovers 0 and is upright in 4 (worse).
- v2 Tier B recovers 6 and is upright in 12. Tier A recovers 12. The oracle recovers 15.
- Healing speed matters: with instant healing 55% of the tested runs recover, 30% at 1.0 s delay, 15% at 1.5 s.
- Tier B does not close the gap to the oracle and half its upright runs stand still.

## What I do not know
Whether any of this holds on a real robot, on rough ground, with other faults, at other speeds, or with a better search. Why the two Stage 2 fixes failed (only a guess).

## Glossary
- **Seed**: the random start (small variations in the starting pose and the simulator's noise). 0-9 evaluate, 100-109 tune.
- **Case**: which leg or pair of legs is lost (R1-R3 right, L1-L3 left, front to rear).
- **Gait**: the repeating leg pattern. **Duty cycle**: fraction of the cycle a foot is on the ground.
- **Tripod gait**: alternating groups of three legs.
- **Oracle**: offline best-known gait per case; upper bound, not a controller.
- **Upright / recovered / standing still**: no fall / no fall and at least 0.125 m/s over the last 8 s / upright but slower than that.
- **N_recovered, N_upright**: number of the 21 cases where the controller meets the definition on at least 7 of 10 seeds.
- **Wilson interval**: 95% range for a success rate from few trials. **Paired bootstrap**: resampling test for a difference between two controllers on the same seeds.
- **CMA-ES**: evolutionary search that adapts its sampling to what worked.
- **Pre-registration**: protocol committed before the runs, so the analysis cannot be bent afterwards.
- **MEASURED / GUESS / UNKNOWN**: result in a file / my estimate / not tested.
