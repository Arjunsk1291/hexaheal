import numpy as np
import pytest

from neurowalker.env import TERRAINS, HexapodEnv
from neurowalker.faults import Fault
from neurowalker.hexapod import generate_mjcf


def test_mjcf_has_18_dof_and_sensors():
    import mujoco
    m = mujoco.MjModel.from_xml_string(generate_mjcf())
    assert m.nu == 18
    assert m.nq == 7 + 18
    for n in ["imu_gyro", "imu_acc", "R1_contact", "L3_tibia_enc"]:
        m.sensor(n)


@pytest.mark.parametrize("terrain", list(TERRAINS))
def test_stands_on_every_terrain(terrain):
    e = HexapodEnv(terrain)
    e.reset(seed=0)
    for _ in range(100):
        _, _, term, _, _ = e.step(np.zeros(18))
    assert not term


def test_obs_shape_and_gym_api():
    e = HexapodEnv()
    o, _ = e.reset(seed=1)
    assert o.shape == e.observation_space.shape
    o, r, te, tr, info = e.step(e.action_space.sample())
    assert np.isfinite(r)


def test_fault_disable_leg_removes_torque():
    e = HexapodEnv(faults=[Fault("disable_leg", 0.2, leg=2)])
    e.reset(seed=0)
    for _ in range(30):
        e.step(np.zeros(18))
    assert [f.kind for f in e.active_faults] == ["disable_leg"]
    assert np.all(e.model.actuator_gainprm[6:9, 0] == 0)
    assert np.all(e.model.actuator_gainprm[0:6, 0] > 0)


def test_lock_joint_and_reduce_torque_and_dropout():
    e = HexapodEnv(faults=[Fault("lock_joint", 0.0, leg=0, joint=1), Fault("reduce_torque", 0.0, leg=1, severity=0.3),
                           Fault("sensor_dropout", 0.0, leg=3)])
    e.reset(seed=0)
    for _ in range(5):
        e.step(np.ones(18) * 0.5)
    assert 1 in e.locked
    assert e.model.actuator_forcerange[3, 1] == pytest.approx(0.3 * 2.5)
    assert 3 in e.sensor_dropout_legs


def test_reset_restores_faults():
    e = HexapodEnv(faults=[Fault("disable_leg", 0.0, leg=0)])
    e.reset(seed=0); e.step(np.zeros(18))
    e.fault_list = []
    e.reset(seed=0)
    assert np.all(e.model.actuator_gainprm[0:3, 0] > 0)


def test_push_perturbation_moves_body():
    e = HexapodEnv(pushes=[(0.1, 0.0, 30.0, 0.1)])
    e.reset(seed=0)
    for _ in range(25):
        e.step(np.zeros(18))
    assert abs(e.data.qpos[1]) > 1e-3
