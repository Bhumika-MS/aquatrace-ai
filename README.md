# AquaTrace AI — Smart Campus Water Intelligence

A beginner-friendly hackathon prototype that demonstrates how a campus could review water-meter readings, spot unusual consumption, and prioritize zones for human inspection.

> **Prototype transparency:** The initial readings are synthetic demonstration data. The anomaly/risk score is a transparent statistical heuristic, not a trained or validated machine-learning model, not a probability of a leak, and not proof that a leak exists. The app does not connect to real sensors or locate a physical leak. Validate with real meter data and on-site inspection before making operational decisions.

## Features

- Dashboard summarizing latest water usage across campus zones.
- Zone-level comparison of the latest reading against up to six prior readings.
- Flags material increases for review and ranks them with an explainable prototype risk score.
- Form to add a reading locally and recalculate the dashboard.
- CSV export of zone analysis.
- Local SQLite storage; no paid AI API, external database, sensor hardware, or hosting required to run the demo.
- `/health` endpoint for a quick local check.

## Technology

- Python 3.11+
- Flask
- SQLite (Python standard library)
- HTML, CSS and JavaScript

## Run on Windows

1. Install Python and make sure the `py` command works.
2. Open this folder in VS Code.
3. In the VS Code terminal, create and activate a virtual environment (recommended):

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`, or skip the virtual environment and use `py -m pip install -r requirements.txt`.

4. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   py app.py
   ```

6. Open `http://127.0.0.1:5000` in Chrome.
7. Add a test reading, check how the zone analysis changes, and use **Export CSV** to download a report.
8. Check `http://127.0.0.1:5000/health` for a small JSON status response.

The first launch creates `instance/aquatrace.db` and seeds the dashboard with synthetic readings. This local database is intentionally ignored by Git. If you wish to reset the demo, stop the app, delete `instance/aquatrace.db`, and run `py app.py` again; a fresh synthetic dataset will be created.

## How the demo score works

For each zone, the app compares the newest reading against up to six previous readings. It calculates the percentage change, a standardized deviation, and a bounded 0–100 **prototype risk score**. A zone is flagged when the change is at least 20% and its score is at least 30. These thresholds are illustrative and should be tuned only after testing on representative real data.

“Estimated excess” is simply the latest reading minus the recent baseline average for a flagged zone. It is not confirmed water loss. Higher usage can also arise from occupancy, cleaning, weather, or scheduled activity.

## Suggested next improvements (after organizer approval / during the build period)

- Import a well-documented CSV from an approved real or open dataset.
- Add uncertainty and false-positive analysis using held-out test data.
- Compare the transparent heuristic with a trained anomaly-detection model if data and time permit.
- Add meter metadata and an editable simplified campus zone map.
- Add authentication and production-grade configuration before any public deployment.

## Repository structure

```text
aquatrace-ai/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── app.js
└── instance/           # local database created at runtime; do not upload
```

## Safety and limitations

This is an educational prototype for a hackathon demonstration, not a certified leak-detection system. It does not control valves or other physical equipment. Do not place personal, confidential, or operationally sensitive data into a public repository. Set a strong secret key and use a production server before any real deployment.
