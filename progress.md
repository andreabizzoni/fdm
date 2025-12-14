# Project Summary: Steel Production API (fdm)

## Purpose
Build a FastAPI application for a steel plant to manage production plans and forecast steel grade breakdowns for ScrapChef integration.

## Core Problem
- Customer provides production plans as **product groups** (Rebar, MBQ, SBQ, CHQ)
- ScrapChef requires **steel grade** level detail
- Solution: Use historical production ratios to distribute product group heats across individual steel grades

## Data Files (in `/data/`)
1. **daily_charge_schedule.xlsx** - Daily heat schedules with times, grades, mould sizes
2. **product_groups_monthly.xlsx** - Monthly heat forecasts by product group (June-Sept 2024)
3. **steel_grade_production.xlsx** - Historical tons produced per grade (June-Aug 2024)

## Product Group → Steel Grade Mapping
- **Rebar**: B500A, B500B, B500C
- **MBQ**: A36, A5888, GR50, 44W, 50W, 55W, 60W
- **SBQ**: S235JR, S355J, C35, C40
- **CHQ**: A53/A543, A53/C591

## Completed Work
1. ✅ Project structure created (`app/`, `routers/`, `services/`, `tests/`)
2. ✅ Dependencies installed via `uv` (fastapi, sqlalchemy, pandas, openpyxl, uvicorn)
3. ✅ `app/database.py` - SQLite connection, session factory, Base class
4. ✅ `app/models.py` - 5 SQLAlchemy models (ProductGroup, SteelGrade, MonthlyForecast, ProductionHistory, DailySchedule)
5. ✅ `app/main.py` - FastAPI app with lifespan handler for table creation

## Remaining Work (per plan.md)
5. `schemas.py` - Pydantic schemas for API responses
6. `services/parser.py` - Excel file parsing functions
7. `routers/upload.py` - POST endpoints for file uploads
8. `services/forecast.py` - Forecast calculation (distribute heats by historical ratios)
9. `routers/forecast.py` - GET /forecast/september endpoint
10. `tests/` - API tests

## Key Technical Details
- **Run command**: `uvicorn app.main:app --reload`
- **Database**: SQLite at `./fdm.db`
- **Assumption**: 1 heat ≈ 100 tons of steel

## Forecast Logic
For September: Take product group heat counts → calculate each grade's historical % share within its group → apply ratios → return `[{"grade": "B500A", "heats": X}, ...]`
