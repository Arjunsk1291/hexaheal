# ruff: noqa: E402
"""Fit the MLP ablation to the connectome: sample random 8-channel level vectors (held 5 control steps = 100 ms, state carried), record the connectome's
raw decoded command x (before smoothing), fit 8-16-16-4 tanh MLP by Adam (torch). Uses seed range 100+ for the sampling rng; writes data/processed/mlp_ablation.npz."""
try:
    import torch
    import torch._dynamo  # noqa: F401
except ImportError:
    pass
import numpy as np

from neurowalker.brain import CHANNELS, BrainController

rng = np.random.default_rng(100)
b = BrainController(); n = b.net; ms = 20.0
X, Y = [], []
n.reset(); n.rng = np.random.default_rng(100)
for i in range(2500):
    lv = np.clip(0.5 + rng.normal(0, 0.25, 8), 0, 1) if i % 3 else rng.uniform(0, 1, 8)
    b._drive(lv)
    for k in range(5):
        counts = n.run(ms)
    rate = np.array([counts[b.readout[c]].mean() for c in CHANNELS]) / (ms * 1e-3)
    diff = rate[0::2] - rate[1::2]
    x = np.where(b.slope > 1.0, (diff - b.d0) / np.where(b.slope > 1.0, b.slope, 1.0), 0.0)
    X.append(lv); Y.append(np.clip(x, -1.5, 1.5))
X, Y = np.array(X, np.float32), np.array(Y, np.float32)
idx = rng.permutation(len(X)); tr, va = idx[:2000], idx[2000:]
torch.manual_seed(0)
net = torch.nn.Sequential(torch.nn.Linear(8, 16), torch.nn.Tanh(), torch.nn.Linear(16, 16), torch.nn.Tanh(), torch.nn.Linear(16, 4))
opt = torch.optim.Adam(net.parameters(), 3e-3)
Xt, Yt = torch.tensor(X[tr]), torch.tensor(Y[tr])
for ep in range(3000):
    opt.zero_grad(); loss = torch.nn.functional.mse_loss(net(Xt), Yt); loss.backward(); opt.step()
with torch.no_grad():
    pv = net(torch.tensor(X[va])).numpy()
r2 = 1 - ((pv - Y[va]) ** 2).sum(0) / ((Y[va] - Y[va].mean(0)) ** 2).sum(0)
print("train mse", float(loss), "val R2 per command (speed, turn, pitch, roll):", r2.round(3).tolist(), "target std", Y.std(0).round(3).tolist())
w = [p.detach().numpy().astype(np.float64) for p in net.parameters()]
np.savez("data/processed/mlp_ablation.npz", W1=w[0].T, b1=w[1], W2=w[2].T, b2=w[3], W3=w[4].T, b3=w[5], r2=r2)
