"""API for the vision pipeline and the compliance records stored in SQLite."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.analysis.pipeline import EVIDENCE_ROOT, ROOT, PipelineConfig, analyze_video
from backend.app.schemas import AnalyzeResponse
from backend.app.store import (
    dashboard_summary,
    get_alert,
    get_centre,
    init_db,
    list_alerts,
    list_centres,
    record_analysis,
    submitted_attendance,
    update_alert_status,
)

app = FastAPI(title="Prastuti AI", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8742", "http://localhost:8742"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS = ROOT / "data" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)


class AlertStatusUpdate(BaseModel):
    status: str


@app.on_event("startup")
def startup() -> None:
    init_db()


def _config(expected: int | None, frame_interval: int | None, confidence: float | None) -> PipelineConfig:
    return PipelineConfig(
        model=os.getenv("MODEL", "yolo11n.pt"),
        confidence=confidence if confidence is not None else float(os.getenv("CONFIDENCE_THRESHOLD", "0.35")),
        frame_interval=frame_interval if frame_interval is not None else int(os.getenv("FRAME_INTERVAL", "5")),
        device=os.getenv("DEVICE", "cpu"),
        attendance_gap_threshold=int(os.getenv("ATTENDANCE_GAP_THRESHOLD", "3")),
        expected_attendance=expected,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "phase": 3, "facial_identification": False}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return dashboard_summary()


@app.post("/api/analyze/demo")
def analyze_demo(centre_id: str = "TC-PB-001") -> dict:
    if get_centre(centre_id) is None:
        raise HTTPException(status_code=404, detail="Centre not found.")
    video = ROOT / "demo" / "workshop.mp4"
    if not video.exists():
        raise HTTPException(status_code=400, detail="demo/workshop.mp4 is missing.")
    try:
        report = analyze_video(video, _config(submitted_attendance(centre_id), 4, None))
        stored = record_analysis(report, centre_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    return {"alerts": stored["alerts"], "report": stored["report"]}


@app.get("/api/centres")
def centres() -> list[dict]:
    return list_centres()


@app.get("/api/centres/{centre_id}")
def centre_detail(centre_id: str) -> dict:
    centre = get_centre(centre_id)
    if centre is None:
        raise HTTPException(status_code=404, detail="Centre not found.")
    return centre


@app.get("/api/inventory/{centre_id}")
def inventory(centre_id: str) -> dict:
    centre = get_centre(centre_id)
    if centre is None:
        raise HTTPException(status_code=404, detail="Centre not found.")
    return {"centre_id": centre_id, "inventory": centre["inventory"]}


@app.get("/api/alerts")
def alerts(centre_id: str | None = None) -> list[dict]:
    return list_alerts(centre_id)


@app.get("/api/alerts/{alert_id}")
def alert_detail(alert_id: str) -> dict:
    alert = get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


@app.patch("/api/alerts/{alert_id}")
def alert_status(alert_id: str, body: AlertStatusUpdate) -> dict:
    try:
        updated = update_alert_status(alert_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return updated


@app.post("/api/analyze/video", response_model=AnalyzeResponse)
async def analyze_upload(
    video: UploadFile = File(...),
    expected_attendance: int | None = Form(default=None),
    frame_interval: int | None = Form(default=None),
    confidence: float | None = Form(default=None),
    centre_id: str = Form(default="TC-PB-001"),
) -> AnalyzeResponse:
    if not video.filename:
        raise HTTPException(status_code=400, detail="Upload a video file.")
    suffix = Path(video.filename).suffix.lower()
    if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        raise HTTPException(status_code=400, detail="Use an mp4, avi, mov, mkv, or webm file.")
    if get_centre(centre_id) is None:
        raise HTTPException(status_code=404, detail="Centre not found.")
    if expected_attendance is None:
        expected_attendance = submitted_attendance(centre_id)
    destination = UPLOADS / Path(video.filename).name
    destination.write_bytes(await video.read())
    try:
        report = analyze_video(destination, _config(expected_attendance, frame_interval, confidence))
        stored = record_analysis(report, centre_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    report = stored["report"]
    return AnalyzeResponse(
        analysis_id=report["analysis_id"],
        status=report["compliance"]["attendance"]["status"],
        observed_presence=report["occupancy"]["observed_presence"],
        expected_attendance=report["expected_attendance"],
        variance=report["variance"],
        evidence_peak_frame=report["evidence"]["peak_frame"],
        report=report,
    )


@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: str) -> dict:
    path = EVIDENCE_ROOT / analysis_id / "analysis.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/analysis/{analysis_id}/evidence/{name}")
def get_evidence(analysis_id: str, name: str) -> FileResponse:
    if name not in {"peak_frame.jpg", "annotated.mp4", "analysis.json"}:
        raise HTTPException(status_code=404, detail="Unknown evidence file.")
    path = EVIDENCE_ROOT / analysis_id / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    media = "image/jpeg" if name.endswith(".jpg") else "video/mp4" if name.endswith(".mp4") else "application/json"
    return FileResponse(path, media_type=media)


_DIST = ROOT / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="dashboard")
