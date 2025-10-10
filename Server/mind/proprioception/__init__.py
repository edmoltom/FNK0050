"""Lumo's proprioception subsystem.

This package houses components that maintain an internal model of the
robot's body state, bridging raw sensor data from :mod:`core.sensing`
with higher-level cognitive reasoning in :mod:`mind.context` and
behavior planners.
"""

__all__ = ["body_model", "sensor_bus"]

