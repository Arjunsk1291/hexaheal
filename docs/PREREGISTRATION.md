# Pre-registration (written and committed before any v2 experiment)

Date: 2026-10-05. Environment: 2 vCPU sandbox, simulation only.

## Seeds
- Tuning, debugging and any parameter choice: seeds 100-109 only.
- Final evaluation: seeds 0-9 only, run once per cell after the code is frozen.

## Question 1: does the connectome wiring matter?
Variants (same sensory encoding, same readout procedure, same CPG nudge limits, same calibration procedure):
(a) connectome, (b) degree-preserving edge shuffle, (c) random graph with the same neuron and synapse count,
(d) no network (same 8 input channels mapped to the same output nudges by a fixed linear low-pass filter with matched time constant),
(e) small MLP fitted to reproduce the connectome input-output mapping (skipped if it takes more than 2 h).
Cells: flat, rough1, rough3, push 48 N, slope10, disable_leg+healing, lock_joint+healing, sensor_dropout+healing; 10 seeds each.

Decision rule (fixed now): the connectome "matters" only if it beats ALL of (b), (c), (d), (e) on flat+rough distance
(flat, rough1, rough3), with paired-bootstrap 95% CIs of the per-seed difference that exclude zero (non-overlapping), and the
effect is over 0.1 m in each comparison. Otherwise the conclusion is: no evidence the wiring matters.
Variant (e) is dropped from the rule only if it is not run, and that will be stated.

## Question 2: does healing work on sequential faults?
Cell: leg R3 (leg 2) disabled at 4 s, leg L3 (leg 5) disabled at 9 s, 16 s episode, all three controllers, 10 seeds.
Success is stated per controller as falls/10 and speed retained after the second fault. No threshold is claimed in advance
beyond: "works" requires a detection of the second fault in at least 8/10 seeds and no more falls than the single-fault
healing cell for the same controller. A healthy+healing false-positive cell (14 s, 10 seeds) must show 0 transitions.

## Statistics
Paired bootstrap on per-seed differences, 10000 resamples, percentile 95% CI. Holm correction across the main comparisons.
Falls reported as counts out of 10 with Wilson 95% intervals.

## Honesty rules
Failed or skipped stages are reported as such. No numbers from seeds 100-109 appear in final tables. ROS 2 and Docker stay UNVERIFIED.
