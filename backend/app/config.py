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

    # Image-quality gate (initial guesses; calibrate on real farmer photos)
    quality_min_side: int = 224  # px, shorter side
    quality_min_brightness: float = 40.0  # mean gray 0-255
    quality_max_brightness: float = 220.0
    quality_max_clipped_fraction: float = 0.4  # share of near-black or near-white pixels
    quality_min_sharpness: float = 60.0  # Laplacian variance at 512px long side

    # Routing thresholds (initial, tune later)
    vision_low_confidence: float = 0.60
    vision_high_confidence: float = 0.85


@lru_cache
def get_settings() -> Settings:
    return Settings()
