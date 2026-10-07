# Fresh validation release

Simulation only. All rows below are MEASURED from the attached raw files.

| Controller | Recovered /21 | Upright /21 |
|---|---:|---:|
| tripod | 0 | 6 |
| tuned | 0 | 6 |
| healing_v1 | 0 | 4 |
| tierA | 12 | 13 |
| tierB | 6 | 12 |
| warm_start | 9 | 14 |
| oracle | 15 | 18 |

Warm-start pre-registered rule passed: False

The oracle has different initial-fault timing and episode length; it is contextual, not a matched baseline.
PPO and historical latency counts are not part of this fresh release: their full reproduction remains UNVERIFIED.
