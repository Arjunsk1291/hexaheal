"""Audited tables/figures exclusively from complete, fresh simulation raw results."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from release_run import CASES, CONTROLLERS, load_rows
from neurowalker.hh_eval import case_name

def audit(rows, controllers=CONTROLLERS, seeds=range(10)):
    expected = {(c,k,s) for c in controllers for k in CASES for s in seeds}
    actual = {(r['controller'],r['case'],r['seed']) for r in rows}
    if len(rows) != len(actual): raise ValueError('Duplicate run keys')
    if actual != expected: raise ValueError(f'Incomplete/extra data: missing {len(expected-actual)}, extra {len(actual-expected)}')
    for r in rows:
        if r['recovered'] != (not r['fell'] and r['v_last8'] >= 0.125):
            raise ValueError('Recovery label conflicts with metric')
        for k in ('t_end','v_last8','distance','wall_runtime_s'):
            if not np.isfinite(r[k]): raise ValueError(f'Non-finite {k}')
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('release/validation'));a=p.parse_args()
    path=a.output; rows=load_rows(path/'runs.jsonl');audit(rows)
    fieldnames=sorted(set().union(*(r.keys() for r in rows)))
    with (path/'runs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fieldnames);w.writeheader();w.writerows(rows)
    data={(r['controller'],r['case'],r['seed']):r for r in rows}
    rec={c:np.array([[data[c,k,s]['recovered'] for s in range(10)] for k in CASES]) for c in CONTROLLERS}
    upright={c:np.array([[not data[c,k,s]['fell'] for s in range(10)] for k in CASES]) for c in CONTROLLERS}
    def n(m): return int((m.sum(1)>=7).sum())
    idx=np.random.default_rng(0).integers(0,10,(10000,10))
    def boot(x,y):
        ds=np.array([n(rec[x][:,i])-n(rec[y][:,i]) for i in idx])
        return {'difference_cases':n(rec[x])-n(rec[y]),'ci95_cases':np.percentile(ds,[2.5,97.5]).tolist(),
                'method':'paired seed-cluster percentile bootstrap, 10000 draws, RNG seed 0'}
    summary={'status':'MEASURED','simulation_only':True,'runs':len(rows),'by_controller':{},
             'tierB_minus_tripod':boot('tierB','tripod'),'warm_minus_tierB':boot('warm_start','tierB')}
    for c in CONTROLLERS:
        rr=[r for r in rows if r['controller']==c]
        summary['by_controller'][c]={'recovered_cases':n(rec[c]),'upright_cases':n(upright[c]),
          'recovered_runs':int(rec[c].sum()),'upright_not_recovered_runs':int((upright[c]&~rec[c]).sum()),
          'runtime_s':sum(r['wall_runtime_s'] for r in rr),'per_case_recovered':{k:int(rec[c][i].sum()) for i,k in enumerate(CASES)}}
    b=summary['warm_minus_tierB'];summary['warm_rule_passed']=bool(b['difference_cases']>=2 and n(rec['warm_start'])>=8 and b['ci95_cases'][0]>0)
    (path/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,ax=plt.subplots(figsize=(12,4.5))
    im=ax.imshow(np.array([rec[c].sum(1) for c in CONTROLLERS]),vmin=0,vmax=10,cmap='viridis',aspect='auto')
    ax.set_xticks(range(21),[case_name(c) for c in CASES],rotation=55,ha='right')
    ax.set_yticks(range(7),CONTROLLERS);ax.set_title('MuJoCo simulation: walking recovery across all 21 cases')
    for i,c in enumerate(CONTROLLERS):
        for j in range(21):ax.text(j,i,str(int(rec[c][j].sum())),ha='center',va='center',color='white' if rec[c][j].sum()<6 else 'black',fontsize=8)
    fig.colorbar(im,ax=ax,label='Recovered seeds / 10')
    fig.text(.01,.015,'Recovered = no fall and >=0.125 m/s over last 8 s. Oracle: faults at t=0, 15 s, NOT a matched online controller.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(path/'recovery_matrix.png',dpi=160);fig.savefig(path/'recovery_matrix.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.8));x=np.arange(7)
    ax.bar(x-.18,[n(rec[c]) for c in CONTROLLERS],width=.36,label='walking recovery',color='#147d92')
    ax.bar(x+.18,[n(upright[c]) for c in CONTROLLERS],width=.36,label='upright only',color='#b7c5cf')
    ax.set_xticks(x,CONTROLLERS,rotation=25,ha='right');ax.set_ylim(0,21);ax.set_ylabel('Cases / 21 (>=7 of 10 seeds)');ax.legend()
    ax.set_title('Simulation results: success and failure use the same rule')
    fig.text(.02,.01,'Warm-start rule passed: '+str(summary['warm_rule_passed'])+'. Oracle has different fault/episode conditions.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1));fig.savefig(path/'baseline_comparison.png',dpi=160);plt.close(fig)
    lines=['# Fresh validation release','', 'Simulation only. All rows below are MEASURED from the attached raw files.','',
           '| Controller | Recovered /21 | Upright /21 |','|---|---:|---:|']
    for c,d in summary['by_controller'].items():lines.append(f"| {c} | {d['recovered_cases']} | {d['upright_cases']} |")
    lines+=['',f"Warm-start pre-registered rule passed: {summary['warm_rule_passed']}",
            '','The oracle has different initial-fault timing and episode length; it is contextual, not a matched baseline.',
            'PPO and historical latency counts are not part of this fresh release: their full reproduction remains UNVERIFIED.']
    (path/'REPORT.md').write_text('\n'.join(lines)+'\n')
    files=sorted(p for p in path.iterdir() if p.is_file() and p.name!='SHA256SUMS')
    (path/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
