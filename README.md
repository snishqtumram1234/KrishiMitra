# KrishiMitra

Uncertainty-aware agricultural AI orchestrator for soybean farmers in Maharashtra.
See [CLAUDE.md](CLAUDE.md) for scope, routing policy and rules.

**Status:** backend has the orchestrator, policy engine, case/upload/analyze endpoints (in-memory store) and an ONNX vision service. `ml/` trains the model. No frontend or Supabase persistence yet.

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

## Layout

```
backend/app/   main.py, config.py, api/, schemas/, services/ (empty stubs)
frontend/      Next.js app (not created yet)
ml/            dataset prep, training, evaluation, ONNX export
supabase/migrations/
data/          advisories/, demo-cases/, evaluation/
```
