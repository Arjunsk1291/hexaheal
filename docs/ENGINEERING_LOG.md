# Engineering log

Decisions, deviations and measured findings, appended per phase. Environment for all measurements unless stated:
2 vCPU Linux sandbox, 1.5 GB RAM, no GPU, no Docker, Python 3.10, MuJoCo 3.14. **Nothing was run on the owner's GTX 1660 Ti laptop.**

## Phase 0 - preflight and scaffold
- Preflight (`scripts/preflight.py`, `results/preflight.json`): Docker and nvidia-smi absent in the build sandbox, so the Docker/ROS 2 layer is written but **not executed** here (see Phase 7).
- Headless GL: EGL fails (no device), so rendering uses OSMesa. `render.pick_gl_backend()` tries EGL, then OSMesa, then GLFW.
- Core package has no ROS dependency.

## Phase 1 - simulation core
- Procedural MJCF: 6 legs x (coxa, femur, tibia), position actuators (kp=8, kv=0.4, +-2.5 N m), IMU, touch sensors, joint encoders.
- Terrains: flat, heightfield rough L1/L2/L3 (noise amplitude 1.2/2.2/3.5 cm), slopes 10/15/20 deg. Faults: disable_leg, lock_joint, reduce_torque, sensor_dropout, triggered at a chosen time. Pushes: force pulses on the torso.
- Measured: ~3,500-4,900 control steps/s (0.02 s each), i.e. 70-100x real time for the bare physics.
- Fall detection uses torso-geom contact or up-vector z < 0.5 (an absolute height check gave false falls on downhill slopes).

## Phase 2 - tripod baseline
- Tuned by a small grid (freq 1-2 Hz, stride 0.2-0.4, lift 0.3-0.5). Defaults: 1.5 Hz, stride 0.35, lift 0.35, duty 0.55.
- Finding (not hidden): the tripod gait walks flat, rough L1-L3 and a 10 deg slope, but **falls on 15 and 20 deg slopes** in most seeds.

## Spec v2 adaptations (2026-10-05)
CPU-only design, PPO as a residual on the CPG (64x64 MLP), verification labels, no tokens handled, push via `PUSH.md` + `push.sh` (written at the end), kinematic-replay fallback not needed because OSMesa works.

