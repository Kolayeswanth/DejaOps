import os, json, re
from dotenv import load_dotenv
from groq import Groq
from memory import recall_similar, record_outcome, learned_summary  # re-exported for the UI

load_dotenv(override=True)
groq = Groq(api_key=os.environ["GROQ_API_KEY"])
MODELS = ["openai/gpt-oss-120b"]

JSON_SPEC = ('Reply with ONLY a JSON object, no markdown, exactly this shape: '
             '{"hypothesis": "...", "recommended_fixes": [{"step": "...", "reason": "..."}], '
             '"evidence": [{"incident_id": "INC-000", "summary": "...", "outcome": "..."}], '
             '"warnings": ["..."], "rejected_by_memory": [{"remediation": "...", "incident_id": "INC-000", "outcome": "failed", "reason": "...", "confidence": "high"}], '
             '"memory_influence": "..."}')

SYSTEM_NO_MEMORY = ("You are an on-call SRE assistant. You know nothing about this company's "
                    "history. Give a reasonable generic first response to the alert. "
                    "Leave evidence empty. " + JSON_SPEC)

SYSTEM_MEMORY = ("You are DejaOps, an on-call assistant with memory of this company's past "
                 "incidents, shown below as MEMORY.\nRules:\n"
                 "- Base your answer on MEMORY and cite incident IDs (like INC-014) in evidence.\n"
                 "- If MEMORY shows a fix FAILED before, do NOT recommend it; add a warning saying "
                 "it failed and in which incidents.\n"
                 "- If a remediation succeeded in older incidents but a DEPRECATED or later-failed "
                 "attempt of the SAME remediation exists too, treat the deprecation/later failure as "
                 "authoritative: do not recommend it, and explain the shift in memory_influence.\n"
                 "- If MEMORY contains a previously attempted remediation that failed under similar conditions, "
                 "add a rejected_by_memory object with the failed remediation, incident ID, outcome, why it failed, "
                 "and confidence.\n"
                 "- If MEMORY shows a runbook is deprecated, warn and recommend its replacement, "
                 "but ONLY if that runbook applies to this alert's service or symptoms. "
                 "Otherwise do not mention it.\n"
                 "- Some memories are engineer feedback with no incident ID. For those use "
                 "incident_id 'FEEDBACK'. Never write UNKNOWN.\n"
                 "- Put fixes that WORKED first and say how many times they worked.\n"
                 "- Set memory_influence to one concise sentence explaining how relevant MEMORY changed "
                 "the recommendation; use an empty string when MEMORY is not relevant.\n"
                 "- If MEMORY has no relevant past incident, say so in the hypothesis, keep "
                 "evidence empty, and add the warning 'No similar past incidents found; low confidence.'\n"
                 + JSON_SPEC)

