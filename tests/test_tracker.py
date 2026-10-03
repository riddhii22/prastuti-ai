from ai.detection.tracker import iou, update_tracks


def test_iou_identical_box_is_one():
    box = (0, 0, 10, 10)
    assert iou(box, box) == 1


def test_tracker_keeps_one_identity_when_the_box_moves_slightly():
    tracks, next_id = update_tracks([], [(0, 0, 20, 40)], 1)
    assert next_id == 2
    tracks, next_id = update_tracks(tracks, [(2, 1, 22, 41)], next_id)
    assert next_id == 2
    assert len(tracks) == 1
    assert tracks[0].hits == 2


def test_tracker_opens_a_new_track_for_a_distant_box():
    tracks, next_id = update_tracks([], [(0, 0, 10, 10)], 1)
    tracks, next_id = update_tracks(tracks, [(0, 0, 10, 10), (100, 100, 130, 140)], next_id)
    assert len(tracks) == 2
    assert next_id == 3
