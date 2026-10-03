"""Build demo/workshop.mp4 from the generated workshop still.

The still is a synthetic centre photograph created for this prototype.
The clip is a slow pan of that still so the pipeline has a real video file.
It is not footage from a training centre.
"""

from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STILL = ROOT / "demo" / "workshop_still.jpg"
OUT = ROOT / "demo" / "workshop.mp4"


def main() -> None:
    image = cv2.imread(str(STILL))
    if image is None:
        raise SystemExit(f"Missing still: {STILL}")
    height, width = image.shape[:2]
    scale = 1.08
    enlarged = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_LINEAR)
    eh, ew = enlarged.shape[:2]
    max_x = ew - width
    max_y = eh - height
    fps = 8
    frames = 32
    writer = cv2.VideoWriter(str(OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for i in range(frames):
        t = i / max(frames - 1, 1)
        x = int(max_x * (0.5 - 0.5 * np.cos(np.pi * t)) * 0.35)
        y = int(max_y * 0.2 * np.sin(np.pi * t))
        crop = enlarged[y : y + height, x : x + width]
        writer.write(crop)
    writer.release()
    print(f"Wrote {OUT} ({frames} frames at {fps} fps)")


if __name__ == "__main__":
    main()
