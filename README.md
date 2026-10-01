# KrishiMitra

Uncertainty-aware agricultural AI orchestrator for soybean farmers in Maharashtra.
See [CLAUDE.md](CLAUDE.md) for scope, routing policy and rules.

**Status:** backend has the orchestrator, policy engine, OpenCV quality gate, ONNX vision model, and JWT-protected `/api` endpoints with an in-memory or Supabase store. `ml/` trains the model. No frontend yet.

## Run the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# real model: put soybean_vision.onnx + soybean_vision.json in backend/models/ (see ml/README.md),
# or set VISION_BACKEND=fake in .env for random dev output
uvicorn app.main:app --reload
```

## Test

```powershell
# in backend/, venv active
pytest
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok","app":"KrishiMitra","environment":"development"}`.
Interactive docs: http://127.0.0.1:8000/docs

## API
All `/api/*` routes need `Authorization: Bearer <Supabase access token>`; `/health` is public.

| Method | Path | |
|---|---|---|
| POST | `/api/cases` | create a case (soybean only) |
| GET | `/api/cases`, `/api/cases/{id}` | your cases |
| POST | `/api/cases/{id}/images` | multipart: `kind` = `leaf_closeup` or `field_overview`, `file` (JPEG/PNG/WebP, max 10 MB) |
| POST | `/api/cases/{id}/analyze` | run the orchestrator; returns `routing_run_id` + state |
| GET | `/api/cases/{id}/analysis` | latest analysis |
| GET | `/api/runs/{routing_run_id}` | route trace: intent, path, steps, models, latency, cost, skipped steps |
| POST | `/api/questions` | ask a text question with no photo (weather, advisory, treatment-safety, expert); a crop-health question asks for a photo |
| GET | `/api/cases/{id}/images/{image_id}/signed-url` | 5-minute link to a photo (case owner, or an expert on an escalated case) |
| GET | `/api/weather?district=Pune` | district weather with `source` (live / cached / demo / unavailable), `observed_at`, `source_label` |

| GET | `/api/metrics/overview`, `/routes`, `/cost-latency` | expert-only orchestration metrics (`?days=N` to window), computed from `routing_runs` / `model_runs` |

Every analysis returns stable codes (`reason_code`, `confidence_band`, `missing_information`, `follow_up_options`) and the full `trace`; the backend does not localize, so clients build English/Marathi text from those. Advisory sources are demo sources (`verified: false`) until real documents are ingested; set `ALLOW_DEMO_SOURCES=true` in `.env` for local demos. See [API.md](API.md).

Weather: live data is Open-Meteo forecast-model data (free, no key), **not IMD**. If it fails or takes over 3 s,
the backend serves the latest cached live reading (with its original `observed_at`, flagged stale after 6 h),
then the demo file in `data/demo-cases/weather/`, and labels which one it used. Every result is stored in `weather_snapshots`.

Local testing without Supabase: set `SUPABASE_JWT_SECRET` in `.env` to any long random string and run `python scripts/dev_token.py` to mint a test token.
Production: `STORE_BACKEND=supabase`, apply `supabase/migrations/`, and verify tokens via the project's JWKS (leave `SUPABASE_JWT_SECRET` empty) or its legacy JWT secret.

## Metrics dashboard data
```powershell
# terminal 1: uvicorn app.main:app      (memory store: data lives in this process)
# terminal 2, in backend/:
python scripts/seed_demo.py --api http://127.0.0.1:8000
```
Runs the 50 cases in `data/demo-cases/cases.json` through the real API, then prints the metrics. Needs `SUPABASE_JWT_SECRET` in `.env` (dev tokens).
Images are synthetic unless you add real photos to `data/demo-cases/images/`, so vision *predictions* in the seeded data are meaningless; routing, cost and latency numbers are real.

## Layout

```
backend/app/   main.py, config.py, api/, schemas/, services/ (empty stubs)
frontend/      Next.js app (not created yet)
ml/            dataset prep, training, evaluation, ONNX export
supabase/migrations/
data/          advisories/, demo-cases/, evaluation/
```
