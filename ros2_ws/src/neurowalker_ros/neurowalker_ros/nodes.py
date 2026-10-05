"""ROS 2 nodes. UNVERIFIED: written against rclpy's documented API but never executed in the build environment.

Topics (50 Hz lockstep): sim_node publishes /joint_states, /imu, /contacts, /body_vel and then applies the next /joint_commands.
brain_node (connectome-inspired) publishes /brain_cmd = [speed_gain, turn, stance_adj, freq_scale]; gait_node (tripod CPG) subscribes
to it and publishes /joint_commands; health_monitor_node publishes /health; decision_node publishes /decision (JSON string)
and /gait_params; metrics_logger writes CSV.
"""
from __future__ import annotations

import json

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Float32MultiArray, String

from neurowalker.env import HexapodEnv
from neurowalker.hexapod import JOINT_NAMES, LEG_NAMES
from neurowalker.tripod import TripodController

DT = 0.02
NAMES = [f"{leg}_{j}" for leg in LEG_NAMES for j in JOINT_NAMES]


class StateProxy:
    """Duck-types the parts of HexapodEnv that controllers read, from ROS messages."""

    def __init__(self, env_template: HexapodEnv):
        self.q_nom, self.dt, self.target_speed = env_template.q_nom, DT, env_template.target_speed
        self.scale, self.q_lo, self.q_hi = env_template.scale, env_template.q_lo, env_template.q_hi
        self.t, self.rpy, self.v = 0.0, (0.0, 0.0, 0.0), np.zeros(3)
        self.last_sensed_q = env_template.q_nom.copy()

    def euler(self): return self.rpy
    def body_vel(self): return self.v
    def q_to_action(self, q): return np.clip((np.asarray(q) - self.q_nom) / self.scale, -1, 1)
    def action_to_q(self, a): return np.clip(self.q_nom + np.asarray(a) * self.scale, self.q_lo, self.q_hi)


class SimNode(Node):
    def __init__(self):
        super().__init__("sim_node")
        self.declare_parameter("terrain", "flat"); self.declare_parameter("seed", 0); self.declare_parameter("max_time", 10.0)
        self.env = HexapodEnv(self.get_parameter("terrain").value, max_time=self.get_parameter("max_time").value, rand=0.1,
                              seed=self.get_parameter("seed").value, target_speed=0.25)
        self.env.reset(seed=self.get_parameter("seed").value)
        self.pj = self.create_publisher(JointState, "/joint_states", 10)
        self.pi = self.create_publisher(Imu, "/imu", 10)
        self.pc = self.create_publisher(Float32MultiArray, "/contacts", 10)
        self.pv = self.create_publisher(Float32MultiArray, "/body_vel", 10)
        self.cmd = np.zeros(18)
        self.create_subscription(Float32MultiArray, "/joint_commands", self._on_cmd, 10)
        self.create_timer(DT, self.tick)

    def _on_cmd(self, m): self.cmd = np.array(m.data, dtype=float)

    def tick(self):
        e = self.env
        e.step(self.cmd)
        now = self.get_clock().now().to_msg()
        js = JointState(); js.header.stamp = now; js.name = NAMES
        js.position = [float(x) for x in e.last_sensed_q]; js.velocity = [float(x) for x in e.qd]
        self.pj.publish(js)
        im = Imu(); im.header.stamp = now
        w, x, y, z = e.data.qpos[3:7]
        im.orientation.w, im.orientation.x, im.orientation.y, im.orientation.z = float(w), float(x), float(y), float(z)
        self.pi.publish(im)
        self.pc.publish(Float32MultiArray(data=[float(c) for c in e.last_contacts]))
        self.pv.publish(Float32MultiArray(data=[float(e.t)] + [float(v) for v in e.body_vel()] + [float(e.data.qpos[0])]))


class _ProxyNode(Node):
    """Base for nodes that need a state proxy updated from topics."""

    def __init__(self, name):
        super().__init__(name)
        self.proxy = StateProxy(HexapodEnv("flat"))
        self.create_subscription(JointState, "/joint_states", self._js, 10)
        self.create_subscription(Imu, "/imu", self._imu, 10)
        self.create_subscription(Float32MultiArray, "/body_vel", self._bv, 10)

    def _js(self, m): self.proxy.last_sensed_q = np.array(m.position)
    def _imu(self, m):
        w, x, y, z = m.orientation.w, m.orientation.x, m.orientation.y, m.orientation.z
        roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)); pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
        yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)); self.proxy.rpy = (roll, pitch, yaw)
    def _bv(self, m): self.proxy.t = m.data[0]; self.proxy.v = np.array(m.data[1:4])


