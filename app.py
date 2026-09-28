"""DejaOps — operational intelligence workspace."""
import html
import json
import os
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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#07090d;--line:rgba(255,255,255,.075);--text:#eef2f7;--muted:#8d98a8;--subtle:#5e6978;--accent:#8b7cff;--accent-2:#42b7f4;--success:#45d39c;--warning:#eab95a;--danger:#f26f86}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;color:var(--text)}
.stApp{background:radial-gradient(900px 500px at 0% -10%,rgba(139,124,255,.12),transparent 68%),radial-gradient(800px 460px at 100% 0%,rgba(66,183,244,.08),transparent 66%),var(--bg)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.32;background-image:linear-gradient(rgba(255,255,255,.016) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.016) 1px,transparent 1px);background-size:64px 64px;mask-image:linear-gradient(to bottom,#000,transparent 72%)}
#MainMenu,footer,[data-testid="stDecoration"],.stAppDeployButton{display:none!important} header{background:transparent!important}.block-container{max-width:1500px;padding:1rem 2.5rem 3.5rem}
.topbar{display:flex;align-items:center;gap:24px;min-height:66px;padding:8px 12px 8px 16px;margin-bottom:16px;border:1px solid var(--line);border-radius:18px;background:rgba(9,12,17,.84);backdrop-filter:blur(24px);box-shadow:0 18px 55px rgba(0,0,0,.18)}
.brand{display:flex;align-items:center;gap:12px;min-width:245px}.brand-mark{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--accent),var(--accent-2));box-shadow:0 8px 26px rgba(91,91,220,.25);font:700 12px 'Space Grotesk';color:#fff;letter-spacing:-.03em}.brand-name{font:700 18px 'Space Grotesk';letter-spacing:-.025em}.brand-sub{font-size:10px;color:var(--muted);margin-top:2px}.nav-caption{font-size:10px;color:var(--subtle);text-transform:uppercase;letter-spacing:.12em;margin-left:auto}.status{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:11px;white-space:nowrap}.status-dot{width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 0 5px rgba(69,211,156,.08)}
.stButton>button{min-height:40px;border-radius:11px!important;border:1px solid var(--line)!important;background:rgba(255,255,255,.025)!important;color:var(--text)!important;font-weight:600!important;transition:transform .2s ease,border-color .2s ease,background .2s ease,box-shadow .2s ease}.stButton>button:hover{transform:translateY(-1px);border-color:rgba(139,124,255,.45)!important;background:rgba(139,124,255,.07)!important;box-shadow:0 10px 28px rgba(0,0,0,.2)}.stButton>button[kind="primary"]{border:0!important;color:#fff!important;background:linear-gradient(110deg,#7568ef,#36aee6)!important;box-shadow:0 12px 32px rgba(87,103,235,.22)}
[data-baseweb="select"]>div,[data-baseweb="textarea"],[data-testid="stTextArea"] textarea{background:rgba(255,255,255,.025)!important;border:1px solid var(--line)!important;border-radius:13px!important;color:var(--text)!important}[data-testid="stTextArea"] textarea{min-height:126px}label{color:var(--muted)!important;font-size:11px!important;font-weight:600!important}
.eyebrow{color:#9e95ff;font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;margin-bottom:10px}.hero-title{font:700 clamp(2.3rem,4.7vw,4.4rem)/.98 'Space Grotesk';letter-spacing:-.06em;max-width:980px;margin:0}.hero-title span{color:#9b91ff}.hero-copy{color:var(--muted);font-size:15px;line-height:1.75;max-width:760px;margin:16px 0 0}.page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:28px;margin-bottom:30px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0 30px}.metric{padding:20px 21px;min-height:112px}.metric-value{font:600 30px 'Space Grotesk';letter-spacing:-.045em}.metric-label{color:var(--muted);font-size:11px;margin-top:5px}.metric-meta{color:var(--subtle);font-size:10px;margin-top:13px;line-height:1.45}.panel{background:linear-gradient(145deg,rgba(16,21,29,.96),rgba(10,13,18,.93));border:1px solid var(--line);border-radius:20px;box-shadow:0 22px 70px rgba(0,0,0,.17)}.panel-pad{padding:24px}.panel-accent{border-color:rgba(139,124,255,.3);box-shadow:0 24px 75px rgba(83,72,185,.09)}
.section-title{font:600 19px 'Space Grotesk';letter-spacing:-.025em}.section-copy{color:var(--muted);font-size:12px;line-height:1.6;margin-top:5px}.composer{padding:24px;margin-top:26px}.composer-head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:18px}.composer-title{font:600 18px 'Space Grotesk'}.composer-note{color:var(--muted);font-size:12px;margin-top:4px}.pill{display:inline-flex;align-items:center;border:1px solid var(--line);color:var(--muted);padding:5px 9px;border-radius:999px;font-size:9px;font-weight:700;letter-spacing:.07em;text-transform:uppercase}.pill.accent{color:#ddd9ff;border-color:rgba(139,124,255,.3);background:rgba(139,124,255,.08)}
.compare-head{display:flex;align-items:center;justify-content:space-between;margin:38px 0 14px}.result-panel{min-height:420px;padding:24px}.result-label{display:flex;align-items:center;justify-content:space-between;padding-bottom:17px;border-bottom:1px solid var(--line);margin-bottom:18px}.result-title{font:600 16px 'Space Grotesk'}.hypothesis{padding:18px;border-radius:15px;background:rgba(255,255,255,.022);border:1px solid var(--line);margin-bottom:14px}.hypothesis-title{color:#9e95ff;font-size:9px;letter-spacing:.15em;text-transform:uppercase;font-weight:700;margin-bottom:9px}.hypothesis-text{color:#dce3eb;line-height:1.65;font-size:13px}.fix-card{display:flex;gap:14px;padding:17px 0;border-bottom:1px solid var(--line);animation:fadeUp .42s both}.fix-number{flex:none;width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:rgba(139,124,255,.11);border:1px solid rgba(139,124,255,.2);color:#bbb4ff;font-size:11px;font-weight:700}.fix-step{color:#eef2f7;font-size:13px;font-weight:600;line-height:1.5}.fix-reason{color:var(--muted);font-size:11px;line-height:1.55;margin-top:4px}
.evidence-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.evidence-card{padding:18px}.evidence-id{color:#8bd9ff;font-size:9px;font-weight:700;letter-spacing:.12em}.evidence-summary{color:#dbe2eb;font-size:12px;line-height:1.6;margin-top:8px}.evidence-outcome{color:var(--muted);font-size:10px;margin-top:8px}.warning{padding:13px 15px;border-left:3px solid var(--warning);background:rgba(234,185,90,.055);border-radius:10px;color:#e8d7a7;font-size:11px;line-height:1.55;margin-top:10px}.rejected{padding:17px;border:1px solid rgba(242,111,134,.22);background:rgba(242,111,134,.045);border-radius:15px;margin-top:12px}.rejected-label{color:#ff91a2;font-size:9px;letter-spacing:.13em;text-transform:uppercase;font-weight:700}
.dashboard-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;margin-top:22px}.dashboard-card{padding:24px;min-height:230px}.arch-row{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:20px}.arch-step{padding:14px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.017);transition:transform .2s ease,border-color .2s ease}.arch-step:hover{transform:translateY(-2px);border-color:rgba(139,124,255,.25)}.arch-kicker{color:var(--subtle);font-size:9px;text-transform:uppercase;letter-spacing:.12em}.arch-name{margin-top:7px;font-weight:600;font-size:12px}.summary-text{color:#cfd7e2;font-size:12px;line-height:1.75;white-space:pre-wrap}.kpi-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}.mini-kpi{padding:14px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.018)}.mini-kpi b{font:600 18px 'Space Grotesk';display:block}.mini-kpi span{color:var(--muted);font-size:10px}.learn-card{padding:24px}.learn-point{display:flex;gap:12px;padding:13px 0;border-bottom:1px solid var(--line);color:var(--muted);font-size:12px;line-height:1.55}.learn-line{width:4px;height:4px;margin-top:7px;border-radius:50%;background:#9e95ff;flex:none}
.footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--line);display:flex;justify-content:space-between;color:var(--subtle);font-size:10px}.footer strong{color:#8995a5;font-weight:600}.stSpinner>div{border-top-color:var(--accent)!important}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@media(max-width:1050px){.brand{min-width:190px}.nav-caption{display:none}.metrics{grid-template-columns:repeat(2,1fr)}.dashboard-grid{grid-template-columns:1fr}}@media(max-width:760px){.block-container{padding:1rem 1rem 2.5rem}.topbar{margin-bottom:24px}.brand-sub,.status{display:none}.metrics,.evidence-grid,.arch-row,.kpi-strip{grid-template-columns:1fr}.page-head{display:block}.composer{padding:18px}}
</style>
""", unsafe_allow_html=True)

for key, default in {"page":"overview","res_plain":None,"res_mem":None,"alert":"","done":False,"not_alert":False,"saved":{},"summary":None,"stale":False,"graph":None}.items():
    st.session_state.setdefault(key, default)


@st.cache_data
def load_demo():
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "demo_alerts.json"), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"id":"DEMO-X","alert":"payments-api p99 latency > 12s, error rate 38%, pgbouncer at 100% of pool"}]


demo = load_demo()


def navigate(page):
    st.session_state.page = page
    st.rerun()


def render_header():
    md(f'<div class="topbar"><div class="brand"><div class="brand-mark">DO</div><div><div class="brand-name">DejaOps</div><div class="brand-sub">Operational memory workspace</div></div></div><div class="nav-caption">Workspace</div></div>')
    cols = st.columns([1,1,1,1,1,2.4], gap="small")
    for col, (label, page) in zip(cols, [("Overview","overview"),("Triage","triage"),("Memory","memory"),("Learn","learn"),("Graph","graph")]):
        with col:
            if st.button(label, type="primary" if st.session_state.page == page else "secondary", use_container_width=True, key=f"nav_{page}"):
                navigate(page)
    with cols[5]:
        md(f'<div class="status" style="justify-content:flex-end;margin-top:9px"><span class="status-dot"></span>Memory bank <strong style="color:#dce3eb">{esc(BANK_ID)}</strong></div>')


def footer():
    md('<div class="footer"><div><strong>DejaOps</strong> · Operational intelligence workspace</div><div>Historical memory · Human-reviewed outcomes · Synthetic incident data</div></div>')


def metric_card(value, label, meta=""):
    return f'<div class="panel metric"><div class="metric-value">{esc(value)}</div><div class="metric-label">{esc(label)}</div><div class="metric-meta">{esc(meta)}</div></div>'


def fix_html(index, fix):
    return f'<div class="fix-card" style="animation-delay:{index*70}ms"><div class="fix-number">{index+1}</div><div><div class="fix-step">{esc(fix.get("step"))}</div><div class="fix-reason">{esc(fix.get("reason"))}</div></div></div>'


def render_overview():
    md('<div class="page-head"><div><div class="eyebrow">Operational intelligence</div><h1 class="hero-title">A memory layer for <span>incident response.</span></h1><div class="hero-copy">DejaOps connects the current alert with historical incidents, verified outcomes, and operational context so engineers can investigate with less repetition and better evidence.</div></div></div>')
    md(f'<div class="metrics">{metric_card(len(demo),"Demo scenarios","Ready-to-run incident alerts")}{metric_card("Recall","Historical context","Hindsight memory retrieval")}{metric_card("Human","Outcome loop","Worked and failed feedback")}{metric_card("Online","Memory bank",BANK_ID)}</div>')
    md('<div class="dashboard-grid"><div class="panel dashboard-card"><div class="section-title">Investigation workflow</div><div class="section-copy">The response pipeline keeps retrieval, reasoning, evidence, and feedback visible.</div><div class="arch-row"><div class="arch-step"><div class="arch-kicker">01</div><div class="arch-name">Alert</div></div><div class="arch-step"><div class="arch-kicker">02</div><div class="arch-name">Recall</div></div><div class="arch-step"><div class="arch-kicker">03</div><div class="arch-name">Reason</div></div><div class="arch-step"><div class="arch-kicker">04</div><div class="arch-name">Learn</div></div></div></div><div class="panel dashboard-card"><div class="section-title">Workspace status</div><div class="section-copy">Current system capabilities</div><div class="kpi-strip"><div class="mini-kpi"><b>Live</b><span>Memory connection</span></div><div class="mini-kpi"><b>4</b><span>Core workflow stages</span></div><div class="mini-kpi"><b>2</b><span>Outcome states</span></div></div><div class="summary-text" style="margin-top:22px">Run a seeded scenario from Triage, inspect the evidence in Memory, or teach a verified postmortem from Learn.</div></div></div>')


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
        except Exception as exc:
            st.session_state.done = False; st.error(str(exc))


def render_composer():
    md('<div class="panel composer"><div class="composer-head"><div><div class="composer-title">Start an investigation</div><div class="composer-note">Choose a seeded scenario or paste an alert from your monitoring system.</div></div><span class="pill accent">Incident triage</span></div></div>')
    c1, c2 = st.columns([1, 1.9], gap="large")
    with c1:
        options = ["Select a demo scenario"] + [f"{item['id']} · {item['alert'][:76]}" for item in demo]
        selected = st.selectbox("Demo scenario", options, key="demo_selector")
        if selected != options[0]: st.session_state.alert = demo[options.index(selected)-1]["alert"]
    with c2:
        alert_text = st.text_area("Alert payload", value=st.session_state.alert, height=130, placeholder="Paste a monitoring alert, incident message, or Kubernetes event...", key="alert_editor")
    _, action = st.columns([4, 1])
    with action:
        if st.button("Run triage", type="primary", use_container_width=True, key="run_triage"):
            run_triage(alert_text)
            if st.session_state.done: st.rerun()


def render_results():
    rp = st.session_state.res_plain or {}; rm = st.session_state.res_mem or {}
    evidence = rm.get("evidence", []); warnings = rm.get("warnings", []); fixes = rm.get("recommended_fixes", []); rejected = rm.get("rejected_by_memory", [])
    relevant = rm.get("display_memories", evidence); relevant_count = len(relevant) if isinstance(relevant, list) else len(evidence)
    effective_warnings = [w for w in warnings if "no similar" not in w.lower()]
    confidence = "High" if relevant_count >= 2 and fixes else ("Medium" if relevant_count or fixes else "Low")
    md(f'<div class="metrics">{metric_card(relevant_count,"Relevant memories","Focused evidence for this alert")}{metric_card(len(effective_warnings),"Historical warnings","Past failure or runbook signals")}{metric_card(len(fixes),"Recommended actions","Current response candidates")}{metric_card(confidence,"Confidence","Based on available historical evidence")}</div>')
    md('<div class="compare-head"><div><div class="section-title">Triage comparison</div><div class="section-copy">Baseline reasoning versus memory-assisted reasoning.</div></div></div>')
    left, right = st.columns(2, gap="medium")
    with left:
        md('<div class="panel result-panel"><div class="result-label"><div class="result-title">Baseline analysis</div><span class="pill">No memory</span></div>')
        md(f'<div class="hypothesis"><div class="hypothesis-title">Hypothesis</div><div class="hypothesis-text">{esc(rp.get("hypothesis"))}</div></div>')
        for i, fix in enumerate(rp.get("recommended_fixes", [])): md(fix_html(i, fix))
        md('</div>')
    with right:
        md('<div class="panel panel-accent result-panel"><div class="result-label"><div class="result-title">Memory-assisted analysis</div><span class="pill accent">Hindsight context</span></div>')
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
        md('</div>')
    if evidence:
        md('<div style="margin-top:38px"><div class="section-title">Historical evidence</div><div class="section-copy">Focused memories that directly support the current investigation.</div></div><div class="evidence-grid" style="margin-top:14px">')
        for item in evidence: md(f'<div class="panel evidence-card"><div class="evidence-id">{esc(item.get("incident_id"))}</div><div class="evidence-summary">{esc(item.get("summary"))}</div><div class="evidence-outcome">Historical outcome · {esc(item.get("outcome"))}</div></div>')
        md('</div>')
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
        md('<div class="panel learn-card"><div class="section-title">New postmortem</div><div class="section-copy">Include the incident, root cause, failed attempts, successful resolution, and relevant runbook IDs.</div>')
        pm = st.text_area("Postmortem content", height=360, placeholder="Incident ID, service, date, symptoms, root cause, what failed, what worked, and why...", key="postmortem_editor")
        if st.button("Store postmortem", type="primary", use_container_width=True, key="store_postmortem"):
            if not pm.strip(): st.warning("Add postmortem content first.")
            else:
                try:
                    result = retain_postmortem(pm.strip())
                    if result is False: raise RuntimeError("Memory store did not confirm the postmortem.")
                    st.session_state.stale = True; st.success("Postmortem stored successfully.")
                except Exception as exc: st.error(str(exc))
        md('</div>')
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