def _extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def _token_set(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    stop = {"the", "with", "from", "that", "this", "these", "those", "into", "than", "then", "when",
            "where", "how", "have", "has", "had", "were", "was", "been", "will", "would", "should",
            "could", "your", "they", "them", "their", "after", "before", "about", "against", "similar",
            "alert", "service", "incident", "memory", "failed", "worked", "restart", "restarted", "tune",
            "using", "used", "again", "issue", "problem"}
    aliases = {"restarting": "restart", "restarted": "restart", "restarts": "restart",
               "increased": "increase", "increasing": "increase", "scaling": "scale", "scaled": "scale",
               "replicas": "replica",
               "pods": "pod", "timeouts": "timeout", "services": "service",
               "four": "4", "eight": "8"}
    return {aliases.get(w, w) for w in text.split() if len(w) >= 3 and w not in stop}


def _step_similarity(a, b):
    a_tokens = _token_set(a)
    b_tokens = _token_set(b)
    if not a_tokens or not b_tokens:
        return 0.0
    union = a_tokens | b_tokens
    if not union:
        return 0.0
    return len(a_tokens & b_tokens) / len(union)


FAIL_CUES = ("failed to resolve", "did not resolve", "did not work", "was unsuccessful",
             "had no effect", "did not fix", "was ineffective", "failed.", " failed ", "failed to")
WORK_CUES = ("resolved the", "successfully resolved", "fixed the", "resolved it",
             "worked.", " worked ", "successfully")
INC_RE = re.compile(r"\bINC-\d+\b")


def _split_sentences(text):
    text = (text or "").replace("\n", " ")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\s*\|\s*", text) if s.strip()]


def _sentence_outcome(sentence):
    low = " " + sentence.lower() + " "
    if any(cue in low for cue in FAIL_CUES):
        return "failed"
    if any(cue in low for cue in WORK_CUES):
        return "worked"
    return None


def _parse_memory_actions(memory_text):
    """Best-effort extraction of (step, outcome, incident_id) triples.

    Hindsight rewrites retained text into its own sentences on recall, so this
    cannot assume the literal "- Tried: X -> WORKED" format used at retain
    time. It parses natural prose sentence by sentence and only falls back to
    the literal format for the rare case it is still present verbatim.
    """
    memory_text = memory_text or ""
    actions = []
    mem_id_match = INC_RE.search(memory_text)
    mem_incident_id = mem_id_match.group(0) if mem_id_match else None
    date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", memory_text)
    mem_date = date_match.group(1) if date_match else None

    # Legacy exact pattern: still checked in case raw retain-time text is
    # ever returned verbatim (e.g. very short memories).
    for step, outcome in re.findall(r"-\s*Tried:\s*(.+?)\s*->\s*(WORKED|FAILED)", memory_text, flags=re.I | re.S):
        actions.append({"step": step.strip(), "outcome": outcome.lower(), "reason": "",
                        "incident_id": mem_incident_id, "date": mem_date})
    for step, outcome in re.findall(r"fix\s*[\'\"](.+?)[\'\"]\s*(WORKED|FAILED)\.", memory_text, flags=re.I | re.S):
        actions.append({"step": step.strip(), "outcome": outcome.lower(),
                        "reason": "Engineer feedback recorded from a prior attempt.",
                        "incident_id": mem_incident_id, "date": mem_date})

    # Natural-language parsing: this is the path that actually matches what
    # Hindsight returns on recall.
    for sentence in _split_sentences(memory_text):
        outcome = _sentence_outcome(sentence)
        if not outcome:
            continue
        sent_id_match = INC_RE.search(sentence)
        actions.append({"step": sentence, "outcome": outcome, "reason": "",
                        "incident_id": (sent_id_match.group(0) if sent_id_match else mem_incident_id),
                        "date": mem_date})
    return actions


def build_action_provenance(memories, candidate_fixes=None):
    provenance = []
    primary_candidate = ((candidate_fixes or [])[0] or {}).get("step", "") if candidate_fixes and isinstance(candidate_fixes[0], dict) else ""
    for memory in memories or []:
        memory_text = (memory or {}).get("text") or ""
        actions = _parse_memory_actions(memory_text)
        for fix in candidate_fixes or []:
            candidate = fix.get("step", "") if isinstance(fix, dict) else str(fix)
            if not candidate:
                continue
            for action in actions:
                if not action.get("incident_id"):
                    continue
                if _step_similarity(candidate, action["step"]) < 0.16:
                    continue
                if action["outcome"] == "worked" and primary_candidate and candidate != primary_candidate:
                    continue
                item = {
                    "candidate": candidate,
                    "action": action["step"],
                    "outcome": action["outcome"],
                    "incident_id": action.get("incident_id"),
                    "source": "historical_memory",
                    "date": action.get("date"),
                    "historical_result": action.get("reason", ""),
                    "memory_text": memory_text,
                }
                if item not in provenance:
                    provenance.append(item)
    return provenance


def select_display_memories(alert_text, memories, candidate_fixes=None, limit=3):
    """Select memories with actions that support or contradict current candidates."""
    provenance = build_action_provenance(memories, candidate_fixes)
    selected_text = {item["memory_text"] for item in provenance}
    return [dict(memory, relevance_score=1)
            for memory in memories or [] if memory.get("text") in selected_text][:limit]


def detect_rejected_by_memory(alert_text, mems, candidate_fixes=None):
    candidate_fixes = candidate_fixes or []
    if not mems or not candidate_fixes:
        return []
    matches = []
    for memory in mems or []:
        mem_text = (memory or {}).get("text") or ""
        failed_steps = [a for a in _parse_memory_actions(mem_text) if a["outcome"] == "failed"]
        worked_steps = [a for a in _parse_memory_actions(mem_text) if a["outcome"] == "worked"]
        for fix in candidate_fixes:
            if isinstance(fix, dict):
                step = fix.get("step") or ""
            else:
                step = str(fix)
            if not step:
                continue
            for failed in failed_steps:
                similarity = _step_similarity(step, failed["step"])
                if similarity < 0.14:
                    continue
                mixed = any(_step_similarity(step, w["step"]) >= 0.14 for w in worked_steps)
                reason = failed.get("reason") or "Historical evidence shows this remediation failed under similar conditions."
                item = {
                    "remediation": failed["step"],
                    "incident_id": failed.get("incident_id") or "FEEDBACK",
                    "outcome": "failed",
                    "reason": reason,
                    "date": failed.get("date"),
                    "confidence": "mixed" if mixed else "high",
                }
                if item not in matches:
                    matches.append(item)
    return matches


def list_failed_actions(mems, limit=5):
    """Every distinct failed action found in the recalled memories, regardless of
    whether it overlaps with what's currently recommended.

    detect_rejected_by_memory() above only fires when a FAILED historical action
    resembles one of the model's *current* recommendations — but SYSTEM_MEMORY
    already instructs the model never to recommend something that failed before,
    so that set is nearly always empty by construction and the check rarely has
    anything to compare against. This is the fallback that actually powers the
    "rejected by memory" panel: it surfaces what was tried and failed for this
    alert's situation, independent of the current recommendation list.
    """
    seen, items = set(), []
    for memory in mems or []:
        for action in _parse_memory_actions((memory or {}).get("text") or ""):
            if action["outcome"] != "failed":
                continue
            key = (action["step"], action.get("incident_id"))
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "remediation": action["step"],
                "incident_id": action.get("incident_id") or "FEEDBACK",
                "outcome": "failed",
                "reason": "Historical evidence shows this was tried and did not resolve a similar incident.",
                "date": action.get("date"),
                "confidence": "medium",
            })
            if len(items) >= limit:
                return items
    return items


