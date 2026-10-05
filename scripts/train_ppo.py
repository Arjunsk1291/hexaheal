"""Train the PPO residual policy. Resumable (checkpoints), CPU only, honors --max-minutes."""
import argparse, json, os, time
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from neurowalker.rl import ResidualEnv

ap = argparse.ArgumentParser()
ap.add_argument("--max-minutes", type=float, default=25)
ap.add_argument("--total-steps", type=int, default=800_000)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--out", default="runs/ppo")
a = ap.parse_args()
torch.set_num_threads(1)
os.makedirs(a.out, exist_ok=True)
CURR = [("flat",), ("flat", "rough1"), ("flat", "rough1", "rough2", "slope10"), ("flat", "rough1", "rough2", "rough3", "slope10", "slope15")]


class Curriculum(BaseCallback):
    def __init__(self, max_min, t0):
        super().__init__(); self.max_min, self.t0, self.stage = max_min, t0, -1
        self.log = []
    def _on_step(self):
        frac = self.num_timesteps / a.total_steps
        st = min(int(frac * len(CURR)), len(CURR) - 1)
        if st != self.stage:
            self.stage = st
            for e in self.training_env.envs:
                e.unwrapped.set_terrains(CURR[st])
        if self.n_calls % 2000 == 0:
            ep = [x["r"] for x in self.model.ep_info_buffer]
            self.log.append({"steps": self.num_timesteps, "minutes": (time.time() - self.t0) / 60, "mean_ep_reward": float(np.mean(ep)) if ep else None, "stage": st})
            json.dump(self.log, open(f"{a.out}/curve.json", "w"))
        return (time.time() - self.t0) / 60 < self.max_min


def make(i):
    return lambda: Monitor(ResidualEnv(CURR[0], seed=a.seed * 100 + i))

venv = DummyVecEnv([make(i) for i in range(4)])
ckpt = f"{a.out}/ppo_latest.zip"
kw = dict(n_steps=512, batch_size=256, learning_rate=3e-4, gamma=0.99, gae_lambda=0.95, n_epochs=6, ent_coef=0.0, clip_range=0.2,
          policy_kwargs=dict(net_arch=[64, 64]), seed=a.seed, device="cpu", tensorboard_log=f"{a.out}/tb", verbose=0)
t0 = time.time()
prior = 0
if os.path.exists(ckpt):
    model = PPO.load(ckpt, env=venv, device="cpu"); prior = model.num_timesteps; print("resumed at", prior)
else:
    model = PPO("MlpPolicy", venv, **kw)
cb = Curriculum(a.max_minutes, t0)
model.learn(total_timesteps=a.total_steps - prior, callback=[cb, CheckpointCallback(50_000, a.out, name_prefix="ckpt")], reset_num_timesteps=False)
model.save(ckpt)
json.dump({"steps": model.num_timesteps, "wall_minutes": (time.time() - t0) / 60, "hyperparameters": {k: v for k, v in kw.items() if k != "tensorboard_log"},
           "curriculum": CURR, "env": "CPU sandbox, 2 vCPU, DummyVecEnv x4"}, open(f"{a.out}/train_summary.json", "w"), indent=1, default=str)
print("done", model.num_timesteps)
