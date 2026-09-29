# Deployment

## Local runtime

The checked-in runtime is a local Streamlit application. Install the dependencies, configure the environment, validate and seed the data, run the setup check, then start Streamlit:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python validate_data.py
python seed.py
python check_setup.py
streamlit run app.py
```

## Required configuration

- `HINDSIGHT_URL`: Hindsight service endpoint.
- `HINDSIGHT_API_KEY`: Hindsight credential.
- `GROQ_API_KEY`: Groq credential.
- `DEJAOPS_BANK`: optional bank ID; `memory.py` defaults to `dev-test` when absent.

## Data initialization

`seed.py` creates the bank when needed, retains runbooks and incidents, and records completed IDs in `data/.seeded_<bank>.txt`. Keep that progress file aligned with the target bank when reseeding.

## Runtime architecture

There is no Dockerfile, CI workflow, deployment manifest, or separate HTTP service in the repository. A hosted deployment can wrap the same Streamlit process, but should supply secret management, network policy, identity, bank isolation, logging, and data retention controls appropriate to its environment.
