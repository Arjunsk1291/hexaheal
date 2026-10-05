import json
import os

import numpy as np

from neurowalker.benchmark import FAULTS, SCENARIOS, _speed, scenario_spec


def test_scenario_list_complete():
    assert len(SCENARIOS) == 16
    assert all(f"{k}+healing" in SCENARIOS for k in FAULTS)


def test_scenario_spec_known_names():
    for s in SCENARIOS:
        assert scenario_spec(s) is not None


def test_speed_linear_motion():
    ts = np.linspace(0, 10, 101)
    xs = 0.25 * ts
    assert abs(_speed(xs, ts, 2.0, 6.0) - 0.25) < 1e-6


def test_summary_consistent_with_benchmark_file():
    if not os.path.exists("results/summary.json"):
        return
    S = json.load(open("results/summary.json"))
    for c in S.values():
        for cell in c.values():
            fr = cell["fall_rate"]
            assert 0 <= fr["falls"] <= fr["n"]
