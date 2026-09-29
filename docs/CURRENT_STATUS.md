# Current Scope

DejaOps currently provides a focused Streamlit incident-response experience for the Northwind Payments synthetic environment.

## Implemented capabilities

- Generic and Hindsight-assisted alert triage.
- Incident and runbook seeding.
- Worked/Failed feedback retention.
- Evidence, warning, rejection, memory-influence, and provenance fields.
- Memory Graph visualization with local lexical clusters.
- Dataset validation and focused pytest coverage.

## Validation snapshot

The source data validation passes. The repository currently contains 15 test functions; the documented pytest snapshot is 10 passed and 5 failed when run with the repository root on the module path. See [TESTING.md](TESTING.md) for the exact command and scope.

## Extension points

The architecture is ready to be extended through the JSON data model, Hindsight wrapper, agent prompts/post-processing, Streamlit UI, and graph renderer. The roadmap is in [ROADMAP.md](ROADMAP.md).
