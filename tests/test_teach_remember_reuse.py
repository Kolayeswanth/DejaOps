from types import SimpleNamespace

import agent
import memory


class FakeMemoryClient:
    def __init__(self, retain_result=None, retain_error=None):
        self.retain_result = retain_result
        self.retain_error = retain_error
        self.retained = []

    def retain(self, **kwargs):
        if self.retain_error:
            raise self.retain_error
        self.retained.append(kwargs)
        return self.retain_result


def test_teach_calls_hindsight_retain_and_reports_success(monkeypatch):
    client = FakeMemoryClient(SimpleNamespace(id="memory-123"))
    monkeypatch.setattr(memory, "client", client)

    result = memory.retain_postmortem(
        "Kafka lag followed a traffic spike. Restarting consumers failed; increasing parallelism worked."
    )

    assert result["stored"] is True
    assert result["id"] == "memory-123"
    assert client.retained[0]["bank_id"] == memory.BANK_ID
    assert client.retained[0]["context"] == "postmortem"
    assert "increasing parallelism worked" in client.retained[0]["content"]


def test_teach_failure_does_not_report_success(monkeypatch):
    monkeypatch.setattr(memory, "client", FakeMemoryClient(retain_error=RuntimeError("Hindsight offline")))

    try:
        memory.retain_postmortem("A taught incident lesson")
    except RuntimeError as error:
        assert str(error) == "Hindsight offline"
    else:
        raise AssertionError("retain_postmortem reported success after retain failed")


def test_recall_preserves_memory_metadata(monkeypatch):
    result = SimpleNamespace(results=[SimpleNamespace(
        text="Incident INC-034: restarting consumers failed; increasing parallelism worked.",
        type="postmortem",
        id="memory-123",
        context="postmortem",
    )])

    class RecallClient:
        def recall(self, **kwargs):
            return result

    monkeypatch.setattr(memory, "client", RecallClient())

    recalled = memory.recall_similar("Consumer lag is rising after a traffic spike.")

    assert recalled == [{
        "type": "postmortem",
        "text": "Incident INC-034: restarting consumers failed; increasing parallelism worked.",
        "id": "memory-123",
        "context": "postmortem",
    }]


def test_triage_passes_recalled_memory_into_reasoning_and_marks_influence(monkeypatch):
    recalled = [{
        "type": "postmortem",
        "text": "Incident INC-034: restarting consumers failed; increasing parallelism worked.",
        "id": "memory-123",
        "context": "postmortem",
    }]
    captured = {}

    def fake_recall(alert):
        return recalled

    def fake_ask(system, user):
        captured["user"] = user
        return {
            "hypothesis": "Consumer throughput is insufficient.",
            "recommended_fixes": [{"step": "Increase consumer parallelism", "reason": "It worked historically."}],
            "evidence": [{"incident_id": "INC-034", "summary": "Consumer lag", "outcome": "worked"}],
            "warnings": [],
            "memory_influence": "Increasing parallelism worked in the recalled incident.",
        }

    monkeypatch.setattr(agent, "recall_similar", fake_recall)
    monkeypatch.setattr(agent, "_ask", fake_ask)

    result = agent.triage("Consumer lag is rising after a traffic spike.", use_memory=True)

    assert "Incident INC-034" in captured["user"]
    assert result["recalled_memories"] == recalled
    assert result["memory_influence"] == "Increasing parallelism worked in the recalled incident."
    assert result["evidence"][0]["incident_id"] == "INC-034"


def test_triage_without_recalled_memory_has_no_fake_memory_reference(monkeypatch):
    monkeypatch.setattr(agent, "recall_similar", lambda alert: [])
    monkeypatch.setattr(agent, "_ask", lambda system, user: {
        "hypothesis": "Generic analysis.",
        "recommended_fixes": [{"step": "Inspect consumer health", "reason": "Start with current evidence."}],
        "evidence": [],
        "warnings": ["No similar past incidents found; low confidence."],
    })

    result = agent.triage("A previously unseen service has elevated latency.", use_memory=True)

    assert result["recalled_memories"] == []
    assert result["memory_influence"] == ""
    assert result["evidence"] == []


def test_display_memory_ranking_prefers_relevant_checkout_memory():
    memories = [
        {"type": "postmortem", "text": (
            "Incident DEMO-MEM-001 on 2026-09-28 checkout-service traffic spike caused elevated latency and checkout timeouts. "
            "The deployment had four replicas. Restarting checkout-service pods failed. "
            "Increasing replicas from 4 to 8 worked."
        )},
        {"type": "incident postmortem", "text": (
            "INC-007 payments-api PayFlow requests timed out while payment gateway latency increased."
        )},
        {"type": "incident postmortem", "text": (
            "INC-005 postgres-primary-0 disk usage reached 97 percent because WAL was retained."
        )},
    ]

    selected = agent.select_display_memories(
        "checkout-service is experiencing elevated request latency and intermittent checkout timeouts "
        "after a recent increase in traffic. The deployment currently has four replicas and CPU utilization is rising.",
        memories,
        [{"step": "Increase checkout-service replicas from 4 to 8", "reason": ""}],
    )

    assert [memory["text"] for memory in selected] == [memories[0]["text"]]


