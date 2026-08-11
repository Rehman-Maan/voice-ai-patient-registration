# Voice AI Patient Registration System - Implementation Plan

## 1. Goal and definition of done

Build and deploy a voice-based patient registration application that a reviewer can call through a real U.S. phone number. The agent must collect and validate required demographics through natural conversation, allow corrections, read the complete record back for confirmation, save it only after confirmation, and make the persisted record available through a REST API.

The submission is complete when all of the following are true:

- A reviewer can call a live U.S. number and finish a registration without developer assistance.
- Required fields are collected; optional groups are offered without making the call unnecessarily long.
- Invalid values trigger a precise re-prompt for only the affected field.
- Corrections, interruptions, spelling, out-of-order details, restart requests, and save failures are handled gracefully.
- The agent reads back the normalized record and obtains explicit confirmation before writing it.
- The record remains available after service restarts and is retrievable through the documented REST API.
- All five CRUD endpoints, filters, soft deletion, response envelopes, and server-side validation work.
- The repository contains the agent prompt, setup/deployment instructions, architecture, trade-offs, limitations, tests, and live demo details.

## 2. Requirements distilled from the challenge

### Mandatory voice behavior

- Real dialable U.S. phone number.
- LLM-driven, conversational intake rather than keypad IVR.
- Understand varied phrasing and information supplied out of order.
- Ask clarifying questions when a value is ambiguous or incomplete.
- Accept corrections, including spelled names.
- Validate data during the call and specifically re-prompt invalid fields.
- Read back all collected data before saving.
- Save only after an explicit confirmation such as "yes, that is correct."
- Announce whether the save succeeded, then end the call gracefully.

### Mandatory patient fields

| Field | Required | Rule |
|---|---:|---|
| `first_name` | Yes | 1-50 characters; letters, spaces only where appropriate, hyphens, apostrophes |
| `last_name` | Yes | 1-50 characters; letters, spaces only where appropriate, hyphens, apostrophes |
| `date_of_birth` | Yes | Real date, `MM/DD/YYYY` at API boundary, not in the future |
| `sex` | Yes | `Male`, `Female`, `Other`, or `Decline to Answer` |
| `phone_number` | Yes | Valid U.S. 10-digit number; store normalized digits or E.164 consistently |
| `email` | No | Valid email address |
| `address_line_1` | Yes | Non-empty street address |
| `address_line_2` | No | Apartment, suite, or unit |
| `city` | Yes | 1-100 characters |
| `state` | Yes | Valid two-letter U.S. state abbreviation |
| `zip_code` | Yes | Five digits or ZIP+4 |
| `insurance_provider` | No | Insurance company name |
| `insurance_member_id` | No | Alphanumeric member/subscriber identifier |
| `preferred_language` | No | Defaults to `English` |
| `emergency_contact_name` | No | Full name |
| `emergency_contact_phone` | No | Valid U.S. 10-digit number |
| `patient_id` | Auto | UUID |
| `created_at` | Auto | UTC timestamp |
| `updated_at` | Auto | UTC timestamp, refreshed on update |

Add `deleted_at` as a nullable UTC timestamp because soft deletion is a required API behavior.

### Mandatory API behavior

- `GET /patients` returns non-deleted patients and supports `last_name`, `date_of_birth`, and `phone_number` filters.
- `GET /patients/{patient_id}` returns one non-deleted patient by UUID.
- `POST /patients` creates and returns a patient.
- `PUT /patients/{patient_id}` performs a partial update despite the method name being `PUT` in the assignment.
- `DELETE /patients/{patient_id}` sets `deleted_at`; it never removes the row.
- Inputs are validated server-side independently of the agent.
- Responses use `{ "data": ..., "error": null }` on success and `{ "data": null, "error": { ... } }` on failure.
- Use meaningful `200`, `201`, `400`, `404`, `422`, and `500` responses.

## 3. Recommended architecture and stack

Use the smallest architecture that is dependable under review:

