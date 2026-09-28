"""Hindsight retain / recall / reflect wrappers for DejaOps."""

from __future__ import annotations

import os
from typing import Any

from hindsight_client import Hindsight


def _client() -> Hindsight:
    kwargs: dict[str, Any] = {
        "base_url": os.getenv("HINDSIGHT_BASE_URL", "http://localhost:8888"),
    }
    api_key = os.getenv("HINDSIGHT_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key
    return Hindsight(**kwargs)


def bank_id() -> str:
    return os.getenv("HINDSIGHT_BANK_ID", "dejaops")


def format_incident(incident: dict[str, Any]) -> str:
    tags = ", ".join(incident.get("tags") or [])
    return (
        f"Incident {incident.get('id')}: {incident.get('title')}\n"
        f"Service: {incident.get('service')}\n"
        f"Severity: {incident.get('severity')}\n"
        f"When: {incident.get('occurred_at')}\n"
        f"Symptoms: {incident.get('symptoms')}\n"
        f"Root cause: {incident.get('root_cause')}\n"
        f"Resolution: {incident.get('resolution')}\n"
        f"Runbook: {incident.get('runbook_id')}\n"
        f"Tags: {tags}"
    )


def format_runbook(runbook: dict[str, Any]) -> str:
    triggers = ", ".join(runbook.get("triggers") or [])
    steps = "\n".join(f"- {step}" for step in (runbook.get("steps") or []))
    return (
        f"Runbook {runbook.get('id')}: {runbook.get('title')}\n"
        f"Service: {runbook.get('service')}\n"
        f"Triggers: {triggers}\n"
        f"Steps:\n{steps}"
    )


def retain_text(content: str, context: str | None = None, metadata: dict[str, Any] | None = None) -> Any:
    client = _client()
    return client.retain(
        bank_id=bank_id(),
        content=content,
        context=context,
        metadata=metadata or {},
    )


def recall(query: str, limit: int = 8) -> list[str]:
    client = _client()
    results = client.recall(bank_id=bank_id(), query=query)
    items = getattr(results, "results", None) or []
    texts: list[str] = []
    for item in items[:limit]:
        text = getattr(item, "text", None) or str(item)
        if text:
            texts.append(text)
    return texts


def reflect(query: str) -> str:
    client = _client()
    answer = client.reflect(bank_id=bank_id(), query=query)
    return getattr(answer, "text", None) or str(answer)
