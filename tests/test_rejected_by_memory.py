import pytest

from agent import detect_rejected_by_memory


INCIDENT_MEMORY = """Incident INC-034 on 2026-01-10T09:26:00Z | service kafka | SEV2
Alert: Kafka consumer lag increased.
Root cause: Consumer throughput was insufficient.
Actions taken:
- Tried: Restart Kafka consumers -> FAILED
- Tried: Increase consumer parallelism and tune consumer configuration -> WORKED
Postmortem: Restarting consumers temporarily reduced lag but caused duplicate processing and did not resolve the underlying issue.
"""


def test_detects_failed_historical_remediation_and_reason():
    rejected = detect_rejected_by_memory(
        "Kafka consumer lag increased after new traffic.",
        [{"type": "incident postmortem", "text": INCIDENT_MEMORY}],
        [{"step": "Restart Kafka consumers", "reason": "A fast fix"}],
    )

    assert rejected
    assert rejected[0]["incident_id"] == "INC-034"
    assert rejected[0]["remediation"] == "Restart Kafka consumers"
    assert rejected[0]["outcome"] == "failed"
    assert "duplicate processing" in rejected[0]["reason"].lower()


def test_ignores_working_remediations():
    rejected = detect_rejected_by_memory(
        "Kafka consumer lag increased after new traffic.",
        [{"type": "incident postmortem", "text": INCIDENT_MEMORY}],
        [{"step": "Increase consumer parallelism and tune consumer configuration", "reason": "This worked before"}],
    )

    assert rejected == []


def test_handles_no_memory_or_no_failed_match():
    rejected = detect_rejected_by_memory(
        "Database latency drifted above baseline.",
        [{"type": "incident postmortem", "text": "Incident INC-010 on 2026-02-04 | service payments-api | SEV3\n- Tried: Increase cache cluster -> WORKED"}],
        [{"step": "Restart the service", "reason": "Generic restart"}],
    )

    assert rejected == []
