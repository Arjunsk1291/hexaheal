"""Validation: reproduce a published qualitative circuit result (Shiu et al. 2024): activating sugar-sensing
gustatory neurons drives feeding-related (proboscis/ingestion) motor neurons. Runs on the full 138,639-neuron
v783 network (engine check) and on the 10k-neuron subgraph used for control."""
import json, time, sys
import numpy as np, pandas as pd, scipy.sparse as sp
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from neurowalker.connectome import load_full
from neurowalker.snn import SpikingNet

N_TRIALS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
comp, A, ann = load_full()
sub = ann["cell_sub_class"] if "cell_sub_class" in ann else None
full_ann = pd.read_csv("data/raw/Supplemental_file1_neuron_annotations.tsv", sep="\t", usecols=["root_id", "cell_sub_class", "side"], low_memory=False)
full_ann = full_ann.drop_duplicates("root_id").set_index("root_id").reindex(comp.index)
subc = full_ann["cell_sub_class"].fillna("").to_numpy()
side = full_ann["side"].fillna("").to_numpy()

def groups(sc):
    return {"proboscis_motor": np.where(sc == "proboscis_motor_neuron")[0],
            "ingestion_motor": np.where(sc == "ingestion_motor_neuron")[0],
            "antennal_motor": np.where(sc == "antennal_motor_neuron")[0],
            "neck_motor": np.where(sc == "neck_motor_neuron")[0],
            "eye_motor": np.where(sc == "eye_motor_neuron")[0]}

def experiment(net, sc, label):
    G = groups(sc)
    conds = {"none": np.array([], int), "sugar_GRN": np.where((sc == "sugar") & (side == "right"))[0] if False else np.where(sc == "sugar")[0],
             "bitter_GRN": np.where(sc == "bitter")[0]}
    out, t_total, sim_total = {}, 0, 0
    for cname, idx in conds.items():
        rates = {g: [] for g in G}
        for trial in range(N_TRIALS):
            net.reset(); net.rng = np.random.default_rng(100 + trial)
            if len(idx):
                net.set_rates(idx, 100.0)
            t0 = time.time(); c = net.run(1000.0); t_total += time.time() - t0; sim_total += 1.0
            for g, ids in G.items():
                rates[g].append(float(c[ids].mean()) if len(ids) else float("nan"))
        out[cname] = {g: {"mean_hz": float(np.mean(v)), "sd_hz": float(np.std(v)), "n_neurons": int(len(G[g]))} for g, v in rates.items()}
        out[cname]["n_stimulated"] = int(len(idx))
    return out, t_total / sim_total

res = {"n_trials": N_TRIALS, "stim_rate_hz": 100.0}
t0 = time.time(); net = SpikingNet(A); res["full_build_s"] = time.time() - t0
res["full_network"] = {"neurons": int(net.n), "synapse_pairs": int(net.nnz)}
res["full"], res["full_wall_s_per_sim_s"] = experiment(net, subc, "full")
del net
meta = pd.read_parquet("data/processed/subgraph_meta.parquet")
Wsub = sp.load_npz("data/processed/subgraph_weights.npz")
idmap = pd.read_csv("data/raw/Supplemental_file1_neuron_annotations.tsv", sep="\t", usecols=["root_id", "cell_sub_class"], low_memory=False).drop_duplicates("root_id").set_index("root_id").reindex(meta.flywire_id)
sc_sub = idmap["cell_sub_class"].fillna("").to_numpy()
side = meta["side"].to_numpy()
net = SpikingNet(Wsub)
res["subgraph_network"] = {"neurons": int(net.n), "synapse_pairs": int(net.nnz)}
res["subgraph"], res["subgraph_wall_s_per_sim_s"] = experiment(net, sc_sub, "sub")
json.dump(res, open("results/validation/shiu_sugar_validation.json", "w"), indent=2)

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
cols = {"none": "#6b7280", "sugar_GRN": "#2dd4bf", "bitter_GRN": "#f59e0b"}
for ax, key, title in [(axes[0], "full", f"Full network ({res['full_network']['neurons']:,} neurons)"),
                       (axes[1], "subgraph", f"10k-neuron control subgraph")]:
    gs = ["proboscis_motor", "ingestion_motor", "antennal_motor", "neck_motor", "eye_motor"]
    x = np.arange(len(gs)); w = 0.27
    for k, (cn, col) in enumerate(cols.items()):
        m = [res[key][cn][g]["mean_hz"] for g in gs]; s = [res[key][cn][g]["sd_hz"] for g in gs]
        ax.bar(x + (k - 1) * w, m, w, yerr=s, color=col, label={"none": "no stimulus", "sugar_GRN": "sugar GRNs @100 Hz", "bitter_GRN": "bitter GRNs @100 Hz"}[cn], capsize=2)
    ax.set_xticks(x); ax.set_xticklabels([g.replace("_", "\n") for g in gs]); ax.set_ylabel("mean spike rate (Hz)"); ax.set_title(title)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(frameon=False, fontsize=8)
fig.suptitle(f"Dynamics check: sugar-sensing GRN drive propagates to feeding motor neurons (mean +- SD, {N_TRIALS} trials x 1 s)", fontsize=10)
fig.tight_layout(); fig.savefig("docs/figures/validation_shiu_sugar.png", dpi=160)
print(json.dumps(res, indent=1)[:2500])
