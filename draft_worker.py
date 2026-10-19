import argparse
import sqlite3
import time

from engine import connect
from runbook_drafts import prepare


def process():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS runbook_drafts (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unverified'
            )
        """)

        rows = con.execute("""
            SELECT i.id
            FROM incidents i
            WHERE i.status='recovered'
              AND EXISTS (
                  SELECT 1 FROM cli_sessions c
                  WHERE c.incident_id=i.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM runbook_drafts d
                  WHERE d.incident_id=i.id
              )
            ORDER BY i.id
            LIMIT 5
        """).fetchall()

    for (incident_id,) in rows:
        with connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS draft_attempts (
                    incident_id INTEGER PRIMARY KEY,
                    last_attempt TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)

            previous = con.execute(
                "SELECT last_attempt FROM draft_attempts WHERE incident_id=?",
                (incident_id,)
            ).fetchone()

            if previous:
                from datetime import datetime, timezone, timedelta
                last = datetime.fromisoformat(previous[0])
                if datetime.now(timezone.utc) - last < timedelta(hours=24):
                    continue

            from datetime import datetime, timezone
            con.execute(
                """INSERT INTO draft_attempts
                   (incident_id,last_attempt,status)
                   VALUES (?,?,'attempting')
                   ON CONFLICT(incident_id) DO UPDATE SET
                   last_attempt=excluded.last_attempt,
                   status=excluded.status""",
                (incident_id, datetime.now(timezone.utc).isoformat())
            )
        try:
            result = prepare(incident_id)
            print(f"Incident #{incident_id}: {result}", flush=True)
        except Exception as exc:
            print(
                f"Incident #{incident_id}: draft error: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=120)
    args = parser.parse_args()

    if args.once:
        process()
    else:
        while True:
            process()
            time.sleep(max(60, args.interval))
