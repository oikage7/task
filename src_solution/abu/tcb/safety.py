from __future__ import annotations

def enforce_depth_cap(depth_m: float, max_depth_m: float) -> bool:
    return depth_m <= max_depth_m

def enforce_rpm_cap(rpm: float, max_rpm: float) -> bool:
    return rpm <= max_rpm

def should_emergency_stop(
    risk: str,
    vibration_score: float,
    vib_threshold: float = 0.9,
) -> bool:
    if risk == "high":
        return True
    if vibration_score >= vib_threshold:
        return True
    return False