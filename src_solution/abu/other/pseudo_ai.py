from __future__ import annotations
from typing import Literal

def anomaly_vibration(samples: list[float]) -> float:
    if not samples:
        return 1.0
    if len(samples) == 1:
        return 0.0
    window = samples[-5:]
    mean = sum(window) / len(window)
    last = window[-1]
    spread = max(abs(x - mean) for x in window) or 1e-9
    raw = abs(last - mean) / spread
    return max(0.0, min(1.0, raw))

def regime_suggest(depth_m: float, torque_nm: float) -> tuple[float, float]:
    rpm = 120.0 + min(depth_m * 2.0, 80.0)
    if torque_nm > 5000:
        rpm *= 0.85
    feed = 0.2 + min(depth_m * 0.01, 0.15)
    return round(rpm, 1), round(feed, 3)

RiskLevel = Literal["low", "medium", "high"]

def risk_flag(vibration: float, pressure: float, depth_m: float) -> RiskLevel:
    score = 0
    if vibration > 0.75:
        score += 2
    if pressure > 180.0:
        score += 2
    if depth_m > 95.0:
        score += 1
    if score >= 3:
        return "high"
    if score >= 1:
        return "medium"
    return "low"