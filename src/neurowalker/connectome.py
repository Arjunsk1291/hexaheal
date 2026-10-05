"""Focused connectome subgraph extraction (FlyWire v783 via the Shiu et al. 2024 tables)."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import scipy.sparse as sp

RAW = "data/raw"
OUT = "data/processed"


def load_full(raw=RAW):
    comp = pd.read_csv(f"{raw}/Completeness_783.csv", index_col=0)
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(f"{raw}/Connectivity_783.parquet")
    pres, posts, ws = [], [], []
    for b in pf.iter_batches(batch_size=1_000_000, columns=["Presynaptic_Index", "Postsynaptic_Index", "Excitatory x Connectivity"]):
        pres.append(b.column(0).to_numpy().astype(np.int32))
        posts.append(b.column(1).to_numpy().astype(np.int32))
        ws.append(b.column(2).to_numpy().astype(np.float32))
    n = len(comp)
    pre, post, w = np.concatenate(pres), np.concatenate(posts), np.concatenate(ws)
    del pres, posts, ws
    A = sp.csr_matrix((w, (post, pre)), shape=(n, n))  # row = post, col = pre (signed synapse counts)
    ann = pd.read_csv(f"{raw}/Supplemental_file1_neuron_annotations.tsv", sep="\t",
                      usecols=["root_id", "super_class", "cell_class", "cell_type", "side", "top_nt"])
    ann = ann.drop_duplicates("root_id").set_index("root_id").reindex(comp.index)
    return comp, A, ann


def diffuse(M, seed, hops=3, decay=0.5):
    """Weighted reach of `seed` through M for `hops` steps (M[post,pre] column-normalized)."""
    x = seed.astype(np.float32)
    tot = np.zeros_like(x)
    for k in range(hops):
        x = M @ x
        m = x.max()
        if m > 0:
            x = x / m
        tot += (decay ** k) * x
    return tot


def extract(n_target=10000, raw=RAW, out=OUT, seed_cls=("mechanosensory", "gustatory")):
    comp, A, ann = load_full(raw)
    N = A.shape[0]
    sc = ann["super_class"].fillna("").to_numpy()
    cc = ann["cell_class"].fillna("").to_numpy()
    sensory = np.where((sc == "sensory") & np.isin(cc, seed_cls))[0]
    desc = np.where(sc == "descending")[0]
    motor = np.where(sc == "motor")[0]
    pool_mask = np.isin(sc, ["central", "sensory", "descending", "motor"]) & ~np.isin(cc, ["visual", "olfactory", "optic_lobes"])
    must = np.union1d(np.union1d(sensory, desc), motor)
    Aabs = abs(A).astype(np.float32)
    inw = np.asarray(Aabs.sum(axis=1)).ravel()
    Mf = sp.diags(1.0 / np.maximum(inw, 1)) @ Aabs  # post-normalized: fraction of input from each pre
    outw = np.asarray(Aabs.sum(axis=0)).ravel()
    Mb = (Aabs @ sp.diags(1.0 / np.maximum(outw, 1))).T.tocsr()  # reverse flow
    s0 = np.zeros(N, np.float32); s0[sensory] = 1
    d0 = np.zeros(N, np.float32); d0[desc] = 1
    fwd = diffuse(Mf.tocsr(), s0)  # reached from sensory
    bwd = diffuse(Mb, d0)  # reaches descending
    score = np.sqrt(fwd * bwd)
    score[~pool_mask] = -1
    score[must] = np.inf
    keep = np.argsort(-score)[:n_target]
    keep = np.sort(keep)
    sub = A[keep][:, keep].tocsr()
    os.makedirs(out, exist_ok=True)
    sp.save_npz(f"{out}/subgraph_weights.npz", sub)
    meta = pd.DataFrame({"flywire_id": comp.index.to_numpy()[keep], "super_class": sc[keep], "cell_class": cc[keep],
                         "cell_type": ann["cell_type"].fillna("").to_numpy()[keep], "side": ann["side"].fillna("").to_numpy()[keep]})
    meta.to_parquet(f"{out}/subgraph_meta.parquet")
    info = {"n_neurons": int(len(keep)), "n_synapse_pairs": int(sub.nnz), "n_sensory_seeds": int(len(sensory)),
            "n_descending": int(len(desc)), "n_motor": int(len(motor)),
            "descending_kept": int((meta.super_class == "descending").sum()),
            "source": "FlyWire v783 (CC BY-NC 4.0) via Shiu et al. 2024 repo tables",
            "selection": "all mechanosensory+gustatory sensory neurons, all descending and motor neurons, remaining slots filled "
                         "by sqrt(forward reach from sensory * backward reach to descending) over 3 hops, excluding visual/olfactory/optic."}
    json.dump(info, open(f"{out}/subgraph_info.json", "w"), indent=2)
    return info


if __name__ == "__main__":
    print(extract())
