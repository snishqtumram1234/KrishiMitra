from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import cases as cases_router
from app.api.cases import runs as runs_router
from app.api.expert import router as expert_router
from app.api.metrics import router as metrics_router
from app.api.weather import router as weather_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name)

    # CORS: lets the browser frontend call this API from another origin. Auth is a Bearer token in
    # the Authorization header (no cookies), so credentials are not enabled. Preflight (OPTIONS)
    # requests are answered here, before auth, because browsers send them without a token.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            max_age=600,
        )

    app.include_router(cases_router)
    app.include_router(runs_router)
    app.include_router(weather_router)
    app.include_router(expert_router)
    app.include_router(metrics_router)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
        }

    return app


app = create_app()
