"""Media pipeline: render clips (640x360, 30 fps), neural-activity data, dashboard data, showcase reel, LinkedIn assets."""
import glob
import json
import os
import shutil
import sys

import numpy as np

os.environ.setdefault("MUJOCO_GL", "osmesa"); os.environ.setdefault("PYOPENGL_PLATFORM", "osmesa")
from neurowalker.benchmark import TARGET_SPEED, scenario_spec
from neurowalker.env import HexapodEnv
from neurowalker.healing import HealingController
from neurowalker.render import EpisodeRecorder
from neurowalker.tripod import TripodController

MEDIA, PUB = "docs/media", "dashboard/public"
os.makedirs(MEDIA, exist_ok=True); os.makedirs(f"{PUB}/media", exist_ok=True); os.makedirs(f"{PUB}/data", exist_ok=True)
LABEL = {"tripod": "TRIPOD CPG", "connectome": "CONNECTOME-INSPIRED", "ppo": "PPO RESIDUAL"}
CLIPS = ["flat", "rough3", "slope10", "slope15", "push", "fault_disable_leg+healing", "fault_lock_joint+healing"]
only = sys.argv[1].split(",") if len(sys.argv) > 1 else None


def make_ctrl(name):
    if name == "tripod": return TripodController()
    if name == "connectome":
        from neurowalker.brain import BrainController; return BrainController()
    from neurowalker.rl import PPOController; return PPOController("models/ppo_residual.zip")


def render(ctrl_name, ctrl, scenario, seed=0, record_neural=False):
    sp = scenario_spec(scenario)
    env = HexapodEnv(sp["terrain"], max_time=sp["t"], faults=sp["faults"], pushes=sp["pushes"], rand=0.1, seed=seed, target_speed=TARGET_SPEED)
    c = HealingController(ctrl, terrain=sp["terrain"], seed=seed) if sp["heal"] else ctrl
    if hasattr(ctrl, "seed"): ctrl.seed = seed
    env.reset(seed=seed); c.reset()
    label = f"{LABEL[ctrl_name]}{' + HEALING' if sp['heal'] else ''} | {scenario.replace('+healing','').replace('_',' ')}"
    rec = EpisodeRecorder(env, 640, 360, 30, cam_dist=1.25, label=label)
    frames_n, last_x, last_t = [], 0.0, 0.0
    acc = None
    while True:
        a = c.act(env)
        _, _, te, tr, info = env.step(a)
        v = (env.data.qpos[0] - last_x) / max(env.t - last_t, 1e-6) if env.t - last_t >= 0.2 else None
        if v is not None: last_x, last_t, rec.v = env.data.qpos[0], env.t, v
        rec.maybe_capture(speed=getattr(rec, "v", 0.0), extra=(f"| state {c.state}" if sp["heal"] else ""))
        if record_neural:
            acc = ctrl.last_counts.astype(np.int32) if acc is None else acc + ctrl.last_counts
            if int(round(env.t / env.dt)) % 5 == 0:
                frames_n.append(np.minimum(acc, 99).astype(np.int8).tolist()); acc = None
        if te or tr: break
    if record_neural:
        rec.neural_frames = frames_n
    return rec, env


def main():
    manifest = {"videos": {}, "arena_scenarios": []}
    ctrls = [c for c in ["tripod", "connectome", "ppo"] if os.path.exists("models/ppo_residual.zip") or c != "ppo"]
    objs = {c: make_ctrl(c) for c in ctrls}
    for sc in CLIPS:
        if only and sc not in only: continue
        key = sc.replace("+healing", "")
        for cn in ctrls:
            fn = f"{cn}__{key}.mp4"
            rec, env = render(cn, objs[cn], sc)
            rec.save(f"{MEDIA}/{fn}"); shutil.copy(f"{MEDIA}/{fn}", f"{PUB}/media/{fn}")
            manifest["videos"].setdefault(key, {})[cn] = fn
            print("rendered", fn, len(rec.frames), "frames, fell" if env.fell else "ok", flush=True)
        manifest["arena_scenarios"].append(key)
    json.dump(manifest, open("results/media_manifest.json", "w"), indent=1)


