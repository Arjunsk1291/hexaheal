"""Ablation controllers for the 'does the connectome wiring matter' test (Stage 3, see docs/PREREGISTRATION.md).
Every variant keeps the SAME sensory encoding, input groups, readout procedure (calibration), decode and CPG nudge limits as BrainController.
Only the recurrent wiring changes (b, c) or the network is replaced by a filter (d)."""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .brain import CHANNELS, BrainController


def shuffled_weights(W, seed=0):
    """Degree-preserving shuffle: edge presynaptic ends (with their signed weights) are permuted among edges; each neuron keeps its
    in-degree and its out-degree. Self-loops are removed, duplicate edges are summed."""
    C = W.tocoo(); rng = np.random.default_rng(10_000 + seed)
    perm = rng.permutation(C.nnz)
    cols, data = C.col[perm], C.data[perm]
    M = sp.coo_matrix((data, (C.row, cols)), shape=W.shape).tocsr(); M.setdiag(0); M.eliminate_zeros()
    return M


def random_weights(W, seed=0):
    """Random directed graph with the same neuron count and (about) the same number of synapse pairs; weights drawn from the original weights."""
    C = W.tocoo(); rng = np.random.default_rng(20_000 + seed); n = W.shape[0]
    rows, cols = rng.integers(0, n, C.nnz), rng.integers(0, n, C.nnz)
    data = rng.permutation(C.data)
    M = sp.coo_matrix((data, (rows, cols)), shape=W.shape).tocsr(); M.setdiag(0); M.eliminate_zeros()
    return M


class ShuffledBrain(BrainController):
    name = "ablation_shuffled"

    def __init__(self, data_dir="data/processed", seed=0, **kw):
        W = sp.load_npz(f"{data_dir}/subgraph_weights.npz")
        super().__init__(data_dir, seed, W=shuffled_weights(W), **kw)


class RandomGraphBrain(BrainController):
    name = "ablation_random_graph"

    def __init__(self, data_dir="data/processed", seed=0, **kw):
        W = sp.load_npz(f"{data_dir}/subgraph_weights.npz")
        super().__init__(data_dir, seed, W=random_weights(W), **kw)


class FilterBrain:
    """No network. The 8 input channel levels are mapped straight to the 4 commands: x_p = level[2p] - level[2p+1] (this is exactly the
    convention the connectome calibration uses, x=+-1 at levels 0.5+-0.5), then the same 0.7/0.3 smoothing (~65 ms at 20 ms control period)."""
    name = "ablation_filter"

    def __init__(self, gains=None, tripod=None, **_):
        from .tripod import TripodController
        self.cpg = TripodController(tripod)
        self.g = {"speed": 0.6, "turn": 0.45, "stance": -0.1, "roll": 0.08, "speed_freq": 0.35}
        if gains:
            self.g.update(gains)
        self.seed = 0
        self.reset()

    encode = BrainController.encode

    def reset(self):
        self.cpg.reset()
        self.dec = np.zeros(4)
        self.nudges = []
        self.last_counts = np.zeros(1, np.int32)

    def act(self, env, turn_cmd=0.0, legs_disabled=None):
        lv = BrainController.encode(self, env, turn_cmd)
        x = np.clip(lv[0::2] - lv[1::2], -1.5, 1.5)
        self.dec = 0.7 * self.dec + 0.3 * x
        d = self.dec; g = self.g
        speed_gain = float(np.clip(1.0 + g["speed"] * d[0], 0.5, 1.5))
        freq_scale = float(np.clip(1.0 + g["speed_freq"] * d[0], 0.6, 1.4))
        turn = float(np.clip(g["turn"] * d[1], -0.6, 0.6))
        stance = float(np.clip(g["stance"] * d[2], -0.2, 0.2))
        self.nudges.append((speed_gain, freq_scale, turn, stance))
        return self.cpg.act(env, speed_gain=speed_gain, turn=turn, stance_adj=stance, freq_scale=freq_scale)


def make_variant(name):
    if name == "connectome":
        return BrainController()
    if name == "shuffled":
        return ShuffledBrain()
    if name == "random_graph":
        return RandomGraphBrain()
    if name == "filter":
        return FilterBrain()
    if name == "mlp":
        return MLPBrain()
    raise KeyError(name)


VARIANTS = ["connectome", "shuffled", "random_graph", "filter"]
_ = CHANNELS


class MLPBrain:
    """Small MLP (8 -> 16 -> 16 -> 4, tanh) fitted offline to the connectome's raw (pre-smoothing) input-output mapping, then used in its place.
    Same encoding, same 0.7/0.3 smoothing, same nudge limits. Weights: data/processed/mlp_ablation.npz (built by scripts/fit_mlp_ablation.py)."""
    name = "ablation_mlp"

    def __init__(self, path="data/processed/mlp_ablation.npz", gains=None, tripod=None, **_):
        from .tripod import TripodController
        z = np.load(path)
        self.w = [z[k] for k in ("W1", "b1", "W2", "b2", "W3", "b3")]
        self.cpg = TripodController(tripod)
        self.g = {"speed": 0.6, "turn": 0.45, "stance": -0.1, "roll": 0.08, "speed_freq": 0.35}
        if gains:
            self.g.update(gains)
        self.seed = 0
        self.reset()

    def reset(self):
        self.cpg.reset()
        self.dec = np.zeros(4)
        self.nudges = []
        self.last_counts = np.zeros(1, np.int32)

    def mlp(self, lv):
        W1, b1, W2, b2, W3, b3 = self.w
        h = np.tanh(lv @ W1 + b1); h = np.tanh(h @ W2 + b2)
        return h @ W3 + b3

    def act(self, env, turn_cmd=0.0, legs_disabled=None):
        lv = BrainController.encode(self, env, turn_cmd)
        x = np.clip(self.mlp(lv), -1.5, 1.5)
        self.dec = 0.7 * self.dec + 0.3 * x
        d = self.dec; g = self.g
        speed_gain = float(np.clip(1.0 + g["speed"] * d[0], 0.5, 1.5))
        freq_scale = float(np.clip(1.0 + g["speed_freq"] * d[0], 0.6, 1.4))
        turn = float(np.clip(g["turn"] * d[1], -0.6, 0.6))
        stance = float(np.clip(g["stance"] * d[2], -0.2, 0.2))
        self.nudges.append((speed_gain, freq_scale, turn, stance))
        return self.cpg.act(env, speed_gain=speed_gain, turn=turn, stance_adj=stance, freq_scale=freq_scale)
