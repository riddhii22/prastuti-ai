from backend.app import store


def _report(observed: int = 9) -> dict:
    return {
        "analysis_id": "an_test",
        "source_filename": "workshop.mp4",
        "expected_attendance": 12,
        "attendance_gap_threshold": 3,
        "variance": 3,
        "occupancy": {"observed_presence": observed},
        "objects": {
            "chair": {"peak": 4},
            "dining table": {"peak": 4},
        },
        "evidence": {"peak_frame": "evidence/an_test/peak_frame.jpg"},
    }


def test_record_analysis_stores_attendance_and_seat_alerts(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "prastuti.db")
    stored = store.record_analysis(_report(), "TC-PB-001")
    kinds = [alert["alert_type"] for alert in stored["alerts"]]
    assert "attendance" in kinds
    seat_alerts = [alert for alert in stored["alerts"] if "Seats" in alert["description"]]
    assert seat_alerts
    assert "AI_DETECTED" in seat_alerts[0]["description"]
    machine_alerts = [alert for alert in stored["alerts"] if "Training machines" in alert["description"]]
    assert machine_alerts == []

    updated = store.update_alert_status(stored["alerts"][0]["id"], "under_review")
    assert updated["status"] == "under_review"
    centre = store.get_centre("TC-PB-001")
    assert centre["centre"]["name"] == "Prastuti Skill Development Centre"
    seats = next(item for item in centre["inventory"] if item["item_key"] == "seats")
    assert seats["observed"] == 4
    assert seats["source"] == "AI_DETECTED"
    machines = next(item for item in centre["inventory"] if item["item_key"] == "training_machines")
    assert machines["status"] == "NOT_ASSESSED"
    summary = store.dashboard_summary()
    assert summary["centres_monitored"] == 1
    assert summary["open_attendance_alerts"] == 1
    assert summary["source"] == "local_database"