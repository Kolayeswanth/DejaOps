"""DejaOps brain view: builds a memory graph from Hindsight and renders an animated,
zoomable cluster explorer (D3 inside a Streamlit component)."""
import json, re
from collections import Counter
import streamlit as st
import streamlit.components.v1 as components
from memory import client, BANK_ID

STOP = set("""the and for with from that this these those into than then not never use used using after
before which who what when where how has have had did done can will would should could their they them
our you your incident service alert logs log root cause actions action taken tried resolved minutes
runbook postmortem engineer feedback fix fixes worked failed on was were been are its""".split())

QUERIES = ["incident root cause and resolution", "runbook deprecated or replaced",
           "fix that worked", "fix that failed", "database connection pool exhaustion",
           "latency and error rate alert", "engineer feedback outcome", "payments service"]


def _get(r, k):
    return r.get(k) if isinstance(r, dict) else getattr(r, k, None)


def _fetch():
    """Get stored memories. Tries a direct listing first, falls back to broad recalls."""
    mems, seen = [], set()

    def add(text, typ, mid=None):
        text = (text or "").strip()
        if text and text not in seen:
            seen.add(text)
            mems.append({"id": f"m{len(mems)}", "text": text, "type": str(typ or "memory")})

    try:
        res = client.list_memories(bank_id=BANK_ID, limit=300)
        rows = _get(res, "items") or _get(res, "results") or []
        for r in rows:
            add(_get(r, "text") or _get(r, "content"), _get(r, "fact_type") or _get(r, "type"))
    except Exception:
        pass
    if len(mems) < 8:
        for q in QUERIES:
            try:
                res = client.recall(bank_id=BANK_ID, query=q, max_tokens=2000, budget="low")
                for r in res.results:
                    add(r.text, getattr(r, "type", None))
            except Exception:
                continue
    return mems


def _tok(t):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]{2,}", t.lower()) if w not in STOP}


