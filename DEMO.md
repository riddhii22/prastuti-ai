# Prastuti AI — 2 to 3 minute demo

Use the records already stored for **Prastuti Skill Development Centre**, `TC-PB-001`. Do not press **Analyze camera sample** during the recording. That writes another run, and the centre page will show the newest one.

Start from the project folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8741
```

Open http://127.0.0.1:8741

If the centre page does not show submitted 12, observed 9, and gap 3, say the numbers that are on the screen. Do not replace them with these.

## What to say, in order

**Dashboard, about 40 seconds.** Read the line under Monitoring: these counts are rows in this prototype database, not a national or ministry statistic. Point at the four figures: 1 centre, 1 open attendance alert, 2 open infrastructure alerts, 0/3 compliant checks. Point at the centre row and the red ALERT pill. In the table, read one attendance row as Submitted 12, Observed 9, Gap 3, and one infrastructure row as Sanctioned 4, Observed 1 dining table, Gap 3.

**Centre, about 50 seconds.** Open Centre. Read Submitted attendance 12, Observed people 9, Gap 3. In the table, say projectors and training machines are NOT_ASSESSED because this model has no class for them. Say seats are compared with the peak chair count, and workbenches with the peak dining-table count. The label stays dining table. Point at the person-count bars, then the evidence photo. Read the caption: the analysis id, then “boxes are person, chair, and dining table.”

**One alert, about 40 seconds.** Open Alerts, then the attendance row. Press **Under review**. The status pill changes to Under review. Say this is a review mark on the stored alert, not a new count.

**Close, about 20 seconds.** Return to Dashboard. Say the same privacy lines that are on the page: person, chair, and dining-table boxes only; no facial recognition; no name or biometric record. Say the clip used for the prototype is a synthetic workshop pan on this computer, not a live centre camera, and it is not installed on centre hardware.

## If a judge asks about Analyze

Open Analyze and read the sentence already on the page: `demo/workshop.mp4` is a slow pan of a synthetic workshop photo, not a live centre camera. The three lines are Sample selected, Frames processing, and Alerts stored. Leave the button unpressed unless you are willing to store a new run.

## Do not claim

- An accuracy percentage.
- Facial recognition or a named trainee.
- A live government CCTV connection.
- A detected training machine or projector.
- That 0/3, or any other figure, is a ministry statistic.
