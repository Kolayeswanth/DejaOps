# Testing

## Framework and organization

The repository uses pytest. Two files under `tests/` cover rejected-by-memory behavior, Hindsight retain boundaries, recall metadata, triage prompt propagation, display selection, provenance, and no-memory cases.

## Validation commands

```powershell
python validate_data.py
$env:PYTHONPATH='.'
python -m pytest -q
```

`check_setup.py` is the external smoke check for Hindsight and Groq and requires configured credentials. `streamlit run app.py` is the manual UI check.

## Current validation snapshot

- Data validation passes: 120 incidents, 20 runbooks, and 10 demo alerts satisfy the checked-in validation rules.
- The repository contains 15 test functions.
- With the repository root on `PYTHONPATH`, the current pytest snapshot is 10 passed and 5 failed. The failures are in existing agent/provenance expectations around natural-language action parsing, failure reasons, incident ID extraction, and display-memory selection.
- A plain `pytest -q` from this Windows checkout does not collect imports because the repository root is not placed on the module path; use `python -m pytest -q` with `PYTHONPATH=.` for the current module layout.

The exact status is recorded here so validation remains reproducible while the documentation describes the implemented behavior accurately.

## High-value scenarios

- Failed historical remediations are surfaced as rejected memory evidence.
- Worked/Failed feedback reaches the Hindsight retain boundary.
- Recall metadata is preserved.
- Memory context reaches the reasoning prompt.
- A new alert with no recalled history does not receive fabricated evidence.
- Incident IDs and action outcomes can be mapped into provenance when the recalled text supports it.

## Additional validation opportunities

Future test additions can cover live Hindsight contracts, provider response shapes, seed-to-bank flows, browser interactions, security/redaction behavior, and runtime measurements.
