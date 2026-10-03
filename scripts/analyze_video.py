"""Run the person-detection pipeline on a local video and print the occupancy JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.analysis.pipeline import PipelineConfig, analyze_video  # noqa: E402
from backend.app.store import record_analysis  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Count people in a training-centre video.")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--expected", type=int, default=None, help="Submitted attendance, if you want a variance.")
    parser.add_argument("--frame-interval", type=int, default=4)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--gap-threshold", type=int, default=3)
    parser.add_argument("--centre", default="TC-PB-001")
    args = parser.parse_args()

    config = PipelineConfig(
        model=args.model,
        confidence=args.confidence,
        frame_interval=args.frame_interval,
        device=args.device,
        attendance_gap_threshold=args.gap_threshold,
        expected_attendance=args.expected,
    )
    report = analyze_video(args.video, config)
    stored = record_analysis(report, args.centre)
    report = stored["report"]
    print(json.dumps(report, indent=2))
    print(
        f"\nObserved presence: {report['occupancy']['observed_presence']}"
        f"  status: {report['compliance']['attendance']['status']}"
        f"  evidence: {report['evidence']['peak_frame']}"
    )
    print(f"Alerts stored: {len(stored['alerts'])}")
    for alert in stored["alerts"]:
        print(f"  {alert['id']}  {alert['severity']}  {alert['alert_type']}  {alert['description']}")


if __name__ == "__main__":
    main()
