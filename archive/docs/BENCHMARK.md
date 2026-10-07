# Benchmark analysis (auto-generated from results/summary.json)

Episodes: 480; controllers: Tripod CPG, Connectome-inspired, PPO residual; seeds per cell: 10.

## Distance (m, mean +- 95% CI) and fall rate

| scenario | Tripod CPG | Connectome-inspired | PPO residual |
|---|---|---|---|
| flat | 2.63 +- 0.04 (0/10 falls) | 2.76 +- 0.06 (0/10 falls) | 1.44 +- 0.06 (0/10 falls) |
| rough1 | 2.68 +- 0.04 (0/10 falls) | 2.78 +- 0.05 (0/10 falls) | 1.51 +- 0.06 (0/10 falls) |
| rough2 | 2.66 +- 0.04 (0/10 falls) | 2.76 +- 0.06 (0/10 falls) | 1.54 +- 0.06 (0/10 falls) |
| rough3 | 2.62 +- 0.05 (0/10 falls) | 2.73 +- 0.05 (0/10 falls) | 1.55 +- 0.04 (0/10 falls) |
| slope10 | 2.15 +- 0.04 (0/10 falls) | 1.56 +- 0.79 (3/10 falls) | 1.58 +- 0.10 (0/10 falls) |
| slope15 | 0.19 +- 0.46 (8/10 falls) | -0.09 +- 0.01 (10/10 falls) | 1.49 +- 0.04 (0/10 falls) |
| slope20 | -0.12 +- 0.01 (10/10 falls) | -0.08 +- 0.01 (10/10 falls) | 1.22 +- 0.03 (0/10 falls) |
| push | 2.02 +- 0.70 (5/10 falls) | 2.23 +- 0.84 (5/10 falls) | 0.83 +- 0.01 (10/10 falls) |

## Where each controller loses

- **flat**: best distance Connectome-inspired. Behind: Tripod CPG (2.63 m vs 2.76 m); PPO residual (1.44 m vs 2.76 m). Fall rates: Tripod CPG 0%, Connectome-inspired 0%, PPO residual 0%.
- **rough1**: best distance Connectome-inspired. Behind: Tripod CPG (2.68 m vs 2.78 m); PPO residual (1.51 m vs 2.78 m). Fall rates: Tripod CPG 0%, Connectome-inspired 0%, PPO residual 0%.
- **rough2**: best distance Connectome-inspired. Behind: PPO residual (1.54 m vs 2.76 m). Fall rates: Tripod CPG 0%, Connectome-inspired 0%, PPO residual 0%.
- **rough3**: best distance Connectome-inspired. Behind: Tripod CPG (2.62 m vs 2.73 m); PPO residual (1.55 m vs 2.73 m). Fall rates: Tripod CPG 0%, Connectome-inspired 0%, PPO residual 0%.
- **slope10**: best distance Tripod CPG. Behind: Connectome-inspired (1.56 m vs 2.15 m); PPO residual (1.58 m vs 2.15 m). Fall rates: Tripod CPG 0%, Connectome-inspired 30%, PPO residual 0%.
- **slope15**: best distance PPO residual. Behind: Tripod CPG (0.19 m vs 1.49 m); Connectome-inspired (-0.09 m vs 1.49 m). Fall rates: Tripod CPG 80%, Connectome-inspired 100%, PPO residual 0%.
- **slope20**: best distance PPO residual. Behind: Tripod CPG (-0.12 m vs 1.22 m); Connectome-inspired (-0.08 m vs 1.22 m). Fall rates: Tripod CPG 100%, Connectome-inspired 100%, PPO residual 0%.
- **push**: best distance Connectome-inspired. Behind: Tripod CPG (2.02 m vs 2.23 m); PPO residual (0.83 m vs 2.23 m). Fall rates: Tripod CPG 50%, Connectome-inspired 50%, PPO residual 100%.

## Faults: retained speed (% of pre-fault), plain vs +healing

| fault | Tripod CPG / +healing | Connectome-inspired / +healing | PPO residual / +healing |
|---|---|---|---|
| disable_leg | 0% / 30% | 0% / 38% | 77% / 49% |
| lock_joint | 0% / 78% | 71% / 80% | 79% / 70% |
| reduce_torque | 0% / 140% | 0% / 57% | 0% / 8% |
| sensor_dropout | 98% / 82% | 107% / 97% | 0% / 2% |

## Detection and verified recovery (healing runs)

| fault | controller | detect (s, mean) | verified recovery (s, mean) | runs verified / total |
|---|---|---|---|---|
| disable_leg | Tripod CPG | 0.31 | 3.91 | 5/10 (final states {'NORMAL': 5, 'FAULT_SUSPECTED': 3, 'SAFE_STOP': 1, 'ADAPT': 1}) |
| disable_leg | Connectome-inspired | 0.33 | 3.91 | 4/10 (final states {'ADAPT': 4, 'NORMAL': 4, 'VERIFY': 2}) |
| disable_leg | PPO residual | 0.34 | 3.82 | 8/10 (final states {'NORMAL': 8, 'SAFE_STOP': 2}) |
| lock_joint | Tripod CPG | 0.44 | 4.55 | 8/10 (final states {'NORMAL': 8, 'SAFE_STOP': 2}) |
| lock_joint | Connectome-inspired | 0.33 | 3.86 | 10/10 (final states {'NORMAL': 10}) |
| lock_joint | PPO residual | 2.89 | 6.14 | 4/10 (final states {'NORMAL': 6, 'SAFE_STOP': 3, 'VERIFY': 1}) |
| reduce_torque | Tripod CPG | 5.11 | 6.19 | 9/10 (final states {'NORMAL': 4, 'ADAPT': 4, 'VERIFY': 1, 'FAULT_SUSPECTED': 1}) |
| reduce_torque | Connectome-inspired | 3.58 | 5.44 | 9/10 (final states {'NORMAL': 6, 'SAFE_STOP': 1, 'VERIFY': 1, 'ADAPT': 1, 'FAULT_SUSPECTED': 1}) |
| reduce_torque | PPO residual | 3.16 | 5.11 | 5/10 (final states {'ADAPT': 4, 'SAFE_STOP': 4, 'NORMAL': 2}) |
| sensor_dropout | Tripod CPG | 0.32 | 2.48 | 9/10 (final states {'NORMAL': 9, 'SAFE_STOP': 1}) |
| sensor_dropout | Connectome-inspired | 0.36 | 2.52 | 10/10 (final states {'NORMAL': 10}) |
| sensor_dropout | PPO residual | 0.29 | 2.45 | 10/10 (final states {'NORMAL': 10}) |
