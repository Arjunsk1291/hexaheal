# LinkedIn series - DRAFTS ONLY. Nothing is posted until Arjun approves the exact text.
Every number below is read from results/summary.json (10 seeds per cell, simulation, 2 vCPU CPU sandbox).
Wording rule: "connectome-inspired". Never "uploaded", "emulated" or "thinks like a fly".

## Post 1 - What I built
I built a simulated six-legged robot and gave its walking a connectome-inspired controller.

The controller is a 10,000-neuron spiking subgraph cut from the published FlyWire fruit-fly connectome. Robot sensor readings go into input cells, output cells nudge the speed and turning of a standard tripod gait. The input/output mapping is my design choice. It is not a copy of a fly brain.

I compared it with a plain tripod gait and a PPO residual policy, 10 seeds per scenario.
Flat ground, 10 s: tripod 2.63 m, connectome-inspired 2.76 m, PPO residual 1.44 m.

Simulation only. Code and results in the repo. [repo link after push]
Media: docs/social/reel_showcase.mp4 or cover_1080x1080.png

## Post 2 - Where it breaks
The part I like most is where each controller fails.
15 degree slope, falls out of 10: tripod 8/10, connectome-inspired 10/10, PPO residual 0/10.
48 N push, falls out of 10: tripod 5/10, connectome-inspired 5/10, PPO residual 10/10.
The PPO residual survives the slopes but is slower and falls on every push. The connectome-inspired controller is fastest on flat ground and does not beat the tripod on slopes.
One training seed for PPO, 1.18M steps on CPU. Treat it as a first result, not a ranking.
Media: carousel_3.png to carousel_5.png

## Post 3 - Self-healing and honest limits
When a leg is disabled, a monitor detects it, diagnoses which leg, and searches for a new gait. Speed kept after a disabled leg, without -> with healing: tripod 0% -> 30%, connectome-inspired 0% -> 38%, PPO residual 77% -> 49% (healing made PPO worse here).
Limits: simulation only, no hardware. Timings are from a 2 vCPU CPU sandbox, not a GPU laptop. Several healing runs ended before the search finished. ROS 2 nodes and the Docker image are written but not run yet (UNVERIFIED).
Data: FlyWire connectome (CC BY-NC 4.0) and Shiu et al. (MIT code).
Media: carousel_6.png to carousel_8.png
