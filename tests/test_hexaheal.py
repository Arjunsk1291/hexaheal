"""HexaHeal v3 tests: determinism, no state leaks across episodes, no wall-clock dependence in v2/eval, and the 'recovered' definition."""
import pathlib
import sys

sys.path.insert(0, "scripts")
from hh_common import make  # noqa: E402

from neurowalker.hh_eval import LAST_S, REC_FRAC, run_episode  # noqa: E402
from neurowalker.tripod import TripodController  # noqa: E402

KW = dict(confirm_s=0.3, n_joints=1, thr=0.3, suspect_n=8, min_confirm_s=0.0, interim="stand", max_trials=6)


def test_recovered_definition_is_the_preregistered_one():
    assert LAST_S == 8.0 and REC_FRAC == 0.5  # no fall AND >= 50% of 0.25 m/s over the last 8 s (docs/PREREGISTRATION_V3.md)
    r = run_episode(TripodController(), "healthy", 0)
    assert not r["fell"] and r["recovered"] and r["v_last8"] >= 0.125


def test_episode_is_deterministic():
    a, b = run_episode(TripodController(), "dl_1", 3), run_episode(TripodController(), "dl_1", 3)
    assert a == b


def test_healing_v2_no_state_leak_between_episodes():
    c = make("B", **KW)
    first = run_episode(c, "dl_2", 1)
    run_episode(c, "dl_0_4", 2)  # a different case and seed on the same controller object
    again = run_episode(c, "dl_2", 1)
    assert first == again
    assert first == run_episode(make("B", **KW), "dl_2", 1)


def test_fall_is_never_recovered():
    r = run_episode(TripodController(), "dl_3", 0)  # L1 lost: the plain tripod falls
    assert r["fell"] and not r["recovered"]


def test_v2_and_eval_do_not_use_wall_clock():
    for f in ("src/neurowalker/healing2.py", "src/neurowalker/hh_eval.py"):
        src = pathlib.Path(f).read_text()
        assert "time.time" not in src and "perf_counter" not in src and "import time" not in src
