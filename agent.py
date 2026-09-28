import os, json, re
from dotenv import load_dotenv
from groq import Groq
from memory import recall_similar, record_outcome, learned_summary  # re-exported for the UI

load_dotenv()
groq = Groq(api_key=os.environ["GROQ_API_KEY"])
MODELS = ["openai/gpt-oss-120b", "qwen/qwen3-32b"]

JSON_SPEC = ('Reply with ONLY a JSON object, no markdown, exactly this shape: '
             '{"hypothesis": "...", "recommended_fixes": [{"step": "...", "reason": "..."}], '
             '"evidence": [{"incident_id": "INC-000", "summary": "...", "outcome": "..."}], '
             '"warnings": ["..."]}')

SYSTEM_NO_MEMORY = ("You are an on-call SRE assistant. You know nothing about this company's "
                    "history. Give a reasonable generic first response to the alert. "
                    "Leave evidence empty. " + JSON_SPEC)

SYSTEM_MEMORY = ("You are DejaOps, an on-call assistant with memory of this company's past "
                 "incidents, shown below as MEMORY.\nRules:\n"
                 "- Base your answer on MEMORY and cite incident IDs (like INC-014) in evidence.\n"
                 "- If MEMORY shows a fix FAILED before, do NOT recommend it; add a warning saying "
                 "it failed and in which incidents.\n"
                 "- If MEMORY shows a runbook is deprecated, warn and recommend its replacement.\n"
                 "- Put fixes that WORKED first and say how many times they worked.\n"
                 "- If MEMORY has no relevant past incident, say so in the hypothesis, keep "
                 "evidence empty, and add the warning 'No similar past incidents found; low confidence.'\n"
                 + JSON_SPEC)

def _extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return json.loads(text[text.find("{"): text.rfind("}") + 1])

def _ask(system, user):
    last = None
    for model in MODELS:
        for _ in range(2):
            try:
                r = groq.chat.completions.create(
                    model=model, temperature=0.2,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}])
                return _extract_json(r.choices[0].message.content)
            except Exception as e:
                last = e
    return {"hypothesis": f"Agent error: {last}", "recommended_fixes": [],
            "evidence": [], "warnings": ["LLM call failed"]}

def triage(alert_text, use_memory=True):
    if use_memory:
        mems = recall_similar(alert_text)
        block = "\n\n".join(f"[{m['type']}] {m['text']}" for m in mems) or "(nothing recalled)"
        out = _ask(SYSTEM_MEMORY, f"MEMORY:\n{block}\n\nNEW ALERT:\n{alert_text}")
    else:
        out = _ask(SYSTEM_NO_MEMORY, f"ALERT:\n{alert_text}")
    for k, d in (("hypothesis", ""), ("recommended_fixes", []), ("evidence", []), ("warnings", [])):
        out.setdefault(k, d)
    return out