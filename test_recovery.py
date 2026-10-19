import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import engine
import monitor
import runbook_recall

with tempfile.TemporaryDirectory() as folder:
    test_db = Path(folder) / "test.db"

    with sqlite3.connect(test_db) as con:
        con.execute("""
            CREATE TABLE recovery_tracking (
                incident_id INTEGER PRIMARY KEY,
                resources TEXT NOT NULL,
                healthy_checks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

    original_engine_db = engine.DB
    original_recall_db = runbook_recall.DB

    engine.DB = test_db
    runbook_recall.DB = test_db

    try:
        limits = {"CPU": 90, "memory": 90, "disk": 90}
        state = {"last_alert": 0, "tracked": {}}

        readings = [
            {"CPU": 95, "memory": 40, "disk": 30},
            {"CPU": 20, "memory": 40, "disk": 30},
            {"CPU": 21, "memory": 40, "disk": 30},
            {"CPU": 19, "memory": 40, "disk": 30},
        ]

        with patch.object(monitor, "sample", side_effect=readings):
            for step in range(4):
                monitor.check(limits, state)

                if step == 1:
                    state = {"last_alert": 0, "tracked": {}}
                    print("SIMULATED MONITOR RESTART")

                with sqlite3.connect(test_db) as con:
                    incident = con.execute(
                        "SELECT id, status, verified FROM incidents"
                    ).fetchone()
                    tracking = con.execute(
                        "SELECT healthy_checks FROM recovery_tracking"
                    ).fetchone()
                    recoveries = con.execute(
                        "SELECT COUNT(*) FROM observations "
                        "WHERE event_type='resource_recovery'"
                    ).fetchone()[0]

                print(
                    f"Step {step + 1}: "
                    f"incident={incident}, "
                    f"tracking={tracking}, "
                    f"recovery_events={recoveries}"
                )

        with sqlite3.connect(test_db) as con:
            status, verified = con.execute(
                "SELECT status, verified FROM incidents"
            ).fetchone()
            remaining = con.execute(
                "SELECT COUNT(*) FROM recovery_tracking"
            ).fetchone()[0]
            recovery_events = con.execute(
                "SELECT COUNT(*) FROM observations "
                "WHERE event_type='resource_recovery'"
            ).fetchone()[0]

        assert status == "recovered"
        assert verified == 0
        assert remaining == 0
        assert recovery_events == 1

        print("PASS: Recovery detected, evidence saved, tracking cleaned.")
        print("PASS: Incident remains unverified.")

    finally:
        engine.DB = original_engine_db
        runbook_recall.DB = original_recall_db
