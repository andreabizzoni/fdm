import io
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_data_path():
    """Path to sample data files."""
    return Path(__file__).parent.parent / "app" / "data"


# ============================================================================
# Helper functions to create test Excel files
# ============================================================================


def create_excel_bytes(df: pd.DataFrame) -> io.BytesIO:
    """Convert DataFrame to Excel bytes."""
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, header=False)
    buffer.seek(0)
    return buffer


def create_valid_monthly_forecast() -> io.BytesIO:
    """Create a valid monthly forecast Excel file."""
    data = [
        ["Order forecast (heats per quality group)", None, None, None, None],
        ["Quality:", "Jun 24", "Jul 24", "Aug 24", "Sep 24"],
        ["Rebar", 238, 219, 246, 232],
        ["MBQ", 18, 67, 62, 54],
        ["SBQ", 8, 6, 6, 10],
        ["CHQ", 24, 11, 26, 22],
    ]
    df = pd.DataFrame(data)
    return create_excel_bytes(df)


def create_valid_production_history() -> io.BytesIO:
    """Create a valid production history Excel file."""
    data = [
        ["Production history (short tons)", None, None, None, None],
        ["Quality group", "Grade", "Jun 24", "Jul 24", "Aug 24"],
        ["Rebar", "B500A", 8724, 9230, 8989],
        [None, "B500B", 10880, 11030, 10822],
        [None, "B500C", 4111, 1557, 4756],
        ["MBQ", "A36", 0, 202, 199],
    ]
    df = pd.DataFrame(data)
    return create_excel_bytes(df)


# ============================================================================
# Upload Endpoint Tests
# ============================================================================


class TestUploadEndpoints:
    """Tests for file upload endpoints."""

    def test_upload_monthly_forecast_success(self, client):
        """Test successful upload of valid monthly forecast file."""
        file_content = create_valid_monthly_forecast()
        response = client.post(
            "/upload/monthly-forecast",
            files={
                "file": (
                    "forecast.xlsx",
                    file_content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Monthly forecast uploaded successfully"
        assert data["records_processed"] > 0

    def test_upload_production_history_success(self, client):
        """Test successful upload of valid production history file."""
        file_content = create_valid_production_history()
        response = client.post(
            "/upload/production-history",
            files={
                "file": (
                    "history.xlsx",
                    file_content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Production history uploaded successfully"
        assert data["records_processed"] > 0

    def test_upload_rejects_non_excel_file(self, client):
        """Test that non-Excel files are rejected."""
        csv_content = io.BytesIO(b"col1,col2\n1,2\n3,4")
        response = client.post(
            "/upload/monthly-forecast",
            files={"file": ("data.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 400
        assert "Excel file" in response.json()["detail"]

    def test_upload_rejects_empty_excel(self, client):
        """Test that empty Excel files are rejected."""
        df = pd.DataFrame()
        buffer = create_excel_bytes(df)
        response = client.post(
            "/upload/monthly-forecast",
            files={
                "file": (
                    "empty.xlsx",
                    buffer,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code in [400, 500]

    def test_upload_rejects_wrong_structure_missing_months(self, client):
        """Test that files with missing month columns are rejected."""
        # Monthly forecast with no month data
        data = [
            ["Order forecast (heats per quality group)"],
            ["Quality:"],  # No months
            ["Rebar"],
        ]
        df = pd.DataFrame(data)
        buffer = create_excel_bytes(df)
        response = client.post(
            "/upload/monthly-forecast",
            files={
                "file": (
                    "bad.xlsx",
                    buffer,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 400
        assert "No valid records" in response.json()["detail"]

    def test_upload_rejects_wrong_structure_missing_data_rows(self, client):
        """Test that files with only headers (no data) are rejected."""
        data = [
            ["Production history (short tons)", None, None, None, None],
            ["Quality group", "Grade", "Jun 24", "Jul 24", "Aug 24"],
            # No data rows
        ]
        df = pd.DataFrame(data)
        buffer = create_excel_bytes(df)
        response = client.post(
            "/upload/production-history",
            files={
                "file": (
                    "headers_only.xlsx",
                    buffer,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 400

    def test_upload_rejects_completely_wrong_format(self, client):
        """Test that files with completely wrong format are rejected."""
        # Random data that doesn't match any expected format
        data = [
            ["Random", "Data", "Here"],
            [1, 2, 3],
            ["A", "B", "C"],
        ]
        df = pd.DataFrame(data)
        buffer = create_excel_bytes(df)
        response = client.post(
            "/upload/monthly-forecast",
            files={
                "file": (
                    "random.xlsx",
                    buffer,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 400


# ============================================================================
# Forecast Endpoint Tests
# ============================================================================


class TestForecastEndpoint:
    """Tests for forecast generation endpoint."""

    def test_forecast_september_2024_success(self, client):
        """Test successful forecast for September 2024 after uploading data."""
        # First upload required data
        forecast_file = create_valid_monthly_forecast()
        client.post(
            "/upload/monthly-forecast",
            files={
                "file": (
                    "forecast.xlsx",
                    forecast_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        history_file = create_valid_production_history()
        client.post(
            "/upload/production-history",
            files={
                "file": (
                    "history.xlsx",
                    history_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        # Now request forecast
        response = client.get("/forecast/2024/9")
        assert response.status_code == 200
        data = response.json()
        assert data["month"] == "September 2024"
        assert "forecasts" in data
        assert isinstance(data["forecasts"], list)

    def test_forecast_rejects_unsupported_month(self, client):
        """Test that forecasts for unsupported months are rejected."""
        response = client.get("/forecast/2024/10")  # October 2024
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]
        assert "September 2024" in response.json()["detail"]

    def test_forecast_rejects_different_year(self, client):
        """Test that forecasts for different years are rejected."""
        response = client.get("/forecast/2025/9")  # September 2025
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]

    def test_forecast_rejects_past_month(self, client):
        """Test that forecasts for past months are rejected."""
        response = client.get("/forecast/2024/1")  # January 2024
        assert response.status_code == 400
        assert "not available" in response.json()["detail"]

    def test_forecast_returns_non_negative_heats(self, client):
        """Test that all forecast heats are non-negative."""
        # Upload data
        forecast_file = create_valid_monthly_forecast()
        client.post(
            "/upload/monthly-forecast",
            files={
                "file": (
                    "forecast.xlsx",
                    forecast_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        history_file = create_valid_production_history()
        client.post(
            "/upload/production-history",
            files={
                "file": (
                    "history.xlsx",
                    history_file,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        response = client.get("/forecast/2024/9")
        assert response.status_code == 200
        data = response.json()

        for forecast in data["forecasts"]:
            assert forecast["heats"] >= 0, f"Negative heats for {forecast['grade']}"


# ============================================================================
# Health Check Test
# ============================================================================


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test that health check returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
