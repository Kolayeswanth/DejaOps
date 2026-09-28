def triage(alert_text: str, use_memory: bool) -> dict:
    if not use_memory:
        return {"hypothesis": "Possible resource exhaustion.",
                "recommended_fixes": [{"step": "Scale the service up", "reason": "Generic first response."},
                                      {"step": "Check the logs", "reason": "Generic."}],
                "evidence": [], "warnings": []}
    return {"hypothesis": "Postgres connection pool exhaustion (seen 4 times before).",
            "recommended_fixes": [{"step": "Restart pgbouncer and kill the nightly batch job",
                                   "reason": "Worked in INC-003, INC-011, INC-019."}],
            "evidence": [{"incident_id": "INC-011", "summary": "pgbouncer saturated after batch job",
                          "outcome": "Resolved in 38 min by restarting pgbouncer"}],
            "warnings": ["Scaling pods FAILED in 3 of 3 past incidents.",
                         "Runbook RB-12 is deprecated; use RB-31."]}

def record_outcome(alert_text: str, fix: str, worked: bool) -> None:
    pass

def learned_summary() -> str:
    return "(stub) Pool exhaustion: scaling fails, pgbouncer restart works."