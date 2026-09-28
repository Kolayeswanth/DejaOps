"""
DejaOps — The on-call agent that has seen this before.
Streamlit UI — dark themed, two-column triage comparison.
"""

import json
import os
import html
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from agent import triage, record_outcome, learned_summary
from memory import BANK_ID

def esc(x): return html.escape(str(x or ""))
def blk(s): return "".join(line.strip() for line in s.splitlines())

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DejaOps · On-Call AI Agent",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS — premium dark UI
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Import Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background: linear-gradient(165deg, #0a0e17 0%, #0E1117 40%, #121929 100%);
    }

    /* ── Hero Header ── */
    .hero-container {
        text-align: center;
        padding: 2rem 1rem 1.5rem;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 3.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6C63FF 0%, #B24BF3 50%, #FF6B9D 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
        margin-bottom: 0.25rem;
        animation: glow 3s ease-in-out infinite alternate;
    }
    @keyframes glow {
        from { filter: drop-shadow(0 0 6px rgba(108,99,255,0.3)); }
        to   { filter: drop-shadow(0 0 18px rgba(178,75,243,0.5)); }
    }
    .hero-tagline {
        font-size: 1.15rem;
        color: #8B949E;
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    /* ── Divider ── */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #30363d, transparent);
        margin: 1.5rem 0;
    }

    /* ── Column headers ── */
    .col-header {
        font-size: 1.15rem;
        font-weight: 700;
        padding: 0.6rem 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 1rem;
        letter-spacing: 0.02em;
    }
    .col-header-plain {
        background: linear-gradient(135deg, #1c2333 0%, #21283b 100%);
        border: 1px solid #30363d;
        color: #8B949E;
    }
    .col-header-memory {
        background: linear-gradient(135deg, #1a1640 0%, #251a4a 100%);
        border: 1px solid #6C63FF44;
        color: #B8B0FF;
    }

    /* ── Cards ── */
    .result-card {
        background: linear-gradient(145deg, #161B22 0%, #1c2333 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    .result-card:hover {
        border-color: #6C63FF66;
        box-shadow: 0 4px 24px rgba(108, 99, 255, 0.08);
    }
    .card-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #6C63FF;
        margin-bottom: 0.5rem;
    }
    .card-text {
        color: #C9D1D9;
        font-size: 0.92rem;
        line-height: 1.65;
    }

    /* ── Fix step card ── */
    .fix-card {
        background: #161B22;
        border: 1px solid #30363d;
        border-left: 3px solid #6C63FF;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    .fix-step {
        color: #E6EDF3;
        font-weight: 600;
        font-size: 0.92rem;
        margin-bottom: 0.35rem;
    }
    .fix-reason {
        color: #8B949E;
        font-size: 0.84rem;
        font-style: italic;
    }

    /* ── Evidence cards ── */
    .evidence-card {
        background: linear-gradient(135deg, #1a1640 0%, #1c1d3a 100%);
        border: 1px solid #6C63FF33;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    .evidence-id {
        display: inline-block;
        background: #6C63FF22;
        color: #B8B0FF;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        margin-bottom: 0.5rem;
        letter-spacing: 0.05em;
    }
    .evidence-summary {
        color: #C9D1D9;
        font-size: 0.88rem;
        margin-bottom: 0.35rem;
        line-height: 1.55;
    }
    .evidence-outcome {
        color: #8B949E;
        font-size: 0.82rem;
    }

    /* ── Saved badge ── */
    .saved-badge {
        display: inline-block;
        background: linear-gradient(135deg, #0d3320 0%, #0f3d27 100%);
        color: #3FB950;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        border: 1px solid #3FB95044;
        margin-top: 0.3rem;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161B22 100%);
        border-right: 1px solid #21262d;
    }
    .sidebar-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #E6EDF3;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #6C63FF44;
    }
    .sidebar-content {
        background: #161B22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem;
        font-size: 0.88rem;
        color: #C9D1D9;
        line-height: 1.7;
    }

    /* ── Button overrides ── */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }

    /* ── Hide Streamlit branding ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    [data-testid="stDecoration"] {display: none;}
    header {background: transparent !important;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────
defaults = {
    "triage_result_no_mem": None,
    "triage_result_mem": None,
    "current_alert": "",
    "triage_done": False,
    "outcome_saved": {},       # key: (col, fix_index) → bool
    "sidebar_summary": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# Load demo alerts
# ─────────────────────────────────────────────
@st.cache_data
def load_demo_alerts():
    path = os.path.join(os.path.dirname(__file__), "data", "demo_alerts.json")
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return [
            {"id": "ALERT-001", "alert": "CRITICAL: payments-api p99 latency > 12s. Error rate 38%. PgBouncer at 100%."},
            {"id": "ALERT-002", "alert": "WARNING: auth-service HTTP 503 for 40% of requests. Redis cluster unreachable."},
            {"id": "ALERT-003", "alert": "CRITICAL: Kafka consumer lag > 500k. Consumer group has 0 active members."},
        ]

demo_alerts = load_demo_alerts()


# ─────────────────────────────────────────────
# Sidebar — Learned Summary
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-header">🧠 What DejaOps Has Learned</div>', unsafe_allow_html=True)

    st.caption(f"Memory bank: {BANK_ID}")

    if st.session_state.get("summary_stale"):
        st.caption("Memory updated - click Refresh to update this summary")

    if st.button("🔄 Refresh", key="refresh_summary", use_container_width=True):
        with st.spinner("Reflecting on past incidents..."):
            try:
                st.session_state.sidebar_summary = learned_summary()
                st.session_state.summary_stale = False
            except Exception as e:
                st.error(str(e))

    if st.session_state.sidebar_summary:
        st.markdown(st.session_state.sidebar_summary)
    else:
        st.markdown("Click Refresh to load")

    st.markdown("---")
    st.markdown(
        '<p style="color:#484f58;font-size:0.75rem;text-align:center;">'
        'DejaOps v0.1 · Memory-augmented on-call triage</p>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────
# Hero header
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-container">
    <div class="hero-title">DejaOps</div>
    <div class="hero-tagline">The on-call agent that has seen this before.</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Alert input section
# ─────────────────────────────────────────────
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

input_col1, input_col2 = st.columns([3, 1])

with input_col1:
    # Demo alert dropdown
    alert_options = ["— Select a demo alert —"] + [f"{a['id']}: {a['alert'][:80]}…" for a in demo_alerts]
    selected = st.selectbox("Load a demo alert", alert_options, key="demo_select", label_visibility="collapsed")

    # If a demo alert is selected, populate the text area
    if selected != "— Select a demo alert —":
        idx = alert_options.index(selected) - 1
        default_text = demo_alerts[idx]["alert"]
    else:
        default_text = st.session_state.get("current_alert", "")

    alert_text = st.text_area(
        "📋 Paste an alert",
        value=default_text,
        height=120,
        placeholder="Paste a PagerDuty / Datadog / CloudWatch alert here, or pick a demo above…",
    )

with input_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    triage_clicked = st.button(
        "🚨 Triage",
        use_container_width=True,
        type="primary",
    )


# ─────────────────────────────────────────────
# Run triage
# ─────────────────────────────────────────────
if triage_clicked:
    if not alert_text.strip():
        st.warning("Paste an alert or pick a demo alert first.")
    else:
        alert = alert_text.strip()
        st.session_state.current_alert = alert
        st.session_state.outcome_saved = {}

        with st.spinner("⏳ Running triage — comparing with & without memory…"):
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    f_plain = ex.submit(triage, alert_text.strip(), False)  # Groq only, thread-safe
                    mem = triage(alert_text.strip(), True)                   # uses Hindsight: MUST stay on the main thread
                    plain = f_plain.result()
                st.session_state.triage_result_no_mem = plain
                st.session_state.triage_result_mem = mem
                st.session_state.triage_done = True
            except Exception as e:
                st.error(str(e))


# ─────────────────────────────────────────────
# Display results
# ─────────────────────────────────────────────
if st.session_state.triage_done:
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2, gap="large")

    # ── LEFT COLUMN: Without Memory ──
    with col_left:
        st.markdown('<div class="col-header col-header-plain">🤖 Without Memory</div>', unsafe_allow_html=True)

        result = st.session_state.triage_result_no_mem
        if result:
            # Hypothesis
            st.markdown(blk(f"""
            <div class="result-card">
                <div class="card-label">Hypothesis</div>
                <div class="card-text">{esc(result.get("hypothesis", ""))}</div>
            </div>
            """), unsafe_allow_html=True)

            # Recommended fixes
            if result.get("recommended_fixes"):
                st.markdown(f'<div class="card-label" style="margin-top:0.5rem;">Recommended Fixes</div>', unsafe_allow_html=True)
                for i, fix in enumerate(result.get("recommended_fixes", [])):
                    st.markdown(blk(f"""
                    <div class="fix-card">
                        <div class="fix-step">Step {i+1}: {esc(fix.get("step", ""))}</div>
                        <div class="fix-reason">{esc(fix.get("reason", ""))}</div>
                    </div>
                    """), unsafe_allow_html=True)

    # ── RIGHT COLUMN: With Memory ──
    with col_right:
        st.markdown('<div class="col-header col-header-memory">🧠 With Memory (Hindsight)</div>', unsafe_allow_html=True)

        result = st.session_state.triage_result_mem
        if result:
            # Hypothesis
            st.markdown(blk(f"""
            <div class="result-card">
                <div class="card-label">Hypothesis</div>
                <div class="card-text">{esc(result.get("hypothesis", ""))}</div>
            </div>
            """), unsafe_allow_html=True)

            # Recommended fixes with Worked/Failed buttons
            if result.get("recommended_fixes"):
                st.markdown(f'<div class="card-label" style="margin-top:0.5rem;">Recommended Fixes</div>', unsafe_allow_html=True)
                for i, fix in enumerate(result.get("recommended_fixes", [])):
                    st.markdown(blk(f"""
                    <div class="fix-card">
                        <div class="fix-step">Step {i+1}: {esc(fix.get("step", ""))}</div>
                        <div class="fix-reason">{esc(fix.get("reason", ""))}</div>
                    </div>
                    """), unsafe_allow_html=True)

                    # Worked / Failed buttons
                    outcome_key = f"mem_fix_{i}"
                    if outcome_key not in st.session_state.outcome_saved or not st.session_state.outcome_saved[outcome_key]:
                        btn_cols = st.columns([1, 1, 3])
                        with btn_cols[0]:
                            if st.button("✅ Worked", key=f"worked_{i}"):
                                try:
                                    record_outcome(st.session_state.current_alert, fix.get("step", ""), True)
                                    st.session_state.outcome_saved[outcome_key] = "worked"
                                    st.session_state.summary_stale = True
                                    st.toast("Saved to memory")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                        with btn_cols[1]:
                            if st.button("❌ Failed", key=f"failed_{i}"):
                                try:
                                    record_outcome(st.session_state.current_alert, fix.get("step", ""), False)
                                    st.session_state.outcome_saved[outcome_key] = "failed"
                                    st.session_state.summary_stale = True
                                    st.toast("Saved to memory")
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                    else:
                        saved_type = st.session_state.outcome_saved[outcome_key]
                        icon = "✅" if saved_type == "worked" else "❌"
                        st.markdown(
                            f'<div class="saved-badge">{icon} Saved to memory</div>',
                            unsafe_allow_html=True
                        )

            # Evidence section
            if result.get("evidence"):
                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="card-label">📚 Recalled from Memory</div>', unsafe_allow_html=True)

                for ev in result.get("evidence", []):
                    st.markdown(blk(f"""
                    <div class="evidence-card">
                        <div class="evidence-id">{esc(ev.get("incident_id", ""))}</div>
                        <div class="evidence-summary">{esc(ev.get("summary", ""))}</div>
                        <div class="evidence-outcome">↳ <strong>Outcome:</strong> {esc(ev.get("outcome", ""))}</div>
                    </div>
                    """), unsafe_allow_html=True)

            # Warnings
            if result.get("warnings"):
                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
                for warning in result.get("warnings", []):
                    st.warning(str(warning))
