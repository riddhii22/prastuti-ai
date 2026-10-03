"""SQLite store for centres, inventory, analysis runs, and alerts."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ai.compliance.engine import InventoryItem, attendance_check, inventory_check

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "prastuti.db"

ALERT_STATUSES = {"new", "under_review", "resolved"}

SEED_CENTRE = {
    "id": "TC-PB-001",
    "name": "Prastuti Skill Development Centre",
    "location": "Punjab",
    "submitted_attendance": 12,
}

SEED_ITEMS = [
    InventoryItem(
        "seats",
        "Seats",
        25,
        "chair",
        1,
        "Compared with the peak COCO chair count. A chair box is not a verified seat.",
    ),
    InventoryItem(
        "workbenches",
        "Workbenches",
        4,
        "dining table",
        1,
        "Compared with the peak COCO dining-table count. This model is not trained on workbenches.",
    ),
    InventoryItem(
        "training_machines",
        "Training machines",
        3,
        None,
        1,
        "No class in the pretrained model. This line is not counted.",
    ),
    InventoryItem(
        "projectors",
        "Projectors",
        1,
        None,
        1,
        "No class in the pretrained model. This line is not counted.",
    ),
]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS centres (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                submitted_attendance INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS inventory_items (
                centre_id TEXT NOT NULL,
                item_key TEXT NOT NULL,
                label TEXT NOT NULL,
                sanctioned INTEGER NOT NULL,
                coco_name TEXT,
                gap_threshold INTEGER NOT NULL,
                note TEXT NOT NULL,
                PRIMARY KEY (centre_id, item_key)
            );
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id TEXT PRIMARY KEY,
                centre_id TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                observed_presence INTEGER NOT NULL,
                expected_attendance INTEGER,
                variance INTEGER,
                status TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                centre_id TEXT NOT NULL,
                analysis_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_path TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO centres (id, name, location, submitted_attendance)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                location = excluded.location,
                submitted_attendance = excluded.submitted_attendance
            """,
            (
                SEED_CENTRE["id"],
                SEED_CENTRE["name"],
                SEED_CENTRE["location"],
                SEED_CENTRE["submitted_attendance"],
            ),
        )
        for item in SEED_ITEMS:
            connection.execute(
                """
                INSERT INTO inventory_items
                    (centre_id, item_key, label, sanctioned, coco_name, gap_threshold, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(centre_id, item_key) DO UPDATE SET
                    label = excluded.label,
                    sanctioned = excluded.sanctioned,
                    coco_name = excluded.coco_name,
                    gap_threshold = excluded.gap_threshold,
                    note = excluded.note
                """,
                (
                    SEED_CENTRE["id"],
                    item.item_key,
                    item.label,
                    item.sanctioned,
                    item.coco_name,
                    item.gap_threshold,
                    item.note,
                ),
            )


def submitted_attendance(centre_id: str) -> int | None:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT submitted_attendance FROM centres WHERE id = ?", (centre_id,)).fetchone()
    if row is None:
        return None
    return int(row["submitted_attendance"])


def record_analysis(report: dict, centre_id: str = "TC-PB-001") -> dict:
    """Apply the rules to a vision report and store the run plus any alerts."""
    init_db()
    items = _items(centre_id)
    if not items and centre_id != SEED_CENTRE["id"]:
        raise KeyError(f"Unknown centre: {centre_id}")
    peaks = {name: int(payload["peak"]) for name, payload in report.get("objects", {}).items()}
    attendance = attendance_check(
        report.get("expected_attendance"),
        int(report["occupancy"]["observed_presence"]),
        int(report["attendance_gap_threshold"]),
    )
    inventory = inventory_check(items, peaks)
    compliance = {"attendance": attendance, "inventory": inventory}
    report = {**report, "centre_id": centre_id, "compliance": compliance}
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    alerts = _alert_rows(centre_id, report["analysis_id"], attendance, inventory, report["evidence"]["peak_frame"], created_at)

    with connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO analysis_runs
                (id, centre_id, source_filename, observed_presence, expected_attendance, variance, status, report_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report["analysis_id"],
                centre_id,
                report["source_filename"],
                attendance["observed"],
                attendance["expected"],
                attendance["variance"],
                attendance["status"],
                json.dumps(report),
                created_at,
            ),
        )
        connection.execute("DELETE FROM alerts WHERE analysis_id = ?", (report["analysis_id"],))
        connection.executemany(
            """
            INSERT INTO alerts
                (id, centre_id, analysis_id, alert_type, severity, status, description, evidence_path, created_at)
            VALUES (:id, :centre_id, :analysis_id, :alert_type, :severity, :status, :description, :evidence_path, :created_at)
            """,
            alerts,
        )
    from ai.analysis.pipeline import EVIDENCE_ROOT

    evidence_dir = EVIDENCE_ROOT / report["analysis_id"]
    if evidence_dir.exists():
        (evidence_dir / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"report": report, "alerts": alerts}


