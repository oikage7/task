from __future__ import annotations
from src_solution.abu.tcb.safety import enforce_depth_cap, enforce_rpm_cap, should_emergency_stop
from src_solution.abu.tcb.event_log import default_log, EventLevel

def validate_and_enforce_safety(
    current_depth: float,
    target_depth: float,
    rpm: float,
    max_rpm_cap: float,
    risk: str,
    vibration_score: float
) -> str:
    if not enforce_depth_cap(current_depth, target_depth + 1e-6):
        default_log.record(EventLevel.WARNING, "mission_stopped_depth_cap")
        return "stopped_depth"

    if not enforce_rpm_cap(rpm, max_rpm_cap):
        default_log.record(EventLevel.ERROR, "mission_stopped_rpm_cap")
        return "stopped_rpm"

    if should_emergency_stop(risk, vibration_score):
        default_log.record(EventLevel.CRITICAL, "emergency_stop_triggered")
        return "emergency"

    if current_depth >= target_depth:
        default_log.record(EventLevel.INFO, "mission_completed_target_depth")
        return "completed"

    return "running"