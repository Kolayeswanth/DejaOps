# Workflows

## Triage

Alert input -> shape check -> generic baseline and memory-assisted triage -> normalized response -> evidence, warnings, fixes, and confidence.

## Teach and feedback

The current visible workflow exposes Worked/Failed controls in the triage result and retains their outcome. `memory.retain_postmortem` is available as a module-level retention boundary for future or embedding UI flows; the current graph page does not render a postmortem editor.

## Graph

Open the brain button -> fetch Hindsight memories -> cluster locally -> inspect graph nodes, statuses, and nearest relationships -> highlight latest recalled evidence.

See [INCIDENT_RESPONSE_WORKFLOW.md](INCIDENT_RESPONSE_WORKFLOW.md) and [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md) for details.
