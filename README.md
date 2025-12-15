Author: Andrea Bizzoni

# Steel Production Forecasting API

A REST API for steel production forecasting. 

## How it works

1. Upload Excel files using one of the available endpoints.

__Note: the spreadsheets must follow the templates provided by the hiring team. You can find sample spreadsheets in the ```app/data``` folder.__

2. Use the forecast endpoint to forecast heats production.

## Setup

### Prerequisites

Make sure you have the following tools available on your machine:

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone repository
git clone https://github.com/andreabizzoni/fdm.git

# Enter directory
cd fdm

# Install dependencies
uv sync

# Run the server
uv run uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

## Usage

### Upload Data

Run the following curl commands from your terminal to upload the data to the database. These commands already point to the right spreadsheets within the project. Alternatively, you can try uploading your own spreadsheets.

```bash
# Upload monthly forecast
curl -s -X POST "http://localhost:8000/upload/monthly-forecast" -F "file=@app/data/product_groups_monthly.xlsx"

# Upload production history
curl -s -X POST "http://localhost:8000/upload/production-history" -F "file=@app/data/steel_grade_production.xlsx"

# Upload daily schedule
curl -s -X POST "http://localhost:8000/upload/daily-schedule" -F "file=@app/data/daily_charge_schedule.xlsx"
```

### Get Forecast

To get the production forecast, use the following curl command:

```bash
curl -X GET "http://localhost:8000/forecast/2024/9"
```

**Response:**
```json
{
  "month": "September 2024",
  "forecasts": [
    {"grade": "B500A", "product_group": "Rebar", "heats": 86},
    {"grade": "B500B", "product_group": "Rebar", "heats": 105},
    ...
  ]
}
```

__Note: The forecast is currently only avaiable for Sep 2024 production. If you try accessing any other forecast endpoints, the request will fail.__

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload/daily-schedule` | Upload daily charge schedule |
| `POST` | `/upload/monthly-forecast` | Upload monthly forecast by product group |
| `POST` | `/upload/production-history` | Upload historical production data |
| `GET` | `/forecast/{year}/{month}` | Get heat forecast by steel grade |
| `GET` | `/health` | Health check |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Excel Parsing | pandas + openpyxl |

## Database Schema

```
product_groups (id, name)
steel_grades (id, name, product_group_id)
monthly_forecasts (id, product_group_id, month, heats)
production_history (id, steel_grade_id, month, tons)
daily_schedules (id, date, start_time, steel_grade_id, mould_size)
```

## Testing

Like any good Software Engineer, I have included a comprehensive test suite, which you can access by running:

```bash
uv run pytest tests/ -v
```
