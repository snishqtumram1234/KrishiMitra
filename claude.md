# KrishiMitra

Uncertainty-aware agricultural AI ORCHESTRATOR for soybean farmers in Maharashtra.
Domain: AI model optimization. Track: AI model orchestration.

## Non-negotiable rules
- Orchestration is the product. The orchestrator decides per query: classify,
  retrieve, calculate, ask for more evidence, or escalate to a human expert.
- ML models (image-quality, soybean vision, intent, embeddings) are specialist
  components called BY the orchestrator. They are never the product.
- Every model/tool call is logged (route, model, latency, cost, confidence, outcome).
- Never present a prediction as a confirmed diagnosis.
- Never generate pesticide dosage. No treatment advice without a verified source.
- Build ONE small piece at a time. Test before moving on. Do not expand the MVP.

## MVP scope
- Geography: Maharashtra (district level, default Pune)
- Crop: soybean only
- Languages: English + Marathi (text)
- Categories: healthy, rust_like, leaf_spot_like, insect_damage, unknown
- Required input: close-up leaf photo, crop, district, symptom context
- Optional: field overview photo, growth stage, rainfall, description

## Decision states
NEEDS_BETTER_IMAGE, NEEDS_MORE_CONTEXT, PRELIMINARY_GUIDANCE, EXPERT_REVIEW, UNSUPPORTED

## Routing policy (initial thresholds, tune later)
1. Check image quality first. Poor -> request better image.
2. Crop != soybean -> unsupported.
3. Classify intent (keyword rules / lightweight classifier, not an expensive model).
4. Vision confidence < 0.60 -> do not diagnose; request evidence or escalate.
5. 0.60-0.85 -> retrieve advisory, ask one follow-up, no high-risk treatment.
6. > 0.85 -> retrieve advisory + weather, cautious preliminary guidance.
7. Missing/stale sources, or conflicting models -> uncertain, escalate.
8. Log everything.

## Stack (fixed, do not change)
- Frontend: Next.js, TypeScript, Tailwind, Recharts
- Backend: Python, FastAPI, Pydantic, HTTPX
- DB/Auth/Storage: Supabase (Postgres, optional pgvector)
- NO Vite, Docker, Kubernetes, or microservices

## Folder structure
krishimitra/
  frontend/   (Next.js app)
  backend/app/ (main.py, api/, schemas/, services/: orchestrator, quality_gate,
                intent_router, vision_service, weather_service, advisory_service,
                policy_engine, metrics_service)
  ml/         (dataset prep, training, evaluation, ONNX export)
  supabase/migrations/
  data/ (advisories/, demo-cases/, evaluation/)

## Datasets
- ASDID: healthy, rust, leaf spot classes (train)
- Mignoni insect dataset: insect damage class (train)
- Indian/Maharashtra soybean dataset: HELD-OUT evaluation only, never train on it

## Data tables
profiles, farmer_profiles, crop_cases, case_images, routing_runs, model_runs,
weather_snapshots, advisory_documents, advisory_matches, expert_reviews, audit_events

## First milestone (vertical slice)
create case -> upload image -> quality check -> vision prediction ->
safety decision -> result page. Nothing else until this works.