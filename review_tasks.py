import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).with_name("incidents.db")

def create_review_task(incident_id):
    with sqlite3.connect(DB, timeout=10) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS review_tasks (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reason TEXT NOT NULL
            )
        """)

        incident = con.execute(
            "SELECT id FROM incidents WHERE id=?",
            (incident_id,)
        ).fetchone()

        if not incident:
            raise ValueError("Incident not found")

        existing = con.execute(
            """SELECT id FROM review_tasks
               WHERE incident_id=? AND status='pending'""",
            (incident_id,)
        ).fetchone()

        if existing:
            return existing[0]

        cur = con.execute(
            """INSERT INTO review_tasks
               (incident_id, created_at, status, reason)
               VALUES (?, ?, ?, ?)""",
            (
                incident_id,
                datetime.now(timezone.utc).isoformat(),
                "pending",
                "Strands Decider 2B recommended human review."
            )
        )
        con.commit()
        return cur.lastrowid

if __name__ == "__main__":
    task_id = create_review_task(3)
    print(f"Review task #{task_id} created or already exists")
