# KrishiMitra API

Backend API for the KrishiMitra soybean crop-health orchestrator (FastAPI). This document describes every
endpoint as implemented in `backend/app/api/`. Example responses are real output from a running server.

- [Quick facts](#quick-facts)
- [Authentication](#authentication)
- [Conventions](#conventions)
- [CORS (browser access)](#cors-browser-access)
- [Endpoint index](#endpoint-index)
- [Endpoints](#endpoints)
- [Reference: states, intents, routes, reasons](#reference-states-intents-routes-reasons)
- [Schemas](#schemas)
- [Known gaps](#known-gaps)

## Quick facts

| | |
|---|---|
| Base URL (local) | `http://127.0.0.1:8000` (uvicorn's default: `uvicorn app.main:app`). No deployed environment yet; substitute your host. |
| Path prefix | All application routes are under `/api`. Only `/health` is outside it. No version segment. |
| Format | JSON (`application/json`). Image uploads use `multipart/form-data`. UTF-8, including Marathi text. |
| Auth | Supabase JWT in `Authorization: Bearer <access_token>` on every `/api/*` route. |
| CORS | Enabled for the origins in `CORS_ALLOWED_ORIGINS` (default: the local Next.js dev server). See [CORS](#cors-browser-access). |
| Interactive docs | `/docs` (Swagger UI), `/redoc`, `/openapi.json`. These are public and expose the schema. |
| Identifiers / time | UUIDs; timestamps are ISO 8601 (`2026-10-01T02:00:00+05:30` or `...Z`); dates are `YYYY-MM-DD`. |
| Limits | Images: JPEG, PNG or WebP, max 10 MB. Text fields: see [CaseCreate](#cases-and-images). |

## Authentication

Every `/api/*` route requires a valid Supabase access token. `/health`, `/docs`, `/redoc` and
`/openapi.json` are public.

```http
GET /api/cases HTTP/1.1
Authorization: Bearer eyJhbGciOi...
```

**Getting a token.** The backend has no login endpoint. Sign in through Supabase Auth from the client and send the
session's `access_token`, for example `supabase.auth.signInWithPassword(...)` then `data.session.access_token`.
Tokens expire; refresh through Supabase.

**How the backend verifies it** (`backend/app/api/auth.py`):

| Check | Rule |
|---|---|
| Signature | If `SUPABASE_JWT_SECRET` is set: HS256 with that secret (legacy Supabase projects). Otherwise: ES256/RS256 keys fetched from `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. If neither is configured, every request gets **503**. |
| Audience | `aud` must be `authenticated`. |
| Expiry | `exp` must be in the future (**401** `Token expired`). |
| Subject | `sub` must be a UUID. It becomes the user id that owns cases. |

**Roles.** Every signed-in user is a farmer. A user is an **expert** only if the token has
`app_metadata.role == "expert"`. `app_metadata` can only be set server-side (for example in the Supabase SQL editor);
`user_metadata`, which users can edit themselves, is ignored. Exact match only: `"Expert "` does not count.

```sql
update auth.users set raw_app_meta_data = raw_app_meta_data || '{"role":"expert"}' where email = 'expert@example.com';
```

The user must sign in again to get a token that carries the role.

| Access level | Routes |
|---|---|
| Public | `GET /health` |
| Any signed-in user | `/api/cases/**`, `/api/runs/{id}`, `/api/weather` |
| Expert only (403 otherwise) | `/api/expert/**`, `/api/metrics/**` |

**Ownership.** Farmers can only see their own cases, images, analyses and runs. Another user's resource returns
**404** (not 403), so IDs cannot be probed. Experts do **not** get access to farmers' cases through the farmer routes;
they use `/api/expert/**`.

**Local testing without Supabase:** set `SUPABASE_JWT_SECRET` in `backend/.env`, then
`python scripts/dev_token.py` (farmer) or `python scripts/dev_token.py --expert`. It refuses to run when
`ENVIRONMENT=production`.

## Conventions

**Errors.** Non-2xx responses have a `detail` field. It is a string for most errors, a list of validation issues for
`422` on request bodies, and an object for the unknown-district `422`.

| Status | When | `detail` |
|---|---|---|
| 400 | Uploaded file is empty | `"Empty file"` |
| 401 | No/invalid/expired token. Response has header `WWW-Authenticate: Bearer` | `"Missing bearer token"`, `"Invalid token"`, `"Token expired"`, `"Token has no valid subject"` |
| 403 | Signed in but not an expert | `"Expert role required"` |
| 404 | Resource missing **or not yours** | `"Case not found"`, `"Run not found"`, `"Case has not been analyzed yet"`, `"No escalation for this case"` |
| 409 | Review submitted but nothing is waiting for review | `"This case has no escalation waiting for review"` |
| 413 | Image over 10 MB | `"Image larger than 10 MB"` |
| 415 | File is not a real JPEG/PNG/WebP (checked from the bytes, not the `Content-Type` header) | `"File is not a valid JPEG, PNG or WebP image"`, `"Only JPEG, PNG or WebP images"` |
| 422 | Request validation failed | list of issues (below) |
| 503 | Server has no auth configuration | `"Auth is not configured on the server"` |

```json
{"detail": [{"type": "value_error", "loc": ["body", "crop"],
  "msg": "Value error, Only soybean is supported in this version of KrishiMitra", "input": "cotton", "ctx": {"error": {}}}]}
```

**Analyses are synchronous.** `POST .../analyze` and `POST .../follow-up` run the whole orchestrator inside the
request (typically tens to a few hundred milliseconds; weather can add up to 3 s if the live source is slow).

**No pagination.** List endpoints return everything they match.

**Nothing is a confirmed diagnosis.** Responses never contain pesticide names or doses. Image-based answers are always
labelled preliminary.

## CORS (browser access)

Browsers block a web app from calling this API on a different origin unless the API opts in. The backend allows the origins
listed in the `CORS_ALLOWED_ORIGINS` environment variable (comma-separated):

```bash
CORS_ALLOWED_ORIGINS=https://app.example.com,http://localhost:3000
```

| | |
|---|---|
| Default | `http://localhost:3000,http://127.0.0.1:3000` (a local Next.js dev server) |
| Format | Each origin is `scheme://host[:port]` with **no path and no trailing slash**. Anything else stops the server at startup with `Invalid CORS origin ...`. |
| Empty value | CORS off: only same-origin callers (or non-browser clients such as curl or a server) can use the API. |
| `*` | Accepted in development, **refused when `ENVIRONMENT=production`**. |
| Methods / headers | `GET`, `POST`, `OPTIONS`; request headers `Authorization` and `Content-Type` (JSON and multipart uploads both work). |
| Credentials | Not enabled. Authentication is the `Authorization: Bearer` header, not cookies, so the frontend must send that header itself. |
| Preflight | `OPTIONS` requests are answered **before** authentication, because browsers send them without a token. |
| Errors | `401`, `403`, `404` and `422` responses also carry `Access-Control-Allow-Origin`, so the frontend can read the error message. |
| Other origins | Get no `Access-Control-Allow-Origin` header; the browser then refuses to expose the response. Non-browser clients are unaffected, since CORS is enforced by browsers, not the server. |

CORS is not an access-control mechanism: every `/api/*` route still requires a valid token.

## Endpoint index

| Method | URL | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | Liveness check |
| POST | `/api/cases` | user | Create a case |
| GET | `/api/cases` | user | List your cases |
| GET | `/api/cases/{case_id}` | user (owner) | Get one case |
| POST | `/api/cases/{case_id}/images` | user (owner) | Upload a photo |
| POST | `/api/cases/{case_id}/analyze` | user (owner) | Run the orchestrator |
| POST | `/api/cases/{case_id}/follow-up` | user (owner) | Answer a question / add a photo, then re-run |
| GET | `/api/cases/{case_id}/analysis` | user (owner) | Latest analysis |
| GET | `/api/runs/{routing_run_id}` | user (owner) | Full route trace of one analysis |
| GET | `/api/weather` | user | District weather with provenance |
| GET | `/api/expert/cases` | expert | Expert queue |
| GET | `/api/expert/cases/{case_id}` | expert | One escalated case |
| POST | `/api/expert/cases/{case_id}/review` | expert | Submit a review |
| GET | `/api/metrics/overview` | expert | Headline orchestration metrics |
| GET | `/api/metrics/routes` | expert | Route distribution |
| GET | `/api/metrics/cost-latency` | expert | Cost and latency by step and tier |

Typical farmer flow: `POST /api/cases` → `POST .../images` → `POST .../analyze` → (if the state asks for more)
`POST .../follow-up` → `GET .../analysis`. Use `GET /api/runs/{id}` to see what the orchestrator did.

## Endpoints

### GET /health

Auth: none. Response `200`:

```json
{"status": "ok", "app": "KrishiMitra", "environment": "development"}
```

---

### POST /api/cases

Create a case. Auth: user. Body: `application/json`, [CaseCreate](#casecreate). Response `201`: [CaseOut](#caseout).

- `crop` must be soybean (case-insensitive, whitespace ignored; stored as `"soybean"`). Anything else is `422`.
- `symptom_context` is required (1 to 2000 chars): the farmer's question or description of the problem.
- `symptom_started_at` may not be in the future. `language` is `"en"` or `"mr"`.
- `district` is not validated here, but weather lookups need a known Maharashtra district (see `/api/weather`).

```bash
curl -X POST http://127.0.0.1:8000/api/cases \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"crop":"soybean","district":"Pune","symptom_context":"yellow spots on leaves","language":"en","growth_stage":"R3","symptom_started_at":"2026-09-25","recent_rainfall":"heavy rain last week"}'
```

```json
{
  "crop": "soybean", "district": "Pune", "symptom_context": "Will it rain in my area?", "language": "en",
  "growth_stage": "R3", "symptom_started_at": "2026-09-25", "recent_rainfall": "heavy rain last week",
  "description": "spots on lower leaves",
  "id": "6f735c81-721d-449f-af14-46b5f536a72d",
  "user_id": "6b577ed4-7ceb-4911-ad38-9d73461a146c",
  "decision_state": null,
  "created_at": "2026-09-30T20:30:44.346721Z"
}
```

Errors: `401`, `422`.

---

### GET /api/cases

List the caller's cases, newest first. Auth: user. Response `200`: [CaseOut](#caseout)`[]`. Errors: `401`.

### GET /api/cases/{case_id}

Auth: user (owner). Response `200`: [CaseOut](#caseout). `decision_state` is `null` until the case is analyzed, then
holds the state of the latest analysis. Errors: `401`, `404`, `422` (malformed UUID).

---

### POST /api/cases/{case_id}/images

Upload a photo. Auth: user (owner). Body: `multipart/form-data`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `kind` | `leaf_closeup` \| `field_overview` | yes | `leaf_closeup` is what the quality gate and vision model use. `field_overview` is optional extra evidence. |
| `file` | file | yes | JPEG, PNG or WebP, at most 10 MB. |

Response `201`: [ImageOut](#imageout). One image per kind is used: a newer upload of the same kind **replaces** the
older one for analysis (older files are kept in storage). Images are stored in the **private** `case-images` bucket at
`storage_path = <user_id>/<case_id>/<kind>-<image_id>.<ext>`; there is no endpoint to download them yet.

```bash
curl -X POST http://127.0.0.1:8000/api/cases/$CASE_ID/images \
  -H "Authorization: Bearer $TOKEN" -F kind=leaf_closeup -F "file=@leaf.jpg"
```

```json
{
  "id": "f577e0b8-8474-4548-8bb7-24438d625a3a", "case_id": "6f735c81-721d-449f-af14-46b5f536a72d",
  "kind": "leaf_closeup",
  "storage_path": "6b577ed4-.../6f735c81-.../leaf_closeup-f577e0b8-8474-4548-8bb7-24438d625a3a.jpg",
  "content_type": "image/jpeg", "size_bytes": 209652, "created_at": "2026-09-30T20:30:44.689696Z"
}
```

`content_type` in the response is detected from the file bytes, not taken from the request. Errors: `400` empty file,
`401`, `404`, `413`, `415`, `422` (bad `kind`).

---

### POST /api/cases/{case_id}/analyze

Run the orchestrator on the case as it is now (its text, latest images, and any follow-up answers). Auth: user (owner).
No request body. Response `200`: [CaseAnalysisOut](#caseanalysisout).

Each call creates a **new** analysis (a new `routing_run_id`); earlier ones stay retrievable. The orchestrator first
classifies the question's [intent](#intents-and-the-rules-that-pick-them), then takes that intent's
[route](#routes-orchestration-paths). See [Decision states](#decision-states) for how to read `state`.

**What the router reads.** The intent is decided from `symptom_context` + `description` + every follow-up answer,
joined together, and from whether a `leaf_closeup` photo exists. So extra words in `description` can change the route.
The example below is a case with symptom text "Will it rain in my area?", description "spots on lower leaves" and a photo:
it was routed to `image_diagnosis`, because "spots"/"leaves" plus the photo outweigh one "rain".

```jsonc
{
  "routing_run_id": "db64b52b-3915-4f7b-ab05-985de208001d",
  "case_id": "6f735c81-721d-449f-af14-46b5f536a72d",
  "state": "PRELIMINARY_GUIDANCE",
  "result": {
    "state": "PRELIMINARY_GUIDANCE",
    "reason": "mid_confidence",
    "message": "The photo may show signs of rust like. This is a preliminary observation, not a confirmed diagnosis. General information about rust_like symptoms in soybean (Pune). No treatment is suggested at this confidence level.",
    "follow_up_question": "Are the symptoms on older leaves, younger leaves, or both?",
    "preliminary_label": "rust_like",
    "confidence": 0.6477788090705872,
    "sources": [{"title": "Placeholder advisory: rust_like", "publisher": "placeholder", "verified": true, "stale": false, "structured": false}],
    "route_trace": ["intent_router", "quality_gate", "vision", "advisory", "decision:PRELIMINARY_GUIDANCE"],
    "calls": [
      {"route": "intent_router", "model": "keyword-intent-rules", "latency_ms": 0, "cost_usd": 0.0, "confidence": 0.8,
       "outcome": "ok", "error": null,
       "output": {"intent": "crop_health_image", "confidence": 0.8, "rule": "keywords:crop_health_image", "matched": ["spot", "leaves"]}},
      {"route": "quality_gate", "model": "opencv-quality-gate", "latency_ms": 35, "cost_usd": 0.0, "confidence": 1.0, "outcome": "ok", "error": null,
       "output": {"passed": true, "score": 100, "issues": [], "next_action": "continue",
                  "details": {"width": 640, "height": 480, "brightness": 107.7, "sharpness": 902.8, "leaf_ratio": 1.0}}},
      {"route": "vision", "model": "soybean-mobilenetv3-onnx", "latency_ms": 20, "cost_usd": 2e-05, "confidence": 0.6477788090705872, "outcome": "ok", "error": null,
       "output": [{"model_name": "soybean-mobilenetv3-onnx", "label": "rust_like", "confidence": 0.6477788090705872}]}
      // advisory call omitted here
    ],
    "total_latency_ms": 55, "total_cost_usd": 2e-05,
    "intent": "crop_health_image", "intent_confidence": 0.8, "intent_rule": "keywords:crop_health_image",
    "path": "image_diagnosis",
    "skipped_steps": ["weather"], "estimated_cost_saved_usd": 0.0
  },
  "created_at": "2026-09-30T20:30:45.260551Z",
  "expert": null
}
```

A weather question (no photo involved) never calls the quality gate, vision model or advisory lookup:

```jsonc
{
  "routing_run_id": "f95bb9e5-9cf5-4001-870d-ff34cfbd6787", "case_id": "711ed19a-f610-4747-a189-47fe386d7be3",
  "state": "PRELIMINARY_GUIDANCE",
  "result": {
    "state": "PRELIMINARY_GUIDANCE", "reason": "weather_context",
    "message": "Pune: now 23°C, humidity 92%. Rain expected in the next 24 hours: 1 mm (chance up to 71%). Source: Open-Meteo forecast-model data (live), for 01 Oct 02:00 IST. Weather information is indicative; check local forecasts before field work.",
    "follow_up_question": null, "preliminary_label": null, "confidence": null, "sources": [],
    "route_trace": ["intent_router", "weather", "decision:PRELIMINARY_GUIDANCE"],
    "calls": [ /* intent_router, weather */ ],
    "total_latency_ms": 187, "total_cost_usd": 0.0,
    "intent": "weather_context", "intent_confidence": 0.7, "intent_rule": "keywords:weather_context",
    "path": "weather", "skipped_steps": ["quality_gate", "vision", "advisory"], "estimated_cost_saved_usd": 2e-05
  },
  "created_at": "2026-09-30T20:31:05.372190Z", "expert": null
}
```

A pesticide/dose question never produces a name or a dose. With no verified source it escalates, and the response carries
the expert-side status:

```jsonc
{
  "routing_run_id": "6c763648-1844-4979-a1c2-6a57b38d7b8b", "case_id": "19463e4c-55e9-4c5a-9413-9a4f740f3a83",
  "state": "EXPERT_REVIEW",
  "result": {
    "state": "EXPERT_REVIEW", "reason": "treatment_needs_expert",
    "message": "KrishiMitra does not give pesticide names or doses. We do not have a verified source for this, so your question is being sent to a human agriculture expert. Meanwhile, contact your local Krishi Vigyan Kendra or agriculture officer before spraying anything.",
    "route_trace": ["intent_router", "advisory", "decision:EXPERT_REVIEW"],
    "intent": "treatment_safety", "intent_rule": "guard:treatment_safety", "path": "treatment_safety",
    "skipped_steps": ["quality_gate", "vision", "weather"]
    // remaining fields as above
  },
  "created_at": "2026-09-30T20:31:05.700124Z",
  "expert": {"status": "pending_review", "decision": null, "label": null, "notes": null, "recommended_advisory": null, "reviewed_at": null}
}
```

Errors: `401`, `404`.

---

### POST /api/cases/{case_id}/follow-up

The farmer answers a question and/or adds a photo, then the orchestrator re-runs. Auth: user (owner).
Body: `multipart/form-data`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `answer` | string, max 2000 | one of `answer` / `file` | Free text. Stored, and added to the text the router reads on this and later analyses. Blank text counts as missing. |
| `file` | file | one of `answer` / `file` | JPEG, PNG or WebP, max 10 MB. |
| `kind` | `leaf_closeup` \| `field_overview` | no (default `leaf_closeup`) | Which slot the photo fills. |

Response `200`: [CaseAnalysisOut](#caseanalysisout) for the **new** analysis. If an expert had asked for more
information (`expert.status == "awaiting_farmer"`), it moves to `follow_up_received`; if the new analysis escalates
again, a fresh `pending_review` case opens. Everything is recorded in the audit trail.

```bash
curl -X POST http://127.0.0.1:8000/api/cases/$CASE_ID/follow-up \
  -H "Authorization: Bearer $TOKEN" -F "answer=Mostly the older lower leaves" -F kind=leaf_closeup -F "file=@closer.jpg"
```

Errors: `401`, `404`, `413`/`415`/`400` (bad file), `422` (neither `answer` nor `file`).

---

### GET /api/cases/{case_id}/analysis

The latest analysis. Auth: user (owner). Response `200`: [CaseAnalysisOut](#caseanalysisout), identical in shape to the
`analyze` response, with `expert` reflecting the current expert-side status. Errors: `401`, `404` (case not found, or
not analyzed yet).

---

### GET /api/runs/{routing_run_id}

The full route trace of one analysis: which steps ran, which model each used, latency, cost, and which steps were
skipped. Auth: user (owner of the case). Response `200`: [RunTrace](#runtrace). Errors: `401`, `404`.

```json
{
  "routing_run_id": "db64b52b-3915-4f7b-ab05-985de208001d", "case_id": "6f735c81-721d-449f-af14-46b5f536a72d",
  "decision_state": "PRELIMINARY_GUIDANCE", "reason": "mid_confidence",
  "intent": "crop_health_image", "intent_confidence": 0.8, "intent_rule": "keywords:crop_health_image",
  "path": "image_diagnosis",
  "route_trace": ["intent_router", "quality_gate", "vision", "advisory", "decision:PRELIMINARY_GUIDANCE"],
  "steps": [
    {"step": "intent_router", "model_name": "keyword-intent-rules", "latency_ms": 0, "cost_usd": 0.0, "confidence": 0.8, "predicted_label": null, "outcome": "ok", "error": null},
    {"step": "quality_gate", "model_name": "opencv-quality-gate", "latency_ms": 35, "cost_usd": 0.0, "confidence": 1.0, "predicted_label": null, "outcome": "ok", "error": null},
    {"step": "vision", "model_name": "soybean-mobilenetv3-onnx", "latency_ms": 20, "cost_usd": 2e-05, "confidence": 0.6477788090705872, "predicted_label": "rust_like", "outcome": "ok", "error": null},
    {"step": "advisory", "model_name": "placeholder-advisory", "latency_ms": 0, "cost_usd": 0.0, "confidence": null, "predicted_label": null, "outcome": "ok", "error": null}
  ],
  "skipped_steps": ["weather"], "estimated_cost_saved_usd": 0.0,
  "total_latency_ms": 55, "total_cost_usd": 2e-05, "created_at": "2026-09-30T20:30:45.260551Z"
}
```

---

### GET /api/weather

District weather with provenance. Auth: any signed-in user. Query: `district` (string, 1 to 60 chars, default `Pune`;
any of the 36 Maharashtra districts; old and new names both work, for example `Aurangabad` resolves to
`Chhatrapati Sambhajinagar`). Response `200`: [WeatherResult](#weatherresult).

Source order: **live** Open-Meteo forecast-model data (3 second timeout; this is *not* IMD), then **cached** (the latest
live reading, keeping its original `observed_at`, `stale: true` after 6 hours), then **demo** data (only Pune has a demo
file; clearly labelled), then **unavailable** (`available: false`). When the live source was not used, `error` says why.
Every result is stored in `weather_snapshots`.

```bash
curl "http://127.0.0.1:8000/api/weather?district=Pune" -H "Authorization: Bearer $TOKEN"
```

```json
{
  "available": true, "source": "live", "provider": "Open-Meteo", "district": "Pune",
  "observed_at": "2026-10-01T02:00:00+05:30", "fetched_at": "2026-09-30T20:31:03.240691Z", "stale": false,
  "temperature_c": 22.7, "humidity_pct": 92.0, "precipitation_mm": 0.0,
  "rain_next_24h_mm": 0.8, "rain_probability_max_pct": 71.0, "wind_speed_kmh": 0.8,
  "error": null,
  "summary": "Pune: now 23°C, humidity 92%. Rain expected in the next 24 hours: 1 mm (chance up to 71%).",
  "source_label": "Open-Meteo forecast-model data (live), for 01 Oct 02:00 IST"
}
```

A fallback is labelled honestly, for example `"source": "demo"`, `"source_label": "DEMO data for testing only, not a
real forecast"`, `"error": "live_failed: ConnectTimeout: timed out"`.

Errors: `401`; `422` for an unknown district:

```json
{"detail": {"message": "Unknown Maharashtra district: 'Atlantis'", "districts": ["Ahilyanagar", "Akola", "Amravati", "..."]}}
```

---

### GET /api/expert/cases

The expert queue. Auth: **expert**. Query: `status` = `pending_review` (default) \| `awaiting_farmer` \| `reviewed` \|
`follow_up_received` \| `all`; anything else is `422`. Response `200`: [ExpertCaseSummary](#expertcasesummary)`[]`,
newest first. Errors: `401`, `403`, `422`.

```json
[{
  "case_id": "19463e4c-55e9-4c5a-9413-9a4f740f3a83", "expert_review_id": "a1925d00-7433-4836-a9eb-0141af9bd527",
  "status": "pending_review", "escalation_reason": "treatment_needs_expert", "district": "Pune",
  "question": "Which pesticide and how much?", "decision_state": "EXPERT_REVIEW",
  "created_at": "2026-09-30T20:31:05.700378Z"
}]
```

A case gets an entry whenever an analysis ends in `EXPERT_REVIEW`. Re-analysing a case that is still `pending_review`
refreshes that entry instead of creating a duplicate.

### GET /api/expert/cases/{case_id}

Everything the expert needs, frozen at escalation time. Auth: **expert**. Response `200`:
[ExpertCaseDetail](#expertcasedetail): `current` is the newest escalation and `history` lists all of them for the case
(newest first, including `current`). The `snapshot` holds the question, images (metadata and storage paths),
model predictions, `missing_information`, retrieved `sources` and farmer follow-up answers. Errors: `401`, `403`,
`404` (case never escalated).

```jsonc
{
  "case_id": "19463e4c-55e9-4c5a-9413-9a4f740f3a83",
  "current": {
    "id": "a1925d00-7433-4836-a9eb-0141af9bd527", "case_id": "19463e4c-55e9-4c5a-9413-9a4f740f3a83",
    "routing_run_id": "6c763648-1844-4979-a1c2-6a57b38d7b8b",
    "status": "pending_review", "escalation_reason": "treatment_needs_expert",
    "snapshot": {
      "question": "Which pesticide and how much?", "description": null, "district": "Pune",
      "growth_stage": null, "symptom_started_at": null, "recent_rainfall": null,
      "intent": "treatment_safety", "path": "treatment_safety", "images": [],
      "predictions": [{"step": "intent_router", "model_name": "keyword-intent-rules", "label": null, "confidence": 0.95,
                       "output": {"intent": "treatment_safety", "confidence": 0.95, "rule": "guard:treatment_safety", "matched": ["pesticide"]}}],
      "missing_information": ["a verified treatment source for this question", "field overview photo", "growth stage", "when the symptoms started", "recent rainfall"],
      "sources": [], "follow_ups": []
    },
    "decision": null, "label": null, "notes": null, "recommended_advisory": null,
    "reviewer_id": null, "reviewed_at": null,
    "created_at": "2026-09-30T20:31:05.700378Z", "updated_at": "2026-09-30T20:31:05.700378Z"
  },
  "history": [ /* same records, newest first */ ]
}
```

### POST /api/expert/cases/{case_id}/review

Review the case's pending escalation. Auth: **expert**. Body: `application/json`, [ReviewIn](#reviewin).
Response `200`: the updated [ExpertReviewRecord](#expertreviewrecord).

| `decision` | Meaning | Extra rules | New `status` |
|---|---|---|---|
| `likely` | Expert thinks a category is likely (still not a lab-confirmed diagnosis) | `label` **required** (a [Category](#enums)) | `reviewed` |
| `insufficient` | Not enough evidence to say anything | `label` not allowed | `reviewed` |
| `unknown` | Expert cannot identify it | `label` not allowed | `reviewed` |
| `request_more` | Ask the farmer for more information | `notes` **required** (what to send); `label` not allowed | `awaiting_farmer` |

`notes` is at most 4000 characters; `recommended_advisory` (`title`, `publisher`, optional `url`) is optional with any
decision. The farmer sees the outcome in the `expert` block of their analysis. The reviewer's user id is taken from the
token, not the body. Expert notes are **not** filtered for dosage text.

```bash
curl -X POST http://127.0.0.1:8000/api/expert/cases/$CASE_ID/review \
  -H "Authorization: Bearer $EXPERT_TOKEN" -H "Content-Type: application/json" \
  -d '{"decision":"request_more","notes":"Which crop stage is it, and which leaves are affected?"}'
```

```json
{
  "id": "a1925d00-7433-4836-a9eb-0141af9bd527", "case_id": "19463e4c-55e9-4c5a-9413-9a4f740f3a83",
  "routing_run_id": "6c763648-1844-4979-a1c2-6a57b38d7b8b",
  "status": "awaiting_farmer", "escalation_reason": "treatment_needs_expert", "snapshot": { "...": "as above" },
  "decision": "request_more", "label": null,
  "notes": "Which crop stage is it, and which leaves are affected?", "recommended_advisory": null,
  "reviewer_id": "629a692b-3f89-4aa1-bbea-b4afb67b4871", "reviewed_at": "2026-09-30T20:31:06.345145Z",
  "created_at": "2026-09-30T20:31:05.700378Z", "updated_at": "2026-09-30T20:31:06.345145Z"
}
```

Errors: `401`, `403`, `404` (never escalated), `409` (already reviewed, nothing pending), `422` (rules above).

Every escalation, update, review and follow-up is written to `audit_events` (`escalation_created`,
`escalation_updated`, `expert_review_submitted`, `follow_up_submitted`). There is no API to read the audit log yet.

---

### Metrics: GET /api/metrics/overview, /routes, /cost-latency

Auth: **expert** (they aggregate every farmer's cases; counts and timings only, no personal data). All three accept
`?days=N` (integer 1 to 365) to count only analyses from the last N days; the default is all time. Everything is
computed from stored `routing_runs` and `model_runs`. Every rate is an object `{numerator, denominator, rate}`; `rate`
is `null` when there is nothing to divide by. Percentiles use the nearest-rank method. Errors: `401`, `403`, `422`
(`days` out of range).

| Endpoint | Response | Contents |
|---|---|---|
| `/api/metrics/overview` | [Overview](#overview) | Total cases/analyses; average, p50, p95 latency; cost per case; escalation, abstention, vision-abstention, retrieval-success and cache-hit rates; weather sources; model-disagreement count; decision-state counts; explanatory `notes`. |
| `/api/metrics/routes` | [RoutesOut](#routesout) | Route distribution (share, latency, cost, states per path); intent and state counts; how often vision was called; skipped steps; estimated cost saved. |
| `/api/metrics/cost-latency` | [CostLatencyOut](#costlatencyout) | Per-step calls, errors, latency stats and cost; usage by tier (small model / vision model / large model / tool); cost saved; a what-if cost if vision always ran. |

Definitions:

| Metric | Meaning |
|---|---|
| `total_cases` / `total_analyses` | Distinct cases analyzed / `routing_runs` rows (a re-analysis or follow-up counts again). |
| `cost_per_case_usd` | Total estimated cost ÷ distinct cases. Costs are estimates from a per-call table, not billed amounts. |
| `escalation_rate` | Analyses ending in `EXPERT_REVIEW`. |
| `abstention_rate` | Analyses that gave no guidance: every state except `PRELIMINARY_GUIDANCE`. |
| `vision_abstention_rate` | Of analyses where the vision model ran, those ending in low confidence, unknown label, or conflict. |
| `retrieval_success_rate` | Advisory lookups that returned at least one source, all verified and not stale. |
| `cache_hit_rate` | Weather lookups served from the cached snapshot instead of live. |
| `model_disagreement_count` | Analyses where vision models named different labels (always 0 while only one vision model is deployed). |
| Tiers | `small_model`: intent router and OpenCV quality gate. `vision_model`: the soybean classifier. `large_model`: LLM calls (none yet). `tool`: advisory and weather. |

Example (`/api/metrics/overview`, abbreviated to 3 analyses):

```json
{
  "window": {"days": null, "since": null, "generated_at": "2026-09-30T20:31:06.522388Z"},
  "total_cases": 3, "total_analyses": 3,
  "latency_per_analysis": {"n": 3, "avg_ms": 80.67, "p50_ms": 55.0, "p95_ms": 187.0, "max_ms": 187.0},
  "cost_total_usd": 2e-05, "cost_per_case_usd": 6.67e-06, "cost_per_analysis_usd": 6.67e-06,
  "escalation_rate": {"numerator": 1, "denominator": 3, "rate": 0.3333},
  "abstention_rate": {"numerator": 1, "denominator": 3, "rate": 0.3333},
  "vision_abstention_rate": {"numerator": 0, "denominator": 1, "rate": 0.0},
  "retrieval_success_rate": {"numerator": 1, "denominator": 2, "rate": 0.5},
  "cache_hit_rate": {"numerator": 0, "denominator": 1, "rate": 0.0},
  "weather_sources": {"live": 1}, "model_disagreement_count": 0,
  "decision_states": {"PRELIMINARY_GUIDANCE": 2, "EXPERT_REVIEW": 1},
  "notes": ["Only one vision model is deployed, so model disagreement cannot occur yet (count is 0 by construction).",
            "No weather lookup was served from cache in this window (the cache is used only when the live source fails)."]
}
```

## Reference: states, intents, routes, reasons

### Decision states

`state` (in `CaseOut.decision_state`, `CaseAnalysisOut.state`, `OrchestratorResult.state`, `RunTrace.decision_state`).

| State | Meaning | What the client should do |
|---|---|---|
| `NEEDS_BETTER_IMAGE` | The photo failed the quality gate (or no photo was sent). The vision model was **not** called. | Show `message`; let the farmer retake/upload, then `follow-up` or `analyze` again. Check `result.calls[].output.next_action`. |
| `NEEDS_MORE_CONTEXT` | Not enough information to go on. | Show `message` and `follow_up_question`; send the answer or a field-overview photo via `follow-up`. |
| `PRELIMINARY_GUIDANCE` | An answer was produced. Image answers are always a preliminary observation, never a confirmed diagnosis, and never contain pesticide names or doses. | Show `message`; if `follow_up_question` is set, ask it. |
| `EXPERT_REVIEW` | Escalated to a human expert; an expert case is open (`expert.status`). | Tell the farmer an expert is looking. Poll the analysis for `expert.status` / `expert.notes`. |
| `UNSUPPORTED` | Out of scope: not soybean, or a request type the app does not handle (other crops, loans, prices, schemes). | Show `message`. |

### Intents and the rules that pick them

`result.intent` is one of seven values, decided by deterministic English + Marathi keyword rules (no model call).
`result.intent_rule` says which rule fired and `result.intent_confidence` is the rule's confidence.

| Intent | Typical question | Route taken |
|---|---|---|
| `expert_escalation` | "I want to talk to an expert" | `expert_escalation` → `EXPERT_REVIEW` |
| `treatment_safety` | "Which pesticide and how much?" | `treatment_safety` → `EXPERT_REVIEW` (no verified structured source exists yet) |
| `unsupported_request` | "My cotton leaves have spots", "market price?" | `unsupported_request` → `UNSUPPORTED` |
| `weather_context` | "Will it rain in my area?" | `weather` |
| `advisory_lookup` | "Latest KVK advisory for soybean" | `advisory_lookup` |
| `general_crop_question` | "When should I sow?" | `general_crop_question` |
| `crop_health_image` | "Yellow spots on the leaves" (+ photo) | `image_diagnosis` |

`intent_rule` values: `guard:<intent>` (only for `expert_escalation`, `treatment_safety`, `unsupported_request`; these win over any
other match), `keywords:<intent>` (topic intents, highest keyword score wins; an attached photo adds a point to
`crop_health_image`), `fallback:photo_attached` (nothing matched, photo present → `crop_health_image`), `fallback:no_match`
(nothing matched, no photo → `general_crop_question` with low confidence, which ends as `NEEDS_MORE_CONTEXT` /
`intent_unclear`).

### Routes (orchestration paths)

`result.path`, `RunTrace.path`, and `routing_runs.route`. The path is chosen by the intent; it decides which steps run.

| Route | Steps that run | Possible states |
|---|---|---|
| `image_diagnosis` | `intent_router` → `quality_gate` → `vision` → `advisory` → `weather` (weather only above 0.85 confidence) | `NEEDS_BETTER_IMAGE`, `NEEDS_MORE_CONTEXT`, `PRELIMINARY_GUIDANCE`, `EXPERT_REVIEW` |
| `weather` | `intent_router` → `weather` | `PRELIMINARY_GUIDANCE`, `EXPERT_REVIEW` (weather unusable) |
| `treatment_safety` | `intent_router` → `advisory` | `EXPERT_REVIEW`; `PRELIMINARY_GUIDANCE` only with a verified structured source (none exist yet) |
| `advisory_lookup` | `intent_router` → `advisory` | `PRELIMINARY_GUIDANCE`, `EXPERT_REVIEW` (no usable source) |
| `general_crop_question` | `intent_router` → `advisory` | `PRELIMINARY_GUIDANCE`, `EXPERT_REVIEW` (no usable source), and `NEEDS_MORE_CONTEXT` (`intent_unclear`) when the question was not understood and there is no photo |
| `expert_escalation` | `intent_router` | `EXPERT_REVIEW` |
| `unsupported_request` | `intent_router` | `UNSUPPORTED` |
| `none` | none | Stored only in `routing_runs` when the case's crop is not soybean (the API rejects those at creation, so it is unreachable through it). |

### Steps (model / tool names)

Names used in `route_trace`, `calls[].route` and `steps[].step`. `route_trace` also ends with `decision:<STATE>`.

| Step | Model name | Tier | What it does |
|---|---|---|---|
| `intent_router` | `keyword-intent-rules` | small model | Classifies the question. `confidence` = rule confidence. |
| `quality_gate` | `opencv-quality-gate` | small model | Blur, brightness, size, leaf presence. `confidence` = score ÷ 100. |
| `vision` | `soybean-mobilenetv3-onnx` | vision model | Soybean classifier; `output[].label` is a [Category](#enums). |
| `advisory` | `placeholder-advisory` | tool | Retrieval (placeholder source for now). |
| `weather` | `weather-adapter` | tool | Open-Meteo → cache → demo. |

`skipped_steps` lists the steps of this set that were not called in that analysis; `estimated_cost_saved_usd` is
their estimated cost.

### Decision reasons

`result.reason` (and `expert_reviews.escalation_reason`). Confidence thresholds are configurable
(`VISION_LOW_CONFIDENCE=0.60`, `VISION_HIGH_CONFIDENCE=0.85`): below 0.60 is low, 0.60 to 0.85 inclusive is mid, above 0.85 is high.

| Reason | State | Meaning |
|---|---|---|
| `quality:<issue>` | `NEEDS_BETTER_IMAGE` | Quality gate failed; `<issue>` is one of the [quality issues](#quality-gate-issues) |
| `crop_not_soybean` | `UNSUPPORTED` | Crop is not soybean (defence in depth) |
| `unsupported_request` | `UNSUPPORTED` | Out-of-scope request |
| `intent_unclear` | `NEEDS_MORE_CONTEXT` | Question not understood and no photo; `follow_up_question` set |
| `farmer_requested_expert` | `EXPERT_REVIEW` | Farmer asked for an expert |
| `treatment_needs_expert` | `EXPERT_REVIEW` | Pesticide/dose question with no verified structured source |
| `treatment_verified_source` | `PRELIMINARY_GUIDANCE` | Points to a verified structured source, never a dose (not reachable yet) |
| `weather_context` | `PRELIMINARY_GUIDANCE` | Weather answer with its source label |
| `advisory_lookup` / `general_crop_question` | `PRELIMINARY_GUIDANCE` | Advisory-based answer |
| `low_confidence_request_evidence` | `NEEDS_MORE_CONTEXT` | Vision confidence < 0.60, no field-overview photo yet: asks for one |
| `low_confidence_escalate` | `EXPERT_REVIEW` | Vision confidence < 0.60 even with a field-overview photo |
| `models_conflict` | `EXPERT_REVIEW` | Vision models disagree |
| `label_unknown` | `EXPERT_REVIEW` | Vision says `unknown` with enough confidence |
| `mid_confidence` | `PRELIMINARY_GUIDANCE` | 0.60 to 0.85: advisory + one follow-up question, **no treatment** |
| `high_confidence` | `PRELIMINARY_GUIDANCE` | > 0.85: advisory + weather, still preliminary |
| `sources_unavailable:<why>` | `EXPERT_REVIEW` | A needed source failed or was missing/stale. `<why>` is `advisory`, `weather`, `vision_error`, `quality_gate_error` or `intent_router_error` |

### Quality-gate issues

`quality:<issue>` reasons and `calls[].output.issues` (all issues found are listed; the first drives `next_action`).

| Issue | `next_action` | Meaning |
|---|---|---|
| `missing_image` | `upload_image` | No close-up photo |
| `unreadable_image` | `upload_image` | File could not be decoded |
| `too_small` | `retake_closer` | Shorter side below 224 px |
| `too_dark` | `retake_in_daylight` | Too dark |
| `too_bright` | `retake_avoid_glare` | Overexposed |
| `blurry` | `retake_steady` | Out of focus / motion blur |
| `no_leaf_detected` | `retake_leaf_in_frame` | Too little plant colour |

When the gate passes, `issues` is `[]` and `next_action` is `"continue"`. `score` is 0 to 100.

### Expert workflow

`ExpertStatus`: `pending_review` (waiting for an expert) → `reviewed` (decision `likely` / `insufficient` / `unknown`) or
`awaiting_farmer` (decision `request_more`) → `follow_up_received` (farmer answered). `escalation_reason` is one of the
decision reasons above that produced `EXPERT_REVIEW`.

### Weather sources

`WeatherResult.source`: `live` (Open-Meteo, not IMD), `cached` (a re-served live reading with its original `observed_at`;
`stale: true` after 6 h, and stale weather is not used for answers), `demo` (illustrative file, labelled), `unavailable`.

## Schemas

Generated from the running app's OpenAPI spec. `?` marks an optional field; `| null` means the value can be null.

### Cases and images

#### CaseCreate

```ts
CaseCreate {
  crop: string;
  district?: string;  // default "Pune"
  symptom_context: string;  // min length 1, max length 2000
  language?: "en" | "mr";  // default "en"
  growth_stage?: string | null;  // max length 100
  symptom_started_at?: string /* date */ | null;
  recent_rainfall?: string | null;  // max length 200
  description?: string | null;  // max length 2000
}
```

#### CaseOut

```ts
CaseOut {
  crop: string;
  district?: string;  // default "Pune"
  symptom_context: string;  // min length 1, max length 2000
  language?: "en" | "mr";  // default "en"
  growth_stage?: string | null;  // max length 100
  symptom_started_at?: string /* date */ | null;
  recent_rainfall?: string | null;  // max length 200
  description?: string | null;  // max length 2000
  id: string /* uuid */;
  user_id: string /* uuid */;
  decision_state?: DecisionState | null;
  created_at: string /* date-time */;
}
```

#### ImageOut

```ts
ImageOut {
  id: string /* uuid */;
  case_id: string /* uuid */;
  kind: ImageKind;
  storage_path: string;
  content_type: string;
  size_bytes: integer;
  created_at: string /* date-time */;
}
```

### Analysis

#### CaseAnalysisOut

```ts
CaseAnalysisOut {
  routing_run_id: string /* uuid */;
  case_id: string /* uuid */;
  state: DecisionState;
  result: OrchestratorResult;
  created_at: string /* date-time */;
  expert?: ExpertFeedback | null;
}
```

#### OrchestratorResult

```ts
OrchestratorResult {
  state: DecisionState;
  reason: string;
  message: string;
  follow_up_question?: string | null;
  preliminary_label?: Category | null;
  confidence?: number | null;
  sources?: AdvisorySource[];
  route_trace?: string[];
  calls?: CallLog[];
  total_latency_ms?: integer;  // default 0
  total_cost_usd?: number;  // default 0.0
  intent?: Intent | null;
  intent_confidence?: number | null;
  intent_rule?: string | null;
  path?: string | null;
  skipped_steps?: string[];
  estimated_cost_saved_usd?: number;  // default 0.0
}
```

#### CallLog

```ts
CallLog {
  route: string;
  model: string;
  latency_ms: integer;
  cost_usd?: number;  // default 0.0
  confidence?: number | null;
  outcome?: string;  // default "ok"
  error?: string | null;
  output?: object | any[] | null;
}
```

#### AdvisorySource

```ts
AdvisorySource {
  title: string;
  publisher: string;
  verified: boolean;
  stale?: boolean;  // default False
  structured?: boolean;  // default False
}
```

#### ExpertFeedback

```ts
ExpertFeedback {
  status: ExpertStatus;
  decision?: ReviewDecision | null;
  label?: Category | null;
  notes?: string | null;
  recommended_advisory?: RecommendedAdvisory | null;
  reviewed_at?: string /* date-time */ | null;
}
```

#### RecommendedAdvisory

```ts
RecommendedAdvisory {
  title: string;  // min length 1, max length 300
  publisher: string;  // min length 1, max length 200
  url?: string | null;  // max length 500
}
```

### Run trace

#### RunTrace

```ts
RunTrace {
  routing_run_id: string /* uuid */;
  case_id: string /* uuid */;
  decision_state: DecisionState | null;
  reason: string | null;
  intent: string | null;
  intent_confidence: number | null;
  intent_rule: string | null;
  path: string;
  route_trace: string[];
  steps: RunStep[];
  skipped_steps: string[];
  estimated_cost_saved_usd: number;
  total_latency_ms: integer;
  total_cost_usd: number;
  created_at: string /* date-time */;
}
```

#### RunStep

```ts
RunStep {
  step: string;
  model_name: string;
  latency_ms: integer;
  cost_usd: number;
  confidence?: number | null;
  predicted_label?: string | null;
  outcome: string;
  error?: string | null;
}
```

### Weather

#### WeatherResult

```ts
WeatherResult {
  available: boolean;
  source?: "live" | "cached" | "demo" | "unavailable";  // default "unavailable"
  provider?: string | null;
  district?: string | null;
  observed_at?: string /* date-time */ | null;
  fetched_at?: string /* date-time */ | null;
  stale?: boolean;  // default False
  temperature_c?: number | null;
  humidity_pct?: number | null;
  precipitation_mm?: number | null;
  rain_next_24h_mm?: number | null;
  rain_probability_max_pct?: number | null;
  wind_speed_kmh?: number | null;
  error?: string | null;
  summary?: string;
  source_label: string;
}
```

### Expert workflow

#### ExpertCaseSummary

```ts
ExpertCaseSummary {
  case_id: string /* uuid */;
  expert_review_id: string /* uuid */;
  status: ExpertStatus;
  escalation_reason: string;
  district: string;
  question: string;
  decision_state?: DecisionState | null;
  created_at: string /* date-time */;
}
```

#### ExpertCaseDetail

```ts
ExpertCaseDetail {
  case_id: string /* uuid */;
  current: ExpertReviewRecord;
  history: ExpertReviewRecord[];
}
```

#### ExpertReviewRecord

```ts
ExpertReviewRecord {
  id: string /* uuid */;
  case_id: string /* uuid */;
  routing_run_id: string /* uuid */;
  status: ExpertStatus;
  escalation_reason: string;
  snapshot: EscalationSnapshot;
  decision?: ReviewDecision | null;
  label?: Category | null;
  notes?: string | null;
  recommended_advisory?: RecommendedAdvisory | null;
  reviewer_id?: string /* uuid */ | null;
  reviewed_at?: string /* date-time */ | null;
  created_at: string /* date-time */;
  updated_at: string /* date-time */;
}
```

#### EscalationSnapshot

```ts
EscalationSnapshot {
  question: string;
  description?: string | null;
  district: string;
  growth_stage?: string | null;
  symptom_started_at?: string | null;
  recent_rainfall?: string | null;
  intent?: string | null;
  path?: string | null;
  images?: ImageOut[];
  predictions?: Prediction[];
  missing_information?: string[];
  sources?: AdvisorySource[];
  follow_ups?: string[];
}
```

#### Prediction

```ts
Prediction {
  step: string;
  model_name: string;
  label?: string | null;
  confidence?: number | null;
  output?: object | any[] | null;
}
```

#### ReviewIn

```ts
ReviewIn {
  decision: ReviewDecision;
  notes?: string;  // max length 4000
  label?: Category | null;
  recommended_advisory?: RecommendedAdvisory | null;
}
```

### Metrics

#### Overview

```ts
Overview {
  window: MetricsWindow;
  total_cases: integer;
  total_analyses: integer;
  latency_per_analysis: LatencyStats;
  cost_total_usd: number;
  cost_per_case_usd: number | null;
  cost_per_analysis_usd: number | null;
  escalation_rate: Rate;
  abstention_rate: Rate;
  vision_abstention_rate: Rate;
  retrieval_success_rate: Rate;
  cache_hit_rate: Rate;
  weather_sources: { [key: string]: integer };
  model_disagreement_count: integer;
  decision_states: { [key: string]: integer };
  notes?: string[];
}
```

#### RoutesOut

```ts
RoutesOut {
  window: MetricsWindow;
  total_analyses: integer;
  by_path: PathStats[];
  by_intent: { [key: string]: integer };
  by_decision_state: { [key: string]: integer };
  vision_call_rate: Rate;
  skipped_steps: { [key: string]: integer };
  estimated_cost_saved_usd: number;
}
```

#### CostLatencyOut

```ts
CostLatencyOut {
  window: MetricsWindow;
  total_analyses: integer;
  latency_per_analysis: LatencyStats;
  cost_total_usd: number;
  cost_per_analysis_usd: number | null;
  cost_per_case_usd: number | null;
  by_step: StepStats[];
  by_tier: TierStats[];
  estimated_cost_saved_usd: number;
  cost_if_vision_always_ran_usd: number | null;
  notes?: string[];
}
```

#### Rate

```ts
Rate {
  numerator: integer;
  denominator: integer;
  rate: number | null;
}
```

#### LatencyStats

```ts
LatencyStats {
  n: integer;
  avg_ms?: number | null;
  p50_ms?: number | null;
  p95_ms?: number | null;
  max_ms?: number | null;
}
```

#### MetricsWindow

```ts
MetricsWindow {
  days: integer | null;
  since: string /* date-time */ | null;
  generated_at: string /* date-time */;
}
```

#### PathStats

```ts
PathStats {
  path: string;
  count: integer;
  share: number;
  avg_latency_ms: number | null;
  avg_cost_usd: number | null;
  decision_states: { [key: string]: integer };
}
```

#### StepStats

```ts
StepStats {
  step: string;
  tier: string;
  calls: integer;
  errors: integer;
  latency: LatencyStats;
  total_cost_usd: number;
  avg_cost_usd: number | null;
}
```

#### TierStats

```ts
TierStats {
  tier: string;
  description: string;
  calls: integer;
  share_of_calls: number | null;
  total_cost_usd: number;
  share_of_cost: number | null;
}
```

### Enums

- `DecisionState`: `NEEDS_BETTER_IMAGE`, `NEEDS_MORE_CONTEXT`, `PRELIMINARY_GUIDANCE`, `EXPERT_REVIEW`, `UNSUPPORTED`
- `Intent`: `crop_health_image`, `general_crop_question`, `weather_context`, `advisory_lookup`, `treatment_safety`, `expert_escalation`, `unsupported_request`
- `Category`: `healthy`, `rust_like`, `leaf_spot_like`, `insect_damage`, `unknown`
- `ImageKind`: `leaf_closeup`, `field_overview`
- `ExpertStatus`: `pending_review`, `awaiting_farmer`, `reviewed`, `follow_up_received`
- `ReviewDecision`: `likely`, `insufficient`, `request_more`, `unknown`

## Known gaps

Things a client developer should know are **not** there (or not proven) yet:

- **No image download.** Photos are private in Supabase Storage and only `storage_path` is returned. Experts cannot view
  the photos through the API yet (they need signed links).
- **No audit-log endpoint.** `audit_events` is written but cannot be read through the API.
- **No pagination or rate limiting.** `/api/cases` and the expert queue return every row.
- **Public schema.** `/docs`, `/redoc` and `/openapi.json` need no token.
- **Advisory source is a placeholder.** `sources[].publisher == "placeholder"`; no verified, structured treatment records
  exist, so every treatment question escalates.
- **Expert notes are not filtered** for pesticide names or doses.
- **Default storage is in memory** (`STORE_BACKEND=memory`): data disappears on restart. `STORE_BACKEND=supabase` is
  implemented and tested against a fake of Supabase's API, but has not been run against a real project, and the SQL
  migrations in `supabase/migrations/` have not been applied to one.
- **Weather demo data exists only for Pune.** Other districts fall back from live straight to `unavailable`.
- **Keyword intent routing is brittle:** misspellings and Marathi written in Latin letters fall back to "unclear".
- **`description` is routing input** (see `analyze`), so stray words there can change the route.