def _label(t):
    m = re.search(r"\b[A-Z]{2,5}-\d+\b", t)
    if m:
        return m.group(0)
    w = [x for x in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", t) if x.lower() not in STOP]
    return " ".join(w[:2]).title() or "Memory"


def _status(t):
    """worked / failed / mixed / deprecated, read from the stored memory text."""
    low = t.lower()
    if "deprecated" in low and "runbook" in low:
        return "deprecated"
    bad = re.search(r"\b(failed|fails|did not work|didn't work|ineffective|made it worse)\b", low)
    good = re.search(r"\b(worked|succeeded|fixed it)\b", low)
    if bad and good:
        return "mixed"
    return "failed" if bad else ("worked" if good else "")


def mark_hot(data, evidence):
    """Map the last triage's recalled evidence onto graph node ids."""
    hot = set()
    for e in evidence or []:
        e = e or {}
        iid = str(e.get("incident_id") or "").strip()
        summ = _tok(str(e.get("summary") or ""))
        hits = [n["id"] for n in data["nodes"] if iid and iid in n["text"]]
        if not hits and summ:
            sc = [(len(summ & _tok(n["text"])) / len(summ | _tok(n["text"])), n["id"]) for n in data["nodes"]]
            sc = [s for s in sc if s[0] >= 0.2]
            if sc:
                hits = [max(sc)[1]]
        hot.update(hits)
    return sorted(hot)


def build_graph():
    mems = _fetch()
    n = len(mems)
    toks = [_tok(m["text"]) for m in mems]
    tags = [set(re.findall(r"\b[A-Z]{2,5}-\d+\b", m["text"])) for m in mems]
    sims = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            u = toks[i] | toks[j]
            if not u:
                continue
            w = len(toks[i] & toks[j]) / len(u) + (0.25 if tags[i] & tags[j] else 0)
            if w > 0.03:
                sims[i].append((j, w))
                sims[j].append((i, w))
    best = {i: sorted(sims[i], key=lambda x: -x[1]) for i in range(n)}

    links = {(min(i, j), max(i, j)): round(w, 3) for i in range(n) for j, w in best[i][:4]}

    # cluster: every memory joins its closest neighbour (union-find), singletons get adopted
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        if best[i] and best[i][0][1] >= 0.10:
            parent[find(i)] = find(best[i][0][0])
    comp = {}
    for i in range(n):
        comp.setdefault(find(i), []).append(i)
    groups = list(comp.values())
    cid = {i: k for k, ms in enumerate(groups) for i in ms}
    for k, ms in enumerate(groups):
        if len(ms) == 1 and best[ms[0]] and len(groups[cid[best[ms[0]][0][0]]]) > 1:
            cid[ms[0]] = cid[best[ms[0]][0][0]]
    remap = {old: new for new, old in enumerate(sorted(set(cid.values())))}

    clusters = []
    for old, new in remap.items():
        members = [i for i in range(n) if cid[i] == old]
        cnt = Counter(w for i in members for w in toks[i] if not w.isdigit())
        label = " · ".join(w.title() for w, _ in cnt.most_common(2)) or "Memories"
        clusters.append({"id": new, "label": label, "count": len(members)})

    nodes = [{"id": m["id"], "label": _label(m["text"]), "text": m["text"],
              "type": m["type"], "status": _status(m["text"]), "c": remap[cid[i]]}
             for i, m in enumerate(mems)]
    lk = [{"s": mems[i]["id"], "t": mems[j]["id"], "w": w} for (i, j), w in links.items()]
    return {"nodes": nodes, "clusters": clusters, "links": lk}


def graph_html(data, hot=None, height=720):
    payload = json.dumps({**data, "hot": hot or []}).replace("</", "<\\/")
    return HTML.replace("__DATA__", payload).replace("__H__", str(height))


def render_brain_page(learned_summary, retain_postmortem=None, evidence=None):
    st.markdown("""<style>
    .st-key-back_home button,.st-key-rebuild button{border-radius:12px}
    </style>""", unsafe_allow_html=True)
    a, b, c = st.columns([1.2, 6, 1.4], vertical_alignment="center")
    if a.button("← Back", key="back_home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
    b.markdown(f"""<div class="hero" style="padding:.2rem 0"><h1 style="font-size:2.4rem">Memory Graph</h1>
    <p style="margin:.1rem 0 .4rem">Click a cluster to zoom in · click a memory to see its nearest neighbours</p>
    <span class="live"><i class="dot"></i>Memory bank: {BANK_ID}</span></div>""", unsafe_allow_html=True)
    if c.button("🔄 Rebuild", key="rebuild", use_container_width=True):
        st.session_state.graph = None

    if st.session_state.get("graph") is None:
        with st.spinner("Mapping memories into clusters…"):
            try:
                st.session_state.graph = build_graph()
            except Exception as e:
                st.error(f"Could not load memory graph: {e}")
                return
    hot = mark_hot(st.session_state.graph, evidence)
    if hot:
        st.caption(f"★ {len(hot)} memories recalled by your last triage are highlighted in pink.")
    components.html(graph_html(st.session_state.graph, hot), height=735, scrolling=False)

    t1, t2 = st.tabs(["🧠 What DejaOps has learned", "📝 Teach a postmortem"])
    with t1:
        if st.button("Refresh summary", key="refresh"):
            with st.spinner("Reflecting on past incidents..."):
                try:
                    st.session_state.summary, st.session_state.stale = learned_summary(), False
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get("stale"):
            st.caption("Memory updated - refresh the summary and rebuild the graph")
        st.markdown(st.session_state.get("summary") or "Click Refresh to load")
    with t2:
        if retain_postmortem:
            pm = st.text_area("Postmortem", key="pm_text", height=140)
            if st.button("Teach DejaOps", key="pm_btn"):
                if not pm.strip():
                    st.warning("Paste a postmortem first.")
                else:
                    try:
                        retain_postmortem(pm.strip())
                        st.toast("Learned - rebuilding the graph")
                        st.session_state.stale, st.session_state.graph = True, None; st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.info("retain_postmortem is not available in memory.py")


HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
:root{--bg:#070a13;--line:rgba(255,255,255,.09);--txt:#e7ebf5;--mut:#8b94ab;--cy:#22d3ee;--vio:#7c5cff;--pink:#ff5c9d}
*{box-sizing:border-box}html,body{margin:0;background:transparent;font-family:Inter,system-ui,sans-serif;color:var(--txt)}
#stage{position:relative;height:__H__px;border:1px solid var(--line);border-radius:22px;overflow:hidden;
 background:radial-gradient(40rem 26rem at 20% 0%,rgba(124,92,255,.25),transparent 60%),
 radial-gradient(36rem 24rem at 100% 100%,rgba(34,211,238,.16),transparent 60%),#0a0e1a;
 box-shadow:0 20px 60px rgba(0,0,0,.45)}
#stage:before{content:"";position:absolute;inset:0;opacity:.12;pointer-events:none;
 background-image:linear-gradient(#fff 1px,transparent 1px),linear-gradient(90deg,#fff 1px,transparent 1px);background-size:44px 44px}
svg{position:absolute;inset:0;width:100%;height:100%;cursor:grab}svg:active{cursor:grabbing}
.spark{position:absolute;width:3px;height:3px;border-radius:50%;background:#fff;opacity:.0;animation:tw 6s infinite}
@keyframes tw{0%,100%{opacity:0;transform:translateY(0)}50%{opacity:.5;transform:translateY(-16px)}}
.halo{animation:pulse 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes pulse{0%,100%{transform:scale(1);opacity:.07}50%{transform:scale(1.08);opacity:.16}}
.dot,.aura{animation:bob 6s ease-in-out infinite}
@keyframes bob{0%,100%{transform:translate(0,0)}50%{transform:translate(2px,-3px)}}
.bl{fill:#fff;font:700 15px 'Space Grotesk',Inter,sans-serif;pointer-events:none;paint-order:stroke;stroke:#0a0e1a;stroke-width:4px}
.bn{fill:var(--mut);font:500 11px Inter,sans-serif;pointer-events:none}
.nl{fill:#dbe2f3;font:600 10.5px Inter,sans-serif;pointer-events:none;paint-order:stroke;stroke:#0a0e1a;stroke-width:3px}
.lk{fill:none;stroke:#8ea2ff;stroke-linecap:round}
.lk.flow{stroke:var(--cy);stroke-dasharray:7 7;animation:flow 1s linear infinite}
@keyframes flow{to{stroke-dashoffset:-14}}
#hud{position:absolute;left:16px;top:14px;display:flex;gap:.5rem;align-items:center;padding:.4rem .8rem;border:1px solid var(--line);
 border-radius:99px;background:rgba(13,17,32,.7);backdrop-filter:blur(10px);font-size:.78rem;z-index:3}
#hud a{color:var(--cy);cursor:pointer}#hud i{color:var(--mut);font-style:normal}#hud b{color:#fff}
#hint{position:absolute;left:16px;bottom:14px;font-size:.72rem;color:var(--mut);z-index:3}
#panel{position:absolute;right:14px;top:14px;bottom:14px;width:310px;padding:1.1rem;border:1px solid var(--line);border-radius:18px;
 background:rgba(12,16,30,.82);backdrop-filter:blur(16px);overflow-y:auto;transform:translateX(120%);opacity:0;
 transition:transform .7s cubic-bezier(.2,.8,.2,1),opacity .5s;z-index:4}
#panel.open{transform:none;opacity:1}
#panel::-webkit-scrollbar{width:5px}#panel::-webkit-scrollbar-thumb{background:rgba(255,255,255,.15);border-radius:9px}
.pill{display:inline-block;padding:.15rem .6rem;border-radius:99px;font-size:.66rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
 background:rgba(255,255,255,.08);color:var(--c,var(--cy));border:1px solid var(--c,var(--cy))}
h2{font:700 1.35rem 'Space Grotesk',Inter,sans-serif;margin:.6rem 0 .2rem}
.sub{color:var(--mut);font-size:.8rem;margin:0 0 .8rem}
.full{font-size:.85rem;line-height:1.6;color:#d5dbea;margin:.2rem 0 1rem;animation:up .5s both}
.sec{font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:var(--cy);font-weight:700;margin:1rem 0 .5rem}
.item,.nn{display:flex;gap:.65rem;padding:.6rem .7rem;margin-bottom:.45rem;border:1px solid var(--line);border-radius:12px;
 background:rgba(255,255,255,.04);cursor:pointer;transition:.25s;animation:up .5s both}
.item:hover,.nn:hover{border-color:var(--vio);transform:translateX(-3px);background:rgba(124,92,255,.12)}
.item b,.nn b{font-size:.82rem;display:block}.item small,.nn small{color:var(--mut);font-size:.72rem;line-height:1.4;display:block}
.rank{flex:none;width:26px;height:26px;border-radius:8px;display:grid;place-items:center;font-size:.72rem;font-weight:700;
 background:linear-gradient(135deg,var(--vio),var(--cy));color:#fff}
.sw{flex:none;width:10px;height:10px;border-radius:50%;margin-top:.25rem;background:var(--c)}
.mbar,.tbar{height:5px;border-radius:9px;background:rgba(255,255,255,.08);margin-top:.4rem;overflow:hidden}
.mbar i,.tbar i{display:block;height:100%;border-radius:9px;background:linear-gradient(90deg,var(--vio),var(--cy));animation:grow 1s both}
.trow{font-size:.75rem;color:var(--mut);margin-bottom:.5rem;display:flex;justify-content:space-between}
.back{width:100%;margin-top:.6rem;padding:.55rem;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.05);color:#fff;
 font-weight:600;cursor:pointer;transition:.25s}.back:hover{border-color:var(--cy);box-shadow:0 6px 22px rgba(34,211,238,.25)}
.ripple{fill:none;stroke:#ff5c9d;stroke-width:2;transform-box:fill-box;transform-origin:center;animation:rip 2s ease-out infinite;pointer-events:none}
@keyframes rip{0%{transform:scale(.6);opacity:.95}100%{transform:scale(2.4);opacity:0}}
.badgepulse{transform-box:fill-box;transform-origin:center;animation:bp 2.2s ease-in-out infinite}
@keyframes bp{0%,100%{transform:scale(1)}50%{transform:scale(1.15)}}
#rec{display:none;margin-left:.4rem;padding:.2rem .7rem;border-radius:99px;border:1px solid #ff5c9d;background:rgba(255,92,157,.15);color:#fff;font-weight:600;font-size:.72rem;cursor:pointer}
#rec:hover{background:rgba(255,92,157,.35)}
.pill{margin-right:.3rem}
.lg{margin-right:.9rem}.lg i{display:inline-block;width:9px;height:9px;border-radius:50%;border:2px solid;margin-right:.35rem;vertical-align:-1px}
.lg i.rp{border-color:#ff5c9d;box-shadow:0 0 8px #ff5c9d}
#empty{position:absolute;inset:0;display:none;place-items:center;text-align:center;color:var(--mut);z-index:5}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes grow{from{width:0}}
</style></head><body>
<div id="stage">
  <svg id="svg"></svg>
  <div id="hud"><span id="crumb"></span><button id="rec"></button></div>
  <div id="hint"><span class="lg"><i style="border-color:#34d399"></i>worked</span><span class="lg"><i style="border-color:#fb7185"></i>failed</span><span class="lg"><i style="border-color:#94a3b8"></i>deprecated</span><span class="lg"><i class="rp"></i>recalled by last triage</span>· scroll to zoom · drag to pan</div>
  <div id="panel"></div>
  <div id="empty"><div><div style="font-size:3rem">🧠</div>No memories yet.<br>Teach DejaOps a postmortem, then hit Rebuild.</div></div>
</div>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const stage = $('#stage'), W = stage.clientWidth || 1000, H = stage.clientHeight || 720, PW = 340;
const PAL = ['#7c5cff','#22d3ee','#ff5c9d','#34d399','#fbbf24','#fb7185','#60a5fa','#a78bfa'];
const TYPE = {world:'#22d3ee', experience:'#ff5c9d', opinion:'#fbbf24', observation:'#34d399'};
const tcol = t => TYPE[String(t).toLowerCase()] || '#a78bfa';
const STATUS = {worked:'#34d399', failed:'#fb7185', mixed:'#fbbf24', deprecated:'#94a3b8'};
const SLBL = {worked:'✅ Worked', failed:'❌ Failed', mixed:'⚠ Mixed results', deprecated:'🚫 Deprecated'};
const hot = new Set(D.hot || []);

for (let i = 0; i < 28; i++) { const s = document.createElement('i'); s.className = 'spark';
  s.style.cssText = `left:${Math.random()*100}%;top:${Math.random()*100}%;animation-delay:${Math.random()*6}s`; stage.appendChild(s); }

if (!D.nodes.length) { $('#empty').style.display = 'grid'; }
else {
const svg = d3.select('#svg').attr('viewBox', [0, 0, W, H]);
const defs = svg.append('defs');
const glow = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
glow.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'b');
glow.append('feMerge').selectAll('feMergeNode').data(['b', 'SourceGraphic']).join('feMergeNode').attr('in', d => d);
const g = svg.append('g'), gI = g.append('g'), gL = g.append('g'), gB = g.append('g'), gN = g.append('g');
const zoom = d3.zoom().scaleExtent([.3, 6]).on('zoom', e => g.attr('transform', e.transform));
svg.call(zoom).on('dblclick.zoom', null);

const cl = new Map(D.clusters.map((c, i) => [c.id, c]));
const K = D.clusters.length;
D.clusters.forEach((c, i) => { c.col = PAL[i % PAL.length];
  const a = 2 * Math.PI * i / K - Math.PI / 2;
  c.cx = K === 1 ? W / 2 : W / 2 + W * .27 * Math.cos(a); c.cy = K === 1 ? H / 2 : H / 2 + H * .28 * Math.sin(a);
  const rg = defs.append('radialGradient').attr('id', 'g' + c.id);
  rg.append('stop').attr('offset', '0%').attr('stop-color', c.col).attr('stop-opacity', .35);
  rg.append('stop').attr('offset', '100%').attr('stop-color', c.col).attr('stop-opacity', .05); });

const byId = new Map(D.nodes.map(n => [n.id, n]));
const nb = new Map(D.nodes.map(n => [n.id, []]));
D.links.forEach(l => { nb.get(l.s).push({id: l.t, w: l.w}); nb.get(l.t).push({id: l.s, w: l.w}); });
nb.forEach(a => a.sort((x, y) => y.w - x.w));
const top = n => nb.get(n.id).slice(0, 3);
const simLinks = D.links.map(l => ({source: l.s, target: l.t, w: l.w}));

D.nodes.forEach(n => { const c = cl.get(n.c); n.x = c.cx + (Math.random() - .5) * 50; n.y = c.cy + (Math.random() - .5) * 50;
  n.r = 7 + Math.min(6, nb.get(n.id).length * 1.5); n.col = cl.get(n.c).col; });
const sim = d3.forceSimulation(D.nodes)
  .force('link', d3.forceLink(simLinks).id(d => d.id).strength(l => Math.min(.5, l.w * .3)).distance(80))
  .force('x', d3.forceX(n => cl.get(n.c).cx).strength(.14)).force('y', d3.forceY(n => cl.get(n.c).cy).strength(.14))
  .force('charge', d3.forceManyBody().strength(-70)).force('collide', d3.forceCollide(n => n.r + 20)).stop();
for (let i = 0; i < 400; i++) sim.tick();

D.clusters.forEach(c => { const ms = D.nodes.filter(n => n.c === c.id);
  c.x = d3.mean(ms, n => n.x); c.y = d3.mean(ms, n => n.y);
  c.r = Math.max(48, d3.max(ms, n => Math.hypot(n.x - c.x, n.y - c.y)) + 38); c.ms = ms; });

// inter-cluster ghost lines
const pair = new Map();
D.links.forEach(l => { const a = byId.get(l.s).c, b = byId.get(l.t).c; if (a === b) return;
  const k = Math.min(a, b) + '-' + Math.max(a, b); pair.set(k, (pair.get(k) || 0) + 1); });
const ghost = gI.selectAll('line').data([...pair]).join('line')
  .attr('x1', d => cl.get(+d[0].split('-')[0]).x).attr('y1', d => cl.get(+d[0].split('-')[0]).y)
  .attr('x2', d => cl.get(+d[0].split('-')[1]).x).attr('y2', d => cl.get(+d[0].split('-')[1]).y)
  .attr('stroke', '#8ea2ff').attr('stroke-opacity', .22).attr('stroke-width', d => 1 + d[1]).attr('stroke-dasharray', '4 8').attr('class', 'lk flow');

const link = gL.selectAll('path').data(simLinks).join('path').attr('class', 'lk')
  .attr('d', l => `M${l.source.x},${l.source.y}L${l.target.x},${l.target.y}`).attr('stroke-width', l => 1 + l.w * 4).style('opacity', 0);

const bub = gB.selectAll('g').data(D.clusters).join('g').attr('transform', c => `translate(${c.x},${c.y})`)
  .style('cursor', 'pointer').on('click', (e, c) => { e.stopPropagation(); focusCluster(c); });
bub.append('circle').attr('class', 'halo').attr('r', c => c.r + 18).attr('fill', c => c.col);
bub.append('circle').attr('r', c => c.r).attr('fill', c => `url(#g${c.id})`).attr('stroke', c => c.col).attr('stroke-opacity', .55).attr('stroke-width', 1.5);
bub.append('text').attr('class', 'bl').attr('text-anchor', 'middle').attr('y', c => -c.r - 8).text(c => c.label);
bub.append('text').attr('class', 'bn').attr('text-anchor', 'middle').attr('y', c => -c.r + 8).text(c => c.count + ' memories');
const bb = bub.filter(c => c.ms.some(n => hot.has(n.id))).append('g').attr('transform', c => `translate(${c.r * .72},${-c.r * .72})`);
bb.append('circle').attr('r', 15).attr('fill', '#ff5c9d').attr('class', 'badgepulse');
bb.append('text').attr('text-anchor', 'middle').attr('dy', '.35em').attr('fill', '#fff').style('font', '700 11px Inter').style('pointer-events', 'none')
  .text(c => '★' + c.ms.filter(n => hot.has(n.id)).length);

const node = gN.selectAll('g').data(D.nodes).join('g').attr('transform', n => `translate(${n.x},${n.y})`)
  .style('cursor', 'pointer').style('pointer-events', 'none').on('click', (e, n) => { e.stopPropagation(); focusNode(n); });
node.append('circle').attr('class', 'aura').attr('r', n => n.r + 10).attr('fill', n => n.col).attr('opacity', .18)
  .style('animation-delay', () => -Math.random() * 6 + 's');
node.filter(n => hot.has(n.id)).append('circle').attr('class', 'ripple').attr('r', n => n.r + 4);
node.append('circle').attr('class', 'dot').attr('r', 3.5).attr('fill', n => n.col)
  .attr('stroke', n => STATUS[n.status] || '#fff').attr('stroke-width', n => n.status ? 2.8 : 1.6)
  .attr('filter', 'url(#glow)').style('animation-delay', () => -Math.random() * 6 + 's');
node.append('text').attr('class', 'nl').attr('text-anchor', 'middle').attr('y', n => n.r + 17).text(n => n.label).style('opacity', 0);

let state = {level: 'all'};
function render() {
  const s = state, vis = new Set(), foc = new Set();
  if (s.level === 'cluster') s.c.ms.forEach(n => vis.add(n.id));
  if (s.level === 'node') { foc.add(s.n.id); vis.add(s.n.id);
    top(s.n).forEach(x => { foc.add(x.id); vis.add(x.id); }); cl.get(s.n.c).ms.forEach(n => vis.add(n.id)); }
  const T = 700;
  node.style('pointer-events', n => s.level !== 'all' && vis.has(n.id) ? 'all' : 'none')
    .transition().duration(T).style('opacity', n => s.level === 'all' ? .95 : foc.size ? (foc.has(n.id) ? 1 : vis.has(n.id) ? .25 : .05) : vis.has(n.id) ? 1 : .05);
  node.select('.dot').transition().duration(T).attr('r', n => s.level === 'all' ? (hot.has(n.id) ? 5.5 : 3.5) : vis.has(n.id) ? n.r + (s.n && s.n.id === n.id ? 4 : 0) : 3);
  node.select('.aura').transition().duration(T).attr('r', n => s.level === 'all' ? 9 : n.r + 10);
  node.select('text').transition().duration(T).style('opacity', n => s.level === 'all' ? 0 : foc.size ? (foc.has(n.id) ? 1 : 0) : vis.has(n.id) ? 1 : 0);
  link.style('stroke', l => hot.has(l.source.id) && hot.has(l.target.id) ? '#ff5c9d' : null);
  link.classed('flow', l => s.level === 'node' && foc.has(l.source.id) && foc.has(l.target.id) && (l.source.id === s.n.id || l.target.id === s.n.id))
    .transition().duration(T).style('opacity', l => {
      if (s.level === 'all') return 0;
      const a = l.source.id, b = l.target.id;
      if (s.level === 'node') return (a === s.n.id || b === s.n.id) && foc.has(a) && foc.has(b) ? .95 : vis.has(a) && vis.has(b) ? .12 : 0;
      return vis.has(a) && vis.has(b) ? .35 : 0; });
  bub.style('pointer-events', s.level === 'all' ? 'all' : (s.level === 'cluster' ? 'all' : 'none'))
    .transition().duration(T).style('opacity', c => s.level === 'all' ? 1 : s.level === 'cluster' ? (c.id === s.c.id ? 0 : .3) : .06);
  ghost.transition().duration(T).style('opacity', s.level === 'all' ? 1 : 0);
  $('#panel').classList.toggle('open', s.level !== 'all');
  crumb();
}
function zoomTo(x, y, k, panel = true) {
  const cx = panel ? (W - PW) / 2 : W / 2;
  svg.transition().duration(1100).ease(d3.easeCubicInOut)
    .call(zoom.transform, d3.zoomIdentity.translate(cx, H / 2).scale(k).translate(-x, -y)); }
function focusAll() { state = {level: 'all'}; zoomTo(W / 2, H / 2, 1, false); render(); }
function focusCluster(c) {
  state = {level: 'cluster', c};
  const xs = c.ms.map(n => n.x), ys = c.ms.map(n => n.y);
  const bw = Math.max(120, d3.max(xs) - d3.min(xs) + 120), bh = Math.max(120, d3.max(ys) - d3.min(ys) + 120);
  zoomTo((d3.max(xs) + d3.min(xs)) / 2, (d3.max(ys) + d3.min(ys)) / 2, Math.min(2.6, .9 * Math.min((W - PW) / bw, H / bh)));
  render(); panelCluster(c); }
function focusNode(n) {
  state = {level: 'node', n, c: cl.get(n.c)};
  const t = top(n).map(x => byId.get(x.id)), all = [n, ...t];
  const xs = all.map(a => a.x), ys = all.map(a => a.y);
  const bw = d3.max(xs) - d3.min(xs) + 220, bh = d3.max(ys) - d3.min(ys) + 220;
  zoomTo((d3.max(xs) + d3.min(xs)) / 2, (d3.max(ys) + d3.min(ys)) / 2, Math.min(2.8, .9 * Math.min((W - PW) / bw, H / bh)));
  render(); panelNode(n); }
function goBack() { state.level === 'node' ? focusCluster(state.c) : focusAll(); }
svg.on('click', () => { if (state.level !== 'all') goBack(); });

function crumb() {
  let h = `<a data-a="all">All memory</a>`;
  if (state.c) h += ` <i>›</i> <a data-a="cluster">${esc(state.c.label)}</a>`;
  if (state.n) h += ` <i>›</i> <b>${esc(state.n.label)}</b>`;
  $('#crumb').innerHTML = h;
  $('#crumb').querySelectorAll('a').forEach(a => a.onclick = () => a.dataset.a === 'all' ? focusAll() : focusCluster(state.c)); }
function bindList() {
  $('#panel').querySelectorAll('[data-id]').forEach(el => el.onclick = () => focusNode(byId.get(el.dataset.id)));
  const b = $('#panel .back'); if (b) b.onclick = goBack; }
function panelCluster(c) {
  const tc = {}; c.ms.forEach(n => tc[n.type] = (tc[n.type] || 0) + 1);
  $('#panel').style.setProperty('--c', c.col);
  $('#panel').innerHTML = `<span class="pill" style="--c:${c.col}">Cluster</span><h2>${esc(c.label)}</h2>
   <p class="sub">${c.ms.length} related memories</p>
   ${Object.entries(tc).map(([t, v]) => `<div class="trow"><span>${esc(t)}</span><span>${v}</span></div>
     <div class="tbar" style="margin:-.3rem 0 .6rem"><i style="width:${v / c.ms.length * 100}%"></i></div>`).join('')}
   <div class="sec">Memories in this cluster</div>
   ${c.ms.map((n, i) => `<div class="item" data-id="${n.id}" style="--c:${c.col};animation-delay:${i * 50}ms"><span class="sw"></span>
     <div><b>${hot.has(n.id) ? '★ ' : ''}${esc(n.label)}</b><small>${esc(n.text.slice(0, 95))}…</small></div></div>`).join('')}
   <button class="back">↩ Zoom out</button>`;
  bindList(); }
function panelNode(n) {
  const t = top(n), mx = Math.max(.001, ...t.map(x => x.w));
  $('#panel').innerHTML = `<span class="pill" style="--c:${tcol(n.type)}">${esc(n.type)}</span>
   ${n.status ? `<span class="pill" style="--c:${STATUS[n.status]}">${SLBL[n.status]}</span>` : ''}
   ${hot.has(n.id) ? `<span class="pill" style="--c:#ff5c9d">★ Recalled</span>` : ''}<h2>${esc(n.label)}</h2>
   <p class="sub">in cluster · ${esc(cl.get(n.c).label)}</p><p class="full">${esc(n.text)}</p>
   <div class="sec">Nearest memories</div>
   ${t.length ? t.map((x, i) => { const m = byId.get(x.id); return `<div class="nn" data-id="${m.id}" style="animation-delay:${i * 90}ms">
     <span class="rank">#${i + 1}</span><div style="flex:1"><b>${esc(m.label)}</b><small>${esc(m.text.slice(0, 110))}…</small>
     <div class="mbar"><i style="width:${Math.max(12, x.w / mx * 100)}%"></i></div></div></div>`; }).join('')
     : '<p class="sub">No close neighbours yet.</p>'}
   <button class="back">↩ Back to cluster</button>`;
  bindList(); }

const hotNodes = D.nodes.filter(n => hot.has(n.id)); let hi = 0;
if (hotNodes.length) { const rec = $('#rec'); rec.style.display = 'inline-block';
  rec.textContent = '★ Recalled (' + hotNodes.length + ')';
  rec.onclick = e => { e.stopPropagation(); focusNode(hotNodes[hi++ % hotNodes.length]); }; }
// intro: zoom-in reveal
g.style('opacity', 0).transition().duration(1400).style('opacity', 1);
svg.call(zoom.transform, d3.zoomIdentity.translate(W * .2, H * .2).scale(.6));
svg.transition().duration(1400).ease(d3.easeCubicOut).call(zoom.transform, d3.zoomIdentity);
render();
}
</script></body></html>"""