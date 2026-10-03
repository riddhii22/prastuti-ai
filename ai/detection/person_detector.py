"""YOLO detector for the classes this demo actually uses.

COCO person, chair, and dining table. No face model is loaded.
A dining table is not a workbench. Callers must keep that label.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

CLASS_NAMES = {
    0: "person",
    56: "chair",
    60: "dining table",
}


@dataclass
class Detection:
    box: tuple[float, float, float, float]
    confidence: float
    label: str


class PersonDetector:
    def __init__(self, model_name: str, confidence: float, device: str) -> None:
        from ultralytics import YOLO

        weights = _resolve_weights(model_name)
        self.model_name = weights.name
        self.confidence = confidence
        self.device = device
        self._model = YOLO(str(weights))

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            source=frame,
            classes=list(CLASS_NAMES),
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )
        detections: list[Detection] = []
        if not results:
            return detections
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)
        for box, conf, class_id in zip(xyxy, confs, class_ids):
            label = CLASS_NAMES.get(int(class_id))
            if label is None:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.tolist())
            detections.append(Detection(box=(x1, y1, x2, y2), confidence=float(conf), label=label))
        return detections


def _resolve_weights(model_name: str) -> Path:
    """Use a local weights file when present. Otherwise let Ultralytics fetch the named checkpoint."""
    root = Path(__file__).resolve().parents[2]
    local = root / "models" / model_name
    local.parent.mkdir(parents=True, exist_ok=True)
    if local.exists():
        return local
    return local
