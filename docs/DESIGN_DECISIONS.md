# Design Decisions

## Persistent memory

Incident response improves when the assistant can reuse outcomes rather than treating every alert as a fresh prompt. Hindsight provides the retain, recall, and reflect operations needed for that lifecycle.

## Feedback loop

Worked/Failed controls make the central idea visible and give the system a direct experience signal. Feedback is retained as timestamped text so future recall can surface it.

## Incident, runbook, action, and outcome model

These entities match the language of on-call work. Action results make failed remediations explicit, while runbook status and replacement IDs preserve operational change over time.

## Provenance

The UI should show why a recommendation was influenced by memory. Candidate-to-action links, incident IDs, dates, outcomes, and source text provide an inspectable path when the recalled prose supports one.

## Streamlit

Streamlit keeps the demo workflow small and directly connects widgets to Python orchestration. It also makes the generic-versus-memory comparison and graph visualization easy to inspect locally.

## Synthetic data

A synthetic Northwind Payments environment provides repeatable recurring patterns without exposing real operational data. It also makes validation and demonstration deterministic at the repository level.

## Outcome visualization

The triage view puts evidence and outcome controls beside recommendations, while the Memory Graph exposes clusters and status signals. This makes the feedback loop observable to a human operator.

## LLM context documentation

`LLM_CONTEXT.md` records source files, response contracts, runtime ordering, memory boundaries, and extension points so another developer or LLM can continue the project without reconstructing the architecture from scratch.
