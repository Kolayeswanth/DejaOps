# DejaOps

Incident commander with deja vu: seed past outages and runbooks into Hindsight memory, then diagnose a live incident against what the team has already seen.

```
dejaops/
  data/incidents.json
  data/runbooks.json
  memory.py
  agent.py
  app.py
  seed.py
  .env.example
  README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `HINDSIGHT_*` and `LLM_API_KEY`. Point `HINDSIGHT_BASE_URL` at a running Hindsight server (local default is `http://localhost:8888`).

## Seed memory

```bash
python seed.py
```

This retains every record in `data/incidents.json` and `data/runbooks.json` into bank `HINDSIGHT_BANK_ID`.

## Run the API

```bash
uvicorn app:app --reload --port 8000
```

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness and bank id |
| POST | `/seed` | Same as `python seed.py` |
| POST | `/diagnose` | Recall similar memories, match runbooks, ask the LLM |
| POST | `/recall` | Search the bank |
| POST | `/reflect` | Ask Hindsight to synthesize patterns |

Example diagnose body:

```json
{
  "title": "Checkout timeouts",
  "service": "payments-api",
  "severity": "SEV-2",
  "symptoms": "too many connections on Postgres, p99 is 4s",
  "tags": ["postgres"],
  "persist": false
}
```
