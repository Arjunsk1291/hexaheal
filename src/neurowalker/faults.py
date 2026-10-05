"""Fault injection specification."""
from __future__ import annotations

from dataclasses import dataclass

FAULT_TYPES = ("disable_leg", "lock_joint", "reduce_torque", "sensor_dropout")


@dataclass
class Fault:
    kind: str  # one of FAULT_TYPES
    time: float  # seconds into the episode at which it triggers
    leg: int = 1  # 0..5
    joint: int = 1  # 0 coxa, 1 femur, 2 tibia (lock_joint only)
    severity: float = 0.3  # reduce_torque: remaining torque fraction

    def __post_init__(self):
        if self.kind not in FAULT_TYPES:
            raise ValueError(f"unknown fault {self.kind}")

    def describe(self) -> str:
        return f"{self.kind}(leg={self.leg},joint={self.joint},sev={self.severity})"
