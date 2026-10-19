from __future__ import annotations

import csv
import io
import math
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, pstdev

from flask import Flask, flash, make_response, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DB_PATH = INSTANCE_DIR / "aquatrace.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "local-demo-key-change-before-deployment"
app.config["DATABASE"] = str(DB_PATH)

# Synthetic readings used only to demonstrate the prototype. Values are litres/day.
DEMO_READINGS = {
    "Hostel Block A": [18500, 18900, 18700, 19100, 18600, 18800, 28600],
    "Canteen": [9200, 9500, 9100, 9300, 9400, 9250, 13100],
    "Sports Complex": [4800, 4700, 4900, 4650, 4800, 4750, 7250],
    "Academic Block": [11000, 10850, 11200, 11100, 10900, 11050, 11400],
    "Lab Wing": [6400, 6500, 6300, 6450, 6350, 6420, 6500],
    "Library": [3200, 3100, 3250, 3180, 3220, 3200, 3280],
}

ZONE_NOTES = {
    "Hostel Block A": "High occupancy zone; inspect visible plumbing and tank overflow first.",
    "Canteen": "Check cleaning schedules, taps, and kitchen supply lines.",
    "Sports Complex": "Inspect washrooms, showers, and outdoor taps.",
    "Academic Block": "Compare usage with class schedules and maintenance activity.",
    "Lab Wing": "Check meter consistency and scheduled lab activity.",
    "Library": "Low recent variation; continue routine monitoring.",
}


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_db() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone TEXT NOT NULL,
                usage_liters REAL NOT NULL CHECK(usage_liters >= 0),
                recorded_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'demo'
            )"""
        )
        count = db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        if count == 0:
            today = date.today()
            rows = []
            for zone, values in DEMO_READINGS.items():
                for index, liters in enumerate(values):
                    recorded_day = today - timedelta(days=6 - index)
                    # The demo's current-day sample is deliberately timestamped in the morning,
                    # so a user-added reading later today becomes the newest reading.
                    recorded_at = datetime.combine(recorded_day, datetime.min.time()).replace(hour=8).isoformat(timespec="seconds")
                    rows.append((zone, float(liters), recorded_at, "simulated"))
            db.executemany(
                "INSERT INTO readings (zone, usage_liters, recorded_at, source) VALUES (?, ?, ?, ?)",
                rows,
            )


def analyze_zone(zone: str, rows: list[sqlite3.Row]) -> dict:
    # rows are sorted from oldest to newest. Compare the newest reading against up to
    # six prior readings. This is a transparent demo heuristic, not a calibrated ML model.
    if len(rows) >= 2:
        baseline_rows = rows[:-1][-6:]
        baseline_values = [float(row["usage_liters"]) for row in baseline_rows]
        current = float(rows[-1]["usage_liters"])
        baseline = mean(baseline_values)
        spread = pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
        safe_spread = max(spread, baseline * 0.03, 1.0)
        z_score = (current - baseline) / safe_spread
        percent_change = ((current - baseline) / baseline * 100.0) if baseline > 0 else 0.0
        excess = max(0.0, current - baseline)
        score = min(100.0, max(0.0, 0.75 * max(percent_change, 0.0) + 25.0 * min(max(z_score, 0.0) / 4.0, 1.0)))
    else:
        current = float(rows[-1]["usage_liters"])
        baseline = current
        percent_change = 0.0
        excess = 0.0
        score = 0.0

    if score >= 60:
        level = "High"
        action = "Inspect soon"
    elif score >= 30:
        level = "Medium"
        action = "Review meter / inspect"
    else:
        level = "Low"
        action = "Continue monitoring"

    # Require a material increase as well as a score to flag a zone.
    flagged = percent_change >= 20 and score >= 30
    return {
        "zone": zone,
        "latest": current,
        "baseline": baseline,
        "percent_change": percent_change,
        "excess": excess if flagged else 0.0,
        "score": score,
        "level": level,
        "flagged": flagged,
        "action": action,
        "note": ZONE_NOTES.get(zone, "Review the meter and compare against normal activity."),
        "latest_at": rows[-1]["recorded_at"],
    }


def load_dashboard_data() -> dict:
    with get_db() as db:
        zone_rows = db.execute("SELECT DISTINCT zone FROM readings ORDER BY zone").fetchall()
        zones = [row["zone"] for row in zone_rows]
        readings_by_zone: dict[str, list[sqlite3.Row]] = {}
        for zone in zones:
            rows = db.execute(
                "SELECT * FROM readings WHERE zone = ? ORDER BY recorded_at ASC, id ASC",
                (zone,),
            ).fetchall()
            readings_by_zone[zone] = rows

        analysis = [analyze_zone(zone, readings_by_zone[zone]) for zone in zones]
        analysis.sort(key=lambda item: (not item["flagged"], -item["score"], -item["excess"]))

        # Daily chart shows one reading per zone per date (the latest entry for that
        # date), so adding a correction does not double-count a zone's daily usage.
        latest_by_zone_day: dict[tuple[str, str], sqlite3.Row] = {}
        for zone, rows in readings_by_zone.items():
            for row in rows:
                day = row["recorded_at"][:10]
                key = (zone, day)
                prior = latest_by_zone_day.get(key)
                if prior is None or (row["recorded_at"], row["id"]) > (prior["recorded_at"], prior["id"]):
                    latest_by_zone_day[key] = row
        day_map: dict[str, float] = {}
        for (_, day), row in latest_by_zone_day.items():
            day_map[day] = day_map.get(day, 0.0) + float(row["usage_liters"])
        last_days = [(date.today() - timedelta(days=offset)) for offset in reversed(range(7))]
        chart = []
        for day in last_days:
            iso = day.isoformat()
            chart.append({"day": day.strftime("%a"), "date": iso, "total": day_map.get(iso, 0.0)})
        # If additional readings are entered for the same day, today's aggregate includes them.
        max_total = max((item["total"] for item in chart), default=1.0) or 1.0
        for item in chart:
            item["height"] = max(8, int(item["total"] / max_total * 100))

        total_latest = sum(item["latest"] for item in analysis)
        flagged = [item for item in analysis if item["flagged"]]
        total_excess = sum(item["excess"] for item in flagged)
        all_readings = sum(len(rows) for rows in readings_by_zone.values())

        return {
            "zones": analysis,
            "zone_names": zones,
            "total_latest": total_latest,
            "flagged_count": len(flagged),
            "total_excess": total_excess,
            "all_readings": all_readings,
            "chart": chart,
            "max_total": max_total,
            "last_updated": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        }


@app.route("/")
def dashboard():
    data = load_dashboard_data()
    return render_template("index.html", data=data)


@app.route("/readings", methods=["POST"])
def add_reading():
    zone = request.form.get("zone", "").strip()
    usage_text = request.form.get("usage_liters", "").strip()
    try:
        usage = float(usage_text)
    except ValueError:
        flash("Enter a valid numeric meter reading.", "error")
        return redirect(url_for("dashboard"))

    if not zone:
        flash("Choose a zone before adding a reading.", "error")
    elif not math.isfinite(usage) or usage <= 0 or usage > 100_000_000:
        flash("Reading must be a positive number below 100,000,000 litres.", "error")
    else:
        with get_db() as db:
            exists = db.execute("SELECT 1 FROM readings WHERE zone = ? LIMIT 1", (zone,)).fetchone()
            if not exists:
                flash("Choose one of the listed campus zones.", "error")
                return redirect(url_for("dashboard"))
            timestamp = datetime.now().isoformat(timespec="seconds")
            db.execute(
                "INSERT INTO readings (zone, usage_liters, recorded_at, source) VALUES (?, ?, ?, ?)",
                (zone, usage, timestamp, "user-entered"),
            )
        flash(f"New reading saved for {zone}. The dashboard has been recalculated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/export.csv")
def export_csv():
    data = load_dashboard_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "zone", "latest_reading_liters", "baseline_average_liters", "change_percent",
        "estimated_excess_liters", "prototype_risk_score", "risk_level", "flagged_for_review",
        "suggested_action", "latest_reading_timestamp",
    ])
    for item in data["zones"]:
        writer.writerow([
            item["zone"], round(item["latest"], 2), round(item["baseline"], 2),
            round(item["percent_change"], 2), round(item["excess"], 2), round(item["score"], 1),
            item["level"], "yes" if item["flagged"] else "no", item["action"], item["latest_at"],
        ])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=aquatrace-zone-report.csv"
    return response


@app.route("/health")
def health():
    return {"status": "ok", "app": "AquaTrace AI prototype", "data": "synthetic demo + locally entered readings"}


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
else:
    # Also initialize when loaded by an application server or Flask test client.
    init_db()
