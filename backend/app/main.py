from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.cases import cases as cases_router
from app.api.cases import questions as questions_router
from app.api.cases import runs as runs_router
from app.api.expert import router as expert_router
from app.api.files import router as files_router
from app.api.metrics import router as metrics_router
from app.api.weather import router as weather_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Same 422 body as FastAPI's default, but safe when the offending input is raw bytes (for example a
        multipart upload sent to a JSON endpoint), which the default handler cannot encode and turns into a 500."""
        errors = [
            {**e, "input": "<binary data omitted>"} if isinstance(e.get("input"), (bytes, bytearray)) else e
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})

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
    app.include_router(questions_router)
    app.include_router(files_router)
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
