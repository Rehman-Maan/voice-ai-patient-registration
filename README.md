# Voice AI Patient Registration

A deployable take-home assessment implementation that registers synthetic patients through a natural phone conversation, validates and confirms demographics, persists records to PostgreSQL, and exposes a REST API.

> Assessment demo only. Do not provide real patient or medical information. This project is not HIPAA-ready.

## Live demo

- **Phone:** `+1 (732) 825-8211`
- **API base URL:** `https://voice-ai-patient-registration-production-70b4.up.railway.app`
- **API documentation:** `https://voice-ai-patient-registration-production-70b4.up.railway.app/docs`
- **Health check:** `https://voice-ai-patient-registration-production-70b4.up.railway.app/health`

## Architecture

```text
Caller -> Vapi phone/STT/TTS -> LLM assistant -> HTTPS voice tools
                                                   |
                                                   v
                              FastAPI routes -> patient service -> PostgreSQL
```

Vapi handles the real-time media path and barge-in. FastAPI owns deterministic validation, REST and voice interfaces, error envelopes, and shared business rules. PostgreSQL provides restart-safe persistence. The assistant prompt is version-controlled in [app/prompts/patient_intake.md](app/prompts/patient_intake.md).

## Features

- Required and optional assessment demographics with server-side validation.
- Phone normalization, DOB/state/ZIP/name/email validation, and emergency-contact consistency.
- List, retrieve, create, partial update, and soft delete.
- Required filters by last name, DOB, and phone.
- Consistent JSON success/error envelopes and request IDs.
- Protected Vapi tool routes, duplicate lookup, and idempotent voice creation.
- PostgreSQL migration plus SQLite convenience for local development.
- Automated validation, API, soft-delete, filter, auth, and voice-tool tests.

## Local setup

Python 3.11-3.12 is recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Or run the API and PostgreSQL together:

```bash
docker compose up --build
```

Open `http://localhost:8000/docs` and `http://localhost:8000/health`.

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `DATABASE_URL` | Deployment | SQLAlchemy URL; use `postgresql+psycopg://...` for PostgreSQL |
| `VAPI_WEBHOOK_SECRET` | Live voice | Shared secret accepted through `X-Vapi-Secret` or a Bearer credential |
| `APP_ENV` | No | Environment name |
| `LOG_LEVEL` | No | Python log level, default `INFO` |
| `ALLOWED_ORIGINS` | No | Comma-separated dashboard origins |

Vapi/LLM account keys normally remain in Vapi and do not need to enter this backend. Never commit `.env`.

## REST API

All normal responses use `{"data": ..., "error": null}`. Failures use `{"data": null, "error": {...}}`.

```bash
# List/filter
curl "http://localhost:8000/patients?last_name=Patient"
curl "http://localhost:8000/patients?date_of_birth=1992-04-15"
curl "http://localhost:8000/patients?phone_number=2025550147"

# Create
curl -X POST http://localhost:8000/patients \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: example-create-1" \
  -d '{"first_name":"Demo","last_name":"Patient","date_of_birth":"1992-04-15","sex":"Decline to Answer","phone_number":"2025550147","address_line_1":"100 Demo Avenue","city":"Washington","state":"DC","zip_code":"20001"}'

# Retrieve, partially update using the assignment-required PUT, and soft-delete
curl http://localhost:8000/patients/PATIENT_UUID
curl -X PUT http://localhost:8000/patients/PATIENT_UUID -H "Content-Type: application/json" -d '{"city":"Arlington"}'
curl -X DELETE http://localhost:8000/patients/PATIENT_UUID
```

## Tests

```bash
pytest
python scripts/smoke_test.py
```

The manual call matrix is in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). At minimum, test a happy path, invalid DOB/phone, spelling correction, out-of-order fields, interruption, restart, duplicate phone, backend failure, and disconnect before confirmation.

## Vapi configuration

1. Deploy the backend over HTTPS and set a long random `VAPI_WEBHOOK_SECRET`.
2. Create a Vapi assistant using the full prompt in `app/prompts/patient_intake.md`.
3. Create the three functions in `vapi/tool-definitions.json`, replacing `{{APP_BASE_URL}}`.
4. Create a Vapi Bearer Token credential containing the same value as `VAPI_WEBHOOK_SECRET` and assign it to every custom tool.
5. Use a low-latency tool-capable model, English transcriber, and natural voice. Enable interruptions/barge-in.
6. Attach a provisioned U.S. number to the assistant.
7. Call with synthetic data, inspect tool logs, and confirm the record through `GET /patients`.

Live Vapi calls provide their call ID in the tool-call envelope. Creation derives an idempotency key from it, so a repeated tool request cannot create a duplicate row.

## Deployment

Railway is the recommended path:

1. Push this repository to GitHub.
2. Create a Railway project from the repository and add PostgreSQL.
3. Set `DATABASE_URL` to the PostgreSQL URL using the `postgresql+psycopg://` scheme.
4. Set `VAPI_WEBHOOK_SECRET` and deploy. The Docker command runs `alembic upgrade head` before Uvicorn.
5. Run `APP_BASE_URL=https://... python scripts/smoke_test.py`.
6. Configure Vapi tools and place an external test call.
7. Verify the live health endpoint, complete a synthetic registration by phone, and retrieve it through the public API.

## Design decisions and trade-offs

- Managed Vapi replaces custom STT/TTS streaming so effort is focused on integration and conversation quality.
- PostgreSQL is used in deployment; SQLite exists only for fast local setup.
- Phone numbers are indexed but not unique because family members can share a number. The agent presents matches instead.
- The challenge specifies `PUT` with partial updates, so the endpoint follows that contract even though `PATCH` is conventional.
- Full demographic payload logging requested by the assessment should use synthetic data only. A real system would redact logs, encrypt data, add access controls/audit trails, complete vendor agreements, and undergo a HIPAA security review.
- Voice state currently lives in the assistant call context. A production version would persist expiring draft sessions to recover from disconnects.

## Known limitations / next steps

- The live Vapi number is inbound-only under the assessment account.
- Full state-name-to-abbreviation conversion is left to the agent prompt; the API deliberately accepts only canonical two-letter codes.
- Unicode personal names are not yet supported by the conservative assessment validator.
- Add Vapi-native signature verification when the selected account/tool API exposes its exact signing format.
- Add persisted call sessions/transcripts, Spanish conversation tests, a read-only dashboard, and mock scheduling only after the core call path is stable.
