# Implementation Plan

## Data Analysis Summary

### Input Files:
1. **daily_charge_schedule.xlsx** - Detailed daily schedule with start times, steel grades, and mould sizes per day
2. **product_groups_monthly.xlsx** - Monthly forecast of heats per product group (Rebar, MBQ, SBQ, CHQ) for June-September 2024
3. **steel_grade_production.xlsx** - Historical production in tons per steel grade (June-August 2024)

### Key Relationships:
- **Product Groups → Steel Grades:**
  - Rebar: B500A, B500B, B500C
  - MBQ: A36, A5888, GR50, 44W, 50W, 55W, 60W
  - SBQ: S235JR, S355J, C35, C40
  - CHQ: A53/A543, A53/C591

---

## Database Schema

```
product_groups (id, name)
steel_grades (id, name, product_group_id)
monthly_forecasts (id, product_group_id, month, heats)
production_history (id, steel_grade_id, month, tons)
daily_schedules (id, date, start_time, steel_grade_id, mould_size)
```

---

## API Endpoints

1. **POST /upload/daily-schedule** - Upload daily charge schedule file
2. **POST /upload/monthly-forecast** - Upload product groups monthly file
3. **POST /upload/production-history** - Upload steel grade production file
4. **GET /forecast/september** - Generate September forecast for ScrapChef

---

## Forecast Logic (September)

**Input:** September forecast = 232 Rebar, 54 MBQ, 10 SBQ, 22 CHQ heats

**Approach:** Distribute heats across steel grades within each product group based on historical production ratios.

**Steps:**
1. For each product group, calculate % share of each steel grade from historical tons
2. Apply ratios to September's heat count per group
3. Return: `[{ "grade": "B500A", "heats": X }, ...]`

**Assumptions:**
- 1 heat ≈ 100 tons (as stated)
- Historical ratios reflect expected future demand
- Grades with zero recent production get zero heats (or minimum allocation if needed)

---

## Tech Stack
- **Framework:** FastAPI
- **Database:** SQLite (simple, file-based)
- **ORM:** SQLAlchemy

---

## Project Structure

```
fdm/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # DB connection & session
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── upload.py        # Upload endpoints
│   │   └── forecast.py      # Forecast endpoint
│   └── services/
│       ├── __init__.py
│       ├── parser.py        # Excel file parsing logic
│       └── forecast.py      # Forecast calculation logic
├── data/                    # Input Excel files
├── tests/
│   └── test_api.py
├── plan.md
├── pyproject.toml
└── README.md
```

### Module Responsibilities:
- **models.py** - SQLAlchemy ORM models for all 5 tables
- **schemas.py** - Pydantic models for request/response validation
- **services/parser.py** - Parse Excel files into DB-ready format
- **services/forecast.py** - Calculate grade breakdown from historical ratios
- **routers/upload.py** - Handle file uploads, parse & store in DB
- **routers/forecast.py** - Query DB, compute forecast, return ScrapChef format

---

## Implementation Order

1. **Setup** - Install dependencies (fastapi, uvicorn, sqlalchemy, pandas, openpyxl, python-multipart)
2. **database.py** - DB engine, session, Base class
3. **models.py** - All SQLAlchemy models
4. **main.py** - Basic FastAPI app with table creation on startup
5. **schemas.py** - Pydantic schemas for API responses
6. **services/parser.py** - Excel parsing functions for all 3 file types
7. **routers/upload.py** - Upload endpoints (test with sample files)
8. **services/forecast.py** - Forecast calculation logic
9. **routers/forecast.py** - GET /forecast/september endpoint
10. **tests/** - Basic API tests
