from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_user
from app.api.deps import get_weather_service
from app.schemas.orchestration import WeatherResult
from app.services.districts import all_districts, resolve_district
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/api/weather", tags=["weather"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=WeatherResult)
def get_weather(
    district: str = Query("Pune", min_length=1, max_length=60),
    service: WeatherService = Depends(get_weather_service),
):
    if resolve_district(district) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"message": f"Unknown Maharashtra district: {district!r}", "districts": all_districts()},
        )
    return service.get(district)
