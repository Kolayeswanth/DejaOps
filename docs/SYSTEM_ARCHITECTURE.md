# System Architecture

## System overview

```mermaid
flowchart LR
    User[On-call engineer] --> UI[Streamlit app.py]
    UI --> Agent[agent.py]
    Agent --> Groq[Groq chat completion]
    Agent --> Memory[memory.py]
    Memory --> H[Hindsight bank]
    UI --> Graph[brain_graph.py]
    Graph --> H
    Data[JSON data] --> Seed[seed.py]
    Seed --> H
```

## Runtime architecture

```mermaid
sequenceDiagram
    participant U as User
    participant S as Streamlit
    participant A as agent.py
    participant M as memory.py
    participant H as Hindsight
    participant G as Groq
    U->>S: Enter or select alert
    S->>A: triage(alert, False)
    A->>G: Generic prompt
    S->>A: triage(alert, True)
    A->>M: recall_similar(alert)
    M->>H: Two recall queries
    H-->>M: Recalled text and metadata
    M-->>A: Memory context
    A->>G: Memory prompt plus alert
    G-->>A: JSON response
    A-->>S: Normalized response and provenance
    S-->>U: Compare results and record outcome
    S->>M: record_outcome(alert, fix, verdict)
    M->>H: Retain feedback
```

## Component responsibilities

- `app.py`: Streamlit state, alert input, triage comparison, feedback controls, and graph navigation.
- `agent.py`: alert guard, prompts, Groq call retries, JSON normalization, rejection detection, and provenance enrichment.
- `memory.py`: Hindsight client, bank initialization, incident/runbook retention, recall, reflection, feedback, and taught postmortem retention.
- `brain_graph.py`: memory listing/recall fallback, lexical similarity, clusters, statuses, and D3 rendering.
- `seed.py`: resumable retention of local incidents and runbooks.
- `validate_data.py`: source-data structure and relationship validation.

## Data architecture

```mermaid
flowchart TD
    I[data/incidents.json] --> V[validate_data.py]
    R[data/runbooks.json] --> V
    D[data/demo_alerts.json] --> UI[app.py]
    I --> Seed[seed.py]
    R --> Seed
    Seed --> Bank[Hindsight bank]
    Bank --> Recall[Alert/runbook recall]
    Recall --> Agent[Memory-assisted reasoning]
    Agent --> UI
    UI --> Feedback[Worked/Failed feedback]
    Feedback --> Bank
```

## Agent and feedback architecture

The agent is request-driven rather than a background worker. It recommends and records outcomes; it does not execute infrastructure changes. The feedback loop is documented in [FEEDBACK_LOOP.md](FEEDBACK_LOOP.md), and the detailed agent path is in [AI_AGENT_ARCHITECTURE.md](AI_AGENT_ARCHITECTURE.md).

## UI and metrics architecture

The home view renders the two triage paths and feedback. The Memory Graph reads Hindsight separately and performs local lexical clustering. Current dataset metrics are derived from JSON; no production telemetry pipeline is present. See [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md) and [METRICS.md](METRICS.md).
