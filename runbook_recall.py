import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).with_name("incidents.db")


def recall(incident_id):
    with sqlite3.connect(DB, timeout=10) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS runbook_recommendations (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                runbook_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                match_reason TEXT NOT NULL,
                UNIQUE(incident_id, runbook_id)
            )
        """)

        incident = con.execute(
            "SELECT service, signal FROM incidents WHERE id=?",
            (incident_id,)
        ).fetchone()

        if not incident:
            raise ValueError(f"Incident #{incident_id} not found")

        service, signal = incident

        matches = con.execute("""
            SELECT r.id, r.title, r.body, i.service, i.signal
            FROM runbooks r
            JOIN incidents i ON i.id = r.incident_id
            WHERE r.approved = 1
              AND r.incident_id != ?
              AND i.service = ?
              AND i.signal = ?
            ORDER BY r.id DESC
            LIMIT 5
        """, (incident_id, service, signal)).fetchall()

        recommendations = []

        for runbook_id, title, body, _, _ in matches:
            reason = "Same service and incident signal as a verified runbook"

            con.execute("""
                INSERT OR IGNORE INTO runbook_recommendations
                (incident_id, runbook_id, created_at, match_reason)
                VALUES (?, ?, ?, ?)
            """, (
                incident_id,
                runbook_id,
                datetime.now(timezone.utc).isoformat(),
                reason
            ))

            recommendations.append({
                "runbook_id": runbook_id,
                "title": title,
                "body": body,
                "match_reason": reason
            })

        return recommendations


if __name__ == "__main__":
    import sys
    matches = recall(int(sys.argv[1]))
    print(f"Found {len(matches)} approved matching runbooks")
    for item in matches:
        print(item["runbook_id"], item["title"])