```text
Reviewer phone
    |
    v
Vapi U.S. number + managed STT/TTS
    |
    v
LLM assistant + documented system prompt
    |
    | HTTPS tool calls
    v
FastAPI application on Railway or Render
    |
    +-- REST routes
    +-- validation and service layer
    +-- Vapi tool/webhook routes
    +-- structured logs
    |
    v
Managed PostgreSQL
```

### Stack choices

- **Voice platform: Vapi.** It provisions/attaches a number and handles telephony, streaming STT/TTS, interruptions, endpointing, and LLM tool calls. This preserves time for conversation design and resilience, which account for a large part of the score.
- **Backend: Python 3.12 + FastAPI.** Strong typed validation, automatic OpenAPI documentation, concise async endpoints, and rapid testing.
- **Models/validation: Pydantic v2.** Use separate create, update, database, and public-response schemas.
- **Persistence: PostgreSQL + SQLAlchemy 2 + Alembic.** A managed database gives restart-safe persistence and production-oriented constraints without excessive complexity.
- **LLM: a low-latency tool-capable OpenAI model supported by Vapi.** Pin the exact model in configuration and document it; prioritize latency and tool reliability over benchmark strength.
- **Testing: Pytest + FastAPI TestClient/httpx.** Run database integration tests against a dedicated test database or transactional PostgreSQL fixture.
- **Deployment: Railway is the first choice** because the API and PostgreSQL can live in one project. Render is a suitable fallback.

Do not build custom STT/TTS or a custom audio streaming stack for this assessment. It increases failure modes without improving the core score.

## 4. Repository structure

```text
voice-ai-patient-registration/
|-- app/
|   |-- main.py                 # FastAPI startup, exception handlers, health route
|   |-- config.py               # Environment-based settings
|   |-- database.py             # Engine and session dependency
|   |-- models/
|   |   `-- patient.py          # SQLAlchemy patient model
|   |-- schemas/
|   |   `-- patient.py          # Create/update/read/filter schemas
|   |-- api/
|   |   |-- patients.py         # Required REST endpoints
|   |   `-- voice.py            # Vapi tool/webhook endpoints
|   |-- services/
|   |   `-- patients.py         # Shared business rules and persistence
|   |-- validation/
|   |   `-- demographics.py     # Names, phones, DOB, state, ZIP normalization
|   |-- prompts/
|   |   `-- patient_intake.md   # Version-controlled system prompt
|   `-- logging.py              # Structured logs and sensitive-field policy
|-- alembic/
|-- tests/
|   |-- test_patients_api.py
|   |-- test_validation.py
|   |-- test_voice_tools.py
|   `-- test_conversation_scenarios.md
|-- scripts/
|   |-- seed.py
|   `-- smoke_test.py
|-- .env.example
|-- .gitignore
|-- alembic.ini
|-- Dockerfile
|-- pyproject.toml
|-- README.md
`-- IMPLEMENTATION_PLAN.md
```

Keep HTTP handlers thin. Both public routes and voice tools must call the same patient service and validators so behavior cannot drift.

## 5. Database design

Create a `patients` table with:

- UUID primary key generated server-side.
- `DATE` for date of birth and timezone-aware UTC timestamps for audit fields.
- An enum or checked string for `sex`.
- bounded `VARCHAR` columns matching specified maximum lengths.
- non-null constraints for every required field.
- normalized phone fields suitable for exact filtering.
- nullable optional fields.
- `preferred_language NOT NULL DEFAULT 'English'`.
- `created_at` and `updated_at` generated by the application/database.
- nullable `deleted_at`.
- indexes on `last_name`, `date_of_birth`, and `phone_number` because these are required filters.

Important design decisions:

- Do not make phone number globally unique. Family members can share a number; duplicate detection should return possible matches rather than force a database collision.
- Filter all normal reads with `deleted_at IS NULL`.
- Normalize U.S. phones before storage and comparison. Return a consistent display form through the API.
- Store dates as dates, never formatted strings. Format them only at the API or speech layer.
- Enforce rules twice: friendly Pydantic errors at the service boundary and durable database constraints where practical.

