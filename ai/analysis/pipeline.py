"""Sample a video, count people, and write annotated evidence.

Observed presence is the peak person-count on a sampled frame.
A separate IoU tracker reports how many tracks were seen. Tracks are not identities.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from ai.detection.person_detector import Detection, PersonDetector
from ai.detection.tracker import Track, update_tracks

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = ROOT / "evidence"

OBJECT_LABELS = ("chair", "dining table")
BOX_COLORS = {
    "person": (214, 196, 0),
    "chair": (40, 140, 230),
    "dining table": (80, 170, 90),
}

PRIVACY = {
    "mode": "aggregate_presence",
    "facial_identification": False,
    "biometric_database": False,
    "note": "Person, chair, and dining-table boxes only. No face crop, name, or identity is stored.",
}


@dataclass
class PipelineConfig:
    model: str = "yolo11n.pt"
    confidence: float = 0.35
    frame_interval: int = 5
    device: str = "cpu"
    attendance_gap_threshold: int = 3
    expected_attendance: int | None = None


def analyze_video(video_path: Path, config: PipelineConfig, analysis_id: str | None = None) -> dict:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path.name}")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0) or 25.0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if width <= 0 or height <= 0:
        capture.release()
        raise ValueError(f"Video has no frames: {video_path.name}")

    analysis_id = analysis_id or f"an_{uuid.uuid4().hex[:12]}"
    out_dir = EVIDENCE_ROOT / analysis_id
    out_dir.mkdir(parents=True, exist_ok=True)

    detector = PersonDetector(config.model, config.confidence, config.device)
    interval = max(1, config.frame_interval)

    tracks: list[Track] = []
    next_id = 1
    per_frame_counts: list[int] = []
    object_counts = {label: [] for label in OBJECT_LABELS}
    sampled_indexes: list[int] = []
    peak_count = -1
    peak_image: np.ndarray | None = None
    peak_index = 0

    writer = cv2.VideoWriter(
        str(out_dir / "annotated.mp4"),
        cv2.VideoWriter_fourcc(*"mp4v"),
        max(fps / interval, 2.0),
        (width, height),
    )

    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % interval != 0:
            index += 1
            continue
        detections = detector.detect(frame)
        people = [item for item in detections if item.label == "person"]
        tracks, next_id = update_tracks(tracks, [item.box for item in people], next_id)
        annotated = _draw(frame, detections, index, len(people))
        writer.write(annotated)
        count = len(people)
        per_frame_counts.append(count)
        for label in OBJECT_LABELS:
            object_counts[label].append(sum(1 for item in detections if item.label == label))
        sampled_indexes.append(index)
        if count > peak_count:
            peak_count = count
            peak_image = annotated
            peak_index = index
        index += 1

    capture.release()
    writer.release()

    if not per_frame_counts:
        raise ValueError(f"No frames could be sampled from {video_path.name}")

    if peak_image is None:
        peak_image = np.zeros((height, width, 3), dtype=np.uint8)
    peak_file = out_dir / "peak_frame.jpg"
    cv2.imwrite(str(peak_file), peak_image)

    observed = max(per_frame_counts)
    unique_tracks = next_id - 1
    mean_count = round(sum(per_frame_counts) / len(per_frame_counts), 2)
    variance = None if config.expected_attendance is None else config.expected_attendance - observed
    status = _status(config.expected_attendance, observed, config.attendance_gap_threshold)

    report = {
        "analysis_id": analysis_id,
        "source_filename": video_path.name,
        "model": detector.model_name,
        "device": config.device,
        "confidence_threshold": config.confidence,
        "frame_interval": interval,
        "privacy": PRIVACY,
        "video": {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration_sec": round(frame_count / fps, 2) if fps else None,
        },
        "occupancy": {
            "frames_sampled": len(per_frame_counts),
            "sampled_frame_indexes": sampled_indexes,
            "per_frame_counts": per_frame_counts,
            "observed_presence": observed,
            "observed_presence_meaning": "Peak person count on one sampled frame.",
            "mean_simultaneous": mean_count,
            "estimated_unique_tracks": unique_tracks,
            "tracker": "Greedy IoU across sampled frames. A track is presence, not a person identity.",
            "peak_frame_index": peak_index,
        },
        "expected_attendance": config.expected_attendance,
        "variance": variance,
        "attendance_gap_threshold": config.attendance_gap_threshold,
        "status": status,
        "rule": (
            "ALERT when expected_attendance is set and "
            "(expected_attendance - observed_presence) >= attendance_gap_threshold. "
            "REVIEW when the gap is positive but below the threshold. "
            "OBSERVED_ONLY when no expected attendance was provided."
        ),
        "objects": {
            label: {
                "coco_name": label,
                "source": "AI_DETECTED",
                "per_frame_counts": counts,
                "peak": max(counts) if counts else 0,
                "meaning": "Peak count of this COCO class on one sampled frame.",
            }
            for label, counts in object_counts.items()
        },
        "evidence": {
            "annotated_video": str((out_dir / "annotated.mp4").relative_to(ROOT)),
            "peak_frame": str(peak_file.relative_to(ROOT)),
        },
    }
    (out_dir / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _status(expected: int | None, observed: int, threshold: int) -> str:
    if expected is None:
        return "OBSERVED_ONLY"
    gap = expected - observed
    if gap >= threshold:
        return "ALERT"
    if gap > 0:
        return "REVIEW"
    return "COMPLIANT"


def _draw(frame: np.ndarray, detections: list[Detection], frame_index: int, person_count: int) -> np.ndarray:
    image = frame.copy()
    for item in detections:
        x1, y1, x2, y2 = (int(v) for v in item.box)
        color = BOX_COLORS.get(item.label, (214, 196, 0))
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        label = f"{item.label} {item.confidence:.2f}"
        width, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
        cv2.rectangle(image, (x1, max(0, y1 - 18)), (x1 + width + 8, y1), color, -1)
        cv2.putText(image, label, (x1 + 4, max(12, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (15, 30, 45), 1, cv2.LINE_AA)
    banner = f"frame {frame_index}   persons {person_count}   no facial id"
    cv2.rectangle(image, (0, 0), (image.shape[1], 28), (20, 32, 48), -1)
    cv2.putText(image, banner, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (190, 240, 255), 1, cv2.LINE_AA)
    return image