## Phase 3 - connectome-inspired controller
- Data: FlyWire v783 connectivity/completeness tables from the Shiu et al. repo (MIT code; FlyWire data CC BY-NC 4.0, https://flywire.ai/guidelines) and the Schlegel et al. annotation table. Raw data is downloaded to `data/raw` (git-ignored), never committed.
- Subgraph (`neurowalker.connectome`): 10,000 neurons, 797,577 synapse pairs. All mechanosensory + gustatory sensory neurons, all descending (1,299) and motor neurons, remaining slots by sqrt(forward reach from sensory x backward reach to descending), 3 hops, excluding visual/olfactory/optic neurons.
- Engine (`neurowalker.snn`): LIF with Shiu et al. constants (v_th -45 mV, v_rst -52 mV, t_mbr 20 ms, tau 5 ms, refractory 2.2 ms, w_syn 0.275 mV, Poisson kick 0.275*250 mV). Deviations: 0.5 ms Euler step (reference Brian2 0.1 ms, exact linear), 2.0 ms delay (reference 1.8 ms), numba event-driven delivery.
- Measured here: 10k subgraph 0.098 s compute per simulated second (about 10x faster than real time); full 138,639-neuron network about 1.2 s per simulated second.
- Validation (`scripts/validate_shiu.py`, `results/validation/shiu_sugar_validation.json`): sugar-GRN drive reaches proboscis/ingestion motor neurons; bitter and no-stimulus controls stay silent. Qualitative reproduction only.
- I/O mapping (8 disjoint mechanosensory groups in, readout DN groups out, calibrated paired readouts) is a DESIGN CHOICE, not a biological claim.
- Finding: first decoding used the wrong normalisation (readouts saturated at the speed clip); fixed by paired-channel calibration.

## Phase 4 - self-healing
- Monitor: tracking residual EMA vs per-joint healthy baseline (t=1.5-3.5 s), frozen/flat sensor detection. State machine NORMAL -> FAULT_SUSPECTED -> DIAGNOSE -> ADAPT -> VERIFY -> NORMAL | SAFE_STOP; CMA-ES over 6 gait parameters in model rollouts; search wall time is charged to the robot as time spent on the old gait.
- Finding: a torque-reduction fault at 30% remaining torque does not change tracking at all (loads stay below the limit), so it is undetectable and harmless; the benchmark uses 5%.
- Finding: the severity of reduce_torque is assumed (5%), not estimated, in the model rollouts.

## Phase 5 - PPO residual
- `neurowalker.rl`: residual (scale 0.25) on the tripod CPG, 64x64 MLP, 4 envs, curriculum over terrains, random faults/pushes during training. Single seed (budget).

## Phase 6 - benchmark (tripod + connectome-inspired; PPO rows appended separately)
- 320 episodes, 10 seeds per cell (`results/benchmark.parquet`, `results/summary.json`, `docs/BENCHMARK.md`, figures in `docs/figures`).
- Caveat: this run shared 2 vCPUs with PPO training, so latency and CPU numbers are inflated and the wall time of the CMA-ES search (charged to the robot as time spent on the old gait) is load-dependent. Several healing episodes ended while still in ADAPT/VERIFY/FAULT_SUSPECTED; those are reported as such in the tables, not as recoveries.
- Findings (not hidden): connectome-inspired and tripod both fall on 15/20 deg slopes; on 10 deg slope the connectome-inspired controller falls in 3/10 seeds, the tripod in 0/10; the 48 N push topples both in 5/10 seeds. Slight distance advantage of the connectome-inspired controller on flat and rough terrain (about +0.1 m of 10 s) is small and comes mostly from the closed-loop speed command pushing gait gain above the fixed tripod setting.
- Retained speed above 100% (reduce_torque + healing) means the healed run walked faster than its own pre-fault window; plain 0% rows include falls and backward motion (negative speed is clipped to 0).

## Phase 6b - lesion sweep, media, dashboard (2 vCPU sandbox)
- Lesion sweep (5 seeds per group, silencing named neuron groups of the subgraph; results/lesion_sweep_summary.json): no group caused a fall. Speed change vs. unlesioned: dn_turn_left -113%, dn_turn_right -90%, in_turn_left -83%, dn_all and sensory_all_mech -78%, dn_speed_up -67%, in_speed_up -38%, pitch/roll/other groups -18% to 0%.
- Caveat: the input/output mapping from neurons to the gait is a design choice, so these effects describe this controller, not fly biology. A turn-group lesion changing forward speed shows the readout couples channels; it is not a finding about fly turning circuits.
- Validation rerun with 10 trials (results/validation/shiu_sugar_validation.json). Qualitative reproduction only.
- Dashboard bug found while checking screenshots: results/summary.json contains NaN (cells with no fault metric). Browsers reject NaN in JSON, so leaderboard and charts were empty. Fixed by writing null into the dashboard copy.
- Build host hit a memory stall when the first asset script held all frames in RAM (1.5 GB box). Rewritten to stream frames.
- Healing made the PPO residual worse after a disabled leg (77% -> 49% speed retained). Reported as is.
- Playwright screenshots (desktop and mobile) are in docs/screenshots; ROS 2, Docker and CI remain UNVERIFIED.

## v4 media rebuild (environment note)
- The sandbox VM was replaced mid-build, so the v4 media was re-rendered from the pushed repo plus the v4 model source.
- On the reinstalled stack, importing torch.optim after mujoco segfaulted when loading the PPO policy. `scripts/make_media.py` now imports `torch` and `torch._dynamo` first. No result files were affected.
- Wall-clock note: connectome clips take about 8 min each in the 2 vCPU sandbox because the spiking network runs every control step.

## v2 Stage 1 (reproducibility) - 2026-10-05, 2 vCPU sandbox
- Wall-time budget removed from the healing re-planner: the old gait now continues for trials x 0.075 s of SIMULATED time (src/neurowalker/healing.py, SEARCH_SIM_S_PER_TRIAL). CMA-ES and rollouts were already seeded.
- Verification (results/repro_check.json, scripts/repro_check.py): connectome, fault_disable_leg+healing, seed 8, 3 runs idle + 3 runs with one core burned: all 6 outcomes bit-identical (fell=True, t_end 6.5 s, distance 1.366976876199071, states FAULT_SUSPECTED 4.28, DIAGNOSE 4.9, ADAPT 4.9, VERIFY 6.36).
- Seed 8 now FALLS at 6.5 s. The v1 benchmark row for seed 8 (survived, 90-98% speed retained) did NOT reproduce.
- Cause of the pre-fault speed difference (no-heal vs healing runs, same seeds; v1 connectome 0.275 vs 0.322 m/s) and of the v1 irreproducibility: a state LEAK. HealingController.apply() mutated the shared controller's CPG params (freq/stride/lift/duty/turn_bias) and leg_stride_scale and nothing restored them, so every episode after a healing episode started with the previously searched gait. Demonstration (tripod, seed 101, x at t=4 s before any fault): 1.0175 m on a fresh controller, 1.3329 m after one healing episode (params freq 1.90, stride 0.498 instead of 1.5, 0.35). With the fix: 1.0175 m both times.
- CONSEQUENCE: all v1 "+healing" cells and any v1 cell run after a healing episode on the same controller object are contaminated by the leak. v1 healing numbers (e.g. 38% speed kept, 6/10 falls) are not valid and are superseded by the v2 re-run.
- Fix: the wrapper applies the searched gait only inside its own act() and restores the base gait; reset() restores the pristine gait.
## v2 Stage 2 (multi-fault healing) - code only so far, results pending
- Removed the suspect_count = -1e6 latch. After a verified recovery: commit the gait, remember the diagnosed fault (later searches include it), mask its legs in the monitor, re-baseline over a 0.8 s window (t+0.1 .. t+0.9) and return to monitoring.
- New scenarios in src/neurowalker/benchmark.py: fault_sequential (R3 @4 s, L3 @9 s, 16 s), fault_sequential+healing, healthy+healing (14 s); extra metrics n_suspect, n_recover, n_safe_stop, detect2_s.
- tests/test_healing.py: 3 new tests (no false positive on healthy seeds 100-102, second fault detected on tuning seed 101, no leak into the shared controller). tests/test_healing.py: 7 passed. Full suite and the 10-seed cells: pending.
