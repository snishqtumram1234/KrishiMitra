# KrishiMitra

Uncertainty-aware agricultural AI orchestrator for soybean farmers in Maharashtra.
See [CLAUDE.md](CLAUDE.md) for scope, routing policy and rules.

**Status:** project skeleton only. Backend has a `/health` endpoint; no features yet.

## Run the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
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
