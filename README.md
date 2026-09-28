# agent.py
triage(alert_text: str, use_memory: bool) -> dict
# returns {"hypothesis": str, "recommended_fixes": [{"step": str, "reason": str}],
#          "evidence": [{"incident_id": str, "summary": str, "outcome": str}],
#          "warnings": [str]}

# memory.py
record_outcome(alert_text: str, fix: str, worked: bool) -> None
learned_summary() -> str   # "what the agent has learned so far"