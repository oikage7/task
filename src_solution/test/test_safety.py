import os
import pytest

from abu.tcb.safety import enforce_depth_cap, enforce_rpm_cap, should_emergency_stop
from abu.tcb.monitor import validate_and_enforce_safety

def test_enforce_depth_cap():
    assert enforce_depth_cap(50.0, 100.0) is True
    assert enforce_depth_cap(100.0, 100.0) is True
    assert enforce_depth_cap(100.1, 100.0) is False

def test_enforce_rpm_cap():
    assert enforce_rpm_cap(250.0, 300.0) is True
    assert enforce_rpm_cap(300.0, 300.0) is True
    assert enforce_rpm_cap(301.0, 300.0) is False

def test_should_emergency_stop_by_risk():
    assert should_emergency_stop(risk="high", vibration_score=0.5) is True
    assert should_emergency_stop(risk="medium", vibration_score=0.5) is False
    assert should_emergency_stop(risk="low", vibration_score=0.5) is False

def test_should_emergency_stop_by_vibration():
    assert should_emergency_stop(risk="low", vibration_score=0.95, vib_threshold=0.9) is True
    assert should_emergency_stop(risk="low", vibration_score=0.85, vib_threshold=0.9) is False

def test_security_monitor_enforces_emergency_on_compromised_ai():
    status = validate_and_enforce_safety(
        current_depth=10.0,
        target_depth=50.0,
        rpm=150.0,
        max_rpm_cap=300.0,
        risk="low",
        vibration_score=0.95
    )
    assert status == "emergency"

def test_security_monitor_blocks_overflow_rpm_command():
    status = validate_and_enforce_safety(
        current_depth=10.0,
        target_depth=50.0,
        rpm=450.0,
        max_rpm_cap=400.0,
        risk="low",
        vibration_score=0.1
    )
    assert status == "stopped_rpm"

def test_security_monitor_blocks_overdrilling_attack():
    status = validate_and_enforce_safety(
        current_depth=55.0,
        target_depth=50.0,
        rpm=100.0,
        max_rpm_cap=300.0,
        risk="low",
        vibration_score=0.2
    )
    assert status == "stopped_depth"