def list_centres() -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM centres ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def get_centre(centre_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        centre = connection.execute("SELECT * FROM centres WHERE id = ?", (centre_id,)).fetchone()
        if centre is None:
            return None
        latest = connection.execute(
            "SELECT report_json, created_at FROM analysis_runs WHERE centre_id = ? ORDER BY created_at DESC LIMIT 1",
            (centre_id,),
        ).fetchone()
        alerts = connection.execute(
            "SELECT * FROM alerts WHERE centre_id = ? ORDER BY created_at DESC, id DESC",
            (centre_id,),
        ).fetchall()
    inventory = [row_to_public(item) for item in _items(centre_id)]
    latest_report = json.loads(latest["report_json"]) if latest else None
    if latest_report:
        by_key = {row["item_key"]: row for row in latest_report["compliance"]["inventory"]}
        for item in inventory:
            item.update({key: by_key[item["item_key"]][key] for key in ("observed", "variance", "status", "source")})
    return {
        "centre": dict(centre),
        "inventory": inventory,
        "latest_analysis": latest_report,
        "alerts": [dict(row) for row in alerts],
    }


def dashboard_summary() -> dict:
    """Counts and lists taken only from this local database."""
    init_db()
    centres = list_centres()
    alerts = list_alerts()
    open_alerts = [row for row in alerts if row["status"] != "resolved"]
    centre_rows = []
    assessed = 0
    compliant = 0
    activity = []
    with connect() as connection:
        runs = connection.execute(
            "SELECT id, centre_id, source_filename, status, created_at FROM analysis_runs ORDER BY created_at DESC LIMIT 8"
        ).fetchall()
    for centre in centres:
        detail = get_centre(centre["id"])
        latest = detail["latest_analysis"] if detail else None
        status = "NOT_RUN"
        observed = None
        expected = centre["submitted_attendance"]
        if latest:
            attendance = latest["compliance"]["attendance"]
            observed = attendance["observed"]
            expected = attendance["expected"]
            statuses = [attendance["status"]]
            for item in latest["compliance"]["inventory"]:
                if item["status"] == "NOT_ASSESSED":
                    continue
                statuses.append(item["status"])
            assessed += len(statuses)
            compliant += sum(1 for item_status in statuses if item_status == "COMPLIANT")
            if "ALERT" in statuses:
                status = "ALERT"
            elif "REVIEW" in statuses:
                status = "REVIEW"
            else:
                status = "COMPLIANT"
        centre_rows.append(
            {
                "id": centre["id"],
                "name": centre["name"],
                "location": centre["location"],
                "status": status,
                "observed_presence": observed,
                "submitted_attendance": expected,
            }
        )
    for run in runs:
        activity.append(
            {
                "created_at": run["created_at"],
                "text": f"Attendance analysis {run['status']} · {run['centre_id']} · {run['source_filename']}",
                "analysis_id": run["id"],
            }
        )
    return {
        "source": "local_database",
        "note": "These counts are rows in this prototype database. They are not a national or ministry statistic.",
        "centres_monitored": len(centres),
        "open_attendance_alerts": sum(1 for row in open_alerts if row["alert_type"] == "attendance"),
        "open_infrastructure_alerts": sum(1 for row in open_alerts if row["alert_type"] == "infrastructure"),
        "assessed_checks": assessed,
        "compliant_checks": compliant,
        "centres": centre_rows,
        "alerts": open_alerts[:12],
        "activity": activity[:8],
    }


def list_alerts(centre_id: str | None = None) -> list[dict]:
    init_db()
    with connect() as connection:
        if centre_id:
            rows = connection.execute(
                "SELECT * FROM alerts WHERE centre_id = ? ORDER BY created_at DESC, id DESC",
                (centre_id,),
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM alerts ORDER BY created_at DESC, id DESC").fetchall()
    return [dict(row) for row in rows]


def get_alert(alert_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return dict(row) if row else None


def update_alert_status(alert_id: str, status: str) -> dict | None:
    if status not in ALERT_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(sorted(ALERT_STATUSES))}")
    init_db()
    with connect() as connection:
        cursor = connection.execute("UPDATE alerts SET status = ? WHERE id = ?", (status, alert_id))
        if cursor.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return dict(row)


def _items(centre_id: str) -> list[InventoryItem]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM inventory_items WHERE centre_id = ? ORDER BY item_key",
            (centre_id,),
        ).fetchall()
    return [
        InventoryItem(
            row["item_key"],
            row["label"],
            int(row["sanctioned"]),
            row["coco_name"],
            int(row["gap_threshold"]),
            row["note"],
        )
        for row in rows
    ]


def row_to_public(item: InventoryItem) -> dict:
    return {
        "item_key": item.item_key,
        "label": item.label,
        "sanctioned": item.sanctioned,
        "coco_name": item.coco_name,
        "gap_threshold": item.gap_threshold,
        "note": item.note,
        "observed": None,
        "variance": None,
        "status": "NOT_RUN",
        "source": "AI_DETECTED" if item.coco_name else "NOT_ASSESSED",
    }


def _alert_rows(centre_id: str, analysis_id: str, attendance: dict, inventory: list[dict], evidence: str, created_at: str) -> list[dict]:
    rows = []
    sequence = 1
    if attendance["status"] in {"ALERT", "REVIEW"}:
        rows.append(
            {
                "id": f"{analysis_id}-A{sequence:02d}",
                "centre_id": centre_id,
                "analysis_id": analysis_id,
                "alert_type": "attendance",
                "severity": "high" if attendance["status"] == "ALERT" else "medium",
                "status": "new",
                "description": (
                    f"Submitted attendance {attendance['expected']}. "
                    f"Peak person count {attendance['observed']}. "
                    f"Gap {attendance['variance']}."
                ),
                "evidence_path": evidence,
                "created_at": created_at,
            }
        )
        sequence += 1
    for item in inventory:
        if item["status"] not in {"ALERT", "REVIEW"}:
            continue
        rows.append(
            {
                "id": f"{analysis_id}-A{sequence:02d}",
                "centre_id": centre_id,
                "analysis_id": analysis_id,
                "alert_type": "infrastructure",
                "severity": "medium",
                "status": "new",
                "description": (
                    f"{item['label']} sanctioned {item['sanctioned']}. "
                    f"Peak {item['coco_name']} count {item['observed']}. "
                    f"Gap {item['variance']}. Source: AI_DETECTED."
                ),
                "evidence_path": evidence,
                "created_at": created_at,
            }
        )
        sequence += 1
    return rows
