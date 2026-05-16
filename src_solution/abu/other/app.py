from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src_solution.abu.tcb.event_log import EventLevel, default_log
from src_solution.abu.tcb.monitor import validate_and_enforce_safety
from src_solution.abu.other.numpy_workflow import smooth_vibration_window
from src_solution.abu.other.pseudo_ai import anomaly_vibration, regime_suggest, risk_flag

app = FastAPI(title="АБУ (прототип)", version="0.1.0")

class MissionIn(BaseModel):
    target_depth_m: float = Field(gt=0, le=200)
    max_rpm: float = Field(default=300.0, gt=0)

class MissionState(BaseModel):
    mission_id: str
    target_depth_m: float
    depth_m: float = 0.0
    rpm: float = 0.0
    torque_nm: float = 2000.0
    pressure: float = 120.0
    vibration_samples: list[float] = Field(default_factory=list)
    status: str = "running"

_mission: MissionState | None = None

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    default_log.record(EventLevel.INFO, "health_check")
    return {"status": "ok", "service": "abu"}

@app.get("/api/v1/events/ring")
def events_ring() -> dict[str, list[str]]:
    return {"lines": default_log.ring_snapshot()}

@app.get("/api/v1/events/full")
def events_full_tail() -> dict[str, str]:
    return {"log": default_log.read_full_tail()}

@app.get("/api/v1/status")
def status() -> dict[str, Any]:
    if _mission is None:
        return {"idle": True}
    m = _mission
    vibration_score = anomaly_vibration(m.vibration_samples) if m.vibration_samples else 0.0
    risk = risk_flag(vibration_score, m.pressure, m.depth_m)
    return {
        "idle": False,
        "mission_id": m.mission_id,
        "depth_m": m.depth_m,
        "rpm": m.rpm,
        "torque_nm": m.torque_nm,
        "pressure": m.pressure,
        "vibration_score": vibration_score,
        "risk": risk,
        "mission_status": m.status,
    }

@app.post("/api/v1/missions")
def start_mission(body: MissionIn) -> dict[str, Any]:
    global _mission
    mid = str(uuid.uuid4())
    _mission = MissionState(
        mission_id=mid,
        target_depth_m=body.target_depth_m,
        rpm=min(150.0, body.max_rpm),
    )
    default_log.record(
        EventLevel.INFO,
        f"mission_started mission_id={mid} target_depth_m={body.target_depth_m}",
    )
    return {"accepted": True, "mission_id": mid}

@app.get("/api/v1/missions/current")
def current_mission() -> dict[str, Any]:
    if _mission is None:
        raise HTTPException(status_code=404, detail="нет активной миссии")
    return _mission.model_dump()

@app.post("/api/v1/missions/tick")
def tick_step() -> dict[str, Any]:
    global _mission
    if _mission is None:
        raise HTTPException(status_code=400, detail="нет миссии")
    m = _mission
    if m.status != "running":
        return {"done": True, "status": m.status}
    m.depth_m = round(min(m.depth_m + 0.5, m.target_depth_m), 2)
    m.vibration_samples.append(0.1 + 0.05 * (m.depth_m % 3))
    _smooth = smooth_vibration_window(m.vibration_samples)
    vibration_score = anomaly_vibration(m.vibration_samples) if m.vibration_samples else 0.0
    risk = risk_flag(vibration_score, m.pressure, m.depth_m)
    default_log.record(
        EventLevel.INFO,
        f"tick depth={m.depth_m} smooth_vib={_smooth:.4f}",
    )
    m.torque_nm = 2000 + m.depth_m * 30
    m.pressure = 120 + m.depth_m * 0.4
    rpm_suggest, _feed = regime_suggest(m.depth_m, m.torque_nm)
    try:
        cap = float(os.environ.get("ABU_MAX_RPM", "300"))
    except ValueError:
        cap = 300.0
    m.rpm = min(rpm_suggest, cap)
    if risk == "high":
        default_log.record(
            EventLevel.WARNING,
            f"risk_high depth_m={m.depth_m:.2f} rpm={m.rpm:.1f}",
        )
    max_rpm_env = float(os.environ.get("ABU_MAX_RPM", "400"))
    m.status = validate_and_enforce_safety(
        current_depth=m.depth_m,
        target_depth=m.target_depth_m,
        rpm=m.rpm,
        max_rpm_cap=max_rpm_env,
        risk=risk,
        vibration_score=vibration_score
    )
    return {"mission": m.model_dump(), "risk": risk}

class AISuggestIn(BaseModel):
    depth_m: float = Field(ge=0)
    torque_nm: float = Field(ge=0)

@app.post("/api/v1/ai/suggest")
def ai_suggest(body: AISuggestIn) -> dict[str, float]:
    rpm, feed = regime_suggest(body.depth_m, body.torque_nm)
    return {"suggested_rpm": rpm, "suggested_feed_mm_rev": feed}