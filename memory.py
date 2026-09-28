import os
from datetime import datetime
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()
BANK_ID = os.getenv("DEJAOPS_BANK", "dev-test")
client = Hindsight(base_url=os.environ["HINDSIGHT_URL"],
                   api_key=os.environ["HINDSIGHT_API_KEY"], timeout=90.0)

def init_bank():
    try:
        client.create_bank(
            bank_id=BANK_ID, name="DejaOps On-Call Memory",
            mission=("I am DejaOps, an on-call assistant for Northwind Payments. I track "
                     "incidents, which fixes worked or failed for each pattern, and which "
                     "runbooks are deprecated. I never recommend a fix that failed before."),
            disposition={"skepticism": 4, "literalism": 4, "empathy": 2})
    except Exception as e:
        print("create_bank skipped (may already exist):", e)

def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def incident_text(inc):
    acts = "\n".join(f"- Tried: {a['step']} -> {a['result'].upper()}" for a in inc["actions"])
    return (f"Incident {inc['id']} on {inc['date']} | service {inc['service']} | {inc['severity']}\n"
            f"Alert: {inc['alert']}\nLogs: {inc['logs'][:800]}\nRoot cause: {inc['root_cause']}\n"
            f"Actions taken:\n{acts}\n"
            f"Resolved in {inc['resolution_minutes']} minutes using runbook {inc['runbook']}.\n"
            f"Postmortem: {inc['postmortem']}")

def retain_incident(inc):
    client.retain(bank_id=BANK_ID, content=incident_text(inc), context="incident postmortem",
                  timestamp=_ts(inc["date"]), document_id=inc["id"], retain_async=False)

def retain_runbook(rb):
    text = f"Runbook {rb['id']}: {rb['title']}. Status: {rb['status'].upper()}."
    if rb["status"] == "deprecated":
        text += (f" It was DEPRECATED on {rb['deprecated_on']} and replaced by {rb['replaced_by']}."
                 f" Reason: {rb.get('reason', '')} Do not use {rb['id']}.")
    text += " Steps: " + " ".join(rb["steps"])
    d = rb.get("deprecated_on") or rb.get("effective_from")
    kw = {"timestamp": _ts(d + "T00:00:00Z")} if d else {}
    client.retain(bank_id=BANK_ID, content=text, context="runbook", document_id=rb["id"],
                  retain_async=False, **kw)

def recall_similar(alert_text):
    seen, out = set(), []
    for q in (alert_text,
              f"Which runbooks apply here and are any deprecated or replaced? {alert_text[:300]}"):
        res = client.recall(bank_id=BANK_ID, query=q, max_tokens=3000, budget="mid")
        for r in res.results:
            if r.text not in seen:
                seen.add(r.text)
                out.append({"type": r.type, "text": r.text})
    return out

def record_outcome(alert_text, fix, worked):
    verdict = "WORKED" if worked else "FAILED"
    client.retain(bank_id=BANK_ID,
                  content=(f"Engineer feedback on {datetime.now().isoformat(timespec='minutes')}: "
                           f"for the alert '{alert_text[:400]}', the fix '{fix}' {verdict}."),
                  context="outcome feedback", timestamp=datetime.now(), retain_async=False)

def learned_summary():
    ans = client.reflect(
        bank_id=BANK_ID, budget="mid",
        query=("In up to 5 short bullets, summarize ONLY what is actually stored in this memory "
               "bank: which fixes worked or failed for each recurring incident pattern, and which "
               "runbooks are deprecated. Use only stored facts and the exact incident and runbook "
               "IDs from memory. If the bank has little or no relevant information, reply exactly: "
               "Not enough memory yet. Never invent IDs, dates or runbooks."))
    return ans.text