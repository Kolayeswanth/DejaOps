# Judge-Ready Project Story

## Problem

AI incident assistants often treat each incident independently, even though operational teams accumulate experience in incidents, runbooks, actions, and outcomes.

## Insight

An incident response assistant becomes more useful when it can remember which approaches worked, which failed, and which operational guidance changed.

## Solution

DejaOps combines Hindsight persistent memory with an agentic triage flow. It recalls relevant experience, reasons over it, shows provenance, and retains engineer feedback for future alerts.

## Loop

```text
Incident -> Reason -> Act or recommend -> Observe -> Learn -> Remember -> Recall -> Respond with experience
```

## Demonstration sequence

1. Start the Streamlit app and choose a demo alert.
2. Run triage and show the generic and memory-assisted panels.
3. Point out recalled incidents, historical outcomes, warnings, and memory influence.
4. Show a recommended fix and mark it Worked or Failed.
5. Open the Memory Graph and show the stored memory clusters and status colors.
6. Re-run a related alert or select another alert sharing the same operational pattern.
7. Show recalled evidence and the associated incident ID or feedback marker.
8. Use the graph highlight from the latest triage to connect evidence to stored memory.
9. Explain how the retained outcome becomes available to later reasoning.

The sequence uses the controls and views implemented in `app.py` and `brain_graph.py`; it does not depend on a fictional dashboard or action executor.
