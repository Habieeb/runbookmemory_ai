import argparse
import os
import re
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "incidents.db"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start"])
    parser.add_argument("--incident", type=int, required=True)
    args = parser.parse_args()

    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT id FROM incidents WHERE id=?",
            (args.incident,)
        ).fetchone()

    if not row:
        raise SystemExit("Incident not found.")

    with tempfile.TemporaryDirectory() as folder:
        raw = Path(folder) / "session.log"
        os.chmod(folder, 0o700)

        print(f"Recording incident #{args.incident}.")
        print("Use only non-sensitive diagnostic commands.")
        print("Type exit to finish recording.")

        subprocess.run(
            ["script", "-q", "-c", "/bin/bash --noprofile --norc", str(raw)],
            check=False
        )

        transcript = raw.read_text(errors="replace")
        transcript = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", transcript)
        transcript = re.sub(
            r"(?i)(password|token|api[_-]?key|secret)\s*[=:]\s*\S+",
            r"\1=[REDACTED]",
            transcript
        )

    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS cli_sessions (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                transcript TEXT NOT NULL
            )
        """)
        con.execute(
            "INSERT INTO cli_sessions (incident_id,created_at,transcript) "
            "VALUES (?,?,?)",
            (
                args.incident,
                datetime.now(timezone.utc).isoformat(),
                transcript[:100000]
            )
        )
        con.commit()

    print(f"Investigation saved for incident #{args.incident}.")

if __name__ == "__main__":
    main()