class BrainNode(_ProxyNode):
    def __init__(self):
        super().__init__("brain_node")
        from neurowalker.brain import BrainController
        self.brain = BrainController(); self.brain.reset()
        self.pub = self.create_publisher(Float32MultiArray, "/brain_cmd", 10)
        self.create_timer(DT, self.tick)

    def tick(self):
        # BrainController.act also returns a CPG action; here only the high-level commands are published (gait_node owns the CPG).
        self.brain.act(self.proxy)
        c = self.brain.last_cmd; g = self.brain.g
        self.pub.publish(Float32MultiArray(data=[float(np.clip(1 + g["speed"] * c["speed"], 0.5, 1.5)), float(np.clip(g["turn"] * c["turn"], -0.6, 0.6)),
                                                 float(np.clip(g["stance"] * c["pitch"], -0.2, 0.2)), float(np.clip(1 + g["speed_freq"] * c["speed"], 0.6, 1.4))]))


class GaitNode(_ProxyNode):
    def __init__(self):
        super().__init__("gait_node")
        self.cpg = TripodController(); self.cmd = [1.0, 0.0, 0.0, 1.0]
        self.create_subscription(Float32MultiArray, "/brain_cmd", lambda m: setattr(self, "cmd", list(m.data)), 10)
        self.create_subscription(String, "/gait_params", self._params, 10)
        self.pub = self.create_publisher(Float32MultiArray, "/joint_commands", 10)
        self.create_timer(DT, self.tick)

    def _params(self, m):
        p = json.loads(m.data); self.cpg.p.freq, self.cpg.p.stride, self.cpg.p.lift = p["freq"], p["stride"], p["lift"]

    def tick(self):
        a = self.cpg.act(self.proxy, speed_gain=self.cmd[0], turn=self.cmd[1], stance_adj=self.cmd[2], freq_scale=self.cmd[3])
        self.last = a
        self.pub.publish(Float32MultiArray(data=[float(x) for x in a]))


class HealthMonitorNode(_ProxyNode):
    def __init__(self):
        super().__init__("health_monitor_node")
        from neurowalker.healing import HealthMonitor
        self.mon = HealthMonitor(); self.cmd = np.zeros(18)
        self.create_subscription(Float32MultiArray, "/joint_commands", lambda m: setattr(self, "cmd", np.array(m.data)), 10)
        self.pub = self.create_publisher(String, "/health", 10)
        self.create_timer(DT, self.tick)

    def tick(self):
        self.mon.update(self.proxy.t, self.proxy.action_to_q(self.cmd), self.proxy.last_sensed_q, *self.proxy.rpy[:2])
        if self.mon.ready():
            sus, f = self.mon.suspect()
            self.pub.publish(String(data=json.dumps({"t": self.proxy.t, "suspect": sus, "diagnosis": self.mon.diagnose(f) if sus else None}, default=float)))


class DecisionNode(Node):
    def __init__(self):
        super().__init__("decision_node")
        self.create_subscription(String, "/health", self._h, 10)
        self.pub = self.create_publisher(String, "/decision", 10)
        self.n = 0

    def _h(self, m):
        h = json.loads(m.data)
        self.n = self.n + 1 if h["suspect"] else 0
        if self.n == 8:
            self.pub.publish(String(data=json.dumps({"t": h["t"], "state": "FAULT_SUSPECTED", "evidence": h["diagnosis"]})))


class MetricsLogger(Node):
    def __init__(self):
        super().__init__("metrics_logger")
        self.f = open("ros_metrics.csv", "w"); self.f.write("t,x,vx\n")
        self.create_subscription(Float32MultiArray, "/body_vel", self._b, 10)

    def _b(self, m): self.f.write(f"{m.data[0]},{m.data[4]},{m.data[1]}\n")


def _main(cls):
    rclpy.init(); n = cls(); rclpy.spin(n); rclpy.shutdown()


def sim_node_main(): _main(SimNode)
def brain_node_main(): _main(BrainNode)
def gait_node_main(): _main(GaitNode)
def health_monitor_node_main(): _main(HealthMonitorNode)
def decision_node_main(): _main(DecisionNode)
def metrics_logger_main(): _main(MetricsLogger)
