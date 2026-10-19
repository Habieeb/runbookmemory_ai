import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).with_name("incidents.db")


def execute(incident_id, action):
    if action not in {"investigate", "search_memory"}:
        raise ValueError(f"Unsupported action: {action}")

    with sqlite3.connect(DB, timeout=10) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS agent_actions (
                id INTEGER PRIMARY KEY,
                incident_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT NOT NULL
            )
        """)

        incident = con.execute(
            "SELECT service, signal FROM incidents WHERE id=?",
            (incident_id,)
        ).fetchone()

        if incident is None:
            raise ValueError(f"Incident #{incident_id} not found")

        service, signal = incident

        if action == "investigate":
            result = {
                "message": "Investigation requested by Strands Decider 2B.",
                "next_step": "Collect diagnostic evidence using the CLI watcher.",
                "verified": False
            }
            status = "pending"

        else:
            from runbook_recall import recall

            matches = recall(incident_id)

            result = {
                "message": "Searched approved runbook memory.",
                "matches": matches,
                "verified": False
            }
            status = "completed"

        cursor = con.execute(
            """
            INSERT INTO agent_actions
            (incident_id, created_at, action, status, result)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                datetime.now(timezone.utc).isoformat(),
                action,
                status,
                json.dumps(result)
            )
        )

        return {
            "action_id": cursor.lastrowid,
            "action": action,
            "status": status,
            "result": result
        }


def complete_investigation(action_id, engineer_notes):
    """Complete an investigation only when CLI evidence exists."""
    notes = engineer_notes.strip()

    if not notes:
        raise ValueError("Engineer findings are required.")

    with sqlite3.connect(DB, timeout=10) as con:
        row = con.execute(
            """SELECT incident_id, action, status, result
               FROM agent_actions WHERE id=?""",
            (action_id,)
        ).fetchone()

        if row is None:
            raise ValueError("Investigation action not found.")

        incident_id, action, status, raw_result = row

        if action != "investigate":
            raise ValueError("Only investigations can be completed.")

        if status != "pending":
            raise ValueError("Investigation is not pending.")

        evidence = con.execute(
            """SELECT id FROM cli_sessions
               WHERE incident_id=?
               ORDER BY id DESC LIMIT 1""",
            (incident_id,)
        ).fetchone()

        if evidence is None:
            raise ValueError(
                "Record a CLI investigation session before completing."
            )

        result = json.loads(raw_result)
        result["engineer_findings"] = notes
        result["cli_session_id"] = evidence[0]
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["verified"] = False

        cursor = con.execute(
            """UPDATE agent_actions
               SET status='completed', result=?
               WHERE id=? AND action='investigate' AND status='pending'""",
            (json.dumps(result), action_id)
        )

        if cursor.rowcount != 1:
            raise ValueError("Investigation status changed. Refresh the page.")

        return {
            "action_id": action_id,
            "incident_id": incident_id,
            "cli_session_id": evidence[0],
            "status": "completed"
        }
