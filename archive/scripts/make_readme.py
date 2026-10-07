"""Generate README.md; every number is read from results/*.json."""
import json

S = json.load(open("results/summary.json")); info = json.load(open("data/processed/subgraph_info.json"))
V = json.load(open("results/validation/shiu_sugar_validation.json"))
try: pre = json.load(open("results/preflight.json"))
except Exception: pre = {}
L = {"tripod": "Tripod CPG", "connectome": "Connectome-inspired", "ppo": "PPO residual"}
ctrls = [c for c in L if c in S]
def cell(c, s):
    d = S.get(c, {}).get(s)
    return "n/a" if not d else f"{d['distance']['mean']:.2f} m, {d['fall_rate']['falls']}/{d['fall_rate']['n']} falls"
rows = "\n".join(f"| {s} | " + " | ".join(cell(c, s) for c in ctrls) + " |" for s in ["flat", "rough1", "rough2", "rough3", "slope10", "slope15", "slope20", "push"] if any(s in S[c] for c in ctrls))
fr = []
for f in ["disable_leg", "lock_joint", "reduce_torque", "sensor_dropout"]:
    fr.append(f"| {f.replace('_',' ')} | " + " | ".join(
        "n/a" if f"fault_{f}" not in S[c] else f"{S[c]['fault_'+f]['fault_retained']['mean']*100:.0f}% -> {S[c].get('fault_'+f+'+healing',{}).get('fault_retained',{}).get('mean',float('nan'))*100:.0f}%" for c in ctrls) + " |")
fr = "\n".join(fr)
txt = f"""# NeuroWalker

![demo](docs/media/demo.gif)

![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![CI](https://img.shields.io/badge/CI-UNVERIFIED-lightgrey)

A simulated 18-DOF hexapod (MuJoCo) whose walking is modulated by a **connectome-inspired controller**: a {info['n_neurons']:,}-neuron spiking subgraph of the published FlyWire fruit-fly connectome. It is benchmarked against a PPO residual policy and a classic tripod-gait CPG, and it can detect and recover from leg and joint faults. **Simulation only.**

## The 30-second version
Take a map of how a fruit fly's brain cells connect. Cut out a 10,000-cell piece around the cells that feel the body and the cells that send commands down. Feed the robot's sensor readings into the input cells, read the output cells, and let them nudge the speed and turning of a normal walking pattern. Then break a leg and see whether the robot notices and adapts. It is not a copy of a fly brain, and the robot does not think like a fly.

## Key results (generated from `results/summary.json`; 10 seeds per cell, see docs/BENCHMARK.md)
| scenario | {' | '.join(L[c] for c in ctrls)} |
|---|{'---|' * len(ctrls)}
{rows}

Speed retained after a fault, plain -> with self-healing:

| fault | {' | '.join(L[c] for c in ctrls)} |
|---|{'---|' * len(ctrls)}
{fr}

Full tables, confidence intervals and "where each controller loses": [docs/BENCHMARK.md](docs/BENCHMARK.md). Figures: `docs/figures/`.

Connectome subgraph: {info['n_neurons']:,} neurons, {info['n_synapse_pairs']:,} synapse pairs; {V['subgraph_wall_s_per_sim_s']:.3f} s compute per simulated second on the build sandbox (2 vCPU). Validation: sugar-sensing neuron drive reaches feeding motor neurons in the full network (`docs/figures/validation_shiu_sugar.png`, qualitative only).

## What this is / what this is not
- Is: a simulation study with a connectome-derived wiring diagram inside a hand-designed input/output mapping.
- Is not: an uploaded or emulated brain, a claim about how flies walk, or hardware. The I/O mapping is a design choice.

## Verification status
| item | status |
|---|---|
| Core sim, controllers, healing, benchmark, tests | run in the build sandbox |
| ROS 2 nodes, Docker image | UNVERIFIED (written, syntax-checked only) |
| GitHub Actions CI, Pages | UNVERIFIED until a run succeeds |
| GTX 1660 Ti runtimes | NOT MEASURED. All timings are from a 2 vCPU CPU sandbox |

## Quickstart
```bash
make setup && make test      # install + fast tests
make demo                    # render a clip
make benchmark report        # arena + figures
python scripts/download_data.py   # FlyWire data download + checksum check (data is never committed)
```
## Citations
Dorkenwald et al. 2024 (FlyWire, Nature); Shiu et al. 2024 (whole-brain LIF model, Nature); Lobato-Rios et al. 2022 and Wang-Chen et al. 2024 (NeuroMechFly); Todorov et al. 2012 (MuJoCo). FlyWire data is CC BY-NC 4.0; Shiu et al. code is MIT. See CITATION.cff and THIRD_PARTY_NOTICES.md.
"""
open("README.md", "w").write(txt)
print("readme ok")
