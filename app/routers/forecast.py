from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ForecastResponse
from app.services.forecast import Forecaster

router = APIRouter(prefix="/forecast", tags=["forecast"])

AVAILABLE_FORECASTS = {(2024, 9)}


@router.get("/{year}/{month}", response_model=ForecastResponse)
def get_forecast(year: int, month: int, db: Session = Depends(get_db)):
    """
    Generate forecast for ScrapChef.

    Returns heat distribution by steel grade based on:
    - Monthly forecast heats per product group
    - Historical production ratios per grade

    Note: Only September 2024 forecast is currently available.
    """
    if (year, month) not in AVAILABLE_FORECASTS:
        raise HTTPException(
            status_code=400,
            detail=f"Forecast for {year}/{month:02d} is not available. "
            "This version only supports September 2024 (2024/9).",
        )

    target_month = date(year, month, 1)
    forecaster = Forecaster(db)
    forecasts = forecaster.calculate(target_month)

    month_name = target_month.strftime("%B %Y")
    return ForecastResponse(
        month=month_name,
        forecasts=forecasts,
    )
