# Security

## Secrets and credentials

Store `HINDSIGHT_URL`, `HINDSIGHT_API_KEY`, and `GROQ_API_KEY` in environment variables or a local `.env` excluded from version control. `.env.example` contains empty names only. Do not paste credential values into issues, screenshots, prompts, or retained memories.

## Data handling

The checked-in Northwind Payments dataset is synthetic. Real operational data may contain credentials, tokens, customer data, or sensitive infrastructure details. Add redaction and retention policies before loading real incidents into a shared memory bank.

## External services

Alert text and recalled memory are sent to the configured Groq and Hindsight services according to their APIs. Review provider data handling, network controls, and organization policy before using sensitive incident content.

## User-controlled input

Alert text and taught postmortems are user-controlled. Treat them as untrusted content, keep model instructions separate from data, and validate structured model output before rendering or acting on it. `app.py` HTML-escapes displayed model-derived text in the current result views.

## Operational actions

The current application recommends and records outcomes; it does not execute infrastructure commands. Any future action executor should add authentication, authorization, approval, command allowlists, audit logs, and failure handling.

## Access and lifecycle

The current Streamlit app does not implement application-user authentication, authorization, memory deletion, or correction workflows. A deployment that serves multiple teams should add identity, bank isolation, retention, correction, and audit policies before exposing shared operational memory.
