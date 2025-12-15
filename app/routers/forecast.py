"""
Forecast endpoints.

Endpoints:
- GET /forecast/september - Generate September forecast for ScrapChef
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ForecastResponse
from app.services.forecast import calculate_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])

# September 2024 target month
SEPTEMBER_2024 = date(2024, 9, 1)


@router.get("/september", response_model=ForecastResponse)
def get_september_forecast(db: Session = Depends(get_db)):
    """
    Generate September 2024 forecast for ScrapChef.

    Returns heat distribution by steel grade based on:
    - Monthly forecast heats per product group
    - Historical production ratios per grade
    """
    forecasts = calculate_forecast(db, SEPTEMBER_2024)

    return ForecastResponse(
        month="September 2024",
        forecasts=forecasts,
    )
