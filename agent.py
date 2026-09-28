"""
Stub agent module for DejaOps UI development.
Returns realistic sample data without requiring any API keys.
Swap in real implementations later — the UI code won't change.
"""

import time
import random


def triage(alert_text: str, use_memory: bool = True) -> dict:
    """
    Triage an alert and return hypothesis, fixes, evidence, and warnings.
    Simulates a short delay to mimic real LLM call latency.
    """
    # Simulate network latency
    time.sleep(random.uniform(1.0, 2.5))

    if not use_memory:
        # --- Without memory: generic response ---
        return {
            "hypothesis": (
                "The alert indicates a service degradation. Based on the symptoms described, "
                "this could be caused by resource exhaustion, a downstream dependency failure, "
                "or a recent deployment. Without historical context, I recommend starting with "
                "standard triage procedures."
            ),
            "recommended_fixes": [
                {
                    "step": "Check recent deployments and rollback if a deploy happened in the last 2 hours",
                    "reason": "Recent code changes are the most common cause of sudden degradations."
                },
                {
                    "step": "Scale up the affected service horizontally (add 4-8 pods)",
                    "reason": "Provides immediate relief if the issue is load-related."
                },
                {
                    "step": "Restart the service and monitor for recovery",
                    "reason": "Generic recovery step that resolves transient state corruption."
                }
            ],
            "evidence": [],
            "warnings": []
        }
    else:
        # --- With memory: enriched response with past incidents ---
        return {
            "hypothesis": (
                "This alert pattern closely matches INC-014 and INC-011, both involving "
                "connection pool exhaustion on the database tier. In past incidents, scaling "
                "pods did NOT help because the bottleneck was PgBouncer, not the application. "
                "The root cause was likely a long-running query holding connections open, causing "
                "cascading timeouts upstream."
            ),
            "recommended_fixes": [
                {
                    "step": "Restart PgBouncer to release stale connections",
                    "reason": "Worked in INC-014 (resolved in 47 min). This is the highest-confidence fix for this pattern."
                },
                {
                    "step": "Identify and kill long-running queries (> 30s) on the primary DB",
                    "reason": "Worked in INC-011. Prevents connection pool starvation at the source."
                },
                {
                    "step": "Temporarily increase PgBouncer max_client_conn from 200 → 400",
                    "reason": "Buys time while root cause is investigated. Used successfully in INC-008."
                }
            ],
            "evidence": [
                {
                    "incident_id": "INC-014",
                    "summary": "payments-api latency spike caused by PgBouncer connection exhaustion after a long-running analytics query locked the pool.",
                    "outcome": "Resolved by restarting PgBouncer. Scaling pods was attempted first but FAILED."
                },
                {
                    "incident_id": "INC-011",
                    "summary": "Similar p99 latency spike on payments-api. Root cause was a missing index causing a 45-second query.",
                    "outcome": "Resolved by killing the query and adding the missing index. PgBouncer restart also helped."
                },
                {
                    "incident_id": "INC-008",
                    "summary": "Connection pool exhaustion during Black Friday traffic spike.",
                    "outcome": "Temporarily increased max_client_conn. Permanent fix was connection pooling refactor in Q2."
                }
            ],
            "warnings": [
                "⚠️ Scaling pods (4→12) FAILED in INC-014 — the bottleneck was PgBouncer, not app CPU/memory. Do not repeat this fix.",
                "⚠️ Runbook RB-09 ('Restart payments-api pods') is DEPRECATED since 2026-01-15. Use RB-12 ('PgBouncer recovery') instead."
            ]
        }


def record_outcome(alert_text: str, fix_step: str, worked: bool) -> None:
    """
    Record whether a fix worked or failed. In production this writes to
    the Hindsight memory bank. Stub just logs to console.
    """
    verdict = "WORKED ✓" if worked else "FAILED ✗"
    print(f"[DejaOps] Outcome recorded: '{fix_step[:60]}...' → {verdict}")


def learned_summary() -> str:
    """
    Return a summary of what DejaOps has learned from past incidents.
    In production this calls Hindsight reflect(). Stub returns sample text.
    """
    time.sleep(random.uniform(0.5, 1.5))
    return """• **PgBouncer restarts** are the most reliable fix for payments-api latency spikes caused by connection exhaustion (worked 3/3 times).

• **Scaling pods** does NOT fix connection-pool issues — it failed in INC-014 and INC-019. Only scale if CPU/memory is the confirmed bottleneck.

• **Runbook RB-09** ("Restart payments-api pods") was deprecated on 2026-01-15. Always use **RB-12** ("PgBouncer recovery procedure") instead.

• **Long-running queries** (> 30s) are the most common root cause of pool exhaustion. Kill them first, then investigate missing indexes.

• **Redis cluster failovers** (auth-service) resolve within 2-4 minutes if sentinel is healthy. Do NOT restart redis manually — it causes split-brain (failed in INC-022)."""