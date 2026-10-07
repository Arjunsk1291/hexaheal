# Validation release

Simulation only. This release isolates a fresh, complete leg-loss validation from older plots, missing historical raw files and superseded captions. The saved release contains all 1470 episodes; `release_report.py` refuses missing or duplicate runs.

## One command

Ubuntu/Linux, Python 3.10 and a working headless EGL driver:

```sh
bash scripts/release.sh
```

This installs exact dependencies, runs the tests, resumes 1470 simulation episodes, renders a short declared demo, audits all records, exports CSV and makes plots plus SHA-256 checksums. On a new machine, remove `release/validation` or use a fresh clone and a new output directory rather than pretending saved runs were rerun. The default command checks existing keys and resumes; it does not recompute completed runs. To force a full independent reproduction:

```sh
mv release/validation release/recorded
bash scripts/release.sh
```

No tuning occurs in this command. Tuned gains, gait library and Tier A/B configs are frozen source inputs with hashes in `experiment.json`. Evaluation seeds are 0-9; tuning seeds were 100-109. Rebuilding the historical tuning process is outside this release.

## Matched experiment

- 6 single-leg plus 15 two-leg torque-disable cases, every evaluation seed, flat ground.
- Tripod, tuned tripod, healing v1, Tier A, Tier B and warm start: 14 simulated seconds, faults at 4 s, command 0.25 m/s.
- Oracle: gait library built on tuning data, faults at 0 s, 15 s episodes. It is contextual and has different initial conditions; never describe its row as a matched online baseline.
- Recovery: no fall and forward speed >=0.125 m/s across the last 8 seconds. A recovered case requires >=7/10 seeds. Upright but below this threshold is not walking recovery, and is not proof of zero motion.
- Tier B uses a nominal 60-trial search setting, but completed populations evaluate 61 candidates. It charges artificial simulated delay, not observed compute time. A completed search holds the robot for 4.6 simulated seconds. This is not evidence of real-time replanning capability.
- Warm start excludes the exact failed-leg set and its left/right mirror from its library, at the same search setting. The pre-registered adoption rule requires >=2 extra cases, >=8 recovered cases and a positive lower paired-bootstrap bound.

The raw wall-runtime field is separately recorded and machine-dependent; it does not drive the controller. Baselines reset independently for every episode. Nothing here is hardware, and neither ROS2 runtime nor sim-to-real transfer is verified.

## Files

`validation/runs.jsonl` and `runs.csv`: every measured episode, including failure.
`experiment.json`: seed sets, geometry, MJCF hash, controller/source input hashes.
`hardware.json`: CPU, OS, Python, starting source commit.
`summary.json`: case/run counts and paired seed-cluster bootstrap intervals.
`recovery_matrix.png`, `baseline_comparison.png`: derived only from complete raw files.
`demo.mp4`: first case (R1) and first seed (0), predeclared, not a success-rate estimate.
`SHA256SUMS`: audit integrity, not proof a run occurred.

Negative results use the same denominator and prominence as successful results. PPO and response-delay historical counts are not independently rerun by this release. They remain historical context, not fresh validation. No new latency/dropout sweep is being introduced.

## License boundary

The release robot is procedural original geometry; no imported robot meshes or external dataset. Code is MIT. Installed dependency license texts are copied in `dependency_licenses/`, with package versions and upstream source links in its index. These notices do not relicense upstream packages. The archived connectome code is outside this release. FlyWire-derived tables left in earlier git history still retain their third-party non-commercial terms; calling current HexaHeal code MIT does not remove those history restrictions. See `docs/LICENSES.md`. The encoded demonstration uses FFmpeg via imageio; see imageio-ffmpeg and FFmpeg notices below.
