"""PLACEHOLDER weather lookup. Replace with a real weather API (via HTTPX) later."""

from app.schemas.orchestration import WeatherResult


class WeatherService:
    model_name = "placeholder-weather"

    def get(self, district: str) -> WeatherResult:
        return WeatherResult(available=True, stale=False, summary=f"Placeholder weather for {district}.")
