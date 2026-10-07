"""Connectome-inspired controller: a 10k-neuron spiking subgraph of the FlyWire v783 connectome modulates a tripod CPG.

DESIGN CHOICE, NOT A BIOLOGICAL CLAIM: the mapping from robot state to stimulated neuron groups and from descending-neuron
populations to commands is engineered by us. The wiring inside the network comes from the connectome; the I/O assignment does not.

Encoding: eight disjoint groups of mechanosensory neurons (150 each, fixed random partition) receive Poisson drive whose rate
depends on robot state (speed deficit/excess, left/right turn error, pitch up/down, roll left/right).
Decoding: for each channel, the descending neurons (DNs) most selectively driven by it in a calibration run form a readout group.
Population rate differences of paired groups give speed, turn and stance commands for the CPG.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from .snn import SpikingNet
from .tripod import TripodController, TripodParams

CHANNELS = ["speed_up", "speed_down", "turn_left", "turn_right", "pitch_up", "pitch_down", "roll_left", "roll_right"]
R_MAX = 100.0  # Hz drive at full channel activation
K_DN = 12  # readout DNs per channel


class BrainController:
    name = "connectome_inspired"

    def __init__(self, data_dir="data/processed", seed=0, gains=None, synthetic_fallback=False, tripod: TripodParams | None = None, W=None):
        self.meta = pd.read_parquet(f"{data_dir}/subgraph_meta.parquet")
        W = sp.load_npz(f"{data_dir}/subgraph_weights.npz") if W is None else W
        self.net = SpikingNet(W, seed=seed)
        self.seed = seed
        self.cpg = TripodController(tripod)
        self.g = {"speed": 0.6, "turn": 0.45, "stance": -0.1, "roll": 0.08, "speed_freq": 0.35}
        if gains:
            self.g.update(gains)
        rng = np.random.default_rng(1234)  # fixed I/O assignment, independent of the run seed
        mech = np.where(self.meta.cell_class == "mechanosensory")[0]
        perm = rng.permutation(mech)
        self.in_groups = {c: perm[i * 150:(i + 1) * 150] for i, c in enumerate(CHANNELS)}
        self.dn = np.where(self.meta.super_class == "descending")[0]
        self._calibrate()
        self.named_groups = self._named_groups()
        self.lesioned: list[str] = []
        self.dec = np.zeros(4)
        self.reset()

    # ------------------------------------------------------------------ setup
    def _drive(self, levels):
        idx = np.concatenate([self.in_groups[c] for c in CHANNELS])
        rates = np.concatenate([np.full(150, R_MAX * levels[i]) for i, c in enumerate(CHANNELS)])
        keep = rates > 0
        self.net.set_rate_array(idx[keep], rates[keep])

    def _calibrate(self, ms=400.0):
        n = self.net
        R = []
        for c in range(8):
            lv = np.zeros(8); lv[c] = 1.0
            n.reset(); n.rng = np.random.default_rng(7 + c); self._drive(lv)
            R.append(n.run(ms)[self.dn] / (ms * 1e-3))
        R = np.array(R)
        self.readout = {}
        for c in range(8):
            others = np.delete(R, c, 0).max(0)
            score = R[c] - others
            order = np.argsort(-score)
            top = order[:K_DN]
            self.readout[CHANNELS[c]] = self.dn[top]
        # paired-channel calibration: command x in {-1,0,+1} on one pair, others neutral (0.5)
        self.d0, self.slope = np.zeros(4), np.ones(4)
        self.pair_curve = []
        for p in range(4):
            ds = []
            for x in (-1.0, 0.0, 1.0):
                lv = np.full(8, 0.5); lv[2 * p] = 0.5 + 0.5 * x; lv[2 * p + 1] = 0.5 - 0.5 * x
                trial = []
                for k in range(3):
                    n.reset(); n.rng = np.random.default_rng(300 + 10 * p + k); self._drive(lv)
                    cnt = n.run(ms) / (ms * 1e-3)
                    trial.append(cnt[self.readout[CHANNELS[2 * p]]].mean() - cnt[self.readout[CHANNELS[2 * p + 1]]].mean())
                ds.append(float(np.mean(trial)))
            self.pair_curve.append(ds)
            self.d0[p] = ds[1]
            self.slope[p] = (ds[2] - ds[0]) / 2
        n.reset()

    def _named_groups(self):
        m = self.meta
        groups = {f"in_{c}": v for c, v in self.in_groups.items()}
        groups.update({f"dn_{c}": v for c, v in self.readout.items()})
        groups["dn_all"] = self.dn
        groups["sensory_all_mech"] = np.concatenate(list(self.in_groups.values()))
        cen = m[(m.super_class == "central") & (m.cell_type != "")]
        top = cen.cell_type.value_counts()
        top = top[top >= 15].head(12).index
        for t in top:
            groups[f"type_{t}"] = np.where((m.cell_type == t) & (m.super_class == "central"))[0]
        for sd in ["left", "right"]:
            groups[f"central_{sd}"] = np.where((m.super_class == "central") & (m.side == sd))[0]
        rng = np.random.default_rng(5)
        cen_idx = np.where(m.super_class == "central")[0]
        groups["random_central_500"] = rng.choice(cen_idx, 500, replace=False)
        return groups

    # ------------------------------------------------------------------ API
    def reset(self):
        self.cpg.reset()
        self.net.reset()
        self.net.rng = np.random.default_rng(self.seed)
        for name in self.lesioned:
            self.net.silence(self.named_groups[name])
        self.dec = np.zeros(4)
        self.last_rates = np.zeros(8)
        self.last_spikes = 0
        self.rt_ms = []
        self.nudges = []

    def lesion(self, group: str):
        """Silence a named neuron group (all its incoming and outgoing synapses are inactive; the neurons are clamped at rest)."""
        if group not in self.named_groups:
            raise KeyError(group)
        self.lesioned.append(group)
        self.net.silence(self.named_groups[group])

    def unlesion_all(self):
        self.lesioned = []
        self.net.unsilence_all()

    def encode(self, env, turn_cmd=0.0):
        roll, pitch, yaw = env.euler()
        vx = env.body_vel()[0]
        err = (env.target_speed - vx) / 0.15
        turn_err = np.clip(turn_cmd - yaw / 0.5, -1, 1)
        lv = np.array([
            np.clip(0.5 + 0.5 * err, 0, 1), np.clip(0.5 - 0.5 * err, 0, 1),
            np.clip(0.5 + 0.5 * turn_err, 0, 1), np.clip(0.5 - 0.5 * turn_err, 0, 1),
            np.clip(0.5 + 0.5 * pitch / 0.25, 0, 1), np.clip(0.5 - 0.5 * pitch / 0.25, 0, 1),
            np.clip(0.5 + 0.5 * roll / 0.25, 0, 1), np.clip(0.5 - 0.5 * roll / 0.25, 0, 1)])
        return lv

    def decode(self, counts, ms):
        rate = np.array([counts[self.readout[c]].mean() for c in CHANNELS]) / (ms * 1e-3)
        diff = rate[0::2] - rate[1::2]
        x = np.where(self.slope > 1.0, (diff - self.d0) / np.where(self.slope > 1.0, self.slope, 1.0), 0.0)
        x = np.clip(x, -1.5, 1.5)
        self.dec = 0.7 * self.dec + 0.3 * x  # ~65 ms smoothing at 20 ms control period
        d = self.dec
        return {"speed": d[0], "turn": d[1], "pitch": d[2], "roll": d[3]}

    def act(self, env, turn_cmd=0.0, legs_disabled=None):
        import time
        t0 = time.perf_counter()
        lv = self.encode(env, turn_cmd)
        self.last_rates = R_MAX * lv
        self._drive(lv)
        ms = env.dt * 1000.0
        counts = self.net.run(ms)
        self.last_spikes = int(counts.sum())
        self.last_counts = counts
        c = self.decode(counts, ms)
        self.last_cmd = c
        g = self.g
        speed_gain = float(np.clip(1.0 + g["speed"] * c["speed"], 0.5, 1.5))
        freq_scale = float(np.clip(1.0 + g["speed_freq"] * c["speed"], 0.6, 1.4))
        turn = float(np.clip(g["turn"] * c["turn"], -0.6, 0.6))
        stance = float(np.clip(g["stance"] * c["pitch"], -0.2, 0.2))
        a = self.cpg.act(env, speed_gain=speed_gain, turn=turn, stance_adj=stance, freq_scale=freq_scale)
        self.rt_ms.append((time.perf_counter() - t0) * 1000)
        self.nudges.append((speed_gain, freq_scale, turn, stance))
        return a
