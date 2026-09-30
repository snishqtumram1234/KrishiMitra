import re
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ORIGIN_RE = re.compile(r"^https?://[^/\s?#]+$")  # scheme://host[:port], no path, no trailing slash


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KrishiMitra"
    environment: str = "development"
    default_district: str = "Pune"

    supabase_url: str = ""
    supabase_service_key: str = ""  # server only, never send to the frontend
    supabase_jwt_secret: str = ""  # legacy HS256 projects; leave empty to use the JWKS endpoint

    # Browser origins allowed to call the API (CORS), comma-separated, e.g.
    # "https://app.example.com,http://localhost:3000". Each must be scheme://host[:port] with no
    # trailing slash. The default covers a local Next.js dev server. Empty = same-origin only.
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Case storage: "memory" (dev/tests, lost on restart) or "supabase"
    store_backend: str = "memory"

    # Vision model: "onnx" (real, fails loudly if the file is missing) or "fake" (random, dev only)
    vision_backend: str = "onnx"
    vision_model_path: str = "models/soybean_vision.onnx"

    # Image-quality gate (initial guesses; calibrate on real farmer photos)
    quality_min_side: int = 224  # px, shorter side
    quality_min_brightness: float = 40.0  # mean gray 0-255
    quality_max_brightness: float = 220.0
    quality_max_clipped_fraction: float = 0.4  # share of near-black or near-white pixels
    quality_min_sharpness: float = 60.0  # Laplacian variance at 512px long side
    quality_min_leaf_ratio: float = 0.10  # share of plant-coloured (yellow-green to green) pixels

    # Weather: Open-Meteo live (free, no key) -> cached snapshot -> demo dataset
    weather_live_enabled: bool = True
    weather_timeout_s: float = 3.0
    weather_cache_max_age_hours: float = 6.0
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"

    # Routing thresholds (initial, tune later)
    vision_low_confidence: float = 0.60
    vision_high_confidence: float = 0.85

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _check_cors(self) -> "Settings":
        for origin in self.cors_origins:
            if origin == "*":
                if self.environment == "production":
                    raise ValueError("CORS_ALLOWED_ORIGINS=* is not allowed when ENVIRONMENT=production")
            elif not ORIGIN_RE.match(origin):
                raise ValueError(
                    f"Invalid CORS origin {origin!r}: use scheme://host[:port] with no path or trailing slash "
                    "(for example https://app.example.com)"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
