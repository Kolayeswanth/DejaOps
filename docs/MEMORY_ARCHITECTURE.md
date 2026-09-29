# Memory Architecture

## Lifecycle

```mermaid
flowchart LR
    Incident[Incident JSON] --> Retain1[retain_incident]
    Runbook[Runbook JSON] --> Retain2[retain_runbook]
    Teach[Taught postmortem] --> Retain3[retain_postmortem]
    Outcome[Worked/Failed feedback] --> Retain4[record_outcome]
    Retain1 --> Bank[Configured Hindsight bank]
    Retain2 --> Bank
    Retain3 --> Bank
    Retain4 --> Bank
    Alert[New alert] --> Recall[Two recall queries]
    Bank --> Recall
    Recall --> Prompt[Memory context]
    Prompt --> Agent[Groq reasoning]
    Agent --> Result[Evidence and recommendation]
```

## Stored memory types

- Incident postmortem: formatted incident fields, logs, root cause, actions, resolution, runbook, and postmortem.
- Runbook: title, status, lifecycle dates, replacement, reason, scope, and steps.
- Outcome feedback: timestamped alert/fix text with `WORKED` or `FAILED`.
- Taught postmortem: free-form engineer text retained with a timestamp.

## Retrieval

`recall_similar` queries the alert and a runbook applicability/deprecation question, requests a bounded token budget, and deduplicates exact result text. The recalled result preserves Hindsight type, text, ID, and context when available.

## Reflection and graph

`learned_summary` uses Hindsight `reflect` to summarize stored facts. `brain_graph.py` uses `list_memories` first and broad fallback recalls when needed, then builds a local token-overlap graph. This graph is a UI projection and not Hindsight's internal graph.

## Provenance

`agent.py` parses recalled memory sentences for action outcomes and links them to candidate fixes using token containment/similarity. Provenance is shown only when an incident ID can be established; feedback without one is represented as `FEEDBACK` rather than an invented ID.
