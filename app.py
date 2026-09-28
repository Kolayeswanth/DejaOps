"""DejaOps - the on-call agent that has seen this before. Modern glass UI."""
import html, json, os, time
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
import streamlit.components.v1 as components
from agent import triage, record_outcome, learned_summary
from memory import BANK_ID
try:
    from agent import looks_like_alert
except ImportError:
    looks_like_alert = lambda t: len((t or "").split()) >= 3
try:
    from memory import retain_postmortem
except ImportError:
    retain_postmortem = None

st.set_page_config(page_title="DejaOps", page_icon="🔮", layout="wide", initial_sidebar_state="collapsed")

esc = lambda x: html.escape(str(x or ""))
def blk(s): return "".join(l.strip() for l in s.splitlines())
def md(s): st.markdown(blk(s), unsafe_allow_html=True)
tm = lambda t: f'<span class="tm">⏱ {t:.1f}s</span>' if t is not None else ""

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');
:root{--bg:#070a13;--glass:rgba(255,255,255,.045);--line:rgba(255,255,255,.09);--txt:#e7ebf5;--mut:#8b94ab;--vio:#7c5cff;--cy:#22d3ee;--pink:#ff5c9d;--ok:#34d399;--warn:#fbbf24;--bad:#fb7185}
html,body,[class*="css"]{font-family:Inter,sans-serif;color:var(--txt)}
.stApp{background:radial-gradient(60rem 40rem at 8% -10%,rgba(124,92,255,.30),transparent 60%),radial-gradient(50rem 35rem at 95% 0%,rgba(34,211,238,.18),transparent 60%),radial-gradient(45rem 30rem at 50% 110%,rgba(255,92,157,.14),transparent 60%),var(--bg)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.16;background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px);background-size:46px 46px;-webkit-mask-image:radial-gradient(ellipse at 50% 0%,#000 15%,transparent 70%);mask-image:radial-gradient(ellipse at 50% 0%,#000 15%,transparent 70%)}
#MainMenu,footer,.stAppDeployButton,[data-testid="stDecoration"]{display:none}
header{background:transparent!important}
[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"]{display:none}
.hero{text-align:center;padding:1.6rem 0 .6rem}
.hero h1{font-family:'Space Grotesk',sans-serif;font-size:3.6rem;margin:0;letter-spacing:-.03em;background:linear-gradient(120deg,#a78bfa,#22d3ee 45%,#ff5c9d);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
.hero p{color:var(--mut);margin:.2rem 0 .8rem;font-size:1.05rem}
.live{display:inline-flex;align-items:center;gap:.5rem;padding:.3rem .8rem;border:1px solid var(--line);border-radius:99px;background:var(--glass);font-size:.75rem;color:var(--mut)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 0 rgba(52,211,153,.7);animation:pulse 2s infinite}
.pipe{display:flex;justify-content:center;align-items:center;gap:.4rem;margin:.6rem 0 1.4rem;flex-wrap:wrap}
.step{padding:.35rem .9rem;border-radius:99px;border:1px solid var(--line);background:var(--glass);font-size:.78rem;color:var(--mut);transition:.4s}
.step.on{color:#fff;border-color:transparent;background:linear-gradient(120deg,var(--vio),var(--cy));box-shadow:0 6px 24px rgba(124,92,255,.45)}
.arrow{color:var(--mut);opacity:.5}
.glass{background:var(--glass);border:1px solid var(--line);border-radius:18px;padding:1.05rem 1.25rem;margin-bottom:.8rem;backdrop-filter:blur(14px);animation:rise .55s both}
.glow{border:1px solid transparent;background:linear-gradient(#0d1120,#0d1120) padding-box,linear-gradient(120deg,var(--vio),var(--cy),var(--pink),var(--vio)) border-box;background-size:auto,300% 300%;animation:rise .55s both,shift 6s linear infinite;box-shadow:0 10px 40px rgba(124,92,255,.18)}
.lab{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;color:var(--cy);margin-bottom:.4rem;font-weight:600}
.txt{font-size:.93rem;line-height:1.65;color:#d5dbea}
.colh{display:flex;justify-content:space-between;align-items:center;margin-bottom:.8rem;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem}
.badge{font-family:Inter;font-size:.68rem;font-weight:600;padding:.25rem .65rem;border-radius:99px;border:1px solid var(--line);color:var(--mut)}
.badge.mem{color:#fff;border-color:transparent;background:linear-gradient(120deg,var(--vio),var(--pink))}
.fix{display:flex;gap:.85rem;align-items:flex-start}
.n{flex:none;width:28px;height:28px;border-radius:9px;display:grid;place-items:center;font-weight:700;font-size:.8rem;background:linear-gradient(135deg,var(--vio),var(--cy));color:#fff}
.gen .n{background:rgba(255,255,255,.08);color:var(--mut)}
.fs{font-weight:600;font-size:.92rem;color:#f1f4fb}.fr{color:var(--mut);font-size:.82rem;margin-top:.25rem}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin-bottom:1.1rem}
.tile{padding:.9rem 1rem;text-align:left}.tile b{display:block;font-family:'Space Grotesk';font-size:1.9rem;line-height:1.1;background:linear-gradient(120deg,#fff,var(--cy));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}.tile span{font-size:.72rem;color:var(--mut)}
.bar{height:6px;border-radius:9px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:.5rem}.bar i{display:block;height:100%;border-radius:9px;animation:grow 1s both}
.eid{display:inline-block;padding:.15rem .6rem;border-radius:99px;font-size:.72rem;font-weight:700;background:rgba(34,211,238,.12);color:var(--cy);margin-bottom:.4rem}
.warn{border-left:3px solid var(--warn);background:rgba(251,191,36,.07);border-radius:12px;padding:.75rem 1rem;margin-bottom:.6rem;font-size:.88rem;color:#fde9b0;animation:rise .55s both}
.saved{display:inline-block;margin:.1rem 0 .8rem 2.5rem;padding:.25rem .8rem;border-radius:99px;font-size:.75rem;font-weight:600;color:var(--ok);background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.3)}
.stButton>button{border-radius:12px;font-weight:600;border:1px solid var(--line);background:var(--glass);color:var(--txt);transition:.25s}
.stButton>button:hover{border-color:var(--vio);transform:translateY(-1px);box-shadow:0 6px 22px rgba(124,92,255,.3)}
.stButton>button[kind="primary"]{border:0;color:#fff;background:linear-gradient(120deg,var(--vio),var(--cy));box-shadow:0 8px 30px rgba(124,92,255,.45)}
[data-baseweb="textarea"],[data-baseweb="select"]>div{background:rgba(255,255,255,.04)!important;border:1px solid var(--line)!important;border-radius:14px!important}
.glass{position:relative}
.tm{position:absolute;top:.75rem;right:1rem;font-size:.7rem;font-weight:600;color:var(--cy);background:rgba(34,211,238,.1);border:1px solid rgba(34,211,238,.25);padding:.15rem .6rem;border-radius:99px}
.st-key-brain_btn button{width:54px;height:54px;border-radius:50%;font-size:1.6rem;padding:0;border:1px solid transparent;background:linear-gradient(#0d1120,#0d1120) padding-box,linear-gradient(120deg,var(--vio),var(--cy),var(--pink)) border-box;animation:brainpulse 2.6s ease-in-out infinite}
.st-key-brain_btn button:hover{transform:scale(1.12) rotate(-6deg)}
@keyframes brainpulse{0%,100%{box-shadow:0 0 0 0 rgba(124,92,255,.55)}50%{box-shadow:0 0 0 14px rgba(124,92,255,0)}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes pulse{70%{box-shadow:0 0 0 9px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}
@keyframes shift{to{background-position:0 0,300% 0}}
@keyframes grow{from{width:0}}
.brand{display:flex;align-items:center;gap:.6rem;font:700 1.2rem 'Space Grotesk',sans-serif}.brand small{color:var(--mut);font:500 .72rem Inter,sans-serif}
.logo{width:36px;height:36px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,var(--vio),var(--cy));box-shadow:0 6px 22px rgba(124,92,255,.5)}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:.9rem;margin-top:1.2rem}.card b{display:block;margin:.35rem 0 .2rem;font-family:'Space Grotesk',sans-serif}.card span{color:var(--mut);font-size:.85rem;line-height:1.5}.ci{font-size:1.6rem}
.card:hover{border-color:rgba(124,92,255,.5);transform:translateY(-3px);transition:.3s}
[data-baseweb="tab-list"]{gap:.4rem}[data-baseweb="tab"]{border-radius:12px!important}
@media(max-width:800px){.tiles,.cards{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:2.6rem}.colh{flex-direction:column;align-items:flex-start;gap:.4rem}}
</style>""", unsafe_allow_html=True)

for k, v in {"res_plain": None, "res_mem": None, "alert": "", "done": False, "not_alert": False,
             "saved": {}, "summary": None, "stale": False, "t_plain": None, "t_mem": None,
             "page": "home", "graph": None}.items():
    st.session_state.setdefault(k, v)

@st.cache_data
def load_demo():
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "demo_alerts.json"), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return [{"id": "DEMO-X", "alert": "payments-api p99 latency > 12s, error rate 38%, pgbouncer at 100% of pool"}]
demo = load_demo()

# ---------- brain page (memory graph) ----------
if st.session_state.page == "brain":
    from brain_graph import render_brain_page
    render_brain_page(learned_summary, retain_postmortem,
                      (st.session_state.res_mem or {}).get("evidence", []))
    st.stop()

# ---------- home page ----------
_nl, _nr, _bc = st.columns([5, 4, 1], vertical_alignment="center")
_nl.markdown('<div class="brand"><span class="logo">🔮</span>DejaOps<small>on-call memory</small></div>', unsafe_allow_html=True)
_nr.markdown(f'<div style="text-align:right"><span class="live"><i class="dot"></i>Memory bank: {esc(BANK_ID)}</span></div>', unsafe_allow_html=True)
with _bc:
    if st.button("🧠", key="brain_btn", help="Open memory graph"):
        st.session_state.page = "brain"
        st.rerun()

done = st.session_state.done
md(f'''<div class="hero"><h1>DejaOps</h1><p>The on-call agent that has seen this before.</p>
<span class="live"><i class="dot"></i>Powered by Hindsight memory</span></div>
<div class="pipe"><span class="step on">① Alert</span><span class="arrow">→</span>
<span class="step {'on' if done else ''}">② Recall</span><span class="arrow">→</span>
<span class="step {'on' if done else ''}">③ Recommend</span><span class="arrow">→</span>
<span class="step {'on' if any(st.session_state.saved.values()) else ''}">④ Learn</span></div>''')

c1, c2 = st.columns([4, 1])
with c1:
    opts = ["— Pick a demo alert —"] + [f"{a['id']}: {a['alert'][:90]}…" for a in demo]
    sel = st.selectbox("Demo", opts, label_visibility="collapsed")
    default = demo[opts.index(sel) - 1]["alert"] if sel != opts[0] else st.session_state.alert
    alert_text = st.text_area("Alert", value=default, height=110, label_visibility="collapsed",
                              placeholder="Paste a PagerDuty / Datadog / CloudWatch alert, or pick a demo above…")
with c2:
    go = st.button("🚨 Triage", type="primary", use_container_width=True)

def live_loader(title, stages, step_s, accent):
    """Client-side loader: spinner, stage checklist and a running timer (works while Python is busy)."""
    components.html(f"""
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:Inter,system-ui,sans-serif;color:#e7ebf5;background:transparent}}
.card{{position:relative;padding:1rem 1.2rem;border:1px solid rgba(255,255,255,.12);border-radius:18px;background:rgba(255,255,255,.05);overflow:hidden}}
.card:after{{content:"";position:absolute;left:0;top:0;height:3px;width:40%;background:linear-gradient(90deg,transparent,{accent},transparent);animation:sweep 1.6s linear infinite}}
@keyframes sweep{{from{{left:-40%}}to{{left:100%}}}}
.tm{{position:absolute;top:.8rem;right:1rem;font:600 .75rem Inter,sans-serif;color:#22d3ee;background:rgba(34,211,238,.1);padding:.15rem .6rem;border-radius:99px}}
.t{{font:700 .95rem 'Space Grotesk',Inter,sans-serif;margin-bottom:.7rem}}
.row{{display:flex;align-items:center;gap:.6rem;font-size:.83rem;color:#8b94ab;padding:.22rem 0}}
.row.on{{color:#fff}}.row.done{{color:#34d399}}
.ic{{width:16px;height:16px;border-radius:50%;border:2px solid #3a4258;flex:none;display:grid;place-items:center;font-size:10px}}
.row.on .ic{{border-color:{accent};border-top-color:transparent;animation:spin .8s linear infinite}}
.row.done .ic{{border-color:#34d399;background:#34d399;color:#07130e}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style>
<div class="card"><span class="tm" id="tm">⏱ 0.0s</span><div class="t">{title}</div><div id="rows"></div></div>
<script>
const S={json.dumps(stages)},STEP={step_s}*1000,t0=performance.now();
const rows=document.getElementById('rows');
rows.innerHTML=S.map((s,i)=>`<div class="row" id="r${{i}}"><span class="ic"></span>${{s}}</div>`).join('');
function tick(){{const e=performance.now()-t0;
document.getElementById('tm').textContent='⏱ '+(e/1000).toFixed(1)+'s';
const cur=Math.min(S.length-1,Math.floor(e/STEP));
S.forEach((_,i)=>{{const r=document.getElementById('r'+i);r.className='row '+(i<cur?'done':i===cur?'on':'');
r.querySelector('.ic').textContent=i<cur?'✓':'';}});}}
tick();setInterval(tick,100);
</script>""", height=80 + 28 * len(stages))

if go:
    a = alert_text.strip()
    if not looks_like_alert(a):
        st.session_state.not_alert, st.session_state.done = True, False
        st.rerun()
    st.session_state.not_alert, st.session_state.alert, st.session_state.saved = False, a, {}
    st.session_state.done = False

    LC, RC = st.columns(2, gap="large")
    with LC:
        md('<div class="colh">🤖 Without memory<span class="badge">generic · no company context</span></div>')
        live_loader("Generic AI is thinking…",
                    ["Reading the alert", "Reasoning from general knowledge", "Drafting generic fixes"], 2, "#8b94ab")
    with RC:
        md('<div class="colh">🧠 With memory<span class="badge mem">Hindsight</span></div>')
        live_loader("Searching team memory…",
                    ["Reading the alert", "Recalling past incidents", "Comparing with history",
                     "Checking deprecated runbooks", "Drafting vetted fixes"], 3, "#7c5cff")

    def timed(fn, *args):
        t0 = time.perf_counter()
        return fn(*args), time.perf_counter() - t0

    ok = False
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fp = ex.submit(timed, triage, a, False)                                    # Groq only: thread-safe
            st.session_state.res_mem, st.session_state.t_mem = timed(triage, a, True)  # Hindsight: main thread only
            st.session_state.res_plain, st.session_state.t_plain = fp.result()
        st.session_state.done, ok = True, True
    except Exception as e:
        st.error(str(e))
    if ok:
        st.rerun()

if not (st.session_state.done or st.session_state.not_alert or go):
    md('''<div class="cards"><div class="glass card"><div class="ci">🔎</div><b>Recall</b><span>Finds the past incidents that look like this alert, even when the wording is different.</span></div>
    <div class="glass card"><div class="ci">🛡️</div><b>Vet</b><span>Drops fixes that failed before and warns when a runbook is deprecated.</span></div>
    <div class="glass card"><div class="ci">📈</div><b>Learn</b><span>Mark a fix Worked or Failed and the next recommendation changes. Open the 🧠 to watch memory grow.</span></div></div>''')
if st.session_state.not_alert:
    md('''<div class="glass"><div class="lab">Needs more detail</div><div class="txt">That doesn't look like an incident
    alert. Paste the alert text (service, symptom, error message) or pick a demo alert.</div></div>''')

def fix_html(i, f, gen):
    return f'''<div class="glass fix {'gen' if gen else ''}" style="animation-delay:{i*90}ms"><div class="n">{i+1}</div>
    <div><div class="fs">{esc(f.get("step"))}</div><div class="fr">{esc(f.get("reason"))}</div></div></div>'''

if st.session_state.done:
    rp, rm = st.session_state.res_plain or {}, st.session_state.res_mem or {}
    ev, wn, fx = rm.get("evidence", []), rm.get("warnings", []), rm.get("recommended_fixes", [])
    low = not ev or any("no similar" in w.lower() for w in wn)
    lvl, pct, col = ("Low", 18, "var(--bad)") if low else (("High", 92, "var(--ok)") if len(ev) >= 3 else ("Medium", 58, "var(--warn)"))
    md(f'''<div class="tiles"><div class="glass tile"><b>{len(ev)}</b><span>past incidents recalled</span></div>
    <div class="glass tile"><b>{len([w for w in wn if 'no similar' not in w.lower()])}</b><span>warnings from history</span></div>
    <div class="glass tile"><b>{len(fx)}</b><span>vetted fixes</span></div>
    <div class="glass tile"><b>{lvl}</b><span>confidence</span><div class="bar"><i style="width:{pct}%;background:{col}"></i></div></div></div>''')
    L, R = st.columns(2, gap="large")
    with L:
        md('<div class="colh">🤖 Without memory<span class="badge">generic · no company context</span></div>')
        md(f'<div class="glass">{tm(st.session_state.t_plain)}<div class="lab">Hypothesis</div><div class="txt">{esc(rp.get("hypothesis"))}</div></div>')
        for i, f in enumerate(rp.get("recommended_fixes", [])):
            md(fix_html(i, f, True))
    with R:
        md(f'<div class="colh">🧠 With memory<span class="badge mem">Hindsight · {len(ev)} recalled</span></div>')
        md(f'<div class="glass glow">{tm(st.session_state.t_mem)}<div class="lab">Hypothesis</div><div class="txt">{esc(rm.get("hypothesis"))}</div></div>')
        for i, f in enumerate(fx):
            md(fix_html(i, f, False))
            key = f"fix_{i}"
            if not st.session_state.saved.get(key):
                b1, b2, _ = st.columns([1, 1, 3])
                for col_, label, ok in ((b1, "✅ Worked", True), (b2, "❌ Failed", False)):
                    if col_.button(label, key=f"{'w' if ok else 'f'}{i}"):
                        try:
                            record_outcome(st.session_state.alert, f.get("step", ""), ok)
                            st.session_state.saved[key] = "worked" if ok else "failed"
                            st.session_state.stale, st.session_state.graph = True, None
                            st.toast("Saved to memory")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            else:
                md(f'<span class="saved">{"✅" if st.session_state.saved[key] == "worked" else "❌"} Saved to memory</span>')
        for e in ev:
            md(f'''<div class="glass"><span class="eid">{esc(e.get("incident_id"))}</span>
            <div class="txt">{esc(e.get("summary"))}</div><div class="fr">↳ {esc(e.get("outcome"))}</div></div>''')
        for w in wn:
            md(f'<div class="warn">⚠ {esc(w)}</div>')