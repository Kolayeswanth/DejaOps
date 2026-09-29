# Current Capabilities

## Incident Intelligence

Accepts alert text, rejects inputs that do not resemble alerts, and produces a structured hypothesis and recommended fixes through a generic baseline and a memory-assisted path.

## Persistent Memory

Retains incidents, runbooks, engineer feedback, and taught postmortems in a configured Hindsight bank. Recalls relevant text through alert and runbook-focused queries.

## Feedback Loop

Lets an engineer mark a memory-assisted fix Worked or Failed. The verdict is retained with the alert and fix text so later recall can include the experience.

## Operational Knowledge

Historical incidents include alert text, logs, root cause, action results, resolution time, runbook reference, and postmortem. Runbooks include lifecycle status, replacement information, scope, and steps.

## Outcome Tracking

The agent prompt and local enrichment detect worked and failed historical actions. The graph additionally presents mixed and deprecated display statuses when those signals appear in stored text.

## Visualization

The triage view presents recalled counts, warnings, evidence, memory influence, confidence, and outcome controls. The Memory Graph clusters stored memories with lexical similarity and highlights memories associated with the latest evidence.

## Dataset

The synthetic Northwind Payments environment contains 120 incidents, 20 runbooks, 10 demo alerts, and 304 action records, including 172 worked and 132 failed historical actions.

## Developer Extensibility

The main extension points are the JSON dataset, `memory.py` retain/recall boundaries, `agent.py` prompt and normalization logic, and Streamlit rendering in `app.py` and `brain_graph.py`.
