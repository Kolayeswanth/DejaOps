# Pipelines

## Incident pipeline

```mermaid
flowchart LR
    Alert --> IncidentContext[Alert and current context]
    IncidentContext --> Retrieval[Incident and runbook recall]
    Retrieval --> Reasoning[Agent reasoning]
    Reasoning --> Recommendation[Recommended fixes]
    Recommendation --> Outcome[Engineer outcome]
```

## Memory pipeline

```mermaid
flowchart LR
    Interaction[Incident or feedback interaction] --> Experience[Formatted experience]
    Experience --> Retain[Hindsight retain]
    Retain --> Memory[Persistent memory]
    Memory --> Recall[Future recall]
    Recall --> Reasoning[Future reasoning]
```

## Feedback pipeline

```mermaid
flowchart LR
    Action --> Result[Observed result]
    Result --> Classification[Worked or Failed]
    Classification --> Provenance[Historical provenance]
    Provenance --> Memory[Hindsight memory]
    Memory --> Recommendation[Future recommendation]
```

## Data pipeline

`data/incidents.json` and `data/runbooks.json` are validated, then retained by `seed.py`. `data/demo_alerts.json` is read by `app.py` for selectable demonstrations. `merge_batches.py` can rebuild the incident source from `data/batches/`.

## UI pipeline

```mermaid
flowchart LR
    User --> Streamlit
    Streamlit --> Agent
    Agent --> Memory
    Memory --> Result[Normalized triage result]
    Result --> Visualization[Evidence, warnings, graph, and feedback controls]
```
