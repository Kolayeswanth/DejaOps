# Metrics

## Current project dataset and implementation metrics

| Metric | Value | Source or method |
|---|---:|---|
| Incidents | 120 | Records in `data/incidents.json` |
| Runbooks | 20 | Records in `data/runbooks.json` |
| Demo alerts | 10 | Records in `data/demo_alerts.json` |
| Action records | 304 | All incident action entries |
| Worked actions | 172 | Action result equals `worked` |
| Failed actions | 132 | Action result equals `failed` |
| Worked-action rate | 56.58% | 172 / 304 action records |
| Failed-action rate | 43.42% | 132 / 304 action records |
| Active runbooks | 18 | Runbook status equals `active` |
| Deprecated runbooks | 2 | Runbook status equals `deprecated` |
| Python source files | 8 | Root `*.py` files |
| Python source lines | 1,283 | Line count over root `*.py` files |
| Test files | 2 | `tests/test_*.py` |
| Test functions | 15 | Functions named `test_*` |

These counts describe the checked-in dataset and implementation. They are not accuracy, latency, reliability, or production-scale claims.

## Runtime signals available in the UI

The triage UI displays elapsed time for the generic and memory-assisted calls, recalled evidence count, warning count, vetted-fix count, and an evidence-based confidence label. The application does not persist these as a long-term telemetry series.

## Recommended future evaluation metrics

Future contributors could evaluate incident resolution success, recommendation acceptance, memory recall relevance, repeated-incident resolution improvement, time-to-resolution, mean time to acknowledge, feedback coverage, successful runbook reuse, and memory retrieval precision. These are evaluation ideas, not current measurements.

## Future observability metrics

A deployed extension could collect recall latency, model latency, retention latency, token usage, retrieval relevance, recommendation outcome rates, feedback volume, memory growth, and end-to-end incident resolution measures. Those require explicit instrumentation and an evaluation policy before being reported as operational metrics.
