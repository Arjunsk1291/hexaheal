"""Fresh simulation validation. Resumable without touching historical results."""
import argparse
import dataclasses
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import mujoco
import numpy as np

sys.path.insert(0, 'scripts')
from hh_common import CASES, library, make, tuned
from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.freegait import FreeGait
from neurowalker.healing import HealingController
from neurowalker.hexapod import HexapodParams, generate_mjcf
from neurowalker.hh_eval import case_legs, run_episode
from neurowalker.tripod import TripodController

CONTROLLERS = ('tripod', 'tuned', 'healing_v1', 'tierA', 'tierB', 'warm_start', 'oracle')
INPUTS = ['results/v3/v2_config_final.json', 'results/tuned_tripod_tuning.json',
          'results/v3_oracle.jsonl', 'results/v3_oracle_long.jsonl', 'results/v3_oracle_long2.jsonl']
INPUTS += sorted(str(p) for p in Path('src/neurowalker').glob('*.py'))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def experiment():
    return {'schema': 1, 'simulation_only': True, 'mujoco': mujoco.__version__,
            'numpy': np.__version__, 'eval_seeds': list(range(10)), 'tuning_seeds': list(range(100, 110)),
            'cases': CASES, 'controllers': list(CONTROLLERS), 'fault_t_s': 4.0, 'episode_s': 14.0,
            'oracle_fault_t_s': 0.0, 'oracle_episode_s': 15.0, 'recovery_last_s': 8.0,
            'recovery_speed_m_s': 0.125, 'case_min_recovered_seeds': 7,
            'model': dataclasses.asdict(HexapodParams()),
            'mjcf_sha256': hashlib.sha256(generate_mjcf().encode()).hexdigest(),
            'inputs_sha256': {p: digest(p) for p in INPUTS}}

def controller(name, case):
    cfg = json.loads(Path('results/v3/v2_config_final.json').read_text())
    if name == 'tripod': return TripodController()
    if name == 'tuned': return tuned()
    if name == 'healing_v1': return HealingController(tuned())
    if name == 'tierA': return make('A', **cfg['A'])
    c = make('B', **cfg['B'])
    if name == 'warm_start':
        s = tuple(sorted(case_legs(case)))
        c.warm_library = library()
        c.exclude = {s, tuple(sorted((i + 3) % 6 for i in s))}
    return c

def oracle(case, seed):
    legs = case_legs(case)
    e = HexapodEnv('flat', max_time=15.0, faults=[Fault('disable_leg', 0.0, leg=i) for i in legs],
                   rand=0.1, seed=seed, target_speed=0.25)
    e.reset(seed=seed)
    g = FreeGait(np.array(library()[tuple(legs)])); g.reset()
    ts, xs = [], []
    while True:
        _, _, term, trunc, _ = e.step(g.act(e))
        ts.append(e.t); xs.append(float(e.data.qpos[0]))
        if term or trunc: break
    full = not e.fell and ts[-1] >= 14.95
    v = float((xs[-1] - xs[min(np.searchsorted(ts, 7.0), len(xs)-1)]) / 8) if full else 0.0
    return dict(case=case, seed=seed, fell=bool(e.fell), t_end=float(e.t), v_last8=v,
                distance=float(xs[-1] - e.x0), recovered=bool(full and v >= 0.125))

def load_rows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    keys = [(r['controller'], r['case'], r['seed']) for r in rows]
    if len(keys) != len(set(keys)): raise ValueError('Duplicate run keys')
    return rows

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=Path('release/validation'))
    p.add_argument('--max-seconds', type=float, default=0)
    p.add_argument('--controller', choices=CONTROLLERS, action='append')
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    spec = json.loads(json.dumps(experiment())); mf = a.output / 'experiment.json'
    if mf.exists() and json.loads(mf.read_text()) != spec:
        raise ValueError('Inputs/configs changed. Start a new output directory; no mixed runs.')
    mf.write_text(json.dumps(spec, indent=2)+'\n')
    hf = a.output / 'hardware.json'
    if not hf.exists():
        hf.write_text(json.dumps({'platform':platform.platform(), 'python':sys.version,
          'cpu':subprocess.check_output(['lscpu'], text=True), 'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}, indent=2)+'\n')
    path = a.output / 'runs.jsonl'; done = {(r['controller'],r['case'],r['seed']) for r in load_rows(path)}
    start = time.perf_counter()
    for name in a.controller or CONTROLLERS:
        for case in CASES:
            for seed in range(10):
                key = (name,case,seed)
                if key in done: continue
                if a.max_seconds and time.perf_counter() - start >= a.max_seconds:
                    print(f'Checkpoint: {len(done)}/{len(CONTROLLERS)*210}'); return
                t = time.perf_counter()
                r = oracle(case,seed) if name=='oracle' else run_episode(controller(name,case),case,seed)
                r.update(controller=name, wall_runtime_s=time.perf_counter()-t, status='MEASURED')
                with path.open('a') as f: f.write(json.dumps(r,allow_nan=False)+'\n'); f.flush()
                done.add(key)
            print(name,case,len(done),flush=True)
    print('DONE', len(done))

if __name__ == '__main__': main()
