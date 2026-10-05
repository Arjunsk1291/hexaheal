import pytest

from neurowalker.env import HexapodEnv
from neurowalker.faults import Fault
from neurowalker.healing import HealingController
from neurowalker.tripod import TripodController


def run(fault, t_end=12.0):
    e = HexapodEnv("flat", max_time=t_end, faults=[fault] if fault else [], rand=0.05)
    e.reset(seed=1)
    c = HealingController(TripodController())
    c.reset()
    while True:
        _, _, te, tr, _ = e.step(c.act(e))
        if te or tr:
            return e, c


def test_no_fault_no_alarm():
    e, c = run(None, 8.0)
    assert c.state == "NORMAL" and c.t_detect is None and c.log == []


@pytest.mark.parametrize("kind,kw", [("disable_leg", {"leg": 2}), ("lock_joint", {"leg": 4, "joint": 0}),
                                      ("sensor_dropout", {"leg": 3})])
def test_diagnoses_fault_type_and_leg(kind, kw):
    e, c = run(Fault(kind, 4.0, **kw))
    assert c.diag is not None
    assert c.diag["kind"] == kind and c.diag["leg"] == kw["leg"]
    states = [d["to"] for d in c.log]
    assert states[:3] == ["FAULT_SUSPECTED", "DIAGNOSE", "ADAPT"]
    assert all("t" in d and "evidence" in d and "action" in d for d in c.log)
    assert c.t_detect >= 4.0
