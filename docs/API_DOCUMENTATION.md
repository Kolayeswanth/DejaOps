# API Documentation

## Local application boundary

There is no local HTTP API or separate backend server. Streamlit widgets call Python functions in-process.

## Agent functions

| Function | Purpose |
|---|---|
| `agent.triage(alert_text, use_memory=True)` | Runs alert validation, optional recall, Groq reasoning, normalization, and enrichment |
| `agent.looks_like_alert(text)` | Applies the minimum alert shape check |
| `agent.build_action_provenance(memories, candidate_fixes)` | Derives historical action links |
| `agent.detect_rejected_by_memory(alert, memories, candidate_fixes)` | Finds failed historical remediation matches |
| `agent.demote_conflicting_fixes(fixes, rejected)` | Removes closely matching rejected recommendations |

## Memory functions

| Function | Hindsight operation | Purpose |
|---|---|---|
| `memory.init_bank()` | `create_bank` | Creates/configures the named bank |
| `memory.retain_incident(incident)` | `retain` | Stores formatted incident history |
| `memory.retain_runbook(runbook)` | `retain` | Stores runbook and lifecycle context |
| `memory.record_outcome(alert, fix, worked)` | `retain` | Stores engineer feedback |
| `memory.retain_postmortem(text)` | `retain` | Stores taught postmortem text |
| `memory.recall_similar(alert)` | `recall` | Retrieves alert and runbook context |
| `memory.learned_summary()` | `reflect` | Summarizes stored facts |
| `brain_graph._fetch()` | `list_memories` plus fallback `recall` | Loads graph source memories |

## Configuration

Hindsight uses `HINDSIGHT_URL`, `HINDSIGHT_API_KEY`, and `DEJAOPS_BANK`. Groq uses `GROQ_API_KEY`. Credential values are read from environment variables and are never part of this documentation.
