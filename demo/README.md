# Demo clip

`workshop_still.jpg` is a synthetic workshop photograph made for this prototype. It is not a recording from a training centre.

`workshop.mp4` is a slow pan of that still, produced by:

```bash
python scripts/make_demo_clip.py
```

Person counts on this clip come from YOLO. They are not typed in by hand.

A CPU run with `yolo11n` at confidence 0.35 counted 8 people on most sampled frames. One frame counted 9 because two boxes landed on the same person. The JSON keeps every frame count, so a later run can differ slightly.
