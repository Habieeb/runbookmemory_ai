import sqlite3
import psutil
from engine import connect as shared_connect
from datetime import datetime, timezone
from pathlib import Path
import streamlit as st

DB = Path(__file__).with_name('incidents.db')
st.set_page_config(page_title='RunbookMemory AI | Incident Intelligence', page_icon='🧠', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif}
.stApp {background: #0b1120; color:#e7edf8}
[data-testid="stSidebar"] {background:#0e192d;border-right:1px solid #23334e}
[data-testid="stHeader"] {background:transparent}
.block-container {max-width:1500px;padding-top:2rem;padding-bottom:4rem}
h1,h2,h3 {letter-spacing:-.035em;color:#f5f8ff!important}
h1 {font-size:2.15rem!important}
[data-testid="stMetric"] {background:#14223a;border:1px solid #273b58;border-radius:15px;padding:20px}
[data-testid="stMetricLabel"] {color:#9fb1ca}
[data-testid="stMetricValue"] {color:#f6faff}
div[data-testid="stForm"],div[data-testid="stExpander"] {background:#121f34;border:1px solid #283b57;border-radius:15px;padding:12px}
.stButton>button[kind="primary"],.stFormSubmitButton>button {background:#347cf7;color:white;border:0;border-radius:9px;font-weight:700}
.stButton>button {border-radius:9px}
[data-testid="stAlert"] {border-radius:12px}
.smallcaps {font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#79aaff;font-weight:800}
.hero {background:linear-gradient(115deg,#172c51,#122039 70%);border:1px solid #304d79;padding:27px 30px;border-radius:20px;margin-bottom:20px}
.hero h2 {font-size:28px;margin:6px 0 9px;color:white}
.hero p {color:#aebfda;margin:0;max-width:760px}
.chip {display:inline-block;border:1px solid #315b89;color:#a7d4ff;background:#153150;padding:5px 10px;border-radius:30px;font-size:12px;margin:4px 6px 4px 0}
.step {border-left:3px solid #448bff;padding:12px 17px;background:#14233c;border-radius:0 12px 12px 0;margin-bottom:12px}
.step b {color:#f0f5ff}
.step small {color:#9fb4cf}
.note {color:#9eb2cf;font-size:13px}


/* Improve text visibility throughout the dashboard */
[data-testid="stSidebar"] {
    color: #f1f5f9 !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small {
    color: #e2e8f0 !important;
}

/* Sidebar navigation */
[data-testid="stSidebar"] [role="radiogroup"] label,
[data-testid="stSidebar"] [role="radiogroup"] label p {
    color: #f8fafc !important;
}

/* General text */
.stApp p,
.stApp label {
    color: #cbd5e1;
}

/* Main headings */
.stApp h1,
.stApp h2,
.stApp h3 {
    color: #f8fafc !important;
}

/* Input labels */
[data-testid="stWidgetLabel"] p {
    color: #e2e8f0 !important;
}

/* Disabled elements */
.stApp [disabled] {
    opacity: 0.65;
}
</style>''', unsafe_allow_html=True)

def connection():
    return shared_connect()

def detect(signal,details):
    t=f'{signal} {details}'.lower()
    if any(x in t for x in ('503','502','service unavailable','outage')):return 'high','investigate','Availability failure signal detected'
    if any(x in t for x in ('cpu','memory','latency','timeout')):return 'medium','investigate','Performance degradation signal detected'
    return 'low','request_review','Insufficient evidence for automatic incident classification'

con=connection()
incidents=con.execute('SELECT id,service,severity,signal,details,status,decision,resolution,verified FROM incidents ORDER BY id DESC LIMIT 5').fetchall()
books=con.execute('SELECT id,incident_id,title,body,approved FROM runbooks ORDER BY id DESC').fetchall()

with st.sidebar:
    st.markdown('## 🧠 RunbookMemory')
    st.caption('INCIDENT INTELLIGENCE · LOCAL LAB')
    st.divider()
    page=st.radio('WORKSPACE',['Overview','Live monitoring','Detect incident','Incident memory','Review queue','Runbooks'],label_visibility='collapsed')
    st.divider()
    st.markdown('**SYSTEM STATUS**')
    st.success('● Local engine online')
    st.caption('Storage: SQLite · AWS Bedrock status check enabled')
    import requests

    try:
        response = requests.get(
            'http://127.0.0.1:8070/health',
            timeout=2
        )
        response.raise_for_status()
        st.success('Decider 2B: server online')
        st.caption('Real model inference available · CPU')
    except requests.RequestException:
        st.warning('Decider 2B: server offline')
        st.caption('Start the Decider server on port 8070')
    from bedrock_status import check_bedrock
    bedrock = check_bedrock()

    if bedrock["connected"]:
        st.info("Bedrock: AWS access verified")
        st.caption("AI inference: quota blocked")
    else:
        st.error(bedrock["message"])
    st.divider()
    st.caption('Prototype · Rule-based decisions only')

st.markdown('<div class="smallcaps">OPERATIONS / INCIDENT MEMORY</div>',unsafe_allow_html=True)
st.title('Incident intelligence workspace')
st.caption('Detect signals · preserve evidence · verify fixes · build reusable runbooks')

if page=='Overview':
    st.markdown('''<div class="hero"><span class="smallcaps">RUNBOOKMEMORY AI</span><h2>From incidents to institutional memory.</h2><p>Capture what happened, why a fix worked, and what to verify before using that knowledge again. Start with a simulated alert to explore the complete local workflow.</p><div style="margin-top:15px"><span class="chip">● Local-first</span><span class="chip">Evidence-led</span><span class="chip">Human-approved runbooks</span></div></div>''',unsafe_allow_html=True)
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    total_30d = con.execute(
        'SELECT COUNT(*) FROM incidents WHERE created_at >= ?',
        (cutoff,)
    ).fetchone()[0]

    active_30d = con.execute(
        "SELECT COUNT(*) FROM incidents WHERE created_at >= ? AND status != 'resolved'",
        (cutoff,)
    ).fetchone()[0]

    verified_30d = con.execute(
        'SELECT COUNT(*) FROM incidents WHERE created_at >= ? AND verified = 1',
        (cutoff,)
    ).fetchone()[0]

    review_table_exists = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='review_tasks'"
    ).fetchone()

    pending_reviews = (
        con.execute(
            "SELECT COUNT(*) FROM review_tasks WHERE status='pending'"
        ).fetchone()[0]
        if review_table_exists else 0
    )

    c1,c2,c3,c4=st.columns(4)
    c1.metric('Incidents · 30 days', total_30d)
    c2.metric('Active · 30 days', active_30d)
    c3.metric('Verified · 30 days', verified_30d)
    c4.metric('Pending reviews', pending_reviews)
    left,right=st.columns([1.5,1],gap='large')
    with left:
        st.subheader('Recent incidents')
        if not incidents:st.info('No incidents recorded yet. Open Detect incident to create one.')
        for r in incidents[:5]:
            st.markdown(f'**#{r[0]} · {r[1]}**  — {r[3]}  \n\n`{r[2].upper()}` · `{r[5].upper()}` · Decision: `{r[6]}`')
            st.divider()
    with right:
        st.subheader('Agent workflow')
        for a,b in [('01  Detect','Receive an alert and classify its signal'),('02  Decide','Choose investigate or request review'),('03  Capture','Record investigation and resolution'),('04  Verify','Engineer confirms the fix worked'),('05  Remember','Draft and approve reusable runbook')]:
            st.markdown(f'<div class="step"><b>{a}</b><br><small>{b}</small></div>',unsafe_allow_html=True)
        st.caption('The current routing is deterministic, not AI inference.')

elif page=='Live monitoring':
    st.subheader('WSL system monitoring')
    st.caption('Live snapshot of the Linux environment running this app. To create incidents automatically, run monitor.py separately.')
    cpu=psutil.cpu_percent(interval=0.3)
    memory=psutil.virtual_memory().percent
    disk=psutil.disk_usage('/').percent
    x,y,z=st.columns(3)
    x.metric('CPU',f'{cpu:.1f}%')
    y.metric('Memory',f'{memory:.1f}%')
    z.metric('Root disk',f'{disk:.1f}%')
    st.info('Automatic alerting runs in a separate WSL terminal: python monitor.py --interval 30')
    if st.button('Refresh metrics'):st.rerun()
    st.subheader('Recent ingested events')
    rows=con.execute('SELECT created_at,source,service,event_type,evidence,incident_id FROM observations ORDER BY id DESC LIMIT 20').fetchall()
    if not rows:st.caption('No monitoring or API events yet.')
    for when,source,service,event_type,evidence,iid in rows:
        with st.expander(f'{when[:19]} · {source} · {service} · #{iid}'):
            st.write(event_type)
            st.code(evidence)

elif page=='Detect incident':
    st.subheader('New incident signal')
    st.caption('Simulate a monitoring alert. The local engine classifies the signal and records its decision.')
    a,b=st.columns([1.45,1],gap='large')
    with a:
        with st.form('alert',clear_on_submit=False):
            service=st.text_input('Affected service','checkout-api')
            signal=st.selectbox('Alert type',['HTTP 503 Service Unavailable','High CPU utilization','Latency increase','Informational event'])
            details=st.text_area('Evidence / log excerpt','HTTP 503 errors increased after deployment v3.0',height=180)
            submit=st.form_submit_button('⚡ Detect and record incident',use_container_width=True)
        if submit:
            if not service.strip() or not details.strip():st.error('Provide a service and evidence to continue.')
            else:
                severity,decision,reason=detect(signal,details)
                cur=con.execute('INSERT INTO incidents(created_at,service,severity,signal,details,status,decision,resolution) VALUES(?,?,?,?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),service.strip(),severity,signal,details,'open',decision,''))
                con.commit()
                st.success(f'Incident #{cur.lastrowid} recorded · {severity.upper()} · {decision}')
                st.info(f'Decision explanation: {reason}. This is a rule-based prototype, not Strands Decider 2B.')
    with b:
        st.subheader('Decision pipeline')
        for x,y in [('Signal ingestion','Alert + service + log evidence'),('Classification','Severity from transparent local rules'),('Decision routing','Investigate or request review'),('Incident memory','Persist event and decision in SQLite')]:
            st.markdown(f'<div class="step"><b>{x}</b><br><small>{y}</small></div>',unsafe_allow_html=True)
        st.warning('Hackathon integration pending: actual Strands Decider 2B decision and Amazon Bedrock generation.')

elif page=='Incident memory':
    st.subheader('Incident memory')
    st.caption('Search historical incidents. Showing 20 records per page.')

    from datetime import datetime, timezone, timedelta

    search = st.text_input(
        'Search incidents',
        placeholder='Search by service, signal, or evidence...'
    )

    f1, f2, f3 = st.columns(3)

    with f1:
        period = st.selectbox(
            'Time range',
            ['Last 24 hours', 'Last 7 days', 'Last 30 days', 'All time'],
            index=2
        )

    with f2:
        severity_filter = st.selectbox(
            'Severity',
            ['All', 'High', 'Medium', 'Low']
        )

    with f3:
        status_filter = st.selectbox(
            'Status',
            ['All', 'Open', 'Investigating', 'Resolved']
        )

    conditions = []
    params = []

    if search.strip():
        conditions.append(
            '(service LIKE ? OR signal LIKE ? OR details LIKE ?)'
        )
        term = f'%{search.strip()}%'
        params.extend([term, term, term])

    if severity_filter != 'All':
        conditions.append('LOWER(severity) = ?')
        params.append(severity_filter.lower())

    if status_filter != 'All':
        conditions.append('LOWER(status) = ?')
        params.append(status_filter.lower())

    days = {
        'Last 24 hours': 1,
        'Last 7 days': 7,
        'Last 30 days': 30
    }

    if period in days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days[period])
        conditions.append('created_at >= ?')
        params.append(cutoff.isoformat())

    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''

    total = con.execute(
        'SELECT COUNT(*) FROM incidents' + where,
        params
    ).fetchone()[0]

    page_size = 20
    total_pages = max(1, (total + page_size - 1) // page_size)

    page_number = st.number_input(
        'Page',
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1
    )

    st.caption(
        f'{total} matching incidents · Page {page_number} of {total_pages}'
    )

    filtered = con.execute(
        'SELECT id,service,severity,signal,details,status,decision,'
        'resolution,verified FROM incidents'
        + where +
        ' ORDER BY id DESC LIMIT ? OFFSET ?',
        params + [page_size, (page_number - 1) * page_size]
    ).fetchall()

    if not filtered:st.info('No matching incidents. Add an alert in Detect incident.')
    for r in filtered:
        iid,service,severity,signal,details,status,decision,resolution,verified=r
        with st.expander(f'#{iid}  ·  {service}  ·  {signal}  ·  {status.upper()}'):
            a,b,c=st.columns(3)
            a.metric('Severity',severity.upper())
            b.metric('Initial rule decision',decision.replace('_',' ').title())
            c.metric('Verified','Yes' if verified else 'No')
            st.markdown('**Agent action history**')
            actions_table = con.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='agent_actions'"
            ).fetchone()

            if actions_table:
                action_rows = con.execute(
                    """SELECT id, created_at, action, status, result
                       FROM agent_actions
                       WHERE incident_id=?
                       ORDER BY id DESC LIMIT 10""",
                    (iid,)
                ).fetchall()

                if action_rows:
                    import json
                    for action_id, created_at, action, status, raw in action_rows:
                        with st.expander(
                            f"Action #{action_id} · {action} · {status}"
                        ):
                            st.caption(created_at)
                            try:
                                st.json(json.loads(raw))
                            except (ValueError, TypeError):
                                st.code(raw, language="text")

                else:
                    st.caption("No agent actions recorded yet.")
            else:
                st.caption("No agent actions recorded yet.")

            pending_investigations = con.execute(
                """SELECT id FROM agent_actions
                   WHERE incident_id=? AND action='investigate'
                   AND status='pending' ORDER BY id DESC""",
                (iid,)
            ).fetchall()

            if pending_investigations:
                st.markdown("**Complete pending investigation**")
                session_count = con.execute(
                    "SELECT COUNT(*) FROM cli_sessions WHERE incident_id=?",
                    (iid,)
                ).fetchone()[0]
                st.caption(f"Recorded CLI sessions: {session_count}")

                if session_count:
                    for (pending_id,) in pending_investigations:
                        with st.form(f"complete_action_{pending_id}"):
                            findings = st.text_area(
                                f"Engineer findings · Action #{pending_id}",
                                key=f"findings_{pending_id}",
                                placeholder="Enter findings supported by the CLI evidence."
                            )
                            submitted = st.form_submit_button(
                                "Complete investigation"
                            )

                        if submitted:
                            from decider_actions import complete_investigation
                            try:
                                complete_investigation(pending_id, findings)
                            except ValueError as exc:
                                st.error(str(exc))
                            else:
                                st.success("Investigation completed. Resolution remains unverified.")
                                st.rerun()
                else:
                    st.info("Record a CLI session before completing the investigation.")

            st.markdown("**AI-generated runbook drafts**")

            draft_table = con.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='runbook_drafts'"
            ).fetchone()

            if draft_table:
                drafts = con.execute(
                    """SELECT id, created_at, body, status
                       FROM runbook_drafts
                       WHERE incident_id=?
                       ORDER BY id DESC LIMIT 3""",
                    (iid,)
                ).fetchall()

                if drafts:
                    for draft_id, created_at, body, draft_status in drafts:
                        with st.expander(
                            f"AI draft #{draft_id} · {draft_status}"
                        ):
                            st.caption(created_at)
                            st.markdown(body)
                            st.warning(
                                "AI-generated draft only. "
                                "Remediation has not been verified."
                            )
                else:
                    st.caption("No AI draft available yet.")
            else:
                st.caption("AI drafting has not produced a draft yet.")

            st.markdown("**Recommended runbooks from memory**")

            recall_table = con.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='runbook_recommendations'"
            ).fetchone()

            if recall_table:
                recommendations = con.execute(
                    """SELECT r.id, r.title, r.body, rr.match_reason
                       FROM runbook_recommendations rr
                       JOIN runbooks r ON r.id=rr.runbook_id
                       WHERE rr.incident_id=? AND r.approved=1
                       ORDER BY rr.id DESC LIMIT 5""",
                    (iid,)
                ).fetchall()

                if recommendations:
                    for book_id, title, body, reason in recommendations:
                        with st.expander(f"Suggested runbook #{book_id} · {title}"):
                            st.caption(reason)
                            st.markdown(body)
                            st.info("Review applicability before executing any remediation.")
                else:
                    st.caption("No matching approved runbooks found.")
            else:
                st.caption("No runbook recommendations recorded yet.")

            st.markdown('**Recorded evidence**')
            st.code(details,language=None)

            cli_table_exists = con.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type='table' AND name='cli_sessions'"
            ).fetchone()

            if cli_table_exists:
                cli_rows = con.execute(
                    '''SELECT id, created_at, transcript
                       FROM cli_sessions
                       WHERE incident_id=?
                       ORDER BY id DESC LIMIT 10''',
                    (iid,)
                ).fetchall()

                if cli_rows:
                    st.markdown('**CLI investigation history**')
                    st.caption(
                        'Recorded troubleshooting evidence. '
                        'Not an automatically verified resolution.'
                    )

                    for session_id, recorded_at, transcript in cli_rows:
                        with st.expander(
                            f'Terminal session #{session_id} · {recorded_at}'
                        ):
                            st.code(transcript, language='text')


            if st.button('Run Strands Decider 2B', key=f'decider_{iid}'):
                from decider_client import decide
                with st.spinner('Running real Decider 2B inference on CPU...'):
                    try:
                        decide(iid)
                        st.success('Model decision recorded in SQLite.')
                        st.rerun()
                    except Exception as exc:
                        st.error(f'Decider inference failed: {exc}')

            decider_row = con.execute(
                """SELECT action, confidence, probabilities, model, created_at
                   FROM decider_results
                   WHERE incident_id=?
                   ORDER BY id DESC LIMIT 1""",
                (iid,)
            ).fetchone() if con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='decider_results'"
            ).fetchone() else None

            if decider_row:
                action, confidence, probabilities, model, created_at = decider_row
                import json
                st.markdown('**Latest real Decider 2B decision**')
                st.info(f'Action: {action.replace("_", " ").title()}')
                st.caption(f'Model: {model} · {created_at}')
                if confidence is not None:
                    st.metric('Model confidence', f'{confidence:.1%}')
                probs = json.loads(probabilities or '{}')
                st.markdown('**Model action probabilities**')
                for option, probability in sorted(
                    probs.items(),
                    key=lambda item: item[1],
                    reverse=True
                ):
                    st.write(f'{option.replace("_", " ").title()}: {probability:.1%}')
                    st.progress(float(probability))


            if st.button('Analyze with Amazon Bedrock', key=f'bedrock_{iid}'):
                from bedrock_analysis import analyze
                with st.spinner('Analyzing incident with Amazon Bedrock...'):
                    result = analyze(iid)
                st.session_state[f'bedrock_result_{iid}'] = result

            if f'bedrock_result_{iid}' in st.session_state:
                st.markdown('**Bedrock incident analysis**')
                result = st.session_state[f'bedrock_result_{iid}']
                if result.startswith('Bedrock inference unavailable:'):
                    st.warning(result)
                else:
                    st.markdown(result)


            with st.form(f'resolve_{iid}'):
                fix=st.text_area('Troubleshooting steps / resolution',value=resolution or '',key=f'fix_{iid}')
                proof=st.checkbox('I verified that this resolution worked',value=bool(verified),key=f'proof_{iid}')
                save=st.form_submit_button('Save investigation')
            if save:
                con.execute('UPDATE incidents SET resolution=?,verified=?,status=? WHERE id=?',(fix,int(proof),'resolved' if proof and fix.strip() else 'investigating',iid))
                con.commit();st.success('Investigation saved.');st.rerun()
            if verified and resolution and st.button('Create runbook draft',key=f'draft_{iid}'):
                title=f'{service}: {signal}'
                body=f'# {title}\n\n## Incident signal\n{signal}\n\n## Environment / evidence\n{details}\n\n## Verified resolution\n{resolution}\n\n## Verification\nEngineer confirmed the resolution.\n\n## Reuse caution\nCheck versions, dependencies, and environment before applying this fix.\n'
                con.execute('INSERT INTO runbooks(incident_id,title,body) VALUES(?,?,?)',(iid,title,body))
                con.commit();st.success('Runbook draft created.');st.rerun()

elif page=='Review queue':
    st.subheader('Human review queue')
    st.caption(
        'Incidents escalated for engineer review. '
        'No remediation is executed automatically.'
    )

    con.execute('''
        CREATE TABLE IF NOT EXISTS review_tasks (
            id INTEGER PRIMARY KEY,
            incident_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            reason TEXT NOT NULL
        )
    ''')
    con.commit()

    review_filter = st.selectbox(
        'Review status',
        ['Pending', 'Completed', 'All'],
        key='review_status_filter'
    )

    review_where = {
        'Pending': "WHERE rt.status='pending'",
        'Completed': "WHERE rt.status='completed'",
        'All': ''
    }[review_filter]

    review_total = con.execute(
        'SELECT COUNT(*) FROM review_tasks rt ' + review_where
    ).fetchone()[0]

    st.metric('Matching review tasks', review_total)

    review_rows = con.execute(
        '''
        SELECT rt.id, rt.incident_id, rt.created_at,
               rt.status, rt.reason,
               i.service, i.severity, i.signal, i.details
        FROM review_tasks rt
        LEFT JOIN incidents i ON i.id = rt.incident_id
        '''
        + review_where +
        ' ORDER BY rt.id DESC LIMIT 50'
    ).fetchall()

    if not review_rows:
        st.info('No review tasks match this filter.')

    for task in review_rows:
        (task_id, incident_id, created_at, status, reason,
         service, severity, signal, details) = task

        with st.expander(
            f'Review #{task_id} · Incident #{incident_id} · '
            f'{(service or "Unknown service")} · {status.upper()}'
        ):
            st.markdown(f'**Reason:** {reason}')
            st.caption(f'Created: {created_at}')
            st.write(f'**Severity:** {(severity or "Unknown").upper()}')
            st.write(f'**Signal:** {signal or "Incident unavailable"}')

            st.markdown('**Recorded evidence**')
            st.code(details or 'No evidence available', language=None)

            if status == 'pending':
                if st.button(
                    'Mark reviewed',
                    key=f'complete_review_{task_id}'
                ):
                    con.execute(
                        "UPDATE review_tasks SET status='completed' "
                        "WHERE id=? AND status='pending'",
                        (task_id,)
                    )
                    con.commit()
                    st.success('Review marked complete.')
                    st.rerun()

else:
    st.subheader('Knowledge base / runbooks')
    st.caption('Only engineer-verified incidents can become runbook drafts. Approval remains a human action.')
    if not books:st.info('No runbooks yet. Verify a resolution in Incident memory and create a draft.')
    for bid,iid,title,body,approved in books:
        with st.expander(f'{"✅ Approved" if approved else "📝 Draft"}  ·  {title}  ·  Incident #{iid}'):
            st.markdown(body)
            st.download_button('Download Markdown',body,file_name=f'runbook_{bid}.md',key=f'dl_{bid}')
            if not approved and st.button('Approve runbook',key=f'approve_{bid}'):
                con.execute('UPDATE runbooks SET approved=1 WHERE id=?',(bid,))
                con.commit();st.rerun()

con.close()

# Readability improvements for incident input controls
st.markdown("""
<style>
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    color: #111827 !important;
    background-color: #f1f5f9 !important;
}

div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
}

div[data-testid="stTextArea"] textarea {
    caret-color: #111827 !important;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] * {
    color: #111827 !important;
}
</style>
""", unsafe_allow_html=True)

# Keep expander headings readable against light backgrounds.
st.markdown("""
<style>
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary * {
    color: #111827 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stExpander"] summary {
    background: #243650 !important;
    color: #ffffff !important;
}
div[data-testid="stExpander"] summary * {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)
