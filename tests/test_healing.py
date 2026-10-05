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


def test_no_false_positive_healthy_14s_all_seeds():
    for seed in (100, 101, 102):  # tuning seeds only
        e = HexapodEnv("flat", max_time=14.0, rand=0.1, seed=seed)
        e.reset(seed=seed)
        c = HealingController(TripodController(), seed=seed); c.reset()
        while True:
            _, _, te, tr, _ = e.step(c.act(e))
            if te or tr:
                break
        assert c.log == [] and not e.fell


def test_sequential_faults_second_is_detected():
    seed = 101
    e = HexapodEnv("flat", max_time=16.0, faults=[Fault("disable_leg", 4.0, leg=2), Fault("disable_leg", 9.0, leg=5)], rand=0.1, seed=seed)
    e.reset(seed=seed)
    c = HealingController(TripodController(), seed=seed); c.reset()
    while True:
        _, _, te, tr, _ = e.step(c.act(e))
        if te or tr:
            break
    sus = [d["t"] for d in c.log if d["to"] == "FAULT_SUSPECTED"]
    assert sus and sus[0] >= 4.0
    assert any(t >= 9.0 for t in sus), c.log  # the old -1e6 latch made this impossible


def test_healing_does_not_leak_into_shared_controller():
    ctrl = TripodController(); f0, s0 = ctrl.p.freq, ctrl.leg_stride_scale.copy()
    e = HexapodEnv("flat", max_time=10.0, faults=[Fault("disable_leg", 4.0, leg=2)], rand=0.1, seed=101)
    e.reset(seed=101)
    c = HealingController(ctrl, seed=101); c.reset()
    while True:
        _, _, te, tr, _ = e.step(c.act(e))
        if te or tr:
            break
    assert ctrl.p.freq == f0 and (ctrl.leg_stride_scale == s0).all()