def test_triage_keeps_all_memory_for_reasoning_but_filters_display_evidence(monkeypatch):
    relevant = {"type": "postmortem", "text": "Incident DEMO-MEM-001 on 2026-09-28 checkout-service traffic spike; scaling replicas worked."}
    unrelated = {"type": "postmortem", "text": "INC-007 payments-api PayFlow timeout."}
    captured = {}

    monkeypatch.setattr(agent, "recall_similar", lambda alert: [relevant, unrelated])

    def fake_ask(system, user):
        captured["prompt"] = user
        return {
            "hypothesis": "Traffic increased demand on checkout-service.",
            "recommended_fixes": [{"step": "Scale checkout-service replicas", "reason": "Historical success."}],
            "evidence": [
                {"incident_id": "DEMO-MEM-001", "summary": "Scaling worked", "outcome": "worked"},
                {"incident_id": "INC-007", "summary": "PayFlow timeout", "outcome": "worked"},
            ],
            "warnings": [],
            "memory_influence": "Scaling worked in the recalled checkout incident.",
        }

    monkeypatch.setattr(agent, "_ask", fake_ask)

    result = agent.triage(
        "checkout-service latency and timeouts increased after a traffic spike with four replicas.",
        use_memory=True,
    )

    assert "DEMO-MEM-001" in captured["prompt"]
    assert "INC-007" in captured["prompt"]
    assert len(result["display_memories"]) == 1
    assert [item["incident_id"] for item in result["display_evidence"]] == ["DEMO-MEM-001"]
    assert result["action_provenance"][0]["incident_id"] == "DEMO-MEM-001"
    assert result["action_provenance"][0]["date"] == "2026-09-28"
    assert result["action_provenance"][0]["outcome"] == "worked"
    assert result["memory_influence"] == "Scaling worked in the recalled checkout incident."


def test_rejected_by_memory_remains_available_with_focused_display():
    memory_text = (
        "Incident DEMO-MEM-001 on 2026-09-28 checkout-service traffic spike. Actions taken:\n"
        "- Tried: Restart checkout-service pods -> FAILED\n"
        "- Tried: Increase checkout-service replicas from 4 to 8 -> WORKED\n"
        "Postmortem: Restarting pods did not resolve the traffic-spike latency."
    )

    rejected = agent.detect_rejected_by_memory(
        "checkout-service latency increased after traffic rose.",
        [{"type": "postmortem", "text": memory_text}],
        [{"step": "Restart checkout-service pods", "reason": ""}],
    )

    assert rejected
    assert rejected[0]["incident_id"] == "DEMO-MEM-001"
    assert rejected[0]["outcome"] == "failed"
    assert rejected[0]["date"] == "2026-09-28"


def test_memory_without_incident_id_does_not_create_provenance():
    provenance = agent.build_action_provenance(
        [{"type": "outcome feedback", "text": "Restart checkout-service pods failed."}],
        [{"step": "Restart checkout-service pods", "reason": ""}],
    )

    assert provenance == []


def test_recommendation_without_historical_evidence_is_not_supported_by_history():
    provenance = agent.build_action_provenance(
        [], [{"step": "Increase checkout-service replicas", "reason": ""}]
    )

    assert provenance == []


def test_hpa_only_memory_is_not_primary_scaling_evidence():
    memories = [{
        "type": "runbook",
        "text": (
            "Incident INC-HPA-001 on 2026-09-20 HPA configuration. "
            "What worked: Correct the HPA minReplicas and maxReplicas settings."
        ),
    }]

    selected = agent.select_display_memories(
        "checkout-service latency increased after a traffic spike with four replicas.",
        memories,
        [
            {"step": "Increase checkout-service replicas from 4 to 8", "reason": ""},
            {"step": "Review HPA configuration", "reason": ""},
        ],
    )

    assert selected == []


def test_database_pool_memory_is_not_scaling_evidence():
    memories = [{
        "type": "incident postmortem",
        "text": (
            "Incident INC-105 on 2026-09-18 payments-api database pool. "
            "What worked: Restart pgbouncer and pause the nightly batch workload."
        ),
    }]

    selected = agent.select_display_memories(
        "checkout-service latency increased after a traffic spike with four replicas.",
        memories,
        [{"step": "Increase checkout-service replicas from 4 to 8", "reason": ""}],
    )

    assert selected == []
