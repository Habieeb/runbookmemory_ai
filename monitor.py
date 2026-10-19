import argparse
import time
from datetime import datetime, timezone

import psutil
from engine import connect, record


def sample():
    return {
        "CPU": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
    }


def check(limits, state):
    values = sample()
    print(
        " ".join(f"{k}={v:.1f}%" for k, v in values.items()),
        flush=True,
    )

    breached = [
        name for name, value in values.items()
        if value >= limits[name]
    ]

    now = time.time()

    # Restore tracked incidents from SQLite on every cycle.
    with connect() as con:
        saved = con.execute(
            "SELECT incident_id, resources, healthy_checks "
            "FROM recovery_tracking"
        ).fetchall()

    state["tracked"] = {
        iid: {
            "resources": set(resources.split(",")),
            "healthy_checks": count,
        }
        for iid, resources, count in saved
    }

    if breached and now - state["last_alert"] >= 300:
        evidence = "; ".join(
            f"{name} {values[name]:.1f}% exceeds {limits[name]}%"
            for name in breached
        )
        result = record(
            "wsl-host",
            "Resource threshold exceeded",
            evidence,
            "wsl-monitor",
            "resource_alert",
        )
        state["last_alert"] = now
        state["tracked"][result["incident_id"]] = {
            "resources": set(breached),
            "healthy_checks": 0,
        }
        with connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO recovery_tracking "
                "(incident_id, resources, healthy_checks, created_at) "
                "VALUES (?, ?, 0, ?)",
                (
                    result["incident_id"],
                    ",".join(breached),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        print(
            f"Incident #{result['incident_id']} created",
            flush=True,
        )

    for incident_id, tracked in list(state["tracked"].items()):
        healthy = all(
            values[name] < limits[name]
            for name in tracked["resources"]
        )

        tracked["healthy_checks"] = (
            tracked["healthy_checks"] + 1 if healthy else 0
        )

        with connect() as con:
            con.execute(
                "UPDATE recovery_tracking SET healthy_checks=? "
                "WHERE incident_id=?",
                (tracked["healthy_checks"], incident_id),
            )

        if tracked["healthy_checks"] < 3:
            continue

        evidence = "; ".join(
            f"{name}={values[name]:.1f}%"
            for name in tracked["resources"]
        )

        with connect() as con:
            cursor = con.execute(
                """UPDATE incidents
                   SET status='recovered'
                   WHERE id=? AND status='open'
                     AND verified=0""",
                (incident_id,),
            )

            if cursor.rowcount:
                con.execute(
                    """INSERT INTO observations
                       (created_at, source, service,
                        event_type, evidence, incident_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        "wsl-monitor",
                        "wsl-host",
                        "resource_recovery",
                        evidence,
                        incident_id,
                    ),
                )
                print(
                    f"Incident #{incident_id} recovered: {evidence}",
                    flush=True,
                )

            con.execute(
                "DELETE FROM recovery_tracking WHERE incident_id=?",
                (incident_id,),
            )

        del state["tracked"][incident_id]

    return bool(breached)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--cpu", type=float, default=90)
    parser.add_argument("--memory", type=float, default=90)
    parser.add_argument("--disk", type=float, default=90)
    args = parser.parse_args()

    limits = {
        "CPU": args.cpu,
        "memory": args.memory,
        "disk": args.disk,
    }

    state = {
        "last_alert": 0,
        "tracked": {},
    }

    if args.once:
        check(limits, state)
    else:
        while True:
            check(limits, state)
            time.sleep(max(5, args.interval))
