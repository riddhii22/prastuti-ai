# Prastuti AI

Local tool for one training centre. It samples a video, counts people, chairs, and dining tables with YOLO, and stores attendance and inventory alerts in `data/prastuti.db`. The page at http://127.0.0.1:8741 reads those rows.

The slide deck is `PRastuti-AI-SIH2026.pptx`.

The demo file `demo/workshop.mp4` is a slow pan of `demo/workshop_still.jpg`. That still is a synthetic workshop photo, not centre CCTV. The counts in the JSON are whatever the model returned on that clip.

No face detector runs. Each evidence frame is labelled `no facial id`.

## Run the video check

From the project folder, with the virtual environment already installed:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_video.py --video demo/workshop.mp4 --expected 12 --centre TC-PB-001
```

The first run downloads `yolo11n.pt` into `models/`. It uses the CPU unless you pass `--device`.

If you are installing from scratch:

```powershell
"C:\Program Files\Python313\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/make_demo_clip.py
```

Use Python 3.13. `py -3` on this machine can pick Python 3.14 free-threaded, and those wheels do not install.

## What gets counted

Frames are sampled (every 4th frame in the command above, every 5th if you leave the env default). The model keeps three COCO classes: person, chair, and dining table.

Observed presence is the peak person count on one sampled frame. Boxes are tracked with IoU so the same person is not treated as a new identity on every frame. Tracks are not names.

Each run writes `evidence/<analysis_id>/peak_frame.jpg`, `annotated.mp4`, and `analysis.json`.

Attendance, when you pass `--expected`:

- `ALERT` if expected minus observed is at least 3
- `REVIEW` if the gap is smaller but still above 0
- `COMPLIANT` if observed meets or exceeds the submitted number
- `OBSERVED_ONLY` if you do not pass an expected number

The seeded centre is Prastuti Skill Development Centre, `TC-PB-001`, Punjab. Submitted attendance is 12.

| Line | Sanctioned | What is counted |
| --- | --- | --- |
| Seats | 25 | Peak chair count. A chair box is not a verified seat. |
| Workbenches | 4 | Peak dining-table count. The label stays dining table. |
| Training machines | 3 | Not assessed. No class in this model. |
| Projectors | 1 | Not assessed. No class in this model. |

Alerts are stored only for `ALERT` and `REVIEW`. `NOT_ASSESSED` lines stay in the JSON and do not become alerts.

## Open the page

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8741
```

Open http://127.0.0.1:8741

The menu is the green column on the left. The four numbers, the 0/3 ring, and the alert table all come from `data/prastuti.db`. Mark an alert under review or resolved on its page.

The Analyze page runs `demo/workshop.mp4` and writes another set of alerts. For a recording, use the alerts already stored and do not press Analyze. The click path is in `DEMO.md`.

## Settings

See `.env.example`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `FRAME_INTERVAL` | 5 | Process one frame out of every N |
| `MODEL` | `yolo11n.pt` | Ultralytics checkpoint |
| `CONFIDENCE_THRESHOLD` | 0.35 | Box cutoff |
| `DEVICE` | `cpu` | `cpu` or a CUDA id |
| `ATTENDANCE_GAP_THRESHOLD` | 3 | Gap that raises `ALERT` |

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

The tracker test does not load YOLO.

## Not in this build

No accuracy study. No live centre camera. Training machines and projectors are not detected. Nothing here is installed on centre hardware. A missing video returns an error and does not invent a count.