def _ask(system, user):
    errors = []

    for model in MODELS:
        for _ in range(2):
            try:
                r = groq.chat.completions.create(
                    model=model,
                    temperature=0.2,
                    messages=[
                        {
                            "role": "system",
                            "content": system + " " + NOT_ALERT
                        },
                        {
                            "role": "user",
                            "content": user
                        }
                    ]
                )
                return _extract_json(r.choices[0].message.content)

            except Exception as e:
                errors.append(f"{model}: {e}")

    return {
        "hypothesis": "Agent error: " + " | ".join(errors),
        "recommended_fixes": [],
        "evidence": [],
        "warnings": ["LLM call failed"],
        "rejected_by_memory": []
    }

def _normalize(out):
    if not isinstance(out, dict):
        out = {}
    def s(x):
        if x is None:
            return ""
        return x if isinstance(x, str) else json.dumps(x)
    fixes = []
    for f in out.get("recommended_fixes") or []:
        if isinstance(f, dict):
            fixes.append({"step": s(f.get("step")), "reason": s(f.get("reason"))})
        elif isinstance(f, str):
            fixes.append({"step": f, "reason": ""})
    evidence = []
    for e in out.get("evidence") or []:
        if isinstance(e, dict):
            evidence.append({"incident_id": s(e.get("incident_id")),
                             "summary": s(e.get("summary")),
                             "outcome": s(e.get("outcome"))})
    warnings = [s(w) for w in (out.get("warnings") or [])]
    rejected = []
    for r in out.get("rejected_by_memory") or []:
        if isinstance(r, dict):
            rejected.append({
                "remediation": s(r.get("remediation")),
                "incident_id": s(r.get("incident_id")),
                "outcome": s(r.get("outcome")),
                "reason": s(r.get("reason")),
                "confidence": s(r.get("confidence")),
            })
    return {"hypothesis": s(out.get("hypothesis")), "recommended_fixes": fixes,
            "evidence": evidence, "warnings": warnings, "rejected_by_memory": rejected,
            "memory_influence": s(out.get("memory_influence"))}


def looks_like_alert(t):
    t = (t or "").strip()
    return len(t) >= 15 and len(t.split()) >= 3

NOT_ALERT = ("If the input is not an incident alert (a greeting, a question, random text), return "
             "hypothesis \"This doesn't look like an alert.\", empty recommended_fixes and evidence, "
             "and the single warning \"Not an incident alert.\"")   

