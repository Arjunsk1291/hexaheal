"""Release integrity checks plus an actual simulation smoke run."""
import sys

import pytest

sys.path.insert(0,'scripts')
from release_report import audit
from release_run import CASES, controller, experiment

from neurowalker.hh_eval import run_episode


def test_seed_split_and_model_are_frozen():
    e=experiment()
    assert not set(e['eval_seeds']) & set(e['tuning_seeds'])
    assert len(e['cases'])==21 and len(e['mjcf_sha256'])==64
    assert e['model']['dt']==0.005 and e['simulation_only']

def test_audit_rejects_missing_data():
    with pytest.raises(ValueError,match='Incomplete'):audit([])

def test_audit_rejects_duplicates():
    r={'controller':'tripod','case':CASES[0],'seed':0}
    with pytest.raises(ValueError,match='Duplicate'):audit([r,r])

def test_leave_one_case_out_also_excludes_mirror():
    c=controller('warm_start','dl_1_5')
    assert c.exclude=={(1,5),(2,4)}

def test_release_baseline_simulation_repeats_exactly():
    a=run_episode(controller('tripod','dl_1'),'dl_1',0)
    b=run_episode(controller('tripod','dl_1'),'dl_1',0)
    assert a==b
