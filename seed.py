"""Load local incidents and runbooks into the Hindsight bank."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import memory

ROOT = Path(__file__).resolve().parent
INCIDENTS_PATH = ROOT / "data" / "incidents.json"
RUNBOOKS_PATH = ROOT / "data" / "runbooks.json"


def _load(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_all() -> dict[str, Any]:
    load_dotenv()
    incidents = _load(INCIDENTS_PATH)
    runbooks = _load(RUNBOOKS_PATH)
    retained = 0
    errors: list[str] = []

    for incident in incidents:
        try:
            memory.retain_text(
                memory.format_incident(incident),
                context="seed-incident",
                metadata={"id": incident.get("id"), "kind": "incident"},
            )
            retained += 1
        except Exception as exc:  # noqa: BLE001 - seed should keep going
            errors.append(f"{incident.get('id')}: {exc}")

    for runbook in runbooks:
        try:
            memory.retain_text(
                memory.format_runbook(runbook),
                context="seed-runbook",
                metadata={"id": runbook.get("id"), "kind": "runbook"},
            )
            retained += 1
        except Exception as exc:  # noqa: BLE001 - seed should keep going
            errors.append(f"{runbook.get('id')}: {exc}")

    return {
        "bank_id": memory.bank_id(),
        "incidents": len(incidents),
        "runbooks": len(runbooks),
        "retained": retained,
        "errors": errors,
    }


if __name__ == "__main__":
    result = seed_all()
    print(json.dumps(result, indent=2))
