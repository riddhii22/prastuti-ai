"""Lightweight IoU tracker for presence, not identity.

Tracks keep a box across sampled frames so the same person is not counted
again on every frame. There is no appearance embedding and no face.
"""

from __future__ import annotations


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


class Track:
    def __init__(self, track_id: int, box: tuple[float, float, float, float]) -> None:
        self.track_id = track_id
        self.box = box
        self.hits = 1
        self.missed = 0


def update_tracks(
    tracks: list[Track],
    detections: list[tuple[float, float, float, float]],
    next_id: int,
    iou_threshold: float = 0.25,
    max_missed: int = 2,
) -> tuple[list[Track], int]:
    """Greedy IoU association. Returns the live tracks and the next free id."""
    unmatched = set(range(len(detections)))
    used_tracks: set[int] = set()

    pairs: list[tuple[float, int, int]] = []
    for ti, track in enumerate(tracks):
        for di, box in enumerate(detections):
            score = iou(track.box, box)
            if score >= iou_threshold:
                pairs.append((score, ti, di))
    pairs.sort(reverse=True)

    for _score, ti, di in pairs:
        if ti in used_tracks or di not in unmatched:
            continue
        tracks[ti].box = detections[di]
        tracks[ti].hits += 1
        tracks[ti].missed = 0
        used_tracks.add(ti)
        unmatched.remove(di)

    for ti, track in enumerate(tracks):
        if ti not in used_tracks:
            track.missed += 1

    alive = [track for track in tracks if track.missed <= max_missed]
    for di in sorted(unmatched):
        alive.append(Track(next_id, detections[di]))
        next_id += 1
    return alive, next_id
