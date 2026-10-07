"""Compare fresh episodes to surviving historical records; ignore machine runtime."""
import json
from pathlib import Path
from release_run import load_rows

HISTORICAL = {'tripod':'results/v3/hh3_final_tripod_0-9.jsonl',
 'tierB':'results/v4/hh4_final_v2B_0-9.jsonl',
 'warm_start':'results/v4/hh4_final_v2Bplus_0-9.jsonl',
 'oracle':'results/v3/hh3_oracle_0-9.jsonl'}

def compare(output=Path('release/validation')):
    fresh=load_rows(output/'runs.jsonl'); result={}
    for c,f in HISTORICAL.items():
        old={(r['case'],r['seed']):r for r in [json.loads(x) for x in Path(f).read_text().splitlines()]}
        rows=[r for r in fresh if r['controller']==c]; bad=[]
        for r in rows:
            h=old[r['case'],r['seed']]
            keys=[k for k in h if k in r and k not in ('controller','wall_runtime_s')]
            mismatch=[k for k in keys if r[k]!=h[k]]
            if mismatch:bad.append({'case':r['case'],'seed':r['seed'],'fields':mismatch})
        result[c]={'compared_runs':len(rows),'historical_runs':len(old),'all_shared_fields_exact':(not bad) if rows else None,'mismatches':bad}
    (output/'historical_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':print(json.dumps(compare(),indent=2))
