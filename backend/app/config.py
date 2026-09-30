from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KrishiMitra"
    environment: str = "development"
    default_district: str = "Pune"

    supabase_url: str = ""
    supabase_service_key: str = ""

    # Vision model: "onnx" (real, fails loudly if the file is missing) or "fake" (random, dev only)
    vision_backend: str = "onnx"
    vision_model_path: str = "models/soybean_vision.onnx"

    # Routing thresholds (initial, tune later)
    vision_low_confidence: float = 0.60
    vision_high_confidence: float = 0.85


@lru_cache
def get_settings() -> Settings:
    return Settings()
