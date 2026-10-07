"""Sparse leaky integrate-and-fire network following Shiu et al. (Nature 2024) constants.

Equations (per neuron):  dv/dt = (v0 - v + g)/t_mbr ; dg/dt = -g/tau ; spike if v > v_th -> v = v_rst, g = 0.
Synaptic input: a presynaptic spike adds  w_syn * (signed synapse count)  to g of the target after a delay.
Differences from the reference Brian2 implementation (documented in docs/ENGINEERING_LOG.md):
fixed 0.5 ms Euler step (reference: Brian2 0.1 ms with exact linear integration), synaptic delay 2.0 ms
(4 steps; reference 1.8 ms), event-driven numba spike delivery.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

try:
    from numba import njit
except Exception:  # pragma: no cover - pure-numpy fallback
    def njit(*a, **k):
        def deco(f):
            return f
        return deco if not (len(a) == 1 and callable(a[0])) else a[0]


@njit(cache=True)
def _deliver(spk, n_spk, indptr, indices, data, ring, slot):
    for s in range(n_spk):
        i = spk[s]
        for k in range(indptr[i], indptr[i + 1]):
            ring[slot, indices[k]] += data[k]


@njit(cache=True)
def _update(v, g, ref, ring_slot, silenced, kick, v0, vrst, vth, t_mbr, tau, dt, w_syn, spk, t_rfc_steps, rfc_zero):
    n = v.shape[0]
    cnt = 0
    dec = np.exp(-dt / tau)
    gfac = tau / dt * (1.0 - dec)
    for i in range(n):
        if silenced[i]:
            v[i] = v0
            g[i] = 0.0
            ring_slot[i] = 0.0
            continue
        g[i] += ring_slot[i] * w_syn
        ring_slot[i] = 0.0
        if ref[i] > 0:
            ref[i] -= 1
            g[i] *= dec
            # kicks still apply to Poisson targets (no refractory period for them)
            if not rfc_zero[i]:
                continue
        gm = g[i] * gfac
        v[i] += dt / t_mbr * (v0 - v[i] + gm) + kick[i]
        g[i] *= dec
        if v[i] > vth:
            v[i] = vrst
            g[i] = 0.0
            ref[i] = 0 if rfc_zero[i] else t_rfc_steps
            spk[cnt] = i
            cnt += 1
    return cnt


class SpikingNet:
    V0, VRST, VTH = -52.0, -52.0, -45.0  # mV
    T_MBR, TAU, T_RFC, T_DLY = 20.0, 5.0, 2.2, 1.8  # ms
    W_SYN, F_POI = 0.275, 250.0  # mV per synapse; Poisson kick scale

    def __init__(self, W: sp.spmatrix, dt: float = 0.5, seed: int = 0):
        """W: (post, pre) signed synapse-count matrix."""
        self.n = W.shape[0]
        self.dt = dt
        csc = sp.csc_matrix(W)  # column = presynaptic neuron
        self.indptr = csc.indptr.astype(np.int64)
        self.indices = csc.indices.astype(np.int32)
        self.data = csc.data.astype(np.float32)
        self.nnz = int(csc.nnz)
        self.delay_steps = max(1, int(round(self.T_DLY / dt)))
        self.D = self.delay_steps + 1
        self.rng = np.random.default_rng(seed)
        self.t_rfc_steps = int(round(self.T_RFC / dt))
        self.reset()

    def reset(self):
        self.v = np.full(self.n, self.V0)
        self.g = np.zeros(self.n)
        self.ref = np.zeros(self.n, np.int32)
        self.ring = np.zeros((self.D, self.n), np.float32)
        self.silenced = np.zeros(self.n, bool)
        self.rate_hz = np.zeros(self.n)
        self.rfc_zero = np.zeros(self.n, bool)
        self.spk = np.zeros(self.n, np.int32)
        self.step_i = 0
        self.t_ms = 0.0

    def set_rates(self, idx, rate_hz):
        """Poisson drive (Hz) onto neurons `idx`; targets get no refractory period, as in the reference."""
        idx = np.asarray(idx, int)
        self.rate_hz[:] = 0.0
        self.rate_hz[idx] = rate_hz
        self.rfc_zero[:] = self.rate_hz > 0

    def set_rate_array(self, idx, rates):
        self.rate_hz[:] = 0.0
        self.rate_hz[np.asarray(idx, int)] = rates
        self.rfc_zero[:] = self.rate_hz > 0

    def silence(self, idx):
        self.silenced[np.asarray(idx, int)] = True

    def unsilence_all(self):
        self.silenced[:] = False

    def step(self):
        slot = self.step_i % self.D
        kick = np.zeros(self.n)
        act = self.rate_hz > 0
        if act.any():
            lam = self.rate_hz[act] * self.dt * 1e-3
            kick[act] = self.rng.poisson(lam) * (self.W_SYN * self.F_POI)
        k = _update(self.v, self.g, self.ref, self.ring[slot], self.silenced, kick, self.V0, self.VRST, self.VTH,
                    self.T_MBR, self.TAU, self.dt, self.W_SYN, self.spk, self.t_rfc_steps, self.rfc_zero)
        dslot = (self.step_i + self.delay_steps) % self.D
        _deliver(self.spk, k, self.indptr, self.indices, self.data, self.ring, dslot)
        self.step_i += 1
        self.t_ms += self.dt
        return self.spk[:k]

    def run(self, duration_ms: float):
        """Run and return spike counts per neuron."""
        counts = np.zeros(self.n, np.int32)
        for _ in range(int(round(duration_ms / self.dt))):
            s = self.step()
            counts[s] += 1
        return counts
