from fastapi import FastAPI

from app.api.cases import cases as cases_router
from app.api.cases import runs as runs_router
from app.api.expert import router as expert_router
from app.api.weather import router as weather_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(cases_router)
app.include_router(runs_router)
app.include_router(weather_router)
app.include_router(expert_router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }
