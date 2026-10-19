import sqlite3
from datetime import datetime, timezone
from pathlib import Path
DB=Path(__file__).with_name('incidents.db')
def connect():
    con=sqlite3.connect(DB, timeout=10)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, created_at TEXT, service TEXT, severity TEXT, signal TEXT, details TEXT, status TEXT, decision TEXT, resolution TEXT, verified INTEGER DEFAULT 0)')
    con.execute('CREATE TABLE IF NOT EXISTS runbooks (id INTEGER PRIMARY KEY, incident_id INTEGER, title TEXT, body TEXT, approved INTEGER DEFAULT 0)')
    con.execute('CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY, created_at TEXT, source TEXT, service TEXT, event_type TEXT, evidence TEXT, incident_id INTEGER)')
    con.commit()
    return con
def detect(signal, details):
    t=f'{signal} {details}'.lower()
    if any(x in t for x in ('503','502','service unavailable','outage','ansible task failed','unreachable')):
        return 'high','investigate','Failure signal detected'
    if any(x in t for x in ('cpu','memory','latency','timeout','disk')):
        return 'medium','investigate','Resource or performance signal detected'
    return 'low','request_review','Insufficient evidence for automatic classification'
def record(service,signal,details,source='api',event_type='alert'):
    severity,decision,reason=detect(signal,details)
    con=connect()
    try:
        cur=con.execute('INSERT INTO incidents(created_at,service,severity,signal,details,status,decision,resolution) VALUES(?,?,?,?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),service,severity,signal,details,'open',decision,''))
        iid=cur.lastrowid
        con.execute('INSERT INTO observations(created_at,source,service,event_type,evidence,incident_id) VALUES(?,?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),source,service,event_type,details,iid))
        con.commit()

        # Automatically recall approved runbooks for each new incident.
        # Recall failures must never prevent incident recording.
        recommendations = []
        try:
            from runbook_recall import recall
            recommendations = recall(iid)
        except (sqlite3.Error, ValueError, ImportError) as exc:
            print(f'Runbook recall unavailable for incident #{iid}: {exc}')

        return {
            'incident_id': iid,
            'severity': severity,
            'decision': decision,
            'reason': reason,
            'runbook_matches': len(recommendations)
        }
    finally:con.close()