def neural_data():
    import pandas as pd
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla
    b = make_ctrl("connectome")
    rec, env = render("connectome", b, "flat", seed=0, record_neural=True)
    rec.save(f"{MEDIA}/neural_walk.mp4"); shutil.copy(f"{MEDIA}/neural_walk.mp4", f"{PUB}/media/neural_walk.mp4")
    W = sp.load_npz("data/processed/subgraph_weights.npz"); A = abs(W); A = (A + A.T).astype(float)
    d = np.asarray(A.sum(1)).ravel() + 1e-6; L = sp.diags(1 / np.sqrt(d)) @ A @ sp.diags(1 / np.sqrt(d))
    vals, vecs = sla.eigsh(L, k=4, which="LA"); xy = vecs[:, [1, 2]]
    xy = (xy - xy.min(0)) / (xy.max(0) - xy.min(0)); xy = 0.03 + 0.94 * xy
    out = {"fps": 10, "xy": np.round(xy, 4).tolist(), "frames": rec.neural_frames, "baseline_distance": None, "lesions": {},
           "note": "Per-neuron spike counts per 100 ms from the real simulation run; layout is a spectral embedding of the subgraph (no anatomical meaning)."}
    if os.path.exists("results/lesion_sweep_summary.json"):
        json.load(open("results/lesion_sweep.json")) if False else None
        df = pd.read_parquet("results/lesion_sweep.parquet"); base = df[df.group == "none"]
        out["baseline_distance"] = float((base.speed_post * 8 + base.speed_pre * 2).mean())
        summ = json.load(open("results/lesion_sweep_summary.json"))
        pick = sorted([g for g in summ if g != "none"], key=lambda g: summ[g]["speed_change_pct"])[:3] + ["random_central_500"]
        for g in pick:
            gi = b.named_groups[g]; mask = np.zeros(len(xy), bool); mask[gi] = True
            sub = df[df.group == g]
            out["lesions"][g] = {"mask": mask.astype(int).tolist(), "distance": float((sub.speed_post * 8 + sub.speed_pre * 2).mean())}
    json.dump(out, open(f"{PUB}/data/neural.json", "w"), separators=(",", ":"))
    print("neural frames", len(out["frames"]), "size MB", round(os.path.getsize(f"{PUB}/data/neural.json") / 1e6, 2))


def dashboard_data():
    summ = json.load(open("results/summary.json")); json.dump(json.loads(json.dumps(summ).replace("NaN", "null")), open(f"{PUB}/data/summary.json", "w"), separators=(",", ":"))  # browsers reject NaN
    man = json.load(open("results/media_manifest.json"))
    info = json.load(open("data/processed/subgraph_info.json")); val = json.load(open("results/validation/shiu_sugar_validation.json"))
    c = summ["connectome"]; head = []
    head.append({"value": f"{info['n_neurons']:,} neurons", "label": f"{info['n_synapse_pairs']:,} synapse pairs, {1/val['subgraph_wall_s_per_sim_s']:.0f}x faster than real time on a CPU (sandbox measurement)"})
    h = c.get("fault_disable_leg+healing"); p = c.get("fault_disable_leg")
    if h and p: head.append({"value": f"{h['fault_retained']['mean']*100:.0f}% speed kept", "label": f"after losing a leg, with self-healing (without: {p['fault_retained']['mean']*100:.0f}%)"})
    r = c.get("rough3")
    if r: head.append({"value": f"{(1-r['fall_rate']['mean'])*100:.0f}% upright", "label": f"on the roughest terrain, connectome-inspired controller ({r['fall_rate']['n']} seeds)"})
    man["headline"] = head
    json.dump(man, open(f"{PUB}/data/manifest.json", "w"), indent=1)
    heal = {}
    for f in sorted(glob.glob("results/decision_logs/*.json")):
        d = json.load(open(f)); heal[f"{d['scenario'].replace('fault_','').replace('+healing','')} ({d['controller']})"] = {"controller": d["controller"], "decisions": d["decisions"]}
    json.dump(heal, open(f"{PUB}/data/healing.json", "w"), indent=1)
    print("dashboard data ok", head)


if __name__ == "__main__":
    main()
    neural_data()
    dashboard_data()
