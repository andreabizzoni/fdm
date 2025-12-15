from datetime import date, time
from pydantic import BaseModel


# ============================================================================
# Parser Record Schemas
# ============================================================================


class DailyScheduleRecord(BaseModel):
    """Represents a single heat from the daily schedule."""

    date: date
    start_time: time
    grade: str
    mould_size: str | None = None


class MonthlyForecastRecord(BaseModel):
    """Represents a monthly forecast for a product group."""

    product_group: str
    month: date
    heats: int


class ProductionHistoryRecord(BaseModel):
    """Represents historical production for a steel grade."""

    product_group: str
    grade: str
    month: date
    tons: float


# ============================================================================
# Upload Response Schemas
# ============================================================================


class UploadResponse(BaseModel):
    """Response for successful file upload."""

    message: str
    records_processed: int


class ErrorResponse(BaseModel):
    """Response for errors."""

    detail: str


# ============================================================================
# Forecast Schemas
# ============================================================================


class GradeForecast(BaseModel):
    """Forecast for a single steel grade."""

    grade: str
    product_group: str
    heats: int


class ForecastResponse(BaseModel):
    """Response for forecast endpoint."""

    month: str
    forecasts: list[GradeForecast]


# ============================================================================
# Data Read Schemas (for GET endpoints if needed)
# ============================================================================


class ProductGroupRead(BaseModel):
    """Read schema for product group."""

    id: int
    name: str

    model_config = {"from_attributes": True}


class SteelGradeRead(BaseModel):
    """Read schema for steel grade."""

    id: int
    name: str
    product_group_id: int

    model_config = {"from_attributes": True}


class MonthlyForecastRead(BaseModel):
    """Read schema for monthly forecast."""

    id: int
    product_group_id: int
    month: date
    heats: int

    model_config = {"from_attributes": True}


class ProductionHistoryRead(BaseModel):
    """Read schema for production history."""

    id: int
    steel_grade_id: int
    month: date
    tons: float

    model_config = {"from_attributes": True}


class DailyScheduleRead(BaseModel):
    """Read schema for daily schedule."""

    id: int
    date: date
    start_time: time
    steel_grade_id: int
    mould_size: str | None

    model_config = {"from_attributes": True}
