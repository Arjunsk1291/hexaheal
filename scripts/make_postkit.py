"""LinkedIn DRAFTS. Numbers come from results/summary.json. Nothing is posted; Arjun reviews exact text."""
import json

S = json.load(open("results/summary.json")); V = json.load(open("results/validation/shiu_sugar_validation.json")); I = json.load(open("data/processed/subgraph_info.json"))
d = lambda c, s: S[c][s]["distance"]["mean"]; fl = lambda c, s: f"{S[c][s]['fall_rate']['falls']}/{S[c][s]['fall_rate']['n']}"
fr = lambda c, f, h="": S[c][f"fault_{f}{h}"]["fault_retained"]["mean"] * 100
open("docs/post_kit/linkedin_series_DRAFT.md", "w").write(f"""# LinkedIn series - DRAFTS ONLY. Nothing is posted until Arjun approves the exact text.
Every number below is read from results/summary.json (10 seeds per cell, simulation, 2 vCPU CPU sandbox).
Wording rule: "connectome-inspired". Never "uploaded", "emulated" or "thinks like a fly".

## Post 1 - What I built
I built a simulated six-legged robot and gave its walking a connectome-inspired controller.

The controller is a {I['n_neurons']:,}-neuron spiking subgraph cut from the published FlyWire fruit-fly connectome. Robot sensor readings go into input cells, output cells nudge the speed and turning of a standard tripod gait. The input/output mapping is my design choice. It is not a copy of a fly brain.

I compared it with a plain tripod gait and a PPO residual policy, 10 seeds per scenario.
Flat ground, 10 s: tripod {d('tripod','flat'):.2f} m, connectome-inspired {d('connectome','flat'):.2f} m, PPO residual {d('ppo','flat'):.2f} m.

Simulation only. Code and results in the repo. [repo link after push]
Media: docs/social/reel_showcase.mp4 or cover_1080x1080.png

## Post 2 - Where it breaks
The part I like most is where each controller fails.
15 degree slope, falls out of 10: tripod {fl('tripod','slope15')}, connectome-inspired {fl('connectome','slope15')}, PPO residual {fl('ppo','slope15')}.
48 N push, falls out of 10: tripod {fl('tripod','push')}, connectome-inspired {fl('connectome','push')}, PPO residual {fl('ppo','push')}.
The PPO residual survives the slopes but is slower and falls on every push. The connectome-inspired controller is fastest on flat ground and does not beat the tripod on slopes.
One training seed for PPO, 1.18M steps on CPU. Treat it as a first result, not a ranking.
Media: carousel_3.png to carousel_5.png

## Post 3 - Self-healing and honest limits
When a leg is disabled, a monitor detects it, diagnoses which leg, and searches for a new gait. Speed kept after a disabled leg, without -> with healing: tripod {fr('tripod','disable_leg'):.0f}% -> {fr('tripod','disable_leg','+healing'):.0f}%, connectome-inspired {fr('connectome','disable_leg'):.0f}% -> {fr('connectome','disable_leg','+healing'):.0f}%, PPO residual {fr('ppo','disable_leg'):.0f}% -> {fr('ppo','disable_leg','+healing'):.0f}% (healing made PPO worse here).
Limits: simulation only, no hardware. Timings are from a 2 vCPU CPU sandbox, not a GPU laptop. Several healing runs ended before the search finished. ROS 2 nodes and the Docker image are written but not run yet (UNVERIFIED).
Data: FlyWire connectome (CC BY-NC 4.0) and Shiu et al. (MIT code).
Media: carousel_6.png to carousel_8.png
""")
open("docs/post_kit/alt_text.md", "w").write("""# Alt text (drafts)
- cover_1080x1080.png: Dark card reading NeuroWalker, connectome-inspired hexapod, simulation only.
- carousel_1.png: Title slide: NeuroWalker, connectome-inspired hexapod, simulation only.
- carousel_2.png: Text slide describing a 10,000-neuron piece of a published fruit-fly connectome steering a simulated 18-joint hexapod.
- carousel_3.png: Flat-ground distance in 10 seconds for the tripod, connectome-inspired and PPO residual controllers.
- carousel_4.png: Number of falls out of 10 on a 15 degree slope for each controller.
- carousel_5.png: Number of falls out of 10 under a 48 newton push for each controller.
- carousel_6.png: Speed kept after a disabled leg, without and with self-healing, for each controller.
- carousel_7.png: Honest limits: simulation only, not an emulated fly brain, 10 seeds, sandbox timings.
- carousel_8.png: Pointer to code, data and results, with the FlyWire CC BY-NC 4.0 data note.
- reel_showcase.mp4 / hero.mp4: Side-by-side simulated hexapods (tripod, connectome-inspired, PPO residual) walking on flat ground, then slope, push and leg-fault scenes. Labeled SIMULATION.
- vertical_*.mp4: One simulated hexapod walking, 15 seconds, labeled simulation only.
""")
open("docs/post_kit/repo_meta.md", "w").write("""# Repo description and topics
Description: Simulated 18-DOF hexapod with a connectome-inspired spiking controller, benchmarked against PPO and a tripod CPG. Simulation only.
Topics: robotics, mujoco, ros2, connectome, drosophila, reinforcement-learning, hexapod, simulation
""")
print("postkit ok")
