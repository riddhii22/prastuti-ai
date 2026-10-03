from ai.compliance.engine import InventoryItem, attendance_check, inventory_check


def test_attendance_alert_when_the_gap_meets_the_threshold():
    result = attendance_check(12, 9, 3)
    assert result["status"] == "ALERT"
    assert result["variance"] == 3
    assert result["source"] == "AI_DETECTED"


def test_attendance_review_for_a_smaller_gap():
    assert attendance_check(12, 11, 3)["status"] == "REVIEW"


def test_attendance_compliant_when_the_count_meets_the_register():
    assert attendance_check(8, 9, 3)["status"] == "COMPLIANT"


def test_inventory_uses_model_peaks_and_leaves_untrained_items_alone():
    items = [
        InventoryItem("seats", "Seats", 25, "chair", 1, "chair stand-in"),
        InventoryItem("training_machines", "Training machines", 3, None, 1, "no class"),
    ]
    rows = inventory_check(items, {"chair": 4})
    seats, machines = rows
    assert seats["source"] == "AI_DETECTED"
    assert seats["observed"] == 4
    assert seats["status"] == "ALERT"
    assert machines["source"] == "NOT_ASSESSED"
    assert machines["observed"] is None
    assert machines["status"] == "NOT_ASSESSED"


def test_missing_class_peak_counts_as_zero_detections():
    rows = inventory_check([InventoryItem("seats", "Seats", 2, "chair")], {})
    assert rows[0]["observed"] == 0
    assert rows[0]["status"] == "ALERT"
