# Demonstration Guide

This guide presents DejaOps as an independent open-source incident-response system. The goal is to make the persistent-memory workflow easy to inspect and reproduce locally.

## Demonstration sequence

1. Start the application and choose a seeded alert from the Streamlit triage view.
2. Run the alert through the generic and memory-assisted paths.
3. Compare the hypotheses, recommended fixes, recalled evidence, warnings, and memory influence.
4. Select a memory-assisted fix and record whether the operational outcome was Worked or Failed.
5. Open the Memory Graph to inspect stored memories, outcome statuses, clusters, and relationships.
6. Submit a related alert or use another seeded scenario with a similar operational pattern.
7. Show how recalled incident or feedback memory appears in the new investigation.
8. Explain the lifecycle: incident, investigation, outcome, retained memory, and future recall.

## What to highlight

- The generic path reasons without company history.
- The memory-assisted path receives recalled Hindsight context.
- Historical evidence can include incident IDs, action outcomes, and runbook status.
- Outcome feedback is retained as operational memory rather than treated as a disposable UI event.
- The current graph is a local visualization of fetched memory text, with lexical clusters and latest-recall highlighting.

## Suggested scenarios

The seeded demo alerts cover database pool exhaustion, Redis failover, Kafka consumer lag, TLS expiry, memory growth, payment-gateway latency, database disk pressure, cache-related load, multi-dependency failure, and GPU inference pressure. Use a scenario that matches the seeded incident history to make recall and historical outcome reuse visible.

## Developer walkthrough

For a technical walkthrough, read [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md), [FEEDBACK_LOOP.md](FEEDBACK_LOOP.md), and [LLM_CONTEXT.md](LLM_CONTEXT.md) alongside the source files. The application can be extended by replacing the synthetic data, adding runbooks or tools, and defining domain-specific outcome signals.
