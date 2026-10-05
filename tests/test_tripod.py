from neurowalker.env import HexapodEnv
from neurowalker.tripod import TripodController, run_episode


def test_tripod_walks_flat_without_falling():
    e = HexapodEnv("flat", max_time=8.0, rand=0.1)
    info = run_episode(TripodController(), e, seed=0)
    assert not info["fell"]
    assert e.distance() >= 1.5


def test_tripod_walks_on_rough_level3():
    e = HexapodEnv("rough3", max_time=8.0, rand=0.1)
    info = run_episode(TripodController(), e, seed=1)
    assert not info["fell"] and e.distance() >= 1.0
