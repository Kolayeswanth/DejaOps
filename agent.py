"""Diagnose a live incident using recalled memories, runbooks, and an LLM."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

import memory

ROOT = Path(__file__).resolve().parent
RUNBOOKS_PATH = ROOT / "data" / "runbooks.json"


def load_runbooks() -> list[dict[str, Any]]:
    return json.loads(RUNBOOKS_PATH.read_text(encoding="utf-8"))


def _match_runbooks(incident: dict[str, Any], runbooks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    haystack = " ".join(
        [
            str(incident.get("title") or ""),
            str(incident.get("symptoms") or ""),
            str(incident.get("service") or ""),
            " ".join(incident.get("tags") or []),
        ]
    ).lower()
    matched = []
    for runbook in runbooks:
        triggers = [t.lower() for t in (runbook.get("triggers") or [])]
        if any(trigger in haystack for trigger in triggers):
            matched.append(runbook)
            continue
        service = str(runbook.get("service") or "").lower()
        if service and service in haystack:
            matched.append(runbook)
    return matched[:3]


def _llm_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
    )


def diagnose(incident: dict[str, Any], persist: bool = False) -> dict[str, Any]:
    query = (
        f"{incident.get('title', '')}\n"
        f"{incident.get('service', '')}\n"
        f"{incident.get('symptoms', '')}"
    )
    recalled = memory.recall(query)
    runbooks = _match_runbooks(incident, load_runbooks())

    prompt = (
        "You are DejaOps, an incident commander that uses past incidents "
        "and runbooks. Diagnose the live incident. Return concise JSON with "
        "keys: likely_cause, recommended_runbook_id, next_steps (array of strings), "
        "confidence (0-1), similar_incident_ids (array of strings).\n\n"
        f"LIVE INCIDENT:\n{json.dumps(incident, indent=2)}\n\n"
        f"RECALLED MEMORIES:\n{chr(10).join(recalled) or '(none)'}\n\n"
        f"MATCHED RUNBOOKS:\n{json.dumps(runbooks, indent=2)}"
    )

    diagnosis_text = ""
    parsed: dict[str, Any] | None = None
    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        completion = _llm_client().chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        diagnosis_text = completion.choices[0].message.content or ""
        try:
            parsed = json.loads(diagnosis_text)
        except json.JSONDecodeError:
            parsed = None
    else:
        diagnosis_text = "LLM_API_KEY is not set; returning heuristic diagnosis only."

    if parsed is None:
        parsed = {
            "likely_cause": "Insufficient model output; use recalled memories and runbook steps.",
            "recommended_runbook_id": runbooks[0]["id"] if runbooks else None,
            "next_steps": (runbooks[0].get("steps") or [])[:4] if runbooks else [],
            "confidence": 0.35 if runbooks or recalled else 0.1,
            "similar_incident_ids": [],
        }

    if persist:
        memory.retain_text(
            memory.format_incident(incident),
            context="live-incident",
            metadata={"id": incident.get("id"), "kind": "incident"},
        )

    return {
        "incident": incident,
        "recalled_memories": recalled,
        "matched_runbooks": runbooks,
        "diagnosis": parsed,
        "raw_model_output": diagnosis_text,
    }