def _containment(candidate, target):
    """Fraction of candidate's own tokens that also appear in target.

    Jaccard similarity (_step_similarity) penalizes matching a short
    recommendation like "Runbook RB-15 manual TLS renewal" against a full
    prose sentence from memory like "Runbook RB-15 manual TLS renewal was
    deprecated and did not resolve incident INC-088...", because the long
    sentence's extra words dilute the intersection-over-union ratio well
    below any reasonable threshold even though every word of the short
    candidate is present. Containment (intersection over the candidate's own
    token count) is the right measure for "does this short fix restate a
    remediation described in this longer memory sentence".
    """
    a_tokens, b_tokens = _token_set(candidate), _token_set(target)
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens)


def demote_conflicting_fixes(fixes, rejected):
    """Never let a fix that memory just rejected still show up as a recommendation.

    The model is instructed not to recommend a previously-failed action, but it
    can still slip through (e.g. an older successful run of the same runbook
    outweighs a newer failure in its reasoning). This is a deterministic
    safety net: any recommended fix that closely matches a rejected
    remediation is pulled out of the recommendation list before the UI ever
    renders it, so the two panels can never contradict each other.
    """
    if not fixes or not rejected:
        return fixes, []
    rejected_steps = [r.get("remediation", "") for r in rejected if isinstance(r, dict)]
    kept, demoted = [], []
    for fix in fixes:
        step = fix.get("step", "") if isinstance(fix, dict) else str(fix)
        if any(_containment(step, rs) >= 0.6 for rs in rejected_steps):
            demoted.append(fix)
        else:
            kept.append(fix)
    return kept, demoted


def triage(alert_text, use_memory=True):
    if not looks_like_alert(alert_text):
        return {"hypothesis": "This doesn't look like an alert. Paste the alert text or pick a demo alert.",
                "recommended_fixes": [], "evidence": [],
                "warnings": ["Include the service, the symptom and any error message."],
            "rejected_by_memory": [], "recalled_memories": [], "memory_influence": ""}
    if use_memory:
        mems = recall_similar(alert_text)
        block = "\n\n".join(f"[{m['type']}] {m['text']}" for m in mems) or "(nothing recalled)"
        out = _ask(SYSTEM_MEMORY, f"MEMORY:\n{block}\n\nNEW ALERT:\n{alert_text}")
    else:
        out = _ask(SYSTEM_NO_MEMORY, f"ALERT:\n{alert_text}")
    norm = _normalize(out)
    if use_memory:
        # The LLM saw the full recalled MEMORY block and already produced its own
        # `evidence` and `rejected_by_memory`, validated by _normalize(). Those are
        # the primary source of truth for the UI. The local regex/token-overlap
        # parsing below (build_action_provenance) is best-effort enrichment on top
        # of Hindsight's own paraphrased recall text, and is used to backfill
        # rejected_by_memory only when the model didn't already supply it — never
        # to filter down evidence the model already cited correctly.
        norm["recalled_memories"] = mems
        norm["action_provenance"] = build_action_provenance(mems, norm.get("recommended_fixes", []))
        if not norm.get("rejected_by_memory"):
            norm["rejected_by_memory"] = detect_rejected_by_memory(alert_text, mems, norm.get("recommended_fixes", []))
        if not norm.get("rejected_by_memory"):
            norm["rejected_by_memory"] = list_failed_actions(mems)
        norm["recommended_fixes"], demoted = demote_conflicting_fixes(
            norm.get("recommended_fixes", []), norm["rejected_by_memory"])
        for fix in demoted:
            step = fix.get("step", "") if isinstance(fix, dict) else str(fix)
            norm["warnings"].append(
                f"Removed from recommendations: \"{step}\" matches a remediation memory has already rejected.")
        # display_memories/display_evidence used to be filtered down to only what
        # the local parser could match, which silently hid correct LLM evidence
        # whenever Hindsight's recall wording didn't fit the parser's patterns.
        # They now default to everything the model actually used.
        norm["display_memories"] = mems
        norm["display_evidence"] = norm.get("evidence", [])
    else:
        norm["recalled_memories"] = []
        norm["display_memories"] = []
        norm["display_evidence"] = []
        norm["action_provenance"] = []
    return norm