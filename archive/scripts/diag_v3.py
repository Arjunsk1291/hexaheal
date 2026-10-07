"""V3 diagnosis helper: run one scenario for a controller on given seeds and print healing timeline, fall time, tilt at fall. Tuning seeds (100-109) for diagnosis."""
import sys


sys.path.insert(0, "scripts")
from make_media import make_ctrl
from neurowalker.benchmark import TARGET_SPEED, scenario_spec
from neurowalker.env import HexapodEnv
from neurowalker.healing import HealingController

ctrl_name, scenario, seeds = sys.argv[1], sys.argv[2], [int(s) for s in sys.argv[3].split(",")]
for sd in seeds:
    sp = scenario_spec(scenario)
    ctrl = make_ctrl(ctrl_name)
    env = HexapodEnv(sp["terrain"], max_time=sp["t"], faults=sp["faults"], pushes=sp["pushes"], rand=0.1, seed=sd, target_speed=TARGET_SPEED)
    c = HealingController(ctrl, terrain=sp["terrain"], seed=sd) if sp["heal"] else ctrl
    if hasattr(ctrl, "seed"): ctrl.seed = sd
    env.reset(seed=sd); c.reset()
    tl = []
    while True:
        a = c.act(env)
        _, _, te, tr, info = env.step(a)
        if int(env.t / env.dt) % 25 == 0 and 3.5 <= env.t <= 7.5:
            nud = ctrl.nudges[-1] if hasattr(ctrl, "nudges") and ctrl.nudges else None
            tl.append((round(env.t, 2), round(info["roll"], 2), round(info["pitch"], 2), None if nud is None else tuple(round(v, 2) for v in nud)))
        if te or tr: break
    print(f"seed {sd} fell {env.fell} t_end {env.t:.2f} roll {info['roll']:.2f} pitch {info['pitch']:.2f}")
    if hasattr(c, "log"):
        for d in c.log: print("  ", d["t"], d["from"], "->", d["to"], str(d["action"])[:90], str(d["evidence"])[:80])
    for x in tl[:14]: print("   tl", x)
