# Extending the Project

DejaOps is intentionally organized around replaceable data, memory, agent, and UI boundaries.

## New incident types

Add records matching the Incident schema to `data/incidents.json`, then run `validate_data.py` and `seed.py`. Keep stable IDs, timestamps, action results, and runbook references so recall and provenance remain explainable.

## New runbooks

Add a runbook record to `data/runbooks.json` with status, steps, scope, and effective/deprecation metadata where applicable. `memory.retain_runbook` is the single formatting boundary for Hindsight retention.

## New tools or actions

The current UI records outcomes but does not execute infrastructure tools. A future tool adapter should be introduced beside the agent orchestration, with explicit input validation, authorization, audit logging, and a result-to-outcome mapping before it is exposed in `app.py`.

## New agent behavior

Update the prompts and deterministic post-processing in `agent.py`. Preserve the normalized response keys consumed by `app.py`. Keep model output parsing defensive and keep historical evidence distinct from current observations.

## New memory behavior

Add Hindsight operations in `memory.py`, keeping bank configuration and timestamp/document-ID handling in that module. Extend `recall_similar` when a new retrieval query is needed, and update `LLM_CONTEXT.md` and `MEMORY_ARCHITECTURE.md` with the lifecycle change.

## New metrics

Derive dataset metrics from source JSON or add explicit runtime instrumentation around recall, model calls, retention, and feedback. Record measurement method and scope so local dataset counts are not presented as production performance.

## New UI components

Add Streamlit rendering in `app.py` or a focused module, using the existing session-state contract. For memory visualizations, follow the `brain_graph.py` boundary and keep graph-derived classifications labeled as visualization metadata.

## New domains

Replace the synthetic incident/runbook vocabulary with a domain dataset, update the bank mission in `memory.init_bank`, and define domain-specific outcome signals. The current architecture can support SRE, SOC, IT operations, support operations, and infrastructure troubleshooting as adaptations; those integrations are extension points rather than current features.
