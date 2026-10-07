"""Report-metric checks without hiding complete-run or negative-result errors."""
import sys

sys.path.insert(0,'scripts')
import pytest
from release_report import audit
from release_run import CASES


def rows():
    return [dict(controller='tripod',case=c,seed=0,recovered=False,fell=True,
                 v_last8=0.,t_end=8.,distance=1.,wall_runtime_s=.1) for c in CASES]

def test_audit_accepts_complete_negative_cases():
    assert audit(rows(),controllers=['tripod'],seeds=[0])

def test_recovery_never_counts_fall_even_with_high_speed():
    a=rows();a[0].update(recovered=True,v_last8=.2)
    with pytest.raises(ValueError,match='Recovery label'):audit(a,controllers=['tripod'],seeds=[0])

def test_bad_numeric_is_rejected():
    a=rows();a[0]['distance']=float('nan')
    with pytest.raises(ValueError,match='Non-finite'):audit(a,controllers=['tripod'],seeds=[0])

def test_wrong_seed_or_extra_case_is_rejected():
    a=rows();a[0]['seed']=100
    with pytest.raises(ValueError,match='Incomplete/extra'):audit(a,controllers=['tripod'],seeds=[0])
