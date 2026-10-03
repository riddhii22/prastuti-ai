"""Rule checks for attendance and sanctioned inventory.

A gap is expected minus observed. The status names are the whole score.
Nothing here invents a detection.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryItem:
    item_key: str
    label: str
    sanctioned: int
    coco_name: str | None
    gap_threshold: int = 1
    note: str = ""


def attendance_status(expected: int | None, observed: int, threshold: int) -> str:
    if expected is None:
        return "OBSERVED_ONLY"
    gap = expected - observed
    if gap >= threshold:
        return "ALERT"
    if gap > 0:
        return "REVIEW"
    return "COMPLIANT"


def attendance_check(expected: int | None, observed: int, threshold: int) -> dict:
    gap = None if expected is None else expected - observed
    status = attendance_status(expected, observed, threshold)
    return {
        "kind": "attendance",
        "expected": expected,
        "observed": observed,
        "variance": gap,
        "threshold": threshold,
        "status": status,
        "source": "AI_DETECTED",
        "rule": (
            "ALERT when expected - observed person count >= threshold. "
            "REVIEW when the gap is positive and smaller. "
            "COMPLIANT when observed presence meets the submitted count."
        ),
    }


def inventory_check(items: list[InventoryItem], peaks: dict[str, int]) -> list[dict]:
    """Compare each sanctioned line with a model peak, or mark it unassessed."""
    rows = []
    for item in items:
        if not item.coco_name:
            rows.append(
                {
                    "item_key": item.item_key,
                    "label": item.label,
                    "sanctioned": item.sanctioned,
                    "observed": None,
                    "variance": None,
                    "status": "NOT_ASSESSED",
                    "source": "NOT_ASSESSED",
                    "coco_name": None,
                    "note": item.note,
                }
            )
            continue
        observed = int(peaks.get(item.coco_name, 0))
        gap = item.sanctioned - observed
        if gap >= item.gap_threshold:
            status = "ALERT"
        elif gap > 0:
            status = "REVIEW"
        else:
            status = "COMPLIANT"
        rows.append(
            {
                "item_key": item.item_key,
                "label": item.label,
                "sanctioned": item.sanctioned,
                "observed": observed,
                "variance": gap,
                "status": status,
                "source": "AI_DETECTED",
                "coco_name": item.coco_name,
                "note": item.note,
            }
        )
    return rows
