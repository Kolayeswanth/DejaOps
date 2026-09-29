"""DejaOps — operational intelligence workspace."""
import html
import json
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from agent import triage, record_outcome, learned_summary
from memory import BANK_ID

try:
    from agent import looks_like_alert
except ImportError:
    looks_like_alert = lambda text: len((text or "").split()) >= 3

try:
    from memory import retain_postmortem
except ImportError:
    retain_postmortem = None

try:
    from brain_graph import render_brain_page
except ImportError:
    render_brain_page = None

st.set_page_config(page_title="DejaOps", page_icon=None, layout="wide", initial_sidebar_state="collapsed")


def esc(value):
    return html.escape(str(value or ""))


def md(value):
    st.markdown(value, unsafe_allow_html=True)


st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,600;1,700&family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#07090d;--line:rgba(255,255,255,.075);--text:#eef2f7;--muted:#8d98a8;--subtle:#5e6978;--accent:#8b7cff;--accent-2:#42b7f4;--success:#45d39c;--warning:#eab95a;--danger:#f26f86}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:var(--text)}
.stApp{background:radial-gradient(900px 500px at 0% -10%,rgba(139,124,255,.12),transparent 68%),radial-gradient(800px 460px at 100% 0%,rgba(66,183,244,.08),transparent 66%),var(--bg)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background-image:linear-gradient(rgba(255,255,255,.016) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.016) 1px,transparent 1px);background-size:64px 64px;mask-image:linear-gradient(to bottom,#000,transparent 72%)}
#MainMenu,footer,[data-testid="stDecoration"],.stAppDeployButton{display:none!important} header{background:transparent!important}.block-container{max-width:1500px;padding:1rem 2.5rem 3.5rem}
.masthead{text-align:center;padding:4px 0 20px}.masthead-title{font-size:clamp(3.4rem,7vw,6.4rem);line-height:.85;letter-spacing:-.06em;white-space:nowrap}.masthead-title em{font:italic 700 1.08em/1 'Cormorant Garamond',serif;color:#b9b0ff}.masthead-title strong{font:700 .82em/1 'Space Grotesk',sans-serif;color:#eef2f7}
.topbar{display:flex;align-items:center;gap:24px;min-height:66px;padding:8px 12px 8px 16px;margin-bottom:16px;border:1px solid var(--line);border-radius:18px;background:rgba(9,12,17,.84);backdrop-filter:blur(24px);box-shadow:0 18px 55px rgba(0,0,0,.18)}
.brand{display:flex;align-items:center;gap:12px;min-width:245px}.brand-mark{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--accent-2));box-shadow:0 8px 26px rgba(91,91,220,.25);font:700 12px 'Space Grotesk';color:#fff;letter-spacing:-.03em}.brand-name{font:700 18px 'Space Grotesk';letter-spacing:-.025em}.brand-sub{font-size:10px;color:var(--muted);margin-top:2px}.nav-caption{font-size:10px;color:var(--subtle);text-transform:uppercase;letter-spacing:.12em;margin-left:auto}.status{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:11px;white-space:nowrap}.status-dot{width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 0 5px rgba(69,211,156,.08)}
.stButton>button{min-height:40px;border-radius:11px!important;border:1px solid var(--line)!important;background:rgba(255,255,255,.025)!important;color:var(--text)!important;font-weight:600!important;transition:transform .2s ease,border-color .2s ease,background .2s ease,box-shadow .2s ease}.stButton>button:hover{transform:translateY(-1px);border-color:rgba(139,124,255,.45)!important;background:rgba(139,124,255,.07)!important;box-shadow:0 10px 28px rgba(0,0,0,.2)}.stButton>button[kind="primary"]{border:0!important;color:#fff!important;background:linear-gradient(110deg,#7568ef,#36aee6)!important;box-shadow:0 12px 32px rgba(87,103,235,.22)}
[data-baseweb="select"]>div,[data-baseweb="textarea"],[data-testid="stTextArea"] textarea{background:rgba(255,255,255,.025)!important;border:1px solid var(--line)!important;border-radius:13px!important;color:var(--text)!important}[data-testid="stTextArea"] textarea{min-height:126px}label{color:var(--muted)!important;font-size:11px!important;font-weight:600!important}
.eyebrow{color:#9e95ff;font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;margin-bottom:10px}.hero-title{font:700 clamp(2.3rem,4.7vw,4.4rem)/.98 'Space Grotesk';letter-spacing:-.025em;word-spacing:.12em;max-width:980px;margin:0}.hero-title span{color:#9b91ff}.hero-copy{color:var(--muted);font-size:15px;line-height:1.75;max-width:760px;margin:16px 0 0}.page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:28px;margin-bottom:30px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0 30px}.metric{padding:20px 21px;min-height:112px}.metric-value{font:600 30px 'Space Grotesk';letter-spacing:-.045em}.metric-label{color:var(--muted);font-size:11px;margin-top:5px}.metric-meta{color:var(--subtle);font-size:10px;margin-top:13px;line-height:1.45}.panel{background:linear-gradient(145deg,rgba(16,21,29,.96),rgba(10,13,18,.93));border:1px solid var(--line);border-radius:20px;box-shadow:0 22px 70px rgba(0,0,0,.17)}.panel-pad{padding:24px}.panel-accent{border-color:rgba(139,124,255,.3);box-shadow:0 24px 75px rgba(83,72,185,.09)}
.section-title{font:600 19px 'Space Grotesk';letter-spacing:-.025em}.section-title .title-mark{border-bottom:2px solid #8b7cff;padding-bottom:2px}.section-copy{color:var(--muted);font-size:12px;line-height:1.6;margin-top:5px}.composer{padding:24px;margin-top:26px}.composer-head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:18px}.composer-title{font:600 18px 'Space Grotesk'}.composer-note{color:var(--muted);font-size:12px;margin-top:4px}.pill{display:inline-flex;align-items:center;border:1px solid var(--line);color:var(--muted);padding:5px 9px;border-radius:999px;font-size:9px;font-weight:700;letter-spacing:.07em;text-transform:uppercase}.pill.accent{color:#ddd9ff;border-color:rgba(139,124,255,.3);background:rgba(139,124,255,.08)}
.mvp-intro{margin:34px 0 14px;max-width:820px}.mvp-intro .section-copy{font-size:13px;line-height:1.8}.mvp-underline{text-decoration:underline;text-decoration-color:#8b7cff;text-decoration-thickness:2px;text-underline-offset:4px}
.overview-insights{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin-top:14px}.insight-panel{padding:24px}.recent-row,.knowledge-row{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);font-size:12px}.recent-row:last-child,.knowledge-row:last-child{border-bottom:0}.recent-service{font-weight:600;color:#e6ebf3;min-width:150px}.recent-time,.recent-mode{color:var(--muted);font-size:10px}.recent-mode{margin-left:auto;color:#a9a1ff}.knowledge-row{color:#dbe2eb}.knowledge-row::before{content:'+';color:#9e95ff;font-weight:700}
.analysis-summary{margin:24px 0 18px}.analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.analysis-panel{padding:22px}.analysis-panel.memory{border-color:rgba(139,124,255,.3);box-shadow:0 20px 55px rgba(83,72,185,.08)}.analysis-kicker{color:#9e95ff;font-size:9px;letter-spacing:.15em;text-transform:uppercase;font-weight:700}.analysis-item{padding:12px 0;border-bottom:1px solid var(--line);color:#dbe2eb;font-size:12px;line-height:1.55}.analysis-item:last-child{border-bottom:0}.analysis-item span{display:block;color:var(--muted);font-size:10px;margin-top:3px}
.compare-head{display:flex;align-items:center;justify-content:space-between;margin:38px 0 14px}.result-panel{min-height:420px;padding:24px}.result-label{display:flex;align-items:center;justify-content:space-between;padding-bottom:17px;border-bottom:1px solid var(--line);margin-bottom:18px}.result-title{font:600 16px 'Space Grotesk'}.hypothesis{padding:18px;border-radius:15px;background:rgba(255,255,255,.022);border:1px solid var(--line);margin-bottom:14px}.hypothesis-title{color:#9e95ff;font-size:9px;letter-spacing:.15em;text-transform:uppercase;font-weight:700;margin-bottom:9px}.hypothesis-text{color:#dce3eb;line-height:1.65;font-size:13px}.fix-card{display:flex;gap:14px;padding:17px 0;border-bottom:1px solid var(--line);animation:fadeUp .42s both}.fix-number{flex:none;width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:rgba(139,124,255,.11);border:1px solid rgba(139,124,255,.2);color:#bbb4ff;font-size:11px;font-weight:700}.fix-step{color:#eef2f7;font-size:13px;font-weight:600;line-height:1.5}.fix-reason{color:var(--muted);font-size:11px;line-height:1.55;margin-top:4px}
.evidence-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.evidence-card{padding:18px}.evidence-id{color:#8bd9ff;font-size:9px;font-weight:700;letter-spacing:.12em}.evidence-summary{color:#dbe2eb;font-size:12px;line-height:1.6;margin-top:8px}.evidence-outcome{color:var(--muted);font-size:10px;margin-top:8px}.warning{padding:13px 15px;border-left:3px solid var(--warning);background:rgba(234,185,90,.055);border-radius:10px;color:#e8d7a7;font-size:11px;line-height:1.55;margin-top:10px}.rejected{padding:17px;border:1px solid rgba(242,111,134,.22);background:rgba(242,111,134,.045);border-radius:15px;margin-top:12px}.rejected-label{color:#ff91a2;font-size:9px;letter-spacing:.13em;text-transform:uppercase;font-weight:700}
.dashboard-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;margin-top:22px}.dashboard-card{padding:24px;min-height:230px}.arch-row{display:flex;align-items:center;gap:10px;margin-top:20px}.arch-step{flex:1;min-height:96px;padding:20px 18px;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.017);transition:transform .25s ease,border-color .25s ease,box-shadow .25s ease,background .25s ease}.arch-step:hover{transform:translateY(-5px) scale(1.035);border-color:rgba(139,124,255,.7);background:rgba(139,124,255,.1);box-shadow:0 16px 34px rgba(92,82,220,.28),0 0 24px rgba(66,183,244,.12)}.arch-step:hover .arch-kicker,.arch-step:hover .arch-name{color:#fff}.arch-arrow{flex:none;color:#657083;font-size:20px;transition:color .25s ease,text-shadow .25s ease,transform .25s ease}.arch-row:has(.arch-step:hover) .arch-arrow{color:#a9a1ff;text-shadow:0 0 14px rgba(139,124,255,.8);transform:scale(1.15)}.arch-kicker{color:var(--subtle);font-size:9px;text-transform:uppercase;letter-spacing:.12em}.arch-name{margin-top:9px;font-weight:600;font-size:14px;transition:color .25s ease}.summary-text{color:#cfd7e2;font-size:12px;line-height:1.75;white-space:pre-wrap}.kpi-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}.mini-kpi{padding:14px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.018)}.mini-kpi b{font:600 18px 'Space Grotesk';display:block}.mini-kpi span{color:var(--muted);font-size:10px}.learn-card{padding:24px}.learn-point{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.55}.learn-line{width:4px;height:4px;margin-top:7px;border-radius:50%;background:#9e95ff;flex:none}
[data-testid="stVerticalBlockBorderWrapper"]:has(.result-label),[data-testid="stVerticalBlockBorderWrapper"]:has(.learn-card-marker){border:1px solid var(--line)!important;border-radius:20px!important;background:linear-gradient(145deg,rgba(16,21,29,.96),rgba(10,13,18,.93))!important;box-shadow:0 22px 70px rgba(0,0,0,.17)!important}
.footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);display:flex;justify-content:space-between;color:var(--subtle);font-size:10px}.footer strong{color:#8995a5;font-weight:600}.stSpinner>div{border-top-color:var(--accent)!important}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@media(max-width:1050px){.brand{min-width:190px}.nav-caption{display:none}.metrics{grid-template-columns:repeat(2,1fr)}.dashboard-grid,.overview-insights{grid-template-columns:1fr}}@media(max-width:760px){.block-container{padding:1rem 1rem 2.5rem}.masthead{padding-bottom:18px}.masthead-title{font-size:clamp(3rem,17vw,5rem)}.topbar{margin-bottom:24px}.brand-sub,.status{display:none}.metrics,.evidence-grid,.kpi-strip,.analysis-grid{grid-template-columns:1fr}.arch-row{display:grid;grid-template-columns:1fr;gap:8px}.arch-arrow{justify-self:center;transform:rotate(90deg)}.page-head{display:block}.composer{padding:18px}}
</style>
""", unsafe_allow_html=True)

for key, default in {"page":"overview","res_plain":None,"res_mem":None,"alert":"","done":False,"not_alert":False,"saved":{},"summary":None,"stale":False,"graph":None,"recent_investigations":[]}.items():
    st.session_state.setdefault(key, default)


@st.cache_data
def load_demo():
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "demo_alerts.json"), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"id":"DEMO-X","alert":"payments-api p99 latency > 12s, error rate 38%, pgbouncer at 100% of pool"}]


demo = load_demo()


@st.cache_data
def load_catalog_counts():
    base = os.path.join(os.path.dirname(__file__), "data")
    try:
        with open(os.path.join(base, "incidents.json"), encoding="utf-8") as f:
            incidents = json.load(f)
        with open(os.path.join(base, "runbooks.json"), encoding="utf-8") as f:
            runbooks = json.load(f)
        actions = [action for incident in incidents for action in incident.get("actions", [])]
        failed_actions = sum(action.get("result") == "failed" for action in actions)
        worked_actions = sum(action.get("result") == "worked" for action in actions)
        incidents_with_failures = sum(
            any(action.get("result") == "failed" for action in incident.get("actions", []))
            for incident in incidents
        )
        return (len(incidents), len(runbooks), sum(item.get("status") == "deprecated" for item in runbooks),
            failed_actions, worked_actions, incidents_with_failures)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 0, 0, 0, 0, 0

incident_count, runbook_count, deprecated_runbook_count, failed_action_count, worked_action_count, incidents_with_failures = load_catalog_counts()


@st.cache_data
def load_knowledge_topics():
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "runbooks.json"), encoding="utf-8") as f:
            runbooks = json.load(f)
        return [f"{runbook.get('id', 'Runbook')} · {runbook.get('title', 'Operational procedure')}"
                for runbook in runbooks[:5]]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


knowledge_topics = load_knowledge_topics()


def navigate(page):
    st.session_state.page = page
    st.rerun()


def render_header():
    md('<div class="masthead"><div class="masthead-title"><em>Deja</em><strong>Ops</strong></div></div>')
    cols = st.columns([1,1,1,1,1,2.4], gap="small")
    for col, (label, page) in zip(cols, [("Overview","overview"),("Triage","triage"),("Memory","memory"),("Learn","learn"),("Graph","graph")]):
        with col:
            if st.button(label, type="primary" if st.session_state.page == page else "secondary", use_container_width=True, key=f"nav_{page}"):
                navigate(page)
    with cols[5]:
        md(f'<div class="status" style="justify-content:flex-end;margin-top:9px"><span class="status-dot"></span>Memory bank <strong style="color:#dce3eb">{esc(BANK_ID)}</strong></div>')


def footer():
    md('<div class="footer"><div><strong>Ravenclaw</strong> · DejaOps incident intelligence</div><div>Persistent memory · Evidence-led triage · Human-reviewed outcomes · Synthetic incident data</div></div>')


def metric_card(value, label, meta=""):
    return f'<div class="panel metric"><div class="metric-value">{esc(value)}</div><div class="metric-label">{esc(label)}</div><div class="metric-meta">{esc(meta)}</div></div>'


def fix_html(index, fix):
    return f'<div class="fix-card" style="animation-delay:{index*70}ms"><div class="fix-number">{index+1}</div><div><div class="fix-step">{esc(fix.get("step"))}</div><div class="fix-reason">{esc(fix.get("reason"))}</div></div></div>'


def relative_age(timestamp):
    minutes = max(0, int((datetime.now().timestamp() - timestamp) / 60))
    return "just now" if minutes == 0 else f"{minutes}m ago"


def render_overview():
    md('<div class="page-head"><div><div class="eyebrow">Operational intelligence</div><h1 class="hero-title">A <span>memory</span> layer for <span>incident</span> response.</h1><div class="hero-copy">DejaOps connects the current alert with historical incidents, verified outcomes, and operational context so engineers can investigate with less repetition and better evidence.</div></div></div>')
    
    md(f'<div class="metrics">{metric_card(failed_action_count,"Failed fixes remembered","Remediations DejaOps can warn against")}{metric_card(worked_action_count,"Worked fixes remembered","Historical actions supporting recommendations")}{metric_card(incidents_with_failures,"Incidents with failure history",f"of {incident_count} seeded incidents")}{metric_card(deprecated_runbook_count,"Deprecated runbooks","Replacements need attention")}</div>')
    md('<div class="mvp-intro"><div class="section-title"><span class="title-mark">See</span> the MVP in action</div><div class="section-copy">Teach DejaOps a verified incident lesson, then return with a differently worded alert and watch the system recall the relevant experience. The loop makes <span class="mvp-underline">persistent memory visible</span> through better recommendations, rejected failed fixes, and evidence from past incidents.</div></div>')

    md('<div class="dashboard-grid"><div class="panel dashboard-card"><div class="section-title"><span class="title-mark">Inve</span>stigation workflow</div><div class="section-copy">The response pipeline keeps retrieval, reasoning, evidence, and feedback visible.</div><div class="arch-row"><div class="arch-step"><div class="arch-kicker">01</div><div class="arch-name">Alert</div></div><div class="arch-arrow" aria-hidden="true">→</div><div class="arch-step"><div class="arch-kicker">02</div><div class="arch-name">Recall</div></div><div class="arch-arrow" aria-hidden="true">→</div><div class="arch-step"><div class="arch-kicker">03</div><div class="arch-name">Reason</div></div><div class="arch-arrow" aria-hidden="true">→</div><div class="arch-step"><div class="arch-kicker">04</div><div class="arch-name">Learn</div></div></div></div><div class="panel dashboard-card"><div class="section-title"><span class="title-mark">Work</span>space status</div><div class="section-copy">Current system capabilities</div><div class="kpi-strip"><div class="mini-kpi"><b>Live</b><span>Memory connection</span></div><div class="mini-kpi"><b>4</b><span>Core workflow stages</span></div><div class="mini-kpi"><b>2</b><span>Outcome states</span></div></div><div class="summary-text" style="margin-top:22px">Run a seeded scenario from Triage, inspect the evidence in Memory, or teach a verified postmortem from Learn.</div></div></div>')
    recent_rows = ''.join(f'<div class="recent-row"><span class="recent-service">{esc(item.get("service", "Incident alert"))}</span><span class="recent-time">{esc(relative_age(item.get("at", datetime.now().timestamp())))}</span><span class="recent-mode">{esc(item.get("mode", "Memory-assisted"))}</span></div>' for item in st.session_state.recent_investigations)
    recent_rows = recent_rows or '<div class="section-copy" style="margin-top:18px">Run an investigation from Triage to populate recent activity.</div>'
    knowledge_rows = ''.join(f'<div class="knowledge-row">{esc(topic)}</div>' for topic in knowledge_topics)
    md(f'<div class="overview-insights"><div class="panel insight-panel"><div class="section-title">Recent investigations</div><div class="section-copy">Successful triage runs from this session.</div>{recent_rows}</div><div class="panel insight-panel"><div class="section-title">Knowledge</div><div class="section-copy">Representative runbooks retained by the system.</div>{knowledge_rows}</div></div>')


def run_triage(alert_text):
    a = alert_text.strip()
    if not looks_like_alert(a):
        st.session_state.not_alert = True; st.session_state.done = False; return
    st.session_state.not_alert = False; st.session_state.alert = a; st.session_state.saved = {}; st.session_state.done = False
    with st.spinner("Running incident analysis"):
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future_plain = ex.submit(triage, a, False); mem_result = triage(a, True); plain_result = future_plain.result()
            st.session_state.res_mem = mem_result; st.session_state.res_plain = plain_result; st.session_state.done = True
            service = next((name for name in ("checkout-service", "payments-api", "orders-api", "auth-service", "Redis", "CoreDNS", "PayFlow") if name.lower() in a.lower()), "Incident alert")
            recent = st.session_state.recent_investigations
            recent.insert(0, {"service": service, "at": datetime.now().timestamp(), "mode": "Memory-assisted"})
            st.session_state.recent_investigations = recent[:5]
        except Exception as exc:
            st.session_state.done = False; st.error(str(exc))


def _apply_demo_selection():
    # Runs as an on_change callback, BEFORE the widgets below are re-created on
    # this rerun, so writing directly into "alert_editor" (the text_area's own
    # key) is what actually updates the visible box. Writing to a differently
    # named key (the old st.session_state.alert = ...) and passing it in as
    # `value=` does NOT work on Streamlit: once a keyed widget has rendered
    # once, `value=` is ignored on every later rerun and only the widget's own
    # session_state[key] controls what's shown. That mismatch was why picking
    # a second demo scenario silently left the previous alert's text in the box.
    options = ["Select a demo scenario"] + [f"{item['id']} · {item['alert'][:76]}" for item in demo]
    selected = st.session_state.get("demo_selector")
    if selected and selected != options[0]:
        chosen = demo[options.index(selected) - 1]["alert"]
        st.session_state["alert_editor"] = chosen
        st.session_state.alert = chosen


def render_composer():
    md('<div class="panel composer"><div class="composer-head"><div><div class="composer-title">Start an investigation</div><div class="composer-note">Choose a seeded scenario or paste an alert from your monitoring system.</div></div><span class="pill accent">Incident triage</span></div></div>')
    c1, c2 = st.columns([1, 1.9], gap="large")
    with c1:
        options = ["Select a demo scenario"] + [f"{item['id']} · {item['alert'][:76]}" for item in demo]
        st.selectbox("Demo scenario", options, key="demo_selector", on_change=_apply_demo_selection)
    with c2:
        st.session_state.setdefault("alert_editor", st.session_state.alert)
        alert_text = st.text_area("Alert payload", height=130, placeholder="Paste a monitoring alert, incident message, or Kubernetes event...", key="alert_editor")
    _, action = st.columns([4, 1])
    with action:
        if st.button("Run triage", type="primary", use_container_width=True, key="run_triage"):
            run_triage(alert_text)
            if st.session_state.done: st.rerun()


def render_results():
    rp = st.session_state.res_plain or {}; rm = st.session_state.res_mem or {}
    evidence = rm.get("display_evidence", rm.get("evidence", [])); warnings = rm.get("warnings", []); fixes = rm.get("recommended_fixes", []); rejected = rm.get("rejected_by_memory", [])
    relevant = rm.get("display_memories", evidence); relevant_count = len(relevant) if isinstance(relevant, list) else len(evidence)
    effective_warnings = [w for w in warnings if "no similar" not in w.lower()]
    confidence = "High" if relevant_count >= 2 and fixes else ("Medium" if relevant_count or fixes else "Low")
    md(f'<div class="metrics">{metric_card(relevant_count,"Relevant memories","Focused evidence for this alert")}{metric_card(len(effective_warnings),"Historical warnings","Past failure or runbook signals")}{metric_card(len(fixes),"Recommended actions","Current response candidates")}{metric_card(confidence,"Confidence","Based on available historical evidence")}</div>')
    baseline_steps = ''.join(f'<div class="analysis-item">{esc(fix.get("step"))}<span>{esc(fix.get("reason"))}</span></div>' for fix in rp.get("recommended_fixes", [])) or '<div class="analysis-item">No investigation steps returned.</div>'
    historical_items = ''.join(f'<div class="analysis-item">{esc(item.get("incident_id"))}<span>{esc(item.get("summary"))} · {esc(item.get("outcome"))}</span></div>' for item in evidence) or '<div class="analysis-item">No focused historical evidence.</div>'
    supported = [item for item in rm.get("action_provenance", []) if item.get("outcome") == "worked" and item.get("incident_id")]
    supported_items = ''.join(f'<div class="analysis-item">{esc(item.get("action"))}<span>{esc(item.get("incident_id"))} · {esc(item.get("date") or "date unavailable")}</span></div>' for item in supported) or '<div class="analysis-item">No historically supported action matched.</div>'
    rejected_items = ''.join(f'<div class="analysis-item">{esc(item.get("remediation"))}<span>{esc(item.get("incident_id", "FEEDBACK"))} · failed · {esc(item.get("date") or "date unavailable")}</span></div>' for item in rejected) or '<div class="analysis-item">No rejected historical action matched.</div>'
    md(f'<div class="analysis-summary"><div class="section-title"><span class="title-mark">Current</span> analysis</div><div class="section-copy">A live comparison of the baseline response and the memory-assisted investigation.</div></div><div class="analysis-grid"><div class="panel analysis-panel"><div class="result-title">Without memory</div><div class="analysis-kicker" style="margin-top:20px">Hypothesis</div><div class="analysis-item">{esc(rp.get("hypothesis"))}</div><div class="analysis-kicker" style="margin-top:16px">Investigation steps</div>{baseline_steps}</div><div class="panel analysis-panel memory"><div class="result-title">With memory</div><div class="analysis-kicker" style="margin-top:20px">Hypothesis</div><div class="analysis-item">{esc(rm.get("hypothesis"))}</div><div class="analysis-kicker" style="margin-top:16px">Historical evidence</div>{historical_items}<div class="analysis-kicker" style="margin-top:16px">Supported actions</div>{supported_items}<div class="analysis-kicker" style="margin-top:16px">Rejected actions</div>{rejected_items}</div></div>')
    md('<div class="compare-head"><div><div class="section-title">Triage comparison</div><div class="section-copy">Baseline reasoning versus memory-assisted reasoning.</div></div></div>')
    left, right = st.columns(2, gap="medium")
    with left:
        # Each st.markdown() call is its own isolated DOM fragment in Streamlit,
        # so a <div> opened in one call is never actually closed by content added
        # in a later call -- the browser auto-closes it empty right where that
        # call ends. .result-panel has min-height:420px, so the auto-closed empty
        # div still renders as a large blank box, with the real content (which
        # ended up in separate, unwrapped fragments) appearing below it instead
        # of inside it. st.container(border=True) is a real Streamlit layout
        # primitive: everything rendered inside the `with` block -- across as
        # many markdown/widget calls as needed -- is grouped under one real
        # bordered box, so this can't happen.
        with st.container(border=True):
            md('<div class="result-label"><div class="result-title">Baseline analysis</div><span class="pill">No memory</span></div>')
            md(f'<div class="hypothesis"><div class="hypothesis-title">Hypothesis</div><div class="hypothesis-text">{esc(rp.get("hypothesis"))}</div></div>')
            for i, fix in enumerate(rp.get("recommended_fixes", [])): md(fix_html(i, fix))
    with right:
        with st.container(border=True):
            md('<div class="result-label"><div class="result-title">Memory-assisted analysis</div><span class="pill accent">Hindsight context</span></div>')
            md(f'<div class="hypothesis"><div class="hypothesis-title">Hypothesis</div><div class="hypothesis-text">{esc(rm.get("hypothesis"))}</div></div>')
            for i, fix in enumerate(fixes):
                md(fix_html(i, fix)); key = f"fix_{i}"
                if not st.session_state.saved.get(key):
                    b1, b2, _ = st.columns([1, 1, 3])
                    with b1:
                        if st.button("Worked", key=f"worked_{i}"):
                            try: record_outcome(st.session_state.alert, fix.get("step", ""), True); st.session_state.saved[key] = "worked"; st.session_state.stale = True; st.rerun()
                            except Exception as exc: st.error(str(exc))
                    with b2:
                        if st.button("Failed", key=f"failed_{i}"):
                            try: record_outcome(st.session_state.alert, fix.get("step", ""), False); st.session_state.saved[key] = "failed"; st.session_state.stale = True; st.rerun()
                            except Exception as exc: st.error(str(exc))
                else: md(f'<div class="pill" style="display:inline-flex;margin-top:8px">Outcome recorded: {esc(st.session_state.saved[key])}</div>')
    if evidence:
        md('<div style="margin-top:38px"><div class="section-title">Historical evidence</div><div class="section-copy">Focused memories that directly support the current investigation.</div></div>')
        cards = ''.join(f'<div class="panel evidence-card"><div class="evidence-id">{esc(item.get("incident_id"))}</div><div class="evidence-summary">{esc(item.get("summary"))}</div><div class="evidence-outcome">Historical outcome · {esc(item.get("outcome"))}</div></div>' for item in evidence)
        md(f'<div class="evidence-grid" style="margin-top:14px">{cards}</div>')
    if rejected:
        md('<div style="margin-top:34px"><div class="section-title">Rejected by historical evidence</div><div class="section-copy">Previously attempted remediations that should not be repeated without new evidence.</div></div>')
        for item in rejected: md(f'<div class="rejected"><div class="rejected-label">Historical rejection</div><div style="font-weight:600;font-size:13px;margin-top:8px">{esc(item.get("remediation"))}</div><div class="evidence-outcome">{esc(item.get("incident_id"))} · {esc(item.get("reason"))}</div></div>')
    if effective_warnings:
        md('<div style="margin-top:28px"><div class="section-title">Operational warnings</div></div>')
        for warning in effective_warnings: md(f'<div class="warning">{esc(warning)}</div>')


def render_triage_page():
    md('<div class="page-head"><div><div class="eyebrow">Triage workspace</div><h1 class="hero-title">Investigate the signal, <span>then act.</span></h1><div class="hero-copy">Compare a baseline response with a memory-assisted response and keep historical evidence visible alongside each remediation.</div></div></div>')
    render_composer()
    if st.session_state.not_alert: md('<div class="panel panel-pad" style="margin-top:18px"><div class="eyebrow">Input validation</div><div class="summary-text">The current input does not contain enough incident context. Add a service, symptom, error, or alert condition and try again.</div></div>')
    if st.session_state.done: render_results()
    else: md('<div class="dashboard-grid"><div class="panel dashboard-card"><div class="section-title">How the analysis works</div><div class="section-copy">Every investigation follows the same operational sequence.</div><div class="arch-row"><div class="arch-step"><div class="arch-kicker">01</div><div class="arch-name">Capture signal</div></div><div class="arch-step"><div class="arch-kicker">02</div><div class="arch-name">Recall history</div></div><div class="arch-step"><div class="arch-kicker">03</div><div class="arch-name">Generate actions</div></div><div class="arch-step"><div class="arch-kicker">04</div><div class="arch-name">Record outcome</div></div></div></div><div class="panel dashboard-card"><div class="section-title">Current workspace</div><div class="section-copy">Ready for a new incident.</div><div class="summary-text" style="margin-top:25px">Use a seeded alert to demonstrate historical fixes, failed attempts, runbook context, and outcome feedback.</div></div></div>')


def render_memory_page():
    md('<div class="page-head"><div><div class="eyebrow">Organizational memory</div><h1 class="hero-title">See what the system <span>remembers.</span></h1><div class="hero-copy">Review learned patterns, recent recall, and the state of the memory bank used during triage.</div></div></div>')
    if st.session_state.stale: md('<div class="warning" style="margin-top:0">New outcome feedback has been stored. Refresh the memory summary to include the latest information.</div>')
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Refresh summary", type="primary", use_container_width=True, key="refresh_summary"):
            with st.spinner("Refreshing memory summary"):
                try: st.session_state.summary = learned_summary(); st.session_state.stale = False; st.rerun()
                except Exception as exc: st.error(str(exc))
    with c2: md(f'<div class="pill" style="display:inline-flex;margin-top:8px">Memory bank · {esc(BANK_ID)}</div>')
    a, b = st.columns([1.3, .7], gap="large")
    with a: md(f'<div class="panel dashboard-card" style="margin-top:22px"><div class="section-title">Learned summary</div><div class="section-copy">Reflected from stored incidents, runbooks, and outcomes.</div><div class="summary-text" style="margin-top:20px">{esc(st.session_state.summary or "No summary loaded yet. Refresh to query the memory bank.")}</div></div>')
    with b:
        evidence = (st.session_state.res_mem or {}).get("evidence", []); relevant = (st.session_state.res_mem or {}).get("display_memories", evidence)
        md(f'<div class="panel dashboard-card" style="margin-top:22px"><div class="section-title">Latest recall</div><div class="section-copy">Focused evidence from the most recent triage.</div><div class="metric-value" style="margin-top:24px">{len(relevant)}</div><div class="metric-label">relevant memories</div><div class="metric-meta">The complete recalled block remains available to reasoning; this view shows focused evidence.</div></div>')
    footer()


def render_learn_page():
    md('<div class="page-head"><div><div class="eyebrow">Knowledge capture</div><h1 class="hero-title">Teach the system from <span>postmortems.</span></h1><div class="hero-copy">Capture verified incident narratives so future investigations can reuse the same operational context.</div></div></div>')
    if not retain_postmortem:
        md('<div class="warning" style="margin-top:24px">Postmortem retention is not available in the current memory module.</div>'); footer(); return
    left, right = st.columns([1.2, .8], gap="large")
    with left:
        with st.container(border=True):
            md('<div class="learn-card-marker" style="display:none"></div><div class="section-title">New postmortem</div><div class="section-copy">Include the incident, root cause, failed attempts, successful resolution, and relevant runbook IDs.</div>')
            pm = st.text_area("Postmortem content", height=360, placeholder="Incident ID, service, date, symptoms, root cause, what failed, what worked, and why...", key="postmortem_editor")
            if st.button("Store postmortem", type="primary", use_container_width=True, key="store_postmortem"):
                if not pm.strip(): st.warning("Add postmortem content first.")
                else:
                    try:
                        result = retain_postmortem(pm.strip())
                        if result is False: raise RuntimeError("Memory store did not confirm the postmortem.")
                        st.session_state.stale = True; st.success("Postmortem stored successfully.")
                    except Exception as exc: st.error(str(exc))
    with right:
        md('<div class="panel learn-card"><div class="section-title">A useful memory contains</div><div class="section-copy">Keep incident records specific enough to guide a future response.</div><div style="margin-top:18px"><div class="learn-point"><span class="learn-line"></span><span>The affected service and observable symptoms.</span></div><div class="learn-point"><span class="learn-line"></span><span>Failed remediation attempts separated from successful actions.</span></div><div class="learn-point"><span class="learn-line"></span><span>Incident IDs and dates when available.</span></div><div class="learn-point"><span class="learn-line"></span><span>Why the successful fix worked under those conditions.</span></div></div></div>')
    footer()


def render_graph_page():
    if render_brain_page:
        render_brain_page(learned_summary, retain_postmortem, (st.session_state.res_mem or {}).get("display_memories") or (st.session_state.res_mem or {}).get("evidence", []))
    else:
        md('<div class="warning">Memory graph module is unavailable.</div>')


render_header()
if st.session_state.page == "overview": render_overview()
elif st.session_state.page == "triage": render_triage_page()
elif st.session_state.page == "memory": render_memory_page()
elif st.session_state.page == "learn": render_learn_page()
elif st.session_state.page == "graph":
    render_graph_page()
    footer()
else: render_overview()
if st.session_state.page in {"overview", "triage"}: footer()