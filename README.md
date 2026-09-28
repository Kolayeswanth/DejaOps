# DejaOps

**The on-call agent that has seen this before.**

DejaOps is an incident-response assistant with long-term memory, built on [Hindsight](https://github.com/vectorize-io/hindsight). Paste an alert and it shows two answers side by side: what a generic LLM would say, and what DejaOps says after recalling your team's past incidents, failed fixes and outdated runbooks. Mark a fix as **Worked** or **Failed** and the next recommendation changes.

- Demo video: `[ADD YOUR YOUTUBE LINK]`
- Team: `[ADD NAMES]`

## The problem

On-call engineers keep re-solving incidents their team has already solved. The knowledge lives in old tickets, postmortems and Slack threads, and runbooks quietly go out of date. A stateless chatbot cannot know that "scale up the pods" already failed three times on this exact failure, or that runbook RB-12 was replaced last month.

## What memory changes

| Situation | Without memory | With Hindsight memory |
|---|---|---|
| Database connection pool exhausted | Generic checklist (raise `max_connections`, restart the service) | Cites past incidents, puts the fix that worked first, warns that scaling pods failed before |
| A runbook was replaced | Recommends whatever it was trained on | Warns the old runbook is deprecated and names its replacement |
| An alert it has never seen | Confident generic advice | "No similar past incidents found; low confidence" and no invented history |
| Engineer marks a fix Worked / Failed | Forgets | The outcome is stored and shapes the next answer |
| Engineer pastes a new postmortem | Cannot learn | Learns it immediately and cites it next time |

## How Hindsight memory is used

One Hindsight memory bank per company (`DEJAOPS_BANK`, see `.env.example`).

| Operation | Where | What happens |
|---|---|---|
| `retain` | `memory.retain_incident`, `retain_runbook` | Every incident (alert, logs, root cause, each action and whether it worked or failed, postmortem) and every runbook (including its deprecation date and replacement) is stored with its real timestamp and a document id |
| `retain` | `memory.record_outcome` | Each Worked / Failed click is stored as timestamped engineer feedback |
| `retain` | `memory.retain_postmortem` | A pasted postmortem becomes memory instantly |
| `recall` | `memory.recall_similar` | Two recalls per alert: one with the alert text, one asking which runbooks apply and whether any are deprecated. Hindsight runs semantic, keyword, graph and temporal search and returns what fits the token budget |
| `reflect` | `memory.learned_summary` | Produces the "what DejaOps has learned" summary, instructed to use only stored facts |
| bank config | `memory.init_bank` | A mission and disposition tell the bank to track fixes that worked or failed and to never recommend a fix that failed before |

The Memory Graph page (the 🧠 button) reads stored memories with `list_memories`, groups them by similarity on our side (token overlap and shared incident or runbook ids), and lets you zoom from cluster to memory to nearest neighbours. Memories recalled by your last triage are highlighted. This clustering is our own visualisation, not Hindsight's internal graph.

## Architecture

```
 Streamlit UI (app.py, brain_graph.py)
        |
        v
  agent.py  ---- Groq LLM (gpt-oss-120b, qwen3-32b fallback)
        |            ^
        v            | only recalled memory + rules
  memory.py  ----> Hindsight  (retain / recall / reflect)
```

`agent.py` gives the LLM only what Hindsight recalled, plus rules: never recommend a fix that failed before, warn about deprecated runbooks (only if relevant), cite incident ids, and admit when nothing similar exists. Model output is validated and normalised so the UI cannot break on malformed JSON. Inputs that are not alerts ("hi") are rejected before any model call.

## Setup

```
git clone <this repo>
cd DejaOps
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env  then fill in the keys
python seed.py                # loads the synthetic company history into the bank
python check_setup.py         # verifies Hindsight, Groq and the bank
streamlit run app.py
```

`.env` needs `HINDSIGHT_URL`, `HINDSIGHT_API_KEY`, `GROQ_API_KEY` and `DEJAOPS_BANK`. Seeding is resumable: it records progress in `data/.seeded_<bank>.txt`.

## Data

The company, **Northwind Payments**, is fictional and all data is synthetic (generated with an LLM, then checked by `validate_data.py`): 120 incidents, 20 runbooks and 10 demo alerts. The history is designed with recurring patterns (pool exhaustion, Redis failover, TLS expiry, memory leaks, disk full from WAL, DNS, a flaky payment gateway), fixes that repeatedly fail, and runbooks that are deprecated on known dates. Demo alerts are deliberately not copies of stored incidents, and two describe problems the history has never seen.

## Project layout

```
app.py            Streamlit UI: triage, side-by-side comparison, Worked/Failed feedback
brain_graph.py    Memory Graph page (D3 cluster explorer)
agent.py          LLM triage with rules, validation and input guard
memory.py         Hindsight retain / recall / reflect wrapper
seed.py           Resumable loader for the company history
validate_data.py  Sanity checks on the data files
check_setup.py    Pre-demo health check
data/             incidents.json, runbooks.json, demo_alerts.json
```

## Lessons learned

- The Hindsight Python client uses async networking internally. Calling it from a worker thread fails with "Timeout context manager should be used inside a task", so all Hindsight calls stay on the main thread and only the Groq-only baseline runs in a thread.
- Feedback memories have no incident id, so the agent labels them `FEEDBACK` instead of guessing.
- Environment variables set in the shell override `.env` unless you load it with `override=True`. We hit this and briefly read the wrong bank.

## Limitations

- All data is synthetic, so accuracy on real incidents is unproven.
- There are no PagerDuty, Slack or Datadog integrations yet, and no access control or redaction of sensitive logs.
- DejaOps suggests, it does not act. A human approves every change.
- Whether one Worked / Failed click changes a recommendation depends on how much history already exists for that pattern.
- Graph clustering uses lexical similarity and can group unrelated memories that share vocabulary.