Optional bonus tables can be added only after the core flow is stable:

- `call_sessions`: call ID, status, transcript/summary, linked patient ID, timestamps, and failure reason.
- `appointments`: mock appointment slot and patient link.

## 6. API contract

### Envelope

Success:

```json
{
  "data": {},
  "error": null
}
```

Failure:

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "details": [{ "field": "date_of_birth", "message": "Date of birth cannot be in the future." }],
    "request_id": "..."
  }
}
```

### Endpoint details

1. `GET /health`
   - Verify process and database connectivity for deployment checks.
2. `GET /patients`
   - Optional exact normalized filters: `last_name`, `date_of_birth`, `phone_number`.
   - Case-insensitive last-name matching.
   - Exclude soft-deleted rows.
   - Return an array; optional pagination is acceptable but should not break the required shape.
3. `GET /patients/{id}`
   - Validate UUID syntax; return `404` if absent or deleted.
4. `POST /patients`
   - Accept required and optional demographic fields only.
   - Reject client-provided IDs or audit timestamps.
   - Normalize, validate, create, and return `201`.
5. `PUT /patients/{id}`
   - Treat omitted values as unchanged.
   - Reject an empty update with `400`.
   - Re-run validation on the merged record and refresh `updated_at`.
6. `DELETE /patients/{id}`
   - Set `deleted_at` and `updated_at`; return the deleted record or a documented success object.

Add automatic exception handlers so validation, not-found, database, and unexpected errors always use the same envelope. Do not expose stack traces or secrets.

## 7. Voice-agent tools and conversation state

Prefer small, explicit tools over allowing the LLM to invent API payloads:

- `validate_patient_field(field, value)` normalizes and validates one value, returning a speakable reason on failure.
- `find_patient_by_phone(phone_number)` returns zero or more safe match summaries for duplicate detection.
- `create_patient(patient)` calls the shared patient service only after confirmation.
- `update_patient(patient_id, changes)` is used when a returning caller agrees to update.

If Vapi can maintain structured variables reliably, keep the draft patient in assistant state. Otherwise add a draft/session endpoint keyed by Vapi call ID. Never create a final patient record field by field.

### Conversation state machine

Although the interaction is LLM-driven, the prompt must enforce these states:

1. **Greeting and consent:** explain that this is a demo patient-registration assistant and ask to begin. Tell callers not to use real sensitive information for the assessment demo.
2. **Required-field collection:** ask one logical question at a time, while accepting and retaining extra fields volunteered in the same utterance.
3. **Immediate validation:** normalize each value and re-prompt only invalid/ambiguous items.
4. **Duplicate check:** once the primary phone is valid, search for matches. If a likely match exists, name it and offer update versus new registration.
5. **Optional-field offer:** offer insurance, emergency contact, and preferred language as groups. Respect a decline immediately.
6. **Final read-back:** read every collected field in digestible groups, explicitly noting skipped optional fields.
7. **Correction loop:** if anything is wrong, update the named field, validate it, and perform a new read-back of the changed field plus a concise final summary.
8. **Explicit confirmation gate:** call create/update only after an unambiguous confirmation.
9. **Completion:** on success, give the first-name confirmation and end gracefully. On failure, apologize, explain that the record was not saved, offer one retry, and provide a graceful close.

### Prompt rules that must be version-controlled

- Never fabricate or infer a value the caller did not provide, except the documented default language.
- Never say a record was saved until the tool reports success.
- Do not call a write tool before explicit final confirmation.
- Ask concise questions and avoid reciting internal field names.
- Allow barge-in and respond to the caller's latest correction.
- Resolve relative/ambiguous dates by asking for month, day, and four-digit year.
- Repeat critical strings slowly: names, phone, email, member ID, street address, and ZIP.
- For spelling, preserve the corrected spelling rather than the earlier transcription.
- If asked to restart, clear the draft only after confirming the restart request.
- If the caller wants to stop, discard the unconfirmed draft and end politely.
- After two failed attempts on the same field, explain the expected format with a short example.
- Avoid medical advice and explain that the agent only handles registration.

## 8. Validation and normalization

Implement shared deterministic validation rather than trusting the LLM:

- **Names:** trim whitespace; normalize repeated spaces; allow Unicode letters if the library handles them safely plus spaces, apostrophes, and hyphens; enforce length. This is slightly more inclusive than ASCII-only while satisfying the intent.
- **Date of birth:** parse common spoken forms into a date, reject impossible/future dates, and serialize as `MM/DD/YYYY` if the challenge-facing API requires that display.
- **Sex:** map common utterances to the four exact stored enum values; never infer from a name or voice.
- **Phone:** use a phone-number library with U.S. region; reject extensions unless explicitly supported; store normalized form and return a human-readable form.
- **Email:** validate syntax, then confirm it back character-by-character where ambiguity exists.
- **State:** map full state names to valid USPS abbreviations and reject other codes.
- **ZIP:** accept `12345` and `12345-6789` only.
- **Insurance member ID:** trim and allow documented alphanumeric separators; avoid silently dropping meaningful characters.
- **Optional dependencies:** if an emergency phone is given without a contact name, ask for the name, and vice versa; apply a documented all-or-none rule unless product requirements say otherwise.

Every error returned to the voice layer should include `field`, `normalized_value` when safe, and a short speakable message.

## 9. Resilience and edge cases

Explicitly design and test these reviewer-visible cases:

| Scenario | Required behavior |
|---|---|
| Invalid/future DOB | Explain the problem and ask only for DOB again |
| Three-digit or non-U.S. phone | Ask for a ten-digit U.S. number and provide a format example |
| Invalid state/ZIP/email | Identify the affected value and re-prompt only that field |
| Caller corrects spelling | Replace the old value and confirm the new spelling |
| Caller gives fields out of order | Capture all valid values and ask only for missing requirements |
| Caller interrupts read-back | Stop, handle the correction/question, then resume confirmation |
| Caller says "start over" | Confirm, clear draft state, restart without persisting |
| Caller declines optional fields | Skip them without pressure |
| Duplicate phone match | Offer update; do not overwrite without caller agreement |
| Ambiguous duplicate matches | Ask for another identifier such as DOB; do not expose excessive data |
| Database write timeout/failure | Never claim success; retry once if appropriate and close gracefully |
| Duplicate/retried tool request | Use Vapi call/tool ID as an idempotency key to prevent double creation |
| Call drops before confirmation | Do not create a patient; optionally keep an expiring draft/call log |
| Call drops after confirmed save | Idempotency prevents a retry from creating a duplicate |
| Malformed webhook or bad signature | Reject it and log a safe error |

Set reasonable database/tool timeouts. Add bounded retries only for transient failures; never blindly retry validation errors.

## 10. Security, privacy, and observability

The assignment explicitly says HIPAA compliance is not required and real patient data must not be stored. Still demonstrate sound engineering:

- Put all secrets in environment variables; commit only `.env.example`.
- Validate the Vapi webhook signature/shared secret if supported.
- Restrict CORS to the dashboard origin or disable it when no browser client is used.
- Use parameterized ORM queries and strict request schemas.
- Add request IDs and structured JSON logs.
- Log call ID, tool name, status, duration, validation failures, and the final collected payload as required by the challenge.
- Because the payload is sensitive in a real system, mark full-payload logging as **assessment-only**, use synthetic data, and document how production would redact/encrypt it.
- Never log API keys, authorization headers, full stack traces to callers, or raw payment/medical information.
- Add basic rate limiting if time permits, but do not let it delay the working call path.

Required environment variables should include:

```text
DATABASE_URL=
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
VAPI_PHONE_NUMBER_ID=
VAPI_WEBHOOK_SECRET=
OPENAI_API_KEY=          # only if the selected Vapi configuration requires it
APP_BASE_URL=
LOG_LEVEL=INFO
```

## 11. Testing strategy

### Automated tests

1. **Validation unit tests**
   - Boundary lengths and punctuation for names.
   - Leap dates, impossible dates, and future DOB.
   - All sex enum mappings.
   - Valid/invalid phones, ZIP/ZIP+4, email, and every state abbreviation.
2. **API integration tests**
   - Create success and every required-field failure.
   - List and each required filter.
   - Retrieve present/missing/deleted records.
   - Partial update, invalid update, and `updated_at` behavior.
   - Soft delete and proof the row still exists in the database but is absent from normal reads.
   - Envelope and status-code consistency.
3. **Voice tool tests**
   - Tool payload validation, auth/signature rejection, service errors, and idempotent repeats.
   - Duplicate phone lookup and update flow.

### Manual call test matrix

Conduct and document at least these calls using synthetic data:

1. Happy path with only required fields.
2. Optional insurance and emergency contact path.
3. Invalid DOB and phone, then successful correction.
4. Spelled-name correction during confirmation.
5. Several fields supplied in one utterance and out of order.
6. Interruption during read-back.
7. "Start over" midway through the call.
8. Returning phone number and accepted update.
9. Returning phone number but request to create a separate family member.
10. Simulated backend failure or timeout.
11. Call disconnect before confirmation; verify no patient was created.
12. Second call after an app restart; verify the first record still exists.

For each call, capture expected result, actual result, call ID, API/DB verification, and any prompt adjustment. Re-run the happy path after every prompt or tool-schema change.

## 12. Deployment plan

1. Create the managed PostgreSQL database and record the internal `DATABASE_URL`.
2. Deploy the FastAPI container to Railway/Render.
3. Run Alembic migrations as a release/startup step with failure visibility.
4. Verify `GET /health`, API docs, CRUD behavior, persistence across a redeploy, and public TLS.
5. Create/configure the Vapi assistant with the version-controlled prompt and exact tool schemas.
6. Set Vapi tool URLs to the deployed HTTPS backend and configure webhook authentication.
7. Provision or attach a U.S. phone number.
8. Place external test calls from at least two phones, including one noisy/interrupting call.
9. Confirm tool calls, latency, payloads, database rows, and API reads in logs.
10. Add the final phone number, API base URL, repository URL, and test notes to the README.

Keep a local fallback using Docker Compose or a local API plus a tunnel. If phone provisioning fails, document the vendor error, retain screenshots/logs, and provide exact local testing steps as allowed by the FAQ.

## 13. Execution order and time budget

The challenge states a three-hour maximum, so prioritize a flawless core before bonuses.

### First 15 minutes - scaffold and accounts

- Confirm Vapi, hosting, database, and LLM credentials.
- Create the repository, dependency file, environment template, and deployment project.
- Write the initial schema and lock the API contract.

### Minutes 15-60 - database and API

- Implement model, migration, validators, envelopes, error handlers, and service layer.
- Implement all required routes and filters.
- Add focused API/validation tests.
- Deploy early and verify persistence rather than waiting until the end.

### Minutes 60-105 - voice integration

- Create the assistant prompt and tool schemas.
- Implement validation, lookup, create, and update tools.
- Attach the live number and complete the first happy-path call.

### Minutes 105-140 - conversational quality

- Tune pacing, question grouping, barge-in, spelled-name correction, optional-field opt-in, read-back, and explicit confirmation.
- Add restart behavior and out-of-order field handling.

### Minutes 140-160 - resilience

- Add/verify idempotency, duplicate lookup, database failure response, and disconnect behavior.
- Run the highest-value negative calls.

### Minutes 160-180 - submission readiness

- Complete README and architecture/trade-off notes.
- Run automated tests and the deployment smoke test.
- Restart/redeploy and prove prior data survives.
- Make one final external call and query its record through the public API.
- Check the repository for secrets and prepare the submission message.

If time slips, cut in this order: dashboard, appointment scheduling, transcript storage, Spanish support, seed data, then duplicate-update bonus. Never cut confirmation, validation, persistence, required CRUD, graceful errors, or documentation.

## 14. README and reviewer handoff

The README must contain:

- One-paragraph project overview.
- Live U.S. phone number and calling instructions.
- Live API base URL and example `curl` commands for all endpoints/filters.
- Architecture diagram and request/call flow.
- Exact technology choices and why they fit the time constraint.
- Local setup, migrations, tests, seed, and run commands.
- Vapi assistant/number/tool configuration steps.
- Complete environment-variable table without values.
- Data model and validation rules.
- Conversation design and a link to the full prompt.
- Deployment/redeployment instructions.
- Security/privacy note: synthetic data only, assessment logging, not HIPAA-ready.
- Known limitations and deliberate trade-offs.
- Manual test evidence or a concise test matrix.
- "Next Steps" section.

Prepare the final submission with exactly:

- Repository URL.
- Phone number to call.
- API base URL.
- Credentials or special testing notes, if any.

## 15. Evaluation-aligned acceptance checklist

### Working System - 20%

- [ ] Live number answers consistently.
- [ ] A complete call creates exactly one record.
- [ ] Public API retrieves the newly created record.
- [ ] Record survives API restart/redeployment and a second call.

### Conversational Quality - 20%

- [ ] Natural short prompts, no rigid IVR wording.
- [ ] Corrections and spelled names work.
- [ ] Out-of-order and multi-field utterances work.
- [ ] Barge-in works during questions and read-back.
- [ ] Every write is preceded by complete read-back and explicit confirmation.

### Technical Architecture - 20%

- [ ] Telephony, prompt/tool orchestration, service, API, and data layers are separated.
- [ ] Database types, nullability, constraints, indexes, and soft deletion are correct.
- [ ] Required REST endpoints, filters, validation, envelopes, and status codes are correct.
- [ ] Prompt and tool contracts are version-controlled and documented.

### Code Quality and Documentation - 20%

- [ ] Code is typed, consistently formatted, and organized around shared services.
- [ ] README is sufficient for another engineer to run and deploy the system.
- [ ] Tests pass from a clean checkout.
- [ ] Trade-offs, limitations, prompt, and next steps are documented.

### Edge Cases and Resilience - 20%

- [ ] Invalid DOB/phone/state/ZIP/email produces field-specific recovery.
- [ ] Start-over and early-exit behavior is safe.
- [ ] Database failures produce a spoken error and never false success.
- [ ] Drop before confirmation creates no patient.
- [ ] Idempotent retries cannot create duplicate rows.

## 16. Bonus priority after the core passes

1. Duplicate detection and update offer - high value because it directly strengthens the second-call experience.
2. Automated tests - high value for architecture, code quality, and resilience evidence.
3. Transcript/call summary linked through `call_sessions` - useful observability, with synthetic data only.
4. Spanish flow - valuable but requires end-to-end prompt, STT/TTS, validation, and manual-call verification.
5. Small read-only dashboard - visually useful but lower value than call reliability.
6. Mock appointment scheduling - implement last because it expands scope beyond the core registration system.

## 17. Final go/no-go gate

Do not submit until one synthetic patient has passed this exact proof:

1. Register through the public phone number.
2. Correct at least one field during the call.
3. Hear a complete read-back and explicitly confirm.
4. Hear a genuine tool-backed success message.
5. Retrieve the record from the public API.
6. Restart/redeploy the backend.
7. Retrieve the same record again.
8. Call again with the same phone and verify the existing-record behavior or, at minimum, verify no previous data was lost.

This sequence demonstrates the central promise of the assignment and directly covers the most important reviewer checks.
